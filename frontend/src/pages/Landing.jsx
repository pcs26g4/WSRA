import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import BackendInfo from '../components/BackendInfo';
import { startScan, getScanStatus, getScanSummary, exportScan } from '../api';

const Landing = () => {
    const [activeTab, setActiveTab] = useState('track'); // Default to track as per user focus
    const [targetUrl, setTargetUrl] = useState('');
    const [scanId, setScanId] = useState('');
    const [status, setStatus] = useState(null);
    const [summary, setSummary] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    // Poll for status if running
    React.useEffect(() => {
        let interval;
        if (status === 'RUNNING' || status === 'INITIALIZING') {
            interval = setInterval(async () => {
                try {
                    const data = await getScanStatus(scanId);
                    setStatus(data.status);
                    if (data.status === 'COMPLETED') {
                        const sum = await getScanSummary(scanId);
                        setSummary(sum);
                    }
                } catch (err) {
                    // Ignore temporary errors
                }
            }, 3000);
        }
        return () => clearInterval(interval);
    }, [status, scanId]);

    const handleStart = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            const res = await startScan(targetUrl);
            setScanId(res.scan_id);
            setStatus('INITIALIZING');
            setActiveTab('track');
        } catch (err) {
            setError('Failed to start scan. Ensure backend is running.');
        } finally {
            setLoading(false);
        }
    };

    const handleTrack = async (e) => {
        e.preventDefault();
        if (!scanId) return;
        setLoading(true);
        setError('');
        setSummary(null);
        try {
            const data = await getScanStatus(scanId);
            setStatus(data.status);
            if (data.status === 'COMPLETED') {
                try {
                    const sum = await getScanSummary(scanId);
                    setSummary(sum);
                } catch (summaryErr) {
                    console.error("Summary not ready yet", summaryErr);
                }
            }
        } catch (err) {
            setError('Scan not found or backend unavailable.');
            setStatus(null);
        } finally {
            setLoading(false);
        }
    };

    const handleDownload = async (format) => {
        try {
            const blob = await exportScan(scanId, format);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `wsra_scan_${scanId}.${format === 'burp' ? 'xml' : format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (err) {
            alert('Download failed. results may not be ready.');
        }
    };

    return (
        <>
            <Navbar />

            {/* HERO SECTION */}
            <section style={{
                paddingTop: '150px',
                paddingBottom: '80px',
                textAlign: 'center',
                background: 'radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.1) 0%, transparent 50%)'
            }}>
                <div className="container">
                    <h1 className="animate-float">Web Security<br />Reconnaissance Agent</h1>
                    <p style={{ fontSize: '1.2rem', margin: '2rem auto', maxWidth: '700px' }}>
                        An advanced, autonomous security agent designed to map, analyze, and identify vulnerabilities in modern web applications.
                    </p>

                    {/* CONTROL PANEL */}
                    <div className="glass-panel" style={{ maxWidth: '600px', margin: '3rem auto', textAlign: 'left' }}>
                        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '1px solid var(--border-light)' }}>
                            <button
                                onClick={() => setActiveTab('track')}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    padding: '1rem',
                                    color: activeTab === 'track' ? 'var(--text-primary)' : 'var(--text-secondary)',
                                    borderBottom: activeTab === 'track' ? '2px solid var(--primary)' : 'none',
                                    cursor: 'pointer',
                                    fontWeight: 600
                                }}
                            >
                                Track Results
                            </button>
                            <button
                                onClick={() => setActiveTab('new')}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    padding: '1rem',
                                    color: activeTab === 'new' ? 'var(--text-primary)' : 'var(--text-secondary)',
                                    borderBottom: activeTab === 'new' ? '2px solid var(--primary)' : 'none',
                                    cursor: 'pointer',
                                    fontWeight: 600
                                }}
                            >
                                New Scan
                            </button>
                        </div>

                        {error && (
                            <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', borderRadius: '8px', marginBottom: '1rem' }}>
                                {error}
                            </div>
                        )}

                        {activeTab === 'new' ? (
                            <form onSubmit={handleStart} style={{ display: 'flex', gap: '1rem', flexDirection: 'column' }}>
                                <label style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Target URL</label>
                                <input
                                    type="url"
                                    required
                                    placeholder="https://example.com"
                                    className="input-field"
                                    value={targetUrl}
                                    onChange={(e) => setTargetUrl(e.target.value)}
                                />
                                <button type="submit" disabled={loading} className="btn btn-primary">
                                    {loading ? 'Initializing...' : 'Launch Agent'}
                                </button>
                            </form>
                        ) : (
                            <form onSubmit={handleTrack} style={{ display: 'flex', gap: '1rem', flexDirection: 'column' }}>
                                <label style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Scan ID</label>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <input
                                        type="text"
                                        required
                                        placeholder="Enter UUID..."
                                        className="input-field"
                                        value={scanId}
                                        onChange={(e) => setScanId(e.target.value)}
                                    />
                                    <button type="submit" disabled={loading} className="btn btn-primary">
                                        {loading ? 'Fetching...' : 'Check Status'}
                                    </button>
                                </div>
                            </form>
                        )}

                        {status && (
                            <div style={{ marginTop: '2rem', padding: '1rem', background: 'var(--bg-card)', borderRadius: '12px', border: '1px solid var(--border-light)' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                    <span style={{ color: 'var(--text-secondary)' }}>Status</span>
                                    <span style={{
                                        padding: '0.25rem 0.75rem',
                                        borderRadius: '20px',
                                        background: status === 'COMPLETED' ? 'var(--success)' : 'var(--warning)',
                                        color: '#000',
                                        fontWeight: 700,
                                        fontSize: '0.8rem'
                                    }}>
                                        {status}
                                    </span>
                                </div>

                                {summary && (
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                                        <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                                            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{summary.statistics.urls}</div>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>URLs Found</div>
                                        </div>
                                        <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                                            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{summary.statistics.network_requests}</div>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Requests</div>
                                        </div>
                                        <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                                            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{summary.statistics.forms}</div>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Forms</div>
                                        </div>
                                        <div style={{ textAlign: 'center', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                                            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{summary.statistics.js_files}</div>
                                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>JS Files</div>
                                        </div>
                                    </div>
                                )}

                                {status === 'COMPLETED' && (
                                    <div style={{ display: 'grid', gap: '0.5rem' }}>
                                        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Download Reports</p>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                                            <button onClick={() => handleDownload('json')} className="btn btn-secondary">JSON</button>
                                            <button onClick={() => handleDownload('markdown')} className="btn btn-secondary">Markdown</button>
                                            <button onClick={() => handleDownload('csv')} className="btn btn-secondary">CSV</button>
                                            <button onClick={() => handleDownload('burp')} className="btn btn-secondary">Burp XML</button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </section>

            <BackendInfo />

            <footer style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-light)' }}>
                <p>&copy; 2024 WSRA Security. All systems operational.</p>
            </footer>
        </>
    );
};

export default Landing;
