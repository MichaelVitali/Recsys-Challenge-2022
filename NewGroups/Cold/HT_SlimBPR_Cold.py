if __name__ == "__main__":

    from Recommenders.SLIM.Cython.SLIM_BPR_Cython import SLIM_BPR_Cython
    from Evaluation.K_Fold_Evaluator import K_Fold_Evaluator_MAP
    from Utils.recsys2022DataReader import createURM
    from Data_manager.split_functions.split_train_validation_random_holdout import split_train_in_two_percentage_global_sample
    from Evaluation.Evaluator import EvaluatorHoldout
    import json
    from datetime import datetime
    import optuna as op
    import numpy as np
    import csv
    from optuna.samplers import RandomSampler, GridSampler

    # ---------------------------------------------------------------------------------------------------------
    # Loading URM
    URM = createURM()

    URM_train_init, URM_test = split_train_in_two_percentage_global_sample(URM, train_percentage=0.85)


    # ---------------------------------------------------------------------------------------------------------
    # Creating CSV header

    header = ['recommender', 'TopK', 'Epochs', 'lambda_i', 'lambda_j', 'MAP']

    partialsFile = 'SlimBPR_' + datetime.now().strftime('%b%d_%H-%M-%S')

    with open('partials/' + partialsFile + '.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)


    # ---------------------------------------------------------------------------------------------------------
    # Profiling

    group_id = 0

    profile_length = np.ediff1d(URM_train_init.indptr)
    sorted_users = np.argsort(profile_length)

    interactions = []
    for i in range(41629):
        interactions.append(len(URM_train_init[i, :].nonzero()[0]))

    list_group_interactions = [[0, 20], [21, 49], [50, max(interactions)]]

    lower_bound = list_group_interactions[group_id][0]
    higher_bound = list_group_interactions[group_id][1]

    users_in_group = [user_id for user_id in range(len(interactions))
                      if (lower_bound <= interactions[user_id] <= higher_bound)]
    users_in_group_p_len = profile_length[users_in_group]

    users_not_in_group_flag = np.isin(sorted_users, users_in_group, invert=True)
    users_not_in_group = sorted_users[users_not_in_group_flag]

    # ---------------------------------------------------------------------------------------------------------
    # K-Fold Cross Validation + Preparing training, validation, test split and evaluator

    URM_train_list = []
    URM_validation_list = []
    users_not_in_group_list = []

    for k in range(3):
        URM_train, URM_validation = split_train_in_two_percentage_global_sample(URM_train_init, train_percentage=0.85)
        URM_train_list.append(URM_train)
        URM_validation_list.append(URM_validation)

        profile_length = np.ediff1d(URM_train_init.indptr)
        sorted_users = np.argsort(profile_length)

        users_in_group = [user_id for user_id in range(len(interactions))
                          if (lower_bound <= interactions[user_id] <= higher_bound)]
        users_in_group_p_len = profile_length[users_in_group]

        users_not_in_group_flag = np.isin(sorted_users, users_in_group, invert=True)
        users_not_in_group_list.append(sorted_users[users_not_in_group_flag])

    evaluator_validation = K_Fold_Evaluator_MAP(URM_validation_list, cutoff_list=[10], verbose=False,
                                                ignore_users_list=users_not_in_group_list)
    MAP_results_list = []


    # ---------------------------------------------------------------------------------------------------------
    # Optuna hyperparameter model

    search_space = {
        'topK': [100, 500],
        'epochs': [10, 100],
        'lambda_i': [0.004, 0.005],
        'lambda_j': [0.003, 0.005]
    }

    def objective(trial):

        recommender_SlimBPR_list = []

        topK = trial.suggest_int("topK", 100, 500)
        epochs = trial.suggest_int("epochs", 10, 100)
        lambda_i = trial.suggest_float("lambda_i", 0.004, 0.005)
        lambda_j = trial.suggest_float("lambda_j", 0.003, 0.005)

        for index in range(len(URM_train_list)):
            recommender_SlimBPR_list.append(SLIM_BPR_Cython(URM_train_list[index], verbose=False))
            recommender_SlimBPR_list[index].fit(topK=topK, epochs=epochs, lambda_j=lambda_j, lambda_i=lambda_i)

        MAP_result = evaluator_validation.evaluateRecommender(recommender_SlimBPR_list)
        MAP_results_list.append(MAP_result)

        resultsToPrint = [recommender_SlimBPR_list[0].RECOMMENDER_NAME, topK, epochs, lambda_i, lambda_j, sum(MAP_result) / len(MAP_result)]

        with open('partials/' + partialsFile + '.csv', 'a+', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(resultsToPrint)

        return sum(MAP_result) / len(MAP_result)

    study = op.create_study(direction='maximize', sampler=GridSampler(search_space))
    study.optimize(objective, n_trials=50)

    # ---------------------------------------------------------------------------------------------------------
    # Fitting and testing to get local MAP

    topK = study.best_params['topK']
    epochs = study.best_params['epochs']
    lambda_i = study.best_params['lambda_i']
    lambda_j = study.best_params['lambda_j']

    recommender_SlimBPR = SLIM_BPR_Cython(URM_train_init, verbose=False)
    recommender_SlimBPR.fit(topK=topK, epochs=epochs, lambda_j=lambda_j, lambda_i=lambda_i)

    evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[10], ignore_users=users_not_in_group)
    result_dict, _ = evaluator_test.evaluateRecommender(recommender_SlimBPR)

    # ---------------------------------------------------------------------------------------------------------
    # Writing hyperparameter into a log

    resultParameters = result_dict.to_json(orient="records")
    parsed = json.loads(resultParameters)

    with open("logs/" + recommender_SlimBPR.RECOMMENDER_NAME + "_logs_" + datetime.now().strftime(
            '%b%d_%H-%M-%S') + ".json", 'w') as json_file:
        json.dump(study.best_params, json_file, indent=4)
        json.dump(parsed, json_file, indent=4)