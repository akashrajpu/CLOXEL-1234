import re
import time
import json
import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Configure Firewall Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CloxelWAF")

# ==============================================================================
# 🛡️ CLOXEL ULTIMATE WEB APPLICATION FIREWALL (WAF) & THREAT SHIELD
# ==============================================================================

class ThreatSignatures:
    """
    Comprehensive attack signature repository covering SQLi, NoSQLi, XSS, RCE,
    Path Traversal, LFI/RFI, and Malicious Scanners.
    """
    
    # 1. SQL Injection (SQLi) Patterns
    SQLI_PATTERNS = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|UNION|GRANT|REVOKE)\b)", re.IGNORECASE),
        re.compile(r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)", re.IGNORECASE),
        re.compile(r"(\bOR\b\s+['\"]?[a-zA-Z]+['\"]?\s*=\s*['\"]?[a-zA-Z]+)", re.IGNORECASE),
        re.compile(r"(--\s*|#|/\*|\*/)", re.IGNORECASE),
        re.compile(r"(\b(INFORMATION_SCHEMA|BENCHMARK|SLEEP|WAITFOR|PG_SLEEP)\b)", re.IGNORECASE),
        re.compile(r"('|\")\s*(OR|AND)\s*('|\")?\d+('|\")?\s*=\s*('|\")?\d+", re.IGNORECASE),
    ]

    # 2. NoSQL Injection (MongoDB) Patterns
    NOSQLI_PATTERNS = [
        re.compile(r"(\$where|\$regex|\$gt|\$gte|\$lt|\$lte|\$ne|\$nin|\$exists|\$or|\$and|\$not)", re.IGNORECASE),
        re.compile(r"(this\.[a-zA-Z0-9_]+\s*==\s*this\.[a-zA-Z0-9_]+)", re.IGNORECASE),
        re.compile(r"(\{\$ne:\s*null\}|\{\$gt:\s*\"\"\}|\{\$exists:\s*true\})", re.IGNORECASE),
    ]

    # 3. Cross-Site Scripting (XSS) Patterns
    XSS_PATTERNS = [
        re.compile(r"(<script[^>]*>.*?</script>)", re.IGNORECASE),
        re.compile(r"(javascript\s*:|vbscript\s*:|data\s*:text/html)", re.IGNORECASE),
        re.compile(r"(on(load|error|click|mouseover|focus|blur|keydown|submit)\s*=)", re.IGNORECASE),
        re.compile(r"(eval\s*\(|document\.cookie|document\.location|window\.location)", re.IGNORECASE),
        re.compile(r"(<iframe|<object|<embed|<applet|<meta|<link)", re.IGNORECASE),
    ]

    # 4. Remote Code Execution (RCE) / Command Injection Patterns
    RCE_PATTERNS = [
        re.compile(r"(;\s*(cat|ls|pwd|whoami|id|uname|nc|netcat|curl|wget|bash|sh|zsh|powershell|cmd)\b)", re.IGNORECASE),
        re.compile(r"(\|\s*(cat|ls|pwd|whoami|id|nc|curl|wget|bash|sh)\b)", re.IGNORECASE),
        re.compile(r"(`[^`]+`|\$\([^)]+\))"),
        re.compile(r"(system\(|exec\(|passthru\(|shell_exec\(|popen\(|proc_open\()", re.IGNORECASE),
        re.compile(r"(/etc/passwd|/etc/shadow|/etc/group|/proc/self/environ|c:\\boot\.ini)", re.IGNORECASE),
    ]

    # 5. Path Traversal & LFI/RFI Patterns
    TRAVERSAL_PATTERNS = [
        re.compile(r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f)", re.IGNORECASE),
        re.compile(r"(file://|php://|zlib://|data://|glob://|expect://)", re.IGNORECASE),
        re.compile(r"(/WEB-INF/|/META-INF/|\.env|\.git/|\.htaccess)", re.IGNORECASE),
    ]

    # 6. Malicious User-Agent & Scanner Fingerprints
    MALICIOUS_BOTS = [
        "sqlmap", "nikto", "nmap", "acunetix", "havij", "dirbuster", "gobuster", 
        "masscan", "w3af", "netsparker", "zgrab", "zmap", "fimap", "commix", 
        "hydra", "medusa", "john", "burpsuite", "owasp", "metasploit"
    ]


