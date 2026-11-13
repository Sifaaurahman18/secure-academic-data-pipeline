"""Pemeriksaan hasil Pertemuan 10 — pipeline yang gagal dengan aman.

Skrip ini menguji PERILAKU pipeline Anda, bukan bentuk kodenya. Cara Anda
menulis setiap TODO bebas, selama pipelinya berlaku sebagaimana mestinya. Satu
pengecualian ada pada bagian 6: di sana isi berkas memang dibaca, untuk
memastikan tidak ada kata sandi yang tertulis di dalam kode.

Menjalankan, dari folder mana pun:

    python "starter/periksa_hasil_p10.py"

**MySQL tidak diperlukan.** Pemuatan diuji memakai koneksi tiruan, sehingga
Anda dapat memeriksa pekerjaan sendiri sebelum laboratorium tersedia. Yang
diuji koneksi tiruan itu justru bagian yang paling sulit dibuktikan pada basis
data sungguhan, yaitu apa yang terjadi ketika pemuatan gagal di tengah jalan.

Skrip ini menjalankan `pipeline.validasi` dua kali, sehingga menimpa
`data/processed/hasil_pipeline.csv` dan menambah berkas karantina. Berkas
mentah dan berkas pembanding tidak pernah disentuh.

Lolosnya pemeriksa adalah syarat lulus praktikum, bukan nilainya.
"""

# =============================================================================
# CARA MEMBACA SKRIP INI
# =============================================================================
# Skrip ini adalah "penguji dari luar" untuk pipeline Anda. Ia memanggil fungsi
# yang Anda lengkapi (keutuhan.hitung_sha256, aturan.periksa_baris,
# validasi.cari_duplikat, pencatatan.bersihkan, muat.muat_batch) dengan masukan
# yang sudah ditentukan, lalu memeriksa PERILAKU hasilnya.
#
# Pola umum: fungsi harus(kondisi, pesan) di bawah. Bila kondisi salah, Gagal
# dilempar dengan pesan yang menjelaskan apa yang keliru. Bila benar, lapor()
# mencetak satu baris keterangan.
#
# Urutan jalannya: main() menjalankan enam pemeriksaan berurutan, satu per TODO
# (bagian 6 memeriksa hasil akhir). Pemeriksaan berhenti pada kegagalan PERTAMA;
# perbaiki, lalu jalankan ulang untuk melihat pesan berikutnya.
#
# Bagian 5 (pemuatan) memakai koneksi TIRUAN (kelas _Sambungan dan _Kursor): objek
# buatan yang mencatat commit/rollback dan meniru baris tertunda/permanen.
# Ini bukan pengujian integrasi terhadap MySQL yang sebenarnya.
#
# Isi berkas ini: konstanta dan alat bantu cetak, enam fungsi periksa_*, dua kelas
# koneksi tiruan, pelapor galat, dan main() di bagian bawah.
# =============================================================================
from __future__ import annotations

# io: StringIO dipakai untuk menampung keluaran layar pipeline sementara (bagian 6).
import io
# sys: untuk mengatur keluaran terminal dan jalur pencarian modul.
import sys
# redirect_stdout: mengalihkan teks yang di-print() ke penampung, bukan ke layar.
from contextlib import redirect_stdout
# Path: cara menulis jalur berkas yang sama di Windows, macOS, dan Linux.
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

# Memaksa keluaran terminal berbahasa UTF-8 agar huruf dan simbol tampil benar di
# terminal Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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

# Menambahkan akar proyek ke jalur pencarian modul supaya "from pipeline import ..."
# di bawah menemukan paket pipeline/ milik Anda.
sys.path.insert(0, str(PROYEK))

# noqa: E402 meminta alat pemeriksa gaya tidak mengeluh bahwa import ini muncul
# setelah baris kode lain (sys.path harus diatur dulu agar import ini berhasil).
from pipeline import aturan, keutuhan, konfigurasi, muat, pencatatan, validasi  # noqa: E402

