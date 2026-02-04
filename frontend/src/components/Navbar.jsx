import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, Activity, History, Menu } from 'lucide-react';
import { cn } from '../lib/utils';

const Navbar = () => {
    const location = useLocation();

    const links = [
        { href: '/', label: 'Mission Control', icon: Activity },
        { href: '/history', label: 'Scan History', icon: History },
    ];

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-[#030014]/80 backdrop-blur-md">
            <div className="container mx-auto px-6 h-16 flex items-center justify-between">
                <Link to="/" className="flex items-center gap-3 group">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
                        <Shield className="w-6 h-6" />
                    </div>
                    <div className="flex flex-col">
                        <span className="font-bold text-lg leading-none tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/90">
                            WSRA
                        </span>
                        <span className="text-[0.65rem] font-medium tracking-widest text-cyan-400 uppercase">
                            Web Security Reconnaissance Agent
                        </span>
                    </div>
                </Link>

                <div className="flex items-center gap-1">
                    {links.map((link) => {
                        const Icon = link.icon;
                        const isActive = location.pathname === link.href;

                        return (
                            <Link
                                key={link.href}
                                to={link.href}
                                className={cn(
                                    "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
                                    isActive
                                        ? "bg-white/10 text-white shadow-[0_0_10px_rgba(255,255,255,0.1)]"
                                        : "text-gray-400 hover:text-white hover:bg-white/5"
                                )}
                            >
                                <Icon className="w-4 h-4" />
                                {link.label}
                            </Link>
                        );
                    })}
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