class SecurityFirewall:
    """
    Core WAF Engine: Handles IP Rate Limiting, Threat Scoring, IP Blacklisting,
    Request Inspection, and OWASP Security Headers.
    """
    def __init__(self):
        # IP Rate Limiting: ip -> list of timestamps
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        
        # IP Threat Scores: ip -> score
        self.threat_scores: Dict[str, int] = defaultdict(int)
        
        # Blacklisted IPs: ip -> ban_expiry_timestamp
        self.banned_ips: Dict[str, float] = {}
        
        # Attack Counters for Security Monitoring
        self.attack_stats = {
            "sqli_blocked": 0,
            "nosqli_blocked": 0,
            "xss_blocked": 0,
            "rce_blocked": 0,
            "traversal_blocked": 0,
            "scanner_blocked": 0,
            "rate_limit_blocked": 0,
            "total_threats_blocked": 0
        }

    def clean_old_history(self, ip: str, window_seconds: float = 60.0):
        """Removes request timestamps older than window_seconds."""
        now = time.time()
        self.request_history[ip] = [ts for ts in self.request_history[ip] if now - ts < window_seconds]

    def is_banned(self, ip: str) -> bool:
        """Checks if an IP is currently banned."""
        now = time.time()
        if ip in self.banned_ips:
            if now < self.banned_ips[ip]:
                return True
            else:
                # Ban expired
                del self.banned_ips[ip]
                self.threat_scores[ip] = 0
        return False

    def ban_ip(self, ip: str, duration_seconds: int = 3600):
        """Bans a hostile IP for the specified duration (default: 1 hour)."""
        self.banned_ips[ip] = time.time() + duration_seconds
        logger.warning(f"🚫 [FIREWALL BANNED IP] IP {ip} has been BANNED for {duration_seconds}s due to severe threat activity.")

    def record_threat(self, ip: str, threat_type: str, weight: int = 2):
        """Increments threat score for an IP and triggers auto-ban if threshold reached."""
        self.threat_scores[ip] += weight
        self.attack_stats[threat_type] = self.attack_stats.get(threat_type, 0) + 1
        self.attack_stats["total_threats_blocked"] += 1
        
        logger.warning(f"🚨 [FIREWALL DETECTED THREAT] Type: {threat_type.upper()} | IP: {ip} | Total Threat Score: {self.threat_scores[ip]}")
        
        # Auto-ban if threat score exceeds threshold (e.g. >= 5 points)
        if self.threat_scores[ip] >= 5:
            self.ban_ip(ip, duration_seconds=3600)

    def check_rate_limit(self, ip: str, path: str) -> bool:
        """
        Enforces strict sliding window rate limits based on path sensitivity.
        - Auth/Payment routes: 10 requests / min
        - Render/Script routes: 15 requests / min
        - General API routes: 120 requests / min
        """
        self.clean_old_history(ip, 60.0)
        req_count = len(self.request_history[ip])

        if any(auth_path in path for auth_path in ["/login", "/register", "/create-razorpay-order", "/verify-razorpay-payment"]):
            max_limit = 10
        elif any(render_path in path for render_path in ["/generate-custom-video", "/generate-script", "/api/generate-ai-script"]):
            max_limit = 15
        else:
            max_limit = 120

        if req_count >= max_limit:
            self.record_threat(ip, "rate_limit_blocked", weight=1)
            return False

        self.request_history[ip].append(time.time())
        return True

    def inspect_text(self, text: str) -> Tuple[bool, str]:
        """
        Recursively scans string input against all WAF attack signature rules.
        Returns (is_malicious, threat_type).
        """
        if not text or not isinstance(text, str):
            return False, ""

        # 1. Scanner Check
        for bot in ThreatSignatures.MALICIOUS_BOTS:
            if bot in text.lower():
                return True, "scanner_blocked"

        # 2. Path Traversal
        for pattern in ThreatSignatures.TRAVERSAL_PATTERNS:
            if pattern.search(text):
                return True, "traversal_blocked"

        # 3. RCE / Command Injection
        for pattern in ThreatSignatures.RCE_PATTERNS:
            if pattern.search(text):
                return True, "rce_blocked"

        # 4. XSS Injection
        for pattern in ThreatSignatures.XSS_PATTERNS:
            if pattern.search(text):
                return True, "xss_blocked"

        # 5. SQL Injection
        for pattern in ThreatSignatures.SQLI_PATTERNS:
            if pattern.search(text):
                return True, "sqli_blocked"

        # 6. NoSQL Injection
        for pattern in ThreatSignatures.NOSQLI_PATTERNS:
            if pattern.search(text):
                return True, "nosqli_blocked"

        return False, ""

    def inspect_data(self, data) -> Tuple[bool, str]:
        """
        Deep recursive inspection of dicts, lists, numbers, and strings.
        """
        if isinstance(data, str):
            return self.inspect_text(data)
        elif isinstance(data, dict):
            for k, v in data.items():
                is_bad_key, threat_k = self.inspect_text(str(k))
                if is_bad_key:
                    return True, threat_k
                is_bad_val, threat_v = self.inspect_data(v)
                if is_bad_val:
                    return True, threat_v
        elif isinstance(data, list):
            for item in data:
                is_bad, threat = self.inspect_data(item)
                if is_bad:
                    return True, threat
        return False, ""


