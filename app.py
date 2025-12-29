import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.io as pio

st.set_page_config(
    page_title="Indonesia Car Retail Sales (2020–2022)",
    page_icon="🚗",
    layout="wide"
)


def _clean_colname(c: str) -> str:
    return re.sub(r"\s+", " ", str(c)).strip()

def detect_year_from_filename(path: str) -> int | None:
    m = re.search(r"(20\d{2})", Path(path).name)
    return int(m.group(1)) if m else None

def detect_year_from_columns(cols) -> int | None:
    for c in cols:
        m = re.search(r"(20\d{2})", str(c))
        if m:
            return int(m.group(1))
    return None

def pick_brand_col(cols):
    for c in cols:
        if "brand" in c.lower():
            return c
    return cols[0] if cols else None

def pick_retail_col(cols):
    for c in cols:
        if "retail" in c.lower():
            return c
    return cols[1] if len(cols) > 1 else None

def _fmt_int(x):
    return "-" if pd.isna(x) else f"{x:,.0f}"

def _fmt_pct(x, digits=1):
    return "-" if pd.isna(x) else f"{x:.{digits}f}%"

@st.cache_data
def load_one_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [_clean_colname(c) for c in df.columns]
    return df

def to_long(df: pd.DataFrame, year: int) -> pd.DataFrame:
    cols = list(df.columns)
    brand_col = pick_brand_col(cols)
    retail_col = pick_retail_col(cols)

    out = df[[brand_col, retail_col]].copy()
    out = out.rename(columns={brand_col: "Brand", retail_col: "Retail"})
    out["Brand"] = out["Brand"].astype(str).str.strip()
    out["Retail"] = pd.to_numeric(out["Retail"], errors="coerce")
    out["Year"] = year
    out = out.dropna(subset=["Brand", "Retail"])
    return out[["Year", "Brand", "Retail"]]

@st.cache_data
def load_dataset_from_folder(folder="data"):
    folder = Path(folder)
    files = sorted(folder.glob("*_data.csv"))
    if not files:
        files = sorted(folder.glob("*.csv"))

    parts = []
    used = []
    for f in files:
        df = load_one_csv(str(f))
        year = detect_year_from_filename(str(f)) or detect_year_from_columns(df.columns)
        if year is None:
            continue
        parts.append(to_long(df, year))
        used.append(f.name)

    if not parts:
        return pd.DataFrame(columns=["Year", "Brand", "Retail"]), []

    data = pd.concat(parts, ignore_index=True)
    data["Year"] = data["Year"].astype(int)
    data = data.sort_values(["Year", "Retail"], ascending=[True, False])
    return data, used

# Load data & intro

st.title("🚗 Indonesia Retail Car Sales (2020–2022)")

st.markdown("""
### 🎯 Tujuan Dashboard

Dashboard ini membantu **analis pasar** dan **pengambil keputusan** untuk:
- Melihat total ukuran pasar dan pertumbuhan penjualan mobil ritel per tahun.
- Mengidentifikasi merek yang paling dominan dan pergeseran market share pasarnya.
- Menganalisis tren penjualan jangka pendek/menengah untuk tiap merek.

Gunakan panel di sebelah kiri untuk mengatur **tahun**, **merek**, dan **metrik** yang ingin dianalisis.
""")

st.divider()

df, used_files = load_dataset_from_folder("data")
with st.sidebar:
    st.header("Dataset")
    if used_files:
        st.success("Loaded: " + ", ".join(used_files))
    else:
        st.error("Tidak menemukan file bertahun (mis. 2020_data.csv). Taruh file CSV di folder /data.")
        st.stop()

years = sorted(df["Year"].unique().tolist())
brands_all = sorted(df["Brand"].unique().tolist())

# Sidebar controls

