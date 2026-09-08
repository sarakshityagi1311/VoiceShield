import React, { useState, useEffect } from 'react';

// Read API URL from Vite environment variable, fallback to Render URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://voiceshield-api.onrender.com';

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('Checking connection...');
  const [logs, setLogs] = useState([]);
  const [backendStatus, setBackendStatus] = useState('offline');

  // Check backend connectivity on mount
  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (res.ok) {
        const data = await res.json();
        setBackendStatus(data.status === 'healthy' ? 'online' : 'degraded');
        setStatus('Backend online and ready.');
      } else {
        setBackendStatus('offline');
        setStatus('Backend returned non-200 response.');
      }
    } catch (err) {
      setBackendStatus('offline');
      setStatus('Cannot reach backend server.');
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      alert('Please select an audio file first.');
      return;
    }

    setLoading(true);
    setStatus('Uploading audio and requesting verification...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/verify-audio`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const result = await response.json();
      setStatus(`Processing complete! Verdict: ${result.is_deepfake ? 'DEEPFAKE DETECTED' : 'AUTHENTIC VOICE'}`);
      
      // Append new log item
      setLogs((prev) => [
        {
          id: Date.now(),
          filename: file.name,
          verdict: result.is_deepfake ? 'Deepfake' : 'Authentic',
          txHash: result.tx_hash || 'Pending / Local',
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prev,
      ]);
    } catch (error) {
      console.error('Processing Error:', error);
      alert(`Error processing audio: ${error.message}`);
      setStatus('Network Error / Processing failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1>VoiceShield Audit Dashboard</h1>
        <div style={styles.badgeContainer}>
          <span style={{
            ...styles.badge,
            backgroundColor: backendStatus === 'online' ? '#22c55e' : '#ef4444'
          }}>
            API: {backendStatus.toUpperCase()}
          </span>
        </div>
      </header>

      <main style={styles.main}>
        {/* Upload Card */}
        <div style={styles.card}>
          <h2>Verify Voice Recording</h2>
          <form onSubmit={handleUpload} style={styles.form}>
            <input 
              type="file" 
              accept="audio/*" 
              onChange={handleFileChange} 
              style={styles.fileInput} 
            />
            <button 
              type="submit" 
              disabled={loading || !file} 
              style={loading ? {...styles.button, opacity: 0.6} : styles.button}
            >
              {loading ? 'Processing...' : 'Verify & Commit On-Chain'}
            </button>
          </form>
          <p style={styles.statusText}><strong>Status:</strong> {status}</p>
        </div>

        {/* Audit Log Table */}
        <div style={styles.card}>
          <h2>Smart Contract Audit Logs</h2>
          {logs.length === 0 ? (
            <p style={styles.emptyText}>No verifications executed in this session.</p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Time</th>
                  <th style={styles.th}>File</th>
                  <th style={styles.th}>Result</th>
                  <th style={styles.th}>Transaction Hash</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td style={styles.td}>{log.timestamp}</td>
                    <td style={styles.td}>{log.filename}</td>
                    <td style={styles.td}>
                      <span style={{
                        color: log.verdict === 'Deepfake' ? '#ef4444' : '#22c55e',
                        fontWeight: 'bold'
                      }}>
                        {log.verdict}
                      </span>
                    </td>
                    <td style={{...styles.td, fontFamily: 'monospace'}}>{log.txHash}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}

// Inline styles object for quick setup
const styles = {
  container: { maxWidth: '900px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif', color: '#1e293b' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #e2e8f0', paddingBottom: '10px' },
  badgeContainer: { display: 'flex', gap: '10px' },
  badge: { color: '#fff', padding: '4px 12px', borderRadius: '12px', fontSize: '12px', fontWeight: 'bold' },
  main: { marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '20px' },
  card: { padding: '20px', borderRadius: '8px', border: '1px solid #e2e8f0', backgroundColor: '#f8fafc' },
  form: { display: 'flex', gap: '10px', margin: '15px 0' },
  fileInput: { padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px', flexGrow: 1 },
  button: { padding: '10px 20px', backgroundColor: '#0284c7', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' },
  statusText: { fontSize: '14px', color: '#64748b' },
  emptyText: { color: '#94a3b8', fontStyle: 'italic' },
  table: { width: '100%', borderCollapse: 'collapse', marginTop: '10px' },
  th: { textAlign: 'left', borderBottom: '2px solid #cbd5e1', padding: '8px', fontSize: '14px' },
  td: { padding: '8px', borderBottom: '1px solid #e2e8f0', fontSize: '14px' }
};