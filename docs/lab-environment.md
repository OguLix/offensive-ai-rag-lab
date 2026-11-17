# Lingkungan lab

Pemilik: B. Isi dokumen ini dari mesin yang benar-benar dipakai untuk eksperimen
final. Jangan mengisi angka perkiraan.

## 1. Topologi

TODO(B): gambar topologi di `docs/topology.drawio`, ekspor ke `docs/topology.png`,
lalu jelaskan komponen dan arah koneksinya di sini.

Poin yang harus terlihat:

- Semua komponen berjalan di satu mesin lokal.
- Browser, aplikasi Flask, Ollama, dan ChromaDB berada di satu host.
- Tidak ada koneksi ke jaringan kampus atau internet saat pengujian.

## 2. Target

| Aspek | Nilai |
|---|---|
| URL target | `http://127.0.0.1:5000` |
| Endpoint yang diuji | `POST /api/chat` |
| Mode percakapan | Stateless, satu giliran per permintaan |
| Koleksi yang digunakan | `kb_clean`, `kb_poisoned`, `kb_poisoned_sanitized` (lihat `docs/decisions.md`) |
| Model chat | TODO |
| Model embedding | TODO |

## 3. Spesifikasi mesin

| Item | Nilai |
|---|---|
| CPU | TODO |
| RAM | TODO |
| GPU | TODO (tulis "tidak ada" bila memakai CPU) |
| Sistem operasi dan versi | TODO |
| Penyimpanan bebas saat eksperimen | TODO |

## 4. Versi software

| Software | Versi |
|---|---|
| Python | TODO |
| Ollama | TODO |
| Model chat (nama dan kuantisasi) | TODO |
| Model embedding | TODO |
| ChromaDB | TODO |
| Flask | TODO |
| garak (venv terpisah) | TODO |

## 5. Catatan waktu

TODO(B): catat perkiraan latensi satu permintaan dan total waktu satu run penuh,
supaya anggaran waktu eksperimen di laporan bisa dipertanggungjawabkan.
