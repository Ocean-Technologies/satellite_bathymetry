import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine
import os


conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)


def abort_create_prediction(request, context):
    connection = engine.connect()

    # Remove forecast from db
    if request.get('forecast_id'):
        query_delete_forecast = """
        DELETE FROM forecast WHERE id='{}'
        """.format(request['forecast_id'])
        connection.execute(query_delete_forecast)

    return {
        "statusCode": 400,
        "body": json.dumps(
            "Create prediction aborted"
        )
    }
