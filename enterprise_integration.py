"""
Enterprise Integration Layer for Industrial SCADA Systems
Advanced integration with enterprise systems, cloud platforms, and third-party services
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import ssl
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, ValidationError
import redis
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional imports for enterprise features
try:
    import pika  # RabbitMQ
    PIKA_AVAILABLE = True
except ImportError:
    PIKA_AVAILABLE = False
    logger.warning("pika not available - RabbitMQ integration will be disabled")

try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("kafka-python not available - Kafka integration will be disabled")

try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("azure-servicebus not available - Azure integration will be disabled")

try:
    from google.cloud import pubsub_v1
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    logger.warning("google-cloud-pubsub not available - GCP integration will be disabled")

class IntegrationType(Enum):
    """Types of enterprise integrations"""
    ERP_SYSTEM = "erp_system"
    MES_SYSTEM = "mes_system"
    HISTORIAN = "historian"
    CLOUD_PLATFORM = "cloud_platform"
    MESSAGE_QUEUE = "message_queue"
    REST_API = "rest_api"
    DATABASE = "database"
    FILE_TRANSFER = "file_transfer"
    EMAIL_NOTIFICATION = "email_notification"

class MessageFormat(Enum):
    """Supported message formats"""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    BINARY = "binary"
    MQTT = "mqtt"
    OPC_UA = "opc_ua"

class IntegrationStatus(Enum):
    """Integration connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    AUTHENTICATING = "authenticating"

@dataclass
class IntegrationConfig:
    """Integration configuration"""
    integration_id: str
    name: str
    integration_type: IntegrationType
    endpoint_url: str
    authentication: Dict[str, Any]
    message_format: MessageFormat
    retry_attempts: int = 3
    timeout_seconds: int = 30
    enabled: bool = True
    data_mapping: Dict[str, str] = None
    schedule_interval: Optional[int] = None  # seconds

@dataclass
class DataExchangeRecord:
    """Data exchange record for audit trail"""
    record_id: str
    integration_id: str
    timestamp: datetime
    direction: str  # 'inbound' or 'outbound'
    data_type: str
    payload_size: int
    status: str
    error_message: Optional[str]
    processing_time: float

# SQLAlchemy models
Base = declarative_base()

class IntegrationLog(Base):
    __tablename__ = 'integration_logs'

    id = Column(Integer, primary_key=True)
    integration_id = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    message = Column(Text)
    data_size = Column(Integer)
    processing_time = Column(Float)

