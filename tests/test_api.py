"""Pengujian negatif starter API — Pertemuan 9.

Menjalankan, dari folder proyek:

    python -m pytest tests/test_api.py -v

Berkas ini ditulis SEBELUM perbaikan, dan karena itu hasilnya merah pada
mulanya. Itu disengaja. Sebuah pengujian yang tidak pernah gagal tidak pernah
membuktikan apa pun; keberadaannya sekadar pelengkap.

Urutan kerja pada pertemuan ini:

    1. jalankan berkas ini, lihat pengujian mana yang merah;
    2. buktikan kelemahannya sendiri melalui Swagger UI, catat pada worksheet;
    3. perbaiki TODO yang bersangkutan;
    4. jalankan lagi sampai hijau.

Sebagian besar pengujian di sini adalah pengujian NEGATIF, yaitu yang
membuktikan bahwa sesuatu DITOLAK. Pengujian positif membuktikan layanan berguna;
pengujian negatif membuktikan layanan aman. Keduanya diperlukan, dan yang
kedua hampir selalu lebih sedikit ditulis orang.

Syarat: MySQL menyala, basis data sudah dimuat, dan `.env` memuat ketiga
kunci API.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api import konfigurasi, keamanan
from api.main import app

MILIK_SENDIRI = "MHS-SYN-0002"   # identitas pemegang API_KEY_MAHASISWA
MILIK_ORANG_LAIN = "MHS-SYN-0004"  # program studi sama, orang berbeda
PRODI_LAIN = "MHS-SYN-0001"      # program studi berbeda


@pytest.fixture(scope="module")
def klien() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def kunci(nama_variabel: str) -> dict:
    nilai = konfigurasi.ambil(nama_variabel, "")
    if not nilai:
        pytest.skip(f"{nama_variabel} belum diisi pada .env")
    return {keamanan.NAMA_HEADER_KUNCI: nilai}


# ---------------------------------------------------------------------
# Autentikasi
# ---------------------------------------------------------------------


def test_tanpa_kunci_ditolak(klien):
    """Permintaan tanpa kunci tidak boleh dilayani."""
    respons = klien.get(f"/nilai/{MILIK_SENDIRI}")
    assert respons.status_code == 401


def test_kunci_salah_ditolak(klien):
    """Kunci yang tidak dikenali tidak boleh dilayani."""
    respons = klien.get(
        f"/nilai/{MILIK_SENDIRI}",
        headers={keamanan.NAMA_HEADER_KUNCI: "kunci-yang-tidak-pernah-dibuat"},
    )
    assert respons.status_code == 401


# ---------------------------------------------------------------------
# Otorisasi tingkat objek — TODO 1
# ---------------------------------------------------------------------


def test_mahasiswa_boleh_membaca_miliknya(klien):
    """Kontrol yang menolak semua orang bukan kontrol, melainkan layanan mati."""
    respons = klien.get(f"/nilai/{MILIK_SENDIRI}", headers=kunci("API_KEY_MAHASISWA"))
    assert respons.status_code == 200
    assert respons.json(), "catatan milik sendiri seharusnya tidak kosong"


def test_mahasiswa_tidak_boleh_membaca_milik_orang_lain(klien):
    """API1:2023 Broken Object Level Authorization.

    Kunci yang sah membuktikan identitas, bukan hak atas objek tertentu.
    """
    respons = klien.get(f"/nilai/{MILIK_ORANG_LAIN}", headers=kunci("API_KEY_MAHASISWA"))
    assert respons.status_code == 403


def test_analis_tidak_boleh_membaca_data_record(klien):
    """Analis bekerja dengan laporan agregat, bukan catatan perorangan."""
    respons = klien.get(f"/nilai/{MILIK_SENDIRI}", headers=kunci("API_KEY_ANALIS"))
    assert respons.status_code == 403


# ---------------------------------------------------------------------
# Validasi masukan — TODO 2
# ---------------------------------------------------------------------


@pytest.mark.parametrize("batas", [0, -5, 100000])
def test_batas_di_luar_rentang_ditolak(klien, batas):
    """Tanpa batas atas, satu permintaan dapat menarik seluruh isi view."""
    respons = klien.get("/nilai", headers=kunci("API_KEY_DOSEN_WALI"), params={"batas": batas})
    assert respons.status_code in (400, 422)


def test_kolom_urut_di_luar_daftar_izin_ditolak(klien):
    """Masukan yang salah dijawab 400, bukan 500.

    Nama kolom tidak dapat diparameterkan. Satu-satunya cara aman adalah
    daftar izin, dan penolakannya harus berupa jawaban yang wajar terhadap
    masukan yang salah, bukan kegagalan program.
    """
    respons = klien.get("/nilai", headers=kunci("API_KEY_DOSEN_WALI"), params={"urut": "nama_mk"})
    assert respons.status_code in (400, 422)


# ---------------------------------------------------------------------
# Kebocoran pada respons — TODO 3 dan TODO 5
# ---------------------------------------------------------------------


def test_status_pendampingan_tidak_pernah_muncul(klien):
    """Atribut paling sensitif pada proyek ini tidak boleh dapat dijangkau.

    Pengujian ini hijau sejak awal, tetapi tetap ditulis karena nilainya baru
    terasa pada hari seseorang menambahkan kolom itu ke view tanpa tahu
    alasannya tidak ada di sana.
    """
    respons = klien.get(f"/nilai/{MILIK_SENDIRI}", headers=kunci("API_KEY_MAHASISWA"))
    assert respons.status_code == 200
    assert "status_pendampingan" not in respons.text


def test_sel_kecil_tidak_menerbitkan_angka(klien):
    """Agregasi tidak dengan sendirinya membuat data menjadi anonim."""
    respons = klien.get("/ringkasan", headers=kunci("API_KEY_ANALIS"))
    assert respons.status_code == 200

    ambang = konfigurasi.AMBANG_SEL_KECIL
    kecil = [sel for sel in respons.json() if sel["jumlah_record"] < ambang]
    assert kecil, (
        "data uji seharusnya memuat sel di bawah ambang; "
        "periksa apakah seed_data.sql sudah dimuat"
    )
    for sel in kecil:
        assert sel["jumlah_lulus"] is None
        assert sel["rata_nilai"] is None
        assert sel["rata_kehadiran"] is None
        assert sel["disensor"] is True


# =====================================================================
# Bagian Anda — tiga pengujian negatif tambahan
#
# Rancang sendiri, lalu ganti `pytest.fail(...)` dengan pengujiannya.
# Setiap pengujian harus membuktikan sebuah akses DITOLAK atau sebuah
# masukan yang salah DIJAWAB DENGAN BENAR, bukan sekadar membuktikan
# jalur yang sudah berhasil.
#
# Beberapa arah yang belum tercakup di atas:
#
#   - dosen wali terhadap mahasiswa di luar program studinya;
#   - semester di luar rentang 1 sampai 14;
#   - arah pengurutan selain ASC dan DESC;
#   - kode mahasiswa yang tidak terdaftar sama sekali — apakah jawabannya
#     dapat dibedakan dari kode yang terdaftar?
#   - respons galat: apakah responsnya menyebutkan nama pustaka atau nama tabel?
#
# Tuliskan pada worksheet bagian I apa yang dibuktikan setiap pengujian
# Anda, dan mengapa pengujian itu perlu ada.
# =====================================================================



def test_negatif_pilihan_anda_1(klien):
    """Dosen wali tidak boleh membaca mahasiswa dari prodi lain."""
    respons = klien.get(
        f"/nilai/{PRODI_LAIN}",
        headers=kunci("API_KEY_DOSEN_WALI"),
    )
    assert respons.status_code == 403


def test_negatif_pilihan_anda_2(klien):
    """Semester di luar rentang 1 sampai 14 harus ditolak."""
    respons = klien.get(
        "/nilai",
        headers=kunci("API_KEY_DOSEN_WALI"),
        params={"semester": 999},
    )
    assert respons.status_code == 422


def test_negatif_pilihan_anda_3(klien):
    """Arah pengurutan selain ASC dan DESC harus ditolak."""
    respons = klien.get(
        "/nilai",
        headers=kunci("API_KEY_DOSEN_WALI"),
        params={"arah": "RANDOM"},
    )
    assert respons.status_code == 400
