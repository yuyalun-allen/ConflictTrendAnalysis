import pickle

import numpy as np
from tslearn.clustering import TimeSeriesKMeans
from tslearn.preprocessing import TimeSeriesResampler


def cluster_trends(trend_path, cluster_num):
    with open(trend_path, 'rb') as f:
        conflict_trends = pickle.load(f)

    lines = []
    for c in conflict_trends:
        lines.append(c['counts'])

    max_inter_length = max_length(lines)
    lines = TimeSeriesResampler(sz=max_inter_length).fit_transform(lines)

    kmeans = TimeSeriesKMeans(n_clusters=cluster_num, metric="softdtw", n_jobs=-1)
    labels = kmeans.fit_predict(lines)

    cluster_dict = {}
    for index, label in enumerate(labels):
        label = label.item()
        if label not in cluster_dict:
            cluster_dict[label] = []
        cluster_dict[label].append(index)
    
    with open(f'cluster/rails_cluster_dict.pkl', 'wb') as f:
        pickle.dump(cluster_dict, f)



def max_length(lines):
    return max([len(line) for line in lines])

cluster_trends('trends/rails_x_axis_datetime.pkl', 9)

