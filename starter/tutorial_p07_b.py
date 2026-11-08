"""Contoh B P07: membatasi pilihan nama kolom dan arah pengurutan.

Jalankan dari akar proyek: python starter/tutorial_p07_b.py
Contoh ini tidak terhubung ke MySQL; query hanya dicetak, bukan dijalankan.
Pelajari pemeriksaan daftar yang diizinkan untuk TODO 2.
"""

KOLOM_BOLEH = ("judul", "tahun", "cabang")
ARAH_BOLEH = ("ASC", "DESC")


def susun_urutan(kolom, arah="ASC"):
    if kolom not in KOLOM_BOLEH:
        raise ValueError(f"kolom tidak sah: {kolom}. Pilihan: {', '.join(KOLOM_BOLEH)}")
    if arah not in ARAH_BOLEH:
        raise ValueError(f"arah tidak sah: {arah}. Pilihan: {', '.join(ARAH_BOLEH)}")
    return f"SELECT * FROM buku ORDER BY {kolom} {arah} LIMIT 5"


def main():
    print(susun_urutan("tahun", "DESC"))
    try:
        susun_urutan("tahun; DROP TABLE buku")
    except ValueError as galat:
        print("Ditolak:", galat)


if __name__ == "__main__":
    main()
