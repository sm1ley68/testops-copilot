from typing import Optional
import httpx
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from app.agents.coordinator import CoordinatorAgent
from app.agents.requirements_agent import RequirementsAgent
from app.agents.html_agent import HtmlAnalysisAgent
from app.agents.allure_code_generator import AllureCodeGenerator
from app.models import CoverageReport, TestSuite
from app.agents.automation_agent import AutomationAgent

router = APIRouter(prefix="/generation", tags=["generation"])

coordinator = CoordinatorAgent()


class UiSourcePayload(BaseModel):
    url: Optional[HttpUrl] = None
    html: Optional[str] = None
    requirements_text: Optional[str] = None


class ApiSpecPayload(BaseModel):
    swagger_url: Optional[str] = None  # URL на swagger.json/yaml
    swagger_text: Optional[str] = None  # Или текст спецификации
    requirements_text: Optional[str] = None  # Дополнительные требования


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


@router.post("/allure-code/ui", response_model=dict)
async def generate_ui_allure_code(payload: UiSourcePayload):
    """
    Генерирует ручные тест-кейсы в формате Allure TestOps as Code для UI.

    Входные данные:
    - url: URL сайта (например https://cloud.ru/calculator)
    - html: HTML страницы (опционально)
    - requirements_text: Дополнительные требования

    Выход:
    - Python код в формате Allure TestOps as Code (минимум 15 тест-кейсов)
    """
    import traceback
    try:
        print("[DEBUG] ===== Starting UI Allure TestOps as Code generation =====")
        print(f"[DEBUG] url={payload.url}, html_len={len(payload.html or '')}")

        # 1. Парсим HTML
        html_agent = HtmlAnalysisAgent()
        ui_model = await html_agent.analyze(
            url=str(payload.url) if payload.url else None,
            html=payload.html
        )
        print(f"[DEBUG] UI model parsed: {len(ui_model.pages)} pages")

        # 2. Генерируем тест-кейсы
        requirements_agent = RequirementsAgent()
        test_suite = await requirements_agent.generate_from_ui_model(ui_model)
        print(f"[DEBUG] Generated {len(test_suite.cases)} test cases")

        # 3. Генерируем Allure TestOps as Code
        allure_generator = AllureCodeGenerator()
        allure_code = allure_generator.generate_allure_code(test_suite)
        print(f"[DEBUG] Allure code generated: {len(allure_code)} characters")

        return {
            "allure_code": allure_code,
            "test_count": len(test_suite.cases),
            "suite_name": test_suite.name,
            "format": "Allure TestOps as Code",
            "url": str(payload.url) if payload.url else "from HTML"
        }

    except Exception as e:
        print(f"[ERROR] Failed to generate UI Allure code: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Allure code: {str(e)}"
        )


