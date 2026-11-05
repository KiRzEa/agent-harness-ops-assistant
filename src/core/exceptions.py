class InvalidObjectiveError(ValueError):
    pass


class RunNotFoundError(LookupError):
    pass


class ApprovalConflictError(RuntimeError):
    pass
