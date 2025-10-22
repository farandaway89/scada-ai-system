# SCADA AI System - Enterprise Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/config /app/reports /app/templates

# Copy requirements file
COPY requirements_production.txt requirements.txt

# Install Python dependencies in stages to avoid memory issues
# Increase timeout for slow network connections
# Stage 1: Core web framework
RUN pip install --no-cache-dir --default-timeout=300 \
    fastapi>=0.75.0 \
    uvicorn[standard]>=0.17.0 \
    pydantic>=1.9.0 \
    python-multipart>=0.0.5 \
    jinja2>=3.0.0

# Stage 2: Database and authentication
RUN pip install --no-cache-dir --default-timeout=300 \
    sqlalchemy>=1.4.0 \
    alembic>=1.7.0 \
    redis>=4.0.0 \
    psycopg2-binary>=2.9.0 \
    mysql-connector-python>=8.0.0 \
    python-jose[cryptography]>=3.3.0 \
    passlib[bcrypt]>=1.7.0 \
    cryptography>=36.0.0 \
    bcrypt>=3.2.0

# Stage 3: Basic data processing
RUN pip install --no-cache-dir --default-timeout=300 \
    pandas>=1.3.0 \
    numpy>=1.21.0 \
    joblib>=1.1.0 \
    python-dateutil>=2.8.0 \
    pytz>=2021.3

# Stage 4: Machine Learning (large packages)
RUN pip install --no-cache-dir --default-timeout=300 \
    scikit-learn>=1.0.0 \
    xgboost>=1.5.0 \
    lightgbm>=3.3.0

# Stage 5: TensorFlow (largest package)
RUN pip install --no-cache-dir --default-timeout=300 \
    tensorflow>=2.8.0 \
    keras>=2.8.0

# Stage 6: Visualization
RUN pip install --no-cache-dir --default-timeout=300 \
    matplotlib>=3.5.0 \
    seaborn>=0.11.0 \
    plotly>=5.5.0 \
    bokeh>=2.4.0

# Stage 7: Industrial protocols
RUN pip install --no-cache-dir --default-timeout=300 \
    pyserial>=3.5.0 \
    pymodbus>=2.5.0 \
    opcua>=0.98.0

# Stage 8: Reporting and documents
RUN pip install --no-cache-dir --default-timeout=300 \
    reportlab>=3.6.0 \
    openpyxl>=3.0.0 \
    xlsxwriter>=3.0.0 \
    fpdf2>=2.5.0 \
    python-docx>=0.8.11 \
    Pillow>=9.0.0

# Stage 9: Networking and monitoring
RUN pip install --no-cache-dir --default-timeout=300 \
    aiohttp>=3.8.0 \
    websockets>=10.0 \
    requests>=2.27.0 \
    httpx>=0.23.0 \
    prometheus-client>=0.13.0 \
    sentry-sdk>=1.5.0

# Stage 10: Utilities
RUN pip install --no-cache-dir --default-timeout=300 \
    pyyaml>=6.0 \
    python-dotenv>=0.19.0 \
    structlog>=22.1.0 \
    psutil>=5.8.0 \
    email-validator>=1.1.0 \
    gunicorn>=20.1.0 \
    boto3>=1.20.0 \
    dask>=2022.1.0 \
    statsmodels>=0.13.0

# Copy application code
COPY . /app/

# Make shell scripts executable (if any exist)
RUN find /app -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO

# Expose ports
EXPOSE 9000 9765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Run the application
CMD ["python", "main_application.py"]
