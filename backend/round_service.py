from concurrent.futures import ThreadPoolExecutor
from google.cloud import firestore

from design_direction_planner import plan_stage2_directions
from image_generation_service import generate_image_with_gemini


STYLE_URL_MAP = {
    "Minimalist": "/static/styles/minimalist.png",
    "Maximalist": "/static/styles/maximalist.png",
    "Industrial": "/static/styles/industrial.png",
    "Scandinavian": "/static/styles/scandinavian.png",
    "Japandi": "/static/styles/japandi.png",
    "Midcentury Modern": "/static/styles/midcentury_modern.png",
    "Modern Farmhouse": "/static/styles/modern_farmhouse.png",
    "French Country": "/static/styles/french_country.png",
    "Hollywood Regency": "/static/styles/hollywood_regency.png",
    "Coastal": "/static/styles/coastal.png",
}


DIRECTION_A_COPY = {
    "Minimalist": {
        "style_name": "Minimalist Quiet Edit",
        "direction_summary": "A restrained minimalist direction centered on visual silence, open space, and low-noise material choices.",
        "color_story": "Warm white, greige, pale taupe, soft stone",
        "wall_material": "Smooth warm-white plaster",
        "floor_material": "Pale natural wood",
        "furniture_silhouette": "Low-profile, straight-lined, reduced forms",
        "furniture_finishes": "Matte plaster, pale wood, linen, subtle stone",
        "decor_density": "Very low and carefully edited",
        "botanical_species": "Single sculptural branch or minimal greenery",
        "lighting_character": "Soft indirect light with gentle shadow play",
        "commentary": "This direction keeps the composition disciplined and calm, using reduction and warm restraint rather than emptiness."
    },
    "Maximalist": {
        "style_name": "Maximalist Narrative Edit",
        "direction_summary": "A layered maximalist direction with strong storytelling through objects, color, and expressive surfaces.",
        "color_story": "Jewel tones, rich neutrals, saturated accents",
        "wall_material": "Decorative painted or wallpapered backdrop",
        "floor_material": "Dark timber or richly grounded base",
        "furniture_silhouette": "Statement silhouettes with bold personality",
        "furniture_finishes": "Velvet, mixed metals, lacquer, patterned textiles",
        "decor_density": "High but intentionally composed",
        "botanical_species": "Lush statement greenery",
        "lighting_character": "Decorative layered lighting with dramatic contrast",
        "commentary": "This direction embraces abundance and personality, but still needs a clear visual hierarchy to feel curated rather than cluttered."
    },
    "Industrial": {
        "style_name": "Industrial Soft Loft",
        "direction_summary": "A grounded industrial direction that balances exposed rawness with comfort and edited warmth.",
        "color_story": "Concrete grey, charcoal, rust, black, muted brown",
        "wall_material": "Concrete, exposed brick, or industrial plaster language",
        "floor_material": "Dark timber or concrete-toned base",
        "furniture_silhouette": "Utilitarian forms with metal-framed confidence",
        "furniture_finishes": "Steel, leather, reclaimed wood, matte black",
        "decor_density": "Low to moderate",
        "botanical_species": "Architectural green plant",
        "lighting_character": "Directional, urban, slightly dramatic",
        "commentary": "This direction exposes structure and material honesty while keeping enough softness to avoid a cold, over-staged loft look."
    },
    "Scandinavian": {
        "style_name": "Scandinavian Gentle Warmth",
        "direction_summary": "A light, functional Scandinavian direction built on comfort, proportion, and subtle warmth.",
        "color_story": "Soft white, pale oak, light grey, muted pastel accents",
        "wall_material": "Clean warm-white painted walls",
        "floor_material": "Light oak",
        "furniture_silhouette": "Understated forms with rounded edges and slim legs",
        "furniture_finishes": "Light wood, wool, cotton, ceramics",
        "decor_density": "Low to moderate",
        "botanical_species": "Soft, fresh greenery",
        "lighting_character": "Warm ambient glow with a natural daylight feel",
        "commentary": "This direction feels calm and welcoming through light materials and quiet comfort, without tipping into stark minimalism."
    },
    "Japandi": {
        "style_name": "Japandi Grounded Calm",
        "direction_summary": "A composed Japandi direction rooted in restraint, natural craft, and quietly grounded forms.",
        "color_story": "Warm beige, sand, pale oak, clay, charcoal accents",
        "wall_material": "Soft warm plaster",
        "floor_material": "Natural oak with a calm matte finish",
        "furniture_silhouette": "Low, simple, crafted, and grounded",
        "furniture_finishes": "Solid wood, linen, handmade ceramics, woven textures",
        "decor_density": "Minimal but not empty",
        "botanical_species": "Olive tree or sparse sculptural greenery",
        "lighting_character": "Soft daylight with a subtle paper-lantern warmth",
        "commentary": "This direction keeps the room serene and intentional, with warmth coming from material honesty and proportion rather than decoration."
    },
    "Midcentury Modern": {
        "style_name": "Midcentury Living Edit",
        "direction_summary": "A confident midcentury direction with clean geometry, iconic silhouettes, and optimistic warmth.",
        "color_story": "Walnut, mustard, olive, teal, warm neutrals",
        "wall_material": "Clean painted backdrop with selective feature emphasis",
        "floor_material": "Warm timber base",
        "furniture_silhouette": "Tapered legs, organic curves, classic midcentury forms",
        "furniture_finishes": "Walnut veneer, leather, brass accents, textured upholstery",
        "decor_density": "Moderate and edited",
        "botanical_species": "Graphic indoor plant",
        "lighting_character": "Warm, sculptural, and design-led",
        "commentary": "This direction leans on proportion and iconic shape language, keeping the room playful and polished rather than retro-themed."
    },
    "Modern Farmhouse": {
        "style_name": "Modern Farmhouse Balance",
        "direction_summary": "A relaxed modern farmhouse direction that blends familiarity, softness, and clean contemporary editing.",
        "color_story": "Warm white, soft grey, black accents, natural wood",
        "wall_material": "Painted wall or subtle panel detail",
        "floor_material": "Warm rustic wood tone",
        "furniture_silhouette": "Comfortable, generous, grounded forms",
        "furniture_finishes": "Linen-like upholstery, reclaimed wood, iron accents",
        "decor_density": "Moderate",
        "botanical_species": "Soft natural greenery",
        "lighting_character": "Warm ambient light with lantern-style character",
        "commentary": "This direction works when comfort stays elevated and edited, avoiding novelty farmhouse signals or overly distressed finishes."
    },
    "French Country": {
        "style_name": "French Country Grace",
        "direction_summary": "A romantic French country direction with gentle refinement, layered softness, and timeless warmth.",
        "color_story": "Cream, dusty blue, sage, muted lavender, warm neutrals",
        "wall_material": "Elegant painted wall with subtle decorative character",
        "floor_material": "Softly aged oak tone",
        "furniture_silhouette": "Curved legs, upholstered forms, graceful proportions",
        "furniture_finishes": "Distressed oak, linen, carved wood, wrought iron",
        "decor_density": "Moderate and layered",
        "botanical_species": "Soft, airy natural greenery",
        "lighting_character": "Warm chandeliers and wall-lit softness",
        "commentary": "This direction feels graceful and collected, as long as decoration stays refined and does not become too heavy or overly ornate."
    },
    "Hollywood Regency": {
        "style_name": "Hollywood Regency Glamour",
        "direction_summary": "A theatrical glam direction built on contrast, polish, symmetry, and confident statement pieces.",
        "color_story": "Black and white, emerald, metallic gold, bold accent tones",
        "wall_material": "High-contrast refined surface treatment",
        "floor_material": "Polished dark or dramatic neutral base",
        "furniture_silhouette": "Curved, sculptural, high-drama forms",
        "furniture_finishes": "Velvet, lacquer, brass, mirror",
        "decor_density": "Moderate but high-impact",
        "botanical_species": "Statement greenery with elegance",
        "lighting_character": "Reflective, dramatic, chandelier-led",
        "commentary": "This direction succeeds through confident editing and polish, where glamour feels intentional rather than crowded or costume-like."
    },
    "Coastal": {
        "style_name": "Coastal Quiet Breeze",
        "direction_summary": "A light coastal direction focused on openness, airiness, and relaxed natural textures.",
        "color_story": "White, sand, driftwood grey, soft blue",
        "wall_material": "Bright soft-white coastal wall finish",
        "floor_material": "Light weathered wood tone",
        "furniture_silhouette": "Relaxed, breathable, easy silhouettes",
        "furniture_finishes": "Rattan, jute, linen, weathered wood",
        "decor_density": "Low to moderate",
        "botanical_species": "Fresh airy greenery",
        "lighting_character": "Daylight-led with soft ambient support",
        "commentary": "This direction should feel effortless and breathable, staying away from overly literal nautical styling."
    },
}


