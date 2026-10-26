# Phase Three: Web Application Architecture, Frontend & Backend Guide

**Document:** `docs/03_web_application.md`  
**System:** LeafScan Web Application  
**Target Audience:** Beginner to Intermediate Web Developers  

---

## 1. Web Technology Stack Overview

The LeafScan web application is built with a minimalist, robust, zero-build-step architecture:
- **Backend Framework:** **Python Flask 3.1.3** — a lightweight WSGI web framework.
- **Server Templating Engine:** **Jinja2** — renders server-side dynamic HTML templates.
- **Frontend Core:** **Vanilla HTML5, Vanilla CSS3, and Vanilla JavaScript (ES6+)**.
- **Data Visualization:** **Chart.js v4.4.1** (loaded via CDN on the monitoring dashboard).
- **Typography & Icons:** Google Fonts (**Inter**) and FontAwesome v6.
- **Image Processing Library:** **Pillow 12.3.0** (Python Imaging Library).
- **Inference Runtime:** **TensorFlow-CPU 2.16.2 / Keras 3.x**.
- **Persistence Engine:** **SQLite 3** via Python standard library `sqlite3`.

No external frontend build pipeline (Webpack, Vite, npm, Babel) is required. You can edit any `.html`, `.css`, or `.js` file and simply refresh the web browser to see changes.

---

## 2. Frontend Engineering & Design System

### A. Template Hierarchy & Layout Inheritance

LeafScan uses Jinja2 template inheritance to maintain a consistent visual structure across all pages without duplicating navigation bars or footers.

```text
base.html (Master Shell)
  ├── <head>: Viewport, Meta, Google Fonts (Inter), styles.css, FontAwesome
  ├── <header class="topbar">: Brand identity ("Tomato Leaf Scan"), mobile toggle, navigation links
  ├── <main>: {% block content %} (Child templates inject page-specific DOM here)
  ├── <footer class="site-footer card">: Brand mission, footer links, advisory disclaimer
  └── Toast Notification Container: Dynamically renders pop-up toast alerts
```

