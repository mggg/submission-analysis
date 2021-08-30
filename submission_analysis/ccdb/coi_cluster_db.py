import pandas
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform
from scipy.optimize import linear_sum_assignment
import numpy as np
import networkx as nx
import json
import matplotlib.pyplot as plt
from pathos.multiprocessing import ProcessPool as Pool
from ast import literal_eval
import pickle
import sys
import os
import tqdm
import copy
import warnings


def matching_distance_between_maps(map_a, map_b, geoid_to_id,
                                   distances_matrix):
    # Make map_a the map with more units
    if len(map_a) < len(map_b):
        map_c = map_b
        map_b = map_a
        map_a = map_c
    # Remove common units from A and B
    common_units = map_a & map_b
    reduced_map_a = map_a - common_units
    reduced_map_b = map_b - common_units
    if len(reduced_map_a) == 0:
        return 0

    infinity_standin = distances_matrix.shape[0] + 1
    # Copy the relevant subset of the distances
    # as a cost matrix
    num_rows = len(reduced_map_a)
    num_cols = len(reduced_map_b)
    row_ids = [geoid_to_id[geo_unit] for geo_unit in reduced_map_a]
    col_ids = [geoid_to_id[geo_unit] for geo_unit in reduced_map_b]
    cost_matrix = np.zeros((num_rows, num_rows))
    cost_matrix[:, 0:num_cols] = distances_matrix[:, col_ids][row_ids, :]
    row_maxes = cost_matrix.max(axis=1)
    big_max = row_maxes.sum()
    if num_rows > num_cols:
        cost_matrix[:, (num_cols + 1):(num_rows)] = big_max

    # Do an initial lowest cost matching from the units of the
    # larger map to the units of the smaller map
    #
    # If one of the maps is substantially larger the matching takes a long
    # time, so just skip the matching step as it's not exceptionally useful
    if num_rows - num_cols <= 50:
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        rows_that_were_matched = row_ind[col_ind < num_cols]
        rows_that_were_not_matched = row_ind[col_ind >= num_cols]
        cols_that_were_matched = col_ind[col_ind < num_cols]
        match_cost = cost_matrix[rows_that_were_matched,
                                 cols_that_were_matched].sum()
    else:
        match_cost = 0
        rows_that_were_not_matched = range(num_rows)

    # If the two maps have units in different graph components
    # it's possible to get an "infinite" distance between them
    if match_cost >= infinity_standin:
        return np.Infinity

    # Whatever remains, add cost equal to an average path
    unmatched_unit_ids = np.asarray(row_ids)[rows_that_were_not_matched]
    ids_in_map_b = [geoid_to_id[geo_unit] for geo_unit in map_b]
    for unit_id in unmatched_unit_ids:
        match_cost = match_cost + np.mean(distances_matrix[unit_id,
                                                           ids_in_map_b])

    return (match_cost / (num_rows + len(common_units)))


def avg_hausdorff_distance_between_maps(map_a, map_b, distances_matrix):
    # Copy the relevant subset of the distances
    # as a cost matrix
    num_rows = len(map_a)
    num_cols = len(map_b)
    if num_rows == 0 or num_cols == 0:
        return np.Infinity
    cost_matrix = distances_matrix[:, map_b][map_a, :]
    dij = cost_matrix.min(axis=0).mean()
    dji = cost_matrix.min(axis=1).mean()

    return (max(dij, dji))


def avg_hausdorff_distance_one_map(map_b, distances_matrix):
    # Copy the relevant subset of the distances
    # as a cost matrix
    if len(map_b) == 0:
        return np.Infinity
    cost_matrix = distances_matrix[:, map_b]
    dij = cost_matrix.min(axis=0).mean()
    dji = cost_matrix.min(axis=1).mean()

    return (max(dij, dji))


def mp_compute_distance_wrapper(data, dists, row_num):
    max_index = data.shape[0]
    output = []
    for j in range(row_num + 1, max_index):
        second_map_plan = data[j, :]
        #output.append(((row_num,j),matching_distance_between_maps(first_map_plan,second_map_plan,geo,dist_mat)))
        output.append(((row_num, j),
                       avg_hausdorff_distance_one_map(second_map_plan, dists)))
    return output


