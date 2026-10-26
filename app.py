"""
Tomato Leaf Scan — Root Web Entry Point
=======================================
This root-level entry point delegates execution to the organized backend in:
    web-app/backend/app.py

You can run the web server either by executing this file:
    python app.py
or directly from the web-app folder:
    cd web-app
    python backend/app.py
or by running:
    start_app.bat
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'web-app', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import app

if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    app.run(host=host, port=port, debug=False)
