# -*- coding: utf-8 -*-
from . import *
import random
from ..main.errors import *
from .user_models import Student
from .gerenal_models import TeachDay, Period

TESTS_PER_PAGE = 6
NOTIFICATIONS_PER_PAGE = 10


class TimeAndRoom(EmbeddedDocument):
    room_name = StringField(required=True)
    room_id = StringField(required=True)
    days = ListField(IntField(), required=True)
    period = IntField(required=True)
    weeks = ListField(IntField(), required=True)

    def to_dict(self):
        return {'room_name': self.room_name, 'room_id': self.room_id, 'days': self.days, 'period':
            self.period, 'weeks': self.weeks}


class Section(EmbeddedDocument):
    chapter_num = IntField(required=True)
    section_num = IntField(required=True)
    section_name = StringField(required=True)
    planned_hours = IntField()
    points = ListField(ReferenceField('KnowledgePoint'))

    def to_dict(self):
        return {'section_name': self.section_name, 'section_num': self.section_num,
                'points': traverse_detecting_none(self.points, lambda x: x.to_dict_brief()),
                'planned_hours': self.planned_hours}


class Chapter(EmbeddedDocument):
    chapter_num = IntField(required=True)
    chapter_name = StringField(required=True)

    def to_dict(self):
        return {'chapter_num': self.chapter_num, 'chapter_name': self.chapter_name}


class Syllabus(Document):
    main_course_id = StringField(required=True, primary_key=True)
    chapters = EmbeddedDocumentListField(Chapter)
    sections = EmbeddedDocumentListField(Section)

    def add_chapters(self, chapters_dict):
        chapters = []
        chapter_nums = []
        for chapter in chapters_dict:
            chapter_num = chapter['chapter_num']
            chapter_nums.append(chapter_num)
            chapters.append(Chapter(chapter_num=chapter_num, chapter_name=chapter['chapter_name']))
        r = self.modify({'chapters__chapter_num__nin': chapter_nums}, add_to_set__chapters=chapters)
        if not r:
            return Error.CHAPTER_ALREADY_EXISTS

    def add_sections(self, sections_dict):
        sections = []
        for section in sections_dict:
            chapter_num = section['chapter_num']
            section_num = section['section_num']
            c_list = self.chapters.filter(chapter_num=chapter_num)
            if not c_list:
                return Error.CHAPTER_NOT_FOUND
            s_list = self.sections.filter(chapter_num=chapter_num, section_num=section_num)
            if s_list:
                return Error.SECTION_ALREADY_EXISTS
            section = Section(chapter_num=section['chapter_num'], section_num=section_num,
                              section_name=section['section_name'], planned_hours=section['planned_hours'])
            sections.append(section)
        self.update(add_to_set__sections=sections)

    def to_dict(self):
        chapters = {}
        for chapter in self.chapters:
            t = chapter.to_dict()
            t['sections'] = []
            chapters[chapter.chapter_num] = t
        for section in self.sections:
            chapters[section.chapter_num]['sections'].append(section.to_dict())
        return map(lambda (key, value): value, chapters.items())


# 知识点
class KnowledgePoint(Document):
    main_course_id = StringField(required=True)
    chapter_num = IntField(required=True)
    section_num = IntField(required=True)
    point_id = ObjectIdField(default=lambda: ObjectId(), primary_key=True)
    content = StringField(required=True)

    level = IntField(required=True)
    questions = ListField(ReferenceField('Question'))
    question_num = DictField(default=lambda: KnowledgePoint.init_question_num_dict(), required=True)

    @staticmethod
    def init_question_num_dict():
        t = {}
        for q_type in QuestionType:
            a = {}
            for difficulty in QuestionDifficulty:
                a[str(difficulty._value_)] = 0
            t[str(q_type._value_)] = a
        return t

    def to_dict_brief(self):
        return {'point_id': str(self.point_id), 'content': self.content,
                'level': self.level, 'question_num': len(self.questions)}

    def to_dict_all(self):
        return {'chapter': self.chapter, 'section': self.section, 'point_id': str(self.point_id),
                'content': self.content,
                'level': self.level}

    def get_questions_list(self):
        q = map(lambda x: x.to_dict_student_take_test(), self.questions)
        return q

    def add_question(self, question):
        self.update(add_to_set__questions=question)


