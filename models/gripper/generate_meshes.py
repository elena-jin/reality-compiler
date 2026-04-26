"""Generate STL meshes for a parallel-jaw gripper using trimesh."""

import numpy as np
import trimesh
from pathlib import Path

OUT = Path(__file__).parent / "meshes"
OUT.mkdir(exist_ok=True)


def _concat(meshes):
    return trimesh.util.concatenate(meshes)


def gripper_housing(w=0.060, h=0.035, d=0.045):
    body = trimesh.creation.box((w, h, d))
    # mounting flange on top
    flange = trimesh.creation.cylinder(radius=0.020, height=0.006, sections=32)
    flange.apply_translation([0, h / 2 + 0.003, 0])
    # guide rail channels
    rail_l = trimesh.creation.box((0.004, h + 0.004, d * 0.8))
    rail_l.apply_translation([-w / 2 + 0.006, 0, 0])
    rail_r = trimesh.creation.box((0.004, h + 0.004, d * 0.8))
    rail_r.apply_translation([w / 2 - 0.006, 0, 0])
    return _concat([body, flange, rail_l, rail_r])


def actuator(w=0.025, h=0.020, d=0.030):
    body = trimesh.creation.box((w, h, d))
    lead_screw = trimesh.creation.cylinder(radius=0.003, height=d + 0.010, sections=16)
    lead_screw.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    return _concat([body, lead_screw])


def finger_base(w=0.012, h=0.030, d=0.040):
    body = trimesh.creation.box((w, h, d))
    pivot = trimesh.creation.cylinder(radius=0.004, height=w + 0.002, sections=24)
    pivot.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
    pivot.apply_translation([0, -h / 2 + 0.004, d / 2 - 0.005])
    return _concat([body, pivot])


def finger_tip(w=0.010, h=0.025, d=0.020, teeth=4):
    body = trimesh.creation.box((w, h, d))
    parts = [body]
    # serrated grip surface
    for i in range(teeth):
        tooth = trimesh.creation.box((0.002, 0.003, d * 0.7))
        y = -h / 2 + 0.005 + i * (h / (teeth + 1))
        tooth.apply_translation([w / 2 + 0.001, y, 0])
        parts.append(tooth)
    return _concat(parts)


def force_sensor(w=0.008, h=0.008, d=0.015):
    body = trimesh.creation.box((w, h, d))
    pad = trimesh.creation.cylinder(radius=0.004, height=0.002, sections=16)
    pad.apply_translation([w / 2 + 0.001, 0, 0])
    pad.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
    return _concat([body, pad])


def mounting_plate(r=0.025, h=0.005):
    plate = trimesh.creation.cylinder(radius=r, height=h, sections=32)
    # bolt holes
    for angle in [0, np.pi / 2, np.pi, 3 * np.pi / 2]:
        hole = trimesh.creation.cylinder(radius=0.002, height=h + 0.002, sections=12)
        hole.apply_translation([r * 0.7 * np.cos(angle), 0, r * 0.7 * np.sin(angle)])
        plate = _concat([plate, hole])
    return plate


def main():
    parts = {
        "housing": gripper_housing(),
        "actuator": actuator(),
        "finger_base_left": finger_base(),
        "finger_base_right": finger_base(),
        "finger_tip_left": finger_tip(),
        "finger_tip_right": finger_tip(),
        "force_sensor_left": force_sensor(),
        "force_sensor_right": force_sensor(),
        "mounting_plate": mounting_plate(),
    }

    for name, mesh in parts.items():
        path = OUT / f"{name}.stl"
        mesh.export(str(path))
        print(f"  {name}.stl  ({len(mesh.vertices)} verts, {len(mesh.faces)} faces)")

    print(f"\nGenerated {len(parts)} STL meshes in {OUT}")


if __name__ == "__main__":
    main()
