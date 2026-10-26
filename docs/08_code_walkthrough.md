# Phase Eight: File-by-File Line-by-Line Code Walkthrough

**Document:** `docs/08_code_walkthrough.md`  
**System:** LeafScan Source Code Guide  
**Target Audience:** Beginner to Intermediate Programmers Learning Software Architecture  

---

## 1. Walkthrough Scope & Approach

This guide examines the core source files that govern application behavior, data persistence, artificial intelligence execution, and user interaction. For each file, we follow a strict 12-point educational structure with real code excerpts and line-by-line analysis.

---

## 2. File 1: `web-app/backend/app.py` (Main Flask Application Server)

### 1. Responsibility
Serves as the central application controller. It initializes the Flask WSGI instance, registers all URL endpoints, handles multipart file uploads, coordinates model inference, and interfaces with the database layer.

### 2. Why It Exists
Web applications need an orchestrator to listen for HTTP requests from browsers and smartphones, process data, and return structured HTML or JSON responses.

### 3. Technologies Used
Python 3.11, Flask 3.1, Pillow (PIL), NumPy 2.4, TensorFlow-CPU 2.16 (Keras).

### 4. Imports & Dependencies
- `import os, sys, uuid, logging`: System path resolution and unique identifier generation.
- `from datetime import datetime`: Timestamps for file naming and database logs.
- `from typing import Any`: Type annotations.
- `import numpy as np`: Array formatting and argmax index extraction.
- `from flask import Flask, jsonify, redirect, render_template, request, url_for`: Web server utilities.
- `from PIL import Image, UnidentifiedImageError`: Safe image decoding and resizing.
- `import tensorflow as tf`: Neural network runtime.
- `import db`: Local database CRUD module (`db.py`).

### 5. Important Variables & Data Structures
- `MODEL_PATH`: String path resolving to `web-app/backend/tomato_disease_model.h5`.
- `CLASS_NAMES = ['Early Blight', 'Late Blight', 'Healthy Leaf']`: The exact 3-class list matching Keras ASCII alphabetical folder sorting.
- `CONFIDENCE_THRESHOLD = 0.50`: The cut-off percentage below which the model marks the result as uncertain.
- `DAMAGE_DB`: Dictionary storing tailored treatment records (causes, immediate actions, spread prevention, chemical/organic treatments) for each disease.

### 6. Functions & Classes
- `class TrueDivide(tf.keras.layers.Layer)`: Custom scaling layer.
- `class Subtract(tf.keras.layers.Layer)`: Custom shifting layer.
- `ensure_model_loaded()`: Lazy-loads the H5 neural network weights into global memory.
- `preprocess_image(image)`: Transforms a PIL image into a `(1, 224, 224, 3)` NumPy array.
- `build_result_for_image(image)`: Coordinates inference, threshold checking, and treatment lookup.
- Page routes: `home()`, `scan_page()`, `farms_page()`, `monitoring_page()`, `history_page()`, `health()`.
- API controllers: `predict()`, `api_list_farms()`, `api_create_farm()`, `api_list_scans()`, `api_dashboard_stats()`.

---

### 7. Line-by-Line Excerpt Analysis

#### Excerpt A: Custom Keras Scaling Layers ([app.py:L102-L125](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L102-L125))

```python
class TrueDivide(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def __call__(self, *args, **kwargs):
        # Pass only the image tensor (args[0]) to the graph builder
        return super().__call__(args[0], **kwargs)
        
    def call(self, inputs):
        # Execute the actual math required by MobileNetV2
        return inputs / 127.5
```
- **Line 102:** Declares a custom Keras layer inheriting from `tf.keras.layers.Layer`.
- **Line 103-104:** Standard constructor accepting keyword arguments like layer names.
- **Line 106-108:** Overrides `__call__`. In newer Keras versions, legacy layer graphs sometimes pass unexpected metadata tuples. By extracting `args[0]`, we ensure only the image tensor enters the layer.
- **Line 110-112:** `call(self, inputs)` defines the mathematical tensor transformation: dividing every pixel by $127.5$.

#### Excerpt B: Image Preprocessing ([app.py:L145-L152](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L145-L152))

