import os
import hashlib
import json
import time
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3

app = FastAPI(
    title="VoiceShield AI & Blockchain API",
    description="Backend service for deepfake audio detection and Ethereum on-chain verification.",
    version="1.0.0"
)

# CRITICAL FOR VERCEL: Allow CORS requests from any origin or specific Vercel domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (including Vercel frontend deployments)
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, OPTIONS, PUT, DELETE
    allow_headers=["*"],  # Allows all headers including Authorization & custom headers
)

RPC_URL = os.getenv("RPC_URL", "https://xxxx.ngrok-free.app")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

# Default VoiceShield Minimal Smart Contract ABI
DEFAULT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "fileHash", "type": "string"},
            {"internalType": "uint8", "name": "confidence", "type": "uint8"},
            {"internalType": "bool", "name": "isDeepfake", "type": "bool"}
        ],
        "name": "logVerification",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "string", "name": "fileHash", "type": "string"},
            {"indexed": False, "internalType": "uint8", "name": "confidence", "type": "uint8"},
            {"indexed": False, "internalType": "bool", "name": "isDeepfake", "type": "bool"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "AudioVerified",
        "type": "event"
    }
]

# Initialize Web3 provider with custom headers for tunneling services (e.g. ngrok / localtunnel)
def get_web3_instance():
    headers = {"Bypass-Tunnel-Reminder": "true", "ngrok-skip-browser-warning": "true"}
    provider = Web3.HTTPProvider(RPC_URL, request_kwargs={"headers": headers, "timeout": 10})
    return Web3(provider)

class HealthResponse(BaseModel):
    status: str
    web3_connected: bool
    rpc_url: str
    contract_address: str

class AnalysisResponse(BaseModel):
    file_name: str
    file_hash: str
    is_deepfake: bool
    confidence_score: int
    spectral_entropy: float
    on_chain_logged: bool
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    timestamp: float

@app.get("/", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse)
def health_check():
    """Verify backend status and Web3 RPC connectivity."""
    w3 = get_web3_instance()
    is_connected = False
    try:
        is_connected = w3.is_connected()
    except Exception as e:
        print(f"Web3 connection error: {e}")

    return HealthResponse(
        status="active",
        web3_connected=is_connected,
        rpc_url=RPC_URL,
        contract_address=CONTRACT_ADDRESS
    )

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(file: UploadFile = File(...)):
    """Receives audio sample, computes cryptographic hash, performs deepfake analysis, and logs to smart contract."""
    if not file.filename.endswith(('.wav', '.mp3', '.ogg', '.flac', '.m4a')):
        raise HTTPException(status_code=400, detail="Invalid audio file format supported (.wav, .mp3, .ogg, .flac)")

    try:
        # Read raw bytes and calculate SHA-256 fingerprint
        contents = await file.read()
        sha256_hash = hashlib.sha256(contents).hexdigest()

        # Perform synthetic spectrum feature extraction simulation
        file_size = len(contents)
        byte_sum = sum(contents[:1000]) if file_size > 1000 else sum(contents)
        spectral