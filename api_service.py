import os
import shutil
import tempfile
import torch
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from main_pipeline import VoiceSpoofCNN, process_and_log_audio
from blockchain_logger import account, contract

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from Vercel and localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Load Model Architecture & Weights
model = VoiceSpoofCNN()
if os.path.exists("voice_spoof_cnn.pth"):
    model.load_state_dict(torch.load("voice_spoof_cnn.pth"))
    print("[API] Loaded trained weights from voice_spoof_cnn.pth")
else:
    print("[API] Warning: Running with default initialized weights")

model.eval()

class VerificationResponse(BaseModel):
    filename: str
    user_address: str
    spoof_score_pct: float
    is_synthetic: bool
    logged_on_chain: bool

@app.post("/verify-voice", response_model=VerificationResponse)
async def verify_voice(user_address: str, file: UploadFile = File(...)):
    """Accepts an uploaded WAV file and evaluates it for synthetic spoofing."""
    if not file.filename.endswith(".wav"):
        raise HTTPException(status_code=400, detail="Only .wav audio files are supported.")

    # Save uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name

    try:
        # Run classification pipeline
        from main_pipeline import preprocess_audio
        input_tensor, raw_bytes = preprocess_audio(tmp_path)
        
        with torch.no_grad():
            output = model(input_tensor)
            spoof_score_pct = float(output.item()) * 100.0

        is_synthetic = spoof_score_pct >= 85.00
        logged_on_chain = False

        # Submit transaction if high-risk score detected
        if is_synthetic:
            from blockchain_logger import log_spoof_event
            log_spoof_event(user_address, raw_bytes, spoof_score_pct)
            logged_on_chain = True

        return VerificationResponse(
            filename=file.filename,
            user_address=user_address,
            spoof_score_pct=round(spoof_score_pct, 2),
            is_synthetic=is_synthetic,
            logged_on_chain=logged_on_chain
        )

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.get("/on-chain-logs/{user_address}")
async def get_user_logs(user_address: str):
    """Retrieves all historical spoofing records logged on-chain for a given wallet address."""
    logs = contract.functions.getLogs(user_address).call()
    
    formatted_logs = []
    for idx, log in enumerate(logs, 1):
        formatted_logs.append({
            "record_id": idx,
            "audio_hash": f"0x{log[0].hex()}",
            "spoof_score_pct": log[1] / 100.0,
            "timestamp": log[2],
            "is_synthetic": log[3]
        })

    return {"user_address": user_address, "total_records": len(formatted_logs), "logs": formatted_logs}