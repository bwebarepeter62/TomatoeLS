# Phase Ten: Testing, Quality Assurance & Debugging Manual

**Document:** `docs/10_testing_and_debugging.md`  
**System:** LeafScan QA & Diagnostic Manual  
**Target Audience:** QA Engineers, Software Testers, and Debugging Engineers  

---

## 1. Test Architecture & Actual Project Behavior

LeafScan includes two automated test suites in `web-app/tests/`, each reflecting different historical stages of development:

1. **`web-app/tests/test_app.py` (Active Integration Suite):**
   - **Status:** **54/54 TESTS PASS SYNCHRONOUSLY**.
   - **Scope:** Route availability, HTML template rendering, Farm CRUD lifecycle, leaf upload validation, inference output schema, database persistence, and safe unlinking of deleted photos.
   - **Environment:** Executes against a disposable temporary directory (`tempfile.mkdtemp()`), ensuring zero data corruption of production records.
2. **`web-app/tests/test_prediction.py` (Legacy Model Regression Guard):**
   - **Status:** **FAILS (8 failures, 9 errors)**.
   - **Root Cause:** Written for the 15-class YOLOv8 TFLite model (`(1, 3, 640, 640)` tensor), whereas `web-app/backend/app.py` now runs the 3-class MobileNetV2 Keras model (`(1, 224, 224, 3)` tensor).

---

## 2. Comprehensive Test Verification Matrix (54 Verified Tests)

Below is the verified test matrix matching the actual execution of `web-app/tests/test_app.py`:

