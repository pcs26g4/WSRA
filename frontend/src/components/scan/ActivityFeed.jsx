import React, { useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Cpu, Clock, Activity } from 'lucide-react';
import { cn } from '../../lib/utils';

const ActivityFeed = ({ logs }) => {
    const scrollRef = useRef(null);

    // Sort logs by timestamp ASC (Oldest -> Newest) for "Terminal Flow"
    const sortedLogs = useMemo(() => {
        if (!logs) return [];
        return [...logs].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    }, [logs]);

    // Auto-scroll to bottom on new logs
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: 'smooth'
            });
        }
    }, [sortedLogs]);

    if (!logs || logs.length === 0) return (
        <div className="flex flex-col items-center justify-center p-12 text-muted-foreground border border-dashed border-white/5 rounded-2xl bg-white/2">
            <Activity className="w-8 h-8 mb-4 opacity-20" />
            <p className="text-sm font-mono tracking-wider">AWAITING AGENT TELEMETRY...</p>
        </div>
    );

    return (
        <div className="bg-[#0a0a0c] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-white/[0.02]">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-500">
                        <Terminal className="w-4 h-4" />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-white tracking-wide uppercase">Live Intelligence Feed</h3>
                        <p className="text-[10px] text-cyan-500/50 font-mono">ENCRYPTED TELEMETRY STREAM</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[10px] font-mono text-green-500 uppercase tracking-tighter">Live Connection</span>
                </div>
            </div>

            {/* Logs Area */}
            <div
                ref={scrollRef}
                className="p-4 h-[400px] overflow-y-auto font-mono scrollbar-thin scrollbar-thumb-white/10"
            >
                <div className="space-y-3">
                    <AnimatePresence initial={false}>
                        {sortedLogs.map((log, i) => (
                            <motion.div
                                key={log.id || i}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="flex gap-4 group"
                            >
                                <span className="text-muted-foreground/30 text-[10px] mt-1 shrink-0">
                                    {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                </span>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <span className={cn(
                                            "text-[10px] px-1.5 py-0.5 rounded border leading-none uppercase font-bold",
                                            log.agent === 'Orchestrator' ? "bg-purple-500/10 text-purple-400 border-purple-500/20" :
                                                log.agent === 'CrawlAgent' ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                                                    log.agent === 'InteractionAgent' ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                                                        "bg-cyan-500/10 text-cyan-400 border-cyan-500/20"
                                        )}>
                                            {log.agent}
                                        </span>
                                        <span className="text-white/80 text-xs tracking-tight">{log.message}</span>
                                    </div>
                                    {log.action === 'vuln_found' && (
                                        <div className="ml-0 p-2 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-[11px] animate-pulse">
                                            CRITICALFinding: Potential security risk detected.
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </div>

            {/* Footer Statistics */}
            <div className="px-6 py-3 border-t border-white/5 bg-white/[0.01] flex justify-between items-center text-[10px] text-muted-foreground font-mono">
                <span>BUFFER: {sortedLogs.length} EVENTS</span>
                <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    LAST UPDATE: {new Date().toLocaleTimeString()}
                </span>
            </div>
        </div>
    );
};

export default ActivityFeed;
