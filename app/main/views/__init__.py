# -*- coding: utf-8 -*-
from app.main.errors import *
from app.models.user_models import *
from app.models.gerenal_models import *
from app.models.course_models import *
from app.models.form import *
from flask import g, request, abort, make_response, jsonify, Response, send_file
from functools import wraps
from mongoengine.errors import ValidationError, DoesNotExist, NotUniqueError
from app.models import no_dereference_id_only_list
import app.general as general
from server import app

PER_PAGE = 5




def get_sub_course_pre():

    course_id =  get_arg_or_error('course_id', allow_none=True)
    if course_id is None:
        get = get_json()
        course_id = get('course_id')
    return get_by_id_or_error(Course, course_id, error=Error.SUB_COURSE_NOT_FOUND)


def get_arg_or_error(arg_name, allow_none=False, field_type=object):
    if arg_name in request.args:
        if isinstance(request.args[arg_name], field_type):
            return request.args[arg_name]
        else:
            handle_error(Error.WRONG_FIELD_TYPE, arg_name=arg_name, given_type=type(request.args[arg_name]).__name__,
                         should_be_type=field_type.__name__)
    elif allow_none:
        return
    else:
        handle_error(Error.ARGUMENT_MISSING, arg_name=arg_name)


def get_user(role, user_id, password=None):
    user = User.get_user(role, user_id, password)
    if isinstance(user, Error):
        handle_error(user)
    return user


def get_user_pre():
    if hasattr(g, 'user'):
        return
    token = get_arg_or_error('token', field_type=unicode)
    credential = User.decrypt_token(token)
    if isinstance(credential, Error):
        handle_error(credential)
    user = get_user(credential['role'], credential['user_id'])
    if isinstance(user, Error):
        handle_error(user)
    g.user = user


# 使用此修饰器的View都需要验证token
def require_token(func):
    @wraps(func)
    def require_func(*args, **kwargs):
        get_user_pre()
        return func(*args, **kwargs)

    return require_func


def get_json():
    json = request.get_json()
    if not json:
        abort(406)

    def get_field(field, field_type=object, allow_none=False):
        value = json.get(field)
        if value is None and not allow_none:
            handle_error(Error.FIELD_MISSING, field=field)
        elif value is None and allow_none:
            return None
        elif isinstance(value, field_type):
            return value
        else:
            handle_error(Error.WRONG_FIELD_TYPE, field=field, given_type=type(value).__name__,
                         should_be_type=field_type.__name__)

    return get_field


def instantiate_from_request_or_422(cls, *exceptions, **extra_attrs):
    get = get_json()
    instance = cls()
    fields = dict(cls._fields)

    def get_and_field(field):
        attr = getattr(cls, field)
        if (field not in exceptions) and (field not in extra_attrs) and (
                    attr.required and not attr.primary_key) and (attr.default is None):
            value = get(field)
            setattr(instance, field, value)

    def set_field((key, value)):
        setattr(instance, key, value)

    map(get_and_field, fields)
    map(set_field, extra_attrs.items())
    return instance


def modify_from_request_or_422(instance, allowed_fields, exceptions, **extra_attrs):
    json = request.get_json()
    json.pop('token', None)
    fields = dict(instance._fields)
    cls = type(instance)
    exceptions.append('token')

    def get_and_try_setting((key, value)):
        if key in exceptions:
            return
        if not hasattr(cls, key):
            handle_error(Error.UNKNOWN_FIELD, field=key)
        if key not in allowed_fields:
            handle_error(Error.FORBIDDEN)
        attr = getattr(instance, key)
        if type(attr) == type(value):
            setattr(instance, key, value)
        else:
            handle_error(Error.WRONG_FIELD_TYPE, field=key, should_be="")

    def set_field((key, value)):
        setattr(instance, key, value)

    map(get_and_try_setting, json.items())
    map(set_field, extra_attrs.items())


def require_is_teacher(func):
    @wraps(func)
    def require(*args, **kwargs):
        get_user_pre()
        if not g.user.role == 1:
            handle_error(Error.YOU_ARE_NOT_THE_TEACHER)
        return func(*args, **kwargs)

    return require


def require_is_student(func):
    @wraps(func)
    def require(*args, **kwargs):
        get_user_pre()
        if not g.user.role == 2:
            handle_error(Error.YOU_ARE_NOT_A_STUDENT)
        return func(*args, **kwargs)

    return require


def require_having_course(func):
    @wraps(func)
    def require(*args, **kwargs):
        get_user_pre()
        course = get_sub_course_pre()
        g.course = course
        if g.user.role == 1:
            if g.user.user_id not in no_dereference_id_only_list(course.teachers):
                handle_error(Error.YOU_DO_NOT_HAVE_THIS_COURSE)
        elif g.user.role == 2:
            if g.user.user_id not in no_dereference_id_only_list(course.students):
                handle_error(Error.YOU_DO_NOT_HAVE_THIS_COURSE)
        return func(*args, **kwargs)

    return require




def get_main_course_pre():
    get = get_json()
    course_id = get('course_id')
    course = Course.objects(course_id=course_id).first()
    return course


def get_by_id_or_error(cls, id, error=None):
    try:
        return cls.objects.get(pk=id)
    except (DoesNotExist, ValidationError):
        if error is None:
            handle_error(Error.RESOURCE_NOT_FOUND)
        handle_error(error)


# OK的Response,接受键值对作为附加信息
def success_response(*args, **kwargs):
    msg = {}
    for arg in args:
        msg.update(arg)
    for key in kwargs:
        msg[key] = kwargs[key]

    return make_response(jsonify(msg), 200)

def send_static_file(filename):
    return app.send_static_file(filename)


from flask import render_template

def render_error_message(error_message=u"未知错误"):
    return render_template('my_error.html', error_message=error_message)


def render_success_message(success_message):
    return render_template('success.html', success_message=success_message)
