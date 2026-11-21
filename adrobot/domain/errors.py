class Problem(Exception):
    def __init__(self, message, status=400, code="error"):
        super().__init__(message)
        self.status = status
        self.code = code
