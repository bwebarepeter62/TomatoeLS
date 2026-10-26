import hashlib
import io
import json
import os
import shutil
import sys
import tempfile

# Add backend directory to sys.path so tests import app and db correctly
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(TEST_DIR, '..', 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from PIL import Image
import app
import db


def run_tests():
    """Run the suite against a throw-away database + uploads folder (real production data is never touched)."""
    tmp = tempfile.mkdtemp(prefix='leafscan_webtest_')
    saved = (db.DB_PATH, db.DATABASE_DIR, db.UPLOADS_DIR, app.UPLOADS_DIR)
    db.DATABASE_DIR = tmp
    db.DB_PATH = os.path.join(tmp, 'test.db')
    db.UPLOADS_DIR = app.UPLOADS_DIR = os.path.join(tmp, 'uploads')
    db.init_db()
    try:
        _run_tests()
    finally:
        db.DB_PATH, db.DATABASE_DIR, db.UPLOADS_DIR, app.UPLOADS_DIR = saved
        shutil.rmtree(tmp, ignore_errors=True)


def _run_tests():
    print("==================================================")
    print("Running LeafScan Production Test Suite (Tasks 1-13)")
    print("==================================================")
    
    client = app.app.test_client()
    passed = 0
    total = 0

    def assert_test(name, condition, extra=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"[PASS] {name} {extra}")
        else:
            print(f"[FAIL] {name} {extra}")
            raise AssertionError(f"Test failed: {name} {extra}")

    # ==========================================================
    # 1. AI MODEL INTEGRITY CHECK (CONSTRAINT COMPLIANCE)
    # ==========================================================
    model_path = app.MODEL_PATH
    bak_path = model_path + '.bak_stage1'
    if os.path.exists(bak_path):
        with open(model_path, 'rb') as f1, open(bak_path, 'rb') as f2:
            h1 = hashlib.sha256(f1.read()).hexdigest()
            h2 = hashlib.sha256(f2.read()).hexdigest()
        assert_test("AI Model SHA-256 Checksum Unchanged", h1 == h2, f"({h1[:10]}...)")
    else:
        assert_test("AI Model exists at MODEL_PATH", os.path.exists(model_path))

    # ==========================================================
    # 2. HEALTH CHECK & BASE ROUTES
    # ==========================================================
    res = client.get('/health')
    assert_test("GET /health status 200", res.status_code == 200)
    data = res.get_json()
    assert_test("Health check model exists", data.get('model_exists') is True)
    assert_test("Health check DB initialized", data.get('db_initialized') is True)

    res = client.get('/')
    assert_test("GET / (Landing page) status 200", res.status_code == 200)
    assert_test("Landing page contains hero title", b"Detect tomato leaf diseases early" in res.data)
    assert_test("Landing page contains Scan CTA", b"Scan a Leaf" in res.data)

    # ==========================================================
    # 3. TASK 1: SCANNING NOTICE VERIFICATION
    # ==========================================================
    res = client.get('/scan')
    assert_test("GET /scan (Scanner page) status 200", res.status_code == 200)
    assert_test("Scan page contains 'IMPORTANT SCANNING NOTICE'", b"IMPORTANT SCANNING NOTICE" in res.data)
    assert_test("Scan page contains advisory disclaimer", b"AI predictions are advisory and may be incorrect" in res.data)
    assert_test("Scan page contains button reminder text", b"Upload tomato leaf images with suspected blight symptoms only" in res.data)
    assert_test("Scan page has Download Report button element", b"download-report-btn" in res.data)

    # ==========================================================
    # 4. TASK 2: AUTHENTICATION & ACCESS CONTROL
    # ==========================================================
    # 4a. Anonymous user visiting protected routes should be redirected to login
    res = client.get('/farms')
    assert_test("GET /farms unauthenticated redirects to /login (302)", res.status_code == 302 and '/login' in res.location)

    res = client.get('/monitoring')
    assert_test("GET /monitoring unauthenticated redirects to /login (302)", res.status_code == 302 and '/login' in res.location)

    res = client.get('/history')
    assert_test("GET /history unauthenticated redirects to /login (302)", res.status_code == 302 and '/login' in res.location)

    # 4b. GET /login and GET /register
    res = client.get('/login')
    assert_test("GET /login renders 200", res.status_code == 200)
    assert_test("Login page has username_or_email input", b"name=\"username_or_email\"" in res.data)

    res = client.get('/register')
    assert_test("GET /register renders 200", res.status_code == 200)
    assert_test("Register page has username input", b"name=\"username\"" in res.data)

    # 4c. Register a new user
    csrf_tok = 'test_csrf_token_123'
    with client.session_transaction() as sess:
        sess['_csrf_token'] = csrf_tok
    
    reg_data = {
        'csrf_token': csrf_tok,
        'username': 'john_farmer',
        'email': 'john@agrifarm.test',
        'full_name': 'John Farmer',
        'password': 'SecurePassword123!',
        'confirm_password': 'SecurePassword123!'
    }
    res = client.post('/register', data=reg_data, follow_redirects=True)
    assert_test("POST /register redirects to /farms on success", res.status_code == 200)
    assert_test("User session active after registration", b"john_farmer" in res.data or b"John Farmer" in res.data)

    # Verify user in database and password hashed
    user = db.get_user_by_username('john_farmer')
    assert_test("User saved in SQLite users table", user is not None and user['email'] == 'john@agrifarm.test')
    assert_test("Password securely hashed (not plain text)", user['password_hash'] != 'SecurePassword123!' and user['password_hash'].startswith('scrypt:'))

    # 4d. Test Profile page for authenticated user
    res = client.get('/profile')
    assert_test("GET /profile renders 200 for authenticated user", res.status_code == 200)
    assert_test("Profile contains user's email", b"john@agrifarm.test" in res.data)

    # 4e. Test Logout
    res = client.get('/logout', follow_redirects=True)
    assert_test("GET /logout clears session and redirects to home", res.status_code == 200)

    # 4f. Test Login with credentials
    with client.session_transaction() as sess:
        sess['_csrf_token'] = csrf_tok

    login_data = {
        'csrf_token': csrf_tok,
        'username_or_email': 'john_farmer',
        'password': 'SecurePassword123!'
    }
    res = client.post('/login', data=login_data, follow_redirects=True)
    assert_test("POST /login authenticates successfully", res.status_code == 200 and b"Tomato Farm Management" in res.data)

    res = client.get('/monitoring')
    assert_test("GET /monitoring renders 200 for authenticated user", res.status_code == 200)

    res = client.get('/history')
    assert_test("GET /history renders 200 for authenticated user", res.status_code == 200)

    # ==========================================================
    # 5. TASK 3: FARM MANAGEMENT (AUTHENTICATED & ISOLATED)
    # ==========================================================
    farm_payload = {
        'name': 'Green Horizon Farm',
        'location': 'Southern Valley, Block 4',
        'size': '3.2 Acres',
        'variety': 'Roma VF',
        'planting_date': '2026-03-01',
        'plant_count': 650,
        'notes': 'Drip irrigated beds with organic straw mulch.'
    }
    res = client.post('/api/farms', json=farm_payload)
    assert_test("POST /api/farms creates farm (201)", res.status_code == 201)
    farm_id = res.get_json().get('farm_id')
    assert_test("Farm ID returned", isinstance(farm_id, int) and farm_id > 0)

    res = client.get('/api/farms')
    assert_test("GET /api/farms returns 200", res.status_code == 200)
    farms = res.get_json().get('farms', [])
    assert_test("Created farm exists in list", any(f['id'] == farm_id and f['name'] == 'Green Horizon Farm' for f in farms))

    res = client.get(f'/api/farms/{farm_id}')
    assert_test(f"GET /api/farms/{farm_id} returns 200", res.status_code == 200)
    assert_test("Correct farm variety retrieved", res.get_json()['farm']['variety'] == 'Roma VF')

    update_payload = {
        'name': 'Green Horizon Organic Estate',
        'location': 'Southern Valley, Block 4',
        'size': '3.5 Acres',
        'variety': 'Roma VF & San Marzano',
        'planting_date': '2026-03-01',
        'plant_count': 720,
        'notes': 'Expanded planting area.'
    }
    res = client.put(f'/api/farms/{farm_id}', json=update_payload)
    assert_test(f"PUT /api/farms/{farm_id} status 200", res.status_code == 200)
    res = client.get(f'/api/farms/{farm_id}')
    assert_test("Farm update persisted in database", res.get_json()['farm']['name'] == 'Green Horizon Organic Estate')
    assert_test("Farm plant count updated", res.get_json()['farm']['plant_count'] == 720)

    # ==========================================================
    # 6. TASK 8: SECURITY & IMAGE UPLOAD VALIDATION
    # ==========================================================
    # 6a. Reject non-image extension (.txt)
    invalid_file = (io.BytesIO(b"Hello text file"), "test.txt")
    res = client.post('/api/predict', data={'image': invalid_file}, content_type='multipart/form-data')
    assert_test("POST /api/predict rejects invalid file extension (400)", res.status_code == 400)

    # 6b. Reject corrupted image bytes
    corrupt_file = (io.BytesIO(b"Not an image at all but pretending to be jpg"), "fake.jpg")
    res = client.post('/api/predict', data={'image': corrupt_file}, content_type='multipart/form-data')
    assert_test("POST /api/predict rejects corrupted image file (400)", res.status_code == 400)

    # ==========================================================
    # 7. AI PREDICTION & SCAN PERSISTENCE
    # ==========================================================
    test_img = Image.new('RGB', (640, 640), color=(40, 160, 60))
    img_byte_arr = io.BytesIO()
    test_img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    predict_data = {
        'image': (img_byte_arr, 'test_leaf_sample.jpg'),
        'farm_id': str(farm_id)
    }
    res = client.post('/api/predict', data=predict_data, content_type='multipart/form-data')
    assert_test("POST /api/predict status 200", res.status_code == 200)
    pred_res = res.get_json()
    assert_test("Predict response contains status ok", pred_res.get('status') == 'ok')
    assert_test("Predict response contains label", 'label' in pred_res)
    assert_test("Predict response contains confidence", 'confidence' in pred_res)
    assert_test("Predict response contains scan_id", 'scan_id' in pred_res and pred_res['scan_id'] > 0)
    scan_id = pred_res['scan_id']
    assert_test("Predict response contains image_url", pred_res.get('image_url', '').startswith('/static/uploads/'))

    saved_filename = pred_res['image_url'].replace('/static/uploads/', '')
    file_exists = os.path.exists(os.path.join(app.UPLOADS_DIR, saved_filename))
    assert_test("Physical leaf image saved in uploads directory", file_exists)

    # Verify scan record in DB has user_id populated
    scan_in_db = db.get_scan(scan_id)
    assert_test("Saved scan associated with authenticated user_id", scan_in_db['user_id'] == user['id'])

    # ==========================================================
    # 8. TASK 6: PDF DIAGNOSIS REPORT GENERATION
    # ==========================================================
    res = client.get(f'/api/scans/{scan_id}/report')
    assert_test(f"GET /api/scans/{scan_id}/report status 200", res.status_code == 200)
    assert_test("Report has application/pdf content type", res.content_type == 'application/pdf')
    assert_test("Report bytes start with PDF magic number '%PDF-'", res.data.startswith(b'%PDF-'))
    assert_test("Report size is non-trivial (> 2000 bytes)", len(res.data) > 2000)

    # ==========================================================
    # 9. TASK 4 & 5: SCAN HISTORY & CROP MONITORING DASHBOARD
    # ==========================================================
    res = client.get('/api/scans')
    assert_test("GET /api/scans status 200", res.status_code == 200)
    scans = res.get_json().get('scans', [])
    assert_test("Saved scan appears in scan list", any(s['id'] == scan_id for s in scans))

    # Filter scans by farm
    res = client.get(f'/api/scans?farm_id={farm_id}')
    assert_test(f"GET /api/scans?farm_id={farm_id} status 200", res.status_code == 200)
    farm_scans = res.get_json().get('scans', [])
    assert_test("Scan correctly filtered by farm", all(s['farm_id'] == farm_id for s in farm_scans))

    # Dashboard Stats
    res = client.get('/api/dashboard/stats')
    assert_test("GET /api/dashboard/stats status 200", res.status_code == 200)
    stats = res.get_json().get('stats', {})
    assert_test("Dashboard total_farms >= 1", stats.get('total_farms', 0) >= 1)
    assert_test("Dashboard total_scans >= 1", stats.get('total_scans', 0) >= 1)
    assert_test("Dashboard includes early_blight_scans metric", 'early_blight_scans' in stats)
    assert_test("Dashboard includes late_blight_scans metric", 'late_blight_scans' in stats)
    assert_test("Dashboard includes farm_breakdown list", isinstance(stats.get('farm_breakdown'), list))
    assert_test("Dashboard recent_scans non-empty", len(stats.get('recent_scans', [])) >= 1)
    assert_test("Dashboard timeline calculated", isinstance(stats.get('timeline'), list))

    # ==========================================================
    # 10. TASK 7: MOBILE INTEGRATION & SYNCHRONIZATION
    # ==========================================================
    res = client.get('/api/mobile/status')
    assert_test("GET /api/mobile/status status 200", res.status_code == 200)
    mob_status = res.get_json()
    assert_test("Mobile status documents 15-class edge detector model", 'best_int8.tflite' in mob_status.get('mobile_model', ''))
    assert_test("Mobile status documents 3-class web model", 'MobileNetV2' in mob_status.get('web_model', ''))

    # Synchronize batch of mobile scans
    mobile_sync_payload = {
        'scans': [
            {
                'sync_id': 'mob_sync_uuid_001',
                'prediction_label': 'Tomato Early Blight',
                'is_healthy': False,
                'confidence': 92.4,
                'disease_name': 'Early Blight',
                'disease_type': 'fungal',
                'farm_id': farm_id,
                'model_name': 'best_int8.tflite',
                'platform': 'mobile'
            },
            {
                'sync_id': 'mob_sync_uuid_002',
                'prediction_label': 'Tomato Healthy',
                'is_healthy': True,
                'confidence': 97.1,
                'disease_name': 'Healthy Leaf',
                'disease_type': 'none',
                'farm_id': farm_id,
                'model_name': 'best_int8.tflite',
                'platform': 'mobile'
            }
        ]
    }
    res = client.post('/api/mobile/sync', json=mobile_sync_payload)
    assert_test("POST /api/mobile/sync status 200", res.status_code == 200)
    sync_resp = res.get_json()
    assert_test("Mobile sync successfully inserted 2 records", sync_resp.get('synced_count') == 2)

    # Test deduplication on repeated sync
    res = client.post('/api/mobile/sync', json=mobile_sync_payload)
    sync_resp_2 = res.get_json()
    assert_test("Mobile sync deduplicates already synchronized records", sync_resp_2.get('synced_count') == 0)
    assert_test("Mobile sync reported skipped duplicates", len(sync_resp_2.get('skipped_duplicates', [])) == 2)

    # ==========================================================
    # 11. RECORD CLEANUP
    # ==========================================================
    res = client.delete(f'/api/scans/{scan_id}')
    assert_test(f"DELETE /api/scans/{scan_id} status 200", res.status_code == 200)
    res = client.get(f'/api/scans/{scan_id}')
    assert_test("Scan record was deleted (404)", res.status_code == 404)
    file_still_exists = os.path.exists(os.path.join(app.UPLOADS_DIR, saved_filename))
    assert_test("Image file safely cleaned up after scan deletion", not file_still_exists)

    # Test Clear Scan History API
    res = client.post('/api/scans/clear')
    assert_test("POST /api/scans/clear status 200", res.status_code == 200)
    assert_test("Clear response status ok", res.get_json().get('status') == 'ok')
    res = client.get('/api/scans')
    assert_test("Scan history empty after clear", len(res.get_json().get('scans', [])) == 0)

    res = client.delete(f'/api/farms/{farm_id}')
    assert_test(f"DELETE /api/farms/{farm_id} status 200", res.status_code == 200)
    res = client.get(f'/api/farms/{farm_id}')
    assert_test("Farm was deleted (404)", res.status_code == 404)

    print("==================================================")
    print(f"ALL {passed}/{total} PRODUCTION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == '__main__':
    run_tests()
