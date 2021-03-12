import sys
import csv
import math
import time
import os.path
import maxflow

import numpy as np
import pandas
import xlrd
from pulp import *

use_cplex=False


production_lower = 3300000*.97
production_upper = 3300000
extraxtion_upper = 10000000000000
discount_rate = .15

objective = 'NPVnDist'

'''capMatrix=np.array(pandas.read_csv('capacity.csv',header=None))

for c in capMatrix:
    if c[0]==0:
        extraxtion_upper.append(c[3])
    else:
        production_upper.append(c[3])
        production_lower.append(c[3]*.97)'''


B=np.array(pandas.read_csv('mclaughlin.blocks',header=None,sep=" "))

len_b=len(B)

'''
prec=[]
prec1=[]
file = open("zuck_medium.prec", "r")
for line in file:
    fields = line.split(",")
    prec1 = []
    for j in range(0, len(fields)):
        prec1.append(int(fields[j]))
    prec.append(prec1)'''
prec=[]
file = open("mclaughlin.prec","r")
for line in file:
    fields = line.split(" ")
    prec1=[]
    for j in range(0,len(fields)):
        prec1.append(float(fields[j]))
    prec.append(prec1)
'''prec.fillna(0,inplace=True)
prec[:0]=prec[:0].astype'''
del file
print(sys.getsizeof(prec))

'''def split_list(prec):
    half = len(prec)//2
    return prec[:half], prec[half:]

B1, C1 = split_list(prec)

if not os.path.isfile('file.txt'):
    file = open("file.txt","w")

    for p in B1:
        i=int(p[0])
        if not int(p[1])==0:
            for j in p[2:int(p[1])+2]:
                r = str(i) + " " + str(int(j)) + '\n'
                file.write(r)
                if i% 100 == 0 :
                    print(i)

    for p in C1:
        i=int(p[0])
        if not int(p[1])==0:
            for j in p[2:int(p[1])+2]:
                r =  str(i) + " " + str(int(j)) + '\n'
                file.write(r)
                if i% 100 == 0 :
                    print(i)
    file.close()
del B1
del C1
pr_arcs = []

file = open("file.txt","r")
for line in file:
    #print(line)
    row = line.split(" ")
    pr_arcs.append([int(float(row[0])), int(float(row[1]))])
file.close()
print("file closed...")
del file'''
a_v_c=[]
for i in range(0, len_b):
    if B[i,4]>0:
        a_v_c.append([int(i),float(B[i,4]),0])
    else:
        a_v_c.append([int(i),0,-float(B[i,4])])

# Tonnage Calculation
tonmat=np.array(pandas.read_csv('tonn.csv',header=None))
Tonnage = B[:,5]
Rock=np.zeros(len_b)
for row in tonmat:
    Rock[int(row[0])]=row[2]

del B
B=[]

last_year=False
results_bucket={}
pr_range = []

import gurobipy as gp
from gurobipy import GRB



def sche_opti_g(B, prec, blocks, lower, upper, tonnage, pit_ton):
    print(len(blocks))
    model=gp.Model("hue") #create model
    x=model.addVars(range(len_b),vtype=GRB.BINARY)
    a=time.time()
    for i in blocks:
        if 0 != prec[i][1]:
            for j in range(0, int(prec[i][1])):
                model.addConstr(x[prec[i][j+2]] - x[i] >= 0, "")
    print('modeling prec take',time.time()-a,'secs')
    obj=gp.quicksum(x[i] * (a_v_c[i][1]-a_v_c[i][2]) for i in blocks)
    model.setObjective(obj,GRB.MAXIMIZE)

    
    
    model.addConstr(gp.quicksum(Rock[i] * x[i] for i in blocks) <= upper, "upper")
    #model.addConstr(gp.quicksum(Rock[i]*tonnage[i] * x[i] for i in blocks) >= lower, "")
    #model.addConstr(gp.quicksum(tonnage[i] * x[i] for i in blocks) <= pit_ton, "")
    model.setParam("TimeLimit", 1500.0)
    model.optimize()
    res = []
    tonn = 0
    tton = 0
    for b in blocks:
        if x[b].x:
            res.append(b)
            tonn += Rock[b]
            tton += tonnage[b]
    
    # print('mini pit tonnage',tonn,tton)
    # print(res)
    return (tton, tonn, res, obj.getValue())

