import json
import os
from web3 import Web3

# Use environment variable for RPC_URL (defaults to localhost, but uses ngrok on Render)
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")

# Add ngrok bypass header so Web3.py doesn't get blocked by the warning page
w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"headers": {"ngrok-skip-browser-warning": "true"}}))

# Soft connection check to prevent server crashes on boot
try:
    if not w3.is_connected():
        print(f"[EVM Bridge Warning] Web3 currently unreachable at {RPC_URL}. Will retry on request.")
    else:
        print(f"[EVM Bridge] Connected successfully to RPC endpoint: {RPC_URL}")
except Exception as e:
    print(f"[EVM Bridge Error] Initial connection attempt failed: {e}")

# Load environment variables for credentials
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
OWNER_PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

account = w3.eth.account.from_key(OWNER_PRIVATE_KEY)

# Load ABI cleanly from local file or minimal inline fallback
ARTIFACT_PATH = os.path.join("artifacts", "contracts", "VoiceRegistry.sol", "VoiceRegistry.json")

if os.path.exists(ARTIFACT_PATH):
    with open(ARTIFACT_PATH, "r") as f:
        artifact = json.load(f)
        contract_abi = artifact["abi"]
else:
    # Minimal ABI fallback if build artifacts are ignored in git
    contract_abi = [
        {
            "inputs": [
                {"internalType": "address", "name": "user_address", "type": "address"},
                {"internalType": "bytes32", "name": "audio_hash", "type": "bytes32"},
                {"internalType": "uint256", "name": "score_scaled", "type": "uint256"},
                {"internalType": "bool", "name": "is_synthetic", "type": "bool"}
            ],
            "name": "logDetection",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

def log_spoof_event(user_address: str, audio_bytes: bytes, spoof_score_pct: float):
    """
    Submits a detection log to the VoiceRegistry smart contract.
    """
    if not w3.is_connected():
        print("[EVM Bridge] Skipped transaction: Web3 provider is unreachable.")
        return None

    audio_hash = w3.keccak(audio_bytes)
    score_scaled = int(spoof_score_pct * 100)
    
    # Updated threshold to 50.00% to catch modern TTS voices
    is_synthetic = score_scaled >= 5000 

    print(f"\n[EVM Bridge] Logging payload for {user_address}...")
    print(f"  Audio Hash: {audio_hash.hex()}")
    print(f"  Spoof Score: {spoof_score_pct:.2f}% ({score_scaled})")
    print(f"  Flagged Synthetic: {is_synthetic}")

    tx = contract.functions.logDetection(
        Web3.to_checksum_address(user_address),
        audio_hash,
        score_scaled,
        is_synthetic
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 300000,
        'maxFeePerGas': w3.to_wei('2', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('1', 'gwei')
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=OWNER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    print(f"[EVM Bridge] Broadcasted Tx Hash: {tx_hash.hex()}")
    return tx_hash.hex()

if __name__ == "__main__":
    dummy_audio = b"synthetic_voice_sample_data"
    dummy_user = account.address
    log_spoof_event(dummy_user, dummy_audio, spoof_score_pct=92.3)