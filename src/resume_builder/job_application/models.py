from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PlatformInfo(BaseModel):
    vendor: str
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class WorkflowInfo(BaseModel):
    states: list[str] = Field(default_factory=list)
    current_state: str = ""


class DetectedField(BaseModel):
    selector_hint: str
    canonical: str
    kind: str
    required: bool = False
    mapped_value: str | None = None
    source: str | None = None
    confidence: float = 0.0


class RequiredDocument(BaseModel):
    type: str
    format: str = "pdf"
    source: str | None = None
    ready: bool = False


class MissingInformation(BaseModel):
    canonical: str
    label: str
    reason: str


class UploadStrategy(BaseModel):
    field: str
    method: str = "file_input"
    artifact: str = ""
    auto_parse_expected: bool = False


class BrowserAction(BaseModel):
    step: int
    action: str
    target: str
    value: str = ""


class ValidationStep(BaseModel):
    check: str


class RecoveryRule(BaseModel):
    on: str
    do: str


class Hitl(BaseModel):
    stop_before: str = "Submit"
    status: str = "awaiting_human_review"


class ApplicationPlan(BaseModel):
    platform: PlatformInfo
    workflow: WorkflowInfo
    detected_fields: list[DetectedField] = Field(default_factory=list)
    required_documents: list[RequiredDocument] = Field(default_factory=list)
    missing_information: list[MissingInformation] = Field(default_factory=list)
    upload_strategy: UploadStrategy | None = None
    browser_actions: list[BrowserAction] = Field(default_factory=list)
    validation_steps: list[ValidationStep] = Field(default_factory=list)
    recovery_plan: list[RecoveryRule] = Field(default_factory=list)
    hitl: Hitl = Field(default_factory=Hitl)

    @model_validator(mode="after")
    def enforce_hitl_gate(self) -> ApplicationPlan:
        if self.hitl.stop_before != "Submit":
            raise ValueError(
                f"HITL gate violation: stop_before must be 'Submit', got '{self.hitl.stop_before}'"
            )
        return self
