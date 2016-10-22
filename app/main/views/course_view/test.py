# -*- coding: utf-8 -*-
from app.main.views import *

TESTS_PER_PAGE = 6


@main.route('/api/course/question/addQuestions', methods=['POST'])
@require_having_course
def add_questions():
    course = g.main_course
    get = get_json()
    questions_dict = get('questions')
    temp_points_dict = {}
    for question_dict in questions_dict:
        point_id = question_dict['point_id']
        if point_id not in temp_points_dict:
            try:
                point = KnowledgePoint.objects.get(point_id=point_id)
            except:
                handle_error(Error.KNOWLEDGE_POINT_NOT_FOUND, point_id=point_id)
        else:
            point = temp_points_dict[point_id]
        answers = question_dict['answers']
        choices = question_dict['choices']
        choices = [choices['A'], choices['B'], choices['C'], choices['D']]
        content = question_dict['content']
        answers = question_dict['answers']
        type = question_dict['type']
        score = question_dict['score']
        question = Question(course_id=course.course_id, content=content, choices=choices,
                            knowledge_point=point, answers=answers, hint="",
                            level=0, difficulty=0, detailed_answer="", type=type, score=score)
        question.save()
        point.add_question(question)
    return success_response(question_id=str(question.question_id))


# @main.route('/api/course/question/modifyQuestion', methods=['POST'])
# def modify_question():
#     get = get_json()
#     question_id = get('question_id')
#     try:
#         question = Question.objects.get(question_id=question_id)
#     except:
#         handle_error(Error.KNOWLEDGE_POINT_NOT_FOUND)
#
#
#     modify_from_request_or_422(question, allowed=['content','hint','choices','answers',''],knowledge_point=point)
#     question.save()
#     return success_response()


@main.route('/api/course/question/deleteQuestion', methods=['POST'])
def delete_question():
    get = get_json()
    question_id = get('question_id')
    try:
        question = Question.objects.get(question_id=question_id)
    except (DoesNotExist, ValidationError):
        return success_response()
    question.delete()
    return success_response()


@main.route('/api/course/question/getQuestionsInPoint', methods=['POST'])
@require_having_course
def get_questions_with_points():
    get = get_json()
    point_id = get('point_id')
    print point_id
    try:
        point = KnowledgePoint.objects.get(point_id=point_id)
    except (DoesNotExist, ValidationError):
        handle_error(Error.KNOWLEDGE_POINT_NOT_FOUND, point_id=point_id)
    return success_response(point_id=point_id, questions=point.get_questions_list())


@main.route('/api/course/question/getAllQuestions', methods=['POST'])
@require_having_course
@require_is_teacher
def get_all_questions():
    get = get_json()
    course_id = get('course_id')
    page = get('page')
    per_page = get('per_page', allow_none=True)
    course = get_by_id_or_error(Course, course_id)
    questions = course.get_questions_dict_paginating(page=page, per_page=PER_PAGE)
    return success_response(questions=questions)


@main.route('/api/course/question/getQuestion', methods=['POST'])
@require_having_course
@require_is_teacher
def get_question():
    get = get_json()
    question = get_by_id_or_error(Question, get('question_id'))
    return success_response(question=question.to_dict_all())


@main.route('/api/course/question/getQuestionsInList', methods=['POST'])
def get_questions():
    get = get_json()
    question_list = get('questions')
    questions = []

    def get_a_question(question_id):
        try:
            q = Question.objects(question_id=question_id).first()
        except ValidationError:
            handle_error(Error.RESOURCE_NOT_FOUND)
        if not q:
            handle_error(Error.RESOURCE_NOT_FOUND)
        questions.append(q.to_dict_all())

    map(get_a_question, question_list)
    return success_response(questions=questions)


