"""Lembar jawaban Pertemuan 7: memperbaiki aplikasi yang rentan.

Lengkapi empat bagian bertanda TODO. Letakkan berkas ini di folder starter/
proyek secure-academic-data-pipeline. Setelah selesai, jalankan pemeriksa
dari akar proyek (folder yang berisi starter/):

    python starter/periksa_hasil_p07.py

Sebelum mengerjakan, jalankan contoh siap pakai tutorial_p07_a.py sampai
tutorial_p07_d.py. A memberi pola untuk TODO 1, B untuk TODO 2, C untuk
TODO 3, dan D untuk TODO 4. Contoh perlu disesuaikan dengan tugas ini;
jangan menyalin fungsi dan nama tabelnya begitu saja.

Ikuti aturan berikut saat melengkapi fungsi:

  - kirim nilai dari pengguna sebagai parameter SQL;
  - nama tabel dan kolom tidak dapat dikirim sebagai parameter, sehingga
    keduanya diperiksa terhadap daftar yang diizinkan;
  - catat peristiwa tanpa menyimpan rahasia atau isi data pribadi dalam log.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from koneksi import buka  # noqa: E402,F401

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Nama kolom tidak dapat dikirim sebagai parameter. Periksa pilihan pengguna
# terhadap daftar tetap ini sebelum menyusunnya ke ORDER BY.
KOLOM_URUT_DIIZINKAN = ("kode_mahasiswa", "semester", "nilai_angka")
ARAH_DIIZINKAN = ("ASC", "DESC")

# Tabel yang dibandingkan saat memverifikasi hasil pemulihan.
TABEL_DIPERIKSA = (
    "mahasiswa",
    "mata_kuliah",
    "nilai_akademik",
    "staging_nilai",
    "log_aktivitas",
)

PANJANG_KETERANGAN_MAKS = 255


# ---------------------------------------------------------------------
# TODO 1 — Pencarian dengan parameter
# ---------------------------------------------------------------------


def cari_mahasiswa(kursor, kata_kunci: str) -> list:
    """Cari nilai berdasarkan kode mahasiswa dengan query berparameter.

    Kembalikan daftar tuple dengan urutan kolom berikut:

        kode_mahasiswa, program_studi, semester, kode_mk, nilai_angka

    dari view `v_nilai_mahasiswa`.

    Kirim `kata_kunci` sebagai parameter, terpisah dari teks query. Pada
    mysql-connector, gunakan penanda %s dan kirim nilainya sebagai tuple
    pada argumen kedua execute():

        kursor.execute("... WHERE kolom = %s", (nilai,))

    %s di sini adalah penanda parameter, bukan operator pemformatan string
    Python. Jangan menyisipkan nilai dengan f-string, operator %, atau
    .format(), karena ketiganya menyusun ulang query yang rentan.

    Setelah execute(), ambil seluruh barisnya dengan kursor.fetchall() dan
    kembalikan hasilnya.
    """
    raise NotImplementedError("TODO 1 belum dikerjakan: cari_mahasiswa()")


# ---------------------------------------------------------------------
# TODO 2 — Pengurutan dengan daftar yang diizinkan
# ---------------------------------------------------------------------


def urutkan_aman(kursor, kolom: str, arah: str = "ASC") -> list:
    """Ambil 10 baris pertama v_nilai_mahasiswa, diurutkan sesuai permintaan.

    Kolom yang sama seperti cari_mahasiswa, dengan ORDER BY <kolom> <arah>
    dan LIMIT 10.

    Nama kolom dan arah pengurutan **tidak dapat** dikirim sebagai parameter.
    Pada "ORDER BY %s", MySQL membaca parameter sebagai nilai teks, bukan
    nama kolom untuk mengurutkan hasil.

    Periksa keduanya terhadap KOLOM_URUT_DIIZINKAN dan ARAH_DIIZINKAN.
    Jika pilihan tidak ada dalam daftar, lempar ValueError dan sebutkan
    pilihan yang sah dalam pesannya.

    Tolak seluruh nilai yang tidak sah. Menghapus beberapa karakter dari
    masukan tidak menjamin hasilnya menjadi nama kolom yang diizinkan.

    Setelah kolom dan arah lolos pemeriksaan, keduanya boleh disisipkan ke
    ORDER BY dengan f-string karena berasal dari daftar tetap.
    Hindari kata WHERE, VALUES, dan SET di dalam f-string, karena pemeriksa
    menandai f-string yang memuatnya. Ambil barisnya dengan kursor.fetchall().
    """
    raise NotImplementedError("TODO 2 belum dikerjakan: urutkan_aman()")


# ---------------------------------------------------------------------
# TODO 3 — Log yang tidak ikut membocorkan
# ---------------------------------------------------------------------


def bersihkan_keterangan(teks: str) -> str:
    """Samarkan informasi sensitif sebelum keterangan ditulis ke log.

    Log perlu membantu penelusuran tanpa menyimpan rahasia atau data pribadi.

    Tiga hal yang harus dilakukan:

      1. Ganti nilai pada pasangan `nama=nilai` menjadi `nama=***` bila
         namanya memuat salah satu kata: password, sandi, token, secret,
         atau kunci. Perbandingannya tidak peka huruf besar-kecil.
         Contoh: "user=budi password=rahasia123" -> "user=budi password=***"

      2. Ganti setiap rentetan sepanjang 32 karakter atau lebih yang hanya
         terdiri dari huruf, angka, dan tanda + / = _ - menjadi `***`.
         Rentetan sepanjang itu hampir selalu kunci atau token.

      3. Potong hasilnya menjadi paling banyak PANJANG_KETERANGAN_MAKS
         karakter, karena kolom `keterangan` pada tabel log berukuran
         VARCHAR(255) dan baris yang terlalu panjang akan ditolak.

    Kembalikan teks yang sudah bersih. Modul `re` sudah diimpor di atas.
    """
    raise NotImplementedError("TODO 3 belum dikerjakan: bersihkan_keterangan()")


# ---------------------------------------------------------------------
# TODO 4 — Verifikasi hasil pemulihan
# ---------------------------------------------------------------------


def ringkasan_tabel(kursor) -> dict:
    """Ringkas isi basis data agar dapat dibandingkan setelah pemulihan.

    Kembalikan kamus berbentuk:

        {nama_tabel: (jumlah_baris, checksum)}

    untuk setiap tabel pada TABEL_DIPERIKSA.

    Jumlah baris diperoleh dengan SELECT COUNT(*). Checksum diperoleh dengan
    perintah MySQL `CHECKSUM TABLE <nama>`, yang mengembalikan satu baris
    berisi (nama_tabel_lengkap, nilai_checksum).

    Mengapa keduanya, bukan salah satu: jumlah baris yang sama belum berarti
    isinya sama. Pemulihan yang menghasilkan jumlah baris tepat tetapi nilai
    berbeda adalah kegagalan yang paling sulit disadari.

    Nama tabel di sini berasal dari TABEL_DIPERIKSA, bukan dari pengguna,
    sehingga menyusunnya ke dalam query dapat diterima. Bila suatu saat
    daftar itu berasal dari masukan luar, isinya harus diperlakukan seperti
    TODO 2.

    kursor.fetchone() mengembalikan satu baris sebagai tuple; unsur pertamanya
    [0], kedua [1]. Pada hasil CHECKSUM TABLE, nilai checksum ada di [1].
    """
    raise NotImplementedError("TODO 4a belum dikerjakan: ringkasan_tabel()")


def bandingkan(asal: dict, pulih: dict) -> list:
    """Bandingkan dua ringkasan dan kembalikan daftar perbedaannya.

    Kembalikan daftar berisi teks yang mudah dipahami, satu per
    perbedaan. Daftar kosong berarti pemeriksaan tidak menemukan perbedaan.

    Tiga jenis perbedaan yang harus terdeteksi:

      1. tabel ada di `asal` tetapi tidak ada di `pulih`;
      2. jumlah barisnya berbeda;
      3. jumlah barisnya sama tetapi checksum-nya berbeda.

    Sertakan nama tabel dan kedua nilainya pada setiap pesan agar petugas
    dapat menelusuri penyebab kegagalan pemulihan.
    """
    raise NotImplementedError("TODO 4b belum dikerjakan: bandingkan()")


# ---------------------------------------------------------------------
# Sudah jadi — tidak perlu diubah
# ---------------------------------------------------------------------


def catat_aktivitas(
    koneksi,
    aktor: str,
    komponen: str,
    aksi: str,
    objek: str | None,
    hasil: str,
    korelasi_id: str | None = None,
    keterangan: str | None = None,
) -> None:
    """Tulis satu baris ke log_aktivitas.

    Perhatikan dua hal pada fungsi ini, karena keduanya akan diuji pemeriksa:

      - seluruh nilai dikirim sebagai parameter, termasuk yang berasal dari
        program sendiri. Kebiasaan ini yang menjaga konsistensi;
      - keterangan selalu melewati bersihkan_keterangan().
    """
    if keterangan is not None:
        keterangan = bersihkan_keterangan(keterangan)

    kursor = koneksi.cursor()
    kursor.execute(
        "INSERT INTO log_aktivitas "
        "(aktor, komponen, aksi, objek, hasil, korelasi_id, keterangan) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (aktor, komponen, aksi, objek, hasil, korelasi_id, keterangan),
    )
    koneksi.commit()
    kursor.close()


def main() -> None:
    """Pratinjau hasil kerja Anda."""
    koneksi = buka("app_service")
    try:
        kursor = koneksi.cursor()

        print("PRATINJAU HASIL JAWABAN P07")

        print("\n1. Pencarian biasa:")
        for baris in cari_mahasiswa(kursor, "MHS-SYN-0007"):
            print("   ", " | ".join(str(n) for n in baris))

        print("\n2. Pencarian dengan muatan injection:")
        hasil = cari_mahasiswa(kursor, "' OR '1'='1")
        print(f"    {len(hasil)} baris — seharusnya 0, karena tidak ada")
        print("    mahasiswa yang kodenya benar-benar berbunyi seperti itu.")

        print("\n3. Pengurutan yang diizinkan:")
        for baris in urutkan_aman(kursor, "nilai_angka", "DESC")[:3]:
            print("   ", " | ".join(str(n) for n in baris))

        print("\n4. Pengurutan yang ditolak:")
        try:
            urutkan_aman(kursor, "nilai_angka; DROP TABLE mahasiswa")
            print("    TIDAK DITOLAK — periksa kembali TODO 2.")
        except ValueError as galat:
            print(f"    Ditolak: {galat}")

        print("\n5. Pembersihan keterangan:")
        contoh = "login user=budi password=rahasia123 token=" + "A" * 40
        print(f"    sebelum : {contoh}")
        print(f"    sesudah : {bersihkan_keterangan(contoh)}")
    finally:
        koneksi.close()


if __name__ == "__main__":
    main()
