# Web Deployment Guide

## Quick Deploy Options

This SCADA AI System can be deployed to the web using several platforms.

### Option 1: Render.com (Recommended - Free Tier Available)

**Steps**:

1. Go to https://render.com/
2. Sign up / Login with GitHub
3. Click "New +" → "Web Service"
4. Connect this repository: `farandaway89/scada-ai-system`
5. Configure:
   - **Name**: scada-ai-system
   - **Environment**: Docker
   - **Instance Type**: Free
   - **Dockerfile Path**: ./Dockerfile
6. Add Environment Variables:
   ```
   ENVIRONMENT=production
   API_PORT=9000
   DATABASE_URL=sqlite:///./data/scada.db
   REDIS_ENABLED=false
   ```
7. Click "Create Web Service"

**Result**: Your app will be live at `https://scada-ai-system.onrender.com`

**API Documentation**: `https://scada-ai-system.onrender.com/docs`

### Option 2: Railway.app (Easy Deploy)

**Steps**:

1. Go to https://railway.app/
2. Sign up / Login with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select: `farandaway89/scada-ai-system`
5. Railway will auto-detect `railway.json` and `Dockerfile`
6. Add Environment Variables (Settings → Variables):
   ```
   ENVIRONMENT=production
   API_PORT=9000
   DATABASE_URL=sqlite:///./data/scada.db
   ```
7. Click "Deploy"

**Result**: Your app will be live at generated Railway URL

### Option 3: Fly.io

**Steps**:

1. Install Fly CLI:
   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

2. Login:
   ```bash
   fly auth login
   ```

3. Deploy:
   ```bash
   cd C:\developer\scada_ai_project
   fly launch --dockerfile Dockerfile --name scada-ai-system
   fly deploy
   ```

**Result**: Your app will be live at `https://scada-ai-system.fly.dev`

### Option 4: Heroku

**Steps**:

1. Install Heroku CLI
2. Login:
   ```bash
   heroku login
   ```

3. Create app:
   ```bash
   cd C:\developer\scada_ai_project
   heroku create scada-ai-system
   heroku stack:set container
   git push heroku main
   ```

**Result**: Your app will be live at `https://scada-ai-system.herokuapp.com`

### Option 5: Google Cloud Run

**Steps**:

1. Install Google Cloud SDK
2. Build and deploy:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/scada-ai-system
   gcloud run deploy scada-ai-system \
     --image gcr.io/PROJECT_ID/scada-ai-system \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

## Configuration Files

This repository includes:

- `render.yaml` - Render.com configuration
- `railway.json` - Railway.app configuration
- `Dockerfile` - Docker image definition
- `docker-compose.yml` - Local development

## Environment Variables

Required variables for production:

```bash
ENVIRONMENT=production
API_PORT=9000
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./data/scada.db
REDIS_ENABLED=false
```

Optional (for full features):

```bash
# Database (PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/scada_db

# Redis (for caching)
REDIS_ENABLED=true
REDIS_URL=redis://host:6379/0

# Security
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
```

## API Endpoints

Once deployed, access these endpoints:

- **API Documentation**: `/docs` (Swagger UI)
- **Health Check**: `/status`
- **Sensors**: `/sensors`
- **Real-time Data**: `/monitoring/current`
- **AI Analytics**: `/analytics/dashboard`
- **Compliance**: `/compliance/dashboard`

## Authentication

Default credentials:

- **Admin**: username `admin`, password `admin123`, token `demo_token_admin`
- **Operator**: username `operator`, password `operator123`, token `demo_token_operator`

Use Bearer Token authentication:

```bash
curl -H "Authorization: Bearer demo_token_admin" \
  https://your-app-url.com/sensors
```

## Free Tier Limitations

| Platform | Memory | CPU | Hours/Month | Sleep |
|----------|--------|-----|-------------|-------|
| Render | 512MB | Shared | 750 | Yes (15min idle) |
| Railway | 512MB | Shared | 500 | No |
| Fly.io | 256MB | Shared | Unlimited | Yes |
| Heroku | 512MB | Shared | 550 | Yes (30min idle) |

**Recommendation**: Use Render.com or Railway.app for best free tier.

## Performance Optimization

For production deployment:

1. **Upgrade Plan**: Use paid tier for better performance
2. **Add PostgreSQL**: Replace SQLite with PostgreSQL
3. **Add Redis**: Enable caching for faster responses
4. **CDN**: Use Cloudflare for static assets
5. **Monitoring**: Add Sentry or New Relic

## Scaling

To handle more traffic:

```bash
# Render.com
# Upgrade to Starter plan ($7/mo) or higher

# Railway.app
# Add resources in Settings → Resources

# Fly.io
fly scale count 2  # Run 2 instances
fly scale vm shared-cpu-2x  # Upgrade CPU
```

## Database Setup (Production)

For PostgreSQL (recommended for production):

```bash
# Render.com
# Create PostgreSQL database in dashboard
# Copy connection string to DATABASE_URL

# Railway.app
# Add PostgreSQL service
# Connection string auto-configured
```

## Monitoring

Check application logs:

```bash
# Render.com - View logs in dashboard

# Railway.app - View logs in dashboard

# Fly.io
fly logs

# Heroku
heroku logs --tail
```

## Troubleshooting

**App won't start**:
- Check environment variables
- Verify Dockerfile builds locally: `docker build .`
- Check logs for errors

**API returns 502/503**:
- App is sleeping (free tier) - first request wakes it up
- Wait 30 seconds and try again

**Database errors**:
- SQLite not persisting? Add volume mount
- Use PostgreSQL for production

**Out of memory**:
- Upgrade to paid plan
- Optimize TensorFlow models
- Disable heavy features

## Support

- Documentation: `/docs` folder in repository
- GitHub Issues: https://github.com/farandaway89/scada-ai-system/issues
- API Docs: `https://your-app-url.com/docs`

## Quick Links

- **GitHub**: https://github.com/farandaway89/scada-ai-system
- **Render**: https://dashboard.render.com/
- **Railway**: https://railway.app/dashboard
- **Fly.io**: https://fly.io/dashboard

---

**Current Status**: Ready for deployment
**Estimated Deploy Time**: 5-10 minutes
**Cost**: Free (with limitations) or $7+/month (full features)
