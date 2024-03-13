import spacy
from spacy.pipeline import EntityRuler
from spacy.matcher import Matcher
import base64
import io
import pandas as pd
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from pdfminer.high_level import extract_text
from collections import defaultdict
import json

# Load the spaCy model
nlp = spacy.load('en_core_web_md')

# Create and add the EntityRuler to the pipeline
ruler = nlp.add_pipe("entity_ruler")  # For spaCy 3.x
skill_path = "skills.jsonl"
ruler.from_disk(skill_path)

# Initialize Matcher and define patterns
matcher = Matcher(nlp.vocab)


# Define patterns
work_experience_patterns = [
    [{"POS": "PROPN", "OP": "+"}, {"LOWER": "at"}, {"POS": "PROPN", "OP": "+"}],  # Match company names preceded by "at"
    [{"POS": "NOUN", "OP": "+"}, {"POS": "ADP"}, {"POS": "PROPN", "OP": "+"}],    # Match job titles followed by prepositions and company names
    [{"POS": "VERB"}, {"POS": "NOUN", "OP": "+"}, {"LOWER": "at"}, {"POS": "PROPN", "OP": "+"}],  # Match verbs followed by job titles and company names
]
matcher.add("WORK_EXPERIENCE", work_experience_patterns)

contact_info_patterns = [
    [{"LIKE_EMAIL": True}],  # Match email addresses
    # Additional patterns for phone numbers or other contact info can be added here
]
matcher.add("CONTACT_INFO", contact_info_patterns)

certification_patterns = [
    [{"LOWER": {"IN": ["certified", "certificate", "certification"]}}, {"IS_ALPHA": True, "OP": "*"}],  # Match variations of certification terms
]
matcher.add("CERTIFICATION", certification_patterns)

# Define function to extract all information from text
def extract_all_information(text):
    doc = nlp(text)
    extracted_info = {
        "Person Name": [],
        "Skill": [],
        "Work Experience": [],
        "Certification": [],
        "Contact Info": []
    }
    # Extract entities
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            extracted_info["Person Name"].append(ent.text)
        elif ent.label_ == "SKILL":
            extracted_info["Skill"].append(ent.text)
    # Use matcher to find matches
    matches = matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        label = nlp.vocab.strings[match_id]
        key = label.title().replace("_", " ")
        extracted_info[key].append(span.text)
    for key in extracted_info.keys():
        extracted_info[key] = list(set(extracted_info[key]))
    return extracted_info

# Process uploaded file
def process_uploaded_file(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        text = extract_text(io.BytesIO(decoded))
        processed_info = extract_all_information(text)
        return processed_info
    except Exception as e:
        print(e)
        return 'Error processing the file.'

# Dash app setup
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Setup Dash app layout with descriptive elements
app.layout = dbc.Container(fluid=True, children=[
    html.H1("Resume Parser Dashboard", className="mb-4 mt-4"),
    html.P("Upload your resume in PDF format to extract and analyze skills, work experiences, certifications, and contact information.", className="mb-4"),
    dcc.Upload(
        id='upload-data',
        children=html.Div(['Drag and Drop or ', html.A('Click to Select a Resume File')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
            'textAlign': 'center', 'margin-top': '20px', 'margin-bottom': '20px'
        },
        multiple=False
    ),
    html.Div(id='output-data-upload', className="mt-4")
])

@app.callback(Output('output-data-upload', 'children'),
              Input('upload-data', 'contents'))
def update_output(contents):
    if contents is not None:
        processed_info = process_uploaded_file(contents)
        if isinstance(processed_info, dict):
            return html.Div([
                html.H5("Extracted Information", className="mb-4"),
                dbc.Table.from_dataframe(pd.DataFrame.from_dict(processed_info, orient='index').transpose(), striped=True, bordered=True, hover=True, responsive=True, className="mb-4"),
            ])
        else:
            return dbc.Alert("Failed to process file. Please ensure it's a valid PDF document.", color="danger", className="mt-4")
    return html.Div()

if __name__ == '__main__':
    app.run_server(debug=True)
