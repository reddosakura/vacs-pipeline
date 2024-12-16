import os
from datetime import datetime

import jwt
from fastapi import APIRouter
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette_wtf import csrf_protect
from .appconfig import templates
from .forms import SearchForm, FilterForm
from .utils import build_request

router = APIRouter()


async def format_date(passages: dict) -> dict:
    for passage in passages:
        print(passage)
        passage['time'] = datetime.fromisoformat(passage['pass_date']).strftime("%H:%M")
        passage['fdate'] = datetime.fromisoformat(passage['pass_date']).strftime("%d.%m.%Y")
    return passages


# @router.get("/passages")
@router.route('/passages', methods=["GET", "POST"])
@csrf_protect
async def _passages(request: Request):
    access_token = request.cookies.get('access_token')
    role = request.cookies.get('role')

    search_form = await SearchForm.from_formdata(request)
    filter_form = await FilterForm.from_formdata(request)

    if not access_token or not role:
        return RedirectResponse(url='/sudpapp/auth')

    decoded_jwt = jwt.decode(access_token,
                             key=os.environ.get('SECRETKEY'),
                             algorithms=[os.environ.get('ALGORITHM'), ])

    creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

    if await search_form.validate_on_submit():
        print("search validated")
        if search_form.search_submit.data:
            if search_form.search_field.data == "":
                return RedirectResponse(url='/sudpapp/passages', status_code=status.HTTP_302_FOUND)
            url = str(
                request.base_url) + (f"api/v1/read/passages/search?search_value={search_form.search_field.data}"
                                     f"&fdate=2024-05-20&tdate=2024-05-20&is_filtered=false")
            print(request.cookies.get("is_filtered"), "<-- filtered")
            if request.cookies.get("is_filtered") != "False":
                url = str(
                    request.base_url) + (f"api/v1/read/passages/search?search_value={search_form.search_field.data}"
                                         f"&fdate={request.cookies.get('fdate')}"
                                         f"&tdate={request.cookies.get('tdate')}&is_filtered=true")

            search_response = await build_request(
                url=url,
                access_token=access_token,
            )

            cars = search_response.json()['cars']
            visitors = search_response.json()['visitors']
            spectransport = search_response.json()['spectransport']

            formatted_v_passages = await format_date(visitors)
            formatted_c_passages = await format_date(cars)
            formatted_s_passages = await format_date(spectransport)

            context = {
                'v_passages': formatted_v_passages,
                'c_passages': formatted_c_passages,
                's_passages': formatted_s_passages,
                'search_form': search_form,
                'filter_form': filter_form,
                "role": role,
                "user": creator
            }

            response = templates.TemplateResponse(
                request=request,
                name="html/passage_reports.html",
                context=context
            )

            if not request.cookies.get("is_filtered"):
                response.set_cookie("is_filtered", False)

            return response

    if await filter_form.validate_on_submit():
        if filter_form.apply_button.data:
            passages = await build_request(
                url=str(
                    request.base_url) + f"api/v1/read/passages/actual?fdate={filter_form.filter_fdate.data}"
                                        f"&tdate={filter_form.filter_tdate.data}",
                access_token=access_token
            )

            print(passages.json(), "<- response")

            formatted_v_passages = await format_date(passages.json()['visitors'])
            formatted_c_passages = await format_date(passages.json()['cars'])
            formatted_s_passages = await format_date(passages.json()['spectransport'])

            context = {
                'v_passages': formatted_v_passages,
                'c_passages': formatted_c_passages,
                's_passages': formatted_s_passages,
                'search_form': search_form,
                'filter_form': filter_form,
                "role": role,
                "user": creator
            }

            response = templates.TemplateResponse(
                request=request,
                name="html/passage_reports.html",
                context=context
            )

            response.set_cookie("fdate", filter_form.filter_fdate.data)
            response.set_cookie("tdate", filter_form.filter_tdate.data)
            response.set_cookie("is_filtered", True)

            return response
        elif filter_form.reset_button.data:
            response = RedirectResponse(url='/sudpapp/passages', status_code=status.HTTP_302_FOUND)
            response.set_cookie("fdate", str(filter_form.filter_fdate.data))
            response.set_cookie("tdate", str(filter_form.filter_tdate.data))
            response.set_cookie("is_filtered", str(False))

            return response

    passages = await build_request(
        url="http://host.docker.internal:5768/" + f"api/v1/read/passages/actual",
        access_token=access_token
    )

    formatted_v_passages = await format_date(passages.json()['visitors'])
    formatted_c_passages = await format_date(passages.json()['cars'])
    formatted_s_passages = await format_date(passages.json()['spectransport'])

    context = {
        'v_passages': formatted_v_passages,
        'c_passages': formatted_c_passages,
        's_passages': formatted_s_passages,
        'search_form': search_form,
        'filter_form': filter_form,
        "role": role,
        "user": creator
    }

    response = templates.TemplateResponse(
        request=request,
        name="html/passage_reports.html",
        context=context
    )

    if not request.cookies.get("is_filtered"):
        response.set_cookie("is_filtered", False)

    return response
