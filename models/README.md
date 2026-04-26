# Models

This directory is the project-local CAD workspace for this harness.

## Inventory

Reusable CAD and URDF workflow rules live in:

- [`../skills/cad/SKILL.md`](../skills/cad/SKILL.md)
- [`../skills/urdf/SKILL.md`](../skills/urdf/SKILL.md)

Create only the subdirectories the current project actually uses. When this
directory gains project-specific inventory, dependency notes, preferred rebuild
roots, or durable quirks, keep those notes compact and local to this file.

## Source Of Truth

- Edit generator Python sources or imported STEP/STP files first.
- Treat STEP, STL, DXF, GLB/topology, and URDF outputs as derived artifacts.
- Regenerate explicit targets with the CAD or URDF skill tools.
- Keep temporary review images outside `models/`, usually under `/tmp/...`.
