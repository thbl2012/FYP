from scipy.spatial import distance_matrix

from src.util import *


class AtomChain:
    def __init__(self, atoms, charges,
                 spring_const=1., spring_len=1.,
                 atom_radius=1., epsilon=1.,
                 boltzmann_const=1., temperature=1.,
                 charge_matrix=None, dist_matrix=None,
                 lennard=0., spring=0., coulomb=0.,
                 energy=0., last_index=None,
                 rebuild=False,):
        self.atoms = np.copy(atoms)
        self.charges = np.copy(charges)
        self.atom_radius = atom_radius
        self.spring_const = spring_const
        self.spring_len = spring_len
        self.epsilon = epsilon
        self.boltzmann_const = boltzmann_const
        self.temperature = temperature
        if rebuild:
            self.dist_matrix = pairwise_dist(atoms)
            self.charge_matrix = pairwise_charges(charges)
            self.spring = spring_energy(self.dist_matrix, spring_len, spring_const)
            self.lennard = lennard_energy(self.dist_matrix, atom_radius, epsilon)
            self.coulomb = coulomb_energy(self.dist_matrix, self.charge_matrix)
            self.energy = self.spring + self.lennard + self.coulomb
            self.last_index = last_index
        else:
            self.dist_matrix = np.copy(dist_matrix)
            self.charge_matrix = charge_matrix
            self.spring = spring
            self.lennard = lennard
            self.coulomb = coulomb
            self.energy = energy
            self.last_index = None

    def get_trial_dist_vector(self, p):
        return distance_matrix(self.atoms, p[None, :]).reshape(-1)

    def update_position(self, i, p, trial_dist_vector):
        self.atoms[i] = p
        self.dist_matrix[i] = trial_dist_vector
        self.dist_matrix[:, i] = trial_dist_vector

    def spring_diff(self, i, trial_dist_vector):
        prev_link_diff = (0 if i == 0
                          else ((trial_dist_vector[i-1] - self.spring_len)**2
                                - (self.dist_matrix[i-1, i] - self.spring_len)**2))
        next_link_diff = (0 if i == len(self.atoms)-1
                          else ((trial_dist_vector[i+1] - self.spring_len)**2
                                - (self.dist_matrix[i, i+1] - self.spring_len)**2))
        return (prev_link_diff + next_link_diff) * self.spring_const

    def coulomb_diff(self, i, trial_dist_vector):
        diff = (self.charge_matrix[i]/trial_dist_vector
                - self.charge_matrix[i]/self.dist_matrix[i])
        diff[i] = 0
        return np.sum(diff)

    def lennard_diff(self, i, trial_dist_vector):
        old = self.atom_radius/self.dist_matrix[i]
        old[i] = 0
        old = old*old*old*old*old*old
        new = self.atom_radius/trial_dist_vector
        new[i] = 0
        new = new*new*new*new*new*new
        return np.sum(new*new - new - old*old + old) * self.epsilon * 4

    def mutate(self, max_dist):
        rand = np.random.RandomState()
        i = rand.randint(0, len(self.atoms))
        p = random_position(self.atoms[i], max_dist)

        # Compute energy difference
        v = self.get_trial_dist_vector(p)
        spring_diff = self.spring_diff(i, v)
        lennard_diff = self.lennard_diff(i, v)
        coulomb_diff = self.coulomb_diff(i, v)
        energy_diff = spring_diff + lennard_diff + coulomb_diff

        # Generate acceptance decision
        accepted = 0
        if rand.uniform(0, 1) < np.exp(- energy_diff / (self.boltzmann_const * self.temperature)):
            self.update_position(i, p, v)
            self.energy += energy_diff
            self.spring += spring_diff
            self.lennard += lennard_diff
            self.coulomb += coulomb_diff
            accepted = 1
        self.last_index = i
        return accepted

    def test_mutate(self, max_dist):
        rand = np.random.RandomState()
        i = rand.randint(0, len(self.atoms))
        p = random_position(self.atoms[i], max_dist)

        # Compute energy difference
        v = self.get_trial_dist_vector(p)
        spring_diff = self.spring_diff(i, v)
        lennard_diff = self.lennard_diff(i, v)
        coulomb_diff = self.coulomb_diff(i, v)
        energy_diff = spring_diff + lennard_diff + coulomb_diff

        # Generate acceptance decision
        accepted = 0
        uni = rand.uniform(0, 1)
        old = self.energy
        new = old + energy_diff
        prob = np.exp(- energy_diff / (self.boltzmann_const * self.temperature))
        if uni < prob:
            self.update_position(i, p, v)
            self.energy += energy_diff
            self.spring += spring_diff
            self.lennard += lennard_diff
            self.coulomb += coulomb_diff
            accepted = 1
        self.last_index = i
        return {'acc': accepted, 'r': uni, 'p': prob, 'old': old, 'new': new, 'd': v[i]}

    def recompute(self):
        self.dist_matrix = pairwise_dist(self.atoms)
        self.charge_matrix = pairwise_charges(self.charges)
        self.spring = spring_energy(self.dist_matrix, self.spring_len, self.spring_const)
        self.lennard = lennard_energy(self.dist_matrix, self.atom_radius, self.epsilon)
        self.coulomb = coulomb_energy(self.dist_matrix, self.charge_matrix)
        self.energy = self.spring + self.lennard + self.coulomb

    def copy(self):
        return AtomChain(
            self.atoms, self.charges,
            spring_const=self.spring_const,
            spring_len=self.spring_len,
            atom_radius=self.atom_radius,
            epsilon=self.epsilon,
            boltzmann_const=self.boltzmann_const,
            temperature=self.temperature,
            dist_matrix=self.dist_matrix,
            charge_matrix=self.charge_matrix,
            spring=self.spring,
            lennard=self.lennard,
            coulomb=self.coulomb,
            energy=self.energy,
            last_index=self.last_index,
            rebuild=False
        )
