#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from sklearn.metrics.pairwise import rbf_kernel
import numpy as np
from ns3gym import ns3env
from CMAB.CMAB import iCMAB

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
simTime = 20 # seconds
stepTime = 0.5  # seconds
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
optimal_arm_count = 0
num_times_arm_optimal = []
exploitation_arm_count = []
hypothesis = []
samples = []
advice = []
reward_history = []
regret_history = []
contextual_bandits = ["epochgreedy", "kernelucb", "exp4"]
arima_models = []
prev_free_arm = 0
data_gathering_step_counter = 10
netThroughput = 0

# Assumptions
num_arms = 5
num_experts = 5
num_features = 4
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
    obsSNR = obs["SNR"]
    obsRSSI = obs["RSSI"]
    obsNoise = obs["noise"]
    obsThroughput = obs["throughput"]
    obsDistance = obs["distance"]
    obsWidth = obs["channel-width"]
    obsUnoccupied = obs["isUnoccupied"]
    obsOnline = obs["isOnline"]

    print("---SNR: ", obsSNR)
    print("---RSSI: ", obsRSSI)
    print("---noise: ", obsNoise)
    print("---throughput: ", obsThroughput)
    print("---distance: ", obsDistance)
    print("---channel_width", obsWidth)
    print("---isUnoccupied: ", obsUnoccupied)
    print("---isOnline: ", obsOnline)

'''
Generate the hypothesis space's information
Arguments: samples: the samples from past exploration steps
           context: the observed context
'''
def generateHypothesis(samples, context):
    # Find the maximum throughput of the context
    maxThroughput = context[0][3]
    for i in range(num_arms):
        maxThroughput = max(maxThroughput, context[i][4])

    # Generate hypothesis space based on the maximum throughput
    for i in range(len(hypothesis)):
        hypothesis[i] = 0
        for j in range(len(samples)):
            if(samples[j][1] == i and samples[j][0][3] >= maxThroughput):
                hypothesis[i] += samples[j][2]

'''
Generate the advice vectors for the experts
Arguments: context: the observed context
'''
def generateAdvice(context):
    # *****************************************************************
    # Look through the context for variables to base advice off of
    # *****************************************************************
    maxSNR = context[0][0]
    maxRSSI = context[0][1]
    minNoise = context[0][2]
    maxThroughput = context[0][3]

    countOfMaxSNR = 0
    countOfMaxRSSI = 0
    countOfMinNoise = 0
    countOfMaxThroughput = 0

    # Get the max SNR, max RSSI, and min noise
    for i in range(num_arms):
        maxSNR = max(maxSNR, context[i][0])
        if(context[i][1] != 0):
            maxRSSI = max(maxRSSI, context[i][1])
        minNoise = min(minNoise, context[i][2])
        maxThroughput = max(maxThroughput, context[i][3])

    # Get the number of arms that match the variables
    for i in range(num_arms):
        if(context[i][0] == maxSNR):
            countOfMaxSNR += 1
        if(context[i][1] == maxRSSI):
            countOfMaxRSSI += 1
        if(context[i][2] == minNoise):
            countOfMinNoise += 1
        if(context[i][3] == maxThroughput):
            countOfMaxThroughput += 1

    # **********************************************************
    # Create the advice vectors for the next step
    # **********************************************************

    # Create advice for the expert that just picks the arm with the highest SNR
    tempArray = []
    for i in range(num_arms):
        if(context[i][0] == maxSNR):
            tempArray.append(1.0/countOfMaxSNR)
        else:
            tempArray.append(0)
    advice[1] = tempArray

    # Create advice for the expert that picks the arms with the highest RSSI
    tempArray = []
    for i in range(num_arms):
        if(context[i][1] == maxRSSI):
            tempArray.append(1.0/countOfMaxRSSI)
        else:
            tempArray.append(0)
    advice[2] = tempArray

    # Create advice for the expert that picks the arms with the lowest noise
    tempArray = []
    for i in range(num_arms):
        if(context[i][2] == minNoise):
            tempArray.append(1.0/countOfMinNoise)
        else:
            tempArray.append(0)
    advice[3] = tempArray

    # Create advice for the expert that picks the arms with the highest throughput
    tempArray = []
    for i in range(num_arms):
        if(context[i][3] == maxThroughput):
            tempArray.append(1.0/countOfMaxThroughput)
        else:
            tempArray.append(0)
    advice[4] = tempArray

