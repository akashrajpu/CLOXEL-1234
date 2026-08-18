import React, { useState, useEffect } from 'react';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

function YouTubeIntegration({ userId }) {
  const [status, setStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/youtube/status/${userId}`);
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError("Failed to fetch YouTube status");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [userId]);

  const handleLink = async () => {
    try {
      const response = await fetch(`${API_BASE}/youtube/auth-url?internal_id=${userId}`);
      const data = await response.json();
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err) {
      alert("Failed to get authorization URL");
    }
  };

  const handleUnlink = async () => {
    if (!window.confirm("Are you sure you want to unlink your YouTube account?")) return;
    
    try {
      const response = await fetch(`${API_BASE}/youtube/unlink`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ internal_id: userId })
      });
      
      const data = await response.json();
      if (!response.ok) {
        alert(data.detail || "Failed to unlink");
      } else {
        alert("Successfully unlinked!");
        fetchStatus();
      }
    } catch (err) {
      alert("Error unlinking account");
    }
  };

  if (isLoading) return <div className="yt-card">Checking YouTube connection...</div>;

  return (
    <div className="yt-card">
      <h3>YouTube Auto-Upload</h3>
      <p className="yt-desc">Connect your YouTube account to automatically upload generated videos directly to your channel.</p>
      
      {status && status.linked ? (
        <div className="yt-status linked">
          <div className="yt-badge">✅ YouTube Account Linked</div>
          
          <div className="yt-actions">
            <button 
              className={`btn-unlink ${!status.can_unlink ? 'disabled' : ''}`}
              onClick={handleUnlink}
              disabled={!status.can_unlink}
            >
              Unlink Account
            </button>
            
            {!status.can_unlink && (
              <div className="yt-lock-msg">
                🔒 Locked for security. You can unlink in {status.hours_left} hours.
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="yt-status unlinked">
          <button className="btn-yt-link" onClick={handleLink}>
            Link YouTube Account
          </button>
          <div className="yt-security-note">
            Your credentials are kept strictly on our secure servers.
          </div>
        </div>
      )}
    </div>
  );
}

export default YouTubeIntegration;
