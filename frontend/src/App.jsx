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
  
  // Auth state
  const [userId, setUserId] = useState(() => localStorage.getItem('cloxel_user_id') || null);

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

  if (!userId) {
    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Cloxel <span>Video Generator</span></h1>
        <p>AI-powered Faceless Videos in Minutes</p>
        <button onClick={handleLogout} className="btn-secondary" style={{position: 'absolute', top: '20px', right: '20px', fontSize: '0.8rem'}}>Logout</button>
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

          {/* Video History Section */}
          {userId && history.length > 0 && (
            <div className="history-section" style={{ marginTop: '2rem', textAlign: 'left' }}>
              <h3>🕒 Your Video History</h3>
              <div className="history-grid">
                {history.map((vid, idx) => (
                  <div key={idx} className="history-card" style={{ padding: '0.5rem', border: '1px solid #ccc', marginBottom: '0.5rem' }}>
                    <p style={{ fontWeight: 'bold' }}>{vid.topic || 'Untitled'}</p>
                    {vid.cloudinary_url ? (
                      <a href={vid.cloudinary_url} target="_blank" rel="noreferrer">Watch Video</a>
                    ) : (
                      <span>Local file</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

        </aside>
      </div>
    </div>
  );
}

export default App;
