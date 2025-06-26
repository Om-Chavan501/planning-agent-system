#!/usr/bin/env python3
"""
Test script for the Planning Agent System API endpoints.
Run this after starting the server to verify functionality.
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_create_plan():
    """Test creating a plan with user-provided steps."""
    print("Testing plan creation...")
    
    plan_data = {
        "name": "Test Website Project",
        "description": "A test project for website development",
        "user_id": "test_user_123",
        "steps": [
            {
                "description": "Setup project repository",
                "order": 1,
                "notes": "Initialize Git repo and project structure"
            },
            {
                "description": "Create database schema",
                "order": 2,
                "notes": "Design and implement database tables"
            },
            {
                "description": "Develop API endpoints",
                "order": 3,
                "depends_on": [],
                "notes": "Create RESTful API"
            },
            {
                "description": "Build frontend interface",
                "order": 4,
                "notes": "React-based user interface"
            },
            {
                "description": "Deploy to production",
                "order": 5,
                "notes": "Setup CI/CD pipeline and deploy"
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/api/plans", json=plan_data)
    
    if response.status_code == 201:
        plan = response.json()
        print(f"✅ Plan created successfully: {plan['plan_id']}")
        print(f"   Name: {plan['name']}")
        print(f"   Steps: {len(plan['steps'])}")
        return plan['plan_id']
    else:
        print(f"❌ Failed to create plan: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def test_get_plan(plan_id):
    """Test retrieving a plan."""
    print(f"Testing plan retrieval for {plan_id}...")
    
    response = requests.get(f"{BASE_URL}/api/plans/{plan_id}")
    
    if response.status_code == 200:
        plan = response.json()
        print(f"✅ Plan retrieved successfully")
        print(f"   Status: {plan['status']}")
        print(f"   Steps: {len(plan['steps'])}")
        return plan
    else:
        print(f"❌ Failed to retrieve plan: {response.status_code}")
        return None

def test_update_step_status(plan_id, step_id):
    """Test updating a step status."""
    print(f"Testing step status update...")
    
    update_data = {
        "status": "completed",
        "notes": "Step completed successfully during testing"
    }
    
    response = requests.put(f"{BASE_URL}/api/plans/{plan_id}/steps/{step_id}", json=update_data)
    
    if response.status_code == 200:
        step = response.json()
        print(f"✅ Step updated successfully")
        print(f"   Status: {step['status']}")
        print(f"   Notes: {step['notes']}")
        return True
    else:
        print(f"❌ Failed to update step: {response.status_code}")
        return False

def test_regenerate_plan(plan_id):
    """Test regenerating a plan with new steps."""
    print(f"Testing plan regeneration...")
    
    regenerate_data = {
        "description": "Updated test project with security focus",
        "steps": [
            {
                "description": "Security audit and assessment",
                "order": 1,
                "notes": "Comprehensive security review"
            },
            {
                "description": "Setup secure development environment",
                "order": 2,
                "notes": "Configure security tools and practices"
            },
            {
                "description": "Implement secure authentication",
                "order": 3,
                "notes": "OAuth2 and JWT implementation"
            },
            {
                "description": "Develop secure API with validation",
                "order": 4,
                "notes": "Input validation and rate limiting"
            }
        ]
    }
    
    response = requests.put(f"{BASE_URL}/api/plans/{plan_id}/regenerate", json=regenerate_data)
    
    if response.status_code == 200:
        plan = response.json()
        print(f"✅ Plan regenerated successfully")
        print(f"   New step count: {len(plan['steps'])}")
        print(f"   New description: {plan['description']}")
        return True
    else:
        print(f"❌ Failed to regenerate plan: {response.status_code}")
        return False

def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    
    response = requests.get(f"{BASE_URL}/api/health")
    
    if response.status_code == 200:
        health = response.json()
        print(f"✅ Health check passed")
        print(f"   Status: {health['status']}")
        print(f"   Database connected: {health['database_connected']}")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Planning Agent System API Tests")
    print("=" * 50)
    
    # Test health check first
    if not test_health_check():
        print("❌ Health check failed - server may not be running")
        return
    
    print()
    
    # Test creating a plan
    plan_id = test_create_plan()
    if not plan_id:
        print("❌ Cannot continue tests without a plan")
        return
    
    print()
    
    # Test retrieving the plan
    plan = test_get_plan(plan_id)
    if not plan:
        print("❌ Cannot continue tests without plan data")
        return
    
    print()
    
    # Test updating a step status
    if plan['steps']:
        first_step_id = plan['steps'][0]['step_id']
        test_update_step_status(plan_id, first_step_id)
        print()
    
    # Test regenerating the plan
    test_regenerate_plan(plan_id)
    
    print()
    print("🎉 All tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
