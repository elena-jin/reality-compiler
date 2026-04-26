"""Procedural Robot Compiler — generative architecture engine.

Converts any concept prompt into a unique robotic design with:
1. Concept parsing (morphology, function, visual style)
2. Procedural graph generation with variation
3. Dynamic URDF with seeded randomness
4. Geometry abstraction rules
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
# 1. Concept Parsing Layer
# ---------------------------------------------------------------------------

_MORPHOLOGY_KEYWORDS = {
    "humanoid": ["humanoid", "biped", "human", "android", "baymax", "nao", "pepper"],
    "wheeled": ["wheeled", "rover", "car", "mobile", "vehicle", "tank", "line follower"],
    "quadruped": ["quadruped", "dog", "spot", "four-leg", "4-leg", "walking", "boston dynamics"],
    "hexapod": ["hexapod", "spider", "six-leg", "6-leg", "insect", "ant"],
    "articulated_arm": ["arm", "7dof", "6dof", "manipulator", "cobot", "lucid", "pick and place", "industrial arm", "robot arm"],
    "soft_body": ["soft", "inflatable", "pneumatic", "silicone", "flexible", "tentacle"],
    "aerial": ["drone", "quadcopter", "uav", "flying", "multirotor", "aerial"],
    "snake": ["snake", "serpentine", "modular chain", "worm"],
}

_FUNCTION_KEYWORDS = {
    "assistant": ["assistant", "helper", "companion", "service", "butler"],
    "medical": ["medical", "healthcare", "surgical", "rehab", "prosthetic", "baymax"],
    "industrial": ["industrial", "factory", "manufacturing", "welding", "assembly", "cobot", "pick and place"],
    "companion": ["companion", "pet", "social", "toy", "emotional", "cute"],
    "exploration": ["exploration", "rover", "mars", "rescue", "inspection", "underwater"],
    "education": ["education", "teaching", "learning", "stem", "classroom", "demo"],
    "filming": ["filming", "camera", "vlog", "gimbal", "tracking", "cinematography"],
    "lab": ["lab", "laboratory", "research", "experiment", "testing", "scientific"],
}

_STYLE_KEYWORDS = {
    "mechanical": ["mechanical", "industrial", "metal", "steel", "gear", "piston"],
    "soft": ["soft", "round", "friendly", "cute", "plush", "inflatable"],
    "biomechanical": ["biomechanical", "organic", "alien", "exoskeleton", "biological"],
    "sleek": ["sleek", "modern", "futuristic", "minimal", "clean", "lucid"],
    "rugged": ["rugged", "military", "heavy", "armored", "tactical", "tough"],
    "minimalist": ["minimalist", "simple", "elegant", "minimal", "zen"],
}


def _classify(prompt: str, keyword_map: dict[str, list[str]], default: str) -> str:
    lp = prompt.lower()
    best, best_score = default, 0
    for category, keywords in keyword_map.items():
        score = sum(1 for k in keywords if k in lp)
        if score > best_score:
            best, best_score = category, score
    return best


def parse_concept(prompt: str) -> ConceptParse:
    morphology = _classify(prompt, _MORPHOLOGY_KEYWORDS, "articulated_arm")
    function_role = _classify(prompt, _FUNCTION_KEYWORDS, "industrial")
    visual_style = _classify(prompt, _STYLE_KEYWORDS, "mechanical")

    summary = f"{visual_style.title()} {morphology.replace('_', ' ')} for {function_role} applications"
    return ConceptParse(
        morphology=morphology,
        function_role=function_role,
        visual_style=visual_style,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# 2. Procedural Robot Graph — morphology templates with variation
# ---------------------------------------------------------------------------

# Each morphology defines a base part graph.
# Variation engine modifies counts, proportions, joint types per seed.

def _make_seed(prompt: str) -> int:
    return int(hashlib.md5(prompt.encode()).hexdigest(), 16) % (2**31)


def _seeded_range(rng: random.Random, base: float, variance: float) -> float:
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


# ---------------------------------------------------------------------------
# 3. Geometry rules + X-ray generation
# ---------------------------------------------------------------------------

_PRIM_MAP = {
    "servo": "box", "motor": "cylinder", "bracket": "box", "link": "capsule",
    "base": "box", "plate": "cylinder", "finger": "box", "propeller": "box",
    "wheel": "cylinder", "gear": "cylinder", "pcb": "box", "controller": "box",
    "housing": "box", "sensor": "sphere", "battery": "box",
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

def compile_robot(prompt: str) -> RobotArchitecture:
    """Main entry: concept prompt → full robot architecture."""
    concept = parse_concept(prompt)
    seed = _make_seed(prompt)
    rng = random.Random(seed)

    builder = _GRAPH_BUILDERS.get(concept.morphology, _arm_graph)
    parts, robot_class = builder(rng, concept)

    geometry_rules = _build_geometry_rules(parts, rng)
    xray = _build_xray(parts)

    logger.info(
        "Robot compiled: class=%s morphology=%s parts=%d seed=%d",
        robot_class, concept.morphology, len(parts), seed,
    )

    return RobotArchitecture(
        concept_parse=concept,
        robot_class=robot_class,
        variation_seed=seed,
        parametric_geometry_rules=[GeometryRule(**r) for r in geometry_rules],
        xray_internal_structure=[XRayComponent(**x) for x in xray],
    ), parts
