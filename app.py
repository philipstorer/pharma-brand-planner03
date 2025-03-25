import streamlit as st
import pandas as pd
import numpy as np
import os
import openai

# Set your OpenAI API key (for production, load from an environment variable instead)
openai.api_key = "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"

# -------------------------------
# Utility functions and caching
# -------------------------------

@st.cache_data
def load_data(excel_path):
    """
    Load all sheets from the Excel file.
    Adjust sheet names or indices as needed.
    """
    # We assume the file is named "pharma_brand_planner.xlsx"
    df_sheet1 = pd.read_excel(excel_path, sheet_name=0, header=None)  # Lifecycle & Strategic Imperatives
    df_sheet2 = pd.read_excel(excel_path, sheet_name=1)  # Differentiators (assumes header row exists)
    df_sheet3 = pd.read_excel(excel_path, sheet_name=2, header=None)  # Brand Tone list (no header)
    df_sheet4 = pd.read_excel(excel_path, sheet_name=3, header=None)  # Objectives & Tactics

    return df_sheet1, df_sheet2, df_sheet3, df_sheet4

def get_product_lifecycle_options(df_sheet1):
    """
    Extract the product lifecycle stages from cells B2-F2.
    (Row index 1, columns 1 to 5, 0-indexed)
    """
    lifecycle_row = df_sheet1.iloc[1, 1:6]
    lifecycles = lifecycle_row.dropna().tolist()
    return lifecycles

def get_strategic_imperatives(df_sheet1, lifecycle_index):
    """
    From Sheet 1 (Lifecycle_SI), return a list of strategic imperatives 
    that have an "X" in the column corresponding to the selected lifecycle stage.
    Also return the row indices (offset relative to the tactics matrix later)
    to later map to tactics.
    """
    si_df = df_sheet1.iloc[2:, :]  # rows starting from Excel row3 (0-indexed)
    si_options = []
    si_row_indices = []
    col_index = lifecycle_index + 1  # since lifecycle stages start at col B (index 1)

    for idx, row in si_df.iterrows():
        if str(row.iloc[col_index]).strip().upper() == "X":
            si_options.append(row.iloc[0])  # SI name from column A
            si_row_indices.append(idx)
    return si_options, si_row_indices

def get_differentiator_categories(df_sheet2):
    """
    The differentiator categories are assumed to be the column headers.
    """
    return list(df_sheet2.columns)

def get_differentiators_for_category(df_sheet2, category):
    """
    Return non-null differentiator options for the given category.
    """
    differentiators = df_sheet2[category].dropna().tolist()
    return differentiators

def get_brand_tone_options(df_sheet3):
    """
    Return a list of brand tone options from Sheet3.
    We assume the tones are in the first column.
    """
    tones = df_sheet3.iloc[:, 0].dropna().tolist()
    return tones

def get_objectives(df_sheet4):
    """
    In Sheet4, cells B1-F1 (row 0, columns 1 to 5) are the objective options.
    """
    objective_row = df_sheet4.iloc[0, 1:6]
    objectives = objective_row.dropna().tolist()
    return objectives

def get_tactics_for_lifecycle_and_si(df_sheet4, lifecycle_index, si_row_indices):
    """
    From Sheet4, we assume:
    - Row 0 is the header with objectives (cells B1-F1)
    - Tactics are in rows 1 to end in columns B-F.
    We map each strategic imperative (from Sheet1) to a corresponding row in Sheet4 
    (offset by 1, as Sheet4’s first row is the header).
    """
    tactics_list = []
    col_index = lifecycle_index + 1  # since column B is index 1
    for si_idx in si_row_indices:
        tactic_row = si_idx - 1  # mapping: SI row in Sheet1 to tactic row in Sheet4
        if tactic_row < 1 or tactic_row >= len(df_sheet4):
            continue
        tactic = df_sheet4.iloc[tactic_row, col_index]
        if pd.notna(tactic) and str(tactic).strip() != "":
            tactics_list.append(tactic)
    return tactics_list

# -------------------------------
# OpenAI API helper function
# -------------------------------

def ai_generate(prompt, max_tokens=300, temperature=0.7):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful marketing strategist."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error generating response: {e}"

# -------------------------------
# AI Generation Functions (using OpenAI)
# -------------------------------

def generate_ai_description(tactic, differentiators, brand_tone, objective):
    diff_text = ", ".join(differentiators) if differentiators else "no differentiators provided"
    tone_text = brand_tone if brand_tone else "a default"
    prompt = (
        f"Generate a 3-4 sentence description for the tactic: '{tactic}'. "
        f"Explain how it aligns with the objective '{objective}', leverages the differentiators: {diff_text}, "
        f"and reflects {tone_text} brand tone."
    )
    return ai_generate(prompt)

def generate_ai_estimate(tactic):
    prompt = (
        f"Provide an industry-standard budget estimate and high-level timing for executing the tactic: '{tactic}'. "
        "Include a budget range (e.g., $50K - $100K) and expected duration in months."
    )
    return ai_generate(prompt, max_tokens=150)

def generate_ai_key_messaging(differentiators, brand_tone, objective, si_list):
    diff_text = ", ".join(differentiators) if differentiators else "no differentiators provided"
    tone_text = brand_tone if brand_tone else "a default"
    si_text = ", ".join(si_list) if si_list else "no strategic imperatives provided"
    prompt = (
        f"Based on the differentiators ({diff_text}), brand tone ({tone_text}), objective ({objective}), "
        f"and strategic imperatives ({si_text}), generate 5 key messaging ideas for a pharmaceutical brand campaign. "
        "List each idea on a new line."
    )
    response = ai_generate(prompt)
    # Split the response into separate lines for each messaging idea.
    return [line.strip() for line in response.split("\n") if line.strip()]

