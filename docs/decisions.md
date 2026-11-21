# Keputusan proyek

Catatan keputusan teknis dan perubahan pembagian tugas. Setiap perubahan yang
memengaruhi kontrak antarmodul atau file bersama dicatat di sini sebelum
dikerjakan, sesuai `AGENTS.md` Bagian 3 dan 6.

## Pembagian tugas

Diambil dari `AGENTS.md` Bagian 3. Nama anggota masih placeholder sampai tim mengisi.

| Anggota | Komponen inti | Skenario | Mitigasi | Tambahan |
|---|---|---|---|---|
| **A** `<NAMA_A>` | `ingest.py`, `vectorstore.py`, korpus fiktif di `data/corpus/` | **S1** prompt injection langsung dan kebocoran system prompt | **M1** prompt hardening, input filter, output filter | Integrasi dan konfigurasi garak |
| **B** `<NAMA_B>` | `retriever.py`, `prompt_builder.py`, `pipeline.py` | **S2** prompt injection tidak langsung lewat dokumen | **M2** context isolation, sanitasi hasil retrieval | — |
| **C** `<NAMA_C>` | `llm_client.py`, `logging_utils.py`, `evaluation/` | **S3** document poisoning | **M3** ingest sanitizer, provenance | Dokumentasi lab (topologi, target, spesifikasi, versi), kumpulan bukti dan tabel hasil |

File bersama: `app/`, `config/`, `README.md`, skrip video, dan penggabungan laporan.
Perubahan di sana lewat PR dengan dua peninjau.

## Keputusan yang sudah ada

| Keputusan | Alasan / rujukan |
|---|---|
| Python 3.11 atau 3.12 di venv, bukan 3.14 | Kompatibilitas library; `AGENTS.md` Bagian 4 |
| Frontend Flask + Jinja2 + CSS/JS biasa, tanpa CDN | Ditulis bersama, cukup untuk demo; Bagian 4 dan 10.3 |
| LLM lokal lewat Ollama, model kelas 3B-8B terkuantisasi | Tanpa GPU dan tanpa biaya API; Bagian 4 |
| ChromaDB persistent di `chroma_db/` (di-gitignore) | Vector store sederhana, tidak perlu server; Bagian 4 |
| Tanpa LangChain/LlamaIndex, Python murni | Alur retrieve-prompt-generate harus terlihat agar bisa diserang dan dimitigasi; Bagian 4 |
| Nama model dibaca dari `config/settings.yaml`, bukan hard-code | Bagian 4 dan 11; diisi di branch `feature/a-vectorstore` |
| Konfigurasi tambahan di `settings.yaml`: `allowed_collections`, `app_host`, `app_port`, `max_question_chars` | Whitelist dan batas validasi tidak boleh jadi magic string di `app/routes.py`; Bagian 10.3 dan 11 |
| `POST /api/chat` mengembalikan `501` selama pipeline masih stub | Membedakan "belum jadi" dari galat nyata; Bagian 10.1 |
| Repo private; payload hanya di `attacks/` | Bagian 2 |
| Agent AI tidak menjalankan perintah git yang mengubah repo | Bagian 12.1; commit dilakukan manusia |
| Kontrak dataclass di `types.py` dibekukan seperti Bagian 6 | Tiga orang bekerja paralel; perubahan butuh persetujuan ketiganya |
| Model chat `llama3.2:3b`, embedding `nomic-embed-text` (keduanya via Ollama) | Disepakati tim; diterapkan ke `config/settings.yaml` di branch `feature/a-vectorstore`. Embedding dihitung di `vectorstore.py` lewat Ollama (prefix tugas `search_document:`/`search_query:`), bukan embedding bawaan ChromaDB yang akan mengunduh model lain. Kuantisasi dicatat C di `docs/lab-environment.md` |
| Organisasi fiktif: Unit Layanan Administrasi **RAG REDTeam** | Korpus bersih `data/corpus/` (14 dokumen) memuat versi benar dari topik yang diserang S2/S3 (jam layanan, biaya administrasi, prosedur pengambilan dokumen, kontak, pendaftaran) dan diuji di `tests/test_corpus.py` agar tidak memuat marker atau klaim palsu |
| Canary S1: `S1-CANARY-RAGREDTEAM-7492` | Ditanam di `config/prompts/system_prompt.txt` (bukan data nyata) dan dipakai oleh varian kebocoran system prompt di `attacks/scenarios/s1_direct_injection.yaml`. Varian override memakai penanda `S1-OVERRIDE-vXX`. Semua varian S1 dinilai lewat `variant.marker` (case-insensitive) |

## Belum diputuskan

| Hal | Pemilik keputusan | Catatan |
|---|---|---|
| Jumlah percobaan per kombinasi | Tim | Minimal 10 menurut Bagian 8; angka final disepakati di Fase 3 |
| Pemilik `attacks/judges.py` | Tim | Belum ada di tabel Bagian 3; usulan: setiap pemilik skenario menulis aturannya, C merapikan |
| Signature fungsi `apply()` di modul mitigasi | A untuk M1, B untuk M2, C untuk M3 | Stub Fase 0 memakai `*args, **kwargs` agar tidak mengunci kontrak yang belum disepakati |
| Apakah `kb_poisoned_sanitized` dipakai di run final | C | Menentukan tabel hasil di laporan |

## Perubahan pembagian tugas

| Tanggal | Perubahan | Alasan | Persetujuan |
|---|---|---|---|
| 2026-11-18 | Dokumentasi lab (`docs/lab-environment.md`, `docs/topology.drawio`, `docs/topology.png`) dipindahkan dari B ke C | Eksperimen final dijalankan di laptop C, sehingga spesifikasi mesin, versi Ollama dan model, serta latensi hanya dapat diisi dari mesin tersebut | Diajukan B; disetujui saat PR dokumentasi ini ditinjau A dan C |
