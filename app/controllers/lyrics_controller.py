from flask import Blueprint, request, jsonify
from app.services.song_infor_fetcher import fetch_lyrics_from_genius

lyrics_bp = Blueprint('lyrics', __name__)

@lyrics_bp.route('/lyrics', methods=['GET'])
def get_lyrics():
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Missing query'}), 400
    result, error = fetch_lyrics_from_genius(query)
    if error:
        return jsonify({'error': error}), 404
    return jsonify(result)