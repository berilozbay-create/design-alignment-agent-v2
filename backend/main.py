from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os
import uuid
from google.cloud import firestore
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai.types import HttpOptions

from round_service import start_round
from selection_service import select_option
from final_brief_service import generate_final_brief

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {
        "ok": True,
        "project": "design-alignment-agent",
        "timestamp": datetime.utcnow().isoformat()
    }


STYLE_NAMES = [
    "Minimalist",
    "Maximalist",
    "Industrial",
    "Scandinavian",
    "Japandi",
    "Midcentury Modern",
    "Modern Farmhouse",
    "French Country",
    "Hollywood Regency",
    "Coastal",
]


STYLE_BLURBS = {
    "Minimalist": "Clean, restrained interiors with simple forms and very low visual noise.",
    "Maximalist": "Layered, expressive interiors with bold contrast, personality, and richness.",
    "Industrial": "Raw, urban interiors using metal, concrete, darker tones, and exposed character.",
    "Scandinavian": "Bright, calm interiors with light woods, soft textiles, and functional simplicity.",
    "Japandi": "Minimal Japanese calm blended with Scandinavian warmth and natural materials.",
    "Midcentury Modern": "Retro-modern interiors with clean lines, warm woods, and sculptural furniture.",
    "Modern Farmhouse": "Comfortable, welcoming interiors with rustic warmth and modern clarity.",
    "French Country": "Rustic elegance with antique character, soft patina, and warm layered textiles.",
    "Hollywood Regency": "Bold glamour with luxurious finishes, contrast, and statement lighting.",
    "Coastal": "Light, airy interiors inspired by seaside homes with relaxed textures and fresh tones.",
}


