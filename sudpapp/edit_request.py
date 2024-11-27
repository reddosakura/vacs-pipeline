import json
import os

import uuid
from datetime import datetime
from pprint import pprint

import aiofiles
from fastapi import APIRouter
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse, PlainTextResponse
from starlette_wtf import csrf_protect
import jwt
from api.schemas import MainRequestsSchema
from .appconfig import templates, UPLOAD_FOLDER
from api.enums import RequestStatus, RequestType
from .utils import build_request, _upload_list_data, _check_date, _validate_visitors, \
    _validate_cars
from .forms import RequestForm, UploadListForm, UpdateRequestForm, VisitorSubForm, CarSubForm
from .forms import TYPES, TIME_INTERVALS, PASSAGE_MODES
from werkzeug.utils import secure_filename

router = APIRouter()


async def _send_request(request: Request, _id: int):
    try:
        access_token = request.cookies.get('access_token')

        if not access_token:
            return RedirectResponse(url='/sudpapp/auth')

        decoded_jwt = jwt.decode(access_token,
                                 key=os.environ.get('SECRETKEY'),
                                 algorithms=[os.environ.get('ALGORITHM'), ])

        creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

        internal_id = request.cookies.get('intr_request_id')

        form = await UpdateRequestForm.from_formdata(request)
        upload_list_form = await UploadListForm.from_formdata(request)

        if await upload_list_form.validate_on_submit():
            if upload_list_form.data.get("upload"):
                return await _upload_list_data(request, await upload_list_form.data.get("list_file").read(),
                                               creator=creator)

        if await form.validate_on_submit():

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
                from_time = datetime.strptime('00:00', "%H:%M").time().isoformat()
                to_time = datetime.strptime('23:59', "%H:%M").time().isoformat()
            else:
                interval = dict(TIME_INTERVALS)[form_data['time_interval']]
                from_time = datetime.strptime(interval.split()[1], "%H:%M").time().isoformat()
                to_time = datetime.strptime(interval.split()[-1], "%H:%M").time().isoformat()

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
                "contract_name": form_data['contract_name'],
                "organization": form_data['organization'],
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "from_time": from_time,
                "to_time": to_time,
                "comment": form_data['comment'],
                "files": "Нет прикрепленных файлов" if not files["filenames"] else json.dumps(files),
                "created_date": datetime.now().isoformat(),
                "status": request_status,
                "passcount": 0,
                "passmode": dict(PASSAGE_MODES)[form_data['passage_mode']],
            }

            pprint(request_base)
            print("<-- Request base")
            _request = await build_request(
                "host.docker.internal:8000/" + f"api/v1/read/request/{_id}",
                access_token=access_token,
            )

            request_json = _request.json()

            request_object = MainRequestsSchema.parse_obj(request_json)

            additional_data = {
                "passed": False,
                "is_deleted": False,
                "date_created": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                "date_deleted": None,
                "req_intr_id": internal_id
            }

            # delete_passages_visitors = await build_request(
            #     "host.docker.internal:8000/" + "api/v1/update/bulk/visitors",
            #     data=[{
            #               "id": visitor.id,
            #               "lastname": visitor.lastname.upper(),
            #               "name": visitor.name.upper(),
            #               "patronymic": visitor.patronymic.upper()
            #               if visitor.patronymic else str(),
            #               "passed": False,
            #               "is_deleted": visitor.is_deleted,
            #               "date_created": visitor.date_created.isoformat(),
            #               "date_deleted": None,
            #               "req_intr_id": internal_id
            #           } for visitor in request_object.visitor],
            #     method="PUT",
            #     access_token=access_token
            # )
            #
            # delete_passages_cars = await build_request(
            #     "host.docker.internal:8000/" + "api/v1/update/bulk/cars",
            #     data=[{
            #               "id": car.id,
            #               "carmodel": car.carmodel.upper() if car.carmodel.upper() else str(),
            #               "govern_num": car.govern_num.upper().replace(" ", ""),
            #               "passed": False,
            #               "is_deleted": car.is_deleted,
            #               "date_created": car.date_created.isoformat(),
            #               "date_deleted": None,
            #               "req_intr_id": internal_id
            #           } for car in request_object.car],
            #     method="PUT",
            #     access_token=access_token
            # )
            #
            # if delete_passages_visitors.status_code == 401:
            #     return RedirectResponse(url='/sudpapp/auth')
            #
            # if delete_passages_cars.status_code == 401:
            #     return RedirectResponse(url='/sudpapp/auth')

            req = await build_request(
                "host.docker.internal:8000/" + f"api/v1/update/request/{_id}",
                data=request_base,
                method="PUT",
                access_token=access_token
            )

            if req.status_code == 401:
                return RedirectResponse(url='/sudpapp/auth')

            if form_data["visitor"]:
                updated_visitors = []
                additional_visitors = []
                deleted_visitors = []
                updated_ids = []
                added_ids = []
                form_visitors = form.visitor.data
                print(form_visitors)
                for u_visitor in form_visitors:
                    if u_visitor["v_id"] is None:
                        additional_visitors.append(
                            {
                                "lastname": u_visitor["lastname"].upper() if u_visitor["lastname"] else str(),
                                "name": u_visitor["name"].upper() if u_visitor["name"] else str(),
                                "patronymic": u_visitor["patronymic"].upper()
                                if u_visitor["patronymic"] else str()
                            } | additional_data)
                        added_ids.append(u_visitor["v_id"])

                for u_visitor in form_visitors:
                    for a_visitor in request_object.visitor:
                        if str(u_visitor["v_id"]) == str(a_visitor.id):
                            print("update " + str(a_visitor.id))
                            if list(u_visitor.values()) != [a_visitor.lastname,
                                                            a_visitor.name,
                                                            a_visitor.patronymic,
                                                            a_visitor.id]:
                                updated_visitors.append(
                                    {
                                        "id": a_visitor.id,
                                        "lastname": u_visitor["lastname"].upper(),
                                        "name": u_visitor["name"].upper(),
                                        "patronymic": u_visitor["patronymic"].upper()
                                        if u_visitor["patronymic"] else str()
                                    } | additional_data)
                                updated_ids.append(a_visitor.id)

                for a_visitor in request_object.visitor:
                    if (({"lastname": a_visitor.lastname, "name": a_visitor.name,
                          "patronymic": a_visitor.patronymic, "v_id": a_visitor.id} not in form_visitors)
                            and (a_visitor.id not in updated_ids and a_visitor.id not in added_ids)
                            and not a_visitor.is_deleted):
                        a_visitor.date_deleted = datetime.now().isoformat()
                        a_visitor.is_deleted = True
                        if a_visitor.date_created is not None and not isinstance(a_visitor.date_created, str):
                            a_visitor.date_created = a_visitor.date_created.isoformat()
                        deleted_visitors.append(a_visitor.model_dump())

                if additional_visitors:
                    await build_request(
                        "host.docker.internal:8000/" + "api/v1/create/visitors",
                        data=additional_visitors,
                        method="POST",
                        access_token=access_token
                    )

                if updated_visitors:
                    await build_request(
                        "host.docker.internal:8000/" + "api/v1/update/bulk/visitors",
                        data=updated_visitors,
                        method="PUT",
                        access_token=access_token
                    )
                if deleted_visitors:
                    await build_request(
                        "host.docker.internal:8000/" + "api/v1/update/bulk/visitors",
                        data=deleted_visitors,
                        method="PUT",
                        access_token=access_token
                    )

            elif not form_data["visitor"]:

                deleted_visitors = []

                for a_visitor in request_object.visitor:
                    a_visitor.date_deleted = datetime.now().isoformat()
                    a_visitor.is_deleted = True
                    if a_visitor.date_created is not None and not isinstance(a_visitor.date_created, str):
                        a_visitor.date_created = a_visitor.date_created.isoformat()
                    deleted_visitors.append(a_visitor.model_dump())

                if deleted_visitors:
                    await build_request(
                        "host.docker.internal:8000/" + "api/v1/update/bulk/visitors",
                        data=deleted_visitors,
                        method="PUT",
                        access_token=access_token
                    )

            if form_data["car"]:
                updated_cars = []
                additional_cars = []
                updated_ids = []
                deleted_cars = []
                added_ids = []
                form_cars = form.car.data
                print(form_cars, "<-- form data car")
                for u_car in form_cars:
                    if u_car["c_id"] is None:
                        additional_cars.append(
                            {
                                "carmodel": u_car["carmodel"].upper() if u_car["carmodel"] else str(),
                                "govern_num": u_car["govern_num"].upper().replace(" ", "") if u_car[
                                    "govern_num"] else str(),
                            } | additional_data)
                        added_ids.append(u_car["c_id"])

                for u_car in form_cars:
                    for a_car in request_object.car:
                        if str(u_car["c_id"]) == str(a_car.id):
                            if list(u_car.values()) != [a_car.carmodel, a_car.govern_num, a_car.id]:
                                updated_cars.append(
                                    {
                                        "id": a_car.id,
                                        "carmodel": u_car["carmodel"].upper() if u_car["carmodel"] else str(),
                                        "govern_num": u_car["govern_num"].upper().replace(" ", "")
                                        if u_car["govern_num"] else str(),
                                    } | additional_data)
                                updated_ids.append(a_car.id)
                for a_car in request_object.car:
                    if ({"carmodel": a_car.carmodel, "govern_num": a_car.govern_num, "c_id": a_car.id}
                            not in form.car.data and a_car.id not in updated_ids and a_car.id not in added_ids):
                        a_car.date_deleted = datetime.now().isoformat()
                        a_car.is_deleted = True
                        if a_car.date_created is not None and not isinstance(a_car.date_created, str):
                            a_car.date_created = a_car.date_created.isoformat()
                        deleted_cars.append(a_car.model_dump())

                if additional_cars:
                    await build_request(
                        "host.docker.internal:8000/" + "api/v1/create/cars",
                        data=additional_cars,
                        method="POST",
                        access_token=access_token
                    )

                if updated_cars:
                    await build_request(
                        "host.docker.internal:8000/" + "api/v1/update/bulk/cars",
                        data=updated_cars,
                        method="PUT",
                        access_token=access_token
                    )

                if deleted_cars:
                    await build_request(
                        "host.docker.internal:8000/" + "api/v1/update/bulk/cars",
                        data=deleted_cars,
                        method="PUT",
                        access_token=access_token
                    )
            elif not form_data["car"]:
                deleted_cars = []
                for a_car in request_object.car:

                    a_car.date_deleted = datetime.now().isoformat()
                    a_car.is_deleted = True
                    if a_car.date_created is not None and not isinstance(a_car.date_created, str):
                        a_car.date_created = a_car.date_created.isoformat()
                    deleted_cars.append(a_car.model_dump())

                if deleted_cars:
                    await build_request(
                        "host.docker.internal:8000/" + "api/v1/update/bulk/cars",
                        data=deleted_cars,
                        method="PUT",
                        access_token=access_token
                    )

            return RedirectResponse(url='/sudpapp/requests/my', status_code=status.HTTP_302_FOUND)

        return PlainTextResponse("???")

    except jwt.exceptions.ExpiredSignatureError:
        return RedirectResponse(url='/sudpapp/auth')


