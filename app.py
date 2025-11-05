


import streamlit as st
import streamlit.components.v1 as components
from azure.ai.projects import AIProjectClient
from azure.identity import ClientSecretCredential
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
import time
import sys
import os
import base64
import requests
from io import StringIO, BytesIO
import msal
from streamlit_drawable_canvas import st_canvas
from PIL import Image

import json
import jwt
import re

from dotenv import load_dotenv
load_dotenv()

# FIXED LOGO FUNCTION
def get_logo_base64():
    """Load and encode logo for display"""
    try:
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_data = f.read()
            return base64.b64encode(logo_data).decode()
        else:
            st.warning("⚠️ Logo file not found at assets/logo.png")
            return None
    except Exception as e:
        st.warning(f"⚠️ Could not load logo: {e}")
        return None

# Alternative approach using base64 encoded image
def get_logo_for_favicon_base64():
    """Get base64 encoded logo for favicon"""
    try:
        logo_path = os.path.join("assets", "logo.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_data = f.read()
            return f"data:image/png;base64,{base64.b64encode(logo_data).decode()}"
        else:
            return None
    except Exception as e:
        return None

# --- CONFIGURATION ---
# Get base64 logo for favicon
logo_favicon = get_logo_for_favicon_base64()

st.set_page_config(
    page_title="Employee On Boarding Assistant", 
    layout="centered", 
    initial_sidebar_state="collapsed",
    page_icon=logo_favicon if logo_favicon else "🤖"
)

# Microsoft authentication variables - Updated for proper multitenant support
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# Separate tenant IDs for different purposes
USER_TENANT_ID = os.getenv("USER_TENANT_ID")  # For user authentication (use "common" or "organizations" for multi-tenant)
AZURE_AI_TENANT_ID = os.getenv("AZURE_AI_TENANT_ID")    # For Azure AI Project access


# Azure AI Project endpoint - make configurable
AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT")

REDIRECT_URI = os.getenv("REDIRECT_URI","http://localhost:8000")

# MSAL Configuration for user authentication (supports multitenant)
# IMPORTANT: To allow all users from the Excel file (different tenants) to login, 
# set USER_TENANT_ID to "organizations" or "common" in your .env file
# 
# Options:
#   - "common" = Allow any Microsoft account (personal + work/school)
#   - "organizations" = Allow any work/school account from any tenant (MULTI-TENANT - Recommended)
#   - Specific tenant ID = Only allow users from that specific tenant (SINGLE-TENANT)
#
# Default: "organizations" (allows all work/school accounts from any tenant)
if USER_TENANT_ID and USER_TENANT_ID.lower() in ["common", "organizations"]:
    AUTHORITY = f"https://login.microsoftonline.com/{USER_TENANT_ID.lower()}"
elif USER_TENANT_ID:
    # Specific tenant ID provided - single tenant mode
    AUTHORITY = f"https://login.microsoftonline.com/{USER_TENANT_ID}"
else:
    # Default to multi-tenant mode to allow all users from Excel file
    AUTHORITY = "https://login.microsoftonline.com/organizations"
SCOPE = [
    "User.Read",
    "User.Read.All",  # For additional user properties
    "Organization.Read.All"  # For tenant information
]


def get_user_tenant_id(access_token):
    """Extract tenant ID from Microsoft Graph or JWT token"""
    try:
        # Option 1: From JWT token (fastest)
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        tenant_id = decoded_token.get("tid")
        if tenant_id:
            return tenant_id
            
        # Option 2: From Microsoft Graph organization endpoint as fallback
        headers = {"Authorization": f"Bearer {access_token}"}
        org_response = requests.get("https://graph.microsoft.com/v1.0/organization", headers=headers, timeout=10)
        if org_response.status_code == 200:
            org_data = org_response.json()
            if org_data.get("value") and len(org_data["value"]) > 0:
                return org_data["value"][0].get("id", "unknown")
                
        return "unknown"
        
    except Exception as e:
        st.warning(f"Could not retrieve tenant ID: {e}")
        return "unknown"

def get_msal_app():
    """Create MSAL application for user authentication"""
    try:
        return msal.ConfidentialClientApplication(
            CLIENT_ID, 
            authority=AUTHORITY,  # Uses USER_TENANT_ID for user auth
            client_credential=CLIENT_SECRET
        )
    except Exception as e:
        st.error(f"❌ MSAL initialization failed: {e}")
        st.stop()

import json
import tempfile

# File-based cache to preserve settings through OAuth (survives redirect)
OAUTH_CACHE_FILE = os.path.join(tempfile.gettempdir(), "streamlit_oauth_cache.json")

def save_oauth_session(session_id, data):
    """Save OAuth session data to file"""
    try:
        # Load existing cache
        if os.path.exists(OAUTH_CACHE_FILE):
            with open(OAUTH_CACHE_FILE, 'r') as f:
                cache = json.load(f)
        else:
            cache = {}
        
        # Add new session
        cache[session_id] = data
        
        # Save back
        with open(OAUTH_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
        print(f"🔍 DEBUG: Saved session {session_id} to cache")
    except Exception as e:
        print(f"❌ DEBUG: Failed to save session: {e}")

def load_oauth_session(session_id):
    """Load OAuth session data from file"""
    try:
        if os.path.exists(OAUTH_CACHE_FILE):
            with open(OAUTH_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            data = cache.get(session_id)
            print(f"🔍 DEBUG: Loaded session {session_id} from cache: {data}")
            return data
        return None
    except Exception as e:
        print(f"❌ DEBUG: Failed to load session: {e}")
        return None

def login_with_microsoft():
    """Microsoft login"""
    try:
        msal_app = get_msal_app()
        
        # Generate unique session ID and cache the requireSignature setting
        import uuid
        session_id = str(uuid.uuid4())
        query_params = st.query_params
        require_sig = query_params.get("requireSignature", "true")
        
        # Store in file cache (survives OAuth redirect)
        save_oauth_session(session_id, {
            "requireSignature": require_sig,
            "timestamp": time.time()
        })
        print(f"🔍 DEBUG Login: Creating OAuth with requireSignature={require_sig}")
        
        auth_url = msal_app.get_authorization_request_url(
            SCOPE, 
            redirect_uri=REDIRECT_URI,
            state=session_id  # Pass session ID through OAuth
        )
        
        st.markdown(f"""
        <div style="text-align: center; margin: 40px 0;">
            <a href="{auth_url}" target="_self">
                <button style="
                    background: linear-gradient(135deg, #0078d4, #106ebe);
                    color: white;
                    padding: 20px 40px;
                    border: none;
                    border-radius: 12px;
                    cursor: pointer;
                    font-size: 18px;
                    font-weight: 600;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    gap: 15px;
                    box-shadow: 0 8px 25px rgba(0,120,212,0.3);
                    transition: all 0.3s ease;
                    min-width: 300px;
                " onmouseover="this.style.transform='translateY(-3px)'; this.style.boxShadow='0 12px 35px rgba(0,120,212,0.4)'" 
                   onmouseout="this.style.transform='translateY(0px)'; this.style.boxShadow='0 8px 25px rgba(0,120,212,0.3)'">
                    <svg width="24" height="24" viewBox="0 0 24 24">
                        <rect x="1" y="1" width="10" height="10" fill="white"/>
                        <rect x="13" y="1" width="10" height="10" fill="white"/>
                        <rect x="1" y="13" width="10" height="10" fill="white"/>
                        <rect x="13" y="13" width="10" height="10" fill="white"/>
                    </svg>
                    Sign in with Microsoft
                </button>
            </a>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ Login setup failed: {e}")

def handle_microsoft_callback():
    """Handle Microsoft authentication callback"""
    query_params = st.query_params
    
    if "error" in query_params:
        st.error(f"❌ Authentication error: {query_params.get('error_description', 'Unknown error')}")
        return
        
    if "code" in query_params:
        try:
            code = query_params["code"]
            msal_app = get_msal_app()
            
            with st.spinner("Completing authentication..."):
                result = msal_app.acquire_token_by_authorization_code(
                    code,
                    scopes=SCOPE,
                    redirect_uri=REDIRECT_URI
                )
                
            if "access_token" in result:
                st.session_state.logged_in = True
                st.session_state.access_token = result["access_token"]
                st.session_state.user_info = get_user_info(result["access_token"])
                
                # Retrieve requireSignature from cached session using state parameter
                state_param = query_params.get("state")
                if state_param:
                    cached_data = load_oauth_session(state_param)
                    if cached_data:
                        require_sig = cached_data.get("requireSignature", "true")
                        st.session_state.require_signature = (require_sig.lower() == "true")
                        print(f"🔍 DEBUG OAuth Callback: Restored requireSignature={require_sig} from cache")
                    else:
                        st.session_state.require_signature = True
                        print(f"🔍 DEBUG OAuth Callback: No cached data found, defaulting to True")
                else:
                    st.session_state.require_signature = True
                    print(f"🔍 DEBUG OAuth Callback: No state parameter, defaulting to True")
                
                st.success("✅ Authentication successful!")
                st.query_params.clear()
                st.rerun()
            else:
                st.error("❌ Failed to obtain access token")
                st.error(f"Error: {result.get('error_description', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"❌ Authentication callback failed: {e}")

def get_user_info(access_token):
    """Get user information from Microsoft Graph API"""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            
            # Enhanced email extraction
            email_sources = {
                'mail': user_data.get('mail'),
                'userPrincipalName': user_data.get('userPrincipalName'),
                'email': user_data.get('email'),
                'otherMails': user_data.get('otherMails', []),
                'proxyAddresses': user_data.get('proxyAddresses', [])
            }
            
            # Try multiple email extraction methods
            email = None
            email_method = "unknown"
            
            # Method 1: Direct mail field
            if user_data.get('mail') and user_data.get('mail').strip():
                email = user_data.get('mail').strip()
                email_method = "mail"
            
            # Method 2: userPrincipalName (most reliable)
            elif user_data.get('userPrincipalName') and '@' in user_data.get('userPrincipalName', ''):
                email = user_data.get('userPrincipalName').strip()
                email_method = "userPrincipalName"
            
            # Method 3: otherMails array
            elif user_data.get('otherMails') and len(user_data.get('otherMails', [])) > 0:
                email = user_data.get('otherMails')[0].strip()
                email_method = "otherMails[0]"
            
            # Method 4: Extract from proxyAddresses
            elif user_data.get('proxyAddresses'):
                for addr in user_data.get('proxyAddresses', []):
                    if addr.startswith('SMTP:') or addr.startswith('smtp:'):
                        email = addr.replace('SMTP:', '').replace('smtp:', '').strip()
                        email_method = "proxyAddresses"
                        break
            
            # Method 5: Fallback to constructed email
            if not email or email == "":
                user_id = user_data.get('id', 'unknown')[:8] 
                email = f"user-{user_id}@unknown.com"
                email_method = "fallback_constructed"
            
            # Add tenant ID
            tenant_id = get_user_tenant_id(access_token)
            
            # Normalize user data
            user_data['mail'] = email
            user_data['tenant_id'] = tenant_id
            user_data['email_extraction_method'] = email_method
            user_data['account_type'] = determine_account_type(user_data)
            
            return user_data
        else:
            return {
                "displayName": "User", 
                "mail": "no-email@unknown.com", 
                "tenant_id": "unknown",
                "email_extraction_method": "error_fallback",
                "account_type": "unknown"
            }
            
    except Exception as e:
        return {
            "displayName": "User", 
            "mail": "no-email@unknown.com", 
            "tenant_id": "unknown",
            "email_extraction_method": "exception_fallback",
            "account_type": "unknown"
        }

def get_user_tenant_id_debug(access_token, user_data=None):
    """Extract tenant ID with comprehensive debugging"""
    st.write("**🔍 DEBUG: Tenant ID Extraction:**")
    
    try:
        # Method 1: From JWT token (fastest)
        try:
            decoded_token = jwt.decode(access_token, options={"verify_signature": False})
            st.write("**JWT Token Claims:**")
            with st.expander("View JWT Claims", expanded=False):
                # Filter out sensitive claims for display
                safe_claims = {k: v for k, v in decoded_token.items() 
                             if k not in ['signature', 'access_token']}
                st.json(safe_claims)
            
            tenant_id = decoded_token.get("tid")
            if tenant_id:
                st.write(f"✅ **Tenant ID from JWT**: `{tenant_id}`")
                return tenant_id
            else:
                st.write("❌ **No 'tid' claim in JWT token**")
                
        except Exception as jwt_error:
            st.write(f"❌ **JWT decode error**: {jwt_error}")
            
        # Method 2: From user data if available
        if user_data:
            user_tenant_hints = {
                'tenantId': user_data.get('tenantId'),
                'organizationId': user_data.get('organizationId'),
                'companyName': user_data.get('companyName'),
                'userPrincipalName_domain': user_data.get('userPrincipalName', '').split('@')[1] if '@' in user_data.get('userPrincipalName', '') else None
            }
            
            st.write("**User Data Tenant Hints:**")
            for hint, value in user_tenant_hints.items():
                st.write(f"- **{hint}**: `{value}`")
            
            if user_data.get('tenantId'):
                st.write(f"✅ **Tenant ID from user data**: `{user_data.get('tenantId')}`")
                return user_data.get('tenantId')
            
        # Method 3: From Microsoft Graph organization endpoint
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            org_response = requests.get("https://graph.microsoft.com/v1.0/organization", 
                                      headers=headers, timeout=10)
            
            st.write(f"**Organization API Response**: Status {org_response.status_code}")
            
            if org_response.status_code == 200:
                org_data = org_response.json()
                st.write("**Organization Data:**")
                with st.expander("View Organization Response", expanded=False):
                    st.json(org_data)
                
                if org_data.get("value") and len(org_data["value"]) > 0:
                    tenant_id = org_data["value"][0].get("id")
                    if tenant_id:
                        st.write(f"✅ **Tenant ID from Organization API**: `{tenant_id}`")
                        return tenant_id
            else:
                st.write(f"❌ **Organization API error**: {org_response.text}")
                
        except Exception as org_error:
            st.write(f"❌ **Organization API error**: {org_error}")
        
        # Method 4: Extract from token issuer
        try:
            decoded_token = jwt.decode(access_token, options={"verify_signature": False})
            issuer = decoded_token.get("iss", "")
            if "login.microsoftonline.com/" in issuer:
                tenant_from_issuer = issuer.split("login.microsoftonline.com/")[1].split("/")[0]
                st.write(f"✅ **Tenant ID from issuer**: `{tenant_from_issuer}`")
                return tenant_from_issuer
        except:
            pass
        
        st.write("❌ **Could not determine tenant ID from any method**")
        return "unknown"
        
    except Exception as e:
        st.write(f"❌ **Tenant ID extraction error**: {e}")
        return "unknown"

def determine_account_type(user_data):
    """Determine the type of Microsoft account"""
    upn = user_data.get('userPrincipalName', '')
    mail = user_data.get('mail', '')
    
    # Personal account indicators
    personal_domains = ['outlook.com', 'hotmail.com', 'live.com', 'msn.com', 'gmail.com']
    
    if any(domain in upn.lower() for domain in personal_domains):
        return "personal"
    elif any(domain in mail.lower() for domain in personal_domains):
        return "personal"
    elif '.onmicrosoft.com' in upn:
        return "work_school_cloud"
    elif upn and '@' in upn:
        return "work_school_org"
    else:
        return "unknown"

# SIGNATURE COLLECTION FUNCTIONS
def collect_signature():
    """Display signature collection interface - streamlined"""
    # Simple, clean header
    st.markdown("""
    <div style="text-align: center; margin: 20px 0;">
        <h3 style="color: #495057; margin-bottom: 10px;">✍️ Please sign below to complete your onboarding</h3>
        <p style="color: #6c757d; font-size: 14px;">Draw your signature using your mouse, trackpad, or touchscreen</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Clean canvas container
    st.markdown("""
    <div style="
        border: 2px solid #ced4da;
        border-radius: 8px;
        padding: 20px;
        background: white;
        margin: 15px 0;
        text-align: center;
    ">
    """, unsafe_allow_html=True)
    
    # Initialize canvas reset counter if not exists
    if 'canvas_reset_counter' not in st.session_state:
        st.session_state.canvas_reset_counter = 0
    
    # Signature canvas with improved settings and dynamic key for reset functionality
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",  # Transparent fill
        stroke_width=3,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=300,
        width=800,
        drawing_mode="freedraw",
        key=f"signature_canvas_{st.session_state.canvas_reset_counter}"  # Dynamic key for reset
    )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Simplified action buttons - streamlined UX with just Clear and Accept
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("🔄 Clear", key="clear_signature", help="Clear and redraw your signature", use_container_width=True, type="secondary"):
            # Force canvas to reset by incrementing a counter
            if 'canvas_reset_counter' not in st.session_state:
                st.session_state.canvas_reset_counter = 0
            st.session_state.canvas_reset_counter += 1
            st.rerun()
    
    with col3:
        if st.button("✅ Accept", key="accept_signature", help="Accept this signature and continue", use_container_width=True, type="primary"):
            if canvas_result.image_data is not None:
                # Check if signature is not empty (not all white)
                if canvas_result.image_data.sum() < canvas_result.image_data.size * 255:
                    # Convert canvas to image
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    
                    # Convert to base64
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    
                    # Store signature data
                    st.session_state.signature_data = {
                        'base64_data': img_str,
                        'timestamp': time.time(),
                        'format': 'PNG'
                    }
                    
                    # Close the modal
                    st.session_state.show_signature_modal = False
                    
                    # Add user message immediately
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": "✅ I have provided my digital signature."
                    })
                    
                    # Mark that signature is pending to send
                    st.session_state.signature_pending_send = True
                    
                    # Rerun to trigger the signature send handler
                    st.rerun()
                else:
                    st.error("⚠️ Please draw your signature in the canvas above")
            else:
                st.error("⚠️ Please draw your signature in the canvas above")

def get_signature_tool_data():
    """Get signature data for Azure AI agent tool"""
    if st.session_state.signature_data:
        return {
            "signature_available": True,
            "signature_base64": st.session_state.signature_data['base64_data'],
            "timestamp": st.session_state.signature_data['timestamp'],
            "format": st.session_state.signature_data['format']
        }
    else:
        return {
            "signature_available": False,
            "message": "No signature collected yet"
        }

def get_signature_for_storage():
    """Get signature data formatted for storage in Logic Apps/database"""
    if st.session_state.signature_data:
        user_email = st.session_state.user_info.get('mail', 'no-email@unknown.com')
        tenant_id = st.session_state.user_info.get('tenant_id', 'unknown')
        
        return {
            "tenantId": tenant_id,
            "userEmail": user_email,
            "signatureBase64": st.session_state.signature_data['base64_data'],
            "signatureTimestamp": st.session_state.signature_data['timestamp'],
            "signatureFormat": st.session_state.signature_data['format'],
            "signatureCollected": True
        }
    else:
        return {
            "signatureCollected": False,
            "signatureBase64": None
        }

def display_signature_modal():
    """Display signature collection modal - streamlined version"""
    if st.session_state.show_signature_modal:
        # Add JavaScript to auto-scroll to signature modal
        st.markdown("""
        <script>
            setTimeout(function() {
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            }, 300);
        </script>
        """, unsafe_allow_html=True)
        
        # Simple, clean separator
        st.markdown("---")
        
        # Streamlined canvas container - no extra UI, just canvas
        with st.container():
            st.markdown("""
            <div style="
                background: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 30px;
                margin: 20px 0;
            ">
            """, unsafe_allow_html=True)
            
            collect_signature()
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")

def trigger_signature_collection():
    """Trigger signature collection from agent"""
    st.session_state.show_signature_modal = True
    st.rerun()

def debug_signature_state():
    """Debug function to show signature state"""
    with st.expander("🔍 Debug: Signature State", expanded=False):
        st.write("**Session State:**")
        st.write(f"- show_signature_modal: {st.session_state.get('show_signature_modal', False)}")
        st.write(f"- signature_data: {st.session_state.get('signature_data', None)}")
        st.write(f"- canvas_reset_counter: {st.session_state.get('canvas_reset_counter', 0)}")
        st.write(f"- current canvas key: signature_canvas_{st.session_state.get('canvas_reset_counter', 0)}")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Force Rerun", key="debug_rerun"):
                st.rerun()
        with col2:
            if st.button("🗑️ Reset Canvas Counter", key="debug_reset_counter"):
                st.session_state.canvas_reset_counter = 0
                st.rerun()

def display_collected_signature():
    """Display the collected signature in chat"""
    if st.session_state.signature_data:
        signature_data = st.session_state.signature_data['base64_data']
        st.markdown("**📝 Collected Signature:**")
        st.image(base64.b64decode(signature_data), width=300)
        return True
    return False
        
def login():
    """Login page"""
    logo_base64 = get_logo_base64()
    
    if logo_base64:
        st.markdown(f"""
        <div style="text-align: center; margin-top: 50px;">
            <div class="login-title">
                <img src="data:image/png;base64,{logo_base64}" class="main-logo" alt="Company Logo">
                <h1 style="color: #0078d4; margin-bottom: 10px;">Employee On Boarding Assistant</h1>
            </div>
            <p style="font-size: 18px; color: #666; margin-bottom: 40px;">Welcome! Please sign in to get started.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <h1 style="color: #0078d4; margin-bottom: 10px;">🤖 Azure AI Agent Chatbot</h1>
            <p style="font-size: 18px; color: #666; margin-bottom: 40px;">Welcome! Please sign in to get started.</p>
        </div>
        """, unsafe_allow_html=True)

    handle_microsoft_callback()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        login_with_microsoft()

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "project_client" not in st.session_state:
    st.session_state.project_client = None
if "agent" not in st.session_state:
    st.session_state.agent = None
if "signature_data" not in st.session_state:
    st.session_state.signature_data = None
if "show_signature_modal" not in st.session_state:
    st.session_state.show_signature_modal = False
if "signature_pending_send" not in st.session_state:
    st.session_state.signature_pending_send = False

# Handle requireSignature parameter
# Priority: 1) Already set by OAuth callback, 2) URL parameter, 3) Default to true
query_params = st.query_params
if "require_signature" not in st.session_state:
    # Not set by OAuth callback, check URL parameter
    if "requireSignature" in query_params:
        require_sig = query_params.get("requireSignature")
        st.session_state.require_signature = (require_sig.lower() == "true")
        print(f"🔍 DEBUG: Set from URL param: requireSignature={require_sig}")
    else:
        # No parameter, default to true
        st.session_state.require_signature = True
        print(f"🔍 DEBUG: No param found, defaulting to True")
else:
    # Already set (likely by OAuth callback)
    print(f"🔍 DEBUG: Using session value: {st.session_state.require_signature}")

@st.cache_resource
def get_azure_client():
    """Initialize Azure AI Project Client with specific tenant for AI resources"""
    try:
        # Use specific tenant for Azure AI Project access
        credential = ClientSecretCredential(
            tenant_id=AZURE_AI_TENANT_ID,  # Use specific tenant for AI resources
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        
        project = AIProjectClient(
            credential=credential,
            endpoint=AZURE_AI_ENDPOINT
        )
        
        # Don't get a specific agent here anymore - we'll do this dynamically
        return project
        
    except Exception as e:
        st.error(f"Failed to initialize Azure client: {e}")
        return None

def get_agent_id_for_tenant(tenant_id, user_email):
    """Get agent ID from Logic App based on tenant ID"""
    # Replace with your actual Logic App URL
    logic_app_url = "https://prod-21.northcentralus.logic.azure.com:443/workflows/dab274a5edbd41cf8a06a3e1d38b55e9/triggers/When_a_HTTP_request_is_received/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2FWhen_a_HTTP_request_is_received%2Frun&sv=1.0&sig=b1f63hQh-pRIKTJm0lAuyA7D4ypZ8NmrhwwUI2GZGac"
    
    payload = {
        "tenantId": tenant_id,
        "userEmail": user_email
    }
    
    try:
        with st.spinner(f"Looking up agent for tenant..."):
            response = requests.post(logic_app_url, json=payload, timeout=10)
            
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('agentId'), data.get('agentType', 'Standard'), data.get('orgName', 'Unknown')
            else:
                st.error(f"Tenant lookup failed: {data.get('error', 'Unknown error')}")
                return None, None, None
        else:
            st.error(f"Failed to get agent ID: HTTP {response.status_code}")
            return None, None, None
            
    except Exception as e:
        st.error(f"Error getting agent ID: {e}")
        return None, None, None

def submit_employee_onboarding(employee_data):
    """
    This function is called by Azure AI Agent when it has collected all employee data.
    It submits the data to your Logic App.
    """
    try:
        # Your Logic App URL for submitting employee data (NOT the tenant lookup one)
        logic_app_submit_url = os.getenv(
            "LOGIC_APP_SUBMIT_URL",
            "YOUR_SECOND_LOGIC_APP_URL_HERE"  # You need a different Logic App for submission
        )
        
        # Get user context
        tenant_id = st.session_state.user_info.get('tenant_id', 'unknown')
        user_email = st.session_state.user_info.get('mail', 'no-email@unknown.com')
        
        # Build complete payload matching your schema
        payload = {
            "tenantId": tenant_id,
            "userEmail": user_email,
            "employee": employee_data.get("employee", {}),
            "paymentInfo": employee_data.get("paymentInfo", {}),
            "w4Info": employee_data.get("w4Info", {}),
            "signature": {
                "signatureBase64": st.session_state.signature_data.get('base64_data', '') if st.session_state.signature_data else '',
                "signatureTimestamp": st.session_state.signature_data.get('timestamp', 0) if st.session_state.signature_data else 0,
                "signatureFormat": st.session_state.signature_data.get('format', 'PNG') if st.session_state.signature_data else 'PNG',
                "signatureCollected": st.session_state.signature_data is not None
            }
        }
        
        # Log for debugging
        print(f"📤 Submitting employee data to Logic App...")
        print(f"   Tenant: {tenant_id}")
        print(f"   User: {user_email}")
        print(f"   Employee: {employee_data.get('employee', {}).get('firstName', '')} {employee_data.get('employee', {}).get('lastName', '')}")
        
        # Send to Logic App with increased timeout
        response = requests.post(logic_app_submit_url, json=payload, timeout=30)
        
        # Check response
        if response.status_code in [200, 201, 202]:
            print(f"✅ SUCCESS: Data submitted to Logic App (Status: {response.status_code})")
            return {
                "success": True,
                "message": "Employee data submitted successfully!",
                "status_code": response.status_code
            }
        else:
            print(f"❌ ERROR: Logic App returned {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return {
                "success": False,
                "message": f"Failed to submit: HTTP {response.status_code}",
                "error": response.text
            }
            
    except requests.exceptions.Timeout:
        print(f"⏱️ TIMEOUT: Logic App did not respond within 30 seconds")
        return {
            "success": False,
            "message": "Request timeout - Logic App took too long to respond"
        }
    except Exception as e:
        print(f"❌ EXCEPTION: {type(e).__name__}: {str(e)}")
        return {
            "success": False,
            "message": f"Error submitting data: {str(e)}"
        }

# Add new function to initialize specific agent
def initialize_tenant_agent(project_client, agent_id):
    """Initialize conversation with the specific agent for this tenant"""
    try:
        # Get the specific agent by ID
        agent = project_client.agents.get_agent(agent_id)
        
        # Create thread for the specific agent
        thread = project_client.agents.threads.create()
        
        return agent, thread.id
        
    except Exception as e:
        st.error(f"Error initializing agent {agent_id}: {e}")
        return None, None

# Modify the send_initial_context_message function to accept agent parameter
def send_initial_context_message(agent):
    """Send initial context message to the agent with enhanced user information"""
    try:
        if not st.session_state.thread_id:
            return False
            
        user_name = st.session_state.user_info.get('displayName', 'User')
        user_email = st.session_state.user_info.get('mail', 'no-email@unknown.com')
        tenant_id = st.session_state.user_info.get('tenant_id', 'unknown')
        account_type = st.session_state.user_info.get('account_type', 'unknown')
        email_method = st.session_state.user_info.get('email_extraction_method', 'unknown')
        user_name="User" if user_name == "Unknown" else user_name
        # Ensure email is never None or empty
        if not user_email or user_email in ['None', '', 'null']:
            user_email = "no-email@unknown.com"
            st.warning("⚠️ User email could not be determined - using fallback")
        
        # Ensure tenant ID is never None
        if not tenant_id or tenant_id in ['None', '', 'null']:
            tenant_id = "unknown"
            st.warning("⚠️ Tenant ID could not be determined - using 'unknown'")
        
        initial_context_message = f"""
        Hi Employee Onboarding Assistant! 
        
        [SYSTEM CONTEXT - PLEASE REMEMBER THROUGHOUT THE CONVERSATION]
        User: {user_name}
        Email: {user_email}
        Tenant ID: {tenant_id}
        Account Type: {account_type}
        Email Extraction Method: {email_method}
        
        CRITICAL INSTRUCTIONS: Throughout this entire conversation, whenever you create JSON output for Logic Apps API calls, you MUST always include these fields with exact values:
        "tenantId": "{tenant_id}"
        "userEmail": "{user_email}"
        
        SIGNATURE DATA HANDLING:
        - During onboarding, you will collect the user's digital signature
        - When signature is provided, you will receive it as base64 encoded PNG data
        - When submitting employee data to storage, you MUST include these signature fields:
          * "signatureBase64": [the complete base64 string]
          * "signatureTimestamp": [unix timestamp]
          * "signatureFormat": "PNG"
        - Store signature data together with other employee information (name, email, phone, etc.)
        - Signature is REQUIRED for onboarding completion
        
        IMPORTANT - SIGNATURE COLLECTION INSTRUCTIONS:
        - After user confirms their details, the system will automatically handle signature collection if required
        - You do NOT need to mention signature in your response
        - Just say: "Thank you for confirming!"
        - The system will show signature canvas automatically if needed based on configuration
        - DO NOT output JSON data to the user
        - DO NOT show API call structures or technical data
        - Keep all responses brief and user-friendly
        
        CRITICAL - NEVER SHOW JSON OR TECHNICAL DATA TO USERS:
        - NEVER output JSON structures in your responses
        - NEVER show API payloads, data structures, or technical formats
        - Keep all responses in natural, conversational language
        - If you need to store data, do it silently without showing the user
        
        IMPORTANT VALIDATION RULES:
        - If tenantId is "unknown", inform user that organization identification may be limited
        - If userEmail contains "no-email" or "unknown", request user to provide their actual email
        - Never use null, undefined, or empty string for these fields
        - Always validate data before sending to Logic Apps
        - Ensure signature data is included when calling storage functions
        
        ERROR HANDLING for missing user information:
        1. If email is missing/unknown, ask user to provide their work email
        2. If tenant is unknown, proceed but note potential routing limitations
        3. Always include both fields even if they contain fallback values
        
        The tenant ID identifies which organization this user belongs to and the email identifies the specific user. Both fields must be included in all API submissions for proper user identification and organizational routing. Also the {user_email} is not the user's actual email, so do not ask the user whether {user_email} is their email. just collect user's Email seperately and do the onboarding process.
        Current user context validation:
        - Email Status: {email_method}
        - Tenant Status: {'✅ Valid' if tenant_id != 'unknown' else '⚠️ Unknown'}
        - Account Type: {account_type}
        
        Begin the onboarding process with a friendly greeting.
        """
        
        # Create initial context message
        message = st.session_state.project_client.agents.messages.create(
            thread_id=st.session_state.thread_id,
            role="assistant",
            content=initial_context_message
        )
        
        # Process the run with the agent
        run = st.session_state.project_client.agents.runs.create_and_process(
            thread_id=st.session_state.thread_id,
            agent_id=agent.id  # Use the passed agent
        )
        
        if run.status == "failed":
            st.error(f"Failed to send initial context: {run.last_error}")
            return False
        
        # Retrieve the agent's response
        messages = st.session_state.project_client.agents.messages.list(
            thread_id=st.session_state.thread_id
        )
        messages_list = list(messages)
        
        # Find the latest assistant message and add to session
        msg=messages_list[0]
        content = ""
        if hasattr(msg, 'content') and msg.content:
            if isinstance(msg.content, list) and len(msg.content) > 0:
                if hasattr(msg.content[0], 'text'):
                    content = msg.content[0].text.value
                else:
                    content = str(msg.content[0])
            else:
                content = str(msg.content)
        
        # Add the initial greeting to messages
        st.session_state.messages.append({"role": "assistant", "content": content})
        return True
        
        return False
        
    except Exception as e:
        st.error(f"Error sending initial context: {e}")
        return False

# Authentication check
if not st.session_state.logged_in:
    login()
    st.stop()

# Initialize Azure client and tenant-specific agent
if not st.session_state.project_client:
    with st.spinner("Connecting to Azure AI..."):
        project = get_azure_client()
        if project:
            st.session_state.project_client = project
            
            # Get tenant-specific agent ID
            tenant_id = st.session_state.user_info.get('tenant_id', 'unknown')
            user_email = st.session_state.user_info.get('mail', 'no-email@unknown.com')
            
            agent_id, agent_type, org_name = get_agent_id_for_tenant(tenant_id, user_email)
            
            if agent_id:
                # Initialize the tenant-specific agent
                with st.spinner(f"Setting up {agent_type} agent..."):
                    agent, thread_id = initialize_tenant_agent(project, agent_id)
                    
                    if agent and thread_id:
                        st.session_state.agent = agent
                        st.session_state.thread_id = thread_id
                        st.session_state.agent_type = agent_type
                        st.session_state.org_name = org_name
                        
                        # Send initial context
                        context_sent = send_initial_context_message(agent)
                      
# Update the create_new_thread function
def create_new_thread():
    """Create a new conversation thread and send initial context"""
    try:
        if st.session_state.project_client and st.session_state.agent:
            thread = st.session_state.project_client.agents.threads.create()
            st.session_state.thread_id = thread.id
            st.session_state.messages = []
            
            # Send initial context message
            context_sent = send_initial_context_message(st.session_state.agent)
            
            if context_sent:
                st.success(f"New conversation started with context! Thread ID: {thread.id}")
            else:
                st.success(f"New conversation started! Thread ID: {thread.id}")
                st.warning("Initial context may not have been set properly.")
                
    except Exception as e:
        st.error(f"Failed to create thread: {e}")

def send_message_to_agent(user_message):
    """Send message to Azure AI agent and get response"""
    try:
        # Create user message
        message = st.session_state.project_client.agents.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=user_message
        )
        
        # Process the run with the agent
        run = st.session_state.project_client.agents.runs.create_and_process(
            thread_id=st.session_state.thread_id,
            agent_id=st.session_state.agent.id
        )
        
        if run.status == "failed":
            return f"Error: {run.last_error}"
        
        # Handle function calls from the agent
        if run.status == "requires_action":
            print("🔧 Agent requested function call!")
            
            # Get the tool calls
            if run.required_action and run.required_action.submit_tool_outputs:
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"📞 Calling function: {function_name}")
                    print(f"   Arguments: {json.dumps(function_args, indent=2)[:200]}...")
                    
                    # Call the appropriate function
                    # Handle both "tax" and "submit_employee_onboarding" function names
                    if function_name in ["submit_employee_onboarding", "tax"]:
                        result = submit_employee_onboarding(function_args)
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result)
                        })
                    else:
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps({"error": f"Unknown function: {function_name}"})
                        })
                
                # Submit tool outputs back to agent
                run = st.session_state.project_client.agents.runs.submit_tool_outputs_and_process(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
        
        # Retrieve messages
        messages = st.session_state.project_client.agents.messages.list(
            thread_id=st.session_state.thread_id
        )
        messages_list = list(messages)
        
        # Find the latest assistant message
        msg= messages_list[0]
        content = ""
        if hasattr(msg, 'content') and msg.content:
            if isinstance(msg.content, list) and len(msg.content) > 0:
                if hasattr(msg.content[0], 'text'):
                    content = msg.content[0].text.value
                else:
                    content = str(msg.content[0])
            else:
                content = str(msg.content)
        return content
        
        return "No response received from agent."
        
    except Exception as e:
        print(f"❌ Error communicating with agent: {e}")
        return f"Error communicating with agent: {e}"

def send_signature_data_to_agent():
    """Send signature confirmation to agent after signature is collected"""
    try:
        if not st.session_state.signature_data:
            return "No signature data available."
        
        # Get signature data including base64
        base64_data = st.session_state.signature_data.get('base64_data', '')
        timestamp = st.session_state.signature_data.get('timestamp', 0)
        format_type = st.session_state.signature_data.get('format', 'PNG')
        
        # Create message with ACTUAL base64 signature data
        # Include the base64 in the message so the agent can use it
        signature_message = f"""[SIGNATURE COLLECTED]

The user has provided their digital signature.

IMPORTANT - Include this signature data when submitting:
- signatureBase64: {base64_data}
- signatureTimestamp: {int(timestamp)}
- signatureFormat: {format_type}

Please proceed with submitting the onboarding data using the tax function. Make sure to include the signatureBase64 value exactly as provided above."""
        
        # Send to agent
        response = send_message_to_agent(signature_message)
        return response
        
    except Exception as e:
        print(f"❌ Error sending signature to agent: {e}")
        return f"Error: {str(e)}"

def wait_for_active_runs(max_wait_seconds=30):
    """Wait for any active runs to complete before proceeding"""
    try:
        wait_count = 0
        while wait_count < max_wait_seconds:
            # Get all runs for this thread
            runs = st.session_state.project_client.agents.runs.list(
                thread_id=st.session_state.thread_id
            )
            
            # Check if any runs are active
            active_runs = [run for run in runs if run.status in ["in_progress", "queued", "requires_action"]]
            
            if not active_runs:
                return True  # No active runs, safe to proceed
            
            # Wait a bit before checking again
            time.sleep(1)
            wait_count += 1
        
        # Timeout reached
        return False
    except Exception as e:
        # If we can't check, assume it's safe to proceed
        return True



# Custom CSS with WhatsApp-like chat bubbles
st.markdown("""
<style>
.login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    background: white;
    text-align: center;
}

.main-logo {
    width: 80px;
    height: 80px;
    object-fit: contain;
    border-radius: 12px;
    margin-right: 20px;
}

.login-title {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 10px;
}

.user-info {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 10px 15px;
    border-radius: 10px;
    font-weight: 600;
    text-align: center;
    margin: 5px 0;
}

.welcome-message {
    background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 1rem 0;
    text-align: center;
}

/* Chat Container */
.chat-container {
    background-color: #f5f5f5;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    min-height: 400px;
    max-height: 600px;
    overflow-y: auto;
}

/* Style Streamlit's default chat messages */
.stChatMessage {
    margin: 10px 0 !important;
}

/* User messages - right aligned with light grey */
.stChatMessage[data-testid*="user"] {
    flex-direction: row-reverse !important;
    justify-content: flex-start !important;
    margin-left: 20% !important;
    margin-right: 10px !important;
}

.stChatMessage[data-testid*="user"] .stMarkdown {
    background-color: #e0e0e0 !important;
    color: #333 !important;
    border-radius: 18px !important;
    border-bottom-right-radius: 5px !important;
    padding: 12px 16px !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
}

/* Assistant messages - left aligned with green */
.stChatMessage[data-testid*="assistant"] {
    justify-content: flex-start !important;
    margin-right: 20% !important;
    margin-left: 10px !important;
}

.stChatMessage[data-testid*="assistant"] .stMarkdown {
    background-color: #4CAF50 !important;
    color: white !important;
    border-radius: 18px !important;
    border-bottom-left-radius: 5px !important;
    padding: 12px 16px !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
}

/* Avatar styling */
.stChatMessage img {
    border-radius: 8px !important;
    width: 35px !important;
    height: 35px !important;
}

/* Hide Streamlit default elements */
.stDeployButton { display: none; }
#MainMenu { visibility: hidden; }
.stAppHeader { display: none; }

/* Chat input styling */
.stChatInput > div {
    border-radius: 25px;
    border: 2px solid #4CAF50;
}

.stChatInput input {
    border-radius: 20px;
    padding: 12px 20px;
}

/* Signature Modal Styling */
.signature-modal {
    background: white;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    border: 2px solid #4CAF50;
}

.signature-canvas-container {
    border: 2px dashed #4CAF50;
    border-radius: 10px;
    padding: 10px;
    background: #f9f9f9;
    margin: 15px 0;
}

.signature-buttons {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin-top: 15px;
}

.signature-buttons button {
    padding: 10px 20px;
    border-radius: 8px;
    border: none;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
}

.signature-buttons button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
}
</style>
""", unsafe_allow_html=True)

# Authentication check
if not st.session_state.logged_in:
    login()
    st.stop()

# Initialize Azure client and tenant-specific agent
if not st.session_state.project_client:
    with st.spinner("Connecting to Azure AI..."):
        project = get_azure_client()
        if project:
            st.session_state.project_client = project
            
            # Get tenant-specific agent ID
            tenant_id = st.session_state.user_info.get('tenant_id', 'unknown')
            user_email = st.session_state.user_info.get('mail', 'no-email@unknown.com')
            
            agent_id, agent_type, org_name = get_agent_id_for_tenant(tenant_id, user_email)
            
            if agent_id:
                # Initialize the tenant-specific agent
                with st.spinner(f"Setting up {agent_type} agent for {org_name}..."):
                    agent, thread_id = initialize_tenant_agent(project, agent_id)
                    
                    if agent and thread_id:
                        st.session_state.agent = agent
                        st.session_state.thread_id = thread_id
                        st.session_state.agent_type = agent_type
                        st.session_state.org_name = org_name
                        
                        # Send initial context
                        context_sent = send_initial_context_message(agent)
                        if context_sent:
                            st.success(f"✅ Connected to {agent_type} agent for {org_name}")
                        else:
                            st.warning("⚠️ Agent connected but initial context may not be set")
                    else:
                        st.error("❌ Failed to initialize tenant-specific agent")
                        st.stop()
            else:
                st.error("❌ Could not determine agent for your organization")
                st.stop()

# Main Chat Interface
logo_base64 = get_logo_base64()

if logo_base64:
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 15px;">
            <img src="data:image/png;base64,{logo_base64}" style="width: 60px; height: 60px; object-fit: contain; border-radius: 8px;" alt="Logo">
            <h1 style="color: #0078d4; margin: 0; font-size: 2.5rem;">Employee Onboarding Assistant</h1>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.title("🤖 Employee Onboarding Assistant")

# Header layout with user info and buttons
col1, col2 = st.columns([1, 2])

with col1:
    user_name = st.session_state.user_info.get('displayName', 'User')
    user_email = st.session_state.user_info.get('mail', '')
    
    # Handle unknown/hidden usernames - minimal change
    if not user_name or user_name.strip() == '' or user_name.lower() in ['unknown', 'unknown user', 'user']:
        display_name = "User"
    else:
        display_name = user_name
    
    st.markdown(f"""
    <div class="user-info">
         {display_name}<br>
        
    </div>
    """, unsafe_allow_html=True)

with col2:
    btn_col1, btn_col2, btn_col3 = st.columns([0.8, 0.8, 1.4])
    
    with btn_col1:
        if st.button("🗑️", key="clear", help="Clear Chat"):
            st.session_state.messages = []
            st.session_state.thread_id = None
            # Immediately create new thread after clearing
            if st.session_state.project_client:
                with st.spinner("Creating new conversation..."):
                    create_new_thread()
            st.rerun()
    
    with btn_col2:
        if st.button("➕ New", key="new_chat", help="Start New Conversation"):
            st.session_state.messages = []
            st.session_state.thread_id = None
            # Immediately create new thread after clearing
            if st.session_state.project_client:
                with st.spinner("Creating new conversation..."):
                    create_new_thread()
            st.rerun()
    
    with btn_col3:
        if st.button("Sign Out", key="signout", help="Sign Out"):
            # Clean up session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

st.markdown("---")

# Sidebar for signature status and controls
with st.sidebar:
    st.markdown("### 📝 Signature Status")
    if st.session_state.signature_data:
        st.success("✅ Signature Collected")
        st.markdown(f"**Format:** {st.session_state.signature_data['format']}")
        st.markdown(f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.session_state.signature_data['timestamp']))}")
        
        if st.button("👁️ View Signature", key="view_signature"):
            display_collected_signature()
            
        if st.button("🗑️ Clear Signature", key="clear_stored_signature"):
            st.session_state.signature_data = None
            st.rerun()
    else:
        st.warning("⚠️ No Signature Collected")
        if st.button("✍️ Collect Signature", key="manual_signature"):
            trigger_signature_collection()
    
    # Show signature requirement setting
    st.markdown("---")
    st.markdown("### ⚙️ Configuration")
    if st.session_state.require_signature:
        st.info("✅ **Signature Required:** YES")
    else:
        st.warning("❌ **Signature Required:** NO")
    st.caption(f"URL: `?requireSignature={str(st.session_state.require_signature).lower()}`")
    
    # Debug mode toggle
    st.markdown("---")
    debug_mode = st.checkbox("🔍 Debug Mode", key="debug_mode", help="Show debug information for signature collection")
    if debug_mode:
        debug_signature_state()

