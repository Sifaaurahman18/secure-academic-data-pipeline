"""Pemeriksaan hasil praktikum Pertemuan 7.

Menguji `jawaban_p07.py` yang Anda lengkapi. Yang diperiksa bukan bentuk
kodenya saja, melainkan perilakunya terhadap masukan yang tidak wajar:

    1. tidak ada query yang disusun dengan menempelkan teks;
    2. muatan injection tidak lagi membuka baris yang bukan miliknya;
    3. pengurutan hanya menerima kolom yang ada di daftar;
    4. log tidak ikut memuat rahasia, dan tidak melebihi batas kolom;
    5. pencatatan aktivitas berjalan memakai parameter;
    6. ringkasan tabel memuat jumlah baris dan checksum;
    7. pembandingan mendeteksi tabel hilang, selisih baris, dan selisih isi.

Taruh berkas ini di folder starter/ pada proyek secure-academic-data-pipeline
Anda, bersama berkas Pertemuan 7 lainnya, lalu jalankan dari akar proyek:

    python starter/periksa_hasil_p07.py

Bagian 1 sampai 5 memakai akun app_service. Bagian 6 dan 7 memerlukan akun
admin_lab karena harus membaca tabel dasar. Kata sandi dibaca dari variabel
lingkungan atau .env proyek; bila tidak ada, skrip akan menanyakannya. Kata
sandi admin_lab sengaja tidak disimpan di .env, sehingga selalu ditanyakan.
Jalankan dari terminal sungguhan agar permintaan kata sandi dapat dibaca.

Lewati bagian pemulihan dengan:

    python starter/periksa_hasil_p07.py --tanpa-pemulihan
"""

# =============================================================================
# CARA MEMBACA SKRIP INI
# =============================================================================
# Skrip ini memeriksa perilaku fungsi pada jawaban_p07.py, bukan gaya kodenya.
# Pemeriksaan memakai masukan uji seperti muatan injection, nama kolom tidak
# sah, dan rahasia dalam teks log.
#
# Perbedaan dengan P5 dan P6: pemeriksa ini terhubung ke MySQL sungguhan.
# Bagian 1 sampai 5 memakai akun app_service (hak terbatas), bagian 6 dan 7 memakai
# akun admin_lab karena harus membaca tabel dasar. Karena itu MySQL harus menyala
# dan siapkan_p07.sql sudah dijalankan.
#
# Urutan jalannya: main() memuat jawaban_p07.py, membuka koneksi, lalu menjalankan
# tujuh pemeriksaan berurutan (periksa_*). Pemeriksaan berhenti pada kegagalan
# PERTAMA; perbaiki, lalu jalankan ulang untuk melihat pesan berikutnya.
#
# Isi berkas ini: daftar muatan uji di bagian atas, tujuh fungsi periksa_*,
# pelapor galat, dan main() di bagian paling bawah.
# =============================================================================
from __future__ import annotations

# re: pustaka ekspresi reguler (pencocok pola teks), dipakai untuk mencari query
# yang dirakit dari teks.
import re
# sys: untuk mengatur keluaran terminal, jalur pencarian modul, dan opsi baris perintah.
import sys
# Path: cara menulis jalur berkas yang sama di Windows, macOS, dan Linux.
from pathlib import Path

# __file__ adalah jalur berkas ini; resolve() menjadikannya jalur lengkap; parent adalah
# folder tempat berkas ini berada, yaitu starter/.
STARTER = Path(__file__).resolve().parent
# Menambahkan starter/ ke jalur pencarian modul supaya "import koneksi" dan
# "import jawaban_p07" di bawah menemukan berkas di folder ini.
sys.path.insert(0, str(STARTER))

# noqa: E402 meminta alat pemeriksa gaya tidak mengeluh bahwa import ini muncul
# setelah baris kode lain (sys.path harus diatur dulu agar import ini berhasil).
from koneksi import TidakDapatTerhubung, buka  # noqa: E402

# Memaksa keluaran terminal berbahasa UTF-8 agar huruf dan simbol tampil benar di
# terminal Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BERKAS_JAWABAN = STARTER / "jawaban_p07.py"

