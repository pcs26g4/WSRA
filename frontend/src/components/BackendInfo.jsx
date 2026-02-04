import React from 'react';

const BackendInfo = () => {
    return (
        <section id="backend" style={{ padding: '6rem 0' }}>
            <div className="container">
                <h2 style={{ textAlign: 'center' }}>Powered by Advanced Agentic AI</h2>
                <p style={{ textAlign: 'center', maxWidth: '600px', margin: '0 auto 4rem auto' }}>
                    What's running in the background? A sophisticated orchestration of autonomous agents working in harmony.
                </p>

                <div className="grid-cols-2" style={{ gap: '3rem' }}>
                    <div className="glass-panel">
                        <h3 style={{ color: 'var(--primary)' }}>Orchestrator</h3>
                        <p>The central brain that manages the lifecycle of every scan. It assigns tasks to specialized agents and compiles the results in real-time.</p>
                    </div>

                    <div style={{ display: 'grid', gap: '1.5rem' }}>
                        <div className="glass-card">
                            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ width: '10px', height: '10px', background: 'var(--accent)', borderRadius: '50%' }}></span>
                                Crawler Agent
                            </h4>
                            <p style={{ fontSize: '0.9rem' }}>Maps the target application, discovering URLs, assets, and entry points.</p>
                        </div>
                        <div className="glass-card">
                            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ width: '10px', height: '10px', background: 'var(--secondary)', borderRadius: '50%' }}></span>
                                Interaction Agent
                            </h4>
                            <p style={{ fontSize: '0.9rem' }}>Simulates user behavior, filling forms and triggering dynamic content.</p>
                        </div>
                        <div className="glass-card">
                            <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ width: '10px', height: '10px', background: 'var(--success)', borderRadius: '50%' }}></span>
                                Analysis Agent
                            </h4>
                            <p style={{ fontSize: '0.9rem' }}>Identifies vulnerabilities and security risks using the collected data.</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default BackendInfo;
