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

  // Nav Modals
  const [showHowItWorks, setShowHowItWorks] = useState(false);
  const [showFeatures, setShowFeatures] = useState(false);
  const [showSupport, setShowSupport] = useState(false);
  const [showPrivacyPolicy, setShowPrivacyPolicy] = useState(false);

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
          <button className="nav-link-btn" onClick={() => setShowHowItWorks(true)}>How it works</button>
          <button className="nav-link-btn" onClick={() => setShowFeatures(true)}>Features</button>
          <button className="nav-link-btn" onClick={() => setShowSupport(true)}>Support</button>
          <button className="nav-link-btn" onClick={() => setShowPrivacyPolicy(true)}>Privacy Policy</button>
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
                {isLoading ? 'Processing...' : (isLogin ? 'Login to Dashboard' : 'Create Account')}
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

      {/* Big Full-Screen Loading Animation Overlay */}
      {isLoading && (
        <div className="pricing-modal-overlay" style={{ zIndex: 2000 }}>
          <div style={{ maxWidth: '400px', textAlign: 'center', padding: '40px 24px', background: 'transparent', border: 'none', boxShadow: 'none' }}>
            <lottie-player 
              src="/loding.json" 
              background="transparent" 
              speed="1" 
              style={{ width: '220px', height: '220px', margin: '0 auto' }} 
              loop 
              autoplay
            ></lottie-player>
            <h3 style={{ color: '#ffffff', fontSize: '1.5rem', marginTop: '16px', marginBottom: '8px' }}>
              {isLogin ? 'Logging into Dashboard...' : 'Creating Your Account...'}
            </h3>
            <p style={{ color: '#cbd5e1', fontSize: '0.9rem', margin: 0 }}>
              Please wait a moment while we set up your session.
            </p>
          </div>
        </div>
      )}

      {/* 1. HOW IT WORKS MODAL */}
      {showHowItWorks && (
        <div className="pricing-modal-overlay" onClick={() => setShowHowItWorks(false)} style={{ zIndex: 3000 }}>
          <div className="pricing-modal-card" style={{ maxWidth: '850px', padding: '36px' }} onClick={e => e.stopPropagation()}>
            <button className="sidebar-close-btn" style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: '#fff', fontSize: '1.8rem', cursor: 'pointer' }} onClick={() => setShowHowItWorks(false)}>×</button>

            <div style={{ textAlign: 'center', marginBottom: '28px' }}>
              <span className="pricing-badge">⚙️ AUTOMATION WORKFLOW GRAPH</span>
              <h2 style={{ color: '#ffffff', fontSize: '2rem', marginTop: '8px', fontWeight: '800' }}>
                How Cloxel AI Automation Engine Works
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '0.95rem' }}>
                An end-to-end cloud pipeline converting your topics into 60FPS viral videos & auto-publishing.
              </p>
            </div>

            {/* Visual Step-by-step Flow Graph */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '28px' }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '16px', padding: '20px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', marginBottom: '10px' }}>💡 Step 1</div>
                <h4 style={{ color: '#c084fc', marginBottom: '6px' }}>Script Generation</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.8rem', margin: 0 }}>Gemini AI parses your topic and writes viral scene hooks.</p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '16px', padding: '20px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', marginBottom: '10px' }}>🗣️ Step 2</div>
                <h4 style={{ color: '#c084fc', marginBottom: '6px' }}>Madhur Voiceover</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.8rem', margin: 0 }}>Hyper-realistic Madhur Neural Voice synthesizes crisp speech.</p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '16px', padding: '20px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', marginBottom: '10px' }}>🎬 Step 3</div>
                <h4 style={{ color: '#c084fc', marginBottom: '6px' }}>FFmpeg Compositing</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.8rem', margin: 0 }}>HD stock visuals + auto-animated yellow captions are merged.</p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '16px', padding: '20px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', marginBottom: '10px' }}>🚀 Step 4</div>
                <h4 style={{ color: '#c084fc', marginBottom: '6px' }}>Cloud & YouTube</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.8rem', margin: 0 }}>100% Cloud storage delivery and 1-click YouTube auto-upload.</p>
              </div>
            </div>

            <button className="btn-hero-cta" style={{ width: '100%', padding: '12px' }} onClick={() => setShowHowItWorks(false)}>
              Got It! Close Guide →
            </button>
          </div>
        </div>
      )}

      {/* 2. FEATURES MODAL */}
      {showFeatures && (
        <div className="pricing-modal-overlay" onClick={() => setShowFeatures(false)} style={{ zIndex: 3000 }}>
          <div className="pricing-modal-card" style={{ maxWidth: '850px', padding: '36px' }} onClick={e => e.stopPropagation()}>
            <button className="sidebar-close-btn" style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: '#fff', fontSize: '1.8rem', cursor: 'pointer' }} onClick={() => setShowFeatures(false)}>×</button>

            <div style={{ textAlign: 'center', marginBottom: '28px' }}>
              <span className="pricing-badge">⚡ CORE CAPABILITIES</span>
              <h2 style={{ color: '#ffffff', fontSize: '2rem', marginTop: '8px', fontWeight: '800' }}>
                Cloxel AI Platform Features
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '0.95rem' }}>
                Everything you need to automate your YouTube & Shorts content creation.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '28px' }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '16px', padding: '20px' }}>
                <h4 style={{ color: '#c084fc', fontSize: '1.1rem', marginBottom: '8px' }}>📱 9:16 Shorts & Reels</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', margin: 0 }}>Create vertical viral Shorts with animated yellow subtitles.</p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '16px', padding: '20px' }}>
                <h4 style={{ color: '#c084fc', fontSize: '1.1rem', marginBottom: '8px' }}>🖥️ 16:9 Long YouTube Videos</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', margin: 0 }}>Full length landscape videos for long-form documentary channels.</p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '16px', padding: '20px' }}>
                <h4 style={{ color: '#c084fc', fontSize: '1.1rem', marginBottom: '8px' }}>🗣️ Madhur Neural Voice</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', margin: 0 }}>Natural human-like Indian voiceover with perfect pronunciation.</p>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(168,85,247,0.3)', borderRadius: '16px', padding: '20px' }}>
                <h4 style={{ color: '#c084fc', fontSize: '1.1rem', marginBottom: '8px' }}>📅 30-Day Auto Upload</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', margin: 0 }}>Schedule daily automated video generation and YouTube posting.</p>
              </div>
            </div>

            <button className="btn-hero-cta" style={{ width: '100%', padding: '12px' }} onClick={() => setShowFeatures(false)}>
              Explore Features & Start →
            </button>
          </div>
        </div>
      )}

      {/* 3. SUPPORT MODAL */}
      {showSupport && (
        <div className="pricing-modal-overlay" onClick={() => setShowSupport(false)} style={{ zIndex: 3000 }}>
          <div className="pricing-modal-card" style={{ maxWidth: '800px', padding: '36px' }} onClick={e => e.stopPropagation()}>
            <button className="sidebar-close-btn" style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: '#fff', fontSize: '1.8rem', cursor: 'pointer' }} onClick={() => setShowSupport(false)}>×</button>

            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <span className="pricing-badge">💬 24/7 SUPPORT CENTER</span>
              <h2 style={{ color: '#ffffff', fontSize: '2rem', marginTop: '8px', fontWeight: '800' }}>
                Cloxel AI Help & Support
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '0.95rem' }}>
                Have questions or need assistance? Our support team is here to help you 24/7.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
              <div style={{ background: 'rgba(255,255,255,0.04)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(168,85,247,0.3)' }}>
                <h4 style={{ color: '#c084fc', marginBottom: '10px' }}>✉️ Direct Email Support</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', marginBottom: '8px' }}>Email us anytime for account or payment queries:</p>
                <a href="mailto:support@cloxel.com" style={{ color: '#ec4899', fontWeight: 'bold', fontSize: '0.95rem', display: 'block' }}>support@cloxel.com</a>
                <a href="mailto:contact@zobbly.com" style={{ color: '#a855f7', fontWeight: 'bold', fontSize: '0.85rem', display: 'block', marginTop: '4px' }}>contact@zobbly.com</a>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.04)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(168,85,247,0.3)' }}>
                <h4 style={{ color: '#c084fc', marginBottom: '10px' }}>👤 Founder & Executive Contact</h4>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', margin: 0 }}><strong>Founder & CEO:</strong> Akash Raj</p>
                <p style={{ color: '#cbd5e1', fontSize: '0.85rem', marginTop: '4px' }}><strong>Organization:</strong> Cloxel AI Technologies India</p>
                <p style={{ color: '#22c55e', fontSize: '0.8rem', marginTop: '8px', margin: 0 }}>⚡ Guaranteed response within 24 hours.</p>
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.06)' }}>
              <h4 style={{ color: '#ffffff', marginBottom: '10px' }}>❓ Frequently Asked Questions</h4>
              <ul style={{ color: '#cbd5e1', fontSize: '0.85rem', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <li><strong>How do I activate my 30-day membership?</strong> Select your desired plan and complete Razorpay checkout. Activation is instant.</li>
                <li><strong>What if I repurchase an active plan?</strong> Your active membership is automatically extended by an additional 30 days.</li>
                <li><strong>Can I auto-upload videos to YouTube?</strong> Yes, connect your YouTube channel from the dashboard panel.</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* 4. OFFICIAL LEGAL PRIVACY POLICY MODAL */}
      {showPrivacyPolicy && (
        <div className="pricing-modal-overlay" onClick={() => setShowPrivacyPolicy(false)} style={{ zIndex: 3000 }}>
          <div className="pricing-modal-card" style={{ maxWidth: '850px', padding: '40px', background: '#0b071a', border: '2px solid rgba(168,85,247,0.5)' }} onClick={e => e.stopPropagation()}>
            <button className="sidebar-close-btn" style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: '#fff', fontSize: '1.8rem', cursor: 'pointer' }} onClick={() => setShowPrivacyPolicy(false)}>×</button>

            {/* Official Legal Header */}
            <div style={{ borderBottom: '2px solid rgba(168,85,247,0.3)', paddingBottom: '16px', marginBottom: '24px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', letterSpacing: '2px', color: '#c084fc', fontWeight: '800', textTransform: 'uppercase' }}>OFFICIAL LEGAL DOCUMENT • REPUBLIC OF INDIA COMPLIANT</div>
              <h2 style={{ color: '#ffffff', fontSize: '1.8rem', margin: '8px 0', fontWeight: '800' }}>
                Privacy Policy & User Terms Document
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '0.82rem' }}>
                Issued by Cloxel AI Technologies India | IT Act 2000 & Digital Personal Data Protection (DPDP) Act 2023 Guidelines
              </p>
            </div>

            {/* Document Body */}
            <div style={{ maxHeight: '50vh', overflowY: 'auto', paddingRight: '12px', fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.65', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <section>
                <h4 style={{ color: '#ffffff', fontSize: '1rem', marginBottom: '4px' }}>1. Advanced Binary Security Architecture (SMS OTP Replacement)</h4>
                <p>To eliminate SIM-swapping vulnerabilities and SMS interception delays, Cloxel AI utilizes high-level <strong>Binary Cryptographic Hash Architecture & SHA-256 Protocol Encryption</strong>, which is exponentially more powerful, secure, and resilient than traditional OTP systems. Account authorization relies directly on binary token handshakes and encrypted credentials.</p>
              </section>

              <section style={{ background: 'rgba(239, 68, 68, 0.08)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                <h4 style={{ color: '#f87171', fontSize: '1rem', marginBottom: '4px' }}>2. User Password Disclosure & Zero Responsibility Disclaimer</h4>
                <p style={{ color: '#fca5a5' }}>
                  While Cloxel AI implements state-of-the-art Binary Encryption, <strong>users remain 100% solely and completely responsible for maintaining strict password secrecy</strong>.
                </p>
                <p style={{ color: '#fca5a5', marginTop: '8px' }}>
                  <strong>Password Sharing Exclusion:</strong> If a user voluntarily or accidentally discloses, shares, or reveals their account password or email credentials to any third party, friend, or external service, <strong>Cloxel AI, its website, infrastructure, servers, and Founder Akash Raj hold ZERO legal liability, financial responsibility, or obligation for any resulting account breach, data loss, or unauthorized access.</strong>
                </p>
              </section>

              <section>
                <h4 style={{ color: '#ffffff', fontSize: '1rem', marginBottom: '4px' }}>3. Third-Party Integrations & YouTube API Services</h4>
                <p>By connecting YouTube channels, users agree to YouTube Terms of Service and Google Privacy Policy. Cloxel AI accesses OAuth tokens strictly for automated video publishing initiated by the user.</p>
              </section>

              <section>
                <h4 style={{ color: '#ffffff', fontSize: '1rem', marginBottom: '4px' }}>4. Official Company & Contact Details</h4>
                <p>For legal inquiries, formal notices, or privacy data requests, contact our legal office:</p>
                <ul style={{ paddingLeft: '20px', marginTop: '6px' }}>
                  <li><strong>Founder & Managing Director:</strong> Akash Raj</li>
                  <li><strong>Official Entity:</strong> Cloxel AI Technologies India</li>
                  <li><strong>Primary Contact Email:</strong> contact@zobbly.com</li>
                  <li><strong>Support Desk Email:</strong> support@cloxel.com</li>
                </ul>
              </section>
            </div>

            {/* Official Signature & Seal Block */}
            <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '2px dashed rgba(168,85,247,0.3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ color: '#94a3b8', fontSize: '0.75rem', margin: 0 }}>AUTHORIZATION SEAL</p>
                <div style={{ background: 'rgba(168,85,247,0.15)', border: '1px solid #a855f7', color: '#c084fc', padding: '6px 12px', borderRadius: '8px', fontSize: '0.75rem', fontWeight: 'bold', display: 'inline-block', marginTop: '4px' }}>
                  ✓ VERIFIED LEGAL POLICY DOC • REPUBLIC OF INDIA
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <p style={{ color: '#c084fc', fontFamily: 'cursive', fontSize: '1.4rem', margin: 0, fontWeight: 'bold' }}>
                  Akash Raj
                </p>
                <p style={{ color: '#ffffff', fontSize: '0.8rem', margin: 0, fontWeight: 'bold' }}>Akash Raj</p>
                <p style={{ color: '#94a3b8', fontSize: '0.75rem', margin: 0 }}>Founder & CEO, Cloxel AI</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Auth;
