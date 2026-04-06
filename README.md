Design Alignment Agent v2
Explore → Blend → Describe → Converge
Most people cannot describe their design taste — but they can recognise it when they see it. And they can tell you exactly what they liked.
Design Alignment Agent v2 is a stateful multimodal AI system that helps users discover and articulate aesthetic preferences through structured visual dialogue and natural language feedback. Users pick two styles, explore six generated rooms that blend those styles in different proportions, describe what they liked in their own words, and receive a refined proposal that directly incorporates their stated preferences.
Built as a fork of the original Gemini Live Agent Challenge submission. V2 is an active development branch pushing the interaction model further.

What Changed from V1
V1 was a fixed click-based flow: pick one style, see three cards, click one, see three material refinements, click one, receive a brief.
V2 changes the interaction model fundamentally:
Dual style selection. Users pick a primary and secondary style. The system generates a structured 6-card layout that spans pure styles, distinct variations, and blended interpretations — giving users a much richer design space to react to.
Progressive card loading. Cards appear one by one as they generate rather than all at once. The experience feels alive throughout the ~2 minute generation process.
Natural language feedback. After seeing 6 cards, users describe what they liked and disliked in their own words — "I liked the furniture from B but it was too dark, I want it lighter like F, and I loved the plant from D." Any language is supported. Voice input is transcribed to text for editing before submission.
Signal-driven Round 2. Round 2 no longer generates mechanical material variations. Gemini reads the user's comment, extracts structured design signals (liked elements, disliked elements, overall mood), and uses those signals alongside all 6 labeled reference card images to generate refined proposals that directly incorporate what the user asked for.
Correct final hero image. The final proposal image now correctly reflects the user's Round 2 selection.

How It Works
The experience follows a structured arc:

Dual style selection — user picks a primary and secondary style from 10 curated options. The same living room is shown for each style so only the aesthetic language changes.
Style commentary — Gemini interprets both style choices into design language: vibe, key rules, exploration guidance.
Six-card exploration — the agent generates 6 living room cards appearing one by one:

A — pure primary style (static reference, appears at 5s)
B — primary style, distinct variation (generated)
C — primary-led blend: 70% primary, 30% secondary influence (generated)
D — pure secondary style (static reference, appears at 30s)
E — secondary style, distinct variation (generated)
F — secondary-led blend: 70% secondary, 30% primary influence (generated)


Natural language feedback — a text box with voice input appears after all 6 cards load. User describes what they liked or disliked across the cards by letter. Gemini reads the comment, extracts design signals, and confirms what it understood.
Signal-driven refinement — Round 2 generates 3 refined proposals using the extracted signals and all 6 labeled reference images. Gemini can visually identify liked elements in the reference cards and incorporate them into the new room.
Final brief — Gemini synthesises the full interaction history into a structured design brief: title, summary, 5 design rules, and axis scores.


Why This Is an Agent
Design Alignment Agent v2 is not a generation tool. It is a stateful multimodal AI agent that mediates a creative alignment process.
The system maintains persistent session state across rounds, interprets visual reactions and natural language as preference signals, plans generation steps before rendering images, uses labeled visual references to ground Round 2 in what the user actually saw, and synthesises a final brief from the full interaction history.
The interaction model reflects how creative alignment actually works — not through forms or prompts, but through reaction, description, and iteration.

Architecture
Browser
  │
  ▼
FastAPI (Google Cloud Run)
  ├── /session/start                    → creates Firestore session
  ├── /session/{id}/select-style        → Gemini Flash generates style commentary
  ├── /session/{id}/round/start         → direction planner + sequential image generation
  ├── /session/{id}/round/poll          → returns options ready so far (progressive loading)
  ├── /session/{id}/round/feedback      → Gemini reads comment + extracts signals
  └── /session/{id}/final-brief         → Gemini synthesises design brief

Google Cloud Firestore                  → stateful session storage
Gemini 2.5 Flash                        → text generation (planning, commentary, signals, brief)
gemini-2.5-flash-image                  → photorealistic room rendering
Pillow                                  → stamping A-F labels on reference images
Gemini calls per session:
CallModelPurposeStyle commentaryGemini 2.5 FlashInterprets both style picksRound 1 direction plannerGemini 2.5 FlashPlans B, C, E, F specsRound 1 image Bgemini-2.5-flash-imageRenders primary variationRound 1 image Cgemini-2.5-flash-imageRenders primary-led blendRound 1 image Egemini-2.5-flash-imageRenders secondary variationRound 1 image Fgemini-2.5-flash-imageRenders secondary-led blendFeedback analysisGemini 2.5 FlashExtracts signals from commentRound 2 direction plannerGemini 2.5 FlashPlans 3 signal-driven directionsRound 2 images 1, 2, 3gemini-2.5-flash-imageRenders refined proposals with reference imagesFinal briefGemini 2.5 FlashSynthesises journey into structured brief
All image generations run sequentially with 25-second cooldowns to stay within API rate limits.