with st.sidebar:
    st.header("Controls")

    st.caption("1️⃣ Pilih tahun yang ingin dianalisis (bisa lebih dari satu).")
    selected_years = st.multiselect("Tahun", years, default=years)
    if not selected_years:
        st.warning("Pilih minimal 1 tahun.")
        st.stop()

    topn = st.slider("Top brand (ranking)", 5, min(30, len(brands_all)), min(10, len(brands_all)))

    metric = st.selectbox(
        "Metrik utama",
        ["Retail (Units)", "Market Share (%)", "YoY Growth (%)", "YoY Change (Units)"],
        index=0,
        help=(
            "Retail (Units): total unit terjual.\n"
            "Market Share: persentase kontribusi merek di tahun itu.\n"
            "YoY Growth: % perubahan vs tahun sebelumnya.\n"
            "YoY Change: selisih unit vs tahun sebelumnya."
        )
    )

    st.caption("2️⃣ Pilih cara memilih merek: otomatis atau pilih manual.")
    brand_mode = st.radio("Brand filter", ["Top (per tahun)", "Manual pilih brand"], index=0)
    manual_brands = []
    if brand_mode == "Manual pilih brand":
        manual_brands = st.multiselect("Pilih brand", brands_all, default=brands_all[: min(10, len(brands_all))])

    st.divider()
    kpi_year = st.selectbox(
        "KPI Year (fokus analisis)",
        selected_years,
        index=len(selected_years) - 1,
        help="Tahun fokus untuk treemap market share, dan highlight utama."
    )


# Filter data

df_f = df[df["Year"].isin(selected_years)].copy()

if brand_mode == "Top (per tahun)":
    top_brands = (
        df_f.groupby("Year", group_keys=False)
            .apply(lambda x: x.nlargest(topn, "Retail"))["Brand"]
            .unique()
            .tolist()
    )
    df_f = df_f[df_f["Brand"].isin(top_brands)]
else:
    if manual_brands:
        df_f = df_f[df_f["Brand"].isin(manual_brands)]


# Derived metrics: Share + YoY

total_by_year = df_f.groupby("Year", as_index=False)["Retail"].sum().rename(columns={"Retail": "TotalYear"})
df_f = df_f.merge(total_by_year, on="Year", how="left")
df_f["Share"] = np.where(df_f["TotalYear"] > 0, (df_f["Retail"] / df_f["TotalYear"]) * 100, np.nan)

df_f["YoY_Change"] = np.nan
df_f["YoY_Growth"] = np.nan

if len(years) >= 2:
    pivot_all = df.pivot_table(index="Brand", columns="Year", values="Retail", aggfunc="sum")
    for y in years[1:]:
        prev = y - 1
        if prev in pivot_all.columns and y in pivot_all.columns:
            change = pivot_all[y] - pivot_all[prev]
            growth = (change / pivot_all[prev]) * 100
            mask = df_f["Year"].eq(y)
            df_f.loc[mask, "YoY_Change"] = df_f.loc[mask, "Brand"].map(change)
            df_f.loc[mask, "YoY_Growth"] = df_f.loc[mask, "Brand"].map(growth)

if metric == "Retail (Units)":
    df_f["Value"] = df_f["Retail"]
    value_label = "Units"
elif metric == "Market Share (%)":
    df_f["Value"] = df_f["Share"]
    value_label = "Share (%)"
elif metric == "YoY Growth (%)":
    df_f["Value"] = df_f["YoY_Growth"]
    value_label = "YoY Growth (%)"
else:
    df_f["Value"] = df_f["YoY_Change"]
    value_label = "YoY Change (Units)"

years_label = ", ".join(map(str, sorted(selected_years)))
years_range = f"{min(selected_years)}–{max(selected_years)}" if len(selected_years) > 1 else str(selected_years[0])


# KPI row + Insight
st.markdown("### Ringkasan pasar (KPI)")


market_by_year = df.groupby("Year")["Retail"].sum().sort_index()

total_kpi = market_by_year.get(kpi_year, np.nan)
prev_year = kpi_year - 1
total_prev = market_by_year.get(prev_year, np.nan)

market_change = total_kpi - total_prev if pd.notna(total_kpi) and pd.notna(total_prev) else np.nan
market_growth = (market_change / total_prev * 100) if pd.notna(market_change) and pd.notna(total_prev) and total_prev != 0 else np.nan

tmp_year = df_f[df_f["Year"].eq(kpi_year)].sort_values("Retail", ascending=False)

top_brand = tmp_year.iloc[0]["Brand"] if len(tmp_year) else "-"
top_units = tmp_year.iloc[0]["Retail"] if len(tmp_year) else np.nan
top_share = tmp_year.iloc[0]["Share"] if len(tmp_year) else np.nan

top_yoy_units = tmp_year.iloc[0]["YoY_Change"] if len(tmp_year) else np.nan
top_yoy_pct = tmp_year.iloc[0]["YoY_Growth"] if len(tmp_year) else np.nan

