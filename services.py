"""
Business logic services for the Planning Agent System.
"""
import logging
from typing import List, Optional
from datetime import datetime

from models import Plan, Step, StepStatus, PlanStatus, CreateStepRequest
from database import db_connection

logger = logging.getLogger(__name__)

class PlanningService:
    """Service for creating and managing plans."""
    
    @staticmethod
    def create_plan_with_steps(name: str, description: str, user_id: str, 
                              steps: List[CreateStepRequest]) -> Plan:
        """Create a new plan with user-provided steps."""
        try:
            # Create the plan
            plan = Plan(
                name=name,
                description=description,
                user_id=user_id
            )
            
            # Add user-provided steps to plan
            for i, step_request in enumerate(steps):
                order = step_request.order if step_request.order is not None else i + 1
                plan.add_step(
                    description=step_request.description,
                    order=order,
                    depends_on=step_request.depends_on,
                    notes=step_request.notes
                )
            
            # Save to database
            db_connection.create_plan(plan)
            
            logger.info(f"Created new plan {plan.plan_id} with {len(steps)} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            raise
    
    @staticmethod
    def regenerate_plan(plan_id: str, new_description: Optional[str], 
                       new_steps: List[CreateStepRequest]) -> Optional[Plan]:
        """Regenerate a plan with user-provided steps."""
        try:
            # Get existing plan
            plan = db_connection.get_plan(plan_id)
            if not plan:
                return None
            
            # Update description if provided
            if new_description is not None:
                plan.description = new_description
            
            plan.updated_at = datetime.utcnow()
            
            # Clear existing steps
            plan.steps = []
            
            # Add new user-provided steps
            for i, step_request in enumerate(new_steps):
                order = step_request.order if step_request.order is not None else i + 1
                plan.add_step(
                    description=step_request.description,
                    order=order,
                    depends_on=step_request.depends_on,
                    notes=step_request.notes
                )
            
            # Reset plan status
            plan.status = PlanStatus.NOT_STARTED
            
            # Save updated plan
            db_connection.update_plan(plan)
            
            logger.info(f"Regenerated plan {plan_id} with {len(new_steps)} new steps")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to regenerate plan {plan_id}: {e}")
            raise

class ExecutionService:
    """Service for managing plan execution."""
    
    @staticmethod
    def get_plan(plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        return db_connection.get_plan(plan_id)
    
    @staticmethod
    def get_plans(user_id: Optional[str] = None, 
                  status: Optional[PlanStatus] = None,
                  name_filter: Optional[str] = None) -> List[Plan]:
        """Get plans with optional filtering."""
        return db_connection.get_plans(user_id=user_id, status=status, name_filter=name_filter)
    
    @staticmethod
    def update_step_status(plan_id: str, step_id: str, 
                          status: StepStatus, notes: Optional[str] = None) -> bool:
        """Update a step's status."""
        try:
            plan = db_connection.get_plan(plan_id)
            if not plan:
                logger.warning(f"Plan {plan_id} not found")
                return False
            
            success = plan.update_step(step_id, status=status, notes=notes)
            if success:
                db_connection.update_plan(plan)
                logger.info(f"Updated step {step_id} status to {status}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update step {step_id}: {e}")
            raise
    
    @staticmethod
    def get_next_step(plan_id: str) -> Optional[Step]:
        """Get the next pending step for a plan."""
        plan = db_connection.get_plan(plan_id)
        if not plan:
            return None
        
        return plan.get_next_step()
    
    @staticmethod
    def skip_step(plan_id: str, step_id: str) -> bool:
        """Mark a step as skipped."""
        return ExecutionService.update_step_status(plan_id, step_id, StepStatus.SKIPPED)

class ManagementService:
    """Service for plan and step management operations."""
    
    @staticmethod
    def update_plan_metadata(plan_id: str, name: Optional[str] = None,
                           description: Optional[str] = None,
                           status: Optional[PlanStatus] = None) -> bool:
        """Update plan metadata."""
        try:
            plan = db_connection.get_plan(plan_id)
            if not plan:
                return False
            
            if name is not None:
                plan.name = name
            if description is not None:
                plan.description = description
            if status is not None:
                plan.status = status
            
            plan.updated_at = datetime.utcnow()
            db_connection.update_plan(plan)
            
            logger.info(f"Updated plan {plan_id} metadata")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update plan {plan_id}: {e}")
            raise
    
    @staticmethod
    def delete_plan(plan_id: str) -> bool:
        """Delete a plan."""
        try:
            success = db_connection.delete_plan(plan_id)
            if success:
                logger.info(f"Deleted plan {plan_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to delete plan {plan_id}: {e}")
            raise
    
    @staticmethod
    def add_step_to_plan(plan_id: str, description: str, order: Optional[int] = None,
                        depends_on: Optional[List[str]] = None, 
                        notes: Optional[str] = None) -> Optional[str]:
        """Add a new step to a plan."""
        try:
            plan = db_connection.get_plan(plan_id)
            if not plan:
                return None
            
            step_id = plan.add_step(
                description=description,
                order=order,
                depends_on=depends_on,
                notes=notes
            )
            
            db_connection.update_plan(plan)
            logger.info(f"Added step {step_id} to plan {plan_id}")
            return step_id
            
        except Exception as e:
            logger.error(f"Failed to add step to plan {plan_id}: {e}")
            raise
    
    @staticmethod
    def delete_step_from_plan(plan_id: str, step_id: str) -> bool:
        """Delete a step from a plan."""
        try:
            plan = db_connection.get_plan(plan_id)
            if not plan:
                return False
            
            success = plan.delete_step(step_id)
            if success:
                db_connection.update_plan(plan)
                logger.info(f"Deleted step {step_id} from plan {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete step {step_id}: {e}")
            raise
    
    @staticmethod
    def reset_plan_steps(plan_id: str) -> bool:
        """Reset all steps in a plan to pending status."""
        try:
            plan = db_connection.get_plan(plan_id)
            if not plan:
                return False
            
            plan.reset_steps()
            db_connection.update_plan(plan)
            
            logger.info(f"Reset all steps in plan {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset plan {plan_id}: {e}")
            raise
