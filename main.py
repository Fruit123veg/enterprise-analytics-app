import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import os
import time
import datetime
import psycopg2
import matplotlib.pyplot as plt

# 1. Initialize OpenAI Client with Titan Enterprise Gateway
API_KEY = st.secrets["TITAN_API_KEY"]
client = OpenAI(
    base_url="https://ai.titan.in/gateway",
    api_key=API_KEY
)

# 2. Redshift Database Connection Setup (Fetched securely from Streamlit Cloud Secrets)
DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
DB_NAME = st.secrets["DB_NAME"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]

def get_redshift_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

st.title("📊 Enterprise Live Database Analytics Portal")
st.write("Connected Directly to Amazon Redshift View.")

# Create the dedicated history folder if it doesn't exist
HISTORY_FOLDER = "chat_history"
if not os.path.exists(HISTORY_FOLDER):
    os.makedirs(HISTORY_FOLDER)

# Initialize session state lists to track query text and saved chart image paths
if 'chart_history' not in st.session_state:
    st.session_state['chart_history'] = []  
if 'query_history' not in st.session_state:
    st.session_state['query_history'] = []  

# Target View Name provided by your mentor
TARGET_VIEW = "sem_pu_wtch.mv_tgt_wtch_etp_mendix_cs_metrics_bi_store"

# 3. User Input Query
user_query = st.text_input("What would you like to see? (e.g., 'Show a lollipop chart of sales by region' or 'table format')")

