#!/usr/bin/env python3
"""
💾 MASTER DATABASE LOADER
Lädt die unified_master_database für Trainingsnutzung
"""

import json
import os
from typing import Dict, Optional


class MasterDatabaseLoader:
    """Lädt und verwaltet die Master-Datenbank."""
    
    _instance = None
    _database = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_database(self, filepath: Optional[str] = None) -> Dict:
        """Lädt die Master-Datenbank."""
        if self._database is not None:
            return self._database
        
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(__file__),
                "unified_master_database.json"
            )
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Database not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            self._database = json.load(f)
        
        return self._database
    
    def get_objects(self) -> Dict:
        """Returns all objects."""
        if self._database is None:
            self.load_database()
        return self._database.get("objects", {})
    
    def get_materials(self) -> Dict:
        """Returns all materials."""
        if self._database is None:
            self.load_database()
        return self._database.get("materials", {})
    
    def get_synonyms(self) -> Dict:
        """Returns all synonyms."""
        if self._database is None:
            self.load_database()
        return self._database.get("synonyms", {})
    
    def get_recycling_rules(self) -> Dict:
        """Returns recycling rules."""
        if self._database is None:
            self.load_database()
        return self._database.get("recycling_rules", {})
    
    def get_training_metadata(self) -> Dict:
        """Returns ML training metadata."""
        if self._database is None:
            self.load_database()
        return self._database.get("training_metadata", {})
    
    def get_statistics(self) -> Dict:
        """Returns database statistics."""
        if self._database is None:
            self.load_database()
        return self._database.get("metadata", {}).get("statistics", {})
    
    def print_info(self):
        """Prints database information."""
        if self._database is None:
            self.load_database()
        
        meta = self._database.get("metadata", {})
        stats = meta.get("statistics", {})
        
        print("=" * 80)
        print("🗄️  MASTER DATABASE INFORMATION")
        print("=" * 80)
        print(f"Version: {meta.get('version')}")
        print(f"Created: {meta.get('creation_date')}")
        print(f"\nOBJECTS: {stats.get('total_objects'):,}")
        print(f"MATERIALS: {stats.get('total_materials')}")
        print(f"SYNONYMS: {stats.get('total_synonyms'):,}")
        print(f"CATEGORIES: {stats.get('total_categories')}")
        print(f"HAZARDS: {stats.get('total_hazards')}")
        print("=" * 80)


def load_master_database(filepath: Optional[str] = None) -> Dict:
    """Convenience function to load master database."""
    loader = MasterDatabaseLoader()
    return loader.load_database(filepath)


def get_all_objects() -> Dict:
    """Get all objects from database."""
    loader = MasterDatabaseLoader()
    loader.load_database()
    return loader.get_objects()


def get_all_materials() -> Dict:
    """Get all materials from database."""
    loader = MasterDatabaseLoader()
    loader.load_database()
    return loader.get_materials()


def get_training_info() -> Dict:
    """Get training metadata."""
    loader = MasterDatabaseLoader()
    loader.load_database()
    return loader.get_training_metadata()


if __name__ == "__main__":
    loader = MasterDatabaseLoader()
    loader.load_database()
    loader.print_info()
