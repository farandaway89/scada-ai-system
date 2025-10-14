#!/usr/bin/env python3
"""
간단한 SCADA AI 시스템 테스트
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="SCADA AI System - Simple Test")

@app.get("/")
async def root():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SCADA AI System - Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 20px; background: #e8f5e8; border-radius: 8px; margin: 20px 0; }
            .success { color: #28a745; font-size: 24px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>SCADA AI System</h1>
            <div class="status">
                <div class="success">시스템이 정상적으로 실행되고 있습니다!</div>
                <p>기본 웹 서버가 작동 중입니다.</p>
                <p>이제 전체 시스템을 시작할 준비가 되었습니다.</p>
            </div>

            <h3>시스템 정보</h3>
            <p>버전: 2.0.0 (통합 완료)</p>
            <p>상태: 테스트 모드</p>
            <p>포트: 8000</p>

            <h3>다음 단계</h3>
            <p>1. 이 페이지가 보이면 기본 설정이 올바릅니다</p>
            <p>2. 전체 시스템을 시작하려면 터미널을 확인하세요</p>
        </div>
    </body>
    </html>
    """)

@app.get("/test")
async def test():
    return {"status": "ok", "message": "SCADA AI System is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "2024-09-17"}

if __name__ == "__main__":
    print("Starting SCADA AI System Test...")
    print("Opening web browser at: http://localhost:8000")
    print("Press Ctrl+C to stop")

    uvicorn.run(app, host="0.0.0.0", port=8000)