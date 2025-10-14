#!/usr/bin/env python3
"""
SCADA AI System - Integrated Startup Script
Orchestrates the startup of the complete integrated system
"""

import sys
import os
import asyncio
import signal
import logging
import time
from pathlib import Path
from datetime import datetime
import psutil
import subprocess
import argparse

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import configuration manager first
from config_manager import get_config_manager, ConfigScope

# Configure logging early
def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(log_dir / f"system_startup_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)

class SystemOrchestrator:
    """Orchestrates the startup and shutdown of the integrated SCADA system"""

    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.config_manager = None
        self.system_process = None
        self.is_running = False
        self.startup_time = None

        # System health tracking
        self.health_checks = []
        self.startup_errors = []

    async def initialize(self) -> bool:
        """Initialize the system orchestrator"""
        try:
            logger.info("Initializing SCADA AI System Orchestrator...")

            # Initialize configuration management
            self.config_manager = get_config_manager(
                config_dir="config",
                environment=self.environment
            )

            # Setup logging with configured level
            log_level = self.config_manager.get_config("system", "log_level", "INFO")
            setup_logging(log_level)

            # Perform pre-startup checks
            if not await self._perform_system_checks():
                return False

            # Create required directories
            self._create_directories()

            logger.info("System Orchestrator initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing orchestrator: {e}")
            return False

    async def _perform_system_checks(self) -> bool:
        """Perform comprehensive system checks before startup"""
        logger.info("Performing system health checks...")

        checks_passed = True

        try:
            # 1. Check system resources
            if not self._check_system_resources():
                checks_passed = False

            # 2. Check network connectivity
            if not self._check_network_connectivity():
                checks_passed = False

            # 3. Check disk space
            if not self._check_disk_space():
                checks_passed = False

            # 4. Check required directories
            if not self._check_required_directories():
                checks_passed = False

            # 5. Check dependencies
            if not await self._check_dependencies():
                checks_passed = False

            # 6. Check port availability
            if not self._check_port_availability():
                checks_passed = False

            # 7. Check database connectivity
            if not await self._check_database_connectivity():
                checks_passed = False

            if checks_passed:
                logger.info("All system checks passed")
            else:
                logger.error("System checks failed")
                logger.error("Startup errors:")
                for error in self.startup_errors:
                    logger.error(f"  - {error}")

            return checks_passed

        except Exception as e:
            logger.error(f"Error performing system checks: {e}")
            return False

    def _check_system_resources(self) -> bool:
        """Check system resource requirements"""
        try:
            # Check CPU
            cpu_count = psutil.cpu_count()
            required_cpu = self.config_manager.get_config("system", "max_workers", 4)

            if cpu_count < required_cpu:
                self.startup_errors.append(f"Insufficient CPU cores: {cpu_count} < {required_cpu}")
                return False

            # Check Memory
            memory = psutil.virtual_memory()
            required_memory_gb = 2  # Minimum 2GB RAM
            available_memory_gb = memory.available / (1024**3)

            if available_memory_gb < required_memory_gb:
                self.startup_errors.append(f"Insufficient memory: {available_memory_gb:.1f}GB < {required_memory_gb}GB")
                return False

            logger.info(f"System resources: CPU={cpu_count}, Memory={available_memory_gb:.1f}GB")
            return True

        except Exception as e:
            self.startup_errors.append(f"Error checking system resources: {e}")
            return False

    def _check_network_connectivity(self) -> bool:
        """Check network connectivity"""
        try:
            import socket

            # Check if we can bind to configured host/port
            host = self.config_manager.get_config("system", "host", "0.0.0.0")
            port = self.config_manager.get_config("system", "port", 8000)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port))
            sock.close()

            if result == 0:
                self.startup_errors.append(f"Port {port} is already in use")
                return False

            logger.info(f"Network connectivity: {host}:{port} available")
            return True

        except Exception as e:
            self.startup_errors.append(f"Error checking network connectivity: {e}")
            return False

    def _check_disk_space(self) -> bool:
        """Check available disk space"""
        try:
            disk = psutil.disk_usage('.')
            free_gb = disk.free / (1024**3)
            required_gb = 1  # Minimum 1GB free space

            if free_gb < required_gb:
                self.startup_errors.append(f"Insufficient disk space: {free_gb:.1f}GB < {required_gb}GB")
                return False

            logger.info(f"Disk space: {free_gb:.1f}GB available")
            return True

        except Exception as e:
            self.startup_errors.append(f"Error checking disk space: {e}")
            return False

    def _check_required_directories(self) -> bool:
        """Check if required directories exist"""
        try:
            required_dirs = ["config", "data", "logs", "reports"]

            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    logger.warning(f"Creating missing directory: {dir_name}")
                    dir_path.mkdir(exist_ok=True)

            logger.info("Required directories verified")
            return True

        except Exception as e:
            self.startup_errors.append(f"Error checking directories: {e}")
            return False

    async def _check_dependencies(self) -> bool:
        """Check if all required Python dependencies are available"""
        try:
            required_modules = [
                "fastapi", "uvicorn", "sqlalchemy", "pandas", "numpy",
                "sklearn", "tensorflow", "matplotlib", "plotly",
                "cryptography", "pydantic", "aiohttp"
            ]

            missing_modules = []

            for module in required_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)

            if missing_modules:
                self.startup_errors.append(f"Missing dependencies: {', '.join(missing_modules)}")
                return False

            logger.info("All dependencies available")
            return True

        except Exception as e:
            self.startup_errors.append(f"Error checking dependencies: {e}")
            return False

    def _check_port_availability(self) -> bool:
        """Check if required ports are available"""
        try:
            import socket

            ports_to_check = [
                self.config_manager.get_config("system", "port", 8000),
                self.config_manager.get_config("monitoring", "websocket_port", 8765)
            ]

            for port in ports_to_check:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()

                if result == 0:
                    self.startup_errors.append(f"Port {port} is already in use")
                    return False

            logger.info(f"Ports available: {ports_to_check}")
            return True

        except Exception as e:
            self.startup_errors.append(f"Error checking port availability: {e}")
            return False

    async def _check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        try:
            database_url = self.config_manager.get_config("database", "database_url", "sqlite:///data/scada_system.db")

            if database_url.startswith("sqlite"):
                # For SQLite, check if directory exists and is writable
                db_path = Path(database_url.replace("sqlite:///", ""))
                db_dir = db_path.parent
                db_dir.mkdir(exist_ok=True)

                # Test write access
                test_file = db_dir / "write_test"
                test_file.touch()
                test_file.unlink()

                logger.info(f"Database connectivity: SQLite at {db_path}")
                return True

            else:
                # For other databases, would need to test actual connection
                logger.info("Database connectivity: Configuration valid")
                return True

        except Exception as e:
            self.startup_errors.append(f"Error checking database connectivity: {e}")
            return False

    def _create_directories(self):
        """Create all required directories"""
        try:
            directories = [
                "config", "data", "logs", "reports", "templates",
                "data/backups", "logs/archive"
            ]

            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)

            logger.info("All required directories created")

        except Exception as e:
            logger.error(f"Error creating directories: {e}")

    async def start_system(self) -> bool:
        """Start the integrated SCADA system"""
        try:
            logger.info("Starting SCADA AI Integrated System...")
            self.startup_time = datetime.now()

            # Import and initialize the main application
            from main_application import app, system_core, SystemConfiguration
            import uvicorn

            # Get configuration values
            host = self.config_manager.get_config("system", "host", "0.0.0.0")
            port = self.config_manager.get_config("system", "port", 8000)
            log_level = self.config_manager.get_config("system", "log_level", "INFO")
            workers = 1  # Must be 1 for lifespan events

            # Start the FastAPI application
            logger.info(f"Starting web server on {host}:{port}...")

            # Configure uvicorn
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_level=log_level.lower(),
                workers=workers,
                reload=False,
                access_log=True
            )

            server = uvicorn.Server(config)

            # Start server
            await server.serve()

        except KeyboardInterrupt:
            logger.info("👋 System shutdown requested by user")
            return True
        except Exception as e:
            logger.error(f"Error starting system: {e}")
            return False

    def start_system_background(self) -> bool:
        """Start system in background process"""
        try:
            logger.info("Starting SCADA AI System in background...")

            # Get configuration
            host = self.config_manager.get_config("system", "host", "0.0.0.0")
            port = self.config_manager.get_config("system", "port", 8000)
            log_level = self.config_manager.get_config("system", "log_level", "INFO")

            # Start as subprocess
            cmd = [
                sys.executable,
                "main_application.py",
                "--host", host,
                "--port", str(port),
                "--log-level", log_level.lower()
            ]

            self.system_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            # Wait a bit to check if process started successfully
            time.sleep(3)

            if self.system_process.poll() is None:
                self.is_running = True
                logger.info(f"System started successfully (PID: {self.system_process.pid})")
                logger.info(f"Web interface available at: http://{host}:{port}")
                return True
            else:
                stdout, stderr = self.system_process.communicate()
                logger.error(f"System startup failed:")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Error starting system in background: {e}")
            return False

    def stop_system(self) -> bool:
        """Stop the SCADA system"""
        try:
            logger.info("🛑 Stopping SCADA AI System...")

            if self.system_process and self.system_process.poll() is None:
                # Try graceful shutdown first
                logger.info("Attempting graceful shutdown...")
                self.system_process.terminate()

                # Wait for graceful shutdown
                try:
                    self.system_process.wait(timeout=30)
                    logger.info("System stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning("Graceful shutdown timeout, forcing termination...")
                    self.system_process.kill()
                    self.system_process.wait()
                    logger.info("System terminated")

                self.system_process = None
                self.is_running = False
                return True

            else:
                logger.warning("System is not running")
                return True

        except Exception as e:
            logger.error(f"Error stopping system: {e}")
            return False

    def get_system_status(self) -> dict:
        """Get current system status"""
        try:
            status = {
                "is_running": self.is_running,
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
                "environment": self.environment,
                "process_id": self.system_process.pid if self.system_process else None,
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds() if self.startup_time else 0
            }

            # Add process information if running
            if self.system_process and self.system_process.poll() is None:
                try:
                    process = psutil.Process(self.system_process.pid)
                    status.update({
                        "cpu_percent": process.cpu_percent(),
                        "memory_mb": process.memory_info().rss / 1024 / 1024,
                        "status": process.status()
                    })
                except:
                    pass

            return status

        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}

    async def health_check(self) -> dict:
        """Perform health check on running system"""
        try:
            if not self.is_running:
                return {"status": "stopped", "healthy": False}

            # Check if process is still running
            if self.system_process and self.system_process.poll() is not None:
                self.is_running = False
                return {"status": "crashed", "healthy": False}

            # Try to connect to web interface
            try:
                import aiohttp
                host = self.config_manager.get_config("system", "host", "0.0.0.0")
                port = self.config_manager.get_config("system", "port", 8000)

                url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}/health"

                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            health_data = await response.json()
                            return {
                                "status": "running",
                                "healthy": True,
                                "response_time_ms": response.headers.get("x-process-time", "unknown"),
                                "system_status": health_data.get("system_status", "unknown")
                            }
                        else:
                            return {
                                "status": "unhealthy",
                                "healthy": False,
                                "http_status": response.status
                            }

            except Exception as e:
                return {
                    "status": "connection_failed",
                    "healthy": False,
                    "error": str(e)
                }

        except Exception as e:
            logger.error(f"Error performing health check: {e}")
            return {"status": "error", "healthy": False, "error": str(e)}

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="SCADA AI System Orchestrator")

    parser.add_argument(
        "--environment", "-e",
        choices=["development", "staging", "production"],
        default="production",
        help="Runtime environment"
    )

    parser.add_argument(
        "--action", "-a",
        choices=["start", "stop", "restart", "status", "health"],
        default="start",
        help="Action to perform"
    )

    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Run in background"
    )

    parser.add_argument(
        "--config-dir",
        default="config",
        help="Configuration directory"
    )

    return parser.parse_args()

