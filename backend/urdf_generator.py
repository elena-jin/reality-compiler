"""Dynamic URDF + STL generator.

Generates realistic STL meshes and URDF kinematic chains on-the-fly
for any product prompt. Uses trimesh for geometry generation.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
import trimesh

logger = logging.getLogger("reality_compiler.urdf_generator")

MODELS_DIR = Path(__file__).parent.parent / "models" / "_generated"


def _concat(meshes: list) -> trimesh.Trimesh:
    return trimesh.util.concatenate(meshes)


# ---------------------------------------------------------------------------
# Part generators: produce trimesh objects for common hardware components
# ---------------------------------------------------------------------------

def _servo_motor(w=0.040, h=0.040, d=0.020):
    body = trimesh.creation.box((w, h, d))
    shaft = trimesh.creation.cylinder(radius=0.006, height=0.006, sections=32)
    shaft.apply_translation([0, h / 2 + 0.003, 0])
    horn = trimesh.creation.cylinder(radius=0.012, height=0.002, sections=32)
    horn.apply_translation([0, h / 2 + 0.007, 0])
    return _concat([body, shaft, horn])


def _bracket_u(w=0.050, h=0.060, d=0.004, flange=0.015):
    back = trimesh.creation.box((w, h, d))
    left = trimesh.creation.box((d, h, flange))
    left.apply_translation([-(w / 2 - d / 2), 0, flange / 2 + d / 2])
    right = trimesh.creation.box((d, h, flange))
    right.apply_translation([(w / 2 - d / 2), 0, flange / 2 + d / 2])
    return _concat([back, left, right])


def _cylinder_part(r=0.015, h=0.030):
    return trimesh.creation.cylinder(radius=r, height=h, sections=32)


def _box_part(w=0.050, h=0.050, d=0.050):
    return trimesh.creation.box((w, h, d))


def _plate(w=0.10, h=0.006, d=0.10):
    plate = trimesh.creation.box((w, h, d))
    hub = trimesh.creation.cylinder(radius=0.018, height=0.008, sections=32)
    hub.apply_translation([0, h / 2 + 0.004, 0])
    return _concat([plate, hub])


def _arm_link(length=0.10, w=0.025, d=0.012):
    body = trimesh.creation.box((w, length, d))
    cap_top = trimesh.creation.cylinder(radius=w / 2, height=d, sections=32)
    cap_top.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    cap_top.apply_translation([0, length / 2, 0])
    cap_bot = trimesh.creation.cylinder(radius=w / 2, height=d, sections=32)
    cap_bot.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    cap_bot.apply_translation([0, -length / 2, 0])
    return _concat([body, cap_top, cap_bot])


def _finger(length=0.045, w=0.008, d=0.012, teeth=3):
    body = trimesh.creation.box((w, length, d))
    tip = trimesh.creation.box((w * 0.7, 0.006, d * 0.8))
    tip.apply_translation([0, length / 2 + 0.003, 0])
    parts = [body, tip]
    for i in range(teeth):
        tooth = trimesh.creation.box((0.002, 0.003, d * 0.6))
        y = -length / 2 + 0.008 + i * (length / (teeth + 1))
        tooth.apply_translation([w / 2 + 0.001, y, 0])
        parts.append(tooth)
    return _concat(parts)


def _propeller(length=0.060, w=0.006, h=0.002):
    blade1 = trimesh.creation.box((length, h, w))
    blade2 = trimesh.creation.box((w, h, length))
    hub = trimesh.creation.cylinder(radius=0.004, height=0.003, sections=24)
    return _concat([blade1, blade2, hub])


def _wheel(r=0.025, w=0.012):
    return trimesh.creation.cylinder(radius=r, height=w, sections=32)


def _gear(r=0.020, h=0.008, teeth=12):
    base = trimesh.creation.cylinder(radius=r, height=h, sections=48)
    parts = [base]
    for i in range(teeth):
        angle = 2 * math.pi * i / teeth
        tooth = trimesh.creation.box((0.004, h, 0.006))
        tooth.apply_translation([r * math.cos(angle) + 0.002 * math.cos(angle),
                                 0,
                                 r * math.sin(angle) + 0.002 * math.sin(angle)])
        parts.append(tooth)
    return _concat(parts)


def _pcb_board(w=0.050, h=0.002, d=0.035):
    board = trimesh.creation.box((w, h, d))
    # IC chip
    chip = trimesh.creation.box((0.012, 0.003, 0.012))
    chip.apply_translation([0, h / 2 + 0.0015, 0])
    # capacitor
    cap = trimesh.creation.cylinder(radius=0.003, height=0.008, sections=16)
    cap.apply_translation([w / 3, h / 2 + 0.004, d / 4])
    # USB port
    usb = trimesh.creation.box((0.008, 0.004, 0.006))
    usb.apply_translation([0, h / 2 + 0.002, -d / 2 + 0.003])
    return _concat([board, chip, cap, usb])


def _housing(w=0.060, h=0.040, d=0.060):
    outer = trimesh.creation.box((w, h, d))
    # mounting features
    for sx, sz in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        standoff = trimesh.creation.cylinder(radius=0.003, height=0.004, sections=16)
        standoff.apply_translation([sx * (w / 2 - 0.008), h / 2 + 0.002, sz * (d / 2 - 0.008)])
        outer = _concat([outer, standoff])
    return outer


def _sensor(w=0.015, h=0.010, d=0.015):
    body = trimesh.creation.box((w, h, d))
    lens = trimesh.creation.cylinder(radius=0.004, height=0.003, sections=16)
    lens.apply_translation([0, h / 2 + 0.0015, 0])
    return _concat([body, lens])


def _battery(w=0.050, h=0.015, d=0.030):
    return trimesh.creation.box((w, h, d))


def _spring(r=0.005, h=0.025, coils=5):
    parts = []
    for i in range(coils * 2):
        ring = trimesh.creation.cylinder(radius=r, height=h / (coils * 2), sections=16)
        ring.apply_translation([0, -h / 2 + (i + 0.5) * h / (coils * 2), 0])
        parts.append(ring)
    return _concat(parts)


def _tube(r_outer=0.008, r_inner=0.006, h=0.060):
    outer = trimesh.creation.cylinder(radius=r_outer, height=h, sections=24)
    inner = trimesh.creation.cylinder(radius=r_inner, height=h + 0.002, sections=24)
    return _concat([outer, inner])


# ---------------------------------------------------------------------------
# Component inference: determine what parts to generate based on prompt
# ---------------------------------------------------------------------------

# Maps categories to (generator_fn, material_name, scale_multiplier)
COMPONENT_LIBRARY = {
    "servo": (_servo_motor, "servo_blue", 1.0),
    "motor": (_servo_motor, "dark_metal", 1.2),
    "bracket": (_bracket_u, "aluminum", 1.0),
    "link": (_arm_link, "aluminum", 1.0),
    "base": (_plate, "black_anodized", 1.0),
    "plate": (_plate, "aluminum", 0.8),
    "finger": (_finger, "rubber_black", 1.0),
    "gripper": (_finger, "rubber_black", 1.0),
    "propeller": (_propeller, "carbon_fiber", 1.0),
    "wheel": (_wheel, "rubber_black", 1.0),
    "gear": (_gear, "aluminum", 1.0),
    "pcb": (_pcb_board, "pcb_green", 1.0),
    "board": (_pcb_board, "pcb_green", 1.0),
    "controller": (_pcb_board, "pcb_green", 1.0),
    "arduino": (_pcb_board, "pcb_green", 1.2),
    "housing": (_housing, "black_anodized", 1.0),
    "enclosure": (_housing, "black_anodized", 1.0),
    "sensor": (_sensor, "dark_metal", 1.0),
    "battery": (_battery, "battery_blue", 1.0),
    "spring": (_spring, "aluminum", 1.0),
    "tube": (_tube, "clear", 1.0),
    "frame": (_box_part, "aluminum", 1.0),
    "body": (_housing, "black_anodized", 1.0),
}

MATERIAL_DEFS = {
    "black_anodized": (0.12, 0.12, 0.14),
    "dark_metal": (0.25, 0.25, 0.28),
    "aluminum": (0.75, 0.75, 0.78),
    "servo_blue": (0.10, 0.12, 0.20),
    "pcb_green": (0.05, 0.30, 0.12),
    "rubber_black": (0.08, 0.08, 0.08),
    "carbon_fiber": (0.10, 0.10, 0.12),
    "battery_blue": (0.12, 0.18, 0.35),
    "clear": (0.80, 0.80, 0.82),
    "red_wire": (0.70, 0.10, 0.10),
    "yellow": (0.80, 0.70, 0.10),
}

# Product archetypes: define typical part lists for common products
PRODUCT_ARCHETYPES = {
    "robot_arm": [
        ("base_plate", "base", "fixed", None),
        ("turntable", "plate", "revolute", {"axis": "y", "lo": -3.14, "hi": 3.14}),
        ("shoulder_servo", "servo", "fixed", None),
        ("shoulder_bracket", "bracket", "revolute", {"axis": "z", "lo": -1.57, "hi": 1.57}),
        ("upper_arm", "link", "fixed", None),
        ("elbow_servo", "servo", "fixed", None),
        ("elbow_bracket", "bracket", "revolute", {"axis": "z", "lo": -2.35, "hi": 0.78}),
        ("forearm", "link", "fixed", None),
        ("wrist_servo", "servo", "fixed", None),
        ("wrist_bracket", "bracket", "revolute", {"axis": "y", "lo": -3.14, "hi": 3.14}),
        ("gripper_base", "plate", "fixed", None),
        ("finger_left", "finger", "revolute", {"axis": "z", "lo": 0, "hi": 0.78}),
        ("finger_right", "finger", "revolute", {"axis": "z", "lo": -0.78, "hi": 0}),
    ],
    "drone": [
        ("body", "housing", "fixed", None),
        ("arm_fr", "link", "fixed", None),
        ("motor_fr", "motor", "fixed", None),
        ("prop_fr", "propeller", "continuous", {"axis": "y"}),
        ("arm_fl", "link", "fixed", None),
        ("motor_fl", "motor", "fixed", None),
        ("prop_fl", "propeller", "continuous", {"axis": "y"}),
        ("arm_br", "link", "fixed", None),
        ("motor_br", "motor", "fixed", None),
        ("prop_br", "propeller", "continuous", {"axis": "y"}),
        ("arm_bl", "link", "fixed", None),
        ("motor_bl", "motor", "fixed", None),
        ("prop_bl", "propeller", "continuous", {"axis": "y"}),
        ("camera", "sensor", "revolute", {"axis": "x", "lo": -1.57, "hi": 0.3}),
        ("battery", "battery", "fixed", None),
        ("controller", "pcb", "fixed", None),
    ],
    "gripper": [
        ("mounting_plate", "base", "fixed", None),
        ("housing", "housing", "fixed", None),
        ("actuator", "motor", "fixed", None),
        ("finger_base_l", "bracket", "prismatic", {"axis": "x", "lo": -0.025, "hi": 0}),
        ("finger_tip_l", "finger", "fixed", None),
        ("sensor_l", "sensor", "fixed", None),
        ("finger_base_r", "bracket", "prismatic", {"axis": "x", "lo": 0, "hi": 0.025}),
        ("finger_tip_r", "finger", "fixed", None),
        ("sensor_r", "sensor", "fixed", None),
    ],
    "wheeled_robot": [
        ("chassis", "housing", "fixed", None),
        ("controller", "pcb", "fixed", None),
        ("motor_l", "motor", "fixed", None),
        ("wheel_l", "wheel", "continuous", {"axis": "z"}),
        ("motor_r", "motor", "fixed", None),
        ("wheel_r", "wheel", "continuous", {"axis": "z"}),
        ("caster", "wheel", "fixed", None),
        ("sensor_front", "sensor", "fixed", None),
        ("battery", "battery", "fixed", None),
    ],
    "generic_mechanism": [
        ("base", "base", "fixed", None),
        ("main_body", "housing", "fixed", None),
        ("actuator", "motor", "revolute", {"axis": "y", "lo": -3.14, "hi": 3.14}),
        ("arm", "link", "revolute", {"axis": "z", "lo": -1.57, "hi": 1.57}),
        ("end_effector", "bracket", "fixed", None),
        ("controller", "pcb", "fixed", None),
        ("sensor", "sensor", "fixed", None),
    ],
}


def _detect_archetype(prompt: str) -> str:
    lp = prompt.lower()
    if any(w in lp for w in ["arm", "7dof", "6dof", "articulated", "robot arm"]):
        return "robot_arm"
    if any(w in lp for w in ["drone", "quadcopter", "uav", "multirotor"]):
        return "drone"
    if any(w in lp for w in ["gripper", "claw", "grabber", "jaw"]):
        return "gripper"
    if any(w in lp for w in ["car", "rover", "wheeled", "mobile robot", "line follower"]):
        return "wheeled_robot"
    return "generic_mechanism"


def generate_urdf_for_prompt(prompt: str) -> Optional[str]:
    """Generate URDF + STL meshes for a prompt. Returns the URDF path relative to /models/."""
    archetype = _detect_archetype(prompt)
    parts = PRODUCT_ARCHETYPES[archetype]

    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
    model_id = f"{archetype}_{prompt_hash}"
    model_dir = MODELS_DIR / model_id / "meshes"
    model_dir.mkdir(parents=True, exist_ok=True)

    urdf_path = MODELS_DIR / model_id / "model.urdf"

    # Skip regeneration if already exists
    if urdf_path.exists():
        return f"/models/_generated/{model_id}/model.urdf"

    # Generate STL meshes
    for part_name, part_type, _, _ in parts:
        gen_fn, _, scale = COMPONENT_LIBRARY.get(part_type, (_box_part, "dark_metal", 1.0))
        mesh = gen_fn()
        if scale != 1.0:
            mesh.apply_scale(scale)
        stl_path = model_dir / f"{part_name}.stl"
        mesh.export(str(stl_path))

    # Generate URDF
    urdf_xml = _build_urdf(model_id, parts)
    urdf_path.write_text(urdf_xml)

    logger.info("Generated URDF model: %s with %d parts", model_id, len(parts))
    return f"/models/_generated/{model_id}/model.urdf"


def _build_urdf(model_id: str, parts: list) -> str:
    lines = ['<?xml version="1.0" ?>']
    lines.append(f'<robot name="{model_id}">')
    lines.append("")

    # Material definitions
    for mat_name, (r, g, b) in MATERIAL_DEFS.items():
        lines.append(f'  <material name="{mat_name}">')
        lines.append(f'    <color rgba="{r:.2f} {g:.2f} {b:.2f} 1.0"/>')
        lines.append(f'  </material>')

    lines.append("")

    prev_link = None
    y_offset = 0.0

    for i, (part_name, part_type, joint_type, joint_params) in enumerate(parts):
        _, mat_name, _ = COMPONENT_LIBRARY.get(part_type, (_box_part, "dark_metal", 1.0))
        link_name = f"{part_name}_link"

        # Link
        lines.append(f'  <link name="{link_name}">')
        lines.append(f'    <visual>')
        lines.append(f'      <origin xyz="0 0 0" rpy="0 0 0"/>')
        lines.append(f'      <geometry><mesh filename="meshes/{part_name}.stl"/></geometry>')
        lines.append(f'      <material name="{mat_name}"/>')
        lines.append(f'    </visual>')
        lines.append(f'    <inertial>')
        lines.append(f'      <mass value="0.05"/>')
        lines.append(f'      <inertia ixx="0.00001" ixy="0" ixz="0" iyy="0.00001" iyz="0" izz="0.00001"/>')
        lines.append(f'    </inertial>')
        lines.append(f'  </link>')

        # Joint (skip for first link)
        if prev_link is not None:
            joint_name = f"{part_name}_joint"
            y_step = 0.025 if joint_type != "fixed" else 0.015
            y_offset += y_step

            lines.append(f'  <joint name="{joint_name}" type="{joint_type}">')
            lines.append(f'    <parent link="{prev_link}"/>')
            lines.append(f'    <child link="{link_name}"/>')

            # Position parts based on archetype layout
            if "arm_f" in part_name or "arm_b" in part_name:
                # Drone arms - spread out
                angle = {"arm_fr": 0.785, "arm_fl": 2.356, "arm_br": 3.927, "arm_bl": 5.498}
                a = angle.get(part_name, i * 1.5)
                lines.append(f'    <origin xyz="{0.05 * math.cos(a):.4f} 0.005 {0.05 * math.sin(a):.4f}" rpy="0 0 {a:.3f}"/>')
            elif "motor" in part_name:
                lines.append(f'    <origin xyz="0.05 0.008 0" rpy="0 0 0"/>')
            elif "prop" in part_name:
                lines.append(f'    <origin xyz="0 0.012 0" rpy="0 0 0"/>')
            elif "wheel_l" in part_name:
                lines.append(f'    <origin xyz="-0.04 -0.01 0" rpy="1.5708 0 0"/>')
            elif "wheel_r" in part_name:
                lines.append(f'    <origin xyz="0.04 -0.01 0" rpy="1.5708 0 0"/>')
            elif "finger" in part_name and "l" in part_name:
                lines.append(f'    <origin xyz="-0.015 0.010 0" rpy="0 0 0.1"/>')
            elif "finger" in part_name and "r" in part_name:
                lines.append(f'    <origin xyz="0.015 0.010 0" rpy="0 0 -0.1"/>')
            else:
                lines.append(f'    <origin xyz="0 {y_step:.4f} 0" rpy="0 0 0"/>')

            if joint_type in ("revolute", "continuous", "prismatic"):
                axis = (joint_params or {}).get("axis", "y")
                axis_vec = {"x": "1 0 0", "y": "0 1 0", "z": "0 0 1"}.get(axis, "0 1 0")
                lines.append(f'    <axis xyz="{axis_vec}"/>')

            if joint_type == "revolute":
                lo = (joint_params or {}).get("lo", -3.14)
                hi = (joint_params or {}).get("hi", 3.14)
                lines.append(f'    <limit lower="{lo}" upper="{hi}" effort="10" velocity="1.0"/>')
            elif joint_type == "prismatic":
                lo = (joint_params or {}).get("lo", -0.025)
                hi = (joint_params or {}).get("hi", 0.025)
                lines.append(f'    <limit lower="{lo}" upper="{hi}" effort="5" velocity="0.1"/>')

            lines.append(f'  </joint>')

        lines.append("")
        prev_link = link_name

    lines.append("</robot>")
    return "\n".join(lines)
