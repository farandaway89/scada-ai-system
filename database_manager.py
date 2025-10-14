"""
Enterprise Database Management System
기업급 데이터베이스 관리 시스템
"""

import asyncio
import asyncpg
import pymongo
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Dict, List, Optional, Any, Union
import redis
import json
from datetime import datetime, timedelta
import logging
import pandas as pd
from contextlib import contextmanager
import hashlib
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
import schedule
import time
import threading
from pathlib import Path
import shutil
import gzip

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    REDIS = "redis"
    TIMESCALEDB = "timescaledb"

class BackupType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"

@dataclass
class DatabaseConfig:
    db_type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    ssl_mode: str = "prefer"

@dataclass
class BackupConfig:
    backup_type: str
    destination: str
    retention_days: int = 30
    compression: bool = True
    encryption: bool = True

class DatabaseConnectionManager:
    """데이터베이스 연결 관리자"""

    def __init__(self):
        self.connections = {}
        self.engines = {}
        self.session_factories = {}

    def register_database(self, name: str, config: DatabaseConfig):
        """데이터베이스 등록"""
        try:
            if config.db_type == DatabaseType.MYSQL.value:
                connection_string = f"mysql+pymysql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
                engine = create_engine(
                    connection_string,
                    poolclass=QueuePool,
                    pool_size=config.pool_size,
                    max_overflow=config.max_overflow,
                    pool_timeout=config.pool_timeout,
                    pool_pre_ping=True,
                    echo=False
                )

            elif config.db_type == DatabaseType.POSTGRESQL.value:
                connection_string = f"postgresql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}?sslmode={config.ssl_mode}"
                engine = create_engine(
                    connection_string,
                    poolclass=QueuePool,
                    pool_size=config.pool_size,
                    max_overflow=config.max_overflow,
                    pool_timeout=config.pool_timeout,
                    pool_pre_ping=True,
                    echo=False
                )

            else:
                raise ValueError(f"Unsupported database type: {config.db_type}")

            self.engines[name] = engine
            self.session_factories[name] = sessionmaker(bind=engine)
            logger.info(f"Database '{name}' registered successfully")

        except Exception as e:
            logger.error(f"Failed to register database '{name}': {e}")
            raise

    @contextmanager
    def get_session(self, db_name: str):
        """세션 컨텍스트 매니저"""
        if db_name not in self.session_factories:
            raise ValueError(f"Database '{db_name}' not registered")

        session = self.session_factories[db_name]()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_engine(self, db_name: str):
        """엔진 반환"""
        if db_name not in self.engines:
            raise ValueError(f"Database '{db_name}' not registered")
        return self.engines[db_name]

