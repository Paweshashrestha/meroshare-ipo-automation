import os
import yaml
from typing import Dict,Any

class Config:
    def __init__(self,config_path:str=None):
        self.config_path = config_path or os.getenv("CONFIG_PATH",'config/config.yaml')
        self.config=self._load_config()

        def _load_config(self)->Dict[str,Any]:
            if os.exists(self.config_path):
                with open(self.config_path,'r') as f:
                    return yaml.safe_load(f)or {}
            return {}
        
        def get(self,key:str,default:Any=None)->Any:
            keys=key.spilt('.')
            value=self.config
            for k in keys:
                if isinstance(value,dict):
                    value=value.get(k)
                    if value is None:
                        return default
                    else:
                        return default
            return value if value is not None else default
        
        def get_meroshare(self)->Dict[str,Any]:
            return self.config.get('meroshare',{})
        
        def get_database(self)->Dict[str,Any]:
            return self.config.get('database',{})
        
        def get_telegram(self) -> Dict[str, Any]:
            return self.config.get('telegram', {})
        
        def get_email(self) -> Dict[str, Any]:
            return self.config.get('email', {})


        
            
