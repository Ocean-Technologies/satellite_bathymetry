from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from skopt import forest_minimize
from functools import partial


def _tune_tree_model(model_object, metric, X_train, X_val, y_train, y_val, kind, space):

    if issubclass(model_object, LGBMRegressor):
            lr = space[0]
            max_depth = space[1]
            min_child_samples = space[2]
            subsample = space[3]
            colsample_bytree = space[4]
            n_estimators = space[5]
        
            mdl = LGBMRegressor(learning_rate=lr, max_depth=max_depth, min_child_samples=min_child_samples, subsample=subsample, 
                                colsample_bytree=colsample_bytree, n_estimators=n_estimators)
            mdl.fit(X_train, y_train)
            p = mdl.predict(X_val)

            score = metric(y_val, p)

            if kind=='maximize':
                return -score
            return score

    elif issubclass(model_object, RandomForestRegressor):
        max_depth = space[0]
        n_estimators = space[1]
        min_samples_split = space[2]
        min_samples_leaf = space[3]
        max_features = space[4]
        
        mdl = RandomForestRegressor(max_depth=max_depth, n_estimators=n_estimators, min_samples_split=min_samples_split, 
                            min_samples_leaf=min_samples_leaf, max_features=max_features, random_state=42, n_jobs=-1)

        mdl.fit(X_train, y_train)
        p = mdl.predict(X_val)

        score = metric(y_val, p)
        print(score)
        if kind=='maximize':
            return -score
        return score

def tune_tree_model(model_object, metric, X_train, X_val, y_train, y_val, kind='maximize', random_state=160000, n_random_starts=20, n_calls=20, verbose=False, **kwargs):
    """
        Apply simple Bayesian optimization to tree models (LGBM or RandomForestRegressor)
        using the forest_minimize skopt method.
        Choose a metric and the kind of validation.
        maximize to search for a higher metric value
        minimize to search for a lower metric value

    Args:
        model_object ([class]): [Model to be used. (LGBMRegressor | RandomForestRegressor)]
        metric ([function]): [Metric function to be applied. (e.g r2_score, mean_absolute_error)]
        X_train ([pandas Dataframe]): [Train features dataframe]
        X_val ([pandas Dataframe]): [Validation features dataframe]
        y_train ([pandas Series]): [Train target series]
        y_val ([pandas Series]): [Validation target series]
        kind (str, optional): [Defines the type of optimization, if maximize it will search for the higher 
                              value of defined metric, else it will search for the lower value]. Defaults to 'maximize'.
        random_state (int, optional): [Set random state to something other than None for reproducible results]. Defaults to 160000.
        n_random_starts (int, optional): [Number of evaluations of func with random points before approximating it with base_estimator]. Defaults to 20.
        n_calls (int, optional): [Number of calls to func]. Defaults to 20.
        verbose (boolean, optional): [Control the verbosity. It is advised to set the verbosity to True for long optimization runs]. Defaults to False.

        **kwargs: (tuples, optional): [Key arguments containing tuples for the search space]

        - e.g:
            res = tune_tree_model(LGBMRegressor, r2_score, X_train, X_val, y_train, y_val, learning_rate=(1e-5, 1e-1, 'log-uniform'), max_depth=(1,20))

    Raises:
        Exception: [If model subclass is not the accepted raises an Exception]

    Returns:
        [scipy.optimize.optimize.OptimizeResult]: [scipy object containing all results for the optimization. 
                                                  To get the best set of hyperparameters use the key ['x'] on the results variable
                                                  e.g: res = tune_tree_model(LGBMRegressor, r2_score, X_train, X_val, y_train, y_val)
                                                       hypers = res['x']
    """

    if issubclass(model_object, LGBMRegressor):
        lr = kwargs.get('learning_rate', (1e-3, 1e-1, 'log-uniform'))
        max_depth = kwargs.get('max_depth', (1, 10))
        min_child_samples = kwargs.get('min_child_samples', (1, 20))
        subsample = kwargs.get('subsample', (0.05, 1.))
        colsample_bytree = kwargs.get('colsample_bytree', (0.05, 1.))
        n_estimators = kwargs.get('n_estimators', (100,1000))
        
        space = [
            lr,
            max_depth,
            min_child_samples,
            subsample,
            colsample_bytree,
            n_estimators
        ]
        func = partial(_tune_tree_model, model_object, metric, X_train, X_val, y_train, y_val, kind)
        
        res = forest_minimize(func, space, random_state=random_state, n_random_starts=n_random_starts, n_calls=n_calls, verbose=verbose)
        
        return res

    elif issubclass(model_object, RandomForestRegressor):
        max_depth = kwargs.get('max_depth', (1, 10))
        n_estimators=kwargs.get('n_estimators', (100,200))
        min_samples_split = kwargs.get('min_samples_split', (2, 10))
        min_samples_leaf = kwargs.get('min_samples_leaf', (1, 4))
        max_features = kwargs.get('max_features', ('auto', 'sqrt'))

        space = [
            max_depth,
            n_estimators,
            min_samples_split,
            min_samples_leaf,
            max_features
        ]
        func = partial(_tune_tree_model, model_object, metric, X_train, X_val, y_train, y_val, kind)
        res = forest_minimize(func, space, random_state=random_state, n_random_starts=n_random_starts, n_calls=n_calls, verbose=verbose)

        return res
    
    raise Exception('Model object not found')
