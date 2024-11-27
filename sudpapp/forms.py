from datetime import date
import wtforms
from starlette_wtf import StarletteForm
from wtforms.fields.numeric import IntegerField
from wtforms.fields.simple import StringField, PasswordField, TextAreaField, SubmitField, FileField
from wtforms.fields import DateField, MultipleFileField, FormField, FieldList, BooleanField
from wtforms.fields.choices import SelectField, RadioField
from wtforms.validators import DataRequired, Optional, Regexp
from flask_wtf.file import FileAllowed

TIME_INTERVALS = [
    ("1", "С 5:00 ДО 15:00"),
    ("2", "С 5:00 ДО 18:00"),
    ("3", "С 5:00 ДО 21:30"),
    ("4", "C 7:30 ДО 21:00"),
    ("5", "С 9:00 ДО 12:00"),
    ("6", "С 9:00 ДО 17:00"),
    ("7", "С 12:00 ДО 15:00"),
    ("8", "С 15:00 ДО 17:15"),
    ("9", "КРУГЛОСУТОЧНО"),
]

TYPES = [
    ("1", "ОДНОРАЗОВАЯ"),
    ("2", "МНОГОРАЗОВАЯ"),
]

SPECTYPES = [
    ("1", "ДРУГОЕ"),
    ("2", "СКОРАЯ ПОМОЩЬ"),
    ("3", "ПОЖАРНАЯ СЛУЖБА"),
    ("4", "ПОЛИЦИЯ"),
    ("5", "ГАЗОВАЯ СЛУЖБА"),
]

PASSAGE_MODES = [
    ("1", "По всем дням"),
    ("2", "Только по будням"),
    ("3", "Только по выходным"),
]


ROLES = [
    ("0", "ОХРАНА"),
    ("1", "ЗАЯВИТЕЛЬ"),
    ("2", "ОГРАНИЧЕННОЕ АДМИНИСТРИРОВАНИЕ"),
    ("3", "АДМИНИСТРАТОР"),
    ("4", "СУПЕРПОЛЬЗОВАТЕЛЬ"),
]


class AuthForm(StarletteForm):
    username = StringField('name', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])


class ProcessRequestForm(StarletteForm):
    comment = TextAreaField('comment', render_kw={'data-simplebar': None, 'data-simplebar-auto-hide': False})
    allow = SubmitField('ОДОБРИТЬ')
    deny = SubmitField('ОТКЛОНИТЬ')
    approve = SubmitField('СОГЛАСУЮ')


class VisitorSubForm(wtforms.Form):
    lastname = StringField('lastname', validators=[DataRequired()])
    name = StringField('name', validators=[DataRequired()])
    patronymic = StringField('patronymic')
    v_id = IntegerField("id")


class CarSubForm(wtforms.Form):
    carmodel = StringField('model', validators=[DataRequired()])
    govern_num = StringField('govern_num', validators=[DataRequired()])
    c_id = IntegerField("id")


class RequestForm(StarletteForm):
    organization = StringField('organisation')
    comment = TextAreaField('comment')
    type = SelectField('type',
                       choices=TYPES)
    time_interval = SelectField('time_interval',
                                choices=TIME_INTERVALS, default="4")
    passage_mode = SelectField('passage_mode',
                               choices=PASSAGE_MODES)
    from_date = DateField("from_date", validators=[DataRequired()], default=date.today)
    to_date = DateField("to_date", validators=[DataRequired()], default=date.today)
    contract = StringField('contract')

    visitors_list = FieldList(FormField(VisitorSubForm))
    cars_list = FieldList(FormField(CarSubForm))

    add_files_btn = MultipleFileField(validators=[FileAllowed(['pdf'], 'Только pdf')])
    create_btn = SubmitField('СОЗДАТЬ')


class UploadListForm(StarletteForm):
    list_file = FileField()
    upload = SubmitField('ВЫГРУЗИТЬ ДАННЫЕ')


class PassageForm(StarletteForm):
    request_type = None
    visitors_radio_group = RadioField("visitors", coerce=int, validate_choice=False)
    cars_radio_group = RadioField("cars", coerce=int, validate_choice=False)
    pass_submit = SubmitField("ПРОПУСТИТЬ")


class SearchForm(StarletteForm):
    search_field = StringField()
    search_submit = SubmitField("ПОИСК")


class ExitForm(StarletteForm):
    cars_on_terr_field = RadioField("cars_on_territory", coerce=str, validate_choice=False)
    exit_submit = SubmitField("ВЫЕЗД")


class SpecTransportForm(StarletteForm):
    model_field = StringField('model', validators=[DataRequired()])
    govern_num_field = StringField('model', validators=[DataRequired()])
    type_field = SelectField('type', choices=SPECTYPES)
    pass_spec_submit = SubmitField("ПРОПУСТИТЬ")


class FilterForm(StarletteForm):
    filter_fdate = DateField("filter_fdate", default=date.today)
    filter_tdate = DateField("filter_tdate", default=date.today)
    apply_button = SubmitField("ПРИМЕНИТЬ ФИЛЬТР")
    reset_button = SubmitField("СБРОСИТЬ ФИЛЬТР")


class RecallForm(StarletteForm):
    recall_button = SubmitField("ОТОЗВАТЬ")


class DeleteRequestForm(StarletteForm):
    delete_button = SubmitField("УДАЛИТЬ")


class UpdateRequestForm(StarletteForm):
    type = SelectField('type',
                       choices=TYPES)
    organization = StringField('organization')
    comment = TextAreaField('comment')
    from_date = DateField("from_date", validators=[DataRequired()], default=date.today)
    to_date = DateField("to_date", validators=[DataRequired()], default=date.today)
    time_interval = SelectField('time_interval',
                                choices=TIME_INTERVALS)
    contract_name = StringField('contract')
    passage_mode = SelectField('passage_mode',
                               choices=PASSAGE_MODES)
    visitor = FieldList(FormField(VisitorSubForm))
    car = FieldList(FormField(CarSubForm))
    create_btn = SubmitField('СОХРАНИТЬ ИЗМЕНЕНИЯ')
    add_files_btn = MultipleFileField(validators=[FileAllowed(['pdf'], 'Только pdf')])


class CreateUserForm(StarletteForm):
    lastname = StringField('lastname', validators=[DataRequired()])
    name = StringField('name', validators=[DataRequired()])
    patronymic = StringField('patronymic')
    speciality = StringField('specility', validators=[DataRequired()])
    role = SelectField('roles', choices=ROLES)
    login = StringField('login', validators=[DataRequired()])
    password = StringField('password', validators=[DataRequired()])
    create_btn = SubmitField("ЗАРЕГИСТРИРОВАТЬ")


class UpdateUserForm(StarletteForm):
    lastname = StringField('lastname', validators=[DataRequired()])
    name = StringField('name', validators=[DataRequired()])
    patronymic = StringField('patronymic')
    speciality = TextAreaField('specility', validators=[DataRequired()])
    role = SelectField('roles', choices=ROLES)
    login = StringField('login', validators=[DataRequired()])
    password = StringField('password', validators=[Optional()])
    selector = BooleanField("ИЗМЕНИТЬ ЛОГИН ИЛИ ПАРОЛЬ")
    edit_btn = SubmitField("СОХРАНИТЬ ИЗМЕНЕНИЯ")
    delete_btn = SubmitField("УДАЛИТЬ ПОЛЬЗОВАТЕЛЯ")
