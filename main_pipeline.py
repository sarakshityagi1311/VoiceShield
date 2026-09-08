import os
import wave
import torch
import torch.nn as nn
import numpy as np
from scipy.signal import spectrogram
from blockchain_logger import log_spoof_event, account

# ------------------------------------------------------------------
# 1. PyTorch CNN Model Definition
# ------------------------------------------------------------------
class VoiceSpoofCNN(nn.Module):
    def __init__(self):
        super(VoiceSpoofCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(32 * 32 * 32, 64)
        self.fc2 = nn.Linear(64, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = self.relu(self.fc1(x))
        x = self.sigmoid(self.fc2(x))
        return x

# ------------------------------------------------------------------
# 2. Audio Processing Pipeline
# ------------------------------------------------------------------
def preprocess_audio(file_path: str) -> tuple[torch.Tensor, bytes]:
    """Reads WAV audio, extracts raw bytes, and converts to Mel-Spectrogram tensor."""
    with wave.open(file_path, 'rb') as wf:
        audio_bytes = wf.readframes(wf.getnframes())
        sr = wf.getframerate()
        signal = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)

    # Compute Spectrogram
    _, _, Sxx = spectrogram(signal, fs=sr)
    
    # Resize to standard 128x128 matrix
    Sxx_resized = np.resize(Sxx, (128, 128))
    tensor = torch.tensor(Sxx_resized, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    
    return tensor, audio_bytes

# ------------------------------------------------------------------
# 3. End-to-End Execution Pipeline
# ------------------------------------------------------------------
def process_and_log_audio(audio_path: str, user_address: str, model: nn.Module):
    print(f"\nProcessing Audio File: {audio_path}")
    
    # Preprocess audio
    input_tensor, raw_bytes = preprocess_audio(audio_path)
    
    # Model Inference
    model.eval()
    with torch.no_grad():
        output = model(input_tensor)
        spoof_score_pct = float(output.item()) * 100.0

    print(f"Prediction Complete -> Spoof Score: {spoof_score_pct:.2f}%")

    # Trigger EVM Smart Contract Logging if threshold (85.00%) is met
    if spoof_score_pct >= 85.00:
        print("[ALERT] High-risk synthetic voice detected! Submitting to Blockchain...")
        log_spoof_event(user_address, raw_bytes, spoof_score_pct)
    else:
        print("[INFO] Sample verified authentic (score < 85.00%). No blockchain record created.")

# ------------------------------------------------------------------
# 4. Main Entry Point
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Instantiate model
    model = VoiceSpoofCNN()

    # Load pre-trained model weights if present
    if os.path.exists("voice_spoof_cnn.pth"):
        model.load_state_dict(torch.load("voice_spoof_cnn.pth"))
        print("Loaded pre-trained weights from voice_spoof_cnn.pth")
    else:
        print("Running with default initialized model weights...")

    # Run inference on sample audio
    test_audio = "test_sample.wav"
    target_user = account.address

    process_and_log_audio(test_audio, target_user, model)