def generate_ai_campaign_concept(differentiators, brand_tone, objective, si_list):
    diff_text = ", ".join(differentiators) if differentiators else "no differentiators provided"
    tone_text = brand_tone if brand_tone else "a default"
    si_text = ", ".join(si_list) if si_list else "no strategic imperatives provided"
    prompt = (
        f"Based on the differentiators ({diff_text}), brand tone ({tone_text}), objective ({objective}), "
        f"and strategic imperatives ({si_text}), generate a campaign concept for a pharma brand. "
        "Provide a headline on the first line and a subheadline on the second line."
    )
    response = ai_generate(prompt)
    lines = [line.strip() for line in response.split("\n") if line.strip()]
    if len(lines) >= 2:
        return lines[0], lines[1]
    else:
        return response, ""

def generate_ai_competitive_insights(drug_name):
    prompt = (
        f"Provide competitive insights for the drug '{drug_name}'. List at least three competitors, "
        "including for each competitor a key website headline, subheadline, and a short assumption about their brand positioning. "
        "Return the results in a clear and concise format."
    )
    return ai_generate(prompt, max_tokens=400)

# -------------------------------
# Streamlit App Layout
# -------------------------------

st.title("Pharma Brand Planner Tool")
st.write("Create a custom brand plan leveraging AI-enhanced recommendations.")

# Path to the Excel file – ensure this file is in your repo/folder.
EXCEL_FILE = "pharma_brand_planner.xlsx"
if not os.path.exists(EXCEL_FILE):
    st.error(f"Excel file '{EXCEL_FILE}' not found. Please ensure it is in the working directory.")
    st.stop()

# Load data from Excel
df_sheet1, df_sheet2, df_sheet3, df_sheet4 = load_data(EXCEL_FILE)

st.header("Step 1: Select Product Lifecycle Stage")
lifecycles = get_product_lifecycle_options(df_sheet1)
selected_lifecycle = st.radio("Choose your product lifecycle stage:", lifecycles)

# Determine the index of the selected lifecycle stage.
lifecycle_index = lifecycles.index(selected_lifecycle)

st.header("Step 2: Select Strategic Imperatives")
si_options, si_row_indices = get_strategic_imperatives(df_sheet1, lifecycle_index)
if not si_options:
    st.warning("No strategic imperatives found for this lifecycle stage. Please check your Excel file data.")
selected_si = st.multiselect("Select one or more Strategic Imperatives:", si_options)

# Filter the row indices based on the selected SI
selected_si_indices = [si_row_indices[si_options.index(si)] for si in selected_si]

st.header("Step 3: Select Product Differentiators")
diff_categories = get_differentiator_categories(df_sheet2)
selected_diff_category = st.selectbox("Select a Differentiator Category:", diff_categories)
differentiators = get_differentiators_for_category(df_sheet2, selected_diff_category)
selected_differentiators = st.multiselect("Select one or more Differentiators:", differentiators)

st.header("Step 4 (Optional): Select Brand Tone")
brand_tones = get_brand_tone_options(df_sheet3)
selected_brand_tone = st.selectbox("Select a Brand Tone:", [""] + brand_tones)

st.header("Step 5: Select Your Objective")
objectives = get_objectives(df_sheet4)
selected_objective = st.radio("Choose your objective:", objectives)

st.markdown("---")
st.header("Step 6: Generate Tactics & Creative Recommendations")

if st.button("Generate Brand Plan"):
    # Get tactics based on selected lifecycle and strategic imperative rows.
    tactics = get_tactics_for_lifecycle_and_si(df_sheet4, lifecycle_index, selected_si_indices)
    
    if not tactics:
        st.error("No tactics were found based on your selections. Please review your inputs and Excel data.")
    else:
        st.subheader("Tactical Recommendations")
        for tactic in tactics:
            description = generate_ai_description(
                tactic,
                selected_differentiators,
                selected_brand_tone,
                selected_objective
            )
            estimate = generate_ai_estimate(tactic)
            st.markdown(f"**Tactic:** {tactic}")
            st.markdown(f"**Description:** {description}")
            st.markdown(f"**Estimate & Timing:** {estimate}")
            st.markdown("---")
        
        st.subheader("Key Messaging & Campaign Concept")
        messaging_ideas = generate_ai_key_messaging(
            selected_differentiators,
            selected_brand_tone,
            selected_objective,
            selected_si
        )
        for idea in messaging_ideas:
            st.markdown(f"- {idea}")
        
        headline, subhead = generate_ai_campaign_concept(
            selected_differentiators,
            selected_brand_tone,
            selected_objective,
            selected_si
        )
        st.markdown("**Campaign Concept**")
        st.markdown(f"**Headline:** {headline}")
        st.markdown(f"**Subhead:** {subhead}")

st.markdown("---")
st.header("Step 7: Generate Competitive Insights")
drug_name_input = st.text_input("Enter Drug Name:")
if st.button("Generate Competitive Insights"):
    if drug_name_input.strip() == "":
        st.warning("Please enter a drug name to generate competitive insights.")
    else:
        insights = generate_ai_competitive_insights(drug_name_input)
        st.subheader("Competitive Insights")
        st.markdown(insights)
