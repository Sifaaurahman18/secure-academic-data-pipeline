"""Pembuat dataset sintetik Secure Academic Data Pipeline.

Skrip ini hanya memakai pustaka standar Python. Seluruh data yang dihasilkan
bersifat buatan dan tidak mewakili mahasiswa, akun, atau nilai nyata.

Keluaran:

    data/referensi_mata_kuliah.csv          referensi kode mata kuliah
    data/raw/akademik_sintetik_raw.csv      masukan pipeline; memuat cacat yang disengaja
    data/processed/akademik_sintetik_bersih.csv  hasil yang diharapkan setelah validasi
    database/seed_data.sql                  seed MySQL untuk praktikum P04
    data/manifest.sha256                    hash SHA-256 seluruh aset data

Penggunaan:

    python tools/buat_dataset.py                  # seed bawaan, hasil selalu sama
    python tools/buat_dataset.py --seed 2026      # varian lain untuk kelas paralel
    python tools/buat_dataset.py --mahasiswa 300  # ukuran berbeda

Dosen dapat mengganti seed agar setiap kelas menerima dataset yang berbeda
tanpa mengubah aturan validasi maupun struktur kolom.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]

FILE_REFERENSI = ROOT / "data" / "referensi_mata_kuliah.csv"
FILE_RAW = ROOT / "data" / "raw" / "akademik_sintetik_raw.csv"
FILE_BERSIH = ROOT / "data" / "processed" / "akademik_sintetik_bersih.csv"
FILE_SEED = ROOT / "database" / "seed_data.sql"
FILE_MANIFEST = ROOT / "data" / "manifest.sha256"

KOLOM = [
    "record_id",
    "kode_mahasiswa",
    "program_studi",
    "semester",
    "kode_mk",
    "nilai_angka",
    "persentase_kehadiran",
    "status_kelulusan",
    "status_pendampingan",
    "waktu_pembaruan",
]

PROGRAM_STUDI = [
    ("Sains Data", 40),
    ("Ekonomi Syariah", 30),
    ("Akuntansi Syariah", 20),
    ("Manajemen Bisnis Syariah", 10),
]

MATA_KULIAH = [
    ("SSD1011", "Dasar Pemrograman", 3),
    ("SSD1022", "Basis Data", 3),
    ("SSD1033", "Keamanan Data", 3),
    ("SSD1044", "Statistika Terapan", 3),
    ("SSD1055", "Analisis Data Eksploratif", 3),
    ("SSD1066", "Pembelajaran Mesin", 3),
    ("SSD1077", "Etika Data dan Profesi", 2),
    ("SSD1088", "Visualisasi Data", 2),
]

SEMESTER_TERSEDIA = [1, 3, 5, 7]

# Aturan kelulusan yang harus divalidasi pipeline pada P10.
BATAS_NILAI_LULUS = 60
BATAS_KEHADIRAN_LULUS = 75

WAKTU_AWAL = datetime(2026, 7, 1, 8, 0, 0)


def tentukan_kelulusan(nilai: int, kehadiran: int) -> str:
    lulus = nilai >= BATAS_NILAI_LULUS and kehadiran >= BATAS_KEHADIRAN_LULUS
    return "Lulus" if lulus else "Tidak Lulus"


def buat_baris_valid(rng: random.Random, jumlah_mahasiswa: int) -> list[dict[str, str]]:
    """Membuat baris yang seluruhnya lolos aturan validasi."""
    bobot_prodi = [nama for nama, bobot in PROGRAM_STUDI for _ in range(bobot)]

    mahasiswa: list[tuple[str, str, int]] = []
    for nomor in range(1, jumlah_mahasiswa + 1):
        kode = f"MHS-SYN-{nomor:04d}"
        prodi = rng.choice(bobot_prodi)
        semester = rng.choice(SEMESTER_TERSEDIA)
        mahasiswa.append((kode, prodi, semester))

    # Sel kecil yang disengaja untuk pembahasan risiko re-identifikasi pada P06:
    # kombinasi Manajemen Bisnis Syariah semester 7 dibuat hanya berisi dua
    # mahasiswa, dan hanya satu di antaranya berstatus didampingi. Laporan
    # agregat karena itu dapat menunjuk satu orang tertentu.
    mahasiswa = [
        (kode, prodi, 5 if (prodi == "Manajemen Bisnis Syariah" and semester == 7) else semester)
        for kode, prodi, semester in mahasiswa
    ]
    mahasiswa.append((f"MHS-SYN-{jumlah_mahasiswa + 1:04d}", "Manajemen Bisnis Syariah", 7))
    mahasiswa.append((f"MHS-SYN-{jumlah_mahasiswa + 2:04d}", "Manajemen Bisnis Syariah", 7))
    sel_kecil = {mahasiswa[-1][0], mahasiswa[-2][0]}

    baris: list[dict[str, str]] = []
    nomor_record = 0
    waktu = WAKTU_AWAL

    for kode, prodi, semester in mahasiswa:
        for kode_mk, _nama, _sks in rng.sample(MATA_KULIAH, k=4):
            nomor_record += 1
            waktu = waktu + timedelta(minutes=rng.randint(1, 4))

            nilai = max(0, min(100, int(rng.gauss(74, 13))))
            kehadiran = max(0, min(100, int(rng.gauss(86, 11))))

            if kode in sel_kecil:
                # Hanya satu dari dua mahasiswa pada sel kecil yang didampingi,
                # sehingga laporan agregat dapat menunjuk satu orang.
                pendampingan = "Ya" if kode == min(sel_kecil) else "Tidak"
            else:
                pendampingan = "Ya" if rng.random() < 0.12 else "Tidak"

            baris.append(
                {
                    "record_id": f"R{nomor_record:05d}",
                    "kode_mahasiswa": kode,
                    "program_studi": prodi,
                    "semester": str(semester),
                    "kode_mk": kode_mk,
                    "nilai_angka": str(nilai),
                    "persentase_kehadiran": str(kehadiran),
                    "status_kelulusan": tentukan_kelulusan(nilai, kehadiran),
                    "status_pendampingan": pendampingan,
                    "waktu_pembaruan": waktu.strftime("%Y-%m-%dT%H:%M:%S"),
                }
            )

    return baris


def buat_baris_cacat(valid: list[dict[str, str]]) -> list[dict[str, str]]:
    """Membuat baris bermasalah yang harus ditolak pipeline pada P10.

    Setiap cacat mewakili satu aturan validasi yang berbeda sehingga mahasiswa
    dapat menghubungkan temuan dengan aturan yang gagal, bukan sekadar
    menghitung baris yang ditolak.
    """
    cacat: list[dict[str, str]] = []
    nomor = 0

    def salin(_sumber: object = None, **ubah: str) -> dict[str, str]:
        """Membuat satu baris cacat di atas basis yang sah.

        Baris cacat memakai identitas mahasiswa tersendiri (`MHS-SYN-9xxx`)
        supaya setiap baris hanya melanggar satu aturan. Bila baris cacat
        disalin dari baris valid, kunci alami kode_mahasiswa + kode_mk +
        semester ikut terduplikasi dan latihan deduplikasi pada P10 menjadi
        rancu.
        """
        nonlocal nomor
        nomor += 1
        kode_mk = MATA_KULIAH[nomor % len(MATA_KULIAH)][0]
        semester = SEMESTER_TERSEDIA[nomor % len(SEMESTER_TERSEDIA)]
        nilai = 60 + (nomor * 7) % 35
        kehadiran = 76 + (nomor * 5) % 22
        waktu = WAKTU_AWAL + timedelta(days=3, minutes=nomor * 3)
        baris = {
            "record_id": f"X{nomor:05d}",
            "kode_mahasiswa": f"MHS-SYN-9{nomor:03d}",
            "program_studi": PROGRAM_STUDI[nomor % len(PROGRAM_STUDI)][0],
            "semester": str(semester),
            "kode_mk": kode_mk,
            "nilai_angka": str(nilai),
            "persentase_kehadiran": str(kehadiran),
            "status_kelulusan": tentukan_kelulusan(nilai, kehadiran),
            "status_pendampingan": "Tidak",
            "waktu_pembaruan": waktu.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        baris.update(ubah)
        return baris

    # 1. Nilai di luar rentang 0-100.
    cacat.append(salin(nilai_angka="105"))
    cacat.append(salin(nilai_angka="132"))
    cacat.append(salin(nilai_angka="-8"))

    # 2. Nilai bukan bilangan.
    cacat.append(salin(nilai_angka="N/A"))
    cacat.append(salin(nilai_angka="delapan puluh"))

    # 3. Nilai wajib kosong.
    cacat.append(salin(nilai_angka=""))
    cacat.append(salin(kode_mahasiswa=""))

    # 4. Kehadiran di luar rentang.
    cacat.append(salin(persentase_kehadiran="118"))
    cacat.append(salin(persentase_kehadiran="-3"))

    # 5. Status kelulusan tidak konsisten dengan nilai dan kehadiran.
    cacat.append(salin(nilai_angka="41", persentase_kehadiran="52", status_kelulusan="Lulus"))
    cacat.append(salin(nilai_angka="88", persentase_kehadiran="93", status_kelulusan="Tidak Lulus"))
    cacat.append(salin(status_kelulusan="LULUS"))

    # 6. Format waktu tidak sah.
    cacat.append(salin(waktu_pembaruan="01/08/2026 09:15"))
    cacat.append(salin(waktu_pembaruan="2026-13-45T99:00:00"))

    # 7. Program studi tidak konsisten penulisannya.
    cacat.append(salin(program_studi="sains data"))
    cacat.append(salin(program_studi=" Sains  Data "))
    cacat.append(salin(program_studi="Sains Data (SD)"))

    # 8. Kode mata kuliah tidak ada pada referensi.
    cacat.append(salin(kode_mk="SSD9999"))
    cacat.append(salin(kode_mk="ssd1022"))

    # 9. Nilai status pendampingan di luar daftar yang diizinkan.
    cacat.append(salin(status_pendampingan="belum diketahui"))

    # 10. Semester di luar daftar yang diizinkan.
    cacat.append(salin(semester="0"))

    # 11. record_id ganda dan kunci alami ganda.
    duplikat_id = dict(valid[10])
    cacat.append(duplikat_id)

    duplikat_alami = dict(valid[25])
    duplikat_alami["record_id"] = "X00099"
    nilai_baru = min(100, int(valid[25]["nilai_angka"]) + 5)
    duplikat_alami["nilai_angka"] = str(nilai_baru)
    duplikat_alami["status_kelulusan"] = tentukan_kelulusan(
        nilai_baru, int(valid[25]["persentase_kehadiran"])
    )
    cacat.append(duplikat_alami)

    return cacat


def tulis_csv(path: Path, baris: list[dict[str, str]], kolom: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=kolom, lineterminator="\n")
        writer.writeheader()
        writer.writerows(baris)


def tulis_seed_sql(path: Path, baris: list[dict[str, str]]) -> None:
    """Menulis seed MySQL sebagai INSERT bertahap.

    Perintah INSERT dipilih agar seed dapat dijalankan dari MySQL Workbench
    tanpa memerlukan hak akses berkas seperti pada LOAD DATA INFILE.
    """

    def kutip(nilai: str) -> str:
        return "'" + nilai.replace("\\", "\\\\").replace("'", "''") + "'"

    mahasiswa: dict[str, tuple[str, str]] = {}
    for row in baris:
        mahasiswa.setdefault(row["kode_mahasiswa"], (row["program_studi"], row["semester"]))

    bagian: list[str] = [
        "-- Seed data Secure Academic Data Pipeline",
        "-- Dihasilkan oleh tools/buat_dataset.py. Jangan disunting manual.",
        "-- Seluruh isi berkas ini adalah data sintetik untuk laboratorium.",
        "",
        "USE secure_academic_lab;",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "TRUNCATE TABLE nilai_akademik;",
        "TRUNCATE TABLE staging_nilai;",
        "TRUNCATE TABLE mahasiswa;",
        "TRUNCATE TABLE mata_kuliah;",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
        "-- Referensi mata kuliah",
    ]

    nilai_mk = ", ".join(
        f"({kutip(kode)}, {kutip(nama)}, {sks})" for kode, nama, sks in MATA_KULIAH
    )
    bagian.append(f"INSERT INTO mata_kuliah (kode_mk, nama_mk, sks) VALUES {nilai_mk};")
    bagian.append("")
    bagian.append("-- Identitas mahasiswa sintetik")

    daftar_mhs = sorted(mahasiswa.items())
    for awal in range(0, len(daftar_mhs), 50):
        potongan = daftar_mhs[awal : awal + 50]
        nilai = ",\n  ".join(
            f"({kutip(kode)}, {kutip(prodi)}, {semester})" for kode, (prodi, semester) in potongan
        )
        bagian.append(
            "INSERT INTO mahasiswa (kode_mahasiswa, program_studi, semester) VALUES\n  "
            + nilai
            + ";"
        )

    bagian.append("")
    bagian.append("-- Catatan nilai akademik yang sudah tervalidasi")

    for awal in range(0, len(baris), 50):
        potongan = baris[awal : awal + 50]
        nilai = ",\n  ".join(
            "("
            + ", ".join(
                [
                    kutip(row["record_id"]),
                    kutip(row["kode_mahasiswa"]),
                    kutip(row["kode_mk"]),
                    row["semester"],
                    row["nilai_angka"],
                    row["persentase_kehadiran"],
                    kutip(row["status_kelulusan"]),
                    kutip(row["status_pendampingan"]),
                    kutip(row["waktu_pembaruan"].replace("T", " ")),
                ]
            )
            + ")"
            for row in potongan
        )
        bagian.append(
            "INSERT INTO nilai_akademik\n"
            "  (record_id, kode_mahasiswa, kode_mk, semester, nilai_angka,\n"
            "   persentase_kehadiran, status_kelulusan, status_pendampingan, waktu_pembaruan)\n"
            "VALUES\n  " + nilai + ";"
        )

    bagian.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(bagian), encoding="utf-8")


def tulis_manifest(path: Path, berkas: list[Path]) -> None:
    baris = []
    for item in sorted(berkas, key=lambda p: p.relative_to(ROOT).as_posix()):
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        baris.append(f"{digest} *{item.relative_to(ROOT).as_posix()}")
    path.write_text("\n".join(baris) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260828, help="seed acak; hasil deterministik")
    parser.add_argument("--mahasiswa", type=int, default=200, help="jumlah mahasiswa sintetik")
    argumen = parser.parse_args()

    rng = random.Random(argumen.seed)

    valid = buat_baris_valid(rng, argumen.mahasiswa)
    cacat = buat_baris_cacat(valid)

    mentah = valid + cacat
    rng.shuffle(mentah)

    tulis_csv(FILE_REFERENSI, [
        {"kode_mk": kode, "nama_mk": nama, "sks": str(sks)} for kode, nama, sks in MATA_KULIAH
    ], ["kode_mk", "nama_mk", "sks"])
    tulis_csv(FILE_RAW, mentah, KOLOM)
    tulis_csv(FILE_BERSIH, valid, KOLOM)
    tulis_seed_sql(FILE_SEED, valid)
    tulis_manifest(FILE_MANIFEST, [FILE_REFERENSI, FILE_RAW, FILE_BERSIH])

    jumlah_pendamping = sum(1 for row in valid if row["status_pendampingan"] == "Ya")
    print("PEMBUATAN DATASET PROYEK")
    print(f"Seed                 : {argumen.seed}")
    print(f"Mahasiswa sintetik   : {len({row['kode_mahasiswa'] for row in valid})}")
    print(f"Baris bersih         : {len(valid)}")
    print(f"Baris cacat disengaja: {len(cacat)}")
    print(f"Baris mentah         : {len(mentah)}")
    print(f"Status pendampingan Ya: {jumlah_pendamping}")
    print(f"Referensi mata kuliah: {len(MATA_KULIAH)}")
    print("Manifest SHA-256     : ditulis ulang")
    print("DATASET PROYEK SIAP DIGUNAKAN")


if __name__ == "__main__":
    main()
