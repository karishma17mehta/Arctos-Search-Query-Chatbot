# 🔍 Arctos Search Query Chatbot
This AI-powered Streamlit chatbot allows researchers to search the Arctos biodiversity database using plain English queries like:

"Find birds collected in Alaska in 1999"
"Show me shrews from California with tissue samples"

Developed as part of a UC Davis MSBA practicum in collaboration with the Museum of Vertebrate Zoology (MVZ) and the Arctos Consortium, the tool enhances accessibility and usability of over 5 million biological specimen records.

**📁 Project Structure**
File / Folder	Description
app.py	Main Streamlit app with all chatbot logic
_portals.csv	Mapping of institutions to Arctos GUID_PREFIX
requirements.txt	Python dependencies
.streamlit/secrets.toml	Secure API credentials (OpenAI, Arctos, Google Sheets)
README.md	This documentation

**🔧 Features**

- Natural language query input

- GPT-3.5-based field extraction

- Arctos-compatible search URL generation

- Query logs to Google Sheets for future analysis


**Functional Flow**

- User Input: Natural query (e.g. "Find skinks collected by Charles Burt in San Diego")

- OpenAI GPT-3.5: Extracts structured fields (taxon, location, collector, etc.)

- Field Mapping: Converts fields to Arctos API-compatible parameters

- Institution Mapping: Matches institution names to guid_prefix (from _portals.csv)

- URL Generation: Creates a ready-to-use Arctos search URL

- Query Logging: Logs the search with timestamp to Google Sheets


**Google Sheets Logging**

All user queries, extracted fields, and the generated search URL are logged to a Google Sheet.

This log can be used for user behavior analysis, training improvements, and future NLP enhancements.


**Future Improvements**

- Editable extracted fields before submitting

- Pagination and sorting of API results

- Enhanced synonym resolution for taxon names

- Support for more complex queries (multi-taxon, date ranges)

- OAuth-based user access and saved searches



**
