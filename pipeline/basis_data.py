"""Akses basis data untuk pipeline.

Berkas ini sudah jadi dan tidak perlu diubah pada Pertemuan 10.

Bentuknya sengaja dibuat mirip dengan `api/basis_data.py`. Perbedaannya hanya
satu, dan justru perbedaan itulah pelajarannya: modul ini terhubung sebagai
`operator_pipeline`, bukan `app_service`. Kedua akun membaca basis data yang
sama, tetapi masing-masing hanya diberi hak yang dibutuhkan pekerjaannya.

Hak `operator_pipeline` menurut `database/roles.sql` bagian 2.3:

    INSERT, SELECT  staging_nilai      menulis batch dan membacanya kembali
    SELECT          mata_kuliah        memeriksa kode mata kuliah
    INSERT          log_aktivitas      mencatat kejadian

Yang tidak diberikan sama pentingnya dengan yang diberikan. Akun ini tidak
dapat menyentuh `nilai_akademik` maupun `mahasiswa`, sehingga kekeliruan pada
pipeline — dan serangan yang berhasil menguasai pipeline — tidak dapat merusak
nilai yang sudah tervalidasi. Pemindahan data dari `staging_nilai` ke
`nilai_akademik` adalah pekerjaan terpisah yang dijalankan akun lain setelah
datanya ditinjau.

Seluruh query di sini berparameter, mengikuti aturan yang sudah berlaku sejak
Pertemuan 7. Tidak ada satu pun nilai dari berkas masukan yang dirangkai ke
dalam teks SQL.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from . import konfigurasi


class BasisDataTidakSiap(Exception):
    """Koneksi gagal dengan sebab yang perlu dibaca pengelola pipeline."""


KOLOM_STAGING = (
    "batch_id",
    "record_id",
    "kode_mahasiswa",
    "program_studi",
    "semester",
    "kode_mk",
    "nilai_angka",
    "persentase_kehadiran",
    "status_kelulusan",
    "status_pendampingan",
    "waktu_pembaruan",
)

PERINTAH_SISIP = (
    "INSERT INTO staging_nilai (" + ", ".join(KOLOM_STAGING) + ") "
    "VALUES (" + ", ".join(["%s"] * len(KOLOM_STAGING)) + ")"
)


@contextmanager
def koneksi() -> Iterator[Any]:
    """Buka koneksi sebagai `operator_pipeline`, dan pastikan selalu ditutup."""
    try:
        import mysql.connector
    except ImportError as galat:  # pragma: no cover - lingkungan tidak lengkap
        raise BasisDataTidakSiap(
            "pustaka mysql-connector-python belum terpasang.\n"
            "  Jalankan: python -m pip install -r requirements.txt"
        ) from galat

    try:
        sambungan = mysql.connector.connect(
            host=konfigurasi.DB_HOST,
            port=konfigurasi.DB_PORT,
            database=konfigurasi.DB_NAME,
            user=konfigurasi.DB_USER,
            password=konfigurasi.kata_sandi_basis_data(),
        )
    except Exception as galat:
        # Pesan galat dari pustaka basis data sering memuat seluruh parameter
        # koneksi. Pesan itu tidak diteruskan apa adanya ke layar maupun ke
        # log; yang disebut hanya nama akunnya.
        raise BasisDataTidakSiap(
            f"tidak dapat terhubung sebagai {konfigurasi.DB_USER}.\n"
            "  Periksa: MySQL menyala, skema sudah dibuat melalui\n"
            "  database/schema.sql, akun sudah dibuat melalui database/roles.sql,\n"
            "  dan PIPELINE_DB_PASSWORD sudah diisi pada .env."
        ) from galat

    try:
        yield sambungan
    finally:
        sambungan.close()
