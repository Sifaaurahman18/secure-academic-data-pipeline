"""Contoh C P07: menyamarkan nilai sensitif sebelum masuk log.

Jalankan dari akar proyek: python starter/tutorial_p07_c.py
Contoh ini tidak terhubung ke MySQL. Pola dan batas panjang pada TODO 3
berbeda; gunakan tekniknya, bukan menyalin angka atau nama rahasia ini.
"""

import re


def main():
    # C1: mengenali angka. Ini pengantar re.sub(), bukan aturan log tugas.
    teks = "Anggota A-017 meminjam 3 buku pada 12 Mei"
    print(re.sub(r"\d+", "#", teks))

    # C2: pertahankan nama pasangan, tetapi samarkan nilainya.
    catatan = "petugas=sari PIN=4821 kode_akses=zx9 cabang=utara"
    print(re.sub(r"(\w*(?:pin|kode)\w*)=\S+", r"\1=***", catatan, flags=re.IGNORECASE))

    # C3: samarkan rentetan panjang yang tampak seperti token.
    contoh = "salinan " + "x" * 15 + " selesai"
    print(re.sub(r"[A-Za-z0-9+/=_-]{12,}", "***", contoh))

    # C4: batasi panjang teks sesudah penyamaran.
    print("halo dunia"[:4])


if __name__ == "__main__":
    main()
