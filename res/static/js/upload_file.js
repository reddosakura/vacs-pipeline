document.getElementById('docxFileInput').addEventListener('change', function (event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                mammoth.convertToHtml({ arrayBuffer: e.target.result })
                    .then(result => {
                        const contents = result.value;
                        const parser = new DOMParser();
                        const docx_document = parser.parseFromString(contents, 'text/html');
                        const tables = docx_document.querySelectorAll("table");

                        let allVisitorsFieldWrapper = document.getElementById('visitors_list_container');
                        let allVisitors = allVisitorsFieldWrapper.getElementsByTagName('input');

                        let newname = `${allVisitors.length / 4}`;

                        if (allVisitors.length > 0){
                            let visitorsInputIds = []
                            for (let j = 0; j < allVisitors.length; j++) {
                                visitorsInputIds.push(parseInt(allVisitors[j].id.split('-')[1]))
                            }
                            newname = Math.max(...visitorsInputIds.filter((number) => !isNaN(number))) + 1;
                        }

                        for (let i = 0; i < tables.length; i++) {
                            const table_body = tables[i].querySelector("tbody");
                            const table_header = table_body.firstChild.textContent.replace(" ", "");

                            if (table_header === "ФамилияИмяОтчество"){
                                let rows = Array.from(table_body.rows).splice(1);

                                for (let j = 0; j < rows.length; j++) {
                                    let cells = rows[j].cells;
                                    let lastname = cells[0].textContent;
                                    let name = cells[1].textContent;
                                    let patronymic = cells[2].textContent;
                                    let html = `<div class="visitor-subform container text-label rounded-4 mb-2 m-0"><div class="row p-1"><div class="col w-25 p-0 rounded-4 d-flex"><div class="w-100 p-1"><div class="form-floating "><input id=visitors_list-${newname}-lastname name=visitors_list-${newname}-lastname class="form-control fs-5 regular-input" placeholder="Фамилия" value=${lastname} required><label class="text-truncate mw-100" for="lastname">ФАМИЛИЯ<span class="text-danger">*</span></label></div></div></div><div class="col w-25 rounded-4 d-flex p-0"><div class="w-100 p-1"><div class="form-floating"><input id=visitors_list-${newname}-name name=visitors_list-${newname}-name class="form-control fs-5 regular-input" placeholder="Имя" value=${name} required><label class="text-truncate mw-100" for="name">ИМЯ<span class="text-danger">*</span></label></div></div></div><div class="col w-25 rounded-4 d-flex p-0"><div class="w-100 p-1"><div class="form-floating"><input id=visitors_list-${newname}-patronymic name=visitors_list-${newname}-patronymic class="form-control fs-5 regular-input" placeholder="Отчество" value=${patronymic} ><label class="text-truncate mw-100" for="patronymic">ОТЧЕСТВО</label></div></div></div><div class="col w-25 p-1"><div class="h-100 internal-btn"><input class="rounded-4 remove-visitor-subform fs-6 w-100 h-100 regular-btn" type="button" value="УДАЛИТЬ"></div></div></div></div>`;
                                    $('#visitors_list_container').append(html);
                                    newname++;
                                }
                            }

                            else if (table_header === "ФамилияИмяОтчествоМаркаавтомобиляНомер автомобиля"){
                                let rows = Array.from(table_body.rows).splice(1);
                                for (let j = 0; j < rows.length; j++) {
                                    let cells = rows[j].cells;
                                    let lastname = cells[0].textContent;
                                    let name = cells[1].textContent;
                                    let patronymic = cells[2].textContent;

                                    let carmodel = cells[3].textContent;
                                    let governnum = cells[4].textContent;

                                    let html_v = `<div class="visitor-subform container text-label rounded-4 mb-2 m-0"><div class="row p-1"><div class="col w-25 p-0 rounded-4 d-flex"><div class="w-100 p-1"><div class="form-floating "><input id=visitors_list-${newname}-lastname name=visitors_list-${newname}-lastname class="form-control fs-5 regular-input" placeholder="Фамилия" value=${lastname} required><label class="text-truncate mw-100" for="lastname">ФАМИЛИЯ<span class="text-danger">*</span></label></div></div></div><div class="col w-25 rounded-4 d-flex p-0"><div class="w-100 p-1"><div class="form-floating"><input id=visitors_list-${newname}-name name=visitors_list-${newname}-name class="form-control fs-5 regular-input" placeholder="Имя" value=${name} required><label class="text-truncate mw-100" for="name">ИМЯ<span class="text-danger">*</span></label></div></div></div><div class="col w-25 rounded-4 d-flex p-0"><div class="w-100 p-1"><div class="form-floating"><input id=visitors_list-${newname}-patronymic name=visitors_list-${newname}-patronymic class="form-control fs-5 regular-input" placeholder="Отчество" value=${patronymic} ><label class="text-truncate mw-100" for="patronymic">ОТЧЕСТВО</label></div></div></div><div class="col w-25 p-1"><div class="h-100 internal-btn"><input class="rounded-4 remove-visitor-subform fs-6 w-100 h-100 regular-btn" type="button" value="УДАЛИТЬ"></div></div></div></div>`;
                                    $('#visitors_list_container').append(html_v);
                                    let html = `<div class="car-subform container text-label rounded-4 mb-2 m-0"><div class="row p-1"><div class="col w-25 rounded-4 d-flex p-0"><div class="w-100 p-1"><div class="form-floating"><input id="cars_list-${newname}-carmodel" value="${carmodel}" name="cars_list-${newname}-carmodel" class="form-control fs-5 regular-input" placeholder="МОДЕЛЬ" required><label class="text-truncate mw-100" for="cars_list-${newname}-model">МОДЕЛЬ<span class="text-danger">*</span></label></div></div></div><div class="col w-25 rounded-4 d-flex p-0"><div class="w-100 p-1"><div class="form-floating"><input id="cars_list-${newname}-govern_num" value="${governnum}" name="cars_list-${newname}-govern_num" class="form-control fs-5 regular-input govern_num" placeholder="ГОС. НОМЕР" required><label class="text-truncate mw-100" for="cars_list-${newname}-govern_num">ГОС. НОМЕР<span class="text-danger">*</span></label></div></div></div><div class="col w-25 p-1"><div class="h-100 internal-btn"><input class="remove-car-subform rounded-4 fs-6 w-100 h-100 regular-btn" type="button" value="УДАЛИТЬ"></div></div></div></div>`;
                                    $('#cars_list_container').append(html);
                                    newname++;
                                }
                            }

                            else if (table_header === "МаркаавтомобиляНомер автомобиля") {
                                let rows = Array.from(table_body.rows).splice(1);
                                for (let j = 0; j < rows.length; j++) {
                                    let cells = rows[j].cells;
                                    let carmodel = cells[0].textContent;
                                    let governnum = cells[1].textContent;

                                    let html = `<div class="car-subform container text-label rounded-4 mb-2 m-0"><div class="row p-1"><div class="col w-25 rounded-4 d-flex p-0"><div class="w-100 p-1"><div class="form-floating"><input id="cars_list-${newname}-carmodel" value="${carmodel}" name="cars_list-${newname}-carmodel" class="form-control fs-5 regular-input" placeholder="МОДЕЛЬ" required><label class="text-truncate mw-100" for="cars_list-${newname}-model">МОДЕЛЬ<span class="text-danger">*</span></label></div></div></div><div class="col w-25 rounded-4 d-flex p-0"><div class="w-100 p-1"><div class="form-floating"><input id="cars_list-${newname}-govern_num" value="${governnum}" name="cars_list-${newname}-govern_num" class="form-control fs-5 regular-input govern_num" placeholder="ГОС. НОМЕР" required><label class="text-truncate mw-100" for="cars_list-${newname}-govern_num">ГОС. НОМЕР<span class="text-danger">*</span></label></div></div></div><div class="col w-25 p-1"><div class="h-100 internal-btn"><input class="remove-car-subform rounded-4 fs-6 w-100 h-100 regular-btn" type="button" value="УДАЛИТЬ"></div></div></div></div>`;
                                    $('#cars_list_container').append(html);
                                    newname++;
                                }
                            }

                            document.getElementById('docxFileInput').value= null;
                        }
                    });
            };
            reader.readAsArrayBuffer(file);
        }
    });