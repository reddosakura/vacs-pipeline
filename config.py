import json
import logging
import os
import pprint
import sys
import traceback
from datetime import datetime

import sqlalchemy.exc
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette import status
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, PlainTextResponse, JSONResponse
from starlette.routing import Mount
from starlette_wtf import CSRFProtectMiddleware
from starlette.middleware import Middleware
from wtforms.validators import ValidationError

from api import apihandler
from sudpapp import (
    auth,
    proc,
    creation,
    monitoring,
    passages_report,
    requests_reports, edit_request, users_management
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from json.decoder import JSONDecodeError
from routing_enum import Routes
from dotenv import load_dotenv, find_dotenv

from sudpapp.appconfig import templates

load_dotenv(find_dotenv('.venv/.env'))

app = FastAPI(debug=True,
              title="VACS/СУДП",
              version="0.3.1",
              # docs_url=None,
              # redoc_url=None,
              middleware=[
                  Middleware(
                      SessionMiddleware,
                      secret_key=os.environ.get('SECRETKEY')
                  ),
                  Middleware(
                      CSRFProtectMiddleware,
                      csrf_secret=os.environ.get('CSRFSECRET'),
                      csrf_time_limit=31536000
                  )
              ],
              routes=[
                  Mount("/static", StaticFiles(directory="res/static"), name="static")
              ])


@app.exception_handler(404)
async def validation_exception_handler(request, exc):
    return templates.TemplateResponse(
        request=request,
        name="html/not_found.html",
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return templates.TemplateResponse(
        request=request,
        name="html/not_found.html",
    )


log = logging.getLogger('uvicorn.access')
log.setLevel(logging.INFO)

handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(
    logging.Formatter(fmt='[%(asctime)s] %(name)s | %(levelname)s | %(message)s | %(filename)s:%(lineno)d')
)
log.addHandler(handler)


async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        log.exception(str(traceback.format_exc()))
        return templates.TemplateResponse(
            request=request,
            name="html/error.html",
            context={
                "exc": e.__class__.__name__,
                "ip": request.client.host,
                "date": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                "url": request.url,
                "json": json.dumps(dict(request.headers), indent=4, sort_keys=True),
                "method": request.method,
                "error": str(traceback.format_exc()),
            },
            status_code=500
        )


app.middleware('http')(catch_exceptions_middleware)
# app.add_middleware(HTTPSRedirectMiddleware)


"""НАСТРОЙКА РОУТИНГА"""

app.include_router(apihandler.router, prefix=Routes.API_PREFIX.value)
app.include_router(auth.router, prefix=Routes.SUDP_PREFIX.value)
app.include_router(proc.router, prefix=Routes.SUDP_PREFIX.value)
app.include_router(creation.router, prefix=Routes.SUDP_PREFIX.value)
app.include_router(monitoring.router, prefix=Routes.SUDP_PREFIX.value)
app.include_router(passages_report.router, prefix=Routes.SUDP_PREFIX.value)
app.include_router(requests_reports.router, prefix=Routes.SUDP_PREFIX.value)
app.include_router(edit_request.router, prefix=Routes.SUDP_PREFIX.value)
app.include_router(users_management.router, prefix=Routes.SUDP_PREFIX.value)

@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url='/docs')
