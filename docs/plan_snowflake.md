# Sprint 5 — Snowflake Staging (Phase 5)

> Pengganti `docs/plan1.md` (yang sudah selesai & dihapus). Acuan teknis: `docs/Modern_Data_Platform_Spa_TDD.md`
> PRD section 13 (Snowflake Architecture), Phase 5 (Snowflake), section 12 (Metadata & Logging), section 17 (Idempotency).

## Status Awal (Sprint 0–4, sudah selesai)

- Phase 0–4: business design, cloud infra (S3/IAM), connectivity, generic extractor, data validation.
- 11 tabel diekstrak dari Supabase ke S3 raw sebagai CSV, semuanya `SUCCESS` + validation `PASS`.
- Test suite 40 test, semua hijau (offline, mock/moto).
- `docs/plan1.md` dihapus karena plan-nya sudah tuntas.

## Goal Sprint 5

Membawa data dari AWS S3 (data lake) ke Snowflake `STAGING` secara **config-driven**, **idempotent**,
dengan **metadata batch** dan **test otomatis offline** — sehingga siap dikonsumsi oleh dbt (Phase 7).

Arsitektur yang dipakai (pola ELT, sesuai PRD):

```text
Supabase PostgreSQL
   |
   | Python extract + validate + upload CSV      (Selesai: Sprint 2-4)
   v
AWS S3 RAW  s3://spa-data-platform-dev/raw/<table>/...
   |
   | SQL COPY INTO  (Snowflake menarik sendiri dari S3 stage)
   v
Snowflake STAGING  (SPA_ANALYTICS.STAGING)
   |
   | dbt (Phase 7)
   v
Snowflake WAREHOUSE -> MART -> Power BI
```

**Pembagian tanggung jawab (keputusan arsitektur):**

| Komponen | Yang melakukan | Data bytes |
|---|---|---|
| Extract S3 | Python (`extract/`) | Python upload ke S3 |
| S3 → Snowflake | SQL `COPY INTO` (mesin Snowflake yang membaca S3) | **Snowflake** |
| Trigger COPY | Thin Python runner (`warehouse/loader.py`) — hanya kirim SQL + catat metadata | — |
| Transform | dbt (SQL dieksekusi di dalam Snowflake, Phase 7) | Snowflake |

Pola ini = best practice industri: load via SQL COPY (standar Snowflake), trigger otomatis yang tipis
(yang nanti di Phase 10 dijalankan/dijadwalkan Airflow), transformasi via dbt (SQL-first).

## Task Breakdown

### Task 1 — Dependency & konfigurasi (Snowflake interface)
- `requirements.txt`: tambah `snowflake-connector-python` (connector resmi Python → Snowflake).
- `config/settings.py`: tambah `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USERNAME`, `SNOWFLAKE_PASSWORD`,
  `SNOWFLAKE_ROLE`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`.
  - Catatan: hanya divalidasi oleh `loader.py`, BUKAN oleh `main.py` — supaya pipeline extract & test
    tetap jalan walau Snowflake belum dikonfigurasi.
- `.env.example`: tambah placeholder `SNOWFLAKE_*` (tanpa secret).
- Verifikasi: `pip install -r requirements.txt` + `import snowflake.connector` sukses.

### Task 2 — `warehouse/sql/` DDL (idempotent, bisa dijalankan manual di SnowSQL)
- `01_database_warehouse.sql`: DB `SPA_ANALYTICS`, warehouse `SPA_WH` (XSMALL, auto-suspend/resume),
  schemas `STAGING`, `WAREHOUSE`, `MART`.
- `02_storage_integration.sql`:
  - File format CSV: `SKIP_HEADER=1`, `FIELD_OPTIONALLY_ENCLOSED_BY='"'`, `EMPTY_FIELD_AS_NULL=TRUE`,
    `NULL_IF=('NULL','')`, `ERROR_ON_COLUMN_COUNT_MISMATCH=FALSE`.
  - Storage integration ke IAM role (ARN placeholder) + external stage ke `s3://spa-data-platform-dev/raw/`.