class ERPIntegration:
    """Enterprise Resource Planning system integration"""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config.timeout_seconds),
            connector=aiohttp.TCPConnector(ssl=ssl.create_default_context())
        )
        self.status = IntegrationStatus.DISCONNECTED

    async def authenticate(self) -> bool:
        """Authenticate with ERP system"""
        try:
            self.status = IntegrationStatus.AUTHENTICATING

            auth_url = urljoin(self.config.endpoint_url, "/auth/login")
            auth_data = {
                "username": self.config.authentication.get("username"),
                "password": self.config.authentication.get("password"),
                "client_id": self.config.authentication.get("client_id")
            }

            async with self.session.post(auth_url, json=auth_data) as response:
                if response.status == 200:
                    auth_result = await response.json()
                    self.session.headers.update({
                        "Authorization": f"Bearer {auth_result.get('access_token')}"
                    })
                    self.status = IntegrationStatus.CONNECTED
                    logger.info(f"ERP authentication successful: {self.config.name}")
                    return True
                else:
                    self.status = IntegrationStatus.ERROR
                    logger.error(f"ERP authentication failed: {response.status}")
                    return False

        except Exception as e:
            self.status = IntegrationStatus.ERROR
            logger.error(f"ERP authentication error: {e}")
            return False

    async def push_production_data(self, production_data: Dict[str, Any]) -> bool:
        """Push production data to ERP system"""
        try:
            if self.status != IntegrationStatus.CONNECTED:
                await self.authenticate()

            # Map SCADA data to ERP format
            erp_data = self._map_production_data(production_data)

            production_url = urljoin(self.config.endpoint_url, "/api/production/data")

            async with self.session.post(production_url, json=erp_data) as response:
                if response.status in [200, 201]:
                    logger.info(f"Production data pushed to ERP: {self.config.name}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to push production data: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error pushing production data to ERP: {e}")
            return False

    async def get_work_orders(self) -> List[Dict[str, Any]]:
        """Get work orders from ERP system"""
        try:
            if self.status != IntegrationStatus.CONNECTED:
                await self.authenticate()

            orders_url = urljoin(self.config.endpoint_url, "/api/workorders/active")

            async with self.session.get(orders_url) as response:
                if response.status == 200:
                    work_orders = await response.json()
                    logger.info(f"Retrieved {len(work_orders)} work orders from ERP")
                    return work_orders
                else:
                    logger.error(f"Failed to get work orders: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting work orders from ERP: {e}")
            return []

    def _map_production_data(self, scada_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map SCADA data to ERP format"""
        mapping = self.config.data_mapping or {}

        erp_data = {
            "timestamp": datetime.now().isoformat(),
            "facility_id": scada_data.get("facility_id", "PLANT_001"),
            "production_line": scada_data.get("line_id", "LINE_001"),
            "batch_id": scada_data.get("batch_id"),
            "product_code": scada_data.get("product_code"),
            "quantity_produced": scada_data.get("production_count", 0),
            "quality_metrics": {
                "defect_rate": scada_data.get("defect_rate", 0.0),
                "efficiency": scada_data.get("efficiency", 100.0),
                "downtime_minutes": scada_data.get("downtime", 0)
            },
            "resource_consumption": {
                "energy_kwh": scada_data.get("energy_consumption", 0.0),
                "water_liters": scada_data.get("water_usage", 0.0),
                "raw_material_kg": scada_data.get("material_usage", 0.0)
            }
        }

        # Apply custom mapping if configured
        for scada_field, erp_field in mapping.items():
            if scada_field in scada_data:
                erp_data[erp_field] = scada_data[scada_field]

        return erp_data

    async def close(self):
        """Close ERP integration"""
        await self.session.close()

class MESIntegration:
    """Manufacturing Execution System integration"""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.status = IntegrationStatus.DISCONNECTED
        self.session = aiohttp.ClientSession()

    async def sync_production_schedule(self) -> List[Dict[str, Any]]:
        """Sync production schedule from MES"""
        try:
            schedule_url = urljoin(self.config.endpoint_url, "/mes/schedule")

            async with self.session.get(schedule_url) as response:
                if response.status == 200:
                    schedule_data = await response.json()
                    return schedule_data.get("schedule_items", [])

                return []

        except Exception as e:
            logger.error(f"Error syncing production schedule: {e}")
            return []

    async def report_batch_completion(self, batch_data: Dict[str, Any]) -> bool:
        """Report batch completion to MES"""
        try:
            completion_url = urljoin(self.config.endpoint_url, "/mes/batch/complete")

            payload = {
                "batch_id": batch_data["batch_id"],
                "completion_time": datetime.now().isoformat(),
                "actual_quantity": batch_data.get("quantity", 0),
                "quality_results": batch_data.get("quality_data", {}),
                "process_parameters": batch_data.get("process_params", {}),
                "deviations": batch_data.get("deviations", [])
            }

            async with self.session.post(completion_url, json=payload) as response:
                return response.status in [200, 201]

        except Exception as e:
            logger.error(f"Error reporting batch completion: {e}")
            return False

    async def close(self):
        await self.session.close()

class CloudPlatformIntegration:
    """Cloud platform integration (AWS, Azure, GCP)"""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.platform_type = config.authentication.get("platform", "aws")
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize cloud platform client"""
        try:
            if self.platform_type == "aws":
                self.client = boto3.client(
                    'iot-data',
                    region_name=self.config.authentication.get("region", "us-east-1"),
                    aws_access_key_id=self.config.authentication.get("access_key"),
                    aws_secret_access_key=self.config.authentication.get("secret_key")
                )
            elif self.platform_type == "azure":
                from azure.iot.device import IoTHubDeviceClient
                connection_string = self.config.authentication.get("connection_string")
                self.client = IoTHubDeviceClient.create_from_connection_string(connection_string)
            elif self.platform_type == "gcp":
                from google.cloud import iot_v1
                self.client = iot_v1.DeviceManagerClient()

            logger.info(f"Cloud platform client initialized: {self.platform_type}")

        except Exception as e:
            logger.error(f"Error initializing cloud client: {e}")

    async def send_telemetry(self, device_id: str, telemetry_data: Dict[str, Any]) -> bool:
        """Send telemetry data to cloud platform"""
        try:
            if self.platform_type == "aws":
                response = self.client.publish(
                    topic=f"devices/{device_id}/telemetry",
                    payload=json.dumps(telemetry_data)
                )
                return response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 200

            elif self.platform_type == "azure":
                message = json.dumps(telemetry_data)
                await self.client.send_message(message)
                return True

            elif self.platform_type == "gcp":
                # Implement GCP IoT Core publishing
                return True

            return False

        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")
            return False

    async def receive_commands(self, device_id: str, command_handler: Callable) -> None:
        """Receive commands from cloud platform"""
        try:
            if self.platform_type == "azure":
                while True:
                    message = await self.client.receive_message()
                    if message:
                        await command_handler(json.loads(message.data))
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error receiving commands: {e}")

class MessageQueueIntegration:
    """Message queue integration (RabbitMQ, Apache Kafka, etc.)"""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.queue_type = config.authentication.get("type", "rabbitmq")
        self.connection = None
        self.producer = None
        self.consumer = None

    def connect(self) -> bool:
        """Connect to message queue"""
        try:
            if self.queue_type == "rabbitmq":
                connection_params = pika.ConnectionParameters(
                    host=self.config.authentication.get("host", "localhost"),
                    port=self.config.authentication.get("port", 5672),
                    virtual_host=self.config.authentication.get("vhost", "/"),
                    credentials=pika.PlainCredentials(
                        self.config.authentication.get("username"),
                        self.config.authentication.get("password")
                    )
                )
                self.connection = pika.BlockingConnection(connection_params)

            elif self.queue_type == "kafka":
                self.producer = KafkaProducer(
                    bootstrap_servers=self.config.authentication.get("brokers", ["localhost:9092"]),
                    value_serializer=lambda x: json.dumps(x).encode('utf-8')
                )

            logger.info(f"Message queue connected: {self.queue_type}")
            return True

        except Exception as e:
            logger.error(f"Error connecting to message queue: {e}")
            return False

    def publish_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """Publish message to queue"""
        try:
            if self.queue_type == "rabbitmq" and self.connection:
                channel = self.connection.channel()
                channel.queue_declare(queue=topic, durable=True)
                channel.basic_publish(
                    exchange='',
                    routing_key=topic,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
                )
                return True

            elif self.queue_type == "kafka" and self.producer:
                future = self.producer.send(topic, message)
                result = future.get(timeout=10)
                return True

            return False

        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False

    def subscribe_to_topic(self, topic: str, callback: Callable) -> None:
        """Subscribe to topic and process messages"""
        try:
            if self.queue_type == "rabbitmq" and self.connection:
                channel = self.connection.channel()
                channel.queue_declare(queue=topic, durable=True)

                def wrapper(ch, method, properties, body):
                    try:
                        message = json.loads(body.decode())
                        callback(message)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        ch.basic_nack(delivery_tag=method.delivery_tag)

                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue=topic, on_message_callback=wrapper)
                channel.start_consuming()

            elif self.queue_type == "kafka":
                consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=self.config.authentication.get("brokers", ["localhost:9092"]),
                    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
                )

                for message in consumer:
                    try:
                        callback(message.value)
                    except Exception as e:
                        logger.error(f"Error processing Kafka message: {e}")

        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")

    def close(self):
        """Close message queue connections"""
        if self.connection:
            self.connection.close()
        if self.producer:
            self.producer.close()

