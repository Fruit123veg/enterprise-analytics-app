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

st.set_page_config(page_title="Enterprise Excel Analytics Portal", layout="wide")
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
EXCEL_FILE_NAME = "Dummy Data.xlsx" 

@st.cache_data
def load_excel_data():
    return pd.read_excel(EXCEL_FILE_NAME)

try:
    df_raw = load_excel_data()
    st.success(f"Successfully loaded {len(df_raw)} rows from {EXCEL_FILE_NAME}")
except Exception as e:
    st.error(f"Could not load Excel file. Make sure '{EXCEL_FILE_NAME}' is uploaded next to main.py. Error: {e}")
    st.stop()

# --- ADD INTERACTIVE MODE TOGGLE ---
explain_mode = st.toggle("💡 Turn ON for Data Explanation / Turn OFF for Visual Chart", value=False)

# 2. User Input Query
user_query = st.text_input("What would you like to see? (e.g., 'Show a bar chart of sales by region' or 'table format')")

if user_query:
    today = datetime.date.today()
    current_year = today.year
    current_month = today.month
    
    timestamp = int(time.time())
    current_chart_filename = os.path.join(HISTORY_FOLDER, f"chart_{timestamp}.png").replace("\\", "/")
    
    # SYSTEM INSTRUCTIONS: Explicit handling of runtime aggregation and dynamic insight generation
    prompt = f"""
    You are an expert data analyst. Your job is to output a Python Pandas aggregation snippet AND a secondary response to address the user's request.
    The raw data resides in a pre-loaded pandas DataFrame named: `df_raw`
    The DataFrame contains columns representing transactional data like 'region', 'retail_revenue', 'service_revenue', and a date column named 'date'.

    User Query: "{user_query}"
    Current Target Mode: {"TEXT_EXPLANATION" if explain_mode else "PICTORIAL_CHART"}
    
    STRICT BUSINESS DICTIONARY & TIME-PERIOD RULES:
    1. DEFAULT TIMELINE (MTD): If the user asks for "sales", "MTD sales", or specifies ANY specific month (e.g., "sales for May"), check if they ask for a specific month.
       - If they ask for a specific month (like "May"), filter `df_raw['date']` for that specific month.
       - If they do NOT specify a month, strictly DEFAULT to the current calendar month and year (Current Year: {current_year}, Current Month: {current_month}).
    2. REVENUE SELECTION: Default strictly to grouping and summing the 'retail_revenue' column. If the user explicitly types "service revenue", calculate using 'service_revenue' instead.
    3. PANDAS AGGREGATION: You must write code that aggregates the raw rows into a summary dataframe named `df`. 
       CRITICAL CRITERIA: Your pandas snippet MUST explicitly assign its final result to a variable named 'df'. You MUST start the line with 'df = '. Do not just write a dangling statement.
       Example: `df = df_raw[filters].groupby('region')['retail_revenue'].sum().reset_index()`

    OUTPUT FORMAT REQUIREMENT:
    You must output your response in exactly two parts separated by a unique delimiter line: '---PLOT_CODE_START---'.
    
    CRITICAL TOGGLE LOGIC:
    - IF CURRENT TARGET MODE IS "TEXT_EXPLANATION": Everything after '---PLOT_CODE_START---' must be raw Python code that dynamically generates a string variable named `insight_text`. 
      You must programmatically inspect `df` to extract precise, hard facts (e.g., finding the exact highest/lowest metrics and regions dynamically using idxmax() or max()) and format them into an explanatory narrative paragraph. Do NOT write static text. Do NOT write plotting code.
      Example structure:
      ```python
      max_val = df.iloc[:, 1].max()
      max_region = df.iloc[df.iloc[:, 1].idxmax()][df.columns[0]]
      insight_text = f"The absolute highest performing region is {{max_region}} with an exact metric value of {{max_val:,.2f}}..."
      ```

    - IF CURRENT TARGET MODE IS "PICTORIAL_CHART": Everything after '---PLOT_CODE_START---' must be raw Matplotlib plotting code using the aggregated dataframe named 'df'.
    
    CRITICAL TABLE VS CHART LOGIC:
    - If the user explicitly asks for the output in a "table format", "table", or "grid", simply write a comment `# TABLE REQUESTED` instead of plotting.

    STRICT VISUALIZATION LABELLING CODE RULES (FOR CHARTS):
    - NO INDEPENDENT FUNCTIONS ALLOWED: Do NOT call a function called `format_currency()`. Write out the conditional loop logic explicitly inline.
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
    - READABILITY & SPACING: Call `plt.tight_layout()` right before saving. Increase the top margin of the Y-axis by 15% using `ax.set_ylim(0, max_val * 1.15)`.
    - Clear the figure at the start using `plt.figure()`.
    - Save the plot using: `plt.savefig("{current_chart_filename}", bbox_inches="tight")`.

    Do not include standard markdown code blocks wrappers like ```python. Start directly with the raw pandas statement.
    """
    
    with st.spinner("Processing Data Pipeline Execution..."):
        try:
            response = client.chat.completions.create(
                model="gemini-3.1-flash-lite",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            raw_text = response.choices[0].message.content
            raw_text = raw_text.replace("```python", "").replace("```", "").strip()
            
            if "---PLOT_CODE_START---" in raw_text:
                pandas_logic, execution_content = raw_text.split("---PLOT_CODE_START---")
                pandas_logic = pandas_logic.strip()
                execution_content = execution_content.strip()
                
                with st.expander("See generated Data Filtering & Aggregation Logic"):
                    st.code(pandas_logic, language="python")
                
                # 1. Execute pandas logic within a unified scope block to preserve variable states safely
                exec_context = {'df_raw': df_raw, 'pd': pd, 'df': None}
                exec(pandas_logic, exec_context, exec_context)
                df = exec_context.get('df')
                
                if df is None or not isinstance(df, pd.DataFrame):
                    st.error("Data tracking pipeline execution failed to generate a structured Summary DataFrame.")
                    st.stop()
                
                # 2. Check if the user specifically forced a data grid view
                if "table" in user_query.lower() or "grid" in user_query.lower():
                    st.subheader("📋 Requested Data Table")
                    st.dataframe(df, use_container_width=True)
                    st.session_state['chart_history'].append("TABLE_OUTPUT")
                    st.session_state['query_history'].append(user_query)
                
                # 3. Handle Mode Toggle: Dynamic Explanation text script vs. Chart rendering
                elif explain_mode:
                    st.subheader("💡 AI Data Insight & Explanation")
                    
                    # Run the logic that programmatically structures textual findings from data rows
                    text_context = {'df': df, 'pd': pd, 'insight_text': ""}
                    exec(execution_content, text_context, text_context)
                    generated_insight = text_context.get('insight_text', "Analysis executed successfully, but no narrative statement variable was generated.")
                    
                    st.info(generated_insight)
                    
                    # Store textual explanation marker inside timeline history
                    st.session_state['chart_history'].append(f"TEXT_EXPLAIN: {generated_insight}")
                    st.session_state['query_history'].append(user_query)
                else:
                    with st.expander("See executed plotting code"):
                        st.code(execution_content, language="python")
                    
                    # Clear canvas and compile dynamic graph metrics
                    plt.close('all')
                    plot_context = {'df': df, 'plt': plt, 'pd': pd}
                    exec(execution_content, plot_context, plot_context)
                    
                    if os.path.exists(current_chart_filename):
                        st.session_state['chart_history'].append(current_chart_filename)
                        st.session_state['query_history'].append(user_query)
                    else:
                        st.error("Plot script finished execution, but no physical visualization image was caught.")
                
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
            elif img_path.startswith("TEXT_EXPLAIN:"):
                text_insight = img_path.replace("TEXT_EXPLAIN:", "").strip()
                st.info(f"💡 **Data Insight:** {text_insight}")
            elif os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            st.write("") 

# --- CLEAR ACTION BUTTON ---
if st.button("Clear Chat & History"):
    for img_file in st.session_state['chart_history']:
        if not img_file.startswith("TEXT_EXPLAIN:") and img_file != "TABLE_OUTPUT" and os.path.exists(img_file):
            try:
                os.remove(img_file)
            except:
                pass
                
    st.session_state['chart_history'] = []
    st.session_state['query_history'] = []
    plt.close('all')
    st.success("App history cleared!")
    st.rerun()
