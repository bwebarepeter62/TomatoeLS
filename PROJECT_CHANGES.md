# LeafScan System Upgrade — Project Changes Log

**Project:** LeafScan — AI-Based Tomato Leaf Disease Detection and Farm Monitoring System  
**Stage:** Full-Stack University Final-Year Upgrade  
**Date:** October 2026  
**Status:** All Non-Model Tasks (Tasks 1–13) Implemented & Verified (86/86 Tests Passing)

---

## 🔒 Crucial Compliance Guarantee: Zero AI Model Modifications

As explicitly mandated, **no AI model files, weights, architectures, or prediction algorithms were modified, retrained, fine-tuned, or replaced**:
- `web-app/backend/tomato_disease_model.h5`: **UNTOUCHED** (SHA-256: `0f951c47ed1ee24a4d95208f9f170e80e59932ad8d37c564344e1cae3d5ebf27`)
- `mobile-app/assets/models/best_int8.tflite`: **UNTOUCHED**
- Model preprocessing (MobileNetV2 $224 \times 224$ with `TrueDivide` / `Subtract` custom scaling): **PRESERVED**
- Class mappings (`Early Blight`, `Late Blight`, `Healthy Leaf`): **PRESERVED**
- Confidence threshold ($0.50$): **PRESERVED**
- No artificial image rejection heuristics, green-pixel thresholds, background segmentation, or synthetic severity labels were introduced.

---

## 📋 Comprehensive Task-by-Task Implementation Summary

### Task 1: Scanning Notice & Guidance on `/scan`
- **Implemented:** Added a prominent, responsive information card near the upload dropzone.
- **Wording:**
  > **IMPORTANT SCANNING NOTICE**  
  > LeafScan is currently designed to identify Early Blight and Late Blight in tomato leaves. For the best results, upload clear photographs of tomato leaves showing suspected blight symptoms.  
  > Avoid uploading unrelated plants, fruits, objects, or unclear photographs.  
  > AI predictions are advisory and may be incorrect. If you are unsure about the diagnosis, consult a qualified agricultural expert.
- **Button Reminder:** Added explicit reminder under the primary upload trigger: *"Upload tomato leaf images with suspected blight symptoms only."*
- **Design System:** Styled using LeafScan's green palette (`#1d7b43`, `#0a2a2a`) and Inter typography without disrupting existing drag-and-drop or camera controls.

### Task 2: Secure User Authentication & Account Management
- **Implemented:** Session-based authentication with Scrypt/PBKDF2 password hashing via `werkzeug.security`.
- **Database Schema:** Created `users` table via non-destructive migration (`id`, `username`, `email`, `password_hash`, `full_name`, `role`, `created_at`).
- **Protected Endpoints:** Created `@login_required` decorator. Unauthenticated access to `/farms` redirects to `/login?next=/farms`.
- **User Isolation:** All farm and scan database queries are scoped to `session['user_id']`. Existing legacy records (`user_id IS NULL`) are safely preserved.
- **CSRF Protection:** Integrated cryptographic CSRF tokens on all POST forms (`login`, `register`, `profile_update`, `profile_password`).
- **Views Added:**
  - `web-app/frontend/templates/login.html`: Clean sign-in form with error alerts.
  - `web-app/frontend/templates/register.html`: Sign-up form with input validation and password confirmation.
  - `web-app/frontend/templates/profile.html`: Operator profile editor and password update card.

### Task 3: Farm Management Enhancements
- **Preserved Existing Design:** Retained existing `/farms` layout, modal workflows, and styling.
- **CRUD Validation:** Enhanced modal validation for farm name (required), location, tomato variety, planting date, plant count ($\ge 0$), and cultivation notes.
- **User Ownership:** Added `farms.user_id` foreign key referencing `users(id)` with `ON DELETE SET NULL`.
- **Safe Operations:** Implemented confirmation modal before deleting farm records.

### Task 4: Crop Monitoring Dashboard Analytics
- **KPI Metrics:** Expanded KPI summary grid from 4 to 6 metric cards: Total Farms, Total Scans, Healthy Leaves, Early Blight Detections, Late Blight Detections, and Overall Disease Rate.
- **Farm Health Breakdown Table:** Added plot analytics table displaying farm-specific inspection counts, healthy leaves, Early Blight, Late Blight, and disease incidence rates.
- **Interactive Filtering:** Added filter bar with Farm Plot selector, Date From, and Date To inputs wired via asynchronous `loadDashboard()` calls.
- **Live Visualizations:** Powered by Chart.js (Doughnut health distribution, bar disease frequency, line scan timeline) using live SQLite data without synthetic filler.

### Task 5: Scan Diagnostic History Improvements
- **Listing & Filtering:** Enhanced `/history` with date-range filters (`date_from`, `date_to`), diagnosis type (`healthy`, `disease`, `early_blight`, `late_blight`, `unclear`), and farm plot filters.
- **Sorting:** Added chronological sorting (newest first vs. oldest first).
- **Direct PDF Download:** Added direct "Download PDF" icon button on each scan card and inside the detailed inspection modal.
- **Safe Cleanup:** Deleting a scan record removes the database row and safely deletes the image file from `static/uploads/`.

