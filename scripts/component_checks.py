"""Checks on component records that JSON Schema cannot express."""

from __future__ import annotations


def parameter_reference_errors(component: dict) -> list[str]:
    """Return one message per length given as a parameter name the component does not define.

    Placement elevation and clearance width and depth may name one of the
    component's own parameters instead of a number in metres.
    """
    parameters = set(component.get("parameters") or {})
    references: list[tuple[str, object]] = [
        ("placement.elevation", (component.get("placement") or {}).get("elevation")),
    ]
    for index, clearance in enumerate(component.get("clearances") or []):
        references.append((f"clearances[{index}].width", clearance.get("width")))
        references.append((f"clearances[{index}].depth", clearance.get("depth")))
    return [
        f"{component.get('id')}: {where} references unknown parameter '{value}'."
        for where, value in references
        if isinstance(value, str) and value not in parameters
    ]
