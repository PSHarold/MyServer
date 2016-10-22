# -*- coding: utf-8 -*-

from flask_wtf import Form
from wtforms.fields import StringField, BooleanField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo


class LoginForm(Form):
    user_id = StringField(u'用户名', validators=[DataRequired()])
    password = PasswordField(u'密码')
    submit = SubmitField(u'登陆')


class ResetPasswordForm(Form):
    password = PasswordField(u'新密码', validators=[DataRequired()])
    confirm_password = PasswordField(u'确认密码', validators=[DataRequired(),
                                                         EqualTo('confirm_password',
                                                                 message=u'两次密码必须一致!')])
    submit = SubmitField(u'提交')