if __name__ == '__main__':
    try:
        # f1 = open("reward_data.txt", "w")
        # f1.close()
        # f2 = open("regret_data.txt", "w")
        # f2.close()
        # f3 = open("throughput1.txt", "w")
        # f3.close()
        # f4 = open("throughput2.txt", "w")
        # f4.close()
        # f5 = open("throughput3.txt", "w")
        # f5.close()
        # f6 = open("throughput4.txt", "w")
        # f6.close()
        # f7 = open("throughput5.txt", "w")
        # f7.close()
        while True:
            print("Start iteration: ", currIt)
            obs = env.reset()

            # Initial Observation
            print("Step: ", stepIdx)
            printObs(obs=obs)

            icmab = iCMAB(n_arms=num_arms, n_experts=num_experts, n_features=num_features, bandit=banditAlgo, obs=obs,
                        epsilon=epsilon, gamma=gamma, eta=eta, kern=kern)

            if(banditAlgo == "exp4"):
                for i in range(num_experts):
                    tempArray = []
                    for j in range(num_arms):
                        tempArray.append(1.0/num_arms)
                    advice.append(tempArray)

            for i in range(num_arms):
                arm_count.append(0)
                num_times_arm_optimal.append(0)
                if(banditAlgo == "epochgreedy"):
                    exploitation_arm_count.append(0)
                    hypothesis.append(0)

            for i in range(num_arms):
                if(obs["isUnoccupied"][i] == 1):
                    prev_free_arm = i
            
            # f1 = open("reward_data.txt", "a")
            # f2 = open("regret_data.txt", "a")
            # f3 = open("throughput1.txt", "a")
            # f4 = open("throughput2.txt", "a")
            # f5 = open("throughput3.txt", "a")
            # f6 = open("throughput4.txt", "a")
            # f7 = open("throughput5.txt", "a")

            while True:
                stepIdx += 1

                # Get the contexts
                # Non-contextual bandits would only see the first context for each arm
                # This is because the first context is the context that is used to generate the reward
                context = []
                for i in range(num_arms):
                    context.append([obs["SNR"][i], 
                                    obs["RSSI"][i], 
                                    obs["noise"][i], 
                                    obs["throughput"][i]])
                    
                rewards = []
                for i in range(num_arms):
                    rewards.append(obs["SNR"][i]/100.0)

                current_free_arm = 0
                best_arm = 0
                for i in range(num_arms):
                    if(obs["isUnoccupied"][i] == 1):
                        best_arm = i
                        current_free_arm = i

                # print(data_gathering_step_counter)
                
                # Check if the current free arm is not the same as the last
                if(current_free_arm != prev_free_arm):
                    data_gathering_step_counter = 10
                    prev_free_arm = current_free_arm
                    icmab.clearContextHistory()
                    icmab.clearRewardHistory()
                    arima_models.clear()

                # Generate ARIMA models once 10 steps have passed
                if(data_gathering_step_counter == 0):
                    for i in range(num_arms):
                        reward_arima_model = icmab.generateRewardARIMA(arm=i)
                        snr_arima_model = icmab.generateContextARIMA(arm=i, context="SNR")
                        rssi_arima_model = icmab.generateContextARIMA(arm=i, context="RSSI")
                        noise_arima_model = icmab.generateContextARIMA(arm=i, context="noise")
                        throughput_arima_model = icmab.generateContextARIMA(arm=i, context="throughput")
                        arima_models.append([snr_arima_model,
                                             rssi_arima_model,
                                             noise_arima_model,
                                             throughput_arima_model,
                                             reward_arima_model])
                
                # Handle contextual anomalies
                if(data_gathering_step_counter <= 0):    
                    for i in range(num_arms):
                        for j in range(num_features):
                            context_arima = arima_models[i][j]

                            contextPred = icmab.detectContextAnomaly(contextIndex=j, context=context[i], arima_model=context_arima)
                            # print("arm ", i)
                            # print("context ", j)
                            # print(contextPred)
                            context_arima.update(contextPred)
                            context[i][j] = contextPred
                
                for i in range(num_arms):
                    netThroughput += context[i][3]

                # f3.write(str(context[0][3]) + "\n")
                # f4.write(str(context[1][3]) + "\n")
                # f5.write(str(context[2][3]) + "\n")
                # f6.write(str(context[3][3]) + "\n")
                # f7.write(str(context[4][3]) + "\n")

                if(banditAlgo == "exp4"):
                    generateAdvice(context=context)

                # Use the MAB algorithm to pick an arm
                if(banditAlgo == "epochgreedy"):
                    action = icmab.pickArm(context=None, hypothesis=hypothesis)
                elif(banditAlgo == "exp4"):
                    print("---advice: ", advice)
                    action = icmab.pickArm(advice=advice)
                elif(banditAlgo == "thompsonsampling"):
                    action = icmab.pickArm(context=context)
                elif(banditAlgo == "kernelucb"):
                    action = icmab.pickArm(context=context, tround=(stepIdx-1))
                else:
                    action = icmab.pickArm()
                
                arm_count[action] += 1
                
                if(banditAlgo == "epochgreedy"):
                    print("---exploration action: ", action)
                else:
                    print("---action: ", action)

                # Get the reward for the picked arm and the next step's observation
                obs, reward, done, info = env.step(action)

                # Handle reward anomalies
                if(data_gathering_step_counter <= 0):
                    for i in range(num_arms):
                        reward_arima = arima_models[i][num_features]

                        rewardPred = icmab.detectRewardAnomaly(reward=rewards[i], arima_model=reward_arima)
                    
                        reward_arima.update(rewardPred)
                        rewards[i] = rewardPred
                    reward = rewards[action]
                   
                if(banditAlgo == "epochgreedy"):
                    # Add explored arm to the samples list
                    samples.append([context[action], action, reward])
                    generateHypothesis(samples=samples, context=context)

                print("---reward: ", reward)
                icmab.update(reward=reward, obs=obs, action=action, arm_rewards=rewards)

                num_times_arm_optimal[best_arm] += 1
                reward_history.append(reward)
                regret = (rewards[best_arm]) - reward
                regret_history.append(regret)
                avg_regret = np.sum(regret_history)/len(regret_history)
                if(action == best_arm):
                    optimal_arm_count += 1

                # f1.write(str(np.sum(reward_history)) + "\n")
                # f2.write(str(avg_regret) + "\n")

                data_gathering_step_counter -= 1

                # Get the new observation
                print("Step: ", stepIdx)
                printObs(obs=obs)
                print("---done: ", done)
                print("---info: ", info)

                # Use the Epoch Algorithm to get an arm
                # Exploitation Step(s)
                # Not really implemented due to OpenGym needing to know the exact number of steps
                # Can still get the arm that the algorithm would exploit multiple times however.
                if(banditAlgo == "epochgreedy"):
                    num_times_arm_optimal[best_arm] += len(samples)
                    action = icmab.pickArm(context=context, hypothesis=hypothesis)
                    if(action == best_arm):
                        optimal_arm_count += len(samples)
                    print("---exploitation action: ", action)
                    exploitation_arm_count[action] += len(samples)

                if done:
                    stepIdx = 0
                    if currIt + 1 < iterationNum:
                        env.reset()
                    break

            currIt += 1
            if currIt == iterationNum:
                break

    except KeyboardInterrupt:
        print("Ctrl-C -> Exit")
    finally:
        # f1.close()
        # f2.close()
        # f3.close()
        # f4.close()
        # f5.close()
        # f6.close()
        # f7.close()
        print(arm_count)
        if(banditAlgo == "epochgreedy"):
            print(exploitation_arm_count)
        print(num_times_arm_optimal)
        print(optimal_arm_count)
        print(netThroughput)
        env.close()
        print("Done")