### Task 6: Professional PDF Diagnosis Reports
- **Library:** Integrated lightweight `reportlab==5.1.0`.
- **Generator Module:** Implemented `web-app/backend/pdf_report.py`.
- **Report Contents:**
  - LeafScan header with formal branding and report tracking number (`LS-XXXXX`).
  - Metadata table: Inspection Date, Time, Associated Farm Plot, Analysis Platform, AI Engine.
  - Uploaded leaf photo embedded with aspect-ratio preservation.
  - Diagnosis section with color-coded badges (Green: Healthy, Amber: Early Blight, Red: Late Blight).
  - Model confidence percentage.
  - Disease summary, biological causes, and immediate containment measures.
  - Long-term prevention practices and cultural management advice.
  - Mandatory agricultural advisory disclaimer.
- **Endpoint:** `GET /api/scans/<int:scan_id>/report` streaming attachment with proper MIME type.

### Task 7: Web & Mobile Application Integration
- **Preserved Dual Model Architecture:**
  - Web: 3-class MobileNetV2 classifier (`Early Blight`, `Late Blight`, `Healthy Leaf`).
  - Mobile: 15-class edge detector running INT8 quantized TFLite (`best_int8.tflite`).
- **Synchronization API:**
  - `GET /api/mobile/status`: Exposes server version, models, and platform contracts.
  - `GET /api/mobile/farms`: Retrieves authenticated user's farm plots for mobile selection.
  - `GET /api/mobile/scans`: Retrieves inspection history.
  - `POST /api/mobile/sync`: Accepts batch scan payloads from mobile, records `platform='mobile'` and `model_name='best_int8.tflite'`, and prevents duplicate syncs via `sync_id` UUID tracking.

### Task 8: Security & File Upload Hardening
- **Upload Size Limit:** Configured `MAX_CONTENT_LENGTH = 16 * 1024 * 1024` (16 MB).
- **Format Restrictions:** Allowed extensions restricted to `.jpg`, `.jpeg`, `.png`, `.webp`.
- **Image Integrity:** Validated via Pillow image decoding with structured error handling for corrupted files.
- **Filename Sanitization:** Stored images renamed with timestamped UUIDs (`leaf_YYYYMMDD_HHMMSS_xxxxxx.ext`).
- **Session Security:** `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`.

### Task 9: Database Reliability & Non-Destructive Migrations
- **Safe Migrations:** `init_db()` in `db.py` uses `PRAGMA table_info` before applying `ALTER TABLE` to add `user_id`, `platform`, `model_name`, and `sync_id` without dropping tables or losing rows.
- **Concurrency & WAL Mode:** Activated `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=30000` (30 seconds) for concurrent requests.
- **Foreign Key Integrity:** Enforced `PRAGMA foreign_keys = ON`.
- **Persistent Disk Config:** Supported configurable `LEAFSCAN_DATA_DIR` environment variable.

### Task 10: Render Production Deployment & Persistence
- **Procfile:** Configured `web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 wsgi:app`.
- **Dockerfile:** Updated entry point to use dynamic `$PORT` and `wsgi:app`.
- **Persistent Storage Ready:** Points database and uploads to `/var/data` when `LEAFSCAN_DATA_DIR` is set on Render persistent disks.

### Task 11: UI/UX Consistency
- **Design Preserved:** Kept all CSS variables, typography (Inter), responsive navigation, cards, and modal dialogs.
- **Component Polish:** Form inputs, loading spinners, alert toasts, and empty states.

---

## 🔮 Task 12: Future Improvements — Disease Severity Assessment

As mandated, **disease severity estimation was intentionally not implemented** in this upgrade cycle. The system does not emit synthetic or guessed "Mild", "Moderate", or "Severe" labels.

### What is Needed to Implement Reliable Disease Severity in the Future:
1. **Pixel-Level Foliage Segmentation:**
   - A semantic segmentation model (e.g., U-Net, DeepLabV3+, or YOLOv8-seg) trained to isolate the leaf blade boundary from the background (soil, hands, mulch).
2. **Pathological Lesion Masking:**
   - Pixel-level annotation distinguishing active necrotic lesions, chlorotic halos, and healthy green tissue.
3. **Calculated Percentage of Affected Leaf Area (PALA):**
   - Severity is mathematically defined as:
     $$\text{Severity (\%)} = \frac{\text{Lesion Pixel Count}}{\text{Total Leaf Blade Pixel Count}} \times 100$$
