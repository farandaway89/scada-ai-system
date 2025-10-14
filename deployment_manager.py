"""
Configuration Management and Deployment Tools
구성 관리 및 배포 도구
"""

import os
import yaml
import json
import docker
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import subprocess
import shutil
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import psutil
import requests
import time
from jinja2 import Template
import zipfile
import hashlib

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class DeploymentStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class ConfigProfile:
    name: str
    environment: str
    database: Dict[str, Any]
    redis: Dict[str, Any]
    api: Dict[str, Any]
    monitoring: Dict[str, Any]
    security: Dict[str, Any]

@dataclass
class DeploymentRecord:
    id: str
    version: str
    environment: str
    timestamp: str
    status: str
    config_hash: str
    rollback_version: Optional[str] = None
    deploy_time_seconds: Optional[float] = None
    error_message: Optional[str] = None

class ConfigurationManager:
    """구성 관리자"""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.profiles = {}
        self.load_profiles()

    def create_profile(self, profile: ConfigProfile):
        """구성 프로필 생성"""
        profile_path = self.config_dir / f"{profile.name}.yaml"

        config_data = {
            "profile": asdict(profile),
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }

        with open(profile_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        self.profiles[profile.name] = profile
        logger.info(f"Configuration profile created: {profile.name}")

    def load_profiles(self):
        """모든 프로필 로드"""
        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)

                profile_data = config_data.get("profile", {})
                profile = ConfigProfile(**profile_data)
                self.profiles[profile.name] = profile

            except Exception as e:
                logger.error(f"Failed to load profile {config_file}: {e}")

    def get_profile(self, name: str) -> Optional[ConfigProfile]:
        """프로필 조회"""
        return self.profiles.get(name)

    def update_profile(self, name: str, updates: Dict[str, Any]):
        """프로필 업데이트"""
        if name not in self.profiles:
            raise ValueError(f"Profile {name} not found")

        profile = self.profiles[name]
        profile_dict = asdict(profile)

        # 중첩된 딕셔너리 업데이트
        for key, value in updates.items():
            if '.' in key:
                keys = key.split('.')
                current = profile_dict
                for k in keys[:-1]:
                    current = current[k]
                current[keys[-1]] = value
            else:
                profile_dict[key] = value

        updated_profile = ConfigProfile(**profile_dict)
        self.create_profile(updated_profile)

    def validate_profile(self, profile: ConfigProfile) -> List[str]:
        """프로필 유효성 검사"""
        errors = []

        # 필수 필드 확인
        if not profile.database.get('host'):
            errors.append("Database host is required")

        if not profile.redis.get('host'):
            errors.append("Redis host is required")

        if profile.api.get('port', 0) <= 0:
            errors.append("Valid API port is required")

        # 보안 설정 확인
        if profile.environment == Environment.PRODUCTION.value:
            if not profile.security.get('secret_key'):
                errors.append("Secret key is required for production")

            if profile.database.get('password') == 'default':
                errors.append("Default database password not allowed in production")

        return errors

    def export_profile(self, name: str, output_path: str):
        """프로필 내보내기"""
        profile = self.get_profile(name)
        if not profile:
            raise ValueError(f"Profile {name} not found")

        config_data = {
            "profile": asdict(profile),
            "exported_at": datetime.utcnow().isoformat(),
            "export_version": "1.0.0"
        }

        with open(output_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)

        logger.info(f"Profile exported to: {output_path}")

