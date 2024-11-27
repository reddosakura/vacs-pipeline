import jinja2
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory="res/templates")
UPLOAD_FOLDER = './uploads/'
