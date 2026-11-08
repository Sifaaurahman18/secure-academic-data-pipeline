"""Contoh D P07: membandingkan ringkasan dua salinan data.

Jalankan dari akar proyek: python starter/tutorial_p07_d.py
Contoh ini memakai angka buatan dan tidak terhubung ke MySQL. Pada TODO 4,
ringkasan diambil dari COUNT(*) dan CHECKSUM TABLE pada basis data lab.
"""


def ringkas(tabel):
    hasil = {}
    for nama, jumlah, cek in tabel:
        hasil[nama] = (jumlah, cek)
    return hasil


def bedakan(asal, pulih):
    hasil = []
    for nama in asal:
        if nama not in pulih:
            hasil.append(f"{nama}: tidak ada pada hasil pemulihan")
        elif asal[nama][0] != pulih[nama][0]:
            hasil.append(f"{nama}: jumlah baris {asal[nama][0]} menjadi {pulih[nama][0]}")
        elif asal[nama][1] != pulih[nama][1]:
            hasil.append(f"{nama}: checksum {asal[nama][1]} menjadi {pulih[nama][1]}")
    return hasil


def main():
    asal = ringkas([("buku", 10, 111), ("anggota", 5, 222), ("denda", 2, 333)])
    pulih = ringkas([("buku", 10, 999), ("anggota", 4, 222)])
    print(asal)
    for kalimat in bedakan(asal, pulih):
        print(kalimat)


if __name__ == "__main__":
    main()
