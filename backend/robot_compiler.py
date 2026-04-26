"""Procedural Robot Compiler — generative architecture engine.

CRITICAL RULE: Always preserve the identity of the input concept.
"Baymax" must stay a soft inflatable humanoid healthcare robot.
"Robot dog" must stay a quadruped. Variation only in proportions,
joint placement, surface detail, material style — never core form.

1. Named concept matching → fixed archetype identity
2. Structural variation (±10-20% proportions only)
3. Dynamic URDF with seeded randomness
4. Geometry abstraction (capsules preferred over cylinders)
5. X-ray internal structure
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
from typing import Optional

from backend.schemas import (
    ConceptParse,
    GeometryRule,
    RobotArchitecture,
    Vec3,
    XRayComponent,
)

logger = logging.getLogger("reality_compiler.robot_compiler")


# ---------------------------------------------------------------------------
# 1. Concept Parsing — IDENTITY PRESERVATION IS CRITICAL
# ---------------------------------------------------------------------------

# Named concept map: these are the canonical identities.
# When a user says "Baymax", the output MUST be a soft inflatable humanoid.
# Variation is ONLY allowed in proportions/joints/materials, never core form.

_NAMED_CONCEPTS = {
    # Healthcare / companion humanoids
    "baymax": {"morphology": "humanoid", "function_role": "medical", "visual_style": "soft", "character": "baymax", "base_archetype": "Soft inflatable humanoid healthcare robot", "style_modifiers": ["soft", "round_body", "inflatable_vinyl", "white", "friendly_face"]},
    "pepper": {"morphology": "humanoid", "function_role": "companion", "visual_style": "sleek", "base_archetype": "Social humanoid companion robot", "style_modifiers": ["sleek", "white_plastic", "tablet_chest", "wheeled_base"]},
    "nao": {"morphology": "humanoid", "function_role": "education", "visual_style": "sleek", "base_archetype": "Small bipedal education robot", "style_modifiers": ["compact", "colorful", "walking_biped"]},
    "atlas": {"morphology": "humanoid", "function_role": "exploration", "visual_style": "rugged", "base_archetype": "Heavy-duty bipedal dynamic robot", "style_modifiers": ["rugged", "hydraulic", "high_mobility"]},

    # Quadrupeds
    "spot": {"morphology": "quadruped", "function_role": "exploration", "visual_style": "mechanical", "base_archetype": "Agile quadruped inspection robot like Boston Dynamics Spot", "style_modifiers": ["mechanical", "yellow_body", "sensor_head"]},
    "robot dog": {"morphology": "quadruped", "function_role": "companion", "visual_style": "mechanical", "base_archetype": "Quadruped mechanical animal robot", "style_modifiers": ["mechanical", "dog_proportions", "4_legs"]},
    "dog robot": {"morphology": "quadruped", "function_role": "companion", "visual_style": "mechanical", "base_archetype": "Quadruped mechanical animal robot", "style_modifiers": ["mechanical", "dog_proportions", "4_legs"]},

    # Arms
    "lucid": {"morphology": "articulated_arm", "function_role": "lab", "visual_style": "sleek", "base_archetype": "Lucid-1 style 7-DOF articulated arm", "style_modifiers": ["sleek", "anodized_aluminum", "high_precision"]},
    "cobot": {"morphology": "articulated_arm", "function_role": "industrial", "visual_style": "sleek", "base_archetype": "Collaborative industrial robot arm", "style_modifiers": ["sleek", "rounded_joints", "force_limited"]},
    "ur5": {"morphology": "articulated_arm", "function_role": "industrial", "visual_style": "mechanical", "base_archetype": "Universal Robots UR5 style 6-DOF arm", "style_modifiers": ["mechanical", "blue_joints", "industrial"]},

    # Hexapods
    "spider robot": {"morphology": "hexapod", "function_role": "exploration", "visual_style": "biomechanical", "base_archetype": "Six-legged spider exploration robot", "style_modifiers": ["biomechanical", "low_profile", "terrain_adaptive"]},

    # Aerials
    "racing drone": {"morphology": "aerial", "function_role": "filming", "visual_style": "sleek", "base_archetype": "High-speed racing quadcopter", "style_modifiers": ["sleek", "carbon_fiber", "lightweight"]},

    # Toy / character robots
    "labubu": {"morphology": "humanoid", "function_role": "companion", "visual_style": "soft", "character": "labubu", "base_archetype": "Labubu wind-up toy robot rabbit", "style_modifiers": ["boxy", "bunny_ears", "wind_up_key", "purple", "zigzag_teeth"]},

    # Soft robots
    "soft gripper": {"morphology": "soft_body", "function_role": "industrial", "visual_style": "soft", "base_archetype": "Pneumatic soft-body gripper", "style_modifiers": ["soft", "silicone", "pneumatic_actuation"]},
}

_MORPHOLOGY_KEYWORDS = {
    "humanoid": ["humanoid", "biped", "human", "android", "baymax", "nao", "pepper", "atlas", "walking robot", "labubu"],
    "wheeled": ["wheeled", "rover", "car", "mobile", "vehicle", "tank", "line follower"],
    "quadruped": ["quadruped", "dog", "spot", "four-leg", "4-leg", "boston dynamics", "robot dog", "puppy"],
    "hexapod": ["hexapod", "spider", "six-leg", "6-leg", "insect", "ant"],
    "articulated_arm": ["arm", "7dof", "6dof", "manipulator", "cobot", "lucid", "pick and place", "industrial arm", "robot arm"],
    "soft_body": ["soft", "inflatable", "pneumatic", "silicone", "flexible", "tentacle"],
    "aerial": ["drone", "quadcopter", "uav", "flying", "multirotor", "aerial"],
    "snake": ["snake", "serpentine", "modular chain", "worm"],
}

_FUNCTION_KEYWORDS = {
    "assistant": ["assistant", "helper", "service", "butler"],
    "medical": ["medical", "healthcare", "surgical", "rehab", "prosthetic", "nurse", "hospital"],
    "industrial": ["industrial", "factory", "manufacturing", "welding", "assembly", "cobot", "pick and place"],
    "companion": ["companion", "pet", "social", "toy", "emotional", "cute", "friend"],
    "exploration": ["exploration", "rover", "mars", "rescue", "inspection", "underwater", "search"],
    "education": ["education", "teaching", "learning", "stem", "classroom", "demo"],
    "filming": ["filming", "camera", "vlog", "gimbal", "tracking", "cinematography"],
    "lab": ["lab", "laboratory", "research", "experiment", "testing", "scientific"],
}

_STYLE_KEYWORDS = {
    "mechanical": ["mechanical", "industrial", "metal", "steel", "gear", "piston"],
    "soft": ["soft", "round", "friendly", "cute", "plush", "inflatable", "gentle"],
    "biomechanical": ["biomechanical", "organic", "alien", "exoskeleton", "biological"],
    "sleek": ["sleek", "modern", "futuristic", "minimal", "clean", "lucid"],
    "rugged": ["rugged", "military", "heavy", "armored", "tactical", "tough"],
    "minimalist": ["minimalist", "simple", "elegant", "zen"],
}


def _classify(prompt: str, keyword_map: dict[str, list[str]], default: str) -> str:
    lp = prompt.lower()
    best, best_score = default, 0
    for category, keywords in keyword_map.items():
        score = sum(1 for k in keywords if k in lp)
        if score > best_score:
            best, best_score = category, score
    return best


def _match_named_concept(prompt: str) -> dict | None:
    """Check if prompt matches a known named concept (identity preservation)."""
    lp = prompt.lower()
    best_match = None
    best_len = 0
    for name, identity in _NAMED_CONCEPTS.items():
        if name in lp and len(name) > best_len:
            best_match = identity
            best_len = len(name)
    return best_match


def parse_concept(prompt: str) -> tuple[ConceptParse, str, list[str]]:
    """Parse prompt into concept, returning (parse, base_archetype, style_modifiers).

    Named concepts get identity-locked archetypes. Generic prompts get classified.
    """
    named = _match_named_concept(prompt)

    if named:
        base_archetype = named["base_archetype"]
        style_modifiers = named["style_modifiers"]
        return ConceptParse(
            morphology=named["morphology"],
            function_role=named["function_role"],
            visual_style=named["visual_style"],
            summary=base_archetype,
        ), base_archetype, style_modifiers

    morphology = _classify(prompt, _MORPHOLOGY_KEYWORDS, "articulated_arm")
    function_role = _classify(prompt, _FUNCTION_KEYWORDS, "industrial")
    visual_style = _classify(prompt, _STYLE_KEYWORDS, "mechanical")
    base_archetype = f"{visual_style.title()} {morphology.replace('_', ' ')} for {function_role} applications"
    style_modifiers = [visual_style, morphology]

    return ConceptParse(
        morphology=morphology,
        function_role=function_role,
        visual_style=visual_style,
        summary=base_archetype,
    ), base_archetype, style_modifiers


# ---------------------------------------------------------------------------
# 2. Procedural Robot Graph — morphology templates with variation
# ---------------------------------------------------------------------------

# Each morphology defines a base part graph.
# Variation engine modifies counts, proportions, joint types per seed.

def _make_seed(prompt: str) -> int:
    return int(hashlib.md5(prompt.encode()).hexdigest(), 16) % (2**31)


def _seeded_range(rng: random.Random, base: float, variance: float) -> float:
    """Vary base value by ±variance. For identity preservation, keep variance
    at 10-20% of base so the core silhouette is recognizable."""
    return base + rng.uniform(-variance, variance)


def _arm_graph(rng: random.Random, concept: ConceptParse):
    """Generate articulated arm (5-7 DOF) with variation."""
    dof = rng.choice([5, 6, 7])
    base_w = _seeded_range(rng, 120, 30)
    link_l = _seeded_range(rng, 200, 50)
    servo_w = _seeded_range(rng, 40, 8)

    parts = [
        {"name": "base_plate", "type": "base", "joint": "fixed", "dims_mm": (base_w, 8, base_w), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 250},
        {"name": "turntable", "type": "plate", "joint": "revolute", "axis": "y", "lo": -3.14, "hi": 3.14, "effort": 8.0, "velocity": 1.57, "dims_mm": (base_w * 0.8, 12, base_w * 0.8), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 120},
    ]

    for i in range(dof - 2):
        joint_name = ["shoulder", "elbow", "wrist", "wrist_roll", "wrist_pitch"][min(i, 4)]
        axis = "z" if i % 2 == 0 else "y"
        lo = _seeded_range(rng, -2.0, 1.0)
        hi = _seeded_range(rng, 2.0, 0.8)
        link_len = link_l * (1.0 - i * 0.1)
        parts.append({
            "name": f"{joint_name}_servo_{i}", "type": "servo", "joint": "fixed",
            "dims_mm": (servo_w, servo_w * 1.07, servo_w * 0.49),
            "material": "ABS + Nylon gears", "function": "actuator", "mass_g": 55,
            "equivalent": "MG996R Servo" if i < 3 else "SG90 Micro Servo",
        })
        parts.append({
            "name": f"{joint_name}_bracket_{i}", "type": "bracket", "joint": "revolute",
            "axis": axis, "lo": lo, "hi": hi, "effort": max(3, 10 - i), "velocity": 1.05 + i * 0.2,
            "dims_mm": (50, 60, 4), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 28,
        })
        if i < dof - 3:
            parts.append({
                "name": f"{joint_name}_link_{i}", "type": "link", "joint": "fixed",
                "dims_mm": (25, link_len, 12), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 35,
            })

    # End effector
    gripper_style = rng.choice(["parallel_jaw", "three_finger", "suction", "tool_mount"])
    if gripper_style == "parallel_jaw":
        parts.append({"name": "gripper_base", "type": "plate", "joint": "fixed", "dims_mm": (60, 6, 50), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 40})
        parts.append({"name": "finger_left", "type": "finger", "joint": "revolute", "axis": "z", "lo": 0, "hi": 0.78, "effort": 2, "velocity": 1.57, "dims_mm": (8, 50, 12), "material": "PLA", "function": "end_effector", "mass_g": 8})
        parts.append({"name": "finger_right", "type": "finger", "joint": "revolute", "axis": "z", "lo": -0.78, "hi": 0, "effort": 2, "velocity": 1.57, "dims_mm": (8, 50, 12), "material": "PLA", "function": "end_effector", "mass_g": 8})
    elif gripper_style == "three_finger":
        parts.append({"name": "gripper_hub", "type": "housing", "joint": "fixed", "dims_mm": (50, 30, 50), "material": "ABS", "function": "structural", "mass_g": 35})
        for j in range(3):
            angle = j * 120
            parts.append({"name": f"finger_{j}", "type": "finger", "joint": "revolute", "axis": "z", "lo": -0.5, "hi": 0.7, "effort": 1.5, "velocity": 1.57, "dims_mm": (6, 40, 10), "material": "PLA", "function": "end_effector", "mass_g": 6})
    elif gripper_style == "suction":
        parts.append({"name": "suction_mount", "type": "housing", "joint": "fixed", "dims_mm": (40, 50, 40), "material": "ABS", "function": "end_effector", "mass_g": 30})
        parts.append({"name": "suction_cup", "type": "sensor", "joint": "fixed", "dims_mm": (30, 15, 30), "material": "Shore 40A Silicone", "function": "end_effector", "mass_g": 12})
    else:
        parts.append({"name": "tool_flange", "type": "plate", "joint": "revolute", "axis": "y", "lo": -3.14, "hi": 3.14, "effort": 3, "velocity": 2.09, "dims_mm": (60, 10, 60), "material": "Stainless Steel 304", "function": "structural", "mass_g": 80})

    return parts, f"Lucid-{dof}DOF-Arm-{gripper_style.replace('_', '')}"


def _quadruped_graph(rng: random.Random, concept: ConceptParse):
    leg_len = _seeded_range(rng, 150, 40)
    body_l = _seeded_range(rng, 250, 60)
    body_w = _seeded_range(rng, 150, 40)

    parts = [
        {"name": "body_chassis", "type": "housing", "joint": "fixed", "dims_mm": (body_w, 60, body_l), "material": "Carbon fiber composite", "function": "structural", "mass_g": 400},
        {"name": "controller", "type": "pcb", "joint": "fixed", "dims_mm": (50, 2, 35), "material": "FR-4", "function": "electronics", "mass_g": 12},
        {"name": "battery", "type": "battery", "joint": "fixed", "dims_mm": (60, 20, 40), "material": "LiPo 3S", "function": "electronics", "mass_g": 120},
    ]

    leg_names = ["front_left", "front_right", "rear_left", "rear_right"]
    for leg in leg_names:
        hip_range = _seeded_range(rng, 1.2, 0.4)
        knee_range = _seeded_range(rng, 2.0, 0.5)
        parts.append({"name": f"{leg}_hip_servo", "type": "servo", "joint": "fixed", "dims_mm": (40, 43, 20), "material": "ABS + Metal gears", "function": "actuator", "mass_g": 55, "equivalent": "MG996R"})
        parts.append({"name": f"{leg}_hip", "type": "bracket", "joint": "revolute", "axis": "x", "lo": -hip_range, "hi": hip_range, "effort": 10, "velocity": 1.05, "dims_mm": (40, 50, 4), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 22})
        parts.append({"name": f"{leg}_upper", "type": "link", "joint": "fixed", "dims_mm": (20, leg_len * 0.5, 10), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 25})
        parts.append({"name": f"{leg}_knee_servo", "type": "servo", "joint": "fixed", "dims_mm": (30, 34, 16), "material": "ABS + Nylon gears", "function": "actuator", "mass_g": 35, "equivalent": "SG90"})
        parts.append({"name": f"{leg}_knee", "type": "bracket", "joint": "revolute", "axis": "z", "lo": -knee_range, "hi": 0.2, "effort": 6, "velocity": 1.57, "dims_mm": (35, 45, 3), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 18})
        parts.append({"name": f"{leg}_lower", "type": "link", "joint": "fixed", "dims_mm": (15, leg_len * 0.5, 8), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 20})
        parts.append({"name": f"{leg}_foot", "type": "sensor", "joint": "fixed", "dims_mm": (20, 8, 20), "material": "Shore 60A rubber", "function": "end_effector", "mass_g": 10})

    if rng.random() > 0.3:
        parts.append({"name": "head_camera", "type": "sensor", "joint": "revolute", "axis": "y", "lo": -1.57, "hi": 1.57, "effort": 0.5, "velocity": 3.14, "dims_mm": (25, 18, 25), "material": "ABS", "function": "sensor", "mass_g": 15, "equivalent": "OV5647 camera module"})

    return parts, f"QuadBot-{int(leg_len)}-{concept.visual_style}"


def _hexapod_graph(rng: random.Random, concept: ConceptParse):
    leg_len = _seeded_range(rng, 120, 30)
    body_r = _seeded_range(rng, 100, 25)

    parts = [
        {"name": "body_plate", "type": "base", "joint": "fixed", "dims_mm": (body_r * 2, 10, body_r * 2), "material": "Carbon fiber composite", "function": "structural", "mass_g": 300},
        {"name": "controller", "type": "pcb", "joint": "fixed", "dims_mm": (50, 2, 35), "material": "FR-4", "function": "electronics", "mass_g": 12},
    ]

    for i in range(6):
        angle = i * 60
        prefix = f"leg_{i}"
        coxa_range = _seeded_range(rng, 0.8, 0.3)
        femur_range = _seeded_range(rng, 1.5, 0.4)
        tibia_range = _seeded_range(rng, 2.0, 0.5)
        parts.append({"name": f"{prefix}_coxa_servo", "type": "servo", "joint": "fixed", "dims_mm": (30, 34, 16), "material": "ABS", "function": "actuator", "mass_g": 35})
        parts.append({"name": f"{prefix}_coxa", "type": "bracket", "joint": "revolute", "axis": "y", "lo": -coxa_range, "hi": coxa_range, "effort": 4, "velocity": 1.57, "dims_mm": (25, 35, 3), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 12})
        parts.append({"name": f"{prefix}_femur", "type": "link", "joint": "revolute", "axis": "z", "lo": -femur_range, "hi": 0.3, "effort": 4, "velocity": 1.57, "dims_mm": (15, leg_len * 0.45, 8), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 18})
        parts.append({"name": f"{prefix}_tibia", "type": "link", "joint": "revolute", "axis": "z", "lo": -tibia_range, "hi": 0.1, "effort": 3, "velocity": 2.09, "dims_mm": (12, leg_len * 0.55, 6), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 15})
        parts.append({"name": f"{prefix}_foot", "type": "sensor", "joint": "fixed", "dims_mm": (15, 5, 15), "material": "Shore 60A rubber", "function": "end_effector", "mass_g": 5})

    return parts, f"HexaCrawler-{int(body_r * 2)}"


def _humanoid_graph(rng: random.Random, concept: ConceptParse):
    torso_h = _seeded_range(rng, 200, 50)
    arm_l = _seeded_range(rng, 180, 40)
    head_d = _seeded_range(rng, 100, 25)

    parts = [
        {"name": "hip_base", "type": "base", "joint": "fixed", "dims_mm": (120, 15, 80), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 200},
        {"name": "torso", "type": "housing", "joint": "revolute", "axis": "y", "lo": -0.5, "hi": 0.5, "effort": 15, "velocity": 0.5, "dims_mm": (100, torso_h, 60), "material": "ABS", "function": "structural", "mass_g": 350},
        {"name": "head", "type": "housing", "joint": "revolute", "axis": "y", "lo": -2.0, "hi": 2.0, "effort": 2, "velocity": 3.14, "dims_mm": (head_d, head_d, head_d * 0.8), "material": "ABS", "function": "structural", "mass_g": 80},
        {"name": "head_camera", "type": "sensor", "joint": "revolute", "axis": "x", "lo": -0.5, "hi": 0.8, "effort": 0.5, "velocity": 1.57, "dims_mm": (30, 20, 15), "material": "ABS", "function": "sensor", "mass_g": 15},
    ]

    for side in ["left", "right"]:
        parts.append({"name": f"{side}_shoulder_servo", "type": "servo", "joint": "fixed", "dims_mm": (40, 43, 20), "material": "ABS", "function": "actuator", "mass_g": 55})
        parts.append({"name": f"{side}_shoulder", "type": "bracket", "joint": "revolute", "axis": "x", "lo": -1.57, "hi": 3.14, "effort": 10, "velocity": 1.05, "dims_mm": (45, 55, 4), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 28})
        parts.append({"name": f"{side}_upper_arm", "type": "link", "joint": "fixed", "dims_mm": (25, arm_l * 0.5, 12), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 35})
        parts.append({"name": f"{side}_elbow_servo", "type": "servo", "joint": "fixed", "dims_mm": (35, 38, 18), "material": "ABS", "function": "actuator", "mass_g": 45})
        parts.append({"name": f"{side}_elbow", "type": "bracket", "joint": "revolute", "axis": "z", "lo": -2.35, "hi": 0, "effort": 6, "velocity": 1.57, "dims_mm": (40, 50, 4), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 22})
        parts.append({"name": f"{side}_forearm", "type": "link", "joint": "fixed", "dims_mm": (20, arm_l * 0.45, 10), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 28})
        parts.append({"name": f"{side}_hand", "type": "finger", "joint": "revolute", "axis": "z", "lo": -0.5, "hi": 0.8, "effort": 2, "velocity": 1.57, "dims_mm": (30, 50, 20), "material": "PLA", "function": "end_effector", "mass_g": 25})

    parts.append({"name": "controller", "type": "pcb", "joint": "fixed", "dims_mm": (60, 2, 40), "material": "FR-4", "function": "electronics", "mass_g": 15})
    parts.append({"name": "battery", "type": "battery", "joint": "fixed", "dims_mm": (80, 25, 50), "material": "LiPo 4S", "function": "electronics", "mass_g": 200})

    return parts, f"HumanoidBot-{concept.function_role}-{int(torso_h)}"


def _aerial_graph(rng: random.Random, concept: ConceptParse):
    arm_count = rng.choice([4, 6, 8])
    arm_len = _seeded_range(rng, 100, 30)
    body_w = _seeded_range(rng, 80, 20)

    parts = [
        {"name": "body", "type": "housing", "joint": "fixed", "dims_mm": (body_w, 40, body_w), "material": "Carbon fiber composite", "function": "structural", "mass_g": 150},
        {"name": "controller", "type": "pcb", "joint": "fixed", "dims_mm": (50, 2, 35), "material": "FR-4", "function": "electronics", "mass_g": 12},
        {"name": "battery", "type": "battery", "joint": "fixed", "dims_mm": (50, 15, 30), "material": "LiPo 3S 1000mAh", "function": "electronics", "mass_g": 85},
    ]

    for i in range(arm_count):
        angle = i * (360 / arm_count)
        parts.append({"name": f"arm_{i}", "type": "link", "joint": "fixed", "dims_mm": (15, arm_len, 8), "material": "Carbon fiber tube", "function": "structural", "mass_g": 12})
        parts.append({"name": f"motor_{i}", "type": "motor", "joint": "fixed", "dims_mm": (28, 15, 28), "material": "Neodymium + copper windings", "function": "actuator", "mass_g": 30, "equivalent": f"2204 1400KV brushless"})
        parts.append({"name": f"prop_{i}", "type": "propeller", "joint": "continuous", "axis": "y", "effort": 0.5, "velocity": 1047.2, "dims_mm": (120, 2, 6), "material": "Glass-filled nylon", "function": "end_effector", "mass_g": 4})

    if rng.random() > 0.4:
        parts.append({"name": "camera_gimbal", "type": "bracket", "joint": "revolute", "axis": "x", "lo": -1.57, "hi": 0.5, "effort": 0.5, "velocity": 3.14, "dims_mm": (30, 25, 30), "material": "6061-T6 Aluminum", "function": "structural", "mass_g": 25})
        parts.append({"name": "camera", "type": "sensor", "joint": "fixed", "dims_mm": (25, 18, 25), "material": "ABS", "function": "sensor", "mass_g": 15})

    name_prefix = {4: "Quad", 6: "Hex", 8: "Octo"}
    return parts, f"{name_prefix.get(arm_count, 'Multi')}Rotor-{int(arm_len * 2)}mm"


def _wheeled_graph(rng: random.Random, concept: ConceptParse):
    wheel_count = rng.choice([2, 4, 6])
    chassis_l = _seeded_range(rng, 200, 60)
    chassis_w = _seeded_range(rng, 150, 40)
    wheel_r = _seeded_range(rng, 35, 15)

    parts = [
        {"name": "chassis", "type": "housing", "joint": "fixed", "dims_mm": (chassis_w, 50, chassis_l), "material": "ABS", "function": "structural", "mass_g": 250},
        {"name": "controller", "type": "pcb", "joint": "fixed", "dims_mm": (50, 2, 35), "material": "FR-4", "function": "electronics", "mass_g": 12},
        {"name": "battery", "type": "battery", "joint": "fixed", "dims_mm": (60, 20, 40), "material": "LiPo 2S", "function": "electronics", "mass_g": 80},
    ]

    positions = ["front_left", "front_right", "rear_left", "rear_right", "mid_left", "mid_right"]
    for i in range(wheel_count):
        wn = positions[i]
        parts.append({"name": f"{wn}_motor", "type": "motor", "joint": "fixed", "dims_mm": (25, 30, 25), "material": "Steel + copper", "function": "actuator", "mass_g": 40, "equivalent": "N20 DC gearmotor"})
        parts.append({"name": f"{wn}_wheel", "type": "wheel", "joint": "continuous", "axis": "z", "effort": 2, "velocity": 10.47, "dims_mm": (wheel_r * 2, 15, wheel_r * 2), "material": "Shore 60A rubber tire, aluminum hub", "function": "end_effector", "mass_g": 25})

    if rng.random() > 0.3:
        parts.append({"name": "ultrasonic_sensor", "type": "sensor", "joint": "revolute", "axis": "y", "lo": -1.0, "hi": 1.0, "effort": 0.2, "velocity": 3.14, "dims_mm": (20, 15, 15), "material": "ABS", "function": "sensor", "mass_g": 8, "equivalent": "HC-SR04"})

    return parts, f"Rover-{wheel_count}WD-{int(chassis_l)}mm"


def _snake_graph(rng: random.Random, concept: ConceptParse):
    segments = rng.randint(6, 12)
    seg_len = _seeded_range(rng, 40, 10)

    parts = [
        {"name": "head", "type": "housing", "joint": "fixed", "dims_mm": (35, 25, 45), "material": "ABS", "function": "structural", "mass_g": 30},
        {"name": "head_camera", "type": "sensor", "joint": "fixed", "dims_mm": (15, 10, 15), "material": "ABS", "function": "sensor", "mass_g": 8},
    ]

    for i in range(segments):
        axis = "y" if i % 2 == 0 else "z"
        parts.append({"name": f"seg_{i}_servo", "type": "servo", "joint": "fixed", "dims_mm": (25, 28, 14), "material": "ABS", "function": "actuator", "mass_g": 30, "equivalent": "SG90"})
        parts.append({"name": f"seg_{i}_body", "type": "link", "joint": "revolute", "axis": axis, "lo": -0.8, "hi": 0.8, "effort": 2, "velocity": 2.09, "dims_mm": (25, seg_len, 25), "material": "PLA", "function": "structural", "mass_g": 15})

    parts.append({"name": "tail", "type": "sensor", "joint": "fixed", "dims_mm": (20, 15, 20), "material": "ABS", "function": "structural", "mass_g": 10})
    return parts, f"SnakeBot-{segments}seg"


def _soft_body_graph(rng: random.Random, concept: ConceptParse):
    chamber_count = rng.randint(3, 6)
    body_h = _seeded_range(rng, 150, 40)

    parts = [
        {"name": "base_frame", "type": "base", "joint": "fixed", "dims_mm": (80, 10, 80), "material": "PLA", "function": "structural", "mass_g": 60},
        {"name": "controller", "type": "pcb", "joint": "fixed", "dims_mm": (40, 2, 30), "material": "FR-4", "function": "electronics", "mass_g": 10},
    ]

    for i in range(chamber_count):
        parts.append({"name": f"chamber_{i}", "type": "housing", "joint": "revolute", "axis": "z" if i % 2 == 0 else "x", "lo": -0.6, "hi": 0.6, "effort": 1, "velocity": 0.5, "dims_mm": (40, body_h / chamber_count, 40), "material": "Shore 30A Silicone", "function": "structural", "mass_g": 20})
        parts.append({"name": f"valve_{i}", "type": "sensor", "joint": "fixed", "dims_mm": (10, 8, 10), "material": "ABS", "function": "actuator", "mass_g": 5, "equivalent": "Pneumatic solenoid valve"})

    parts.append({"name": "tip_sensor", "type": "sensor", "joint": "fixed", "dims_mm": (25, 15, 25), "material": "Shore 20A Silicone", "function": "sensor", "mass_g": 8})
    return parts, f"SoftGripper-{chamber_count}ch"


def _baymax_graph(rng: random.Random, concept: ConceptParse):
    """Baymax-specific graph: inflatable balloon humanoid healthcare robot."""
    torso_w = _seeded_range(rng, 180, 20)
    torso_h = _seeded_range(rng, 240, 30)
    head_w = _seeded_range(rng, 100, 10)
    arm_h = _seeded_range(rng, 160, 20)
    leg_h = _seeded_range(rng, 100, 15)

    parts = [
        {"name": "hip_base", "type": "baymax_foot", "joint": "fixed", "dims_mm": (80, 30, 100), "material": "Inflatable vinyl", "function": "structural", "mass_g": 50},
        {"name": "torso", "type": "baymax_torso", "joint": "revolute", "axis": "y", "lo": -0.3, "hi": 0.3, "effort": 12, "velocity": 0.5, "dims_mm": (torso_w, torso_h, torso_w * 0.9), "material": "Inflatable vinyl", "function": "structural", "mass_g": 800},
        {"name": "head", "type": "baymax_head", "joint": "revolute", "axis": "y", "lo": -1.5, "hi": 1.5, "effort": 2, "velocity": 2.0, "dims_mm": (head_w, head_w * 0.8, head_w * 0.9), "material": "Inflatable vinyl + OLED eyes", "function": "structural", "mass_g": 120},
        {"name": "head_camera", "type": "sensor", "joint": "revolute", "axis": "x", "lo": -0.5, "hi": 0.8, "effort": 0.5, "velocity": 1.57, "dims_mm": (30, 20, 15), "material": "ABS", "function": "sensor", "mass_g": 15},
    ]

    for side in ["left", "right"]:
        parts.append({"name": f"{side}_shoulder_servo", "type": "servo", "joint": "fixed", "dims_mm": (40, 43, 20), "material": "ABS", "function": "actuator", "mass_g": 55})
        parts.append({"name": f"{side}_upper_arm", "type": "baymax_arm", "joint": "revolute", "axis": "x", "lo": -1.57, "hi": 3.14, "effort": 8, "velocity": 1.05, "dims_mm": (60, arm_h, 60), "material": "Inflatable vinyl", "function": "structural", "mass_g": 100})
        parts.append({"name": f"{side}_elbow_servo", "type": "servo", "joint": "fixed", "dims_mm": (30, 32, 16), "material": "ABS", "function": "actuator", "mass_g": 35})
        parts.append({"name": f"{side}_forearm", "type": "baymax_arm", "joint": "revolute", "axis": "z", "lo": -2.0, "hi": 0, "effort": 5, "velocity": 1.57, "dims_mm": (55, arm_h * 0.75, 55), "material": "Inflatable vinyl", "function": "structural", "mass_g": 80})
        parts.append({"name": f"{side}_hand", "type": "baymax_hand", "joint": "revolute", "axis": "z", "lo": -0.5, "hi": 0.8, "effort": 2, "velocity": 1.57, "dims_mm": (50, 40, 50), "material": "Inflatable vinyl", "function": "end_effector", "mass_g": 40})

    for side in ["left", "right"]:
        parts.append({"name": f"{side}_leg", "type": "baymax_leg", "joint": "revolute", "axis": "x", "lo": -0.8, "hi": 0.8, "effort": 15, "velocity": 0.8, "dims_mm": (70, leg_h, 70), "material": "Inflatable vinyl", "function": "structural", "mass_g": 150})
        parts.append({"name": f"{side}_foot", "type": "baymax_foot", "joint": "revolute", "axis": "x", "lo": -0.3, "hi": 0.5, "effort": 8, "velocity": 1.0, "dims_mm": (60, 30, 80), "material": "Inflatable vinyl", "function": "structural", "mass_g": 50})

    parts.append({"name": "controller", "type": "pcb", "joint": "fixed", "dims_mm": (60, 2, 40), "material": "FR-4", "function": "electronics", "mass_g": 15})
    parts.append({"name": "battery", "type": "battery", "joint": "fixed", "dims_mm": (80, 25, 50), "material": "LiPo 4S", "function": "electronics", "mass_g": 200})

    return parts, f"Baymax-Healthcare-{int(torso_h)}"


def _labubu_graph(rng: random.Random, concept: ConceptParse):
    """Labubu-specific graph: boxy wind-up toy robot rabbit."""
    body_w = _seeded_range(rng, 60, 6)
    upper_h = _seeded_range(rng, 55, 5)
    lower_h = _seeded_range(rng, 50, 5)
    ear_h = _seeded_range(rng, 40, 4)

    parts = [
        {"name": "left_foot", "type": "labubu_foot", "joint": "fixed", "dims_mm": (25, 15, 30), "material": "ABS plastic (red)", "function": "structural", "mass_g": 10},
        {"name": "right_foot", "type": "labubu_foot", "joint": "fixed", "dims_mm": (25, 15, 30), "material": "ABS plastic (red)", "function": "structural", "mass_g": 10},
        {"name": "body_lower", "type": "labubu_body_lower", "joint": "fixed", "dims_mm": (body_w, lower_h, body_w * 0.83), "material": "ABS plastic (purple)", "function": "structural", "mass_g": 40},
        {"name": "body_upper", "type": "labubu_body_upper", "joint": "revolute", "axis": "y", "lo": -0.3, "hi": 0.3, "effort": 1, "velocity": 1.0, "dims_mm": (body_w, upper_h, body_w * 0.83), "material": "ABS plastic (purple)", "function": "structural", "mass_g": 45},
        {"name": "left_ear", "type": "labubu_ear", "joint": "revolute", "axis": "x", "lo": -0.2, "hi": 0.2, "effort": 0.3, "velocity": 2.0, "dims_mm": (12, ear_h, 5), "material": "ABS plastic (purple)", "function": "structural", "mass_g": 5},
        {"name": "right_ear", "type": "labubu_ear", "joint": "revolute", "axis": "x", "lo": -0.2, "hi": 0.2, "effort": 0.3, "velocity": 2.0, "dims_mm": (12, ear_h, 5), "material": "ABS plastic (purple)", "function": "structural", "mass_g": 5},
        {"name": "left_arm", "type": "labubu_arm", "joint": "revolute", "axis": "z", "lo": -1.0, "hi": 1.0, "effort": 0.5, "velocity": 1.5, "dims_mm": (12, 30, 10), "material": "ABS plastic (red)", "function": "end_effector", "mass_g": 5},
        {"name": "right_arm", "type": "labubu_arm", "joint": "revolute", "axis": "z", "lo": -1.0, "hi": 1.0, "effort": 0.5, "velocity": 1.5, "dims_mm": (12, 30, 10), "material": "ABS plastic (red)", "function": "end_effector", "mass_g": 5},
        {"name": "wind_up_key", "type": "labubu_key", "joint": "continuous", "axis": "z", "effort": 0.2, "velocity": 6.28, "dims_mm": (20, 25, 4), "material": "Die-cast zinc alloy (gold)", "function": "actuator", "mass_g": 8},
        {"name": "spring_motor", "type": "spring", "joint": "fixed", "dims_mm": (15, 20, 15), "material": "Spring steel", "function": "actuator", "mass_g": 12},
    ]

    return parts, f"Labubu-ToyBot-{int(body_w)}"


_GRAPH_BUILDERS = {
    "articulated_arm": _arm_graph,
    "quadruped": _quadruped_graph,
    "hexapod": _hexapod_graph,
    "humanoid": _humanoid_graph,
    "aerial": _aerial_graph,
    "wheeled": _wheeled_graph,
    "snake": _snake_graph,
    "soft_body": _soft_body_graph,
}

# Character-specific graph builders override morphology-based routing
_CHARACTER_BUILDERS = {
    "baymax": _baymax_graph,
    "labubu": _labubu_graph,
}


# ---------------------------------------------------------------------------
# 3. Geometry rules + X-ray generation
# ---------------------------------------------------------------------------

_PRIM_MAP = {
    "servo": "capsule", "motor": "cylinder", "bracket": "capsule", "link": "capsule",
    "base": "box", "plate": "cylinder", "finger": "capsule", "propeller": "box",
    "wheel": "cylinder", "gear": "cylinder", "pcb": "box", "controller": "box",
    "housing": "capsule", "sensor": "sphere", "battery": "box",
    "baymax_torso": "sphere", "baymax_head": "sphere", "baymax_arm": "capsule",
    "baymax_hand": "sphere", "baymax_leg": "capsule", "baymax_foot": "sphere",
    "labubu_body_upper": "box", "labubu_body_lower": "box", "labubu_ear": "box",
    "labubu_foot": "box", "labubu_arm": "capsule", "labubu_key": "cylinder",
}

_ROLE_MAP = {
    "actuator": "actuator", "structural": "body", "sensor": "sensor",
    "end_effector": "gripper", "electronics": "shell",
}


def _build_geometry_rules(parts: list[dict], rng: random.Random) -> list[dict]:
    rules = []
    y_pos = 0.0
    for p in parts:
        dims = p.get("dims_mm", (50, 50, 50))
        prim = _PRIM_MAP.get(p["type"], "box")
        scale_x = dims[0] / 50.0
        scale_y = dims[1] / 50.0
        scale_z = dims[2] / 50.0
        role = _ROLE_MAP.get(p.get("function", ""), "body")
        y_step = dims[1] / 1000.0
        y_pos += y_step * 0.5
        rules.append({
            "primitive": prim,
            "scale": {"x": scale_x, "y": scale_y, "z": scale_z},
            "position": {"x": rng.uniform(-0.01, 0.01), "y": round(y_pos, 4), "z": 0},
            "rotation": {"x": 0, "y": 0, "z": 0},
            "material": p.get("material", ""),
            "role": role,
        })
        y_pos += y_step * 0.5
    return rules


def _build_xray(parts: list[dict]) -> list[dict]:
    xray = []
    fn_to_cat = {
        "actuator": "motor", "structural": "structural_frame",
        "sensor": "sensor", "end_effector": "joint",
        "electronics": "controller",
    }
    y = 0.0
    for p in parts:
        dims = p.get("dims_mm", (50, 50, 50))
        fn = p.get("function", "structural")
        cat = fn_to_cat.get(fn, "structural_frame")
        if fn == "electronics" and "batter" in p["name"]:
            cat = "power"
        y += dims[1] / 2000.0
        xray.append({
            "name": p["name"],
            "category": cat,
            "position": {"x": 0, "y": round(y, 4), "z": 0},
            "description": p.get("equivalent", f"{p.get('material', '')} {p['type']}"),
        })
        y += dims[1] / 2000.0
    return xray


# ---------------------------------------------------------------------------
# 4. Public API
# ---------------------------------------------------------------------------

def compile_robot(prompt: str) -> tuple[RobotArchitecture, list[dict]]:
    """Main entry: concept prompt → full robot architecture.

    Identity preservation: named concepts (Baymax, Spot, etc.) lock to
    fixed archetypes. Variation is ±10-20% proportions only, never core form.
    """
    concept, base_archetype, style_modifiers = parse_concept(prompt)
    seed = _make_seed(prompt)
    rng = random.Random(seed)

    # Character-specific builders override morphology-based routing
    named = _match_named_concept(prompt)
    character = named.get("character") if named else None
    if character and character in _CHARACTER_BUILDERS:
        builder = _CHARACTER_BUILDERS[character]
    else:
        builder = _GRAPH_BUILDERS.get(concept.morphology, _arm_graph)
    parts, robot_class = builder(rng, concept)

    geometry_rules = _build_geometry_rules(parts, rng)
    xray = _build_xray(parts)

    logger.info(
        "Robot compiled: class=%s archetype=%s morphology=%s parts=%d seed=%d",
        robot_class, base_archetype, concept.morphology, len(parts), seed,
    )

    return RobotArchitecture(
        concept_parse=concept,
        robot_class=robot_class,
        variation_seed=seed,
        base_archetype=base_archetype,
        style_modifiers=style_modifiers,
        parametric_geometry_rules=[GeometryRule(**r) for r in geometry_rules],
        xray_internal_structure=[XRayComponent(**x) for x in xray],
    ), parts