# 课程通知
class Notification(EmbeddedDocument):
    ntfc_id = ObjectIdField(required=True, default=lambda: ObjectId())
    created_on = DateTimeField(default=lambda: datetime.datetime.now())
    content = StringField(required=True)
    title = StringField(required=True)
    on_top = BooleanField(required=True)
    by = StringField(required=True)
    unread_students = ListField(StringField(), required=True)

    def to_dict(self):
        return {'ntfc_id': str(self.ntfc_id), 'created_on': time_to_string(self.created_on), 'content': self.content,
                'on_top':
                    self.on_top, 'by': self.by, 'title': self.title}


class QuestionType(Enum):
    MULTIPLE_CHOICE = 1
    TRUE_OR_FALSE = 2
    COMPLETION = 3
    MULTIPLE_CHOICE_MULTIPLE_ANSWERS = 4
    MULTIPLE_COMPLETION = 5
    OTHER = 6


class QuestionDifficulty(Enum):
    VERY_EASY = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    VERY_HARD = 5


class Question(Document):
    main_course_id = StringField(required=True)
    question_id = ObjectIdField(default=lambda: ObjectId(), primary_key=True)
    created_on = DateTimeField(default=lambda: datetime.datetime.now())
    last_modified = DateTimeField(default=lambda: datetime.datetime.now())
    type = IntField(required=True, default=1)
    choices = ListField(StringField(), required=True)
    content = StringField(required=True)
    difficulty = IntField(required=True, default=1)
    answers = ListField(StringField(), required=True)
    detailed_answer = StringField(required=True, default="")
    knowledge_point = ReferenceField('KnowledgePoint', reverse_delete_rule=1, required=True)
    score = IntField(default=5)
    by = StringField()
    hint = StringField(default="")
    level = IntField(default=1)

    def to_dict_student_take_test(self):
        return {'question_id': str(self.question_id), 'type': self.type, 'choices': self.choices,
                'content': self.content,
                'difficulty': self.difficulty, 'answers': self.answers, 'detailed_answer': self.detailed_answer,
                'point_id': str(self.knowledge_point.point_id)}

    def to_dict_all(self):
        temp_dict = self.to_dict_student_take_test()
        temp_dict['created_on'] = self.created_on
        # temp_dict['last_modified'] = self.last_modified
        temp_dict['by'] = self.by
        return temp_dict

    def to_dict_brief(self):
        return {'question_id': str(self.question_id), 'content': self.content, 'type': self.type,
                'difficulty': self.difficulty}


class StudentQuestionResultType(Enum):
    wrong = 0
    totally_correct = 1
    half_correct = 2
    no_answers = -1


class TestStudentResultItem(EmbeddedDocument):
    my_answers = ListField(StringField())
    point_id = StringField(required=True)
    correct = IntField(required=True)
    answers = ListField(StringField())

    def to_dict(self):
        return {'my_answers': self.my_answers, 'correct': self.correct, 'answers': self.answers}


