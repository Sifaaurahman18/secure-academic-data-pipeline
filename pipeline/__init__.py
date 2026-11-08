"""Pipeline Secure Academic Data Pipeline — Pertemuan 10 dan 11.

Paket ini memindahkan data akademik sintetik dari berkas mentah ke basis data
laboratorium melalui tiga langkah yang dijalankan berurutan:

    python -m pipeline.validasi      berkas mentah  -> processed dan karantina
    python -m pipeline.muat          hasil validasi -> tabel staging_nilai
    python -m pipeline.ringkas       tabel staging  -> laporan agregat

Modul pendukungnya:

    konfigurasi.py   nilai konfigurasi dan jalur berkas, dibaca dari lingkungan
    keutuhan.py      ringkasan SHA-256 dan gerbang keutuhan berkas masukan
    aturan.py        aturan validasi satu baris
    pencatatan.py    pencatatan kejadian pipeline

Lima bagian bertanda TODO harus Anda kerjakan. Rinciannya ada pada modul
masing-masing, dan urutannya mengikuti urutan pipeline berjalan:

    TODO 1  gerbang keutuhan          keutuhan.py
    TODO 2  aturan validasi           aturan.py
    TODO 3  pemeriksaan duplikat      validasi.py
    TODO 4  penyensoran rahasia       pencatatan.py
    TODO 5  pemuatan yang aman gagal  muat.py

Akun basis data yang dipakai paket ini adalah `operator_pipeline`. Akun
tersebut hanya boleh menulis dan membaca `staging_nilai`, membaca `mata_kuliah`, dan
menulis `log_aktivitas`. Akun tersebut tidak dapat menyentuh tabel
`nilai_akademik` sama sekali. Pembatasan itu disengaja: pipeline yang salah
sekalipun tidak boleh mampu merusak nilai yang sudah tervalidasi.
"""
