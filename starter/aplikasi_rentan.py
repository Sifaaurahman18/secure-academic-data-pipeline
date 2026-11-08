"""Demonstrasi Pertemuan 7: aplikasi yang sengaja dibuat rentan.

Jalankan skrip ini sebelum mengerjakan tugas. Amati empat hasil berikut:

    1. pencarian biasa berjalan normal;
    2. masukan khusus mengubah syarat query dan menampilkan data mahasiswa lain;
    3. UNION membaca view yang tidak ditampilkan oleh halaman;
    4. perintah SELECT kedua yang tidak mengubah data menunjukkan apakah
       pustaka meneruskan perintah bertumpuk; hak DROP diperiksa lewat audit.

Bagian keempat sengaja tidak mencoba DROP TABLE. Hak minimum dari Pertemuan 4
diperiksa melalui audit_keamanan.sql, bukan dengan menguji perintah perusak
pada tabel akademik.

Taruh berkas ini di folder starter/ pada proyek secure-academic-data-pipeline
Anda, bersama koneksi.py, lalu jalankan dari akar proyek (folder yang berisi
folder starter/):

    python starter/aplikasi_rentan.py

Skrip ini hanya membaca, memakai akun app_service pada basis data sintetik
secure_academic_lab, dan tidak mengubah satu pun baris.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from koneksi import TidakDapatTerhubung, buka  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GARIS = "-" * 70


def judul(nomor: int, teks: str) -> None:
    print(f"\n{GARIS}\n{nomor}. {teks}\n{GARIS}")


def cari_rentan(kursor, kata_kunci: str) -> list:
    """Contoh rentan: masukan pengguna disisipkan langsung ke query.

    Nilai pengguna menjadi bagian dari teks perintah SQL. Bentuk ini dipakai
    hanya untuk demonstrasi pada basis data praktikum.
    """
    query = (
        "SELECT kode_mahasiswa, program_studi, semester, kode_mk, nilai_angka "
        "FROM v_nilai_mahasiswa "
        f"WHERE kode_mahasiswa = '{kata_kunci}' "
        "LIMIT 5"
    )
    print(f"  Query yang dikirim:\n    {query}\n")
    kursor.execute(query)
    return kursor.fetchall()


def tampilkan(baris: list, batas: int = 5) -> None:
    if not baris:
        print("  (tidak ada hasil)")
        return
    for satu in baris[:batas]:
        print("   ", " | ".join(str(nilai) for nilai in satu))
    if len(baris) > batas:
        print(f"    ... dan {len(baris) - batas} baris lain")


def demo_pencarian_normal(kursor) -> None:
    judul(1, "Pencarian biasa — cacatnya belum terlihat")
    hasil = cari_rentan(kursor, "MHS-SYN-0007")
    print(f"  Jumlah baris: {len(hasil)}")
    tampilkan(hasil)
    print("\n  Pencarian biasa berhasil. Karena itu, uji dengan masukan biasa")
    print("  saja belum cukup untuk menemukan kerentanan ini.")


def demo_injection_dasar(kursor) -> None:
    judul(2, "Masukan pengguna mengubah syarat pencarian")
    muatan = "' OR '1'='1"
    print(f"  Yang diketik pengguna: {muatan}\n")
    hasil = cari_rentan(kursor, muatan)
    print(f"  Jumlah baris: {len(hasil)}")
    tampilkan(hasil)
    print("\n  Syarat WHERE berubah menjadi selalu benar. Halaman yang dirancang")
    print("  menampilkan satu mahasiswa kini menampilkan baris milik mahasiswa")
    print("  lain; jumlahnya hanya dibatasi LIMIT 5 di akhir query.")
    print("\n  MySQL menjalankan query yang diterima. Kerentanan muncul karena")
    print("  aplikasi menyisipkan masukan pengguna ke dalam teks perintah SQL.")


def demo_union(kursor) -> None:
    judul(3, "UNION mengambil data dari view lain")
    muatan = (
        "' UNION SELECT program_studi, 'BOCOR', semester, kode_mk, "
        "jumlah_lulus FROM v_ringkasan_kelulusan -- "
    )
    print(f"  Yang diketik pengguna:\n    {muatan}\n")
    try:
        hasil = cari_rentan(kursor, muatan)
    except Exception as galat:
        print(f"  Ditolak: {galat}")
        print("\n  Jika percobaan ini gagal, periksa bentuk query dan hak akun.")
        print("  Satu percobaan yang gagal belum membuktikan aplikasi aman.")
        return

    print(f"  Jumlah baris: {len(hasil)}")
    tampilkan(hasil, batas=6)
    print("\n  Halaman ini hanya dirancang menampilkan nilai per mahasiswa, tetapi")
    print("  penyerang membaca laporan agregat kelulusan melaluinya.")
    print("\n  Perhatikan juga jumlah barisnya. Query aslinya diakhiri LIMIT 5,")
    print("  tetapi tanda -- membuat LIMIT menjadi komentar. Akibatnya,")
    print("  pembatas tersebut tidak diterapkan.")
    print("\n  Akun aplikasi memiliki SELECT atas dua view. Karena itu,")
    print("  masukan yang mengubah query dapat membaca keduanya.")


def demo_perintah_bertumpuk(kursor) -> None:
    judul(4, "Perintah kedua yang tidak mengubah data")
    muatan = "MHS-SYN-0007'; SELECT 'P07-OK' AS penanda; -- "
    print(f"  Yang diketik pengguna: {muatan}\n")
    try:
        hasil = cari_rentan(kursor, muatan)
    except Exception as galat:
        print(f"  Pustaka atau server menolak perintah bertumpuk: {galat}")
        print("  Catat hasil ini; perilaku dapat berbeda menurut versi dan konfigurasi.")
        return

    print(f"  Perintah pertama mengembalikan {len(hasil)} baris.")
    try:
        ada_lanjutan = kursor.nextset()
        if ada_lanjutan:
            hasil_kedua = kursor.fetchall()
            print(f"  Hasil perintah kedua: {hasil_kedua}")
            if hasil_kedua == [("P07-OK",)]:
                print("  Penanda P07-OK membuktikan perintah kedua diteruskan.")
        else:
            print("  Tidak ada hasil perintah kedua pada konfigurasi ini.")
    except Exception as galat:
        print(f"  Perintah kedua tidak dapat dibaca: {galat}")

    print("\n  Tidak ada perintah penghapus tabel yang dijalankan.")
    print("  Periksa hak app_service pada bagian E3 audit_keamanan.sql.")
    print("  Query berparameter mencegah masukan mengubah perintah;")
    print("  hak minimum membatasi dampak bila aplikasi masih rentan.")


def main() -> None:
    print("CONTOH PERTEMUAN 7 — APLIKASI YANG SENGAJA RENTAN")
    print("Mata Kuliah Keamanan Data (SSD1033)")
    print("\nSeluruh data bersifat sintetik. Skrip ini hanya membaca.")

    try:
        koneksi = buka("app_service")
    except TidakDapatTerhubung as galat:
        print(f"\nGAGAL: {galat}")
        raise SystemExit(1)

    try:
        kursor = koneksi.cursor()
        demo_pencarian_normal(kursor)
        demo_injection_dasar(kursor)
        demo_union(kursor)
        demo_perintah_bertumpuk(kursor)
    finally:
        koneksi.close()

    print(f"\n{GARIS}")
    print("Catat keempat perilaku pada worksheet bagian D sebagai P07-E01.")
    print("Perbaikannya dikerjakan pada jawaban_p07.py, bukan pada berkas ini.")
    print(GARIS)


if __name__ == "__main__":
    main()
