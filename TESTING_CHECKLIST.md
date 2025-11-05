# Testing Checklist - Multi-Tenant Authentication

## Pre-Testing Setup

### 1. Verify Environment Configuration

Check your `.env` file has the correct settings:

```bash
# Required for multi-tenant authentication
USER_TENANT_ID=organizations

# Other required settings
AZURE_CLIENT_ID=your_client_id_here
AZURE_CLIENT_SECRET=your_client_secret_here
AZURE_AI_TENANT_ID=your_ai_tenant_id_here
AZURE_AI_ENDPOINT=your_ai_endpoint_here
REDIRECT_URI=http://localhost:8501
```

**✅ Checklist:**
- [ ] `.env` file exists in the project root
- [ ] `USER_TENANT_ID=organizations` is set (or "common")
- [ ] All other required variables are set
- [ ] No typos or extra spaces

### 2. Verify Azure AD App Registration

In Azure Portal → App registrations → Your app:

**✅ Checklist:**
- [ ] Go to **Authentication** → **Supported account types**
- [ ] Should be set to one of:
  - ✅ "Accounts in any organizational directory"
  - ✅ "Accounts in any organizational directory and personal Microsoft accounts"
- [ ] **NOT** set to "Single tenant"
- [ ] Redirect URI matches your `REDIRECT_URI` (e.g., `http://localhost:8501`)

---

## Testing Steps

### Test 1: Start the Application

```bash
cd /Users/cpashal/Downloads/final

# Activate virtual environment (if using one)
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install/upgrade dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

**✅ Expected Result:**
- [ ] Application starts without errors
- [ ] Browser opens to `http://localhost:8000`
- [ ] Login page displays with "Sign in with Microsoft" button
- [ ] No error messages in terminal

### Test 2: Test Authentication with Drew (navpayroll.onmicrosoft.com)

**Test User:** `Drew@navpayroll.onmicrosoft.com`

**Steps:**
1. Click "Sign in with Microsoft"
2. Enter: `Drew@navpayroll.onmicrosoft.com`
3. Complete authentication

**✅ Expected Result:**
- [ ] Authentication succeeds (no tenant mismatch error)
- [ ] User is redirected back to application
- [ ] Success message appears: "✅ Authentication successful!"
- [ ] User info displays in the header
- [ ] Chat interface loads

**❌ If Error Occurs:**
- Check terminal for error messages
- Verify `USER_TENANT_ID=organizations` in `.env`
- Verify Azure AD app supports multi-tenant
- Check redirect URI matches exactly

### Test 3: Verify Tenant ID Extraction

After successful login, check the terminal output:

**✅ Look for:**
- [ ] Console shows tenant ID extraction (if debug logging enabled)
- [ ] Tenant ID should be: `f9dc0130-ce02-40fa-8e6d-0565d0d9b3f3` for Drew
- [ ] No "unknown" tenant ID errors

**To verify in code (add temporarily for testing):**
```python
# After line 254 in app.py, add:
print(f"🔍 DEBUG: User logged in - Email: {st.session_state.user_info.get('mail')}, Tenant: {st.session_state.user_info.get('tenant_id')}")
```

### Test 4: Test with Other Users from Excel File

**Test User 2:** `info@primopayday.com` (or any primopayday.com user)

**Steps:**
1. Sign out (if logged in)
2. Click "Sign in with Microsoft"
3. Enter: `info@primopayday.com`
4. Complete authentication

**✅ Expected Result:**
- [ ] Authentication succeeds
- [ ] Tenant ID extracted: `c38d599e-1cac-4c0b-a29c-a94fe9d2fea9`
- [ ] Application loads correctly

### Test 5: Test Agent Initialization

After login, verify the agent is initialized:

**✅ Expected Result:**
- [ ] Spinner shows: "Connecting to Azure AI..."
- [ ] Spinner shows: "Looking up agent for tenant..."
- [ ] Spinner shows: "Setting up [agent type] agent for [org name]..."
- [ ] Success message: "✅ Connected to [agent type] agent for [org name]"
- [ ] Agent greeting message appears in chat

