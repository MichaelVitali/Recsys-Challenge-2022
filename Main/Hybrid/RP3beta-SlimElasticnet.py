if __name__ == '__main__':

    from Utils.recsys2022DataReader import createURMBinary
    from Recommenders.SLIM.SLIMElasticNetRecommender import SLIMElasticNetRecommender
    from Recommenders.GraphBased.RP3betaRecommender import RP3betaRecommender
    from Recommenders.Hybrid.LinearHybridRecommender import LinearHybridTwoRecommenderTwoVariables
    from Utils.writeSubmission import write_submission

    # Loading URM
    URM = createURMBinary()


    rec1 = RP3betaRecommender(URM)
    rec1.fit(alpha=0.8401946814961014, beta=0.3073181471251768, topK=77)

    rec2 = SLIMElasticNetRecommender(URM)
    rec2.fit(topK=250, alpha=0.00312082198837027, l1_ratio=0.009899185175306373)

    recommender_Hybrid = LinearHybridTwoRecommenderTwoVariables(URM_train=URM, Recommender_1=rec1,
                                                                Recommender_2=rec2)
    recommender_Hybrid.fit(alpha=0.4133522121773261, beta=0.7451419993321209)


    # Write the submission file
    write_submission(recommender=recommender_Hybrid,
                     target_users_path="../../Input/data_target_users_test.csv",
                     out_path='../../Output/{}_submission.csv'.format('SlimRP3_0401'))