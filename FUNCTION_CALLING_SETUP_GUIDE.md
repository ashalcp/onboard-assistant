# 🔧 Function Calling Setup Guide - Employee Data Submission

## Overview

This guide explains how to configure your Azure AI Agent to submit employee onboarding data to Logic Apps using **Function Calling**. The implementation allows the agent to automatically send collected data to your backend when the onboarding process is complete.

---

## 📋 What Was Changed

### 1. **New Function: `submit_employee_onboarding()` (Line 769)**

This function is called by the Azure AI Agent when it has collected all employee data and signature. It:
- Builds a complete payload with employee, payment, W4, and signature data
- Sends the data to your Logic App via HTTP POST
- Returns success/failure status to the agent

### 2. **Enhanced: `send_message_to_agent()` (Line 1036)**

Updated to handle function calls from the agent:
- Detects when agent status is `requires_action`
- Extracts function name and arguments
- Calls the appropriate Python function
- Returns results back to the agent

### 3. **New Function: `send_signature_data_to_agent()` (Line 1116)**

Sends a notification to the agent when signature is collected, prompting it to proceed with data submission.

### 4. **Updated: `env_template.txt`**

Added `LOGIC_APP_SUBMIT_URL` environment variable for the data submission endpoint.

---

## 🚀 Setup Instructions

### Step 1: Create Logic App for Data Submission

1. **Go to Azure Portal** → Logic Apps
2. **Create new Logic App** or add new workflow to existing:
   - Name: `employee-data-submission`
   - Region: Same as your other resources

3. **Configure HTTP Trigger:**
   - Trigger type: "When a HTTP request is received"
   - Method: POST
   - Schema: Use the JSON schema below

#### Request Body Schema for Logic App

```json
{
  "type": "object",
  "properties": {
    "tenantId": {
      "type": "string"
    },
    "userEmail": {
      "type": "string"
    },
    "employee": {
      "type": "object",
      "properties": {
        "firstName": {
          "type": "string"
        },
        "middleName": {
          "type": "string"
        },
        "lastName": {
          "type": "string"
        },
        "email": {
          "type": "string"
        },
        "employee_id": {
          "type": "string"
        },
        "departmentCode": {
          "type": "string"
        },
        "ethnicity": {
          "type": "string"
        },
        "startDate": {
          "type": "string"
        },
        "address": {
          "type": "object",
          "properties": {
            "street": {
              "type": "string"
            },
            "city": {
              "type": "string"
            },
            "state": {
              "type": "string"
            },
            "zipCode": {
              "type": "string"
            }
          }
        }
      }
    },
    "paymentInfo": {
      "type": "object",
      "properties": {
        "payrollDivisionCode": {
          "type": "string"
        },
        "directDeposit": {
          "type": "boolean"
        },
        "bankAccountNumber": {
          "type": "string"
        },
        "routingNumber": {
          "type": "string"
        }
      }
    },
    "w4Info": {
      "type": "object",
      "properties": {
        "filingStatus": {
          "type": "string"
        },
        "qualifyingChildrenDependents": {
          "type": "integer"
        },
        "otherDependents": {
          "type": "integer"
        },
        "multipleJobs": {
          "type": "boolean"
        },
        "extraWithholding": {
          "type": "boolean"
        },
        "extraWithholdingAmount": {
          "type": "integer"
        },
        "otherIncome": {
          "type": "integer"
        },
        "deductionsAmount": {
          "type": "integer"
        }
      }
    },
    "signature": {
      "type": "object",
      "properties": {
        "signatureBase64": {
          "type": "string"
        },
        "signatureTimestamp": {
          "type": "number"
        },
        "signatureFormat": {
          "type": "string"
        },
        "signatureCollected": {
          "type": "boolean"
        }
      }
    }
  }
}
```

4. **Add Actions** to process the data:
   - Option A: Add row to Excel/SharePoint
   - Option B: Insert into SQL Database
   - Option C: Store in Azure Cosmos DB
   - Option D: Forward to another API

5. **Add Response Action:**
   ```json
   {
     "success": true,
     "message": "Employee data received successfully"
   }
   ```

6. **Save** and copy the **HTTP POST URL**

---

### Step 2: Update Environment Variables

1. Open your `.env` file (or create from `env_template.txt`)

2. Add the Logic App URL:

```bash
# Logic App URL for submitting employee onboarding data
LOGIC_APP_SUBMIT_URL=https://prod-XX.logic.azure.com:443/workflows/YOUR_WORKFLOW_ID/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=YOUR_SIGNATURE
```

Replace with your actual Logic App HTTP POST URL from Step 1.

---

### Step 3: Configure Azure AI Agent Function Tool

