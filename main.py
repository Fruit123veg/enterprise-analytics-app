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
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IndoMDZzRWt6TEhKNXNOTmFVeVJZMl82TzhLMCIsImtpZCI6IndoMDZzRWt6TEhKNXNOTmFVeVJZMl82TzhLMCJ9.eyJhdWQiOiJhcGk6Ly80NmVjZWEzYy05MTU4LTQwM2QtYmJjMS0xNTExNTdlMTgyZWEiLCJpc3MiOiJodHRwczovL3N0cy53aW5kb3dzLm5ldC83Y2M5MWMzOC02NDhlLTRjZTItYTRlNC01MTdhZTM5ZmMxODkvIiwiaWF0IjoxNzgxMDAxMzc3LCJuYmYiOjE3ODEwMDEzNzcsImV4cCI6MTc4MTAwNjc1NywiYWNyIjoiMSIsImFpbyI6IkFkUUFLLzhjQUFBQVo0L2FiZzcvMENrM3owUmhKZmZCYjJIVDlVR2I4cDZYSWkwWmptQ2VIY2MyYTM5akxKNmdJaWpJTVZtSGtOQUNHODJYeXR1QktVR2plVTdqWDAybVA0WkhDZjdsWXFyS21kUHBYaGNUTWU3MkYreDZXUXJUT3l6TEZ4ZDR5bjFJeStVK1RWYWM3WHRmQkNFQkxmZ3l4cGlhUFNJM2ZRV2R1bm03TXRsNk5RdFc3d093dFkxT1NXK1kwMExsMG1zOEZXdE1UVDhQL2x4SGZiaWRnenBuYjFUdUJudTlnMXBSSEt5RUtScFBCK2tHMGJyUUtKNER6eTVLZDFnd0ZtSDdEVzJrdTV5MXZkQlROT1dlM3V5V29nPT0iLCJhbXIiOlsicnNhIiwibWZhIl0sImFwcGlkIjoiYjc0YzZiYjAtMzk5Ni00NWUyLWE4NjQtNTlmYjU3YmU1NGRhIiwiYXBwaWRhY3IiOiIxIiwiZGV2aWNlaWQiOiIyYThkN2U2Mi00ZjgzLTQ3NGEtYjY4Ny03MjEwZjczMTNhNTEiLCJmYW1pbHlfbmFtZSI6IkRldmkgWWFzYXN3aSIsImdpdmVuX25hbWUiOiJWZW11bGEiLCJpcGFkZHIiOiIxNjcuMTAzLjc0LjEyMiIsIm5hbWUiOiJWZW11bGEgRGV2aSBZYXNhc3dpIiwib2lkIjoiNmE3NTkyNzQtNDIzZC00MDIyLWI1YzgtOWE1OTU1ZjA1ZTA4Iiwib25wcmVtX3NpZCI6IlMtMS01LTIxLTEwNTY4NjM2MzItODY0NzExODEtMTg0OTYwMTEzLTc3MDQxIiwicmgiOiIxLkFWWUFPQnpKZkk1azRreWs1RkY2NDVfQmlUenE3RVpZa1QxQXU4RVZFVmZoZ3VxZkFDUldBQS4iLCJzY3AiOiJhY2Nlc3NfYXNfdXNlciIsInNpZCI6IjAwYmFhNTU5LWE3M2MtMWUyYS05YzA5LWU2YWI5MjAxZjYxZCIsInN1YiI6IlBHUjBjdTd0VFVBMVhtWlFXaGQxNHBXcDZEUkZBdm9jR0NMSzZxRDBGOVkiLCJ0aWQiOiI3Y2M5MWMzOC02NDhlLTRjZTItYTRlNC01MTdhZTM5ZmMxODkiLCJ1bmlxdWVfbmFtZSI6InZlbXVsYWRldml5QHRpdGFuLmNvLmluIiwidXBuIjoidmVtdWxhZGV2aXlAdGl0YW4uY28uaW4iLCJ1dGkiOiJBX05lcEpKa0NrQ2pJLWRoc1NZWkFBIiwidmVyIjoiMS4wIiwieG1zX2Z0ZCI6Im83RFpCcnROMW5YVHE0MzRoLU1SVHVmUE9PNEthbHJiYklXTXk3RG5FN3NCYTI5eVpXRmpaVzUwY21Gc0xXUnpiWE0ifQ.Tta1ZXfOtlI-RxejL_EJd0z9MVgIjDwToB0rr4AVj6DTnHrHD8fNMBMvjmcUcjZVkwYHS2oQEinK7i4eq0WHggoc5XEUe16T3mhEoNr8EId3Xl2Ca7z1S0OxzKzTkR5PKtYU_n_Jqxu_tmERMTuuNSj_NQSDc8n-Eo1djvtjsR6R9HpIoSCCeP9M4Wl16z5hFRT9wYj7lRyq0etNFtJGzQIefnRR7YBjZ5O7nTrcQGSeSlKpsiwzzO8r4yATFXCGiDyabe_LsEjBXnbG98VD8bQVvrbDy1u304vkjb05N2pAodh3v7tUo9U4xAQLWm1yY1OH4ypKkMu0IeBfdvnf2A"  # Replace with your actual paid key string
client = OpenAI(
    base_url="https://ai.titan.in/gateway",
    api_key=API_KEY
)

