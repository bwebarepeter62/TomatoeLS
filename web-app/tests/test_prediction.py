"""
Prediction and AI Pipeline Tests for LeafScan
==============================================
Standard-library unittest test suite verifying the 3-class Keras MobileNetV2
architecture (Early Blight, Late Blight, Healthy Leaf).

Run from project root:
    python -m unittest discover -s web-app/tests -p "test_prediction.py" -v
"""

import io
import os
import shutil
import sys
import tempfile
import unittest

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, '..', '..'))
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'web-app', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import numpy as np
from PIL import Image

import app as leafscan
import db

LAB_DIR = os.path.join(PROJECT_ROOT, 'ai-model', 'eval_data')
FIELD_DIR = os.path.join(PROJECT_ROOT, 'ai-model', 'eval_data_field')


def jpeg_bytes(size=(300, 200), color=(60, 140, 60), mode='RGB', fmt='JPEG'):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format=fmt)
    buf.seek(0)
    return buf


class ModelArchitectureTests(unittest.TestCase):
    """Verifies that the loaded Keras model matches the production specification."""

    def test_class_names_and_healthy_index(self):
        self.assertEqual(leafscan.CLASS_NAMES, ['Early Blight', 'Late Blight', 'Healthy Leaf'])
        self.assertEqual(leafscan.HEALTHY_INDEX, 2)
        self.assertEqual(len(leafscan.CLASS_NAMES), 3)

    def test_every_class_has_treatment_guidance(self):
        for name in leafscan.CLASS_NAMES:
            self.assertIn(name, leafscan.DAMAGE_DB, f"Missing treatment guidance for {name}")

    def test_model_input_and_output_shapes(self):
        model = leafscan.ensure_model_loaded()
        self.assertEqual(model.input_shape[1:], (224, 224, 3))
        self.assertEqual(model.output_shape[1], 3)

    def test_custom_layers_math(self):
        divide_layer = leafscan.TrueDivide()
        sub_layer = leafscan.Subtract()
        test_in = np.array([0.0, 127.5, 255.0], dtype=np.float32)
        div_out = divide_layer.call(test_in)
        if hasattr(div_out, 'numpy'):
            div_out = div_out.numpy()
        np.testing.assert_allclose(div_out, [0.0, 1.0, 2.0], atol=1e-5)
        sub_out = sub_layer.call(div_out)
        if hasattr(sub_out, 'numpy'):
            sub_out = sub_out.numpy()
        np.testing.assert_allclose(sub_out, [-1.0, 0.0, 1.0], atol=1e-5)


class PreprocessingTests(unittest.TestCase):
    """Verifies that preprocessing converts raw images into valid (1, 224, 224, 3) arrays."""

    def test_shape_dtype_and_dimensions(self):
        img = Image.new('RGB', (640, 480), (255, 128, 0))
        arr = leafscan.preprocess_image(img)
        self.assertEqual(arr.shape, (1, 224, 224, 3))
        self.assertEqual(arr.dtype, np.float32)
        self.assertAlmostEqual(float(arr.max()), 255.0, places=1)
        self.assertGreaterEqual(float(arr.min()), 0.0)

    def test_color_modes_converted_to_three_channels(self):
        for mode, color in (('L', 128), ('RGBA', (10, 200, 30, 255)), ('P', 5)):
            img = Image.new(mode, (100, 100), color)
            arr = leafscan.preprocess_image(img)
            self.assertEqual(arr.shape, (1, 224, 224, 3), f"Failed for mode {mode}")


class UncertaintyAndDecisionTests(unittest.TestCase):
    """Verifies uncertainty thresholds and diagnosis decision mapping."""

    def test_uncertainty_flagging_when_confidence_low(self):
        old_thresh = leafscan.CONFIDENCE_THRESHOLD
        leafscan.CONFIDENCE_THRESHOLD = 0.999999  # Force uncertainty
        try:
            img = Image.new('RGB', (224, 224), (100, 100, 100))
            res = leafscan.build_result_for_image(img)
            self.assertTrue(res['uncertain'])
            self.assertFalse(res['available'])
            self.assertFalse(res['is_healthy'])
            self.assertEqual(res['label'], 'No clear disease found')
        finally:
            leafscan.CONFIDENCE_THRESHOLD = old_thresh

    def test_confident_prediction_returns_available(self):
        old_thresh = leafscan.CONFIDENCE_THRESHOLD
        leafscan.CONFIDENCE_THRESHOLD = 0.01  # Force confident
        try:
            img = Image.new('RGB', (224, 224), (40, 160, 60))
            res = leafscan.build_result_for_image(img)
            self.assertFalse(res['uncertain'])
            self.assertTrue(res['available'])
            self.assertIn(res['class_index'], [0, 1, 2])
        finally:
            leafscan.CONFIDENCE_THRESHOLD = old_thresh


