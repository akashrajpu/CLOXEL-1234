import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("React Error Boundary Caught An Error:", error, errorInfo);
  }

  handleReset = () => {
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch(e) {}
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: '#fff', fontFamily: 'sans-serif', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#090d16' }}>
          <h2 style={{ color: '#f43f5e', fontSize: '1.5rem', marginBottom: '10px' }}>⚠️ Cloxel AI Interface Recovered</h2>
          <p style={{ color: '#94a3b8', maxWidth: '500px', fontSize: '0.9rem', marginBottom: '20px' }}>
            {this.state.error?.toString() || "A temporary browser rendering error occurred."}
          </p>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={() => window.location.reload()} style={{ padding: '10px 20px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
              🔄 Refresh App
            </button>
            <button onClick={this.handleReset} style={{ padding: '10px 20px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
              🧹 Clear Cache & Reset Session
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
