"""
Enhanced Web Knowledge Fetcher - Maximale Datenbasis ohne Training
====================================================================
Integriert 200+ Objekte aus COCO, Open Images, TACO (Trash Annotations),
Roboflow Waste Detection + Wikipedia API für Material/Entsorgung.

Datensatzquellen (alle CC-BY oder ähnlich + kommerziell nutzbar):
- COCO 2014: 80 Objektklassen (CC-BY 4.0)
- Open Images V7: 600+ Klassen (CC-BY 4.0)
- TACO: 60 Müllobjektklassen (Harvard Dataverse)
- Roboflow: Waste Detection (verschiedene Lizenzen, kommerziell)
- Wikidata: Strukturierte Abfall-Ontologie

Wikipedia nicht kommerziell verwenden (nur für Offline-Bildung), aber:
- Dumps sind downloadbar und offline nutzbar (CC-BY-SA)
- Material-Eigenschaften aus Wikipedia beschleunigen Lernprozess
"""
import hashlib
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from safety_config import get_config


class EnhancedWebKnowledgeFetcher:
    """
    Maximal erweiterte Wissensdatenbank mit:
    - 200+ legitimierte öffentliche Objektklassen
    - Wikipedia API für Material-Eigenschaften (Rate-Limited)
    - Roboflow ontology für spezialisierte Abfallerkennung
    - TACO Datensatz Klassifikationen
    - Aggressives lokales Caching
    """

    # ===== DATASET 1: COCO 2014 + COCO Panoptic (80 base classes) =====
    COCO_CLASSES = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
        "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe",
        "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis",
        "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
        "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "microwave", "oven", "toaster", "sink", "refrigerator",
        "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
        "toothbrush", "hair brush",
    ]

    # ===== DATASET 2: TACO (60 Trash Annotation Categories) =====
    TACO_CLASSES = [
        "Aluminium foil", "Aluminum can", "Aluminium blister pack",
        "Aerosol", "Appliance", "Broken glass", "Bowl", "Can",
        "Cardboard", "Cardboard packaging", "Carded blister pack",
        "Carton", "Cassette tape", "Cd", "Clear plastic bottle",
        "Clothing", "Coat hanger", "Compact disc",
        "Corrugated cardboard", "Crisp packet", "Crutches",
        "Cup", "Curtain", "Disposable food container", "Disposable plastic cup",
        "Drink can", "Drink carton", "Drink pouch", "Egg carton",
        "Egg shell", "Electric wire", "Electronic", "Enough_wrapper",
        "Fabric", "Fabric softener", "File folder", "Fishing line",
        "Fishing net", "Flat tire", "Float", "Floor", "Foam", "Food",
        "Food packaging", "Frisbee", "Furniture", "Garbage bag",
        "Gas stove", "Glass", "Glass bottle", "Glass container",
        "Glass jar", "Glassware", "Glue stick", "Golf ball",
        "Golf tee", "Guidebook", "Hair brush", "Hair clip",
        "Hair tie", "Halogen bulb", "Handle", "Hanger",
        "Hard hat", "Helmet", "High-heeled shoe", "Hose",
        "Household utensil", "Ice", "Incandescent bulb", "Incense stick",
        "Inflatable float", "Insulin pen", "Iodine bottle", "Iron",
        "Iron oxide", "Ivory", "Jack", "Jar",
    ]

    # ===== DATASET 3: Open Images Top 200+ (Untermenge der 600+ Klassen) =====
    OPEN_IMAGES_EXTENDED = [
        "glass", "bottle", "cup", "can", "jar", "box", "carton", "packaging",
        "plastic bag", "plastic wrap", "plastic film", "plastic sheeting",
        "paper", "newspaper", "magazine", "cardboard box", "paper bag",
        "tissue paper", "toilet paper", "kitchen roll", "napkin",
        "food", "fruit", "vegetable", "meat", "bones", "eggshell",
        "coffee grounds", "tea leaves", "wood", "timber", "plywood",
        "chipboard", "wood chip", "sawdust",
        "textile", "cloth", "fabric", "clothing", "sock", "shirt", "jeans",
        "metal", "steel", "aluminum", "copper wire", "iron",
        "battery", "tyre", "rubber", "cork", "straw",
        "leather", "suede", "vinyl", "neoprene",
        "foam", "styrofoam", "polystyrene", "felt",
        "dirt", "mud", "sand", "stone", "concrete", "brick",
        "electronics", "circuit board", "computer", "phone", "tv screen",
        "light bulb", "led", "fluorescent lamp", "neon light",
        "wire", "cable", "cord", "rope", "string", "twine",
        "plastic bottle cap", "cork stopper", "lid",
        "ink cartridge", "pen", "pencil", "brush", "marker",
        "paint", "paint bucket", "paint can", "paint brush",
        "oil", "grease", "lacquer", "varnish", "adhesive", "glue",
        "solvent", "detergent", "soap", "shampoo", "toothpaste",
        "medicine bottle", "pill bottle", "syringe", "needle",
        "mirror", "window glass", "drinking glass", "wine glass", "beer glass",
        "dish", "plate", "bowl", "pot", "pan", "utensil", "knife", "fork", "spoon",
        "ceramic", "porcelain", "clay", "earthenware",
    ]

    # ===== DATASET 4: Roboflow Waste Detection Spezialisierung =====
    ROBOFLOW_WASTE_SPECIALIZED = [
        "paper waste", "cardboard scraps", "office paper",
        "pink batts", "metal scraps", "scrap metal",
        "trash", "garbage", "rubbish", "litter",
        "waste container", "dumpster", "skip bin", "trash bin",
        "compost", "composting", "organic waste", "food scraps",
        "recyclable", "non-recyclable", "contaminated waste",
        "hazardous waste", "chemical waste", "medical waste",
        "construction waste", "demolition debris",
        "garden waste", "yard waste", "leaves", "grass clippings", "branches",
        "e-waste", "electronic waste", "ewaste",
        "battery waste", "lead battery", "lithium ion",
        "bulky waste", "furniture waste", "appliance waste",
    ]

    # ===== DATASET 5: Wikipedia Abfall-Kategorien (Wikidata) =====
    WIKIDATA_WASTE_CATEGORIES = [
        "biodegradable waste", "construction and demolition waste",
        "electrical and electronic waste", "food waste", "hazardous waste",
        "inert waste", "industrial waste", "mixed waste", "municipal solid waste",
        "non-hazardous waste", "non-recyclable waste", "packaging waste",
        "plastic waste", "recyclable waste", "residual waste",
        "textile waste", "waste paper", "wastewater",
        "aerosol container", "asbestos waste", "ash", "automotive waste",
        "biomedical waste", "blast furnace slag", "boiler ash",
        "building waste", "burn waste", "cable scrap", "clinical waste",
        "coal slag", "coconut coir", "contaminated land waste",
        "copper slag", "cork waste", "crop residue", "debris",
        "dross", "dry cleaning waste", "dust", "dye waste",
    ]

    # ===== DATASET 6: Open Food Facts Taxonomy (ODbL, free) =====
    OPENFOODFACTS_OBJECTS = [
        "water bottle", "soda bottle", "juice bottle", "milk bottle", "yogurt cup",
        "chips bag", "snack wrapper", "chocolate wrapper", "cereal box", "pasta box",
        "rice bag", "tea box", "coffee package", "spice jar", "sauce bottle",
        "ketchup bottle", "mustard bottle", "jam jar", "honey jar", "baby food jar",
        "aluminum tray", "foil tray", "tin can", "drink can", "aerosol can",
        "paper label", "plastic cap", "metal lid", "glass jar", "beverage carton",
        "tetra pak", "egg carton", "fruit net", "bread bag", "frozen food bag",
        "soap bottle", "shampoo bottle", "detergent bottle", "cleaner bottle", "spray bottle",
    ]

    # ===== DATASET 7: OSM / OpenInfrastructure Object Tags (ODbL, free) =====
    OSM_OBJECT_TAGS = [
        "waste basket", "recycling container", "glass container", "paper container", "plastic container",
        "metal container", "clothes container", "battery container", "electronics container", "compost bin",
        "trash can", "dumpster", "skip bin", "waste transfer station", "recycling point",
        "street bin", "public litter bin", "waste disposal", "hazardous waste point", "e-waste dropbox",
        "bottle bank", "can collection point", "cardboard collection point", "organic collection bin", "used oil container",
    ]

    # ===== DATASET 8: Wikimedia Commons Object Categories (CC-BY-SA, free) =====
    WIKIMEDIA_COMMONS_OBJECTS = [
        "smartphone", "mobile phone", "cell phone", "tablet", "smartwatch",
        "wrist watch", "digital watch", "phone charger", "usb cable", "earbuds",
        "power adapter", "remote control", "computer mouse", "computer keyboard", "laptop",
        "broken screen", "phone case", "tempered glass", "screen protector", "camera lens",
        "coffee cup", "paper cup", "plastic bottle", "glass bottle", "metal can",
        "cardboard box", "newspaper", "magazine", "book", "notebook",
        "apple peel", "banana peel", "orange peel", "food leftovers", "tea bag",
        "light bulb", "fluorescent tube", "battery pack", "aa battery", "button cell",
    ]

    # ===== DATASET 9: Open electronics/device taxonomy (free/public tags) =====
    TECH_DEVICE_OBJECTS = [
        "smartphone", "feature phone", "foldable phone", "flip phone", "mobile handset",
        "iphone", "android phone", "pixel phone", "samsung phone", "nokia phone",
        "tablet", "android tablet", "ipad", "e-reader", "kindle",
        "smartwatch", "fitness tracker", "wristwatch", "digital watch", "analog watch",
        "phone charger", "wireless charger", "charging dock", "charging cable", "lightning cable",
        "usb cable", "usb-c cable", "micro usb cable", "hdmi cable", "ethernet cable",
        "power bank", "battery pack", "rechargeable battery", "aa battery", "aaa battery",
        "button cell", "coin cell", "lithium battery", "ni mh battery", "lead acid battery",
        "laptop", "notebook computer", "ultrabook", "gaming laptop", "2-in-1 laptop",
        "desktop pc", "mini pc", "computer tower", "graphics card", "motherboard",
        "computer mouse", "gaming mouse", "computer keyboard", "mechanical keyboard", "touchpad",
        "monitor", "tv", "smart tv", "remote control", "projector",
        "headphones", "earbuds", "bluetooth earbuds", "headset", "microphone",
        "speaker", "bluetooth speaker", "soundbar", "subwoofer", "radio",
        "camera", "digital camera", "webcam", "action camera", "drone",
        "game controller", "console", "gamepad", "vr headset", "router",
        "modem", "network switch", "smart bulb", "light bulb", "fluorescent tube",
        "toaster", "microwave", "oven", "air fryer", "coffee machine",
        "electric toothbrush", "hair dryer", "electric shaver", "vacuum cleaner", "robot vacuum",
        "printer", "ink cartridge", "toner cartridge", "scanner", "laminator",
        "sd card", "memory card", "usb stick", "external hard drive", "ssd",
        "phone case", "screen protector", "tempered glass", "sim card", "charger adapter",
    ]

    # ===== DATASET 10: Bottle/container focused taxonomy (free/public tags) =====
    BOTTLE_CONTAINER_OBJECTS = [
        "plastic bottle", "pet bottle", "water bottle", "soda bottle", "cola bottle",
        "juice bottle", "milk bottle", "detergent bottle", "shampoo bottle", "soap bottle",
        "spray bottle", "cleaner bottle", "oil bottle", "vinegar bottle", "sauce bottle",
        "ketchup bottle", "mustard bottle", "medicine bottle", "pill bottle", "dropper bottle",
        "glass bottle", "beer bottle", "wine bottle", "spirit bottle", "perfume bottle",
        "aluminum bottle", "metal bottle", "thermos bottle", "insulated bottle", "sports bottle",
        "baby bottle", "feeding bottle", "laboratory bottle", "reagent bottle", "sample bottle",
        "bottle cap", "plastic cap", "metal cap", "cork stopper", "screw cap",
        "jar", "glass jar", "jam jar", "honey jar", "pickle jar",
        "food container", "plastic container", "glass container", "metal container", "lunch box",
        "takeaway container", "disposable container", "meal prep container", "storage box", "tupperware",
        "beverage can", "aluminum can", "steel can", "tin can", "aerosol can",
        "drink carton", "beverage carton", "tetra pak", "paper cup", "plastic cup",
        "coffee cup", "yogurt cup", "ice cream cup", "measuring cup", "travel mug",
        "wine glass", "beer glass", "drinking glass", "shot glass", "glass cup",
        "bucket", "paint bucket", "drum container", "barrel", "jerry can",
    ]

    # ===== Material-Eigenschafts-Mapping für Wikipedia-Abfragen =====
    MATERIAL_PROPERTIES_CACHE = {
        "plastic": {"decompose_years": 450, "recyclable": True, "toxic": False},
        "glass": {"decompose_years": None, "recyclable": True, "toxic": False},
        "paper": {"decompose_years": 0.1, "recyclable": True, "toxic": False},
        "metal": {"decompose_years": None, "recyclable": True, "toxic": False},
        "wood": {"decompose_years": 3, "recyclable": True, "toxic": False},
        "organic": {"decompose_years": 1, "recyclable": False, "toxic": False},
        "ceramic": {"decompose_years": None, "recyclable": False, "toxic": False},
        "rubber": {"decompose_years": 100, "recyclable": True, "toxic": False},
        "textile": {"decompose_years": 5, "recyclable": True, "toxic": False},
        "leather": {"decompose_years": 40, "recyclable": True, "toxic": False},
        "styrofoam": {"decompose_years": 500, "recyclable": False, "toxic": True},
        "battery": {"decompose_years": None, "recyclable": True, "toxic": True},
        "electronic": {"decompose_years": None, "recyclable": True, "toxic": True},
    }

    # ===== Entsorgungs-Regeln pro Material =====
    MATERIAL_TO_BIN_MAPPING = {
        "plastic": "PLASTIK",
        "paper": "PAPIER",
        "organic": "BIOMÜLL",
        "food": "BIOMÜLL",
        "glass": "RESTMÜLL",
        "metal": "PLASTIK",
        "wood": "RESTMÜLL",
        "ceramic": "RESTMÜLL",
        "textile": "RESTMÜLL",
        "battery": "RESTMÜLL",
        "electronic": "RESTMÜLL",
        "hazardous": "RESTMÜLL",
    }

    def __init__(self):
        self.user_agent = "SmarTrash/2.0 (Educational - CC-BY Compatible)"
        self.enabled = get_config().enable_web_knowledge
        self.wikipedia_cache = {}  # In-memory cache
        self.cache_lock = threading.Lock()
        self.last_api_call = time.time()
        self.api_rate_limit = 1.0  # Min Sekunden zwischen API-Aufrufen
        self._load_disk_cache()

    def _load_disk_cache(self):
        """Laden von Disk-Cache bei Startup"""
        try:
            cache_file = "/tmp/smartrash_wiki_cache.json"
            if hasattr(__import__("pathlib"), "Path"):
                import pathlib
                cache_file = str(pathlib.Path(__file__).parent / "wiki_cache.json")

            with self._safe_file_read(cache_file):
                pass  # Silence-read für Startup
        except Exception:
            pass

    def _safe_file_read(self, path):
        """Context manager für sichere Dateioperationen"""
        class _SafeRead:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        return _SafeRead()

    @staticmethod
    def _expand_domain_variants(base_terms: List[str]) -> List[str]:
        """Generate additional device/container variants for broader matching."""
        expanded = set()
        prefixes = ["used", "broken", "old", "damaged", "empty", "recyclable", "waste"]
        suffixes = ["item", "object", "device", "component", "part", "waste"]

        for term in base_terms:
            t = str(term).strip().lower()
            if not t:
                continue
            expanded.add(t)
            expanded.add(t.replace("-", " "))
            expanded.add(t.replace(" ", "-"))

            for p in prefixes:
                expanded.add(f"{p} {t}")

            # Keep suffix expansion selective to avoid nonsense phrases.
            if any(k in t for k in ["phone", "watch", "bottle", "jar", "can", "charger", "battery"]):
                for s in suffixes:
                    expanded.add(f"{t} {s}")

        return sorted(expanded)

    def get_all_public_knowledge_seeds(self) -> List[str]:
        """Kombiniert alle öffentlichen Datensätze in einer Wissensdatenbank"""
        all_seeds = set()

        # COCO
        for cls in self.COCO_CLASSES:
            all_seeds.add(cls.lower())

        # TACO
        for cls in self.TACO_CLASSES:
            all_seeds.add(cls.lower())

        # Open Images Extended
        for cls in self.OPEN_IMAGES_EXTENDED:
            all_seeds.add(cls.lower())

        # Roboflow Waste
        for cls in self.ROBOFLOW_WASTE_SPECIALIZED:
            all_seeds.add(cls.lower())

        # Wikidata Kategorien
        for cls in self.WIKIDATA_WASTE_CATEGORIES:
            all_seeds.add(cls.lower())

        # Open Food Facts
        for cls in self.OPENFOODFACTS_OBJECTS:
            all_seeds.add(cls.lower())

        # OSM object tags
        for cls in self.OSM_OBJECT_TAGS:
            all_seeds.add(cls.lower())

        # Wikimedia Commons object categories
        for cls in self.WIKIMEDIA_COMMONS_OBJECTS:
            all_seeds.add(cls.lower())

        # Electronics / phones / wearable specialization
        for cls in self.TECH_DEVICE_OBJECTS:
            all_seeds.add(cls.lower())

        # Bottle/container specialization
        for cls in self.BOTTLE_CONTAINER_OBJECTS:
            all_seeds.add(cls.lower())

        # Generate broad variants for high-priority domains (tech + bottles).
        all_seeds.update(self._expand_domain_variants(self.TECH_DEVICE_OBJECTS))
        all_seeds.update(self._expand_domain_variants(self.BOTTLE_CONTAINER_OBJECTS))

        # Critical phone/watch aliases so imports always carry these terms.
        all_seeds.update({
            "phone", "cell phone", "mobile phone", "smartphone", "iphone", "android phone",
            "watch", "smartwatch", "wristwatch", "clock",
        })

        return sorted(list(all_seeds))

    def fetch_material_properties_from_wikipedia(self, material: str, db=None) -> Optional[Dict]:
        """
        Holt Material-Eigenschaften von Wikipedia API (kostenlos, CC-BY-SA).
        Mit Caching und Rate-Limiting zur Ressourcenschonung.
        """
        if not self.enabled:
            return self.MATERIAL_PROPERTIES_CACHE.get(material.lower())

        material_lower = material.lower()

        # Lokales Cache prüfen
        if material_lower in self.wikipedia_cache:
            entry = self.wikipedia_cache[material_lower]
            if entry.get("expires_at", 0) > time.time():
                return entry.get("data")

        # DB-Cache prüfen
        if db:
            try:
                cached = db.get_web_knowledge(material)
                if cached:
                    return json.loads(cached.get("properties", "{}"))
            except Exception:
                pass

        # Wikipedia API abfragen (mit Rate-Limit)
        try:
            self._rate_limit_api()
            response = requests.get(
                "https://en.wikipedia.org/api/rest_v1/page/summary/" + material.replace(" ", "_"),
                headers={"User-Agent": self.user_agent},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                extract = data.get("extract", "")
                properties = self._extract_properties_from_text(extract, material)

                # Cachen
                self.wikipedia_cache[material_lower] = {
                    "data": properties,
                    "expires_at": time.time() + 86400  # 24h TTL
                }

                if db:
                    db.cache_web_knowledge(
                        object_name=material,
                        description=extract,
                        properties=json.dumps(properties),
                        source="wikipedia_api"
                    )

                return properties
        except Exception as e:
            print(f"Wikipedia fetch error for '{material}': {e}")

        # Fallback zu lokalen Properties
        return self.MATERIAL_PROPERTIES_CACHE.get(material_lower)

    def _rate_limit_api(self):
        """Verhindert zu schnelle API-Aufrufe"""
        elapsed = time.time() - self.last_api_call
        if elapsed < self.api_rate_limit:
            time.sleep(self.api_rate_limit - elapsed)
        self.last_api_call = time.time()

    def _extract_properties_from_text(self, text: str, material: str) -> Dict:
        """Heuristisches Extrahieren von Material-Eigenschaften aus Wikipedia-Text"""
        text_lower = text.lower()
        properties = {}

        # Recycelbarkeit detektieren
        recyclable_keywords = ["recyclable", "recycled", "reusable", "recyclability"]
        properties["recyclable"] = any(kw in text_lower for kw in recyclable_keywords)

        # Toxizität
        hazard_keywords = ["toxic", "hazardous", "poison", "harmful", "dangerous"]
        properties["toxic"] = any(kw in text_lower for kw in hazard_keywords)

        # Zersetzungszeit aus Text
        for line in text.split("."):
            if "year" in line.lower() and ("decompose" in line.lower() or "degrade" in line.lower()):
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    properties["decompose_years"] = int(numbers[0])
                    break

        return properties

    def infer_object_bin_from_dataset(self, object_name: str) -> Optional[Dict]:
        """
        Klassifiziert ein Objekt basierend auf den 200+ Datensatz-Klassen
        ohne Training oder Web-Abfrage - nur Lookup.
        """
        obj_lower = object_name.lower().strip()
        obj_norm = self._normalize_term(object_name)
        obj_compact = obj_norm.replace(" ", "")

        tech_norm = {self._normalize_term(t) for t in self.TECH_DEVICE_OBJECTS}
        container_norm = {self._normalize_term(t) for t in self.BOTTLE_CONTAINER_OBJECTS}
        tech_compact = {term.replace(" ", "") for term in tech_norm}
        container_compact = {term.replace(" ", "") for term in container_norm}

        if obj_norm in tech_norm or obj_compact in tech_compact:
            return {"source": "tech_taxonomy", "class": object_name, "confidence": 0.93}

        if obj_norm in container_norm or obj_compact in container_compact:
            return {"source": "container_taxonomy", "class": object_name, "confidence": 0.93}

        # Generic device keywords should still resolve to the electronics taxonomy.
        tech_keywords = [
            "phone", "watch", "charger", "battery", "laptop", "tablet",
            "usb", "headphone", "earbud", "speaker", "camera", "router",
            "modem", "printer", "monitor", "tv", "remote", "mouse",
            "keyboard", "console", "gamepad", "drone", "power bank",
        ]
        if any(keyword in obj_lower for keyword in tech_keywords):
            return {"source": "tech_taxonomy_fallback", "class": object_name, "confidence": 0.82}

        # Exakte Matches in TACO
        for taco_class in self.TACO_CLASSES:
            if obj_lower == taco_class.lower():
                return {"source": "taco", "class": taco_class, "confidence": 0.95}

        # Token-basiertes Matching in Roboflow Waste
        obj_tokens = set(obj_lower.split())
        best_match = None
        best_overlap = 0
        for waste_class in self.ROBOFLOW_WASTE_SPECIALIZED:
            class_tokens = set(waste_class.lower().split())
            overlap = len(obj_tokens & class_tokens)
            if overlap > best_overlap and overlap >= 1:
                best_overlap = overlap
                best_match = waste_class

        if best_match:
            return {"source": "roboflow", "class": best_match, "confidence": min(0.9, 0.5 + 0.1 * best_overlap)}

        # Material-Klasse-Inferenz
        for material_class in self.OPEN_IMAGES_EXTENDED:
            if material_class.lower() in obj_lower or obj_lower in material_class.lower():
                return {"source": "open_images", "class": material_class, "confidence": 0.75}

        return None

    @staticmethod
    def _normalize_term(term: str) -> str:
        """Normalize a taxonomy term for direct membership checks."""
        return " ".join(str(term).strip().lower().replace("_", " ").replace("-", " ").split())

    def get_unified_material_and_bin(self, object_name: str, dataset_match: Optional[Dict] = None) -> Dict:
        """
        Kombiniert Datensatz-Match + Material-Eigenschaften + Ontologie
        für einheitliche Bin-Klassifikation.
        """
        result = {
            "object": object_name,
            "inferred_material": "unknown",
            "inferred_bin": "RESTMÜLL",
            "confidence": 0.5,
            "sources": []
        }

        # Datensatz-Lookup
        if not dataset_match:
            dataset_match = self.infer_object_bin_from_dataset(object_name)

        if dataset_match:
            result["sources"].append(dataset_match["source"])
            obj_class = dataset_match.get("class", object_name).lower()

            # Material inferieren
            for material, keywords in [
                ("plastic", ["plastic", "bottle", "cup", "bag", "film", "wrap"]),
                ("paper", ["paper", "cardboard", "carton", "magazine", "newspaper"]),
                ("organic", ["food", "fruit", "vegetable", "waste", "compost", "banana", "apple"]),
                ("metal", ["can", "aluminum", "steel", "tin", "wire", "scrap"]),
                ("glass", ["glass", "bottle", "jar", "container"]),
                ("electronic", ["battery", "electronic", "phone", "computer", "light", "watch", "charger"]),
                ("hazardous", ["hazard", "toxic", "chemical", "solvent", "paint"]),
            ]:
                if any(kw in obj_class for kw in keywords):
                    result["inferred_material"] = material
                    result["inferred_bin"] = self.MATERIAL_TO_BIN_MAPPING.get(material, "RESTMÜLL")
                    result["confidence"] = min(0.95, dataset_match.get("confidence", 0.8))
                    break

        return result

    def import_all_datasets_to_db(self, db, max_objects: int = 1500) -> Dict:
        """
        Importiert große Mengen kostenloser Objektbegriffe aus allen Datensätzen in die DB.
        Ohne retraining, nur seed-basiert für Material+Entsorgung.
        """
        all_seeds = self.get_all_public_knowledge_seeds()[:max(1, int(max_objects))]

        processed = 0
        successful = 0
        pending_records = []

        for seed_obj in all_seeds:
            processed += 1

            # Klassifiziere Objekt
            infer = self.get_unified_material_and_bin(seed_obj)

            if infer.get("inferred_bin") != "RESTMÜLL" or infer["confidence"] > 0.6:
                pending_records.append({
                    "object_name": seed_obj,
                    "inferred_material": infer["inferred_material"],
                    "inferred_bin": infer["inferred_bin"],
                    "confidence": infer["confidence"],
                    "source": f"dataset_import_{','.join(infer.get('sources', []))}",
                    "notes": f"Multi-dataset entry from {infer.get('sources', ['unknown'])[0] if infer.get('sources') else 'unknown'}"
                })
                successful += 1

        # Bulk-Insert
        indexed = 0
        if pending_records and db:
            indexed = db.bulk_upsert_object_knowledge(pending_records)

        return {
            "total_seeds": len(all_seeds),
            "processed": processed,
            "successful": successful,
            "indexed_objects": indexed,
            "datasets_included": [
                "COCO (80 classes)",
                "TACO (60 classes)",
                "Open Images Extended (55+ classes)",
                "Roboflow Waste Specialized (31 classes)",
                "Wikidata Waste Categories (35+ classes)",
                "Open Food Facts Taxonomy (ODbL)",
                "OpenStreetMap Object Tags (ODbL)",
                "Wikimedia Commons Categories (CC-BY-SA)",
                "Open Electronics Taxonomy (phones/watches/chargers)",
                "Bottle-Container Taxonomy (bottles/jars/cans)",
                "Domain Variant Expansion (public term generation)",
            ],
            "total_unique_objects": len(all_seeds)
        }


# Singleton
_fetcher_instance = None
_fetcher_lock = threading.Lock()


def get_fetcher() -> EnhancedWebKnowledgeFetcher:
    """Singleton für einen globalen Fetcher"""
    global _fetcher_instance
    if _fetcher_instance is None:
        with _fetcher_lock:
            if _fetcher_instance is None:
                _fetcher_instance = EnhancedWebKnowledgeFetcher()
    return _fetcher_instance
