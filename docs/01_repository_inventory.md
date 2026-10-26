# Phase One: Complete Repository Inventory & Component Catalog

**Document:** `docs/01_repository_inventory.md`  
**System:** LeafScan (Tomato Leaf Scan) AI Crop Health Platform  
**Target Audience:** Beginner to Intermediate Software & ML Engineers  

---

## 1. Project Directory Overview

The LeafScan codebase is organized into four main functional tiers (Web Application, Mobile Client, AI Model Assets, and Automation Scripts) plus root launchers and documentation:

```text
D:\projects\blight\Leafscan-main\
├── app.py                          # Root Python entry point (delegates to web-app/backend/app.py)
├── db.py                           # Root database shim (re-exports web-app/backend/db.py)
├── test_app.py                     # Root test runner shim (delegates to web-app/tests/test_app.py)
├── requirements.txt                # Pinned Python package dependencies for the web server
├── start_app.bat                   # Master Windows batch launcher
├── README.md                       # High-level executive overview and setup instructions
├── Tomato Vision Scanner Icon.png  # Graphic branding asset (1.16 MB)
│
├── web-app/                        # Full-Stack Web Application (Flask + SQLite + Jinja2 + Keras)
│   ├── .env.example                # Environment variable configuration template
│   ├── README.md                   # Web-app specific documentation and API guidelines
│   ├── requirements.txt            # Package manifest matching root requirements
│   ├── start_app.bat               # Web launcher executing web-app/backend/app.py
│   ├── backend/                    # Python Application Controllers & Model Inference
│   │   ├── app.py                  # Main Flask server, routing controllers, and AI inference pipeline
│   │   ├── app.py.bak_before_diagnosis # Historical backup before switching to 3-class .h5 model
│   │   ├── db.py                   # SQLite connection context manager, CRUD operations, KPI analytics
│   │   └── tomato_disease_model.h5 # Keras H5 binary neural network weights (23.26 MB)
│   ├── database/                   # Relational Persistence Layer
│   │   ├── leafscan.db             # Active SQLite database file
│   │   ├── leafscan_backup_20261020_084358.db # Timestamped database backup created by reset_db()
│   │   ├── schema.sql              # Raw SQL table definitions and performance indexes
│   │   └── README.md               # Database entity-relationship documentation
│   ├── frontend/                   # Client-Side Presentation Layer
│   │   ├── static/
│   │   │   ├── css/styles.css      # CSS design system (tokens, glassmorphism, responsive grid)
│   │   │   ├── js/app.js           # Scanner page client logic (upload preview, API fetch, render)
│   │   │   ├── images/hero-tomato.jpg # High-resolution hero banner for landing page
│   │   │   └── uploads/            # Persistent leaf inspection images saved during user scans
│   │   └── templates/              # Jinja2 HTML5 view templates
│   │       ├── base.html           # Master layout with topbar navigation and footer
│   │       ├── home.html           # Platform overview and feature breakdown
│   │       ├── scan.html           # AI leaf scanner interface and treatment display
│   │       ├── farms.html          # Multi-farm plot registration and management
│   │       ├── monitoring.html     # Chart.js analytics dashboard and health trends
│   │       ├── history.html        # Searchable and filterable diagnostic scan archive
│   │       └── index.html          # Redirect helper to home view
│   └── tests/                      # Automated Web Test Suites
│       ├── test_app.py             # 54-point synchronous integration test suite (PASSES)
│       └── test_prediction.py      # Unittest suite for legacy 15-class TFLite model (FAILS)
│
├── mobile-app/                     # Cross-Platform Flutter Client (Dart)
│   ├── pubspec.yaml                # Flutter project definition, dependencies, and asset declarations
│   ├── pubspec.lock                # Pinned dependency lockfile
│   ├── analysis_options.yaml       # Dart static analyzer linting rules
│   ├── README.md                   # Mobile installation, build instructions, and architecture guide
│   ├── lib/                        # Dart source code
│   │   ├── main.dart               # App entry point, State management, Tab navigation, Scan orchestration
│   │   ├── models/
│   │   │   ├── detector.dart       # On-device TFLite runner, anchor decoding, and NMS calculation
│   │   │   └── disease_info.dart   # Agronomic disease catalog (15 conditions + healthy)
│   │   ├── services/
│   │   │   └── chat.dart           # DeepSeek cloud API client with offline fallback assistant
│   │   └── widgets/
│   │       └── detection_image.dart# CustomPainter rendering normalized bounding boxes over image
│   ├── assets/                     # Packaged mobile runtime assets
│   │   ├── models/best_int8.tflite # INT8-quantized YOLOv8 object detector model (26.5 MB)
│   │   ├── google_fonts/           # Bundled DM Sans font files for 100% offline typography
│   │   ├── icon/                   # App launcher icons
│   │   └── favicon/                # Web favicons
│   ├── test/                       # Unit tests for Dart widgets and logic
│   └── android/ ios/ windows/ ...  # Platform-specific native host wrappers
│
├── ai-model/                       # AI Model Assets & Benchmarking Scripts
│   ├── README.md                   # Model architecture, tensor specifications, and class taxonomy
│   ├── download_eval_samples.py    # Fetches ground truth images from PlantVillage and PlantDoc
│   ├── evaluate_model.py           # Benchmark script calculating recall and false alarms
│   ├── models/
│   │   └── best_int8.tflite        # Master copy of the INT8 YOLOv8 model (26.5 MB)
│   ├── eval_data/                  # Downloaded PlantVillage laboratory samples (180 images)
│   └── eval_data_field/            # Downloaded PlantDoc field photos (233 images)
│
├── scripts/                        # Maintenance & Verification Scripts
│   ├── verify_system.py            # Comprehensive system health check (Python, TF, DB, templates)
│   ├── reset_db.py                 # Database wipe utility with automated backup and image cleanup
│   └── run_tests.bat               # Windows batch shortcut executing web-app/tests/test_app.py
│
└── docs/                           # Documentation Suite
    ├── README.md                   # Documentation index and recommended reading order
    ├── IMPLEMENTATION_STATUS.md    # Feature operational status matrix
    ├── DEPENDENCY_MAP.md           # Component relationship and dependency map
    ├── OPEN_QUESTIONS.md           # Unresolved technical questions and investigation guide
    ├── TECHNICAL_DOCUMENTATION.md  # 13-Chapter engineering reference manual
    ├── PROJECT_REPORT_DRAFT.md     # 5-Chapter academic undergraduate dissertation draft
    ├── REPORT_COMPLETION_CHECKLIST.md # Actionable submission checklist
    └── DOCUMENTATION.md            # Original Flutter mobile reference manual
```

