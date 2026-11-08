-- =====================================================================
-- Secure Academic Data Pipeline - Skema Basis Data Laboratorium
-- Mata Kuliah Keamanan Data (SSD1033), Program Studi Sains Data
--
-- Dijalankan oleh akun administrator laboratorium, bukan oleh akun
-- aplikasi. Urutan penggunaan:
--
--   1. database/schema.sql     <- berkas ini
--   2. database/seed_data.sql  data sintetik hasil tools/buat_dataset.py
--   3. database/roles.sql      akun, role, dan privilege
--   4. database/uji_akses.sql  pengujian positif dan negatif
--
-- Seluruh isi basis data ini adalah data sintetik. Tidak ada identitas,
-- nilai, atau akun mahasiswa nyata di dalamnya.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS secure_academic_lab
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE secure_academic_lab;

-- ---------------------------------------------------------------------
-- 1. Tabel referensi
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS mata_kuliah;
CREATE TABLE mata_kuliah (
  kode_mk  VARCHAR(12)      NOT NULL,
  nama_mk  VARCHAR(120)     NOT NULL,
  sks      TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (kode_mk),
  CONSTRAINT ck_mata_kuliah_sks CHECK (sks BETWEEN 1 AND 6)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 2. Tabel identitas
--
-- Tabel ini memuat pengenal mahasiswa. Akun aplikasi dan akun operator
-- tidak diberi akses langsung ke tabel ini; keduanya bekerja melalui
-- view atau tabel staging.
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS mahasiswa;
CREATE TABLE mahasiswa (
  kode_mahasiswa VARCHAR(16)      NOT NULL,
  program_studi  VARCHAR(60)      NOT NULL,
  semester       TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (kode_mahasiswa),
  KEY ix_mahasiswa_prodi (program_studi, semester),
  CONSTRAINT ck_mahasiswa_semester CHECK (semester BETWEEN 1 AND 14)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 3. Tabel fakta nilai akademik
--
-- Batasan pada tabel ini adalah lapisan pertahanan terakhir. Validasi
-- utama tetap dilakukan pipeline Python sebelum data dimuat, sehingga
-- baris bermasalah dikarantina dengan pesan yang dapat dibaca, bukan
-- ditolak sebagai galat basis data.
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS nilai_akademik;
CREATE TABLE nilai_akademik (
  record_id            VARCHAR(12)                NOT NULL,
  kode_mahasiswa       VARCHAR(16)                NOT NULL,
  kode_mk              VARCHAR(12)                NOT NULL,
  semester             TINYINT UNSIGNED           NOT NULL,
  nilai_angka          TINYINT UNSIGNED           NOT NULL,
  persentase_kehadiran TINYINT UNSIGNED           NOT NULL,
  status_kelulusan     ENUM('Lulus','Tidak Lulus') NOT NULL,
  status_pendampingan  ENUM('Ya','Tidak')          NOT NULL,
  waktu_pembaruan      DATETIME                    NOT NULL,
  PRIMARY KEY (record_id),
  CONSTRAINT uq_nilai_alami UNIQUE (kode_mahasiswa, kode_mk, semester),
  CONSTRAINT fk_nilai_mahasiswa FOREIGN KEY (kode_mahasiswa)
    REFERENCES mahasiswa (kode_mahasiswa),
  CONSTRAINT fk_nilai_mata_kuliah FOREIGN KEY (kode_mk)
    REFERENCES mata_kuliah (kode_mk),
  CONSTRAINT ck_nilai_angka CHECK (nilai_angka BETWEEN 0 AND 100),
  CONSTRAINT ck_nilai_kehadiran CHECK (persentase_kehadiran BETWEEN 0 AND 100),
  CONSTRAINT ck_nilai_semester CHECK (semester BETWEEN 1 AND 14)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 4. Tabel staging
--
-- Staging menerima data mentah apa adanya dalam bentuk teks. Tujuannya
-- adalah memisahkan penerimaan dari pemuatan: operator boleh memasukkan
-- data ke sini tanpa diberi akses ke tabel identitas maupun tabel nilai.
-- Karena itu kolomnya sengaja tidak bertipe ketat.
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS staging_nilai;
CREATE TABLE staging_nilai (
  staging_id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  batch_id             VARCHAR(40)     NOT NULL,
  record_id            VARCHAR(32)     NULL,
  kode_mahasiswa       VARCHAR(32)     NULL,
  program_studi        VARCHAR(80)     NULL,
  semester             VARCHAR(8)      NULL,
  kode_mk              VARCHAR(16)     NULL,
  nilai_angka          VARCHAR(16)     NULL,
  persentase_kehadiran VARCHAR(16)     NULL,
  status_kelulusan     VARCHAR(24)     NULL,
  status_pendampingan  VARCHAR(24)     NULL,
  waktu_pembaruan      VARCHAR(32)     NULL,
  diterima_pada        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (staging_id),
  KEY ix_staging_batch (batch_id)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 5. Log aktivitas
--
-- Log bersifat tambah-saja. Akun aplikasi dan operator hanya diberi hak
-- INSERT; auditor hanya diberi hak SELECT. Tidak ada akun aplikasi yang
-- dapat mengubah atau menghapus catatan.
--
-- Kolom `keterangan` tidak boleh memuat kata sandi, token, kunci, atau
-- isi data pribadi. Simpan pengenal dan hasil, bukan muatan data.
-- ---------------------------------------------------------------------

DROP TABLE IF EXISTS log_aktivitas;
CREATE TABLE log_aktivitas (
  log_id      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  waktu       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  aktor       VARCHAR(64)     NOT NULL,
  komponen    VARCHAR(64)     NOT NULL,
  aksi        VARCHAR(64)     NOT NULL,
  objek       VARCHAR(120)    NULL,
  hasil       ENUM('berhasil','ditolak','gagal') NOT NULL,
  korelasi_id VARCHAR(64)     NULL,
  keterangan  VARCHAR(255)    NULL,
  PRIMARY KEY (log_id),
  KEY ix_log_waktu (waktu),
  KEY ix_log_aktor (aktor)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- 6. View
--
-- View dibuat oleh administrator dan memakai SQL SECURITY DEFINER.
-- Akibatnya, akun yang hanya diberi SELECT pada view dapat membaca
-- hasilnya tanpa memiliki hak apa pun pada tabel dasar. Inilah cara
-- pembatasan kolom dan baris diterapkan pada mata kuliah ini.
-- ---------------------------------------------------------------------

-- 6.1 Data tingkat record untuk starter API.
--     Kolom status_pendampingan sengaja tidak disertakan supaya atribut
--     paling sensitif tidak pernah dapat dijangkau melalui API.
CREATE OR REPLACE
  SQL SECURITY DEFINER
  VIEW v_nilai_mahasiswa AS
SELECT
  n.record_id,
  n.kode_mahasiswa,
  m.program_studi,
  n.semester,
  n.kode_mk,
  k.nama_mk,
  n.nilai_angka,
  n.persentase_kehadiran,
  n.status_kelulusan,
  n.waktu_pembaruan
FROM nilai_akademik n
JOIN mahasiswa   m ON m.kode_mahasiswa = n.kode_mahasiswa
JOIN mata_kuliah k ON k.kode_mk        = n.kode_mk;

-- 6.2 Ringkasan kelulusan per program studi, semester, dan mata kuliah.
CREATE OR REPLACE
  SQL SECURITY DEFINER
  VIEW v_ringkasan_kelulusan AS
SELECT
  m.program_studi,
  n.semester,
  n.kode_mk,
  COUNT(*)                                          AS jumlah_record,
  SUM(n.status_kelulusan = 'Lulus')                 AS jumlah_lulus,
  ROUND(AVG(n.nilai_angka), 2)                      AS rata_nilai,
  ROUND(AVG(n.persentase_kehadiran), 2)             AS rata_kehadiran
FROM nilai_akademik n
JOIN mahasiswa m ON m.kode_mahasiswa = n.kode_mahasiswa
GROUP BY m.program_studi, n.semester, n.kode_mk;

-- 6.3 Ringkasan pendampingan per program studi dan semester.
--     Dipakai pada Pertemuan 6 ketika membahas minimisasi data dan
--     risiko re-identifikasi pada laporan agregat.
CREATE OR REPLACE
  SQL SECURITY DEFINER
  VIEW v_ringkasan_pendampingan AS
SELECT
  m.program_studi,
  m.semester,
  COUNT(DISTINCT m.kode_mahasiswa) AS jumlah_mahasiswa,
  COUNT(DISTINCT CASE WHEN n.status_pendampingan = 'Ya'
                      THEN m.kode_mahasiswa END) AS jumlah_didampingi
FROM mahasiswa m
JOIN nilai_akademik n ON n.kode_mahasiswa = m.kode_mahasiswa
GROUP BY m.program_studi, m.semester;

-- ---------------------------------------------------------------------
-- Pemeriksaan cepat setelah skema dibuat
-- ---------------------------------------------------------------------

SELECT
  (SELECT COUNT(*) FROM information_schema.tables
     WHERE table_schema = 'secure_academic_lab' AND table_type = 'BASE TABLE') AS jumlah_tabel,
  (SELECT COUNT(*) FROM information_schema.views
     WHERE table_schema = 'secure_academic_lab')                               AS jumlah_view;
-- Hasil yang diharapkan: jumlah_tabel = 5, jumlah_view = 3
