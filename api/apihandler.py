import datetime
import json
import os
from datetime import timedelta
import sqlalchemy.exc
from fastapi import APIRouter, HTTPException, Depends, Security
from pydantic import ValidationError
from sqlalchemy import sql, select, delete, update, insert, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from typing import Annotated
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes
)
from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.responses import RedirectResponse

from werkzeug.security import check_password_hash, generate_password_hash

from api import dbhandler
from api.enums import (
    RequestStatus,
    OnTerritoryMode,
    Scopes
)
from api.models import (
    MainRequests,
    Visitors,
    Cars,
    UsersTable,
    CarsOnTerritoryTable,
    SpecTransOnTerritory,
    CPassage,
    VPassage,
    SpecTransport,
    ApprovalPool, HolidayDates
)
from api.schemas import (
    MainRequestsSchema,
    # MainRequestsMinSchema,
    UsersSchema,
    CarsOnTerritorySchema,
    SpecTransOnTerritorySchema,
    VisitorPassageSchema,
    CarPassageSchema,
    SpecTransportPassageSchema,
    MainRequestsCreate,
    VisitorCreate,
    CarCreate,
    # CarPassageMain,
    SpecTransportPassageBase,
    # CarsOnTerritoryMain,
    ApprovalBase,
    MainRequestsBaseSchema,
    # MainRequestsIdSchema,
    # CarBaseSchema,
    # VisitorBaseSchema,
    CarSchema,
    VisitorSchema,
    UserBaseSchema,
    UserWithPasswordSchema,
    VisitorPassageBase,
    TokenData,
    Token,
    ApprovalSchema, MainRequestsStatusSchema, HolidayDatesSchema, CarPassageBase, CarsOnTerritoryBase,
    SpecTransportBaseSchema, CreateUserSchema
)

SECRET_KEY = os.environ.get('SECRETKEY')

ALGORITHM = os.environ.get('ALGORITHM')

ACCESS_TOKEN_EXPIRE_MINUTES = 90

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

dbhandler.global_init(os.environ.get("DBPASSWORD"),
                      os.environ.get("SERVER"),
                      os.environ.get("PORT"),
                      os.environ.get("DBNAME"))

# Настройка предъявителя, настройка прав доступа
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/login",
    scopes={
        "superuser": "SUDO privileges",
        "admin": "ALLOW and REJECT requests",
        "limited_admin": "APPROVE and REJECT reusable request, ALLOW and REJECT disposable requests",
        "requestor": "CREATE requests",
        "monitoring": "READ requests",
        "current_user": "Current user. It's you"
    }
)

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.on_event("startup")
async def on_startup():
    await dbhandler.initialize_tables()


# Верификация пароля
def verify_password(plain_password: str,
                    hashed_password: str) -> bool:
    return check_password_hash(hashed_password, plain_password)


# Генерация хэша пароля
def get_password_hash(password: str) -> str:
    return generate_password_hash(password)


"""OAuth2 аутентификация"""


# Генерация JWT токена
def create_access_token(data: dict,
                        expires_delta: timedelta | None):
    to_encode = data.copy()

    if expires_delta:  # расчет дельты срока валидности токена
        expire = datetime.datetime.now() + expires_delta
    else:
        expire = datetime.datetime.now() + datetime.timedelta(minutes=15)

    to_encode.update({
        "exp": expire
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # Совмещение трех основных частей токена
    return encoded_jwt


# Получение текущего пользователя
async def get_current_user(
        security_scopes: SecurityScopes,
        token: Annotated[str, Depends(oauth2_scheme)],
        session: AsyncSession = Depends(dbhandler.create_session)
):
    if security_scopes.scopes:  # проверка наличия прав доступа у пользователя
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    # исключение, которое будет вызываться при попытке входа с невалидными данными
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value}
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # Декодирование данных из токена
        login: str = payload.get("sub")

        if login is None:  # Вызов ошибки при пустом логине
            print("Invalid login")
            raise credentials_exception

        token_scopes = payload.get("scopes", [])  # получение прав доступа
        token_data = TokenData(scopes=token_scopes, login=login)

    except (JWTError, ValidationError):  # Вызов ошибки при невалидном JWT токене или схемы
        print("Invalid token")

        raise credentials_exception

    user = (await session.execute(select(UsersTable).where(UsersTable.login == token_data.login))).one()[0]

    if user is None:
        raise credentials_exception

    for scope in security_scopes.scopes:  # проверка наличия прав доступа у пользователя
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value}
            )

    return user


