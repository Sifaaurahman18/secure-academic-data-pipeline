"""Langkah 3 — meringkas satu batch menjadi laporan agregat.

Berkas ini sudah jadi dan tidak memuat TODO. Bacalah tetap: worksheet bagian F
menanyakan dua keputusan rancangan di dalamnya, dan keduanya lebih penting
daripada kode yang menghitung.

Jalankan dari folder proyek, setelah `python -m pipeline.muat` selesai:

    python -m pipeline.ringkas                 batch terakhir
    python -m pipeline.ringkas --batch a1b2c3   batch tertentu

**Keputusan pertama: kolom yang tidak ikut.** Tabel `staging_nilai` memuat
`status_pendampingan`, dan akun pipeline dapat membacanya kembali. Laporan ini
tetap tidak menyertakannya, dalam bentuk apa pun, termasuk bentuk agregat.
Kamus data proyek bagian 4 menyebut kolom itu atribut paling sensitif pada
dataset: kolom tersebut menggambarkan kondisi pribadi, bukan capaian akademik.
Yang menentukan bukanlah apakah sebuah data dapat diambil, melainkan apakah
data itu memang dibutuhkan penerima laporan.

**Keputusan kedua: sel kecil ditekan.** Aturan yang dipakai sama persis dengan
Pertemuan 6, dan ambangnya pun sama. Laporan per program studi dan semester
akan memuat sel yang hanya berisi dua atau tiga orang; menerbitkan angka
semacam itu berarti menerbitkan orangnya. Penekanan sekunder ikut diterapkan
karena laporan ini juga menerbitkan total per program studi: satu sel yang
ditekan sendirian dapat dihitung kembali dari selisih terhadap total.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict

from . import basis_data, keutuhan, konfigurasi, pencatatan

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KOLOM_LAPORAN = (
    "batch_id",
    "program_studi",
    "semester",
    "jumlah_mahasiswa",
    "jumlah_catatan",
    "jumlah_tidak_lulus",
)

# Kolom angka yang ikut ditekan ketika sebuah sel dinyatakan terlalu kecil.
KOLOM_ANGKA = ("jumlah_mahasiswa", "jumlah_catatan", "jumlah_tidak_lulus")

DITEKAN = "*"


def batch_terakhir(sambungan) -> str | None:
    """Cari `batch_id` yang paling akhir diterima tabel staging."""
    kursor = sambungan.cursor()
    kursor.execute(
        "SELECT batch_id FROM staging_nilai "
        "GROUP BY batch_id ORDER BY MAX(diterima_pada) DESC LIMIT 1"
    )
    hasil = kursor.fetchone()
    kursor.close()
    return hasil[0] if hasil else None


def baca_batch(sambungan, batch_id: str) -> list[dict[str, str]]:
    """Baca kembali satu batch dari tabel staging.

    Hanya kolom yang dibutuhkan laporan yang diminta. Membaca `SELECT *` lalu
    membuang kolom yang tidak dipakai memberikan hasil yang sama, tetapi
    membuat kolom sensitif sempat berpindah ke memori proses, ke jaringan, dan
    berpotensi ke pesan galat.
    """
    kursor = sambungan.cursor(dictionary=True)
    kursor.execute(
        "SELECT kode_mahasiswa, program_studi, semester, status_kelulusan "
        "FROM staging_nilai WHERE batch_id = %s",
        (batch_id,),
    )
    baris = kursor.fetchall()
    kursor.close()
    return baris


def ringkas(baris: list[dict[str, str]]) -> list[dict[str, object]]:
    """Hitung tiga angka per program studi dan semester.

    Ketiganya menjawab pertanyaan yang berbeda, dan karena itu dihitung dengan
    cara yang berbeda pula:

        jumlah_mahasiswa     banyaknya ORANG yang berbeda
        jumlah_catatan       banyaknya baris nilai
        jumlah_tidak_lulus   banyaknya baris nilai yang tidak lulus

    Angka pertama dihitung dari himpunan `kode_mahasiswa`, bukan dari jumlah
    baris. Satu mahasiswa memiliki beberapa catatan nilai, sehingga menghitung
    baris akan melipatgandakan angkanya — dan laporan yang salah hitung tidak
    hanya keliru, tetapi juga membuat sel yang sebenarnya kecil tampak besar
    dan aman. Justru angka pertama inilah yang dipakai menilai apakah sebuah
    sel terlalu kecil untuk diterbitkan.
    """
    orang: dict[tuple[str, str], set[str]] = defaultdict(set)
    catatan: dict[tuple[str, str], int] = defaultdict(int)
    tidak_lulus: dict[tuple[str, str], int] = defaultdict(int)

    for satu in baris:
        kunci = (satu["program_studi"], str(satu["semester"]))
        orang[kunci].add(satu["kode_mahasiswa"])
        catatan[kunci] += 1
        if satu["status_kelulusan"] == "Tidak Lulus":
            tidak_lulus[kunci] += 1

    return [
        {
            "program_studi": program_studi,
            "semester": semester,
            "jumlah_mahasiswa": len(orang[(program_studi, semester)]),
            "jumlah_catatan": catatan[(program_studi, semester)],
            "jumlah_tidak_lulus": tidak_lulus[(program_studi, semester)],
        }
        for program_studi, semester in sorted(orang)
    ]


def tekan_sel_kecil(
    ringkasan: list[dict[str, object]], ambang: int = konfigurasi.AMBANG_SEL_KECIL
) -> list[dict[str, object]]:
    """Tekan sel yang terlalu kecil sebelum laporan diterbitkan.

    Ketiga aturannya sama persis dengan yang dikerjakan pada Pertemuan 6, hanya
    dipasang pada laporan yang berbeda.

    Aturan 1 — penekanan primer. Sel dengan `jumlah_mahasiswa` di bawah ambang
    ditekan seluruhnya. Menerbitkan `jumlah_catatan` saja ketika
    `jumlah_mahasiswa` disembunyikan tetap membocorkan, karena pembaca tahu
    jumlah orangnya tidak lebih besar daripada jumlah catatannya.

    Aturan 2 — penekanan atribut sensitif. Untuk sel yang lolos aturan 1,
    `jumlah_tidak_lulus` ditekan sendiri bila kelompok yang terbentuk terlalu
    kecil, baik kelompok yang tidak lulus maupun kelompok pelengkapnya. Nol
    tidak ditekan: "tidak ada yang tidak lulus" tidak menunjuk siapa pun.
    Angka 2, sebaliknya, menunjuk dua orang di dalam kelompok yang sudah
    diketahui ukurannya.

    Aturan 3 — penekanan sekunder. Bila dalam satu program studi aturan 1
    menekan tepat satu sel, satu sel lagi ikut ditekan, karena sel tunggal yang
    ditekan dapat dihitung kembali dari selisih terhadap total program studi.
    Yang dipilih adalah sel dengan `jumlah_mahasiswa` terkecil di antara yang
    tersisa; bila seri, semester terkecil, supaya hasilnya tidak bergantung
    pada urutan masukan.

    Nilai yang ditekan diwakili `None`, bukan 0 dan bukan teks kosong, supaya
    "ditekan" tidak pernah tertukar dengan "memang nol".
    """
    hasil = [dict(sel) for sel in ringkasan]

    def tekan(sel: dict[str, object]) -> None:
        for kolom in KOLOM_ANGKA:
            sel[kolom] = None

    for sel in hasil:
        if sel["jumlah_mahasiswa"] < ambang:
            tekan(sel)

    for sel in hasil:
        if sel["jumlah_mahasiswa"] is None:
            continue
        tidak_lulus = sel["jumlah_tidak_lulus"]
        lulus = sel["jumlah_catatan"] - tidak_lulus
        if 0 < tidak_lulus < ambang or 0 < lulus < ambang:
            sel["jumlah_tidak_lulus"] = None

    per_program: dict[str, list[dict[str, object]]] = defaultdict(list)
    for sel in hasil:
        per_program[sel["program_studi"]].append(sel)

    for kelompok in per_program.values():
        ditekan = [sel for sel in kelompok if sel["jumlah_mahasiswa"] is None]
        tersisa = [sel for sel in kelompok if sel["jumlah_mahasiswa"] is not None]
        if len(ditekan) != 1 or not tersisa:
            continue
        tekan(
            min(tersisa, key=lambda sel: (sel["jumlah_mahasiswa"], int(sel["semester"])))
        )

    return hasil


def jalankan(batch_diminta: str | None) -> int:
    """Susun laporan agregat satu batch. Kembalikan kode keluar proses."""
    korelasi = pencatatan.korelasi_baru()

    try:
        with basis_data.koneksi() as sambungan:
            batch_id = batch_diminta or batch_terakhir(sambungan)
            if not batch_id:
                print("GAGAL: tabel staging masih kosong. Jalankan dahulu:")
                print("  python -m pipeline.muat")
                return 1
            baris = baca_batch(sambungan, batch_id)
    except basis_data.BasisDataTidakSiap as galat:
        print(f"GAGAL: {galat}")
        return 1

    if not baris:
        print(f"GAGAL: batch {batch_id} tidak ditemukan pada tabel staging.")
        return 1

    ringkasan = tekan_sel_kecil(ringkas(baris))
    berkas = konfigurasi.DIR_PROCESSED / f"ringkasan-{batch_id}.csv"
    berkas.parent.mkdir(parents=True, exist_ok=True)
    with berkas.open("w", encoding="utf-8", newline="") as tujuan:
        penulis = csv.DictWriter(tujuan, fieldnames=list(KOLOM_LAPORAN), lineterminator="\n")
        penulis.writeheader()
        for sel in ringkasan:
            baris_laporan = {"batch_id": batch_id}
            baris_laporan.update(
                {kolom: sel[kolom] for kolom in ("program_studi", "semester")}
            )
            baris_laporan.update(
                {
                    kolom: DITEKAN if sel[kolom] is None else sel[kolom]
                    for kolom in KOLOM_ANGKA
                }
            )
            penulis.writerow(baris_laporan)

    print("LAPORAN AGREGAT")
    print(f"Batch             : {batch_id}")
    print(f"Baris dibaca      : {len(baris)}")
    print(f"Ambang sel kecil  : {konfigurasi.AMBANG_SEL_KECIL}\n")
    print(
        f"  {'Program studi':<26} {'Sem':>4} {'Mahasiswa':>10} "
        f"{'Catatan':>8} {'Tidak lulus':>12}"
    )
    for sel in ringkasan:
        angka = [DITEKAN if sel[kolom] is None else sel[kolom] for kolom in KOLOM_ANGKA]
        print(
            f"  {sel['program_studi']:<26} {sel['semester']:>4} "
            f"{str(angka[0]):>10} {str(angka[1]):>8} {str(angka[2]):>12}"
        )

    jumlah_ditekan = sum(1 for sel in ringkasan if sel["jumlah_mahasiswa"] is None)
    print(f"\n  {DITEKAN} = ditekan; {jumlah_ditekan} dari {len(ringkasan)} sel")
    print(f"\nLaporan           : {berkas.name}")
    print(f"Manifest laporan  : {keutuhan.tulis_manifest_keluaran(berkas).name}")

    pencatatan.catat(
        "ringkas",
        "berhasil",
        berkas.name,
        f"batch={batch_id} sel={len(ringkasan)} ditekan={jumlah_ditekan}",
        korelasi,
    )
    return 0


def main() -> int:
    pengurai = argparse.ArgumentParser(description="Laporan agregat satu batch staging.")
    pengurai.add_argument(
        "--batch",
        default=None,
        help="batch_id yang diringkas; bawaannya batch terakhir yang dimuat",
    )
    return jalankan(pengurai.parse_args().batch)


if __name__ == "__main__":
    raise SystemExit(main())
