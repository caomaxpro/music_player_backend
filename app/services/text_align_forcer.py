import os
import tempfile
import subprocess
import numpy as np
from pydub import AudioSegment
import requests
import whisperx
import torch
import gc
import tempfile
import os
from aeneas.executetask import ExecuteTask
from aeneas.task import Task
from werkzeug.datastructures import FileStorage
import re
import json
import unidecode
from dataclasses import dataclass
from typing import List, Tuple


torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

# Load model sẵn khi import file (chỉ load 1 lần)
WHISPERX_MODEL = None
WHISPERX_ALIGN_MODEL = {}
WHISPERX_MODEL_NAME = "tiny"
WHISPERX_DEVICE = "cuda"
WHISPERX_COMPUTE_TYPE = "int8"

def get_whisperx_model(language=None):
    global WHISPERX_MODEL
    global WHISPERX_DEVICE 

    if torch.cuda.is_available():
        WHISPERX_DEVICE = "cuda"
    else:
        WHISPERX_DEVICE = "cpu"

    if WHISPERX_MODEL is None:
        WHISPERX_MODEL = whisperx.load_model(
            WHISPERX_MODEL_NAME,
            WHISPERX_DEVICE,
            compute_type=WHISPERX_COMPUTE_TYPE,
            language=language
        )
    return WHISPERX_MODEL

def get_whisperx_align_model(language):
    global WHISPERX_ALIGN_MODEL
    if language not in WHISPERX_ALIGN_MODEL:
        WHISPERX_ALIGN_MODEL[language] = whisperx.load_align_model(language_code=language, device=WHISPERX_DEVICE)
    return WHISPERX_ALIGN_MODEL[language]

