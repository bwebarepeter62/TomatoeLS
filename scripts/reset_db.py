"""
Tomato Leaf Scan — Database Refresh / Reset Script
File: scripts/reset_db.py

Wipes ALL farms and scan history, deletes the saved leaf photos, and recreates an empty
database with the current schema.  A timestamped backup of the old database is written to
web-app/database/ first (disable with --no-backup).

Usage (from the project root):
    python scripts/reset_db.py            # asks for confirmation
    python scripts/reset_db.py --yes      # no prompt
    python scripts/reset_db.py --yes --no-backup
    python scripts/reset_db.py --keep-uploads   # keep the photos in static/uploads
"""

import argparse
import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, '..'))
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'web-app', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import db  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description='Refresh (reset) the LeafScan database.')
    parser.add_argument('-y', '--yes', action='store_true', help='do not ask for confirmation')
    parser.add_argument('--no-backup', action='store_true', help='do not keep a backup of the old database')
    parser.add_argument('--keep-uploads', action='store_true', help='do not delete saved leaf photos')
    args = parser.parse_args()

    if not args.yes:
        print(f'This will DELETE all farms and scans in:\n  {db.DB_PATH}')
        if input('Type "yes" to continue: ').strip().lower() != 'yes':
            print('Cancelled. Nothing was changed.')
            return 1

    backup_path = db.reset_db(backup=not args.no_backup, clear_uploads=not args.keep_uploads)

    print('[OK] Database refreshed: empty farms and scans tables recreated.')
    if backup_path:
        print(f'[OK] Backup of the old database: {backup_path}')

    with db.get_db_connection() as conn:
        farms = conn.execute('SELECT COUNT(*) FROM farms').fetchone()[0]
        scans = conn.execute('SELECT COUNT(*) FROM scans').fetchone()[0]
    print(f'     farms: {farms} | scans: {scans}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
