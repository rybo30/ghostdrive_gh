# =============================================================
# AI COUNCIL v7.3 — FULL PRODUCTION SCRIPT (FIXED INDENTS)
# =============================================================
import json, os, re
from cryptography.fernet import Fernet
from model_registry import load_model_from_config

# --- CONFIGURATION & MAPPING ---
PRETTY_NAMES = {
    "jynx_summarizer": "Summary",
    "jynx_vision": "Vision Expert",
    "jynx_expert_logic": "Logic Expert",
    "jynx_expert_math": "Math Expert",
    "jynx_expert_coding": "Coding Expert",
    "jynx_expert_emotion": "Emotion Expert",
    "jynx_expert_survival": "Survival Expert",
    "jynx_expert_finance": "Finance Expert",
    "jynx_expert_psychology": "Psychology Expert",
    "jynx_expert_medical": "Medical Expert",
    "jynx_expert_cyber": "Cybersecurity Expert",
    "jynx_judge": "Final Verdict",
    "jynx_expert_history": "History Expert",
    "jynx_expert_sarcasm": "People Expert",
    "jynx_expert_politics": "Political Expert",
    "jynx_expert_conspiracy": "Conspiracy Intelligence Expert",
    "jynx_expert_mental_health": "Mental Health Expert",
}

EXPERT_MAP = {
    "logic": "jynx_expert_logic",
    "math": "jynx_expert_math",
    "coding": "jynx_expert_coding",
    "emotion": "jynx_expert_emotion",
    "survival": "jynx_expert_survival",
    "finance": "jynx_expert_finance",
    "psychology": "jynx_expert_psychology",
    "medical": "jynx_expert_medical",
    "cyber": "jynx_expert_cyber",
    "history": "jynx_expert_history",
    "people": "jynx_expert_sarcasm",
    "politics": "jynx_expert_politics",
    "conspiracy": "jynx_expert_conspiracy",
    "mental health": "jynx_expert_mental_health",
}

FIELD_DESCRIPTIONS = {
    "jynx_vision": "objective visual decomposition",
    "jynx_expert_logic": "deductive reasoning and formal logic",
    "jynx_expert_math": "statistical and numerical analysis",
    "jynx_expert_coding": "algorithmic thinking and architecture",
    "jynx_expert_emotion": "affective empathy and emotional states",
    "jynx_expert_survival": "tactical resource and risk management",
    "jynx_expert_finance": "market mechanics and economics",
    "jynx_expert_psychology": "cognitive patterns and personality",
    "jynx_expert_medical": "biological systems and health",
    "jynx_expert_cyber": "network vulnerability and digital forensics",
    "jynx_expert_history": "historical precedent and causality",
    "jynx_expert_sarcasm": "crowd dynamics and human behavior",
    "jynx_expert_politics": "power mechanics and statecraft",
    "jynx_expert_conspiracy": "asymmetric and covert information",
    "jynx_expert_mental_health": "therapeutic resilience",
}

# --- NEURAL MAPPING HELPERS ---
def get_user_profile_context(username, fernet):
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        vault_path = os.path.join(base_dir, "Everything_else", "vault", f"{username}_profile.enc")
        if not os.path.exists(vault_path):
            vault_path = os.path.join(base_dir, "core", "Everything_else", "vault", f"{username}_profile.enc")

        if os.path.exists(vault_path):
            with open(vault_path, "rb") as f:
                decrypted = fernet.decrypt(f.read())
                data = json.loads(decrypted)
                h = data.get("heuristics", {})
                
                context = f"\n[OPERATOR NEURAL MAP]\n"
                context += f"Callsign: {h.get('callsign', username)}\n"
                context += f"Goal: {h.get('goal', 'Classified')}\n"
                context += f"Fear: {h.get('fear', 'Classified')}\n"
                context += f"Style: {h.get('logic', 'Standard')}\n"
                return context
    except Exception: pass
    return f"\n[OPERATOR NEURAL MAP]\nCallsign: {username}\n"

