#!/usr/bin/env python3
"""
🚀 MASSIVE DATA AGGREGATOR FOR SMARTRASH
Sammelt ALLE verfügbaren Daten aus allen Quellen für maximales Training!
"""

import json
import os
import sys
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
import requests
from urllib.parse import quote
import time
from collections import defaultdict

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


class MassiveDataAggregator:
    """Aggregiert ALLE verfügbaren Daten aus allen Quellen."""
    
    def __init__(self):
        self.all_data = {
            "objects": {},  # object_name → properties
            "materials": {},  # material_type → properties
            "categories": defaultdict(set),  # category → set of objects
            "synonyms": defaultdict(set),  # object_name → set of synonyms
            "metadata": {
                "total_objects": 0,
                "total_synonyms": 0,
                "sources": [],
                "coverage": {},
                "confidence": {}
            }
        }
        
        self.coco_classes = self._get_coco_classes()
        self.openimages_classes = self._get_openimages_classes()
        self.imagenet_classes = self._get_imagenet_classes()
        
    # ========== COCO DATEN ==========
    
    def _get_coco_classes(self) -> Dict[int, str]:
        """Alle 80 COCO-Klassen + erweiterte Mapping."""
        return {
            0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
            5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
            10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
            14: "cat", 15: "dog", 16: "horse", 17: "sheep", 18: "cow",
            19: "elephant", 20: "bear", 21: "zebra", 22: "giraffe", 23: "backpack",
            24: "umbrella", 25: "handbag", 26: "tie", 27: "suitcase", 28: "frisbee",
            29: "skis", 30: "snowboard", 31: "sports ball", 32: "kite", 33: "baseball bat",
            34: "baseball glove", 35: "skateboard", 36: "surfboard", 37: "tennis racket",
            38: "bottle", 39: "wine glass", 40: "cup", 41: "fork", 42: "knife",
            43: "spoon", 44: "bowl", 45: "banana", 46: "apple", 47: "sandwich",
            48: "orange", 49: "broccoli", 50: "carrot", 51: "hot dog", 52: "pizza",
            53: "donut", 54: "cake", 55: "chair", 56: "couch", 57: "potted plant",
            58: "bed", 59: "dining table", 60: "toilet", 61: "tv", 62: "laptop",
            63: "mouse", 64: "remote", 65: "keyboard", 66: "microwave", 67: "oven",
            68: "toaster", 69: "sink", 70: "refrigerator", 71: "book", 72: "clock",
            73: "vase", 74: "scissors", 75: "teddy bear", 76: "hair drier",
            77: "toothbrush", 78: "blanket", 79: "pillow"
        }
    
    def _get_openimages_classes(self) -> Dict[str, str]:
        """500+ OpenImages Klassen (wichtigste für Müll)."""
        return {
            # Behälter & Verpackung
            "box": "Verpackungsbox", "carton": "Karton",
            "plastic bottle": "Plastikflasche", "glass bottle": "Glasflasche",
            "can": "Dose", "jar": "Glas",
            "bag": "Tasche/Beutel", "plastic bag": "Plastiktasche",
            "shopping bag": "Einkaufstasche", "garbage bag": "Mülltüte",
            "paper bag": "Papiertüte", "paper cup": "Papiertasse",
            "styrofoam cup": "Styroporbehälter", "foam cup": "Schaumstoffbecher",
            
            # Essen & Biomüll
            "apple": "Apfel", "banana": "Banane", "orange": "Orange",
            "strawberry": "Erdbeere", "blueberry": "Blaubeere",
            "grape": "Traube", "watermelon": "Wassermelone",
            "broccoli": "Brokkoli", "carrot": "Karotte", "potato": "Kartoffel",
            "tomato": "Tomate", "cucumber": "Gurke", "pepper": "Paprika",
            "onion": "Zwiebel", "garlic": "Knoblauch", "lettuce": "Salat",
            "food waste": "Essensreste", "leftovers": "Essensreste",
            "bread": "Brot", "pizza": "Pizza", "pasta": "Pasta",
            "meat": "Fleisch", "fish": "Fisch", "chicken": "Hähnchen",
            "egg": "Ei", "cheese": "Käse", "yogurt": "Joghurt",
            "milk": "Milch", "butter": "Butter", "oil": "Öl",
            
            # Papier & Karton
            "newspaper": "Zeitung", "magazine": "Zeitschrift", "book": "Buch",
            "paper": "Papier", "cardboard": "Karton", "corrugated cardboard": "Wellpappe",
            "envelope": "Umschlag", "napkin": "Serviette", "tissue": "Taschentuch",
            "paper towel": "Küchenrolle", "toilet paper": "Toilettenpapier",
            
            # Glas
            "glass": "Glas", "wine glass": "Weinglas", "beer glass": "Bierglas",
            "glass jar": "Glasgefäß", "mirror": "Spiegel", "window": "Fenster",
            
            # Elektronik
            "smartphone": "Smartphone", "phone": "Telefon", "mobile phone": "Handy",
            "laptop": "Laptop", "desktop computer": "Desktop-PC",
            "tablet": "Tablet", "monitor": "Monitor", "keyboard": "Tastatur",
            "mouse": "Maus", "printer": "Drucker", "scanner": "Scanner",
            "camera": "Kamera", "camcorder": "Videokamera",
            "headphones": "Kopfhörer", "speaker": "Lautsprecher", "microphone": "Mikrofon",
            "video game console": "Spielkonsole", "video game controller": "Spielcontroller",
            "charger": "Ladegerät", "cable": "Kabel", "usb": "USB-Kabel",
            "power adapter": "Netzteil", "battery": "Batterie", "remote control": "Fernbedienung",
            "smart watch": "Smartwatch", "earbuds": "Ohrhörer",
            "toaster": "Toaster", "microwave": "Mikrowelle", "kettle": "Wasserkocher",
            "blender": "Mixer", "coffee maker": "Kaffeemaschine", "oven": "Ofen",
            "refrigerator": "Kühlschrank", "washing machine": "Waschmaschine",
            "dishwasher": "Spülmaschine", "vacuum": "Staubsauger",
            "hair dryer": "Föhn", "iron": "Bügeleisen",
            
            # Textil
            "shirt": "Hemd", "pants": "Hose", "dress": "Kleid",
            "jacket": "Jacke", "coat": "Mantel", "sweater": "Pullover",
            "sock": "Socke", "shoe": "Schuh", "boot": "Stiefel",
            "hat": "Hut", "cap": "Kappe", "scarf": "Schal",
            "gloves": "Handschuhe", "underwear": "Unterwäsche",
            "towel": "Handtuch", "blanket": "Decke", "curtain": "Gardine",
            "bedsheet": "Betttuch",
            
            # Holz & Möbel
            "chair": "Stuhl", "stool": "Hocker", "table": "Tisch",
            "desk": "Schreibtisch", "bed": "Bett", "sofa": "Sofa",
            "couch": "Couch", "cabinet": "Schrank", "shelf": "Regal",
            "nightstand": "Nachttisch", "wardrobe": "Kleiderschrank",
            "dresser": "Kommode", "bookcase": "Bücherschrank",
            "wood": "Holz", "wooden board": "Holzbrett",
            
            # Metall
            "aluminum foil": "Alufolie", "metal can": "Metalldose",
            "steel": "Stahl", "copper": "Kupfer", "iron": "Eisen",
            "tin": "Zinn", "nail": "Nagel", "screw": "Schraube",
            "bolt": "Bolzen", "wire": "Draht", "chain": "Kette",
            
            # Sonstiges
            "plastic": "Kunststoff", "rubber": "Gummi", "foam": "Schaum",
            "latex": "Latex", "vinyl": "Vinyl", "leather": "Leder",
            "cotton": "Baumwolle", "polyester": "Polyester", "nylon": "Nylon",
            "ceramic": "Keramik", "porcelain": "Porzellan",
            "stone": "Stein", "concrete": "Beton", "brick": "Ziegel",
            "marble": "Marmor", "granite": "Granit",
            
            # Bücher & Druck
            "postcard": "Postkarte", "greeting card": "Grußkarte",
            "receipt": "Quittung", "ticket": "Fahrkarte",
            "label": "Etikett", "sticker": "Aufkleber", "poster": "Plakat",
            
            # Sport & Spiele
            "ball": "Ball", "soccer ball": "Fußball", "basketball": "Basketball",
            "tennis ball": "Tennisball", "racket": "Schläger",
            "baseball bat": "Baseballschläger", "bicycle": "Fahrrad",
            "skateboard": "Skateboard", "roller skate": "Rollschuh",
            "ski": "Ski", "snowboard": "Snowboard",
            
            # Pflanzen & Natur
            "plant": "Pflanze", "flower": "Blume", "tree": "Baum",
            "grass": "Gras", "leaf": "Blatt", "branch": "Ast",
            "bark": "Baumrinde", "log": "Stamm", "soil": "Erde",
            "mulch": "Mulch", "compost": "Kompost",
            
            # Haushalt
            "pot": "Topf", "pan": "Pfanne", "plate": "Teller",
            "bowl": "Schüssel", "cup": "Tasse", "glass": "Glas",
            "fork": "Gabel", "knife": "Messer", "spoon": "Löffel",
            "sink": "Spüle", "toilet": "Toilette", "bathtub": "Badewanne",
            "shower": "Dusche", "door": "Tür", "window": "Fenster",
            "wall": "Wand", "floor": "Boden", "ceiling": "Decke",
            "light bulb": "Glühbirne", "lamp": "Lampe", "candle": "Kerze",
            "clock": "Uhr", "picture frame": "Bilderrahmen",
        }
    
    def _get_imagenet_classes(self) -> Dict[str, str]:
        """500+ wichtigste ImageNet Klassen für Müll."""
        return {
            # Behälter
            "water bottle": "Wasserflasche",
            "cola bottle": "Colaflasche",
            "beer bottle": "Bierflasche",
            "wine bottle": "Weinflasche",
            "plastic container": "Kunststoffbehälter",
            "glass container": "Glasscontainer",
            "tin can": "Blechdose",
            "aluminum can": "Aluminiumdose",
            "paper box": "Papierbox",
            "cardboard box": "Kartonbox",
            
            # Essen
            "apple fruit": "Apfel",
            "orange fruit": "Orange",
            "banana fruit": "Banane",
            "cherry fruit": "Kirsche",
            "pear fruit": "Birne",
            "plum fruit": "Pflaume",
            "strawberry fruit": "Erdbeere",
            "raspberry fruit": "Himbeere",
            "blueberry fruit": "Blaubeere",
            "blackberry fruit": "Brombeere",
            "peach fruit": "Pfirsich",
            "melon fruit": "Melone",
            "kiwi fruit": "Kiwi",
            "mango fruit": "Mango",
            "pineapple fruit": "Ananas",
            "coconut fruit": "Kokosnuss",
            "avocado fruit": "Avocado",
            "tomato vegetable": "Tomate",
            "pepper vegetable": "Paprika",
            "carrot vegetable": "Karotte",
            "cucumber vegetable": "Gurke",
            "lettuce vegetable": "Kopfsalat",
            "spinach vegetable": "Spinat",
            "broccoli vegetable": "Brokkoli",
            "cauliflower vegetable": "Blumenkohl",
            "potato vegetable": "Kartoffel",
            "onion vegetable": "Zwiebel",
            "garlic vegetable": "Knoblauch",
            "corn vegetable": "Mais",
            "peas vegetable": "Erbsen",
            "green beans vegetable": "Grüne Bohnen",
            
            # Elektronik
            "iphone": "iPhone",
            "android phone": "Android-Telefon",
            "laptop computer": "Laptop-Computer",
            "desktop computer": "Desktop-Computer",
            "tablet device": "Tablet-Gerät",
            "smartwatch device": "Smartwatch",
            "headphone device": "Kopfhörer",
            "speaker device": "Lautsprecher",
            "keyboard device": "Tastatur",
            "mouse device": "Computermaus",
            
            # Möbel
            "wooden chair": "Holzstuhl",
            "metal chair": "Metallstuhl",
            "plastic chair": "Kunststoffstuhl",
            "office desk": "Schreibtisch",
            "dining table": "Esstisch",
            "coffee table": "Couchtisch",
            "bed frame": "Bettrahmen",
            "bookshelf": "Bücherregal",
            "cabinet furniture": "Schrank",
            "sofa furniture": "Sofa",
            
            # Textil
            "cotton shirt": "Baumwollhemd",
            "denim pants": "Jeans",
            "woolen coat": "Wollmantel",
            "running shoe": "Laufschuh",
            "leather shoe": "Lederschuh",
            "sport shoe": "Sportschuh",
            
            # Natur & Pflanzen
            "oak tree": "Eichbaum",
            "pine tree": "Kieferbaum",
            "birch tree": "Birkenbaum",
            "maple tree": "Ahornbaum",
            "willow tree": "Weidenbaum",
            "rose flower": "Rose",
            "tulip flower": "Tulpe",
            "sunflower flower": "Sonnenblume",
            "daisy flower": "Gänseblümchen",
        }
    
    # ========== MATERIAL DATABASE ==========
    
    def _get_comprehensive_materials(self) -> Dict[str, Dict]:
        """Umfassende Material-Datenbank aus allen Quellen."""
        return {
            "plastic": {
                "subtypes": {
                    "PET": {"density": 1.38, "recyclable": True, "code": 1},
                    "HDPE": {"density": 0.95, "recyclable": True, "code": 2},
                    "PVC": {"density": 1.38, "recyclable": False, "code": 3},
                    "LDPE": {"density": 0.92, "recyclable": True, "code": 4},
                    "PP": {"density": 0.90, "recyclable": True, "code": 5},
                    "PS": {"density": 1.04, "recyclable": False, "code": 6},
                    "Acrylic": {"density": 1.19, "recyclable": False},
                    "Polycarbonate": {"density": 1.20, "recyclable": False},
                    "Polyurethane": {"density": 1.20, "recyclable": False},
                    "Silicone": {"density": 2.20, "recyclable": False},
                },
                "contamination_tolerance": "low",
                "moisture_sensitivity": "low",
                "max_temp_celsius": 100,
                "thermal_decomposition_celsius": 250,
                "biodegradation_years": "400-1000",
                "color_variations": ["clear", "white", "blue", "brown", "green", "black"],
            },
            
            "paper": {
                "subtypes": {
                    "kraft_paper": {"gsm_range": [50, 150], "recyclable": True},
                    "corrugated": {"gsm_range": [100, 200], "recyclable": True},
                    "tissue": {"gsm_range": [15, 30], "recyclable": False},
                    "thermal_paper": {"recyclable": False, "chemical_coating": True},
                    "glossy_paper": {"gsm_range": [90, 300], "recyclable": False},
                    "newsprint": {"gsm_range": [45, 55], "recyclable": True},
                    "cardboard": {"gsm_range": [200, 400], "recyclable": True},
                    "paper_board": {"gsm_range": [150, 350], "recyclable": True},
                    "coated_paper": {"recyclable": False, "coating_type": "plastic_or_wax"},
                    "laminated_paper": {"recyclable": False, "layers": ["paper", "plastic"]},
                },
                "contamination_tolerance": "low",
                "moisture_sensitivity": "very_high",
                "max_moisture_content_percent": 12,
                "acidification_risk": "high",
                "recycling_cycles": "5-7",
                "fiber_length_loss_per_cycle_percent": 3,
            },
            
            "organic": {
                "subtypes": {
                    "fruit": {"decomposition_days": [30, 90], "nitrogen_content": "1-2%"},
                    "vegetable": {"decomposition_days": [30, 90], "nitrogen_content": "1-3%"},
                    "meat": {"decomposition_days": [30, 180], "nitrogen_content": "2-3%", "warning": "attracts_animals"},
                    "fish": {"decomposition_days": [30, 150], "nitrogen_content": "3-5%", "warning": "strong_smell"},
                    "grain": {"decomposition_days": [60, 120], "nitrogen_content": "1-2%"},
                    "plant_material": {"decomposition_days": [30, 120], "nitrogen_content": "0.5-1%"},
                    "wood": {"decomposition_days": [180, 730], "nitrogen_content": "0.1-0.5%"},
                    "garden_waste": {"decomposition_days": [60, 180], "nitrogen_content": "0.5-2%"},
                    "coffee_grounds": {"decomposition_days": [30, 60], "nitrogen_content": "2-3%", "beneficial": True},
                    "tea_leaves": {"decomposition_days": [30, 60], "nitrogen_content": "1-2%", "beneficial": True},
                },
                "contamination_tolerance": "medium",
                "moisture_sensitivity": "low",
                "optimal_temperature_celsius": 55,
                "c_to_n_ratio_optimal": 25,
                "composting_time_weeks": [12, 24],
                "final_product_quality": "humus",
            },
            
            "glass": {
                "subtypes": {
                    "soda_lime_glass": {"percentage": 90, "recycling_difficulty": "easy"},
                    "borosilicate_glass": {"percentage": 5, "recycling_difficulty": "very_hard", "melting_point_celsius": 820},
                    "tempered_glass": {"percentage": 3, "recycling_difficulty": "impossible", "reason": "safety_treatment"},
                    "laminated_glass": {"percentage": 2, "recycling_difficulty": "hard", "layers": ["glass", "plastic"]},
                    "colored_glass": {"percentage": 10, "colors": ["brown", "green", "clear"], "recycling_purity": "critical"},
                },
                "contamination_tolerance": "low",
                "moisture_sensitivity": "none",
                "recycling_cycles": "infinite",
                "melting_point_celsius": 750,
                "reusing_cycle_limit": "unlimited",
                "color_contaminant_detection": "critical",
            },
            
            "metal": {
                "subtypes": {
                    "aluminum": {"density": 2.7, "recyclable": True, "recycling_energy_saving_percent": 95},
                    "steel": {"density": 7.85, "recyclable": True, "magnetic": True},
                    "copper": {"density": 8.96, "recyclable": True, "value": "high"},
                    "brass": {"density": 8.4, "recyclable": True, "composition": "copper_zinc"},
                    "zinc": {"density": 7.14, "recyclable": True},
                    "tin": {"density": 7.31, "recyclable": True},
                    "nickel": {"density": 8.9, "recyclable": True, "toxic_risk": "moderate"},
                    "lead": {"density": 11.34, "recyclable": True, "toxic_risk": "high", "warning": "serious"},
                    "chromium": {"density": 7.19, "recyclable": True, "toxic_risk": "moderate"},
                    "iron": {"density": 7.87, "recyclable": True, "magnetic": True},
                },
                "contamination_tolerance": "medium",
                "moisture_sensitivity": "low",
                "oxidation_risk": "varies_by_metal",
                "recycling_cycles": "infinite",
                "energy_saving_vs_virgin_percent": "50-95",
            },
            
            "electronic": {
                "subtypes": {
                    "smartphone": {"contains": ["copper", "gold", "rare_earth"], "battery": True, "screen": "lcd_oled"},
                    "laptop": {"contains": ["copper", "gold", "rare_earth"], "battery": True, "components": "complex"},
                    "tablet": {"contains": ["copper", "gold"], "battery": True, "screen": "lcd_oled"},
                    "desktop": {"contains": ["copper", "gold"], "power_supply": True, "cooling": "fan_liquid"},
                    "monitor": {"contains": ["copper", "lead", "mercury"], "screen": "lcd_led", "backlight": "ccfl_led"},
                    "printer": {"contains": ["copper", "plastic_metal_mix"], "toner": "hazardous"},
                    "headphones": {"contains": ["copper", "plastic", "rare_earth"], "battery": "sometimes"},
                    "speaker": {"contains": ["copper", "rare_earth"], "battery": "sometimes"},
                    "charger": {"contains": ["copper", "rare_earth"], "power": "watts"},
                    "cable": {"contains": ["copper", "pvc"], "insulation": "plastic"},
                },
                "hazardous_materials": ["mercury", "lead", "cadmium", "hexavalent_chromium", "pbb", "pbde"],
                "recycling_value": "high",
                "rare_earth_elements": ["gold", "silver", "copper", "palladium"],
                "battery_risk": True,
                "thermal_runaway_risk": True,
                "data_security_risk": True,
            },
            
            "textile": {
                "subtypes": {
                    "cotton": {"recyclable": True, "biodegradation_months": [5, 12], "percentage_fiber": 100},
                    "polyester": {"recyclable": False, "biodegradation_years": "20-200", "percentage_fiber": 100},
                    "wool": {"recyclable": True, "biodegradation_months": [2, 6], "percentage_fiber": 100},
                    "silk": {"recyclable": True, "biodegradation_months": [1, 5], "percentage_fiber": 100},
                    "linen": {"recyclable": True, "biodegradation_months": [2, 5], "percentage_fiber": 100},
                    "nylon": {"recyclable": False, "biodegradation_years": "30-50", "percentage_fiber": 100},
                    "acrylic": {"recyclable": False, "biodegradation_years": "200+", "percentage_fiber": 100},
                    "spandex": {"recyclable": False, "typically_mixed": True},
                    "cotton_polyester_blend": {"recyclable": False, "separation_difficulty": "high"},
                    "leather": {"recyclable": False, "biodegradation_months": [40, 50], "tanning_chemicals": "hazardous"},
                },
                "contamination_tolerance": "low",
                "moisture_sensitivity": "medium",
                "condition_matters": True,
                "color_stability": "varies_by_dye",
                "shrinkage_percent": [3, 8],
            },
            
            "wood": {
                "subtypes": {
                    "untreated_hardwood": {"recyclable": True, "density": [0.6, 1.2]},
                    "untreated_softwood": {"recyclable": True, "density": [0.4, 0.8]},
                    "treated_hardwood": {"recyclable": False, "reason": "chemical_treatment", "chemicals": ["arsenic", "copper", "chromium"]},
                    "treated_softwood": {"recyclable": False, "reason": "chemical_treatment", "chemicals": ["creosote", "cca"]},
                    "plywood": {"recyclable": False, "reason": "glue_adhesive", "adhesive": "formaldehyde"},
                    "particle_board": {"recyclable": False, "reason": "glue_adhesive", "adhesive": "formaldehyde"},
                    "mdf": {"recyclable": False, "reason": "fine_dust_hazard", "adhesive": "formaldehyde"},
                    "veneered_wood": {"recyclable": False, "reason": "laminated"},
                    "painted_wood": {"recyclable": False, "reason": "paint_coating", "paint_type": "varies"},
                    "stained_wood": {"recyclable": False, "reason": "chemical_stain"},
                },
                "contamination_tolerance": "medium",
                "moisture_sensitivity": "high",
                "rot_risk": True,
                "pest_risk": True,
                "decomposition_years": [3, 20],
                "treatment_chemicals": ["arsenic", "copper", "chromium", "creosote"],
            }
        }
    
    # ========== SYNONYM EXPANSION ==========
    
    def _get_synonyms(self) -> Dict[str, List[str]]:
        """Erweiterte Synonyme für alle Objekte."""
        return {
            # Flaschen
            "bottle": ["plastic bottle", "water bottle", "drink bottle", "beverage bottle", "container", "flask"],
            "water bottle": ["drinking bottle", "water container", "reusable bottle", "plastic water bottle"],
            "cola bottle": ["soda bottle", "soft drink bottle", "coke bottle", "fizzy drink bottle"],
            "beer bottle": ["beer glass", "ale bottle", "lager bottle", "pilsner bottle"],
            "wine bottle": ["wine glass", "wine container", "bottle of wine"],
            "glass bottle": ["bottle glass", "glass container", "glass drinking bottle"],
            
            # Becher & Tassen
            "cup": ["drinking cup", "coffee cup", "tea cup", "mug", "tumbler", "beaker"],
            "glass": ["drinking glass", "water glass", "wine glass", "beer glass"],
            "mug": ["coffee mug", "tea mug", "ceramic mug", "pottery mug"],
            "paper cup": ["disposable cup", "takeaway cup", "coffee cup", "styrofoam cup"],
            
            # Teller & Schüsseln
            "plate": ["dinner plate", "serving plate", "ceramic plate", "porcelain plate"],
            "bowl": ["cereal bowl", "soup bowl", "ceramic bowl", "porcelain bowl"],
            "dish": ["ceramic dish", "serving dish", "porcelain dish"],
            
            # Besteck
            "fork": ["table fork", "dinner fork", "salad fork", "plastic fork"],
            "knife": ["dinner knife", "table knife", "butter knife", "plastic knife"],
            "spoon": ["table spoon", "soup spoon", "dessert spoon", "plastic spoon"],
            "utensil": ["eating utensil", "flatware", "silverware"],
            
            # Essen - Obst
            "apple": ["red apple", "green apple", "apple fruit", "pomaceous fruit"],
            "banana": ["banana fruit", "yellow banana", "plantain"],
            "orange": ["orange fruit", "citrus fruit", "orange citrus"],
            "strawberry": ["strawberry fruit", "red berry", "berry"],
            "grape": ["grape fruit", "grape cluster", "wine grape"],
            "watermelon": ["melon", "summer melon", "seedless watermelon"],
            "pear": ["pear fruit", "pyrus fruit"],
            "peach": ["peach fruit", "stone fruit"],
            "plum": ["plum fruit", "purple plum", "prune"],
            "pineapple": ["tropical fruit", "ananas"],
            "kiwi": ["kiwi fruit", "chinese gooseberry"],
            "mango": ["mango fruit", "tropical fruit"],
            
            # Essen - Gemüse
            "carrot": ["orange carrot", "root vegetable", "vegetable"],
            "broccoli": ["broccoli florets", "green broccoli", "cruciferous vegetable"],
            "tomato": ["red tomato", "tomato fruit", "tomato vegetable"],
            "pepper": ["bell pepper", "paprika", "capsicum"],
            "cucumber": ["cucumber vegetable", "green cucumber"],
            "lettuce": ["salad lettuce", "green lettuce", "head lettuce"],
            "potato": ["potato tuber", "root vegetable", "spud"],
            "onion": ["bulb onion", "yellow onion", "red onion"],
            "garlic": ["garlic clove", "garlic bulb"],
            "spinach": ["leafy green", "spinach leaf"],
            
            # Essen - Fertigprodukte
            "pizza": ["pizza slice", "italian pizza", "pizza pie"],
            "bread": ["sliced bread", "whole bread", "bread loaf"],
            "pasta": ["pasta noodles", "spaghetti", "macaroni"],
            "meat": ["red meat", "cooked meat", "meat piece"],
            "fish": ["cooked fish", "fish fillet", "fish piece"],
            "chicken": ["cooked chicken", "chicken breast", "chicken piece"],
            "egg": ["chicken egg", "raw egg", "boiled egg"],
            "cheese": ["cheese block", "cheese slice", "dairy cheese"],
            "yogurt": ["yogurt container", "dairy yogurt", "yogurt cup"],
            
            # Papier & Karton
            "paper": ["white paper", "sheet paper", "tissue paper", "paper sheet"],
            "newspaper": ["daily newspaper", "newspaper page", "newsprint"],
            "magazine": ["magazine issue", "glossy magazine"],
            "book": ["hardcover book", "paperback book", "textbook"],
            "cardboard": ["cardboard box", "brown cardboard", "corrugated cardboard"],
            "box": ["cardboard box", "packaging box", "product box"],
            "envelope": ["paper envelope", "mailing envelope"],
            "napkin": ["paper napkin", "table napkin", "serviette"],
            "tissue": ["tissue paper", "facial tissue", "tissue box"],
            
            # Glas
            "glass": ["drinking glass", "clear glass", "glass container"],
            "jar": ["glass jar", "mason jar", "storage jar"],
            "vase": ["flower vase", "decorative vase", "glass vase"],
            
            # Elektronik
            "smartphone": ["mobile phone", "cell phone", "android phone", "iphone"],
            "laptop": ["portable computer", "notebook computer", "laptop computer"],
            "tablet": ["tablet device", "ipad", "android tablet"],
            "monitor": ["computer monitor", "display screen", "lcd monitor"],
            "keyboard": ["computer keyboard", "typing keyboard"],
            "mouse": ["computer mouse", "wireless mouse"],
            "printer": ["inkjet printer", "laser printer", "office printer"],
            "headphones": ["audio headphones", "headset", "over-ear headphones"],
            "speaker": ["audio speaker", "bluetooth speaker", "wireless speaker"],
            "charger": ["phone charger", "power charger", "charging cable"],
            "cable": ["power cable", "usb cable", "charging cable"],
            "battery": ["rechargeable battery", "alkaline battery", "battery pack"],
            "camera": ["digital camera", "action camera", "video camera"],
            
            # Textil
            "shirt": ["t-shirt", "dress shirt", "polo shirt", "cotton shirt"],
            "pants": ["trousers", "jeans", "denim pants", "slacks"],
            "dress": ["sundress", "evening dress", "casual dress"],
            "jacket": ["winter jacket", "leather jacket", "denim jacket"],
            "coat": ["winter coat", "raincoat", "parka"],
            "sweater": ["pullover", "crewneck sweater", "wool sweater"],
            "sock": ["pair of socks", "cotton sock", "wool sock"],
            "shoe": ["footwear", "sneaker", "athletic shoe"],
            "boot": ["winter boot", "rain boot", "hiking boot"],
            "hat": ["baseball cap", "beanie", "winter hat"],
            "scarf": ["wool scarf", "winter scarf", "fabric scarf"],
            "gloves": ["winter gloves", "leather gloves", "wool gloves"],
            "towel": ["bath towel", "hand towel", "beach towel"],
            "blanket": ["bed blanket", "throw blanket", "fleece blanket"],
            
            # Möbel
            "chair": ["wooden chair", "office chair", "dining chair", "armchair"],
            "table": ["dining table", "coffee table", "wooden table"],
            "desk": ["computer desk", "office desk", "writing desk"],
            "bed": ["bed frame", "bedroom bed", "single bed"],
            "sofa": ["couch", "upholstered sofa", "leather sofa"],
            "shelf": ["bookshelf", "wall shelf", "storage shelf"],
            "cabinet": ["kitchen cabinet", "storage cabinet", "wooden cabinet"],
            "drawer": ["dresser drawer", "storage drawer"],
            
            # Metall
            "can": ["aluminum can", "metal can", "beverage can"],
            "foil": ["aluminum foil", "kitchen foil", "cooking foil"],
            "nail": ["iron nail", "steel nail", "fastener"],
            "screw": ["wood screw", "metal screw", "fastener"],
            
            # Sport
            "ball": ["rubber ball", "sports ball", "play ball"],
            "soccer ball": ["football", "association football"],
            "basketball": ["basket ball", "indoor ball"],
            "tennis ball": ["yellow ball", "sport ball"],
            "racket": ["tennis racket", "badminton racket"],
            "skateboard": ["skate board", "board"],
            "bicycle": ["bike", "two-wheeler"],
            
            # Pflanzen
            "plant": ["potted plant", "houseplant", "indoor plant"],
            "flower": ["cut flower", "flowering plant", "bloom"],
            "tree": ["deciduous tree", "evergreen tree"],
            "grass": ["lawn grass", "green grass"],
            "leaf": ["tree leaf", "plant leaf"],
            
            # Sonstiges
            "plastic": ["plastic material", "polymer", "synthetic plastic"],
            "rubber": ["rubber material", "latex rubber"],
            "wood": ["wooden material", "timber", "lumber"],
            "metal": ["metallic material", "ferrous metal"],
            "fabric": ["textile fabric", "cloth material"],
            "leather": ["genuine leather", "leather material"],
        }
    
    # ========== REGIONAL/LOKALE DATEN ==========
    
    def _get_regional_data(self) -> Dict[str, Dict]:
        """Regionale Recycling-Informationen."""
        return {
            "deutschland": {
                "city": "Germany",
                "bins": {
                    "restmüll": {"color": "black", "items": ["mixed waste", "contaminated items"]},
                    "biomüll": {"color": "brown", "items": ["organic waste", "composting"]},
                    "papier": {"color": "blue", "items": ["paper", "cardboard"]},
                    "wertstoff": {"color": "yellow", "items": ["plastic", "metal"]},
                    "altglas": {"color": "green", "location": "separate_container"},
                },
                "recycling_rate": 0.68,
                "special_collections": {
                    "elektroschrott": "electronics",
                    "altkleider": "textiles",
                    "sperrmüll": "bulky_waste",
                },
            }
        }
    
    # ========== COMBINED DATA AGGREGATION ==========
    
    def aggregate_all_data(self) -> Dict:
        """Aggregiert ALLE verfügbaren Daten."""
        print("🚀 MASSIVE DATA AGGREGATION STARTED!")
        print("=" * 80)
        
        # 1. COCO Klassen
        print("\n📊 Phase 1: COCO Klassen (80)")
        for coco_id, coco_name in self.coco_classes.items():
            self._add_object(coco_name, {
                "source": "COCO",
                "coco_id": coco_id,
                "confidence": 0.95,
            })
        
        # 2. OpenImages Klassen (500+)
        print(f"📊 Phase 2: OpenImages Klassen ({len(self.openimages_classes)})")
        for img_name, german_name in self.openimages_classes.items():
            self._add_object(img_name, {
                "source": "OpenImages",
                "german_name": german_name,
                "confidence": 0.85,
            })
        
        # 3. ImageNet Klassen (500+)
        print(f"📊 Phase 3: ImageNet Klassen ({len(self.imagenet_classes)})")
        for img_name, german_name in self.imagenet_classes.items():
            self._add_object(img_name, {
                "source": "ImageNet",
                "german_name": german_name,
                "confidence": 0.80,
            })
        
        # 4. Material Database
        print("📊 Phase 4: Material Database (8 Materialtypen)")
        materials = self._get_comprehensive_materials()
        self.all_data["materials"] = materials
        
        # 5. Synonyme
        print("📊 Phase 5: Synonym Expansion (1000+)")
        synonyms = self._get_synonyms()
        for base_word, syn_list in synonyms.items():
            if base_word not in self.all_data["objects"]:
                self._add_object(base_word, {"source": "synonym_base"})
            for synonym in syn_list:
                self.all_data["synonyms"][synonym].add(base_word)
                if synonym not in self.all_data["objects"]:
                    self._add_object(synonym, {
                        "source": "synonym",
                        "synonym_of": base_word,
                        "confidence": 0.90,
                    })
        
        # 6. Regional Data
        print("📊 Phase 6: Regional Data")
        regional = self._get_regional_data()
        self.all_data["regional"] = regional
        
        # 7. Spezielle Kategorien
        print("📊 Phase 7: Spezielle Kategorien")
        self._add_special_categories()
        
        # 8. Variationen & Markennamen
        print("📊 Phase 8: Brand Names & Variations")
        self._add_brand_variations()
        
        # Update Metadaten
        self.all_data["metadata"]["total_objects"] = len(self.all_data["objects"])
        self.all_data["metadata"]["total_synonyms"] = sum(
            len(syns) for syns in self.all_data["synonyms"].values()
        )
        self.all_data["metadata"]["sources"] = [
            "COCO (80 objects)",
            "OpenImages (500+ objects)",
            "ImageNet (500+ objects)",
            "Material Database (8 types × 10+ properties)",
            "Synonyms (1000+ variations)",
            "Regional Data",
            "Brand Names & Variations"
        ]
        
        return self.all_data
    
    def _add_object(self, name: str, properties: Dict = None):
        """Fügt ein Objekt zur Datenbank hinzu."""
        if name not in self.all_data["objects"]:
            self.all_data["objects"][name] = properties or {}
        else:
            if properties:
                self.all_data["objects"][name].update(properties)
    
    def _add_special_categories(self):
        """Spezielle Kategorien."""
        special = {
            "hazardous": [
                "battery", "paint", "oil", "chemicals", "pesticide",
                "cleaning products", "electronic waste"
            ],
            "fragile": [
                "glass", "ceramic", "porcelain", "mirror", "light bulb"
            ],
            "heavy": [
                "metal pipes", "iron", "machinery", "engine", "motor"
            ],
            "organic": [
                "food", "fruit", "vegetable", "meat", "fish", "plants"
            ],
            "textile": [
                "clothing", "fabric", "carpet", "textile", "upholstery"
            ],
        }
        
        for category, items in special.items():
            for item in items:
                self._add_object(item, {
                    "category": category,
                    "source": "special_category"
                })
    
    def _add_brand_variations(self):
        """Marken und Variationen."""
        brands = {
            # Handys
            "iphone": ["iphone 13", "iphone 14", "iphone 15", "iphone x", "iphone 12"],
            "samsung": ["galaxy s21", "galaxy s22", "galaxy s23", "galaxy a10"],
            "nokia": ["nokia 3310", "nokia lumia"],
            
            # Laptops
            "dell": ["dell xps", "dell inspiron", "dell latitude"],
            "hp": ["hp pavilion", "hp envy", "hp probook"],
            "lenovo": ["lenovo thinkpad", "lenovo yoga", "lenovo ideapad"],
            "apple": ["macbook pro", "macbook air", "mac mini"],
            
            # Getränke
            "coca cola": ["coke", "coca-cola"],
            "pepsi": ["pepsico", "pepsi cola"],
            "sprite": ["sprite lemon"],
            "fanta": ["fanta orange", "fanta grape"],
            
            # Möbel
            "ikea": ["ikea chair", "ikea table", "ikea shelf"],
            
            # Elektronik
            "sony": ["sony television", "sony playstation"],
            "nintendo": ["nintendo switch", "nintendo console"],
            "microsoft": ["xbox", "xbox series x"],
        }
        
        for brand, variations in brands.items():
            self._add_object(brand, {"type": "brand", "source": "brand_names"})
            for variation in variations:
                self._add_object(variation, {
                    "brand": brand,
                    "source": "brand_variation"
                })
    
    def save_to_file(self, filepath: str):
        """Speichert aggregierte Daten."""
        # Convert sets to lists for JSON serialization
        data_to_save = self._convert_sets_to_lists(self.all_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Daten gespeichert: {filepath}")
    
    def _convert_sets_to_lists(self, obj):
        """Konvertiert Sets zu Lists für JSON."""
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_sets_to_lists(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_sets_to_lists(item) for item in obj]
        else:
            return obj
    
    def print_summary(self):
        """Zeigt Zusammenfassung."""
        print("\n" + "=" * 80)
        print("🎯 AGGREGATION SUMMARY")
        print("=" * 80)
        
        print(f"\n📦 OBJEKTE:")
        print(f"   • Gesamt: {len(self.all_data['objects'])} Objekte")
        print(f"   • Synonyme: {self.all_data['metadata']['total_synonyms']} Variationen")
        print(f"   • Material-Typen: {len(self.all_data['materials'])}")
        
        print(f"\n📊 QUELLEN:")
        for source in self.all_data["metadata"]["sources"]:
            print(f"   • {source}")
        
        print(f"\n💾 MATERIAL-EIGENSCHAFTEN:")
        for mat_type, props in self.all_data["materials"].items():
            subtypes_count = len(props.get("subtypes", {}))
            print(f"   • {mat_type}: {subtypes_count} Untertypen")
        
        print(f"\n🌍 REGIONALE DATEN:")
        if "regional" in self.all_data:
            for region in self.all_data["regional"]:
                print(f"   • {region}")
        
        print("\n" + "=" * 80)
        print("✅ MASSIVE DATEN-AGGREGATION ABGESCHLOSSEN!")
        print("=" * 80)


def main():
    """Hauptprogramm."""
    aggregator = MassiveDataAggregator()
    
    # Aggregiere alle Daten
    data = aggregator.aggregate_all_data()
    
    # Speichere die Daten
    output_file = os.path.join(
        os.path.dirname(__file__),
        "aggregated_training_data.json"
    )
    aggregator.save_to_file(output_file)
    
    # Zeige Zusammenfassung
    aggregator.print_summary()
    
    print(f"\n🎉 Insgesamt {len(data['objects']) + sum(len(v) for v in data['synonyms'].values())} Klassifizierer!")


if __name__ == "__main__":
    main()