```python
def preprocess_image(image: Image.Image) -> np.ndarray:
    """Turn a PIL image into the (1, 224, 224, 3) array."""
    resized = image.convert('RGB').resize(MODEL_INPUT_SIZE, Image.Resampling.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32)
    return np.expand_dims(arr, axis=0)
```
- **Line 145:** Type-hinted function accepting a Pillow Image object and returning a NumPy array.
- **Line 147:** `.convert('RGB')` strips any alpha/transparency channels (e.g. from PNGs). `.resize((224, 224), Image.Resampling.BILINEAR)` smoothly interpolates the image to the exact square dimensions MobileNetV2 expects.
- **Line 151:** Converts the PIL image into a 3D float array of shape `(224, 224, 3)` with raw pixel values $[0.0, 255.0]$.
- **Line 152:** `np.expand_dims(..., axis=0)` adds a batch dimension at index 0, producing a 4D tensor of shape `(1, 224, 224, 3)`. Neural networks always expect a batch dimension, even for a single image.

#### Excerpt C: Handling Image Uploads & File Saving ([app.py:L270-L283](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L270-L283))

```python
try:
    image = Image.open(uploaded.stream).convert('RGB')
except UnidentifiedImageError:
    return jsonify({'error': 'The uploaded file is not a valid image.'}), 400

result = build_result_for_image(image)

ext = os.path.splitext(uploaded.filename.lower())[1] or '.jpg'
saved_filename = f"leaf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
saved_filepath = os.path.join(UPLOADS_DIR, saved_filename)
os.makedirs(os.path.dirname(saved_filepath), exist_ok=True)
image.save(saved_filepath, quality=90)
```
- **Line 270-273:** Attempts to parse the raw byte stream using Pillow. If a user uploads corrupt data, it catches `UnidentifiedImageError` and immediately returns an HTTP 400 JSON error.
- **Line 276:** Runs neural network inference and generates the diagnosis dictionary.
- **Line 278:** Extracts the lowercase file extension (`.jpg`, `.png`, `.jfif`).
- **Line 279:** Formats a secure filename: `leaf_` + timestamp (`20261021_215219`) + 6-character random hex UUID + extension.
- **Line 282:** Writes the sanitized image to disk with 90% JPEG quality.

---

### 8. Relationships & Callers
- Executed by root `app.py` or `start_app.bat`.
- Imported and tested by `web-app/tests/test_app.py`.
- Calls `db.py` to record scans and query dashboard statistics.

### 9. What Happens If Removed
The web application ceases to exist. Browsers will receive "Connection Refused" errors.

### 10. Common Bugs & Debugging
- **Keras Custom Layer Error:** If TensorFlow is updated and `custom_objects` is missing from `load_model()`, loading fails with `ValueError: Unknown layer: TrueDivide`.
- **Fix:** Ensure `custom_objs = {'TrueDivide': TrueDivide, 'Subtract': Subtract}` is passed to `tf.keras.models.load_model()`.

### 11. How to Write from Scratch
1. Instantiate `app = Flask(__name__)`.
2. Define `@app.route('/')` returning `render_template()`.
3. Define `@app.route('/api/predict', methods=['POST'])` accepting `request.files['image']`.
4. Load your model with `tf.keras.models.load_model()`.
5. Return predictions using `jsonify()`.

---

## 3. File 2: `web-app/backend/db.py` (Database Access Layer)

### 1. Responsibility
Manages all interactions with the SQLite relational database (`leafscan.db`), including schema creation, connection pooling, farm CRUD operations, scan audit logging, and KPI aggregation.

### 2. Why It Exists
Separating database code from HTTP route controllers follows the **Single Responsibility Principle**. If the database engine changes (e.g. migrating from SQLite to PostgreSQL), only `db.py` needs modification; `app.py` remains untouched.

### 3. Technologies Used
Python 3.11 standard library (`sqlite3`, `contextlib`, `json`, `shutil`, `os`).

### 4. Imports & Dependencies
- `import sqlite3`: Embedded relational database engine.
- `from contextlib import contextmanager`: Python generator context manager decorator.
- `import json`: Encodes Python dictionaries into JSON strings for database storage.
- `import shutil`: Performs binary file copying for timestamped database backups.

