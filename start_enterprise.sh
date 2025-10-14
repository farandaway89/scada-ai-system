#!/bin/bash

# SCADA AI System Enterprise Edition Startup Script
# 기업급 지능형 수처리 시스템 시작 스크립트

set -e

echo "🏭 SCADA AI System Enterprise Edition v2.0.0"
echo "================================================"
echo "Starting enterprise-grade water treatment management system..."
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 환경 변수 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export ENVIRONMENT=${ENVIRONMENT:-development}

# 함수 정의
check_requirements() {
    echo -e "${BLUE}📋 Checking system requirements...${NC}"

    # Python 버전 확인
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✓ Python version: $python_version"

    # Redis 상태 확인
    if redis-cli ping >/dev/null 2>&1; then
        echo "✓ Redis is running"
    else
        echo -e "${YELLOW}⚠ Redis is not running. Starting Redis...${NC}"
        redis-server --daemonize yes
        sleep 2
    fi

    # MySQL 상태 확인
    if mysqladmin ping >/dev/null 2>&1; then
        echo "✓ MySQL is running"
    else
        echo -e "${YELLOW}⚠ MySQL is not running. Please start MySQL service${NC}"
    fi

    echo ""
}

install_dependencies() {
    echo -e "${BLUE}📦 Installing dependencies...${NC}"

    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate

    echo "Installing enterprise requirements..."
    pip install -r requirements_enterprise.txt

    echo "✓ Dependencies installed"
    echo ""
}

setup_database() {
    echo -e "${BLUE}🗄️ Setting up database...${NC}"

    # 데이터베이스 존재 확인
    if mysql -u root -p1234 -e "USE scada_db;" 2>/dev/null; then
        echo "✓ Database 'scada_db' exists"
    else
        echo "Creating database 'scada_db'..."
        mysql -u root -p1234 -e "CREATE DATABASE scada_db;" 2>/dev/null || {
            echo -e "${RED}✗ Failed to create database. Please check MySQL connection${NC}"
            exit 1
        }
        echo "✓ Database created"
    fi

    echo ""
}

initialize_configs() {
    echo -e "${BLUE}⚙️ Initializing configurations...${NC}"

    # 디렉토리 생성
    mkdir -p configs
    mkdir -p backups
    mkdir -p logs
    mkdir -p sdk

    # 기본 구성 생성
    python3 -c "
import deployment_manager
try:
    config_manager = deployment_manager.create_default_configurations()
    print('✓ Configuration profiles created')
except Exception as e:
    print(f'⚠ Configuration setup warning: {e}')
"

    echo ""
}

start_monitoring() {
    echo -e "${BLUE}📊 Starting monitoring system...${NC}"

    python3 -c "
import monitoring_alerting
try:
    monitoring_alerting.initialize_monitoring_system()
    print('✓ Monitoring system initialized')
except Exception as e:
    print(f'⚠ Monitoring setup warning: {e}')
" &

    echo ""
}

start_enterprise_backend() {
    echo -e "${BLUE}🚀 Starting enterprise backend server...${NC}"
    echo "Environment: $ENVIRONMENT"
    echo "API Documentation: http://localhost:8000/docs"
    echo "Health Check: http://localhost:8000/api/health"
    echo ""
    echo -e "${GREEN}Server is starting...${NC}"
    echo "Press Ctrl+C to stop the server"
    echo ""

    # 엔터프라이즈 백엔드 시작
    python3 enterprise_backend.py
}

# 메인 실행 흐름
main() {
    echo "Starting SCADA AI System Enterprise Edition..."
    echo ""

    # 시스템 요구사항 확인
    check_requirements

    # 의존성 설치
    if [ "$1" = "--install" ] || [ ! -d "venv" ]; then
        install_dependencies
    else
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate
    fi

    # 데이터베이스 설정
    setup_database

    # 구성 초기화
    initialize_configs

    # 모니터링 시스템 시작
    start_monitoring

    # 백엔드 서버 시작
    start_enterprise_backend
}

# 사용법 출력
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --install    Install dependencies before starting"
    echo "  --help       Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  ENVIRONMENT  Set environment (development/staging/production)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start with existing environment"
    echo "  $0 --install          # Install dependencies and start"
    echo "  ENVIRONMENT=production $0  # Start in production mode"
    echo ""
}

# 신호 처리
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down SCADA AI System...${NC}"

    # 백그라운드 프로세스 종료
    jobs -p | xargs -r kill

    echo "✓ System shutdown complete"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 명령행 인수 처리
case "$1" in
    --help|-h)
        usage
        exit 0
        ;;
    --install)
        main --install
        ;;
    *)
        main
        ;;
esac