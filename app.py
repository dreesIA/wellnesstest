# main.py or app.py
"""
Main Streamlit application for Wellness Tracking
"""

import streamlit as st
import pandas as pd
from utils.data_loader import load_google_sheet, refresh_data, validate_google_connection
from utils.ai_insights import WellnessAIAnalyst, get_cached_insights

# Page config
st.set_page_config(
    page_title="Team Wellness Tracker",
    page_icon="💪",
    layout="wide"
)

# Title
st.title("🏃 Team Wellness Dashboard")
st.markdown("Connected to Google Forms for real-time wellness tracking")

# Sidebar for controls
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Connection status
    with st.expander("🔗 Google Sheets Connection"):
        if st.button("Test Connection"):
            success, message = validate_google_connection()
            if success:
                st.success(message)
            else:
                st.error(message)
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        refresh_data()
    
    # Auto-refresh option
    auto_refresh = st.checkbox("Auto-refresh every 5 minutes")
    if auto_refresh:
        st.info("Data will refresh automatically")

# Load data
try:
    # You can specify the sheet name or URL here
    # The function will also check environment variables and secrets
    df = load_google_sheet(
        sheet_title="Your Wellness Form (Responses)",  # Replace with your sheet name
        worksheet_name="Form Responses 1"  # Default for Google Forms
    )
    
    # Display basic stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Responses", len(df))
    
    with col2:
        st.metric("Athletes", df['Athlete'].nunique() if 'Athlete' in df.columns else 0)
    
    with col3:
        latest_date = df['Date'].max() if 'Date' in df.columns else None
        st.metric("Latest Entry", latest_date.strftime("%Y-%m-%d") if latest_date else "N/A")
    
    with col4:
        avg_readiness = df['Readiness'].mean() if 'Readiness' in df.columns else 0
        st.metric("Avg Team Readiness", f"{avg_readiness:.1f}")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "👤 Individual", "🤖 AI Insights", "📈 Raw Data"])
    
    with tab1:
        st.header("Team Overview")
        
        # Recent submissions
        st.subheader("Recent Submissions")
        recent = df.nlargest(10, 'Timestamp') if 'Timestamp' in df.columns else df.head(10)
        
        display_cols = ['Timestamp', 'Athlete', 'Readiness', 'Sleep', 'Energy', 'Stress']
        available_cols = [col for col in display_cols if col in recent.columns]
        
        st.dataframe(
            recent[available_cols],
            use_container_width=True,
            hide_index=True
        )
        
        # Team averages chart
        if 'Readiness' in df.columns:
            st.subheader("Team Readiness Trend")
            daily_avg = df.groupby('Date')['Readiness'].mean().reset_index()
            st.line_chart(daily_avg.set_index('Date'))
    
    with tab2:
        st.header("Individual Athlete View")
        
        # Athlete selector
        athletes = df['Athlete'].unique() if 'Athlete' in df.columns else []
        selected_athlete = st.selectbox("Select Athlete", athletes)
        
        if selected_athlete:
            athlete_df = df[df['Athlete'] == selected_athlete]
            
            # Display latest metrics
            if not athlete_df.empty:
                latest = athlete_df.iloc[-1]
                
                col1, col2, col3, col4 = st.columns(4)
                
                metrics = [
                    ('Readiness', '🎯'),
                    ('Sleep', '😴'),
                    ('Energy', '⚡'),
                    ('Stress', '😰')
                ]
                
                for (metric, emoji), col in zip(metrics, [col1, col2, col3, col4]):
                    if metric in latest.index:
                        value = latest[metric]
                        if pd.notna(value):
                            col.metric(f"{emoji} {metric}", f"{value:.1f}/10")
                
                # Individual trend chart
                st.subheader(f"Wellness Trends - {selected_athlete}")
                
                trend_metrics = ['Readiness', 'Sleep', 'Energy', 'Mood']
                available_metrics = [m for m in trend_metrics if m in athlete_df.columns]
                
                if available_metrics and 'Date' in athlete_df.columns:
                    chart_data = athlete_df[['Date'] + available_metrics].set_index('Date')
                    st.line_chart(chart_data)
    
    with tab3:
        st.header("🤖 AI-Powered Insights")
        
        # Check if API key is configured
        analyst = WellnessAIAnalyst()
        if not analyst.client:
            st.warning("⚠️ OpenAI API key not configured. Add OPENAI_API_KEY to enable AI insights.")
            st.info("You can add it to your `.env` file or Streamlit secrets.")
        else:
            insight_type = st.radio(
                "Select Insight Type",
                ["Individual Athlete", "Team Overview", "Comparative Analysis"]
            )
            
            if insight_type == "Individual Athlete":
                athlete = st.selectbox("Select athlete for AI analysis", athletes, key="ai_athlete")
                
                if st.button("Generate Insights"):
                    with st.spinner("Analyzing wellness data..."):
                        insights = get_cached_insights(df, athlete, "individual")
                        st.markdown(insights)
            
            elif insight_type == "Team Overview":
                if st.button("Generate Team Insights"):
                    with st.spinner("Analyzing team data..."):
                        insights = get_cached_insights(df, None, "team")
                        st.markdown(insights)
            
            else:  # Comparative Analysis
                col1, col2 = st.columns(2)
                with col1:
                    athlete1 = st.selectbox("First athlete", athletes, key="comp1")
                with col2:
                    athlete2 = st.selectbox("Second athlete", athletes, key="comp2")
                
                if st.button("Compare Athletes"):
                    if athlete1 != athlete2:
                        with st.spinner("Generating comparison..."):
                            insights = get_cached_insights(
                                df, athlete1, "comparison", athlete2=athlete2
                            )
                            st.markdown(insights)
                    else:
                        st.error("Please select two different athletes")
    
    with tab4:
        st.header("📈 Raw Data")
        
        # Data filters
        col1, col2 = st.columns(2)
        with col1:
            filter_athlete = st.multiselect(
                "Filter by Athlete",
                options=athletes,
                default=[]
            )
        
        with col2:
            if 'Date' in df.columns:
                date_range = st.date_input(
                    "Date Range",
                    value=(df['Date'].min(), df['Date'].max()),
                    min_value=df['Date'].min(),
                    max_value=df['Date'].max()
                )
        
        # Apply filters
        filtered_df = df.copy()
        if filter_athlete:
            filtered_df = filtered_df[filtered_df['Athlete'].isin(filter_athlete)]
        
        if 'Date' in df.columns and len(date_range) == 2:
            filtered_df = filtered_df[
                (filtered_df['Date'] >= pd.to_datetime(date_range[0])) &
                (filtered_df['Date'] <= pd.to_datetime(date_range[1]))
            ]
        
        # Display data
        st.dataframe(filtered_df, use_container_width=True)
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"wellness_data_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    
    st.info("""
    ### 📋 Setup Instructions:
    
    1. **Create your Google Form** with these fields:
       - Name/Athlete (Text)
       - Sleep Quality (1-10 scale)
       - Mood (1-10 scale)
       - Energy Level (1-10 scale)
       - Stress Level (1-10 scale)
       - Soreness (1-10 scale)
       - Fatigue (1-10 scale)
    
    2. **Link Form to Google Sheets**:
       - In Google Forms, go to Responses tab
       - Click the Sheets icon to create linked spreadsheet
    
    3. **Set up API access**:
       - Create service account in Google Cloud Console
       - Download credentials as `gspread_credentials.json`
       - Share your Google Sheet with the service account email
    
    4. **Configure the app**:
       - Add sheet name/URL to environment variables
       - Add OpenAI API key for AI insights
    """)

# Footer
st.markdown("---")
st.markdown("💪 Wellness Tracker | Data synced with Google Forms")