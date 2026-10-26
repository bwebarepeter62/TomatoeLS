import functools
import io
import json
import logging
import os
import secrets
import sys
import uuid
from datetime import datetime
from typing import Any, Optional

import numpy as np
from flask import (
    Flask, jsonify, redirect, render_template, request,
    send_file, session, url_for
)
from PIL import Image, UnidentifiedImageError
import tensorflow as tf
from werkzeug.security import check_password_hash, generate_password_hash

import db
import pdf_report

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

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATE_DIR)

# Production security and session configurations
app.secret_key = os.environ.get('SECRET_KEY', 'leafscan-secure-session-key-dev-2026')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload limit (Task 8)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

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
# CSRF PROTECTION & TEMPLATE CONTEXT HELPERS
# -------------------------------------------------------------------------

class _CSRFToken(str):
    def __call__(self):
        return str(self)


def get_csrf_token() -> str:
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']


@app.context_processor
def inject_context():
    user = None
    uid = session.get('user_id')
    if uid:
        user = db.get_user_by_id(uid)
    tok = _CSRFToken(get_csrf_token())
    return {
        'current_user': user,
        'csrf_token': tok,
        'now_year': datetime.now().year,
    }


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session or not db.get_user_by_id(session['user_id']):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.'}), 401
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


def is_allowed_file(filename: str) -> bool:
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@app.errorhandler(413)
def request_entity_too_large(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Uploaded file exceeds the 16 MB maximum upload limit.'}), 413
    return '<h3>File too large</h3><p>Uploaded image exceeds the 16 MB limit. Please select a smaller photo.</p>', 413


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
    arr = np.asarray(resized, dtype=np.float32)
    return np.expand_dims(arr, axis=0)


def build_result_for_image(image: Image.Image) -> dict[str, Any]:
    model = ensure_model_loaded()
    arr = preprocess_image(image)

    # Predict outputs a 2D array: [[prob_class0, prob_class1, prob_class2]]
    raw_output = model.predict(arr, verbose=0)
    probabilities = raw_output[0]
    
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
@login_required
def farms_page():
    return render_template('farms.html', active_page='farms')


@app.route('/monitoring')
@login_required
def monitoring_page():
    return render_template('monitoring.html', active_page='monitoring')


@app.route('/history')
@login_required
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
# AUTHENTICATION & ACCOUNT MANAGEMENT (TASK 2)
# ==========================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session and db.get_user_by_id(session['user_id']):
        return redirect(url_for('farms_page'))
    
    error = None
    if request.method == 'POST':
        token = request.form.get('csrf_token') or request.form.get('_csrf_token')
        if not token or token != session.get('_csrf_token'):
            error = 'Session expired. Please try submitting again.'
        else:
            identifier = (request.form.get('username_or_email') or request.form.get('identifier') or request.form.get('username') or '').strip()
            password = request.form.get('password') or ''
            if not identifier or not password:
                error = 'Please enter your username/email and password.'
            else:
                user = db.authenticate_user(identifier, password)
                if user:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    next_url = request.args.get('next') or url_for('farms_page')
                    return redirect(next_url)
                else:
                    error = 'Invalid username/email or password.'
    return render_template('login.html', error=error, active_page='login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session and db.get_user_by_id(session['user_id']):
        return redirect(url_for('farms_page'))
    
    error = None
    if request.method == 'POST':
        token = request.form.get('csrf_token') or request.form.get('_csrf_token')
        if not token or token != session.get('_csrf_token'):
            error = 'Session expired. Please try submitting again.'
        else:
            username = (request.form.get('username') or '').strip()
            email = (request.form.get('email') or '').strip()
            full_name = (request.form.get('full_name') or '').strip()
            password = request.form.get('password') or ''
            confirm_password = request.form.get('confirm_password') or ''

            if not username or not email or not password:
                error = 'Username, email, and password are required.'
            elif len(username) < 3:
                error = 'Username must be at least 3 characters long.'
            elif len(password) < 6:
                error = 'Password must be at least 6 characters long.'
            elif password != confirm_password:
                error = 'Passwords do not match.'
            else:
                try:
                    user_id = db.create_user(username, email, password, full_name=full_name)
                    session['user_id'] = user_id
                    session['username'] = username
                    return redirect(url_for('farms_page'))
                except ValueError as ve:
                    error = str(ve)
                except Exception as ex:
                    error = f'Registration error: {ex}'
    return render_template('register.html', error=error, active_page='register')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/profile', methods=['GET'], endpoint='profile_page')
@login_required
def profile_page():
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    return render_template('profile.html', current_user=user, active_page='profile')


@app.route('/profile/update', methods=['POST'], endpoint='profile_update')
@login_required
def profile_update():
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    token = request.form.get('csrf_token') or request.form.get('_csrf_token')
    if not token or token != session.get('_csrf_token'):
        return render_template('profile.html', current_user=user, profile_message=None, error='Session expired. Please try again.', active_page='profile')
    
    full_name = (request.form.get('full_name') or '').strip()
    email = (request.form.get('email') or '').strip()
    if not email:
        return render_template('profile.html', current_user=user, error='Email address cannot be empty.', active_page='profile')
    try:
        db.update_user_profile(user_id, email=email, full_name=full_name)
        user = db.get_user_by_id(user_id)
        return render_template('profile.html', current_user=user, profile_message='Profile updated successfully.', active_page='profile')
    except ValueError as ve:
        return render_template('profile.html', current_user=user, error=str(ve), active_page='profile')


@app.route('/profile/password', methods=['POST'], endpoint='profile_password')
@login_required
def profile_password():
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    token = request.form.get('csrf_token') or request.form.get('_csrf_token')
    if not token or token != session.get('_csrf_token'):
        return render_template('profile.html', current_user=user, password_error='Session expired. Please try again.', active_page='profile')

    current_pass = request.form.get('current_password') or ''
    new_pass = request.form.get('new_password') or ''
    confirm_new = request.form.get('confirm_new_password') or ''

    if not check_password_hash(user['password_hash'], current_pass):
        return render_template('profile.html', current_user=user, password_error='Current password is incorrect.', active_page='profile')
    if len(new_pass) < 6:
        return render_template('profile.html', current_user=user, password_error='New password must be at least 6 characters long.', active_page='profile')
    if new_pass != confirm_new:
        return render_template('profile.html', current_user=user, password_error='New passwords do not match.', active_page='profile')

    db.change_user_password(user_id, new_pass)
    return render_template('profile.html', current_user=user, password_success='Password updated successfully.', active_page='profile')


app.add_url_rule('/profile', endpoint='profile', view_func=profile_page)


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

    if not is_allowed_file(uploaded.filename):
        return jsonify({'error': 'Unsupported format. Please upload a JPG, PNG, or WEBP image.'}), 400

    try:
        image = Image.open(uploaded.stream).convert('RGB')
    except (UnidentifiedImageError, OSError):
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

        current_user_id = session.get('user_id')

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
            user_id=current_user_id,
            platform='web',
            model_name='tomato_disease_model.h5',
        )

        result['scan_id'] = scan_id
        result['image_url'] = f'/static/uploads/{saved_filename}'
        return jsonify(result)

    except Exception as e:
        logging.error(f"Prediction error: {e}")
        return jsonify({'error': 'Prediction failed. Please check the model file and try again.'}), 500


# ==========================================================
# REST API: FARM MANAGEMENT (USER ISOLATED)
# ==========================================================

@app.route('/api/farms', methods=['GET'])
def api_list_farms():
    user_id = session.get('user_id')
    return jsonify({'status': 'ok', 'farms': db.list_farms(user_id=user_id)})


@app.route('/api/farms', methods=['POST'])
@login_required
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
    user_id = session.get('user_id')

    farm_id = db.create_farm(
        name=name,
        location=location,
        size=size,
        variety=variety,
        planting_date=planting_date,
        plant_count=plant_count,
        notes=notes,
        user_id=user_id,
    )
    return jsonify({'status': 'ok', 'farm_id': farm_id, 'message': 'Farm created successfully.'}), 201


@app.route('/api/farms/<int:farm_id>', methods=['GET'])
def api_get_farm(farm_id: int):
    user_id = session.get('user_id')
    farm = db.get_farm(farm_id, user_id=user_id)
    if not farm:
        return jsonify({'error': 'Farm not found.'}), 404
    return jsonify({'status': 'ok', 'farm': farm})


@app.route('/api/farms/<int:farm_id>', methods=['PUT'])
@login_required
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
    user_id = session.get('user_id')

    updated = db.update_farm(
        farm_id=farm_id,
        name=name,
        location=location,
        size=size,
        variety=variety,
        planting_date=planting_date,
        plant_count=plant_count,
        notes=notes,
        user_id=user_id,
    )
    if not updated:
        return jsonify({'error': 'Farm not found or could not be updated.'}), 404
    return jsonify({'status': 'ok', 'message': 'Farm updated successfully.'})


@app.route('/api/farms/<int:farm_id>', methods=['DELETE'])
@login_required
def api_delete_farm(farm_id: int):
    user_id = session.get('user_id')
    deleted = db.delete_farm(farm_id, user_id=user_id)
    if not deleted:
        return jsonify({'error': 'Farm not found or could not be deleted.'}), 404
    return jsonify({'status': 'ok', 'message': 'Farm deleted successfully.'})


# ==========================================================
# REST API: SCAN RECORDS & AUDIT HISTORY
# ==========================================================

@app.route('/api/scans', methods=['GET'])
@login_required
def api_list_scans():
    user_id = session.get('user_id')
    search = request.args.get('search')
    status_filter = request.args.get('status')
    raw_farm_id = request.args.get('farm_id')
    sort_order = request.args.get('sort', 'newest')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

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
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )
    return jsonify({'status': 'ok', 'scans': scans})