def build_stage2_image_prompt(option: dict) -> str:
    return f"""
You are generating a photorealistic premium interior design catalogue render.

Use image_0 as the fixed room anchor.

ABSOLUTE CONSTRAINTS
- Keep the exact same room layout
- Keep the exact same architecture
- Keep the exact same camera angle
- Keep the exact same perspective
- Keep the exact same window placement
- Keep the exact same daylight direction
- Do not crop or reframe the scene
- Do not redesign the space itself
- Only change styling

STYLE DIRECTION
Style Name: {option.get("style_name", "")}
Direction Summary: {option.get("direction_summary", "")}
Color Story: {option.get("color_story", "")}
Wall Material: {option.get("wall_material", "")}
Floor Material: {option.get("floor_material", "")}
Furniture Silhouette: {option.get("furniture_silhouette", "")}
Furniture Finishes: {option.get("furniture_finishes", "")}
Decor Density: {option.get("decor_density", "")}
Botanical Species: {option.get("botanical_species", "")}
Lighting Character: {option.get("lighting_character", "")}

FURNITURE INVENTORY & PLACEMENT
- Sofa on left wall, facing the windows
- Console table centered on the back wall
- Two accent chairs plus coffee table in the center
- Premium rug
- Curated art on the back wall
- Style-appropriate botanical
- Architectural ceiling fixture plus sculptural floor lamp

QUALITY
- Photorealistic
- High-end editorial
- Interior design catalogue quality
- Premium materials
- Avoid sterile AI look
- Avoid plastic-looking finishes

Output one image only.
Do not return text.
""".strip()


