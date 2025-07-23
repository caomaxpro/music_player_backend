import os
import subprocess
import tempfile
import zipfile
import secrets
from pydub import AudioSegment

env2_python = "/home/cao-le/Flutter Projects/music_player_app/backend/env2/bin/python"

def zip_audio_files(result_dict, output_zip_path):
    """
    Zip audio files into a single archive.
    
    Args:
        result_dict (dict): Dictionary containing file paths (e.g., {"vocals": "path/to/vocals.mp3"}).
        output_zip_path (str): Path to save the zip file.
    
    Returns:
        str: Path to the created zip file.
    """
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for key, file_path in result_dict.items():
                if os.path.exists(file_path):
                    zipf.write(file_path, os.path.basename(file_path))
        return output_zip_path
    except Exception as e:
        print(f"Error creating zip file: {e}")
        return None

def convert_to_mp3(wav_path, output_dir):
    """
    Convert a .wav file to .mp3 format.
    
    Args:
        wav_path (str): Path to the .wav file.
        output_dir (str): Directory to save the .mp3 file.
    
    Returns:
        str: Path to the converted .mp3 file.
    """
    try:
        random_id = secrets.token_hex(4)  # Generates 8 characters (4 bytes in hex)
        base_name = os.path.basename(wav_path).replace(".wav", "")
        mp3_file_name = f"{base_name}_{random_id}.mp3"
        mp3_path = os.path.join(output_dir, mp3_file_name)

        audio = AudioSegment.from_wav(wav_path)
        audio.export(mp3_path, format="mp3")
        return mp3_path
    except Exception as e:
        print(f"Error converting {wav_path} to mp3: {e}")
        return None

def spleeter_separate(input_path, stems, output_dir):
    result = subprocess.run([
        env2_python, "-m", "spleeter", "separate", "-p", f"spleeter:{stems}stems", "-o", output_dir, input_path
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Spleeter failed:", result.stderr)
        return None

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    vocals_path = os.path.join(output_dir, base_name, "vocals.wav")
    accompaniment_path = os.path.join(output_dir, base_name, "accompaniment.wav")
    drums_path = os.path.join(output_dir, base_name, "drums.wav") if stems == "4" else ""
    bass_path = os.path.join(output_dir, base_name, "bass.wav") if stems == "4" else ""
    other_path = os.path.join(output_dir, base_name, "other.wav") if stems == "5" else ""

    result_dict = {}

    # Convert .wav files to .mp3 and update result_dict
    if os.path.exists(vocals_path):
        result_dict["vocals"] = convert_to_mp3(vocals_path, output_dir)

    if os.path.exists(accompaniment_path):
        result_dict["accompaniment"] = convert_to_mp3(accompaniment_path, output_dir)

    if os.path.exists(drums_path):
        result_dict["drums"] = convert_to_mp3(drums_path, output_dir)

    if os.path.exists(bass_path):
        result_dict["bass"] = convert_to_mp3(bass_path, output_dir)

    if os.path.exists(other_path):
        result_dict["other"] = convert_to_mp3(other_path, output_dir)
    
    if result_dict:
        return result_dict
    else:
        print("No output files found.")
        return None

# spleeter_separate("/home/cao-le/Music/castle_of_glass.mp3", ".")