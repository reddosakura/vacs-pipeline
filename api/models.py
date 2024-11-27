from datetime import datetime, time
from typing import List

import sqlalchemy
from sqlalchemy.orm import Mapped, mapped_column
from .dbhandler import SqlAlchemyBase, indexed_str, intpk, null_str, create_date, intr_id
from sqlalchemy import orm


class VPassage(SqlAlchemyBase):
    __tablename__ = 'v_passage'
    id: Mapped[intpk]
    pass_date: Mapped[datetime]
    v_id: Mapped[sqlalchemy.BigInteger] = mapped_column(sqlalchemy.ForeignKey('visitors.id'))
    visitor: Mapped['Visitors'] = orm.relationship(back_populates='passage', lazy='selectin')
    status: Mapped[str]


class UsersTable(SqlAlchemyBase):
    __tablename__ = 'users'
    id: Mapped[intpk]
    lastname: Mapped[str]
    name: Mapped[str]
    patronymic: Mapped[null_str]
    role: Mapped[str]
    logged_in: Mapped[bool]
    login: Mapped[indexed_str]
    speciality: Mapped[str]
    hashed_password: Mapped[bytes]
    created_date: Mapped[create_date]


class SpecTransOnTerritory(SqlAlchemyBase):
    __tablename__ = 'spectrans_on_territory_table'
    id: Mapped[intpk]
    type: Mapped[null_str]
    govern_num: Mapped[indexed_str]
    model: Mapped[str]


class SpecTransport(SqlAlchemyBase):
    __tablename__ = 'spectrans_pass'
    id: Mapped[intpk]
    type: Mapped[null_str]
    govern_num: Mapped[indexed_str]
    pass_date: Mapped[create_date]
    status: Mapped[str]
    model: Mapped[str]


class HolidayDates(SqlAlchemyBase):
    __tablename__ = 'holiday_dates'
    id: Mapped[intpk]
    from_date: Mapped[datetime]
    to_date: Mapped[datetime]


class Cars(SqlAlchemyBase):
    __tablename__ = 'cars'
    id: Mapped[intpk]
    carmodel: Mapped[str]
    govern_num: Mapped[indexed_str]
    req_intr_id: Mapped[sqlalchemy.BigInteger] = mapped_column(sqlalchemy.ForeignKey('main.internal_req_id'),
                                                               index=True)
    creq: Mapped['MainRequests'] = orm.relationship(back_populates='car', lazy='subquery')
    passage: Mapped['CPassage'] = orm.relationship(back_populates='car', lazy='subquery')
    passed: Mapped[bool] = mapped_column(default=False)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    date_created: Mapped[datetime] = mapped_column(default=datetime.now)
    date_deleted: Mapped[datetime]


class CarsOnTerritoryTable(SqlAlchemyBase):
    __tablename__ = 'cars_on_territory_table'
    id: Mapped[intpk]
    car_id: Mapped[sqlalchemy.BigInteger] = mapped_column(sqlalchemy.ForeignKey('cars.id'))
    car: Mapped['Cars'] = orm.relationship(lazy='selectin')


class CPassage(SqlAlchemyBase):
    __tablename__ = 'c_passage'
    id: Mapped[intpk]
    pass_date: Mapped[datetime]
    c_id: Mapped[sqlalchemy.BigInteger] = mapped_column(sqlalchemy.ForeignKey('cars.id'))
    car: Mapped['Cars'] = orm.relationship(back_populates='passage', lazy='selectin')
    status: Mapped[str]


class ApprovalPool(SqlAlchemyBase):
    __tablename__ = 'approval_pool'
    id: Mapped[intpk]
    lastname: Mapped[str]
    name: Mapped[str]
    patronymic: Mapped[null_str]
    approval_comments: Mapped[str]
    approval_status: Mapped[str]
    intr_req_id: Mapped[intr_id]
    areq: Mapped['MainRequests'] = orm.relationship(back_populates='approve', lazy='subquery')
    created_date: Mapped[create_date]


class Visitors(SqlAlchemyBase):
    __tablename__ = 'visitors'
    id: Mapped[intpk]
    lastname: Mapped[indexed_str]
    name: Mapped[str]
    patronymic: Mapped[str]
    req_intr_id: Mapped[sqlalchemy.BigInteger] = mapped_column(sqlalchemy.ForeignKey('main.internal_req_id'),
                                                               unique=True)
    vreq: Mapped["MainRequests"] = orm.relationship(back_populates='visitor', lazy='subquery')
    passage: Mapped["VPassage"] = orm.relationship(back_populates='visitor', lazy='subquery')
    passed: Mapped[bool] = mapped_column(default=False)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    date_created: Mapped[datetime] = mapped_column(default=datetime.now)
    date_deleted: Mapped[datetime]


class MainRequests(SqlAlchemyBase):
    __tablename__ = 'main'
    id: Mapped[intpk]
    creator: Mapped[str]
    type: Mapped[str]
    contract_name: Mapped[null_str]
    organization: Mapped[str] = mapped_column(nullable=True, index=True)
    from_date: Mapped[datetime]
    to_date: Mapped[datetime]
    from_time: Mapped[time]
    to_time: Mapped[time]
    comment: Mapped[str]
    files: Mapped[null_str]
    created_date: Mapped[create_date]
    status: Mapped[indexed_str]
    passcount: Mapped[int]
    passmode: Mapped[str]
    internal_req_id: Mapped[int] = mapped_column(type_=sqlalchemy.BigInteger, index=True, unique=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)
    visitor: Mapped[List['Visitors']] = orm.relationship(lazy='selectin')
    car: Mapped[List['Cars']] = orm.relationship(lazy='selectin')
    approve: Mapped[List['ApprovalPool']] = orm.relationship(back_populates='areq', lazy='selectin')
    __mapper_args__ = {"eager_defaults": True}
