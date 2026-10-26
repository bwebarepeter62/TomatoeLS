# LeafScan — AI Tomato Leaf Disease Detection and Farm Monitoring System

> **An AI-Powered Agricultural Technology Platform for Tomato Folium Pathology Detection, Crop Monitoring, and Multi-Plot Farm Management**

---

## 🌟 Overview & Objectives

**LeafScan** is a full-stack smart agriculture platform engineered for tomato growers, agronomists, and extension officers. The system provides rapid foliar disease detection, preventative treatment advice, multi-farm plot monitoring, downloadable diagnostic reports, and offline field synchronization.

### Primary Capabilities:
1. **AI Folium Diagnostics:** Web-based and mobile image analysis identifying high-impact tomato pathologies (*Early Blight* and *Late Blight*) alongside healthy leaves.
2. **Multi-Farm Plot Management:** Organize fields, track tomato varieties (Roma, MoneyMaker, San Marzano, etc.), planting cycles, and plant densities.
3. **Crop Monitoring Analytics:** Real-time dashboards visualizing crop health distribution, pathogen trends over time, farm-specific disease incidence, and actionable agronomic alerts.
4. **Professional PDF Diagnostic Reports:** Downloadable, printable inspection reports with leaf photos, color-coded diagnostic badges, treatment regimes, and advisory disclaimers.
5. **Secure Multi-User System:** Session-based authentication with Scrypt password hashing, CSRF tokens, and user-isolated farm and scan records.
6. **Mobile Field Synchronization:** Cross-platform Flutter mobile client support with batch synchronization and deduplication.

---

## 🔒 AI Model Architecture & Dual-Platform Contracts

> [!IMPORTANT]
> The existing AI models were **strictly preserved** in this upgrade cycle. No model files, weights, training pipelines, or prediction logic were modified.

| Attribute | Web Application Platform | Mobile Field Client |
| :--- | :--- | :--- |
| **Model File** | `web-app/backend/tomato_disease_model.h5` | `mobile-app/assets/models/best_int8.tflite` |
| **Architecture** | MobileNetV2 (Keras / TensorFlow CPU) | Quantized INT8 YOLOv8 Edge Detector |
| **Input Shape** | $(1, 224, 224, 3)$ RGB | Quantized mobile input tensor |
| **Diagnoses** | **3 Classes:** Early Blight, Late Blight, Healthy Leaf | **15 Classes:** Multi-condition edge detector |
| **Confidence Policy** | Predictions $< 50\%$ flagged as *"No clear disease found"* | On-device confidence thresholding |
| **Execution** | Centralized server-side inference | Fully offline on-device smartphone inference |

---

## 🚀 Quick Start Guide (Local Execution)

### Prerequisites:
- Python 3.11.x installed (e.g., Python 3.11.9)
- Git (optional)

### 1. Launch Using the Batch Script (Windows)
Double-click `start_app.bat` in the project root:
```cmd
start_app.bat
```

### 2. Manual Terminal Launch (PowerShell / Command Prompt)
```powershell
# Navigate to project root
cd d:\projects\blight\Leafscan-main

# Install dependencies
pip install -r requirements.txt

# Start Flask server
python app.py
```
Open your web browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🧪 Automated Testing & Verification

The system includes comprehensive automated test suites covering all non-model features, user authentication, PDF generation, mobile sync, and model integrity:

```powershell
# 1. Run Production Full-Stack Test Suite (72 tests)
python web-app\tests\test_app.py

# 2. Run Model Prediction Pipeline Test Suite (14 tests)
python -m unittest discover -s web-app/tests -p "test_prediction.py" -v
```

**Overall Test Results:** **86/86 TESTS PASSED (100% SUCCESS RATE)**.  
See [TEST_RESULTS.md](file:///d:/projects/blight/Leafscan-main/TEST_RESULTS.md) for the detailed test execution log.

---

## ☁️ Production Deployment on Render

LeafScan is pre-configured for deployment as a **Render Web Service**:
- **Procfile:**
  ```text
  web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 wsgi:app
  ```
- **Persistent Disk Storage:** Set `LEAFSCAN_DATA_DIR=/var/data` to persist the SQLite database (`leafscan.db`) and uploaded leaf photographs across restarts.
- **Docker Support:** Ready with root `Dockerfile` using dynamic `$PORT` and `python:3.11-slim`.

See [DEPLOYMENT_GUIDE.md](file:///d:/projects/blight/Leafscan-main/DEPLOYMENT_GUIDE.md) for step-by-step Render setup instructions.

---

## 📁 Repository Directory Structure

```text
Leafscan-main/
│
├── app.py                             # Root web entry point (delegates to backend)
├── wsgi.py                            # Production WSGI entry point (Gunicorn)
├── Procfile                           # Render process declaration
├── Dockerfile                         # Container build definition
├── runtime.txt                        # Pinned Python version (python-3.11.9)
├── requirements.txt                   # Production Python package manifest
│
├── web-app/                           # Full-Stack Web Application
│   ├── backend/                       # Application Controller & Data Logic
│   │   ├── app.py                     # Flask controllers, auth, PDF & mobile API
│   │   ├── db.py                      # SQLite database operations & WAL schema
│   │   ├── pdf_report.py              # ReportLab PDF report generator
│   │   └── tomato_disease_model.h5    # Untouched 3-class MobileNetV2 model
│   │
│   ├── frontend/                      # Presentation Layer
│   │   ├── templates/                 # Jinja2 views (scan, farms, monitoring, etc.)
│   │   └── static/                    # CSS design system, JS, and uploads
│   │
│   └── tests/                         # Automated Test Suites
│       ├── test_app.py                # 72-point comprehensive feature test suite
│       └── test_prediction.py         # 14-point model contract & inference test suite
│
├── mobile-app/                        # Cross-Platform Flutter Mobile Application
│   └── assets/models/best_int8.tflite # Untouched 15-class INT8 quantized TFLite model
│
├── PROJECT_CHANGES.md                 # Detailed changelog for all tasks (Tasks 1–13)
├── DOCUMENTATION.md                   # Complete architectural & API documentation
├── DEPLOYMENT_GUIDE.md                # Render production deployment guide
└── TEST_RESULTS.md                    # Verification test run logs
```

---

## ⚖️ Agricultural Advisory Notice
> "LeafScan diagnoses are generated by an AI-assisted computer vision system and serve strictly as advisory decision-support information. Results should not replace professional agronomic diagnosis. If symptoms persist or severe infestation is suspected, consult a certified plant pathologist or agricultural extension officer."
