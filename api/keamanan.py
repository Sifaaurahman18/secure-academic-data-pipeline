"""Identitas pemanggil dan keputusan otorisasi starter API.

Berkas ini memuat **TODO 1**, kelemahan terpenting pada Pertemuan 9.

Dua hal yang sering dianggap satu padahal berbeda:

    Authentication  — siapa Anda?                    Dijawab oleh kunci API.
    Authorization   — apa yang boleh Anda lakukan?   Dijawab oleh aturan di bawah.

Kunci API yang sah hanya membuktikan hal pertama. Sebuah layanan yang berhenti
di situ akan melayani permintaan apa pun dari siapa pun yang punya kunci sah,
termasuk permintaan atas data milik orang lain. OWASP API Security Top 10 (2023)
menempatkan kelemahan itu pada urutan pertama: API1:2023 Broken Object Level
Authorization.

Tentang kunci API. Mekanisme ini dipilih supaya perhatian tertuju pada
otorisasi, bukan pada seluk-beluk protokol. Layanan sungguhan memakai OAuth 2.0
atau OpenID Connect dengan token berumur pendek. Yang tidak berubah antara
keduanya: token membuktikan identitas, dan identitas saja tidak pernah cukup.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from . import konfigurasi


@dataclass(frozen=True)
class Identitas:
    """Siapa yang memanggil, dan atas nama apa."""

    nama: str
    peran: str
    kode_mahasiswa: str | None = None
    program_studi: str | None = None


class TidakDikenali(Exception):
    """Kunci API tidak ada atau tidak cocok."""


# Pemetaan kunci ke identitas.
#
# Yang tertulis di sini adalah NAMA variabel lingkungan, bukan nilainya.
# Nilainya dibaca dari `.env` dan tidak pernah masuk ke kode maupun ke log.
# Pemetaan ini sendiri bukan rahasia: justru harus dapat dibaca agar
# aturan akses dapat diperiksa orang lain.
PENGGUNA: dict[str, Identitas] = {
    "API_KEY_MAHASISWA": Identitas(
        nama="mahasiswa_demo",
        peran="mahasiswa",
        kode_mahasiswa="MHS-SYN-0002",
        program_studi="Sains Data",
    ),
    "API_KEY_DOSEN_WALI": Identitas(
        nama="dosen_wali_demo",
        peran="dosen_wali",
        program_studi="Sains Data",
    ),
    "API_KEY_ANALIS": Identitas(
        nama="analis_demo",
        peran="analis",
    ),
}

NAMA_HEADER_KUNCI = "X-API-Key"


def identitas_dari_kunci(kunci: str | None) -> Identitas:
    """Cocokkan kunci yang dikirim dengan kunci yang dikonfigurasi.

    Perbandingan memakai `secrets.compare_digest`, bukan `==`. Operator `==`
    berhenti pada karakter pertama yang berbeda, sehingga waktu yang dibutuhkan
    membocorkan jumlah karakter awal yang sudah benar. Selisihnya sangat
    kecil, tetapi dapat diukur, dan pada layanan yang dapat dipanggil berulang
    kali selisih kecil itu cukup untuk menebak kunci karakter demi karakter.
    """
    if not kunci:
        raise TidakDikenali("header X-API-Key tidak dikirim")

    for nama_variabel, identitas in PENGGUNA.items():
        kunci_sah = konfigurasi.ambil(nama_variabel, "")
        if not kunci_sah:
            continue
        if secrets.compare_digest(kunci, kunci_sah):
            return identitas

    raise TidakDikenali("kunci API tidak dikenali")


def daftar_kunci_terpasang() -> list[str]:
    """Nama variabel kunci yang sudah terisi. Nilainya tidak pernah dikembalikan."""
    return [nama for nama in PENGGUNA if konfigurasi.ambil(nama, "")]


# =====================================================================
# TODO 1 — Otorisasi tingkat objek (API1:2023)
#
# Fungsi di bawah ini menentukan apakah seorang pemanggil boleh membaca
# catatan nilai milik SATU mahasiswa tertentu. Sekarang fungsi itu mengembalikan
# True untuk siapa pun. Akibatnya, setiap pemegang kunci yang sah dapat
# membaca nilai mahasiswa mana pun hanya dengan mengganti kode pada URL.
#
# Buktikan lebih dahulu, baru perbaiki. Langkahnya ada pada worksheet
# bagian D. Jangan memperbaiki kelemahan yang belum Anda lihat sendiri.
#
# Aturan yang harus berlaku setelah perbaikan:
#
#   peran "mahasiswa"   : hanya boleh membaca catatan miliknya sendiri,
#                         yaitu ketika kode_mahasiswa sama dengan
#                         identitas.kode_mahasiswa.
#   peran "dosen_wali"  : hanya boleh membaca mahasiswa pada program studi
#                         yang sama dengan identitas.program_studi.
#   peran "analis"      : tidak boleh membaca data tingkat record sama
#                         sekali. Analis bekerja dengan laporan agregat.
#   peran lain          : ditolak.
#
# Aturan yang sama berlaku pada endpoint pencarian `GET /nilai` di
# api/main.py, karena endpoint itu juga mengembalikan catatan perorangan.
# Tulis fungsi kedua, misalnya `boleh_mencari_nilai()`, dengan bentuk yang
# sama: dosen_wali hanya pada program studinya sendiri, peran lain ditolak.
#
# Perhatikan bentuk aturan terakhir. Tulis fungsi ini sebagai daftar izin
# yang diakhiri penolakan, bukan daftar larangan yang diakhiri pengizinan.
# Peran baru yang ditambahkan bulan depan lalu terlupa didaftarkan akan
# ditolak dengan sendirinya, bukan diizinkan dengan sendirinya.
#
# Catatan tentang urutan. Pemanggil fungsi ini sudah mengambil datanya dari
# basis data lebih dahulu, karena program_studi pemilik catatan hanya
# diketahui setelah data dibaca. Itu wajar: untuk memutuskan apakah sebuah
# objek boleh diberikan, objek itu memang harus diambil dulu. Yang tidak
# boleh terjadi adalah objek itu ikut terkirim tanpa keputusan ini dijalankan.
# =====================================================================


def boleh_membaca_mahasiswa(
    identitas: Identitas,
    kode_mahasiswa: str,
    program_studi: str | None,
) -> bool:
    """Apakah `identitas` boleh membaca catatan milik `kode_mahasiswa`?"""

    # Mahasiswa hanya boleh membaca nilai miliknya sendiri.
    if identitas.peran == "mahasiswa":
        return identitas.kode_mahasiswa == kode_mahasiswa

    # Dosen wali hanya boleh membaca mahasiswa dari program studinya.
    if identitas.peran == "dosen_wali":
        return (
            program_studi is not None
            and identitas.program_studi == program_studi
        )

    # Analis dan peran lainnya tidak boleh membaca data individu.
    return False

def boleh_mencari_nilai(identitas: Identitas) -> bool:
    """Apakah identitas boleh mencari catatan nilai perorangan?"""

    # Hanya dosen wali yang boleh mencari nilai.
    return identitas.peran == "dosen_wali"


def boleh_membaca_ringkasan(identitas: Identitas) -> bool:
    """Siapa yang boleh membaca laporan agregat.

    Bagian ini sudah benar dan dipakai sebagai pembanding: perhatikan bahwa
    fungsi itu menyebutkan peran yang diizinkan lalu menolak sisanya, bukan
    sebaliknya. TODO 1 harus berbentuk sama.
    """
    return identitas.peran in ("dosen_wali", "analis", "mahasiswa")
