"""
cascade.reflection
==================
Post-analysis reflection layer for CASCADE.

Converts the three-artefact triple
  (original_code, synthesized_code, original_doc)
plus an optional synthesized_doc into:
  - a typed InconsistencyType label
  - a developer-facing natural-language explanation
  - a precision_confidence score

Public API
----------
    from cascade.reflection import (
        Reflector,
        ReflectionResult,
        InconsistencyType,
        DiffReflector,
        LLMSemanticReflector,
        ChainedReflector,
        ReflectionPipeline,
    )

Extension
---------
To add a custom reflector:
  1. Subclass Reflector and implement reflect().
  2. Drop the file in this package.
  3. Reference it by class name in your CASCADE config under "reflection.name".
"""

from .Reflector import InconsistencyType, ReflectionResult, Reflector
from .DiffReflector import DiffReflector
from .LLMSemanticReflector import LLMSemanticReflector
from .ChainedReflector import ChainedReflector
from .ReflectionPipeline import ReflectionPipeline

__all__ = [
    "Reflector",
    "ReflectionResult",
    "InconsistencyType",
    "DiffReflector",
    "LLMSemanticReflector",
    "ChainedReflector",
    "ReflectionPipeline",
]