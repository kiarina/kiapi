class MemoryBudgetError(RuntimeError):
    """Target model can't fit within the budget even after evicting all others."""