def build_stage3_image_prompt(option: dict) -> str:
    return f"""
You are generating a refined photorealistic premium interior render.

Use image_0 as the selected direction anchor.

ABSOLUTE CONSTRAINTS
- Preserve the exact room shown in image_0
- Preserve the exact camera and composition shown in image_0
- Preserve the exact architecture shown in image_0
- Preserve the exact window placement shown in image_0
- Preserve the exact daylight direction shown in image_0
- Preserve the same furniture layout shown in image_0
- Preserve the same sofa shape and position shown in image_0
- Preserve the same chairs, table, decor objects, and styling layout shown in image_0
- Do not crop or reframe the scene
- Do not redesign the room
- Do not replace furniture pieces
- Only refine materials, surface tonality, and finish choices

REFINEMENT DIRECTION
Style Name: {option.get("style_name", "")}
Direction Summary: {option.get("direction_summary", "")}
Color Story: {option.get("color_story", "")}
Wall Material: {option.get("wall_material", "")}
Floor Material: {option.get("floor_material", "")}
Furniture Silhouette: {option.get("furniture_silhouette", "")}
Furniture Finishes: {option.get("furniture_finishes", "")}
Decor Density: {option.get("decor_density", "")}
Botanical Species: {option.get("botanical_species", "")}
Lighting Character: {option.get("lighting_character", "")}
Commentary: {option.get("commentary", "")}

MATERIAL EXPLORATION RULE
Explore variation only through:
- wood tone
- textile tone
- wall finish
- flooring material
- carpet tone and texture
- surface warmth or coolness
- lighting warmth

Do not change the composition.
Do not change the furniture inventory.
Do not change the styling objects.
The visual difference must come from materials and tonality only.

QUALITY
- Photorealistic
- High-end editorial
- Interior design catalogue quality
- Premium materials
- Avoid sterile AI look
- Avoid plastic-looking finishes

Output one image only.
Do not return text.
""".strip()


