# 🚀 Azure Web App Deployment Guide

## Employee Onboarding Assistant - Deployment Instructions

---

## 📋 **Prerequisites**

- ✅ Azure account with active subscription
- ✅ Azure Web App created (Python 3.11, Linux)
- ✅ GitHub repository created
- ✅ Azure App Registration for Microsoft authentication

---

## **Step 1: Configure Azure App Registration**

### Update Redirect URI (CRITICAL - Do this FIRST!)

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: **Azure Active Directory** → **App registrations**
3. Find and click your app
4. Click **Authentication** (left sidebar)
5. Under "Web" → **Redirect URIs**, click **"+ Add URI"**
6. Add your Azure Web App URL:
   ```
   https://YOUR-APP-NAME.azurewebsites.net
   ```
7. Keep localhost for testing:
   ```
   http://localhost:800
   ```
8. Click **Save**

---

## **Step 2: Configure Azure Web App Environment Variables**

### Add Application Settings

1. Go to: **Azure Portal** → Your Web App
2. Click: **Configuration** (left sidebar)
3. Click: **"+ New application setting"**
4. Add each variable from `azure-env-template.txt`:

```bash
# Required Variables:
REDIRECT_URI = https://YOUR-APP-NAME.azurewebsites.net
AZURE_CLIENT_ID = [from App Registration]
AZURE_CLIENT_SECRET = [from App Registration]
USER_TENANT_ID = [your user tenant ID]
AZURE_AI_TENANT_ID = [your AI tenant ID]
AZURE_AI_ENDPOINT = [your AI endpoint URL]
WEBSITES_PORT = 8000
SCM_DO_BUILD_DURING_DEPLOYMENT = true
```

5. Click **"Save"** at the top
6. App will restart automatically

---

## **Step 3: Prepare Code for Deployment**

### Initialize Git Repository (if not done)

```bash
cd /Users/cpashal/Downloads/final

# Initialize git
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit - Employee Onboarding App"
```

---

## **Step 4: Push to GitHub**

```bash
# Add your GitHub remote (replace with your company repo)
git remote add origin https://github.com/YOUR_COMPANY/YOUR_REPO.git

# Push to GitHub
git push -u origin main
```

---

## **Step 5: Connect GitHub to Azure Web App**

### Set Up Continuous Deployment

1. Go to: **Azure Portal** → Your Web App
2. Click: **Deployment Center** (left sidebar)
3. Select: **GitHub**
4. Click: **Authorize** and sign in to GitHub
5. Select:
   - **Organization**: Your company
   - **Repository**: Your repo name
   - **Branch**: main
6. Click: **Save**

Azure will automatically:
- Create a GitHub Actions workflow
- Deploy your code
- Redeploy on every push to main branch

---

## **Step 6: Monitor Deployment**

### Check Build Status

1. **GitHub**: Check Actions tab for build progress
2. **Azure Portal**: 
   - Deployment Center → **Logs** (see deployment history)
   - **Log stream** (see real-time logs)

### First Deployment Takes ~5-10 Minutes

The app needs to:
- Install Python packages
- Configure Streamlit
- Start the server

---

## **Step 7: Test Your Deployment**

1. Open: `https://YOUR-APP-NAME.azurewebsites.net`
2. You should see the login page
3. Click "Sign in with Microsoft"
4. Complete authentication
5. Test the onboarding flow including signature

---

## **🐛 Troubleshooting**

### App Shows "Application Error"

**Check:**
1. Log Stream for error messages
2. All environment variables are set correctly
3. `WEBSITES_PORT=8000` is configured
4. `startup.sh` has execute permissions

**Fix:**
```bash
# Make startup.sh executable
chmod +x startup.sh
git add startup.sh
git commit -m "Fix startup.sh permissions"
git push
```

### Authentication Fails

**Check:**
1. Redirect URI matches exactly in App Registration
2. `REDIRECT_URI` environment variable is correct
3. Client ID and Secret are correct
4. Tenant IDs are correct

### Packages Not Installing

**Check:**
1. `requirements.txt` is in root directory
2. `.deployment` file exists
3. `SCM_DO_BUILD_DURING_DEPLOYMENT=true` is set

### Port Binding Error

**Check:**
1. `WEBSITES_PORT=8000` is set in Configuration
2. `startup.sh` uses `$WEBSITES_PORT` variable
3. `.streamlit/config.toml` port matches

---

## **📊 Monitoring & Logs**

### View Real-Time Logs

**Azure Portal → Your Web App:**
- **Log stream**: Real-time application logs
- **Metrics**: CPU, Memory, Response times
- **Application Insights**: Advanced monitoring (optional)

### Download Logs

```bash
# Using Azure CLI
az webapp log download \
  --resource-group YOUR_RESOURCE_GROUP \
  --name YOUR_APP_NAME
```

---

## **🔄 Update Your App**

### Make Changes and Redeploy

```bash
# Make code changes
# ...

# Commit and push
git add .
git commit -m "Your update message"
git push

# Azure automatically deploys!
```

---

## **⚙️ Performance Optimization**

### Recommended Azure Web App Tier

- **Development/Testing**: B1 Basic ($13/month)
- **Production**: P1V2 Premium ($96/month) - Better performance
- **High Traffic**: P2V2 or P3V2

### Scale Out

**Azure Portal → Your Web App → Scale out (App Service plan)**
- Increase instance count for high traffic
- Enable auto-scaling based on CPU/Memory

---

## **🔐 Security Best Practices**

1. ✅ Use Azure Key Vault for secrets (advanced)
2. ✅ Enable HTTPS only (should be default)
3. ✅ Enable Application Insights for monitoring
4. ✅ Review access logs regularly
5. ✅ Keep dependencies updated in `requirements.txt`

---

## **📞 Need Help?**

### Useful Azure CLI Commands

```bash
# View app status
az webapp show --name YOUR_APP_NAME --resource-group YOUR_RG

# Restart app
az webapp restart --name YOUR_APP_NAME --resource-group YOUR_RG

# View recent logs
az webapp log tail --name YOUR_APP_NAME --resource-group YOUR_RG

# Download logs
az webapp log download --name YOUR_APP_NAME --resource-group YOUR_RG
```

---

## **✅ Deployment Checklist**

- [ ] Azure Web App created (Python 3.11, Linux)
- [ ] Updated redirect URI in Azure App Registration
- [ ] Added all environment variables in Azure Configuration
- [ ] Code pushed to GitHub
- [ ] GitHub connected to Azure Deployment Center
- [ ] Deployment completed successfully
- [ ] Tested login and authentication
- [ ] Tested onboarding flow
- [ ] Tested signature functionality
- [ ] Verified data is being stored correctly

---

## **🎉 Success!**

Your Employee Onboarding Assistant is now live on Azure! 🚀

**App URL**: `https://YOUR-APP-NAME.azurewebsites.net`

Share this with your team and start onboarding employees!

---

**Questions?** Check Azure Log Stream for detailed error messages.

