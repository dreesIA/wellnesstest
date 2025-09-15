# app.py
"""
Goalkeeper Wellness Tracking Application
Southern Soccer Academy - Swarm FC
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Import from utils folder
from utils.data_loader import load_google_sheet, refresh_data, validate_google_connection
from utils.ai_insights import WellnessAIAnalyst, get_cached_insights

# Page config
st.set_page_config(
    page_title="Goalkeeper Wellness Tracker",
    page_icon="",
    layout="wide"
)

# Title
st.title("Goalkeeper Wellness Dashboard")
st.markdown("Southern Soccer Academy - Swarm FC Goalkeeper Training")

# Sidebar for controls
with st.sidebar:
    # Add logo or fallback
    import os
    if os.path.exists("SSALogoTransparent.jpeg"):
        st.image("SSALogoTransparent.jpeg", use_column_width=True)
    else:
        # Styled fallback when image not found
        st.markdown("""
        <div style="text-align: center; padding: 20px; background-color: #B8352F; border-radius: 10px; margin-bottom: 20px;">
            <h2 style="color: white; margin: 0;"> SWARM FC</h2>
            <p style="color: white; margin: 5px 0 0 0; font-size: 0.9em;">Goalkeeper Academy</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.header("Controls")
    
    # Refresh button
    if st.button("Refresh Data"):
        refresh_data()
    
    # Auto-refresh option
    auto_refresh = st.checkbox("Auto-refresh every 5 minutes")
    if auto_refresh:
        st.info("Data will refresh automatically")
    
    # Add keeper info at bottom of sidebar
    st.markdown("---")
    st.markdown("**Southern Soccer Academy**")
    st.caption("Swarm Goalkeepers")