---

## 2. Component Categorization & Inventory

### A. Web Frontend (Presentation Layer)
| File Path | Technology | Purpose |
|---|---|---|
| `web-app/frontend/templates/base.html` | HTML5 / Jinja2 | Core site layout, responsive topbar header, brand identity, navigation links, footer, and notification toast container. |
| `web-app/frontend/templates/home.html` | HTML5 / Jinja2 | Welcome landing page explaining LeafScan features, crop monitoring highlights, and call-to-action buttons. |
| `web-app/frontend/templates/scan.html` | HTML5 / Jinja2 | Leaf inspection portal with drag-and-drop file upload, preview box, optional farm plot dropdown, and diagnosis card. |
| `web-app/frontend/templates/farms.html` | HTML5 / Jinja2 / Vanilla JS | Farm plot management view. Features a modal dialog for adding/editing farms, summary pills, and responsive farm cards. |
| `web-app/frontend/templates/monitoring.html` | HTML5 / Jinja2 / Chart.js | Visual analytics dashboard showing health distribution doughnut chart, 14-day scan history timeline, and urgent alerts. |
| `web-app/frontend/templates/history.html` | HTML5 / Jinja2 / Vanilla JS | Inspection audit log with text search, diagnosis status filters (healthy/disease/unclear), farm filters, and detail report modal. |
| `web-app/frontend/templates/index.html` | HTML5 / Jinja2 | Simple redirect view sending `/index` requests to `/`. |
| `web-app/frontend/static/css/styles.css` | Vanilla CSS | Complete design system using CSS custom properties (`--primary: #1b7a43`, `--bg: #f4f8f5`), cards, modals, tables, and animations. |
| `web-app/frontend/static/js/app.js` | Vanilla JavaScript (ES6) | Client logic for `scan.html`: handles file selection, client-side MIME validation, FormData creation, `fetch('/api/predict')`, and DOM rendering. |
| `web-app/frontend/static/images/hero-tomato.jpg` | JPEG Image | High-resolution hero graphic displayed on the landing page. |
| `web-app/frontend/static/uploads/` | JPEG/PNG/JFIF Files | Physical storage directory where uploaded tomato leaf photos are saved permanently. |