# Satu baris yang sah menurut seluruh aturan. Setiap pengujian pada bagian 2
# mengubah tepat satu kolom, sehingga kode yang muncul dapat dipastikan berasal
# dari kolom itu dan bukan dari sisa barisnya.
BARIS_SAH = {
    "record_id": "R99001",
    "kode_mahasiswa": "MHS-SYN-0001",
    "program_studi": "Sains Data",
    "semester": "5",
    "kode_mk": "SSD1033",
    "nilai_angka": "80",
    "persentase_kehadiran": "90",
    "status_kelulusan": "Lulus",
    "status_pendampingan": "Tidak",
    "waktu_pembaruan": "2026-07-01T08:00:00",
}


# Jenis galat milik pemeriksa sendiri. main() menangkapnya dan menampilkan
# "GAGAL: <pesan>"; galat Python biasa ditangani terpisah oleh laporkan_galat_praktikum.
class Gagal(Exception):
    """Satu pemeriksaan tidak terpenuhi."""


# Alat bantu cetak: judul bagian bergaris bawah, lalu satu baris hasil berlabel
# (label diratakan kiri selebar 44 karakter agar rapi).
def bagian(judul: str) -> None:
    print(f"\n{judul}")
    print("-" * len(judul))


def lapor(label: str, nilai: str) -> None:
    print(f"  {label:<44} {nilai}")


# Inti semua pemeriksaan: kondisi yang salah langsung menjadi kegagalan berpesan.
def harus(benar: bool, pesan: str) -> None:
    if not benar:
        raise Gagal(pesan)


# Contoh: ubah(nilai_angka="105") menghasilkan salinan BARIS_SAH yang hanya berbeda
# pada nilai_angka. "**kolom" menampung semua argumen bernama sebagai kamus, dan
# {**a, **b} menggabungkan dua kamus (yang belakangan menimpa).
def ubah(**kolom: str) -> dict[str, str]:
    """Salin baris sah, lalu ganti kolom yang disebut."""
    return {**BARIS_SAH, **kolom}


# ---------------------------------------------------------------------
# 1. Gerbang keutuhan — TODO 1
# ---------------------------------------------------------------------


