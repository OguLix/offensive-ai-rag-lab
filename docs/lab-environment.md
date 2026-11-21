# Lingkungan lab

Pemilik: C. Diisi dari mesin yang benar-benar dipakai untuk eksperimen final.
Angka yang berasal dari mesin ini dicatat apa adanya; angka yang belum diukur
dibiarkan sebagai TODO.

## 1. Topologi

Semua komponen berjalan di satu mesin lokal. Tidak ada koneksi ke jaringan
kampus atau internet saat pengujian; Ollama dan ChromaDB diakses lewat loopback.

Komponen dan arah koneksinya:

- **Browser (pengguna/demo)** -> `http://127.0.0.1:5000` (Flask, `app/`).
- **Flask (`app/routes.py`)** -> `pipeline.answer` (Python murni, `src/ragbot/`).
- **Pipeline** -> **ChromaDB** (persistent di `chroma_db/`) untuk retrieval.
- **Pipeline** -> **Ollama** (`http://127.0.0.1:11434`) untuk embedding
  (`nomic-embed-text`) dan generasi (`llama3.2:3b`).
- ChromaDB dan Ollama tidak diekspos ke jaringan; hanya diakses dari proses
  Flask di host yang sama.

Gambar topologi: `docs/topology.drawio` (sumber), ekspor ke `docs/topology.png`
dilakukan manual di draw.io (TODO: ekspor dan commit `docs/topology.png`).

## 2. Target

| Aspek | Nilai |
|---|---|
| URL target | `http://127.0.0.1:5000` |
| Endpoint yang diuji | `POST /api/chat` |
| Mode percakapan | Stateless, satu giliran per permintaan |
| Koleksi yang digunakan | `kb_clean`, `kb_poisoned`, `kb_poisoned_sanitized` (lihat `docs/decisions.md`) |
| Model chat | `llama3.2:3b` (Ollama) |
| Model embedding | `nomic-embed-text` (Ollama) |

## 3. Spesifikasi mesin

| Item | Nilai |
|---|---|
| CPU | 12th Gen Intel(R) Core(TM) i7-12700H |
| RAM | 15.73 GB |
| GPU | Tidak ada (CPU only) |
| Sistem operasi dan versi | Microsoft Windows 11 Home Single Language, 10.0.26300, 64-bit |
| Penyimpanan bebas saat eksperimen | 70.96 GB (drive C:, total 474.31 GB) |

## 4. Versi software

| Software | Versi |
|---|---|
| Python | 3.12.10 |
| Ollama | 0.40.17 |
| Model chat (nama dan kuantisasi) | `llama3.2:3b`, Q4_K_M, 3.2B parameter, context length 131072 |
| Model embedding | `nomic-embed-text` |
| ChromaDB | 1.5.9 |
| Flask | 3.1.3 |
| garak (venv terpisah) | TODO (venv `.venv-garak` belum terpasang di mesin ini) |

## 5. Catatan waktu

TODO: diisi setelah pilot run. Catat latensi satu permintaan (rata-rata dan p95)
dari `latency_s` di CSV, lalu hitung total waktu satu run penuh
(skenario x varian x trial x kondisi) dan bandingkan dengan estimasi
`--dry-run`. Angka ini dipakai untuk anggaran waktu di laporan.