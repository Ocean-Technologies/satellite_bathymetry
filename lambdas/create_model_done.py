import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import os


conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)


def create_model_done(request, context):
    connection = engine.connect()

    query_update_model = """
    UPDATE model SET status='{}', r2_score='{}', mean_absolute_error='{}', mean_squared_error='{}' WHERE id='{}'
    """.format(
        'active',
        request['r2_score'],
        request['mean_absolute_error'],
        request['mean_squared_error'],
        request['model_id']
    )
    connection.execute(query_update_model)
    connection.close()

    return {
        "statusCode": 200,
        "body": json.dumps(
            "Model training finished"
        )
    }