def periksa_gerbang(kode_mk_sah: set[str]) -> None:
    bagian("1. Gerbang keutuhan berkas masukan (TODO 1)")

    # Berkas referensi (daftar mata kuliah) dihitung ringkasan SHA-256-nya dengan fungsi
    # Anda. Hasil yang benar: 64 karakter heksadesimal huruf kecil, dan sama dengan nilai
    # yang tercatat di manifest.
    referensi = konfigurasi.BERKAS_REFERENSI_MK
    ringkasan = keutuhan.hitung_sha256(referensi)
    harus(
        isinstance(ringkasan, str) and len(ringkasan) == 64,
        "hitung_sha256() harus mengembalikan 64 karakter heksadesimal, "
        f"bukan {ringkasan!r}",
    )
    harus(
        ringkasan == ringkasan.lower(),
        "hitung_sha256() harus mengembalikan huruf kecil agar dapat dibandingkan "
        "langsung dengan isi manifest",
    )
    tercatat = keutuhan.baca_manifest().get(keutuhan.kunci_manifest(referensi))
    harus(
        ringkasan == tercatat,
        f"ringkasan {referensi.name} tidak sama dengan yang tercatat pada manifest. "
        "Pastikan berkas dibaca dalam mode biner dan seluruh isinya ikut dihitung",
    )
    lapor("hitung_sha256 cocok dengan manifest", ringkasan[:16] + "...")

    # Berkas yang isinya berubah harus ditolak, bukan sekadar diperingatkan.
    # Caranya: salin berkas referensi ditambah satu baris, simpan sebagai berkas
    # sementara, lalu minta gerbang memeriksanya. Berkas itu tidak ada di manifest,
    # sehingga gerbang yang benar melempar KeutuhanGagal. Blok finally menghapus
    # berkas sementara apa pun hasilnya.
    sementara = konfigurasi.DIR_PROCESSED / "_uji_keutuhan.tmp"
    sementara.parent.mkdir(parents=True, exist_ok=True)
    sementara.write_bytes(referensi.read_bytes() + b"# baris tambahan\n")
    try:
        keutuhan.gerbang_keutuhan(sementara)
    except keutuhan.KeutuhanGagal:
        lapor("berkas tak dikenal ditolak", "ya")
    else:
        raise Gagal(
            "gerbang_keutuhan() meloloskan berkas yang tidak tercatat pada manifest. "
            "Peringatan yang tidak menghentikan apa pun bukan gerbang"
        )
    finally:
        sementara.unlink(missing_ok=True)

    # Berkas yang tercatat dan tidak berubah harus lolos, dan mengembalikan
    # ringkasannya untuk dipakai sebagai catatan asal-usul.
    kembali = keutuhan.gerbang_keutuhan(referensi)
    harus(
        kembali == ringkasan,
        "gerbang_keutuhan() harus mengembalikan ringkasan berkas yang diperiksa",
    )
    lapor("berkas yang cocok diloloskan", "ya")

    # Manifest uji hanya berlaku selama blok ini; aset proyek tidak diubah.
    with TemporaryDirectory(prefix="_uji_p10_", dir=konfigurasi.PROYEK) as folder:
        dikenal = Path(folder) / "tercatat.csv"
        dikenal.write_bytes(b"nilai\n66\n")
        kunci = keutuhan.kunci_manifest(dikenal)
        catatan = {kunci: keutuhan.hitung_sha256(dikenal)}
        dikenal.write_bytes(b"nilai\n95\n")
        with patch.object(keutuhan, "baca_manifest", return_value=catatan):
            try:
                keutuhan.gerbang_keutuhan(dikenal)
            except keutuhan.KeutuhanGagal:
                lapor("berkas tercatat yang berubah ditolak", "ya")
            else:
                raise Gagal(
                    "gerbang_keutuhan() meloloskan berkas tercatat yang hash-nya "
                    "berubah. Bandingkan hash aktual dengan manifest dan "
                    "raise KeutuhanGagal bila berbeda"
                )


# ---------------------------------------------------------------------
# 2. Aturan validasi per baris — TODO 2
# ---------------------------------------------------------------------


