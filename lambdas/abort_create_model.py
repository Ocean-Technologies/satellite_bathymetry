import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import os
#import boto3

conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)
#s3_client = boto3.client('s3')

def abort_create_model(request, context):

    connection = engine.connect()

    # Remove model from db
    if request.get('model_id'):
        query_delete_model = """
        DELETE FROM model WHERE id='{}'
        """.format(request['model_id'])
        connection.execute(query_delete_model)
    
    # Remove model folder from s3
    if request.get('s3_mdl_path'):
        s3_bucket_name = os.environ.get('s3_bucket_name')
        s3_response = s3_client.list_objects_v2(Bucket=s3_bucket_name, Prefix=request['s3_mdl_path'])
        if 'Contents' in s3_response:
            for obj in s3_response['Contents']:
                print('Deleting', obj['Key'])
                s3_client.delete_object(Bucket=s3_bucket_name, Key=obj['Key'])
    
    return {
        "statusCode": 400,
        "body": json.dumps(
            "Create model aborted"
        )
    }
