"""Bentuk data yang keluar dari starter API.

Berkas ini sudah jadi dan tidak perlu diubah pada Pertemuan 9.

Model di sini menentukan apa yang boleh keluar. Bila sebuah query kelak
mengembalikan kolom tambahan, kolom itu tidak akan ikut terkirim selama kolom itu
tidak disebut di sini. Perlindungan semacam itu bekerja tanpa diingat, dan
itulah nilainya: kebocoran data pada API biasanya bukan hasil keputusan,
melainkan hasil lupa.

Ada tiga lapis yang menahan `status_pendampingan` — atribut paling sensitif
pada proyek ini — agar tidak pernah sampai ke pemanggil:

    1. akun `app_service` tidak memiliki hak pada tabel dasar;
    2. view `v_nilai_mahasiswa` tidak menyertakan kolom itu;
    3. model di berkas ini tidak memiliki field untuk menampungnya.

Satu lapis sebenarnya cukup untuk hari ini. Tiga lapis diperlukan untuk hari
ketika salah satunya diubah orang lain yang tidak tahu alasannya.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CatatanNilai(BaseModel):
    """Satu catatan nilai tingkat record."""

    record_id: str
    kode_mahasiswa: str
    program_studi: str
    semester: int
    kode_mk: str
    nama_mk: str
    nilai_angka: int
    persentase_kehadiran: int
    status_kelulusan: str
    waktu_pembaruan: datetime


class RingkasanKelulusan(BaseModel):
    """Satu sel laporan agregat.

    Ketika sebuah sel terlalu kecil, ukurannya tetap ditampilkan tetapi
    angkanya ditahan. Pembaca perlu tahu bahwa sel itu ada dan mengapa
    isinya kosong; menghilangkannya diam-diam justru membuat laporan
    tampak lengkap padahal tidak.
    """

    program_studi: str
    semester: int
    kode_mk: str
    jumlah_record: int
    jumlah_lulus: int | None = None
    rata_nilai: float | None = None
    rata_kehadiran: float | None = None
    disensor: bool = Field(
        default=False,
        description="True bila angka ditahan karena jumlah record di bawah ambang.",
    )


class Galat(BaseModel):
    """Bentuk tunggal untuk seluruh respons galat.

    `pesan` ditujukan kepada pengguna dan tidak memuat detail internal.
    `korelasi_id` adalah satu-satunya jembatan ke catatan lengkap di sisi
    layanan. Pengguna melaporkan nilai itu; pengelola mencarinya di log.
    """

    pesan: str
    korelasi_id: str


class Kesehatan(BaseModel):
    """Jawaban endpoint `/sehat`.

    Sengaja miskin informasi. Endpoint kesehatan dapat dipanggil siapa saja
    tanpa kunci, sehingga jawabannya tidak boleh menyebutkan versi pustaka, nama
    host, jalur berkas, atau apakah basis data sedang bermasalah — semuanya
    berguna bagi penyerang dan tidak berguna bagi pemanggil yang sah.
    """

    status: str
    layanan: str
