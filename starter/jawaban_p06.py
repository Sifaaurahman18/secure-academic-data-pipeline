"""Lembar jawaban Pertemuan 6 — penyamaran dan penyembunyian sel kecil.

Lengkapi tiga bagian bertanda TODO. Bagian lain sudah jadi dan tidak perlu
diubah. Taruh berkas ini di folder starter/ pada proyek
secure-academic-data-pipeline Anda. Setelah selesai, jalankan dari akar
proyek (folder yang berisi folder starter/):

    python starter/periksa_hasil_p06.py

Aturan yang berlaku sepanjang berkas ini:

  - kunci dibaca dari berkas melalui muat_kunci(), tidak pernah ditulis di
    dalam kode;
  - nilai yang disembunyikan diwakili None, bukan 0 dan bukan string kosong,
    supaya "disembunyikan" tidak tertukar dengan "memang nol".
"""

from __future__ import annotations

import collections
import csv
import hashlib
import hmac
import os
import secrets
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

STARTER = Path(__file__).resolve().parent
BERKAS_KUNCI = STARTER / "secrets" / "kunci_samaran.txt"

NAMA_DATASET = Path("data") / "processed" / "akademik_sintetik_bersih.csv"


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
    return next((k for k in kandidat if (k / NAMA_DATASET).is_file()), None)


PROYEK = _cari_proyek()
# Bila proyek tidak ditemukan, DATASET menunjuk tempat yang seharusnya supaya
# pesan galat menyebut lokasi yang dapat diperiksa.
DATASET = (PROYEK or STARTER.parent) / NAMA_DATASET

# Ambang ukuran sel minimum. Nilai 5 adalah titik awal yang lazim dipakai
# lembaga statistik, bukan angka yang berlaku mutlak. Pada worksheet Anda
# diminta membela atau menolak angka ini untuk konteks data akademik.
AMBANG_BAWAAN = 5


# ---------------------------------------------------------------------
# Sudah jadi — tidak perlu diubah
# ---------------------------------------------------------------------


def muat_kunci() -> bytes:
    """Baca kunci penyamaran dari berkas; buat sekali bila belum ada.

    Kunci disimpan di folder secrets/ yang sudah terdaftar pada .gitignore.
    Kunci yang pernah tertulis di berkas yang dibagikan harus dianggap bocor
    dan wajib diganti, bukan sekadar dihapus.
    """
    dari_lingkungan = os.environ.get("PDP_KUNCI_SAMARAN")
    if dari_lingkungan:
        return dari_lingkungan.encode("utf-8")

    if not BERKAS_KUNCI.exists():
        BERKAS_KUNCI.parent.mkdir(parents=True, exist_ok=True)
        BERKAS_KUNCI.write_text(secrets.token_hex(32), encoding="utf-8")
        print(f"Kunci penyamaran baru dibuat di {BERKAS_KUNCI}")

    return BERKAS_KUNCI.read_text(encoding="utf-8").strip().encode("utf-8")


def baca_dataset() -> list[dict]:
    """Baca dataset proyek apa adanya."""
    if not DATASET.exists():
        raise FileNotFoundError(
            f"dataset tidak ditemukan di {DATASET}. Taruh berkas ini di folder "
            "starter/ pada proyek 'secure-academic-data-pipeline', lalu jalankan "
            "dari akar proyek. Dataset dibuat dengan tools/buat_dataset.py."
        )
    with DATASET.open(encoding="utf-8", newline="") as berkas:
        return list(csv.DictReader(berkas))


# ---------------------------------------------------------------------
# TODO 1 — Penyamaran pengenal
# ---------------------------------------------------------------------


def samarkan(kode_mahasiswa: str, kunci: bytes) -> str:
    pesan = kode_mahasiswa.encode("utf-8")
    return hmac.new(kunci, pesan, hashlib.sha256).hexdigest()[:16]


# ---------------------------------------------------------------------
# TODO 2 — Peringkasan kelompok
# ---------------------------------------------------------------------


def ringkas_kelompok(baris: list[dict]) -> list[dict]:
    kelompok = collections.defaultdict(lambda: {"mahasiswa": set(), "didampingi": set()})

    for satu in baris:
        kunci = (satu["program_studi"], int(satu["semester"]))
        kelompok[kunci]["mahasiswa"].add(satu["kode_mahasiswa"])

        if satu["status_pendampingan"] == "Ya":
            kelompok[kunci]["didampingi"].add(satu["kode_mahasiswa"])

    hasil = []

    for (program_studi, semester), data in kelompok.items():
        hasil.append({
            "program_studi": program_studi,
            "semester": semester,
            "jumlah_mahasiswa": len(data["mahasiswa"]),
            "jumlah_didampingi": len(data["didampingi"]),
        })

    return hasil

# ---------------------------------------------------------------------
# TODO 3 — Penyembunyian sel kecil
# ---------------------------------------------------------------------


def tekan_sel_kecil(ringkasan: list[dict], ambang: int = AMBANG_BAWAAN) -> list[dict]:
    hasil = [satu.copy() for satu in ringkasan]

    for satu in hasil:
        if satu["jumlah_mahasiswa"] < ambang:
            satu["jumlah_mahasiswa"] = None
            satu["jumlah_didampingi"] = None
        elif (
            satu["jumlah_didampingi"] < ambang
            or (satu["jumlah_mahasiswa"] - satu["jumlah_didampingi"]) < ambang
        ):
            satu["jumlah_didampingi"] = None

    per_program = collections.defaultdict(list)

    for satu in hasil:
        per_program[satu["program_studi"]].append(satu)

    for program_studi, kelompok in per_program.items():
        disembunyikan = [
            satu for satu in kelompok
            if satu["jumlah_mahasiswa"] is None
        ]

        if len(disembunyikan) == 1:
            tersisa = [
                satu for satu in kelompok
                if satu["jumlah_mahasiswa"] is not None
            ]

            if tersisa:
                tambahan = min(
                    tersisa,
                    key=lambda satu: (
                        satu["jumlah_mahasiswa"],
                        satu["semester"],
                    ),
                )

                tambahan["jumlah_mahasiswa"] = None
                tambahan["jumlah_didampingi"] = None

    return hasil

# ---------------------------------------------------------------------
# Sudah jadi — pratinjau hasil kerja Anda
# ---------------------------------------------------------------------


def main() -> None:
    kunci = muat_kunci()
    baris = baca_dataset()

    print("PRATINJAU HASIL JAWABAN P06")
    print(f"Baris dataset: {len(baris)}")

    contoh = baris[0]["kode_mahasiswa"]
    print(f"\nPenyamaran  : {contoh} -> {samarkan(contoh, kunci)}")

    ringkasan = ringkas_kelompok(baris)
    ditekan = tekan_sel_kecil(ringkasan, AMBANG_BAWAAN)

    print(f"\nLaporan setelah penyembunyian (ambang = {AMBANG_BAWAAN}):\n")
    print(f"  {'Program studi':<26} {'Sem':>4} {'Mahasiswa':>10} {'Didampingi':>11}")
    for satu in sorted(ditekan, key=lambda s: (s["program_studi"], s["semester"])):
        mhs = "*" if satu["jumlah_mahasiswa"] is None else satu["jumlah_mahasiswa"]
        dmp = "*" if satu["jumlah_didampingi"] is None else satu["jumlah_didampingi"]
        print(
            f"  {satu['program_studi']:<26} {satu['semester']:>4} "
            f"{str(mhs):>10} {str(dmp):>11}"
        )
    print("\n  * = disembunyikan")


if __name__ == "__main__":
    main()
