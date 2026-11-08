"""Pemeriksaan hasil praktikum Pertemuan 6.

Menguji `jawaban_p06.py` yang Anda lengkapi. Yang diperiksa bukan hanya
apakah fungsinya berjalan, melainkan apakah laporan yang dihasilkannya
benar-benar tidak membocorkan orang:

    1. tidak ada kunci yang tertulis di dalam kode;
    2. penyamaran tetap sama untuk orang yang sama;
    3. penyamaran berubah bila kuncinya berbeda;
    4. penyamaran tidak dapat dibalik dengan menebak seluruh NIM;
    5. peringkasan menghitung orang, bukan baris;
    6. tidak ada sel di bawah ambang yang tetap terbit;
    7. tidak ada nilai tersembunyi yang dapat dihitung kembali dari selisih;
    8. penyembunyiannya tidak berlebihan sehingga laporan kehilangan gunanya.

Taruh berkas ini di folder starter/ pada proyek secure-academic-data-pipeline
Anda, bersebelahan dengan jawaban_p06.py, lalu jalankan dari akar proyek:

    python starter/periksa_hasil_p06.py

Skrip ini tidak mengirim apa pun ke luar komputer Anda.
"""

# =============================================================================
# CARA MEMBACA SKRIP INI
# =============================================================================
# Skrip ini adalah "penguji dari luar". Ia memanggil tiga fungsi pada
# jawaban_p06.py dengan masukan yang sudah ditentukan, lalu memeriksa PERILAKU
# hasilnya, bukan gaya kodenya.
#
# Satu hal yang membedakannya dari pemeriksa P5: pemeriksa ini menghitung
# jawaban yang benar sendiri (fungsi ringkas_acuan di bawah) dan membandingkannya
# dengan hasil kode Anda. Ia tidak pernah memakai hasil kode Anda sebagai acuan.
#
# Urutan jalannya: main() memuat jawaban_p06.py, membaca dataset, lalu
# menjalankan empat pemeriksaan berurutan. Pemeriksaan berhenti pada kegagalan
# PERTAMA; perbaiki, lalu jalankan ulang untuk melihat pesan berikutnya.
#
# Isi berkas ini: konstanta dan alat bantu cetak, fungsi acuan, empat fungsi
# periksa_*, pelapor galat, dan main() di bagian paling bawah.
# =============================================================================
from __future__ import annotations

# collections: Counter menghitung kemunculan, defaultdict membuat nilai awal otomatis.
# Dipakai pemeriksa untuk menghitung jawaban yang benar.
import collections
# hashlib: dipakai pemeriksa untuk MENCOBA membalik penyamaran Anda dengan hash biasa
# (md5, sha1, sha256), seperti yang dilakukan penyerang.
import hashlib
# re: pustaka ekspresi reguler (pencocok pola teks).
import re
# sys: dipakai untuk mengatur keluaran terminal dan jalur pencarian modul.
import sys
# Path: cara menulis jalur berkas yang sama di Windows, macOS, dan Linux.
from pathlib import Path

# Memaksa keluaran terminal berbahasa UTF-8 agar huruf dan simbol tampil benar di
# terminal Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# __file__ adalah jalur berkas ini; resolve() menjadikannya jalur lengkap; parent adalah
# folder tempat berkas ini berada, yaitu starter/.
STARTER = Path(__file__).resolve().parent
BERKAS_JAWABAN = STARTER / "jawaban_p06.py"

# Ambang ukuran sel minimum. Nilainya sama dengan AMBANG_BAWAAN pada jawaban_p06.py.
# Pemeriksa selalu memanggil tekan_sel_kecil(ringkasan, AMBANG) dengan nilai ini.
AMBANG = 5

# Cara kerja pola di bawah, dari kiri ke kanan:
#   ["']             sebuah tanda kutip pembuka (tunggal atau ganda);
#   (?=...{32,})     "lihat ke depan": pastikan setelah kutip ada sedikitnya 32 karakter
#                    berurutan dari himpunan huruf, angka, dan + / = _ - ;
#   [...]{32,}       cocokkan karakter-karakter itu;
#   ["']             sebuah tanda kutip penutup.
# Teks berspasi biasa tidak akan cocok.
# Literal panjang yang menyerupai kunci atau token yang dikodekan base64.
POLA_RAHASIA = re.compile(r"""["'](?=[A-Za-z0-9+/=_-]{32,})[A-Za-z0-9+/=_-]{32,}["']""")

