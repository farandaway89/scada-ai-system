"""
SCADA AI System - Main Application Entry Point
Integrated Enterprise-Grade Industrial Automation System
"""

import asyncio
import logging
import signal
import sys
import os
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass
import json

# FastAPI and web framework
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn

# Import our integrated modules
from industrial_protocols import ProtocolManager, ProtocolConfig, ProtocolType
from cybersecurity_framework import SecurityFramework, SecurityEvent, ThreatType, SecurityLevel
from ml_analytics_engine import MLAnalyticsEngine, AnalyticsType
from realtime_monitoring import RealTimeMonitoringSystem, MonitoringPoint, AlertRule, AlertType, AlertPriority
from professional_reporting import ReportGenerator, ReportConfiguration, ReportType, ReportFormat
from compliance_audit_system import ComplianceManager, AuditTrailManager, ComplianceStandard, AuditEvent, AuditEventType, AuditSeverity
from enterprise_integration import EnterpriseIntegrationManager, IntegrationConfig, IntegrationType, MessageFormat
from data_pipeline import IntegratedDataPipeline, create_integrated_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/application.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Ensure log directory exists
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('config', exist_ok=True)
os.makedirs('reports', exist_ok=True)

@dataclass
class SystemConfiguration:
    """System-wide configuration"""
    environment: str = os.getenv("ENVIRONMENT", "production")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "9000"))
    websocket_port: int = int(os.getenv("WEBSOCKET_PORT", "9765"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/scada_system.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    enable_security: bool = os.getenv("ENABLE_SECURITY", "true").lower() == "true"
    enable_analytics: bool = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    enable_monitoring: bool = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    enable_reporting: bool = os.getenv("ENABLE_REPORTING", "true").lower() == "true"
    enable_compliance: bool = os.getenv("ENABLE_COMPLIANCE", "true").lower() == "true"
    enable_integration: bool = os.getenv("ENABLE_INTEGRATION", "true").lower() == "true"

class SCADASystemCore:
    """Core system that manages all integrated modules"""

    def __init__(self, config: SystemConfiguration):
        self.config = config
        self.is_running = False
        self.startup_time = None

        # System state
        self.system_status = "initializing"
        self.active_connections = 0
        self.processed_messages = 0

        # Initialize all subsystems
        self.security_framework = None
        self.protocol_manager = None
        self.monitoring_system = None
        self.analytics_engine = None
        self.report_generator = None
        self.compliance_manager = None
        self.audit_manager = None
        self.integration_manager = None
        self.data_pipeline = None

        # Background tasks
        self.background_tasks = []

    async def initialize(self) -> bool:
        """Initialize all system components"""
        try:
            logger.info("🚀 Starting SCADA AI System initialization...")

            # 1. Initialize Security Framework (First - everything depends on security)
            if self.config.enable_security:
                logger.info("🔐 Initializing Security Framework...")
                self.security_framework = SecurityFramework()
                if not self.security_framework.initialize_security():
                    raise Exception("Security framework initialization failed")
                logger.info("✅ Security Framework initialized")

            # 2. Initialize Audit Trail Manager
            logger.info("📋 Initializing Audit Trail Manager...")
            self.audit_manager = AuditTrailManager("data/audit_trail.db")
            logger.info("✅ Audit Trail Manager initialized")

            # 3. Initialize Compliance Manager
            if self.config.enable_compliance:
                logger.info("📊 Initializing Compliance Manager...")
                self.compliance_manager = ComplianceManager("data/compliance.db")
                logger.info("✅ Compliance Manager initialized")

            # 4. Initialize Protocol Manager
            logger.info("🔌 Initializing Protocol Manager...")
            self.protocol_manager = ProtocolManager()
            self._configure_default_protocols()
            logger.info("✅ Protocol Manager initialized")

            # 5. Initialize Real-time Monitoring System
            if self.config.enable_monitoring:
                logger.info("📡 Initializing Real-time Monitoring System...")
                self.monitoring_system = RealTimeMonitoringSystem()
                self.monitoring_system.initialize_database("data/monitoring.db")
                self._configure_monitoring_points()
                self.monitoring_system.start_monitoring()
                logger.info("✅ Real-time Monitoring System initialized")

            # 6. Initialize ML Analytics Engine
            if self.config.enable_analytics:
                logger.info("🧠 Initializing ML Analytics Engine...")
                self.analytics_engine = MLAnalyticsEngine()
                logger.info("✅ ML Analytics Engine initialized")

            # 7. Initialize Report Generator
            if self.config.enable_reporting:
                logger.info("📊 Initializing Report Generator...")
                self.report_generator = ReportGenerator(
                    sqlite3.connect("data/monitoring.db"),
                    "reports"
                )
                logger.info("✅ Report Generator initialized")

            # 8. Initialize Enterprise Integration Manager
            if self.config.enable_integration:
                logger.info("🌐 Initializing Enterprise Integration Manager...")
                # Use DATABASE_URL from environment or default to SQLite
                integration_db_url = self.config.database_url if self.config.database_url != "sqlite:///data/scada_system.db" else "sqlite:///data/integration.db"
                self.integration_manager = EnterpriseIntegrationManager(integration_db_url)
                self._configure_enterprise_integrations()
                logger.info("✅ Enterprise Integration Manager initialized")

            # 9. Initialize Integrated Data Pipeline
            logger.info("🔄 Initializing Integrated Data Pipeline...")
            self.data_pipeline = create_integrated_pipeline(self)
            if not await self.data_pipeline.initialize():
                raise Exception("Data pipeline initialization failed")
            logger.info("✅ Integrated Data Pipeline initialized")

            # 10. Start background tasks
            await self._start_background_tasks()

            self.system_status = "running"
            self.startup_time = datetime.now()
            self.is_running = True

            # Log successful initialization
            await self._log_system_event(
                "SYSTEM_STARTUP",
                "SCADA AI System initialized successfully",
                "SYSTEM"
            )

            logger.info("🎉 SCADA AI System initialization completed successfully!")
            return True

        except Exception as e:
            self.system_status = "error"
            logger.error(f"❌ System initialization failed: {e}")
            await self._log_system_event(
                "SYSTEM_ERROR",
                f"System initialization failed: {str(e)}",
                "SYSTEM"
            )
            return False

    def _configure_default_protocols(self):
        """Configure default industrial protocol connections"""
        try:
            # Modbus TCP configuration for water treatment plant
            modbus_config = ProtocolConfig(
                protocol_type=ProtocolType.MODBUS_TCP,
                host="192.168.1.100",
                port=502,
                unit_id=1,
                timeout=10.0
            )

            # DNP3 configuration for distribution system
            dnp3_config = ProtocolConfig(
                protocol_type=ProtocolType.DNPV3,
                host="192.168.1.101",
                port=20000,
                unit_id=10
            )

            # IEC 61850 configuration for power monitoring
            iec61850_config = ProtocolConfig(
                protocol_type=ProtocolType.IEC_61850,
                host="192.168.1.102",
                port=102
            )

            # Add connections (will show connection attempts in logs)
            self.protocol_manager.add_connection("main_plc", modbus_config)
            self.protocol_manager.add_connection("distribution_rtu", dnp3_config)
            self.protocol_manager.add_connection("power_monitor", iec61850_config)

            logger.info("📡 Default protocol connections configured")

        except Exception as e:
            logger.error(f"Error configuring default protocols: {e}")

    def _configure_monitoring_points(self):
        """Configure default monitoring points"""
        try:
            # Water treatment monitoring points
            monitoring_points = [
                MonitoringPoint(
                    point_id="T001",
                    name="Inlet Temperature",
                    data_type="float",
                    source_address="192.168.1.100:502",
                    scan_rate_ms=1000,
                    alarm_high=35.0,
                    warning_high=30.0
                ),
                MonitoringPoint(
                    point_id="P001",
                    name="System Pressure",
                    data_type="float",
                    source_address="192.168.1.100:502",
                    scan_rate_ms=500,
                    alarm_high=8.0,
                    alarm_low=2.0
                ),
                MonitoringPoint(
                    point_id="F001",
                    name="Flow Rate",
                    data_type="float",
                    source_address="192.168.1.100:502",
                    scan_rate_ms=2000,
                    alarm_low=50.0
                ),
                MonitoringPoint(
                    point_id="L001",
                    name="Tank Level",
                    data_type="float",
                    source_address="192.168.1.100:502",
                    scan_rate_ms=5000,
                    alarm_high=95.0,
                    alarm_low=10.0
                ),
                MonitoringPoint(
                    point_id="PH001",
                    name="pH Level",
                    data_type="float",
                    source_address="192.168.1.100:502",
                    scan_rate_ms=10000,
                    alarm_high=8.5,
                    alarm_low=6.5
                )
            ]

            # Add monitoring points
            for point in monitoring_points:
                self.monitoring_system.add_monitoring_point(point)

            # Configure alert rules
            alert_rules = [
                AlertRule(
                    rule_id="HIGH_TEMP",
                    name="High Temperature Alert",
                    condition="get_value('T001') > 35",
                    alert_type=AlertType.PROCESS_ALARM,
                    priority=AlertPriority.CRITICAL,
                    message_template="Critical temperature: {value}°C at {point}",
                    acknowledgement_required=True
                ),
                AlertRule(
                    rule_id="LOW_PRESSURE",
                    name="Low Pressure Alert",
                    condition="get_value('P001') < 2",
                    alert_type=AlertType.SYSTEM_FAULT,
                    priority=AlertPriority.EMERGENCY,
                    message_template="Emergency: Low pressure {value} bar at {point}"
                ),
                AlertRule(
                    rule_id="PH_DEVIATION",
                    name="pH Deviation Alert",
                    condition="get_value('PH001') > 8.5 or get_value('PH001') < 6.5",
                    alert_type=AlertType.QUALITY_DEVIATION,
                    priority=AlertPriority.HIGH,
                    message_template="pH deviation: {value} at {point}"
                )
            ]

            for rule in alert_rules:
                self.monitoring_system.alert_manager.add_alert_rule(rule)

            logger.info("📊 Default monitoring points and alert rules configured")

        except Exception as e:
            logger.error(f"Error configuring monitoring points: {e}")

    def _configure_enterprise_integrations(self):
        """Configure enterprise system integrations"""
        try:
            # ERP Integration (Mock configuration)
            erp_config = IntegrationConfig(
                integration_id="erp_production",
                name="Production ERP System",
                integration_type=IntegrationType.ERP_SYSTEM,
                endpoint_url="http://localhost:8080/api",  # Mock endpoint
                authentication={
                    "username": "scada_user",
                    "password": "demo_password",
                    "client_id": "scada_client"
                },
                message_format=MessageFormat.JSON,
                schedule_interval=300,  # 5 minutes
                enabled=False  # Disabled by default for demo
            )

            # Cloud Platform Integration
            cloud_config = IntegrationConfig(
                integration_id="cloud_telemetry",
                name="Cloud Telemetry Platform",
                integration_type=IntegrationType.CLOUD_PLATFORM,
                endpoint_url="https://api.demo-cloud.com",
                authentication={
                    "platform": "aws",
                    "region": "us-east-1",
                    "access_key": "demo_key",
                    "secret_key": "demo_secret"
                },
                message_format=MessageFormat.JSON,
                schedule_interval=60,  # 1 minute
                enabled=False  # Disabled by default for demo
            )

            # Add integrations
            self.integration_manager.add_integration(erp_config)
            self.integration_manager.add_integration(cloud_config)

            logger.info("🏢 Enterprise integrations configured")

        except Exception as e:
            logger.error(f"Error configuring enterprise integrations: {e}")

    async def _start_background_tasks(self):
        """Start background tasks"""
        try:
            # Data processing task
            async def data_processing_task():
                while self.is_running:
                    try:
                        if self.analytics_engine and self.monitoring_system:
                            # Run analytics on recent data every 5 minutes
                            await asyncio.sleep(300)
                            if self.is_running:
                                await self._run_periodic_analytics()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error in data processing task: {e}")
                        await asyncio.sleep(60)

            # System health monitoring task
            async def health_monitoring_task():
                while self.is_running:
                    try:
                        await asyncio.sleep(60)  # Check every minute
                        if self.is_running:
                            await self._monitor_system_health()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error in health monitoring task: {e}")
                        await asyncio.sleep(60)

            # Enterprise integration sync task
            async def integration_sync_task():
                while self.is_running:
                    try:
                        await asyncio.sleep(600)  # Sync every 10 minutes
                        if self.is_running and self.integration_manager:
                            await self._sync_enterprise_integrations()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error in integration sync task: {e}")
                        await asyncio.sleep(300)

            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(data_processing_task()),
                asyncio.create_task(health_monitoring_task()),
                asyncio.create_task(integration_sync_task())
            ]

            logger.info("🔄 Background tasks started")

        except Exception as e:
            logger.error(f"Error starting background tasks: {e}")

    async def _run_periodic_analytics(self):
        """Run periodic analytics on system data"""
        try:
            logger.info("🧠 Running periodic analytics...")

            # This would integrate with real data from monitoring system
            # For now, we'll log the capability

            if self.monitoring_system:
                status = self.monitoring_system.get_system_status()
                logger.info(f"📊 System Status: {status}")

            # Log analytics completion
            await self._log_system_event(
                "ANALYTICS_COMPLETED",
                "Periodic analytics completed successfully",
                "SYSTEM"
            )

        except Exception as e:
            logger.error(f"Error running periodic analytics: {e}")

    async def _monitor_system_health(self):
        """Monitor system health and performance"""
        try:
            import psutil

            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Check thresholds
            alerts = []
            if cpu_percent > 80:
                alerts.append(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 85:
                alerts.append(f"High memory usage: {memory.percent}%")
            if disk.percent > 90:
                alerts.append(f"High disk usage: {disk.percent}%")

            # Log alerts if any
            for alert in alerts:
                logger.warning(f"⚠️ System Health Alert: {alert}")
                await self._log_system_event(
                    "SYSTEM_HEALTH_ALERT",
                    alert,
                    "SYSTEM"
                )

            # Update system metrics (could be exposed via API)
            self.system_metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "uptime": (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0
            }

        except Exception as e:
            logger.error(f"Error monitoring system health: {e}")

    async def _sync_enterprise_integrations(self):
        """Sync with enterprise systems"""
        try:
            if self.integration_manager:
                logger.info("🔄 Syncing enterprise integrations...")
                results = await self.integration_manager.sync_all_integrations()
                logger.info(f"📊 Integration sync results: {results}")

                await self._log_system_event(
                    "INTEGRATION_SYNC",
                    f"Enterprise integration sync completed: {results}",
                    "SYSTEM"
                )
        except Exception as e:
            logger.error(f"Error syncing enterprise integrations: {e}")

    async def _log_system_event(self, event_type: str, description: str, user: str):
        """Log system events to audit trail"""
        try:
            if self.audit_manager:
                event = AuditEvent(
                    event_id=f"sys_{int(datetime.now().timestamp())}",
                    timestamp=datetime.now(),
                    event_type=AuditEventType.SYSTEM_MAINTENANCE,
                    severity=AuditSeverity.INFO,
                    user_id=user,
                    session_id=None,
                    source_ip="127.0.0.1",
                    resource_accessed="system",
                    action_performed=event_type,
                    old_value=None,
                    new_value=description,
                    success=True,
                    error_message=None,
                    additional_data={}
                )

                self.audit_manager.log_audit_event(event)
        except Exception as e:
            logger.error(f"Error logging system event: {e}")

    async def shutdown(self):
        """Gracefully shutdown the system"""
        try:
            logger.info("🛑 Starting system shutdown...")
            self.is_running = False
            self.system_status = "shutting_down"

            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()

            # Shutdown monitoring system
            if self.monitoring_system:
                self.monitoring_system.stop_monitoring()

            # Shutdown data pipeline
            if self.data_pipeline:
                await self.data_pipeline.shutdown()

            # Shutdown integration manager
            if self.integration_manager:
                await self.integration_manager.stop_monitoring()

            # Shutdown protocol manager
            if self.protocol_manager:
                self.protocol_manager.shutdown()

            # Log shutdown
            await self._log_system_event(
                "SYSTEM_SHUTDOWN",
                "SCADA AI System shutdown completed",
                "SYSTEM"
            )

            self.system_status = "stopped"
            logger.info("✅ System shutdown completed")

        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "system_status": self.system_status,
            "is_running": self.is_running,
            "startup_time": self.startup_time.isoformat() if self.startup_time else None,
            "uptime_seconds": (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0,
            "active_connections": self.active_connections,
            "processed_messages": self.processed_messages,
            "modules": {
                "security": self.security_framework is not None,
                "protocols": self.protocol_manager is not None,
                "monitoring": self.monitoring_system is not None,
                "analytics": self.analytics_engine is not None,
                "reporting": self.report_generator is not None,
                "compliance": self.compliance_manager is not None,
                "integration": self.integration_manager is not None,
                "data_pipeline": self.data_pipeline is not None
            },
            "data_pipeline_status": self.data_pipeline.get_pipeline_status() if self.data_pipeline else None,
            "system_metrics": getattr(self, 'system_metrics', {}),
            "timestamp": datetime.now().isoformat()
        }

# Global system instance
system_core = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global system_core

    # Startup
    config = SystemConfiguration()
    system_core = SCADASystemCore(config)

    success = await system_core.initialize()
    if not success:
        logger.error("Failed to initialize system")
        raise Exception("System initialization failed")

    yield

    # Shutdown
    if system_core:
        await system_core.shutdown()

# Create FastAPI application
app = FastAPI(
    title="SCADA AI System",
    description="Enterprise-Grade Industrial Automation and Intelligence Platform",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Security dependency
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    if not credentials:
        if system_core and system_core.config.enable_security:
            raise HTTPException(status_code=401, detail="Authentication required")
        # If security is disabled, allow access
        return {"user_id": "demo_user", "role": "admin"}

    # Validate token (simple check for demo)
    if credentials.credentials.startswith("demo_token_"):
        return {"user_id": "demo_user", "role": "admin"}

    raise HTTPException(status_code=401, detail="Invalid token")

# API Routes

@app.post("/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Simple login endpoint for demo purposes"""
    # Simple authentication - in production, verify against database
    if username == "admin" and password == "admin123":
        # Generate a simple token (in production, use JWT)
        token = f"demo_token_{username}"
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"username": username, "role": "admin"}
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/")
async def root():
    """Root endpoint - return the frontend dashboard"""
    return FileResponse("static/index.html")

@app.get("/status")
async def system_status():
    """Get comprehensive system status"""
    if not system_core:
        raise HTTPException(status_code=503, detail="System not initialized")

    return system_core.get_system_status()

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers"""
    if not system_core or not system_core.is_running:
        raise HTTPException(status_code=503, detail="System not ready")

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system_status": system_core.system_status
    }

@app.get("/monitoring/current")
async def get_current_monitoring_data(user = Depends(get_current_user)):
    """Get current monitoring data"""
    if not system_core or not system_core.monitoring_system:
        raise HTTPException(status_code=503, detail="Monitoring system not available")

    status = system_core.monitoring_system.get_system_status()
    return {
        "monitoring_status": status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/analytics/dashboard")
async def get_analytics_dashboard(user = Depends(get_current_user)):
    """Get analytics dashboard data"""
    if not system_core or not system_core.analytics_engine:
        raise HTTPException(status_code=503, detail="Analytics engine not available")

    summary = system_core.analytics_engine.get_analytics_summary()
    return {
        "analytics_summary": summary,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/reports/generate")
async def generate_report(
    report_type: str,
    format: str = "html",
    days_back: int = 7,
    user = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Generate system report"""
    if not system_core or not system_core.report_generator:
        raise HTTPException(status_code=503, detail="Report generator not available")

    try:
        # Configure report
        config = ReportConfiguration(
            report_id=f"report_{int(datetime.now().timestamp())}",
            title=f"SCADA System {report_type.title()} Report",
            report_type=ReportType.OPERATIONAL_SUMMARY,
            format=ReportFormat.HTML if format.lower() == "html" else ReportFormat.PDF,
            time_range={
                'start': datetime.now() - timedelta(days=days_back),
                'end': datetime.now()
            },
            data_sources=['T001', 'P001', 'F001', 'L001', 'PH001'],
            visualizations=[]
        )

        # Generate report in background
        if background_tasks:
            background_tasks.add_task(system_core.report_generator.generate_report, config)
            return {"message": "Report generation started", "report_id": config.report_id}
        else:
            report_path = system_core.report_generator.generate_report(config)
            return {"report_path": report_path, "report_id": config.report_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@app.get("/compliance/dashboard")
async def get_compliance_dashboard(user = Depends(get_current_user)):
    """Get compliance dashboard"""
    if not system_core or not system_core.compliance_manager:
        raise HTTPException(status_code=503, detail="Compliance manager not available")

    dashboard = system_core.compliance_manager.get_compliance_dashboard()
    return {
        "compliance_dashboard": dashboard,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/integration/status")
async def get_integration_status(user = Depends(get_current_user)):
    """Get enterprise integration status"""
    if not system_core or not system_core.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not available")

    status = system_core.integration_manager.get_integration_status()
    return {
        "integration_status": status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/pipeline/status")
async def get_pipeline_status(user = Depends(get_current_user)):
    """Get data pipeline status"""
    if not system_core or not system_core.data_pipeline:
        raise HTTPException(status_code=503, detail="Data pipeline not available")

    status = system_core.data_pipeline.get_pipeline_status()
    return {
        "pipeline_status": status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/pipeline/metrics")
async def get_pipeline_metrics(user = Depends(get_current_user)):
    """Get detailed pipeline metrics"""
    if not system_core or not system_core.data_pipeline:
        raise HTTPException(status_code=503, detail="Data pipeline not available")

    status = system_core.data_pipeline.get_pipeline_status()
    return {
        "metrics": status.get("metrics", {}),
        "queue_sizes": status.get("queue_sizes", {}),
        "buffer_sizes": status.get("buffer_sizes", {}),
        "performance": {
            "throughput_per_second": status.get("metrics", {}).get("throughput_per_second", 0),
            "avg_processing_time": status.get("metrics", {}).get("avg_processing_time", 0),
            "error_rate": status.get("metrics", {}).get("error_rate", 0)
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/system/shutdown")
async def shutdown_system(user = Depends(get_current_user)):
    """Gracefully shutdown the system"""
    if not system_core:
        raise HTTPException(status_code=503, detail="System not available")

    # Check if user has admin privileges (in production)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    await system_core.shutdown()
    return {"message": "System shutdown initiated"}

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    if system_core:
        asyncio.create_task(system_core.shutdown())

# Main execution
if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Configuration
    config = SystemConfiguration()

    # Update logging level
    logging.getLogger().setLevel(getattr(logging, config.log_level))

    logger.info("🚀 Starting SCADA AI System...")

    try:
        # Run the application
        uvicorn.run(
            "main_application:app",
            host=config.host,
            port=config.port,
            log_level=config.log_level.lower(),
            workers=1,  # Must be 1 for lifespan events
            reload=config.debug
        )
    except KeyboardInterrupt:
        logger.info("👋 SCADA AI System stopped by user")
    except Exception as e:
        logger.error(f"❌ SCADA AI System error: {e}")
        sys.exit(1)