import codecs
from flask import Flask, json, request, jsonify
import librosa
import numpy as np
import tempfile
import os
import subprocess
import whisperx
import sys
import requests
from bs4 import BeautifulSoup
import urllib.parse
import torch
from bs4 import Tag

app = Flask(__name__)

# Đường dẫn python của env2
env2_python = "/home/cao-le/Flutter Projects/music_player_app/backend/env2/bin/python"

def spleeter_separate(input_path, output_dir):
    result = subprocess.run([
        env2_python, "-m", "spleeter", "separate", "-p", "spleeter:2stems", "-o", output_dir, input_path
    ], capture_output=True, text=True)
    return result

# Kiểm tra CUDA
if torch.cuda.is_available():
    print("CUDA is available. Using GPU for inference.")
    device = "cuda"
else:
    print("CUDA is NOT available. Exiting. Please install CUDA and a compatible GPU.")
    sys.exit("CUDA is not available. Server stopped.")

# Load model 1 lần duy nhất khi khởi động server
model = whisperx.load_model(
    "tiny",
    device=device,
    compute_type="int8"
)
align_model, metadata = whisperx.load_align_model(language_code="vi", device=device)

GENIUS_TOKEN = "yI7jrw69mBdd7PVOzcvzlBQ7MWW2ODEFNYbMVKj85F589hwYvlwhPrJMIU5coQCy"  

@app.route('/search_lyrics', methods=['GET'])
def search_lyrics():
    song_title = request.args.get('song_title', '')
    artist = request.args.get('artist', '')
    if not song_title:
        return jsonify({'error': 'Missing song_title'}), 400
    
    encoded_song_title = urllib.parse.quote(song_title)
    encoded_artist = urllib.parse.quote(artist)

    print(f"{song_title}: {encoded_song_title}")

    search_url = f"https://api.genius.com/search?q={encoded_song_title}"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    response = requests.get(search_url, headers=headers)
    hits = response.json()["response"]["hits"]

    # Lấy thông tin cơ bản của từng bài hát
    results = []
    for hit in hits:
        result = hit["result"]
        results.append({
            "title": result.get("title"),
            "artist_names": result.get("artist_names"),
            "full_title": result.get("full_title"),
            "url": result.get("url"),
            "song_art_image_url": result.get("song_art_image_url"),
        })

    return jsonify({"results": results})

def decode_unicode_escape(text):
    try:
        # Decode nhiều lần cho đến khi ra unicode chuẩn
        for _ in range(3):
            text = codecs.decode(text, 'unicode_escape')

        text = text.encode('latin1').decode('utf-8')
        return text
    except Exception:
        return text

def fetch_lyrics(song_title, artist):
    # Encode song title và artist để đảm bảo URL hợp lệ
    encoded_song_title = urllib.parse.quote(song_title)
    encoded_artist = urllib.parse.quote(artist)
    search_url = f"https://api.genius.com/search?q={encoded_song_title}%20{encoded_artist}"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    response = requests.get(search_url, headers=headers)
    hits = response.json()["response"]["hits"]
    if not hits:
        return None
    song_url = hits[0]["result"]["url"]
    # Scrape lyrics from song_url
    page = requests.get(song_url)
    soup = BeautifulSoup(page.text, "html.parser")
    # Genius mới dùng <div data-lyrics-container="true">
    lyrics = "\n".join([el.get_text(separator="\n") for el in soup.find_all("div", attrs={"data-lyrics-container": "true"})])
    lyrics = lyrics.strip() if lyrics else None
    # if lyrics:
    #     lyrics = decode_unicode_escape(json.loads(lyrics)["lyrics"])
    return lyrics

