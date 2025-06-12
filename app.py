import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import json
import requests

# --- Configuration & Constants ---
st.set_page_config(page_title="BFM Financial Analysis", page_icon="💰", layout="wide")

# API Key has been inserted as requested
GOOGLE_API_KEY = "AIzaSyBynjotD4bpji6ThOtpO14tstc-qF2cFp4"

# --- CSS Styling ---
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #005A9C 0%, #002D4C 100%); /* Navy/Gov Blue Gradient */
    padding: 2rem;
    border-radius: 15px;
    color: white;
    text-align: center;
    margin-bottom: 2rem;
}
.stApp {
    background-color: #f0f2f6;
}
.stButton>button {
    background-color: #007bff;
    color: white;
    border-radius: 8px;
    border: none;
    padding: 10px 20px;
}
.stTextInput>div>div>input {
    background-color: #ffffff;
}
.stDataFrame {
    border: 2px solid #e0e0e0;
    border-radius: 10px;
}
.status-card {
    border-radius: 15px;
    padding: 1.5rem;
    text-align: center;
    margin: 0.5rem 0;
    color: white;
    min-height: 200px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.urgent-expiry {
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
  100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
}
</style>
""", unsafe_allow_html=True)


# --- Core AI and Data Functions ---

def get_federal_holidays(year):
    """Returns a list of federal holidays for a given year."""
    if year == 2025:
        return [
            datetime(2025, 1, 1), datetime(2025, 1, 20), datetime(2025, 2, 17),
            datetime(2025, 5, 26), datetime(2025, 6, 19), datetime(2025, 7, 4),
            datetime(2025, 9, 1), datetime(2025, 10, 13), datetime(2025, 11, 11),
            datetime(2025, 11, 27), datetime(2025, 12, 25)
        ]
    return []

def extract_data_for_ai_analysis(csv_file, col_map):
    """
    Extracts data for branches BL12200 and BL16200 from the
    Consolidated Data CSV for detailed AI analysis.
    """
    if not csv_file:
        return None
    try:
        df = pd.read_csv(csv_file, header=1)
        df.columns = [str(c).strip() for c in df.columns]
        target_branches = ['BL12200', 'BL16200']
        required_cols = [col_map['work_ctr']]
        if not all(col in df.columns for col in required_cols):
            st.error(f"The required column '{col_map['work_ctr']}' was not found in the uploaded file.")
            return None
        mask = df[col_map['work_ctr']].astype(str).str.contains('|'.join(target_branches), na=False)
        relevant_data = df[mask]
        if relevant_data.empty:
            st.warning(f"No data found for branches {', '.join(target_branches)}.")
            return None
        analysis_data = relevant_data.to_dict(orient='records')
        return analysis_data
    except Exception as e:
        st.error(f"Error processing the Consolidated Data file: {e}")
        return None


def prompt_for_gemini(data_for_ai):
    """Creates a detailed, specific prompt for the Gemini API."""
    data_json = json.dumps(data_for_ai, indent=2)
    prompt = f"""
    As an expert financial analyst, your name is Gemini. You are tasked with providing a detailed financial evaluation for Brian Benedicks, a Project Manager.

    **User Information:**
    - **Name:** Brian Benedicks
    - **Role:** Project Manager (PM)
    - **Responsibilities:** He is the primary PM for branch **BL12200** and is also a team member in branch **BL16200**.

    **Data Provided:**
    The following is a list of project data records for the branches he is involved with. The data is for FY25 and is current as of early June 2025.

    ```json
    {data_json}
    ```

    **Your Task:**
    Based *only* on the data provided above, please generate a comprehensive yearly spend evaluation. Structure your response with the following sections:

    1.  **Overall Summary:** Start with a brief, high-level summary for the PM.
    2.  **Branch BL12200 Analysis:** Provide a detailed breakdown for this branch. For each project, or logical project groups, analyze the budget vs. actual costs, planned hours ('Work') vs. actual hours ('Actual Work'), and the hourly rate ('Rate'). Pay close attention to the 'Work Comp. Date' and flag projects with approaching deadlines.
    3.  **Branch BL16200 Analysis:** Provide a similar detailed breakdown for the projects he is involved with in this branch.
    4.  **Key Factors & Recommendations:**
        * Explicitly mention the impact of work completion dates.
        * Discuss the hourly rates and their consistency.
        * List the standard 2025 federal holidays as non-working days that must be factored into project timelines.
        * Provide actionable recommendations based on your analysis (e.g., monitor specific projects, watch for budget overruns, etc.).

    Format your response using clear headings and markdown for readability. Be direct, professional, and data-driven in your analysis.
    """
    return prompt


def ask_gemini(prompt):
    """Sends the request to the Gemini API and returns the response."""
    if not GOOGLE_API_KEY:
        st.error("Google API Key is not configured.")
        return None

    # ---FIXED: Updated the model from 'gemini-pro' to 'gemini-1.5-pro-latest' to resolve 404 error ---
    model_name = 'gemini-1.5-pro-latest'
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GOOGLE_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        candidates = response.json().get('candidates', [])
        if candidates:
            return candidates[0]['content']['parts'][0]['text']
        else:
            st.error("No content received from Gemini. The response may be empty or blocked.")
            st.json(response.json())
            return None
    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP error occurred: {http_err}")
        st.error(f"Full response: {response.text}")
        # Add a note for the user to check their API key's configuration
        st.warning("If this is a 403 Forbidden error, please ensure the 'Generative Language API' is enabled for your project in the Google Cloud Console.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None


# --- Streamlit UI ---
st.markdown("<h1 class='main-header'>BFM Financial Performance Analysis</h1>", unsafe_allow_html=True)

st.sidebar.header("⚙️ Configuration")
uploaded_file = st.sidebar.file_uploader(
    "Upload 'Consolidated Data.csv'",
    type=['csv']
)

st.sidebar.subheader("Advanced: Column Mapping")
st.sidebar.info("Adjust these if your CSV file has different column names.")
col_map = {
    'work_ctr': st.sidebar.text_input("Work Center Column", "Work Ctr"),
    'pm': st.sidebar.text_input("PM Column", "PM"),
    'desc': st.sidebar.text_input("Description Column", "Project Description"),
    'co': st.sidebar.text_input("CO Column", "Billing Element"),
    'appn': st.sidebar.text_input("APPN Column", "APPN"),
    'balance': st.sidebar.text_input("Balance Column", "Balance"),
    'budget': st.sidebar.text_input("Budget Column", "Budget"),
    'actual_costs': st.sidebar.text_input("Actual Costs Column", "Actual Costs"),
    'work': st.sidebar.text_input("Planned Work Column", "Work"),
    'actual_work': st.sidebar.text_input("Actual Work Column", "Actual Work"),
    'rate': st.sidebar.text_input("Rate Column", "Rate"),
    'work_comp_date': st.sidebar.text_input("Completion Date Column", "Work Comp. Date")
}

if uploaded_file:
    st.header("📊 AI-Powered Financial Evaluation")
    
    if st.button("🚀 Generate Analysis for Brian Benedicks"):
        with st.spinner("Extracting relevant data for analysis..."):
            data_for_ai = extract_data_for_ai_analysis(uploaded_file, col_map)

        if data_for_ai:
            st.success("Data extracted successfully. Asking Gemini for insights...")
            with st.spinner("🤖 Gemini is analyzing the data... This may take a moment."):
                prompt = prompt_for_gemini(data_for_ai)
                ai_response = ask_gemini(prompt)

            if ai_response:
                st.markdown(ai_response)
            else:
                st.error("Could not retrieve analysis from AI. See error details above.")
        else:
            st.error("Could not extract the necessary data. Please check the file and column mappings.")
else:
    st.info("👋 Welcome! Please upload your 'Consolidated Data.csv' file using the sidebar to begin.")
