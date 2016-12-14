# -*- coding: utf-8 -*-

import random, string, flask
from itsdangerous import TimedJSONWebSignatureSerializer, BadSignature, SignatureExpired

SEAT_KEY = 'Harold'

def generate_qr_code():
    s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=5)
    return s.dumps({'seat_key': SEAT_KEY})

def validate_qr_code(code):
    try:
        s = TimedJSONWebSignatureSerializer(flask.current_app.config['SECRET_KEY'], expires_in=5)
        c = s.loads(code)
        if c['seat_key'] == SEAT_KEY:
            return True
        return False
    except BadSignature:
        return False
    except SignatureExpired:
        return False

# DYNAMIC_QR_CODE = ''.join(
#     random.SystemRandom().choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(20))

import os

#HOME = os.path.expanduser('~')
FACE_FOLDER = "./FACES/"
AVATAR_FOLDER = "./AVATARS/"
COVER_FOLDER = "./COVERS/"


# @scheduler.scheduled_job('interval', seconds=5)
# def generate_qr_code():
#     global DYNAMIC_QR_CODE
#     DYNAMIC_QR_CODE = ''.join(
#         random.SystemRandom().choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in
#         range(20))
