-- =====================================================================
-- Secure Academic Data Pipeline - Pengujian Kontrol Akses
-- Mata Kuliah Keamanan Data (SSD1033)
--
-- Berkas ini berisi pengujian positif dan negatif untuk konfigurasi
-- pada roles.sql.
--
-- CARA MEMBACA HASIL
--
--   Pengujian positif  : akses yang diizinkan HARUS berhasil.
--   Pengujian negatif  : akses yang tidak diizinkan HARUS gagal.
--
-- Pada pengujian negatif, pesan galat adalah hasil yang benar. Pengujian
-- negatif yang berhasil dijalankan berarti kontrol TIDAK bekerja dan
-- harus dilaporkan sebagai temuan.
--
-- CARA MENJALANKAN
--
-- Setiap bagian dijalankan dengan akun yang berbeda. Tutup koneksi lalu
-- buka koneksi baru sebagai akun yang disebut pada judul bagian. Jangan
-- menjalankan seluruh berkas sekaligus dengan satu akun.
--
--   mysql -u app_service -p secure_academic_lab
--
-- Simpan keluaran yang sudah disanitasi sebagai bukti. Sanitasi berarti
-- menghapus nama host, nama komputer, dan jalur berkas pribadi.
-- =====================================================================


-- =====================================================================
-- BAGIAN A - Jalankan sebagai: app_service@localhost
-- Peran: identitas yang dipakai starter API.
-- =====================================================================

-- A-POS-01 Membaca data tingkat record melalui view yang diizinkan.
-- Diharapkan: 5 baris tampil.
SELECT record_id, kode_mahasiswa, kode_mk, nilai_angka, status_kelulusan
FROM v_nilai_mahasiswa
ORDER BY record_id
LIMIT 5;

-- A-POS-02 Membaca ringkasan agregat.
-- Diharapkan: beberapa baris ringkasan tampil.
SELECT program_studi, semester, kode_mk, jumlah_record, jumlah_lulus
FROM v_ringkasan_kelulusan
ORDER BY program_studi, semester
LIMIT 5;

-- A-POS-03 Menulis catatan aktivitas.
-- Diharapkan: 1 baris terpengaruh.
INSERT INTO log_aktivitas (aktor, komponen, aksi, objek, hasil, korelasi_id, keterangan)
VALUES ('app_service', 'starter_api', 'baca_nilai', 'v_nilai_mahasiswa', 'berhasil',
        'UJI-A-POS-03', 'pengujian positif kontrol akses');

-- A-NEG-01 Membaca tabel nilai secara langsung.
-- Diharapkan GAGAL: ERROR 1142 (SELECT command denied ... 'nilai_akademik').
SELECT * FROM nilai_akademik LIMIT 1;

-- A-NEG-02 Membaca tabel identitas.
-- Diharapkan GAGAL: ERROR 1142 (SELECT command denied ... 'mahasiswa').
SELECT * FROM mahasiswa LIMIT 1;

-- A-NEG-03 Membaca atribut paling sensitif melalui view yang diizinkan.
-- Diharapkan GAGAL: ERROR 1054 (Unknown column 'status_pendampingan').
-- Kolom tersebut tidak pernah disertakan dalam view, sehingga tidak ada
-- jalur apa pun dari starter API menuju atribut ini.
SELECT status_pendampingan FROM v_nilai_mahasiswa LIMIT 1;

-- A-NEG-04 Mengubah nilai akademik.
-- Diharapkan GAGAL: ERROR 1142 (UPDATE command denied).
UPDATE nilai_akademik SET nilai_angka = 100 WHERE record_id = 'R00001';

-- A-NEG-05 Membaca kembali log yang ditulisnya sendiri.
-- Diharapkan GAGAL: ERROR 1142 (SELECT command denied ... 'log_aktivitas').
-- Hak tulis pada log tidak otomatis memberi hak baca.
SELECT * FROM log_aktivitas LIMIT 1;

-- A-NEG-06 Mengubah struktur basis data.
-- Diharapkan GAGAL: ERROR 1142 (DROP command denied).
DROP TABLE staging_nilai;


-- =====================================================================
-- BAGIAN B - Jalankan sebagai: analyst@localhost
-- Peran: pembaca laporan agregat.
-- =====================================================================

-- B-POS-01 Membaca ringkasan kelulusan.
-- Diharapkan: beberapa baris tampil.
SELECT program_studi, semester, kode_mk, jumlah_record, rata_nilai
FROM v_ringkasan_kelulusan
ORDER BY rata_nilai DESC
LIMIT 5;

-- B-POS-02 Membaca ringkasan pendampingan.
-- Diharapkan: beberapa baris tampil.
--
-- Perhatikan kolom jumlah_mahasiswa pada setiap kelompok. Catat kelompok
-- yang jumlahnya paling kecil dan simpan pengamatan itu; laporan agregat
-- akan dibahas kembali pada Pertemuan 6.
SELECT program_studi, semester, jumlah_mahasiswa, jumlah_didampingi
FROM v_ringkasan_pendampingan
ORDER BY jumlah_mahasiswa ASC;

