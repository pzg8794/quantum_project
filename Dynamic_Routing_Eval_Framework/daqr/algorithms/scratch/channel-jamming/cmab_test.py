#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from sklearn.metrics.pairwise import rbf_kernel
from ns3gym import ns3env
from CMAB import CMAB
import numpy as np

parser = argparse.ArgumentParser(description='Start simulation script on/off')
parser.add_argument('--start',
                    type=int,
                    default=1,
                    help='Start ns-3 simulation script 0/1, Default: 1')
parser.add_argument('--iterations',
                    type=int,
                    default=1,
                    help='Number of iterations, Default: 1')
parser.add_argument('--bandit',
                    type=str,
                    default="",
                    help=
                    '''
                    Set to the bandit algorithm you want to use.\n
                    Options: EpsilonGreedy, Pursuit, EXP4, EpochGreedy, KernelUCB, ThompsonSampling
                    ''')
args = parser.parse_args()
startSim = bool(args.start)
iterationNum = int(args.iterations)
banditAlgo = str(args.bandit).lower()

port = 5555
simTime = 300 # seconds
stepTime = 0.1  # seconds
seed = 0
simArgs = {"--simTime": simTime,
           "--testArg": 123}
debug = False

env = ns3env.Ns3Env(port=port, stepTime=stepTime, startSim=startSim, simSeed=seed, simArgs=simArgs, debug=debug)
# simpler:
#env = ns3env.Ns3Env()
env.reset()

ob_space = env.observation_space
ac_space = env.action_space
print("Observation space: ", ob_space,  ob_space.dtype)
print("Action space: ", ac_space, ac_space.dtype)

stepIdx = 0
currIt = 0

arm_count = []
optimal_picks = 0
average_reward = []
exploitation_arm_count = []
hypothesis = []
samples = []
advice = []
reward_history = []
regret_history = []

# Assumptions
num_arms = 8
num_experts = 3
num_features = 8
epsilon = 0.1
gamma = 0.1
eta = 1.0
learning_rate = 0.1
kern = rbf_kernel

'''
Prints the observations in a readable format
Arguments: obs: the observed data
'''
def printObs(obs):
    obsDatarate = obs["datarate"]
    obsThroughput = obs["throughput"]

    print("---datarate: ", obsDatarate)
    print("---throughput: ", obsThroughput)


'''
Generate the hypothesis space's information
Arguments: samples: the samples from past exploration steps
           context: the observed context
'''
def generateHypothesis(samples, context):
    minDistance = context[0][4]
    for i in range(num_arms):
        minDistance = min(minDistance, context[i][4])

    for i in range(len(hypothesis)):
        hypothesis[i] = 0
        for j in range(len(samples)):
            if(samples[j][1] == i and samples[j][0][4] == minDistance):
                hypothesis[i] += samples[j][2]


if __name__ == '__main__':
    try:
        while True:
            print("Start iteration: ", currIt)
            obs = env.reset()

            # Initial Observation
            print("Step: ", stepIdx)
            printObs(obs=obs)

            cmab = CMAB.iCMAB(n_arms=num_arms, n_experts=num_experts, n_features=num_features, 
                            bandit=banditAlgo, epsilon=epsilon, gamma=gamma, eta=eta, kern=kern)

            if(banditAlgo == "exp4"):
                tempArray = []
                for j in range(num_arms):
                    tempArray.append(1.0/num_arms)
                advice.append(tempArray)
                # advice.append([0.1, 0.0, 0.8, 0.1])
                # advice.append([0.0, 0.0, 1.0, 0.0])

            for i in range(num_arms):
                arm_count.append(0)
                average_reward.append(-1)
                if(banditAlgo == "epochgreedy"):
                    exploitation_arm_count.append(0)
                    hypothesis.append(0)

            context = [0] * num_features
            arima_models = []
            data_gathering_step_counter = 10
            while True:
                stepIdx += 1

                # Use the MAB algorithm to pick an arm
                if(banditAlgo == "epochgreedy"):
                    action = cmab.pickArm(context=None, hypothesis=hypothesis)
                elif(banditAlgo == "exp4"):
                    print("---advice: ", advice)
                    action = cmab.pickArm(advice=advice)
                elif(banditAlgo == "thompsonsampling"):
                    action = cmab.pickArm(context=context)
                elif(banditAlgo == "kernelucb"):
                    action = cmab.pickArm(context=context, tround=(stepIdx-1))
                else:
                    action = cmab.pickArm()
                
                if(banditAlgo == "epochgreedy"):
                    print("---exploration action: ", action)
                else:
                    print("---action: ", action)

                # Get the reward for the picked arm and the next step's observation
                obs, reward, done, info = env.step(action)
                context = obs["datarate"]
                
                if (action == -2):
                    continue

                if (reward == -1):
                    continue

                # data_gathering_step_counter -= 1

                optimalArm = np.argmax(obs["datarate"])
                if (action == optimalArm):
                    optimal_picks += 1

                arm_count[action] += 1
                average_reward[action] = ((average_reward[action] * (arm_count[action] - 1)) + reward) / arm_count[action]
                   
                if(banditAlgo == "epochgreedy"):
                    # Add explored arm to the samples list
                    samples.append([context[action], action, reward])
                    generateHypothesis(samples=samples, context=context)
                        
                # elif(banditAlgo == "exp4"):
                #     generateAdvice(context=context)

                print("---reward: ", reward)
                cmab.update(reward=reward, obs=obs, action=action)
                # cmab.update(reward=reward)

                reward_history.append(reward)
                regret = average_reward[np.argmax(average_reward)] - reward
                regret_history.append(regret)

                # f1.write(str(banditAlgo) + "\n")
                # f2.write(str(regret) + "\n")

                # Get the new observation
                print("Step: ", stepIdx)
                printObs(obs=obs)
                # print("---done: ", done)
                # print("---info: ", info)

                if(banditAlgo == "epochgreedy"):
                    # Use the Epoch Algorithm to get an arm
                    # Exploitation Step(s)
                    # Not really implemented due to OpenGym needing to know the exact number of steps
                    # Can still get the arm that the algorithm would exploit multiple times however.
                    action = cmab.pickArm(context=context, hypothesis=hypothesis)
                    print("---exploitation action: ", action)
                    exploitation_arm_count[action] += len(samples)

                # X29
                if done | stepIdx > 529:
                    stepIdx = 0
                    if currIt + 1 < iterationNum:
                        env.reset()
                    break

            currIt += 1
            if currIt == iterationNum:
                break
        
        f1 = open("reward_data.txt", "w")
        f2 = open("regret_data.txt", "w")

        for regret in regret_history:
            f2.write(str(regret) + "\n")

        for reward in reward_history:
            f1.write(str(reward) + "\n")
        
        f1.close()
        f2.close()

    except KeyboardInterrupt:
        print("Ctrl-C -> Exit")
    finally:
        # f1.close()
        # f2.close()
        print()
        print("Final Info")
        print("Arm Count:  " + str(arm_count))
        print("Avg Reward: " + str(average_reward))
        print("Optimal Picks: " + str(optimal_picks))
        if(banditAlgo == "epochgreedy"):
            print(exploitation_arm_count)
        env.close()
        print("Done")