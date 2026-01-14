# Description
Dashboard menganalisis data penjualan ritel mobil di Indonesia (2020–2022). Menggunakan Streamlit dan Plotly untuk visualisasi tren pasar, pangsa pasar, dan pertumbuhan tahunan.

# Indonesia Car Retail Sales Dashboard (2020–2022)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)

Dashboard analisis data interaktif yang memvisualisasikan performa penjualan ritel mobil di Indonesia dari tahun 2020 hingga 2022. Aplikasi ini membantu pengguna memahami tren pasar, dominasi merek, dan pertumbuhan industri otomotif pasca-pandemi.

## Fitur 

* **KPI Metrics Card**: Menampilkan total penjualan tahunan, pertumbuhan *Year-over-Year* (YoY), dan merek dengan performa terbaik secara instan.
* **Analisis Multi-Dimensi**:
    * **Top 10 Brands**: Bar chart interaktif untuk melihat pemimpin pasar.
    * **Trend Analysis**: Line chart untuk membandingkan performa antar tahun.
    * **Market Heatmap**: Visualisasi intensitas persaingan antar merek.
    * **Market Share**: Pie chart untuk melihat proporsi penguasaan pasar.
* **Mode Fleksibel**: Toggle antara **Absolute Numbers** (Total Unit) dan **Market Share (%)**.
* **Filter Interaktif**: Pilih tahun spesifik untuk perbandingan yang lebih fokus.
* **Export Laporan**: Fitur unik untuk mengunduh dashboard sebagai file **HTML statis** yang tetap interaktif (dapat dibuka tanpa server Python).

## Struktur Data

Aplikasi ini memproses data penjualan ritel tahunan yang tersimpan dalam format CSV:
* `2020_data.csv`
* `2021_data.csv`
* `2022_data.csv`

*Sistem dirancang untuk secara otomatis mendeteksi tahun berdasarkan nama file, sehingga mudah untuk menambahkan data tahun berikutnya (misal: `2023_data.csv`).*

## Cara Menjalankan (Installation)

1.  **Clone repository ini**
    ```bash
    git clone [https://github.com/username-kamu/indonesia-car-sales.git](https://github.com/username-kamu/indonesia-car-sales.git)
    cd indonesia-car-sales
    ```

2.  **Buat Virtual Environment**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Library**
    ```bash
    pip install streamlit pandas plotly numpy
    ```

4.  **Jalankan Aplikasi**
    ```bash
    streamlit run app.py
    ```

## 🛠️ Teknologi yang Digunakan

* **[Streamlit](https://streamlit.io/)**: Framework utama untuk membangun antarmuka web data.
* **[Plotly Express](https://plotly.com/python/)**: Membuat grafik interaktif (zoom, pan, hover).
* **[Pandas](https://pandas.pydata.org/)**: Manipulasi dan pembersihan data (Data Wrangling).
* **Python**: Bahasa pemrograman utama.