Tech Stack

Backend — FastAPI, Python 3.11
AI — Google GenAI SDK, Gemini 2.5 Flash, gemini-2.5-flash-image
Image processing — Pillow (label stamping on reference images)
Database — Google Cloud Firestore
Deployment — Google Cloud Run (containerised via Docker)


Project Structure
├── main.py                       # FastAPI routes, session logic, demo UI
├── round_service.py              # Round orchestration, option building, prompts
├── selection_service.py          # Selection handling, phase advancement
├── design_direction_planner.py   # Gemini planning calls, direction specs
├── image_generation_service.py   # Image generation, label stamping, retry logic
├── final_brief_service.py        # Brief generation, JSON parsing
├── prompt_builders.py            # Prompt construction utilities
├── static/
│   ├── room/empty_room.png       # Base living room anchor for all generations
│   └── styles/                   # 10 style reference thumbnails
├── Dockerfile
├── requirements.txt
└── .env.example

Running Locally
Prerequisites

Python 3.11+
A Google Cloud project with Vertex AI and Firestore enabled
Application Default Credentials configured (gcloud auth application-default login)

Setup
bashgit clone https://github.com/berilozbay-create/design-alignment-agent-v2
cd design-alignment-agent-v2/backend

pip install -r requirements.txt
Environment variables
GOOGLE_CLOUD_PROJECT=your-project-id
FIRESTORE_COLLECTION=sessions
Run
bashuvicorn main:app --reload --port 8080
Open http://localhost:8080/demo to try the full experience.

Deploying to Cloud Run
bashcd backend

gcloud builds submit --tag gcr.io/$PROJECT_ID/design-alignment-agent-v2

gcloud run deploy design-alignment-agent-v2 \
  --image gcr.io/$PROJECT_ID/design-alignment-agent-v2 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID
Note on images: Cloud Run containers have ephemeral file systems. Generated images are saved to disk within the container and are accessible for the duration of a session. Images do not persist across container restarts. For persistent storage, migrate image saving to Google Cloud Storage.

Session State
Each session is a Firestore document tracking the full journey:
json{
  "phase": 4,
  "style_selected": ["Japandi", "Coastal"],
  "style_commentary": { "raw_text": "..." },
  "rounds": {
    "1": { "options": [...] },
    "2": { "options": [...], "selected": "2" }
  },
  "last_selected_option": { "image_url": "...", "style_name": "..." },
  "signals": {
    "liked": ["sofa from Card B", "plant from Card D"],
    "disliked": ["dark palette from Card B"],
    "mood": "warm and airy with natural elements",
    "primary_style_weight": 7
  },
  "final_brief": {
    "final_title": "...",
    "final_summary": "...",
    "key_design_rules": ["...", "...", "...", "...", "..."],
    "axis_summary": { "minimalism": "medium", "warmth": "high" }
  },
  "history": [...]
}

Design Decisions
Fixed spatial canvas. Every generation uses the same living room: same camera angle, same windows, same natural light. Users evaluate style and material differences — not architectural ones.
Planning before rendering. Gemini Flash plans structured direction specs (11 fields) before any image is generated. This keeps reasoning and rendering separate, improves quality, and controls cost.
Static A and D. Cards A and D are handcrafted reference images for each style, not AI-generated. This gives users a reliable baseline and ensures two cards are always coherent regardless of generation quality.
Labeled reference images. Before sending Round 1 cards to Gemini for Round 2 generation, each image is stamped with its letter (A-F) using Pillow. Gemini can visually identify which card the user referenced and extract the specific elements they liked.
Sequential generation with cooldowns. Images generate one at a time with 25-second gaps. This prevents API rate limit errors (429s) that occur when multiple simultaneous image requests hit the shared capacity pool.
Polling architecture. The frontend fires the round/start call in the background and polls every 8 seconds for new options. Cards appear as they arrive rather than all at once, making the wait feel active rather than frozen.
Natural language over clicks. Round 2 is driven by what the user says, not which card they click. This produces richer preference signals and a more natural interaction — users can reference multiple cards, express nuance, and describe what they want in their own words.

Known Limitations

Generated images do not persist across Cloud Run container restarts (no Cloud Storage integration yet)
Voice input uses the browser's Web Speech API which has variable accuracy across browsers and languages
Image generation rate limits (429 errors) can occur during heavy testing — the 25-second cooldown reduces but does not eliminate this risk
Round 2 image quality depends on Gemini's ability to visually identify specific elements in the labeled reference images, which is not always precise


Relationship to V1
This repo is a fork of the original hackathon submission at github.com/berilozbay-create/design-alignment-agent. V1 is frozen and not modified. All active development happens here.

Built For
Gemini Live Agent Challenge — a hackathon focused on multimodal, interactive AI agent experiences.
The theme: storytelling through preference evolution. The user's journey from aesthetic uncertainty to a clearly articulated design direction, guided by an AI agent that observes, interprets, and converges.
