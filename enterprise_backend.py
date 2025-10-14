"""
Enterprise-Grade SCADA AI Backend Server
기업급 SCADA AI 백엔드 서버
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import joblib
import pandas as pd
import mysql.connector
from mysql.connector import Error
import numpy as np
import json
from typing import List, Optional, Dict, Any
import asyncio
import aioredis
from sqlalchemy import create_engine, text
import logging

# 커스텀 모듈 임포트
from auth_manager import (
    auth_manager, get_current_user, require_permission,
    AuditLogger, SecurityLevel, UserRole, USERS_DB,
    SecurityMiddleware, SessionManager
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Enterprise SCADA AI System",
    description="기업급 지능형 수처리 시스템 API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # 보안 강화
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 데이터베이스 설정
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",  # 실제 환경에서는 환경변수 사용
    "database": "scada_db"
}

MODEL_PATH = "turbidity_model.pkl"

# Pydantic 모델들
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_info: Dict[str, Any]

class PredictionResponse(BaseModel):
    actual_ph: float
    actual_do: float
    actual_turbidity: float
    actual_tds: float
    predicted_turbidity: float
    prediction_confidence: float
    future_predictions: List[float]
    timestamp: str

class AlertRequest(BaseModel):
    alert_type: str
    severity: str
    message: str
    parameters: Dict[str, Any]

class SystemStatusResponse(BaseModel):
    status: str
    uptime: str
    active_users: int
    last_prediction: str
    model_accuracy: float
    alerts_count: int

class AuditLogResponse(BaseModel):
    timestamp: str
    event_type: str
    user_id: str
    security_level: str
    details: Dict[str, Any]

# AI 모델 로드
try:
    model = joblib.load(MODEL_PATH)
    logger.info(f"Model '{MODEL_PATH}' loaded successfully.")
except FileNotFoundError:
    logger.error(f"Model file not found at '{MODEL_PATH}'. Please run model_trainer.py first.")
    model = None

# 전역 변수
app.state.system_start_time = datetime.utcnow()
app.state.prediction_history = []
app.state.active_alerts = []

# 데이터베이스 연결 함수
def get_db_connection():
    """데이터베이스 연결 생성"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        logger.error(f"Database connection error: {e}")
        return None

# 미들웨어 및 의존성
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """보안 미들웨어"""
    start_time = datetime.utcnow()

    # IP 기반 접근 제한 (예시)
    client_ip = request.client.host

    response = await call_next(request)

    # 응답 시간 로깅
    process_time = (datetime.utcnow() - start_time).total_seconds()
    response.headers["X-Process-Time"] = str(process_time)

    return response

# 인증 엔드포인트
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, request: Request):
    """사용자 로그인"""
    user = USERS_DB.get(login_data.username)

    if not user or not auth_manager.verify_password(login_data.password, user["hashed_password"]):
        # 실패한 로그인 시도 기록
        AuditLogger.log_security_event(
            "failed_login_attempt",
            login_data.username,
            {"ip_address": request.client.host},
            SecurityLevel.MEDIUM
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )

    # 토큰 생성
    access_token = auth_manager.create_access_token(
        data={"sub": user["user_id"], "role": user["role"]}
    )
    refresh_token = auth_manager.create_refresh_token(
        data={"sub": user["user_id"]}
    )

    # 세션 생성
    session_id = SessionManager.create_session(user["user_id"], user)

    # 로그인 성공 기록
    AuditLogger.log_security_event(
        "successful_login",
        user["user_id"],
        {"ip_address": request.client.host, "session_id": session_id},
        SecurityLevel.LOW
    )

    # 마지막 로그인 시간 업데이트
    user["last_login"] = datetime.utcnow().isoformat()
    user["failed_login_attempts"] = 0

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=auth_manager.access_token_expire_minutes * 60,
        user_info={
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    )

@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """사용자 로그아웃"""
    AuditLogger.log_security_event(
        "user_logout",
        current_user["sub"],
        {},
        SecurityLevel.LOW
    )
    return {"message": "Successfully logged out"}

# 예측 엔드포인트 (권한 필요)
@app.get("/api/predict", response_model=PredictionResponse)
async def predict(current_user: dict = Depends(require_permission("view_dashboard"))):
    """AI 예측 수행 (인증 필요)"""
    if model is None:
        raise HTTPException(status_code=503, detail="AI model not available")

    # Rate limiting 확인
    if not SecurityMiddleware.rate_limiter(current_user["sub"], max_requests=1000):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=503, detail="Database connection failed")

    try:
        # 최신 데이터 조회
        water_query = "SELECT * FROM water_quality_data ORDER BY timestamp DESC LIMIT 1"
        weather_query = "SELECT * FROM weather_data ORDER BY forecast_time DESC LIMIT 1"

        water_df = pd.read_sql(water_query, conn)
        weather_df = pd.read_sql(weather_query, conn)

        if water_df.empty or weather_df.empty:
            raise HTTPException(status_code=404, detail="Insufficient data")

        # 예측 수행
        features_for_prediction = pd.DataFrame({
            'ph_value': [water_df.iloc[0]['ph_value']],
            'do_value': [water_df.iloc[0]['do_value']],
            'tds_value': [water_df.iloc[0]['tds_value']],
            'temperature_x': [water_df.iloc[0]['temperature']],
            'precipitation_mm': [weather_df.iloc[0]['precipitation_mm']],
            'humidity': [weather_df.iloc[0]['humidity']]
        })

        prediction = model.predict(features_for_prediction)
        predicted_turbidity = prediction[0]

        # 예측 신뢰도 계산 (간단한 예시)
        confidence = min(95.0, max(70.0, 90.0 - abs(predicted_turbidity - water_df.iloc[0]['turbidity']) * 10))

        # 미래 예측 생성
        future_predictions = generate_future_predictions(features_for_prediction, model)

        # 예측 이력에 추가
        prediction_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user["sub"],
            "predicted_value": predicted_turbidity,
            "actual_value": water_df.iloc[0]['turbidity'],
            "confidence": confidence
        }
        app.state.prediction_history.append(prediction_record)

        # 최근 100개 기록만 유지
        if len(app.state.prediction_history) > 100:
            app.state.prediction_history = app.state.prediction_history[-100:]

        result = PredictionResponse(
            actual_ph=float(water_df.iloc[0]['ph_value']),
            actual_do=float(water_df.iloc[0]['do_value']),
            actual_turbidity=float(water_df.iloc[0]['turbidity']),
            actual_tds=float(water_df.iloc[0]['tds_value']),
            predicted_turbidity=round(predicted_turbidity, 2),
            prediction_confidence=round(confidence, 1),
            future_predictions=future_predictions,
            timestamp=datetime.utcnow().isoformat()
        )

        return result

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn and conn.is_connected():
            conn.close()

