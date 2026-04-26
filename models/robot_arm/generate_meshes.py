"""Generate STL meshes for a 6-DOF robot arm using trimesh.

Each part is built from compound primitives (boxes, cylinders) to approximate
real servo-driven robot arm components like the reference image.
"""

import numpy as np
import trimesh
from pathlib import Path

OUT = Path(__file__).parent / "meshes"
OUT.mkdir(exist_ok=True)


def servo_motor(w=0.040, h=0.040, d=0.020, horn_r=0.006, horn_h=0.006):
    """MG996R-style servo motor body with output horn."""
    body = trimesh.creation.box((w, h, d))

    # mounting ears
    ear_w = 0.005
    ear = trimesh.creation.box((w + 2 * ear_w + 0.004, 0.0025, d))
    ear.apply_translation([0, h / 2 - 0.004, 0])
    body = trimesh.boolean.union([body, ear], engine="blender") if _has_blender() else _union_fallback(body, ear)

    # output shaft cylinder
    shaft = trimesh.creation.cylinder(radius=horn_r, height=horn_h, sections=32)
    shaft.apply_translation([0, h / 2 + horn_h / 2, 0])

    # horn disc
    horn = trimesh.creation.cylinder(radius=0.012, height=0.002, sections=32)
    horn.apply_translation([0, h / 2 + horn_h + 0.001, 0])

    return _concat([body, shaft, horn])


def bracket_u(w=0.050, h=0.060, d=0.004, flange=0.015):
    """U-shaped aluminum bracket."""
    back = trimesh.creation.box((w, h, d))
    left = trimesh.creation.box((d, h, flange))
    left.apply_translation([-(w / 2 - d / 2), 0, flange / 2 + d / 2])
    right = trimesh.creation.box((d, h, flange))
    right.apply_translation([(w / 2 - d / 2), 0, flange / 2 + d / 2])

    bracket = _concat([back, left, right])

    # mounting holes (visual only - small cylinders as holes)
    for sx in [-1, 1]:
        hole = trimesh.creation.cylinder(radius=0.002, height=d + 0.002, sections=16)
        hole.apply_translation([sx * (w / 2 - d / 2), h * 0.3, flange + d / 2])
        hole2 = trimesh.creation.cylinder(radius=0.002, height=d + 0.002, sections=16)
        hole2.apply_translation([sx * (w / 2 - d / 2), -h * 0.3, flange + d / 2])
        bracket = _concat([bracket, hole, hole2])

    return bracket


def bracket_l(w=0.050, h=0.060, d=0.004, flange=0.020):
    """L-shaped aluminum bracket."""
    plate_v = trimesh.creation.box((w, h, d))
    plate_h = trimesh.creation.box((w, d, flange))
    plate_h.apply_translation([0, -h / 2 + d / 2, flange / 2 + d / 2])
    return _concat([plate_v, plate_h])


def base_plate(w=0.10, h=0.006, d=0.10):
    """Thick metal base plate with mounting standoffs."""
    plate = trimesh.creation.box((w, h, d))

    # corner standoffs
    for sx, sz in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        standoff = trimesh.creation.cylinder(radius=0.005, height=0.012, sections=24)
        standoff.apply_translation([sx * (w / 2 - 0.012), h / 2 + 0.006, sz * (d / 2 - 0.012)])
        plate = _concat([plate, standoff])

    # center hub
    hub = trimesh.creation.cylinder(radius=0.018, height=0.010, sections=32)
    hub.apply_translation([0, h / 2 + 0.005, 0])
    plate = _concat([plate, hub])

    return plate


def upper_arm_link(length=0.12, w=0.030, d=0.015):
    """Arm link with rounded profile and mounting features."""
    body = trimesh.creation.box((w, length, d))

    # end caps (rounded)
    cap_top = trimesh.creation.cylinder(radius=w / 2, height=d, sections=32)
    cap_top.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    cap_top.apply_translation([0, length / 2, 0])

    cap_bot = trimesh.creation.cylinder(radius=w / 2, height=d, sections=32)
    cap_bot.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    cap_bot.apply_translation([0, -length / 2, 0])

    # pivot holes
    pivot_top = trimesh.creation.cylinder(radius=0.004, height=d + 0.004, sections=16)
    pivot_top.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    pivot_top.apply_translation([0, length / 2, 0])

    pivot_bot = trimesh.creation.cylinder(radius=0.004, height=d + 0.004, sections=16)
    pivot_bot.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    pivot_bot.apply_translation([0, -length / 2, 0])

    return _concat([body, cap_top, cap_bot, pivot_top, pivot_bot])


