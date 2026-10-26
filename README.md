# Tomato Leaf Scan — AI Crop Health Platform

> **An AI-Based Image Processing System for Early Tomato Leaf Disease Detection and Agronomic Farm Management**

---

## 🌟 Executive Summary

**Tomato Leaf Scan** is an intelligent agricultural technology platform engineered to help tomato farmers, agronomists, and agricultural extension officers detect crop pathologies early, prevent pathogen spread, and manage farm plot health.

The system combines:
1. **On-Device Computer Vision (AI/ML):** An INT8-quantized **Ultralytics YOLOv8** model running locally on commodity CPU hardware via **TensorFlow Lite**, capable of detecting and classifying 15 tomato foliar conditions and healthy foliage.
2. **Interactive Web Application:** A responsive **Python Flask** web platform with multi-farm plot management, live crop monitoring dashboards (Chart.js), and searchable diagnostic scan history.
3. **Cross-Platform Mobile Application:** A self-contained **Flutter** mobile client for offline smartphone edge detection.
4. **Relational Data Storage:** An embedded **SQLite** database storing farm registries and inspection audit logs with automated safe image cleanup.
5. **Academic & Technical Documentation:** Comprehensive university Capstone dissertation draft, technical architecture manual, and completion checklist.

---

## 📁 Organized Project Structure

The project is structured into clean, modular, self-contained components:

```text
Leafscan-main/
│
├── README.md                          # Master project documentation (this file)
├── .gitignore                         # Git tracking exclusions
├── start_app.bat                      # Master one-click Windows launcher
│
├── web-app/                           # Full-Stack Web Application
│   ├── README.md                      # Web app architecture & API reference
│   ├── requirements.txt               # Pinned Python packages (Flask, Pillow, numpy, tf-cpu)
│   ├── .env.example                   # Environment configuration template
│   ├── start_app.bat                  # Web application launcher
│   │
│   ├── frontend/                      # Presentation Layer
│   │   ├── templates/                 # Jinja2 HTML5 views (home, scan, farms, monitoring, history)
│   │   └── static/                    # Static assets
│   │       ├── css/styles.css         # Unified CSS design system & responsive styling
│   │       ├── js/app.js              # Leaf scanner client logic & farm selector
│   │       ├── images/hero-tomato.jpg # High-resolution landing visual
│   │       └── uploads/               # Persistent uploaded inspection photos
│   │
│   ├── backend/                       # Application Controller Layer
│   │   ├── app.py                     # Flask server, route controllers, and TFLite inference
│   │   └── db.py                      # SQLite database access layer, CRUD helpers, stats
│   │
│   ├── database/                      # Data Persistence Layer
│   │   ├── README.md                  # Database documentation & ER schema
│   │   ├── leafscan.db                # SQLite database file
│   │   └── schema.sql                 # SQL schema definition & indexes
│   │
│   └── tests/                         # Web Test Suite
│       └── test_app.py                # Automated 54-point integration test suite
│
├── mobile-app/                        # Cross-Platform Mobile Client (Flutter)
│   ├── README.md                      # Mobile app documentation & build guide
│   ├── pubspec.yaml                   # Flutter dependencies & asset manifest
│   ├── lib/                           # Dart application code (main.dart, models, services)
│   ├── assets/                        # Mobile assets (best_int8.tflite, fonts, icons)
│   ├── test/                          # Mobile unit tests (leafscan_test.dart)
│   └── android/ · ios/ · windows/ …  # Native platform host projects
│
├── ai-model/                          # Machine Learning & Model Assets
│   ├── README.md                      # Model specifications, tensor formats, and class taxonomy
│   └── models/
│       └── best_int8.tflite           # INT8-quantized YOLOv8 model (~26.5 MB)
│
├── docs/                              # Academic & Technical Documentation
│   ├── README.md                      # Documentation index
│   ├── TECHNICAL_DOCUMENTATION.md     # 13-Chapter Software & Architecture Manual
│   ├── PROJECT_REPORT_DRAFT.md        # 5-Chapter University Final-Year Dissertation
│   ├── REPORT_COMPLETION_CHECKLIST.md # Actionable submission checklist
│   └── DOCUMENTATION.md               # Original Flutter technical reference
│
└── scripts/                           # Safe Maintenance & Test Scripts
    ├── verify_system.py               # Comprehensive system health check
    └── run_tests.bat                  # One-click test runner batch script
```