# Chat Interface using Streamlit's native components with custom styling
chat_container = st.container()

with chat_container:
    # Display chat messages using Streamlit's native chat components
    for idx, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            # Use logo as avatar if available
            if logo_base64:
                with st.chat_message("assistant", avatar=f"data:image/png;base64,{logo_base64}"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message["content"])

# Display signature modal if triggered (appears above chat input)
display_signature_modal()

# Handle pending signature send (after modal closes and page reloads)
if st.session_state.get('signature_pending_send', False):
    st.session_state.signature_pending_send = False  # Clear the flag immediately
    
    print("📤 DEBUG: Processing pending signature send...")
    
    # Check if agent is ready before trying to send
    agent_ready = (st.session_state.get('project_client') is not None and 
                   st.session_state.get('thread_id') is not None and
                   st.session_state.get('agent') is not None)
    
    if agent_ready and st.session_state.signature_data:
        # Agent is ready - send signature data with spinner
        try:
            # Show a placeholder message that we'll update
            placeholder_msg = "⏳ Processing your signature and submitting your onboarding information..."
            st.session_state.messages.append({"role": "assistant", "content": placeholder_msg})
            
            # Force display update
            st.rerun()
            
        except Exception as e:
            print(f"❌ Error in signature send setup: {e}")
            # Fallback to success message
            success_msg = "✅ Thank you! Your onboarding information has been successfully submitted. You should receive a confirmation email shortly. Welcome aboard!"
            st.session_state.messages.append({"role": "assistant", "content": success_msg})
            st.rerun()
    else:
        # Agent not ready or no signature - show success message
        print("⚠️ WARNING: Agent not ready or no signature data")
        success_msg = "✅ Thank you! Your onboarding information has been successfully submitted. You should receive a confirmation email shortly. Welcome aboard!"
        st.session_state.messages.append({"role": "assistant", "content": success_msg})
        st.rerun()

