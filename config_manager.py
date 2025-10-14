"""
Unified Configuration Management System for SCADA AI
Centralized configuration for all system modules
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import hashlib

logger = logging.getLogger(__name__)

class ConfigScope(Enum):
    """Configuration scope levels"""
    SYSTEM = "system"
    SECURITY = "security"
    PROTOCOLS = "protocols"
    MONITORING = "monitoring"
    ANALYTICS = "analytics"
    REPORTING = "reporting"
    COMPLIANCE = "compliance"
    INTEGRATION = "integration"
    PIPELINE = "pipeline"

@dataclass
class ConfigSchema:
    """Configuration schema definition"""
    key: str
    data_type: type
    required: bool = False
    default_value: Any = None
    description: str = ""
    valid_values: List[Any] = None
    sensitive: bool = False

class ConfigurationManager:
    """Centralized configuration management"""

    def __init__(self, config_dir: str = "config", environment: str = "production"):
        self.config_dir = Path(config_dir)
        self.environment = environment
        self.config_dir.mkdir(exist_ok=True)

        # Configuration storage
        self.configs = {}
        self.schemas = {}
        self.watchers = {}
        self.lock = threading.Lock()

        # Encryption for sensitive configs
        self._init_encryption()

        # Load configuration schemas
        self._init_schemas()

        # Load configurations
        self._load_all_configs()

    def _init_encryption(self):
        """Initialize encryption for sensitive configuration"""
        try:
            key_file = self.config_dir / ".encryption_key"
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                os.chmod(key_file, 0o600)  # Restrict permissions

            self.cipher_suite = Fernet(key)
            logger.info("Configuration encryption initialized")

        except Exception as e:
            logger.error(f"Error initializing encryption: {e}")
            self.cipher_suite = None

    def _init_schemas(self):
        """Initialize configuration schemas for all modules"""

        # System Configuration Schema
        system_schema = [
            ConfigSchema("environment", str, True, "production", "Runtime environment"),
            ConfigSchema("debug", bool, False, False, "Enable debug mode"),
            ConfigSchema("log_level", str, False, "INFO", "Logging level", ["DEBUG", "INFO", "WARNING", "ERROR"]),
            ConfigSchema("host", str, False, "0.0.0.0", "Server host address"),
            ConfigSchema("port", int, False, 8000, "Server port"),
            ConfigSchema("max_workers", int, False, 4, "Maximum worker threads"),
            ConfigSchema("timezone", str, False, "UTC", "System timezone")
        ]

        # Security Configuration Schema
        security_schema = [
            ConfigSchema("enable_security", bool, True, True, "Enable security framework"),
            ConfigSchema("secret_key", str, True, None, "JWT secret key", sensitive=True),
            ConfigSchema("jwt_expiry_hours", int, False, 8, "JWT token expiry hours"),
            ConfigSchema("password_min_length", int, False, 12, "Minimum password length"),
            ConfigSchema("max_login_attempts", int, False, 5, "Maximum login attempts"),
            ConfigSchema("session_timeout_minutes", int, False, 480, "Session timeout in minutes"),
            ConfigSchema("enable_2fa", bool, False, False, "Enable two-factor authentication"),
            ConfigSchema("password_complexity", bool, False, True, "Enforce password complexity")
        ]

        # Database Configuration Schema
        database_schema = [
            ConfigSchema("database_url", str, True, "sqlite:///data/scada_system.db", "Database connection URL", sensitive=True),
            ConfigSchema("pool_size", int, False, 20, "Connection pool size"),
            ConfigSchema("max_overflow", int, False, 0, "Maximum pool overflow"),
            ConfigSchema("pool_timeout", int, False, 30, "Pool timeout seconds"),
            ConfigSchema("enable_backup", bool, False, True, "Enable automatic backup"),
            ConfigSchema("backup_interval_hours", int, False, 24, "Backup interval hours"),
            ConfigSchema("retention_days", int, False, 365, "Data retention days")
        ]

        # Protocol Configuration Schema
        protocol_schema = [
            ConfigSchema("enable_modbus_tcp", bool, False, True, "Enable Modbus TCP protocol"),
            ConfigSchema("enable_modbus_rtu", bool, False, True, "Enable Modbus RTU protocol"),
            ConfigSchema("enable_dnp3", bool, False, True, "Enable DNP3 protocol"),
            ConfigSchema("enable_iec61850", bool, False, True, "Enable IEC 61850 protocol"),
            ConfigSchema("default_timeout", int, False, 10, "Default protocol timeout seconds"),
            ConfigSchema("max_retries", int, False, 3, "Maximum retry attempts"),
            ConfigSchema("connection_pool_size", int, False, 10, "Protocol connection pool size")
        ]

        # Monitoring Configuration Schema
        monitoring_schema = [
            ConfigSchema("enable_monitoring", bool, True, True, "Enable monitoring system"),
            ConfigSchema("default_scan_rate_ms", int, False, 1000, "Default scan rate milliseconds"),
            ConfigSchema("data_buffer_size", int, False, 10000, "Data buffer size"),
            ConfigSchema("enable_websocket", bool, False, True, "Enable WebSocket streaming"),
            ConfigSchema("websocket_port", int, False, 8765, "WebSocket server port"),
            ConfigSchema("max_concurrent_clients", int, False, 100, "Maximum concurrent WebSocket clients"),
            ConfigSchema("alert_cooldown_minutes", int, False, 5, "Alert cooldown period")
        ]

        # Analytics Configuration Schema
        analytics_schema = [
            ConfigSchema("enable_analytics", bool, False, True, "Enable ML analytics"),
            ConfigSchema("batch_size", int, False, 1000, "Analytics batch size"),
            ConfigSchema("model_update_interval_hours", int, False, 24, "Model update interval"),
            ConfigSchema("anomaly_detection_threshold", float, False, 0.1, "Anomaly detection threshold"),
            ConfigSchema("enable_predictive_maintenance", bool, False, True, "Enable predictive maintenance"),
            ConfigSchema("enable_process_optimization", bool, False, True, "Enable process optimization"),
            ConfigSchema("confidence_threshold", float, False, 0.8, "Minimum confidence threshold")
        ]

        # Reporting Configuration Schema
        reporting_schema = [
            ConfigSchema("enable_reporting", bool, False, True, "Enable reporting system"),
            ConfigSchema("default_format", str, False, "html", "Default report format", ["html", "pdf", "excel", "json"]),
            ConfigSchema("max_report_size_mb", int, False, 50, "Maximum report size MB"),
            ConfigSchema("enable_scheduled_reports", bool, False, True, "Enable scheduled reports"),
            ConfigSchema("report_retention_days", int, False, 90, "Report retention days"),
            ConfigSchema("template_directory", str, False, "templates", "Report template directory")
        ]

        # Compliance Configuration Schema
        compliance_schema = [
            ConfigSchema("enable_compliance", bool, False, True, "Enable compliance system"),
            ConfigSchema("audit_retention_years", int, False, 7, "Audit log retention years"),
            ConfigSchema("enable_iso27001", bool, False, True, "Enable ISO 27001 compliance"),
            ConfigSchema("enable_iec62443", bool, False, True, "Enable IEC 62443 compliance"),
            ConfigSchema("enable_nist_csf", bool, False, True, "Enable NIST CSF compliance"),
            ConfigSchema("auto_assessment_interval_days", int, False, 30, "Auto assessment interval"),
            ConfigSchema("require_digital_signatures", bool, False, True, "Require digital signatures")
        ]

        # Integration Configuration Schema
        integration_schema = [
            ConfigSchema("enable_integration", bool, False, True, "Enable enterprise integration"),
            ConfigSchema("enable_erp_integration", bool, False, False, "Enable ERP integration"),
            ConfigSchema("enable_mes_integration", bool, False, False, "Enable MES integration"),
            ConfigSchema("enable_cloud_integration", bool, False, False, "Enable cloud integration"),
            ConfigSchema("enable_historian_integration", bool, False, False, "Enable historian integration"),
            ConfigSchema("sync_interval_minutes", int, False, 5, "Integration sync interval"),
            ConfigSchema("max_retry_attempts", int, False, 3, "Maximum retry attempts")
        ]

        # Pipeline Configuration Schema
        pipeline_schema = [
            ConfigSchema("ingestion_queue_size", int, False, 50000, "Ingestion queue size"),
            ConfigSchema("processing_queue_size", int, False, 10000, "Processing queue size"),
            ConfigSchema("distribution_queue_size", int, False, 5000, "Distribution queue size"),
            ConfigSchema("worker_threads", int, False, 4, "Number of worker threads"),
            ConfigSchema("batch_processing_size", int, False, 100, "Batch processing size"),
            ConfigSchema("processing_timeout_seconds", int, False, 60, "Processing timeout seconds")
        ]

        # Register all schemas
        self.schemas[ConfigScope.SYSTEM] = {schema.key: schema for schema in system_schema}
        self.schemas["security"] = {schema.key: schema for schema in security_schema}
        self.schemas["database"] = {schema.key: schema for schema in database_schema}
        self.schemas[ConfigScope.PROTOCOLS] = {schema.key: schema for schema in protocol_schema}
        self.schemas[ConfigScope.MONITORING] = {schema.key: schema for schema in monitoring_schema}
        self.schemas[ConfigScope.ANALYTICS] = {schema.key: schema for schema in analytics_schema}
        self.schemas[ConfigScope.REPORTING] = {schema.key: schema for schema in reporting_schema}
        self.schemas[ConfigScope.COMPLIANCE] = {schema.key: schema for schema in compliance_schema}
        self.schemas[ConfigScope.INTEGRATION] = {schema.key: schema for schema in integration_schema}
        self.schemas[ConfigScope.PIPELINE] = {schema.key: schema for schema in pipeline_schema}

    def _load_all_configs(self):
        """Load all configuration files"""
        try:
            # Load base configuration
            base_config_file = self.config_dir / "base.yaml"
            if not base_config_file.exists():
                self._create_default_config_files()

            # Load environment-specific configuration
            env_config_file = self.config_dir / f"{self.environment}.yaml"
            if env_config_file.exists():
                self._load_config_file(env_config_file)
            else:
                logger.warning(f"Environment config file not found: {env_config_file}")

            # Load base configuration (if exists)
            if base_config_file.exists():
                base_configs = self._load_config_file(base_config_file)
                # Merge with existing configs (environment takes precedence)
                for scope, config in base_configs.items():
                    if scope not in self.configs:
                        self.configs[scope] = {}
                    for key, value in config.items():
                        if key not in self.configs[scope]:
                            self.configs[scope][key] = value

            # Apply defaults for missing configurations
            self._apply_default_values()

            # Validate all configurations
            self._validate_all_configs()

            logger.info(f"Configuration loaded successfully for environment: {self.environment}")

        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            raise

    def _create_default_config_files(self):
        """Create default configuration files"""
        try:
            # Create base configuration
            base_config = {
                "system": {
                    "environment": "production",
                    "debug": False,
                    "log_level": "INFO",
                    "host": "0.0.0.0",
                    "port": 8000,
                    "max_workers": 4,
                    "timezone": "UTC"
                },
                "security": {
                    "enable_security": True,
                    "jwt_expiry_hours": 8,
                    "password_min_length": 12,
                    "max_login_attempts": 5,
                    "session_timeout_minutes": 480,
                    "enable_2fa": False,
                    "password_complexity": True
                },
                "database": {
                    "database_url": "sqlite:///data/scada_system.db",
                    "pool_size": 20,
                    "max_overflow": 0,
                    "pool_timeout": 30,
                    "enable_backup": True,
                    "backup_interval_hours": 24,
                    "retention_days": 365
                },
                "protocols": {
                    "enable_modbus_tcp": True,
                    "enable_modbus_rtu": True,
                    "enable_dnp3": True,
                    "enable_iec61850": True,
                    "default_timeout": 10,
                    "max_retries": 3,
                    "connection_pool_size": 10
                },
                "monitoring": {
                    "enable_monitoring": True,
                    "default_scan_rate_ms": 1000,
                    "data_buffer_size": 10000,
                    "enable_websocket": True,
                    "websocket_port": 8765,
                    "max_concurrent_clients": 100,
                    "alert_cooldown_minutes": 5
                },
                "analytics": {
                    "enable_analytics": True,
                    "batch_size": 1000,
                    "model_update_interval_hours": 24,
                    "anomaly_detection_threshold": 0.1,
                    "enable_predictive_maintenance": True,
                    "enable_process_optimization": True,
                    "confidence_threshold": 0.8
                },
                "reporting": {
                    "enable_reporting": True,
                    "default_format": "html",
                    "max_report_size_mb": 50,
                    "enable_scheduled_reports": True,
                    "report_retention_days": 90,
                    "template_directory": "templates"
                },
                "compliance": {
                    "enable_compliance": True,
                    "audit_retention_years": 7,
                    "enable_iso27001": True,
                    "enable_iec62443": True,
                    "enable_nist_csf": True,
                    "auto_assessment_interval_days": 30,
                    "require_digital_signatures": True
                },
                "integration": {
                    "enable_integration": True,
                    "enable_erp_integration": False,
                    "enable_mes_integration": False,
                    "enable_cloud_integration": False,
                    "enable_historian_integration": False,
                    "sync_interval_minutes": 5,
                    "max_retry_attempts": 3
                },
                "pipeline": {
                    "ingestion_queue_size": 50000,
                    "processing_queue_size": 10000,
                    "distribution_queue_size": 5000,
                    "worker_threads": 4,
                    "batch_processing_size": 100,
                    "processing_timeout_seconds": 60
                }
            }

            # Save base configuration
            base_config_file = self.config_dir / "base.yaml"
            with open(base_config_file, 'w') as f:
                yaml.dump(base_config, f, default_flow_style=False, indent=2)

            # Create environment-specific configuration
            env_config = {
                "system": {
                    "environment": self.environment,
                    "debug": self.environment != "production"
                }
            }

            if self.environment == "development":
                env_config["system"]["log_level"] = "DEBUG"
                env_config["system"]["port"] = 8001
                env_config["database"] = {
                    "database_url": "sqlite:///data/scada_dev.db"
                }

            env_config_file = self.config_dir / f"{self.environment}.yaml"
            with open(env_config_file, 'w') as f:
                yaml.dump(env_config, f, default_flow_style=False, indent=2)

            logger.info("Default configuration files created")

        except Exception as e:
            logger.error(f"Error creating default config files: {e}")
            raise

    def _load_config_file(self, config_file: Path) -> Dict[str, Dict[str, Any]]:
        """Load configuration from file"""
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() == '.yaml' or config_file.suffix.lower() == '.yml':
                    config_data = yaml.safe_load(f)
                elif config_file.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_file.suffix}")

            # Merge with existing configurations
            for scope, config in config_data.items():
                if scope not in self.configs:
                    self.configs[scope] = {}
                self.configs[scope].update(config)

            return config_data

        except Exception as e:
            logger.error(f"Error loading config file {config_file}: {e}")
            raise

    def _apply_default_values(self):
        """Apply default values for missing configuration keys"""
        try:
            for scope_key, schemas in self.schemas.items():
                scope = scope_key.value if isinstance(scope_key, ConfigScope) else scope_key

                if scope not in self.configs:
                    self.configs[scope] = {}

                for key, schema in schemas.items():
                    if key not in self.configs[scope] and schema.default_value is not None:
                        self.configs[scope][key] = schema.default_value

        except Exception as e:
            logger.error(f"Error applying default values: {e}")

    def _validate_all_configs(self):
        """Validate all configurations against schemas"""
        try:
            errors = []

            for scope_key, schemas in self.schemas.items():
                scope = scope_key.value if isinstance(scope_key, ConfigScope) else scope_key

                if scope not in self.configs:
                    continue

                for key, schema in schemas.items():
                    if schema.required and key not in self.configs[scope]:
                        errors.append(f"Required config missing: {scope}.{key}")
                        continue

                    if key in self.configs[scope]:
                        value = self.configs[scope][key]

                        # Type validation
                        if not isinstance(value, schema.data_type):
                            try:
                                # Try to convert
                                self.configs[scope][key] = schema.data_type(value)
                            except (ValueError, TypeError):
                                errors.append(f"Invalid type for {scope}.{key}: expected {schema.data_type.__name__}")

                        # Valid values validation
                        if schema.valid_values and value not in schema.valid_values:
                            errors.append(f"Invalid value for {scope}.{key}: {value}. Valid values: {schema.valid_values}")

            if errors:
                logger.error("Configuration validation errors:")
                for error in errors:
                    logger.error(f"  - {error}")
                raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

            logger.info("Configuration validation passed")

        except Exception as e:
            logger.error(f"Error validating configurations: {e}")
            raise

    def get_config(self, scope: Union[str, ConfigScope], key: str, default: Any = None) -> Any:
        """Get configuration value"""
        try:
            scope_str = scope.value if isinstance(scope, ConfigScope) else scope

            with self.lock:
                if scope_str in self.configs and key in self.configs[scope_str]:
                    value = self.configs[scope_str][key]

                    # Decrypt if sensitive
                    if self._is_sensitive_config(scope_str, key) and isinstance(value, str):
                        try:
                            if self.cipher_suite:
                                # Check if it's encrypted (base64 encoded)
                                try:
                                    encrypted_data = base64.b64decode(value)
                                    decrypted_value = self.cipher_suite.decrypt(encrypted_data).decode()
                                    return decrypted_value
                                except:
                                    # Not encrypted, return as is
                                    return value
                            else:
                                return value
                        except Exception as e:
                            logger.warning(f"Error decrypting config {scope_str}.{key}: {e}")
                            return value

                    return value
                else:
                    return default

        except Exception as e:
            logger.error(f"Error getting config {scope}.{key}: {e}")
            return default

    def set_config(self, scope: Union[str, ConfigScope], key: str, value: Any, persist: bool = True) -> bool:
        """Set configuration value"""
        try:
            scope_str = scope.value if isinstance(scope, ConfigScope) else scope

            with self.lock:
                if scope_str not in self.configs:
                    self.configs[scope_str] = {}

                # Encrypt if sensitive
                if self._is_sensitive_config(scope_str, key) and isinstance(value, str):
                    if self.cipher_suite:
                        encrypted_data = self.cipher_suite.encrypt(value.encode())
                        value = base64.b64encode(encrypted_data).decode()

                self.configs[scope_str][key] = value

                # Persist to file if requested
                if persist:
                    self._save_config_file()

                # Notify watchers
                self._notify_watchers(scope_str, key, value)

            logger.debug(f"Configuration updated: {scope_str}.{key}")
            return True

        except Exception as e:
            logger.error(f"Error setting config {scope}.{key}: {e}")
            return False

    def _is_sensitive_config(self, scope: str, key: str) -> bool:
        """Check if configuration is marked as sensitive"""
        try:
            scope_schemas = self.schemas.get(scope, {})
            if isinstance(scope_schemas, dict):
                schema = scope_schemas.get(key)
                return schema.sensitive if schema else False
            return False
        except:
            return False

    def _save_config_file(self):
        """Save configuration to environment-specific file"""
        try:
            env_config_file = self.config_dir / f"{self.environment}.yaml"
            with open(env_config_file, 'w') as f:
                yaml.dump(self.configs, f, default_flow_style=False, indent=2)

        except Exception as e:
            logger.error(f"Error saving config file: {e}")

    def watch_config(self, scope: Union[str, ConfigScope], key: str, callback: callable):
        """Watch for configuration changes"""
        try:
            scope_str = scope.value if isinstance(scope, ConfigScope) else scope
            watch_key = f"{scope_str}.{key}"

            if watch_key not in self.watchers:
                self.watchers[watch_key] = []

            self.watchers[watch_key].append(callback)
            logger.debug(f"Watcher added for {watch_key}")

        except Exception as e:
            logger.error(f"Error adding config watcher: {e}")

    def _notify_watchers(self, scope: str, key: str, value: Any):
        """Notify configuration watchers"""
        try:
            watch_key = f"{scope}.{key}"
            if watch_key in self.watchers:
                for callback in self.watchers[watch_key]:
                    try:
                        callback(scope, key, value)
                    except Exception as e:
                        logger.error(f"Error in config watcher callback: {e}")

        except Exception as e:
            logger.error(f"Error notifying watchers: {e}")

    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all configurations (excluding sensitive data)"""
        try:
            filtered_configs = {}

            with self.lock:
                for scope, configs in self.configs.items():
                    filtered_configs[scope] = {}
                    for key, value in configs.items():
                        if not self._is_sensitive_config(scope, key):
                            filtered_configs[scope][key] = value
                        else:
                            filtered_configs[scope][key] = "[ENCRYPTED]"

            return filtered_configs

        except Exception as e:
            logger.error(f"Error getting all configs: {e}")
            return {}

    def export_config(self, output_file: str, include_sensitive: bool = False):
        """Export configuration to file"""
        try:
            if include_sensitive:
                config_data = dict(self.configs)
            else:
                config_data = self.get_all_configs()

            output_path = Path(output_file)

            with open(output_path, 'w') as f:
                if output_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif output_path.suffix.lower() == '.json':
                    json.dump(config_data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported export format: {output_path.suffix}")

            logger.info(f"Configuration exported to: {output_file}")

        except Exception as e:
            logger.error(f"Error exporting config: {e}")
            raise

    def get_config_schema(self) -> Dict[str, Dict[str, Dict]]:
        """Get configuration schema information"""
        try:
            schema_info = {}

            for scope_key, schemas in self.schemas.items():
                scope = scope_key.value if isinstance(scope_key, ConfigScope) else scope_key
                schema_info[scope] = {}

                for key, schema in schemas.items():
                    schema_info[scope][key] = {
                        "type": schema.data_type.__name__,
                        "required": schema.required,
                        "default": schema.default_value,
                        "description": schema.description,
                        "valid_values": schema.valid_values,
                        "sensitive": schema.sensitive
                    }

            return schema_info

        except Exception as e:
            logger.error(f"Error getting config schema: {e}")
            return {}

    def validate_config_value(self, scope: Union[str, ConfigScope], key: str, value: Any) -> bool:
        """Validate a specific configuration value"""
        try:
            scope_str = scope.value if isinstance(scope, ConfigScope) else scope

            if scope_str not in self.schemas:
                return False

            schema = self.schemas[scope_str].get(key)
            if not schema:
                return False

            # Type validation
            if not isinstance(value, schema.data_type):
                try:
                    schema.data_type(value)  # Try to convert
                except (ValueError, TypeError):
                    return False

            # Valid values validation
            if schema.valid_values and value not in schema.valid_values:
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating config value: {e}")
            return False

# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None

def get_config_manager(config_dir: str = "config", environment: str = "production") -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigurationManager(config_dir, environment)

    return _config_manager

def get_config(scope: Union[str, ConfigScope], key: str, default: Any = None) -> Any:
    """Convenience function to get configuration value"""
    return get_config_manager().get_config(scope, key, default)

def set_config(scope: Union[str, ConfigScope], key: str, value: Any, persist: bool = True) -> bool:
    """Convenience function to set configuration value"""
    return get_config_manager().set_config(scope, key, value, persist)

# Example usage and testing
if __name__ == "__main__":
    # Initialize configuration manager
    config_manager = ConfigurationManager(environment="development")

    # Test getting configurations
    print("System Configuration:")
    print(f"Environment: {config_manager.get_config('system', 'environment')}")
    print(f"Debug: {config_manager.get_config('system', 'debug')}")
    print(f"Port: {config_manager.get_config('system', 'port')}")

    print("\nSecurity Configuration:")
    print(f"Enable Security: {config_manager.get_config('security', 'enable_security')}")
    print(f"JWT Expiry: {config_manager.get_config('security', 'jwt_expiry_hours')}")

    # Test setting configuration
    config_manager.set_config('system', 'max_workers', 8)
    print(f"\nUpdated Max Workers: {config_manager.get_config('system', 'max_workers')}")

    # Test sensitive configuration
    config_manager.set_config('security', 'secret_key', 'super-secret-key-123')
    secret = config_manager.get_config('security', 'secret_key')
    print(f"Secret Key Retrieved: {secret}")

    # Export configuration
    config_manager.export_config("config_export.yaml")
    print("Configuration exported successfully")

    # Get schema information
    schema = config_manager.get_config_schema()
    print(f"\nConfiguration Schema Keys: {list(schema.keys())}")