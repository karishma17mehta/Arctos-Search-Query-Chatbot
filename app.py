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


# In[5]:


# Define field mapping
FIELD_TO_ARCTOS_PARAM = {
    "taxonomy": "scientific_name",
    "taxon": "scientific_name",
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
    "institution": "guid_prefix",
}


# In[19]:


# Define extract query function
def extract_query_fields(user_input):
    prompt = f"""
    Extract the taxonomy, location, country, state, collector, year (verbatim_date), institution name (if any), interaction type (if any),
    part (if any), media type (if any), and type status (if any) from this user query: '{user_input}'.

    Return the result as a JSON dictionary using only these keys if mentioned:
    'taxon_name', 'verbatim_date', 'part', 'media_type', 'type_status', 
    'has tissue', 'collector', 'country', 'state', 'location', 'institution'.

    Additional instructions:
    - Recognize known institutions (like "Abilene Christian University") and assign them to the 'institution' key.
    - Recognize phrases like "Museum of Natural History" or university collection names as institutions.
    - If a query includes both a location and an institution, ensure the institution is NOT assigned to 'location'.
    - When a query mentions both an organism and a museum/university/center/natural history/academy/wildlife refuge/laboratory/commission/college/institute/, assign it to the 'institution' field, not 'location' or 'spec_locality'.
    - Do NOT assign institutions to 'collector', 'verbatim_date', or 'location'.
    - Use 'location' only for geographic localities, lakes, cities, landmarks, etc.
    - Only use 'collector' for human names.
    - Output should be valid JSON only.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    extracted = response.choices[0].message.content
    return json.loads(extracted)


# In[21]:


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


# In[23]:


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


# In[61]:


import pandas as pd

# Load institution-to-guid_prefix mapping
portal_df = pd.read_csv("_portals.csv")  # Adjust path if needed

# Normalize institution names and group guid_prefixes
institution_to_prefix = {}
for _, row in portal_df.iterrows():
    name = row["INSTITUTION"].lower().strip()
    prefix = row["GUID_PREFIX"].strip()
    if name in institution_to_prefix:
        institution_to_prefix[name].append(prefix)
    else:
        institution_to_prefix[name] = [prefix]


# In[69]:


TAXON_CATEGORY_MAP = {
    "reptiles and amphibians": "herp",
    "amphibians": "herp",
    "reptiles": "herp",
    "herpetofauna": "herp",
    "herp": "herp",
    "birds": "bird",
    "aves": "bird",
    "avian": "bird",
    "bird": "bird",
    "mammals": "mamm",
    "mammal": "mamm",
    "mammalia": "mamm",
    "fishes": "fish",
    "fish": "fish",
    "pisces": "fish",
    "insects": "ento",
    "insect": "ento",
    "entomology": "ento",
    "bugs": "ento",
    "ento": "ento",
    "invertebrates": "inv",
    "invertebrate": "inv",
    "inv": "inv",
    "parasites": "para",
    "parasite": "para",
    "para": "para",
    "arthropods": "arth",
    "arthropod": "arth",
    "arth": "arth",
    "plants": "plant",
    "plant": "plant",
    "flora": "plant",
    "fungi": "fung",
    "fungus": "fung",
    "mycology": "fung",
    "paleontology": "paleo",
    "fossils": "paleo",
    "paleo": "paleo",
    "eggs": "egg",
    "egg": "egg",
    "tissues": "tissue",
    "tissue": "tissue",
    "dna": "dna",
    "genetic material": "dna",
    "genetics": "gen",
    "genes": "gen",
    "genetic": "gen",
    "algae": "algae",
    "botany": "bot",
    "botanical": "bot",
    "bot": "bot"
}


# In[71]:


# Generate Arctos search URL function
import inflect
p = inflect.engine()

# Make sure TAXON_CATEGORY_MAP is defined globally before this function
def generate_arctos_search_url(fields):
    base_url = "https://arctos.database.museum/search.cfm"
    params = {}

    # Handle institution → guid_prefix mapping
    if "institution" in fields:
        inst = fields["institution"].lower().strip()

        # Standardize taxon
        taxon = fields.get("taxon_name", "")
        taxon = taxon.lower().strip() if isinstance(taxon, str) else ""

        # Try direct mapping using your category map
        taxon_mapped = TAXON_CATEGORY_MAP.get(taxon, "")
        if taxon_mapped:
            taxon = taxon_mapped
        else:
            taxon = p.singular_noun(taxon) or taxon

        matched_prefixes = []
        if inst in institution_to_prefix:
            prefixes = institution_to_prefix[inst]

            if taxon:
                for prefix in prefixes:
                    if taxon and taxon in prefix.lower():  # match taxon with suffix in GUID_PREFIX
                        matched_prefixes.append(prefix)
            else:
                matched_prefixes = prefixes  # fallback to all if taxon not given

            if matched_prefixes:
                params["guid_prefix"] = ",".join(matched_prefixes)

    # Add all other mapped fields
    for user_field, arctos_field in FIELD_TO_ARCTOS_PARAM.items():
        if user_field == "institution":
            continue  # skip, already handled

        if user_field in fields:
            value = fields[user_field]
            if value not in ["N/A", "not specified", "", None]:
                if user_field == "location":
                    inst_val = fields.get("institution", "").lower()
                    location_val = str(value).lower()
                    if inst_val and inst_val in location_val:
                        continue  # skip redundant location
                params[arctos_field] = value

    return f"{base_url}?{urlencode(params)}"


# In[75]:


# 📍 INTERACTIVE CHATBOT TEST

# Example user input
user_input = input("Enter your specimen search query: ")

# Extract fields
fields = extract_query_fields(user_input)
print("\nExtracted Fields:")
print(fields)

# Generate Arctos URL
arctos_url = generate_arctos_search_url(fields)
print("\nGenerated Arctos Search URL:")
print(arctos_url)

# Query Arctos
results = query_arctos(fields)
# Format and show results
response = format_results(results)
print("\nChatbot Response:\n")
print(response)

# In[53]:


import streamlit as st


# In[59]:


# Streamlit app
# Streamlit app
import streamlit as st
from streamlit.components.v1 import html
from PIL import Image

# Load and display logo
logo = Image.open("Arctos_logo.png")
st.image(logo, width=140)

st.markdown("<h1 style='color: #003366;'>🔎 Arctos Query Search Chatbot</h1>", unsafe_allow_html=True)

# Description
st.markdown("""
<div style='text-align: left; font-size: 16px; line-height: 1.6;color: #003366;'>
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

            except Exception as e:
                st.error(f"Error: {e}")
elif clear_clicked:
    st.experimental_rerun()
