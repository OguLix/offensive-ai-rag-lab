# garak (pemindaian lokal)

Pemilik: A. Pemindaian otomatis tambahan terhadap chatbot RAG lokal untuk
melengkapi pengujian manual skenario S1.

## Batasan wajib

- Target satu-satunya adalah chatbot di repo ini di `http://127.0.0.1:5000/api/chat`.
- Dilarang mengarahkan garak ke host lain, jaringan kampus, layanan publik, atau
  milik orang lain (`AGENTS.md` Bagian 2). Skrip `run_scan.ps1` menolak URI di
  luar `http://127.0.0.1:<port>/api/chat`.
- garak dipasang di venv terpisah (`.venv-garak`) sesuai `requirements-garak.txt`.
- Log mentah garak ditulis ke `logs/garak/` (di-gitignore); hanya ringkasan
  angka yang dicatat di dokumen ini.

## File konfigurasi

| File | Fungsi |
|---|---|
| `garak/rest_baseline.json` | Konfigurasi `RestGenerator` ke `127.0.0.1:5000/api/chat` pada koleksi `kb_clean`, semua flag mitigasi `false` |
| `garak/rest_m1.json` | Konfigurasi `RestGenerator` ke `127.0.0.1:5000/api/chat` pada koleksi `kb_clean`, mitigasi M1 aktif (`prompt_hardening`, `input_filter`, `output_filter`) |
| `garak/run_scan.ps1` | Skrip PowerShell untuk validasi target loopback, cek server Flask aktif, lalu menjalankan garak |

## Pemilihan probe dan alasannya

Hanya probe yang **tidak menghasilkan konten berbahaya** dan relevan dengan
injeksi instruksi yang dipilih (`AGENTS.md` Bagian 2.3):

| Probe | Alasan pemilihan |
|---|---|
| `promptinject.HijackLongPrompt` | Menguji apakah input pengguna dapat membajak instruksi sistem dengan target string tidak berbahaya (relevan langsung dengan S1). |
| `latentinjection.LatentWhois` | Menguji kerentanan injeksi tersembunyi di dalam teks kontekstual (melengkapi pengamatan terhadap instruksi tertanam). |

Catatan: sebelum run pertama, pastikan nama probe tersedia di versi garak yang
terpasang dengan perintah `.\.venv-garak\Scripts\garak.exe --list_probes`.

## Cara menjalankan (Windows PowerShell)

1. Pasang garak di venv terpisah (sekali saja):

   ```powershell
   py -3.12 -m venv .venv-garak
   .\.venv-garak\Scripts\Activate.ps1
   pip install -r requirements-garak.txt
   ```

2. Pastikan Ollama berjalan (`llama3.2:3b` dan `nomic-embed-text` sudah di-pull),
   koleksi `kb_clean` sudah di-ingest, dan server Flask aktif di terminal lain:

   ```powershell
   flask --app app run --host 127.0.0.1 --port 5000
   ```

3. Jalankan pemindaian baseline dan M1:

   ```powershell
   .\garak\run_scan.ps1 -Mode baseline -Generations 1
   .\garak\run_scan.ps1 -Mode m1 -Generations 1
   ```

## Ringkasan hasil pemindaian

Status: **belum dijalankan** (menunggu Ollama + `.venv-garak` + hook filter M1 di `pipeline.py`). Jangan mengisi angka perkiraan di tabel ini (`AGENTS.md` Bagian 2.6).

| Tanggal | Mode | Probe | Passed / Total | Catatan |
|---|---|---|---|---|
| — | baseline | — | — | Belum ada hasil eksekusi nyata |
| — | m1 | — | — | Belum ada hasil eksekusi nyata |
