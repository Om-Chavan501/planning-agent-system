"""
CouchDB database connection and operations for the Planning Agent System.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import couchdb
from couchdb.http import ResourceNotFound, ResourceConflict

from config import settings
from models import Plan, PlanStatus

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Manages CouchDB connection and operations."""
    
    def __init__(self):
        """Initialize the database connection."""
        self.server = None
        self.db = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to CouchDB server."""
        try:
            # Connect to CouchDB server
            self.server = couchdb.Server(settings.COUCH_URL)
            self.server.resource.credentials = (settings.COUCH_USER, settings.COUCH_PASS)
            
            # Test connection
            _ = self.server.version()
            logger.info(f"Connected to CouchDB at {settings.COUCH_URL}")
            
            # Initialize database
            self._initialize_database()
            
        except Exception as e:
            logger.error(f"Failed to connect to CouchDB: {e}")
            raise
    
    def _initialize_database(self) -> None:
        """Initialize the plans database."""
        try:
            # Try to get existing database
            self.db = self.server[settings.COUCH_DATABASE]
            logger.info(f"Connected to existing database: {settings.COUCH_DATABASE}")
        except ResourceNotFound:
            # Create new database
            try:
                self.db = self.server.create(settings.COUCH_DATABASE)
                logger.info(f"Created new database: {settings.COUCH_DATABASE}")
            except ResourceConflict:
                # Database was created by another process
                self.db = self.server[settings.COUCH_DATABASE]
                logger.info(f"Connected to database: {settings.COUCH_DATABASE}")
    
    def is_connected(self) -> bool:
        """Check if database connection is active."""
        try:
            if self.server and self.db:
                _ = self.server.version()
                return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
        return False
    
    def create_plan(self, plan: Plan) -> str:
        """Create a new plan in the database."""
        try:
            # Convert plan to dictionary for CouchDB
            plan_dict = self._plan_to_dict(plan)
            
            # Use plan_id as document ID
            doc_id = plan.plan_id
            plan_dict['_id'] = doc_id
            
            # Save to database
            doc_id, doc_rev = self.db.save(plan_dict)
            logger.info(f"Created plan {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            raise
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by ID."""
        try:
            doc = self.db[plan_id]
            return self._dict_to_plan(doc)
        except ResourceNotFound:
            logger.warning(f"Plan {plan_id} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to get plan {plan_id}: {e}")
            raise
    
    def update_plan(self, plan: Plan) -> bool:
        """Update an existing plan."""
        try:
            # Get current document
            doc = self.db[plan.plan_id]
            
            # Update with new data
            updated_dict = self._plan_to_dict(plan)
            updated_dict['_id'] = doc['_id']
            updated_dict['_rev'] = doc['_rev']
            
            # Save updated document
            self.db.save(updated_dict)
            logger.info(f"Updated plan {plan.plan_id}")
            return True
            
        except ResourceNotFound:
            logger.warning(f"Plan {plan.plan_id} not found for update")
            return False
        except Exception as e:
            logger.error(f"Failed to update plan {plan.plan_id}: {e}")
            raise
    
    def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan."""
        try:
            doc = self.db[plan_id]
            self.db.delete(doc)
            logger.info(f"Deleted plan {plan_id}")
            return True
        except ResourceNotFound:
            logger.warning(f"Plan {plan_id} not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Failed to delete plan {plan_id}: {e}")
            raise
    
    def get_plans(self, user_id: Optional[str] = None, 
                  status: Optional[PlanStatus] = None,
                  name_filter: Optional[str] = None) -> List[Plan]:
        """Get all plans with optional filtering."""
        try:
            plans = []
            
            # Get all documents
            for doc_id in self.db:
                try:
                    doc = self.db[doc_id]
                    
                    # Skip design documents
                    if doc_id.startswith('_design'):
                        continue
                    
                    plan = self._dict_to_plan(doc)
                    
                    # Apply filters
                    if user_id and plan.user_id != user_id:
                        continue
                    
                    if status and plan.status != status:
                        continue
                    
                    if name_filter and name_filter.lower() not in plan.name.lower():
                        continue
                    
                    plans.append(plan)
                    
                except Exception as e:
                    logger.warning(f"Failed to process document {doc_id}: {e}")
                    continue
            
            # Sort by creation date (newest first)
            plans.sort(key=lambda x: x.created_at, reverse=True)
            return plans
            
        except Exception as e:
            logger.error(f"Failed to get plans: {e}")
            raise
    
    def _plan_to_dict(self, plan: Plan) -> Dict[str, Any]:
        """Convert Plan object to dictionary for CouchDB storage."""
        plan_dict = {
            'plan_id': plan.plan_id,
            'name': plan.name,
            'description': plan.description,
            'status': plan.status.value,
            'user_id': plan.user_id,
            'created_at': plan.created_at.isoformat(),
            'updated_at': plan.updated_at.isoformat(),
            'steps': []
        }
        
        # Convert steps
        for step in plan.steps:
            step_dict = {
                'step_id': step.step_id,
                'order': step.order,
                'description': step.description,
                'status': step.status.value,
                'depends_on': step.depends_on,
                'notes': step.notes,
                'created_at': step.created_at.isoformat(),
                'updated_at': step.updated_at.isoformat(),
                'completed_at': step.completed_at.isoformat() if step.completed_at else None
            }
            plan_dict['steps'].append(step_dict)
        
        return plan_dict
    
    def _dict_to_plan(self, doc: Dict[str, Any]) -> Plan:
        """Convert CouchDB document to Plan object."""
        from models import Step, StepStatus  # Import here to avoid circular imports
        
        # Parse dates
        created_at = datetime.fromisoformat(doc['created_at'].replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(doc['updated_at'].replace('Z', '+00:00'))
        
        # Parse steps
        steps = []
        for step_dict in doc.get('steps', []):
            step_created_at = datetime.fromisoformat(step_dict['created_at'].replace('Z', '+00:00'))
            step_updated_at = datetime.fromisoformat(step_dict['updated_at'].replace('Z', '+00:00'))
            step_completed_at = None
            if step_dict.get('completed_at'):
                step_completed_at = datetime.fromisoformat(step_dict['completed_at'].replace('Z', '+00:00'))
            
            step = Step(
                step_id=step_dict['step_id'],
                order=step_dict['order'],
                description=step_dict['description'],
                status=StepStatus(step_dict['status']),
                depends_on=step_dict.get('depends_on', []),
                notes=step_dict.get('notes'),
                created_at=step_created_at,
                updated_at=step_updated_at,
                completed_at=step_completed_at
            )
            steps.append(step)
        
        # Create plan
        plan = Plan(
            plan_id=doc['plan_id'],
            name=doc['name'],
            description=doc['description'],
            status=PlanStatus(doc['status']),
            user_id=doc['user_id'],
            created_at=created_at,
            updated_at=updated_at,
            steps=steps
        )
        
        return plan

# Global database connection instance
db_connection = DatabaseConnection()
