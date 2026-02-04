import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useScroll, useTransform, useMotionValue, useSpring } from 'framer-motion';
import { Shield, Globe, Search, ArrowRight, Activity, Terminal, Lock, Cpu, Eye, Database, Code2 } from 'lucide-react';
import { startScan, getScans } from '../api';
import { cn } from '../lib/utils';

// --- SECTIONS ---

const HeroSection = ({ onStart }) => {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!url) return;
        setLoading(true);
        setError(null);
        try {
            await onStart(url);
        } catch (e) {
            console.error(e);
            setError("Failed to connect to backend. Is it running?");
            setLoading(false);
        }
    };

    return (
        <section className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden pt-20">
            {/* Animated Background Nodes */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-30">
                {[...Array(20)].map((_, i) => (
                    <motion.div
                        key={i}
                        className="absolute w-1 h-1 bg-cyan-500 rounded-full"
                        initial={{
                            x: Math.random() * window.innerWidth,
                            y: Math.random() * window.innerHeight
                        }}
                        animate={{
                            y: [null, Math.random() * window.innerHeight],
                            opacity: [0, 0.8, 0]
                        }}
                        transition={{
                            duration: Math.random() * 10 + 10,
                            repeat: Infinity,
                            ease: "linear"
                        }}
                    />
                ))}
            </div>

            <div className="container mx-auto px-6 relative z-10 text-center space-y-8">
                {/* Content Wrapper */}
                <div className="animate-in fade-in zoom-in duration-1000">
                    <span className="inline-block px-4 py-1.5 rounded-full border border-cyan-500/30 bg-cyan-950/30 text-cyan-400 text-xs font-mono tracking-widest uppercase mb-6 backdrop-blur-md">
                        System Status: Online
                    </span>
                    <h1 className="text-4xl md:text-7xl font-bold tracking-tighter mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white via-white to-white/40 max-w-4xl mx-auto leading-tight">
                        Web Security Reconnaissance Agent
                    </h1>
                    <p className="text-xl md:text-2xl text-gray-400 max-w-2xl mx-auto font-light leading-relaxed">
                        An autonomous AI that explores, understands, and secures your website.
                    </p>
                </div>

                <motion.form
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3, duration: 0.6 }}
                    onSubmit={handleSubmit}
                    className="w-full max-w-lg mx-auto relative group"
                >
                    <div className="absolute -inset-1 bg-gradient-to-r from-cyan-600 to-purple-600 rounded-2xl blur opacity-30 group-hover:opacity-60 transition duration-500" />
                    <div className="relative bg-[#050a14] border border-white/10 rounded-xl p-2 shadow-2xl backdrop-blur-xl">
                        <div className="flex items-center">
                            <div className="pl-4 pr-3 text-cyan-500">
                                <Terminal className="w-5 h-5" />
                            </div>
                            <input
                                type="url"
                                placeholder="Enter target URL (e.g., https://example.com)..."
                                className="flex-1 bg-transparent border-none text-white focus:ring-0 placeholder:text-gray-600 font-mono text-sm outline-none py-3"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                required
                            />
                            <button
                                type="submit"
                                disabled={loading}
                                className="cursor-pointer bg-cyan-500 hover:bg-cyan-400 text-black px-6 py-3 rounded-lg font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {loading ? (
                                    <span className="animate-pulse">Initializing...</span>
                                ) : (
                                    <>Scan <ArrowRight className="w-4 h-4" /></>
                                )}
                            </button>
                        </div>
                    </div>
                    {/* Error Message Display */}
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="absolute top-full left-0 right-0 mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center font-mono"
                        >
                            Error: {error}
                        </motion.div>
                    )}
                </motion.form>

            </div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-gray-500 text-xs uppercase tracking-widest animate-bounce z-20"
            >
                Scroll to Explore
                <ArrowRight className="w-4 h-4 rotate-90" />
            </motion.div>
        </section>
    );
};

