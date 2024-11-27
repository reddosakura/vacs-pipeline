import io
import json
import traceback
import zipfile
from datetime import datetime
from pprint import pprint

from docx import Document
import httpx
from httpx import Response
from starlette.responses import PlainTextResponse

from api.enums import RequestType
from .Row import Row
from .appconfig import templates
from .forms import UploadListForm, RequestForm, UpdateRequestForm


async def build_request(url: str,
                        access_token: str,
                        method: str = "GET",
                        data: dict | list[dict] = None) -> Response:
    timeout = httpx.Timeout(10.0, read=None)
    if method == "GET":
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=timeout
            )

    elif method == "POST":
        print(data, "<-- data")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "accept": "*/*",
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                data=json.dumps(data),
                timeout=timeout)
            # print(response.json())

    elif method == "PUT":
        pprint(data)
        print("<-- data")
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                data=json.dumps(data),
                timeout=timeout)
    elif method == "DELETE":
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={
                    "accept": "application/json",
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=timeout)
    return response


def check_table(table: list) -> bool:
    header = list(map(lambda _: _.upper().strip(), table[0].get()))
    if header == ['ФАМИЛИЯ', 'ИМЯ', 'ОТЧЕСТВО'] or \
            header == ['ФАМИЛИЯ', 'ИМЯ', 'ОТЧЕСТВО', 'МАРКА АВТОМОБИЛЯ', 'НОМЕР АВТОМОБИЛЯ'] or \
            header == ['МАРКА АВТОМОБИЛЯ', 'НОМЕР АВТОМОБИЛЯ']:
        return True
    return False


def parse_docx_table(doc: Document) -> list:
    all_tables = []
    for table in doc.tables:
        completed_table = []
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                row_data.append(cell.text.upper())
            completed_table.append(Row(row_data))
        all_tables.append(completed_table)
    return all_tables


async def _process_raw_request(requests: list,
                               request_id: str,
                               choices=None) -> tuple:
    if choices is None:
        choices = {}
    request_type = None
    for sudp_request in requests:
        if str(sudp_request['id']) == request_id:
            choices = {
                'visitors-checks': [(v['id'], f"{v['lastname']} {v['name']} {v['patronymic']}")
                                    for v in sudp_request['visitor'] if not
                                    (sudp_request['type'].upper() == RequestType.DISPOSABLE.value.upper() and
                                     v['passed'])],
                'cars-checks': [(c['id'], f"{c['govern_num']} {c['carmodel']}")
                                for c in sudp_request['car'] if not
                                (sudp_request['type'].upper() == RequestType.DISPOSABLE.value.upper() and
                                 c['passed'])],
            }
            request_type = sudp_request['type'].upper()
        sudp_request['from_date'] = datetime.fromisoformat(sudp_request['from_date']).strftime(
            "%d.%m.%Y")
        sudp_request['to_date'] = datetime.fromisoformat(sudp_request['to_date']).strftime(
            "%d.%m.%Y")
        sudp_request['created_date'] = datetime.fromisoformat(sudp_request['created_date']
                                                              ).strftime("%d.%m.%Y %H:%M")
        sudp_request['from_time'] = datetime.strptime(sudp_request['from_time'],
                                                      '%H:%M:%S').strftime("%H:%M")
        sudp_request['to_time'] = datetime.strptime(sudp_request['to_time'], '%H:%M:%S').strftime(
            "%H:%M")

        if sudp_request['approve']:
            sudp_request['approve'][-1]['created_date'] = datetime.fromisoformat(sudp_request['approve'][-1]['created_date']
                                                              ).strftime("%d.%m.%Y %H:%M")

        if sudp_request['files'] != 'Нет прикрепленных файлов':
            sudp_request['files'] = json.loads(sudp_request['files'])
        else:
            sudp_request['files'] = None
    return requests, choices, request_type


