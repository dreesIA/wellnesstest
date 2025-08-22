#!/usr/bin/env python3
"""
Test Google Sheets Connection on Streamlit Cloud
"""

import streamlit as st
import pandas as pd

st.title("🔍 Google Sheets Connection Diagnostic")

# Step 1: Check if secrets are configured
st.header("1. Checking Streamlit Secrets")

secrets_found = {}

# Check for sheet name/URL
if 'GOOGLE_SHEET_NAME' in st.secrets:
    secrets_found['GOOGLE_SHEET_NAME'] = st.secrets['GOOGLE_SHEET_NAME']
    st.success(f"✅ GOOGLE_SHEET_NAME: `{secrets_found['GOOGLE_SHEET_NAME']}`")
else:
    st.error("❌ GOOGLE_SHEET_NAME not found in secrets")

if 'GOOGLE_SHEET_URL' in st.secrets:
    st.success("✅ GOOGLE_SHEET_URL found")
    secrets_found['GOOGLE_SHEET_URL'] = "Found"

# Check for credentials
if 'gcp_service_account' in st.secrets:
    st.success("✅ gcp_service_account found in secrets")
    
    # Check the service account email
    try:
        service_email = st.secrets["gcp_service_account"].get("client_email", "Not found")
        st.info(f"📧 Service Account Email: `{service_email}`")
        st.warning("⚠️ Make sure your Google Sheet is shared with this email address!")
        
        # Check type field
        type_field = st.secrets["gcp_service_account"].get("type", "Not found")
        if type_field == "service_account":
            st.success(f"✅ Type field correct: `{type_field}`")
        else:
            st.error(f"❌ Type field incorrect: `{type_field}` (should be 'service_account')")
    except Exception as e:
        st.error(f"Error reading service account details: {e}")
else:
    st.error("❌ gcp_service_account NOT found in secrets")

# Step 2: Try to authenticate
st.header("2. Testing Authentication")

if st.button("Test Google Sheets Connection"):
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        
        if 'gcp_service_account' not in st.secrets:
            st.error("Cannot test - no credentials in secrets")
        else:
            # Get credentials
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # Force type to be correct
            creds_dict['type'] = 'service_account'
            
            # Define scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Create credentials
            with st.spinner("Creating credentials..."):
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                st.success("✅ Credentials created")
            
            # Authenticate
            with st.spinner("Authenticating with Google..."):
                client = gspread.authorize(creds)
                st.success("✅ Authenticated successfully")
            
            # Try to open the sheet
            sheet_name = st.secrets.get("GOOGLE_SHEET_NAME")
            sheet_url = st.secrets.get("GOOGLE_SHEET_URL")
            
            if sheet_name:
                with st.spinner(f"Opening sheet: {sheet_name}"):
                    try:
                        sheet = client.open(sheet_name)
                        st.success(f"✅ Opened sheet: {sheet_name}")
                        
                        # List worksheets
                        worksheets = sheet.worksheets()
                        st.write("**Available worksheets:**")
                        for ws in worksheets:
                            st.write(f"  • {ws.title}")
                        
                        # Try to open Form Responses 1
                        try:
                            worksheet = sheet.worksheet("Form Responses 1")
                            st.success("✅ Found 'Form Responses 1' worksheet")
                            
                            # Get data
                            data = worksheet.get_all_records()
                            st.success(f"✅ Retrieved {len(data)} records")
                            
                            if data:
                                df = pd.DataFrame(data)
                                st.write("**Columns found:**")
                                for col in df.columns:
                                    st.write(f"  • {col}")
                                
                                st.write("\n**Preview of data:**")
                                st.dataframe(df.head())
                        
                        except gspread.exceptions.WorksheetNotFound:
                            st.error("❌ 'Form Responses 1' worksheet not found")
                            st.info("Your form might be using a different worksheet name")
                            
                    except gspread.exceptions.SpreadsheetNotFound:
                        st.error(f"❌ Sheet '{sheet_name}' not found")
                        st.write("**Possible issues:**")
                        st.write("1. Sheet name doesn't match exactly (check capitalization)")
                        st.write(f"2. Sheet not shared with: `{service_email}`")
                        st.write("3. Sheet might have been renamed or deleted")
                        
                        # List available sheets
                        st.write("\n**Sheets accessible to service account:**")
                        try:
                            sheets = client.openall()
                            if sheets:
                                for s in sheets[:10]:
                                    st.write(f"  • {s.title}")
                            else:
                                st.warning("No sheets found - share at least one sheet with the service account")
                        except:
                            st.error("Could not list sheets")
            
            elif sheet_url:
                with st.spinner("Opening sheet by URL..."):
                    try:
                        sheet = client.open_by_url(sheet_url)
                        st.success("✅ Opened sheet by URL")
                    except Exception as e:
                        st.error(f"Failed to open by URL: {e}")
            else:
                st.warning("No sheet name or URL configured")
                
    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        with st.expander("Full error details"):
            st.code(traceback.format_exc())

# Step 3: Show setup checklist
st.header("3. Setup Checklist")

checklist = {
    "Google Cloud Project created": "Create at console.cloud.google.com",
    "Google Sheets API enabled": "Enable in APIs & Services → Library",
    "Google Drive API enabled": "Enable in APIs & Services → Library",
    "Service Account created": "Create in APIs & Services → Credentials",
    "Credentials added to Streamlit Secrets": "Add [gcp_service_account] section",
    "Sheet name added to secrets": "Add GOOGLE_SHEET_NAME",
    "Sheet shared with service account": "Click Share in Google Sheets",
    "Form connected to Sheet": "In Google Forms → Responses → Sheets icon"
}

for item, instruction in checklist.items():
    col1, col2 = st.columns([3, 2])
    with col1:
        st.write(f"☐ {item}")
    with col2:
        st.caption(instruction)

# Step 4: Common fixes
st.header("4. Most Common Issues")

with st.expander("❌ 'Unexpected credentials type' Error"):
    st.markdown("""
    **Fix:** Make sure your secrets have exactly:
    ```toml
    [gcp_service_account]
    type = "service_account"
    ```
    Not `type = service_account` (missing quotes) or any other variation.
    """)

with st.expander("❌ 'Sheet not found' Error"):
    st.markdown("""
    **Fixes:**
    1. Check the exact sheet name (case-sensitive, including spaces)
    2. Share the sheet with your service account email
    3. Make sure the sheet still exists and hasn't been renamed
    """)

with st.expander("❌ 'No credentials found' Error"):
    st.markdown("""
    **Fix:** Add your service account JSON to Streamlit Secrets:
    1. Go to your app settings in Streamlit Cloud
    2. Navigate to Secrets
    3. Add the [gcp_service_account] section with all fields from your JSON
    """)

# Show current configuration for debugging
if st.checkbox("Show current configuration (for debugging)"):
    st.json({
        "Secrets found": list(st.secrets.keys()) if hasattr(st, 'secrets') else [],
        "Has gcp_service_account": 'gcp_service_account' in st.secrets if hasattr(st, 'secrets') else False,
        "Sheet name configured": 'GOOGLE_SHEET_NAME' in secrets_found,
        "Sheet URL configured": 'GOOGLE_SHEET_URL' in secrets_found
    })
