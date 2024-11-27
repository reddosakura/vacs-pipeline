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

from api.enums import RequestType, OnTerritoryMode, PassageReportsMode, RequestStatus
from .appconfig import templates
from .forms import SearchForm, FilterForm, RecallForm, DeleteRequestForm
from .utils import build_request, _process_raw_request

router = APIRouter()


# @router.get("/reports")
@router.route('/reports', methods=["GET", "POST"])
@csrf_protect
async def _reports(request: Request):
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')
    try:
        decoded_jwt = jwt.decode(access_token,
                                 key=os.environ.get('SECRETKEY'),
                                 algorithms=[os.environ.get('ALGORITHM'),])

        creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"
    except JWTError:
        return RedirectResponse(url='/sudpapp/auth')

    search_form = await SearchForm.from_formdata(request)
    filter_form = await FilterForm.from_formdata(request)
    recall_form = await RecallForm.from_formdata(request)
    # delete_form = await DeleteRequestForm.from_formdata(request)

    if await search_form.validate_on_submit():
        print("search validated")
        if search_form.search_submit.data:
            if search_form.search_field.data == "":
                return RedirectResponse(url='/sudpapp/reports', status_code=status.HTTP_302_FOUND)

            url = "host.docker.internal:8000/" + f"api/v1/read/search/{search_form.search_field.data}?monitoring=false"
            print(request.cookies.get("is_requests_filtered"), "<-- filtred")
            if request.cookies.get("is_requests_filtered") != "False":
                url = str(
                    request.base_url) + f"api/v1/read/search/{search_form.search_field.data}?monitoring=false&is_filtered=true&fdate={request.cookies.get('fdate_requests')}&tdate={request.cookies.get('tdate_requests')}"

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
                "filter_form": filter_form,
                "recall_form": recall_form,
                "role": role,
                "user": creator
            }

            response = templates.TemplateResponse(
                request=request,
                name="html/request_reports.html",
                context=context
            )

            if not request.cookies.get("is_requests_filtered"):
                response.set_cookie("is_requests_filtered", False)

            return response

    if await filter_form.validate_on_submit():
        if filter_form.apply_button.data:
            raw_actual_requests = await build_request(
                url=str(
                    request.base_url) + f"api/v1/read/requests/actual?monitoring=false&fdate={filter_form.filter_fdate.data}&tdate={filter_form.filter_tdate.data}&is_filtered=true",
                access_token=access_token
            )

            actual_requests = (await _process_raw_request(raw_actual_requests.json(), str()))[0]

            print(actual_requests)

            context = {
                'actual_requests': actual_requests,
                "search_form": search_form,
                "filter_form": filter_form,
                "recall_form": recall_form,
                "role": role,
                "user": creator
            }

            response = templates.TemplateResponse(
                request=request,
                name="html/request_reports.html",
                context=context
            )

            response.set_cookie("fdate_requests", filter_form.filter_fdate.data)
            response.set_cookie("tdate_requests", filter_form.filter_tdate.data)
            response.set_cookie("is_requests_filtered", True)

            return response
        elif filter_form.reset_button.data:
            response = RedirectResponse(url='/sudpapp/reports', status_code=status.HTTP_302_FOUND)
            response.set_cookie("fdate_requests", str(filter_form.filter_fdate.data))
            response.set_cookie("tdate_requests", str(filter_form.filter_tdate.data))
            response.set_cookie("is_requests_filtered", str(False))

            return response

    if await recall_form.validate_on_submit():
        if recall_form.recall_button.data:
            try:
                request_id = request.query_params.get('request', None)
                req = await build_request(
                    "host.docker.internal:8000/" + f"api/v1/update/request/status/{{req_id}}?req_id={request_id}",
                    data={
                        "status": "ОТОЗВАНА",
                        "comment": f"Отозвал(а) {creator}:\n"
                    },
                    method="POST",
                    access_token=access_token
                )

                if req.status_code == 401:
                    return RedirectResponse(url='/sudpapp/auth')

                return RedirectResponse(url='/sudpapp/reports', status_code=status.HTTP_302_FOUND)
            except JWTError:
                return RedirectResponse(url='/sudpapp/auth')

    raw_actual_requests = await build_request(
        url="host.docker.internal:8000/" + "api/v1/read/requests/actual?monitoring=false",
        access_token=access_token
    )

    actual_requests = (await _process_raw_request(raw_actual_requests.json(), str()))[0]

    context = {
        'actual_requests': actual_requests,
        "search_form": search_form,
        "filter_form": filter_form,
        "recall_form": recall_form,
        "role": role,
        "user": creator
    }

    response = templates.TemplateResponse(
        request=request,
        name="html/request_reports.html",
        context=context
    )
    if not request.cookies.get("is_requests_filtered"):
        response.set_cookie("is_requests_filtered", False)

    return response
