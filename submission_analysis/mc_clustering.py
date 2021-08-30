"""Markov chain-based cluster refinement."""
from copy import deepcopy
from random import randrange, random, choice
from typing import Callable, Dict, Set, Tuple, List
from dataclasses import dataclass, field, InitVar
import numpy as np

ChainParts = Dict[int, Set[int]]
ChainAssignment = Dict[int, int]

Score = float
Probability = float

ProposalFn = Callable['ChainState', 'ChainState']
ScoreFn = Callable['ChainState', Score]
ConstraintFn = Callable['ChainState', Probability]
AcceptFn = Callable[Tuple['ChainState', 'ChainState'], Probability]


@dataclass(frozen=True)
class ChainState:
    """A state of a clustering Markov chain."""
    partitions: ChainParts
    assignment: ChainAssignment
    score_fns: Dict[str, ScoreFn]
    scores: Dict[str, Score] = field(default_factory=dict)

    def __post_init__(self):
        for name, score_fn in self.score_fns.items():
            self.scores[name] = score_fn(self)

    def flip(self, flips: Dict[int, int]) -> 'ChainState':
        """Moves nodes between partitions."""
        partitions = deepcopy(self.partitions)
        assignment = deepcopy(self.assignment)
        for index, part in flips.items():
            partitions[assignment[index]].remove(index)
            partitions[part].add(index)
            assignment[index] = part
        return self.__class__(partitions, assignment, self.score_fns)

    @staticmethod
    def random(num_docs: int, num_clusters: int,
               score_fns: Dict[str, ScoreFn]) -> 'ChainState':
        """Generates a random partition of `num_docs` into `num_clusters`."""
        assignment = {doc: randrange(num_clusters) for doc in range(num_docs)}
        partitions = {cluster: set() for cluster in range(num_clusters)}
        for doc, label in assignment.items():
            partitions[label].add(doc)
        return ChainState(partitions, assignment, score_fns)


def single_flip_proposal(current: ChainState) -> ChainState:
    """Moves a single document to another cluster."""
    index = randrange(len(current.assignment))
    curr_partition = current.assignment[index]
    next_partition = randrange(len(current.partitions))
    assert len(current.partitions) > 1
    while curr_partition == next_partition:
        next_partition = randrange(len(current.partitions))
    return current.flip({index: next_partition})


@dataclass
class MarkovChain:
    """A Markov chain for clustering."""
    proposal_fn: ProposalFn
    score_fns: Dict[str, ScoreFn]
    accept_fn: AcceptFn
    soft_constraints: List[ConstraintFn]
    num_docs: int
    num_clusters: int
    length: int
    step: int = 0
    state: ChainState = None

    def __post_init__(self):
        self.state = ChainState.random(self.num_docs, self.num_clusters,
                                       self.score_fns)

    def __iter__(self):
        return self

    def __next__(self):
        if self.step == self.length:
            raise StopIteration
        last_state = self.state

        proposal = self.proposal_fn(self.state)
        acceptance_prob = self.accept_fn(self.state, proposal)
        for constraint in self.soft_constraints:
            acceptance_prob *= constraint(proposal)
        if random() < acceptance_prob:
            self.state = proposal

        self.step += 1
        return last_state


def intracluster_score(dist_matrix: np.ndarray) -> ScoreFn:
    """Creates an average intracluster distance score from `distance_matrix."""
    def score_fn(state: ChainState) -> float:
        score = 0
        n_pairs = 0
        for indices in state.partitions.values():
            for outer_index in indices:
                for inner_index in indices:
                    score += dist_matrix[outer_index, inner_index]
                    n_pairs += 1
        return score / max(n_pairs, 1)

    return score_fn


