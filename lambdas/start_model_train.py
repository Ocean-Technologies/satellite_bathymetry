import boto3
import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import uuid
from datetime import datetime


step_client = boto3.client('stepfunctions')

conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)

def start_model_train(event, context):

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

    coordinates = request.get('coordinates')
    start_date = request.get('start_date')
    end_date = request.get('end_date')
    request['project_id'] = str(uuid.uuid4()).replace('-', '')

    if coordinates is None or start_date is None or end_date is None:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Invalid request"
            })
        }

    connection = engine.connect()

    query_insert_model = """
    INSERT INTO model (created, name, s3_mdl_path, status, user_id)
    VALUES ('{}', '{}', '{}', '{}', '{}')
    """.format(
        datetime.utcnow(),
        request['model_name'],
        request['project_id'],
        'creating',
        request['user_id']
    )
    connection.execute(query_insert_model)
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




