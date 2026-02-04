import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, LayoutDashboard, History, Settings } from 'lucide-react';
import { cn } from '../../lib/utils';
import { motion } from 'framer-motion';

const Navbar = () => {
  const location = useLocation();

  const navItems = [
    { name: 'Home', path: '/', icon: LayoutDashboard },
    { name: 'Intelligence Vault', path: '/history', icon: History },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 transition-all duration-300 pointer-events-none">
      <div className="container mx-auto px-6 h-24 flex items-center justify-between pointer-events-auto">
        {/* Logo Area */}
        <div className="flex items-center gap-3">
          <div className="relative group">
            <div className="absolute -inset-1 bg-cyan-500/50 rounded-full blur opacity-25 group-hover:opacity-75 transition duration-500" />
            <div className="relative w-10 h-10 bg-black/50 border border-white/10 rounded-full flex items-center justify-center backdrop-blur-xl">
              <Shield className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <span className="font-bold text-lg tracking-wider font-mono text-white/90">
            WSRA
          </span>
        </div>

        {/* Links */}
        <div className="hidden md:flex items-center gap-1 bg-white/5 border border-white/10 rounded-full p-1 backdrop-blur-md shadow-2xl">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "relative flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium transition-all duration-300",
                  isActive ? "text-cyan-300 bg-white/10 shadow-[0_0_15px_rgba(6,182,212,0.1)]" : "text-gray-400 hover:text-white hover:bg-white/5"
                )}
              >
                {item.name}
              </Link>
            );
          })}
        </div>

        <div className="w-10"></div> {/* Spacer for balance */}
      </div>
    </nav>
  );
};

export default Navbar;