@app.route('/api/scans/<int:scan_id>', methods=['GET'])
@login_required
def api_get_scan(scan_id: int):
    user_id = session.get('user_id')
    scan = db.get_scan(scan_id, user_id=user_id)
    if not scan:
        return jsonify({'error': 'Scan record not found.'}), 404
    return jsonify({'status': 'ok', 'scan': scan})


@app.route('/api/scans/<int:scan_id>', methods=['DELETE'])
@login_required
def api_delete_scan(scan_id: int):
    user_id = session.get('user_id')
    deleted = db.delete_scan(scan_id, user_id=user_id)
    if not deleted:
        return jsonify({'error': 'Scan record not found or could not be deleted.'}), 404
    return jsonify({'status': 'ok', 'message': 'Scan record deleted successfully.'})


@app.route('/api/scans/clear', methods=['POST', 'DELETE'])
@login_required
def api_clear_scans():
    user_id = session.get('user_id')
    deleted_count = db.clear_scans(user_id=user_id)
    return jsonify({
        'status': 'ok',
        'message': f'Successfully cleared {deleted_count} scan records.',
        'deleted_count': deleted_count
    })


# ==========================================================
# REST API: PDF DIAGNOSIS REPORT (TASK 6)
# ==========================================================

@app.route('/api/scans/<int:scan_id>/report', methods=['GET'])
@login_required
def api_scan_report(scan_id: int):
    user_id = session.get('user_id')
    scan = db.get_scan(scan_id, user_id=user_id)
    if not scan:
        return jsonify({'error': 'Scan record not found or unauthorized.'}), 404

    try:
        pdf_buffer = pdf_report.generate_pdf_report(scan, UPLOADS_DIR)
        report_num = f"LS-{scan_id:05d}"
        filename = f"LeafScan_Report_{report_num}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logging.error(f"PDF generation failed: {e}")
        return jsonify({'error': f'Failed to generate PDF report: {str(e)}'}), 500


