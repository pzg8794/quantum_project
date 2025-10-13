import numpy as np
import math
from ..interface.bandit import ContextualMultiArmedBandit

class ThompsonSampling(ContextualMultiArmedBandit):
    def __init__(self, n_arms=1, d = 2, epsilon=0.5, delta=0.5, R=0.1) -> None:
        self.banditAlgo = "thompsonsampling"

        self.start = False
        self.n_arms = n_arms
        self.epsilon = epsilon
        self.delta = delta,
        self.R = R
        self.sums = [0] * n_arms
        self.iter = 0
        self.count = [0] * n_arms
        self.d = d
        self.arms = []
        self.cum_reward = 0

        self.rewardHistory = [[] for _ in range(n_arms)]
        self.totalRewardHistory = []
        self.last_choice = 0

        self.v = self.R * math.sqrt((24 / self.epsilon) * self.d * math.log(1 / 0.5))
        self.B = np.identity(d)
        self.mu_hat = np.zeros((d, 1))
        self.f = np.zeros((d, 1))

    def set_confidence(self, conf):
        self.epsilon = conf

    def run(self, context, **kwargs):
        self.context = context

        # print(self.mu_hat.T)
        # print(self.v**2 * self.B)

        if self.start == False:
            return 0
        
        print(self.mu_hat.T[0])
        print(self.v**2 * self.B)
        u_t = np.random.multivariate_normal(self.mu_hat.T[0], self.v**2 * self.B)

        # a_m = np.argmax(u_t)
        # return a_m
    
        best_arm, best = None, None

        print("MAX")
        print(u_t)
        print(context.transpose())
        print(np.dot(context.transpose(), u_t[0]))
        print(context.transpose() * u_t)
        a_m = np.argmax(context.transpose() * u_t)

        self.last_choice = a_m
        return a_m

    def update(self, reward=0, regret=0, choice=0):
        self.start = True
        arm = self.last_choice
        self.rewardHistory[arm].append(reward)
        self.totalRewardHistory.append(reward)

        self.iter += 1
        self.B += self.context * self.context.transpose()
        self.f += self.context * reward
        self.mu_hat = np.dot(np.linalg.inv(self.B), self.f)
        self.cum_reward += reward