class TestStudentResult(Document):
    processed = BooleanField(required=True, default=False)
    test_id = StringField(required=True)
    student_id = StringField(required=True)
    result_id = StringField(primary_key=True)
    temp_results = DictField()
    results = MapField(EmbeddedDocumentField(TestStudentResultItem))
    should_questions = DictField()
    total_number = IntField()
    total_correct = IntField()
    score = IntField()
    finished = BooleanField(required=True, default=False)

    def process(self):
        if self.processed:
            return
        if self.finished:
            return Error.TEST_ALREADY_TAKEN
        result_dict = {}
        try:
            test = Test.objects.get(pk=self.test_id)
        except DoesNotExist:
            self.delete()
            self.save()
            return Error.TEST_NOT_FOUND
        try:
            for (question_id, my_answers) in self.temp_results.items():
                try:
                    question = Question.objects.get(pk=question_id)
                except DoesNotExist:
                    self.delete()
                    self.save()
                    return Error.BAD_STUDENT_TEST_RESULT

                if question_id not in self.should_questions:
                    return Error.BAD_STUDENT_TEST_RESULT

                r = TestStudentResultItem()
                r.point_id = str(question.knowledge_point.id)
                question_type = QuestionType(question.type)
                r.answers = question.answers
                if question_type == QuestionType.MULTIPLE_CHOICE:
                    r.my_answers = map(lambda x: str(x), my_answers)
                    if str(my_answers[0]) in question.answers:
                        r.correct = StudentQuestionResultType.totally_correct._value_
                    else:
                        r.correct = StudentQuestionResultType.wrong._value_
                elif question_type == QuestionType.MULTIPLE_CHOICE_MULTIPLE_ANSWERS:
                    pass

                del self.should_questions[question_id]
                result_dict[question_id] = r

            for question_id in self.should_questions:
                try:
                    question = Question.objects.get(pk=question_id)
                except DoesNotExist:
                    self.delete()
                    self.save()
                    return Error.QUESTION_NOT_FOUND
                r = TestStudentResultItem()
                r.my_answers = []
                r.answers = question.answers
                r.correct = StudentQuestionResultType.no_answers._value_
                r.point_id = str(question.knowledge_point.id)
                result_dict[question_id] = r
                del self.should_questions[question_id]

        except (AttributeError, KeyError):
            self.delete()
            self.save()
            return Error.WRONG_FIELD_TYPE
        test.update(inc__finished_count=1)
        self.results = result_dict
        self.processed = True
        self.save()
        self.temp_results = {}
        self.finished = True
        self.save()

    def to_dict(self):
        results = {}
        for (point_id, result) in self.results.items():
            results[point_id] = result.to_dict()
        return results

    def to_dict_preview(self):
        return {"total_number": self.total_number, "total_correct": self.total_correct}


class TestStatisticQuestion(EmbeddedDocument):
    question_id = StringField(required=True)
    point_id = StringField(required=True)
    total_finished = IntField(required=True, default=0)
    total_correct = IntField(required=True, default=0)
    answers = DictField()

    def to_dict(self):
        answers = {}
        for (answer, student_list) in self.answers.items():
            answers[answer] = len(student_list)
        return {'total_finished': self.total_finished, 'total_correct': self.total_correct, 'point_id': self.point_id,
                'answers': answers}

    def get_choices_dict(self):
        return self.answers


class TestStatisticKnowledgePoint(EmbeddedDocument):
    total_finished = IntField(required=True, default=0)
    total_correct = IntField(required=True, default=0)
    point_id = StringField(requried=True)

    def to_dict(self):
        return {'total_finished': self.total_finished, 'total_correct': self.total_correct}


class TestRandomType(Enum):
    FIXED = 0


