-- =====================================================================
-- Penyiapan Pertemuan 7 — basis data tujuan pemulihan
-- Mata Kuliah Keamanan Data (SSD1033)
--
-- Dijalankan SATU KALI sebelum kelas, sebagai akun administrator server
-- (root) di komputer Anda sendiri. Pada komputer laboratorium bersama,
-- pengelola laboratorium yang menjalankannya. Jalankan dari akar proyek, yaitu
-- folder yang berisi folder starter/:
--
--   mysql -u root -p -e "source starter/siapkan_p07.sql"
--
-- Bentuk `mysql ... < berkas.sql` tidak berjalan di PowerShell, yang
-- menjadi terminal bawaan VS Code di Windows.
--
-- Mengapa perlu berkas terpisah: akun admin_lab sengaja hanya diberi hak
-- atas secure_academic_lab.*, sehingga akun itu tidak dapat membuat basis data
-- baru. Itu memang rancangan yang benar dari Pertemuan 4, dan kali ini
-- rancangan itu menghalangi pekerjaan yang sah.
--
-- Situasi seperti inilah yang sering diselesaikan dengan memberi hak
-- global "supaya lancar". Yang benar adalah menambah hak sesempit
-- mungkin, tepat pada sasaran yang dibutuhkan — dan itulah yang
-- dilakukan berkas ini.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS secure_academic_lab_pulih
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

-- Hak diberikan hanya pada basis data tujuan pemulihan, bukan pada *.*
GRANT ALL PRIVILEGES ON secure_academic_lab_pulih.* TO 'admin_lab'@'localhost';

FLUSH PRIVILEGES;


-- ---------------------------------------------------------------------
-- Pemeriksaan setelah penyiapan
-- ---------------------------------------------------------------------

SELECT 'Basis data tujuan pemulihan' AS pemeriksaan;

SELECT schema_name, default_character_set_name
FROM information_schema.schemata
WHERE schema_name IN ('secure_academic_lab', 'secure_academic_lab_pulih');
-- Harapan: dua baris.

SELECT 'Hak admin_lab' AS pemeriksaan;

SELECT table_schema, COUNT(*) AS jumlah_hak
FROM information_schema.schema_privileges
WHERE grantee = "'admin_lab'@'localhost'"
GROUP BY table_schema;
-- Harapan: dua baris, masing-masing untuk secure_academic_lab dan
-- secure_academic_lab_pulih. Tidak ada hak pada basis data lain.

SELECT 'Hak global admin_lab' AS pemeriksaan;

SELECT COUNT(*) AS jumlah_hak_global
FROM information_schema.user_privileges
WHERE grantee = "'admin_lab'@'localhost'"
  AND privilege_type <> 'USAGE';
-- Harapan: 0. Menambah basis data tujuan tidak boleh menambah hak global.


-- ---------------------------------------------------------------------
-- Membatalkan penyiapan, bila laboratorium sudah selesai
-- ---------------------------------------------------------------------
--
--   REVOKE ALL PRIVILEGES ON secure_academic_lab_pulih.* FROM 'admin_lab'@'localhost';
--   DROP DATABASE secure_academic_lab_pulih;
--
-- Dua baris di atas sengaja dibiarkan sebagai komentar. Perintah yang
-- menghapus basis data tidak pernah ditaruh pada berkas yang dijalankan
-- otomatis.