def build_direction_a_option(selected_style: str) -> dict:
    if selected_style not in STYLE_URL_MAP:
        raise ValueError(f"Style image URL not found for style: {selected_style}")

    style_copy = DIRECTION_A_COPY.get(selected_style)
    if not style_copy:
        raise ValueError(f"Direction A copy not found for style: {selected_style}")

    return {
        "id": "A",
        "style_name": style_copy["style_name"],
        "direction_summary": style_copy["direction_summary"],
        "color_story": style_copy["color_story"],
        "wall_material": style_copy["wall_material"],
        "floor_material": style_copy["floor_material"],
        "furniture_silhouette": style_copy["furniture_silhouette"],
        "furniture_finishes": style_copy["furniture_finishes"],
        "decor_density": style_copy["decor_density"],
        "botanical_species": style_copy["botanical_species"],
        "lighting_character": style_copy["lighting_character"],
        "commentary": style_copy["commentary"],
        "image_url": STYLE_URL_MAP[selected_style],
        "title": style_copy["style_name"],
    }


def normalize_stage_option(option: dict) -> dict:
    return {
        "id": option.get("id"),
        "style_name": option.get("style_name", ""),
        "direction_summary": option.get("direction_summary", ""),
        "color_story": option.get("color_story", ""),
        "wall_material": option.get("wall_material", ""),
        "floor_material": option.get("floor_material", ""),
        "furniture_silhouette": option.get("furniture_silhouette", ""),
        "furniture_finishes": option.get("furniture_finishes", ""),
        "decor_density": option.get("decor_density", ""),
        "botanical_species": option.get("botanical_species", ""),
        "lighting_character": option.get("lighting_character", ""),
        "commentary": option.get("commentary", ""),
        "title": option.get("style_name", option.get("id", "")),
    }


def validate_ids(options: list, expected_ids: set):
    seen = set()

    for option in options:
        option_id = option.get("id")
        if option_id not in expected_ids:
            raise ValueError(f"Invalid option id: {option_id}")
        if option_id in seen:
            raise ValueError(f"Duplicate option id: {option_id}")
        seen.add(option_id)

    if seen != expected_ids:
        raise ValueError(f"Expected ids {expected_ids}, got {seen}")


def build_refinement_anchor_option(selected_option: dict) -> dict:
    return {
        "id": "A",
        "style_name": selected_option.get("style_name", "Selected Direction"),
        "direction_summary": selected_option.get("direction_summary", ""),
        "color_story": selected_option.get("color_story", ""),
        "wall_material": selected_option.get("wall_material", ""),
        "floor_material": selected_option.get("floor_material", ""),
        "furniture_silhouette": selected_option.get("furniture_silhouette", ""),
        "furniture_finishes": selected_option.get("furniture_finishes", ""),
        "decor_density": selected_option.get("decor_density", ""),
        "botanical_species": selected_option.get("botanical_species", ""),
        "lighting_character": selected_option.get("lighting_character", ""),
        "commentary": selected_option.get("commentary", ""),
        "image_url": selected_option.get("image_url", ""),
        "title": selected_option.get("title", selected_option.get("style_name", "Selected Direction")),
    }


