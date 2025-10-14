# GitHub 업로드 가이드

## 현재 상태

Git 저장소가 초기화되고 모든 파일이 커밋되었습니다.

**커밋 정보**:
- 커밋 1: Initial commit (80 files, 43,431 insertions)
- 커밋 2: README.md 추가 (283 lines)
- 총 파일: 81개
- 브랜치: master

## GitHub에 업로드하는 방법

### 방법 1: GitHub 웹사이트에서 레포지토리 생성 (권장)

#### 1단계: GitHub 로그인
```
https://github.com/login
```

#### 2단계: 새 레포지토리 생성
1. GitHub 우측 상단 `+` 클릭 → `New repository`
2. 레포지토리 정보 입력:
   - **Repository name**: `scada-ai-system` (또는 원하는 이름)
   - **Description**: `Industrial SCADA System with AI/ML Analytics`
   - **Public/Private**: 선택 (공개/비공개)
   - **Initialize**: 체크하지 않음 (이미 프로젝트가 있음)
3. `Create repository` 클릭

#### 3단계: 레포지토리 URL 복사
생성 후 표시되는 URL을 복사:
```
https://github.com/yourusername/scada-ai-system.git
```

#### 4단계: 로컬에서 원격 저장소 연결 및 푸시

**PowerShell 또는 Git Bash에서**:

```bash
# 프로젝트 디렉토리로 이동
cd "C:\developer\scada_ai_project"

# 원격 저장소 추가 (URL을 실제 GitHub URL로 변경)
git remote add origin https://github.com/yourusername/scada-ai-system.git

# 메인 브랜치 이름 확인 및 변경 (필요시)
git branch -M main

# GitHub에 푸시
git push -u origin main
```

**인증 방법**:
- Personal Access Token (PAT) 사용 권장
- Username: GitHub 사용자명
- Password: Personal Access Token (PAT)

### 방법 2: GitHub Desktop 사용 (가장 쉬움)

#### 1단계: GitHub Desktop 설치
```
https://desktop.github.com/
```

#### 2단계: GitHub Desktop에서 로그인
1. GitHub Desktop 실행
2. `File` → `Options` → `Accounts`
3. `Sign in` 클릭하여 GitHub 계정 로그인

#### 3단계: 로컬 레포지토리 추가
1. `File` → `Add local repository`
2. 경로 입력: `C:\developer\scada_ai_project`
3. `Add repository` 클릭

#### 4단계: GitHub에 퍼블리시
1. `Publish repository` 버튼 클릭
2. 레포지토리 이름 확인: `scada-ai-system`
3. Description 입력 (선택)
4. `Keep this code private` 체크 (비공개시)
5. `Publish repository` 클릭

완료! 자동으로 GitHub에 업로드됩니다.

### 방법 3: GitHub CLI 사용

#### 1단계: GitHub CLI 설치
```bash
# Windows (winget)
winget install --id GitHub.cli

# 또는 Chocolatey
choco install gh
```

#### 2단계: 인증
```bash
gh auth login
```
화면 안내에 따라 로그인

#### 3단계: 레포지토리 생성 및 푸시
```bash
cd "C:\developer\scada_ai_project"

# 레포지토리 생성 (public)
gh repo create scada-ai-system --public --source=. --push

# 또는 private
gh repo create scada-ai-system --private --source=. --push
```

## Personal Access Token (PAT) 생성 방법

명령줄에서 Git push할 때 필요합니다.

### 1단계: GitHub 설정
```
https://github.com/settings/tokens
```

### 2단계: 새 토큰 생성
1. `Generate new token` → `Generate new token (classic)` 클릭
2. Note: `SCADA AI System Upload`
3. Expiration: `90 days` (또는 원하는 기간)
4. 권한 선택:
   - [x] repo (전체 선택)
   - [x] workflow
5. `Generate token` 클릭

### 3단계: 토큰 복사 및 저장
**중요**: 토큰은 한 번만 표시됩니다. 안전한 곳에 저장하세요.

