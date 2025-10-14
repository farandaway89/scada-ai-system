"""
API Management and Documentation System
API 관리 및 문서화 시스템
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Any, Union
import time
import json
from datetime import datetime, timedelta
import redis
from collections import defaultdict
import logging
from pathlib import Path
import yaml
import asyncio
from dataclasses import dataclass
import uuid

# 로깅 설정
logger = logging.getLogger(__name__)

class APIKeyManager:
    """API 키 관리자"""

    def __init__(self, redis_client):
        self.redis = redis_client

    def create_api_key(self, user_id: str, name: str, permissions: List[str],
                      expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """API 키 생성"""
        api_key = f"scada_api_{uuid.uuid4().hex}"

        key_data = {
            "user_id": user_id,
            "name": name,
            "permissions": permissions,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "active": True,
            "usage_count": 0,
            "last_used": None
        }

        self.redis.hset(f"api_key:{api_key}", mapping={
            k: json.dumps(v) if isinstance(v, list) else str(v)
            for k, v in key_data.items()
        })

        if expires_at:
            self.redis.expireat(f"api_key:{api_key}", expires_at)

        return {"api_key": api_key, **key_data}

    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """API 키 검증"""
        key_data = self.redis.hgetall(f"api_key:{api_key}")

        if not key_data:
            return None

        # JSON 파싱
        parsed_data = {}
        for k, v in key_data.items():
            if k == "permissions":
                parsed_data[k] = json.loads(v)
            elif k in ["active"]:
                parsed_data[k] = v.lower() == "true"
            elif k in ["usage_count"]:
                parsed_data[k] = int(v)
            else:
                parsed_data[k] = v

        if not parsed_data.get("active", False):
            return None

        # 만료 확인
        if parsed_data.get("expires_at"):
            expires_at = datetime.fromisoformat(parsed_data["expires_at"])
            if datetime.utcnow() > expires_at:
                return None

        # 사용량 업데이트
        self.redis.hincrby(f"api_key:{api_key}", "usage_count", 1)
        self.redis.hset(f"api_key:{api_key}", "last_used", datetime.utcnow().isoformat())

        return parsed_data

    def revoke_api_key(self, api_key: str) -> bool:
        """API 키 비활성화"""
        if self.redis.exists(f"api_key:{api_key}"):
            self.redis.hset(f"api_key:{api_key}", "active", "false")
            return True
        return False

class RateLimiter:
    """API 속도 제한기"""

    def __init__(self, redis_client):
        self.redis = redis_client

    def is_allowed(self, api_key: str, limit: int = 1000, window: int = 3600) -> bool:
        """속도 제한 확인"""
        key = f"rate_limit:{api_key}:{int(time.time() // window)}"
        current = self.redis.incr(key)

        if current == 1:
            self.redis.expire(key, window)

        return current <= limit

    def get_usage(self, api_key: str, window: int = 3600) -> Dict[str, int]:
        """현재 사용량 조회"""
        current_window = int(time.time() // window)
        key = f"rate_limit:{api_key}:{current_window}"

        current_usage = self.redis.get(key)
        current_usage = int(current_usage) if current_usage else 0

        return {
            "current_usage": current_usage,
            "window_seconds": window,
            "reset_time": (current_window + 1) * window
        }

class APIAnalytics:
    """API 분석기"""

    def __init__(self, redis_client):
        self.redis = redis_client

    def record_request(self, api_key: str, endpoint: str, method: str,
                      status_code: int, response_time: float):
        """API 요청 기록"""
        timestamp = datetime.utcnow()
        date_key = timestamp.strftime("%Y-%m-%d")
        hour_key = timestamp.strftime("%Y-%m-%d:%H")

        # 일별 통계
        self.redis.hincrby(f"analytics:daily:{date_key}", f"{api_key}:requests", 1)
        self.redis.hincrby(f"analytics:daily:{date_key}", f"{api_key}:response_time", int(response_time * 1000))

        # 시간별 통계
        self.redis.hincrby(f"analytics:hourly:{hour_key}", f"{api_key}:requests", 1)

        # 엔드포인트별 통계
        self.redis.hincrby(f"analytics:endpoints:{date_key}", f"{endpoint}:{method}", 1)

        # 상태 코드별 통계
        self.redis.hincrby(f"analytics:status:{date_key}", str(status_code), 1)

        # TTL 설정 (30일)
        for key in [f"analytics:daily:{date_key}", f"analytics:hourly:{hour_key}",
                   f"analytics:endpoints:{date_key}", f"analytics:status:{date_key}"]:
            self.redis.expire(key, 30 * 24 * 3600)

    def get_analytics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """분석 데이터 조회"""
        analytics = {
            "daily_stats": {},
            "endpoint_stats": {},
            "status_code_stats": {},
            "summary": {
                "total_requests": 0,
                "avg_response_time": 0,
                "error_rate": 0
            }
        }

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        current = start

        total_requests = 0
        total_response_time = 0
        total_errors = 0

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")

            # 일별 통계
            daily_data = self.redis.hgetall(f"analytics:daily:{date_str}")
            if daily_data:
                analytics["daily_stats"][date_str] = daily_data

                for key, value in daily_data.items():
                    if key.endswith(":requests"):
                        total_requests += int(value)
                    elif key.endswith(":response_time"):
                        total_response_time += int(value)

            # 엔드포인트별 통계
            endpoint_data = self.redis.hgetall(f"analytics:endpoints:{date_str}")
            if endpoint_data:
                for endpoint, count in endpoint_data.items():
                    if endpoint not in analytics["endpoint_stats"]:
                        analytics["endpoint_stats"][endpoint] = 0
                    analytics["endpoint_stats"][endpoint] += int(count)

            # 상태 코드별 통계
            status_data = self.redis.hgetall(f"analytics:status:{date_str}")
            if status_data:
                for status, count in status_data.items():
                    if status not in analytics["status_code_stats"]:
                        analytics["status_code_stats"][status] = 0
                    analytics["status_code_stats"][status] += int(count)

                    if status.startswith(('4', '5')):
                        total_errors += int(count)

            current += timedelta(days=1)

        # 요약 통계 계산
        analytics["summary"]["total_requests"] = total_requests
        analytics["summary"]["avg_response_time"] = (
            total_response_time / total_requests if total_requests > 0 else 0
        )
        analytics["summary"]["error_rate"] = (
            total_errors / total_requests * 100 if total_requests > 0 else 0
        )

        return analytics

# Pydantic 모델들
class APIKeyRequest(BaseModel):
    name: str = Field(..., description="API 키 이름")
    permissions: List[str] = Field(..., description="권한 목록")
    expires_days: Optional[int] = Field(None, description="만료일 (일)")

class APIKeyResponse(BaseModel):
    api_key: str
    name: str
    permissions: List[str]
    created_at: str
    expires_at: Optional[str]
    active: bool

class APIUsageResponse(BaseModel):
    api_key: str
    usage_count: int
    last_used: Optional[str]
    rate_limit: Dict[str, int]

class EndpointInfo(BaseModel):
    path: str
    method: str
    summary: str
    description: str
    parameters: List[Dict[str, Any]]
    responses: Dict[str, Dict[str, Any]]
    tags: List[str]
    security: List[Dict[str, Any]]

class APIDocumentation(BaseModel):
    title: str
    version: str
    description: str
    endpoints: List[EndpointInfo]
    authentication: Dict[str, Any]
    rate_limits: Dict[str, Any]
    examples: Dict[str, Any]

def create_api_management_app() -> FastAPI:
    """API 관리 앱 생성"""

    app = FastAPI(
        title="SCADA AI System API",
        description="기업급 지능형 수처리 시스템 API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # 미들웨어 추가
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.company.com"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://app.company.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Redis 클라이언트
    redis_client = redis.Redis(host='localhost', port=6379, db=4, decode_responses=True)

    # 관리자 인스턴스
    api_key_manager = APIKeyManager(redis_client)
    rate_limiter = RateLimiter(redis_client)
    analytics = APIAnalytics(redis_client)

    # API 키 검증 의존성
    async def validate_api_key_dependency(request: Request):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=401, detail="API key required")

        key_data = api_key_manager.validate_api_key(api_key)
        if not key_data:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # 속도 제한 확인
        if not rate_limiter.is_allowed(api_key):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        return key_data

    # 권한 확인 의존성
    def require_permission(permission: str):
        def permission_checker(key_data: dict = Depends(validate_api_key_dependency)):
            if permission not in key_data.get("permissions", []):
                raise HTTPException(status_code=403, detail=f"Permission '{permission}' required")
            return key_data
        return permission_checker

    # 미들웨어 - 요청 분석
    @app.middleware("http")
    async def analytics_middleware(request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time

        # API 키가 있는 경우만 분석 기록
        api_key = request.headers.get("X-API-Key")
        if api_key:
            analytics.record_request(
                api_key=api_key,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=process_time
            )

        response.headers["X-Process-Time"] = str(process_time)
        return response

    # API 키 관리 엔드포인트
    @app.post("/api/keys", response_model=APIKeyResponse)
    async def create_api_key(
        request: APIKeyRequest,
        admin_key: dict = Depends(require_permission("admin"))
    ):
        """API 키 생성"""
        expires_at = None
        if request.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_days)

        result = api_key_manager.create_api_key(
            user_id=admin_key["user_id"],
            name=request.name,
            permissions=request.permissions,
            expires_at=expires_at
        )

        return APIKeyResponse(**result)

    @app.get("/api/keys/{api_key}/usage", response_model=APIUsageResponse)
    async def get_api_usage(
        api_key: str,
        admin_key: dict = Depends(require_permission("admin"))
    ):
        """API 키 사용량 조회"""
        key_data = api_key_manager.validate_api_key(api_key)
        if not key_data:
            raise HTTPException(status_code=404, detail="API key not found")

        rate_limit_info = rate_limiter.get_usage(api_key)

        return APIUsageResponse(
            api_key=api_key,
            usage_count=key_data["usage_count"],
            last_used=key_data.get("last_used"),
            rate_limit=rate_limit_info
        )

    @app.delete("/api/keys/{api_key}")
    async def revoke_api_key(
        api_key: str,
        admin_key: dict = Depends(require_permission("admin"))
    ):
        """API 키 비활성화"""
        success = api_key_manager.revoke_api_key(api_key)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        return {"message": "API key revoked successfully"}

    # 분석 엔드포인트
    @app.get("/api/analytics")
    async def get_api_analytics(
        start_date: str,
        end_date: str,
        admin_key: dict = Depends(require_permission("admin"))
    ):
        """API 분석 데이터 조회"""
        try:
            # 날짜 형식 검증
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")

            analytics_data = analytics.get_analytics(start_date, end_date)
            return analytics_data

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # API 문서화 엔드포인트
    @app.get("/api/documentation", response_model=APIDocumentation)
    async def get_api_documentation():
        """API 문서 조회"""
        # OpenAPI 스키마에서 엔드포인트 정보 추출
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        endpoints = []
        for path, path_item in openapi_schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    endpoint_info = EndpointInfo(
                        path=path,
                        method=method.upper(),
                        summary=operation.get("summary", ""),
                        description=operation.get("description", ""),
                        parameters=operation.get("parameters", []),
                        responses=operation.get("responses", {}),
                        tags=operation.get("tags", []),
                        security=operation.get("security", [])
                    )
                    endpoints.append(endpoint_info)

        return APIDocumentation(
            title=app.title,
            version=app.version,
            description=app.description,
            endpoints=endpoints,
            authentication={
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API 키를 X-API-Key 헤더에 포함하여 인증"
            },
            rate_limits={
                "default": "시간당 1000 요청",
                "premium": "시간당 10000 요청"
            },
            examples={
                "authentication": {
                    "curl": "curl -H 'X-API-Key: your_api_key_here' https://api.scada.com/predict",
                    "javascript": "fetch('/api/predict', { headers: { 'X-API-Key': 'your_api_key_here' } })"
                }
            }
        )

    # 상태 확인 엔드포인트
    @app.get("/api/health")
    async def health_check():
        """API 상태 확인"""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": app.version
        }

    # 예측 API (예시)
    @app.get("/api/predict")
    async def predict_water_quality(
        key_data: dict = Depends(require_permission("predict"))
    ):
        """수질 예측 API"""
        # 실제 예측 로직 (기존 backend_server.py 코드 활용)
        return {
            "prediction": "0.25",
            "confidence": "85%",
            "timestamp": datetime.utcnow().isoformat()
        }

    return app

def generate_api_client_sdk():
    """API 클라이언트 SDK 생성"""

    # Python SDK 예시
    python_sdk = '''
"""
SCADA AI System Python SDK
"""

import requests
from typing import Dict, Any, Optional
from datetime import datetime

class ScadaAPIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        })

    def predict(self) -> Dict[str, Any]:
        """수질 예측 요청"""
        response = self.session.get(f"{self.base_url}/api/predict")
        response.raise_for_status()
        return response.json()

    def get_analytics(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """분석 데이터 조회"""
        params = {'start_date': start_date, 'end_date': end_date}
        response = self.session.get(f"{self.base_url}/api/analytics", params=params)
        response.raise_for_status()
        return response.json()

    def health_check(self) -> Dict[str, Any]:
        """상태 확인"""
        response = self.session.get(f"{self.base_url}/api/health")
        response.raise_for_status()
        return response.json()

# 사용 예시
# client = ScadaAPIClient("https://api.scada.com", "your_api_key")
# prediction = client.predict()
# print(prediction)
'''

    # JavaScript SDK 예시
    javascript_sdk = '''
/**
 * SCADA AI System JavaScript SDK
 */

class ScadaAPIClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'X-API-Key': this.apiKey,
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        return response.json();
    }

    async predict() {
        return this.request('/api/predict');
    }

    async getAnalytics(startDate, endDate) {
        const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
        return this.request(`/api/analytics?${params}`);
    }

    async healthCheck() {
        return this.request('/api/health');
    }
}

// 사용 예시
// const client = new ScadaAPIClient('https://api.scada.com', 'your_api_key');
// const prediction = await client.predict();
// console.log(prediction);
'''

    # SDK 파일 저장
    Path("sdk").mkdir(exist_ok=True)

    with open("sdk/scada_python_sdk.py", "w", encoding="utf-8") as f:
        f.write(python_sdk)

    with open("sdk/scada_javascript_sdk.js", "w", encoding="utf-8") as f:
        f.write(javascript_sdk)

def generate_api_documentation_site():
    """API 문서화 사이트 생성"""

    html_template = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SCADA AI System API Documentation</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #0052D4, #4364F7); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
        .section { background: white; padding: 25px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .endpoint { border-left: 4px solid #4364F7; padding-left: 15px; margin-bottom: 20px; }
        .method { display: inline-block; padding: 5px 10px; border-radius: 5px; color: white; font-weight: bold; margin-right: 10px; }
        .get { background: #28a745; }
        .post { background: #007bff; }
        .put { background: #ffc107; color: black; }
        .delete { background: #dc3545; }
        pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
        code { background: #f8f9fa; padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SCADA AI System API Documentation</h1>
            <p>기업급 지능형 수처리 시스템 REST API</p>
        </div>

        <div class="section">
            <h2>인증</h2>
            <p>모든 API 요청에는 X-API-Key 헤더를 포함해야 합니다.</p>
            <pre><code>X-API-Key: your_api_key_here</code></pre>
        </div>

        <div class="section">
            <h2>속도 제한</h2>
            <p>기본적으로 시간당 1,000회 요청으로 제한됩니다.</p>
        </div>

        <div class="section">
            <h2>엔드포인트</h2>

            <div class="endpoint">
                <h3><span class="method get">GET</span>/api/predict</h3>
                <p>실시간 수질 예측을 수행합니다.</p>
                <h4>응답 예시:</h4>
                <pre><code>{
  "actual_ph": 7.2,
  "actual_do": 5.8,
  "actual_turbidity": 0.15,
  "predicted_turbidity": 0.18,
  "confidence": 85.5,
  "timestamp": "2025-09-17T10:30:00Z"
}</code></pre>
            </div>

            <div class="endpoint">
                <h3><span class="method get">GET</span>/api/analytics</h3>
                <p>API 사용 분석 데이터를 조회합니다. (관리자 권한 필요)</p>
                <h4>매개변수:</h4>
                <ul>
                    <li><code>start_date</code> (string): 시작 날짜 (YYYY-MM-DD)</li>
                    <li><code>end_date</code> (string): 종료 날짜 (YYYY-MM-DD)</li>
                </ul>
            </div>

            <div class="endpoint">
                <h3><span class="method get">GET</span>/api/health</h3>
                <p>API 서버 상태를 확인합니다.</p>
                <h4>응답 예시:</h4>
                <pre><code>{
  "status": "healthy",
  "timestamp": "2025-09-17T10:30:00Z",
  "version": "2.0.0"
}</code></pre>
            </div>
        </div>

        <div class="section">
            <h2>SDK</h2>
            <p>다음 언어에 대한 SDK를 제공합니다:</p>
            <ul>
                <li><a href="sdk/scada_python_sdk.py">Python SDK</a></li>
                <li><a href="sdk/scada_javascript_sdk.js">JavaScript SDK</a></li>
            </ul>
        </div>
    </div>
</body>
</html>
'''

    with open("api_documentation.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    # API 관리 앱 생성
    app = create_api_management_app()

    # SDK 및 문서 생성
    generate_api_client_sdk()
    generate_api_documentation_site()

    print("API management system created successfully")
    print("- FastAPI app with authentication and rate limiting")
    print("- Client SDKs generated in ./sdk/ directory")
    print("- API documentation site: api_documentation.html")