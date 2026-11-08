"""Konfigurasi pipeline, dibaca dari lingkungan.

Berkas ini sudah jadi dan tidak perlu diubah pada Pertemuan 10.

Aturan yang sama sudah berlaku sejak Pertemuan 4: yang boleh berada di dalam
kode hanyalah *nama* variabel, tidak pernah nilainya.

    PIPELINE_DB_PASSWORD       <- nama variabel, boleh dibaca siapa saja
    "kata sandi sebenarnya"    <- nilai, hanya ada di berkas .env

Urutan pencarian nilai ada dua: variabel lingkungan proses lebih dahulu, lalu
berkas `.env` pada folder proyek. Tidak ada langkah ketiga. Pipeline yang
kekurangan konfigurasi harus berhenti dengan pesan yang jelas, bukan berjalan
setengah jadi lalu menulis data yang tidak lengkap.

Modul ini sengaja berdiri sendiri dan tidak mengimpor `api/konfigurasi.py`
meskipun keduanya memakai cara baca yang mirip. Pipeline harus tetap dapat
dijalankan pada komputer yang belum memasang FastAPI, dan kedua komponen
memakai akun basis data yang berbeda.
"""

from __future__ import annotations

import os
from pathlib import Path

PROYEK = Path(__file__).resolve().parents[1]
BERKAS_ENV = PROYEK / ".env"


class KonfigurasiTidakLengkap(Exception):
    """Pipeline tidak dapat dijalankan karena konfigurasi kurang."""


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
    pipeline akan mencoba terhubung memakai kata sandi harfiah
    `__GANTI_PASSWORD_OPERATOR__`, lalu gagal dengan pesan yang membingungkan.
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


def _folder(nama_variabel: str, bawaan: str) -> Path:
    """Ubah jalur relatif pada `.env` menjadi jalur mutlak di folder proyek."""
    return PROYEK / ambil(nama_variabel, bawaan).lstrip("./")


# --- Basis data ------------------------------------------------------
# Akun pipeline berbeda dengan akun API. Lihat database/roles.sql bagian 2.3:
# operator_pipeline hanya boleh menulis dan membaca staging_nilai, membaca mata_kuliah,
# dan menulis log. Akun tersebut tidak dapat membaca maupun mengubah
# nilai_akademik.
DB_HOST = ambil("DB_HOST", "127.0.0.1")
DB_PORT = int(ambil("DB_PORT", "3306"))
DB_NAME = ambil("DB_NAME", "secure_academic_lab")
DB_USER = ambil("PIPELINE_DB_USER", "operator_pipeline")

# --- Lokasi berkas ---------------------------------------------------
DIR_RAW = _folder("DATA_RAW_DIR", "./data/raw")
DIR_PROCESSED = _folder("DATA_PROCESSED_DIR", "./data/processed")
DIR_KARANTINA = _folder("DATA_QUARANTINE_DIR", "./data/karantina")
DIR_LOG = _folder("LOG_DIR", "./logs")

BERKAS_MASUKAN = DIR_RAW / "akademik_sintetik_raw.csv"
BERKAS_KELUARAN = DIR_PROCESSED / "hasil_pipeline.csv"
BERKAS_PEMBANDING = DIR_PROCESSED / "akademik_sintetik_bersih.csv"
BERKAS_REFERENSI_MK = PROYEK / "data" / "referensi_mata_kuliah.csv"
BERKAS_MANIFEST = PROYEK / "data" / "manifest.sha256"

# --- Perilaku pipeline -----------------------------------------------
LOG_LEVEL = ambil("LOG_LEVEL", "INFO")

# Jumlah baris yang dikirim ke basis data dalam satu perintah INSERT.
# Angka ini soal kecepatan, bukan keamanan: satu INSERT per baris membuat
# 808 perjalanan bolak-balik ke server yang sebenarnya tidak diperlukan.
UKURAN_BATCH = 200

# Ambang sel kecil untuk laporan agregat. Nilainya sengaja sama dengan ambang
# pada Pertemuan 6 dan pada starter API; ketiganya melindungi orang yang sama.
AMBANG_SEL_KECIL = int(ambil("API_AMBANG_SEL_KECIL", "5"))


def kata_sandi_basis_data() -> str:
    """Dibaca saat dibutuhkan, bukan saat modul diimpor.

    Dengan begitu `python -m pipeline.validasi`, yang sama sekali tidak
    menyentuh basis data, tetap berjalan pada komputer yang belum mengisi
    kata sandi pipeline.
    """
    return ambil("PIPELINE_DB_PASSWORD")
