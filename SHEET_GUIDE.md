# Panduan Membaca Google Sheet G2G-bot

Dokumen ini menjelaskan **setiap kolom** dan **konsep** yang muncul di Sheet, beserta **sumber datanya**. Cocok di-copy ke tab terpisah di Sheet sebagai dokumentasi.

---

## Apa yang Bot Ini Lakukan

Setiap jam, bot otomatis:
1. Ambil daftar **game Roblox populer** dari Roblox API
2. Scrape **semua offer item Roblox** di G2G (USD)
3. Scrape **harga item per game** di Itemku (IDR)
4. Hitung **margin per game** (potensi profit) dan **score** (composite ranking)
5. **Cocokkan item per item** antara Itemku (beli) dan G2G (jual) — surface item dengan margin tinggi spesifik (mis. "Disco Bee" 15rb -> 30rb)
6. Tulis hasil ke tab `Latest` (overwrite per-game), `History` (append snapshot per-game), dan `Items` (overwrite per-item)

Tujuan: **menemukan game Roblox yang itemnya menguntungkan untuk di-resell** dari Itemku ke G2G.

---

## Sumber Data

| Sumber | URL | Yang Diambil |
|---|---|---|
| **Roblox Explore API** | `apis.roblox.com/explore-api/v1/get-sorts` | Daftar game populer + jumlah pemain (CCU) |
| **G2G Marketplace** | `sls.g2g.com/offer/search?seo_term=rbl-item` | Listing item Roblox yang dijual di pasar internasional (USD) |
| **Itemku Marketplace** | `itemku.com/g/<slug>/<kategori-item>` | Listing item per game di pasar Indonesia (IDR) |
| **Kurs USD/IDR** | `open.er-api.com/v6/latest/USD` | Kurs live untuk konversi margin |

Semua sumber **gratis, tanpa API key**.

---

## Tab `Latest` — Snapshot Terbaru

Berisi data **scan paling baru saja**. Di-overwrite tiap jam. Sorted by **Score desc**, fallback **CCU desc** (yang paling potensial di atas).

| Kolom | Arti | Sumber |
|---|---|---|
| **Game Name** | Nama canonical game (mis. "Blox Fruits") | Manual di `data/game_aliases.json` |
| **CCU** | Concurrent Users — jumlah pemain yang sedang online di game ini saat scan dilakukan | Roblox Explore API |
| **Tradable** | `Yes` jika game punya minimal 1 offer item di G2G; `No` jika tidak ada item-nya di pasar | Derived dari G2G |
| **G2G Sold Count 30d** | **(placeholder)** Total order lifetime per game di G2G. Akan jadi delta 30 hari setelah History tab terkumpul 30+ hari | G2G `total_success_order` field |
| **Icon** | (placeholder, future enhancement) | — |
| **G2G Avg Price (USD)** | Rata-rata harga item Roblox game ini di G2G dalam USD | G2G `unit_price_in_usd` |
| **Itemku Avg Price (IDR)** | Rata-rata harga item Roblox game ini di Itemku dalam Rupiah | Itemku `price` field |
| **Margin %** | Potensi profit jika beli di Itemku, jual di G2G. Formula: `(G2G median USD - Itemku median IDR / kurs) / cost × 100`. Pakai **median** (bukan avg) supaya tidak terdistorsi item premium/whale | Hitungan internal |
| **G2G Sellers** | Jumlah seller unik yang menjual item game ini di G2G. Tinggi = pasar likuid, kompetitif. Rendah = niche, peluang lebih tinggi tapi risiko slow-move | G2G `seller_id` distinct count |
| **Score** | Composite ranking. Formula: `margin% × log(lifetime_orders) × log(ccu) / 100`. Kombinasi profit × velocity penjualan × demand pemain. Score tinggi = kandidat kuat | Hitungan internal |
| **Trend 7d** | (placeholder, future — akan menghitung perubahan CCU/harga 7 hari) | — |
| **Roblox Link** | Direct link ke halaman game di roblox.com | Roblox `place_id` |
| **G2G Link** | Link ke kategori item Roblox di G2G | Static |
| **Itemku Link** | Link ke kategori item pertama game ini di Itemku | Itemku slug discovery |
| **Last Updated WIB** | Timestamp scan dalam zona Asia/Jakarta (UTC+7) | Server clock saat scan |

---

## Tab `History` — Log Append-Only

Setiap scan menambah snapshot baris baru. **Tidak di-overwrite**. Pakai untuk:
- Trend analysis (Margin & CCU dari waktu ke waktu)
- Hitung Sold Count 30d (delta lifetime orders dari 30 hari lalu)
- Audit konsistensi data antar scan

