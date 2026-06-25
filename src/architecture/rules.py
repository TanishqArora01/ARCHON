import os
import yaml
from typing import Dict, List
from pydantic import BaseModel, Field

class ComponentRules(BaseModel):
    can_call: List[str] = Field(default_factory=list)
    cannot_call: List[str] = Field(default_factory=list)

class ArchitectureRules(BaseModel):
    """
    Represents the parsed .aegis/rules.yaml file.
    """
    components: Dict[str, ComponentRules] = Field(default_factory=dict)

    @classmethod
    def load_from_file(cls, filepath: str) -> "ArchitectureRules":
        if not os.path.exists(filepath):
            return cls()
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        components: Dict[str, ComponentRules] = {}
        
        # Parse main component rules
        for key, value in data.items():
            if key == "Forbidden":
                continue
            if isinstance(value, dict):
                can_call = value.get("can_call", [])
                cannot_call = value.get("cannot_call", [])
                components[key] = ComponentRules(can_call=can_call, cannot_call=cannot_call)
                
        # Parse Forbidden blocks
        if "Forbidden" in data and isinstance(data["Forbidden"], dict):
            for key, value in data["Forbidden"].items():
                if isinstance(value, dict):
                    cannot_call = value.get("cannot_call", [])
                    if key not in components:
                        components[key] = ComponentRules()
                    components[key].cannot_call.extend(cannot_call)
                    
        # Ensure all components mentioned in can_call and cannot_call are tracked as keys
        all_mentioned_components = set()
        for _comp, rules in components.items():
            all_mentioned_components.update(rules.can_call)
            all_mentioned_components.update(rules.cannot_call)
            
        for comp in all_mentioned_components:
            if comp not in components:
                components[comp] = ComponentRules()
                    
        return cls(components=components)