def force_align_lyrics_with_mfa(lyrics: str, audio_file, acoustic_model_path, dictionary_path, mfa_bin="mfa", output_dir=None):
    """
    Force align lyrics with audio using Montreal Forced Aligner (MFA).
    - lyrics: string, lyrics to align
    - audio_file: Werkzeug FileStorage (from Flask request.files['audio_file'])
    - acoustic_model_path: path to MFA acoustic model (.zip)
    - dictionary_path: path to MFA dictionary (.dict)
    - mfa_bin: 'mfa' command or path to MFA binary
    - output_dir: optional, where to save TextGrid result
    Returns: path to TextGrid file or error message
    """
    # Tạo thư mục tạm cho dữ liệu
    with tempfile.TemporaryDirectory() as tmpdir:
        # Lưu file gốc vào file tạm
        original_ext = os.path.splitext(audio_file.filename)[-1].lower()
        input_path = os.path.join(tmpdir, "input" + original_ext)
        audio_file.save(input_path)

        # Nếu là mp3 thì convert sang wav
        if original_ext == ".mp3":
            audio = AudioSegment.from_file(input_path)
            audio_path = os.path.join(tmpdir, "audio.wav")
            audio.export(audio_path, format="wav")
        else:
            audio_path = input_path

        # Lưu transcript (lab file)
        lab_path = os.path.join(tmpdir, "audio.lab")
        with open(lab_path, "w", encoding="utf-8") as f:
            f.write(lyrics)

        # Tạo thư mục output
        align_output = output_dir or os.path.join(tmpdir, "aligned")
        os.makedirs(align_output, exist_ok=True)

        # Gọi MFA align
        cmd = [
            mfa_bin, "align",
            tmpdir,
            dictionary_path,
            acoustic_model_path,
            align_output,
            "--clean"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            return None, f"MFA align failed: {e.stderr}"

        # Kết quả là file TextGrid
        textgrid_path = os.path.join(align_output, "audio.TextGrid")
        if not os.path.exists(textgrid_path):
            return None, "TextGrid not found after alignment"
        return textgrid_path, None
    

def force_align_lyrics_with_gentle(lyrics: str, audio_file, gentle_server_url="http://localhost:8765/transcriptions"):
    """
    Force align lyrics with audio using Gentle HTTP server.
    - lyrics: string, lyrics to align
    - audio_file: Werkzeug FileStorage (from Flask request.files['audio_file'])
    - gentle_server_url: URL of the Gentle server (default: http://localhost:8765/transcriptions)
    Returns: alignment JSON (dict) or error message
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        original_ext = os.path.splitext(audio_file.filename)[-1].lower()
        input_path = os.path.join(tmpdir, "input" + original_ext)
        audio_file.save(input_path)

        audio_path = None  # Ensure audio_path is always defined

        # Convert mp3 to wav if needed
        if original_ext == ".mp3":
            audio = AudioSegment.from_file(input_path)
            audio_path = os.path.join(tmpdir, "audio.wav")
            audio.export(audio_path, format="wav")
            audio_to_send = open(audio_path, "rb")
            audio_filename = "audio.wav"
            audio_mimetype = "audio/wav"
        else:
            audio_to_send = open(input_path, "rb")
            audio_filename = audio_file.filename
            audio_mimetype = audio_file.mimetype or "audio/wav"

        # Save lyrics to a temp file (Gentle expects a file for transcript)
        transcript_path = os.path.join(tmpdir, "transcript.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(lyrics)
        transcript_to_send = open(transcript_path, "rb")

        files = {
            'audio': (audio_filename, audio_to_send, audio_mimetype),
            'transcript': ('transcript.txt', transcript_to_send, 'text/plain')
        }

        response = None
        try:
            response = requests.post(
                gentle_server_url,
                files=files,
                params={'async': 'false'}
            )
            response.raise_for_status()
            return response.json(), None
        except Exception as e:
            # In response text để debug nếu lỗi JSON
            try:
                err_text = response.text if response is not None else ''
            except Exception:
                err_text = ''
            return None, f"Gentle server align failed: {str(e)} | Response: {err_text[:200]}"
        finally:
            audio_to_send.close()
            transcript_to_send.close()
            try:
                if original_ext == ".mp3" and audio_path is not None and os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(input_path):
                    os.remove(input_path)
                if os.path.exists(transcript_path):
                    os.remove(transcript_path)
            except Exception:
                pass

def force_align_lyrics_with_whisperx(
    audio_file,
    language="en",
    device=WHISPERX_DEVICE,
    batch_size=16,
):
    """
    Force align audio using WhisperX (không diarization), cho phép định nghĩa ngôn ngữ.
    """
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        original_ext = os.path.splitext(audio_file.filename)[-1].lower()
        input_path = os.path.join(tmpdir, "input" + original_ext)
        audio_file.save(input_path)

        try:
            # 1. Dùng model đã load sẵn (có truyền language)
            model = get_whisperx_model(language=language)
            audio = whisperx.load_audio(input_path)
            result = model.transcribe(audio, batch_size=batch_size, language=language)
            segments = result["segments"]

            # 2. Dùng align model đã load sẵn
            model_a, metadata = get_whisperx_align_model(language)
            result = whisperx.align(segments, model_a, metadata, audio, device, return_char_alignments=False)

            return {
                "segments": result["segments"]
            }, None

        except Exception as e:
            return None, f"WhisperX align failed: {str(e)}"
        
def force_align_lyrics_with_aeneas(
    lyrics: str,
    audio_file,
    language="eng",
    output_format="json"
):
    """
    Force align lyrics with audio using Aeneas.
    - lyrics: string, lyrics to align (one line per segment)
    - audio_file: Werkzeug FileStorage (from Flask request.files['audio_file'])
    - language: ISO 639-3 code (e.g., "eng" for English, "vie" for Vietnamese)
    - output_format: "json" or "txt" or "csv" or "smil" or "textgrid"
    Returns: alignment result (dict or str) or error message
    """
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save audio file
        original_ext = os.path.splitext(audio_file.filename)[-1].lower()
        input_path = os.path.join(tmpdir, "input" + original_ext)
        audio_file.save(input_path)

        # Convert mp3 to wav if needed (Aeneas prefers wav)
        if original_ext == ".mp3":
            from pydub import AudioSegment
            audio = AudioSegment.from_file(input_path)
            audio_path = os.path.join(tmpdir, "audio.wav")
            audio.export(audio_path, format="wav")
        else:
            audio_path = input_path

        # Save lyrics to a temp file (one line per segment)
        transcript_path = os.path.join(tmpdir, "transcript.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(lyrics)

        # Set up Aeneas task
        config_string = f"task_language={language}|is_text_type=plain|os_task_file_format={output_format}"
        task = Task(config_string=config_string)
        task.audio_file_path_absolute = audio_path
        task.text_file_path_absolute = transcript_path
        task.sync_map_file_path_absolute = os.path.join(tmpdir, f"alignment.{output_format}")

        try:
            ExecuteTask(task).execute()
            task.output_sync_map_file()
            # Read result
            with open(task.sync_map_file_path_absolute, "r", encoding="utf-8") as f:
                result = f.read()
            if output_format == "json":
                import json
                return json.loads(result), None
            return result, None
        except Exception as e:
            return None, f"Aeneas align failed: {str(e)}"


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

audio_file = None
audio_path = "/home/cao-le/Music/vocals.wav"

lrc_text = '''
    [id: pshkpfmv]
    [ar: Sơn Tùng M-TP]
    [al: m-tp M-TP]
    [ti: Lạc Trôi]
    [length: 03:53]
    [00:27.09]Người theo hương hoa mây mù giăng lối
    [00:29.81]Làn sương khói phôi phai đưa bước ai xa rồi
    [00:34.02]Đơn côi mình ta vấn vương
    [00:36.10]Hồi ức, trong men say chiều mưa buồn
    [00:39.44]Ngăn giọt lệ ngừng khiến khoé mi sầu bi
    [00:43.75]Đường xưa nơi cố nhân từ giã biệt li
    [00:47.00]Cánh hoa rụng rơi
    [00:49.52]Phận duyên mong manh rẽ lối trong mơ ngày tương phùng
    [00:54.62]Tiếng khóc cuốn theo làn gió bay
    [00:57.35]Thuyền ai qua sông lỡ quên vớt ánh trăng tàn nơi này
    [01:02.02]Trống vắng bóng ai dần hao gầy
    [01:07.86]Lòng ta xin nguyện khắc ghi trong tim tình nồng mê say
    [01:11.40]Mặc cho tóc mây vương lên đôi môi cay
    [01:14.59]Bâng khuâng mình ta lạc trôi giữa đời
    [01:18.15]Ta lạc trôi giữa trời
    [01:49.78]Đôi chân lang thang về nơi đâu?
    [01:51.59]Bao yêu thương giờ nơi đâu?
    [01:53.15]Câu thơ tình xưa vội phai mờ
    [01:54.74]Theo làn sương tan biến trong cõi mơ
    [01:56.64]Mưa bụi vương trên làn mi mắt
    [01:58.34]Ngày chia lìa hoa rơi buồn hiu hắt
    [02:00.14]Tiếng đàn ai thêm sầu tương tư lặng mình trong chiều hoàng hôn,
    [02:02.38]Tan vào lời ca (Hey)
    [02:03.64]Lối mòn đường vắng một mình ta
    [02:05.11]Nắng chiều vàng úa nhuộm ngày qua
    [02:07.07]Xin đừng quay lưng xoá
    [02:08.72]Đừng mang câu hẹn ước kia rời xa
    [02:10.32]Yên bình nơi nào đây
    [02:12.15]Chôn vùi theo làn mây
    [02:14.36]Eh-h-h-h-h, la-la-la-la-a-a
    [02:16.77]Người theo hương hoa mây mù giăng lối
    [02:19.79]Làn sương khói phôi phai đưa bước ai xa rồi
    [02:23.58]Đơn côi mình ta vấn vương, hồi ức trong men say chiều mưa buồn
    [02:29.32]Ngăn giọt lệ ngừng khiến khoé mi sầu bi
    [02:33.32]Đường xưa nơi cố nhân từ giã biệt li
    [02:36.88]Cánh hoa rụng rơi
    [02:39.38]Phận duyên mong manh rẽ lối trong mơ ngày tương phùng
    [02:44.60]Tiếng khóc cuốn theo làn gió bay
    [02:47.10]Thuyền ai qua sông lỡ quên vớt ánh trăng tàn nơi này
    [02:51.56]Trống vắng bóng ai dần hao gầy
    [02:57.43]Lòng ta xin nguyện khắc ghi trong tim tình nồng mê say
    [03:00.96]Mặc cho tóc mây vương lên đôi môi cay
    [03:04.22]Bâng khuâng mình ta lạc trôi giữa đời
    [03:07.95]Ta lạc trôi giữa trời
    [03:12.85]Ta lạc trôi (Lạc trôi)
    [03:13.18]Ta lạc trôi giữa đời
    [03:13.77]Lạc trôi giữa trời
    [03:14.46]Yeah, ah-h-h-h-h-h
    [03:42.07]Ta đang lạc nơi nào (Lạc nơi nào, lạc nơi nào)
    [03:49.06]Ta đang lạc nơi nào
    [03:54.62]Lối mòn đường vắng một mình ta
    [03:55.81]Ta đang lạc nơi nào
    [04:00.85]Nắng chiều vàng úa nhuộm ngày qua
    [04:02.64]Ta đang lạc nơi nào
'''

ouput_path = "/home/cao-le/Documents/lyrics"

def normalize_title(title):
    # Loại bỏ ký tự đặc biệt, chuyển về không dấu, lowercase, thay khoảng trắng bằng _
    title = re.sub(r"[^\w\s]", "", title)
    title = unidecode.unidecode(title)
    title = title.lower().replace(" ", "_")
    return title

def extract_title(lrc_text):
    ti_match = re.search(r"\[ti:\s*(.+?)\s*\]", lrc_text, re.IGNORECASE)
    ar_match = re.search(r"\[ar:\s*(.+?)\s*\]", lrc_text, re.IGNORECASE)
    title = normalize_title(ti_match.group(1)) if ti_match else ""
    artist = normalize_title(ar_match.group(1)) if ar_match else ""
    if title and artist:
        return f"{title}_{artist}"
    elif title:
        return title
    elif artist:
        return artist
    else:
        return "lyrics"

def clean_lrc_metadata(lrc_text):
    """
    Loại bỏ các dòng metadata khỏi nội dung .lrc
    """
    lines = lrc_text.strip().splitlines()
    cleaned = []
    for line in lines:
        if not re.match(r"\[(id:|ar:|al:|ti:|length:)", line.strip(), re.IGNORECASE):
            cleaned.append(line)
    return "\n".join(cleaned)

def lrc_to_json(lrc_text, output_path):
    """
    Chuyển lyrics dạng LRC sang JSON [{start, end, line}]
    """
    
    file_name = extract_title(lrc_text) + ".json"
    lrc_text = clean_lrc_metadata(lrc_text)

    # print(lrc_text)

    pattern = re.compile(r"\[(\d+):(\d+\.\d+)\](.*)")
    
    entries = []

    for line in lrc_text.splitlines():
        match = pattern.match(line.strip())

        print(match)

        if match:
            m, s, lyric = match.groups()
            start = int(m) * 60 + float(s)
            entries.append({
                "start": round(start, 2),
                "line": lyric.strip()
            })

    # Tính end cho từng dòng (dòng cuối end = start)
    for i in range(len(entries)):
        if i < len(entries) - 1:
            entries[i]["end"] = entries[i+1]["start"]
        else:
            entries[i]["end"] = entries[i]["start"]

    # Đưa trường end lên đúng thứ tự
    result = [{"start": e["start"], "end": e["end"], "line": e["line"]} for e in entries]

    output_path = os.path.join(output_path, file_name)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # print(result)

    return result

# json_result = lrc_to_json(lrc_text, ouput_path)
# print(json.dumps(json_result, ensure_ascii=False, indent=2))

''' 
    params:
        + first word segment
        + timestamp_lyrics
        + allow_distance (khoảng chênh lệch cho phép)
 '''

@dataclass
class TimestampLyric:
    timestamp: str
    lyric: str

def align_timestamps_with_amplitude(
    first_word_segment: Tuple[float, float], 
    timestamp_lyrics: List[TimestampLyric],  
    allow_difference: float 
) -> List[TimestampLyric]:
    """
    Align the first timestamp of lyrics with the first detected word segment.
    """
    try:
        adjusted_timestamps: List[TimestampLyric] = []

        if not timestamp_lyrics or not first_word_segment:
            print("[Debug] No timestamp_lyrics or first_word_segment provided.")
            return [TimestampLyric(timestamp=tl.timestamp, lyric=tl.lyric) for tl in timestamp_lyrics]

        # Extract the first timestamp and lyric
        first_timestamp = timestamp_lyrics[0].timestamp
        first_lyric = timestamp_lyrics[0].lyric
        print(f"[Debug] First timestamp: {first_timestamp}, First lyric: {first_lyric}")

        # Convert timestamp to seconds
        timestamp_seconds = float(first_timestamp.split(':')[0]) * 60 + float(first_timestamp.split(':')[1])
        print(f"[Debug] First timestamp in seconds: {timestamp_seconds}")

        # Extract the start time of the first detected word
        first_word_start = first_word_segment[0]
        print(f"[Debug] First word start: {first_word_start}")

        # Calculate the difference
        difference = first_word_start - timestamp_seconds
        # print(f"[Debug] Difference: {difference}")

        if abs(difference) <= allow_difference:
            print("[Debug] Difference is within allowable range.")
            adjusted_timestamps.append(TimestampLyric(timestamp=f"{timestamp_seconds:.2f}", lyric=first_lyric))
            adjusted_timestamps.extend(
                [TimestampLyric(timestamp=f"{float(tl.timestamp.split(':')[0]) * 60 + float(tl.timestamp.split(':')[1]):.2f}", lyric=tl.lyric) for tl in timestamp_lyrics[1:]]
            )
        else:
            print("[Debug] Adjusting all timestamps based on the detected word start time.")
            adjusted_timestamps.append(TimestampLyric(timestamp=f"{first_word_start:.2f}", lyric=first_lyric))
            for tl in timestamp_lyrics[1:]:
                original_seconds = float(tl.timestamp.split(':')[0]) * 60 + float(tl.timestamp.split(':')[1])
                adjusted_seconds = original_seconds + difference
                print(f"[Debug] Original seconds: {original_seconds}, Adjusted seconds: {adjusted_seconds}, Lyric: {tl.lyric}")
                adjusted_timestamps.append(TimestampLyric(timestamp=f"{adjusted_seconds:.2f}", lyric=tl.lyric))

        print(f"[Debug] Adjusted timestamps: {adjusted_timestamps}")

        return adjusted_timestamps

    except Exception as e:
        print(f"[Error] Failed to align timestamps: {str(e)}")
        return []