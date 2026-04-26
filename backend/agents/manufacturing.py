"""Manufacturing Agent – Shenzhen sourcing, supplier matching, RFQ generation.

Given any product concept, generates:
1. Product interpretation (what physical object is being designed)
2. Shenzhen supplier recommendations with contact info
3. RFQ (Request for Quotation) templates per component category
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from backend.schemas import (
    BillOfMaterials,
    ManufacturingPlan,
    ManufacturingSupplier,
    ProductInterpretation,
    RFQTemplate,
)

logger = logging.getLogger("reality_compiler.manufacturing_agent")

# ---------------------------------------------------------------------------
# Shenzhen supplier database (real industrial manufacturers)
# ---------------------------------------------------------------------------

_SUPPLIERS: list[dict] = [
    # --- CNC / Metal ---
    {
        "name": "Shenzhen Kaiao Rapid Prototyping",
        "specialization": "CNC machining, rapid prototyping (aluminum, steel, brass)",
        "best_use_case": "cnc",
        "contact_method": "info@kaborapid.com / Alibaba inquiry",
        "appointment_required": False,
        "lead_time_prototype": "3-5 business days",
        "lead_time_production": "2-3 weeks",
        "district": "Bao'an",
        "moq": "1 piece (prototype)",
        "categories": ["mechanical", "structural", "metal"],
    },
    {
        "name": "Star Rapid (Zhongshan/Shenzhen)",
        "specialization": "CNC machining, die casting, injection molding, finishing",
        "best_use_case": "cnc",
        "contact_method": "info@starrapid.com / starrapid.com inquiry form",
        "appointment_required": False,
        "lead_time_prototype": "5-7 business days",
        "lead_time_production": "3-5 weeks",
        "district": "Bao'an",
        "moq": "1 piece",
        "categories": ["mechanical", "structural", "metal", "plastic"],
    },
    # --- PCB ---
    {
        "name": "JLCPCB",
        "specialization": "PCB fabrication, SMT assembly, 3D printing",
        "best_use_case": "pcb",
        "contact_method": "jlcpcb.com (online order) / support@jlcpcb.com",
        "appointment_required": False,
        "lead_time_prototype": "1-3 days (PCB only), 5-7 days (PCBA)",
        "lead_time_production": "1-2 weeks",
        "district": "Nanshan",
        "moq": "5 pieces",
        "categories": ["electronics", "pcb"],
    },
    {
        "name": "PCBWay",
        "specialization": "PCB prototyping, assembly, stencil, CNC, 3D printing",
        "best_use_case": "pcb",
        "contact_method": "pcbway.com (online) / service@pcbway.com",
        "appointment_required": False,
        "lead_time_prototype": "1-2 days (PCB), 3-5 days (assembly)",
        "lead_time_production": "1-2 weeks",
        "district": "Bao'an",
        "moq": "5 pieces",
        "categories": ["electronics", "pcb"],
    },
    {
        "name": "AllPCB",
        "specialization": "Quick-turn PCB, flexible PCB, HDI boards",
        "best_use_case": "pcb",
        "contact_method": "allpcb.com (online order)",
        "appointment_required": False,
        "lead_time_prototype": "24 hours (express), 3-5 days (standard)",
        "lead_time_production": "1-2 weeks",
        "district": "Longgang",
        "moq": "1 piece",
        "categories": ["electronics", "pcb"],
    },
    # --- Injection molding / Plastic ---
    {
        "name": "Shenzhen Silver Basis Technology",
        "specialization": "Injection mold tooling, plastic parts, overmolding",
        "best_use_case": "injection_molding",
        "contact_method": "silverbasis.com / sales@silver-basis.com",
        "appointment_required": False,
        "lead_time_prototype": "7-10 days (soft tooling)",
        "lead_time_production": "3-5 weeks (steel mold + production)",
        "district": "Bao'an",
        "moq": "500 pieces (production)",
        "categories": ["plastic", "housing", "enclosure"],
    },
    {
        "name": "HLH Prototypes",
        "specialization": "Rapid prototyping, injection molding, vacuum casting, CNC",
        "best_use_case": "prototype",
        "contact_method": "hlhprototypes.com / sales@hlhprototypes.com",
        "appointment_required": False,
        "lead_time_prototype": "3-5 days",
        "lead_time_production": "2-4 weeks",
        "district": "Bao'an",
        "moq": "1 piece (prototype), 100+ (production)",
        "categories": ["plastic", "mechanical", "structural"],
    },
    # --- 3D Printing ---
    {
        "name": "Shenzhen Wenext Technology",
        "specialization": "SLA/SLS/MJF 3D printing, rapid prototyping",
        "best_use_case": "prototype",
        "contact_method": "wenext.cn / WeChat: wenext3d",
        "appointment_required": False,
        "lead_time_prototype": "1-3 days",
        "lead_time_production": "3-7 days (batch printing)",
        "district": "Nanshan",
        "moq": "1 piece",
        "categories": ["plastic", "prototype", "3d_printing"],
    },
    # --- Assembly / Box Build ---
    {
        "name": "Titoma Design (Taiwan/Shenzhen)",
        "specialization": "Full product assembly, box build, testing, packaging",
        "best_use_case": "mass_production",
        "contact_method": "titoma.com / info@titoma.com",
        "appointment_required": True,
        "lead_time_prototype": "2-4 weeks (pilot run)",
        "lead_time_production": "4-8 weeks",
        "district": "Bao'an",
        "moq": "500 units",
        "categories": ["assembly", "mass_production"],
    },
    {
        "name": "Dragon Innovation (advisory + Shenzhen factory network)",
        "specialization": "Factory selection, production ramp, supply chain advisory",
        "best_use_case": "mass_production",
        "contact_method": "dragoninnovation.com / contact form",
        "appointment_required": True,
        "lead_time_prototype": "N/A (advisory)",
        "lead_time_production": "Varies by factory",
        "district": "N/A (remote + Shenzhen network)",
        "moq": "1000+ units",
        "categories": ["mass_production", "advisory"],
    },
    # --- Electronics components ---
    {
        "name": "Huaqiangbei Electronics Market",
        "specialization": "Electronic components, sensors, motors, MCU boards, connectors",
        "best_use_case": "prototype",
        "contact_method": "Walk-in (Futian district) / individual vendor WeChat",
        "appointment_required": False,
        "lead_time_prototype": "Same day",
        "lead_time_production": "1-3 days (bulk order)",
        "district": "Huaqiangbei",
        "moq": "1 piece",
        "categories": ["electronics", "sensors", "actuators", "connectors"],
    },
    {
        "name": "LCSC Electronics",
        "specialization": "Electronic components distributor (same parent as JLCPCB)",
        "best_use_case": "prototype",
        "contact_method": "lcsc.com (online order)",
        "appointment_required": False,
        "lead_time_prototype": "1-2 days (Shenzhen), 5-7 days (international)",
        "lead_time_production": "1-2 weeks",
        "district": "Nanshan",
        "moq": "1 piece (most components)",
        "categories": ["electronics", "sensors", "connectors", "passive"],
    },
    # --- Motor / actuator specialists ---
    {
        "name": "Shenzhen Hengdrive Electric",
        "specialization": "BLDC motors, servo motors, stepper motors, custom windings",
        "best_use_case": "mass_production",
        "contact_method": "hengdrivemotor.com / sales@hengdrivemotor.com",
        "appointment_required": False,
        "lead_time_prototype": "5-7 days (sample)",
        "lead_time_production": "2-4 weeks",
        "district": "Bao'an",
        "moq": "10 pieces (sample), 100+ (production)",
        "categories": ["actuators", "motors"],
    },
    # --- Cable / wiring ---
    {
        "name": "Shenzhen Kuncan Electronics",
        "specialization": "Custom cable assemblies, wire harnesses, connectors",
        "best_use_case": "mass_production",
        "contact_method": "kuncan.net / sales@kuncan.net",
        "appointment_required": False,
        "lead_time_prototype": "3-5 days",
        "lead_time_production": "1-2 weeks",
        "district": "Longgang",
        "moq": "50 pieces",
        "categories": ["wiring", "connectors", "cables"],
    },
]

# ---------------------------------------------------------------------------
# Product interpretation heuristics
# ---------------------------------------------------------------------------

_FORM_KEYWORDS = {
    "robot": ["robot", "arm", "manipulator", "humanoid", "quadruped", "drone", "gripper", "bot", "baymax", "labubu", "walker", "crawler"],
    "device": ["device", "sensor", "monitor", "tracker", "detector", "meter", "gauge", "reader"],
    "gadget": ["gadget", "wearable", "watch", "band", "ring", "earphone", "headphone", "speaker"],
    "machine": ["machine", "sorter", "printer", "cutter", "mill", "lathe", "cnc", "press", "extruder"],
    "tool": ["tool", "drill", "driver", "wrench", "plier", "clamp", "jig", "fixture"],
    "hybrid": ["hybrid", "companion", "assistant", "smart", "iot", "connected"],
}

_CATEGORY_KEYWORDS = {
    "electronics": ["servo", "motor", "arduino", "pcb", "mcu", "battery", "sensor", "led", "oled", "camera", "bluetooth", "wifi", "controller"],
    "mechanical": ["gear", "shaft", "bearing", "bracket", "linkage", "spring", "actuator", "pneumatic", "hydraulic"],
    "structural": ["frame", "chassis", "housing", "enclosure", "plate", "beam", "rail", "extrusion"],
    "sensors": ["accelerometer", "gyroscope", "lidar", "ultrasonic", "ir", "camera", "force sensor", "temperature", "humidity"],
    "plastic": ["shell", "cover", "body", "case", "housing", "enclosure", "panel"],
    "actuators": ["servo", "motor", "stepper", "bldc", "solenoid", "linear actuator", "pneumatic cylinder"],
}


def _classify_form(prompt: str) -> str:
    lp = prompt.lower()
    best, best_score = "device", 0
    for form, keywords in _FORM_KEYWORDS.items():
        score = sum(1 for k in keywords if k in lp)
        if score > best_score:
            best, best_score = form, score
    return best


def _infer_categories(prompt: str, bom_items: list[str]) -> list[str]:
    combined = (prompt + " " + " ".join(bom_items)).lower()
    categories = []
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(k in combined for k in keywords):
            categories.append(cat)
    if not categories:
        categories = ["electronics", "mechanical"]
    return categories


def _interpret_product(prompt: str) -> ProductInterpretation:
    lp = prompt.lower()
    form = _classify_form(prompt)

    # Extract key concepts
    words = re.findall(r'\b[a-z]{3,}\b', lp)
    stop_words = {"the", "and", "for", "with", "that", "this", "from", "your", "make", "create", "build", "design", "generate", "robot", "style"}
    key_words = [w for w in words if w not in stop_words][:5]
    name = " ".join(key_words[:3]).title() if key_words else "Smart Device"

    features = []
    if any(w in lp for w in ["servo", "motor", "actuator"]):
        features.append("Servo-actuated movement")
    if any(w in lp for w in ["sensor", "camera", "lidar", "detect"]):
        features.append("Integrated sensing capabilities")
    if any(w in lp for w in ["battery", "rechargeable", "portable"]):
        features.append("Battery-powered portable operation")
    if any(w in lp for w in ["wireless", "bluetooth", "wifi", "iot"]):
        features.append("Wireless connectivity")
    if any(w in lp for w in ["3d print", "printed", "pla", "abs"]):
        features.append("3D-printable enclosure/parts")
    if any(w in lp for w in ["arduino", "esp32", "raspberry", "mcu"]):
        features.append("Microcontroller-based intelligence")
    if not features:
        features = ["Electromechanical actuation", "Modular assembly", "Prototype-ready design"]

    analogues = []
    if "gripper" in lp:
        analogues = ["Robotiq 2F-85", "OnRobot RG2"]
    elif "drone" in lp or "quadcopter" in lp:
        analogues = ["DJI Mavic", "Crazyflie 2.1"]
    elif "arm" in lp or "manipulator" in lp:
        analogues = ["Universal Robots UR5", "Dobot Magician"]
    elif any(w in lp for w in ["dog", "quadruped", "spot"]):
        analogues = ["Boston Dynamics Spot", "Unitree Go1"]
    elif any(w in lp for w in ["humanoid", "baymax", "pepper"]):
        analogues = ["SoftBank Pepper", "Boston Dynamics Atlas"]
    elif any(w in lp for w in ["labubu", "toy", "figurine"]):
        analogues = ["Pop Mart Labubu", "Bandai Gunpla model kits"]
    elif "lamp" in lp or "light" in lp:
        analogues = ["Dyson Lightcycle", "BenQ ScreenBar"]
    elif "plant" in lp or "water" in lp:
        analogues = ["Xiaomi Smart Planter", "Parrot Pot"]
    else:
        analogues = ["Arduino Starter Kit", "Adafruit Feather"]

    categories = _infer_categories(prompt, [])

    return ProductInterpretation(
        object_name=name,
        description=f"A {form} designed for {prompt[:80].strip()}",
        physical_form=form,
        key_features=features,
        analogues=analogues,
        bom_categories=categories,
    )


# ---------------------------------------------------------------------------
# Supplier matching
# ---------------------------------------------------------------------------

def _match_suppliers(categories: list[str], is_mass_production: bool = False) -> list[ManufacturingSupplier]:
    matched = []
    seen_names = set()

    for supplier in _SUPPLIERS:
        s_cats = supplier.get("categories", [])
        overlap = set(categories) & set(s_cats)
        if not overlap:
            continue
        if supplier["name"] in seen_names:
            continue

        if is_mass_production and supplier["best_use_case"] not in ("mass_production", "injection_molding", "cnc"):
            continue

        seen_names.add(supplier["name"])
        matched.append(ManufacturingSupplier(
            name=supplier["name"],
            specialization=supplier["specialization"],
            best_use_case=supplier["best_use_case"],
            contact_method=supplier["contact_method"],
            appointment_required=supplier["appointment_required"],
            lead_time_prototype=supplier["lead_time_prototype"],
            lead_time_production=supplier["lead_time_production"],
            district=supplier["district"],
            moq=supplier.get("moq"),
        ))

    # Always include at least a general prototyping supplier
    if not matched:
        matched.append(ManufacturingSupplier(
            name="HLH Prototypes",
            specialization="Rapid prototyping, injection molding, vacuum casting, CNC",
            best_use_case="prototype",
            contact_method="hlhprototypes.com / sales@hlhprototypes.com",
            appointment_required=False,
            lead_time_prototype="3-5 days",
            lead_time_production="2-4 weeks",
            district="Bao'an",
            moq="1 piece",
        ))

    return matched


# ---------------------------------------------------------------------------
# RFQ template generation
# ---------------------------------------------------------------------------

def _generate_rfq(prompt: str, interpretation: ProductInterpretation, bom: Optional[BillOfMaterials]) -> list[RFQTemplate]:
    templates = []

    bom_text = ""
    if bom and bom.items:
        bom_lines = [f"  - {item.name} x{item.quantity}: {item.specification}" for item in bom.items]
        bom_text = "\n".join(bom_lines)

    categories = interpretation.bom_categories

    if any(c in categories for c in ["electronics", "pcb"]):
        templates.append(RFQTemplate(
            subject=f"RFQ: PCB Fabrication + Assembly for {interpretation.object_name}",
            body=(
                f"Dear team,\n\n"
                f"We are developing a {interpretation.physical_form} product: {interpretation.description}\n\n"
                f"We need:\n"
                f"- PCB fabrication (2-4 layer, FR-4)\n"
                f"- SMT assembly for prototype run (5-10 units)\n"
                f"- BOM:\n{bom_text or '  (attached separately)'}\n\n"
                f"Please quote for:\n"
                f"1. Prototype run: 5-10 assembled boards\n"
                f"2. Production run: 100 / 500 / 1000 units\n\n"
                f"Timeline: prototype within 2 weeks\n\n"
                f"Best regards"
            ),
            target_supplier_type="pcb",
        ))

    if any(c in categories for c in ["mechanical", "structural", "metal"]):
        templates.append(RFQTemplate(
            subject=f"RFQ: CNC Machined Parts for {interpretation.object_name}",
            body=(
                f"Dear team,\n\n"
                f"We require CNC machined parts for: {interpretation.description}\n\n"
                f"Materials: 6061-T6 Aluminum (primary), Stainless Steel 304 (secondary)\n"
                f"Finish: Anodized / Bead-blasted\n"
                f"Tolerances: ±0.05mm\n\n"
                f"Parts list:\n{bom_text or '  (STEP files attached separately)'}\n\n"
                f"Quantities:\n"
                f"- Prototype: 2-5 sets\n"
                f"- Production: 100 / 500 units\n\n"
                f"Please provide DFM feedback and quote.\n\n"
                f"Best regards"
            ),
            target_supplier_type="cnc",
        ))

    if any(c in categories for c in ["plastic", "housing", "enclosure"]):
        templates.append(RFQTemplate(
            subject=f"RFQ: Injection Molding / 3D Printing for {interpretation.object_name}",
            body=(
                f"Dear team,\n\n"
                f"We need plastic parts for: {interpretation.description}\n\n"
                f"For prototyping: SLA or SLS 3D printing (5-10 units)\n"
                f"For production: injection molding (ABS/PC/PA)\n\n"
                f"Parts:\n{bom_text or '  (3D files attached separately)'}\n\n"
                f"Please quote for:\n"
                f"1. 3D printed prototypes (5-10 sets)\n"
                f"2. Soft tooling (silicone mold) for 50-100 units\n"
                f"3. Steel mold for 1000+ unit production\n\n"
                f"Best regards"
            ),
            target_supplier_type="injection_molding",
        ))

    if any(c in categories for c in ["actuators", "motors"]):
        templates.append(RFQTemplate(
            subject=f"RFQ: Motors / Actuators for {interpretation.object_name}",
            body=(
                f"Dear team,\n\n"
                f"We need motors/actuators for: {interpretation.description}\n\n"
                f"Requirements:\n{bom_text or '  - Servo motors / BLDC motors (specs TBD)'}\n\n"
                f"Quantities:\n"
                f"- Samples: 5-10 units\n"
                f"- Production: 100 / 500 units\n\n"
                f"Please provide specs, pricing, and lead times.\n\n"
                f"Best regards"
            ),
            target_supplier_type="mass_production",
        ))

    if not templates:
        templates.append(RFQTemplate(
            subject=f"RFQ: Prototype Manufacturing for {interpretation.object_name}",
            body=(
                f"Dear team,\n\n"
                f"We are developing: {interpretation.description}\n\n"
                f"We need a manufacturing partner for prototype and small-batch production.\n\n"
                f"BOM:\n{bom_text or '  (to be provided)'}\n\n"
                f"Please advise on capabilities, pricing, and timelines.\n\n"
                f"Best regards"
            ),
            target_supplier_type="prototype",
        ))

    return templates


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_manufacturing(
    prompt: str,
    bom: Optional[BillOfMaterials] = None,
) -> ManufacturingPlan:
    logger.info("Manufacturing agent: generating plan for %r", prompt[:80])

    interpretation = _interpret_product(prompt)

    bom_item_names = [item.name for item in bom.items] if bom and bom.items else []
    all_categories = list(set(interpretation.bom_categories + _infer_categories(prompt, bom_item_names)))
    interpretation.bom_categories = all_categories

    suppliers = _match_suppliers(all_categories)
    rfq_templates = _generate_rfq(prompt, interpretation, bom)

    # Cost estimates based on complexity
    part_count = len(bom.items) if bom else 5
    proto_cost = max(50, part_count * 15 + 100)
    mass_cost = max(15, part_count * 3 + 20)

    recommendation = (
        f"Start with rapid prototyping (3D printing + off-the-shelf electronics) "
        f"to validate form factor. Source PCBs from JLCPCB and components from LCSC/Huaqiangbei. "
        f"For production, engage CNC + injection molding suppliers in Bao'an district. "
        f"Expected prototype timeline: 1-2 weeks. Production-ready: 6-8 weeks."
    )

    plan = ManufacturingPlan(
        product_interpretation=interpretation,
        suppliers=suppliers,
        rfq_templates=rfq_templates,
        estimated_prototype_cost_usd=proto_cost,
        estimated_mass_production_cost_usd=mass_cost,
        recommended_approach=recommendation,
    )

    logger.info("Manufacturing agent: %d suppliers, %d RFQ templates", len(suppliers), len(rfq_templates))
    return plan
