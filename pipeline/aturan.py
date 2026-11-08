"""Aturan validasi satu baris data akademik.

**TODO 2 ada di berkas ini.**

Seluruh aturan di sini berasal dari kamus data proyek bagian 2 dan 3
(`data/kamus_data_proyek.md`). Kamus itulah sumber kebenarannya; berkas ini
hanya menuliskannya kembali dalam bentuk yang dapat dijalankan. Bila keduanya
berbeda, kamus yang benar dan berkas ini yang harus diperbaiki.

Satu rancangan yang perlu diperhatikan: fungsi di sini **tidak mencetak apa
pun dan tidak menulis berkas apa pun**. Fungsi ini hanya menerima satu baris
dan mengembalikan daftar kode aturan yang dilanggar. Pemisahan itu membuat
aturan dapat diuji satu per satu tanpa menjalankan seluruh pipeline, dan
membuat keputusan tentang apa yang dilakukan terhadap baris bermasalah —
ditolak, dikarantina, atau dihentikan — berada di satu tempat, yaitu
`validasi.py`.

Berkas mentah proyek memuat 23 baris bermasalah yang disengaja. Dua puluh satu
di antaranya melanggar aturan pada berkas ini. Dua sisanya sah bila dibaca
sendiri-sendiri dan hanya bermasalah dalam hubungannya dengan baris lain;
keduanya ditangani TODO 3 pada `validasi.py`.
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
# Kode inilah yang ditulis ke berkas karantina dan dihitung pada ringkasan.
# Kode yang tetap sama antarjalannya membuat dua hasil pipeline dapat
# dibandingkan; kalimat penjelasan yang berubah-ubah tidak dapat.

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

# Aturan yang tidak dapat diperiksa dari satu baris saja. Sebuah baris dapat
# melanggar keduanya sekaligus, dan pada berkas mentah proyek memang ada satu
# baris semacam itu.
ATURAN_ANTARBARIS: dict[str, str] = {
    "RECORD_ID_GANDA": "record_id sudah dipakai baris lain pada berkas yang sama.",
    "KUNCI_ALAMI_GANDA": "Kombinasi kode_mahasiswa, kode_mk, dan semester sudah ada.",
}


# ---------------------------------------------------------------------
# Sudah jadi — pembantu yang boleh langsung Anda pakai
# ---------------------------------------------------------------------


def bilangan_bulat(teks: str) -> int | None:
    """Ubah teks menjadi bilangan bulat, atau `None` bila tidak dapat diubah.

    Mengembalikan `None` alih-alih melemparkan pengecualian membuat pemanggil
    dapat membedakan "bukan bilangan" dari "bilangan yang di luar rentang".
    Keduanya cacat, tetapi sebabnya berbeda dan perbaikannya juga berbeda.
    """
    try:
        return int(teks.strip())
    except (ValueError, AttributeError):
        return None


def waktu_sah(teks: str) -> bool:
    """Periksa apakah teks berbentuk `YYYY-MM-DDTHH:MM:SS` dan tanggalnya ada.

    Pemeriksaan bentuk saja tidak cukup. Teks `2026-13-45T99:00:00` memenuhi
    bentuknya, tetapi bulan ke-13 dan tanggal 45 tidak pernah ada.
    `datetime.strptime` memeriksa keduanya sekaligus.
    """
    try:
        datetime.strptime(teks.strip(), BENTUK_WAKTU)
    except (ValueError, AttributeError):
        return False
    return True


def tentukan_kelulusan(nilai: int, kehadiran: int) -> str:
    """Hitung status kelulusan dari nilai dan kehadiran.

    Aturan ini adalah model latihan mata kuliah, bukan ketentuan akademik yang
    berlaku di program studi. Karena status kelulusan dapat dihitung ulang dari
    kolom lain, kolom tersebut berguna untuk melatih pemeriksaan konsistensi:
    catatan yang menyatakan `Lulus` padahal nilainya 41 menandakan data telah
    berubah, salah dimasukkan, atau berasal dari sumber yang tidak dapat
    dipercaya.
    """
    if nilai >= BATAS_NILAI_LULUS and kehadiran >= BATAS_KEHADIRAN_LULUS:
        return "Lulus"
    return "Tidak Lulus"


def muat_kode_mk_sah(berkas: Path | None = None) -> set[str]:
    """Baca kode mata kuliah yang sah dari berkas referensi.

    Daftar ini dibaca dari berkas, bukan ditulis di dalam kode, supaya
    penambahan mata kuliah baru tidak menuntut kode pipeline diubah.
    """
    sumber = berkas or konfigurasi.BERKAS_REFERENSI_MK
    with sumber.open(encoding="utf-8", newline="") as berkas_referensi:
        return {baris["kode_mk"] for baris in csv.DictReader(berkas_referensi)}


# ---------------------------------------------------------------------
# TODO 2 — Aturan validasi satu baris
# ---------------------------------------------------------------------


def periksa_baris(baris: dict[str, str], kode_mk_sah: set[str]) -> list[str]:
    """Kembalikan daftar kode aturan yang dilanggar satu baris.

    Daftar kosong berarti baris tersebut sah. Kode yang dikembalikan harus
    berasal dari `ATURAN`; kode di luar daftar itu akan ditolak pemeriksa
    hasil.

    Contoh bentuk yang diharapkan, memakai satu aturan sebagai contoh:

        temuan: list[str] = []
        if baris["status_pendampingan"] not in STATUS_PENDAMPINGAN_SAH:
            temuan.append("STATUS_PENDAMPINGAN_TIDAK_SAH")
        ...
        return temuan

    Tiga hal yang menentukan benar atau tidaknya jawaban Anda:

      1. **Satu kolom kosong hanya menghasilkan satu temuan.** Kolom
         `nilai_angka` yang kosong melanggar `WAJIB_KOSONG`, dan pemeriksaan
         lain atas kolom itu dilewati. Melaporkan bahwa teks kosong juga
         "bukan bilangan" dan juga "di luar rentang" tidak menambah informasi
         apa pun bagi orang yang harus memperbaiki datanya.

      2. **Konsistensi kelulusan hanya diperiksa bila bahan hitungnya sah.**
         Bandingkan `status_kelulusan` dengan `tentukan_kelulusan()` hanya
         ketika nilai dan kehadiran sudah terbukti bilangan bulat dalam
         rentang 0 sampai 100, dan status kelulusannya sendiri sudah ada pada
         `STATUS_KELULUSAN_SAH`. Baris yang nilainya `N/A` tidak dapat
         dinyatakan tidak konsisten, karena tidak ada yang dapat dihitung.

      3. **Setiap baris cacat pada berkas mentah proyek melanggar tepat satu
         aturan.** Sifat itu disengaja oleh pembuat datasetnya. Bila jawaban
         Anda menghasilkan dua kode untuk satu baris, hampir pasti butir 1
         atau butir 2 di ataslah yang terlewat.

    Petunjuk urutan pengerjaan: kerjakan `WAJIB_KOSONG` lebih dahulu, lalu
    aturan per kolom, dan simpan `KELULUSAN_TIDAK_KONSISTEN` untuk paling
    akhir karena aturan itu bergantung pada hasil aturan sebelumnya.

    Jumlah temuan yang benar pada berkas mentah proyek, sebagai pembanding:

        WAJIB_KOSONG                    2      KODE_MK_TIDAK_TERDAFTAR        2
        NILAI_BUKAN_BILANGAN            2      PROGRAM_STUDI_TIDAK_BAKU       3
        NILAI_DI_LUAR_RENTANG           3      WAKTU_TIDAK_SAH                2
        KEHADIRAN_DI_LUAR_RENTANG       2      SEMESTER_TIDAK_SAH             1
        STATUS_KELULUSAN_TIDAK_SAH      1      STATUS_PENDAMPINGAN_TIDAK_SAH  1
        KELULUSAN_TIDAK_KONSISTEN       2                             jumlah  21

    Dua aturan sisanya, `KODE_MAHASISWA_TIDAK_BERPOLA` dan
    `KEHADIRAN_BUKAN_BILANGAN`, tidak pernah dilanggar berkas mentah proyek.
    Keduanya tetap wajib Anda terapkan: aturan ada karena kamus data
    mensyaratkannya, bukan karena kebetulan ada data yang melanggarnya hari
    ini. Pemeriksa hasil mengujinya memakai baris buatan.
    """
    # TODO 2: ganti baris berikut dengan pemeriksaan yang sebenarnya.
    return []