# Query yang dirakit dari potongan teks.
#
# Yang dicari khusus klausa tempat NILAI pengguna masuk: WHERE, VALUES, dan
# SET. Klausa lain sengaja tidak diperiksa, karena nama tabel dan nama kolom
# memang tidak dapat dikirim sebagai parameter dan harus disisipkan setelah
# lolos daftar yang diizinkan — itulah yang dikerjakan TODO 2 dan TODO 4.
# Kebenaran penyisipan itu diuji melalui perilakunya pada bagian 3.
#
# Tiga pola di bawah mewakili tiga cara merakit query dari teks:
#   1. f-string:      f"... WHERE kode = '{x}'"
#   2. operator % atau +:  "... WHERE kode = '%s'" % x
#   3. .format():     "... WHERE kode = '{}'".format(x)
# \b berarti batas kata, re.I berarti tidak membedakan huruf besar dan kecil.
# Catatan: %s sebagai penanda parameter yang BENAR (dikirim lewat argumen kedua
# execute()) tidak cocok dengan pola 2, karena di sana tidak ada operator % atau +
# setelah kutip penutup.
POLA_RAKITAN = (
    re.compile(r"""f["'][^"']*\b(?:WHERE|VALUES|SET)\b""", re.I),
    re.compile(r"""["'][^"']*\b(?:WHERE|VALUES|SET)\b[^"']*["']\s*(?:%|\+)\s*""", re.I),
    re.compile(r"""["'][^"']*\b(?:WHERE|VALUES|SET)\b[^"']*["']\s*\.format\(""", re.I),
)

# Empat muatan serangan klasik. Query yang benar memperlakukan semuanya sebagai
# teks biasa yang dicari, sehingga tidak ada baris yang cocok.
MUATAN_INJECTION = (
    "' OR '1'='1",
    "' OR 1=1 -- ",
    "' UNION SELECT program_studi, 'X', semester, kode_mk, 1 "
    "FROM v_ringkasan_kelulusan -- ",
    "MHS-SYN-0007'; DROP TABLE nilai_akademik; -- ",
)

# Nama kolom yang TIDAK boleh diterima urutkan_aman(): berisi perintah tambahan,
# kolom yang ada di tabel tetapi tidak ada di daftar yang diizinkan, angka, dan
# komentar SQL.
KOLOM_DITOLAK = (
    "nilai_angka; DROP TABLE mahasiswa",
    "status_pendampingan",
    "1",
    "kode_mahasiswa--",
)


# Jenis galat milik pemeriksa sendiri. main() menangkapnya dan menampilkan
# "GAGAL: <pesan>"; galat Python biasa ditangani terpisah oleh laporkan_galat_praktikum.
class Gagal(Exception):
    """Kegagalan pemeriksaan yang perlu diperbaiki mahasiswa."""


# Dua alat bantu cetak: judul bagian, lalu satu baris hasil berlabel (label diratakan
# kiri selebar 46 karakter agar titik dua sejajar).
def bagian(judul: str) -> None:
    print(f"\n== {judul} ==")


def hasil(label: str, nilai: str) -> None:
    print(f"  {label:<46}: {nilai}")


# ---------------------------------------------------------------------
# 1. Bentuk kode
# ---------------------------------------------------------------------


def periksa_rakitan_query() -> None:
    bagian("1. Query yang dirakit dari teks")
    if not BERKAS_JAWABAN.exists():
        raise Gagal(f"berkas {BERKAS_JAWABAN.name} tidak ditemukan.")

    bermasalah = []
    # Membaca jawaban_p07.py baris demi baris; enumerate memberi nomor baris
    # (start=1 agar dimulai dari 1, sama seperti di editor).
    for nomor, teks in enumerate(
        BERKAS_JAWABAN.read_text(encoding="utf-8").splitlines(), start=1
    ):
        # Membuang komentar (semua setelah tanda #) agar komentar yang kebetulan
        # memuat kata WHERE tidak dianggap sebagai kode.
        bersih = teks.split("#", 1)[0]
        if any(pola.search(bersih) for pola in POLA_RAKITAN):
            bermasalah.append((nomor, teks.strip()[:70]))

    if bermasalah:
        rincian = "; ".join(f"baris {n}: {t}" for n, t in bermasalah)
        raise Gagal(
            f"ditemukan query yang disusun dengan menempelkan teks ({rincian}).\n"
            "  Nilai dari pengguna dikirim sebagai parameter melalui %s dan\n"
            "  tuple pada argumen kedua execute(), bukan disisipkan ke dalam\n"
            "  teks query."
        )
    hasil("query dirakit dari teks", "tidak ditemukan")


# ---------------------------------------------------------------------
# 2. Pencarian
# ---------------------------------------------------------------------


