"""Pemeriksaan hasil praktikum Pertemuan 4.

Skrip ini terhubung ke basis data `secure_academic_lab` pada komputer Anda dan
memeriksa apakah role, akun, dan hak aksesnya sesuai rancangan praktikum.

Yang diperiksa:

    1. empat role bawaan ada dengan hak yang tepat;
    2. lima akun ada, memegang role yang benar, dan role-nya sudah aktif;
    3. tidak ada hak berlebih pada akun mana pun;
    4. tantangan `asisten_dosen` memenuhi kebutuhan tanpa hak berlebih.

Simpan skrip ini di folder `secure-academic-data-pipeline`, lalu dari folder itu
jalankan:

    python periksa_hasil_p04.py

Skrip meminta kata sandi akun administrator MySQL saat berjalan. Kata sandi
tidak disimpan ke berkas mana pun. Jalankan dari terminal sungguhan, misalnya
Git Bash atau terminal bawaan VS Code; permintaan kata sandi memakai getpass
yang membaca langsung dari konsol.

Ganti akun administrator melalui variabel lingkungan bila perlu:

    DB_HOST        bawaan 127.0.0.1
    DB_PORT        bawaan 3306
    DB_ADMIN_USER  bawaan root

Skrip ini hanya membaca dan tidak mengubah satu pun hak akses.
"""

from __future__ import annotations

import getpass
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASIS_DATA = "secure_academic_lab"

# Rancangan yang diajarkan pada roles.sql.
RANCANGAN_ROLE = {
    "r_app_service": {
        ("v_nilai_mahasiswa", "SELECT"),
        ("v_ringkasan_kelulusan", "SELECT"),
        ("log_aktivitas", "INSERT"),
    },
    "r_analyst": {
        ("v_ringkasan_kelulusan", "SELECT"),
        ("v_ringkasan_pendampingan", "SELECT"),
    },
    "r_operator_pipeline": {
        ("staging_nilai", "INSERT"),
        ("staging_nilai", "SELECT"),
        ("mata_kuliah", "SELECT"),
        ("log_aktivitas", "INSERT"),
    },
    "r_auditor": {
        ("log_aktivitas", "SELECT"),
    },
}

AKUN_ROLE = {
    "app_service": "r_app_service",
    "analyst": "r_analyst",
    "operator_pipeline": "r_operator_pipeline",
    "auditor": "r_auditor",
}

# --- Tantangan: asisten_dosen ------------------------------------------------
#
# Tugasnya menyiapkan berkas nilai untuk diunggah, lalu memeriksa laporan
# agregat kelulusan. Dua hak berikut wajib ada karena tanpanya tugas itu tidak
# dapat dikerjakan.
TANTANGAN_WAJIB = {
    ("staging_nilai", "INSERT"),
    ("v_ringkasan_kelulusan", "SELECT"),
}

# Boleh ada, boleh tidak. Alasan keduanya dapat dipertahankan: membaca
# kembali unggahan sendiri, dan memvalidasi kode mata kuliah.
TANTANGAN_BOLEH = {
    ("staging_nilai", "SELECT"),
    ("mata_kuliah", "SELECT"),
}

# Objek yang tidak boleh dijangkau sama sekali oleh asisten dosen.
TANTANGAN_TERLARANG_OBJEK = {
    "mahasiswa",
    "nilai_akademik",
    "v_nilai_mahasiswa",
    "v_ringkasan_pendampingan",
    "log_aktivitas",
}

# Operasi yang tidak boleh dimiliki asisten dosen pada objek mana pun.
TANTANGAN_TERLARANG_OPERASI = {
    "UPDATE", "DELETE", "DROP", "ALTER",
    "CREATE", "GRANT OPTION", "INDEX", "REFERENCES",
}

AKUN_TANTANGAN = "asisten_dosen"


class Gagal(Exception):
    """Kegagalan pemeriksaan yang perlu diperbaiki mahasiswa."""


def bagian(judul: str) -> None:
    print(f"\n== {judul} ==")


def hasil(label: str, nilai: str) -> None:
    print(f"  {label:<34}: {nilai}")


