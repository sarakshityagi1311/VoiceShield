// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VoiceRegistry {
    address public owner;

    struct AttackRecord {
        bytes32 audioHash;
        uint256 spoofScore;
        uint256 timestamp;
        bool isSynthetic;
    }

    mapping(address => AttackRecord[]) private attackLogs;

    event AttackDetected(address indexed user, bytes32 indexed audioHash, uint256 spoofScore);

    modifier onlyOwner() {
        require(msg.sender == owner, "Unauthorized caller");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function logDetection(
        address _user,
        bytes32 _audioHash,
        uint256 _spoofScore,
        bool _isSynthetic
    ) external onlyOwner {
        attackLogs[_user].push(AttackRecord(_audioHash, _spoofScore, block.timestamp, _isSynthetic));
        
        if (_isSynthetic && _spoofScore >= 8500) {
            emit AttackDetected(_user, _audioHash, _spoofScore);
        }
    }

    function getLogs(address _user) external view returns (AttackRecord[] memory) {
        return attackLogs[_user];
    }
}