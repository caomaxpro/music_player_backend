import sys
import torch
import whisperx
from app import create_app
import os
import subprocess

app = create_app()

# check if GPU is available
# device = "cuda" if torch.cuda.is_available() else "cpu"
# model = whisperx.load_model("tiny", device=device, compute_type="int8")

# Gán model vào app context
# app.config["whisperx_model"] = model

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)