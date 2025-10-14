# Enterprise SCADA AI System - Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying the Enterprise SCADA AI System in production environments, including high-availability configurations, security hardening, and enterprise integration.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Pre-deployment Checklist](#pre-deployment-checklist)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Security Configuration](#security-configuration)
6. [High Availability Setup](#high-availability-setup)
7. [Enterprise Integration](#enterprise-integration)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Hardware Requirements
- **CPU**: 8 cores, 3.0 GHz (Intel Xeon or AMD EPYC recommended)
- **Memory**: 32 GB RAM (64 GB recommended for ML workloads)
- **Storage**: 1 TB NVMe SSD (for OS, applications, and local data)
- **Network**: Gigabit Ethernet with redundancy
- **GPU**: NVIDIA Tesla/RTX series for ML acceleration (optional)

### Operating System Support
- **Primary**: Ubuntu 20.04 LTS or CentOS 8
- **Alternative**: Windows Server 2019/2022, Red Hat Enterprise Linux 8
- **Container**: Docker 20.10+ with Kubernetes 1.21+

### Network Requirements
- **Internal Network**: Isolated VLAN for SCADA communications
- **Management Network**: Separate network for administration
- **DMZ**: For external integrations and web interfaces
- **Bandwidth**: Minimum 100 Mbps for real-time operations

## Pre-deployment Checklist

### Infrastructure Preparation
- [ ] Verify hardware meets requirements
- [ ] Configure network segmentation
- [ ] Set up firewall rules
- [ ] Install operating system with latest security patches
- [ ] Configure NTP for time synchronization
- [ ] Set up DNS resolution
- [ ] Configure backup storage
- [ ] Establish monitoring infrastructure

### Security Prerequisites
- [ ] Certificate Authority (CA) setup
- [ ] SSL/TLS certificates obtained
- [ ] Security scanning completed
- [ ] Vulnerability assessment performed
- [ ] Access control policies defined
- [ ] Incident response procedures established

### Integration Requirements
- [ ] ERP/MES system connectivity verified
- [ ] Database servers configured
- [ ] Message queue infrastructure ready
- [ ] Cloud platform accounts configured
- [ ] Third-party API credentials obtained

## Installation

### Method 1: Docker Container Deployment (Recommended)

1. **Install Docker and Docker Compose**
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Create Directory Structure**
```bash
mkdir -p /opt/scada-ai/{config,data,logs,certs,backups}
cd /opt/scada-ai
```

3. **Create Docker Compose Configuration**
```yaml
# docker-compose.yml
version: '3.8'

services:
  scada-ai-app:
    image: scada-ai:latest
    container_name: scada-ai-main
    ports:
      - "8000:8000"
      - "8765:8765"  # WebSocket
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
      - ./certs:/app/certs
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/scada_ai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    networks:
      - scada-network

  postgres:
    image: postgres:14
    container_name: scada-postgres
    environment:
      - POSTGRES_DB=scada_ai
      - POSTGRES_USER=scada_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - scada-network

  redis:
    image: redis:7-alpine
    container_name: scada-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - scada-network

  nginx:
    image: nginx:alpine
    container_name: scada-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - scada-ai-app
    restart: unless-stopped
    networks:
      - scada-network

volumes:
  postgres_data:
  redis_data:

networks:
  scada-network:
    driver: bridge
```

4. **Build and Deploy**
```bash
docker-compose up -d
docker-compose logs -f scada-ai-app
```

### Method 2: Native Installation

1. **Install Python and Dependencies**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev
sudo apt install postgresql postgresql-contrib redis-server nginx

# Create virtual environment
python3.9 -m venv /opt/scada-ai/venv
source /opt/scada-ai/venv/bin/activate

# Install Python packages
pip install -r requirements_production.txt
```

2. **Configure System Services**
```bash
# Create systemd service file
sudo tee /etc/systemd/system/scada-ai.service > /dev/null <<EOF
[Unit]
Description=SCADA AI System
After=network.target

[Service]
Type=simple
User=scada
WorkingDirectory=/opt/scada-ai
Environment=PATH=/opt/scada-ai/venv/bin
ExecStart=/opt/scada-ai/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable scada-ai
sudo systemctl start scada-ai
```

## Configuration

### Main Configuration File
Create `/opt/scada-ai/config/production.yaml`:

```yaml
# production.yaml
system:
  environment: production
  debug: false
  log_level: INFO
  max_workers: 8

database:
  url: postgresql://scada_user:secure_password@localhost:5432/scada_ai
  pool_size: 20
  max_overflow: 0

redis:
  url: redis://localhost:6379/0
  max_connections: 100

security:
  secret_key: "your-secret-key-here"
  jwt_expiry: 3600
  password_min_length: 12
  max_login_attempts: 5

protocols:
  modbus_tcp:
    enabled: true
    timeout: 10
    retries: 3
  dnp3:
    enabled: true
    timeout: 15
  iec61850:
    enabled: true

monitoring:
  scan_rate_ms: 1000
  buffer_size: 10000
  websocket_port: 8765

analytics:
  ml_enabled: true
  batch_size: 1000
  model_update_interval: 3600

alerts:
  email_enabled: true
  sms_enabled: true
  webhook_enabled: true
  max_alerts_per_hour: 100

compliance:
  audit_enabled: true
  encryption_required: true
  data_retention_days: 2555  # 7 years

integration:
  erp_enabled: true
  mes_enabled: true
  cloud_enabled: true
  historian_enabled: true
```

### Environment Variables
Create `/opt/scada-ai/.env`:

```bash
# Environment Configuration
ENVIRONMENT=production
DATABASE_URL=postgresql://scada_user:secure_password@localhost:5432/scada_ai
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-very-secure-secret-key-here

# Security
SSL_CERT_PATH=/opt/scada-ai/certs/server.crt
SSL_KEY_PATH=/opt/scada-ai/certs/server.key

# SMTP Configuration
SMTP_SERVER=smtp.company.com
SMTP_PORT=587
SMTP_USERNAME=scada@company.com
SMTP_PASSWORD=smtp_password

# Cloud Integration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AZURE_CONNECTION_STRING=your_azure_connection_string

# External Systems
ERP_API_URL=https://erp.company.com/api
ERP_USERNAME=scada_user
ERP_PASSWORD=erp_password
```

## Security Configuration

### SSL/TLS Setup
1. **Generate SSL Certificates**
```bash
# Create private key
openssl genrsa -out /opt/scada-ai/certs/server.key 2048

# Create certificate signing request
openssl req -new -key /opt/scada-ai/certs/server.key -out /opt/scada-ai/certs/server.csr

# Generate self-signed certificate (use CA-signed in production)
openssl x509 -req -days 365 -in /opt/scada-ai/certs/server.csr -signkey /opt/scada-ai/certs/server.key -out /opt/scada-ai/certs/server.crt

# Set proper permissions
chmod 600 /opt/scada-ai/certs/server.key
chmod 644 /opt/scada-ai/certs/server.crt
```

### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port as needed)
sudo ufw allow 22/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow SCADA protocols (restrict by IP)
sudo ufw allow from 192.168.1.0/24 to any port 502  # Modbus TCP
sudo ufw allow from 192.168.1.0/24 to any port 102  # IEC 61850

# Enable firewall
sudo ufw enable
```

### Database Security
```sql
-- PostgreSQL security configuration
-- Create dedicated user
CREATE USER scada_user WITH PASSWORD 'secure_password';
CREATE DATABASE scada_ai OWNER scada_user;

-- Grant minimal privileges
GRANT CONNECT ON DATABASE scada_ai TO scada_user;
GRANT USAGE ON SCHEMA public TO scada_user;
GRANT CREATE ON SCHEMA public TO scada_user;

-- Configure pg_hba.conf for secure connections
-- Add to /etc/postgresql/14/main/pg_hba.conf:
-- hostssl scada_ai scada_user 192.168.1.0/24 md5
```

## High Availability Setup

### Load Balancer Configuration (Nginx)
```nginx
# /etc/nginx/nginx.conf
upstream scada_backend {
    server 192.168.1.10:8000 max_fails=3 fail_timeout=30s;
    server 192.168.1.11:8000 max_fails=3 fail_timeout=30s;
    server 192.168.1.12:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name scada.company.com;

    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://scada_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
    }
}
```

### Database Clustering (PostgreSQL)
```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  postgres-primary:
    image: postgres:14
    environment:
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=repl_password
    volumes:
      - primary_data:/var/lib/postgresql/data
    command: |
      bash -c "
      echo 'wal_level = replica' >> /var/lib/postgresql/data/postgresql.conf
      echo 'max_wal_senders = 3' >> /var/lib/postgresql/data/postgresql.conf
      echo 'wal_keep_segments = 64' >> /var/lib/postgresql/data/postgresql.conf
      postgres
      "

  postgres-standby:
    image: postgres:14
    environment:
      - PGUSER=postgres
      - POSTGRES_PASSWORD=postgres
    command: |
      bash -c "
      until pg_basebackup --host=postgres-primary --username=replicator --no-password --pgdata=/var/lib/postgresql/data --wal-method=stream
      do
        echo 'Waiting for primary to be available...'
        sleep 1s
      done
      echo 'standby_mode = on' >> /var/lib/postgresql/data/recovery.conf
      echo 'primary_conninfo = host=postgres-primary port=5432 user=replicator' >> /var/lib/postgresql/data/recovery.conf
      postgres
      "
    depends_on:
      - postgres-primary
```

## Enterprise Integration

### ERP Integration Setup
```python
# config/erp_integration.py
ERP_CONFIG = {
    "sap": {
        "endpoint": "https://sap.company.com:8000/sap/bc/rest/",
        "username": "SCADA_USER",
        "password": "sap_password",
        "client": "100",
        "language": "EN"
    },
    "oracle": {
        "endpoint": "https://oracle.company.com/ords/api/",
        "username": "scada_user",
        "password": "oracle_password"
    }
}

# Data mapping configuration
DATA_MAPPING = {
    "production_data": {
        "batch_id": "AUFNR",
        "quantity": "GAMNG",
        "start_time": "GSTRP",
        "end_time": "GLTRP"
    }
}
```

### Message Queue Setup (RabbitMQ)
```yaml
# rabbitmq.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rabbitmq
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: rabbitmq
        image: rabbitmq:3.9-management
        ports:
        - containerPort: 5672
        - containerPort: 15672
        env:
        - name: RABBITMQ_CLUSTER_NAME
          value: "scada-cluster"
        volumeMounts:
        - name: rabbitmq-data
          mountPath: /var/lib/rabbitmq
```

## Monitoring & Logging

### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'scada-ai'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
```

### Grafana Dashboards
```json
{
  "dashboard": {
    "title": "SCADA AI System",
    "panels": [
      {
        "title": "System Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Request Rate"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "stat",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "Active Connections"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation (ELK Stack)
```yaml
# logstash.conf
input {
  file {
    path => "/opt/scada-ai/logs/*.log"
    start_position => "beginning"
  }
}

filter {
  if [path] =~ "access" {
    mutate { replace => { "type" => "nginx_access" } }
    grok {
      match => { "message" => "%{NGINXACCESS}" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "scada-ai-%{+YYYY.MM.dd}"
  }
}
```

## Backup & Recovery

### Database Backup Strategy
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/opt/scada-ai/backups"
DB_NAME="scada_ai"
DB_USER="scada_user"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Full backup
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/full_backup_$TIMESTAMP.sql.gz

# Differential backup (WAL archiving)
rsync -av /var/lib/postgresql/14/main/pg_wal/ $BACKUP_DIR/wal_archive/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "full_backup_*.sql.gz" -mtime +30 -delete

# Upload to cloud storage
aws s3 sync $BACKUP_DIR s3://company-scada-backups/
```

### Recovery Procedures
```bash
#!/bin/bash
# restore_database.sh

BACKUP_FILE=$1
DB_NAME="scada_ai"
DB_USER="scada_user"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop applications
systemctl stop scada-ai

# Drop and recreate database
dropdb -U $DB_USER $DB_NAME
createdb -U $DB_USER $DB_NAME

# Restore from backup
gunzip -c $BACKUP_FILE | psql -U $DB_USER -d $DB_NAME

# Start applications
systemctl start scada-ai

echo "Database restored successfully"
```

## Performance Optimization

### Database Optimization
```sql
-- PostgreSQL performance tuning
-- postgresql.conf settings

shared_buffers = 8GB                    # 25% of total RAM
effective_cache_size = 24GB             # 75% of total RAM
maintenance_work_mem = 2GB
work_mem = 256MB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
wal_buffers = 64MB
checkpoint_completion_target = 0.9
random_page_cost = 1.1                  # For SSD storage

-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_monitoring_data_timestamp ON monitoring_data(timestamp);
CREATE INDEX CONCURRENTLY idx_monitoring_data_point_id ON monitoring_data(point_id);
CREATE INDEX CONCURRENTLY idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX CONCURRENTLY idx_audit_events_user ON audit_events(user_id);
```

### Application Performance Tuning
```python
# config/performance.py
PERFORMANCE_CONFIG = {
    "workers": 8,                       # Number of worker processes
    "worker_class": "uvicorn.workers.UvicornWorker",
    "worker_connections": 1000,
    "max_requests": 10000,
    "max_requests_jitter": 1000,
    "preload_app": True,
    "keepalive": 5,

    # Database connection pool
    "db_pool_size": 20,
    "db_max_overflow": 0,
    "db_pool_timeout": 30,

    # Cache settings
    "redis_max_connections": 100,
    "cache_ttl": 300,

    # ML model settings
    "batch_inference_size": 1000,
    "model_cache_size": 5,

    # Real-time data buffer
    "data_buffer_size": 10000,
    "scan_rate_ms": 1000
}
```

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: High CPU Usage
```bash
# Check process utilization
top -p $(pgrep -f scada-ai)

# Check system resources
iostat -x 1 10
vmstat 1 10

# Optimize Python process
# Add to systemd service file:
Environment="PYTHONOPTIMIZE=1"
Environment="PYTHONUNBUFFERED=1"
```

#### Issue 2: Database Connection Issues
```bash
# Check PostgreSQL status
systemctl status postgresql
pg_isready -h localhost -p 5432

# Check connections
psql -U scada_user -d scada_ai -c "SELECT count(*) FROM pg_stat_activity;"

# Optimize connections
# Edit postgresql.conf:
max_connections = 200
```

#### Issue 3: Memory Leaks
```bash
# Monitor memory usage
ps aux | grep scada-ai
free -h

# Enable memory profiling
pip install memory-profiler
python -m memory_profiler main.py
```

### Log Analysis
```bash
# Check application logs
tail -f /opt/scada-ai/logs/application.log

# Search for errors
grep -i error /opt/scada-ai/logs/*.log

# Analyze performance
awk '/Processing time/ { sum += $NF; count++ } END { print "Average:", sum/count }' /opt/scada-ai/logs/performance.log
```

### Health Check Endpoints
```python
# Health check implementation
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database_connection(),
        "redis": await check_redis_connection(),
        "disk_space": check_disk_space(),
        "memory": check_memory_usage()
    }

    healthy = all(checks.values())
    status_code = 200 if healthy else 503

    return JSONResponse(
        content={
            "status": "healthy" if healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        },
        status_code=status_code
    )
```

## Maintenance Procedures

### Routine Maintenance Tasks
```bash
#!/bin/bash
# maintenance.sh - Run weekly

# 1. Update system packages
apt update && apt upgrade -y

# 2. Clean up logs
find /opt/scada-ai/logs -name "*.log" -mtime +7 -exec gzip {} \;
find /opt/scada-ai/logs -name "*.log.gz" -mtime +30 -delete

# 3. Vacuum database
psql -U scada_user -d scada_ai -c "VACUUM ANALYZE;"

# 4. Clear Redis cache
redis-cli FLUSHDB

# 5. Check disk usage
df -h

# 6. Restart services if needed
systemctl restart scada-ai
```

### Security Updates
```bash
#!/bin/bash
# security_update.sh

# Check for security updates
apt list --upgradable | grep -i security

# Update Python packages
pip list --outdated
pip install --upgrade -r requirements_production.txt

# Rotate logs
logrotate -f /etc/logrotate.d/scada-ai

# Update SSL certificates if needed
certbot renew --quiet
```

## Support and Documentation

### Contact Information
- **Technical Support**: support@company.com
- **Emergency Hotline**: +1-800-SCADA-01
- **Documentation**: https://docs.company.com/scada-ai

### Additional Resources
- System Architecture Documentation
- API Reference Guide
- Compliance Certification Documents
- Vendor Support Contacts
- Training Materials

---

**Document Version**: 1.0
**Last Updated**: 2024-01-15
**Next Review**: 2024-07-15