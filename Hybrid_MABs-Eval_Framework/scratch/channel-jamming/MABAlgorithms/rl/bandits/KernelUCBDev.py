import numpy as np

class LinUCB():
    def __init__(self, n_arms=1, d = 2, alpha=0.1) -> None:
        self.n_arms = n_arms
        self.alpha = alpha
        self.sums = [0] * n_arms
        self.iter = 0
        self.count = [0] * n_arms
        self.d = d
        self.arms = []
        for _ in range(n_arms):
            A = np.identity(d)
            b = np.zeros((d, 1))
            self.arms.append((A, b))
        self.cum_reward = 0

    def set_confidence(self, conf):
        self.epsilon = conf

    def select_arm(self, context, **kwargs):
        # if context.shape[0] < context.shape[1]:
        #     context = np.transpose(context)
        self.context = context.values if isinstance(context, pd.DataFrame) else context
        self.context = np.expand_dims(self.context, axis=1)
        UCB_Values = [0] * self.n_arms

        for i in range(0, self.n_arms):
            A, b = self.arms[i]
            theta = np.dot(inv(A), b)
            p = np.dot(np.transpose(theta),self.context) +\
                 self.alpha * np.sqrt(np.dot(self.context.T, np.dot(inv(A), self.context)))
            p = np.asscalar(p)
            UCB_Values[i] = p

        bandit_arms = np.argwhere(UCB_Values == np.amax(UCB_Values)).flatten().tolist()
        try:
            bandit = np.random.choice(bandit_arms)
        except:
            bandit=0

        return bandit

    def update(self, reward=0, regret=0, choice=0):
        self.iter += 1
        A, b = self.arms[choice]
        A += np.matmul(self.context, np.transpose(self.context))
        b += reward * self.context
        self.arms[choice] = (A, b)
        self.cum_reward += reward