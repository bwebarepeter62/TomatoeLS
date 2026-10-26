# Phase Nine: Progressive Learning Path — Rebuilding LeafScan from Scratch

**Document:** `docs/09_rebuild_from_scratch.md`  
**System:** LeafScan Progressive Engineering Curriculum  
**Target Audience:** Beginner Programmers Aspiring to Full-Stack & ML Independence  

---

## 1. Educational Methodology & Philosophy

To master this system, do not blindly copy and paste code. You must follow the eight-stage engineering cycle:

```text
[1. Understand] ➔ [2. Plan] ➔ [3. Implement] ➔ [4. Debug] ➔ [5. Test] ➔ [6. Explain] ➔ [7. Rebuild] ➔ [8. Extend]
```

We will start with the smallest possible working program and introduce complexity in 16 structured milestones.

---

## 2. Milestone 1: Python Fundamentals for Backend Engineering

### Learning Objectives:
Understand Python execution, variables, dynamic types, lists, dictionaries, string formatting, and control flow.

### Concepts You Must Understand First:
- How Python scripts run from the command line (`python script.py`).
- The difference between numbers (`int`, `float`), text (`str`), lists (`[]`), and key-value maps (`dict {}`).

### Small Practical Exercise:
Create a dictionary mapping disease names to treatment recommendations and query it:
```python
# exercise1.py
damage_catalog = {
    "Early Blight": "Remove affected lower leaves and apply copper fungicide.",
    "Late Blight": "Destroy infected plants immediately; do not compost.",
    "Healthy": "No treatment required. Continue morning drip irrigation."
}

def get_treatment(disease_name):
    return damage_catalog.get(disease_name, "Unknown condition. Consult an agronomist.")

print(get_treatment("Early Blight"))
```

### Common Beginner Mistakes:
- **`KeyError`:** Accessing `damage_catalog["Rust"]` directly crashes if the key doesn't exist. Always use `.get(key, default)`.
- **Indentation Errors:** Mixing tabs and spaces. Use 4 spaces for every indent level.

### Self-Assessment Question:
*Why is a dictionary faster than a list when looking up disease treatment by name?*  
*(Answer: A dictionary uses a hash table providing $O(1)$ constant-time lookup, whereas a list requires $O(n)$ scanning).*

---

## 3. Milestone 2: Functions, Modules, Paths, and File Handling

### Learning Objectives:
Learn how to structure code across multiple files, import modules, manage paths safely on Windows, and handle binary file streams.

### Project Task:
Build a safe file storage helper that accepts an image path and saves it to a designated folder with a collision-resistant timestamp name.

### File to Create:
`storage_helper.py`

### Implementation:
```python
# storage_helper.py
import os
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

def save_uploaded_bytes(image_bytes: bytes, original_extension: str = ".jpg") -> str:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:6]
    clean_filename = f"leaf_{stamp}_{unique_id}{original_extension}"
    target_path = os.path.join(UPLOADS_DIR, clean_filename)
    
    with open(target_path, "wb") as f:
        f.write(image_bytes)
        
    return clean_filename
```

### Tests That Prove It Works:
```python
if __name__ == "__main__":
    test_data = b"\xFF\xD8\xFF\xE0" # JPEG Magic Header Bytes
    name = save_uploaded_bytes(test_data, ".jpg")
    assert os.path.exists(os.path.join(UPLOADS_DIR, name))
    print(f"Saved successfully as: {name}")
```

---

## 4. Milestone 3: HTTP, JSON, APIs, and the Request/Response Cycle

### Learning Objectives:
Understand client-server architecture, HTTP methods (`GET`, `POST`, `DELETE`), status codes (`200 OK`, `400 Bad Request`, `404 Not Found`, `500 Server Error`), and JSON serialization.

### Concepts You Must Understand:
- A web client sends a **Request** containing a Method, URL, Headers, and optional Body.
- The web server processes the request and sends a **Response** with a Status Code and Data.

