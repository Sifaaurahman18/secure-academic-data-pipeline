"""Pemeriksaan hasil Pertemuan 9 — hardening starter API.

Skrip ini menguji PERILAKU layanan, bukan bentuk kode Anda. Tidak ada satu pun
pemeriksaan yang mencari kata tertentu di dalam berkas Anda, kecuali satu:
pemeriksaan terakhir yang memastikan tidak ada kunci API yang tertulis di dalam
kode. Selebihnya, cara Anda menulis perbaikan bebas selama layanannya berlaku
sebagaimana mestinya.

Menjalankan, dari folder mana pun:

    python "starter/periksa_hasil_p09.py"

Syarat sebelum menjalankan:

    1. MySQL menyala dan basis data `secure_academic_lab` sudah dimuat;
    2. berkas `.env` proyek memuat ketiga kunci API;
    3. pustaka pada requirements.txt sudah terpasang.

Skrip ini mengubah keadaan basis data hanya melalui satu jalur: baris log yang
memang ditulis layanan ketika layanan itu dipanggil. Tidak ada tabel yang dibuat,
diubah, atau dihapus.

Lolosnya pemeriksa adalah syarat lulus praktikum, bukan nilainya.
"""

# =============================================================================
# CARA MEMBACA SKRIP INI
# =============================================================================
# Skrip ini adalah "penguji dari luar" untuk API Anda. Ia tidak membuka server:
# ia memakai TestClient dari FastAPI, yaitu "klien palsu" yang memanggil aplikasi
# langsung di dalam proses yang sama, seolah-olah Swagger UI atau curl yang
# mengirim permintaan. Karena itu server uvicorn TIDAK perlu menyala.
#
# Pola setiap pemeriksaan sama:
#   1. kirim permintaan (klien.get(...)) dengan kunci API tertentu;
#   2. status_diharapkan() membandingkan kode status balasan (200, 400, 401, 403,
#      500) dengan yang seharusnya; bila berbeda, Gagal dilempar dengan pesan
#      yang menjelaskan kelemahan apa yang belum tertutup;
#   3. lapor() mencetak satu baris keterangan bila lolos.
#
# Urutan jalannya: main() menyiapkan lingkungan, lalu menjalankan enam pemeriksaan
# berurutan (satu per TODO, ditambah kebersihan sumber). Pemeriksaan berhenti pada
# kegagalan PERTAMA; perbaiki, lalu jalankan ulang untuk melihat pesan berikutnya.
#
# Tiga kunci API dipakai bergantian untuk menyamar sebagai tiga peran:
# API_KEY_MAHASISWA, API_KEY_DOSEN_WALI, dan API_KEY_ANALIS (dari .env proyek).
#
# Isi berkas ini: konstanta dan alat bantu cetak, siapkan() untuk memeriksa
# lingkungan, enam fungsi periksa_*, pelapor galat, dan main() di bagian bawah.
# =============================================================================
from __future__ import annotations

# json: dipakai untuk membaca baris log (setiap baris di logs/api.log berupa JSON).
import json
# sys: untuk mengatur keluaran terminal dan jalur pencarian modul.
import sys
# warnings: untuk menyembunyikan satu peringatan pustaka yang tidak relevan (di bawah).
import warnings
# Path: cara menulis jalur berkas yang sama di Windows, macOS, dan Linux.
from pathlib import Path

# Memaksa keluaran terminal berbahasa UTF-8 agar huruf dan simbol tampil benar di
# terminal Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Starlette memperingatkan bahwa TestClient sebaiknya memakai httpx2. Peringatan
# itu tidak memengaruhi hasil pemeriksaan dan hanya membuat keluaran ramai.
warnings.filterwarnings("ignore", message=".*httpx.*", category=DeprecationWarning)

# __file__ adalah jalur berkas ini; resolve() menjadikannya jalur lengkap; parent adalah
# folder tempat berkas ini berada, yaitu starter/.
STARTER = Path(__file__).resolve().parent


def _cari_proyek() -> Path | None:
    """Temukan akar proyek secure-academic-data-pipeline.

    Dicari berurutan: folder kerja saat ini beserta folder di atasnya (skrip
    dijalankan dari akar proyek), folder di atas skrip ini (skrip ditaruh di
    <proyek>/starter/), lalu susunan folder mata kuliah, yaitu
    03_Materi Pertemuan/<pertemuan>/starter/ bersebelahan dengan
    04_Proyek dan Praktikum/.
    """
    # Daftar tempat yang dicoba berurutan: folder kerja, semua folder di atasnya, lalu
    # semua folder di atas starter/. Tanda * "membuka" isi daftar ke dalam daftar ini.
    kandidat = [Path.cwd(), *Path.cwd().parents, *STARTER.parents]
    if len(STARTER.parents) > 2:
        kandidat.append(STARTER.parents[2] / "04_Proyek dan Praktikum" / "secure-academic-data-pipeline")
    # Folder pertama yang berisi api/ DAN pipeline/ dianggap akar proyek; bila tidak
    # ada yang cocok, hasilnya None.
    return next((k for k in kandidat if (k / "api").is_dir() and (k / "pipeline").is_dir()), None)


PROYEK = _cari_proyek()

if PROYEK is None:  # pragma: no cover
    print("GAGAL: folder proyek secure-academic-data-pipeline tidak ditemukan.")
    print("Jalankan skrip ini dari akar proyek, misalnya:")
    print("    cd secure-academic-data-pipeline")
    print(f"    python starter/{Path(__file__).name}")
    raise SystemExit(1)

# Menambahkan akar proyek ke jalur pencarian modul supaya "from api import ..."
# di bawah menemukan paket api/ milik Anda.
sys.path.insert(0, str(PROYEK))

