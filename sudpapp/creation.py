import json
import os
import uuid
from datetime import datetime
import aiofiles
from fastapi import APIRouter
from jose import JWTError
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette_wtf import csrf_protect
import jwt
from .appconfig import templates, UPLOAD_FOLDER
from api.enums import RequestStatus, RequestType
from .utils import build_request, _process_raw_request, _upload_list_data, _check_date, \
    _validate_visitors, _validate_cars
from .forms import RequestForm, SearchForm, RecallForm, DeleteRequestForm
from .forms import TYPES, TIME_INTERVALS, PASSAGE_MODES
from werkzeug.utils import secure_filename

router = APIRouter()


async def _send_request(request: Request):
    try:
        access_token = request.cookies.get('access_token')

        if not access_token:
            return RedirectResponse(url='/sudpapp/auth')

        decoded_jwt = jwt.decode(access_token,
                                 key=os.environ.get('SECRETKEY'),
                                 algorithms=[os.environ.get('ALGORITHM'),])

        creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

        form = await RequestForm.from_formdata(request)


        if await form.validate_on_submit():
            internal_id = uuid.uuid4().time_low

            form_data = form.data
            print(form_data, "<-- form data files")

            files = {"filenames": []}

            if form.add_files_btn.data[0].size != 0:
                for file in form.data.get("add_files_btn"):
                    filename = str(uuid.uuid4().time) + "." + secure_filename(file.filename)

                    async with aiofiles.open(UPLOAD_FOLDER + filename, "wb") as f:
                        await f.write(await file.read())

                    files["filenames"].append(filename)

            if form_data['time_interval'] == "9":
                from_time = datetime.strptime('00:00', "%H:%M").time().strftime("%H:%M")
                to_time = datetime.strptime('23:59', "%H:%M").time().strftime("%H:%M")
            else:
                interval = dict(TIME_INTERVALS)[form_data['time_interval']]
                from_time = datetime.strptime(interval.split()[1], "%H:%M").time().strftime("%H:%M")
                to_time = datetime.strptime(interval.split()[-1], "%H:%M").time().strftime("%H:%M")

            from_date = form_data['from_date']
            to_date = form_data['to_date']
            request_type = dict(TYPES)[form_data['type']]

            if ((request_type == RequestType.REUSABLE.value.upper() and (to_date - from_date).days != 0)
                    or (request_type == RequestType.DISPOSABLE.value.upper() and (to_date - from_date).days > 0)
                    or (request_type == RequestType.DISPOSABLE.value.upper() and (to_date - from_date).days == 0
                        and from_date.weekday() in [5, 6])
                    or (request_type == RequestType.DISPOSABLE.value.upper()
                        and (to_date - from_date).days == 0 and await _check_date(request, from_date))):
                request_status = RequestStatus.APPROVE.value
            else:
                request_status = RequestStatus.CONSIDERATION.value

            request_base = {
                "creator": creator,
                "type": request_type,
                "contract_name": form_data['contract'],
                "organization": form_data['organization'],
                "from_date": from_date.strftime('%Y-%m-%d'),
                "to_date": to_date.strftime('%Y-%m-%d'),
                "from_time": from_time,
                "to_time": to_time,
                "comment": form_data['comment'],
                "files": "Нет прикрепленных файлов" if not files["filenames"] else json.dumps(files),
                "created_date": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                "status": request_status,
                "passcount": 0,
                "passmode": dict(PASSAGE_MODES)[form_data['passage_mode']],
                "internal_req_id": internal_id
            }

            print(request_base, "<-- Request")

            req = await build_request(
                "http://host.docker.internal:5768/" + "api/v1/create/request",
                data=request_base,
                method="POST",
                access_token=access_token
            )

            if req.status_code == 401:
                return RedirectResponse(url='/sudpapp/auth')

            additional_data = {
                "passed": False,
                "is_deleted": False,
                "date_created": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                "date_deleted": None,
                "req_intr_id": internal_id
            }

            if form_data["visitors_list"]:
                await build_request(
                    "http://host.docker.internal:5768/" + "api/v1/create/visitors",
                    data=[await _validate_visitors(v) | additional_data for v in form_data['visitors_list']],
                    method="POST",
                    access_token=access_token
                )

            if form_data["cars_list"]:
                await build_request(
                    "http://host.docker.internal:5768/" + "api/v1/create/cars",
                    data=[await _validate_cars(c) | additional_data for c in form_data['cars_list']],
                    method="POST",
                    access_token=access_token
                )

            return RedirectResponse(url='/sudpapp/requests/my', status_code=status.HTTP_302_FOUND)

    except jwt.exceptions.ExpiredSignatureError:
        return RedirectResponse(url='/sudpapp/auth')


