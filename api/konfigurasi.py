"""Pengaturan starter API, dibaca dari lingkungan.

Berkas ini sudah jadi dan tidak perlu diubah pada Pertemuan 9.

Satu aturan yang berlaku sejak Pertemuan 4 ditegakkan di sini: nilai rahasia
tidak pernah ditulis di dalam kode. Yang boleh berada di kode hanyalah *nama*
variabelnya. Perbedaan itu penting dan sering disalahpahami:

    API_KEY_MAHASISWA          <- nama variabel, bukan rahasia
    "7fK2p...j9Q"              <- nilai, rahasia

Nama variabel boleh dibaca siapa saja, bahkan wajib didokumentasikan supaya
orang lain dapat menjalankan aplikasi ini. Nilainya tidak pernah keluar dari
berkas `.env` yang sudah didaftarkan pada `.gitignore`.

Urutan pencarian nilai:

    1. variabel lingkungan proses;
    2. berkas `.env` pada folder proyek.

Tidak ada langkah ketiga. Berbeda dengan skrip praktikum yang boleh bertanya
melalui `getpass`, sebuah layanan tidak punya siapa-siapa untuk ditanyai saat
layanan itu dijalankan. Layanan yang kekurangan konfigurasi harus berhenti dengan pesan
yang jelas, bukan berjalan setengah jadi.
"""

from __future__ import annotations

import os
from pathlib import Path

PROYEK = Path(__file__).resolve().parents[1]
BERKAS_ENV = PROYEK / ".env"


class KonfigurasiTidakLengkap(Exception):
    """Layanan tidak dapat dijalankan karena konfigurasi kurang."""


def _baca_env() -> dict[str, str]:
    """Baca `.env` sebagai kamus sederhana, tanpa pustaka tambahan."""
    if not BERKAS_ENV.exists():
        return {}
    isi: dict[str, str] = {}
    for baris in BERKAS_ENV.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        nama, nilai = baris.split("=", 1)
        isi[nama.strip()] = nilai.strip().strip('"').strip("'")
    return isi


_ENV = _baca_env()


def ambil(nama: str, bawaan: str | None = None) -> str:
    """Ambil satu nilai konfigurasi.

    Penanda `__GANTI_..._` diperlakukan sebagai nilai kosong. Tanpa aturan ini
    aplikasi akan mencoba terhubung memakai kata sandi harfiah
    `__GANTI_PASSWORD_APP_SERVICE__` lalu gagal dengan pesan yang membingungkan.
    """
    nilai = os.environ.get(nama) or _ENV.get(nama, "")
    if nilai.startswith("__GANTI"):
        nilai = ""
    if not nilai:
        if bawaan is not None:
            return bawaan
        raise KonfigurasiTidakLengkap(
            f"{nama} belum diisi.\n"
            f"  Salin .env.example menjadi .env, lalu isi {nama}.\n"
            "  Nilai rahasia tidak boleh ditulis di dalam kode."
        )
    return nilai


# --- Basis data ------------------------------------------------------
# Akun yang dipakai API adalah app_service: hanya boleh membaca dua view
# dan menulis log. Kolom status_pendampingan tidak dapat dijangkau darinya
# melalui jalur mana pun. Lihat database/roles.sql bagian 2.1.
DB_HOST = ambil("DB_HOST", "127.0.0.1")
DB_PORT = int(ambil("DB_PORT", "3306"))
DB_NAME = ambil("DB_NAME", "secure_academic_lab")
DB_USER = ambil("DB_USER", "app_service")

# --- Perilaku layanan ------------------------------------------------
LOG_DIR = PROYEK / ambil("LOG_DIR", "./logs").lstrip("./")
LOG_LEVEL = ambil("LOG_LEVEL", "INFO")

# Batas jumlah baris yang boleh diminta sekali panggil. Batas ini bukan
# soal kenyamanan: tanpa batas, satu permintaan dapat menarik seluruh isi
# view dalam sekali jalan.
BATAS_BARIS_MAKS = int(ambil("API_BATAS_BARIS_MAKS", "50"))

# Ambang sel kecil untuk laporan agregat. Nilai ini sengaja sama dengan
# ambang yang dipakai Pertemuan 6; keduanya melindungi orang yang sama.
AMBANG_SEL_KECIL = int(ambil("API_AMBANG_SEL_KECIL", "5"))


def kata_sandi_basis_data() -> str:
    """Dibaca saat dibutuhkan, bukan saat modul diimpor.

    Dengan begitu perkakas yang hanya memeriksa struktur kode tidak ikut
    menyentuh kredensial.
    """
    return ambil("DB_PASSWORD")
