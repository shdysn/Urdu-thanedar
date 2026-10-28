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

# 1. Munshi
def run_munshi(pil_image):
    prompt = """Transcribe all Urdu Nastaliq text verbatim. Output ONLY the raw Urdu text."""
    response = client_munshi.models.generate_content(
        model="gemini-1.5-flash",
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
        model="gemini-1.5-flash",
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
        model="gemini-1.5-flash",
        contents=[pil_image, prompt],
        config=strict_config
    )
    
    full_output = response.text.strip() if response and hasattr(response, 'text') and response.text else ""
    
    final_text = full_output
    if "[VERDICT_START]" in full_output and "[VERDICT_END]" in full_output:
        final_text = full_output.split("[VERDICT_START]")[1].split("[VERDICT_END]")[0].strip()
        
    doubts = "None"
    if "[DOUBTS_START]" in full_output and "[DOUBTS_END]" in full_output:
        doubts = full_output.split("[DOUBTS_START]")[1].split("[DOUBTS_END]")[0].strip()
        
    return final_text, doubts

def run_multi_agent_pipeline(pil_image):
    draft = run_munshi(pil_image)
    objections = run_inspector_debate(pil_image, draft)
    final_text, doubts = run_thanedar_ruling(pil_image, draft, objections)
    return final_text, doubts