top3_share = tmp_year.head(3)["Share"].sum() if len(tmp_year) >= 3 else np.nan

k1, k2, k3, k4, k5 = st.columns([1, 1.3, 1.4, 1.4, 1.8])

k1.metric("Brands (filtered)", f"{df_f['Brand'].nunique():,}")
k2.metric("Years (selected)", years_range)

k3.metric(
    f"Total Market {kpi_year}",
    _fmt_int(total_kpi),
    delta=(f"{_fmt_int(market_change)} ({_fmt_pct(market_growth)})" if pd.notna(market_growth) else None),
)

k4.metric(
    f"Top Brand {kpi_year}",
    top_brand,
    delta=(f"{_fmt_int(top_units)} units • Share {_fmt_pct(top_share)}" if top_brand != "-" else None),
)

k5.metric(
    "Top-3 Market Share",
    _fmt_pct(top3_share) if pd.notna(top3_share) else "-"
)

detail_lines = []
if len(tmp_year) >= 3:
    detail_lines.append(f"**Top-3 brands {kpi_year}:** {', '.join(tmp_year.head(3)['Brand'].tolist())}")
if pd.notna(top_yoy_units) and pd.notna(top_yoy_pct):
    detail_lines.append(f"**Top brand YoY:** {_fmt_int(top_yoy_units)} units ({_fmt_pct(top_yoy_pct)})")

if detail_lines:
    st.markdown("\n\n".join(detail_lines))

# ===== Insight summary text =====
st.markdown("### Insight")

top3_names = []
if len(tmp_year) >= 3:
    top3_names = tmp_year.head(3)["Brand"].tolist()
elif len(tmp_year) > 0:
    top3_names = tmp_year["Brand"].tolist()

if pd.notna(total_kpi):
    summary = (
        f"Pada {kpi_year}, total pasar mobil ritel mencapai {_fmt_int(total_kpi)} unit "
        f"dengan perubahan {_fmt_int(market_change)} unit "
        f"({_fmt_pct(market_growth)}) dibanding {prev_year}."
    )
else:
    summary = f"Data pasar untuk {kpi_year} tidak tersedia di filter saat ini."

if len(tmp_year) >= 1:
    summary += (
        f" Brand dengan penjualan tertinggi adalah **{top_brand}** "
        f"dengan {_fmt_int(top_units)} unit dan market share {_fmt_pct(top_share)}."
    )

if pd.notna(top3_share) and top3_names:
    brand_list = ", ".join(top3_names)
    summary += (
        f" Tiga merek teratas ({brand_list}) menguasai "
        f"{_fmt_pct(top3_share)} dari pasar, "
        "menunjukkan bahwa persaingan utama terkonsentrasi pada sedikit pemain besar."
    )

st.write(summary)




MIN_BASE_UNITS = 1000
prev_df = df.pivot_table(index="Brand", columns="Year", values="Retail", aggfunc="sum")
eligible = None
if prev_year in prev_df.columns and kpi_year in prev_df.columns:
    base = prev_df[prev_year]
    curr = prev_df[kpi_year]
    yoy_growth = (curr - base) / base * 100
    yoy_change = (curr - base)
    eligible = pd.DataFrame({
        "Brand": yoy_growth.index,
        "YoY_Growth": yoy_growth.values,
        "YoY_Change": yoy_change.values,
        "Base": base.values
    }).dropna()
    eligible = eligible[(eligible["Base"] >= MIN_BASE_UNITS)].sort_values("YoY_Growth", ascending=False)


st.divider()


# Highlights

st.subheader("🔎 Highlights")

h1, h2, h3 = st.columns(3)

h1.info(
    f"**Top (filtered) {kpi_year}:** "
    + (f"{top_brand} — {_fmt_int(top_units)} units" if top_brand else "-")
)

if len(tmp_year) >= 3:
    top3_share_curr = tmp_year.head(3)["Share"].sum()
    top3_brands = ", ".join(tmp_year.head(3)["Brand"].tolist())
    h2.info(f"**Top-3 share {kpi_year}:** {_fmt_pct(top3_share_curr)}\n\n{top3_brands}")
else:
    h2.info(f"**Top-3 share {kpi_year}:** -")