@main.route('/api/course/test/postTest', methods=['POST'])
@require_having_course
def post_test():
    course = g.course
    get = get_json()
    course_id = course.course_id
    question_settings = get('question_settings')
    total_score = get('total_score', int, allow_none=True)

    blacklsit = get('blacklist', allow_none=True)
    by = g.user.user_id
    new_test = instantiate_from_request_or_422(Test, course_id=course_id, by=by,
                                               question_settings=question_settings, blacklsit=blacklsit, total_score=total_score)
    new_test.save()
    course.update(add_to_set__unfinished_tests=new_test)

    return success_response(test_id=str(new_test.test_id))


@main.route('/api/course/test/endTest', methods=['POST'])
@require_is_teacher
@require_having_course
def end_test():
    course = g.course
    test_id = get_json()('test_id')
    test = get_by_id_or_error(Test, test_id, error=Error.TEST_NOT_FOUND)
    test.update(finished=True)
    course.unfinished_tests.remove(test)
    course.finished_tests.insert(0, test)
    course.save()
    return success_response(test_id=test_id)


@main.route('/api/course/test/getUnfinishedTests', methods=['POST'])
@require_having_course
def get_all_tests():
    course = get_sub_course_pre()
    if g.user.role == 1:
        tests = course.get_unfinished_tests_teacher()
    elif g.user.role == 2:
        tests = course.get_unfinished_tests_student(g.user.user_id)
    else:
        tests = []
    return success_response(tests=tests)


@main.route('/api/course/test/getFinishedStudentsInTest', methods=['POST'])
@require_having_course
def get_finished_student_list():
    course = g.course
    test_id = get_json()('test_id')
    test = get_by_id_or_error(Test, test_id, error=Error.TEST_NOT_FOUND)
    return success_response(students=test.get_finished_students())


@main.route('/api/course/test/getFinishedTests', methods=['POST'])
@require_having_course
def get_finished_test():
    course = g.course

    # page = get('page')
    # descending = get('descending')
    # tests = course.get_finished_tests_paginating(page=page)

    # for test_dict in tests:
    #     test_id = test_dict['test_id']
    #     try:
    #         test_result = TestStudentResult.objects.get(pk=test_id + '#' + g.user.user_id)
    #         test_dict.update({'total_number': test_result.total_number, 'total_correct': test_result.total_correct})
    #     except DoesNotExist:
    #         pass
    if g.user.role == 1:
        tests = course.get_finished_tests_teacher()
    elif g.user.role == 2:
        tests = course.get_finished_tests_student(student_id=g.user.user_id)
    else:
        tests = []
    return success_response(tests=tests)


@main.route('/api/course/test/getQuestionsInTest', methods=['POST'])
@require_having_course
def get_test_questions():
    get = get_json()
    test_id = get('test_id')
    test = get_by_id_or_error(Test, test_id, error=Error.TEST_NOT_FOUND)
    now = datetime.datetime.now()
    if test.begins_on > now:
        handle_error(Error.TEST_HAVENT_BEGUN)

    combined_id = test_id + '#' + g.user.user_id
    try:
        result = TestStudentResult.objects.get(pk=combined_id)
        if result.finished:
            handle_error(Error.TEST_ALREADY_TAKEN)
    except DoesNotExist:
        pass

    questions = test.get_questions()
    question_ids = map(lambda x: x['question_id'], questions)
    should_questions = {}
    for q in question_ids:
        should_questions[q] = True
    TestStudentResult(result_id=combined_id, test_id=test_id, student_id=g.user.user_id,
                      temp_results={}, should_questions=should_questions, total_number=len(should_questions)).save()
    return success_response(questions=questions)


@main.route('/api/course/test/getQuestionsInTestForResult', methods=['POST'])
@require_having_course
def get_questions_in_test_for_results():
    student_id = g.user.user_id
    get = get_json()
    test_id = get('test_id')
    try:
        test_result = TestStudentResult.objects.get(pk=test_id + '#' + student_id)
    except DoesNotExist:
        handle_error(Error.YOU_HAVENT_TAKEN_THE_TEST)
    questions = []
    for question_id in test_result.results.keys():
        try:
            question = Question.objects.get(pk=question_id)
        except DoesNotExist:
            handle_error(Error.QUESTION_NOT_FOUND, question_id=question_id)
        questions.append(question.to_dict_student_take_test())
    return success_response(questions=questions)


