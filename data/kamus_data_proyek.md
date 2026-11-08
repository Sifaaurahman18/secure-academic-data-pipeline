# Kamus Data Proyek Secure Academic Data Pipeline

Seluruh isi berkas pada folder `data/` adalah **data sintetik** yang dibuat untuk
pembelajaran. Tidak ada nama, Nomor Induk Mahasiswa (NIM), nilai, akun, atau
alamat server nyata di dalamnya. Dataset dihasilkan oleh `tools/buat_dataset.py`
dan dapat dibuat ulang kapan saja dengan hasil yang sama.

## 1. Berkas

| Berkas | Isi | Dipakai pada |
|---|---|---|
| `referensi_mata_kuliah.csv` | Daftar kode dan nama mata kuliah yang sah | Validasi kode, P07 dan P10 |
| `raw/akademik_sintetik_raw.csv` | Masukan pipeline apa adanya, **sengaja memuat baris bermasalah** | P10 dan P11 |
| `processed/akademik_sintetik_bersih.csv` | Hasil yang diharapkan setelah seluruh aturan validasi diterapkan | Pembanding hasil P10 |
| `karantina/` | Tujuan baris yang ditolak pipeline | P10 dan P11 |
| `manifest.sha256` | Ringkasan SHA-256 tiga berkas data | Pemeriksaan keutuhan, P01 sampai P14 |

Berkas `raw` dan `processed` memakai kolom yang sama. Perbedaannya bukan pada
struktur, melainkan pada apakah isinya sudah lolos aturan validasi.

## 2. Kolom data akademik

| Kolom | Arti | Aturan validasi |
|---|---|---|
| `record_id` | Kode unik satu catatan nilai | Wajib ada, unik dalam satu berkas |
| `kode_mahasiswa` | Pengenal semu mahasiswa, bukan NIM nyata | Wajib ada, format `MHS-SYN-nnnn` |
| `program_studi` | Program studi pada catatan tersebut | Wajib ada, tanpa spasi berlebih, penulisan konsisten |
| `semester` | Semester saat mata kuliah ditempuh | Salah satu dari 1, 3, 5, atau 7 |
| `kode_mk` | Kode mata kuliah | Harus terdaftar pada `referensi_mata_kuliah.csv` |
| `nilai_angka` | Nilai akhir numerik | Bilangan bulat 0 sampai 100 |
| `persentase_kehadiran` | Persentase kehadiran | Bilangan bulat 0 sampai 100 |
| `status_kelulusan` | Hasil kelulusan mata kuliah | `Lulus` atau `Tidak Lulus`, dan harus sesuai aturan pada bagian 3 |
| `status_pendampingan` | Penanda apakah mahasiswa sedang menerima pendampingan akademik | `Ya` atau `Tidak` |
| `waktu_pembaruan` | Waktu catatan terakhir diperbarui | Format `YYYY-MM-DDTHH:MM:SS` |

Selain aturan per kolom, kombinasi `kode_mahasiswa` + `kode_mk` + `semester`
harus unik. Satu mahasiswa tidak boleh memiliki dua catatan nilai untuk mata
kuliah dan semester yang sama.

## 3. Aturan turunan status kelulusan

```text
status_kelulusan = "Lulus"       bila nilai_angka >= 60 DAN persentase_kehadiran >= 75
status_kelulusan = "Tidak Lulus" untuk kondisi lainnya
```

Aturan ini adalah **model latihan mata kuliah**, bukan ketentuan akademik yang
berlaku di program studi. Karena nilainya dapat dihitung ulang dari kolom lain,
`status_kelulusan` berguna untuk melatih pemeriksaan konsistensi: catatan yang
menyatakan `Lulus` padahal nilainya 41 menandakan data telah berubah, salah
dimasukkan, atau berasal dari sumber yang tidak dapat dipercaya.

## 4. Kolom paling sensitif

Kolom `status_pendampingan` adalah atribut paling sensitif pada dataset ini.
Kolom tersebut menggambarkan kondisi pribadi, bukan capaian akademik, dan tidak
dibutuhkan oleh sebagian besar pengguna data.

Konsekuensi rancangannya:

- kolom ini **tidak disertakan** pada view `v_nilai_mahasiswa`, sehingga tidak
  dapat dijangkau melalui starter API;
- kolom ini hanya muncul dalam bentuk agregat pada view
  `v_ringkasan_pendampingan`;
- kolom ini tidak boleh ditulis ke log, pesan galat, atau berkas keluaran.

Prinsip minimisasi data dibahas lebih lanjut pada Pertemuan 6.

## 5. Klasifikasi latihan

Klasifikasi berikut memakai model Publik, Internal, dan Terbatas dari
Pertemuan 2. Model ini adalah kesepakatan kelas, bukan klasifikasi resmi
institusi.

| Aset | Klasifikasi latihan | Alasan singkat |
|---|---|---|
| `referensi_mata_kuliah.csv` | Publik | Tidak memuat data orang |
| `raw/akademik_sintetik_raw.csv` | Terbatas | Memuat pengenal dan atribut pendampingan |
| `processed/akademik_sintetik_bersih.csv` | Terbatas | Sama seperti di atas, ditambah dipakai untuk keputusan |
| Laporan agregat dari view | Internal | Perlu ditinjau lebih dahulu; ukuran kelompok kecil dapat membuka identitas |
| `manifest.sha256` | Internal | Tidak memuat data, tetapi menjadi dasar pembuktian keutuhan |

## 6. Membuat ulang dataset

```bash
python tools/buat_dataset.py                 # hasil sama dengan yang dibagikan
python tools/buat_dataset.py --seed 2027     # varian untuk kelas paralel
```

Perintah tersebut menulis ulang tiga berkas data, `database/seed_data.sql`, dan
`data/manifest.sha256`. Setelah dataset diganti, hash pada manifest ikut
berubah. Jalankan `python tools/periksa_aset_proyek.py` untuk memastikan seluruh
aset kembali konsisten sebelum dibagikan.
