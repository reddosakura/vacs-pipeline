from enum import Enum


class Routes(Enum):
    INDEX = "/"
    SUDP_PREFIX = "/sudpapp"
    API_PREFIX = "/api/v1"
    READ_API_PREFIX = "api/v1/read"
    AUTH = "/auth"
    PROC = "/proc"