def sche_opti(B, prec, blocks, lower, upper, tonnage, pit_ton):
    # print(upper,lower)
    print('pulp',len(blocks))
    prob = LpProblem("Hue", LpMaximize)

    x = LpVariable.dicts("x", blocks, 0, 1, LpInteger)
    prob += lpSum([x[i] * (a_v_c[i][1]-a_v_c[i][2]) for i in blocks]), ""

   # Precedence
    for i in blocks:
        if 0 != prec[i][1]:
            for j in range(0, int(prec[i][1])):
                if prec[i][j+2] in blocks:
                    prob += x[prec[i][j+2]] - x[i] >= 0, ""

    prob += sum(Rock[i] * x[i] for i in blocks) <= upper, ""
    #prob += sum(tonnage[i] * x[i] for i in blocks) <= pit_ton, ""

    #try:
    print('pulp modeled')
    prob.solve(CPLEX(path=None, keepFiles=0, mip=1, msg=0, options=['set mip tolerances mipgap 0.01'], timeLimit=7200))
    #except:
    #prob.solve(GUROBI())
    #if LpStatus[prob.status]=='Infeasible':
        #print(lower, upper, pit_ton)
        #return(sche_opti(B, prec, blocks, lower, upper, tonnage, pit_ton,True))
    print("Status:", LpStatus[prob.status])
    #print(value(prob.objective))
    res = []
    tonn = 0
    tton = 0
    for i in blocks:
        if x[i].value() == 1:
            res.append(i)
            tonn += Rock[i]
            tton += tonnage[i]
    # print('mini pit tonnage',tonn,tton)
    # print(res)
    return (tton, tonn, res, value(prob.objective))


def LPHeuristic(coal_ton_pre, y, production_lower, production_upper, tbase_tonnage):
    lower_expected = coal_ton_pre+production_lower
    upper_expected = coal_ton_pre+production_upper
    upper_t_expected = tbase_tonnage+extraxtion_upper
    #print('uper t expected',upper_t_expected)
    # print('bet',round(lower_expected),round(upper_expected))
    ceil=results_bucket[0]
    floor=results[y-1]
    fot=0
    ftt=0
    for i in range(y+1):
        fot += results[i-1]['ore_ton']
        ftt += results[i-1]['total_ton']
    floor={'ore_ton':fot,'total_ton':ftt,'blocks':floor['blocks']}
    for i_key in results_bucket:
        if upper_t_expected >= results_bucket[i_key]['total_ton'] and results_bucket[i_key]['ore_ton']<=lower_expected-2*production_lower:
            if floor['ore_ton']<=results_bucket[i_key]['ore_ton'] and (set(results[y-1]['blocks'])-set(results_bucket[i_key]['blocks']))==set():
                floor=results_bucket[i_key]
        if results_bucket[i_key]['ore_ton']>=upper_expected+4*production_upper and not (set(results[y-1]['blocks'])-set(results_bucket[i_key]['blocks'])):
            if ceil['ore_ton']>=results_bucket[i_key]['ore_ton']:
                ceil=results_bucket[i_key]
    # print('floor_ton',floor[0])
    # print('ciel_ton',ceil[0])
    '''floorb=list(set(results[y-1]['blocks']).union(set(floor['blocks'])))
    floor_oreton=0
    floor_totton=0
    for b in floorb:
        floor_oreton+=Tonnage[b]*Rock[b]
        floor_totton+=Tonnage[b]
    
    floor={'blocks':floorb,'ore_ton':floor_oreton,'total_ton':floor_totton}'''
    lower = lower_expected-floor['ore_ton']
    upper = upper_expected-floor['ore_ton']
    pit_ton = upper_t_expected - floor['total_ton']
    blocks = list(set(ceil['blocks'])-set(floor['blocks']))
    if len(blocks)==0:
        return floor['blocks'],floor['ore_ton']-coal_ton_pre,floor['total_ton']-tbase_tonnage,0
    pv=0
    for i in floor['blocks']:
        pv+=(a_v_c[i][1]-a_v_c[i][2])
    if use_cplex:
        tton, oretonn, res, v = sche_opti(
            B, prec, blocks, lower, upper, Tonnage, pit_ton)
    else:
        tton, oretonn, res, v = sche_opti_g(
            B, prec, blocks, lower, upper, Tonnage, pit_ton)
    for i in floor['blocks']:
        res.append(i)
    oretonn += floor['ore_ton']
    tton += floor['total_ton']
    results_bucket[len(results_bucket)]={'blocks':res,'ore_ton':oretonn,'total_ton':tton}
    '''for b in res:
        if not int(prec[b,1])==0:
            for j in prec[b,2:int(prec[b,1])+2]:
                if not int(j) in res:
                    print('prec infeasible')'''
    return res, oretonn-coal_ton_pre, tton-tbase_tonnage, v+pv

