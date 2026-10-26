# Render Deployment & Production Operations Guide

**Application:** LeafScan — Tomato Leaf Disease Detection and Farm Monitoring System  
**Target Platform:** Render Cloud Application Platform (Web Service)  

---

## 1. Production Architecture on Render

```
                             Render Cloud Platform
+-------------------------------------------------------------------------------+
|                                                                               |
|   Web Service (Gunicorn + wsgi:app)                                           |
|   - Port binding: 0.0.0.0:$PORT                                               |
|   - Workers: 1, Threads: 2 (optimized for TensorFlow RAM limits)             |
|   - Health Check Endpoint: /health                                            |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   | Persistent Disk Mount: /var/data (Render Persistent Storage)          |   |
|   | - Database: /var/data/database/leafscan.db                            |   |
|   | - Uploads:  /var/data/uploads/leaf_*.jpg                              |   |
|   +-----------------------------------------------------------------------+   |
|                                                                               |
+-------------------------------------------------------------------------------+
```

---

## 2. Critical Render Storage Consideration: Ephemeral vs. Persistent

> [!WARNING]
> By default, standard Render Web Services run on ephemeral filesystems. Any files written inside the container (such as newly uploaded leaf photos and new SQLite rows) will be lost when Render spins down the service or redeploys!

### The Solution:
1. Attach a **Render Persistent Disk** mounted at `/var/data` (available on Render standard plans).
2. Configure the environment variable:
   ```text
   LEAFSCAN_DATA_DIR=/var/data
   ```
3. The LeafScan database layer automatically redirects:
   - Database $\rightarrow$ `/var/data/database/leafscan.db`
   - Uploaded Images $\rightarrow$ `/var/data/uploads/`
4. If running on Render Free Tier (without Persistent Disks):
   - SQLite and uploads will reside in the container directory (`web-app/database/` and `web-app/frontend/static/uploads/`).
   - Note that data resets on restart unless an external PostgreSQL or cloud bucket (S3/Cloudinary) is integrated.

---

## 3. Recommended Render Configuration

### 3.1 Web Service Settings
- **Environment:** `Python 3` (Native) or `Docker`
- **Region:** Closest to target users (e.g., Frankfurt, Ohio, Oregon)
- **Branch:** `main`
- **Build Command:**
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```
- **Start Command (Native):**
  ```bash
  gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 wsgi:app
  ```
- **Health Check Path:**
  ```text
  /health
  ```

### 3.2 Environment Variables
| Variable Name | Recommended Value | Purpose |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Matches pinned runtime |
| `SECRET_KEY` | *(Generate 32-byte hex secret)* | Encrypts user session cookies and CSRF tokens |
| `LEAFSCAN_DATA_DIR` | `/var/data` *(if disk attached)* | Directs database and uploads to persistent storage |
| `TF_ENABLE_ONEDNN_OPTS`| `0` | Suppresses floating-point variance warnings in logs |

---

## 4. Docker Deployment Alternative

If deploying via Docker on Render:
1. Render automatically builds from `Dockerfile` located in the root repository.
2. The `Dockerfile` is pre-configured with:
   - Base image: `python:3.11-slim`
   - Imaging libraries: `libgl1`, `libglib2.0-0`
   - Dynamic port binding:
     ```dockerfile
     CMD exec gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 2 --timeout 120 wsgi:app
     ```

---

## 5. Memory & RAM Optimization (TensorFlow CPU)

Running TensorFlow in production requires disciplined worker management:
- **Workers:** Set strictly to `--workers 1`. Multiple Gunicorn workers each load a separate copy of TensorFlow and MobileNetV2 into RAM (~450MB each), which can cause Out-Of-Memory (OOM) crashes on 512MB RAM tiers.
- **Threads:** Set to `--threads 2` or `--threads 4`. Threading shares the single model instance in memory while concurrently handling HTTP requests.
- **Timeout:** Set to `--timeout 120` to prevent worker restarts during cold-start model loading.

---

## 6. Database Backups & Maintenance

1. **Automatic Schema Migrations:**
   Every time the application boots on Render, `db.init_db()` runs automatically. It safely checks and adds missing columns (`user_id`, `platform`, `model_name`, `sync_id`) without dropping tables or altering existing scans and farms.
2. **Manual SQLite Backup Command:**
   ```bash
   sqlite3 /var/data/database/leafscan.db ".backup '/var/data/database/leafscan_backup_$(date +%Y%m%d).db'"
   ```
