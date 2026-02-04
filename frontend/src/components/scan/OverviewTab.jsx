import React from 'react';
import { motion } from 'framer-motion';
import {
    AlertTriangle, Globe, FileCode, CheckCircle,
    Link, Activity, Server, Users
} from 'lucide-react';
import { cn } from '../../lib/utils';

const StatCard = ({ icon: Icon, label, value, color, delay }) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay }}
        className={cn("p-6 rounded-xl bg-white/5 border hover:bg-white/10 transition-colors backdrop-blur-sm", color.includes('border') ? color.split(' ').find(c => c.startsWith('border')) : 'border-white/5')}
    >
        <div className="flex items-center justify-between mb-4">
            <div className={cn("p-2 rounded-lg", color)}>
                <Icon className="w-5 h-5" />
            </div>
            {/* Sparkline placeholder */}
            <Activity className="w-4 h-4 text-muted-foreground opacity-20" />
        </div>
        <div className="space-y-1">
            <h3 className="text-3xl font-bold font-mono">{value}</h3>
            <p className="text-sm text-muted-foreground">{label}</p>
        </div>
    </motion.div>
);

const OverviewTab = ({ data }) => {
    if (!data) return null;

    const stats = data.statistics || {};
    // Handle both new (total_*) and old keys for robustness, defaulting to 0
    const safeStats = {
        total_urls: stats.total_urls || stats.urls || 0,
        total_js_files: stats.total_js_files || stats.js_files || 0,
        total_endpoints: stats.total_endpoints || stats.endpoints?.length || 0
    };

    const vulnerabilities = data.vulnerabilities || [];
    const severity = vulnerabilities.reduce((acc, v) => {
        acc[v.severity] = (acc[v.severity] || 0) + 1;
        return acc;
    }, {});

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                    icon={Globe} label="Pages Crawled"
                    value={safeStats.total_urls} color="text-cyan-400 border-cyan-500/20 bg-cyan-950/10" delay={0}
                />
                <StatCard
                    icon={FileCode} label="JS Files"
                    value={safeStats.total_js_files} color="text-purple-400 border-purple-500/20 bg-purple-950/10" delay={0.1}
                />
                <StatCard
                    icon={Link} label="Endpoints"
                    value={safeStats.total_endpoints} color="text-blue-400 border-blue-500/20 bg-blue-950/10" delay={0.2}
                />
                <StatCard
                    icon={AlertTriangle} label="Issues Found"
                    value={vulnerabilities.length} color="text-red-400 border-red-500/20 bg-red-950/10" delay={0.3}
                />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Severity Distribution */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="p-6 rounded-2xl bg-card border border-white/10"
                >
                    <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-primary" />
                        Risk Distribution
                    </h3>
                    <div className="space-y-4">
                        {['critical', 'high', 'medium', 'low', 'info'].map((sev) => {
                            const count = severity[sev] || 0;
                            const total = vulnerabilities.length || 1;
                            const percent = (count / total) * 100;

                            const colorMap = {
                                critical: 'bg-red-600',
                                high: 'bg-orange-500',
                                medium: 'bg-yellow-500',
                                low: 'bg-blue-500',
                                info: 'bg-gray-500'
                            };

                            return (
                                <div key={sev} className="space-y-1">
                                    <div className="flex justify-between text-sm">
                                        <span className="capitalize text-muted-foreground">{sev}</span>
                                        <span className="font-mono">{count}</span>
                                    </div>
                                    <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${percent}%` }}
                                            transition={{ duration: 1, delay: 0.5 }}
                                            className={cn("h-full", colorMap[sev])}
                                        />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </motion.div>

                {/* Features Detected */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="p-6 rounded-2xl bg-card border border-white/10"
                >
                    <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                        <Server className="w-4 h-4 text-primary" />
                        Detected Features
                    </h3>
                    <div className="flex flex-wrap gap-2">
                        {(data.features || []).map((feature, i) => (
                            <span key={i} className="px-3 py-1 text-sm bg-white/5 border border-white/10 rounded-lg flex items-center gap-2">
                                <CheckCircle className="w-3 h-3 text-green-500" />
                                {feature.name}
                            </span>
                        ))}
                        {(data.features || []).length === 0 && (
                            <p className="text-muted-foreground text-sm">No specific features identified.</p>
                        )}
                    </div>
                </motion.div>
            </div>
        </div>
    );
};

export default OverviewTab;
