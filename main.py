import streamlit as st
import pandas as pd
from openai import OpenAI
import re
import os
import time
import datetime
import matplotlib.pyplot as plt

# 1. Initialize OpenAI Client with Titan Enterprise Gateway
API_KEY = st.secrets["TITAN_API_KEY"]
client = OpenAI(
    base_url="https://ai.titan.in/gateway",
    api_key=API_KEY
)

st.title("📊 Enterprise Excel Analytics Portal")
st.write("Running Analytics on Validated Excel Data Source.")

# Create the dedicated history folder if it doesn't exist
HISTORY_FOLDER = "chat_history"
if not os.path.exists(HISTORY_FOLDER):
    os.makedirs(HISTORY_FOLDER)

# Initialize session state lists to track query text and saved chart image paths
if 'chart_history' not in st.session_state:
    st.session_state['chart_history'] = []  
if 'query_history' not in st.session_state:
    st.session_state['query_history'] = []  

# --- LOAD EXCEL FILE ---
# Make sure your excel file name matches your actual file name uploaded to GitHub
EXCEL_FILE_NAME = "your_data_file.xlsx" 

@st.cache_data
def load_excel_data():
    return pd.read_excel(EXCEL_FILE_NAME)

try:
    df_raw = load_excel_data()
    st.success(f"Successfully loaded {len(df_raw)} rows from {EXCEL_FILE_NAME}")
except Exception as e:
    st.error(f"Could not load Excel file. Make sure '{EXCEL_FILE_NAME}' is uploaded to GitHub next to main.py. Error: {e}")
    st.stop()

# 2. User Input Query
user_query = st.text_input("What would you like to see? (e.g., 'Show a lollipop chart of sales by region' or 'table format')")

