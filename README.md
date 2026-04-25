# G2G-bot — Roblox Item Arbitrage Scanner

Bot otomatis untuk mencari **game Roblox yang punya item tradable** dan menghitung potensi margin antara **G2G** (USD) dan **Itemku** (IDR). Hasilnya ditulis ke Google Sheet — kandidat di-rank by composite Score (margin × sales velocity × demand).

**Stack**: Python · Google Sheets · GitHub Actions cron · 100% gratis

---

## Apa yang Bot Ini Lakukan

Setiap kali dijalankan:

1. **Roblox** — fetch ~237 game populer + CCU (concurrent users) dari Explore API
2. **G2G** — scrape semua offer di kategori `rbl-item`, agregat per game
3. **Itemku** — discover kategori item per game (fruit, pet, gems, dll), agregat harga IDR
4. **Hitung margin** = `(G2G median USD - Itemku median IDR / kurs) / cost × 100`
5. **Hitung Score** = `margin% × log(lifetime_orders) × log(ccu) / 100`
6. **Tulis** ke tab `Latest` (overwrite) dan `History` (append snapshot)

Game yang tidak punya item di G2G di-filter out (fokus item, bukan akun).

---

## Setup Awal (Sekali Saja)

### 1. Clone repo & install dependencies

```bash
git clone https://github.com/dennypa77/g2g-scraper.git
cd g2g-scraper
pip install -r requirements.txt
```

### 2. Google Cloud + Service Account

1. Buat project di https://console.cloud.google.com (nama bebas, misal `g2g-roblox-bot`)
2. Enable **Google Sheets API** + **Google Drive API**
3. Buat **Service Account** (`IAM & Admin` → `Service Accounts` → `Create`)
4. Buat JSON key untuk service account → download
5. Simpan ke `credentials/service_account.json` (folder ini sudah di-gitignore)

### 3. Google Sheet

1. Buat sheet baru, beri nama bebas (misal `G2G Roblox Scanner`)
2. **Share sheet** ke email service account (xxx@xxx.iam.gserviceaccount.com) dengan akses **Editor**
3. Copy **Spreadsheet ID** dari URL (string panjang antara `/d/` dan `/edit`)

### 4. File `.env`

Buat file `.env` di root project:

```ini
SPREADSHEET_ID=paste_id_dari_url_sheet_anda
SERVICE_ACCOUNT_PATH=credentials/service_account.json
```

### 5. Bootstrap tab Sheet

```bash
python scripts/setup_tabs.py
```

Akan create tab `Latest`, `History`, `Watchlist` dengan header yang benar.

---

## Cara Menjalankan

Ada **3 mode** sesuai kebutuhan:

### Mode 1 — Interactive Menu (Termudah)

```bash
python scripts/menu.py
```

Pilih dari menu:
- `1` — Full scan (paling sering dipakai)
- `2-7` — Test individual collector / connection
- `8` — Cek kurs USD/IDR live

### Mode 2 — Direct Command (Cepat untuk Power User)

```bash
python scripts/run_scan.py
```

Output di terminal akan show progress 5 step (Roblox → G2G → Itemku → Combine → Write). Selesai dalam ~70-90 detik. Cek Google Sheet untuk hasil.

### Mode 3 — GitHub Actions (Auto Cron, Cloud)

Sudah aktif di repo ini. Berjalan **otomatis tiap jam** (menit ke-5 UTC).

**Setup yang sudah dilakukan**:
- Workflow file: `.github/workflows/scan.yml`
- Repo public (Actions free unlimited)
- 2 GitHub Secrets:
  - `g2g` → seluruh isi `service_account.json`
  - `SPREADSHEET_ID` → ID Google Sheet

**Trigger manual**: tab Actions → **Hourly Scan** → **Run workflow** → branch `main` → **Run**.

**Disable cron**: comment out 2 baris `schedule:` dan `- cron:` di `.github/workflows/scan.yml`, push.

---

## Membaca Hasil di Google Sheet

### Tab `Latest` (15 kolom)

| Kolom | Arti |
|---|---|
| Game Name | Canonical name dari `data/game_aliases.json` |
| CCU | Concurrent users di Roblox |
| Tradable | Yes jika ada item offer di G2G |
| G2G Sold Count 30d | Lifetime orders (placeholder; jadi delta 30d setelah History 30+ hari) |
| Icon | (placeholder, future) |
| G2G Avg Price (USD) | Rata-rata harga item di G2G |
| Itemku Avg Price (IDR) | Rata-rata harga item di Itemku |
| Margin % | Potensi profit (median G2G vs median Itemku × kurs) |
| G2G Sellers | Jumlah seller unik di G2G |
| Score | Composite — yang paling tinggi = kandidat terbaik |
| Trend 7d | (placeholder, future) |
| Roblox / G2G / Itemku Link | Direct link |
| Last Updated UTC | Timestamp scan |