# Baris seperti DATASET_PATH = "..." bisa panjang tetapi bukan rahasia. Pemeriksa 1 melewati
# baris yang nama di sebelah kiri tanda = berakhiran salah satu dari ini.
# Nama konstanta yang memuat lokasi, bukan rahasia.
AKHIRAN_BUKAN_RAHASIA = ("_PATH", "_DIR", "_FILE", "_URL")

# Dua kunci tetap untuk pengujian. Keduanya bukan rahasia dan tidak melindungi apa pun;
# tujuannya agar pemeriksa dapat memanggil samarkan() dengan kunci yang diketahui dan
# membandingkan hasilnya. Awalan b berarti byte, bukan teks.
KUNCI_UJI_A = b"kunci-uji-a-untuk-pemeriksaan-p06-saja"
KUNCI_UJI_B = b"kunci-uji-b-yang-berbeda-sama-sekali-00"


# Gagal adalah jenis galat milik skrip ini. Ia dilempar (raise) setiap kali sebuah
# pemeriksaan tidak terpenuhi, lalu ditangkap main() untuk dicetak sebagai "GAGAL: ...".
# Galat Python lain (yang bukan Gagal) berarti kode Anda sendiri yang bermasalah.
class Gagal(Exception):
    """Kegagalan pemeriksaan yang perlu diperbaiki mahasiswa."""


# Mencetak judul bagian, diawali baris kosong (\n).
def bagian(judul: str) -> None:
    print(f"\n== {judul} ==")


# Mencetak satu baris hasil. {label:<44} berarti label rata kiri dalam lebar 44 karakter,
# supaya titik dua pada semua baris sejajar.
def hasil(label: str, nilai: str) -> None:
    print(f"  {label:<44}: {nilai}")


# Satu sel laporan dikenali oleh pasangan (program_studi, semester). Pasangan ini dipakai
# untuk mencocokkan sel hasil kode Anda dengan sel acuan.
def kunci_sel(satu: dict) -> tuple:
    return (satu["program_studi"], satu["semester"])


# ---------------------------------------------------------------------
# Acuan: dihitung ulang oleh pemeriksa, bukan diambil dari jawaban
# ---------------------------------------------------------------------


# Jawaban BENAR versi pemeriksa untuk TODO 2: mengelompokkan menurut (program_studi,
# semester) dan menghitung ORANG memakai himpunan (set), bukan baris. Hasil kode Anda
# dibandingkan dengan ini. Bentuknya sama dengan ringkas() pada contoh_penyamaran.py.
def ringkas_acuan(baris: list[dict]) -> dict:
    mahasiswa = collections.defaultdict(set)
    didampingi = collections.defaultdict(set)
    for satu in baris:
        kunci = (satu["program_studi"], int(satu["semester"]))
        mahasiswa[kunci].add(satu["kode_mahasiswa"])
        if satu["status_pendampingan"] == "Ya":
            didampingi[kunci].add(satu["kode_mahasiswa"])
    return {
        kunci: (len(nilai), len(didampingi[kunci]))
        for kunci, nilai in mahasiswa.items()
    }


# Menentukan sel mana yang SEHARUSNYA dipilih aturan 3: di antara sel yang tidak disembunyikan
# aturan 1, ambil yang jumlah mahasiswanya terkecil; bila seri, semester terkecil. min()
# dengan key membandingkan pasangan (jumlah, semester) dari kiri ke kanan.
def sel_sekunder_seharusnya(acuan: dict, prodi: str) -> tuple | None:
    """Sel mana yang seharusnya dipilih aturan 3 untuk satu program studi."""
    tersisa = [
        (kunci, nilai)
        for kunci, nilai in acuan.items()
        if kunci[0] == prodi and nilai[0] >= AMBANG
    ]
    if not tersisa:
        return None
    return min(tersisa, key=lambda pasangan: (pasangan[1][0], pasangan[0][1]))[0]


# ---------------------------------------------------------------------
# Pemeriksaan
# ---------------------------------------------------------------------


