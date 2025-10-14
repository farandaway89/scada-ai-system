@echo off
chcp 65001 >nul
echo ============================================================
echo SCADA AI 시스템 문서 열기
echo ============================================================
echo.
echo HTML 파일을 브라우저로 열겠습니다.
echo PDF로 저장하려면: Ctrl+P → "대상: PDF로 저장" → 저장
echo.
pause

start "" "html_output\01_프로젝트_개요.html"
timeout /t 2 /nobreak >nul

start "" "html_output\02_개발계획서.html"
timeout /t 2 /nobreak >nul

start "" "html_output\03_기술개발일지.html"
timeout /t 2 /nobreak >nul

start "" "html_output\01_전체_요약.html"
timeout /t 2 /nobreak >nul

start "" "html_output\03_고도화버전_분석.html"
timeout /t 2 /nobreak >nul

start "" "html_output\04_비교분석표.html"
timeout /t 2 /nobreak >nul

start "" "html_output\05_파일구조_분석.html"
timeout /t 2 /nobreak >nul

start "" "html_output\06_코드_상세분석.html"
timeout /t 2 /nobreak >nul

start "" "html_output\07_문제해결_과정.html"
timeout /t 2 /nobreak >nul

start "" "html_output\05_사용자_가이드.html"
timeout /t 2 /nobreak >nul

start "" "html_output\06_향후_개선계획.html"

echo.
echo ============================================================
echo 모든 문서가 열렸습니다!
echo ============================================================
echo.
echo PDF 저장 방법:
echo 1. 각 탭에서 Ctrl+P 누르기
echo 2. "대상" 에서 "PDF로 저장" 선택
echo 3. 파일명 확인하고 저장
echo.
echo 또는 html_output 폴더를 직접 열려면:
echo start html_output
echo.
pause
