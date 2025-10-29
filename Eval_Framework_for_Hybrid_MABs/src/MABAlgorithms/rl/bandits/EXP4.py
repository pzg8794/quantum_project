import numpy as np
from ..interface.bandit import ContextualMultiArmedBandit

'''
Class for EXP4 Algorithm for Adversarial Bandits
Link - https://doi.org/10.1137/S0097539701398375
'''
class EXP4(ContextualMultiArmedBandit):
    '''
    Initalize the Algorithm
    Arguements - data : data set containing the arms
        advice : advice vectors hardcoded in for demo purposes
    '''
    def __init__(self, n_arms, n_experts, gamma=0.1):
        self.n_arms = n_arms
        self.n_experts = n_experts
        self.gamma = gamma
        self.weights = []
        self.cumulativeExpectedRewards = []
        self.estimatedExpectedRewards = []
        self.probabilities = []
        self.expectedRewards = []
        self.actualExpectedReward = 0
        self.maxExpectedReward = 0

        for i in range(self.n_arms):
            self.probabilities.append(0)
            self.expectedRewards.append(0)

        for i in range(self.n_experts):
            self.weights.append(1)
            self.cumulativeExpectedRewards.append(0)
            self.estimatedExpectedRewards.append(0)

    '''
    Pick the best arm based on weighted probabilities using advice vectors
    Arguements - context : context used to generate advice (not implemented for demo purposes)
        gamma : a float (0,1] used to calculate weighted probabilities
    '''
    def run(self, context=None, **kwargs):
        self.context = context
        self.advice = kwargs['advice']

        # Calculates a weighted probability for each arm using every expert's advice
        sumOfWeights = np.sum(self.weights)
        for j in range(self.n_arms):
            weightedProbability = 0
            for i in range(self.n_experts):
                weightedProbability += (self.weights[i]*self.advice[i][j])/sumOfWeights
            self.probabilities[j] = (1-self.gamma) * weightedProbability + (self.gamma/self.n_arms)

        # Picks an arm based on the weighted probabilities
        a_t = np.random.choice(self.n_arms, p=self.probabilities)
        self.lastChoice = a_t
        return a_t

    '''
    Update the algorithm with the reward received
    Update the weights of each advice vector
    '''
    def update(self, reward):
        # Gets an estimated reward for the arm
        self.expectedRewards[self.lastChoice] = reward/self.probabilities[self.lastChoice]
        self.actualExpectedReward += reward/self.probabilities[self.lastChoice]

        # Update weights of each expert
        for i in range(len(self.weights)):
            self.estimatedExpectedRewards[i] = np.dot(self.advice[i], self.expectedRewards)
            self.cumulativeExpectedRewards[i] += self.estimatedExpectedRewards[i]
            self.weights[i] = self.weights[i]*np.exp(((self.gamma*self.estimatedExpectedRewards[i])/self.n_arms))
        
        # For writing regret per step to a file
        # maxReward = self.estimatedExpectedRewards[np.argmax(self.estimatedExpectedRewards)]
        # regret = maxReward - (receivedReward/self.probabilities[a_t])
        # f = open("EXP4.txt", "a")
        # f.write("%f\n" %(regret))
        # f.close()

    '''
    Final print statements to be called after algorithm is finished
    Prints the regret
    Prints the regret bound
    Arguements - steps : the number of steps the algorithm has done
    '''
    def finalPrints(self, steps):
        # Calculate regret
        maxExpectedReward = self.cumulativeExpectedRewards[np.argmax(self.cumulativeExpectedRewards)]
        # print("The maximum expected reward is: %f" %(maxExpectedReward))
        # print("The actual expected reward received is: %f" %(self.actualExpectedReward))
        regret = maxExpectedReward - self.actualExpectedReward
        print("The regret is: %f" %(regret))

        # Calculate regret bound
        regretBound = np.sqrt(steps*self.n_arms*np.log(len(self.advice)))
        print("The regret bound is: %f" %(regretBound))