# Kode mahasiswa yang dipakai pengujian. Ketiganya ada pada data sintetik.
MILIK_SENDIRI = "MHS-SYN-0002"        # Sains Data - identitas kunci mahasiswa
SEPRODI_LAIN = "MHS-SYN-0004"         # Sains Data - orang lain, prodi sama
PRODI_LAIN = "MHS-SYN-0001"           # Ekonomi Syariah - prodi berbeda

PRODI_LAIN_NAMA = "Ekonomi Syariah"   # program studi milik PRODI_LAIN

# Kata umpan yang disisipkan ke pesan galat buatan pada pemeriksaan TODO 3. Bila
# kata ini muncul di balasan API, berarti detail internal bocor ke pengguna.
PENANDA_BOCOR = "PENANDA-KEBOCORAN-UJI"


# Jenis galat milik pemeriksa sendiri. main() menangkapnya dan menampilkan
# "GAGAL: <pesan>"; galat Python biasa ditangani terpisah oleh laporkan_galat_praktikum.
class Gagal(Exception):
    """Perbaikan belum lengkap. Pesannya menyebutkan apa yang belum berlaku."""


# Dua alat bantu cetak: judul bagian, lalu satu baris hasil berlabel (label diratakan
# kiri selebar 46 karakter agar titik dua sejajar).
def bagian(judul: str) -> None:
    print(f"\n== {judul} ==")


def lapor(label: str, nilai: str) -> None:
    print(f"  {label:<46}: {nilai}")


# Alat bantu utama. "diharapkan" boleh satu angka (401) atau beberapa (400, 422);
# angka tunggal dijadikan tuple agar pengecekan "in" di bawah berlaku untuk keduanya.
def status_diharapkan(respons, diharapkan, keterangan: str) -> None:
    if isinstance(diharapkan, int):
        diharapkan = (diharapkan,)
    if respons.status_code not in diharapkan:
        # Hanya 300 karakter pertama badan balasan yang ditampilkan, cukup untuk
        # melihat pesan galat tanpa membanjiri layar.
        badan = respons.text[:300]
        raise Gagal(
            f"{keterangan}\n"
            f"  status diharapkan {' atau '.join(str(k) for k in diharapkan)}, "
            f"diperoleh {respons.status_code}\n"
            f"  badan respons: {badan}"
        )


# ---------------------------------------------------------------------
# 0. Lingkungan
# ---------------------------------------------------------------------