def process_student_test_result(test_result):
    try:
        status = test_result.process()
        if isinstance(status, Error):
            handle_error(status)
    except DoesNotExist:
        handle_error(Error.RESOURCE_NOT_FOUND)
    except (AttributeError, KeyError):
        handle_error(Error.WRONG_FIELD_TYPE)


@main.route('/api/course/test/postAnswers', methods=['POST'])
@require_having_course
def post_answers():
    get = get_json()
    student_id = g.user.user_id
    test_id = get('test_id')
    results = get('my_answers')
    try:
        test_result = TestStudentResult.objects.get(pk=test_id + '#' + student_id)
        if test_result.finished:
            handle_error(Error.TEST_ALREADY_TAKEN)
    except DoesNotExist:
        handle_error(Error.YOU_HAVENT_TAKEN_THE_TEST)

    print results
    test_result.temp_results = results
    test_result.save()
    process_student_test_result(test_result)
    return success_response(results=test_result.to_dict())


@main.route('/api/course/test/result/getStudentResult', methods=['POST'])
@require_having_course
def get_result():
    role = g.user.role
    if role == 2:
        student_id = g.user.user_id
        get = get_json()
        test_id = get('test_id')
        try:
            results = TestStudentResult.objects.get(pk=test_id + '#' + student_id)
            if not results.processed:
                process_student_test_result(results)
            return success_response(results=results.to_dict())
        except DoesNotExist:
            handle_error(Error.YOU_HAVENT_TAKEN_THE_TEST)
    elif role == 1:
        pass


@main.route('/api/course/test/result/getQuestionResultDetails', methods=['POST'])
def get_question_result_details():
    get = get_json()
    test_id = get('test_id')
    question_id = get('question_id')
    test_results = get_by_id_or_error(TestStatistic, test_id, error=Error.TEST_NOT_FOUND)
    r = test_results.get_question_result(question_id)
    if isinstance(r, Error):
        handle_error(r)
    return success_response(results=r)


@main.route('/api/course/test/result/getTestResults', methods=['POST'])
@require_having_course
def get_test_results():
    get = get_json()
    test_id = get('test_id')
    course = g.course
    with_questions = get('with_questions', allow_none=True)
    try:
        test_statistic = TestStatistic.objects.get(pk=test_id)
    except DoesNotExist:
        test_statistic = TestStatistic(test_id=test_id,
                                       unfinished_students={}.fromkeys(course.get_student_ids(),
                                                                       False))
        try:
            test_statistic.save()
        except:
            return handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    if test_statistic.processed:
        results = test_statistic.to_dict()
    else:
        error = test_statistic.process()
        if error is not None:
            handle_error(error)
        results = test_statistic.to_dict()

    if not with_questions:
        return success_response(results=results)
    else:
        for (question_id, result) in results['question_results'].items():
            question = get_by_id_or_error(Question, question_id)
            results['question_results'][question_id].update(question.to_dict_all())
        return success_response(results=results)


@main.route('/api/course/test/result/getUnfinishedStudents', methods=['POST'])
@require_having_course
def get_unfinished_students():
    get = get_json()
    test_id = get('test_id')
    try:
        test_statistic = TestStatistic.objects.get(pk=test_id)
    except DoesNotExist:
        handle_error(Error.TEST_STILL_ONGOING)
    if test_statistic.processed:
        results = test_statistic.get_unfinished_students()
    else:
        error = test_statistic.process()
        if error is not None:
            handle_error(error)
        results = test_statistic.get_unfinished_students()
    return success_response(students=results)


@main.route('/api/course/test/deleteTest', methods=['POST'])
@require_is_teacher
@require_having_course
def delete_test():
    get = get_json()
    test_id = get('test_id')
    course = g.course
    try:
        test = get_by_id_or_error(Test, test_id)
        course.update(pull__finished_tests=test, pull__unfinished_tests=test)
        test.delete()
        test.save()
    except DoesNotExist:
        pass
    return success_response()

