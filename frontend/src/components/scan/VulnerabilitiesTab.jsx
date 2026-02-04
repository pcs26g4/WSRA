import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, AlertCircle, AlertTriangle, Info, Terminal, CheckCircle } from 'lucide-react';
import { cn } from '../../lib/utils';

const SeverityBadge = ({ severity }) => {
    const colors = {
        critical: "bg-red-500/10 text-red-500 border-red-500/20",
        high: "bg-orange-500/10 text-orange-500 border-orange-500/20",
        medium: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
        low: "bg-blue-500/10 text-blue-500 border-blue-500/20",
        info: "bg-gray-500/10 text-gray-400 border-gray-500/20"
    };

    return (
        <span className={cn("px-2 py-0.5 rounded text-xs font-mono font-bold border uppercase", colors[severity] || colors.info)}>
            {severity}
        </span>
    );
};

const VulnerabilityCard = ({ vuln, isOpen, onClick }) => {
    return (
        <motion.div 
            layout
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="border border-white/10 bg-card rounded-xl overflow-hidden"
        >
            <div 
                onClick={onClick}
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-4">
                    <div className={cn(
                        "p-2 rounded-lg",
                        vuln.severity === 'critical' ? "bg-red-500/10 text-red-500" :
                        vuln.severity === 'high' ? "bg-orange-500/10 text-orange-500" :
                        "bg-white/5 text-muted-foreground"
                    )}>
                        <AlertTriangle className="w-5 h-5" />
                    </div>
                    <div>
                        <h4 className="font-semibold text-sm">{vuln.type.replace('_', ' ').toUpperCase()}</h4>
                         <p className="text-xs text-muted-foreground truncate max-w-md">{vuln.location}</p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                     <SeverityBadge severity={vuln.severity} />
                     <ChevronDown className={cn("w-4 h-4 transition-transform text-muted-foreground", isOpen && "rotate-180")} />
                </div>
            </div>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="p-4 pt-0 border-t border-white/5 bg-black/20 space-y-4">
                            <div>
                                <h5 className="text-xs font-bold text-muted-foreground uppercase mb-2">Description</h5>
                                <p className="text-sm leading-relaxed">{vuln.description}</p>
                            </div>
                            
                            {vuln.payload && (
                                <div>
                                    <h5 className="text-xs font-bold text-muted-foreground uppercase mb-2">Payload</h5>
                                    <div className="bg-black/40 rounded-lg p-3 font-mono text-xs text-green-400 flex items-start gap-2 overflow-x-auto">
                                        <Terminal className="w-3 h-3 mt-0.5 shrink-0" />
                                        {vuln.payload}
                                    </div>
                                </div>
                            )}

                            <div>
                                <h5 className="text-xs font-bold text-muted-foreground uppercase mb-2">Remediation</h5>
                                <p className="text-sm text-muted-foreground">{vuln.remediation}</p>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

const VulnerabilitiesTab = ({ data }) => {
    const [openId, setOpenId] = useState(null);

    if (!data.vulnerabilities?.length) {
        return (
             <div className="text-center py-20 bg-white/5 rounded-2xl border border-dashed border-white/10">
                 <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                 <h3 className="text-xl font-bold">No Vulnerabilities Found</h3>
                 <p className="text-muted-foreground">Great job! No standard vulnerabilities were detected.</p>
             </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-4">
            {data.vulnerabilities.map((vuln) => (
                <VulnerabilityCard 
                    key={vuln.id} 
                    vuln={vuln} 
                    isOpen={openId === vuln.id}
                    onClick={() => setOpenId(openId === vuln.id ? null : vuln.id)}
                />
            ))}
        </div>
    );
};

export default VulnerabilitiesTab;
