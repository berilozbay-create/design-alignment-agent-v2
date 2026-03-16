import json
import re
from prompt_builders import build_final_brief_prompt


def generate_final_brief(session_id: str, db, gemini_client):
    doc_ref = db.collection("sessions").document(session_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise ValueError("Session not found")

    session = snap.to_dict() or {}

    style_selected = session.get("style_selected", [])
    style_commentary = session.get("style_commentary")
    rounds = session.get("rounds", {})
    current_round = session.get("current_round", 1)

    if not style_commentary:
        raise ValueError("style_commentary not found in session")

    if not isinstance(rounds, dict) or not rounds:
        raise ValueError("round data not found in session")

    selected_path = []

    for round_key in sorted(rounds.keys(), key=lambda x: int(x)):
        round_data = rounds.get(round_key, {})
        selected = round_data.get("selected")
        if selected:
            selected_path.append(selected)

    prompt = build_final_brief_prompt(
        style_selected=style_selected,
        style_commentary=style_commentary,
        rounds=rounds,
        current_round=current_round,
        selected_path=selected_path,
    )

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    raw_text = getattr(response, "text", "") or ""
    raw_text = re.sub(r"```json", "", raw_text)
    raw_text = re.sub(r"```", "", raw_text).strip()

    try:
        parsed = json.loads(raw_text)
    except Exception:
        raise ValueError(f"Gemini did not return valid JSON. Raw output:\n{raw_text}")

    required_keys = [
        "final_title",
        "final_summary",
        "key_design_rules",
        "axis_summary",
    ]

    for key in required_keys:
        if key not in parsed:
            raise ValueError(f"Missing key in final brief: {key}")

    doc_ref.set(
        {
            "final_brief": parsed,
        },
        merge=True,
    )

    return {
        "session_id": session_id,
        "final_round": current_round,
        "selected_path": selected_path,
        "final_brief": parsed,
    }