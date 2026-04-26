# Reality Compiler

Hardware idea to prototype in 60 seconds.

Describe any product — get a 3D model, bill of materials, sourcing links, assembly steps, and feasibility check.

## Quick Start

```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn backend.main:app --reload

# Frontend
cd viewer && npm install && npm run dev
```

Open [http://localhost:4178](http://localhost:4178).

## What It Does

- **3D URDF Models** — Engineering-grade parametric parts with real kinematics, not boxes
- **Bill of Materials** — Real components with sourcing (Amazon UK, RS, Alibaba)
- **Assembly** — Step-by-step build instructions + Arduino wiring
- **Feasibility** — Cost estimates, risk assessment, manufacturing readiness
- **Engineering Specs** — Exact dimensions (mm), materials, connection points, STEP/STL/DXF export definitions
- **Topology Graph** — Part connection map with joint types and degrees of freedom
- **X-Ray Mode** — See internal structure: motors, joints, wiring paths, frame

## Architecture

```
backend/
  main.py          — FastAPI server
  agents/          — Design, BOM, Sourcing, Feasibility, Arduino
  urdf_generator.py — Parametric URDF + STL generation
  schemas.py       — Pydantic validation for all outputs
viewer/
  components/reality-compiler/  — React + Three.js frontend
```

## Integrations

- **Pydantic Logfire** — Structured observability for every generation stage
- **Mubit SDK** — Design memory for iteration ("make it cheaper")

## Deploy

```bash
fly deploy
```

Live at [reality-compiler-taejuaku.fly.dev](https://reality-compiler-taejuaku.fly.dev/)
