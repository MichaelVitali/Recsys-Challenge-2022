if __name__ == "__main__":
    from Recommenders.GraphBased.RP3betaRecommender import RP3betaRecommender
    from Recommenders.KNN.ItemKNNCFRecommenderPLUS import ItemKNNCFRecommender
    from Recommenders.SLIM.SLIMElasticNetRecommender import SLIMElasticNetRecommender
    from Evaluation.K_Fold_Evaluator import K_Fold_Evaluator_MAP
    from Recommenders.Hybrid.LinearHybridRecommender import LinearHybridTwoRecommenderTwoVariables
    from Evaluation.Evaluator import EvaluatorHoldout
    from Utils.recsys2022DataReader import *
    import numpy as np
    import csv
    from datetime import datetime
    import optuna as op
    import json
    from optuna.samplers import RandomSampler

    # ---------------------------------------------------------------------------------------------------------
    # Creating CSV header

    header = ['recommender', 'alpha', 'beta' 'MAP']

    partialsFile = 'SLIM_RP3beta_ItemKNNCF' + datetime.now().strftime('%b%d_%H-%M-%S')

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
    ICM = createSmallICM()

    evaluator_validation = K_Fold_Evaluator_MAP(URM_validation_list, cutoff_list=[10], verbose=False)

    # ---------------------------------------------------------------------------------------------------------
    # Profiling

    group_id = 1

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

    users_not_in_group_list = []

    for k in range(3):
        profile_length = np.ediff1d(URM_train_list[k].indptr)
        sorted_users = np.argsort(profile_length)

        users_in_group = [user_id for user_id in range(len(interactions))
                          if (lower_bound <= interactions[user_id] <= higher_bound)]
        users_in_group_p_len = profile_length[users_in_group]

        users_not_in_group_flag = np.isin(sorted_users, users_in_group, invert=True)
        users_not_in_group_list.append(sorted_users[users_not_in_group_flag])

    evaluator_validation = K_Fold_Evaluator_MAP(URM_validation_list, cutoff_list=[10], verbose=False,
                                                ignore_users_list=users_not_in_group_list)

    # ---------------------------------------------------------------------------------------------------------
    # Optuna hyperparameter model

    recommender_RP3beta_list = []
    recommender_ItemKNN_list = []
    recommender_hybrid_RP3beta_ItemKNN_list = []
    recommender_SLIM_list = []
    MAP_results_list = []

    for index in range(len(URM_train_list)):

        #Fit RP3beta-ItemKNN hybrid
        recommender_RP3beta_list.append(RP3betaRecommender(URM_train_list[index], verbose=False))
        recommender_RP3beta_list[index].fit(alpha=0.7849910963981444, beta=0.3219406144420833, topK=64)

        recommender_ItemKNN_list.append(ItemKNNCFRecommender(URM_train_list[index], verbose=False))
        recommender_ItemKNN_list[index].fit(ICM=ICM, topK=377, shrink=10, similarity='rp3beta', normalization='tfidf')

        recommender_hybrid_RP3beta_ItemKNN_list.append(LinearHybridTwoRecommenderTwoVariables(URM_train_list[index], Recommender_1=recommender_RP3beta_list[index], Recommender_2=recommender_ItemKNN_list[index]))
        recommender_hybrid_RP3beta_ItemKNN_list[index].fit(alpha=0.6745409371119246, beta=0.19918230600969603)

        #Fit SLIMElasticnet
        recommender_SLIM_list.append(SLIMElasticNetRecommender(URM_train_list[index]))
        recommender_SLIM_list[index].fit(topK=258, alpha=0.035237980092119314, l1_ratio=0.05512644878845981)

    def objective(trial):

        recommender_hybrid_list = []

        alpha = trial.suggest_float("alpha", 0, 1)
        beta = trial.suggest_float("beta", 0, 1)

        for index in range(len(URM_train_list)):

            recommender_hybrid_list.append(LinearHybridTwoRecommenderTwoVariables(URM_train_list[index], Recommender_1=recommender_hybrid_RP3beta_ItemKNN_list[index], Recommender_2=recommender_SLIM_list[index]))
            recommender_hybrid_list[index].fit(alpha=alpha, beta=beta)

        MAP_result = evaluator_validation.evaluateRecommender(recommender_hybrid_list)
        MAP_results_list.append(MAP_result)

        resultsToPrint = ["Slim_RP3beta_ItemKNNCF", alpha, beta, sum(MAP_result) / len(MAP_result)]

        with open('partials/' + partialsFile + '.csv', 'a+', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(resultsToPrint)

        return sum(MAP_result) / len(MAP_result)


    study = op.create_study(direction='maximize')
    study.optimize(objective, n_trials=200)

    # ---------------------------------------------------------------------------------------------------------
    # Fitting and testing to get local MAP

    alpha = study.best_params['alpha']
    beta = study.best_params['beta']

    recommender_RP3beta = RP3betaRecommender(URM_train_init, verbose=False)
    recommender_RP3beta.fit(alpha=0.8815611011233834, beta=0.23472570066237713, topK=225)

    recommender_ItemKNN = ItemKNNCFRecommender(URM_train_init, verbose=False)
    recommender_ItemKNN.fit(ICM=ICM, topK=1296, shrink=51, similarity='rp3beta', normalization='tfidf')

    recommender_hybrid_RP3beta_ItemKNN = LinearHybridTwoRecommenderTwoVariables(URM_train_init, Recommender_1=recommender_RP3beta, Recommender_2=recommender_ItemKNN)
    recommender_hybrid_RP3beta_ItemKNN.fit(alpha=0.8190677327782062, beta=0.686509249107007)

    recommender_SLIM = SLIMElasticNetRecommender(URM_train_init, verbose=False)
    recommender_SLIM.fit(topK=299, alpha=0.057940560184114316, l1_ratio=0.06563962491123715)

    recommender_hybrid = LinearHybridTwoRecommenderTwoVariables(URM_train=URM_train_init, Recommender_1=recommender_hybrid_RP3beta_ItemKNN, Recommender_2=recommender_SLIM)
    recommender_hybrid.fit(alpha=alpha, beta=beta)

    evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[10], ignore_users=users_not_in_group)
    result_dict, _ = evaluator_test.evaluateRecommender(recommender_hybrid)

    # ---------------------------------------------------------------------------------------------------------
    # Writing hyperparameter into a log

    resultParameters = result_dict.to_json(orient="records")
    parsed = json.loads(resultParameters)

    with open("logs/" + "SLIM_RP3beta_ItemKNNCF" + "_logs_" + datetime.now().strftime(
            '%b%d_%H-%M-%S') + ".json", 'w') as json_file:
        json.dump(study.best_params, json_file, indent=4)
        json.dump(parsed, json_file, indent=4)