@router.post("/api/vms", response_model=dict)
async def generate_api_vm_test_cases(payload: ApiSpecPayload):
    """
    Генерирует ручные тест-кейсы для REST API на основе OpenAPI/Swagger спецификации.

    Пользователь может передать:
    - swagger_url: URL на swagger.json/yaml (например https://compute.api.cloud.ru/swagger.json)
    - swagger_text: Текст OpenAPI спецификации целиком
    - requirements_text: Дополнительные требования (необязательно)

    Если ничего не передано - используется дефолтная спецификация Cloud.ru VMs API.

    Генерирует минимум 15 тест-кейсов с покрытием CRUD, auth, errors.
    """

    try:
        print("[DEBUG] ===== Starting API test case generation =====")
        print(f"[DEBUG] swagger_url={payload.swagger_url}")
        print(f"[DEBUG] swagger_text length={len(payload.swagger_text or '')}")
        print(f"[DEBUG] requirements_text={payload.requirements_text}")

        requirements_agent = RequirementsAgent()

        if payload.swagger_url or payload.swagger_text:
            result = await requirements_agent.generate_from_api_spec(
                swagger_url=payload.swagger_url,
                swagger_text=payload.swagger_text,
                requirements_text=payload.requirements_text
            )
        else:
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
            result = await requirements_agent.generate_api_test_cases(
                api_specification,
                requirements_text=payload.requirements_text
            )

        print(f"[DEBUG] Result: {len(result.cases)} test cases generated")

        return {
            "test_suite": result.dict(),
            "test_count": len(result.cases),
            "source": payload.swagger_url if payload.swagger_url else (
                "inline spec" if payload.swagger_text else "default Cloud.ru VMs API")
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate API test cases: {str(e)}")


@router.post("/allure-code/api", response_model=dict)
async def generate_api_allure_code(payload: ApiSpecPayload):
    """
    Генерирует ручные тест-кейсы в формате Allure TestOps as Code для API.

    Входные данные:
    - swagger_url: URL на swagger.json/yaml
    - swagger_text: Текст OpenAPI спецификации
    - requirements_text: Дополнительные требования

    Выход:
    - Python код в формате Allure TestOps as Code (минимум 15 тест-кейсов)
    """
    import traceback
    try:
        print("[DEBUG] ===== Starting API Allure TestOps as Code generation =====")
        print(f"[DEBUG] swagger_url={payload.swagger_url}")
        print(f"[DEBUG] swagger_text length={len(payload.swagger_text or '')}")

        requirements_agent = RequirementsAgent()

        # Генерируем тест-кейсы из спецификации
        if payload.swagger_url or payload.swagger_text:
            test_suite = await requirements_agent.generate_from_api_spec(
                swagger_url=payload.swagger_url,
                swagger_text=payload.swagger_text,
                requirements_text=payload.requirements_text
            )
        else:
            # Дефолтная спецификация Cloud.ru VMs API
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
"""
            test_suite = await requirements_agent.generate_api_test_cases(
                api_specification,
                requirements_text=payload.requirements_text
            )

        print(f"[DEBUG] Generated {len(test_suite.cases)} test cases")

        # Генерируем Allure TestOps as Code
        allure_generator = AllureCodeGenerator()
        allure_code = allure_generator.generate_allure_code(test_suite)
        print(f"[DEBUG] Allure code generated: {len(allure_code)} characters")

        return {
            "allure_code": allure_code,
            "test_count": len(test_suite.cases),
            "suite_name": test_suite.name,
            "format": "Allure TestOps as Code",
            "source": payload.swagger_url if payload.swagger_url else (
                "inline spec" if payload.swagger_text else "default Cloud.ru VMs API"
            )
        }

    except Exception as e:
        print(f"[ERROR] Failed to generate API Allure code: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Allure code: {str(e)}"
        )


@router.post("/automation/e2e", response_model=dict)
async def generate_e2e_automation(
        test_suite: TestSuite,
        base_url: str
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
async def generate_api_automation(payload: ApiSpecPayload):
    """
    Генерирует pytest из Swagger/OpenAPI спецификации.
    Парсит реальный Swagger и создаёт тест для КАЖДОГО эндпоинта.
    """

    try:
        if not payload.swagger_url:
            raise HTTPException(
                status_code=400,
                detail="swagger_url is required"
            )

        swagger_url = payload.swagger_url
        print(f"[DEBUG] Downloading Swagger from: {swagger_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(swagger_url)
            resp.raise_for_status()
            swagger_data = resp.json()

        schemes = swagger_data.get('schemes', ['https'])
        host = swagger_data.get('host', '')
        base_path = swagger_data.get('basePath', '')
        base_url = f"{schemes[0]}://{host}{base_path}"

        print(f"[DEBUG] Parsed base_url: {base_url}")
        print(f"[DEBUG] Found {len(swagger_data.get('paths', {}))} endpoints")

        agent = AutomationAgent()
        pytest_code = await agent.generate_from_swagger(swagger_data, base_url)

        return {
            "pytest_code": pytest_code,
            "test_count": len(swagger_data.get('paths', {})),
            "base_url": base_url,
            "swagger_url": swagger_url
        }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Swagger: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
