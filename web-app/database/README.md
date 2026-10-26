# Tomato Leaf Scan — Database Layer

## Overview
The web application uses a local, embedded **SQLite 3** relational database to persist farm plot registries, leaf scan inspections, AI model prediction metadata, and treatment advice.

- **Primary Database File:** `web-app/database/leafscan.db`
- **Schema Definition:** `web-app/database/schema.sql`
- **Database Driver:** Python standard library `sqlite3` (no external database server required)

---

## Schema Architecture

The database consists of two core tables linked by a one-to-many relationship:

```text
┌───────────────────────────┐         ┌─────────────────────────────────┐
│           farms           │ 1     * │              scans              │
├───────────────────────────┤─────────├─────────────────────────────────┤
│ id (PK, AUTOINCREMENT)    │         │ id (PK, AUTOINCREMENT)          │
│ name (TEXT, NOT NULL)     │         │ farm_id (FK -> farms.id)        │
│ location (TEXT)           │         │ farm_name (TEXT)                │
│ size (TEXT)               │         │ image_filename (TEXT, NOT NULL) │
│ variety (TEXT)            │         │ prediction_label (TEXT)         │
│ planting_date (TEXT)      │         │ is_healthy (INTEGER 0/1)        │
│ plant_count (INTEGER)     │         │ confidence (REAL)               │
│ notes (TEXT)              │         │ disease_name (TEXT)             │
│ created_at (TIMESTAMP)    │         │ disease_type (TEXT)             │
│ updated_at (TIMESTAMP)    │         │ disease_summary (TEXT)          │
│                           │         │ disease_cause (TEXT)            │
│                           │         │ raw_json (TEXT)                 │
│                           │         │ created_at (TIMESTAMP)          │
└───────────────────────────┘         └─────────────────────────────────┘
```

---

## Key Design Decisions & Security

1. **Foreign Key Integrity:** `PRAGMA foreign_keys = ON;` is strictly enforced on every database connection.
2. **Safe Farm Plot Archiving:** Deleting a farm record executes an `ON DELETE SET NULL` cascade on associated scans, and stamps `(Archived)` onto historical scan farm names so inspection logs are never lost.
3. **Safe Image Cleanup on Scan Deletion:** When a scan record is removed, `db.delete_scan()` checks if any other scan references the same physical image before unlinking it from `web-app/frontend/static/uploads/`.
4. **Parameterized SQL Queries:** Every database interaction in `db.py` uses parameterized tuple placeholders (`?`) to prevent SQL injection vulnerabilities.
5. **No Public Web Exposure:** The database file is located inside `web-app/database/`, strictly isolated from the public `static/` asset directory.

---

## Re-Initializing the Database

If the database file is removed or reset, the backend automatically initializes the tables and indexes upon startup:
```python
import db
db.init_db()
```
Or you can manually apply the SQL schema using SQLite CLI or Python:
```bash
sqlite3 web-app/database/leafscan.db < web-app/database/schema.sql
```

---

## Refreshing (Wiping) the Database

| Goal | Command |
|---|---|
| Refresh **once** (backup → wipe → empty DB) | `python scripts/reset_db.py` (add `--yes` to skip the prompt, `--no-backup` to skip the backup, `--keep-uploads` to keep photos) |
| Refresh **on every start** | `start_app.bat --fresh`, or set `LEAFSCAN_RESET_DB=1` before running `python app.py` (PowerShell: `$env:LEAFSCAN_RESET_DB='1'`) |
| Refresh on every start, no backup | also set `LEAFSCAN_RESET_BACKUP=0` |

Backups are saved as `web-app/database/leafscan_backup_<timestamp>.db` (git-ignored). To restore, stop the server and copy a backup over `leafscan.db`.