def periksa_rahasia_di_kode() -> None:
    # Pemeriksaan 1 membaca jawaban_p06.py sebagai teks biasa, bukan menjalankannya.
    bagian("1. Kunci di dalam kode")
    if not BERKAS_JAWABAN.exists():
        raise Gagal(f"berkas {BERKAS_JAWABAN.name} tidak ditemukan.")

    baris_bermasalah = []
    for nomor, teks in enumerate(
        BERKAS_JAWABAN.read_text(encoding="utf-8").splitlines(), start=1
    ):
        # split("#", 1)[0] memotong baris pada tanda # pertama dan mengambil bagian sebelumnya,
        # sehingga isi komentar tidak ikut diperiksa.
        bersih = teks.split("#", 1)[0]
        # Mengambil nama di sebelah kiri tanda = (huruf besar), untuk dicocokkan dengan
        # AKHIRAN_BUKAN_RAHASIA.
        nama = bersih.split("=", 1)[0].strip().upper()
        if nama.endswith(AKHIRAN_BUKAN_RAHASIA):
            continue
        if POLA_RAHASIA.search(bersih):
            baris_bermasalah.append((nomor, teks.strip()[:70]))

    if baris_bermasalah:
        rincian = "; ".join(f"baris {n}: {t}" for n, t in baris_bermasalah)
        raise Gagal(
            f"ditemukan nilai panjang yang menyerupai kunci di dalam kode ({rincian}).\n"
            "  Kunci dibaca dari berkas melalui muat_kunci(), tidak ditulis di kode.\n"
            "  Kunci yang pernah tertulis di berkas yang dibagikan harus dianggap\n"
            "  bocor dan wajib diganti, bukan sekadar dihapus."
        )
    hasil("kunci tertulis di kode", "tidak ditemukan")


def periksa_penyamaran(jawaban) -> None:
    bagian("2. Penyamaran pengenal")
    # Kode uji yang dipakai pemeriksa. Pemeriksa memanggil samarkan() dua kali dengan kode dan
    # kunci yang sama, lalu sekali dengan kunci lain.
    kode = "MHS-SYN-0201"

    pertama = jawaban.samarkan(kode, KUNCI_UJI_A)
    kedua = jawaban.samarkan(kode, KUNCI_UJI_A)

    if not isinstance(pertama, str):
        raise Gagal("samarkan harus mengembalikan teks.")
    # fullmatch: SELURUH teks harus terdiri dari 16 karakter heksadesimal huruf kecil (angka
    # 0-9 dan huruf a-f). Potongan [:16] pada hasil hexdigest() menghasilkan bentuk ini.
    if not re.fullmatch(r"[0-9a-f]{16}", pertama):
        raise Gagal(
            f"pengenal tersamar harus 16 karakter heksadesimal, diperoleh {pertama!r}."
        )
    hasil("bentuk pengenal", f"{len(pertama)} karakter heksadesimal")

    if kode in pertama:
        raise Gagal("pengenal tersamar masih memuat kode aslinya.")

    # Kode dan kunci yang sama harus menghasilkan pengenal yang SAMA. Salt acak melanggar
    # ini, karena baris milik satu orang tidak dapat lagi digabungkan.
    if pertama != kedua:
        raise Gagal(
            "orang yang sama menghasilkan dua pengenal berbeda.\n"
            "  Baris milik satu mahasiswa tidak akan dapat digabungkan, dan\n"
            "  laporannya akan menghitung satu orang sebagai beberapa orang.\n"
            "  Jangan memakai salt acak di sini; penyamaran bukan kata sandi."
        )
    hasil("orang yang sama, pengenal sama", "ya")

    # Kunci berbeda harus menghasilkan pengenal berbeda. Bila sama, kunci tidak dipakai.
    dengan_kunci_lain = jawaban.samarkan(kode, KUNCI_UJI_B)
    if dengan_kunci_lain == pertama:
        raise Gagal(
            "kunci tidak berpengaruh terhadap hasil penyamaran.\n"
            "  Berarti fungsinya memakai hash biasa. Dua laporan yang terbit\n"
            "  pada waktu berbeda akan memakai pengenal yang sama persis dan\n"
            "  dapat digabungkan oleh siapa pun yang memegang keduanya."
        )
    hasil("kunci berbeda, pengenal berbeda", "ya")

    # Memeriksa apakah hasil Anda sama dengan hash BIASA (tanpa kunci) atas kode yang sama.
    # Bila sama, berarti fungsi Anda belum memakai kunci.
    for nama_algoritma in ("md5", "sha1", "sha256", "sha512"):
        polos = hashlib.new(nama_algoritma, kode.encode("utf-8")).hexdigest()[:16]
        if pertama == polos:
            raise Gagal(
                f"pengenal sama dengan {nama_algoritma} biasa atas kode mahasiswa.\n"
                "  Bentuk NIM dapat ditebak, sehingga seluruh kemungkinannya dapat\n"
                "  dicoba satu per satu dalam hitungan milidetik. Lihat bagian 1\n"
                "  pada contoh_penyamaran.py."
            )

    # Percobaan serangan. Penyerang yang tahu bentuk NIM (MHS-SYN-0001 sampai 9999) cukup
    # menghitung hash biasa untuk setiap kemungkinan dan mencari yang sama dengan pengenal
    # Anda. Pemeriksa melakukan hal itu untuk 9999 kandidat. Penyamaran berkunci lolos karena
    # penyerang tidak memegang kunci, sehingga tidak ada hash biasa yang cocok.
    ditemukan = None
    for nomor in range(1, 10000):
        kandidat = f"MHS-SYN-{nomor:04d}"
        for nama_algoritma in ("md5", "sha1", "sha256"):
            polos = hashlib.new(nama_algoritma, kandidat.encode("utf-8")).hexdigest()[:16]
            if polos == pertama:
                ditemukan = kandidat
                break
        if ditemukan:
            break
    if ditemukan:
        raise Gagal(
            f"pengenal dapat dibalik dengan menebak; ketemu {ditemukan}.\n"
            "  Penyamaran harus memakai kunci, bukan hash biasa."
        )
    hasil("tahan tebakan seluruh ruang NIM", "ya, 9999 percobaan gagal")