def periksa_pencarian(jawaban, kursor) -> None:
    bagian("2. Pencarian dengan parameter")

    # Pencarian wajar dulu: pastikan fungsi bekerja sebelum diserang.
    normal = jawaban.cari_mahasiswa(kursor, "MHS-SYN-0007")
    if not isinstance(normal, list):
        raise Gagal("cari_mahasiswa harus mengembalikan senarai.")
    if not normal:
        raise Gagal(
            "pencarian MHS-SYN-0007 tidak mengembalikan baris apa pun.\n"
            "  Periksa nama view dan urutan kolomnya."
        )
    if len(normal[0]) != 5:
        raise Gagal(
            f"setiap baris harus berisi 5 kolom, diperoleh {len(normal[0])}.\n"
            "  Urutannya: kode_mahasiswa, program_studi, semester, kode_mk, "
            "nilai_angka."
        )
    if any(baris[0] != "MHS-SYN-0007" for baris in normal):
        raise Gagal("hasil pencarian memuat mahasiswa lain.")
    hasil("pencarian biasa", f"{len(normal)} baris, seluruhnya MHS-SYN-0007")

    # Lalu serang dengan tiap muatan. Hasil yang benar adalah 0 baris tanpa galat:
    # dengan parameter, muatan hanya dianggap sebagai teks kode mahasiswa yang tidak ada.
    for muatan in MUATAN_INJECTION:
        try:
            keluar = jawaban.cari_mahasiswa(kursor, muatan)
        except Exception as galat:
            raise Gagal(
                f"muatan {muatan!r} membuat fungsi melempar galat "
                f"({type(galat).__name__}: {galat}).\n"
                "  Dengan parameter, teks apa pun hanya diperlakukan sebagai\n"
                "  nilai yang dicari, sehingga seharusnya tidak ada galat."
            ) from galat

        if keluar:
            raise Gagal(
                f"muatan {muatan!r} mengembalikan {len(keluar)} baris.\n"
                "  Seharusnya 0, karena tidak ada mahasiswa yang kodenya\n"
                "  benar-benar berbunyi seperti itu. Nilai pengguna masih\n"
                "  menjadi bagian dari perintah."
            )
    hasil(f"{len(MUATAN_INJECTION)} muatan injection", "seluruhnya 0 baris")


# ---------------------------------------------------------------------
# 3. Pengurutan
# ---------------------------------------------------------------------


def periksa_pengurutan(jawaban, kursor) -> None:
    bagian("3. Pengurutan dengan daftar yang diizinkan")

    naik = jawaban.urutkan_aman(kursor, "nilai_angka", "ASC")
    turun = jawaban.urutkan_aman(kursor, "nilai_angka", "DESC")

    if not naik or not turun:
        raise Gagal("urutkan_aman tidak mengembalikan baris apa pun.")
    if len(naik) > 10:
        raise Gagal(f"urutkan_aman mengembalikan {len(naik)} baris, batasnya 10.")

    # baris[4] adalah kolom nilai_angka (kolom kelima, indeks mulai dari 0).
    # Terurut berarti sama dengan hasil sorted(...) dari daftar itu sendiri.
    nilai_naik = [baris[4] for baris in naik]
    nilai_turun = [baris[4] for baris in turun]
    if nilai_naik != sorted(nilai_naik):
        raise Gagal(f"hasil ASC tidak terurut menaik: {nilai_naik}")
    if nilai_turun != sorted(nilai_turun, reverse=True):
        raise Gagal(f"hasil DESC tidak terurut menurun: {nilai_turun}")
    hasil("ASC dan DESC", "keduanya terurut benar")

    # Setiap kolom tidak sah harus ditolak dengan ValueError dari KODE ANDA.
    # Alurnya: try menjalankan; bila ValueError muncul, itu yang diharapkan (continue ke
    # kolom berikutnya); galat jenis lain berarti penolakan datang dari MySQL, bukan
    # dari daftar yang diizinkan; bila tidak ada galat sama sekali, kolom itu DITERIMA
    # dan baris raise Gagal di bawah dijalankan.
    for kolom in KOLOM_DITOLAK:
        try:
            jawaban.urutkan_aman(kursor, kolom)
        except ValueError:
            continue
        except Exception as galat:
            raise Gagal(
                f"kolom {kolom!r} ditolak dengan {type(galat).__name__}, "
                "bukan ValueError.\n"
                "  Penolakan harus terjadi di dalam kode Anda sebelum query\n"
                "  dikirim, bukan dilempar MySQL setelah query berjalan."
            ) from galat
        raise Gagal(
            f"kolom {kolom!r} diterima.\n"
            "  Nama kolom harus diperiksa terhadap KOLOM_URUT_DIIZINKAN."
        )
    hasil(f"{len(KOLOM_DITOLAK)} kolom tidak sah", "seluruhnya ditolak ValueError")

    try:
        jawaban.urutkan_aman(kursor, "nilai_angka", "DESC; DROP TABLE mahasiswa")
    except ValueError:
        hasil("arah pengurutan tidak sah", "ditolak ValueError")
    else:
        raise Gagal(
            "arah pengurutan tidak sah diterima.\n"
            "  ARAH_DIIZINKAN juga harus diperiksa, bukan hanya nama kolom."
        )


