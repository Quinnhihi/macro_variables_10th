#%%
# Solow Swan Growth estimates for APEC economies

import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
import openpyxl

# Change the working drive
wanted_wd = 'macro_variables_9th'
os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)

APEC_econcode = pd.read_csv('./data/APEC_economy_code.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

# Estimates begin from 2028:
# GDP output estimates to 2027 are from the IMF

# To estimate GDP after 2027, the main inputs are:  
# 1. UN DESA population data out to 2100 (this is the labour input in the cobb douglas function)
# 2. Capital stock estimates to 2019 from PWT, that are then estimated to 2027 using an output to capital stock ratio from 2019
# 3. Derived labour efficiency estimate to 2027 (assumed to grow at a chosen growth rate) 

# Import required dataframes

UN_df = pd.read_csv('./data/UN_DESA/undesa_pop_to2100.csv')
IMF_df = pd.read_csv('./data/IMF/IMF_to2027.csv')
leff_df = pd.read_csv('./data/labour_efficiency_estimate_to2027.csv')
cap_df = pd.read_csv('./data/capital_stock.csv')

input_df = pd.concat([UN_df, IMF_df, leff_df, cap_df]).reset_index(drop = True)

input_df = input_df[(input_df['variable']\
                          .isin(['population_1jan', 'Real GDP PPP 2017 USD', 
                                 'Labour efficiency', 'Capital stock'])) &
                     (input_df['year'] >= 1980)].copy()\
                                 .reset_index(drop = True)

# Also import GDP estimates from 8th Outlook

GDP_8th = pd.read_excel('./data/GDP_8thOutlook.xlsx').loc[:, :2070]

GDP_8th = GDP_8th.melt(id_vars = ['Economy', 'Unit'])\
    .rename(columns = {'Economy': 'economy_code', 
                       'Unit': 'variable',
                       'variable': 'year'}).reset_index(drop = True)

# Change GDP to millions
GDP_8th['value'] = GDP_8th['value'] / (10**6)

GDP_8th['source'] = '8th Outlook'

# Specify some parameters needed for the cobb douglas model

ALPHA = 0.4

# For the model: Y[i+1] = K[i+1]**alpha * (L[i+1] * E[i+1])**(1-alpha))

# L is given from UN_DESA
# E (derived for historical 1980 to project 2027 from IMF), grown via a function defined below out to 2100
# K[i+1] = K[i] - K[i] * delta + (Y[i] * s)
# Depreciation (delta) and savings are also changed via a function defined below 

GDP_df1 = pd.DataFrame()

for economy in APEC_econcode.values():
    pop_df1 = input_df[(input_df['economy_code'] == economy) &
                           (input_df['variable'] == 'population_1jan')].copy()\
                            [['economy_code', 'economy', 'year', 'value']]\
                                .rename(columns = {'value': 'labour'}).reset_index(drop = True)
    
    eff_df1 = input_df[(input_df['economy_code'] == economy) &
                       (input_df['variable'] == 'Labour efficiency')].copy()\
                        [['year', 'value']]\
                            .rename(columns = {'value': 'efficiency'}).reset_index(drop = True)
    
    interim_df1 = pop_df1.merge(eff_df1, 
                                how = 'left', 
                                on = 'year').copy()
    
    cap_df1 = input_df[(input_df['economy_code'] == economy) &
                       (input_df['variable'] == 'Capital stock')].copy()\
                        [['year', 'value']]\
                            .rename(columns = {'value': 'capital'}).reset_index(drop = True)
    
    interim_df2 = interim_df1.merge(cap_df1,
                                    how = 'left',
                                    on = 'year').copy()
    
    y_df1 = input_df[(input_df['economy_code'] == economy) &
                     (input_df['variable'] == 'Real GDP PPP 2017 USD')].copy()\
                        [['year', 'value']]\
                            .rename(columns = {'value': 'real_output'}).reset_index(drop = True)
    
    interim_df3 = interim_df2.merge(y_df1,
                                    how = 'left',
                                    on = 'year').copy()

    GDP_df1 = pd.concat([GDP_df1, interim_df3]).reset_index(drop = True)

GDP_df1 = GDP_df1.set_index('year', drop = True)

##########################################################################################
# Labour efficiency estimates
lab_eff = pd.read_csv('./data/labour_efficiency_estimate_to2027.csv')

# Labour efficiency inputs
# How many recent periods to look at to get the next rate of labour efficiency out to 2100
lab_eff_periods = 10

# Bounds for long-term labour efficiency rate
high_eff = 0.0175
low_eff = 0.0125

# Rate at which labour efficiency moves lower or higher
down_eff = 0.0015
up_eff = 0.0015

GDP_df2 = pd.DataFrame()

for economy in APEC_econcode.values(): 
    # Labour efficiency calculation
    eff_df = lab_eff[lab_eff['economy_code'] == economy][['year', 'percent']]\
        .set_index('year', drop = True).iloc[-lab_eff_periods:]
    
    lab_eff_improvement = eff_df['percent'].sum() / lab_eff_periods

    # Update labour efficiency
    for year in range(2028, 2101, 1):
        if eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods > high_eff:
            eff_df.loc[year, 'percent'] = eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods - down_eff

        elif eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods < low_eff:
            eff_df.loc[year, 'percent'] = eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods + up_eff

        else: 
            eff_df.loc[year, 'percent'] = lab_eff_improvement

    # Labour efficiency
    interim_df1 = GDP_df1[GDP_df1['economy_code'] == economy].copy()
    
    for year in range (2028, 2101, 1):
        interim_df1.at[year, 'efficiency'] = interim_df1.loc[year - 1, 'efficiency'] * \
            (1 + (eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods))

    GDP_df2 = pd.concat([GDP_df2, interim_df1])

# Capital and output
# Delta assumptions (bounds and adjustment)
high_delta = 0.046
low_delta = 0.045
down_delta = 0.005
up_delta = 0.005

# Savings assumptions (bounds and adjustment)
high_sav = 0.30
low_sav = 0.22
down_sav = 0.004
up_sav = 0.002

# Read data
delta_df = pd.read_csv('./data/PWT_delta_2019.csv')
delta_df = pd.concat([delta_df, pd.DataFrame({'economy_code': '13_PNG', 'year': 2019}, index = [0])])\
    .sort_values('economy_code').reset_index(drop = True)
savings_df = pd.read_csv('./data/IMF_savings_2027.csv')

GDP_df3 = pd.DataFrame()

for economy in APEC_econcode.values():
    delta = delta_df[delta_df['economy_code'] == economy]['value'].values[0]
    savings = savings_df[savings_df['economy_code'] == economy]['value'].values[0] / 100

    interim_df1 = GDP_df2[GDP_df2['economy_code'] == economy].copy()

    # Create savings data frame
    dyn_savings = pd.DataFrame(index = range(2028, 2101, 1), columns = ['savings'])
    dyn_savings.loc[2028, 'savings'] = savings

    # Create depreciation data frame
    dyn_delta = pd.DataFrame(index = range(2028, 2101, 1), columns = ['delta'])
    dyn_delta.loc[2028, 'delta'] = delta

    for year in range(2028, 2101, 1):
        if dyn_savings.loc[year, 'savings'] > high_sav:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings'] - down_sav
        
        elif dyn_savings.loc[year, 'savings'] < low_sav:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings'] + up_sav
        
        else:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings']

    for year in range(2028, 2101, 1):
        if dyn_delta.loc[year, 'delta'] > high_delta:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta'] - down_delta
        
        elif dyn_delta.loc[year, 'delta'] < low_delta:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta'] + up_delta
        
        else:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta']

        # Capital
        interim_df1.at[year, 'capital'] = interim_df1.loc[year - 1, 'capital']\
            - interim_df1.loc[year - 1, 'capital'] * dyn_delta.loc[year, 'delta']\
                + interim_df1.loc[year - 1, 'real_output'] * dyn_savings.loc[year, 'savings'] 
        # Output
        interim_df1.at[year, 'real_output'] = (interim_df1.loc[year, 'capital']) ** ALPHA\
            * ((interim_df1.loc[year, 'labour'] * interim_df1.loc[year, 'efficiency']) ** (1 - ALPHA))      

    GDP_df3 = pd.concat([GDP_df3, interim_df1]) 

GDP_estimates = GDP_df3.reset_index()

GDP_estimates['real_output_IMF'] = np.where(GDP_estimates['year'] > 2027, np.nan, 
                                                   np.where(GDP_estimates['year'] <= 2027, 
                                                            GDP_estimates['real_output'], np.nan))

GDP_estimates['real_output_projection'] = np.where(GDP_estimates['year'] <= 2027, np.nan, 
                                                   np.where(GDP_estimates['year'] > 2027, 
                                                            GDP_estimates['real_output'], np.nan))

# Now add GDP estimates from 8th

GDP_estimates = GDP_estimates.merge(GDP_8th, on = ['economy_code', 'year'], how = 'left')\
    [['year', 'economy_code', 'economy', 'labour', 'efficiency', 'capital', 'real_output_IMF', 'real_output_projection', 'value']]\
        .rename(columns = {'value': 'real_output_8th'})

GDP_estimates_long = GDP_estimates.melt(id_vars = ['economy_code', 'economy', 'year'])

# Change variable names so they're more descriptive for charts
GDP_estimates_long['variable'] = GDP_estimates_long['variable'].map({'real_output_IMF': 'IMF GDP projections to 2027',
                                                                     'real_output_projection': 'APERC real GDP projections',
                                                                     'real_output_8th': '8th Outlook projections'})

######################################################################################################
# CHARTS
# Labour efficiency

# Save location for charts
lab_eff = './results/labour_efficiency/To2100/'

if not os.path.isdir(lab_eff):
    os.makedirs(lab_eff)

for economy in APEC_econcode.values():
    chart_df = GDP_df2[GDP_df2['economy_code'] == economy].copy().reset_index(drop = False)
    
    if chart_df['efficiency'].isna().sum() == len(chart_df['efficiency']):
        pass

    else:

        fig, ax = plt.subplots()

        sns.set_theme(style = 'ticks')

        # Labour efficiency
        sns.lineplot(ax = ax,
                    data = chart_df,
                    x = 'year',
                    y = 'efficiency')
        
        ax.set(title = economy + ' labour efficiency estimate', 
                    xlabel = 'Year', 
                    ylabel = 'Labour efficiency')
        
        plt.tight_layout()
        fig.savefig(lab_eff + economy + '_labour_efficiency_to2100.png')
        plt.close()

# GDP ESTIMATES
# Save location for charts
GDP_est = './results/GDP_estimates/'

if not os.path.isdir(GDP_est):
    os.makedirs(GDP_est)

# GDP charts
for economy in APEC_econcode.values():
    chart_df = GDP_estimates_long[(GDP_estimates_long['economy_code'] == economy) &
                                  (GDP_estimates_long['variable'].isin(['IMF GDP projections to 2027',
                                                                        'APERC real GDP projections']))]\
                                    .copy().reset_index(drop = True)
    
    chart_df_8th = GDP_estimates_long[(GDP_estimates_long['economy_code'] == economy) &
                                      (GDP_estimates_long['variable'].isin(['8th Outlook projections']))]\
                                        .copy().reset_index(drop = True)

    fig, ax = plt.subplots()

    sns.set_theme(style = 'ticks')

    # real GDP IMF
    sns.lineplot(ax = ax,
                 data = chart_df,
                 x = 'year',
                 y = 'value',
                 hue = 'variable',
                 palette = sns.color_palette('Paired', 2))
    
    # real GDP IMF
    sns.lineplot(ax = ax,
                 data = chart_df_8th,
                 x = 'year',
                 y = 'value',
                 hue = 'variable')
    
    ax.lines[1].set_linestyle('--')
    
    plt.legend(title = '', 
               fontsize = 8)
    
    ax.set(title = economy + ' real GDP (2017 USD PPP)', 
           xlabel = 'Year', 
           ylabel = 'Real output (millions)',
           xlim = (1980, 2070))
    
    plt.tight_layout()
    fig.savefig(GDP_est + economy + '_GDP_estimates.png')
    plt.close()
#%%
