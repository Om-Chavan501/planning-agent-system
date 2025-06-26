"""
FastAPI application for Planning Agent System.
"""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models import (
    CreatePlanRequest, UpdatePlanRequest, UpdateStepRequest, AddStepRequest,
    RegeneratePlanRequest, PlanResponse, PlanSummaryResponse, ProgressResponse,
    NextStepResponse, HealthResponse, StepResponse, PlanStatus, StepStatus
)
from services import PlanningService, ExecutionService, ManagementService
from database import db_connection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Utility functions
def plan_to_response(plan) -> PlanResponse:
    """Convert Plan model to PlanResponse."""
    steps = [
        StepResponse(
            step_id=step.step_id,
            order=step.order,
            description=step.description,
            status=step.status,
            depends_on=step.depends_on,
            notes=step.notes,
            created_at=step.created_at,
            updated_at=step.updated_at,
            completed_at=step.completed_at
        )
        for step in plan.steps
    ]
    
    return PlanResponse(
        plan_id=plan.plan_id,
        name=plan.name,
        description=plan.description,
        status=plan.status,
        user_id=plan.user_id,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        steps=steps
    )

def plan_to_summary(plan) -> PlanSummaryResponse:
    """Convert Plan model to PlanSummaryResponse."""
    progress = plan.get_progress()
    
    return PlanSummaryResponse(
        plan_id=plan.plan_id,
        name=plan.name,
        description=plan.description,
        status=plan.status,
        user_id=plan.user_id,
        total_steps=progress["total_steps"],
        completed_steps=progress["completed_steps"],
        pending_steps=progress["pending_steps"],
        created_at=plan.created_at,
        updated_at=plan.updated_at
    )

# Planning Agent APIs
@app.post("/api/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(request: CreatePlanRequest):
    """Create a new plan with user-provided steps."""
    try:
        plan = PlanningService.create_plan_with_steps(
            name=request.name,
            description=request.description,
            user_id=request.user_id,
            steps=request.steps
        )
        return plan_to_response(plan)
    except Exception as e:
        logger.error(f"Failed to create plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create plan"
        )

@app.put("/api/plans/{plan_id}/regenerate", response_model=PlanResponse)
async def regenerate_plan(plan_id: str, request: RegeneratePlanRequest):
    """Regenerate/update existing plan with new user-provided steps."""
    try:
        plan = PlanningService.regenerate_plan(
            plan_id, 
            request.description, 
            request.steps
        )
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        return plan_to_response(plan)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate plan"
        )

