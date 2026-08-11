# MIU Trace Worklog

Last updated: 2026-08-11 (Asia/Seoul)

## Current release

- Repository: `https://github.com/i7444636/miu-trace`
- Pages: `https://i7444636.github.io/miu-trace/`
- Stage: static UI prototype / beta integration pending
- Deployment: GitHub Actions → GitHub Pages

## Completed

- Independent `miu-trace` repository and GitHub Pages workflow
- Installable responsive PWA shell
- GitHub-inspired barcode search and chronological timeline UI
- Source Authority domain rules for official receiving and finalized/current sales
- Five Google spreadsheet IDs registered in `config/sources.yaml`
- Barcode normalization and coverage-bound current-period fallback rules
- Static `C24304` demo timeline

## Confirmed integration gap

The deployed page is currently in `DEMO_MODE`. Google Sheets and Dropbox are not queried yet. The five Google spreadsheet IDs are configuration only; there is no credentialed adapter, worksheet profiler, parser, database indexer, evidence merger, or deployed timeline API. Therefore intermediate Google Sheets events cannot appear in the current UI.

## Beta milestones

### B1 — Source Profiler

- Connect five Google Sheets read-only
- Discover every worksheet title, gid, headers, sample value types and barcode/date candidates
- Profile Dropbox workbook sheets without creating production events
- Store reports under `reports/` with secrets and raw sensitive values excluded

### B2 — Lineage database

- Raw Source → Raw Record → Observation → Event → Event Evidence
- SQLite locally; PostgreSQL-compatible schema for hosted beta
- Parser profile/version and source revision tracking

### B3 — Google supporting evidence

- Normalize barcode and timestamps
- Parse explicit price/location/status/operation changes
- Never create official `RECEIVED` from Google Sheets alone
- Attach Google rows as evidence to matching authoritative events
- Preserve distinct intermediate events when time/type/value differs

### B4 — Dropbox authority parsers

- `공동판매_auto / 입고`: official receiving, product snapshots, location/price/status changes
- `전매장매입매출_auto용_수빈 / 매출`: finalized sales/refunds
- `공동판매_auto / 전매장매출`: uncovered-period fallback only

### B5 — Beta API and live UI

- Private FastAPI timeline API
- Pages frontend points to API through `API_BASE_URL`
- CORS restricted to the Pages origin
- No source credentials or private keys in GitHub/Pages
- Source Diagnostics reports real scan/index status

### B6 — Acceptance test

- Select 3–10 known barcodes with expected intermediate events
- Compare every timeline item to its original source row
- Verify deduplication, authority, confidence and time precision
- Record false positives, omissions and `NEEDS_REVIEW` profiles

## Commit policy

Each completed milestone is committed independently to `main` while the beta is being assembled. Secrets, service-account JSON, Dropbox tokens and raw company data are never committed.

