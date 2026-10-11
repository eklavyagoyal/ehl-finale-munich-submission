"""Build competitors/themes.json: the shared theme taxonomy for BMW and competitor feedback.

Every BMW G60 VFC level2 topic is mapped to one coarse theme, so BMW verbatims and
competitor findings can be compared on the same axis.

Usage: .venv/bin/python competitors/tools/build_themes.py data/G60_feedback_hackathon.xlsx
"""

import json
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

THEMES = [
    ("powertrain_performance", "Antrieb & Leistung", "Engine/motor power, acceleration, transmission, start-stop, recuperation feel, drive readiness"),
    ("range_charging_efficiency", "Reichweite, Laden & Effizienz", "Electric range, charging speed/infrastructure/home charging, battery, fuel/energy consumption, refuelling"),
    ("ride_handling", "Fahrkomfort & Fahrdynamik", "Ride comfort, handling, steering, braking, suspension, tyres, driving modes"),
    ("adas_parking", "Fahrassistenz & Parken", "Cruise control, lane keeping, highway/hands-free assist, warnings, cameras, parking assist, remote parking"),
    ("hmi_infotainment", "Bedienung & Infotainment", "Touchscreen, operating concept, menus, displays, HUD, navigation, voice assistant, physical controls, in-car apps"),
    ("connectivity_app_digital", "Konnektivität, Smartphone & App", "CarPlay/Android Auto, phone pairing/charging, USB, eSIM/WiFi, companion app, remote services, OTA updates, digital upgrades"),
    ("access_locking", "Zugang, Türen & Kofferraumöffnung", "Locking/unlocking, keys, digital key, comfort access, door and tailgate operation, handles"),
    ("seats_comfort", "Sitze & Komfort", "Seat comfort, adjustment, heating/ventilation, massage, memory, general interior comfort"),
    ("climate", "Klima & Heizung", "Air conditioning, heating, blower, climate controls, heated steering wheel, sun protection"),
    ("space_practicality", "Platz & Praktikabilität", "Front/rear space, entry/exit, trunk and frunk, storage, cupholders, child seats, towing"),
    ("interior_design_quality", "Innenraum: Design & Materialqualität", "Interior styling, materials, trim, workmanship, ambient light, steering wheel feel, glass roof"),
    ("exterior_design", "Exterieur-Design", "Exterior styling, proportions, grille, bumpers, colours, wheels look"),
    ("lighting_visibility", "Licht & Sicht", "Headlights, exterior lighting, wipers, windshield, mirrors, all-round visibility"),
    ("audio_acoustics", "Audio & Akustik", "Sound system, cabin quietness, wind/road noise, engine sound, horn"),
    ("safety", "Sicherheit", "Perceived safety, crash safety, seat belts, emergency call"),
    ("equipment_value", "Ausstattung & Preis-Leistung (wahrgenommen)", "Standard vs optional equipment, missing features, perceived value for money (customer perception only, no price analysis)"),
    ("overall_quality_ownership", "Gesamtqualität & Ownership", "Overall impression, build quality and reliability in general, owner's manual, service, parts, 12V battery"),
    ("unclassified", "Nicht zuordenbar", "Generic praise/complaint without a clear topic"),
]

