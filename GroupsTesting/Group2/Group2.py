if __name__ == "__main__":

    import scipy.sparse as sp
    from Data_manager.split_functions.split_train_validation_random_holdout import \
        split_train_in_two_percentage_global_sample
    from Utils.recsys2022DataReader import *
    from Recommenders.Implicit.ImplicitALSRecommender import ImplicitALSRecommender
    from Recommenders.SLIM.SLIM_BPR_Python import SLIM_BPR_Python
    from Recommenders.KNN.ItemKNNCFRecommenderPLUS import ItemKNNCFRecommender
    from Recommenders.SLIM.SLIMElasticNetRecommender import MultiThreadSLIM_SLIMElasticNetRecommender
    from Recommenders.GraphBased.P3alphaRecommender import P3alphaRecommender
    from Recommenders.GraphBased.RP3betaRecommender import RP3betaRecommender
    from Recommenders.Hybrid.LinearHybridRecommender import LinearHybridTwoRecommenderTwoVariables
    import matplotlib.pyplot as plt
    from Evaluation.Evaluator import EvaluatorHoldout

    # ---------------------------------------------------------------------------------------------------------
    # Loading URM + ICM

    URM = createURM()

    ICM = createSmallICM()

    # ---------------------------------------------------------------------------------------------------------
    # Preparing training, validation, test split and evaluator

    URM_train, URM_test = split_train_in_two_percentage_global_sample(URM, train_percentage=0.85)

    # ---------------------------------------------------------------------------------------------------------
    # Fitting of recommenders

    recommender_object_dict = {}

    # IALS
    IASL = ImplicitALSRecommender(URM_train)
    IASL.fit(iterations=96, factors=320, alpha=10, regularization=0.001)
    recommender_object_dict['IALS'] = IASL

    # SLIM BPR
    SlimBPR = SLIM_BPR_Python(URM_train)
    SlimBPR.fit(topK=45, epochs=75, lambda_j=1e-05, lambda_i=1e-05)
    recommender_object_dict['SlimBPR'] = SlimBPR
    """
    # SLIM Elastic Net
    SlimElasticNet = MultiThreadSLIM_SLIMElasticNetRecommender(URM_train)
    SlimElasticNet.fit(topK=359, alpha=0.04183472018614359, l1_ratio=0.03260349571135893)
    recommender_object_dict['SLIM Elastic Net'] = SlimElasticNet"""

    # ItemKNNCF
    ItemKNNCFG2 = ItemKNNCFRecommender(URM_train)
    ItemKNNCFG2.fit(ICM, shrink=10.253981267190092, topK=390, similarity='rp3beta',
                    normalization='tfidf')
    recommender_object_dict['CombinedItemKNNCFG2'] = ItemKNNCFG2

    # RP3beta
    RP3betaG2 = RP3betaRecommender(URM_train)
    RP3betaG2.fit(alpha=0.748706443270007, beta=0.16081149387492433, topK=370)
    recommender_object_dict['RP3betaG2'] = RP3betaG2

    # ---------------------------------------------------------------------------------------------------------
    # Evaluation of recommenders based on group

    MAP_recommender_per_group = {}

    group_id = 2

    cutoff = 10

    profile_length = np.ediff1d(URM.indptr)

    block_size = int(len(profile_length) * 0.25)

    sorted_users = np.argsort(profile_length)

    start_pos = group_id * block_size
    end_pos = min((group_id + 1) * block_size, len(profile_length))

    users_in_group = sorted_users[start_pos:end_pos]

    users_in_group_p_len = profile_length[users_in_group]

    users_not_in_group_flag = np.isin(sorted_users, users_in_group, invert=True)
    users_not_in_group = sorted_users[users_not_in_group_flag]

    evaluator_test = EvaluatorHoldout(URM_test, cutoff_list=[cutoff], ignore_users=users_not_in_group)

    for label, recommender in recommender_object_dict.items():
        result_df, _ = evaluator_test.evaluateRecommender(recommender)
        if label in MAP_recommender_per_group:
            MAP_recommender_per_group[label].append(result_df.loc[cutoff]["MAP"])
        else:
            MAP_recommender_per_group[label] = [result_df.loc[cutoff]["MAP"]]

    # ---------------------------------------------------------------------------------------------------------
    # Plot

    _ = plt.figure(figsize=(16, 9))
    for label, recommender in recommender_object_dict.items():
        results = MAP_recommender_per_group[label]
        plt.scatter(x=label, y=results, label=label)
    plt.title('User Group 0')
    plt.ylabel('MAP')
    plt.xlabel('Recommenders')
    plt.legend()
    plt.show()

