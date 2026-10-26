import io
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
    """Run the suite against a throw-away database + uploads folder (real data is never touched)."""
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
    print("==========================================")
    print("Running Tomato Leaf Scan Web Test Suite")
    print("==========================================")
    
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

    # 1. Health check
    res = client.get('/health')
    assert_test("GET /health status 200", res.status_code == 200)
    data = res.get_json()
    assert_test("Health check model exists", data.get('model_exists') is True)
    assert_test("Health check DB initialized", data.get('db_initialized') is True)

    # 2. Page route checks
    res = client.get('/')
    assert_test("GET / (Landing page) status 200", res.status_code == 200)
    assert_test("Landing page contains hero title", b"Detect tomato leaf diseases early" in res.data)
    assert_test("Landing page contains Scan CTA", b"Scan a Leaf" in res.data)
    assert_test("Landing page contains How It Works", b"How Tomato Leaf Scan Works" in res.data)
    assert_test("Landing page contains Features", b"Tomato Farm Management" in res.data)

    res = client.get('/scan')
    assert_test("GET /scan (Scanner page) status 200", res.status_code == 200)
    assert_test("Scanner page contains upload box", b"id=\"image-input\"" in res.data)
    assert_test("Scanner page contains farm selector", b"id=\"farm-select\"" in res.data)
    assert_test("Scanner page contains results panel", b"id=\"results\"" in res.data)

    res = client.get('/farms')
    assert_test("GET /farms (Tomato Farm page) status 200", res.status_code == 200)
    assert_test("Farms page contains title", b"Tomato Farm Management" in res.data)
    assert_test("Farms page contains modal", b"id=\"farm-modal\"" in res.data)

    res = client.get('/monitoring')
    assert_test("GET /monitoring (Crop Monitoring page) status 200", res.status_code == 200)
    assert_test("Monitoring page contains title", b"Crop Monitoring Dashboard" in res.data)
    assert_test("Monitoring page contains Chart.js canvas", b"healthDistributionChart" in res.data)

    res = client.get('/history')
    assert_test("GET /history (Scan History page) status 200", res.status_code == 200)
    assert_test("History page contains title", b"Scan Diagnostic History" in res.data)
    assert_test("History page contains filter toolbar", b"id=\"search-input\"" in res.data)
    assert_test("History page contains detail modal", b"id=\"scan-detail-modal\"" in res.data)

    # 3. Farm CRUD API testing
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
    assert_test("POST /api/farms status 201", res.status_code == 201)
    farm_id = res.get_json().get('farm_id')
    assert_test("Farm ID returned", isinstance(farm_id, int) and farm_id > 0)

    res = client.get('/api/farms')
    assert_test("GET /api/farms status 200", res.status_code == 200)
    farms = res.get_json().get('farms', [])
    assert_test("Created farm in list", any(f['id'] == farm_id and f['name'] == 'Green Horizon Farm' for f in farms))

    res = client.get(f'/api/farms/{farm_id}')
    assert_test(f"GET /api/farms/{farm_id} status 200", res.status_code == 200)
    assert_test("Correct farm retrieved", res.get_json()['farm']['variety'] == 'Roma VF')

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
    assert_test("Farm update persisted", res.get_json()['farm']['name'] == 'Green Horizon Organic Estate')
    assert_test("Farm plant count updated", res.get_json()['farm']['plant_count'] == 720)

    # 4. Predict & Scan persistence API testing
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
    assert_test("Physical leaf image saved in static/uploads", file_exists)

    # 5. Scan History API testing
    res = client.get('/api/scans')
    assert_test("GET /api/scans status 200", res.status_code == 200)
    scans = res.get_json().get('scans', [])
    assert_test("Saved scan appears in scan list", any(s['id'] == scan_id for s in scans))

    res = client.get(f'/api/scans?farm_id={farm_id}')
    assert_test(f"GET /api/scans?farm_id={farm_id} status 200", res.status_code == 200)
    farm_scans = res.get_json().get('scans', [])
    assert_test("Scan correctly filtered by farm", all(s['farm_id'] == farm_id for s in farm_scans))

    res = client.get(f'/api/scans/{scan_id}')
    assert_test(f"GET /api/scans/{scan_id} status 200", res.status_code == 200)
    scan_detail = res.get_json().get('scan', {})
    assert_test("Scan detail has raw_json advice", 'raw_json' in scan_detail and isinstance(scan_detail['raw_json'], dict))

    # 6. Dashboard Stats API testing
    res = client.get('/api/dashboard/stats')
    assert_test("GET /api/dashboard/stats status 200", res.status_code == 200)
    stats = res.get_json().get('stats', {})
    assert_test("Dashboard total_farms >= 1", stats.get('total_farms', 0) >= 1)
    assert_test("Dashboard total_scans >= 1", stats.get('total_scans', 0) >= 1)
    assert_test("Dashboard recent_scans non-empty", len(stats.get('recent_scans', [])) >= 1)
    assert_test("Dashboard timeline calculated", isinstance(stats.get('timeline'), list))

    # 7. Safe Delete testing
    res = client.delete(f'/api/scans/{scan_id}')
    assert_test(f"DELETE /api/scans/{scan_id} status 200", res.status_code == 200)
    res = client.get(f'/api/scans/{scan_id}')
    assert_test("Scan record was deleted (404)", res.status_code == 404)
    file_still_exists = os.path.exists(os.path.join(app.UPLOADS_DIR, saved_filename))
    assert_test("Image file safely cleaned up after scan deletion", not file_still_exists)

    res = client.delete(f'/api/farms/{farm_id}')
    assert_test(f"DELETE /api/farms/{farm_id} status 200", res.status_code == 200)
    res = client.get(f'/api/farms/{farm_id}')
    assert_test("Farm was deleted (404)", res.status_code == 404)

    print("==========================================")
    print(f"ALL {passed}/{total} TESTS PASSED SUCCESSFULLY!")
    print("==========================================")


if __name__ == '__main__':
    run_tests()
