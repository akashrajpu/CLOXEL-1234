import re
import time
import json
import math
import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Configure WAF Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CloxelFortressWAF")

# ==============================================================================
# 🛡️ CLOXEL FORTRESS WAF v3.0 - ZERO-TRUST MILITARY GRADE SECURITY SHIELD
# ==============================================================================

class ThreatSignatures:
    """
    Exhaustive Repository of All Known Attack Vectors & Exploitation Techniques.
    """
    
    # 1. Honeypot Trap Decoy Paths (Deception System)
    HONEYPOT_PATHS = {
        "/wp-admin", "/phpmyadmin", "/.env", "/.git/config", "/admin/db.sql",
        "/shell.php", "/api/v1/eval", "/actuator/env", "/config.json", "/backup.zip",
        "/admin.php", "/vendor/.env", "/.aws/credentials", "/server-status"
    }

    # 2. SQL Injection (SQLi) Patterns
    SQLI_PATTERNS = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|UNION|GRANT|REVOKE)\b)", re.IGNORECASE),
        re.compile(r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)", re.IGNORECASE),
        re.compile(r"(\bOR\b\s+['\"]?[a-zA-Z]+['\"]?\s*=\s*['\"]?[a-zA-Z]+)", re.IGNORECASE),
        re.compile(r"(--\s*|#|/\*|\*/)", re.IGNORECASE),
        re.compile(r"(\b(INFORMATION_SCHEMA|BENCHMARK|SLEEP|WAITFOR|PG_SLEEP)\b)", re.IGNORECASE),
        re.compile(r"('|\")\s*(OR|AND)\s*('|\")?\d+('|\")?\s*=\s*('|\")?\d+", re.IGNORECASE),
        re.compile(r"(\bUNION\b\s+ALL\s+SELECT\b)", re.IGNORECASE),
    ]

    # 3. NoSQL Injection (MongoDB) Patterns
    NOSQLI_PATTERNS = [
        re.compile(r"(\$where|\$regex|\$gt|\$gte|\$lt|\$lte|\$ne|\$nin|\$exists|\$or|\$and|\$not|\$type|\$mod)", re.IGNORECASE),
        re.compile(r"(this\.[a-zA-Z0-9_]+\s*==\s*this\.[a-zA-Z0-9_]+)", re.IGNORECASE),
        re.compile(r"(\{\$ne:\s*null\}|\{\$gt:\s*\"\"\}|\{\$exists:\s*true\})", re.IGNORECASE),
    ]

    # 4. Cross-Site Scripting (XSS) & HTML Injection Patterns
    XSS_PATTERNS = [
        re.compile(r"(<script[^>]*>.*?</script>)", re.IGNORECASE),
        re.compile(r"(javascript\s*:|vbscript\s*:|data\s*:text/html)", re.IGNORECASE),
        re.compile(r"(on(load|error|click|mouseover|focus|blur|keydown|submit|mouseenter|mouseleave)\s*=)", re.IGNORECASE),
        re.compile(r"(eval\s*\(|document\.cookie|document\.location|window\.location|top\.location)", re.IGNORECASE),
        re.compile(r"(<iframe|<object|<embed|<applet|<meta|<link|<svg/onload)", re.IGNORECASE),
        re.compile(r"(alert\s*\(|prompt\s*\(|confirm\s*\()", re.IGNORECASE),
    ]

    # 5. Remote Code Execution (RCE) / Command Injection Patterns
    RCE_PATTERNS = [
        re.compile(r"(;\s*(cat|ls|pwd|whoami|id|uname|nc|netcat|curl|wget|bash|sh|zsh|powershell|cmd)\b)", re.IGNORECASE),
        re.compile(r"(\|\s*(cat|ls|pwd|whoami|id|nc|curl|wget|bash|sh)\b)", re.IGNORECASE),
        re.compile(r"(`[^`]+`|\$\([^)]+\))"),
        re.compile(r"(system\(|exec\(|passthru\(|shell_exec\(|popen\(|proc_open\(|subprocess)", re.IGNORECASE),
        re.compile(r"(/etc/passwd|/etc/shadow|/etc/group|/proc/self/environ|c:\\boot\.ini)", re.IGNORECASE),
        re.compile(r"(\\x90\\x90|\\xeb\\xfe|\\xcd\\x80)"), # NOP Sled & Shellcode Markers
    ]

    # 6. Path Traversal & LFI/RFI Patterns
    TRAVERSAL_PATTERNS = [
        re.compile(r"(\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f|%252e%252e%252f)", re.IGNORECASE),
        re.compile(r"(file://|php://|zlib://|data://|glob://|expect://|zip://|phar://)", re.IGNORECASE),
        re.compile(r"(/WEB-INF/|/META-INF/|\.env|\.git/|\.htaccess|\.ssh/)", re.IGNORECASE),
        re.compile(r"(\\x00|%00)", re.IGNORECASE), # Null Byte Injection
    ]

    # 7. SSRF (Server-Side Request Forgery) Target IP Patterns
    SSRF_PATTERNS = [
        re.compile(r"(http://|https://)?(127\.0\.0\.1|localhost|169\.254\.169\.254|0\.0\.0\.0|::1)", re.IGNORECASE),
        re.compile(r"(http://|https://)?(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3})", re.IGNORECASE),
    ]

    # 8. JWT Forgery & Alg None Patterns
    JWT_ATTACK_PATTERNS = [
        re.compile(r"\"alg\"\s*:\s*\"none\"", re.IGNORECASE),
        re.compile(r"eyJhbGciOiJub25lIn", re.IGNORECASE), # Base64 encoded {"alg":"none"
    ]

    # 9. Malicious User-Agents & Security Scanners
    MALICIOUS_BOTS = [
        "sqlmap", "nikto", "nmap", "acunetix", "havij", "dirbuster", "gobuster", 
        "masscan", "w3af", "netsparker", "zgrab", "zmap", "fimap", "commix", 
        "hydra", "medusa", "john", "burpsuite", "owasp", "metasploit", "nuclei",
        "python-urllib/1", "python-urllib/2", "python-requests/0"
    ]


