from typing import List, Literal, Optional
from pydantic import BaseModel


class UiElement(BaseModel):
    id: Optional[str] = None
    type: Literal["button", "input", "select", "checkbox", "link", "text", "other"]
    name: str
    locator: str
    role: Optional[str] = None


class UiPage(BaseModel):
    url: str
    name: str
    elements: List[UiElement] = []
    main_flows: List[str] = []


class UiModel(BaseModel):
    pages: List[UiPage]


class TestCase(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    steps: List[str]
    expected_result: str
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "NORMAL", "LOW"] = "NORMAL"
    tags: List[str] = []


class TestSuite(BaseModel):
    name: str
    cases: List[TestCase]


class AutomatedTest(BaseModel):
    id: Optional[str] = None
    kind: Literal["ui_e2e", "api"]
    path: str
    code: str


class CoverageReport(BaseModel):
    covered_features: List[str]
    missing_features: List[str]
    duplicates: List[str]
    summary: str


class ValidationIssue(BaseModel):
    test_case_id: str
    test_case_title: str
    severity: Literal["critical", "warning", "info"]
    issue: str
    recommendation: str


class ValidationReport(BaseModel):
    total_cases: int
    passed: int
    failed: int
    issues: List[ValidationIssue]
    summary: str
