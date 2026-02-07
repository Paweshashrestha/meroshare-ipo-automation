import os
import yaml
from typing import Dict, Any

class Config:
    def __init__(self, config_path: str | None = None):
        if config_path:
            self.config_path = config_path
        elif os.getenv('CONFIG_PATH'):
            self.config_path = os.getenv('CONFIG_PATH')
        else:
            # Try multiple locations
            possible_paths = [
                'config.yaml',  # Root directory
                'config/config.yaml',  # Config folder
                os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),  # Relative to src
            ]
            self.config_path = None
            for path in possible_paths:
                full_path = os.path.abspath(path)
                if os.path.exists(full_path):
                    self.config_path = full_path
                    break
            if not self.config_path:
                self.config_path = 'config/config.yaml'  # Default fallback
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        else:
            # Try to find config file
            possible_paths = [
                'config.yaml',
                'config/config.yaml',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        return yaml.safe_load(f) or {}
        return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default
    
    def get_meroshare(self) -> Dict[str, Any]:
        return self.config.get('meroshare', {})
    
    def get_database(self) -> Dict[str, Any]:
        return self.config.get('database', {})
    
    def get_telegram(self) -> Dict[str, Any]:
        return self.config.get('telegram', {})

