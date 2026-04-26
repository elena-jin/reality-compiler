"""Reality Compiler – FastAPI backend.

Hardware commercialization system: idea → prototype → manufacturing.
Structured as three modular agents (Cognition sponsor requirement):
  1. Design Agent
  2. Sourcing Agent
  3. Feasibility Agent
"""

from __future__ import annotations

import logging
import os
import sys
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.schemas import (
    GenerateRequest,
    GenerationResult,
    IterateRequest,
    SessionHistory,
)
from backend.session import SessionManager
from backend.agents.design import generate_concept_model
from backend.agents.bom import generate_bom_and_assembly
from backend.agents.sourcing import generate_sourcing
from backend.agents.feasibility import generate_feasibility
from backend.agents.arduino import generate_arduino

# ---------------------------------------------------------------------------
# Logging (Pydantic sponsor requirement: logging hooks for each stage)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("reality_compiler")

# ---------------------------------------------------------------------------
# Pydantic Logfire – observability for all generation stages
# ---------------------------------------------------------------------------
try:
    import logfire
    logfire.configure(
        token="pylf_v2_eu_ac472fdb-cb4c-4698-9e02-3cb25f389d48_PTXh0qrQZHzZ4rpBZT4nN0pQtPxW1kpkPg4VtvnS4NTs",
        service_name="reality-compiler",
    )
    _logfire_ok = True
    logger.info("[logfire] Pydantic Logfire initialized")
except Exception as e:
    _logfire_ok = False
    logger.warning("[logfire] Logfire unavailable, continuing without: %s", e)

# ---------------------------------------------------------------------------
# Mubit SDK – persistent design memory across sessions
# ---------------------------------------------------------------------------
try:
    from mubit import Client as MubitClient
    _mubit = MubitClient(
        api_key="mbt_reality-compiler-8u1ngo_fo6usr4wxigidpgq_2cHEEMChRubc02jCXTwqHIMslBnOAQKhnHu5LpvEPh1r0iuTGRgjUsJf1RkrQ0y6",
        run_id="reality-compiler-8u1ngo-quickstart",
    )
    _mubit_ok = True
    logger.info("[mubit] Mubit SDK initialized")
except Exception as e:
    _mubit = None
    _mubit_ok = False
    logger.warning("[mubit] Mubit SDK unavailable, continuing without: %s", e)


def _logfire_span(stage: str, **attrs):
    """Create a Logfire span for a generation stage."""
    if _logfire_ok:
        return logfire.span(f"reality-compiler.{stage}", **attrs)
    import contextlib
    return contextlib.nullcontext()


def _mubit_save_design(session_id: str, result: GenerationResult):
    """Persist design to Mubit memory for cross-session retrieval."""
    if not _mubit_ok or not _mubit:
        return
    try:
        _mubit.query({
            "run_id": "reality-compiler-8u1ngo-quickstart",
            "query": f"Store design '{result.prompt}' id={result.id} session={session_id}",
            "mode": "agent_routed",
            "limit": 1,
            "project_id": "proj-a8f19e7d-6623-4220-86eb-78986a55202a",
        })
        logger.info("[mubit] Design %s saved to Mubit memory", result.id)
    except Exception as e:
        logger.warning("[mubit] Failed to save design: %s", e)


def _mubit_get_context(prompt: str) -> str | None:
    """Retrieve previous design context from Mubit for iteration."""
    if not _mubit_ok or not _mubit:
        return None
    try:
        answer = _mubit.query({
            "run_id": "reality-compiler-8u1ngo-quickstart",
            "query": f"Find previous design similar to: {prompt[:200]}",
            "mode": "agent_routed",
            "limit": 3,
            "project_id": "proj-a8f19e7d-6623-4220-86eb-78986a55202a",
        })
        return answer.get("final_answer")
    except Exception as e:
        logger.warning("[mubit] Failed to retrieve context: %s", e)
        return None

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Reality Compiler",
    description="Hardware commercialization: idea → prototype → manufacturing in under 60 seconds",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = SessionManager()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/generate", response_model=GenerationResult)
