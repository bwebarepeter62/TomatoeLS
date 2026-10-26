"""
WSGI entry point for production deployment on Render, Gunicorn, Waitress.
"""
import os
import sys
import importlib.util

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'web-app', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Dynamically load the backend app
_backend_app_path = os.path.join(BACKEND_DIR, 'app.py')
_spec = importlib.util.spec_from_file_location('backend_app', _backend_app_path)
_backend_module = importlib.util.module_from_spec(_spec)
sys.modules['backend_app'] = _backend_module
_spec.loader.exec_module(_backend_module)

app = _backend_module.app

if __name__ == '__main__':
    app.run()