const ThreeDTerminal = () => {
    const x = useMotionValue(0);
    const y = useMotionValue(0);

    const mouseX = useSpring(x, { stiffness: 150, damping: 15 });
    const mouseY = useSpring(y, { stiffness: 150, damping: 15 });

    function handleMouseMove({ currentTarget, clientX, clientY }) {
        const { left, top, width, height } = currentTarget.getBoundingClientRect();
        const xPct = (clientX - left) / width - 0.5;
        const yPct = (clientY - top) / height - 0.5;
        x.set(xPct);
        y.set(yPct);
    }

    function handleMouseLeave() {
        x.set(0);
        y.set(0);
    }

    const rotateX = useTransform(mouseY, [-0.5, 0.5], ["10deg", "-10deg"]);
    const rotateY = useTransform(mouseX, [-0.5, 0.5], ["-10deg", "10deg"]);
    const brightness = useTransform(mouseY, [-0.5, 0.5], [1.2, 0.8]);

    return (
        <motion.div
            style={{
                perspective: 1200,
            }}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="w-full h-[450px] flex items-center justify-center py-4"
        >
            <motion.div
                style={{
                    rotateX,
                    rotateY,
                    filter: `brightness(${brightness})`,
                    transformStyle: "preserve-3d",
                }}
                className="relative w-full h-full bg-[#030014]/90 rounded-2xl border border-cyan-500/20 p-6 font-mono text-xs md:text-sm overflow-hidden flex flex-col shadow-[0_0_50px_rgba(34,211,238,0.1)] backdrop-blur-xl group"
            >
                {/* 3D Glass Reflection */}
                <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" style={{ transform: "translateZ(1px)" }} />

                {/* Header of terminal with 3D depth */}
                <div style={{ transform: "translateZ(20px)" }} className="flex items-center gap-2 mb-6 border-b border-white/5 pb-4">
                    <div className="flex gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500/80 shadow-[0_0_10px_rgba(239,68,68,0.5)]" />
                        <div className="w-3 h-3 rounded-full bg-yellow-500/80 shadow-[0_0_10px_rgba(234,179,8,0.5)]" />
                        <div className="w-3 h-3 rounded-full bg-green-500/80 shadow-[0_0_10px_rgba(34,197,94,0.5)]" />
                    </div>
                    <span className="ml-4 text-cyan-400/80 font-bold tracking-widest">WSRA_INTELLIGENCE_CORE_V2.4</span>
                </div>

                {/* Rolling logs floating in 3D space */}
                <div style={{ transform: "translateZ(50px)" }} className="space-y-4 text-gray-300 font-mono relative z-10">
                    <motion.div
                        animate={{ opacity: [0.4, 1, 0.4] }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className="absolute -left-4 top-0 bottom-0 w-[1px] bg-cyan-500/20"
                    />

                    <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 0.5 }} className="flex gap-3">
                        <span className="text-cyan-400 font-bold">[TARGET_LOCK]</span>
                        <span className="text-white/80 border-b border-dashed border-gray-600">example.com</span>
                    </motion.div>

                    <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 1.2 }} className="flex gap-3 items-center">
                        <span className="text-blue-400 font-bold">[TOPOLOGY]</span>
                        <span className="flex items-center gap-2">
                            Mapping nodes...
                            <span className="inline-block w-20 h-1 bg-gray-800 rounded-full overflow-hidden">
                                <motion.div className="h-full bg-blue-500" animate={{ width: "100%" }} transition={{ duration: 1.5, delay: 1.5 }} />
                            </span>
                            <span className="text-green-400">COMPLETE</span>
                        </span>
                    </motion.div>

                    <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 2.8 }} className="flex gap-3">
                        <span className="text-purple-400 font-bold">[HEURISTICS]</span>
                        <span>Analyzing authentication flow patterns</span>
                    </motion.div>

                    <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 3.5 }} className="flex gap-3 bg-red-500/10 p-2 rounded -ml-2 border-l-2 border-red-500">
                        <span className="text-red-500 font-bold animate-pulse">[THREAT_DETECT]</span>
                        <span className="text-red-200">High Severity: SQL Injection in /api/v1/query</span>
                    </motion.div>

                    <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 4.5 }} className="flex gap-3">
                        <span className="text-yellow-400 font-bold">[COUNTERMEASURE]</span>
                        <span>Generating patch recommendations...</span>
                    </motion.div>

                    <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ delay: 5.5 }} className="flex gap-3 pt-2 items-center text-gray-500">
                        <span className="animate-spin">⟳</span>
                        <span>Awaiting operator command_</span>
                    </motion.div>
                </div>

                {/* Cyber Grid Background inside Terminal */}
                <div style={{ transform: "translateZ(-10px)" }} className="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:20px_20px] pointer-events-none" />
            </motion.div>
        </motion.div>
    );
};