Sort otomatis by **Score desc**, fallback **CCU desc**.

### Tab `History` (9 kolom)

Append-only snapshot tiap run. Pakai untuk:
- Trend analysis (Margin vs waktu)
- Hitung sold count 30d (delta dari 30 hari lalu)
- Verifikasi konsistensi data

### Tab `Watchlist`

Manual — Anda isi sendiri game favorit. Tidak ditulis bot.

---

## Customization

### Tambah / edit game yang di-scan

Edit `data/game_aliases.json`:

```json
{
  "Nama Canonical Game": ["keyword1", "keyword2", "alias3"]
}
```

- Key = nama yang muncul di Sheet
- Value = list keyword (lowercase) untuk match di G2G title
- Tambah keyword spesifik item (misal `huge cat` untuk Pet Sim X) untuk improve match rate

### Override slug Itemku

Kalau matching otomatis gagal, edit `data/itemku_overrides.json`:

```json
{
  "Nama Canonical Game": "itemku-slug-asli"
}
```

Cek slug benar dengan buka URL `https://www.itemku.com/g/<slug>`.

### Ganti fokus dari item kembali ke akun

Edit `src/collectors/g2g.py`:

```python
ROBLOX_SEO_TERM = "rbl-account"   # ganti dari "rbl-item"
```

Dan pertimbangkan revert filter di `scripts/run_scan.py` agar terima semua signal lagi.

### Set kurs USD/IDR manual (untuk test)

Set environment variable `USD_IDR_RATE=16500` sebelum run, akan override fetch live.

---

## Troubleshooting

### `KeyError: 'SPREADSHEET_ID'`
File `.env` tidak ada / belum di-load. Pastikan ada di root project, dan `python-dotenv` ke-install (`pip install python-dotenv`).

### `gspread.exceptions.APIError: PERMISSION_DENIED`
Sheet belum di-share ke email service account, atau permission cuma Viewer. Set ke **Editor**.

### `gspread.WorksheetNotFound`
Tab belum dibuat. Run `python scripts/setup_tabs.py`.

### GitHub Actions error "account is locked"
Akun GitHub kena billing lock. Buka https://github.com/settings/billing, resolve. Atau bikin akun baru.

### Workflow run sukses tapi Sheet kosong
Cek log step `Run scan`. Kalau output `0 rows ready`, mungkin G2G API berubah atau filter terlalu ketat. Coba `python scripts/test_g2g.py` lokal.

### Itemku match rate rendah
Edit `data/itemku_overrides.json` untuk game yang slug-nya beda dari pattern `<game>-roblox`. Atau tambah varian di `_normalize_name` jika nama Indo vs Inggris beda jauh.

---

## Struktur Project

```
g2g-scraper/
├── .github/workflows/scan.yml    # GitHub Actions cron
├── credentials/                   # service_account.json (gitignored)
├── data/
│   ├── game_aliases.json         # Keyword aliases per game (G2G title match)
│   └── itemku_overrides.json     # Manual Itemku slug overrides
├── scripts/
│   ├── menu.py                   # Interactive launcher (Mode 1)
│   ├── run_scan.py               # Pipeline entry (Mode 2)
│   ├── setup_tabs.py             # Bootstrap Sheet tabs
│   ├── test_*.py                 # Per-component tests
│   └── verify_state.py           # Inspect current Sheet content
├── src/
│   ├── collectors/
│   │   ├── roblox.py            # Explore API → popular games + CCU
│   │   ├── g2g.py               # rbl-item offer scrape + classify
│   │   └── itemku.py            # Per-game item-category aggregation
│   ├── sheets_client.py          # gspread wrapper
│   └── exchange.py               # USD/IDR rate (live + fallback)
├── .env                           # Local config (gitignored)
├── .env.example                   # Template
└── requirements.txt
```

---

## Catatan Penting

- **JANGAN commit** `credentials/service_account.json` atau `.env` — keduanya sudah di-gitignore.
- **Margin% adalah ROUGH SIGNAL** — selalu sanity-check secara manual sebelum eksekusi resell. Item premium (e.g. Permanent Dragon Fruit) bisa beda harga 10x dari item basic di kategori sama.
- **Sold count 30d** masih placeholder lifetime orders. Butuh History tab terkumpul 30+ hari untuk dapat delta valid.
- **Pagination Itemku** terbatas — cuma sample 32 produk pertama per kategori. Sufficient untuk baseline price, tapi bukan total inventory absolut.
- **Free tier GitHub Actions**: public repo unlimited, private repo 2000 menit/bulan. Repo ini public.

---

## Maintenance

| Task | Frekuensi |
|---|---|
| Update `data/game_aliases.json` saat ada game viral baru | Bulanan |
| Cek log GitHub Actions saat workflow merah | Saat error |
| Refresh service account JSON kalau di-rotate | Tahunan |
| Bersihkan tab `History` kalau > 100k baris | Tahunan |

Selamat berburu arbitrage.
