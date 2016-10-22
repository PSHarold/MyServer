from mongoengine import Document, EmbeddedDocument, StringField, ListField, ReferenceField, EmbeddedDocumentField, \
    DateTimeField, \
    BooleanField, IntField, EmbeddedDocumentListField, ObjectIdField, DictField, NULLIFY, PULL, context_managers, \
    DoesNotExist, ValidationError, MapField

from bson import ObjectId, DBRef
import datetime
from enum import Enum
from ..general import *
from .face_models import *

def no_dereference_id_only_list(list_field):
    if list_field is None:
        return []
    with context_managers.no_dereference(list_field._instance.__class__):
        return map(lambda x: x.id, list_field)




def pull_from_reference_list(list_field, pk):
    document = list_field._instance
    document.update(**{'pull__' + list_field._name: DBRef(collection=document._cls, id=pk)})



def time_to_string(time_o):
    if time_o is None:
        return ""
    return time_o.strftime("%Y-%m-%d %H:%M:%S")


def traverse_detecting_none(src_list, func):
    t_list = []

    def safely(x):
        if isinstance(x, DBRef):
            return
        t_list.append(func(x))

    map(safely, src_list)
    return t_list

class ToDictType(Enum):
    base = 0
    for_teacher = 1
    for_teacher_brief = 2
    for_teacher_detail = 3
    for_student = 4
    for_student_brief = 5
    for_student_detail = 6
