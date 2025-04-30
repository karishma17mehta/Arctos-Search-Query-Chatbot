#!/usr/bin/env python
# coding: utf-8

# In[48]:




# In[21]:


# 🧪 Arctos Specimen Chatbot - Jupyter Notebook Version
# This notebook mirrors the Streamlit app, but allows you to run the chatbot inside Jupyter!

# Import libraries
import os
import openai
import json
import requests
from dotenv import load_dotenv
from urllib.parse import urlencode


# In[22]:


# Load environment variables
load_dotenv()

import streamlit as st

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
ARCTOS_API_KEY = st.secrets["ARCTOS_API_KEY"]
ARCTOS_API_BASE_URL = "https://arctos.database.museum/component/api/v2/catalog.cfc"


# In[23]:


# Define field mapping
FIELD_TO_ARCTOS_PARAM = {
    "taxonomy": "taxon_name",
    "taxon": "taxon_name",
    "location": "spec_locality",
    "any_geog": "any_geog",
    "country": "country",
    "state": "state_prov",
    "state_province": "state_prov",
    "part": "part_search",
    "part search": "part_search",
    "collector": "collector",
    "media type": "media_type",
    "type status": "type_status",
    "date": "verbatim_date",
    "year": "verbatim_date",
    "has tissue": "is_tissue",
    "scientific_name_match": "scientific_name_match_type",
    "agent role": "coll_role",
    "guid_prefix": "guid_prefix",
}


# In[24]:


# Extract fields function
def extract_query_fields(user_input):
    prompt = f"""
    Extract the taxonomy, location, country, state, collector, preparation type, sex, lifestage, year, interaction type (if any), part (if any), media type (if any), and type status (if any) from this user query: '{user_input}'.
    Return as a JSON dictionary using only these keys if mentioned in the query: 'taxon_name', 'verbatim_date', 'part', 'media_type', 'type_status', 'has tissue', 'collector', 'country', 'state', 'location'.
    Do not include fields like 'preparation_type'.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    extracted = response.choices[0].message.content
    return json.loads(extracted)


# In[25]:


# Query Arctos function
def query_arctos(fields):
    params = {
        "method": "getCatalogData",
        "queryformat": "struct",
        "api_key": ARCTOS_API_KEY
    }

    for user_field, arctos_field in FIELD_TO_ARCTOS_PARAM.items():
        if user_field in fields:
            value = fields[user_field]
            if value not in ["N/A", "not specified", "", None]:
                params[arctos_field] = value

    response = requests.get(ARCTOS_API_BASE_URL, params=params)
    response.raise_for_status()
    return response.json()


# In[26]:


# Format results function
def format_results(results):
    data_records = results.get('DATA', [])
    if not data_records:
        return "No results found."

    formatted = []
    for record in data_records:
        species = record.get('scientific_name', 'Unknown species')
        locality = record.get('spec_locality') or record.get('state_prov') or record.get('country') or "Unknown location"
        date = record.get('verbatim_date', 'Unknown date')
        entry = f"{species} collected from {locality} on {date}."
        formatted.append(entry)

    return "\n\n".join(formatted)


# In[57]:


# Generate Arctos search URL function
from urllib.parse import urlencode
import inflect

p = inflect.engine()

US_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri",
    "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia",
    "Washington", "West Virginia", "Wisconsin", "Wyoming"
}

def generate_arctos_search_url(fields):
    base_url = "https://arctos.database.museum/search.cfm"
    params = {}

    # Explicitly handle taxon_name field first
    if "taxon_name" in fields and fields["taxon_name"] not in ["N/A", "not specified", "", None]:
        taxon = fields["taxon_name"]
        if isinstance(taxon, str):
            taxon = taxon.strip()
            if " " in taxon:
                params["scientific_name"] = taxon
            else:
                singular = p.singular_noun(taxon)
                params["taxon_name"] = singular if singular else taxon

    # Continue with rest of parameters
    for user_field, arctos_field in FIELD_TO_ARCTOS_PARAM.items():
        if user_field == "taxon_name":
            continue  # already handled above

        if user_field in fields and fields[user_field] not in ["N/A", "not specified", "", None]:
            value = fields[user_field]
            if isinstance(value, str):
                value = value.strip()

            # Handle tissue flag
            if user_field == "has tissue":
                if (isinstance(value, str) and value.lower() in ["yes", "true", "1"]) or value is True:
                    params["is_tissue"] = 1
                    params["sp"] = "Tissue"
                    continue

            # Skip US states from being added as spec_locality
            if arctos_field == "spec_locality" and value in US_STATES:
                continue

            params[arctos_field] = value

    query_string = urlencode(params)
    return f"{base_url}?{query_string}"


# In[28]:

# In[53]:


import streamlit as st


# In[59]:


# Streamlit app
# Streamlit app
import streamlit as st
from streamlit.components.v1 import html
from PIL import Image

# Load and display logo
logo = Image.open("/Users/karishmamehta/Documents/Practicum_Project/Arctos_logo.png")
st.image(logo, width=140)

st.markdown("<h1 style='color:white;'>🔎 Arctos Query Search Chatbot</h1>", unsafe_allow_html=True)

# Description
st.markdown("""
<div style='text-align: left; font-size: 16px; line-height: 1.6; color: #ddd;'>
This tool helps researchers search the Arctos database using natural language queries.<br>
Enter phrases like <em>'Find shrews collected in New York in 1999'</em>
or <em>'Search for Canis latrans in Alaska in 2001'</em>.<br>
The chatbot will extract parameters, generate a URL, and retrieve matching records from the Arctos Search Database.
</div>
""", unsafe_allow_html=True)


# Search input
user_query = st.text_input("🗣️ Enter your specimen search query:", placeholder="e.g. Search birds in Alaska")

# Create side-by-side button columns, wider spacing
search_col, clear_col = st.columns([1, 1])

# Handle actions
search_clicked = search_col.button("🔍 Search")
clear_clicked = clear_col.button("❌ Clear")

if search_clicked:
    if user_query:
        with st.spinner("Processing query..."):
            try:
                fields = extract_query_fields(user_query)
                st.subheader("🧾 Extracted Fields")
                st.json(fields)

                search_url = generate_arctos_search_url(fields)
                st.markdown(f"🔗 [**Open Arctos Search URL**]({search_url})")

                results = query_arctos(fields)
                formatted = format_results(results)

                st.subheader("📋 Search Results")
                st.text(formatted)
            except Exception as e:
                st.error(f"Error: {e}")
elif clear_clicked:
    st.experimental_rerun()
