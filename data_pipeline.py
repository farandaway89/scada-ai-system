"""
Integrated Data Pipeline for SCADA AI System
Connects all modules through a unified data flow architecture
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
from collections import defaultdict, deque
import pandas as pd
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class DataType(Enum):
    """Types of data flowing through the pipeline"""
    RAW_SENSOR_DATA = "raw_sensor_data"
    PROCESSED_DATA = "processed_data"
    ALARM_DATA = "alarm_data"
    ANALYTICS_RESULT = "analytics_result"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_DATA = "compliance_data"
    INTEGRATION_DATA = "integration_data"

class PipelineStage(Enum):
    """Pipeline processing stages"""
    INGESTION = "ingestion"
    VALIDATION = "validation"
    PROCESSING = "processing"
    ANALYTICS = "analytics"
    STORAGE = "storage"
    DISTRIBUTION = "distribution"

@dataclass
class DataPacket:
    """Standard data packet for pipeline"""
    packet_id: str
    timestamp: datetime
    data_type: DataType
    source: str
    destination: List[str]
    payload: Dict[str, Any]
    metadata: Dict[str, Any]
    quality: str = "GOOD"
    priority: int = 1  # 1=low, 5=critical

@dataclass
class PipelineMetrics:
    """Pipeline performance metrics"""
    packets_processed: int = 0
    packets_dropped: int = 0
    avg_processing_time: float = 0.0
    queue_depth: int = 0
    throughput_per_second: float = 0.0
    error_rate: float = 0.0
    last_updated: datetime = None

class DataTransformer:
    """Transforms data between different module formats"""

    @staticmethod
    def protocol_to_monitoring(protocol_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform protocol data to monitoring format"""
        try:
            return {
                "point_id": protocol_data.get("device_id", "unknown"),
                "timestamp": datetime.now(),
                "value": protocol_data.get("value", 0),
                "quality": protocol_data.get("quality", "GOOD"),
                "status": protocol_data.get("status", "ONLINE"),
                "unit": protocol_data.get("unit", ""),
                "description": protocol_data.get("description", "")
            }
        except Exception as e:
            logger.error(f"Error transforming protocol data: {e}")
            return {}

    @staticmethod
    def monitoring_to_analytics(monitoring_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform monitoring data to analytics format"""
        try:
            return {
                "feature_id": monitoring_data.get("point_id"),
                "timestamp": monitoring_data.get("timestamp"),
                "value": monitoring_data.get("value"),
                "quality_score": 1.0 if monitoring_data.get("quality") == "GOOD" else 0.5,
                "metadata": {
                    "unit": monitoring_data.get("unit", ""),
                    "source": "monitoring_system"
                }
            }
        except Exception as e:
            logger.error(f"Error transforming monitoring data: {e}")
            return {}

    @staticmethod
    def analytics_to_reporting(analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform analytics results to reporting format"""
        try:
            return {
                "report_data": {
                    "analysis_type": analytics_data.get("analysis_type"),
                    "results": analytics_data.get("predictions", {}),
                    "anomalies": analytics_data.get("anomalies", []),
                    "confidence": analytics_data.get("confidence", 0.0),
                    "timestamp": analytics_data.get("timestamp"),
                    "summary": analytics_data.get("recommendations", [])
                }
            }
        except Exception as e:
            logger.error(f"Error transforming analytics data: {e}")
            return {}

    @staticmethod
    def monitoring_to_compliance(monitoring_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform monitoring data to compliance format"""
        try:
            return {
                "compliance_point": monitoring_data.get("point_id"),
                "measurement_value": monitoring_data.get("value"),
                "measurement_time": monitoring_data.get("timestamp"),
                "within_limits": True,  # Would be calculated based on thresholds
                "quality_indicator": monitoring_data.get("quality"),
                "regulatory_context": {
                    "standard": "operational_limits",
                    "threshold_reference": "normal_operation"
                }
            }
        except Exception as e:
            logger.error(f"Error transforming monitoring data to compliance: {e}")
            return {}

class DataQueue:
    """High-performance thread-safe data queue"""

    def __init__(self, max_size: int = 10000):
        self.queue = queue.Queue(maxsize=max_size)
        self.metrics = PipelineMetrics()
        self.dropped_packets = 0
        self._lock = threading.Lock()

    def put(self, packet: DataPacket, block: bool = False) -> bool:
        """Add packet to queue"""
        try:
            if self.queue.full() and not block:
                self.dropped_packets += 1
                logger.warning(f"Queue full, dropping packet: {packet.packet_id}")
                return False

            self.queue.put(packet, block=block, timeout=1.0)
            return True

        except queue.Full:
            self.dropped_packets += 1
            return False
        except Exception as e:
            logger.error(f"Error adding packet to queue: {e}")
            return False

    def get(self, timeout: Optional[float] = None) -> Optional[DataPacket]:
        """Get packet from queue"""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error getting packet from queue: {e}")
            return None

    def size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.queue.empty()

class DataProcessor:
    """Processes data packets through various stages"""

    def __init__(self):
        self.validators = {}
        self.processors = {}
        self.enrichers = {}

    def add_validator(self, data_type: DataType, validator: Callable):
        """Add data validator for specific type"""
        self.validators[data_type] = validator

    def add_processor(self, data_type: DataType, processor: Callable):
        """Add data processor for specific type"""
        self.processors[data_type] = processor

    def add_enricher(self, data_type: DataType, enricher: Callable):
        """Add data enricher for specific type"""
        self.enrichers[data_type] = enricher

    async def validate_packet(self, packet: DataPacket) -> bool:
        """Validate data packet"""
        try:
            # Basic validation
            if not packet.packet_id or not packet.payload:
                return False

            # Type-specific validation
            validator = self.validators.get(packet.data_type)
            if validator:
                return await validator(packet)

            return True

        except Exception as e:
            logger.error(f"Error validating packet {packet.packet_id}: {e}")
            return False

    async def process_packet(self, packet: DataPacket) -> Optional[DataPacket]:
        """Process data packet"""
        try:
            # Type-specific processing
            processor = self.processors.get(packet.data_type)
            if processor:
                processed_payload = await processor(packet.payload)
                if processed_payload:
                    packet.payload = processed_payload

            # Enrich data
            enricher = self.enrichers.get(packet.data_type)
            if enricher:
                enriched_metadata = await enricher(packet.metadata)
                if enriched_metadata:
                    packet.metadata.update(enriched_metadata)

            return packet

        except Exception as e:
            logger.error(f"Error processing packet {packet.packet_id}: {e}")
            return None

class DataRouter:
    """Routes data packets to appropriate destinations"""

    def __init__(self):
        self.routes = defaultdict(list)
        self.subscribers = defaultdict(list)

    def add_route(self, data_type: DataType, source: str, destinations: List[str]):
        """Add routing rule"""
        self.routes[f"{data_type.value}_{source}"] = destinations

    def subscribe(self, subscriber_id: str, data_types: List[DataType], callback: Callable):
        """Subscribe to data types"""
        for data_type in data_types:
            self.subscribers[data_type].append({
                "id": subscriber_id,
                "callback": callback
            })

    async def route_packet(self, packet: DataPacket) -> List[str]:
        """Route packet to destinations"""
        try:
            # Get configured routes
            route_key = f"{packet.data_type.value}_{packet.source}"
            destinations = self.routes.get(route_key, packet.destination)

            # Notify subscribers
            subscribers = self.subscribers.get(packet.data_type, [])
            for subscriber in subscribers:
                try:
                    await subscriber["callback"](packet)
                except Exception as e:
                    logger.error(f"Error notifying subscriber {subscriber['id']}: {e}")

            return destinations

        except Exception as e:
            logger.error(f"Error routing packet {packet.packet_id}: {e}")
            return []

class IntegratedDataPipeline:
    """Main data pipeline coordinating all modules"""

    def __init__(self, system_core):
        self.system_core = system_core
        self.is_running = False

        # Pipeline components
        self.ingestion_queue = DataQueue(max_size=50000)
        self.processing_queue = DataQueue(max_size=10000)
        self.distribution_queue = DataQueue(max_size=5000)

        self.data_processor = DataProcessor()
        self.data_router = DataRouter()
        self.data_transformer = DataTransformer()

        # Worker threads
        self.workers = []
        self.worker_count = 4

        # Metrics
        self.pipeline_metrics = PipelineMetrics()
        self.start_time = None

        # Data buffers for analytics
        self.data_buffers = {
            DataType.RAW_SENSOR_DATA: deque(maxlen=10000),
            DataType.PROCESSED_DATA: deque(maxlen=5000),
            DataType.ALARM_DATA: deque(maxlen=1000)
        }

    async def initialize(self) -> bool:
        """Initialize the data pipeline"""
        try:
            logger.info("🔄 Initializing Integrated Data Pipeline...")

            # Setup data processors
            self._setup_data_processors()

            # Setup data routes
            self._setup_data_routes()

            # Setup module subscriptions
            await self._setup_module_subscriptions()

            # Start worker threads
            self._start_workers()

            # Connect to protocol manager
            await self._connect_protocol_manager()

            self.is_running = True
            self.start_time = datetime.now()

            logger.info("✅ Integrated Data Pipeline initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Error initializing data pipeline: {e}")
            return False

    def _setup_data_processors(self):
        """Setup data processors for different types"""

        async def validate_sensor_data(packet: DataPacket) -> bool:
            """Validate sensor data"""
            payload = packet.payload
            return (
                'value' in payload and
                isinstance(payload['value'], (int, float)) and
                'point_id' in payload
            )

        async def process_sensor_data(payload: Dict[str, Any]) -> Dict[str, Any]:
            """Process sensor data"""
            # Add calculated fields
            payload['processed_timestamp'] = datetime.now().isoformat()

            # Basic data validation and cleanup
            if isinstance(payload.get('value'), (int, float)):
                payload['value_validated'] = True
                # Add statistical info if we have historical data
                payload['trend'] = 'stable'  # Would calculate actual trend

            return payload

        async def enrich_sensor_data(metadata: Dict[str, Any]) -> Dict[str, Any]:
            """Enrich sensor data with additional metadata"""
            return {
                'pipeline_stage': 'processing',
                'quality_check': 'passed',
                'enrichment_timestamp': datetime.now().isoformat()
            }

        # Register processors
        self.data_processor.add_validator(DataType.RAW_SENSOR_DATA, validate_sensor_data)
        self.data_processor.add_processor(DataType.RAW_SENSOR_DATA, process_sensor_data)
        self.data_processor.add_enricher(DataType.RAW_SENSOR_DATA, enrich_sensor_data)

    def _setup_data_routes(self):
        """Setup data routing rules"""

        # Route sensor data to monitoring and analytics
        self.data_router.add_route(
            DataType.RAW_SENSOR_DATA,
            "protocol_manager",
            ["monitoring_system", "analytics_engine"]
        )

        # Route processed data to reporting and compliance
        self.data_router.add_route(
            DataType.PROCESSED_DATA,
            "monitoring_system",
            ["reporting_system", "compliance_system"]
        )

        # Route alarms to all interested systems
        self.data_router.add_route(
            DataType.ALARM_DATA,
            "monitoring_system",
            ["security_system", "integration_manager", "compliance_system"]
        )

    async def _setup_module_subscriptions(self):
        """Setup subscriptions for different modules"""

        # Analytics engine subscription
        async def analytics_callback(packet: DataPacket):
            """Handle data for analytics engine"""
            try:
                if self.system_core.analytics_engine and packet.data_type == DataType.PROCESSED_DATA:
                    # Store in analytics buffer
                    self.data_buffers[DataType.PROCESSED_DATA].append(packet.payload)

                    # Trigger analytics if we have enough data
                    if len(self.data_buffers[DataType.PROCESSED_DATA]) >= 100:
                        await self._trigger_analytics_processing()

            except Exception as e:
                logger.error(f"Error in analytics callback: {e}")

        # Security system subscription
        async def security_callback(packet: DataPacket):
            """Handle data for security system"""
            try:
                if self.system_core.security_framework:
                    # Check for security patterns
                    if packet.data_type == DataType.ALARM_DATA:
                        await self._check_security_patterns(packet)
            except Exception as e:
                logger.error(f"Error in security callback: {e}")

        # Compliance system subscription
        async def compliance_callback(packet: DataPacket):
            """Handle data for compliance system"""
            try:
                if self.system_core.compliance_manager:
                    # Transform and store for compliance
                    compliance_data = self.data_transformer.monitoring_to_compliance(packet.payload)
                    if compliance_data:
                        # Would store in compliance database
                        pass
            except Exception as e:
                logger.error(f"Error in compliance callback: {e}")

        # Register subscriptions
        self.data_router.subscribe(
            "analytics_engine",
            [DataType.PROCESSED_DATA, DataType.RAW_SENSOR_DATA],
            analytics_callback
        )

        self.data_router.subscribe(
            "security_system",
            [DataType.ALARM_DATA, DataType.SECURITY_EVENT],
            security_callback
        )

        self.data_router.subscribe(
            "compliance_system",
            [DataType.PROCESSED_DATA, DataType.ALARM_DATA],
            compliance_callback
        )

    async def _connect_protocol_manager(self):
        """Connect to protocol manager for data ingestion"""
        try:
            if not self.system_core.protocol_manager:
                return

            # Simulate protocol data ingestion
            async def protocol_data_generator():
                """Generate mock protocol data"""
                point_ids = ["T001", "P001", "F001", "L001", "PH001"]

                while self.is_running:
                    try:
                        for point_id in point_ids:
                            # Generate realistic sensor data
                            value = self._generate_sensor_value(point_id)

                            packet = DataPacket(
                                packet_id=f"proto_{point_id}_{int(time.time() * 1000)}",
                                timestamp=datetime.now(),
                                data_type=DataType.RAW_SENSOR_DATA,
                                source="protocol_manager",
                                destination=["monitoring_system"],
                                payload={
                                    "point_id": point_id,
                                    "value": value,
                                    "quality": "GOOD",
                                    "timestamp": datetime.now().isoformat(),
                                    "unit": self._get_unit_for_point(point_id)
                                },
                                metadata={
                                    "protocol": "modbus_tcp",
                                    "device_id": "main_plc",
                                    "register_address": hash(point_id) % 1000
                                }
                            )

                            await self.ingest_data(packet)

                        await asyncio.sleep(1)  # Generate data every second

                    except Exception as e:
                        logger.error(f"Error generating protocol data: {e}")
                        await asyncio.sleep(5)

            # Start data generation
            asyncio.create_task(protocol_data_generator())

        except Exception as e:
            logger.error(f"Error connecting to protocol manager: {e}")

    def _generate_sensor_value(self, point_id: str) -> float:
        """Generate realistic sensor values"""
        base_time = time.time()

        if point_id == "T001":  # Temperature
            return 20 + 10 * np.sin(base_time / 3600) + np.random.normal(0, 1)
        elif point_id == "P001":  # Pressure
            return 5 + 2 * np.cos(base_time / 1800) + np.random.normal(0, 0.2)
        elif point_id == "F001":  # Flow
            return 100 + 20 * np.sin(base_time / 900) + np.random.normal(0, 2)
        elif point_id == "L001":  # Level
            return 50 + 30 * np.cos(base_time / 7200) + np.random.normal(0, 1)
        elif point_id == "PH001":  # pH
            return 7.0 + 0.5 * np.sin(base_time / 1800) + np.random.normal(0, 0.1)
        else:
            return np.random.uniform(0, 100)

    def _get_unit_for_point(self, point_id: str) -> str:
        """Get unit for measurement point"""
        units = {
            "T001": "°C",
            "P001": "bar",
            "F001": "L/min",
            "L001": "%",
            "PH001": "pH"
        }
        return units.get(point_id, "")

    def _start_workers(self):
        """Start worker threads for pipeline processing"""

        def ingestion_worker():
            """Process ingestion queue"""
            while self.is_running:
                try:
                    packet = self.ingestion_queue.get(timeout=1.0)
                    if packet:
                        # Move to processing queue after validation
                        asyncio.run(self._process_ingestion_packet(packet))
                except Exception as e:
                    if self.is_running:  # Only log if not shutting down
                        logger.error(f"Error in ingestion worker: {e}")

        def processing_worker():
            """Process processing queue"""
            while self.is_running:
                try:
                    packet = self.processing_queue.get(timeout=1.0)
                    if packet:
                        asyncio.run(self._process_packet_async(packet))
                except Exception as e:
                    if self.is_running:
                        logger.error(f"Error in processing worker: {e}")

        def distribution_worker():
            """Process distribution queue"""
            while self.is_running:
                try:
                    packet = self.distribution_queue.get(timeout=1.0)
                    if packet:
                        asyncio.run(self._distribute_packet(packet))
                except Exception as e:
                    if self.is_running:
                        logger.error(f"Error in distribution worker: {e}")

        # Start worker threads
        self.workers = [
            threading.Thread(target=ingestion_worker, name="ingestion_worker"),
            threading.Thread(target=processing_worker, name="processing_worker_1"),
            threading.Thread(target=processing_worker, name="processing_worker_2"),
            threading.Thread(target=distribution_worker, name="distribution_worker")
        ]

        for worker in self.workers:
            worker.daemon = True
            worker.start()

        logger.info(f"🔄 Started {len(self.workers)} pipeline workers")

    async def _process_ingestion_packet(self, packet: DataPacket):
        """Process packet in ingestion stage"""
        try:
            start_time = time.time()

            # Validate packet
            if await self.data_processor.validate_packet(packet):
                # Move to processing queue
                if not self.processing_queue.put(packet):
                    logger.warning(f"Processing queue full, dropping packet: {packet.packet_id}")
            else:
                logger.warning(f"Packet validation failed: {packet.packet_id}")

            # Update metrics
            processing_time = time.time() - start_time
            self._update_metrics(processing_time, success=True)

        except Exception as e:
            logger.error(f"Error processing ingestion packet: {e}")
            self._update_metrics(0, success=False)

    async def _process_packet_async(self, packet: DataPacket):
        """Process packet asynchronously"""
        try:
            start_time = time.time()

            # Process packet
            processed_packet = await self.data_processor.process_packet(packet)

            if processed_packet:
                # Update data type to processed
                processed_packet.data_type = DataType.PROCESSED_DATA

                # Route packet
                destinations = await self.data_router.route_packet(processed_packet)
                processed_packet.destination = destinations

                # Send to distribution
                if not self.distribution_queue.put(processed_packet):
                    logger.warning(f"Distribution queue full, dropping packet: {packet.packet_id}")

                # Store in buffer for analytics
                self.data_buffers[DataType.PROCESSED_DATA].append(processed_packet.payload)

            processing_time = time.time() - start_time
            self._update_metrics(processing_time, success=True)

        except Exception as e:
            logger.error(f"Error processing packet: {e}")
            self._update_metrics(0, success=False)

    async def _distribute_packet(self, packet: DataPacket):
        """Distribute packet to destinations"""
        try:
            # Send to monitoring system
            if "monitoring_system" in packet.destination and self.system_core.monitoring_system:
                await self._send_to_monitoring_system(packet)

            # Send to reporting system
            if "reporting_system" in packet.destination and self.system_core.report_generator:
                await self._send_to_reporting_system(packet)

            # Send to integration manager
            if "integration_manager" in packet.destination and self.system_core.integration_manager:
                await self._send_to_integration_manager(packet)

        except Exception as e:
            logger.error(f"Error distributing packet: {e}")

    async def _send_to_monitoring_system(self, packet: DataPacket):
        """Send data to monitoring system"""
        try:
            # Transform data to monitoring format
            monitoring_data = self.data_transformer.protocol_to_monitoring(packet.payload)

            if monitoring_data and self.system_core.monitoring_system:
                # Add to monitoring system's data buffer
                from realtime_monitoring import MonitoringData

                mon_data = MonitoringData(
                    point_id=monitoring_data.get("point_id"),
                    timestamp=monitoring_data.get("timestamp"),
                    value=monitoring_data.get("value"),
                    quality=monitoring_data.get("quality"),
                    status=monitoring_data.get("status")
                )

                self.system_core.monitoring_system.data_buffer.add_point(
                    mon_data.point_id, mon_data
                )

        except Exception as e:
            logger.error(f"Error sending to monitoring system: {e}")

    async def _send_to_reporting_system(self, packet: DataPacket):
        """Send data to reporting system"""
        try:
            # Reporting system will pull data from monitoring database
            # This is just a placeholder for integration
            pass
        except Exception as e:
            logger.error(f"Error sending to reporting system: {e}")

    async def _send_to_integration_manager(self, packet: DataPacket):
        """Send data to integration manager"""
        try:
            # Integration manager would format and send to external systems
            if self.system_core.integration_manager:
                # This would trigger actual integration sync
                pass
        except Exception as e:
            logger.error(f"Error sending to integration manager: {e}")

    async def _trigger_analytics_processing(self):
        """Trigger analytics processing on buffered data"""
        try:
            if not self.system_core.analytics_engine:
                return

            # Convert buffer to DataFrame for analytics
            data_list = list(self.data_buffers[DataType.PROCESSED_DATA])
            if len(data_list) < 10:
                return

            # Create analytics data structure
            df_data = []
            for item in data_list[-100:]:  # Last 100 points
                df_data.append({
                    'point_id': item.get('point_id'),
                    'timestamp': item.get('timestamp'),
                    'value': item.get('value', 0),
                    'quality': item.get('quality', 'GOOD')
                })

            if df_data:
                df = pd.DataFrame(df_data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])

                # This would trigger actual analytics processing
                logger.debug(f"Analytics triggered with {len(df)} data points")

        except Exception as e:
            logger.error(f"Error triggering analytics: {e}")

    async def _check_security_patterns(self, packet: DataPacket):
        """Check for security patterns in alarm data"""
        try:
            if self.system_core.security_framework:
                # Analyze packet for security threats
                # This would implement actual security analysis
                pass
        except Exception as e:
            logger.error(f"Error checking security patterns: {e}")

    def _update_metrics(self, processing_time: float, success: bool):
        """Update pipeline metrics"""
        try:
            with threading.Lock():
                if success:
                    self.pipeline_metrics.packets_processed += 1
                else:
                    self.pipeline_metrics.packets_dropped += 1

                # Update average processing time
                total_packets = self.pipeline_metrics.packets_processed
                if total_packets > 0:
                    self.pipeline_metrics.avg_processing_time = (
                        (self.pipeline_metrics.avg_processing_time * (total_packets - 1) + processing_time) / total_packets
                    )

                # Update queue depths
                self.pipeline_metrics.queue_depth = (
                    self.ingestion_queue.size() +
                    self.processing_queue.size() +
                    self.distribution_queue.size()
                )

                # Calculate throughput
                if self.start_time:
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    if elapsed > 0:
                        self.pipeline_metrics.throughput_per_second = total_packets / elapsed

                # Calculate error rate
                total_attempts = total_packets + self.pipeline_metrics.packets_dropped
                if total_attempts > 0:
                    self.pipeline_metrics.error_rate = self.pipeline_metrics.packets_dropped / total_attempts

                self.pipeline_metrics.last_updated = datetime.now()

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    async def ingest_data(self, packet: DataPacket) -> bool:
        """Main entry point for data ingestion"""
        try:
            return self.ingestion_queue.put(packet)
        except Exception as e:
            logger.error(f"Error ingesting data: {e}")
            return False

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get comprehensive pipeline status"""
        return {
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "metrics": asdict(self.pipeline_metrics),
            "queue_sizes": {
                "ingestion": self.ingestion_queue.size(),
                "processing": self.processing_queue.size(),
                "distribution": self.distribution_queue.size()
            },
            "worker_count": len([w for w in self.workers if w.is_alive()]),
            "buffer_sizes": {
                data_type.value: len(buffer)
                for data_type, buffer in self.data_buffers.items()
            },
            "timestamp": datetime.now().isoformat()
        }

    async def shutdown(self):
        """Shutdown the data pipeline"""
        try:
            logger.info("🛑 Shutting down data pipeline...")
            self.is_running = False

            # Wait for workers to finish
            for worker in self.workers:
                if worker.is_alive():
                    worker.join(timeout=5)

            logger.info("✅ Data pipeline shutdown completed")

        except Exception as e:
            logger.error(f"Error shutting down pipeline: {e}")

# Integration function to connect pipeline with main application
def create_integrated_pipeline(system_core) -> IntegratedDataPipeline:
    """Create and initialize the integrated data pipeline"""
    return IntegratedDataPipeline(system_core)