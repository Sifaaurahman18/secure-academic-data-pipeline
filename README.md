# Starter Secure Academic Data Pipeline

Paket awal proyek Mata Kuliah **Keamanan Data (SSD1033)**, Program Studi Sains
Data, Universitas Islam Negeri (UIN) K.H. Abdurrahman Wahid Pekalongan.

Folder ini dipakai satu kali untuk seluruh semester. Setiap pertemuan praktikum
menambahkan bagian baru ke folder yang sama, bukan membuat proyek baru.

> [!CAUTION]
> Seluruh data pada paket ini adalah data sintetik. Jangan memasukkan nama,
> NIM, nilai, atau identitas mahasiswa nyata. Jangan menuliskan kata sandi,
> token, atau kunci aktif ke dalam kode, berkas SQL, log, maupun tangkapan
> layar. Jangan menguji sistem di luar laboratorium yang diizinkan.

## 1. Isi paket

```text
secure-academic-data-pipeline/
├── database/
│   ├── schema.sql          struktur tabel dan view
│   ├── seed_data.sql       data sintetik siap muat
│   ├── roles.sql           akun, role, dan privilege
│   └── uji_akses.sql       pengujian positif dan negatif
├── data/
│   ├── referensi_mata_kuliah.csv
│   ├── raw/                masukan pipeline apa adanya
│   ├── processed/          hasil yang diharapkan setelah validasi
│   ├── karantina/          tujuan baris yang ditolak
│   ├── kamus_data_proyek.md
│   └── manifest.sha256
├── api/                    starter API - Pertemuan 9 dan 11
│   ├── main.py             aplikasi dan seluruh endpoint
│   ├── keamanan.py         identitas pemanggil dan otorisasi
│   ├── basis_data.py       query, semuanya berparameter
│   ├── skema.py            bentuk data yang boleh keluar
│   ├── pencatatan.py       pencatatan keamanan
│   └── konfigurasi.py      pembacaan konfigurasi
├── pipeline/               starter pipeline - Pertemuan 10 dan 11
│   ├── konfigurasi.py      konfigurasi dan jalur berkas
│   ├── keutuhan.py         ringkasan SHA-256 dan gerbang masukan
│   ├── aturan.py           aturan validasi satu baris
│   ├── pencatatan.py       pencatatan kejadian pipeline
│   ├── basis_data.py       koneksi sebagai operator_pipeline
│   ├── validasi.py         langkah 1 - memisahkan yang sah dan yang ditolak
│   ├── muat.py             langkah 2 - memuat ke tabel staging
│   └── ringkas.py          langkah 3 - laporan agregat
├── tests/
│   ├── conftest.py
│   └── test_api.py         pengujian negatif starter API
├── logs/
├── tools/
│   ├── buat_dataset.py     pembuat dataset sintetik
│   └── periksa_aset_proyek.py
├── .env.example
├── .gitignore
└── requirements.txt
```

Folder `docs/` dibuat pada pertemuan yang membutuhkannya, mengikuti struktur pada
[Spesifikasi Proyek](<../Spesifikasi Proyek - Secure Academic Data Pipeline.md>).

## 2. Persiapan Python

> [!IMPORTANT]
> **Jangan membuat `.venv` di dalam folder yang disinkronkan** ke Google Drive, OneDrive, atau layanan sejenis. Satu virtual environment berisi sekitar 1.100 berkas dan 70 MB; layanan sinkronisasi akan menyalin semuanya terus-menerus dan dapat mengunci berkas saat dipakai.
>
> Buat virtual environment di folder lokal, misalnya `C:/kuliah/keamanan-data/.venv`, lalu aktifkan dari sana ketika bekerja pada proyek. Berkas proyek boleh tetap berada di folder tersinkron.

