if __name__ == '__main__':

    from Evaluation.Evaluator import EvaluatorHoldout
    from Evaluation.K_Fold_Evaluator import K_Fold_Evaluator_MAP
    from datetime import datetime
    from Utils.recsys2022DataReader import *
    from Recommenders.GraphBased.RP3betaRecommender import RP3betaRecommender
    import optuna as op
    import json
    import csv

    # ---------------------------------------------------------------------------------------------------------
    # Creating CSV header

    header = ['recommender', 'alpha', 'beta', 'TopK', 'MAP']

    partialsFile = 'RP3beta_Normal' + datetime.now().strftime('%b%d_%H-%M-%S')

    with open('partials/' + partialsFile + '.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

    # ---------------------------------------------------------------------------------------------------------
    # Loading URMs
    URM_train_init = load_URMTrainInit()
    URM_train_list = load_K_URMTrain()
    URM_validation_list = load_K_URMValid()
    URM_test = load_URMTest()

    evaluator_validation = K_Fold_Evaluator_MAP(URM_validation_list, cutoff_list=[10], verbose=False)

    # ---------------------------------------------------------------------------------------------------------
    # Optuna hyperparameter model

    def objective(trial):

        recommender_RP3beta_list = []

        alpha = trial.suggest_float("alpha", 0.1, 0.9)
        beta = trial.suggest_float("beta", 0.1, 0.9)
        topK = trial.suggest_int("topK", 100, 1000)

        for index in range(len(URM_train_list)):

            recommender_RP3beta_list.append(RP3betaRecommender(URM_train_list[index], verbose=False))
            recommender_RP3beta_list[index].fit(alpha=alpha, topK=topK, beta=beta)


        MAP_result = evaluator_validation.evaluateRecommender(recommender_RP3beta_list)

        resultsToPrint = [recommender_RP3beta_list[0].RECOMMENDER_NAME, alpha, beta, topK, sum(MAP_result) / len(MAP_result)]

        with open('partials/' + partialsFile + '.csv', 'a+', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(resultsToPrint)

        return sum(MAP_result) / len(MAP_result)


    study = op.create_study(direction='maximize')
    study.optimize(objective, n_trials=200)

    # ---------------------------------------------------------------------------------------------------------
    # Fitting and testing to get local MAP

    topK = study.best_params['topK']
    alpha = study.best_params['alpha']
    beta = study.best_params['beta']

    recommender_RP3beta = RP3betaRecommender(URM_train_init, verbose=False)
    recommender_RP3beta.fit(alpha=alpha, topK=topK, beta=beta)

    evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[10])
    result_dict, _ = evaluator_test.evaluateRecommender(recommender_RP3beta)

    # ---------------------------------------------------------------------------------------------------------
    # Writing hyperparameter into a log

    resultParameters = result_dict.to_json(orient="records")
    parsed = json.loads(resultParameters)

    with open("logs/" + recommender_RP3beta.RECOMMENDER_NAME + "_Normal_logs_" + datetime.now().strftime(
            '%b%d_%H-%M-%S') + ".json", 'w') as json_file:
        json.dump(study.best_params, json_file, indent=4)
        json.dump(parsed, json_file, indent=4)