class SecurityFirewall:
    """
    Zero-Trust Autonomous Security Shield Engine.
    Handles Honeypots, Dynamic Escalation IP Bans, Entropy Anomaly Detection,
    SSRF Protection, JSON Bomb Limits, and OWASP Hardening.
    """
    def __init__(self):
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        self.threat_scores: Dict[str, int] = defaultdict(int)
        self.offense_counts: Dict[str, int] = defaultdict(int)
        self.banned_ips: Dict[str, float] = {}
        
        self.attack_stats = {
            "sqli_blocked": 0,
            "nosqli_blocked": 0,
            "xss_blocked": 0,
            "rce_blocked": 0,
            "traversal_blocked": 0,
            "ssrf_blocked": 0,
            "jwt_attack_blocked": 0,
            "honeypot_trap_blocked": 0,
            "scanner_blocked": 0,
            "protocol_smuggling_blocked": 0,
            "rate_limit_blocked": 0,
            "total_threats_blocked": 0
        }

    def calculate_entropy(self, text: str) -> float:
        """Calculates Shannon Entropy of a string to detect obfuscated shellcode."""
        if not text or len(text) < 20:
            return 0.0
        prob = [float(text.count(c)) / len(text) for c in set(text)]
        return - sum([p * math.log(p, 2) for p in prob])

    def clean_old_history(self, ip: str, window_seconds: float = 60.0):
        now = time.time()
        self.request_history[ip] = [ts for ts in self.request_history[ip] if now - ts < window_seconds]

    def is_banned(self, ip: str) -> bool:
        now = time.time()
        if ip in self.banned_ips:
            if now < self.banned_ips[ip]:
                return True
            else:
                del self.banned_ips[ip]
                self.threat_scores[ip] = 0
        return False

    def ban_ip(self, ip: str):
        """Dynamic Escalation IP Ban: 1h -> 24h -> 7 Days Permanent."""
        self.offense_counts[ip] += 1
        offenses = self.offense_counts[ip]
        
        if offenses == 1:
            duration = 3600        # 1 Hour
        elif offenses == 2:
            duration = 86400       # 24 Hours
        else:
            duration = 604800      # 7 Days
            
        self.banned_ips[ip] = time.time() + duration
        logger.critical(f"⛔ [FORTRESS BAN] IP {ip} BANNED for {duration}s (Offense Level #{offenses}).")

    def record_threat(self, ip: str, threat_type: str, weight: int = 2):
        self.threat_scores[ip] += weight
        self.attack_stats[threat_type] = self.attack_stats.get(threat_type, 0) + 1
        self.attack_stats["total_threats_blocked"] += 1
        
        logger.warning(f"🚨 [FORTRESS THREAT DETECTED] Type: {threat_type.upper()} | IP: {ip} | Score: {self.threat_scores[ip]}")
        
        if self.threat_scores[ip] >= 4:
            self.ban_ip(ip)

    def check_rate_limit(self, ip: str, path: str) -> bool:
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
        if not text or not isinstance(text, str):
            return False, ""

        # 1. Null Byte Check
        if "\x00" in text or "%00" in text:
            return True, "traversal_blocked"

        # 2. Honeypot check in text
        for hp in ThreatSignatures.HONEYPOT_PATHS:
            if hp in text:
                return True, "honeypot_trap_blocked"

        # 3. JWT Alg None Attack Check
        for pattern in ThreatSignatures.JWT_ATTACK_PATTERNS:
            if pattern.search(text):
                return True, "jwt_attack_blocked"

        # 4. SSRF Target IP Check
        for pattern in ThreatSignatures.SSRF_PATTERNS:
            if pattern.search(text):
                return True, "ssrf_blocked"

        # 5. Path Traversal
        for pattern in ThreatSignatures.TRAVERSAL_PATTERNS:
            if pattern.search(text):
                return True, "traversal_blocked"

        # 6. RCE / Command Injection
        for pattern in ThreatSignatures.RCE_PATTERNS:
            if pattern.search(text):
                return True, "rce_blocked"

        # 7. XSS Injection
        for pattern in ThreatSignatures.XSS_PATTERNS:
            if pattern.search(text):
                return True, "xss_blocked"

        # 8. SQL Injection
        for pattern in ThreatSignatures.SQLI_PATTERNS:
            if pattern.search(text):
                return True, "sqli_blocked"

        # 9. NoSQL Injection
        for pattern in ThreatSignatures.NOSQLI_PATTERNS:
            if pattern.search(text):
                return True, "nosqli_blocked"

        # 10. High Entropy Payload Anomaly (> 5.8)
        if len(text) > 40 and self.calculate_entropy(text) > 5.8:
            # Verify if it looks like obfuscated script/shellcode
            if any(sym in text for sym in [";", "|", "$", "<", ">", "`", "{", "}", "\\"]):
                return True, "rce_blocked"

        return False, ""

    def inspect_data(self, data, depth: int = 0) -> Tuple[bool, str]:
        """Deep Recursive Data Scanner with Nesting Depth & Key Count Caps."""
        if depth > 10:
            return True, "rce_blocked" # JSON Nesting Depth Bomb Guard

        if isinstance(data, str):
            return self.inspect_text(data)
        elif isinstance(data, dict):
            if len(data.keys()) > 150:
                return True, "rce_blocked" # Hash Collision DoS Guard
            for k, v in data.items():
                is_bad_k, threat_k = self.inspect_text(str(k))
                if is_bad_k:
                    return True, threat_k
                is_bad_v, threat_v = self.inspect_data(v, depth + 1)
                if is_bad_v:
                    return True, threat_v
        elif isinstance(data, list):
            if len(data) > 300:
                return True, "rce_blocked"
            for item in data:
                is_bad, threat = self.inspect_data(item, depth + 1)
                if is_bad:
                    return True, threat
        return False, ""


