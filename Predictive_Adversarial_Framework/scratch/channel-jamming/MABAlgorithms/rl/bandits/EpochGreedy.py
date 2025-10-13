import numpy as np
from ..interface.bandit import ContextualMultiArmedBandit

'''
Class for Epoch Greedy Bandit Algorithm
Link - https://doi.org/10.1145/1772690.1772758
'''
class EpochGreedy(ContextualMultiArmedBandit):
    '''
    Initializes the Epoch Greedy algorithm
    Arguements - data : data set containing the arms
    '''
    def __init__(self, n_arms):
        self.banditAlgo = "epochgreedy"
        self.n_arms = n_arms
        self.rewardHistory = []
        self.actualExpectedReward = 0
        self.maxExpectedReward = 0

        for i in range(self.n_arms):
            self.rewardHistory.append([])
    
    '''
    Picks the arm depending on the context
    Arguements - context : context for this scenario
        hypothesis : the hypothesis vector used to pick the best arm
    '''
    def run(self, context=None, **kwargs):
        self.context = context
        self.hypothesis = kwargs['hypothesis']

        if(context==None):
            # Exploration Step
            # Choose arm uniformly at random
            a_t = np.random.choice(self.n_arms)
        else:
            # Exploitation Step(s)
            # Pick best arm from hypothesis
            a_t = np.argmax(list(self.hypothesis[i] for i in range(len(self.hypothesis))))
            
        self.lastChoice = a_t
        return a_t

    '''
    Updates the algorithm with the given reward
    Arguements - reward : reward recieved from arm
    '''
    def update(self, reward):
        self.rewardHistory[self.lastChoice].append(reward)
        self.actualExpectedReward += reward

        estimatedMeans = []
        for i in range(self.n_arms):
            estimatedMeans.append(0)

        for i in range(self.n_arms):
            if(not(len(self.rewardHistory[i]) == 0)):
                estimatedMeans[i] = np.sum(self.rewardHistory[i])/len(self.rewardHistory[i])
        self.maxExpectedReward += estimatedMeans[np.argmax(estimatedMeans)]

        # For writing regret per step to a file
        # maxReward = np.sum(self.rewardHistory[arm])/len(self.rewardHistory[arm])
        # regret = maxReward - reward
        # f = open("EpochGreedy.txt", "a")
        # f.write("%f\n" %(regret))
        # f.close()

    '''
    Final print statements to be called after algorithm is finished
    Prints the final best arm at the end of the algorithm
    Prints the regret
    Prints the regret bound
    Arguments - T : total number of steps
        hypothesis : hypothesis vector
        delta : variable used to calculate regret bound
    '''
    def finalPrints(self, T, hypothesis, delta=0.01):
        # Calculate regret
        # print("The maximum expected reward is: %f" %(maxExpectedReward))
        # print("The actual expected reward received is: %f" %(self.actualExpectedReward))
        regret = self.maxExpectedReward - self.actualExpectedReward
        print("The regret is: %f" %(regret))

        # Calculate regret bound
        regretBound = pow((self.n_arms * np.log(len(hypothesis)/delta)), (1/3)) * pow(T, (2/3))
        print("The regret bound is: %f" %(regretBound))