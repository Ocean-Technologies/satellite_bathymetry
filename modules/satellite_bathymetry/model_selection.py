from sklearn.model_selection import KFold
from lightgbm import LGBMRegressor

def cross_validation(features, target, metric, n_splits=10, shuffle=True, random_state=None, **hyper_kwargs):
    """[Function to run cross validation easily and automated for LGBMRegressor model]

    Args:
        features     ([pandas dataframe]): [Pandas dataframe with used features]
        target       ([pandas series]):    [Pandas series with target]
        metric       ([function]):         [Metric function to be applied. (e.g r2_score, mean_absolute_error)]
        n_splits     (int, optional):      [K fold splits number]. Defaults to 10.
        shuffle      (bool, optional):     [Whether to shuffle the data before splitting into batches]. Defaults to True.
        random_state ([int], optional):    [Controls the randomness of each fold when shuffle True]. Defaults to None.

        hyper_kwargs ([kwargs], optional): [Key arguments for model hyperparameters]

    Returns:
        k_fold_scores ([dict]):            [Dict with scores for each fold on cross validation]
    """

    learning_rate = hyper_kwargs.get('learning_rate', 0.1)
    max_depth = hyper_kwargs.get('max_depth', -1)
    min_child_samples = hyper_kwargs.get('min_child_samples', 20)
    subsample = hyper_kwargs.get('subsample', 1.0)
    colsample_bytree = hyper_kwargs.get('colsample_bytree', 1.0)
    n_estimators = hyper_kwargs.get('n_estimators', 100)

    k_fold_scores = dict()
    kf = KFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state)
    for i, (lines_train, lines_val) in enumerate(kf.split(features)):
        X_train = features.iloc[lines_train]
        X_val = features.iloc[lines_val]
        y_train = target.iloc[lines_train]
        y_val = target.iloc[lines_val]
        
        mdl = LGBMRegressor(learning_rate=learning_rate, max_depth=max_depth, 
                    min_child_samples=min_child_samples, subsample=subsample, 
                    colsample_bytree=colsample_bytree, n_estimators=n_estimators)

        mdl.fit(X_train, y_train)
        p = mdl.predict(X_val)
        score = metric(y_val, p)
        
        k_fold_scores[f'k_fold_{i}'] = score
        
    return k_fold_scores