def maxflow_upl(profit_per):
    founded=False
    for pr in pr_range:
        if profit_per >= pr[1] and profit_per <= pr[2]:
            founded=True
            s_coal_ton_m=pr[0]
            s_total_ton_m=pr[3]
    if not founded:
        g=maxflow.Graph[float](2, 2)
        nodes=g.add_nodes(len_b)
        for p in prec:
            if not int(p[1]==0):
                for i in range(int(p[1])):
                    g.add_edge(int(p[0]), int(p[2+i]), float('inf'), 0)

        for a in a_v_c:
            if profit_per/100*a[1]-a[2] <= 0:
                g.add_tedge(a[0], 0, a[2]-profit_per/100*a[1])
            else:
                g.add_tedge(a[0], profit_per/100*a[1]-a[2], 0)
        g.maxflow()


        temp_pit=[]
        pit=[]
        for i in range(len(nodes)):
                temp_pit.append(g.get_segment(i))
                if temp_pit[i]==0:
                    pit.append(i)
        
        coal_ton_m=(1-np.array(temp_pit))*Rock
        total_ton_m=(1-np.array(temp_pit))*(Tonnage)
        s_coal_ton_m=sum(coal_ton_m)
        s_total_ton_m=sum(total_ton_m)
        new_ton=True
        for i in range(len(pr_range)):
            if pr_range[i][0] == s_coal_ton_m and pr_range[i][3]==s_total_ton_m:
                if profit_per < pr_range[i][1]:
                    pr_range[i][1]=profit_per
                else:
                    pr_range[i][2]=profit_per
                new_ton=False
        if new_ton:
            pr_range.append([s_coal_ton_m, profit_per,
                            profit_per, s_total_ton_m])
            pv=0
            for b in pit:
                pv += (a_v_c[b][1]-a_v_c[b][2])
            results_bucket[len(results_bucket)]={'blocks':pit,'ore_ton':s_coal_ton_m,'total_ton':s_total_ton_m,'value':pv}
            
            #print(pv,len(pit),profit_per)
    return s_coal_ton_m,s_total_ton_m

results = {}
results[-1] = {'blocks': [], 'ore_ton': 0,
    'total_ton': 0, 'value': 0, 'discounted v': 0}


start = time.time()
g = maxflow.Graph[float](2, 2)
nodes = g.add_nodes(len_b)
#maxflow_upl(50)

