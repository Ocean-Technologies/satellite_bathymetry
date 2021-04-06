import os
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
from datetime import datetime
import json


conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)


def get_detailed_prediction_info(project_id):
    global engine

    connection = engine.connect()

    query_prediction = """
    SELECT prediction.name as pred_name, prediction.s3_prediction_path as pred_path, model.name as model_name, model.id as model_id 
    FROM prediction INNER JOIN
    model ON prediction.model_id=model.id WHERE prediction.id='{}'
    """.format(project_id)
    response = dict(connection.execute(query_prediction).fetchone())

    connection.close()

    return response


def get_all_user_predictions(user_email):
    global engine

    connection = engine.connect()

    query_all = """
    SELECT id, created, name, status FROM prediction WHERE user_email='{}'
    """.format(
        user_email
    )

    # TODO work with pagination?
    results = connection.execute(query_all).fetchall()
    results_dict_list = [dict(row) for row in results]

    response = dict()
    for row in results_dict_list:
        aux_dict = row.copy()
        aux_id = aux_dict['id']
        aux_dict['created'] = aux_dict['created'].strftime(format='%Y-%m-%d %H:%M:%S')
        del aux_dict['id']
        response[aux_id] = aux_dict

    connection.close()

    return response


def get_predictions_handler(event, context):
    query_parameters = event['queryStringParameters']

    prediction_id_bool = bool(query_parameters.get('prediction_id'))
    user_email_bool = bool(query_parameters.get('user_email'))

    if prediction_id_bool or (prediction_id_bool and user_email_bool):
        prediction_id = event['queryStringParameters']['prediction_id']
        response_object = {}
        response_object['statusCode'] = 200
        response_object['headers'] = {}
        response_object['headers']['Content-Type'] = 'application/json'
        #response_object['headers']['Access-Control-Allow-Origin'] = "*"
        response_object['headers']['Access-Control-Allow-Credentials']: True
        response_projects = get_detailed_prediction_info(prediction_id)
        response_object['body'] = json.dumps(response_projects)
    elif user_email_bool and not prediction_id_bool:
        user_email = event['queryStringParameters']['user_email']
        response_object = {}
        response_object['statusCode'] = 200
        response_object['headers'] = {}
        response_object['headers']['Content-Type'] = 'application/json'
        response_object['headers']['Access-Control-Allow-Origin'] = "*"
        response_object['headers']['Access-Control-Allow-Credentials']: True
        response_predictions = get_all_user_predictions(user_email)
        response_object['body'] = json.dumps(response_predictions)
    else:
        response_object = {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Bad Request"
            })
        }

    return response_object