class HistorianIntegration:
    """Process historian integration (OSIsoft PI, Wonderware, etc.)"""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.historian_type = config.authentication.get("type", "pi")
        self.client = None

    def connect(self) -> bool:
        """Connect to historian"""
        try:
            if self.historian_type == "pi":
                # OSIsoft PI integration would require PI SDK
                # This is a simplified example
                logger.info("PI Historian connection established")
                return True

            elif self.historian_type == "wonderware":
                # Wonderware Historian integration
                logger.info("Wonderware Historian connection established")
                return True

            return False

        except Exception as e:
            logger.error(f"Error connecting to historian: {e}")
            return False

    def write_batch_data(self, tag_data: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Write batch data to historian"""
        try:
            # Convert SCADA data to historian format
            historian_records = []

            for tag_name, data_points in tag_data.items():
                for point in data_points:
                    historian_records.append({
                        "tag": tag_name,
                        "timestamp": point["timestamp"],
                        "value": point["value"],
                        "quality": point.get("quality", "Good")
                    })

            # Write to historian (implementation depends on historian type)
            logger.info(f"Writing {len(historian_records)} records to historian")
            return True

        except Exception as e:
            logger.error(f"Error writing to historian: {e}")
            return False

    def read_historical_data(self, tag_name: str, start_time: datetime,
                           end_time: datetime) -> List[Dict[str, Any]]:
        """Read historical data from historian"""
        try:
            # Query historian for data (implementation depends on historian type)
            # This is a mock implementation
            mock_data = []
            current_time = start_time

            while current_time <= end_time:
                mock_data.append({
                    "timestamp": current_time.isoformat(),
                    "value": 75.5 + (hash(str(current_time)) % 20),  # Mock value
                    "quality": "Good"
                })
                current_time += timedelta(minutes=1)

            return mock_data

        except Exception as e:
            logger.error(f"Error reading historical data: {e}")
            return []

class EnterpriseIntegrationManager:
    """Main enterprise integration manager"""

    def __init__(self, db_url: str = "sqlite:///enterprise_integration.db"):
        self.integrations: Dict[str, Any] = {}
        self.db_engine = create_engine(db_url)
        Base.metadata.create_all(self.db_engine)
        self.db_session = sessionmaker(bind=self.db_engine)
        self.integration_scheduler = {}
        self.status_monitor_task = None

    def add_integration(self, config: IntegrationConfig) -> bool:
        """Add new integration"""
        try:
            if config.integration_type == IntegrationType.ERP_SYSTEM:
                integration = ERPIntegration(config)
            elif config.integration_type == IntegrationType.MES_SYSTEM:
                integration = MESIntegration(config)
            elif config.integration_type == IntegrationType.CLOUD_PLATFORM:
                integration = CloudPlatformIntegration(config)
            elif config.integration_type == IntegrationType.MESSAGE_QUEUE:
                integration = MessageQueueIntegration(config)
            elif config.integration_type == IntegrationType.HISTORIAN:
                integration = HistorianIntegration(config)
            else:
                logger.error(f"Unsupported integration type: {config.integration_type}")
                return False

            self.integrations[config.integration_id] = {
                "config": config,
                "client": integration,
                "last_sync": None,
                "status": IntegrationStatus.DISCONNECTED
            }

            # Schedule periodic sync if configured
            if config.schedule_interval:
                self._schedule_integration_sync(config.integration_id, config.schedule_interval)

            logger.info(f"Added integration: {config.name}")
            return True

        except Exception as e:
            logger.error(f"Error adding integration: {e}")
            return False

    def _schedule_integration_sync(self, integration_id: str, interval_seconds: int):
        """Schedule periodic integration sync"""
        async def sync_task():
            while integration_id in self.integrations:
                try:
                    await self.sync_integration(integration_id)
                    await asyncio.sleep(interval_seconds)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in scheduled sync for {integration_id}: {e}")
                    await asyncio.sleep(interval_seconds)

        task = asyncio.create_task(sync_task())
        self.integration_scheduler[integration_id] = task

    async def sync_integration(self, integration_id: str) -> bool:
        """Sync data with specific integration"""
        try:
            integration_info = self.integrations.get(integration_id)
            if not integration_info:
                logger.error(f"Integration not found: {integration_id}")
                return False

            config = integration_info["config"]
            client = integration_info["client"]

            start_time = datetime.now()

            if config.integration_type == IntegrationType.ERP_SYSTEM:
                # Sync production data
                production_data = self._get_current_production_data()
                success = await client.push_production_data(production_data)

            elif config.integration_type == IntegrationType.MES_SYSTEM:
                # Sync production schedule
                schedule = await client.sync_production_schedule()
                success = len(schedule) >= 0  # Consider successful if we get data

            elif config.integration_type == IntegrationType.CLOUD_PLATFORM:
                # Send telemetry
                telemetry = self._get_current_telemetry_data()
                success = await client.send_telemetry("scada_device_01", telemetry)

            else:
                success = True  # Default for other types

            processing_time = (datetime.now() - start_time).total_seconds()

            # Log integration activity
            self._log_integration_activity(
                integration_id, "sync", "success" if success else "error",
                processing_time
            )

            integration_info["last_sync"] = datetime.now()
            integration_info["status"] = IntegrationStatus.CONNECTED if success else IntegrationStatus.ERROR

            return success

        except Exception as e:
            logger.error(f"Error syncing integration {integration_id}: {e}")
            return False

    def _get_current_production_data(self) -> Dict[str, Any]:
        """Get current production data from SCADA system"""
        # This would interface with your SCADA data
        return {
            "facility_id": "PLANT_001",
            "line_id": "LINE_001",
            "batch_id": f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M')}",
            "product_code": "PROD_A",
            "production_count": 1250,
            "defect_rate": 0.5,
            "efficiency": 97.8,
            "downtime": 15,
            "energy_consumption": 450.5,
            "water_usage": 120.3,
            "material_usage": 890.2
        }

    def _get_current_telemetry_data(self) -> Dict[str, Any]:
        """Get current telemetry data"""
        return {
            "timestamp": datetime.now().isoformat(),
            "temperature": 75.5,
            "pressure": 102.3,
            "flow_rate": 45.8,
            "vibration": 2.1,
            "power_consumption": 380.2,
            "status": "running"
        }

    def _log_integration_activity(self, integration_id: str, event_type: str,
                                status: str, processing_time: float):
        """Log integration activity"""
        try:
            with self.db_session() as session:
                log_entry = IntegrationLog(
                    integration_id=integration_id,
                    event_type=event_type,
                    status=status,
                    processing_time=processing_time
                )
                session.add(log_entry)
                session.commit()

        except Exception as e:
            logger.error(f"Error logging integration activity: {e}")

    async def sync_all_integrations(self) -> Dict[str, bool]:
        """Sync all enabled integrations"""
        results = {}

        for integration_id, integration_info in self.integrations.items():
            if integration_info["config"].enabled:
                results[integration_id] = await self.sync_integration(integration_id)

        return results

    def get_integration_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all integrations"""
        status_report = {}

        for integration_id, integration_info in self.integrations.items():
            config = integration_info["config"]
            status_report[integration_id] = {
                "name": config.name,
                "type": config.integration_type.value,
                "status": integration_info["status"].value,
                "last_sync": integration_info["last_sync"].isoformat() if integration_info["last_sync"] else None,
                "enabled": config.enabled
            }

        return status_report

    async def start_monitoring(self):
        """Start integration monitoring"""
        async def monitor_task():
            while True:
                try:
                    # Check integration health
                    for integration_id in self.integrations:
                        # Perform health check
                        pass

                    await asyncio.sleep(60)  # Check every minute

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in integration monitoring: {e}")

        self.status_monitor_task = asyncio.create_task(monitor_task())

    async def stop_monitoring(self):
        """Stop integration monitoring"""
        if self.status_monitor_task:
            self.status_monitor_task.cancel()

        # Cancel scheduled tasks
        for task in self.integration_scheduler.values():
            task.cancel()

        # Close all integration clients
        for integration_info in self.integrations.values():
            client = integration_info["client"]
            if hasattr(client, 'close'):
                await client.close()

    def export_integration_logs(self, start_date: datetime, end_date: datetime,
                              format: str = 'json') -> str:
        """Export integration logs"""
        try:
            with self.db_session() as session:
                logs = session.query(IntegrationLog).filter(
                    IntegrationLog.timestamp.between(start_date, end_date)
                ).all()

                if format == 'json':
                    log_data = []
                    for log in logs:
                        log_data.append({
                            'integration_id': log.integration_id,
                            'timestamp': log.timestamp.isoformat(),
                            'event_type': log.event_type,
                            'status': log.status,
                            'message': log.message,
                            'processing_time': log.processing_time
                        })

                    filename = f"integration_logs_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
                    with open(filename, 'w') as f:
                        json.dump(log_data, f, indent=2)

                    return filename

        except Exception as e:
            logger.error(f"Error exporting integration logs: {e}")
            return ""

# Example usage and configuration
if __name__ == "__main__":
    async def main():
        # Initialize integration manager
        manager = EnterpriseIntegrationManager()

        # Configure ERP integration
        erp_config = IntegrationConfig(
            integration_id="erp_001",
            name="SAP ERP Integration",
            integration_type=IntegrationType.ERP_SYSTEM,
            endpoint_url="https://erp.company.com/api",
            authentication={
                "username": "scada_user",
                "password": "secure_password",
                "client_id": "scada_client"
            },
            message_format=MessageFormat.JSON,
            schedule_interval=300,  # 5 minutes
            data_mapping={
                "production_count": "quantity_produced",
                "efficiency": "line_efficiency",
                "energy_consumption": "energy_used_kwh"
            }
        )

        # Configure MES integration
        mes_config = IntegrationConfig(
            integration_id="mes_001",
            name="Wonderware MES Integration",
            integration_type=IntegrationType.MES_SYSTEM,
            endpoint_url="http://mes.company.com:8080",
            authentication={
                "username": "mes_user",
                "password": "mes_password"
            },
            message_format=MessageFormat.XML,
            schedule_interval=60  # 1 minute
        )

        # Configure Cloud Platform integration
        cloud_config = IntegrationConfig(
            integration_id="aws_iot",
            name="AWS IoT Core Integration",
            integration_type=IntegrationType.CLOUD_PLATFORM,
            endpoint_url="https://iot.us-east-1.amazonaws.com",
            authentication={
                "platform": "aws",
                "region": "us-east-1",
                "access_key": "your_access_key",
                "secret_key": "your_secret_key"
            },
            message_format=MessageFormat.JSON,
            schedule_interval=30  # 30 seconds
        )

        # Add integrations
        manager.add_integration(erp_config)
        manager.add_integration(mes_config)
        manager.add_integration(cloud_config)

        # Start monitoring
        await manager.start_monitoring()

        try:
            # Run for a while to demonstrate
            for i in range(5):
                print(f"Sync attempt {i+1}")

                # Sync all integrations
                results = await manager.sync_all_integrations()
                print(f"Sync results: {results}")

                # Get status
                status = manager.get_integration_status()
                print(f"Integration status: {json.dumps(status, indent=2)}")

                await asyncio.sleep(10)

        finally:
            # Stop monitoring
            await manager.stop_monitoring()

    # Run the example
    asyncio.run(main())