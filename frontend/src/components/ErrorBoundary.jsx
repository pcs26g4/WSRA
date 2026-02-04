import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#030712] text-white flex flex-col items-center justify-center p-6 text-center">
          <div className="p-4 rounded-full bg-cyan-500/10 border border-cyan-500/20 mb-6">
            <RefreshCw className="w-12 h-12 text-cyan-500 animate-spin-slow" />
          </div>
          <h1 className="text-3xl font-bold mb-4 font-mono">Connection Interrupted</h1>
          <p className="text-gray-400 max-w-md mb-8">
            The agent interface needs a quick refresh to realign with the network.
          </p>
          
          {this.state.error && (
            <div className="bg-black/50 p-4 rounded-lg border border-white/10 text-left w-full max-w-lg mb-8 overflow-auto max-h-48 opacity-50 hover:opacity-100 transition-opacity">
               <span className="text-xs text-uppercase text-gray-500 block mb-1">Diagnostic Code</span>
               <code className="text-xs text-red-300 font-mono">
                 {this.state.error.toString()}
               </code>
            </div>
          )}

          <button 
            onClick={() => window.location.reload()}
            className="flex items-center gap-2 px-6 py-3 bg-white text-black font-bold rounded-full hover:bg-gray-200 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Reconnect Agent
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
