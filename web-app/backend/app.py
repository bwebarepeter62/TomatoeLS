import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any

import numpy as np
from flask import Flask, jsonify, redirect, render_template, request, url_for
from PIL import Image, UnidentifiedImageError
import tensorflow as tf

import db

# Project-relative path resolution
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_APP_DIR = os.path.abspath(os.path.join(BACKEND_DIR, '..'))
PROJECT_ROOT = os.path.abspath(os.path.join(WEB_APP_DIR, '..'))
TEMPLATE_DIR = os.path.join(WEB_APP_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(WEB_APP_DIR, 'frontend', 'static')
UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')

# Update this path to point to your newly trained .h5 model
MODEL_PATH = os.path.join(BACKEND_DIR, 'tomato_disease_model.h5')

# IMPORTANT: These match the exact Keras class indices from Colab.
CLASS_NAMES = [
    'Early Blight',   # Index 0
    'Late Blight',    # Index 1
    'Healthy Leaf'    # Index 2
]
HEALTHY_INDEX = CLASS_NAMES.index('Healthy Leaf')
HEALTHY_LABEL = 'Healthy leaf - no disease detected.'

# MobileNetV2 takes 224x224
MODEL_INPUT_SIZE = (224, 224)

# Confidence threshold to avoid guessing on random images
CONFIDENCE_THRESHOLD = 0.50

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)

# Initialize Database
if os.environ.get('LEAFSCAN_RESET_DB', '').strip().lower() in ('1', 'true', 'yes', 'on'):
    _backup_path = db.reset_db(backup=True)
db.init_db()

# Pruned Damage DB to only include your 3 classes
DAMAGE_DB = {
    'Early Blight': {
        'name': 'Early blight',
        'type': 'fungal',
        'summary': 'Dark brown spots with concentric rings and yellow halos on lower leaves.',
        'cause': 'Fungus surviving in debris and soil, spread by wind and splash.',
        'effects': ['Lower leaves yellow and drop', 'Reduced photosynthesis'],
        'stopNow': ['Remove worst lower leaves and bag them', 'Spray a protectant fungicide'],
        'preventSpread': ['Do not work when plants are wet', 'Disinfect tools between plants'],
        'preventFuture': ['Rotate 2-3 years without tomato/potato', 'Stake and space for airflow'],
        'treatments': ['Copper fungicide', 'Broad protectant fungicide'],
        'seeExpertIf': 'More than a third of leaves are affected.',
    },
    'Late Blight': {
        'name': 'Late blight',
        'type': 'fungal',
        'summary': 'Large dark water-soaked blotches with pale grey rims spreading from leaf edges.',
        'cause': 'Water mould spread by wind and rain. Explodes in cool, wet weather.',
        'effects': ['Leaves and stems collapse quickly', 'Whole crop loss within a week'],
        'stopNow': ['Act today - it moves fast', 'Pull and bag the worst plants'],
        'preventSpread': ['Bag and burn infected plants', 'Clean boots, tools'],
        'preventFuture': ['Resistant varieties', 'No tomatoes near potatoes'],
        'treatments': ['Systemic + protectant fungicide', 'Copper protectant'],
        'seeExpertIf': 'Contact your extension officer today.',
    },
    'Healthy Leaf': {
        'name': 'Healthy leaf',
        'type': 'none',
        'summary': 'Even green leaf with no spots, curling, moulds, or pests visible.',
        'cause': 'No disease detected.',
        'effects': ['No yield loss expected from this leaf'],
        'stopNow': ['Nothing to treat right now'],
        'preventSpread': ['Wash hands and tools between plots'],
        'preventFuture': ['Water at base in the morning', 'Check undersides for pests'],
        'treatments': ['Bio spray (optional)', 'Mulch and airflow'],
        'seeExpertIf': 'No action required unless symptoms change.',
    }
}

NO_DETECTION = {
    'name': 'No clear disease found',
    'type': 'unclear',
    'summary': 'The model did not find a strong match. Try a closer, well-lit picture.',
    'cause': 'Confidence was below the threshold.',
}

MODEL = None