def build_refinement_option(base_option: dict, new_id: str, mode: str) -> dict:
    option = {
        "id": new_id,
        "style_name": base_option.get("style_name", ""),
        "direction_summary": base_option.get("direction_summary", ""),
        "color_story": base_option.get("color_story", ""),
        "wall_material": base_option.get("wall_material", ""),
        "floor_material": base_option.get("floor_material", ""),
        "furniture_silhouette": base_option.get("furniture_silhouette", ""),
        "furniture_finishes": base_option.get("furniture_finishes", ""),
        "decor_density": base_option.get("decor_density", ""),
        "botanical_species": base_option.get("botanical_species", ""),
        "lighting_character": base_option.get("lighting_character", ""),
        "commentary": base_option.get("commentary", ""),
        "title": base_option.get("title", base_option.get("style_name", "")),
    }

    base_title = base_option.get("title", base_option.get("style_name", "Selected Direction"))

    if mode == "cool":
        option["title"] = f"{base_title} — Cool Material Edit"
        option["style_name"] = option["title"]
        option["direction_summary"] = (
            f"{base_option.get('direction_summary', '')} "
            "Keep the exact same room and furniture, but shift the design toward a cooler, calmer material palette."
        )
        option["color_story"] = "Soft grey, pale ash wood, cool beige, muted stone"
        option["wall_material"] = "Soft cool-toned plaster or matte mineral paint"
        option["floor_material"] = "Light ash wood or pale cool-toned timber"
        option["furniture_finishes"] = "Cool neutral textiles, pale wood, soft stone, low-contrast finishes"
        option["lighting_character"] = "Balanced daylight with a slightly cooler and calmer feel"
        option["commentary"] = (
            "This refinement keeps the same design composition but shifts the room into a cooler, quieter material mood."
        )

    elif mode == "dark":
        option["title"] = f"{base_title} — Dark Material Edit"
        option["style_name"] = option["title"]
        option["direction_summary"] = (
            f"{base_option.get('direction_summary', '')} "
            "Keep the exact same room and furniture, but shift the design toward deeper woods, richer textiles, and a more atmospheric tonality."
        )
        option["color_story"] = "Dark walnut, deep taupe, warm brown, charcoal accents"
        option["wall_material"] = "Richer plaster or darker matte painted finish"
        option["floor_material"] = "Dark walnut or deeper grounded timber tone"
        option["furniture_finishes"] = "Richer woven textiles, deeper wood tones, grounded premium surfaces"
        option["lighting_character"] = "Warmer, moodier, more atmospheric light"
        option["commentary"] = (
            "This refinement preserves the same design direction while exploring a darker and more atmospheric material palette."
        )

    elif mode == "warm":
        option["title"] = f"{base_title} — Warm Material Edit"
        option["style_name"] = option["title"]
        option["direction_summary"] = (
            f"{base_option.get('direction_summary', '')} "
            "Keep the exact same room and furniture, but shift the design toward warmer woods, richer textiles, and a golden ambient light."
        )
        option["color_story"] = "Warm honey oak, amber, terracotta, soft cream"
        option["wall_material"] = "Warm plaster or softly tinted matte paint"
        option["floor_material"] = "Honey oak or warm-toned timber"
        option["furniture_finishes"] = "Warm woven textiles, honey wood, soft terracotta accents"
        option["lighting_character"] = "Warm golden ambient light with a soft, inviting glow"
        option["commentary"] = (
            "This refinement shifts the room into a warmer, more inviting material mood while preserving the same design composition."
        )

    else:
        raise ValueError(f"Unsupported refinement mode: {mode}")

    return option


def _generate_option_image(option, gemini_client, session_id, round_number, prompt_fn, direction_image_url=None):
    option_id = option["id"]
    print(f"[start_round] image generation start for {option_id}")
    image_prompt = prompt_fn(option)
    image_url = generate_image_with_gemini(
        gemini_client=gemini_client,
        session_id=session_id,
        round_number=round_number,
        option_id=option_id,
        prompt=image_prompt,
        style_image_path=None,
        direction_image_url=direction_image_url,
    )
    print(f"[start_round] image generation done for {option_id}: {image_url}")
    option["image_url"] = image_url
    return option