def periksa_peringkasan(jawaban, baris: list[dict], acuan: dict) -> list[dict]:
    bagian("3. Peringkasan kelompok")

    # Memanggil kode Anda dengan seluruh dataset. Hasil yang diharapkan: senarai kamus.
    ringkasan = jawaban.ringkas_kelompok(baris)
    if not isinstance(ringkasan, list) or not ringkasan:
        raise Gagal("ringkas_kelompok harus mengembalikan senarai yang tidak kosong.")

    # Himpunan nama kunci yang wajib ada. wajib - set(ringkasan[0]) adalah selisih himpunan:
    # kunci wajib yang TIDAK ada pada kamus pertama hasil Anda.
    wajib = {"program_studi", "semester", "jumlah_mahasiswa", "jumlah_didampingi"}
    kurang = wajib - set(ringkasan[0])
    if kurang:
        raise Gagal(f"kunci kamus belum lengkap, kurang: {sorted(kurang)}")

    if len(ringkasan) != len(acuan):
        raise Gagal(
            f"jumlah kelompok {len(ringkasan)}, seharusnya {len(acuan)}.\n"
            "  Kelompoknya adalah kombinasi program studi dan semester."
        )
    hasil("jumlah kelompok", f"{len(ringkasan)}")

    bukan_bilangan = [s for s in ringkasan if not isinstance(s["semester"], int)]
    if bukan_bilangan:
        contoh = bukan_bilangan[0]["semester"]
        raise Gagal(
            f"semester harus bilangan bulat, diperoleh {contoh!r}.\n"
            "  Nilai dari CSV selalu berupa teks; ubah dengan int()."
        )

    diperoleh = {kunci_sel(s): (s["jumlah_mahasiswa"], s["jumlah_didampingi"]) for s in ringkasan}

    # Counter menghitung jumlah BARIS per kelompok. Angka ini dipakai untuk mengenali jawaban
    # yang keliru menghitung baris alih-alih orang.
    total_baris = collections.Counter(
        (s["program_studi"], int(s["semester"])) for s in baris
    )
    for kunci, nilai in sorted(acuan.items()):
        if kunci not in diperoleh:
            raise Gagal(f"kelompok {kunci} tidak ada pada hasil.")
        # Bila angka Anda sama persis dengan jumlah baris padahal jumlah orang yang benar berbeda,
        # pemeriksa tahu Anda menghitung baris dan memberi pesan khusus untuk itu.
        if diperoleh[kunci][0] == total_baris[kunci] and nilai[0] != total_baris[kunci]:
            raise Gagal(
                f"kelompok {kunci[0]} semester {kunci[1]} menghitung "
                f"{diperoleh[kunci][0]} — itu jumlah BARIS, bukan jumlah orang.\n"
                f"  Jumlah orang yang benar adalah {nilai[0]}.\n"
                "  Setiap mahasiswa punya beberapa baris nilai. Menghitung baris\n"
                "  membuat sel yang sebenarnya kecil tampak besar dan aman."
            )
        if diperoleh[kunci] != nilai:
            raise Gagal(
                f"kelompok {kunci[0]} semester {kunci[1]} menghasilkan "
                f"{diperoleh[kunci]}, seharusnya {nilai} "
                "(jumlah_mahasiswa, jumlah_didampingi)."
            )
    hasil("menghitung orang, bukan baris", "ya")
    hasil("seluruh angka cocok dengan acuan", "ya")
    return ringkasan


