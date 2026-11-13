
"""Aturan validasi satu baris data akademik.

TODO 2: Aturan validasi satu baris berdasarkan kamus data proyek.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from . import konfigurasi

# --- Daftar nilai yang sah -------------------------------------------

KOLOM_WAJIB = (
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

PROGRAM_STUDI_BAKU = (
    "Sains Data",
    "Ekonomi Syariah",
    "Akuntansi Syariah",
    "Manajemen Bisnis Syariah",
)

SEMESTER_SAH = (1, 3, 5, 7)
STATUS_KELULUSAN_SAH = ("Lulus", "Tidak Lulus")
STATUS_PENDAMPINGAN_SAH = ("Ya", "Tidak")

POLA_KODE_MAHASISWA = re.compile(r"^MHS-SYN-\d{4}$")
BENTUK_WAKTU = "%Y-%m-%dT%H:%M:%S"

NILAI_MINIMUM, NILAI_MAKSIMUM = 0, 100
BATAS_NILAI_LULUS = 60
BATAS_KEHADIRAN_LULUS = 75

# --- Katalog aturan --------------------------------------------------

ATURAN: dict[str, str] = {
    "WAJIB_KOSONG": "Satu atau lebih kolom wajib tidak terisi.",
    "KODE_MAHASISWA_TIDAK_BERPOLA": "Kode mahasiswa tidak berbentuk MHS-SYN-nnnn.",
    "PROGRAM_STUDI_TIDAK_BAKU": "Program studi tidak sama dengan penulisan baku.",
    "SEMESTER_TIDAK_SAH": "Semester bukan salah satu dari 1, 3, 5, atau 7.",
    "KODE_MK_TIDAK_TERDAFTAR": "Kode mata kuliah tidak ada pada berkas referensi.",
    "NILAI_BUKAN_BILANGAN": "Nilai angka bukan bilangan bulat.",
    "NILAI_DI_LUAR_RENTANG": "Nilai angka di luar rentang 0 sampai 100.",
    "KEHADIRAN_BUKAN_BILANGAN": "Persentase kehadiran bukan bilangan bulat.",
    "KEHADIRAN_DI_LUAR_RENTANG": "Persentase kehadiran di luar rentang 0 sampai 100.",
    "STATUS_KELULUSAN_TIDAK_SAH": "Status kelulusan bukan Lulus atau Tidak Lulus.",
    "KELULUSAN_TIDAK_KONSISTEN": "Status kelulusan tidak sesuai nilai dan kehadirannya.",
    "STATUS_PENDAMPINGAN_TIDAK_SAH": "Status pendampingan bukan Ya atau Tidak.",
    "WAKTU_TIDAK_SAH": "Waktu pembaruan tidak berbentuk YYYY-MM-DDTHH:MM:SS.",
}

ATURAN_ANTARBARIS: dict[str, str] = {
    "RECORD_ID_GANDA": "record_id sudah dipakai baris lain pada berkas yang sama.",
    "KUNCI_ALAMI_GANDA": "Kombinasi kode_mahasiswa, kode_mk, dan semester sudah ada.",
}


# --- Fungsi pembantu -------------------------------------------------


def bilangan_bulat(teks: str) -> int | None:
    """Ubah teks menjadi bilangan bulat, atau None bila gagal."""
    try:
        return int(teks.strip())
    except (ValueError, AttributeError):
        return None


def waktu_sah(teks: str) -> bool:
    """Periksa format dan keabsahan tanggal waktu."""
    try:
        datetime.strptime(teks.strip(), BENTUK_WAKTU)
    except (ValueError, AttributeError):
        return False
    return True


def tentukan_kelulusan(nilai: int, kehadiran: int) -> str:
    """Tentukan status kelulusan berdasarkan nilai dan kehadiran."""
    if nilai >= BATAS_NILAI_LULUS and kehadiran >= BATAS_KEHADIRAN_LULUS:
        return "Lulus"
    return "Tidak Lulus"


def muat_kode_mk_sah(berkas: Path | None = None) -> set[str]:
    """Baca kode mata kuliah yang sah dari berkas referensi."""
    sumber = berkas or konfigurasi.BERKAS_REFERENSI_MK
    with sumber.open(encoding="utf-8", newline="") as berkas_referensi:
        return {
            baris["kode_mk"]
            for baris in csv.DictReader(berkas_referensi)
        }


# ---------------------------------------------------------------------
# TODO 2 — Aturan validasi satu baris
# ---------------------------------------------------------------------


def periksa_baris(
    baris: dict[str, str],
    kode_mk_sah: set[str],
) -> list[str]:
    """Periksa satu baris dan kembalikan seluruh kode aturan yang dilanggar."""

    temuan: list[str] = []

    # 1. Pemeriksaan kolom wajib.
    # Semua kolom kosong hanya menghasilkan satu kode WAJIB_KOSONG.
    kolom_kosong = {
        kolom
        for kolom in KOLOM_WAJIB
        if not str(baris.get(kolom, "") or "").strip()
    }

    if kolom_kosong:
        temuan.append("WAJIB_KOSONG")

    # 2. Format kode mahasiswa.
    kode_mahasiswa = str(baris.get("kode_mahasiswa", "") or "").strip()
    if (
        "kode_mahasiswa" not in kolom_kosong
        and not POLA_KODE_MAHASISWA.fullmatch(kode_mahasiswa)
    ):
        temuan.append("KODE_MAHASISWA_TIDAK_BERPOLA")

    # 3. Program studi.
    program_studi = str(baris.get("program_studi", "") or "").strip()
    if (
        "program_studi" not in kolom_kosong
        and program_studi not in PROGRAM_STUDI_BAKU
    ):
        temuan.append("PROGRAM_STUDI_TIDAK_BAKU")

    # 4. Semester.
    semester_teks = str(baris.get("semester", "") or "").strip()
    if "semester" not in kolom_kosong:
        semester = bilangan_bulat(semester_teks)
        if semester not in SEMESTER_SAH:
            temuan.append("SEMESTER_TIDAK_SAH")

    # 5. Kode mata kuliah.
    kode_mk = str(baris.get("kode_mk", "") or "").strip()
    if (
        "kode_mk" not in kolom_kosong
        and kode_mk not in kode_mk_sah
    ):
        temuan.append("KODE_MK_TIDAK_TERDAFTAR")

    # 6. Nilai angka.
    nilai = None
    if "nilai_angka" not in kolom_kosong:
        nilai_teks = str(baris.get("nilai_angka", "")).strip()
        nilai = bilangan_bulat(nilai_teks)

        if nilai is None:
            temuan.append("NILAI_BUKAN_BILANGAN")
        elif not NILAI_MINIMUM <= nilai <= NILAI_MAKSIMUM:
            temuan.append("NILAI_DI_LUAR_RENTANG")

    # 7. Persentase kehadiran.
    kehadiran = None
    if "persentase_kehadiran" not in kolom_kosong:
        kehadiran_teks = str(
            baris.get("persentase_kehadiran", "")
        ).strip()

        kehadiran = bilangan_bulat(kehadiran_teks)

        if kehadiran is None:
            temuan.append("KEHADIRAN_BUKAN_BILANGAN")
        elif not NILAI_MINIMUM <= kehadiran <= NILAI_MAKSIMUM:
            temuan.append("KEHADIRAN_DI_LUAR_RENTANG")

    # 8. Status kelulusan.
    status_kelulusan = str(
        baris.get("status_kelulusan", "") or ""
    ).strip()

    status_kelulusan_valid = (
        "status_kelulusan" not in kolom_kosong
        and status_kelulusan in STATUS_KELULUSAN_SAH
    )

    if (
        "status_kelulusan" not in kolom_kosong
        and not status_kelulusan_valid
    ):
        temuan.append("STATUS_KELULUSAN_TIDAK_SAH")

    # 9. Konsistensi kelulusan.
    # Hanya diperiksa jika nilai dan kehadiran valid dalam rentang.
    nilai_valid = (
        nilai is not None
        and NILAI_MINIMUM <= nilai <= NILAI_MAKSIMUM
    )

    kehadiran_valid = (
        kehadiran is not None
        and NILAI_MINIMUM <= kehadiran <= NILAI_MAKSIMUM
    )

    if nilai_valid and kehadiran_valid and status_kelulusan_valid:
        status_seharusnya = tentukan_kelulusan(nilai, kehadiran)

        if status_kelulusan != status_seharusnya:
            temuan.append("KELULUSAN_TIDAK_KONSISTEN")

    # 10. Status pendampingan.
    status_pendampingan = str(
        baris.get("status_pendampingan", "") or ""
    ).strip()

    if (
        "status_pendampingan" not in kolom_kosong
        and status_pendampingan not in STATUS_PENDAMPINGAN_SAH
    ):
        temuan.append("STATUS_PENDAMPINGAN_TIDAK_SAH")

    # 11. Waktu pembaruan.
    waktu = str(baris.get("waktu_pembaruan", "") or "").strip()

    if (
        "waktu_pembaruan" not in kolom_kosong
        and not waktu_sah(waktu)
    ):
        temuan.append("WAKTU_TIDAK_SAH")

    return temuan
