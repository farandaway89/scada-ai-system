# SCADA AI 시스템 문서 가이드

## 문서 구조

```
docs/
├── README.md (본 파일)
├── 01_프로젝트_개요.md (7.6KB)
├── 02_개발계획서.md (12KB)
├── 03_기술개발일지.md (18KB)
├── 04_완료보고서/
│   ├── 01_전체_요약.md (17KB)
│   ├── 02_간단버전_분석.md (누락)
│   ├── 03_고도화버전_분석.md (36KB)
│   ├── 04_비교분석표.md (21KB)
│   ├── 05_파일구조_분석.md (24KB)
│   ├── 06_코드_상세분석.md (33KB)
│   └── 07_문제해결_과정.md (21KB)
├── 05_사용자_가이드.md (17KB)
├── 06_향후_개선계획.md (24KB)
├── diagrams/
│   └── system_architecture.md (Mermaid 다이어그램)
└── screenshots/
    └── README.md (스크린샷 캡처 가이드)
```

**총 문서**: 11개 MD 파일 (약 230KB)

## Markdown 파일 보는 방법

### 방법 1: Visual Studio Code (가장 권장)

**설치**:
1. https://code.visualstudio.com/ 에서 다운로드
2. 설치 후 실행

**사용법**:
```bash
# 문서 폴더 열기
code "C:\새 폴더\scada_ai_project\docs"

# 특정 파일 열기
code "C:\새 폴더\scada_ai_project\docs\01_프로젝트_개요.md"
```

**미리보기**:
- `Ctrl + Shift + V`: 미리보기 열기
- `Ctrl + K V`: 옆에 미리보기 열기 (권장)

**확장 프로그램 (선택)**:
- Markdown All in One: 목차 자동 생성
- Markdown Preview Enhanced: 고급 미리보기
- Markdown PDF: PDF 변환

### 방법 2: GitHub에 업로드

**장점**:
- 자동 렌더링 (예쁨)
- 목차 자동 생성
- Mermaid 다이어그램 자동 표시
- 검색 가능
- 버전 관리

**업로드 방법**:
```bash
cd "C:\새 폴더\scada_ai_project"

# Git 초기화 (처음만)
git init
git add docs/
git commit -m "Add documentation"

# GitHub 레포지토리 생성 후
git remote add origin https://github.com/yourusername/scada-ai.git
git push -u origin main
```

**접속**:
- https://github.com/yourusername/scada-ai/tree/main/docs

### 방법 3: 브라우저 확장 프로그램

**Chrome/Edge**:
1. Chrome 웹 스토어에서 "Markdown Viewer" 검색
2. 설치
3. 확장 프로그램 설정 → "파일 URL 접근 허용" 체크
4. MD 파일을 브라우저로 드래그

**Firefox**:
1. Add-ons에서 "Markdown Viewer Webext" 검색
2. 설치
3. MD 파일을 브라우저로 드래그

### 방법 4: 온라인 Markdown 에디터