async def get_current_active_user(  # получение текущего пользователя с проверкой активности
        current_user: Annotated[UsersSchema, Security(get_current_user, scopes=["current_user"])]
):
    if not current_user.logged_in:  # Проверка входа пользователя
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


@router.post("/login",
             tags=["Аутетификация"])
async def create_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],  # Получение формы аутентификации
        session: AsyncSession = Depends(dbhandler.create_session)  # Инициализация сессии подключения к бд
) -> Token:
    """
    **OAuth аутентификация**

    - **Запрашивает**:
        * Пароль и логин пользователя, так же можно указать требуемые права доступа scope
    - return:
        * Возвращает сгенерированный JWT токен
    """

    async with session as session:
        user = await session.execute(select(UsersTable).where(UsersTable.login == form_data.username))
    try:
        user = user.one()[0]
    except sqlalchemy.exc.NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    print(str(user.hashed_password.decode('utf-8')), "<-- password")

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    elif not verify_password(form_data.password, str(user.hashed_password.decode('utf-8'))):  # Верификация пароля
        print(user.hashed_password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    async with session as session:  # Включение у пользователя флага logged_in
        await session.execute(update(UsersTable)
                              .where(UsersTable.login == form_data.username)
                              .values({UsersTable.logged_in: True}))

        await session.commit()

    scopes = None
    if user.role == "4":
        scopes = [Scopes.SUPERUSER.value,
                  Scopes.ADMIN.value,
                  Scopes.LIMITED_ADMIN.value,
                  Scopes.REQUESTER.value,
                  Scopes.MONITORING.value,
                  Scopes.CURRENT.value]

    elif user.role == "3":
        scopes = [Scopes.ADMIN.value,
                  Scopes.LIMITED_ADMIN.value,
                  Scopes.REQUESTER.value,
                  Scopes.MONITORING.value,
                  Scopes.CURRENT.value]

    elif user.role == "2":
        scopes = [Scopes.LIMITED_ADMIN.value,
                  Scopes.REQUESTER.value,
                  Scopes.MONITORING.value,
                  Scopes.CURRENT.value]

    elif user.role == "1":
        scopes = [Scopes.REQUESTER.value,
                  Scopes.CURRENT.value]

    elif user.role == "0":
        scopes = [Scopes.MONITORING.value,
                  Scopes.CURRENT.value]

    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # Временная метка истечения токена
    access_token = create_access_token(  # Генерация токена для данного пользователя
        data={
            "sub": user.login,
            "lastname": f'{user.lastname}',
            "name": f'{user.name}',
            "patronymic": f'{user.patronymic}',
            "scopes": scopes if not form_data.scopes else form_data.scopes
        },
        expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


"""GET REQUEST API"""


@router.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url='/docs')


@router.get("/read/user/{_id}",
            response_model=UserWithPasswordSchema,
            tags=["Аутетификация", "GET операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.SUPERUSER.value])])
async def get_user(_id: int,
                   session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Получение пользователя по логину**

    - param **login**:
        * Строка, значение login
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает объект найденного пользователя
    """
    async with session as session:
        query = await session.execute(select(UsersTable).where(UsersTable.id == _id))

    result = query.one()[0]

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result


@router.get("/read/search/{value}",
            tags=["GET операции"],
            response_model=list[MainRequestsSchema])
async def search_engine(value: str,
                        monitoring: bool = False,
                        is_filtered: bool = False,
                        creator: str = None,
                        fdate: datetime.datetime = datetime.datetime.now().date(),
                        tdate: datetime.datetime = datetime.datetime.now().date(),
                        session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **API поиска по заявкам**

    - param **value**:
        * Принимает на вход поисковое значение в виде строки
    - return:
        * Возвращает заявку с прикрепленными посетителями и автомобилями
    """

    query_v = select(MainRequests).join(MainRequests.visitor).where(
        (Visitors.lastname.like(f'%{value.upper()}%')) |
        ((Visitors.lastname.in_(value.upper().split())) &
         (Visitors.name.in_(value.upper().split())) &
         (Visitors.patronymic.in_(value.upper().split()))) |
        (MainRequests.organization.like(f'%{value}%')) |
        (MainRequests.organization.in_(value.upper().split())) |
        (MainRequests.organization.match(value.upper())) |
        (MainRequests.contract_name.like(f'%{value}%'))
    )
    query_c = select(MainRequests).join(MainRequests.car).where(
        Cars.govern_num.like(f'%{value.upper()}%'))

    if is_filtered:
        query_v = query_v.where((sql.func.date(MainRequests.from_date).between(fdate, tdate.date()))
                                & sql.func.date(MainRequests.to_date).between(fdate, tdate.date()))
        query_c = query_c.where((sql.func.date(MainRequests.from_date).between(fdate, tdate.date()))
                                & sql.func.date(MainRequests.to_date).between(fdate.date(), tdate.date()))

    if monitoring:
        query_v = query_v.where(((datetime.datetime.now().date().today() >= MainRequests.from_date)
                                 & (MainRequests.to_date >= datetime.datetime.now().date().today())
                                 | (MainRequests.from_date > datetime.datetime.now().today()))
                                & (MainRequests.status == RequestStatus.ALLOWED.value)
                                )

        query_c = query_c.where(((datetime.datetime.now().date().today() >= MainRequests.from_date)
                                 & (MainRequests.to_date >= datetime.datetime.now().date().today())
                                 | (MainRequests.from_date > datetime.datetime.now().today()))
                                & (MainRequests.status == RequestStatus.ALLOWED.value))

    if creator:
        query_v = query_v.where(MainRequests.creator == creator)
        query_c = query_c.where(MainRequests.creator == creator)

    union_query = select(MainRequests).from_statement(union_all(query_v, query_c))

    async with (session as session):
        async with session.begin():
            query = await session.execute(union_query)
    result = query.scalars()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result


@router.get("/read/requests/actual",
            response_model=list[MainRequestsSchema],
            tags=["GET операции"])
async def get_actual_requests(monitoring: bool = False,
                              fdate: datetime.datetime = datetime.datetime.now().date(),
                              tdate: datetime.datetime = datetime.datetime.now().date(),
                              is_filtered: bool = False,
                              creator: str = None,
                              session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Получение актуальных заявок, а так же актуальных заявок для мониторинга**

    - param **monitoring**:
        * Булевое значение, переключение режима для получения актуальных заявок для мониторинга
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает объекты найденных заявок
    """
    query = select(MainRequests).where((fdate >= MainRequests.from_date)
                                       & (MainRequests.to_date >= tdate)
                                       | (MainRequests.from_date > fdate))
    if is_filtered:
        query = select(MainRequests).where((sql.func.date(MainRequests.from_date).between(fdate, tdate))
                                           & sql.func.date(MainRequests.to_date).between(fdate, tdate))
    if monitoring:
        query = select(MainRequests).where((datetime.datetime.now().date().today() >= MainRequests.from_date)
                                           & (MainRequests.to_date >= datetime.datetime.now().date().today())
                                           | (MainRequests.from_date > datetime.datetime.now().today())
                                           ).where((MainRequests.status == RequestStatus.ALLOWED.value))
    if creator:
        query = query.where(MainRequests.creator == creator).where(~MainRequests.is_deleted)

    async with (session as session):
        async with session.begin():
            result = await session.execute(query)
            result = result.scalars()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result


@router.get("/read/requests/actual/min",
            tags=["GET операции"])
async def get_min_requests(request_status: RequestStatus = RequestStatus.APPROVE,
                           forced: bool = False,
                           session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Получение актуальных заявок, а так же актуальных заявок для мониторинга**

    - param **monitoring**:
        * Булевое значение, переключение режима для получения актуальных заявок для мониторинга
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает объекты найденных заявок
    """
    query = (select(MainRequests.id, MainRequests.creator)
             .where(MainRequests.status == RequestStatus.APPROVE.value))

    if request_status is RequestStatus.CONSIDERATION:
        query = (select(MainRequests.id, MainRequests.creator)
                 .where((MainRequests.status == RequestStatus.CONSIDERATION.value)))

    if forced:
        query = (select(MainRequests.id, MainRequests.creator)
                 .where((MainRequests.status == RequestStatus.APPROVE.value) |
                        (MainRequests.status == RequestStatus.PASSAPPROVAL.value)))

    async with session as session:
        async with session.begin():
            result = await session.execute(query)
            result = json.dumps([{'id': _id, 'creator': _creator} for _id, _creator in list(result)],
                                ensure_ascii=False)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    print(result, '<-- API json')

    return result


@router.get("/read/request/{id}/approval",
            response_model=ApprovalSchema,
            tags=["GET операции"])
async def get_appr_requests(req_id: int,
                            session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Получение актуальных заявок, а так же актуальных заявок для мониторинга**

    - param **monitoring**:
        * Булевое значение, переключение режима для получения актуальных заявок для мониторинга
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает объекты найденных заявок
    """
    query = select(ApprovalPool).where(ApprovalPool.intr_req_id == req_id)
    try:
        async with session as session:
            async with session.begin():
                result = (await session.execute(query)).one()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"results not found"
            )
    except sqlalchemy.exc.NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result[0]


#
# @router.get("/read/requests/ids/actual",
#             response_model=list[MainRequestsIdSchema],
#             tags=["GET операции"])
# async def get_actual_requests(monitoring: bool = False,
#                               session: AsyncSession = Depends(dbhandler.create_session)):
#     """
#     **Получение списка id актуальных заявок, а так же актуальных заявок для мониторинга**
#
#     - param **monitoring**:
#         * Булевое значение, переключение режима для получения актуальных заявок для мониторинга
#     - param **session**:
#         * Сессия, вызов создания сессии подключения к базе данных
#     - return:
#         * Возвращает объекты найденных заявок
#     """
#     query = session.query(MainRequests.id).filter(
#         (datetime.datetime.now().date().today() >= MainRequests.from_date)
#         & (MainRequests.to_date >= datetime.datetime.now().date().today())
#         | (MainRequests.from_date > datetime.datetime.now().today()))
#     if monitoring:
#         query = (session.query(MainRequests.id)
#                  .filter((datetime.datetime.now().date().today() >= MainRequests.from_date)
#                          & (MainRequests.to_date >= datetime.datetime.now().date().today()))
#                  .filter((MainRequests.status == RequestStatus.ALLOWED.value)))
#
#     result = query.all()
#     if not result:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"results not found"
#         )
#
#     return result


@router.get("/read/users",
            response_model=list[UsersSchema],
            response_description="Получение всех пользователей из базы данных",
            tags=["GET операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.SUPERUSER.value])])
async def get_users(session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Получение списка пользователей системы**

    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает объекты найденных пользователей
    """

    query = select(UsersTable)

    async with session as session:
        async with session.begin():
            result = await session.execute(query)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result.scalars()


@router.get("/read/transport/on_territory",
            response_model=list[SpecTransOnTerritorySchema | CarsOnTerritorySchema],
            tags=["GET операции"])
async def get_transport_on_territory(mode: OnTerritoryMode = OnTerritoryMode.CARS,
                                     session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Получение транспорта на территории**

    - param **mode**:
        * Режим получения данных, перечисляемый тип данных
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает объекты найденного транспорта
    """
    query = None
    if mode is OnTerritoryMode.CARS:
        query = select(CarsOnTerritoryTable)
    elif mode is OnTerritoryMode.SPEC_TRANSPORT:
        query = select(SpecTransOnTerritory)

    async with session as session:
        async with session.begin():
            result = await session.execute(query)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result.scalars()


@router.get("/read/request/{_id}",
            response_model=MainRequestsSchema,
            tags=["GET операции"])
async def get_request(_id: int,
                      session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Получение заявки по id**

    - param **_id**:
        * Целое число, id заявки
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает объект найденной заявки
    """
    query = select(MainRequests).where(MainRequests.id == _id)
    async with session as session:
        async with session.begin():
            result = (await session.execute(query)).one()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    print()

    return result[0]


@router.get("/read/passages/actual",
            tags=["GET операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.LIMITED_ADMIN.value])])
async def get_actual_visitors_cars_passages(fdate: datetime.datetime = datetime.datetime.now().date(),
                                            tdate: datetime.datetime = datetime.datetime.now().date(),
                                            session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Получение актуальных проходов посетителей**

    - param **passage_mode**:
        * Перечисляемый тип PassageReportsMode, режим получения данных о проходах
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает объекты найденных проходов
    """

    async with session as session:
        async with session.begin():
            # query = None
            # if passage_mode is PassageReportsMode.CARS:
            query_c = (select(CPassage).where(sql.func.date(CPassage.pass_date).between(fdate, tdate)))
            # elif passage_mode is PassageReportsMode.VISITORS:
            query_v = select(VPassage).where(sql.func.date(VPassage.pass_date).between(fdate, tdate))
            # elif passage_mode is PassageReportsMode.SPEC_TRANSPORT:
            query_s = select(SpecTransport).where(sql.func.date(SpecTransport.pass_date).between(fdate, tdate))

            result_c = (await session.execute(query_c)).scalars()
            result_v = (await session.execute(query_v)).scalars()
            result_s = (await session.execute(query_s)).scalars()
            # print(result, "<-- union result")
            result = {
                "cars": [CarPassageSchema.model_validate(c, from_attributes=True) for c in result_c],
                "visitors": [VisitorPassageSchema.model_validate(v, from_attributes=True) for v in result_v],
                "spectransport": [SpecTransportPassageSchema.model_validate(s, from_attributes=True) for s in result_s],
            }

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result


@router.get("/read/passages/search",
            tags=["GET операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.LIMITED_ADMIN.value])])
async def search_passages(search_value: str,
                          fdate: datetime.datetime = datetime.datetime.now().date(),
                          tdate: datetime.datetime = datetime.datetime.now().date(),
                          is_filtered: bool = False,
                          session: AsyncSession = Depends(dbhandler.create_session)):
    query_c = (select(CPassage).join(CPassage.car)
               .where(Cars.govern_num.like(f'%{search_value.upper()}%')))

    query_v = (select(
        VPassage
    ).join(VPassage.visitor)
    .where(
        (Visitors.lastname.like(f'%{search_value.upper()}%')) |
        ((Visitors.lastname.in_(search_value.upper().split())) &
         (Visitors.name.in_(search_value.upper().split())) &
         (Visitors.patronymic.in_(search_value.upper().split()))))
    )

    query_s = (select(SpecTransport)
               .where(SpecTransport.govern_num.like(f'%{search_value.upper()}%')))

    print(fdate, tdate, "<-- dates")

    if is_filtered:
        query_c = query_c.where(sql.func.date(CPassage.pass_date).between(fdate, tdate))
        query_v = query_v.where(sql.func.date(VPassage.pass_date).between(fdate, tdate))
        query_s = query_s.where(sql.func.date(SpecTransport.pass_date).between(fdate, tdate))

    async with session as session:
        async with session.begin():
            searched_cars = (await session.execute(query_c)).scalars()
            searched_visitors = (await session.execute(query_v)).scalars()
            searched_spec = (await session.execute(query_s)).scalars()

            print(searched_cars)

            result = {
                "cars": [CarPassageSchema.model_validate(c, from_attributes=True) for c in searched_cars],
                "visitors": [VisitorPassageSchema.model_validate(v, from_attributes=True) for v in searched_visitors],
                "spectransport": [SpecTransportPassageSchema.model_validate(s, from_attributes=True) for s in
                                  searched_spec],
            }

    print(result, "<-- union result")

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result


@router.get("/read/holidays",
            response_model=list[HolidayDatesSchema],
            tags=["GET операции"])
async def get_holiday_dates(session: AsyncSession = Depends(dbhandler.create_session)):
    async with session as session:
        query = select(HolidayDates)
        result = (await session.execute(query)).scalars()
    print(result)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result


@router.get(
    "/read/request/visitors/{req_id}",
    response_model=list[VisitorSchema],
    tags=["GET операции"],
)
async def get_visitors(request_id: int,
                       session: AsyncSession = Depends(dbhandler.create_session)):
    async with session as session:
        async with session.begin():
            query = select(Visitors).where(Visitors.req_intr_id == request_id)
            result = (await session.execute(query)).scalars()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result


@router.get(
    "/read/request/cars/{req_id}",
    response_model=list[CarSchema],
    tags=["GET операции"],
)
async def get_cars(request_id: int,
                   session: AsyncSession = Depends(dbhandler.create_session)):
    async with session as session:
        async with session.begin():
            query = select(Cars).where(Cars.req_intr_id == request_id)
            result = (await session.execute(query)).scalars()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"results not found"
        )

    return result


"""API ДОБАВЛЕНИЯ"""

@router.post("/create/superuser",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"])
async def create_superuser(session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Создание пользователей**

    - param **request**:
        * Список схем модели UsersWithPasswordSchema
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        user = CreateUserSchema(
            lastname="Латышев",
            name="Александр",
            patronymic="Евгеньевич",
            role="4",
            speciality="Программист",
            logged_in=False,
            login="superuser",
            hashed_password=f'{generate_password_hash("12345678", method="pbkdf2:sha256", salt_length=8)}'

        )
        await session.execute(
            insert(UsersTable).values(user.model_dump())
        )
        await session.commit()
    return {"message": "user created"}


@router.post("/create/user",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"],
             dependencies=[Security(get_current_active_user, scopes=[Scopes.SUPERUSER.value])])
async def create_user(user: CreateUserSchema,
                      session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Создание пользователей**

    - param **request**:
        * Список схем модели UsersWithPasswordSchema
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        await session.execute(
            insert(UsersTable).values(user.model_dump())
        )
        await session.commit()

    return {"message": "user created"}


@router.post("/create/request",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"],
             dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
async def create_request(request: MainRequestsCreate,
                         session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Создание заявки**

    - param **request**:
        * Схема модели MainRequests
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        await session.execute(
            insert(MainRequests).values(request.model_dump())
        )
        await session.commit()

    return {"message": "request created",
            "data": request}


@router.post("/create/visitors",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"],
             dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
async def create_visitors(visitors: list[VisitorCreate],
                          session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Создание посетителей**

    - param **request**:
        * Список схем модели Visitors
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    visitors = [visitor.model_dump() for visitor in visitors]
    async with session as session:
        async with session.begin():
            await session.execute(
                insert(Visitors),
                visitors
            )
            await session.commit()

    return {"message": "visitors created",
            "data": visitors}


@router.post("/create/cars",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"],
             dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
async def create_cars(cars: list[CarCreate],
                      session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Создание автомобиля**

    - param **cars**:
        * Список схем модели Cars
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    cars = [car.model_dump() for car in cars]
    async with session as session:
        async with session.begin():
            await session.execute(
                insert(Cars),
                cars
            )
            await session.commit()

    return {"message": "cars created",
            "data": cars}


@router.post("/create/passage/car",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"])
async def create_car_passage(car: CarPassageBase,
                             session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Регистрация проезда автомобиля**

    - param **car**:
        * Схема модели CPassage
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        cpassage = CPassage(**car.model_dump())
        session.add(cpassage)
        await session.commit()
    return {"message": "car passage created",
            "data": cpassage}


@router.post("/create/passage/visitor",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"])
async def create_visitor_passage(visitor: VisitorPassageBase,
                                 session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Регистрация прохода посетителя**

    - param **visitor**:
        * Схема модели VPassage
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        vpassage = VPassage(**visitor.model_dump())
        session.add(vpassage)
        await session.commit()
    return {"message": "visitor passage created",
            "data": vpassage}


@router.post("/create/passage/spectransport",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"])
async def create_passage_spectransport(spec: SpecTransportPassageBase,
                                       session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Регистрация проезда спецтранспорта**

    - param **spec**:
        * Схема модели SpecTransport
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        passage = SpecTransport(**spec.model_dump())
        session.add(passage)
        await session.commit()
    return {"message": "spec transport passage created",
            "data": passage}


@router.post("/create/on_terr/car",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"])
async def create_on_terr_car(car_on_terr: CarsOnTerritoryBase,
                             session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Регистрация автомобиля на территории**

    - param **car_on_terr**:
        * Схема модели CarsOnTerritoryTable
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        on_terr = CarsOnTerritoryTable(**car_on_terr.model_dump())
        session.add(on_terr)
        await session.commit()
    return {"message": "car on territory created",
            "data": on_terr}


@router.post("/create/on_terr/spectransport",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"])
async def create_on_terr_spectransport(spec_on_terr: SpecTransportBaseSchema,
                                       session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Регистрация спецтранспорта на территории**

    - param **spec_on_terr**:
        * Схема модели SpecTransOnTerritory
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        on_terr = SpecTransOnTerritory(**spec_on_terr.model_dump())
        session.add(on_terr)
        await session.commit()
    return {"message": "car on territory created",
            "data": on_terr}


@router.post("/create/approval",
             status_code=status.HTTP_201_CREATED,
             tags=["POST операции"],
             dependencies=[Security(get_current_active_user, scopes=[Scopes.LIMITED_ADMIN.value])])
async def create_approval(approval: ApprovalBase,
                          session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Регистрация комментария согласанта**

    - param **approval**:
        * Схема модели ApprovalPool
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    - return:
        * Возвращает JSON с сообщением message и добавленными данными data
    """
    async with session as session:
        approval = ApprovalPool(**approval.model_dump())
        session.add(approval)
        await session.commit()
    return {"message": "approval created",
            "data": approval}


"""API Обновления"""


@router.put("/update/request/{_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
async def update_request(_id: int,
                         request_upd: MainRequestsBaseSchema,
                         session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление заявки**

    - param **request_id**:
        * ID заявки
    - param **request_upd**:
        * Схема модели MainRequests
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """

    async with session as session:
        await session.execute(update(MainRequests)
                              .where(MainRequests.id == _id)
                              .values(request_upd.model_dump()))

        await session.commit()


# @router.put("/update/car/{id}",
#             status_code=status.HTTP_204_NO_CONTENT,
#             tags=["PUT операции"],
#             dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
# async def update_car(car_id: int,
#                      car_upd: CarBaseSchema,
#                      session: AsyncSession = Depends(dbhandler.create_session)):
#     """
#     **Обновление автомобиля**
#
#     - param **car_id**:
#         * ID автомобиля
#     - param **car_upd**:
#         * Схема модели Cars
#     - param **session**:
#         * Сессия, вызов создания сессии подключения к базе данных
#     """
#     with session as session:
#         session.query(Cars) \
#             .filter(Cars.id == car_id) \
#             .update(car_upd.model_dump(), synchronize_session=False)
#         session.commit()


# @router.put("/update/visitor/{id}",
#             status_code=status.HTTP_204_NO_CONTENT,
#             tags=["PUT операции"],
#             dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
# async def update_visitor(visit_id: int,
#                          visitor_upd: VisitorBaseSchema,
#                          session: AsyncSession = Depends(dbhandler.create_session)):
#     """
#     **Обновление посетителя**
#
#     - param **visit_id**:
#         * ID посетителя
#     - param **visitor_upd**:
#         * Схема модели Visitors
#     - param **session**:
#         * Сессия, вызов создания сессии подключения к базе данных
#     """
#     with session as session:
#         session.query(Visitors) \
#             .filter(Visitors.id == visit_id) \
#             .update(visitor_upd.model_dump(), synchronize_session=False)
#         session.commit()


@router.put("/update/bulk/cars",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
async def update_bulk_cars(cars: list[CarSchema],
                           session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Массовое обновление записей автомобилей**

    - param **cars**:
        * Список схем модели Cars
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    cars = [c.model_dump() for c in cars]
    async with session as session:
        async with session.begin():
            await session.execute(
                update(Cars),
                cars
            )
            await session.commit()


@router.put("/update/bulk/visitors",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
async def update_bulk_visitors(visitors: list[VisitorSchema],
                               session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Массовое обновление записей посетителей**

    - param **visitors**:
        * Список схем модели Visitors
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    visitors = [v.model_dump() for v in visitors]
    async with session as session:
        async with session.begin():
            await session.execute(
                update(Visitors),
                visitors
            )
            await session.commit()


@router.put("/update/user/base/{user_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.SUPERUSER.value])])
async def update_user_base(user_id: int,
                           user: UserBaseSchema,
                           session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя без пароля и логина**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """

    async with session as session:
        await session.execute(update(UsersTable)
                              .where(UsersTable.id == user_id)
                              .values(user.model_dump()))

        await session.commit()


@router.put("/update/visitor/passed/{_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"])
async def update_visitor_passed(_id: int,
                                passmode: bool,
                                session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя без пароля и логина**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        await session.execute(update(Visitors).where(Visitors.id == _id).values({Visitors.passed: passmode}))
        await session.commit()


@router.put("/update/car/passed/{_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"])
async def update_car_passed(_id: int,
                            passmode: bool,
                            session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя без пароля и логина**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        await session.execute(update(Cars).where(Cars.id == _id).values({Cars.passed: passmode}))
        await session.commit()


@router.put("/update/user/full/{user_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"],
            dependencies=[Security(get_current_active_user, scopes=[Scopes.SUPERUSER.value])])
async def update_user_full(user_id: int,
                           user: UserWithPasswordSchema,
                           session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя вместе с паролем и логином**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """

    async with session as session:
        await session.execute(update(UsersTable)
                              .where(UsersTable.id == user_id)
                              .values(user.model_dump()))

        await session.commit()


@router.post("/update/request/status/{id}",
             status_code=status.HTTP_204_NO_CONTENT,
             tags=["POST операции"],
             dependencies=[Security(get_current_active_user, scopes=[Scopes.REQUESTER.value])])
async def update_request_status(req_id: int,
                                req: MainRequestsStatusSchema,
                                session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя вместе с паролем и логином**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        await session.execute(update(MainRequests).where(
            MainRequests.id == req_id).values(req.model_dump()))

        await session.commit()


@router.put("/delete/request/{req_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"],
            dependencies=[Security(get_current_active_user,
                                   scopes=[Scopes.REQUESTER.value])])
async def update_request_status(req_id: int,
                                session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя вместе с паролем и логином**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        await session.execute(update(MainRequests).where(
            MainRequests.id == req_id).values({MainRequests.is_deleted: True}))

        await session.commit()


@router.post("/update/request/close/{_id}",
             status_code=status.HTTP_204_NO_CONTENT,
             tags=["POST операции"])
async def update_request_status(_id: int,
                                session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя вместе с паролем и логином**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        await session.execute(
            update(MainRequests)
            .where(MainRequests.id == _id)
            .values({"status": RequestStatus.CLOSED.value})
        )

        await session.commit()


@router.put("/update/request/passcount/{_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"])
async def update_request_status(_id: int,
                                count: int,
                                session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя вместе с паролем и логином**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        await session.execute(update(MainRequests).where(
            MainRequests.id == _id).values({"passcount": count}))

        await session.commit()


@router.put("/user/{_id}/logout",
            status_code=status.HTTP_204_NO_CONTENT,
            tags=["PUT операции"])
async def update_request_status(_id: int,
                                session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Обновление основной информации учетной записи пользователя вместе с паролем и логином**

    - param **user_id**:
        * ID пользователя
    - param **user**:
        * Схема модели User
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:  # Включение у пользователя флага logged_in
        await session.execute(update(UsersTable)
                              .where(UsersTable.id == _id)
                              .values({UsersTable.logged_in: False}))

        await session.commit()


"""DELETE операции"""


@router.delete("/delete/on_terr/car/{car_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["DELETE операции"])
async def delete_car_on_territory(car_id: int,
                                  session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Удаление записи автомобиля на территории**

    - param **car_id**:
        * ID записи автомобиля на территории
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        reg_car_out = delete(CarsOnTerritoryTable) \
            .where(CarsOnTerritoryTable.id == car_id)
        await session.execute(reg_car_out)
        await session.commit()


@router.delete("/delete/on_terr/spec_trans/{spec_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["DELETE операции"])
async def delete_spec_on_territory(spec_id: int,
                                   session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Удаление записи спецтранспорта на территории**

    - param **spec_id**:
        * ID записи спецтранспорта на территории
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        reg_spectrans_out = delete(SpecTransOnTerritory).where(SpecTransOnTerritory.id == spec_id)
        await session.execute(reg_spectrans_out)
        await session.commit()


@router.delete("/delete/user/{user_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               tags=["DELETE операции"])
async def delete_user(user_id: int,
                      session: AsyncSession = Depends(dbhandler.create_session)):
    """
    **Удаление записи спецтранспорта на территории**

    - param **spec_id**:
        * ID записи спецтранспорта на территории
    - param **session**:
        * Сессия, вызов создания сессии подключения к базе данных
    """
    async with session as session:
        await session.execute(delete(UsersTable).where(UsersTable.id == user_id))
        await session.commit()
