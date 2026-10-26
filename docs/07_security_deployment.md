# Phase Seven: Dependencies, Security Audit & Production Deployment

**Document:** `docs/07_security_deployment.md`  
**System:** LeafScan Platform  
**Target Audience:** DevOps Engineers, Security Auditors, and System Administrators  

---

## 1. Dependencies & Package Analysis

### A. Python Dependencies (`requirements.txt`)

Located at both `requirements.txt` (root) and `web-app/requirements.txt`:

```text
Flask==3.1.3
Pillow==12.3.0
numpy==2.4.6
tensorflow-cpu==2.16.2
```

| Package Name | Pinned Version | Architectural Role | Why It is Required |
|---|---|---|---|
| **`Flask`** | `3.1.3` | Application Server Framework | Provides HTTP routing, JSON serialization (`jsonify`), request parsing, and Jinja2 HTML rendering. |
| **`Pillow`** | `12.3.0` | Image Processing Engine | Validates incoming file streams, converts color palettes to RGB, resizes to $224 \times 224$ (bilinear), and writes JPEGs to disk. |
| **`numpy`** | `2.4.6` | Numerical Computing | Formats pixel matrices into float32 tensors, manipulates multidimensional arrays, and computes argmax. |
| **`tensorflow-cpu`** | `2.16.2` | Deep Learning Runtime | Loads the Keras MobileNetV2 model (`tomato_disease_model.h5`) and executes mathematical inference on CPU without needing heavy CUDA/GPU drivers. |

*Note on Built-In Libraries:* LeafScan also relies on Python standard libraries that require no installation: `sqlite3` (database), `os` / `sys` (paths), `uuid` / `datetime` (unique file naming), `json` (serialization), `shutil` (backups), `contextlib` (connection pooling), and `tempfile` (test isolation).

---

### B. Mobile Flutter Dependencies (`pubspec.yaml`)

| Package | Pinned Constraint | Purpose |
|---|---|---|
| **`tflite_flutter`** | `^0.12.1` | Native Dart FFI bindings to Google's TensorFlow Lite C++ runtime. |
| **`image_picker`** | `^1.1.2` | Native camera and gallery photo capture. |
| **`image`** | `^4.2.0` | In-memory pixel decoding, resizing, and array packing. |
| **`path_provider`** | `^2.1.4` | Locates platform-safe application sandbox directories. |
| **`google_fonts`** | `^6.2.1` | Typography styling (paired with local offline font assets). |
| **`http`** | `^1.2.2` | Issues outbound HTTPS requests to DeepSeek Chat API. |

---

## 2. Complete Security Audit & Vulnerability Assessment

A thorough inspection of the repository reveals the following security profile:

### A. Strengths & Defenses Implemented in Code
1. **Safe File Upload Naming (Path Traversal Protection):**
   In [app.py:L278-L282](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L278-L282):
   ```python
   ext = os.path.splitext(uploaded.filename.lower())[1] or '.jpg'
   saved_filename = f"leaf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
   ```
   The application **never uses the client-supplied filename directly**. By generating an internal filename based on timestamp and a random UUID, it completely neutralizes **Path Traversal attacks** (e.g. uploading `../../etc/passwd` or `..\Windows\System32\cmd.exe`).
2. **Stream Validation (Polyglot / Trojan Protection):**
   In [app.py:L270-L274](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L270-L274):
   ```python
   try:
       image = Image.open(uploaded.stream).convert('RGB')
   except UnidentifiedImageError:
       return jsonify({'error': 'The uploaded file is not a valid image.'}), 400
   ```
   Pillow parses the internal binary image headers. An executable file renamed with a `.jpg` extension is caught and rejected immediately.
