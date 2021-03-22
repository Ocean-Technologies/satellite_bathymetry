from lightgbm import LGBMRegressor
import pandas as pd
import boto3
import joblib
import tempfile


s3_client = boto3.client('s3')
s3r = boto3.resource('s3')

def train_model(request, context):
    
    bucket_name = request['s3_bucket_name']
    train_path = request['train_data_name']
    test_path = request['test_data_name']

    resp_train = s3_client.get_object(Bucket=bucket_name, Key=train_path)
    resp_test = s3_client.get_object(Bucket=bucket_name, Key=test_path)

    df_train = pd.read_csv(resp_train['Body'], sep=',')
    df_val = pd.read_csv(resp_test['Body'], sep=',')

    features_train = df_train.drop('z', axis=1)
    target_train = df_train['z']

    features_val = df_val.drop('z', axis=1)
    target_val = df_val['z']

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
    p_lgbm = lgbm.predict(features_val)

    project_id = request['project_id']
    model_path = f'{project_id}/lgbm_model.pkl.z'
    bucket_name = request['s3_bucket_name']

    # Write model into bucket
    with tempfile.TemporaryFile() as fp:
        joblib.dump(lgbm, fp)
        fp.seek(0)
        s3r.put_object(Body=fp.read(), Bucket=bucket_name, Key=model_path)







