# arctos_chatbot_app.py

import os
import json
import openai
import requests
import pandas as pd
import inflect
import streamlit as st
import gspread
from datetime import datetime
from urllib.parse import urlencode
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image

# Load env variables
load_dotenv()

# Set up API clients
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
ARCTOS_API_KEY = st.secrets["ARCTOS_API_KEY"]
ARCTOS_API_BASE_URL = "https://arctos.database.museum/component/api/v2/catalog.cfc"
p = inflect.engine()

# Load guid_prefix mapping
try:
    portal_df = pd.read_csv("_portals.csv")
    institution_to_prefix = {}
    for _, row in portal_df.iterrows():
        name = row["INSTITUTION"].lower().strip()
        prefix = row["GUID_PREFIX"].strip()
        institution_to_prefix.setdefault(name, []).append(prefix)
except Exception as e:
    st.error(f"Failed to load portals.csv: {e}")
    institution_to_prefix = {}

# Taxon mapping
TAXON_CATEGORY_MAP = {
    "reptiles and amphibians": "herp", "amphibians": "herp", "reptiles": "herp",
    "birds": "bird", "aves": "bird", "avian": "bird",
    "mammals": "mamm", "mammal": "mamm", "mammalia": "mamm",
    "fishes": "fish", "fish": "fish", "pisces": "fish",
    "insects": "ento", "bugs": "ento", "entomology": "ento",
    "invertebrates": "inv", "invertebrate": "inv",
    "parasites": "para", "parasite": "para",
    "arthropods": "arth", "arthropod": "arth",
    "plants": "plant", "flora": "plant",
    "fungi": "fung", "fungus": "fung", "mycology": "fung",
    "paleontology": "paleo", "fossils": "paleo",
    "eggs": "egg", "tissues": "tissue", "tissue": "tissue",
    "dna": "dna", "genetic material": "dna", "genetics": "gen",
    "algae": "algae", "botany": "bot", "botanical": "bot"
}

FIELD_TO_ARCTOS_PARAM = {
    "taxonomy": "scientific_name", "taxon": "scientific_name", "location": "spec_locality",
    "any_geog": "any_geog", "country": "country", "state": "state_prov", "state_province": "state_prov",
    "part": "part_search", "part search": "part_search", "collector": "collector",
    "media type": "media_type", "type status": "type_status",
    "date": "verbatim_date", "year": "verbatim_date",
    "has tissue": "is_tissue", "scientific_name_match": "scientific_name_match_type",
    "agent role": "coll_role", "guid_prefix": "guid_prefix", "institution": "guid_prefix"
}

# Extract fields

def extract_query_fields(user_input):
    prompt = f"""
    Extract relevant fields from: '{user_input}'.
    Return JSON with only: 'taxon_name', 'verbatim_date', 'part', 'media_type', 'type_status', 
    'has tissue', 'collector', 'country', 'state', 'location', 'institution'.

    Instructions:
    - Assign museum/university names to 'institution'.
    - Only assign geographic locations to 'location'.
    - Do not use 'location' for museums/universities.
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)

# Query Arctos

def query_arctos(fields):
    params = {"method": "getCatalogData", "queryformat": "struct", "api_key": ARCTOS_API_KEY}
    for user_field, arctos_field in FIELD_TO_ARCTOS_PARAM.items():
        if user_field in fields:
            value = fields[user_field]
            if value:
                params[arctos_field] = value
    response = requests.get(ARCTOS_API_BASE_URL, params=params)
    response.raise_for_status()
    return response.json()

# Format results

def format_results(results):
    records = results.get('DATA', [])
    if not records:
        return "No results found."
    return "\n\n".join(
        f"{r.get('scientific_name', 'Unknown species')} collected from {r.get('spec_locality') or r.get('state_prov') or r.get('country', 'Unknown')} on {r.get('verbatim_date', 'Unknown date')}"
        for r in records)

# Generate URL

def generate_arctos_search_url(fields):
    base_url = "https://arctos.database.museum/search.cfm"
    params = {}

    if "institution" in fields:
        inst = fields["institution"].lower().strip()
        taxon = fields.get("taxon_name", "").lower().strip()
        taxon = TAXON_CATEGORY_MAP.get(taxon, p.singular_noun(taxon) or taxon)
        if inst in institution_to_prefix:
            prefixes = institution_to_prefix[inst]
            matched = [pfx for pfx in prefixes if taxon and taxon in pfx.lower()] or prefixes
            params["guid_prefix"] = ",".join(matched)

    for user_field, arctos_field in FIELD_TO_ARCTOS_PARAM.items():
        if user_field != "institution" and user_field in fields:
            value = fields[user_field]
            if value and not (user_field == "location" and fields.get("institution", "").lower() in str(value).lower()):
                params[arctos_field] = value

    return f"{base_url}?{urlencode(params)}"

# Log to Google Sheets

def log_to_google_sheets(query, fields, url):
    try:
        creds_dict = st.secrets["google_service_account"]
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("arctos_search_logs").sheet1
        sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query, json.dumps(fields), url])
    except Exception as e:
        st.warning(f"Logging failed: {e}")

# UI
logo = Image.open("Arctos_logo.png")
st.image(logo, width=140)

st.markdown("""
<h1 style='color: #003366;'>🔎 Arctos Query Search Chatbot</h1>
<div style='text-align: left; font-size: 16px; line-height: 1.6; color: #003366;'>
This tool helps researchers search the Arctos database using natural language queries.<br><br>
Enter queries like <em>'Find shrews collected in New York in 1999'</em>.<br><br>
<b>Note:</b> Created by MSBA students at UC Davis in collaboration with the <b>Museum of Vertebrate Zoology (MVZ), UC Berkeley</b> and the <b>Arctos Consortium</b>.<br>
</div>
""", unsafe_allow_html=True)

user_query = st.text_input(" Enter your specimen search query:", placeholder="e.g. Search birds in Alaska")
search_col, clear_col = st.columns([1, 2])
search_clicked = search_col.button("SEARCH")
clear_clicked = clear_col.button("CLEAR")

if search_clicked and user_query:
    with st.spinner("Processing query..."):
        try:
            fields = extract_query_fields(user_query)
            st.subheader("Extracted Fields")
            st.json(fields)

            search_url = generate_arctos_search_url(fields)
            st.markdown(f"🔗 [**Open Arctos Search URL**]({search_url})")

            log_to_google_sheets(user_query, fields, search_url)

           # Optionally disable result querying:
           # results = query_arctos(fields)
           # st.subheader("📋 Search Results")
           # st.text(format_results(results))
        except Exception as e:
            st.error(f"❌ Error: {e}")

if clear_clicked:
    st.experimental_rerun()
