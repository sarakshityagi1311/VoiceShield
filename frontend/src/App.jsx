import React, { useState } from 'react';
import axios from 'axios';
import { ShieldCheck, AlertTriangle, Database, Cpu, RefreshCw } from 'lucide-react';
import './index.css';

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [walletAddress, setWalletAddress] = useState("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!file || !walletAddress) return;

    setLoading(true);
    setVerificationResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post(`${API_BASE}/verify-voice?user_address=${walletAddress}`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setVerificationResult(res.data);
      fetchLogs();
    } catch (err) {
      alert("Error processing audio: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    if (!walletAddress) return;
    setLogsLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/on-chain-logs/${walletAddress}`);
      setLogs(res.data.logs || []);
    } catch (err) {
      console.error("Failed to load logs:", err);
    } finally {
      setLogsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <ShieldCheck size={40} color="#38bdf8" />
        <div>
          <h1>VoiceShield</h1>
          <p>Synthetic Voice Detection & Immutable EVM Audit Registry</p>
        </div>
      </header>

      <div className="grid-layout">
        {/* Analysis Form */}
        <div className="card">
          <h2 className="card-title">
            <Cpu size={22} color="#38bdf8" /> Analyze Voice Sample
          </h2>

          <form onSubmit={handleVerify}>
            <div className="form-group">
              <label>Target Wallet Address</label>
              <input
                type="text"
                className="input-text"
                value={walletAddress}
                onChange={(e) => setWalletAddress(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Audio Payload (.wav)</label>
              <input
                type="file"
                accept=".wav"
                onChange={(e) => setFile(e.target.files[0])}
                style={{ color: '#94a3b8', fontSize: '0.9rem' }}
                required
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Evaluating Audio..." : "Verify & Commit"}
            </button>
          </form>

          {verificationResult && (
            <div className={`result-card ${verificationResult.is_synthetic ? 'synthetic' : 'authentic'}`}>
              <h3 style={{ fontSize: '1.05rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {verificationResult.is_synthetic ? <AlertTriangle color="#ef4444" /> : <ShieldCheck color="#10b981" />}
                {verificationResult.is_synthetic ? "Synthetic Voice Detected" : "Authentic Audio Verified"}
              </h3>
              <p style={{ fontSize: '0.9rem' }}><strong>Spoof Score:</strong> {verificationResult.spoof_score_pct}%</p>
              <p style={{ fontSize: '0.9rem' }}><strong>On-Chain Logged:</strong> {verificationResult.logged_on_chain ? "Yes" : "No"}</p>
            </div>
          )}
        </div>

        {/* Audit Log Panel */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h2 className="card-title" style={{ margin: 0 }}>
              <Database size={22} color="#38bdf8" /> Smart Contract Logs
            </h2>
            <button onClick={fetchLogs} className="btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <RefreshCw size={14} /> Refresh
            </button>
          </div>

          {logsLoading ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Querying EVM RPC Node...</p>
          ) : logs.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No audit entries registered for this wallet address.</p>
          ) : (
            <div style={{ maxHeight: '360px', overflowY: 'auto', paddingRight: '0.25rem' }}>
              {logs.map((log) => (
                <div key={log.record_id} className="log-item">
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                    <span>Record #{log.record_id}</span>
                    <span>{log.timestamp}</span>
                  </div>
                  <p className="log-hash">Hash: {log.audio_hash}</p>
                  <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
                    <strong>Score:</strong> {log.spoof_score_pct}% | <strong>Synthetic:</strong> {log.is_synthetic ? "True" : "False"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}