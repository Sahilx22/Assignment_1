#!/bin/bash
# Render deployment helper script
# This script sets up your Render deployment

echo "🚀 Render Deployment Setup"
echo "=========================="

# Check if render.yaml exists
if [ ! -f "render.yaml" ]; then
    echo "❌ render.yaml not found!"
    exit 1
fi

echo "✅ render.yaml found"
echo ""
echo "📋 Next steps:"
echo "1. Go to https://render.com and sign up (free)"
echo "2. Connect your GitHub repository"
echo "3. Select 'kalliber_test1' repository"
echo "4. Create Web Service:"
echo "   - Name: fastapi-auth-service"
echo "   - Runtime: Python 3"
echo "   - Build Command: pip install -r requirements.txt && alembic upgrade head"
echo "   - Start Command: uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
echo "   - Plan: Free"
echo ""
echo "5. Create PostgreSQL database (Free plan)"
echo "6. Add environment variables:"
echo "   - DEBUG=false"
echo "   - ENVIRONMENT=production"
echo "   - JWT_SECRET_KEY=<generate new secret>"
echo "   - GOOGLE_CLIENT_ID=<your_id>"
echo "   - GOOGLE_CLIENT_SECRET=<your_secret>"
echo "   - GOOGLE_REDIRECT_URI=https://<your-service>.onrender.com/api/v1/auth/google/callback"
echo "   - SENDGRID_API_KEY=<your_key>"
echo "   - TWILIO_ACCOUNT_SID=<your_sid>"
echo "   - TWILIO_AUTH_TOKEN=<your_token>"
echo "   - TWILIO_PHONE_NUMBER=<your_number>"
echo "   - TWILIO_VERIFY_SERVICE_SID=<your_verify_id>"
echo ""
echo "📚 Full guide: See RENDER_DEPLOYMENT.md"
echo ""
echo "✨ That's it! Your app will auto-deploy on every GitHub push!"
