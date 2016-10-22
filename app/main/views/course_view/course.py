# -*- coding: utf-8 -*-
from app.main.views import *

import datetime
import json


# @main.route('/api/seat/getSeatMapToken', methods=['POST'])
# @require_having_course
# def get_seat_map_token():
#     course = g.course
#     period = course.get_period_of_day()
#     if not period:
#         handle_error(Error.COURSE_IS_NOT_ON_TODAY)
#     remaining_secs = period.get_remaining_seconds_before_beginning()
#     if remaining_secs > 0:
#         handle_error(Error.COURSE_NOT_BEGUN)
#     return success_response(seat_map_token=g.user.generate_seat_map_token(period=period.num, room_id=period.room_id,
#                                                                           course_id=course.course_id))
#
#
# def validate_seat_map_token():
#     get = get_json()
#     get_user_pre()
#     token = get('seat_map_token')
#     r = g.user.validate_seat_map_token(token)
#     if isinstance(r, Error):
#         handle_error(r)
#     return r







@main.route('/api/course/getMainCourse', methods=['GET', 'POST'])
def get_main_course():
    get = get_json()
    course = Course.objects(course_id=get('course_id')).first()
    if course:
        return make_response(jsonify(course.to_dict_all()), 200)
    abort(404)


@main.route('/api/course/getCourseDetails', methods=['POST'])
# @require_having_course
@require_token
def get_sub_course():
    course = get_sub_course_pre()
    role = g.user.role
    return success_response(sub_course=course.to_dict_all(from_preview=True, for_teacher=False))


@main.route('/api/course/syllabus/getSyllabus', methods=['POST'])
@require_having_course
def get_syllabus():
    course = g.course
    syllabus = course.get_syllabus()
    chapters = syllabus.to_dict()
    for chapter in chapters:
        for section in chapter["sections"]:
            for point in section["points"]:
                point["questions"] = KnowledgePoint.objects.get(pk=point["point_id"]).get_questions_list()
    if not isinstance(chapters, list):
        return success_response(chapters={})
    return success_response(chapters=chapters)


@main.route('/api/course/syllabus/postSyllabus', methods=['POST'])
@require_having_course
def post_syllabus():
    course = g.course
    temp_syllabus = Syllabus()
    temp_syllabus.main_course_id = course.main_course_id
    temp_syllabus.chapters = []
    syllabus = course.get_syllabus()
    new_points = {}
    new_questions = {}
    get = get_json()
    for chapter in get('chapters'):
        c = Chapter()
        c.chapter_name = chapter['chapter_name']
        c.chapter_num = chapter['chapter_num']
        temp_syllabus.chapters.append(c)
        for section in chapter['sections']:
            s = Section()
            s.chapter_num = c.chapter_num
            s.section_num = section['section_num']
            s.section_name = section['section_name']
            s.points = []
            for point in section['points']:
                if point['point_id'] == "new":
                    p = KnowledgePoint()
                    p.main_course_id = course.main_course_id
                    p.section_num = s.section_num
                    p.chapter_num = s.chapter_num
                    p.content = point['content']
                    p.level = 1
                    p.save()
                    s.points.append(p)
                    point['point_id'] = p.point_id
                    new_points[str(p.point_id)] = 1
                else:
                    pl = KnowledgePoint.objects(pk=point['point_id'])
                    if len(pl) == 0:
                        print "!"
                        continue
                    pl[0].content = point["content"]
                    pl[0].save()
                    s.points.append(pl[0])
                    new_points[point['point_id']] = 1
                p = KnowledgePoint.objects.get(pk=point['point_id'])
                for question in point["questions"]:
                    if question["question_id"] == "new":
                        q = Question()
                        q.knowledge_point = p
                        q.answers = question["answers"]
                        q.choices = question["choices"]
                        q.content = question["content"]
                        q.difficulty = question["difficulty"]
                        q.type = question["type"]
                        q.detailed_answer = question["detailed_answer"]
                        q.main_course_id = course.main_course_id
                        q.save()
                        new_questions[str(q.question_id)] = 1
                        p.update(add_to_set__questions=q)
                    else:
                        ql = Question.objects(pk=question["question_id"])
                        if len(ql) == 0:
                            continue
                        q = ql[0]
                        q.answers = question["answers"]
                        q.choices = question["choices"]
                        q.content = question["content"]
                        q.knowledge_point = p
                        q.difficulty = question["difficulty"]
                        q.type = question["type"]
                        q.detailed_answer = question["detailed_answer"]
                        q.save()
                        p.update(add_to_set__questions=ql[0])
                        new_questions[question["question_id"]] = 1

            temp_syllabus.sections.append(s)
    temp_syllabus.validate()

    for section in syllabus.sections:
        for point in section.points:
            if isinstance(point, DBRef):
                continue
            if str(point.point_id) not in new_points:
                point.delete()
            for question in point.questions:
                if str(question.question_id) not in new_questions:
                    question.delete()
    syllabus.delete()
    temp_syllabus.save()

    return get_syllabus()


