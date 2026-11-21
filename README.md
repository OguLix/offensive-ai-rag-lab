# RAG Red Team Lab

Kerangka lab lokal untuk Final Project Keamanan Informasi (KP70065004), Prodi
Informatika, Universitas Siliwangi.

Judul: **Evaluasi Keamanan Chatbot RAG dengan LLM Lokal melalui Pendekatan Red
Teaming: Studi Kasus Prompt Injection dan Document Poisoning.**

Repo ini berisi chatbot RAG buatan sendiri sebagai target, tiga skenario serangan
(S1 prompt injection langsung, S2 prompt injection tidak langsung, S3 document
poisoning), dan mitigasinya (M1-M3). Seluruh data bersifat fiktif dan target hanya
berjalan di `127.0.0.1`.

> **Baca [AGENTS.md](AGENTS.md) sebelum mengubah apa pun.** Bagian 2 (etika) dan
> Bagian 12.1 (larangan git untuk agent) tidak bisa ditawar.

## Status

Fase 0: kerangka repo saja. Semua modul RAG, mitigasi, dan evaluasi masih
`NotImplementedError`. `POST /api/chat` menjawab `501` sampai Fase 1 selesai.

## Prasyarat

- Python 3.11 atau 3.12 (venv). Jangan 3.14.
- Ollama terpasang, dengan model chat dan embedding yang dipilih tim.
- Nama model di `config/settings.yaml`: chat `llama3.2:3b`, embedding `nomic-embed-text`.

## Setup Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# venv terpisah untuk garak (berat, hanya dipakai pemilik garak)
py -3.12 -m venv .venv-garak
.\.venv-garak\Scripts\Activate.ps1
pip install -r requirements-garak.txt
```

## Setup Linux/macOS

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Salin `.env.example` menjadi `.env` bila perlu mengubah alamat Ollama. `.env`
tidak pernah di-commit.

## Menjalankan

```powershell
# dari venv utama, setelah nama model diisi di config/settings.yaml
ollama pull <model_chat>
ollama pull <model_embedding>

python -m ragbot.ingest --collection kb_clean --path data/corpus   # Fase 1
flask --app app run --host 127.0.0.1 --port 5000
```

Buka `http://127.0.0.1:5000`. Jangan memakai `--host 0.0.0.0` dan jangan
mengaktifkan debug mode di luar mesin sendiri.

## Pemeriksaan mutu

```bash
ruff check . && ruff format .
pytest
pytest -m integration   # hanya bila Ollama berjalan
```

## Struktur singkat

| Path | Isi |
|---|---|
| `config/` | `settings.yaml` dan `prompts/system_prompt.txt` |
| `src/ragbot/` | Paket inti: ingest, retriever, prompt builder, pipeline, LLM client |
| `src/ragbot/mitigations/` | M1 (A), M2 (B), M3 (C) |
| `attacks/` | Skema skenario S1-S3 dan `judges.py` |
| `evaluation/` | Runner eksperimen, metrik, dan `results/` |
| `app/` | Frontend Flask (halaman chat + panel inspeksi) |
| `data/` | Korpus fiktif dan dokumen serangan yang dikarantina |
| `evidence/` | Bukti untuk laporan, aturan penamaan di `evidence/README.md` |
| `docs/` | Keputusan, lingkungan lab, skrip video, draf laporan |
| `garak/` | Catatan pemindaian lokal |

## Aturan kerja

- Pembagian tugas dan kontrak antarmodul: `AGENTS.md` Bagian 3 dan 6.
- Agent AI tidak boleh menjalankan perintah git yang mengubah repo; commit
  dilakukan manusia (`AGENTS.md` Bagian 12.1).
- Repo harus private. Payload serangan tidak dipublikasikan di luar repo ini.
