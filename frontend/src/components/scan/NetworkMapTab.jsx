import React from 'react';
import { motion } from 'framer-motion';
import { GitBranch, Globe, Link as LinkIcon, Server } from 'lucide-react';

const Node = ({ label, type, delay }) => (
    <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 20, delay }}
        className="flex flex-col items-center gap-2"
    >
        <div className="w-12 h-12 rounded-full bg-white/10 border border-white/20 flex items-center justify-center shadow-xl backdrop-blur-sm z-10 relative">
             {type === 'root' ? <Globe className="w-6 h-6 text-blue-400" /> : 
              type === 'api' ? <Server className="w-6 h-6 text-purple-400" /> :
              <LinkIcon className="w-6 h-6 text-gray-400" />}
             
             {/* Pulse effect for root */}
             {type === 'root' && <div className="absolute inset-0 bg-blue-500/20 rounded-full animate-ping" />}
        </div>
        <span className="text-xs font-mono bg-black/50 px-2 py-1 rounded max-w-[120px] truncate">
            {label}
        </span>
    </motion.div>
);

const NetworkMapTab = ({ data }) => {
    // Determine unique paths
    const paths = data.endpoints.map(e => new URL(e.url).pathname);
    const uniquePaths = [...new Set(paths)].slice(0, 15); // Limit for visual clarity
    
    // Group roughly by "depth"
    const root = data.target;

    return (
        <div className="h-[500px] w-full bg-black/20 rounded-2xl border border-white/10 relative overflow-hidden flex items-center justify-center p-10">
             {/* Background Grid */}
             <div className="absolute inset-0 opacity-20" 
                  style={{ backgroundImage: 'radial-gradient(circle, #444 1px, transparent 1px)', backgroundSize: '20px 20px' }} 
             />

             <div className="relative z-10 flex flex-col items-center gap-16 w-full">
                  {/* Root Node */}
                  <div className="relative">
                      <Node label={root} type="root" delay={0} />
                      {/* Connecting lines container */}
                      <svg className="absolute top-12 left-1/2 -translate-x-1/2 w-[800px] h-16 pointer-events-none overflow-visible">
                           {uniquePaths.map((_, i) => {
                               const x = (i - uniquePaths.length / 2 + 0.5) * 60;
                               return (
                                   <motion.path
                                       key={i}
                                       initial={{ pathLength: 0 }}
                                       animate={{ pathLength: 1 }}
                                       transition={{ delay: 0.5 + i * 0.05, duration: 0.5 }}
                                       d={`M 400 0 C 400 30, ${400 + x} 30, ${400 + x} 60`}
                                       fill="none"
                                       stroke="rgba(255,255,255,0.2)"
                                       strokeWidth="2"
                                   />
                               );
                           })}
                      </svg>
                  </div>

                  {/* Child Nodes */}
                  <div className="flex flex-wrap justify-center gap-8 w-full max-w-4xl">
                       {uniquePaths.map((path, i) => (
                           <Node 
                               key={i} 
                               label={path} 
                               type={path.startsWith('/api') ? 'api' : 'page'} 
                               delay={0.8 + i * 0.05} 
                           />
                       ))}
                  </div>
             </div>
             
             <div className="absolute bottom-4 right-4 text-xs text-muted-foreground bg-black/50 px-3 py-1 rounded border border-white/10 flex items-center gap-2">
                 <GitBranch className="w-3 h-3" />
                 Visualizing Top 15 Nodes
             </div>
        </div>
    );
};

export default NetworkMapTab;
