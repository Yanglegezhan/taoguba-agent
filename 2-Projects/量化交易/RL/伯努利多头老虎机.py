import numpy as np
import matplotlib.pyplot as plt

class BernoulliBandit:
    def __init__(self,K):
        '''伯努利老虎机，输入K表示拉杆个数'''
        self.probs = np.random.uniform(size=K)#获得奖励概率

        self.best_idx = np.argmax(self.probs)#获奖概率最大的拉杆
        self.best_probs = self.probs[self.best_idx]#最大获奖率
        self.K = K

    def step(self,k):
        #选择k号拉杆，根据获奖概率返回0/1
        if np.random.rand() < self.probs[k]:
            return 1
        else:
            return 0
#np.random.seed(1)

K=10
bandit_10_arm = BernoulliBandit(K)
print("随机生成了一个%d臂老虎机" % K)
print("获奖最大的拉杆为%d，获奖概率为%.4f" %(bandit_10_arm.best_idx,bandit_10_arm.best_probs))

class Solver:

    def __init__(self,bandit):
        self.bandit = bandit
        self.counts = np.zeros(self.bandit.K)#每根拉杆的尝试次数
        self.regret = 0.#记录当前后悔
        self.actions = []#列表，记录每一步的动作
        self.regrets = []#列表，记录每一步的累计后悔值

    def update_regret(self,k):
        #记录累计后悔并保存，k为本次行动选择拉杆的编号
        self.regret +=self.bandit.best_probs - self.bandit.probs[k]
        self.regrets.append(self.regret)

    def run_one_step(self):
        #返回当前动作选择哪一根拉杆，由每一个具体策略实现
        raise NotImplementedError

    def run(self,num_steps):
        #运行一定次数，num_steps为总次数
        for _ in range(num_steps):
            k = self.run_one_step()
            self.counts[k] +=1
            self.actions.append(k)
            self.update_regret(k)

class EpsilonGreedy(Solver):
    def __init__(self,bandit,epsilon=0.01,init_prob=1.0):
        super(EpsilonGreedy,self).__init__(bandit)
        self.epsilon=epsilon

        self.estimates = np.array([init_prob] * self.bandit.K)

    def run_one_step(self):
        if np.random.random() < self.epsilon:
            k = np.random.randint(0,self.bandit.K)
        else:
            k = np.argmax(self.estimates)
        r = self.bandit.step(k)
        self.estimates[k] += 1. / (self.counts[k] + 1) * (r - self.estimates[k])
        return k


def plot_results(solvers,solver_names):

    for idx , solver in enumerate(solvers):
        time_list = range(len(solver.regrets))
        plt.plot(time_list,solver.regrets,label=solver_names[idx])
    plt.xlabel('Time steps')
    plt.ylabel('Cumulative regrets')
    plt.title('%d-armed bandit' % solvers[0].bandit.K)
    plt.legend()
    plt.show()
np.random.seed(1)
epsilon_greed_solver = EpsilonGreedy(bandit_10_arm,epsilon=0.01)
epsilon_greed_solver.run(5000)
print('累计后悔：',epsilon_greed_solver.regret)
plot_results([epsilon_greed_solver],["EpsilonGreedy"])