3. **SQL Injection Defense (Parameterized Queries):**
   In [db.py](file:///d:/projects/blight/Leafscan-main/web-app/backend/db.py), **100% of user inputs** are passed as query parameters using `?` placeholders:
   ```python
   cursor.execute('INSERT INTO farms (...) VALUES (?, ?, ?)', (name, location, size))
   ```
   There are zero string concatenations (`f"SELECT * FROM scans WHERE id = {scan_id}"`), eliminating standard SQL Injection attacks.
4. **No Secrets Hardcoded in Public Git Files:**
   The DeepSeek API key is read via `String.fromEnvironment('DEEPSEEK_API_KEY')`, keeping API keys out of source control.
5. **Debug Mode Disabled by Default:**
   In [app.py:L27](file:///d:/projects/blight/Leafscan-main/app.py#L27) and [backend/app.py:L450](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L450), `debug=False` is enforced, preventing Werkzeug interactive debugger PIN exploitation.

---

### B. Identified Vulnerabilities & Technical Risks

| Vulnerability | Severity | Code Location | Description & Real-World Impact | Remediation Plan |
|---|---|---|---|---|
| **No Authentication / Authorization** | **HIGH** | All API routes | Endpoints (`/api/farms`, `/api/scans`) have no auth checks. Any visitor can read, edit, or delete any farm plot or scan record. | Implement Flask-Login or JWT session authentication with password hashing (`bcrypt`). |
| **Missing Upload File-Size Limit** | **MEDIUM** | `app.py` | Flask does not configure `MAX_CONTENT_LENGTH`. A malicious user could post a 10 GB file stream, causing Denial of Service (DoS) by exhausting disk space or memory. | Set `app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024` (16 MB limit). |
| **No Rate Limiting** | **MEDIUM** | `POST /api/predict` | The prediction endpoint runs heavy CPU matrix multiplication. Repeated automated POST requests could exhaust 100% of the server CPU. | Implement `Flask-Limiter` (e.g. limit to 10 requests per minute per IP). |
| **CORS Policy Unrestricted** | **LOW** | `app.py` | Currently runs without explicit CORS headers. While safe when accessed from same origin, integrating external mobile apps requires explicit origins. | Configure `flask-cors` to only allow trusted domain origins. |
| **Insecure HTTP Transport** | **MEDIUM** | Development server | Runs over plain `http://127.0.0.1:5000`. In transit across public WiFi, photos and data can be intercepted. | Enforce HTTPS via Let's Encrypt SSL/TLS certificates and Nginx reverse proxy. |

---

## 3. Step-by-Step Environment Reproduction (Clean Computer)

Follow these exact steps to set up LeafScan on a brand new Windows machine:

### Step 1: Install Python
1. Download and install **Python 3.11** (64-bit) from [python.org](https://www.python.org/).
2. **Crucial:** Check the box: **"Add python.exe to PATH"** during installation.

### Step 2: Clone or Extract Codebase
Extract the repository to your projects folder (e.g., `D:\projects\blight\Leafscan-main`).

### Step 3: Create & Activate Virtual Environment
Open PowerShell in the project directory:

```powershell
cd "D:\projects\blight\Leafscan-main"

# Create a clean isolated virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1
```

### Step 4: Install Dependencies
```powershell
# Upgrade pip package manager
python -m pip install --upgrade pip

# Install pinned dependencies
pip install -r requirements.txt
```

### Step 5: Verify System Health
Run the automated verification script:
```powershell
python scripts\verify_system.py
```
*Expected Output:* `[SUCCESS] All system components are verified and operational!`

### Step 6: Launch the Web Application
```powershell
python app.py
```
Navigate to: **`http://127.0.0.1:5000`** in Google Chrome or Edge.

---

## 4. Local Development vs. Production Deployment

The built-in Flask development server (`app.run()`) is single-threaded and explicitly warns:
`WARNING: This is a development server. Do not use it in a production deployment.`

### Architecture Comparison:

```mermaid
graph TD
    subgraph Development Setup
        DevBrowser["Web Browser"] -->|Direct HTTP Port 5000| DevFlask["Flask Development Server\n(Single-threaded Werkzeug WSGI)"]
        DevFlask --> DevDB[("SQLite Database")]
    end

    subgraph Production Setup
        ProdBrowser["Web Browser / Mobile App"] -->|HTTPS Port 443 (SSL/TLS)| Nginx["Nginx Reverse Proxy\n(Static Cache, Rate Limiting, SSL Offloading)"]
        Nginx -->|Unix Domain Socket / Reverse Proxy| Gunicorn["Gunicorn / Waitress WSGI Server\n(4 Worker Processes)"]
        Gunicorn --> ProdFlask["LeafScan Flask App"]
        ProdFlask --> ProdDB[("PostgreSQL / SQLite Database")]
    end
```

### Production Deployment Blueprint (Ubuntu / Linux Cloud VM):
1. **WSGI Application Server (Gunicorn):**
   Replace `app.run()` with Gunicorn to handle concurrent worker processes:
   ```bash
   pip install gunicorn
   gunicorn --workers 4 --bind 127.0.0.1:5000 "app:app"
   ```
2. **Reverse Proxy (Nginx):**
   Place Nginx in front of Gunicorn to handle SSL certificates (Let's Encrypt HTTPS), enforce max file sizes, and serve `/static/` images directly from disk at high speed.
3. **Process Management (Systemd):**
   Create a Systemd service (`/etc/systemd/system/leafscan.service`) to keep the server running continuously and restart automatically after system reboots.