# -------------------------------------------------------------------------
# CUSTOM LAYERS: These safely perform MobileNetV2 mathematical scaling
# inside the model graph, while ignoring the illegal positional arguments
# that cause TensorFlow to crash.
# -------------------------------------------------------------------------
class TrueDivide(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def __call__(self, *args, **kwargs):
        # Pass only the image tensor (args[0]) to the graph builder
        return super().__call__(args[0], **kwargs)
        
    def call(self, inputs):
        # Execute the actual math required by MobileNetV2
        return inputs / 127.5

class Subtract(tf.keras.layers.Layer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def __call__(self, *args, **kwargs):
        # Pass only the image tensor (args[0]) to the graph builder
        return super().__call__(args[0], **kwargs)
        
    def call(self, inputs):
        # Execute the actual math required by MobileNetV2
        return inputs - 1.0
# -------------------------------------------------------------------------

def ensure_model_loaded():
    global MODEL
    if MODEL is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f'Model file was not found at {MODEL_PATH}.')
        
        custom_objs = {
            'TrueDivide': TrueDivide,
            'Subtract': Subtract
        }
        
        MODEL = tf.keras.models.load_model(
            MODEL_PATH, 
            compile=False, 
            custom_objects=custom_objs
        )
    return MODEL

def preprocess_image(image: Image.Image) -> np.ndarray:
    """Turn a PIL image into the (1, 224, 224, 3) array."""
    resized = image.convert('RGB').resize(MODEL_INPUT_SIZE, Image.Resampling.BILINEAR)
    
    # We pass RAW 0-255 pixels directly. The TrueDivide and Subtract 
    # custom layers we built above will safely handle the scaling.
    arr = np.asarray(resized, dtype=np.float32)
    return np.expand_dims(arr, axis=0)

def build_result_for_image(image: Image.Image) -> dict[str, Any]:
    model = ensure_model_loaded()
    arr = preprocess_image(image)

    # Predict outputs a 2D array: [[prob_class0, prob_class1, prob_class2]]
    raw_output = model.predict(arr, verbose=0)
    probabilities = raw_output[0]
    
    # Debugging output to see exact AI calculations
    print("\n" + "="*50)
    print(f"RAW PREDICTION NUMBERS: {probabilities}")
    print("="*50 + "\n")
    
    predicted_index = int(np.argmax(probabilities))
    confidence_score = float(probabilities[predicted_index])
    predicted_label = CLASS_NAMES[predicted_index]
    confidence_pct = round(confidence_score * 100.0, 2)
    
    uncertain = confidence_score < CONFIDENCE_THRESHOLD
    is_healthy = (not uncertain) and (predicted_index == HEALTHY_INDEX)

    if uncertain:
        final_label = NO_DETECTION['name']
        return_message = 'The model is not confident about this image. Please upload a closer photo.'
        disease_info = dict(NO_DETECTION)
    elif is_healthy:
        final_label = HEALTHY_LABEL
        return_message = HEALTHY_LABEL
        disease_info = dict(DAMAGE_DB['Healthy Leaf'])
        disease_info['name'] = HEALTHY_LABEL
        disease_info['type'] = 'healthy'
    else:
        final_label = predicted_label
        return_message = f'{predicted_label} detected.'
        disease_info = DAMAGE_DB.get(predicted_label, {})

    all_predictions = sorted(
        (
            {
                'class': CLASS_NAMES[i],
                'label': HEALTHY_LABEL if i == HEALTHY_INDEX else CLASS_NAMES[i],
                'confidence': round(float(probabilities[i]) * 100.0, 2),
                'probability': float(probabilities[i]),
            }
            for i in range(len(CLASS_NAMES))
        ),
        key=lambda item: item['probability'],
        reverse=True,
    )

    return {
        'status': 'ok',
        'label': final_label,
        'prediction': final_label,
        'message': return_message,
        'confidence': confidence_pct,
        'confidence_score': round(confidence_score, 4),
        'disease': disease_info,
        'available': not uncertain,
        'uncertain': uncertain,
        'predictions': all_predictions,
        'class_index': predicted_index,
        'is_healthy': is_healthy
    }

# ==========================================================
# PAGE ROUTES
# ==========================================================

@app.route('/')
def home():
    return render_template('home.html', active_page='home')

@app.route('/scan')
def scan_page():
    return render_template('scan.html', active_page='scan')

@app.route('/farms')
def farms_page():
    return render_template('farms.html', active_page='farms')

@app.route('/monitoring')
def monitoring_page():
    return render_template('monitoring.html', active_page='monitoring')

@app.route('/history')
def history_page():
    return render_template('history.html', active_page='history')

@app.route('/index')
def index_redirect():
    return redirect(url_for('home'))

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'model_path': MODEL_PATH,
        'model_exists': os.path.exists(MODEL_PATH),
        'db_initialized': True,
        'python': sys.version.split()[0],
    })

# ==========================================================
# REST API: AI PREDICTION
# ==========================================================

