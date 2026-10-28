import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

raw_keys = os.getenv("GEMINI_API_KEY", "")
api_keys = []
for k in raw_keys.replace("\n", ",").replace(";", ",").split(","):
    cleaned = k.strip().strip("'\"")
    if "GEMINI_API_KEY=" in cleaned:
        cleaned = cleaned.split("GEMINI_API_KEY=")[-1].strip().strip("'\"")
    if cleaned:
        api_keys.append(cleaned)

if not api_keys:
    raise ValueError("GEMINI_API_KEY nahi mili!")

key_munshi = api_keys[0]
key_inspector = api_keys[1] if len(api_keys) > 1 else api_keys[0]
key_thanedar = api_keys[2] if len(api_keys) > 2 else (api_keys[1] if len(api_keys) > 1 else api_keys[0])

client_munshi = genai.Client(api_key=key_munshi)
client_inspector = genai.Client(api_key=key_inspector)
client_thanedar = genai.Client(api_key=key_thanedar)

# Zero Creativity Configuration (Guessed words jaise 'kitchen' ko rokne ke liye)
strict_config = types.GenerateContentConfig(
    temperature=0.0
)

import re

# 1. Munshi
def run_munshi(pil_image):
    prompt = """Transcribe all Urdu Nastaliq text verbatim. Output ONLY the raw Urdu text."""
    response = client_munshi.models.generate_content(
        model="gemini-2.5-flash",
        contents=[pil_image, prompt],
        config=strict_config
    )
    return response.text.strip() if response and hasattr(response, 'text') and response.text else ""

# 2. Inspector Debate
def run_inspector_debate(pil_image, munshi_draft):
    prompt = f"""You are the Quality Inspector.
Munshi's draft:
---
{munshi_draft}
---
TASK:
Compare against image closely. Challenge any missed letters, substituted words (e.g. confusing 'میس' with 'کچن', or 'حبس' with 'جس'), or dropped prepositions.
State your objections clearly."""
    response = client_inspector.models.generate_content(
        model="gemini-2.5-flash",
        contents=[pil_image, prompt],
        config=strict_config
    )
    return response.text.strip() if response and hasattr(response, 'text') and response.text else ""

# 3. Thanedar Supreme Verdict + Doubt Logger
def run_thanedar_ruling(pil_image, munshi_draft, inspector_objections):
    prompt = f"""You are the 'THANEDAR' (Supreme Arbiter).

CRITICAL ANTI-HALLUCINATION RULES:
1. NEVER substitute uncommon words with common words (e.g. if the ink says 'میس', write 'میس', DO NOT write 'کچن').
2. NEVER guess missing words. Only transcribe what is visibly inked.
3. Verify subtle ligatures and context carefully.

[MUNSHI DRAFT]: {munshi_draft}
[INSPECTOR OBJECTIONS]: {inspector_objections}

OUTPUT FORMAT (STRICT):
[VERDICT_START]
(Put 100% verified Urdu text here)
[VERDICT_END]

[DOUBTS_START]
(If you have any doubt about any specific word, list: - Page word: [word1 / word2] (Reason). If NO doubts, write 'None')
[DOUBTS_END]"""

    response = client_thanedar.models.generate_content(
        model="gemini-2.5-flash",
        contents=[pil_image, prompt],
        config=strict_config
    )
    
    full_output = response.text.strip() if response and hasattr(response, 'text') and response.text else ""
    
    # Safe regex parsing to extract text blocks even if brackets are malformed
    verdict_match = re.search(r'\[VERDICT_START\](.*?)(?:\[VERDICT_END\]|$)', full_output, re.DOTALL | re.IGNORECASE)
    if verdict_match:
        final_text = verdict_match.group(1).strip()
    else:
        final_text = full_output

    doubts_match = re.search(r'\[DOUBTS_START\](.*?)(?:\[DOUBTS_END\]|$)', full_output, re.DOTALL | re.IGNORECASE)
    if doubts_match:
        doubts = doubts_match.group(1).strip()
    else:
        doubts = "None"
        
    # Strictly enforce pure Urdu Nastaliq (Perso-Arabic) script
    # Strip Devanagari/Hindi characters
    final_text = re.sub(r'[\u0900-\u097F]+', '', final_text)

    # Strip common English meta-comments (e.g. "(Wait, let's keep...)")
    final_text = re.sub(r'\([a-zA-Z\s,.\']+\)', '', final_text)

    # Strip any stray unclosed tags like [VERDICT_START
    final_text = re.sub(r'\[\w+.*?$', '', final_text, flags=re.MULTILINE)
    final_text = re.sub(r'\[VERDICT_START.*?$', '', final_text, flags=re.MULTILINE | re.IGNORECASE)
    final_text = re.sub(r'\[VERDICT_END.*?$', '', final_text, flags=re.MULTILINE | re.IGNORECASE)
    final_text = re.sub(r'\[DOUBTS_START.*?$', '', final_text, flags=re.MULTILINE | re.IGNORECASE)
    final_text = re.sub(r'\[DOUBTS_END.*?$', '', final_text, flags=re.MULTILINE | re.IGNORECASE)

    return final_text.strip(), doubts

def run_multi_agent_pipeline(pil_image):
    draft = run_munshi(pil_image)
    objections = run_inspector_debate(pil_image, draft)
    final_text, doubts = run_thanedar_ruling(pil_image, draft, objections)
    return final_text, doubts