1. **Go to Azure AI Foundry** (https://ai.azure.com)

2. **Navigate to your project** → Agents

3. **Select your employee onboarding agent** → Edit

4. **Go to Tools section** → Add Tool → Function

5. **Add the following function definition:**

```json
{
  "type": "function",
  "function": {
    "name": "submit_employee_onboarding",
    "description": "Submit collected employee onboarding data to the system. Call this function ONLY after the signature has been collected and user has confirmed all their information is correct. This function sends all collected data including employee details, payment information, W4 tax form data, and digital signature to the backend system for processing.",
    "parameters": {
      "type": "object",
      "properties": {
        "employee": {
          "type": "object",
          "description": "Employee personal information",
          "properties": {
            "firstName": {
              "type": "string",
              "description": "Employee's first name"
            },
            "middleName": {
              "type": "string",
              "description": "Employee's middle name (can be empty string)"
            },
            "lastName": {
              "type": "string",
              "description": "Employee's last name"
            },
            "email": {
              "type": "string",
              "description": "Employee's email address"
            },
            "employee_id": {
              "type": "string",
              "description": "Employee ID (can be empty if not provided)"
            },
            "departmentCode": {
              "type": "string",
              "description": "Department code"
            },
            "ethnicity": {
              "type": "string",
              "description": "Ethnicity (optional)"
            },
            "startDate": {
              "type": "string",
              "description": "Start date in MM/DD/YYYY format"
            },
            "address": {
              "type": "object",
              "description": "Employee's address",
              "properties": {
                "street": {
                  "type": "string"
                },
                "city": {
                  "type": "string"
                },
                "state": {
                  "type": "string"
                },
                "zipCode": {
                  "type": "string"
                }
              },
              "required": ["street", "city", "state", "zipCode"]
            }
          },
          "required": ["firstName", "lastName", "email", "startDate", "address"]
        },
        "paymentInfo": {
          "type": "object",
          "description": "Payment and direct deposit information",
          "properties": {
            "payrollDivisionCode": {
              "type": "string",
              "description": "Payroll division code (can be empty)"
            },
            "directDeposit": {
              "type": "boolean",
              "description": "Whether direct deposit is enabled"
            },
            "bankAccountNumber": {
              "type": "string",
              "description": "Bank account number (required if directDeposit is true)"
            },
            "routingNumber": {
              "type": "string",
              "description": "Bank routing number (required if directDeposit is true)"
            }
          },
          "required": ["directDeposit"]
        },
        "w4Info": {
          "type": "object",
          "description": "W4 tax form information",
          "properties": {
            "filingStatus": {
              "type": "string",
              "description": "Tax filing status (Single or Married filing separately, Married filing jointly, Head of household)",
              "enum": ["Single or Married filing separately", "Married filing jointly", "Head of household"]
            },
            "qualifyingChildrenDependents": {
              "type": "integer",
              "description": "Number of qualifying children dependents"
            },
            "otherDependents": {
              "type": "integer",
              "description": "Number of other dependents"
            },
            "multipleJobs": {
              "type": "boolean",
              "description": "Whether employee has multiple jobs"
            },
            "extraWithholding": {
              "type": "boolean",
              "description": "Whether extra withholding is requested"
            },
            "extraWithholdingAmount": {
              "type": "integer",
              "description": "Extra withholding amount per paycheck (0 if extraWithholding is false)"
            },
            "otherIncome": {
              "type": "integer",
              "description": "Other income amount (0 if none)"
            },
            "deductionsAmount": {
              "type": "integer",
              "description": "Deductions amount (0 if none)"
            }
          },
          "required": ["filingStatus", "qualifyingChildrenDependents", "otherDependents", "multipleJobs", "extraWithholding", "extraWithholdingAmount", "otherIncome", "deductionsAmount"]
        }
      },
      "required": ["employee", "paymentInfo", "w4Info"]
    }
  }
}
```

6. **Save the function tool**

---

### Step 4: Update Agent Instructions

Update your agent instructions in Azure AI Foundry to include function calling guidance. Add this section after the signature collection step:

```markdown
### 6. **CRITICAL: Form Submission Using Function Tool**

**After signature is collected and confirmed, you MUST call the `submit_employee_onboarding` function tool to submit all data.**

Call the function with this structure:

- Convert all "yes/no" responses to boolean (true/false)
- Convert all numeric values to integers (no strings)
- Use empty string "" for optional fields not provided
- Ensure all required fields are present

**Function Calling Rules:**
1. DO NOT call function until signature is confirmed collected
2. ALWAYS call `submit_employee_onboarding` after signature confirmation
3. Use exact field names as specified
4. The function will automatically include tenantId, userEmail, and signature data

### 7. Confirmation Message

After successful function call:
"✅ Thank you! Your onboarding information has been successfully submitted. You should receive a confirmation email shortly. Welcome aboard!"

If function call fails:
"❌ I apologize, but there was an issue submitting your information. Please contact HR for assistance. Your information has been saved and we'll resolve this shortly."
```

---

## 🧪 Testing the Implementation

### Test 1: Verify Function is Registered

1. In Azure AI Foundry, check that `submit_employee_onboarding` appears in the agent's Tools list
2. Verify all parameters are correctly configured

### Test 2: End-to-End Onboarding

1. Start your Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Log in with Azure authentication

3. Complete the onboarding conversation:
   - Provide all employee details
   - Provide payment information
   - Complete W4 form
   - Confirm all information
   - Provide signature

4. **Watch for these signs of success:**
   - Console logs: `📤 Submitting employee data to Logic App...`
   - Console logs: `✅ SUCCESS: Data submitted to Logic App`
   - Agent response: "Your onboarding information has been successfully submitted"
   - **Logic App Run History shows new run with your data**

### Test 3: Verify Data in Logic App

1. Go to Azure Portal → Your Logic App
2. Click "Run History"
3. Click the most recent run
4. Expand "When a HTTP request is received"
5. Check the **Body** - you should see:
   ```json
   {
     "tenantId": "...",
     "userEmail": "...",
     "employee": { ... full employee data ... },
     "paymentInfo": { ... },
     "w4Info": { ... },
     "signature": {
       "signatureBase64": "iVBORw0KGgo...",
       "signatureTimestamp": 1234567890,
       "signatureFormat": "PNG",
       "signatureCollected": true
     }
   }
   ```

---

## 🐛 Troubleshooting

### Issue: Agent doesn't call the function

**Symptoms:** Conversation ends but no data appears in Logic App

**Solutions:**
1. Verify function tool is added to agent in Azure AI Foundry
2. Check agent instructions explicitly tell it to call the function after signature
3. Ensure signature was collected (`st.session_state.signature_data` is not None)
4. Check console logs for `🔧 Agent requested function call!`

### Issue: Function call fails

**Symptoms:** Console shows `❌ ERROR: Logic App returned 4xx/5xx`

**Solutions:**
1. Verify `LOGIC_APP_SUBMIT_URL` in `.env` is correct
2. Test Logic App URL directly using Postman with sample data
3. Check Logic App is enabled and not suspended
4. Verify Logic App schema matches the data structure

### Issue: Signature data is missing

**Symptoms:** Signature fields are empty in Logic App

**Solutions:**
1. Check that signature was collected before function call
2. Verify `st.session_state.signature_data` contains base64_data
3. Check the `submit_employee_onboarding()` function properly accesses signature data

### Issue: "LOGIC_APP_SUBMIT_URL not found"

**Symptoms:** Error about missing environment variable

**Solutions:**
1. Ensure `.env` file exists in project root
2. Add `LOGIC_APP_SUBMIT_URL=your_url_here` to `.env`
3. Restart Streamlit app after adding variable

---

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User completes onboarding conversation                   │
│    ↓ Provides all info + signature                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Agent receives "[SIGNATURE COLLECTED]" message           │
│    ↓ Agent instructions: Call submit_employee_onboarding    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Azure AI Agent calls function tool                       │
│    ↓ Sends employee, payment, w4 data as JSON               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Streamlit app.py receives function call                  │
│    ↓ send_message_to_agent() detects requires_action        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. submit_employee_onboarding() function executes           │
│    ↓ Builds complete payload with signature data            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. HTTP POST to Logic App (LOGIC_APP_SUBMIT_URL)           │
│    ↓ Sends full JSON with all employee data                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Logic App receives and processes data                    │
│    ↓ Saves to Excel/Database/etc.                           │
│    ↓ Returns success response                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. Function returns result to agent                         │
│    ↓ Agent confirms success to user                         │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Success Checklist

- [ ] Logic App created with correct HTTP trigger schema
- [ ] Logic App URL copied to `.env` as `LOGIC_APP_SUBMIT_URL`
- [ ] Function tool added to Azure AI Agent in AI Foundry
- [ ] Agent instructions updated to call function after signature
- [ ] Streamlit app restarted to load new environment variables
- [ ] Test run completed successfully
- [ ] Data appears in Logic App run history
- [ ] Data stored in final destination (Excel/DB/etc.)

---

## 📚 Additional Resources

- [Azure AI Projects Function Calling](https://learn.microsoft.com/en-us/azure/ai-services/)
- [Azure Logic Apps HTTP Triggers](https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-http-endpoint)
- [Streamlit Session State](https://docs.streamlit.io/library/api-reference/session-state)

---

**Last Updated:** October 2025  
**Version:** 1.0  
**Status:** Production Ready ✅

