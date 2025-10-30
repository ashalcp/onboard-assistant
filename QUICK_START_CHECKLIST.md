# ✅ Quick Start Checklist - Get Data Flowing to Logic App

Follow these steps in order to enable employee data submission to Logic App.

---

## 📋 Pre-Flight Check

- [x] **Code changes applied** (already done)
- [ ] **Create/Update Logic App** (you need to do this)
- [ ] **Update .env file** (you need to do this)  
- [ ] **Configure Azure AI Agent** (you need to do this)
- [ ] **Test end-to-end** (after above steps)

---

## Step 1: Create Logic App for Data Submission (5 minutes)

### Option A: Create New Logic App

1. **Azure Portal** → Logic Apps → **+ Create**
2. **Name:** `employee-data-submission`
3. **Region:** Same as other resources
4. **Plan:** Consumption (Standard)
5. Click **Review + Create**

### Option B: Add Workflow to Existing Logic App

1. Go to your existing `on-boarding` Logic App
2. Click **Workflows** → **+ Add**
3. **Name:** `submit-employee-data`
4. **Type:** Stateful

### Configure the Workflow:

1. Open the workflow → **Designer**

2. **Add Trigger:** "When a HTTP request is received"
   - Method: **POST**
   - Click "Use sample payload to generate schema"
   - Paste this (or use schema from `FUNCTION_CALLING_SETUP_GUIDE.md`):

   ```json
   {
     "tenantId": "abc-123",
     "userEmail": "user@company.com",
     "employee": {
       "firstName": "John",
       "lastName": "Doe",
       "email": "john@company.com",
       "startDate": "01/01/2025",
       "address": {
         "street": "123 Main St",
         "city": "City",
         "state": "CA",
         "zipCode": "12345"
       }
     },
     "paymentInfo": {
       "directDeposit": true
     },
     "w4Info": {
       "filingStatus": "Single"
     },
     "signature": {
       "signatureBase64": "base64string",
       "signatureCollected": true
     }
   }
   ```

3. **Add Action:** Choose where to save data
   - **Excel Online:** "Add a row into a table"
   - **SharePoint:** "Create item"
   - **SQL:** "Insert row"
   - **Cosmos DB:** "Create or update document"

4. **Add Response Action:**
   - Status code: `200`
   - Body:
   ```json
   {
     "success": true,
     "message": "Data received successfully"
   }
   ```

5. **Save** the workflow

6. **Copy the HTTP POST URL** (top of the trigger box)

---

## Step 2: Update .env File (1 minute)

1. Open `/Users/cpashal/Downloads/final/.env` (create from `env_template.txt` if needed)

2. Add this line (paste your Logic App URL):

```bash
LOGIC_APP_SUBMIT_URL=https://prod-XX.logic.azure.com:443/workflows/YOUR_WORKFLOW_ID/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=YOUR_SIGNATURE
```

3. **Save** the file

---

## Step 3: Configure Azure AI Agent (5 minutes)

### 3A: Add Function Tool

1. Go to **https://ai.azure.com**
2. Navigate to your **Project** → **Agents**
3. Click your **employee onboarding agent**
4. Go to **Tools** tab → **+ Add tool** → **Function**
5. **Copy the entire JSON** from `FUNCTION_CALLING_SETUP_GUIDE.md` (section "Step 3: Configure Azure AI Agent Function Tool")
6. **Paste** into the function definition
7. **Save**

### 3B: Update Instructions

1. Still in agent settings, go to **Instructions** tab
2. **Replace** with content from `AGENT_INSTRUCTIONS_UPDATE.md`
3. **Key addition:** Section 6 tells agent to call `submit_employee_onboarding` function
4. **Save**

---

## Step 4: Test Everything (10 minutes)

### Start the App:

```bash
cd /Users/cpashal/Downloads/final
streamlit run app.py
```

### Complete Onboarding:

1. **Log in** with Azure
2. **Chat with agent** - provide all info:
   - Name: "John Doe"
   - Email: "john@test.com"  
   - Start date: "01/15/2025"
   - Address, payment info, W4 details
3. **Confirm** information
4. **Sign** when prompted
5. **Wait** for confirmation message

### Verify Success:

**In Terminal/Console:**
```
🔧 Agent requested function call!
📞 Calling function: submit_employee_onboarding
📤 Submitting employee data to Logic App...
   Employee: John Doe
✅ SUCCESS: Data submitted to Logic App (Status: 200)
```

**In Azure Portal:**
1. Go to Logic App → **Run History**
2. Click **most recent run**
3. Expand **"When a HTTP request is received"**
4. Check **Body** - should show all employee data including signature!

---

## 🐛 Quick Troubleshooting

### ❌ "YOUR_SECOND_LOGIC_APP_URL_HERE"
**Fix:** You forgot Step 2. Add `LOGIC_APP_SUBMIT_URL` to `.env`

### ❌ No function call in console
**Fix:** You forgot Step 3A. Add function tool in Azure AI Foundry

### ❌ Agent doesn't call function
**Fix:** You forgot Step 3B. Update agent instructions

### ❌ HTTP 404 error
**Fix:** Logic App URL in `.env` is incorrect. Copy again from Azure Portal

### ❌ HTTP 400 error  
**Fix:** Logic App schema doesn't match data. Use the schema from the guide

---

## 📊 Expected Results

### Before Fix:
- ❌ No entries in Logic App run history
- ❌ Data stays in chat only

### After Fix:
- ✅ New entry appears in Logic App run history
- ✅ Entry contains full employee data + signature
- ✅ Data saved to your destination (Excel/DB/etc.)
- ✅ User sees success message

---

## 📚 More Help

- **Detailed guide:** `FUNCTION_CALLING_SETUP_GUIDE.md`
- **What changed:** `CHANGES_SUMMARY.md`  
- **Agent instructions:** `AGENT_INSTRUCTIONS_UPDATE.md`
- **Function tool JSON:** In `FUNCTION_CALLING_SETUP_GUIDE.md`

---

## ⏱️ Time Estimate

- Logic App setup: **5 minutes**
- .env update: **1 minute**
- Agent configuration: **5 minutes**
- Testing: **10 minutes**
- **Total: ~20 minutes**

---

## 🎉 Success Criteria

You'll know it's working when:

1. ✅ Console shows "📤 Submitting employee data to Logic App..."
2. ✅ Console shows "✅ SUCCESS: Data submitted to Logic App"
3. ✅ Logic App run history has new entry with your test data
4. ✅ Agent says "Your onboarding information has been successfully submitted"

---

**Ready to start? Begin with Step 1! 🚀**

