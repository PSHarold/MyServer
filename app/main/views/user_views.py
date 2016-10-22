# -*- coding: utf-8 -*-
from flask import g, request, abort, session, send_from_directory

from app.main import main
from . import *
import json
from app.main import *
from mongoengine import EmbeddedDocument, EmbeddedDocumentListField, IntField, ListField, StringField, NotUniqueError
import time
from PIL import Image


@main.route('/api/user/login', methods=['POST'])
def user_login(token_only=False):
    get = get_json()
    user_id = get('user_id', unicode)
    password = get('password', unicode)
    role = get('role', int)
    user = get_user(role, user_id, password)
    if isinstance(user, Error):
        handle_error(user)
    if token_only:
        return success_response(token=user.generate_token())
    json_dict = user.to_dict_all()
    pending_asks = []
    if user.role == 1:  # 教师
        for course in user.courses:
            pending_asks.extend(map(lambda x: x.to_dict(), course.pending_asks))
    json_dict['pending_asks'] = pending_asks
    return success_response(user=json_dict, week_no=CURRENT_WEEK_NO, day_no=CURRENT_DAY_NO, token=user.generate_token())


@main.route('/api/user/login/getToken', methods=['POST'])
def get_token():
    return user_login(token_only=True)


@main.route('/api/user/modifyMe', methods=['POST'])
@require_token
def modify_my_info():
    allowed = ['email', 'gender']
    user = g.user
    modify_from_request_or_422(user, allowed_fields=allowed)
    user.save()
    return success_response(user=user.to_dict_all())


@main.route('/api/user/register/getSchools', methods=['POST'])
def get_schools():
    school_list = []
    schools = School.objects()
    return success_response(schools=map(lambda x: {'school_id': x.school_id, 'school_name': x.school_name}, schools))


@main.route('/api/user/register/getDepartments', methods=['POST'])
def get_departments():
    get = get_json()
    school_id = get('school_id')
    school = get_by_id_or_error(School, school_id)
    return success_response(departmens=school.departments)


@main.route('/api/user/register/getMajors', methods=['POST'])
def get_majors():
    get = get_json()
    school_id = get('school_id')
    school = get_by_id_or_error(School, school_id)
    return success_response(majors=school.majors)


@main.route('/api/user/register/getClasses', methods=['POST'])
def get_classes():
    get = get_json()
    major_id = get('major_id')
    major = get_by_id_or_error(Major, major_id)
    return success_response(classes=major.classes)


def register_common(role):
    get = get_json()
    user_id = get('user_id')
    name = get('name')
    password = get('password')
    email = get('email', allow_none=True)
    tel = get('tel', allow_none=True)
    gender = get('gender')
    temp_user = get_user(role, user_id, password)
    if not isinstance(temp_user, Error):
        handle_error(Error.USER_ALREADY_EXISTS)
    user = User()
    user.user_id = user_id
    user.name = name
    user.password = password
    user.email = email
    user.gender = gender
    user.role = role
    user.tel = tel
    return user


@main.route('/api/user/register/student', methods=['POST'])
def register_student():
    user = register_common(2)
    student = Student().init_from_user(user)
    student.save()
    # get = get_json()
    # class_id = get('class_id')
    # major_id = get('major_id')
    # class_o = get_by_id_or_error(DClass, class_id)
    # major = get_by_id_or_error(Major, major_id)
    # if not class_o:
    #     handle_error(Error.CLASS_NOT_FOUND)
    # if not major:
    #     handle_error(Error.MAJOR_NOT_FOUND)
    # base_user = register_common(2)
    # user = Student().init_from_user(base_user)
    # user.class_name = class_o.class_name
    # user.major_name = major.major_name
    # user.grade = class_o.grade
    # user.save()
    # class_o.update(add_to_set__students={'name': user.name, 'student_id': user.user_id})
    return success_response()


@main.route('/api/user/register/teacher', methods=['POST'])
def register_teacher():
    user = register_common(1)
    teacher = Teacher().init_from_user(user)
    teacher.save()
    return success_response()


@main.route('/api/user/registerCourse', methods=['POST'])
@require_token
def register_course():
    course = get_sub_course_pre()
    role = g.user.role
    if role == 1:
        if g.user in course.teachers:
            handle_error(Error.USER_ALREADY_EXISTS)
        course.update(add_to_set__teachers=g.user)
    elif role == 2:
        if g.user in course.students:
            handle_error(Error.USER_ALREADY_EXISTS)
        course.update(add_to_set__students=g.user, add_to_set__classes=g.user.class_name)
    g.user.update(add_to_set__courses=course)
    return success_response()


# 头像上传
@main.route('/api/user/avatar', methods=['POST'])
@require_token
def post_avatar():
    get = get_json()
    img = get('img')
    with open(FACE_FOLDER + g.user.user_id + '.jpg', 'w') as file:
        try:
            file.write(img.decode('base64'))
            print img
        except:
            handle_error(Error.BASE64_ERROR)
    return success_response()


