from vosk import Model, KaldiRecognizer
import wave
import json
import tempfile
from pydub import AudioSegment
import os
import openai

# Tải model một lần khi khởi động server
# vosk_model = Model("vosk-model-en-us-0.22")

# def transcribe_audio_with_vosk(audio_file):
#     # Lưu file tạm
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
#         # Convert về wav nếu không phải wav
#         original_ext = os.path.splitext(audio_file.filename)[-1].lower()
#         input_path = tmp.name.replace(".wav", original_ext)
#         audio_file.save(input_path)
#         if original_ext != ".wav":
#             audio = AudioSegment.from_file(input_path)
#             audio = audio.set_channels(1).set_frame_rate(16000)
#             audio.export(tmp.name, format="wav")
#             os.remove(input_path)
#         else:
#             os.rename(input_path, tmp.name)
#         audio_path = tmp.name

#     try:
#         wf = wave.open(audio_path, "rb")
#         rec = KaldiRecognizer(vosk_model, wf.getframerate())
#         rec.SetWords(True)
#         results = []
#         while True:
#             data = wf.readframes(4000)
#             if len(data) == 0:
#                 break
#             if rec.AcceptWaveform(data):
#                 res = json.loads(rec.Result())
#                 results.append(res.get("text", ""))
#         # Lấy phần còn lại
#         res = json.loads(rec.FinalResult())
#         results.append(res.get("text", ""))
#         text = " ".join(results).strip()
#     finally:
#         os.remove(audio_path)
#     return text


def transcribe_audio_with_openai(audio_file, api_key):
    """
    Transcribe audio using OpenAI Whisper API.
    - audio_file: Flask FileStorage
    - api_key: OpenAI API key string
    """
    openai.api_key = api_key

    # Lưu file tạm
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        audio_file.save(tmp.name)
        audio_path = tmp.name

    try:
        with open(audio_path, "rb") as f:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
                language='vi'
            )
        return transcript
    finally:
        os.remove(audio_path)