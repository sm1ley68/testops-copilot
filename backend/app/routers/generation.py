from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from app.agents.coordinator import CoordinatorAgent
from app.agents.requirements_agent import RequirementsAgent
from app.models import CoverageReport, TestSuite
from app.agents.automation_agent import AutomationAgent

router = APIRouter(prefix="/generation", tags=["generation"])

coordinator = CoordinatorAgent()


class UiSourcePayload(BaseModel):
    url: Optional[HttpUrl] = None
    html: Optional[str] = None
    requirements_text: Optional[str] = None


@router.post("/ui/full", response_model=CoverageReport)
async def generate_full_ui_flow(payload: UiSourcePayload):
    import traceback
    try:
        print(f"[DEBUG] Starting full_ui_flow")
        print(f"[DEBUG] url={payload.url}, html_len={len(payload.html or '')}, req_text={payload.requirements_text}")

        report = await coordinator.full_ui_flow(
            url=str(payload.url) if payload.url else None,
            html=payload.html,
            requirements_text=payload.requirements_text,
        )

        print(f"[DEBUG] Success!")
        return report

    except Exception as exc:
        print(f"[ERROR] Exception in /ui/full: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/vms", response_model=TestSuite)
async def generate_api_vm_test_cases():
    """
    Генерирует ручные тест-кейсы для Cloud.ru Evolution Compute API.
    Покрывает VMs, Disks, Flavors endpoints согласно кейсу 2 из ТЗ.

    Генерирует минимум 15 тест-кейсов с покрытием:
    - CRUD операции для VMs (create, read, update, delete, start, stop, reboot)
    - CRUD операции для Disks + attach/detach к VM
    - GET операции для Flavors (список и детали конфигураций)
    - Аутентификация (Bearer token) и обработка ошибок
    - Позитивные и негативные сценарии
    """

    api_specification = """
# Cloud.ru Evolution Compute API v3

## Base Information
- Base URL: https://compute.api.cloud.ru
- Authentication: Bearer token (userPlaneApiToken in Authorization header)
- Content-Type: application/json
- ID Format: All resource IDs must be in UUIDv4 format

## API Sections

### 1. Virtual Machines (VMs)
- GET /vms - Get list of all virtual machines
- POST /vms - Create new virtual machine (requires: name, flavor_id, image_id)
- GET /vms/{vm_id} - Get specific VM details by ID
- PATCH /vms/{vm_id} - Update VM configuration (name, flavor, etc.)
- DELETE /vms/{vm_id} - Delete virtual machine
- POST /vms/{vm_id}/start - Start stopped VM
- POST /vms/{vm_id}/stop - Stop running VM
- POST /vms/{vm_id}/reboot - Reboot running VM

### 2. Disks
- GET /disks - Get list of all disks
- POST /disks - Create new disk (requires: name, size, availability_zone)
- GET /disks/{disk_id} - Get specific disk details by ID
- PATCH /disks/{disk_id} - Update disk configuration (name, size)
- DELETE /disks/{disk_id} - Delete disk (only if not attached to VM)
- POST /disks/{disk_id}/attach - Attach disk to VM (requires: vm_id in body)
- POST /disks/{disk_id}/detach - Detach disk from VM

### 3. Flavors (Instance Configurations)
- GET /flavors - Get list of available instance configurations
- GET /flavors/{flavor_id} - Get specific flavor details (CPU, RAM, disk, network specs)

## Common Response Codes
- 200 OK - Successful GET/PATCH/action
- 201 Created - Successful POST (resource created)
- 204 No Content - Successful DELETE
- 400 Bad Request - Invalid request data or parameters
- 401 Unauthorized - Missing or invalid authentication token
- 404 Not Found - Resource with specified ID does not exist
- 409 Conflict - Operation not allowed in current state (e.g., delete attached disk)
- 500 Internal Server Error - Server-side error

## Error Response Format
All errors return ExceptionSchema format:
{
  "code": "ERROR_CODE",
  "message": "Human-readable error description"
}

## Example Requests

### Create VM:
POST /vms
{
  "name": "test-vm-01",
  "flavor_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_id": "660e8400-e29b-41d4-a716-446655440000"
}

### Attach Disk:
POST /disks/{disk_id}/attach
{
  "vm_id": "770e8400-e29b-41d4-a716-446655440000"
}
"""

    try:
        print("[DEBUG] ===== Starting API test case generation =====")
        requirements_agent = RequirementsAgent()
        print(f"[DEBUG] Agent created: {requirements_agent}")
        result = await requirements_agent.generate_api_test_cases(api_specification)
        print(f"[DEBUG] Result type: {type(result)}, cases: {len(result.cases) if result else 'None'}")
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate API test cases: {str(e)}")


@router.post("/automation/e2e", response_model=dict)
async def generate_e2e_automation(
        test_suite: TestSuite,
        base_url: str = "https://calculator.net"
):
    try:
        agent = AutomationAgent()
        pytest_code = await agent.generate_e2e_tests(test_suite, base_url)

        return {
            "pytest_code": pytest_code,
            "test_count": len(test_suite.cases),
            "base_url": base_url
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate E2E tests: {str(e)}")


@router.post("/automation/api", response_model=dict)
async def generate_api_automation(
        test_suite: TestSuite,
        base_url: str = "https://compute.api.cloud.ru"
):
    try:
        agent = AutomationAgent()
        pytest_code = await agent.generate_api_tests(test_suite, base_url)

        return {
            "pytest_code": pytest_code,
            "test_count": len(test_suite.cases),
            "base_url": base_url
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate API tests: {str(e)}")