# 头像获取
@main.route('/api/user/avatar/<user_id>.jpg')
def get_avatar(user_id):
    return send_from_directory(FACE_FOLDER, user_id + '.jpg')


@main.route('/getServerTime')
def check_time():
    return success_response(server_time=time.time())


@main.route('/api/user/modify_password', methods=['POST'])
@require_token
def modify_password():
    get = get_json()
    old_pwd = get('old_pwd')
    new_pwd = get('new_pwd')
    r = g.user.modify_password(old_pwd, new_pwd)
    if isinstance(r, Error):
        handle_error(r)
    return success_response()


@main.route('/api/user/get_face_img', methods=['POST'])
@require_token
def get_face():
    get = get_json()
    faces = g.user.get_faces()
    face_id = get('face_id')
    img_path = faces.faces.get(face_id)
    if img_path:
        return send_file(img_path)
    else:
        abort(404)


@main.route('/api/user/get_faces')
@require_token
def get_face_ids():
    faces = g.user.get_faces()
    l = []
    for face_id in faces.faces.keys():
        l.append(face_id)
    return success_response(faces=l)


@main.route('/api/user/add_face', methods=['POST'])
@require_token
def add_face():
    faces = g.user.get_faces()
    if not faces:
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    if not faces.check_if_session_finished():
        handle_error(Error.FACE_TRAINING_NOT_DONE)
    face_count = len(faces.faces)
    file = request.files.get('file')
    if file:
        img_path = FACE_FOLDER + g.user.user_id + str(face_count + 1) + ".jpg"
        file.save(img_path)
        img = Image.open(img_path)
        width, height = img.size
        max_length = max(width, height)
        if max_length > 600:
            ratio = max_length / 600
            height /= ratio
            width /= ratio
        img = img.resize((width, height), Image.ANTIALIAS)
        img.save(img_path, optimize=True, quality=95)
    else:
        handle_error(Error.BAD_IMAGE)
    r = faces.add_face(img_path=img_path)
    if isinstance(r, Error):
        handle_error(r)
    return success_response(face_id=r)


@main.route('/api/user/test_face', methods=['POST'])
@require_token
def test_face():
    faces = g.user.get_faces()
    if not faces:
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    if not faces.check_if_session_finished():
        handle_error(Error.FACE_TRAINING_NOT_DONE)
    face_count = len(faces.faces)
    file = request.files.get('file')
    if file:
        img_path = FACE_FOLDER + g.user.user_id + "temp.jpg"
        file.save(img_path)
        img = Image.open(file)
        width, height = img.size
        max_length = max(width, height)
        if max_length > 600:
            ratio = max_length / 600
            height /= ratio
            width /= ratio
        img = img.resize((width, height), Image.ANTIALIAS)
        img.save(img_path, optimize=True, quality=95)
    else:
        handle_error(Error.BAD_IMAGE)
    r = faces.recognize_verify(img_path=img_path)
    os.remove(img_path)
    if isinstance(r, Error):
        handle_error(r)
    return success_response(is_same_person=r)


@main.route('/api/user/delete_face', methods=['POST'])
@require_token
def delete_face():
    get = get_json()
    faces = g.user.get_faces()
    face_id = get('face_id')
    r = faces.delete_face(face_id=face_id)
    if isinstance(r, Error):
        handle_error(r)
    return success_response()


@main.route('/api/user/delete_all_faces')
@require_token
def delete_all_faces():
    faces = g.user.get_faces()
    r = faces.delete_person()
    if isinstance(r, Error):
        handle_error(r)
    return success_response()


@main.route('/api/user/upload_avatar', methods=['POST'])
@require_token
def upload_avatar():
    file = request.files.get('file')
    if file:
        img_path = FACE_FOLDER + g.user.user_id + ".jpg"
        file.save(img_path)
        img = Image.open(img_path)
        width, height = img.size
        max_length = max(width, height)
        if max_length > 600:
            ratio = max_length / 600
            height /= ratio
            width /= ratio
        img = img.resize((width, height), Image.ANTIALIAS)
        img.save(img_path, optimize=True, quality=95)

    else:
        handle_error(Error.UNKNOWN_FIELD)
    return success_response()


@main.route('/api/user/my_avatar')
@require_token
def my_avatar():
    avatar = g.user.get_avatar()
    if avatar:
        return send_file(avatar)
    else:
        return send_static_file('no_avatar.png')


import app.models.add_data

from flask_mail import Message
from smtplib import SMTPRecipientsRefused
from app import mail
from flask import url_for

@main.route('/user/confirm_email/<email_token>')
def confirm_email(email_token):
    try:
        s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=3600)
        credential = s.loads(email_token)
        role = credential['role']
        user_id = credential['user_id']
        email = credential['email']
        if role == 1:
            user = Teacher.objects.get(pk=user_id)
        elif role == 2:
            user = Student.objects.get(pk=user_id)
        if email != user.email:
            return render_error_message(u"无效的验证链接!")
        user.update(email_activated=True)
        return render_success_message(u"验证成功!")
    except BadSignature:
        return render_error_message(u"无效的验证链接!")
    except SignatureExpired:
        return render_error_message(u"链接已过期!")
    except DoesNotExist:
        return render_error_message(u"找不到用户" + user_id)
    except:
        return render_error_message()


