import React, { useState, useEffect } from 'react';
import Auth from './Auth';
import YouTubeIntegration from './YouTubeIntegration';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

function App() {
  const [topic, setTopic] = useState('Space Exploration');
  const [duration, setDuration] = useState(20);
  const [videoType, setVideoType] = useState('short'); // 'short' or 'long'
  const [fullScript, setFullScript] = useState('');
  
  // Customization Settings
  const [fontName, setFontName] = useState('Arial.ttf');
  const [fontSize, setFontSize] = useState(220);
  const [fontColor, setFontColor] = useState('yellow');
  const [voiceId, setVoiceId] = useState('hi-IN-MadhurNeural');

  const [scenes, setScenes] = useState([
    { text: '', keyword: '' },
    { text: '', keyword: '' }
  ]);
  
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [cloudinaryUrl, setCloudinaryUrl] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [history, setHistory] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showPricingModal, setShowPricingModal] = useState(false);
  const [showPaymentSuccessModal, setShowPaymentSuccessModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('long'); // 'short', 'long', 'combo'
  const [subStatus, setSubStatus] = useState({ free_demo_count: 2, has_active_subscription: false, plan_type: 'none' });
  
  // Auth state
  const [userId, setUserId] = useState(() => localStorage.getItem('cloxel_user_id') || null);

  const fetchSubscriptionStatus = async () => {
    if (!userId) return;
    try {
      const response = await fetch(`${API_BASE}/user-subscription/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setSubStatus(data);
      }
    } catch (e) {
      console.error("Failed to fetch subscription status:", e);
    }
  };

  const fetchHistory = async () => {
    if (!userId) return;
    try {
      const response = await fetch(`${API_BASE}/history/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data.history || []);
      }
    } catch (e) {
      console.error("Failed to fetch history:", e);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchHistory();
      fetchSubscriptionStatus();
    }
  }, [userId]);

  const handleLoginSuccess = (id) => {
    setUserId(id);
    localStorage.setItem('cloxel_user_id', id);
  };

  const handleLogout = () => {
    setUserId(null);
    setHistory([]);
    localStorage.removeItem('cloxel_user_id');
  };

  // Update scenes array when duration changes
  useEffect(() => {
    // Check for youtube success or error param
    const params = new URLSearchParams(window.location.search);
    if (params.get('yt_success')) {
      alert('YouTube Account successfully linked!');
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get('yt_error')) {
      alert(`YouTube Link Error: ${params.get('yt_error')}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    const chunkCount = Math.max(1, Math.floor(duration / 10));
    setScenes(prev => {
      if (prev.length === chunkCount) return prev;
      const newScenes = [...prev];
      if (newScenes.length < chunkCount) {
        while (newScenes.length < chunkCount) {
          newScenes.push({ text: '', keyword: '' });
        }
      } else {
        newScenes.length = chunkCount;
      }
      return newScenes;
    });
  }, [duration]);

  const handleSceneChange = (index, field, value) => {
    const newScenes = [...scenes];
    newScenes[index][field] = value;
    setScenes(newScenes);
  };

  const handleAutoGenerate = async () => {
    setIsGeneratingScript(true);
    try {
      const response = await fetch('https://cloxel.onrender.com/generate-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic,
          duration_seconds: duration
        })
      });
      const data = await response.json();
      if (data.scenes) {
        setScenes(data.scenes);
      }
    } catch (error) {
      alert("Failed to auto-generate script. Backend might be off.");
    } finally {
      setIsGeneratingScript(false);
    }
  };

  const handleGenerateVideo = async () => {
    setJobId(null);
    setJobStatus(null);
    setCloudinaryUrl(null);
    setDownloadUrl(null);
    
    try {
      const response = await fetch(`${API_BASE}/generate-custom-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic,
          scenes: scenes,
          font_name: fontName,
          font_color: fontColor,
          font_size: parseInt(fontSize),
          voice_id: voiceId,
          language: 'hi',
          video_type: videoType,
          full_script: fullScript,
          user_id: userId
        })
      });
      const data = await response.json();
      if (data.job_id) {
        setJobId(data.job_id);
        setJobStatus('processing');
        pollStatus(data.job_id);
      }
    } catch (error) {
      alert("Failed to connect to video generator backend.");
    }
  };

  const pollStatus = async (id) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/status/${id}`);
        const data = await response.json();
        
        setJobStatus(data.status);
        
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          if (data.cloudinary_url) {
            setCloudinaryUrl(data.cloudinary_url);
          } else if (data.status === 'completed') {
            setDownloadUrl(`${API_BASE}/download/${id}`);
          }
          // Refresh history after video generation completes
          if (data.status === 'completed' && userId) {
            fetchHistory();
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 5000);
  };

  const handleBuyPlan = async (planType) => {
    try {
      const response = await fetch(`${API_BASE}/create-razorpay-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ internal_id: userId, plan_type: planType })
      });
      const orderData = await response.json();
      
      if (!response.ok) {
        alert(orderData.detail || "Failed to create order");
        return;
      }

      // Real Razorpay Popup Checkout Integration
      if (window.Razorpay && orderData.key_id) {
        const options = {
          key: orderData.key_id,
          amount: orderData.amount,
          currency: orderData.currency,
          name: "Cloxel AI Video Generator",
          description: `30 Days Membership (${planType.toUpperCase()})`,
          order_id: orderData.order_id,
          prefill: {
            name: "Zobbly User",
            email: "user@cloxel.com",
            contact: "9876543210"
          },
          handler: async function (res) {
            // Verify payment on backend ONLY when payment actually succeeds!
            const verifyResp = await fetch(`${API_BASE}/verify-razorpay-payment`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                internal_id: userId,
                plan_type: planType,
                razorpay_order_id: res.razorpay_order_id,
                razorpay_payment_id: res.razorpay_payment_id,
                razorpay_signature: res.razorpay_signature
              })
            });
            
            if (verifyResp.ok) {
              setShowPricingModal(false);
              setShowPaymentSuccessModal(true);
              fetchSubscriptionStatus();
            } else {
              const errData = await verifyResp.json();
              alert(errData.detail || "Payment Verification Failed.");
            }
          },
          modal: {
            ondismiss: function() {
              alert("⚠️ Payment cancelled. Membership was NOT activated.");
            }
          },
          theme: { color: "#8b5cf6" }
        };

        const rzp = new window.Razorpay(options);
        rzp.on('payment.failed', function (res) {
          alert(`❌ Payment Failed: ${res.error.description || 'Transaction declined'}`);
        });
        rzp.open();
      } else {
        alert("⚠️ Live Razorpay API Keys are not yet configured in Render environment variables (RAZORPAY_KEY_ID & RAZORPAY_KEY_SECRET).\n\nPlease add your Razorpay keys to Render to allow live user payments!");
      }
    } catch (err) {
      alert("Payment processing error. Please try again.");
    }
  };

  if (!userId) {
    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <button className="hamburger-btn" onClick={() => setIsSidebarOpen(true)} title="Open Menu">
            ☰
          </button>
          <h1>Cloxel <span>AI Video Generator</span></h1>
        </div>
        <div className="header-right" style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button className="btn-upgrade-pill" onClick={() => setShowPricingModal(true)}>
            💎 Upgrade Plan
          </button>
          <button className="profile-pill-btn" onClick={() => setIsSidebarOpen(true)}>
            <span>👤 Account</span>
          </button>
        </div>
      </header>

      <div className="dashboard">
        <main className="panel">
          <h2>🎬 Script & Content Editor</h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label>Video Type</label>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button 
                  className={`button ${videoType === 'short' ? 'primary' : 'secondary'}`}
                  onClick={() => setVideoType('short')}
                  style={{ flex: 1 }}
                >📱 Short (9:16)</button>
                <button 
                  className={`button ${videoType === 'long' ? 'primary' : 'secondary'}`}
                  onClick={() => setVideoType('long')}
                  style={{ flex: 1 }}
                >🖥️ Long (16:9)</button>
              </div>
            </div>
            <div className="form-group">
              <label>Target Duration (Seconds)</label>
              <select value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                <option value={20}>20 Seconds (2 Scenes)</option>
                <option value={30}>30 Seconds (3 Scenes)</option>
                <option value={60}>60 Seconds (6 Scenes)</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Main Topic</label>
            <input 
              type="text" 
              value={topic} 
              onChange={e => setTopic(e.target.value)} 
              placeholder="e.g. History of AI, Space Exploration, Fitness Motivation"
            />
          </div>

          <div className="form-group">
            <button 
              className="button secondary" 
              onClick={handleAutoGenerate}
              disabled={isGeneratingScript}
              style={{ width: '100%', marginBottom: '1.5rem', background: '#3b82f6', color: 'white' }}
            >
              {isGeneratingScript ? 'Generating Script via Gemini AI...' : '✨ Auto-Generate Script via AI'}
            </button>
          </div>

          {videoType === 'long' ? (
            <div className="form-group">
              <label>Full Video Script (AI generated or custom)</label>
              <textarea 
                rows={8}
                value={fullScript}
                onChange={e => setFullScript(e.target.value)}
                placeholder="Paste or write your full video script here. Our smart AI will automatically split it into matching scenes and generate appropriate background visuals."
              />
            </div>
          ) : (
            <div className="scenes-list">
              {scenes.map((scene, index) => (
                <div key={index} className="scene-card" style={{ borderLeft: '4px solid var(--primary)', paddingLeft: '1rem', marginBottom: '1.5rem' }}>
                  <h4 style={{ color: '#a855f7', marginBottom: '0.5rem' }}>Scene {index + 1} ({index * 10}s - {(index + 1) * 10}s)</h4>
                  <div className="form-group">
                    <label>Script Chunk</label>
                    <textarea 
                      rows={2}
                      value={scene.text}
                      onChange={e => handleSceneChange(index, 'text', e.target.value)}
                      placeholder="Enter script text for this part..."
                    />
                  </div>
                  <div className="form-group">
                    <label>Video Search Keyword</label>
                    <input 
                      type="text"
                      value={scene.keyword}
                      onChange={e => handleSceneChange(index, 'keyword', e.target.value)}
                      placeholder="e.g. galaxy stars"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

        </main>

        <aside className="panel">
          <h2>⚙️ Video Settings</h2>
          
          <div className="form-group">
            <label>AI Voice</label>
            <select value={voiceId} onChange={e => setVoiceId(e.target.value)}>
              <option value="hi-IN-MadhurNeural">Madhur (Male, Hindi)</option>
              <option value="hi-IN-SwaraNeural">Swara (Female, Hindi)</option>
              <option value="en-US-GuyNeural">Guy (Male, English)</option>
              <option value="en-US-JennyNeural">Jenny (Female, English)</option>
            </select>
          </div>

          <div className="form-group">
            <label>Font Family</label>
            <select value={fontName} onChange={e => setFontName(e.target.value)}>
              <option value="Arial.ttf">Arial</option>
              <option value="Roboto.ttf">Roboto</option>
              <option value="Impact.ttf">Impact (Bold Shorts Style)</option>
            </select>
          </div>
          
          <div className="form-group">
            <label>Font Size</label>
            <input 
              type="number" 
              value={fontSize} 
              onChange={e => setFontSize(e.target.value)} 
            />
          </div>

          <div className="form-group">
            <label>Highlight Color</label>
            <select value={fontColor} onChange={e => setFontColor(e.target.value)}>
              <option value="yellow">Yellow</option>
              <option value="#00FF00">Neon Green</option>
              <option value="#FF00FF">Magenta</option>
              <option value="cyan">Cyan</option>
            </select>
          </div>

          <button 
            className="button" 
            onClick={handleGenerateVideo}
            disabled={jobStatus === 'processing'}
            style={{ marginTop: '2rem' }}
          >
            {jobStatus === 'processing' ? 'Processing...' : '🚀 Generate Video'}
          </button>

          {jobStatus && (
            <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
              <div className={`status-badge status-${jobStatus}`}>
                Status: {jobStatus.toUpperCase()}
              </div>
              {jobStatus === 'processing' && (
                <div style={{ marginTop: '1rem' }}>
                  <lottie-player 
                    src="/loding.json" 
                    background="transparent" 
                    speed="1" 
                    style={{ width: '120px', height: '120px', margin: '0 auto' }} 
                    loop 
                    autoplay
                  ></lottie-player>
                  <p className="animate-pulse" style={{ marginTop: '0.5rem', color: 'var(--text-muted)' }}>
                    Rendering video scenes & mixing audio... please wait.
                  </p>
                </div>
              )}
            </div>
          )}

          {cloudinaryUrl ? (
            <div className="video-result">
              <video src={cloudinaryUrl} controls autoPlay loop muted></video>
              <a href={cloudinaryUrl} target="_blank" rel="noreferrer" className="download-link">
                Open in Cloudinary
              </a>
            </div>
          ) : downloadUrl ? (
            <div className="video-result">
              <video src={downloadUrl} controls autoPlay loop muted></video>
              <a href={downloadUrl} target="_blank" rel="noreferrer" className="download-link">
                Download Direct Video
              </a>
            </div>
          ) : null}

          {/* YOUTUBE INTEGRATION */}
          <YouTubeIntegration userId={userId} />
        </aside>
      </div>

      {/* Slide-out Sidebar Drawer */}
      {isSidebarOpen && (
        <div className="sidebar-backdrop" onClick={() => setIsSidebarOpen(false)}>
          <div className="sidebar-drawer" onClick={e => e.stopPropagation()}>
            <div className="sidebar-header">
              <h3>Menu & Profile</h3>
              <button className="sidebar-close-btn" onClick={() => setIsSidebarOpen(false)}>×</button>
            </div>

            <div className="sidebar-profile">
              <div className="profile-avatar">👤</div>
              <div className="profile-info">
                <p className="profile-title">Account Active</p>
                <p className="profile-id">ID: {userId ? `${userId.substring(0, 12)}...` : 'Unknown'}</p>
                <p className="profile-sub-badge" style={{ fontSize: '0.75rem', color: '#c084fc', marginTop: '4px', fontWeight: 'bold' }}>
                  {subStatus.has_active_subscription ? `Active Plan: ${subStatus.plan_type.toUpperCase()}` : `Free Demo Videos Left: ${subStatus.free_demo_count}/2`}
                </p>
              </div>
            </div>

            <div style={{ marginBottom: '15px' }}>
              <button className="btn-upgrade-sidebar" onClick={() => { setIsSidebarOpen(false); setShowPricingModal(true); }}>
                💎 Upgrade Membership
              </button>
            </div>

            <div className="sidebar-history-section">
              <h4>🕒 Your Video History ({history.length})</h4>
              {history.length === 0 ? (
                <p className="no-history-msg">No videos generated yet.</p>
              ) : (
                <div className="sidebar-history-list">
                  {history.map((vid, idx) => (
                    <div key={idx} className="sidebar-history-card">
                      <p className="history-card-topic">{vid.topic || 'Untitled Video'}</p>
                      <p className="history-card-date">
                        {vid.created_at ? new Date(vid.created_at).toLocaleString() : ''}
                      </p>
                      {vid.cloudinary_url ? (
                        <a href={vid.cloudinary_url} target="_blank" rel="noreferrer" className="history-watch-btn">
                          ▶ Watch (Cloudinary)
                        </a>
                      ) : vid.job_id ? (
                        <a href={`${API_BASE}/download/${vid.job_id}`} target="_blank" rel="noreferrer" className="history-watch-btn">
                          ⬇ Download Video
                        </a>
                      ) : (
                        <span className="history-local-tag">Local file</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="sidebar-footer">
              <button className="btn-logout-sidebar" onClick={() => { setIsSidebarOpen(false); handleLogout(); }}>
                🚪 Logout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pricing & Membership Modal with Dynamic Highlighting */}
      {showPricingModal && (
        <div className="pricing-modal-overlay" onClick={() => setShowPricingModal(false)}>
          <div className="pricing-modal-card" onClick={e => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setShowPricingModal(false)}>×</button>
            
            <div className="pricing-header">
              <span className="pricing-badge">💎 MEMBERSHIP PLANS</span>
              <h2>Choose Your Monthly Video Plan</h2>
              <p>Unlock 30 days of daily automated AI video creation and auto-uploads.</p>
            </div>

            <div className="pricing-grid">
              {/* Plan 1: Short Starter */}
              <div 
                className={`pricing-card ${selectedPlan === 'short' ? 'featured' : ''}`}
                onClick={() => setSelectedPlan('short')}
                style={{ cursor: 'pointer' }}
              >
                <div className="card-tag">30 DAYS</div>
                <h3>Short Starter</h3>
                <div className="plan-price">₹50 <span>/ month</span></div>
                <p className="plan-desc">Perfect for Shorts & Reels creators.</p>
                <ul className="plan-features">
                  <li>✅ Daily 1 Short Video (9:16) for 30 Days</li>
                  <li>✅ YouTube Auto-Upload Enabled</li>
                  <li>✅ Cloud Storage & History</li>
                </ul>
                <button 
                  className={`btn-buy-plan ${selectedPlan === 'short' ? 'featured-btn' : ''}`} 
                  onClick={(e) => { e.stopPropagation(); setSelectedPlan('short'); handleBuyPlan('short'); }}
                >
                  Subscribe for ₹50
                </button>
              </div>

              {/* Plan 2: Long Master */}
              <div 
                className={`pricing-card ${selectedPlan === 'long' ? 'featured' : ''}`}
                onClick={() => setSelectedPlan('long')}
                style={{ cursor: 'pointer' }}
              >
                <div className="card-tag gold">POPULAR</div>
                <h3>Long Master</h3>
                <div className="plan-price">₹100 <span>/ month</span></div>
                <p className="plan-desc">For full-length YouTube video channels.</p>
                <ul className="plan-features">
                  <li>✅ Daily 1 Long Video (16:9) for 30 Days</li>
                  <li>✅ YouTube Auto-Upload Enabled</li>
                  <li>✅ Cloud Storage & History</li>
                </ul>
                <button 
                  className={`btn-buy-plan ${selectedPlan === 'long' ? 'featured-btn' : ''}`} 
                  onClick={(e) => { e.stopPropagation(); setSelectedPlan('long'); handleBuyPlan('long'); }}
                >
                  Subscribe for ₹100
                </button>
              </div>

              {/* Plan 3: Pro Combo */}
              <div 
                className={`pricing-card ${selectedPlan === 'combo' ? 'featured' : ''}`}
                onClick={() => setSelectedPlan('combo')}
                style={{ cursor: 'pointer' }}
              >
                <div className="card-tag purple">BEST VALUE</div>
                <h3>Pro Combo</h3>
                <div className="plan-price">₹119 <span>/ month</span></div>
                <p className="plan-desc">All-in-one power suite for max reach.</p>
                <ul className="plan-features">
                  <li>✅ Daily 1 Short + 1 Long Video for 30 Days</li>
                  <li>✅ YouTube Auto-Upload Enabled</li>
                  <li>✅ Priority AI Rendering</li>
                </ul>
                <button 
                  className={`btn-buy-plan ${selectedPlan === 'combo' ? 'featured-btn' : ''}`} 
                  onClick={(e) => { e.stopPropagation(); setSelectedPlan('combo'); handleBuyPlan('combo'); }}
                >
                  Subscribe for ₹119
                </button>
              </div>
            </div>

            <div className="pricing-footer">
              🔒 Safe & Secure Payments via Razorpay. Cancel anytime.
            </div>
          </div>
        </div>
      )}

      {/* Payment Success Confirmation Modal with payment.json Lottie animation */}
      {showPaymentSuccessModal && (
        <div className="pricing-modal-overlay" onClick={() => setShowPaymentSuccessModal(false)}>
          <div className="pricing-modal-card" style={{ maxWidth: '420px', textAlign: 'center', padding: '40px 24px' }} onClick={e => e.stopPropagation()}>
            <lottie-player 
              src="/payment.json" 
              background="transparent" 
              speed="1" 
              style={{ width: '220px', height: '220px', margin: '0 auto' }} 
              autoplay
            ></lottie-player>

            <h2 style={{ color: '#22c55e', fontSize: '1.8rem', marginTop: '16px', marginBottom: '8px' }}>
              🎉 Payment Successful!
            </h2>
            <p style={{ color: '#cbd5e1', fontSize: '0.95rem', marginBottom: '24px' }}>
              Your 30-Day Membership has been activated. You can now generate videos and auto-upload to YouTube!
            </p>

            <button 
              className="btn-hero-cta" 
              style={{ width: '100%', padding: '14px', fontSize: '1rem' }} 
              onClick={() => setShowPaymentSuccessModal(false)}
            >
              Start Creating Videos →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
