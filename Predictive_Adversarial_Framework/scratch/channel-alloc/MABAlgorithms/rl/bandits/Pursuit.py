import numpy as np
from ..interface.bandit import MultiArmedBandit

'''
Class for Pursuit Bandit Algorithm
Link - 
'''
class Pursuit(MultiArmedBandit):
    '''
    Initialize Algorithm
    Arguements - data : data set containing the arms
        learning_rate : a float (0,1) that affects how probabilities are changed
    '''
    def __init__(self, n_arms, learning_rate=0.1):
        self.n_arms = n_arms
        self.learning_rate = learning_rate
        self.probabilities = []
        self.rewardHistory = []
        self.expectedRewards = []
        self.actualExpectedReward = 0
        self.maxExpectedReward = 0
        for i in range(self.n_arms):
            self.probabilities.append(1/n_arms)
            self.rewardHistory.append([])
            self.expectedRewards.append(0)

    '''
    Pick the best arm based on stored proabilities
    '''
    def run(self):
        # Choose an arm based on stored probabilities
        a_t = np.random.choice(self.n_arms, p=self.probabilities)
        self.lastChoice = a_t
        return a_t

    '''
    Update the algorithm based on the reward received
    Update the proababilites of picking each arm
    '''
    def update(self, reward):
        self.rewardHistory[self.lastChoice].append(reward)
        self.actualExpectedReward += reward

        for i in range(self.n_arms):
            if(not len(self.rewardHistory[i]) == 0):
                self.expectedRewards[i] = np.sum(self.rewardHistory[i])/len(self.rewardHistory[i])

        # Predict the best arm to be chosen based on current samples
        predictedBestArm = np.argmax(self.expectedRewards)
        self.maxExpectedReward += self.expectedRewards[predictedBestArm]

        # For writing regret per step to a file
        # maxExpectedReward = self.expectedRewards[predictedBestArm]
        # regret = maxExpectedReward - recievedReward
        # f = open("Pursuit.txt", "a")
        # f.write("%f\n" %(regret))
        # f.close()
            
        # Update probabilities
        for i in range(len(self.probabilities)):
                
            # If arm is the predicted best arm, make it more likely to be chosen next time
            if(i == predictedBestArm):
                self.probabilities[i] = self.probabilities[i] + self.learning_rate * (1-self.probabilities[i])

            # If arm is not the predicted best arm, make it less likely to be chosen next time
            else:
                self.probabilities[i] = self.probabilities[i] + self.learning_rate * (0-self.probabilities[i])
                
    '''
    Final print statements to be called after algorithm is finished
    Prints the regret
    Prints the regret bound
    Arguements - steps : the total amount of steps done by the algorithm
    '''
    def finalPrints(self, steps):
        # Calculate regret
        # print("The maximum expected reward is: %f" %(self.maxExpectedReward))
        # print("The actual expected reward received is: %f" %(self.actualExpectedReward))
        regret = self.maxExpectedReward - self.actualExpectedReward
        print("The regret is: %f" %(regret))

        # Calculate regret bound
        regretBound = np.log2(steps)
        print("The regret bound is: %f" %(regretBound))