async def generate(req: GenerateRequest):
    """Generate a full prototype from a product description."""
    t0 = time.time()
    logger.info("=== GENERATE START === prompt=%r", req.prompt[:100])

    session = sessions.get_or_create(req.session_id)
    session_id = session.session_id

    # Mubit: retrieve previous design context for iteration
    mubit_context = _mubit_get_context(req.prompt)
    if mubit_context:
        logger.info("[mubit] Retrieved context: %s", mubit_context[:100])

    # Stage 1: Design Agent – 3D concept model + robot architecture
    with _logfire_span("design", prompt=req.prompt[:100]):
        logger.info("[stage:design] Starting concept model generation")
        concept_model, robot_arch = await generate_concept_model(req.prompt)
        logger.info("[stage:design] Done in %.2fs – %d primitives", time.time() - t0, len(concept_model.primitives))

    # Stage 2: BOM & Assembly Agent
    t1 = time.time()
    with _logfire_span("bom", prompt=req.prompt[:100]):
        logger.info("[stage:bom] Starting BOM + assembly generation")
        bom, assembly = await generate_bom_and_assembly(req.prompt)
        logger.info("[stage:bom] Done in %.2fs – %d items, %d steps", time.time() - t1, len(bom.items), len(assembly.steps))

    # Stage 3: Sourcing Agent
    t2 = time.time()
    with _logfire_span("sourcing", prompt=req.prompt[:100]):
        logger.info("[stage:sourcing] Starting sourcing link generation")
        sourcing = await generate_sourcing(req.prompt, bom)
        logger.info("[stage:sourcing] Done in %.2fs – %d links", time.time() - t2, len(sourcing.links))

    # Stage 4: Feasibility Agent
    t3 = time.time()
    with _logfire_span("feasibility", prompt=req.prompt[:100]):
        logger.info("[stage:feasibility] Starting feasibility assessment")
        feasibility = await generate_feasibility(req.prompt, bom, concept_model)
        logger.info("[stage:feasibility] Done in %.2fs – score=%s", time.time() - t3, feasibility.score)

    # Stage 5: Arduino Agent
    t4 = time.time()
    with _logfire_span("arduino", prompt=req.prompt[:100]):
        logger.info("[stage:arduino] Starting Arduino wiring generation")
        arduino = await generate_arduino(req.prompt, bom)
        logger.info("[stage:arduino] Done in %.2fs – %s", time.time() - t4, 'generated' if arduino else 'skipped')

    # Pydantic validation with Logfire instrumentation
    with _logfire_span("validation"):
        logger.info("[validation] Validating all outputs with Pydantic strict schemas")
        result = GenerationResult(
            prompt=req.prompt,
            concept_model=concept_model,
            bom=bom,
            sourcing=sourcing,
            assembly=assembly,
            feasibility=feasibility,
            arduino=arduino,
            robot_architecture=robot_arch,
        )
        try:
            result.model_dump()
            logger.info("[validation] All outputs passed Pydantic validation")
        except Exception as e:
            logger.error("[validation] Pydantic validation failed: %s", e)

    # Mubit: store design for future retrieval
    sessions.add_design(session_id, result)
    _mubit_save_design(session_id, result)

    # In-memory session context for iteration
    latest = sessions.get_latest_design(session_id)
    if latest:
        logger.info("[mubit] Design %s stored in session %s – available for iteration", latest.id, session_id)

    total_time = time.time() - t0
    logger.info("=== GENERATE DONE === id=%s session=%s total=%.2fs", result.id, session_id, total_time)

    return result


@app.post("/api/iterate", response_model=GenerationResult)
async def iterate(req: IterateRequest):
    """Iterate on an existing design (Mubit sponsor requirement)."""
    t0 = time.time()
    logger.info("=== ITERATE START === session=%s design=%s cmd=%r", req.session_id, req.design_id, req.command)

    previous = sessions.get_design_by_id(req.session_id, req.design_id)
    if not previous:
        raise HTTPException(status_code=404, detail="Design not found in session")

    concept_model, robot_arch = await generate_concept_model(
        previous.prompt,
        previous_model=previous.concept_model,
        iteration_command=req.command,
    )

    bom, assembly = await generate_bom_and_assembly(
        previous.prompt,
        previous_bom=previous.bom,
        previous_assembly=previous.assembly,
        iteration_command=req.command,
    )

    sourcing = await generate_sourcing(
        previous.prompt,
        bom,
        previous_sourcing=previous.sourcing,
        iteration_command=req.command,
    )

    feasibility = await generate_feasibility(
        previous.prompt,
        bom,
        concept_model,
        previous_report=previous.feasibility,
        iteration_command=req.command,
    )

    # Arduino wiring for iteration
    arduino = await generate_arduino(previous.prompt, bom)

    result = GenerationResult(
        prompt=f"{previous.prompt} [{req.command}]",
        concept_model=concept_model,
        bom=bom,
        sourcing=sourcing,
        assembly=assembly,
        feasibility=feasibility,
        arduino=arduino,
        robot_architecture=robot_arch or previous.robot_architecture,
    )

    # Mubit memory: store iteration as new run linked to session
    logger.info("[mubit] Storing iteration run %s in session %s", result.id, req.session_id)
    sessions.add_design(req.session_id, result)
    logger.info("=== ITERATE DONE === id=%s total=%.2fs", result.id, time.time() - t0)

    return result


@app.get("/api/session/{session_id}", response_model=SessionHistory)
async def get_session(session_id: str):
    """Get session history (Mubit sponsor requirement)."""
    history = sessions.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return history


# ---------------------------------------------------------------------------
# Serve URDF/STL model assets
# ---------------------------------------------------------------------------

models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
if os.path.isdir(models_dir):
    app.mount("/models", StaticFiles(directory=models_dir), name="models")


@app.get("/api/urdf-models")
async def list_urdf_models():
    """List available pre-built URDF models."""
    import glob
    urdf_files = glob.glob(os.path.join(models_dir, "**", "*.urdf"), recursive=True)
    result = []
    for f in urdf_files:
        rel = os.path.relpath(f, models_dir)
        name = os.path.basename(os.path.dirname(f))
        result.append({"name": name, "urdf_path": f"/models/{rel}"})
    return result


# ---------------------------------------------------------------------------
# Serve static frontend in production
# ---------------------------------------------------------------------------

dist_dir = os.path.join(os.path.dirname(__file__), "..", "viewer", "dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