if objective == 'NPVnDist':
    
    #calculate upl
    maxflow_upl(100)
    print(pr_range[0])

    base_tonnage = 0
    tbase_tonnage = 0
    last_year = False
    years = 30
    profit_per = 50
    coal_ton = 0
    for y in range(0, years):
        if round(results_bucket[0]['ore_ton'])==round(base_tonnage):
            break
        print('year', y)
        #print('tbase', tbase_tonnage)
        total_ton_annual=0
        coal_ton = 0
        profit_per = 50
        profit_per_u = 100
        profit_per_l = 0
        itr = 0
        last_ton = 0
        pv = 0
        while True:
            dff=pandas.DataFrame(results_bucket)
            dff.to_excel('results_bucket.xlsx')
            founded = False
            if profit_per > 99.999 or sum(Rock) <= (base_tonnage+production_upper):
                profit_per = 100
                last_year = True

            if (coal_ton >= production_lower and coal_ton <= production_upper) or last_year:
                if total_ton_annual <= extraxtion_upper:
                    br, coal_ton, total_ton_annual, pv=LPHeuristic(base_tonnage, y,
                                    production_lower, production_upper, tbase_tonnage)
                    base_tonnage=0
                    tbase_tonnage=0
                    itr=0
                    results[y]={'blocks': br, 'ore_ton': coal_ton, 'total_ton': total_ton_annual}
                    for i in range(y+1):
                        base_tonnage += results[i]['ore_ton']
                        tbase_tonnage += results[i]['total_ton']
                    print('base tonnage', round(base_tonnage), 'total tonnage', round(tbase_tonnage), "this year ore", round(
                        coal_ton), "this tone", round(total_ton_annual), "max_flow hybrid applied")
                    break
                else:
                    br, coal_ton, total_ton_annual, pv=LPHeuristic(base_tonnage, y,
                                    production_lower, production_upper, tbase_tonnage)
                    base_tonnage=0
                    tbase_tonnage=0
                    itr=0
                    results[y]={'blocks': br, 'ore_ton': coal_ton, 'total_ton': total_ton_annual}
                    for i in range(y+1):
                        base_tonnage += results[i]['ore_ton']
                        tbase_tonnage += results[i]['total_ton']
                    print('base tonnage', round(base_tonnage), 'total tonnage', round(tbase_tonnage), "this year ore", round(
                        coal_ton), "this tone", round(total_ton_annual), "pr heu applied")
                    # print("p heuristic applied")
                    break
            elif itr < 10 and not round(profit_per_u, 6) == round(profit_per_l, 6):
                profit_per=(profit_per_u+profit_per_l)/2
            else:
                # print('year',y)
                br, coal_ton, total_ton_annual, v=LPHeuristic(base_tonnage, y,
                                    production_lower, production_upper, tbase_tonnage)
                base_tonnage=0
                tbase_tonnage=0
                itr=0
                results[y]={'blocks': br, 'ore_ton': coal_ton, 'total_ton': total_ton_annual}
                for i in range(y+1):
                    base_tonnage += results[i]['ore_ton']
                    tbase_tonnage += results[i]['total_ton']
                print('base tonnage', round(base_tonnage), 'total tonnage', round(tbase_tonnage), "this year ore", round(
                        coal_ton), "this tone", round(total_ton_annual), "heu  applied")
                # print("heuristic applied")
                break
            s_coal_ton_m,s_total_ton_m=maxflow_upl(profit_per)
            #print(pr_range[-1])
            coal_ton=s_coal_ton_m-base_tonnage
            total_ton_annual=s_total_ton_m-tbase_tonnage
            if coal_ton > production_upper:
                profit_per_u=profit_per
            if coal_ton < production_lower:
                profit_per_l=profit_per
            if round(last_ton) == round(s_coal_ton_m):
                itr += 1
            #print(itr,last_ton,s_coal_ton_m)
            last_ton=s_coal_ton_m
    results_sheet=[]
    results_sheet.append(
        ['year', 'ore tonnage', 'total tonnage', 'Value', 'discounted'])
    bb=[]
    bb.append(['block','sch'])
    for i in np.arange(y-1,0,-1):
        results[i]['blocks']=list(set(results[i]['blocks'])-set(results[i-1]['blocks']))
    for i in range(y):
        
        pv=0
        for b in results[i]['blocks']:
            #if not b in list(np.array(bb)[:,0]):
            pv += (a_v_c[b][1]-a_v_c[b][2])
            bb.append([b, i])
        results_sheet.append([i, results[i]['ore_ton'], results[i]['total_ton'], pv, float(pv)/(1+discount_rate)**i])
    print(results_sheet)    
    df=pandas.DataFrame(results_sheet)
    df.to_excel('the_result.xlsx')
    df=pandas.DataFrame(bb)
    df.to_excel('blocks.xlsx')

    '''x=[]
    yy=[]
    z=[]
    c=[]
    for i in range(y):
        for b in results[i]['blocks']:
            x.append(B[b,1])
            yy.append(B[b,2])
            z.append(B[b,3])
            c.append(i)

    from mpl_toolkits import mplot3d
    #%matplotlib inline
    import numpy as np
    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = plt.axes(projection='3d')
    ax.scatter3D(x, yy, z, c=c);


    plt.show()'''