STYLE_IMAGE_MAP = {
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


AXIS_KEYS = [
    "sofa_profile",
    "coffee_table_character",
    "wall_treatment",
    "floor_finish",
    "material_temperature",
    "palette_strategy",
    "decor_density",
    "lighting_fixture",
    "greenery",
    "wall_art_character",
]


def get_firestore_client():
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
    return firestore.Client(project=project) if project else firestore.Client()


db = get_firestore_client()


def get_genai_client():
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT") or "design-alignment-agent"

    return genai.Client(
        vertexai=True,
        project=project,
        http_options=HttpOptions(api_version="v1"),
    )


def default_state():
    axes = {
        key: {
            "value": None,
            "confidence": 0.0,
            "status": "flexible"
        }
        for key in AXIS_KEYS
    }

    return {
        "phase": 1,
        "style_selected": [],
        "style_commentary": None,
        "axes": axes,
        "history": [],
        "clarification_pending": False,
        "schema_version": 1,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }


class SelectStyleRequest(BaseModel):
    styles: List[str] = Field(..., min_length=1, max_length=2)


class RoundStartRequest(BaseModel):
    round: int
    signals: Optional[dict] = None


class FeedbackRequest(BaseModel):
    comment: str


def _validate_styles(styles: List[str]) -> List[str]:
    cleaned = [s.strip() for s in styles]

    unique = []
    for s in cleaned:
        if s not in unique:
            unique.append(s)

    if len(unique) < 1 or len(unique) > 2:
        raise ValueError("You must select 1 or 2 unique styles.")

    invalid = [s for s in unique if s not in STYLE_NAMES]
    if invalid:
        raise ValueError(f"Invalid style(s): {invalid}. Must be one of STYLE_NAMES.")

    return unique


def generate_style_commentary(styles: List[str]) -> dict:
    client = get_genai_client()
    style_text = ", ".join(styles)

    prompt = f"""
You are an interior design mediator helping interpret early style preferences for a living room.

Selected styles: {style_text}

Return exactly 4 sections using this format:

VIBE:
<2-3 sentences>

KEY_RULES:
- bullet
- bullet
- bullet
- bullet

WATCH_OUTS:
- bullet
- bullet
- bullet

NEXT_EXPLORATION:
- bullet
- bullet
- bullet

Keep it practical, visually specific, and concise.
Do not use markdown headings other than the exact labels above.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = (getattr(response, "text", "") or "").strip()

    return {
        "selected_styles": styles,
        "raw_text": text,
        "generated_at": datetime.utcnow().isoformat()
    }



@app.get("/demo", response_class=HTMLResponse)
def demo_page():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Design Alignment Agent</title>
    <style>
        :root {
            --bg: #f4f3ef;
            --panel: #ffffff;
            --line: #d8d4ca;
            --muted: #6a655c;
            --text: #222018;
            --soft: #f8f7f3;
            --accent: #1f1d17;
            --accent-soft: #ece8de;
            --selected: #111111;
            --shadow: 0 8px 24px rgba(0,0,0,0.06);
            --success-bg: #f1efe7;
            --success-line: #bdb39e;
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: Arial, sans-serif;
            line-height: 1.45;
        }

        .page {
            max-width: 1240px;
            margin: 0 auto;
            padding: 28px 20px 48px;
        }

        .hero {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: var(--shadow);
            padding: 28px;
            margin-bottom: 18px;
        }

        .eyebrow {
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 10px;
        }

        h1 {
            margin: 0 0 12px 0;
            font-size: 34px;
            line-height: 1.1;
        }

        .intro {
            max-width: 860px;
            color: #3f3a31;
            margin-bottom: 18px;
        }

        .cap-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(260px, 1fr));
            gap: 12px;
            margin-top: 18px;
        }

        .cap-card {
            background: var(--soft);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 14px;
        }

        .cap-card strong {
            display: block;
            margin-bottom: 4px;
        }

        .tracker {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin: 18px 0 24px;
        }

        .tracker-step {
            background: #ebe7dc;
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px;
            font-size: 14px;
            color: #5a5448;
        }

        .tracker-step.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }

        .tracker-step.done {
            background: var(--accent-soft);
            color: var(--text);
            border-color: #cfc7b7;
        }

        .stage {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: var(--shadow);
            padding: 24px;
            margin-bottom: 18px;
        }

        .stage.hidden {
            display: none;
        }

        .stage h2 {
            margin: 0 0 6px 0;
            font-size: 24px;
        }

        .stage-sub {
            color: var(--muted);
            margin-bottom: 8px;
        }

        .cap-label {
            display: inline-block;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #5f584b;
            background: #f1ede3;
            border: 1px solid #d8d1c1;
            padding: 6px 10px;
            border-radius: 999px;
            margin-bottom: 14px;
        }

        .same-room-note {
            background: #f8f5ec;
            border: 1px solid #e2dbc9;
            color: #4f493d;
            border-radius: 12px;
            padding: 10px 12px;
            margin: 12px 0 18px;
            font-size: 14px;
            font-weight: bold;
        }

        .transition-banner {
            display: none;
            background: var(--success-bg);
            border: 1px solid var(--success-line);
            border-radius: 16px;
            padding: 20px;
            margin-top: 18px;
        }

        .transition-banner.show {
            display: block;
        }

        .transition-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 6px;
        }

        .transition-text {
            color: #4d473d;
            font-size: 16px;
        }

        .inline-banner {
            display: none;
            background: var(--success-bg);
            border: 1px solid var(--success-line);
            border-radius: 14px;
            padding: 16px;
            margin: 14px 0 0;
        }

        .inline-banner.show {
            display: block;
        }

        .inline-banner-title {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 4px;
        }

        .inline-banner-text {
            color: #4d473d;
            font-size: 15px;
        }

        .style-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(280px, 1fr));
            gap: 16px;
        }

        .card-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(220px, 1fr));
            gap: 16px;
        }

        .card {
            position: relative;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: #fff;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease, opacity 0.12s ease;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 22px rgba(0,0,0,0.08);
        }

        .card.selected {
            border: 3px solid var(--selected);
            box-shadow: 0 10px 24px rgba(0,0,0,0.10);
        }

        .card.locked {
            cursor: default;
        }

        .card.locked:hover {
            transform: none;
        }

        .card.dimmed {
            opacity: 0.45;
            pointer-events: none;
        }

        .selected-badge {
            position: absolute;
            top: 10px;
            right: 10px;
            background: #111;
            color: white;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
            z-index: 2;
        }

        .option-letter-badge {
            position: absolute;
            top: 8px;
            left: 8px;
            background: rgba(0, 0, 0, 0.55);
            color: #f5f0e8;
            font-weight: bold;
            font-size: 13px;
            padding: 4px 9px;
            border-radius: 6px;
            z-index: 10;
        }

        .card-media {
            aspect-ratio: 16 / 10;
            background: #e9e5db;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #776f60;
            font-size: 14px;
            overflow: hidden;
        }

        .card-media img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .spinner {
            width: 18px;
            height: 18px;
            border: 3px solid #d8d4ca;
            border-top-color: #2a271f;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            flex-shrink: 0;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .card-body {
            padding: 14px;
        }

        .card-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 6px;
        }

        .card-text {
            color: #554f45;
            font-size: 14px;
        }

        .loader {
            background: #faf8f2;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 20px;
            margin-top: 14px;
        }

        .loader.hidden {
            display: none;
        }

        .loader-title {
            font-weight: bold;
            margin-bottom: 10px;
        }

        .progress-row {
            display: flex;
            gap: 8px;
            margin: 10px 0 8px;
        }

        .progress-seg {
            height: 10px;
            flex: 1;
            border-radius: 999px;
            background: #ddd7ca;
        }

        .progress-seg.done {
            background: #2a271f;
        }

        .small {
            font-size: 13px;
            color: var(--muted);
        }

        .insight-box,
        .brief-box,
        .raw-box {
            white-space: pre-wrap;
            background: #faf9f5;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 16px;
            margin-top: 14px;
            overflow-x: auto;
        }

        .final-layout {
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 18px;
        }

        .button-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 16px;
        }

        button, .link-button {
            border: 1px solid var(--accent);
            background: var(--accent);
            color: white;
            border-radius: 12px;
            padding: 12px 16px;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }

        button:hover, .link-button:hover {
            background: #343027;
        }

        button.secondary, .link-button.secondary {
            background: white;
            color: var(--accent);
        }

        .status-line {
            font-size: 14px;
            color: var(--muted);
            margin-top: 10px;
        }

        .brief-section {
            margin-bottom: 18px;
        }

        .brief-section:last-child {
            margin-bottom: 0;
        }

        .brief-heading {
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #6a655c;
            margin-bottom: 8px;
        }

        .brief-title {
            font-size: 24px;
            font-weight: bold;
            line-height: 1.2;
        }

        .brief-list {
            margin: 0;
            padding-left: 20px;
        }

        .brief-list li {
            margin-bottom: 6px;
        }

        .axis-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(120px, 1fr));
            gap: 8px 14px;
        }

        .axis-item {
            padding: 8px 10px;
            background: #f5f3ed;
            border: 1px solid #dfdacd;
            border-radius: 10px;
            font-size: 14px;
        }

        .hero-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 12px;
        }

        .hero-clickable {
            cursor: pointer;
        }

        .hero-clickable:hover {
            opacity: 0.96;
        }

        @media (max-width: 900px) {
            .cap-grid,
            .tracker,
            .style-grid,
            .final-layout,
            .axis-grid {
                grid-template-columns: 1fr;
            }

            .card-grid {
                grid-template-columns: 1fr;
            }
        }
        .feedback-section {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: var(--shadow);
            padding: 24px;
            margin-top: 18px;
        }

        .feedback-heading {
            font-size: 22px;
            font-weight: bold;
            margin: 0 0 8px 0;
        }

        .feedback-subtext {
            color: var(--muted);
            font-size: 14px;
            margin-bottom: 14px;
            line-height: 1.5;
        }

        .feedback-textarea {
            width: 100%;
            min-height: 90px;
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px 14px;
            font-size: 15px;
            font-family: inherit;
            background: var(--soft);
            color: var(--text);
            resize: vertical;
            box-sizing: border-box;
        }

        .feedback-textarea:focus {
            outline: none;
            border-color: var(--accent);
        }

        .feedback-actions {
            display: flex;
            gap: 10px;
            margin-top: 12px;
            align-items: center;
        }

        .mic-button {
            border: 1px solid var(--line);
            background: var(--soft);
            color: var(--text);
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 18px;
            cursor: pointer;
            line-height: 1;
        }

        .mic-button.recording {
            background: #ffe5e5;
            border-color: #e05555;
            animation: pulse 1s ease-in-out infinite;
        }

        .feedback-response {
            margin-top: 16px;
            background: var(--soft);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 16px;
            white-space: pre-wrap;
            font-size: 15px;
            line-height: 1.55;
        }
    </style>
</head>
<body>
    <div class="page">
        <section class="hero">
            <div class="eyebrow">Creative Storytelling Demo</div>
            <h1>Design Alignment Agent</h1>
            <div class="intro">
                A conversational agent for early-stage interior design alignment.
                Many clients struggle to describe what they want in words, while architects often receive vague
                or contradictory taste signals that lead to repeated redesign cycles.
                <br><br>
                Design Mediator helps translate visual taste into a clear design direction.
                Instead of asking users to describe preferences verbally, the system lets them react to visual options.
                Through a small number of selections, the agent infers aesthetic preference and synthesizes a coherent final proposal.
            </div>

            <div class="cap-grid">
                <div class="cap-card">
                    <strong>Multimodal reasoning</strong>
                    Interpreting visual style references and architectural context.
                </div>
                <div class="cap-card">
                    <strong>Taste inference</strong>
                    Understanding aesthetic preference through visual selections.
                </div>
                <div class="cap-card">
                    <strong>Design exploration</strong>
                    Generating multiple stylistic interpretations of the same space.
                </div>
                <div class="cap-card">
                    <strong>Design synthesis</strong>
                    Producing a final design proposal from user signals.
                </div>
            </div>
        </section>

        <div class="tracker" id="tracker">
            <div class="tracker-step active" id="track-1">1. Style Discovery</div>
            <div class="tracker-step" id="track-2">2. Direction Exploration</div>
            <div class="tracker-step" id="track-3">3. Taste Refinement</div>
            <div class="tracker-step" id="track-4">4. Final Proposal</div>
        </div>

        <section class="stage" id="stage-1">
            <div class="cap-label">Design Mediator demonstrates multimodal reasoning</div>
            <h2>Style Discovery</h2>
            <div class="stage-sub">
                Select your primary and secondary design styles. Each option shows the same room rendered in a different interior style.
            </div>
            <div class="same-room-note">Same room. Same lighting. Same camera. Focus only on style.</div>

            <div class="style-grid" id="styleGrid"></div>

            <div class="transition-banner" id="styleTransition">
                <div class="transition-title" id="styleTransitionTitle">Style selected</div>
                <div class="transition-text" id="styleTransitionText">Design Alignment Agent is now exploring directions across both styles…</div>
            </div>

            <div class="status-line" id="styleStatus">Choose your primary style to begin.</div>
        </section>

        <section class="stage hidden" id="stage-2">
            <div class="cap-label">Design Mediator demonstrates design exploration</div>
            <h2>Direction Exploration</h2>
            <div class="stage-sub">
                Explore six directions — pure styles, distinct variations, and blended interpretations across your two chosen styles.
            </div>
            <div class="same-room-note">Same room. Same lighting. Same camera. Focus only on style.</div>

            <div class="loader hidden" id="loader-stage-2">
                <div class="loader-title">Design Alignment Agent is preparing six direction cards across both styles…</div>
                <div class="progress-row">
                    <div class="progress-seg" id="s2p1"></div>
                    <div class="progress-seg" id="s2p2"></div>
                    <div class="progress-seg" id="s2p3"></div>
                    <div class="progress-seg" id="s2p4"></div>
                    <div class="progress-seg" id="s2p5"></div>
                    <div class="progress-seg" id="s2p6"></div>
                </div>
                <div class="small" id="loader-stage-2-text">Preparing design directions…</div>
            </div>

            <div class="card-grid" id="round1Grid"></div>

            <div class="feedback-section" id="round1Feedback" style="display:none;">
                <h3 class="feedback-heading">What caught your eye?</h3>
                <div class="feedback-subtext">Tell us what you liked or didn’t like across the cards. For example: “I loved the walls from B and the plants from E, but the sofa from A felt too heavy.”</div>
                <textarea class="feedback-textarea" id="round1FeedbackText" placeholder="Share your thoughts about the designs..."></textarea>
                <div class="feedback-actions">
                    <button class="mic-button" id="round1MicBtn" title="Voice input" onclick="toggleMic()">&#127908;</button>
                    <button onclick="submitRound1Feedback()">Generate my refined options →</button>
                </div>
                <div class="feedback-response" id="round1FeedbackResponse" style="display:none;"></div>
            </div>

            <div class="inline-banner" id="round1Transition">
                <div class="inline-banner-title" id="round1TransitionTitle">Direction selected</div>
                <div class="inline-banner-text" id="round1TransitionText">Design Mediator is now refining this direction. This may take a little time.</div>
            </div>

            <div class="raw-box" id="round1Raw" style="display:none;"></div>
        </section>

        <section class="stage hidden" id="stage-2b">
            <div class="cap-label">Design Mediator demonstrates taste inference</div>
            <h2>Preference Insight</h2>
            <div class="stage-sub">
                Your selection reveals the kind of atmosphere, material balance, and decorative character you prefer.
            </div>
            <div class="insight-box" id="insightBox">Waiting for your selection…</div>
        </section>

        <section class="stage hidden" id="stage-3">
            <div class="cap-label">Design Mediator demonstrates guided exploration</div>
            <h2>Taste Refinement</h2>
            <div class="stage-sub">
                Based on your preference, Design Mediator refines the direction into three closer options.
                Choose the version that feels most complete.
            </div>
            <div class="same-room-note">Same room. Same lighting. Same camera. Focus only on style.</div>

            <div class="loader hidden" id="loader-stage-3">
                <div class="loader-title">Design Alignment Agent is refining your preferred direction…</div>
                <div style="display:flex;align-items:center;gap:10px;margin:10px 0;">
                    <div class="spinner"></div>
                    <div class="small" id="loader-stage-3-text">Generating refined variations… this takes about 2 minutes</div>
                </div>
            </div>

            <div class="card-grid" id="round2Grid"></div>

            <div class="inline-banner" id="round2Transition">
                <div class="inline-banner-title" id="round2TransitionTitle">Refined direction selected</div>
                <div class="inline-banner-text" id="round2TransitionText">Design Mediator is now synthesizing your final proposal. This may take a little time.</div>
            </div>

            <div class="raw-box" id="round2Raw" style="display:none;"></div>
        </section>

        <section class="stage hidden" id="stage-4">
            <div class="cap-label">Design Mediator demonstrates design synthesis</div>
            <h2>Final Design Proposal</h2>
            <div class="stage-sub">
                Based on your visual selections, Design Mediator synthesizes a final proposal.
            </div>

            <div class="loader hidden" id="loader-stage-4">
                <div class="loader-title">Design Mediator is synthesizing your final design proposal…</div>
                <div class="progress-row">
                    <div class="progress-seg" id="s4p1"></div>
                    <div class="progress-seg" id="s4p2"></div>
                    <div class="progress-seg" id="s4p3"></div>
                </div>
                <div class="small" id="loader-stage-4-text">Preparing final brief…</div>
            </div>

            <div class="final-layout">
                <div>
                    <div class="card-media" id="finalHeroBox">Final hero image will appear here when available.</div>
                    <div class="hero-actions" id="heroActions" style="display:none;">
                        <a class="link-button secondary" id="openFullBtn" href="#" target="_blank" rel="noopener noreferrer">Open full size</a>
                        <a class="link-button secondary" id="downloadBtn" href="#" download="design-mediator-final.png">Download image</a>
                    </div>
                </div>
                <div>
                    <div class="brief-box" id="briefBox">Final brief not generated yet.</div>
                </div>
            </div>
        </section>

        <section class="stage">
            <h2>Debug</h2>
            <div class="stage-sub">Use these only if needed while testing.</div>
            <div class="button-row">
                <button class="secondary" onclick="toggleRaw('round1Raw')">Toggle Round 1 JSON</button>
                <button class="secondary" onclick="toggleRaw('round2Raw')">Toggle Round 2 JSON</button>
                <button class="secondary" onclick="restartDemo()">Restart Demo</button>
            </div>
        </section>
    </div>

    <script>
        const STYLE_NAMES = [
            "Minimalist",
            "Maximalist",
            "Industrial",
            "Scandinavian",
            "Japandi",
            "Midcentury Modern",
            "Modern Farmhouse",
            "French Country",
            "Hollywood Regency",
            "Coastal"
        ];

        const STYLE_BLURBS = {
            "Minimalist": "Clean, restrained interiors with simple forms and very low visual noise.",
            "Maximalist": "Layered, expressive interiors with bold contrast, personality, and richness.",
            "Industrial": "Raw, urban interiors using metal, concrete, darker tones, and exposed character.",
            "Scandinavian": "Bright, calm interiors with light woods, soft textiles, and functional simplicity.",
            "Japandi": "Minimal Japanese calm blended with Scandinavian warmth and natural materials.",
            "Midcentury Modern": "Retro-modern interiors with clean lines, warm woods, and sculptural furniture.",
            "Modern Farmhouse": "Comfortable, welcoming interiors with rustic warmth and modern clarity.",
            "French Country": "Rustic elegance with antique character, soft patina, and warm layered textiles.",
            "Hollywood Regency": "Bold glamour with luxurious finishes, contrast, and statement lighting.",
            "Coastal": "Light, airy interiors inspired by seaside homes with relaxed textures and fresh tones."
        };

        const STYLE_IMAGE_MAP = {
            "Minimalist": "/static/styles/minimalist.png",
            "Maximalist": "/static/styles/maximalist.png",
            "Industrial": "/static/styles/industrial.png",
            "Scandinavian": "/static/styles/scandinavian.png",
            "Japandi": "/static/styles/japandi.png",
            "Midcentury Modern": "/static/styles/midcentury_modern.png",
            "Modern Farmhouse": "/static/styles/modern_farmhouse.png",
            "French Country": "/static/styles/french_country.png",
            "Hollywood Regency": "/static/styles/hollywood_regency.png",
            "Coastal": "/static/styles/coastal.png"
        };

        let sessionId = null;
        let selectedStylePrimary = null;
        let selectedStyleSecondary = null;
        let round1Data = null;
        let round2Data = null;
        let selectedRound1Id = null;
        let selectedRound2Id = null;
        let styleLocked = false;
        let round1Locked = false;
        let round2Locked = false;
        let finalHeroUrl = null;

        function setTracker(active) {
            for (let i = 1; i <= 4; i++) {
                const el = document.getElementById(`track-${i}`);
                el.classList.remove("active");
                el.classList.remove("done");

                if (i < active) el.classList.add("done");
                if (i === active) el.classList.add("active");
            }
        }

        function showStage(id) {
            document.getElementById(id).classList.remove("hidden");
        }

        function hideStage(id) {
            document.getElementById(id).classList.add("hidden");
        }

        function toggleRaw(id) {
            const el = document.getElementById(id);
            el.style.display = el.style.display === "none" ? "block" : "none";
        }

        function restartDemo() {
            sessionId = null;
            selectedStylePrimary = null;
            selectedStyleSecondary = null;
            round1Data = null;
            round2Data = null;
            selectedRound1Id = null;
            selectedRound2Id = null;
            styleLocked = false;
            round1Locked = false;
            round2Locked = false;
            finalHeroUrl = null;

            document.getElementById("styleStatus").textContent = "Choose your primary style to begin.";
            document.getElementById("round1Grid").innerHTML = "";
            document.getElementById("round2Grid").innerHTML = "";
            document.getElementById("round1Raw").textContent = "";
            document.getElementById("round2Raw").textContent = "";
            document.getElementById("insightBox").textContent = "Waiting for your selection…";
            document.getElementById("briefBox").textContent = "Final brief not generated yet.";
            document.getElementById("finalHeroBox").innerHTML = "Final hero image will appear here when available.";
            document.getElementById("styleTransition").classList.remove("show");
            document.getElementById("round1Transition").classList.remove("show");
            document.getElementById("round2Transition").classList.remove("show");
            document.getElementById("heroActions").style.display = "none";
            document.getElementById("openFullBtn").href = "#";
            document.getElementById("downloadBtn").href = "#";

            hideStage("stage-2");
            hideStage("stage-2b");
            hideStage("stage-3");
            hideStage("stage-4");

            renderStyleGrid();
            setTracker(1);
        }

        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        function setProgress(prefix, current, total, labelText) {
            for (let i = 1; i <= total; i++) {
                const seg = document.getElementById(`${prefix}${i}`);
                if (!seg) continue;
                seg.classList.toggle("done", i <= current);
            }
            const textEl = document.getElementById(`loader-stage-${prefix[1]}-text`);
            if (textEl && labelText) textEl.textContent = labelText;
        }

        function safeText(value, fallback = "") {
            if (value === null || value === undefined) return fallback;
            return String(value);
        }

        function extractImageUrl(obj) {
            if (!obj || typeof obj !== "object") return null;

            const directKeys = [
                "image_url", "imageUrl", "url", "image", "image_uri", "imageUri",
                "render_url", "renderUrl", "hero_image_url", "heroImageUrl"
            ];

            for (const key of directKeys) {
                if (typeof obj[key] === "string" && obj[key].trim()) return obj[key];
            }

            if (obj.image && typeof obj.image === "object") {
                for (const k of ["url", "image_url", "uri"]) {
                    if (typeof obj.image[k] === "string" && obj.image[k].trim()) return obj.image[k];
                }
            }

            if (Array.isArray(obj.images)) {
                for (const item of obj.images) {
                    const found = extractImageUrl(item);
                    if (found) return found;
                }
            }

            for (const key of Object.keys(obj)) {
                const value = obj[key];
                if (value && typeof value === "object") {
                    const found = extractImageUrl(value);
                    if (found) return found;
                }
            }

            return null;
        }

        function renderStyleGrid() {
            const grid = document.getElementById("styleGrid");
            grid.innerHTML = "";

            STYLE_NAMES.forEach(style => {
                const card = document.createElement("div");

                const isPrimary = style === selectedStylePrimary;
                const isSecondary = style === selectedStyleSecondary;

                let className = "card";
                if (isPrimary || isSecondary) className += " selected";
                if (styleLocked) className += " locked";
                if (styleLocked && !isPrimary && !isSecondary) className += " dimmed";
                card.className = className;

                if (!styleLocked) {
                    card.onclick = () => selectStyleCard(style);
                }

                const imgSrc = STYLE_IMAGE_MAP[style] || "";
                const mediaHtml = imgSrc
                    ? `<img src="${imgSrc}" alt="${style}">`
                    : `<div>${style}</div>`;

                let badgeHtml = "";
                if (isPrimary) badgeHtml = `<div class="selected-badge">PRIMARY</div>`;
                else if (isSecondary) badgeHtml = `<div class="selected-badge">SECONDARY</div>`;

                card.innerHTML = `
                    ${badgeHtml}
                    <div class="card-media">${mediaHtml}</div>
                    <div class="card-body">
                        <div class="card-title">${style}</div>
                        <div class="card-text">${STYLE_BLURBS[style] || ""}</div>
                    </div>
                `;

                grid.appendChild(card);
            });
        }

        async function ensureSession() {
            if (sessionId) return sessionId;

            const res = await fetch("/session/start", { method: "POST" });
            const data = await res.json();
            sessionId = data.session_id || null;
            return sessionId;
        }

        async function selectStyleCard(style) {
            if (styleLocked) return;

            if (!selectedStylePrimary) {
                selectedStylePrimary = style;
                document.getElementById("styleStatus").textContent = "Primary style selected. Now choose a secondary style.";
                renderStyleGrid();
                return;
            }

            if (style === selectedStylePrimary) return;

            selectedStyleSecondary = style;
            styleLocked = true;
            renderStyleGrid();

            // Show stage-2 and placeholder grid immediately
            showStage("stage-2");
            setTracker(2);

            try {
                document.getElementById("styleStatus").textContent = "";
                document.getElementById("styleTransitionTitle").textContent = `Styles selected: ${selectedStylePrimary} & ${selectedStyleSecondary}`;
                document.getElementById("styleTransitionText").textContent = "Design Mediator is now exploring directions within these styles…";
                document.getElementById("styleTransition").classList.add("show");

                await ensureSession();

                const res = await fetch(`/session/${sessionId}/select-style`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ styles: [selectedStylePrimary, selectedStyleSecondary] })
                });

                const data = await res.json();

                if (data.error) {
                    document.getElementById("styleStatus").textContent = "Error selecting style: " + JSON.stringify(data, null, 2);
                    styleLocked = false;
                    selectedStyleSecondary = null;
                    renderStyleGrid();
                    return;
                }

                await generateRound1();
            } catch (err) {
                document.getElementById("styleStatus").textContent = "Error selecting style: " + err;
                styleLocked = false;
                selectedStyleSecondary = null;
                renderStyleGrid();
            }
        }

        async function generateRound1() {
            fetch(`/session/${sessionId}/round/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ round: 1 })
            });

            const loader = document.getElementById("loader-stage-2");
            const grid = document.getElementById("round1Grid");
            const raw = document.getElementById("round1Raw");

            grid.innerHTML = "";
            raw.textContent = "";
            loader.classList.remove("hidden");
            setProgress("s2p", 0, 6, "Kicking off generation\u2026");

            function fillCard(id, option) {
                const card = document.getElementById(`r1card-${id}`);
                if (!card) return;
                const imageUrl = extractImageUrl(option) || "";
                const title = safeText(option.title || option.style_name, `Option ${id}`);
                const desc = safeText(option.commentary || option.direction || option.description, "");
                card.innerHTML = `
                    <div class="option-letter-badge">${id}</div>
                    <div class="card-media">
                        <img src="${imageUrl}" alt="${title}" style="opacity:0;transition:opacity 0.6s;" onload="this.style.opacity=1">
                    </div>
                    <div class="card-body">
                        <div class="card-title">${title}</div>
                        <div class="card-text">${desc}</div>
                    </div>
                `;
                card.style.opacity = "0";
                card.style.transition = "opacity 0.4s ease";
                requestAnimationFrame(() => requestAnimationFrame(() => { card.style.opacity = "1"; }));
            }

            const ALL_IDS = ["A", "B", "C", "D", "E", "F"];
            for (const id of ALL_IDS) {
                const card = document.createElement("div");
                card.className = "card";
                card.id = `r1card-${id}`;
                card.innerHTML = `
                    <div class="option-letter-badge">${id}</div>
                    <div class="card-media" style="animation:pulse 1.5s ease-in-out infinite;"></div>
                    <div class="card-body">
                        <div class="card-title">Option ${id}</div>
                        <div class="card-text">Designing…</div>
                    </div>
                `;
                grid.appendChild(card);
            }


            try {
                await sleep(5000);
                const optionA = { id: "A", title: selectedStylePrimary, style_name: selectedStylePrimary, image_url: STYLE_IMAGE_MAP[selectedStylePrimary] || "", commentary: STYLE_BLURBS[selectedStylePrimary] || "" };
                fillCard("A", optionA);
                setProgress("s2p", 1, 6, "Option A ready\u2026");

                await sleep(25000);
                const optionD = { id: "D", title: selectedStyleSecondary, style_name: selectedStyleSecondary, image_url: STYLE_IMAGE_MAP[selectedStyleSecondary] || "", commentary: STYLE_BLURBS[selectedStyleSecondary] || "" };
                fillCard("D", optionD);
                setProgress("s2p", 2, 6, "Option D ready\u2026");

                const filled = { A: optionA, D: optionD };
                let filledCount = 2;

                await new Promise((resolve, reject) => {
                    let pollCount = 0;
                    let polling = false;
                    const intervalId = setInterval(async () => {
                        if (polling) return; polling = true;
                        if (++pollCount > 75) { polling = false; clearInterval(intervalId); reject(new Error("Polling timed out")); return; }
                        try {
                            const res = await fetch(`/session/${sessionId}/round/poll`);
                            const data = await res.json();
                            if (data.error) { polling = false; return; }
                            for (const option of (data.options || [])) {
                                const oid = option.id;
                                if (filled[oid] || !option.image_url) continue;
                                filled[oid] = option;
                                fillCard(oid, option);
                                setProgress("s2p", ++filledCount, 6, `Option ${oid} ready\u2026`);
                            }
                            if (data.complete && filledCount >= 6) { clearInterval(intervalId); resolve(filled); }
                        } catch (e) { /* keep polling */ } finally { polling = false; }
                    }, 8000);
                });

                round1Data = { session_id: sessionId, phase: 3, round: 1, options: ALL_IDS.map(id => filled[id]).filter(Boolean) };
                raw.textContent = JSON.stringify(round1Data, null, 2);
                setProgress("s2p", 6, 6, "All directions ready.");
                renderRoundGrid("round1Grid", round1Data, 1);
                document.getElementById("round1Feedback").style.display = "block";
            } catch (err) {
                grid.innerHTML = `<div class="brief-box">Error generating directions: ${safeText(err)}</div>`;
            } finally {
                loader.classList.add("hidden");
            }
        }
        async function generateRound2(signals) {
            showStage("stage-3");
            setTracker(3);

            const loader = document.getElementById("loader-stage-3");
            const grid = document.getElementById("round2Grid");
            const raw = document.getElementById("round2Raw");

            grid.innerHTML = "";
            raw.textContent = "";
            loader.classList.remove("hidden");

            fetch(`/session/${sessionId}/round/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ round: 2, signals: signals || null })
            });

            const ALL_IDS = ["1", "2", "3"];
            for (const id of ALL_IDS) {
                const card = document.createElement("div");
                card.className = "card";
                card.id = `r2card-${id}`;
                card.innerHTML = `
                    <div class="card-media" style="animation:pulse 1.5s ease-in-out infinite;"></div>
                    <div class="card-body">
                        <div class="card-title">Designing\u2026</div>
                        <div class="card-text"></div>
                    </div>
                `;
                grid.appendChild(card);
            }

            function fillCard(id, option) {
                const card = document.getElementById(`r2card-${id}`);
                if (!card) return;
                const imageUrl = extractImageUrl(option) || "";
                const title = safeText(option.title || option.style_name, `Option ${id}`);
                const desc = safeText(option.commentary || option.direction || option.description, "");
                card.innerHTML = `
                    <div class="card-media">
                        <img src="${imageUrl}" alt="${title}" style="opacity:0;transition:opacity 0.6s;" onload="this.style.opacity=1">
                    </div>
                    <div class="card-body">
                        <div class="card-title">${title}</div>
                        <div class="card-text">${desc}</div>
                    </div>
                `;
                card.style.opacity = "0";
                card.style.transition = "opacity 0.4s ease";
                requestAnimationFrame(() => requestAnimationFrame(() => { card.style.opacity = "1"; }));
            }

            try {
                const filled = {};
                let filledCount = 0;

                await new Promise((resolve, reject) => {
                    let pollCount = 0;
                    let polling = false;
                    const intervalId = setInterval(async () => {
                        if (polling) return; polling = true;
                        if (++pollCount > 75) { polling = false; clearInterval(intervalId); reject(new Error("Polling timed out")); return; }
                        try {
                            const res = await fetch(`/session/${sessionId}/round/poll?round=2`);
                            const data = await res.json();
                            if (data.error) { polling = false; return; }
                            console.log('[round2 poll]', JSON.stringify(data));
                            for (const option of (data.options || [])) {
                                const oid = option.id;
                                if (filled[oid] || !option.image_url) continue;
                                filled[oid] = option;
                                fillCard(oid, option);
                                filledCount++;
                            }
                            if (data.complete) { clearInterval(intervalId); resolve(filled); }
                        } catch (e) { /* keep polling */ } finally { polling = false; }
                    }, 8000);
                });

                round2Data = { session_id: sessionId, phase: 3, round: 2, options: ALL_IDS.map(id => filled[id]).filter(Boolean) };
                raw.textContent = JSON.stringify(round2Data, null, 2);
                round2Locked = false;
                renderRoundGrid("round2Grid", round2Data, 2);
            } catch (err) {
                console.error('[generateRound2] caught error:', err);
                grid.innerHTML = `<div class="brief-box">Error generating refined options: ${safeText(err)}</div>`;
            } finally {
                loader.classList.add("hidden");
            }
        }

        function renderRoundGrid(containerId, data, roundNumber) {
            const container = document.getElementById(containerId);
            container.innerHTML = "";

            const options = Array.isArray(data && data.options) ? data.options : [];
            if (!options.length) {
                container.innerHTML = `<div class="brief-box">No options found in response.</div>`;
                return;
            }

            const locked = roundNumber === 1 ? round1Locked : round2Locked;
            const selectedId = roundNumber === 1 ? selectedRound1Id : selectedRound2Id;

            options.forEach(option => {
                const imageUrl = extractImageUrl(option);
                const title = safeText(option.title, `Option ${safeText(option.id, "")}`);
                const desc = safeText(option.direction || option.commentary || option.description, "");
                const optionId = safeText(option.id, "");

                const card = document.createElement("div");

                let className = "card";
                if (selectedId === optionId) className += " selected";
                if (locked) className += " locked";
                if (locked && selectedId !== optionId) className += " dimmed";
                card.className = className;

                if (!locked && roundNumber !== 1) {
                    card.onclick = () => handleOptionClick(roundNumber, optionId, title);
                }

                const mediaHtml = imageUrl
                    ? `<img src="${imageUrl}" alt="${title}">`
                    : `<div>No preview image provided</div>`;

                const badgeHtml = selectedId === optionId && locked
                    ? `<div class="selected-badge">Selected</div>`
                    : "";

                card.innerHTML = `
                    ${roundNumber === 1 ? `<div class="option-letter-badge">${optionId}</div>` : ''}
                    ${badgeHtml}
                    <div class="card-media">${mediaHtml}</div>
                    <div class="card-body">
                        <div class="card-title">${title}</div>
                        <div class="card-text">${desc}</div>
                    </div>
                `;

                container.appendChild(card);
            });
        }

        function buildPreferenceInsight(data, selectedId) {
            const options = Array.isArray(data && data.options) ? data.options : [];
            const selected = options.find(x => safeText(x.id) === safeText(selectedId));

            if (!selected) {
                return "Your selection suggests a clearer preference is emerging. Design Mediator will now refine this direction further.";
            }

            const selectedTitle = safeText(selected.title, "this direction").toLowerCase();
            const directionText = safeText(selected.direction || selected.commentary || selected.description, "").toLowerCase();

            if (directionText.includes("warm") || selectedTitle.includes("warm")) {
                return "Your selection suggests you prefer warmer materials and a softer, more inviting atmosphere rather than a stricter or cooler interpretation. Design Mediator will now refine this direction further.";
            }

            if (directionText.includes("natural") || directionText.includes("organic") || selectedTitle.includes("natural") || selectedTitle.includes("botanical")) {
                return "Your selection suggests you prefer a more natural and organic atmosphere, with greater emphasis on texture, greenery, and material warmth. Design Mediator will now refine this direction further.";
            }

            if (directionText.includes("contrast") || selectedTitle.includes("contrast") || directionText.includes("urban")) {
                return "Your selection suggests you prefer a sharper, more defined atmosphere with stronger contrast and a more graphic visual character. Design Mediator will now refine this direction further.";
            }

            if (directionText.includes("minimal") || selectedTitle.includes("minimal") || selectedTitle.includes("zen")) {
                return "Your selection suggests you prefer a calmer and more restrained design language, with reduced visual noise and stronger simplicity. Design Mediator will now refine this direction further.";
            }

            return `Your selection suggests you prefer ${safeText(selected.title, "this direction").toLowerCase()} over the other alternatives, revealing a more specific preference in atmosphere, material balance, and furnishing character. Design Mediator will now refine this direction further.`;
        }

        async function handleOptionClick(roundNumber, optionId, optionTitle) {
            if (!sessionId) return;

            if (roundNumber === 1) {
                if (round1Locked) return;
                selectedRound1Id = optionId;
                round1Locked = true;
                renderRoundGrid("round1Grid", round1Data, 1);
                document.getElementById("round1TransitionTitle").textContent = `Direction selected: ${optionTitle}`;
                document.getElementById("round1TransitionText").textContent = "Design Mediator is now refining this direction. This may take a little time.";
                document.getElementById("round1Transition").classList.add("show");
            } else {
                if (round2Locked) return;
                selectedRound2Id = optionId;
                round2Locked = true;
                renderRoundGrid("round2Grid", round2Data, 2);
                document.getElementById("round2TransitionTitle").textContent = `Refined direction selected: ${optionTitle}`;
                document.getElementById("round2TransitionText").textContent = "Design Mediator is now synthesizing your final proposal. This may take a little time.";
                document.getElementById("round2Transition").classList.add("show");
            }

            const res = await fetch(`/session/${sessionId}/round/select`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ selected: optionId })
            });

            await res.json();

            if (roundNumber === 1) {
                showStage("stage-2b");
                const insight = buildPreferenceInsight(round1Data, optionId);
                document.getElementById("insightBox").textContent = insight;

                showStage("stage-3");
                setTracker(3);
                await sleep(500);
                await generateRound2();
            } else {
                showStage("stage-4");
                setTracker(4);
                await generateFinalBrief();
            }
        }

        function renderFormattedBrief(data) {
            const brief = data && data.final_brief ? data.final_brief : null;

            if (!brief) {
                return `<div>No structured final brief was found in the response.</div>`;
            }

            const title = safeText(brief.final_title, "Final Design Direction");
            const summary = safeText(brief.final_summary, "No summary provided.");
            const rules = Array.isArray(brief.key_design_rules) ? brief.key_design_rules : [];
            const axisSummary = brief.axis_summary && typeof brief.axis_summary === "object" ? brief.axis_summary : {};

            const rulesHtml = rules.length
                ? `<ul class="brief-list">${rules.map(rule => `<li>${safeText(rule)}</li>`).join("")}</ul>`
                : `<div>No key design rules provided.</div>`;

            const axisEntries = Object.entries(axisSummary);
            const axisHtml = axisEntries.length
                ? `<div class="axis-grid">${axisEntries.map(([k, v]) => `<div class="axis-item"><strong>${safeText(k)}</strong><br>${safeText(v)}</div>`).join("")}</div>`
                : `<div>No axis summary provided.</div>`;

            return `
                <div class="brief-section">
                    <div class="brief-heading">Final Direction</div>
                    <div class="brief-title">${title}</div>
                </div>
                <div class="brief-section">
                    <div class="brief-heading">Summary</div>
                    <div>${summary}</div>
                </div>
                <div class="brief-section">
                    <div class="brief-heading">Key Design Rules</div>
                    ${rulesHtml}
                </div>
                <div class="brief-section">
                    <div class="brief-heading">Axis Summary</div>
                    ${axisHtml}
                </div>
                <div class="brief-section">
                    <div class="brief-heading">Process Note</div>
                    <div>This proposal was generated based on visual selections made by the user.</div>
                </div>
            `;
        }

        async function generateFinalBrief() {
            const loader = document.getElementById("loader-stage-4");
            const briefBox = document.getElementById("briefBox");
            const heroBox = document.getElementById("finalHeroBox");
            const heroActions = document.getElementById("heroActions");
            const openFullBtn = document.getElementById("openFullBtn");
            const downloadBtn = document.getElementById("downloadBtn");

            loader.classList.remove("hidden");
            setProgress("s4p", 0, 3, "Preparing final brief…");
            briefBox.textContent = "Generating final brief...";
            heroBox.innerHTML = "Preparing final hero image...";
            heroBox.classList.remove("hero-clickable");
            heroBox.onclick = null;
            heroActions.style.display = "none";
            finalHeroUrl = null;

            try {
                setProgress("s4p", 1, 3, "Synthesizing final proposal…");

                const res = await fetch(`/session/${sessionId}/final-brief`, {
                    method: "POST"
                });

                setProgress("s4p", 2, 3, "Formatting final design brief…");
                const data = await res.json();

                setProgress("s4p", 3, 3, "Final proposal ready.");

                briefBox.innerHTML = renderFormattedBrief(data);

                const selectedRound2Option = round2Data?.options?.find(o => o.id === selectedRound2Id);
                finalHeroUrl = selectedRound2Option?.image_url || round2Data?.options?.[0]?.image_url;

                if (finalHeroUrl) {
                    heroBox.innerHTML = `<img src="${finalHeroUrl}" alt="Final hero render">`;
                    heroBox.classList.add("hero-clickable");
                    heroBox.onclick = () => window.open(finalHeroUrl, "_blank", "noopener,noreferrer");
                    openFullBtn.href = finalHeroUrl;
                    downloadBtn.href = finalHeroUrl;
                    heroActions.style.display = "flex";
                } else {
                    heroBox.innerHTML = "No final hero image URL was found in the current responses.";
                }
            } catch (err) {
                briefBox.textContent = "Error generating final brief: " + err;
                heroBox.innerHTML = "Final hero image unavailable.";
            } finally {
                loader.classList.add("hidden");
            }
        }

        // Voice input (Web Speech API)
        (function() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const micBtn = document.getElementById('round1MicBtn');
            if (!SpeechRecognition) {
                if (micBtn) micBtn.style.display = 'none';
                return;
            }
            let recognition = null;
            let isRecording = false;
            window.toggleMic = function() {
                if (isRecording) {
                    recognition.stop();
                    return;
                }
                recognition = new SpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'en-US';
                recognition.onstart = () => {
                    isRecording = true;
                    micBtn.classList.add('recording');
                };
                recognition.onend = () => {
                    isRecording = false;
                    micBtn.classList.remove('recording');
                };
                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    const ta = document.getElementById('round1FeedbackText');
                    ta.value = (ta.value ? ta.value + ' ' : '') + transcript;
                };
                recognition.onerror = () => {
                    isRecording = false;
                    micBtn.classList.remove('recording');
                };
                recognition.start();
            };
        })();

        async function submitRound1Feedback() {
            const textarea = document.getElementById('round1FeedbackText');
            const responseArea = document.getElementById('round1FeedbackResponse');
            const submitBtn = document.querySelector('#round1Feedback button:last-of-type');

            const comment = (textarea.value || '').trim();
            if (!comment) {
                responseArea.style.display = 'block';
                responseArea.textContent = 'Please share your thoughts before continuing.';
                return;
            }

            submitBtn.disabled = true;
            submitBtn.textContent = 'Reading your feedback…';
            responseArea.style.display = 'none';

            try {
                const res = await fetch(`/session/${sessionId}/round/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ comment })
                });
                const data = await res.json();
                console.log('[feedback] data:', JSON.stringify(data));

                if (data.error) {
                    responseArea.style.display = 'block';
                    responseArea.textContent = 'Something went wrong. Please try again.';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Generate my refined options →';
                    return;
                }

                if (!data.understood) {
                    responseArea.style.display = 'block';
                    responseArea.textContent = data.reply || 'Could you tell us more about what you liked or disliked?';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Generate my refined options →';
                    return;
                }

                responseArea.style.display = 'block';
                responseArea.textContent = 'Got it. Generating your refined options based on your feedback…';
                submitBtn.disabled = true;

                await sleep(1500);
                console.log('[round2] signals being passed:', JSON.stringify(data.signals));
                await generateRound2(data.signals);

            } catch (err) {
                responseArea.style.display = 'block';
                responseArea.textContent = 'Error: ' + err;
                submitBtn.disabled = false;
                submitBtn.textContent = 'Generate my refined options →';
            }
        }

        restartDemo();
    </script>
</body>
</html>
"""

@app.get("/gemini-test")
def gemini_test():
    try:
        client = get_genai_client()

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with exactly this sentence and nothing else: Gemini connection successful."
        )

        text = getattr(response, "text", None)

        return {
            "ok": True,
            "project": os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT") or "design-alignment-agent",
            "location": "global",
            "response": text,
        }

    except Exception as e:
        return {
            "ok": False,
            "error_type": type(e).__name__,
            "error": str(e),
        }