# ==========================================================
# REST API: CROP MONITORING DASHBOARD STATISTICS
# ==========================================================

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def api_dashboard_stats():
    user_id = session.get('user_id')
    raw_farm_id = request.args.get('farm_id')
    farm_id = int(raw_farm_id) if raw_farm_id and raw_farm_id.isdigit() else None
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    stats = db.get_dashboard_stats(
        user_id=user_id,
        farm_id=farm_id,
        date_from=date_from,
        date_to=date_to,
    )
    return jsonify({'status': 'ok', 'stats': stats})


# ==========================================================
# REST API: MOBILE APP INTEGRATION & SYNCHRONIZATION (TASK 7)
# ==========================================================

@app.route('/api/mobile/status', methods=['GET'])
def api_mobile_status():
    return jsonify({
        'status': 'ok',
        'server_version': '2.0.0',
        'web_model': 'MobileNetV2 (3 classes: Early Blight, Late Blight, Healthy Leaf)',
        'mobile_model': 'best_int8.tflite (15-class edge detector)',
        'sync_supported': True,
        'authenticated': 'user_id' in session
    })


@app.route('/api/mobile/farms', methods=['GET'])
def api_mobile_farms():
    user_id = session.get('user_id')
    farms = db.list_farms(user_id=user_id)
    return jsonify({'status': 'ok', 'farms': farms})


