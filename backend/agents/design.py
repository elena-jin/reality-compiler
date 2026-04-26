"""Design Agent – generates a 3D concept model from a product description.

Produces a list of geometric primitives (box, cylinder, sphere, cone, torus)
that approximate the described product for Three.js rendering.
"""

from __future__ import annotations

import json
import logging
import math
import os
from typing import Optional

from backend.schemas import ConceptModel, ModelPrimitive, ParametricPart, TopologyGraph, Vec3
from backend.urdf_generator import generate_urdf_for_prompt, generate_urdf_from_compiled_parts
from backend.robot_compiler import compile_robot

logger = logging.getLogger("reality_compiler.design_agent")

# ---------------------------------------------------------------------------
# OpenAI integration (optional – falls back to heuristic generation)
# ---------------------------------------------------------------------------

DESIGN_SYSTEM_PROMPT = """You are a hardware product design agent. Given a product description, generate a simplified 3D concept model using geometric primitives.

Return ONLY valid JSON matching this schema:
{
  "primitives": [
    {
      "shape": "box|cylinder|sphere|cone|torus",
      "position": {"x": 0, "y": 0, "z": 0},
      "rotation": {"x": 0, "y": 0, "z": 0},
      "scale": {"x": 1, "y": 1, "z": 1},
      "color": "#hexcolor",
      "label": "part name"
    }
  ],
  "camera_distance": 5.0
}

Guidelines:
- Use simple primitives to approximate the product shape
- Keep total primitives under 20 for performance
- Use realistic proportions (units are roughly in cm)
- Choose distinct colors for different functional parts
- Position parts relative to each other realistically
- Set camera_distance so the full model is visible"""


async def generate_concept_model(
    prompt: str,
    previous_model: Optional[ConceptModel] = None,
    iteration_command: Optional[str] = None,
) -> tuple[ConceptModel, "RobotArchitecture | None"]:
    logger.info("Design agent: generating concept model for '%s'", prompt[:80])

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            return await _generate_with_openai(prompt, previous_model, iteration_command, api_key), None
        except Exception:
            logger.warning("OpenAI call failed, falling back to heuristic generation", exc_info=True)

    return _generate_heuristic(prompt, previous_model, iteration_command)


async def _generate_with_openai(
    prompt: str,
    previous_model: Optional[ConceptModel],
    iteration_command: Optional[str],
    api_key: str,
) -> ConceptModel:
    import httpx

    messages = [{"role": "system", "content": DESIGN_SYSTEM_PROMPT}]

    user_content = f"Product idea: {prompt}"
    if previous_model and iteration_command:
        user_content += f"\n\nPrevious model JSON:\n{previous_model.model_dump_json()}"
        user_content += f"\n\nIteration command: {iteration_command}"
        user_content += "\nUpdate the previous model according to the command. Return the full updated model."

    messages.append({"role": "user", "content": user_content})

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        logger.info("Design agent: OpenAI returned %d primitives", len(parsed.get("primitives", [])))
        return ConceptModel(**parsed)


# ---------------------------------------------------------------------------
# Heuristic fallback – keyword-driven model generation
# ---------------------------------------------------------------------------

_PALETTE = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#64748b"]


def _generate_heuristic(
    prompt: str,
    previous_model: Optional[ConceptModel],
    iteration_command: Optional[str],
) -> tuple[ConceptModel, "RobotArchitecture | None"]:
    lp = prompt.lower()

    if previous_model and iteration_command:
        return _apply_iteration(previous_model, iteration_command), None

    # Procedural robot compilation — unique design per prompt
    urdf_path = None
    parametric_parts = []
    topology = None
    robot_arch = None
    compiled_parts = None

    try:
        robot_arch, compiled_parts = compile_robot(prompt)
        logger.info("Robot compiler: %s (%s, %d parts)", robot_arch.robot_class, robot_arch.concept_parse.morphology, len(compiled_parts))

        urdf_path, parametric_parts, topology = generate_urdf_from_compiled_parts(
            prompt, compiled_parts, robot_arch.robot_class,
        )
        if urdf_path:
            logger.info("Design agent: procedural URDF generated at %s", urdf_path)
    except Exception:
        logger.warning("Procedural compilation failed, falling back to archetype", exc_info=True)
        robot_arch = None
        try:
            urdf_path, parametric_parts, topology = generate_urdf_for_prompt(prompt)
        except Exception:
            logger.warning("Archetype URDF also failed", exc_info=True)

    if any(w in lp for w in ["gripper", "robot", "claw", "grabber"]):
        model = _gripper_model()
    elif any(w in lp for w in ["plant", "pot", "water", "planter"]):
        model = _plant_pot_model()
    elif any(w in lp for w in ["coin", "sort", "sorting"]):
        model = _coin_sorter_model()
    elif any(w in lp for w in ["lamp", "light", "desk light"]):
        model = _lamp_model()
    elif any(w in lp for w in ["phone", "stand", "holder", "dock"]):
        model = _phone_stand_model()
    elif any(w in lp for w in ["drone", "quadcopter", "uav"]):
        model = _drone_model()
    elif any(w in lp for w in ["gear", "gearbox", "transmission"]):
        model = _gearbox_model()
    else:
        model = _generic_model(prompt)

    # Attach engineering-grade data
    if urdf_path:
        model.urdf_path = urdf_path
    if parametric_parts:
        model.parametric_parts = [ParametricPart(**p) for p in parametric_parts]
    if topology:
        model.topology = TopologyGraph(**topology)

    return model, robot_arch


