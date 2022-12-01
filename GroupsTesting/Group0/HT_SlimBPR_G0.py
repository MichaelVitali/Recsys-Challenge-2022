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

    # ---------------------------------------------------------------------------------------------------------
    # Loading URM
    URM = createURM()

    # ---------------------------------------------------------------------------------------------------------
    # Creating CSV header

    header = ['recommender', 'topK', 'epochs', 'lambda_i', 'lambda_j', 'MAP']

    partialsFile = 'SlimBPR_' + datetime.now().strftime('%b%d_%H-%M-%S')

    with open('partials/' + partialsFile + '.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

    # ---------------------------------------------------------------------------------------------------------
    # Profiling

    group_id = 0

    profile_length = np.ediff1d(URM.indptr)

    block_size = int(len(profile_length) * 0.25)

    sorted_users = np.argsort(profile_length)

    start_pos = group_id * block_size
    end_pos = min((group_id + 1) * block_size, len(profile_length))

    users_in_group = sorted_users[start_pos:end_pos]

    users_in_group_p_len = profile_length[users_in_group]

    users_not_in_group_flag = np.isin(sorted_users, users_in_group, invert=True)
    users_not_in_group = sorted_users[users_not_in_group_flag]

    # ---------------------------------------------------------------------------------------------------------
    # K-Fold Cross Validation + Preparing training, validation, test split and evaluator

    URM_train_init, URM_test = split_train_in_two_percentage_global_sample(URM, train_percentage=0.85)

    URM_train_list = []
    URM_validation_list = []

    for k in range(3):
        URM_train, URM_validation = split_train_in_two_percentage_global_sample(URM_train_init, train_percentage=0.85)
        URM_train_list.append(URM_train)
        URM_validation_list.append(URM_validation)

    evaluator_validation = K_Fold_Evaluator_MAP(URM_validation_list, cutoff_list=[10], verbose=False, ignore_users_list=users_not_in_group)

    MAP_results_list = []


    # ---------------------------------------------------------------------------------------------------------
    # Optuna hyperparameter model

    def objective(trial):

        recommender_SlimBPR_list = []

        topK = trial.suggest_int("topK", 5, 5000)
        epochs = trial.suggest_int("epochs", 10, 100)
        lambda_i = trial.suggest_float("lambda_i", 1e-5, 1e-2)
        lambda_j = trial.suggest_float("lambda_j", 1e-5, 1e-2)

        for index in range(len(URM_train_list)):

            recommender_SlimBPR_list.append(SLIM_BPR_Cython(URM_train_list[index], verbose=False))
            recommender_SlimBPR_list[index].fit(topK=topK, epochs=epochs, lambda_j=lambda_j, lambda_i=lambda_i)
            recommender_SlimBPR_list[index].URM_Train = URM_train_list[index]

        MAP_result = evaluator_validation.evaluateRecommender(recommender_SlimBPR_list)
        MAP_results_list.append(MAP_result)

        resultsToPrint = [recommender_SlimBPR_list[0].RECOMMENDER_NAME, topK, epochs, lambda_i, lambda_j,sum(MAP_result) / len(MAP_result)]

        with open('partials/' + partialsFile + '.csv', 'a+', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(resultsToPrint)

        return sum(MAP_result) / len(MAP_result)


    study = op.create_study(direction='maximize')
    study.optimize(objective, n_trials=50)

    # ---------------------------------------------------------------------------------------------------------
    # Fitting and testing to get local MAP

    topK = study.best_params["topK"]
    epochs = study.best_params["epochs"]
    lambda_i = study.best_params["lambda_i"]
    lambda_j = study.best_params["lambda_j"]

    recommender_SlimBPR = SLIM_BPR_Cython(URM_train=URM_train_init, verbose=False)
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