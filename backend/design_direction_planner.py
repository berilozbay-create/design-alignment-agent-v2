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


def build_stage2_planner_prompt(primary_style: str, secondary_style: str, style_commentary_text: str) -> str:
    return f"""
Role:
You are a Senior Interior Design Director.

Task:
Create 4 distinct, high-end design directions based on a primary style and a secondary style.

Primary style:
{primary_style}

Secondary style:
{secondary_style}

Style commentary:
{style_commentary_text}

Direction briefs:
- B: Stay entirely within {primary_style}. Same aesthetic soul, but choose a distinctly different expression — different colour palette, different material character, different furniture objects. Do not introduce any influence from {secondary_style}.
- C: Lead strongly with {primary_style} — approximately 70% of the design language should feel like {primary_style}. Introduce {secondary_style} influence through one or two specific elements only: for example the colour palette, a textile choice, or a lighting character. The room should read as {primary_style} first.
- E: Stay entirely within {secondary_style}. Same aesthetic soul, but choose a distinctly different expression — different colour palette, different material character, different furniture objects. Do not introduce any influence from {primary_style}.
- F: Lead strongly with {secondary_style} — approximately 70% of the design language should feel like {secondary_style}. Introduce {primary_style} influence through one or two specific elements only. The room should read as {secondary_style} first.

Do not drift into unrelated styles.

Output exactly 4 options with ids B, C, E, F.

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
    }},
    {{
      "id": "E",
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
      "id": "F",
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
    primary_style: str,
    secondary_style: str,
    style_commentary: dict,
):
    style_commentary_text = style_commentary.get("raw_text", "") if isinstance(style_commentary, dict) else ""

    prompt = build_stage2_planner_prompt(
        primary_style=primary_style,
        secondary_style=secondary_style,
        style_commentary_text=style_commentary_text,
    )

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    raw_text = getattr(response, "text", "") or ""
    parsed = _parse_json_response(raw_text)

    options = parsed.get("options", [])
    if not isinstance(options, list) or len(options) != 4:
        raise ValueError("Stage 2 planner must return exactly 4 options")

    expected_ids = {"B", "C", "E", "F"}
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
        raise ValueError(f"Planner must return ids B, C, E and F exactly. Got: {seen_ids}")

    return {
        "options": normalized_options
    }