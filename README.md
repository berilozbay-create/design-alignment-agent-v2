🔗 **[Live Demo](https://design-alignment-agent-71566893016.us-central1.run.app/demo)**  
💚 **[Health Endpoint](https://design-alignment-agent-71566893016.us-central1.run.app/health)**


# Design Alignment Agent

**Explore → Compare → Refine → Converge**

*Most people cannot describe their design taste — but they can recognise it when they see it.*

Design Alignment Agent is a stateful multimodal AI agent that helps users discover and articulate aesthetic preferences through structured visual interaction. Instead of asking users to describe what they want, the agent presents a sequence of AI-generated living rooms and observes how they react. Each selection updates the session state, progressively narrowing the design space until a clear aesthetic direction emerges.

Built for the **Gemini Live Agent Challenge**, this project explores how AI agents can guide creative decision-making through iterative visual dialogue. Creative storytelling here emerges through the evolution of visual preferences: the user's journey from uncertainty to a clearly defined aesthetic direction becomes the narrative the agent helps construct.

Although the current MVP focuses on interior living rooms, the underlying interaction model applies to any creative domain where **visual preference needs to be clarified before design execution begins** — branding, poster design, product aesthetics, marketing visuals.

---

## The Problem

Creative work often begins with unclear requirements. Clients rarely start with a precise specification — preferences emerge reactively, recognised only after seeing examples. Design labels like *Japandi* or *Hollywood Regency* are meaningful to designers but abstract to everyone else.

This leads to vague briefs, repeated revision cycles, and misalignment between designer and client. Mood boards collect references but don't guide users toward decisions.

Design Alignment Agent approaches the problem differently. Instead of requiring users to describe their taste in words, it translates **visual reactions into structured preferences**.

Users react to visual options. The agent interprets those reactions. Each round reduces the design space.

---

## How It Works

The experience follows a structured 4-phase arc:

1. **Style selection** — user picks one of 10 curated interior styles; all shown using the same living room so only the aesthetic language changes
2. **Style commentary** — Gemini interprets the choice into design language: overall vibe, key rules, common pitfalls, and exploration guidance
3. **Two rounds of visual comparison** — the agent presents 3 living room variations per round; the user picks one; each round narrows the direction
4. **Final brief** — Gemini synthesises the full interaction history into a structured design brief with title, summary, 5 design rules, and axis scores

The user never fills out a form. They just react to images.

---

## Why This Is an Agent

Design Alignment Agent is not a generation tool. It is a stateful multimodal AI agent that guides a decision process.

The system maintains a persistent session state across rounds, interprets user selections as preference signals, plans the next generation step before rendering images, and synthesises a final brief from the full interaction history. Rather than producing isolated outputs, the agent **aligns aesthetic intent through interaction**.

This also makes it a creative storytelling agent. Each interaction step becomes part of a narrative: the user explores options, reacts to them, and the agent interprets those reactions to guide the next stage. The final design brief is the conclusion — a record of how aesthetic preferences evolved from uncertainty to clarity.

---

## Beyond Prompt-Based Generation

Most generative design tools follow the same loop: describe what you want → model generates an image → repeat.

Design Alignment Agent follows a different paradigm. Instead of asking users to describe preferences, it observes how they react to visual alternatives. Each selection becomes a signal that updates the agent's understanding of the user's taste. The images serve as **decision instruments**, not final outputs.

---

## Architecture

![Architecture Diagram](design_mediator_arch_flow_01.png)

```
Browser
  │
  ▼
FastAPI (Google Cloud Run)
  ├── /session/start               → creates Firestore session
  ├── /session/{id}/select-style   → Gemini Flash generates style commentary
  ├── /session/{id}/round/start    → direction planner + sequential Imagen 3 calls
  ├── /session/{id}/round/select   → saves selection, advances phase
  └── /session/{id}/final-brief    → Gemini Flash synthesises design brief

Google Cloud Firestore             → stateful session storage
Gemini 2.5 Flash                   → text generation (planning, commentary, brief)
Gemini Imagen 3                    → photorealistic room rendering
```

**Gemini is called 7 times per session:**

| Call | Model | Purpose | Cost |
|------|-------|---------|------|
| Style commentary | Gemini 2.5 Flash | Interprets style pick into design language | Low |
| Direction planner | Gemini 2.5 Flash | Generates B + C specs (11 fields each) | Low |
| Round 1 image B | Gemini Imagen 3 | Renders option B | High |
| Round 1 image C | Gemini Imagen 3 | Renders option C | High |
| Round 2 image B | Gemini Imagen 3 | Renders cool refinement | High |
| Round 2 image C | Gemini Imagen 3 | Renders dark refinement | High |
| Final brief | Gemini 2.5 Flash | Synthesises journey into structured brief | Low |

Image generations run sequentially — B completes before C starts. All cost is in the 4 Imagen calls.

---

## Tech Stack

- **Backend** — FastAPI, Python 3.11
- **AI** — Google GenAI SDK (`google-genai==1.65.0`), Gemini 2.5 Flash, Gemini Imagen 3
- **Database** — Google Cloud Firestore
- **Deployment** — Google Cloud Run (containerised via Docker)

---

## Project Structure

```
├── main.py                       # FastAPI routes, session logic, demo UI
├── round_service.py              # Round orchestration, option building
├── selection_service.py          # Selection handling, phase advancement
├── design_direction_planner.py   # Gemini planning calls, direction specs
├── image_generation_service.py   # Imagen 3 calls, retry logic, file saving
├── final_brief_service.py        # Brief generation, JSON parsing
├── prompt_builders.py            # Prompt construction for image generation
├── static/
│   ├── room/empty_room.png       # Base living room anchor for all generations
│   └── styles/                   # 10 style reference thumbnails
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Running Locally

**Prerequisites**
- Python 3.11+
- A Google Cloud project with Vertex AI and Firestore enabled
- Application Default Credentials configured (`gcloud auth application-default login`)

**Setup**

```bash
git clone https://github.com/berilozbay-create/design-alignment-agent
cd design-alignment-agent

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your project values
```

**Environment variables**

```
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_LOCATION=us-central1
FIRESTORE_COLLECTION=sessions
```

**Run**

```bash
uvicorn main:app --reload --port 8080
```

Open `http://localhost:8080/demo` to try the full experience.

To verify your Gemini connection:

```
GET http://localhost:8080/gemini-test
```

---

## Deploying to Cloud Run

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/design-alignment-agent

gcloud run deploy design-alignment-agent \
  --image gcr.io/$PROJECT_ID/design-alignment-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,VERTEX_LOCATION=us-central1
```

---

## Session State

Each session is a Firestore document tracking the full journey:

```json
{
  "phase": 4,
  "style_selected": ["Japandi"],
  "style_commentary": { "raw_text": "..." },
  "rounds": {
    "1": { "options": [...], "selected": "B" },
    "2": { "options": [...], "selected": "A" }
  },
  "selected_path": ["B", "A"],
  "last_selected_option": { "image_url": "...", "style_name": "...", "..." : "..." },
  "final_brief": {
    "final_title": "Calm Material Edit",
    "final_summary": "...",
    "key_design_rules": ["...", "...", "...", "...", "..."],
    "axis_summary": {
      "minimalism": "high",
      "warmth": "medium",
      "texture": "medium-high",
      "contrast": "low",
      "craft": "medium"
    }
  },
  "history": [...]
}
```

The selected image URL stored in session enables Round 2 to use Round 1's output as its spatial anchor — same room, different material direction.

---

## Design Decisions

**Fixed spatial canvas.** Every generation uses the same living room: same camera angle, same floor-to-ceiling windows, same natural light. This means users evaluate stylistic differences — not architectural ones. The options remain directly comparable across all rounds.

**Planning before rendering.** Design reasoning is separated from image generation. Gemini Flash first produces structured direction specs (palette, materials, furniture character, lighting) across 11 fields. Imagen 3 then renders those specs. This makes the system behave like a design reasoning agent, not a raw generator — and keeps quality high while controlling cost.

**Hardcoded Option A.** Option A in Round 1 is a handcrafted reference for each style, not AI-generated. This gives users a known-good baseline and ensures one card is always coherent regardless of generation quality.

**One style, not many.** A single style keeps the convergence arc clean. The direction planner generates two meaningful variations within one style family — blending styles would dilute the signal.

**Visual comparison over text input.** Each round presents exactly 3 options. Users respond to images rather than writing descriptions. This mirrors how people naturally evaluate design — through direct comparison.

---

## Built For

[Gemini Live Agent Challenge](https://googledevai.devpost.com/) — a hackathon focused on multimodal, interactive AI agent experiences.

The theme: **storytelling through preference evolution.** The user's journey from aesthetic uncertainty to a clearly articulated design direction, guided by an AI agent that observes, interprets, and converges.

---

## Original Vision & Future Direction

The MVP delivers a fixed 2-round click-based flow. This was a deliberate scope decision for the hackathon — but the original vision was more ambitious.

The intended experience was **conversational and open-ended**: users would move through as many rounds as needed, guided by natural language or voice, until they felt genuinely aligned. Rather than clicking thumbnails, users would describe reactions in their own words:

> "I like the sofa from A, the lighting from B, and I want the floor warmer."

The agent would interpret those references, update the session state, and generate the next iteration accordingly.

What exists today is the convergence loop and stateful memory that makes this possible. The interaction layer — voice, typed commentary, compositional feedback across cards — is the next layer to build.

**Planned extensions:**
- additional refinement rounds until the user is satisfied, not a fixed 2-round limit
- spoken or typed commentary between rounds as preference signals
- compositional selection across multiple cards ("take the sofa from A, the palette from C")
- richer session state modeling that tracks why decisions were made, not just what was selected
- expansion beyond living rooms into other creative domains

The core idea remains the same: AI agents can help people understand their own aesthetic preferences through guided visual exploration — and that process becomes more powerful the more natural the conversation.
