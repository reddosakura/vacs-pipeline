import datetime
import os

import jwt
from fastapi import Request, APIRouter
from starlette.responses import RedirectResponse
from starlette_wtf import csrf_protect
import httpx

from api.enums import Scopes
from .appconfig import templates
from .forms import AuthForm
from routing_enum import Routes


router = APIRouter()


@router.route("/auth", methods=['GET', 'POST'])
@csrf_protect
async def auth(request: Request):

    form = await AuthForm.from_formdata(request)

    if await form.validate_on_submit():
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "http://host.docker.internal:5768/" + "api/v1/login",
                data={
                    "username": form.data["username"],
                    "password": form.data["password"]
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if token_response.status_code != 200:
                return templates.TemplateResponse(
                    request=request,
                    name="html/auth.html",
                    context={
                        "request": request,
                        "form": form
                    })
            decoded_jwt = jwt.decode(token_response.json()["access_token"],
                                     key=os.environ.get('SECRETKEY'),
                                     algorithms=[os.environ.get('ALGORITHM')])

            if Scopes.SUPERUSER.value in decoded_jwt["scopes"]:
                response = RedirectResponse(url=Routes.SUDP_PREFIX.value + Routes.PROC.value + "/approve", status_code=302)
                response.set_cookie("role", Scopes.SUPERUSER.value)

            elif Scopes.ADMIN.value in decoded_jwt["scopes"]:
                response = RedirectResponse(url=Routes.SUDP_PREFIX.value + Routes.PROC.value + "/approve", status_code=302)
                response.set_cookie("role", Scopes.ADMIN.value)

            elif Scopes.LIMITED_ADMIN.value in decoded_jwt["scopes"]:
                response = RedirectResponse(url=Routes.SUDP_PREFIX.value + Routes.PROC.value + "/approve", status_code=302)
                response.set_cookie("role", Scopes.LIMITED_ADMIN.value)

            elif Scopes.REQUESTER.value in decoded_jwt["scopes"]:
                response = RedirectResponse(url=Routes.SUDP_PREFIX.value + "/requests" + "/my", status_code=302)
                response.set_cookie("role", Scopes.REQUESTER.value)

            elif Scopes.MONITORING.value in decoded_jwt["scopes"]:
                response = RedirectResponse(url=Routes.SUDP_PREFIX.value + "/monitoring", status_code=302)
                response.set_cookie("role", Scopes.MONITORING.value)

            expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)

            response.set_cookie(
                key="access_token",
                value=token_response.json()["access_token"],
                expires=expires,
                # secure=True,
                # httponly=True,
                # samesite="none"
            )

        return response

    return templates.TemplateResponse(
        request=request,
        name="html/auth.html",
        context={
            "request": request,
            "form": form
        })
