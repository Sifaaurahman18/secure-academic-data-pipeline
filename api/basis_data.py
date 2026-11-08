"""Akses basis data untuk starter API.

Berkas ini sudah jadi dan tidak perlu diubah pada Pertemuan 9.

Seluruh query di sini berparameter. Tidak ada satu pun nilai dari pengguna yang
dirangkai ke dalam teks SQL. Aturan itu sudah dibahas pada Pertemuan 7; yang
baru di sini adalah tempat aturan itu diterapkan, yaitu pada layanan yang
menerima permintaan dari luar.

Satu bagian sengaja TIDAK dapat diparameterkan, yaitu nama kolom pada
`ORDER BY`. Penanganannya memakai daftar yang diizinkan, sama seperti
Pertemuan 7. Lihat `KOLOM_URUT_DIIZINKAN` di bawah.

Koneksi dibuka dan ditutup pada setiap permintaan. Untuk layanan sungguhan
pilihan itu boros, dan yang lazim dipakai adalah connection pool. Di sini
kejelasan didahulukan: satu permintaan, satu koneksi, ditutup pada `finally`,
sehingga tidak ada koneksi menggantung ketika sebuah permintaan gagal.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from . import konfigurasi


class BasisDataTidakSiap(Exception):
    """Koneksi gagal dengan sebab yang perlu dibaca pengelola layanan."""


# Kolom yang boleh dipakai untuk mengurutkan hasil pencarian. Nama kolom
# tidak dapat diparameterkan, sehingga satu-satunya cara aman adalah
# mencocokkannya dengan daftar tetap seperti ini.
KOLOM_URUT_DIIZINKAN = ("kode_mahasiswa", "semester", "nilai_angka", "kode_mk")
ARAH_URUT_DIIZINKAN = ("ASC", "DESC")

KOLOM_NILAI = (
    "record_id, kode_mahasiswa, program_studi, semester, kode_mk, nama_mk, "
    "nilai_angka, persentase_kehadiran, status_kelulusan, waktu_pembaruan"
)


@contextmanager
def koneksi() -> Iterator[Any]:
    """Buka koneksi sebagai `app_service`, dan pastikan selalu ditutup."""
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
        raise BasisDataTidakSiap(
            f"tidak dapat terhubung sebagai {konfigurasi.DB_USER} ({galat}).\n"
            "  Periksa: MySQL menyala, skema sudah dibuat, dan akun sudah dibuat\n"
            "  melalui database/roles.sql."
        ) from galat

    try:
        yield sambungan
    finally:
        sambungan.close()


def _ambil_semua(sql: str, nilai: tuple) -> list[dict]:
    with koneksi() as sambungan:
        kursor = sambungan.cursor(dictionary=True)
        try:
            kursor.execute(sql, nilai)
            return kursor.fetchall()
        finally:
            kursor.close()


def nilai_satu_mahasiswa(kode_mahasiswa: str) -> list[dict]:
    """Seluruh catatan nilai milik satu mahasiswa.

    Fungsi ini tidak memutuskan siapa yang berhak membacanya, melainkan hanya
    mengambil data. Keputusan itu milik lapisan otorisasi, dan justru di
    situlah kelemahan yang harus Anda temukan pada Pertemuan 9 berada.
    """
    return _ambil_semua(
        f"SELECT {KOLOM_NILAI} FROM v_nilai_mahasiswa "
        "WHERE kode_mahasiswa = %s ORDER BY semester, kode_mk",
        (kode_mahasiswa,),
    )


def cari_nilai(
    program_studi: str | None,
    semester: int | None,
    kode_mk: str | None,
    urut: str,
    arah: str,
    batas: int,
) -> list[dict]:
    """Pencarian bertingkat dengan seluruh nilai diparameterkan.

    `urut` dan `arah` dicocokkan dengan daftar yang diizinkan lebih dahulu.
    Bila tidak cocok, fungsi ini menolak alih-alih diam-diam memakai nilai
    bawaan: penolakan yang terlihat lebih mudah diperbaiki daripada perilaku
    yang berubah tanpa diketahui.
    """
    if urut not in KOLOM_URUT_DIIZINKAN:
        raise ValueError(f"kolom pengurutan tidak diizinkan: {urut!r}")
    if arah.upper() not in ARAH_URUT_DIIZINKAN:
        raise ValueError(f"arah pengurutan tidak diizinkan: {arah!r}")

    syarat = []
    nilai: list[Any] = []
    if program_studi:
        syarat.append("program_studi = %s")
        nilai.append(program_studi)
    if semester is not None:
        syarat.append("semester = %s")
        nilai.append(semester)
    if kode_mk:
        syarat.append("kode_mk = %s")
        nilai.append(kode_mk)

    where = f"WHERE {' AND '.join(syarat)}" if syarat else ""
    nilai.append(batas)

    # urut dan arah sudah lolos daftar izin di atas, sehingga aman disisipkan.
    # Nilai apa pun yang berasal dari pengguna tetap melalui %s.
    return _ambil_semua(
        f"SELECT {KOLOM_NILAI} FROM v_nilai_mahasiswa {where} "
        f"ORDER BY {urut} {arah.upper()} LIMIT %s",
        tuple(nilai),
    )


def ringkasan_kelulusan(
    program_studi: str | None, semester: int | None
) -> list[dict]:
    """Laporan agregat per program studi, semester, dan mata kuliah."""
    syarat = []
    nilai: list[Any] = []
    if program_studi:
        syarat.append("program_studi = %s")
        nilai.append(program_studi)
    if semester is not None:
        syarat.append("semester = %s")
        nilai.append(semester)

    where = f"WHERE {' AND '.join(syarat)}" if syarat else ""
    return _ambil_semua(
        "SELECT program_studi, semester, kode_mk, jumlah_record, jumlah_lulus, "
        "rata_nilai, rata_kehadiran "
        f"FROM v_ringkasan_kelulusan {where} "
        "ORDER BY program_studi, semester, kode_mk",
        tuple(nilai),
    )


def tulis_log(
    aktor: str,
    aksi: str,
    objek: str | None,
    hasil: str,
    korelasi_id: str | None,
    keterangan: str | None,
) -> None:
    """Tambahkan satu baris ke `log_aktivitas`.

    Akun `app_service` hanya memiliki INSERT pada tabel ini, sehingga tidak dapat
    membaca, mengubah, maupun menghapus catatan. Pembatasan itulah yang
    membuat log dapat dipercaya sebagai bukti: layanan yang disusupi pun
    tidak dapat menghapus jejaknya sendiri.
    """
    with koneksi() as sambungan:
        kursor = sambungan.cursor()
        try:
            kursor.execute(
                "INSERT INTO log_aktivitas "
                "(aktor, komponen, aksi, objek, hasil, korelasi_id, keterangan) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (aktor, "starter_api", aksi, objek, hasil, korelasi_id, keterangan),
            )
            sambungan.commit()
        finally:
            kursor.close()
