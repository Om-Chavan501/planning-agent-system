"""
Pydantic models for the Planning Agent System.
"""
from datetime import datetime
from typing import List, Optional, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator
from enum import Enum

class PlanStatus(str, Enum):
    """Enumeration for plan status values."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"

class StepStatus(str, Enum):
    """Enumeration for step status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

# Request Models
class CreateStepRequest(BaseModel):
    """Request model for creating a step within a plan."""
    description: str = Field(..., min_length=1, max_length=500, description="Step description")
    order: Optional[int] = Field(None, ge=1, description="Step order (auto-assigned if not provided)")
    depends_on: Optional[List[str]] = Field(default_factory=list, description="List of step IDs this step depends on")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes for the step")

class CreatePlanRequest(BaseModel):
    """Request model for creating a new plan."""
    name: str = Field(..., min_length=1, max_length=200, description="Plan name")
    description: str = Field(..., min_length=1, max_length=1000, description="Detailed description of what needs to be accomplished")
    user_id: str = Field(..., min_length=1, max_length=100, description="User identifier")
    steps: List[CreateStepRequest] = Field(..., min_items=1, description="List of steps for the plan")

class UpdatePlanRequest(BaseModel):
    """Request model for updating plan metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    status: Optional[PlanStatus] = None

class UpdateStepRequest(BaseModel):
    """Request model for updating a step."""
    status: Optional[StepStatus] = None
    notes: Optional[str] = Field(None, max_length=500)

class AddStepRequest(BaseModel):
    """Request model for adding a new step to a plan."""
    description: str = Field(..., min_length=1, max_length=500)
    order: Optional[int] = Field(None, ge=1)
    depends_on: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=500)

class RegeneratePlanRequest(BaseModel):
    """Request model for regenerating a plan."""
    description: Optional[str] = Field(None, min_length=1, max_length=1000, description="Updated description for the plan")
    steps: List[CreateStepRequest] = Field(..., min_items=1, description="New list of steps for the plan")

# Response Models
class StepResponse(BaseModel):
    """Response model for a step."""
    step_id: str
    order: int
    description: str
    status: StepStatus
    depends_on: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PlanResponse(BaseModel):
    """Response model for a plan."""
    plan_id: str
    name: str
    description: str
    status: PlanStatus
    user_id: str
    created_at: datetime
    updated_at: datetime
    steps: List[StepResponse] = Field(default_factory=list)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PlanSummaryResponse(BaseModel):
    """Response model for plan summary."""
    plan_id: str
    name: str
    description: str
    status: PlanStatus
    user_id: str
    total_steps: int
    completed_steps: int
    pending_steps: int
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ProgressResponse(BaseModel):
    """Response model for plan progress."""
    plan_id: str
    total_steps: int
    completed_steps: int
    in_progress_steps: int
    pending_steps: int
    failed_steps: int
    skipped_steps: int
    completion_percentage: float

class NextStepResponse(BaseModel):
    """Response model for next step."""
    step: Optional[StepResponse] = None
    message: str

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: datetime
    database_connected: bool
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Internal Models for CouchDB
class Step(BaseModel):
    """Internal model for a step within a plan."""
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    order: int
    description: str
    status: StepStatus = StepStatus.PENDING
    depends_on: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def mark_completed(self) -> None:
        """Mark the step as completed."""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_status(self, status: StepStatus, notes: Optional[str] = None) -> None:
        """Update step status and notes."""
        self.status = status
        self.updated_at = datetime.utcnow()
        if status == StepStatus.COMPLETED:
            self.completed_at = datetime.utcnow()
        if notes is not None:
            self.notes = notes

class Plan(BaseModel):
    """Internal model for a plan document."""
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    status: PlanStatus = PlanStatus.NOT_STARTED
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    steps: List[Step] = Field(default_factory=list)

    def add_step(self, description: str, order: Optional[int] = None, 
                 depends_on: Optional[List[str]] = None, notes: Optional[str] = None) -> str:
        """Add a new step to the plan."""
        if order is None:
            order = len(self.steps) + 1
        
        step = Step(
            description=description,
            order=order,
            depends_on=depends_on or [],
            notes=notes
        )
        
        # Insert step at correct position based on order
        inserted = False
        for i, existing_step in enumerate(self.steps):
            if existing_step.order > order:
                self.steps.insert(i, step)
                inserted = True
                break
        
        if not inserted:
            self.steps.append(step)
        
        # Reorder subsequent steps
        for i, step_item in enumerate(self.steps):
            if step_item.step_id != step.step_id and step_item.order >= order:
                step_item.order += 1
        
        self.updated_at = datetime.utcnow()
        self._update_plan_status()
        return step.step_id

    def get_step(self, step_id: str) -> Optional[Step]:
        """Get a step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def update_step(self, step_id: str, status: Optional[StepStatus] = None, 
                    notes: Optional[str] = None) -> bool:
        """Update a step's status and notes."""
        step = self.get_step(step_id)
        if not step:
            return False
        
        if status:
            step.update_status(status, notes)
        elif notes is not None:
            step.notes = notes
            step.updated_at = datetime.utcnow()
        
        self.updated_at = datetime.utcnow()
        self._update_plan_status()
        return True

    def delete_step(self, step_id: str) -> bool:
        """Delete a step from the plan."""
        step = self.get_step(step_id)
        if not step:
            return False
        
        # Remove the step
        self.steps = [s for s in self.steps if s.step_id != step_id]
        
        # Reorder remaining steps
        self.steps.sort(key=lambda x: x.order)
        for i, step_item in enumerate(self.steps):
            step_item.order = i + 1
        
        self.updated_at = datetime.utcnow()
        self._update_plan_status()
        return True

    def reset_steps(self) -> None:
        """Reset all steps to pending status."""
        for step in self.steps:
            step.status = StepStatus.PENDING
            step.completed_at = None
            step.updated_at = datetime.utcnow()
        
        self.status = PlanStatus.NOT_STARTED
        self.updated_at = datetime.utcnow()

    def get_next_step(self) -> Optional[Step]:
        """Get the next pending step."""
        # Sort steps by order
        sorted_steps = sorted(self.steps, key=lambda x: x.order)
        
        for step in sorted_steps:
            if step.status == StepStatus.PENDING:
                # Check if dependencies are met
                if self._dependencies_met(step):
                    return step
        return None

    def _dependencies_met(self, step: Step) -> bool:
        """Check if all dependencies for a step are completed."""
        if not step.depends_on:
            return True
        
        for dep_id in step.depends_on:
            dep_step = self.get_step(dep_id)
            if not dep_step or dep_step.status != StepStatus.COMPLETED:
                return False
        return True

    def _update_plan_status(self) -> None:
        """Update plan status based on step statuses."""
        if not self.steps:
            self.status = PlanStatus.NOT_STARTED
            return
        
        step_statuses = [step.status for step in self.steps]
        
        if all(status == StepStatus.COMPLETED for status in step_statuses):
            self.status = PlanStatus.COMPLETED
        elif any(status == StepStatus.FAILED for status in step_statuses):
            self.status = PlanStatus.FAILED
        elif any(status in [StepStatus.IN_PROGRESS, StepStatus.COMPLETED] for status in step_statuses):
            self.status = PlanStatus.IN_PROGRESS
        else:
            self.status = PlanStatus.NOT_STARTED

    def get_progress(self) -> dict:
        """Get plan progress statistics."""
        total = len(self.steps)
        if total == 0:
            return {
                "total_steps": 0,
                "completed_steps": 0,
                "in_progress_steps": 0,
                "pending_steps": 0,
                "failed_steps": 0,
                "skipped_steps": 0,
                "completion_percentage": 0.0
            }
        
        completed = sum(1 for step in self.steps if step.status == StepStatus.COMPLETED)
        in_progress = sum(1 for step in self.steps if step.status == StepStatus.IN_PROGRESS)
        pending = sum(1 for step in self.steps if step.status == StepStatus.PENDING)
        failed = sum(1 for step in self.steps if step.status == StepStatus.FAILED)
        skipped = sum(1 for step in self.steps if step.status == StepStatus.SKIPPED)
        
        completion_percentage = (completed / total) * 100 if total > 0 else 0
        
        return {
            "total_steps": total,
            "completed_steps": completed,
            "in_progress_steps": in_progress,
            "pending_steps": pending,
            "failed_steps": failed,
            "skipped_steps": skipped,
            "completion_percentage": round(completion_percentage, 2)
        }
