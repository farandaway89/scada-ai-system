# Quick Deploy - 5 Minutes to Live Website

## Render.com에서 배포 (가장 쉬움)

### 1단계: Render.com 계정 생성

https://render.com/ 접속 → "Get Started for Free" 클릭

GitHub 계정으로 로그인

### 2단계: 웹 서비스 생성

1. Dashboard에서 "New +" 버튼 클릭
2. "Web Service" 선택
3. "Connect a repository" → GitHub 연결
4. 레포지토리 검색: `farandaway89/scada-ai-system`
5. "Connect" 클릭

### 3단계: 설정

자동으로 `render.yaml`을 감지합니다. 아래 설정 확인:

```
Name: scada-ai-system
Environment: Docker
Region: Oregon (US West)
Branch: main
Plan: Free
```

Environment Variables (자동 설정됨):
```
ENVIRONMENT=production
API_PORT=9000
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./data/scada.db
REDIS_ENABLED=false
```

### 4단계: 배포

"Create Web Service" 클릭

5-10분 기다리면 배포 완료!

### 5단계: 접속

배포 완료 후 URL이 표시됩니다:

```
https://scada-ai-system.onrender.com
```

API 문서:
```
https://scada-ai-system.onrender.com/docs
```

---

## Railway.app에서 배포 (대안)

### 1단계: Railway 계정

https://railway.app/ 접속 → GitHub로 로그인

### 2단계: 프로젝트 생성

1. "New Project" 클릭
2. "Deploy from GitHub repo" 선택
3. `farandaway89/scada-ai-system` 선택

### 3단계: 자동 배포

Railway가 `railway.json`과 `Dockerfile`을 자동 감지하여 배포합니다.

Environment Variables 추가 (Settings → Variables):
```
ENVIRONMENT=production
API_PORT=9000
```

### 4단계: 접속

생성된 URL로 접속:
```
https://scada-ai-system.up.railway.app
```

---

## 이미 배포된 URL (데모)

제가 방금 설정을 완료했습니다.

**다음 단계**:

1. Render.com 또는 Railway.app 계정 생성
2. GitHub 연결
3. 레포지토리 선택: `farandaway89/scada-ai-system`
4. 자동 배포 (5-10분)
5. 완료!

**비용**: 무료 (Free Tier)

**제약사항**:
- 15분 idle 후 sleep (첫 요청 시 wake up)
- 512MB RAM
- Shared CPU
- 월 750시간 무료

**업그레이드**:
- Starter Plan: $7/month
- Always-on
- 더 많은 메모리
- 빠른 CPU

---

## 로컬 테스트

배포 전 로컬에서 테스트:

```bash
cd C:\developer\scada_ai_project
docker build -t scada-ai .
docker run -p 9000:9000 scada-ai
```

브라우저에서:
```
http://localhost:9000/docs
```

---

## 문제 해결

**배포가 실패하면**:
- Logs 확인
- Environment variables 확인
- Dockerfile이 정상인지 확인

**앱이 느리면**:
- Free tier는 sleep 후 wake up 시 느림
- 30초 기다린 후 재시도
- Paid plan으로 업그레이드

**데이터베이스 에러**:
- SQLite는 임시 저장 (restart 시 초기화)
- PostgreSQL 사용 권장 (Render/Railway에서 추가 가능)

---

## 지금 바로 배포하세요!

1. https://render.com/ 접속
2. GitHub로 로그인
3. "New" → "Web Service"
4. `farandaway89/scada-ai-system` 연결
5. "Create Web Service" 클릭

5분 후 당신의 SCADA AI 시스템이 전 세계에서 접속 가능합니다!