class TimeSeriesDataManager:
    """시계열 데이터 관리자"""

    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self.redis_client = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)

    async def insert_sensor_data(self, db_name: str, table_name: str, data: Dict[str, Any]):
        """센서 데이터 삽입"""
        try:
            # 실시간 데이터를 Redis에 캐시
            cache_key = f"latest:{table_name}"
            data_with_timestamp = {**data, "timestamp": datetime.utcnow().isoformat()}
            self.redis_client.setex(cache_key, 300, json.dumps(data_with_timestamp))  # 5분 캐시

            # 데이터베이스에 삽입
            with self.db_manager.get_session(db_name) as session:
                # 동적 테이블 정보 가져오기
                engine = self.db_manager.get_engine(db_name)
                metadata = MetaData()
                metadata.reflect(bind=engine)

                if table_name in metadata.tables:
                    table = metadata.tables[table_name]
                    insert_stmt = table.insert().values(**data)
                    session.execute(insert_stmt)
                else:
                    logger.error(f"Table '{table_name}' not found")

        except Exception as e:
            logger.error(f"Error inserting sensor data: {e}")
            raise

    def get_latest_data(self, table_name: str) -> Optional[Dict[str, Any]]:
        """최신 데이터 조회 (Redis 캐시 우선)"""
        try:
            cache_key = f"latest:{table_name}"
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                return json.loads(cached_data)

            return None

        except Exception as e:
            logger.error(f"Error getting latest data: {e}")
            return None

    def get_time_range_data(self, db_name: str, table_name: str,
                           start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """시간 범위 데이터 조회"""
        try:
            with self.db_manager.get_session(db_name) as session:
                query = f"""
                SELECT * FROM {table_name}
                WHERE timestamp BETWEEN %s AND %s
                ORDER BY timestamp
                """

                engine = self.db_manager.get_engine(db_name)
                df = pd.read_sql(query, engine, params=[start_time, end_time])
                return df

        except Exception as e:
            logger.error(f"Error getting time range data: {e}")
            return pd.DataFrame()

    def aggregate_data(self, db_name: str, table_name: str,
                      start_time: datetime, end_time: datetime,
                      interval: str = '1h') -> pd.DataFrame:
        """데이터 집계 (시간 간격별)"""
        try:
            with self.db_manager.get_session(db_name) as session:
                # PostgreSQL의 경우
                if 'postgresql' in str(self.db_manager.get_engine(db_name).url):
                    query = f"""
                    SELECT
                        date_trunc('{interval}', timestamp) as time_bucket,
                        AVG(ph_value) as avg_ph,
                        AVG(do_value) as avg_do,
                        AVG(turbidity) as avg_turbidity,
                        AVG(tds_value) as avg_tds,
                        AVG(temperature) as avg_temperature,
                        COUNT(*) as data_points
                    FROM {table_name}
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY time_bucket
                    ORDER BY time_bucket
                    """
                else:
                    # MySQL의 경우
                    query = f"""
                    SELECT
                        DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') as time_bucket,
                        AVG(ph_value) as avg_ph,
                        AVG(do_value) as avg_do,
                        AVG(turbidity) as avg_turbidity,
                        AVG(tds_value) as avg_tds,
                        AVG(temperature) as avg_temperature,
                        COUNT(*) as data_points
                    FROM {table_name}
                    WHERE timestamp BETWEEN %s AND %s
                    GROUP BY time_bucket
                    ORDER BY time_bucket
                    """

                engine = self.db_manager.get_engine(db_name)
                df = pd.read_sql(query, engine, params=[start_time, end_time])
                return df

        except Exception as e:
            logger.error(f"Error aggregating data: {e}")
            return pd.DataFrame()

class DataArchiveManager:
    """데이터 아카이브 관리자"""

    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager

    def archive_old_data(self, db_name: str, table_name: str, archive_table: str, days_old: int = 90):
        """오래된 데이터 아카이브"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            with self.db_manager.get_session(db_name) as session:
                # 아카이브 테이블로 데이터 이동
                move_query = f"""
                INSERT INTO {archive_table}
                SELECT * FROM {table_name}
                WHERE timestamp < %s
                """

                # 원본 테이블에서 삭제
                delete_query = f"""
                DELETE FROM {table_name}
                WHERE timestamp < %s
                """

                engine = self.db_manager.get_engine(db_name)

                # 트랜잭션 내에서 실행
                with engine.begin() as conn:
                    result = conn.execute(move_query, [cutoff_date])
                    archived_rows = result.rowcount

                    conn.execute(delete_query, [cutoff_date])

                logger.info(f"Archived {archived_rows} rows from {table_name} to {archive_table}")
                return archived_rows

        except Exception as e:
            logger.error(f"Error archiving data: {e}")
            raise

    def compress_archived_data(self, db_name: str, archive_table: str):
        """아카이브 데이터 압축"""
        try:
            # 아카이브 테이블을 CSV로 내보내기
            with self.db_manager.get_session(db_name) as session:
                query = f"SELECT * FROM {archive_table}"
                engine = self.db_manager.get_engine(db_name)
                df = pd.read_sql(query, engine)

                # 연도별로 분할하여 압축
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    years = df['timestamp'].dt.year.unique()

                    for year in years:
                        year_data = df[df['timestamp'].dt.year == year]

                        # CSV 파일로 저장
                        csv_path = f"archive_{archive_table}_{year}.csv"
                        year_data.to_csv(csv_path, index=False)

                        # 압축
                        with open(csv_path, 'rb') as f_in:
                            with gzip.open(f"{csv_path}.gz", 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)

                        # 원본 CSV 삭제
                        Path(csv_path).unlink()

                        logger.info(f"Compressed archive for year {year}: {csv_path}.gz")

        except Exception as e:
            logger.error(f"Error compressing archived data: {e}")
            raise

class DatabaseBackupManager:
    """데이터베이스 백업 관리자"""

    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager
        self.backup_history = []

    def create_backup(self, db_name: str, backup_config: BackupConfig):
        """백업 생성"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{db_name}_backup_{timestamp}"

            if backup_config.backup_type == BackupType.FULL.value:
                backup_path = self._create_full_backup(db_name, backup_filename, backup_config)
            elif backup_config.backup_type == BackupType.INCREMENTAL.value:
                backup_path = self._create_incremental_backup(db_name, backup_filename, backup_config)
            else:
                raise ValueError(f"Unsupported backup type: {backup_config.backup_type}")

            # 백업 이력 저장
            backup_info = {
                "database": db_name,
                "type": backup_config.backup_type,
                "timestamp": timestamp,
                "file_path": backup_path,
                "size_bytes": Path(backup_path).stat().st_size if Path(backup_path).exists() else 0
            }
            self.backup_history.append(backup_info)

            logger.info(f"Backup created: {backup_path}")
            return backup_info

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise

    def _create_full_backup(self, db_name: str, filename: str, config: BackupConfig) -> str:
        """전체 백업 생성"""
        engine = self.db_manager.get_engine(db_name)
        backup_path = Path(config.destination) / f"{filename}.sql"

        # 테이블별로 데이터 덤프
        metadata = MetaData()
        metadata.reflect(bind=engine)

        with open(backup_path, 'w') as f:
            f.write(f"-- Full backup of {db_name} created at {datetime.utcnow()}\n\n")

            for table_name in metadata.tables:
                df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
                if not df.empty:
                    f.write(f"-- Table: {table_name}\n")
                    # SQL INSERT 문 생성 (간단한 버전)
                    for _, row in df.iterrows():
                        values = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in row.values])
                        f.write(f"INSERT INTO {table_name} VALUES ({values});\n")
                    f.write("\n")

        # 압축 적용
        if config.compression:
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_path.unlink()
            return str(compressed_path)

        return str(backup_path)

    def _create_incremental_backup(self, db_name: str, filename: str, config: BackupConfig) -> str:
        """증분 백업 생성"""
        # 마지막 백업 이후 변경된 데이터만 백업
        last_backup = self._get_last_backup(db_name)

        if not last_backup:
            # 첫 백업이면 전체 백업 수행
            return self._create_full_backup(db_name, filename, config)

        last_backup_time = datetime.strptime(last_backup["timestamp"], "%Y%m%d_%H%M%S")

        engine = self.db_manager.get_engine(db_name)
        backup_path = Path(config.destination) / f"{filename}_incremental.sql"

        with open(backup_path, 'w') as f:
            f.write(f"-- Incremental backup of {db_name} since {last_backup_time}\n\n")

            # timestamp 컬럼이 있는 테이블만 처리
            tables_with_timestamp = ['water_quality_data', 'weather_data', 'predictions', 'alerts']

            for table_name in tables_with_timestamp:
                try:
                    query = f"SELECT * FROM {table_name} WHERE timestamp > %s"
                    df = pd.read_sql(query, engine, params=[last_backup_time])

                    if not df.empty:
                        f.write(f"-- Table: {table_name} (changes since {last_backup_time})\n")
                        for _, row in df.iterrows():
                            values = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in row.values])
                            f.write(f"INSERT INTO {table_name} VALUES ({values});\n")
                        f.write("\n")

                except Exception as e:
                    logger.warning(f"Could not backup table {table_name}: {e}")

        return str(backup_path)

    def _get_last_backup(self, db_name: str) -> Optional[Dict[str, Any]]:
        """마지막 백업 정보 조회"""
        db_backups = [b for b in self.backup_history if b["database"] == db_name]
        return max(db_backups, key=lambda x: x["timestamp"]) if db_backups else None

    def cleanup_old_backups(self, retention_days: int = 30):
        """오래된 백업 정리"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        for backup in self.backup_history[:]:  # 복사본으로 순회
            backup_date = datetime.strptime(backup["timestamp"], "%Y%m%d_%H%M%S")

            if backup_date < cutoff_date:
                try:
                    backup_file = Path(backup["file_path"])
                    if backup_file.exists():
                        backup_file.unlink()
                        logger.info(f"Deleted old backup: {backup['file_path']}")

                    self.backup_history.remove(backup)

                except Exception as e:
                    logger.error(f"Error deleting backup {backup['file_path']}: {e}")

class DatabaseMaintenanceScheduler:
    """데이터베이스 유지보수 스케줄러"""

    def __init__(self, db_manager: DatabaseConnectionManager,
                 archive_manager: DataArchiveManager,
                 backup_manager: DatabaseBackupManager):
        self.db_manager = db_manager
        self.archive_manager = archive_manager
        self.backup_manager = backup_manager
        self.running = False

    def schedule_maintenance_tasks(self):
        """유지보수 작업 스케줄링"""
        # 매일 자정에 백업
        schedule.every().day.at("00:00").do(self._daily_backup)

        # 주간 데이터 아카이브 (일요일 오전 2시)
        schedule.every().sunday.at("02:00").do(self._weekly_archive)

        # 월간 백업 정리 (매월 1일 오전 3시)
        schedule.every().month.do(self._monthly_cleanup)

        # 데이터베이스 최적화 (매주 수요일 오전 1시)
        schedule.every().wednesday.at("01:00").do(self._optimize_database)

    def _daily_backup(self):
        """일일 백업"""
        try:
            backup_config = BackupConfig(
                backup_type=BackupType.INCREMENTAL.value,
                destination="./backups",
                retention_days=30,
                compression=True
            )

            self.backup_manager.create_backup("scada_main", backup_config)
            logger.info("Daily backup completed")

        except Exception as e:
            logger.error(f"Daily backup failed: {e}")

    def _weekly_archive(self):
        """주간 데이터 아카이브"""
        try:
            archived = self.archive_manager.archive_old_data(
                "scada_main",
                "water_quality_data",
                "water_quality_archive",
                days_old=90
            )
            logger.info(f"Weekly archive completed: {archived} rows archived")

        except Exception as e:
            logger.error(f"Weekly archive failed: {e}")

    def _monthly_cleanup(self):
        """월간 정리"""
        try:
            self.backup_manager.cleanup_old_backups(retention_days=90)
            logger.info("Monthly cleanup completed")

        except Exception as e:
            logger.error(f"Monthly cleanup failed: {e}")

    def _optimize_database(self):
        """데이터베이스 최적화"""
        try:
            with self.db_manager.get_session("scada_main") as session:
                # 테이블 분석 및 최적화
                tables = ["water_quality_data", "weather_data", "predictions", "alerts"]

                for table in tables:
                    session.execute(f"ANALYZE TABLE {table}")
                    session.execute(f"OPTIMIZE TABLE {table}")

                logger.info("Database optimization completed")

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")

    def start_scheduler(self):
        """스케줄러 시작"""
        self.running = True

        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 확인

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Database maintenance scheduler started")

    def stop_scheduler(self):
        """스케줄러 중지"""
        self.running = False
        logger.info("Database maintenance scheduler stopped")

# 전역 인스턴스 생성
db_manager = DatabaseConnectionManager()
ts_manager = TimeSeriesDataManager(db_manager)
archive_manager = DataArchiveManager(db_manager)
backup_manager = DatabaseBackupManager(db_manager)
maintenance_scheduler = DatabaseMaintenanceScheduler(db_manager, archive_manager, backup_manager)

# 초기화 함수
def initialize_enterprise_database():
    """기업급 데이터베이스 시스템 초기화"""
    try:
        # 메인 데이터베이스 등록
        main_db_config = DatabaseConfig(
            db_type=DatabaseType.MYSQL.value,
            host="localhost",
            port=3306,
            database="scada_db",
            username="root",
            password="1234",
            pool_size=20,
            max_overflow=30
        )

        db_manager.register_database("scada_main", main_db_config)

        # 유지보수 스케줄러 설정 및 시작
        maintenance_scheduler.schedule_maintenance_tasks()
        maintenance_scheduler.start_scheduler()

        # 백업 디렉토리 생성
        Path("./backups").mkdir(exist_ok=True)
        Path("./archives").mkdir(exist_ok=True)

        logger.info("Enterprise database system initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize enterprise database system: {e}")
        raise

if __name__ == "__main__":
    # 테스트 실행
    initialize_enterprise_database()

    # 테스트 데이터 삽입
    test_data = {
        "ph_value": 7.2,
        "do_value": 5.8,
        "turbidity": 0.15,
        "tds_value": 120,
        "temperature": 22.5,
        "timestamp": datetime.utcnow()
    }

    asyncio.run(ts_manager.insert_sensor_data("scada_main", "water_quality_data", test_data))
    print("Test data inserted successfully")