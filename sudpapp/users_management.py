import json
import os
from datetime import datetime
from fastapi import APIRouter
from jose import JWTError
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette_wtf import csrf_protect
import jwt
from werkzeug.security import generate_password_hash

from api.enums import RequestType, OnTerritoryMode, PassageReportsMode, RequestStatus
from api.schemas import UserWithPasswordSchema
from .appconfig import templates
from .forms import SearchForm, FilterForm, RecallForm, CreateUserForm, UpdateUserForm
from .utils import build_request, _process_raw_request

router = APIRouter()


@router.route('/users', methods=["GET", "POST"])
@csrf_protect
async def _users(request: Request):
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')

    decoded_jwt = jwt.decode(access_token,
                             key=os.environ.get('SECRETKEY'),
                             algorithms=[os.environ.get('ALGORITHM'), ])

    creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

    actual_users = await build_request(
        url="host.docker.internal:8000/" + "api/v1/read/users",
        access_token=access_token
    )

    form = await CreateUserForm.from_formdata(request)

    if await form.validate_on_submit():
        if form.create_btn.data:
            await build_request(
                url="host.docker.internal:8000/" + "api/v1/create/user",
                method="POST",
                data={
                    "lastname": form.lastname.data,
                    "name": form.name.data,
                    "patronymic": form.patronymic.data,
                    "role": form.role.data,
                    "speciality": form.speciality.data,
                    "logged_in": False,
                    "created_date": datetime.now().isoformat(),
                    "login": form.login.data,
                    "hashed_password": f"{generate_password_hash(form.password.data,
                                                                 method="pbkdf2:sha256", salt_length=8)}"
                },
                access_token=access_token,
            )

            return RedirectResponse(url='/sudpapp/users', status_code=status.HTTP_302_FOUND)

    context = {
        'actual_users': actual_users.json(),
        "role": role,
        "user": creator,
        "form": form
    }

    response = templates.TemplateResponse(
        request=request,
        name="html/users.html",
        context=context
    )

    return response


@router.get('/user/edit/{_id}')
async def _users(request: Request,
                 _id: int):
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')

    decoded_jwt = jwt.decode(access_token,
                             key=os.environ.get('SECRETKEY'),
                             algorithms=[os.environ.get('ALGORITHM'), ])

    creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

    _user = await build_request(
        "host.docker.internal:8000/" + f"api/v1/read/user/{_id}",
        access_token=access_token,
    )

    _user_json = _user.json()

    _user_object = UserWithPasswordSchema.parse_obj(_user_json)

    form = await UpdateUserForm.from_formdata(request)

    form.lastname.data = _user_object.lastname
    form.name.data = _user_object.name
    form.patronymic.data = _user_object.patronymic
    form.role.data = _user_object.role
    form.speciality.data = _user_object.speciality
    form.login.data = _user_object.login

    context = {
        "role": role,
        "user": creator,
        "form": form
    }

    response = templates.TemplateResponse(
        request=request,
        name="html/user_edit.html",
        context=context
    )

    return response


@router.post('/user/edit/{_id}')
@csrf_protect
async def _users(request: Request,
                 _id: int):
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')

    decoded_jwt = jwt.decode(access_token,
                             key=os.environ.get('SECRETKEY'),
                             algorithms=[os.environ.get('ALGORITHM'), ])

    creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

    form = await UpdateUserForm.from_formdata(request)

    if await form.validate_on_submit():
        if form.edit_btn.data:
            if not form.selector.data:
                await build_request(
                    url="host.docker.internal:8000/" + f"api/v1/update/user/base/{_id}",
                    method="PUT",
                    data={
                        "lastname": form.lastname.data,
                        "name": form.name.data,
                        "patronymic": form.patronymic.data,
                        "role": form.role.data,
                        "speciality": form.speciality.data,
                        "logged_in": True,
                        "created_date": datetime.now().isoformat()
                    },
                    access_token=access_token,
                )

                return RedirectResponse(url='/sudpapp/users', status_code=status.HTTP_302_FOUND)
            else:
                await build_request(
                    url="host.docker.internal:8000/" + f"api/v1/update/user/full/{_id}",
                    method="PUT",
                    data={
                        "lastname": form.lastname.data,
                        "name": form.name.data,
                        "patronymic": form.patronymic.data,
                        "role": form.role.data,
                        "speciality": form.speciality.data,
                        "logged_in": True,
                        "created_date": datetime.now().isoformat(),
                        "login": form.login.data,
                        "hashed_password": f"{generate_password_hash(form.password.data,
                                                                     method="pbkdf2:sha256", salt_length=8)}"
                    },
                    access_token=access_token,
                )
                return RedirectResponse(url='/sudpapp/users', status_code=status.HTTP_302_FOUND)
        elif form.delete_btn.data:
            await build_request(
                url="host.docker.internal:8000/" + f"api/v1/delete/user/{_id}",
                method="DELETE",
                access_token=access_token
            )
            return RedirectResponse(url='/sudpapp/users', status_code=status.HTTP_302_FOUND)

    context = {
        "role": role,
        "user": creator,
        "form": form
    }

    response = templates.TemplateResponse(
        request=request,
        name="html/user_edit.html",
        context=context
    )

    return response
