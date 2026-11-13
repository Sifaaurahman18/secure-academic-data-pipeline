"""Pencatatan kejadian pipeline.

**TODO 4 ada di berkas ini.**

Setiap langkah pipeline mencatat kejadiannya ke dua tempat, sama seperti
starter API:

    1. berkas `logs/pipeline.log`, satu baris JSON per kejadian, dapat dibaca
       tanpa basis data ketika basis data justru sedang bermasalah;
    2. tabel `log_aktivitas`, tempat auditor membacanya.

Yang dicatat: waktu, aktor, komponen, aksi, objek, hasil, `korelasi_id`, dan
keterangan singkat.

Yang tidak pernah dicatat: kata sandi, kunci, dan isi data pribadi. Auditor
perlu mengetahui bahwa sebuah batch dimuat, oleh akun mana, dari berkas dengan
ringkasan apa, dan berapa baris yang ditolak. Auditor tidak perlu mengetahui
nilai seorang mahasiswa, dan sama sekali tidak boleh mengetahui status
pendampingannya.

Log pipeline punya satu risiko yang tidak dimiliki log aplikasi biasa: pesan
galat basis data sering memuat seluruh parameter koneksi, kata sandi termasuk
di dalamnya. Menyalin pesan galat apa adanya ke dalam log adalah cara paling
umum sebuah kata sandi berpindah dari `.env` ke berkas yang dikumpulkan.
Itulah yang harus dicegah TODO 4.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from . import konfigurasi

BERKAS_LOG = konfigurasi.DIR_LOG / "pipeline.log"

KOMPONEN = "pipeline"

# Panjang kolom `keterangan` pada tabel log_aktivitas. Teks yang lebih panjang
# dipotong di sini, bukan dibiarkan ditolak MySQL: kegagalan menulis log tidak
# boleh menjatuhkan pemuatan yang sebenarnya berhasil.
PANJANG_KETERANGAN_MAKS = 255

# Runtutan panjang tanpa spasi menyerupai token atau kunci. Pola ini menjaring
# rahasia yang belum terdaftar pada `.env`, misalnya token yang tidak sengaja
# tertempel ke dalam nama berkas masukan.
#
# Ambang 32 dipilih setelah pola ini terbukti menyensor terlalu banyak. Nama
# berkas keluaran pipeline berbentuk `ringkasan-<korelasi>.csv`, yang panjang
# runtutannya 22 karakter; dengan ambang 20 nama itu ikut hilang dari log, dan
# auditor kehilangan justru keterangan yang dicarinya. Rahasia yang sungguhan
# jauh lebih panjang: `secrets.token_urlsafe(32)` menghasilkan 43 karakter.
#
# Ambang yang lebih tinggi berarti rahasia yang pendek lolos dari pola ini.
# Itulah sebabnya pola ini bukan pertahanan utama, melainkan pelengkap
# `_rahasia_diketahui()` yang mencocokkan nilai sebenarnya.
POLA_MIRIP_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")

# Pasangan kunci-nilai yang menyebut kata sandi, dalam bentuk apa pun yang
# lazim muncul pada pesan galat dan pada string koneksi.
POLA_KATA_SANDI = re.compile(
    r"(?i)\b(password|passwd|pwd|pass|secret)(\s*[=:]\s*)[^\s,;)'\"]+"
)

PENGGANTI = "[RAHASIA]"


def korelasi_baru() -> str:
    """Pengenal singkat yang menyatukan satu jalannya pipeline di semua tempat.

    Nilai yang sama muncul pada berkas log, pada tabel log, pada nama berkas
    karantina, dan pada `batch_id` di tabel staging. Dengan begitu satu batch
    yang bermasalah dapat ditelusuri dari laporan agregat sampai kembali ke
    baris mentahnya, tanpa menebak-nebak berkas mana yang dipakai.
    """
    return uuid.uuid4().hex[:12]


def _rahasia_diketahui() -> tuple[str, ...]:
    """Kumpulkan nilai rahasia yang memang dipegang proses ini.

    Pola umum tidak selalu cukup. Kata sandi yang pendek dan tidak didahului
    kata "password" akan lolos dari kedua pola di atas. Karena proses ini
    memang mengetahui nilainya, nilai itu dapat dicocokkan langsung.

    Kegagalan membaca konfigurasi sengaja diabaikan di sini. Fungsi ini
    dipanggil ketika sesuatu sudah berjalan salah, dan penyensoran log tidak
    boleh ikut gagal hanya karena `.env` belum lengkap.
    """
    nilai: list[str] = []
    for nama in ("PIPELINE_DB_PASSWORD", "DB_PASSWORD", "APP_SECRET"):
        try:
            rahasia = konfigurasi.ambil(nama, "")
        except konfigurasi.KonfigurasiTidakLengkap:  # pragma: no cover
            continue
        if rahasia:
            nilai.append(rahasia)
    return tuple(nilai)


# ---------------------------------------------------------------------
# TODO 4 — Menahan rahasia agar tidak ikut tertulis
# ---------------------------------------------------------------------



def bersihkan(teks: str | None) -> str | None:
    """Membersihkan teks dari informasi rahasia sebelum dicatat ke log."""

    if teks is None:
        return None

    # 1. Sensor nilai rahasia yang diketahui dari konfigurasi.
    for rahasia in _rahasia_diketahui():
        teks = teks.replace(rahasia, PENGGANTI)

    # 2. Sensor pasangan kata sandi, tetapi pertahankan nama kuncinya.
    teks = POLA_KATA_SANDI.sub(
        lambda cocok: cocok.group(1) + cocok.group(2) + PENGGANTI,
        teks
    )

    # 3. Sensor rangkaian karakter yang menyerupai token atau kunci.
    teks = POLA_MIRIP_TOKEN.sub(PENGGANTI, teks)

    return teks


# ---------------------------------------------------------------------
# Sudah jadi — tidak perlu diubah
# ---------------------------------------------------------------------


def catat(
    aksi: str,
    hasil: str,
    objek: str | None = None,
    keterangan: str | None = None,
    korelasi_id: str | None = None,
    sambungan: Any = None,
) -> None:
    """Tulis satu kejadian ke berkas log, dan ke basis data bila tersambung.

    Urutannya disengaja: berkas lebih dahulu, basis data kemudian. Bila
    penulisan ke basis data gagal, kejadiannya sudah terlanjur tercatat di
    berkas. Urutan sebaliknya akan menghilangkan justru catatan yang paling
    dibutuhkan, yaitu catatan tentang saat basis data bermasalah.

    Parameter `hasil` mengikuti nilai kolomnya di MySQL: `berhasil`,
    `ditolak`, atau `gagal`.
    """
    objek_bersih = bersihkan(objek)
    keterangan_bersih = bersihkan(keterangan)
    if keterangan_bersih and len(keterangan_bersih) > PANJANG_KETERANGAN_MAKS:
        keterangan_bersih = keterangan_bersih[: PANJANG_KETERANGAN_MAKS - 3] + "..."

    kejadian = {
        "waktu": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "aktor": konfigurasi.DB_USER,
        "komponen": KOMPONEN,
        "aksi": aksi,
        "objek": objek_bersih,
        "hasil": hasil,
        "korelasi_id": korelasi_id,
        "keterangan": keterangan_bersih,
    }

    konfigurasi.DIR_LOG.mkdir(parents=True, exist_ok=True)
    with BERKAS_LOG.open("a", encoding="utf-8") as berkas:
        berkas.write(json.dumps(kejadian, ensure_ascii=False) + "\n")

    if sambungan is None:
        return

    try:
        kursor = sambungan.cursor()
        kursor.execute(
            "INSERT INTO log_aktivitas "
            "(aktor, komponen, aksi, objek, hasil, korelasi_id, keterangan) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                konfigurasi.DB_USER,
                KOMPONEN,
                aksi,
                objek_bersih,
                hasil,
                korelasi_id,
                keterangan_bersih,
            ),
        )
        kursor.close()
    except Exception as galat:  # pragma: no cover - bergantung pada server
        # Log yang gagal ditulis tidak boleh menjatuhkan pekerjaan yang
        # sebenarnya berhasil. Kegagalannya sendiri tetap dicatat ke berkas,
        # supaya lubang pada catatan basis data dapat diketahui kemudian.
        with BERKAS_LOG.open("a", encoding="utf-8") as berkas:
            berkas.write(
                json.dumps(
                    {
                        "waktu": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "komponen": KOMPONEN,
                        "aksi": "catat_ke_basis_data",
                        "hasil": "gagal",
                        "korelasi_id": korelasi_id,
                        "keterangan": bersihkan(str(galat)),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
