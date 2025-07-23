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
from difflib import SequenceMatcher
import re
from pydub import AudioSegment

app = Flask(__name__)

# Đường dẫn python của env2

# Kiểm tra CUDA

def decode_unicode_escape(text):
    try:
        # Decode nhiều lần cho đến khi ra unicode chuẩn
        for _ in range(3):
            text = codecs.decode(text, 'unicode_escape')

        text = text.encode('latin1').decode('utf-8')
        return text
    except Exception:
        return text


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)