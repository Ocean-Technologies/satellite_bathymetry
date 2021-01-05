from sklearn.model_selection import KFold

def cross_validation(features, target, n_splits=10, shuffle=True, random_state=None, **hyper_kwargs):
    """[Function to run cross validation easily and automated]

    Args:
        features     ([pandas dataframe]): [Pandas dataframe with used features]
        target       ([pandas series]):    [Pandas series with target]
        n_splits     (int, optional):      [K fold splits number]. Defaults to 10.
        shuffle      (bool, optional):     [Whether to shuffle the data before splitting into batches]. Defaults to True.
        random_state ([int], optional):    [Controls the randomness of each fold when shuffle True]. Defaults to None.

        kwargs       ([kwargs], optional): [Key arguments for model hyperparameters]

    Returns:
        k_fold_scores ([dict]):            [Dict with scores for each fold on cross validation]
    """

    learning_rate = kwargs.get('learning_rate', 0.1)
    max_depth = kwargs.get('max_depth', -1)
    min_child_samples = kwargs.get('min_child_samples', 20)
    subsample = kwargs.get('subsample', 1.0)
    colsample_bytree = kwargs.get(colsample_bytree, 1.0)
    n_estimators = kwargs.get(n_estimators, 100)

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
        score = r2_score(y_val, p)
        
        k_fold_scores[f'k_fold_{i}'] = score
        
    return k_fold_scores