async def _validate_visitors(visitors: dict) -> dict:
    for elem in visitors:
        print(visitors["patronymic"], "<-- patr")
        if visitors["patronymic"] is None:
            visitors["patronymic"] = ""
        if visitors[elem]:
            visitors[elem] = visitors[elem].upper().strip()
    return visitors


async def _validate_cars(cars: dict) -> dict:
    cars["carmodel"] = cars["carmodel"].upper().strip()
    cars["govern_num"] = cars["govern_num"].upper().replace(" ", "")
    return cars


async def _check_date(request, date):
    date_day = date.day
    date_month = date.month

    access_token = request.cookies.get('access_token')

    req = await build_request(
        "host.docker.internal:8000/" +
        f"api/v1/read/holidays",
        access_token=access_token)
    for holiday in req.json():
        from_date_day = datetime.strptime(holiday["from_date"], "%Y-%m-%dT%H:%M:%S").day
        from_date_month = datetime.strptime(holiday["from_date"], "%Y-%m-%dT%H:%M:%S").month
        to_date_day = datetime.strptime(holiday["to_date"], "%Y-%m-%dT%H:%M:%S").day
        to_date_month = datetime.strptime(holiday["to_date"], "%Y-%m-%dT%H:%M:%S").month
        if (from_date_day <= date_day <= to_date_day) and (from_date_month <= date_month <= to_date_month):
            return True
    return False


async def _upload_list_data(request, doc, creator, update=False):
    try:
        form = await RequestForm.from_formdata(request)
        if update:
            form = await UpdateRequestForm.from_formdata(request)
        upload_list_form = await UploadListForm.from_formdata(request)
        headers = [
            ['ФАМИЛИЯ', 'ИМЯ', 'ОТЧЕСТВО'],
            ['ФАМИЛИЯ', 'ИМЯ', 'ОТЧЕСТВО', 'МАРКА АВТОМОБИЛЯ', 'НОМЕР АВТОМОБИЛЯ'],
            ['МАРКА АВТОМОБИЛЯ', 'НОМЕР АВТОМОБИЛЯ']
        ]

        visitors_list = []
        cars_list = []
        table_mode_flag = 'fio'
        for table in parse_docx_table(Document(io.BytesIO(doc))):
            if check_table(table):
                for row in table:
                    get_row = list(map(lambda _: _.upper().strip(), row.get()))
                    if get_row == headers[0]:
                        table_mode_flag = 'fio'
                    if get_row == headers[1]:
                        table_mode_flag = 'fioncmc'
                    if get_row == headers[2]:
                        table_mode_flag = 'ncmc'

                    if table_mode_flag == 'fio' and get_row not in headers:
                        visitors_list.append(dict(zip(["lastname", "name", "patronymic"], get_row)))
                    elif table_mode_flag == 'fioncmc' and get_row not in headers:

                        visitors_list.append(dict(zip(["lastname", "name", "patronymic"],
                                                      [get_row[0], get_row[1], get_row[2]])))

                        cars_list.append(dict(zip(["carmodel", "govern_num"],
                                                  [get_row[3].replace(' ', '').upper(), get_row[4]])))
                    elif table_mode_flag == 'ncmc' and get_row not in headers:
                        cars_list.append(dict(zip(["carmodel", "govern_num"],
                                                  [get_row[0].replace(' ', '').upper(), get_row[1]])))

        for visitor in visitors_list:
            if update:
                form.visitor.append_entry(visitor)
            else:
                form.visitors_list.append_entry(visitor)

        for car in cars_list:
            if update:
                form.car.append_entry(car)
            else:
                form.cars_list.append_entry(car)

        role = request.cookies.get('role')

        return templates.TemplateResponse(
            request=request,
            name="html/request_creation.html",
            context={
                "request": request,
                "form": form,
                "upload_list_form": upload_list_form,
                "uploaded_visitors": visitors_list,
                "uploaded_cars": cars_list,
                "user": creator,
                "role": role
            })

    except zipfile.BadZipFile as e:
        raise e

