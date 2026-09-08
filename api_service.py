import os
import io
import torch
import torch.nn as nn
import torchaudio.transforms as T
import librosa
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3

# ------------------------------------------------------------------
# 1. FastAPI Application Setup & CORS Configuration
# ------------------------------------------------------------------
app = FastAPI(
    title="VoiceShield API",
    description="Backend service for synthetic voice detection and EVM audit logging."
)

# Open CORS configuration allowing requests from Vercel and local environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# 2. PyTorch ML Architecture Definition
# ------------------------------------------------------------------
class VoiceSpoofCNN(nn.Module):
    def __init__(self):
        super(VoiceSpoofCNN, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((16, 16))
        )
        self.fc = nn.Sequential(
            nn.Linear(32 * 16 * 16, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)

# Load model weights safely
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = VoiceSpoofCNN().to(device)

MODEL_PATH = "voice_spoof_model.pth"
if os.path.exists(MODEL_PATH):
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.eval()
    print(f"[*] Loaded model weights successfully from {MODEL_PATH}")
else:
    print(f"[!] Warning: {MODEL_PATH} not found. Running with uninitialized weights.")
    model.eval()

# ------------------------------------------------------------------
# 3. Web3 & Smart Contract Setup
# ------------------------------------------------------------------
RPC_URL = "https://uranium-unbiased-duckbill.ngrok-free.dev -> http://localhost:8545 "
CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_user", "type": "address"},
            {"internalType": "string", "name": "_audioHash", "type": "string"},
            {"internalType": "uint8", "name": "_spoofScorePct", "type": "uint8"},
            {"internalType": "bool", "name": "_isSynthetic", "type": "bool"}
        ],
        "name": "logAuditRecord",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "_user", "type": "address"}],
        "name": "getAuditLogs",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "recordId", "type": "uint256"},
                    {"internalType": "string", "name": "audioHash", "type": "string"},
                    {"internalType": "uint8", "name": "spoofScorePct", "type": "uint8"},
                    {"internalType": "bool", "name": "isSynthetic", "type": "bool"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"}
                ],
                "internalType": "struct VoiceRegistry.AuditRecord[]",
                "name": "",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# ------------------------------------------------------------------
# 4. Helper Functions
# ------------------------------------------------------------------
def extract_spectrogram(audio_bytes: bytes) -> torch.Tensor:
    """Converts uploaded raw audio bytes into a normalized Mel Spectrogram tensor."""
    try:
        y, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000, duration=3.0)
        if len(y) < 16000 * 3:
            y = librosa.util.fix_length(y, size=16000 * 3)

        audio_tensor = torch.tensor(y, dtype=torch.float32)
        mel_transform = T.MelSpectrogram(sample_rate=16000, n_mels=64)
        spectrogram = mel_transform(audio_tensor)
        spectrogram = (spectrogram - spectrogram.mean()) / (spectrogram.std() + 1e-6)

        return spectrogram.unsqueeze(0).unsqueeze(0).to(device)
    except Exception as e:
        raise ValueError(f"Audio processing failed: {str(e)}")

# ------------------------------------------------------------------
# 5. API Endpoints
# ------------------------------------------------------------------
@app.get("/")
def health_check():
    """Health check endpoint to verify backend service status."""
    return {
        "status": "online",
        "service": "VoiceShield API",
        "blockchain_connected": w3.is_connected()
    }

@app.post("/verify-voice")
async def verify_voice(user_address: str, file: UploadFile = File(...)):
    """Processes uploaded audio file, calculates spoof score, and writes log to smart contract."""
    if not w3.is_checksum_address(user_address):
        user_address = w3.to_checksum_address(user_address)

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty audio file uploaded.")

    # 1. Feature extraction & model evaluation
    try:
        tensor = extract_spectrogram(contents)
        with torch.no_grad():
            raw_score = model(tensor).item()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to analyze audio: {str(e)}")

    spoof_score_pct = int(raw_score * 100)
    is_synthetic = spoof_score_pct >= 50
    audio_hash = w3.keccak(contents).hex()

    # 2. EVM Blockchain logging
    logged_on_chain = False
    tx_hash = None

    if w3.is_connected():
        try:
            accounts = w3.eth.accounts
            if accounts:
                tx = contract.functions.logAuditRecord(
                    user_address,
                    audio_hash,
                    spoof_score_pct,
                    is_synthetic
                ).transact({'from': accounts[0]})
                
                receipt = w3.eth.wait_for_transaction_receipt(tx)
                tx_hash = receipt.transactionHash.hex()
                logged_on_chain = True
        except Exception as e:
            print(f"[!] Smart contract logging failed: {str(e)}")

    return {
        "user_address": user_address,
        "audio_hash": audio_hash,
        "spoof_score_pct": spoof_score_pct,
        "is_synthetic": is_synthetic,
        "logged_on_chain": logged_on_chain,
        "tx_hash": tx_hash
    }

@app.get("/on-chain-logs/{user_address}")
def get_on_chain_logs(user_address: str):
    """Retrieves all historical audit logs for a given address from the smart contract."""
    if not w3.is_checksum_address(user_address):
        user_address = w3.to_checksum_address(user_address)

    if not w3.is_connected():
        raise HTTPException(status_code=503, detail="EVM node unreachable.")

    try:
        raw_logs = contract.functions.getAuditLogs(user_address).call()
        formatted_logs = [
            {
                "record_id": log[0],
                "audio_hash": log[1],
                "spoof_score_pct": log[2],
                "is_synthetic": log[3],
                "timestamp": log[4]
            }
            for log in raw_logs
        ]
        return {"user_address": user_address, "logs": formatted_logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch contract logs: {str(e)}")