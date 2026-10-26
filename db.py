"""
Tomato Leaf Scan — Root Database Module Shim
============================================
Delegates database operations to:
    web-app/backend/db.py
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'web-app', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from db import *  # noqa: F401,F403  (intentional re-export of web-app/backend/db.py)
