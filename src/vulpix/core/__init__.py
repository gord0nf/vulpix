class VulpixError(Exception):
    message: str
    exit_status: int

    def __init__(self, message: str, exit_status: int = 1):
        self.message = message
        self.exit_status = exit_status