# Singleton WAF Instance
waf = SecurityFirewall()


# ==============================================================================
# 🧱 FASTAPI FIREWALL MIDDLEWARE IMPLEMENTATION
# ==============================================================================

class FirewallMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Identify Client IP Address (Handles reverse proxy headers: X-Forwarded-For)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        # 2. Banned IP Check (Instant 403 Block)
        if waf.is_banned(client_ip):
            logger.warning(f"🚫 [FIREWALL REJECTED BANNED IP] {client_ip} tried accessing {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": "blocked",
                    "error": "Access denied by Cloxel Security Shield. IP address has been flagged for malicious behavior.",
                    "ip": client_ip
                }
            )

        # 3. User-Agent Scanner Inspection
        user_agent = request.headers.get("User-Agent", "").lower()
        for bot in ThreatSignatures.MALICIOUS_BOTS:
            if bot in user_agent:
                waf.record_threat(client_ip, "scanner_blocked", weight=3)
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"status": "blocked", "error": "Automated security scanner detected and blocked."}
                )

        # 4. Rate Limiting Check
        if not waf.check_rate_limit(client_ip, request.url.path):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "rate_limited",
                    "error": "Too many requests. Please slow down and try again shortly."
                }
            )

        # 5. Query Parameter Threat Inspection
        for key, val in request.query_params.items():
            is_malicious, threat_type = waf.inspect_text(f"{key}={val}")
            if is_malicious:
                waf.record_threat(client_ip, threat_type, weight=2)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status": "blocked",
                        "error": f"Security Shield Flagged Request: Malicious payload pattern detected in query parameters."
                    }
                )

        # 6. Request Body Payload Threat Inspection (JSON / Form Data)
        if request.method in ["POST", "PUT", "PATCH"]:
            # Protect against huge payload memory exhaustion attacks (> 25MB)
            content_length = request.headers.get("Content-Length")
            if content_length and int(content_length) > 25 * 1024 * 1024:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"status": "blocked", "error": "Request payload exceeds 25MB safety limit."}
                )

            # Inspect JSON Body
            content_type = request.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    body_bytes = await request.body()
                    if body_bytes:
                        body_json = json.loads(body_bytes.decode("utf-8"))
                        is_malicious, threat_type = waf.inspect_data(body_json)
                        if is_malicious:
                            waf.record_threat(client_ip, threat_type, weight=3)
                            return JSONResponse(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                content={
                                    "status": "blocked",
                                    "error": f"Security Shield Flagged Request: Malicious attack pattern ({threat_type.upper()}) detected."
                                }
                            )

                        # Re-bind body stream for downstream route handlers
                        async def receive():
                            return {"type": "http.request", "body": body_bytes}

                        request._receive = receive
                except Exception:
                    pass

        # 7. Execute Downstream Request with Sanitized Error Handling
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            logger.error(f"❌ Internal Server Exception: {exc}", exc_info=True)
            # Never leak internal stack trace / sensitive DB credentials in production response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": "error",
                    "message": "An internal server error occurred. Our security system has safely logged this event."
                }
            )

        # 8. Attach OWASP Hardened Security Headers to Every Response
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval';"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Server Header Masking (Hide server fingerprints)
        response.headers["Server"] = "Cloxel-Secure-Shield/2.0"
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response
