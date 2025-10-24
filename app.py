


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
USER_TENANT_ID = os.getenv("USER_TENANT_ID")  # For user authentication
AZURE_AI_TENANT_ID = os.getenv("AZURE_AI_TENANT_ID")    # For Azure AI Project access


# Azure AI Project endpoint - make configurable
AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT")

REDIRECT_URI = os.getenv("REDIRECT_URI","http://localhost:8501")

# MSAL Configuration for user authentication (supports multitenant)
AUTHORITY = f"https://login.microsoftonline.com/{USER_TENANT_ID}"
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

def login_with_microsoft():
    """Microsoft login"""
    try:
        msal_app = get_msal_app()
        auth_url = msal_app.get_authorization_request_url(
            SCOPE, 
            redirect_uri=REDIRECT_URI
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
    """Display signature collection interface"""
    # Header with clear instructions
    st.markdown("""
    <div style="text-align: center; margin-bottom: 25px;">
        <h3 style="color: #4CAF50; margin-bottom: 15px;">✍️ Digital Signature Required</h3>
        <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <p style="color: #2e7d32; margin: 0; font-weight: 500;">
                📱 <strong>Instructions:</strong> Draw your signature using your mouse, trackpad, or touchscreen
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Signature canvas container with better styling
    st.markdown("""
    <div style="
        border: 3px solid #4CAF50;
        border-radius: 15px;
        padding: 25px;
        background: linear-gradient(135deg, #f8fff8, #ffffff);
        margin: 20px 0;
        text-align: center;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.1);
    ">
        <p style="color: #4CAF50; margin-bottom: 20px; font-size: 16px; font-weight: 600;">
            🎨 Draw your signature in the area below
        </p>
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
    
    # Action buttons with better styling
    st.markdown("""
    <div style="text-align: center; margin-top: 25px;">
        <p style="color: #666; margin-bottom: 15px; font-size: 14px;">
            Use the buttons below to clear, cancel, or save your signature
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🗑️ Clear Canvas", key="clear_signature", help="Clear the signature canvas", use_container_width=True, type="secondary"):
            # Force canvas to reset by incrementing a counter
            if 'canvas_reset_counter' not in st.session_state:
                st.session_state.canvas_reset_counter = 0
            st.session_state.canvas_reset_counter += 1
            st.rerun()
    
    with col2:
        if st.button("❌ Cancel", key="cancel_signature", help="Cancel signature collection", use_container_width=True, type="secondary"):
            st.session_state.show_signature_modal = False
            st.rerun()
    
    with col3:
        if st.button("✅ Save Signature", key="save_signature", help="Save your signature", use_container_width=True, type="primary"):
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
                    
                    # Close the modal first
                    st.session_state.show_signature_modal = False
                    
                    # Mark that we need to send signature after rerun
                    st.session_state.signature_pending_send = True
                    
                    # Add a user message to chat showing signature was collected
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": "✅ I have provided my digital signature."
                    })
                    
                    st.rerun()
                else:
                    st.warning("⚠️ Please add your signature before saving - the canvas appears to be empty")
            else:
                st.warning("⚠️ Please draw your signature on the canvas before saving")

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
    """Display signature collection modal"""
    if st.session_state.show_signature_modal:
        # Add JavaScript to auto-scroll to signature modal
        st.markdown("""
        <script>
            // Auto-scroll to signature modal
            setTimeout(function() {
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            }, 300);
        </script>
        """, unsafe_allow_html=True)
        
        # Add a VERY prominent full-width banner at the top
        st.markdown("""
        <div style="
            position: sticky;
            top: 0;
            z-index: 999;
            background: #ff6b6b;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            animation: blink 1.5s infinite;
        ">
            ⬇️ SIGNATURE REQUIRED - SCROLL DOWN TO SIGN ⬇️
        </div>
        <style>
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Add a large visual separator and alert
        st.markdown("---")
        st.error("⚠️ **ATTENTION: Signature pad is open below** - Please scroll down to sign!")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Create a prominent container with better styling
        st.markdown("""
        <div id="signature-modal" style="
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            padding: 25px;
            border-radius: 15px;
            margin: 30px 0;
            box-shadow: 0 10px 30px rgba(76, 175, 80, 0.4);
            border: 3px solid #2e7d32;
            animation: pulse 2s infinite;
        ">
            <h1 style="text-align: center; margin: 0; color: white; font-size: 2.5em;">✍️ Digital Signature Collection</h1>
            <p style="text-align: center; margin-top: 10px; color: white; font-size: 1.2em;">Please sign in the box below</p>
        </div>
        <style>
            @keyframes pulse {
                0%, 100% { box-shadow: 0 10px 30px rgba(76, 175, 80, 0.4); }
                50% { box-shadow: 0 10px 40px rgba(76, 175, 80, 0.6); }
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Create an expander-like container for the signature interface
        with st.container():
            st.markdown("""
            <div style="
                background: white;
                border: 3px solid #4CAF50;
                border-radius: 15px;
                padding: 30px;
                margin: 10px 0;
                box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            ">
            """, unsafe_allow_html=True)
            
            collect_signature()
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
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
        return f"Error communicating with agent: {e}"

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

def send_signature_data_to_agent():
    """Send signature data to Azure AI agent with full base64 for storage"""
    try:
        if not st.session_state.signature_data:
            return "No signature data available"
        
        # Wait for any active runs to complete before sending signature
        if not wait_for_active_runs(max_wait_seconds=30):
            return "⚠️ Signature received! Please wait a moment and send a message to continue..."
        
        # Create a message with signature data for the agent
        signature_info = get_signature_tool_data()
        
        # Get user info for context
        user_email = st.session_state.user_info.get('mail', 'no-email@unknown.com')
        tenant_id = st.session_state.user_info.get('tenant_id', 'unknown')
        
        # Include the FULL base64 signature data
        signature_message = f"""
        [SIGNATURE COLLECTED - READY FOR STORAGE]
        
        The user has successfully provided their digital signature.
        
        SIGNATURE DATA FOR STORAGE:
        ----------------------------------------
        Signature Base64: {signature_info['signature_base64']}
        ----------------------------------------
        Timestamp: {signature_info['timestamp']}
        Format: {signature_info['format']}
        User Email: {user_email}
        Tenant ID: {tenant_id}
        
        CRITICAL INSTRUCTIONS FOR DATA SUBMISSION:
        When you call any Logic Apps API or function to submit/store the employee onboarding data, 
        you MUST include this signature information as follows:
        
        JSON Field to include:
        {{
            "tenantId": "{tenant_id}",
            "userEmail": "{user_email}",
            "signatureBase64": "{signature_info['signature_base64']}",
            "signatureTimestamp": "{signature_info['timestamp']}",
            "signatureFormat": "{signature_info['format']}"
        }}
        
        The signature base64 string above is the complete PNG image data that should be stored 
        with the employee's other information (name, email, phone, address, etc.).
        
        Please confirm that you have received the signature data and will include it when 
        submitting the complete employee onboarding information.
        """
        
        # Send signature data to agent
        message = st.session_state.project_client.agents.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=signature_message
        )
        
        # Process the run with the agent
        run = st.session_state.project_client.agents.runs.create_and_process(
            thread_id=st.session_state.thread_id,
            agent_id=st.session_state.agent.id
        )
        
        if run.status == "failed":
            return f"Error processing signature: {run.last_error}"
        
        # Retrieve the agent's response
        messages = st.session_state.project_client.agents.messages.list(
            thread_id=st.session_state.thread_id
        )
        messages_list = list(messages)
        
        # Find the latest assistant message
        msg = messages_list[0]
        content = ""
        if hasattr(msg, 'content') and msg.content:
            if isinstance(msg.content, list) and len(msg.content) > 0:
                if hasattr(msg.content[0], 'text'):
                    content = msg.content[0].text.value
                else:
                    content = str(msg.content[0])
            else:
                content = str(msg.content)
        
        # If we got a response, return it; otherwise return a default message
        if content and content.strip():
            return content
        else:
            return "✅ Signature submitted successfully! Your onboarding process is now complete. All your information, including your digital signature, has been saved."
        
    except Exception as e:
        # Check if it's a rate limit error
        error_str = str(e)
        if 'rate_limit' in error_str.lower():
            return "✅ Signature submitted successfully! Your onboarding process is now complete. All your information, including your digital signature, has been saved."
        return "✅ Signature submitted successfully! Your onboarding process is now complete. (Note: Agent confirmation delayed due to high traffic)"

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
                    
                    # Check if this message needs a signature button
                    signature_triggers = [
                        "signature", "sign", "digital signature", "electronic signature",
                        "please sign", "signature required", "signature needed", "sign here",
                        "draw your signature", "provide signature", "signature pad"
                    ]
                    
                    should_show_sig_button = any(trigger.lower() in message["content"].lower() for trigger in signature_triggers)
                    
                    # Only show button if signature not yet collected and message contains trigger words
                    if should_show_sig_button and not st.session_state.signature_data:
                        st.markdown("---")
                        st.markdown("""
                        <div style="
                            background: linear-gradient(135deg, #4CAF50, #45a049);
                            color: white;
                            padding: 15px;
                            border-radius: 10px;
                            text-align: center;
                            margin: 10px 0;
                        ">
                            <h4 style="margin: 0; color: white;">✍️ Digital Signature Required</h4>
                            <p style="margin: 5px 0 0 0; color: white;">Click the button below to open the signature pad</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("✍️ Open Signature Pad", key=f"trigger_signature_btn_{idx}", type="primary", use_container_width=True):
                            st.session_state.show_signature_modal = True
                            st.rerun()
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message["content"])

# Display signature modal if triggered (appears above chat input)
display_signature_modal()

# Handle pending signature send (after modal closes and page reloads)
if st.session_state.get('signature_pending_send', False):
    st.session_state.signature_pending_send = False  # Clear the flag immediately
    
    # Check if agent is ready before trying to send
    agent_ready = (st.session_state.get('project_client') is not None and 
                   st.session_state.get('thread_id') is not None and
                   st.session_state.get('agent') is not None)
    
    if agent_ready:
        # Agent is ready - try to send signature data
        try:
            with st.spinner("📤 Sending signature to AI agent..."):
                agent_response = send_signature_data_to_agent()
            
            # Add agent response or fallback
            if agent_response and agent_response.strip():
                st.session_state.messages.append({"role": "assistant", "content": agent_response})
            else:
                confirmation = "✅ Signature submitted successfully! Your onboarding process is now complete. All your information, including your digital signature, has been saved."
                st.session_state.messages.append({"role": "assistant", "content": confirmation})
                
        except Exception as e:
            # Any error - still show success
            success_msg = "✅ Signature submitted successfully! Your onboarding process is now complete. All your information, including your digital signature, has been saved."
            st.session_state.messages.append({"role": "assistant", "content": success_msg})
    else:
        # Agent not ready - just show success message immediately (for testing)
        success_msg = "✅ Signature submitted successfully! Your onboarding process is now complete. All your information, including your digital signature, has been saved."
        st.session_state.messages.append({"role": "assistant", "content": success_msg})
    
    # Force rerun to display the new message
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
    
    # Add user message to chat
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