import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

raw_keys = os.getenv("GEMINI_API_KEY", "")
api_keys = []
for key in raw_keys.replace("\n", ",").replace(";", ",").split(","):
    cleaned = key.strip().strip("'\"")
    if "GEMINI_API_KEY=" in cleaned:
        cleaned = cleaned.split("GEMINI_API_KEY=")[-1].strip().strip("'\"")
    if cleaned:
        api_keys.append(cleaned)

if not api_keys:
    raise ValueError("GEMINI_API_KEY nahi mili! GitHub Secrets check karein.")

key_munshi = api_keys[0]
key_inspector = api_keys[1] if len(api_keys) > 1 else api_keys[0]
key_thanedar = api_keys[2] if len(api_keys) > 2 else key_inspector

client_munshi = genai.Client(api_key=key_munshi)
client_inspector = genai.Client(api_key=key_inspector)
client_thanedar = genai.Client(api_key=key_thanedar)
MODEL = "gemini-3.5-flash-lite"


def run_munshi(pil_image):
    prompt = """Transcribe all visible Urdu Nastaliq text from this book page image verbatim.
Do not skip lines or watermarks. Return ONLY the transcribed text."""
    response = client_munshi.models.generate_content(
        model=MODEL,
        contents=[pil_image, prompt],
    )
    return (response.text or "").strip()


def run_inspector(pil_image, munshi_draft):
    prompt = f"""You are the Quality Inspector.
Munshi (Agent 1) has prepared this transcription draft:
---
{munshi_draft}
---

Inspect the image closely. Identify missed words under watermarks, wrong ligatures, or missing prepositions. Provide a revised and corrected draft."""
    response = client_inspector.models.generate_content(
        model=MODEL,
        contents=[pil_image, prompt],
    )
    return (response.text or "").strip()


def run_thanedar(pil_image, munshi_draft, inspector_draft):
    prompt = f"""You are the THANEDAR, the final authority on Urdu Nastaliq transcription.

Use the original page image as the source of truth. Compare these drafts and resolve any disagreements by inspecting the image:
Munshi's first draft:
---
{munshi_draft}
---
Inspector's audited version:
---
{inspector_draft}
---

Ensure no words are dropped under watermarks and verify ligatures and nuqtas.
Output ONLY the final Urdu text between [VERDICT_START] and [VERDICT_END]. No notes or English."""
    response = client_thanedar.models.generate_content(
        model=MODEL,
        contents=[pil_image, prompt],
    )
    full_output = (response.text or "").strip()
    start_marker = "[VERDICT_START]"
    end_marker = "[VERDICT_END]"
    if start_marker in full_output and end_marker in full_output:
        return full_output.split(start_marker, 1)[1].split(end_marker, 1)[0].strip()
    return full_output


def run_multi_agent_pipeline(pil_image):
    munshi_draft = run_munshi(pil_image)
    inspector_draft = run_inspector(pil_image, munshi_draft)
    return run_thanedar(pil_image, munshi_draft, inspector_draft)
