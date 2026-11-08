-- =====================================================================
-- Audit keamanan server MySQL — Pertemuan 7
-- Mata Kuliah Keamanan Data (SSD1033)
--
-- Berkas ini HANYA MEMBACA. Tidak ada satu pun perintah yang mengubah
-- akun, hak, atau pengaturan. Setiap perbaikan dikerjakan manual setelah
-- Anda memahami akibatnya.
--
-- Dijalankan sebagai akun administrator server, karena sebagian besar
-- query membaca tabel mysql.user dan variabel global. Jalankan dari akar
-- proyek, yaitu folder yang berisi folder starter/:
--
--   mysql -u root -p --table -e "source starter/audit_keamanan.sql"
--
-- Bentuk `mysql ... < berkas.sql` tidak berjalan di PowerShell, yang
-- menjadi terminal bawaan VS Code di Windows.
--
-- Pada WAMP, mysql.exe berada di:
--   C:/wamp64/bin/mysql/mysql8.4.7/bin/mysql.exe
-- Nomor versinya mengikuti pemasangan Anda; periksa isi C:/wamp64/bin/mysql/
--
-- Catat setiap temuan pada worksheet bagian E sebagai P07-E02.
-- =====================================================================


-- ---------------------------------------------------------------------
-- A. Akun tanpa kata sandi
--
-- Peran (role) MySQL sengaja tidak berkata sandi dan selalu terkunci.
-- Karena itu account_locked disaring, agar yang tersisa benar-benar akun
-- yang dapat dipakai masuk. Audit yang tidak menyaring ini menghasilkan
-- daftar penuh temuan palsu, dan daftar seperti itu berhenti dibaca.
-- ---------------------------------------------------------------------

SELECT 'A. Akun tanpa kata sandi' AS pemeriksaan;

SELECT user, host, plugin, account_locked
FROM mysql.user
WHERE authentication_string = ''
  AND account_locked = 'N'
ORDER BY user;

-- Harapan: kosong.
-- Bila root muncul di sini, siapa pun yang dapat menjalankan program di
-- komputer ini menjadi administrator basis data tanpa perlu tahu apa pun.


-- ---------------------------------------------------------------------
-- B. Akun yang dapat masuk dari mana saja
-- ---------------------------------------------------------------------

SELECT 'B. Akun dengan host terbuka' AS pemeriksaan;

SELECT user, host, account_locked
FROM mysql.user
WHERE host IN ('%', '')
  AND account_locked = 'N'
ORDER BY user;

-- Harapan: kosong pada komputer laboratorium.
-- Akun laboratorium seluruhnya dibuat dengan host 'localhost'.


-- ---------------------------------------------------------------------
-- C. Hak global yang berlebih
--
-- Hak pada *.* berlaku untuk SELURUH basis data, termasuk yang belum ada.
-- Akun aplikasi tidak pernah membutuhkannya.
-- ---------------------------------------------------------------------

SELECT 'C1. Hak global pada akun laboratorium' AS pemeriksaan;

SELECT grantee, privilege_type
FROM information_schema.user_privileges
WHERE privilege_type <> 'USAGE'
  AND grantee IN (
        "'app_service'@'localhost'",
        "'analyst'@'localhost'",
        "'operator_pipeline'@'localhost'",
        "'auditor'@'localhost'",
        "'admin_lab'@'localhost'")
ORDER BY grantee, privilege_type;

-- Harapan: kosong. Hak kelima akun itu seluruhnya melekat pada
-- secure_academic_lab.*, tidak pernah pada *.*

SELECT 'C2. Jumlah hak global per akun' AS pemeriksaan;