### B. Web Backend & Server (Application Layer)
| File Path | Technology | Purpose |
|---|---|---|
| `app.py` | Python 3.11 | Root entry point shim. Adds `web-app/backend` to `sys.path` and runs the Flask development server on `127.0.0.1:5000`. |
| `web-app/backend/app.py` | Python (Flask, Pillow, TensorFlow) | Primary server application. Defines all HTTP view routes and REST API endpoints. Loads the Keras model and coordinates inference. |
| `web-app/backend/db.py` | Python (`sqlite3`, `contextlib`) | Database access layer. Provides context-managed connections, schema initialization, farm CRUD, scan logging, and KPI aggregation. |
| `db.py` | Python | Root database shim re-exporting `web-app/backend/db.py`. |
| `web-app/backend/app.py.bak_before_diagnosis` | Python | Inactive backup file preserving the earlier 15-class TFLite implementation before the backend was switched to the 3-class H5 model. |

### C. Mobile Application (Flutter Client)
| File Path | Technology | Purpose |
|---|---|---|
| `mobile-app/lib/main.dart` | Dart / Flutter | Entry point (`main()`) and root widget (`LeafScanApp`). Implements an `IndexedStack` managing Home, Scan, Analysis, and Chat screens. |
| `mobile-app/lib/models/detector.dart` | Dart (`tflite_flutter`, `image`) | Core on-device edge AI detector. Loads `best_int8.tflite`, normalizes input, invokes the interpreter, decodes bounding boxes, and performs NMS. |
| `mobile-app/lib/models/disease_info.dart` | Dart | Self-contained agronomic database of 15 diseases and healthy foliage, specifying causes, symptoms, and organic/chemical treatments. |
| `mobile-app/lib/services/chat.dart` | Dart (`http`, `json`) | AI conversational assistant. Calls the remote DeepSeek API (`api.deepseek.com`) or falls back to an offline rule-based knowledge engine. |
| `mobile-app/lib/widgets/detection_image.dart` | Dart (Flutter `CustomPainter`) | Custom widget that renders the leaf photograph with color-coded bounding boxes and confidence badges drawn directly on top. |
| `mobile-app/pubspec.yaml` | YAML | Declares package dependencies (`tflite_flutter`, `image_picker`, `google_fonts`, `http`) and bundled asset paths. |
| `mobile-app/assets/models/best_int8.tflite` | TFLite Binary (26.5 MB) | Bundled INT8 quantized YOLOv8 neural network weights for edge inference. |
| `mobile-app/assets/google_fonts/` | TTF Font Files | Offline DM Sans font files ensuring the app renders beautiful typography without Internet access. |

### D. AI Models & Computer Vision Assets
| File Path | Type | Architecture | Specifications |
|---|---|---|---|
| `web-app/backend/tomato_disease_model.h5` | Keras H5 (23.26 MB) | MobileNetV2 with custom layers | Input: `(1, 224, 224, 3)` Float32 [0..255]. Output: `(1, 3)` Softmax probabilities. Classes: Early Blight, Late Blight, Healthy Leaf. |
| `ai-model/models/best_int8.tflite` | TensorFlow Lite (26.5 MB) | Ultralytics YOLOv8 (Single-Stage) | Input: `(1, 3, 640, 640)` Float32 [0..1] NCHW. Output: `(1, 19, 8400)`. Classes: 15 foliar conditions. |
| `mobile-app/assets/models/best_int8.tflite` | TensorFlow Lite (26.5 MB) | Ultralytics YOLOv8 (Single-Stage) | Identical duplicate of `ai-model/models/best_int8.tflite` bundled into the mobile app. |
| `ai-model/download_eval_samples.py` | Python Script | Data Ingestion | Downloads sample evaluation images from GitHub repositories (`PlantVillage` and `PlantDoc`). |
| `ai-model/evaluate_model.py` | Python Script | Model Evaluation | Computes recall and false-alarm rates against ground-truth directories. (Legacy). |
| `ai-model/eval_data/` | Directory (180 files) | Evaluation Images | Ground truth lab samples from PlantVillage (60 Early Blight, 60 Late Blight, 60 Healthy). |
| `ai-model/eval_data_field/` | Directory (233 files) | Evaluation Images | Ground truth field photos from PlantDoc (80 Early Blight, 92 Late Blight, 61 Healthy). |

