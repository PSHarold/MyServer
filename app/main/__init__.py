from flask import Blueprint
main = Blueprint('main',__name__)
import errors
from app.main.views.course_view import test, seat, notification, course, attendance_and_asks
import app.main.views.user_views