### 5. Important Functions
- `get_db_connection()`: Context manager yielding an open connection with foreign keys and Row factory.
- `init_db()`: Creates the `farms` and `scans` tables and performance indexes.
- `reset_db(backup, clear_uploads)`: Wipes tables, creates timestamped backups, and unlinks upload files.
- `create_farm()`, `list_farms()`, `get_farm()`, `update_farm()`, `delete_farm()`: Farm CRUD helpers.
- `save_scan()`, `list_scans()`, `get_scan()`, `delete_scan()`: Scan CRUD and image cleanup helpers.
- `get_dashboard_stats()`: Computes total farms, total scans, healthy rate, top diseases, and 14-day timeline.

---

### 6. Line-by-Line Excerpt Analysis

#### Excerpt A: Context Manager Connection Pool ([db.py:L17-L37](file:///d:/projects/blight/Leafscan-main/web-app/backend/db.py#L17-L37))

```python
@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```
- **Line 17:** `@contextmanager` allows this function to be invoked using the Python `with get_db_connection() as conn:` statement.
- **Line 26:** `sqlite3.connect(DB_PATH)` opens the database file.
- **Line 27:** `conn.row_factory = sqlite3.Row` configures rows to be dictionary-accessible.
- **Line 28:** Explicitly turns on SQLite foreign key constraint validation.
- **Line 30:** `yield conn` pauses execution, handing the active connection to the calling block.
- **Line 31:** If the calling block finishes without error, `conn.commit()` commits the transaction to disk.
- **Line 33:** If an exception occurs, `conn.rollback()` undoes any partial writes.
- **Line 36:** `finally: conn.close()` guarantees the file handle is closed, preventing Windows file locks.

#### Excerpt B: Scan Record Creation ([db.py:L191-L220](file:///d:/projects/blight/Leafscan-main/web-app/backend/db.py#L191-L220))

```python
def save_scan(image_filename: str, prediction_label: str, is_healthy: bool,
              confidence: float, disease_name: str, disease_type: str,
              disease_summary: str, disease_cause: str, raw_data: Dict[str, Any],
              farm_id: Optional[int] = None) -> int:
    farm_name = 'General / Unassigned'
    if farm_id:
        farm = get_farm(farm_id)
        if farm:
            farm_name = farm['name']
        else:
            farm_id = None

    raw_json = json.dumps(raw_data)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scans (
                farm_id, farm_name, image_filename, prediction_label,
                is_healthy, confidence, disease_name, disease_type,
                disease_summary, disease_cause, raw_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            farm_id, farm_name, image_filename, prediction_label,
            1 if is_healthy else 0, round(confidence, 1), disease_name,
            disease_type, disease_summary, disease_cause, raw_json
        ))
        conn.commit()
        return cursor.lastrowid
```
- **Line 195-202:** Resolves the `farm_name`. If a `farm_id` was passed, it retrieves the farm to cache its name. If the farm ID is invalid, it falls back to `None`.
- **Line 203:** `json.dumps(raw_data)` serializes the entire dictionary of treatment recommendations into a single text string.
- **Line 207-217:** Issues an `INSERT` statement using parameterized `?` placeholders.
- **Line 219:** `cursor.lastrowid` returns the auto-increment integer ID of the newly created scan record.

---

## 4. File 3: `web-app/frontend/static/js/app.js` (Frontend Scanner Controller)

### 1. Responsibility
Manages client-side interactivity on `scan.html`, including drag-and-drop file picking, client validation, local blob image previewing, asynchronous HTTP communication via `fetch()`, DOM updates, and smooth scrolling.

### 2. Technologies Used
Vanilla JavaScript (ES6+), Fetch API, DOM manipulation API.

### 3. Key Functions
- `updatePreview(file)`: Creates a temporary blob URL (`URL.createObjectURL`) to show the photo immediately.
- `clearSelection()`: Revokes the blob URL and hides preview containers.
- `renderResult(data)`: Unhides `#results` and injects disease text, confidence scores, and guidance lists.
- `loadFarmsIntoSelect()`: Fetches `/api/farms` to populate the plot dropdown.

### 4. Line-by-Line Excerpt Analysis ([app.js:L120-L163](file:///d:/projects/blight/Leafscan-main/web-app/frontend/static/js/app.js#L120-L163))

