"""
LeafScan — Database & Persistence Module
========================================
SQLite relational database operations with:
- Safe migrations preserving existing legacy records
- Multi-user authentication & user ownership relationships
- WAL mode, busy timeout (30s), foreign key enforcement
- Configurable persistent disk storage via LEAFSCAN_DATA_DIR
- Farm & scan CRUD with user-level isolation
- Advanced dashboard analytics with date-range & farm filters
- Mobile synchronization tracking (platform, model_name, sync_id)
"""

import json
import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

# Reliable project-relative path resolution with persistent volume support
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_APP_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..'))

# If LEAFSCAN_DATA_DIR is configured (e.g. Render Persistent Disk mount at /var/data),
# database and uploads will persist across container redeployments and restarts.
PERSISTENT_DATA_DIR = os.environ.get('LEAFSCAN_DATA_DIR', '').strip()
if PERSISTENT_DATA_DIR:
    DATABASE_DIR = os.path.join(PERSISTENT_DATA_DIR, 'database')
    UPLOADS_DIR = os.path.join(PERSISTENT_DATA_DIR, 'uploads')
else:
    DATABASE_DIR = os.path.join(WEB_APP_DIR, 'database')
    UPLOADS_DIR = os.path.join(WEB_APP_DIR, 'frontend', 'static', 'uploads')

