# SCADA AI 시스템 아키텍처 다이어그램

## 1. 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Client Layer"
        Browser[웹 브라우저]
        Mobile[모바일 앱]
        API_Client[API 클라이언트]
    end

    subgraph "API Gateway"
        FastAPI[FastAPI Server<br/>Port 9000]
        WebSocket[WebSocket<br/>Port 9765]
    end

    subgraph "Security Layer"
        Auth[인증 시스템<br/>JWT Bearer Token]
        RBAC[권한 관리<br/>Admin/Operator/Viewer]
        IDS[침입 탐지<br/>IDS]
    end

    subgraph "Business Logic"
        Monitor[실시간 모니터링]
        Analytics[AI/ML 분석<br/>TensorFlow]
        Report[보고서 생성]
        Compliance[규정 준수<br/>ISO27001/IEC62443]
        Protocol[산업 프로토콜<br/>Modbus/DNP3]
        Integration[엔터프라이즈<br/>통합]
    end

    subgraph "Data Layer"
        Pipeline[데이터 파이프라인]
        Cache[Redis Cache]
        Database[PostgreSQL 14]
    end

    subgraph "External Systems"
        Sensors[산업 센서]
        ERP[ERP 시스템]
        Cloud[클라우드<br/>Azure/GCP]
    end

    Browser --> FastAPI
    Mobile --> FastAPI
    API_Client --> FastAPI
    Browser --> WebSocket

    FastAPI --> Auth
    Auth --> RBAC
    Auth --> IDS

    FastAPI --> Monitor
    FastAPI --> Analytics
    FastAPI --> Report
    FastAPI --> Compliance
    FastAPI --> Protocol
    FastAPI --> Integration

    Monitor --> Pipeline
    Analytics --> Pipeline
    Report --> Pipeline
    Compliance --> Pipeline
    Protocol --> Pipeline
    Integration --> Pipeline

    Pipeline --> Cache
    Pipeline --> Database

    Protocol --> Sensors
    Integration --> ERP
    Integration --> Cloud
```

## 2. 데이터 흐름 다이어그램

```mermaid
sequenceDiagram
    participant Sensor as 산업 센서
    participant Protocol as Protocol Manager
    participant Pipeline as Data Pipeline
    participant DB as PostgreSQL
    participant Cache as Redis
    participant ML as ML Engine
    participant API as FastAPI
    participant Client as 클라이언트

    Sensor->>Protocol: 센서 데이터 전송<br/>(Modbus/DNP3)
    Protocol->>Pipeline: 데이터 수집
    Pipeline->>Pipeline: 검증 및 변환
    Pipeline->>DB: 데이터 저장
    Pipeline->>Cache: 실시간 캐시
    Pipeline->>ML: AI 분석 요청
    ML->>ML: 예측 및 이상 탐지
    ML->>DB: 분석 결과 저장
    Client->>API: 데이터 조회 요청
    API->>Cache: 캐시 확인
    alt Cache Hit
        Cache->>API: 캐시된 데이터
    else Cache Miss
        API->>DB: 데이터베이스 조회
        DB->>API: 데이터 반환
        API->>Cache: 캐시 저장
    end
    API->>Client: 응답 반환
```

## 3. 인증 흐름 다이어그램

```mermaid
sequenceDiagram
    participant Client as 클라이언트
    participant API as FastAPI
    participant Auth as Auth Manager
    participant Security as Security Framework
    participant DB as PostgreSQL

    Client->>API: POST /auth/login<br/>(username, password)
    API->>Auth: 로그인 요청
    Auth->>Security: 비밀번호 검증
    Security->>DB: 사용자 조회
    DB->>Security: 사용자 정보
    Security->>Security: 비밀번호 해싱 확인
    alt 인증 성공
        Security->>Auth: 인증 성공
        Auth->>Auth: JWT Token 생성
        Auth->>API: Token 반환
        API->>Client: access_token 반환
        Client->>API: API 요청<br/>(Bearer Token)
        API->>Auth: Token 검증
        Auth->>Auth: 역할 확인
        alt 권한 있음
            API->>Client: 데이터 반환
        else 권한 없음
            API->>Client: 403 Forbidden
        end
    else 인증 실패
        Security->>Auth: 인증 실패
        Auth->>API: 실패 반환
        API->>Client: 401 Unauthorized
    end
```

## 4. Docker 컨테이너 구조

```mermaid
graph TB
    subgraph "Docker Host"
        subgraph "scada_network"
            App[scada-ai<br/>FastAPI Application<br/>Port: 9000, 9765]
            DB[postgres<br/>PostgreSQL 14<br/>Port: 5432]
            Cache[redis<br/>Redis 7<br/>Port: 6379]
        end

        subgraph "Volumes"
            PG_Data[postgres_data]
            Redis_Data[redis_data]
            Logs[./logs]
            Data[./data]
            Reports[./reports]
        end
    end

    subgraph "External"
        Client[클라이언트<br/>localhost:9000]
    end

    Client -->|HTTP/WS| App
    App -->|SQL| DB
    App -->|Cache| Cache
    DB -.->|저장| PG_Data
    Cache -.->|저장| Redis_Data
    App -.->|로그| Logs
    App -.->|데이터| Data
    App -.->|보고서| Reports
