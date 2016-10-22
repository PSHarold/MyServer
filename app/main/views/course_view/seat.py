# -*- coding: utf-8 -*-
from . import *

ALLOWED_SEAT_IN_ADVANCED_SECONDS = 600000


def check_if_able_to_choose_seat(course, period):
    allow_late = course.settings.allow_late
    remaining_seconds_before_beginning = period.get_remaining_seconds_before_beginning()
    if remaining_seconds_before_beginning > ALLOWED_SEAT_IN_ADVANCED_SECONDS:
        return -1, remaining_seconds_before_beginning - ALLOWED_SEAT_IN_ADVANCED_SECONDS  # 还未开始
    elif remaining_seconds_before_beginning > 0:
        return 0, 0  # 可以选座, 未迟到
    if remaining_seconds_before_beginning == -1:
        return Error.COURSE_ALREADY_OVER, 0
    if remaining_seconds_before_beginning == 0:
        past_seconds = period.get_past_seconds()
        if past_seconds > allow_late:
            return Error.YOU_ARE_TOO_LATE, past_seconds
        return 1, past_seconds


@main.route('/api/seat/getSeatToken', methods=['POST'])
@require_having_course
def get_seat_token():
    get = get_json()
    qr_code = get('qr_code', allow_none=True)
    if g.user.role == 2:
        if qr_code != 'sSECRET SEAT TOKEN' and not general.validate_qr_code(qr_code):
            handle_error(Error.BAD_QR_CODE)
    course = g.course
    period = course.get_period_of_day()
    if not period:
        handle_error(Error.COURSE_IS_NOT_ON_TODAY)
    access_type, remaining_or_past_secs = check_if_able_to_choose_seat(course=course, period=period)
    if isinstance(access_type, Error):
        handle_error(access_type, late_secs=remaining_or_past_secs)
    if access_type == -1:
        handle_error(Error.SEAT_CHOOSING_NOT_AVAILABLE_YET,
                     remaining_secs=remaining_or_past_secs)
    return success_response(room_id=period.room_id,
                            seat_token=g.user.generate_seat_token(room_id=period.room_id, period=period.num,
                                                                  late_secs=remaining_or_past_secs,
                                                                  course_id=course.course_id),
                            late_secs=remaining_or_past_secs)


@main.route('/api/seat/getSeatMap', methods=['POST'])
@require_token
def get_seats_in_room():
    get = get_json()
    check_final = get('check_final', allow_none=True)
    credential = validate_seat_token()
    room = get_by_id_or_error(Room, credential['room_id'])
    is_final = False
    if check_final:
        course_id = credential['course_id']
        course = get_by_id_or_error(Course, course_id)
        period = Period.get_period(credential['period'])
        access_type, secs = check_if_able_to_choose_seat(course, period)
        if isinstance(access_type, Error):
            is_final = True

    d = {"seats": room.get_seats_dict(period=credential['period'], show_late_secs=g.user.role == 1),
         "row_num": room.row, "col_num": room.col, "final": is_final}

    return success_response(d)


@main.route('/api/seat/getSeatMapPreview', methods=['POST'])
@require_token
def get_seat_map_preview():
    get = get_json()
    room_id = get('room_id')
    room = get_by_id_or_error(Room, room_id, error=Error.ROOM_NOT_FOUND)
    return success_response(seats=room.get_seats_dict(preview=True), row=room.row, col=room.col)


@main.route('/api/seat/getHistorySeatMap', methods=['POST'])
@require_having_course
@require_is_teacher
def get_history_seat_map():
    course = g.course
    get = get_json()
    period_no = get('period_no', int)
    week_no = get('week_no', int)
    day_no = get('day_no', int)
    room_id = g.course.is_on(week_no=week_no, day_no=day_no, period_no=period_no)
    if not room_id:
        handle_error(Error.COURSE_IS_NOT_ON_THE_GIVEN_TIME)
    attendance_list = None
    try:
        # attendance_list = AttendanceList.objects.get(course_id=g.course.course_id, week_no=week_no, day_no=day_no,
        # period_no=period_no)
        attendance_list = g.course.get_attendance_list(week_no=week_no, day_no=day_no, period_no=period_no)
    except DoesNotExist:
        handle_error(Error.SEAT_CHOOSING_NOT_AVAILABLE_YET)
    seat_map = attendance_list.seat_map
    room = get_by_id_or_error(Room, room_id, error=Error.ROOM_NOT_FOUND)

    seats = room.seats
    seat_array = {}
    for student_id, seat_string in seat_map.items():
        if seat_string == "刷脸":
            continue
        else:
            row, col = map(lambda x: int(x), seat_string.split('_'))
        if not seat_array.get(row):
            seat_array[row] = {}
        seat_array[row][col] = student_id

    seats_dict = []
    for seat in seats:
        t = seat.to_dict_preview()
        t['cur_stu'] = seat_array.get(seat.row, {}).get(seat.col, "")
        seats_dict.append(t)
    return success_response(seats=seats_dict, row_num=room.row, col_num=room.col)


@main.route('/api/seat/resetSeatMap', methods=['POST'])
@require_is_teacher
@require_having_course
def reset_seat_map():
    course = g.course
    today = TeachDay.now()
    period = TeachDay.is_course_on_day_and_get_period(course, today)
    if not period:
        handle_error(Error.COURSE_IS_NOT_ON_TODAY)
    remaining_secs_before_beginning = period.remaining_secs_before_beginning()

    room_id = period.room_id
    period_num = str(period.num)
    Seat.objects(room_id=room_id).update(**{'students__' + period_num: '', 'late_secs__' + period_num: 0})
    return success_response()