def hak_efektif(kursor, nama_akun: str) -> set[tuple[str, str]]:
    """Menghitung hak sebuah akun: hak langsung ditambah hak dari role."""
    pemegang = {f"'{nama_akun}'@'localhost'"}

    kursor.execute(
        "SELECT FROM_USER, FROM_HOST FROM mysql.role_edges "
        "WHERE TO_USER = %s AND TO_HOST = 'localhost'",
        (nama_akun,),
    )
    for role_user, role_host in kursor.fetchall():
        pemegang.add(f"'{role_user}'@'{role_host}'")

    hak: set[tuple[str, str]] = set()
    for grantee in pemegang:
        kursor.execute(
            "SELECT TABLE_NAME, PRIVILEGE_TYPE FROM information_schema.table_privileges "
            "WHERE TABLE_SCHEMA = %s AND GRANTEE = %s",
            (BASIS_DATA, grantee),
        )
        hak.update((t, p) for t, p in kursor.fetchall())

        kursor.execute(
            "SELECT TABLE_NAME, PRIVILEGE_TYPE FROM information_schema.column_privileges "
            "WHERE TABLE_SCHEMA = %s AND GRANTEE = %s",
            (BASIS_DATA, grantee),
        )
        hak.update((t, p) for t, p in kursor.fetchall())

        # Hak tingkat skema tercatat terpisah dan mencakup seluruh objek.
        kursor.execute(
            "SELECT PRIVILEGE_TYPE FROM information_schema.schema_privileges "
            "WHERE TABLE_SCHEMA = %s AND GRANTEE = %s",
            (BASIS_DATA, grantee),
        )
        hak.update(("*", p) for (p,) in kursor.fetchall())

    return hak


def periksa_role(kursor) -> None:
    bagian("1. Role bawaan")
    for nama_role, diharapkan in RANCANGAN_ROLE.items():
        # Host dikirim sebagai parameter, bukan ditulis di dalam SQL. Tanda
        # persen literal diperlakukan berbeda oleh masing-masing driver.
        kursor.execute(
            "SELECT COUNT(*) FROM mysql.user WHERE user = %s AND host = %s",
            (nama_role, "%"),
        )
        if kursor.fetchone()[0] == 0:
            raise Gagal(
                f"role '{nama_role}' tidak ditemukan.\n"
                "  Jalankan database/roles.sql, dan pastikan tidak berhenti di tengah."
            )

        kursor.execute(
            "SELECT TABLE_NAME, PRIVILEGE_TYPE FROM information_schema.table_privileges "
            "WHERE TABLE_SCHEMA = %s AND GRANTEE = %s",
            (BASIS_DATA, f"'{nama_role}'@'%'"),
        )
        aktual = {(t, p) for t, p in kursor.fetchall()}

        kurang = diharapkan - aktual
        lebih = aktual - diharapkan
        if kurang:
            raise Gagal(
                f"role '{nama_role}' kekurangan hak: {sorted(kurang)}.\n"
                "  Periksa kembali bagian 2 pada roles.sql."
            )
        if lebih:
            raise Gagal(
                f"role '{nama_role}' memiliki hak berlebih: {sorted(lebih)}.\n"
                "  Hak yang tidak dibutuhkan melanggar prinsip hak minimum."
            )
        hasil(nama_role, f"{len(aktual)} hak, sesuai rancangan")


