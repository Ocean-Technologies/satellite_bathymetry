import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import os
import json

conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)


def create_prediction_done(request, context):
    connection = engine.connect()

    query_update_prediction = """
    UPDATE prediction SET status='{}', s3_prediction_path='{}' WHERE id='{}'
    """.format(
        'active',
        request['s3_prediction_path'],
        request['prediction_id']
    )
    connection.execute(query_update_prediction)
    connection.close()

    return {
        "statusCode": 200,
        "body": json.dumps(
            "Prediction finished"
        )
    }