def start_round(session_id: str, round_number: int, db, gemini_client):
    print(f"[start_round] session_id={session_id} round_number={round_number}")

    doc_ref = db.collection("sessions").document(session_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise ValueError("Session not found")

    session = snap.to_dict() or {}

    rounds = session.get("rounds", {})
    if not isinstance(rounds, dict):
        rounds = {}

    if round_number == 1:
        style_commentary = session.get("style_commentary")
        style_selected = session.get("style_selected", [])

        if not style_commentary:
            raise ValueError("style_commentary not found in session")

        if not style_selected or not isinstance(style_selected, list):
            raise ValueError("style_selected not found in session")

        primary_style = style_selected[0]
        secondary_style = style_selected[1] if len(style_selected) > 1 else primary_style
        print(f"[start_round] primary_style={primary_style} secondary_style={secondary_style}")
        print("[start_round] entering round 1 flow")

        planner_result = plan_stage2_directions(
            gemini_client=gemini_client,
            primary_style=primary_style,
            secondary_style=secondary_style,
            style_commentary=style_commentary,
        )
        print("[start_round] planner done")

        planned_options = planner_result.get("options", [])
        if not isinstance(planned_options, list) or len(planned_options) != 4:
            raise ValueError("Stage 2 planner must return exactly 4 options")

        validate_ids(planned_options, {"B", "C", "E", "F"})
        print("[start_round] planner ids validated")

        option_a = build_direction_a_option(primary_style)
        option_d = {**build_direction_a_option(secondary_style), "id": "D"}
        options = [option_a]
        print("[start_round] direction A added")

        options_to_generate = {opt["id"]: normalize_stage_option(opt) for opt in planned_options}

        for oid in ("B", "C", "E", "F"):
            options.append(_generate_option_image(options_to_generate[oid], gemini_client, session_id, 1, build_stage2_image_prompt))
            doc_ref.set(
                {"rounds": {str(round_number): {"options": sorted(options, key=lambda x: x.get("id", ""))}}},
                merge=True,
            )
            print(f"[start_round] option {oid} written to firestore")

        options.append(option_d)
        options = sorted(options, key=lambda x: x.get("id", ""))
        print("[start_round] round 1 options sorted")

    elif round_number == 2:
        print("[start_round] entering round 2 flow")

        selected_option = session.get("last_selected_option")
        last_selected_round = session.get("last_selected_round")

        if not selected_option or not isinstance(selected_option, dict):
            raise ValueError("last_selected_option missing in session")

        if last_selected_round != 1:
            raise ValueError("Round 2 requires a selection from Round 1")

        anchor_image_url = selected_option.get("image_url")
        if not anchor_image_url:
            raise ValueError("Selected option image_url missing")

        options = [build_refinement_anchor_option(selected_option)]
        print("[start_round] refinement anchor A added")

        option_b = build_refinement_option(selected_option, "B", "cool")
        option_c = build_refinement_option(selected_option, "C", "dark")
        option_d = build_refinement_option(selected_option, "D", "warm")

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(_generate_option_image, opt, gemini_client, session_id, 2, build_stage3_image_prompt, anchor_image_url)
                for opt in [option_b, option_c, option_d]
            ]
            for future in futures:
                options.append(future.result())

        options = sorted(options, key=lambda x: x.get("id", ""))
        print("[start_round] round 2 options sorted")

    else:
        raise ValueError("Only round 1 and round 2 are supported")

    print("[start_round] writing round data to firestore")
    rounds[str(round_number)] = {
        "options": options
    }

    doc_ref.set(
        {
            "phase": 3,
            "current_round": round_number,
            "rounds": rounds,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    print("[start_round] firestore write complete")

    result = {
        "session_id": session_id,
        "phase": 3,
        "round": round_number,
        "options": options,
    }
    print("[start_round] returning success response")
    return result