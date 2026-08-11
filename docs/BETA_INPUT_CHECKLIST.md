# Beta input checklist

Do not commit or paste credentials into source files. Use local `.env` or the selected hosting provider's secret manager.

## 1. Google Sheets access

Choose one:

- Recommended: a Google service account with Viewer access to all five spreadsheets; provide the JSON as a private local attachment, never as a GitHub file.
- Temporary beta: publish only the required worksheets as read-only CSV if company policy permits it.

For each spreadsheet, provide:

- Expected worksheet(s) containing history
- 5–20 representative rows with sensitive fields masked if necessary
- Meaning of date/time, barcode, location, price, status, staff and memo columns
- Two or more known barcodes whose intermediate events should appear

## 2. Dropbox access

- Dropbox app key, secret and refresh token through local `.env`/secret manager
- Read-only access to `/공동판매_auto` and `/전매장매입매출_auto용_수빈`
- One representative workbook from each family for profiler testing, or exported header/sample rows
- Confirmed refund indicator/rule from the actual `매출` sheet

## 3. Known-answer beta cases

For 3–10 barcodes, list:

- Expected official receiving record
- Expected Google intermediate events
- Expected location/price transitions
- Expected sales/refunds/resales
- Any known duplicates across sources

## 4. Beta hosting choice

GitHub Pages can host only the frontend. Choose a private API/database host, for example Cloud Run, Render, Railway, Fly.io or an existing company server. Provide the preferred target and whether access must be restricted to company users.

## 5. Security confirmation

- Whether barcode timelines may be reachable from a public URL
- Whether login is required
- Data retention requirement
- Whether raw source rows may be stored or only hashes/selected fields

