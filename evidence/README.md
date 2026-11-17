# Aturan bukti

Bukti dipakai di laporan dan video, jadi harus berasal dari eksekusi nyata
(`AGENTS.md` Bagian 2 poin 6). Jangan menambahkan tangkapan layar hasil rekayasa.

## Penamaan

```
evidence/<Sx>/<Sx>-<varian>-<trial>-<sebelum|sesudah>-mitigasi.<ext>
```

Contoh: `evidence/S1/S1-v03-t05-sebelum-mitigasi.png`.

- `<Sx>`: `S1`, `S2`, atau `S3`.
- `<varian>`: id varian di `attacks/scenarios/`, misalnya `v03`.
- `<trial>`: nomor percobaan dua digit, misalnya `t05`.
- Kondisi: `sebelum-mitigasi` atau `sesudah-mitigasi`.
- `<ext>`: `png` untuk tangkapan layar, `json` atau `txt` untuk potongan log.

## Isi minimum satu bukti

- Pertanyaan atau payload yang dipakai.
- Jawaban model apa adanya.
- Status berhasil/gagal menurut aturan di `attacks/judges.py`.
- Nama koleksi, flags mitigasi, dan timestamp yang bisa dicocokkan dengan JSONL.

## Larangan

- Jangan menyimpan data pribadi, kredensial, atau dokumen nyata di sini.
- Jangan mengunggah isi `evidence/` ke luar repo; repo harus private.
- Jangan menghapus bukti percobaan yang gagal; hasil negatif tetap dipakai di pembahasan.