class Test(Document):
    course_id = StringField(required=True)
    test_id = ObjectIdField(default=lambda: ObjectId(), primary_key=True)
    created_on = DateTimeField(default=lambda: datetime.datetime.now(), required=True)
    begins_on = DateTimeField(default=lambda: datetime.datetime.now(), required=True)
    expires_on = DateTimeField()
    finished_students = ListField(ReferenceField('Student'))
    results = ListField(ReferenceField(TestStudentResult, reverse_delete_rule=PULL))
    statistic = ReferenceField('TestStatistic')
    message = StringField()
    time_limit = IntField(required=True)
    random_type = IntField(required=True, default=0)
    blacklist = ListField(StringField())
    black_info = StringField()
    question_settings = DictField(required=True)
    total_score = IntField(required=True, default=100)
    by = StringField(required=True)
    finished = BooleanField(default=False)
    finished_count = IntField(required=True, default=0)

    def is_finished(self):
        try:
            if self.expires_on > datetime.datetime.now() and not self.finished:
                self.update(finished=True)
            return self.expires_on > datetime.datetime.now() or self.finished
        except:
            return self.finished

    def to_dict_preview_teacher(self):
        return {'test_id': str(self.test_id), 'finished': self.finished, 'begins_on': time_to_string(self.begins_on),
                'expires_on': time_to_string(self.expires_on), 'finished_count': self.finished_count,
                'random_type': self.random_type}

    def to_dict_preview_student(self):
        return {'test_id': str(self.test_id), 'finished': self.finished, 'begins_on': time_to_string(self.begins_on),
                'expires_on': time_to_string(self.expires_on), 'finished_count': self.finished_count,
                'time_limit': self.time_limit}

    def to_dict_student_take(self):
        json = dict()
        json['test_id'] = str(self.test_id)
        json['begins_on'] = time_to_string(self.begins_on)
        json['expires_on'] = time_to_string(self.begins_on)
        json['message'] = self.message
        json['has_hint'] = self.has_hint
        json['blacklist'] = self.blacklist
        json['finished_students'] = self.finished_students
        return json

    def to_dict_all(self):
        json = self.to_dict_student_take()
        json['created_on'] = self.created_on
        return json

    def get_questions_dict(self, question_list=None):

        questions = []
        if question_list == None:
            map(lambda x: questions.append(x.to_dict_student_take_test()), self.questions)
        else:
            map(lambda x: questions.append(x.to_dict_student_take_test()), question_list)
        return questions

    def get_questions(self):
        def dereference_question(question_id):
            try:
                question = Question.objects.get(pk=question_id)
            except DoesNotExist:
                handle_error(Error.QUESTION_NOT_FOUND)
            return question.to_dict_student_take_test()

        random_type = TestRandomType(self.random_type)
        if random_type == TestRandomType.FIXED:
            return map(dereference_question, self.question_settings['questions'])
        elif self.random_type == 1:
            new_list = list(self.questions)
            random.shuffle(new_list)
            return self.get_questions_dict(new_list)
        elif self.random_type == 2:
            pass

        elif self.random_type == 3:
            if not self.random_settings:
                return Error.RANDOM_TEST_NOT_SET
            new_list = []

            def choose_question(preference):
                raw_list = random.sample(preference.knowledge_point.questions, preference.num)
                temp_list = []
                map(lambda x: temp_list.append(x.to_dict_student_take_test()), raw_list)
                new_list.extend(temp_list)

            map(choose_question, self.random_settings)
            random.shuffle(new_list)
            return new_list

    def get_finished_students(self):
        students = []
        for student_id in no_dereference_id_only_list(self.finished_students):
            try:
                test_result = TestStudentResult.objects.get(pk=self.test_id + student_id)
                t = {'student_id': student_id, 'total_correct': test_result.total_correct,
                     'total_number': test_result.total_number}
                students.append(t)
            except DoesNotExist:
                continue
        return students


class CourseSetting(EmbeddedDocument):
    allow_late = IntField(default=0)


