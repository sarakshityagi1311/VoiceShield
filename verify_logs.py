from blockchain_logger import contract, account

# Fetch all logs for the registered account
logs = contract.functions.getLogs(account.address).call()

print("================ ON-CHAIN REGISTRY LOGS ================")
for idx, log in enumerate(logs, 1):
    audio_hash, spoof_score, timestamp, is_synthetic = log
    print(f"Record #{idx}:")
    print(f"  Audio Hash : 0x{audio_hash.hex()}")
    print(f"  Spoof Score: {spoof_score / 100:.2f}% ({spoof_score})")
    print(f"  Timestamp  : {timestamp}")
    print(f"  Synthetic  : {is_synthetic}")
    print("-" * 56)