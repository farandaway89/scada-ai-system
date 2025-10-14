"""
Real-time Monitoring and Alerting System
실시간 모니터링 및 알림 시스템
"""

import asyncio
import websockets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import requests
import redis
import logging
from threading import Thread, Event
import time
import numpy as np
from collections import defaultdict, deque
import uuid
from pathlib import Path
import yaml

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertType(Enum):
    SENSOR_MALFUNCTION = "sensor_malfunction"
    THRESHOLD_VIOLATION = "threshold_violation"
    SYSTEM_ERROR = "system_error"
    COMMUNICATION_FAILURE = "communication_failure"
    MAINTENANCE_REQUIRED = "maintenance_required"
    PERFORMANCE_DEGRADATION = "performance_degradation"

class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    PUSH_NOTIFICATION = "push_notification"

@dataclass
class Alert:
    id: str
    type: str
    severity: str
    title: str
    message: str
    source: str
    timestamp: str
    data: Dict[str, Any]
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None

@dataclass
class Threshold:
    parameter: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    warning_threshold: float = 0.8
    critical_threshold: float = 0.9
    duration_seconds: int = 60
    enabled: bool = True

@dataclass
class NotificationConfig:
    channel: str
    enabled: bool
    config: Dict[str, Any]
    severity_filter: List[str]