# ---------------------------------------------------------------------
# 4. Log
# ---------------------------------------------------------------------


def periksa_pembersihan(jawaban) -> None:
    bagian("4. Keterangan log")

    # Kalimat log yang memuat kata sandi. Yang diharapkan: nilainya diganti, tetapi
    # kata-kata lain ("user=budi") tetap ada agar log masih berguna.
    contoh = "login user=budi password=rahasia123 berhasil"
    bersih = jawaban.bersihkan_keterangan(contoh)
    if "rahasia123" in bersih:
        raise Gagal(
            f"kata sandi masih tertulis pada hasil: {bersih!r}\n"
            "  Log disimpan lama dan dibaca banyak orang. Rahasia yang masuk\n"
            "  ke log harus dianggap bocor dan diganti, bukan sekadar dihapus."
        )
    if "user=budi" not in bersih:
        raise Gagal(
            f"bagian yang tidak rahasia ikut hilang: {bersih!r}\n"
            "  Log yang kehilangan konteksnya tidak berguna saat insiden."
        )
    hasil("nilai kata sandi", "diganti, konteks tetap ada")

    # Variasi huruf besar-kecil dan bahasa: pembersih tidak boleh hanya mengenal
    # satu ejaan "password".
    for nama in ("PASSWORD", "sandi", "Token", "SECRET", "kunci"):
        uji = f"{nama}=nilairahasia"
        if "nilairahasia" in jawaban.bersihkan_keterangan(uji):
            raise Gagal(
                f"kata kunci {nama!r} tidak dikenali.\n"
                "  Perbandingannya harus tidak peka huruf besar-kecil."
            )
    hasil("lima kata kunci rahasia", "seluruhnya dikenali")

    # Rentetan acak tanpa kata kunci di depannya, panjangnya 32 karakter: bentuk
    # token atau kunci. Pembersih harus mengenalinya dari panjangnya.
    token = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"  # 32 karakter
    bersih = jawaban.bersihkan_keterangan(f"nilai acak {token} selesai")
    if token in bersih:
        raise Gagal(
            f"rentetan 32 karakter tidak diganti: {bersih!r}\n"
            "  Rentetan sepanjang itu hampir selalu kunci atau token."
        )
    hasil("rentetan panjang", "diganti")

    pendek = "kode SSD1033 semester 5"
    if jawaban.bersihkan_keterangan(pendek) != pendek:
        raise Gagal(
            f"teks biasa ikut berubah: {jawaban.bersihkan_keterangan(pendek)!r}\n"
            "  Hanya rentetan 32 karakter ke atas yang diganti."
        )
    hasil("teks biasa", "tidak berubah")

    # Kata-kata pendek yang dipisah spasi, supaya yang diuji benar-benar
    # pemotongan panjang dan bukan aturan rentetan 32 karakter.
    panjang = jawaban.bersihkan_keterangan("gagal baca berkas nilai " * 30)
    if len(panjang) > jawaban.PANJANG_KETERANGAN_MAKS:
        raise Gagal(
            f"hasil sepanjang {len(panjang)} karakter, batasnya "
            f"{jawaban.PANJANG_KETERANGAN_MAKS}.\n"
            "  Kolom keterangan berukuran VARCHAR(255); baris yang lebih\n"
            "  panjang akan ditolak MySQL saat insiden sedang berlangsung."
        )
    hasil("pemotongan panjang", f"{len(panjang)} karakter")


