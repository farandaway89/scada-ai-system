"""
Industrial Cybersecurity Framework for SCADA Systems
Implements comprehensive security measures for industrial control systems
"""

import hashlib
import hmac
import time
import json
import logging
import ssl
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import ipaddress
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security classification levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    """Types of security threats"""
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_TAMPERING = "data_tampering"
    DENIAL_OF_SERVICE = "denial_of_service"
    MAN_IN_THE_MIDDLE = "man_in_the_middle"
    MALWARE = "malware"
    INSIDER_THREAT = "insider_threat"
    PROTOCOL_MANIPULATION = "protocol_manipulation"

@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_id: str
    timestamp: datetime
    threat_type: ThreatType
    severity: SecurityLevel
    source_ip: str
    target_system: str
    description: str
    evidence: Dict[str, Any]
    mitigation_actions: List[str]

class CryptographicManager:
    """Manages encryption, decryption, and key management"""

    def __init__(self):
        self.master_key = self._generate_master_key()
        self.session_keys: Dict[str, bytes] = {}
        self.rsa_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.rsa_public_key = self.rsa_private_key.public_key()

    def _generate_master_key(self) -> bytes:
        """Generate a master encryption key"""
        password = b"SCADA_MASTER_KEY_2024"
        salt = b"industrial_salt_2024"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password)

    def encrypt_data(self, data: str, key_id: str = "master") -> bytes:
        """Encrypt sensitive data"""
        try:
            if key_id == "master":
                fernet = Fernet(Fernet.generate_key_from_password(self.master_key))
            else:
                if key_id not in self.session_keys:
                    self.session_keys[key_id] = Fernet.generate_key()
                fernet = Fernet(self.session_keys[key_id])

            encrypted_data = fernet.encrypt(data.encode())
            return encrypted_data

        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt_data(self, encrypted_data: bytes, key_id: str = "master") -> str:
        """Decrypt sensitive data"""
        try:
            if key_id == "master":
                fernet = Fernet(Fernet.generate_key_from_password(self.master_key))
            else:
                if key_id not in self.session_keys:
                    raise ValueError(f"Session key {key_id} not found")
                fernet = Fernet(self.session_keys[key_id])

            decrypted_data = fernet.decrypt(encrypted_data)
            return decrypted_data.decode()

        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    def generate_digital_signature(self, data: str) -> bytes:
        """Generate digital signature for data integrity"""
        try:
            message = data.encode()
            signature = self.rsa_private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return signature

        except Exception as e:
            logger.error(f"Digital signature error: {e}")
            raise

    def verify_digital_signature(self, data: str, signature: bytes) -> bool:
        """Verify digital signature"""
        try:
            message = data.encode()
            self.rsa_public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True

        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False

