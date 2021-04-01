import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import os

conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)

def get_models(user_email):
    global engine

    connection = engine.connect()

    query_user_models = """
    SELECT id, created, name, s3_mdl_path, status FROM model where user_email='{}';
    """.format(user_email)

    results = [dict(row) for row in connection.execute(query_user_models).fetchall()]

    connection.close()

    response_dict = dict()
    for dic in results:
        response_dict[dic['id']] = {
            "name": dic['name'],
            "created": dic['created'].strftime(format='%Y-%m-%d %H:%M:%S'),
            "s3_mdl_path": dic['s3_mdl_path'],
            "status": dic['status']
        }


    return response_dict

def generate_predictions(request):
    pass


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
        response_body = generate_predictions(request)
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid request')
        }
    
        