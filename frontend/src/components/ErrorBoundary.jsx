import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="glass-panel rounded-2xl p-8 border border-red-500/30 text-center space-y-4 my-4 bg-cyber-bg/90 backdrop-blur-md">
          <div className="flex justify-center">
            <div className="p-3 bg-red-500/10 rounded-full border border-red-500/30 text-red-500 animate-pulse">
              <AlertTriangle className="w-8 h-8" />
            </div>
          </div>
          <h3 className="font-orbitron text-sm font-bold text-white uppercase tracking-wider">
            Rendering Exception Captured
          </h3>
          <p className="text-xs text-cyber-gray leading-relaxed max-w-md mx-auto font-mono">
            {this.state.error?.message || "An unexpected error occurred in this view module."}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              if (this.props.onReset) this.props.onReset();
            }}
            className="flex items-center gap-1.5 mx-auto px-4 py-2 bg-red-500/20 border border-red-500/40 rounded-lg text-xs font-semibold hover:bg-red-500/30 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> RESET VIEWPORT
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
