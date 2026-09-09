import os
import io
import hashlib
import torch
import torchaudio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
import torch.nn as nn

# Model architecture matching your trained spoof_detector.pt checkpoint
class SpoofDetectorCNN(nn.Module):
    def __init__(self):
        super(SpoofDetectorCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(64 * 16 * 23, 128)
        self.fc2 = nn.Linear(128, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = torch.flatten(x, 1)
        x = torch.relu(self.fc1(x))
        x = self.sigmoid(self.fc2(x))
        return x

app = FastAPI(title="VoiceShield API - production")

# Enable Cross-Origin Resource Sharing for Vercel Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Environment Variables with production fallbacks
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

# Initialize PyTorch Model on CPU
device = torch.device('cpu')
model = SpoofDetectorCNN()
try:
    model.load_state_dict(torch.load("spoof_detector.pt", map_location=device))
    model.eval()
except Exception as e:
    print(f"Warning: Could not load model weights: {e}")

# Web3 Configuration with ngrok browser-warning bypass
w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"headers": {"ngrok-skip-browser-warning": "true"}}))

# VoiceRegistry Smart Contract ABI
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_fileHash", "type": "string"},
            {"internalType": "bool", "name": "_isSynthetic", "type": "bool"},
            {"internalType": "uint256", "name": "_confidenceScore", "type": "uint256"}
        ],
        "name": "recordVerification",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def analyze_audio_tensor(waveform, sr):
    if sr != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
        waveform = resampler(waveform)

    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    stride = 48000
    chunk_scores = []
    
    mel_transform = torchaudio.transforms.MelSpectrogram(
        sample_rate=16000, n_fft=1024, hop_length=512, n_mels=64
    )
    amp_to_db = torchaudio.transforms.AmplitudeToDB()

    for i in range(0, waveform.shape[1], stride):
        chunk = waveform[:, i:i + stride]
        if chunk.shape[1] < 48000:
            chunk = torch.nn.functional.pad(chunk, (0, 48000 - chunk.shape[1]))
        else:
            chunk = chunk[:, :48000]

        mel_spec = amp_to_db(mel_transform(chunk)).unsqueeze(0)

        with torch.no_grad():
            score = model(mel_spec).item()
            chunk_scores.append(score)

    return max(chunk_scores) if chunk_scores else 0.0

def commit_to_blockchain(file_hash: str, is_synthetic: bool, confidence: float):
    if not w3.is_connected():
        return "Web3 Not Connected"

    try:
        account = w3.eth.account.from_key(PRIVATE_KEY)
        contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
        
        confidence_scaled = int(confidence * 10000)
        
        tx = contract.functions.recordVerification(file_hash, is_synthetic, confidence_scaled).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        raw_bytes = getattr(signed_tx, 'raw_transaction', getattr(signed_tx, 'rawTransaction', None))
        
        tx_hash = w3.eth.send_raw_transaction(raw_bytes)
        return w3.to_hex(tx_hash)
    except Exception as e:
        print(f"Blockchain Error: {e}")
        return f"Transaction Failed: {str(e)}"

@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "VoiceShield API Active",
        "service_url": "https://voiceshield-13.onrender.com",
        "web3_connected": w3.is_connected()
    }

@app.post("/verify-audio")
async def verify_audio(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        file_hash = hashlib.sha256(audio_bytes).hexdigest()

        waveform, sr = torchaudio.load(io.BytesIO(audio_bytes))
        spoof_score = analyze_audio_tensor(waveform, sr)
        
        is_synthetic = spoof_score >= 0.50
        tx_hash = commit_to_blockchain(file_hash, is_synthetic, spoof_score)

        return {
            "filename": file.filename,
            "file_hash": file_hash,
            "spoof_probability": round(spoof_score * 100, 2),
            "classification": "SYNTHETIC (FAKE)" if is_synthetic else "AUTHENTIC (REAL)",
            "is_synthetic": is_synthetic,
            "tx_hash": tx_hash
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")