def periksa_aturan(kode_mk_sah: set[str]) -> None:
    bagian("2. Aturan validasi satu baris (TODO 2)")

    harus(
        aturan.periksa_baris(dict(BARIS_SAH), kode_mk_sah) == [],
        "baris yang sepenuhnya sah tidak boleh menghasilkan temuan apa pun",
    )
    lapor("baris sah lolos", "ya")

    # Tiga belas kasus uji. Tiap kasus = (kode aturan yang harus muncul, baris yang
    # hanya berbeda pada SATU kolom dari baris sah). Dengan begitu kode yang muncul
    # pasti berasal dari kolom itu.
    kasus: list[tuple[str, dict[str, str]]] = [
        ("WAJIB_KOSONG", ubah(nilai_angka="")),
        ("KODE_MAHASISWA_TIDAK_BERPOLA", ubah(kode_mahasiswa="12345")),
        ("PROGRAM_STUDI_TIDAK_BAKU", ubah(program_studi="sains data")),
        ("SEMESTER_TIDAK_SAH", ubah(semester="2")),
        ("KODE_MK_TIDAK_TERDAFTAR", ubah(kode_mk="SSD9999")),
        ("NILAI_BUKAN_BILANGAN", ubah(nilai_angka="N/A")),
        ("NILAI_DI_LUAR_RENTANG", ubah(nilai_angka="105")),
        ("KEHADIRAN_BUKAN_BILANGAN", ubah(persentase_kehadiran="tinggi")),
        ("KEHADIRAN_DI_LUAR_RENTANG", ubah(persentase_kehadiran="118")),
        ("STATUS_KELULUSAN_TIDAK_SAH", ubah(status_kelulusan="LULUS")),
        (
            "KELULUSAN_TIDAK_KONSISTEN",
            ubah(nilai_angka="41", persentase_kehadiran="52"),
        ),
        ("STATUS_PENDAMPINGAN_TIDAK_SAH", ubah(status_pendampingan="belum diketahui")),
        ("WAKTU_TIDAK_SAH", ubah(waktu_pembaruan="01/08/2026 09:15")),
    ]

    # Tiga syarat per kasus: (1) tidak ada kode di luar katalog ATURAN; (2) kode yang
    # diharapkan muncul; (3) hanya SATU kode yang muncul, tidak berlebih.
    for kode, baris in kasus:
        temuan = aturan.periksa_baris(baris, kode_mk_sah)
        asing = [satu for satu in temuan if satu not in aturan.ATURAN]
        harus(not asing, f"kode di luar katalog ATURAN dikembalikan: {asing}")
        harus(
            kode in temuan,
            f"aturan {kode} tidak terdeteksi. Baris ujinya hanya berbeda pada satu "
            "kolom dari baris yang sah",
        )
        harus(
            len(temuan) == 1,
            f"baris uji {kode} menghasilkan {len(temuan)} kode sekaligus: {temuan}. "
            "Setiap baris uji dirancang melanggar tepat satu aturan; periksa kembali "
            "butir 1 dan 2 pada docstring periksa_baris()",
        )
    lapor("ketiga belas aturan terdeteksi satu per satu", f"{len(kasus)} kasus")
    temuan = aturan.periksa_baris(ubah(nilai_angka="", status_pendampingan="asing"), kode_mk_sah)
    harus(set(temuan) == {"WAJIB_KOSONG", "STATUS_PENDAMPINGAN_TIDAK_SAH"} and len(temuan) == 2,
          "kolom kosong tidak boleh menghentikan pemeriksaan kolom lain yang terisi")
    temuan = aturan.periksa_baris(ubah(nilai_angka="", kode_mahasiswa=""), kode_mk_sah)
    harus(temuan == ["WAJIB_KOSONG"], "beberapa kolom kosong cukup satu WAJIB_KOSONG")
    lapor("kolom kosong dan cacat lain diperiksa terpisah", "ya")

    harus(
        len(aturan.ATURAN) == len(kasus),
        f"katalog ATURAN memuat {len(aturan.ATURAN)} kode, tetapi hanya {len(kasus)} "
        "yang diuji. Katalog tidak boleh diubah",
    )


# ---------------------------------------------------------------------
# 3. Duplikat antarbaris — TODO 3
# ---------------------------------------------------------------------


