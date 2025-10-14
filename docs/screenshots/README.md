# 스크린샷 가이드

## 1. 스크린샷 캡처 방법

### Windows 스크린샷 단축키
- **전체 화면**: `Windows + PrtScn` (자동 저장: Pictures\Screenshots)
- **특정 영역**: `Windows + Shift + S` (Snipping Tool)
- **활성 창**: `Alt + PrtScn`

### Chrome 전체 페이지 캡처
1. F12 (개발자 도구)
2. Ctrl + Shift + P
3. "Capture full size screenshot" 입력
4. Enter

## 2. 간단 버전 스크린샷 (4개)

### 캡처 대상

#### 1. API 문서 (Swagger UI)
**URL**: http://localhost:8000/docs
**파일명**: `simple_01_swagger_ui.png`
**캡처 내용**:
- 전체 API 엔드포인트 목록 (8개)
- FastAPI 자동 생성 문서

#### 2. 대시보드 데이터
**URL**: http://localhost:8000/api/dashboard
**파일명**: `simple_02_dashboard.png`
**캡처 내용**:
- JSON 응답 데이터
- 5개 센서 현황
- 시스템 상태

#### 3. 센서 목록
**URL**: http://localhost:8000/api/sensors
**파일명**: `simple_03_sensors.png`
**캡처 내용**:
- 센서 목록 JSON
- 센서 ID, 이름, 단위

#### 4. ML 예측 결과
**URL**: http://localhost:8000/api/ml/predict
**파일명**: `simple_04_ml_prediction.png`
**캡처 내용**:
- 예측값
- 모델 정확도
- Linear Regression 결과

### 실행 순서

```bash
# 1. 간단 버전 프로젝트로 이동
cd "C:\새 폴더\Project\water_treatment_ai_project"

# 2. Docker Compose 실행
docker-compose up -d

# 3. 컨테이너 확인
docker-compose ps

# 4. 로그 확인 (정상 실행 여부)
docker-compose logs backend

# 5. 브라우저 접속
start http://localhost:8000/docs

# 6. 각 URL 순서대로 접속하여 스크린샷 캡처

# 7. 종료
docker-compose down
```

## 3. 고도화 버전 스크린샷 (6개)

### 캡처 대상

#### 1. Swagger UI 메인
**URL**: http://localhost:9000/docs
**파일명**: `enterprise_01_swagger_main.png`
**캡처 내용**:
- 전체 API 엔드포인트 (12개)
- 인증 버튼 (Authorize)
- API 그룹별 분류

#### 2. 로그인 API
**URL**: http://localhost:9000/docs (POST /auth/login)
**파일명**: `enterprise_02_login.png`
**캡처 내용**:
- 로그인 엔드포인트 확장
- Try it out 버튼
- username, password 입력 폼
- 응답 예시 (access_token)

#### 3. 시스템 상태
**URL**: http://localhost:9000/status
**파일명**: `enterprise_03_status.png`
**캡처 내용**:
- 시스템 버전 (2.0.0)
- 모듈 상태 (10개)
- 데이터베이스 연결 상태
- CPU/메모리 사용률

#### 4. 실시간 모니터링
**URL**: http://localhost:9000/monitoring/current (인증 필요)
**파일명**: `enterprise_04_monitoring.png`
**캡처 내용**:
- 5개 센서 실시간 데이터
- 센서 상태 (normal/warning/critical)
- 알람 목록
- 타임스탬프

#### 5. AI 분석 대시보드
**URL**: http://localhost:9000/analytics/dashboard (인증 필요)
**파일명**: `enterprise_05_analytics.png`
**캡처 내용**:
- AI 예측 결과
- 이상 탐지 결과
- 추천 사항
- 모델 성능 지표

#### 6. 규정 준수 현황
**URL**: http://localhost:9000/compliance/dashboard (인증 필요)
**파일명**: `enterprise_06_compliance.png`
**캡처 내용**:
- 전체 규정 준수율 (97%)
- ISO27001, IEC62443, NIST 상태
- 미준수 항목
- 개선 권장사항

### 실행 순서

```bash
# 1. 고도화 버전 프로젝트로 이동
cd "C:\새 폴더\scada_ai_project"

# 2. Docker Compose 실행
docker-compose up -d

# 3. 컨테이너 확인 (3개: app, postgres, redis)
docker-compose ps

# 4. 로그 확인
docker-compose logs -f scada-ai

# 5. 브라우저 접속
start http://localhost:9000/docs

# === 스크린샷 1: Swagger UI 메인 ===
# 그대로 캡처

# === 스크린샷 2: 로그인 API ===
# 1. POST /auth/login 찾기
# 2. "Try it out" 클릭
# 3. username: admin, password: admin123 입력
# 4. "Execute" 클릭
# 5. Response에서 access_token 복사
# 6. 캡처

# === 인증 설정 (나머지 스크린샷 위해) ===
# 1. 페이지 상단 "Authorize" 버튼 클릭
# 2. Value 입력란에 토큰 붙여넣기 (예: demo_token_admin)
# 3. "Authorize" 클릭
# 4. "Close" 클릭

# === 스크린샷 3: 시스템 상태 ===
# 1. GET /status 찾기
# 2. "Try it out" → "Execute"
# 3. Response 캡처

# === 스크린샷 4: 실시간 모니터링 ===
# 1. GET /monitoring/current 찾기
# 2. "Try it out" → "Execute"
# 3. Response 캡처

# === 스크린샷 5: AI 분석 ===
# 1. GET /analytics/dashboard 찾기
# 2. "Try it out" → "Execute"
# 3. Response 캡처

# === 스크린샷 6: 규정 준수 ===
# 1. GET /compliance/dashboard 찾기
# 2. "Try it out" → "Execute"
# 3. Response 캡처

# 7. 종료
docker-compose down
```

