from enum import Enum


class RequestType(Enum):
    REUSABLE = "Многоразовая"
    DISPOSABLE = "Одноразовая"


class Value(Enum):
    DEFAULT = 1


class RequestStatus(Enum):
    APPROVE = "СОГЛАСОВАНИЕ"
    ALLOWED = "ОДОБРЕНА"
    REJECTED = "ОТКЛОНЕНА"
    WITHDRAWN = "ОТОЗВАНА"
    CONSIDERATION = "РАССМОТРЕНИЕ"
    CLOSED = "ЗАКРЫТА"
    PASSAPPROVAL = "ПРОШЛА СОГЛАСОВАНИЕ"
    UNPASSAPPROVAL = "НЕ ПРОШЛА СОГЛАСОВАНИЕ"


class PassageReportsMode(str, Enum):
    CARS = "Автомобили"
    VISITORS = "Посетители"
    SPEC_TRANSPORT = "Спецтранспорт"
    SEARCH_CAR = "ПОИСК"
    SEARCH_VISITOR = "ПОИСК"
    SEARCH_SPECTRANSPORT = "ПОИСК"


class OnTerritoryMode(str, Enum):
    CARS = "Автомобили"
    SPEC_TRANSPORT = "Спецтранспорт"


class Scopes(Enum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    LIMITED_ADMIN = "limited_admin"
    REQUESTER = "requester"
    MONITORING = "monitoring"
    CURRENT = "current_user"
