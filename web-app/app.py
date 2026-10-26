import os
import sys
import importlib.util

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

_backend_app_path = os.path.join(BACKEND_DIR, 'app.py')
_spec = importlib.util.spec_from_file_location('backend_app', _backend_app_path)
_backend_module = importlib.util.module_from_spec(_spec)
sys.modules['backend_app'] = _backend_module
_spec.loader.exec_module(_backend_module)

app = _backend_module.app

if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    app.run(host=host, port=port, debug=False)
