from flask import Blueprint, request, jsonify, current_app
from app.services.text_transcriber import transcribe_audio_with_openai
from dotenv import load_dotenv
import os

load_dotenv()

transcription_bp = Blueprint('transcription', __name__)

openai_key = os.getenv("OPENAI_API_KEY")

@transcription_bp.route('/transcribe', methods=['POST'])
def transcribe():
    audio_file = request.files.get('audio_file')
    if not audio_file:
        return jsonify({'error': 'Missing audio_file'}), 400

    # Lấy model từ app context
    # model = current_app.config["whisperx_model"]
    # text = transcribe_audio_with_vosk(audio_file)
    text = transcribe_audio_with_openai(audio_file=audio_file, api_key=openai_key)
    if not text:
        return jsonify({'error': 'Transcription failed'}), 500

    return jsonify({'text': text}), 200