4. **Standardized Agronomic Severity Scale (Horsfall-Barratt / EPPO):**
   - Grade 1 (Very Mild): $< 5\%$ leaf area infected.
   - Grade 2 (Mild): $5\% - 15\%$ leaf area infected.
   - Grade 3 (Moderate): $16\% - 35\%$ leaf area infected.
   - Grade 4 (Severe): $36\% - 60\%$ leaf area infected.
   - Grade 5 (Devastating): $> 60\%$ leaf area infected with defoliation risk.

---

## 🧪 Task 13: Test Verification Results

All tests executed successfully in the test environment:

```text
==================================================
Running LeafScan Production Test Suite (Tasks 1-13)
==================================================
[PASS] AI Model SHA-256 Checksum Unchanged (0f951c47ed...)
[PASS] GET /health status 200
[PASS] Health check model exists
[PASS] Health check DB initialized
[PASS] GET / (Landing page) status 200
[PASS] Landing page contains hero title
[PASS] Landing page contains Scan CTA
[PASS] GET /scan (Scanner page) status 200
[PASS] Scan page contains 'IMPORTANT SCANNING NOTICE'
[PASS] Scan page contains advisory disclaimer
[PASS] Scan page contains button reminder text
[PASS] Scan page has Download Report button element
[PASS] GET /farms unauthenticated redirects to /login (302)
[PASS] GET /login renders 200
[PASS] Login page has username_or_email input
[PASS] GET /register renders 200
[PASS] Register page has username input
[PASS] POST /register redirects to /farms on success
[PASS] User session active after registration
[PASS] User saved in SQLite users table
[PASS] Password securely hashed (not plain text)
[PASS] GET /profile renders 200 for authenticated user
[PASS] Profile contains user's email
[PASS] GET /logout clears session and redirects to home
[PASS] POST /login authenticates successfully
[PASS] POST /api/farms creates farm (201)
[PASS] Farm ID returned
[PASS] GET /api/farms returns 200
[PASS] Created farm exists in list
[PASS] GET /api/farms/1 returns 200
[PASS] Correct farm variety retrieved
[PASS] PUT /api/farms/1 status 200
[PASS] Farm update persisted in database
[PASS] Farm plant count updated
[PASS] POST /api/predict rejects invalid file extension (400)
[PASS] POST /api/predict rejects corrupted image file (400)
[PASS] POST /api/predict status 200
[PASS] Predict response contains status ok
[PASS] Predict response contains label
[PASS] Predict response contains confidence
[PASS] Predict response contains scan_id
[PASS] Predict response contains image_url
[PASS] Physical leaf image saved in uploads directory
[PASS] Saved scan associated with authenticated user_id
[PASS] GET /api/scans/1/report status 200
[PASS] Report has application/pdf content type
[PASS] Report bytes start with PDF magic number '%PDF-'
[PASS] Report size is non-trivial (> 2000 bytes)
[PASS] GET /api/scans status 200
[PASS] Saved scan appears in scan list
[PASS] GET /api/scans?farm_id=1 status 200
[PASS] Scan correctly filtered by farm
[PASS] GET /api/dashboard/stats status 200
[PASS] Dashboard total_farms >= 1
[PASS] Dashboard total_scans >= 1
[PASS] Dashboard includes early_blight_scans metric
[PASS] Dashboard includes late_blight_scans metric
[PASS] Dashboard includes farm_breakdown list
[PASS] Dashboard recent_scans non-empty
[PASS] Dashboard timeline calculated
[PASS] GET /api/mobile/status status 200
[PASS] Mobile status documents 15-class edge detector model
[PASS] Mobile status documents 3-class web model
[PASS] POST /api/mobile/sync status 200
[PASS] Mobile sync successfully inserted 2 records
[PASS] Mobile sync deduplicates already synchronized records
[PASS] Mobile sync reported skipped duplicates
[PASS] DELETE /api/scans/1 status 200
[PASS] Scan record was deleted (404)
[PASS] Image file safely cleaned up after scan deletion
[PASS] DELETE /api/farms/1 status 200
[PASS] Farm was deleted (404)
==================================================
ALL 72/72 PRODUCTION TESTS PASSED SUCCESSFULLY!
==================================================
```

Prediction Pipeline Unit Tests:
```text
test_corrupted_non_image_file_returns_400 ... ok
test_empty_filename_returns_400 ... ok
test_missing_image_payload_returns_400 ... ok
test_valid_image_upload_returns_expected_contract ... ok
test_reset_db_preserves_backup_and_cleans_tables ... ok
test_lab_healthy_leaves_accuracy ... ok
test_class_names_and_healthy_index ... ok
test_custom_layers_math ... ok
test_every_class_has_treatment_guidance ... ok
test_model_input_and_output_shapes ... ok
test_color_modes_converted_to_three_channels ... ok
test_shape_dtype_and_dimensions ... ok
test_confident_prediction_returns_available ... ok
test_uncertainty_flagging_when_confidence_low ... ok

Ran 14 tests in 4.793s — OK (14/14 PASSED)
```

**Total Tests Passed: 86/86 (100% Pass Rate).**
