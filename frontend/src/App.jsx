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
      
      const verifyResp = await fetch(`${API_BASE}/verify-razorpay-payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          internal_id: userId,
          plan_type: planType,
          razorpay_order_id: orderData.order_id,
          razorpay_payment_id: `pay_${Date.now()}`
        })
      });
      
      if (verifyResp.ok) {
        alert("🎉 Membership Activated successfully for 30 Days!");
        setShowPricingModal(false);
        fetchSubscriptionStatus();
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
                <option value={10}>10 Seconds (1 Scene)</option>
                <option value={20}>20 Seconds (2 Scenes)</option>
                <option value={30}>30 Seconds (3 Scenes)</option>
                <option value={60}>60 Seconds (6 Scenes)</option>
                <option value={120}>2 Minutes (12 Scenes)</option>
                <option value={300}>5 Minutes (30 Scenes)</option>
              </select>
            </div>
          </div>

          {videoType === 'short' ? (
            <>
              <div className="form-group">
                <label>Main Topic</label>
                <input 
                  value={topic} 
                  onChange={(e) => setTopic(e.target.value)} 
                  placeholder="e.g. Space Facts"
                />
              </div>
              <button 
                className="button secondary" 
                style={{ marginBottom: '2rem' }}
                onClick={handleAutoGenerate}
                disabled={isGeneratingScript}
              >
                {isGeneratingScript ? "✨ Generating AI Script..." : "✨ Auto-Generate Script via AI"}
              </button>

              <div className="scenes-container">
                {scenes.map((scene, idx) => (
                  <div key={idx} className="scene-card">
                    <div className="scene-header">Scene {idx + 1} ({idx * 10}s - {(idx + 1) * 10}s)</div>
                    <div className="form-group">
                      <label>Script Chunk</label>
                      <textarea 
                        rows="3"
                        value={scene.text}
                        onChange={(e) => handleSceneChange(idx, 'text', e.target.value)}
                        placeholder="Enter script text for this part..."
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: 0 }}>
                      <label>Video Search Keyword</label>
                      <input 
                        value={scene.keyword}
                        onChange={(e) => handleSceneChange(idx, 'keyword', e.target.value)}
                        placeholder="e.g. galaxy stars"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="form-group">
              <label>Paste your Long Script here (System will automatically chunk it and extract keywords)</label>
              <textarea 
                rows="15"
                value={fullScript}
                onChange={(e) => setFullScript(e.target.value)}
                placeholder="Yahan hacked data, illegal deals aur anonymous websites mil sakti hain..."
              />
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
              <option value="en-IN-PrabhatNeural">Prabhat (Male, Hinglish/Indian)</option>
              <option value="en-IN-NeerjaExpressiveNeural">Neerja (Female, Expressive Hinglish)</option>
              <option value="en-US-ChristopherNeural">Christopher (Male, US English)</option>
              <option value="en-US-JennyNeural">Jenny (Female, US English)</option>
            </select>
          </div>

          <div className="form-group">
            <label>Font Family</label>
            <select value={fontName} onChange={e => setFontName(e.target.value)}>
              <option value="Arial.ttf">Arial</option>
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
                <p className="animate-pulse" style={{ marginTop: '1rem', color: 'var(--text-muted)' }}>
                  Rendering chunks and mixing... this takes time.
                </p>
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

      {/* Pricing & Membership Modal */}
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
              <div className="pricing-card">
                <div className="card-tag">30 DAYS</div>
                <h3>Short Starter</h3>
                <div className="plan-price">₹50 <span>/ month</span></div>
                <p className="plan-desc">Perfect for Shorts & Reels creators.</p>
                <ul className="plan-features">
                  <li>✅ Daily 1 Short Video (9:16) for 30 Days</li>
                  <li>✅ YouTube Auto-Upload Enabled</li>
                  <li>✅ Cloud Storage & History</li>
                </ul>
                <button className="btn-buy-plan" onClick={() => handleBuyPlan('short')}>
                  Subscribe for ₹50
                </button>
              </div>

              {/* Plan 2: Long Master */}
              <div className="pricing-card featured">
                <div className="card-tag gold">POPULAR</div>
                <h3>Long Master</h3>
                <div className="plan-price">₹100 <span>/ month</span></div>
                <p className="plan-desc">For full-length YouTube video channels.</p>
                <ul className="plan-features">
                  <li>✅ Daily 1 Long Video (16:9) for 30 Days</li>
                  <li>✅ YouTube Auto-Upload Enabled</li>
                  <li>✅ Cloud Storage & History</li>
                </ul>
                <button className="btn-buy-plan featured-btn" onClick={() => handleBuyPlan('long')}>
                  Subscribe for ₹100
                </button>
              </div>

              {/* Plan 3: Pro Combo */}
              <div className="pricing-card">
                <div className="card-tag purple">BEST VALUE</div>
                <h3>Pro Combo</h3>
                <div className="plan-price">₹119 <span>/ month</span></div>
                <p className="plan-desc">All-in-one power suite for max reach.</p>
                <ul className="plan-features">
                  <li>✅ Daily 1 Short + 1 Long Video for 30 Days</li>
                  <li>✅ YouTube Auto-Upload Enabled</li>
                  <li>✅ Priority AI Rendering</li>
                </ul>
                <button className="btn-buy-plan" onClick={() => handleBuyPlan('combo')}>
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
    </div>
  );
}

export default App;
