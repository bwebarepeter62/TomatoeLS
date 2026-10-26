"""
Tomato Leaf Scan — System Verification & Health Check Script
File: scripts/verify_system.py

Verifies:
1. Python runtime version.
2. Required dependencies (Flask, Pillow, numpy, tensorflow).
3. AI model weight presence and loadability.
4. Database connection and schema tables.
5. Directory structure and file access permissions.
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, '..'))
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'web-app', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def check_system():
    print("=" * 60)
    print("Tomato Leaf Scan — System Verification & Health Check")
    print("=" * 60)

    errors = []
    warnings = []

    # 1. Python Version
    py_ver = sys.version.split()[0]
    print(f"[INFO] Python Version: {py_ver}")
    if sys.version_info < (3, 10):
        errors.append(f"Python 3.10 or higher is required. Found: {py_ver}")

    # 2. Package Imports
    for pkg in ['flask', 'PIL', 'numpy', 'tensorflow', 'sqlite3']:
        try:
            __import__(pkg)
            print(f"[PASS] Package '{pkg}' is installed and importable.")
        except ImportError as e:
            errors.append(f"Missing required package: {pkg} ({e})")

    # 3. Model Verification
    try:
        import app
        model_path = app.MODEL_PATH
        if os.path.exists(model_path):
            size_mb = os.path.getsize(model_path) / (1024 * 1024)
            rel_path = os.path.relpath(model_path, PROJECT_ROOT)
            print(f"[PASS] AI Model found at {rel_path} ({size_mb:.2f} MB)")
            model = app.ensure_model_loaded()
            in_shape = getattr(model, 'input_shape', None)
            out_shape = getattr(model, 'output_shape', None)
            print(f"[PASS] Model loaded successfully: input {in_shape}, output {out_shape}")
        else:
            errors.append(f"AI Model file missing at: {model_path}")
    except Exception as exc:
        errors.append(f"Model verification failed: {exc}")

    # 4. Database Verification
    try:
        import db
        db.init_db()
        farms = db.list_farms()
        scans = db.list_scans(limit=5)
        print("[PASS] SQLite Database initialized at web-app/database/leafscan.db")
        print(f"       Registered farms: {len(farms)} | Recorded scans: {len(scans)}")
    except Exception as exc:
        errors.append(f"Database verification failed: {exc}")

    # 5. Frontend Templates & Static
    tpl_dir = os.path.join(PROJECT_ROOT, 'web-app', 'frontend', 'templates')
    static_dir = os.path.join(PROJECT_ROOT, 'web-app', 'frontend', 'static')
    if os.path.exists(tpl_dir) and len(os.listdir(tpl_dir)) >= 5:
        print(f"[PASS] Frontend templates verified ({len(os.listdir(tpl_dir))} templates found)")
    else:
        errors.append("Frontend templates directory missing or incomplete.")

    if os.path.exists(static_dir):
        print("[PASS] Frontend static directory verified")
    else:
        errors.append("Frontend static directory missing.")

    # 6. Summary
    print("=" * 60)
    if errors:
        print(f"[FAILED] {len(errors)} issues detected:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("[SUCCESS] All system components are verified and operational!")
        if warnings:
            for w in warnings:
                print(f"  [WARNING] {w}")
        print("=" * 60)


if __name__ == '__main__':
    check_system()
