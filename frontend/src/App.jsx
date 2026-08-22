import React, { useState, useEffect } from 'react';
import Auth from './Auth';
import YouTubeIntegration from './YouTubeIntegration';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

const CATEGORIES = [
  '🎲 Random / All Categories',
  '🤖 AI & Technology',
  '🌌 Space & Astronomy',
  '🦁 Nature & Wildlife',
  '🏛️ History & Ancient Mysteries',
  '💰 Wealth & Finance',
  '🏋️ Fitness & Health',
  '🎨 Cartoon & Animation',
  '👻 Horror & Paranormal',
  '🎮 Gaming & Esports',
  '🍕 Food & Cooking',
  '🔥 Motivation & Success',
  '🎬 Movie Recaps & Reviews',
  '💡 Life Hacks & Science Facts',
  '🧠 Philosophy & Psychology',
  '💼 Business & Startups',
  '🕵️ True Crime & Mystery',
  '📱 Tech Gadgets & Unboxing',
  '🔱 Mythology & Legends',
  '✈️ Travel & Adventure',
  '🚗 Luxury Cars & Supercars',
  '⚽ Sports & Athletics',
  '👗 Fashion & Lifestyle',
  '🎶 Music & Pop Culture',
  '🧪 Physics & Chemistry Wonders',
  '🐶 Pets & Animals',
  '🧘 Meditation & Mindfulness',
  '📖 Book Summaries & Literature',
  '🚀 Future Tech & Sci-Fi',
  '🌐 World News & Geopolitics',
  '🛠️ DIY & Crafts',
  '✍️ Custom Category (Type Below)'
];

