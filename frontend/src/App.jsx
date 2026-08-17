import React, { useState, useEffect } from 'react';

function App() {
  const [topic, setTopic] = useState('Space Exploration');
  const [duration, setDuration] = useState(20);
  const [videoType, setVideoType] = useState('short'); // 'short' or 'long'
  const [fullScript, setFullScript] = useState('');
  
  // Customization Settings
  const [fontName, setFontName] = useState('UTM Kabel KT.ttf');
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
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);

  // Update scenes array when duration changes
  useEffect(() => {
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
    
    try {
      const response = await fetch('https://cloxel.onrender.com/generate-custom-video', {
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
          full_script: fullScript
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
        const response = await fetch(`https://cloxel.onrender.com/status/${id}`);
        const data = await response.json();
        
        setJobStatus(data.status);
        
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          if (data.cloudinary_url) {
            setCloudinaryUrl(data.cloudinary_url);
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 5000);
  };

  return (
    <div className="app-container">
      <header>
        <h1>Zobbly AI Automation</h1>
        <p>Generate & Manage Your Automated Videos Seamlessly</p>
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
            {/* Duration slider ab dono me dikhega kyuki manual scene building ho rahi hai */}
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
              <option value="UTM Kabel KT.ttf">UTM Kabel KT</option>
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

          {cloudinaryUrl && (
            <div className="video-result">
              <video src={cloudinaryUrl} controls autoPlay loop muted></video>
              <a href={cloudinaryUrl} target="_blank" rel="noreferrer" className="download-link">
                Open in Cloudinary
              </a>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

export default App;
