"""Generate STL meshes for a quadcopter drone using trimesh."""

import numpy as np
import trimesh
from pathlib import Path

OUT = Path(__file__).parent / "meshes"
OUT.mkdir(exist_ok=True)


def _concat(meshes):
    return trimesh.util.concatenate(meshes)


def center_body(w=0.12, h=0.025, d=0.12):
    body = trimesh.creation.box((w, h, d))
    # rounded top shell
    dome = trimesh.creation.cylinder(radius=w * 0.35, height=0.012, sections=32)
    dome.apply_translation([0, h / 2 + 0.006, 0])
    # battery bay
    bay = trimesh.creation.box((w * 0.5, 0.010, d * 0.4))
    bay.apply_translation([0, -h / 2 - 0.005, 0])
    return _concat([body, dome, bay])


def arm(length=0.10, r=0.006):
    arm = trimesh.creation.cylinder(radius=r, height=length, sections=24)
    arm.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
    return arm


def motor_mount(r=0.014, h=0.018):
    mount = trimesh.creation.cylinder(radius=r, height=h, sections=32)
    # shaft
    shaft = trimesh.creation.cylinder(radius=0.002, height=0.008, sections=16)
    shaft.apply_translation([0, h / 2 + 0.004, 0])
    return _concat([mount, shaft])


def propeller(length=0.065, w=0.008, h=0.002):
    blade1 = trimesh.creation.box((length, h, w))
    blade2 = trimesh.creation.box((w, h, length))
    hub = trimesh.creation.cylinder(radius=0.005, height=0.004, sections=24)
    return _concat([blade1, blade2, hub])


def landing_gear_leg(h=0.025, r=0.003):
    leg = trimesh.creation.cylinder(radius=r, height=h, sections=16)
    foot = trimesh.creation.icosphere(radius=0.005, subdivisions=2)
    foot.apply_translation([0, -h / 2 - 0.003, 0])
    return _concat([leg, foot])


def camera_gimbal(w=0.020, h=0.015, d=0.020):
    housing = trimesh.creation.box((w, h, d))
    lens = trimesh.creation.cylinder(radius=0.005, height=0.008, sections=24)
    lens.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    lens.apply_translation([0, 0, d / 2 + 0.004])
    return _concat([housing, lens])


def gps_module(w=0.025, h=0.005, d=0.025):
    board = trimesh.creation.box((w, h, d))
    antenna = trimesh.creation.cylinder(radius=0.003, height=0.012, sections=16)
    antenna.apply_translation([0, h / 2 + 0.006, 0])
    return _concat([board, antenna])


def battery(w=0.050, h=0.015, d=0.030):
    return trimesh.creation.box((w, h, d))


def main():
    parts = {
        "center_body": center_body(),
        "arm_fr": arm(),
        "arm_fl": arm(),
        "arm_br": arm(),
        "arm_bl": arm(),
        "motor_fr": motor_mount(),
        "motor_fl": motor_mount(),
        "motor_br": motor_mount(),
        "motor_bl": motor_mount(),
        "prop_fr": propeller(),
        "prop_fl": propeller(),
        "prop_br": propeller(),
        "prop_bl": propeller(),
        "landing_gear_l": landing_gear_leg(),
        "landing_gear_r": landing_gear_leg(),
        "camera_gimbal": camera_gimbal(),
        "gps_module": gps_module(),
        "battery": battery(),
    }

    for name, mesh in parts.items():
        path = OUT / f"{name}.stl"
        mesh.export(str(path))
        print(f"  {name}.stl  ({len(mesh.vertices)} verts, {len(mesh.faces)} faces)")

    print(f"\nGenerated {len(parts)} STL meshes in {OUT}")


if __name__ == "__main__":
    main()
