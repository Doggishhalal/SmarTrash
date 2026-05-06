"""
Waste Classification System - Intelligente Mülltrennung
========================================================
Ordnet erkannte Objekte den 4 Mülltonnen zu: Restmüll, Biomüll, Papier, Plastik
Berücksichtigt Material, Zustand und Verunreinigungen
"""
from typing import Dict, List, Optional

import cv2
import numpy as np
from safety_config import get_config


class WasteClassifier:
    """Klassifiziert Müll in die richtige Tonne basierend auf Objekt, Material und Zustand"""

    # 4 Mülltonnen
    BINS = {
        "PLASTIK": "Gelbe Tonne / Wertstofftonne",
        "PAPIER": "Blaue Tonne / Papiertonne",
        "BIOMÜLL": "Braune Tonne / Biotonne",
        "RESTMÜLL": "Schwarze Tonne / Restmülltonne"
    }

    # UMFASSENDE MÜLLKLASSIFIZIERUNG (300+ Objekte mit Materialdetails)
    # Format: "name": {"primary": TONNE, "material": TYP, "recyclable": BOOL, ...weitere Properties}
    WASTE_MAPPING = {
        # ===== PLASTIK / KUNSTSTOFF (Wertstofftonne) =====
        # Verpackungen & Behälter
        "bottle": {"primary": "PLASTIK", "material": "plastic", "type": "PET", "recyclable": True},
        "plastic bottle": {"primary": "PLASTIK", "material": "plastic", "type": "PET", "recyclable": True},
        "water bottle": {"primary": "PLASTIK", "material": "plastic", "type": "PET", "recyclable": True},
        "juice bottle": {"primary": "PLASTIK", "material": "plastic", "type": "PET", "recyclable": True},
        "cola bottle": {"primary": "PLASTIK", "material": "plastic", "type": "PET", "recyclable": True},
        "cup": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic cup": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "takeout container": {"primary": "PLASTIK", "material": "plastic", "type": "PP", "recyclable": True},
        "bowl": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic bowl": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "bag": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic bag": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "shopping bag": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "trash bag": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False, "note": "Mit Inhalt = Restmüll"},
        "packaging": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "package": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "wrapping": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "bubble wrap": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "foam": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "styrofoam": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "container": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic container": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic lid": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "lid": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "cap": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "bottle cap": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "straw": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic straw": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "bucket": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic bucket": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "crate": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic crate": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        
        # Essensbesteck & Geschirr
        "fork": {"primary": "PLASTIK", "material": "plastic", "recyclable": False, "note": "Einwegbesteck"},
        "plastic fork": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "knife": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "plastic knife": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "spoon": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "plastic spoon": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "plate": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic plate": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "dish": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "plastic dish": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        
        # Haushalt & Konsumgüter
        "toothbrush": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "plastic toothbrush": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "comb": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "hairbrush": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "brush": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "plastic brush": {"primary": "PLASTIK", "material": "plastic", "recyclable": False},
        "toy": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False, "note": "Je nach Zustand"},
        "plastic toy": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "doll": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "figurine": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "action figure": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "lego": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False, "note": "Zu kontaminiert"},
        
        # Sportgeräte & Freizeit
        "frisbee": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "boomerang": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "disc": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        
        # Verpackungen spezial
        "blister pack": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "clamshell": {"primary": "PLASTIK", "material": "plastic", "recyclable": True},
        "candy wrapper": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False, "note": "Zu kontaminiert"},
        "chip bag": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False, "note": "Aluminiumkaschiert"},
        "snack bag": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "food wrapper": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False, "note": "Fett/Öl"},
        "chocolate wrapper": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        
        # ===== PAPIER & KARTON (Papiertonne) =====
        "book": {"primary": "PAPIER", "material": "paper", "type": "book_paper", "recyclable": True},
        "magazine": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "newspaper": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "paper": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "cardboard": {"primary": "PAPIER", "material": "paper", "type": "cardboard", "recyclable": True},
        "cardboard box": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "box": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "carton": {"primary": "PAPIER", "material": "paper", "type": "carton", "recyclable": True},
        "paper bag": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "brown bag": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "envelope": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "letter": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "paper sheet": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "notebook": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "notepad": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "memo": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "flyer": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "brochure": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "pamphlet": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "receipt": {"primary": "RESTMÜLL", "material": "paper", "recyclable": False, "note": "Thermopapier"},
        "paper towel": {"primary": "PAPIER", "material": "paper", "recyclable": True, "note": "Küchenpapier"},
        "paper towels": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "kitchen roll": {"primary": "PAPIER", "material": "paper", "recyclable": True, "note": "Küchenrolle"},
        "toilet paper": {"primary": "PAPIER", "material": "paper", "recyclable": True, "note": "Toilettenpapier"},
        "toilet tissue": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "tissue": {"primary": "PAPIER", "material": "paper", "recyclable": True, "note": "Taschentuch"},
        "facial tissue": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "napkin": {"primary": "BIOMÜLL", "material": "paper", "recyclable": False, "note": "Papierserviette meist verschmutzt → Bio"},
        "serviette": {"primary": "BIOMÜLL", "material": "paper", "recyclable": False, "note": "Papierserviette dreckig → Bio"},
        "paper napkin": {"primary": "BIOMÜLL", "material": "paper", "recyclable": False, "note": "Papierserviette → Bio"},
        "handkerchief": {"primary": "PAPIER", "material": "paper", "recyclable": True, "note": "Taschentuch"},
        "egg carton": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "egg box": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "pizza box": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "pizza carton": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "paper cup": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "coffee cup": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "hot cup": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "paper plate": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "paper container": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "corrugated cardboard": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "paper roll": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "paper tube": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        "cardboard tube": {"primary": "PAPIER", "material": "paper", "recyclable": True},
        
        # ===== BIOMÜLL (Biotonne) =====
        # Obst & Gemüse
        "apple": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "apples": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "orange": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "oranges": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "banana": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "bananas": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "grape": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "grapes": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "strawberry": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "strawberries": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "blueberry": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "blueberries": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "watermelon": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "melon": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "pineapple": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "pear": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "pears": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "peach": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "peaches": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "plum": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "plums": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "cherry": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "cherries": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "lemon": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "lemons": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "lime": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        "coconut": {"primary": "BIOMÜLL", "material": "organic", "type": "fruit", "recyclable": False},
        
        "vegetable": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "vegetables": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "broccoli": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "carrot": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "carrots": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "potato": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "potatoes": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "cabbage": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "lettuce": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "spinach": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "tomato": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "tomatoes": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "cucumber": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "pepper": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "peppers": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "onion": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "onions": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "garlic": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "corn": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "maize": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "bean": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "beans": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "pea": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "peas": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "beet": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "beetroot": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "celery": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "asparagus": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "mushroom": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "mushrooms": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        
        # Essensreste & Speisen
        "food": {"primary": "BIOMÜLL", "material": "organic", "type": "food_waste", "recyclable": False},
        "food waste": {"primary": "BIOMÜLL", "material": "organic", "type": "food_waste", "recyclable": False},
        "leftover": {"primary": "BIOMÜLL", "material": "organic", "type": "food_waste", "recyclable": False},
        "leftovers": {"primary": "BIOMÜLL", "material": "organic", "type": "food_waste", "recyclable": False},
        "bread": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "sandwich": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "sandwiches": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "pizza": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "pasta": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "rice": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "soup": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "sauce": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "meat": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "fish": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "chicken": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "egg": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "eggs": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "eggshell": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "eggshells": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "cheese": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "yogurt": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "milk": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "butter": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "oil": {"primary": "RESTMÜLL", "material": "organic", "recyclable": False, "special": "Sammelstelle"},
        "cooking oil": {"primary": "RESTMÜLL", "material": "organic", "recyclable": False, "special": "Sammelstelle"},
        "grease": {"primary": "RESTMÜLL", "material": "organic", "recyclable": False, "special": "Sammelstelle"},
        "fat": {"primary": "RESTMÜLL", "material": "organic", "recyclable": False, "special": "Sammelstelle"},
        "donut": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "donuts": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "cake": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "cakes": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "cookie": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "cookies": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "ice cream": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "candy": {"primary": "RESTMÜLL", "material": "organic", "recyclable": False, "note": "Mit Verpackung"},
        "chocolate": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "nuts": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "almonds": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "seeds": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "herb": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "herbs": {"primary": "BIOMÜLL", "material": "organic", "type": "vegetable", "recyclable": False},
        "spices": {"primary": "BIOMÜLL", "material": "organic", "type": "food", "recyclable": False},
        "coffee grounds": {"primary": "BIOMÜLL", "material": "organic", "type": "food_waste", "recyclable": False},
        "tea leaves": {"primary": "BIOMÜLL", "material": "organic", "type": "food_waste", "recyclable": False},
        "tea bag": {"primary": "BIOMÜLL", "material": "organic", "type": "food_waste", "recyclable": False},
        
        # Pflanzen & Garten
        "potted plant": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False, "note": "Pflanze zu Bio, Topf zu Plastik"},
        "plant": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "flower": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "flowers": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "tree": {"primary": "RESTMÜLL", "material": "wood", "recyclable": False, "special": "Sperrmüll/Grünschnitt"},
        "branch": {"primary": "RESTMÜLL", "material": "wood", "recyclable": False, "special": "Grünschnitt"},
        "branches": {"primary": "RESTMÜLL", "material": "wood", "recyclable": False, "special": "Grünschnitt"},
        "leaf": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "leaves": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "grass": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "hay": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "straw": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "wood chips": {"primary": "RESTMÜLL", "material": "wood", "recyclable": False, "special": "Grünschnitt"},
        "saw dust": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "soil": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        "compost": {"primary": "BIOMÜLL", "material": "organic", "type": "plant", "recyclable": False},
        
        # Besonderheiten Bio
        "pferdepenal": {"primary": "BIOMÜLL", "material": "organic", "recyclable": False, "note": "Pferde-Kotbeutel → Biotonne"},
        "animal waste": {"primary": "BIOMÜLL", "material": "organic", "type": "animal", "recyclable": False},
        "pet waste": {"primary": "BIOMÜLL", "material": "organic", "type": "animal", "recyclable": False},
        "feather": {"primary": "BIOMÜLL", "material": "organic", "type": "animal", "recyclable": False},
        "feathers": {"primary": "BIOMÜLL", "material": "organic", "type": "animal", "recyclable": False},
        "fur": {"primary": "BIOMÜLL", "material": "organic", "type": "animal", "recyclable": False},
        
        # ===== GLAS (aber in Altglascontainer, nicht Haustonne!) =====
        "glass": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "bottle glass": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "wine glass": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "glass bottle": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "beer bottle": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "wine bottle": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "glass jar": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "jar": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "vase": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "glass cup": {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"},
        "mirror": {"primary": "RESTMÜLL", "material": "glass", "recyclable": False, "note": "Spiegel/Spiegelglas"},
        "window": {"primary": "RESTMÜLL", "material": "glass", "recyclable": False, "special": "Sperrmüll"},
        "picture frame": {"primary": "RESTMÜLL", "material": "glass", "recyclable": False},
        
        # ===== ELEKTRONIK & ELEKTROSCHROTT =====
        # Smartphones, Computer
        "cell phone": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "mobile phone": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "smartphone": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "phone": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "iphone": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "android": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "laptop": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "notebook": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "computer": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "pc": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "desktop": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott/Wertstoffhof"},
        "tablet": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        "ipad": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott/Wertstoffhof"},
        
        # Eingabegeräte
        "mouse": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "keyboard": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "monitor": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "display": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "screen": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "printer": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "scanner": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        
        # TV & Audio
        "tv": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "television": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "speaker": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "speakers": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "headphone": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "headphones": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "earbud": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "earbuds": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "microphone": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "radio": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        
        # Kameras & Optik
        "camera": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "camera": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "camcorder": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "video camera": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "webcam": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        
        # Kleingeräte & Zubehör
        "remote": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterien entfernen"},
        "remote control": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterien entfernen"},
        "clock": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterie entfernen"},
        "watch": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterie entfernen"},
        "smartwatch": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterie entfernen"},
        "fitness tracker": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterie entfernen"},
        "charger": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "power adapter": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "cable": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "usb cable": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "power cord": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "power bank": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterie-Warnung!"},
        "battery": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Sammelstelle"},
        "batteries": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Sammelstelle"},
        "rechargeable battery": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Sammelstelle"},
        "accumulator": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Sammelstelle"},
        "flashlight": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterien entfernen"},
        "torch": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Batterien entfernen"},
        "lamp": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "light bulb": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "led bulb": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "fluorescent bulb": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Quecksilber-Warnung!"},
        
        # Haushaltsgeräte
        "hair drier": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "hairdryer": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "hair dryer": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "toaster": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "kettle": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "microwave": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "oven": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "cooktop": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "stove": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "refrigerator": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "fridge": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "freezer": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "washing machine": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "dryer": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "dishwasher": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Wertstoffhof"},
        "vacuum": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "iron": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "coffee maker": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "coffee machine": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "blender": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "mixer": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        
        # Gaming & Freizeit
        "gaming console": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "playstation": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "xbox": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "nintendo": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "controller": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "game controller": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "joystick": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        "vr headset": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": True, "special": "Elektroschrott"},
        
        # Netzwerkgeräte
        "router": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "modem": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        "switch": {"primary": "RESTMÜLL", "material": "electronic", "battery_warning": False, "special": "Elektroschrott"},
        
        # ===== METALL & VERPACKUNGEN =====
        "can": {"primary": "PLASTIK", "material": "metal", "type": "aluminum", "recyclable": True, "note": "Wertstoffsammlung"},
        "aluminum can": {"primary": "PLASTIK", "material": "metal", "type": "aluminum", "recyclable": True},
        "aluminum": {"primary": "PLASTIK", "material": "metal", "type": "aluminum", "recyclable": True},
        "metal can": {"primary": "PLASTIK", "material": "metal", "recyclable": True},
        "tin can": {"primary": "PLASTIK", "material": "metal", "recyclable": True},
        "foil": {"primary": "PLASTIK", "material": "metal", "type": "aluminum", "recyclable": True, "note": "Alufolie → Wertstoff"},
        "aluminum foil": {"primary": "PLASTIK", "material": "metal", "type": "aluminum", "recyclable": True},
        "baking foil": {"primary": "PLASTIK", "material": "metal", "type": "aluminum", "recyclable": True},
        
        # ===== TEXTILE & KLEIDUNG =====
        "clothing": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider-Container"},
        "clothes": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider-Container"},
        "shirt": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "pants": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "dress": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "skirt": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "jacket": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "coat": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "sweater": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "sweatshirt": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "hoodie": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "sock": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "socks": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "shoe": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "shoes": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "boot": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "boots": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "underwear": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "tie": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "scarf": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "glove": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "gloves": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "hat": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "cap": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "handbag": {"primary": "RESTMÜLL", "material": "leather", "recyclable": False},
        "backpack": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False},
        "bag": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False},
        "towel": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "cloth": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "rags": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "blanket": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "special": "Sperrmüll"},
        "curtain": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "special": "Sperrmüll"},
        "bedsheet": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "Altkleider"},
        "pillow": {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "special": "Sperrmüll"},
        
        # ===== MÖBEL & GROßMÜLL (Sperrmüll) =====
        "chair": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "couch": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "sofa": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "bed": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "mattress": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "table": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "dining table": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "desk": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "shelf": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "cabinet": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "bookshelf": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "wardrobe": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "cupboard": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "dresser": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "nightstand": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "bench": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "stool": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        
        # ===== SPORTGERÄTE & SPIELZEUG =====
        "sports ball": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False},
        "ball": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False},
        "football": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False},
        "basketball": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False},
        "soccer ball": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False},
        "tennis ball": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False},
        "ping pong ball": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "baseball": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False},
        "toy": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False, "note": "Je nach Zustand"},
        "doll": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "action figure": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "lego": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False, "note": "Zu kontaminiert"},
        "puzzle": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "board game": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "baseball bat": {"primary": "RESTMÜLL", "material": "wood", "recyclable": False},
        "baseball glove": {"primary": "RESTMÜLL", "material": "leather", "recyclable": False},
        "tennis racket": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "tennis racquet": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "skateboard": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "skateboard": {"primary": "RESTMÜLL", "material": "wood", "recyclable": False},
        "skis": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "snowboard": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "surfboard": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "bicycle": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "bike": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll"},
        "roller skates": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "ice skates": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        
        # ===== SONSTIGES & RESTMÜLL =====
        "person": {"primary": "RESTMÜLL", "material": "none", "recyclable": False, "note": "Nicht Müll!"},
        "car": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Schrottplatz"},
        "umbrella": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "suitcase": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "luggage": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "briefcase": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "kite": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "boomerang": {"primary": "RESTMÜLL", "material": "plastic", "recyclable": False},
        "picture frame": {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False},
        "mirror": {"primary": "RESTMÜLL", "material": "glass", "recyclable": False, "note": "Spiegel/Spiegelglas"},
        "door": {"primary": "RESTMÜLL", "material": "wood", "recyclable": False, "special": "Sperrmüll"},
        "window": {"primary": "RESTMÜLL", "material": "glass", "recyclable": False, "special": "Sperrmüll"},
        "scissors": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        "knife": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        "tool": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        "hammer": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        "screwdriver": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        "wrench": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        "nail": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        "screw": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        "bolt": {"primary": "RESTMÜLL", "material": "metal", "recyclable": False},
        
        # Spezial: Luftballons
        "luftballon": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False, "note": "Luftballon → Restmüll"},
        "balloon": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False, "note": "Ballon → Restmüll"},
        "balloons": {"primary": "RESTMÜLL", "material": "rubber", "recyclable": False},
    }

    # Elektronische Geräte die typisch Batterien/Akkus haben
    BATTERY_DEVICES = {
        "cell phone", "laptop", "mouse", "remote", "keyboard", "clock",
        "camera", "hair drier", "toothbrush"
    }

    ELECTRONIC_DEVICE_KEYWORDS = {
        "electronic", "phone", "smartphone", "cell", "laptop", "notebook",
        "tablet", "watch", "smartwatch", "clock", "remote", "keyboard",
        "mouse", "camera", "tv", "monitor", "charger", "adapter", "power bank",
        "headphone", "earbud", "speaker", "console", "controller", "toothbrush",
        "razor", "vacuum", "drone", "router", "modem"
    }

    HEURISTIC_GROUPS = {
        "organic": {
            "banana", "apple", "orange", "broccoli", "carrot", "sandwich", "pizza", "donut", "cake", "hot dog"
        },
        "paper": {
            "book", "newspaper", "cardboard", "paper", "paper towel", "kitchen roll",
            "toilet paper", "tissue", "napkin", "handkerchief"
        },
        "plastic": {
            "bottle", "cup", "bowl", "toothbrush", "tooth brush", "frisbee"
        },
        "glass": {
            "wine glass", "glass", "vase"
        },
        "electronic": {
            "cell phone", "laptop", "mouse", "remote", "keyboard", "tv", "clock", "hair drier", "toaster", "microwave"
        },
        "bulky": {
            "chair", "couch", "bed", "dining table", "bench", "refrigerator", "oven", "sink", "toilet"
        }
    }

    TOKEN_MATERIAL_RULES = {
        "paper": ["paper", "cardboard", "carton", "tissue", "napkin", "toilet paper", "newspaper", "magazine", "book", "envelope", "notebook", "papier", "karton", "serviette", "taschentuch"],
        "plastic": ["plastic", "bottle", "container", "pack", "packaging", "bag", "wrapper", "cup", "bucket", "canister", "kunststoff", "pet", "hdpe"],
        "organic": ["food", "fruit", "vegetable", "banana", "apple", "orange", "broccoli", "carrot", "pizza", "cake", "organic", "bio"],
        "glass": ["glass", "bottle glass", "jar", "vase", "wine glass"],
        "electronic": ["phone", "laptop", "keyboard", "remote", "tv", "monitor", "camera", "mouse", "electronic", "battery", "akku", "batterie"],
        "textile": ["cloth", "textile", "shirt", "pants", "dress", "sock", "shoe", "tie", "jacket", "fabric"],
        "wood": ["wood", "wooden", "bat", "furniture", "chair", "table", "bed"],
        "metal": ["metal", "aluminum", "steel", "iron", "scissors", "tool", "can"]
    }

    HINT_MATERIAL_MAP = {
        "paper_material": "paper",
        "plastic_material": "plastic",
        "packaging_material": "plastic",
        "organic_material": "organic",
        "glass_material": "glass",
        "electronic_waste": "electronic",
        "contains_battery": "electronic",
        "metal_material": "metal",
        "textile_material": "textile",
        "wood_material": "wood",
    }

    # ===== DETAILLIERTE MATERIAL-DATENBANK =====
    # Umfangreiche Informationen über Materialien für intelligente Analyse
    MATERIAL_DATABASE = {
        "plastic": {
            "bin": "PLASTIK",
            "types": {
                "PET": {"recyclable": True, "symbol": "♻️ 1", "examples": "Getränkeflaschen, Behälter"},
                "HDPE": {"recyclable": True, "symbol": "♻️ 2", "examples": "Milchflaschen, Behälter"},
                "PVC": {"recyclable": False, "symbol": "♻️ 3", "examples": "Rohre, alte Fenster"},
                "LDPE": {"recyclable": True, "symbol": "♻️ 4", "examples": "Folien, Tüten"},
                "PP": {"recyclable": True, "symbol": "♻️ 5", "examples": "Behälter, Deckel"},
                "PS": {"recyclable": False, "symbol": "♻️ 6", "examples": "Styropor, Behälter"},
                "Other": {"recyclable": False, "symbol": "♻️ 7", "examples": "Mehrschicht-Kunststoff"},
            },
            "contamination_tolerance": "low",
            "moisture_sensitivity": "low",
            "max_acceptable_contamination": 0.6,
            "special_rules": ["Zu stark verschmutzt → Restmüll", "Lebensmittelreste entfernen"],
        },
        "paper": {
            "bin": "PAPIER",
            "subtypes": ["cardboard", "newspaper", "office_paper", "tissue"],
            "contamination_tolerance": "low",
            "moisture_sensitivity": "very_high",
            "max_acceptable_contamination": 0.4,
            "moisture_threshold": 0.3,
            "special_rules": ["Nass/dreckig → Restmüll", "Fette/Öle → Restmüll", "Beschichtet → Restmüll"],
            "examples": ["Zeitungen", "Kartons", "Schreibpapier"],
        },
        "organic": {
            "bin": "BIOMÜLL",
            "subtypes": ["food_waste", "plant_matter", "animal_waste"],
            "contamination_tolerance": "medium",
            "moisture_sensitivity": "low",
            "max_acceptable_contamination": 0.8,
            "special_rules": ["Verpackung entfernen", "Fleisch OK", "Knochen OK", "Essensöl OK"],
            "decomposition_time": "4-8 weeks",
            "examples": ["Essensreste", "Obst/Gemüse", "Gartenschnitt"],
        },
        "glass": {
            "bin": "RESTMÜLL (Altglascontainer)",
            "types": ["clear", "brown", "green"],
            "contamination_tolerance": "medium",
            "moisture_sensitivity": "none",
            "max_acceptable_contamination": 0.7,
            "special_rules": ["→ Altglascontainer", "Nicht in Haustonne!", "Farben trennen"],
            "recycling_note": "100% recyclebar, unbegrenzter Zyklus",
            "examples": ["Bierflaschen", "Gläser", "Vasen"],
        },
        "metal": {
            "bin": "PLASTIK (Wertstoff)",
            "types": {
                "aluminum": {"recyclable": True, "examples": "Alufolie, Dosen"},
                "steel": {"recyclable": True, "examples": "Dosen, Behälter"},
                "copper": {"recyclable": True, "examples": "Drähte, Rohre"},
            },
            "contamination_tolerance": "low",
            "moisture_sensitivity": "low",
            "special_rules": ["Alufolie kann gereinigt werden", "Metall kann verformt sein"],
            "examples": ["Alufolie", "Dosen", "Verpackungen"],
        },
        "electronic": {
            "bin": "RESTMÜLL (Elektroschrott/Wertstoffhof)",
            "contains": ["copper", "gold", "rare_earth", "toxic_substances"],
            "contamination_tolerance": "none",
            "moisture_sensitivity": "very_high",
            "battery_risk": "high",
            "special_rules": ["🔋 BATTERIE/AKKU-WARNUNG", "Separat zu Wertstoffhof", "Nicht in Hausmüll", "Daten löschen"],
            "hazardous_materials": ["Quecksilber", "Blei", "Kadmium"],
            "examples": ["Telefone", "Computer", "Fernbedienungen"],
        },
        "textile": {
            "bin": "RESTMÜLL (Altkleider-Container)",
            "condition_matters": True,
            "contamination_tolerance": "low",
            "moisture_sensitivity": "medium",
            "special_rules": ["Saubere Kleidung in Altkleider-Container", "Zerrissene = Restmüll"],
            "examples": ["Kleidung", "Schuhe", "Textilien"],
        },
        "wood": {
            "bin": "RESTMÜLL (Sperrmüll)",
            "subtypes": ["treated", "untreated"],
            "contamination_tolerance": "low",
            "moisture_sensitivity": "medium",
            "special_rules": ["Behandelt (lackiert) = Sperrmüll", "Kompost-würdig → Grünschnitt"],
            "examples": ["Möbel", "Bretter", "Holzwerkstoff"],
        },
    }

    # ===== COMPOUND-MATERIALIEN (Mehrschicht) =====
    # Objekte die aus mehreren Materialien bestehen
    COMPOUND_MATERIALS = {
        "tetrapak": {
            "materials": ["paper", "plastic", "aluminum"],
            "composition": "75% Papier, 20% Kunststoff, 5% Aluminium",
            "recyclable": False,
            "note": "Nicht in normales Papier-Recycling",
            "correct_disposal": "Restmüll oder spezielle Tetrapak-Sammelstellen",
        },
        "laminated_paper": {
            "materials": ["paper", "plastic"],
            "composition": "Papier mit Kunststoff-Beschichtung",
            "recyclable": False,
            "note": "Kann nicht getrennt werden",
            "correct_disposal": "Restmüll",
        },
        "chipbag": {
            "materials": ["plastic", "aluminum"],
            "composition": "Kunststoff mit Aluminiumschicht",
            "recyclable": False,
            "note": "Auch wenn äußerlich metallic wirkt",
            "correct_disposal": "Restmüll",
        },
        "yogurt_container": {
            "materials": ["plastic", "paper"],
            "composition": "Kunststoff-Deckel + Papp-Becher",
            "recyclable": True,
            "note": "Trennung kann helfen, aber Wertstoff akzeptiert gemischt",
            "correct_disposal": "Wertstoff/Gelbe Tonne",
        },
    }

    # ===== SPECIAL OBJECT KNOWLEDGE =====
    # Spezialwissen für knifflige Objekte
    SPECIAL_KNOWLEDGE = {
        "serviette": {
            "material": "paper",
            "key_issue": "Meist ölig/verschmutzt",
            "classification": "BIOMÜLL",
            "reasoning": "Nicht sauberes Papier, daher zu Bio",
        },
        "pferdepenal": {
            "material": "organic",
            "key_issue": "Tierkot",
            "classification": "BIOMÜLL",
            "reasoning": "Organisches Material, kompostierbar",
        },
        "luftballon": {
            "material": "rubber",
            "key_issue": "Nicht abbaubar",
            "classification": "RESTMÜLL",
            "reasoning": "Kunststoff/Gummi, nicht recyclebar",
        },
        "receipt": {
            "material": "paper",
            "key_issue": "Thermopapier mit Chemikalien",
            "classification": "RESTMÜLL",
            "reasoning": "Chemikalien machen Recycling unmöglich",
        },
        "styrofoam": {
            "material": "plastic",
            "key_issue": "PS-Kunststoff, schwer recyclebar",
            "classification": "RESTMÜLL",
            "reasoning": "Extrem voluminös, kaum Wert im Recycling",
        },
    }

    def __init__(self):
        self.config = get_config()
        self.dynamic_mapping = {}

    def classify_waste(self, class_name: str, confidence: float,
                       object_condition: Optional[Dict] = None,
                       image_region: Optional[np.ndarray] = None,
                       learning_context: Optional[Dict] = None,
                       knowledge_hints: Optional[List[str]] = None,
                       adaptive_policy: Optional[Dict] = None,
                       prior_knowledge: Optional[Dict] = None) -> Dict:
        """
        Klassifiziert Müll in richtige Tonne

        Args:
            class_name: YOLOX erkannte Klasse
            confidence: Erkennungs-Confidence
            object_condition: Zustandsanalyse (Dreck, Nässe, etc.)
            image_region: Bildausschnitt für Material-Analyse

        Returns:
            Dict mit: bin, material, reasoning, warnings, special_instructions
        """
        normalized_name = self._normalize_class_name(class_name)
        knowledge_hints = knowledge_hints or []

        # Standard Mapping + Heuristic Fallback für breitere Klassenabdeckung
        mapping_source = "static"
        mapping = self.WASTE_MAPPING.get(normalized_name)
        if mapping is None:
            mapping_source = "dynamic_cache"
            mapping = self.dynamic_mapping.get(normalized_name)
        if mapping is None:
            mapping_source = "name_hint_or_heuristic"
            mapping = self._mapping_from_name_and_hints(normalized_name, knowledge_hints)
            if mapping is None:
                mapping_source = "heuristic"
                mapping = self._heuristic_mapping(normalized_name)
            if mapping is not None:
                self.dynamic_mapping[normalized_name] = mapping
        if mapping is None:
            return self._unknown_object(normalized_name)
        primary_bin = mapping["primary"]
        material = mapping["material"]

        # Analyse Zustand für Entscheidung
        reasoning = []
        warnings = []
        final_bin = primary_bin
        knowledge_hints = knowledge_hints or []

        # 1. Basis-Entscheidung
        reasoning.append(f"Objekt '{normalized_name}' ist primär: {primary_bin}")

        # 1a. Persistiertes Objektwissen kann unsichere Zuordnungen stabilisieren
        if prior_knowledge:
            prior_conf = float(prior_knowledge.get("confidence", 0.0))
            prior_material = str(prior_knowledge.get("inferred_material", "")).strip().lower()
            prior_bin = str(prior_knowledge.get("inferred_bin", "")).strip().upper()

            if prior_conf >= 0.80:
                if material == "unknown" and prior_material and prior_material != "unknown":
                    material = prior_material
                    reasoning.append("Lernwissen: Material aus Historie übernommen")

                unstable_notes = {"heuristic", "heuristic_fallback", "dynamic_token", "hint_based"}
                if prior_bin in self.BINS and str(mapping.get("note", "")) in unstable_notes:
                    primary_bin = prior_bin
                    final_bin = primary_bin
                    reasoning.append("Lernwissen: Zieltonne aus historischer Evidenz übernommen")

        likely_battery_device = self._is_likely_battery_device(normalized_name, knowledge_hints)

        # 1b. Internetwissen als zusätzlicher Sicherheitsfaktor
        if "contains_battery" in knowledge_hints and material != "electronic":
            warnings.append("Internet-Hinweis: Möglicherweise Akku/Batterie enthalten - manuell prüfen")
            reasoning.append("Web-Wissen deutet auf Akku/Batterie hin")

        # 2. Material-spezifische Regeln
        if material == "plastic":
            reasoning.append("Material: Kunststoff → Gelbe Tonne")
            if object_condition:
                # Verschmutztes Plastik?
                if self._is_heavily_contaminated(object_condition):
                    final_bin = "RESTMÜLL"
                    reasoning.append("⚠️ ÄNDERUNG: Stark verschmutzt → Restmüll")
                    warnings.append("Zu dreckig für Recycling")

        elif material == "paper":
            reasoning.append("Material: Papier/Karton → Blaue Tonne")
            if object_condition:
                # Nasses oder verschmutztes Papier?
                if self._is_wet_or_dirty(object_condition):
                    final_bin = "RESTMÜLL"
                    reasoning.append("⚠️ ÄNDERUNG: Nass/verschmutzt → Restmüll")
                    warnings.append("Nasses Papier nicht recyclebar")

        elif material == "organic":
            reasoning.append("Material: Organisch → Biotonne")
            if object_condition:
                # Verpackung noch dran?
                if image_region is not None:
                    has_packaging = self._detect_packaging(image_region)
                    if has_packaging:
                        warnings.append("Verpackung entfernen vor Biotonne!")

        elif material == "glass":
            reasoning.append("Material: Glas → Altglascontainer (nicht Haustonne!)")
            warnings.append("Glas gehört in Altglascontainer, nicht in Restmüll")
            final_bin = "RESTMÜLL"  # Für Haustonne = Restmüll, aber mit Hinweis

        elif material == "electronic":
            reasoning.append("Material: Elektronik → Sondermüll")
            warnings.append("Elektroschrott nicht in Hausmüll!")

            # Nutzerwunsch: bei elektronischen Geräten IMMER klarer Akku/Batterie-Hinweis.
            warnings.append("Hinweis: Elektronisches Gerät könnte Akku/Batterien enthalten - bitte prüfen")

            # Batteriewarnung?
            if mapping.get("battery_warning", False):
                warnings.append("⚠️⚠️ BATTERIE-WARNUNG: Bitte prüfen ob Batterien/Akkus enthalten sind!")
                warnings.append("→ Batterien separat entsorgen (Sammelstelle)")
                reasoning.append("🔋 Batterie-Check erforderlich")

        # 2c. Sicherheitsnetz: Auch bei unsicherem Material eine Batterie-Warnung ausgeben,
        # falls Name/Hints klar auf potenzielles Akku-Gerät deuten.
        if likely_battery_device and not any("könnte Akku/Batterien enthalten" in w for w in warnings):
            warnings.append("Hinweis: Elektronisches Gerät könnte Akku/Batterien enthalten - bitte prüfen")
        if likely_battery_device and not any("Batterien separat entsorgen" in w for w in warnings):
            warnings.append("→ Batterien separat entsorgen (Sammelstelle)")

        # 2b. Web-Wissen kann Sonderfall markieren
        if "hazardous_hint" in knowledge_hints:
            warnings.append("Gefahrenhinweis aus Web-Wissen: bitte Sonderentsorgung prüfen")
            reasoning.append("Web-Wissen: potenziell gefährlicher Stoff")

        # 3. Spezielle Anweisungen
        special = mapping.get("special")
        if special:
            warnings.append(f"Spezialentsorgung: {special}")

        # 4. Recycling-Status
        recyclable = mapping.get("recyclable", False)

        # 5. Qualitätsbewertung und Review-Entscheidung
        decision_quality = self._compute_decision_quality(
            model_confidence=confidence,
            warnings=warnings,
            learning_context=learning_context
        )

        policy_min_quality = self.config.min_decision_quality_for_autosort
        policy_min_confidence = self.config.min_confidence_for_autosort
        risky_classes = []
        if adaptive_policy:
            policy_min_quality = max(policy_min_quality, float(adaptive_policy.get("min_quality", policy_min_quality)))
            policy_min_confidence = max(policy_min_confidence, float(adaptive_policy.get("min_confidence", policy_min_confidence)))
            risky_classes = adaptive_policy.get("force_manual_for_risky_classes", []) or []

        review_reasons = []
        if decision_quality < 0.6:
            review_reasons.append("low_decision_quality")
        if learning_context and learning_context.get("requires_manual_review"):
            review_reasons.extend(learning_context.get("reasons", []))
        if any("BATTERIE" in w or "Akku" in w or "akku" in w for w in warnings):
            review_reasons.append("battery_check_required")
        if "Unbekanntes Objekt" in " ".join(reasoning):
            review_reasons.append("unknown_object")
        if normalized_name in risky_classes:
            review_reasons.append("risky_class_manual_review")
        if likely_battery_device:
            review_reasons.append("battery_check_required")

        requires_manual_review = len(set(review_reasons)) > 0

        # Hard Safety Mode: unsichere Fälle niemals automatisch entsorgen
        action = "AUTO_SORT"
        recommended_bin = final_bin
        safe_fallback_bin = "RESTMÜLL"

        if self.config.hard_safety_mode:
            if (
                requires_manual_review
                or decision_quality < policy_min_quality
                or confidence < policy_min_confidence
            ):
                action = "MANUAL_CHECK_REQUIRED"
                recommended_bin = None

            if self.config.strict_battery_policy and any(
                ("BATTERIE" in w) or ("Akku" in w) or ("akku" in w) for w in warnings
            ):
                action = "MANUAL_CHECK_REQUIRED"
                recommended_bin = None
                if "battery_check_required" not in review_reasons:
                    review_reasons.append("battery_check_required")
                requires_manual_review = True

        # Ultra Strict: Elektronik und kritische Klassen nie blind auto-sortieren
        if self.config.ultra_strict_mode:
            if material in {"electronic", "unknown"}:
                action = "MANUAL_CHECK_REQUIRED"
                recommended_bin = None
                requires_manual_review = True
                if material == "electronic" and "electronic_manual_confirmation" not in review_reasons:
                    review_reasons.append("electronic_manual_confirmation")
                if material == "unknown" and "unknown_object" not in review_reasons:
                    review_reasons.append("unknown_object")

            if likely_battery_device:
                action = "MANUAL_CHECK_REQUIRED"
                recommended_bin = None
                requires_manual_review = True
                if "battery_check_required" not in review_reasons:
                    review_reasons.append("battery_check_required")

        verification = self._verify_and_refine_sorting(
            class_name=normalized_name,
            material=material,
            final_bin=final_bin,
            warnings=warnings,
            review_reasons=review_reasons,
            action=action,
            recommended_bin=recommended_bin,
            safe_fallback_bin=safe_fallback_bin,
            confidence=confidence,
            knowledge_hints=knowledge_hints,
        )

        final_bin = verification["final_bin"]
        warnings = verification["warnings"]
        review_reasons = verification["review_reasons"]
        action = verification["action"]
        recommended_bin = verification["recommended_bin"]
        safe_fallback_bin = verification["safe_fallback_bin"]
        requires_manual_review = verification["requires_manual_review"]
        decision_quality = min(decision_quality, verification["quality_cap"])

        return {
            "bin": final_bin,
            "bin_description": self.BINS[final_bin],
            "material": material,
            "recyclable": recyclable,
            "confidence": confidence,
            "decision_quality": decision_quality,
            "reasoning": reasoning,
            "warnings": warnings,
            "special_disposal": special,
            "condition_affected_decision": final_bin != primary_bin,
            "requires_manual_review": requires_manual_review,
            "review_reasons": sorted(list(set(review_reasons))),
            "action": action,
            "recommended_bin": recommended_bin,
            "safe_fallback_bin": safe_fallback_bin,
            "hard_safety_applied": self.config.hard_safety_mode,
            "verification": {
                "consistency_checked": True,
                "corrected": verification["corrected"],
                "issues": verification["issues"],
            },
            "explainability": {
                "normalized_class": normalized_name,
                "mapping_source": mapping_source,
                "mapping_note": str(mapping.get("note", "")),
                "model_confidence": float(confidence),
                "decision_quality": float(decision_quality),
                "knowledge_hints_used": list(knowledge_hints),
                "prior_knowledge_used": bool(prior_knowledge),
                "likely_battery_device": bool(likely_battery_device),
                "reasoning_steps": list(reasoning),
            },
        }

    def _verify_and_refine_sorting(
        self,
        class_name: str,
        material: str,
        final_bin: str,
        warnings: List[str],
        review_reasons: List[str],
        action: str,
        recommended_bin: Optional[str],
        safe_fallback_bin: str,
        confidence: float,
        knowledge_hints: Optional[List[str]] = None,
    ) -> Dict:
        """Second-pass verification for bin/material consistency and safety."""
        issues = []
        corrected = False
        hints = set(knowledge_hints or [])
        likely_battery_device = self._is_likely_battery_device(class_name, list(hints))
        warnings_out = list(warnings)
        reasons_out = list(review_reasons)
        quality_cap = 1.0

        expected_bin_by_material = {
            "paper": "PAPIER",
            "plastic": "PLASTIK",
            "organic": "BIOMÜLL",
            "electronic": "RESTMÜLL",
            "glass": "RESTMÜLL",
            "metal": "RESTMÜLL",
            "textile": "RESTMÜLL",
            "wood": "RESTMÜLL",
            "unknown": "RESTMÜLL",
        }

        expected_bin = expected_bin_by_material.get(material, "RESTMÜLL")
        contamination_override_active = any(
            marker in str(w)
            for w in warnings_out
            for marker in (
                "Zu dreckig für Recycling",
                "Nasses Papier nicht recyclebar",
                "Verpackung entfernen vor Biotonne",
            )
        )

        if (
            final_bin != expected_bin
            and material in {"paper", "plastic", "organic"}
            and not contamination_override_active
        ):
            issues.append(f"material_bin_mismatch:{material}:{final_bin}->{expected_bin}")
            final_bin = expected_bin
            corrected = True

        if material == "electronic" and "contains_battery" in hints:
            if not any(("BATTERIE" in w) or ("Akku" in w) or ("akku" in w) for w in warnings_out):
                warnings_out.append("⚠️ BATTERIE-Hinweis: Onlinewissen bestätigt Akku/Batterie-Risiko")
            if "battery_check_required" not in reasons_out:
                reasons_out.append("battery_check_required")
            action = "MANUAL_CHECK_REQUIRED"
            recommended_bin = None
            quality_cap = min(quality_cap, 0.72)

        if likely_battery_device:
            if not any("könnte Akku/Batterien enthalten" in w for w in warnings_out):
                warnings_out.append("Hinweis: Elektronisches Gerät könnte Akku/Batterien enthalten - bitte prüfen")
            if "battery_check_required" not in reasons_out:
                reasons_out.append("battery_check_required")
            action = "MANUAL_CHECK_REQUIRED"
            recommended_bin = None
            quality_cap = min(quality_cap, 0.72)

        if confidence < 0.62:
            if "low_confidence_postcheck" not in reasons_out:
                reasons_out.append("low_confidence_postcheck")
            action = "MANUAL_CHECK_REQUIRED"
            recommended_bin = None
            quality_cap = min(quality_cap, 0.68)

        if material == "unknown":
            if "unknown_object" not in reasons_out:
                reasons_out.append("unknown_object")
            action = "MANUAL_CHECK_REQUIRED"
            recommended_bin = None
            quality_cap = min(quality_cap, 0.60)

        requires_manual_review = len(set(reasons_out)) > 0
        if action == "MANUAL_CHECK_REQUIRED" and recommended_bin is not None:
            recommended_bin = None
            corrected = True
            issues.append("action_recommended_bin_conflict")

        return {
            "final_bin": final_bin,
            "warnings": warnings_out,
            "review_reasons": reasons_out,
            "action": action,
            "recommended_bin": recommended_bin,
            "safe_fallback_bin": safe_fallback_bin,
            "requires_manual_review": requires_manual_review,
            "corrected": corrected,
            "issues": issues,
            "quality_cap": quality_cap,
        }

    def _is_likely_battery_device(self, class_name: str, knowledge_hints: Optional[List[str]] = None) -> bool:
        """Heuristic battery/electronic risk detection for robust user warnings."""
        name = str(class_name or "").strip().lower()
        hints = set(knowledge_hints or [])

        if "contains_battery" in hints:
            return True
        if name in self.BATTERY_DEVICES:
            return True
        if any(token in name for token in self.ELECTRONIC_DEVICE_KEYWORDS):
            return True
        return False

    def _normalize_class_name(self, class_name: str) -> str:
        """Normalisiert Modellklassen für robustes Mapping."""
        name = str(class_name or "").strip().lower().replace("_", " ").replace("-", " ")
        name = " ".join(name.split())
        aliases = {
            "cellphone": "cell phone",
            "mobile phone": "cell phone",
            "smartphone": "cell phone",
            "tvmonitor": "tv",
            "television": "tv",
            "books": "book",
            "bottles": "bottle",
            "cups": "cup",
            "cans": "can",
            "paper towels": "paper towel",
            "kitchen towels": "paper towel",
            "kitchen towel": "paper towel",
            "kitchen roll towel": "paper towel",
            "paper roll": "kitchen roll",
            "kitchen tissue": "tissue",
            "facial tissue": "tissue",
            "kleenex": "tissue",
            "napkins": "napkin",
            "handkerchiefs": "handkerchief",
            "taschentuch": "tissue",
            "taschentücher": "tissue",
            "küchenrolle": "kitchen roll",
            "kuechenrolle": "kitchen roll",
            "küchenpapier": "paper towel",
            "kuechenpapier": "paper towel",
            "toilettenpapier": "toilet paper",
            # WICHTIG: Serviette → BIOMÜLL, nicht Papier!
            "serviette": "serviette",
            "servietten": "serviette",
        }
        if name in aliases:
            return aliases[name]
        if name.endswith("es") and len(name) > 4:
            singular = name[:-2]
            if singular in self.WASTE_MAPPING:
                return singular
        if name.endswith("s") and len(name) > 3:
            singular = name[:-1]
            if singular in self.WASTE_MAPPING:
                return singular
        return name

    def _heuristic_mapping(self, class_name: str) -> Optional[Dict]:
        """Heuristische Zuordnung für Klassen, die nicht explizit im Mapping stehen."""
        name = str(class_name or "").strip().lower()
        if not name:
            return None

        # SPEZIAL-FÄLLE ZUERST prüfen (vor generischen Rules!)
        # Serviette → BIOMÜLL (nicht Papier, weil meist ölig/verschmutzt)
        if any(tok in name for tok in ["serviette", "napkin"]):
            return {"primary": "BIOMÜLL", "material": "paper", "recyclable": False, "note": "Papierserviette meist ölig → Bio"}

        if name in self.HEURISTIC_GROUPS["organic"]:
            return {"primary": "BIOMÜLL", "material": "organic", "recyclable": False, "note": "heuristic"}

        if name in self.HEURISTIC_GROUPS["paper"] or any(tok in name for tok in [
            "paper", "cardboard", "carton", "tissue", "toilet paper",
            "kitchen roll", "kitchen towel", "taschentuch", "papier"
        ]):
            return {"primary": "PAPIER", "material": "paper", "recyclable": True, "note": "heuristic"}

        if name in self.HEURISTIC_GROUPS["plastic"] or any(tok in name for tok in ["plastic", "container", "packaging"]):
            return {"primary": "PLASTIK", "material": "plastic", "recyclable": True, "note": "heuristic"}

        if name in self.HEURISTIC_GROUPS["glass"] or "glass" in name:
            return {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "Altglascontainer"}

        if name in self.HEURISTIC_GROUPS["electronic"] or any(tok in name for tok in ["phone", "laptop", "keyboard", "remote", "electronic", "battery", "akku"]):
            return {
                "primary": "RESTMÜLL",
                "material": "electronic",
                "recyclable": False,
                "battery_warning": True,
                "special": "Elektroschrott",
                "note": "heuristic"
            }

        if name in self.HEURISTIC_GROUPS["bulky"]:
            return {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "special": "Sperrmüll", "note": "heuristic"}

        if any(tok in name for tok in ["bag", "backpack", "umbrella", "shoe", "clothes", "textile", "toy"]):
            return {"primary": "RESTMÜLL", "material": "mixed", "recyclable": False, "note": "heuristic"}

        # fallback: konservativ
        return {"primary": "RESTMÜLL", "material": "unknown", "recyclable": False, "note": "heuristic_fallback"}

    def _mapping_from_name_and_hints(self, class_name: str, knowledge_hints: Optional[List[str]] = None) -> Optional[Dict]:
        """Leitet Mapping dynamisch aus Name + Web-Hinweisen ab."""
        name = str(class_name or "").strip().lower()
        if not name:
            return None

        hints = set(knowledge_hints or [])

        if "paper_material" in hints:
            return {"primary": "PAPIER", "material": "paper", "recyclable": True, "note": "hint_based"}
        if "plastic_material" in hints or "packaging_material" in hints:
            return {"primary": "PLASTIK", "material": "plastic", "recyclable": True, "note": "hint_based"}
        if "organic_material" in hints:
            return {"primary": "BIOMÜLL", "material": "organic", "recyclable": False, "note": "hint_based"}
        if "glass_material" in hints:
            return {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "hint_based"}
        if "electronic_waste" in hints or "contains_battery" in hints:
            return {
                "primary": "RESTMÜLL",
                "material": "electronic",
                "recyclable": False,
                "battery_warning": True,
                "special": "Elektroschrott",
                "note": "hint_based"
            }
        if "metal_material" in hints:
            return {"primary": "RESTMÜLL", "material": "metal", "recyclable": True, "note": "hint_based"}
        if "textile_material" in hints:
            return {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "hint_based"}
        if "wood_material" in hints:
            return {"primary": "RESTMÜLL", "material": "wood", "recyclable": False, "special": "Sperrmüll", "note": "hint_based"}

        matched_material = None
        matched_count = 0
        for material, tokens in self.TOKEN_MATERIAL_RULES.items():
            count = sum(1 for token in tokens if token in name)
            if count > matched_count:
                matched_material = material
                matched_count = count

        if not matched_material:
            return None

        if matched_material == "paper":
            return {"primary": "PAPIER", "material": "paper", "recyclable": True, "note": "dynamic_token"}
        if matched_material == "plastic":
            return {"primary": "PLASTIK", "material": "plastic", "recyclable": True, "note": "dynamic_token"}
        if matched_material == "organic":
            return {"primary": "BIOMÜLL", "material": "organic", "recyclable": False, "note": "dynamic_token"}
        if matched_material == "glass":
            return {"primary": "RESTMÜLL", "material": "glass", "recyclable": True, "note": "dynamic_token"}
        if matched_material == "electronic":
            return {
                "primary": "RESTMÜLL",
                "material": "electronic",
                "recyclable": False,
                "battery_warning": True,
                "special": "Elektroschrott",
                "note": "dynamic_token"
            }
        if matched_material == "textile":
            return {"primary": "RESTMÜLL", "material": "textile", "recyclable": False, "note": "dynamic_token"}
        if matched_material == "wood":
            return {"primary": "RESTMÜLL", "material": "wood", "recyclable": False, "special": "Sperrmüll", "note": "dynamic_token"}
        if matched_material == "metal":
            return {"primary": "RESTMÜLL", "material": "metal", "recyclable": True, "note": "dynamic_token"}

        return None

    def get_class_profile(self, class_name: str, knowledge_hints: Optional[List[str]] = None) -> Dict:
        """Liefert ein standardisiertes Wissensprofil für eine Objektklasse."""
        normalized = self._normalize_class_name(class_name)
        hints = knowledge_hints or []

        mapping = self.WASTE_MAPPING.get(normalized)
        source = "static"
        if mapping is None:
            mapping = self.dynamic_mapping.get(normalized)
            source = "dynamic"
        if mapping is None:
            mapping = self._mapping_from_name_and_hints(normalized, hints)
            source = "hint_or_token"
        if mapping is None:
            mapping = self._heuristic_mapping(normalized)
            source = "heuristic"

        if mapping is None:
            return {
                "class_name": normalized,
                "material": "unknown",
                "bin": "RESTMÜLL",
                "recyclable": False,
                "source": "fallback_unknown",
            }

        return {
            "class_name": normalized,
            "material": mapping.get("material", "unknown"),
            "bin": mapping.get("primary", "RESTMÜLL"),
            "recyclable": bool(mapping.get("recyclable", False)),
            "source": source,
        }

    def bootstrap_known_classes(self, class_names: List[str]):
        """Erzeuge für bekannte Klassen ein dynamisches Grundwissen."""
        if not class_names:
            return
        for class_name in class_names:
            normalized = self._normalize_class_name(class_name)
            if not normalized:
                continue
            if normalized in self.WASTE_MAPPING or normalized in self.dynamic_mapping:
                continue
            mapping = self._mapping_from_name_and_hints(normalized, [])
            if mapping is None:
                mapping = self._heuristic_mapping(normalized)
            if mapping is not None:
                self.dynamic_mapping[normalized] = mapping

    def _unknown_object(self, class_name: str) -> Dict:
        """Standard für unbekannte Objekte"""
        return {
            "bin": "RESTMÜLL",
            "bin_description": self.BINS["RESTMÜLL"],
            "material": "unknown",
            "recyclable": False,
            "confidence": 0.5,
            "decision_quality": 0.2,
            "reasoning": [f"Unbekanntes Objekt '{class_name}' → Sicher: Restmüll"],
            "warnings": ["Unbekanntes Objekt - bitte manuell prüfen"],
            "special_disposal": None,
            "condition_affected_decision": False,
            "requires_manual_review": True,
            "review_reasons": ["unknown_object"],
            "action": "MANUAL_CHECK_REQUIRED",
            "recommended_bin": None,
            "safe_fallback_bin": "RESTMÜLL",
            "hard_safety_applied": self.config.hard_safety_mode
        }

    def _compute_decision_quality(self, model_confidence: float, warnings: List[str], learning_context: Optional[Dict]) -> float:
        """Berechnet Qualität der Trennungsentscheidung zwischen 0 und 1."""
        quality = max(0.0, min(1.0, float(model_confidence)))

        warning_penalty = 0.08 * len(warnings)
        quality -= warning_penalty

        if learning_context:
            reliability = learning_context.get("reliability", {}).get("reliability", 0.5)
            quality = (quality * 0.7) + (reliability * 0.3)

            confusion_level = learning_context.get("confusion", {}).get("risk_level", "unknown")
            if confusion_level == "high":
                quality -= 0.15
            elif confusion_level == "medium":
                quality -= 0.08

        return max(0.0, min(1.0, quality))

    def _is_heavily_contaminated(self, condition: Dict) -> bool:
        """Prüft ob Objekt zu verschmutzt für Recycling ist"""
        if not condition or "details" not in condition:
            return False

        details = condition["details"]

        # Stark verschmutzt wenn:
        # - Dirt severity > 0.6
        # - Mehrere Verschmutzungs-Arten
        dirt_count = 0
        max_severity = 0.0

        for cond in details:
            severity = cond.get("severity", 0.0)
            max_severity = max(max_severity, severity)
            if cond["type"] in ["dirt", "discoloration"]:
                dirt_count += 1

        return max_severity > 0.6 or dirt_count >= 2

    def _is_wet_or_dirty(self, condition: Dict) -> bool:
        """Prüft ob Papier nass oder verschmutzt ist"""
        if not condition or "details" not in condition:
            return False

        details = condition["details"]

        for cond in details:
            if cond["type"] in ["wetness", "dirt"]:
                if cond.get("severity", 0.0) > 0.4:
                    return True

        return False

    def _detect_packaging(self, image_region: np.ndarray) -> bool:
        """
        Erkennt ob noch Verpackung am Bio-Müll ist
        (Einfache Heuristik: Suche nach harten Kanten = Plastik/Karton)
        """
        if image_region is None or image_region.size == 0:
            return False

        # Konvertiere zu Graustufen
        if len(image_region.shape) == 3:
            gray = cv2.cvtColor(image_region, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_region

        # Canny Edge Detection
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Viele harte Kanten = wahrscheinlich Verpackung
        return edge_density > 0.15

    def classify_by_name_only(self, class_name: str) -> Dict:
        """
        Einfache Klassifizierung für Nutzer-Korrektur (nur Name, keine Confidence/Image-Region)
        Gibt direkt Bin + Vorschlag zurück
        
        Args:
            class_name: Objektname vom Nutzer eingegeben (z.B. "Serviette")
            
        Returns:
            Dict mit: bin, bin_description, material, reasoning, warnings
        """
        normalized_name = self._normalize_class_name(class_name)
        
        # Versuche Mapping zu finden
        mapping = self.WASTE_MAPPING.get(normalized_name)
        source = "static"
        
        if mapping is None:
            mapping = self.dynamic_mapping.get(normalized_name)
            source = "dynamic"
        
        if mapping is None:
            mapping = self._mapping_from_name_and_hints(normalized_name, [])
            source = "hint"
        
        if mapping is None:
            mapping = self._heuristic_mapping(normalized_name)
            source = "heuristic"
        
        if mapping is None:
            mapping = {"primary": "RESTMÜLL", "material": "unknown", "recyclable": False}
            source = "fallback"
        
        primary_bin = mapping["primary"]
        material = mapping["material"]
        
        # Warnungen zusammenstellen
        warnings = []
        reasoning = []
        
        reasoning.append(f"'{normalized_name}' → {primary_bin}")
        
        if mapping.get("battery_warning"):
            warnings.append("⚠️ Batterie-/Akku-Warnung möglich!")
            warnings.append("Batterien ggf. separat entsorgen")
        
        if mapping.get("special"):
            warnings.append(f"Spezial: {mapping['special']}")
        
        if source == "fallback" or material == "unknown":
            warnings.append("Objekttyp nicht sicher erkannt - bitte manuell prüfen")
        
        return {
            "bin": primary_bin,
            "bin_description": self.BINS.get(primary_bin, "Unbekannt"),
            "material": material,
            "recyclable": mapping.get("recyclable", False),
            "reasoning": reasoning,
            "warnings": warnings,
            "source": source,
            "normalized_name": normalized_name,
        }

    def get_bin_summary(self) -> Dict:
        """Gibt eine Zusammenfassung aller 4 Tonnen zurück"""
        return {
            "bins": self.BINS,
            "total_classes_mapped": len(self.WASTE_MAPPING),
            "total_dynamic_classes": len(self.dynamic_mapping),
            "materials": ["plastic", "paper", "organic", "glass", "metal", "electronic", "mixed"],
            "battery_warning_classes": list(self.BATTERY_DEVICES)
        }

    # ===== NEUE ANALYSE-METHODEN FÜR MAXIMALE INTELLIGENZ =====

    def analyze_material_detailed(self, material: str) -> Dict:
        """
        Liefert detaillierte Informationen über ein Material
        
        Args:
            material: Material-Typ (z.B. "plastic", "paper", "organic")
            
        Returns:
            Dict mit umfangreichen Material-Infos
        """
        if material not in self.MATERIAL_DATABASE:
            return {
                "found": False,
                "material": material,
                "error": "Material nicht in Datenbank",
            }
        
        db = self.MATERIAL_DATABASE[material]
        return {
            "found": True,
            "material": material,
            "bin": db.get("bin"),
            "subtypes": db.get("subtypes", []),
            "contamination_tolerance": db.get("contamination_tolerance"),
            "moisture_sensitivity": db.get("moisture_sensitivity"),
            "max_acceptable_contamination": db.get("max_acceptable_contamination"),
            "special_rules": db.get("special_rules", []),
            "examples": db.get("examples", []),
            "recycling_note": db.get("recycling_note", ""),
        }

    def analyze_compound_materials(self, object_name: str) -> Optional[Dict]:
        """
        Erkennt Mehrschicht-Materialien (Compound Materials)
        z.B. Tetrapak = Papier + Kunststoff + Aluminium
        
        Args:
            object_name: Name des Objekts
            
        Returns:
            Dict mit Compound-Info oder None
        """
        normalized = self._normalize_class_name(object_name).lower()
        
        for compound_name, compound_info in self.COMPOUND_MATERIALS.items():
            if compound_name in normalized or normalized in compound_name:
                return {
                    "is_compound": True,
                    "compound_type": compound_name,
                    "materials": compound_info.get("materials", []),
                    "composition": compound_info.get("composition"),
                    "recyclable": compound_info.get("recyclable"),
                    "note": compound_info.get("note"),
                    "correct_disposal": compound_info.get("correct_disposal"),
                }
        
        return None

    def get_material_properties(self, material: str) -> Dict:
        """Gibt alle Eigenschaften eines Materials zurück"""
        db = self.MATERIAL_DATABASE.get(material, {})
        return {
            "bin": db.get("bin", "Unbekannt"),
            "contamination_tolerance": db.get("contamination_tolerance", "unknown"),
            "moisture_sensitivity": db.get("moisture_sensitivity", "unknown"),
            "recycling_rate": db.get("recycling_rate", "Unbekannt"),
            "environmental_impact": db.get("environmental_impact", "Unbekannt"),
        }

    def get_disposal_instructions(self, class_name: str, material: str) -> List[str]:
        """
        Gibt detaillierte Entsorgungshinweise für ein Objekt
        
        Args:
            class_name: Objektname
            material: Material-Typ
            
        Returns:
            Liste von Entsorgungshinweisen
        """
        instructions = []
        
        # Spezialwissen?
        normalized = self._normalize_class_name(class_name).lower()
        if normalized in self.SPECIAL_KNOWLEDGE:
            special = self.SPECIAL_KNOWLEDGE[normalized]
            instructions.append(f"⚠️ Spezialfall: {special.get('key_issue', '')}")
            instructions.append(f"   Grund: {special.get('reasoning', '')}")
            return instructions
        
        # Material-spezifische Hinweise
        if material == "plastic":
            instructions.append("✓ Kunststoff-Tipps:")
            instructions.append("  • Gut sichtbar: kleine Öffnungen zum Ausspülen")
            instructions.append("  • Lebensmittelreste vollständig entfernen")
            instructions.append("  • Deckel kann oben bleiben")
            instructions.append("  • Falten ist OK (spart Platz)")
        
        elif material == "paper":
            instructions.append("✓ Papier-Tipps:")
            instructions.append("  • NICHT: nass, ölig, verschmutzt")
            instructions.append("  • Verpackungen vollständig öffnen")
            instructions.append("  • Plastik-Fenster entfernen wenn möglich")
            instructions.append("  • Fasertaschentücher können mitgehen")
        
        elif material == "organic":
            instructions.append("✓ Bio-Müll-Tipps:")
            instructions.append("  • Verpackung entfernen!")
            instructions.append("  • Fleisch/Fisch/Knochen: OK")
            instructions.append("  • Essensöle: OK")
            instructions.append("  • Gartenschnitt/Laub: OK")
        
        elif material == "electronic":
            instructions.append("🔋 ELEKTRONIK-WARNUNG:")
            instructions.append("  ⚠️  BATTERIE/AKKU-WARNUNG!")
            instructions.append("  • Wertstoffhof oder Elektroschrott-Sammelstelle")
            instructions.append("  • NICHT in Hausmüll!")
            instructions.append("  • Batterien separat entfernen wenn möglich")
        
        return instructions

    def generate_detailed_reasoning(self, class_name: str, confidence: float, 
                                   material: str, bin_assignment: str) -> Dict:
        """
        Generiert eine ausführliche Erklärung WARUM etwas in eine bestimmte Tonne gehört
        
        Args:
            class_name: Erkannter Objektname
            confidence: KI-Confidence
            material: Erkanntes Material
            bin_assignment: Zugewiesene Tonne
            
        Returns:
            Dict mit ausführlicher Erklärung
        """
        reasoning_chain = []
        confidence_assessment = "🟢 HOCH" if confidence > 0.8 else "🟡 MITTEL" if confidence > 0.6 else "🔴 NIEDRIG"
        
        reasoning_chain.append({
            "step": 1,
            "title": "Objekt-Erkennung",
            "result": f"'{class_name}' (Confidence: {confidence:.1%} → {confidence_assessment})",
        })
        
        reasoning_chain.append({
            "step": 2,
            "title": "Material-Klassifizierung",
            "result": f"Material erkannt: {material.upper()}",
        })
        
        material_db = self.MATERIAL_DATABASE.get(material, {})
        reasoning_chain.append({
            "step": 3,
            "title": "Material-Eigenschaften",
            "contamination": material_db.get("contamination_tolerance", "unknown"),
            "moisture": material_db.get("moisture_sensitivity", "unknown"),
            "recyclable": material_db.get("special_rules", ["Info nicht vorhanden"]),
        })
        
        reasoning_chain.append({
            "step": 4,
            "title": "Tonne-Zuordnung",
            "result": f"{bin_assignment} → {self.BINS.get(bin_assignment, 'Unbekannt')}",
            "reasoning": f"{material.upper()} → {bin_assignment}",
        })
        
        # Spezialwissen?
        normalized = self._normalize_class_name(class_name).lower()
        if normalized in self.SPECIAL_KNOWLEDGE:
            special = self.SPECIAL_KNOWLEDGE[normalized]
            reasoning_chain.append({
                "step": 5,
                "title": "Spezialfall-Anpassung",
                "issue": special.get("key_issue"),
                "solution": special.get("reasoning"),
            })
        
        return {
            "object_name": class_name,
            "confidence": confidence,
            "confidence_level": confidence_assessment,
            "material": material,
            "final_bin": bin_assignment,
            "reasoning_chain": reasoning_chain,
        }

    def estimate_recyclability_score(self, class_name: str, material: str, 
                                     contamination_level: float = 0.0) -> Dict:
        """
        Schätzt wie recycelbar ein Objekt ist (0-100%)
        
        Args:
            class_name: Objektname
            material: Material
            contamination_level: Verschmutzungsgrad (0-1)
            
        Returns:
            Dict mit Recycling-Score und Erklärung
        """
        # Basis-Score nach Material
        base_scores = {
            "plastic": 60,
            "paper": 85,
            "organic": 100,  # 100% biologisch abbaubar
            "glass": 100,
            "metal": 90,
            "electronic": 45,
            "textile": 70,
            "wood": 75,
        }
        
        score = base_scores.get(material, 20)
        factors = []
        
        # Abzug für Verschmutzung
        contamination_penalty = contamination_level * 50
        score -= contamination_penalty
        if contamination_level > 0:
            factors.append(f"Verschmutzung: -{contamination_penalty:.1f}% ({contamination_level:.0%} Verschmutzung)")
        
        # Spezialwissen Anpassungen
        normalized = self._normalize_class_name(class_name).lower()
        if normalized in self.COMPOUND_MATERIALS:
            compound = self.COMPOUND_MATERIALS[normalized]
            if not compound.get("recyclable"):
                score = 10
                factors.append(f"Compound-Material: Nicht recyclebar")
        
        score = max(0, min(100, score))
        
        return {
            "object": class_name,
            "material": material,
            "recyclability_score": score,
            "score_description": "🟢 Sehr recyclebar" if score > 80 else "🟡 Mäßig recyclebar" if score > 50 else "🔴 Schwer recyclebar",
            "contamination_impact": contamination_level,
            "factors": factors,
        }

    def get_knowledge_summary(self) -> Dict:
        """
        Gibt eine Zusammenfassung aller Wissensdaten zurück
        Zeigt wie umfangreich die Datenbank ist
        """
        return {
            "total_objects_mapped": len(self.WASTE_MAPPING),
            "dynamic_objects_learned": len(self.dynamic_mapping),
            "materials_known": len(self.MATERIAL_DATABASE),
            "material_list": list(self.MATERIAL_DATABASE.keys()),
            "compound_materials_known": len(self.COMPOUND_MATERIALS),
            "special_cases_known": len(self.SPECIAL_KNOWLEDGE),
            "total_battery_warning_devices": len(self.BATTERY_DEVICES),
            "electronic_device_keywords": len(self.ELECTRONIC_DEVICE_KEYWORDS),
            "token_rules": {mat: len(tokens) for mat, tokens in self.TOKEN_MATERIAL_RULES.items()},
        }

    def predict_next_question(self, class_name: str) -> List[str]:
        """
        Vorhersagt welche Fragen der Nutzer möglicherweise hat
        Hilft die KI produktiver zu machen
        
        Args:
            class_name: Objektname
            
        Returns:
            Liste von möglichen Fragen
        """
        normalized = self._normalize_class_name(class_name).lower()
        mapping = self.WASTE_MAPPING.get(normalized, {})
        material = mapping.get("material", "unknown")
        
        questions = []
        
        if "battery_warning" in mapping or material == "electronic":
            questions.append("❓ Hat das Gerät Batterien/Akkus?")
            questions.append("❓ Kann ich die Batterie selbst rausnehmen?")
            questions.append("❓ Wo sammelt man Elektroschrott in meiner Stadt?")
        
        if mapping.get("special"):
            questions.append(f"❓ Was bedeutet: {mapping['special']}?")
        
        if material == "organic":
            questions.append("❓ Kann ich die Verpackung auch in Bio werfen?")
            questions.append("❓ Sind gekochte Essensreste OK?")
        
        if material == "paper":
            questions.append("❓ Funktioniert das auch wenn es nass ist?")
            questions.append("❓ Muss ich die Verpackung waschen?")
        
        if material == "plastic":
            questions.append("❓ Muss ich das ausspülen?")
            questions.append("❓ Kann der Deckel mit rein?")
        
        return questions

    def get_learning_priorities(self) -> List[Dict]:
        """
        Zeigt welche Objekt-Klassen am häufigsten zu Verwechslungen führen
        und wo die KI am meisten von Feedback profitieren würde
        
        Returns:
            Liste von Prioritäten für Lernfokus
        """
        confusion_classes = [
            {
                "class": "Serviette",
                "common_mistake": "→ PAPIER statt BIOMÜLL",
                "why_confused": "Optisch sieht es wie Papier aus",
                "correct_bin": "BIOMÜLL (wegen Öl/Verschmutzung)",
                "priority": "HIGH",
            },
            {
                "class": "Luftballon",
                "common_mistake": "→ PLASTIK statt RESTMÜLL",
                "why_confused": "Sieht nach recycelbarem Kunststoff aus",
                "correct_bin": "RESTMÜLL (Gummi, nicht recyclebar)",
                "priority": "HIGH",
            },
            {
                "class": "Tetrapak",
                "common_mistake": "→ PAPIER statt RESTMÜLL",
                "why_confused": "Sieht nach Papier-Verpackung aus",
                "correct_bin": "RESTMÜLL (Compound-Material)",
                "priority": "HIGH",
            },
            {
                "class": "Pferdepenal",
                "common_mistake": "→ RESTMÜLL statt BIOMÜLL",
                "why_confused": "Sieht nach Kunststoff-Beutel aus",
                "correct_bin": "BIOMÜLL (Organischer Inhalt)",
                "priority": "MEDIUM",
            },
            {
                "class": "Elektronische Geräte",
                "common_mistake": "→ RESTMÜLL statt WERTSTOFFHOF",
                "why_confused": "Nutzer wirft alles in die näcste Tonne",
                "correct_bin": "ELEKTROSCHROTT (nicht zu Hause!)",
                "priority": "CRITICAL (Sicherheit)",
            },
        ]
        return confusion_classes


# Singleton
_classifier = None

def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = WasteClassifier()
    return _classifier
