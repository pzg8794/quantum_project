import numpy as np
from ..interface.bandit import ContextualMultiArmedBandit
'''
Class for KernelUCB with online updates
https://arxiv.org/pdf/1309.6869
Arguments - <>
'''
class KernelUCB(ContextualMultiArmedBandit):
    '''
    Constructor
    Arguments - <Number of Arms, Size of Context Vector, Gamma, Eta (η), Kernel Function>
    '''
    def __init__(self, n_arms, n_features, gamma, eta, kern):
        self.n_arms = n_arms
        self.n_features = n_features

        # regularization parameter (η)
        self.eta = eta
        # exploration parameter

        self.gamma = gamma

        # kernel function
        self.kern = kern

        self.u = np.zeros(n_arms)
        self.sigma = np.zeros(n_arms)

        self.pulled = []
        self.rewards = []

        self.means = [0 for _ in range(n_arms)]
        self.rewardHistory = [[] for _ in range(n_arms)]
        self.totalRewardHistory = []
        self.regretHistory = []

        self.Kinv = {}

        return
    
    '''
    Run the bandit and return the best performing arm/decision
    Arguments - <Context Vector>
    '''
    def run(self, context=None, **kwargs):
        self.context = context
        self.tround = kwargs['tround']
        context = np.reshape(context, (self.n_arms,self.n_features))

        if self.tround == 0:
            self.u[0] = 1.0
        else:
            k_x = self.kern(context,np.reshape(self.pulled,(self.tround,self.n_features)))
            for i in range(self.n_arms):
                self.sigma[i] = np.sqrt(self.kern(context[i].reshape(1,-1),context[i].reshape(1,-1))-k_x[i].T.dot(self.Kinv[self.tround-1]).dot(k_x[i]))
                self.u[i] = k_x[i].T.dot(self.Kinv[self.tround-1]).dot(self.y) + (self.eta/np.sqrt(self.gamma))*self.sigma[i]

        action = np.random.choice(np.where(self.u==max(self.u))[0])
        self.last_choice = action
        return action
    
    '''
    Upate the bandit with the corresponding reward
    Updates Kernel
    Arguments - <Reward Value>
    '''
    def update(self, reward):
        arm = self.last_choice
        self.rewardHistory[self.last_choice].append(reward)
        self.totalRewardHistory.append(reward)
        self.means[self.last_choice] = sum(self.rewardHistory[self.last_choice]) / len(self.rewardHistory[self.last_choice])

        optimalArm = np.argmax(self.means)
        self.regretHistory.append(self.means[optimalArm] - reward)

        context = self.context
        context = np.reshape(context, (self.n_arms,self.n_features))

        self.pulled.append(context[arm].reshape(1,-1))

        x_t = context[arm].reshape(1,-1)

        k_x = self.kern(context,np.reshape(self.pulled,(self.tround+1,self.n_features)))

        self.rewards.append(reward)
        self.y = np.reshape(self.rewards,(self.tround+1,1))

        # If first round build inverse kernel
        if self.tround==0:
            self.Kinv[self.tround] = 1.0/(self.kern(x_t,x_t) + self.gamma)
        else: # online update of the kernel matrix inverse
            Kinv = self.Kinv[self.tround-1]
            b = k_x[arm][:-1]
            b = b.reshape(self.tround,1)

            bKinv = np.dot(b.T,Kinv)
            Kinvb = np.dot(Kinv,b)

            K22 = 1.0/(k_x[arm][-1] + self.gamma - np.dot(bKinv,b))
            K11 = Kinv + K22*np.dot(Kinvb,bKinv)
            K12 = -K22*Kinvb
            K21 = -K22*bKinv

            K11 = np.reshape(K11,(self.tround,self.tround))
            K12 = np.reshape(K12,(self.tround,1))
            K21 = np.reshape(K21,(1,self.tround))
            K22 = np.reshape(K22,(1,1))

            self.Kinv[self.tround] = np.vstack((np.hstack((K11,K12)),np.hstack((K21,K22))))
            
    '''
    Find the regret bound at time T
    Arguments - <Total Time>
    '''
    def regretBound(self, T):
        return self.n_features * np.sqrt(T * np.log((1 + T) / self.gamma))