def periksa_akun(kursor) -> None:
    bagian("2. Akun dan role aktif")
    for nama_akun, nama_role in AKUN_ROLE.items():
        kursor.execute(
            "SELECT COUNT(*) FROM mysql.user WHERE user = %s AND host = 'localhost'",
            (nama_akun,),
        )
        if kursor.fetchone()[0] == 0:
            raise Gagal(
                f"akun '{nama_akun}'@'localhost' tidak ditemukan.\n"
                "  Jalankan database/roles.sql bagian 3."
            )

        kursor.execute(
            "SELECT COUNT(*) FROM mysql.role_edges "
            "WHERE FROM_USER = %s AND TO_USER = %s AND TO_HOST = 'localhost'",
            (nama_role, nama_akun),
        )
        if kursor.fetchone()[0] == 0:
            raise Gagal(
                f"akun '{nama_akun}' belum memegang role '{nama_role}'.\n"
                "  Periksa perintah GRANT pada roles.sql bagian 4."
            )

        kursor.execute(
            "SELECT COUNT(*) FROM mysql.default_roles "
            "WHERE USER = %s AND HOST = 'localhost'",
            (nama_akun,),
        )
        if kursor.fetchone()[0] == 0:
            raise Gagal(
                f"akun '{nama_akun}' belum memiliki default role.\n"
                "  Tanpa SET DEFAULT ROLE, akun terhubung tanpa hak apa pun dan\n"
                "  setiap query akan ditolak walaupun role sudah diberikan."
            )
        hasil(nama_akun, f"memegang {nama_role}, role aktif")

    kursor.execute(
        "SELECT COUNT(*) FROM mysql.user WHERE user = 'admin_lab' AND host = 'localhost'"
    )
    if kursor.fetchone()[0] == 0:
        raise Gagal("akun 'admin_lab'@'localhost' tidak ditemukan.")
    hasil("admin_lab", "ada")


def periksa_hak_berlebih(kursor) -> None:
    bagian("3. Hak berlebih pada akun aplikasi")
    for nama_akun in AKUN_ROLE:
        kursor.execute(
            "SELECT PRIVILEGE_TYPE FROM information_schema.user_privileges "
            "WHERE GRANTEE = %s AND PRIVILEGE_TYPE <> 'USAGE'",
            (f"'{nama_akun}'@'localhost'",),
        )
        hak_global = [p for (p,) in kursor.fetchall()]
        if hak_global:
            raise Gagal(
                f"akun '{nama_akun}' memiliki hak global: {sorted(hak_global)}.\n"
                "  Hak pada *.* memberi akses ke seluruh basis data pada server,\n"
                "  termasuk basis data yang tidak ada hubungannya dengan praktikum."
            )

        kursor.execute(
            "SELECT PRIVILEGE_TYPE FROM information_schema.schema_privileges "
            "WHERE GRANTEE = %s",
            (f"'{nama_akun}'@'localhost'",),
        )
        hak_skema = [p for (p,) in kursor.fetchall()]
        if hak_skema:
            raise Gagal(
                f"akun '{nama_akun}' memiliki hak tingkat skema: {sorted(hak_skema)}.\n"
                "  Hak tingkat skema mencakup seluruh tabel dan view, termasuk yang\n"
                "  tidak dibutuhkan akun ini."
            )
    hasil("akun aplikasi", "tidak ada hak global maupun skema")


def periksa_tantangan(kursor) -> list[str]:
    bagian("4. Tantangan asisten_dosen")
    catatan: list[str] = []

    kursor.execute(
        "SELECT COUNT(*) FROM mysql.user WHERE user = %s AND host = 'localhost'",
        (AKUN_TANTANGAN,),
    )
    if kursor.fetchone()[0] == 0:
        raise Gagal(
            f"akun '{AKUN_TANTANGAN}'@'localhost' belum dibuat.\n"
            "  Tantangan minimum pada bagian 9 materi belum dikerjakan."
        )

    kursor.execute(
        "SELECT COUNT(*) FROM mysql.role_edges WHERE TO_USER = %s AND TO_HOST = 'localhost'",
        (AKUN_TANTANGAN,),
    )
    pakai_role = kursor.fetchone()[0] > 0
    if not pakai_role:
        catatan.append(
            "asisten_dosen memperoleh hak langsung, bukan melalui role. "
            "Berjalan, tetapi menyimpang dari pola yang diajarkan"
        )

    hak = hak_efektif(kursor, AKUN_TANTANGAN)

    kurang = TANTANGAN_WAJIB - hak
    if kurang:
        raise Gagal(
            f"asisten_dosen belum dapat menjalankan tugasnya. Hak yang kurang: {sorted(kurang)}.\n"
            "  Tugasnya menyiapkan berkas nilai untuk diunggah, lalu memeriksa\n"
            "  laporan agregat kelulusan."
        )

    terlarang = sorted(
        (objek, operasi)
        for objek, operasi in hak
        if objek in TANTANGAN_TERLARANG_OBJEK
        or operasi in TANTANGAN_TERLARANG_OPERASI
        or objek == "*"
    )
    if terlarang:
        raise Gagal(
            f"asisten_dosen memiliki hak yang tidak dibutuhkan: {terlarang}.\n"
            "  Untuk setiap hak, tanyakan tugas mana yang gagal bila hak itu dicabut.\n"
            "  Bila tidak ada tugas yang gagal, hak itu tidak dibutuhkan."
        )

    lebih = hak - TANTANGAN_WAJIB - TANTANGAN_BOLEH
    if lebih:
        catatan.append(
            f"asisten_dosen memiliki hak di luar daftar yang diharapkan: {sorted(lebih)}. "
            "Bukan pelanggaran otomatis, tetapi siapkan alasannya"
        )

    hasil("hak wajib", "lengkap")
    hasil("hak terlarang", "tidak ditemukan")
    hasil("jumlah hak efektif", str(len(hak)))
    return catatan


