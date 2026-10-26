# LeafScan System: Implementation & Verification Status

This document establishes the verified operational status of every component, feature, route, and asset in the **LeafScan** (Tomato Leaf Scan) repository as of October 2026.

Every claim in this document is backed by direct code inspection and actual test execution in the local Windows environment (Python 3.11.9).

---

## 1. Executive Summary of Verifications

| Component | Status | Verification Evidence | Notes / Discrepancies |
|---|---|---|---|
| **Web Application (Flask Backend)** | **IMPLEMENTED & VERIFIED** | Ran `python scripts/verify_system.py` and `python web-app/tests/test_app.py` (54/54 passed). | Routes `/`, `/scan`, `/farms`, `/monitoring`, `/history`, and `/health` work as expected. |
| **Relational Database (SQLite)** | **IMPLEMENTED & VERIFIED** | Live database `web-app/database/leafscan.db` inspected. Foreign keys, indexes, and CRUD verified. | Farm CRUD, scan logging, image file cleanup on deletion all operational. |
| **Web AI Model (`tomato_disease_model.h5`)** | **IMPLEMENTED & VERIFIED** | Loaded via Keras: input `(None, 224, 224, 3)`, output `(None, 3)`. | **3 Classes**: Early Blight, Late Blight, Healthy Leaf. Uses custom layers `TrueDivide` & `Subtract`. |
| **Mobile App (Flutter / Dart)** | **IMPLEMENTED (STANDALONE)** | Inspected `pubspec.yaml`, `main.dart`, `detector.dart`, `chat.dart`. | **100% on-device edge AI**. Does NOT connect to the Flask server. Has DeepSeek AI chat with offline fallback. |
| **Mobile AI Model (`best_int8.tflite`)** | **IMPLEMENTED (STANDALONE)** | File exists (26.5 MB). 15-class YOLOv8 object detector with NMS in Dart. | Completely different model architecture and class taxonomy than the web app. |
| **Automated Test Suite (`test_app.py`)** | **IMPLEMENTED & VERIFIED** | Executed: 54/54 assertions passed synchronously. | Runs in an isolated `tempfile` environment without mutating production data. |
| **Legacy Test Suite (`test_prediction.py`)** | **BROKEN / OUT OF DATE** | Executed: 8 failures, 9 errors out of 23 tests. | Was written for the 15-class YOLOv8 model; fails because `app.py` was switched to 3-class H5. |
| **Model Evaluation Script (`evaluate_model.py`)** | **BROKEN / OUT OF DATE** | Code inspection shows it calls `backend.score_classes()`. | Attribute missing in current `app.py`. Requires the 15-class TFLite backend shim. |
| **Model Training Pipeline** | **MISSING FROM REPO** | No training code, loss curves, or raw training scripts present. | Both models (`.h5` and `.tflite`) are pre-compiled export binaries. |

---

## 2. Feature-by-Feature Detailed Status

### A. Web Frontend (Presentation Layer)
- [x] **Landing Page (`home.html` / `/`):** Fully implemented. Renders hero visual, platform features, how-it-works workflow, and navigation links. Verified via HTTP 200 and DOM element assertions.
- [x] **AI Leaf Scanner Page (`scan.html` / `/scan`):** Fully implemented. Image file selector (PNG, JPG, WEBP), client-side file-type validation, instant browser preview using `URL.createObjectURL()`, optional farm plot dropdown selector, submit animation, diagnosis summary card, confidence percentage, and actionable treatment guidance list.
- [x] **Tomato Farm Management (`farms.html` / `/farms`):** Fully implemented. Modal dialog for creating and editing farms (name, location, size, variety, planting date, plant count, notes), live statistics cards (total farms, total plants, varieties), farm card grid with scan counts, and farm deletion.
- [x] **Crop Monitoring Dashboard (`monitoring.html` / `/monitoring`):** Fully implemented. 4 KPI metric cards (Total Farms, Total Scans, Healthy Scans %, Disease Scans %), interactive Chart.js doughnut chart (Health Distribution) and bar/line charts, contextual urgent disease warning banners, recent scan activity feed, and empty states.
- [x] **Scan Diagnostic History (`history.html` / `/history`):** Fully implemented. Filter toolbar with live text search, diagnosis status filter (Healthy / Disease / Unclear), farm plot filter, sort order (Newest / Oldest), responsive grid of scan cards, and detail modal showing the full stored JSON recommendations.
- [x] **Client-Side Notification Toasts:** Fully implemented in `base.html` via dynamic DOM injection with automated slide-in and fade-out timer.

### B. Web Backend & APIs (Application Layer)
- [x] **Flask Application Server (`web-app/backend/app.py`):** Fully implemented. Modular path resolution, static/template folder binding, and unified JSON error handling.
- [x] **Health Check Endpoint (`GET /health`):** Fully implemented. Returns status, Python version, model path, model file existence boolean, and database initialized boolean.
- [x] **Prediction Endpoint (`POST /api/predict`):** Fully implemented. Accepts multipart form data (`image` and optional `farm_id`), validates image using Pillow, converts to RGB, resizes to $224 \times 224$, runs inference through Keras MobileNetV2 `.h5`, saves file to `static/uploads/`, persists audit record to SQLite `scans` table, and returns complete diagnosis payload.
- [x] **Farm Management CRUD Endpoints:**
  - `GET /api/farms` — Lists all registered farms with scan counts and disease counts.
  - `POST /api/farms` — Creates a new farm plot.
  - `GET /api/farms/<id>` — Retrieves single farm plot metadata.
  - `PUT /api/farms/<id>` — Updates farm plot metadata and retroactively updates scan records.
  - `DELETE /api/farms/<id>` — Deletes farm plot, setting associated scans to archived (`farm_id = NULL`).
