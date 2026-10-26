# LeafScan: Open Questions & Investigation Guide

This document catalogs every architectural, technical, and model uncertainty that cannot be verified solely from the files in this repository, along with precise instructions on how to investigate them.

---

## 1. Unresolved Technical Questions

### Question 1: What was the exact training dataset, hyperparameter configuration, and loss curve for `tomato_disease_model.h5`?
- **Status:** **UNKNOWN**
- **What is known:**
  - The model file exists at `web-app/backend/tomato_disease_model.h5` (23.26 MB).
  - Its input shape is `(None, 224, 224, 3)` and its output shape is `(None, 3)`.
  - The classes are `['Early Blight', 'Late Blight', 'Healthy Leaf']`.
  - It contains custom layers `TrueDivide` (divides by 127.5) and `Subtract` (subtracts 1.0), typical of MobileNetV2 preprocessing in tf.keras.
  - A comment in `web-app/backend/app.py` line 26 states: `# IMPORTANT: These match the exact Keras class indices from Colab.`
- **What is missing:**
  - The Google Colab notebook (`.ipynb` file).
  - The training dataset directory or URL.
  - The number of epochs trained, batch size, learning rate schedule, optimizer (Adam, SGD), and validation split.
  - The training loss, validation loss, and confusion matrix.
- **How to investigate:**
  - Check your Google Drive / Google Colab account under "Colab Notebooks" for a notebook named `tomato_disease_model.ipynb` or similar.
  - Inspect model weights metadata in Python using:
    ```python
    import h5py
    with h5py.File('web-app/backend/tomato_disease_model.h5', 'r') as f:
        print(f.attrs.get('training_config'))
        print(f.attrs.get('model_config'))
    ```

---

### Question 2: Why do the web application and mobile application use completely different model architectures and class taxonomies?
- **Status:** **UNKNOWN (HISTORICAL DIVERGENCE)**
- **What is known:**
  - The mobile app (`mobile-app/`) uses `best_int8.tflite` (26.5 MB), which is a 15-class YOLOv8 object detector ($640 \times 640$ input, $1 \times 19 \times 8400$ output tensor).
  - The web application backend (`web-app/backend/app.py`) uses `tomato_disease_model.h5` (23.26 MB), which is a 3-class MobileNetV2 image classifier ($224 \times 224$ input, $1 \times 3$ output tensor).
  - An older backup file exists at `web-app/backend/app.py.bak_before_diagnosis` which previously supported the 15-class TFLite model or an earlier 3-class mapping.
  - `web-app/tests/test_prediction.py` fails because it was written assuming the web app would use the 15-class YOLOv8 model.
- **What is missing:**
  - Documentation explaining whether the 3-class Keras model was a temporary experiment to solve false positives on blight, or intended as a permanent replacement for the web platform.
- **How to investigate:**
  - Check version control history (`git log -p web-app/backend/app.py`).
  - Decide whether you want the web app to be updated to run the 15-class TFLite model, or keep the 3-class `.h5` model and update `test_prediction.py`.

---

### Question 3: Where did the 15-class model `best_int8.tflite` originate?
- **Status:** **UNKNOWN**
- **What is known:**
  - The model outputs 15 classes: `Aphids`, `Early Blight`, `Healthy Leaf-`, `Leaf Curl`, `Leafhoppers and Jassids`, `Molds`, `Mosaic Virus`, `Septoria`, `bactarial canker`, `bacterial spot`, `flea beetle`, `late_blight`, `leafminer`, `powedry_mildew`, `yellow curl virus`.
  - The spelling errors (`bactarial canker`, `powedry_mildew`, `Healthy Leaf-`) are identical in `ai-model/README.md`, `mobile-app/lib/models/detector.dart`, and `web-app/backend/app.py.bak_before_diagnosis`.
  - These names are characteristic of Roboflow public tomato disease datasets.
- **What is missing:**
  - The Roboflow dataset URL or YOLOv8 training command (`yolo train data=... model=yolov8n.pt ...`).
  - The original float32 `.pt` or `.onnx` model weights before quantization.
- **How to investigate:**
  - Search your Roboflow workspace or download history for tomato disease projects containing these exact 15 class labels.

---

### Question 4: Was mobile-to-web data synchronization planned or intentionally excluded?
- **Status:** **UNKNOWN**
- **What is known:**
  - The Flutter mobile app has no networking code to connect to `127.0.0.1:5000` or any remote Flask endpoint.
  - The mobile app runs 100% on-device (offline) using SQLite-free in-memory state.
  - The web application has a multi-farm SQLite database (`leafscan.db`) and Crop Monitoring dashboard (`monitoring.html`).
- **What is missing:**
  - Design documents explaining whether mobile scans were meant to sync back to the farmer's registered farm plot on the web dashboard.
- **How to investigate:**
  - If mobile syncing is desired, an API endpoint `POST /api/mobile/sync` can be designed where the mobile app uploads scan records to the central SQLite/PostgreSQL server when WiFi or cellular data is available.

---

### Question 5: How should the DeepSeek API key be managed in a production release?
- **Status:** **ARCHITECTURALLY UNRESOLVED**
- **What is known:**
  - In `mobile-app/lib/services/chat.dart`, the key is read via `String.fromEnvironment('DEEPSEEK_API_KEY', defaultValue: '')`.
  - A comment on line 13 warns: `SECURITY: any key compiled into a mobile app can be extracted from the APK. For a public release, proxy requests through your own server and keep the key server-side.`
- **How to investigate / solve:**
  - For university demonstration: Building with `--dart-define=DEEPSEEK_API_KEY=sk-...` is sufficient.
  - For public production: Route chat requests through the Flask backend (`POST /api/chat`), where the DeepSeek key is stored in server-side environment variables (`.env`).
