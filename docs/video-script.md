# Skrip video demo

Target durasi 5-10 menit, diunggah ke YouTube, ketiga anggota tampil.
Kerangka ini hanya judul; isi narasi ditulis setelah eksperimen Fase 3-4 selesai.

## 1. Pembukaan (0:00-1:00)

- Perkenalan anggota `<NAMA_A>`, `<NAMA_B>`, `<NAMA_C>`.
- Judul proyek dan alasan memilih topik.
- Batasan etika: target hanya lokal, data fiktif, tujuan serangan hanya canary.

## 2. Arsitektur target (1:00-2:30)

- Alur ingest, retrieve, prompt building, generate.
- Peran `ragbot.pipeline.answer` sebagai satu-satunya pintu masuk.

## 3. Skenario S1 (2:30-4:00)

- Demonstrasi sebelum mitigasi, lalu M1 aktif.
- Tunjukkan canary dan `blocked_by` di panel inspeksi.

## 4. Skenario S2 (4:00-5:30)

- Demonstrasi dokumen berisi instruksi tersembunyi, lalu M2 aktif.

## 5. Skenario S3 (5:30-7:00)

- Demonstrasi dokumen beracun mengalahkan dokumen asli, lalu M3 aktif.

## 6. Hasil dan metrik (7:00-8:30)

- Tabel ASR sebelum dan sesudah mitigasi dari `evaluation/results/`.
- False positive pada pertanyaan normal dan dampak latensi.

## 7. Penutup (8:30-9:30)

- Keterbatasan, serangan yang masih lolos, dan rekomendasi.
- Pembagian kontribusi tiap anggota.

## Checklist sebelum rekaman

- [ ] Model dan koleksi sudah sesuai `docs/decisions.md`.
- [ ] Semua angka di layar berasal dari CSV/JSONL yang benar-benar dijalankan.
- [ ] Tidak ada data nyata, kredensial, atau payload di luar repo yang tampil.
- [ ] Ukuran huruf dan kontras layar sudah dicek di rekaman percobaan.
