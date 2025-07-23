from flask import Blueprint, request, jsonify
from app.services.aplitude_processor import compute_amplitude

amplitude_bp = Blueprint('amplitude', __name__)

@amplitude_bp.route('/amplitude', methods=['POST'])
def amplitude():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    rms_list = compute_amplitude(file)
    return jsonify({'rms': rms_list})