const ProblemSection = () => (
    <section className="py-32 bg-black/20 overflow-hidden">
        <div className="container mx-auto px-6">
            <div className="grid md:grid-cols-2 gap-20 items-center">
                <div className="space-y-6 relative z-10">
                    <h2 className="text-4xl font-bold">Traditional scanners are blind.</h2>
                    <p className="text-lg text-gray-400 leading-relaxed">
                        Modern web applications are dynamic ecosystems. Static scanners treat them like documents, missing the critical logic hidden behind buttons, forms, and JavaScript interactions.
                    </p>
                    <div className="flex gap-4 pt-4">
                        <div className="p-4 rounded-xl border border-white/5 bg-white/5 w-full">
                            <span className="text-red-400 font-mono text-xs uppercase block mb-2">Static Scanner</span>
                            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    whileInView={{ width: "30%" }}
                                    transition={{ duration: 1.5, ease: "easeOut" }}
                                    viewport={{ once: true }}
                                    className="h-full bg-red-400"
                                />
                            </div>
                            <span className="text-xs text-muted-foreground mt-2 block">30% Coverage</span>
                        </div>
                        <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/10 w-full relative overflow-hidden">
                            <div className="absolute inset-0 bg-cyan-500/5 animate-pulse" />
                            <span className="text-cyan-400 font-mono text-xs uppercase block mb-2">WSRA Agent</span>
                            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    whileInView={{ width: "95%" }}
                                    transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
                                    viewport={{ once: true }}
                                    className="h-full bg-cyan-400"
                                />
                            </div>
                            <span className="text-xs text-muted-foreground mt-2 block">Deep Coverage</span>
                        </div>
                    </div>
                </div>

                {/* 3D Moving Terminal Component */}
                <ThreeDTerminal />
            </div>
        </div>
    </section>
);