DB_PATH = os.path.join(DATABASE_DIR, 'leafscan.db')


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Yield an SQLite connection with WAL mode, busy timeout, and foreign keys.

    Commits on success, rolls back on error, and ALWAYS closes the connection cleanly.
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
    except Exception:
        pass
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize SQLite tables and safely run non-destructive schema migrations."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table (Authentication & User Isolation)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                role TEXT DEFAULT 'farmer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Farms Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                location TEXT DEFAULT '',
                size TEXT DEFAULT '',
                variety TEXT DEFAULT '',
                planting_date TEXT DEFAULT '',
                plant_count INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        ''')

        # 3. Scans Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
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
                platform TEXT DEFAULT 'web',
                model_name TEXT DEFAULT 'tomato_disease_model.h5',
                sync_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL
            )
        ''')

        # Run Non-Destructive Migrations on Existing Databases
        # Check farms columns
        existing_farm_cols = [row['name'] for row in cursor.execute("PRAGMA table_info(farms)").fetchall()]
        if 'user_id' not in existing_farm_cols:
            cursor.execute('ALTER TABLE farms ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL')

        # Check scans columns
        existing_scan_cols = [row['name'] for row in cursor.execute("PRAGMA table_info(scans)").fetchall()]
        if 'user_id' not in existing_scan_cols:
            cursor.execute('ALTER TABLE scans ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL')
        if 'platform' not in existing_scan_cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN platform TEXT DEFAULT 'web'")
        if 'model_name' not in existing_scan_cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN model_name TEXT DEFAULT 'tomato_disease_model.h5'")
        if 'sync_id' not in existing_scan_cols:
            cursor.execute("ALTER TABLE scans ADD COLUMN sync_id TEXT")

        # Indexes for query performance and data isolation
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_farms_user_id ON farms(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_user_id ON scans(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_farm_id ON scans(farm_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_is_healthy ON scans(is_healthy)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scans_sync_id ON scans(sync_id)')
        conn.commit()


def reset_db(backup: bool = True, clear_uploads: bool = True) -> Optional[str]:
    """Wipe database and recreate schema with automated timestamped backup."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    backup_path: Optional[str] = None
    if backup and os.path.exists(DB_PATH):
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(DATABASE_DIR, f'leafscan_backup_{stamp}.db')
        shutil.copy2(DB_PATH, backup_path)

    for suffix in ('', '-wal', '-shm', '-journal'):
        path = DB_PATH + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

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
# USER AUTHENTICATION & MANAGEMENT
# ==========================================

def create_user(username: str, email: str, password_or_hash: str, full_name: str = '', role: str = 'farmer') -> int:
    clean_username = username.strip().lower()
    clean_email = email.strip().lower()

    if get_user_by_username(clean_username):
        raise ValueError(f"Username '{clean_username}' is already registered.")
    if get_user_by_email(clean_email):
        raise ValueError(f"Email '{clean_email}' is already in use.")

    # Automatically hash if raw password is provided
    if not (password_or_hash.startswith('scrypt:') or password_or_hash.startswith('pbkdf2:')):
        from werkzeug.security import generate_password_hash
        pwd_hash = generate_password_hash(password_or_hash)
    else:
        pwd_hash = password_or_hash

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (clean_username, clean_email, pwd_hash, full_name.strip(), role))
        conn.commit()
        return cursor.lastrowid


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute('SELECT * FROM users WHERE username = ?', (username.strip().lower(),)).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute('SELECT * FROM users WHERE email = ?', (email.strip().lower(),)).fetchone()
        return dict(row) if row else None


def authenticate_user(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    clean_id = identifier.strip().lower()
    user = get_user_by_username(clean_id) or get_user_by_email(clean_id)
    if not user:
        return None
    from werkzeug.security import check_password_hash
    if check_password_hash(user['password_hash'], password):
        return user
    return None


def update_user_profile(user_id: int, full_name: str, email: str) -> bool:
    clean_email = email.strip().lower()
    existing = get_user_by_email(clean_email)
    if existing and existing['id'] != user_id:
        raise ValueError(f"Email '{clean_email}' is already in use by another account.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET full_name = ?, email = ? WHERE id = ?
        ''', (full_name.strip(), clean_email, user_id))
        conn.commit()
        return cursor.rowcount > 0


def update_user_password(user_id: int, new_password_hash: str) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET password_hash = ? WHERE id = ?
        ''', (new_password_hash, user_id))
        conn.commit()
        return cursor.rowcount > 0


def change_user_password(user_id: int, new_password: str) -> bool:
    from werkzeug.security import generate_password_hash
    return update_user_password(user_id, generate_password_hash(new_password))


# ==========================================
# FARM CRUD OPERATIONS (USER ISOLATED)
# ==========================================

def list_farms(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT f.*,
                   (SELECT COUNT(*) FROM scans s WHERE s.farm_id = f.id) as scan_count,
                   (SELECT COUNT(*) FROM scans s WHERE s.farm_id = f.id AND s.is_healthy = 0 AND s.prediction_label != 'No clear disease found') as disease_scan_count
            FROM farms f
            WHERE 1=1
        '''
        params: List[Any] = []
        if user_id is not None:
            # Show farms belonging to this user, plus unassigned legacy farms
            query += ' AND (f.user_id = ? OR f.user_id IS NULL)'
            params.append(user_id)

        query += ' ORDER BY f.created_at DESC'
        rows = cursor.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_farm(farm_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT f.*,
                   (SELECT COUNT(*) FROM scans s WHERE s.farm_id = f.id) as scan_count
            FROM farms f
            WHERE f.id = ?
        '''
        params: List[Any] = [farm_id]
        if user_id is not None:
            query += ' AND (f.user_id = ? OR f.user_id IS NULL)'
            params.append(user_id)

        row = cursor.execute(query, params).fetchone()
        return dict(row) if row else None


def create_farm(name: str, location: str = '', size: str = '', variety: str = '',
                planting_date: str = '', plant_count: int = 0, notes: str = '',
                user_id: Optional[int] = None) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO farms (user_id, name, location, size, variety, planting_date, plant_count, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (user_id, name.strip(), location.strip(), size.strip(), variety.strip(), planting_date.strip(), plant_count, notes.strip()))
        conn.commit()
        return cursor.lastrowid


def update_farm(farm_id: int, name: str, location: str = '', size: str = '', variety: str = '',
                planting_date: str = '', plant_count: int = 0, notes: str = '',
                user_id: Optional[int] = None) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = '''
            UPDATE farms
            SET name = ?, location = ?, size = ?, variety = ?, planting_date = ?, plant_count = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''
        params = [name.strip(), location.strip(), size.strip(), variety.strip(), planting_date.strip(), plant_count, notes.strip(), farm_id]
        if user_id is not None:
            query += ' AND (user_id = ? OR user_id IS NULL)'
            params.append(user_id)

        cursor.execute(query, params)
        farm_updated = (cursor.rowcount > 0)
        if farm_updated:
            cursor.execute('UPDATE scans SET farm_name = ? WHERE farm_id = ?', (name.strip(), farm_id))
        conn.commit()
        return farm_updated


def delete_farm(farm_id: int, user_id: Optional[int] = None) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        check_query = 'SELECT id FROM farms WHERE id = ?'
        check_params: List[Any] = [farm_id]
        if user_id is not None:
            check_query += ' AND (user_id = ? OR user_id IS NULL)'
            check_params.append(user_id)

        farm = cursor.execute(check_query, check_params).fetchone()
        if not farm:
            return False

        cursor.execute("UPDATE scans SET farm_name = farm_name || ' (Archived)' WHERE farm_id = ?", (farm_id,))
        cursor.execute('DELETE FROM farms WHERE id = ?', (farm_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==========================================
# SCAN CRUD OPERATIONS (USER ISOLATED)
# ==========================================

def save_scan(image_filename: str, prediction_label: str, is_healthy: bool,
              confidence: float, disease_name: str, disease_type: str,
              disease_summary: str, disease_cause: str, raw_data: Dict[str, Any],
              farm_id: Optional[int] = None, user_id: Optional[int] = None,
              platform: str = 'web', model_name: str = 'tomato_disease_model.h5',
              sync_id: Optional[str] = None) -> int:
    farm_name = 'General / Unassigned'
    if farm_id:
        farm = get_farm(farm_id, user_id=user_id)
        if farm:
            farm_name = farm['name']
        else:
            farm_id = None

    raw_json = json.dumps(raw_data)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scans (
                user_id, farm_id, farm_name, image_filename, prediction_label,
                is_healthy, confidence, disease_name, disease_type,
                disease_summary, disease_cause, raw_json, platform, model_name, sync_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_id, farm_id, farm_name, image_filename, prediction_label,
            1 if is_healthy else 0, round(confidence, 1), disease_name,
            disease_type, disease_summary, disease_cause, raw_json,
            platform, model_name, sync_id
        ))
        conn.commit()
        return cursor.lastrowid


def get_scan_by_sync_id(sync_id: str) -> Optional[Dict[str, Any]]:
    if not sync_id:
        return None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute('SELECT * FROM scans WHERE sync_id = ?', (sync_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data['raw_json'] = json.loads(data['raw_json']) if data['raw_json'] else {}
        except Exception:
            data['raw_json'] = {}
        return data


def list_scans(search: Optional[str] = None, status_filter: Optional[str] = None,
               farm_id: Optional[int] = None, sort_order: str = 'newest',
               limit: int = 100, offset: int = 0, user_id: Optional[int] = None,
               date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM scans WHERE 1=1'
        params: List[Any] = []

        if user_id is not None:
            query += ' AND (user_id = ? OR user_id IS NULL)'
            params.append(user_id)

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
        elif status_filter == 'early_blight':
            query += " AND (prediction_label LIKE '%Early Blight%' OR disease_name LIKE '%Early Blight%')"
        elif status_filter == 'late_blight':
            query += " AND (prediction_label LIKE '%Late Blight%' OR disease_name LIKE '%Late Blight%')"

        if farm_id is not None:
            query += ' AND farm_id = ?'
            params.append(farm_id)

        if date_from:
            query += ' AND date(created_at) >= date(?)'
            params.append(date_from)
        if date_to:
            query += ' AND date(created_at) <= date(?)'
            params.append(date_to)

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


def get_scan(scan_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM scans WHERE id = ?'
        params: List[Any] = [scan_id]
        if user_id is not None:
            query += ' AND (user_id = ? OR user_id IS NULL)'
            params.append(user_id)

        row = cursor.execute(query, params).fetchone()
        if not row:
            return None
        data = dict(row)
        try:
            data['raw_json'] = json.loads(data['raw_json']) if data['raw_json'] else {}
        except Exception:
            data['raw_json'] = {}
        return data


def delete_scan(scan_id: int, user_id: Optional[int] = None) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = 'SELECT image_filename FROM scans WHERE id = ?'
        params: List[Any] = [scan_id]
        if user_id is not None:
            query += ' AND (user_id = ? OR user_id IS NULL)'
            params.append(user_id)

        scan = cursor.execute(query, params).fetchone()
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


def clear_scans(user_id: Optional[int] = None) -> int:
    """Safely delete all scan records and associated uploaded image files for a user (or all if user_id is None)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id is not None:
            rows = cursor.execute('SELECT image_filename FROM scans WHERE user_id = ? OR user_id IS NULL', (user_id,)).fetchall()
            cursor.execute('DELETE FROM scans WHERE user_id = ? OR user_id IS NULL', (user_id,))
        else:
            rows = cursor.execute('SELECT image_filename FROM scans').fetchall()
            cursor.execute('DELETE FROM scans')
        conn.commit()
        deleted_count = len(rows)

    # Clean up physical image files from disk
    for r in rows:
        filename = r['image_filename']
        if filename:
            filepath = os.path.join(UPLOADS_DIR, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass

    return deleted_count


# ==========================================
# CROP MONITORING & DASHBOARD METRICS
# ==========================================

def get_dashboard_stats(user_id: Optional[int] = None, farm_id: Optional[int] = None,
                        date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Build dynamic where clause for scans
        where_clauses = ['1=1']
        params: List[Any] = []

        if user_id is not None:
            where_clauses.append('(user_id = ? OR user_id IS NULL)')
            params.append(user_id)

        if farm_id is not None:
            where_clauses.append('farm_id = ?')
            params.append(farm_id)

        if date_from:
            where_clauses.append('date(created_at) >= date(?)')
            params.append(date_from)

        if date_to:
            where_clauses.append('date(created_at) <= date(?)')
            params.append(date_to)

        where_sql = ' AND '.join(where_clauses)

        # Farm count (user scoped)
        farm_params = [user_id] if user_id is not None else []
        farm_query = 'SELECT COUNT(*) as c FROM farms'
        if user_id is not None:
            farm_query += ' WHERE (user_id = ? OR user_id IS NULL)'
        total_farms = cursor.execute(farm_query, farm_params).fetchone()['c']

        # Scan counts
        total_scans = cursor.execute(f'SELECT COUNT(*) as c FROM scans WHERE {where_sql}', params).fetchone()['c']
        healthy_scans = cursor.execute(f'SELECT COUNT(*) as c FROM scans WHERE is_healthy = 1 AND {where_sql}', params).fetchone()['c']
        disease_scans = cursor.execute(
            f"SELECT COUNT(*) as c FROM scans WHERE is_healthy = 0 AND prediction_label != 'No clear disease found' AND {where_sql}", params
        ).fetchone()['c']
        unclear_scans = cursor.execute(
            f"SELECT COUNT(*) as c FROM scans WHERE prediction_label = 'No clear disease found' AND {where_sql}", params
        ).fetchone()['c']

        early_blight_scans = cursor.execute(
            f"SELECT COUNT(*) as c FROM scans WHERE (prediction_label LIKE '%Early Blight%' OR disease_name LIKE '%Early Blight%') AND {where_sql}", params
        ).fetchone()['c']
        late_blight_scans = cursor.execute(
            f"SELECT COUNT(*) as c FROM scans WHERE (prediction_label LIKE '%Late Blight%' OR disease_name LIKE '%Late Blight%') AND {where_sql}", params
        ).fetchone()['c']

        # Most frequently detected diseases
        top_diseases_rows = cursor.execute(f'''
            SELECT disease_name, COUNT(*) as count
            FROM scans
            WHERE is_healthy = 0 AND prediction_label != 'No clear disease found' AND disease_name IS NOT NULL AND {where_sql}
            GROUP BY disease_name
            ORDER BY count DESC
            LIMIT 6
        ''', params).fetchall()
        top_diseases = [dict(r) for r in top_diseases_rows]

        # Farm-specific disease breakdown
        farm_breakdown_rows = cursor.execute(f'''
            SELECT farm_name,
                   COUNT(*) as total,
                   SUM(CASE WHEN is_healthy = 1 THEN 1 ELSE 0 END) as healthy,
                   SUM(CASE WHEN is_healthy = 0 AND prediction_label != 'No clear disease found' THEN 1 ELSE 0 END) as disease,
                   SUM(CASE WHEN prediction_label LIKE '%Early Blight%' OR disease_name LIKE '%Early Blight%' THEN 1 ELSE 0 END) as early_blight,
                   SUM(CASE WHEN prediction_label LIKE '%Late Blight%' OR disease_name LIKE '%Late Blight%' THEN 1 ELSE 0 END) as late_blight
            FROM scans
            WHERE {where_sql}
            GROUP BY farm_name
            ORDER BY total DESC
            LIMIT 8
        ''', params).fetchall()
        farm_breakdown = [dict(r) for r in farm_breakdown_rows]

        # Activity timeline - scans grouped by day for the MOST RECENT 14 active days
        timeline_rows = cursor.execute(f'''
            SELECT * FROM (
                SELECT substr(created_at, 1, 10) as scan_date,
                       COUNT(*) as total,
                       SUM(CASE WHEN is_healthy = 1 THEN 1 ELSE 0 END) as healthy,
                       SUM(CASE WHEN is_healthy = 0 AND prediction_label != 'No clear disease found' THEN 1 ELSE 0 END) as disease
                FROM scans
                WHERE {where_sql}
                GROUP BY substr(created_at, 1, 10)
                ORDER BY scan_date DESC
                LIMIT 14
            ) ORDER BY scan_date ASC
        ''', params).fetchall()
        timeline = [dict(r) for r in timeline_rows]

        # Recent scans (up to 8)
        recent_rows = cursor.execute(f'''
            SELECT id, farm_name, image_filename, prediction_label, is_healthy, confidence, disease_name, created_at, platform
            FROM scans
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT 8
        ''', params).fetchall()
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
            if late_blight_scans > 0:
                alerts.append({
                    'level': 'danger',
                    'title': f'Urgent Alert: {late_blight_scans} Late Blight case{"s" if late_blight_scans != 1 else ""} detected',
                    'message': 'Late Blight progresses rapidly in moist weather. Inspect affected plots immediately and implement containment measures.'
                })
            if early_blight_scans > 0:
                alerts.append({
                    'level': 'warning',
                    'title': f'{early_blight_scans} Early Blight detection{"s" if early_blight_scans != 1 else ""} on record',
                    'message': 'Prune affected lower leaves and monitor soil moisture to prevent fungal spread.'
                })
            if healthy_scans == total_scans and total_scans > 0:
                alerts.append({
                    'level': 'success',
                    'title': 'Optimal Crop Foliage Health',
                    'message': 'All recorded inspections are healthy! Continue preventative watering and crop rotation practices.'
                })

        return {
            'total_farms': total_farms,
            'total_scans': total_scans,
            'healthy_scans': healthy_scans,
            'disease_scans': disease_scans,
            'early_blight_scans': early_blight_scans,
            'late_blight_scans': late_blight_scans,
            'unclear_scans': unclear_scans,
            'healthy_percentage': round((healthy_scans / total_scans * 100), 1) if total_scans > 0 else 0,
            'disease_percentage': round((disease_scans / total_scans * 100), 1) if total_scans > 0 else 0,
            'top_diseases': top_diseases,
            'farm_breakdown': farm_breakdown,
            'timeline': timeline,
            'recent_scans': recent_scans,
            'alerts': alerts,
        }
