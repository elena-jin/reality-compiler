"""Pydantic schemas for Reality Compiler outputs.

All outputs (BOM, assembly steps, feasibility reports) use strict JSON schemas
with validation at every stage. (Pydantic sponsor requirement)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FeasibilityLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class SourcePlatform(str, Enum):
    AMAZON_UK = "Amazon UK"
    RS_COMPONENTS = "RS Components"
    ALIBABA = "Alibaba"


# ---------------------------------------------------------------------------
# 3-D Model primitives
# ---------------------------------------------------------------------------

class Vec3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class ModelPrimitive(BaseModel):
    shape: str = Field(description="box | cylinder | sphere | cone | torus")
    position: Vec3 = Field(default_factory=Vec3)
    rotation: Vec3 = Field(default_factory=Vec3, description="Euler angles in radians")
    scale: Vec3 = Field(default_factory=lambda: Vec3(x=1, y=1, z=1))
    color: str = Field(default="#6366f1", description="Hex colour")
    label: str = ""


# ---------------------------------------------------------------------------
# Parametric part definitions (engineering-grade)
# ---------------------------------------------------------------------------

class ConnectionPoint(BaseModel):
    name: str = Field(description="e.g. shaft_output, mounting_hole_1")
    type: str = Field(description="joint | socket | axis | mounting_hole | flange")
    position_mm: Vec3 = Field(default_factory=Vec3, description="Position relative to part origin in mm")
    axis: Optional[Vec3] = Field(default=None, description="Axis direction for rotational connections")


class ParametricDimensions(BaseModel):
    length_mm: float = Field(ge=0, description="Length in mm")
    width_mm: float = Field(ge=0, description="Width in mm")
    height_mm: float = Field(ge=0, description="Height in mm")
    diameter_mm: Optional[float] = Field(default=None, ge=0, description="Diameter for cylindrical parts")
    wall_thickness_mm: Optional[float] = Field(default=None, ge=0, description="Wall thickness for hollow parts")


class ExportSpec(BaseModel):
    step_definition: str = Field(default="", description="Parametric solid description for STEP export")
    stl_resolution: str = Field(default="0.1mm tolerance, 32 segments", description="Mesh resolution for STL")
    dxf_profile: Optional[str] = Field(default=None, description="2D profile description if part is planar")
    glb_metadata: str = Field(default="", description="Scene placement metadata for GLB export")


class ParametricPart(BaseModel):
    name: str
    function: str = Field(description="Functional role: actuator | structural | sensor | end_effector | fastener | electronics")
    dimensions: ParametricDimensions
    material: str = Field(description="e.g. 6061-T6 Aluminum, ABS, PLA, Stainless Steel 304")
    mass_grams: float = Field(ge=0, default=0.0)
    connection_points: list[ConnectionPoint] = Field(default_factory=list)
    export_spec: ExportSpec = Field(default_factory=ExportSpec)
    real_world_equivalent: str = Field(default="", description="e.g. MG996R Servo Motor, M3x12 Socket Cap Screw")


# ---------------------------------------------------------------------------
# Topology graph
# ---------------------------------------------------------------------------

class TopologyNode(BaseModel):
    id: str
    part_name: str
    function: str = ""


class TopologyEdge(BaseModel):
    source: str = Field(description="Node ID of parent part")
    target: str = Field(description="Node ID of child part")
    connection_type: str = Field(description="revolute | prismatic | fixed | fastener | contact")
    degrees_of_freedom: int = Field(ge=0, le=6, default=0)


class TopologyGraph(BaseModel):
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)


class ConceptModel(BaseModel):
    primitives: list[ModelPrimitive] = Field(default_factory=list)
    camera_distance: float = Field(default=5.0, description="Suggested camera distance")
    urdf_path: Optional[str] = Field(default=None, description="Path to URDF file for realistic rendering")
    parametric_parts: list[ParametricPart] = Field(default_factory=list, description="Engineering-grade part definitions")
    topology: Optional[TopologyGraph] = Field(default=None, description="Part connection graph")


# ---------------------------------------------------------------------------
# Bill of Materials
# ---------------------------------------------------------------------------

class BomItem(BaseModel):
    name: str
    quantity: int = 1
    specification: str = ""
    unit_cost_gbp: float = Field(ge=0)
    category: str = ""


class BillOfMaterials(BaseModel):
    items: list[BomItem] = Field(default_factory=list)
    total_cost_gbp: float = Field(ge=0, default=0.0)


# ---------------------------------------------------------------------------
# Sourcing
# ---------------------------------------------------------------------------

class SourcingLink(BaseModel):
    component: str
    platform: SourcePlatform
    search_query: str
    url: str = ""


class SourcingResult(BaseModel):
    links: list[SourcingLink] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

class AssemblyStep(BaseModel):
    step_number: int
    title: str
    description: str
    tools_required: list[str] = Field(default_factory=list)
    estimated_time_min: float = Field(ge=0, default=5.0)


class AssemblyInstructions(BaseModel):
    steps: list[AssemblyStep] = Field(default_factory=list)
    total_time_min: float = Field(ge=0, default=0.0)


# ---------------------------------------------------------------------------
# Arduino Assembly
# ---------------------------------------------------------------------------

class ArduinoPin(BaseModel):
    pin: str = Field(description="e.g. D9, A0, GND, 5V")
    component: str
    wire_color: str = ""
    note: str = ""


class ArduinoWiring(BaseModel):
    pins: list[ArduinoPin] = Field(default_factory=list)
    board: str = Field(default="Arduino Nano")
    code_snippet: str = Field(default="")
    libraries: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Feasibility
# ---------------------------------------------------------------------------

class FeasibilityRisk(BaseModel):
    area: str
    description: str
    severity: FeasibilityLevel


class FeasibilityReport(BaseModel):
    score: FeasibilityLevel = FeasibilityLevel.GREEN
    summary: str = ""
    risks: list[FeasibilityRisk] = Field(default_factory=list)
    prototype_cost_gbp: float = Field(ge=0, default=0.0)
    manufacturing_unit_cost_gbp: float = Field(ge=0, default=0.0)


# ---------------------------------------------------------------------------
# Top-level generation result
# ---------------------------------------------------------------------------

class GenerationResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    concept_model: ConceptModel
    bom: BillOfMaterials
    sourcing: SourcingResult
    assembly: AssemblyInstructions
    feasibility: FeasibilityReport
    arduino: Optional[ArduinoWiring] = Field(default=None, description="Arduino wiring and code for electronics projects")


# ---------------------------------------------------------------------------
# Request / response wrappers
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    session_id: Optional[str] = None


class IterateRequest(BaseModel):
    session_id: str
    design_id: str
    command: str = Field(min_length=2, max_length=500, description="e.g. 'make it smaller', 'reduce cost'")


class SessionHistory(BaseModel):
    session_id: str
    designs: list[GenerationResult] = Field(default_factory=list)