const PipelineSection = () => {
    const steps = [
        { icon: Activity, label: "Orchestrator", desc: "Mission Control" },
        { icon: Globe, label: "Crawler", desc: "Discovery" },
        { icon: Database, label: "Mapper", desc: "Structure" },
        { icon: Eye, label: "Net Monitor", desc: "Traffic Analysis" },
        { icon: Code2, label: "JS Analyzer", desc: "Code Review" },
        { icon: ArrowRight, label: "Interaction", desc: "Behavior" },
        { icon: Lock, label: "Form Agent", desc: "Auth & Input" },
        { icon: Shield, label: "Vuln Hunter", desc: "Exploitation" },
    ];

    return (
        <section className="py-24 border-y border-white/5 bg-[#030712] overflow-hidden">
            <div className="container mx-auto px-6">
                <h2 className="text-3xl font-bold mb-20 text-center"><span className="text-cyan-400">Autonomous</span> Pipeline</h2>

                <div className="relative">
                    {/* Animated Connection Line (Desktop) */}
                    <div className="absolute top-8 left-0 right-0 h-0.5 bg-gray-800 hidden lg:block">
                        <motion.div
                            className="h-full bg-gradient-to-r from-transparent via-cyan-500 to-transparent w-1/3"
                            animate={{ x: ["-100%", "400%"] }}
                            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                        />
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-8 relative">
                        {steps.map((step, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.1 }}
                                className="relative z-10 flex flex-col items-center text-center gap-3"
                            >
                                <div className="relative">
                                    <div className="w-16 h-16 rounded-2xl bg-[#030712] border border-white/10 flex items-center justify-center text-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.1)] group hover:scale-110 transition-transform duration-300 relative z-20">
                                        <step.icon className="w-6 h-6" />
                                    </div>
                                    {/* Pulse effect behind icon */}
                                    <div className="absolute inset-0 bg-cyan-500/20 blur-xl rounded-full z-10 animate-pulse" />
                                </div>

                                <div className="mt-2">
                                    <h3 className="font-bold text-sm text-white">{step.label}</h3>
                                    <p className="text-xs text-gray-500 font-mono mt-1">{step.desc}</p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>
        </section>
    );
};

const AgentsSection = () => {
    const agents = [
        { name: "Orchestrator", role: "Commander", desc: "I manage the entire reconnaissance mission, coordinating the swarm and deciding the strategic path forward.", color: "text-cyan-400", border: "border-cyan-500/30" },
        { name: "Crawler Agent", role: "Explorer", desc: "I systematically navigate the target, extracting HTML, discovering assets, and mapping the initial attack surface.", color: "text-blue-400", border: "border-blue-500/30" },
        { name: "Mapper Agent", role: "Cartographer", desc: "I construct comprehensive sitemaps and analyze the structural topology to identify high-value targets.", color: "text-emerald-400", border: "border-emerald-500/30" },
        { name: "Interaction Agent", role: "Behaviorist", desc: "I emulate human behavior by interacting with dynamic elements to uncover hidden states and functional logic.", color: "text-purple-400", border: "border-purple-500/30" },
        { name: "Form Agent", role: "Tactician", desc: "I analyze and bypass authentication mechanisms and handle complex input requirements to breach gated areas.", color: "text-pink-400", border: "border-pink-500/30" },
        { name: "JS Analyzer", role: "Analyst", desc: "I deconstruct client-side code to extract hardcoded secrets, hidden API endpoints, and sensitive logic.", color: "text-yellow-400", border: "border-yellow-500/30" },
        { name: "Network Monitor", role: "Watcher", desc: "I intercept and analyze real-time network traffic to detect API leaks, unencrypted data, and sensitive headers.", color: "text-orange-400", border: "border-orange-500/30" },
        { name: "Vuln Hunter", role: "Attacker", desc: "I autonomously identify security flaws like XSS and SQLi by analyzing response patterns and anomalies.", color: "text-red-400", border: "border-red-500/30" },
    ];

    return (
        <section className="py-32 container mx-auto px-6">
            <div className="text-center mb-16">
                <h2 className="text-4xl font-bold mb-4">The Agents</h2>
                <p className="text-gray-400">A cooperative swarm of specialized intelligences.</p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                {agents.map((agent, i) => (
                    <motion.div
                        key={i}
                        initial={{ opacity: 0, scale: 0.9 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: i * 0.1 }}
                        className={`p-6 rounded-3xl bg-white/5 backdrop-blur-sm border ${agent.border} hover:bg-white/10 transition-colors flex flex-col`}
                    >
                        <div className="mb-4">
                            <span className={`text-xs font-mono uppercase tracking-wider ${agent.color}`}>{agent.role}</span>
                            <h3 className="text-xl font-bold mt-1">{agent.name}</h3>
                        </div>
                        <p className="text-sm leading-relaxed text-gray-300 mt-auto">"{agent.desc}"</p>
                    </motion.div>
                ))}
            </div>
        </section>
    );
};

const Dashboard = () => {
    const navigate = useNavigate();

    const handleStart = async (url) => {
        try {
            const response = await startScan(url);
            navigate(`/scan/${response.scan_id}`);
        } catch (error) {
            console.error("Failed to start scan", error);
            // Ideally show toast
        }
    };

    return (
        <div className="text-foreground">
            <HeroSection onStart={handleStart} />
            <ProblemSection />
            <PipelineSection />
            <AgentsSection />

            <section className="py-24 text-center">
                <div className="container mx-auto px-6">
                    <h2 className="text-3xl font-bold mb-8">Ready to secure your infrastructure?</h2>
                    <button
                        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                        className="bg-white text-black px-8 py-4 rounded-full font-bold hover:bg-gray-200 transition-colors cursor-pointer"
                    >
                        Start Autonomous Scan
                    </button>
                </div>
            </section>

            <footer className="py-12 border-t border-white/5 text-center text-gray-600 text-sm">
                <p>© 2026 WSRA. All systems nominal.</p>
            </footer>
        </div>
    );
};

export default Dashboard;