if user_query:
    # Get current date configurations to build precise dynamic SQL filters
    today = datetime.date.today()
    current_year = today.year
    current_month = today.month
    
    # Identify the start of the standard Indian Fiscal Year (April 1st)
    fiscal_year_start = f"{current_year}-04-01" if current_month >= 4 else f"{current_year-1}-04-01"
    
    # Generate a unique chart file path
    timestamp = int(time.time())
    current_chart_filename = os.path.join(HISTORY_FOLDER, f"chart_{timestamp}.png").replace("\\", "/")
    
    # SYSTEM INSTRUCTIONS: Handling Charts, Tables, locked MTD defaults, and visual spacing
    prompt = f"""
    You are an expert data analyst. Your job is to output a Redshift SQL query AND the Python display code to address the user's request.
    The data resides in an Amazon Redshift view named: `{TARGET_VIEW}`

    User Query: "{user_query}"
    
    STRICT BUSINESS DICTIONARY & TIME-PERIOD RULES:
    1. DEFAULT TIMELINE (MTD): If the user asks for "sales", "MTD sales", or specifies ANY specific month (e.g., "sales for May", "sales for January"), you MUST check if the user is asking for a specific month.
       - If they ask for a specific month (like "May"), look for that specific month in the database.
       - If they do NOT specify a month (e.g., just "sales"), strictly DEFAULT to the current calendar month and year (Current Year: {current_year}, Current Month: {current_month}).
    2. REVENUE SELECTION: Default strictly to 'retail_revenue' columns. However, if the user explicitly types "service revenue", you MUST calculate using the service revenue column instead.
    3. DATABASE AGGREGATION: The SQL statement MUST perform the `GROUP BY` and `SUM()` aggregation directly inside the database view.

    OUTPUT FORMAT REQUIREMENT:
    You must output your response in exactly two parts separated by a unique delimiter line: '---PLOT_CODE_START---'.
    
    CRITICAL TABLE VS CHART LOGIC:
    - If the user explicitly asks for the output in a "table format", "table", or "grid", your Python code should NOT create a matplotlib chart. Instead, print the dataframe as a beautifully formatted markdown table using `print(df.to_markdown(index=False))`.
    - Otherwise, default to writing Matplotlib plotting code using a pre-existing dataframe named 'df'.

    SUPPORT FOR ANY PICTORIAL REPRESENTATION CHART STYLES:
    You must dynamically write the code for whatever specific visualization style the user explicitly requests:
    - LOLLIPOP CHART: Use `plt.vlines(x=df[x_col], ymin=0, ymax=df[y_col])` combined with `plt.scatter(df[x_col], df[y_col])` to draw lines with clean dots at the top.
    - DONUT CHART: Use `plt.pie(..., wedgeprops=dict(width=0.4, edgecolor='w'))`.
    - BAR CHART / HORIZONTAL BAR CHART: Use `ax.bar()` or `ax.barh()`.
    - LINE / AREA / PIE CHARTS: Use standard `plt.plot()`, `plt.fill_between()`, or `plt.pie()`.

    STRICT VISUALIZATION & EXACT LABELLING RULES (FOR CHARTS):
    - FIXED CURRENCY LABELLING MATH: For data labels on charts, use this exact conditional logic loop in python over the series values:
      If value >= 10000000 -> label as `f"{{value / 10000000:.2f}} Cr"`
      If value >= 100000 and < 10000000 -> label as `f"{{value / 100000:.2f}} Lakh"`
      Otherwise -> label as `f"{{value:.2f}}"`
    
    - READABILITY & SPACING (FIX FOR CLIPPED VALUES): 
      1. Always call `plt.tight_layout()` right before saving to prevent labels or legends from getting cut off.
      2. For vertical graphs (like bar or lollipop), increase the top margin of the Y-axis by 15% using `ax.set_ylim(0, max_val * 1.15)` so data labels are never cramped or cut off at the ceiling.
      3. Place labels clearly beside or above the markers so they never overlap lines.
    
    - Clear the figure at the start using `plt.figure()`.
    - Save the plot using: `plt.savefig("{current_chart_filename}", bbox_inches="tight")`.

    Do not include any standard conversational text explanations.
    """
    
    with st.spinner("Executing Redshift Live Query & Chart Processing..."):
        try:
            # Generate response from Titan Enterprise Gateway
            response = client.chat.completions.create(
                model="gemini-3.1-flash-lite",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            raw_text = response.choices[0].message.content
            
            # Strip markdown code wrapper symbols if present
            raw_text = raw_text.replace("```python", "").replace("```sql", "").replace("```", "").strip()
            
            if "---PLOT_CODE_START---" in raw_text:
                # Safely split SQL logic text from Matplotlib logic text
                sql_statement, plotting_code = raw_text.split("---PLOT_CODE_START---")
                sql_statement = sql_statement.strip()
                plotting_code = plotting_code.strip()
                
                with st.expander("See generated Redshift SQL Query"):
                    st.code(sql_statement, language="sql")
                
                # 1. Safely run the SQL statement against Redshift first to build 'df'
                conn = get_redshift_connection()
                df = pd.read_sql(sql_statement, conn)
                conn.close()
                
                # 2. Check if the code is a Table output or Chart output
                if "to_markdown" in plotting_code:
                    st.subheader("📋 Requested Data Table")
                    st.dataframe(df, use_container_width=True)  # Displays beautiful data grid
                    
                    # Log to history as a text table note
                    st.session_state['chart_history'].append("TABLE_OUTPUT")
                    st.session_state['query_history'].append(user_query)
                else:
                    with st.expander("See executed plotting code"):
                        st.code(plotting_code, language="python")
                    
                    # Clear open plots and execute custom plotting routine
                    plt.close('all')
                    local_vars = {'df': df, 'plt': plt}
                    exec(plotting_code, globals(), local_vars)
                    
                    # Verify chart generation and save to history timeline
                    if os.path.exists(current_chart_filename):
                        st.session_state['chart_history'].append(current_chart_filename)
                        st.session_state['query_history'].append(user_query)
                
            else:
                st.error("The model response formatting structure was unexpected. Please try again.")
                st.write(raw_text)
                
        except Exception as e:
            st.error(f"An error occurred during database execution: {e}")

# --- DISPLAY HISTORICAL TIMELINE ---
if st.session_state['chart_history']:
    st.write("---")
    st.subheader("📜 Live Database Charts & Tables History")
    
    for i in range(len(st.session_state['chart_history']) - 1, -1, -1):
        img_path = st.session_state['chart_history'][i]
        q_text = st.session_state['query_history'][i]
        
        with st.container():
            st.markdown(f"**Query {i+1}:** *\"{q_text}\"*")
            if img_path == "TABLE_OUTPUT":
                st.info("📊 This query was rendered above as a live database table view.")
            elif os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            st.write("") 

# --- CLEAR ACTION BUTTON ---
if st.button("Clear Chat & History"):
    for img_file in st.session_state['chart_history']:
        if os.path.exists(img_file):
            try:
                os.remove(img_file)
            except:
                pass
                
    st.session_state['chart_history'] = []
    st.session_state['query_history'] = []
    plt.close('all')
    st.success("Chat history folder cleaned up and memory cleared!")
    st.rerun()
