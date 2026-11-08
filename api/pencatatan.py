"""Pencatatan keamanan starter API.

Berkas ini sudah jadi dan tidak perlu diubah pada Pertemuan 9. Bacalah tetap:
worksheet bagian G menanyakan isinya, dan bagian yang paling penting justru
bukan kode yang menulis log, melainkan kode yang menahan sesuatu agar tidak
ikut tertulis.

Setiap kejadian dicatat ke dua tempat sekaligus:

    1. berkas `logs/api.log`, satu baris JSON per kejadian, dapat dibaca
       tanpa basis data ketika layanan sedang bermasalah;
    2. tabel `log_aktivitas`, tempat auditor membacanya.

Keduanya sengaja dipertahankan. Berkas log tetap terisi ketika basis data
tidak dapat dihubungi — dan justru saat itulah catatan paling dibutuhkan.

Yang dicatat: aktor, aksi, objek, hasil, waktu, dan `korelasi_id`.
Yang tidak pernah dicatat: kunci API, kata sandi, dan isi baris data pribadi.
Nilai seorang mahasiswa tidak perlu masuk ke log; yang perlu diketahui auditor
adalah bahwa catatan milik mahasiswa itu dibaca, oleh siapa, dan kapan.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

from . import basis_data, konfigurasi, keamanan

BERKAS_LOG = konfigurasi.LOG_DIR / "api.log"

# Panjang kolom `keterangan` pada tabel log_aktivitas. Teks yang lebih panjang
# dipotong di sini, bukan dibiarkan ditolak MySQL: kegagalan menulis log tidak
# boleh menjatuhkan permintaan yang sebenarnya berhasil.
PANJANG_KETERANGAN_MAKS = 255

# Runtutan panjang tanpa spasi menyerupai token atau kunci. Pola ini menjaring
# rahasia yang belum terdaftar pada .env, misalnya kunci yang tidak sengaja
# tertempel ke dalam sebuah parameter.
POLA_MIRIP_TOKEN = re.compile(r"\b[A-Za-z0-9_\-]{20,}\b")

PENGGANTI = "[RAHASIA]"


def korelasi_baru() -> str:
    """Pengenal singkat yang menyatukan satu permintaan di semua tempat.

    Nilai yang sama muncul pada berkas log, pada tabel log, dan pada respons
    galat yang diterima pengguna. Dengan begitu pengguna dapat melaporkan
    "permintaan saya gagal, korelasinya a1b2c3d4" tanpa layanan perlu
    membocorkan apa pun tentang kegagalan itu kepadanya.
    """
    return uuid.uuid4().hex[:12]


def bersihkan(teks: str | None) -> str | None:
    """Buang nilai rahasia dari teks yang akan dicatat.

    Dua lapis, dan urutannya penting. Nilai kunci yang memang dikonfigurasi
    diganti lebih dahulu; sisanya ditangkap pola umum. Lapis kedua saja tidak
    cukup karena kunci pendek lolos darinya, dan lapis pertama saja tidak cukup
    karena rahasia yang bocor sering bukan rahasia milik kita sendiri.
    """
    if teks is None:
        return None

    for nama_variabel in keamanan.PENGGUNA:
        nilai = konfigurasi.ambil(nama_variabel, "")
        if nilai:
            teks = teks.replace(nilai, PENGGANTI)

    teks = POLA_MIRIP_TOKEN.sub(PENGGANTI, teks)

    if len(teks) > PANJANG_KETERANGAN_MAKS:
        teks = teks[: PANJANG_KETERANGAN_MAKS - 3] + "..."
    return teks


def catat(
    aktor: str,
    aksi: str,
    objek: str | None,
    hasil: str,
    korelasi_id: str,
    keterangan: str | None = None,
) -> None:
    """Catat satu kejadian ke berkas dan ke tabel.

    `hasil` mengikuti tabel `log_aktivitas`: 'berhasil', 'ditolak', atau 'gagal'.
    Bedakan ketiganya dengan cermat. 'ditolak' berarti kontrol keamanan bekerja
    sebagaimana mestinya; 'gagal' berarti ada yang rusak. Menyamakan keduanya
    membuat serangan yang tertahan tampak seperti gangguan teknis biasa.
    """
    keterangan = bersihkan(keterangan)

    kejadian = {
        "waktu": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "komponen": "starter_api",
        "aktor": aktor,
        "aksi": aksi,
        "objek": objek,
        "hasil": hasil,
        "korelasi_id": korelasi_id,
        "keterangan": keterangan,
    }

    try:
        konfigurasi.LOG_DIR.mkdir(parents=True, exist_ok=True)
        with BERKAS_LOG.open("a", encoding="utf-8") as berkas:
            berkas.write(json.dumps(kejadian, ensure_ascii=False) + "\n")
    except OSError:
        # Berkas log tidak dapat ditulis. Permintaan tetap dilayani; kegagalan
        # mencatat bukan alasan untuk menjatuhkan layanan.
        pass

    try:
        basis_data.tulis_log(
            aktor=aktor,
            aksi=aksi,
            objek=objek,
            hasil=hasil,
            korelasi_id=korelasi_id,
            keterangan=keterangan,
        )
    except Exception:
        # Sama seperti di atas. Jejaknya tetap ada pada berkas log, dan
        # selisih antara kedua tempat itu justru sinyal yang berguna
        # bagi auditor.
        pass
