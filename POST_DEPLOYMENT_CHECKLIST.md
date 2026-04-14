# Post-Deployment Checklist

Complete these steps immediately after deploying to production to ensure your OAuth and integrations work correctly.

---

## 📋 **Pre-Deployment Checklist**

- [ ] `.gitignore` includes `.env` and `.env.local` ✓
- [ ] All real credentials are ONLY in `.env` (never in repo) ✓
- [ ] `.env.example` has placeholder values only ✓
- [ ] All required environment variables are set in Render
- [ ] Database migrations have completed successfully
- [ ] Service health check passes: `GET /health`

---

## 🔐 **Step 1: Google OAuth Configuration**

### **1.1 Find Your Deployed URL**
```
https://<your-service-name>.onrender.com
```
- [ ] Copy this URL
- [ ] Test it loads (should show API docs or health check)

### **1.2 Update Google Cloud Console**

1. [ ] Open [Google Cloud Console](https://console.cloud.google.com/)
2. [ ] Go to **APIs & Services → Credentials**
3. [ ] Click your OAuth 2.0 Client ID (Web Application)
4. [ ] Under **Authorized redirect URIs**, add:
   ```
   https://<your-service-name>.onrender.com/api/v1/auth/google/callback
   ```
5. [ ] Remove `http://localhost:8000/api/v1/auth/google/callback` (optional but clean)
6. [ ] Click **Save**

### **1.3 Update Render Environment Variables**

1. [ ] Go to Render Dashboard → Your Service → **Environment**
2. [ ] Update `GOOGLE_REDIRECT_URI`:
   ```
   https://<your-service-name>.onrender.com/api/v1/auth/google/callback
   ```
3. [ ] Click **"Save Changes"**
4. [ ] Wait for auto-redeploy to complete

---

## 🔑 **Step 2: Production Security**

### **2.1 Regenerate JWT Secret (Recommended)**

Generate a new JWT secret for production:

```bash
# On your local machine
python -c "import secrets; print(secrets.token_hex(32))"
```

1. [ ] Copy the output
2. [ ] In Render Dashboard → Environment
3. [ ] Update `JWT_SECRET_KEY` with new value
4. [ ] Save changes

> **Note:** New secret invalidates existing tokens. Do this before users start using the API.

### **2.2 Set Environment to Production**

1. [ ] Go to Render → Environment
2. [ ] Set `ENVIRONMENT=production`
3. [ ] Set `DEBUG=false`
4. [ ] Save changes

This disables Swagger UI (`/docs`) in production for security.

### **2.3 Verify Secrets Are Never in Repo**

```bash
# Check if any real secrets are committed
git log -p | grep -i "sendgrid\|twilio_account\|google_client"
```

If you see real values in history:
1. [ ] Regenerate all secrets immediately
2. [ ] Run `git-secrets` or similar tool
3. [ ] Update `.gitignore` to ensure `.env` is ignored

---

## 🧪 **Step 3: Test All Features**

### **3.1 Test Health Check**
```bash
curl https://<your-service-name>.onrender.com/api/v1/health
```
**Expected:** `{"status": "ok", "version": "1.0.0"}`

### **3.2 Test User Registration**
```bash
curl -X POST https://<your-service-name>.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email":"testuser@example.com",
    "password":"TestPassword123",
    "full_name":"Test User",
    "phone_number":"+1234567890"
  }'
```

- [ ] Returns `201` with user object
- [ ] Check Render logs for email/SMS delivery

### **3.3 Test Google OAuth**
1. [ ] Open: `https://<your-service-name>.onrender.com/api/v1/auth/google/login`
2. [ ] Should redirect to Google login
3. [ ] After login, should return tokens

**If OAuth fails:**
- [ ] Check Render service logs
- [ ] Verify `GOOGLE_REDIRECT_URI` in Render matches Google Console
- [ ] Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct

### **3.4 Test Authenticated Endpoints**
```bash
# Get profile (requires access token from login)
curl -H "Authorization: Bearer <access_token>" \
  https://<your-service-name>.onrender.com/api/v1/users/me
```

- [ ] Returns user profile

---

## 📧 **Step 4: Integration Verification**

### **4.1 SendGrid Email**
- [ ] Check email was received from registration
- [ ] Email address: `SENDGRID_FROM_EMAIL`
- [ ] Subject: Should be welcome email

**If email not received:**
- [ ] Verify email address is verified in SendGrid
- [ ] Check sending domain is configured
- [ ] Check Render logs for errors

### **4.2 Twilio SMS**
- [ ] SMS should be received with welcome message
- [ ] Phone number: `TWILIO_PHONE_NUMBER`

**If SMS not received:**
- [ ] Check `TWILIO_PHONE_NUMBER` format: `+1234567890`
- [ ] Check Twilio account has credits/active status
- [ ] Check Render logs

### **4.3 Database Verification**
1. [ ] Go to Render → PostgreSQL → Info
2. [ ] Note the connection details
3. [ ] Verify migration completed: Check `alembic_version` table exists

---

## 🌐 **Step 5: CORS & Frontend Integration**

### **5.1 Update CORS Origins**
1. [ ] Go to Render → Environment
2. [ ] Update `ALLOWED_ORIGINS` to include your frontend URL:
   ```
   https://yourdomain.com,https://www.yourdomain.com
   ```
3. [ ] Save changes

### **5.2 Update Frontend Configuration**
- [ ] API base URL: `https://<your-service-name>.onrender.com`
- [ ] OAuth client ID: Same (accessible from frontend)
- [ ] Redirect URI for OAuth: `https://<your-service-name>.onrender.com/api/v1/auth/google/callback`

---

## 📊 **Step 6: Monitoring Setup**

### **6.1 Enable Monitoring**
1. [ ] Go to Render Dashboard → Service
2. [ ] Check **Metrics** tab for CPU/Memory usage
3. [ ] Set up alerts (if on paid plan)

### **6.2 Check Logs Regularly**
```
Render Dashboard → Service → Logs
```

- [ ] No error messages on startup
- [ ] Requests completing successfully
- [ ] Database queries working

### **6.3 Set Up Health Checks**
Optional: Use external monitoring service (UptimeRobot, Pingdom, etc.)
```
Endpoint: https://<your-service-name>.onrender.com/api/v1/health
Interval: 5 minutes
```

---

## 🔄 **Step 7: Ongoing Maintenance**

### **7.1 Weekly**
- [ ] Check Render logs for errors
- [ ] Verify health endpoint responds

### **7.2 Monthly**
- [ ] Review user registrations
- [ ] Rotate JWT secret if needed
- [ ] Check database size

### **7.3 After Any Code Change**
- [ ] Push to GitHub
- [ ] Wait for Render auto-deploy
- [ ] Test critical endpoints
- [ ] Check logs

---

## 🆘 **Troubleshooting**

### **OAuth Redirect Not Working**
1. Make sure Render has `GOOGLE_REDIRECT_URI=https://<service>.onrender.com/api/v1/auth/google/callback`
2. Make sure Google Console has exact same URL in normalized form (including trailing slashes)
3. Check that service has redeployed after env variable change

### **Email Not Sending**
1. Verify `SENDGRID_FROM_EMAIL` is verified in SendGrid dashboard
2. Check `SENDGRID_API_KEY` is correct
3. Look at Render logs for SMTP errors

### **SMS Not Sending**
1. Verify Twilio account is active
2. Check `TWILIO_PHONE_NUMBER` format: `+1234567890`
3. Verify Twilio credentials are correct

### **Database Connection Fails**
1. Check `DATABASE_URL` is set in Render Environment
2. Verify PostgreSQL service is in same region
3. Try connecting via Render PostgreSQL shell to test

---

## ✅ **Final Verification**

- [ ] Health endpoint responds
- [ ] User registration works
- [ ] Email received
- [ ] SMS received (if enabled)
- [ ] Google OAuth redirect works
- [ ] Authenticated endpoints return user data
- [ ] No errors in Render logs
- [ ] Service has auto-redeployed after env changes

**🎉 Your production deployment is complete!**

---

## 🚀 **What's Next**

- Set up GitHub Actions for automated testing
- Add more endpoints for your use case
- Scale up if needed (upgrade from free tier)
- Enable custom domain (optional, paid)
- Set up monitoring alerts