-- B-NEG-01 Membaca data tingkat record.
-- Diharapkan GAGAL: ERROR 1142 (SELECT command denied ... 'v_nilai_mahasiswa').
SELECT * FROM v_nilai_mahasiswa LIMIT 1;

-- B-NEG-02 Membaca tabel nilai secara langsung.
-- Diharapkan GAGAL: ERROR 1142.
SELECT * FROM nilai_akademik LIMIT 1;


-- =====================================================================
-- BAGIAN C - Jalankan sebagai: operator_pipeline@localhost
-- Peran: identitas yang memasukkan data mentah ke staging.
-- =====================================================================

-- C-POS-01 Memasukkan satu baris mentah ke staging.
-- Diharapkan: 1 baris terpengaruh.
INSERT INTO staging_nilai
  (batch_id, record_id, kode_mahasiswa, program_studi, semester, kode_mk,
   nilai_angka, persentase_kehadiran, status_kelulusan, status_pendampingan, waktu_pembaruan)
VALUES
  ('UJI-C-POS-01', 'R90001', 'MHS-SYN-0001', 'Sains Data', '5', 'SSD1033',
   '81', '90', 'Lulus', 'Tidak', '2026-08-01T09:00:00');

-- C-POS-02 Membaca referensi mata kuliah untuk memvalidasi kode.
-- Diharapkan: 8 baris tampil.
SELECT kode_mk, nama_mk, sks FROM mata_kuliah ORDER BY kode_mk;

-- C-NEG-01 Membaca tabel identitas.
-- Diharapkan GAGAL: ERROR 1142 (SELECT command denied ... 'mahasiswa').
-- Inilah pemisahan yang membuat operator dapat mengirim data tanpa
-- pernah melihat identitas pemiliknya.
SELECT * FROM mahasiswa LIMIT 1;

-- C-NEG-02 Membaca tabel nilai yang sudah tervalidasi.
-- Diharapkan GAGAL: ERROR 1142.
SELECT * FROM nilai_akademik LIMIT 1;

-- C-NEG-03 Memuat langsung ke tabel nilai tanpa melewati validasi.
-- Diharapkan GAGAL: ERROR 1142 (INSERT command denied).
INSERT INTO nilai_akademik
  (record_id, kode_mahasiswa, kode_mk, semester, nilai_angka,
   persentase_kehadiran, status_kelulusan, status_pendampingan, waktu_pembaruan)
VALUES
  ('R90002', 'MHS-SYN-0001', 'SSD1033', 5, 100, 100, 'Lulus', 'Tidak', NOW());


-- =====================================================================
-- BAGIAN D - Jalankan sebagai: auditor@localhost
-- Peran: pembaca catatan aktivitas.
-- =====================================================================

-- D-POS-01 Membaca log aktivitas.
-- Diharapkan: baris hasil pengujian A-POS-03 tampil.
SELECT log_id, waktu, aktor, komponen, aksi, hasil, korelasi_id
FROM log_aktivitas
ORDER BY log_id DESC
LIMIT 10;

-- D-NEG-01 Menambah catatan sendiri.
-- Diharapkan GAGAL: ERROR 1142 (INSERT command denied).
INSERT INTO log_aktivitas (aktor, komponen, aksi, hasil)
VALUES ('auditor', 'manual', 'sisip_catatan', 'berhasil');

-- D-NEG-02 Menghapus catatan.
-- Diharapkan GAGAL: ERROR 1142 (DELETE command denied).
-- Auditor yang dapat menghapus log membuat log berhenti menjadi bukti.
DELETE FROM log_aktivitas WHERE log_id = 1;

-- D-NEG-03 Membaca data akademik.
-- Diharapkan GAGAL: ERROR 1142.
SELECT * FROM v_nilai_mahasiswa LIMIT 1;


-- =====================================================================
-- BAGIAN E - Pembersihan, jalankan sebagai: admin_lab@localhost
-- =====================================================================

-- Menghapus jejak pengujian agar praktikum dapat diulang dari kondisi
-- awal yang sama.
DELETE FROM staging_nilai  WHERE batch_id    = 'UJI-C-POS-01';
DELETE FROM log_aktivitas  WHERE korelasi_id = 'UJI-A-POS-03';

-- Ringkasan bukti: jumlah pengujian yang tercatat.
SELECT 'staging_nilai' AS tabel, COUNT(*) AS sisa_baris_uji
FROM staging_nilai WHERE batch_id = 'UJI-C-POS-01'
UNION ALL
SELECT 'log_aktivitas', COUNT(*)
FROM log_aktivitas WHERE korelasi_id = 'UJI-A-POS-03';
-- Hasil yang diharapkan: kedua baris bernilai 0.
