
"""Keutuhan berkas: ringkasan SHA-256 dan gerbang masukan.

**TODO 1 ada di berkas ini.** Kerjakan bagian A lebih dahulu, baru bagian B.

Pertemuan 1 memperkenalkan checksum sebagai cara membuktikan bahwa sebuah
berkas tidak berubah. Pertemuan 10 memakainya sebagai kontrol: pipeline
menolak bekerja pada berkas yang berbeda dari yang tercatat.

Perbedaan antara "menghitung checksum" dan "memiliki gerbang keutuhan" adalah
inti pertemuan ini. Banyak sistem melakukan yang pertama, mencatat hasilnya,
lalu tetap memproses berkasnya apa pun hasilnya. Angka yang tidak pernah
dipakai untuk menghentikan apa pun bukan kontrol, melainkan hiasan.

Yang dijawab checksum:

    Apakah berkas ini sama persis dengan berkas yang saya catat sebelumnya?

Yang tidak dijawab checksum:

    Apakah isi berkas ini benar? Apakah berkas ini berasal dari pihak yang
    berwenang? Apakah nilai di dalamnya masuk akal?

Pertanyaan pertama dijawab `aturan.py`. Dua pertanyaan berikutnya menuntut
tanda tangan digital dan tata kelola sumber data, bukan sekadar hash.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from . import konfigurasi

# Dibaca sekaligus 1 MiB, bukan seluruh berkas sekaligus. Berkas praktikum ini
# kecil, tetapi kebiasaan membaca bertahap yang membuat kode yang sama tetap
# berjalan ketika berkasnya berukuran belasan gigabita.
UKURAN_POTONG = 1024 * 1024


class KeutuhanGagal(Exception):
    """Berkas masukan tidak sama dengan yang tercatat pada manifest."""


def kunci_manifest(berkas: Path) -> str:
    """Ubah jalur berkas menjadi bentuk yang dipakai manifest.

    Manifest menyimpan jalur relatif terhadap folder proyek dengan garis miring
    biasa, sehingga berkas yang sama menghasilkan kunci yang sama di Windows
    maupun di Linux.
    """
    return berkas.resolve().relative_to(konfigurasi.PROYEK).as_posix()


def baca_manifest(berkas_manifest: Path | None = None) -> dict[str, str]:
    """Baca manifest menjadi pemetaan jalur berkas ke ringkasan SHA-256.

    Bentuk setiap barisnya mengikuti keluaran `sha256sum`:

        <ringkasan heksadesimal> *<jalur relatif>
    """
    sumber = berkas_manifest or konfigurasi.BERKAS_MANIFEST
    if not sumber.exists():
        raise KeutuhanGagal(
            f"manifest tidak ditemukan di {sumber}.\n"
            "  Jalankan: python tools/buat_dataset.py"
        )

    catatan: dict[str, str] = {}
    for baris in sumber.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or " *" not in baris:
            continue
        ringkasan, jalur = baris.split(" *", 1)
        catatan[jalur.strip()] = ringkasan.strip().lower()
    return catatan


# ---------------------------------------------------------------------
# TODO 1 bagian A — Menghitung ringkasan SHA-256
# ---------------------------------------------------------------------


def hitung_sha256(berkas: Path) -> str:
    """Hitung ringkasan SHA-256 sebuah berkas secara bertahap."""
    sha256 = hashlib.sha256()

    with berkas.open("rb") as sumber:
        while True:
            potongan = sumber.read(UKURAN_POTONG)

            if not potongan:
                break

            sha256.update(potongan)

    return sha256.hexdigest().lower()


# ---------------------------------------------------------------------
# TODO 1 bagian B — Menjadikan hitungan itu sebuah gerbang
# ---------------------------------------------------------------------


def gerbang_keutuhan(berkas: Path) -> str:
    """Pastikan berkas masukan sama dengan yang tercatat, lalu kembalikan ringkasannya.

    Yang harus dipenuhi:

      1. berkas yang tidak tercatat pada manifest ditolak. Berkas tak dikenal
         bukan hal netral: justru berkas semacam itulah yang paling mungkin
         diselipkan seseorang;
      2. berkas yang ringkasannya berbeda dari catatan ditolak;
      3. penolakan dilakukan dengan `raise KeutuhanGagal(...)`, disertai pesan
         yang menyebut nama berkas serta ringkasan yang dicatat dan yang
         ditemukan. Pemanggil tidak boleh perlu menebak apa yang berbeda;
      4. berkas yang cocok mengembalikan ringkasannya, karena `muat.py`
         mencatat nilai itu sebagai asal-usul setiap batch.

    Baris `print` di bawah ini adalah bentuk yang harus Anda ganti. Bentuk itu
    memberi tahu, tetapi tidak menghentikan apa pun, sehingga pipeline tetap
    memproses berkas yang sudah berubah. Worksheet bagian C menanyakan
    mengapa peringatan semacam ini justru lebih berbahaya daripada tidak ada
    pemeriksaan sama sekali.
    """
    tercatat = baca_manifest().get(kunci_manifest(berkas))
    sebenarnya = hitung_sha256(berkas)

    if tercatat is None:
        raise KeutuhanGagal(
            f"{berkas.name} tidak tercatat pada manifest. "
            f"Ringkasan ditemukan: {sebenarnya}"
        )

    if tercatat != sebenarnya:
        raise KeutuhanGagal(
            f"Ringkasan {berkas.name} tidak sesuai manifest. "
            f"Tercatat: {tercatat}; ditemukan: {sebenarnya}"
        )

    return sebenarnya


# ---------------------------------------------------------------------
# Sudah jadi — dapat dipakai setelah TODO 1 bagian A selesai
# ---------------------------------------------------------------------


def tulis_manifest_keluaran(berkas: Path, tujuan: Path | None = None) -> Path:
    """Catat ringkasan SHA-256 sebuah berkas keluaran ke manifestnya sendiri.

    Manifest keluaran dipisahkan dari `data/manifest.sha256` dengan sengaja.
    Manifest bawaan proyek adalah catatan dosen tentang berkas yang dibagikan;
    manifest keluaran adalah catatan Anda tentang berkas yang Anda hasilkan.
    Menggabungkan keduanya membuat asal-usul kedua berkas tidak lagi dapat
    dibedakan.

    Manifest inilah bukti reproduksibilitas: menjalankan ulang pipeline pada
    masukan yang sama harus menghasilkan ringkasan yang sama persis.
    """
    tujuan = tujuan or berkas.with_suffix(berkas.suffix + ".sha256")
    ringkasan = hitung_sha256(berkas)
    tujuan.write_text(f"{ringkasan} *{kunci_manifest(berkas)}\n", encoding="utf-8")
    return tujuan