**❌ If Error Occurs:**
- Check Logic App URL is correct
- Verify Logic App is running and accessible
- Check tenant ID is being passed correctly

### Test 6: Test Full Onboarding Flow (Optional)

**Steps:**
1. Complete authentication
2. Start onboarding conversation
3. Provide employee information
4. Complete signature (if required)
5. Verify data submission

**✅ Expected Result:**
- [ ] Agent collects all required information
- [ ] Signature canvas appears (if `requireSignature=true`)
- [ ] Data submitted successfully
- [ ] Success message displayed

---

## Debugging Commands

### Check Current Configuration

```bash
# Check if .env file exists and has correct values
cat .env | grep USER_TENANT_ID

# Should output: USER_TENANT_ID=organizations
```

### View Application Logs

```bash
# Run with verbose logging
streamlit run app.py --logger.level=debug
```

### Test Authentication Flow Manually

```python
# Add to app.py temporarily for testing (after line 88):
import os
print(f"🔍 DEBUG: AUTHORITY = {AUTHORITY}")
print(f"🔍 DEBUG: USER_TENANT_ID = {USER_TENANT_ID}")
```

---

## Common Issues & Solutions

### ❌ Issue: "Selected user account does not exist in tenant"

**Cause:** `USER_TENANT_ID` is set to a specific tenant ID instead of "organizations"

**Solution:**
1. Check `.env` file: `USER_TENANT_ID=organizations`
2. Restart the application
3. Clear browser cache/cookies

### ❌ Issue: "Application not found"

**Cause:** Azure AD app registration doesn't support multi-tenant

**Solution:**
1. Azure Portal → App registrations → Your app
2. Authentication → Supported account types
3. Change to "Accounts in any organizational directory"
4. Save and wait 5 minutes

### ❌ Issue: Redirect URI mismatch

**Cause:** Redirect URI in Azure AD doesn't match `REDIRECT_URI` in `.env`

**Solution:**
1. Check `.env`: `REDIRECT_URI=http://localhost:8000`
2. Azure Portal → App registrations → Authentication
3. Add redirect URI: `http://localhost:8000`
4. Save

### ❌ Issue: Tenant ID is "unknown"

**Cause:** JWT token doesn't contain tenant ID or extraction failed

**Solution:**
1. Check console logs for extraction errors
2. Verify user successfully authenticated
3. Check if `get_user_tenant_id()` function is working

---

## Success Criteria

✅ **All tests pass if:**
1. ✅ Drew can authenticate successfully
2. ✅ Other Excel file users can authenticate
3. ✅ Tenant ID is correctly extracted
4. ✅ Agent initializes correctly
5. ✅ No authentication errors in console
6. ✅ Application loads and functions normally

---

## Quick Test Script

```bash
#!/bin/bash
echo "🧪 Testing Multi-Tenant Authentication Setup..."
echo ""

echo "1. Checking .env file..."
if grep -q "USER_TENANT_ID=organizations" .env; then
    echo "   ✅ USER_TENANT_ID is set to 'organizations'"
else
    echo "   ❌ USER_TENANT_ID is NOT set correctly"
    exit 1
fi

echo ""
echo "2. Checking required packages..."
python -c "import msal; import streamlit; print('   ✅ Required packages installed')" || echo "   ❌ Missing packages"

echo ""
echo "3. Starting application..."
echo "   Open http://localhost:8000 in your browser"
echo "   Test with: Drew@navpayroll.onmicrosoft.com"
echo ""
streamlit run app.py
```

Save as `test_auth.sh`, then:
```bash
chmod +x test_auth.sh
./test_auth.sh
```

---

## Post-Testing

After successful testing:

1. ✅ Remove any debug print statements
2. ✅ Verify all tests pass
3. ✅ Document any issues found
4. ✅ Ready to push to production

---

**Ready to test? Start with Test 1! 🚀**

