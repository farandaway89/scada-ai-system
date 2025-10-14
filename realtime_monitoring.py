"""
Real-time Monitoring and Alerting System for Industrial SCADA
High-performance monitoring with advanced alerting capabilities
"""

import asyncio
import websockets
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
try:
    from twilio.rest import Client
except ImportError:
    Client = None
import sqlite3
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

class AlertType(Enum):
    """Types of alerts"""
    SYSTEM_FAULT = "system_fault"
    PROCESS_ALARM = "process_alarm"
    SECURITY_BREACH = "security_breach"
    EQUIPMENT_FAILURE = "equipment_failure"
    QUALITY_DEVIATION = "quality_deviation"
    MAINTENANCE_DUE = "maintenance_due"
    PERFORMANCE_DEGRADATION = "performance_degradation"

class MonitoringStatus(Enum):
    """Monitoring system status"""
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class MonitoringPoint:
    """Monitoring point configuration"""
    point_id: str
    name: str
    data_type: str
    source_address: str
    scan_rate_ms: int
    alarm_high: Optional[float] = None
    alarm_low: Optional[float] = None
    warning_high: Optional[float] = None
    warning_low: Optional[float] = None
    deadband: float = 0.1
    enabled: bool = True

@dataclass
class AlertRule:
    """Alert rule definition"""
    rule_id: str
    name: str
    condition: str  # Python expression
    alert_type: AlertType
    priority: AlertPriority
    message_template: str
    cooldown_minutes: int = 5
    enabled: bool = True
    acknowledgement_required: bool = False

@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule_id: str
    timestamp: datetime
    alert_type: AlertType
    priority: AlertPriority
    message: str
    source_point: str
    current_value: Any
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_time: Optional[datetime] = None
    resolved: bool = False
    resolved_time: Optional[datetime] = None

@dataclass
class MonitoringData:
    """Real-time monitoring data"""
    point_id: str
    timestamp: datetime
    value: Any
    quality: str = "GOOD"
    status: str = "ONLINE"

