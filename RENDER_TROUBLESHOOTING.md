# Render Deployment Troubleshooting

## Issue 1: User Registration Returns 500 Error

### **Root Cause**
Missing or incorrect environment variables on Render.

### **Step-by-Step Fix**

#### **1. Verify DATABASE_URL is Set**
1. Go to Render Dashboard → Your PostgreSQL Instance → Info
2. Copy the **Internal Database URL** (starts with `postgresql://`)
3. Go to Your Web Service → Environment
4. Check if `DATABASE_URL` is present and matches

**Expected format:**
```
postgresql://username:password@hostname:5432/dbname
```

#### **2. Check All Required Variables are Set**
Go to Web Service → Environment and verify:

| Variable | Example | Status |
|----------|---------|--------|
| `DATABASE_URL` | `postgresql://...` | ✅ Must exist |
| `GOOGLE_CLIENT_ID` | `264205217933-...apps.googleusercontent.com` | ✅ Must exist |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` | ✅ Must exist |
| `GOOGLE_REDIRECT_URI` | `https://kalliber-assignment.onrender.com/api/v1/auth/google/callback` | ✅ **CRITICAL** |
| `JWT_SECRET_KEY` | 64+ char hex string | ✅ Must exist |
| `SENDGRID_API_KEY` | `SG.....` | ⚠️ If using email |
| `TWILIO_ACCOUNT_SID` | `AC....` | ⚠️ If using SMS |

If any are missing → Add them and click **Save Changes**

#### **3. Verify Database Migrations Ran**

Your migrations now run automatically on startup. To verify they completed:

1. Go to Web Service → Logs
2. Look for these messages on startup:
   ```
   Running database migrations...
   INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
   INFO  [alembic.runtime.migration] Will assume transactional DDL is supported
   INFO  [alembic.migration] Running upgrade  -> 0001_initial
   INFO  [alembic.migration] Running upgrade 0001_initial -> 0002_verification_codes
   ```

3. If you see migration messages → ✅ Good
4. If you see errors like `relation "users" already exists` → ✅ Still OK (already migrated)

#### **4. Test Registration via Logs**

After making changes:

1. Go to Web Service → Dashboard
2. Click **Manual Deploy** (or make a git push to auto-trigger)
3. Wait for deployment to complete
4. Test registration:
   ```bash
   curl -X POST https://kalliber-assignment.onrender.com/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email":"test@example.com",
       "password":"TestPassword123",
       "full_name":"Test User"
     }'
   ```

5. Check Logs for errors:
   - If 201 ✅ Success!
   - If 500 → Look at logs for error details

#### **5. Common 500 Errors and Fixes**

**Error: `(psycopg2.OperationalError) could not connect to server`**
- Fix: DATABASE_URL is missing or invalid
- Reconnect PostgreSQL instance

**Error: `ProgrammingError: relation "users" does not exist`**
- Fix: Migrations didn't run
- Manually trigger deploy again

**Error: `SendGrid authentication failed`**
- Fix: SENDGRID_API_KEY is wrong or missing
- Verify in SendGrid dashboard

**Error: `ValueError: email or password invalid`**
- Fix: This is actually OK - user doesn't exist yet
- Try registration with different email

---

## Issue 2: Google OAuth Redirect URI Mismatch

### **Why It Happens**
- Your code has `GOOGLE_REDIRECT_URI=http://localhost:8000/...`
- Google Cloud is configured with different URL
- They must match exactly

### **How to Fix**

#### **Step 1: Update Google Cloud Console**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services → Credentials**
4. Click your OAuth 2.0 Client ID (Web Application)
5. Find **Authorized redirect URIs**
6. Update to:
   ```
   https://kalliber-assignment.onrender.com/api/v1/auth/google/callback
   ```
7. Remove any `localhost` entries
8. Click **Save**

#### **Step 2: Update Render Environment**
1. Render Dashboard → Web Service → Environment
2. Set `GOOGLE_REDIRECT_URI`:
   ```
   https://kalliber-assignment.onrender.com/api/v1/auth/google/callback
   ```
3. Click **Save Changes**

#### **Step 3: Redeploy (Automatic)**
Service will auto-restart with new variable.

#### **Step 4: Test**
1. Go to Swagger UI: `https://kalliber-assignment.onrender.com/docs`
2. Find `/auth/google/login` endpoint
3. Click **Try it out**
4. You should be redirected to Google login
5. After auth, should receive tokens

---

## Quick Debugging Checklist

- [ ] DATABASE_URL exists in Render Environment
- [ ] GOOGLE_REDIRECT_URI points to your Render URL
- [ ] Google Cloud Console has same redirect URI
- [ ] All required env vars are set (no empty values)
- [ ] Service has been redeployed after env changes
- [ ] Migrations completed (check logs)
- [ ] Test registration returns 201, not 500
- [ ] Google OAuth doesn't show "redirect_uri_mismatch" error

---

## Still Having Issues?

### Check Logs
1. Render Dashboard → Service → Logs
2. Look for first error message
3. Share the error details

### Common Patterns
- **Connection refused** → DATABASE_URL issue
- **Authentication failed** → Credentials (API keys) issue
- **404 Not found** → Wrong URL format
- **500 Internal Server Error** → Check full error in logs

