"""Starter API Secure Academic Data Pipeline.

Mata Kuliah Keamanan Data (SSD1033) — dipakai pada Pertemuan 9 dan 11.

Menjalankan, dari folder proyek:

    uvicorn api.main:app --reload --port 8000

Lalu buka http://127.0.0.1:8000/docs untuk Swagger UI.

------------------------------------------------------------------------
PERINGATAN

Berkas ini sengaja memuat lima kelemahan, sehingga BUKAN contoh API yang aman
dan tidak boleh dipakai sebagai pola untuk pekerjaan lain sebelum kelima
TODO diselesaikan.

    TODO 1  otorisasi tingkat objek        -> api/keamanan.py
    TODO 2  validasi masukan               -> berkas ini, endpoint /nilai
    TODO 3  penanganan galat               -> berkas ini, bagian handler
    TODO 4  pencatatan penolakan           -> berkas ini, endpoint /nilai/{kode}
    TODO 5  penyensoran sel kecil          -> berkas ini, endpoint /ringkasan

Kerjakan berurutan. TODO 4 baru dapat diuji setelah TODO 1 selesai, karena
sebelum itu tidak ada permintaan yang pernah ditolak.

Buktikan setiap kelemahan lebih dahulu melalui Swagger UI, catat buktinya
pada worksheet, baru perbaiki. Perbaikan tanpa bukti tidak dinilai:
yang dilatih pada pertemuan ini adalah kemampuan melihat, bukan kemampuan
menambal.
------------------------------------------------------------------------
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from . import basis_data, keamanan, konfigurasi, pencatatan, skema

app = FastAPI(
    title="Starter API — Secure Academic Data Pipeline",
    description=(
        "Starter praktikum Mata Kuliah Keamanan Data (SSD1033). "
        "Seluruh data adalah data sintetik. "
        "Layanan ini hanya membaca dua view melalui akun `app_service`."
    ),
    version="0.9.0",
)


# ---------------------------------------------------------------------
# Korelasi permintaan
#
# Setiap permintaan diberi satu pengenal yang dipakai di berkas log, di
# tabel log, dan pada respons galat. Bagian ini sudah jadi.
# ---------------------------------------------------------------------


@app.middleware("http")
async def beri_korelasi(request: Request, call_next):
    request.state.korelasi_id = pencatatan.korelasi_baru()
    respons = await call_next(request)
    respons.headers["X-Korelasi-Id"] = request.state.korelasi_id
    return respons


def korelasi(request: Request) -> str:
    return getattr(request.state, "korelasi_id", "tanpa-korelasi")


# ---------------------------------------------------------------------
# Identitas pemanggil
#
# Bagian ini sudah jadi, dan sengaja dipakai sebagai contoh untuk TODO 4:
# perhatikan bahwa penolakan di sini dicatat SEBELUM galat dilempar.
# ---------------------------------------------------------------------


def pemanggil(
    request: Request,
    x_api_key: str | None = Header(default=None, alias=keamanan.NAMA_HEADER_KUNCI),
) -> keamanan.Identitas:
    """Kenali pemanggil dari header `X-API-Key`, atau tolak dengan 401."""
    try:
        return keamanan.identitas_dari_kunci(x_api_key)
    except keamanan.TidakDikenali as galat:
        pencatatan.catat(
            aktor="anonim",
            aksi="autentikasi",
            objek=request.url.path,
            hasil="ditolak",
            korelasi_id=korelasi(request),
            keterangan=str(galat),
        )
        raise HTTPException(
            status_code=401,
            detail="kunci API tidak sah atau tidak dikirim",
        ) from galat


# ---------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------


@app.get("/sehat", response_model=skema.Kesehatan, tags=["umum"])
def sehat() -> skema.Kesehatan:
    """Penanda bahwa layanan hidup. Tidak memerlukan kunci.

    Jawabannya sengaja tidak menyebutkan versi pustaka, nama host, maupun
    keadaan basis data. Endpoint yang terbuka untuk siapa saja tidak boleh
    menjadi sumber keterangan bagi orang yang sedang memetakan sistem.
    """
    return skema.Kesehatan(status="hidup", layanan="starter_api")


@app.get(
    "/nilai/{kode_mahasiswa}",
    response_model=list[skema.CatatanNilai],
    tags=["nilai"],
    summary="Catatan nilai satu mahasiswa",
)
def nilai_mahasiswa(
    kode_mahasiswa: str,
    request: Request,
    identitas: keamanan.Identitas = Depends(pemanggil),
) -> list[dict]:
    """Ambil seluruh catatan nilai milik satu mahasiswa.

    Di sinilah kelemahan utama Pertemuan 9 berada. Coba panggil endpoint ini
    dengan kunci mahasiswa, lalu ganti `kode_mahasiswa` pada URL dengan kode
    milik mahasiswa lain. Amati apa yang Anda terima.
    """
    baris = basis_data.nilai_satu_mahasiswa(kode_mahasiswa)
    program_studi = baris[0]["program_studi"] if baris else None

    if not keamanan.boleh_membaca_mahasiswa(identitas, kode_mahasiswa, program_studi):
        # =============================================================
        # TODO 4 — Catat penolakan
        #
        # Permintaan yang ditolak justru yang paling perlu dicatat.
        # Permintaan yang berhasil menceritakan pemakaian biasa; permintaan
        # yang ditolak menceritakan percobaan. Seseorang yang mencoba
        # tiga puluh kode mahasiswa berbeda dalam satu menit hanya terlihat
        # bila penolakan ikut tercatat.
        #
        # Tambahkan satu panggilan `pencatatan.catat(...)` di sini sebelum
        # baris `raise` di bawah. Contoh lengkapnya ada pada fungsi
        # `pemanggil()` di atas. Isi yang diharapkan:
        #
        #     aktor        identitas.nama
        #     aksi         "baca_nilai"
        #     objek        kode_mahasiswa
        #     hasil        "ditolak"
        #     korelasi_id  korelasi(request)
        #     keterangan   sebutkan peran pemanggil, bukan isi datanya
        #
        # Pertanyaan yang harus Anda jawab pada worksheet bagian G:
        # mengapa `objek` boleh berisi kode mahasiswa, sedangkan
        # `keterangan` tidak boleh berisi nilainya?
        # =============================================================
        raise HTTPException(
            status_code=403,
            detail="tidak berhak membaca catatan mahasiswa ini",
        )

    pencatatan.catat(
        aktor=identitas.nama,
        aksi="baca_nilai",
        objek=kode_mahasiswa,
        hasil="berhasil",
        korelasi_id=korelasi(request),
        keterangan=f"{len(baris)} catatan",
    )
    return baris


@app.get(
    "/nilai",
    response_model=list[skema.CatatanNilai],
    tags=["nilai"],
    summary="Pencarian catatan nilai",
)

def cari_nilai(
    request: Request,
    identitas: keamanan.Identitas = Depends(pemanggil),
    program_studi: str | None = None,
    semester: int | None = Query(default=None, ge=1, le=14),
    kode_mk: str | None = Query(default=None, max_length=12),
    urut: str = "kode_mahasiswa",
    arah: str = "ASC",
    batas: int = Query(
        default=20,
        ge=1,
        le=konfigurasi.BATAS_BARIS_MAKS
    ),
) -> list[dict]:

    if not keamanan.boleh_mencari_nilai(identitas):
        raise HTTPException(
            status_code=403,
            detail="tidak berhak mencari data nilai"
        )

    if urut not in basis_data.KOLOM_URUT_DIIZINKAN:
        raise HTTPException(
            status_code=400,
            detail="kolom pengurutan tidak diizinkan"
        )

    arah = arah.upper()

    if arah not in basis_data.ARAH_URUT_DIIZINKAN:
        raise HTTPException(
            status_code=400,
            detail="arah pengurutan tidak diizinkan"
        )

    baris = basis_data.cari_nilai(
        program_studi=program_studi,
        semester=semester,
        kode_mk=kode_mk,
        urut=urut,
        arah=arah,
        batas=batas,
    )

    pencatatan.catat(
        aktor=identitas.nama,
        aksi="cari_nilai",
        objek="v_nilai_mahasiswa",
        hasil="berhasil",
        korelasi_id=korelasi(request),
        keterangan=f"{len(baris)} baris",
    )

    return baris


@app.get(
    "/ringkasan",
    response_model=list[skema.RingkasanKelulusan],
    tags=["laporan"],
    summary="Laporan agregat kelulusan",
)
def ringkasan(
    request: Request,
    identitas: keamanan.Identitas = Depends(pemanggil),
    program_studi: str | None = None,
    semester: int | None = None,
) -> list[dict]:
    """Laporan agregat per program studi, semester, dan mata kuliah.

    =================================================================
    TODO 5 — Sel kecil pada laporan agregat

    Panggil endpoint ini tanpa penyaring, lalu urutkan hasilnya menurut
    `jumlah_record` dari yang terkecil. Anda akan menemukan sel yang
    berisi satu record. Untuk sel semacam itu, `jumlah_lulus` tidak lagi
    berbicara tentang kelompok; ia berbicara tentang satu orang yang
    dapat ditunjuk melalui program studi, semester, dan mata kuliah.

    Ini persoalan Pertemuan 6 yang muncul kembali di tempat baru.
    Agregasi tidak dengan sendirinya membuat data menjadi anonim.

    Yang harus berlaku setelah perbaikan, untuk setiap sel yang
    `jumlah_record`-nya kurang dari `konfigurasi.AMBANG_SEL_KECIL`:

        jumlah_lulus    = None
        rata_nilai      = None
        rata_kehadiran  = None
        disensor        = True

    `jumlah_record` tetap ditampilkan, dan sel tetap muncul di daftar.
    Menghilangkan selnya diam-diam membuat laporan tampak lengkap
    padahal ada yang ditahan, dan pembaca tidak punya cara mengetahuinya.

    Ambang di sini hanya menerapkan penekanan primer. Pertemuan 6 sudah
    menunjukkan bahwa penekanan primer saja dapat dibatalkan lewat
    pengurangan bila totalnya ikut diterbitkan. Worksheet bagian H
    menanyakan apakah laporan ini punya celah yang sama.
    =================================================================
    """
    if not keamanan.boleh_membaca_ringkasan(identitas):
        pencatatan.catat(
            aktor=identitas.nama,
            aksi="baca_ringkasan",
            objek="v_ringkasan_kelulusan",
            hasil="ditolak",
            korelasi_id=korelasi(request),
            keterangan=f"peran {identitas.peran}",
        )
        raise HTTPException(status_code=403, detail="tidak berhak membaca laporan ini")

    
    baris = basis_data.ringkasan_kelulusan(program_studi, semester)

    # Penyensoran sel kecil
    for sel in baris:
        if sel["jumlah_record"] < konfigurasi.AMBANG_SEL_KECIL:
            sel["jumlah_lulus"] = None
            sel["rata_nilai"] = None
            sel["rata_kehadiran"] = None
            sel["disensor"] = True
        else:
            sel["disensor"] = False

    pencatatan.catat(
        aktor=identitas.nama,
        aksi="baca_ringkasan",
        objek="v_ringkasan_kelulusan",
        hasil="berhasil",
        korelasi_id=korelasi(request),
        keterangan=f"{len(baris)} sel",
    )
    return baris



# ---------------------------------------------------------------------
# Penanganan galat
# ---------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def galat_http(request: Request, exc: HTTPException) -> JSONResponse:
    """Galat yang memang disengaja: 401, 403, 404.

    Bagian ini sudah jadi. Pesannya singkat dan tidak menyebutkan apa pun
    tentang keadaan internal. Perhatikan bahwa 403 pada `/nilai/{kode}`
    tidak menyebutkan apakah kode mahasiswa itu ada atau tidak; kalau
    disebutkan, endpoint ini berubah menjadi alat untuk menguji keberadaan
    seseorang di dalam basis data.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=skema.Galat(
            pesan=str(exc.detail),
            korelasi_id=korelasi(request),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def galat_tak_terduga(request: Request, exc: Exception) -> JSONResponse:
    """Galat yang tidak disengaja.

    =================================================================
    TODO 3 — Jangan bocorkan detail internal

    Sekarang badan respons memuat jenis pengecualian dan pesannya apa
    adanya. Buktikan akibatnya: panggil `/nilai?urut=nama_mk` dan baca
    apa yang Anda terima. Anda akan mendapat nama kolom, dan pada galat
    lain Anda akan mendapat nama pustaka, nama basis data, bahkan
    potongan query.

    Perbaiki menjadi:

        1. status 500;
        2. badan respons berbentuk `skema.Galat`, dengan pesan umum
           yang sama untuk semua galat tak terduga, misalnya
           "terjadi kesalahan pada layanan";
        3. `korelasi_id` disertakan supaya pengguna dapat melaporkannya;
        4. detail lengkapnya dicatat melalui `pencatatan.catat(...)`
           dengan hasil "gagal" — masuk ke log, bukan ke respons.

    Butir keempat yang membuat tiga butir pertama dapat diterima.
    Menyembunyikan detail dari pengguna tanpa menyimpannya di suatu
    tempat bukan keamanan, melainkan kehilangan informasi.
    =================================================================
    """
    return JSONResponse(
        status_code=500,
        content={
            "pesan": f"{type(exc).__name__}: {exc}",
            "korelasi_id": korelasi(request),
        },
    )
