# Railway Deployment Guide

## Setup Steps

### 1. **Install Railway CLI** (Optional but recommended)
```bash
npm install -g @railway/cli
# or
brew install railway  # on macOS
```

### 2. **Configure Environment Variables**

In your Railway dashboard, add these environment variables:

```
DATABASE_URL=postgresql://[user]:[password]@[host]:[port]/[database]
JWT_SECRET_KEY=[generate new secure key: python -c "import secrets; print(secrets.token_hex(32))"]
DEBUG=False
ENVIRONMENT=production

# Google OAuth2
GOOGLE_CLIENT_ID=[your_client_id]
GOOGLE_CLIENT_SECRET=[your_client_secret]
GOOGLE_REDIRECT_URI=https://[your-railway-domain]/api/v1/auth/google/callback

# SendGrid Email
SENDGRID_API_KEY=[your_sendgrid_key]
SENDGRID_FROM_EMAIL=noreply@example.com

# Twilio SMS
TWILIO_ACCOUNT_SID=[your_account_sid]
TWILIO_AUTH_TOKEN=[your_auth_token]
TWILIO_PHONE_NUMBER=[your_twilio_number]
TWILIO_VERIFY_SERVICE_SID=[your_verify_service_sid]
```

### 3. **Deploy Steps**

#### **Option A: Using Railway CLI**
```bash
# Login to Railway
railway login

# Connect to project (skip if already in project dir)
railway connect

# Deploy
railway up

# View logs
railway logs
```

#### **Option B: Using Railway Dashboard**
1. Go to https://railway.app/dashboard
2. Create new project or select existing
3. Connect GitHub repository
4. Railway will auto-detect `Procfile` and `railway.json`
5. Add environment variables in Settings
6. Click "Deploy"

#### **Option C: Using GitHub Integration** (Recommended)
1. Go to Railway Dashboard → GitHub Integration
2. Connect your GitHub account
3. Select repository: `Sahilx22/kalliber_test1`
4. Railway auto-deploys on every push to `main` branch
5. Set environment variables in Railway dashboard

### 4. **Database Setup**

Railway will handle PostgreSQL provisioning:

1. In Railway Dashboard, click "Add a service"
2. Select "PostgreSQL"
3. Railway auto-populates `DATABASE_URL` environment variable
4. On first deploy, migrations run automatically (Procfile `release` command)

### 5. **Post-Deployment**

Once deployed:

1. **Get your Railway domain**: `https://your-service-name.railway.app`
2. **Update OAuth redirect URL** in Google Cloud Console:
   ```
   https://your-service-name.railway.app/api/v1/auth/google/callback
   ```
3. **Test endpoints**:
   ```bash
   curl https://your-service-name.railway.app/docs  # Swagger UI
   curl https://your-service-name.railway.app/health  # Health check
   ```

### 6. **Monitoring & Debugging**

- **Logs**: Railway Dashboard → Logs tab
- **Metrics**: Railway Dashboard → Metrics tab
- **Environment Variables**: Railway Dashboard → Variables tab

### 7. **Custom Domain** (Optional)

1. Railway Dashboard → Settings → Domains
2. Add custom domain
3. Follow DNS configuration instructions

## Troubleshooting

### Deployment Fails
```bash
# Check Railway logs
railway logs

# Check build logs specifically
railway logs --service=[service-name] --follow
```

### Database Connection Issues
```
Error: could not connect to database
→ Verify DATABASE_URL is set in Railway environment
→ Check PostgreSQL service is provisioned
→ Run: railway run bash -c "echo $DATABASE_URL"
```

### Migrations Not Running
```bash
# Manually run migrations
railway run alembic upgrade head
```

### Environment Variables Not Loaded
```bash
# Verify they're set in Railway
railway variables

# Re-deploy after adding/changing variables
railway redeploy
```

## Performance Optimization

### For Production:
1. Set `DEBUG=False` (default for security)
2. Use PostgreSQL (not SQLite)
3. Enable Railway's auto-scaling if needed
4. Consider adding Redis for token caching
5. Set up monitoring alerts in Railway

### Database Optimization:
```bash
# Create indexes for frequently queried columns
railway run psql $DATABASE_URL << EOF
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_verification_codes_code ON verification_codes(code);
EOF
```

## Rollback

If something goes wrong:

```bash
# View deployment history
railway deployments

# Rollback to previous version
railway rollback [deployment-id]
```

## Cost Estimation

Railway pricing (as of 2024):
- **Compute**: $5/month starter → $20/month standard
- **PostgreSQL**: $0.1/GB storage + $0.15/hour compute
- **Free tier**: 5GB storage, 100 GB/month bandwidth

Typical cost for this project: **$15-25/month** (small to medium usage)
