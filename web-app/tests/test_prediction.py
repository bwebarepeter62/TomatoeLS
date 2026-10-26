"""
Prediction tests for LeafScan (standard-library unittest, no extra packages needed).

Run from the project root:
    python -m unittest discover -s web-app/tests -p "test_prediction.py" -v

What is tested
--------------
* class index -> label mapping and confidence selection      (pure logic, no model)
* uncertainty threshold and invalid model output handling     (pure logic, no model)
* image preprocessing (shape, dtype, 0-1 range, RGB, NCHW)    (no model)
* API: invalid / unsupported uploads, missing file, JSON keys (real Flask test client)
* API: missing model file -> generic error, no path leaked    (real Flask test client)
* Real model on LABELED REAL-WORLD FIELD photos (PlantDoc sample)
                                                             (skipped if ai-model/eval_data_field is absent)

IMPORTANT HONESTY NOTE
The field-photo test is a regression guard on a small sample, not a proof of accuracy. Its main
purpose is to make sure healthy field leaves are NOT confidently called blight (the failure of
the previous 3-class model). The model is still imperfect on field photos; see ai-model/README.md.
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

LABELED_DIR = os.path.join(PROJECT_ROOT, 'ai-model', 'eval_data_field')
FOLDER_FOR_LABEL = {
    'Early Blight': 'Tomato___Early_blight',
    'Late Blight': 'Tomato___Late_blight',
    'Healthy Leaf': 'Tomato___healthy',
}
BLIGHT_LABELS = ('Early Blight', 'Late Blight')
N = len(leafscan.CLASS_NAMES)


def jpeg_bytes(size=(300, 200), color=(60, 140, 60), mode='RGB', fmt='JPEG'):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format=fmt)
    buf.seek(0)
    return buf


class ClassMappingTests(unittest.TestCase):
    def test_class_order_is_the_documented_one(self):
        # Order of the model's output channels 4..18 (see ai-model/README.md).
        self.assertEqual(leafscan.CLASS_NAMES, [
            'Aphids', 'Early Blight', 'Healthy Leaf', 'Leaf Curl', 'Leafhoppers and Jassids',
            'Molds', 'Mosaic Virus', 'Septoria', 'Bacterial Canker', 'Bacterial Spot',
            'Flea Beetle', 'Late Blight', 'Leafminer', 'Powdery Mildew', 'Yellow Curl Virus',
        ])
        self.assertEqual(leafscan.HEALTHY_INDEX, 2)

    def test_every_class_has_treatment_guidance(self):
        for name in leafscan.CLASS_NAMES:
            self.assertIn(name, leafscan.DAMAGE_DB, name)

    def test_each_index_maps_to_its_own_label_and_confidence(self):
        for idx, name in enumerate(leafscan.CLASS_NAMES):
            scores = np.full(N, 0.05)
            scores[idx] = 0.90
            out = leafscan.interpret_scores(scores, threshold=0.5)
            self.assertEqual(out['index'], idx)
            self.assertEqual(out['label'], name)
            self.assertAlmostEqual(out['confidence'], 0.90)  # taken from the winning class
            self.assertFalse(out['uncertain'])

    def test_model_class_count_matches_label_list(self):
        model = leafscan.ensure_model_loaded()
        self.assertEqual(model.output_shape[1], 4 + len(leafscan.CLASS_NAMES))
        self.assertEqual(model.input_shape[1:], (3, 640, 640))

    def test_score_classes_takes_best_anchor_per_class_and_ignores_boxes(self):
        raw = np.zeros((1, 4 + N, 50), dtype=np.float32)
        raw[0, :4, :] = 600.0          # box coordinates must be ignored
        raw[0, 4 + 11, 7] = 0.8        # Late Blight, best anchor 7
        raw[0, 4 + 11, 9] = 0.3
        raw[0, 4 + 2, 3] = 0.4         # Healthy Leaf
        scores = leafscan.score_classes(raw)
        self.assertEqual(scores.shape, (N,))
        self.assertAlmostEqual(float(scores[11]), 0.8, places=5)
        self.assertAlmostEqual(float(scores[2]), 0.4, places=5)
        self.assertEqual(int(np.argmax(scores)), 11)


class UncertaintyTests(unittest.TestCase):
    def _scores(self, **top):
        scores = np.full(N, 0.02)
        for idx, val in top.items():
            scores[int(idx[1:])] = val
        return scores

    def test_low_top_score_is_uncertain(self):
        out = leafscan.interpret_scores(self._scores(i11=0.20, i2=0.15), threshold=0.25)
        self.assertTrue(out['uncertain'])

    def test_high_top_score_is_not_uncertain(self):
        out = leafscan.interpret_scores(self._scores(i2=0.90), threshold=0.25)
        self.assertFalse(out['uncertain'])

    def test_threshold_is_configurable(self):
        scores = self._scores(i11=0.60)
        self.assertTrue(leafscan.interpret_scores(scores, threshold=0.8)['uncertain'])
        self.assertFalse(leafscan.interpret_scores(scores, threshold=0.5)['uncertain'])

    def test_invalid_model_output_is_rejected_not_mislabelled(self):
        for bad in ([0.5, 0.5], [2.0] + [0.0] * (N - 1), [-1.0] + [0.0] * (N - 1),
                    [float('nan')] + [0.5] * (N - 1)):
            with self.assertRaises(ValueError, msg=f'{bad} should be rejected'):
                leafscan.interpret_scores(bad)


class PreprocessingTests(unittest.TestCase):
    def test_shape_dtype_and_range(self):
        img = Image.new('RGB', (640, 480), (255, 0, 128))
        arr = leafscan.preprocess_image(img)
        self.assertEqual(arr.shape, (1, 3, 640, 640))
        self.assertEqual(arr.dtype, np.float32)
        self.assertAlmostEqual(float(arr.max()), 1.0, places=5)   # scaled to 0-1
        self.assertGreaterEqual(float(arr.min()), 0.0)
        # channels-first, RGB order preserved
        self.assertAlmostEqual(float(arr[0, 0, 0, 0]), 1.0, places=5)
        self.assertAlmostEqual(float(arr[0, 1, 0, 0]), 0.0, places=5)
        self.assertAlmostEqual(float(arr[0, 2, 0, 0]), 128 / 255, places=3)

    def test_other_color_modes_become_three_channels(self):
        for mode, color in (('L', 100), ('RGBA', (10, 200, 30, 128)), ('P', 5)):
            arr = leafscan.preprocess_image(Image.new(mode, (50, 70), color))
            self.assertEqual(arr.shape, (1, 3, 640, 640), mode)


class ApiTests(unittest.TestCase):
    """Uses a throw-away database and upload folder so real scan history is never touched."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='leafscan_test_')
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

    def post(self, data, filename='leaf.jpg'):
        payload = {'image': (data, filename)} if data is not None else {}
        return self.client.post('/api/predict', data=payload, content_type='multipart/form-data')

    def test_valid_image_returns_expected_json_structure(self):
        res = self.post(jpeg_bytes())
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        for key in ('status', 'label', 'prediction', 'message', 'confidence', 'confidence_score',
                    'disease', 'available', 'predictions', 'class_index', 'is_healthy',
                    'probabilities', 'scan_id', 'image_url'):
            self.assertIn(key, body)
        self.assertEqual(len(body['predictions']), N)
        self.assertEqual(len(body['probabilities']), N)
        # the confidence shown must be the score of the class that was picked
        picked_name = leafscan.CLASS_NAMES[body['class_index']]
        self.assertAlmostEqual(body['confidence'], body['probabilities'][picked_name] * 100, places=1)
        # predictions are sorted best-first
        scores = [p['probability'] for p in body['predictions']]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_uncertain_result_is_never_reported_as_healthy(self):
        old = leafscan.CONFIDENCE_THRESHOLD
        leafscan.CONFIDENCE_THRESHOLD = 1.01  # force every prediction to be "uncertain"
        try:
            body = self.post(jpeg_bytes()).get_json()
        finally:
            leafscan.CONFIDENCE_THRESHOLD = old
        self.assertTrue(body['uncertain'])
        self.assertFalse(body['available'])
        self.assertFalse(body['is_healthy'])
        self.assertNotEqual(body['label'], leafscan.HEALTHY_LABEL)
        self.assertEqual(body['label'], 'No clear disease found')

    def test_no_file(self):
        res = self.post(None)
        self.assertEqual(res.status_code, 400)

    def test_empty_filename(self):
        res = self.post(jpeg_bytes(), filename='')
        self.assertEqual(res.status_code, 400)

    def test_unsupported_extension(self):
        res = self.post(jpeg_bytes(fmt='GIF', mode='P', color=3), filename='leaf.gif')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Unsupported', res.get_json()['error'])

    def test_filename_without_extension_is_rejected(self):
        res = self.post(jpeg_bytes(), filename='leaf')
        self.assertEqual(res.status_code, 400)

    def test_text_file_pretending_to_be_jpg(self):
        res = self.post(io.BytesIO(b'this is not an image'), filename='leaf.jpg')
        self.assertEqual(res.status_code, 400)
        self.assertIn('not a valid image', res.get_json()['error'])

    def test_corrupted_jpeg(self):
        good = jpeg_bytes().getvalue()
        res = self.post(io.BytesIO(good[: len(good) // 3]), filename='leaf.jpg')
        self.assertIn(res.status_code, (400, 500))
        self.assertIn('error', res.get_json())

    def test_bad_pagination_values_are_a_400_not_a_crash(self):
        self.assertEqual(self.client.get('/api/scans?limit=abc').status_code, 400)

    def test_missing_model_gives_generic_error_without_leaking_path(self):
        saved_model, saved_candidates = leafscan.MODEL, leafscan.MODEL_CANDIDATES
        leafscan.MODEL = None
        leafscan.MODEL_CANDIDATES = [os.path.join(self.tmp, 'definitely_missing', 'model.tflite')]
        try:
            res = self.post(jpeg_bytes())
        finally:
            leafscan.MODEL, leafscan.MODEL_CANDIDATES = saved_model, saved_candidates
        self.assertEqual(res.status_code, 500)
        error = res.get_json()['error']
        self.assertNotIn('definitely_missing', error)
        self.assertNotIn(self.tmp, error)


class DatabaseResetTests(unittest.TestCase):
    """reset_db() must wipe data, keep a backup and leave a usable empty schema."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='leafscan_reset_')
        self._old = (db.DB_PATH, db.DATABASE_DIR, db.UPLOADS_DIR)
        db.DATABASE_DIR = self.tmp
        db.DB_PATH = os.path.join(self.tmp, 'test.db')
        db.UPLOADS_DIR = os.path.join(self.tmp, 'uploads')
        db.init_db()

    def tearDown(self):
        db.DB_PATH, db.DATABASE_DIR, db.UPLOADS_DIR = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reset_wipes_data_and_keeps_backup(self):
        db.create_farm('Test farm')
        with open(os.path.join(db.UPLOADS_DIR, 'leaf_x.jpg'), 'wb') as fh:
            fh.write(b'x')
        self.assertEqual(len(db.list_farms()), 1)

        backup = db.reset_db(backup=True)

        self.assertEqual(db.list_farms(), [])
        self.assertEqual(db.list_scans(), [])
        self.assertFalse(os.path.exists(os.path.join(db.UPLOADS_DIR, 'leaf_x.jpg')))
        self.assertTrue(backup and os.path.exists(backup))

    def test_reset_without_backup(self):
        db.create_farm('Test farm')
        self.assertIsNone(db.reset_db(backup=False))
        self.assertEqual(db.list_farms(), [])


@unittest.skipUnless(os.path.isdir(LABELED_DIR),
                     'ai-model/eval_data_field not found - run: python ai-model/download_eval_samples.py plantdoc')
class LabeledFieldImageTests(unittest.TestCase):
    """Real model, real labeled FIELD photos (PlantDoc sample). Each image is judged on its own.

    Thresholds are set well below the measured full-sample results so the test is stable but
    still catches the earlier failure (healthy leaves called blight ~98% of the time).
    """

    PER_CLASS = 15

    @classmethod
    def setUpClass(cls):
        cls.results = {}
        model = leafscan.ensure_model_loaded()
        for label, folder in FOLDER_FOR_LABEL.items():
            files = sorted(f for f in os.listdir(os.path.join(LABELED_DIR, folder))
                           if f.lower().endswith(('.jpg', '.jpeg', '.png')))
            step = max(1, len(files) // cls.PER_CLASS)
            preds = []
            for name in files[::step][:cls.PER_CLASS]:
                img = Image.open(os.path.join(LABELED_DIR, folder, name))
                scores = leafscan.score_classes(model.predict(leafscan.preprocess_image(img)))
                decision = leafscan.interpret_scores(scores)
                preds.append('uncertain' if decision['uncertain'] else decision['label'])
            cls.results[label] = preds

    def rate(self, true_label, predicate):
        preds = self.results[true_label]
        return sum(predicate(p) for p in preds) / len(preds)

    def test_enough_images(self):
        for label, preds in self.results.items():
            self.assertGreaterEqual(len(preds), 10, label)

    def test_healthy_leaves_are_rarely_called_blight(self):
        # Previous 3-class model: 98% of healthy field leaves were called blight.
        rate = self.rate('Healthy Leaf', lambda p: p in BLIGHT_LABELS)
        self.assertLessEqual(rate, 0.20, self.results['Healthy Leaf'])

    def test_late_blight_is_usually_detected(self):
        rate = self.rate('Late Blight', lambda p: p == 'Late Blight')
        self.assertGreaterEqual(rate, 0.50, self.results['Late Blight'])

    def test_early_blight_is_often_detected(self):
        rate = self.rate('Early Blight', lambda p: p == 'Early Blight')
        self.assertGreaterEqual(rate, 0.30, self.results['Early Blight'])

    def test_model_does_not_return_one_class_for_everything(self):
        every_prediction = [p for preds in self.results.values() for p in preds]
        self.assertGreaterEqual(len(set(every_prediction) - {'uncertain'}), 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
