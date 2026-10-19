# Fatigue Design Agent (Agentic AI)

An autonomous, tool-using AI agent that performs fatigue design checks for mechanical components.
Give it a task in plain English; it plans, calls engineering tools in a loop, self-corrects on errors,
and saves a markdown report.

## Why it is "agentic"
- **Autonomy** - decides which tools to call and in what order (no fixed pipeline)
- **Tool use** - 8 tools: material DB, Peterson Kt, notch sensitivity, Marin factors, Goodman/Langer, Basquin-Morrow life, safe calculator, report writer
- **Feedback loop** - tool errors are returned to the model, which fixes inputs and retries
- **Reflection** - sanity checks before concluding (units, Kf >= 1, yield vs fatigue)
- **Memory** - persists recent tasks across sessions
- **Guardrails** - max 12 steps, AST-sandboxed calculator, no `eval`

## Architecture
![Architecture schema](docs/schema.png)

Mermaid version: [`docs/schema.md`](docs/schema.md)

## Setup
```bash
git clone <your-repo-url> && cd fatigue-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
python -m pytest -q    # 10 tool tests, no API key needed
```

## Run
```bash
python main.py "A 20 mm machined AISI 1045 plate, 100 mm wide, has a 10 mm central hole. Axial load gives sigma_a = 80 MPa, sigma_m = 60 MPa. Check infinite life at 99% reliability and estimate cycles if not."
python main.py            # interactive mode
```

## Example trace (abridged)
```
[step 1] THOUGHT: Plan: 1) material props 2) Kt for hole 3) Kf 4) Marin Se 5) Goodman 6) Basquin 7) report
[step 1] ACTION: get_material_properties({"name": "1045"})
[step 2] ACTION: stress_concentration_hole({"hole_dia_mm": 10, "plate_width_mm": 100})
...
[step 7] ACTION: save_report({"filename": "plate_hole_check", ...})
```

## Limitations
Handbook-level material data and closed-form factors; use for concept design, then validate with FEA/testing.

## Author
Athyanth - B.Tech Mechanical Engineering, VIT Chennai