class ApiPredictionTests(unittest.TestCase):
    """Tests /api/predict using a temporary database."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='leafscan_predtest_')
        cls._old = (db.DB_PATH, db.DATABASE_DIR, db.UPLOADS_DIR, leafscan.UPLOADS_DIR)
        db.DATABASE_DIR = cls.tmp
        db.DB_PATH = os.path.join(cls.tmp, 'test.db')
        db.UPLOADS_DIR = leafscan.UPLOADS_DIR = os.path.join(cls.tmp, 'uploads')
        db.init_db()
        cls.client = leafscan.app.test_client()

    @classmethod
    def tearDownClass(cls):
        db.DB_PATH, db.DATABASE_DIR, db.UPLOADS_DIR, leafscan.UPLOADS_DIR = cls._old
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def post_image(self, data, filename='leaf.jpg', farm_id=None):
        payload = {}
        if data is not None:
            payload['image'] = (data, filename)
        if farm_id is not None:
            payload['farm_id'] = str(farm_id)
        return self.client.post('/api/predict', data=payload, content_type='multipart/form-data')

    def test_valid_image_upload_returns_expected_contract(self):
        res = self.post_image(jpeg_bytes())
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        expected_keys = ('status', 'label', 'prediction', 'message', 'confidence',
                         'confidence_score', 'disease', 'available', 'uncertain',
                         'predictions', 'class_index', 'is_healthy', 'scan_id', 'image_url')
        for key in expected_keys:
            self.assertIn(key, data, f"Missing key '{key}' in prediction response")

        self.assertEqual(len(data['predictions']), 3)
        self.assertTrue(data['image_url'].startswith('/static/uploads/'))
        self.assertTrue(isinstance(data['scan_id'], int))

    def test_missing_image_payload_returns_400(self):
        res = self.post_image(None)
        self.assertEqual(res.status_code, 400)
        self.assertIn('error', res.get_json())

    def test_empty_filename_returns_400(self):
        res = self.post_image(jpeg_bytes(), filename='')
        self.assertEqual(res.status_code, 400)
        self.assertIn('error', res.get_json())

    def test_corrupted_non_image_file_returns_400(self):
        res = self.post_image(io.BytesIO(b'not an image payload'), filename='bad.jpg')
        self.assertEqual(res.status_code, 400)
        self.assertIn('not a valid image', res.get_json()['error'])


class DatabaseResetTests(unittest.TestCase):
    """Verifies that reset_db cleans data, keeps backups, and leaves schema operable."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='leafscan_dbreset_')
        self._old = (db.DB_PATH, db.DATABASE_DIR, db.UPLOADS_DIR)
        db.DATABASE_DIR = self.tmp
        db.DB_PATH = os.path.join(self.tmp, 'test.db')
        db.UPLOADS_DIR = os.path.join(self.tmp, 'uploads')
        db.init_db()

    def tearDown(self):
        db.DB_PATH, db.DATABASE_DIR, db.UPLOADS_DIR = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reset_db_preserves_backup_and_cleans_tables(self):
        db.create_farm('Test Plot')
        self.assertEqual(len(db.list_farms()), 1)

        backup_file = db.reset_db(backup=True)
        self.assertTrue(backup_file and os.path.exists(backup_file))
        self.assertEqual(db.list_farms(), [])
        self.assertEqual(db.list_scans(), [])


@unittest.skipUnless(os.path.isdir(LAB_DIR), 'ai-model/eval_data not found')
class LabDatasetBenchmarkTests(unittest.TestCase):
    """Regression test: Confirms high accuracy on the PlantVillage lab dataset."""

    def test_lab_healthy_leaves_accuracy(self):
        healthy_dir = os.path.join(LAB_DIR, 'Tomato___healthy')
        files = [f for f in os.listdir(healthy_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))][:15]
        correct = 0
        for f in files:
            img = Image.open(os.path.join(healthy_dir, f))
            res = leafscan.build_result_for_image(img)
            if res['is_healthy'] or 'healthy' in res['label'].lower():
                correct += 1
        acc = correct / len(files) if files else 0.0
        self.assertGreaterEqual(acc, 0.90, f"Expected >= 90% accuracy on lab healthy leaves, got {acc:.0%}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
