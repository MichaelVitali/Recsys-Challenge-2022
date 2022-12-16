if __name__ == '__main__':

    from Evaluation.Evaluator import EvaluatorHoldout
    from Evaluation.K_Fold_Evaluator import K_Fold_Evaluator_MAP
    from datetime import datetime
    from Utils.recsys2022DataReader import createURM
    from Data_manager.split_functions.split_train_validation_random_holdout import split_train_in_two_percentage_global_sample
    from Recommenders.SLIM.SLIMElasticNetRecommender import MultiThreadSLIM_SLIMElasticNetRecommender
    from Recommenders.GraphBased.RP3betaRecommender import RP3betaRecommender
    from Recommenders.Hybrid.LinearHybridRecommender import LinearHybridTwoRecommenderOneVariable
    import optuna as op
    import json
    import csv
    from optuna.samplers import RandomSampler


    # ---------------------------------------------------------------------------------------------------------
    # Loading URM

    URM = createURM()

    # ---------------------------------------------------------------------------------------------------------
    # Creating CSV header

    header = ['recommender', 'alpha', 'MAP']

    partialsFile = 'SlimRP3Beta_' + datetime.now().strftime('%b%d_%H-%M-%S')

    with open('partials/' + partialsFile + '.csv', 'w', encoding='UTF8') as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

    # ---------------------------------------------------------------------------------------------------------
    # K-Fold Cross Validation + Preparing training, validation, test split and evaluator

    URM_train_init, URM_test = split_train_in_two_percentage_global_sample(URM, train_percentage=0.85)

    URM_train_list = []
    URM_validation_list = []

    for k in range(3):
        URM_train, URM_validation = split_train_in_two_percentage_global_sample(URM_train_init, train_percentage=0.85)
        URM_train_list.append(URM_train)
        URM_validation_list.append(URM_validation)

    evaluator_validation = K_Fold_Evaluator_MAP(URM_validation_list, cutoff_list=[10], verbose=False)

    MAP_results_list = []
    # ---------------------------------------------------------------------------------------------------------
    # Optuna hyperparameter model

    recommender_SlimElasticnet_list = []
    recommender_RP3beta_list = []

    for index in range(len(URM_train_list)):

        recommender_SlimElasticnet_list.append(MultiThreadSLIM_SLIMElasticNetRecommender(URM_train_list[index]))
        recommender_SlimElasticnet_list[index].fit(topK=490, alpha=0.046206433888392476, l1_ratio=0.01823482143832622)

        recommender_RP3beta_list.append(RP3betaRecommender(URM_train_list[index]))
        recommender_RP3beta_list[index].fit(alpha=0.7136052911660057, beta=0.44828831909194655, topK=54)

    def objective(trial):

        recommender_Hybrid_list = []

        alpha = trial.suggest_float("alpha", 0, 1)

        for index in range(len(URM_train_list)):

            recommender_Hybrid_list.append(LinearHybridTwoRecommenderOneVariable(URM_train=URM_train_list[index], Recommender_1=recommender_SlimElasticnet_list[index], Recommender_2=recommender_RP3beta_list[index]))
            recommender_Hybrid_list[index].fit(alpha=alpha)

        MAP_result = evaluator_validation.evaluateRecommender(recommender_Hybrid_list)
        MAP_results_list.append(MAP_result)

        resultsToPrint = ['SlimRP3Beta', alpha,
                          sum(MAP_result) / len(MAP_result)]

        with open('partials/' + partialsFile + '.csv', 'a+', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(resultsToPrint)

        return sum(MAP_result) / len(MAP_result)


    study = op.create_study(direction='maximize', sampler=RandomSampler())
    study.optimize(objective, n_trials=50)

    # ---------------------------------------------------------------------------------------------------------
    # Fitting and testing to get local MAP

    alpha = study.best_params['alpha']

    recommender_Slim_Elasticnet = MultiThreadSLIM_SLIMElasticNetRecommender(URM_train_init)
    recommender_Slim_Elasticnet.fit(topK=490, alpha=0.046206433888392476, l1_ratio=0.01823482143832622)

    recommender_RP3beta = RP3betaRecommender(URM_train_init)
    recommender_RP3beta.fit(alpha=0.7136052911660057, beta=0.44828831909194655, topK=54)

    recommender_Hybrid = LinearHybridTwoRecommenderOneVariable(URM_train=URM_train_init, Recommender_1=recommender_Slim_Elasticnet, Recommender_2=recommender_RP3beta)
    recommender_Hybrid.fit(alpha=alpha)

    evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[10])
    result_dict, _ = evaluator_test.evaluateRecommender(recommender_Hybrid)

    # ---------------------------------------------------------------------------------------------------------
    # Writing hyperparameter into a log

    resultParameters = result_dict.to_json(orient="records")
    parsed = json.loads(resultParameters)

    with open("logs/" + recommender_Hybrid.RECOMMENDER_NAME + "_logs_" + datetime.now().strftime(
            '%b%d_%H-%M-%S') + ".json", 'w') as json_file:
        json.dump(study.best_params, json_file, indent=4)
        json.dump(parsed, json_file, indent=4)