### 4단계: Git에서 사용
```bash
# Git push 시
Username: yourusername
Password: ghp_xxxxxxxxxxxxxxxxxxxxx (PAT 붙여넣기)
```

## 푸시 후 확인

업로드 완료 후:

1. GitHub 레포지토리 페이지 방문:
   ```
   https://github.com/yourusername/scada-ai-system
   ```

2. 확인 사항:
   - 81개 파일 모두 업로드됨
   - README.md가 메인 페이지에 표시됨
   - `/docs` 폴더의 한글 MD 파일 정상 표시
   - Commit 2개 확인

## 추가 설정 (선택)

### GitHub Pages 활성화 (문서 웹 호스팅)

1. 레포지토리 `Settings` → `Pages`
2. Source: `Deploy from a branch`
3. Branch: `main` / Folder: `/docs`
4. `Save` 클릭

접속 URL:
```
https://yourusername.github.io/scada-ai-system/
```

### 레포지토리 설명 추가

1. 레포지토리 메인 페이지
2. 우측 상단 톱니바퀴 아이콘 (About) 클릭
3. Description 입력:
   ```
   Industrial SCADA System with AI/ML Analytics for Water Treatment Facilities
   ```
4. Website (선택): GitHub Pages URL
5. Topics 추가:
   ```
   scada, iot, ai, machine-learning, tensorflow, fastapi, docker,
   industrial-automation, water-treatment, real-time-monitoring
   ```
6. `Save changes` 클릭

## 자주 묻는 질문

### Q1: 푸시 시 인증 실패
**해결**: Personal Access Token 사용. 비밀번호 대신 PAT 입력.

### Q2: 한글 파일명 문제
**해결**: 이미 처리됨. UTF-8 인코딩으로 커밋했습니다.

### Q3: 파일 크기 제한
**해결**: 현재 프로젝트는 모든 파일이 100MB 이하입니다. 문제없습니다.

### Q4: Private vs Public?
**추천**:
- Public: 포트폴리오용, 오픈소스
- Private: 회사/개인 프로젝트

### Q5: git push가 느림
**원인**: 43,000줄 이상 업로드 중. 2-5분 소요 정상.

## 다음 단계

업로드 완료 후:

1. **README 확인**: GitHub에서 README.md가 제대로 표시되는지 확인
2. **문서 확인**: `/docs` 폴더의 한글 MD 파일 렌더링 확인
3. **다이어그램 확인**: `/docs/diagrams/system_architecture.md`의 Mermaid 다이어그램 자동 렌더링
4. **링크 공유**: 포트폴리오, 이력서, LinkedIn에 레포지토리 링크 추가
5. **스타 받기**: 친구들에게 공유하고 스타 받기

## 업로드 완료 체크리스트

업로드 후 확인:

- [ ] GitHub 레포지토리 페이지 접속 확인
- [ ] README.md 정상 표시
- [ ] 81개 파일 모두 업로드됨
- [ ] `/docs` 폴더 한글 파일 정상
- [ ] Commit 히스토리 2개 확인
- [ ] 레포지토리 Description 추가
- [ ] Topics 태그 추가
- [ ] (선택) GitHub Pages 활성화
- [ ] (선택) LICENSE 파일 추가
- [ ] (선택) .github/workflows/ CI/CD 추가

## 문제 발생 시

문제가 발생하면:

1. Git 상태 확인:
   ```bash
   cd "C:\developer\scada_ai_project"
   git status
   git log
   ```

2. 원격 저장소 확인:
   ```bash
   git remote -v
   ```

3. 푸시 재시도:
   ```bash
   git push -u origin main --force
   ```
   **주의**: --force는 신중히 사용

4. GitHub Desktop 사용 (가장 간단)

## 참고 자료

- GitHub 공식 가이드: https://docs.github.com/
- Git 기본 명령어: https://git-scm.com/docs
- GitHub Desktop 가이드: https://docs.github.com/en/desktop

---

**현재 경로**: `C:\developer\scada_ai_project`
**브랜치**: master (또는 main)
**커밋**: 2개
**준비 상태**: GitHub 업로드 준비 완료
