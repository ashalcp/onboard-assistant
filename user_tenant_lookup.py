"""
User Tenant Lookup Utility
This module provides functionality to look up user tenant configurations
from an Excel file or SharePoint list.
"""

import os
import requests
from typing import Optional, Dict

def lookup_user_tenant_from_excel(user_email: str, excel_url: Optional[str] = None) -> Optional[Dict]:
    """
    Look up user tenant configuration from Excel/SharePoint file.
    
    Args:
        user_email: Email address of the user to look up
        excel_url: Optional SharePoint URL to the Excel file
        
    Returns:
        Dictionary with tenant_id, client_id, url, client_secret if found, None otherwise
    """
    # If Excel URL is provided, try to read from SharePoint
    if excel_url:
        try:
            # This would require authentication to SharePoint
            # For now, return None - implement SharePoint authentication if needed
            pass
        except Exception as e:
            print(f"Error reading from SharePoint: {e}")
            return None
    
    # Alternative: Read from local Excel file if available
    excel_file_path = os.getenv("USER_TENANT_EXCEL_PATH")
    if excel_file_path and os.path.exists(excel_file_path):
        try:
            import pandas as pd
            df = pd.read_excel(excel_file_path)
            
            # Find user by email (case-insensitive)
            user_row = df[df['userEmail'].str.lower() == user_email.lower()]
            
            if not user_row.empty:
                row = user_row.iloc[0]
                return {
                    'tenantId': str(row.get('tenantId', '')),
                    'clientId': str(row.get('clientid', '')),
                    'url': str(row.get('url', '')),
                    'clientSecret': str(row.get('clientSecret', ''))
                }
        except ImportError:
            print("pandas and openpyxl required to read Excel files. Install with: pip install pandas openpyxl")
        except Exception as e:
            print(f"Error reading Excel file: {e}")
    
    return None

def validate_user_tenant(user_email: str, tenant_id: str) -> bool:
    """
    Validate if a user's tenant ID matches expected configuration.
    This can be used to verify user access before proceeding.
    
    Args:
        user_email: Email address of the user
        tenant_id: Tenant ID extracted from JWT token
        
    Returns:
        True if user/tenant combination is valid, False otherwise
    """
    lookup = lookup_user_tenant_from_excel(user_email)
    
    if lookup:
        expected_tenant_id = lookup.get('tenantId')
        if expected_tenant_id and expected_tenant_id.lower() == tenant_id.lower():
            return True
        else:
            print(f"⚠️ Tenant ID mismatch: Expected {expected_tenant_id}, got {tenant_id}")
            return False
    
    # If no lookup data available, allow authentication (fallback)
    return True

def get_user_config_from_excel(user_email: str) -> Optional[Dict]:
    """
    Get complete user configuration from Excel file.
    
    Args:
        user_email: Email address of the user
        
    Returns:
        Dictionary with all user configuration fields
    """
    return lookup_user_tenant_from_excel(user_email)