```javascript
form.addEventListener('submit', async (event) => {
  event.preventDefault(); // Prevents full page reload

  if (!selectedFile) {
    setStatus('Please select an image before scanning.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('image', selectedFile);

  if (farmSelect && farmSelect.value) {
    formData.append('farm_id', farmSelect.value);
  }

  analyzeButton.disabled = true;
  analyzeButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning leaf with AI...';

  try {
    const response = await fetch('/api/predict', {
      method: 'POST',
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || 'Prediction failed.');
    }

    renderResult(payload);
    setStatus('Prediction complete and saved to Scan History.', 'success');
  } catch (error) {
    setStatus(error.message, 'error');
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Scan leaf';
  }
});
```
- **Line 121:** `event.preventDefault()` stops the browser's default behavior of reloading the page on form submit.
- **Line 128-134:** Constructs a `FormData` object. This automatically sets the correct HTTP `multipart/form-data` boundary header required for uploading binary files.
- **Line 136-137:** Disables the button and inserts a spinning FontAwesome spinner icon to provide clear loading feedback.
- **Line 142:** `await fetch('/api/predict', ...)` sends the image asynchronously without blocking the browser UI thread.
- **Line 158:** Calls `renderResult(payload)` to update the DOM with the AI predictions.
- **Line 167-170:** The `finally:` block guarantees the scan button is re-enabled even if a network timeout occurs.

---

## 5. File 4: `mobile-app/lib/models/detector.dart` (Mobile Edge AI Engine)

### 1. Responsibility
Executes on-device YOLOv8 neural network inference inside the Flutter application. It handles asset loading, image preprocessing, multi-scale anchor decoding, and Non-Maximum Suppression (NMS).

### 2. Technologies Used
Dart 3.x, `tflite_flutter` (LiteRT C++ bindings), `package:image/image.dart`.

### 3. Key Classes & Methods
- `class Detection`: Data model storing `rawLabel`, clean `label`, `confidence`, and `bbox` `[x1, y1, x2, y2]`.
- `class TomatoDetector`: Orchestrates the TFLite runtime.
  - `load()`: Loads `best_int8.tflite` from Flutter assets.
  - `detect(File file)`: Accepts a phone photo, resizes, runs inference, and returns filtered `List<Detection>`.
  - `_nms(List<Detection> dets)`: Computes Intersection-over-Union (IoU) to eliminate duplicate boxes.

### 4. Line-by-Line Excerpt Analysis ([detector.dart:L251-L277](file:///d:/projects/blight/Leafscan-main/mobile-app/lib/models/detector.dart#L251-L277))

```dart
List<Detection> _nms(List<Detection> dets) {
  // Sort candidates by confidence descending (highest score first)
  dets.sort((a, b) => b.confidence.compareTo(a.confidence));
  final kept = <Detection>[];

  for (final d in dets) {
    bool keep = true;
    for (final k in kept) {
      if (d.rawLabel == k.rawLabel && _iou(d.bbox, k.bbox) > _iouThreshold) {
        keep = false; // Overlap exceeds 45% -> suppress duplicate
        break;
      }
    }
    if (keep) kept.add(d);
  }
  return kept;
}

double _iou(List<double> a, List<double> b) {
  final x1 = max(a[0], b[0]);
  final y1 = max(a[1], b[1]);
  final x2 = min(a[2], b[2]);
  final y2 = min(a[3], b[3]);
  final inter = max(0.0, x2 - x1) * max(0.0, y2 - y1);
  final union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter;
  return union <= 0 ? 0 : inter / union;
}
```
- **Line 253:** Sorts the candidate boxes so the highest-confidence detections are evaluated first.
- **Line 257-261:** For each candidate `d`, compares it against already accepted detections `k`. If both candidates represent the same disease and their spatial overlap (`_iou`) exceeds the $45\%$ threshold (`_iouThreshold = 0.45`), `d` is marked as a duplicate and discarded.
- **Line 268-277:** Calculates Intersection over Union:
  $$\text{IoU} = \frac{\text{Intersection Area}}{\text{Box A Area} + \text{Box B Area} - \text{Intersection Area}}$$
  This ensures that if a single large blight lesion is detected by 5 adjacent anchors, only the single most confident bounding box is drawn.