| # | Test Name | Target Route / Operation | Assertion Condition | Result |
|:---:|---|---|---|:---:|
| 1 | Health Check Status | `GET /health` | `res.status_code == 200` | **PASS** |
| 2 | Model Existence | `GET /health` | `data['model_exists'] is True` | **PASS** |
| 3 | Database Initialized | `GET /health` | `data['db_initialized'] is True` | **PASS** |
| 4 | Home Page Status | `GET /` | `res.status_code == 200` | **PASS** |
| 5 | Hero Title Rendered | `GET /` | `b"Detect tomato leaf diseases early" in res.data` | **PASS** |
| 6 | Scan CTA Rendered | `GET /` | `b"Scan a Leaf" in res.data` | **PASS** |
| 7 | How It Works Section | `GET /` | `b"How Tomato Leaf Scan Works" in res.data` | **PASS** |
| 8 | Features Section | `GET /` | `b"Tomato Farm Management" in res.data` | **PASS** |
| 9 | Scan Page Status | `GET /scan` | `res.status_code == 200` | **PASS** |
| 10 | File Input Present | `GET /scan` | `b'id="image-input"' in res.data` | **PASS** |
| 11 | Farm Selector Present | `GET /scan` | `b'id="farm-select"' in res.data` | **PASS** |
| 12 | Results Panel Present | `GET /scan` | `b'id="results"' in res.data` | **PASS** |
| 13 | Farms Page Status | `GET /farms` | `res.status_code == 200` | **PASS** |
| 14 | Farms Title Rendered | `GET /farms` | `b"Tomato Farm Management" in res.data` | **PASS** |
| 15 | Farm Modal Present | `GET /farms` | `b'id="farm-modal"' in res.data` | **PASS** |
| 16 | Monitoring Page Status | `GET /monitoring` | `res.status_code == 200` | **PASS** |
| 17 | Monitoring Title Rendered | `GET /monitoring` | `b"Crop Monitoring Dashboard" in res.data` | **PASS** |
| 18 | Chart.js Canvas Present | `GET /monitoring` | `b"healthDistributionChart" in res.data` | **PASS** |
| 19 | History Page Status | `GET /history` | `res.status_code == 200` | **PASS** |
| 20 | History Title Rendered | `GET /history` | `b"Scan Diagnostic History" in res.data` | **PASS** |
| 21 | Search Field Present | `GET /history` | `b'id="search-input"' in res.data` | **PASS** |
| 22 | Detail Modal Present | `GET /history` | `b'id="scan-detail-modal"' in res.data` | **PASS** |
| 23 | Create Farm Status | `POST /api/farms` | `res.status_code == 201` | **PASS** |
| 24 | Farm ID Generated | `POST /api/farms` | `farm_id > 0` | **PASS** |
| 25 | List Farms Status | `GET /api/farms` | `res.status_code == 200` | **PASS** |
| 26 | Farm in List | `GET /api/farms` | Farm name appears in array | **PASS** |
| 27 | Get Farm Detail | `GET /api/farms/<id>` | `res.status_code == 200` | **PASS** |
| 28 | Variety Matches | `GET /api/farms/<id>` | `farm['variety'] == 'Roma VF'` | **PASS** |
| 29 | Update Farm Status | `PUT /api/farms/<id>` | `res.status_code == 200` | **PASS** |
| 30 | Name Update Persisted | `GET /api/farms/<id>` | `name == 'Green Horizon Organic Estate'` | **PASS** |
| 31 | Plant Count Updated | `GET /api/farms/<id>` | `plant_count == 720` | **PASS** |
| 32 | Predict Endpoint Status | `POST /api/predict` | `res.status_code == 200` | **PASS** |
| 33 | Predict Response Status OK | `POST /api/predict` | `pred['status'] == 'ok'` | **PASS** |
| 34 | Label Field Present | `POST /api/predict` | `'label' in pred` | **PASS** |
| 35 | Confidence Field Present | `POST /api/predict` | `'confidence' in pred` | **PASS** |
| 36 | Scan ID Returned | `POST /api/predict` | `pred['scan_id'] > 0` | **PASS** |
| 37 | Image URL Formatted | `POST /api/predict` | Starts with `/static/uploads/` | **PASS** |
| 38 | Physical File Saved | File System | `os.path.exists(static/uploads/leaf_*.jpg)` | **PASS** |
| 39 | Scans List Status | `GET /api/scans` | `res.status_code == 200` | **PASS** |
| 40 | New Scan in History | `GET /api/scans` | `any(s['id'] == scan_id)` | **PASS** |
| 41 | Farm Filter Functional | `GET /api/scans?farm_id=X` | All returned scans match farm ID | **PASS** |
| 42 | Get Scan Detail | `GET /api/scans/<id>` | `res.status_code == 200` | **PASS** |
| 43 | Advice JSON Decoded | `GET /api/scans/<id>` | `isinstance(scan['raw_json'], dict)` | **PASS** |
| 44 | Dashboard Stats Status | `GET /api/dashboard/stats` | `res.status_code == 200` | **PASS** |
| 45 | Total Farms Counted | `GET /api/dashboard/stats` | `total_farms >= 1` | **PASS** |
| 46 | Total Scans Counted | `GET /api/dashboard/stats` | `total_scans >= 1` | **PASS** |
| 47 | Recent Scans Populated | `GET /api/dashboard/stats` | `len(recent_scans) >= 1` | **PASS** |
| 48 | Timeline Computed | `GET /api/dashboard/stats` | `isinstance(timeline, list)` | **PASS** |
| 49 | Delete Scan Status | `DELETE /api/scans/<id>` | `res.status_code == 200` | **PASS** |
| 50 | Scan Record Deleted | `GET /api/scans/<id>` | `res.status_code == 404` | **PASS** |
| 51 | Physical File Cleaned Up | File System | `not os.path.exists(file)` | **PASS** |
| 52 | Delete Farm Status | `DELETE /api/farms/<id>` | `res.status_code == 200` | **PASS** |
| 53 | Farm Record Deleted | `GET /api/farms/<id>` | `res.status_code == 404` | **PASS** |
| 54 | Total Suite Completion | Test Runner | Synchronous teardown of temp directory | **PASS** |

---

## 3. Systematic Debugging Guide

When diagnosing unexpected behavior, **always gather evidence before altering source code**:

```text
[Observe Failure] ➔ [Check System Logs] ➔ [Inspect Tensor Shapes] ➔ [Verify Class Maps] ➔ [Formulate Fix]
```

### Problem 1: Flask Fails to Start with `FileNotFoundError: Model file was not found`
- **Evidence:** `FileNotFoundError: Model file was not found at web-app\backend\tomato_disease_model.h5`.
- **Diagnosis:** The script was executed from a directory where relative path calculations failed, or the `.h5` file was deleted or moved.
- **Verification:** Run `python -c "import os; print(os.path.exists('web-app/backend/tomato_disease_model.h5'))"`.
- **Solution:** Verify the model file exists in `web-app/backend/` and use `os.path.dirname(os.path.abspath(__file__))` for path anchors.

