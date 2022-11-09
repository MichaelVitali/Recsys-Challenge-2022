if __name__ == '__main__':

    from Recommenders.SLIM.Cython.SLIM_BPR_Cython import SLIM_BPR_Cython
    from Utils.createURM import createBumpURM
    from Utils.writeSubmission import write_submission
    import pandas as pd

    dataset = pd.read_csv('../Input/interactions_and_impressions.csv')
    URM = createBumpURM(dataset)

    recommender = SLIM_BPR_Cython(URM)
    recommender.fit(epochs=75, topK=45, lambda_i=1e-05, lambda_j=1e-05)

    write_submission(recommender=recommender,
                     target_users_path="../Input/data_target_users_test.csv",
                     out_path='../Output/{}_submission.csv'.format('SLIMBPR'))