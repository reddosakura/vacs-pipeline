import datetime
from pydantic import BaseModel
from typing import Optional, List


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    login: str | None = None
    scopes: list[str] = []


class CarBaseSchema(BaseModel):
    carmodel: str
    govern_num: str
    passed: Optional[bool]
    is_deleted: bool
    date_created: Optional[datetime.datetime] = datetime.datetime.now()
    date_deleted: Optional[datetime.datetime]


class CarCreate(CarBaseSchema):
    req_intr_id: int

    class Config:
        from_attributes = True


class CarSchema(CarBaseSchema):
    id: int
    req_intr_id: int

    class Config:
        from_attributes = True


class VisitorBaseSchema(BaseModel):
    lastname: str
    name: str
    patronymic: str
    passed: Optional[bool]
    is_deleted: bool
    date_created: Optional[datetime.datetime] = datetime.datetime.now()
    date_deleted: Optional[datetime.datetime]


class VisitorCreate(VisitorBaseSchema):
    req_intr_id: int

    class Config:
        from_attributes = True


class VisitorSchema(VisitorBaseSchema):
    id: int
    req_intr_id: int

    class Config:
        from_attributes = True


class MainRequestsBaseSchema(BaseModel):
    creator: str
    type: str
    contract_name: Optional[str]
    organization: Optional[str]
    from_date: datetime.datetime
    to_date: datetime.datetime
    from_time: datetime.time
    to_time: datetime.time
    comment: str
    files: Optional[str]
    created_date: datetime.datetime = datetime.datetime.now()
    status: str
    passcount: int
    passmode: str


class MainRequestsIdSchema(BaseModel):
    id: int

    class Config:
        from_attributes = True


class ApprovalBase(BaseModel):
    lastname: str
    name: str
    patronymic: str
    approval_comments: str
    approval_status: str
    intr_req_id: int
    created_date: datetime.datetime
    # areq: MainRequestsSchema


class ApprovalSchema(ApprovalBase):
    id: int


class MainRequestsSchema(MainRequestsBaseSchema):
    id: int
    internal_req_id: int
    visitor: Optional[List[VisitorSchema]] = []
    car: Optional[List[CarSchema]] = []
    approve: Optional[List[ApprovalSchema]] = []

    class Config:
        from_attributes = True


class MainRequestsStatusSchema(BaseModel):
    status: str
    comment: str

    class Config:
        from_attributes = True


class MainRequestsPassCountSchema(BaseModel):
    passcount: int

    class Config:
        from_attributes = True


class MainRequestsMinSchema(MainRequestsIdSchema):
    creator: str

    class Config:
        from_attributes = True


class MainRequestsCreate(MainRequestsBaseSchema):
    internal_req_id: int

    class Config:
        from_attributes = True


class UserBaseSchema(BaseModel):
    lastname: str
    name: str
    patronymic: str
    role: str
    speciality: str
    logged_in: bool
    created_date: datetime.datetime = datetime.datetime.now()


class UsersSchema(UserBaseSchema):
    id: int

    class Config:
        from_attributes = True


class UserWithPasswordSchema(UserBaseSchema):
    login: str
    hashed_password: bytes


class CreateUserSchema(UserBaseSchema):
    login: str
    hashed_password: bytes


class SpecTransportBaseSchema(BaseModel):
    type: Optional[str]
    govern_num: str
    model: str

    class Config:
        from_attributes = True


class SpecTransOnTerritorySchema(SpecTransportBaseSchema):
    id: int

    class Config:
        from_attributes = True


class CarsOnTerritoryBase(BaseModel):
    car_id: int


class CarsOnTerritoryMain(CarsOnTerritoryBase):
    car: CarSchema


class CarsOnTerritorySchema(CarsOnTerritoryMain):
    id: int

    class Config:
        from_attributes = True


class VisitorPassageBase(BaseModel):
    pass_date: datetime.datetime
    status: str
    v_id: int


class VisitorPassageSchema(VisitorPassageBase):
    id: int
    visitor: VisitorSchema


class SpecTransportPassageBase(BaseModel):
    type: Optional[str]
    govern_num: str
    pass_date: datetime.datetime
    status: str
    model:  Optional[str]


class SpecTransportPassageSchema(SpecTransportPassageBase):
    id: int


class CarPassageBase(BaseModel):
    pass_date: datetime.datetime
    c_id: int
    status: str


class CarPassageMain(CarPassageBase):
    car: CarSchema


class CarPassageSchema(CarPassageMain):
    id: int


class HolidayDatesSchema(BaseModel):
    id: int
    from_date: datetime.datetime
    to_date: datetime.datetime



