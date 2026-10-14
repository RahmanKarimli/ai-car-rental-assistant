class DomainError(Exception):
    def __init__(self, code: str, detail: str, status: int = 400):
        self.code, self.detail, self.status = code, detail, status
        super().__init__(code)
