"""Small server-side form validation, independent of frontend libraries."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class Field:
    required: bool = True
    kind: str = "text"
    min_length: int = 0
    max_length: int = 200
    minimum: int | Decimal | None = None
    maximum: int | Decimal | None = None
    choices: tuple[str, ...] = ()
    multiple: bool = False

    def __post_init__(self):
        if self.kind not in ("text", "integer", "decimal", "boolean"):
            raise ValueError("Unknown form field kind")
        if not 0 <= self.min_length <= self.max_length:
            raise ValueError("Invalid field lengths")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("Invalid numeric limits")

    def parse(self, raw: str):
        value = raw.strip()
        if not value:
            if self.required:
                raise ValueError("This field is required.")
            return None
        if not self.min_length <= len(value) <= self.max_length:
            raise ValueError(f"Use between {self.min_length} and {self.max_length} characters.")
        if self.choices and value not in self.choices:
            raise ValueError("Select an available choice.")
        try:
            if self.kind == "integer":
                result: Any = int(value)
            elif self.kind == "decimal":
                result = Decimal(value)
                if not result.is_finite():
                    raise ValueError("Enter a finite number.")
            elif self.kind == "boolean":
                if value not in ("true", "false", "1", "0", "on", "off"):
                    raise ValueError("Enter a boolean value.")
                result = value in ("true", "1", "on")
            else:
                result = value
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Enter a valid {self.kind} value.") from exc
        if self.kind in ("integer", "decimal") and (
            (self.minimum is not None and result < self.minimum)
            or (self.maximum is not None and result > self.maximum)
        ):
            raise ValueError("Number is outside the allowed range.")
        return result


@dataclass
class FormResult:
    values: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not self.errors


class Form:
    def __init__(self, **fields: Field):
        self.fields = fields

    def validate(self, body: Any) -> FormResult:
        result = FormResult()
        if not isinstance(body, dict):
            result.errors["_form"] = "Submit a form object."
            return result
        for name, definition in self.fields.items():
            supplied = body.get(name, [])
            values = supplied if isinstance(supplied, list) else [supplied]
            result.values[name] = values if definition.multiple else (values[0] if values else "")
            try:
                if any(not isinstance(value, str) for value in values):
                    raise ValueError("Submit text values.")
                if not definition.multiple and len(values) > 1:
                    raise ValueError("Submit only one value.")
                if definition.multiple:
                    if not values and definition.required:
                        raise ValueError("This field is required.")
                    result.data[name] = [definition.parse(value) for value in values]
                else:
                    result.data[name] = definition.parse(values[0] if values else "")
            except ValueError as exc:
                result.errors[name] = str(exc)
        return result
