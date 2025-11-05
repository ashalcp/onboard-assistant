# Tenant Authentication Error - Fix Guide

## Problem Description

**Error Message:**
> "Selected user account does not exist in tenant 'Integrated Apps LLC' and cannot access the application 'd036a434-eb77-4063-9595-681f0a8fe5b0' in that tenant. The account needs to be added as an external user in the tenant first."

**User Affected:**
- Name: Drew Winborn
- Email: Drew@navpayroll.onmicrosoft.com

## Root Cause

The application was configured to authenticate users from a **specific tenant** (`USER_TENANT_ID`), but the user attempting to log in belongs to a **different tenant** (`navpayroll.onmicrosoft.com`). This creates a tenant mismatch error.

### Technical Details:
1. The code was using: `AUTHORITY = f"https://login.microsoftonline.com/{USER_TENANT_ID}"`
2. This forces authentication to a specific tenant
3. Users from other tenants (like `navpayroll.onmicrosoft.com`) cannot authenticate

## Solution

The code has been updated to support **multi-tenant authentication**. You now have three options:

### Option 1: Multi-Tenant (Recommended for External Users)
Set `USER_TENANT_ID` to one of these values:
- **`organizations`** - Allows any work/school account from any Azure AD tenant
- **`common`** - Allows any Microsoft account (personal + work/school)

**Recommended for your use case:** Use `organizations` to allow users from any organization tenant.

### Option 2: Single Tenant (Specific Organization Only)
Set `USER_TENANT_ID` to a specific tenant ID (e.g., `12345678-1234-1234-1234-123456789abc`)
- Only users from that specific tenant can authenticate
- External users must be added as guests to that tenant

### Option 3: Add External User (Alternative)
If you want to keep single-tenant mode, add the user as an external/guest user in Azure AD:
1. Go to Azure Portal → Azure Active Directory → Users
2. Click "New guest user"
3. Add `Drew@navpayroll.onmicrosoft.com`
4. Assign necessary permissions

## Configuration Steps

### Step 1: Update Environment Variable

In your `.env` file, change:
```bash
# Before (single tenant)
USER_TENANT_ID=your_specific_tenant_id_here

# After (multi-tenant - recommended)
USER_TENANT_ID=organizations
```

### Step 2: Verify Azure AD App Registration

Ensure your Azure AD app registration supports multi-tenant:

1. Go to Azure Portal → Azure Active Directory → App registrations
2. Select your app (Client ID: `d036a434-eb77-4063-9595-681f0a8fe5b0`)
3. Go to **Authentication**
4. Under **Supported account types**, ensure one of these is selected:
   - ✅ "Accounts in any organizational directory and personal Microsoft accounts"
   - ✅ "Accounts in any organizational directory"
5. If it's set to "Single tenant", change it to multi-tenant

### Step 3: Update API Permissions (if needed)

Ensure your app has the necessary permissions:
- `User.Read` (Delegated)
- `User.Read.All` (Delegated or Application)
- `Organization.Read.All` (Delegated or Application)

### Step 4: Test Authentication

1. Restart your application
2. Try logging in with `Drew@navpayroll.onmicrosoft.com`
3. The user should now be able to authenticate successfully

## Code Changes Made

The following changes were made to `app.py`:

1. **Updated Authority Configuration** (lines 81-88):
   - Now supports `"common"`, `"organizations"`, or specific tenant ID
   - Automatically handles multi-tenant vs single-tenant scenarios

2. **Updated Environment Template** (`env_template.txt`):
   - Added documentation for `USER_TENANT_ID` options
   - Set default to `"organizations"` for multi-tenant support

## Verification

After making these changes, verify:
- ✅ Users from different tenants can authenticate
- ✅ The application still works for existing users
- ✅ Tenant ID is correctly extracted from tokens (for routing to correct agent)

## Troubleshooting

### If users still can't authenticate:
1. **Check Azure AD App Registration:**
   - Ensure "Supported account types" is set to multi-tenant
   - Verify redirect URI matches your application URL

2. **Check Environment Variables:**
   - Confirm `USER_TENANT_ID=organizations` in `.env` file
   - Restart the application after changes

3. **Check User Account:**
   - Verify the user account exists and is active
   - Check if there are any conditional access policies blocking access

4. **Review Logs:**
   - Check application logs for authentication errors
   - Review Azure AD sign-in logs for detailed error information

## Additional Notes

- The `AZURE_AI_TENANT_ID` remains separate and is used for Azure AI Project access (not user authentication)
- Multi-tenant authentication allows users from any Azure AD tenant to authenticate
- You can still restrict access using conditional access policies or application-level authorization

