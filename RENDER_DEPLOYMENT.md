# Render Deployment Guide

**Render.com** is a modern cloud platform with a generous free tier. Unlike Railway, Render gives you:
- **750 hours/month free** (enough for continuous deployment)
- **PostgreSQL database for free**
- **No credit card needed** to start
- **Auto-deploys** on GitHub push

---

## 🚀 **Quick Start (5 Minutes)**

### **Step 1: Sign Up**
1. Go to https://render.com
2. Click "Get Started"
3. Sign up with GitHub (recommended) or email
4. No credit card required!

### **Step 2: Create Web Service**

1. Go to Dashboard → "New +"
2. Select "Web Service"
3. Connect your GitHub repository:
   - Search for: `kalliber_test1`
   - Click "Connect"
4. Configure the service:
   ```
   Name:              fastapi-auth-service
   Runtime:           Python 3
   Region:            Choose closest to you (us-east-1 recommended)
   Build Command:     pip install -r requirements.txt && alembic upgrade head
   Start Command:     uvicorn app.main:app --host 0.0.0.0 --port $PORT
   Plan:              Free
   ```
5. Click "Create Web Service"

### **Step 3: Add PostgreSQL Database**

1. From Dashboard → "New +"
2. Select "PostgreSQL"
3. Configure:
   ```
   Name:    fastapi-db
   Region:  Same as your web service
   Plan:    Free
   ```
4. Click "Create Database"

**Render auto-adds `DATABASE_URL` to your service!** ✅

### **Step 4: Set Environment Variables**

1. Go to your Web Service → Environment
2. Add these variables:

```
DEBUG=false
ENVIRONMENT=production
JWT_SECRET_KEY=[Generate: python -c "import secrets; print(secrets.token_hex(32))"]

# Google OAuth2
GOOGLE_CLIENT_ID=[your_client_id]
GOOGLE_CLIENT_SECRET=[your_client_secret]
GOOGLE_REDIRECT_URI=https://<your-service-name>.onrender.com/api/v1/auth/google/callback

# SendGrid
SENDGRID_API_KEY=[your_sendgrid_key]
SENDGRID_FROM_EMAIL=noreply@example.com

# Twilio
TWILIO_ACCOUNT_SID=[your_account_sid]
TWILIO_AUTH_TOKEN=[your_auth_token]
TWILIO_PHONE_NUMBER=[your_phone]
TWILIO_VERIFY_SERVICE_SID=[your_verify_sid]
```

3. Click "Save Changes"
4. Service automatically redeploys

### **Step 5: Auto-Deploy on GitHub Push**

Good news - it's already set up! 🎉

Every time you push to `main` branch:
```bash
git push origin main
```

Render automatically:
1. Builds your Docker image
2. Runs migrations (alembic upgrade head)
3. Deploys your service
4. Zero downtime

---

## ✅ **Deployment Complete!**

Your app is now live at:
```
https://<your-service-name>.onrender.com
```

**Test it**:
```bash
# Swagger UI
https://<your-service-name>.onrender.com/docs

# Health check
curl https://<your-service-name>.onrender.com/api/v1/health

# Register user
curl -X POST https://<your-service-name>.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"user@example.com",
    "password":"Password123",
    "full_name":"Test User"
  }'
```

---

## 📊 **Render Dashboard Overview**

### **Logs**
- Service Logs: Real-time request logs
- Build Logs: See deployment progress
- Database Logs: PostgreSQL query logs (optional)

### **Metrics**
- CPU usage
- Memory usage
- Network I/O
- Response times

### **Environment**
- Add/update environment variables
- Service auto-restarts on changes

### **Deployments**
- View deployment history
- Manual redeploy button
- Rollback to previous versions

---

## 🔧 **Common Tasks**

### **View Logs**
```bash
# In Render Dashboard → Service → Logs
# Or if you have Render CLI installed:
render logs --service fastapi-auth-service --follow
```

### **Manually Run Migrations**
```
In Dashboard → Service → Shell
Then run: alembic upgrade head
```

### **Restart Service**
```
Dashboard → Service → Restart → Confirm
```

### **Update Environment Variables**
```
Dashboard → Environment → Edit → Save
(Auto-redeploys with new variables)
```

### **Check Database Connection**
```
Dashboard → PostgreSQL → Info
Copy connection string and test locally first
```

---

## 📈 **Scaling (When You Outgrow Free Tier)**

When you need more resources, upgrade from:

| Plan | Price | Resources | Cold Start |
|------|-------|-----------|-----------|
| **Free** | $0 | 0.5 CPU, 512 MB RAM | ~30 sec (sleeps) |
| **Standard** | $7/mo | 1 CPU, 512 MB RAM | Instant |
| **Pro** | $12/mo | 2 CPU, 2 GB RAM | Instant |
| **Premium** | $25/mo | 4 CPU, 4 GB RAM | Instant |

Free tier services spin down after 15 mins of inactivity (cold start on next request).
Paid plans stay always-on.

---

## 🆘 **Troubleshooting**

### **Service Won't Deploy**
- Check Build Logs in Dashboard
- Ensure `requirements.txt` is in root directory
- Verify Python version is available

### **DATABASE_URL Not Found**
- Create PostgreSQL database first
- Check it's in same region as web service
- Service auto-detects and sets DATABASE_URL

### **500 Error After Deploy**
```
Check:
1. Service Logs for error details
2. DATABASE_URL is set (Dashboard → Environment)
3. Migrations ran: alembic upgrade head
4. All environment variables are present
```

### **Migrations Failed**
```
In Dashboard → PostgreSQL → Shell:
psql -U [user] -d [dbname]

Then check tables:
\dt

If tables missing, manually run:
alembic upgrade head
```

### **Service Keeps Restarting**
- Check Logs for errors
- Verify all required environment variables are set
- Check memory usage (may need upgrade to paid)

### **GitHub Integration Not Working**
- Disconnect: Account → Integrations
- Reconnect: Account → Integrations → GitHub
- Re-authorize if needed

---

## 💡 **Pro Tips**

### **1. Use Cron Jobs for Maintenance**
```yaml
# In render.yaml, add:
crons:
  - id: cleanup-old-tokens
    schedule: "0 0 * * *"  # Daily at midnight
    command: python scripts/cleanup_tokens.py
```

### **2. Manual Redeploy Without Push**
- Dashboard → Service → Manual Deploy → Latest commit
- Useful for restarting with updated env vars

### **3. Free Database Backup**
- Render auto-backs up PostgreSQL
- Restore via Dashboard → PostgreSQL → Backups

### **4. Monitor Deploys**
- GitHub shows deployment status with checkmark ✓
- Click to see full logs on Render

### **5. Use Render CLI for Local Testing**
```bash
npm install -g @render/cli
render login
render build --project-id <your-project-id>
```

---

## 💰 **Free Tier Limitations**

- **750 hours/month** (enough for always-on service)
- **Services spin down** after 15 mins inactivity
- **1 GB database storage** (plenty for testing)
- **100 GB/month bandwidth** (very generous)
- **No SSL? Nope**, Render provides free SSL for all custom domains!

---

## 🎯 **Next Steps**

1. ✅ Push to GitHub with `render.yaml`
2. ✅ Create Render account
3. ✅ Connect repository
4. ✅ Set environment variables
5. ✅ Deploy PostgreSQL
6. ✅ Get your live URL
7. ✅ Test endpoints

**Your app should be live in ~2-3 minutes!**

Questions? Check Render docs: https://render.com/docs
