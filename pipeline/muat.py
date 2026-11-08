"""Langkah 2 — memuat hasil validasi ke tabel staging.

**TODO 5 ada di berkas ini.**

Jalankan dari folder proyek, setelah `python -m pipeline.validasi` selesai:

    python -m pipeline.muat

Langkah ini membutuhkan MySQL yang menyala dan akun `operator_pipeline` yang
sudah dibuat melalui `database/roles.sql`.

Data masuk ke `staging_nilai`, bukan ke `nilai_akademik`. Tabel staging
menerima seluruh kolom sebagai teks, tanpa tipe dan tanpa batasan. Pilihan itu
disengaja: penolakan data harus terjadi di pipeline, tempat alasannya dapat
dijelaskan kepada manusia, bukan di basis data, tempat penolakan hanya berupa
nomor galat. Basis data tetap menjadi lapis pertahanan terakhir, bukan lapis
pertama.

Setiap pemuatan diberi satu `batch_id` yang sama dengan `korelasi_id` pada
log. Satu nilai itu menghubungkan tiga hal: baris pada tabel staging, baris
pada `log_aktivitas`, dan berkas karantina dari langkah sebelumnya.
"""

from __future__ import annotations

import sys

from . import basis_data, keutuhan, konfigurasi, pencatatan, validasi

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------
# TODO 5 — Pemuatan yang gagal dengan aman
# ---------------------------------------------------------------------


def muat_batch(
    sambungan,
    baris: list[dict[str, str]],
    batch_id: str,
    ukuran_batch: int = konfigurasi.UKURAN_BATCH,
) -> int:
    """Sisipkan seluruh baris ke `staging_nilai`, dan kembalikan jumlahnya.

    Yang harus dipenuhi:

      1. **Seluruh pemuatan adalah satu transaksi.** Matikan `autocommit`,
         lalu panggil `sambungan.commit()` satu kali saja setelah baris
         terakhir berhasil disisipkan;
      2. **Kegagalan mana pun membatalkan seluruhnya.** Tangkap pengecualian
         dari proses penyisipan, panggil `sambungan.rollback()`, lalu lemparkan
         kembali pengecualian itu agar pemanggil tahu pemuatan tidak jadi;
      3. jumlah baris yang dikembalikan adalah jumlah yang benar-benar
         tersisip, bukan panjang senarai masukan.

    Bentuk yang dikirim ke basis data sudah disiapkan `_sebagai_tupel()`, dan
    seluruh nilainya dikirim sebagai parameter. Jangan merangkai nilai apa pun
    ke dalam teks SQL.

    Kode yang ada di bawah ini sengaja ditulis dengan cara yang keliru:
    `autocommit` menyala dan setiap potongan langsung permanen. Cobalah
    memutus MySQL di tengah pemuatan sebelum Anda memperbaikinya, lalu periksa
    isi tabel staging. Yang tertinggal adalah setengah batch tanpa penanda apa
    pun bahwa batch itu tidak lengkap — dan laporan yang dihitung dari data
    setengah jadi akan tampak wajar, hanya saja salah.

    Worksheet bagian E meminta bukti kedua perilaku tersebut: satu jalan yang
    berhasil, dan satu jalan yang gagal di tengah lalu tidak menyisakan apa pun.

    Petunjuk: `kursor.executemany(basis_data.PERINTAH_SISIP, potongan)`
    menyisipkan satu potongan sekaligus, dan `kursor.rowcount` menyebut jumlah
    baris yang tersisip pada pemanggilan itu.
    """
    # TODO 5: ganti seluruh isi fungsi ini.
    sambungan.autocommit = True
    tersisip = 0
    kursor = sambungan.cursor()
    for awal in range(0, len(baris), ukuran_batch):
        potongan = [_sebagai_tupel(satu, batch_id) for satu in baris[awal : awal + ukuran_batch]]
        kursor.executemany(basis_data.PERINTAH_SISIP, potongan)
        tersisip += len(potongan)
    kursor.close()
    return tersisip


