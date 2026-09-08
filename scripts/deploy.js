import { ethers } from "ethers";

async function main() {
  const provider = new ethers.JsonRpcProvider("http://127.0.0.1:8545");
  const signer = await provider.getSigner();

  // Read compiled artifact
  const artifact = await import("../artifacts/contracts/VoiceRegistry.sol/VoiceRegistry.json", {
    assert: { type: "json" }
  });

  const factory = new ethers.ContractFactory(artifact.default.abi, artifact.default.bytecode, signer);
  const registry = await factory.deploy();
  await registry.waitForDeployment();

  const contractAddress = await registry.getAddress();
  console.log("--------------------------------------------------");
  console.log(`VoiceRegistry deployed successfully to: ${contractAddress}`);
  console.log("--------------------------------------------------");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});