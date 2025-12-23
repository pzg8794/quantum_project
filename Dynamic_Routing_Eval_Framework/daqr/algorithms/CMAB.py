from daqr.algorithms.MABAlgorithms.rl.bandits import *
from sklearn.metrics.pairwise import rbf_kernel
import numpy as np
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
            self.bandit = EpsilonGreedy(n_arms=n_arms, epsilon=epsilon)
        elif(bandit == "pursuit"):
            self.bandit = Pursuit(n_arms=n_arms, learning_rate=learning_rate)
        elif(bandit == "exp4"):
            self.bandit = EXP4(n_arms=n_arms, n_experts=n_experts, gamma=gamma)
        elif(bandit == "epochgreedy"):
            self.bandit = EpochGreedy(n_arms=n_arms)
        elif(bandit == "thompsonsampling"):
            self.bandit = ThompsonSampling(n_arms=n_arms)
        elif(bandit == "kernelucb"):
            self.bandit = KernelUCB(n_arms=n_arms, n_features=n_features, gamma=gamma, eta=eta, kern=kern)

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
    def __init__(self, bandit, n_arms, n_features, obs, n_experts=4, epsilon=0.1, gamma=0.1, eta=1, learning_rate=0.1, kern=rbf_kernel, mode="cmab"):
        super().__init__(bandit, n_arms, n_experts, n_features, epsilon, gamma, eta, learning_rate, kern)
        
        self.n_arms = n_arms
        self.obs = obs
        self.pastObs = []
        self.rewardHistory = [[] for i in range(n_arms)]

    '''
    Clear the reward history
    '''
    def clearRewardHistory(self):
        self.rewardHistory.clear()
        self.rewardHistory = [[] for i in range(self.n_arms)]

    '''
    Clear observation history
    '''
    def clearContextHistory(self):
        self.pastObs.clear()

    '''
    Generate an ARIMA model for the reward
    Arguments: arm: the arm that the ARIMA model is for
    '''
    def generateRewardARIMA(self, arm):
        # Get the training data
        training_data = np.array(self.rewardHistory[arm], dtype=np.float64)

        # Handle cases where the data is constant
        testValue = training_data[0]
        isConstant = True
        for i in range(1,len(training_data)):
            if(testValue != training_data[i]):
                isConstant = False
        
        if(isConstant is True):
            training_data[(len(training_data)-1)] = training_data[(len(training_data)-1)] + 0.01

        # Generate an ARIMA model with the training data
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
        
        # Obtain the history of the context
        contextHistory = []
        for i in range(len(self.pastObs)):
            contextHistory.append(self.pastObs[i][context][arm])
        
        # Create the ARIMA model based on the training data
        training_data = np.array(contextHistory, dtype=np.float64)

        # Handle cases where the data is constant
        testValue = training_data[0]
        isConstant = True
        for i in range(1,len(training_data)):
            if(testValue != training_data[i]):
                isConstant = False
        
        if(isConstant is True):
            training_data[(len(training_data)-1)] = training_data[(len(training_data)-1)] + 0.01
        
        # Generate an ARIMA model with the training data
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
    def detectRewardAnomaly(self, reward, arima_model=None):
        if(arima_model is None):
            raise ValueError()

        # x: the unmodified reward
        x = [reward]
        
        # y: the arima model's prediction for the reward
        y = arima_model.predict(n_periods=1)
        if(y[0] < 0.0):
            y[0] = 0.0
        elif(y[0] > 1.0):
            y[0] = 1.0

        # Get the L1 Norm difference between x and y
        l1_diff = abs(np.linalg.norm(x, ord=1) - np.linalg.norm(y, ord=1))

        # If the difference in L1 Norms is greater than 0.2 then we have an anomaly
        if(l1_diff > 0.2):
            return y[0]
        
        return x[0]

    '''
    Detect if the context given is anomalous
    Arguments: contextIndex: the index of the context we are examining for anomalies
               context: the specific observed data to examine for anomalies
               arima_model: the arima model to use
    '''
    def detectContextAnomaly(self, contextIndex, context, arima_model=None):
        if(arima_model is None):
            raise ValueError()
        
        # x: the unmodified context
        x = context
        
        # y: the context but with the arima model's prediction value replacing the actual value in the context
        y = []
        prediction = arima_model.predict(n_periods=1)
        for i in range(len(context)):
            if(i == contextIndex):
                y.append(prediction[0])
            else:
                y.append(context[i])
        
        # Get the L1 Norm difference between x and y
        l1_diff = abs(np.linalg.norm(x, ord=1) - np.linalg.norm(y, ord=1))

        # If the difference in L1 Norms is greater than 2, then there is an anomaly
        if(l1_diff > 2):
            return y[contextIndex]
        
        return x[contextIndex]
    
    '''
    Updates the bandit algorithm and the anomaly detection object
    Arguments: reward: the reward for the chosen arm
               obs: the observed data
               action: the chosen arm
    '''
    def update(self, reward, **kwargs):
        super().update(reward, **kwargs)

        self.pastObs.append(self.obs)
        self.obs = kwargs['obs']
        self.chosen_arm = kwargs['action']
        arm_rewards = kwargs['arm_rewards']
        for i in range(self.n_arms):
            self.rewardHistory[i].append(arm_rewards[i])
