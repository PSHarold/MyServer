from . import *
from ..main.errors import *
import flask
from itsdangerous import TimedJSONWebSignatureSerializer, BadSignature, SignatureExpired
import itsdangerous
from ..main.errors import Error, handle_error


class StudentSetting(EmbeddedDocument):
    id_only_to_non_friend = BooleanField(required=True, default=True)


class User(Document):
    meta = {'allow_inheritance': True, 'abstract': True}
    token = ""
    user_id = StringField(primary_key=True)
    password = StringField(required=True)
    name = StringField(required=True)
    email = StringField()
    avatar = StringField()
    gender = BooleanField(required=True)
    role = IntField(required=True)
    tel = StringField()
    email_activated = BooleanField(default=False)
    reset_pending = BooleanField(default=False)
    courses = ListField(ReferenceField('Course'), reverse_delete_rule=4)

    def get_avatar(self):
        try:
            avatar = open(AVATAR_FOLDER + self.user_id + '.jpg', 'r')
            return avatar
        except IOError:
            pass
        return None

    def init_from_user(self, user):
        self.user_id = user.user_id
        self.password = user.password
        self.name = user.name
        self.email = user.email
        self.gender = user.gender
        self.role = user.role
        self.tel = user.tel
        return self

    def generate_seat_map_token(self, period, room_id, course_id):
        s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=10800)
        return s.dumps(
            {'user_id': self.user_id, 'role': self.role, 'period': period, 'room_id': room_id,
             'course_id': course_id})

    def validate_seat_map_token(self, seat_token):
        try:
            s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=10800)
            credential = s.loads(seat_token)
        except SignatureExpired:
            return Error.SEAT_TOKEN_EXPIRED
        except BadSignature:
            return Error.BAD_SEAT_TOKEN
        try:
            if credential['user_id'] != self.user_id:
                return Error.BAD_SEAT_TOKEN
            return credential
        except AttributeError:
            return Error.BAD_SEAT_TOKEN

    def generate_token(self):
        s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=300000000)
        return s.dumps({'user_id': self.user_id, 'role': self.role})

    def generate_seat_token(self, period, course_id, room_id, late_secs=0, ):
        s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=12000)
        return s.dumps({'user_id': self.user_id, 'period': period, 'late_secs': late_secs, 'course_id': course_id,
                        'room_id': room_id})

    def validate_seat_token(self, seat_token):
        try:
            s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'])
            credential = s.loads(seat_token)
        except SignatureExpired:
            return Error.SEAT_TOKEN_EXPIRED
        except BadSignature:
            return Error.BAD_SEAT_TOKEN
        try:
            if self.role == 2 and credential['user_id'] != self.user_id:
                return Error.BAD_SEAT_TOKEN
            return credential
        except:
            return Error.BAD_SEAT_TOKEN

    def register_course(self, course):
        return self.update(push__courses=course)

    def to_dict_all(self):
        json_dict = dict()
        json_dict['user_id'] = self.user_id
        json_dict['name'] = self.name
        json_dict['email'] = self.email
        json_dict['gender'] = self.gender
        json_dict['role'] = self.role
        json_dict['tel'] = self.tel
        json_dict['email_activated'] = self.email_activated
        json_dict['reset_pending'] = self.reset_pending
        json_dict['courses'] = self.get_course_briefs_dict()
        return json_dict

    def to_dict_brief(self):
        json_dict = dict()
        json_dict['name'] = self.name
        json_dict['email'] = self.email
        json_dict['gender'] = self.gender
        json_dict['tel'] = self.tel
        return json_dict

    def get_course_briefs_dict(self):
        raise NotImplementedError

    def modify_password(self, old_pwd, new_pwd):
        if self.password == old_pwd:
            self.update(password=new_pwd)
        else:
            return Error.WRONG_PASSWORD

    def validate_password(self, password):
        if self.password == password:
            return True
        else:
            return False

    @staticmethod
    def get_user(role, user_id, password=None):
        user = None
        try:
            if role == 1:
                user = Teacher.objects.get(pk=user_id)
            elif role == 2:
                user = Student.objects.get(pk=user_id)
            else:
                return Error.USER_NOT_FOUND
        except DoesNotExist:
            return Error.USER_NOT_FOUND

        if password is not None:
            if not user.validate_password(password):
                return Error.WRONG_PASSWORD
        return user

    @staticmethod
    def decrypt_token(token):
        try:
            s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=3600)
            credential = s.loads(token)
        except SignatureExpired:
            return Error.TOKEN_EXPIRED
        except BadSignature:
            return Error.BAD_TOKEN
        return credential


class Teacher(User, Document):
    meta = {
        'collection': 'teacher',
    }

    title = StringField()
    office = StringField()

    def register_course(self, course):
        if not User.register_course(self, course):
            return False
        if self in course.teachers:
            return False
        return course.update(push__teachers=self)

    def to_dict_all(self):
        json = User.to_dict_all(self)
        json['office'] = self.office
        json['title'] = self.title

        return json

    def to_dict_brief(self):
        return {'teacher_id': self.user_id, 'name': self.name, 'gender': self.gender}

    def get_course_briefs_dict(self):
        return map(
            lambda x: {'course_name': x.name, 'course_id': x.course_id, 'classes': x.classes,
                       'times': x.get_times_and_rooms_dict()},
            self.courses)


class Student(User, Document):
    meta = {
        'collection': 'student',
    }

    settings = EmbeddedDocumentField(StudentSetting)
    class_name = StringField()
    major_name = StringField()
    grade = IntField()
    faces = ReferenceField('Face')
    pending_asks = ListField(ReferenceField('AskForLeave'))
    new_status_asks = ListField(ReferenceField('AskForLeave'))

    def register_course(self, course):
        if not User.registerCourse(self, course):
            return False
        if self in course.students:
            return False
        return course.update(push__students=self)

    def to_dict_all(self):
        json = User.to_dict_all(self)
        json['class_name'] = self.class_name
        json['major_name'] = self.major_name
        json['courses'] = self.get_course_briefs_dict(on_login=True)
        return json

    def to_dict_brief(self):
        json = {'role': 2, 'user_id': self.user_id, 'class_name': '', 'major_name': '', 'name': '',
                'gender': self.gender}
        if not self.settings.id_only_to_non_friend:
            json['name'] = self.name
            json['class_name'] = self.class_name
            json['major_name'] = self.major_name
        return json

    def to_dict_brief_for_teacher(self):
        return {'student_id': self.user_id, 'class_name': self.class_name, 'name': self.name,
                'gender': self.gender}

    def get_course_briefs_dict(self, on_login=False):
        if on_login:
            return map(lambda x: x.to_dict_brief_on_login_student(student=self), self.courses)
        return map(lambda x: x.to_dict_brief(), self.courses)

    def get_faces(self):
        try:
            faces = Face.objects.get(pk=self.user_id)
        except DoesNotExist:
            faces = Face(student_id=self.user_id)
            faces.save()
            self.update(faces=faces)
        return faces


class Guest(User, Document):
    meta = {
        'collection': 'guest',
    }

    def to_dict_all(self):
        json = User.to_dict_all(self)
        return json


class Admin(User, Document):
    meta = {
        'collection': 'admin',
    }

    def to_dict_all(self):
        json = User.to_dict_all(self)
        return json
