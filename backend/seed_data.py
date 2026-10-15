import os
import datetime
from PIL import Image, ImageDraw, ImageFont
from database import SessionLocal, engine, Base
from models import User, Authority, Zone, RoutingRule, Incident, ReportEvidence, StatusHistory, Feedback, Notification
from auth import hash_password
from config import SEED_ASSETS_DIR

def create_sample_image(filename: str, title: str, subtitle: str, bg_color: tuple, accent_color: tuple):
    filepath = os.path.join(SEED_ASSETS_DIR, filename)
    if os.path.exists(filepath):
        return f"/seed_assets/{filename}"

    img = Image.new("RGB", (800, 500), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Draw header banner
    draw.rectangle([0, 0, 800, 70], fill=accent_color)
    draw.text((30, 25), "ENVI CONNECT - INCIDENT EVIDENCE", fill=(255, 255, 255))

    # Draw inner border
    draw.rectangle([20, 90, 780, 470], outline=accent_color, width=3)

    # Draw title and subtitle
    draw.text((50, 140), title, fill=(240, 250, 245))
    draw.text((50, 200), subtitle, fill=(180, 220, 210))
    draw.text((50, 280), f"GPS Tagged: Tirupati Geo-Coordinates", fill=(130, 190, 175))
    draw.text((50, 320), f"Timestamp: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", fill=(130, 190, 175))
    draw.text((50, 400), "STATUS: VERIFIED ENVIRONMENTAL EVIDENCE", fill=accent_color)

    try:
        img.save(filepath, "JPEG", quality=90)
    except Exception as e:
        print(f"[seed_data] Notice: Could not write {filepath}: {e}")
    return f"/seed_assets/{filename}"


def generate_seed_assets():
    assets = {
        "dumping_before.jpg": ("ILLEGAL MUNICIPAL DUMPING (BEFORE)", "Overflowing solid waste, plastic bags & debris on public pavement", (35, 25, 20), (220, 70, 50)),
        "dumping_after.jpg": ("MCT SANITATION CLEARANCE (AFTER PROOF)", "Complete waste cleared, sanitized with bleaching powder, barricaded", (10, 45, 35), (6, 214, 160)),
        "water_before.jpg": ("INDUSTRIAL CHEMICAL EFFLUENT (BEFORE)", "Untreated purple frothing runoff discharging into Swarnamukhi stream", (25, 35, 50), (220, 50, 100)),
        "water_after.jpg": ("STREAM RESTORATION & DRAINAGE SEALED (AFTER PROOF)", "Effluent line plugged, biological aerator placed, clear water flow restored", (10, 45, 40), (6, 214, 160)),
        "air_before.jpg": ("CHIMNEY BLACK SOOT EMISSION (BEFORE)", "Dense toxic hydrocarbon smog billowing from manufacturing unit", (40, 40, 40), (230, 90, 40)),
        "air_after.jpg": ("WET SCRUBBER & FILTERS COMMISSIONED (AFTER PROOF)", "APPCB inspected: Zero visible emission, online continuous monitoring active", (15, 45, 35), (6, 214, 160)),
        "tree_before.jpg": ("ILLEGAL RED SANDERS TREE CUTTING (BEFORE)", "Two mature trees felled illegally near reserve forest boundary", (45, 30, 15), (200, 80, 30)),
        "tree_after.jpg": ("FOREST WING FENCING & SAPLINGS PLANTED (AFTER PROOF)", "Timber seized, 20 compensatory saplings planted with protective mesh", (12, 50, 30), (6, 214, 160)),
        "noise_before.jpg": ("COMMERCIAL GENERATOR NOISE (BEFORE)", "High decibel generator running in silent hospital corridor exceeding 95 dB", (30, 30, 50), (210, 120, 30)),
        "noise_after.jpg": ("ACOUSTIC ENCLOSURE INSTALLED (AFTER PROOF)", "Sealed canopy installed, ambient sound reduced to 48 dB (within limit)", (10, 40, 35), (6, 214, 160)),
        "default_dumping.jpg": ("ENVIRONMENTAL CITIZEN EVIDENCE", "Photographic documentation recorded via Envi Connect Citizen App", (20, 35, 30), (6, 214, 160))
    }

    urls = {}
    for filename, (title, sub, bg, acc) in assets.items():
        urls[filename] = create_sample_image(filename, title, sub, bg, acc)
    return urls


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if already seeded
    if db.query(User).count() > 0 and db.query(Incident).count() >= 25:
        print("Database already seeded with demo data.")
        db.close()
        return

    print("Generating demo image assets...")
    img_urls = generate_seed_assets()

    print("Seeding authorities...")
    authorities_data = [
        {
            "name": "Municipal Corporation of Tirupati (MCT)",
            "code": "MCT",
            "department": "Public Health & Solid Waste Management",
            "jurisdiction": "Tirupati City Corporation limits (Wards 1–50)",
            "contact_email": "mct.health@tirupati.gov.in",
            "phone": "+91 877 2256789",
            "description": "Responsible for municipal garbage clearance, street sanitation, drainage maintenance, and urban noise enforcement."
        },
        {
            "name": "Andhra Pradesh Pollution Control Board (APPCB)",
            "code": "APPCB",
            "department": "Regional Office Tirupati - Environmental Surveillance",
            "jurisdiction": "Tirupati District & Industrial Belts (Renigunta, Settipalli)",
            "contact_email": "ro.tirupati@appcb.gov.in",
            "phone": "+91 877 2284123",
            "description": "Regulates industrial emissions, river effluent discharge, air quality index, and hazardous waste."
        },
        {
            "name": "Tirupati Forest Division",
            "code": "FOREST",
            "department": "Seshachalam Biosphere Reserve & Social Forestry",
            "jurisdiction": "Alipiri Foothills, Karakambadi Buffer, Kapilatheertham Forest Fringe",
            "contact_email": "dfo.tirupati@apforest.gov.in",
            "phone": "+91 877 2231456",
            "description": "Protects endangered flora, red sanders timber, wildlife corridors, and prevents hill deforestation."
        },
        {
            "name": "Tirupati Urban Development Authority (TUDA)",
            "code": "TUDA",
            "department": "Urban Planning & Environmental Monitoring",
            "jurisdiction": "Greater Tirupati Metropolitan & Peripheral Townships",
            "contact_email": "planning@tuda.ap.gov.in",
            "phone": "+91 877 2225500",
            "description": "Monitors lake conservation, green belt compliance, unauthorized construction, and civic hazards."
        }
    ]

    auth_objs = {}
    for a_data in authorities_data:
        existing = db.query(Authority).filter(Authority.code == a_data["code"]).first()
        if not existing:
            existing = Authority(**a_data)
            db.add(existing)
            db.commit()
            db.refresh(existing)
        auth_objs[a_data["code"]] = existing

    print("Seeding zones around Tirupati, AP...")
    zones_data = [
        {
            "name": "Tirupati Central Zone",
            "code": "TCZ",
            "ward_numbers": "Wards 1–15 (Bhavani Nagar, Gandhi Road, Railway Station, Korlagunta)",
            "center_lat": 13.6288,
            "center_lng": 79.4192,
            "radius_km": 3.5,
            "description": "High density commercial hub, railway junction, community markets, and administrative center."
        },
        {
            "name": "Alipiri Foothills & Pilgrimage Corridor",
            "code": "AFC",
            "ward_numbers": "Wards 16–22 (Alipiri Gate, Kapilatheertham, SVIMS, Balaji Colony)",
            "center_lat": 13.6500,
            "center_lng": 79.3900,
            "radius_km": 4.0,
            "description": "Gateway to Tirumala hills, eco-fragile pilgrim zone with high pedestrian traffic."
        },
        {
            "name": "Renigunta Industrial & Logistics Belt",
            "code": "RIB",
            "ward_numbers": "Wards 23–31 (Renigunta Airport Road, Settipalli Industrial Park)",
            "center_lat": 13.6400,
            "center_lng": 79.5100,
            "radius_km": 5.0,
            "description": "Manufacturing units, electronic clusters, textile dyeing, and cargo transit points."
        },
        {
            "name": "Chandragiri Heritage & River Basin",
            "code": "CHB",
            "ward_numbers": "Wards 32–40 (Chandragiri Town, Swarnamukhi River West, Mallavaram)",
            "center_lat": 13.5850,
            "center_lng": 79.3150,
            "radius_km": 4.5,
            "description": "Agricultural wetlands, historical monument precinct, and Swarnamukhi river drainage."
        },
        {
            "name": "Karakambadi Green Buffer & Reservoir",
            "code": "KGB",
            "ward_numbers": "Wards 41–50 (Karakambadi Road, Mangalam, Cherlopalli Reservoir)",
            "center_lat": 13.6700,
            "center_lng": 79.4600,
            "radius_km": 4.0,
            "description": "Percolation tanks, farm lands, social forestry plantation, and residential extensions."
        }
    ]

    zone_objs = {}
    for z_data in zones_data:
        existing = db.query(Zone).filter(Zone.code == z_data["code"]).first()
        if not existing:
            existing = Zone(**z_data)
            db.add(existing)
            db.commit()
            db.refresh(existing)
        zone_objs[z_data["code"]] = existing

    print("Seeding demo users...")
    users_data = [
        {
            "email": "citizen@envi.gov",
            "full_name": "Rajesh Sharma",
            "password": "citizen123",
            "role": "citizen",
            "phone": "+91 98480 12345"
        },
        {
            "email": "mct.officer@tirupati.gov",
            "full_name": "Dr. K. Srinivas Rao",
            "password": "mct123",
            "role": "authority",
            "authority_id": auth_objs["MCT"].id,
            "phone": "+91 98480 23456"
        },
        {
            "email": "appcb.officer@appcb.gov",
            "full_name": "P. V. Ramana",
            "password": "appcb123",
            "role": "authority",
            "authority_id": auth_objs["APPCB"].id,
            "phone": "+91 98480 34567"
        },
        {
            "email": "forest.officer@apforest.gov",
            "full_name": "S. Venkat Reddy",
            "password": "forest123",
            "role": "authority",
            "authority_id": auth_objs["FOREST"].id,
            "phone": "+91 98480 45678"
        },
        {
            "email": "ngo@greenaction.org",
            "full_name": "Ananya Deshmukh",
            "password": "ngo123",
            "role": "ngo",
            "phone": "+91 98480 56789"
        },
        {
            "email": "admin@envi.gov",
            "full_name": "System Administrator",
            "password": "admin123",
            "role": "admin",
            "phone": "+91 98480 99999"
        }
    ]

    user_objs = {}
    for u_data in users_data:
        existing = db.query(User).filter(User.email == u_data["email"]).first()
        if not existing:
            existing = User(
                email=u_data["email"],
                full_name=u_data["full_name"],
                hashed_password=hash_password(u_data["password"]),
                role=u_data["role"],
                authority_id=u_data.get("authority_id"),
                phone=u_data.get("phone")
            )
            db.add(existing)
            db.commit()
            db.refresh(existing)
        user_objs[u_data["email"]] = existing

    print("Seeding routing rules...")
    default_rules = [
        {"category": "illegal_dumping", "authority_id": auth_objs["MCT"].id, "priority": 10},
        {"category": "noise", "authority_id": auth_objs["MCT"].id, "priority": 10},
        {"category": "air_pollution", "authority_id": auth_objs["APPCB"].id, "priority": 10},
        {"category": "water_pollution", "authority_id": auth_objs["APPCB"].id, "priority": 10},
        {"category": "deforestation", "authority_id": auth_objs["FOREST"].id, "priority": 10},
        {"category": "other", "authority_id": auth_objs["TUDA"].id, "priority": 5}
    ]

    for r in default_rules:
        existing = db.query(RoutingRule).filter(
            RoutingRule.category == r["category"],
            RoutingRule.zone_id == None
        ).first()
        if not existing:
            rule = RoutingRule(**r, is_active=True)
            db.add(rule)
    db.commit()

    print("Seeding 30 sample environmental incidents around Tirupati...")
    now = datetime.datetime.utcnow()

    # 30 Sample incidents covering all 6 categories, 5 zones, all 4 severities, and varied statuses
    reports_data = [
        # --- Resolved Incidents with Before & After and Verified Feedback ---
        {
            "title": "Overflowing Garbage Dumper Spilling into Vegetable Market",
            "description": "Massive pile of rotting municipal solid waste and wet garbage dumped directly beside the market stalls, causing unbearable stench and attracting stray cattle.",
            "category": "illegal_dumping",
            "severity": "high",
            "status": "closed",
            "lat": 13.6295, "lng": 79.4210,
            "address": "Gandhi Road Market, Tirupati Central",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["dumping_before.jpg"],
            "after_img": img_urls["dumping_after.jpg"],
            "res_notes": "Sanitation squad deployed with two compactor trucks. Entire 4-ton waste cleared, bleaching powder spread, and warning signboards erected.",
            "resolved_ago": 3, "created_ago": 6,
            "reporters_count": 3,
            "feedback": {"fixed": True, "rating": 5, "comments": "Outstanding prompt action by MCT! The foul odor is completely gone and street is clean."}
        },
        {
            "title": "Untreated Textile Dye Effluent Leaking into Irrigation Stream",
            "description": "Purple chemical water with heavy sulfur smell gushing from an illegal underground pipe directly into the canal used by local farmers.",
            "category": "water_pollution",
            "severity": "critical",
            "status": "closed",
            "lat": 13.6415, "lng": 79.5120,
            "address": "Settipalli Industrial Zone, Renigunta",
            "zone_code": "RIB", "auth_code": "APPCB",
            "before_img": img_urls["water_before.jpg"],
            "after_img": img_urls["water_after.jpg"],
            "res_notes": "APPCB task force inspected site and seized the illegal bypass pipe. Show-cause notice issued with penalty of ₹2,50,000. Effluent diverted to CETP.",
            "resolved_ago": 2, "created_ago": 5,
            "reporters_count": 4,
            "feedback": {"fixed": True, "rating": 5, "comments": "Water is clear again and farmers are greatly relieved. Thank you for the quick intervention!"}
        },
        {
            "title": "Heavy Diesel Generator Without Acoustic Shield Near Maternity Clinic",
            "description": "Commercial diesel generator vibrating the walls of the adjacent health clinic and exceeding 92 decibels throughout patient resting hours.",
            "category": "noise",
            "severity": "medium",
            "status": "resolved",
            "lat": 13.6320, "lng": 79.4180,
            "address": "Korlagunta Main Road, Ward 12",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["noise_before.jpg"],
            "after_img": img_urls["noise_after.jpg"],
            "res_notes": "Commercial establishment compelled to erect soundproofing canopy. Decibel level tested at 48 dB.",
            "resolved_ago": 1, "created_ago": 4,
            "reporters_count": 2,
            "feedback": {"fixed": True, "rating": 4, "comments": "Much quieter now. Patients can rest peacefully."}
        },
        {
            "title": "Unauthorized Clearing of Avenue Banyan Trees for Signboard",
            "description": "Private contractor chopped off large branches and girdled two 40-year-old banyan trees along the bypass road.",
            "category": "deforestation",
            "severity": "high",
            "status": "closed",
            "lat": 13.6520, "lng": 79.3920,
            "address": "Alipiri Bypass Road, Foothills Zone",
            "zone_code": "AFC", "auth_code": "FOREST",
            "before_img": img_urls["tree_before.jpg"],
            "after_img": img_urls["tree_after.jpg"],
            "res_notes": "Forest offense case booked under AP Forest Act. Contractor penalized and planted 20 neem saplings with protective cages.",
            "resolved_ago": 4, "created_ago": 8,
            "reporters_count": 1,
            "feedback": {"fixed": True, "rating": 5, "comments": "Grateful for the strict enforcement."}
        },
        {
            "title": "Dense Black Soot Billowing from Secondary Smelter Furnace",
            "description": "Continuous thick black smoke polluting the air for over 500 meters downwind towards residential school.",
            "category": "air_pollution",
            "severity": "critical",
            "status": "resolved",
            "lat": 13.6380, "lng": 79.5080,
            "address": "Tirupati-Renigunta Highway Industrial Area",
            "zone_code": "RIB", "auth_code": "APPCB",
            "before_img": img_urls["air_before.jpg"],
            "after_img": img_urls["air_after.jpg"],
            "res_notes": "Unit forced to shut down until wet scrubber and bag filters were upgraded. Real-time emission sensors verified.",
            "resolved_ago": 1, "created_ago": 3,
            "reporters_count": 3,
            "feedback": None  # Citizen feedback pending
        },

        # --- Reopened & Escalated Incidents (Citizen clicked 'Was this actually fixed? -> No') ---
        {
            "title": "Recurring Plastic Heap Burning Behind Auto Nagar Complex",
            "description": "Scrap dealers burning piles of PVC pipes, cables and plastic bags at twilight, releasing choking carcinogenic fumes.",
            "category": "air_pollution",
            "severity": "critical",
            "status": "in_progress",
            "is_escalated": True,
            "escalation_count": 2,
            "lat": 13.6310, "lng": 79.4240,
            "address": "Auto Nagar Sector 2, Central Tirupati",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["air_before.jpg"],
            "after_img": None,
            "res_notes": "Previous inspection put out the fire, but citizens reported the burning restarted next evening.",
            "resolved_ago": None, "created_ago": 7,
            "reporters_count": 4,
            "feedback": {"fixed": False, "rating": 1, "comments": "NOT FIXED! The scrap dealers burned plastic again yesterday evening. Need police night patrolling!"}
        },
        {
            "title": "Untreated Hospital Biomedical Waste Dumped Near Public Drain",
            "description": "Used syringes, blood sample vials, and contaminated gloves dumped openly in black bags near residential apartments.",
            "category": "illegal_dumping",
            "severity": "critical",
            "status": "in_progress",
            "is_escalated": True,
            "escalation_count": 1,
            "lat": 13.6335, "lng": 79.4175,
            "address": "Near Balaji Colony Health Subcenter",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["dumping_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 5,
            "reporters_count": 3,
            "feedback": {"fixed": False, "rating": 1, "comments": "Only partial bags were collected. Sharp glass vials are still scattered on the footpath."}
        },

        # --- Multi-Reporter Duplicate Demonstration Incidents (USP) ---
        {
            "title": "Major Illegal Dumping of Construction Debris on Railway Feeder Road",
            "description": "Tipper trucks have dumped several loads of concrete chunks, plaster debris and excavation dirt blocking one full lane.",
            "category": "illegal_dumping",
            "severity": "high",
            "status": "in_progress",
            "lat": 13.6260, "lng": 79.4160,
            "address": "Railway Feeder Road, Ward 8",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["dumping_before.jpg"],
            "after_img": None,
            "res_notes": "MCT JCB earthmover assigned for tomorrow morning clearance.",
            "resolved_ago": None, "created_ago": 3,
            "reporters_count": 5,  # 5 citizens submitted duplicate reports merged here!
            "feedback": None
        },
        {
            "title": "Foaming Chemical Discharge in Swarnamukhi Check Dam",
            "description": "White thick toxic lather floating on top of the river water near the check dam bridge. Pungent chemical odor spreading into nearby fields.",
            "category": "water_pollution",
            "severity": "critical",
            "status": "assigned",
            "lat": 13.5870, "lng": 79.3170,
            "address": "Swarnamukhi Check Dam, Chandragiri",
            "zone_code": "CHB", "auth_code": "APPCB",
            "before_img": img_urls["water_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 2,
            "reporters_count": 3,  # 3 citizens reported
            "feedback": None
        },

        # --- Other In Progress & Assigned Incidents across Tirupati ---
        {
            "title": "Illegal Tree Felling in Seshachalam Forest Fringe",
            "description": "Suspicious cutting of teak and rosewood trees observed during night hours near foothills trail.",
            "category": "deforestation",
            "severity": "critical",
            "status": "in_progress",
            "lat": 13.6550, "lng": 79.3870,
            "address": "Kapilatheertham Trail, Alipiri",
            "zone_code": "AFC", "auth_code": "FOREST",
            "before_img": img_urls["tree_before.jpg"],
            "after_img": None,
            "res_notes": "Armed forest protection team stationed for night ambush.",
            "resolved_ago": None, "created_ago": 2,
            "reporters_count": 2,
            "feedback": None
        },
        {
            "title": "Stone Crusher Unit Generating Uncontrolled Silica Dust Cloud",
            "description": "Operating without dust suppression water sprayers, enveloping nearby agricultural orchards in white powder.",
            "category": "air_pollution",
            "severity": "high",
            "status": "assigned",
            "lat": 13.6730, "lng": 79.4620,
            "address": "Karakambadi Quarry Road",
            "zone_code": "KGB", "auth_code": "APPCB",
            "before_img": img_urls["air_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "High Decibel Music from Marriage Hall Exceeding Midnight Hours",
            "description": "Amplified outdoor speakers playing at over 90 dB past 12:30 AM in a residential neighborhood.",
            "category": "noise",
            "severity": "medium",
            "status": "submitted",
            "lat": 13.6350, "lng": 79.4260,
            "address": "Bhavani Nagar 3rd Cross, Central Tirupati",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["noise_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 2,
            "feedback": None
        },
        {
            "title": "Discharge of Untreated Hotel Sewage into Open Storm Drain",
            "description": "Large restaurant pumping kitchen wash and grease trap effluent into the road culvert.",
            "category": "water_pollution",
            "severity": "medium",
            "status": "assigned",
            "lat": 13.6300, "lng": 79.4170,
            "address": "Near RTC Bus Stand, Tirupati Central",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["water_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 2,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Illegal Sand Excavation in Swarnamukhi River Bed",
            "description": "Tractors illegally digging and hauling river sand near the old bridge pillars, weakening structural banks.",
            "category": "other",
            "severity": "high",
            "status": "in_progress",
            "lat": 13.5820, "lng": 79.3110,
            "address": "Chandragiri Old Bridge Causeway",
            "zone_code": "CHB", "auth_code": "TUDA",
            "before_img": img_urls["default_dumping.jpg"],
            "after_img": None,
            "res_notes": "Revenue and police task force deployed.",
            "resolved_ago": None, "created_ago": 4,
            "reporters_count": 2,
            "feedback": None
        },
        {
            "title": "Dead Animal Carcass Abandoned Along Highway Shoulder",
            "description": "Decomposing cattle carcass emitting foul odor and causing safety hazard on highway shoulder.",
            "category": "illegal_dumping",
            "severity": "medium",
            "status": "submitted",
            "lat": 13.6440, "lng": 79.5160,
            "address": "Renigunta Bypass Highway KM 14",
            "zone_code": "RIB", "auth_code": "MCT",
            "before_img": img_urls["dumping_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Agricultural Crop Stubble Burning Covering Highway in Smoke",
            "description": "Farmer burning paddy field residue after harvest, reducing visibility on highway to under 20 meters.",
            "category": "air_pollution",
            "severity": "high",
            "status": "assigned",
            "lat": 13.5900, "lng": 79.3250,
            "address": "Chandragiri Rural Agricultural Belt",
            "zone_code": "CHB", "auth_code": "APPCB",
            "before_img": img_urls["air_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 2,
            "reporters_count": 2,
            "feedback": None
        },
        {
            "title": "Unauthorized Encroachment and Tree Removal at Cherlopalli Tank",
            "description": "Bulldozer leveling natural tank bund and uprooting trees for commercial plotting.",
            "category": "deforestation",
            "severity": "high",
            "status": "in_progress",
            "lat": 13.6680, "lng": 79.4580,
            "address": "Cherlopalli Reservoir Bund, Karakambadi",
            "zone_code": "KGB", "auth_code": "FOREST",
            "before_img": img_urls["tree_before.jpg"],
            "after_img": None,
            "res_notes": "Stop work order served on developers.",
            "resolved_ago": None, "created_ago": 3,
            "reporters_count": 2,
            "feedback": None
        },
        {
            "title": "Heavy Nighttime Fabricating Noise in Silent Residential Colony",
            "description": "Metal lathe and grinding workshop operating until 2 AM with open metal shutters.",
            "category": "noise",
            "severity": "low",
            "status": "submitted",
            "lat": 13.6340, "lng": 79.4215,
            "address": "Bhavani Nagar 5th Line",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["noise_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Commercial Chemical Tanker Washing in Community Lake",
            "description": "Tanker drivers rinsing residual chemical storage drums directly into the irrigation pond.",
            "category": "water_pollution",
            "severity": "critical",
            "status": "assigned",
            "lat": 13.6420, "lng": 79.5180,
            "address": "Settipalli Tank Outlet, Renigunta",
            "zone_code": "RIB", "auth_code": "APPCB",
            "before_img": img_urls["water_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 2,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Damaged Underground Sewer Line Leaking onto Pedestrian Pathway",
            "description": "Black raw sewage gushing from cracked inspection manhole, flooding footpaths and entrance to school.",
            "category": "water_pollution",
            "severity": "high",
            "status": "in_progress",
            "lat": 13.6275, "lng": 79.4185,
            "address": "Tilak Road Junction, Tirupati Central",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["water_before.jpg"],
            "after_img": None,
            "res_notes": "Drainage repair team mobilized with suction tanker.",
            "resolved_ago": None, "created_ago": 2,
            "reporters_count": 3,
            "feedback": None
        },
        {
            "title": "Plastic Waste Mountain Accumulated Behind Pilgrim Choultries",
            "description": "Styrofoam cups, water pouches and plastic packaging dumped in huge quantities by catering contractors.",
            "category": "illegal_dumping",
            "severity": "high",
            "status": "assigned",
            "lat": 13.6480, "lng": 79.3930,
            "address": "Near Srinivasam Pilgrim Complex, Alipiri Zone",
            "zone_code": "AFC", "auth_code": "MCT",
            "before_img": img_urls["dumping_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 2,
            "feedback": None
        },
        {
            "title": "Illegal Brick Kiln Emitting Acrid Smoke Over Highway",
            "description": "Old clamp-style brick kiln burning coal and spent oil without any scrubber or height clearance.",
            "category": "air_pollution",
            "severity": "high",
            "status": "submitted",
            "lat": 13.6650, "lng": 79.4650,
            "address": "Karakambadi Rural Sector",
            "zone_code": "KGB", "auth_code": "APPCB",
            "before_img": img_urls["air_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Timber Smuggling Camp Detected in Reserve Forest Valley",
            "description": "Clandestine tree felling tools, rations and chopped wood logs spotted in deep hill ravine.",
            "category": "deforestation",
            "severity": "critical",
            "status": "in_progress",
            "lat": 13.6580, "lng": 79.3850,
            "address": "Seshachalam Deep Ridge Section 4",
            "zone_code": "AFC", "auth_code": "FOREST",
            "before_img": img_urls["tree_before.jpg"],
            "after_img": None,
            "res_notes": "Anti-smuggling special task force cordon launched.",
            "resolved_ago": None, "created_ago": 3,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Battery Smelting Workshop Releasing Lead Fumes",
            "description": "Unregistered backyard lead-acid battery melting workshop operating without air filtration.",
            "category": "air_pollution",
            "severity": "critical",
            "status": "assigned",
            "lat": 13.6390, "lng": 79.5110,
            "address": "Settipalli Industrial Lane 4",
            "zone_code": "RIB", "auth_code": "APPCB",
            "before_img": img_urls["air_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 2,
            "reporters_count": 2,
            "feedback": None
        },
        {
            "title": "Illegal Commercial Billboard Erected in Public Green Belt",
            "description": "Huge 40-foot metal billboard structure bolted down damaging avenue trees and lawn in civic park.",
            "category": "other",
            "severity": "low",
            "status": "submitted",
            "lat": 13.6315, "lng": 79.4220,
            "address": "Park Road, Ward 14",
            "zone_code": "TCZ", "auth_code": "TUDA",
            "before_img": img_urls["default_dumping.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Pneumatic Rock Breaker Operating During Silent Night Hours",
            "description": "Commercial building basement excavation using heavy jackhammers after 11:30 PM.",
            "category": "noise",
            "severity": "medium",
            "status": "submitted",
            "lat": 13.6280, "lng": 79.4190,
            "address": "Subhash Nagar Main Road",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["noise_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Hazardous Electronic Waste Dumping Along Stream",
            "description": "Dozens of smashed CRT monitors, copper coils, and leaking battery casings left on stream slope.",
            "category": "illegal_dumping",
            "severity": "high",
            "status": "assigned",
            "lat": 13.6360, "lng": 79.5050,
            "address": "Renigunta Industrial Perimeter Canal",
            "zone_code": "RIB", "auth_code": "APPCB",
            "before_img": img_urls["dumping_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 2,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Illegal Pruning of Avenue Shady Trees for Private Showroom View",
            "description": "Branches of two healthy shade trees sawed off in broad daylight without municipal permission.",
            "category": "deforestation",
            "severity": "low",
            "status": "submitted",
            "lat": 13.6305, "lng": 79.4235,
            "address": "Air Bypass Road, Tirupati Central",
            "zone_code": "TCZ", "auth_code": "MCT",
            "before_img": img_urls["tree_before.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 1,
            "feedback": None
        },
        {
            "title": "Oil Sludge and Grease Discharged from Automobile Garages",
            "description": "Concentrated black automotive oil waste washed into roadside stormwater canal leading into Swarnamukhi.",
            "category": "water_pollution",
            "severity": "high",
            "status": "in_progress",
            "lat": 13.6425, "lng": 79.5130,
            "address": "Tirupati Autonagar Expansion, Renigunta",
            "zone_code": "RIB", "auth_code": "APPCB",
            "before_img": img_urls["water_before.jpg"],
            "after_img": None,
            "res_notes": "Notice issued to 4 garage owners to install oil-water separators.",
            "resolved_ago": None, "created_ago": 3,
            "reporters_count": 2,
            "feedback": None
        },
        {
            "title": "Community Park Encroachment and Dumping of Waste",
            "description": "Lawn boundary broken down with debris dumping and unauthorized vehicle parking.",
            "category": "other",
            "severity": "low",
            "status": "submitted",
            "lat": 13.6710, "lng": 79.4630,
            "address": "Mangalam Housing Colony Park, Karakambadi",
            "zone_code": "KGB", "auth_code": "TUDA",
            "before_img": img_urls["default_dumping.jpg"],
            "after_img": None,
            "res_notes": None,
            "resolved_ago": None, "created_ago": 1,
            "reporters_count": 1,
            "feedback": None
        }
    ]

    citizen_user = user_objs["citizen@envi.gov"]

    for idx, rep in enumerate(reports_data):
        incident_num = f"ENV-2026-{idx+1:04d}"
        existing = db.query(Incident).filter(Incident.incident_number == incident_num).first()
        if existing:
            continue

        created_days = rep.get("created_ago", 3)
        created_time = now - datetime.timedelta(days=created_days, hours=idx % 8, minutes=(idx * 7) % 60)

        resolved_time = None
        if rep.get("resolved_ago") is not None:
            resolved_time = now - datetime.timedelta(days=rep["resolved_ago"], hours=2)

        closed_time = resolved_time if rep["status"] == "closed" else None

        zone = zone_objs.get(rep["zone_code"])
        auth = auth_objs.get(rep["auth_code"])

        inc = Incident(
            incident_number=incident_num,
            title=rep["title"],
            description=rep["description"],
            category=rep["category"],
            severity=rep["severity"],
            status=rep["status"],
            reporters_count=rep.get("reporters_count", 1),
            latitude=rep["lat"],
            longitude=rep["lng"],
            address=rep["address"],
            zone_id=zone.id if zone else None,
            assigned_authority_id=auth.id if auth else None,
            primary_image_url=rep["before_img"],
            after_image_url=rep.get("after_img"),
            resolution_notes=rep.get("res_notes"),
            resolved_at=resolved_time,
            closed_at=closed_time,
            is_escalated=rep.get("is_escalated", False),
            escalation_count=rep.get("escalation_count", 0),
            ai_predicted_category=rep["category"],
            ai_predicted_severity=rep["severity"],
            ai_confidence=0.92,
            created_at=created_time,
            updated_at=now - datetime.timedelta(hours=idx)
        )
        db.add(inc)
        db.commit()
        db.refresh(inc)

        # Primary Evidence
        ev1 = ReportEvidence(
            incident_id=inc.id,
            user_id=citizen_user.id if idx % 2 == 0 else None,
            reporter_name=citizen_user.full_name if idx % 2 == 0 else f"Citizen Reporter #{idx+1}",
            reporter_contact=citizen_user.email if idx % 2 == 0 else "+91 98480 99881",
            image_url=rep["before_img"],
            latitude=rep["lat"],
            longitude=rep["lng"],
            has_exif_gps=True,
            exif_lat=rep["lat"],
            exif_lng=rep["lng"],
            notes="Captured and geo-verified via mobile camera sensor.",
            created_at=created_time
        )
        db.add(ev1)

        # Additional duplicate evidences if reporters_count > 1 (demonstrating USP!)
        for dup_i in range(1, rep.get("reporters_count", 1)):
            dup_lat = rep["lat"] + (0.00015 * dup_i * (-1 if dup_i % 2 == 0 else 1))
            dup_lng = rep["lng"] + (0.00012 * dup_i * (1 if dup_i % 2 == 0 else -1))
            ev_dup = ReportEvidence(
                incident_id=inc.id,
                user_id=None,
                reporter_name=f"Neighboring Citizen #{dup_i+1}",
                reporter_contact=f"citizen{dup_i+10}@gmail.com",
                image_url=rep["before_img"],
                latitude=dup_lat,
                longitude=dup_lng,
                has_exif_gps=True,
                exif_lat=dup_lat,
                exif_lng=dup_lng,
                notes=f"Auto-merged duplicate submission. Located within ~{35 * dup_i}m of initial ticket.",
                created_at=created_time + datetime.timedelta(hours=dup_i * 4)
            )
            db.add(ev_dup)

        # Status History
        hist1 = StatusHistory(
            incident_id=inc.id,
            old_status=None,
            new_status="submitted",
            changed_by_name="Citizen Reporter",
            notes="Initial incident submitted with photographic evidence.",
            created_at=created_time
        )
        db.add(hist1)

        if inc.status in ["assigned", "in_progress", "resolved", "closed"]:
            hist2 = StatusHistory(
                incident_id=inc.id,
                old_status="submitted",
                new_status="assigned",
                changed_by_name="Automated Routing Engine",
                notes=f"Routed to {auth.name} based on rule: category '{rep['category']}'.",
                created_at=created_time + datetime.timedelta(minutes=15)
            )
            db.add(hist2)

        if inc.status in ["in_progress", "resolved", "closed"]:
            hist3 = StatusHistory(
                incident_id=inc.id,
                old_status="assigned",
                new_status="in_progress",
                changed_by_name=f"{auth.code} Field Officer",
                notes="Officer assigned and field inspection initiated.",
                created_at=created_time + datetime.timedelta(hours=2)
            )
            db.add(hist3)

        if inc.status in ["resolved", "closed"]:
            hist4 = StatusHistory(
                incident_id=inc.id,
                old_status="in_progress",
                new_status="resolved",
                changed_by_name=f"{auth.code} Zonal Officer",
                notes=rep.get("res_notes") or "Violation remediated and after-photo uploaded.",
                created_at=resolved_time or (now - datetime.timedelta(hours=5))
            )
            db.add(hist4)

        if inc.status == "closed":
            hist5 = StatusHistory(
                incident_id=inc.id,
                old_status="resolved",
                new_status="closed",
                changed_by_name="Citizen Verifier (Rajesh Sharma)",
                notes="Citizen confirmed fix: 'Yes, actually fixed'. Closed with proof.",
                created_at=closed_time or (now - datetime.timedelta(hours=2))
            )
            db.add(hist5)

        # Feedback
        fb_data = rep.get("feedback")
        if fb_data:
            fb = Feedback(
                incident_id=inc.id,
                user_id=citizen_user.id,
                citizen_name=citizen_user.full_name,
                was_fixed=fb_data["fixed"],
                rating=fb_data["rating"],
                comments=fb_data["comments"],
                proof_image_url=rep.get("after_img"),
                created_at=resolved_time or (now - datetime.timedelta(hours=3))
            )
            db.add(fb)

            if not fb_data["fixed"]:
                # Log the escalation in history
                hist_esc = StatusHistory(
                    incident_id=inc.id,
                    old_status="resolved",
                    new_status="in_progress",
                    changed_by_name="Citizen Verification Failure",
                    notes=f"Citizen reported problem NOT FIXED! Reopened & escalated to CRITICAL priority (Level #{inc.escalation_count}).",
                    created_at=now - datetime.timedelta(hours=4)
                )
                db.add(hist_esc)

    print("Generating demo notifications...")
    # Add representative notifications for citizen and officers
    notifs_seed = [
        (citizen_user.id, "Resolution Confirmed", "Your complaint ENV-2026-0001 at Gandhi Road was officially closed with your 5-star rating.", "feedback", 1),
        (citizen_user.id, "Duplicate Violation Merged", "Your report for construction debris matched active ticket ENV-2026-0008. 4 other citizens are tracking this.", "duplicate_merged", 8),
        (user_objs["mct.officer@tirupati.gov"].id, "ESCALATION ALERT", "Citizen reported ENV-2026-0006 (Plastic Heap Burning) NOT FIXED! Escalated to CRITICAL priority.", "escalation", 6),
        (user_objs["mct.officer@tirupati.gov"].id, "New Assignment: ENV-2026-0008", "High priority illegal dumping on Railway Feeder Road assigned to MCT.", "new_assignment", 8),
        (user_objs["appcb.officer@appcb.gov"].id, "Critical River Pollution Reported", "Foaming chemical runoff detected at Swarnamukhi Check Dam (ENV-2026-0009).", "new_assignment", 9)
    ]

    for uid, title, msg, n_type, link_id in notifs_seed:
        db.add(Notification(
            user_id=uid,
            title=title,
            message=msg,
            type=n_type,
            link_id=link_id,
            is_read=False,
            created_at=now - datetime.timedelta(hours=2)
        ))

    db.commit()
    print("Database seeding completed successfully! 30 incidents, 5 zones, 4 authorities, and demo accounts ready.")
    db.close()


if __name__ == "__main__":
    seed_database()
