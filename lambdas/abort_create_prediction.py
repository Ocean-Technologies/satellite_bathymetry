import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import os
import json


conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)


def abort_create_prediction(request, context):
    connection = engine.connect()

    # Remove forecast from db
    if request.get('prediction_id'):
        query_delete_forecast = """
        DELETE FROM prediction WHERE id='{}'
        """.format(request['prediction_id'])
        connection.execute(query_delete_forecast)

    return {
        "statusCode": 400,
        "body": json.dumps(
            "Create prediction aborted"
        )
    }