def periksa_duplikat() -> None:
    bagian("3. Duplikat yang hanya terlihat antarbaris (TODO 3)")

    harus(
        validasi.cari_duplikat([dict(BARIS_SAH)]) == {},
        "satu baris tunggal tidak mungkin menduplikasi apa pun",
    )

    # Urutan sengaja dibalik: yang ber-record_id lebih besar diletakkan lebih
    # dahulu. Jawaban yang memakai urutan kemunculan berkas akan menahan baris
    # yang salah, dan pemeriksaan ini menangkapnya.
    # Dua baris dengan kunci alami yang sama (mahasiswa, mata kuliah, semester) tetapi
    # record_id berbeda. Yang dipertahankan harus yang record_id-nya terkecil (R00026,
    # indeks 1); yang ditandai sebagai duplikat adalah indeks 0. Hasil cari_duplikat
    # berupa kamus {indeks baris: [kode temuan]}.
    berebut = [
        ubah(record_id="X00099", nilai_angka="75"),
        ubah(record_id="R00026", nilai_angka="70"),
    ]
    temuan = validasi.cari_duplikat(berebut)
    harus(
        set(temuan) == {0},
        "ketika dua baris berebut kunci alami yang sama, yang dipertahankan adalah "
        f"record_id terkecil (R00026), bukan yang lebih dahulu muncul. Hasil: {temuan}",
    )
    harus(
        temuan[0] == ["KUNCI_ALAMI_GANDA"],
        f"kode yang diharapkan hanya KUNCI_ALAMI_GANDA, bukan {temuan[0]}",
    )
    lapor("urutan pemeriksaan ditentukan record_id", "ya")

    # Dua baris yang persis sama: melanggar record_id ganda DAN kunci alami ganda
    # sekaligus, dan keduanya harus dilaporkan (diurutkan agar perbandingan stabil).
    kembar = [dict(BARIS_SAH), dict(BARIS_SAH)]
    temuan = validasi.cari_duplikat(kembar)
    harus(len(temuan) == 1, f"dua baris kembar harus menyisakan satu, bukan {temuan}")
    kode = sorted(next(iter(temuan.values())))
    harus(
        kode == ["KUNCI_ALAMI_GANDA", "RECORD_ID_GANDA"],
        "baris yang menduplikasi record_id sekaligus kunci alami harus melaporkan "
        f"kedua kodenya, bukan {kode}",
    )
    lapor("dua pelanggaran sekaligus dilaporkan keduanya", "ya")


# ---------------------------------------------------------------------
# 4. Penyensoran rahasia pada log — TODO 4
# ---------------------------------------------------------------------


def periksa_penyensoran() -> None:
    bagian("4. Penyensoran rahasia pada log (TODO 4)")

    harus(pencatatan.bersihkan(None) is None, "None harus dikembalikan apa adanya")

    # Pesan galat koneksi yang memuat kata sandi. Nilainya harus hilang, tetapi kata
    # "password" harus tetap ada supaya pembaca log tahu ada yang disensor.
    hasil = pencatatan.bersihkan("connect gagal user=operator_pipeline password=rahasia123")
    harus("rahasia123" not in hasil, f"kata sandi masih terbaca pada log: {hasil}")
    harus(
        "password" in hasil,
        "nama kunci harus tetap terbaca supaya pembaca log tahu ada yang disensor, "
        f"bukan mengira tidak ada apa-apa: {hasil}",
    )
    lapor("kata sandi pada pesan galat disensor", "ya")

    # Runtutan acak panjang tanpa kata "password" di depannya: bentuk token.
    panjang = "kunci: 8Xy2Qw7ZpL4nR6vT1sK3mB9dF0gH5jC8aE2uY7iO1pQ"
    harus(
        "8Xy2Qw7ZpL4nR6vT1sK3mB9dF0gH5jC8aE2uY7iO1pQ" not in pencatatan.bersihkan(panjang),
        "runtutan panjang yang menyerupai token harus disensor",
    )
    lapor("token panjang disensor", "ya")

    # Kata sandi asli dari .env (bila sudah diisi) dimasukkan ke pesan lalu harus
    # tersensor. Bila .env belum diisi, bagian ini dilewati, bukan dianggap gagal.
    try:
        rahasia = konfigurasi.kata_sandi_basis_data()
    except konfigurasi.KonfigurasiTidakLengkap:
        lapor("kata sandi .env dicocokkan langsung", "dilewati, .env belum diisi")
    else:
        pesan = f"koneksi ditolak, nilai yang dipakai {rahasia}"
        harus(
            rahasia not in pencatatan.bersihkan(pesan),
            "kata sandi yang memang diketahui proses ini harus dicocokkan langsung, "
            "karena kata sandi pendek tidak tertangkap pola panjang",
        )
        lapor("kata sandi .env dicocokkan langsung", "ya")

    # Penyensoran yang berlebihan sama merugikannya. Nama berkas dan ringkasan
    # yang dipotong adalah keterangan yang justru dicari auditor.
    for aman in ("ringkasan-4449a9154d22.csv", "sha256=329eba7e1ec71dfa", "batch=4449a9154d22"):
        harus(
            pencatatan.bersihkan(aman) == aman,
            f"keterangan yang bukan rahasia ikut tersensor: {aman} menjadi "
            f"{pencatatan.bersihkan(aman)}",
        )
    lapor("nama berkas dan penanda batch tidak ikut disensor", "ya")


