import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import os
from datetime import datetime
import boto3


conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)

step_client = boto3.client('stepfunctions')


def get_models(user_email):
    global engine
    global step_client

    connection = engine.connect()

    query_user_models = """
    SELECT id, created, name, s3_mdl_path, r2_score, mean_absolute_error, mean_squared_error, status FROM model where user_email='{}';
    """.format(user_email)

    results = [dict(row) for row in connection.execute(query_user_models).fetchall()]

    connection.close()

    response_dict = dict()
    for dic in results:
        response_dict[dic['id']] = {
            "name": dic['name'],
            "created": dic['created'].strftime(format='%Y-%m-%d %H:%M:%S'),
            "s3_mdl_path": dic['s3_mdl_path'],
            "status": dic['status'],
            "r2_score": dic['r2_score'],
            "mean_absolute_error": dic['mean_absolute_error'],
            "mean_squared_error": dic['mean_squared_error']
        }


    return response_dict

def generate_predictions(request):
    """
    {
        gee_image_data: str,
        model_id: int,
        s3_mdl_path: str,
        prediction_name: str,
        user_email: str,
        image_date: str
    }
    """

    gee_image_data = request.get('gee_image_data')
    model_id = request.get('model_id')
    s3_mdl_path = request.get('s3_mdl_path')
    prediction_name = request.get('prediction_name')
    user_email = request.get('user_email')

    # TODO validate with schema?
    if gee_image_data is None or model_id is None or s3_mdl_path is None or prediction_name is None or user_email is None:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Invalid request"
            })
        }

    connection = engine.connect()

    query_check_prediction = """
    SELECT id FROM prediction WHERE name='{}' and user_email='{}'
    """.format(
        prediction_name,
        user_email
    )

    prediction_exists = connection.execute(query_check_prediction).fetchone()

    if prediction_exists:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "Model with this name already exists"
            })
        }

    query_insert_prediction = """
    INSERT INTO prediction (created, name, s3_prediction_path, status, user_email, model_id)
    VALUES ('{}', '{}', '{}', '{}', '{}', '{}')
    """.format(
        datetime.utcnow(),
        request['prediction_name'],
        request['s3_mdl_path'],
        'creating',
        request['user_email'],
        request['model_id']
    )
    result = connection.execute(query_insert_prediction)
    prediction_id = result.lastrowid
    request['prediction_id'] = prediction_id

    step_response = step_client.start_execution(
        stateMachineArn='arn:aws:states:sa-east-1:457581096601:stateMachine:CreatePredictionMachine',
        input=json.dumps(request)
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "msg": "Creating Prediction, it will take a while."
        })
    }
    
    


def lambda_handler(event, context):
    query_string = event.get('queryStringParameters')

    if event['httpMethod'] == 'GET':
        user_email = query_string.get('user_email')
        if user_email is not None:
            response = {
                "statusCode": 200,
                "headers": {
                    "Content-Type": 'application/json'
                }
            }
            body = get_models(user_email)
            response['body'] = json.dumps(body)

            return response
        else:
            return {
                "statusCode": 400,
                'body': json.dumps('Invalid request')
            }
    elif event['httpMethod'] == 'POST':
        try:
            request = json.loads(event['body'])
        except Exception as e:
            return {
                "statusCode": 400,
                'body': json.dumps('Invalid request')
            }
        response = generate_predictions(request)
        return response
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid request')
        }