SELECT grantee, COUNT(*) AS jumlah_hak_global
FROM information_schema.user_privileges
WHERE privilege_type <> 'USAGE'
  AND grantee NOT LIKE '''mysql.%'
GROUP BY grantee
ORDER BY jumlah_hak_global DESC;

-- Daftarnya diringkas menjadi hitungan, bukan diuraikan satu per satu.
-- Audit yang mencetak ratusan baris berhenti dibaca, dan audit yang
-- tidak dibaca sama saja dengan tidak dijalankan.


-- ---------------------------------------------------------------------
-- D. Pengaturan server yang menentukan luas paparan
-- ---------------------------------------------------------------------

SELECT 'D. Pengaturan server' AS pemeriksaan;

SELECT 'bind_address'             AS pengaturan, @@bind_address              AS nilai,
       '127.0.0.1 untuk laptop laboratorium'    AS yang_diharapkan
UNION ALL
SELECT 'skip_networking',          @@skip_networking,
       '1 bila tidak ada klien dari luar komputer'
UNION ALL
SELECT 'local_infile',             @@local_infile,
       '0; bila 1, klien dapat diminta mengirim isi berkasnya'
UNION ALL
SELECT 'secure_file_priv',         IFNULL(@@secure_file_priv, 'NULL'),
       'folder khusus; NULL berarti tidak dibatasi'
UNION ALL
SELECT 'require_secure_transport', @@require_secure_transport,
       '1 bila koneksi datang dari luar komputer'
UNION ALL
SELECT 'general_log',              @@general_log,
       '0; log ini merekam seluruh query termasuk data pribadi'
UNION ALL
SELECT 'log_bin',                  @@log_bin,
       '1 bila pemulihan sampai titik waktu tertentu dibutuhkan';

-- bind_address bernilai * berarti MySQL menerima sambungan dari jaringan.
-- Pada komputer laboratorium yang dibawa berpindah tempat, ini memperluas
-- paparan tanpa menambah manfaat.


-- ---------------------------------------------------------------------
-- E. Hak per basis data pada akun laboratorium
-- ---------------------------------------------------------------------

SELECT 'E1. Hak per basis data' AS pemeriksaan;

SELECT grantee, table_schema, privilege_type
FROM information_schema.schema_privileges
WHERE table_schema = 'secure_academic_lab'
ORDER BY grantee, privilege_type;

-- Rancangan P04 menaruh hak akun aplikasi pada role dan pada view, bukan
-- pada seluruh basis data. Karena itu hak tersebut tidak tampil di E1,
-- melainkan di E2.

SELECT 'E2. Hak per objek pada role laboratorium' AS pemeriksaan;

SELECT grantee, table_name, privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'secure_academic_lab'
ORDER BY grantee, table_name, privilege_type;

SELECT 'E3. Hak efektif app_service melalui role' AS pemeriksaan;

SHOW GRANTS FOR 'app_service'@'localhost' USING 'r_app_service';
-- Harapan: SELECT pada dua view dan INSERT pada log_aktivitas.
-- Hak DROP tidak boleh ada. Jangan mengujinya dengan DROP TABLE pada tabel proyek.


-- ---------------------------------------------------------------------
-- F. View dan cara haknya diperiksa
--
-- SQL SECURITY DEFINER berarti view berjalan memakai hak pembuatnya,
-- bukan hak pemanggilnya. Itulah yang membuat akun tanpa hak atas tabel
-- dasar tetap dapat membaca ringkasannya — dan itulah yang membuat view
-- salah rancang menjadi jalan pintas menembus kontrol akses.
-- ---------------------------------------------------------------------

SELECT 'F. View dan security type' AS pemeriksaan;

SELECT table_name, security_type, definer, is_updatable
FROM information_schema.views
WHERE table_schema = 'secure_academic_lab'
ORDER BY table_name;


-- ---------------------------------------------------------------------
-- G. Ringkasan isi basis data
--
-- Dipakai sebagai angka pembanding sebelum dan sesudah pemulihan.
-- ---------------------------------------------------------------------

SELECT 'G. Ringkasan isi' AS pemeriksaan;

SELECT 'mahasiswa'      AS tabel, COUNT(*) AS jumlah_baris FROM secure_academic_lab.mahasiswa
UNION ALL SELECT 'mata_kuliah',    COUNT(*) FROM secure_academic_lab.mata_kuliah
UNION ALL SELECT 'nilai_akademik', COUNT(*) FROM secure_academic_lab.nilai_akademik
UNION ALL SELECT 'staging_nilai',  COUNT(*) FROM secure_academic_lab.staging_nilai
UNION ALL SELECT 'log_aktivitas',  COUNT(*) FROM secure_academic_lab.log_aktivitas;

CHECKSUM TABLE
  secure_academic_lab.mahasiswa,
  secure_academic_lab.mata_kuliah,
  secure_academic_lab.nilai_akademik,
  secure_academic_lab.staging_nilai,
  secure_academic_lab.log_aktivitas;
