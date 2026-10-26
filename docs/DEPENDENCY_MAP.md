# LeafScan: System Dependency Map & Component Relationships

This document details the dependencies, module interactions, and data-flow connections between all major files in the **LeafScan** repository.

---

## 1. High-Level Dependency Graph

```mermaid
graph TD
    subgraph Root Entry Shims
        RootApp["app.py (Root Launcher)"]
        RootDB["db.py (Root Shim)"]
        RootTest["test_app.py (Root Test Shim)"]
        StartBat["start_app.bat (Batch Launcher)"]
    end

    subgraph Web Application Backend
        FlaskServer["web-app/backend/app.py (Flask Controllers)"]
        DBLayer["web-app/backend/db.py (SQLite Data Access)"]
        WebModel["web-app/backend/tomato_disease_model.h5 (Keras Model)"]
    end

    subgraph Web Application Frontend
        Templates["web-app/frontend/templates/*.html"]
        AppJS["web-app/frontend/static/js/app.js"]
        StylesCSS["web-app/frontend/static/css/styles.css"]
        Uploads["web-app/frontend/static/uploads/*.jpg"]
    end

    subgraph Database Storage
        LeafscanDB["web-app/database/leafscan.db"]
        SchemaSQL["web-app/database/schema.sql"]
    end

    subgraph Mobile Application (Flutter)
        MainDart["mobile-app/lib/main.dart"]
        DetectorDart["mobile-app/lib/models/detector.dart"]
        DiseaseInfo["mobile-app/lib/models/disease_info.dart"]
        ChatService["mobile-app/lib/services/chat.dart"]
        MobileModel["mobile-app/assets/models/best_int8.tflite"]
        DeepSeekAPI["https://api.deepseek.com (Remote Cloud API)"]
    end

    subgraph Scripts & QA
        VerifyScript["scripts/verify_system.py"]
        WebTests["web-app/tests/test_app.py"]
        PredTests["web-app/tests/test_prediction.py (Legacy)"]
        EvalScript["ai-model/evaluate_model.py (Legacy)"]
    end

    %% Linkages
    RootApp -->|Imports and runs| FlaskServer
    RootDB -->|Re-exports| DBLayer
    RootTest -->|Delegates to| WebTests
    StartBat -->|Calls| FlaskServer

    FlaskServer -->|Imports CRUD helpers| DBLayer
    FlaskServer -->|Loads & executes| WebModel
    FlaskServer -->|Serves templates & assets| Templates
    FlaskServer -->|Saves images to| Uploads

    DBLayer -->|Reads & writes| LeafscanDB
    LeafscanDB -.->|Schema defined by| SchemaSQL

    Templates -->|Loads scripts| AppJS
    Templates -->|Loads stylesheets| StylesCSS
    AppJS -->|HTTP POST /api/predict| FlaskServer
    AppJS -->|HTTP GET /api/farms| FlaskServer

    MainDart -->|Uses| DetectorDart
    MainDart -->|Uses| DiseaseInfo
    MainDart -->|Uses| ChatService
    DetectorDart -->|Executes locally| MobileModel
    ChatService -->|Optional cloud queries| DeepSeekAPI

    VerifyScript -->|Inspects| FlaskServer
    VerifyScript -->|Inspects| DBLayer
    VerifyScript -->|Inspects| WebModel
    VerifyScript -->|Inspects| LeafscanDB

    WebTests -->|Tests endpoints against| FlaskServer
    WebTests -->|Tests CRUD against| DBLayer

    PredTests -.->|Broken expectation on| FlaskServer
    EvalScript -.->|Broken expectation on| FlaskServer
```

---

## 2. File-by-File Dependency Breakdown

### A. Root Directory
- **`app.py`**
  - **Depends on:** `sys`, `os`, `web-app/backend/app.py`.
  - **Depended on by:** End users executing `python app.py` from root.
  - **Purpose:** Adds `web-app/backend` to `sys.path` and runs the Flask development server on `127.0.0.1:5000`.
- **`db.py`**
  - **Depends on:** `sys`, `os`, `web-app/backend/db.py`.
  - **Depended on by:** Legacy root scripts or interactive terminal debugging sessions.
  - **Purpose:** Re-exports all functions from `web-app/backend/db.py`.
- **`test_app.py`**
  - **Depends on:** `web-app/tests/test_app.py`.
  - **Depended on by:** Users running `python test_app.py`.
  - **Purpose:** Invokes `web-app/tests/test_app.py:run_tests()`.
- **`start_app.bat`**
  - **Depends on:** `web-app/start_app.bat`.
  - **Purpose:** Windows double-click master launcher.
- **`requirements.txt` (Root & `web-app/`)**
  - **Packages:** `Flask==3.1.3`, `Pillow==12.3.0`, `numpy==2.4.6`, `tensorflow-cpu==2.16.2`.

---

