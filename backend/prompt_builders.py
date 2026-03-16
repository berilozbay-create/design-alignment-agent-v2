def build_round_prompt(style_commentary: dict, selected_styles: list[str], round_number: int) -> str:
    raw_text = style_commentary.get("raw_text", "")

    return f"""
You are an interior design concept generator.

Selected styles:
{selected_styles}

Style commentary:
{raw_text}

Task:
Generate exactly 4 different interior design directions for round {round_number}.

The four options must be labeled A, B, C, and D.

Each option must contain:
- id
- title
- direction
- commentary

Rules:
- Stay consistent with the selected styles
- Make the four options meaningfully different
- Do not change architecture or layout
- Focus on styling, materials, furniture, and atmosphere

Return JSON only in this format:

{{
  "options": [
    {{
      "id": "A",
      "title": "...",
      "direction": "...",
      "commentary": "..."
    }},
    {{
      "id": "B",
      "title": "...",
      "direction": "...",
      "commentary": "..."
    }},
    {{
      "id": "C",
      "title": "...",
      "direction": "...",
      "commentary": "..."
    }},
    {{
      "id": "D",
      "title": "...",
      "direction": "...",
      "commentary": "..."
    }}
  ]
}}
"""


def build_final_brief_prompt(
    style_selected: list[str],
    style_commentary: dict,
    rounds: dict,
    current_round: int,
    selected_path: list[str],
) -> str:
    raw_text = style_commentary.get("raw_text", "")

    return f"""
You are an interior design mediator creating the final aligned design brief for a client.

Selected styles:
{style_selected}

Style commentary:
{raw_text}

Rounds data:
{rounds}

Current round:
{current_round}

Selected path through rounds:
{selected_path}

Task:
Create a final design brief based on the user's design journey so far.

Return valid JSON only in this exact format:

{{
  "final_title": "...",
  "final_summary": "...",
  "key_design_rules": [
    "...",
    "...",
    "...",
    "...",
    "..."
  ],
  "axis_summary": {{
    "minimalism": "...",
    "warmth": "...",
    "texture": "...",
    "contrast": "...",
    "craft": "..."
  }}
}}

Rules:
- final_title should be short and strong
- final_summary should be 3 to 5 sentences
- key_design_rules should contain exactly 5 items
- axis_summary values should be simple words like low, medium, high or medium-high
- Base the result on the actual selected path and round evolution
- Do not return markdown
- Return JSON only
"""