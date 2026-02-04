import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { deleteScan, getScans} from '../api';
import { motion } from 'framer-motion';
import { Shield, Clock, Globe, ArrowRight, Loader2, Trash2 } from 'lucide-react';
import { cn } from '../lib/utils';

const History = () => {
    const [scans, setScans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        const loadScans = async () => {
            try {
                const data = await getScans(100);
                setScans(data);
                setError(null);
            } catch (error) {
                console.error("Failed to load history", error);
                setError("Failed to connect to the backend server. Please ensure the backend is running.");
            } finally {
                setLoading(false);
            }
        };
        loadScans();
    }, []);

    const handleDelete = async (e, id) => {
        e.stopPropagation(); // Prevent navigation
        if (!window.confirm("Are you sure you want to permanently delete this scan?")) return;

        // Optimistic update: Remove immediately from UI
        const previousScans = [...scans];
        setScans(prev => prev.filter(s => s.scan_id !== id));

        try {
            await deleteScan(id);
            console.log("Scan deleted successfully", id);
        } catch (error) {
            // Rollback on failure
            setScans(previousScans);
            const msg = error.response?.data?.detail || error.message || "Failed to delete scan";
            alert(`Error: ${msg}`);
            console.error(error);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-8 max-w-5xl mx-auto pt-24 pb-20 px-6">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Scan History</h1>
                <p className="text-muted-foreground">Archive of previous security operations.</p>
            </div>

            {error && (
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-3">
                    <Shield className="w-5 h-5" />
                    <p>{error}</p>
                </div>
            )}

            <div className="grid gap-4">
                {scans.length === 0 ? (
                    <div className="p-12 text-center border border-dashed border-white/10 rounded-xl bg-white/5">
                        <p className="text-muted-foreground">No scan history available.</p>
                    </div>
                ) : (
                    scans.map((scan, i) => (
                        <motion.div
                            key={scan.scan_id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            onClick={() => navigate(`/scan/${scan.scan_id}`)}
                            className="group relative p-4 rounded-xl bg-card border border-white/5 hover:border-primary/50 cursor-pointer transition-all flex items-center justify-between overflow-hidden"
                        >
                            <div className="flex items-center gap-6">
                                <div className={cn(
                                    "w-12 h-12 rounded-lg flex items-center justify-center",
                                    scan.status === 'COMPLETED' ? "bg-green-500/10 text-green-500" :
                                        scan.status === 'FAILED' ? "bg-red-500/10 text-red-500" :
                                            "bg-blue-500/10 text-blue-500 animate-pulse"
                                )}>
                                    <Shield className="w-6 h-6" />
                                </div>
                                <div className="space-y-1">
                                    <div className="flex items-center gap-3">
                                        <h3 className="font-semibold text-lg">{scan.target || 'Unknown Target'}</h3>
                                        <span className={cn(
                                            "px-2 py-0.5 rounded text-xs font-mono border uppercase",
                                            scan.status === 'COMPLETED' ? "border-green-500/20 text-green-500" :
                                                "border-white/10 text-muted-foreground"
                                        )}>
                                            {scan.status}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                        <span className="flex items-center gap-1 font-mono">
                                            <Globe className="w-3 h-3" />
                                            {scan.scan_id.substring(0, 8)}...
                                        </span>
                                        {scan.created_at && (
                                            <span className="flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {new Date(scan.created_at).toLocaleString()}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-4">
                                <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:-translate-x-12 transition-all duration-300" />
                            </div>

                            <div
                                className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-all duration-300 z-10"
                                onClick={(e) => handleDelete(e, scan.scan_id)}
                            >
                                <div className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-lg backdrop-blur-sm border border-red-500/20 shadow-lg">
                                    <Trash2 className="w-4 h-4" />
                                </div>
                            </div>
                        </motion.div>
                    ))
                )}
            </div>
        </div>
    );
};

export default History;
