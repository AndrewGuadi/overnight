from flask_wtf import FlaskForm
from wtforms    import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class SignupForm(FlaskForm):
    name     = StringField('Name',  validators=[DataRequired(), Length(1,120)])
    email    = StringField('Email', validators=[DataRequired(), Email(), Length(1,120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(8,128)])
    confirm  = PasswordField('Confirm', validators=[EqualTo('password')])
    submit   = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email    = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Log In')