@app.post("/session/start")
def start_session():
    session_id = uuid.uuid4().hex
    doc_ref = db.collection("sessions").document(session_id)

    state = default_state()
    doc_ref.set(state)

    return {
        "session_id": session_id,
        "phase": state["phase"]
    }


@app.post("/session/{session_id}/select-style")
def select_style(session_id: str, payload: SelectStyleRequest):
    try:
        styles = _validate_styles(payload.styles)

        doc_ref = db.collection("sessions").document(session_id)

        snap = doc_ref.get()
        if not snap.exists:
            return {
                "error": "session_not_found",
                "session_id": session_id
            }

        commentary = generate_style_commentary(styles)

        data = snap.to_dict() or {}
        history = data.get("history", [])
        if not isinstance(history, list):
            history = []

        history.append(
            {
                "ts": datetime.utcnow().isoformat(),
                "type": "style_selected",
                "styles": styles,
            }
        )

        history.append(
            {
                "ts": datetime.utcnow().isoformat(),
                "type": "style_commentary_generated",
                "styles": styles,
            }
        )

        doc_ref.set(
            {
                "style_selected": styles,
                "style_commentary": commentary,
                "phase": 2,
                "clarification_pending": False,
                "history": history,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

        return {
            "session_id": session_id,
            "phase": 2,
            "style_selected": styles,
            "style_commentary": commentary,
        }

    except ValueError as ve:
        return {
            "error": "invalid_request",
            "detail": str(ve)
        }
    except Exception as e:
        return {
            "error": "runtime_error",
            "error_type": type(e).__name__,
            "detail": str(e)
        }


@app.post("/session/{session_id}/round/start")
def round_start(session_id: str, payload: RoundStartRequest):
    try:
        client = get_genai_client()

        result = start_round(
            session_id=session_id,
            round_number=payload.round,
            db=db,
            gemini_client=client,
            signals=payload.signals,
        )

        return result

    except ValueError as e:
        return {"error": str(e)}

    except Exception as e:
        return {
            "error": "round_generation_failed",
            "error_type": type(e).__name__,
            "detail": str(e)
        }


@app.get("/session/{session_id}/round/poll")
def round_poll(session_id: str, round: int = None):
    try:
        doc_ref = db.collection("sessions").document(session_id)
        snap = doc_ref.get()

        if not snap.exists:
            return {"error": "Session not found"}

        session = snap.to_dict() or {}
        rounds = session.get("rounds", {})

        if round == 2:
            target_round = 2
            round_data = rounds.get("2", {})
            options = round_data.get("options", [])
            complete = len(options) >= 3 and all(
                any(o.get("id") == oid for o in options)
                for oid in ("1", "2", "3")
            )
        else:
            target_round = session.get("current_round", 1)
            round_data = rounds.get(str(target_round), {})
            options = round_data.get("options", [])
            complete = len(options) >= 6 and all(
                any(o.get("id") == oid for o in options)
                for oid in ("A", "B", "C", "D", "E", "F")
            )

        return {
            "round": target_round,
            "options": options,
            "complete": complete,
        }

    except Exception as e:
        return {
            "error": "poll_failed",
            "error_type": type(e).__name__,
            "detail": str(e)
        }


@app.post("/session/{session_id}/round/select")
def round_select(session_id: str, payload: dict):
    try:
        selected = payload.get("selected")

        if not selected:
            return {
                "error": "invalid_request",
                "detail": "selected option missing"
            }

        client = get_genai_client()

        result = select_option(
            session_id=session_id,
            selected_option=selected,
            db=db,
            gemini_client=client
        )

        return result

    except ValueError as e:
        return {
            "error": "invalid_request",
            "detail": str(e)
        }

    except Exception as e:
        return {
            "error": "round_select_failed",
            "error_type": type(e).__name__,
            "detail": str(e)
        }


@app.post("/session/{session_id}/round/feedback")
def round_feedback(session_id: str, payload: FeedbackRequest):
    import json as _json
    import re as _re
    from google.genai import types as _gtypes

    try:
        doc_ref = db.collection("sessions").document(session_id)
        snap = doc_ref.get()
        if not snap.exists:
            return {"error": "session_not_found"}

        session = snap.to_dict() or {}
        style_selected = session.get("style_selected", [])
        rounds = session.get("rounds", {})
        round1_options = (rounds.get("1") or rounds.get(1) or {}).get("options", [])

        system_prompt = (
            "You are a design alignment assistant. "
            "The user has just seen 6 interior design options labeled A through F. "
            "A and D are pure style references. B and E are distinct variations. "
            "C and F are style blends. "
            "The user will share what they liked or disliked about the designs. "
            "Your job is to extract specific design signals from their comment and the screenshot. "
            "If the comment contains clear design references, respond with a JSON object with "
            "two fields: understood (true) and signals. "
            "signals must be a JSON object with exactly these four fields: "
            "liked (a list of strings, each describing a specific element and which card it came from, "
            "e.g. warm oak walls from B, sculptural plants from E), "
            "disliked (a list of strings, each describing what to avoid, "
            "e.g. busy carpet from A, dark ceiling from D), "
            "mood (a single sentence describing the overall atmosphere the user is drawn to), "
            "primary_style_weight (a number from 0 to 10 indicating how much the user leaned "
            "toward the primary style — 0 means fully secondary, 10 means fully primary). "
            "If the comment is irrelevant or too vague to extract design signals, respond with "
            "understood (false) and reply (a friendly one-sentence redirect asking them to "
            "describe what they liked or disliked about the cards). "
            "Always respond in the same language the user wrote in. "
            "Return valid JSON only — no markdown, no explanation outside the JSON."
        )

        style_context = ""
        if style_selected:
            style_context = f"The user selected these styles: {', '.join(style_selected)}. "
        option_ids = [o.get("id", "") for o in round1_options if o.get("id")]
        if option_ids:
            style_context += f"Options shown: {', '.join(option_ids)}."

        user_message = f"{style_context}\n\nUser comment: {payload.comment}"

        client = get_genai_client()

        text_part = _gtypes.Part.from_text(text=user_message)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                _gtypes.Content(
                    role="user",
                    parts=[text_part],
                )
            ],
            config=_gtypes.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )

        raw_text = (getattr(response, "text", "") or "").strip()
        cleaned = _re.sub(r"```json|```", "", raw_text).strip()

        try:
            parsed = _json.loads(cleaned)
        except Exception:
            return {
                "understood": False,
                "reply": "I had trouble reading your feedback. Could you describe what you liked or disliked about specific cards?",
                "raw": raw_text,
            }

        return parsed

    except Exception as e:
        return {
            "error": "feedback_failed",
            "error_type": type(e).__name__,
            "detail": str(e),
        }


@app.post("/session/{session_id}/final-brief")
def final_brief(session_id: str):
    try:
        client = get_genai_client()

        result = generate_final_brief(
            session_id=session_id,
            db=db,
            gemini_client=client
        )

        return result

    except ValueError as e:
        return {
            "error": "invalid_request",
            "detail": str(e)
        }

    except Exception as e:
        return {
            "error": "final_brief_failed",
            "error_type": type(e).__name__,
            "detail": str(e)
        }