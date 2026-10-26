# Tomato Leaf Scan — Web Application

## Overview
The **Tomato Leaf Scan Web Application** is a local decision-support platform designed for tomato growers, agricultural extension officers, and farm managers. It pairs on-device computer vision AI with multi-farm plot management, real-time crop health monitoring, and a searchable diagnostic scan history.

The application runs locally on Windows using Python 3.11, Flask 3.1.3, SQLite 3, and a TensorFlow Lite inference model (`best_int8.tflite`).

---

## Directory Structure

```text
web-app/
│
├── README.md                  # This documentation file
├── requirements.txt           # Python dependencies (Flask, Pillow, numpy, tensorflow-cpu)
├── .env.example               # Configuration template
├── start_app.bat              # One-click Windows launch script
│
├── frontend/                  # Presentation Layer
│   ├── templates/             # Jinja2 HTML templates
│   │   ├── base.html          # Shared layout, navigation bar, footer, toast system
│   │   ├── home.html          # Landing page (/)
│   │   ├── scan.html          # AI leaf scanner interface (/scan)
│   │   ├── farms.html         # Tomato farm plot manager (/farms)
│   │   ├── monitoring.html    # Crop monitoring dashboard (/monitoring)
│   │   ├── history.html       # Diagnostic scan history archive (/history)
│   │   └── index.html         # Legacy single-page scanner view
│   └── static/                # Static assets served by Flask
│       ├── css/
│       │   └── styles.css     # Unified CSS design system & responsive styling
│       ├── js/
│       │   └── app.js         # Leaf scanner client logic & farm selector loader
│       ├── images/
│       │   └── hero-tomato.jpg# High-resolution landing visual
│       └── uploads/           # Uploaded inspection photos (auto-managed)
│
├── backend/                   # Application & API Layer
│   ├── app.py                 # Flask server, route controllers, and TFLite inference
│   └── db.py                  # SQLite schema initialization, CRUD helpers, and stats
│
├── database/                  # Data Persistence Layer
│   ├── README.md              # Database documentation
│   ├── leafscan.db            # Persistent SQLite database file
│   └── schema.sql             # SQL table definitions and indexes
│
└── tests/                     # Test Suite
    └── test_app.py            # Automated 54-point integration test suite
```

---

## Quick Start Guide (Windows)

### Option 1: One-Click Launch (Recommended)
Double-click `start_app.bat` inside this folder (or `start_app.bat` in the project root).
The script will:
1. Detect Python 3.11 automatically.
2. Verify dependencies from `requirements.txt`.
3. Open your browser to `http://127.0.0.1:5000`.
4. Start the Flask web server.

### Option 2: Manual Terminal Execution
1. Open PowerShell or Command Prompt in the `web-app` folder:
   ```cmd
   cd "D:\coding lectures\toma to\Leafscan-main\web-app"
   ```
2. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
3. Start the Flask server:
   ```cmd
   python backend\app.py
   ```
4. Open your browser to:
   ```text
   http://127.0.0.1:5000
   ```

---

## Running the Automated Test Suite

To verify all routes, database transactions, AI inference, and safe deletion cascades:

```cmd
cd "D:\coding lectures\toma to\Leafscan-main\web-app"
python tests\test_app.py
```

*Expected output: `ALL 54/54 TESTS PASSED SUCCESSFULLY!`*

---

## API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Server and model health check |
| `POST` | `/api/predict` | Upload leaf image for AI diagnosis and persistence |
| `GET` | `/api/farms` | List all registered farm plots |
| `POST` | `/api/farms` | Create a new farm plot |
| `GET` | `/api/farms/<id>` | Retrieve single farm plot details |
| `PUT` | `/api/farms/<id>` | Update an existing farm plot |
| `DELETE`| `/api/farms/<id>` | Delete farm plot (safely archives historical scans) |
| `GET` | `/api/scans` | Query and filter scan records |
| `GET` | `/api/scans/<id>` | Retrieve single scan details with raw guidance JSON |
| `DELETE`| `/api/scans/<id>` | Delete scan record and safely remove image from disk |
| `GET` | `/api/dashboard/stats` | Aggregated KPIs, Chart.js metrics, and alerts |