def main() -> None:
    print("PEMERIKSAAN HASIL PRAKTIKUM P04")
    print("Mata Kuliah Keamanan Data (SSD1033)")

    try:
        import mysql.connector
        from mysql.connector import Error as MySQLError
    except ImportError:
        print("\nGAGAL: pustaka mysql-connector-python belum terpasang.")
        print("  Jalankan: python -m pip install mysql-connector-python")
        raise SystemExit(1)

    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = int(os.environ.get("DB_PORT", "3306"))
    user = os.environ.get("DB_ADMIN_USER", "root")

    bagian("0. Koneksi")
    hasil("Host", f"{host}:{port}")
    hasil("Akun administrator", user)
    print("\nMasukkan kata sandi akun administrator MySQL.")
    print("Kata sandi tidak ditampilkan dan tidak disimpan ke berkas mana pun.")
    sandi = getpass.getpass("Kata sandi: ")

    try:
        koneksi = mysql.connector.connect(
            host=host, port=port, user=user, password=sandi, connection_timeout=10
        )
    except MySQLError as galat:
        print(f"\nGAGAL: tidak dapat terhubung ke MySQL ({galat.errno}: {galat.msg}).")
        print("  Pastikan layanan MySQL berjalan dan kata sandi administrator benar.")
        raise SystemExit(1)
    sandi = ""

    kursor = koneksi.cursor()
    try:
        kursor.execute(
            "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = %s",
            (BASIS_DATA,),
        )
        if kursor.fetchone()[0] == 0:
            raise Gagal(
                f"basis data '{BASIS_DATA}' tidak ditemukan.\n"
                "  Jalankan database/schema.sql terlebih dahulu."
            )

        kursor.execute(f"SELECT COUNT(*) FROM {BASIS_DATA}.nilai_akademik")
        jumlah = kursor.fetchone()[0]
        if jumlah != 808:
            raise Gagal(
                f"tabel nilai_akademik berisi {jumlah} baris, seharusnya 808.\n"
                "  Jalankan ulang database/seed_data.sql."
            )
        hasil("Basis data", f"{BASIS_DATA}, {jumlah} catatan nilai")

        periksa_role(kursor)
        periksa_akun(kursor)
        periksa_hak_berlebih(kursor)
        catatan = periksa_tantangan(kursor)

    except Gagal as galat:
        print(f"\nGAGAL: {galat}")
        print(
            "\nPerbaiki lalu jalankan ulang skrip ini. Catat pesan di atas pada\n"
            "worksheet bagian H bila Anda memerlukan bantuan."
        )
        raise SystemExit(1)
    finally:
        kursor.close()
        koneksi.close()

    print()
    for baris in catatan:
        print(f"Catatan               : {baris}")
    print("HASIL PRAKTIKUM P04 SESUAI RANCANGAN")
    print(
        "\nSalin keluaran ini ke worksheet bagian H sebagai P04-E04.\n"
        "Sanitasi nama komputer bila muncul. Jangan menyalin kata sandi."
    )


if __name__ == "__main__":
    main()