class AccessControlManager:
    """Manages user authentication and authorization"""

    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.role_permissions = self._initialize_role_permissions()

    def _initialize_role_permissions(self) -> Dict[str, List[str]]:
        """Define role-based permissions"""
        return {
            "operator": [
                "read_process_data",
                "view_alarms",
                "acknowledge_alarms"
            ],
            "engineer": [
                "read_process_data",
                "view_alarms",
                "acknowledge_alarms",
                "modify_setpoints",
                "download_trends"
            ],
            "supervisor": [
                "read_process_data",
                "view_alarms",
                "acknowledge_alarms",
                "modify_setpoints",
                "download_trends",
                "user_management",
                "system_configuration"
            ],
            "admin": [
                "read_process_data",
                "view_alarms",
                "acknowledge_alarms",
                "modify_setpoints",
                "download_trends",
                "user_management",
                "system_configuration",
                "security_management",
                "audit_logs"
            ]
        }

    def create_user(self, username: str, password: str, role: str, full_name: str) -> bool:
        """Create a new user account"""
        try:
            if username in self.users:
                logger.warning(f"User {username} already exists")
                return False

            # Hash password with salt
            salt = secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)

            self.users[username] = {
                "password_hash": password_hash.hex(),
                "salt": salt,
                "role": role,
                "full_name": full_name,
                "created_date": datetime.now(),
                "last_login": None,
                "is_active": True,
                "failed_attempts": 0
            }

            logger.info(f"User {username} created successfully")
            return True

        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return False

    def authenticate_user(self, username: str, password: str, source_ip: str) -> Optional[str]:
        """Authenticate user and return session token"""
        try:
            # Check for account lockout
            if self._is_account_locked(username):
                logger.warning(f"Account {username} is locked due to failed attempts")
                return None

            # Check if user exists
            if username not in self.users:
                self._record_failed_attempt(username, source_ip)
                logger.warning(f"Authentication failed for unknown user: {username}")
                return None

            user = self.users[username]

            # Check if account is active
            if not user["is_active"]:
                logger.warning(f"Authentication failed for inactive user: {username}")
                return None

            # Verify password
            salt = user["salt"]
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)

            if password_hash.hex() != user["password_hash"]:
                self._record_failed_attempt(username, source_ip)
                logger.warning(f"Authentication failed for user: {username}")
                return None

            # Generate session token
            session_token = secrets.token_urlsafe(32)
            session_data = {
                "username": username,
                "role": user["role"],
                "login_time": datetime.now(),
                "source_ip": source_ip,
                "last_activity": datetime.now()
            }

            self.active_sessions[session_token] = session_data
            user["last_login"] = datetime.now()
            user["failed_attempts"] = 0

            # Clear failed attempts
            if username in self.failed_attempts:
                del self.failed_attempts[username]

            logger.info(f"User {username} authenticated successfully")
            return session_token

        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            return None

    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts"""
        if username not in self.failed_attempts:
            return False

        attempts = self.failed_attempts[username]
        recent_attempts = [
            attempt for attempt in attempts
            if datetime.now() - attempt < timedelta(minutes=15)
        ]

        return len(recent_attempts) >= 5

    def _record_failed_attempt(self, username: str, source_ip: str):
        """Record failed authentication attempt"""
        if username not in self.failed_attempts:
            self.failed_attempts[username] = []

        self.failed_attempts[username].append(datetime.now())

        # Log security event
        logger.warning(f"Failed authentication attempt for {username} from {source_ip}")

    def authorize_action(self, session_token: str, required_permission: str) -> bool:
        """Check if user is authorized for specific action"""
        try:
            if session_token not in self.active_sessions:
                logger.warning("Invalid session token for authorization")
                return False

            session = self.active_sessions[session_token]

            # Check session timeout (8 hours)
            if datetime.now() - session["last_activity"] > timedelta(hours=8):
                del self.active_sessions[session_token]
                logger.warning("Session expired during authorization")
                return False

            # Update last activity
            session["last_activity"] = datetime.now()

            # Check permission
            user_role = session["role"]
            permissions = self.role_permissions.get(user_role, [])

            authorized = required_permission in permissions
            if not authorized:
                logger.warning(f"User {session['username']} not authorized for {required_permission}")

            return authorized

        except Exception as e:
            logger.error(f"Authorization error: {e}")
            return False

class NetworkSecurityMonitor:
    """Monitors network traffic for security threats"""

    def __init__(self):
        self.allowed_ip_ranges = []
        self.blocked_ips = set()
        self.connection_limits = {}
        self.suspicious_patterns = self._initialize_threat_patterns()
        self.monitoring_active = False
        self.monitor_thread = None

    def _initialize_threat_patterns(self) -> List[Dict[str, Any]]:
        """Define patterns for threat detection"""
        return [
            {
                "name": "Modbus Function Code Flooding",
                "pattern": r"modbus.*function.*code",
                "threshold": 100,
                "window": 60,  # seconds
                "threat_type": ThreatType.DENIAL_OF_SERVICE
            },
            {
                "name": "Unauthorized Protocol Commands",
                "pattern": r"(reset|restart|shutdown|format)",
                "threshold": 5,
                "window": 300,
                "threat_type": ThreatType.PROTOCOL_MANIPULATION
            },
            {
                "name": "Suspicious Data Patterns",
                "pattern": r"(\x00{10,}|\xff{10,})",
                "threshold": 10,
                "window": 60,
                "threat_type": ThreatType.DATA_TAMPERING
            }
        ]

    def add_allowed_ip_range(self, ip_range: str):
        """Add allowed IP range in CIDR notation"""
        try:
            network = ipaddress.ip_network(ip_range)
            self.allowed_ip_ranges.append(network)
            logger.info(f"Added allowed IP range: {ip_range}")

        except Exception as e:
            logger.error(f"Error adding IP range {ip_range}: {e}")

    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is in allowed ranges"""
        try:
            ip = ipaddress.ip_address(ip_address)

            # Check if IP is blocked
            if ip_address in self.blocked_ips:
                return False

            # Check allowed ranges
            for network in self.allowed_ip_ranges:
                if ip in network:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking IP {ip_address}: {e}")
            return False

    def block_ip(self, ip_address: str, reason: str):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        logger.warning(f"Blocked IP {ip_address}: {reason}")

    def analyze_traffic_pattern(self, source_ip: str, data: bytes) -> Optional[SecurityEvent]:
        """Analyze network traffic for threats"""
        try:
            data_str = data.decode('utf-8', errors='ignore').lower()

            for pattern_config in self.suspicious_patterns:
                if re.search(pattern_config["pattern"], data_str):
                    # Create security event
                    event = SecurityEvent(
                        event_id=secrets.token_hex(8),
                        timestamp=datetime.now(),
                        threat_type=pattern_config["threat_type"],
                        severity=SecurityLevel.HIGH,
                        source_ip=source_ip,
                        target_system="SCADA_SYSTEM",
                        description=f"Detected {pattern_config['name']}",
                        evidence={"pattern": pattern_config["pattern"], "data_sample": data_str[:100]},
                        mitigation_actions=["block_ip", "alert_security_team"]
                    )

                    return event

            return None

        except Exception as e:
            logger.error(f"Error analyzing traffic pattern: {e}")
            return None