# Execution Agent APIs
@app.get("/api/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    """Get specific to-do list with all steps."""
    try:
        plan = ExecutionService.get_plan(plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        return plan_to_response(plan)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan"
        )

@app.get("/api/plans", response_model=List[PlanSummaryResponse])
async def get_plans(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[PlanStatus] = Query(None, description="Filter by plan status"),
    name: Optional[str] = Query(None, description="Filter by plan name (case insensitive)")
):
    """Get all plans with optional filtering."""
    try:
        plans = ExecutionService.get_plans(
            user_id=user_id,
            status=status,
            name_filter=name
        )
        return [plan_to_summary(plan) for plan in plans]
    except Exception as e:
        logger.error(f"Failed to get plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plans"
        )

@app.put("/api/plans/{plan_id}/steps/{step_id}", response_model=StepResponse)
async def update_step_status(plan_id: str, step_id: str, request: UpdateStepRequest):
    """Update step status and notes."""
    try:
        success = ExecutionService.update_step_status(
            plan_id=plan_id,
            step_id=step_id,
            status=request.status,
            notes=request.notes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan or step not found"
            )
        
        # Get updated plan to return the step
        plan = ExecutionService.get_plan(plan_id)
        step = plan.get_step(step_id)
        
        return StepResponse(
            step_id=step.step_id,
            order=step.order,
            description=step.description,
            status=step.status,
            depends_on=step.depends_on,
            notes=step.notes,
            created_at=step.created_at,
            updated_at=step.updated_at,
            completed_at=step.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update step {step_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update step"
        )

@app.get("/api/plans/{plan_id}/next-step", response_model=NextStepResponse)
async def get_next_step(plan_id: str):
    """Get next pending step."""
    try:
        step = ExecutionService.get_next_step(plan_id)
        
        if step:
            step_response = StepResponse(
                step_id=step.step_id,
                order=step.order,
                description=step.description,
                status=step.status,
                depends_on=step.depends_on,
                notes=step.notes,
                created_at=step.created_at,
                updated_at=step.updated_at,
                completed_at=step.completed_at
            )
            return NextStepResponse(
                step=step_response,
                message="Next step found"
            )
        else:
            return NextStepResponse(
                step=None,
                message="No pending steps found or plan not found"
            )
            
    except Exception as e:
        logger.error(f"Failed to get next step for plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get next step"
        )

# Management APIs
@app.put("/api/plans/{plan_id}", response_model=PlanResponse)
async def update_plan_metadata(plan_id: str, request: UpdatePlanRequest):
    """Update plan metadata."""
    try:
        success = ManagementService.update_plan_metadata(
            plan_id=plan_id,
            name=request.name,
            description=request.description,
            status=request.status
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        # Return updated plan
        plan = ExecutionService.get_plan(plan_id)
        return plan_to_response(plan)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update plan"
        )

@app.delete("/api/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: str):
    """Delete plan."""
    try:
        success = ManagementService.delete_plan(plan_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete plan"
        )

@app.post("/api/plans/{plan_id}/steps", response_model=StepResponse, status_code=status.HTTP_201_CREATED)
async def add_step(plan_id: str, request: AddStepRequest):
    """Add/insert new step to plan."""
    try:
        step_id = ManagementService.add_step_to_plan(
            plan_id=plan_id,
            description=request.description,
            order=request.order,
            depends_on=request.depends_on,
            notes=request.notes
        )
        
        if not step_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        # Get the created step
        plan = ExecutionService.get_plan(plan_id)
        step = plan.get_step(step_id)
        
        return StepResponse(
            step_id=step.step_id,
            order=step.order,
            description=step.description,
            status=step.status,
            depends_on=step.depends_on,
            notes=step.notes,
            created_at=step.created_at,
            updated_at=step.updated_at,
            completed_at=step.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add step to plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add step"
        )

@app.delete("/api/plans/{plan_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(plan_id: str, step_id: str):
    """Delete step from plan."""
    try:
        success = ManagementService.delete_step_from_plan(plan_id, step_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan or step not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete step {step_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete step"
        )

@app.put("/api/plans/{plan_id}/steps/{step_id}/skip", response_model=StepResponse)
async def skip_step(plan_id: str, step_id: str):
    """Skip step (mark as skipped)."""
    try:
        success = ExecutionService.skip_step(plan_id, step_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan or step not found"
            )
        
        # Get updated step
        plan = ExecutionService.get_plan(plan_id)
        step = plan.get_step(step_id)
        
        return StepResponse(
            step_id=step.step_id,
            order=step.order,
            description=step.description,
            status=step.status,
            depends_on=step.depends_on,
            notes=step.notes,
            created_at=step.created_at,
            updated_at=step.updated_at,
            completed_at=step.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to skip step {step_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to skip step"
        )

# Helper APIs
@app.get("/api/plans/{plan_id}/progress", response_model=ProgressResponse)
async def get_plan_progress(plan_id: str):
    """Get plan progress summary."""
    try:
        plan = ExecutionService.get_plan(plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        progress = plan.get_progress()
        
        return ProgressResponse(
            plan_id=plan.plan_id,
            total_steps=progress["total_steps"],
            completed_steps=progress["completed_steps"],
            in_progress_steps=progress["in_progress_steps"],
            pending_steps=progress["pending_steps"],
            failed_steps=progress["failed_steps"],
            skipped_steps=progress["skipped_steps"],
            completion_percentage=progress["completion_percentage"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get progress for plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plan progress"
        )

@app.get("/api/plans/{plan_id}/summary", response_model=PlanSummaryResponse)
async def get_plan_summary(plan_id: str):
    """Get plan summary."""
    try:
        plan = ExecutionService.get_plan(plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        return plan_to_summary(plan)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get summary for plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get plan summary"
        )

@app.post("/api/plans/{plan_id}/reset", response_model=PlanResponse)
async def reset_plan_steps(plan_id: str):
    """Reset all steps to pending status."""
    try:
        success = ManagementService.reset_plan_steps(plan_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        # Return updated plan
        plan = ExecutionService.get_plan(plan_id)
        return plan_to_response(plan)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset plan"
        )

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        database_connected = db_connection.is_connected()
        
        return HealthResponse(
            status="healthy" if database_connected else "unhealthy",
            timestamp=datetime.utcnow(),
            database_connected=database_connected
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            database_connected=False
        )

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("Starting Planning Agent System")
    
    # Test database connection
    try:
        if db_connection.is_connected():
            logger.info("Database connection established successfully")
        else:
            logger.error("Failed to establish database connection")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("Shutting down Planning Agent System")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