def accept_1d(score: str,
              beta: float,
              flipped: bool = False) -> Callable[ChainState, Probability]:
    """Creates an acceptance function based on a single score.

    Let the improvement ratio m = (proposal score / current score)
    (when `flipped` is `False`) or m = (current score / proposal score) (when
    `flipped` is `True`). If m < 1, we accept with probability e^{-β / m}.
    If m ≥ 1 (that is, we improve), we accept with probability 1.

    :param score: Name of the score.
    :param beta: Determines the propensity to reject (higher is pickier).
    :param flipped: Determines the numerator/denominator direction in the
    acceptance formula.
    :return: Probability of acceptance (0-1).
    """
    def accept_fn(current: ChainState, proposed: ChainState) -> Probability:
        if flipped:
            m = proposed.scores[score] / current.scores[score]
        else:
            m = current.scores[score] / proposed.scores[score]
        if m >= 1:
            return 1.
        return np.exp(-beta * m)

    return accept_fn


# In[8]:


def accept_nd(scores: List[Tuple[str, bool]], beta: float) -> AcceptFn:
    """Creates an acceptance function based on a list of scores.

    If every score improves (that is, the proposal strictly dominates the
    old proposal), we accept. Otherwise, we accept with probability e^{-β / m},
    where m is the minimum improvement ratio.

    :param scores: A list of (score name, flipped) pairs. When a score is
      `flipped`, its improvement ratio is (current score / proposal score);
      otherwise, its improvement ratio is (proposal score / current score).
    :param beta: Determines the propensity to reject (higher is pickier).
    :return: Probability of acceptance.
    """
    def accept_fn(current: ChainState, proposed: ChainState) -> Probability:
        min_ratio = min(
            (proposed.scores[score] /
             current.scores[score] if flipped else current.scores[score] /
             proposed.scores[score]) for score, flipped in scores)
        if min_ratio >= 1:
            return 1.
        return np.exp(-beta / min_ratio)

    return accept_fn


def cluster_size_soft_constraint(ideal_cluster_size: int) -> AcceptFn:
    """Creates a soft constraint based on cluster size.

    If all clusters are at least `ideal_cluster_size`, we
    accept with probability 1; otherwise, we accept with
    probability (min cluster size / `ideal_cluster_size`)."""
    def constraint_fn(state: ChainState) -> Probability:
        min_cluster_size = len(min(state.partitions.values(), key=len))
        if min_cluster_size >= ideal_cluster_size:
            return 1.
        return min_cluster_size / ideal_cluster_size

    return constraint_fn


def geo_chain(distance_matrix: np.ndarray, beta: float, num_clusters: int,
              length: int) -> MarkovChain:
    """Creates a chain that minimizes intracluster geographical distances."""
    num_docs = distance_matrix.shape[0]
    score_fns = {'geo': intracluster_score(distance_matrix)}
    accept_fn = accept_1d('geo', beta)
    soft_constraints = [cluster_size_soft_constraint(num_docs / num_clusters)]
    return MarkovChain(single_flip_proposal, score_fns, accept_fn,
                       soft_constraints, num_docs, num_clusters, length)


def semantic_chain(similarity_matrix: np.ndarray, beta: float,
                   num_clusters: int, length: int) -> MarkovChain:
    """Creates a chain that maximizes intracluster semantic similarities."""
    num_docs = similarity_matrix.shape[0]
    score_fns = {'semantic': intracluster_score(similarity_matrix)}
    accept_fn = accept_1d('semantic', beta, flipped=True)
    soft_constraints = [cluster_size_soft_constraint(num_docs / num_clusters)]
    return MarkovChain(single_flip_proposal, score_fns, accept_fn,
                       soft_constraints, num_docs, num_clusters, length)


def geo_semantic_chain(distance_matrix: np.ndarray,
                       similarity_matrix: np.ndarray, beta: float,
                       num_clusters: int, length: int) -> MarkovChain:
    """Creates a chain that simultaneusly minimizes intracluster geographical
    distances and maximizes intracluster semantic similarities."""
    assert distance_matrix.shape == similarity_matrix.shape
    num_docs = similarity_matrix.shape[0]
    score_fns = {
        'geo': intracluster_score(distance_matrix),
        'semantic': intracluster_score(similarity_matrix)
    }
    accept_fn = accept_nd([('geo', False), ('semantic', True)], beta)
    soft_constraints = [cluster_size_soft_constraint(num_docs / num_clusters)]
    return MarkovChain(single_flip_proposal, score_fns, accept_fn,
                       soft_constraints, num_docs, num_clusters, length)