class RealTimeMonitor:
    """실시간 모니터링 엔진"""

    def __init__(self):
        self.thresholds = {}
        self.data_buffer = defaultdict(lambda: deque(maxlen=1000))
        self.active_alerts = {}
        self.redis_client = redis.Redis(host='localhost', port=6379, db=3, decode_responses=True)
        self.monitoring_active = False
        self.websocket_clients = set()

    def add_threshold(self, threshold: Threshold):
        """임계값 추가"""
        self.thresholds[threshold.parameter] = threshold
        logger.info(f"Threshold added for parameter: {threshold.parameter}")

    def remove_threshold(self, parameter: str):
        """임계값 제거"""
        if parameter in self.thresholds:
            del self.thresholds[parameter]
            logger.info(f"Threshold removed for parameter: {parameter}")

    def update_data(self, parameter: str, value: float, timestamp: datetime = None):
        """데이터 업데이트 및 임계값 검사"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        data_point = {
            'value': value,
            'timestamp': timestamp.isoformat()
        }

        # 데이터 버퍼에 추가
        self.data_buffer[parameter].append(data_point)

        # Redis에 최신 데이터 저장
        cache_key = f"monitor:{parameter}"
        self.redis_client.setex(cache_key, 300, json.dumps(data_point))

        # 임계값 검사
        self._check_thresholds(parameter, value, timestamp)

        # WebSocket 클라이언트에 실시간 데이터 전송
        asyncio.create_task(self._broadcast_data(parameter, data_point))

    def _check_thresholds(self, parameter: str, value: float, timestamp: datetime):
        """임계값 검사"""
        if parameter not in self.thresholds:
            return

        threshold = self.thresholds[parameter]
        if not threshold.enabled:
            return

        violation_type = None
        severity = None

        # 범위 확인
        if threshold.min_value is not None and value < threshold.min_value:
            violation_type = "below_minimum"
            severity = AlertSeverity.CRITICAL.value
        elif threshold.max_value is not None and value > threshold.max_value:
            violation_type = "above_maximum"
            severity = AlertSeverity.CRITICAL.value

        # 경고 및 위험 임계값 확인
        if threshold.max_value is not None:
            warning_value = threshold.max_value * threshold.warning_threshold
            critical_value = threshold.max_value * threshold.critical_threshold

            if value > critical_value:
                violation_type = "critical_threshold"
                severity = AlertSeverity.CRITICAL.value
            elif value > warning_value:
                violation_type = "warning_threshold"
                severity = AlertSeverity.WARNING.value

        # 알림 생성
        if violation_type:
            alert = Alert(
                id=str(uuid.uuid4()),
                type=AlertType.THRESHOLD_VIOLATION.value,
                severity=severity,
                title=f"{parameter} 임계값 위반",
                message=f"{parameter} 값이 {violation_type}: 현재값 {value}, 기준값 {threshold.max_value or threshold.min_value}",
                source=f"monitor.{parameter}",
                timestamp=timestamp.isoformat(),
                data={
                    "parameter": parameter,
                    "current_value": value,
                    "violation_type": violation_type,
                    "threshold_config": asdict(threshold)
                }
            )

            self._trigger_alert(alert)

    def _trigger_alert(self, alert: Alert):
        """알림 트리거"""
        alert_key = f"{alert.source}_{alert.type}"

        # 중복 알림 방지 (같은 소스에서 5분 내 동일한 타입의 알림)
        if alert_key in self.active_alerts:
            last_alert = self.active_alerts[alert_key]
            last_time = datetime.fromisoformat(last_alert.timestamp)
            if datetime.fromisoformat(alert.timestamp) - last_time < timedelta(minutes=5):
                return

        self.active_alerts[alert_key] = alert

        # Redis에 알림 저장
        alert_data = asdict(alert)
        self.redis_client.lpush("alerts", json.dumps(alert_data))
        self.redis_client.ltrim("alerts", 0, 999)  # 최대 1000개 유지

        # 알림 전송
        AlertingSystem.get_instance().send_alert(alert)

        logger.warning(f"Alert triggered: {alert.title}")

    async def _broadcast_data(self, parameter: str, data_point: Dict[str, Any]):
        """WebSocket을 통한 실시간 데이터 브로드캐스트"""
        if not self.websocket_clients:
            return

        message = {
            "type": "data_update",
            "parameter": parameter,
            "data": data_point
        }

        disconnected_clients = set()
        for client in self.websocket_clients:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)

        # 연결이 끊어진 클라이언트 제거
        self.websocket_clients -= disconnected_clients

    async def register_websocket_client(self, websocket):
        """WebSocket 클라이언트 등록"""
        self.websocket_clients.add(websocket)
        logger.info(f"WebSocket client registered. Total clients: {len(self.websocket_clients)}")

        try:
            # 초기 데이터 전송
            for parameter, buffer in self.data_buffer.items():
                if buffer:
                    latest_data = buffer[-1]
                    message = {
                        "type": "initial_data",
                        "parameter": parameter,
                        "data": latest_data
                    }
                    await websocket.send(json.dumps(message))

            # 클라이언트 연결 유지
            await websocket.wait_closed()

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.websocket_clients.discard(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.websocket_clients)}")

class AlertingSystem:
    """알림 시스템"""

    _instance = None

    def __init__(self):
        self.notification_channels = {}
        self.alert_rules = []
        self.escalation_rules = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_notification_channel(self, channel_name: str, config: NotificationConfig):
        """알림 채널 추가"""
        self.notification_channels[channel_name] = config
        logger.info(f"Notification channel added: {channel_name}")

    def send_alert(self, alert: Alert):
        """알림 전송"""
        for channel_name, config in self.notification_channels.items():
            if not config.enabled:
                continue

            if alert.severity not in config.severity_filter:
                continue

            try:
                if config.channel == NotificationChannel.EMAIL.value:
                    self._send_email(alert, config)
                elif config.channel == NotificationChannel.SLACK.value:
                    self._send_slack(alert, config)
                elif config.channel == NotificationChannel.WEBHOOK.value:
                    self._send_webhook(alert, config)
                elif config.channel == NotificationChannel.SMS.value:
                    self._send_sms(alert, config)

            except Exception as e:
                logger.error(f"Failed to send alert via {channel_name}: {e}")

    def _send_email(self, alert: Alert, config: NotificationConfig):
        """이메일 알림 전송"""
        smtp_config = config.config

        msg = MimeMultipart()
        msg['From'] = smtp_config['from_email']
        msg['To'] = ', '.join(smtp_config['to_emails'])
        msg['Subject'] = f"[SCADA Alert] {alert.title}"

        body = f"""
        알림 유형: {alert.type}
        심각도: {alert.severity}
        시간: {alert.timestamp}
        소스: {alert.source}

        메시지: {alert.message}

        세부 정보:
        {json.dumps(alert.data, indent=2, ensure_ascii=False)}
        """

        msg.attach(MimeText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
            if smtp_config.get('use_tls'):
                server.starttls()
            if smtp_config.get('username'):
                server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)

        logger.info(f"Email alert sent: {alert.title}")

    def _send_slack(self, alert: Alert, config: NotificationConfig):
        """Slack 알림 전송"""
        slack_config = config.config
        webhook_url = slack_config['webhook_url']

        color_map = {
            AlertSeverity.INFO.value: "good",
            AlertSeverity.WARNING.value: "warning",
            AlertSeverity.CRITICAL.value: "danger",
            AlertSeverity.EMERGENCY.value: "danger"
        }

        payload = {
            "attachments": [{
                "color": color_map.get(alert.severity, "warning"),
                "title": alert.title,
                "text": alert.message,
                "fields": [
                    {"title": "심각도", "value": alert.severity, "short": True},
                    {"title": "소스", "value": alert.source, "short": True},
                    {"title": "시간", "value": alert.timestamp, "short": True}
                ],
                "footer": "SCADA Monitoring System",
                "ts": int(datetime.fromisoformat(alert.timestamp).timestamp())
            }]
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

        logger.info(f"Slack alert sent: {alert.title}")

    def _send_webhook(self, alert: Alert, config: NotificationConfig):
        """웹훅 알림 전송"""
        webhook_config = config.config
        url = webhook_config['url']

        payload = asdict(alert)
        headers = webhook_config.get('headers', {'Content-Type': 'application/json'})

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        logger.info(f"Webhook alert sent: {alert.title}")

    def _send_sms(self, alert: Alert, config: NotificationConfig):
        """SMS 알림 전송 (예시 - Twilio)"""
        sms_config = config.config

        # Twilio API 호출 예시
        message = f"[SCADA] {alert.title}: {alert.message}"

        # 실제 SMS 서비스 연동 코드
        logger.info(f"SMS alert would be sent: {message}")

class PerformanceMonitor:
    """성능 모니터링"""

    def __init__(self, monitor: RealTimeMonitor):
        self.monitor = monitor
        self.metrics = defaultdict(list)
        self.running = False

    def start_monitoring(self):
        """성능 모니터링 시작"""
        self.running = True
        thread = Thread(target=self._monitoring_loop, daemon=True)
        thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """성능 모니터링 중지"""
        self.running = False
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.running:
            try:
                # 시스템 성능 메트릭 수집
                metrics = self._collect_system_metrics()

                for metric_name, value in metrics.items():
                    self.monitor.update_data(f"system.{metric_name}", value)

                time.sleep(30)  # 30초마다 수집

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(60)

    def _collect_system_metrics(self) -> Dict[str, float]:
        """시스템 메트릭 수집"""
        import psutil

        metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'network_bytes_sent': psutil.net_io_counters().bytes_sent,
            'network_bytes_recv': psutil.net_io_counters().bytes_recv
        }

        return metrics

class AlertDashboard:
    """알림 대시보드"""

    def __init__(self, redis_client):
        self.redis_client = redis_client

    def get_active_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """활성 알림 조회"""
        alerts_data = self.redis_client.lrange("alerts", 0, limit-1)
        alerts = []

        for alert_json in alerts_data:
            alert_dict = json.loads(alert_json)
            if not alert_dict.get('resolved', False):
                alerts.append(alert_dict)

        return alerts

    def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """알림 통계"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        alerts_data = self.redis_client.lrange("alerts", 0, -1)

        total_alerts = 0
        severity_counts = defaultdict(int)
        type_counts = defaultdict(int)
        resolved_count = 0

        for alert_json in alerts_data:
            alert_dict = json.loads(alert_json)
            alert_time = datetime.fromisoformat(alert_dict['timestamp'])

            if alert_time >= cutoff_time:
                total_alerts += 1
                severity_counts[alert_dict['severity']] += 1
                type_counts[alert_dict['type']] += 1

                if alert_dict.get('resolved', False):
                    resolved_count += 1

        return {
            'total_alerts': total_alerts,
            'resolved_alerts': resolved_count,
            'active_alerts': total_alerts - resolved_count,
            'severity_breakdown': dict(severity_counts),
            'type_breakdown': dict(type_counts),
            'time_period_hours': hours
        }

    def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """알림 확인 처리"""
        alerts_data = self.redis_client.lrange("alerts", 0, -1)

        for i, alert_json in enumerate(alerts_data):
            alert_dict = json.loads(alert_json)

            if alert_dict['id'] == alert_id:
                alert_dict['acknowledged'] = True
                alert_dict['acknowledged_by'] = user_id
                alert_dict['acknowledged_at'] = datetime.utcnow().isoformat()

                # Redis 업데이트
                self.redis_client.lset("alerts", i, json.dumps(alert_dict))
                logger.info(f"Alert {alert_id} acknowledged by {user_id}")
                return True

        return False

    def resolve_alert(self, alert_id: str, user_id: str, resolution_note: str = "") -> bool:
        """알림 해결 처리"""
        alerts_data = self.redis_client.lrange("alerts", 0, -1)

        for i, alert_json in enumerate(alerts_data):
            alert_dict = json.loads(alert_json)

            if alert_dict['id'] == alert_id:
                alert_dict['resolved'] = True
                alert_dict['resolved_by'] = user_id
                alert_dict['resolved_at'] = datetime.utcnow().isoformat()
                alert_dict['resolution_note'] = resolution_note

                # Redis 업데이트
                self.redis_client.lset("alerts", i, json.dumps(alert_dict))
                logger.info(f"Alert {alert_id} resolved by {user_id}")
                return True

        return False