class ContainerManager:
    """컨테이너 관리자"""

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.client = None

    def build_image(self, dockerfile_path: str, tag: str, context_path: str = ".") -> bool:
        """Docker 이미지 빌드"""
        if not self.client:
            return False

        try:
            dockerfile_path = Path(dockerfile_path)
            if not dockerfile_path.exists():
                self.create_dockerfile(dockerfile_path)

            # 이미지 빌드
            image, logs = self.client.images.build(
                path=context_path,
                dockerfile=str(dockerfile_path),
                tag=tag,
                rm=True
            )

            logger.info(f"Docker image built successfully: {tag}")
            return True

        except Exception as e:
            logger.error(f"Failed to build Docker image: {e}")
            return False

    def create_dockerfile(self, dockerfile_path: Path):
        """Dockerfile 생성"""
        dockerfile_content = """
FROM python:3.9-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \\
    gcc \\
    default-libmysqlclient-dev \\
    pkg-config \\
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/api/health || exit 1

# 애플리케이션 실행
CMD ["python", "enterprise_backend.py"]
"""

        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content.strip())

        logger.info(f"Dockerfile created: {dockerfile_path}")

    def create_compose_file(self, output_path: str, config: ConfigProfile):
        """Docker Compose 파일 생성"""
        compose_template = Template("""
version: '3.8'

services:
  scada-api:
    build: .
    ports:
      - "{{ api.port }}:8000"
    environment:
      - DB_HOST={{ database.host }}
      - DB_PORT={{ database.port }}
      - DB_NAME={{ database.name }}
      - DB_USER={{ database.user }}
      - DB_PASSWORD={{ database.password }}
      - REDIS_HOST={{ redis.host }}
      - REDIS_PORT={{ redis.port }}
      - SECRET_KEY={{ security.secret_key }}
    depends_on:
      - mysql
      - redis
    networks:
      - scada-network
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD={{ database.password }}
      - MYSQL_DATABASE={{ database.name }}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./sql:/docker-entrypoint-initdb.d
    ports:
      - "{{ database.port }}:3306"
    networks:
      - scada-network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "{{ redis.port }}:6379"
    volumes:
      - redis_data:/data
    networks:
      - scada-network
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - scada-api
    networks:
      - scada-network
    restart: unless-stopped

volumes:
  mysql_data:
  redis_data:

networks:
  scada-network:
    driver: bridge
""")

        rendered = compose_template.render(asdict(config))

        with open(output_path, 'w') as f:
            f.write(rendered)

        logger.info(f"Docker Compose file created: {output_path}")

    def deploy_containers(self, compose_file: str = "docker-compose.yml") -> bool:
        """컨테이너 배포"""
        try:
            # Docker Compose로 배포
            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "up", "-d"],
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("Containers deployed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to deploy containers: {e.stderr}")
            return False

    def stop_containers(self, compose_file: str = "docker-compose.yml") -> bool:
        """컨테이너 중지"""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", compose_file, "down"],
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("Containers stopped successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop containers: {e.stderr}")
            return False

class SystemMonitor:
    """시스템 모니터링"""

    @staticmethod
    def check_system_requirements() -> Dict[str, bool]:
        """시스템 요구사항 확인"""
        checks = {}

        # CPU 확인
        cpu_count = psutil.cpu_count()
        checks['cpu_cores'] = cpu_count >= 2

        # 메모리 확인
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        checks['memory_gb'] = memory_gb >= 4

        # 디스크 확인
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024**3)
        checks['disk_space'] = disk_free_gb >= 10

        # Docker 확인
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            checks['docker'] = True
        except:
            checks['docker'] = False

        # Python 버전 확인
        import sys
        checks['python_version'] = sys.version_info >= (3, 7)

        return checks

    @staticmethod
    def check_service_health(base_url: str) -> Dict[str, Any]:
        """서비스 상태 확인"""
        health_status = {
            'api_server': False,
            'database': False,
            'redis': False,
            'response_time': None
        }

        try:
            # API 서버 확인
            start_time = time.time()
            response = requests.get(f"{base_url}/api/health", timeout=10)
            response_time = time.time() - start_time

            if response.status_code == 200:
                health_status['api_server'] = True
                health_status['response_time'] = response_time

                # 데이터베이스 및 Redis 상태는 API 응답에서 확인
                health_data = response.json()
                health_status['database'] = health_data.get('database', False)
                health_status['redis'] = health_data.get('redis', False)

        except Exception as e:
            logger.error(f"Health check failed: {e}")

        return health_status