# ---------------------------------------------------------------------
# 5. Pemuatan yang gagal dengan aman — TODO 5
# ---------------------------------------------------------------------


# Koneksi dan kursor TIRUAN. _Kursor.executemany tidak menyentuh basis data; ia hanya
# menghitung berapa kali dipanggil dan, bila diminta, melempar galat pada panggilan
# ke-N untuk meniru koneksi yang putus di tengah pemuatan. _Sambungan mencatat apakah
# autocommit dimatikan, berapa kali commit dan rollback dipanggil, dan apakah kursor
# ditutup. Tanda garis bawah di depan nama berarti "alat internal pemeriksa".
class _Kursor:
    def __init__(self, induk: "_Sambungan") -> None:
        self.induk = induk
        self.rowcount = 0

    def executemany(self, perintah: str, potongan: list) -> None:
        harus(
            perintah == muat.basis_data.PERINTAH_SISIP,
            "gunakan PERINTAH_SISIP yang tersedia dan parameter terpisah",
        )
        harus(
            all(isinstance(satu, tuple) and len(satu) == len(muat.basis_data.KOLOM_STAGING)
                for satu in potongan),
            "setiap baris harus disusun dengan _sebagai_tupel() menjadi parameter",
        )
        self.induk.panggilan += 1
        if self.induk.gagal_pada == self.induk.panggilan:
            raise RuntimeError("koneksi terputus di tengah batch")
        self.rowcount = min(len(potongan), self.induk.batas_rowcount or len(potongan))
        self.induk.tersisip += len(potongan)
        self.induk.menunggu += self.rowcount

    def close(self) -> None:
        self.induk.kursor_ditutup = True


class _Sambungan:
    """Koneksi tiruan yang mencatat perlakuan transaksi terhadapnya."""

    def __init__(self, gagal_pada: int | None = None, batas_rowcount: int | None = None) -> None:
        self.gagal_pada = gagal_pada
        self.batas_rowcount = batas_rowcount
        self.autocommit: object = "belum diatur"
        self.panggilan = self.tersisip = 0
        self.commit_dipanggil = self.rollback_dipanggil = 0
        self.kursor_ditutup = False
        self.menunggu = self.permanen = 0
        self.commit_setelah: list[int] = []

    def cursor(self):
        return _Kursor(self)

    def commit(self) -> None:
        self.commit_dipanggil += 1
        self.commit_setelah.append(self.panggilan)
        self.permanen += self.menunggu
        self.menunggu = 0

    def rollback(self) -> None:
        self.rollback_dipanggil += 1
        self.menunggu = 0


