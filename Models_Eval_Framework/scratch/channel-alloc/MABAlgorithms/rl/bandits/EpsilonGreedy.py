import numpy as np
from ..interface.bandit import MultiArmedBandit

'''
Class for Epsilon Greedy
http://proceedings.mlr.press/v28/agrawal13.pdf
Arguments - <>
'''
class EpsilonGreedy(MultiArmedBandit):
    '''
    Constructor
    Arguments - <Number of Arms, Epsilon>
    '''
    def __init__(self, n_arms=2, epsilon=0.1):
        self.n_arms = n_arms
        self.epsilon = epsilon
        self.rewardHistory = [[] for _ in range(n_arms)]
        self.means = [1 for _ in range(n_arms)]
        self.regretHistory = []
    
    '''
    Run the bandit and return the best performing arm/decision
    Arguments - <>
    '''
    def run(self):
        p = np.random.rand()

        # With probibility epsilon, randomly select an arm
        # Otherwise, select the arm with the highest current mean
        if (p < self.epsilon):
            a = np.random.choice(self.n_arms)
        else:
            a = np.argmax(self.means)

        self.last_choice = a

        return a
			
    '''
    Upate the bandit with the corresponding reward
    Arguments - <Reward Value>
    '''
    def update(self, reward):
        arm = self.last_choice
        
        # Regret
        self.regretHistory.append(self.means[arm] - reward)

        self.rewardHistory[arm].append(reward)
        self.means[arm] = np.average(self.rewardHistory[arm])
		
    '''
    Find the regret bound at time t
    Arguments - <Total Time>
    '''
    def regretBound(self, T):
        return T