@app.route('/api/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'Please upload a tomato leaf image.'}), 400

    uploaded = request.files['image']
    if uploaded.filename == '':
        return jsonify({'error': 'No image file was selected.'}), 400

    try:
        image = Image.open(uploaded.stream).convert('RGB')
    except UnidentifiedImageError:
        return jsonify({'error': 'The uploaded file is not a valid image.'}), 400

    try:
        result = build_result_for_image(image)

        ext = os.path.splitext(uploaded.filename.lower())[1] or '.jpg'
        saved_filename = f"leaf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
        saved_filepath = os.path.join(UPLOADS_DIR, saved_filename)
        os.makedirs(os.path.dirname(saved_filepath), exist_ok=True)
        image.save(saved_filepath, quality=90)

        label = result.get('label', 'Healthy Leaf')
        is_healthy = bool(result.get('is_healthy', False))
        disease_info = result.get('disease', {})

        raw_farm_id = request.form.get('farm_id')
        parsed_farm_id = int(raw_farm_id) if raw_farm_id and raw_farm_id.isdigit() else None

        scan_id = db.save_scan(
            image_filename=saved_filename,
            prediction_label=label,
            is_healthy=is_healthy,
            confidence=result.get('confidence', 0.0),
            disease_name=disease_info.get('name', label),
            disease_type=disease_info.get('type', 'healthy' if is_healthy else 'fungal'),
            disease_summary=disease_info.get('summary', ''),
            disease_cause=disease_info.get('cause', ''),
            raw_data=result,
            farm_id=parsed_farm_id,
        )

        result['scan_id'] = scan_id
        result['image_url'] = f'/static/uploads/{saved_filename}'
        return jsonify(result)

    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({'error': 'Prediction failed. Please check the model file and try again.'}), 500

# ==========================================================
# REST API: FARM MANAGEMENT
# ==========================================================

@app.route('/api/farms', methods=['GET'])
def api_list_farms():
    return jsonify({'status': 'ok', 'farms': db.list_farms()})

@app.route('/api/farms', methods=['POST'])
def api_create_farm():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Farm name is required.'}), 400

    location = (data.get('location') or '').strip()
    size = (data.get('size') or '').strip()
    variety = (data.get('variety') or '').strip()
    planting_date = (data.get('planting_date') or '').strip()

    raw_plants = data.get('plant_count', 0)
    try:
        plant_count = max(0, int(raw_plants))
    except (ValueError, TypeError):
        plant_count = 0

    notes = (data.get('notes') or '').strip()

    farm_id = db.create_farm(
        name=name,
        location=location,
        size=size,
        variety=variety,
        planting_date=planting_date,
        plant_count=plant_count,
        notes=notes,
    )
    return jsonify({'status': 'ok', 'farm_id': farm_id, 'message': 'Farm created successfully.'}), 201

@app.route('/api/farms/<int:farm_id>', methods=['GET'])
def api_get_farm(farm_id: int):
    farm = db.get_farm(farm_id)
    if not farm:
        return jsonify({'error': 'Farm not found.'}), 404
    return jsonify({'status': 'ok', 'farm': farm})

@app.route('/api/farms/<int:farm_id>', methods=['PUT'])
def api_update_farm(farm_id: int):
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Farm name is required.'}), 400

    location = (data.get('location') or '').strip()
    size = (data.get('size') or '').strip()
    variety = (data.get('variety') or '').strip()
    planting_date = (data.get('planting_date') or '').strip()

    raw_plants = data.get('plant_count', 0)
    try:
        plant_count = max(0, int(raw_plants))
    except (ValueError, TypeError):
        plant_count = 0

    notes = (data.get('notes') or '').strip()

    updated = db.update_farm(
        farm_id=farm_id,
        name=name,
        location=location,
        size=size,
        variety=variety,
        planting_date=planting_date,
        plant_count=plant_count,
        notes=notes,
    )
    if not updated:
        return jsonify({'error': 'Farm not found or could not be updated.'}), 404
    return jsonify({'status': 'ok', 'message': 'Farm updated successfully.'})

@app.route('/api/farms/<int:farm_id>', methods=['DELETE'])
def api_delete_farm(farm_id: int):
    deleted = db.delete_farm(farm_id)
    if not deleted:
        return jsonify({'error': 'Farm not found or could not be deleted.'}), 404
    return jsonify({'status': 'ok', 'message': 'Farm deleted successfully.'})

# ==========================================================
# REST API: SCAN RECORDS & AUDIT HISTORY
# ==========================================================

@app.route('/api/scans', methods=['GET'])
def api_list_scans():
    search = request.args.get('search')
    status_filter = request.args.get('status')
    raw_farm_id = request.args.get('farm_id')
    sort_order = request.args.get('sort', 'newest')

    farm_id = None
    if raw_farm_id and raw_farm_id.isdigit():
        farm_id = int(raw_farm_id)

    limit = min(200, max(1, int(request.args.get('limit', 100))))
    offset = max(0, int(request.args.get('offset', 0)))

    scans = db.list_scans(
        search=search,
        status_filter=status_filter,
        farm_id=farm_id,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return jsonify({'status': 'ok', 'scans': scans})

@app.route('/api/scans/<int:scan_id>', methods=['GET'])
def api_get_scan(scan_id: int):
    scan = db.get_scan(scan_id)
    if not scan:
        return jsonify({'error': 'Scan record not found.'}), 404
    return jsonify({'status': 'ok', 'scan': scan})

@app.route('/api/scans/<int:scan_id>', methods=['DELETE'])
def api_delete_scan(scan_id: int):
    deleted = db.delete_scan(scan_id)
    if not deleted:
        return jsonify({'error': 'Scan record not found or could not be deleted.'}), 404
    return jsonify({'status': 'ok', 'message': 'Scan record deleted successfully.'})

# ==========================================================
# REST API: CROP MONITORING DASHBOARD STATISTICS
# ==========================================================

@app.route('/api/dashboard/stats', methods=['GET'])
def api_dashboard_stats():
    return jsonify({'status': 'ok', 'stats': db.get_dashboard_stats()})
if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    app.run(host=host, port=port, debug=False)