| Kolom | Arti |
|---|---|
| **Snapshot WIB** | Waktu snapshot diambil (UTC+7) |
| **Game Name** | Sama seperti di Latest |
| **CCU** | Sama seperti di Latest, tapi snapshot historis |
| **Tradable** | Sama seperti di Latest |
| **G2G Sold Count 30d** | Sama seperti di Latest (lifetime orders) |
| **G2G Avg Price (USD)** | Sama seperti di Latest |
| **Itemku Avg Price (IDR)** | Sama seperti di Latest |
| **Margin %** | Sama seperti di Latest |
| **Score** | Sama seperti di Latest |

---

## Tab `Items` — Per-Item Arbitrage Opportunities

Berisi **per-listing match** antara item di Itemku (sumber beli, IDR) dan offer
di G2G (target jual, USD). Inilah tab utama buat **menemukan item dengan
margin tinggi** seperti contoh "Disco Bee 15rb di Itemku vs 30rb di G2G".

Di-overwrite tiap scan. Sorted by **Margin % desc**, max 1000 baris.

### Cara Bot Mencocokkan Item

Untuk setiap canonical game:
1. Ambil semua produk Itemku game itu (nama + harga IDR).
2. Ambil semua offer G2G game itu (title + harga USD).
3. Untuk tiap pasangan, normalisasi nama: lowercase, buang `[tag]`, `(paren)`,
   marketplace fluff (`buy`, `fast`, `roblox`, `murah`, ...), dan token nama
   game-nya sendiri (`bee`, `swarm`, `simulator`).
4. Hitung **Jaccard similarity** antar token yang tersisa. Match jika
   ≥ 0.40 dan minimal 1 token sama.
5. Kalau Itemku item match ke beberapa G2G offer, ambil **median**, **min**,
   dan jumlah offer-nya.

Threshold dipilih supaya "Disco Bee" cocok ke "Disco Bee Adult" tapi TIDAK
cocok ke "Tadpole Bee". Kode di `src/matcher.py`.

### Kolom

| Kolom | Arti | Sumber |
|---|---|---|
| **Game Name** | Canonical game (mis. "Bee Swarm Simulator") | `data/game_aliases.json` |
| **Item Name (Itemku)** | Nama listing dari Itemku, dipotong 120 char | Itemku product `name` |
| **Itemku Price (IDR)** | Harga listing Itemku — ini **harga beli** kamu | Itemku `price` |
| **G2G Min (USD)** | Harga **termurah** dari semua offer G2G yang match item ini | G2G `unit_price_in_usd` (min) |
| **G2G Median (USD)** | Harga **realistis** untuk dijual (median, robust ke outlier) | G2G median |
| **G2G Median (IDR equiv)** | G2G median × kurs USD/IDR — apel-vs-apel dengan kolom Itemku Price | Hitungan internal |
| **Margin %** | `(G2G median IDR - Itemku IDR) / Itemku IDR × 100`. Belum potong fee G2G! | Hitungan internal |
| **Profit per Unit (IDR)** | `G2G median IDR - Itemku IDR`. Estimasi profit kotor per item terjual | Hitungan internal |
| **Itemku Order Count** | Berapa kali listing ini sudah laku di Itemku — proxy untuk demand di pasar lokal | Itemku `order_count` |
| **G2G Match Count** | Berapa offer G2G yang match item ini. >1 = pasar likuid | Jumlah match |
| **Match Confidence** | Jaccard similarity 0..1. ≥ 0.6 = pasti benar; 0.4-0.6 = sanity check dulu | Hitungan internal |
| **G2G Sample Title** | Title G2G dengan match score tertinggi — buat verify mata | G2G `title` |
| **Itemku Link** | Link ke kategori Itemku game ini (klik & cari nama item secara manual) | Itemku slug |
| **G2G Link** | Link ke kategori item Roblox di G2G | Static |
| **Last Updated WIB** | Timestamp scan | Server clock |

### Cara Pakai (Strategi)

1. **Sort by Margin %** — sudah default, tinggi dulu di atas.
2. **Filter Confidence ≥ 0.5** — buang match yang ragu-ragu.
3. **Filter G2G Match Count ≥ 2** — minimum 2 offer berarti harga itu bukan outlier solo seller.
4. **Filter Itemku Order Count ≥ 3** — listing yang pernah laku, bukan barang mati.
5. Buka `Itemku Link` & `G2G Link` di browser, cari nama item, **bandingkan harga aktual** sebelum eksekusi.
6. **Margin > 300%** suspicious — kemungkinan apple-vs-orange (item tier rendah Itemku match ke item tier tinggi G2G).
7. Ingat **fee G2G ~10-15%** dari sell price, kurangi mental dari Margin.

### Contoh Pembacaan

```
Game: Bee Swarm Simulator | Item: Disco Bee | Itemku 15.000 | G2G Med 1.82 USD (≈30.000 IDR) | Margin 100% | Profit 15.000 | Confidence 0.87 | Matches 5
```
Artinya: 5 listing G2G match nama "Disco Bee" dengan confidence 0.87 (kuat),
median harganya $1.82 ≈ Rp 30rb. Beli di Itemku 15rb, jual G2G 30rb, kotor 15rb (sebelum fee).

---

## Tab `Watchlist` — Manual User

