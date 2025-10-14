"""
Enterprise Authentication and Security Manager
기업급 인증 및 보안 관리 시스템
"""

import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import logging
from typing import Optional, Dict, List
import json
from enum import Enum

# 보안 설정
security = HTTPBearer()
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
security_logger = logging.getLogger("security")

class UserRole(Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    MAINTENANCE = "maintenance"

class SecurityLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class AuthManager:
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60
        self.refresh_token_expire_days = 7

    def hash_password(self, password: str) -> str:
        """비밀번호 해시화"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def create_access_token(self, data: dict) -> str:
        """액세스 토큰 생성"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, data: dict) -> str:
        """리프레시 토큰 생성"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        """토큰 검증"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

class SessionManager:
    """세션 관리자"""

    @staticmethod
    def create_session(user_id: str, user_data: dict) -> str:
        """세션 생성"""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "user_data": user_data
        }
        redis_client.setex(f"session:{session_id}", 3600, json.dumps(session_data))
        return session_id

    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """세션 조회"""
        session_data = redis_client.get(f"session:{session_id}")
        if session_data:
            return json.loads(session_data)
        return None

    @staticmethod
    def update_session_activity(session_id: str):
        """세션 활동 업데이트"""
        session_data = SessionManager.get_session(session_id)
        if session_data:
            session_data["last_activity"] = datetime.utcnow().isoformat()
            redis_client.setex(f"session:{session_id}", 3600, json.dumps(session_data))

    @staticmethod
    def revoke_session(session_id: str):
        """세션 무효화"""
        redis_client.delete(f"session:{session_id}")

class AuditLogger:
    """감사 로그 관리자"""

    @staticmethod
    def log_security_event(event_type: str, user_id: str, details: dict,
                          security_level: SecurityLevel = SecurityLevel.MEDIUM):
        """보안 이벤트 로깅"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "security_level": security_level.name,
            "details": details,
            "ip_address": details.get("ip_address", "unknown")
        }

        # Redis에 저장 (최근 1000개 이벤트 유지)
        redis_client.lpush("security_audit_log", json.dumps(log_entry))
        redis_client.ltrim("security_audit_log", 0, 999)

        # 중요도에 따른 로깅
        if security_level == SecurityLevel.CRITICAL:
            security_logger.critical(f"CRITICAL SECURITY EVENT: {event_type} - {details}")
        elif security_level == SecurityLevel.HIGH:
            security_logger.warning(f"HIGH SECURITY EVENT: {event_type} - {details}")
        else:
            security_logger.info(f"Security event: {event_type} - {details}")

    @staticmethod
    def get_audit_logs(limit: int = 100) -> List[dict]:
        """감사 로그 조회"""
        logs = redis_client.lrange("security_audit_log", 0, limit-1)
        return [json.loads(log) for log in logs]

class RolePermissionManager:
    """역할 및 권한 관리자"""

    ROLE_PERMISSIONS = {
        UserRole.ADMIN: [
            "view_dashboard", "modify_settings", "user_management",
            "system_control", "audit_access", "emergency_override"
        ],
        UserRole.OPERATOR: [
            "view_dashboard", "basic_control", "alert_acknowledge",
            "report_generation"
        ],
        UserRole.VIEWER: [
            "view_dashboard", "basic_reports"
        ],
        UserRole.MAINTENANCE: [
            "view_dashboard", "maintenance_mode", "diagnostic_access",
            "equipment_control"
        ]
    }

    @staticmethod
    def check_permission(user_role: UserRole, required_permission: str) -> bool:
        """권한 확인"""
        permissions = RolePermissionManager.ROLE_PERMISSIONS.get(user_role, [])
        return required_permission in permissions

    @staticmethod
    def get_user_permissions(user_role: UserRole) -> List[str]:
        """사용자 권한 목록 조회"""
        return RolePermissionManager.ROLE_PERMISSIONS.get(user_role, [])

# 전역 인스턴스
auth_manager = AuthManager()

# 의존성 함수들
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """현재 사용자 정보 가져오기"""
    payload = auth_manager.verify_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return payload

async def require_permission(permission: str):
    """특정 권한 요구"""
    def permission_checker(current_user: dict = Depends(get_current_user)):
        user_role = UserRole(current_user.get("role", "viewer"))
        if not RolePermissionManager.check_permission(user_role, permission):
            AuditLogger.log_security_event(
                "unauthorized_access_attempt",
                current_user.get("sub", "unknown"),
                {"required_permission": permission},
                SecurityLevel.HIGH
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return current_user
    return permission_checker

# 보안 미들웨어
class SecurityMiddleware:
    """보안 미들웨어"""

    @staticmethod
    def rate_limiter(user_id: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
        """API 호출 제한"""
        key = f"rate_limit:{user_id}"
        current = redis_client.get(key)

        if current is None:
            redis_client.setex(key, window_seconds, 1)
            return True
        elif int(current) < max_requests:
            redis_client.incr(key)
            return True
        else:
            return False

    @staticmethod
    def detect_suspicious_activity(user_id: str, action: str) -> bool:
        """의심스러운 활동 탐지"""
        key = f"activity:{user_id}:{action}"
        count = redis_client.incr(key)
        redis_client.expire(key, 300)  # 5분 윈도우

        # 5분 내 같은 액션 10회 이상시 의심스러운 활동으로 판단
        if count > 10:
            AuditLogger.log_security_event(
                "suspicious_activity_detected",
                user_id,
                {"action": action, "count": count},
                SecurityLevel.HIGH
            )
            return True
        return False

# 데이터 암호화 유틸리티
class DataEncryption:
    """데이터 암호화/복호화"""

    @staticmethod
    def encrypt_sensitive_data(data: str, key: str = None) -> str:
        """민감한 데이터 암호화"""
        from cryptography.fernet import Fernet
        if key is None:
            key = Fernet.generate_key()
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return encrypted_data.decode()

    @staticmethod
    def decrypt_sensitive_data(encrypted_data: str, key: str) -> str:
        """민감한 데이터 복호화"""
        from cryptography.fernet import Fernet
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data.encode())
        return decrypted_data.decode()

# 기본 사용자 데이터베이스 (실제 환경에서는 PostgreSQL 등 사용)
USERS_DB = {
    "admin": {
        "user_id": "admin",
        "username": "admin",
        "email": "admin@scada-system.com",
        "hashed_password": auth_manager.hash_password("admin123!"),
        "role": UserRole.ADMIN.value,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
        "failed_login_attempts": 0
    },
    "operator1": {
        "user_id": "operator1",
        "username": "operator1",
        "email": "operator1@scada-system.com",
        "hashed_password": auth_manager.hash_password("operator123!"),
        "role": UserRole.OPERATOR.value,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
        "failed_login_attempts": 0
    },
    "viewer1": {
        "user_id": "viewer1",
        "username": "viewer1",
        "email": "viewer1@scada-system.com",
        "hashed_password": auth_manager.hash_password("viewer123!"),
        "role": UserRole.VIEWER.value,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
        "failed_login_attempts": 0
    }
}