## 4. cURL 명령어로 데이터 확인 (스크린샷 대안)

인증이 필요한 API는 cURL로 데이터를 확인할 수 있습니다.

```bash
# 1. 로그인
curl -X POST http://localhost:9000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# 응답에서 토큰 복사 (예: demo_token_admin)

# 2. 시스템 상태
curl http://localhost:9000/status

# 3. 실시간 모니터링 (인증 필요)
curl -X GET http://localhost:9000/monitoring/current \
  -H "Authorization: Bearer demo_token_admin"

# 4. AI 분석
curl -X GET http://localhost:9000/analytics/dashboard \
  -H "Authorization: Bearer demo_token_admin"

# 5. 규정 준수
curl -X GET http://localhost:9000/compliance/dashboard \
  -H "Authorization: Bearer demo_token_admin"

# 결과를 JSON 파일로 저장
curl -X GET http://localhost:9000/monitoring/current \
  -H "Authorization: Bearer demo_token_admin" > monitoring_data.json
```

## 5. 스크린샷 저장 위치

```
C:\새 폴더\scada_ai_project\docs\screenshots\
├── README.md (본 파일)
├── simple_01_swagger_ui.png
├── simple_02_dashboard.png
├── simple_03_sensors.png
├── simple_04_ml_prediction.png
├── enterprise_01_swagger_main.png
├── enterprise_02_login.png
├── enterprise_03_status.png
├── enterprise_04_monitoring.png
├── enterprise_05_analytics.png
└── enterprise_06_compliance.png
```

## 6. 추가 캡처 권장 사항

### Docker Desktop
**파일명**: `docker_containers.png`
**캡처 내용**:
- Docker Desktop 실행 화면
- 컨테이너 목록 (5개)
- 컨테이너 상태 (Running/Healthy)

### VS Code
**파일명**: `vscode_project.png`
**캡처 내용**:
- 프로젝트 폴더 구조
- 주요 파일 (main_application.py)
- 터미널 (docker-compose up 실행)

### Windows 터미널
**파일명**: `terminal_commands.png`
**캡처 내용**:
- docker-compose ps 출력
- docker-compose logs 출력
- 시스템 정상 작동 로그

## 7. 스크린샷 품질 가이드

### 해상도
- 최소: 1920x1080
- 권장: 2560x1440 이상

### 파일 형식
- PNG (무손실, 권장)
- JPG (압축, 파일 크기 작음)

### 캡처 범위
- 브라우저 주소창 포함
- 전체 응답 데이터 포함
- 스크롤이 필요한 경우 여러 장 캡처

### 편집
- 민감 정보 블러 처리 (IP, 비밀번호 등)
- 중요 부분 강조 (빨간 박스)
- 설명 텍스트 추가

## 8. 자동 스크린샷 도구 (선택)

### Puppeteer (Node.js)
```javascript
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  await page.setViewport({ width: 1920, height: 1080 });
  await page.goto('http://localhost:9000/docs');
  await page.screenshot({ path: 'enterprise_01_swagger_main.png', fullPage: true });

  await browser.close();
})();
```

### Selenium (Python)
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(options=options)
driver.get('http://localhost:9000/docs')
driver.save_screenshot('enterprise_01_swagger_main.png')
driver.quit()
```

## 9. 문제 해결

### 문제 1: 페이지가 로드되지 않음
```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs -f

# 재시작
docker-compose restart
```

### 문제 2: 인증 오류 (401)
```bash
# 새 토큰 발급
curl -X POST http://localhost:9000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"

# Swagger UI에서 Authorize 다시 설정
```

### 문제 3: 데이터가 비어있음
```bash
# 시스템이 막 시작되었을 수 있음 (1-2분 대기)
# 데이터 시뮬레이터 확인
docker-compose logs scada-ai | grep "Sensor data"
```

---

**참고**:
- 스크린샷은 프로젝트 문서화에 필수적입니다
- GitHub, 발표 자료, 포트폴리오에 활용 가능
- 정기적으로 업데이트하여 최신 상태 유지

**문서 버전**: 1.0
**작성일**: 2025년 10월 14일