class TestStatistic(Document):
    processed = BooleanField(default=False, required=True)
    test_id = StringField(primary_key=True)
    point_results = MapField(EmbeddedDocumentField(TestStatisticKnowledgePoint))
    question_results = MapField(EmbeddedDocumentField(TestStatisticQuestion))
    unfinished_students = DictField(required=True)

    def get_question_result(self, question_id):
        status = None
        if not self.processed:
            status = self.process()
        if status:
            return status
        if not self.question_index.has_key(question_id):
            return Error.QUESTION_NOT_FOUND
        try:
            question_result = self.question_results[question_id]
        except KeyError:
            return Error.QUESTION_NOT_FOUND
        return question_result.get_choices_dict()

    def process(self):
        if self.processed:
            return
        try:
            test = Test.objects(pk=self.test_id).get()
        except DoesNotExist:
            return Error.TEST_NOT_FOUND
        if not test.finished:
            return Error.TEST_STILL_ONGOING
        self.point_results = {}
        self.question_results = {}
        student_results = TestStudentResult.objects(test_id=self.test_id)
        for student_result in student_results:
            if not student_result.processed:
                status = student_result.process()
                if status:
                    return status
            for question_id, question_result in student_result.results.items():
                point_id = question_result.point_id
                if point_id not in self.point_results:
                    point = TestStatisticKnowledgePoint(point_id=point_id)
                    self.point_results[point_id] = point
                else:
                    point = self.point_results[point_id]
                if question_id not in self.question_results:
                    e = TestStatisticQuestion(question_id=question_id, point_id=point_id)
                    self.question_results[question_id] = e
                else:
                    e = self.question_results[question_id]
                e.total_finished += 1
                point.total_finished += 1
                if question_result.correct == StudentQuestionResultType.totally_correct._value_:
                    e.total_correct += 1
                    point.total_correct += 1

                for choice in question_result.my_answers:
                    if choice not in e.answers:
                        e.answers[choice] = []
                    e.answers[str(choice)].append(student_result.student_id)
            try:
                del self.unfinished_students[student_result['student_id']]
            except KeyError:
                pass
        self.processed = True
        self.save()

    def to_dict(self):
        point_results = {}
        for (point_id, value) in self.point_results.items():
            point_results[point_id] = value.to_dict()
        question_results = {}
        for (question_id, value) in self.question_results.items():
            question_results[question_id] = value.to_dict()
        return {'point_results': point_results, 'question_results': question_results}

    def get_unfinished_students(self):
        return self.unfinished_students.keys()


