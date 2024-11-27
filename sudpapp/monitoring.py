import json
import os
from datetime import datetime
from fastapi import APIRouter
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette_wtf import csrf_protect
import jwt

from api.enums import RequestType, OnTerritoryMode
from .appconfig import templates
from .utils import build_request, _process_raw_request
from .forms import (
    PassageForm,
    ExitForm,
    SpecTransportForm,
    SPECTYPES, PASSAGE_MODES
)

router = APIRouter()


async def _process(request: Request):
    try:
        access_token = request.cookies.get('access_token')
        role = request.cookies.get('role')

        if not access_token or not role:
            return RedirectResponse(url='/sudpapp/auth')

        decoded_jwt = jwt.decode(access_token,
                                 key=os.environ.get('SECRETKEY'),
                                 algorithms=[os.environ.get('ALGORITHM'), ])

        creator = f"{decoded_jwt['name'][0]}. {decoded_jwt['patronymic'][0]}. {decoded_jwt['lastname']}"

        request_id = request.query_params.get('request', None)

        print("monitoring init")

        raw_actual_requests = await build_request(
            url="host.docker.internal:8000/" + "api/v1/read/requests/actual?monitoring=true",
            access_token=access_token
        )


        actual_requests, choices, request_type = await _process_raw_request(raw_actual_requests.json(), request_id)

        for areq in actual_requests:

            if ((areq["passmode"].lower() == dict(PASSAGE_MODES)["3"].lower() and datetime.now().weekday() < 5) or (
                    areq["passmode"].lower() == dict(PASSAGE_MODES)["2"].lower()
                    and 5 <= datetime.now().weekday() <= 6)):
                
                print("passmode failed")
                actual_requests.remove(areq)

        if choices:
            passage_form = PassageForm(request)
            passage_form.request_type = request_type
            passage_form.visitors_radio_group.choices = choices['visitors-checks']
            passage_form.cars_radio_group.choices = choices['cars-checks']

        else:
            passage_form = PassageForm(request)
            passage_form.request_type = request_type

        exit_form = ExitForm(request)
        if request.method == "GET":
            cars_on_territory = await build_request(
                url="host.docker.internal:8000/" + f"api/v1/read/transport/on_territory?mode={OnTerritoryMode.CARS.value}",
                access_token=access_token
            )
            spectransport = await build_request(
                url="host.docker.internal:8000/" + f"api/v1/read/transport/"
                                            f"on_territory?mode={OnTerritoryMode.SPEC_TRANSPORT.value}",
                access_token=access_token
            )

            cars_on_territory_choices = []

            for car in cars_on_territory.json():
                cars_on_territory_choices.append((
                    json.dumps({"type": "car", "id": car['id'], "car_id": car["car_id"]}),
                    f"{car['car']['govern_num']} {car['car']['carmodel']}"
                ))

            for car in spectransport.json():
                cars_on_territory_choices.append((
                    json.dumps({"type": "spectransport",
                                "id": car['id'],
                                'govern_num': car['govern_num'],
                                'spec_type': car['type'],
                                'model': car['model']}),
                    f"{car['govern_num']}\n{car['type']}\n{car['model']}"
                ))

            exit_form.cars_on_terr_field.choices = cars_on_territory_choices


        if request.method == "POST" and await passage_form.validate():
            form_data = dict(await request.form())
            print(form_data, " <-- form")
            if "visitors_radio_group" in form_data.keys() or "cars_radio_group" in form_data.keys():
                for r in actual_requests:
                    if request_id == str(r['id']) and r['type'] == RequestType.DISPOSABLE.value.upper():
                        print(r['passcount'] + 1, " <-- update")
                        await build_request(
                            url=str(
                                request.base_url) + f"api/v1/update/request/passcount/"
                                                    f"{request_id}?count={r['passcount'] + 1}",
                            access_token=access_token,
                            method="PUT",
                        )

                        print("--> passcount updated")

                        if r['passcount'] + 1 == (len(r['visitor']) + len(r['car'])):
                            await build_request(
                                url="host.docker.internal:8000/" + f"api/v1/update/request/close/{request_id}",
                                access_token=access_token,
                                method="POST",
                            )
                        break
            if "visitors_radio_group" in form_data.keys():
                await build_request(
                    data={
                        "status": "ПРОХОД",
                        "v_id": form_data['visitors_radio_group'],
                        "pass_date": datetime.now().isoformat()
                    },
                    method="POST",
                    url="host.docker.internal:8000/" + f"api/v1/create/passage/visitor",
                    access_token=access_token
                )
                print("PUT update")
                await build_request(
                    method="PUT",
                    url="host.docker.internal:8000/" + f"api/v1/update/visitor/passed/"
                                                f"{form_data['visitors_radio_group']}?passmode=true",
                    access_token=access_token
                )

                return RedirectResponse(url=f'/sudpapp/monitoring?request={request_id}',
                                        status_code=status.HTTP_302_FOUND)
            elif "cars_radio_group" in form_data.keys():
                await build_request(
                    data={
                        "c_id": form_data['cars_radio_group'],
                        "status": "ВЪЕЗД",
                        "pass_date": datetime.now().isoformat()
                    },
                    method="POST",
                    url="host.docker.internal:8000/" + f"api/v1/create/passage/car",
                    access_token=access_token
                )
                await build_request(
                    method="PUT",
                    url=str(
                        request.base_url) + f"api/v1/update/car/passed/{form_data['cars_radio_group']}?passmode=true",
                    access_token=access_token
                )
                await build_request(
                    data={
                        "car_id": form_data['cars_radio_group']
                    },
                    method="POST",
                    url="host.docker.internal:8000/" + f"api/v1/create/on_terr/car",
                    access_token=access_token
                )

                return RedirectResponse(url=f'/sudpapp/monitoring?request={request_id}',
                                        status_code=status.HTTP_302_FOUND)

        if request.method == "POST" and await exit_form.validate():
            form_data = dict(await request.form())
            if "cars_on_terr_field" in form_data.keys():
                exit_value = json.loads(form_data["cars_on_terr_field"])
                if exit_value['type'] == 'spectransport':
                    await build_request(
                        data={
                            "type": exit_value['spec_type'],
                            "govern_num": exit_value['govern_num'].upper().replace(" ", ""),
                            "status": "ВЫЕЗД",
                            "model": exit_value['model'],
                            "pass_date": datetime.now().isoformat()
                        },
                        method="POST",
                        url="host.docker.internal:8000/" + f"api/v1/create/passage/spectransport",
                        access_token=access_token
                    )
                    await build_request(
                        method="DELETE",
                        url="host.docker.internal:8000/" + f"api/v1/delete/on_terr/spec_trans/{exit_value['id']}",
                        access_token=access_token
                    )
                    return RedirectResponse(url=f'/sudpapp/monitoring', status_code=status.HTTP_302_FOUND)
                elif exit_value['type'] == 'car':
                    await build_request(
                        data={
                            "c_id": exit_value['car_id'],
                            "status": "ВЫЕЗД",
                            "pass_date": datetime.now().isoformat()
                        },
                        method="POST",
                        url="host.docker.internal:8000/" + f"api/v1/create/passage/car",
                        access_token=access_token
                    )

                    await build_request(
                        method="DELETE",
                        url="host.docker.internal:8000/" + f"api/v1/delete/on_terr/car/{exit_value['id']}",
                        access_token=access_token
                    )
                    return RedirectResponse(url=f'/sudpapp/monitoring', status_code=status.HTTP_302_FOUND)

        spectransport_form = await SpecTransportForm.from_formdata(request)

        if await spectransport_form.validate_on_submit():
            if spectransport_form.pass_spec_submit.data:
                await build_request(
                    data={
                        "type": dict(SPECTYPES)[spectransport_form.type_field.data],
                        "govern_num": spectransport_form.govern_num_field.data.upper().replace(" ", ""),
                        "status": "ВЪЕЗД",
                        "model": spectransport_form.model_field.data.upper(),
                        "pass_date": datetime.now().isoformat()
                    },
                    method="POST",
                    url="host.docker.internal:8000/" + f"api/v1/create/passage/spectransport",
                    access_token=access_token
                )
                await build_request(
                    url="host.docker.internal:8000/" + f"api/v1/create/on_terr/spectransport",
                    access_token=access_token,
                    method="POST",
                    data={
                        "type": dict(SPECTYPES)[spectransport_form.type_field.data],
                        "govern_num": spectransport_form.govern_num_field.data.upper().replace(" ", ""),
                        "model": spectransport_form.model_field.data.upper()
                    }
                )
                return RedirectResponse(url=f'/sudpapp/monitoring', status_code=status.HTTP_302_FOUND)

        response = templates.TemplateResponse(
            request=request,
            name="html/monitoring.html",
            context={
                "actual_requests": actual_requests,
                "passage_form": passage_form,
                "exit_form": exit_form,
                "spectransport_form": spectransport_form,
                "role": role,
                "user": creator
            })

        return response
    except jwt.exceptions.ExpiredSignatureError:
        return RedirectResponse(url='/sudpapp/auth')


@router.route('/monitoring', methods=["GET", "POST"])
@csrf_protect
async def monitoring(request: Request):
    return await _process(request)
