# from MABAlgorithms.rl.bandits import *
from MABAlgorithms.rl.bandits import EpsilonGreedy
from MABAlgorithms.rl.bandits import Pursuit
from MABAlgorithms.rl.bandits import EXP4
from MABAlgorithms.rl.bandits import EpochGreedy
from MABAlgorithms.rl.bandits import ThompsonSampling
from MABAlgorithms.rl.bandits import KernelUCB

from sklearn.metrics.pairwise import rbf_kernel
import numpy as np
import statistics as stats

import pmdarima as pm

'''
CMAB class
Used to handle the running of contextual and non-contextual bandits
'''
class CMAB():
    '''
    Initialize tne CMAB framework with the appropriate parameters
    Arguments: bandit: string containing the inputted bandit algorithm
               n_arms: number of arms
               n_experts: number of experts
               n_features: number of features
               epsilon: variable used in Epsilon Greedy Algorithm
               gamma: variable used in EXP4 and Kernel UCB Algorithm
               learning_rate: variable used in Pursuit Algorithm
               kern: the kernel used in the Kernel UCB Algorithm
    '''
    def __init__(self, bandit, n_arms, n_experts, n_features, epsilon=0.1, gamma=0.1, eta=1.0, learning_rate=0.1, kern=rbf_kernel):
        self.banditAlgo = bandit
        if(bandit == "epsilongreedy"):
            self.bandit = EpsilonGreedy.EpsilonGreedy(n_arms=n_arms, epsilon=epsilon)
        elif(bandit == "pursuit"):
            self.bandit = Pursuit.Pursuit(n_arms=n_arms, learning_rate=learning_rate)
        elif(bandit == "exp4"):
            self.bandit = EXP4.EXP4(n_arms=n_arms, n_experts=n_experts, gamma=gamma)
        elif(bandit == "epochgreedy"):
            self.bandit = EpochGreedy.EpochGreedy(n_arms=n_arms)
        elif(bandit == "thompsonsampling"):
            self.bandit = ThompsonSampling.ThompsonSampling(n_arms=n_arms)
        elif(bandit == "kernelucb"):
            self.bandit = KernelUCB.KernelUCB(n_arms=n_arms, n_features=1, gamma=gamma, eta=eta, kern=kern)

    '''
    Runs the appropriate bandit algorithm
    Potential Arguments: advice: Advice vector used in EXP4 Algorithm
                         hypothesis: Hypothesis space used in Epoch Greedy Algorithm
                         tround: step index used in Kernel UCB Algorithm
                         context: the observed context
    '''
    def pickArm(self, **kwargs):
        arm = 0
        if(self.banditAlgo == "exp4"):
            advice = kwargs['advice']
            arm = self.bandit.run(advice=advice)
        elif(self.banditAlgo == "epochgreedy"):
            hypothesis = kwargs['hypothesis']
            context = kwargs['context']
            arm = self.bandit.run(context=context, hypothesis=hypothesis)
        elif(self.banditAlgo == "thompsonsampling"):
            context = kwargs['context']
            arm = self.bandit.run(context=context)
        elif(self.banditAlgo == "kernelucb"):
            context = kwargs['context']
            tround = kwargs['tround']
            arm = self.bandit.run(context=context, tround=tround)
        else:
            arm = self.bandit.run()
        self.chosen_arm = arm
        return arm
    
    '''
    Updates the bandit algorithm with the reward
    Arguments: reward: the reward for the chosen arm
    '''
    def update(self, reward, **kwargs):
        self.bandit.update(reward=reward)

'''
iCMAB class
Extension of the CMAB class
Has the same functionality as the CMAB class only with anomaly detection added in
'''
class iCMAB(CMAB):
    '''
    Initialize the iCMAB framework
    '''
    def __init__(self, bandit, n_arms, n_experts, n_features, epsilon=0.1, gamma=0.1, eta=1, learning_rate=0.1, kern=rbf_kernel):
        super().__init__(bandit, n_arms, n_experts, n_features, epsilon, gamma, eta, learning_rate, kern)
        
        self.obs = None
        self.pastObs = []

    
    '''
    Clear observation history
    '''
    def clearContextHistory(self):
        self.pastObs.clear()

    
    '''
    Generate an ARIMA model for the reward
    '''
    def generateRewardARIMA(self):
        training_data = np.array(self.rewardHistory, dtype=np.float64)

        arima_model = pm.auto_arima(training_data, start_p=1, start_q=1, start_P=1, start_Q=1,
                                    max_p=5, max_q=5, max_P=5, max_Q=5, seasonal=False,
                                    stepwise=True, suppress_warnings=True, D=10, max_D=10,
                                    error_action='ignore')
        
        return arima_model

    '''
    Generate an ARIMA model for the arm and context
    Arguments: arm: the arm that the ARIMA model is for
               context: the context that the ARIMA model's training data will come from
    '''
    def generateContextARIMA(self, arm, context=None):
        if(context is None):
            raise ValueError()
            
        # Get the training data for the specified context and arm
        contextHistory = []
        for i in range(len(self.pastObs)):
            # print("Context:")
            # print(context)
            # print(self.pastObs)
            pastContext = self.pastObs[i][context]
            contextHistory.append(pastContext[arm])

        # Create the ARIMA model based on the training data
        training_data = np.array(contextHistory, dtype=np.float64)

        arima_model = pm.auto_arima(training_data, start_p=1, start_q=1, start_P=1, start_Q=1,
                                    max_p=5, max_q=5, max_P=5, max_Q=5, seasonal=False,
                                    stepwise=True, suppress_warnings=True, D=10, max_D=10,
                                    error_action='ignore')
        return arima_model
    
    '''
    Detect if the reward given is anomalous
    Arguments: reward: the reward
               arima_model: the arima model to use
    '''
    def detectRewardAnomaly(self, reward=None, arima_model=None):
        if(reward is None or arima_model is None):
            raise ValueError()

        x = [reward]
        y = arima_model.predict(n_periods=1)

        l1_diff = abs(np.linalg.norm(x, ord=1) - np.linalg.norm(y, ord=1))
        # print("reward l1_diff: ", l1_diff)

        if(l1_diff > 0.1):
            return True, y[0]
        
        return False, x[0]

    '''
    Detect if the context given is anomalous
    Arguments: contextIndex: the index of the context we are examining for anomalies
               arima_model: the arima model to use
               context: the specific observed data to examine for anomalies
    '''
    def detectContextAnomaly(self, contextIndex=0, arima_model=None, context=None):
        if(context is None or arima_model is None):
            raise ValueError()
        
        if(self.obs is None):
            return False, context[contextIndex]
        
        x = [context]
        
        y = []
        prediction = arima_model.predict(n_periods=1)
        for i in range(len(x)):
            if(i == contextIndex):
                y.append(prediction[0])
            else:
                y.append(context[i])

        l1_diff = abs(np.linalg.norm(x, ord=1) - np.linalg.norm(y, ord=1))
        # print("context l1_diff: ", l1_diff)

        if(l1_diff > 0.1):
            return True, prediction[0]
        
        return False, context
    
    '''
    Updates the bandit algorithm and the anomaly detection object
    Arguments: reward: the reward for the chosen arm
               obs: the observed data
               action: the chosen arm
    '''
    def update(self, reward, **kwargs):
        super().update(reward, **kwargs)

        if (self.obs != None):
            self.pastObs.append(self.obs)
        self.obs = kwargs['obs']
        self.chosen_arm = kwargs['action']