---

## 🚀 Quick Start Guide (Windows)

### 1. Launch the Web Application (One-Click)
Double-click `start_app.bat` in the project root:
```cmd
start_app.bat
```
This automatically verifies Python 3.11, validates dependencies, opens your browser to `http://127.0.0.1:5000`, and starts the Flask server.

### 2. Manual Terminal Launch
```powershell
# Open terminal in web-app folder
cd "d:\TO\tomato\Leafscan-main\web-app"

# Install dependencies
pip install -r requirements.txt

# Start Flask server
python backend\app.py
```
Then navigate to: **`http://127.0.0.1:5000`**

---

## 🧪 System Verification & Automated Testing

### 1. System Health Check
Run the automated verification script:
```powershell
python scripts\verify_system.py
```
*Verifies Python runtime, required packages, AI model loading, database tables, and template availability.*

### 2. Run the Full Test Suite
Run the 54-point automated test suite:
```powershell
python web-app\tests\test_app.py
```
*Or double-click `scripts\run_tests.bat`.*

**All 54/54 tests run synchronously and validate:**
- Route HTTP 200 responses and template rendering (`/`, `/scan`, `/farms`, `/monitoring`, `/history`).
- Full Farm plot CRUD lifecycle (Create, List, Read, Update, Delete).
- Leaf photo upload, image normalization, model inference, and scan history recording.
- Physical file persistence in `static/uploads/` and safe file unlinking upon deletion.
- Crop Monitoring Dashboard KPI metrics, Chart.js structures, and empty states.

---

## 🌿 Detectable Foliar Conditions (15 Classes)

The integrated AI model detects and provides tailored agronomic guidance for:
1. **Healthy Leaf** — Symptom-free foliage
2. **Early Blight** (*Alternaria solani*) — Concentric fungal rings with chlorotic halos
3. **Late Blight** (*Phytophthora infestans*) — Rapid water-soaked leaf blotches
4. **Bacterial Spot** (*Xanthomonas* spp.) — Small dark lesions with yellow margins
5. **Bacterial Canker** (*Clavibacter michiganensis*) — Vascular wilting and upward curling
6. **Tomato Yellow Leaf Curl Virus (TYLCV)** — Upward cupping, chlorosis, and stunting
7. **Tomato Mosaic Virus (ToMV)** — Mottled leaf blister patterns
8. **Septoria Leaf Spot** — Circular spots with dark borders and tan centers
9. **Leaf Mold** (*Passalora fulva*) — Pale upper patches with olive-green velvet mold
10. **Powdery Mildew** — White talcum-like coating on upper leaf surfaces
11. **Pests:** Aphids, Flea Beetles, Leafminers (*Liriomyza*), Leafhoppers and Jassids

---

## 📚 Academic & Technical Documentation

The `docs/` folder contains complete materials for university capstone submission:
- **[TECHNICAL_DOCUMENTATION.md](file:///d:/TO/tomato/Leafscan-main/docs/TECHNICAL_DOCUMENTATION.md):** 13-chapter engineering manual with Mermaid diagrams, API references, security measures, and testing matrices.
- **[PROJECT_REPORT_DRAFT.md](file:///d:/TO/tomato/Leafscan-main/docs/PROJECT_REPORT_DRAFT.md):** 5-chapter academic dissertation formatted with preliminary pages, 100% verified genuine APA 7th edition references, and screenshot placeholders.
- **[REPORT_COMPLETION_CHECKLIST.md](file:///d:/TO/tomato/Leafscan-main/docs/REPORT_COMPLETION_CHECKLIST.md):** Pre-submission checklist for student details, screenshots, and supervisor reviews.

---

## ⚖️ Advisory Notice
Diagnoses generated by Tomato Leaf Scan are calculated via automated machine learning inference and serve as an informational decision-support aid. For critical chemical interventions, farmers should cross-verify symptoms with local agricultural extension officers or certified plant pathologists.