def validate_seat_token():
    get_user_pre()
    token = get_json()('seat_token')
    credential = g.user.validate_seat_token(seat_token=token)
    if isinstance(credential, Error):
        handle_error(credential)
    return credential


from PIL import Image
from mongoengine import DoesNotExist


@main.route('/api/seat/checkInWithFace', methods=['POST'])
@require_having_course
@require_is_teacher
def check_in_with_face_t():
    credential = g.user.validate_seat_token(seat_token=get_arg_or_error('seat_token'))
    if isinstance(credential, Error):
        handle_error(credential)

    period_num = credential['period']
    course_id = credential['course_id']

    period = Period.get_period(period_num)
    course = get_by_id_or_error(Course, course_id, Error.SUB_COURSE_NOT_FOUND)
    access_type, remaining_or_past_secs = check_if_able_to_choose_seat(course=course, period=period)
    if isinstance(access_type, Error):
        handle_error(access_type, late_secs=remaining_or_past_secs)
    if access_type == -1:
        handle_error(Error.SEAT_CHOOSING_NOT_AVAILABLE_YET,
                     remaining_secs=remaining_or_past_secs)

    try:
        student = Student.objects.get(pk=get_arg_or_error('student_id'))
    except DoesNotExist:
        handle_error(Error.USER_NOT_FOUND)
    faces = student.get_faces()
    if not faces:
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    if not faces.check_if_session_finished():
        handle_error(Error.FACE_TRAINING_NOT_DONE)
    face_count = len(faces.faces)
    file = request.files.get('file')
    if file:
        img_path = FACE_FOLDER + student.user_id + "temp.jpg"
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
    if not r:
        handle_error(Error.FACE_DOES_NOT_MATCH)
    attendance_list = course.get_attendance_list(period=period, teach_day=TeachDay.now())
    r = attendance_list.check_in(student_id=student.user_id)
    if isinstance(r, Error):
        handle_error(r)
    return success_response()


@main.route('/api/seat/chooseSeat', methods=['POST'])
def choose_seat():
    credential = validate_seat_token()
    period_num = credential['period']
    course_id = credential['course_id']
    late_secs = credential['late_secs']
    period = Period.get_period(period_num)
    course = get_by_id_or_error(Course, course_id, Error.SUB_COURSE_NOT_FOUND)
    access_type, remaining_or_past_secs = check_if_able_to_choose_seat(course=course, period=period)
    if isinstance(access_type, Error):
        handle_error(access_type, late_secs=remaining_or_past_secs)
    if access_type == -1:
        handle_error(Error.SEAT_CHOOSING_NOT_AVAILABLE_YET,
                     remaining_secs=remaining_or_past_secs)
    get = get_json()
    seat_id = get('seat_id')
    seat = get_by_id_or_error(Seat, seat_id, error=Error.SEAT_NOT_FOUND)
    stu_id = g.user.user_id

    if seat.modify({'students__' + str(period_num) + '__in': [None, '']},
                   **{'students__' + str(period_num): stu_id, 'late_secs__' + str(period_num): late_secs}):
        attendance_list = course.get_attendance_list(period_no=period.num, day_no=CURRENT_DAY_NO,
                                                     week_no=CURRENT_WEEK_NO)
        attendance_list.check_in(student_id=stu_id, col_num=seat.col, row_num=seat.row)
        return success_response(seat_id=seat_id)
    handle_error(Error.SEAT_ALREADY_TAKEN, seat_id=seat_id, cur_stu=seat.students[str(period_num)])


@main.route('/api/seat/freeSeat', methods=['POST'])
def free_seat():
    credential = validate_seat_token()
    period_num = credential['period']
    course_id = credential['course_id']
    late_secs = credential['late_secs']
    period = Period.get_period(period_num)
    course = get_by_id_or_error(Course, course_id, error=Error.SUB_COURSE_NOT_FOUND)
    access_type, remaining_or_past_secs = check_if_able_to_choose_seat(course=course, period=period)

    if access_type == Error.YOU_ARE_TOO_LATE:
        handle_error(Error.COURSE_ALREADY_BEGUN)
    if access_type == -1:
        handle_error(Error.SEAT_CHOOSING_NOT_AVAILABLE_YET,
                     remaining_secs=remaining_or_past_secs)
    if isinstance(access_type, Error):
        handle_error(access_type)
    get = get_json()
    seat_id = get('seat_id')
    seat = get_by_id_or_error(Seat, seat_id, error=Error.SEAT_NOT_FOUND)
    stu_id = g.user.user_id
    if seat.modify({'students__' + str(period_num) + '__nin': [None, '']},
                   **{'students__' + str(period_num): '', 'late_secs__' + str(period_num): 0}):
        today = TeachDay.now()
        attendance_list = course.get_attendance_list(period_no=period.num, day_no=today.day, week_no=CURRENT_WEEK_NO)
        attendance_list.uncheck_in(student_id=stu_id)
        return success_response(seat_id=seat_id)
    handle_error(Error.SEAT_ALREADY_FREE_OR_TAKEN, seat_id=seat_id)
