from flask import Blueprint, request, jsonify
from app.services.text_align_forcer import force_align_lyrics_with_mfa, force_align_lyrics_with_gentle, force_align_lyrics_with_whisperx
from textgrid import TextGrid

align_bp = Blueprint('align', __name__)

def parse_textgrid_to_json(textgrid_path):
    tg = TextGrid()
    tg.read(textgrid_path)
    # Giả sử tier đầu tiên là lyrics
    tier = tg[0]
    segments = []
    for interval in tier:
        if interval.mark.strip():
            segments.append({
                "start": int(interval.minTime * 1000),  # convert to ms
                "end": int(interval.maxTime * 1000),    # convert to ms
                "text": interval.mark
            })
    return segments

@align_bp.route('/align', methods=['POST'])
def align():
    """
    API endpoint to force-align lyrics with audio using MFA.
    Expects:
      - audio_file: file (wav or mp3)
      - lyrics: string (lyrics to align)
    """
    audio_file = request.files.get('audio_file')
    language = request.form.get('language', 'en')

    lyrics = request.form.get('lyrics')
    if not audio_file or not lyrics:
        return jsonify({'error': 'Missing audio_file or lyrics'}), 400

    # Đường dẫn model và dictionary (bạn cần chỉnh lại cho phù hợp hệ thống của bạn)
    acoustic_model_path = "/path/to/acoustic_model.zip"
    dictionary_path = "/path/to/dictionary.dict"

    # textgrid_path, error = force_align_lyrics_with_mfa(
    #     lyrics,
    #     audio_file,
    #     acoustic_model_path,
    #     dictionary_path
    # )
    
    result, error = force_align_lyrics_with_gentle(
        lyrics,
        audio_file
    )

    # result, error = force_align_lyrics_with_whisperx(
    #     audio_file,
    #     language=language
    # )

    if error:
        return jsonify({'error': error}), 500

    # Parse TextGrid thành JSON
    return jsonify(result)