```

## 5. AI/ML 파이프라인

```mermaid
graph LR
    subgraph "데이터 수집"
        Sensors[센서 데이터]
        Historical[이력 데이터]
    end

    subgraph "전처리"
        Clean[데이터 정제]
        Transform[변환]
        Feature[특성 추출]
    end

    subgraph "모델"
        LSTM[LSTM<br/>시계열 예측]
        XGBoost[XGBoost<br/>예측 정비]
        Autoencoder[Autoencoder<br/>이상 탐지]
        IsolationForest[Isolation Forest<br/>이상치 탐지]
    end

    subgraph "결과"
        Prediction[예측 결과]
        Anomaly[이상 탐지]
        Alert[알람 생성]
        Report[보고서]
    end

    Sensors --> Clean
    Historical --> Clean
    Clean --> Transform
    Transform --> Feature

    Feature --> LSTM
    Feature --> XGBoost
    Feature --> Autoencoder
    Feature --> IsolationForest

    LSTM --> Prediction
    XGBoost --> Prediction
    Autoencoder --> Anomaly
    IsolationForest --> Anomaly

    Prediction --> Report
    Anomaly --> Alert
    Alert --> Report
```

## 6. 보안 계층 구조

```mermaid
graph TB
    subgraph "외부"
        Internet[인터넷]
        Attacker[공격자]
    end

    subgraph "방어 계층"
        Firewall[방화벽<br/>포트 제한]
        RateLimit[Rate Limiting<br/>100req/min]
        IPFilter[IP 필터링<br/>White/Black List]
    end

    subgraph "인증 계층"
        JWT[JWT Token<br/>Bearer Auth]
        Session[세션 관리<br/>Redis]
        RBAC[역할 기반<br/>권한 제어]
    end

    subgraph "탐지 계층"
        IDS[침입 탐지<br/>IDS]
        Audit[감사 로그<br/>모든 활동 기록]
        Threat[위협 탐지<br/>패턴 분석]
    end

    subgraph "보호 계층"
        Encrypt[AES-256<br/>암호화]
        Hash[bcrypt<br/>비밀번호 해싱]
        SQLProtect[ORM<br/>SQL Injection 방어]
    end

    Internet --> Firewall
    Attacker -.공격.-> Firewall
    Firewall --> RateLimit
    RateLimit --> IPFilter
    IPFilter --> JWT
    JWT --> Session
    Session --> RBAC
    RBAC --> IDS
    IDS --> Audit
    Audit --> Threat
    Threat --> Encrypt
    Encrypt --> Hash
    Hash --> SQLProtect
```

## 7. 규정 준수 프레임워크

```mermaid
graph TB
    subgraph "규정 표준"
        ISO[ISO 27001<br/>정보 보안 관리]
        IEC[IEC 62443<br/>산업 자동화 보안]
        NIST[NIST CSF<br/>사이버보안 프레임워크]
    end

    subgraph "준수 영역"
        Access[접근 제어]
        Crypto[암호화]
        Audit[감사 추적]
        Incident[사고 관리]
        Risk[위험 관리]
    end

    subgraph "검증"
        Auto[자동 검사<br/>일일]
        Manual[수동 검사<br/>월간]
        External[외부 감사<br/>연간]
    end

    subgraph "결과"
        Compliance[규정 준수 현황<br/>97%]
        Report[준수 보고서]
        Action[개선 조치]
    end

    ISO --> Access
    ISO --> Crypto
    ISO --> Audit
    IEC --> Access
    IEC --> Incident
    NIST --> Risk
    NIST --> Incident

    Access --> Auto
    Crypto --> Auto
    Audit --> Auto
    Incident --> Manual
    Risk --> Manual

    Auto --> Compliance
    Manual --> Compliance
    External --> Compliance

    Compliance --> Report
    Report --> Action
```

## 8. 배포 파이프라인 (향후)

```mermaid
graph LR
    subgraph "개발"
        Code[코드 작성]
        Test[단위 테스트]
        Commit[Git Commit]
    end

    subgraph "CI"
        Build[Docker Build]
        IntTest[통합 테스트]
        Security[보안 검사]
    end

    subgraph "CD"
        Stage[Staging 배포]
        E2E[E2E 테스트]
        Prod[Production 배포]
    end

    subgraph "모니터링"
        Health[헬스 체크]
        Metrics[메트릭 수집]
        Alert[알람]
    end

    Code --> Test
    Test --> Commit
    Commit --> Build
    Build --> IntTest
    IntTest --> Security
    Security --> Stage
    Stage --> E2E
    E2E --> Prod
    Prod --> Health
    Health --> Metrics
    Metrics --> Alert
```

---

**사용 방법**:

1. **GitHub에서 보기**: GitHub에 업로드하면 Mermaid 다이어그램이 자동으로 렌더링됩니다.

2. **VS Code에서 보기**: "Markdown Preview Mermaid Support" 확장 프로그램 설치

3. **온라인 에디터**:
   - https://mermaid.live/ (Mermaid 온라인 에디터)
   - 코드 복사 → 붙여넣기 → PNG/SVG 다운로드

4. **PDF 변환**:
   ```bash
   # Mermaid CLI 설치 (Node.js 필요)
   npm install -g @mermaid-js/mermaid-cli

   # PNG로 변환
   mmdc -i system_architecture.md -o architecture.png
   ```

**문서 버전**: 1.0
**작성일**: 2025년 10월 14일