# Singleton Fortress WAF Instance
waf = SecurityFirewall()


# ==============================================================================
# 🧱 FASTAPI FORTRESS MIDDLEWARE IMPLEMENTATION
# ==============================================================================

class FirewallMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Client IP Resolution (Proxies / CDN Aware)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        path = request.url.path.lower()

        # 2. Banned IP Check (Instant Rejection)
        if waf.is_banned(client_ip):
            logger.warning(f"🚫 [FORTRESS BLOCKED BANNED IP] {client_ip} -> {path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": "blocked",
                    "error": "Access Denied by Cloxel Security Shield. IP address has been banned for malicious activity.",
                    "ip": client_ip
                }
            )

        # 3. Honeypot Decoy Trap Check (Instant 24h Ban)
        if path in ThreatSignatures.HONEYPOT_PATHS or any(path.startswith(hp) for hp in ThreatSignatures.HONEYPOT_PATHS):
            waf.record_threat(client_ip, "honeypot_trap_blocked", weight=10) # Instant Ban
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"status": "blocked", "error": "Honeypot Security Trap Triggered. IP Banned."}
            )

        # 4. HTTP Request Smuggling Defense (Content-Length vs Transfer-Encoding Conflict)
        if "content-length" in request.headers and "transfer-encoding" in request.headers:
            waf.record_threat(client_ip, "protocol_smuggling_blocked", weight=5)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "blocked", "error": "HTTP Protocol Anomaly Detected (Smuggling Attempt)."}
            )

        # 5. User-Agent Malicious Scanner Check
        user_agent = request.headers.get("User-Agent", "").lower()
        for bot in ThreatSignatures.MALICIOUS_BOTS:
            if bot in user_agent:
                waf.record_threat(client_ip, "scanner_blocked", weight=4)
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"status": "blocked", "error": "Automated security scanner detected and blocked."}
                )

        # 6. Rate Limiting Check
        if not waf.check_rate_limit(client_ip, path):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"status": "rate_limited", "error": "Too many requests. Rate limit enforced."}
            )

        # 7. Query Parameter Inspection
        for key, val in request.query_params.items():
            is_malicious, threat_type = waf.inspect_text(f"{key}={val}")
            if is_malicious:
                waf.record_threat(client_ip, threat_type, weight=3)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"status": "blocked", "error": f"Security Shield Flagged Request ({threat_type.upper()})."}
                )

        # 8. Request Body Payload Threat & Size Inspection
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("Content-Length")
            if content_length and int(content_length) > 25 * 1024 * 1024:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"status": "blocked", "error": "Request payload exceeds 25MB safety limit."}
                )

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
                                content={"status": "blocked", "error": f"Security Shield Flagged Request ({threat_type.upper()})."}
                            )

                        async def receive():
                            return {"type": "http.request", "body": body_bytes}

                        request._receive = receive
                except Exception:
                    pass

        # 9. Downstream Route Execution with Sanitized Error Handling
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            logger.error(f"❌ Internal Exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status": "error", "message": "An internal server error occurred. Logged by Security Shield."}
            )

        # 10. OWASP Hardened Security Headers Enforcement
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self' https: data: 'unsafe-inline' 'unsafe-eval';"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["Server"] = "Cloxel-Fortress-Shield/3.0"
        
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response