# Load data
try:
    # Load from Google Sheets
    df = load_google_sheet(
        worksheet_name="Form Responses 1"  # Default for Google Forms
    )
    
    # Filter for goalkeepers only if there's a position column
    if 'Position' in df.columns:
        df = df[df['Position'].str.contains('goal|keeper|gk', case=False, na=False)]
    
    # Display basic stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Responses", len(df))
    
    with col2:
        st.metric("Goalkeepers", df['Athlete'].nunique() if 'Athlete' in df.columns else 0)
    
    with col3:
        latest_date = df['Date'].max() if 'Date' in df.columns else None
        st.metric("Latest Entry", latest_date.strftime("%Y-%m-%d") if latest_date else "N/A")
    
    with col4:
        avg_readiness = df['Readiness'].mean() if 'Readiness' in df.columns else 0
        st.metric("Avg GK Readiness", f"{avg_readiness:.1f}")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Goalkeepers Overview", "Individual Keeper", "AI Insights", "Raw Data"])
    
    with tab1:
        st.header("Goalkeepers Overview")
        
        # Get list of goalkeepers
        if 'Athlete' in df.columns:
            goalkeepers = df['Athlete'].unique()
            
            # Average metrics across all goalkeepers
            st.subheader("Average Goalkeeper Metrics")
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            metrics = [
                ('Sleep', '', col1),
                ('Mood', '', col2),
                ('Energy', '', col3),
                ('Stress', '', col4),
                ('Soreness', '', col5),
                ('Fatigue', '', col6)
            ]
            
            for metric, emoji, col in metrics:
                if metric in df.columns:
                    avg_value = df[metric].mean()
                    if pd.notna(avg_value):
                        with col:
                            st.metric(f"{emoji} {metric}", f"{avg_value:.1f}/10")
            
            # Trend chart for average goalkeeper readiness
            if 'Readiness' in df.columns and 'Date' in df.columns:
                st.subheader("Goalkeeper Readiness Trends")
                
                # Calculate daily averages
                daily_avg = df.groupby('Date')[['Readiness', 'Sleep', 'Energy', 'Mood']].mean().reset_index()
                
                # Create the chart
                chart_data = daily_avg.set_index('Date')
                st.line_chart(chart_data)
            
            # Individual goalkeeper status cards
            st.subheader("Individual Goalkeeper Status")
            
            # Create columns for goalkeeper cards
            cols = st.columns(3)
            
            for idx, gk in enumerate(goalkeepers):
                gk_data = df[df['Athlete'] == gk]
                if not gk_data.empty:
                    latest = gk_data.iloc[-1]
                    
                    with cols[idx % 3]:
                        # Create a card for each goalkeeper
                        with st.container():
                            st.markdown(f"### {gk}")
                            
                            if 'Readiness' in latest.index:
                                readiness = latest['Readiness']
                                if pd.notna(readiness):
                                    # Color code based on readiness
                                    if readiness >= 7:
                                        color = ""
                                    elif readiness >= 5:
                                        color = ""
                                    else:
                                        color = ""
                                    
                                    st.markdown(f"{color} **Readiness: {readiness:.1f}/10**")
                            
                            # Show last update
                            if 'Date' in latest.index:
                                st.caption(f"Last update: {latest['Date'].strftime('%Y-%m-%d')}")
                            
                            st.markdown("---")
        
    with tab2:
        st.header("Individual Goalkeeper Analysis")
        
        # Goalkeeper selector
        goalkeepers = df['Athlete'].unique() if 'Athlete' in df.columns else []
        selected_gk = st.selectbox("Select Goalkeeper", goalkeepers)
        
        if selected_gk:
            gk_df = df[df['Athlete'] == selected_gk]
            
            # Display latest metrics
            if not gk_df.empty:
                latest = gk_df.iloc[-1]
                
                st.subheader(f"Current Status - {selected_gk}")
                
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                
                metrics = [
                    ('Readiness', '', col1),
                    ('Sleep', '', col2),
                    ('Energy', '', col3),
                    ('Stress', '', col4),
                    ('Soreness', '', col5),
                    ('Fatigue', '', col6)
                ]
                
                for metric, emoji, col in metrics:
                    if metric in latest.index:
                        value = latest[metric]
                        if pd.notna(value):
                            with col:
                                st.metric(f"{emoji} {metric}", f"{value:.1f}/10")
                
                # Individual trend chart
                st.subheader(f"Wellness Trends - {selected_gk}")
                
                trend_metrics = ['Readiness', 'Sleep', 'Energy', 'Mood']
                available_metrics = [m for m in trend_metrics if m in gk_df.columns]
                
                if available_metrics and 'Date' in gk_df.columns:
                    chart_data = gk_df[['Date'] + available_metrics].set_index('Date')
                    st.line_chart(chart_data)
                
                # Recent history table
                st.subheader("Recent History")
                display_cols = ['Date', 'Readiness', 'Sleep', 'Energy', 'Stress', 'Soreness', 'Fatigue']
                available_cols = [col for col in display_cols if col in gk_df.columns]
                
                recent_data = gk_df[available_cols].tail(7)
                st.dataframe(recent_data, use_container_width=True, hide_index=True)
    
    with tab3:
        st.header("AI-Powered Goalkeeper Insights")
        
        # Check if API key is configured
        analyst = WellnessAIAnalyst()
        if not analyst.client:
            st.warning("OpenAI API key not configured.")
            with st.expander("Setup Instructions"):
                st.markdown("""
                **To enable AI insights:**
                
                1. Get an API key from [OpenAI](https://platform.openai.com/api-keys)
                2. Add to Streamlit Secrets: `OPENAI_API_KEY=your-key`
                """)
        else:
            insight_type = st.radio(
                "Select Insight Type",
                ["Individual Goalkeeper", "All Goalkeepers Overview", "Comparative Analysis"]
            )
            
            if insight_type == "Individual Goalkeeper":
                gk = st.selectbox("Select goalkeeper for AI analysis", goalkeepers, key="ai_gk")
                
                if st.button("Generate Insights"):
                    with st.spinner("Analyzing goalkeeper data..."):
                        # Customize the prompt for goalkeeper-specific insights
                        insights = get_cached_insights(df, gk, "individual")
                        st.markdown(insights)
            
            elif insight_type == "All Goalkeepers Overview":
                if st.button("Generate Goalkeeper Group Insights"):
                    with st.spinner("Analyzing all goalkeepers..."):
                        # Generate insights for all goalkeepers as a group
                        insights = get_cached_insights(df, None, "team")
                        st.markdown(insights)
            
            else:  # Comparative Analysis
                col1, col2 = st.columns(2)
                with col1:
                    gk1 = st.selectbox("First goalkeeper", goalkeepers, key="comp1")
                with col2:
                    gk2 = st.selectbox("Second goalkeeper", goalkeepers, key="comp2")
                
                if st.button("Compare Goalkeepers"):
                    if gk1 != gk2:
                        with st.spinner("Generating comparison..."):
                            insights = get_cached_insights(
                                df, gk1, "comparison", athlete2=gk2
                            )
                            st.markdown(insights)
                    else:
                        st.error("Please select two different goalkeepers")
    
    with tab4:
        st.header("Raw Data")
        
        # Data filters
        col1, col2 = st.columns(2)
        with col1:
            filter_gk = st.multiselect(
                "Filter by Goalkeeper",
                options=goalkeepers if 'Athlete' in df.columns else [],
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
        if filter_gk:
            filtered_df = filtered_df[filtered_df['Athlete'].isin(filter_gk)]
        
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
            label="Download Goalkeeper Data as CSV",
            data=csv,
            file_name=f"goalkeeper_wellness_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    
    with st.expander("Setup Instructions", expanded=True):
        st.markdown("""
        ### Goalkeeper Wellness Tracking Setup
        
        **1. Create your Google Form** with these fields:
        - Name/Goalkeeper (Text)
        - Position (if tracking multiple positions)
        - Sleep Quality (1-10 scale)
        - Mood (1-10 scale)
        - Energy Level (1-10 scale)
        - Stress Level (1-10 scale)
        - Soreness (1-10 scale)
        - Fatigue (1-10 scale)
        
        **2. The form is already connected to Google Sheets**
        
        **3. For AI insights, add OpenAI API key to Streamlit Secrets**
        """)

# Footer
st.markdown("---")
st.markdown("🥅 Goalkeeper Wellness Tracker | Southern Soccer Academy - Swarm FC")
