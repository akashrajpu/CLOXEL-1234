import React, { useState, useEffect } from 'react';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

function YouTubeIntegration({ userId, hasActiveSubscription, onUpgradeClick, onStatusChange, triggerAlert, compact = false }) {
  const [status, setStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/youtube/status/${userId}`);
      const data = await response.json();
      setStatus(data);
      if (onStatusChange) onStatusChange(data);
    } catch (err) {
      setError("Failed to fetch YouTube status");
      setStatus({ linked: false });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [userId]);

  const handleLink = async () => {
    if (!hasActiveSubscription) {
      if (triggerAlert) {
        triggerAlert(
          "Active Membership Required",
          "Connecting a YouTube account is exclusive to active paid members. Please upgrade your plan first!",
          "🔒",
          "danger",
          onUpgradeClick,
          "Upgrade Plan →"
        );
      } else {
        alert("🔒 Active Paid Membership Required! Please upgrade your plan first.");
        if (onUpgradeClick) onUpgradeClick();
      }
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/youtube/auth-url?internal_id=${userId}`);
      const data = await response.json();
      
      if (!response.ok) {
        if (triggerAlert) {
          triggerAlert("YouTube Error", data.detail || "Error connecting to YouTube API.", "⚠️", "danger");
        } else {
          alert(data.detail || "Error connecting to YouTube API.");
        }
        return;
      }
      
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err) {
      alert("Failed to get authorization URL. Is the backend running?");
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

  if (isLoading) return <div className="yt-card" style={{ padding: compact ? '10px' : '20px', fontSize: '0.85rem' }}>Checking YouTube connection...</div>;

  if (compact) {
    return (
      <div className="yt-card compact" style={{ padding: '12px 14px', borderRadius: '14px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 'bold', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>📺 YouTube Channel</span>
          </div>
          {status && status.linked && (
            <span style={{ background: 'rgba(34, 197, 94, 0.2)', color: '#22c55e', border: '1px solid rgba(34, 197, 94, 0.4)', padding: '2px 8px', borderRadius: '999px', fontSize: '0.72rem', fontWeight: 'bold' }}>
              ✅ Linked
            </span>
          )}
        </div>

        {status && status.linked ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Connected for Auto-Upload</span>
            <button 
              className={`btn-unlink ${!status.can_unlink ? 'disabled' : ''}`}
              onClick={handleUnlink}
              disabled={!status.can_unlink}
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
            >
              Unlink
            </button>
          </div>
        ) : (
          <button 
            className="btn-yt-link" 
            onClick={handleLink}
            style={{ width: '100%', padding: '8px', fontSize: '0.85rem', fontWeight: 'bold', background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', marginTop: '8px' }}
          >
            📺 Link YouTube Account
          </button>
        )}
      </div>
    );
  }

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
