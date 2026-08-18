import React, { useState } from 'react';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

function Auth({ onLoginSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [emailOrMobile, setEmailOrMobile] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const endpoint = isLogin ? '/login' : '/register';
    
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_or_mobile: emailOrMobile,
          password: password
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Authentication failed');
      }

      // Success
      if (data.internal_id) {
        onLoginSuccess(data.internal_id);
      } else {
        throw new Error("No internal ID received");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>{isLogin ? 'Login to Cloxel' : 'Create an Account'}</h2>
        
        {error && <div className="auth-error">{error}</div>}
        
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label>Email or Mobile Number</label>
            <input 
              type="text" 
              placeholder="Enter email or mobile" 
              value={emailOrMobile}
              onChange={(e) => setEmailOrMobile(e.target.value)}
              required 
            />
          </div>
          
          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              placeholder="Enter password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>
          
          <button type="submit" disabled={isLoading} className="btn-primary auth-submit">
            {isLoading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
          </button>
        </form>

        {!isLogin && (
          <div className="auth-warning">
            <strong>Warning:</strong> Once you set your password, it cannot be changed. For security reasons, do not share your password or email with anyone.
          </div>
        )}

        <div className="auth-switch">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button type="button" onClick={() => { setIsLogin(!isLogin); setError(null); }} className="btn-link">
            {isLogin ? 'Register here' : 'Login here'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Auth;
