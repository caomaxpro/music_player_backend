'''
    process and separate sounds: vocals, instrumentals... from an audio file

    load file from client side
    + if there is no file included, in wrong formats or file is too long => return failure warning
    + if the audio file is good then load them into tmp folder, convert into a different format if needed.

    + when done => run spleeter_separate() method to get vocals.mp3, instrumentals.mp3...
        - This depends on what mode users choose
            + 2 stems, 4 stems, 5 stems

    + temporarily save processed files in a temp folder => send files back to client => delete temp files. 
'''

from flask import Blueprint, request, send_file, jsonify
import tempfile
import os
import zipfile
from werkzeug.utils import secure_filename
from app.services.vocal_separater import spleeter_separate
from pydub import AudioSegment

sound_bp = Blueprint("sound", __name__)

ALLOWED_EXTENSIONS = {"mp3", "wav", "flac", "ogg"}
MAX_FILE_SIZE_MB = 20  # adjust as needed

def convert_wav_to_mp3(wav_path):
    mp3_path = wav_path.replace(".wav", ".mp3")
    audio = AudioSegment.from_wav(wav_path)
    audio.export(mp3_path, format="mp3")
    return mp3_path

# Example usage after spleeter_separate:

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@sound_bp.route("/separate", methods=["POST"])
def separate_sound():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Unsupported file format"}), 400

    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)
    if file_length > MAX_FILE_SIZE_MB * 1024 * 1024:
        return jsonify({"success": False, "message": "File too large"}), 400

    stems = request.form.get("stems", "2")
    if stems not in {"2", "4", "5"}:
        stems = "2"

    with tempfile.TemporaryDirectory() as tmpdir:
        filename = secure_filename(file.filename or "uploaded_audio")
        input_path = os.path.join(tmpdir, filename)
        file.save(input_path)

        # Run spleeter
        result = spleeter_separate(input_path, stems=stems, output_dir=tmpdir)
        
        if result:
            for stem, wav_path in result.items():
                if wav_path:
                    mp3_path = convert_wav_to_mp3(wav_path)
                    result[stem] = mp3_path

        if not result:
            return jsonify({"success": False, "message": "Separation failed"}), 500

        # Gom các file kết quả (chỉ lấy file tồn tại)
        files_to_zip = [(stem, path) for stem, path in result.items() if path]

        if not files_to_zip:
            return jsonify({"success": False, "message": "No output files found"}), 500
        
        # Nén các file thành 1 file zip
        zip_path = os.path.join(tmpdir, "separated_stems.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for stem, path in files_to_zip:
                arcname = f"{stem}.wav"
                zipf.write(path, arcname=arcname)

        return send_file(zip_path, as_attachment=True, download_name="separated_stems.zip")

# In vocal_separater.py, update spleeter_separate to accept stems and output_dir:
# def spleeter_separate(input_path, stems="2", output_dir=None):
#   ... (see previous answers for implementation)