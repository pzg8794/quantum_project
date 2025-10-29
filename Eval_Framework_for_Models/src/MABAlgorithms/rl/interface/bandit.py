from abc import ABC, abstractmethod

'''
Multi-Armed Bandit Abstract Class
'''
class MultiArmedBandit(ABC):

    '''
    Select Arm based on bandit algorithm
    '''
    @abstractmethod
    def run(self):
        pass

    '''
    Update bandit weights based on reward from env
    '''
    @abstractmethod
    def update(self, reward):
        pass

'''
Contextual Multi-Armed Bandit Abstract Class
'''
class ContextualMultiArmedBandit(MultiArmedBandit):

    '''
    Select Arm based on provided context from the env
    '''
    @abstractmethod
    def run(self, context=None, **kwargs):
        pass