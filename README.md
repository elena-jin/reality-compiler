# Reality Compiler

Turn ideas into real things you could actually build.

Prompt -> 3D robot -> parts list -> cost -> build plan -> X-ray internals.

---

## Public Repo

https://github.com/elena-jin/reality-compiler

---

60-90 sec flow:

idea -> robot -> BOM -> X-ray mode -> "make it cheaper" -> updated design

---

## What we used (no fluff)

### Built with:

- LLMs for structured robot + product generation

- Three.js for real-time 3D rendering

- Pydantic (strict AI outputs so nothing breaks)

- Mubit (memory + iterative design improvements)

- Devin API (agent that refines and improves designs)

- URDF-style robot structure generation (simulated kinematics)

---

## What we did NOT use

- No CAD engine (Fusion / SolidWorks etc.)

- No physics simulation

- No real supplier APIs

- No prebuilt robot templates

Everything is generated dynamically.

---

## Live App

https://reality-compiler-taejuaku.fly.dev/

---

## What it does

You type:

> "Baymax healthcare robot"

We return:

- 3D interactive robot

- internal X-ray structure

- bill of materials (what to buy)

- cost estimate (prototype vs scale)

- assembly steps

- editable improvements over time

---

## Why it matters

Right now:

- ideas are cheap

- prototyping is slow + expensive

We flip that:

> idea -> buildable hardware in under 60 seconds

---

## One-liner

> "We built a compiler for physical reality."