def generate_future_predictions(current_features, model, num_steps=10):
    """미래 예측 생성"""
    future_predictions = []
    current_data = current_features.iloc[0].copy()

    for i in range(num_steps):
        # 시뮬레이션 로직 (기존과 동일)
        current_data['ph_value'] += (0.01 * (i+1)) + (0.01 * (0.5 - np.random.rand()))
        current_data['do_value'] -= (0.02 * (i+1)) + (0.01 * (0.5 - np.random.rand()))
        current_data['tds_value'] += (0.5 * (i+1)) + (0.5 * (0.5 - np.random.rand()))
        current_data['temperature_x'] += (0.1 * (i+1)) + (0.1 * (0.5 - np.random.rand()))

        future_features = pd.DataFrame([current_data[feature] for feature in current_features.columns]).T
        future_features.columns = current_features.columns

        prediction = model.predict(future_features)
        future_predictions.append(round(prediction[0], 2))

    return future_predictions

# 시스템 상태 엔드포인트
@app.get("/api/system/status", response_model=SystemStatusResponse)
async def get_system_status(current_user: dict = Depends(get_current_user)):
    """시스템 상태 조회"""
    uptime = datetime.utcnow() - app.state.system_start_time

    # 활성 사용자 수 계산 (간단한 예시)
    active_users = len([p for p in app.state.prediction_history
                       if datetime.fromisoformat(p["timestamp"]) > datetime.utcnow() - timedelta(hours=1)])

    # 모델 정확도 계산
    recent_predictions = app.state.prediction_history[-10:] if app.state.prediction_history else []
    if recent_predictions:
        accuracies = [100 - abs(p["predicted_value"] - p["actual_value"]) / p["actual_value"] * 100
                     for p in recent_predictions if p["actual_value"] > 0]
        model_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
    else:
        model_accuracy = 0

    return SystemStatusResponse(
        status="operational",
        uptime=str(uptime),
        active_users=active_users,
        last_prediction=app.state.prediction_history[-1]["timestamp"] if app.state.prediction_history else "N/A",
        model_accuracy=round(model_accuracy, 1),
        alerts_count=len(app.state.active_alerts)
    )

# 알림 관리 엔드포인트
@app.post("/api/alerts")
async def create_alert(
    alert_data: AlertRequest,
    current_user: dict = Depends(require_permission("basic_control"))
):
    """알림 생성"""
    alert = {
        "id": len(app.state.active_alerts) + 1,
        "created_by": current_user["sub"],
        "created_at": datetime.utcnow().isoformat(),
        **alert_data.dict()
    }

    app.state.active_alerts.append(alert)

    AuditLogger.log_security_event(
        "alert_created",
        current_user["sub"],
        {"alert_type": alert_data.alert_type, "severity": alert_data.severity},
        SecurityLevel.MEDIUM
    )

    return {"message": "Alert created successfully", "alert_id": alert["id"]}

@app.get("/api/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    """알림 목록 조회"""
    return {"alerts": app.state.active_alerts}

# 감사 로그 엔드포인트
@app.get("/api/audit/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    limit: int = 50,
    current_user: dict = Depends(require_permission("audit_access"))
):
    """감사 로그 조회 (관리자 전용)"""
    logs = AuditLogger.get_audit_logs(limit)
    return [AuditLogResponse(**log) for log in logs]

# 고급 분석 엔드포인트
@app.get("/api/analytics/trends")
async def get_trends(
    hours: int = 24,
    current_user: dict = Depends(require_permission("view_dashboard"))
):
    """데이터 트렌드 분석"""
    # 실제 구현에서는 더 복잡한 분석 로직 필요
    since = datetime.utcnow() - timedelta(hours=hours)
    recent_predictions = [
        p for p in app.state.prediction_history
        if datetime.fromisoformat(p["timestamp"]) > since
    ]

    if not recent_predictions:
        return {"trend": "no_data", "confidence": 0}

    # 간단한 트렌드 분석
    values = [p["predicted_value"] for p in recent_predictions]
    if len(values) > 1:
        trend = "increasing" if values[-1] > values[0] else "decreasing"
        confidence = sum(p["confidence"] for p in recent_predictions) / len(recent_predictions)
    else:
        trend = "stable"
        confidence = recent_predictions[0]["confidence"] if recent_predictions else 0

    return {
        "trend": trend,
        "confidence": round(confidence, 1),
        "data_points": len(recent_predictions),
        "time_range_hours": hours
    }

# 헬스체크 엔드포인트
@app.get("/api/health")
async def health_check():
    """시스템 헬스체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

# 메인 실행
if __name__ == "__main__":
    logger.info("Starting Enterprise SCADA AI Backend Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)