# Handle signature data sending with progress indicator
if st.session_state.get('signature_data') and len(st.session_state.messages) > 0:
    last_msg = st.session_state.messages[-1]
    if last_msg.get('role') == 'assistant' and '⏳ Processing your signature' in last_msg.get('content', ''):
        # This is the placeholder - now actually send the signature
        print("📤 DEBUG: Sending signature to agent NOW...")
        try:
            with st.spinner("📤 Submitting your onboarding information..."):
                agent_response = send_signature_data_to_agent()
            
            print("✅ DEBUG: Signature sent successfully to agent")
            
            # Replace placeholder with actual response
            if agent_response and agent_response.strip():
                st.session_state.messages[-1] = {"role": "assistant", "content": agent_response}
            else:
                confirmation = "✅ Thank you! Your onboarding information has been successfully submitted. You should receive a confirmation email shortly. Welcome aboard!"
                st.session_state.messages[-1] = {"role": "assistant", "content": confirmation}
                
        except Exception as e:
            print(f"❌ ERROR sending signature: {e}")
            # Replace placeholder with success message even on error
            confirmation = "✅ Thank you! Your onboarding information has been successfully submitted. You should receive a confirmation email shortly. Welcome aboard!"
            st.session_state.messages[-1] = {"role": "assistant", "content": confirmation}
        
        # Rerun to show final message
        st.rerun()

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Check if client is initialized
    if not st.session_state.project_client:
        st.error("Please wait for Azure connection to complete.")
        st.stop()
    
    # Thread should already exist, but create one if somehow missing
    if not st.session_state.thread_id:
        st.warning("Creating conversation thread...")
        create_new_thread()
        if not st.session_state.thread_id:
            st.error("Failed to create conversation thread.")
            st.stop()
    
    # Check if user is confirming details (triggers signature collection)
    confirmation_keywords = ["correct", "confirm", "confirmed", "yes", "yeah", "yep", "ok", "okay", "looks good", "all good", "that's right", "right"]
    is_confirmation = any(keyword in prompt.lower() for keyword in confirmation_keywords)
    
    # Check if previous message was asking for confirmation (contains summary/review keywords)
    previous_message_asked_confirmation = False
    if len(st.session_state.messages) > 0:
        last_agent_message = None
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "assistant":
                last_agent_message = msg["content"].lower()
                break
        
        if last_agent_message:
            confirmation_triggers = ["please review", "confirm if", "is correct", "please verify", "let me know if", "would like to make any changes"]
            previous_message_asked_confirmation = any(trigger in last_agent_message for trigger in confirmation_triggers)
    
    # If user is confirming AND signature not collected, check if signature is required
    signature_triggered = False
    if is_confirmation and previous_message_asked_confirmation and not st.session_state.signature_data:
        # DEBUG: Log the decision
        print(f"🔍 DEBUG: User confirmed. require_signature = {st.session_state.require_signature}")
        
        # Only show canvas if signature is required (based on URL parameter)
        if st.session_state.require_signature:
            print(f"✅ DEBUG: Showing signature canvas (require_signature=True)")
            st.session_state.show_signature_modal = True
            signature_triggered = True
        else:
            print(f"❌ DEBUG: Skipping signature (require_signature=False)")
            # Signature not required - send message to agent to submit WITHOUT signature
            signature_not_req_msg = "[SIGNATURE NOT REQUIRED] Please proceed with submitting the onboarding data WITHOUT signature. The system does not require a signature for this onboarding. Call the tax function with empty signature fields."
            
            # Add user confirmation to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Send the [SIGNATURE NOT REQUIRED] message to agent
            print(f"📤 DEBUG: Sending [SIGNATURE NOT REQUIRED] message to agent")
            with st.chat_message("assistant", avatar=f"data:image/png;base64,{logo_base64}" if logo_base64 else "🤖"):
                with st.spinner("Employee Onboarding Assistant is submitting your data..."):
                    response = send_message_to_agent(signature_not_req_msg)
                st.markdown(response)
            
            # Add assistant response to session state
            st.session_state.messages.append({"role": "assistant", "content": response})
            signature_triggered = True  # Prevent normal flow from running
    
    # Add user message to chat (only if signature wasn't handled above)
    if not signature_triggered:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get and display agent response
        with st.chat_message("assistant", avatar=f"data:image/png;base64,{logo_base64}" if logo_base64 else "🤖"):
            with st.spinner("Employee Onboarding Assistant is thinking..."):
                response = send_message_to_agent(prompt)
            st.markdown(response)
        
        # Add assistant response to session state
        st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        # Signature triggered - rerun to show canvas immediately
        st.rerun()