# 讲台
class Course(Document):
    name = StringField(required=True)
    course_id = StringField(primary_key=True)
    main_course_id = StringField(required=True)
    sub_course_id = StringField(required=True)
    teachers = ListField(ReferenceField('Teacher'), required=True)
    teacher_names = ListField(StringField())
    students = ListField(ReferenceField('Student'))
    top_notifications = EmbeddedDocumentListField(Notification)
    normal_notifications = EmbeddedDocumentListField(Notification)
    times = EmbeddedDocumentListField(TimeAndRoom)
    tests = ListField(ReferenceField('Test', reverse_delete_rule=PULL))
    settings = EmbeddedDocumentField(CourseSetting, required=True, default=CourseSetting())
    classes = ListField(StringField())
    main_course = ReferenceField('Course')
    finished_tests = ListField(ReferenceField('Test'))
    unfinished_tests = ListField(ReferenceField('Test'))
    pending_asks = ListField(ReferenceField('AskForLeave'))

    def get_syllabus(self):
        return Syllabus.objects(
            main_course_id=self.main_course_id).modify(upsert=True, new=True, set_on_insert__chapters=[])

    def to_dict_all(self, from_preview=False, for_teacher=False):
        extra = {'students': self.get_students_dict(for_teacher=for_teacher), 'ntfcs': self.get_notifications(),
                 'teacher_names': self.teacher_names}
        if not from_preview:
            extra.update(self.to_dict_brief())
        return extra

    def to_dict_brief(self):
        teachers = []
        map(lambda x: teachers.append(x.name), self.teachers)
        return {'course_id': self.course_id, 'sub_course_id': self.sub_course_id, 'teachers': teachers,
                'course_name': self.name,
                'times': self.get_times_and_rooms_dict(), 'teacher_names': self.teacher_names}

    def is_on(self, week_no, day_no, period_no):
        for time in self.times:
            if week_no in time.weeks and day_no in time.days and period_no == time.period:
                return time.room_id
        return False

    def to_dict_brief_on_login_student(self, student):
        json = self.to_dict_brief()
        # json['unread_ntfcs'] = self.get_unread_notifications(student)
        # json['unfinished_tests'] = self.get_unfinished_tests(student)
        return json

    def get_students_dict(self):
        return map(lambda x: x.to_dict_brief_for_teacher(), self.students)

    def get_teachers_dict(self):
        teachers = []
        map(lambda x: teachers.append(x.to_dict_brief()), self.teachers)
        return teachers

    def get_times_and_rooms_dict(self):
        times = []
        map(lambda x: times.append(x.to_dict()), self.times)
        return times

    # 返回课程通知列表
    def get_notifications_paginating(self, page):
        if page == 1:
            notifications = self.top_notifications
            notifications = map(lambda x: x.to_dict(), self.top_notifications)
        else:
            notifications = []
        start = (page - 1) * NOTIFICATIONS_PER_PAGE
        normal_notifications = self.normal_notifications[start:start + NOTIFICATIONS_PER_PAGE]
        notifications.extend(map(lambda x: x.to_dict(), normal_notifications))
        return notifications

    def get_all_tests_dict_paginating(self, page, per_page, finished=False, student_id=None):
        offset = (page - 1) * per_page
        test_list = []
        if finished:
            test_list = Test.objects(course_id=self.course_id, done_students__nin=[student_id]).order_by(
                '-begins_on').skip(offset).limit(per_page)
        elif not finished and student_id is not None:
            test_list = Test.objects(course_id=self.course_id, done_students__in=[student_id]).order_by(
                '-begins_on').skip(offset).limit(per_page)
        else:
            test_list = Test.objects(course_id=self.course_id).order_by(
                '-begins_on').skip(offset).limit(per_page)
        tests = []
        map(lambda x: tests.append(x.to_dict_student_take()), test_list)
        return tests

    def get_unread_notifications(self, student):
        notifications = []
        for notification in self.top_notifications:
            if student.user_id in notification.unread_students:
                notifications.append(notification.to_dict())
        for notification in self.normal_notifications:
            if student.user_id in notification.unread_students:
                notifications.append(notification.to_dict())
        # notifications.reverse()
        return notifications

    def get_unfinished_tests_teacher(self):
        count = 0
        for test in self.unfinished_tests:
            if test.is_finished():
                self.update(add_to_set__finished_tests=test, pull__unfinished_tests=test)
                del self.unfinished_tests[count]
            count += 1
        return map(lambda x: x.to_dict_preview_teacher(), self.unfinished_tests)

    def get_unfinished_tests_student(self, student_id):
        tests = []
        for test in self.unfinished_tests:
            t = test.to_dict_preview_student()
            try:
                result = TestStudentResult.objects.get(pk=str(test.test_id) + '#' + student_id)
                if result.finished:
                    continue
            except DoesNotExist:
                t['taken'] = False
            tests.append(t)
        return tests

    def get_finished_tests_student(self, student_id):
        tests = []
        for test in self.unfinished_tests:
            try:
                result = TestStudentResult.objects.get(pk=str(test.test_id) + '#' + student_id)
                if not result.finished:
                    continue
                t = test.to_dict_preview_student()
                t['taken'] = True
                t['total_number'] = result.total_number
                t['total_correct'] = result.total_correct
            except DoesNotExist:
                continue
            tests.append(t)

        for test in self.finished_tests:
            t = test.to_dict_preview_student()
            try:
                result = TestStudentResult.objects.get(pk=str(test.test_id) + '#' + student_id)
                t['taken'] = True
                t['total_number'] = result.total_number
                t['total_correct'] = result.total_correct
            except DoesNotExist:
                t['taken'] = False
            tests.append(t)
        return tests

    def get_period_of_day(self, day=None):
        if day is None:
            day = TeachDay.now()
        for time in self.times:
            if day.week in time.weeks and day.day in time.days:
                period = Period.get_period(time.period)
                period.room_id = time.room_id
                return period
        return None

    def is_on_day(self, day=None):
        if day is None:
            day = TeachDay.now()
        for time in self.times:
            if day.week in time.weeks and day.day in time.days:
                return True
        return False

    def get_finished_tests_teacher(self):
        return map(lambda x: x.to_dict_preview_teacher(), self.finished_tests)

    def get_finished_tests_paginating(self, page):
        test_count = len(self.finished_tests)
        start = (page - 1) * TESTS_PER_PAGE
        tests = self.finished_tests[start:start + TESTS_PER_PAGE]
        # if descending:
        #     start = (page-1) * TESTS_PER_PAGE
        #     if start > test_count:
        #         start = -test_count
        #     end = (page - 1) * TESTS_PER_PAGE
        #     if end <= 0:
        #         end = None
        #     tests = self.finished_tests[start:end]
        #     tests.reverse()
        # else:
        #     start = (page - 1) * TESTS_PER_PAGE
        #     if start < 0:
        #         start = 0
        #     end = start + TESTS_PER_PAGE
        #     if end > test_count:
        #         end = test_count
        #     tests = self.finished_tests[start:end]
        return map(lambda x: x.to_dict_preview_teacher(), tests)

    def get_student_ids(self):
        return no_dereference_id_only_list(self.students)

    def get_attendance_list(self, week_no=None, day_no=None, period_no=None, teach_day=None, period=None):
        if teach_day != None and period != None:

            try:
                list_id = self.course_id + '_' + str(teach_day.week) + '_' + str(teach_day.day) + '_' + str(
                    period.num)
                return AttendanceList.objects(
                    list_id=list_id,
                    week_no=teach_day.week,
                    day_no=teach_day.day,
                    period_no=period.num).modify(upsert=True, new=True,
                                                 set_on_insert__list_id=list_id,
                                                 set_on_insert__course_id=self.course_id,
                                                 set_on_insert__week_no=teach_day.week,
                                                 set_on_insert__day_no=teach_day.day,
                                                 set_on_insert__period_no=period.num,
                                                 set_on_insert__absent_students=no_dereference_id_only_list(
                                                     self.students))
                AttendanceList.objects()
            except DoesNotExist:
                return None
        elif week_no is not None and day_no is not None and period_no is not None:
            try:
                list_id = self.course_id + '_' + str(week_no) + '_' + str(day_no) + '_' + str(period_no)
                return AttendanceList.objects(
                    list_id=list_id, week_no=week_no, day_no=day_no, period_no=period_no).modify(upsert=True, new=True,
                                                                                                 set_on_insert__course_id=self.course_id,
                                                                                                 set_on_insert__week_no=week_no,
                                                                                                 set_on_insert__day_no=day_no,
                                                                                                 set_on_insert__period_no=period_no,
                                                                                                 set_on_insert__absent_students=no_dereference_id_only_list(
                                                                                                     self.students))

            except DoesNotExist:
                return None


