"""Contoh lengkap Pertemuan 6 — apa yang masih terbaca setelah data disamarkan.

Skrip ini sudah jadi dan dapat langsung dijalankan; Anda tidak perlu
menulis apa pun. Tugasnya menunjukkan empat hal yang biasanya baru disadari
setelah laporan terlanjur terbit:

    1. hash biasa atas NIM dapat dibalik dengan menebak, bukan dipecahkan;
    2. penyamaran berkunci menahan tebakan yang sama;
    3. laporan agregat tanpa satu pun pengenal masih dapat menunjuk satu orang;
    4. menyembunyikan satu sel saja belum menyembunyikan angkanya, karena nilainya dapat
       dihitung kembali dari selisih.

Taruh berkas ini di folder starter/ pada proyek secure-academic-data-pipeline
Anda, lalu jalankan dari akar proyek (folder yang berisi folder starter/):

    python starter/contoh_penyamaran.py

Skrip ini hanya membaca berkas CSV proyek dan tidak mengirim apa pun ke luar
komputer Anda.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import hmac
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

STARTER = Path(__file__).resolve().parent
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
# Dataset proyek dipakai apa adanya, tidak disalin ke folder lain. Bila proyek
# tidak ditemukan, DATASET menunjuk tempat yang seharusnya.
DATASET = (PROYEK or STARTER.parent) / NAMA_DATASET

# Kunci ini sengaja ditulis di sini KARENA berkas ini hanya contoh yang tidak
# pernah menyentuh data nyata. Pada jawaban_p06.py kunci wajib dibaca dari
# berkas. Pemeriksa akan menolak kunci yang tertulis di dalam kode.
KUNCI_CONTOH = b"kunci-contoh-p06-tidak-untuk-dipakai-ulang"

GARIS = "-" * 68


def judul(nomor: int, teks: str) -> None:
    print(f"\n{GARIS}\n{nomor}. {teks}\n{GARIS}")


def baca_dataset() -> list[dict]:
    if not DATASET.exists():
        print(f"GAGAL: dataset tidak ditemukan di\n  {DATASET}")
        print("\n  Taruh skrip ini di folder starter/ pada proyek")
        print("  'secure-academic-data-pipeline', lalu jalankan dari akar proyek:")
        print("      cd secure-academic-data-pipeline")
        print("      python starter/contoh_penyamaran.py")
        print("\n  Dataset dibuat dengan tools/buat_dataset.py bila belum ada.")
        raise SystemExit(1)
    with DATASET.open(encoding="utf-8", newline="") as berkas:
        return list(csv.DictReader(berkas))


def samar_hash_biasa(kode: str) -> str:
    """Cara yang TAMPAK aman: hash biasa, tanpa kunci."""
    return hashlib.sha256(kode.encode("utf-8")).hexdigest()[:16]


def samar_berkunci(kode: str, kunci: bytes) -> str:
    """Cara yang menahan tebakan: hash berkunci."""
    return hmac.new(kunci, kode.encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def pilih_korban(baris: list[dict]) -> str:
    """Ambil satu mahasiswa didampingi dari kelompok terkecil.

    Contoh ini sengaja memakai orang yang sama di seluruh bagian, supaya
    terlihat bahwa dua kebocoran yang tampak terpisah — pengenal tersamar
    pada satu laporan, dan sel kecil pada laporan lain — menunjuk orang
    yang sama.
    """
    tabel = ringkas(baris)
    terkecil = min(tabel, key=lambda k: tabel[k]["jumlah_mahasiswa"])
    for satu in baris:
        cocok = (satu["program_studi"], int(satu["semester"])) == terkecil
        if cocok and satu["status_pendampingan"] == "Ya":
            return satu["kode_mahasiswa"]
    return baris[0]["kode_mahasiswa"]


def demo_hash_dapat_ditebak(korban: str) -> None:
    judul(1, "Hash biasa atas NIM dapat dibalik dengan menebak")

    diterbitkan = samar_hash_biasa(korban)

    print(f"  Laporan menerbitkan pengenal tersamar : {diterbitkan}")
    print("  Tidak ada NIM, tidak ada nama. Tampak aman.")
    print()
    print("  Tetapi bentuk NIM di kampus ini dapat ditebak: MHS-SYN-0001 sampai")
    print("  MHS-SYN-9999. Penyerang cukup mencoba semuanya satu per satu.")
    print()

    percobaan = 0
    ketemu = None
    for nomor in range(1, 10000):
        kandidat = f"MHS-SYN-{nomor:04d}"
        percobaan += 1
        if samar_hash_biasa(kandidat) == diterbitkan:
            ketemu = kandidat
            break

    print(f"  Setelah {percobaan} percobaan: {ketemu}")
    print()
    print("  Ruang tebakannya hanya sepuluh ribu. Sebuah laptop menyelesaikannya")
    print("  dalam hitungan milidetik. Hashnya tidak dipecahkan, melainkan ditebak.")


def demo_kunci_menahan_tebakan(korban: str) -> None:
    judul(2, "Penyamaran berkunci menahan tebakan yang sama")

    diterbitkan = samar_berkunci(korban, KUNCI_CONTOH)

    print(f"  Pengenal tersamar berkunci : {diterbitkan}")

    percobaan = 0
    ketemu = None
    for nomor in range(1, 10000):
        kandidat = f"MHS-SYN-{nomor:04d}"
        percobaan += 1
        if samar_hash_biasa(kandidat) == diterbitkan:
            ketemu = kandidat
            break

    print(f"  Setelah {percobaan} percobaan dengan cara yang sama: {ketemu}")
    print()
    print("  Penyerang harus menebak kuncinya lebih dahulu, dan kunci itu tidak")
    print("  punya bentuk yang dapat ditebak seperti NIM.")
    print()
    print("  Konsekuensinya: nilai penyamaran ini bergantung penuh pada kunci.")
    print("  Kunci bocor berarti seluruh penyamaran batal, untuk semua laporan")
    print("  yang pernah terbit memakai kunci itu — termasuk yang sudah dikirim.")

    lain = samar_berkunci(korban, b"kunci-yang-berbeda-sama-sekali-untuk-uji")
    print()
    print(f"  Mahasiswa yang sama dengan kunci berbeda : {lain}")
    print("  Mengganti kunci memutus kaitan antarlaporan. Itu melindungi, tetapi")
    print("  juga membuat dua laporan tidak lagi dapat dibandingkan.")


def ringkas(baris: list[dict]) -> dict:
    mahasiswa = collections.defaultdict(set)
    didampingi = collections.defaultdict(set)
    for satu in baris:
        kunci = (satu["program_studi"], int(satu["semester"]))
        mahasiswa[kunci].add(satu["kode_mahasiswa"])
        if satu["status_pendampingan"] == "Ya":
            didampingi[kunci].add(satu["kode_mahasiswa"])
    return {
        kunci: {
            "jumlah_mahasiswa": len(nilai),
            "jumlah_didampingi": len(didampingi[kunci]),
        }
        for kunci, nilai in mahasiswa.items()
    }


def demo_sel_kecil(baris: list[dict]) -> dict:
    judul(3, "Laporan tanpa pengenal apa pun masih menunjuk satu orang")

    tabel = ringkas(baris)
    print("  Laporan pendampingan per program studi dan semester:")
    print()
    print(f"  {'Program studi':<26} {'Sem':>4} {'Mahasiswa':>10} {'Didampingi':>11}")
    for kunci in sorted(tabel, key=lambda k: (tabel[k]["jumlah_mahasiswa"], k)):
        isi = tabel[kunci]
        print(
            f"  {kunci[0]:<26} {kunci[1]:>4} "
            f"{isi['jumlah_mahasiswa']:>10} {isi['jumlah_didampingi']:>11}"
        )

    print()
    print("  Perhatikan baris teratas. Dua mahasiswa, satu di antaranya didampingi.")
    print("  Tidak ada NIM di laporan ini. Tidak ada nama. Tetapi siapa pun yang")
    print("  tahu siapa saja dua mahasiswa itu — dosen wali, teman seangkatan,")
    print("  petugas administrasi — langsung tahu bahwa peluangnya satu berbanding")
    print("  dua, dan sering kali cukup satu keterangan tambahan untuk memastikan.")
    print()
    print("  Status pendampingan termasuk data yang perlu dilindungi. Laporan ini")
    print("  membocorkannya tanpa satu pun pengenal langsung.")
    return tabel


def demo_penekanan_tunggal(tabel: dict) -> None:
    judul(4, "Menyembunyikan satu sel saja belum menyembunyikan angkanya")

    prodi = "Manajemen Bisnis Syariah"
    sel = {k: v for k, v in tabel.items() if k[0] == prodi}
    total = sum(v["jumlah_mahasiswa"] for v in sel.values())
    disembunyikan = min(sel, key=lambda k: sel[k]["jumlah_mahasiswa"])

    print(f"  Sel yang dianggap terlalu kecil disembunyikan: {prodi} semester {disembunyikan[1]}")
    print()
    print(f"  {'Program studi':<26} {'Sem':>4} {'Mahasiswa':>10}")
    for kunci in sorted(sel):
        tampil = "*" if kunci == disembunyikan else str(sel[kunci]["jumlah_mahasiswa"])
        print(f"  {prodi:<26} {kunci[1]:>4} {tampil:>10}")
    print(f"  {'TOTAL ' + prodi:<31} {total:>10}")

    terlihat = sum(v["jumlah_mahasiswa"] for k, v in sel.items() if k != disembunyikan)
    print()
    print(f"  Penyerang menghitung: {total} - {terlihat} = {total - terlihat}")
    print(f"  Nilai yang disembunyikan kembali terbaca: {sel[disembunyikan]['jumlah_mahasiswa']}")
    print()
    print("  Selama totalnya ikut diterbitkan, satu sel yang disembunyikan selalu dapat")
    print("  dihitung dari selisih. Karena itu penyembunyian harus mengenai sedikitnya")
    print("  dua sel dalam satu kelompok penjumlahan — inilah penyembunyian sekunder,")
    print("  dan inilah yang akan Anda kerjakan pada TODO 3.")


def main() -> None:
    print("CONTOH PERTEMUAN 6 — PRIVASI DAN RISIKO RE-IDENTIFIKASI")
    print("Mata Kuliah Keamanan Data (SSD1033)")
    print()
    print(f"Dataset: {DATASET.name}")

    baris = baca_dataset()
    print(f"Jumlah baris: {len(baris)}")

    korban = pilih_korban(baris)
    demo_hash_dapat_ditebak(korban)
    demo_kunci_menahan_tebakan(korban)
    tabel = demo_sel_kecil(baris)
    demo_penekanan_tunggal(tabel)

    print()
    print(GARIS)
    print("Satu orang, dua jalan masuk")
    print(GARIS)
    print(f"  Mahasiswa pada bagian 1 dan 2 adalah {korban}.")
    print("  Ia juga orang yang sama dengan satu-satunya mahasiswa didampingi")
    print("  pada sel terkecil di bagian 3.")
    print()
    print("  Bagian 1 dan bagian 3 datang dari dua laporan berbeda yang masing-")
    print("  masing terlihat aman. Yang membuka identitasnya bukan salah satu")
    print("  laporan, melainkan keduanya sekaligus. Penilaian risiko privasi")
    print("  karena itu tidak dapat dilakukan per laporan.")

    print()
    print(GARIS)
    print("Catat empat perilaku di atas pada worksheet bagian D sebagai P06-E01.")
    print(GARIS)


if __name__ == "__main__":
    main()