function App() {
  const [topic, setTopic] = useState('Space Exploration');
  const [duration, setDuration] = useState(20);
  const [videoType, setVideoType] = useState('short'); // 'short' or 'long'
  const [fullScript, setFullScript] = useState('');
  
  // Customization Settings
  const [fontName, setFontName] = useState('Arial.ttf');
  const [fontList, setFontList] = useState(['Arial.ttf', 'AgentOrange.ttf', 'BetsyFlanagan.ttf', 'CarbonBlock.ttf', 'Cartoon Blocks.ttf', 'GrapeSoda.ttf', 'HighLevel.ttf', 'RaceFlow.ttf']);
  const [fontSize, setFontSize] = useState(220);
  const [fontColor, setFontColor] = useState('yellow');
  const [voiceId, setVoiceId] = useState('hi-IN-MadhurNeural');
  const [bgMusic, setBgMusic] = useState('cool.mp3');
  const [bgMusicList, setBgMusicList] = useState(['cool.mp3', 'cool1.mp3', 'cool2.mp3', 'cool3.mp3', 'cool4.mp3', 'cool5.mp3', 'random', 'none']);

  const [category, setCategory] = useState('🎲 Random / All Categories');
  const [customCategory, setCustomCategory] = useState('');

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
  const [showAutoUploadModal, setShowAutoUploadModal] = useState(false);
  const [showStopScheduleWarningModal, setShowStopScheduleWarningModal] = useState(false);
  const [customAlert, setCustomAlert] = useState(null);
  const [playingHistoryVideo, setPlayingHistoryVideo] = useState(null);

  const triggerAlert = (title, message, icon = '⚠️', type = 'info', onConfirm = null, confirmText = 'OK', cancelText = 'Cancel') => {
    setCustomAlert({
      title,
      message,
      icon,
      type,
      onConfirm,
      confirmText,
      cancelText
    });
  };
  const [isPaymentProcessing, setIsPaymentProcessing] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('long'); // 'short', 'long', 'combo'
  const [subStatus, setSubStatus] = useState({ free_demo_count: 2, has_active_subscription: false, plan_type: 'none' });
  const [autoSchedule, setAutoSchedule] = useState({
    schedule_enabled: true,
    short_auto_topic: true,
    short_topic: 'Space Exploration, AI Innovations',
    short_category: '🎲 Random / All Categories',
    short_voice: 'hi-IN-MadhurNeural',
    short_font: 'Arial.ttf',
    short_color: 'yellow',
    short_duration: 30,
    short_time: '10:00',
    short_language: 'hi',
    long_auto_topic: true,
    long_topic: 'Space Exploration, AI Technology',
    long_category: '🎲 Random / All Categories',
    long_voice: 'hi-IN-MadhurNeural',
    long_font: 'Arial.ttf',
    long_color: 'yellow',
    long_duration: 60,
    long_time: '18:00',
    long_language: 'hi',
    topics: 'Space Exploration, AI Innovations, Ancient Mysteries, Wealth & Finance',
    total_videos_created: 0,
    remaining_plan_videos: 60,
    next_scheduled_run: 'Short: Daily at 10:00 | Long: Daily at 18:00'
  });
  
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

  const fetchAutoSchedule = async () => {
    if (!userId) return;
    try {
      const res = await fetch(`${API_BASE}/get-auto-schedule/${userId}`);
      if (res.ok) {
        const data = await res.json();
        setAutoSchedule(data);
      }
    } catch (e) {
      console.error("Failed to fetch auto schedule:", e);
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

  const fetchBgMusicAndFonts = async () => {
    try {
      const resM = await fetch(`${API_BASE}/bg-music-list`);
      if (resM.ok) {
        const dataM = await resM.json();
        if (dataM.music_tracks && dataM.music_tracks.length > 0) {
          setBgMusicList(['cool.mp3', 'cool1.mp3', 'cool2.mp3', 'cool3.mp3', 'cool4.mp3', 'cool5.mp3', 'random', 'none', ...dataM.music_tracks.filter(t => !['cool.mp3', 'cool1.mp3', 'cool2.mp3', 'cool3.mp3', 'cool4.mp3', 'cool5.mp3'].includes(t))]);
        }
      }
      const resF = await fetch(`${API_BASE}/fonts-list`);
      if (resF.ok) {
        const dataF = await resF.json();
        if (dataF.fonts && dataF.fonts.length > 0) {
          setFontList(dataF.fonts);
        }
      }
    } catch (e) {
      console.error("Failed to fetch bg music or fonts:", e);
    }
  };

  useEffect(() => {
    fetchBgMusicAndFonts();
    if (userId) {
      fetchHistory();
      fetchSubscriptionStatus();
      fetchAutoSchedule();
    }
  }, [userId]);

  const handleSaveAutoSchedule = async (explicitEnabledState = null) => {
    if (!userId) return;
    if (!subStatus.has_active_subscription) {
      triggerAlert(
        "Active Membership Required",
        "Auto-Schedule & YouTube Auto-Upload are exclusive to active paid members. Please upgrade your plan to activate auto-scheduling!",
        "🔒",
        "danger",
        () => {
          setShowAutoUploadModal(false);
          setShowPricingModal(true);
        },
        "Upgrade Membership Plan →"
      );
      return;
    }

    const finalEnabledState = explicitEnabledState !== null ? explicitEnabledState : autoSchedule.schedule_enabled;

    try {
      const res = await fetch(`${API_BASE}/save-auto-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          internal_id: userId,
          schedule_enabled: finalEnabledState,
          
          short_auto_topic: autoSchedule.short_auto_topic !== false,
          short_topic: autoSchedule.short_topic || 'Space Exploration, AI Innovations',
          short_category: autoSchedule.short_category || 'Random',
          short_voice: autoSchedule.short_voice || 'hi-IN-MadhurNeural',
          short_font: autoSchedule.short_font || 'Arial.ttf',
          short_color: autoSchedule.short_color || 'yellow',
          short_duration: parseInt(autoSchedule.short_duration || 30),
          short_time: autoSchedule.short_time || '10:00',
          short_language: autoSchedule.short_language || 'hi',
          
          long_auto_topic: autoSchedule.long_auto_topic !== false,
          long_topic: autoSchedule.long_topic || 'Space Exploration, AI Technology',
          long_category: autoSchedule.long_category || 'Random',
          long_voice: autoSchedule.long_voice || 'hi-IN-MadhurNeural',
          long_font: autoSchedule.long_font || 'Arial.ttf',
          long_color: autoSchedule.long_color || 'yellow',
          long_duration: parseInt(autoSchedule.long_duration || 60),
          long_time: autoSchedule.long_time || '18:00',
          long_language: autoSchedule.long_language || 'hi'
        })
      });
      if (res.ok) {
        if (finalEnabledState) {
          triggerAlert(
            "Auto-Publishing Activated",
            "Server will automatically track your topics, voice, font, and duration settings for your active plan and publish to YouTube on schedule.",
            "⚡",
            "success"
          );
        } else {
          triggerAlert(
            "Auto-Publishing Stopped",
            "Automated video generation and YouTube publishing have been completely suspended until you re-enable it.",
            "🛑",
            "danger"
          );
        }
        fetchAutoSchedule();
        setShowAutoUploadModal(false);
        setShowStopScheduleWarningModal(false);
      } else {
        const errData = await res.json();
        triggerAlert("Error", errData.detail || "Failed to save schedule settings.", "⚠️", "danger");
      }
    } catch (err) {
      triggerAlert("Error", "Error saving auto schedule.", "⚠️", "danger");
    }
  };

  const handleLoginSuccess = (id) => {
    setUserId(id);
    localStorage.setItem('cloxel_user_id', id);
  };

  const handleLogout = () => {
    try {
      localStorage.clear();
      sessionStorage.clear();
      localStorage.removeItem('cloxel_user_id');
      localStorage.removeItem('user_data');
    } catch (e) {
      console.error("Error clearing browser storage:", e);
    }

    setUserId(null);
    setHistory([]);
    setFullScript('');
    setTopic('Space Exploration');
    setJobId(null);
    setJobStatus(null);
    setCloudinaryUrl(null);
    setDownloadUrl(null);
    setPlayingHistoryVideo(null);
    setIsSidebarOpen(false);
    setShowPricingModal(false);
    setShowAutoUploadModal(false);
    setShowStopScheduleWarningModal(false);
    setCustomAlert(null);
    setSubStatus({ free_demo_count: 2, has_active_subscription: false, plan_type: 'none' });

    window.location.href = window.location.origin + window.location.pathname;
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
    const finalCategory = (category || '').includes('Custom Category') ? (customCategory || 'Random') : category;
    try {
      const response = await fetch(`${API_BASE}/generate-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic,
          category: finalCategory,
          duration_seconds: duration,
          video_type: videoType
        })
      });
      const data = await response.json();
      if (data.full_script) {
        setFullScript(data.full_script);
      }
      if (data.scenes && data.scenes.length > 0) {
        setScenes(data.scenes);
        if (!data.full_script) {
          const combinedScript = data.scenes.map(s => s.text).join(" ");
          setFullScript(combinedScript);
        }
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
          category: (category || '').includes('Custom Category') ? (customCategory || 'Random') : category,
          scenes: scenes,
          font_name: fontName,
          font_color: fontColor,
          font_size: parseInt(fontSize),
          voice_id: voiceId,
          language: 'hi',
          video_type: videoType,
          full_script: fullScript,
          bg_music: bgMusic,
          user_id: userId
        })
      });
      const data = await response.json();
      if (data.job_id) {
        setJobId(data.job_id);
        setJobStatus('processing');
        pollStatus(data.job_id);
      } else if (data.detail) {
        alert(`⚠️ ${data.detail}`);
      } else {
        alert("Failed to start video generation. Please check your account subscription or login status.");
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

  const handleProfilePicUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64Image = reader.result;
      setSubStatus(prev => ({ ...prev, profile_pic: base64Image }));
      try {
        await fetch(`${API_BASE}/update-profile-pic`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ internal_id: userId, profile_pic: base64Image })
        });
      } catch (err) {
        console.error("Profile picture upload error:", err);
      }
    };
    reader.readAsDataURL(file);
  };

  const PLAN_RANKS = { short: 1, long: 2, combo: 3 };
  const PLAN_NAMES = { short: 'Short Starter (₹50)', long: 'Long Master (₹100)', combo: 'Pro Combo (₹119)' };

  const executeCheckout = async (planType) => {
    try {
      setIsPaymentProcessing(true);
      const response = await fetch(`${API_BASE}/create-razorpay-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ internal_id: userId, plan_type: planType })
      });
      const orderData = await response.json();
      setIsPaymentProcessing(false);
      
      if (!response.ok) {
        triggerAlert("Order Creation Failed", orderData.detail || "Failed to create order.", "❌", "danger");
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
            name: "Cloxel User",
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
            
            const verifyData = await verifyResp.json();
            if (verifyResp.ok) {
              setShowPricingModal(false);
              setShowPaymentSuccessModal(true);
              fetchSubscriptionStatus();
              fetchAutoSchedule();
            } else {
              triggerAlert("Payment Verification Failed", verifyData.detail || "Payment Verification Failed.", "❌", "danger");
            }
          },
          modal: {
            ondismiss: function () {
              triggerAlert("Payment Cancelled", "Transaction was cancelled.", "ℹ️", "info");
            }
          }
        };

        const rzp = new window.Razorpay(options);
        rzp.open();
      } else {
        triggerAlert("Razorpay Notice", "Live Razorpay API Keys are not configured in Render. Please add RAZORPAY_KEY_ID & RAZORPAY_KEY_SECRET to Render.", "⚠️", "info");
      }
    } catch (err) {
      setIsPaymentProcessing(false);
      triggerAlert("Payment Error", "Payment processing error. Please try again.", "❌", "danger");
    }
  };

  const handleBuyPlan = async (planType) => {
    if (subStatus.has_active_subscription) {
      const currRank = PLAN_RANKS[subStatus.plan_type] || 0;
      const newRank = PLAN_RANKS[planType] || 0;

      if (newRank < currRank) {
        triggerAlert(
          "Plan Downgrade Restricted",
          `You currently have an active high-tier plan (${PLAN_NAMES[subStatus.plan_type] || subStatus.plan_type.toUpperCase()}).\n\nYou cannot downgrade to ${PLAN_NAMES[planType]} until your current high-tier plan expires on ${subStatus.expires_at ? new Date(subStatus.expires_at).toLocaleDateString() : 'expiry'}.`,
          "⚠️",
          "danger"
        );
        return;
      } else if (newRank > currRank) {
        triggerAlert(
          "Upgrade Membership Notice",
          `Upgrading to ${PLAN_NAMES[planType]} will replace your current ${PLAN_NAMES[subStatus.plan_type]} plan and start a fresh 30-day high-tier subscription immediately!`,
          "🚀",
          "info",
          () => executeCheckout(planType),
          `Upgrade Now (₹${planType === 'combo' ? 119 : 100})`,
          "Cancel"
        );
        return;
      } else {
        triggerAlert(
          "Same Plan Duration Stacking",
          `You already have an active ${PLAN_NAMES[planType]} plan.\n\nPurchasing this plan again will stack and extend your active membership duration by an additional +30 days!`,
          "🔄",
          "info",
          () => executeCheckout(planType),
          "Proceed to Stack (+30 Days)",
          "Cancel"
        );
        return;
      }
    }
    executeCheckout(planType);
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
          <button className="profile-pill-btn" onClick={() => setIsSidebarOpen(true)} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {subStatus.profile_pic ? (
              <img src={subStatus.profile_pic} alt="User" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover' }} />
            ) : (
              <span>👤</span>
            )}
            <span>{subStatus.name ? subStatus.name.split(' ')[0] : 'Account'}</span>
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
                  onClick={() => {
                    setVideoType('short');
                    if (duration > 55) setDuration(30);
                  }}
                  style={{ flex: 1, border: videoType === 'short' ? '2px solid #a855f7' : '1px solid rgba(255,255,255,0.1)' }}
                >📱 Short (9:16)</button>
                <button 
                  className={`button ${videoType === 'long' ? 'primary' : 'secondary'}`}
                  onClick={() => {
                    setVideoType('long');
                    if (duration < 20) setDuration(60);
                  }}
                  style={{ flex: 1, border: videoType === 'long' ? '2px solid #06b6d4' : '1px solid rgba(255,255,255,0.1)' }}
                >🖥️ Long (16:9)</button>
              </div>
            </div>
            <div className="form-group">
              <label>Target Duration (Seconds)</label>
              <select value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                {videoType === 'short' ? (
                  <>
                    <option value={10}>10 Seconds (1 Scene)</option>
                    <option value={20}>20 Seconds (2 Scenes)</option>
                    <option value={30}>30 Seconds (3 Scenes)</option>
                    <option value={45}>45 Seconds (4 Scenes)</option>
                    <option value={55}>55 Seconds (5 Scenes)</option>
                  </>
                ) : (
                  <>
                    <option value={20}>20 Seconds (2 Scenes)</option>
                    <option value={30}>30 Seconds (3 Scenes)</option>
                    <option value={60}>60 Seconds (6 Scenes)</option>
                    <option value={120}>2 Minutes (12 Scenes)</option>
                    <option value={180}>3 Minutes (18 Scenes)</option>
                    <option value={300}>5 Minutes (30 Scenes)</option>
                  </>
                )}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label>Main Topic</label>
              <input 
                type="text" 
                value={topic} 
                onChange={e => setTopic(e.target.value)} 
                placeholder="e.g. History of AI, Space Exploration"
              />
            </div>

            <div className="form-group">
              <label>Category / Niche (30+ Categories)</label>
              <select value={category} onChange={e => setCategory(e.target.value)}>
                {CATEGORIES.map((cat, i) => (
                  <option key={i} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          </div>

          {category === '✍️ Custom Category (Type Below)' && (
            <div className="form-group">
              <label>Custom Category / Niche Name</label>
              <input 
                type="text" 
                value={customCategory} 
                onChange={e => setCustomCategory(e.target.value)} 
                placeholder="Type your custom niche (e.g. Cyberpunk Anime, Ancient Rome)"
              />
            </div>
          )}

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
            <label>Font Family (30+ Custom Fonts)</label>
            <select value={fontName} onChange={e => setFontName(e.target.value)}>
              {fontList.map((f, i) => (
                <option key={i} value={f}>{f.replace(/\.[^/.]+$/, "")}</option>
              ))}
            </select>
          </div>
          
          <div className="form-group">
            <label>🎵 Background Music Track</label>
            <select value={bgMusic} onChange={e => setBgMusic(e.target.value)}>
              {bgMusicList.map((m, i) => (
                <option key={i} value={m}>
                  {m === 'random' ? '🎲 Random Background Music' : (m === 'none' ? '🚫 No Background Music' : `🎵 ${m}`)}
                </option>
              ))}
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
            {jobStatus === 'processing' ? '⏳ Rendering Video in Background...' : '🚀 Generate Video'}
          </button>

          {jobStatus && (
            <div style={{ marginTop: '1.5rem', textAlign: 'center', background: 'rgba(255, 255, 255, 0.04)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(168, 85, 247, 0.3)', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
              <div className={`status-badge status-${jobStatus}`} style={{ display: 'inline-block', padding: '6px 14px', borderRadius: '20px', fontSize: '0.85rem', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '12px' }}>
                Status: {jobStatus.toUpperCase()}
              </div>

              {jobStatus === 'processing' && (
                <div style={{ marginTop: '0.5rem' }}>
                  <lottie-player 
                    src="/loding.json" 
                    background="transparent" 
                    speed="1" 
                    style={{ width: '180px', height: '180px', margin: '0 auto', display: 'block' }} 
                    loop 
                    autoplay
                  ></lottie-player>
                  <h4 style={{ color: '#ffffff', fontSize: '1.15rem', marginTop: '10px', marginBottom: '6px', fontWeight: '800' }}>
                    🎬 Rendering Your AI Video...
                  </h4>
                  <p style={{ color: '#c084fc', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '6px' }}>
                    Combining Voice, Visual Clips, Subtitles & Background Music
                  </p>
                  <p style={{ color: '#94a3b8', fontSize: '0.8rem', margin: 0 }}>
                    💡 You can keep using the dashboard! Edit scripts, change settings, or view history while rendering proceeds.
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
          <YouTubeIntegration 
            userId={userId} 
            hasActiveSubscription={subStatus.has_active_subscription} 
            onUpgradeClick={() => setShowPricingModal(true)} 
          />
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

            <div className="sidebar-profile" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', background: 'rgba(255,255,255,0.04)', padding: '24px 16px', borderRadius: '20px', border: '1px solid rgba(168,85,247,0.3)', marginBottom: '18px' }}>
              <div style={{ position: 'relative', cursor: 'pointer', marginBottom: '12px' }} title="Click to change profile picture">
                {subStatus.profile_pic ? (
                  <img src={subStatus.profile_pic} alt="Profile" style={{ width: '76px', height: '76px', borderRadius: '50%', objectFit: 'cover', border: '3px solid #a855f7', boxShadow: '0 0 20px rgba(168,85,247,0.4)' }} />
                ) : (
                  <div className="profile-avatar" style={{ width: '76px', height: '76px', fontSize: '2.2rem', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #3b0764 0%, #6b21a8 100%)', borderRadius: '50%', color: '#c084fc', border: '3px solid #a855f7', boxShadow: '0 0 20px rgba(168,85,247,0.4)' }}>
                    {subStatus.name ? subStatus.name.charAt(0).toUpperCase() : '👤'}
                  </div>
                )}
                <label htmlFor="profile-pic-input" style={{ position: 'absolute', bottom: '0px', right: '0px', background: '#a855f7', color: 'white', borderRadius: '50%', width: '26px', height: '26px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.8rem', cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.6)' }}>
                  📷
                </label>
                <input 
                  id="profile-pic-input" 
                  type="file" 
                  accept="image/*" 
                  onChange={handleProfilePicUpload} 
                  style={{ display: 'none' }} 
                />
              </div>

              <h3 style={{ margin: '0 0 10px 0', fontSize: '1.25rem', color: '#ffffff', fontWeight: '800' }}>
                {subStatus.name || 'Account Active'}
              </h3>

              <div style={{ width: '100%', textAlign: 'left', background: 'rgba(0,0,0,0.25)', padding: '12px 14px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.82rem', color: '#cbd5e1', border: '1px solid rgba(255,255,255,0.06)' }}>
                {subStatus.email && <div>✉️ <span style={{ color: '#94a3b8' }}>Email:</span> <strong style={{ color: '#ffffff' }}>{subStatus.email}</strong></div>}
                {subStatus.phone && <div>📞 <span style={{ color: '#94a3b8' }}>Phone:</span> <strong style={{ color: '#ffffff' }}>{subStatus.phone}</strong></div>}
                {subStatus.country && <div>🌐 <span style={{ color: '#94a3b8' }}>Country:</span> <strong style={{ color: '#ffffff' }}>{subStatus.country}</strong></div>}
                <div>🆔 <span style={{ color: '#94a3b8' }}>ID:</span> <span style={{ color: '#a855f7', fontFamily: 'monospace' }}>{userId ? `${userId.substring(0, 12)}...` : 'Unknown'}</span></div>
                <div style={{ marginTop: '4px', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.1)', color: '#c084fc', fontWeight: 'bold', fontSize: '0.82rem' }}>
                  💎 {subStatus.has_active_subscription ? `Active Plan: ${subStatus.plan_type.toUpperCase()} (${subStatus.daily_limit_text || (subStatus.plan_type === 'combo' ? '2 Videos Daily: 1 Short + 1 Long' : '1 Video Daily')})` : `Free Demo Videos Left: ${subStatus.free_demo_count}/2`}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '15px' }}>
              <button 
                className="btn-upgrade-sidebar" 
                style={{ background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)', boxShadow: '0 4px 15px rgba(6, 182, 212, 0.4)' }}
                onClick={() => { setIsSidebarOpen(false); setShowAutoUploadModal(true); }}
              >
                ⚙️ Auto-Upload Settings
              </button>

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
                      <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                        <button 
                          className="history-watch-btn" 
                          style={{ flex: 1, padding: '6px 12px', fontSize: '0.8rem', border: 'none', borderRadius: '8px', cursor: 'pointer', background: 'linear-gradient(135deg, #a855f7 0%, #ec4899 100%)', color: 'white', fontWeight: 'bold' }}
                          onClick={() => setPlayingHistoryVideo({
                            topic: vid.topic || 'Untitled Video',
                            videoUrl: vid.cloudinary_url || `${API_BASE}/download/${vid.job_id}`,
                            downloadUrl: vid.cloudinary_url || `${API_BASE}/download/${vid.job_id}`
                          })}
                        >
                          ▶ Play Video In-App
                        </button>
                      </div>
                      {!vid.cloudinary_url && (
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
      {/* Big Clean Full-Screen Loading Animation Overlay */}
      {(isGeneratingScript || isPaymentProcessing) && (
        <div className="pricing-modal-overlay" style={{ zIndex: 4000, background: 'rgba(10, 7, 24, 0.85)', backdropFilter: 'blur(10px)' }}>
          <div style={{ maxWidth: '480px', textAlign: 'center', padding: '20px' }}>
            <lottie-player 
              src="/loding.json" 
              background="transparent" 
              speed="1" 
              style={{ width: '260px', height: '260px', margin: '0 auto', display: 'block' }} 
              loop 
              autoplay
            ></lottie-player>
            <h3 style={{ color: '#ffffff', fontSize: '1.5rem', marginTop: '14px', marginBottom: '8px', fontWeight: '800' }}>
              {isGeneratingScript ? 'Generating AI Video Script...' : 'Preparing Checkout...'}
            </h3>
            <p style={{ color: '#c084fc', fontSize: '0.95rem', fontWeight: 'bold', marginBottom: '6px' }}>
              Processing request via Cloxel AI Cloud
            </p>
            <p style={{ color: '#cbd5e1', fontSize: '0.85rem', margin: 0 }}>
              Please wait a moment while we process your request.
            </p>
          </div>
        </div>
      )}
      {/* In-App Video Player Modal for Video History */}
      {playingHistoryVideo && (
        <div className="pricing-modal-overlay" onClick={() => setPlayingHistoryVideo(null)} style={{ zIndex: 3000 }}>
          <div className="pricing-modal-card" style={{ maxWidth: '640px', padding: '32px 24px', textAlign: 'center' }} onClick={e => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setPlayingHistoryVideo(null)}>×</button>
            
            <h3 style={{ color: '#ffffff', fontSize: '1.3rem', marginBottom: '16px', fontWeight: '800' }}>
              🎬 {playingHistoryVideo.topic}
            </h3>

            <div style={{ borderRadius: '16px', overflow: 'hidden', background: '#000', marginBottom: '20px', border: '1px solid rgba(168,85,247,0.4)', boxShadow: '0 10px 30px rgba(0,0,0,0.8)' }}>
              <video 
                src={playingHistoryVideo.videoUrl} 
                controls 
                autoPlay 
                style={{ width: '100%', maxHeight: '65vh', display: 'block' }}
              ></video>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <a 
                href={playingHistoryVideo.downloadUrl} 
                target="_blank" 
                rel="noreferrer" 
                className="btn-hero-cta" 
                style={{ padding: '10px 20px', fontSize: '0.9rem', textDecoration: 'none' }}
              >
                ⬇ Download Video
              </a>
              <button 
                className="button secondary" 
                style={{ width: 'auto', padding: '10px 20px' }} 
                onClick={() => setPlayingHistoryVideo(null)}
              >
                Close Player
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Auto-Upload Settings Modal (Secret Page) */}
      {showAutoUploadModal && (
        <div className="pricing-modal-overlay" onClick={() => setShowAutoUploadModal(false)} style={{ zIndex: 3000 }}>
          <div className="pricing-modal-card" style={{ maxWidth: '680px', padding: '36px' }} onClick={e => e.stopPropagation()}>
            <button className="sidebar-close-btn" style={{ position: 'absolute', top: '20px', right: '20px', background: 'none', border: 'none', color: '#fff', fontSize: '1.8rem', cursor: 'pointer' }} onClick={() => setShowAutoUploadModal(false)}>×</button>

            <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '100%', marginBottom: '24px' }}>
              <span className="pricing-badge" style={{ background: 'rgba(6, 182, 212, 0.2)', color: '#38bdf8' }}>🤖 AUTOMATED YOUTUBE ENGINE</span>
              <h2 style={{ color: '#ffffff', fontSize: '1.8rem', marginTop: '8px', fontWeight: '800', textAlign: 'center', display: 'block', width: '100%', margin: '8px auto 0 auto' }}>
                Auto-Upload & Schedule Mode
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '0.85rem', textAlign: 'center', display: 'block', width: '100%', margin: '4px auto 0 auto' }}>
                Configure daily automatic video generation and YouTube channel publishing.
              </p>
            </div>

            {/* Current Active Plan Status Card */}
            <div style={{ background: 'rgba(255,255,255,0.04)', padding: '18px 20px', borderRadius: '16px', border: '1px solid rgba(6, 182, 212, 0.3)', marginBottom: '20px' }}>
              <h4 style={{ color: '#38bdf8', marginBottom: '10px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                💎 Active Membership Plan Status
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.85rem', color: '#cbd5e1' }}>
                <div><strong>Current Plan:</strong> <span style={{ color: '#c084fc', textTransform: 'uppercase', fontWeight: 'bold' }}>{subStatus.has_active_subscription ? `${subStatus.plan_type} (${autoSchedule.purchase_count || 1}x Stacked)` : 'Free Demo'}</span></div>
                <div><strong>Daily Video Limit:</strong> <span style={{ color: '#22c55e', fontWeight: 'bold' }}>{subStatus.daily_limit_text || (subStatus.plan_type === 'combo' ? '2 Videos Daily (1 Short + 1 Long)' : '1 Video Daily')}</span></div>
                <div><strong>Today Short Videos:</strong> <span style={{ color: '#38bdf8' }}>{subStatus.today_short_count || 0} / {subStatus.plan_type === 'combo' || subStatus.plan_type === 'short' ? '1' : '0'} Generated</span></div>
                <div><strong>Today Long Videos:</strong> <span style={{ color: '#38bdf8' }}>{subStatus.today_long_count || 0} / {subStatus.plan_type === 'combo' || subStatus.plan_type === 'long' ? '1' : '0'} Generated</span></div>
                <div><strong>Auto-Publish Target:</strong> <span style={{ color: '#ffffff' }}>YouTube Automation Engine</span></div>
                <div><strong>Total History Count:</strong> <span style={{ color: '#c084fc' }}>{history.length} Videos Saved</span></div>
              </div>
            </div>

            {/* Secret Auto-Generate Page Configuration Form */}
            <div style={{ background: 'rgba(0,0,0,0.35)', padding: '24px', borderRadius: '16px', border: '1px solid rgba(6, 182, 212, 0.3)', textAlign: 'left', marginBottom: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <span style={{ fontSize: '1.8rem' }}>🔐</span>
                <div>
                  <h3 style={{ color: '#ffffff', fontSize: '1.15rem', fontWeight: '800', margin: 0 }}>
                    Secret Auto-Generate Page Configuration
                  </h3>
                  <p style={{ color: '#94a3b8', fontSize: '0.8rem', margin: 0 }}>
                    Set exact video generation times & topics. All data syncs directly to your secure account.
                  </p>
                </div>
              </div>

              {/* Plan Video Counter Bar */}
              <div style={{ background: 'rgba(6, 182, 212, 0.1)', border: '1px solid rgba(6, 182, 212, 0.3)', borderRadius: '12px', padding: '12px 16px', marginBottom: '18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                <div><span style={{ color: '#94a3b8' }}>Elapsed Membership Days:</span> <strong style={{ color: '#ffffff' }}>{autoSchedule.total_videos_created} Days Passed</strong></div>
                <div><span style={{ color: '#94a3b8' }}>Total Stacked Plan Remaining:</span> <strong style={{ color: '#38bdf8' }}>{autoSchedule.remaining_plan_videos} / {autoSchedule.total_plan_allowance || (subStatus.plan_type === 'combo' ? 60 : 30)} Videos Left</strong></div>
              </div>

              {/* Auto Schedule Switch */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px', background: 'rgba(255,255,255,0.03)', padding: '12px 16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                <input 
                  type="checkbox" 
                  id="auto-schedule-enable"
                  checked={autoSchedule.schedule_enabled}
                  onChange={(e) => setAutoSchedule({ ...autoSchedule, schedule_enabled: e.target.checked })}
                  style={{ width: '18px', height: '18px', accentColor: '#06b6d4', cursor: 'pointer' }}
                />
                <label htmlFor="auto-schedule-enable" style={{ color: '#ffffff', fontWeight: 'bold', fontSize: '0.9rem', cursor: 'pointer' }}>
                  Enable Daily Automated AI Video Generation & YouTube Upload
                </label>
              </div>

              {/* 1. SHORT REEL SCHEDULE PROFILE (If Short Starter or Pro Combo) */}
              {(subStatus.plan_type === 'short' || subStatus.plan_type === 'combo') && (
                <div style={{ background: 'rgba(168,85,247,0.08)', padding: '18px', borderRadius: '14px', border: '1px solid rgba(168,85,247,0.3)', marginBottom: '20px' }}>
                  <h4 style={{ color: '#c084fc', marginBottom: '14px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    📱 9:16 Short Reels Automation Settings
                  </h4>

                  {/* Topic Choice */}
                  <div style={{ marginBottom: '14px' }}>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '6px' }}>
                      <input 
                        type="checkbox" 
                        id="short-auto-topic"
                        checked={autoSchedule.short_auto_topic !== false}
                        onChange={(e) => setAutoSchedule({ ...autoSchedule, short_auto_topic: e.target.checked })}
                        style={{ width: '16px', height: '16px', accentColor: '#a855f7' }}
                      />
                      <label htmlFor="short-auto-topic" style={{ color: '#ffffff', fontSize: '0.85rem', fontWeight: 'bold' }}>
                        🎲 Dynamic AI Auto-Topic (Everyday New Trending Topic)
                      </label>
                    </div>

                    {autoSchedule.short_auto_topic === false && (
                      <textarea 
                        rows="2"
                        value={autoSchedule.short_topic || ''}
                        onChange={(e) => setAutoSchedule({ ...autoSchedule, short_topic: e.target.value })}
                        placeholder="Enter custom Short topics separated by comma (e.g. Space Facts, Fitness Hacks)"
                        style={{ width: '100%', padding: '10px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#ffffff', fontSize: '0.85rem' }}
                      />
                    )}
                  </div>

                  {/* Short Voice, Font, Category, Color, Duration, Time */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.82rem' }}>
                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Category / Niche (30+ Options):</label>
                      <select value={autoSchedule.short_category || '🎲 Random / All Categories'} onChange={(e) => setAutoSchedule({ ...autoSchedule, short_category: e.target.value })} style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}>
                        {CATEGORIES.map((cat, i) => (
                          <option key={i} value={cat}>{cat}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Voice:</label>
                      <select value={autoSchedule.short_voice || 'hi-IN-MadhurNeural'} onChange={(e) => setAutoSchedule({ ...autoSchedule, short_voice: e.target.value })} style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}>
                        <option value="hi-IN-MadhurNeural">Madhur (Male, Hindi)</option>
                        <option value="hi-IN-SwaraNeural">Swara (Female, Hindi)</option>
                        <option value="en-US-GuyNeural">Guy (Male, English)</option>
                        <option value="en-US-JennyNeural">Jenny (Female, English)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Font Family:</label>
                      <select value={autoSchedule.short_font || 'Arial.ttf'} onChange={(e) => setAutoSchedule({ ...autoSchedule, short_font: e.target.value })} style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}>
                        {fontList.map((f, i) => (
                          <option key={i} value={f}>{f.replace(/\.[^/.]+$/, "")}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Reel Duration (10s - 55s Max):</label>
                      <input 
                        type="number" 
                        min="10" 
                        max="55" 
                        value={autoSchedule.short_duration || 30} 
                        onChange={(e) => setAutoSchedule({ ...autoSchedule, short_duration: Math.min(55, Math.max(10, Number(e.target.value))) })}
                        style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}
                      />
                    </div>

                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Daily Upload Time (24h):</label>
                      <input 
                        type="time" 
                        value={autoSchedule.short_time || '10:00'} 
                        onChange={(e) => setAutoSchedule({ ...autoSchedule, short_time: e.target.value })}
                        style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* 2. LONG VIDEO SCHEDULE PROFILE (If Long Master or Pro Combo) */}
              {(subStatus.plan_type === 'long' || subStatus.plan_type === 'combo') && (
                <div style={{ background: 'rgba(6,182,212,0.08)', padding: '18px', borderRadius: '14px', border: '1px solid rgba(6,182,212,0.3)', marginBottom: '20px' }}>
                  <h4 style={{ color: '#38bdf8', marginBottom: '14px', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    🖥️ 16:9 Long Video Automation Settings
                  </h4>

                  {/* Topic Choice */}
                  <div style={{ marginBottom: '14px' }}>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '6px' }}>
                      <input 
                        type="checkbox" 
                        id="long-auto-topic"
                        checked={autoSchedule.long_auto_topic !== false}
                        onChange={(e) => setAutoSchedule({ ...autoSchedule, long_auto_topic: e.target.checked })}
                        style={{ width: '16px', height: '16px', accentColor: '#06b6d4' }}
                      />
                      <label htmlFor="long-auto-topic" style={{ color: '#ffffff', fontSize: '0.85rem', fontWeight: 'bold' }}>
                        🎲 Dynamic AI Auto-Topic (Everyday New Deep-Dive Topic)
                      </label>
                    </div>

                    {autoSchedule.long_auto_topic === false && (
                      <textarea 
                        rows="2"
                        value={autoSchedule.long_topic || ''}
                        onChange={(e) => setAutoSchedule({ ...autoSchedule, long_topic: e.target.value })}
                        placeholder="Enter custom Long Video topics separated by comma (e.g. Ancient Mysteries, AI Revolution)"
                        style={{ width: '100%', padding: '10px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '8px', color: '#ffffff', fontSize: '0.85rem' }}
                      />
                    )}
                  </div>

                  {/* Long Voice, Font, Category, Color, Duration, Time */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.82rem' }}>
                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Category / Niche (30+ Options):</label>
                      <select value={autoSchedule.long_category || '🎲 Random / All Categories'} onChange={(e) => setAutoSchedule({ ...autoSchedule, long_category: e.target.value })} style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}>
                        {CATEGORIES.map((cat, i) => (
                          <option key={i} value={cat}>{cat}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Voice:</label>
                      <select value={autoSchedule.long_voice || 'hi-IN-MadhurNeural'} onChange={(e) => setAutoSchedule({ ...autoSchedule, long_voice: e.target.value })} style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}>
                        <option value="hi-IN-MadhurNeural">Madhur (Male, Hindi)</option>
                        <option value="hi-IN-SwaraNeural">Swara (Female, Hindi)</option>
                        <option value="en-US-GuyNeural">Guy (Male, English)</option>
                        <option value="en-US-JennyNeural">Jenny (Female, English)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Font Family:</label>
                      <select value={autoSchedule.long_font || 'Arial.ttf'} onChange={(e) => setAutoSchedule({ ...autoSchedule, long_font: e.target.value })} style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}>
                        {fontList.map((f, i) => (
                          <option key={i} value={f}>{f.replace(/\.[^/.]+$/, "")}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Video Duration (20s - 300s / 5m Max):</label>
                      <input 
                        type="number" 
                        min="20" 
                        max="300" 
                        value={autoSchedule.long_duration || 60} 
                        onChange={(e) => setAutoSchedule({ ...autoSchedule, long_duration: Math.min(300, Math.max(20, Number(e.target.value))) })}
                        style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}
                      />
                    </div>

                    <div>
                      <label style={{ color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>Daily Upload Time (24h):</label>
                      <input 
                        type="time" 
                        value={autoSchedule.long_time || '18:00'} 
                        onChange={(e) => setAutoSchedule({ ...autoSchedule, long_time: e.target.value })}
                        style={{ width: '100%', padding: '8px', background: '#1e1738', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', borderRadius: '8px' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {subStatus.has_active_subscription ? (
                autoSchedule.schedule_enabled ? (
                  <button 
                    className="btn-hero-cta" 
                    style={{ width: '100%', padding: '14px', fontSize: '1rem', background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', boxShadow: '0 4px 20px rgba(239, 68, 68, 0.4)' }}
                    onClick={() => setShowStopScheduleWarningModal(true)}
                  >
                    🛑 Stop Auto-Publishing Engine →
                  </button>
                ) : (
                  <button 
                    className="btn-hero-cta" 
                    style={{ width: '100%', padding: '14px', fontSize: '1rem', background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)', boxShadow: '0 4px 20px rgba(6, 182, 212, 0.4)' }}
                    onClick={() => handleSaveAutoSchedule(true)}
                  >
                    ⚡ Start Auto-Publishing Engine →
                  </button>
                )
              ) : (
                <button 
                  className="btn-hero-cta" 
                  style={{ width: '100%', padding: '14px', fontSize: '0.92rem', background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', boxShadow: '0 4px 20px rgba(239, 68, 68, 0.4)', opacity: 0.95 }}
                  onClick={() => {
                    setShowAutoUploadModal(false);
                    setShowPricingModal(true);
                  }}
                >
                  🔒 Active Membership Required — Click to Upgrade Plan & Unlock Auto-Schedule 💎
                </button>
              )}
            </div>

            <div style={{ textAlign: 'center' }}>
              <button className="button secondary" style={{ width: 'auto', padding: '8px 24px' }} onClick={() => setShowAutoUploadModal(false)}>
                Close Settings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stop Auto-Publishing Confirmation Warning Modal */}
      {showStopScheduleWarningModal && (
        <div className="pricing-modal-overlay" style={{ zIndex: 4000 }} onClick={() => setShowStopScheduleWarningModal(false)}>
          <div 
            style={{ 
              maxWidth: '460px', 
              width: '90%',
              padding: '32px 28px', 
              textAlign: 'center',
              background: 'rgba(255, 255, 255, 0.04)', 
              borderRadius: '24px', 
              border: '1px solid rgba(239, 68, 68, 0.45)', 
              boxShadow: '0 20px 50px rgba(239, 68, 68, 0.25)', 
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)'
            }} 
            onClick={e => e.stopPropagation()}
          >
            <div style={{ fontSize: '3rem', marginBottom: '12px' }}>⚠️</div>
            <h3 style={{ color: '#ef4444', fontSize: '1.4rem', fontWeight: '800', marginBottom: '12px' }}>
              Stop Auto-Publishing Warning
            </h3>
            <p style={{ color: '#cbd5e1', fontSize: '0.92rem', lineHeight: '1.5', marginBottom: '24px' }}>
              If you stop auto-publishing now, your automated daily video generation and YouTube channel publishing will be <strong>completely STOPPED</strong>.<br/><br/>
              When you re-enable it in the future, you will need to re-configure your daily upload schedule. Are you sure you want to stop?
            </p>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button 
                className="button secondary" 
                style={{ flex: 1, padding: '12px' }}
                onClick={() => setShowStopScheduleWarningModal(false)}
              >
                Cancel / Keep Active
              </button>
              <button 
                className="button" 
                style={{ flex: 1, padding: '12px', background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', color: '#fff', border: 'none', fontWeight: 'bold' }}
                onClick={() => handleSaveAutoSchedule(false)}
              >
                🛑 Yes, Stop Everything Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom Glassmorphism Transparent Warning & Alert Modal */}
      {customAlert && (
        <div 
          className="pricing-modal-overlay" 
          style={{ zIndex: 5000, background: 'rgba(10, 7, 24, 0.45)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)' }}
          onClick={() => setCustomAlert(null)}
        >
          <div 
            style={{ 
              maxWidth: '460px', 
              width: '90%',
              padding: '36px 28px', 
              textAlign: 'center', 
              background: 'rgba(255, 255, 255, 0.04)', 
              borderRadius: '24px', 
              border: customAlert.type === 'danger' ? '1px solid rgba(239, 68, 68, 0.45)' : (customAlert.type === 'success' ? '1px solid rgba(34, 197, 94, 0.45)' : '1px solid rgba(168, 85, 247, 0.45)'), 
              boxShadow: customAlert.type === 'danger' ? '0 20px 50px rgba(239, 68, 68, 0.25)' : '0 20px 50px rgba(168, 85, 247, 0.25)', 
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)'
            }} 
            onClick={e => e.stopPropagation()}
          >
            <div style={{ fontSize: '3.2rem', marginBottom: '14px', filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.5))' }}>
              {customAlert.icon || '⚠️'}
            </div>
            
            <h3 style={{ color: customAlert.type === 'danger' ? '#ef4444' : (customAlert.type === 'success' ? '#22c55e' : '#ffffff'), fontSize: '1.4rem', fontWeight: '800', marginBottom: '12px' }}>
              {customAlert.title}
            </h3>
            
            <div style={{ color: '#e2e8f0', fontSize: '0.92rem', lineHeight: '1.55', marginBottom: '28px', whiteSpace: 'pre-line' }}>
              {customAlert.message}
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              {customAlert.onConfirm ? (
                <>
                  <button 
                    className="button secondary" 
                    style={{ flex: 1, padding: '12px', borderRadius: '12px', background: 'rgba(255, 255, 255, 0.08)', color: '#cbd5e1', border: '1px solid rgba(255, 255, 255, 0.15)' }}
                    onClick={() => setCustomAlert(null)}
                  >
                    {customAlert.cancelText || 'Cancel'}
                  </button>
                  <button 
                    className="button" 
                    style={{ 
                      flex: 1, 
                      padding: '12px', 
                      borderRadius: '12px', 
                      background: customAlert.type === 'danger' ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' : 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)', 
                      color: '#ffffff', 
                      border: 'none', 
                      fontWeight: 'bold',
                      boxShadow: '0 4px 15px rgba(0,0,0,0.3)'
                    }}
                    onClick={() => {
                      const cb = customAlert.onConfirm;
                      setCustomAlert(null);
                      if (cb) cb();
                    }}
                  >
                    {customAlert.confirmText || 'Confirm'}
                  </button>
                </>
              ) : (
                <button 
                  className="button" 
                  style={{ 
                    width: '100%', 
                    padding: '13px', 
                    borderRadius: '12px', 
                    background: customAlert.type === 'danger' ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' : (customAlert.type === 'success' ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' : 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)'), 
                    color: '#ffffff', 
                    border: 'none', 
                    fontWeight: 'bold',
                    fontSize: '0.95rem'
                  }}
                  onClick={() => setCustomAlert(null)}
                >
                  {customAlert.confirmText || 'Got It →'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
