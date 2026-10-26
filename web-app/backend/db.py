import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

# Reliable project-relative path resolution
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_APP_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..'))
DATABASE_DIR = os.path.join(WEB_APP_DIR, 'database')
DB_PATH = os.path.join(DATABASE_DIR, 'leafscan.db')
UPLOADS_DIR = os.path.join(WEB_APP_DIR, 'frontend', 'static', 'uploads')


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Yield an SQLite connection (Row factory, foreign keys ON).

    Commits on success, rolls back on error, and ALWAYS closes the connection. (sqlite3's own
    ``with conn:`` only commits/rolls back and leaves the file open, which keeps the database
    file locked on Windows and prevents it from being deleted or replaced.)
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize SQLite tables for farms and scan history."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                size TEXT DEFAULT '',
                variety TEXT DEFAULT '',
                planting_date TEXT DEFAULT '',
                plant_count INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER,
                farm_name TEXT DEFAULT 'General / Unassigned',
                image_filename TEXT NOT NULL,
                prediction_label TEXT NOT NULL,
                is_healthy INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.0,
                disease_name TEXT,
                disease_type TEXT,
                disease_summary TEXT,
                disease_cause TEXT,
                raw_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_farm_id ON scans(farm_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_is_healthy ON scans(is_healthy)')
        conn.commit()


def reset_db(backup: bool = True, clear_uploads: bool = True) -> Optional[str]:
    """Refresh the database: wipe ALL farms and scans and recreate an empty schema.

    * backup=True copies the existing database file to ``leafscan_backup_<timestamp>.db``
      (in the same folder) before anything is deleted. Returns the backup path, or None.
    * clear_uploads=True also deletes the saved leaf photos in the uploads folder, so no
      orphaned images remain without a matching scan record.
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)
    backup_path: Optional[str] = None
    if backup and os.path.exists(DB_PATH):
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(DATABASE_DIR, f'leafscan_backup_{stamp}.db')
        shutil.copy2(DB_PATH, backup_path)

    for suffix in ('', '-wal', '-shm', '-journal'):
        path = DB_PATH + suffix
        if os.path.exists(path):
            os.remove(path)

    if clear_uploads and os.path.isdir(UPLOADS_DIR):
        for name in os.listdir(UPLOADS_DIR):
            file_path = os.path.join(UPLOADS_DIR, name)
            if os.path.isfile(file_path) and not name.startswith('.'):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    init_db()
    return backup_path


# ==========================================
# FARM CRUD OPERATIONS
# ==========================================

def list_farms() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT f.*,
                   (SELECT COUNT(*) FROM scans s WHERE s.farm_id = f.id) as scan_count,
                   (SELECT COUNT(*) FROM scans s WHERE s.farm_id = f.id AND s.is_healthy = 0 AND s.prediction_label != 'No clear disease found') as disease_scan_count
            FROM farms f
            ORDER BY f.created_at DESC
        '''
        rows = cursor.execute(query).fetchall()
        return [dict(row) for row in rows]


def get_farm(farm_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT f.*,
                   (SELECT COUNT(*) FROM scans s WHERE s.farm_id = f.id) as scan_count
            FROM farms f
            WHERE f.id = ?
        '''
        row = cursor.execute(query, (farm_id,)).fetchone()
        return dict(row) if row else None


def create_farm(name: str, location: str = '', size: str = '', variety: str = '',
                planting_date: str = '', plant_count: int = 0, notes: str = '') -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO farms (name, location, size, variety, planting_date, plant_count, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (name.strip(), location.strip(), size.strip(), variety.strip(), planting_date.strip(), plant_count, notes.strip()))
        conn.commit()
        return cursor.lastrowid


def update_farm(farm_id: int, name: str, location: str = '', size: str = '', variety: str = '',
                planting_date: str = '', plant_count: int = 0, notes: str = '') -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE farms
            SET name = ?, location = ?, size = ?, variety = ?, planting_date = ?, plant_count = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name.strip(), location.strip(), size.strip(), variety.strip(), planting_date.strip(), plant_count, notes.strip(), farm_id))
        farm_updated = (cursor.rowcount > 0)
        # Also update historical farm_name label in scans associated with this farm
        cursor.execute('UPDATE scans SET farm_name = ? WHERE farm_id = ?', (name.strip(), farm_id))
        conn.commit()
        return farm_updated


def delete_farm(farm_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Farm deletion sets scans.farm_id to NULL and marks historical label
        cursor.execute("UPDATE scans SET farm_name = farm_name || ' (Archived)' WHERE farm_id = ?", (farm_id,))
        cursor.execute('DELETE FROM farms WHERE id = ?', (farm_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==========================================
# SCAN CRUD OPERATIONS
# ==========================================

def save_scan(image_filename: str, prediction_label: str, is_healthy: bool,
              confidence: float, disease_name: str, disease_type: str,
              disease_summary: str, disease_cause: str, raw_data: Dict[str, Any],
              farm_id: Optional[int] = None) -> int:
    farm_name = 'General / Unassigned'
    if farm_id:
        farm = get_farm(farm_id)
        if farm:
            farm_name = farm['name']
        else:
            farm_id = None

    raw_json = json.dumps(raw_data)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scans (
                farm_id, farm_name, image_filename, prediction_label,
                is_healthy, confidence, disease_name, disease_type,
                disease_summary, disease_cause, raw_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            farm_id, farm_name, image_filename, prediction_label,
            1 if is_healthy else 0, round(confidence, 1), disease_name,
            disease_type, disease_summary, disease_cause, raw_json
        ))
        conn.commit()
        return cursor.lastrowid


def list_scans(search: Optional[str] = None, status_filter: Optional[str] = None,
               farm_id: Optional[int] = None, sort_order: str = 'newest',
               limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM scans WHERE 1=1'
        params: List[Any] = []

        if search:
            search_pattern = f'%{search.strip()}%'
            query += ' AND (prediction_label LIKE ? OR disease_name LIKE ? OR farm_name LIKE ?)'
            params.extend([search_pattern, search_pattern, search_pattern])

        if status_filter == 'healthy':
            query += ' AND is_healthy = 1'
        elif status_filter == 'disease':
            query += " AND is_healthy = 0 AND prediction_label != 'No clear disease found'"
        elif status_filter == 'unclear':
            query += " AND prediction_label = 'No clear disease found'"

        if farm_id is not None:
            query += ' AND farm_id = ?'
            params.append(farm_id)

        if sort_order == 'oldest':
            query += ' ORDER BY created_at ASC'
        else:
            query += ' ORDER BY created_at DESC'

        query += ' LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        rows = cursor.execute(query, params).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item['raw_json'] = json.loads(item['raw_json']) if item['raw_json'] else {}
            except Exception:
                item['raw_json'] = {}
            result.append(item)
        return result


def get_scan(scan_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute('SELECT * FROM scans WHERE id = ?', (scan_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data['raw_json'] = json.loads(data['raw_json']) if data['raw_json'] else {}
        except Exception:
            data['raw_json'] = {}
        return data


def delete_scan(scan_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        scan = cursor.execute('SELECT image_filename FROM scans WHERE id = ?', (scan_id,)).fetchone()
        if not scan:
            return False

        image_filename = scan['image_filename']
        cursor.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
        conn.commit()

        # Check if any other scan references this image filename
        other = cursor.execute('SELECT COUNT(*) as cnt FROM scans WHERE image_filename = ?', (image_filename,)).fetchone()
        if other and other['cnt'] == 0:
            file_path = os.path.join(UPLOADS_DIR, image_filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        return True


# ==========================================
# CROP MONITORING & DASHBOARD METRICS
# ==========================================

def get_dashboard_stats() -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()

        total_farms = cursor.execute('SELECT COUNT(*) as c FROM farms').fetchone()['c']
        total_scans = cursor.execute('SELECT COUNT(*) as c FROM scans').fetchone()['c']
        healthy_scans = cursor.execute('SELECT COUNT(*) as c FROM scans WHERE is_healthy = 1').fetchone()['c']
        disease_scans = cursor.execute(
            "SELECT COUNT(*) as c FROM scans WHERE is_healthy = 0 AND prediction_label != 'No clear disease found'"
        ).fetchone()['c']
        unclear_scans = cursor.execute(
            "SELECT COUNT(*) as c FROM scans WHERE prediction_label = 'No clear disease found'"
        ).fetchone()['c']

        # Most frequently detected diseases
        top_diseases_rows = cursor.execute('''
            SELECT disease_name, COUNT(*) as count
            FROM scans
            WHERE is_healthy = 0 AND prediction_label != 'No clear disease found' AND disease_name IS NOT NULL
            GROUP BY disease_name
            ORDER BY count DESC
            LIMIT 5
        ''').fetchall()
        top_diseases = [dict(r) for r in top_diseases_rows]

        # Activity timeline - scans grouped by day for the MOST RECENT 14 active days
        # (newest 14 selected first, then returned oldest -> newest for charting).
        timeline_rows = cursor.execute('''
            SELECT * FROM (
                SELECT substr(created_at, 1, 10) as scan_date,
                       COUNT(*) as total,
                       SUM(CASE WHEN is_healthy = 1 THEN 1 ELSE 0 END) as healthy,
                       SUM(CASE WHEN is_healthy = 0 AND prediction_label != 'No clear disease found' THEN 1 ELSE 0 END) as disease
                FROM scans
                GROUP BY substr(created_at, 1, 10)
                ORDER BY scan_date DESC
                LIMIT 14
            ) ORDER BY scan_date ASC
        ''').fetchall()
        timeline = [dict(r) for r in timeline_rows]

        # Recent scans (up to 6)
        recent_rows = cursor.execute('''
            SELECT id, farm_name, image_filename, prediction_label, is_healthy, confidence, disease_name, created_at
            FROM scans
            ORDER BY created_at DESC
            LIMIT 6
        ''').fetchall()
        recent_scans = [dict(r) for r in recent_rows]

        # Contextual alerts
        alerts = []
        if total_scans == 0:
            alerts.append({
                'level': 'info',
                'title': 'No scans recorded yet',
                'message': 'Upload or take photos of your tomato leaves on the Scan Leaf page to start monitoring crop health.'
            })
        else:
            critical_diseases = ['Late Blight', 'Bacterial Canker', 'Tomato yellow leaf curl virus', 'Yellow Curl Virus']
            urgent_scans = cursor.execute('''
                SELECT disease_name, farm_name, created_at
                FROM scans
                WHERE is_healthy = 0 AND disease_name IN ({})
                ORDER BY created_at DESC
                LIMIT 2
            '''.format(','.join(['?'] * len(critical_diseases))), critical_diseases).fetchall()

            for urgent in urgent_scans:
                alerts.append({
                    'level': 'warning',
                    'title': f'Urgent: {urgent["disease_name"]} detected',
                    'message': f'Detected on {urgent["farm_name"]}. Check spread control guidance immediately to safeguard crops.'
                })

            if disease_scans > 0 and len(alerts) < 3:
                alerts.append({
                    'level': 'warning' if disease_scans > healthy_scans else 'info',
                    'title': f'{disease_scans} disease detection{"s" if disease_scans != 1 else ""} on record',
                    'message': f'{healthy_scans} scans diagnosed healthy ({round((healthy_scans/total_scans)*100 if total_scans else 0)}%). Regular leaf scouting is recommended.'
                })
            elif healthy_scans == total_scans and total_scans > 0:
                alerts.append({
                    'level': 'success',
                    'title': 'Optimal Crop Health',
                    'message': 'All recorded scans have returned healthy leaves! Continue preventative watering and soil maintenance.'
                })

        return {
            'total_farms': total_farms,
            'total_scans': total_scans,
            'healthy_scans': healthy_scans,
            'disease_scans': disease_scans,
            'unclear_scans': unclear_scans,
            'healthy_percentage': round((healthy_scans / total_scans * 100), 1) if total_scans > 0 else 0,
            'disease_percentage': round((disease_scans / total_scans * 100), 1) if total_scans > 0 else 0,
            'top_diseases': top_diseases,
            'timeline': timeline,
            'recent_scans': recent_scans,
            'alerts': alerts,
        }