class DeploymentManager:
    """배포 관리자"""

    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self.container_manager = ContainerManager()
        self.deployment_history = []

    def deploy(self, profile_name: str, version: str) -> DeploymentRecord:
        """애플리케이션 배포"""
        start_time = time.time()
        deployment_id = f"deploy_{int(time.time())}"

        deployment_record = DeploymentRecord(
            id=deployment_id,
            version=version,
            environment=profile_name,
            timestamp=datetime.utcnow().isoformat(),
            status=DeploymentStatus.PENDING.value,
            config_hash=""
        )

        try:
            # 1. 프로필 가져오기 및 검증
            profile = self.config_manager.get_profile(profile_name)
            if not profile:
                raise ValueError(f"Profile {profile_name} not found")

            validation_errors = self.config_manager.validate_profile(profile)
            if validation_errors:
                raise ValueError(f"Profile validation failed: {validation_errors}")

            # 2. 구성 해시 생성
            config_str = json.dumps(asdict(profile), sort_keys=True)
            config_hash = hashlib.sha256(config_str.encode()).hexdigest()
            deployment_record.config_hash = config_hash

            deployment_record.status = DeploymentStatus.IN_PROGRESS.value

            # 3. 시스템 요구사항 확인
            system_checks = SystemMonitor.check_system_requirements()
            failed_checks = [k for k, v in system_checks.items() if not v]
            if failed_checks:
                raise ValueError(f"System requirements not met: {failed_checks}")

            # 4. 백업 생성 (프로덕션 환경)
            if profile.environment == Environment.PRODUCTION.value:
                self.create_backup(deployment_id)

            # 5. Docker Compose 파일 생성
            compose_file = f"docker-compose.{profile_name}.yml"
            self.container_manager.create_compose_file(compose_file, profile)

            # 6. 컨테이너 배포
            if not self.container_manager.deploy_containers(compose_file):
                raise RuntimeError("Container deployment failed")

            # 7. 서비스 상태 확인
            time.sleep(10)  # 서비스 시작 대기
            health_status = SystemMonitor.check_service_health(f"http://localhost:{profile.api['port']}")

            if not health_status['api_server']:
                raise RuntimeError("Service health check failed")

            # 8. 배포 완료
            deployment_record.status = DeploymentStatus.SUCCESS.value
            deployment_record.deploy_time_seconds = time.time() - start_time

            logger.info(f"Deployment successful: {deployment_id}")

        except Exception as e:
            deployment_record.status = DeploymentStatus.FAILED.value
            deployment_record.error_message = str(e)
            deployment_record.deploy_time_seconds = time.time() - start_time

            logger.error(f"Deployment failed: {e}")

            # 실패 시 롤백
            if profile.environment == Environment.PRODUCTION.value:
                self.rollback(deployment_record)

        finally:
            self.deployment_history.append(deployment_record)

        return deployment_record

    def rollback(self, failed_deployment: DeploymentRecord):
        """배포 롤백"""
        try:
            # 이전 성공한 배포 찾기
            successful_deployments = [
                d for d in self.deployment_history
                if d.environment == failed_deployment.environment
                and d.status == DeploymentStatus.SUCCESS.value
                and d.id != failed_deployment.id
            ]

            if not successful_deployments:
                logger.warning("No previous successful deployment found for rollback")
                return

            last_successful = max(successful_deployments, key=lambda x: x.timestamp)

            # 롤백 실행
            logger.info(f"Rolling back to deployment: {last_successful.id}")

            # 이전 구성으로 재배포
            profile = self.config_manager.get_profile(failed_deployment.environment)
            compose_file = f"docker-compose.{failed_deployment.environment}.yml"

            self.container_manager.stop_containers(compose_file)
            time.sleep(5)
            self.container_manager.deploy_containers(compose_file)

            failed_deployment.status = DeploymentStatus.ROLLED_BACK.value
            failed_deployment.rollback_version = last_successful.version

            logger.info("Rollback completed successfully")

        except Exception as e:
            logger.error(f"Rollback failed: {e}")

    def create_backup(self, deployment_id: str):
        """배포 전 백업 생성"""
        backup_dir = Path(f"backups/pre_deploy_{deployment_id}")
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 구성 파일 백업
            shutil.copytree("configs", backup_dir / "configs")

            # 데이터베이스 백업 (간단한 예시)
            # 실제로는 mysqldump 등 사용
            logger.info(f"Backup created: {backup_dir}")

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")

    def create_deployment_package(self, version: str, output_path: str):
        """배포 패키지 생성"""
        package_path = Path(output_path)
        package_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 애플리케이션 파일들
            for file_path in Path('.').rglob('*.py'):
                if 'venv' not in str(file_path) and '__pycache__' not in str(file_path):
                    zipf.write(file_path)

            # 구성 파일들
            for file_path in Path('configs').rglob('*'):
                if file_path.is_file():
                    zipf.write(file_path)

            # 요구사항 파일
            if Path('requirements.txt').exists():
                zipf.write('requirements.txt')

            # 배포 정보 파일
            deploy_info = {
                'version': version,
                'created_at': datetime.utcnow().isoformat(),
                'files_count': len(zipf.namelist())
            }

            zipf.writestr('deploy_info.json', json.dumps(deploy_info, indent=2))

        logger.info(f"Deployment package created: {package_path}")
        return str(package_path)

