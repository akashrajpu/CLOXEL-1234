import React, { useState } from 'react';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

function Auth({ onLoginSuccess }) {
  const [isLogin, setIsLogin] = useState(false); // Default to register or landing view
  const [showAuthModal, setShowAuthModal] = useState(false);

  // Form Fields
  const [name, setName] = useState('');
  const [country, setCountry] = useState('India');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [emailOrMobile, setEmailOrMobile] = useState('');
  const [password, setPassword] = useState('');
  
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const endpoint = isLogin ? '/login' : '/register';
    const payload = isLogin ? {
      email_or_mobile: emailOrMobile,
      password: password
    } : {
      name: name,
      country: country,
      phone: phone,
      email: email,
      password: password,
      email_or_mobile: email
    };

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Authentication failed');
      }

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
    <div className="landing-container">
      {/* Background Glowing Mesh / Orbs */}
      <div className="glow-orb orb-1"></div>
      <div className="glow-orb orb-2"></div>

      {/* Landing Navbar */}
      <nav className="landing-nav">
        <div className="nav-brand">
          <span className="brand-logo">✦</span> Cloxel <span>AI</span>
        </div>
        <div className="nav-links">
          <a href="#how-it-works">How it works</a>
          <a href="#features">Features</a>
          <a href="#support">Support</a>
        </div>
        <div className="nav-actions">
          <button className="btn-nav-login" onClick={() => { setIsLogin(true); setShowAuthModal(true); setError(null); }}>
            Login
          </button>
          <button className="btn-nav-primary" onClick={() => { setIsLogin(false); setShowAuthModal(true); setError(null); }}>
            Get Early Access
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="landing-hero">
        <div className="hero-badge">✨ NEXT-GEN FACELESS VIDEO GENERATOR</div>
        <h1 className="hero-title">
          See your videos come to life <span>before your next move.</span>
        </h1>
        <p className="hero-subtitle">
          AI connects your script, voiceovers, video scenes, and subtitles before you make a move. Fully automated 100% cloud video engine.
        </p>

        <div className="hero-cta-box">
          <button className="btn-hero-cta" onClick={() => { setIsLogin(false); setShowAuthModal(true); setError(null); }}>
            Create Account & Generate Free Video →
          </button>
          <p className="hero-cta-subtext">No credit card required. Instant AI video creation.</p>
        </div>

        {/* Floating Feature Badges */}
        <div className="hero-stats">
          <div className="stat-card">
            <h3>24/7</h3>
            <p>Automated AI Video Processing</p>
          </div>
          <div className="stat-card">
            <h3>100%</h3>
            <p>Cloud Based & Secure Data</p>
          </div>
        </div>
      </header>

      {/* Auth Modal (Overlay) */}
      {(showAuthModal || isLogin) && (
        <div className="auth-modal-overlay" onClick={() => setShowAuthModal(false)}>
          <div className="auth-modal-card" onClick={e => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setShowAuthModal(false)}>×</button>
            
            <div className="modal-header">
              <h2>{isLogin ? 'Welcome Back to Cloxel' : 'Create an Account'}</h2>
              <p>{isLogin ? 'Enter your credentials to access your dashboard' : 'Fill in mandatory details to get started'}</p>
            </div>

            {error && <div className="auth-error">{error}</div>}

            <form onSubmit={handleSubmit} className="auth-form">
              {!isLogin && (
                <>
                  <div className="form-group">
                    <label>Full Name *</label>
                    <input 
                      type="text" 
                      placeholder="e.g. Rahul Sharma" 
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label>Country *</label>
                    <select value={country} onChange={(e) => setCountry(e.target.value)} required>
                      <option value="India">India</option>
                      <option value="United States">United States</option>
                      <option value="United Kingdom">United Kingdom</option>
                      <option value="Canada">Canada</option>
                      <option value="Australia">Australia</option>
                      <option value="United Arab Emirates">United Arab Emirates</option>
                      <option value="Germany">Germany</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Phone Number *</label>
                    <input 
                      type="tel" 
                      placeholder="+91 9876543210" 
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      required 
                    />
                  </div>

                  <div className="form-group">
                    <label>Email Address *</label>
                    <input 
                      type="email" 
                      placeholder="name@example.com" 
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required 
                    />
                  </div>
                </>
              )}

              {isLogin && (
                <div className="form-group">
                  <label>Email Address or Mobile Number *</label>
                  <input 
                    type="text" 
                    placeholder="Enter registered Email or Mobile" 
                    value={emailOrMobile}
                    onChange={(e) => setEmailOrMobile(e.target.value)}
                    required 
                  />
                </div>
              )}

              <div className="form-group">
                <label>Password *</label>
                <input 
                  type="password" 
                  placeholder="Enter secure password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required 
                />
              </div>

              <button type="submit" disabled={isLoading} className="btn-primary auth-submit">
                {isLoading ? 'Please wait...' : (isLogin ? 'Login to Dashboard' : 'Create Account')}
              </button>
            </form>

            {!isLogin && (
              <div className="auth-warning">
                <strong>Warning:</strong> Once you set your password, it cannot be changed. For security reasons, do not share your password or email with anyone.
              </div>
            )}

            <div className="auth-switch">
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button 
                type="button" 
                onClick={() => { setIsLogin(!isLogin); setError(null); }} 
                className="btn-link"
              >
                {isLogin ? 'Register here' : 'Login here'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Auth;
