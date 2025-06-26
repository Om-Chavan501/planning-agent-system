# Planning Agent System

A FastAPI-based planning and execution management system designed for planning engineers and AI agents to manage actionable to-do lists and track their progress using CouchDB.

## Overview

This system is designed to be used by:
- **Planning Engineers**: Who need to create and manage detailed project plans
- **AI Planning Agents**: That generate structured plans programmatically
- **Execution Agents**: That track and update progress on existing plans

The system does **not** include automatic step generation - all steps must be explicitly provided by the user or calling system.

## Features

- **Planning Agent**: Create and regenerate plans from user-provided steps
- **Execution Agent**: Track and update step progress
- **Management APIs**: Full CRUD operations for plans and steps
- **Progress Tracking**: Real-time progress monitoring and analytics
- **CouchDB Integration**: Persistent storage with embedded document structure

## Quick Start

### Prerequisites

- Python 3.8+
- CouchDB server
- pip

### Installation

1. Clone or download the project
2. Navigate to the planning_agent directory
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.template .env
   # Edit .env with your CouchDB credentials
   ```

5. Run the application:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000` with documentation at `http://localhost:8000/docs`.

## Testing

A test script is provided to verify all API endpoints:

```bash
python test_api.py
```

This will test:
- Health check
- Plan creation with steps
- Plan retrieval
- Step status updates
- Plan regeneration

## Configuration

Create a `.env` file with the following variables:

```env
COUCH_URL=http://couchdb.genai-dev.kpit.com
COUCH_USER=admin
COUCH_PASS=your_password_here
COUCH_DATABASE=plans
LOG_LEVEL=INFO
```

## API Documentation

### Planning Agent APIs

- `POST /api/plans` - Create new plan with user-provided steps
- `PUT /api/plans/{plan_id}/regenerate` - Regenerate plan with new user-provided steps

### Execution Agent APIs

- `GET /api/plans/{plan_id}` - Get specific plan with all steps
- `GET /api/plans` - Get all plans with filtering
- `PUT /api/plans/{plan_id}/steps/{step_id}` - Update step status
- `GET /api/plans/{plan_id}/next-step` - Get next pending step

### Management APIs

- `PUT /api/plans/{plan_id}` - Update plan metadata
- `DELETE /api/plans/{plan_id}` - Delete plan
- `POST /api/plans/{plan_id}/steps` - Add new step
- `DELETE /api/plans/{plan_id}/steps/{step_id}` - Delete step
- `PUT /api/plans/{plan_id}/steps/{step_id}/skip` - Skip step

### Helper APIs

- `GET /api/plans/{plan_id}/progress` - Get progress summary
- `GET /api/plans/{plan_id}/summary` - Get plan summary
- `POST /api/plans/{plan_id}/reset` - Reset all steps to pending
- `GET /api/health` - Health check

## Example Usage

### Create a Plan

```bash
curl -X POST "http://localhost:8000/api/plans" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Website Launch",
    "description": "Launch a new marketing website with proper planning and execution.",
    "user_id": "user123",
    "steps": [
      {
        "description": "Design the website UI and UX",
        "order": 1,
        "notes": "Focus on modern, responsive design"
      },
      {
        "description": "Develop the frontend application",
        "order": 2,
        "depends_on": [],
        "notes": "Use React or Vue.js"
      },
      {
        "description": "Setup hosting infrastructure",
        "order": 3,
        "depends_on": [],
        "notes": "Consider AWS or Vercel"
      },
      {
        "description": "Configure domain and DNS settings",
        "order": 4,
        "depends_on": [],
        "notes": "Setup SSL certificate"
      },
      {
        "description": "Deploy and test the application",
        "order": 5,
        "depends_on": [],
        "notes": "Run full QA testing"
      }
    ]
  }'
```

### Update Step Status

```bash
curl -X PUT "http://localhost:8000/api/plans/{plan_id}/steps/{step_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "notes": "Successfully completed the task"
  }'
```

### Regenerate a Plan

```bash
curl -X PUT "http://localhost:8000/api/plans/{plan_id}/regenerate" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated website launch plan with additional security focus",
    "steps": [
      {
        "description": "Conduct security audit and planning",
        "order": 1,
        "notes": "Include penetration testing"
      },
      {
        "description": "Design secure UI/UX with accessibility",
        "order": 2,
        "notes": "Follow WCAG guidelines"
      },
      {
        "description": "Develop frontend with security best practices",
        "order": 3,
        "notes": "Input validation and XSS protection"
      },
      {
        "description": "Setup secure hosting with monitoring",
        "order": 4,
        "notes": "Include WAF and DDoS protection"
      },
      {
        "description": "Deploy with comprehensive testing",
        "order": 5,
        "notes": "Security and performance testing"
      }
    ]
  }'
```

### Get Next Step

```bash
curl "http://localhost:8000/api/plans/{plan_id}/next-step"
```

## Data Models

### Plan Document Structure

```json
{
  "_id": "plan_uuid",
  "_rev": "revision",
  "plan_id": "uuid",
  "name": "string",
  "description": "string",
  "status": "not_started|in_progress|completed|paused|failed",
  "user_id": "string",
  "created_at": "iso_datetime",
  "updated_at": "iso_datetime",
  "steps": [
    {
      "step_id": "uuid",
      "order": 1,
      "description": "string",
      "status": "pending|in_progress|completed|failed|skipped",
      "depends_on": [],
      "notes": "string",
      "created_at": "iso_datetime",
      "updated_at": "iso_datetime",
      "completed_at": "iso_datetime"
    }
  ]
}
```

## Architecture

The application follows a clean architecture pattern:

- **main.py**: FastAPI routes and HTTP layer
- **models.py**: Pydantic models for validation and serialization
- **services.py**: Business logic layer
- **database.py**: CouchDB data access layer
- **config.py**: Configuration management

## Features

### User-Provided Step Management

The system accepts explicit steps from users (planning engineers or AI agents) rather than generating them automatically. This ensures full control over the planning process.

### Automatic Status Management

Plan status is automatically updated based on step completion:
- `not_started`: No steps completed
- `in_progress`: Some steps completed/in progress
- `completed`: All steps completed
- `failed`: Any step failed

### Dependency Management

Steps can depend on other steps, and the system tracks dependencies when determining the next step to execute.

### Progress Tracking

Real-time progress analytics including completion percentages and step status breakdowns.

## Development

### Project Structure

```
planning_agent/
├── main.py                 # FastAPI app entry point
├── config.py              # Configuration settings
├── models.py              # Pydantic models
├── database.py            # CouchDB operations
├── services.py            # Business logic
├── requirements.txt       # Dependencies
├── .env.template          # Environment template
└── README.md              # This file
```

### Running in Development

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

The API documentation provides an interactive testing interface at `/docs`.

## Error Handling

The application includes comprehensive error handling:
- HTTP status codes for different scenarios
- Detailed error messages
- Logging for debugging
- Graceful handling of database connection issues

## License

This project is developed for planning and execution management use cases.