```bash
python -m venv .venv
source .venv/Scripts/activate      # Git Bash di Windows
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Periksa kelengkapan paket sebelum mulai:

```bash
python tools/periksa_aset_proyek.py
```

Hasil yang diharapkan:

```text
PEMERIKSAAN ASET PROYEK
Referensi mata kuliah : 8
Baris raw             : 831
Baris processed       : 808
Baris cacat pada raw  : 21
record_id ganda       : 1
Kunci alami ganda     : 2
Berkas SQL            : schema, seed, roles, uji_akses tersedia
Kamus data            : tersedia dan selaras
Manifest SHA-256      : sesuai
Kredensial aktif      : tidak ditemukan
Mode                  : harian
ASET PROYEK SIAP DIGUNAKAN
```

Selama praktikum berlangsung berkas `.env` Anda sudah ada, sehingga skrip
menambahkan satu baris `Catatan`. Baris itu peringatan, bukan kegagalan.

Selisih antara 831 baris raw dan 808 baris processed adalah 23. Dua puluh satu
di antaranya melanggar aturan per baris, misalnya nilai di luar rentang atau
tanggal yang tidak sah. Dua sisanya justru sah bila diperiksa sendiri-sendiri;
keduanya hanya bermasalah karena menduplikasi baris lain. Perbedaan itu penting:
sebagian cacat hanya terlihat ketika berkas diperiksa sebagai satu kesatuan,
bukan baris demi baris.

Bila skrip berhenti dengan pesan `GAGAL`, catat pesannya lengkap. Jangan
menghapus bukti kegagalan.

## 3. Menyiapkan basis data

Dijalankan **berurutan** menggunakan akun administrator laboratorium, melalui
MySQL Workbench atau baris perintah.

| Urutan | Berkas | Isi |
|---:|---|---|
| 1 | `database/schema.sql` | Membuat basis data `secure_academic_lab`, lima tabel, dan tiga view |
| 2 | `database/seed_data.sql` | Memuat 808 catatan nilai sintetik |
| 3 | `database/roles.sql` | Membuat role dan akun sesuai hak minimum |
| 4 | `database/uji_akses.sql` | Menguji akses yang diizinkan dan yang harus ditolak |

Melalui baris perintah:

```bash
mysql -u root -p -e "source database/schema.sql"
mysql -u root -p -e "source database/seed_data.sql"
mysql -u root -p -e "source database/roles.sql"
```

Bentuk `-e "source …"` berjalan di Git Bash, PowerShell, maupun Command Prompt.
Bentuk `mysql … < berkas.sql` tidak berjalan di PowerShell.

> [!IMPORTANT]
> Sebelum menjalankan `roles.sql`, ganti setiap penanda `__GANTI_..._` dengan
> kata sandi laboratorium Anda. Setelah diganti, berkas tersebut **tidak boleh**
> ikut dikumpulkan. Salin `.env.example` menjadi `.env` untuk menyimpan kata
> sandi yang dipakai program, dan jangan pernah membagikan berkas `.env`.

## 4. Akun dan hak akses

| Akun | Boleh | Tidak boleh |
|---|---|---|
| `admin_lab` | Mengelola skema, seed, dan akun | Dipakai oleh pipeline atau API |
| `app_service` | Membaca `v_nilai_mahasiswa` dan `v_ringkasan_kelulusan`, menulis log | Membaca tabel dasar, membaca log, mengubah data |
| `analyst` | Membaca dua view ringkasan | Membaca data tingkat record |
| `operator_pipeline` | Menulis dan membaca `staging_nilai`, membaca `mata_kuliah`, menulis log | Membaca identitas mahasiswa atau nilai tervalidasi |
| `auditor` | Membaca `log_aktivitas` | Menambah, mengubah, atau menghapus log |

Kolom `status_pendampingan` tidak dapat dijangkau oleh akun mana pun selain
`admin_lab`. Kolom tersebut tidak disertakan dalam view yang dibaca aplikasi.

## 5. Data

Penjelasan setiap kolom, aturan validasi, dan klasifikasi latihan tersedia pada
[kamus data proyek](data/kamus_data_proyek.md).

Dua hal yang perlu diketahui sejak awal:

1. Berkas pada `data/raw/` sengaja memuat baris bermasalah. Berkas tersebut
   adalah masukan pipeline, bukan data yang sudah bersih.
2. Berkas pada `data/processed/` adalah hasil yang diharapkan setelah seluruh
   aturan validasi diterapkan. Gunakan sebagai pembanding, bukan sebagai jalan
   pintas.

Membuat ulang dataset:

```bash
python tools/buat_dataset.py
```

## 6. Starter API

Dipakai pada Pertemuan 9 dan diintegrasikan pada Pertemuan 11.

> [!CAUTION]
> Starter ini **sengaja memuat lima kelemahan keamanan**, sehingga bukan contoh API
> yang aman dan tidak boleh dipakai sebagai pola untuk pekerjaan lain sebelum
> kelima TODO diselesaikan. Penandanya ada pada `api/main.py` dan
> `api/keamanan.py`.

Sebelum menjalankan, buat tiga kunci API dan simpan pada `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Jalankan tiga kali, lalu isikan hasilnya ke `API_KEY_MAHASISWA`,
`API_KEY_DOSEN_WALI`, dan `API_KEY_ANALIS`. Nilainya dibuat program, bukan
diketik sendiri, dan tidak pernah dituliskan ke dalam kode.

Menjalankan layanannya:

```bash
uvicorn api.main:app --reload --port 8000
```

Lalu buka `http://127.0.0.1:8000/docs` untuk Swagger UI.