# ---------------------------------------------------------------------
# Sudah jadi — tidak perlu diubah
# ---------------------------------------------------------------------


def _sebagai_tupel(baris: dict[str, str], batch_id: str) -> tuple[str, ...]:
    """Susun satu baris menjadi tupel parameter, sesuai urutan kolom staging."""
    nilai = {"batch_id": batch_id, **baris}
    return tuple(nilai[kolom] for kolom in basis_data.KOLOM_STAGING)


def jalankan() -> int:
    """Jalankan seluruh langkah pemuatan. Kembalikan kode keluar proses."""
    sumber = konfigurasi.BERKAS_KELUARAN
    korelasi = pencatatan.korelasi_baru()

    print("PEMUATAN KE TABEL STAGING")
    print(f"Batch             : {korelasi}")
    print(f"Berkas sumber     : {sumber.name}")

    if not sumber.exists():
        print(f"GAGAL: {sumber.name} belum ada. Jalankan dahulu:")
        print("  python -m pipeline.validasi")
        return 1

    # Berkas yang dimuat harus berkas yang sama dengan yang dihasilkan langkah
    # validasi. Manifest keluaran menutup celah di antara dua langkah: tanpa
    # pemeriksaan ini, berkas hasil dapat disunting dengan tangan setelah
    # validasi selesai dan tidak ada yang mengetahuinya.
    berkas_manifest = sumber.with_suffix(sumber.suffix + ".sha256")
    if not berkas_manifest.exists():
        print(f"GAGAL: manifest keluaran {berkas_manifest.name} tidak ditemukan.")
        return 1

    tercatat = keutuhan.baca_manifest(berkas_manifest).get(keutuhan.kunci_manifest(sumber))
    ringkasan = keutuhan.hitung_sha256(sumber)
    if tercatat != ringkasan:
        print("GAGAL: berkas hasil berubah setelah divalidasi.")
        print(f"  tercatat  : {tercatat}")
        print(f"  ditemukan : {ringkasan}")
        print("  Jalankan ulang: python -m pipeline.validasi")
        pencatatan.catat("muat", "ditolak", sumber.name, "ringkasan berbeda", korelasi)
        return 1

    baris = validasi.baca_csv(sumber)
    print(f"SHA-256 sumber    : {ringkasan}")
    print(f"Baris akan dimuat : {len(baris)}")

    try:
        with basis_data.koneksi() as sambungan:
            try:
                tersisip = muat_batch(sambungan, baris, korelasi)
            except Exception as galat:
                print(f"GAGAL: pemuatan dibatalkan ({type(galat).__name__}).")
                pencatatan.catat(
                    "muat", "gagal", sumber.name, str(galat), korelasi, sambungan
                )
                # muat_batch() sudah mematikan autocommit. Tanpa commit ini,
                # catatan kegagalan ikut dibatalkan ketika koneksi ditutup,
                # dan auditor yang membaca log_aktivitas tidak pernah tahu
                # bahwa pemuatan ini pernah dicoba. Bila koneksinya sendiri
                # yang putus, commit ikut gagal; catatannya tetap ada di
                # logs/pipeline.log, karena berkas selalu ditulis lebih dahulu.
                try:
                    sambungan.commit()
                except Exception:
                    pass
                return 1

            pencatatan.catat(
                "muat",
                "berhasil",
                sumber.name,
                f"batch={korelasi} baris={tersisip} sha256={ringkasan[:16]}",
                korelasi,
                sambungan,
            )
            sambungan.commit()
    except basis_data.BasisDataTidakSiap as galat:
        print(f"GAGAL: {galat}")
        pencatatan.catat("muat", "gagal", sumber.name, str(galat), korelasi)
        return 1

    print(f"Baris tersisip    : {tersisip}")
    print("\nLangkah berikutnya:")
    print(f"  python -m pipeline.ringkas --batch {korelasi}")
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
