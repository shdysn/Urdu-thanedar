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


def run_inspector_debate(pil_image, munshi_draft):
    prompt = f"""You are the Inspector in a multi-agent debate.
Munshi has submitted this draft:
---
{munshi_draft}
---

Cross-examine Munshi's draft against the original image. Challenge ambiguous words and dots or ligatures (for example, حبس versus جس or بہترین versus بہتر), check context, and identify missing words under watermarks or missing punctuation. Return short, specific objections and corrections addressed to Munshi and Thanedar. Do not provide a replacement transcript."""
    response = client_inspector.models.generate_content(
        model=MODEL,
        contents=[pil_image, prompt],
    )
    return (response.text or "").strip()


def run_thanedar_ruling(pil_image, munshi_draft, inspector_objections):
    prompt = f"""You are the THANEDAR, the final arbiter and judge of this Urdu Nastaliq transcription debate.

The original page image is the primary source of truth.
[MUNSHI'S DRAFT]
{munshi_draft}
[INSPECTOR'S OBJECTIONS AND CHALLENGES]
{inspector_objections}

Review every objection against the image, settle disputes by inspecting the pixels, and produce the final Urdu text. Ensure words under watermarks, ligatures, and nuqtas are checked.
Output ONLY the final certified Urdu text between [VERDICT_START] and [VERDICT_END]. No notes or English."""
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
    print("Munshi draft bana raha hai...")
    munshi_draft = run_munshi(pil_image)
    print("Inspector Munshi ke draft par aitrazat aur behas kar raha hai...")
    inspector_objections = run_inspector_debate(pil_image, munshi_draft)
    print("Thanedar behas aur tasveer dekh kar aakhri faisla kar raha hai...")
    return run_thanedar_ruling(pil_image, munshi_draft, inspector_objections)
