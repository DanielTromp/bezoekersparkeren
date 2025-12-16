import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models import ParkingSession

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("sessions.json")
        
    def save_sessions(self, sessions: List[ParkingSession]):
        """Save sessions to JSON file"""
        try:
            data = [session.model_dump() for session in sessions]
            # Handle datetime JSON serialization if needed, but model_dump with mode='json' (pydantic v2) or manual
            # For pydantic v2, model_dump(mode='json') works best.
            # Assuming pydantic v2 based on requirements (>=2.0.0)
            
            with open(self.storage_path, 'w') as f:
                # We can't dump directly if they contain datetimes that aren't serializable
                # Pydantic v2 helper
                import json
                
                # Custom serializer
                def json_serial(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    raise TypeError(f"Type {type(obj)} not serializable")
                    
                json.dump(data, f, default=json_serial, indent=2)
                
            logger.debug(f"Saved {len(sessions)} sessions to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def load_sessions(self) -> List[ParkingSession]:
        """Load sessions from JSON file"""
        if not self.storage_path.exists():
            return []
            
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                
            sessions = []
            for item in data:
                try:
                    # Pydantic parses ISO strings back to datetime automatically
                    sessions.append(ParkingSession(**item))
                except Exception as e:
                    logger.warning(f"Skipping invalid session in local storage: {e}")
                    
            return sessions
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            return []
            
    def get_session(self, session_id: str) -> Optional[ParkingSession]:
        """Get a specific session by ID"""
        sessions = self.load_sessions()
        for session in sessions:
            if session.id == session_id:
                return session
        return None

    def add_session(self, session: ParkingSession):
        """Add a single session to storage"""
        sessions = self.load_sessions()
        # Check if already exists? (by ID)
        # If ID is None (fresh register), we might need to generate one or wait for list refresh.
        # But user wants update. 
        # If register returns a session without ID, we should probably generate one same way list does.
        
        # If ID exists, update it?
        existing_idx = next((i for i, s in enumerate(sessions) if s.id == session.id), -1)
        
        if existing_idx >= 0:
            sessions[existing_idx] = session
        else:
            sessions.append(session)
            
        self.save_sessions(sessions)

    def remove_session(self, session_id: str):
        """Remove a session from storage"""
        sessions = self.load_sessions()
        sessions = [s for s in sessions if s.id != session_id]
        self.save_sessions(sessions)