@router.get("/requests/edit/{_id}")
async def editing(request: Request, _id: int):
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')

    decoded_jwt = jwt.decode(access_token,
                             key=os.environ.get('SECRETKEY'),
                             algorithms=[os.environ.get('ALGORITHM'), ])

    creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

    form = await UpdateRequestForm.from_formdata(request)

    _request = await build_request(
        "host.docker.internal:8000/" + f"api/v1/read/request/{_id}",
        access_token=access_token,
    )

    request_json = _request.json()

    request_object = MainRequestsSchema.parse_obj(request_json)
    upload_list_form = await UploadListForm(obj=request_object, request=request).from_formdata(request)

    form.organization.data = request_object.organization
    form.comment.data = request_object.comment
    form.from_date.data = request_object.from_date
    form.to_date.data = request_object.to_date
    form.contract_name.data = request_object.contract_name

    for t in dict(TYPES):
        if dict(TYPES)[t] == request_object.type.upper():
            form.type.data = t
            break

    for m in dict(PASSAGE_MODES):
        if dict(PASSAGE_MODES)[m] == request_object.passmode:
            form.passage_mode.data = m
            break

    for i in dict(TIME_INTERVALS):
        if (dict(TIME_INTERVALS)[i] == f"С {request_object.from_time.strftime('%H:%M')} ДО "
                                       f"{request_object.to_time.strftime('%H:%M')}" or
                (dict(TIME_INTERVALS)[i] == "КРУГЛОСУТОЧНО") and
                (f"С {request_object.from_time.strftime('%H:%M')} ДО {request_object.to_time.strftime('%H:%M')}" ==
                 "С 00:00 ДО 23:59")):
            form.time_interval.data = i
            break

    for v in request_object.visitor:
        if not v.is_deleted:
            visitor_form = VisitorSubForm()
            visitor_form.v_id = v.id
            visitor_form.lastname = v.lastname
            visitor_form.name = v.name
            visitor_form.patronymic = v.patronymic
            form.visitor.append_entry(visitor_form)

    for c in request_object.car:
        if not c.is_deleted:
            car_form = CarSubForm()
            car_form.c_id = c.id
            car_form.carmodel = c.carmodel
            car_form.govern_num = c.govern_num
            form.car.append_entry(car_form)

    response = templates.TemplateResponse(
        request=request,
        name="html/request_editing.html",
        context={
            "request": request,
            "form": form,
            "_id": _id,
            "upload_list_form": upload_list_form,
            "uploaded_visitors": [],
            "uploaded_cars": [],
            "role": role,
            "user": creator
        })

    response.set_cookie("intr_request_id", request_object.internal_req_id)

    return response


@router.post("/requests/edit/{_id}")
@csrf_protect
async def editing(request: Request, _id: int):
    return await _send_request(request, _id)
