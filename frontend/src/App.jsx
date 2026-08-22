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
  const [activeTab, setActiveTab] = useState('overview'); // 'overview', 'studio', 'autoupload', 'history', 'pricing'
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
    // 1. Complete Security Wipe: Clear all localStorage and sessionStorage
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch (e) {
      console.error("Error clearing browser storage:", e);
    }

    // 2. Reset all in-memory user states
    setUserId(null);
    setHistory([]);
    setFullScript('');
    setTopic('Space Exploration');
    setJobId(null);
    setJobStatus(null);
    setCloudinaryUrl(null);
    setDownloadUrl(null);
    setPlayingHistoryVideo(null);
    setSubStatus({ free_demo_count: 2, has_active_subscription: false, plan_type: 'none' });

    // 3. Hard page reload & redirect to origin for a clean fresh login state
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

  return (
    <div className="flux-outer-canvas">
      <div className="flux-container">
        
        {/* Left Sidebar Navigation (Matching Image Layout) */}
        <aside className="flux-sidebar">
          <div>
            <div className="flux-brand">
              ⚡ flux <span>.ai</span>
            </div>

            <ul className="flux-nav-list">
              <li 
                className={`flux-nav-item ${activeTab === 'overview' ? 'active' : ''}`} 
                onClick={() => setActiveTab('overview')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span>📊</span> Dashboard
                </div>
                <span className="flux-nav-badge">3</span>
              </li>

              <li 
                className={`flux-nav-item ${activeTab === 'studio' ? 'active' : ''}`} 
                onClick={() => setActiveTab('studio')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span>🎬</span> Home Studio
                </div>
              </li>

              <li 
                className={`flux-nav-item ${activeTab === 'autoupload' ? 'active' : ''}`} 
                onClick={() => setActiveTab('autoupload')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span>🤖</span> Auto-Upload
                </div>
                {autoSchedule.schedule_enabled && <span className="flux-nav-badge" style={{ background: '#d6f466', color: '#141026' }}>ON</span>}
              </li>

              <li 
                className={`flux-nav-item ${activeTab === 'history' ? 'active' : ''}`} 
                onClick={() => setActiveTab('history')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span>📜</span> Video Reports
                </div>
                <span className="flux-nav-badge">{history.length}</span>
              </li>

              <li 
                className={`flux-nav-item ${activeTab === 'pricing' ? 'active' : ''}`} 
                onClick={() => setActiveTab('pricing')}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span>💎</span> Membership
                </div>
              </li>
            </ul>
          </div>

          {/* Bottom Upgrade Banner (Matching Lime Card in Image!) */}
          <div className="flux-sidebar-upgrade-card">
            <h4>Upgrade to Pro 🚀</h4>
            <p>Upgrade your account for a fuller AI video creation experience.</p>
            <button className="flux-btn-upgrade-now" onClick={() => setShowPricingModal(true)}>
              Upgrade Now
            </button>
          </div>
        </aside>

        {/* Main Content Area (Light Silver Canvas) */}
        <main className="flux-content-canvas">
          
          {/* Top Bar Header (User profile, Search, Date badge) */}
          <div className="flux-topbar">
            <div className="flux-user-pill" onClick={() => setIsSidebarOpen(true)}>
              {subStatus.profile_pic ? (
                <img src={subStatus.profile_pic} className="flux-avatar" alt="User" />
              ) : (
                <div className="flux-avatar" style={{ background: '#141026', color: '#c084fc', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                  {subStatus.name ? subStatus.name.charAt(0).toUpperCase() : 'A'}
                </div>
              )}
              <div className="flux-user-info">
                <h5>{subStatus.name || 'Akash Raj'} ▾</h5>
                <p>{subStatus.email || 'contact@cloxel.com'}</p>
              </div>
            </div>

            <div className="flux-topbar-right">
              <div className="flux-search-box">
                <span>🔍</span>
                <input type="text" placeholder="Search videos, scripts..." />
              </div>

              <div className="flux-date-badge">
                📅 22 August, 2026 ▾
              </div>
            </div>
          </div>

          {/* TAB 1: OVERVIEW DASHBOARD (EXACT MATCH TO USER'S MOCKUP IMAGE!) */}
          {activeTab === 'overview' && (
            <div>
              <div style={{ marginBottom: '24px' }}>
                <h1 style={{ fontSize: '2.2rem', fontWeight: '900', color: '#141026', marginBottom: '4px' }}>
                  Production Overview
                </h1>
                <p style={{ color: '#64748b', fontSize: '0.95rem' }}>
                  Take control of your AI video generation today!
                </p>
              </div>

              {/* 3 Overview Top Stat Cards */}
              <div className="flux-overview-grid">
                
                {/* Card 1: Production Volume (Energy Used in image) */}
                <div className="flux-card">
                  <div className="flux-card-header">
                    <div className="flux-card-title">⚡ Production Volume</div>
                    <span style={{ fontSize: '1.2rem', color: '#94a3b8' }}>⋮</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                    <span style={{ fontSize: '2.4rem', fontWeight: '900', color: '#141026' }}>
                      {history.length + 12}k
                    </span>
                    <span style={{ background: '#d6f466', color: '#141026', padding: '2px 8px', borderRadius: '999px', fontSize: '0.75rem', fontWeight: '800' }}>
                      +15%
                    </span>
                  </div>
                  <p style={{ color: '#64748b', fontSize: '0.78rem', marginBottom: '10px' }}>videos rendered total</p>

                  {/* Overlapping Bubble Circles (Purple = Short, Dark = Long, Lime = Today) */}
                  <div className="flux-bubble-circles-container">
                    <div className="flux-bubble-purple">
                      <span style={{ fontSize: '1.4rem', fontWeight: '900' }}>2.6k</span>
                      <span style={{ fontSize: '0.7rem', opacity: 0.9 }}>Short Reels</span>
                    </div>

                    <div className="flux-bubble-dark">
                      <span style={{ fontSize: '1.2rem', fontWeight: '900' }}>1.2k</span>
                      <span style={{ fontSize: '0.65rem', opacity: 0.9 }}>Long Videos</span>
                    </div>

                    <div className="flux-bubble-lime">
                      <span style={{ fontSize: '1.1rem', fontWeight: '900' }}>500</span>
                      <span style={{ fontSize: '0.6rem', fontWeight: '700' }}>Today</span>
                    </div>
                  </div>

                  {/* Progress lines */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                      <span style={{ fontWeight: '800', color: '#141026' }}>45% <span style={{ fontWeight: '500', color: '#64748b' }}>Long Videos Target</span></span>
                      <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e' }}></span>
                    </div>
                    <div style={{ height: '6px', width: '100%', background: '#e2e8f0', borderRadius: '999px', overflow: 'hidden' }}>
                      <div style={{ width: '45%', height: '100%', background: '#22c55e' }}></div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                      <span style={{ fontWeight: '800', color: '#141026' }}>30% <span style={{ fontWeight: '500', color: '#64748b' }}>Short Reels Target (Begni)</span></span>
                      <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#c084fc' }}></span>
                    </div>
                    <div style={{ height: '6px', width: '100%', background: '#e2e8f0', borderRadius: '999px', overflow: 'hidden' }}>
                      <div style={{ width: '30%', height: '100%', background: '#c084fc' }}></div>
                    </div>
                  </div>
                </div>

                {/* Card 2: Upload Engine Status (Heart Rate & Activity in image) */}
                <div className="flux-card">
                  <div className="flux-card-header">
                    <div className="flux-card-title">🤖 Auto Engine Status</div>
                    <span style={{ fontSize: '1.2rem', color: '#94a3b8' }}>⋮</span>
                  </div>

                  <div style={{ marginBottom: '24px' }}>
                    <div style={{ fontSize: '2.2rem', fontWeight: '900', color: autoSchedule.schedule_enabled ? '#22c55e' : '#ef4444' }}>
                      {autoSchedule.schedule_enabled ? 'ACTIVE ⚡' : 'PAUSED 🛑'}
                    </div>
                    <p style={{ color: '#64748b', fontSize: '0.8rem' }}>YouTube Auto-Publishing Engine</p>
                  </div>

                  <hr style={{ border: 'none', borderTop: '1px solid #e2e8f0', margin: '16px 0' }} />

                  <div className="flux-card-header" style={{ marginBottom: '8px' }}>
                    <div className="flux-card-title">🏃 Daily Activity</div>
                    <span style={{ fontSize: '1.2rem', color: '#94a3b8' }}>⋮</span>
                  </div>
                  <div style={{ fontSize: '2rem', fontWeight: '900', color: '#141026' }}>
                    2 Videos <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#64748b' }}>Daily Target</span>
                  </div>
                  <p style={{ color: '#64748b', fontSize: '0.78rem' }}>Next Scheduled Upload: {autoSchedule.short_time || '10:00 AM'}</p>
                </div>

                {/* Card 3: Target Completion Index (Wellness Index in image) */}
                <div className="flux-card">
                  <div className="flux-card-header">
                    <div className="flux-card-title">% Monthly Hit Index</div>
                    <span style={{ fontSize: '1.2rem', color: '#94a3b8' }}>⋮</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '16px' }}>
                    <span style={{ fontSize: '2.5rem', fontWeight: '900', color: '#141026' }}>78%</span>
                    <span style={{ background: '#d6f466', color: '#141026', padding: '2px 8px', borderRadius: '999px', fontSize: '0.75rem', fontWeight: '800' }}>
                      +10%
                    </span>
                  </div>

                  {/* Dot Grid Matrix (Matching Image!) */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '8px', padding: '12px 0' }}>
                    {Array.from({ length: 28 }).map((_, i) => (
                      <div 
                        key={i} 
                        style={{ 
                          width: '10px', 
                          height: '10px', 
                          borderRadius: '50%', 
                          background: i % 3 === 0 ? '#c084fc' : (i % 2 === 0 ? '#d6f466' : '#cbd5e1') 
                        }}
                      />
                    ))}
                  </div>
                </div>

                {/* Dark Chart Card (Sleep Analysis in Image!) */}
                <div className="flux-dark-chart-card">
                  <div className="flux-dark-chart-header">
                    <div>
                      <h3 style={{ fontSize: '1.25rem', fontWeight: '800', margin: '0 0 4px 0', color: '#ffffff' }}>
                        🌙 Monthly Video Breakdown
                      </h3>
                      <p style={{ color: '#94a3b8', fontSize: '0.82rem', margin: 0 }}>
                        Green Bar = Long Videos | Purple Bar (Begni) = Short Reels
                      </p>
                    </div>

                    <div style={{ background: 'rgba(255,255,255,0.1)', padding: '6px 14px', borderRadius: '999px', fontSize: '0.82rem', color: '#ffffff', fontWeight: '600' }}>
                      Monthly ▾
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '32px', marginBottom: '20px' }}>
                    <div>
                      <div style={{ fontSize: '1.6rem', fontWeight: '900', color: '#d6f466' }}>85%</div>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Long Target Efficiency</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '1.6rem', fontWeight: '900', color: '#c084fc' }}>7h 15m</div>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Total Render Duration</div>
                    </div>
                  </div>

                  {/* Monthly Dual Bar Graph (Jun to Dec) */}
                  <div className="flux-bar-graph-container">
                    {[
                      { m: 'Jun', lime: 60, purple: 45 },
                      { m: 'Jul', lime: 75, purple: 60 },
                      { m: 'Aug', lime: 50, purple: 40 },
                      { m: 'Sept ↗', lime: 110, purple: 85 },
                      { m: 'Oct', lime: 65, purple: 50 },
                      { m: 'Nov', lime: 80, purple: 70 },
                      { m: 'Dec', lime: 90, purple: 80 }
                    ].map((item, idx) => (
                      <div key={idx} className="flux-bar-group">
                        <div className="flux-bars-wrapper">
                          <div className="flux-bar-lime" style={{ height: `${item.lime}px` }} title={`Long Videos: ${item.lime}`} />
                          <div className="flux-bar-purple" style={{ height: `${item.purple}px` }} title={`Short Reels: ${item.purple}`} />
                        </div>
                        <span className="flux-month-label" style={{ fontWeight: item.m.includes('Sept') ? 'bold' : 'normal', color: item.m.includes('Sept') ? '#d6f466' : '#94a3b8' }}>
                          {item.m}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Side Card: Manual Studio vs Automation Breakdown */}
                <div className="flux-card" style={{ gridColumn: 'span 1' }}>
                  <div className="flux-card-header">
                    <div className="flux-card-title">🎥 Studio Breakdown</div>
                    <span style={{ fontSize: '1.2rem', color: '#94a3b8' }}>⋮</span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '10px' }}>
                    <div style={{ background: '#141026', color: '#ffffff', padding: '16px', borderRadius: '16px' }}>
                      <div style={{ fontSize: '0.8rem', color: '#d6f466', fontWeight: 'bold' }}>MANUAL STUDIO</div>
                      <div style={{ fontSize: '1.6rem', fontWeight: '900', marginTop: '4px' }}>{history.length} Videos</div>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>Custom studio generations</div>
                    </div>

                    <div style={{ background: '#f1f5f9', color: '#141026', padding: '16px', borderRadius: '16px' }}>
                      <div style={{ fontSize: '0.8rem', color: '#c084fc', fontWeight: 'bold' }}>AUTO ENGINE</div>
                      <div style={{ fontSize: '1.6rem', fontWeight: '900', marginTop: '4px' }}>24 Uploaded</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>Automated daily schedule</div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 2: HOME STUDIO (AI VIDEO GENERATOR & SCRIPT EDITOR) */}
          {activeTab === 'studio' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
              <div style={{ background: '#ffffff', padding: '24px', borderRadius: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.03)' }}>
                <h2 style={{ fontSize: '1.4rem', fontWeight: '800', color: '#141026', marginBottom: '20px' }}>
                  🎬 Script & Content Studio
                </h2>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                  <div className="form-group">
                    <label style={{ color: '#141026', fontWeight: '700' }}>Video Format</label>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                      <button 
                        className={`button ${videoType === 'short' ? 'primary' : 'secondary'}`}
                        onClick={() => { setVideoType('short'); if (duration > 55) setDuration(30); }}
                        style={{ flex: 1, background: videoType === 'short' ? '#c084fc' : '#e2e8f0', color: videoType === 'short' ? '#fff' : '#141026', fontWeight: 'bold' }}
                      >📱 Short (9:16)</button>
                      <button 
                        className={`button ${videoType === 'long' ? 'primary' : 'secondary'}`}
                        onClick={() => { setVideoType('long'); if (duration < 20) setDuration(60); }}
                        style={{ flex: 1, background: videoType === 'long' ? '#141026' : '#e2e8f0', color: videoType === 'long' ? '#fff' : '#141026', fontWeight: 'bold' }}
                      >🖥️ Long (16:9)</button>
                    </div>
                  </div>

                  <div className="form-group">
                    <label style={{ color: '#141026', fontWeight: '700' }}>Target Duration (Seconds)</label>
                    <select value={duration} onChange={(e) => setDuration(Number(e.target.value))} style={{ background: '#f8fafc', color: '#141026', border: '1px solid #cbd5e1' }}>
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

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                  <div className="form-group">
                    <label style={{ color: '#141026', fontWeight: '700' }}>Main Topic</label>
                    <input 
                      type="text" 
                      value={topic} 
                      onChange={e => setTopic(e.target.value)} 
                      placeholder="e.g. History of AI, Space Exploration"
                      style={{ background: '#f8fafc', color: '#141026', border: '1px solid #cbd5e1' }}
                    />
                  </div>

                  <div className="form-group">
                    <label style={{ color: '#141026', fontWeight: '700' }}>Category / Niche</label>
                    <select value={category} onChange={e => setCategory(e.target.value)} style={{ background: '#f8fafc', color: '#141026', border: '1px solid #cbd5e1' }}>
                      {CATEGORIES.map((cat, i) => (
                        <option key={i} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <button 
                  className="button" 
                  onClick={handleAutoGenerate}
                  disabled={isGeneratingScript}
                  style={{ width: '100%', marginBottom: '1.5rem', background: 'linear-gradient(135deg, #a855f7 0%, #3b82f6 100%)', color: 'white', fontWeight: 'bold', padding: '12px' }}
                >
                  {isGeneratingScript ? 'Generating Script via Gemini AI...' : '✨ Auto-Generate Script via AI'}
                </button>

                {videoType === 'long' ? (
                  <div className="form-group">
                    <label style={{ color: '#141026', fontWeight: '700' }}>Full Video Script</label>
                    <textarea 
                      rows={8}
                      value={fullScript}
                      onChange={e => setFullScript(e.target.value)}
                      placeholder="Paste or write your full video script here..."
                      style={{ background: '#f8fafc', color: '#141026', border: '1px solid #cbd5e1' }}
                    />
                  </div>
                ) : (
                  <div className="scenes-list">
                    {scenes.map((scene, index) => (
                      <div key={index} className="scene-card" style={{ borderLeft: '4px solid #c084fc', paddingLeft: '1rem', marginBottom: '1rem', background: '#f8fafc', padding: '12px', borderRadius: '12px' }}>
                        <h4 style={{ color: '#a855f7', marginBottom: '0.5rem' }}>Scene {index + 1} ({index * 10}s - {(index + 1) * 10}s)</h4>
                        <div className="form-group">
                          <textarea 
                            rows={2}
                            value={scene.text}
                            onChange={e => handleSceneChange(index, 'text', e.target.value)}
                            placeholder="Enter script text..."
                            style={{ background: '#ffffff', color: '#141026', border: '1px solid #cbd5e1' }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Video Settings Panel */}
              <div style={{ background: '#141026', color: '#ffffff', padding: '24px', borderRadius: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}>
                <h3 style={{ fontSize: '1.2rem', fontWeight: '800', marginBottom: '20px', color: '#d6f466' }}>
                  ⚙️ Video Settings
                </h3>

                <div className="form-group">
                  <label style={{ color: '#cbd5e1' }}>AI Voice</label>
                  <select value={voiceId} onChange={e => setVoiceId(e.target.value)} style={{ background: '#1e1738', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }}>
                    <option value="hi-IN-MadhurNeural">Madhur (Male, Hindi)</option>
                    <option value="hi-IN-SwaraNeural">Swara (Female, Hindi)</option>
                    <option value="en-US-GuyNeural">Guy (Male, English)</option>
                    <option value="en-US-JennyNeural">Jenny (Female, English)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label style={{ color: '#cbd5e1' }}>Font Family</label>
                  <select value={fontName} onChange={e => setFontName(e.target.value)} style={{ background: '#1e1738', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }}>
                    {fontList.map((f, i) => (
                      <option key={i} value={f}>{f.replace(/\.[^/.]+$/, "")}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label style={{ color: '#cbd5e1' }}>🎵 Background Music</label>
                  <select value={bgMusic} onChange={e => setBgMusic(e.target.value)} style={{ background: '#1e1738', color: '#fff', border: '1px solid rgba(255,255,255,0.15)' }}>
                    {bgMusicList.map((m, i) => (
                      <option key={i} value={m}>
                        {m === 'random' ? '🎲 Random Music' : (m === 'none' ? '🚫 No Music' : `🎵 ${m}`)}
                      </option>
                    ))}
                  </select>
                </div>

                <button 
                  className="button" 
                  onClick={handleGenerateVideo}
                  disabled={jobStatus === 'processing'}
                  style={{ marginTop: '1.5rem', width: '100%', background: '#d6f466', color: '#141026', fontWeight: 'bold', fontSize: '1rem' }}
                >
                  {jobStatus === 'processing' ? '⏳ Rendering Video...' : '🚀 Generate Video'}
                </button>

                {jobStatus && (
                  <div style={{ marginTop: '1rem', textAlign: 'center', background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '16px' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: '#d6f466' }}>
                      STATUS: {jobStatus.toUpperCase()}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: AUTO-UPLOAD SETTINGS */}
          {activeTab === 'autoupload' && (
            <div style={{ background: '#ffffff', padding: '28px', borderRadius: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.03)' }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: '800', color: '#141026', marginBottom: '20px' }}>
                🤖 YouTube Auto-Publishing Engine
              </h2>

              <YouTubeIntegration 
                userId={userId} 
                hasActiveSubscription={subStatus.has_active_subscription} 
                onUpgradeClick={() => setShowPricingModal(true)} 
              />

              <div style={{ marginTop: '24px', background: '#141026', color: '#ffffff', padding: '24px', borderRadius: '20px' }}>
                <h3 style={{ fontSize: '1.2rem', fontWeight: '800', color: '#d6f466', marginBottom: '16px' }}>
                  ⏱️ Daily Upload Timings & Categories
                </h3>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                  <div>
                    <h4 style={{ color: '#c084fc', marginBottom: '8px' }}>📱 Short Reel Automation</h4>
                    <p style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>Time: {autoSchedule.short_time || '10:00 AM'}</p>
                    <p style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>Duration: {autoSchedule.short_duration || 30}s</p>
                  </div>

                  <div>
                    <h4 style={{ color: '#22c55e', marginBottom: '8px' }}>🖥️ Long Video Automation</h4>
                    <p style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>Time: {autoSchedule.long_time || '06:00 PM'}</p>
                    <p style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>Duration: {autoSchedule.long_duration || 60}s</p>
                  </div>
                </div>

                <button 
                  className="button" 
                  style={{ marginTop: '20px', background: '#d6f466', color: '#141026', fontWeight: 'bold' }}
                  onClick={() => setShowAutoUploadModal(true)}
                >
                  ⚙️ Configure Secret Auto-Schedule Settings
                </button>
              </div>
            </div>
          )}

          {/* TAB 4: VIDEO HISTORY */}
          {activeTab === 'history' && (
            <div style={{ background: '#ffffff', padding: '28px', borderRadius: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.03)' }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: '800', color: '#141026', marginBottom: '20px' }}>
                📜 Video Reports & History ({history.length})
              </h2>

              {history.length === 0 ? (
                <p style={{ color: '#64748b' }}>No generated videos found. Create your first video in Home Studio!</p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '20px' }}>
                  {history.map((vid, idx) => (
                    <div key={idx} style={{ background: '#141026', color: '#fff', borderRadius: '16px', padding: '16px' }}>
                      <h4 style={{ fontSize: '0.95rem', fontWeight: '700', color: '#d6f466', marginBottom: '8px' }}>
                        {vid.topic || `Video #${idx + 1}`}
                      </h4>
                      <p style={{ fontSize: '0.78rem', color: '#cbd5e1', marginBottom: '12px' }}>
                        Type: {vid.type ? vid.type.toUpperCase() : 'SHORT'} | {vid.created_at ? new Date(vid.created_at).toLocaleDateString() : 'Recent'}
                      </p>
                      {vid.cloudinary_url && (
                        <a href={vid.cloudinary_url} target="_blank" rel="noreferrer" style={{ color: '#c084fc', fontSize: '0.85rem', fontWeight: 'bold' }}>
                          ▶ Play Video
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: MEMBERSHIP PLANS */}
          {activeTab === 'pricing' && (
            <div style={{ background: '#ffffff', padding: '28px', borderRadius: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.03)' }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: '800', color: '#141026', marginBottom: '20px' }}>
                💎 Membership Plans
              </h2>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px' }}>
                <div style={{ background: '#f8fafc', border: '2px solid #cbd5e1', padding: '24px', borderRadius: '20px', textAlign: 'center' }}>
                  <h3 style={{ color: '#141026' }}>Short Starter</h3>
                  <div style={{ fontSize: '2rem', fontWeight: '900', margin: '10px 0' }}>₹50 / mo</div>
                  <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '20px' }}>Daily 1 Short Reel for 30 Days</p>
                  <button className="button" style={{ background: '#141026', color: '#fff', width: '100%' }} onClick={() => handleBuyPlan('short')}>
                    Subscribe for ₹50
                  </button>
                </div>

                <div style={{ background: '#f8fafc', border: '2px solid #3b82f6', padding: '24px', borderRadius: '20px', textAlign: 'center' }}>
                  <h3 style={{ color: '#141026' }}>Long Master</h3>
                  <div style={{ fontSize: '2rem', fontWeight: '900', margin: '10px 0' }}>₹100 / mo</div>
                  <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '20px' }}>Daily 1 Long Video for 30 Days</p>
                  <button className="button" style={{ background: '#3b82f6', color: '#fff', width: '100%' }} onClick={() => handleBuyPlan('long')}>
                    Subscribe for ₹100
                  </button>
                </div>

                <div style={{ background: '#141026', color: '#fff', border: '2px solid #d6f466', padding: '24px', borderRadius: '20px', textAlign: 'center' }}>
                  <div style={{ background: '#d6f466', color: '#141026', padding: '2px 10px', borderRadius: '999px', fontSize: '0.75rem', fontWeight: 'bold', display: 'inline-block', marginBottom: '10px' }}>BEST VALUE</div>
                  <h3 style={{ color: '#ffffff' }}>Pro Combo</h3>
                  <div style={{ fontSize: '2rem', fontWeight: '900', margin: '10px 0', color: '#d6f466' }}>₹119 / mo</div>
                  <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '20px' }}>Daily 1 Short + 1 Long Video + Unlimited Studio</p>
                  <button className="button" style={{ background: '#d6f466', color: '#141026', fontWeight: 'bold', width: '100%' }} onClick={() => handleBuyPlan('combo')}>
                    Subscribe for ₹119
                  </button>
                </div>
              </div>
            </div>
          )}

        </main>
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

              <button className="btn-logout" onClick={handleLogout} style={{ marginTop: '16px', width: '100%' }}>
                🚪 Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stop Auto-Publishing Confirmation Warning Modal */}
      {showStopScheduleWarningModal && (
        <div className="pricing-modal-overlay" style={{ zIndex: 4000 }} onClick={() => setShowStopScheduleWarningModal(false)}>
          <div style={{ maxWidth: '460px', width: '90%', padding: '32px 28px', textAlign: 'center', background: 'rgba(255, 255, 255, 0.04)', borderRadius: '24px', border: '1px solid rgba(239, 68, 68, 0.45)', boxShadow: '0 20px 50px rgba(239, 68, 68, 0.25)', backdropFilter: 'blur(20px)' }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: '3rem', marginBottom: '12px' }}>⚠️</div>
            <h3 style={{ color: '#ef4444', fontSize: '1.4rem', fontWeight: '800', marginBottom: '12px' }}>
              Stop Auto-Publishing Warning
            </h3>
            <p style={{ color: '#cbd5e1', fontSize: '0.92rem', lineHeight: '1.5', marginBottom: '24px' }}>
              If you stop auto-publishing now, your automated daily video generation and YouTube channel publishing will be <strong>completely STOPPED</strong>.
            </p>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="button secondary" style={{ flex: 1, padding: '12px' }} onClick={() => setShowStopScheduleWarningModal(false)}>
                Cancel / Keep Active
              </button>
              <button className="button" style={{ flex: 1, padding: '12px', background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', color: '#fff', border: 'none', fontWeight: 'bold' }} onClick={() => handleSaveAutoSchedule(false)}>
                🛑 Yes, Stop Everything Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom Glassmorphism Transparent Warning & Alert Modal */}
      {customAlert && (
        <div className="pricing-modal-overlay" style={{ zIndex: 5000, background: 'rgba(10, 7, 24, 0.45)', backdropFilter: 'blur(16px)' }} onClick={() => setCustomAlert(null)}>
          <div style={{ maxWidth: '460px', width: '90%', padding: '36px 28px', textAlign: 'center', background: 'rgba(255, 255, 255, 0.04)', borderRadius: '24px', border: customAlert.type === 'danger' ? '1px solid rgba(239, 68, 68, 0.45)' : '1px solid rgba(168, 85, 247, 0.45)', backdropFilter: 'blur(20px)' }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: '3.2rem', marginBottom: '14px' }}>{customAlert.icon || '⚠️'}</div>
            <h3 style={{ color: customAlert.type === 'danger' ? '#ef4444' : '#ffffff', fontSize: '1.4rem', fontWeight: '800', marginBottom: '12px' }}>{customAlert.title}</h3>
            <div style={{ color: '#e2e8f0', fontSize: '0.92rem', lineHeight: '1.55', marginBottom: '28px' }}>{customAlert.message}</div>
            <button className="button" style={{ width: '100%', padding: '13px', background: customAlert.type === 'danger' ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' : 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)', color: '#fff' }} onClick={() => setCustomAlert(null)}>Got It →</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
