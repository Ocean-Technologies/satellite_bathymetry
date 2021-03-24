from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os


app = Flask(__name__)


conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
app.config['SQLALCHEMY_DATABASE_URI'] = conn_string

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    google_id = db.Column(
        db.Integer, # use this as pk?
        nullable=True, # change to false?
    )
    email = db.Column(
        db.String(300),
        nullable=False
    )
    s3_user_folder = db.Column(
        db.String(300),
        nullable=False
    )


class Model(db.Model):
    __tablename__ = 'model'
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    created = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    name = db.Column(
        db.String(300),
        nullable=False
    )
    s3_mdl_path = db.Column(
        db.String(300),
        nullable=False
    )
    status = db.Column(
        db.String(20),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

class Prediction(db.Model):
    __tablename__ = 'prediction'

    id = db.Column(
        db.Integer,
        primary_key=True
    )
    created = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    name = db.Column(
        db.String(300),
        nullable=False
    )
    s3_forecast_path = db.Column(
        db.String(300),
        nullable=False
    )
    start_date = db.Column(
        db.DateTime,
        nullable=False,
    )
    end_date = db.Column(
        db.DateTime,
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    model_id = db.Column(
        db.Integer,
        db.ForeignKey('model.id'),
        nullable=False
    )