def _apply_iteration(model: ConceptModel, command: str) -> ConceptModel:
    lc = command.lower()
    primitives = [p.model_copy(deep=True) for p in model.primitives]

    urdf = model.urdf_path

    if "small" in lc or "compact" in lc or "mini" in lc:
        for p in primitives:
            p.scale = Vec3(x=p.scale.x * 0.7, y=p.scale.y * 0.7, z=p.scale.z * 0.7)
            p.position = Vec3(x=p.position.x * 0.7, y=p.position.y * 0.7, z=p.position.z * 0.7)
        return ConceptModel(primitives=primitives, camera_distance=model.camera_distance * 0.8, urdf_path=urdf, parametric_parts=model.parametric_parts, topology=model.topology)

    if "big" in lc or "large" in lc or "scale up" in lc:
        for p in primitives:
            p.scale = Vec3(x=p.scale.x * 1.4, y=p.scale.y * 1.4, z=p.scale.z * 1.4)
            p.position = Vec3(x=p.position.x * 1.4, y=p.position.y * 1.4, z=p.position.z * 1.4)
        return ConceptModel(primitives=primitives, camera_distance=model.camera_distance * 1.3, urdf_path=urdf, parametric_parts=model.parametric_parts, topology=model.topology)

    if "simpl" in lc or "fewer" in lc or "less" in lc:
        keep = max(3, len(primitives) // 2)
        return ConceptModel(primitives=primitives[:keep], camera_distance=model.camera_distance, urdf_path=urdf, parametric_parts=model.parametric_parts, topology=model.topology)

    return ConceptModel(primitives=primitives, camera_distance=model.camera_distance, urdf_path=urdf, parametric_parts=model.parametric_parts, topology=model.topology)


def _gripper_model() -> ConceptModel:
    return ConceptModel(
        primitives=[
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0, z=0), scale=Vec3(x=1.2, y=0.4, z=0.8), color="#1a1a1e", label="Base plate"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=0.6, z=0), scale=Vec3(x=0.3, y=0.8, z=0.3), color="#2a2a2e", label="Actuator housing"),
            ModelPrimitive(shape="box", position=Vec3(x=-0.5, y=1.2, z=0), scale=Vec3(x=0.15, y=0.8, z=0.3), rotation=Vec3(x=0, y=0, z=0.2), color="#c0c0c4", label="Left finger"),
            ModelPrimitive(shape="box", position=Vec3(x=0.5, y=1.2, z=0), scale=Vec3(x=0.15, y=0.8, z=0.3), rotation=Vec3(x=0, y=0, z=-0.2), color="#c0c0c4", label="Right finger"),
            ModelPrimitive(shape="box", position=Vec3(x=-0.5, y=1.8, z=0), scale=Vec3(x=0.12, y=0.3, z=0.25), rotation=Vec3(x=0, y=0, z=0.3), color="#1a1a1e", label="Left gripper pad"),
            ModelPrimitive(shape="box", position=Vec3(x=0.5, y=1.8, z=0), scale=Vec3(x=0.12, y=0.3, z=0.25), rotation=Vec3(x=0, y=0, z=-0.3), color="#1a1a1e", label="Right gripper pad"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=-0.4, z=0), scale=Vec3(x=0.15, y=0.3, z=0.15), color="#333338", label="Mounting flange"),
            ModelPrimitive(shape="box", position=Vec3(x=0.35, y=0.5, z=0.35), scale=Vec3(x=0.08, y=0.12, z=0.08), color="#1a1e2a", label="Servo motor"),
        ],
        camera_distance=5.0,
        urdf_path="/models/robot_arm/robot_arm.urdf",
    )


