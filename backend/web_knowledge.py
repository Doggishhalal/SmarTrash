"""
Web Knowledge Fetcher - Holt zusätzliches Wissen über Objekte
==============================================================
Nutzt kostenlose APIs (Wikipedia, Wikidata) für Objekt-Informationen
"""
import json
import time
from typing import Dict, List, Optional

import requests
from safety_config import get_config


class WebKnowledgeFetcher:
    """Holt Wissen über Objekte aus dem Internet (kostenlos)"""

    COCO_OPENIMAGES_LABEL_MAP = {
        "cell phone": ["mobile phone", "smartphone", "telephone", "openimages/mobile phone"],
        "tv": ["television", "monitor", "screen"],
        "wine glass": ["drinking glass", "glass cup"],
        "dining table": ["table", "furniture table"],
        "potted plant": ["plant", "flower pot"],
        "couch": ["sofa", "settee"],
        "book": ["notebook", "paper book"],
        "bottle": ["plastic bottle", "glass bottle", "drink bottle"],
        "cup": ["plastic cup", "paper cup", "coffee cup"],
        "remote": ["remote control", "controller"],
        "keyboard": ["computer keyboard"],
        "mouse": ["computer mouse"],
        "backpack": ["school bag", "rucksack"],
    }

    ONTOLOGY_ALIASES = {
        "battery": ["accumulator", "akku", "batterie", "lithium ion battery"],
        "electronic": ["e-waste", "electrical device", "electronic device"],
        "plastic": ["polyethylene", "polypropylene", "pet", "hdpe", "packaging plastic"],
        "paper": ["cardboard", "carton", "paperboard", "papier", "karton"],
        "organic": ["biowaste", "food waste", "compost", "organics"],
        "glass": ["container glass", "bottle glass", "soda lime glass"],
        "metal": ["aluminum", "aluminium", "steel", "iron", "tinplate"],
        "hazardous": ["toxic", "dangerous", "chemically hazardous"],
        "textile": ["fabric", "cloth", "garment"],
        "wood": ["timber", "wooden material"],
    }

    PUBLIC_KNOWLEDGE_SEEDS = [
        "plastic bottle", "pet bottle", "hdpe bottle", "glass bottle", "aluminum can", "steel can",
        "paper", "newspaper", "cardboard", "magazine", "milk carton", "tetra pak",
        "banana peel", "apple core", "coffee grounds", "tea bag", "eggshell", "food waste",
        "battery", "lithium battery", "phone battery", "charger", "power bank",
        "smartphone", "laptop", "keyboard", "mouse", "headphones", "remote control",
        "light bulb", "led bulb", "fluorescent lamp", "ink cartridge", "paint can", "solvent",
        "styrofoam", "plastic bag", "plastic wrap", "yogurt cup", "chip bag", "foil",
        "textile", "shirt", "jeans", "shoes", "backpack", "umbrella",
        "wood", "wood panel", "furniture", "chair", "table", "broken toy",
        "ceramic", "porcelain", "mirror", "window glass", "vase", "drinking glass",
        # Extra device-heavy and bottle-heavy trusted seeds
        "mobile phone", "cell phone", "iphone", "android phone", "tablet", "smartwatch",
        "wrist watch", "phone charger", "usb cable", "lightning cable", "usb c cable",
        "wireless charger", "charging dock", "adapter", "power adapter", "extension cable",
        "earbuds", "bluetooth earbuds", "headset", "speaker", "bluetooth speaker",
        "camera", "digital camera", "webcam", "router", "modem", "printer",
        "ink bottle", "toner cartridge", "computer monitor", "smart tv", "game controller",
        "aa battery", "aaa battery", "button cell", "coin cell", "battery pack",
        "water bottle", "soda bottle", "juice bottle", "milk bottle", "sports bottle",
        "detergent bottle", "shampoo bottle", "cleaner bottle", "spray bottle", "oil bottle",
        "medicine bottle", "pill bottle", "dropper bottle", "baby bottle", "thermos bottle",
        "jar", "glass jar", "jam jar", "honey jar", "food container",
        "plastic container", "glass container", "metal container", "beverage can", "aerosol can",
        "drink carton", "paper cup", "plastic cup", "coffee cup", "travel mug",
    ]

    ONLINE_SELF_LEARN_PRIORITY_TERMS = [
        "cell phone", "mobile phone", "smartphone", "iphone", "android phone",
        "smartwatch", "watch", "tablet", "phone charger", "battery", "power bank",
        "plastic bottle", "glass bottle", "water bottle", "soda bottle", "jar", "beverage can",
    ]

    TRUSTED_ONLINE_SOURCES = {
        "Wikipedia",
        "DBpedia",
        "OpenFoodFacts",
        "Wikidata",
    }

    LOCAL_CLASS_HINTS = {
        "banana": ["organic_material"],
        "apple": ["organic_material"],
        "orange": ["organic_material"],
        "broccoli": ["organic_material"],
        "carrot": ["organic_material"],
        "sandwich": ["organic_material", "packaging_material"],
        "pizza": ["organic_material", "packaging_material"],
        "cake": ["organic_material"],
        "donut": ["organic_material"],
        "hot dog": ["organic_material", "packaging_material"],
        "bottle": ["plastic_material", "recyclable_hint"],
        "cup": ["plastic_material"],
        "bowl": ["plastic_material"],
        "book": ["paper_material", "recyclable_hint"],
        "newspaper": ["paper_material", "recyclable_hint"],
        "cardboard": ["paper_material", "recyclable_hint"],
        "paper towel": ["paper_material"],
        "kitchen roll": ["paper_material"],
        "toilet paper": ["paper_material"],
        "tissue": ["paper_material"],
        "napkin": ["paper_material"],
        "wine glass": ["glass_material"],
        "vase": ["glass_material"],
        "cell phone": ["electronic_waste", "contains_battery", "hazardous_hint"],
        "laptop": ["electronic_waste", "contains_battery", "hazardous_hint"],
        "keyboard": ["electronic_waste"],
        "mouse": ["electronic_waste"],
        "remote": ["electronic_waste", "contains_battery"],
        "tv": ["electronic_waste"],
        "clock": ["electronic_waste", "contains_battery"],
        "scissors": ["metal_material"],
        "chair": ["wood_material"],
        "dining table": ["wood_material"],
        "bed": ["wood_material", "textile_material"],
        "couch": ["textile_material", "wood_material"],
        "backpack": ["textile_material"],
        "tie": ["textile_material"],
        "umbrella": ["metal_material", "textile_material"],
    }

    LOCAL_TOKEN_HINTS = {
        "battery": "contains_battery",
        "akku": "contains_battery",
        "electronic": "electronic_waste",
        "phone": "electronic_waste",
        "laptop": "electronic_waste",
        "plastic": "plastic_material",
        "bottle": "plastic_material",
        "paper": "paper_material",
        "tissue": "paper_material",
        "napkin": "paper_material",
        "organic": "organic_material",
        "food": "organic_material",
        "glass": "glass_material",
        "metal": "metal_material",
        "textile": "textile_material",
        "wood": "wood_material",
        "packaging": "packaging_material",
        "hazard": "hazardous_hint",
        "toxic": "hazardous_hint",
    }

    def __init__(self):
        self.user_agent = "SmarTrash/1.0 (Educational Project)"
        self.enabled = get_config().enable_web_knowledge  # Kann deaktiviert werden für Offline-Betrieb
        self._internet_ok_cached = False
        self._internet_ok_checked_at = 0.0
        self._internet_cache_ttl_sec = 45.0
        self._last_auto_self_learn_at = 0.0
        self._auto_self_learn_cooldown_sec = 25.0

    def has_internet_connection(self, force_refresh: bool = False) -> bool:
        """Lightweight internet availability check with TTL cache."""
        now = time.time()
        if (not force_refresh) and (now - self._internet_ok_checked_at) <= self._internet_cache_ttl_sec:
            return bool(self._internet_ok_cached)

        probes = [
            "https://en.wikipedia.org/wiki/Main_Page",
            "https://world.openfoodfacts.org/",
        ]
        ok = False
        for url in probes:
            try:
                resp = requests.head(url, headers={"User-Agent": self.user_agent}, timeout=2)
                if 200 <= resp.status_code < 500:
                    ok = True
                    break
            except Exception:
                continue

        self._internet_ok_cached = ok
        self._internet_ok_checked_at = now
        return ok

    def fetch_object_info(self, object_name: str) -> Optional[Dict]:
        """Hole Informationen über ein Objekt"""
        if not self.enabled:
            return None

        try:
            # Versuche Wikipedia
            wiki_info = self._fetch_from_wikipedia(object_name)
            if wiki_info:
                return wiki_info

            # Fallback: DBpedia (strukturierte Wikipedia-Daten)
            dbpedia_info = self._fetch_from_dbpedia(object_name)
            if dbpedia_info:
                return dbpedia_info

            # Fallback: OpenFoodFacts (kostenlos, nützlich für Lebensmittel/Verpackung)
            food_info = self._fetch_from_openfoodfacts(object_name)
            if food_info:
                return food_info

            # Fallback: Wikidata (free, structured, broad domain coverage)
            wikidata_info = self._fetch_from_wikidata(object_name)
            if wikidata_info:
                return wikidata_info

            return None
        except Exception as e:
            print(f"Web fetch error for '{object_name}': {e}")
            return None

    def get_disposal_hints(self, object_name: str, db=None, allow_live_fetch: bool = True) -> Dict:
        """Liefert Entsorgungs-Hinweise aus Cache oder Live-Webwissen."""
        local_hints = self._local_hints_for_object(object_name)
        query_terms = self._expand_object_terms(object_name)

        # Free knowledge expansion: use the enhanced public dataset lexicon first.
        # This increases coverage even when live internet lookup is unavailable.
        try:
            from web_knowledge_enhanced import get_fetcher as get_enhanced_fetcher

            enhanced_fetcher = get_enhanced_fetcher()
            dataset_match = enhanced_fetcher.infer_object_bin_from_dataset(object_name)
            if dataset_match:
                enhanced_profile = enhanced_fetcher.get_unified_material_and_bin(object_name, dataset_match)
                enhanced_hints = []
                material = str(enhanced_profile.get("inferred_material", "unknown")).lower()
                inferred_bin = str(enhanced_profile.get("inferred_bin", "RESTMÜLL")).upper()

                material_hint_map = {
                    "paper": "paper_material",
                    "plastic": "plastic_material",
                    "organic": "organic_material",
                    "glass": "glass_material",
                    "electronic": "electronic_waste",
                    "metal": "metal_material",
                    "textile": "textile_material",
                    "wood": "wood_material",
                    "hazardous": "hazardous_hint",
                }

                hint = material_hint_map.get(material)
                if hint:
                    enhanced_hints.append(hint)
                if inferred_bin == "RESTMÜLL" and material == "electronic":
                    enhanced_hints.append("contains_battery")
                if material in {"electronic", "battery"}:
                    enhanced_hints.append("contains_battery")

                if enhanced_hints:
                    local_hints = self._merge_hints(local_hints, {"hints": enhanced_hints, "confidence": enhanced_profile.get("confidence", 0.65)} )

                if db is not None:
                    try:
                        db.upsert_object_knowledge(
                            object_name=object_name,
                            inferred_material=material,
                            inferred_bin=inferred_bin,
                            confidence=float(enhanced_profile.get("confidence", 0.65) or 0.65),
                            source="free_dataset_lexicon",
                            notes=f"dataset_match:{','.join(enhanced_profile.get('sources', []) or [])}",
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        if db is not None:
            for term in query_terms:
                cached = db.get_web_knowledge(term)
                if cached:
                    description = cached.get("description", "")
                    cached_hints = self._extract_disposal_hints(description)
                    return self._merge_hints(local_hints, cached_hints)

        if not allow_live_fetch:
            return local_hints

        if not self.has_internet_connection():
            return local_hints

        for term in query_terms:
            knowledge = self.fetch_object_info(term)
            if not knowledge:
                continue

            description = knowledge.get("description", "")
            hints = self._extract_disposal_hints(description)
            validation = self._validate_online_knowledge(knowledge, hints)

            if db is not None:
                source_name = str(knowledge.get("source", "unknown"))
                source_to_store = source_name if validation.get("accepted", False) else f"{source_name}_unverified"
                db.cache_web_knowledge(
                    object_name=term,
                    description=description,
                    properties={
                        **(knowledge.get("properties", {}) or {}),
                        "validation": validation,
                    },
                    source=source_to_store,
                )
                if term != object_name:
                    db.cache_web_knowledge(
                        object_name=object_name,
                        description=description,
                        properties={
                            **(knowledge.get("properties", {}) or {}),
                            "validation": validation,
                        },
                        source=source_to_store,
                    )

                if validation.get("accepted", False) and hints.get("hints"):
                    inferred = self._infer_material_bin_from_hints(hints.get("hints", []))
                    db.upsert_object_knowledge(
                        object_name=object_name,
                        inferred_material=inferred["material"],
                        inferred_bin=inferred["bin"],
                        confidence=min(0.95, validation.get("quality_score", 0.0)),
                        source=f"online_validated_{source_name.lower()}",
                        notes=f"validated_online:{term}",
                    )

            merged = self._merge_hints(local_hints, hints)
            merged["online_validation"] = validation
            return merged

        return local_hints

    def _validate_online_knowledge(self, knowledge: Dict, hints: Dict) -> Dict:
        """Scores online knowledge quality and marks if it is safe for direct integration."""
        source = str(knowledge.get("source", "unknown"))
        description = str(knowledge.get("description", "") or "")
        hint_count = len(hints.get("hints", []))

        source_score = 0.45 if source in self.TRUSTED_ONLINE_SOURCES else 0.10
        desc_score = 0.30 if len(description) >= 40 else (0.12 if len(description) >= 12 else 0.0)
        hint_score = min(0.30, hint_count * 0.07)

        quality_score = max(0.0, min(1.0, source_score + desc_score + hint_score))
        accepted = bool(
            source in self.TRUSTED_ONLINE_SOURCES
            and hint_count > 0
            and quality_score >= 0.62
        )

        return {
            "source": source,
            "hint_count": hint_count,
            "description_length": len(description),
            "quality_score": quality_score,
            "accepted": accepted,
            "reason": "accepted" if accepted else "insufficient_quality_or_hints",
        }

    def auto_self_learn_on_recognition_issue(
        self,
        db=None,
        trigger_objects: Optional[List[str]] = None,
        include_priority_terms: bool = True,
        max_terms: int = 120,
        force: bool = False,
    ) -> Dict:
        """Auto-learning path: local trusted seeds first, then live web fetch if internet is available.

        This should be triggered by the inference pipeline when recognition looks weak.
        """
        now = time.time()
        if (not force) and (now - self._last_auto_self_learn_at) < self._auto_self_learn_cooldown_sec:
            return {
                "status": "cooldown",
                "local_seed_terms": 0,
                "live_enriched_terms": 0,
                "internet_available": bool(self._internet_ok_cached),
            }

        # Step 1: Always refresh trusted local seeds into DB knowledge index.
        local_import = self.import_public_knowledge_seeds(
            db=db,
            max_terms=max(1, min(int(max_terms), 1200)),
            allow_live_fetch=False,
        )

        # Step 2: Live enrichment only if internet is available and web knowledge is enabled.
        internet_ok = bool(self.enabled and self.has_internet_connection(force_refresh=True))
        live_enriched = 0
        accepted_online_terms = 0
        live_targets = []

        if include_priority_terms:
            live_targets.extend(self.ONLINE_SELF_LEARN_PRIORITY_TERMS)

        for obj in (trigger_objects or []):
            live_targets.extend(self._expand_object_terms(obj))

        # Deduplicate while keeping order.
        dedup_targets = []
        seen = set()
        for t in live_targets:
            n = str(t or "").strip().lower().replace("_", " ")
            if n and n not in seen:
                seen.add(n)
                dedup_targets.append(n)

        if internet_ok and db is not None:
            for term in dedup_targets[:200]:
                result = self.get_disposal_hints(term, db=db, allow_live_fetch=True)
                if result.get("hints"):
                    live_enriched += 1
                if result.get("online_validation", {}).get("accepted", False):
                    accepted_online_terms += 1

        self._last_auto_self_learn_at = now
        return {
            "status": "ok",
            "local_seed_terms": int(local_import.get("processed", 0)),
            "local_indexed_objects": int(local_import.get("indexed_objects", 0)),
            "live_enriched_terms": int(live_enriched),
            "accepted_online_terms": int(accepted_online_terms),
            "internet_available": internet_ok,
            "trigger_terms_used": len(dedup_targets),
        }

    def warmup_object_knowledge(self, class_names: List[str], db=None, max_live_fetch: int = 20) -> Dict:
        """Wärmt Wissenscache für bekannte Klassen vor (lokal + optional Live-Fetch)."""
        if not class_names:
            return {"processed": 0, "with_hints": 0, "live_fetches": 0}

        processed = 0
        with_hints = 0
        live_fetches = 0

        for class_name in class_names:
            processed += 1
            allow_live = live_fetches < max_live_fetch
            hints = self.get_disposal_hints(class_name, db=db, allow_live_fetch=allow_live)
            if hints.get("hints"):
                with_hints += 1
            if allow_live and self.enabled:
                live_fetches += 1

        return {"processed": processed, "with_hints": with_hints, "live_fetches": live_fetches}

    def import_public_knowledge_seeds(self, db=None, max_terms: int = 80, allow_live_fetch: bool = False) -> Dict:
        """Importiert ein breites, öffentliches Seed-Vokabular in den Wissenscache.

        Ohne Training kann so mehr semantisches Wissen für Material-/Gefahr-Hinweise
        aufgebaut werden, das später bei Klassifikationsentscheidungen hilft.
        """
        base_terms = self.PUBLIC_KNOWLEDGE_SEEDS[:max(0, int(max_terms))]
        terms = []
        seen_terms = set()
        for term in base_terms:
            for variant in self._expand_object_terms(term):
                if variant not in seen_terms:
                    seen_terms.add(variant)
                    terms.append(variant)

        processed = 0
        with_hints = 0
        cached_or_fetched = 0
        indexed_objects = 0
        pending_records = []

        for term in terms:
            processed += 1
            hints = self.get_disposal_hints(term, db=db, allow_live_fetch=allow_live_fetch)
            if hints.get("hints"):
                with_hints += 1
            if db is not None and db.get_web_knowledge(term):
                cached_or_fetched += 1
            if db is not None and hints.get("hints"):
                inferred = self._infer_material_bin_from_hints(hints.get("hints", []))
                pending_records.append(
                    {
                        "object_name": term,
                        "inferred_material": inferred["material"],
                        "inferred_bin": inferred["bin"],
                        "confidence": min(0.88, 0.45 + float(hints.get("confidence", 0.0)) * 0.4),
                        "source": "ontology_seed_import",
                        "notes": "public_seed",
                    }
                )

        if db is not None and pending_records:
            indexed_objects = int(db.bulk_upsert_object_knowledge(pending_records))

        return {
            "processed": processed,
            "with_hints": with_hints,
            "cached_or_fetched": cached_or_fetched,
            "indexed_objects": indexed_objects,
            "live_fetch_enabled": bool(allow_live_fetch),
        }

    def _expand_object_terms(self, object_name: str) -> List[str]:
        """Erweitert Objektbegriffe mit Aliasen aus COCO/OpenImages + Ontologie-Synonymen."""
        base = str(object_name or "").strip().lower().replace("_", " ")
        if not base:
            return []

        terms = [base]
        if base in self.COCO_OPENIMAGES_LABEL_MAP:
            for alias in self.COCO_OPENIMAGES_LABEL_MAP[base]:
                alias_norm = str(alias).strip().lower().replace("_", " ")
                if alias_norm and alias_norm not in terms:
                    terms.append(alias_norm)

        for key, aliases in self.ONTOLOGY_ALIASES.items():
            if key in base:
                for alias in aliases:
                    alias_norm = str(alias).strip().lower().replace("_", " ")
                    if alias_norm and alias_norm not in terms:
                        terms.append(alias_norm)

        for token in base.split():
            aliases = self.ONTOLOGY_ALIASES.get(token, [])
            for alias in aliases:
                alias_norm = str(alias).strip().lower().replace("_", " ")
                if alias_norm and alias_norm not in terms:
                    terms.append(alias_norm)

        return terms[:24]

    def _infer_material_bin_from_hints(self, hints: List[str]) -> Dict:
        """Leitet Material+Tonne aus Hinweis-Tags ab für Seed-Index-Aufbau."""
        tags = set(str(h).strip().lower() for h in hints if str(h).strip())
        if "contains_battery" in tags or "electronic_waste" in tags or "hazardous_hint" in tags:
            return {"material": "electronic", "bin": "RESTMÜLL"}
        if "organic_material" in tags:
            return {"material": "organic", "bin": "BIOMÜLL"}
        if "paper_material" in tags:
            return {"material": "paper", "bin": "PAPIER"}
        if "plastic_material" in tags or "packaging_material" in tags:
            return {"material": "plastic", "bin": "PLASTIK"}
        if "metal_material" in tags:
            return {"material": "metal", "bin": "RESTMÜLL"}
        if "glass_material" in tags:
            return {"material": "glass", "bin": "RESTMÜLL"}
        if "textile_material" in tags:
            return {"material": "textile", "bin": "RESTMÜLL"}
        if "wood_material" in tags:
            return {"material": "wood", "bin": "RESTMÜLL"}
        return {"material": "unknown", "bin": "RESTMÜLL"}

    def _fetch_from_wikipedia(self, term: str) -> Optional[Dict]:
        """Wikipedia API (kostenlos, kein Key nötig)"""
        try:
            # Wikipedia API für Zusammenfassung
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + term.replace(" ", "_")
            headers = {"User-Agent": self.user_agent}

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    "source": "Wikipedia",
                    "description": data.get("extract", ""),
                    "properties": {
                        "title": data.get("title", ""),
                        "thumbnail": data.get("thumbnail", {}).get("source", ""),
                        "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
                    }
                }
            return None
        except Exception as e:
            print(f"Wikipedia fetch failed: {e}")
            return None

    def _fetch_from_dbpedia(self, term: str) -> Optional[Dict]:
        """DBpedia SPARQL Query (strukturierte Daten)"""
        try:
            # SPARQL Query für DBpedia
            query = f"""
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?description ?comment WHERE {{
              ?resource rdfs:label "{term}"@en .
              OPTIONAL {{ ?resource rdfs:comment ?comment . FILTER (lang(?comment) = 'en') }}
              OPTIONAL {{ ?resource dbo:abstract ?description . FILTER (lang(?description) = 'en') }}
            }} LIMIT 1
            """

            url = "http://dbpedia.org/sparql"
            headers = {"Accept": "application/json", "User-Agent": self.user_agent}
            params = {"query": query, "format": "json"}

            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", {}).get("bindings", [])
                if results:
                    result = results[0]
                    return {
                        "source": "DBpedia",
                        "description": result.get("description", {}).get("value", "") or
                                      result.get("comment", {}).get("value", ""),
                        "properties": {}
                    }
            return None
        except Exception as e:
            print(f"DBpedia fetch failed: {e}")
            return None

    def _fetch_from_openfoodfacts(self, term: str) -> Optional[Dict]:
        """OpenFoodFacts Search API (kostenlos, kein API-Key)."""
        try:
            url = "https://world.openfoodfacts.org/cgi/search.pl"
            params = {
                "search_terms": term,
                "search_simple": 1,
                "json": 1,
                "page_size": 1
            }
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, params=params, headers=headers, timeout=5)
            if response.status_code != 200:
                return None

            data = response.json()
            products = data.get("products", [])
            if not products:
                return None

            product = products[0]
            categories = product.get("categories", "")
            packaging = product.get("packaging", "")
            name = product.get("product_name", term)

            description_parts = [p for p in [name, categories, packaging] if p]
            description = " | ".join(description_parts)

            return {
                "source": "OpenFoodFacts",
                "description": description,
                "properties": {
                    "categories": categories,
                    "packaging": packaging,
                }
            }
        except Exception as e:
            print(f"OpenFoodFacts fetch failed: {e}")
            return None

    def _fetch_from_wikidata(self, term: str) -> Optional[Dict]:
        """Wikidata API search (kostenlos, kein API-Key)."""
        try:
            url = "https://www.wikidata.org/w/api.php"
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "language": "en",
                "search": term,
                "limit": 1,
            }
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, params=params, headers=headers, timeout=5)
            if response.status_code != 200:
                return None

            payload = response.json()
            results = payload.get("search", [])
            if not results:
                return None

            hit = results[0]
            description = hit.get("description", "")
            label = hit.get("label", term)
            qid = hit.get("id", "")

            return {
                "source": "Wikidata",
                "description": f"{label} | {description}".strip(" |"),
                "properties": {
                    "id": qid,
                    "label": label,
                    "concepturi": hit.get("concepturi", ""),
                },
            }
        except Exception as e:
            print(f"Wikidata fetch failed: {e}")
            return None

    def enhance_detection_with_knowledge(self, class_name: str, detection: Dict) -> Dict:
        """Reichere Detection mit Web-Wissen an"""
        knowledge = self.fetch_object_info(class_name)

        if knowledge:
            detection["web_knowledge"] = {
                "description": knowledge.get("description", "")[:200],  # Erste 200 Zeichen
                "source": knowledge.get("source", ""),
                "available": True
            }
        else:
            detection["web_knowledge"] = {
                "available": False
            }

        return detection

    def _extract_disposal_hints(self, description: str) -> Dict:
        """Extrahiert relevante Recycling-/Gefahr-Hinweise aus Text."""
        if not description:
            return {"hints": [], "confidence": 0.0}

        text = description.lower()
        hints = []

        keyword_map = {
            "battery": "contains_battery",
            "akku": "contains_battery",
            "batterie": "contains_battery",
            "lithium": "contains_battery",
            "electronic": "electronic_waste",
            "elektronik": "electronic_waste",
            "plastic": "plastic_material",
            "kunststoff": "plastic_material",
            "pet": "plastic_material",
            "hdpe": "plastic_material",
            "polyethylene": "plastic_material",
            "polypropylene": "plastic_material",
            "paper": "paper_material",
            "papier": "paper_material",
            "karton": "paper_material",
            "tissue": "paper_material",
            "napkin": "paper_material",
            "paper towel": "paper_material",
            "kitchen roll": "paper_material",
            "toilet paper": "paper_material",
            "taschentuch": "paper_material",
            "serviette": "paper_material",
            "küchenrolle": "paper_material",
            "kuechenrolle": "paper_material",
            "toilettenpapier": "paper_material",
            "organic": "organic_material",
            "bio": "organic_material",
            "food": "organic_material",
            "compost": "organic_material",
            "biowaste": "organic_material",
            "recycle": "recyclable_hint",
            "recycling": "recyclable_hint",
            "recycelbar": "recyclable_hint",
            "packaging": "packaging_material",
            "verpackung": "packaging_material",
            "metal": "metal_material",
            "aluminum": "metal_material",
            "aluminium": "metal_material",
            "steel": "metal_material",
            "iron": "metal_material",
            "textile": "textile_material",
            "fabric": "textile_material",
            "cloth": "textile_material",
            "wood": "wood_material",
            "holz": "wood_material",
            "hazard": "hazardous_hint",
            "gefahr": "hazardous_hint",
            "toxic": "hazardous_hint",
            "giftig": "hazardous_hint",
            "glass": "glass_material"
        }

        for keyword, tag in keyword_map.items():
            if keyword in text and tag not in hints:
                hints.append(tag)

        confidence = min(len(hints) / 5.0, 1.0)
        return {"hints": hints, "confidence": confidence}

    def _local_hints_for_object(self, object_name: str) -> Dict:
        """Lokale, sofort verfügbare Hinweisableitung ohne Netzwerkanfrage."""
        name = str(object_name or "").strip().lower().replace("_", " ")
        hints = []
        terms = self._expand_object_terms(name)

        for term in terms or [name]:
            explicit = self.LOCAL_CLASS_HINTS.get(term, [])
            for hint in explicit:
                if hint not in hints:
                    hints.append(hint)

            for token, hint in self.LOCAL_TOKEN_HINTS.items():
                if token in term and hint not in hints:
                    hints.append(hint)

        confidence = min(0.25 + (len(hints) * 0.12), 0.85) if hints else 0.0
        return {"hints": hints, "confidence": confidence}

    def _merge_hints(self, base: Dict, extra: Dict) -> Dict:
        """Merge zweier Hinweisquellen ohne Duplikate."""
        base_hints = list(base.get("hints", []))
        extra_hints = list(extra.get("hints", []))
        merged = []
        for hint in base_hints + extra_hints:
            if hint not in merged:
                merged.append(hint)
        confidence = max(float(base.get("confidence", 0.0)), float(extra.get("confidence", 0.0)))
        return {"hints": merged, "confidence": confidence}


# Singleton
_fetcher = None

def get_fetcher():
    global _fetcher
    if _fetcher is None:
        _fetcher = WebKnowledgeFetcher()
    return _fetcher
