import numpy as np
import math
import pandas as pd

class TSLR():
    def __init__(self, n_arms=1, d = 2, epsilon=0.5, delta=0.5, R=0.1) -> None:
        self.n_arms = n_arms
        self.type = 'TSLR'
        self.epsilon = epsilon
        self.delta = delta,
        self.R = R
        self.sums = [0] * n_arms
        self.iter = 0
        self.count = [0] * n_arms
        self.d = d
        self.arms = []
        self.cum_reward = 0

        self.v = self.R * math.sqrt((24 / self.epsilon) * self.d * math.log(1 / self.delta))
        self.B = np.identity(d)
        self.mu_hat = np.zeros((d, 1))
        self.f = np.zeros((d, 1))

    def set_confidence(self, conf):
        self.epsilon = conf

    def select_arm(self, context, **kwargs):
        self.context = context
        if isinstance(context, pd.DataFrame):
            self.context = self.context.values()
        self.context = context.values
        u_t = np.random.multivariate_normal(self.mu_hat, self.v**2 * self.B)
        best_arm, best = None, None
        for i in range(self.n_arms):
            if best is None or best < np.dot(context.transpose(), u_t):
                best = np.dot(context.transpose(), u_t)
                best_arm = i
        return best_arm

    def update(self, reward=0, regret=0, choice=0):
        self.iter += 1
        self.B += self.context * self.context.transpose()
        self.f += self.context * reward
        self.mu_hat = np.linalg.inv(self.B) * self.f
        self.cum_reward += reward