if user_query:
    # Get current date configurations to build precise dynamic filters
    today = datetime.date.today()
    current_year = today.year
    current_month = today.month
    
    # Identify the start of the standard Indian Fiscal Year (April 1st)
    fiscal_year_start = f"{current_year}-04-01" if current_month >= 4 else f"{current_year-1}-04-01"
    
    # Generate a unique chart file path
    timestamp = int(time.time())
    current_chart_filename = os.path.join(HISTORY_FOLDER, f"chart_{timestamp}.png").replace("\\", "/")
    
    # SYSTEM INSTRUCTIONS: Forcing Pandas Manipulation over df_raw and strict layout rules
    prompt = f"""
    You are an expert data analyst. Your job is to output a Python Pandas aggregation snippet AND the matplotlib plotting code to address the user's request.
    The raw data resides in a pre-loaded pandas DataFrame named: `df_raw`
    The DataFrame contains columns representing transactional data like 'region', 'retail_revenue', 'service_revenue', and a date column named 'date_column'.

    User Query: "{user_query}"
    
    STRICT BUSINESS DICTIONARY & TIME-PERIOD RULES:
    1. DEFAULT TIMELINE (MTD): If the user asks for "sales", "MTD sales", or specifies ANY specific month (e.g., "sales for May", "sales for January"), you MUST check if the user is asking for a specific month.
       - If they ask for a specific month (like "May"), filter `df_raw['date_column']` for that specific month.
       - If they do NOT specify a month (e.g., just "sales"), strictly DEFAULT to the current calendar month and year (Current Year: {current_year}, Current Month: {current_month}).
    2. REVENUE SELECTION: Default strictly to grouping and summing the 'retail_revenue' column. However, if the user explicitly types "service revenue", you MUST calculate using the 'service_revenue' column instead.
    3. PANDAS AGGREGATION: You must write code that aggregates the raw rows into a summary dataframe named `df`. 
       Example: `df = df_raw[filters].groupby('region')['retail_revenue'].sum().reset_index()`

    OUTPUT FORMAT REQUIREMENT:
    You must output your response in exactly two parts separated by a unique delimiter line: '---PLOT_CODE_START---'.
    
    Example Structure:
    df = df_raw.groupby('region')['retail_revenue'].sum().reset_index()
    ---PLOT_CODE_START---
    # Matplotlib python code here using the newly created dataframe named 'df'
    
    CRITICAL TABLE VS CHART LOGIC:
    - If the user explicitly asks for the output in a "table format", "table", or "grid", your Python plotting code should NOT create a matplotlib chart. Instead, simply write a comment `# TABLE REQUESTED`.
    - Otherwise, default to writing Matplotlib plotting code using the aggregated dataframe named 'df'.

    SUPPORT FOR ANY PICTORIAL REPRESENTATION CHART STYLES:
    You must dynamically write the code for whatever specific visualization style the user explicitly requests:
    - LOLLIPOP CHART: Use `plt.vlines(x=df[x_col], ymin=0, ymax=df[y_col])` combined with `plt.scatter(df[x_col], df[y_col])`
    - DONUT CHART: Use `plt.pie(..., wedgeprops=dict(width=0.4, edgecolor='w'))`.
    - BAR CHART / HORIZONTAL BAR CHART: Use `ax.bar()` or `ax.barh()`.

    STRICT VISUALIZATION & CRITICAL LABELLING CODE RULES (FOR CHARTS):
    - NO INDEPENDENT FUNCTIONS ALLOWED: Do NOT call or invent a function called `format_currency()` or `currency_format()`. You must write out the conditional loop logic explicitly inline.
    - INLINE CURRENCY MATH LOGIC: For drawing text data labels directly on the chart, use this loop inline:
      ```python
      for bar in bars:
          yval = bar.get_height()
          if yval >= 10000000:
              lbl = f"{{yval / 10000000:.2f}} Cr"
          elif yval >= 100000:
              lbl = f"{{yval / 100000:.2f}} Lakh"
          else:
              lbl = f"{{yval:.2f}}"
          plt.text(bar.get_x() + bar.get_width()/2, yval, lbl, ha='center', va='bottom')
      ```
    
    - READABILITY & SPACING: 
      1. Always call `plt.tight_layout()` right before saving to prevent labels or legends from getting cut off.
      2. For vertical graphs (like bar or lollipop), increase the top margin of the Y-axis by 15% using `ax.set_ylim(0, max_val * 1.15)` so data labels are never cramped or cut off at the ceiling.
    
    - Clear the figure at the start using `plt.figure()`.
    - Save the plot using: `plt.savefig("{current_chart_filename}", bbox_inches="tight")`.

    Return ONLY raw python code inside your block structure. Do not include any standard conversational text explanations.
    """
    
    with st.spinner("Processing Excel Query & Chart Generation..."):
        try:
            # Generate response from Titan Enterprise Gateway
            response = client.chat.completions.create(
                model="gemini-3.1-flash-lite",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            raw_text = response.choices[0].message.content
            
            # Clean up markdown block wrappers if returned
            raw_text = raw_text.replace("```python", "").replace("```", "").strip()
            
            if "---PLOT_CODE_START---" in raw_text:
                pandas_logic, plotting_code = raw_text.split("---PLOT_CODE_START---")
                pandas_logic = pandas_logic.strip()
                plotting_code = plotting_code.strip()
                
                with st.expander("See generated Data Filtering & Aggregation Logic"):
                    st.code(pandas_logic, language="python")
                
                # 1. Execute the pandas data processing logic to create 'df'
                local_vars = {'df_raw': df_raw, 'pd': pd}
                exec(pandas_logic, globals(), local_vars)
                df = local_vars.get('df')
                
                # 2. Check if the user wanted a Table vs a Chart
                if "table" in user_query.lower() or "grid" in user_query.lower():
                    st.subheader("📋 Requested Data Table")
                    st.dataframe(df, use_container_width=True)
                    
                    st.session_state['chart_history'].append("TABLE_OUTPUT")
                    st.session_state['query_history'].append(user_query)
                else:
                    with st.expander("See executed plotting code"):
                        st.code(plotting_code, language="python")
                    
                    # 3. Clear open figures and run plotting logic
                    plt.close('all')
                    plot_vars = {'df': df, 'plt': plt}
                    exec(plotting_code, globals(), plot_vars)
                    
                    if os.path.exists(current_chart_filename):
                        st.session_state['chart_history'].append(current_chart_filename)
                        st.session_state['query_history'].append(user_query)
                
            else:
                st.error("Formatting structure issue. Please re-type your request.")
                st.write(raw_text)
                
        except Exception as e:
            st.error(f"An error occurred during query execution: {e}")

# --- DISPLAY HISTORICAL TIMELINE ---
if st.session_state['chart_history']:
    st.write("---")
    st.subheader("📜 Live Analytics History")
    
    for i in range(len(st.session_state['chart_history']) - 1, -1, -1):
        img_path = st.session_state['chart_history'][i]
        q_text = st.session_state['query_history'][i]
        
        with st.container():
            st.markdown(f"**Query {i+1}:** *\"{q_text}\"*")
            if img_path == "TABLE_OUTPUT":
                st.info("📊 This query was rendered above as a clean data table view.")
            elif os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            st.write("") 

# --- CLEAR ACTION BUTTON ---
if st.button("Clear Chat & History"):
    for img_file in st.session_state['chart_history']:
        if img_file != "TABLE_OUTPUT" and os.path.exists(img_file):
            try:
                os.remove(img_file)
            except:
                pass
                
    st.session_state['chart_history'] = []
    st.session_state['query_history'] = []
    plt.close('all')
    st.success("App history cleared!")
    st.rerun()
