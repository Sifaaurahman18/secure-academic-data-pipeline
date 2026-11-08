"""Cadangan, pemulihan, dan pembuktiannya — Pertemuan 7.

Skrip ini sudah jadi. Isinya tiga langkah yang harus dikerjakan berurutan,
dan langkah ketiga memakai fungsi yang Anda tulis sendiri pada
`jawaban_p07.py`.

    python starter/cadangan_pulih.py --cadangkan
    python starter/cadangan_pulih.py --pulihkan backup/<berkas>.sql
    python starter/cadangan_pulih.py --verifikasi

Langkah ketiga adalah alasan dua langkah pertama ada. Cadangan yang belum
pernah dipulihkan bukan cadangan, dan baru menjadi cadangan setelah terbukti
dapat mengembalikan isi yang sama.

Pemulihan dilakukan ke basis data TERPISAH, `secure_academic_lab_pulih`,
bukan menimpa basis data laboratorium. Menguji pemulihan dengan menimpa
satu-satunya salinan yang masih hidup adalah cara yang paling sering
mengubah gangguan kecil menjadi kehilangan data.

Basis data tujuan disiapkan sekali melalui `starter/siapkan_p07.sql`.

Lokasi cadangan
---------------
Taruh skrip ini di folder starter/ pada proyek Anda dan jalankan dari akar
proyek. Berkas cadangan ditulis ke folder backup/ pada akar proyek. Folder itu
sudah terdaftar pada .gitignore proyek, sehingga cadangan, yang memuat seluruh
isi basis data, tidak ikut terkumpul. Bila proyek tidak ditemukan, cadangan
ditulis ke starter/cadangan/.

Catatan tentang kata sandi
--------------------------
Skrip ini TIDAK pernah menuliskan kata sandi pada baris perintah. Kata
sandi yang ditulis sebagai argumen dapat dibaca pengguna lain pada daftar
proses, dan ikut tersimpan pada riwayat shell. Yang dipakai di sini adalah
berkas konfigurasi sementara yang dihapus setelah perintah selesai.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

STARTER = Path(__file__).resolve().parent
sys.path.insert(0, str(STARTER))

from koneksi import (  # noqa: E402
    BASIS_DATA,
    BASIS_DATA_PULIH,
    PROYEK,
    TidakDapatTerhubung,
    _kata_sandi,
    buka,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Cadangan memuat seluruh isi basis data, jadi disimpan di backup/ pada akar proyek,
# folder yang sudah terdaftar pada .gitignore proyek.
FOLDER_CADANGAN = (PROYEK / "backup") if PROYEK else (STARTER / "cadangan")

# Lokasi mysqldump dan mysql pada pemasangan WAMP yang lazim. Dapat
# ditimpa melalui variabel lingkungan MYSQL_BIN.
KANDIDAT_BIN = (
    Path(os.environ.get("MYSQL_BIN", "")) if os.environ.get("MYSQL_BIN") else None,
    Path("C:/wamp64/bin/mysql/mysql8.4.7/bin"),
    Path("C:/wamp64/bin/mysql/mysql8.0.31/bin"),
    Path("C:/xampp/mysql/bin"),
)


class Gagal(Exception):
    """Kegagalan yang perlu dibaca pengguna."""


def cari_program(nama: str) -> Path:
    """Temukan mysqldump.exe atau mysql.exe."""
    for folder in KANDIDAT_BIN:
        if folder is None:
            continue
        calon = folder / f"{nama}.exe"
        if calon.exists():
            return calon

    from shutil import which

    ditemukan = which(nama)
    if ditemukan:
        return Path(ditemukan)

    raise Gagal(
        f"{nama} tidak ditemukan.\n"
        "  Tunjukkan foldernya melalui variabel lingkungan MYSQL_BIN, misalnya:\n"
        '    MYSQL_BIN="C:/wamp64/bin/mysql/mysql8.4.7/bin"'
    )


def berkas_konfigurasi(peran: str) -> Path:
    """Tulis kredensial ke berkas sementara berizin sempit.

    Inilah cara memberi kata sandi kepada mysqldump tanpa menaruhnya pada
    baris perintah. Berkasnya dihapus pada blok finally pemanggil.
    """
    sandi = _kata_sandi(peran)
    deskriptor, jalur = tempfile.mkstemp(prefix="p07-", suffix=".cnf", text=True)
    with os.fdopen(deskriptor, "w", encoding="utf-8") as berkas:
        berkas.write(
            "[client]\n"
            f"user={peran}\n"
            f"password={sandi}\n"
            f"host={os.environ.get('DB_HOST', '127.0.0.1')}\n"
            f"port={os.environ.get('DB_PORT', '3306')}\n"
        )
    return Path(jalur)


def jalankan(perintah: list, konfigurasi: Path, masukan: Path | None = None,
             keluaran: Path | None = None) -> None:
    lengkap = [str(perintah[0]), f"--defaults-extra-file={konfigurasi}", *perintah[1:]]

    berkas_masuk = masukan.open("rb") if masukan else None
    berkas_keluar = keluaran.open("wb") if keluaran else None
    try:
        proses = subprocess.run(
            lengkap,
            stdin=berkas_masuk,
            stdout=berkas_keluar or subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    finally:
        if berkas_masuk:
            berkas_masuk.close()
        if berkas_keluar:
            berkas_keluar.close()

    if proses.returncode != 0:
        pesan = proses.stderr.decode("utf-8", errors="replace").strip()
        raise Gagal(f"{Path(perintah[0]).name} gagal:\n  {pesan}")


def cadangkan() -> Path:
    print("MEMBUAT CADANGAN")
    FOLDER_CADANGAN.mkdir(parents=True, exist_ok=True)

    mysqldump = cari_program("mysqldump")
    cap_waktu = datetime.now().strftime("%Y%m%d-%H%M%S")
    tujuan = FOLDER_CADANGAN / f"{BASIS_DATA}-{cap_waktu}.sql"

    konfigurasi = berkas_konfigurasi("admin_lab")
    try:
        jalankan(
            [
                mysqldump,
                "--single-transaction",
                "--routines",
                "--triggers",
                "--set-gtid-purged=OFF",
                "--databases",
                BASIS_DATA,
            ],
            konfigurasi,
            keluaran=tujuan,
        )
    finally:
        konfigurasi.unlink(missing_ok=True)

    ukuran = tujuan.stat().st_size
    try:
        tampil = tujuan.relative_to(Path.cwd())
    except ValueError:
        tampil = tujuan
    print(f"  Berkas   : {tampil}")
    print(f"  Ukuran   : {ukuran:,} bita")

    if ukuran < 10_000:
        raise Gagal(
            f"berkas cadangan hanya {ukuran} bita.\n"
            "  Cadangan sekecil itu hampir pasti gagal di tengah jalan.\n"
            "  Memeriksa ukuran adalah pemeriksaan termurah yang ada, dan\n"
            "  sudah menangkap sebagian besar kegagalan senyap."
        )

    isi_akhir = tujuan.read_text(encoding="utf-8", errors="replace")[-200:]
    if "Dump completed" not in isi_akhir:
        raise Gagal(
            "berkas cadangan tidak diakhiri penanda 'Dump completed'.\n"
            "  Berarti proses berhenti sebelum selesai. Berkas seperti ini\n"
            "  tetap dapat dibuka dan dibaca, sehingga kegagalannya baru\n"
            "  ketahuan saat dipulihkan."
        )
    print("  Penanda  : Dump completed ditemukan")
    print("\n  Cadangan ini BELUM terbukti. Lanjutkan dengan:")
    print(f"    python starter/cadangan_pulih.py --pulihkan {tampil.as_posix()}")
    return tujuan


def pulihkan(berkas: Path) -> None:
    print("MEMULIHKAN KE BASIS DATA TERPISAH")
    if not berkas.exists():
        raise Gagal(f"berkas cadangan tidak ditemukan: {berkas}")

    mysql = cari_program("mysql")
    print(f"  Sumber   : {berkas.name}")
    print(f"  Tujuan   : {BASIS_DATA_PULIH}")

    # Berkas dump memuat CREATE DATABASE dan USE untuk basis data asal.
    # Keduanya diganti agar isinya masuk ke basis data tujuan, bukan
    # menimpa basis data laboratorium.
    isi = berkas.read_text(encoding="utf-8", errors="replace")
    isi = isi.replace(f"`{BASIS_DATA}`", f"`{BASIS_DATA_PULIH}`")

    # Jebakan pemulihan yang paling sering menghentikan proses di tengah:
    # definisi view membawa serta DEFINER=`root`@`localhost` dari server
    # asal. Akun yang memulihkan hanya boleh menetapkan definer atas nama
    # dirinya sendiri, kecuali akun itu memegang hak global SET_ANY_DEFINER.
    #
    # Menambah hak global itu akan membuat perintah ini berjalan, dan
    # sekaligus membatalkan rancangan hak minimum yang dibangun sejak
    # Pertemuan 4. Yang benar adalah menulis ulang definernya menjadi akun
    # yang memulihkan.
    #
    # Akibatnya perlu Anda catat: view pada hasil pemulihan berjalan dengan
    # hak admin_lab, bukan hak root. Untuk basis data uji, itu memang yang
    # diinginkan. Untuk pemulihan sungguhan ke server produksi, perbedaan
    # ini harus disengaja dan dicatat, bukan ditemukan belakangan.
    jumlah_definer = len(re.findall(r"DEFINER=`[^`]+`@`[^`]+`", isi))
    isi = re.sub(r"DEFINER=`[^`]+`@`[^`]+`", "DEFINER=CURRENT_USER", isi)
    if jumlah_definer:
        print(f"  Definer  : {jumlah_definer} definisi ditulis ulang "
              "menjadi CURRENT_USER")

    sementara = FOLDER_CADANGAN / "_pemulihan_sementara.sql"
    sementara.write_text(isi, encoding="utf-8")

    konfigurasi = berkas_konfigurasi("admin_lab")
    try:
        jalankan([mysql], konfigurasi, masukan=sementara)
    finally:
        konfigurasi.unlink(missing_ok=True)
        sementara.unlink(missing_ok=True)

    print("  Pemulihan selesai tanpa galat.")
    print("\n  Selesai tanpa galat BELUM berarti berhasil. Lanjutkan dengan")
    print("  --verifikasi, yang membandingkan jumlah baris dan checksum tabel.")


def verifikasi() -> None:
    print("MEMVERIFIKASI HASIL PEMULIHAN")

    try:
        import jawaban_p07 as jawaban
    except Exception as galat:
        raise Gagal(
            f"jawaban_p07.py tidak dapat dimuat ({type(galat).__name__}: {galat})."
        ) from galat

    asal_koneksi = buka("admin_lab", BASIS_DATA)
    pulih_koneksi = buka("admin_lab", BASIS_DATA_PULIH)
    try:
        asal = jawaban.ringkasan_tabel(asal_koneksi.cursor())
        pulih = jawaban.ringkasan_tabel(pulih_koneksi.cursor())
    finally:
        asal_koneksi.close()
        pulih_koneksi.close()

    print(f"\n  {'Tabel':<18} {'Asal':>18} {'Pemulihan':>18}")
    for nama in sorted(asal):
        kiri = asal[nama]
        kanan = pulih.get(nama, ("-", "-"))
        print(
            f"  {nama:<18} {str(kiri[0]) + ' / ' + str(kiri[1]):>18} "
            f"{str(kanan[0]) + ' / ' + str(kanan[1]):>18}"
        )
    print("  (jumlah baris / checksum)")

    laporan = jawaban.bandingkan(asal, pulih)
    if laporan:
        print("\n  PERBEDAAN DITEMUKAN:")
        for baris in laporan:
            print(f"    - {baris}")
        raise Gagal(
            "pemulihan tidak menghasilkan isi yang sama.\n"
            "  Cadangan ini belum dapat diandalkan."
        )

    print("\n  Tidak ada perbedaan terdeteksi pada lima tabel yang diperiksa.")
    print("  Pemeriksaan checksum memberi bukti kuat, tetapi bukan perbandingan")
    print("  setiap baris dan bukan jaminan mutlak seluruh basis data identik.")
    print("  Catat tanggal pembuktian ini pada worksheet bagian F; cadangan")
    print("  yang terbukti bulan lalu tidak membuktikan apa pun tentang")
    print("  cadangan yang dibuat hari ini.")


def main() -> None:
    pengurai = argparse.ArgumentParser(
        description="Cadangan, pemulihan, dan pembuktiannya untuk Pertemuan 7."
    )
    kelompok = pengurai.add_mutually_exclusive_group(required=True)
    kelompok.add_argument("--cadangkan", action="store_true",
                          help="buat berkas cadangan baru")
    kelompok.add_argument("--pulihkan", metavar="BERKAS",
                          help="pulihkan berkas cadangan ke basis data terpisah")
    kelompok.add_argument("--verifikasi", action="store_true",
                          help="bandingkan isi basis data asal dan hasil pemulihan")
    argumen = pengurai.parse_args()

    try:
        if argumen.cadangkan:
            cadangkan()
        elif argumen.pulihkan:
            pulihkan(Path(argumen.pulihkan))
        else:
            verifikasi()
    except (Gagal, TidakDapatTerhubung) as galat:
        print(f"\nGAGAL: {galat}")
        raise SystemExit(1)
    except NotImplementedError as galat:
        print(f"\nBELUM SELESAI: {galat}")
        print("\n  TODO 4 pada jawaban_p07.py belum dilengkapi.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
