from lightgbm import LGBMRegressor
import pandas as pd
import numpy as np
import boto3
import joblib
import tempfile
import os
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import io

s3_client = boto3.client('s3')
s3r = boto3.resource('s3')

def train_model(request, context):

    if not request.get('model_is_created'):
        return request

    # Read bathymetry data from s3
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    project_id = request['project_id']
    model_path = f'{project_id}/lgbm_model.pkl.z'

    resp_train = s3_client.get_object(Bucket=bucket_name, Key=request['train_data_path'])
    df = pd.read_csv(resp_train['Body'], sep=',')
    # split into train and validation
    train_data, val_data = np.split(df.sample(frac=1, random_state=42), [int(0.7 * len(dataset))])

    features_train = train_data.drop('z', axis=1)
    target_train = train_data['z']

    features_val = val_data.drop('z', axis=1)
    target_val = val_data['z']

    args_lgbm = [0.06189835094365267, 9, 1, 0.8695551533271082, 0.6534274736020848, 976, 2, 1]
    lr = args_lgbm[0]
    max_depth = args_lgbm[1]
    min_child_samples = args_lgbm[2]
    subsample = args_lgbm[3]
    colsample_bytree = args_lgbm[4]
    n_estimators = args_lgbm[5]

    lgbm = LGBMRegressor(learning_rate=lr, num_leaves=2 ** max_depth, max_depth=max_depth,
                        min_child_samples=min_child_samples, subsample=subsample,
                        colsample_bytree=colsample_bytree, bagging_freq=1, n_estimators=n_estimators,
                        random_state=0, class_weight='balanced', n_jobs=6)

    # Train model
    lgbm.fit(features_train, target_train)
    # Predict to val data
    p_lgbm = lgbm.predict(features_val)

    # Extract metrics
    r2_score = r2_score(target_val, p_lgbm)
    mae = mean_absolute_error(target_val, p_lgbm)
    mse = mean_squared_error(target_val, p_lgbm)

    metrics_buffer = io.StringIO()
    metrics_df = pd.DataFrame([{"r2 Score": r2, 'Mean Absolute Error': mae, "Mean Squared Error": mse}])
    metrics_df.to_csv(metrics_buffer, index=None)
    metrics_path = f'{project_id}/metrics.csv'

    # Upload metrics df to csv
    try:
        s3r.Object(bucket_name, metrics_path).put(Body=metrics_buffer.getvalue())
    except Exception as e:
        print(e)
        request['model_is_created'] = False

        return request

    # Write model into bucket
    with tempfile.TemporaryFile() as fp:
        joblib.dump(lgbm, fp)
        fp.seek(0)
        s3r.put_object(Body=fp.read(), Bucket=bucket_name, Key=model_path)

    request['model_is_created'] = True

    return request






