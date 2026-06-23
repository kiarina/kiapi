class SetupRequiredError(RuntimeError):
    """Raised when a model is requested before its setup resources are ready."""
