from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class AuditStep:
    step_name: str
    formula_description: str
    input_snapshot: dict
    output_snapshot: dict


@dataclass(frozen=True)
class EngineResult:
    success: bool
    output: dict
    audit_steps: list[AuditStep]
    warnings: list[str]


class EngineError(Exception):
    def __init__(self, code: str, message: str, recoverable: bool = False):
        self.code = code
        self.message = message
        self.recoverable = recoverable
        super().__init__(message)