def siapkan():
    bagian("0. Lingkungan")

    # Pengecekan lingkungan berurutan; bila salah satu gagal, pesannya langsung
    # menunjuk perbaikannya. "# noqa: F401" meminta alat pemeriksa gaya tidak menegur
    # import yang tidak dipakai (di sini import hanya untuk menguji ketersediaan).
    #   a) FastAPI, httpx, dan mysql-connector-python terpasang pada Python YANG SAMA dengan yang
    #      menjalankan pemeriksa ini. sys.executable menyebut jalur Python itu; pesan galat
    #      memakainya agar Anda dapat memasang pustaka ke Python yang benar.
    try:
        from fastapi.testclient import TestClient  # noqa: F401
    except ImportError as galat:
        raise Gagal(
            "pustaka FastAPI atau httpx belum terpasang pada Python ini.\n"
            f"  Python yang menjalankan pemeriksa: {sys.executable}\n"
            f'  Pasang dengan Python yang sama: "{sys.executable}" -m pip install -r requirements.txt'
        ) from galat

    try:
        import mysql.connector  # noqa: F401
    except ImportError as galat:
        raise Gagal(
            "pustaka mysql-connector-python belum terpasang pada Python ini.\n"
            f"  Python yang menjalankan pemeriksa: {sys.executable}\n"
            f'  Pasang dengan Python yang sama: "{sys.executable}" -m pip install -r requirements.txt\n'
            "  Bila layanan dijalankan dengan `uvicorn`, pakai `python -m uvicorn api.main:app --reload`\n"
            "  supaya Python-nya sama."
        ) from galat

    #   b) paket api/ Anda dapat diimpor tanpa galat (salah ketik pada berkas yang
    #      Anda ubah akan tertangkap di sini);
    try:
        from api import basis_data, keamanan, konfigurasi  # noqa: F401
        from api.main import app  # noqa: F401
    except Exception as galat:
        raise Gagal(
            f"paket api tidak dapat diimpor ({type(galat).__name__}: {galat}).\n"
            "  Periksa apakah ada kesalahan penulisan pada berkas yang Anda ubah."
        ) from galat

    from api import konfigurasi as cfg
    from api import keamanan as kmn

    #   c) ketiga kunci API sudah ada di .env.
    terpasang = kmn.daftar_kunci_terpasang()
    kurang = [nama for nama in kmn.PENGGUNA if nama not in terpasang]
    if kurang:
        raise Gagal(
            f"kunci API belum diisi pada .env: {kurang}.\n"
            "  Buat nilai acak dengan:\n"
            '    python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    lapor("kunci API terpasang", f"{len(terpasang)} dari {len(kmn.PENGGUNA)}")

    from api import basis_data as bd

    # Pengujian terakhir lingkungan: membaca satu mahasiswa langsung dari MySQL.
    # Gagal di sini berarti MySQL mati atau data sintetik belum dimuat.
    try:
        contoh = bd.nilai_satu_mahasiswa(MILIK_SENDIRI)
    except Exception as galat:
        raise Gagal(
            f"basis data tidak dapat dibaca ({galat}).\n"
            "  Periksa: MySQL menyala, schema.sql dan seed_data.sql sudah dijalankan."
        ) from galat
    if not contoh:
        raise Gagal(
            f"data sintetik untuk {MILIK_SENDIRI} tidak ditemukan.\n"
            "  Muat ulang database/seed_data.sql."
        )
    lapor("basis data terbaca", f"{len(contoh)} catatan untuk {MILIK_SENDIRI}")
    lapor("ambang sel kecil", str(cfg.AMBANG_SEL_KECIL))
    lapor("batas baris maksimum", str(cfg.BATAS_BARIS_MAKS))

    return cfg, kmn, bd


# raise_server_exceptions=False: galat tak terduga di API dijawab sebagai status 500
# (seperti server sungguhan), bukan dilempar ke pemeriksa. TODO 3 justru menguji
# bentuk balasan 500 itu.
def buat_klien():
    from fastapi.testclient import TestClient
    from api.main import app

    return TestClient(app, raise_server_exceptions=False)


# Membuat header permintaan berisi kunci API dari .env, misalnya
# {"X-API-Key": "<isi API_KEY_MAHASISWA>"}. Dengan header yang berbeda, pemeriksa
# berperan sebagai mahasiswa, dosen wali, atau analis.
def kepala(cfg, nama_variabel: str) -> dict:
    from api import keamanan as kmn

    return {kmn.NAMA_HEADER_KUNCI: cfg.ambil(nama_variabel)}


# ---------------------------------------------------------------------
# 1. TODO 1 — otorisasi tingkat objek
# ---------------------------------------------------------------------


def periksa_otorisasi(klien, cfg, kmn) -> None:
    bagian("1. TODO 1 - otorisasi tingkat objek")

    mhs = kepala(cfg, "API_KEY_MAHASISWA")
    wali = kepala(cfg, "API_KEY_DOSEN_WALI")
    analis = kepala(cfg, "API_KEY_ANALIS")

    # Urutan pengujian: dua kasus tanpa identitas (401), lalu satu kasus yang HARUS
    # berhasil (mahasiswa membaca miliknya), lalu kasus yang HARUS ditolak (403).
    # Kasus yang harus berhasil penting: otorisasi yang menolak semua orang lolos
    # semua uji penolakan, padahal layanannya mati.
    r = klien.get(f"/nilai/{MILIK_SENDIRI}")
    status_diharapkan(r, 401, "permintaan tanpa kunci API harus ditolak")
    lapor("tanpa kunci", "401 seperti seharusnya")

    r = klien.get(f"/nilai/{MILIK_SENDIRI}", headers={kmn.NAMA_HEADER_KUNCI: "salah"})
    status_diharapkan(r, 401, "kunci API yang salah harus ditolak")
    lapor("kunci salah", "401 seperti seharusnya")

    r = klien.get(f"/nilai/{MILIK_SENDIRI}", headers=mhs)
    status_diharapkan(
        r, 200,
        "mahasiswa harus tetap dapat membaca catatannya SENDIRI.\n"
        "  Otorisasi yang menolak semua orang bukan otorisasi, melainkan layanan mati.",
    )
    lapor("mahasiswa membaca miliknya sendiri", f"200, {len(r.json())} catatan")

    r = klien.get(f"/nilai/{SEPRODI_LAIN}", headers=mhs)
    status_diharapkan(
        r, 403,
        f"mahasiswa masih dapat membaca catatan {SEPRODI_LAIN}, milik orang lain.\n"
        "  Inilah kelemahan API1:2023 yang harus ditutup pada TODO 1.\n"
        "  Program studi yang sama tidak membuat catatan itu menjadi miliknya.",
    )
    lapor("mahasiswa membaca teman seprodi", "403 seperti seharusnya")

    r = klien.get(f"/nilai/{PRODI_LAIN}", headers=mhs)
    status_diharapkan(
        r, 403,
        f"mahasiswa masih dapat membaca catatan {PRODI_LAIN} dari program studi lain",
    )
    lapor("mahasiswa membaca prodi lain", "403 seperti seharusnya")

    r = klien.get(f"/nilai/{SEPRODI_LAIN}", headers=wali)
    status_diharapkan(
        r, 200,
        "dosen wali harus dapat membaca mahasiswa pada program studinya sendiri",
    )
    lapor("dosen wali di prodinya", f"200, {len(r.json())} catatan")

    r = klien.get(f"/nilai/{PRODI_LAIN}", headers=wali)
    status_diharapkan(
        r, 403,
        "dosen wali masih dapat membaca mahasiswa di luar program studinya",
    )
    lapor("dosen wali di luar prodinya", "403 seperti seharusnya")

    r = klien.get(f"/nilai/{MILIK_SENDIRI}", headers=analis)
    status_diharapkan(
        r, 403,
        "analis masih dapat membaca data tingkat record.\n"
        "  Analis bekerja dengan laporan agregat, bukan dengan catatan perorangan.",
    )
    lapor("analis membaca data record", "403 seperti seharusnya")

    # Peran yang tidak dikenal harus ditolak dengan sendirinya. Pemeriksaan ini
    # memanggil fungsi otorisasi secara langsung, karena peran seperti ini tidak
    # dapat dibuat melalui kunci API.
    peran_asing = kmn.Identitas(
        nama="peran_baru_yang_belum_didaftarkan",
        peran="wakil_dekan",
        program_studi="Sains Data",
        kode_mahasiswa=MILIK_SENDIRI,
    )
    if kmn.boleh_membaca_mahasiswa(peran_asing, MILIK_SENDIRI, "Sains Data"):
        raise Gagal(
            "peran yang tidak dikenal masih diizinkan.\n"
            "  Tulis aturan sebagai daftar izin yang diakhiri penolakan.\n"
            "  Peran baru yang lupa didaftarkan harus ditolak dengan sendirinya."
        )
    lapor("peran tak dikenal", "ditolak seperti seharusnya")

    # 403 tidak boleh membedakan mahasiswa yang ada dan yang tidak ada. Bila
    # berbeda, endpoint ini menjadi alat untuk menguji keberadaan seseorang.
    # MHS-SYN-9999 tidak ada di data. Keduanya diminta oleh pemanggil yang sama,
    # sehingga jawabannya harus identik (403).
    r_ada = klien.get(f"/nilai/{PRODI_LAIN}", headers=mhs)
    r_tiada = klien.get("/nilai/MHS-SYN-9999", headers=mhs)
    if r_ada.status_code != r_tiada.status_code:
        raise Gagal(
            "jawaban untuk mahasiswa yang ada dan yang tidak ada berbeda "
            f"({r_ada.status_code} vs {r_tiada.status_code}).\n"
            "  Selisih itu cukup untuk menguji siapa yang terdaftar tanpa\n"
            "  pernah berhasil membaca satu pun nilainya."
        )
    lapor("kode yang tidak terdaftar", f"{r_tiada.status_code}, sama dengan yang terdaftar")

    # Pencarian /nilai juga mengembalikan catatan perorangan, sehingga aturan
    # TODO 1 berlaku di sana. Endpoint tanpa pengenal objek pada URL paling
    # mudah terlupa, karena tidak ada kode yang tampak perlu diperiksa.
    prodi_wali = kmn.PENGGUNA["API_KEY_DOSEN_WALI"].program_studi

    r = klien.get("/nilai", headers=mhs)
    status_diharapkan(
        r, 403,
        "mahasiswa masih dapat memakai pencarian /nilai dan membaca catatan\n"
        "  milik orang lain. Aturan TODO 1 berlaku juga pada pencarian: mahasiswa\n"
        "  membaca catatannya melalui /nilai/{kode_mahasiswa}, bukan melalui pencarian.",
    )
    lapor("mahasiswa memakai pencarian /nilai", "403 seperti seharusnya")

    r = klien.get("/nilai", headers=analis)
    status_diharapkan(
        r, 403,
        "analis masih dapat membaca catatan perorangan melalui pencarian /nilai.\n"
        "  Analis bekerja dengan laporan agregat /ringkasan, bukan catatan perorangan.",
    )
    lapor("analis memakai pencarian /nilai", "403 seperti seharusnya")

    r = klien.get("/nilai", headers=wali, params={"program_studi": PRODI_LAIN_NAMA})
    status_diharapkan(
        r, 403,
        f"dosen wali masih dapat mencari catatan {PRODI_LAIN_NAMA} melalui\n"
        "  /nilai?program_studi=... Penyaring program studi lain harus ditolak.",
    )
    lapor("dosen wali mencari prodi lain", "403 seperti seharusnya")

    r = klien.get("/nilai", headers=wali, params={"batas": cfg.BATAS_BARIS_MAKS})
    status_diharapkan(
        r, 200,
        "dosen wali harus tetap dapat mencari catatan program studinya sendiri",
    )
    prodi_hasil = sorted({b.get("program_studi") for b in r.json()})
    if prodi_hasil != [prodi_wali]:
        raise Gagal(
            f"pencarian dosen wali tanpa penyaring memuat {prodi_hasil}.\n"
            f"  Tanpa penyaring, hasilnya harus dibatasi pada {prodi_wali}, program\n"
            "  studi dosen wali itu sendiri."
        )
    lapor("dosen wali mencari tanpa penyaring", f"200, hanya {prodi_wali}")


# ---------------------------------------------------------------------
# 2. TODO 2 — validasi masukan
# ---------------------------------------------------------------------


def periksa_validasi(klien, cfg) -> None:
    bagian("2. TODO 2 - validasi masukan")

    wali = kepala(cfg, "API_KEY_DOSEN_WALI")
    # FastAPI menjawab 422 untuk masukan yang tidak sesuai aturan Query(...), dan kode
    # buatan sendiri biasanya 400. Keduanya diterima; yang tidak boleh adalah 200 atau 500.
    ditolak = (400, 422)

    # Pola setiap bagian: coba nilai yang SALAH (harus ditolak), lalu nilai yang BENAR
    # di batas (harus diterima). Menolak terlalu sedikit dan menolak terlalu banyak
    # sama-sama dianggap gagal.

    r = klien.get("/nilai", headers=wali, params={"batas": 100000})
    status_diharapkan(
        r, ditolak,
        "batas=100000 masih diterima.\n"
        f"  Batas atas yang berlaku adalah konfigurasi.BATAS_BARIS_MAKS "
        f"= {cfg.BATAS_BARIS_MAKS}.\n"
        "  Tanpa batas, satu permintaan dapat menarik seluruh isi view.",
    )
    lapor("batas=100000", f"{r.status_code} seperti seharusnya")

    for nilai_batas in (0, -5):
        r = klien.get("/nilai", headers=wali, params={"batas": nilai_batas})
        status_diharapkan(r, ditolak, f"batas={nilai_batas} masih diterima")
    lapor("batas=0 dan batas=-5", "ditolak seperti seharusnya")

    r = klien.get("/nilai", headers=wali, params={"batas": cfg.BATAS_BARIS_MAKS})
    status_diharapkan(
        r, 200,
        f"batas={cfg.BATAS_BARIS_MAKS} seharusnya masih diterima; "
        "batas atas bersifat inklusif",
    )
    if len(r.json()) > cfg.BATAS_BARIS_MAKS:
        raise Gagal(
            f"permintaan dengan batas={cfg.BATAS_BARIS_MAKS} mengembalikan "
            f"{len(r.json())} baris"
        )
    lapor(f"batas={cfg.BATAS_BARIS_MAKS}", f"200, {len(r.json())} baris")

    for nilai_semester in (0, 15, 999, -1):
        r = klien.get("/nilai", headers=wali, params={"semester": nilai_semester})
        status_diharapkan(
            r, ditolak,
            f"semester={nilai_semester} masih diterima.\n"
            "  Rentang yang sah adalah 1 sampai 14, sama dengan batasan\n"
            "  ck_mahasiswa_semester pada skema basis data.",
        )
    lapor("semester di luar 1-14", "ditolak seperti seharusnya")

    r = klien.get("/nilai", headers=wali, params={"semester": 5})
    status_diharapkan(r, 200, "semester=5 seharusnya diterima")
    lapor("semester=5", f"200, {len(r.json())} baris")

    for kolom in ("nama_mk", "status_kelulusan", "1", "kode_mahasiswa; DROP TABLE"):
        r = klien.get("/nilai", headers=wali, params={"urut": kolom})
        status_diharapkan(
            r, ditolak,
            f"urut={kolom!r} tidak ditolak dengan benar.\n"
            "  Nama kolom tidak dapat diparameterkan, sehingga satu-satunya cara\n"
            "  aman adalah daftar izin. Masukan yang salah dijawab 400, bukan 500:\n"
            "  masukan yang salah bukan kesalahan program.",
        )
    lapor("urut di luar daftar izin", "ditolak seperti seharusnya")

    for arah in ("NAIK", "ASC; DROP TABLE mahasiswa", ""):
        r = klien.get("/nilai", headers=wali, params={"arah": arah})
        status_diharapkan(r, ditolak, f"arah={arah!r} tidak ditolak dengan benar")
    lapor("arah di luar daftar izin", "ditolak seperti seharusnya")

    from api import basis_data as bd

    # Setiap kolom dan arah yang ADA di daftar izin Anda diuji ulang: semuanya harus 200.
    # Ini menangkap daftar izin yang terlalu ketat atau salah ketik.
    for kolom in bd.KOLOM_URUT_DIIZINKAN:
        for arah in bd.ARAH_URUT_DIIZINKAN:
            r = klien.get("/nilai", headers=wali, params={"urut": kolom, "arah": arah})
            status_diharapkan(
                r, 200,
                f"urut={kolom} arah={arah} seharusnya diterima; "
                "keduanya ada pada daftar izin",
            )
    lapor(
        "seluruh kombinasi daftar izin",
        f"{len(bd.KOLOM_URUT_DIIZINKAN) * len(bd.ARAH_URUT_DIIZINKAN)} kombinasi, semuanya 200",
    )


# ---------------------------------------------------------------------
# 3. TODO 3 — penanganan galat
# ---------------------------------------------------------------------


def periksa_galat(klien, cfg, jejak) -> None:
    bagian("3. TODO 3 - penanganan galat")

    from api import basis_data as bd

    wali = kepala(cfg, "API_KEY_DOSEN_WALI")
    # Teknik pengujian: fungsi pembaca basis data DIGANTI sementara dengan fungsi
    # "meledak" yang selalu melempar galat berisi umpan PENANDA_BOCOR dan teks SQL.
    # Setelah /ringkasan dipanggil, fungsi aslinya dikembalikan (blok finally).
    # Yang diperiksa: umpan itu tidak boleh sampai ke pengguna.
    asli = bd.ringkasan_kelulusan

    def meledak(*args, **kwargs):
        raise RuntimeError(
            f"{PENANDA_BOCOR}: SELECT * FROM nilai_akademik "
            "-- pesan internal yang tidak boleh sampai ke pengguna"
        )

    # jejak() tanpa argumen = ukuran berkas log saat ini. Setelah permintaan, jejak(panjang_awal)
    # membaca hanya baris log BARU, sehingga baris lama tidak ikut terhitung.
    panjang_awal = jejak()
    bd.ringkasan_kelulusan = meledak
    try:
        r = klien.get("/ringkasan", headers=wali)
    finally:
        bd.ringkasan_kelulusan = asli

    status_diharapkan(r, 500, "galat tak terduga seharusnya dijawab dengan status 500")

    # Tiga tanda kebocoran: umpan, nama kelas galat, dan potongan SQL.
    badan = r.text
    if PENANDA_BOCOR in badan or "RuntimeError" in badan or "SELECT" in badan:
        raise Gagal(
            "detail internal masih ikut terkirim pada respons galat.\n"
            f"  Badan respons: {badan[:300]}\n"
            "  Pesan untuk pengguna harus umum dan sama untuk semua galat\n"
            "  tak terduga. Detailnya masuk ke log, bukan ke respons."
        )
    lapor("respons 500", "tidak memuat detail internal")

    try:
        isi = r.json()
    except ValueError as galat:
        raise Gagal("respons galat bukan JSON yang sah") from galat

    # set(isi) = himpunan nama field pada JSON balasan; harus persis dua field ini.
    if set(isi) != {"pesan", "korelasi_id"}:
        raise Gagal(
            f"badan respons galat memuat field {sorted(isi)}.\n"
            "  Bentuk yang diharapkan hanya `pesan` dan `korelasi_id`, "
            "mengikuti skema.Galat."
        )
    if not isi.get("korelasi_id"):
        raise Gagal(
            "korelasi_id kosong pada respons galat.\n"
            "  Tanpa nilai itu, pengguna tidak punya cara melaporkan kegagalan\n"
            "  dan pengelola tidak punya cara menemukannya di log."
        )
    lapor("bentuk respons galat", "pesan + korelasi_id")

    baris_baru = jejak(panjang_awal)
    gagal_tercatat = [b for b in baris_baru if b.get("hasil") == "gagal"]
    if not gagal_tercatat:
        raise Gagal(
            "galat tak terduga tidak tercatat pada logs/api.log.\n"
            "  Menyembunyikan detail dari pengguna tanpa menyimpannya di suatu\n"
            "  tempat bukan keamanan, melainkan kehilangan informasi.\n"
            "  Tambahkan pencatatan dengan hasil 'gagal' pada handler TODO 3."
        )
    lapor("galat tercatat di log", f"{len(gagal_tercatat)} baris hasil='gagal'")

    # korelasi_id adalah "nomor tiket" galat. Nomor yang diterima pengguna harus sama
    # dengan nomor pada baris log, supaya pengelola dapat menemukan penyebabnya.
    korelasi_respons = isi["korelasi_id"]
    cocok = [b for b in gagal_tercatat if b.get("korelasi_id") == korelasi_respons]
    if not cocok:
        raise Gagal(
            f"korelasi_id pada respons ({korelasi_respons}) tidak ditemukan di log.\n"
            "  Nilai yang dilaporkan pengguna harus menuntun ke catatan yang tepat."
        )
    lapor("korelasi_id respons ditemukan di log", korelasi_respons)

    # Baris log diubah kembali menjadi teks lalu dicari: nilai kunci API mana pun
    # tidak boleh tampak di sana.
    for baris in gagal_tercatat:
        teks = json.dumps(baris, ensure_ascii=False)
        for nama_variabel in ("API_KEY_MAHASISWA", "API_KEY_DOSEN_WALI", "API_KEY_ANALIS"):
            nilai = cfg.ambil(nama_variabel, "")
            if nilai and nilai in teks:
                raise Gagal(
                    f"nilai {nama_variabel} ikut tertulis ke log.\n"
                    "  Kunci tidak pernah boleh masuk ke catatan mana pun."
                )
    lapor("kunci API pada baris log", "tidak ditemukan")


# ---------------------------------------------------------------------
# 4. TODO 4 — pencatatan penolakan
# ---------------------------------------------------------------------


def periksa_pencatatan(klien, cfg, jejak) -> None:
    bagian("4. TODO 4 - pencatatan penolakan")

    mhs = kepala(cfg, "API_KEY_MAHASISWA")

    panjang_awal = jejak()
    r = klien.get(f"/nilai/{PRODI_LAIN}", headers=mhs)
    status_diharapkan(r, 403, "prasyarat: permintaan ini seharusnya sudah ditolak")
    baris_baru = jejak(panjang_awal)

    # Menyaring baris log baru: hanya yang hasilnya "ditolak" dan aksinya "baca_nilai".
    ditolak = [
        b for b in baris_baru
        if b.get("hasil") == "ditolak" and b.get("aksi") == "baca_nilai"
    ]
    if not ditolak:
        raise Gagal(
            "penolakan 403 tidak tercatat pada logs/api.log.\n"
            "  Permintaan yang berhasil menceritakan pemakaian biasa; permintaan\n"
            "  yang ditolak menceritakan percobaan. Seseorang yang mencoba tiga\n"
            "  puluh kode berbeda dalam satu menit hanya terlihat bila penolakan\n"
            "  ikut tercatat.\n"
            "  Lengkapi TODO 4 pada api/main.py."
        )
    lapor("penolakan tercatat", f"{len(ditolak)} baris hasil='ditolak'")

    # ditolak[-1] = baris terakhir (paling baru). Isinya diperiksa: objek yang dicoba
    # dibaca, siapa pelakunya, dan nomor korelasinya.
    catatan = ditolak[-1]
    if catatan.get("objek") != PRODI_LAIN:
        raise Gagal(
            f"kolom objek berisi {catatan.get('objek')!r}, "
            f"seharusnya {PRODI_LAIN!r}.\n"
            "  Tanpa objek yang tepat, log tidak dapat menjawab pertanyaan\n"
            "  'catatan siapa yang dicoba dibaca'."
        )
    if not catatan.get("aktor") or catatan["aktor"] == "anonim":
        raise Gagal(
            f"kolom aktor berisi {catatan.get('aktor')!r}.\n"
            "  Pemanggil sudah dikenali pada tahap ini, sehingga namanya harus\n"
            "  tercatat. 'anonim' hanya untuk permintaan yang gagal autentikasi."
        )
    if not catatan.get("korelasi_id"):
        raise Gagal("korelasi_id kosong pada baris penolakan")
    lapor("aktor, objek, korelasi_id", "lengkap")

    teks = json.dumps(catatan, ensure_ascii=False)
    for nama_variabel in ("API_KEY_MAHASISWA", "API_KEY_DOSEN_WALI", "API_KEY_ANALIS"):
        nilai = cfg.ambil(nama_variabel, "")
        if nilai and nilai in teks:
            raise Gagal(f"nilai {nama_variabel} ikut tertulis ke baris penolakan")

    # Nilai mahasiswa tidak boleh ikut tercatat. Yang perlu diketahui auditor
    # adalah bahwa catatan itu dicoba dibaca, bukan berapa nilainya.
    from api import basis_data as bd

    milik_korban = bd.nilai_satu_mahasiswa(PRODI_LAIN)
    keterangan = str(catatan.get("keterangan") or "")
    for catatan_nilai in milik_korban:
        jejak_nilai = f"'nilai_angka': {catatan_nilai['nilai_angka']}"
        if jejak_nilai in keterangan or catatan_nilai["record_id"] in keterangan:
            raise Gagal(
                "isi baris data ikut tertulis pada keterangan log.\n"
                "  Catat pengenal dan hasil, bukan muatan datanya. Log yang\n"
                "  memuat data pribadi menjadi salinan kedua yang perlu\n"
                "  dilindungi sekeras aslinya."
            )
    lapor("isi data pada keterangan", "tidak ditemukan")

    panjang_awal = jejak()
    r = klien.get("/nilai", headers=mhs)
    status_diharapkan(r, 403, "prasyarat: pencarian /nilai oleh mahasiswa seharusnya sudah ditolak")
    ditolak_cari = [
        b for b in jejak(panjang_awal)
        if b.get("hasil") == "ditolak" and b.get("aksi") == "cari_nilai"
    ]
    if not ditolak_cari:
        raise Gagal(
            "penolakan pada pencarian /nilai tidak tercatat pada logs/api.log.\n"
            "  Catat penolakan itu seperti TODO 4, dengan aksi 'cari_nilai' dan\n"
            "  hasil 'ditolak'."
        )
    lapor("penolakan pencarian tercatat", f"{len(ditolak_cari)} baris hasil='ditolak'")


# ---------------------------------------------------------------------
# 5. TODO 5 — sel kecil pada laporan agregat
# ---------------------------------------------------------------------


def periksa_sel_kecil(klien, cfg) -> None:
    bagian("5. TODO 5 - sel kecil pada laporan agregat")

    from api import basis_data as bd

    analis = kepala(cfg, "API_KEY_ANALIS")
    ambang = cfg.AMBANG_SEL_KECIL

    r = klien.get("/ringkasan", headers=analis)
    status_diharapkan(r, 200, "analis seharusnya dapat membaca laporan agregat")
    hasil = r.json()

    # Pemeriksa menghitung jawaban yang benar SENDIRI dari data mentah (tanpa melalui
    # API), lalu membandingkan: sel mana yang jumlah_record-nya di bawah ambang harus
    # disensor. Kunci setiap sel berupa tuple (program_studi, semester, kode_mk).
    sumber = bd.ringkasan_kelulusan(None, None)
    diharapkan_disensor = {
        (b["program_studi"], b["semester"], b["kode_mk"])
        for b in sumber
        if b["jumlah_record"] < ambang
    }

    if len(hasil) != len(sumber):
        raise Gagal(
            f"laporan mengembalikan {len(hasil)} sel, seharusnya {len(sumber)}.\n"
            "  Sel kecil ditahan angkanya, bukan dihilangkan dari daftar.\n"
            "  Menghilangkannya diam-diam membuat laporan tampak lengkap\n"
            "  padahal ada yang ditahan."
        )
    lapor("jumlah sel", f"{len(hasil)}, sama dengan sumber")

    # Dua daftar kesalahan: "kurang" = sel kecil yang masih menampakkan angka,
    # "berlebih" = sel biasa yang ikut disensor tanpa perlu.
    kurang = []
    berlebih = []
    for sel in hasil:
        kunci = (sel["program_studi"], sel["semester"], sel["kode_mk"])
        harus_disensor = kunci in diharapkan_disensor
        # any(...) bernilai benar bila SALAH SATU dari tiga angka masih terisi.
        angka_ada = any(
            sel.get(nama_field) is not None
            for nama_field in ("jumlah_lulus", "rata_nilai", "rata_kehadiran")
        )
        if harus_disensor and (angka_ada or not sel.get("disensor")):
            kurang.append((kunci, sel["jumlah_record"]))
        if not harus_disensor and (not angka_ada or sel.get("disensor")):
            berlebih.append((kunci, sel["jumlah_record"]))

    if kurang:
        contoh = kurang[0]
        raise Gagal(
            f"{len(kurang)} sel di bawah ambang {ambang} masih menampilkan angkanya.\n"
            f"  Contoh: {contoh[0]} dengan jumlah_record {contoh[1]}.\n"
            "  Untuk sel sekecil itu, jumlah_lulus tidak lagi berbicara tentang\n"
            "  kelompok; ia berbicara tentang satu orang yang dapat ditunjuk.\n"
            "  Setel jumlah_lulus, rata_nilai, dan rata_kehadiran menjadi None,\n"
            "  lalu disensor menjadi True."
        )
    if berlebih:
        contoh = berlebih[0]
        raise Gagal(
            f"{len(berlebih)} sel yang seharusnya utuh ikut disensor.\n"
            f"  Contoh: {contoh[0]} dengan jumlah_record {contoh[1]}, "
            f"tidak kurang dari ambang {ambang}.\n"
            "  Menyensor terlalu banyak juga merusak laporan. Ambangnya\n"
            "  adalah 'kurang dari', bukan 'kurang dari atau sama dengan'."
        )

    lapor(
        f"sel di bawah ambang {ambang}",
        f"{len(diharapkan_disensor)} sel, seluruhnya disensor",
    )
    lapor(
        "sel yang utuh",
        f"{len(sumber) - len(diharapkan_disensor)} sel, tidak ada yang tersensor keliru",
    )

    # min(..., key=...) mencari sel dengan jumlah_record terkecil; lambda adalah
    # fungsi mini yang menyebut "bandingkan berdasarkan kolom ini".
    terkecil = min(sumber, key=lambda b: b["jumlah_record"])
    lapor(
        "sel terkecil pada data",
        f"{terkecil['program_studi']} sem {terkecil['semester']} "
        f"{terkecil['kode_mk']}, {terkecil['jumlah_record']} record",
    )


# ---------------------------------------------------------------------
# 6. Kebersihan sumber
# ---------------------------------------------------------------------


def periksa_sumber(cfg, kmn) -> None:
    bagian("6. Kebersihan sumber")

    # Kamus {nama variabel: nilainya di .env}: tiga kunci API ditambah kata sandi basis
    # data. Satu-satunya pemeriksaan yang membaca ISI kode Anda: apakah salah satu nilai
    # itu tertulis mentah di berkas api/*.py.
    nilai_rahasia = {
        nama: cfg.ambil(nama, "") for nama in kmn.PENGGUNA
    }
    nilai_rahasia["DB_PASSWORD"] = cfg.ambil("DB_PASSWORD", "")

    berkas = sorted((PROYEK / "api").glob("*.py"))
    if not berkas:
        raise Gagal("tidak ada berkas Python pada folder api/")

    for path in berkas:
        isi = path.read_text(encoding="utf-8")
        for nama, nilai in nilai_rahasia.items():
            if nilai and nilai in isi:
                raise Gagal(
                    f"nilai {nama} tertulis di dalam {path.name}.\n"
                    "  Nilai rahasia dibaca dari lingkungan, tidak pernah dari kode.\n"
                    "  Ganti nilainya di .env setelah membersihkan berkas ini:\n"
                    "  rahasia yang pernah tertulis dianggap sudah bocor."
                )
    lapor("berkas api/ diperiksa", f"{len(berkas)} berkas, tanpa nilai rahasia")

    # Hanya catatan, bukan kegagalan: komentar "TODO 1:" yang lupa dihapus.
    sisa_todo = []
    for path in berkas + [PROYEK / "api" / "main.py"]:
        isi = path.read_text(encoding="utf-8")
        for nomor in range(1, 6):
            if f"TODO {nomor}:" in isi:
                sisa_todo.append(f"{path.name}: TODO {nomor}")
    if sisa_todo:
        print(f"  catatan: penanda tugas masih tertinggal -> {sorted(set(sisa_todo))}")
        print("           perilaku sudah benar; rapikan penanda sebelum mengumpulkan.")


# ---------------------------------------------------------------------


def laporkan_galat_praktikum(galat: Exception, worksheet: str = "") -> None:
    """Ubah galat Python mentah menjadi pesan yang menunjuk baris kode Anda."""
    # sysconfig dan traceback hanya dibutuhkan di sini, sehingga diimpor di dalam fungsi.
    import sysconfig
    import traceback

    print(f"\nGALAT saat pemeriksa menjalankan kode Anda: {type(galat).__name__}: {galat}")

    # Traceback Python mencantumkan semua lapisan pemanggilan, termasuk pustaka dan berkas
    # pemeriksa ini. Daftar di bawah menyaring semuanya, menyisakan hanya kode MILIK
    # ANDA; bingkai terakhir adalah baris tempat galat benar-benar terjadi.
    pustaka = (sysconfig.get_paths()["stdlib"], "site-packages")
    bingkai = [b for b in traceback.extract_tb(galat.__traceback__)
               if Path(b.filename).resolve() != Path(__file__).resolve()
               and not any(p in b.filename for p in pustaka)]
    if bingkai:
        terakhir = bingkai[-1]
        print(f"\n  Terjadi pada {Path(terakhir.filename).name}, baris {terakhir.lineno}, di fungsi {terakhir.name}:")
        if terakhir.line:
            print(f"      {terakhir.line}")

    # Petunjuk dipilih dari jenis galat dan kata kunci di pesannya.
    pesan = str(galat).lower()
    petunjuk = "Baca pesan galat di atas, lalu periksa baris yang disebut."
    if isinstance(galat, TypeError) and any(k in pesan for k in ("bytes", "encoded", "str", "buffer")):
        petunjuk = (
            "Teks (str) dan byte (bytes) kemungkinan tertukar.\n"
            "  Teks menjadi byte dengan .encode(\"utf-8\"); byte menjadi teks dengan .decode(\"utf-8\")."
        )
    elif isinstance(galat, AttributeError) and "nonetype" in pesan:
        petunjuk = (
            "Ada nilai yang berisi None. Fungsi Anda mungkin belum mengembalikan nilai\n"
            "  (lupa return), atau mengembalikan None pada salah satu cabangnya."
        )
    elif isinstance(galat, (KeyError, IndexError)):
        petunjuk = "Ada kunci atau nomor urut yang tidak tersedia. Periksa nama kolom atau indeks yang Anda pakai."
    elif isinstance(galat, NameError):
        petunjuk = "Nama salah ketik atau impor belum ada. Periksa ejaan dan baris import di bagian atas berkas."
    print(f"\n  Petunjuk: {petunjuk}")
    tambahan = f" Catat pesan ini pada worksheet {worksheet}." if worksheet else ""
    print(f"\n  Perbaiki lalu jalankan ulang.{tambahan}")


def main() -> None:
    print("PEMERIKSAAN HASIL PERTEMUAN 9")
    print("Keamanan Starter API - Mata Kuliah Keamanan Data (SSD1033)")

    # Urutan except di bawah: Gagal = perilaku API salah (milik pemeriksa); Exception =
    # galat Python lain di kode Anda (lihat laporkan_galat_praktikum).
    try:
        cfg, kmn, bd = siapkan()
        klien = buat_klien()

        berkas_log = cfg.LOG_DIR / "api.log"

        # Fungsi bersarang yang membaca logs/api.log. Tanpa argumen mengembalikan ukuran
        # berkas; dengan argumen "sejak" (ukuran sebelumnya) mengembalikan baris log yang
        # muncul sesudahnya. seek() melompat ke posisi itu; baris yang bukan JSON dilewati.
        def jejak(sejak: int | None = None):
            """Panjang berkas log, atau baris JSON yang muncul setelah `sejak`."""
            if not berkas_log.exists():
                return 0 if sejak is None else []
            if sejak is None:
                return berkas_log.stat().st_size
            with berkas_log.open("r", encoding="utf-8") as berkas:
                berkas.seek(sejak)
                baris = []
                for teks in berkas:
                    teks = teks.strip()
                    if not teks:
                        continue
                    try:
                        baris.append(json.loads(teks))
                    except ValueError:
                        continue
                return baris

        # Enam pemeriksaan berurutan, berhenti pada kegagalan pertama.
        periksa_otorisasi(klien, cfg, kmn)
        periksa_validasi(klien, cfg)
        periksa_galat(klien, cfg, jejak)
        periksa_pencatatan(klien, cfg, jejak)
        periksa_sel_kecil(klien, cfg)
        periksa_sumber(cfg, kmn)
    except Gagal as galat:
        print(f"\nGAGAL: {galat}")
        raise SystemExit(1)
    except Exception as galat:
        laporkan_galat_praktikum(galat)
        raise SystemExit(1)

    print("\nSTARTER API PERTEMUAN 9 LOLOS PEMERIKSAAN")


# Baris ini menjalankan main() hanya bila berkas dijalankan langsung
# (python starter/periksa_hasil_p09.py), bukan bila diimpor oleh berkas lain.
if __name__ == "__main__":
    main()
