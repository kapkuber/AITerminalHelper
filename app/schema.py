from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional

class Host(BaseModel):
    ip: Optional[str] = None
    mac: Optional[str] = None
    hostnames: List[str] = Field(default_factory=list)

class NmapSummary(BaseModel):
    hosts: List[Host] = Field(default_factory=list)

class NextStep(BaseModel):
    type: str
    cmd: str
    reason: str

class DeviceIdent(BaseModel):
    ip: str
    ident: str
    evidence: str
    confidence: str

class AIResponse(BaseModel):
    devices: List[DeviceIdent] = Field(default_factory=list)
    next_steps: List[NextStep] = Field(default_factory=list)
    notes: Optional[str] = None
