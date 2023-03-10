if __name__ == '__main__':

    from Utils.recsys2022DataReader import createBumpURM
    from Utils.writeSubmission import write_submission
    from Recommenders.KNN.ItemKNNCBFRecommender import  ItemKNNCBFRecommender

    URM = createBumpURM()

    recommender = ItemKNNCBFRecommender(URM)
    # BEST recommender.fit(shrink = 10, topk = 25)
    recommender.fit(shrink = 24.453692628426108, topK = int(22.601403333483844))

    write_submission(recommender=recommender,
                     target_users_path="../Input/data_target_users_test.csv",
                     out_path='../Output/{}_submission.csv'.format('ItemKNNCBF'))