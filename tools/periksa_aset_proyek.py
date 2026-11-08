"""Pemeriksaan aset starter Secure Academic Data Pipeline.

Skrip ini hanya memakai pustaka standar Python dan tidak menyentuh MySQL.
Tujuannya memastikan paket starter lengkap, konsisten, dan bebas dari
kredensial aktif sebelum dibagikan atau dikumpulkan.

Jalankan dari folder proyek:

    python tools/periksa_aset_proyek.py                 # pemeriksaan harian
    python tools/periksa_aset_proyek.py --pengumpulan   # sebelum mengumpulkan

Mode pengumpulan menambahkan satu syarat: berkas .env tidak boleh ada di folder
proyek. Saat praktikum berlangsung berkas itu justru harus ada, sehingga
keberadaannya hanya dilaporkan sebagai catatan pada mode harian.

Skrip berhenti pada kegagalan pertama dengan pesan yang menyebut berkas
dan penyebabnya. Catat pesan tersebut; jangan menghapus bukti kegagalan.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]

FILE_REFERENSI = ROOT / "data" / "referensi_mata_kuliah.csv"
FILE_RAW = ROOT / "data" / "raw" / "akademik_sintetik_raw.csv"
FILE_BERSIH = ROOT / "data" / "processed" / "akademik_sintetik_bersih.csv"
FILE_MANIFEST = ROOT / "data" / "manifest.sha256"
FILE_KAMUS = ROOT / "data" / "kamus_data_proyek.md"
FILE_ENV = ROOT / ".env.example"

BERKAS_SQL = {
    "schema": ROOT / "database" / "schema.sql",
    "seed": ROOT / "database" / "seed_data.sql",
    "roles": ROOT / "database" / "roles.sql",
    "uji": ROOT / "database" / "uji_akses.sql",
}

KOLOM_AKADEMIK = [
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
]
KOLOM_REFERENSI = ["kode_mk", "nama_mk", "sks"]

SEMESTER_SAH = {"1", "3", "5", "7"}
STATUS_KELULUSAN_SAH = {"Lulus", "Tidak Lulus"}
STATUS_PENDAMPINGAN_SAH = {"Ya", "Tidak"}
PROGRAM_STUDI_SAH = {
    "Sains Data",
    "Ekonomi Syariah",
    "Akuntansi Syariah",
    "Manajemen Bisnis Syariah",
}
BATAS_NILAI_LULUS = 60
BATAS_KEHADIRAN_LULUS = 75
FORMAT_WAKTU = "%Y-%m-%dT%H:%M:%S"

KATA_KUNCI_RAHASIA = ("PASSWORD", "SECRET", "TOKEN", "KEY")
# Variabel yang menunjuk lokasi, bukan nilai rahasia, tetap boleh terisi.
AKHIRAN_BUKAN_RAHASIA = ("_PATH", "_DIR", "_FILE", "_URL")
NILAI_AMAN = {"", "[REDACTED]"}


def gagal(pesan: str) -> None:
    raise SystemExit(f"GAGAL: {pesan}")


def baca_csv(path: Path, kolom_diharapkan: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        gagal(f"berkas tidak ditemukan: {path.relative_to(ROOT).as_posix()}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        kolom = list(reader.fieldnames or [])
        if kolom != kolom_diharapkan:
            gagal(f"kolom {path.name} tidak sesuai.\nDiharapkan: {kolom_diharapkan}\nDitemukan : {kolom}")
        return list(reader)


def baris_sah(baris: dict[str, str], kode_mk_sah: set[str]) -> bool:
    """Menerapkan aturan validasi yang sama dengan pipeline P10."""
    if not all(baris[kolom].strip() for kolom in KOLOM_AKADEMIK):
        return False
    if baris["semester"] not in SEMESTER_SAH:
        return False
    if baris["kode_mk"] not in kode_mk_sah:
        return False
    if baris["status_kelulusan"] not in STATUS_KELULUSAN_SAH:
        return False
    if baris["status_pendampingan"] not in STATUS_PENDAMPINGAN_SAH:
        return False
    # Pola saja tidak cukup: "2026-13-45T99:00:00" cocok dengan polanya
    # tetapi bukan tanggal yang sah. Waktu harus benar-benar diurai.
    try:
        datetime.strptime(baris["waktu_pembaruan"], FORMAT_WAKTU)
    except ValueError:
        return False
    if baris["program_studi"] not in PROGRAM_STUDI_SAH:
        return False
    try:
        nilai = int(baris["nilai_angka"])
        kehadiran = int(baris["persentase_kehadiran"])
    except ValueError:
        return False
    if not (0 <= nilai <= 100 and 0 <= kehadiran <= 100):
        return False
    diharapkan = "Lulus" if nilai >= BATAS_NILAI_LULUS and kehadiran >= BATAS_KEHADIRAN_LULUS else "Tidak Lulus"
    return baris["status_kelulusan"] == diharapkan


def periksa_manifest() -> None:
    if not FILE_MANIFEST.exists():
        gagal("data/manifest.sha256 tidak ditemukan")
    entri: dict[str, str] = {}
    for nomor, mentah in enumerate(FILE_MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        if not mentah.strip():
            continue
        bagian = mentah.split(maxsplit=1)
        if len(bagian) != 2 or not re.fullmatch(r"[0-9a-f]{64}", bagian[0]):
            gagal(f"format manifest tidak sah pada baris {nomor}")
        entri[bagian[1].lstrip("* ").replace("\\", "/")] = bagian[0]

    diharapkan = {
        FILE_REFERENSI.relative_to(ROOT).as_posix(),
        FILE_RAW.relative_to(ROOT).as_posix(),
        FILE_BERSIH.relative_to(ROOT).as_posix(),
    }
    if set(entri) != diharapkan:
        gagal(f"manifest harus memuat tepat tiga aset data: {sorted(entri)}")

    for relatif, hash_manifest in entri.items():
        path = ROOT / relatif
        if not path.exists():
            gagal(f"aset pada manifest tidak ditemukan: {relatif}")
        aktual = hashlib.sha256(path.read_bytes()).hexdigest()
        if aktual != hash_manifest:
            gagal(
                f"hash tidak cocok untuk {relatif}.\n"
                f"Manifest: {hash_manifest}\nAktual  : {aktual}\n"
                "Jalankan ulang tools/buat_dataset.py bila dataset memang sengaja diganti."
            )


def periksa_kredensial(mode_pengumpulan: bool) -> list[str]:
    """Memastikan tidak ada kata sandi aktif yang tertinggal di starter.

    Mengembalikan catatan yang perlu ditampilkan tetapi bukan kegagalan.
    """
    catatan: list[str] = []
    isi_roles = BERKAS_SQL["roles"].read_text(encoding="utf-8")
    for nilai in re.findall(r"IDENTIFIED BY '([^']*)'", isi_roles):
        if not nilai.startswith("__GANTI"):
            gagal(
                "roles.sql memuat kata sandi yang sudah diisi. "
                "Ganti kembali menjadi penanda __GANTI_..._ sebelum berkas dibagikan, "
                "lalu ubah kata sandi akun tersebut di MySQL."
            )

    if not FILE_ENV.exists():
        gagal(".env.example tidak ditemukan")
    for nomor, baris in enumerate(FILE_ENV.read_text(encoding="utf-8").splitlines(), start=1):
        bersih = baris.strip()
        if not bersih or bersih.startswith("#") or "=" not in bersih:
            continue
        kunci, _, nilai = bersih.partition("=")
        nama = kunci.strip().upper()
        if nama.endswith(AKHIRAN_BUKAN_RAHASIA):
            continue
        if any(kata in nama for kata in KATA_KUNCI_RAHASIA):
            nilai = nilai.strip()
            if nilai not in NILAI_AMAN and not nilai.startswith("__GANTI"):
                gagal(
                    f".env.example baris {nomor}: variabel {kunci.strip()} berisi nilai. "
                    "Berkas contoh hanya boleh memuat nama variabel dan penanda."
                )

    if (ROOT / ".env").exists():
        if mode_pengumpulan:
            gagal(
                "berkas .env ditemukan di folder proyek. Berkas ini memuat konfigurasi "
                "aktif dan tidak boleh ikut dibagikan atau dikumpulkan. Pindahkan atau "
                "hapus sebelum mengemas artefak."
            )
        catatan.append(
            "berkas .env ada; wajar saat praktikum berlangsung, "
            "tetapi tidak boleh ikut dikumpulkan"
        )

    return catatan


def main() -> None:
    referensi = baca_csv(FILE_REFERENSI, KOLOM_REFERENSI)
    mentah = baca_csv(FILE_RAW, KOLOM_AKADEMIK)
    bersih = baca_csv(FILE_BERSIH, KOLOM_AKADEMIK)

    kode_mk_sah = {row["kode_mk"] for row in referensi}
    if len(kode_mk_sah) != len(referensi):
        gagal("kode_mk pada referensi mata kuliah tidak unik")

    # Berkas processed adalah hasil yang diharapkan pipeline P10.
    for nomor, baris in enumerate(bersih, start=2):
        if not baris_sah(baris, kode_mk_sah):
            gagal(f"berkas processed memuat baris yang melanggar aturan validasi pada baris {nomor}")

    kunci_bersih = [(r["kode_mahasiswa"], r["kode_mk"], r["semester"]) for r in bersih]
    if len(kunci_bersih) != len(set(kunci_bersih)):
        gagal("berkas processed memuat duplikat kode_mahasiswa + kode_mk + semester")
    if len({r["record_id"] for r in bersih}) != len(bersih):
        gagal("record_id pada berkas processed tidak unik")

    # Berkas raw harus memuat cacat; tanpa cacat, praktikum validasi kehilangan bahan.
    cacat = [r for r in mentah if not baris_sah(r, kode_mk_sah)]
    id_ganda = len(mentah) - len({r["record_id"] for r in mentah})
    kunci_mentah = [(r["kode_mahasiswa"], r["kode_mk"], r["semester"]) for r in mentah]
    kunci_ganda = len(kunci_mentah) - len(set(kunci_mentah))

    if not cacat:
        gagal("berkas raw tidak memuat baris cacat; jalankan tools/buat_dataset.py")
    if id_ganda < 1:
        gagal("berkas raw tidak memuat record_id ganda")
    if kunci_ganda < 1:
        gagal("berkas raw tidak memuat duplikat kunci alami")
    if len(mentah) <= len(bersih):
        gagal("berkas raw harus lebih banyak daripada berkas processed")

    for nama, path in BERKAS_SQL.items():
        if not path.exists():
            gagal(f"berkas SQL tidak ditemukan: {path.relative_to(ROOT).as_posix()}")
        if path.stat().st_size == 0:
            gagal(f"berkas SQL kosong: {nama}")

    if not FILE_KAMUS.exists():
        gagal("data/kamus_data_proyek.md tidak ditemukan")
    kamus = FILE_KAMUS.read_text(encoding="utf-8")
    for istilah in ["`status_pendampingan`", "`record_id`", "aturan validasi", "data sintetik"]:
        if istilah not in kamus:
            gagal(f"kamus data belum menjelaskan: {istilah}")

    mode_pengumpulan = "--pengumpulan" in sys.argv

    periksa_manifest()
    catatan = periksa_kredensial(mode_pengumpulan)

    print("PEMERIKSAAN ASET PROYEK")
    print(f"Referensi mata kuliah : {len(referensi)}")
    print(f"Baris raw             : {len(mentah)}")
    print(f"Baris processed       : {len(bersih)}")
    print(f"Baris cacat pada raw  : {len(cacat)}")
    print(f"record_id ganda       : {id_ganda}")
    print(f"Kunci alami ganda     : {kunci_ganda}")
    print("Berkas SQL            : schema, seed, roles, uji_akses tersedia")
    print("Kamus data            : tersedia dan selaras")
    print("Manifest SHA-256      : sesuai")
    print("Kredensial aktif      : tidak ditemukan")
    print("Mode                  : " + ("pengumpulan" if mode_pengumpulan else "harian"))
    for baris in catatan:
        print("Catatan               : " + baris)
    print("ASET PROYEK SIAP DIGUNAKAN")


if __name__ == "__main__":
    main()
