"""Langkah 1 — memvalidasi berkas mentah dan memisahkan hasilnya.

**TODO 3 ada di berkas ini.**

Jalankan dari folder proyek:

    python -m pipeline.validasi

Langkah ini tidak menyentuh basis data sama sekali, sehingga dapat dikerjakan
sebelum MySQL disiapkan.

Yang dihasilkan:

    data/processed/hasil_pipeline.csv          baris yang lolos seluruh aturan
    data/processed/hasil_pipeline.csv.sha256   ringkasan berkas di atas
    data/karantina/karantina-<korelasi>.csv    baris yang ditolak, beserta alasannya
    logs/pipeline.log                          catatan kejadian

Berkas mentah **tidak pernah diubah**. Pemisahan raw dan processed bukan soal
kerapian folder: berkas mentah adalah satu-satunya bukti tentang apa yang
benar-benar diterima pipeline. Berkas yang sudah diperbaiki di tempat tidak
dapat lagi menjawab pertanyaan "sejak kapan datanya salah?".

Baris yang ditolak dikarantina, bukan dibuang. Perbedaannya menentukan: baris
yang dibuang menghilangkan 23 catatan tanpa jejak, sedangkan baris yang
dikarantina dapat diperiksa, diperbaiki, lalu dimasukkan kembali. Kolom
`alasan` pada berkas karantina berisi kode aturan, bukan kalimat bebas,
sehingga hasil dua kali menjalankan pipeline dapat dibandingkan.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from . import aturan, keutuhan, konfigurasi, pencatatan

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KOLOM_KARANTINA = ("alasan", *aturan.KOLOM_WAJIB)


# ---------------------------------------------------------------------
# TODO 3 — Cacat yang hanya terlihat pada berkas sebagai satu kesatuan
# ---------------------------------------------------------------------


def cari_duplikat(baris: list[dict[str, str]]) -> dict[int, list[str]]:
    """Cari baris yang menduplikasi baris lain, dan kembalikan alasannya.

    Kembalikan pemetaan **indeks pada senarai masukan** ke daftar kode dari
    `aturan.ATURAN_ANTARBARIS`. Indeks yang tidak muncul pada hasil berarti
    barisnya dipertahankan.

    Dua bentuk duplikasi yang harus ditemukan:

      1. `record_id` yang sama dipakai lebih dari satu baris;
      2. kombinasi `kode_mahasiswa`, `kode_mk`, dan `semester` yang sama
         dipakai lebih dari satu baris. Kamus data menyebutnya kunci alami:
         satu mahasiswa tidak boleh punya dua catatan nilai untuk mata kuliah
         dan semester yang sama.

    Satu baris dapat melanggar keduanya sekaligus. Kembalikan kedua kodenya
    bila memang demikian; jangan berhenti pada temuan pertama.

    **Urutan pemeriksaan menentukan hasil, dan karena itu harus ditetapkan.**
    Ketika dua baris berebut kunci yang sama, salah satunya dipertahankan dan
    sisanya ditolak. Bila yang dipertahankan adalah "yang lebih dahulu muncul
    di dalam berkas", hasil pipeline bergantung pada urutan baris — padahal
    urutan itu kebetulan, dan sumber data yang sama dapat mengekspor ulang
    isinya dengan urutan berbeda tanpa ada yang berubah maknanya.

    Karena itu **periksa baris menurut `record_id` menaik**, bukan menurut
    urutan kemunculannya. Yang dipertahankan adalah baris dengan `record_id`
    terkecil di antara yang berebut; sisanya ditolak. Urutan itu ditentukan
    isi data, bukan kebetulan penyimpanan, sehingga hasilnya sama pada setiap
    komputer dan pada setiap kali dijalankan.

    Petunjuk: `sorted(enumerate(baris), key=lambda pasangan: pasangan[1]["record_id"])`
    memberikan pasangan indeks dan baris dalam urutan yang diminta, sekaligus
    mempertahankan indeks aslinya untuk dikembalikan.

    Pada berkas mentah proyek, fungsi ini harus menemukan **tepat dua baris**:
    satu yang melanggar kedua aturan sekaligus, dan satu yang hanya melanggar
    aturan kunci alami.
    """
    # TODO 3: ganti baris berikut. Kamus kosong berarti tidak ada duplikat.
    return {}


# ---------------------------------------------------------------------
# Sudah jadi — tidak perlu diubah
# ---------------------------------------------------------------------


def baca_csv(berkas: Path) -> list[dict[str, str]]:
    """Baca berkas CSV menjadi senarai kamus, apa adanya."""
    with berkas.open(encoding="utf-8", newline="") as sumber:
        return list(csv.DictReader(sumber))


def tulis_csv(berkas: Path, baris: list[dict[str, str]], kolom: tuple[str, ...]) -> None:
    """Tulis senarai kamus ke CSV dengan urutan kolom yang tetap.

    Akhir baris ditetapkan melalui `lineterminator`, bukan dibiarkan mengikuti
    kebiasaan sistem operasi. Modul `csv` menulis `\\r\\n` secara bawaan,
    sehingga berkas yang isinya sama persis akan menghasilkan ringkasan SHA-256
    berbeda di Windows dan di Linux — dan pembuktian reproduksibilitas menjadi
    mustahil. Nilai `newline=""` pada `open()` mencegah lapis kedua penerjemahan
    akhir baris; keduanya diperlukan bersama-sama.
    """
    berkas.parent.mkdir(parents=True, exist_ok=True)
    with berkas.open("w", encoding="utf-8", newline="") as tujuan:
        penulis = csv.DictWriter(tujuan, fieldnames=list(kolom), lineterminator="\n")
        penulis.writeheader()
        penulis.writerows(baris)


def jalankan() -> int:
    """Jalankan seluruh langkah validasi. Kembalikan kode keluar proses."""
    korelasi = pencatatan.korelasi_baru()
    masukan = konfigurasi.BERKAS_MASUKAN

    print("VALIDASI BERKAS MASUKAN")
    print(f"Korelasi          : {korelasi}")
    print(f"Berkas masukan    : {masukan.name}")

    if not masukan.exists():
        print(f"GAGAL: berkas masukan tidak ditemukan di {masukan}")
        pencatatan.catat("validasi", "gagal", masukan.name, "berkas tidak ada", korelasi)
        return 1

    # Gerbang keutuhan berjalan lebih dahulu daripada pembacaan isi. Berkas
    # yang tidak dapat dipercaya tidak perlu divalidasi isinya.
    try:
        ringkasan = keutuhan.gerbang_keutuhan(masukan)
    except keutuhan.KeutuhanGagal as galat:
        print(f"GAGAL: {galat}")
        pencatatan.catat("gerbang_keutuhan", "ditolak", masukan.name, str(galat), korelasi)
        return 1

    print(f"SHA-256 masukan   : {ringkasan}")
    # Yang dicatat ke log hanya 16 karakter pertama. Ringkasan lengkapnya sudah
    # berada di manifest, yang memang menjadi catatan resminya; log cukup
    # menjadi penunjuk. Enam belas karakter heksadesimal setara 64 bita, lebih
    # dari cukup untuk memastikan dua catatan menunjuk berkas yang sama.
    pencatatan.catat(
        "gerbang_keutuhan", "berhasil", masukan.name, f"sha256={ringkasan[:16]}", korelasi
    )

    semua = baca_csv(masukan)
    kode_mk_sah = aturan.muat_kode_mk_sah()

    ditolak: list[dict[str, str]] = []
    lolos_per_baris: list[dict[str, str]] = []
    for satu in semua:
        temuan = aturan.periksa_baris(satu, kode_mk_sah)
        if temuan:
            ditolak.append({"alasan": ";".join(sorted(temuan)), **satu})
        else:
            lolos_per_baris.append(satu)

    duplikat = cari_duplikat(lolos_per_baris)
    diterima = [
        satu for nomor, satu in enumerate(lolos_per_baris) if nomor not in duplikat
    ]
    for nomor, temuan in sorted(duplikat.items()):
        ditolak.append({"alasan": ";".join(sorted(temuan)), **lolos_per_baris[nomor]})

    # Keluaran diurutkan menurut record_id dengan alasan yang sama seperti
    # pemeriksaan duplikat: hasil pipeline tidak boleh bergantung pada urutan
    # baris di dalam berkas masukan.
    diterima.sort(key=lambda satu: satu["record_id"])
    ditolak.sort(key=lambda satu: satu["record_id"])

    tulis_csv(konfigurasi.BERKAS_KELUARAN, diterima, aturan.KOLOM_WAJIB)
    berkas_karantina = konfigurasi.DIR_KARANTINA / f"karantina-{korelasi}.csv"
    tulis_csv(berkas_karantina, ditolak, KOLOM_KARANTINA)
    berkas_manifest = keutuhan.tulis_manifest_keluaran(konfigurasi.BERKAS_KELUARAN)

    print(f"Baris dibaca      : {len(semua)}")
    print(f"Baris diterima    : {len(diterima)}")
    print(f"Baris dikarantina : {len(ditolak)}")

    if ditolak:
        print("\nSebaran alasan penolakan:")
        hitungan: dict[str, int] = {}
        for satu in ditolak:
            for kode in satu["alasan"].split(";"):
                hitungan[kode] = hitungan.get(kode, 0) + 1
        for kode in sorted(hitungan):
            penjelasan = aturan.ATURAN.get(kode) or aturan.ATURAN_ANTARBARIS.get(kode, "")
            print(f"  {hitungan[kode]:>3}  {kode:<30} {penjelasan}")

    print(f"\nKeluaran          : {konfigurasi.BERKAS_KELUARAN.name}")
    print(f"Manifest keluaran : {berkas_manifest.name}")
    print(f"Karantina         : {berkas_karantina.name}")

    # Pembanding yang dibagikan dosen adalah hasil yang seharusnya. Berkas itu
    # dibaca, bukan ditimpa; menimpanya akan menghapus satu-satunya acuan yang
    # dimiliki mahasiswa untuk menilai jawabannya sendiri.
    if konfigurasi.BERKAS_PEMBANDING.exists():
        pembanding = keutuhan.hitung_sha256(konfigurasi.BERKAS_PEMBANDING)
        hasil = keutuhan.hitung_sha256(konfigurasi.BERKAS_KELUARAN)
        sama = "ya" if hasil == pembanding else "belum"
        print(f"Sama dengan pembanding: {sama}")
        if hasil != pembanding:
            print(
                "  Keluaran Anda belum identik dengan "
                f"{konfigurasi.BERKAS_PEMBANDING.name}.\n"
                "  Bandingkan sebaran alasan di atas dengan tabel jumlah pada\n"
                "  docstring aturan.periksa_baris()."
            )

    pencatatan.catat(
        "validasi",
        "berhasil",
        konfigurasi.BERKAS_KELUARAN.name,
        f"diterima={len(diterima)} dikarantina={len(ditolak)}",
        korelasi,
    )
    return 0


def _mulai() -> int:
    """Jalankan langkah ini, dan terjemahkan TODO yang belum dikerjakan.

    Tanpa penangkapan ini, bagian TODO yang belum dikerjakan muncul sebagai
    jejak galat Python yang tercampur dengan keluaran biasa. Pesan yang jelas
    lebih berguna, dan langkahnya tetap gagal sebagaimana mestinya.
    """
    try:
        return jalankan()
    except NotImplementedError as galat:
        print(f"\nBELUM SELESAI: {galat}")
        print("  Kerjakan bagian TODO tersebut lebih dahulu, lalu jalankan lagi.")
        return 1


if __name__ == "__main__":
    raise SystemExit(_mulai())
