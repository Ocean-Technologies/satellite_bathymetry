import json
import pymysql
import sqlalchemy
from sqlalchemy import create_engine


conn_string = f"mysql+pymysql://{os.environ['RDS_USERNAME']}:{os.environ['RDS_PASSWORD']}@{os.environ['RDS_HOSTNAME']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB_NAME']}"
engine = create_engine(conn_string)


def create_model_done(request, context):
    connection = engine.connect()

    query_update_model = """
    UPDATE model SET status='{}' WHERE id='{}'
    """.format(
        'active',
        request['model_id']
    )
    connection.execute(query_insert_model)
    connection.close()

    return {
        "statusCode": 200,
        "body": json.dumps(
            "Model training finished"
        )
    }
