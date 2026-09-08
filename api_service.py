import os
import tempfile
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3

app = FastAPI()

# Enable CORS for cross-origin frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment and Network Settings
RPC_URL = os.getenv("RPC_URL", "https://xxxx.ngrok-free.app") # Set in Render environment
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

# Web3 Initialization with tunnel bypass header
w3 = Web3(
    Web3.HTTPProvider(
        RPC_URL,
        request_kwargs={"headers": {"Bypass-Tunnel-Reminder": "true", "ngrok-skip-browser-warning": "true"}}
    )
)

# Minimal Smart Contract ABI for logging
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "fileHash", "type": "string"},
            {"internalType": "bool", "name": "isDeepfake", "type": "bool"}
        ],
        "name": "logVerification",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

@app.get("/")
def read_root():
    return {"status": "VoiceShield API Active", "web3_connected": w3.is_connected()}

@app.get("/health")
def health_check():
    return {"status": "healthy", "web3_connected": w3.is_connected()}

@app.post("/verify-audio")
async def verify_audio(file: UploadFile = File(...)):
    # Save incoming audio file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

    # Audio Processing & Feature Extraction Logic
    try:
        # Dummy analysis output (Replace with model inference if needed)
        is_deepfake = False 
        file_hash = f"hash_{os.path.basename(file.filename)}"
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Smart Contract Transaction Execution
    tx_hash_hex = "0x0000000000000000000000000000000000000000000000000000000000000000"
    if w3.is_connected():
        try:
            account = w3.eth.account.from_key(PRIVATE_KEY)
            contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
            
            nonce = w3.eth.get_transaction_count(account.address)
            tx = contract.functions.logVerification(file_hash, is_deepfake).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': w3.eth.gas_price
            })
            
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = w3.to_hex(tx_hash)
        except Exception as e:
            print(f"Blockchain logging failed: {str(e)}")

    return {
        "filename": file.filename,
        "is_deepfake": is_deepfake,
        "tx_hash": tx_hash_hex,
        "status": "success"
    }