class coi_cluster_database(object):
    def __init__(self,
                 graph_file_name,
                 lookup_table_file_name,
                 number_of_cpus=1,
                 key_name="GEOID10",
                 tiles_col="tiles",
                 dual_graph_distance_file=None,
                 dual_graph_distance_save=None,
                 compressed_coi_data=False):
        js = json.load(open(graph_file_name))
        self.dual_graph = nx.readwrite.json_graph.adjacency_graph(
            js, attrs=dict(id="id", key=key_name))
        self.coi_data = pandas.read_csv(lookup_table_file_name, index_col=0)

        geoids_in_graph = [str(v) for _, v in self.dual_graph.nodes(key_name)]

        if compressed_coi_data:
            # New format: lists of tiles for each row.
            self.coi_data[tiles_col] = self.coi_data[tiles_col].apply(literal_eval)
            geoids_in_dataframe = sorted(
                set.union(*(set(t) for t in self.coi_data[tiles_col])))
        else:
            # Old format: binary encoding (each unit is a column).
            geoids_in_dataframe = self.coi_data.iloc[:, 3:].columns

        excess_columns = set(geoids_in_dataframe) - set(geoids_in_graph)
        if excess_columns:
            warnings.warn(
                "There were more geographic units in submissions",
                "than in the dual graph. Dropping the extras."
            )
            if compressed_coi_data:
                self.coi_data[tiles_col] = self.coi_data[tiles_col].apply(
                    lambda tiles: [t for t in tiles if t not in excess_columns]
                )
            else:
                self.coi_data = pandas.DataFrame.drop(self.coi_data,
                                                      columns=excess_columns)

        infinity_standin = len(self.dual_graph.nodes) + 1

        if dual_graph_distance_file is None:
            distances = dict(
                nx.algorithms.all_pairs_shortest_path_length(self.dual_graph))
            sys.stdout.flush()

            distances_matrix = np.zeros(
                (len(distances.keys()), len(distances.keys())))
            for key in distances.keys():
                row_in_correct_order = np.zeros(len(distances))
                this_row = distances[key]
                # This is to handle disconnected graphs
                indices = this_row.keys()
                for index in range(len(distances.keys())):
                    if index in indices:
                        row_in_correct_order[index] = this_row[index]
                    else:
                        row_in_correct_order[index] = infinity_standin
                distances_matrix[key, :] = row_in_correct_order
            if dual_graph_distance_save is not None:
                np.savetxt(dual_graph_distance_save,
                           distances_matrix,
                           fmt='%d',
                           delimiter=",")
        else:
            distances_matrix = np.loadtxt(dual_graph_distance_file,
                                          delimiter=",")
        print("Finished shortest path")

        number_of_cois = self.coi_data.shape[0]
        self.coi_total_dissimilarities = np.zeros(
            (number_of_cois, number_of_cois))

        dissimilarities_between_submissions = []
        pool = Pool(nodes=number_of_cpus)

        if compressed_coi_data:
            cois_as_bool_matrix = np.zeros((len(self.coi_data), len(distances)), dtype=bool)
            tile_indices = {str(tile): idx
                            for idx, tile in enumerate(geoids_in_graph)}
            for idx, tiles in enumerate(self.coi_data[tiles_col]):
                for tile in tiles:
                    cois_as_bool_matrix[idx, tile_indices[tile]] = True
        else:
            cois_as_bool_matrix = np.array(
                self.coi_data.iloc[:, 3:].to_numpy(), dtype=bool)
        rows = [cois_as_bool_matrix[i, :] for i in range(number_of_cois)]
        row_nums = range(number_of_cois)
        dists = [distances_matrix[row, :] for row in rows]
        dissimilarities_between_submissions = []
        sys.stdout.flush()

        print("Starting dissimilarity computation")
        for result in list(
                tqdm.tqdm(pool.uimap(mp_compute_distance_wrapper,
                                     number_of_cois * [cois_as_bool_matrix],
                                     dists, row_nums),
                          total=len(rows))):
            dissimilarities_between_submissions += result

        for result in dissimilarities_between_submissions:
            i = result[0][0]
            j = result[0][1]
            number = result[1]
            self.coi_total_dissimilarities[i, j] = number

        self.coi_total_dissimilarities = self.coi_total_dissimilarities + np.transpose(
            self.coi_total_dissimilarities)
        if not compressed_coi_data:
            self.coi_location_data = self.coi_data.iloc[:, 3:]
            self.coi_data = self.coi_data.iloc[:, :3]
        self.dendrogram = hierarchy.linkage(
            squareform(
                np.nan_to_num(self.coi_total_dissimilarities,
                              posinf=2 * infinity_standin)), 'complete')

    def save_db(self, file_path):
        with open(file_path, 'wb') as outp:
            pickle.dump(self, outp, pickle.HIGHEST_PROTOCOL)

    def plot_dendrogram(self, ylim=None):
        hierarchy.dendrogram(self.dendrogram)
        if ylim is not None:
            plt.ylim(ylim)
        plt.show()

    def clusters_from_threshold(self, threshold):
        clusters = hierarchy.fcluster(self.dendrogram, threshold, 'distance')
        a = self.coi_data
        a["clusters"] = clusters
        return (a)

    def clusters_from_number(self, number_of_clusters):
        clusters = hierarchy.fcluster(self.dendrogram, number_of_clusters,
                                      'maxclust')
        a = self.coi_data
        a["clusters"] = clusters
        return (a)