class SecurityAuditLogger:
    """Logs all security-related events for compliance"""

    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = log_file
        self.security_logger = logging.getLogger("security_audit")

        # Configure security-specific logger
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.security_logger.addHandler(handler)
        self.security_logger.setLevel(logging.INFO)

    def log_authentication_event(self, username: str, success: bool, source_ip: str):
        """Log authentication events"""
        status = "SUCCESS" if success else "FAILURE"
        message = f"AUTH_{status} | User: {username} | Source: {source_ip}"
        self.security_logger.info(message)

    def log_authorization_event(self, username: str, action: str, success: bool):
        """Log authorization events"""
        status = "GRANTED" if success else "DENIED"
        message = f"AUTHZ_{status} | User: {username} | Action: {action}"
        self.security_logger.info(message)

    def log_security_event(self, event: SecurityEvent):
        """Log security threats and incidents"""
        message = (f"SECURITY_EVENT | ID: {event.event_id} | "
                  f"Type: {event.threat_type.value} | "
                  f"Severity: {event.severity.value} | "
                  f"Source: {event.source_ip} | "
                  f"Description: {event.description}")

        if event.severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            self.security_logger.error(message)
        else:
            self.security_logger.warning(message)

    def log_system_event(self, event_type: str, description: str, user: str = "SYSTEM"):
        """Log general system security events"""
        message = f"SYSTEM_EVENT | Type: {event_type} | User: {user} | Description: {description}"
        self.security_logger.info(message)

