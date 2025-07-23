import base64
from flask import Blueprint, request, jsonify
import os
import json
from app.services.vocal_separater import spleeter_separate, zip_audio_files
from app.services.aplitude_processor import detect_first_word, compute_amplitude
from app.services.text_align_forcer import align_timestamps_with_amplitude
import concurrent.futures

karaoke_bp = Blueprint('karaoke', __name__)

@karaoke_bp.route('/karaoke_process', methods=['POST'])
def process_karaoke():
    """
    Process karaoke request:
    - Extract audio file and timestamp lyrics from request.
    - Split sounds using Spleeter.
    - Process amplitude using Librosa.
    - Align the first timestamp of lyrics with amplitude.
    """
    try:
        print("[Step 1] Extracting audio file and timestamp lyrics from request...")
        # Step 1: Extract audio file and timestamp lyrics from request
        audio_file = request.files.get('audioFile')
        timestamp_lyrics_raw = request.form.get('timestampLyrics') 

        print("Type of timestamp_lyrics_raw:", type(timestamp_lyrics_raw))
        print("Value of timestamp_lyrics_raw:", timestamp_lyrics_raw)

        # Check if timestamp_lyrics_raw is None
        if timestamp_lyrics_raw is None:
            print("[Step 1] Error: Missing timestamp lyrics")
            return jsonify({"error": "Missing timestamp lyrics"}), 400

        # Print the uploaded file details
        if audio_file:
            print("[Step 1] Uploaded file name:", audio_file.filename)
        else:
            print("[Step 1] Error: No audio file uploaded.")
            return jsonify({"error": "Missing audio file"}), 400

        print("[Step 2] Converting timestamp lyrics from JSON string to Python list...")
        # Convert timestamp_lyrics from JSON string to Python list
        try:
            timestamp_lyrics = json.loads(timestamp_lyrics_raw)
            print("[Step 2] Converted Timestamp Lyrics:", timestamp_lyrics)
        except json.JSONDecodeError:
            print("[Step 2] Error: Invalid JSON format for timestamp lyrics")
            return jsonify({"error": "Invalid JSON format for timestamp lyrics"}), 400

        print("[Step 3] Saving audio file temporarily...")
        # Save audio file temporarily
        temp_audio_path = f"./temp/{audio_file.filename}"
        os.makedirs("./temp", exist_ok=True)
        audio_file.save(temp_audio_path)

        print("[Step 3] Audio file saved at:", temp_audio_path)

        print("[Step 4] Splitting sounds using Spleeter...")
        # Step 2: Split sounds using Spleeter
        output_dir = "./temp/spleeter_output"
        os.makedirs(output_dir, exist_ok=True)
        
        result = spleeter_separate(temp_audio_path, "2", output_dir)
        
        if not result or "vocals" not in result:
            print("[Step 4] Error: Failed to process audio")
            return jsonify({"error": "Failed to process audio"}), 500

        vocals_path = result["vocals"]
        print("[Step 4] Vocal Path:", vocals_path)

        print("[Step 5] Processing amplitude and detecting first word in parallel...")
        # Step 3 & 4: Process amplitude and detect first word in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_amplitude = executor.submit(compute_amplitude, temp_audio_path, 100)
            future_first_word = executor.submit(detect_first_word, vocals_path)

            computed_amplitude = future_amplitude.result()
            first_word_segment = future_first_word.result()

        # print("[Step 5] Computed Amplitude:", computed_amplitude)
        # print("[Step 5] First Word Segment:", first_word_segment)

        if not first_word_segment:
            print("[Step 5] Error: No valid word detected in vocals")
            return jsonify({"error": "No valid word detected in vocals"}), 400

        print("[Step 6] Aligning the first timestamp of lyrics with amplitude...")
        # Step 5: Align the first timestamp of lyrics with amplitude
        adjusted_timestamp = align_timestamps_with_amplitude(
            first_word_segment=first_word_segment,
            timestamp_lyrics=timestamp_lyrics,  # Pass the parsed list
            allow_difference=0.10
        )
        # print("[Step 6] Adjusted Timestamp:", adjusted_timestamp)

        print("[Step 7] Zipping the result files...")
        # Step 6: Zip the result files
        zip_path = os.path.join(output_dir, "karaoke_result.zip")
        zip_audio_files(result, zip_path)

        # Ensure zip_path is valid
        if not os.path.exists(zip_path):
            print("[Step 7] Error: Failed to create zip file")
            return jsonify({"error": "Failed to create zip file"}), 500

        with open(zip_path, "rb") as f:
            zip_base64 = base64.b64encode(f.read()).decode('utf-8')

        print("[Step 8] Cleaning up temporary files...")
        # Step 7: Clean up temporary files
        os.remove(temp_audio_path)
        for root, dirs, files in os.walk(output_dir, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))
        os.rmdir(output_dir)

        print("[Step 9] Returning results...")
        # Return results

        print("[Debug] Type of computed_amplitude:", type(computed_amplitude))

        return jsonify({
            "adjusted_timestamp": adjusted_timestamp,
            "computed_amplitude": computed_amplitude,
            "zip_file": zip_base64
        }), 200

    except Exception as e:
        print("[Error] Exception occurred:", str(e))
        return jsonify({"error": str(e)}), 500


