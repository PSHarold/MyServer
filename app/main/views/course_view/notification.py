# -*- coding: utf-8 -*-
from . import *

@main.route('/api/course/notification/getNotifications', methods=['POST'])
@require_having_course
def get_notifications():
    course = g.course
    get = get_json()
    page = get('page')
    notifications=course.get_notifications_paginating(page=page)
    return success_response(notifications=notifications)


@main.route('/api/course/notification/postNotification', methods=['POST'])
# @require_is_teacher
@require_having_course
def post_notification():
    course = get_sub_course_pre()
    get = get_json()
    content = get('content')
    on_top = get('on_top')
    title = get('title')
    by = g.user.name
    notification = Notification(title=title, created_on=datetime.datetime.now(), content=content, on_top=on_top, by=by,
                                unread_students=no_dereference_id_only_list(course.students))
    if notification.on_top:
        course.top_notifications.insert(0, notification)
    else:
        course.normal_notifications.insert(0, notification)
    try:
        course.save()
    except NotImplementedError:
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)

    return success_response(ntfc_id=str(notification.ntfc_id))


@main.route('/api/course/notification/modifyNotification', methods=['POST'])
@require_is_teacher
@require_having_course
def modify_notification():
    course = get_sub_course_pre()
    allowed = ['content', 'title', 'on_top']
    get = get_json()
    try:
        print request.get_json()
        try:
            notification = course.normal_notifications.get(ntfc_id=ObjectId(get('ntfc_id')))
        except:
            notification = course.top_notifications.get(ntfc_id=ObjectId(get('ntfc_id')))
    except:
        handle_error(Error.NOTIFICATION_NOT_FOUND)
    modify_from_request_or_422(instance=notification, allowed_fields=allowed,
                               exceptions=['ntfc_id', 'course_id', 'sub_id'])

    try:
        if notification.on_top:
            course.normal_notifications.remove(notification)
            course.top_notifications.insert(0, notification)
        else:
            course.top_notifications.remove(notification)
            course.normal_notifications.insert(0, notification)
        course.save()
    except:
        handle_error(Error.UNKNOWN_INTERNAL_ERROR)
    return success_response(ntfc_id=str(notification.ntfc_id))


@main.route('/api/course/notification/deleteNotification', methods=['POST'])
def delete_notification():
    course = get_sub_course_pre()
    get = get_json()
    ntfc_id = get('ntfc_id')
    try:
        print get('ntfc_id')
        try:
            notification = course.normal_notifications.get(ntfc_id=get('ntfc_id'))
            course.normal_notifications.remove(notification)
        except:
            notification = course.top_notifications.get(ntfc_id=get('ntfc_id'))
            course.top_notifications.remove(notification)
        course.save()
    except:
        handle_error(Error.NOTIFICATION_NOT_FOUND)

    return success_response()


@main.route('/api/course/notification/markRead', methods=['POST'])
@require_token
def mark_read():
    get = get_json()
    course_id = get('course_id') + '#' + get('sub_id')
    query = Course.objects(pk=course_id)
    query.filter(notifications__ntfc_id=ObjectId(get('ntfc_id'))).update(
        pull__notifications__S__unread_students=g.user.user_id)
    return success_response()


@main.route('/api/course/notification/markUnread', methods=['POST'])
@require_token
def mark_unread():
    get = get_json()
    course_id = get('course_id') + '#' + get('sub_id')
    query = Course.objects(pk=course_id)
    query.filter(notifications__ntfc_id=ObjectId(get('ntfc_id'))).update(
        add_to_set__notifications__S__unread_students=g.user.user_id)
    return success_response()


@main.route('/api/course/notification/getUnreadNotifications', methods=['POST'])
@require_having_course
def get_unread():
    course = g.course
    return success_response(notifications=course.get_unread_notifications(student=g.user))