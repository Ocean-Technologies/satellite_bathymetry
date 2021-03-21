import boto3
import json

step_client = boto3.client('stepfunctions')

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

    if coordinates is None or start_date is None or end_date is None:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Invalid request"
            })
        }

    step_response = step_client.start_execution(
        stateMachineArn='arn:aws:states:sa-east-1:457581096601:stateMachine:TrainModelMachine',
        input=json.dumps(request)
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "msg": "Model training, it will take a while."
        })
    }