Each child template extends `base.html` and populates the block:
- [home.html](file:///d:/projects/blight/Leafscan-main/web-app/frontend/templates/home.html): Welcome hero banner, platform features, agronomic benefits, and call-to-action buttons.
- [scan.html](file:///d:/projects/blight/Leafscan-main/web-app/frontend/templates/scan.html): Photo dropzone, instant image preview, farm selection, and diagnosis treatment cards.
- [farms.html](file:///d:/projects/blight/Leafscan-main/web-app/frontend/templates/farms.html): Farm plot registry, modal forms, and farm cards displaying scan counts.
- [monitoring.html](file:///d:/projects/blight/Leafscan-main/web-app/frontend/templates/monitoring.html): KPI metrics cards, doughnut chart, timeline chart, and urgent disease warnings.
- [history.html](file:///d:/projects/blight/Leafscan-main/web-app/frontend/templates/history.html): Filterable inspection cards, search field, and detailed report modal.

---

### B. The CSS Design System (`styles.css`)

The application styles are declared in [styles.css](file:///d:/projects/blight/Leafscan-main/web-app/frontend/static/css/styles.css) using modern CSS Custom Properties (variables) defined at the `:root` level:

```css
:root {
  --primary: #1b7a43;         /* Agronomic Forest Green */
  --primary-hover: #145e33;   /* Deep Green for interactive states */
  --accent: #2e8b57;          /* SeaGreen accent */
  --bg: #f4f8f5;              /* Clean organic off-white */
  --surface: #ffffff;         /* Pure white container cards */
  --text: #1d2d24;            /* Dark green-slate typography */
  --muted: #526359;           /* Secondary label typography */
  --border: #dbe7df;          /* Subtle card divider borders */
  --danger: #c0392b;          /* Alert red for Late Blight / infections */
  --warning: #d35400;         /* Amber orange for Early Blight / cautions */
  --success: #27ae60;         /* Bright green for healthy foliage */
  --shadow: 0 4px 14px rgba(0, 0, 0, 0.06); /* Card elevation */
  --radius: 12px;             /* Modern rounded corners */
}
```

#### Key Styling Techniques:
1. **Glassmorphism & Elevation:** `.card` components utilize soft drop-shadows, subtle border colors (`--border`), and white surface backgrounds to create a clean, modern aesthetic.
2. **Responsive CSS Grid & Flexbox:**
   - The KPI metric container uses `grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))`, adjusting automatically from single-column on mobile phones to 4-column layouts on wide monitors.
   - Farm cards and history items use auto-fit grids that prevent horizontal scrollbars on smaller viewports.
3. **Interactive Micro-Animations:** Buttons feature `transition: all 0.2s ease` and `transform: translateY(-2px)` on hover, providing tactile feedback when clicked.

---

### C. JavaScript Client Implementation & Functions

#### 1. Leaf Scanner Controller (`app.js`)
The scanner logic in [app.js](file:///d:/projects/blight/Leafscan-main/web-app/frontend/static/js/app.js) manages the entire user lifecycle on `scan.html`.

##### Function Catalog:
- **`setStatus(message: string, variant: string = 'neutral'): void`**
  - **Inputs:** `message` (text to show), `variant` (`'neutral'`, `'info'`, `'success'`, `'warning'`, `'error'`).
  - **Purpose:** Updates the text and background color of the `#status-box` banner below the upload box.
- **`updatePreview(file: File | null): void`**
  - **Inputs:** A browser `File` object from `<input type="file">`.
  - **Purpose:** Creates an in-memory blob URL with `URL.createObjectURL(file)`, assigns it to `#preview-image.src`, and unhides the preview panel.
- **`clearSelection(): void`**
  - **Purpose:** Resets the file input, revokes the blob URL to prevent browser memory leaks (`URL.revokeObjectURL`), hides the preview panel, and restores the status banner.
- **`writeList(target: HTMLElement, items: string[]): void`**
  - **Inputs:** Target DOM element (e.g., `#stop-now`) and an array of treatment strings.
  - **Purpose:** Clears the container and appends `<li>` elements for each agronomic guidance bullet.
- **`renderResult(data: Object): void`**
  - **Inputs:** The JSON response payload received from `/api/predict`.
  - **Purpose:** Unhides `#results`, updates the title, renders the calculated confidence percentage, injects summary, cause, and pathogen group, populates treatment lists via `writeList()`, and initiates a smooth scroll (`scrollIntoView({ behavior: 'smooth' })`).
- **`loadFarmsIntoSelect(): Promise<void>`**
  - **Purpose:** Queries `GET /api/farms` on page load, populates the `<select id="farm-select">` dropdown with registered farm plots, and preselects a farm if a `?farm_id=` URL query parameter is present.

---

### D. Step-by-Step Trace of a Web User Interaction

1. **User Drops Image:** The farmer drags a leaf photo onto `#upload-box`.
2. **Client Validation:** The `change` event fires. `app.js` checks `['image/png', 'image/jpeg', 'image/webp'].includes(file.type)`. If invalid (e.g. `.gif` or `.pdf`), it halts execution and renders a red error message.
3. **Instant Preview:** `updatePreview()` generates a local blob URL (`blob:http://127.0.0.1:5000/3a2f...`). The leaf photo appears instantly on the page without network lag.
4. **Click "Scan Leaf":** The user clicks `#analyze-btn`.
5. **UI Lock & Loading State:** `analyzeButton.disabled = true;` prevents duplicate submissions. The button text changes to `<i class="fa-solid fa-spinner fa-spin"></i> Scanning leaf with AI...`.
6. **Fetch Execution:** A `fetch('/api/predict', { method: 'POST', body: formData })` request is sent to Flask.
7. **DOM Mutation:** Upon receiving the HTTP 200 JSON payload, `renderResult(payload)` populates the diagnosis cards and smoothly scrolls the user directly to their treatment plan.

---

## 3. Backend Architecture & Flask Server Implementation

### A. Server Initialization & Configuration

The backend is initialized in [web-app/backend/app.py](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L16-L47):

```python
# Absolute directory resolution ensures stability regardless of where terminal is opened
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_APP_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..'))
TEMPLATE_DIR = os.path.join(WEB_APP_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(WEB_APP_DIR, 'frontend', 'static')
UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')

MODEL_PATH = os.path.join(BACKEND_DIR, 'tomato_disease_model.h5')

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)
db.init_db()
```

#### Why This Design Matters:
Using `os.path.abspath` prevents path-resolution bugs common on Windows when executing Python from different working directories (e.g., executing from the project root vs inside `web-app/`).

---

### B. Custom Keras Layers for MobileNetV2

MobileNetV2 neural networks expect pixel values normalized between $-1.0$ and $+1.0$ ($x_{norm} = \frac{x}{127.5} - 1.0$). When this model was exported from Google Colab, Keras embedded mathematical operation layers into the graph.

In modern TensorFlow versions, loading these layers directly can cause positional-argument exceptions. [app.py:L102-L125](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L102-L125) solves this with custom layer definitions:

```python
class TrueDivide(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    def __call__(self, *args, **kwargs):
        return super().__call__(args[0], **kwargs)
    def call(self, inputs):
        return inputs / 127.5

class Subtract(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    def __call__(self, *args, **kwargs):
        return super().__call__(args[0], **kwargs)
    def call(self, inputs):
        return inputs - 1.0
```

These layers are injected into `tf.keras.models.load_model(..., custom_objects={'TrueDivide': TrueDivide, 'Subtract': Subtract})`, allowing the `.h5` file to load and execute without errors.

---

### C. Complete REST API Endpoint Reference Table

The table below lists all endpoints verified in the Flask server code:

| Method | Endpoint Path | Function Name | Purpose | Required Inputs | Response Format | Status Codes |
|---|---|---|---|---|---|---|
| `GET` | `/` | `home()` | Serves landing page view | None | HTML document (`home.html`) | 200 |
| `GET` | `/scan` | `scan_page()` | Serves leaf scanner interface | Optional query: `?farm_id=<id>` | HTML document (`scan.html`) | 200 |
| `GET` | `/farms` | `farms_page()` | Serves farm management view | None | HTML document (`farms.html`) | 200 |
| `GET` | `/monitoring` | `monitoring_page()` | Serves analytics dashboard | None | HTML document (`monitoring.html`) | 200 |
| `GET` | `/history` | `history_page()` | Serves inspection history archive | None | HTML document (`history.html`) | 200 |
| `GET` | `/index` | `index_redirect()` | Redirects legacy `/index` to `/` | None | HTTP 302 Redirect | 302 |
| `GET` | `/health` | `health()` | Verifies server & model health | None | `{"status": "ok", "model_exists": bool, "python": str}` | 200 |
| `POST` | `/api/predict` | `predict()` | Runs AI leaf disease diagnosis | Multipart: `image` (file), optional `farm_id` (int) | `{"status": "ok", "label": str, "confidence": float, "disease": {...}, "scan_id": int}` | 200, 400, 500 |
| `GET` | `/api/farms` | `api_list_farms()` | Retrieves all registered farm plots | None | `{"status": "ok", "farms": [...]}` | 200 |
| `POST` | `/api/farms` | `api_create_farm()` | Registers a new farm plot | JSON/Form: `name` (required), `location`, `size`, `variety`, `plant_count`, `notes` | `{"status": "ok", "farm_id": int, "message": str}` | 201, 400 |
| `GET` | `/api/farms/<id>` | `api_get_farm()` | Fetches single farm details | URL param: `id` (integer) | `{"status": "ok", "farm": {...}}` | 200, 404 |
| `PUT` | `/api/farms/<id>` | `api_update_farm()` | Updates farm plot metadata | URL param: `id`, JSON: updated farm attributes | `{"status": "ok", "message": str}` | 200, 400, 404 |
| `DELETE` | `/api/farms/<id>` | `api_delete_farm()` | Removes farm plot (archives scans) | URL param: `id` (integer) | `{"status": "ok", "message": str}` | 200, 404 |
| `GET` | `/api/scans` | `api_list_scans()` | Queries filterable scan logs | Query params: `search`, `status`, `farm_id`, `sort`, `limit`, `offset` | `{"status": "ok", "scans": [...]}` | 200 |
| `GET` | `/api/scans/<id>` | `api_get_scan()` | Fetches single scan detail & advice | URL param: `id` (integer) | `{"status": "ok", "scan": {...}}` | 200, 404 |
| `DELETE` | `/api/scans/<id>` | `api_delete_scan()` | Deletes scan record & unlinks file | URL param: `id` (integer) | `{"status": "ok", "message": str}` | 200, 404 |
| `GET` | `/api/dashboard/stats` | `api_dashboard_stats()` | Computes KPI totals, top 5 diseases, and 14-day timeline | None | `{"status": "ok", "stats": {"total_farms": int, "total_scans": int, "timeline": [...], "alerts": [...]}}` | 200 |

---

### D. Detailed Trace of Endpoint: `POST /api/predict`

Here is the exact line-by-line flow through [app.py:predict()](file:///d:/projects/blight/Leafscan-main/web-app/backend/app.py#L261-L311):

1. **Check Upload Presence:**
   ```python
   if 'image' not in request.files:
       return jsonify({'error': 'Please upload a tomato leaf image.'}), 400
   ```
   If the HTTP multipart request contains no part named `image`, Flask aborts with HTTP 400.
2. **Check Empty Filename:**
   ```python
   uploaded = request.files['image']
   if uploaded.filename == '':
       return jsonify({'error': 'No image file was selected.'}), 400
   ```
   If a user submits an empty form without browsing for a file, it aborts with HTTP 400.
3. **Parse Image Stream via Pillow:**
   ```python
   try:
       image = Image.open(uploaded.stream).convert('RGB')
   except UnidentifiedImageError:
       return jsonify({'error': 'The uploaded file is not a valid image.'}), 400
   ```
   Pillow parses the byte stream. If someone uploads a text file or malware disguised with a `.jpg` extension, Pillow raises `UnidentifiedImageError`, safely rejecting the upload.
4. **Execute Neural Network Inference:**
   `result = build_result_for_image(image)` resizes the image to $224 \times 224$, runs `model.predict()`, evaluates the probabilities, checks the $0.50$ threshold, and attaches agronomic treatment guidance from `DAMAGE_DB`.
5. **Save Image to Disk:**
   ```python
   ext = os.path.splitext(uploaded.filename.lower())[1] or '.jpg'
   saved_filename = f"leaf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
   saved_filepath = os.path.join(UPLOADS_DIR, saved_filename)
   image.save(saved_filepath, quality=90)
   ```
   Generates a safe unique filename avoiding path traversal vulnerabilities.
6. **Save Record to Database:**
   Calls `db.save_scan(...)`, inserting the scan record into SQLite and associating it with `farm_id` if provided.
7. **Return Payload:**
   Attaches `scan_id` and `image_url` (`/static/uploads/...`) to `result` and returns HTTP 200 JSON.
