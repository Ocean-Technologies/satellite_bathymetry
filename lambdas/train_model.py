from lightgbm import LGBMRegressor
import pandas as pd
import numpy as np
import boto3
import joblib
import tempfile
import os
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split
import io

s3_client = boto3.client('s3')
s3r = boto3.resource('s3')

def train_model(request, context):
    
    if not request.get('model_creating'):
        return request

    bucket_name = os.environ.get('S3_BUCKET_NAME')
    s3_model_path = request['s3_mdl_path']
    model_path = f'{s3_model_path}/lgbm_model.pkl.z'

    # Read bathymetry data from s3
    try:
        resp_train = s3_client.get_object(Bucket=bucket_name, Key=request['train_data_path'])
        df = pd.read_csv(resp_train['Body'], sep=',')
    except Exception as e:
        print(e)
        request['model_creating'] = False
        return request

    # split into train and validation
    X_train, X_val, y_train, y_val = train_test_split(df.drop(['pixel_x', 'pixel_y', 'lat', 'long', 'z'], axis=1), df['z'], test_size=0.3, random_state=42)

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
    print('Training Model LGBM')
    lgbm.fit(X_train, y_train)
    # Predict to val data
    print("Predicting")
    p_lgbm = lgbm.predict(X_val)

    #request['predictions'] = p_lgbm.tolist()
    #request['y_val'] = y_val.to_list()

    # Extract metrics
    print('Extracting metrics')
    r2 = r2_score(y_val, p_lgbm)
    mae = mean_absolute_error(y_val, p_lgbm)
    mse = mean_squared_error(y_val, p_lgbm)

    request['r2_score'] = r2
    request['mean_absolute_error'] = mae
    request['mean_squared_error'] = mse


    # Predicti to whole data
    print('Predicting to whole data')
    p_all_data = lgbm.predict(df.drop(['pixel_x', 'pixel_y', 'lat', 'long', 'z'], axis=1))
    request['predictions'] = p_all_data.tolist()
    request['y_true'] = df['z'].to_list()

    # Write model into bucket
    print('Writing model into s3')
    try:
        with tempfile.TemporaryFile() as fp:
            joblib.dump(lgbm, fp)
            fp.seek(0)
            s3r.Object(bucket_name, model_path).put(Body=fp.read())

    except Exception as e:
        print(e)
        request['model_creating'] = False
        return request

    request['model_creating'] = True

    return request