VFC_TO_THEME = {
    "powertrain_performance": [
        "Drivetrain", "Transmission", "Automatic engine start-stop function (MSA)", "Launch Control",
        "Shift paddle", "Operate selector lever", "Start engine/switch on drive readiness", "Starting engine",
        "Fuel tank", "Exhaust system", "Cooling", "Brake Energy Regeneration / recuperation",
    ],
    "range_charging_efficiency": [
        "Electric Range", "Public charging / external providers", "Charge high-voltage battery",
        "Wallbox, charging / home charging", "High voltage battery", "High voltage battery, preconditioning",
        "Opening/closing charging socket cover", "Charging cable", "Route optimized for charging",
        "High-voltage charging power socket", "Bidirectional charging", "Fuel filler flap , open / close",
    ],
    "ride_handling": [
        "Handling / Riding", "Drive, driving dynamics and chassis, overall technology", "Cushioning / damping vehicle",
        "Steering", "Braking", "Wheels / tires", "RSC tire", "Tirefit", "ground clearance",
        "Self-leveling suspension", "Dynamic Stability Control", "My Modes / driving experience", "Experience Modes",
        "Automatic-hold", "Parking brake", "Pedals, operate", "Tire pressure control",
    ],
    "adas_parking": [
        "Highway assistant", "(Active) cruise control", "Parking Assistant",
        "Driver assistance, automated driving, overall technology", "Lane departure warning",
        "Steering and lane guide assist", "Blind spot monitoring", "Remote controlled parking", "Speed Limit Assistant",
        "Front collision warning", "Cross Traffic Warning Rear with Brake Intervention", "Back-up Assistant",
        "Fatigue Alert", "High-beam assistant", "Lane Change Assistant", "Surround View", "Rear view camera",
        "Park Distance Control (PDC)", "All-round view", "Side View", "Night Vision", "Traffic Light And Sign Warning",
        "Emergency Stop Assistant", "Intersection Warning with Brake Intervention", "Rear-end collision warning",
        "Drive Recorder", "Interior camera",
    ],
    "hmi_infotainment": [
        "Touch screen, operation", "Operating concept, operating system", "ConnectedDrive and Infotainment, overall technology",
        "Instrument cluster", "Navigation", "Head-Up Display", "Radio function", "Gesture control",
        "Voice control / speech recognition", "Intelligent Personal Assistant", "Intelligent Personal Assistant, activation word",
        "Apps (in-car)", "Video: playback / streaming", "Controller operation", "Multi-function steering wheel operation",
        "Touch Command", "Display, time", "Map update", "Smart POI search", "Real Time Traffic Information (RTTI)",
        "Traffic Camera Information", "Driver profile", "Light switch operating unit", "Roof function centre",
        "Rear seat entertainment", "CD / DVD changer, playback", "Resting state after door opening",
    ],
    "connectivity_app_digital": [
        "Apple CarPlay", "Android Auto", "Mobile device, wireless charging", "Manage / pair mobile device (Bluetooth)",
        "USB port", "Personal eSIM", "WiFi hotspot", "Wi-Fi connection", "Screen mirroring", "Priorities for telephones",
        "My BMW App / MINI App", "Remote Engine Start (My BMW App / MINI App)",
        "Remote Services & Remote Keyless Entry (My BMW App/MINI App)", "Remote 3D View (My BMW App / MINI App)",
        "Remote interior camera (My BMW App / MINI App)", "Teleservices",
        "ConnectedDrive services (smartphone) technology overall", "BMW ConnectedDrive upgrades/ MINI CONNECTED upgrades",
        "My BMW / MINI Portal", "Customer Account (My BMW / MINI Portal)", "BMW Online / MINI Online", "Apps (smartphone)",
        "Driver's Guide App", "Remote Software Upgrade/RSU",
    ],
    "access_locking": [
        "Vehicle, lock / unlock", "Door, open / close", "Comfort Access", "Vehicle key", "Digital Key", "Display key",
        "Trunk lid, open / close", "non-contact trunk lid opening", "Trunk lid", "Outer door handle, front",
        "Outer door handle, rear", "Automatic doors", "Door, front", "Remote Engine Start (Vehicle Key )",
        "Anti-theft alarm system", "Side window, open / close", "Hood, open / close", "Garage door opener",
        "Interior mirror, garage door opener", "Child safety latch",
    ],
    "seats_comfort": [
        "Seats", "Seating, ventilate / heat", "Seat massage", "Seat memory", "Adjustment of lower lumbar support",
        "Headrest, adjust", "Interior comfort",
    ],
    "climate": [
        "Vehicle, climatization", "Air conditioning, setting", "Blower function", "Air conditioning control panel",
        "Air conditioning, overall technology", "Heated steering wheel", "Panel heating", "Auxiliary heater function",
        "Heated rear window", "Sun protection",
    ],
    "space_practicality": [
        "Space / spatial impression", "Luggage compartment", "Storage compartments", "Cupholder", "Glove box",
        "Center console, front", "Center armrest, front", "Frunk", "Through-loading facility", "Trunk light",
        "Vehicle, access and exit", "Child restraint seat, use", "Grab handle", "Floor mat", "Trailer, use",
        "Running board", "12 V connection",
    ],
    "interior_design_quality": [
        "Interior design", "Instrument panel", "Ambient light", "Vehicle interior, lighting", "Upholstery / interior trim",
        "Door, finisher panel, front", "Interior", "Steering wheel", "Interior rearview mirror", "Sun visor, front",
        "Panorama glass roof", "Roof",
    ],
    "exterior_design": [
        "Exterior design", "Exterior", "Radiator grille", "Bumper, front", "Bumper, rear", "Side sill trim panel", "Hood",
        "Opening / closing convertible top / hardtop",
    ],
    "lighting_visibility": [
        "Exterior lighting", "Fog light", "Flashing", "Windshield wiper", "Rear wiper", "Rain sensor mode", "Windshield",
        "Washer fluid, top up", "Exterior rearview mirror", "Welcome Light Carpet", "Wash / wipe switch",
    ],
    "audio_acoustics": [
        "Audio mode, sound", "Interior acoustics", "Engine acoustics / engine sound", "Horns",
    ],
    "safety": [
        "Impression of safety", "Vehicle safety, overall technology", "Seat belts", "Emergency request",
    ],
    "overall_quality_ownership": [
        "Body equipment, overall technology", "Owner's Manual", "General enquiry: customer feedback",
        "Accessories / Parts", "Vehicle battery", "Engine oil", "Towing eye", "Caring Car",
    ],
    "unclassified": ["no_class_found"],
}