### Practical Exercise:
Use Python's built-in `json` module to encode and decode a scan diagnosis:
```python
import json

diagnosis = {
    "label": "Late Blight",
    "confidence": 88.5,
    "is_healthy": False,
    "actions": ["Pull plants", "Spray copper"]
}

# Serialize dictionary to JSON string (sending over network)
json_string = json.dumps(diagnosis)

# Deserialize JSON string back to Python dictionary (receiving from network)
parsed_dict = json.loads(json_string)
assert parsed_dict["confidence"] == 88.5
```

---

## 5. Milestone 4: HTML, CSS, and DOM JavaScript Fundamentals

### Learning Objectives:
Create semantic HTML5 layouts, apply modern CSS design tokens, and write asynchronous JavaScript with `fetch()`.

### Practical Task:
Create a single-page HTML file (`index.html`) with an image file input, an instant visual preview, and an interactive scan button.

### Implementation:
```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: sans-serif; background: #f4f8f5; padding: 20px; }
    .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); max-width: 400px; }
    .btn { background: #1b7a43; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; }
    .preview { max-width: 100%; border-radius: 8px; margin-top: 15px; display: none; }
  </style>
</head>
<body>
  <div class="card">
    <h3>LeafScan Preview</h3>
    <input type="file" id="leaf-input" accept="image/*" />
    <img id="leaf-preview" class="preview" alt="Preview" />
    <br><br>
    <button id="scan-btn" class="btn">Scan Leaf</button>
  </div>

  <script>
    const input = document.getElementById('leaf-input');
    const preview = document.getElementById('leaf-preview');

    input.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        preview.src = URL.createObjectURL(file);
        preview.style.display = 'block';
      }
    });
  </script>
</body>
</html>
```

---

## 6. Milestone 5: Minimal Flask Server Without AI

### Learning Objectives:
Install Flask, configure routing, and serve your first dynamic web page.

### Code to Write:
```python
# minimal_app.py
from flask import Flask, render_template_string

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head><title>LeafScan Minimal</title></head>
<body>
  <h1>Tomato Leaf Scan Server is Running!</h1>
  <p>Status: Healthy</p>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

---

## 7. Milestone 6: Image Uploads & File Validation

### Learning Objectives:
Handle `multipart/form-data` uploads in Flask, protect against non-image exploits, and use Pillow for image validation.

### Implementation:
```python
from flask import Flask, request, jsonify
from PIL import Image, UnidentifiedImageError

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file uploaded'}), 400
        
    file = request.files['image']
    try:
        # Validate that the stream is a genuine image
        img = Image.open(file.stream).convert('RGB')
        width, height = img.size
        return jsonify({
            'status': 'ok',
            'filename': file.filename,
            'dimensions': f"{width}x{height}",
            'mode': img.mode
        })
    except UnidentifiedImageError:
        return jsonify({'error': 'Uploaded file is not a valid image'}), 400
```

---

## 8. Milestone 7: The SQLite Persistence Layer

### Learning Objectives:
Create relational tables, implement foreign keys, practice parameterized SQL queries, and build CRUD functions.

### Code to Write:
```python
# db_practice.py
import sqlite3