### E. Relational Database Layer
| File Path | Technology | Purpose |
|---|---|---|
| `web-app/database/leafscan.db` | SQLite Database | Primary relational database file storing registered farm plots and scan records. |
| `web-app/database/schema.sql` | SQL DDL | Schema definition script containing `CREATE TABLE` and `CREATE INDEX` statements. |
| `web-app/database/leafscan_backup_20261020_084358.db` | SQLite Database | Timestamped backup copy generated before a previous database reset. |

### F. Automation, Testing, & Configuration Scripts
| File Path | Technology | Purpose |
|---|---|---|
| `scripts/verify_system.py` | Python | Performs a comprehensive 5-point environment health check: Python version, package imports, model loadability, database access, and templates. |
| `scripts/reset_db.py` | Python | Standalone CLI script to safely wipe the database, create a timestamped backup, and remove orphaned upload images. |
| `scripts/run_tests.bat` | Windows Batch | One-click launcher executing `web-app/tests/test_app.py`. |
| `web-app/tests/test_app.py` | Python (`unittest` / Flask Client) | Comprehensive 54-point synchronous integration test suite validating all routes, CRUD, inference, and file cleanup in an isolated temporary directory. |
| `web-app/tests/test_prediction.py` | Python (`unittest`) | Legacy unit test suite written for the 15-class TFLite model. (Currently failing). |
| `test_app.py` | Python | Root test runner shim delegating to `web-app/tests/test_app.py`. |
| `start_app.bat` | Windows Batch | Root launcher delegating to `web-app/start_app.bat`. |
| `web-app/start_app.bat` | Windows Batch | Validates Python environment and launches the Flask server. |
| `web-app/.env.example` | Configuration Template | Shows example environment variables (`FLASK_ENV`, `SECRET_KEY`, `PORT`). |

---

## 3. Component Entry Points: How Execution Begins

### 1. Web Application Entry Point
Execution begins in one of three ways:
1. **Executing `python app.py` from root:**
   - [app.py](file:///d:/projects/blight/Leafscan-main/app.py#L16-L28) calculates absolute paths, inserts `web-app/backend` into `sys.path`, imports `app` from `app.py`, and calls:
     ```python
     app.run(host='127.0.0.1', port=5000, debug=False)
     ```
2. **Executing `python web-app/backend/app.py` directly:**
   - [web-app/backend/app.py](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L41-L47) instantiates the Flask application:
     ```python
     app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)
     db.init_db()
     ```
   - It checks whether `LEAFSCAN_RESET_DB` is set, initializes the database tables, registers all HTTP routes, and begins listening for incoming HTTP connections on port `5000`.
3. **Double-clicking `start_app.bat`:**
   - Runs `web-app/start_app.bat`, opening the default browser to `http://127.0.0.1:5000` and starting the Python server.

### 2. Mobile Application Entry Point
Execution begins in [mobile-app/lib/main.dart](file:///d:/projects/blight/Leafscan-main/mobile-app/lib/main.dart#L12-L35):
1. `main()` sets `GoogleFonts.config.allowRuntimeFetching = false;` to guarantee full offline execution.
2. `runApp(const LeafScanApp());` initializes the Flutter widget tree.
3. `LeafScanApp` configures the Material 3 theme (using teal seed `#0B8379` and bundled DM Sans font) and renders `RootPage`.
4. `_RootPageState.initState()` triggers asynchronous model loading:
   ```dart
   await _detector.load();
   ```
   which initializes the TFLite runtime and loads `assets/models/best_int8.tflite` into phone memory.

### 3. Automated Test Suite Entry Point
Execution begins in [web-app/tests/test_app.py](file:///d:/projects/blight/Leafscan-main/web-app/tests/test_app.py#L18-L31):
1. `run_tests()` creates an isolated temporary directory via `tempfile.mkdtemp(prefix='leafscan_webtest_')`.
2. It overrides `db.DB_PATH`, `db.DATABASE_DIR`, and `app.UPLOADS_DIR` to point to the temporary directory, ensuring the live database is never touched.
3. `db.init_db()` constructs fresh SQLite tables.
4. `_run_tests()` instantiates `app.app.test_client()` and executes 54 assertions validating all routes, CRUD methods, prediction inferences, and safe file cleanups.
5. In a `finally:` block, it restores original path references and recursively deletes the temporary directory.
