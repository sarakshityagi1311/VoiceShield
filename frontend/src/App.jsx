import React, { useState, useEffect } from 'react';

// Hardcoded fallback points directly to your active Render service
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://voiceshield-13.onrender.com';

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('Checking connection...');
  const [logs, setLogs] = useState([]);
  const [backendStatus, setBackendStatus] = useState('offline');

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (res.ok) {
        const data = await res.json();
        setBackendStatus(data.web3_connected ? 'online' : 'degraded');
        setStatus(
          data.web3_connected
            ? 'System Ready. API & Blockchain active.'
            : 'API active (Blockchain disconnected).'
        );
      } else {
        setBackendStatus('offline');
        setStatus('API Offline.');
      }
    } catch (error) {
      setBackendStatus('offline');
      setStatus('Unable to connect to VoiceShield API service.');
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
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

      setLogs((prevLogs) => [
        {
          filename: result.filename,
          hash: result.file_hash,
          score: result.spoof_probability,
          classification: result.classification,
          isSynthetic: result.is_synthetic,
          txHash: result.tx_hash,
          timestamp: new Date().toLocaleTimeString(),
        },
        ...prevLogs,
      ]);

      setStatus(`Verification complete. Result: ${result.classification}`);
    } catch (error) {
      console.error('Error uploading file:', error);
      alert(`Error processing audio: ${error.message}`);
      setStatus('Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>VoiceShield</h1>
        <p style={styles.subtitle}>AI Deepfake Audio Detection & Immutable Verification Ledger</p>
        <div style={styles.badgeContainer}>
          <span
            style={{
              ...styles.badge,
              backgroundColor:
                backendStatus === 'online'
                  ? '#22c55e'
                  : backendStatus === 'degraded'
                  ? '#eab308'
                  : '#ef4444',
            }}
          >
            API: {backendStatus.toUpperCase()}
          </span>
        </div>
      </header>

      <main style={styles.main}>
        <section style={styles.card}>
          <h2 style={styles.cardTitle}>Verify Voice Recording</h2>
          <form onSubmit={handleSubmit} style={styles.form}>
            <input
              type="file"
              accept="audio/*"
              onChange={handleFileChange}
              style={styles.fileInput}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !file}
              style={{
                ...styles.button,
                opacity: loading || !file ? 0.6 : 1,
                cursor: loading || !file ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Analyzing Spectrogram...' : 'Verify Recording'}
            </button>
          </form>
          <p style={styles.statusText}>Status: {status}</p>
        </section>

        <section style={styles.card}>
          <h2 style={styles.cardTitle}>Smart Contract Audit Logs</h2>
          {logs.length === 0 ? (
            <p style={styles.emptyText}>No verifications executed in this session.</p>
          ) : (
            <div style={styles.tableContainer}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Time</th>
                    <th style={styles.th}>File Name</th>
                    <th style={styles.th}>SHA-256 Hash</th>
                    <th style={styles.th}>Spoof %</th>
                    <th style={styles.th}>Classification</th>
                    <th style={styles.th}>Transaction Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, index) => (
                    <tr key={index} style={styles.tr}>
                      <td style={styles.td}>{log.timestamp}</td>
                      <td style={styles.td}>{log.filename}</td>
                      <td style={{ ...styles.td, ...styles.mono }}>
                        {log.hash.substring(0, 10)}...
                      </td>
                      <td style={styles.td}>{log.score}%</td>
                      <td style={styles.td}>
                        <span
                          style={{
                            ...styles.tag,
                            backgroundColor: log.isSynthetic ? '#fecaca' : '#bbf7d0',
                            color: log.isSynthetic ? '#991b1b' : '#166534',
                          }}
                        >
                          {log.classification}
                        </span>
                      </td>
                      <td style={{ ...styles.td, ...styles.mono }}>
                        {log.txHash !== 'Transaction Failed' && log.txHash !== 'Web3 Not Connected'
                          ? `${log.txHash.substring(0, 10)}...`
                          : log.txHash}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

const styles = {
  container: {
    fontFamily: 'Inter, system-ui, Avenir, Helvetica, Arial, sans-serif',
    backgroundColor: '#0f172a',
    color: '#f8fafc',
    minHeight: '100vh',
    padding: '2rem',
  },
  header: {
    textAlign: 'center',
    marginBottom: '2rem',
  },
  title: {
    fontSize: '2.5rem',
    fontWeight: '800',
    margin: '0',
    color: '#38bdf8',
  },
  subtitle: {
    fontSize: '1rem',
    color: '#94a3b8',
    marginTop: '0.5rem',
  },
  badgeContainer: {
    marginTop: '1rem',
  },
  badge: {
    padding: '0.25rem 0.75rem',
    borderRadius: '9999px',
    fontSize: '0.85rem',
    fontWeight: 'bold',
    color: '#ffffff',
  },
  main: {
    maxWidth: '900px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '2rem',
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: '0.75rem',
    padding: '1.5rem',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  },
  cardTitle: {
    fontSize: '1.25rem',
    fontWeight: '600',
    marginBottom: '1rem',
    color: '#f1f5f9',
  },
  form: {
    display: 'flex',
    gap: '1rem',
    flexWrap: 'wrap',
    marginBottom: '1rem',
  },
  fileInput: {
    flex: '1',
    padding: '0.5rem',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '0.375rem',
    color: '#f8fafc',
  },
  button: {
    backgroundColor: '#0284c7',
    color: '#ffffff',
    border: 'none',
    borderRadius: '0.375rem',
    padding: '0.5rem 1.5rem',
    fontWeight: '600',
  },
  statusText: {
    fontSize: '0.9rem',
    color: '#cbd5e1',
    margin: '0',
  },
  emptyText: {
    color: '#64748b',
    fontStyle: 'italic',
  },
  tableContainer: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    textAlign: 'left',
    fontSize: '0.9rem',
  },
  th: {
    borderBottom: '2px solid #334155',
    padding: '0.75rem',
    color: '#94a3b8',
  },
  tr: {
    borderBottom: '1px solid #334155',
  },
  td: {
    padding: '0.75rem',
  },
  mono: {
    fontFamily: 'monospace',
  },
  tag: {
    padding: '0.25rem 0.5rem',
    borderRadius: '0.25rem',
    fontWeight: 'bold',
    fontSize: '0.75rem',
  },
};