@main.route('/api/course/syllabus/addChapters', methods=['POST'])
@require_having_course
def add_chapter():
    course = g.main_course
    get = get_json()
    chapters = get('chapters')
    if course.syllabus is None:
        syllabus = Syllabus(course_id=course.course_id)
        syllabus.save()
        course.update(syllabus=s)
    r = course.syllabus
    if not hasattr(r, 'add_chapters'):
        r = Syllabus(course_id=course.course_id)
        r.save()
        course.update(syllabus=r)
    r.add_chapters(chapters_dict=chapters)
    if isinstance(r, Error):
        handle_error(r)

    return success_response()


@main.route('/api/course/syllabus/addSections', methods=['POST'])
@require_having_course
def add_section():
    course = g.main_course
    get = get_json()
    sections = get('sections')
    r = course.syllabus
    if not hasattr(r, 'add_chapters'):
        r = Syllabus(course_id=course.course_id)
        r.save()
        course.update(syllabus=r)
    try:
        r.add_sections(sections_dict=sections)
    except KeyError, key:
        handle_error(Error.FIELD_MISSING, field=key.message)
    if isinstance(r, Error):
        handle_error(r)
    return success_response()


@main.route('/api/course/syllabus/addKnowledgePoints', methods=['POST'])
@require_having_course
def add_knowledge_points():
    get_main_course_pre()
    course = g.main_course
    get = get_json()
    points = get('points')
    syllabus = course.syllabus
    point_ids = []
    for point in points:
        try:
            chapter_num = point['chapter_num']
            section_num = point['section_num']
            content = point['content']
            level = point['level']
        except KeyError, e:
            handle_error(Error.FIELD_MISSING, field="'" + e.message + "' in element of points")

        try:
            section = syllabus.sections.get(chapter_num=chapter_num, section_num=section_num)
        except DoesNotExist:
            handle_error(Error.SECTION_NOT_FOUND)
        kp = KnowledgePoint(course_id=course.course_id, chapter_num=chapter_num, section_num=section_num,
                            content=content, level=level)
        kp.save()
        section.points.append(kp)
        point_ids.append(str(kp.point_id))
    syllabus.save()

    return success_response(point_ids=point_ids)


@main.route('/api/course/timeAndRoom/getTimes', methods=['POST'])
def get_time_and_room():
    course = get_sub_course_pre()
    return success_response(times=course.get_times_and_rooms_dict())


@main.route('/api/course/registerTeacher', methods=['POST'])
def course_register_teacher():
    course = get_sub_course_pre()
    get = get_json()
    teacher_id = get('teacher_id')
    teacher = get_by_id_or_error(Teacher, teacher_id)
    if not teacher:
        handle_error(Error.USER_NOT_FOUND)
    if not course:
        handle_error(Error.SUB_COURSE_NOT_FOUND)
    course.update(add_to_set__teachers=teacher)
    teacher.update(add_to_set__courses=course, add_to_set__main_course_ids=course.course_id)
    return success_response()


@main.route('/api/course/getStudentIds', methods=['POST'])
@require_having_course
def get_all_students():
    course = g.course
    return success_response(students=course.get_student_ids())


@main.route('/api/course/getStudents', methods=['POST'])
@require_having_course
def get_students():
    course = g.course
    return success_response(students=course.get_students_dict())


@main.route('/api/course/getStudentInfo', methods=['POST'])
@require_having_course
def get_student_info():
    get = get_json()
    student_id = get('student_id')
    student = get_by_id_or_error(Student, student_id, error=Error.USER_NOT_FOUND)
    return success_response(student=student.to_dict_brief())


@main.route('/api/course/getStudentAvatar', methods=['POST'])
@require_is_teacher
@require_having_course
def get_student_avatar():
    get = get_json()
    student_id = get('student_id')
    print student_id
    if student_id not in no_dereference_id_only_list(g.course.students):
        handle_error(Error.FORBIDDEN)
    student = get_by_id_or_error(Student, student_id, Error.USER_NOT_FOUND)
    avatar = student.get_avatar()
    if avatar:
        return send_file(avatar)
    abort(404)




from app.general import COVER_FOLDER


@main.route('/api/course/get_cover', methods=['POST'])
def get_cover():
    get = get_json()
    main_course_id = get('main_course_id', unicode)
    try:
        cover = open(COVER_FOLDER + main_course_id + '.jpg')
    except IOError:
        abort(404)
    return send_file(cover)


import flask


@main.route('/')
def main_route():
    return flask.redirect('/qr_code')

@main.route('/api/course/qr_code')
def qr_code():
    if not flask.session.get('user_id'):
        return success_response({'qr_code': '/qr_code', 'error_code': 401})
    return success_response({'qr_code': general.generate_qr_code(), 'error_code': 200})


@main.route('/qr_code', methods=['GET', 'POST'])
def qr_code_login():
    if flask.session.get('user_id'):
        return flask.render_template('qr_code.html')

    form = LoginForm()
    if form.validate_on_submit():
        user_id = form.user_id.data
        password = form.password.data
        try:
            user = Teacher.objects.get(pk=user_id)
            if password != user.password:
                return flask.render_template('error.html', msg=u"密码错误!")
        except DoesNotExist:
            return flask.render_template('error.html', msg=u"找不到用户!")
        except:
            return flask.render_template('error.html', msg=u"未知错误!")
        flask.session['user_id'] = user.user_id
        return flask.render_template('qr_code.html')
    return flask.render_template('index.html', form=form)