| Endpoint | Isi | Kunci diperlukan |
|---|---|---|
| `GET /sehat` | Penanda layanan hidup | Tidak |
| `GET /nilai/{kode_mahasiswa}` | Catatan nilai satu mahasiswa | Ya |
| `GET /nilai` | Pencarian dengan penyaring | Ya |
| `GET /ringkasan` | Laporan agregat kelulusan | Ya |

Layanan ini terhubung sebagai `app_service`, sehingga hanya dapat membaca dua
view dan menulis log. Kolom `status_pendampingan` tidak dapat dijangkau
melalui jalur mana pun.

Menjalankan pengujian:

```bash
python -m pytest tests/test_api.py -v
```

Berkas pengujian itu **gagal pada mulanya**, dan itu disengaja. Berkas itu ditulis
sebelum perbaikan, sehingga isinya menjadi daftar pekerjaan Anda. Empat pengujian
hijau sejak awal; sisanya menjadi hijau setelah TODO diselesaikan.

Log runtime ditulis ke dua tempat: `logs/api.log` dan tabel `log_aktivitas`.
Isinya tidak boleh memuat kunci, kata sandi, maupun isi baris data pribadi.

## 7. Pipeline

Dipakai pada Pertemuan 10 dan diintegrasikan pada Pertemuan 11.

> [!CAUTION]
> Starter ini **sengaja belum selesai**: lima bagian bertanda TODO adalah bahan
> praktikum Pertemuan 10. Sebelum kelimanya dikerjakan, pipeline berhenti pada
> TODO pertama, dan itu memang perilaku yang diharapkan.

Tiga langkah, dijalankan berurutan dari folder proyek:

```bash
python -m pipeline.validasi    # berkas mentah  -> processed dan karantina
python -m pipeline.muat        # hasil validasi -> tabel staging_nilai
python -m pipeline.ringkas     # tabel staging  -> laporan agregat
```

Langkah pertama tidak menyentuh basis data sama sekali, sehingga dapat
dikerjakan sebelum MySQL disiapkan. Dua langkah berikutnya terhubung sebagai
`operator_pipeline`, yang hanya boleh menulis dan membaca `staging_nilai`, membaca
`mata_kuliah`, dan menulis log. Akun tersebut tidak dapat menyentuh
`nilai_akademik`: pipeline yang keliru sekalipun tidak boleh mampu merusak
nilai yang sudah tervalidasi.

| Berkas keluaran | Isi |
|---|---|
| `data/processed/hasil_pipeline.csv` | Baris yang lolos seluruh aturan |
| `data/processed/hasil_pipeline.csv.sha256` | Ringkasan berkas di atas |
| `data/karantina/karantina-<korelasi>.csv` | Baris yang ditolak, beserta kode alasannya |
| `data/processed/ringkasan-<batch>.csv` | Laporan agregat yang sudah ditekan sel kecilnya |
| `logs/pipeline.log` | Catatan kejadian, satu baris JSON per kejadian |

Berkas mentah tidak pernah diubah, dan berkas
`data/processed/akademik_sintetik_bersih.csv` yang dibagikan dosen adalah
pembanding hasil Anda, bukan berkas yang ditimpa pipeline. Hasil yang benar
sama persis dengan pembanding tersebut, dan tetap sama setiap kali pipeline
dijalankan ulang.

Memeriksa hasil kerja Anda:

```bash
cd "../../03_Materi Pertemuan/P10 - Keamanan Pipeline Python-pandas"
python starter/periksa_hasil_p10.py
```

Pemeriksa itu tidak membutuhkan MySQL.

## 8. Aturan pengumpulan

Sebelum mengumpulkan artefak apa pun dari folder ini:

- [ ] berkas `.env` tidak disertakan;
- [ ] `roles.sql` kembali memakai penanda `__GANTI_..._`;
- [ ] tidak ada kata sandi, token, atau kunci pada kode, log, atau tangkapan layar;
- [ ] log sudah disanitasi dari nama host dan jalur berkas pribadi;
- [ ] `python tools/periksa_aset_proyek.py --pengumpulan` berjalan tanpa kegagalan;
- [ ] `python -m pytest tests/` berjalan tanpa kegagalan;
- [ ] keluaran pipeline (`hasil_pipeline.csv`, `ringkasan-*.csv`, isi `data/karantina/`) tidak ikut dikumpulkan;
- [ ] berkas `logs/api.log` tidak ikut dikumpulkan tanpa diperiksa isinya;
- [ ] cadangan basis data tidak ikut dikumpulkan tanpa persetujuan dosen.

Daftar lengkap tersedia pada
[Rubrik dan Security Checklist](<../../05_Asesmen dan Rubrik/Rubrik dan Security Checklist - Secure Academic Data Pipeline.md>).
