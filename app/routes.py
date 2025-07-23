from app.controllers.align_controller import align_bp
from app.controllers.lyrics_controller import lyrics_bp
from app.controllers.amplitude_controller import amplitude_bp
from app.controllers.transcription_controller import transcription_bp
from app.controllers.karaoke_controller import karaoke_bp

def register_routes(app):
    app.register_blueprint(align_bp)
    app.register_blueprint(lyrics_bp)
    app.register_blueprint(amplitude_bp)
    app.register_blueprint(transcription_bp)
    app.register_blueprint(karaoke_bp)