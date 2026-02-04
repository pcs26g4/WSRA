import React from 'react';
import { FileCode, Link, Database, LayoutTemplate } from 'lucide-react';

const Section = ({ title, icon: Icon, children }) => (
    <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
            <Icon className="w-5 h-5 text-primary" />
            {title}
        </h3>
        {children}
    </div>
);

const AttackSurfaceTab = ({ data }) => {
    return (
        <div className="grid md:grid-cols-2 gap-8">
             {/* Endpoints */}
             <Section title="Discovered Endpoints" icon={Link}>
                 <div className="bg-card border border-white/10 rounded-xl overflow-hidden">
                      <div className="max-h-96 overflow-y-auto">
                           <table className="w-full text-sm text-left">
                               <thead className="text-xs uppercase bg-white/5 text-muted-foreground sticky top-0 backdrop-blur-md">
                                   <tr>
                                       <th className="px-4 py-3">Method</th>
                                       <th className="px-4 py-3">URL Path</th>
                                       <th className="px-4 py-3">Status</th>
                                   </tr>
                               </thead>
                               <tbody className="divide-y divide-white/5">
                                   {data.endpoints.map((ep, i) => (
                                        <tr key={i} className="hover:bg-white/5">
                                            <td className="px-4 py-2 font-mono text-xs">
                                                <span className={ep.method === 'POST' ? 'text-blue-400' : 'text-green-400'}>
                                                    {ep.method}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 truncate max-w-xs" title={ep.url}>{new URL(ep.url).pathname}</td>
                                            <td className="px-4 py-2">
                                                <span className={ep.status_code >= 400 ? 'text-red-400' : 'text-muted-foreground'}>
                                                    {ep.status_code || '-'}
                                                </span>
                                            </td>
                                        </tr>
                                   ))}
                               </tbody>
                           </table>
                      </div>
                 </div>
             </Section>

             <div className="space-y-8">
                 {/* JS Files */}
                 <Section title="JavaScript Files" icon={FileCode}>
                     <div className="bg-card border border-white/10 rounded-xl p-4 max-h-64 overflow-y-auto space-y-2">
                          {data.js_files.map((js, i) => (
                               <div key={i} className="flex justify-between items-center text-sm p-2 rounded hover:bg-white/5">
                                   <div className="truncate max-w-[70%]">
                                       <p className="truncate" title={js.url}>{js.url.split('/').pop()}</p>
                                   </div>
                                    <span className={
                                        js.risk_level === 'High' ? "text-red-500 text-xs font-bold" : 
                                        js.risk_level === 'Medium' ? "text-yellow-500 text-xs" : 
                                        "text-muted-foreground text-xs"
                                    }>{js.risk_level} Risk</span>
                               </div>
                          ))}
                     </div>
                 </Section>

                 {/* Forms */}
                 <Section title="Forms & Inputs" icon={LayoutTemplate}>
                     <div className="bg-card border border-white/10 rounded-xl p-4 max-h-64 overflow-y-auto space-y-2">
                          {data.forms.map((form, i) => (
                               <div key={i} className="flex justify-between items-center text-sm p-2 rounded hover:bg-white/5">
                                   <div className="truncate">
                                       <p className="font-mono text-xs">{new URL(form.url).pathname}</p>
                                   </div>
                                    <span className="text-xs text-muted-foreground">{form.field_count} Fields</span>
                               </div>
                          ))}
                     </div>
                 </Section>
             </div>
        </div>
    );
};

export default AttackSurfaceTab;
