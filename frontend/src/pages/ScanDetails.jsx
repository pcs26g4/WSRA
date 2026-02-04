import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getScanStatus, exportScan, getScanSummary } from '../api';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Shield, Globe, AlertTriangle, FileCode, Database,
    Terminal, ChevronDown, CheckCircle, Clock, Loader2,
    GitBranch
} from 'lucide-react';
import { cn } from '../lib/utils';
import OverviewTab from '../components/scan/OverviewTab';
import VulnerabilitiesTab from '../components/scan/VulnerabilitiesTab';
import AttackSurfaceTab from '../components/scan/AttackSurfaceTab';
import ManualValidationTab from '../components/scan/ManualValidationTab';
import NetworkMapTab from '../components/scan/NetworkMapTab';
import ActivityFeed from '../components/scan/ActivityFeed';

const TABS = [
    { id: 'overview', label: 'Overview', icon: Globe },
    { id: 'network', label: 'Network Map', icon: GitBranch },
    { id: 'vulns', label: 'Vulnerabilities', icon: Shield },
    { id: 'surface', label: 'Attack Surface', icon: Database },
    { id: 'manual', label: 'Manual Validation', icon: Terminal },
];

const ScanDetails = () => {
    const { id } = useParams();
    const [status, setStatus] = useState('LOADING');
    const [scanData, setScanData] = useState(null);
    const [activeTab, setActiveTab] = useState('overview');
    const [loadingData, setLoadingData] = useState(false);

    const [fetchError, setFetchError] = useState(null);

    useEffect(() => {
        let poll;
        const checkStatus = async () => {
            try {
                const s = await getScanStatus(id);
                if (s.status !== status) setStatus(s.status);

                // Fetch new summary data every poll
                // This allows the dashboard to update LIVE while the scan is running
                if (s.status === 'RUNNING' || s.status === 'COMPLETED') {
                    try {
                        const data = await getScanSummary(id);
                        setScanData(data);
                    } catch (e) {
                        console.error("Failed to fetch scan summary during poll", e);
                    }
                }

                if (s.status === 'COMPLETED' || s.status === 'FAILED') {
                    clearInterval(poll);
                }
            } catch (e) {
                console.error(e);
            }
        };

        checkStatus();
        poll = setInterval(checkStatus, 3000);
        return () => clearInterval(poll);
    }, [id, status]); // Removed scanData and loadingData from deps to avoid loop

    return (
        <div className="space-y-8 pb-20 pt-24 max-w-[1600px] mx-auto px-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-card border border-white/10 rounded-2xl relative overflow-hidden">
                <div className="space-y-2 relative z-10">
                    <div className="flex items-center gap-3">
                        <h1 className="text-3xl font-bold tracking-tight">Scan Report</h1>
                        <span className={cn(
                            "px-3 py-1 rounded-full text-xs font-mono font-bold border",
                            status === 'COMPLETED' ? "bg-green-500/10 text-green-500 border-green-500/20" :
                                status === 'FAILED' ? "bg-red-500/10 text-red-500 border-red-500/20" :
                                    "bg-blue-500/10 text-blue-500 border-blue-500/20 animate-pulse"
                        )}>
                            {status}
                        </span>
                    </div>
                    <p className="text-muted-foreground font-mono text-sm">{id}</p>
                </div>

                {scanData && (
                    <div className="flex items-center gap-6 text-sm text-muted-foreground relative z-10">
                        <div className="flex items-center gap-2">
                            <Globe className="w-4 h-4" />
                            <span className="text-white">{scanData.target}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <Clock className="w-4 h-4" />
<span>
  {scanData.duration ? (
    <>
      {Math.floor(scanData.duration / 60) > 0 && `${Math.floor(scanData.duration / 60)}m `}
      {`${Math.round(scanData.duration % 60)}s`}
    </>
  ) : (
    'N/A'
  )}
</span>                        </div>
                    </div>
                )}

                {/* Header Actions */}
                {status === 'COMPLETED' && (
                    <div className="flex flex-wrap items-center gap-2 relative z-10 mt-4 md:mt-0">
                        <button onClick={() => window.open(`http://localhost:8000/scan/${id}/export/json`, '_blank')} className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-mono transition-colors cursor-pointer">JSON</button>
                        <button onClick={() => window.open(`http://localhost:8000/scan/${id}/export/markdown`, '_blank')} className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-mono transition-colors cursor-pointer">MD</button>
                        <button onClick={() => window.open(`http://localhost:8000/scan/${id}/export/csv`, '_blank')} className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-mono transition-colors cursor-pointer">CSV</button>
                        <button onClick={() => window.open(`http://localhost:8000/scan/${id}/export/burp`, '_blank')} className="px-3 py-1.5 rounded-lg bg-orange-500/10 hover:bg-orange-500/20 border border-orange-500/30 text-orange-500 text-xs font-mono transition-colors cursor-pointer">Burp XML</button>
                    </div>
                )}

                {/* Background decorative glow */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
            </div>


            {/* Content Area */}
            {fetchError ? (
                <div className="h-96 flex flex-col items-center justify-center space-y-4 border border-dashed border-red-500/20 rounded-2xl bg-red-500/5">
                    <AlertTriangle className="w-10 h-10 text-red-500" />
                    <p className="text-red-400 font-mono">{fetchError}</p>
                    <button onClick={() => window.location.reload()} className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm transition-colors cursor-pointer">
                        Retry Retrieval
                    </button>
                </div>
            ) : !scanData ? (
                <div className="h-96 flex flex-col items-center justify-center space-y-4 border border-dashed border-white/10 rounded-2xl bg-white/5">
                    <Loader2 className="w-10 h-10 text-primary animate-spin" />
                    <p className="text-muted-foreground">Initializing Agents...</p>
                </div>
            ) : (
                <>
                    {/* Live Progress Info (Only while Running) */}
                    {status === 'RUNNING' && (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                            <div className="lg:col-span-2">
                                <ActivityFeed logs={scanData.logs || []} />
                            </div>
                            <div className="bg-card border border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center text-center space-y-4">
                                <div className="p-4 rounded-full bg-primary/10 relative">
                                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                                    <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full" />
                                </div>
                                <div>
                                    <h4 className="text-lg font-bold">Autonomous Work in Progress</h4>
                                    <p className="text-sm text-muted-foreground max-w-[200px] mx-auto">
                                        Agents are currently exploring targets and analyzing vulnerability vectors.
                                    </p>
                                </div>
                                <div className="w-full pt-4 border-t border-white/5">
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-muted-foreground">Agent Efficiency</span>
                                        <span className="text-primary">High</span>
                                    </div>
                                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            animate={{ x: ["-100%", "100%"] }}
                                            transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                                            className="h-full w-1/2 bg-primary/50"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Tabs Navigation */}
                    <div className="flex items-center gap-2 overflow-x-auto pb-2 mb-6 border-b border-white/5 no-scrollbar">
                        {TABS.map((tab) => {
                            const Icon = tab.icon;
                            const isActive = activeTab === tab.id;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={cn(
                                        "relative flex items-center gap-2 px-6 py-3 rounded-full transition-all min-w-max text-sm font-medium",
                                        isActive ? "text-cyan-400 bg-cyan-950/30 border border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.1)]" : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
                                    )}
                                >
                                    <Icon className={cn("w-4 h-4", isActive ? "text-cyan-400" : "text-gray-500")} />
                                    {tab.label}
                                </button>
                            );
                        })}
                    </div>

                    {/* Tab Panels */}
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeTab}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.2 }}
                        >
                            {activeTab === 'overview' && <OverviewTab data={scanData} />}
                            {activeTab === 'network' && <NetworkMapTab data={scanData} />}
                            {activeTab === 'vulns' && <VulnerabilitiesTab data={scanData} />}
                            {activeTab === 'surface' && <AttackSurfaceTab data={scanData} />}
                            {activeTab === 'manual' && <ManualValidationTab data={scanData} />}
                        </motion.div>
                    </AnimatePresence>
                </>
            )}
        </div>
    );
}

export default ScanDetails;
