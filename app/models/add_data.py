# -*- coding: utf-8 -*-
from gerenal_models import *
from user_models import *
from course_models import *
from PIL import Image


def add_seats(room_id, row, col):
    room = Room.objects.get(pk=room_id)
    room.col = col
    room.row = row
    for i in range(1, row + 1):
        for j in range(1, col + 1):
            seat = Seat()
            seat.room_id = room_id
            seat.row = i
            seat.col = j
            seat.parse_id()
            seat.save()
            room.seats.append(seat)
    room.save()


# add_seats("yf0101", 7, 7)

student_s = '''41358001	王天杏
41358002	王昊
41358003	王佳佳
41358004	王梧蓉
41358005	尹锐哲
41358006	石淼
41358007	冯慎洁
41358008	刘成
41358009	许峥
41358010	孙晨昊
41358011	李宏扬
41358012	李武斌
41358013	杨光
41358014	吴晨霞
41358016	宋子阳
41358017	张钰婕
41358018	张睿杰
41358019	陈曦
41358020	赵秋硕
41358021	徐众贤
41358022	黄万凌
41358023	曹茜男
41358024	崔胜江
41358025	董园园
41358026	谢欣怡
41358027	雷兆和
41358028	谭龙
41358029	谭志凌
41358030	鞠悦
41358031	万建
41358033	王珂
41358034	邓相舟
41358035	冉艾
41358036	刘晓菲
41358037	孙丹阳
41358038	孙泽宇
'''


def add_students(course_id):
    course = Course.objects.get(pk=course_id)
    students = student_s.split("\n")
    students.remove("")
    for student_string in students:
        student_id, student_name = student_string.split("\t")

        student = Student()
        student.courses.append(course)
        student.user_id = student_id
        student.role = 2
        student.name = student_name
        student.gender = True
        student.password = "123"
        student.class_name = "物联1301"
        student.save()
        course.students.append(student)
    course.save()


# add_students("00000000_0001")



def crop_avatars():
    import os
    from app.general import AVATAR_FOLDER
    for file in os.listdir(AVATAR_FOLDER):
        f_e = os.path.splitext(file)
        if f_e[1] != ".jpg":
            continue
        img = Image.open(AVATAR_FOLDER + file)
        width, height = img.size
        if not width == height:
            box = (0, 0, min(width, height), min(width, height))
            img.crop(box).save()
            # img.save(AVATAR_FOLDER + file, optimize=True, quality=95)


#crop_avatars()


def choose_seat(course_id):
    from random import sample, shuffle
    course = Course.objects.get(pk=course_id)
    for a in AttendanceList.objects:
        a.delete()
        a.save()
    for seat in Seat.objects:
        seat.students = {}
        seat.save()
    l = 25
    students = sample(course.students, l)
    for time in course.times:
        room_id = time.room_id
        seats = Seat.objects(room_id=room_id)
        for seat in seats:
            seat.students = {}
            seat.save()

        selected_seats = sample(seats, l)
        shuffle(selected_seats)


        for period_num in range(2, 6):
            for week in time.weeks:
                for day in time.days:
                    attendance_list = course.get_attendance_list(week_no=week, day_no=day, period_no=period_num)
                    for student, seat in zip(students, selected_seats):
                        attendance_list.check_in(student_id=student.user_id, row_num=seat.row, col_num=seat.col)
                        seat.modify({'students__' + str(period_num) + '__in': [None, '']},
                            **{'students__' + str(period_num): student.user_id, 'late_secs__' + str(period_num): 0})


choose_seat("00000000_0001")
