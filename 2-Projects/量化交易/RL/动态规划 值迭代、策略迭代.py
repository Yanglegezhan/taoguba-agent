#creat enviroment:

import copy


class CliffwalkEnv:
    def __init__(self, col=12, row=4):
        self.col = col  # 列
        self.row = row  # 行
        # 转移矩阵P[state][action] = [(p,next_state,reward,done)]包含下一个状态和奖励
        self.P = self.createP()

    def createP(self):
        # 初始化
        P = [[[] for j in range(4)] for i in range(self.row * self.col)]
        # 四种动作，change[0]：上，change[1]：下，change[2]：左，change[3]：右。原点（0,0）
        # 定义在左上角
        change = [[0, -1], [0, 1], [-1, 0], [1, 0]]
        for i in range(self.row):
            for j in range(self.col):
                for a in range(4):
                    # 在悬崖边或者目标状态，无法交互，reward为0
                    if i == self.row - 1 and j > 0:
                        P[i * self.col + j][a] = [(1, i * self.col + j, 0, True)]
                        continue
                    # 其他位置
                    next_x = min(self.col - 1, max(0, j + change[a][0]))
                    next_y = min(self.row - 1, max(0, i + change[a][1]))
                    next_state = next_y * self.col + next_x
                    reward = -1
                    done = False
                    # 下一个位置在悬崖或者终点
                    if next_y == self.row - 1 and next_x > 0:
                        done = True
                        if next_x != self.col - 1:  # 下一个位置在悬崖
                            reward = -100
                    P[i * self.col + j][a] = [(1, next_state, reward, done)]
        return P

#策略迭代:

class PolicyIteration:
    def __init__(self, env, theta, gamma):
        self.env = env
        self.theta = theta  # 收敛阈值
        self.gamma = gamma  # 衰减值
        self.v = [0] * self.env.col * self.env.row  # 初始化value为0
        self.pi = [[0.25, 0.25, 0.25, 0.25] for i in range(self.env.col * self.env.row)]  # 初始化均匀分布的随机策略

    def policy_evaluation(self):
        cnt = 1  # 计数
        while 1:
            max_diff = 0
            new_v = [0] * self.env.col * self.env.row
            for s in range(self.env.col * self.env.row):
                qsa_list = []  # 计算s状态下所有action value q(s,a)值
                for a in range(4):
                    qsa = 0
                    for res in self.env.P[s][a]:
                        p, next_state, r, done = res
                        qsa += p * (r + self.gamma * self.v[next_state] * (1-done))
                        # 奖励与下一个状态有关，所以需要和状态转移概率相乘
                    qsa_list.append(self.pi[s][a] * qsa)
                new_v[s] = sum(qsa_list)
                max_diff = max(max_diff, abs(new_v[s] - self.v[s]))
            self.v = new_v
            if max_diff < self.theta:
                break  # 满足收敛条件，退出评估
            cnt += 1
        print("策略评估进行%d轮后完成" % cnt)
    def policy_imporvment(self):
        for s in range(self.env.row * self.env.col):
            qsa_list = []
            for a in range(4):
                qsa = 0
                for res in self.env.P[s][a]:
                    p, next_value, r, done = res
                    qsa += p * (r + self.gamma * self.v[next_value] * (1-done))
                qsa_list.append(qsa)
            maxq = max(qsa_list)
            cntq = qsa_list.count(maxq)  # 计算有几个动作达到最大的q
            # 让这些动作均分概率
            self.pi[s] = [1/cntq if q == maxq else 0 for q in qsa_list]
        print('policy improvment complete!')
        return self.pi

    def policy_iteration(self):
        while 1:
            self.policy_evaluation()
            old_pi = copy.deepcopy(self.pi)
            new_pi = self.policy_imporvment()
            if old_pi == new_pi: break



def print_agent(agent, action_meaning, disaster=[], end=[]):
    print("状态价值")
    for i in range(agent.env.row):
        for j in range(agent.env.col):
            print("%6.6s" % ('%.3f' % agent.v[i * agent.env.col + j]), end='')
        print()
    print('策略：')
    for i in range(agent.env.row):
        for j in range(agent.env.col):
            if (i * agent.env.col + j) in disaster:
                print('****', end='')
            elif (i * agent.env.col + j) in end:
                print('EEEE', end='')
            else:
                a = agent.pi[i * agent.env.col + j]
                pi_str = ''
                for k in range(len(action_meaning)):
                    pi_str += action_meaning[k] if a[k] > 0 else 'o'
                print(pi_str,end='')
            print()


'''env = CliffwalkEnv()
action_meaning = ['^', 'v', '<', '>']
theta = 0.001
gamma = 0.9
agent = PolicyIteration(env,theta,gamma)
agent.policy_iteration()
print_agent(agent, action_meaning, list(range(37, 47)), [47])
'''
class ValueIteration():
    def __init__(self, env, theta, gamma):
        self.env = env
        self.v = [0] * self.env.col * self.env.row
        self.theta = theta
        self.gamma = gamma
        self.pi = [None for i in range(self.env.col * self.env.row)]

    def value_iteration(self):
        cnt = 0
        while 1:
            max_diff = 0  # 最大变化值
            new_v = [0] * self.env.col * self.env.row
            for s in range(self.env.col * self.env.row):
                qsa_list = []  # 储存在s状态下所有q值
                for a in range(4):
                    qsa = 0
                    for res in self.env.P[s][a]:
                        p, next_state, r, done = res
                        qsa += p * (r + self.gamma * self.v[next_state] * (1-done))  # p：在s下采取a后转移到下一个状态的概率
                    # 下面两行代码是策略迭代和值迭代的区别
                    qsa_list.append(qsa)
                new_v[s] = max(qsa_list)
                max_diff = max(max_diff, abs(new_v[s]-self.v[s]))
            self.v = new_v
            if max_diff < self.theta:
                break
            cnt += 1
        print("价值迭代一共%d轮" % cnt)
        self.get_policy()

    def get_policy(self):  # 根据价值导出一个贪婪策略
        for s in range(self.env.row * self.env.col):
            qsa_list = []
            for a in range(4):
                qsa = 0
                for res in self.env.P[s][a]:
                    p, next_state, r, done = res
                    qsa += p * (r + self.gamma * self.v[next_state] * (1 - done))
                qsa_list.append(qsa)
            maxq = max(qsa_list)
            cntq = qsa_list.count(maxq)
            # 让这些动作均分概率
            self.pi[s] = [1/cntq if q == maxq else 0 for q in qsa_list]

env = CliffwalkEnv()
action_meaning = ['^', 'v', '<', '>']
theta = 0.001
gamma = 0.9
agent = ValueIteration(env, theta, gamma)
agent.value_iteration()
print_agent(agent, action_meaning, list(range(37, 47)), [47])


