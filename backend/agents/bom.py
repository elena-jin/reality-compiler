"""BOM Agent – generates a structured bill of materials.

Part of the Design Agent pipeline. Produces real-world component lists
with specifications and estimated costs.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from backend.schemas import BillOfMaterials, BomItem, AssemblyInstructions, AssemblyStep

logger = logging.getLogger("reality_compiler.bom_agent")

BOM_SYSTEM_PROMPT = """You are a hardware BOM (bill of materials) agent. Given a product description, generate a realistic bill of materials AND step-by-step assembly instructions.

Return ONLY valid JSON matching this schema:
{
  "bom": {
    "items": [
      {
        "name": "Component Name",
        "quantity": 1,
        "specification": "Detailed spec (e.g. M3x12mm socket head cap screw, Grade 8.8)",
        "unit_cost_gbp": 1.50,
        "category": "Fasteners|Electronics|Structural|Mechanical|3D Printed|Off-the-shelf"
      }
    ],
    "total_cost_gbp": 0.0
  },
  "assembly": {
    "steps": [
      {
        "step_number": 1,
        "title": "Step title",
        "description": "Detailed description of what to do",
        "tools_required": ["Tool 1", "Tool 2"],
        "estimated_time_min": 5
      }
    ],
    "total_time_min": 0
  }
}

