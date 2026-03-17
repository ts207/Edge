from __future__ import annotations

class EdgeError(Exception):
    """Base exception for all project-specific errors."""
    pass

class ContractViolationError(EdgeError):
    """Raised when a data contract or structural invariant is violated."""
    pass

class StageExecutionError(EdgeError):
    """Raised when a major pipeline stage or service fails during execution."""
    pass

class ConfigurationError(EdgeError):
    """Raised when configuration or specifications are invalid or missing."""
    pass

class DataIntegrityError(EdgeError):
    """Raised when data source or artifact integrity checks fail."""
    pass

class PromotionDecisionError(EdgeError):
    """Raised when promotion logic cannot reach a valid decision due to data or logic issues."""
    pass

class ArtifactWriteError(EdgeError):
    """Raised when generated artifacts cannot be written or verified."""
    pass