# 기본 설정 로드
def load_monitoring_config(config_file: str = "monitoring_config.yaml") -> Dict[str, Any]:
    """모니터링 설정 로드"""
    config_path = Path(config_file)

    if not config_path.exists():
        # 기본 설정 생성
        default_config = {
            'thresholds': {
                'ph_value': {'min_value': 6.0, 'max_value': 8.5, 'warning_threshold': 0.8, 'critical_threshold': 0.9},
                'do_value': {'min_value': 4.0, 'max_value': None, 'warning_threshold': 0.7, 'critical_threshold': 0.5},
                'turbidity': {'min_value': None, 'max_value': 1.0, 'warning_threshold': 0.8, 'critical_threshold': 0.9},
                'tds_value': {'min_value': None, 'max_value': 500, 'warning_threshold': 0.8, 'critical_threshold': 0.9}
            },
            'notifications': {
                'email': {
                    'enabled': True,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'use_tls': True,
                    'from_email': 'scada@company.com',
                    'to_emails': ['admin@company.com', 'operator@company.com'],
                    'severity_filter': ['warning', 'critical', 'emergency']
                }
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)

        return default_config

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# 전역 인스턴스
monitor = RealTimeMonitor()
alerting_system = AlertingSystem.get_instance()
performance_monitor = PerformanceMonitor(monitor)
redis_client = redis.Redis(host='localhost', port=6379, db=3, decode_responses=True)
dashboard = AlertDashboard(redis_client)

def initialize_monitoring_system():
    """모니터링 시스템 초기화"""
    try:
        # 설정 로드
        config = load_monitoring_config()

        # 임계값 설정
        for param, threshold_config in config.get('thresholds', {}).items():
            threshold = Threshold(parameter=param, **threshold_config)
            monitor.add_threshold(threshold)

        # 알림 채널 설정
        for channel_name, channel_config in config.get('notifications', {}).items():
            severity_filter = channel_config.pop('severity_filter', ['warning', 'critical', 'emergency'])
            notification_config = NotificationConfig(
                channel=channel_name,
                enabled=channel_config.pop('enabled', True),
                config=channel_config,
                severity_filter=severity_filter
            )
            alerting_system.add_notification_channel(channel_name, notification_config)

        # 성능 모니터링 시작
        performance_monitor.start_monitoring()

        logger.info("Monitoring system initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize monitoring system: {e}")
        raise

if __name__ == "__main__":
    # 테스트 실행
    initialize_monitoring_system()

    # 테스트 데이터
    monitor.update_data("ph_value", 8.6)  # 임계값 위반
    monitor.update_data("turbidity", 0.05)  # 정상값

    print("Monitoring system test completed")