if isinstance(eligible, pd.DataFrame) and len(eligible) > 0:
    fb = eligible.iloc[0]
    h3.info(
        f"**Fastest YoY Growth {kpi_year}:** {fb['Brand']}\n\n"
        f"+{_fmt_int(fb['YoY_Change'])} units • {_fmt_pct(fb['YoY_Growth'])} (base {_fmt_int(fb['Base'])})"
    )
else:
    top_yoy = tmp_year.iloc[0]["YoY_Growth"] if len(tmp_year) else np.nan
    top_yoy_units = tmp_year.iloc[0]["YoY_Change"] if len(tmp_year) else np.nan
    h3.info(
        f"**YoY change {kpi_year} (Top brand):**\n\n"
        + (f"{top_brand} — {_fmt_int(top_yoy_units)} units • {_fmt_pct(top_yoy)}" if top_brand and pd.notna(top_yoy) else "-")
    )

st.caption(
    "Highlights merangkum siapa pemimpin pasar, seberapa terkonsentrasi pasar, "
    "dan merek mana yang tumbuh paling cepat di tahun fokus."
)


# Tabs / Charts

tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Trends & Change", "🧾 Data & Export"])

#Tab 1 Ranking + Treemap
with tab1:
    c1, c2 = st.columns([1.4, 1])

    with c1:
        st.markdown("### Ranking (per tahun)")
        st.caption(
            "Grafik ini menunjukkan posisi relatif setiap merek dalam tahun yang dipilih. "
            "Bandingkan panjang bar untuk melihat siapa yang naik atau turun ketika mengubah filter tahun."
        )

        bar_df = df_f.copy()
        bar_df["YearStr"] = bar_df["Year"].astype(int).astype(str)
        bar_df = bar_df.sort_values(["YearStr", "Value"], ascending=[True, False])

        fig_rank = px.bar(
            bar_df,
            x="Value",
            y="Brand",
            color="YearStr",
            orientation="h",
            hover_data={"Retail":":,.0f", "Share":":.2f", "YoY_Change":":,.0f", "YoY_Growth":":.2f"},
            labels={"Value": value_label, "YearStr": "Year"},
            title=f"Brand ranking by {metric}"
        )
        fig_rank.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_rank, use_container_width=True)

    with c2:
        st.markdown("### Market share (Treemap)")
        st.caption(
            "Setiap kotak merepresentasikan market share pasar satu merek di tahun KPI. "
            "Kotak lebih besar berarti market share pasar lebih besar; cocok untuk melihat dominasi beberapa merek besar."
        )

        tre = df[df["Year"].eq(kpi_year)].copy()
        tre["Share"] = tre["Retail"] / tre["Retail"].sum() * 100
        tre = tre.sort_values("Retail", ascending=False).head(max(12, topn))

        fig_tree = px.treemap(
            tre,
            path=["Brand"],
            values="Retail",
            hover_data={"Share":":.2f", "Retail":":,.0f"},
            title=f"Top brands market share – {kpi_year}"
        )
        st.plotly_chart(fig_tree, use_container_width=True)

#Tab 2  Line + Heatmap
with tab2:
    st.markdown("### Trend (line) untuk brand terpilih")
    st.caption(
        "Garis menunjukkan perkembangan penjualan dari tahun ke tahun untuk beberapa merek terbesar. "
        "Cari pola naik terus, turun, atau berfluktuasi tajam."
    )

    cA, cB = st.columns([2, 1])
    with cA:
        topn_line = st.slider("Top brand (line chart)", 3, min(15, df_f["Brand"].nunique()), 8, key="topn_line")
    with cB:
        use_log = st.checkbox("Log scale (opsional)", value=False)

    top_brands_line = (
        df_f.groupby("Brand")["Retail"]
            .sum()
            .sort_values(ascending=False)
            .head(topn_line)
            .index
            .tolist()
    )

    line_df = df_f[df_f["Brand"].isin(top_brands_line)].copy()
    line_df["YearStr"] = line_df["Year"].astype(int).astype(str)

    fig_line = px.line(
        line_df.sort_values("Year"),
        x="YearStr",
        y="Retail",
        color="Brand",
        markers=True,
        hover_data={"Retail":":,.0f", "Share":":.2f"},
        labels={"YearStr": "Year", "Retail": "Retail (Units)"},
        title=f"Trend: Retail (Units) — Top {topn_line} brands"
    )
    fig_line.update_xaxes(type="category")
    if use_log:
        fig_line.update_yaxes(type="log")
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("### Heatmap Brand × Year (Retail Units)")
    st.caption(
        "Baris = merek, kolom = tahun. Warna lebih terang berarti penjualan lebih besar."
    )

    hm = df_f.pivot_table(index="Brand", columns="Year", values="Retail", aggfunc="sum", fill_value=0)
    hm = hm.reindex(sorted(hm.columns), axis=1)
    hm.columns = [str(c) for c in hm.columns]
    hm = hm.loc[hm.sum(axis=1).sort_values(ascending=False).index]

    fig_hm = px.imshow(
        hm,
        aspect="auto",
        text_auto=".0f",
        labels=dict(x="Year", y="Brand", color="Units"),
        title="Heatmap: Retail units"
    )
    fig_hm.update_xaxes(type="category")
    st.plotly_chart(fig_hm, use_container_width=True)

