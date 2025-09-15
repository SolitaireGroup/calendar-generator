import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class CalendarManager:
    """
    Gerencia calendários (Google Calendar + arquivos .ics)
    """
    
    def __init__(self, use_google_calendar: bool = False):
        self.use_google_calendar = use_google_calendar
        self.google_manager = None  # Será implementado depois
        self.metadata_file = "calendar_metadata.json"
    
    def load_metadata(self) -> Dict:
        """
        Carrega metadados dos eventos criados
        """
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"events": [], "last_update": None}
    
    def save_metadata(self, metadata: Dict):
        """
        Salva metadados dos eventos
        """
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def clear_old_school_events(self):
        """
        Remove eventos antigos da escola
        """
        # Limpa metadados locais
        metadata = self.load_metadata()
        old_count = len(metadata.get("events", []))
        metadata["events"] = []
        metadata["last_update"] = datetime.now().isoformat()
        self.save_metadata(metadata)
        
        logger.info(f"Limpos {old_count} eventos dos metadados locais")
        return old_count
    
    def add_event_metadata(self, event_info: Dict):
        """
        Adiciona metadados de um evento criado
        """
        metadata = self.load_metadata()
        metadata["events"].append(event_info)
        metadata["last_update"] = datetime.now().isoformat()
        self.save_metadata(metadata)
    
    def get_events_summary(self) -> Dict:
        """
        Retorna resumo dos eventos gerenciados
        """
        metadata = self.load_metadata()
        return {
            "total_events": len(metadata.get("events", [])),
            "last_update": metadata.get("last_update"),
            "google_calendar_enabled": self.use_google_calendar
        }