def send_confirm_email(user, new_email):
    s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=3600)
    token = s.dumps({'user_id': user.user_id, 'role': user.role, 'email': new_email})
    msg = Message('验证邮箱', sender="923469221@qq.com", recipients=[new_email])
    msg.body = '点击链接验证邮箱, 有效时间60分钟\n' + url_for('main.confirm_email', email_token=token, _external=True)
    try:
        mail.send(msg)
    except SMTPRecipientsRefused:
        return Error.WRONG_EMAIL_ADDRESS


def send_reset_password_email(user):
    s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=3600)
    token = s.dumps({'user_id': user.user_id, 'role': user.role, 'email': user.email})
    msg = Message('重置密码', sender="923469221@qq.com", recipients=[user.email])
    msg.body = '点击链接重置密码, 有效时间60分钟\n' + url_for('main.reset_password_confirm', email_token=token, _external=True)
    try:
        mail.send(msg)
        user.update(reset_pending=True)
    except:
        return Error.WRONG_EMAIL_ADDRESS

@main.route('/api/user/get_email')
@require_token
def get_email():
    email = ""
    if g.user.email:
        email = g.user.email
    return success_response(email=email, activated=g.user.email_activated)


@main.route('/api/user/modify_email', methods=['POST'])
@require_token
def modify_email():
    get = get_json()
    email = get('email')
    r = send_confirm_email(g.user, email)
    if isinstance(r, Error):
        handle_error(r)
    g.user.update(email=email, email_activated=False)
    return success_response()


@main.route('/api/user/reset_password_get_email', methods=['POST'])
def reset_password_request():
    get = get_json()
    user_id = get('user_id')
    role = get('role')
    try:
        if int(role) == 1:
            user = Teacher.objects.get(pk=user_id)
        elif int(role) == 2:
            user = Student.objects.get(pk=user_id)
        else:
            handle_error(Error.USER_NOT_FOUND)
    except:
        handle_error(Error.USER_NOT_FOUND)
    if not user.email_activated:
        handle_error(Error.EMAIL_NOT_ACTIVATED)
    email = list(user.email)
    email[1: len(email) - 3] = '*' * (len(email) - 4)
    return success_response(email=''.join(email))


@main.route('/api/user/reset_password', methods=['POST'])
def reset_password():
    get = get_json()
    user_id = get('user_id')
    role = get('role')
    email = get('email')
    try:
        if int(role) == 1:
            user = Teacher.objects.get(pk=user_id)
        elif int(role) == 2:
            user = Student.objects.get(pk=user_id)
        else:
            handle_error(Error.USER_NOT_FOUND)
        if not user.email_activated:
            handle_error(Error.EMAIL_NOT_ACTIVATED)
        if email != user.email:
            handle_error(Error.WRONG_EMAIL_ADDRESS)
        send_reset_password_email(user)
        return success_response()
    except DoesNotExist:
        handle_error(Error.USER_NOT_FOUND)
    except SMTPRecipientsRefused:
        handle_error(Error.WRONG_EMAIL_ADDRESS)

@main.route('/user/reset_password_confirm/<email_token>', methods=['GET', 'POST'])
def reset_password_confirm(email_token):
    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=3600)
            credential = s.loads(email_token)
            role = credential['role']
            user_id = credential['user_id']
            email = credential['email']
            if role == 1:
                user = Teacher.objects.get(pk=user_id)
            elif role == 2:
                user = Student.objects.get(pk=user_id)
            if email != user.email:
                return render_error_message(u"无效的链接!")
            if not user.reset_pending:
                return render_error_message(u"链接已过期!")
            user.update(password=form.password.data, reset_pending=False)
            return render_success_message(u"密码重置成功!")
        except BadSignature:
            return render_error_message(u"无效的验证链接!")
        except SignatureExpired:
            return render_error_message(u"链接已过期!")
        except DoesNotExist:
            return render_error_message(u"找不到用户" + user_id)


    try:
        s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=3600)
        credential = s.loads(email_token)
        role = credential['role']
        user_id = credential['user_id']
        email = credential['email']
        if role == 1:
            user = Teacher.objects.get(pk=user_id)
        elif role == 2:
            user = Student.objects.get(pk=user_id)
        if email != user.email:
            return render_error_message(u"无效的链接!")
        if not user.reset_pending:
            return render_error_message(u"链接已过期!")
        return render_template('reset_password.html', form=form)
    except BadSignature:
        return render_error_message(u"无效的验证链接!")
    except SignatureExpired:
        return render_error_message(u"链接已过期!")
    except DoesNotExist:
        return render_error_message(u"找不到用户" + user_id)