def _plant_pot_model() -> ConceptModel:
    return ConceptModel(
        primitives=[
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=0, z=0), scale=Vec3(x=1.2, y=0.15, z=1.2), color="#64748b", label="Base tray"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=0.7, z=0), scale=Vec3(x=1.0, y=1.0, z=1.0), color="#8b5cf6", label="Pot body"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=1.3, z=0), scale=Vec3(x=0.85, y=0.15, z=0.85), color="#92400e", label="Soil surface"),
            ModelPrimitive(shape="sphere", position=Vec3(x=0, y=1.9, z=0), scale=Vec3(x=0.5, y=0.6, z=0.5), color="#10b981", label="Plant foliage"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=1.5, z=0), scale=Vec3(x=0.06, y=0.4, z=0.06), color="#065f46", label="Stem"),
            ModelPrimitive(shape="box", position=Vec3(x=0.7, y=0.2, z=0), scale=Vec3(x=0.25, y=0.35, z=0.25), color="#06b6d4", label="Water reservoir"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0.4, y=0.4, z=0), scale=Vec3(x=0.04, y=0.3, z=0.04), color="#06b6d4", label="Water wick"),
            ModelPrimitive(shape="box", position=Vec3(x=-0.7, y=0.3, z=0), scale=Vec3(x=0.15, y=0.15, z=0.15), color="#f59e0b", label="Moisture sensor"),
        ],
        camera_distance=5.0,
    )


def _coin_sorter_model() -> ConceptModel:
    return ConceptModel(
        primitives=[
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0, z=0), scale=Vec3(x=2.0, y=0.2, z=1.5), color="#64748b", label="Base platform"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=1.0, z=-0.3), scale=Vec3(x=0.6, y=0.6, z=0.6), color="#8b5cf6", label="Coin hopper"),
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0.3, z=0), scale=Vec3(x=1.6, y=0.08, z=0.6), rotation=Vec3(x=-0.15, y=0, z=0), color="#6366f1", label="Sorting ramp"),
            ModelPrimitive(shape="box", position=Vec3(x=-0.7, y=0.1, z=0.5), scale=Vec3(x=0.35, y=0.3, z=0.3), color="#f59e0b", label="1p bin"),
            ModelPrimitive(shape="box", position=Vec3(x=-0.2, y=0.1, z=0.5), scale=Vec3(x=0.35, y=0.3, z=0.3), color="#10b981", label="5p bin"),
            ModelPrimitive(shape="box", position=Vec3(x=0.3, y=0.1, z=0.5), scale=Vec3(x=0.35, y=0.3, z=0.3), color="#06b6d4", label="10p bin"),
            ModelPrimitive(shape="box", position=Vec3(x=0.8, y=0.1, z=0.5), scale=Vec3(x=0.35, y=0.3, z=0.3), color="#ec4899", label="£1 bin"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=0.6, z=-0.3), scale=Vec3(x=0.08, y=0.3, z=0.08), color="#ef4444", label="Motor shaft"),
        ],
        camera_distance=6.0,
    )


def _lamp_model() -> ConceptModel:
    return ConceptModel(
        primitives=[
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=0, z=0), scale=Vec3(x=0.8, y=0.1, z=0.8), color="#64748b", label="Base"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=0.8, z=0), scale=Vec3(x=0.08, y=1.2, z=0.08), color="#8b5cf6", label="Stem"),
            ModelPrimitive(shape="cone", position=Vec3(x=0, y=1.8, z=0), scale=Vec3(x=0.7, y=0.5, z=0.7), color="#6366f1", label="Lampshade"),
            ModelPrimitive(shape="sphere", position=Vec3(x=0, y=1.6, z=0), scale=Vec3(x=0.15, y=0.2, z=0.15), color="#f59e0b", label="Bulb"),
            ModelPrimitive(shape="box", position=Vec3(x=0.3, y=0.05, z=0), scale=Vec3(x=0.1, y=0.06, z=0.06), color="#10b981", label="Switch"),
        ],
        camera_distance=5.0,
    )


def _phone_stand_model() -> ConceptModel:
    return ConceptModel(
        primitives=[
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0, z=0), scale=Vec3(x=1.0, y=0.12, z=0.8), color="#64748b", label="Base"),
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0.6, z=-0.25), scale=Vec3(x=0.8, y=1.0, z=0.08), rotation=Vec3(x=-0.2, y=0, z=0), color="#8b5cf6", label="Back support"),
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0.12, z=0.1), scale=Vec3(x=0.7, y=0.08, z=0.15), color="#6366f1", label="Front lip"),
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0.8, z=-0.15), scale=Vec3(x=0.45, y=0.85, z=0.04), rotation=Vec3(x=-0.2, y=0, z=0), color="#1e293b", label="Phone (preview)"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=0.05, z=-0.3), scale=Vec3(x=0.08, y=0.06, z=0.08), color="#06b6d4", label="Cable routing hole"),
        ],
        camera_distance=4.5,
    )