# 2. Redshift Database Connection Setup
DB_HOST = "tcl-it-edw-redshift-prod-03.cktijfqqwie2.ap-south-1.redshift.amazonaws.com"
DB_PORT = "5439"
DB_NAME = "rsdev01"
DB_USER = "e1775050"
DB_PASSWORD = "RedShiftYas#2023"

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
user_query = st.text_input("What would you like to see? (e.g., 'Show a bar chart of sales by region')")

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
    
    # SYSTEM INSTRUCTIONS: Forcing Redshift SQL Generation and strict plotting rules
    prompt = f"""
    You are a data analysis expert. Your job is to output a Redshift SQL query AND the matplotlib plotting code to address the user's request.
    The data resides in an Amazon Redshift view named: `{TARGET_VIEW}`

    User Query: "{user_query}"
    
    STRICT BUSINESS DICTIONARY & REDSHIFT SQL TIME-PERIOD RULES:
    1. STRICT DEFAULT TIMELINE (MTD): If the user asks for "sales", "MTD sales", or specifies ANY other specific month (e.g., "sales for January", "sales for last month"), you MUST IGNORE the user's specified month and STRICTLY force the query to only include data for the current calendar month and year.
       - The current ongoing year is {current_year} and the current month is {current_month}.
       - Redshift SQL Filter Example to lock current month: `date_column >= DATE_TRUNC('month', CURRENT_DATE) AND date_column <= CURRENT_DATE`
       - Crucial: Never let the user's text override this current month filter requirement.
       
    2. YTD DEFINITION: Only apply if user explicitly asks for "YTD". From April 1st of the current financial year to today. 
       - SQL Filter Example: `date_column >= '{fiscal_year_start}' AND date_column <= '{today}'`
       
    3. QTD DEFINITION: Only apply if user explicitly asks for "QTD". From the start of the current financial quarter to today.
    
    4. REVENUE DEFAULT: Default strictly to grouping and summing the 'retail_revenue' column unless the user explicitly mentions "service revenue" in their query string.
    
    5. DATABASE AGGREGATION: The SQL statement MUST perform the `GROUP BY` and `SUM()` aggregation directly inside the database view. Do not pull unaggregated raw database rows.

    OUTPUT FORMAT REQUIREMENT:
    You must output your response in exactly two parts separated by a unique delimiter line: '---PLOT_CODE_START---'.
    
    Example Structure:
    SELECT region, SUM(retail_revenue) as total_revenue FROM {TARGET_VIEW} GROUP BY region
    ---PLOT_CODE_START---
    # Matplotlib python code here using a pre-existing dataframe named 'df'
    
    STRICT VISUALIZATION & EXACT MATH RULES (IN MATPLOTLIB CODE):
    - FIXED CURRENCY LABELLING MATH: For data labels above the bars, use this exact conditional logic loop in python over the series values:
      If value >= 10000000 -> label as `f"{{value / 10000000:.2f}} Cr"`
      If value >= 100000 and < 10000000 -> label as `f"{{value / 100000:.2f}} Lakh"`
      Otherwise -> label as `f"{{value:.2f}}"`
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
                
                # 2. Run the plotting module now that 'df' is successfully populated in memory
                with st.expander("See executed plotting code"):
                    st.code(plotting_code, language="python")
                    
                local_vars = {'df': df, 'plt': plt}
                exec(plotting_code, globals(), local_vars)
                
                # Verify file creation and update web page history timelines
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
    st.subheader("📜 Live Database Charts History Timeline")
    
    for i in range(len(st.session_state['chart_history']) - 1, -1, -1):
        img_path = st.session_state['chart_history'][i]
        q_text = st.session_state['query_history'][i]
        
        with st.container():
            st.markdown(f"**Query {i+1}:** *\"{q_text}\"*")
            if os.path.exists(img_path):
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