### B. Web Backend (`web-app/backend/`)
- **`web-app/backend/app.py`**
  - **Dependencies (Internal):** `db.py`, `tomato_disease_model.h5`.
  - **Dependencies (Third-Party):** `flask` (`Flask`, `jsonify`, `redirect`, `render_template`, `request`, `url_for`), `PIL` (`Image`, `UnidentifiedImageError`), `numpy`, `tensorflow` (`tf.keras.models.load_model`).
  - **Depended on by:** Root `app.py`, `scripts/verify_system.py`, `web-app/tests/test_app.py`.
  - **Output Assets Generated:** Saves leaf image uploads to `web-app/frontend/static/uploads/leaf_<timestamp>_<uuid>.jpg`.
- **`web-app/backend/db.py`**
  - **Dependencies (Internal):** None.
  - **Dependencies (Standard Library):** `sqlite3`, `os`, `shutil`, `json`, `datetime`, `contextlib.contextmanager`, `typing`.
  - **Depended on by:** `app.py`, `scripts/reset_db.py`, `scripts/verify_system.py`, `web-app/tests/test_app.py`.
  - **Data Stores Touched:** Connects to `web-app/database/leafscan.db`. Safely unlinks images in `web-app/frontend/static/uploads/`.
- **`web-app/backend/tomato_disease_model.h5`**
  - **Architecture:** Keras Sequential / Functional MobileNetV2 with custom layers `TrueDivide` and `Subtract`.
  - **Input Tensor:** Float32 array shaped `(1, 224, 224, 3)`.
  - **Output Tensor:** Float32 array shaped `(1, 3)` (Softmax probabilities).

---

### C. Web Frontend (`web-app/frontend/`)
- **`templates/base.html`**
  - Shared master layout extended by `home.html`, `scan.html`, `farms.html`, `monitoring.html`, `history.html`.
  - Depends on CDN assets: Google Fonts (`Inter`), FontAwesome Icons v6 (`kit.fontawesome.com`), and static asset `/static/css/styles.css`.
- **`static/js/app.js`**
  - Executed on `scan.html`.
  - Communicates asynchronously via `fetch('/api/predict')` and `fetch('/api/farms')`.
  - Manipulates preview, submission state, error notices, and diagnosis cards in the DOM.
- **`templates/farms.html`**
  - Embedded client JS communicates with `/api/farms` (`GET`, `POST`, `PUT`, `DELETE`).
- **`templates/monitoring.html`**
  - Depends on CDN Chart.js (`cdn.jsdelivr.net/npm/chart.js@4.4.1`).
  - Embedded client JS communicates with `/api/dashboard/stats`.
- **`templates/history.html`**
  - Embedded client JS communicates with `/api/scans` (`GET`, `DELETE`) and `/api/farms` (`GET`).

---

### D. Mobile Application (`mobile-app/`)
- **`pubspec.yaml`**
  - Defines package dependencies: `flutter`, `cupertino_icons: ^1.0.6`, `tflite_flutter: ^0.12.1`, `image_picker: ^1.1.2`, `image: ^4.2.0`, `path_provider: ^2.1.4`, `google_fonts: ^6.2.1`, `http: ^1.2.2`.
  - Bundles assets: `assets/models/best_int8.tflite`, `assets/google_fonts/`.
- **`lib/main.dart`**
  - Mobile UI orchestrator. Uses `IndexedStack` to transition between Home, Scan, Analysis Result, and Chat.
  - Depends on `lib/models/detector.dart`, `lib/models/disease_info.dart`, `lib/services/chat.dart`, `lib/widgets/detection_image.dart`.
- **`lib/models/detector.dart`**
  - Depends on `tflite_flutter` and `package:image/image.dart`.
  - Loads `assets/models/best_int8.tflite`, converts input image to `(1, 3, 640, 640)`, decodes 8400 anchors, and executes Non-Maximum Suppression (NMS).
- **`lib/services/chat.dart`**
  - Depends on `package:http/http.dart` and `lib/models/disease_info.dart`.
  - Makes outbound HTTPS POST requests to `https://api.deepseek.com/chat/completions`.
  - Falls back to local rule-based responses in `answerQuestion()` when disconnected.

---

### E. AI Assets & Evaluation (`ai-model/`)
- **`ai-model/models/best_int8.tflite`**
  - Size: 26,525,590 bytes (~26.5 MB).
  - YOLOv8 architecture (15 tomato leaf classes, 8400 anchors).
  - Copied to `mobile-app/assets/models/best_int8.tflite`.
- **`ai-model/download_eval_samples.py`**
  - Standalone script using standard library `urllib` and `json`.
  - Downloads ground-truth evaluation images from GitHub repositories (`PlantVillage-Dataset` and `PlantDoc-Dataset`).
- **`ai-model/evaluate_model.py`**
  - Depended on `web-app/backend/app.py` when `app.py` was configured for the 15-class TFLite model. Currently incompatible with the 3-class `.h5` model.
