"""Contoh A P07: membaca view MySQL dengan parameter.

Jalankan dari akar proyek: python starter/tutorial_p07_a.py
Contoh ini hanya membaca data sintetik dengan akun app_service.
Pelajari pola execute(..., (nilai,)) dan fetchall() untuk TODO 1.
"""

from koneksi import TidakDapatTerhubung, buka


def hitung_semester(kursor, semester):
    kursor.execute(
        "SELECT COUNT(*) FROM v_nilai_mahasiswa WHERE semester = %s",
        (semester,),
    )
    return kursor.fetchone()[0]


def daftar_kode(kursor, semester):
    kursor.execute(
        "SELECT DISTINCT kode_mahasiswa FROM v_nilai_mahasiswa "
        "WHERE semester = %s ORDER BY kode_mahasiswa LIMIT 3",
        (semester,),
    )
    return kursor.fetchall()


def main():
    try:
        koneksi = buka("app_service")
    except TidakDapatTerhubung as galat:
        print(f"GAGAL: {galat}")
        raise SystemExit(1)

    try:
        kursor = koneksi.cursor()
        print("Semester 1 :", hitung_semester(kursor, 1), "baris")
        print("Semester 99:", hitung_semester(kursor, 99), "baris")
        for baris in daftar_kode(kursor, 1):
            print(baris[0])
    finally:
        koneksi.close()


if __name__ == "__main__":
    main()