def periksa_penekanan(jawaban, ringkasan: list[dict], acuan: dict) -> None:
    bagian("4. Penyembunyian sel kecil")

    # Menyimpan salinan masukan SEBELUM memanggil kode Anda, supaya dapat diketahui bila
    # fungsi Anda mengubah masukannya. dict(s) membuat salinan tiap kamus.
    salinan = [dict(s) for s in ringkasan]
    ditekan = jawaban.tekan_sel_kecil(ringkasan, AMBANG)

    if not isinstance(ditekan, list) or len(ditekan) != len(ringkasan):
        raise Gagal("tekan_sel_kecil harus mengembalikan senarai dengan panjang sama.")

    # Membuat salinan baru dari masukan sesudah dipakai, lalu membandingkannya dengan salinan
    # tadi. Berbeda berarti fungsi Anda mengubah senarai masukan.
    if [dict(s) for s in ringkasan] != salinan:
        raise Gagal(
            "senarai masukan ikut berubah.\n"
            "  Kembalikan senarai baru. Laporan sebelum dan sesudah penyembunyian\n"
            "  harus tetap dapat dibandingkan saat diaudit."
        )
    hasil("masukan tidak diubah", "ya")

    hasil_sel = {kunci_sel(s): s for s in ditekan}

    # Aturan 1: sel dengan jumlah_mahasiswa di bawah ambang harus disembunyikan, dan KEDUA nilainya
    # (jumlah_mahasiswa dan jumlah_didampingi) harus None.
    # Aturan 1
    for kunci, (jumlah, _) in sorted(acuan.items()):
        if jumlah < AMBANG:
            satu = hasil_sel[kunci]
            if satu["jumlah_mahasiswa"] is not None:
                raise Gagal(
                    f"{kunci[0]} semester {kunci[1]} berisi {jumlah} mahasiswa "
                    f"tetapi tetap diterbitkan.\n"
                    f"  Sel di bawah ambang {AMBANG} harus disembunyikan."
                )
            if satu["jumlah_didampingi"] is not None:
                raise Gagal(
                    f"{kunci[0]} semester {kunci[1]} menyembunyikan jumlah_mahasiswa "
                    "tetapi masih menerbitkan jumlah_didampingi.\n"
                    "  Pembaca tetap tahu jumlah orangnya sedikitnya sebesar angka itu."
                )
    hasil(f"sel di bawah ambang {AMBANG} disembunyikan", "ya")

    # Aturan 2: untuk sel yang lolos aturan 1, jumlah_didampingi disembunyikan bila kelompok
    # didampingi ATAU kelompok tidak didampingi berjumlah kurang dari ambang. Dua arah ini
    # diperiksa. Menyembunyikan yang tidak perlu juga dianggap keliru.
    # Aturan 2
    for kunci, (jumlah, dampingi) in sorted(acuan.items()):
        satu = hasil_sel[kunci]
        if satu["jumlah_mahasiswa"] is None:
            continue
        perlu = dampingi < AMBANG or (jumlah - dampingi) < AMBANG
        if perlu and satu["jumlah_didampingi"] is not None:
            sebab = "didampingi" if dampingi < AMBANG else "tidak didampingi"
            raise Gagal(
                f"{kunci[0]} semester {kunci[1]}: {jumlah} mahasiswa, "
                f"{dampingi} didampingi.\n"
                f"  Kelompok yang {sebab} berjumlah kurang dari {AMBANG} orang,\n"
                "  sehingga jumlah_didampingi harus disembunyikan."
            )
        if not perlu and satu["jumlah_didampingi"] is None:
            raise Gagal(
                f"{kunci[0]} semester {kunci[1]} menyembunyikan jumlah_didampingi "
                "padahal kedua kelompoknya sudah mencapai ambang.\n"
                "  Penyembunyian yang tidak perlu mengurangi guna laporan tanpa "
                "menambah perlindungan."
            )
    hasil("atribut sensitif disembunyikan pada dua arah", "ya")

    # Aturan 3: mencegah nilai yang disembunyikan dihitung kembali dari selisih terhadap total
    # program studi. Dikelompokkan per program studi, lalu dibandingkan dengan acuan.
    # Aturan 3
    per_prodi = collections.defaultdict(list)
    for kunci in acuan:
        per_prodi[kunci[0]].append(kunci)

    for prodi, daftar in sorted(per_prodi.items()):
        primer = [k for k in daftar if acuan[k][0] < AMBANG]
        tertekan = [k for k in daftar if hasil_sel[k]["jumlah_mahasiswa"] is None]

        if not primer:
            if tertekan:
                raise Gagal(
                    f"{prodi}: {len(tertekan)} sel disembunyikan padahal tidak ada sel "
                    f"di bawah ambang.\n"
                    "  Penyembunyian sekunder hanya diperlukan bila ada penyembunyian primer."
                )
            continue

        # Berapa sel yang harus tersembunyi pada satu program studi: bila hanya ada satu sel primer
        # diperlukan 2 (primer + satu sekunder); bila lebih dari satu, jumlah primer sudah cukup.
        wajib = max(2, len(primer))
        if len(tertekan) < wajib:
            terbit = sum(
                acuan[k][0] for k in daftar if hasil_sel[k]["jumlah_mahasiswa"] is not None
            )
            total = sum(acuan[k][0] for k in daftar)
            raise Gagal(
                f"{prodi}: hanya {len(tertekan)} sel yang disembunyikan.\n"
                f"  Total program studi {total} tetap terbit, sel yang terlihat "
                f"berjumlah {terbit},\n"
                f"  sehingga nilai yang disembunyikan terbaca kembali sebagai "
                f"{total - terbit}.\n"
                f"  Sedikitnya {wajib} sel harus disembunyikan (penyembunyian sekunder)."
            )
        if len(tertekan) > wajib:
            raise Gagal(
                f"{prodi}: {len(tertekan)} sel disembunyikan, seharusnya cukup {wajib}.\n"
                "  Menyembunyikan lebih banyak memang lebih aman, tetapi laporan yang\n"
                "  kehilangan gunanya akan ditinggalkan penggunanya."
            )

        # Pilihan sel sekunder hanya dibandingkan bila ada tepat SATU sel primer pada program studi.
        if len(primer) == 1:
            seharusnya = sel_sekunder_seharusnya(acuan, prodi)
            dipilih = [k for k in tertekan if k not in primer]
            if seharusnya is not None and dipilih and dipilih[0] != seharusnya:
                raise Gagal(
                    f"{prodi}: sel sekunder yang disembunyikan adalah semester "
                    f"{dipilih[0][1]}, seharusnya semester {seharusnya[1]}.\n"
                    "  Aturannya: jumlah_mahasiswa terkecil, dan bila seri pilih\n"
                    "  semester terkecil. Laporan harus dapat dihasilkan ulang\n"
                    "  dengan hasil yang sama oleh orang lain."
                )
    hasil("penyembunyian sekunder menutup selisih", "ya")

    # Angka yang tetap terbit harus sama dengan acuan. Penyembunyian tidak boleh mengubah nilai.
    # Nilai yang tidak disembunyikan tidak boleh berubah
    for kunci, (jumlah, dampingi) in acuan.items():
        satu = hasil_sel[kunci]
        if satu["jumlah_mahasiswa"] is not None and satu["jumlah_mahasiswa"] != jumlah:
            raise Gagal(
                f"{kunci[0]} semester {kunci[1]}: jumlah_mahasiswa berubah menjadi "
                f"{satu['jumlah_mahasiswa']}, seharusnya {jumlah}."
            )
        if satu["jumlah_didampingi"] is not None and satu["jumlah_didampingi"] != dampingi:
            raise Gagal(
                f"{kunci[0]} semester {kunci[1]}: jumlah_didampingi berubah menjadi "
                f"{satu['jumlah_didampingi']}, seharusnya {dampingi}."
            )
    hasil("nilai yang terbit tidak berubah", "ya")

    jumlah_ditekan = sum(1 for s in ditekan if s["jumlah_mahasiswa"] is None)
    hasil("sel yang disembunyikan", f"{jumlah_ditekan} dari {len(ditekan)}")