#  Tab 3 Data + Export HTML
with tab3:
    st.markdown("### Data preview (filtered)")
    st.caption(
        "Tabel ini menampilkan data mentah sesuai kombinasi filter yang sedang aktif. "
        "Gunakan untuk memeriksa angka yang muncul di grafik atau untuk analisis lanjutan di Excel/R."
    )

    st.dataframe(df_f.sort_values(["Year", "Retail"], ascending=[True, False]), use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        st.download_button(
            "⬇️ Download filtered data (CSV)",
            df_f.to_csv(index=False).encode("utf-8"),
            file_name="filtered_car_retail_sales_id.csv",
            mime="text/csv"
        )

    with c2:
        st.markdown("### Export static HTML")
    

        hm_mode = st.selectbox(
            "Heatmap mode (untuk HTML)",
            ["Log scale (lebih kontras)", "Normalized per brand (lihat pola naik/turun)"],
            index=0
        )

        try:
            if metric in ["YoY Growth (%)", "YoY Change (Units)"] and 'yoy_year' in locals():
                exp_rank = df_f[df_f["Year"].eq(yoy_year)].dropna(subset=["Value"]).copy()
                exp_rank = exp_rank.sort_values("Value", ascending=False).head(topn)

                fig_rank_export = px.bar(
                    exp_rank.sort_values("Value"),
                    x="Value", y="Brand", orientation="h",
                    hover_data={"Retail":":,.0f","YoY_Change":":,.0f","YoY_Growth":":.2f"},
                    labels={"Value": value_label},
                    title=f"Ranking — {metric} ({yoy_year} vs {yoy_year-1})"
                )
                fig_rank_export.update_yaxes(categoryorder="total ascending")
                fig_rank_export.update_layout(height=520, margin=dict(l=170, r=40, t=70, b=50))
            else:
                exp_rank = df_f.copy()
                exp_rank["YearStr"] = exp_rank["Year"].astype(int).astype(str)

                fig_rank_export = px.bar(
                    exp_rank.sort_values(["YearStr","Value"], ascending=[True, False]),
                    x="Value", y="Brand", color="YearStr", orientation="h",
                    hover_data={"Retail":":,.0f","Share":":.2f","YoY_Change":":,.0f","YoY_Growth":":.2f"},
                    labels={"Value": value_label, "YearStr":"Year"},
                    title=f"Ranking — {metric}"
                )
                fig_rank_export.update_yaxes(categoryorder="total ascending")
                fig_rank_export.update_layout(height=560, margin=dict(l=170, r=40, t=70, b=50))

            tre = df[df["Year"].eq(kpi_year)].copy()
            tre["Share"] = tre["Retail"] / tre["Retail"].sum() * 100
            tre = tre.sort_values("Retail", ascending=False).head(max(12, topn))

            fig_tree_export = px.treemap(
                tre, path=["Brand"], values="Retail",
                hover_data={"Share":":.2f","Retail":":,.0f"},
                title=f"Market share treemap — {kpi_year}"
            )
            fig_tree_export.update_layout(height=520, margin=dict(l=20, r=20, t=70, b=20))

            topn_line_export = 8
            top_brands_line = (
                df_f.groupby("Brand")["Retail"].sum()
                    .sort_values(ascending=False).head(topn_line_export).index.tolist()
            )

            line_df = df_f[df_f["Brand"].isin(top_brands_line)].copy()
            line_df["YearStr"] = line_df["Year"].astype(int).astype(str)

            fig_line_export = px.line(
                line_df.sort_values("Year"),
                x="YearStr", y="Retail", color="Brand", markers=True,
                hover_data={"Retail":":,.0f","Share":":.2f"},
                labels={"YearStr":"Year","Retail":"Units"},
                title=f"Trend: Retail (Units) — Top {topn_line_export} brands"
            )
            fig_line_export.update_xaxes(type="category")
            fig_line_export.update_layout(height=520, margin=dict(l=60, r=30, t=70, b=55))

            hm = df_f.pivot_table(index="Brand", columns="Year", values="Retail", aggfunc="sum", fill_value=0)
            hm = hm.reindex(sorted(hm.columns), axis=1)
            hm = hm.loc[hm.sum(axis=1).sort_values(ascending=False).index]
            hm.columns = [str(c) for c in hm.columns]

            if hm_mode.startswith("Log"):
                hm_display = np.log1p(hm)
                hm_title = "Heatmap: Retail units (log scale)"
                hm_color = "log(1+units)"
                hm_text = False
            else:
                denom = hm.max(axis=1).replace(0, np.nan)
                hm_display = (hm.div(denom, axis=0)).fillna(0)
                hm_display = hm_display ** 0.5
                hm_title = "Heatmap: Normalized per brand (0–1) — contrast enhanced"
                hm_color = "Normalized (gamma)"
                hm_text = False

            fig_hm_export = px.imshow(
                hm_display,
                aspect="auto",
                text_auto=hm_text,
                color_continuous_scale="Viridis",
                labels=dict(x="Year", y="Brand", color=hm_color),
                title=hm_title
            )
            fig_hm_export.update_xaxes(type="category")
            fig_hm_export.update_layout(height=620, margin=dict(l=190, r=50, t=70, b=55))

            for fig in [fig_rank_export, fig_tree_export, fig_line_export, fig_hm_export]:
                fig.update_layout(
                    template="plotly_white",
                    font=dict(size=14),
                    title=dict(x=0.02),
                )

            html_parts = [
                pio.to_html(fig_rank_export, full_html=False, include_plotlyjs="cdn"),
                pio.to_html(fig_tree_export, full_html=False, include_plotlyjs=False),
                pio.to_html(fig_line_export, full_html=False, include_plotlyjs=False),
                pio.to_html(fig_hm_export, full_html=False, include_plotlyjs=False),
            ]

            html_doc = f"""
            <html>
            <head>
            <meta charset="utf-8">
            <title>Indonesia Car Retail Sales (Static)</title>
            <style>
                body {{
                font-family: Arial, sans-serif;
                margin: 24px;
                max-width: 1100px;
                }}
                h1 {{
                margin: 0 0 6px 0;
                font-size: 26px;
                }}
                .subtitle {{
                color: #444;
                margin-bottom: 18px;
                line-height: 1.4;
                }}
                .meta {{
                color: #666;
                font-size: 13px;
                margin-bottom: 12px;
                }}
                .card {{
                border: 1px solid #e6e6e6;
                border-radius: 12px;
                padding: 14px 14px 6px 14px;
                margin: 14px 0;
                box-shadow: 0 1px 6px rgba(0,0,0,0.06);
                background: white;
                }}
            </style>
            </head>
            <body>
            <h1>Indonesia Car Retail Sales (2020–2022)</h1>
            <div class="subtitle">
                Static HTML export dari dashboard Streamlit. Grafik tetap interaktif (zoom/pan + tooltip) berkat Plotly.
            </div>
            <div class="meta">
                KPI Year: <b>{kpi_year}</b> • Selected years: <b>{", ".join([str(y) for y in selected_years])}</b> • Metric: <b>{metric}</b> • Heatmap mode: <b>{hm_mode}</b>
            </div>

            <div class="card">{html_parts[0]}</div>
            <div class="card">{html_parts[1]}</div>
            <div class="card">{html_parts[2]}</div>
            <div class="card">{html_parts[3]}</div>
            </body>
            </html>
            """

            st.download_button(
                "⬇️ Download dashboard.html (improved)",
                html_doc.encode("utf-8"),
                file_name="dashboard.html",
                mime="text/html"
            )

        except Exception as e:
            st.error(f"Gagal export HTML: {e}")
