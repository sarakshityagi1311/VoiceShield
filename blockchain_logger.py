import json
import os
from web3 import Web3

# Connect to Local Hardhat Node
RPC_URL = "http://127.0.0.1:8545"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise ConnectionError("Failed to connect to local Hardhat node.")

# Deployed Contract Address from earlier step
CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

# Hardhat Account #0 private key
OWNER_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
account = w3.eth.account.from_key(OWNER_PRIVATE_KEY)

# Load Compiled Contract ABI from local artifacts
ARTIFACT_PATH = os.path.join("artifacts", "contracts", "VoiceRegistry.sol", "VoiceRegistry.json")
with open(ARTIFACT_PATH, "r") as f:
    artifact = json.load(f)

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=artifact["abi"])

def log_spoof_event(user_address: str, audio_bytes: bytes, spoof_score_pct: float):
    """
    Submits a detection log to the VoiceRegistry smart contract.
    """
    audio_hash = w3.keccak(audio_bytes)
    score_scaled = int(spoof_score_pct * 100)
    is_synthetic = score_scaled >= 8500  # Threshold >= 85.00%

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
        'gasPrice': w3.eth.gas_price
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=OWNER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"[EVM Bridge] Logged successfully in Block #{receipt.blockNumber} (Tx Hash: {tx_hash.hex()})")
    return receipt

if __name__ == "__main__":
    dummy_audio = b"synthetic_voice_sample_data"
    dummy_user = account.address
    log_spoof_event(dummy_user, dummy_audio, spoof_score_pct=92.3)