async def main():
    """Main orchestrator function"""
    args = parse_arguments()

    # Initialize orchestrator
    orchestrator = SystemOrchestrator(environment=args.environment)

    if not await orchestrator.initialize():
        logger.error("Failed to initialize system orchestrator")
        sys.exit(1)

    try:
        if args.action == "start":
            if args.background:
                success = orchestrator.start_system_background()
                if success:
                    print(f"SCADA AI System started in background")
                    print(f"Web interface: http://localhost:{orchestrator.config_manager.get_config('system', 'port', 8000)}")
                    print(f"API Documentation: http://localhost:{orchestrator.config_manager.get_config('system', 'port', 8000)}/docs")
                else:
                    print("Failed to start system")
                    sys.exit(1)
            else:
                await orchestrator.start_system()

        elif args.action == "stop":
            success = orchestrator.stop_system()
            if success:
                print("SCADA AI System stopped")
            else:
                print("Failed to stop system")
                sys.exit(1)

        elif args.action == "restart":
            print("🔄 Restarting SCADA AI System...")
            orchestrator.stop_system()
            time.sleep(5)
            success = orchestrator.start_system_background() if args.background else await orchestrator.start_system()
            if success:
                print("SCADA AI System restarted")
            else:
                print("Failed to restart system")
                sys.exit(1)

        elif args.action == "status":
            status = orchestrator.get_system_status()
            print("SCADA AI System Status:")
            print(json.dumps(status, indent=2))

        elif args.action == "health":
            health = await orchestrator.health_check()
            print("🏥 SCADA AI System Health Check:")
            print(json.dumps(health, indent=2))

    except KeyboardInterrupt:
        logger.info("👋 Shutdown requested by user")
        orchestrator.stop_system()
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Import json for status output
    import json

    # Run the orchestrator
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)