import numpy as np
import math
from ..interface.bandit import ContextualMultiArmedBandit

'''
Class for Thompson Sampling with Linear Payoffs
http://proceedings.mlr.press/v28/agrawal13.pdf
Arguments - <>
'''
class ThompsonSampling(ContextualMultiArmedBandit):
    '''
    Constructor
    Arguments - <Number of Arms, Size of Context Vector, Epsilon, Delta, R>
    '''
    def __init__(self, n_arms=2, n_features=2, epsilon = 0.1, delta = 0.1, R = 1):
        self.n_arms = n_arms
        self.n_features = n_features

        self.epsilon = epsilon
        self.delta = delta # Must be (0, 1]
        self.R = R # Must be (0, 1]

        self.v = self.R * np.sqrt((24/self.epsilon) * self.n_features * np.log(1/self.delta))
        self.v = 0.5
        self.B = np.identity(self.n_arms)
        self.u = np.zeros((self.n_features, self.n_arms))
        self.f = np.zeros((self.n_features, self.n_arms))

        self.rewardHistory = [[] for _ in range(n_arms)]
        self.means = [0 for _ in range(n_arms)]
        self.d = [(1/10000)**-1 for _ in range(n_arms)]
        self.regretHistory = []

        self.totalRewardHistory = []


    '''
    Run the bandit and return the best performing arm/decision
    Arguments - <Context Vector>
    '''
    def run(self, context=None, **kwargs):
        
        if context is None:
            raise ValueError()
        
        u_t = [np.random.normal(self.means[arm], self.d[arm]) for arm in range(self.n_arms)]

        a_t = np.argmax(u_t)

        self.last_choice = a_t

        self.context = context[a_t]

        return a_t

    '''
    Upate the bandit with the corresponding reward
    Arguments - <Reward Value>
    '''
    def update(self, reward):
        # Regret
        optimalArm = np.argmax(self.means)
        self.regretHistory.append(self.means[optimalArm] - reward)


        self.rewardHistory[self.last_choice].append(reward)
        self.totalRewardHistory.append(reward)
        self.means[self.last_choice] = sum(self.rewardHistory[self.last_choice]) / len(self.rewardHistory[self.last_choice])
        
        self.d[self.last_choice] = ((1/10000) + len(self.rewardHistory[self.last_choice]))**-1

        

    

    '''
    Find the regret at time T
    Arguments - <Total Time>
    '''
    def regretBound(self, T):
        # regretBound = ((self.n_features ** 2) / self.epsilon) * np.sqrt(T ** (1 + self.epsilon)) * np.log(T * self.n_features) * np.log(1 / self.delta)
        regretBound = (self.n_features ** (3/2)) * np.sqrt(T)
        # regretBound = self.n_features * np.sqrt(T * np.log(self.n_arms))
        return regretBound