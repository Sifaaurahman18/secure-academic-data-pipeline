"""Pembuka koneksi bersama untuk seluruh skrip Pertemuan 7.

Berkas ini sudah jadi dan tidak perlu diubah. Isinya menegakkan satu aturan yang
sudah berlaku sejak Pertemuan 4: kredensial dibaca dari lingkungan atau dari
berkas `.env` proyek, tidak pernah dituliskan ke dalam kode.

Urutan pencarian kata sandi untuk sebuah peran:

    1. variabel lingkungan, misalnya DB_PASSWORD untuk app_service;
    2. berkas .env pada folder proyek secure-academic-data-pipeline;
    3. permintaan interaktif melalui getpass.

Folder proyek ditemukan otomatis: dari folder kerja saat ini beserta folder di
atasnya, dari folder di atas skrip ini (skrip ditaruh di <proyek>/starter/),
atau dari susunan folder mata kuliah. Bila proyek tidak ditemukan, langkah 2
dilewati dan kata sandi ditanyakan.

Langkah ketiga membaca langsung dari konsol, sehingga skrip ini harus
dijalankan pada terminal sungguhan — Git Bash atau terminal bawaan VS Code.
Kata sandi tidak pernah ditulis ke berkas mana pun oleh skrip ini.
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

STARTER = Path(__file__).resolve().parent


def _cari_proyek() -> Path | None:
    """Temukan akar proyek secure-academic-data-pipeline.

    Dicari berurutan: folder kerja saat ini beserta folder di atasnya (skrip
    dijalankan dari akar proyek), folder di atas skrip ini (skrip ditaruh di
    <proyek>/starter/), lalu susunan folder mata kuliah, yaitu
    03_Materi Pertemuan/<pertemuan>/starter/ bersebelahan dengan
    04_Proyek dan Praktikum/.
    """
    kandidat = [Path.cwd(), *Path.cwd().parents, *STARTER.parents]
    if len(STARTER.parents) > 2:
        kandidat.append(STARTER.parents[2] / "04_Proyek dan Praktikum" / "secure-academic-data-pipeline")
    return next((k for k in kandidat if (k / "api").is_dir() and (k / "pipeline").is_dir()), None)


PROYEK = _cari_proyek()
BERKAS_ENV = PROYEK / ".env" if PROYEK else None

BASIS_DATA = "secure_academic_lab"
BASIS_DATA_PULIH = "secure_academic_lab_pulih"

# Peran yang dipakai praktikum, beserta nama variabel kata sandinya.
# admin_lab sengaja tidak ada pada .env.example: akun administrator tidak dipakai
# aplikasi, jadi kata sandinya tidak disimpan di berkas konfigurasi aplikasi dan
# ditanyakan setiap kali dibutuhkan.
PERAN = {
    "app_service": "DB_PASSWORD",
    "operator_pipeline": "PIPELINE_DB_PASSWORD",
    "auditor": "AUDITOR_DB_PASSWORD",
    "analyst": "ANALYST_DB_PASSWORD",
    "admin_lab": "ADMIN_DB_PASSWORD",
}


class TidakDapatTerhubung(Exception):
    """Koneksi gagal dengan sebab yang perlu dibaca pengguna."""


def _baca_env() -> dict:
    """Baca .env proyek sebagai kamus sederhana. Tidak memakai pustaka luar."""
    if BERKAS_ENV is None or not BERKAS_ENV.exists():
        return {}
    isi = {}
    for baris in BERKAS_ENV.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        nama, nilai = baris.split("=", 1)
        isi[nama.strip()] = nilai.strip().strip('"').strip("'")
    return isi


def _kata_sandi(peran: str) -> str:
    nama_variabel = PERAN.get(peran, f"{peran.upper()}_DB_PASSWORD")

    dari_lingkungan = os.environ.get(nama_variabel)
    if dari_lingkungan:
        return dari_lingkungan

    dari_env = _baca_env().get(nama_variabel, "")
    if dari_env and not dari_env.startswith("__GANTI_"):
        return dari_env

    return getpass.getpass(f"Kata sandi MySQL untuk {peran}: ")


def buka(peran: str = "app_service", basis_data: str | None = BASIS_DATA):
    """Buka koneksi sebagai salah satu peran laboratorium.

    Melempar TidakDapatTerhubung dengan pesan yang dapat dibaca, bukan jejak
    galat pustaka, karena pesan itu bagian dari bahan ajar.
    """
    try:
        import mysql.connector
    except ImportError as galat:
        raise TidakDapatTerhubung(
            "pustaka mysql-connector-python belum terpasang.\n"
            "  Jalankan: python -m pip install mysql-connector-python"
        ) from galat

    pengaturan = {
        "host": os.environ.get("DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": peran,
        "password": _kata_sandi(peran),
    }
    if basis_data:
        pengaturan["database"] = basis_data

    try:
        return mysql.connector.connect(**pengaturan)
    except Exception as galat:
        raise TidakDapatTerhubung(
            f"tidak dapat terhubung sebagai {peran} ({galat}).\n"
            "  Periksa: WAMP sudah menyala, basis data sudah dibuat melalui\n"
            "  database/schema.sql, dan akun sudah dibuat melalui database/roles.sql."
        ) from galat