def periksa_pemuatan() -> None:
    bagian("5. Pemuatan yang gagal dengan aman (TODO 5)")

    # 500 baris sah, dimuat dalam potongan 200 (jadi tiga potongan: 200, 200, 100).
    baris = [ubah(record_id=f"R{nomor:05d}") for nomor in range(500)]

    # Jalan berhasil: autocommit dimatikan, commit tepat SEKALI di akhir.
    sambungan = _Sambungan()
    jumlah = muat.muat_batch(sambungan, baris, "uji", ukuran_batch=200)
    harus(
        sambungan.autocommit is False,
        "autocommit harus dimatikan; tanpa itu setiap potongan langsung permanen "
        f"dan tidak ada yang dapat dibatalkan (nilai sekarang: {sambungan.autocommit!r})",
    )
    harus(
        sambungan.commit_dipanggil == 1,
        f"commit harus dipanggil tepat sekali, bukan {sambungan.commit_dipanggil} kali. "
        "Commit per potongan membuat batch yang gagal menyisakan separuh data",
    )
    harus(jumlah == 500, f"jumlah baris yang dikembalikan salah: {jumlah}, seharusnya 500")
    harus(sambungan.commit_setelah == [3], "commit harus setelah seluruh potongan berhasil")
    harus(sambungan.permanen == 500 and sambungan.menunggu == 0,
          "model transaksi harus menyimpan seluruh batch, bukan sebagian")
    harus(sambungan.kursor_ditutup, "kursor harus ditutup pada jalan berhasil")
    lapor("jalan berhasil: satu transaksi, satu commit", f"{jumlah} baris")
    lapor("commit setelah seluruh potongan dan kursor ditutup", "ya")

    # Jalan gagal: koneksi tiruan melempar galat pada setiap posisi potongan.
    # galat diteruskan ke pemanggil, rollback dipanggil, commit tidak pernah dipanggil,
    # dan kursor tetap ditutup (inilah gunanya blok finally pada muat_batch).
    for gagal_pada in (1, 2, 3):
        sambungan = _Sambungan(gagal_pada=gagal_pada)
        try:
            muat.muat_batch(sambungan, baris, "uji", ukuran_batch=200)
        except RuntimeError:
            pass
        else:
            raise Gagal("kegagalan pemuatan ditelan; rollback lalu teruskan dengan raise")
        harus(sambungan.rollback_dipanggil >= 1, "rollback tidak dipanggil saat gagal")
        harus(sambungan.commit_dipanggil == 0, "commit tetap dipanggil saat gagal")
        harus(sambungan.kursor_ditutup, "kursor harus ditutup, baik berhasil maupun gagal")
        harus(sambungan.menunggu == 0 and sambungan.permanen == 0,
              "model transaksi menyisakan baris setelah gagal")
        lapor(f"gagal di potongan {gagal_pada}: galat diteruskan", "rollback, 0 baris pada model")

    sambungan = _Sambungan(batas_rowcount=100)
    jumlah = muat.muat_batch(sambungan, baris, "uji", ukuran_batch=200)
    harus(jumlah == 300, "jumlah harus dijumlahkan dari rowcount, bukan panjang masukan")
    lapor("jumlah dikembalikan mengikuti rowcount", "ya")


# ---------------------------------------------------------------------
# 6. Hasil akhir, reproduksibilitas, dan rahasia pada kode
# ---------------------------------------------------------------------