class DataBuffer:
    """High-performance circular buffer for monitoring data"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.buffer = {}
        self.locks = {}

    def add_point(self, point_id: str, data: MonitoringData):
        """Add data point to buffer"""
        if point_id not in self.buffer:
            self.buffer[point_id] = []
            self.locks[point_id] = threading.Lock()

        with self.locks[point_id]:
            self.buffer[point_id].append(data)

            # Maintain buffer size
            if len(self.buffer[point_id]) > self.max_size:
                self.buffer[point_id].pop(0)

    def get_latest(self, point_id: str) -> Optional[MonitoringData]:
        """Get latest data for point"""
        if point_id not in self.buffer or not self.buffer[point_id]:
            return None

        with self.locks[point_id]:
            return self.buffer[point_id][-1]

    def get_history(self, point_id: str, minutes: int = 60) -> List[MonitoringData]:
        """Get historical data for point"""
        if point_id not in self.buffer:
            return []

        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        with self.locks[point_id]:
            return [
                data for data in self.buffer[point_id]
                if data.timestamp >= cutoff_time
            ]

    def get_all_latest(self) -> Dict[str, MonitoringData]:
        """Get latest data for all points"""
        result = {}
        for point_id in self.buffer:
            latest = self.get_latest(point_id)
            if latest:
                result[point_id] = latest
        return result

class AlertManager:
    """Manages alert generation, acknowledgment, and escalation"""

    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.cooldown_tracker: Dict[str, datetime] = {}
        self.alert_queue = queue.Queue()
        self.notification_handlers: List[Callable] = []

    def add_alert_rule(self, rule: AlertRule):
        """Add new alert rule"""
        self.alert_rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def remove_alert_rule(self, rule_id: str):
        """Remove alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")

    def evaluate_alerts(self, monitoring_data: Dict[str, MonitoringData]):
        """Evaluate all alert rules against current data"""
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled:
                continue

            # Check cooldown period
            if rule_id in self.cooldown_tracker:
                cooldown_end = self.cooldown_tracker[rule_id] + timedelta(minutes=rule.cooldown_minutes)
                if datetime.now() < cooldown_end:
                    continue

            try:
                # Create evaluation context
                context = {
                    'data': monitoring_data,
                    'time': datetime.now(),
                    'get_value': lambda point_id: monitoring_data.get(point_id, MonitoringData("", datetime.now(), 0)).value,
                    'get_quality': lambda point_id: monitoring_data.get(point_id, MonitoringData("", datetime.now(), 0)).quality
                }

                # Evaluate rule condition
                if eval(rule.condition, {"__builtins__": {}}, context):
                    self._trigger_alert(rule, monitoring_data)

            except Exception as e:
                logger.error(f"Error evaluating alert rule {rule.name}: {e}")

    def _trigger_alert(self, rule: AlertRule, monitoring_data: Dict[str, MonitoringData]):
        """Trigger an alert"""
        alert_id = f"{rule.rule_id}_{int(time.time())}"

        # Find source point (simplified - gets first point mentioned in condition)
        source_point = "unknown"
        current_value = None

        for point_id in monitoring_data:
            if point_id in rule.condition:
                source_point = point_id
                current_value = monitoring_data[point_id].value
                break

        # Format alert message
        message = rule.message_template.format(
            value=current_value,
            point=source_point,
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            timestamp=datetime.now(),
            alert_type=rule.alert_type,
            priority=rule.priority,
            message=message,
            source_point=source_point,
            current_value=current_value,
            acknowledgement_required=rule.acknowledgement_required
        )

        # Add to active alerts
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # Set cooldown
        self.cooldown_tracker[rule.rule_id] = datetime.now()

        # Queue for notification
        self.alert_queue.put(alert)

        logger.warning(f"Alert triggered: {alert.message}")

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_time = datetime.now()

            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True

        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_time = datetime.now()

            # Remove from active alerts
            del self.active_alerts[alert_id]

            logger.info(f"Alert {alert_id} resolved")
            return True

        return False

    def get_active_alerts(self, priority_filter: Optional[AlertPriority] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by priority"""
        alerts = list(self.active_alerts.values())

        if priority_filter:
            alerts = [a for a in alerts if a.priority == priority_filter]

        return sorted(alerts, key=lambda x: (x.priority.value, x.timestamp), reverse=True)

    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """Add notification handler"""
        self.notification_handlers.append(handler)

class NotificationSystem:
    """Handles alert notifications via multiple channels"""

    def __init__(self):
        self.email_config = {}
        self.sms_config = {}
        self.webhook_urls = []
        self.notification_rules = {}

    def configure_email(self, smtp_server: str, smtp_port: int, username: str, password: str):
        """Configure email notifications"""
        self.email_config = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password
        }

    def configure_sms(self, twilio_account_sid: str, twilio_auth_token: str, from_number: str):
        """Configure SMS notifications"""
        self.sms_config = {
            'account_sid': twilio_account_sid,
            'auth_token': twilio_auth_token,
            'from_number': from_number
        }

    def add_webhook(self, url: str):
        """Add webhook URL for notifications"""
        self.webhook_urls.append(url)

    def send_email_alert(self, alert: Alert, recipients: List[str]):
        """Send email alert"""
        try:
            if not self.email_config:
                logger.error("Email not configured")
                return False

            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"SCADA Alert - {alert.priority.name}: {alert.alert_type.value}"

            body = f"""
            Alert Details:
            - Alert ID: {alert.alert_id}
            - Time: {alert.timestamp}
            - Priority: {alert.priority.name}
            - Type: {alert.alert_type.value}
            - Message: {alert.message}
            - Source: {alert.source_point}
            - Current Value: {alert.current_value}

            Please investigate and acknowledge this alert in the SCADA system.
            """

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)

            logger.info(f"Email alert sent to {recipients}")
            return True

        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False

    def send_sms_alert(self, alert: Alert, phone_numbers: List[str]):
        """Send SMS alert"""
        try:
            if not self.sms_config:
                logger.error("SMS not configured")
                return False

            if Client is None:
                logger.error("Twilio not available for SMS alerts")
                return False
            client = Client(self.sms_config['account_sid'], self.sms_config['auth_token'])

            message_body = f"SCADA ALERT [{alert.priority.name}]: {alert.message} at {alert.timestamp.strftime('%H:%M:%S')}"

            for phone_number in phone_numbers:
                client.messages.create(
                    body=message_body,
                    from_=self.sms_config['from_number'],
                    to=phone_number
                )

            logger.info(f"SMS alerts sent to {phone_numbers}")
            return True

        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")
            return False

    def send_webhook_alert(self, alert: Alert):
        """Send webhook notification"""
        try:
            payload = {
                'alert_id': alert.alert_id,
                'timestamp': alert.timestamp.isoformat(),
                'priority': alert.priority.name,
                'type': alert.alert_type.value,
                'message': alert.message,
                'source_point': alert.source_point,
                'current_value': alert.current_value
            }

            for url in self.webhook_urls:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()

            logger.info(f"Webhook alerts sent to {len(self.webhook_urls)} endpoints")
            return True

        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
            return False

class RealTimeMonitoringSystem:
    """Main real-time monitoring system"""

    def __init__(self):
        self.monitoring_points: Dict[str, MonitoringPoint] = {}
        self.data_buffer = DataBuffer()
        self.alert_manager = AlertManager()
        self.notification_system = NotificationSystem()
        self.status = MonitoringStatus.OFFLINE
        self.scan_threads = {}
        self.websocket_server = None
        self.connected_clients = set()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.db_connection = None
        self.performance_stats = {
            'points_scanned': 0,
            'alerts_generated': 0,
            'notifications_sent': 0,
            'scan_rate_achieved': 0,
            'last_scan_time': None
        }

    def initialize_database(self, db_path: str = "monitoring.db"):
        """Initialize SQLite database for historical data"""
        try:
            self.db_connection = sqlite3.connect(db_path, check_same_thread=False)
            cursor = self.db_connection.cursor()

            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    point_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    value REAL,
                    quality TEXT DEFAULT 'GOOD',
                    status TEXT DEFAULT 'ONLINE'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    alert_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    source_point TEXT NOT NULL,
                    current_value REAL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_by TEXT,
                    acknowledged_time DATETIME,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_time DATETIME
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monitoring_timestamp ON monitoring_data(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_monitoring_point ON monitoring_data(point_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)
            """)

            self.db_connection.commit()
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def add_monitoring_point(self, point: MonitoringPoint):
        """Add monitoring point"""
        self.monitoring_points[point.point_id] = point
        logger.info(f"Added monitoring point: {point.name}")

    def remove_monitoring_point(self, point_id: str):
        """Remove monitoring point"""
        if point_id in self.monitoring_points:
            del self.monitoring_points[point_id]

            # Stop scanning thread if exists
            if point_id in self.scan_threads:
                self.scan_threads[point_id]['stop'] = True

            logger.info(f"Removed monitoring point: {point_id}")

    def start_monitoring(self):
        """Start the monitoring system"""
        try:
            self.status = MonitoringStatus.ACTIVE

            # Start scanning threads for each monitoring point
            for point_id, point in self.monitoring_points.items():
                if point.enabled:
                    self._start_point_scanner(point)

            # Start alert evaluation thread
            self.executor.submit(self._alert_evaluation_loop)

            # Start notification processing thread
            self.executor.submit(self._notification_processing_loop)

            # Start WebSocket server for real-time updates
            self.executor.submit(self._start_websocket_server)

            logger.info("Monitoring system started successfully")

        except Exception as e:
            logger.error(f"Error starting monitoring system: {e}")
            self.status = MonitoringStatus.ERROR

    def stop_monitoring(self):
        """Stop the monitoring system"""
        try:
            self.status = MonitoringStatus.OFFLINE

            # Stop all scanning threads
            for thread_info in self.scan_threads.values():
                thread_info['stop'] = True

            # Close database connection
            if self.db_connection:
                self.db_connection.close()

            # Shutdown executor
            self.executor.shutdown(wait=True)

            logger.info("Monitoring system stopped")

        except Exception as e:
            logger.error(f"Error stopping monitoring system: {e}")

    def _start_point_scanner(self, point: MonitoringPoint):
        """Start scanning thread for a monitoring point"""
        def scan_loop():
            thread_info = {'stop': False}
            self.scan_threads[point.point_id] = thread_info

            while not thread_info['stop'] and self.status == MonitoringStatus.ACTIVE:
                try:
                    # Simulate data reading (replace with actual protocol communication)
                    value = self._read_point_value(point)

                    # Create monitoring data
                    data = MonitoringData(
                        point_id=point.point_id,
                        timestamp=datetime.now(),
                        value=value,
                        quality="GOOD",
                        status="ONLINE"
                    )

                    # Add to buffer
                    self.data_buffer.add_point(point.point_id, data)

                    # Store in database
                    if self.db_connection:
                        self._store_data_point(data)

                    # Update performance stats
                    self.performance_stats['points_scanned'] += 1
                    self.performance_stats['last_scan_time'] = datetime.now()

                    # Sleep for scan rate
                    time.sleep(point.scan_rate_ms / 1000.0)

                except Exception as e:
                    logger.error(f"Error scanning point {point.point_id}: {e}")
                    time.sleep(1)  # Wait before retry

        # Start thread
        self.executor.submit(scan_loop)

    def _read_point_value(self, point: MonitoringPoint) -> float:
        """Read point value (simulation - replace with actual protocol reading)"""
        # Simulate different types of process variables
        import random

        if 'temperature' in point.name.lower():
            return random.uniform(20, 100)
        elif 'pressure' in point.name.lower():
            return random.uniform(0, 150)
        elif 'flow' in point.name.lower():
            return random.uniform(0, 1000)
        elif 'level' in point.name.lower():
            return random.uniform(0, 100)
        else:
            return random.uniform(0, 100)

    def _store_data_point(self, data: MonitoringData):
        """Store data point in database"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                INSERT INTO monitoring_data (point_id, timestamp, value, quality, status)
                VALUES (?, ?, ?, ?, ?)
            """, (data.point_id, data.timestamp, data.value, data.quality, data.status))

            self.db_connection.commit()

        except Exception as e:
            logger.error(f"Error storing data point: {e}")

    def _alert_evaluation_loop(self):
        """Alert evaluation loop"""
        while self.status == MonitoringStatus.ACTIVE:
            try:
                # Get latest data for all points
                current_data = self.data_buffer.get_all_latest()

                # Evaluate alert rules
                self.alert_manager.evaluate_alerts(current_data)

                time.sleep(1)  # Evaluate every second

            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                time.sleep(5)

    def _notification_processing_loop(self):
        """Process alert notifications"""
        while self.status == MonitoringStatus.ACTIVE:
            try:
                # Get alert from queue
                alert = self.alert_manager.alert_queue.get(timeout=1)

                # Send notifications based on priority
                self._process_alert_notification(alert)

                # Update performance stats
                self.performance_stats['alerts_generated'] += 1

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing alert notification: {e}")

    def _process_alert_notification(self, alert: Alert):
        """Process alert notification based on priority and configuration"""
        try:
            # Determine notification channels based on priority
            if alert.priority in [AlertPriority.EMERGENCY, AlertPriority.CRITICAL]:
                # High priority - all channels
                self.notification_system.send_webhook_alert(alert)
                # self.notification_system.send_email_alert(alert, ['admin@company.com'])
                # self.notification_system.send_sms_alert(alert, ['+1234567890'])

            elif alert.priority == AlertPriority.HIGH:
                # Medium priority - email and webhook
                self.notification_system.send_webhook_alert(alert)
                # self.notification_system.send_email_alert(alert, ['operator@company.com'])

            else:
                # Low priority - webhook only
                self.notification_system.send_webhook_alert(alert)

            # Broadcast to WebSocket clients
            self._broadcast_alert(alert)

            self.performance_stats['notifications_sent'] += 1

        except Exception as e:
            logger.error(f"Error processing alert notification: {e}")

    async def _websocket_handler(self, websocket, path):
        """Handle WebSocket connections"""
        self.connected_clients.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.connected_clients)}")

        try:
            async for message in websocket:
                # Handle incoming messages from clients
                data = json.loads(message)
                await self._handle_websocket_message(websocket, data)

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.connected_clients.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.connected_clients)}")

    async def _handle_websocket_message(self, websocket, data):
        """Handle incoming WebSocket message"""
        try:
            if data.get('type') == 'acknowledge_alert':
                alert_id = data.get('alert_id')
                user = data.get('user', 'unknown')

                success = self.alert_manager.acknowledge_alert(alert_id, user)
                await websocket.send(json.dumps({
                    'type': 'acknowledge_response',
                    'alert_id': alert_id,
                    'success': success
                }))

            elif data.get('type') == 'get_current_data':
                current_data = self.data_buffer.get_all_latest()
                response = {
                    'type': 'current_data',
                    'data': {
                        point_id: {
                            'value': point_data.value,
                            'timestamp': point_data.timestamp.isoformat(),
                            'quality': point_data.quality
                        }
                        for point_id, point_data in current_data.items()
                    }
                }
                await websocket.send(json.dumps(response))

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    def _start_websocket_server(self):
        """Start WebSocket server"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            start_server = websockets.serve(
                self._websocket_handler,
                "localhost",
                8765
            )

            loop.run_until_complete(start_server)
            loop.run_forever()

        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")

    def _broadcast_alert(self, alert: Alert):
        """Broadcast alert to all connected WebSocket clients"""
        if not self.connected_clients:
            return

        message = json.dumps({
            'type': 'alert',
            'data': asdict(alert),
            'timestamp': alert.timestamp.isoformat()
        }, default=str)

        # Send to all connected clients
        disconnected_clients = set()
        for client in self.connected_clients:
            try:
                asyncio.create_task(client.send(message))
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(client)

        # Remove disconnected clients
        self.connected_clients -= disconnected_clients

    def get_system_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            'status': self.status.value,
            'monitoring_points': len(self.monitoring_points),
            'active_alerts': len(self.alert_manager.active_alerts),
            'connected_clients': len(self.connected_clients),
            'performance_stats': self.performance_stats,
            'uptime': self.performance_stats.get('last_scan_time', datetime.now()).isoformat()
        }

# Example usage and configuration
if __name__ == "__main__":
    # Initialize monitoring system
    monitoring_system = RealTimeMonitoringSystem()
    monitoring_system.initialize_database()

    # Configure monitoring points
    points = [
        MonitoringPoint(
            point_id="T001",
            name="Reactor Temperature",
            data_type="float",
            source_address="192.168.1.100:502",
            scan_rate_ms=1000,
            alarm_high=95.0,
            warning_high=85.0
        ),
        MonitoringPoint(
            point_id="P001",
            name="System Pressure",
            data_type="float",
            source_address="192.168.1.100:502",
            scan_rate_ms=500,
            alarm_high=120.0,
            alarm_low=30.0
        ),
        MonitoringPoint(
            point_id="F001",
            name="Flow Rate",
            data_type="float",
            source_address="192.168.1.101:502",
            scan_rate_ms=2000,
            alarm_low=10.0
        )
    ]

    for point in points:
        monitoring_system.add_monitoring_point(point)

    # Configure alert rules
    alert_rules = [
        AlertRule(
            rule_id="TEMP_HIGH",
            name="High Temperature Alert",
            condition="get_value('T001') > 95",
            alert_type=AlertType.PROCESS_ALARM,
            priority=AlertPriority.CRITICAL,
            message_template="Temperature alarm: {value}°C at point {point}",
            acknowledgement_required=True
        ),
        AlertRule(
            rule_id="PRESSURE_LOW",
            name="Low Pressure Alert",
            condition="get_value('P001') < 30",
            alert_type=AlertType.SYSTEM_FAULT,
            priority=AlertPriority.HIGH,
            message_template="Low pressure alarm: {value} bar at point {point}"
        ),
        AlertRule(
            rule_id="FLOW_STOPPED",
            name="Flow Stopped Alert",
            condition="get_value('F001') < 5",
            alert_type=AlertType.EQUIPMENT_FAILURE,
            priority=AlertPriority.EMERGENCY,
            message_template="Flow stopped: {value} L/min at point {point}",
            acknowledgement_required=True
        )
    ]

    for rule in alert_rules:
        monitoring_system.alert_manager.add_alert_rule(rule)

    # Configure notifications
    monitoring_system.notification_system.add_webhook("http://localhost:9000/alerts")

    try:
        # Start monitoring
        monitoring_system.start_monitoring()
        logger.info("Real-time monitoring system is running...")

        # Keep running (in production, this would be a proper service)
        while True:
            status = monitoring_system.get_system_status()
            logger.info(f"System status: {json.dumps(status, indent=2)}")
            time.sleep(30)

    except KeyboardInterrupt:
        logger.info("Shutting down monitoring system...")
        monitoring_system.stop_monitoring()
    except Exception as e:
        logger.error(f"Monitoring system error: {e}")
        monitoring_system.stop_monitoring()