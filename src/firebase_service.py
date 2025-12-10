"""
Firebase service for real-time conversation updates and analytics.
Optional integration for real-time features.
"""
import os
from typing import Dict, Optional, List
import json

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("Warning: firebase-admin not available. Install with: pip install firebase-admin")


class FirebaseService:
    """
    Firebase service for real-time features.
    Handles conversation updates, analytics, and live knowledge base sync.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Firebase service.
        
        Args:
            credentials_path: Path to Firebase service account credentials JSON file
        """
        self.db = None
        self.initialized = False
        
        if not FIREBASE_AVAILABLE:
            print("Warning: Firebase not available. Real-time features disabled.")
            return
        
        try:
            # Initialize Firebase Admin SDK
            if credentials_path and os.path.exists(credentials_path):
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred)
            else:
                # Try to use default credentials (from environment)
                try:
                    firebase_admin.initialize_app()
                except ValueError:
                    # Already initialized
                    pass
            
            self.db = firestore.client()
            self.initialized = True
            print("✓ Firebase service initialized")
        except Exception as e:
            print(f"Warning: Could not initialize Firebase: {e}")
            self.initialized = False
    
    def update_conversation(self, conversation_id: str, message_data: Dict):
        """
        Update conversation in Firebase for real-time sync.
        
        Args:
            conversation_id: Conversation ID
            message_data: Message data dictionary
        """
        if not self.initialized or not self.db:
            return
        
        try:
            doc_ref = self.db.collection('conversations').document(conversation_id)
            doc_ref.set({
                'last_message': message_data,
                'updated_at': firestore.SERVER_TIMESTAMP,
            }, merge=True)
        except Exception as e:
            print(f"Error updating conversation in Firebase: {e}")
    
    def log_analytics(self, event_type: str, data: Dict):
        """
        Log analytics events to Firebase.
        
        Args:
            event_type: Type of event (e.g., 'message_sent', 'intent_detected')
            data: Event data dictionary
        """
        if not self.initialized or not self.db:
            return
        
        try:
            self.db.collection('analytics').add({
                'event_type': event_type,
                'data': data,
                'timestamp': firestore.SERVER_TIMESTAMP,
            })
        except Exception as e:
            print(f"Error logging analytics to Firebase: {e}")
    
    def sync_knowledge_base_update(self, entry_id: str, entry_data: Dict):
        """
        Sync knowledge base updates to Firebase for live updates.
        
        Args:
            entry_id: FAQ entry ID
            entry_data: Entry data dictionary
        """
        if not self.initialized or not self.db:
            return
        
        try:
            self.db.collection('knowledge_base').document(str(entry_id)).set(entry_data)
        except Exception as e:
            print(f"Error syncing knowledge base to Firebase: {e}")
    
    def get_user_analytics(self, user_id: str, days: int = 30) -> List[Dict]:
        """
        Get user analytics from Firebase.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of analytics events
        """
        if not self.initialized or not self.db:
            return []
        
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.collection('analytics').where(
                'data.user_id', '==', user_id
            ).where(
                'timestamp', '>=', cutoff_date
            ).order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            results = query.stream()
            return [doc.to_dict() for doc in results]
        except Exception as e:
            print(f"Error getting user analytics from Firebase: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if Firebase service is available"""
        return self.initialized and self.db is not None


# Global instance
_firebase_service_instance = None


def get_firebase_service(credentials_path: Optional[str] = None) -> FirebaseService:
    """Get or create global Firebase service instance"""
    global _firebase_service_instance
    if _firebase_service_instance is None:
        _firebase_service_instance = FirebaseService(credentials_path)
    return _firebase_service_instance

