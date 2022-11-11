import pandas as pd
import scipy.sparse as sp
import numpy as np

# path are:
# - ../../Input/ if run from notebooks
# - ../../../Input/ if run from python file

urmPath = "../../Input/interactions_and_impressions.csv"
icmTypePath = "../../Input/data_ICM_type.csv"
icmLenghtPath = "../../Input/data_ICM_length.csv"
targetUserPath = "../../Input/data_target_users_test.csv"

def createBumpURM():

    dataset = pd.read_csv(urmPath)

    dataset = dataset.drop(columns=['Impressions'])

    datasetCOO = sp.coo_matrix((dataset["Data"].values, (dataset["UserID"].values, dataset["ItemID"].values)))
    userIDS = dataset['UserID'].unique()
    itemIDS = dataset['ItemID'].unique()

    URM = np.zeros((len(userIDS), len(itemIDS)), dtype=int)
    for x in range(len(datasetCOO.data)):
        if datasetCOO.data[x] == 0:
            URM[datasetCOO.row[x]][datasetCOO.col[x]] = int(5)
        elif datasetCOO.data[x] == 1 and URM[datasetCOO.row[x]][datasetCOO.col[x]] < 4:
            URM[datasetCOO.row[x]][datasetCOO.col[x]] = URM[datasetCOO.row[x]][datasetCOO.col[x]] + 1

    URM = sp.csr_matrix(URM)

    return URM


def createNormalURM():
    dataset = pd.read_csv(urmPath)
    dataset = dataset.drop(columns=['Impressions'])

    datasetCOO = sp.coo_matrix((dataset["Data"].values, (dataset["UserID"].values, dataset["ItemID"].values)))
    userIDS = dataset['UserID'].unique()
    itemIDS = dataset['ItemID'].unique()

    URM = np.zeros((len(userIDS), len(itemIDS)), dtype=int)
    for x in range(len(datasetCOO.data)):
        if datasetCOO.data[x] == 0:
            URM[datasetCOO.row[x]][datasetCOO.col[x]] = int(5)
        elif URM[datasetCOO.row[x]][datasetCOO.col[x]] != int(5) and datasetCOO.data[x] == 1:
            URM[datasetCOO.row[x]][datasetCOO.col[x]] = int(1)

    URM = sp.csr_matrix(URM)

    return URM

def createSmallICM():

    types = pd.read_csv(icmTypePath)
    lenght = pd.read_csv(icmLenghtPath)

    types = types.drop(columns=['data'], axis=1)
    types = types.rename(columns={'feature_id': 'type'})

    typesFiltered = types[types['item_id'] <= 24506]
    typesArray = typesFiltered['type'].to_numpy()
    itemsID = typesFiltered['item_id'].to_numpy()

    ICM = np.zeros((24507, 2), dtype=int)

    for x in range(len(itemsID)):
        ICM[itemsID[x]][0] = typesArray[x]

    lenght = lenght.drop(columns=['feature_id'], axis=1)
    lenght = lenght.rename(columns={'data': 'numberOfEpisodes'})

    lenghtFiltered = lenght[lenght['item_id'] <= 24506]
    lenghtArray = lenghtFiltered['numberOfEpisodes'].to_numpy()
    itemsID = typesFiltered['item_id'].to_numpy()

    for x in range(len(itemsID)):
        ICM[itemsID[x]][1] = lenghtArray[x]

    ICM = sp.csr_matrix(ICM)

    return ICM


def createBigICM():

    types = pd.read_csv(icmTypePath)
    lenght = pd.read_csv(icmLenghtPath)

    types = types.drop(columns=['data'], axis=1)
    types = types.rename(columns={'feature_id': 'type'})

    typesArray = types['type'].to_numpy()
    itemsID = types['item_id'].to_numpy()


    ICM = np.zeros((27968, 2), dtype=int)

    for x in range(len(itemsID)):
        ICM[itemsID[x]][0] = typesArray[x]


    lenght = lenght.drop(columns=['feature_id'], axis=1)
    lenght = lenght.rename(columns={'data': 'numberOfEpisodes'})

    lenghtArray = lenght['numberOfEpisodes'].to_numpy()

    for x in range(len(itemsID)):
        ICM[itemsID[x]][1] = lenghtArray[x]

    ICM = sp.csr_matrix(ICM)

    return ICM

def combineURM_ICM():

    URM = createBumpURM()

    ICM = createSmallICM()

    combinedURMICM = sp.vstack(URM, ICM.T)

    return combinedURMICM