# 课程
class MainCourse(Document):
    sub_course_ids = ListField(StringField())
    main_course_id = StringField()
    syllabus = ReferenceField(Syllabus)


class AskForLeaveStatus(Enum):
    PENDING = 0
    APPROVED = 1
    DISAPPROVED = 2


class AskForLeave(Document):
    ask_id = ObjectIdField(default=lambda: ObjectId(), primary_key=True)
    student_id = StringField()
    reason = StringField()
    status = IntField(default=0)
    course_id = StringField()
    week_no = IntField()
    day_no = IntField()
    period_no = IntField()
    created_at = DateTimeField(default=lambda: datetime.datetime.now())
    viewed_at = DateTimeField()

    def to_dict(self):
        d = {'ask_id': str(self.ask_id), 'student_id': self.student_id, 'status': self.status,
             'course_id': self.course_id, 'week_no': self.week_no, 'day_no': self.day_no,
             'period_no': self.period_no,
             'reason': self.reason, 'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S")}
        if self.status != AskForLeaveStatus.PENDING._value_:
            d['viewed_at'] = self.viewed_at.strftime("%Y-%m-%d %H:%M:%S")
        return d

    def get_status(self):
        if self.status is None:
            return None
        return AskForLeave(self.status)

    def is_approved(self):
        return self.status == 1

    def is_pending(self):
        return self.status == 0

    def is_disapproved(self):
        return self.status == 2

    def set_status(self, status):
        self.status = status._value_


class AttendanceStatus(Enum):
    ABSENT = 0
    PRESENT = 1
    HAS_ASKED_FOR_LEAVE = 2


class AttendanceList(Document):
    present_students = ListField(StringField())
    absent_students = ListField(StringField())
    asked_students = ListField(StringField())
    list_id = StringField(primary_key=True)
    course_id = StringField()
    asks = ListField(ReferenceField('AskForLeave'))
    week_no = IntField()
    day_no = IntField()
    period_no = IntField()
    processed = BooleanField(default=False)
    seat_map = MapField(StringField())

    def uncheck_in(self, student_id):
        if student_id not in self.seat_map:
            self.update(**{'pull__present_students': student_id, 'add_to_set__absent_students': student_id})
        else:
            self.update(
                **{'unset__seat_map__' + student_id: self.seat_map[student_id], 'pull__present_students': student_id,
                   'add_to_set__absent_students': student_id})

    def check_in(self, student_id, col_num=None, row_num=None):
        assert (col_num is None and row_num is None) or (col_num is not None and row_num is not None)
        if student_id in self.asked_students:
            ask = None
            for t_ask in self.asks:
                if t_ask.student_id == student_id:
                    ask = t_ask
            if ask is None:
                if col_num is None:
                    self.update(**{'add_to_set__present_students': student_id, 'pull__asked_students': student_id,
                                   'set__seat_map__' + student_id: '刷脸'})

                    self.update(**{'add_to_set__present_students': student_id, 'pull__asked_students': student_id,
                                   'set__seat_map__' + student_id: str(row_num) + '_' + str(col_num)})
                return
            if ask.is_approved():
                return Error.ASK_FOR_LEAVE_HAS_BEEN_APPROVED
            else:
                if col_num is None:
                    self.update(**{'add_to_set__present_students': student_id, 'pull__asks_for_leave': ask,
                                   'pull__absent_students': student_id, 'pull__asked_students': student_id,
                                   'set__seat_map__' + student_id: '刷脸'})
                else:
                    self.update(**{'add_to_set__present_students': student_id, 'pull__asks_for_leave': ask,
                                   'pull__absent_students': student_id, 'pull__asked_students': student_id,
                                   'set__seat_map__' + student_id: '刷脸'})
        elif student_id in self.present_students:
            return Error.ALREADY_CHECKED_IN
        else:
            if col_num is None:
                self.update(**{'add_to_set__present_students': student_id, 'pull__absent_students': student_id,
                               'set__seat_map__' + student_id: '刷脸'})
            else:
                self.update(**{'add_to_set__present_students': student_id, 'pull__absent_students': student_id,
                               'set__seat_map__' + student_id: str(row_num) + '_' + str(col_num)})

    def to_dict(self, course):
        all_students = set(no_dereference_id_only_list(course.students))
        presents = set(self.present_students)
        asked = []
        for ask in self.asks:
            if ask.is_approved():
                asked.append(ask.student_id)
        asked = set(asked)
        return {'absent': list(all_students - presents - asked), 'asked': list(asked),
                'present': self.seat_map}

    def get_attendance_status(self, student_id):
        for ask in self.asks:
            if ask.student_id == student_id:
                if ask.is_approved() or ask.is_pending():
                    return ask.to_dict()
                else:
                    return AttendanceStatus.ABSENT._value_
        if student_id in self.present_students:
            return AttendanceStatus.PRESENT._value_
        else:
            return AttendanceStatus.ABSENT._value_
