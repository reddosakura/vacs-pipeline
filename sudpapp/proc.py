import datetime
import json
import os

from fastapi import APIRouter, Security
from jose import jwt, JWTError
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse, FileResponse
from starlette_wtf import csrf_protect

from api.apihandler import get_current_active_user
from .appconfig import templates, UPLOAD_FOLDER
from api.enums import RequestStatus, Scopes
from .utils import build_request
from .forms import ProcessRequestForm

router = APIRouter()


async def _get_context(request: Request,
                       mode: str = RequestStatus.APPROVE.value,
                       _id: int = 0) -> templates.TemplateResponse:
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    intr_id = 0

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')

    try:

        decoded_jwt = jwt.decode(access_token,
                                 key=os.environ.get('SECRETKEY'),
                                 algorithms=[os.environ.get('ALGORITHM'), ])
        scopes = decoded_jwt['scopes']

        creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"
    except JWTError:
        return RedirectResponse(url='/sudpapp/auth')

    form = await ProcessRequestForm.from_formdata(request)

    if mode == RequestStatus.APPROVE.value:
        checked_state = True
    else:
        checked_state = False

    url = "http://host.docker.internal:5768/" + f"api/v1/read/requests/actual/min?request_status={mode}"
    if 'admin' in scopes and mode == RequestStatus.APPROVE.value:
        url = "http://host.docker.internal:5768/" + "api/v1/read/requests/actual/min?&forced=true"

    min_requests = await build_request(
        url,
        access_token=access_token
    )

    if min_requests.status_code == 401:
        return RedirectResponse(url='/sudpapp/auth')

    if min_requests.status_code != 404 and json.loads(min_requests.json()) != []:
        min_response_json = json.loads(min_requests.json())

        if _id == 0:
            _id = min_response_json[_id]['id']

        raw_request = await build_request(
            "http://host.docker.internal:5768/" + f"api/v1/read/request/{_id}",
            access_token=access_token
        )
        intr_id = raw_request.json()['internal_req_id']

        print(raw_request.content)

        formatted_request = raw_request.json()
        formatted_request['from_date'] = datetime.datetime.fromisoformat(formatted_request['from_date']).strftime(
            "%d.%m.%Y")
        formatted_request['to_date'] = datetime.datetime.fromisoformat(formatted_request['to_date']).strftime(
            "%d.%m.%Y")
        formatted_request['created_date'] = datetime.datetime.fromisoformat(formatted_request['created_date']
                                                                            ).strftime("%d.%m.%Y %H:%M")
        formatted_request['from_time'] = datetime.datetime.strptime(formatted_request['from_time'],
                                                                    '%H:%M:%S').strftime("%H:%M")
        formatted_request['to_time'] = datetime.datetime.strptime(formatted_request['to_time'], '%H:%M:%S').strftime(
            "%H:%M")
        if formatted_request['approve']:
            formatted_request['approve'][-1]['created_date'] = (
                datetime.datetime.fromisoformat(
                                    formatted_request['approve'][-1]['created_date']
                                  ).strftime("%d.%m.%Y %H:%M"))

        if formatted_request['files'] != 'Нет прикрепленных файлов':
            formatted_request['files'] = json.loads(formatted_request['files'])
        else:
            formatted_request['files'] = None

    else:
        formatted_request = None

    response = templates.TemplateResponse(
        request=request,
        name="html/main_processing.html",
        context={
            "request": request,
            "min_cards": json.loads(
                min_requests.json()) if min_requests.status_code != 404 and min_requests.json() != [] else None,
            "sudp_request": formatted_request,
            "mode": mode,
            "checked_state": checked_state,
            "file_port": os.environ.get("FILEPORT"),
            "form": form,
            "scopes": scopes,
            "role": role,
            "user": creator
        }
    )
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=10)

    response.set_cookie(
        key="request_id",
        value=_id,
        expires=expires
    )
    response.set_cookie(
        key="intr_request_id",
        value=intr_id,
        expires=expires
    )

    return response


