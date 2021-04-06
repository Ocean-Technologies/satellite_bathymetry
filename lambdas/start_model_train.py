import boto3
import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import uuid
from datetime import datetime
import os


step_client = boto3.client('stepfunctions')

conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)

def start_model_train(event, context):
    """
    {
        user_email: str,
        model_name: str,
        gee_image_data: str,
        raw_bat_path: str,
        bat_utm_region_code: str,
        bat_utm_region_letter: str,
    }
    """

    try:
        request = json.loads(event['body'])
    except Exception as e:
        print(e)

        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Invalid request"
            })
        }

    model_name = request.get('model_name')
    user_email = request.get('user_email')
    request['s3_mdl_path'] = str(uuid.uuid4()).replace('-', '')

    if model_name is None or user_email is None:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Invalid request"
            })
        }

    connection = engine.connect()

    query_check_model = """
    SELECT id FROM model WHERE name='{}' and user_email='{}'
    """.format(
        model_name,
        user_email
    )
    
    model_exists = connection.execute(query_check_model).fetchone()

    if model_exists:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "Model with this name already exists"
            })
        }

    query_insert_model = """
    INSERT INTO model (created, name, s3_mdl_path, status, user_email)
    VALUES ('{}', '{}', '{}', '{}', '{}')
    """.format(
        datetime.utcnow(),
        request['model_name'],
        request['s3_mdl_path'],
        'creating',
        request['user_email']
    )
    result = connection.execute(query_insert_model)
    model_id = result.lastrowid
    request['model_id'] = model_id

    step_response = step_client.start_execution(
        stateMachineArn='arn:aws:states:sa-east-1:457581096601:stateMachine:TrainModelMachine',
        input=json.dumps(request)
    )

    connection.close()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "msg": "Model training, it will take a while."
        })
    }




