import React from 'react';
import Navbar from './Navbar';

const AppShell = ({ children }) => {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-cyan-500/20 selection:text-cyan-200">
      <div className="fixed inset-0 bg-[#030712] -z-50" />
      {/* Vibrant cosmic gradient */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/40 via-[#030712] to-[#030712] -z-40 pointer-events-none" />
      <div className="fixed inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 -z-30 pointer-events-none mix-blend-soft-light" />
      
      <Navbar />
      <main className="relative pt-0 pb-0">
        {children}
      </main>
    </div>
  );
};

export default AppShell;