- [x] **Scan History & Audit Endpoints:**
  - `GET /api/scans` — Supports search query, status filter, farm filter, sort order, and pagination (`limit`, `offset`).
  - `GET /api/scans/<id>` — Retrieves single scan with decoded raw JSON treatment advice.
  - `DELETE /api/scans/<id>` — Deletes scan record from database AND safely unlinks physical leaf photo from `static/uploads/` if unreferenced.
- [x] **Dashboard Statistics Endpoint (`GET /api/dashboard/stats`):** Fully implemented. Aggregates farm counts, total scans, healthy vs disease counts, top 5 detected diseases, 14-day timeline activity, and urgent disease alert generation.

### C. Database & Data Storage Layer
- [x] **SQLite Database Engine (`web-app/database/leafscan.db`):** Fully implemented. Uses Python `sqlite3` standard library with `sqlite3.Row` factory.
- [x] **Context Manager Connection Pool (`get_db_connection`):** Fully implemented. Automatically enforces `PRAGMA foreign_keys = ON`, commits transactions on success, rolls back on exception, and guarantees file descriptor closure (preventing Windows file-lock contention).
- [x] **Database Tables (`farms`, `scans`):** Fully implemented. Defined with `INTEGER PRIMARY KEY AUTOINCREMENT`, timestamps, and foreign key constraint (`ON DELETE SET NULL`).
- [x] **Performance Indexes:** Fully implemented (`idx_scans_farm_id`, `idx_scans_created_at`, `idx_scans_is_healthy`).
- [x] **Database Reset & Backup Utility (`reset_db()`):** Fully implemented. Creates timestamped backup before schema wipe and cleans orphaned upload images.

### D. Artificial Intelligence & Computer Vision
- [x] **Web Inference Pipeline:** Fully implemented using TensorFlow/Keras CPU. Loads `tomato_disease_model.h5` with custom scaling layers `TrueDivide` and `Subtract`. Evaluates 3 classes: Early Blight, Late Blight, Healthy Leaf.
- [x] **Confidence Thresholding:** Fully implemented ($0.50$ threshold). Flags low-confidence predictions as "No clear disease found".
- [x] **Mobile Edge AI Pipeline:** Fully implemented in Dart/Flutter. Uses `tflite_flutter` to load `best_int8.tflite` (YOLOv8 INT8 quantized). Parses 8,400 multi-scale candidate anchors across 15 foliar classes, computes IoU, and performs Non-Maximum Suppression (NMS) directly on-device.
- [ ] **Dual-Model Parity (Web vs Mobile):** **DISCREPANT / DIVERGENT**. The web application uses a 3-class classification model (`.h5`), whereas the mobile application uses a 15-class object detection model (`.tflite`). They do not share weights, class taxonomies, or input tensor shapes.
- [ ] **Model Training Scripts & Notebooks:** **MISSING FROM REPOSITORY**. Neither the Google Colab notebook nor the local Python training scripts used to generate `tomato_disease_model.h5` or `best_int8.tflite` are present in this repository.
- [x] **Evaluation Dataset Downloads (`ai-model/download_eval_samples.py`):** Fully implemented. Downloads PlantVillage (lab) and PlantDoc (field) sample images via GitHub API. Verified present in `ai-model/eval_data` (180 files) and `ai-model/eval_data_field` (233 files).
- [ ] **Model Evaluation Script (`ai-model/evaluate_model.py`):** **BROKEN / UNVERIFIED**. Written against the 15-class TFLite backend interface; currently crashes when importing from `app.py`.

### E. Mobile Application (Flutter)
- [x] **Flutter Client Architecture (`mobile-app/`):** Fully implemented. Cross-platform codebase supporting Android, iOS, Windows, macOS, Linux, and Web.
- [x] **Offline-First Camera / Gallery Scanner:** Fully implemented via `image_picker` and `tflite_flutter`.
- [x] **On-Device Bounding Box Visualization:** Fully implemented via CustomPainter in `detection_image.dart`.
- [x] **Agronomic Treatment Knowledge Base (`disease_info.dart`):** Fully implemented. Structured offline repository containing causes, immediate containment steps, prevention, and chemical/organic treatments for all 15 conditions.
- [x] **AI Agronomist Chat Assistant (`chat.dart`):** Fully implemented. Connects to the DeepSeek Chat API (`api.deepseek.com`) when an API key is provided, and gracefully degrades to an intelligent rule-based offline expert assistant when offline.
- [ ] **Mobile-to-Backend Sync:** **NOT IMPLEMENTED**. The mobile app does NOT send scan logs, photos, or farm data to the Flask server. It operates as an independent edge diagnostic utility.

---

## 3. Discovered Technical Debt & Issues

1. **Model & Architecture Divergence:**
   The documentation in `README.md` and `docs/` states that the platform uses an INT8 YOLOv8 model for 15 classes. In reality, the web app backend was switched to a 3-class MobileNetV2 Keras model (`tomato_disease_model.h5`), while only the mobile app uses the 15-class YOLOv8 model.
2. **Broken Prediction Test Suite (`test_prediction.py`):**
   `test_prediction.py` tests against the 15-class YOLOv8 model and fails because `web-app/backend/app.py` now implements the 3-class model.
3. **Broken Evaluation Script (`ai-model/evaluate_model.py`):**
   Calls `backend.score_classes()`, which was removed from `app.py`.
4. **No Authentication or Authorization:**
   All web API endpoints (`/api/farms`, `/api/scans`, `/api/predict`) are completely unauthenticated. Any user who can access the web port can create, read, update, or delete any farm or scan.
5. **No Mobile Syncing:**
   Farmers using the mobile app cannot synchronize their field scans with the web app's Farm Management or Crop Monitoring dashboard.
