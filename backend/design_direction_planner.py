import json
import re


REQUIRED_TEXT_FIELDS = [
    "style_name",
    "direction_summary",
    "color_story",
    "wall_material",
    "floor_material",
    "furniture_silhouette",
    "furniture_finishes",
    "decor_density",
    "botanical_species",
    "lighting_character",
    "commentary",
]


def _clean_json_text(raw_text: str) -> str:
    raw_text = raw_text or ""
    raw_text = re.sub(r"```json", "", raw_text)
    raw_text = re.sub(r"```", "", raw_text)
    return raw_text.strip()


def _parse_json_response(raw_text: str) -> dict:
    cleaned = _clean_json_text(raw_text)

    try:
        return json.loads(cleaned)
    except Exception:
        raise ValueError(f"Gemini did not return valid JSON. Raw output:\n{cleaned}")


def build_stage2_planner_prompt(selected_style: str, style_commentary_text: str) -> str:
    return f"""
Role:
You are a Senior Interior Design Director.

Task:
Create 2 distinct, high-end design directions for the selected style.

Selected style:
{selected_style}

Style commentary:
{style_commentary_text}

Important:
These two directions must remain clearly within the selected style family.
Distinctness should come from:
- materiality
- palette
- decor density
- furniture silhouette

Do not drift into unrelated styles.

Output exactly 2 options with ids B and C.

Every option must include all fields.
Do not omit commentary.
If you are unsure, still return a short commentary sentence.

Return valid JSON only in this exact format:

{{
  "options": [
    {{
      "id": "B",
      "style_name": "...",
      "direction_summary": "...",
      "color_story": "...",
      "wall_material": "...",
      "floor_material": "...",
      "furniture_silhouette": "...",
      "furniture_finishes": "...",
      "decor_density": "...",
      "botanical_species": "...",
      "lighting_character": "...",
      "commentary": "..."
    }},
    {{
      "id": "C",
      "style_name": "...",
      "direction_summary": "...",
      "color_story": "...",
      "wall_material": "...",
      "floor_material": "...",
      "furniture_silhouette": "...",
      "furniture_finishes": "...",
      "decor_density": "...",
      "botanical_species": "...",
      "lighting_character": "...",
      "commentary": "..."
    }}
  ]
}}
""".strip()


def _normalize_option(option: dict) -> dict:
    if not isinstance(option, dict):
        option = {}

    normalized = {
        "id": str(option.get("id", "")).strip(),
    }

    for field in REQUIRED_TEXT_FIELDS:
        value = option.get(field, "")
        if value is None:
            value = ""
        normalized[field] = str(value).strip()

    return normalized


def plan_stage2_directions(
    gemini_client,
    selected_style: str,
    style_commentary: dict,
):
    style_commentary_text = style_commentary.get("raw_text", "") if isinstance(style_commentary, dict) else ""

    prompt = build_stage2_planner_prompt(
        selected_style=selected_style,
        style_commentary_text=style_commentary_text,
    )

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    raw_text = getattr(response, "text", "") or ""
    parsed = _parse_json_response(raw_text)

    options = parsed.get("options", [])
    if not isinstance(options, list) or len(options) != 2:
        raise ValueError("Stage 2 planner must return exactly 2 options")

    expected_ids = {"B", "C"}
    seen_ids = set()
    normalized_options = []

    for option in options:
        normalized = _normalize_option(option)
        option_id = normalized.get("id")

        if option_id not in expected_ids:
            raise ValueError(f"Invalid planner option id: {option_id}")

        if option_id in seen_ids:
            raise ValueError(f"Duplicate planner option id: {option_id}")

        seen_ids.add(option_id)
        normalized_options.append(normalized)

    if seen_ids != expected_ids:
        raise ValueError(f"Planner must return ids B and C exactly. Got: {seen_ids}")

    return {
        "options": normalized_options
    }