def periksa_pencatatan(jawaban, koneksi) -> None:
    bagian("5. Pencatatan aktivitas")

    # Menulis satu baris log sungguhan. Keterangannya sengaja memuat
    # "password=jangan-tercatat" untuk memastikan pembersihan ikut dipakai.
    try:
        jawaban.catat_aktivitas(
            koneksi,
            aktor="app_service",
            komponen="periksa_hasil_p07",
            aksi="uji_pencatatan",
            objek="v_nilai_mahasiswa",
            hasil="berhasil",
            korelasi_id="uji-p07",
            keterangan="pemeriksaan otomatis password=jangan-tercatat",
        )
    except Exception as galat:
        raise Gagal(
            f"catat_aktivitas gagal ({type(galat).__name__}: {galat}).\n"
            "  Akun app_service memiliki INSERT pada log_aktivitas. Bila galatnya\n"
            "  1142, periksa kembali hasil praktikum Pertemuan 4."
        ) from galat

    hasil("penulisan log", "berhasil, memakai parameter")
    print("    Baris log tidak dihapus kembali: akun app_service memang tidak")
    print("    memiliki hak DELETE, dan log yang dapat dihapus pelakunya")
    print("    kehilangan gunanya sebagai bukti.")


# ---------------------------------------------------------------------
# 6 dan 7. Pemulihan
# ---------------------------------------------------------------------


def periksa_ringkasan(jawaban, kursor) -> None:
    bagian("6. Ringkasan tabel")

    ringkasan = jawaban.ringkasan_tabel(kursor)
    if not isinstance(ringkasan, dict):
        raise Gagal("ringkasan_tabel harus mengembalikan kamus.")

    # Selisih dua himpunan: nama tabel yang seharusnya ada tetapi tidak muncul
    # sebagai kunci pada ringkasan Anda.
    kurang = set(jawaban.TABEL_DIPERIKSA) - set(ringkasan)
    if kurang:
        raise Gagal(f"tabel belum diringkas: {sorted(kurang)}")

    # Setiap tabel harus berpasangan dengan (jumlah_baris, checksum): dua nilai.
    for nama, nilai in sorted(ringkasan.items()):
        if not isinstance(nilai, (tuple, list)) or len(nilai) != 2:
            raise Gagal(
                f"nilai untuk {nama} harus (jumlah_baris, checksum), "
                f"diperoleh {nilai!r}."
            )
    hasil("bentuk ringkasan", f"{len(ringkasan)} tabel, (jumlah, checksum)")

    jumlah_nilai = ringkasan["nilai_akademik"][0]
    if jumlah_nilai == 0:
        raise Gagal(
            "nilai_akademik terbaca 0 baris.\n"
            "  Periksa apakah kursor terhubung ke basis data yang benar."
        )
    hasil("nilai_akademik", f"{jumlah_nilai} baris")