---

### Problem 2: Model Output Returns "Unknown layer: TrueDivide"
- **Evidence:** `ValueError: Unknown layer: 'TrueDivide'. Please ensure this class is passed to the custom_objects argument`.
- **Diagnosis:** The `.h5` model contains custom layer mathematical operations that Keras does not recognize out-of-the-box.
- **Verification:** Check `app.py:L133-L142` to ensure `custom_objects={'TrueDivide': TrueDivide, 'Subtract': Subtract}` is passed to `load_model()`.

---

### Problem 3: Healthy Tomato Leaves Are Classified as Early or Late Blight
- **Evidence:** Clean green leaves photographed under outdoor sunlight receive $90\%+$ confidence scores for `Late Blight`.
- **Diagnostic Protocol:**
  1. **Log Raw Probabilities:** Add `print(probabilities)` before argmax. Observe if the model is truly confident ($99\%$) or borderline ($51\%$).
  2. **Verify Class Names Array:** Check `CLASS_NAMES` in [app.py:L27-L31](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L27-L31):
     ```python
     CLASS_NAMES = [
         'Early Blight',   # Index 0
         'Late Blight',    # Index 1
         'Healthy Leaf'    # Index 2
     ]
     ```
     If the training script sorted folders as `Early_Blight`, `Healthy`, `Late_Blight`, then index 1 is actually `Healthy` and index 2 is `Late Blight`. Swapping these two indices will instantly invert predictions.
  3. **Domain Shift:** If the model was trained only on laboratory images with grey paper backgrounds, it may treat outdoor soil or sunlight glares as disease lesions. Place the leaf on a neutral white sheet of paper and scan again to confirm background bias.

---

### Problem 4: Mobile App Shows "Model Not Loaded" or Crashes on Launch
- **Evidence:** In `_RootPageState`, `_modelError` contains `StateError: assets/models/best_int8.tflite not found`.
- **Diagnosis:** The model file is missing from the Flutter asset manifest.
- **Verification:** Inspect `mobile-app/pubspec.yaml` under `flutter: -> assets:`. Ensure `- assets/models/best_int8.tflite` is indented properly. Run `flutter clean` followed by `flutter pub get`.

---

## 4. Runnable Self-Contained Test Examples

You can run these standalone diagnostic scripts to verify individual subsystems:

### Test 1: Verify Web Model Loading and Output Shape
```python
# test_model_standalone.py
import numpy as np
import tensorflow as tf

class TrueDivide(tf.keras.layers.Layer):
    def call(self, inputs): return inputs / 127.5

class Subtract(tf.keras.layers.Layer):
    def call(self, inputs): return inputs - 1.0

model = tf.keras.models.load_model(
    'web-app/backend/tomato_disease_model.h5',
    compile=False,
    custom_objects={'TrueDivide': TrueDivide, 'Subtract': Subtract}
)

dummy_tensor = np.zeros((1, 224, 224, 3), dtype=np.float32)
output = model.predict(dummy_tensor, verbose=0)

print("Model Input Shape:", model.input_shape)
print("Model Output Shape:", model.output_shape)
print("Sample Prediction Probabilities:", output)

assert model.input_shape == (None, 224, 224, 3)
assert model.output_shape == (None, 3)
assert np.isclose(np.sum(output), 1.0)
print("[PASS] Model successfully verified!")
```

### Test 2: Verify Database Connection & Foreign Key Cascades
```python
# test_db_standalone.py
import sqlite3

conn = sqlite3.connect(':memory:')
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

# Create tables
cursor.execute("CREATE TABLE farms (id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE scans (id INTEGER PRIMARY KEY, farm_id INTEGER, FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL)")

# Insert farm and scan
cursor.execute("INSERT INTO farms VALUES (1, 'Test Farm')")
cursor.execute("INSERT INTO scans VALUES (101, 1)")
conn.commit()

# Delete farm
cursor.execute("DELETE FROM farms WHERE id = 1")
conn.commit()

# Assert scan.farm_id became NULL
scan = cursor.execute("SELECT farm_id FROM scans WHERE id = 101").fetchone()
assert scan[0] is None
print("[PASS] SQLite Foreign Key ON DELETE SET NULL verified!")
```