**Dillinger** (https://dillinger.io/):
1. 사이트 접속
2. MD 파일 내용 복사
3. 왼쪽에 붙여넣기
4. 오른쪽에 실시간 미리보기
5. Export → PDF/HTML 다운로드

**StackEdit** (https://stackedit.io/):
1. 사이트 접속
2. MD 파일 가져오기
3. 편집 및 미리보기
4. Google Drive 연동 가능

### 방법 5: PDF로 변환

**VS Code에서**:
1. "Markdown PDF" 확장 프로그램 설치
2. MD 파일 열기
3. `Ctrl + Shift + P`
4. "Markdown PDF: Export (pdf)" 선택

**명령줄에서**:
```bash
# pandoc 설치 (https://pandoc.org/)
choco install pandoc  # Windows (Chocolatey)

# PDF 변환
pandoc 01_프로젝트_개요.md -o 01_프로젝트_개요.pdf

# 모든 MD 파일 PDF 변환
cd "C:\새 폴더\scada_ai_project\docs"
for %f in (*.md) do pandoc "%f" -o "%~nf.pdf"
```

## 문서별 설명

### 01_프로젝트_개요.md
**내용**: 프로젝트 전체 개요
- 프로젝트 정보 (버전, 기간, 환경)
- 개발 성과 (코드 규모, 시스템 수)
- 주요 기능 (10대 모듈)
- 시스템 아키텍처
- API 엔드포인트 (20개)
- 센서 목록 (5개)
- 접속 정보

**추천 대상**:
- 프로젝트를 처음 접하는 사람
- 경영진, 관리자
- 5분 안에 전체 이해 필요한 경우

### 02_개발계획서.md
**내용**: 개발 전략 및 계획
- 개발 방법론 (2단계 접근)
- 요구사항 정의 (FR, NFR)
- 시스템 설계 (아키텍처, DB, API)
- 일정 계획 (12시간 타임라인)
- 리스크 관리
- 품질 보증 계획

**추천 대상**:
- 프로젝트 매니저
- 개발팀 리더
- 비슷한 프로젝트 기획하는 사람

### 03_기술개발일지.md
**내용**: 시간대별 개발 과정
- 시간대별 작업 기록 (10:00~18:00)
- 8개 주요 문제 발견 및 해결
- 의사결정 과정
- 코드 작성 통계
- 성과 지표

**추천 대상**:
- 개발자
- 개발 과정이 궁금한 사람
- 회고(Retrospective) 자료

### 04_완료보고서/ (7개 문서)

#### 01_전체_요약.md
- 프로젝트 전체 요약
- 달성 목표 및 성과
- 주요 수치 및 통계

#### 02_간단버전_분석.md (누락)
- MVP 버전 상세 분석
- 5개 파일, 575줄

#### 03_고도화버전_분석.md
- Enterprise 버전 상세 분석
- 26개 파일, 14,245줄
- 10대 모듈 상세 설명

#### 04_비교분석표.md
- 간단 vs 고도화 비교
- 19개 섹션
- 상세 비교표

#### 05_파일구조_분석.md
- 전체 파일 시스템 분석
- 디렉토리 구조
- 파일별 역할

#### 06_코드_상세분석.md
- 핵심 코드 분석
- 알고리즘 설명
- 설계 패턴

#### 07_문제해결_과정.md
- 9개 문제 상세 기록
- 해결 과정 (시간 포함)
- 배운 점

**추천 대상**:
- 기술 담당자
- 코드 리뷰어
- 포트폴리오 검토자

### 05_사용자_가이드.md
**내용**: 사용자 매뉴얼
- 설치 방법
- 로그인 및 인증
- 주요 기능 사용법
- API 호출 예시
- 트러블슈팅
- FAQ

**추천 대상**:
- 최종 사용자
- 시스템 관리자
- 운영 담당자

### 06_향후_개선계획.md
**내용**: 개선 및 확장 계획
- 단기 (1-3개월): 웹 UI, 알림
- 중기 (3-6개월): 메시지 큐, 클라우드, Kubernetes
- 장기 (6-12개월): AI 고도화, 하드웨어 연동
- 예산 및 일정
- 리스크 관리

**추천 대상**:
- 경영진
- 투자자
- 프로젝트 스폰서

## 다이어그램 보기

### diagrams/system_architecture.md

**8개 Mermaid 다이어그램 포함**:
1. 전체 시스템 아키텍처
2. 데이터 흐름
3. 인증 흐름
4. Docker 컨테이너 구조
5. AI/ML 파이프라인
6. 보안 계층
7. 규정 준수 프레임워크
8. 배포 파이프라인

**보는 방법**:

1. **GitHub**: 자동 렌더링
2. **VS Code**: "Markdown Preview Mermaid Support" 확장
3. **온라인**: https://mermaid.live/ 에서 코드 붙여넣기
4. **PNG 변환**:
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   mmdc -i system_architecture.md -o architecture.png
   ```

## 스크린샷 캡처

### screenshots/README.md

**캡처 대상**:
- 간단 버전: 4개 스크린샷
- 고도화 버전: 6개 스크린샷

**상세 가이드**:
- 캡처 방법
- 실행 순서
- cURL 명령어
- 문제 해결

**위치**: `docs/screenshots/README.md` 참조

## 문서 활용 방법

### 1. 프레젠테이션 자료로 사용

**Power Point/Google Slides**:
1. MD 파일을 PDF로 변환
2. PDF를 이미지로 변환 (온라인 도구)
3. 슬라이드에 삽입

**또는**:
1. VS Code에서 MD 파일 열기
2. 미리보기 화면 캡처
3. 슬라이드에 삽입

### 2. 포트폴리오로 사용

**GitHub Pages**:
```bash
# docs 폴더를 GitHub Pages로 발행
# GitHub 레포지토리 Settings → Pages → Source: docs/ 선택
```

**접속**: https://yourusername.github.io/scada-ai/

### 3. 기술 블로그 포스팅

MD 파일 내용을 그대로 복사하여 기술 블로그에 게시:
- Medium
- Dev.to
- Velog
- Tistory

### 4. PDF 보고서로 제출

모든 MD 파일을 PDF로 변환하여 하나의 보고서로 합치기:

```bash
# pandoc으로 여러 MD를 하나의 PDF로
pandoc \
  01_프로젝트_개요.md \
  02_개발계획서.md \
  03_기술개발일지.md \
  04_완료보고서/*.md \
  05_사용자_가이드.md \
  06_향후_개선계획.md \
  -o SCADA_AI_완료보고서.pdf
```

## 문서 검색

### VS Code에서 검색

1. 문서 폴더 열기: `code "C:\새 폴더\scada_ai_project\docs"`
2. `Ctrl + Shift + F` (전체 검색)
3. 키워드 입력 (예: "TensorFlow", "Docker", "인증")

### grep 명령어 (PowerShell/WSL)

```bash
# 모든 MD 파일에서 키워드 검색
cd "C:\새 폴더\scada_ai_project\docs"
grep -r "TensorFlow" *.md
grep -r "문제" *.md
```

## 문서 업데이트

### 버전 관리

각 문서 하단에 버전 정보 포함:
```
**문서 버전**: 1.0
**작성일**: 2025년 10월 14일
```

업데이트 시:
```
**문서 버전**: 1.1
**작성일**: 2025년 10월 14일
**수정일**: 2025년 10월 15일
**변경사항**: 스크린샷 추가
```

### Git으로 관리

```bash
# 변경사항 커밋
git add docs/
git commit -m "Update documentation: add screenshots"
git push
```

## 문서 작성 규칙

본 프로젝트 문서는 다음 규칙을 따릅니다:

1. **이모지 없음**: 전문성 유지
2. **명확한 제목**: 계층 구조 (##, ###)
3. **코드 블록**: 언어 지정 (```python, ```bash)
4. **표**: 정보 정리
5. **링크**: 파일 경로, URL 명시
6. **예시**: 실행 가능한 코드

## 추가 자료

### 공식 문서
- FastAPI: https://fastapi.tiangolo.com/
- TensorFlow: https://www.tensorflow.org/
- Docker: https://docs.docker.com/
- PostgreSQL: https://www.postgresql.org/docs/

### Markdown 가이드
- 기본 문법: https://www.markdownguide.org/
- GitHub Markdown: https://guides.github.com/features/mastering-markdown/
- Mermaid 다이어그램: https://mermaid.js.org/

## 문의

문서 관련 문의사항이 있으면:
1. GitHub Issues 생성
2. 문서 하단 "문서 버전" 명시
3. 구체적인 질문 작성

---

**문서 가이드 버전**: 1.0
**작성일**: 2025년 10월 14일
**위치**: `C:\새 폴더\scada_ai_project\docs\README.md`
