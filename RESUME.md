# G2G-bot — Resume Point (2026-04-24)

File ini adalah checkpoint manual supaya Anda (dan Claude) bisa lanjut besok tanpa kehilangan konteks.

## Apa Tujuan Proyek Ini

Scanner otomatis untuk cari game Roblox yang:
1. **Populer** (banyak pemain aktif)
2. **Tradable** (item/akun bisa diperjualbelikan)
3. **Menguntungkan** di-resell dari Itemku (IDR) ke G2G (USD)

Output: Google Sheet dengan shortlist game kandidat, auto-update tiap jam.

## Stack Final (Semua Gratis)

- **Bahasa:** Python
- **Scheduler:** GitHub Actions cron (hourly)
- **Storage & Output:** Google Sheets
- **Sumber data:**
  - Roblox official API (popular games + CCU)
  - Rolimons (cross-reference tradability)
  - G2G (scraping listing + sold count)
  - Itemku (scraping harga IDR)

## Struktur Google Sheet

3 tab:
- **`Latest`** — snapshot terbaru (overwrite tiap scan)
- **`History`** — log append-only untuk trend analysis
- **`Watchlist`** — manual, game favorit Anda

## Kolom Prioritas (MVP)

Wajib ada lebih dulu:
- Game Name
- CCU (concurrent players)
- Tradable (Yes/No + tipe)
- G2G Sold Count 30d

Kolom lain yang akan ditambah setelah MVP:
- Thumbnail URL, G2G Avg Price (USD), Itemku Avg Price (IDR), Margin %,
- G2G Seller Count, Score, CCU Trend 7d, Link ke G2G, Link ke Itemku

## Progress Saat Ini

| # | Task | Status |
|---|---|---|
| 1 | Setup Google Sheets + Service Account | 🔵 In Progress (menunggu Anda) |
| 2 | Scaffold project structure | ⏳ Pending |
| 3 | Build Roblox collector | ⏳ Pending |
| 4 | Build tradability classifier | ⏳ Pending |
| 5 | Build G2G matcher + sold-count scraper | ⏳ Pending |
| 6 | Build Itemku price fetcher | ⏳ Pending |
| 7 | Build Google Sheets writer | ⏳ Pending |
| 8 | Setup GitHub Actions cron | ⏳ Pending |

## Yang Harus Anda Selesaikan Besok (Sebelum Coding Mulai)

Selesaikan 6 step setup ini dulu:

1. ☐ Buat Google Sheet bernama `G2G Roblox Scanner`
2. ☐ Buat Google Cloud project `g2g-roblox-bot`
3. ☐ Enable **Google Sheets API** + **Google Drive API**
4. ☐ Buat Service Account `g2g-bot-writer`
5. ☐ Download JSON key → simpan ke `D:\Project\G2G-bot\credentials\service_account.json`
6. ☐ Share Sheet ke email service account dengan akses **Editor**

## Besok, Kasih Info Ini ke Claude

```
1. Konfirmasi 6 step setup sudah selesai
2. Spreadsheet ID: [paste ID dari URL sheet Anda]
3. Konfirmasi file service_account.json sudah ada di D:\Project\G2G-bot\credentials\
```

Claude akan baca file memory + RESUME.md ini, lalu langsung mulai scaffolding proyek tanpa diskusi ulang.

## Catatan Penting

- **JANGAN commit** `credentials/service_account.json` ke GitHub. File itu seperti password.
- Kalau Anda ingin lihat detail panduan setup step-by-step yang sudah diberikan, cek chat sebelumnya atau minta Claude besok: "tolong tampilkan ulang panduan setup Google Sheets dari memory".