def init_db():
    conn = sqlite3.connect("practice.db")
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            variety TEXT DEFAULT ''
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farm_id INTEGER,
            prediction TEXT NOT NULL,
            confidence REAL,
            FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL
        )
    """)
    conn.commit()
    conn.close()

def add_farm(name, variety):
    conn = sqlite3.connect("practice.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO farms (name, variety) VALUES (?, ?)", (name, variety))
    farm_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return farm_id
```

---

## 9. Milestone 8: Machine Learning Fundamentals & Tensor Manipulation

### Learning Objectives:
Understand NumPy multidimensional arrays, shapes, slicing, and pixel normalization.

### Practical Exercise:
```python
import numpy as np

# Simulate a batch of 1 image with dimensions 224x224 and 3 color channels
fake_image = np.random.randint(0, 256, size=(224, 224, 3), dtype=np.uint8)

# Step 1: Convert to float32
arr = fake_image.astype(np.float32)

# Step 2: Normalize to [-1.0, +1.0] (MobileNetV2 scaling)
arr_normalized = (arr / 127.5) - 1.0

# Step 3: Add batch dimension
tensor = np.expand_dims(arr_normalized, axis=0)

assert tensor.shape == (1, 224, 224, 3)
assert tensor.min() >= -1.0 and tensor.max() <= 1.0
print("Tensor successfully prepared for inference!")
```

---

## 10. Milestone 9: Integrating Keras Model Inference with Flask

### Learning Objectives:
Load pre-trained neural network weights (`.h5`), pass image tensors, extract argmax indices, and return structured JSON.

### Implementation:
```python
import tensorflow as tf
import numpy as np
from PIL import Image

MODEL_PATH = "web-app/backend/tomato_disease_model.h5"
CLASSES = ['Early Blight', 'Late Blight', 'Healthy Leaf']

# In LeafScan, custom scaling layers are defined
class TrueDivide(tf.keras.layers.Layer):
    def call(self, inputs): return inputs / 127.5

class Subtract(tf.keras.layers.Layer):
    def call(self, inputs): return inputs - 1.0

# Load model
model = tf.keras.models.load_model(
    MODEL_PATH, 
    compile=False, 
    custom_objects={'TrueDivide': TrueDivide, 'Subtract': Subtract}
)

def predict_leaf(image_path):
    img = Image.open(image_path).convert('RGB').resize((224, 224))
    arr = np.expand_dims(np.asarray(img, dtype=np.float32), axis=0)
    
    # Run model
    probs = model.predict(arr, verbose=0)[0]
    best_idx = int(np.argmax(probs))
    
    return {
        "class": CLASSES[best_idx],
        "confidence": round(float(probs[best_idx]) * 100.0, 2),
        "probabilities": [float(p) for p in probs]
    }
```

---

## 11. Milestone 10: Building the Scan History and Analytics Dashboard

### Learning Objectives:
Write SQL aggregate queries (`COUNT`, `GROUP BY`, `SUM(CASE WHEN...)`) and render Chart.js graphs.

### SQL Query Exercise:
```sql
-- Compute healthy vs disease counts
SELECT 
    COUNT(*) as total_scans,
    SUM(CASE WHEN is_healthy = 1 THEN 1 ELSE 0 END) as healthy_count,
    SUM(CASE WHEN is_healthy = 0 THEN 1 ELSE 0 END) as disease_count
FROM scans;

-- Top 5 detected diseases
SELECT disease_name, COUNT(*) as frequency
FROM scans
WHERE is_healthy = 0
GROUP BY disease_name
ORDER BY frequency DESC
LIMIT 5;
```

---

## 12. Final Capstone Exercise: The Clean-Room Rebuild Challenge

### Objective:
Recreate the core functionality of LeafScan in an empty folder (`d:\projects\leafscan_scratch`) without copying and pasting any source code from this repository.

### Requirements to Satisfy:
1. Initialize an SQLite database with `farms` and `scans` tables.
2. Build a Flask app with two pages:
   - `/`: Farm registration and list.
   - `/scan`: Image file upload.
3. On `/scan`, accept a leaf photo, validate it via Pillow, resize to $224 \times 224$, run `tomato_disease_model.h5`, save the photo to disk, insert the diagnosis into SQLite, and display the predicted disease name and confidence percentage.
4. Implement an automated test script (`test_my_app.py`) verifying that:
   - Submitting a JPEG returns HTTP 200 and a valid label.
   - Submitting an invalid text file returns HTTP 400.
   - The scan record is saved in SQLite.