@app.route('/api/mobile/scans', methods=['GET'])
def api_mobile_scans():
    user_id = session.get('user_id')
    limit = min(100, max(1, int(request.args.get('limit', 50))))
    offset = max(0, int(request.args.get('offset', 0)))
    scans = db.list_scans(user_id=user_id, limit=limit, offset=offset)
    return jsonify({'status': 'ok', 'scans': scans})


@app.route('/api/mobile/sync', methods=['POST'])
def api_mobile_sync():
    data = request.get_json(silent=True) or {}
    scans_to_sync = data.get('scans', [])
    user_id = session.get('user_id')

    if not isinstance(scans_to_sync, list):
        return jsonify({'error': 'Invalid format. Expected {"scans": [...]} array.'}), 400

    synced_ids = []
    skipped_ids = []

    for item in scans_to_sync:
        sync_id = item.get('sync_id') or item.get('id')
        if not sync_id:
            sync_id = f"mob_{uuid.uuid4().hex[:12]}"

        # Prevent duplicate synchronization
        existing = db.get_scan_by_sync_id(str(sync_id))
        if existing:
            skipped_ids.append(str(sync_id))
            continue

        pred_label = item.get('prediction_label', 'Unknown Condition')
        is_healthy = bool(item.get('is_healthy', False))
        confidence = float(item.get('confidence', 0.0))
        farm_id = item.get('farm_id')
        if farm_id and str(farm_id).isdigit():
            farm_id = int(farm_id)
        else:
            farm_id = None

        img_filename = item.get('image_filename') or 'mobile_scan.jpg'
        if 'image_base64' in item and item['image_base64']:
            try:
                import base64
                img_bytes = base64.b64decode(item['image_base64'])
                img_filename = f"mob_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.jpg"
                with open(os.path.join(UPLOADS_DIR, img_filename), 'wb') as f:
                    f.write(img_bytes)
            except Exception as e:
                logging.warning(f"Could not save mobile scan image bytes: {e}")

        db.save_scan(
            image_filename=img_filename,
            prediction_label=pred_label,
            is_healthy=is_healthy,
            confidence=confidence,
            disease_name=item.get('disease_name', pred_label),
            disease_type=item.get('disease_type', 'fungal'),
            disease_summary=item.get('disease_summary', 'Synchronized from LeafScan Flutter edge inference.'),
            disease_cause=item.get('disease_cause', 'Edge inference record.'),
            raw_data=item.get('raw_data', {}),
            farm_id=farm_id,
            user_id=user_id,
            platform='mobile',
            model_name=item.get('model_name', 'best_int8.tflite'),
            sync_id=str(sync_id)
        )
        synced_ids.append(str(sync_id))

    return jsonify({
        'status': 'ok',
        'synced_count': len(synced_ids),
        'synced_ids': synced_ids,
        'skipped_duplicates': skipped_ids,
        'message': f"Synchronized {len(synced_ids)} mobile records successfully."
    })


if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    app.run(host=host, port=port, debug=False)