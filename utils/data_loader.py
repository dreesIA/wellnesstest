# utils/data_loader.py
"""
Data loader module for fetching data from Google Sheets connected to Google Forms.
Handles authentication, caching, and data normalization.
"""

import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
from typing import Optional, Dict, Any
import os
import json
from datetime import datetime, timedelta


def get_credentials():
    """
    Get Google Sheets credentials from file or Streamlit secrets.
    """
    # Try to load from Streamlit secrets first (for deployment)
    try:
        if 'gcp_service_account' in st.secrets:
            # Convert to dict if needed
            creds_dict = dict(st.secrets["gcp_service_account"])
            return ServiceAccountCredentials.from_json_keyfile_dict(
                creds_dict,
                ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
            )
    except Exception as e:
        print(f"Error loading from secrets: {e}")
    
    # Fall back to local file
    if os.path.exists("gspread_credentials.json"):
        return ServiceAccountCredentials.from_json_keyfile_name(
            "gspread_credentials.json",
            ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
        )
    
    return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_google_sheet(
    sheet_title: str = None,
    sheet_url: str = None,
    worksheet_name: str = "Form Responses 1",
    use_fallback: bool = True
) -> pd.DataFrame:
    """
    Load data from Google Sheets with fallback to local CSV.
    
    Args:
        sheet_title: Name of the Google Sheet (use this OR sheet_url)
        sheet_url: URL of the Google Sheet (use this OR sheet_title)
        worksheet_name: Name of the worksheet tab (default for Forms)
        use_fallback: Whether to use CSV fallback on error
        
    Returns:
        DataFrame with normalized column names and processed dates
    """
    
    try:
        # Get credentials
        creds = get_credentials()
        if not creds:
            raise FileNotFoundError("No credentials found. Please add gspread_credentials.json or configure Streamlit secrets.")
        
        client = gspread.authorize(creds)
        
        # Open the sheet by title or URL
        if sheet_url:
            sheet = client.open_by_url(sheet_url)
        elif sheet_title:
            sheet = client.open(sheet_title)
        else:
            # Try to get from Streamlit secrets or environment
            sheet_identifier = st.secrets.get("GOOGLE_SHEET_URL") or \
                             st.secrets.get("GOOGLE_SHEET_NAME") or \
                             os.getenv("GOOGLE_SHEET_URL") or \
                             os.getenv("GOOGLE_SHEET_NAME")
            
            if not sheet_identifier:
                raise ValueError("No sheet title or URL provided")
            
            if sheet_identifier.startswith("http"):
                sheet = client.open_by_url(sheet_identifier)
            else:
                sheet = client.open(sheet_identifier)
        
        # Get the worksheet (Form Responses 1 is default for Google Forms)
        worksheet = sheet.worksheet(worksheet_name)
        
        # Get all values and convert to DataFrame
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            raise ValueError("No data found in sheet")
        
        st.success(f"✅ Successfully loaded {len(df)} records from Google Sheets")
            
    except Exception as e:
        error_msg = f"Error loading from Google Sheets: {str(e)}"
        
        if use_fallback and os.path.exists("data/example_export.csv"):
            st.warning(error_msg)
            st.info("📁 Loading from local example data...")
            df = pd.read_csv("data/example_export.csv")
        else:
            st.error(error_msg)
            st.info("""
            **To connect your Google Form:**
            1. Ensure your form is linked to a Google Sheet
            2. Share the sheet with your service account email
            3. Add the sheet URL or name to your configuration
            """)
            raise e
    
    # Normalize and process the DataFrame
    df = normalize_dataframe(df)
    
    return df


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names from Google Forms and process data types.
    FIXED: Handles duplicate columns properly
    
    Args:
        df: Raw DataFrame from Google Sheets or CSV
        
    Returns:
        Processed DataFrame with standardized columns
    """
    
    # Debug: Show original columns
    print(f"Original columns: {list(df.columns)}")
    
    # First, check for and handle duplicate column names
    # This can happen if the form has multiple questions with similar names
    columns = list(df.columns)
    seen = {}
    new_columns = []
    
    for col in columns:
        if col in seen:
            seen[col] += 1
            new_columns.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_columns.append(col)
    
    df.columns = new_columns
    print(f"After handling duplicates: {list(df.columns)}")
    
    # More comprehensive column mapping for Google Forms
    column_mapping = {
        # Timestamp variations
        'Timestamp': 'Timestamp',
        'timestamp': 'Timestamp',
        'Date': 'Timestamp',
        'Submission Time': 'Timestamp',
        
        # Athlete/Name variations
        'Athlete': 'Athlete',
        'Name': 'Athlete',
        'Athlete Name': 'Athlete',
        'Your Name': 'Athlete',
        'Player Name': 'Athlete',
        
        # Sleep variations
        'SleepText': 'SleepText',
        'Sleep Text': 'SleepText',
        'Sleep Duration': 'SleepText',
        'Hours of Sleep': 'SleepText',
        'Sleep Hours': 'SleepText',
        
        # Form question variations (common Google Forms patterns)
        'How did you sleep?': 'Sleep',
        'Sleep Quality': 'Sleep',
        'Rate your sleep quality (1-10)': 'Sleep',
        'Sleep (1-10)': 'Sleep',
        'Sleep': 'Sleep',
        
        'How is your mood?': 'Mood',
        'Mood': 'Mood',
        'Rate your mood (1-10)': 'Mood',
        'Current Mood (1-10)': 'Mood',
        
        'What is your overall energy level?': 'Energy',
        'Energy Level': 'Energy',
        'Energy': 'Energy',
        'Rate your energy (1-10)': 'Energy',
        'Energy Level (1-10)': 'Energy',
        
        'What is your overall stress level?': 'Stress',
        'Stress Level': 'Stress',
        'Stress': 'Stress',
        'Rate your stress (1-10)': 'Stress',
        'Stress Level (1-10)': 'Stress',
        
        'What is your general soreness?': 'Soreness',
        'Soreness': 'Soreness',
        'Muscle Soreness': 'Soreness',
        'Rate your soreness (1-10)': 'Soreness',
        'Soreness Level (1-10)': 'Soreness',
        
        'What is your overall fatigue?': 'Fatigue',
        'Fatigue': 'Fatigue',
        'Fatigue Level': 'Fatigue',
        'Rate your fatigue (1-10)': 'Fatigue',
        'Fatigue Level (1-10)': 'Fatigue',
    }
    
    # Create a new dataframe with renamed columns to avoid duplicates
    renamed_df = pd.DataFrame()
    columns_used = set()
    
    for old_col in df.columns:
        # Check if this column should be renamed
        new_col = None
        
        # First try exact match
        if old_col in column_mapping:
            new_col = column_mapping[old_col]
        else:
            # Try case-insensitive match
            for map_old, map_new in column_mapping.items():
                if old_col.lower().strip() == map_old.lower().strip():
                    new_col = map_new
                    break
        
        # If we found a mapping and haven't used this column yet
        if new_col and new_col not in columns_used:
            renamed_df[new_col] = df[old_col]
            columns_used.add(new_col)
        elif new_col in columns_used:
            # Skip duplicate mappings
            print(f"Skipping duplicate column mapping: {old_col} -> {new_col}")
        else:
            # Keep unmapped columns with original name if not already used
            if old_col not in renamed_df.columns:
                renamed_df[old_col] = df[old_col]
    
    df = renamed_df
    print(f"After renaming: {list(df.columns)}")
    
    # Convert Timestamp to datetime and extract Date
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df['Date'] = df['Timestamp'].dt.date
        df['Date'] = pd.to_datetime(df['Date'])
    
    # Parse sleep duration from text if present
    if 'SleepText' in df.columns:
        df['SleepMinutes'] = df['SleepText'].apply(parse_sleep_duration)
    
    # Convert numeric columns (handle various formats)
    numeric_columns = ['Sleep', 'Mood', 'Energy', 'Stress', 'Soreness', 'Fatigue']
    for col in numeric_columns:
        if col in df.columns:
            # Handle potential string formats like "7/10" or "7 out of 10"
            df[col] = df[col].apply(clean_numeric_value)
    
    # Calculate Readiness score if we have the necessary columns
    required_cols = ['Sleep', 'Mood', 'Energy', 'Stress', 'Soreness', 'Fatigue']
    if all(col in df.columns for col in required_cols):
        df['Readiness'] = calculate_readiness(df)
    
    # Sort by Date and Athlete
    if 'Date' in df.columns:
        df = df.sort_values('Date')
        if 'Athlete' in df.columns:
            df = df.sort_values(['Date', 'Athlete'])
    
    # Remove any completely empty rows
    df = df.dropna(how='all')
    
    # Final check for duplicate columns
    if df.columns.duplicated().any():
        print(f"Warning: Duplicate columns found after processing: {df.columns[df.columns.duplicated()].tolist()}")
        # Remove duplicate columns, keeping first
        df = df.loc[:, ~df.columns.duplicated()]
    
    return df


def clean_numeric_value(value):
    """
    Clean and convert various numeric formats to float.
    Handles formats like "7", "7/10", "7 out of 10", etc.
    """
    if pd.isna(value):
        return None
    
    # If already numeric, return as is
    if isinstance(value, (int, float)):
        return float(value)
    
    # Convert to string and clean
    value_str = str(value).strip()
    
    # Handle "X/10" or "X out of 10" formats
    if '/' in value_str:
        try:
            numerator = float(value_str.split('/')[0].strip())
            return numerator
        except:
            pass
    
    if 'out of' in value_str.lower():
        try:
            numerator = float(value_str.lower().split('out of')[0].strip())
            return numerator
        except:
            pass
    
    # Try direct conversion
    try:
        return float(value_str)
    except:
        return None


def parse_sleep_duration(text):
    """
    Parse sleep duration text to minutes.
    Handles formats like "7 hours", "7h", "7:30", "7.5", etc.
    """
    if pd.isna(text):
        return None
    
    text = str(text).lower().strip()
    
    # Handle "X hours Y minutes" format
    import re
    
    # Try hours and minutes
    match = re.search(r'(\d+\.?\d*)\s*h(?:ours?)?\s*(?:(\d+)\s*m(?:ins?|inutes?)?)?', text)
    if match:
        hours = float(match.group(1))
        minutes = float(match.group(2)) if match.group(2) else 0
        return hours * 60 + minutes
    
    # Try HH:MM format
    match = re.search(r'(\d+):(\d+)', text)
    if match:
        hours = float(match.group(1))
        minutes = float(match.group(2))
        return hours * 60 + minutes
    
    # Try just a number (assume hours)
    match = re.search(r'(\d+\.?\d*)', text)
    if match:
        hours = float(match.group(1))
        # If the number is greater than 20, assume it's already in minutes
        if hours > 20:
            return hours
        else:
            return hours * 60
    
    return None


def calculate_readiness(df: pd.DataFrame) -> pd.Series:
    """
    Calculate readiness score from wellness metrics.
    """
    # Weights for each metric
    weights = {
        'Sleep': 0.25,
        'Mood': 0.15,
        'Energy': 0.20,
        'Stress': -0.15,  # Negative weight (high stress = lower readiness)
        'Soreness': -0.10,  # Negative weight
        'Fatigue': -0.15   # Negative weight
    }
    
    readiness = pd.Series(0, index=df.index)
    
    for metric, weight in weights.items():
        if metric in df.columns:
            if weight < 0:
                # Invert negative metrics (10 - value)
                readiness += (10 - df[metric]) * abs(weight)
            else:
                readiness += df[metric] * weight
    
    # Normalize to 1-10 scale
    readiness = readiness * 10 / sum(abs(w) for w in weights.values())
    
    return readiness.round(2)


def refresh_data():
    """Clear the cache to force data refresh."""
    st.cache_data.clear()
    st.success("🔄 Data refreshed successfully!")


def get_latest_date(df: pd.DataFrame) -> Optional[datetime]:
    """Get the most recent date in the dataset."""
    if 'Date' in df.columns and not df['Date'].isna().all():
        return df['Date'].max()
    return None


def get_athletes(df: pd.DataFrame) -> list:
    """Get unique list of athletes."""
    if 'Athlete' in df.columns:
        return sorted(df['Athlete'].dropna().unique().tolist())
    return []


def validate_google_connection():
    """
    Test the Google Sheets connection and provide diagnostic information.
    """
    try:
        creds = get_credentials()
        if not creds:
            return False, "No credentials found"
        
        client = gspread.authorize(creds)
        # Try to list available sheets (will fail if no access)
        sheets = client.openall()
        return True, f"Connected! Access to {len(sheets)} sheets"
    except Exception as e:
        return False, str(e)