@app.route('/lyrics', methods=['GET'])
def get_lyrics():
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Missing query'}), 400

    # Encode query để đảm bảo URL hợp lệ
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://api.genius.com/search?q={encoded_query}"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    response = requests.get(search_url, headers=headers)

    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch lyrics'}), response.status_code

    hits = response.json().get("response", {}).get("hits", [])
    if not hits:
        return jsonify({'error': 'Lyrics not found'}), 404

    # Lấy URL của bài hát đầu tiên trong kết quả tìm kiếm

    result = hits[0]["result"]
    song_url = result["url"]
    song_title = result["full_title"]
    song_artist = result["artist_names"]
    song_image_url = result["song_art_image_url"]

    # Scrape lyrics từ URL của bài hát
    page = requests.get(song_url)
    soup = BeautifulSoup(page.text, "html.parser")
    lyrics_elements = soup.find_all("div", attrs={"data-lyrics-container": "true"})
    
    lyrics = []
    for div in lyrics_elements:
        if isinstance(div, Tag):
            # Lấy nội dung từ các thẻ <br> và nối chúng lại
            for content in div.contents:
                if isinstance(content, str):
                    lyrics.append(content.strip())
                elif isinstance(content, Tag) and content.name == "br":
                    lyrics.append("\n")  # Thay <br> bằng xuống dòng
                elif isinstance(content, Tag) and content.name == "a":
                    a_text = content.get_text(separator="\n", strip=True)
                    lyrics.append(a_text)
                    lyrics.append("\n")  # Thêm xuống dòng sau nội dung thẻ <a>

    # print(lyrics)

    # Kết hợp các dòng lyrics lại
    lyrics = " ".join(lyrics).strip()

    # Làm sạch lyrics: loại bỏ các dòng metadata như [Chorus], [Verse]
    filtered_lyrics = "\n".join([
        line for line in lyrics.split("\n")
        if not line.startswith("[") and line.strip()  # Loại bỏ dòng bắt đầu bằng [ và dòng trống
    ])

    if not filtered_lyrics:
        return jsonify({'error': 'Lyrics not found'}), 404
    

    return jsonify({
        'lyrics': filtered_lyrics, 
        'song_url': result["url"],
        'song_title': result["full_title"],
        'song_artist': result["artist_names"],
        'song_image_url': result["song_art_image_url"]
    })

@app.route('/amplitude', methods=['POST'])
def amplitude():
    print("[Flutter => Python]: Receive request")

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        y, sr = librosa.load(tmp_path, sr=None)
        rms = librosa.feature.rms(y=y)[0]
        # Downsample RMS to 100 points for wave bar
        target_points = 100
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
        os.remove(tmp_path)

    return jsonify({'rms': rms_list})

@app.route('/align_lyrics', methods=['POST'])
def align_lyrics():
    song_title = request.form.get('song_title')
    artist = request.form.get('artist')
    if not song_title or not artist:
        return jsonify({'error': 'Missing song_title or artist'}), 400
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    lyrics = fetch_lyrics(song_title, artist)
    if not lyrics:
        return jsonify({'error': 'Lyrics not found'}), 404

    file = request.files['file']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        file.save(tmp.name)
        audio_path = tmp.name

    try:
        # Lấy độ dài audio
        y, sr = librosa.load(audio_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)

        # Tách lyrics thành từng dòng (hoặc từng câu) để align tốt hơn
        lyric_lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
        num_lines = len(lyric_lines)
        segments = []
        if num_lines > 0:
            # Chia đều thời lượng cho từng dòng lyrics
            avg_duration = duration / num_lines
            for idx, line in enumerate(lyric_lines):
                start = idx * avg_duration
                end = (idx + 1) * avg_duration if idx < num_lines - 1 else duration
                segments.append({
                    "text": line,
                    "start": start,
                    "end": end
                })
        else:
            # Nếu không tách được dòng, align toàn bộ lyrics
            segments = [{
                "text": lyrics,
                "start": 0,
                "end": duration
            }]

        # Sử dụng đúng device đã khai báo ở trên (GPU nếu có)
        word_segments = whisperx.align(segments, align_model, metadata, audio_path, device=device)
    finally:
        os.remove(audio_path)

    return jsonify({'words': word_segments})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)