- `03_staging_tables.sql`: `CREATE OR REPLACE` 11 tabel staging (di-generate, lihat Task 3).

### Task 3 — `warehouse/ddl_generator.py` (PRD Rule 3: jangan mengarang kolom)
- Baca skema asli Supabase via `postgres_connector.inspect_table` (11 tabel).
- Map tipe Postgres → Snowflake: `uuid→VARCHAR(36)`, `text/varchar→VARCHAR`, `numeric→NUMBER(38,9)`,
  `int/integer→NUMBER(38,0)`, `double→FLOAT`, `boolean→BOOLEAN`, `timestamp→TIMESTAMP_NTZ`,
  `date→DATE`, `jsonb→VARIANT`.
- Generate `warehouse/sql/03_staging_tables.sql`.
- Fungsi pure (`map_postgres_type`, `generate_create_table`) → bisa di-test offline.

### Task 4 — `warehouse/loader.py` (thin Python runner)
- CLI: `--setup` (eksekusi DDL 01–03) dan `--load` (default: full load).
- Per tabel dari `config/tables.yaml`:
  1. `TRUNCATE TABLE STAGING.<table>` (idempotensi, PRD section 17)
  2. `COPY INTO STAGING.<table> FROM @<stage>/raw/<table>/ PATTERN='.*\.csv' ON_ERROR='ABORT_STATEMENT'`
  3. `SELECT COUNT(*)` → verifikasi & catat `rows_loaded`
- Metadata batch → `logs/load_log_<batch>.json` (skema sama dengan `extract_log_`):
  `batch_id`, `source_table`, `start/end_time`, `status`, `rows_loaded`, `duration_seconds`, `error_message`.
- Import `snowflake.connector` lazy → test offline tetap jalan.

### Task 5 — `tests/test_snowflake.py` (offline, mock connector)
- `build_copy_statement` → SQL COPY benar.
- `map_postgres_type` & `generate_create_table` → tipe + DDL benar.
- Loader: mock connector → tabel sukses + tabel gagal → status `SUCCESS`/`FAILED`, `rows_loaded`,
  error tertangkap, tabel lain tetap diproses (continue policy), metadata tertulis.

### Task 6 — Dokumentasi
- README: panduan setup Snowflake langkah demi langkah (akun trial, IAM role + trust policy,
  isi `.env`, `--setup`, `--load`, verifikasi count sumber vs staging).
- Update tabel Roadmap/Status PRD repo.

### Task 7 — Verifikasi & commit
- `pytest` semua hijau (40 + test baru).
- Jalankan `ddl_generator` → `03_staging_tables.sql` benar untuk 11 tabel.
- Commit:
  - `chore: remove completed plan1.md`
  - `feat: snowflake staging DDL + loader + tests (Phase 5)`

## Verifikasi / Acceptance

```text
- pytest hijau (offline, tanpa akun Snowflake)
- 03_staging_tables.sql berisi 11 tabel dari skema Supabase asli
- Instruksi setup lengkap di README
- (Setelah akun siap) staging COUNT(*) == count sumber: transactions 179, booking_logs 279, dst.
```

## DoD (PRD section 25)

- [ ] Implementasi ada
- [ ] Konfigurasi terdokumentasi (`.env.example`, README)
- [ ] Test/validasi ada (pytest)
- [ ] Failure behavior dipertimbangkan (per-tabel FAILED + continue, `ON_ERROR='ABORT_STATEMENT'`)
- [ ] Log tersedia (`logs/load_log_*.json`)
- [ ] README di-update
- [ ] Commit ke Git
- [ ] Output siap dikonsumsi fase berikutnya (staging → dbt Phase 7)

## Catatan / Batasan

- Akun Snowflake belum ada → seluruh kode & test diselesaikan offline; eksekusi nyata
  (`--setup`, `--load`) dijalankan user setelah akun & IAM role siap.
- Menggunakan storage integration (IAM role) — bukan menyimpan AWS keys di stage (least privilege, PRD 3.5).
- Snowpipe (continuous ingest) TIDAK dipakai: proyek ini batch terjadwal via Airflow (Phase 10).
