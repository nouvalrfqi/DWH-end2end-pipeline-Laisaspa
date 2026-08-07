Rencana: Sampai Extractor + Validasi (Phase 2–4)
Sprint 0 — Fondasi Repo
1. Perbaiki koneksi Postgres (tindakan kamu, 5 menit): Buka Supabase → Settings → Database → Connection string. Ambil host yang benar (format modern seperti aws-0-ap-southeast-1.pooler.supabase.com dengan ref project, atau host direct yang tercantum di dashboard). Tambahkan SUPABASE_HOST ke .env. Ini syarat wajib sebelum Sprint 2.
2. git init + versi pertama commit (belum ada git repo sama sekali).
3. .env.example berisi placeholder saja + perbaiki .gitignore (tambah logs/, *.csv, cache).
4. README.md dasar: arsitektur, cara setup, env vars.
5. Bersihkan requirements.txt → hanya: python-dotenv, psycopg2-binary, boto3, pyyaml, pandas, pyarrow, pytest, pytest-mock (atau moto untuk mock S3).
Sprint 1 — Validasi Konektivitas (Phase 2)
6. config/settings.py — sentral konfigurasi (bucket, region, daftar tabel, koneksi).
7. extract/s3_client.py — wrapper boto3 + upload test object ke raw/_test/ → verifikasi head_object → hapus.
8. extract/postgres_connector.py — koneksi psycopg2 dengan retry; verifikasi schema + row count (cocokkan dengan count REST yang sudah saya ukur: booking_logs 279, transactions 179, dst).
- Acceptance: Python baca Postgres ✓, auth S3 ✓, upload object ✓.
Sprint 2 — Generic Extraction Framework (Phase 3)
 9. config/tables.yaml — daftar 11 tabel (satu tempat, tanpa kode per-tabel).
10. extract/generic_extractor.py — full load, serialize CSV, upload ke raw/<table>/year=/month=/day=/<table>_<batch>.csv, batch_id YYYYMMDD_HHMMSS, metadata, logging, dan error policy (retry → lanjut/berhenti).
11. utils/logger.py — log ke console + logs/extract_log_<batch>.json.
12. TDD Rule 7: uji 1 tabel dulu (transactions), verifikasi hasil di S3, baru expand ke semua tabel.
- Acceptance: semua tabel terekstrak tanpa kode khusus per tabel.
Sprint 3 — Framework Validasi (Phase 4)
13. validation/validators.py — file exists/non-empty, schema columns sesuai, row-count (Postgres vs S3), null check, PK uniqueness, business rules (price >= 0, rating 1–5, dll).
14. config/validation_rules.yaml — aturan per tabel.
15. Wiring ke extractor: hasil PASS/FAIL dicatat di metadata & log.
Sprint 4 — Automated Testing (pytest)
16. tests/ — test_settings, test_s3 (mock/moto), test_postgres (mock), test_extractor, test_validation. Jalankan pytest, semua hijau.
Sprint 5 — Dokumentasi & Commit
17. Lengkapi README (alur pipeline, cara run, konfigurasi).
18. Commit per DoD (section 25 PRD): implementasi + konfigurasi terdokumentasi + test ada + failure behavior + log + README + commit.