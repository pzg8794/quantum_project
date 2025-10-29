#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from ns3gym import ns3env
import numpy as np
from MABAlgorithms.rl.bandits import KernelUCB
from sklearn.metrics.pairwise import rbf_kernel
from AnomalyDetection.channel_alloc_anomalies import ChannelAllocationAnomalyDetection as channelAllocAnomaly

parser = argparse.ArgumentParser(description='Start simulation script on/off')
parser.add_argument('--start',
                    type=int,
                    default=1,
                    help='Start ns-3 simulation script 0/1, Default: 1')
parser.add_argument('--iterations',
                    type=int,
                    default=1,
                    help='Number of iterations, Default: 1')
args = parser.parse_args()
startSim = bool(args.start)
iterationNum = int(args.iterations)

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

# Assumptions
gamma = 0.1
num_arms = 3
num_features = 1

if __name__ == '__main__':
    try:
        while True:
            print("Start iteration: ", currIt)
            obs = env.reset()

            # Get the intial observation
            print("Step: ", stepIdx)
            obsSNR = obs["SNR"]
            obsRSSI = obs["RSSI"]
            obsNoise = obs["noise"]
            obsThroughput = obs["throughput"]
            obsDistance = obs["distance"]
            obsWidth = obs["channel-width"]
            obsUnoccupied = obs["isUnoccupied"]
            obsOnline = obs["isOnline"]
            obsDetectedIntrusion = obs["detectedIntrusion"]

            print("---SNR: ", obsSNR)
            print("---RSSI: ", obsRSSI)
            print("---noise: ", obsNoise)
            print("---throughput: ", obsThroughput)
            print("---distance: ", obsDistance)
            print("---channel_width: ", obsWidth)
            print("---isUnoccupied: ", obsUnoccupied)
            print("---isOnline: ", obsOnline)
            print("---detectedIntrusion: ", obsDetectedIntrusion)

            # Initialize the KernalUCB Algorithm with the inputted parameters
            kernalAlgo = KernelUCB(n_arms=num_arms, n_features=num_features, gamma=gamma, eta=1.0, kern=rbf_kernel)

            # Initalize the anomaly detection with the inputted parameters
            anomalyDetection = channelAllocAnomaly(n_arms=num_arms)

            for i in range(num_arms):
                arm_count.append(0)
            
            context = np.random.rand(num_arms, num_features)

            while True:
                stepIdx += 1

                for i in range(num_arms):
                    temp = [(obsSNR[i]/100)]
                    for j in range(num_features):
                        context[i][j] = temp[j]

                # Use KernalUCB Algorithm to pick an arm
                action = kernalAlgo.run(context=context, tround=(stepIdx-1))
                arm_count[action] += 1
                print("---action: ", action)

                # Update anomaly detection with the current observation
                anomalyDetection.update(obs=obs,action=action)

                # Get the reward for the picked arm and the observation for the next step
                obs, reward, done, info = env.step(action)

                # Determine if the picked arm has an anomaly
                reward *= anomalyDetection.detectRewardAnomaly()
                reward *= anomalyDetection.detectContextualAnomaly()

                print("---reward: ", reward)

                # Assign the new observations for the next step
                print("Step: ", stepIdx)
                obsSNR = obs["SNR"]
                obsRSSI = obs["RSSI"]
                obsNoise = obs["noise"]
                obsThroughput = obs["throughput"]
                obsDistance = obs["distance"]
                obsWidth = obs["channel-width"]
                obsUnoccupied = obs["isUnoccupied"]
                obsOnline = obs["isOnline"]
                obsDetectedIntrusion = obs["detectedIntrusion"]
                
                print("---SNR: ", obsSNR)
                print("---RSSI: ", obsRSSI)
                print("---noise: ", obsNoise)
                print("---throughput: ", obsThroughput)
                print("---distance: ", obsDistance)
                print("---channel_width", obsWidth)
                print("---isUnoccupied: ", obsUnoccupied)
                print("---isOnline: ", obsOnline)
                print("---detectedIntrusion: ", obsDetectedIntrusion)
                print("---done: ", done)
                print("---info: ", info)

                # Update the KernalUCB algorithm with the resulting reward
                kernalAlgo.update(reward)

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
        print(arm_count)
        env.close()
        print("Done")