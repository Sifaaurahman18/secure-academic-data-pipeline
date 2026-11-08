-- =====================================================================
-- Secure Academic Data Pipeline - Akun, Role, dan Privilege
-- Mata Kuliah Keamanan Data (SSD1033)
--
-- Dijalankan setelah schema.sql dan seed_data.sql, oleh akun
-- administrator laboratorium.
--
-- !! WAJIB DIBACA SEBELUM DIJALANKAN !!
--
-- Berkas ini TIDAK memuat kata sandi aktif. Seluruh nilai bertanda
-- __GANTI_...__ adalah penanda yang harus diganti terlebih dahulu.
-- Aturan yang berlaku sepanjang mata kuliah:
--
--   1. Ganti setiap penanda dengan kata sandi laboratorium Anda sendiri.
--   2. Jangan pernah mengumpulkan berkas ini setelah penanda diganti.
--   3. Kata sandi yang dipakai aplikasi dibaca melalui variabel
--      lingkungan (.env), bukan ditulis di kode atau di berkas SQL.
--   4. Bila berkas ini terlanjur berisi kata sandi asli, ganti kata
--      sandinya di basis data, jangan hanya menghapus barisnya.
--
-- Rancangan hak akses mengikuti prinsip hak minimum: tidak ada satu pun
-- akun aplikasi yang memiliki akses langsung ke tabel identitas
-- `mahasiswa` maupun ke kolom `status_pendampingan`.
-- =====================================================================

USE secure_academic_lab;

-- ---------------------------------------------------------------------
-- 1. Bersihkan sisa percobaan sebelumnya
--
-- Dijalankan agar praktikum dapat diulang dari kondisi awal yang sama.
-- ---------------------------------------------------------------------

DROP USER IF EXISTS 'app_service'@'localhost';
DROP USER IF EXISTS 'analyst'@'localhost';
DROP USER IF EXISTS 'operator_pipeline'@'localhost';
DROP USER IF EXISTS 'auditor'@'localhost';
DROP USER IF EXISTS 'admin_lab'@'localhost';

DROP ROLE IF EXISTS 'r_app_service';
DROP ROLE IF EXISTS 'r_analyst';
DROP ROLE IF EXISTS 'r_operator_pipeline';
DROP ROLE IF EXISTS 'r_auditor';

-- ---------------------------------------------------------------------
-- 2. Role
--
-- Role menyimpan kumpulan hak. Akun kemudian diberi role, bukan diberi
-- hak satu per satu. Dengan begitu perubahan kebijakan cukup dilakukan
-- di satu tempat.
-- ---------------------------------------------------------------------

CREATE ROLE 'r_app_service';
CREATE ROLE 'r_analyst';
CREATE ROLE 'r_operator_pipeline';
CREATE ROLE 'r_auditor';

-- 2.1 Starter API: hanya membaca dua view dan menulis log.
--     Tidak ada akses ke tabel dasar, sehingga kolom status_pendampingan
--     tidak dapat dijangkau melalui jalur mana pun.
GRANT SELECT ON secure_academic_lab.v_nilai_mahasiswa     TO 'r_app_service';
GRANT SELECT ON secure_academic_lab.v_ringkasan_kelulusan TO 'r_app_service';
GRANT INSERT ON secure_academic_lab.log_aktivitas         TO 'r_app_service';

-- 2.2 Analis: hanya membaca laporan agregat.
GRANT SELECT ON secure_academic_lab.v_ringkasan_kelulusan   TO 'r_analyst';
GRANT SELECT ON secure_academic_lab.v_ringkasan_pendampingan TO 'r_analyst';

-- 2.3 Operator pipeline: memasukkan data mentah ke staging dan membaca
--     referensi mata kuliah untuk memvalidasi kode. Tidak memiliki akses
--     ke tabel identitas maupun ke tabel nilai yang sudah tervalidasi.
GRANT INSERT, SELECT ON secure_academic_lab.staging_nilai TO 'r_operator_pipeline';
GRANT SELECT         ON secure_academic_lab.mata_kuliah   TO 'r_operator_pipeline';
GRANT INSERT         ON secure_academic_lab.log_aktivitas TO 'r_operator_pipeline';

-- 2.4 Auditor: hanya membaca log. Tidak dapat menambah, mengubah, atau
--     menghapus catatan, sehingga log tetap dapat dipercaya sebagai bukti.
GRANT SELECT ON secure_academic_lab.log_aktivitas TO 'r_auditor';

-- ---------------------------------------------------------------------
-- 3. Akun
--
-- Setiap akun dibatasi ke 'localhost' agar tidak dapat diakses dari
-- jaringan laboratorium. Ganti penanda kata sandi terlebih dahulu.
-- ---------------------------------------------------------------------

CREATE USER 'app_service'@'localhost'
  IDENTIFIED BY '__GANTI_PASSWORD_APP_SERVICE__';
CREATE USER 'analyst'@'localhost'
  IDENTIFIED BY '__GANTI_PASSWORD_ANALYST__';
CREATE USER 'operator_pipeline'@'localhost'
  IDENTIFIED BY '__GANTI_PASSWORD_OPERATOR__';
CREATE USER 'auditor'@'localhost'
  IDENTIFIED BY '__GANTI_PASSWORD_AUDITOR__';

-- Akun administrator laboratorium. Dipakai untuk membuat skema, memuat
-- seed, dan mengelola akun. TIDAK dipakai oleh pipeline maupun API.
CREATE USER 'admin_lab'@'localhost'
  IDENTIFIED BY '__GANTI_PASSWORD_ADMIN_LAB__';
GRANT ALL PRIVILEGES ON secure_academic_lab.* TO 'admin_lab'@'localhost';

-- ---------------------------------------------------------------------
-- 4. Pemberian role ke akun
--
-- SET DEFAULT ROLE diperlukan agar role langsung aktif ketika akun
-- login. Tanpa baris ini, akun akan terhubung tanpa hak apa pun dan
-- setiap query akan ditolak.
-- ---------------------------------------------------------------------

GRANT 'r_app_service'       TO 'app_service'@'localhost';
GRANT 'r_analyst'           TO 'analyst'@'localhost';
GRANT 'r_operator_pipeline' TO 'operator_pipeline'@'localhost';
GRANT 'r_auditor'           TO 'auditor'@'localhost';

SET DEFAULT ROLE ALL TO
  'app_service'@'localhost',
  'analyst'@'localhost',
  'operator_pipeline'@'localhost',
  'auditor'@'localhost';

FLUSH PRIVILEGES;

-- ---------------------------------------------------------------------
-- 5. Bukti konfigurasi
--
-- Simpan keluaran perintah berikut sebagai bukti praktikum. Keluaran
-- SHOW GRANTS tidak memuat kata sandi, sehingga aman disertakan setelah
-- nama host disanitasi.
-- ---------------------------------------------------------------------

SHOW GRANTS FOR 'app_service'@'localhost'       USING 'r_app_service';
SHOW GRANTS FOR 'analyst'@'localhost'           USING 'r_analyst';
SHOW GRANTS FOR 'operator_pipeline'@'localhost' USING 'r_operator_pipeline';
SHOW GRANTS FOR 'auditor'@'localhost'           USING 'r_auditor';

-- Ringkasan hak per akun langsung dari kamus data MySQL.
SELECT grantee, table_name, privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'secure_academic_lab'
ORDER BY grantee, table_name, privilege_type;
