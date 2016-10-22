from flask import Flask
import mongoengine


class Config:
    SECRET_KEY = 'mysecretsecretkey'
    def init_app(self, app):
        app.config['SECRET_KEY'] = self.SECRET_KEY
        app.config['MAIL_SERVER'] = 'smtp.qq.com'
        app.config['MAIL_PORT'] = 465
        app.config['MAIL_USE_TLS'] = False
        app.config['MAIL_USE_SSL'] = True
        app.config['MAIL_USERNAME'] = '123@qq.com'
        app.config['MAIL_PASSWORD'] = '123'
        app.config['ADMINS'] = ['123@qq.com']
        mongoengine.connect('mydatabase')
        import os
        from app.general import COVER_FOLDER, AVATAR_FOLDER, FACE_FOLDER
        if not os.path.exists(COVER_FOLDER):
            os.mkdir(COVER_FOLDER)
        if not os.path.exists(AVATAR_FOLDER):
            os.mkdir(AVATAR_FOLDER)
        if not os.path.exists(FACE_FOLDER):
            os.mkdir(FACE_FOLDER)
        return app