def periksa_hasil_akhir() -> None:
    bagian("6. Hasil akhir, reproduksibilitas, dan rahasia pada kode")

    # Berkas mentah tidak boleh berubah: ringkasannya harus tetap sama dengan manifest.
    sebelum = keutuhan.hitung_sha256(konfigurasi.BERKAS_MASUKAN)
    tercatat = keutuhan.baca_manifest().get(
        keutuhan.kunci_manifest(konfigurasi.BERKAS_MASUKAN)
    )
    harus(
        sebelum == tercatat,
        "berkas mentah sudah berubah. Pipeline memperbaiki data di berkas keluaran, "
        "bukan di berkas masukan. Pulihkan dengan: python tools/buat_dataset.py",
    )
    lapor("berkas mentah tidak diubah", "ya")

    # Keluaran layar pipeline ditahan supaya laporan pemeriksa tetap terbaca.
    # Yang dinilai di sini hasil berkasnya, bukan tampilannya.
    # Pipeline dijalankan DUA KALI pada masukan yang sama. Hasil yang baik tidak
    # bergantung pada kebetulan, sehingga ringkasan kedua berkas keluaran harus sama
    # (reproduksibilitas). Kode keluar 0 berarti pipeline selesai tanpa galat.
    with redirect_stdout(io.StringIO()):
        kode_pertama = validasi.jalankan()
        pertama = keutuhan.hitung_sha256(konfigurasi.BERKAS_KELUARAN)
        kode_kedua = validasi.jalankan()
        kedua = keutuhan.hitung_sha256(konfigurasi.BERKAS_KELUARAN)

    harus(kode_pertama == 0, "python -m pipeline.validasi berakhir dengan galat")
    harus(kode_kedua == 0, "jalan kedua berakhir dengan galat")
    harus(
        pertama == kedua,
        "dua kali menjalankan pipeline pada masukan yang sama menghasilkan berkas "
        "yang berbeda. Urutan keluaran harus ditentukan isi data, bukan urutan "
        "baris pada berkas masukan",
    )
    lapor("dua kali dijalankan, hasilnya sama", pertama[:16] + "...")

    # Berkas pembanding adalah hasil yang benar, disiapkan dosen. Ringkasan yang sama
    # berarti keluaran Anda sama persis, byte demi byte.
    pembanding = keutuhan.hitung_sha256(konfigurasi.BERKAS_PEMBANDING)
    harus(
        pertama == pembanding,
        "hasil pipeline belum sama dengan berkas pembanding "
        f"{konfigurasi.BERKAS_PEMBANDING.name}. Bandingkan sebaran alasan penolakan "
        "dengan tabel jumlah pada docstring aturan.periksa_baris()",
    )
    lapor("hasil sama dengan berkas pembanding", "ya")

    # Nama manifest = nama berkas keluaran ditambah ".sha256".
    berkas_manifest = konfigurasi.BERKAS_KELUARAN.with_suffix(
        konfigurasi.BERKAS_KELUARAN.suffix + ".sha256"
    )
    harus(
        berkas_manifest.exists(),
        f"manifest keluaran {berkas_manifest.name} tidak ditulis; tanpa berkas itu "
        "asal-usul hasil pipeline tidak dapat dibuktikan",
    )
    lapor("manifest keluaran tertulis", berkas_manifest.name)

    # Satu-satunya pemeriksaan yang membaca isi kode Anda.
    try:
        rahasia = konfigurasi.kata_sandi_basis_data()
    except konfigurasi.KonfigurasiTidakLengkap:
        rahasia = ""
    if rahasia:
        for berkas in sorted((PROYEK / "pipeline").glob("*.py")):
            harus(
                rahasia not in berkas.read_text(encoding="utf-8"),
                f"kata sandi tertulis di dalam {berkas.name}. Kata sandi yang pernah "
                "tertulis di luar .env dianggap bocor dan wajib diganti, bukan sekadar "
                "dihapus barisnya",
            )
        lapor("tidak ada kata sandi di dalam kode", "ya")
    else:
        lapor("tidak ada kata sandi di dalam kode", "dilewati, .env belum diisi")


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
    print("PEMERIKSAAN HASIL PERTEMUAN 10")
    print(f"Folder proyek: {PROYEK}")

    # Urutan except di bawah: Gagal = perilaku pipeline salah (milik pemeriksa);
    # NotImplementedError = fungsi TODO masih berisi raise NotImplementedError;
    # Exception = galat Python lain di kode Anda (lihat laporkan_galat_praktikum).
    # kode_mk_sah = himpunan kode mata kuliah yang sah, dibaca dari berkas referensi.
    try:
        kode_mk_sah = aturan.muat_kode_mk_sah()
        periksa_gerbang(kode_mk_sah)
        periksa_aturan(kode_mk_sah)
        periksa_duplikat()
        periksa_penyensoran()
        periksa_pemuatan()
        periksa_hasil_akhir()
    except Gagal as galat:
        print(f"\nGAGAL: {galat}")
        raise SystemExit(1)
    except NotImplementedError as galat:
        print(f"\nBELUM SELESAI: {galat}")
        raise SystemExit(1)
    except Exception as galat:
        laporkan_galat_praktikum(galat)
        raise SystemExit(1)

    print("\nPIPELINE PERTEMUAN 10 LOLOS PEMERIKSAAN")


# Baris ini menjalankan main() hanya bila berkas dijalankan langsung
# (python starter/periksa_hasil_p10.py), bukan bila diimpor oleh berkas lain.
if __name__ == "__main__":
    main()
