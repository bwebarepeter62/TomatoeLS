# LeafScan Technical System Documentation

**System Title:** LeafScan — AI-Based Tomato Leaf Disease Detection and Farm Monitoring System  
**Version:** 2.0.0 Production Upgrade  
**Academic Target:** Final-Year University Engineering Project & Agronomic Production Platform  

---

## 1. System Architecture Overview

LeafScan is designed as a hybrid distributed agricultural diagnostics architecture comprising:
1. **Web Diagnostics Platform (Flask + TensorFlow/Keras CPU):** Handles browser-based image scans, farm management, analytics dashboards, PDF generation, and multi-user data storage.
2. **Mobile Field Client (Flutter + TensorFlow Lite):** Handles offline smartphone field inference using an on-device quantized model, with batch synchronization to the central backend.
3. **Data Persistence Tier (SQLite + WAL Mode):** ACID-compliant relational storage with foreign keys, write-ahead logging, and user-isolated multi-tenant schema.

```
                           +------------------------------+
                           |     Farmer Web Browser       |
                           |  (HTML5 / CSS3 / Vanilla JS) |
                           +--------------+---------------+
                                          | HTTP / REST
                                          v
+------------------------+  REST Sync   +-----------------------------+
|  Flutter Mobile App    | -----------> | Flask Application Backend   |
|  (TFLite 15-Class Edge)|              |  - CSRF Protection          |
+------------------------+              |  - User Authentication      |
                                        |  - ReportLab PDF Engine     |
                                        |  - 16MB Upload Sanitizer    |
                                        +--------------+--------------+
                                                       |
                       +-------------------------------+-------------------------------+
                       |                                                               |
                       v                                                               v
         +----------------------------+                                  +-----------------------------+
         | MobileNetV2 Keras Model    |                                  | SQLite Database             |
         | (tomato_disease_model.h5)  |                                  | (leafscan.db + WAL Mode)    |
         | - 3 Classes (Blight Focus) |                                  | - users, farms, scans       |
         +----------------------------+                                  +-----------------------------+
```

---

## 2. Existing AI Models & Platform Contracts

### 2.1 Web Classifier (`tomato_disease_model.h5`)
- **Architecture:** MobileNetV2 base with custom Keras classification head.
- **Input Dimensions:** $(1, 224, 224, 3)$ RGB.
- **Preprocessing:** Custom graph layers (`TrueDivide`: $x / 127.5$, `Subtract`: $x - 1.0$) scaling raw $[0, 255]$ pixel floats to $[-1.0, 1.0]$.
- **Supported Diagnoses (3 Classes):**
  - Index 0: `Early Blight` (*Alternaria solani*)
  - Index 1: `Late Blight` (*Phytophthora infestans*)
  - Index 2: `Healthy Leaf`
- **Threshold Policy:** Predictions with confidence $< 0.50$ are flagged as *"No clear disease found"* rather than emitting arbitrary guesses.

### 2.2 Mobile Edge Detector (`best_int8.tflite`)
- **Architecture:** Quantized INT8 mobile model optimized for ARM/mobile CPUs.
- **Supported Diagnoses (15 Classes):** Covers a broader spectrum of tomato foliar diseases (e.g., Bacterial Spot, Septoria Leaf Spot, Target Spot, Yellow Leaf Curl Virus, Mosaic Virus, Spider Mites, Two-spotted Spider Mite, Leaf Mold, Early Blight, Late Blight, Healthy).
- **Offline Autonomy:** Operates fully disconnected in remote fields. When connectivity is restored, records synchronize to the web backend via `/api/mobile/sync`.
- **Label Integrity:** Synchronized records retain their original mobile classification and explicitly record `platform='mobile'` and `model_name='best_int8.tflite'` in the database.

---

## 3. Database Schema

### 3.1 `users` Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT DEFAULT '',
    role TEXT DEFAULT 'farmer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 `farms` Table