# VFC level3 values that describe perceived value / equipment gaps regardless of the level2 component.
LEVEL3_TO_THEME = {
    "Dislike: price-performance ratio": "equipment_value",
    "Like: price-performance ratio": "equipment_value",
    "Vehicle equipment: not available": "equipment_value",
    "Vehicle equipment: not standard / too costly": "equipment_value",
    "Like: vehicle equipment": "equipment_value",
}

FEEDBACK_TYPES = ["Likes", "Wants", "Difficult to Use", "Defect"]
COMPARISON = ["competitor_advantage", "bmw_advantage", "parity"]
EVIDENCE_TIERS = {
    "A": "Customer voice: owner review, owner forum post, owner survey",
    "B": "Professional test/review by automotive press",
    "C": "Manufacturer specification or configurator",
    "D": "Announcement, leak or forecast (forward-looking assumption)",
}


def main(feedback_path: str) -> None:
    df = pd.read_excel(feedback_path, dtype=str)
    # Some BMW topic names contain non-breaking spaces (e.g. "ground clearance").
    df["Vfc level2 Name"] = df["Vfc level2 Name"].str.replace("\xa0", " ")
    counts = df.groupby("Vfc level2 Name")["ID"].nunique()

    mapping = {topic: theme for theme, topics in VFC_TO_THEME.items() for topic in topics}
    dupes = [t for theme, topics in VFC_TO_THEME.items() for t in topics if list(mapping).count(t) > 1]
    assert not dupes, dupes

    unmapped = sorted(t for t in counts.index if t not in mapping)
    unknown = sorted(t for t in mapping if t not in counts.index)
    if unmapped:
        sys.exit(f"Unmapped VFC level2 topics: {unmapped}")
    if unknown:
        print(f"Note: mapped but absent from this file: {unknown}")

    theme_ids = {t[0] for t in THEMES}
    assert set(mapping.values()) <= theme_ids and set(LEVEL3_TO_THEME.values()) <= theme_ids

    out = {
        "version": 1,
        "description": "Shared theme taxonomy so BMW G60 feedback and competitor findings can be compared. "
        "BMW feedback: theme = LEVEL3 override if present, else VFC level2 mapping; empty level2 -> unclassified. "
        "Replace non-breaking spaces in VFC names with plain spaces before lookup.",
        "themes": [{"id": i, "label_de": de, "scope": desc} for i, de, desc in THEMES],
        "feedback_types": FEEDBACK_TYPES,
        "comparison_values": COMPARISON,
        "evidence_tiers": EVIDENCE_TIERS,
        "vfc_level3_to_theme": LEVEL3_TO_THEME,
        "vfc_level2_to_theme": {t: mapping[t] for t in sorted(mapping)},
        "vfc_level2_g60_feedback_counts": {t: int(n) for t, n in counts.sort_values(ascending=False).items()},
    }
    target = Path(__file__).resolve().parents[1] / "themes.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")

    per_theme = pd.Series({t: 0 for t in theme_ids})
    for topic, n in counts.items():
        per_theme[mapping[topic]] += n
    print(per_theme.sort_values(ascending=False).to_string())
    print(f"wrote {target}")


if __name__ == "__main__":
    main(sys.argv[1])
