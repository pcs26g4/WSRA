import React from 'react';
import { Terminal, Copy, Check } from 'lucide-react';
import { motion } from 'framer-motion';

const CodeBlock = ({ label, code }) => {
    const [copied, setCopied] = React.useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="mt-4 first:mt-0 bg-black/40 rounded-xl border border-white/10 overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/5">
                <span className="text-xs font-mono text-muted-foreground">{label}</span>
                <button onClick={copyToClipboard} className="text-muted-foreground hover:text-white transition-colors">
                    {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                </button>
            </div>
            <div className="p-4 overflow-x-auto">
                <pre className="font-mono text-xs text-blue-300 whitespace-pre-wrap break-all">{code}</pre>
            </div>
        </div>
    );
};

const ManualValidationTab = ({ data }) => {
    if (!data.manual_testing?.length) {
        return (
            <div className="text-center py-12">
                <p className="text-muted-foreground">No manual validation steps generated for this scan.</p>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {data.manual_testing.map((test, index) => (
                <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="p-6 bg-card border border-white/10 rounded-xl flex flex-col h-full"
                >
                    <div className="flex items-center justify-between mb-4">
                        <h4 className="font-bold">{test.type}</h4>
                        <span className="px-2 py-0.5 rounded text-xs font-mono bg-white/5 border border-white/10 uppercase">
                            {test.priority}
                        </span>
                    </div>
                    
                    <div className="flex-1 space-y-2">
                         <p className="text-sm text-muted-foreground">
                             Expected Result: <span className="text-white">{test.expected_result}</span>
                         </p>
                         
                         <CodeBlock 
                             label="Test Payload / Command" 
                             code={`curl -X POST "${test.endpoint}" -d "${test.payload}"`} 
                         />
                    </div>
                </motion.div>
            ))}
        </div>
    );
};

export default ManualValidationTab;