def _drone_model() -> ConceptModel:
    arms = []
    for i, angle in enumerate([0.785, 2.356, 3.927, 5.498]):
        x = math.cos(angle) * 0.8
        z = math.sin(angle) * 0.8
        arms.append(ModelPrimitive(shape="box", position=Vec3(x=x * 0.5, y=0, z=z * 0.5), scale=Vec3(x=0.8, y=0.08, z=0.1), rotation=Vec3(x=0, y=-angle, z=0), color="#64748b", label=f"Arm {i+1}"))
        arms.append(ModelPrimitive(shape="cylinder", position=Vec3(x=x, y=0.1, z=z), scale=Vec3(x=0.06, y=0.12, z=0.06), color="#ef4444", label=f"Motor {i+1}"))
        arms.append(ModelPrimitive(shape="cylinder", position=Vec3(x=x, y=0.2, z=z), scale=Vec3(x=0.3, y=0.02, z=0.3), color="#06b6d4", label=f"Propeller {i+1}"))

    return ConceptModel(
        primitives=[
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0, z=0), scale=Vec3(x=0.5, y=0.12, z=0.5), color="#1a1a1e", label="Central frame"),
            ModelPrimitive(shape="box", position=Vec3(x=0, y=-0.12, z=0), scale=Vec3(x=0.3, y=0.08, z=0.2), color="#1e2e4a", label="Battery"),
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0.1, z=0.1), scale=Vec3(x=0.12, y=0.06, z=0.08), color="#0d4d1e", label="Flight controller"),
            *arms,
        ],
        camera_distance=5.0,
        urdf_path="/models/drone/drone.urdf",
    )


def _gearbox_model() -> ConceptModel:
    return ConceptModel(
        primitives=[
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0, z=0), scale=Vec3(x=1.5, y=1.0, z=1.0), color="#333338", label="Housing"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=-0.5, y=0, z=0), scale=Vec3(x=0.4, y=0.15, z=0.4), rotation=Vec3(x=math.pi / 2, y=0, z=0), color="#c0c0c4", label="Input gear"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0.2, y=0, z=0), scale=Vec3(x=0.6, y=0.15, z=0.6), rotation=Vec3(x=math.pi / 2, y=0, z=0), color="#c0c0c4", label="Output gear"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=-0.9, y=0, z=0), scale=Vec3(x=0.08, y=0.5, z=0.08), rotation=Vec3(x=math.pi / 2, y=0, z=0), color="#888890", label="Input shaft"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0.9, y=0, z=0), scale=Vec3(x=0.1, y=0.5, z=0.1), rotation=Vec3(x=math.pi / 2, y=0, z=0), color="#888890", label="Output shaft"),
            ModelPrimitive(shape="sphere", position=Vec3(x=-0.5, y=0, z=0), scale=Vec3(x=0.12, y=0.12, z=0.12), color="#1a1e2a", label="Input bearing"),
            ModelPrimitive(shape="sphere", position=Vec3(x=0.2, y=0, z=0), scale=Vec3(x=0.12, y=0.12, z=0.12), color="#1a1e2a", label="Output bearing"),
        ],
        camera_distance=5.0,
        urdf_path="/models/robot_arm/robot_arm.urdf",
    )


def _generic_model(prompt: str) -> ConceptModel:
    return ConceptModel(
        primitives=[
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0, z=0), scale=Vec3(x=1.5, y=0.15, z=1.0), color="#64748b", label="Base platform"),
            ModelPrimitive(shape="box", position=Vec3(x=0, y=0.5, z=0), scale=Vec3(x=1.0, y=0.7, z=0.8), color="#6366f1", label="Main body"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=1.1, z=0), scale=Vec3(x=0.3, y=0.3, z=0.3), color="#8b5cf6", label="Top module"),
            ModelPrimitive(shape="box", position=Vec3(x=-0.6, y=0.3, z=0), scale=Vec3(x=0.2, y=0.4, z=0.3), color="#06b6d4", label="Left component"),
            ModelPrimitive(shape="box", position=Vec3(x=0.6, y=0.3, z=0), scale=Vec3(x=0.2, y=0.4, z=0.3), color="#10b981", label="Right component"),
            ModelPrimitive(shape="cylinder", position=Vec3(x=0, y=0.5, z=0.5), scale=Vec3(x=0.06, y=0.15, z=0.06), color="#f59e0b", label="Connector"),
        ],
        camera_distance=5.0,
    )