Tab ini **TIDAK ditulis bot**. Anda isi sendiri game favorit / kandidat untuk dipantau.

| Kolom | Arti |
|---|---|
| **Game Name** | Nama game yang ingin dimonitor |
| **Notes** | Catatan personal Anda |
| **Target Buy Price (IDR)** | Harga beli target dari Itemku |
| **Target Sell Price (USD)** | Harga jual target di G2G |
| **Active** | `Yes`/`No` — flag manual buat track status |

---

## Cara Baca & Strategi

### Skema Quick-Scan
1. Sort tab `Latest` by **Score desc**
2. Top 5-10 baris = kandidat utama
3. Filter `Tradable = Yes` (otomatis sudah, karena bot filter game tanpa item G2G)
4. Lihat **G2G Sellers**:
   - Sellers tinggi (>15) = pasar matang, margin tipis tapi cepat laku
   - Sellers rendah (<5) = peluang besar tapi cek dulu apakah memang demand ada

### Sanity Check Sebelum Eksekusi
- **Klik Roblox Link** → cek game memang aktif & trending
- **Klik G2G Link** → bandingkan harga listing vs Avg Price; cek item-item spesifik yang laku
- **Klik Itemku Link** → cek availability di local market & harga aktual
- **Margin >500%** = SUSPICIOUS, kemungkinan apple-vs-orange (item basic vs premium); jangan langsung percaya

### Trend (via History tab)
- Filter History per game, plot Margin % over time → cari yang stabil tinggi
- Plot Sold Count Lifetime → naik konsisten = demand growing
- Drop tiba-tiba di CCU = game lagi turun, hindari masuk

---

## Glossary Istilah

| Istilah | Arti |
|---|---|
| **CCU** | **Concurrent Users**. Jumlah pemain yang **sedang online bersamaan** di sebuah game saat data diambil. Indikator demand realtime — game dengan CCU tinggi = banyak pembeli potensial untuk item-nya. Sumber: Roblox API. |
| **Snapshot** | Foto data pada satu waktu tertentu. Tab `History` adalah kumpulan snapshot dari semua scan, sehingga bisa di-trace perubahannya per jam/hari. |
| **Margin %** | Persentase potensi profit dari arbitrase (beli di Itemku, jual di G2G). Bukan profit pasti — belum dipotong fee G2G (~10-15%), fee transfer pembayaran, dan effort time. |
| **Score** | Ranking gabungan (composite). Tinggi = kombinasi margin bagus + sales velocity tinggi + demand pemain banyak. Pakai untuk shortlist top kandidat. |
| **Lifetime Orders** | Total order yang pernah terjadi sepanjang umur listing G2G — bukan 30 hari terakhir. Sebatas indikator popularitas historis. |
| **Tradable** | Bot menganggap game "tradable" jika punya minimal 1 listing item aktif di G2G. Bukan judgment apakah item-nya legal/safe ditrade — itu tetap tanggung jawab seller. |
| **WIB** | **Waktu Indonesia Barat** = UTC+7 (Asia/Jakarta). Indonesia tidak ada Daylight Saving Time, jadi offset selalu +7 sepanjang tahun. |
| **G2G** | Marketplace internasional (HQ Singapore) untuk gaming items, accounts, currency. Mata uang display: USD. URL: g2g.com |
| **Itemku** | Marketplace gaming Indonesia (HQ Jakarta). Mata uang: IDR. URL: itemku.com |
| **Slug** | Bagian URL yang merepresentasikan suatu entity (mis. `blox-fruits-roblox` adalah slug Itemku untuk Blox Fruits). |
| **Aliases** | Alternative keyword untuk match game di title offer. Disimpan di `data/game_aliases.json`. Editable user. |

---

## Catatan & Limitasi

- **Margin = ROUGH SIGNAL**, bukan kepastian profit. Selalu sanity-check manual sebelum spend uang.
- **G2G fee tidak dihitung** dalam Margin — G2G charge ~10-15% per sale, kurangi mental dari Margin.
- **Pagination Itemku terbatas**: bot ambil sample 32 produk pertama per kategori (sampling representatif, bukan seluruh inventory).
- **Sold Count 30d masih lifetime placeholder** sampai History tab terkumpul 30+ hari.
- **Game tanpa item di G2G di-filter out** — bot fokus item, bukan akun. Untuk lihat akun-tradable game, ganti `ROBLOX_SEO_TERM` di `src/collectors/g2g.py` ke `rbl-account`.
- **Scan tiap 1 jam** (menit ke-5 UTC, sama dengan menit ke-5 setiap jam WIB juga). Jangan spam manual run berlebihan — risiko di-rate-limit oleh G2G/Itemku.

---

## Update Terakhir Bot

Bot di-deploy tanggal 25 April 2026, fokus item Roblox (bukan akun) — hasil pivot dari awalnya scan akun karena prioritas user adalah jualan item.

Source code: https://github.com/dennypa77/g2g-scraper
