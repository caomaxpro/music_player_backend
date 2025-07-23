import os
import tempfile
import librosa
import numpy as np

def compute_amplitude(file_path, target_points=100):
    """
    Nhận file_storage (từ Flask request.files['file']) và trả về list RMS đã downsample.
    """
    # Save the uploaded file to a temporary location

    try:
        y, sr = librosa.load(file_path, sr=None)
        rms = librosa.feature.rms(y=y)[0]
        # Downsample RMS to target_points for wave bar
        if len(rms) > target_points:
            rms_downsampled = np.interp(
                np.linspace(0, len(rms) - 1, target_points),
                np.arange(len(rms)),
                rms
            )
        else:
            rms_downsampled = rms
        rms_list = rms_downsampled.tolist()
        
    finally:
        pass

    return rms_list


def detect_words(audio_path, threshold=0.02, min_duration=0.2):
    """
    Phát hiện các đoạn âm thanh (có thể là từ) dựa trên biên độ.

    Args:
        audio_path (str): Đường dẫn đến tệp âm thanh.
        threshold (float): Ngưỡng biên độ để phát hiện âm thanh.
        min_duration (float): Thời gian tối thiểu (giây) để một đoạn được coi là hợp lệ.

    Returns:
        list: Danh sách các đoạn âm thanh (start, end) tính bằng giây.
    """
    # Load audio file
    y, sr = librosa.load(audio_path)

    # Calculate RMS (Root Mean Square) for amplitude
    rms = librosa.feature.rms(y=y)[0]

    # Convert RMS frames to time
    frame_length = len(y) / len(rms)  # Number of samples per RMS frame
    times = np.arange(len(rms)) * frame_length / sr

    # Detect segments where RMS > threshold
    segments = []
    start = None
    for i, value in enumerate(rms):
        if value > threshold:
            if start is None:
                start = times[i]  # Start of a segment
        else:
            if start is not None:
                end = times[i]  # End of a segment
                # Only keep segments longer than min_duration
                if end - start >= min_duration:
                    segments.append((start, end))
                start = None

    # Handle case where audio ends with a segment
    if start is not None:
        end = times[-1]
        if end - start >= min_duration:
            segments.append((start, end))

    return segments


def detect_first_word(audio_path, threshold=0.02, min_duration=0.2):
    """
    Phát hiện từ đầu tiên dựa trên biên độ của âm thanh.

    Args:
        audio_path (str): Đường dẫn đến tệp âm thanh.
        threshold (float): Ngưỡng biên độ để phát hiện âm thanh.
        min_duration (float): Thời gian tối thiểu (giây) để một đoạn được coi là hợp lệ.

    Returns:
        tuple: Thời gian bắt đầu và kết thúc của từ đầu tiên (start, end) tính bằng giây.
    """
    # Load audio file
    y, sr = librosa.load(audio_path)

    # Calculate RMS (Root Mean Square) for amplitude
    rms = librosa.feature.rms(y=y)[0]

    # Convert RMS frames to time
    frame_length = len(y) / len(rms)  # Number of samples per RMS frame
    times = np.arange(len(rms)) * frame_length / sr

    # Detect the first segment where RMS > threshold
    start = None
    for i, value in enumerate(rms):
        if value > threshold:
            if start is None:
                start = times[i]  # Start of the first segment
        else:
            if start is not None:
                end = times[i]  # End of the first segment
                # Only keep the first segment longer than min_duration
                if end - start >= min_duration:
                    return (start, end)
                start = None

    # Handle case where audio ends with a segment
    if start is not None:
        end = times[-1]
        if end - start >= min_duration:
            return (start, end)

    return None  # 

# Example usage
audio_file = "/home/cao-le/Music/vocals.wav"
# segments = detect_words(audio_file, threshold=0.05, min_duration=0.2)
lyrics = '''
    Take me down to the river bend
    Take me down to the fightin' end
    Wash the poison from off my skin
    Show me how to be whole again
    Fly me up on a silver wing
    Past the black where the sirens sing
    Warm me up in a nova's glow
    And drop me down to the dream below
    'Cause I'm only a crack in this castle of glass
    Hardly anything there, for you to see
    For you to see

    Bring me home in a blindin' dream
    Through the secrets that I have seen
    Wash the sorrow from off my skin
    And show me how to be whole again
    'Cause I'm only a crack in this castle of glass
    Hardly anything there, for you to see
    For you to see

    'Cause I'm only a crack in this castle of glass
    Hardly anything else I need to be
    'Cause I'm only a crack in this castle of glass
    Hardly anything there, for you to see
    For you to see

    For you to see
'''

# _words = lyrics.split()

# print("Detected segments (start, end):")
# print(f"Segments: {len(segments)}")
# print(f"Words: {len(_words)}")
# for start, end in segments:
#     print(f"{start:.2f}s - {end:.2f}s")