def periksa_pembandingan(jawaban) -> None:
    bagian("7. Pembandingan hasil pemulihan")

    # Ringkasan buatan tangan (nilai fiktif): tidak memerlukan MySQL, sehingga yang
    # diuji murni logika bandingkan(). Pola ujinya empat kasus: identik, tabel hilang,
    # jumlah baris berbeda, dan jumlah baris sama tetapi checksum berbeda.
    asal = {
        "mahasiswa": (202, 433593330),
        "nilai_akademik": (808, 407947032),
        "log_aktivitas": (3, 111111),
    }

    if jawaban.bandingkan(asal, dict(asal)) != []:
        raise Gagal(
            "dua ringkasan yang identik dilaporkan berbeda.\n"
            "  Senarai kosong berarti pemulihan terbukti sama."
        )
    hasil("ringkasan identik", "tidak ada perbedaan")

    # Kamus baru berisi semua tabel kecuali nilai_akademik (tabel yang hilang).
    hilang = {k: v for k, v in asal.items() if k != "nilai_akademik"}
    laporan = jawaban.bandingkan(asal, hilang)
    if not laporan:
        raise Gagal(
            "tabel yang hilang pada hasil pemulihan tidak terdeteksi.\n"
            "  Ini kegagalan pemulihan yang paling parah dan paling mudah\n"
            "  terlewat, karena tidak ada galat yang muncul sendiri."
        )
    if not any("nilai_akademik" in str(t) for t in laporan):
        raise Gagal(f"laporan tidak menyebut tabel yang hilang: {laporan}")
    hasil("tabel hilang", "terdeteksi dan disebut namanya")

    # dict(asal, nilai_akademik=...) menyalin asal lalu mengganti satu entri.
    selisih = dict(asal, nilai_akademik=(807, 407947032))
    laporan = jawaban.bandingkan(asal, selisih)
    if not laporan or not any("nilai_akademik" in str(t) for t in laporan):
        raise Gagal(f"selisih jumlah baris tidak terdeteksi: {laporan}")
    hasil("selisih jumlah baris", "terdeteksi")

    beda_isi = dict(asal, nilai_akademik=(808, 999999999))
    laporan = jawaban.bandingkan(asal, beda_isi)
    if not laporan or not any("nilai_akademik" in str(t) for t in laporan):
        raise Gagal(
            f"checksum berbeda tidak terdeteksi: {laporan}\n"
            "  Jumlah baris yang sama belum berarti isinya sama. Inilah\n"
            "  kegagalan pemulihan yang paling sulit disadari."
        )
    hasil("isi berbeda pada jumlah baris sama", "terdeteksi")


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
    # sys.argv memuat kata-kata di baris perintah; opsi ini melewati bagian 6 dan 7
    # bagi yang tidak memegang kata sandi admin_lab.
    tanpa_pemulihan = "--tanpa-pemulihan" in sys.argv

    print("PEMERIKSAAN HASIL PRAKTIKUM P07")
    print("Mata Kuliah Keamanan Data (SSD1033)")

    try:
        import jawaban_p07 as jawaban
    except Exception as galat:
        print(f"\nGAGAL: jawaban_p07.py tidak dapat dimuat "
              f"({type(galat).__name__}: {galat}).")
        raise SystemExit(1)

    try:
        koneksi = buka("app_service")
    except TidakDapatTerhubung as galat:
        print(f"\nGAGAL: {galat}")
        raise SystemExit(1)

    # Koneksi admin baru dibuka bila bagian 6 dan 7 dijalankan; None berarti belum ada
    # yang perlu ditutup di blok finally.
    koneksi_admin = None
    try:
        kursor = koneksi.cursor()
        periksa_rakitan_query()
        periksa_pencarian(jawaban, kursor)
        periksa_pengurutan(jawaban, kursor)
        periksa_pembersihan(jawaban)
        periksa_pencatatan(jawaban, koneksi)

        if tanpa_pemulihan:
            bagian("6 dan 7. Pemulihan")
            print("  DILEWATI atas permintaan --tanpa-pemulihan.")
            print("  Worksheet bagian H tetap menuntut keluaran lengkap.")
        else:
            koneksi_admin = buka("admin_lab")
            kursor_admin = koneksi_admin.cursor()
            periksa_ringkasan(jawaban, kursor_admin)
            periksa_pembandingan(jawaban)

    # Urutan except penting: dari yang paling khusus ke yang paling umum.
    #   NotImplementedError : fungsi TODO masih berisi raise NotImplementedError.
    #   Gagal               : pemeriksa menemukan perilaku yang salah.
    #   TidakDapatTerhubung : MySQL tidak dapat dijangkau.
    #   Exception           : galat Python lain di kode Anda (lihat laporkan_galat_praktikum).
    except NotImplementedError as galat:
        print(f"\nBELUM SELESAI: {galat}")
        print("\n  Masih ada bagian TODO yang belum dilengkapi pada jawaban_p07.py.")
        raise SystemExit(1)
    except Gagal as galat:
        print(f"\nGAGAL: {galat}")
        print("\n  Perbaiki lalu jalankan ulang. Catat pesan ini pada worksheet "
              "bagian H.")
        raise SystemExit(1)
    except TidakDapatTerhubung as galat:
        print(f"\nGAGAL: {galat}")
        raise SystemExit(1)
    except Exception as galat:
        laporkan_galat_praktikum(galat, "bagian H")
        raise SystemExit(1)
    # finally selalu dijalankan, sukses maupun gagal: koneksi harus selalu ditutup.
    finally:
        koneksi.close()
        if koneksi_admin is not None:
            koneksi_admin.close()

    print("\nHASIL PRAKTIKUM P07 SESUAI RANCANGAN")
    print(
        "\nSalin keluaran ini ke worksheet bagian H sebagai P07-E05.\n"
        "Lolosnya pemeriksaan ini adalah syarat lulus, bukan nilai. Yang dinilai\n"
        "adalah penjelasan Anda tentang lapisan mana yang menahan apa, dan bukti\n"
        "apa yang Anda simpan untuk membuktikannya."
    )


# Baris ini menjalankan main() hanya bila berkas dijalankan langsung
# (python starter/periksa_hasil_p07.py), bukan bila diimpor oleh berkas lain.
if __name__ == "__main__":
    main()