def forearm_link(length=0.10, w=0.025, d=0.012):
    """Shorter forearm link."""
    return upper_arm_link(length=length, w=w, d=d)


def wrist_assembly(w=0.030, h=0.025, d=0.020):
    """Compact wrist servo with small bracket."""
    servo_body = trimesh.creation.box((w, h, d))

    # horn
    horn = trimesh.creation.cylinder(radius=0.006, height=0.003, sections=24)
    horn.apply_translation([0, h / 2 + 0.0015, 0])

    # mounting plate
    plate = trimesh.creation.box((w + 0.010, 0.003, d + 0.010))
    plate.apply_translation([0, -h / 2 - 0.0015, 0])

    return _concat([servo_body, horn, plate])


def gripper_base(w=0.040, h=0.015, d=0.030):
    """Gripper mounting plate."""
    plate = trimesh.creation.box((w, h, d))

    # guide rails
    rail_l = trimesh.creation.box((0.003, h, d + 0.010))
    rail_l.apply_translation([-w / 2 + 0.005, 0, 0])
    rail_r = trimesh.creation.box((0.003, h, d + 0.010))
    rail_r.apply_translation([w / 2 - 0.005, 0, 0])

    return _concat([plate, rail_l, rail_r])


def gripper_finger(length=0.050, w=0.008, d=0.015, teeth=3):
    """Gripper finger with serrated grip surface."""
    body = trimesh.creation.box((w, length, d))

    # finger tip (tapered)
    tip = trimesh.creation.box((w * 0.7, 0.008, d * 0.8))
    tip.apply_translation([0, length / 2 + 0.004, 0])

    # grip teeth on inner face
    parts = [body, tip]
    for i in range(teeth):
        tooth = trimesh.creation.box((0.002, 0.003, d * 0.6))
        y = -length / 2 + 0.010 + i * (length / (teeth + 1))
        tooth.apply_translation([w / 2 + 0.001, y, 0])
        parts.append(tooth)

    return _concat(parts)


def turntable(r_outer=0.040, r_inner=0.015, h=0.012):
    """Rotating turntable between base and shoulder."""
    outer = trimesh.creation.cylinder(radius=r_outer, height=h, sections=48)

    # bearing ring visual
    ring = trimesh.creation.cylinder(radius=r_outer + 0.003, height=0.003, sections=48)
    ring.apply_translation([0, -h / 2 + 0.0015, 0])

    inner = trimesh.creation.cylinder(radius=r_inner, height=h + 0.002, sections=32)
    inner.apply_translation([0, 0, 0])

    return _concat([outer, ring, inner])


def _concat(meshes):
    """Concatenate meshes (no boolean, just visual merge)."""
    return trimesh.util.concatenate(meshes)


def _union_fallback(a, b):
    return _concat([a, b])


def _has_blender():
    return False


def main():
    parts = {
        "base_plate": base_plate(),
        "turntable": turntable(),
        "shoulder_servo": servo_motor(w=0.042, h=0.042, d=0.022),
        "shoulder_bracket": bracket_u(w=0.052, h=0.065, d=0.004, flange=0.018),
        "upper_arm": upper_arm_link(length=0.12, w=0.030, d=0.015),
        "elbow_servo": servo_motor(w=0.040, h=0.040, d=0.020),
        "elbow_bracket": bracket_u(w=0.048, h=0.055, d=0.004, flange=0.015),
        "forearm": forearm_link(length=0.10, w=0.025, d=0.012),
        "wrist_servo": wrist_assembly(w=0.030, h=0.025, d=0.020),
        "wrist_bracket": bracket_l(w=0.035, h=0.040, d=0.003, flange=0.015),
        "gripper_base": gripper_base(),
        "gripper_left": gripper_finger(),
        "gripper_right": gripper_finger(),
    }

    for name, mesh in parts.items():
        path = OUT / f"{name}.stl"
        mesh.export(str(path))
        verts = len(mesh.vertices)
        faces = len(mesh.faces)
        print(f"  {name}.stl  ({verts} verts, {faces} faces)")

    print(f"\nGenerated {len(parts)} STL meshes in {OUT}")


if __name__ == "__main__":
    main()