def create_default_configurations():
    """기본 구성 생성"""
    config_manager = ConfigurationManager()

    # 개발 환경 구성
    dev_config = ConfigProfile(
        name="development",
        environment=Environment.DEVELOPMENT.value,
        database={
            "host": "localhost",
            "port": 3306,
            "name": "scada_db",
            "user": "root",
            "password": "1234"
        },
        redis={
            "host": "localhost",
            "port": 6379
        },
        api={
            "host": "0.0.0.0",
            "port": 8000,
            "debug": True
        },
        monitoring={
            "enabled": True,
            "log_level": "DEBUG"
        },
        security={
            "secret_key": "dev-secret-key",
            "cors_origins": ["*"]
        }
    )

    # 프로덕션 환경 구성
    prod_config = ConfigProfile(
        name="production",
        environment=Environment.PRODUCTION.value,
        database={
            "host": "prod-mysql",
            "port": 3306,
            "name": "scada_db",
            "user": "scada_user",
            "password": "secure-password"
        },
        redis={
            "host": "prod-redis",
            "port": 6379
        },
        api={
            "host": "0.0.0.0",
            "port": 8000,
            "debug": False
        },
        monitoring={
            "enabled": True,
            "log_level": "INFO"
        },
        security={
            "secret_key": "production-secret-key",
            "cors_origins": ["https://app.company.com"]
        }
    )

    config_manager.create_profile(dev_config)
    config_manager.create_profile(prod_config)

    return config_manager

def create_deployment_scripts():
    """배포 스크립트 생성"""

    # 배포 스크립트
    deploy_script = '''#!/bin/bash

# SCADA AI System Deployment Script
set -e

ENVIRONMENT=${1:-development}
VERSION=${2:-latest}

echo "Deploying SCADA AI System..."
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"

# 시스템 요구사항 확인
python3 -c "import deployment_manager; deployment_manager.SystemMonitor.check_system_requirements()"

# 배포 실행
python3 -c "
import deployment_manager
config_manager = deployment_manager.create_default_configurations()
deploy_manager = deployment_manager.DeploymentManager(config_manager)
result = deploy_manager.deploy('$ENVIRONMENT', '$VERSION')
print(f'Deployment result: {result.status}')
if result.status == 'failed':
    print(f'Error: {result.error_message}')
    exit(1)
"

echo "Deployment completed successfully!"
'''

    # 헬스체크 스크립트
    health_check_script = '''#!/bin/bash

# SCADA AI System Health Check Script
API_URL=${1:-http://localhost:8000}

echo "Checking system health..."

python3 -c "
import deployment_manager
import sys

health = deployment_manager.SystemMonitor.check_service_health('$API_URL')
print(f'API Server: {\"✓\" if health[\"api_server\"] else \"✗\"}')
print(f'Database: {\"✓\" if health[\"database\"] else \"✗\"}')
print(f'Redis: {\"✓\" if health[\"redis\"] else \"✗\"}')
print(f'Response Time: {health[\"response_time\"]:.3f}s' if health['response_time'] else 'N/A')

if not all([health['api_server'], health['database'], health['redis']]):
    print('Health check failed!')
    sys.exit(1)
else:
    print('All systems operational!')
"
'''

    # 스크립트 파일 생성
    with open("deploy.sh", "w") as f:
        f.write(deploy_script)

    with open("health_check.sh", "w") as f:
        f.write(health_check_script)

    # 실행 권한 부여
    os.chmod("deploy.sh", 0o755)
    os.chmod("health_check.sh", 0o755)

    logger.info("Deployment scripts created successfully")

if __name__ == "__main__":
    # 기본 구성 생성
    config_manager = create_default_configurations()

    # 배포 관리자 초기화
    deploy_manager = DeploymentManager(config_manager)

    # 배포 스크립트 생성
    create_deployment_scripts()

    # 배포 패키지 생성 예시
    package_path = deploy_manager.create_deployment_package("v2.0.0", "dist/scada-ai-v2.0.0.zip")

    print("Deployment system initialized successfully:")
    print(f"- Configuration profiles created in ./configs/")
    print(f"- Deployment scripts: deploy.sh, health_check.sh")
    print(f"- Deployment package: {package_path}")
    print(f"- Usage: ./deploy.sh production v2.0.0")