async def _process(request: Request,
                   mode: str = RequestStatus.APPROVE.value,
                   _id: int = 0):
    access_token = request.cookies.get('access_token')
    try:

        decoded_jwt = jwt.decode(access_token,
                                 key=os.environ.get('SECRETKEY'),
                                 algorithms=[os.environ.get('ALGORITHM'), ])

        creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

        scopes = jwt.decode(access_token,
                            key=os.environ.get('SECRETKEY'),
                            algorithms=[os.environ.get('ALGORITHM'), ])['scopes']
    except JWTError:
        return RedirectResponse(url='/sudpapp/auth')

    if _id == 0:
        _id = request.cookies.get("request_id")

    if not access_token:
        return RedirectResponse(url='/sudpapp/auth')

    decoded_jwt = jwt.decode(access_token,
                             key=os.environ.get('SECRETKEY'),
                             algorithms=[os.environ.get('ALGORITHM'), ])

    creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

    form = await ProcessRequestForm.from_formdata(request)

    if await form.validate_on_submit():
        try:

            _request = await build_request(
                url="http://host.docker.internal:5768/" + f"api/v1/read/request/{_id}",
                access_token=access_token
            )

            comment = form.data["comment"]

            if _request.json()["approve"]:
                if not form.data["comment"] and _request.json()["approve"][-1]["approval_comments"]:
                    comment = _request.json()["approve"][-1]["approval_comments"]

            process_data = {
                "status": "ОДОБРЕНА" if form.data['allow'] else 'ОТКЛОНЕНА',
                "comment": f"Одобрил(а) {creator}:\n" + comment
                if form.data["allow"] else f"Отклонил(а) {creator}:\n" + comment
            }

            if "admin" not in scopes and mode == RequestStatus.CONSIDERATION.value and form.data["approve"]:
                process_data = {
                    "status": "ПРОШЛА СОГЛАСОВАНИЕ",
                    "comment": form.data["comment"]
                }
                iternal_id = request.cookies.get("intr_request_id")
                await build_request(
                    "http://host.docker.internal:5768/" + f"api/v1/create/approval",
                    data={
                        "lastname": decoded_jwt['lastname'],
                        "name": decoded_jwt['name'],
                        "patronymic": decoded_jwt['patronymic'],
                        "approval_comments": form.data["comment"],
                        "approval_status": "СОГЛАСУЮ" if form.data['approve'] else 'НЕ СОГЛАСУЮ',
                        "intr_req_id": iternal_id,
                        "created_date": datetime.datetime.now().isoformat()
                    },
                    method="POST",
                    access_token=access_token
                )

            if "admin" not in scopes and mode == RequestStatus.APPROVE.value:
                process_data = {
                    "status": "ПРОШЛА СОГЛАСОВАНИЕ" if form.data['allow'] else 'НЕ ПРОШЛА СОГЛАСОВАНИЕ',
                    "comment": form.data["comment"]
                }
                iternal_id = request.cookies.get("intr_request_id")
                await build_request(
                    "http://host.docker.internal:5768/" + f"api/v1/create/approval",
                    data={
                        "lastname": decoded_jwt['lastname'],
                        "name": decoded_jwt['name'],
                        "patronymic": decoded_jwt['patronymic'],
                        "approval_comments": form.data["comment"],
                        "approval_status": "СОГЛАСУЮ" if form.data['allow'] else 'НЕ СОГЛАСУЮ',
                        "intr_req_id": iternal_id,
                        "created_date": datetime.datetime.now().isoformat()
                    },
                    method="POST",
                    access_token=access_token
                )

            req = await build_request(
                "http://host.docker.internal:5768/" + f"api/v1/update/request/status/{{req_id}}?req_id={_id}",
                data=process_data,
                method="POST",
                access_token=access_token
            )

            if req.status_code == 401:
                return RedirectResponse(url='/sudpapp/auth')

            if mode == RequestStatus.APPROVE.value:
                return RedirectResponse(url='/sudpapp/proc/approve', status_code=status.HTTP_302_FOUND)
            return RedirectResponse(url='/sudpapp/proc/consider', status_code=status.HTTP_302_FOUND)
        except JWTError:
            return RedirectResponse(url='/sudpapp/auth')


@router.get("/proc/approve")
async def processing(request: Request):
    return await _get_context(request)


@router.get("/proc/consider")
async def processing(request: Request):
    return await _get_context(request, mode=RequestStatus.CONSIDERATION.value)


@router.get("/proc/consider/{_id}")
async def processing(request: Request,
                     _id: int):
    return await _get_context(request, mode=RequestStatus.CONSIDERATION.value, _id=_id)


@router.get("/proc/approve/{_id}")
async def processing(request: Request,
                     _id: int):
    return await _get_context(request, mode=RequestStatus.APPROVE.value, _id=_id)


@router.get("/proc")
async def processing():
    return RedirectResponse("/sudpapp/proc/approve")


@router.get("/files/{filename}")
async def processing(filename: str):
    return FileResponse(
        path=UPLOAD_FOLDER + filename,
        media_type='application/pdf',
        filename=filename,
        content_disposition_type="inline"
    )


@router.post("/proc/approve/{_id}")
@csrf_protect
async def processing(request: Request,
                     _id: int):
    return await _process(request, RequestStatus.APPROVE.value, _id)


@router.post("/proc/consider/{_id}")
@csrf_protect
async def processing(request: Request,
                     _id: int):
    return await _process(request, RequestStatus.CONSIDERATION.value, _id)


@router.post("/proc/consider")
@csrf_protect
async def processing(request: Request):
    return await _process(request, RequestStatus.CONSIDERATION.value)


@router.post("/proc/approve")
@csrf_protect
async def processing(request: Request):
    return await _process(request, RequestStatus.APPROVE.value)