# Dipanggil main() bila kode ANDA menimbulkan galat Python yang tidak dikenali pemeriksa
# (misalnya TypeError karena teks dan byte tertukar). Tanpa fungsi ini yang tampil adalah
# Traceback panjang; dengan fungsi ini yang tampil adalah nama galat, baris kode Anda
# yang menimbulkannya, dan petunjuk singkat.
def laporkan_galat_praktikum(galat: Exception, worksheet: str = "") -> None:
    """Ubah galat Python mentah menjadi pesan yang menunjuk baris kode Anda."""
    import sysconfig
    import traceback

    print(f"\nGALAT saat pemeriksa menjalankan kode Anda: {type(galat).__name__}: {galat}")

    pustaka = (sysconfig.get_paths()["stdlib"], "site-packages")
    bingkai = [b for b in traceback.extract_tb(galat.__traceback__)
               if Path(b.filename).resolve() != Path(__file__).resolve()
               and not any(p in b.filename for p in pustaka)]
    if bingkai:
        terakhir = bingkai[-1]
        print(f"\n  Terjadi pada {Path(terakhir.filename).name}, baris {terakhir.lineno}, di fungsi {terakhir.name}:")
        if terakhir.line:
            print(f"      {terakhir.line}")

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


# Titik awal. Urutannya: (1) muat jawaban_p06.py, (2) baca dataset, (3) hitung acuan,
# (4) jalankan empat pemeriksaan, (5) cetak hasil akhir bila semuanya lolos.
# raise SystemExit(1) mengakhiri skrip dengan kode keluar 1 (artinya gagal); kode keluar 0
# berarti sukses.
def main() -> None:
    print("PEMERIKSAAN HASIL PRAKTIKUM P06")
    print("Mata Kuliah Keamanan Data (SSD1033)")

    # Menambahkan folder starter/ ke daftar tempat Python mencari modul, supaya baris
    # "import jawaban_p06" di bawah menemukan berkas jawaban_p06.py.
    sys.path.insert(0, str(STARTER))
    try:
        # Mengimpor berkas jawaban Anda sebagai modul bernama "jawaban". Saat diimpor, kode di
        # tingkat atas berkas itu dijalankan; kesalahan penulisan (misalnya IndentationError)
        # muncul di sini sebagai "tidak dapat dimuat".
        import jawaban_p06 as jawaban
    except Exception as galat:
        print(f"\nGAGAL: jawaban_p06.py tidak dapat dimuat ({type(galat).__name__}: {galat}).")
        raise SystemExit(1)

    try:
        baris = jawaban.baca_dataset()
    except Exception as galat:
        print(f"\nGAGAL: dataset tidak dapat dibaca ({galat}).")
        raise SystemExit(1)

    acuan = ringkas_acuan(baris)

    try:
        periksa_rahasia_di_kode()
        periksa_penyamaran(jawaban)
        ringkasan = periksa_peringkasan(jawaban, baris, acuan)
        periksa_penekanan(jawaban, ringkasan, acuan)
    # Urutan except penting: Python mencoba dari atas dan memakai yang pertama cocok.
    # NotImplementedError berarti masih ada TODO yang belum dikerjakan. Gagal berarti sebuah
    # pemeriksaan tidak terpenuhi. Exception (paling bawah) menampung galat lain dari kode
    # Anda.
    except NotImplementedError as galat:
        print(f"\nBELUM SELESAI: {galat}")
        print("\n  Masih ada bagian TODO yang belum dilengkapi pada jawaban_p06.py.")
        raise SystemExit(1)
    except Gagal as galat:
        print(f"\nGAGAL: {galat}")
        print("\n  Perbaiki lalu jalankan ulang. Catat pesan ini pada worksheet bagian G.")
        raise SystemExit(1)
    except Exception as galat:
        laporkan_galat_praktikum(galat, "bagian G")
        raise SystemExit(1)

    print("\nHASIL PRAKTIKUM P06 SESUAI RANCANGAN")
    print(
        "\nSalin keluaran ini ke worksheet bagian G sebagai P06-E03.\n"
        "Lolosnya pemeriksaan ini adalah syarat lulus, bukan nilai. Yang dinilai\n"
        "adalah pembelaan Anda atas ambang yang dipilih, dan apa yang tetap\n"
        "tidak terlindungi setelah penyembunyian dilakukan."
    )


if __name__ == "__main__":
    main()
