import streamlit as st
import pandas as pd
import openai
import requests
from bs4 import BeautifulSoup
import time
from openai import RateLimitError

# === CONFIG ===
openai.api_key = st.secrets["OPENAI_API_KEY"]
st.set_page_config(page_title="Pharma Brand Planner", layout="wide")

# === SAFE COMPLETION FUNCTION ===
def safe_openai_chat_completion(prompt, model="gpt-3.5-turbo", fallback_model=None):
    models_to_try = [model, fallback_model]
    for m in models_to_try:
        try:
            return openai.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6
            )
        except RateLimitError:
            time.sleep(2)
        except Exception:
            continue
    return None

# === LOAD EXCEL FILE ===
@st.cache_data
def load_data():
    xls = pd.ExcelFile("SI Tool.xlsx")
    tab1 = xls.parse("Tab 1")
    tab1.columns = tab1.columns.str.strip()
    tab2 = xls.parse("Tab 2")
    tab3 = xls.parse("Tab 3")
    tab4 = xls.parse("Tab 4")
    return tab1, tab2, tab3, tab4

tab1, tab2, tab3, tab4 = load_data()

# === STEP 1: Product Lifecycle ===
st.sidebar.title("Brand Planning Tool")
st.header("Step 1: Select Where You Are in the Product Lifecycle")
lifecycle_options = tab1.iloc[0, 1:6].dropna().tolist()
product_lifecycle = st.radio("Choose one:", lifecycle_options)

# === STEP 2: Strategic Imperatives ===
st.header("Step 2: Select Strategic Imperatives")
selected_col_idx = tab1.iloc[0].tolist().index(product_lifecycle)
strategic_rows = tab1.iloc[1:]
strategic_imperatives = strategic_rows[
    strategic_rows.iloc[:, selected_col_idx] == 'x'
]["Strategic Imperatives"].dropna().tolist()
selected_si = st.multiselect("Choose relevant imperatives:", strategic_imperatives)

# === STEP 3: Product Differentiators ===
st.header("Step 3: Select Product Differentiators")
categories = tab2.columns.tolist()
selected_category = st.selectbox("Choose a differentiator category:", categories)
options = tab2[selected_category].dropna().tolist()
selected_diff = st.multiselect("Select differentiators from this category:", options)

# === STEP 4: Brand Tone ===
st.header("Step 4: Select Optional Brand Tone")
brand_tones = tab3.iloc[:, 0].dropna().tolist()
selected_tone = st.multiselect("Choose brand tone(s):", brand_tones)

# === STEP 5: Strategic Objectives ===
st.header("Step 5: Select Strategic Objectives")
objectives = tab4.columns[1:].tolist()
selected_objectives = st.multiselect("Select your strategic objectives:", objectives)

# === STEP 6: Generate Tactics Plan ===
if st.button("Generate Tactics Plan"):
    st.subheader("Tactics Aligned to Your Strategic Imperatives")
    output_df = pd.DataFrame()

    for si in selected_si:
        matches = tab4[tab4["Strategic Challenge"] == si]
        if not matches.empty:
            for obj in selected_objectives:
                if obj in matches.columns:
                    tactics = matches[obj].dropna().tolist()
                    for tactic in tactics:
                        if pd.isna(tactic):
                            continue

                        prompt = f"You are a pharmaceutical marketing strategist. Write a short 3-4 sentence rationale describing why the following tactic: '{tactic}' aligns with the selected strategic imperative: '{si}', the differentiator(s): {', '.join(selected_diff)}, and the tone(s): {', '.join(selected_tone)}."
                        response = safe_openai_chat_completion(prompt)
                        desc = response.choices[0].message.content.strip() if response else "AI description unavailable."

                        estimate_prompt = f"Estimate the typical time and cost for executing this pharma marketing tactic: '{tactic}'. Provide a 1-line answer like 'Timeline: 6–8 weeks, Cost: $20,000–$35,000'."
                        est_response = safe_openai_chat_completion(estimate_prompt)
                        if est_response:
                            try:
                                estimate = est_response.choices[0].message.content.strip()
                                est_time, est_cost = estimate.split(", ")
                                est_time = est_time.replace("Timeline: ", "")
                                est_cost = est_cost.replace("Cost: ", "")
                            except Exception as e:
                                est_time = "TBD"
                                est_cost = f"Estimation failed: {e}"
                        else:
                            est_time = "Rate limited"
                            est_cost = "Try again later"

                        row_df = pd.DataFrame([{
                            "Strategic Imperative": si,
                            "Tactic": tactic,
                            "AI Description": desc,
                            "Est. Timing": est_time,
                            "Est. Cost": est_cost
                        }])
                        output_df = pd.concat([output_df, row_df], ignore_index=True)

    if output_df.empty:
        st.warning("No tactics were found based on your selected imperatives and objectives.")
    else:
        st.dataframe(output_df)

    st.subheader("5 Key Messaging Ideas")
    if not selected_si or not selected_diff or not selected_tone:
        st.warning("Please select strategic imperatives, differentiators, and tone.")
    else:
        msg_prompt = f"Based on the strategic imperatives: {', '.join(selected_si)}, product differentiators: {', '.join(selected_diff)}, and tone: {', '.join(selected_tone)}, generate 5 pharma marketing message ideas."
        msg_response = safe_openai_chat_completion(msg_prompt)
        if msg_response:
            st.markdown(msg_response.choices[0].message.content.strip())
        else:
            st.error("Message generation failed.")

    st.subheader("Campaign Concept")
    concept_prompt = f"Create a pharma campaign concept with a headline and subhead. The strategy should include: {', '.join(selected_si)}. Emphasize the differentiator(s): {', '.join(selected_diff)} and tone: {', '.join(selected_tone)}."
    concept_response = safe_openai_chat_completion(concept_prompt)
    if concept_response:
        st.markdown(concept_response.choices[0].message.content.strip())
    else:
        st.error("Campaign concept generation failed.")

    st.subheader("Competitive Intelligence")
    drug_name = st.text_input("Enter your drug name to generate competitive insights:")
    if st.button("Get Competitive Insights"):
        search_url = f"https://www.google.com/search?q={drug_name}+site:drugs.com"
        st.info(f"Searching online for competitors to {drug_name}...")
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(search_url, headers=headers)
            soup = BeautifulSoup(res.text, "html.parser")
            links = soup.find_all("a")
            count = 0
            for link in links:
                href = link.get("href")
                if href and "drugs.com" in href and "/compare/" in href:
                    name = href.split("compare/")[-1].replace("+vs+", " vs ")
                    st.write(f"**Competitor Comparison Found:** {name}")
                    count += 1
                    if count > 2:
                        break
            if count == 0:
                st.write("No direct competitors found.")
        except Exception as e:
            st.error(f"Error during competitor search: {e}")
