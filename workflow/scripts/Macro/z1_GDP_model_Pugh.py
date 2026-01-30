#%%
# Initial play around with the solowpy model that was built by David Pugh 

import numpy as np
import pandas as pd
import sympy as sym
import matplotlib as mpl
import matplotlib.pyplot as plt

import os
import sys

import scipy as sp
import math

import seaborn as sns
import statsmodels
import statsmodels.api as sm
import statsmodels.formula.api as smf

# Graphics setup: seaborn-whitegrid and figure size
plt.style.use('seaborn-whitegrid')

figure_size = plt.rcParams["figure.figsize"]
figure_size[0] = 12
figure_size[1] = 10
plt.rcParams["figure.figsize"] = figure_size

# Initial cobb douglas model function
def sgm_bgp_100yr_run(L0, E0, K0, n = 0.01, g = 0.02, s = 0.15, alpha = 0.5, delta = 0.03, T = 100):

    sg_df = pd.DataFrame(index = range(T), 
                         columns = ['Labor', 
                                    'Efficiency',
                                    'Capital',
                                    'Output',
                                    'Output_per_Worker',
                                    'Capital_Output_Ratio',
                                    'BGP_Output',
                                    'BGP_Output_per_Worker',
                                    'BGP_Capital_Output_Ratio',
                                    'BGP_Capital'],
                         dtype = 'float')

    sg_df.Labor[0] = L0
    sg_df.Efficiency[0] = E0
    sg_df.Capital[0] = K0
    sg_df.Output[0] = (sg_df.Capital[0]**alpha * (sg_df.Labor[0] * 
        sg_df.Efficiency[0])**(1-alpha))
    sg_df.Output_per_Worker[0] = sg_df.Output[0]/sg_df.Labor[0]
    sg_df.Capital_Output_Ratio[0] = sg_df.Capital[0]/sg_df.Output[0]
    sg_df.BGP_Capital_Output_Ratio[0] = (s / (n + g + delta))
    sg_df.BGP_Output_per_Worker[0] = sg_df.Efficiency[0] * (
        sg_df.BGP_Capital_Output_Ratio[0]*(alpha/(1 - alpha)))
    sg_df.BGP_Output[0] = sg_df.BGP_Output_per_Worker[0] * sg_df.Labor[0]
    sg_df.BGP_Capital[0] = sg_df.Labor[0] * sg_df.Efficiency[0] * (
        sg_df.BGP_Capital_Output_Ratio[0]*(1/(1 - alpha)))

    for i in range(T - 1):
        sg_df.Labor[i+1] = sg_df.Labor[i] + sg_df.Labor[i] * n
        sg_df.Efficiency[i+1] = sg_df.Efficiency[i] + sg_df.Efficiency[i] * g
        sg_df.Capital[i+1] = sg_df.Capital[i] - sg_df.Capital[i] * delta + (
            sg_df.Output[i] * s)
        sg_df.Output[i+1] = (sg_df.Capital[i+1]**alpha * 
            (sg_df.Labor[i+1] * sg_df.Efficiency[i+1])**(1-alpha))
        sg_df.Output_per_Worker[i+1] = sg_df.Output[i+1]/sg_df.Labor[i+1]
        sg_df.Capital_Output_Ratio[i+1] = (sg_df.Capital[i+1]/
            sg_df.Output[i+1])
        sg_df.BGP_Capital_Output_Ratio[i+1] = (s / (n + g + delta))
        sg_df.BGP_Output_per_Worker[i+1] = sg_df.Efficiency[i+1] * (
            sg_df.BGP_Capital_Output_Ratio[i+1]**(alpha/(1 - alpha)))
        sg_df.BGP_Output[i+1] = (sg_df.BGP_Output_per_Worker[i+1] * 
            sg_df.Labor[i+1])
        sg_df.BGP_Capital[i+1] = (s / (n + g + delta))**(1/(1-alpha)) * (
            sg_df.Efficiency[i+1] * sg_df.Labor[i+1])
        
    fig = plt.figure(figsize=(12, 12))

    ax1 = plt.subplot(3,2,1)
    sg_df.Labor.plot(ax = ax1, title = "Labor Force")
    plt.ylabel("Parameters")
    plt.ylim(0, )

    ax2 = plt.subplot(3,2,2)
    sg_df.Efficiency.plot(ax = ax2, title = "Efficiency of Labor")
    plt.ylim(0, )
    
    ax3 = plt.subplot(3,2,3)
    sg_df.BGP_Capital.plot(ax = ax3, title = "BGP Capital Stock")
    sg_df.Capital.plot(ax = ax3, title = "Capital Stock")
    plt.ylabel("Values")
    plt.ylim(0, )

    ax4 = plt.subplot(3,2,4)
    sg_df.BGP_Output.plot(ax = ax4, title = "BGP Output")
    sg_df.Output.plot(ax = ax4, title = "Output")
    plt.ylim(0, )

    ax5 = plt.subplot(3,2,5)
    sg_df.BGP_Output_per_Worker.plot(ax = ax5, 
        title = "BGP Output per Worker")
    sg_df.Output_per_Worker.plot(ax = ax5, title = "Output per Worker")
    plt.xlabel("Years")
    plt.ylabel("Ratios")
    plt.ylim(0, )

    ax6 = plt.subplot(3,2,6)
    sg_df.BGP_Capital_Output_Ratio.plot(ax = ax6, 
        title = "BGP Capital-Output Ratio")
    sg_df.Capital_Output_Ratio.plot(ax = ax6, 
        title = "Capital-Output Ratio")
    plt.xlabel("Years")
    plt.ylim(0, )

    plt.suptitle('Solow Growth Model: Simulation Run', size = 20)

    plt.show()
    
    print(n, "is the labor force growth rate")
    print(g, "is the efficiency of labor growth rate")
    print(delta, "is the depreciation rate")
    print(s, "is the savings rate")
    print(alpha, "is the decreasing-returns-to-scale parameter")

    return sg_df

# Test output of function
sgm_bgp_100yr_run(1000, 1, 100)
#%%