class SecurityFramework:
    """Main security framework coordinator"""

    def __init__(self):
        self.crypto_manager = CryptographicManager()
        self.access_control = AccessControlManager()
        self.network_monitor = NetworkSecurityMonitor()
        self.audit_logger = SecurityAuditLogger()
        self.security_policies = self._initialize_security_policies()
        self.active_threats: List[SecurityEvent] = []

    def _initialize_security_policies(self) -> Dict[str, Any]:
        """Initialize security policies"""
        return {
            "password_policy": {
                "min_length": 12,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special": True,
                "max_age_days": 90
            },
            "session_policy": {
                "max_duration_hours": 8,
                "idle_timeout_minutes": 30,
                "max_concurrent_sessions": 3
            },
            "network_policy": {
                "allowed_ports": [502, 102, 20000],  # Modbus, IEC61850, DNP3
                "require_encryption": True,
                "max_connections_per_ip": 10
            }
        }

    def initialize_security(self):
        """Initialize security framework"""
        try:
            # Set up default allowed IP ranges (adjust for your network)
            self.network_monitor.add_allowed_ip_range("192.168.1.0/24")
            self.network_monitor.add_allowed_ip_range("10.0.0.0/8")
            self.network_monitor.add_allowed_ip_range("172.16.0.0/12")

            # Create default admin user
            self.access_control.create_user(
                username="admin",
                password="SecureAdmin123!",
                role="admin",
                full_name="System Administrator"
            )

            # Log initialization
            self.audit_logger.log_system_event(
                "SECURITY_INIT",
                "Security framework initialized successfully"
            )

            logger.info("Security framework initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Security initialization failed: {e}")
            return False

    def process_security_event(self, event: SecurityEvent):
        """Process and respond to security events"""
        try:
            # Log the event
            self.audit_logger.log_security_event(event)

            # Add to active threats
            self.active_threats.append(event)

            # Implement automatic mitigation
            for action in event.mitigation_actions:
                if action == "block_ip":
                    self.network_monitor.block_ip(
                        event.source_ip,
                        f"Threat detected: {event.threat_type.value}"
                    )
                elif action == "alert_security_team":
                    self._alert_security_team(event)

            # Escalate critical events
            if event.severity == SecurityLevel.CRITICAL:
                self._escalate_critical_event(event)

        except Exception as e:
            logger.error(f"Error processing security event: {e}")

    def _alert_security_team(self, event: SecurityEvent):
        """Alert security team of threats"""
        # In production, integrate with SIEM, email, SMS, etc.
        logger.critical(f"SECURITY ALERT: {event.description} from {event.source_ip}")

    def _escalate_critical_event(self, event: SecurityEvent):
        """Escalate critical security events"""
        # In production, implement automatic incident response
        logger.critical(f"CRITICAL SECURITY EVENT: {event.description}")

    def validate_data_integrity(self, data: str, signature: bytes) -> bool:
        """Validate data integrity using digital signatures"""
        return self.crypto_manager.verify_digital_signature(data, signature)

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        return {
            "active_sessions": len(self.access_control.active_sessions),
            "blocked_ips": len(self.network_monitor.blocked_ips),
            "active_threats": len(self.active_threats),
            "recent_threats": [
                {
                    "id": event.event_id,
                    "type": event.threat_type.value,
                    "severity": event.severity.value,
                    "timestamp": event.timestamp.isoformat()
                }
                for event in self.active_threats[-10:]  # Last 10 threats
            ]
        }

# Example usage
if __name__ == "__main__":
    # Initialize security framework
    security = SecurityFramework()
    security.initialize_security()

    # Simulate authentication
    session_token = security.access_control.authenticate_user(
        "admin", "SecureAdmin123!", "192.168.1.100"
    )

    if session_token:
        print(f"Authentication successful. Session: {session_token}")

        # Test authorization
        authorized = security.access_control.authorize_action(
            session_token, "read_process_data"
        )
        print(f"Authorization for read_process_data: {authorized}")

    # Test threat detection
    test_data = b"modbus function code reset system"
    threat_event = security.network_monitor.analyze_traffic_pattern(
        "192.168.1.200", test_data
    )

    if threat_event:
        security.process_security_event(threat_event)

    # Get security status
    status = security.get_security_status()
    print(f"Security Status: {json.dumps(status, indent=2)}")