```sql
CREATE TABLE farms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    location TEXT DEFAULT '',
    size TEXT DEFAULT '',
    variety TEXT DEFAULT '',
    planting_date TEXT DEFAULT '',
    plant_count INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

### 3.3 `scans` Table
```sql
CREATE TABLE scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    farm_id INTEGER,
    farm_name TEXT DEFAULT 'General / Unassigned',
    image_filename TEXT NOT NULL,
    prediction_label TEXT NOT NULL,
    is_healthy INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0.0,
    disease_name TEXT,
    disease_type TEXT,
    disease_summary TEXT,
    disease_cause TEXT,
    raw_json TEXT,
    platform TEXT DEFAULT 'web',
    model_name TEXT DEFAULT 'tomato_disease_model.h5',
    sync_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL
);
```

---

## 4. API Reference

### 4.1 Prediction & Diagnostics
- `POST /api/predict`: Multipart form upload containing `image` and optional `farm_id`. Returns diagnosis, confidence score, treatment recommendations, and generated `scan_id`.
- `GET /api/scans/<int:scan_id>/report`: Streams downloadable PDF report with embedded photo, metadata, color badges, and advisory disclaimer.

### 4.2 Farm Management (User Isolated)
- `GET /api/farms`: List farms belonging to the current authenticated user (and unassigned legacy records).
- `POST /api/farms`: Register a new farm plot.
- `GET /api/farms/<int:farm_id>`: Retrieve specific plot details and scan counts.
- `PUT /api/farms/<int:farm_id>`: Update farm details.
- `DELETE /api/farms/<int:farm_id>`: Delete farm with database cascade cleanup.

### 4.3 Scan Audit History
- `GET /api/scans`: Filterable inspection logs. Query parameters: `search`, `status` (`healthy`, `disease`, `early_blight`, `late_blight`, `unclear`), `farm_id`, `date_from`, `date_to`, `sort` (`newest`, `oldest`), `limit`, `offset`.
- `GET /api/scans/<int:scan_id>`: Detailed diagnosis record with full treatment guidance.
- `DELETE /api/scans/<int:scan_id>`: Removes scan record and deletes image file from disk.

### 4.4 Analytics & Crop Monitoring
- `GET /api/dashboard/stats`: Returns aggregated metrics: `total_farms`, `total_scans`, `healthy_scans`, `disease_scans`, `early_blight_scans`, `late_blight_scans`, `healthy_percentage`, `disease_percentage`, `top_diseases`, `farm_breakdown`, `timeline`, `recent_scans`, and contextual alerts. Supports `farm_id`, `date_from`, and `date_to` filters.

### 4.5 Mobile Synchronization
- `GET /api/mobile/status`: Version and platform capability check.
- `GET /api/mobile/farms`: Farm list for mobile selection.
- `GET /api/mobile/scans`: Remote scan history retrieval.
- `POST /api/mobile/sync`: Batch scan synchronization with UUID deduplication via `sync_id`.

---

## 5. Security & Reliability

1. **Upload Size Restrictions:** Enforced `MAX_CONTENT_LENGTH = 16MB`. Payloads exceeding 16MB trigger HTTP 413.
2. **File Extension & Image Validation:** Only `.jpg`, `.jpeg`, `.png`, and `.webp` accepted. Every image stream is decoded through Pillow to reject corrupted files or disguised binaries.
3. **Session & Cookie Protections:** HTTPOnly and SameSite=Lax flags prevent cross-site scripting session hijacking.
4. **CSRF Tokens:** All state-changing HTML forms require a valid cryptographic CSRF token.
5. **Database Resilience:**
   - WAL mode enabled (`PRAGMA journal_mode=WAL`).
   - Concurrency busy timeout configured to 30,000ms (`PRAGMA busy_timeout=30000`).
   - Referential integrity enforced (`PRAGMA foreign_keys=ON`).

---

## 6. Known Limitations & Planned Future Work

1. **Domain Shift on Natural Backgrounds:** The web AI model was trained on PlantVillage laboratory imagery with uniform gray/white backgrounds. When presented with natural soil or brown mulch backgrounds, healthy leaves can be misclassified as Early Blight. Retraining with augmented field imagery is scheduled for the next development phase.
2. **Disease Severity Assessment:** Postponed per specification. Reliable severity estimation requires semantic segmentation to calculate percentage of affected leaf area (PALA), documented in [PROJECT_CHANGES.md](file:///d:/projects/blight/Leafscan-main/PROJECT_CHANGES.md).