@router.get("/requests/creation")
async def creation(request: Request):
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')

    decoded_jwt = jwt.decode(access_token,
                             key=os.environ.get('SECRETKEY'),
                             algorithms=[os.environ.get('ALGORITHM'), ])

    creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

    form = await RequestForm.from_formdata(request)


    return templates.TemplateResponse(
        request=request,
        name="html/request_creation.html",
        context={
            "request": request,
            "form": form,
            # "upload_list_form": upload_list_form,
            "uploaded_visitors": [],
            "uploaded_cars": [],
            "user": creator,
            "role": role
        })


@router.route('/requests/my', methods=["GET", "POST"])
@csrf_protect
async def creation(request: Request):
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')

    decoded_jwt = jwt.decode(access_token,
                             key=os.environ.get('SECRETKEY'),
                             algorithms=[os.environ.get('ALGORITHM'), ])

    creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

    form = await RequestForm.from_formdata(request)

    search_form = await SearchForm.from_formdata(request)
    recall_form = await RecallForm.from_formdata(request)
    delete_form = await DeleteRequestForm.from_formdata(request)

    raw_actual_requests = await build_request(
        url=str(
            request.base_url) + f"api/v1/read/requests/actual?monitoring=false&is_filtered=false&creator={creator}",
        access_token=access_token
    )

    if await search_form.validate_on_submit():
        print("search validated")
        if search_form.search_submit.data:
            if search_form.search_field.data == "":
                return RedirectResponse(url='/sudpapp/requests/my', status_code=status.HTTP_302_FOUND)

            url = ("http://host.docker.internal:5768/" +
                   f"api/v1/read/search/{search_form.search_field.data}?monitoring=false&creator={creator}")

            raw_actual_requests = await build_request(
                url=url,
                access_token=access_token
            )

            print(raw_actual_requests, "<-- searched")

            actual_requests = (await _process_raw_request(raw_actual_requests.json(), str()))[0]

            print(actual_requests)

            context = {
                'actual_requests': actual_requests,
                "search_form": search_form,
                "recall_form": recall_form,
                "delete_form": delete_form,
                "user": creator,
                "role": role,
                "edit": True
            }

            response = templates.TemplateResponse(
                request=request,
                name="html/requestor_reports.html",
                context=context
            )

            return response

    if await recall_form.validate_on_submit():
        if recall_form.recall_button.data:
            try:
                request_id = request.query_params.get('request', None)
                req = await build_request(
                    "http://host.docker.internal:5768/" + f"api/v1/update/request/status/{{req_id}}?req_id={request_id}",
                    data={
                        "status": "ОТОЗВАНА",
                        "comment": f"Отозвал(а) {creator}:\n"
                    },
                    method="POST",
                    access_token=access_token
                )

                if req.status_code == 401:
                    return RedirectResponse(url='/sudpapp/auth')

                return RedirectResponse(url='/sudpapp/requests/my', status_code=status.HTTP_302_FOUND)
            except JWTError:
                return RedirectResponse(url='/sudpapp/auth')

    if await delete_form.validate_on_submit():
        if delete_form.delete_button.data:
            try:
                request_id = request.query_params.get('request', None)
                req = await build_request(
                    "http://host.docker.internal:5768/" + f"api/v1/delete/request/{request_id}",
                    method="PUT",
                    access_token=access_token
                )

                if req.status_code == 401:
                    return RedirectResponse(url='/sudpapp/auth')

                return RedirectResponse(url='/sudpapp/requests/my', status_code=status.HTTP_302_FOUND)
            except JWTError:
                return RedirectResponse(url='/sudpapp/auth')

    actual_requests = (await _process_raw_request(raw_actual_requests.json(), str()))[0]

    return templates.TemplateResponse(
        request=request,
        name="html/requestor_reports.html",
        context={
            "actual_requests": actual_requests,
            "user": creator,
            "form": form,
            "search_form": search_form,
            "recall_form": recall_form,
            "delete_form": delete_form,
            "role": role,
            "edit": True
        })


@router.post("/requests/creation")
@csrf_protect
async def creation(request: Request):
    return await _send_request(request)
