
"""Starter API Secure Academic Data Pipeline.

Mata Kuliah Keamanan Data (SSD1033) — dipakai pada Pertemuan 9 dan 11.

Menjalankan, dari folder proyek:

    uvicorn api.main:app --reload --port 8000

Lalu buka http://127.0.0.1:8000/docs untuk Swagger UI.
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
# ---------------------------------------------------------------------

def pemanggil(
    request: Request,
    x_api_key: str | None = Header(
        default=None,
        alias=keamanan.NAMA_HEADER_KUNCI,
    ),
) -> keamanan.Identitas:
    """Kenali pemanggil dari header X-API-Key, atau tolak dengan 401."""
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
# Endpoint kesehatan
# ---------------------------------------------------------------------

@app.get("/sehat", response_model=skema.Kesehatan, tags=["umum"])
def sehat() -> skema.Kesehatan:
    """Penanda bahwa layanan hidup."""
    return skema.Kesehatan(
        status="hidup",
        layanan="starter_api",
    )


# ---------------------------------------------------------------------
# Endpoint nilai satu mahasiswa
# ---------------------------------------------------------------------

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

    baris = basis_data.nilai_satu_mahasiswa(kode_mahasiswa)
    program_studi = baris[0]["program_studi"] if baris else None

    if not keamanan.boleh_membaca_mahasiswa(
        identitas,
        kode_mahasiswa,
        program_studi,
    ):
        pencatatan.catat(
            aktor=identitas.nama,
            aksi="baca_nilai",
            objek=kode_mahasiswa,
            hasil="ditolak",
            korelasi_id=korelasi(request),
            keterangan=f"peran {identitas.peran}",
        )

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


# ---------------------------------------------------------------------
# Endpoint pencarian nilai
# ---------------------------------------------------------------------

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
        le=konfigurasi.BATAS_BARIS_MAKS,
    ),
) -> list[dict]:

    # Pemeriksaan hak akses pencarian.
    if not keamanan.boleh_mencari_nilai(identitas):
        pencatatan.catat(
            aktor=identitas.nama,
            aksi="cari_nilai",
            objek="v_nilai_mahasiswa",
            hasil="ditolak",
            korelasi_id=korelasi(request),
            keterangan=f"peran {identitas.peran}",
        )
        raise HTTPException(
            status_code=403,
            detail="tidak berhak mencari data nilai",
        )

    # Dosen wali hanya boleh mencari data program studinya sendiri.
    if identitas.peran == "dosen_wali":
        if (
            program_studi is not None
            and program_studi != identitas.program_studi
        ):
            pencatatan.catat(
                aktor=identitas.nama,
                aksi="cari_nilai",
                objek="v_nilai_mahasiswa",
                hasil="ditolak",
                korelasi_id=korelasi(request),
                keterangan="filter program studi di luar kewenangan",
            )
            raise HTTPException(
                status_code=403,
                detail="tidak berhak mencari data program studi tersebut",
            )

        # Batasi pencarian otomatis ke program studi dosen wali.
        program_studi = identitas.program_studi

    # Validasi kolom pengurutan.
    if urut not in basis_data.KOLOM_URUT_DIIZINKAN:
        raise HTTPException(
            status_code=400,
            detail="kolom pengurutan tidak diizinkan",
        )

    # Validasi arah pengurutan.
    arah = arah.upper()

    if arah not in basis_data.ARAH_URUT_DIIZINKAN:
        raise HTTPException(
            status_code=400,
            detail="arah pengurutan tidak diizinkan",
        )

    # Mengambil data sesuai filter.
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


# ---------------------------------------------------------------------
# Endpoint laporan agregat
# ---------------------------------------------------------------------

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

    if not keamanan.boleh_membaca_ringkasan(identitas):
        pencatatan.catat(
            aktor=identitas.nama,
            aksi="baca_ringkasan",
            objek="v_ringkasan_kelulusan",
            hasil="ditolak",
            korelasi_id=korelasi(request),
            keterangan=f"peran {identitas.peran}",
        )

        raise HTTPException(
            status_code=403,
            detail="tidak berhak membaca laporan ini",
        )

    baris = basis_data.ringkasan_kelulusan(
        program_studi,
        semester,
    )

    # Penyensoran sel kecil.
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
# Penanganan galat HTTP
# ---------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def galat_http(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:

    return JSONResponse(
        status_code=exc.status_code,
        content=skema.Galat(
            pesan=str(exc.detail),
            korelasi_id=korelasi(request),
        ).model_dump(),
    )


# ---------------------------------------------------------------------
# Penanganan galat tak terduga
# ---------------------------------------------------------------------

@app.exception_handler(Exception)
async def galat_tak_terduga(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Menyembunyikan detail internal dari pengguna dan mencatat galat."""

    pencatatan.catat(
        aktor="layanan",
        aksi=request.method.lower(),
        objek=request.url.path,
        hasil="gagal",
        korelasi_id=korelasi(request),
        keterangan=f"{type(exc).__name__}: {exc}",
    )

    return JSONResponse(
        status_code=500,
        content=skema.Galat(
            pesan="terjadi kesalahan pada layanan",
            korelasi_id=korelasi(request),
        ).model_dump(),
    )