# --- MAIN ENGINE ---
def run_council_streaming(user_prompt, image_path=None, username="Operator", fernet=None):
    previous_notes = ""
    user_context = get_user_profile_context(username, fernet) if fernet else f"\n[OPERATOR NEURAL MAP]\nCallsign: {username}\n"

    # === 0. VISION ===
    if image_path:
        yield ("expert_start", "Vision Expert")
        vision_prompt = f"{user_context}\nAnalyze visual data for: {user_prompt}"
        try:
            llm_fn, _ = load_model_from_config("jynx_vision")
            vision_buffer = ""
            for token in llm_fn(vision_prompt, image_path=image_path, stream_override=True):
                if token:
                    vision_buffer += token
                    yield ("expert_token", "Vision Expert", token)
            previous_notes += f"Vision Analysis: {vision_buffer}\n\n"
            yield ("expert_done", "Vision Expert", vision_buffer)
        except Exception as e:
            previous_notes += f"Vision Error: {str(e)}\n"

    # === 1. SUMMARIZER & ROUTING ===
    summarizer_prompt = f"""
[SYSTEM DATA: USER PROFILE]
{user_context}
[END PROFILE]

TASK: Analyze the "Current Input" below. 
1. Provide a 1-sentence summary of what the user is asking.
2. Select the 3 most relevant experts from the ALLOWED list.

ALLOWED EXPERTS: Logic, Math, Coding, Emotion, Survival, Finance, Psychology, Medical, Cyber, History, People, Politics, Mental Health, Conspiracy.

EXACT OUTPUT FORMAT:
***SUMMARY*** <brief summary>
***EXPERTS*** <list of experts>

Current Input: "{user_prompt}"
### Response:"""

    llm_fn, _ = load_model_from_config("jynx_summarizer")
    summary_buffer = ""
    for chunk in llm_fn(summarizer_prompt, stream_override=True, max_tokens=200, temperature=0.1):
        token = chunk.get("choices", [{}])[0].get("text") or chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
        if token:
            summary_buffer += token
            display_token = token.replace("***SUMMARY***", "**Target:**").replace("***EXPERTS***", "\n**Experts:**")
            yield ("summary", display_token)
    yield ("summary_done", summary_buffer)

    # === 2. ROBUST EXPERT SELECTION (FUZZY) ===
    expert_ids = []
    search_text = summary_buffer.lower()
    for keyword, model_id in EXPERT_MAP.items():
        if keyword in search_text:
            expert_ids.append(model_id)

    expert_ids = list(dict.fromkeys(expert_ids))[:3]
    if not expert_ids:
        expert_ids = ["jynx_expert_logic", "jynx_expert_psychology"]

    # === 3. SEQUENTIAL EXPERT LOOP ===
    for expert_id in expert_ids:
        expert_name = PRETTY_NAMES.get(expert_id, expert_id)
        field = FIELD_DESCRIPTIONS.get(expert_id, "expertise")
        yield ("expert_start", expert_name)

        expert_prompt = f"""{user_context}
Persona: You are the {expert_name}, an expert in {field}. 

Previous Insights: 
{previous_notes or "You are the lead expert for this request."}

User Request: "{user_prompt}"

Task:
1. Provide a new perspective from your expertise in {field}.
2. Bring new ideas or contrast your view with the previous expert to ensure a unique contribution.
3. Try your best, no wrong answers.
### Response:"""

        llm_fn, _ = load_model_from_config(expert_id)
        expert_buffer = ""
        for chunk in llm_fn(expert_prompt, stream_override=True, max_tokens=800, temperature=0.7, stop=["User:", "You:", "Operator:", "Instruction:"]):
            token = chunk if isinstance(chunk, str) else chunk.get("choices", [{}])[0].get("text") or chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if token:
                expert_buffer += token
                yield ("expert_token", expert_name, token)
        
        previous_notes += f"[{expert_name}]: {expert_buffer}\n\n"
        yield ("expert_done", expert_name, expert_buffer)

    # === 4. FINAL VERDICT ===
    yield ("verdict_start", "")
    verdict_prompt = f"""{user_context}
Review the Council's notes and provide a final synthesis.

Notes:
{previous_notes}

Format:
**Final Verdict:** [1-2 concise paragraphs]
**Actionable Takeaways:**
- [Step]
- [Step]
- [Step]
### Verdict:"""
    
    llm_fn, _ = load_model_from_config("jynx_summarizer")
    for chunk in llm_fn(verdict_prompt, stream_override=True, max_tokens=600, temperature=0.2):
        token = chunk.get("choices", [{}])[0].get("text") or chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
        if token:
            yield ("verdict_token", token)
    yield ("done", "")