Guidelines:
- Use real-world components available from common suppliers
- Include fasteners, wiring, and consumables
- Costs should be realistic UK prices in GBP
- Include 3D-printed parts where appropriate (cost = filament estimate)
- Assembly steps should be clear enough for a university student
- total_cost_gbp should be the sum of (quantity * unit_cost_gbp) for all items
- total_time_min should be the sum of estimated_time_min for all steps"""


async def generate_bom_and_assembly(
    prompt: str,
    previous_bom: Optional[BillOfMaterials] = None,
    previous_assembly: Optional[AssemblyInstructions] = None,
    iteration_command: Optional[str] = None,
) -> tuple[BillOfMaterials, AssemblyInstructions]:
    logger.info("BOM agent: generating for '%s'", prompt[:80])

    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            return await _generate_with_openai(prompt, previous_bom, previous_assembly, iteration_command, api_key)
        except Exception:
            logger.warning("OpenAI BOM call failed, using heuristic", exc_info=True)

    return _generate_heuristic(prompt, previous_bom, iteration_command)


async def _generate_with_openai(
    prompt: str,
    previous_bom: Optional[BillOfMaterials],
    previous_assembly: Optional[AssemblyInstructions],
    iteration_command: Optional[str],
    api_key: str,
) -> tuple[BillOfMaterials, AssemblyInstructions]:
    import httpx

    user_content = f"Product idea: {prompt}"
    if previous_bom and iteration_command:
        user_content += f"\n\nPrevious BOM:\n{previous_bom.model_dump_json()}"
        if previous_assembly:
            user_content += f"\n\nPrevious Assembly:\n{previous_assembly.model_dump_json()}"
        user_content += f"\n\nIteration command: {iteration_command}"
        user_content += "\nUpdate the BOM and assembly based on the command."

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": BOM_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.6,
                "max_tokens": 3000,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        bom = BillOfMaterials(**parsed["bom"])
        assembly = AssemblyInstructions(**parsed["assembly"])
        logger.info("BOM agent: OpenAI returned %d items, %d steps", len(bom.items), len(assembly.steps))
        return bom, assembly


def _generate_heuristic(
    prompt: str,
    previous_bom: Optional[BillOfMaterials],
    iteration_command: Optional[str],
) -> tuple[BillOfMaterials, AssemblyInstructions]:
    lp = prompt.lower()

    if previous_bom and iteration_command:
        return _apply_bom_iteration(previous_bom, iteration_command)

    if any(w in lp for w in ["gripper", "robot", "claw", "grabber"]):
        return _gripper_bom()
    if any(w in lp for w in ["plant", "pot", "water", "planter"]):
        return _plant_pot_bom()
    if any(w in lp for w in ["coin", "sort", "sorting"]):
        return _coin_sorter_bom()
    if any(w in lp for w in ["lamp", "light", "desk light"]):
        return _lamp_bom()
    if any(w in lp for w in ["phone", "stand", "holder", "dock"]):
        return _phone_stand_bom()
    if any(w in lp for w in ["drone", "quadcopter", "uav"]):
        return _drone_bom()

    return _generic_bom(prompt)


def _apply_bom_iteration(
    bom: BillOfMaterials,
    command: str,
) -> tuple[BillOfMaterials, AssemblyInstructions]:
    lc = command.lower()
    items = [item.model_copy(deep=True) for item in bom.items]

    if "reduce cost" in lc or "cheaper" in lc or "budget" in lc:
        for item in items:
            item.unit_cost_gbp = round(item.unit_cost_gbp * 0.7, 2)
        total = sum(i.unit_cost_gbp * i.quantity for i in items)
        new_bom = BillOfMaterials(items=items, total_cost_gbp=round(total, 2))
        assembly = _generic_assembly(len(items))
        return new_bom, assembly

    if "simpl" in lc:
        keep = max(3, len(items) * 2 // 3)
        items = items[:keep]
        total = sum(i.unit_cost_gbp * i.quantity for i in items)
        new_bom = BillOfMaterials(items=items, total_cost_gbp=round(total, 2))
        assembly = _generic_assembly(len(items))
        return new_bom, assembly

    total = sum(i.unit_cost_gbp * i.quantity for i in items)
    new_bom = BillOfMaterials(items=items, total_cost_gbp=round(total, 2))
    assembly = _generic_assembly(len(items))
    return new_bom, assembly


def _make_bom(items: list[BomItem]) -> BillOfMaterials:
    total = sum(i.unit_cost_gbp * i.quantity for i in items)
    return BillOfMaterials(items=items, total_cost_gbp=round(total, 2))


def _generic_assembly(n_items: int) -> AssemblyInstructions:
    steps = [
        AssemblyStep(step_number=1, title="Prepare components", description="Lay out all components and verify against the BOM. Check for any defects.", tools_required=["Workspace mat"], estimated_time_min=5),
        AssemblyStep(step_number=2, title="Assemble structural frame", description="Connect the main structural components. Use appropriate fasteners and ensure alignment.", tools_required=["Allen key set", "Phillips screwdriver"], estimated_time_min=15),
        AssemblyStep(step_number=3, title="Install electronics", description="Mount electronic components, connect wiring following the circuit diagram. Double-check polarity.", tools_required=["Soldering iron", "Wire strippers", "Multimeter"], estimated_time_min=20),
        AssemblyStep(step_number=4, title="Final assembly", description="Attach remaining components, route cables cleanly, and secure with cable ties.", tools_required=["Cable ties", "Side cutters"], estimated_time_min=10),
        AssemblyStep(step_number=5, title="Test and calibrate", description="Power on and test all functions. Calibrate sensors and adjust mechanical alignments as needed.", tools_required=["Power supply", "Multimeter"], estimated_time_min=10),
    ]
    total = sum(s.estimated_time_min for s in steps)
    return AssemblyInstructions(steps=steps, total_time_min=total)


def _gripper_bom() -> tuple[BillOfMaterials, AssemblyInstructions]:
    items = [
        BomItem(name="MG996R Servo Motor", quantity=1, specification="180-degree digital servo, 13kg·cm torque, metal gear", unit_cost_gbp=8.50, category="Electronics"),
        BomItem(name="Arduino Nano", quantity=1, specification="ATmega328P, USB-C, 5V logic", unit_cost_gbp=6.99, category="Electronics"),
        BomItem(name="3D-Printed Gripper Fingers", quantity=2, specification="PLA, 80mm length, 3mm wall thickness", unit_cost_gbp=1.20, category="3D Printed"),
        BomItem(name="3D-Printed Base Plate", quantity=1, specification="PLA, 120x80x8mm, mounting holes", unit_cost_gbp=2.50, category="3D Printed"),
        BomItem(name="M3x12mm Socket Cap Screws", quantity=8, specification="Stainless steel, Grade A2-70", unit_cost_gbp=0.15, category="Fasteners"),
        BomItem(name="M3 Nylon Lock Nuts", quantity=8, specification="Stainless steel", unit_cost_gbp=0.08, category="Fasteners"),
        BomItem(name="Rubber Grip Pads", quantity=2, specification="Silicone, 25x15x3mm, self-adhesive", unit_cost_gbp=0.90, category="Off-the-shelf"),
        BomItem(name="Jumper Wires", quantity=1, specification="Male-to-male, 20cm, 10-pack assorted", unit_cost_gbp=2.50, category="Electronics"),
        BomItem(name="USB-A to USB-C Cable", quantity=1, specification="1m data+power cable", unit_cost_gbp=3.99, category="Electronics"),
        BomItem(name="Heat-Shrink Tubing", quantity=1, specification="Assorted sizes, 2:1 ratio, 30pc", unit_cost_gbp=2.99, category="Electronics"),
    ]
    bom = _make_bom(items)

    steps = [
        AssemblyStep(step_number=1, title="Print gripper parts", description="3D print the base plate and two gripper fingers in PLA at 0.2mm layer height, 30% infill. Add heat-set inserts for M3 screws.", tools_required=["3D printer", "Soldering iron (for inserts)"], estimated_time_min=90),
        AssemblyStep(step_number=2, title="Attach servo to base", description="Mount the MG996R servo centrally on the base plate using the included screws. Ensure the output shaft is oriented upward.", tools_required=["Phillips screwdriver"], estimated_time_min=5),
        AssemblyStep(step_number=3, title="Assemble finger mechanism", description="Attach both gripper fingers to the servo horn using M3 screws and lock nuts. Verify symmetrical movement.", tools_required=["Allen key (2.5mm)", "Small spanner"], estimated_time_min=10),
        AssemblyStep(step_number=4, title="Apply grip pads", description="Peel and stick silicone grip pads to the inner face of each gripper finger.", tools_required=[], estimated_time_min=2),
        AssemblyStep(step_number=5, title="Wire electronics", description="Connect the servo signal wire to Arduino Nano pin D9, power to 5V, and ground to GND. Use heat-shrink on all connections.", tools_required=["Soldering iron", "Heat gun"], estimated_time_min=15),
        AssemblyStep(step_number=6, title="Upload firmware & test", description="Flash the servo sweep test sketch via USB. Verify full open/close range without binding.", tools_required=["Computer", "Arduino IDE"], estimated_time_min=10),
    ]

    return bom, AssemblyInstructions(steps=steps, total_time_min=sum(s.estimated_time_min for s in steps))


def _plant_pot_bom() -> tuple[BillOfMaterials, AssemblyInstructions]:
    items = [
        BomItem(name="Capacitive Soil Moisture Sensor v1.2", quantity=1, specification="3.3-5V, analog output, corrosion-resistant", unit_cost_gbp=3.49, category="Electronics"),
        BomItem(name="Arduino Nano", quantity=1, specification="ATmega328P, USB-C, 5V logic", unit_cost_gbp=6.99, category="Electronics"),
        BomItem(name="Mini Water Pump", quantity=1, specification="3-6V DC submersible, 120L/h flow rate", unit_cost_gbp=4.50, category="Electronics"),
        BomItem(name="Silicone Tubing", quantity=1, specification="4mm ID x 6mm OD, 1 metre", unit_cost_gbp=2.99, category="Off-the-shelf"),
        BomItem(name="3D-Printed Pot Body", quantity=1, specification="PETG, 120mm diameter, integrated reservoir channel", unit_cost_gbp=4.50, category="3D Printed"),
        BomItem(name="3D-Printed Base Tray", quantity=1, specification="PETG, 130mm diameter, drainage collection", unit_cost_gbp=2.00, category="3D Printed"),
        BomItem(name="N-Channel MOSFET", quantity=1, specification="IRLZ44N, logic-level gate, TO-220", unit_cost_gbp=1.20, category="Electronics"),
        BomItem(name="10kΩ Resistor", quantity=1, specification="1/4W, 5% tolerance, through-hole", unit_cost_gbp=0.05, category="Electronics"),
        BomItem(name="9V Battery Holder", quantity=1, specification="PP3 snap connector with leads", unit_cost_gbp=1.50, category="Electronics"),
        BomItem(name="9V Battery", quantity=1, specification="Alkaline PP3", unit_cost_gbp=3.00, category="Off-the-shelf"),
    ]
    bom = _make_bom(items)

    steps = [
        AssemblyStep(step_number=1, title="Print pot components", description="3D print the pot body and base tray in PETG for water resistance. Use 0.2mm layers, 25% infill.", tools_required=["3D printer"], estimated_time_min=120),
        AssemblyStep(step_number=2, title="Install moisture sensor", description="Insert the capacitive moisture sensor into the pot body through the pre-designed slot. Ensure the sensing area will be in contact with soil.", tools_required=[], estimated_time_min=5),
        AssemblyStep(step_number=3, title="Mount water pump", description="Place the submersible pump in the reservoir section. Route silicone tubing from pump outlet to the soil delivery point.", tools_required=["Scissors"], estimated_time_min=10),
        AssemblyStep(step_number=4, title="Wire the circuit", description="Connect moisture sensor to Arduino A0, pump through MOSFET on pin D5 with 10kΩ pull-down resistor. Power via 9V battery.", tools_required=["Soldering iron", "Wire strippers"], estimated_time_min=20),
        AssemblyStep(step_number=5, title="Upload code & calibrate", description="Flash the auto-watering sketch. Calibrate dry/wet thresholds by testing with dry and saturated soil samples.", tools_required=["Computer", "Arduino IDE"], estimated_time_min=15),
    ]

    return bom, AssemblyInstructions(steps=steps, total_time_min=sum(s.estimated_time_min for s in steps))


def _coin_sorter_bom() -> tuple[BillOfMaterials, AssemblyInstructions]:
    items = [
        BomItem(name="28BYJ-48 Stepper Motor", quantity=1, specification="5V unipolar stepper with ULN2003 driver board", unit_cost_gbp=4.99, category="Electronics"),
        BomItem(name="Arduino Uno R3", quantity=1, specification="ATmega328P, USB-B, 5V logic", unit_cost_gbp=9.99, category="Electronics"),
        BomItem(name="3D-Printed Sorting Ramp", quantity=1, specification="PLA, graduated slot widths for UK coins", unit_cost_gbp=3.50, category="3D Printed"),
        BomItem(name="3D-Printed Hopper", quantity=1, specification="PLA, funnel design, 60mm top diameter", unit_cost_gbp=2.00, category="3D Printed"),
        BomItem(name="3D-Printed Collection Bins", quantity=4, specification="PLA, labelled for 1p/5p/10p/£1", unit_cost_gbp=1.50, category="3D Printed"),
        BomItem(name="3D-Printed Base", quantity=1, specification="PLA, 200x150x8mm platform", unit_cost_gbp=3.00, category="3D Printed"),
        BomItem(name="M3x8mm Pan Head Screws", quantity=12, specification="Stainless steel", unit_cost_gbp=0.10, category="Fasteners"),
        BomItem(name="Rubber Feet", quantity=4, specification="Self-adhesive, 10mm diameter", unit_cost_gbp=0.25, category="Off-the-shelf"),
        BomItem(name="USB-A to USB-B Cable", quantity=1, specification="1m, for Arduino power + programming", unit_cost_gbp=3.49, category="Electronics"),
    ]
    bom = _make_bom(items)

    steps = [
        AssemblyStep(step_number=1, title="Print all components", description="Print the sorting ramp, hopper, 4 collection bins, and base plate in PLA. 0.15mm layer height for the ramp (precision slots).", tools_required=["3D printer", "Calipers"], estimated_time_min=180),
        AssemblyStep(step_number=2, title="Assemble base and ramp", description="Screw the sorting ramp onto the base at a 15-degree angle. Attach collection bins below each slot.", tools_required=["Phillips screwdriver"], estimated_time_min=15),
        AssemblyStep(step_number=3, title="Install hopper and motor", description="Mount the stepper motor under the hopper. The rotating disc feeds coins one at a time onto the ramp.", tools_required=["Phillips screwdriver"], estimated_time_min=10),
        AssemblyStep(step_number=4, title="Wire electronics", description="Connect ULN2003 driver to Arduino pins D8-D11. Power stepper from Arduino 5V.", tools_required=["Jumper wires"], estimated_time_min=10),
        AssemblyStep(step_number=5, title="Calibrate and test", description="Test with each UK coin denomination. Adjust slot widths with a file if needed.", tools_required=["Small file", "UK coins"], estimated_time_min=20),
    ]

    return bom, AssemblyInstructions(steps=steps, total_time_min=sum(s.estimated_time_min for s in steps))


def _lamp_bom() -> tuple[BillOfMaterials, AssemblyInstructions]:
    items = [
        BomItem(name="5V LED Strip (Warm White)", quantity=1, specification="2835 SMD, 60 LEDs/m, 30cm length, USB-powered", unit_cost_gbp=4.99, category="Electronics"),
        BomItem(name="3D-Printed Lampshade", quantity=1, specification="PLA (translucent white), conical, 70mm diameter", unit_cost_gbp=2.50, category="3D Printed"),
        BomItem(name="3D-Printed Base", quantity=1, specification="PLA, weighted, 80mm diameter, cable channel", unit_cost_gbp=2.00, category="3D Printed"),
        BomItem(name="Aluminium Tube", quantity=1, specification="8mm OD, 300mm length, anodised", unit_cost_gbp=3.50, category="Structural"),
        BomItem(name="Toggle Switch", quantity=1, specification="SPST, 6A 250V, panel mount", unit_cost_gbp=1.20, category="Electronics"),
        BomItem(name="USB-A Cable", quantity=1, specification="1.5m, cut and solder for power", unit_cost_gbp=2.00, category="Electronics"),
        BomItem(name="M3 Grub Screws", quantity=2, specification="M3x6mm, for tube clamping", unit_cost_gbp=0.15, category="Fasteners"),
    ]
    bom = _make_bom(items)
    steps = [
        AssemblyStep(step_number=1, title="Print shade and base", description="Print lampshade in translucent PLA and base in dark PLA.", tools_required=["3D printer"], estimated_time_min=60),
        AssemblyStep(step_number=2, title="Assemble stem", description="Insert aluminium tube into base, secure with grub screws.", tools_required=["Allen key (1.5mm)"], estimated_time_min=5),
        AssemblyStep(step_number=3, title="Wire LED and switch", description="Solder USB cable to LED strip through toggle switch. Route wiring through tube.", tools_required=["Soldering iron", "Wire strippers"], estimated_time_min=15),
        AssemblyStep(step_number=4, title="Attach shade and test", description="Press-fit lampshade onto tube top. Plug in and verify even illumination.", tools_required=[], estimated_time_min=5),
    ]
    return bom, AssemblyInstructions(steps=steps, total_time_min=sum(s.estimated_time_min for s in steps))


def _phone_stand_bom() -> tuple[BillOfMaterials, AssemblyInstructions]:
    items = [
        BomItem(name="3D-Printed Back Support", quantity=1, specification="PLA, 80x100mm, 15-degree angle", unit_cost_gbp=2.00, category="3D Printed"),
        BomItem(name="3D-Printed Base", quantity=1, specification="PLA, 100x80x12mm, weighted", unit_cost_gbp=2.50, category="3D Printed"),
        BomItem(name="3D-Printed Front Lip", quantity=1, specification="PLA, 70x8x15mm, phone retention", unit_cost_gbp=0.80, category="3D Printed"),
        BomItem(name="Silicone Bumper Pads", quantity=4, specification="Clear, 8mm diameter, self-adhesive", unit_cost_gbp=0.50, category="Off-the-shelf"),
        BomItem(name="Rubber Sheet", quantity=1, specification="1mm thick, 100x80mm, anti-slip base", unit_cost_gbp=1.50, category="Off-the-shelf"),
        BomItem(name="M3x10mm Countersunk Screws", quantity=4, specification="Stainless steel", unit_cost_gbp=0.12, category="Fasteners"),
    ]
    bom = _make_bom(items)
    steps = [
        AssemblyStep(step_number=1, title="Print all parts", description="Print back support, base, and front lip in PLA, 0.2mm layers, 40% infill for weight.", tools_required=["3D printer"], estimated_time_min=45),
        AssemblyStep(step_number=2, title="Assemble stand", description="Screw back support into base at angle. Attach front lip.", tools_required=["Allen key (2mm)"], estimated_time_min=5),
        AssemblyStep(step_number=3, title="Apply pads", description="Stick silicone bumpers on phone-contact surfaces. Apply rubber sheet to base underside.", tools_required=[], estimated_time_min=3),
    ]
    return bom, AssemblyInstructions(steps=steps, total_time_min=sum(s.estimated_time_min for s in steps))


def _drone_bom() -> tuple[BillOfMaterials, AssemblyInstructions]:
    items = [
        BomItem(name="F450 Quadcopter Frame", quantity=1, specification="450mm wheelbase, with integrated PDB", unit_cost_gbp=12.99, category="Structural"),
        BomItem(name="2212 920KV Brushless Motors", quantity=4, specification="CW/CCW pair, bullet connectors", unit_cost_gbp=7.50, category="Electronics"),
        BomItem(name="30A ESC", quantity=4, specification="BLHeli_S firmware, 2-4S LiPo", unit_cost_gbp=6.99, category="Electronics"),
        BomItem(name="1045 Propellers", quantity=4, specification="10x4.5 inch, CW/CCW pair, nylon", unit_cost_gbp=2.50, category="Mechanical"),
        BomItem(name="CC3D Flight Controller", quantity=1, specification="Open-source, LibrePilot compatible", unit_cost_gbp=14.99, category="Electronics"),
        BomItem(name="3S 2200mAh LiPo Battery", quantity=1, specification="11.1V, 25C discharge, XT60 connector", unit_cost_gbp=18.99, category="Electronics"),
        BomItem(name="FlySky FS-i6X Transmitter + Receiver", quantity=1, specification="2.4GHz, 6-channel, AFHDS 2A", unit_cost_gbp=39.99, category="Electronics"),
        BomItem(name="XT60 Connector Pair", quantity=2, specification="Male + Female, with 14AWG leads", unit_cost_gbp=1.50, category="Electronics"),
        BomItem(name="Battery Strap", quantity=2, specification="20x200mm, rubberised Velcro", unit_cost_gbp=1.00, category="Off-the-shelf"),
        BomItem(name="M3 Nylon Standoffs", quantity=8, specification="M3x11mm, for flight controller mounting", unit_cost_gbp=0.20, category="Fasteners"),
    ]
    bom = _make_bom(items)
    steps = [
        AssemblyStep(step_number=1, title="Assemble frame", description="Connect the 4 arms to the top and bottom plates using the included hardware.", tools_required=["Phillips screwdriver"], estimated_time_min=15),
        AssemblyStep(step_number=2, title="Mount motors", description="Attach motors to arm ends (CW motors on opposite arms). Secure with M3 screws.", tools_required=["Allen key (2mm)"], estimated_time_min=20),
        AssemblyStep(step_number=3, title="Install ESCs", description="Mount ESCs on arms with cable ties. Solder ESC power leads to the PDB.", tools_required=["Soldering iron", "Cable ties"], estimated_time_min=30),
        AssemblyStep(step_number=4, title="Wire flight controller", description="Mount FC on nylon standoffs. Connect ESC signal wires to correct channels.", tools_required=["Small screwdriver"], estimated_time_min=15),
        AssemblyStep(step_number=5, title="Bind receiver", description="Mount receiver, bind to transmitter. Connect to FC SBUS/PPM port.", tools_required=["Transmitter"], estimated_time_min=10),
        AssemblyStep(step_number=6, title="Attach propellers and test", description="Attach correct CW/CCW propellers. Calibrate ESCs, test motor spin direction without props first.", tools_required=["Prop tool", "Computer (for FC setup)"], estimated_time_min=20),
    ]
    return bom, AssemblyInstructions(steps=steps, total_time_min=sum(s.estimated_time_min for s in steps))


def _generic_bom(prompt: str) -> tuple[BillOfMaterials, AssemblyInstructions]:
    items = [
        BomItem(name="Arduino Nano", quantity=1, specification="ATmega328P, USB-C, 5V logic", unit_cost_gbp=6.99, category="Electronics"),
        BomItem(name="3D-Printed Enclosure (Top)", quantity=1, specification="PLA, custom dimensions per design", unit_cost_gbp=3.50, category="3D Printed"),
        BomItem(name="3D-Printed Enclosure (Bottom)", quantity=1, specification="PLA, with ventilation slots", unit_cost_gbp=3.00, category="3D Printed"),
        BomItem(name="M3 Hardware Kit", quantity=1, specification="Assorted M3 screws, nuts, washers (50pc)", unit_cost_gbp=4.99, category="Fasteners"),
        BomItem(name="Breadboard", quantity=1, specification="Half-size, 400 tie points", unit_cost_gbp=2.99, category="Electronics"),
        BomItem(name="Jumper Wire Kit", quantity=1, specification="M-M, M-F, F-F, 65pc assorted lengths", unit_cost_gbp=3.99, category="Electronics"),
        BomItem(name="5V Power Supply", quantity=1, specification="USB wall adapter, 2A output", unit_cost_gbp=5.99, category="Electronics"),
        BomItem(name="Rubber Feet", quantity=4, specification="Self-adhesive, 12mm, anti-vibration", unit_cost_gbp=0.30, category="Off-the-shelf"),
    ]
    bom = _make_bom(items)
    assembly = _generic_assembly(len(items))
    return bom, assembly
