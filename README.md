# VoltLab — Battery Module Digital Twin (Hackathon MVP)

A runnable full-stack educational battery-module design platform. Dark React dashboard + Node/Express API + Python/FastAPI numerical model.

## Prerequisites
- Node.js 20+ and npm
- Python 3.10+

## Start (three terminals)

**Terminal 1 — simulator**
```bash
cd simulator
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

**Terminal 2 — API**
```bash
cd backend
npm install
npm run dev
```

**Terminal 3 — frontend**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Simulator API docs: http://localhost:8000/docs. Node API health: http://localhost:3001/api/health.

## Features
- NMC/LFP illustrative parameter presets; configurable S/P topology, load, SOC, ambient temperature, cooling, age and variation.
- Nominal/usable energy, loaded voltage, resistance, heat, temperature trace, SOC trace, cost, mass, volume.
- Baseline vs improved cooling vs additional parallel string, screening and transparent heuristic recommendation.
- Rule-based safety warnings and explicit model assumptions.
- Saved designs persisted in `backend/designs.json` (local development storage), JSON report export.
- Server-side Zod validation and Python domain validation.

## Tests
```bash
cd simulator
python -m pytest -q
```

## Architecture
```text
React/Vite (5173) --HTTP--> Express (3001) --HTTP--> FastAPI (8000)
                            |
                            +--> designs.json (local persistence)
```

## Model and evidence
Read [docs/MODEL.md](docs/MODEL.md) for equations, limits, assumptions, repeatable cases and validation plan.

## Important safety notice
**Educational, first-order simulation only.** No manufacturer-specific certified cell parameters, real BMS, electrochemical model, cell-resolved thermal behavior, validated protection logic or thermal-runaway prediction. Do not use its results to design, assemble, charge or operate real packs without qualified engineering review, verified data and physical testing.

## Automatic design optimizer (added)

Open **Auto Optimizer** in the left navigation. Set minimum nominal energy, maximum peak temperature, maximum estimated cost, and maximum mass, then select **Find best feasible design**. The optimizer enumerates 120 configurations (3S–12S and 1P–12P), applies the selected constraints plus illustrative cell-current and loaded-voltage screens, ranks feasible candidates with a transparent weighted heuristic, and lets you load a candidate into Design Studio.

API: `POST /api/optimize` on the Node API, proxied to `POST /optimize` on FastAPI. Request shape:

```json
{
  "config": {
    "chemistry": "NMC", "series": 4, "parallel": 3,
    "current": 5, "ambient": 25, "cooling": 0.8,
    "duration": 30, "soc": 100, "age": 0, "variation": 0
  },
  "constraints": {
    "minEnergyWh": 120, "maxTempC": 45,
    "maxCostUsd": 100, "maxMassKg": 3
  }
}
```

The search and score are decision-support heuristics over illustrative data, not a proof of a global optimum or a safety certification. Verify parameters against manufacturer datasheets and validate with supervised testing before real-world use.
