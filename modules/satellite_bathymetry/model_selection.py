from sklearn.model_selection import KFold
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor

def cross_validation(features, target, metric, mdl=None, n_splits=10, shuffle=True, random_state=None, verbose=False, **hyper_kwargs):
    """[Function to run cross validation easily and automated for LGBMRegressor model]

    Args:
        features     ([pandas dataframe]): [Pandas dataframe with used features]
        target       ([pandas series]):    [Pandas series with target]
        metric       ([function]):         [Metric function to be applied. (e.g r2_score, mean_absolute_error)]
        n_splits     (int, optional):      [K fold splits number]. Defaults to 10.
        shuffle      (bool, optional):     [Whether to shuffle the data before splitting into batches]. Defaults to True.
        random_state ([int], optional):    [Controls the randomness of each fold when shuffle True]. Defaults to None.
        verbose      ([bool]):             [Controls prints when running]

        hyper_kwargs ([kwargs], optional): [Key arguments for model hyperparameters]

    Returns:
        k_fold_scores ([dict]):            [Dict with scores for each fold on cross validation]
    """

    if mdl is None or issubclass(mdl, LGBMRegressor):
        learning_rate = hyper_kwargs.get('learning_rate', 0.1)
        max_depth = hyper_kwargs.get('max_depth', -1)
        min_child_samples = hyper_kwargs.get('min_child_samples', 20)
        subsample = hyper_kwargs.get('subsample', 1.0)
        colsample_bytree = hyper_kwargs.get('colsample_bytree', 1.0)
        n_estimators = hyper_kwargs.get('n_estimators', 100)

        mdl = LGBMRegressor(learning_rate=learning_rate, max_depth=max_depth, 
                    min_child_samples=min_child_samples, subsample=subsample, 
                    colsample_bytree=colsample_bytree, n_estimators=n_estimators)
        if verbose:
            print('LGBM Regressor chosen')

    elif issubclass(mdl, RandomForestRegressor):
        max_depth = hyper_kwargs.get('max_depth', None)
        n_estimators = hyper_kwargs.get('n_estimators', 100)
        min_samples_split = hyper_kwargs.get('min_samples_split', 2)
        min_samples_leaf = hyper_kwargs.get('min_samples_leaf', 1)
        max_features = hyper_kwargs.get('max_features', 'auto')
        
        mdl = RandomForestRegressor(max_depth=max_depth, n_estimators=n_estimators, min_samples_split=min_samples_split, 
                            min_samples_leaf=min_samples_leaf, max_features=max_features, random_state=42, n_jobs=-1)
        
        if verbose:
            print('Random Forest chosen')
    else:
        raise Exception(f'Model {mdl} not an accepted class')

    k_fold_scores = dict()
    kf = KFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state)
    for i, (lines_train, lines_val) in enumerate(kf.split(features)):
        X_train = features.iloc[lines_train]
        X_val = features.iloc[lines_val]
        y_train = target.iloc[lines_train]
        y_val = target.iloc[lines_val]
        
        

        mdl.fit(X_train, y_train)
        p = mdl.predict(X_val)
        score = metric(y_val, p)
        
        k_fold_scores[f'k_fold_{i}'] = score
        if verbose:
            print(f'Split {i} -- Score: {score}')
        
    return k_fold_scores