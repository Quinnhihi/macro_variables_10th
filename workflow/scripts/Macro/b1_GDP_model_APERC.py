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
lab_eff = pd.read_csv('./data/labour_efficiency_estimate_to2027.csv')
cap_df = pd.read_csv('./data/capital_stock.csv') 

input_df = pd.concat([UN_df, IMF_df, lab_eff, cap_df]).reset_index(drop = True)

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
# Provide source data
GDP_8th['source'] = '8th Outlook'
GDP_8th.to_csv('./data/GDP_8th.csv', index = False)

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
GDP_df1.to_csv('./data/gdp_df1.csv', index = True)

# Capital growth grab
cap_growth_df = cap_df[['economy_code', 'variable', 'year', 'percent']].copy().reset_index(drop = True)
cap_growth_df.to_csv('./data/cap_growth_df.csv', index = False)

##########################################################################################
# READ IN additional data (GDP_df1 and lab_eff obtained from above)

# Depreciation for most recent year of data
delta_df = pd.read_csv('./data/PWT_delta_2019.csv')

# Savings
savings_df = pd.read_csv('./data/IMF_savings_2027.csv')

# Also grab historical depreciation and savings/investment
save_invest_hist = pd.read_csv('./data/IMF/IMF_to2027.csv')
delta_hist = pd.read_csv('./data/PWT/PWT_cap_labour_to2019.csv')

# Build a funtion for the model: Y[i+1] = K[i+1]**alpha * (L[i+1] * E[i+1])**(1-alpha))

# L is given from UN_DESA
# E (derived for historical 1980 to project 2027 from IMF), grown via a function defined below out to 2100
# K[i+1] = K[i] - K[i] * delta + (Y[i] * s)
# Depreciation (delta) and savings are also changed via a function defined below 

def aperc_gdp_model(economy = '01_AUS',
                    input_data = GDP_df1,
                    labour_data = lab_eff,
                    delta_data = delta_df,
                    sav_data = savings_df,
                    GDP_8th = GDP_8th,
                    lab_eff_periods = 10,
                    high_eff = 0.015,
                    low_eff = 0.012,
                    change_eff = 0.002,
                    high_sav = 0.25,
                    low_sav = 0.22,
                    change_sav = 0.002,
                    high_delta = 0.046,
                    low_delta = 0.044,
                    change_del = 0.0005,
                    alpha = 0.4,
                    cap_compare = 0.05):
    """
    This function takes inputs for a Cobb Douglas CES production function and generates a
    dataset with GDP estimates out to 2100 for APEC economies.
    economy: choose one APEC economy code; e.g. '03_CDA'. default is '01_AUS'
    input_data: GDP_df1.
    labour_data: lab_eff.
    delta_data: delta_df.
    sav_data: savings_df.
    GDP_8th: GDP from 8th Outlook
    lab_eff_periods: int; default is 10; how many periods to look back in time to then calculate 
    labour efficiency going forward.
    high_eff: growth rate; default is 0.0175; if labour efficiency is higher than this 
    bound, decrease it.
    low_eff: as above; default is 0.0125; if labour efficiency is lower than this 
    bound, increase it.
    change_eff: fraction; default is 0.0015; how much to increase or decrease labour efficiency 
    if higher or lower than bounds.
    high_sav: fraction between 0 and 1; default is 0.3; if savings is higher than this bound, 
    decrease it.
    low_sav: fraction between 0 and 1; default is 0.22; if savings is lower than this bound, 
    increase it.
    change_sav: fraction; default is 0.002; how much to increase or decrease savings rate if higher 
    or lower than bounds.
    high_delta: fraction between 0 and 1; default is 0.046; if depreciation is higher than this 
    bound, decrease it.
    low_delta: fraction between 0 and 1; default is 0.045; if depreciation is lower than this 
    bound, increase it.
    change_del: fraction; default is 0.005; how much to increase or decrease depreciation rate 
    if higher or lower than bounds.
    alpha: default is 0.4; typically keep this as 0.4 because labour efficiency input data derived 
    to 2027 assumed a value of 0.4. 
    """
 
    # Labour efficiency calculation
    eff_df = labour_data[labour_data['economy_code'] == economy][['year', 'percent']]\
        .set_index('year', drop = True).iloc[-lab_eff_periods:]
    
    lab_eff_improvement = eff_df['percent'].sum() / lab_eff_periods

    # Update labour efficiency
    for year in range(2028, 2101, 1):
        if eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods > high_eff:
            eff_df.loc[year, 'percent'] = eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods - change_eff

        elif eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods < low_eff:
            eff_df.loc[year, 'percent'] = eff_df.iloc[-lab_eff_periods:].sum()[0] / lab_eff_periods + change_eff

        else: 
            eff_df.loc[year, 'percent'] = eff_df.loc[year - 1, 'percent']

    # Labour efficiency
    GDP_df2 = input_data[input_data['economy_code'] == economy].copy()
    
    for year in range (2028, 2101, 1):
        GDP_df2.at[year, 'efficiency'] = GDP_df2.loc[year - 1, 'efficiency'] * \
            (1 + (eff_df.loc[year, 'percent']))

    # Save labour efficiency dataframe. Location for data:
    lab_eff_loc = './results/labour_efficiency/data/'

    if not os.path.isdir(lab_eff_loc):
        os.makedirs(lab_eff_loc)

    GDP_df2[['economy_code', 'economy', 'labour', 'efficiency']].to_csv(lab_eff_loc + '{}_labour_efficiency_estimate.csv'.format(economy))

    # Depreciation and savings    
        
    savings = sav_data[sav_data['economy_code'] == economy]['value'].values[0] / 100
    delta = delta_data[delta_data['economy_code'] == economy]['value'].values[0]

    # Create savings data frame
    dyn_savings = pd.DataFrame(index = range(1980, 2101, 1), columns = ['savings'])
    dyn_savings.index.name = 'year'
    dyn_savings.loc[2028, 'savings'] = savings

    # Create depreciation data frame
    dyn_delta = pd.DataFrame(index = range(1980, 2101, 1), columns = ['delta'])
    dyn_delta.index.name = 'year'
    dyn_delta.loc[2028, 'delta'] = delta

    cap_growth = cap_growth_df[cap_growth_df['economy_code'] == economy][['year', 'percent']].set_index('year')

    for year in range(2028, 2101, 1):
        if dyn_savings.loc[year, 'savings'] > high_sav:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings'] - change_sav
        
        elif dyn_savings.loc[year, 'savings'] < low_sav:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings'] + change_sav
        
        else:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings']

    for year in range(2028, 2101, 1):
        if dyn_delta.loc[year, 'delta'] > high_delta:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta'] - change_del
        
        elif dyn_delta.loc[year, 'delta'] < low_delta:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta'] + change_del
        
        else:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta'] 
        
        # AMENDMENT: BECAUSE CAPITAL ESTIMATES FROM 2028 DO NOT FOLLOW HISTORICAL TRENDS WELL FOR SOME ECONOMIES
        # IE THERE"S A SERIES BREAK. NEED TO BUILD AN IF ELSE

        new_cap_calc = GDP_df2.loc[year - 1, 'capital']\
            - (GDP_df2.loc[year - 1, 'capital'] * dyn_delta.loc[year, 'delta'])\
                + (GDP_df2.loc[year - 1, 'real_output'] * dyn_savings.loc[year, 'savings'])
        
        cap_prev = GDP_df2.loc[year - 1, 'capital']

        cap_diff = (new_cap_calc / cap_prev) - 1

        if ((cap_diff / cap_growth.loc[year - 1, 'percent']) < (1 - cap_compare)) | ((cap_diff / cap_growth.loc[year - 1, 'percent']) > (1 + cap_compare)):
            # Capital
            GDP_df2.at[year, 'capital'] = GDP_df2.loc[year - 1, 'capital'] * (1 + (cap_growth.loc[year - 1, 'percent'] * (1 - cap_compare)))
            cap_growth.loc[year, 'percent'] = cap_growth.loc[year - 1, 'percent'] * (1 - cap_compare)

        else:
             GDP_df2.at[year, 'capital'] = new_cap_calc
             cap_growth.loc[year, 'percent'] = (new_cap_calc / GDP_df2.loc[year - 1, 'capital']) - 1

        # Output
        GDP_df2.at[year, 'real_output'] = (GDP_df2.loc[year, 'capital']) ** alpha\
            * ((GDP_df2.loc[year, 'labour'] * GDP_df2.loc[year, 'efficiency']) ** (1 - alpha)) 

    # Grab historical savings
    for year in range(1980, 2028, 1):
        if economy in ['02_BD']:
            dyn_savings.loc[year, 'savings'] = save_invest_hist[(save_invest_hist['variable'] == 'Total investment') &
                                                                (save_invest_hist['economy_code'] == economy)]\
                                                                    .set_index('year')\
                                                                        .loc[year, 'value'] / 100

        elif economy in ['13_PNG']:
            dyn_savings.loc[year, 'savings'] = savings / 100

        else:
            dyn_savings.loc[year, 'savings'] = save_invest_hist[(save_invest_hist['variable'] == 'Gross national savings') &
                                                                (save_invest_hist['economy_code'] == economy)]\
                                                                    .set_index('year')\
                                                                        .loc[year, 'value'] / 100

    for year in range(1980, 2020, 1):
        dyn_delta.loc[year, 'delta'] = delta_hist[(delta_hist['variable'] == 'delta') &
                                                  (delta_hist['economy_code'] == economy)]\
                                                    .set_index('year')\
                                                    .loc[year, 'value']
        
    for year in range(2020, 2028, 1):
        dyn_delta.loc[year, 'delta'] = delta
    
    GDP_df2 = pd.concat([GDP_df2, dyn_savings, dyn_delta], axis = 1)

    # Finalise data frame with estimates for GDP
    GDP_estimates = GDP_df2.reset_index()

    GDP_estimates['real_output_IMF'] = np.where(GDP_estimates['year'] > 2027, np.nan, 
                                                    np.where(GDP_estimates['year'] <= 2027, 
                                                                GDP_estimates['real_output'], np.nan))

    GDP_estimates['real_output_projection'] = np.where(GDP_estimates['year'] <= 2027, np.nan, 
                                                    np.where(GDP_estimates['year'] > 2027, 
                                                                GDP_estimates['real_output'], np.nan))

    # Now add GDP estimates from 8th
    GDP_estimates = GDP_estimates.merge(GDP_8th, on = ['economy_code', 'year'], how = 'left')\
        [['year', 'economy_code', 'economy', 'labour', 'efficiency', 'capital', 'savings', 'delta', 'real_output_IMF', 'real_output_projection', 'value']]\
            .rename(columns = {'value': 'real_output_8th'})

    GDP_estimates_long = GDP_estimates.melt(id_vars = ['economy_code', 'economy', 'year'])

    # Change variable names so they're more descriptive for charts
    GDP_estimates_long['variable'] = GDP_estimates_long['variable'].map({'real_output_IMF': 'IMF GDP projections to 2027',
                                                                         'real_output_projection': 'APERC real GDP projections from 2027',
                                                                         'real_output_8th': '8th Outlook projections',
                                                                         'labour': 'Population',
                                                                         'capital': 'Capital stock',
                                                                         'efficiency': 'Labour efficiency',
                                                                         'savings': 'Savings',
                                                                         'delta': 'Depreciation'})

    # Save location for data
    GDP_result = './results/GDP_estimates/data/'

    if not os.path.isdir(GDP_result):
        os.makedirs(GDP_result)

    GDP_estimates_long.to_csv(GDP_result + '{}_GDP_estimate.csv'.format(economy), index = False)

    # GDP chart location
    GDP_charts = './results/GDP_estimates/'

    # Chart the results
    GDP_df = GDP_estimates_long[GDP_estimates_long['year'] <= 2070].copy().reset_index(drop = True)
    GDP_df = GDP_df[(GDP_df['variable']\
                     .isin(['IMF GDP projections to 2027',
                            'APERC real GDP projections from 2027']))]\
                                .copy().reset_index(drop = True)
    
    GDP_8th = GDP_estimates_long[(GDP_estimates_long['variable'].isin(['8th Outlook projections']))]\
                                        .copy().reset_index(drop = True)

    fig, ax = plt.subplots()

    sns.set_theme(style = 'ticks')
    custom_palette = {'IMF GDP projections to 2027': sns.color_palette('Paired', 6).as_hex()[0],
                      'APERC real GDP projections from 2027' : sns.color_palette('Paired', 6).as_hex()[1],
                      '8th Outlook projections': sns.color_palette('Dark2', 6).as_hex()[1]}

    # real GDP IMF 
    sns.lineplot(ax = ax,
                 data = GDP_df,
                 x = 'year',
                 y = 'value',
                 hue = 'variable',
                 palette = custom_palette)
    
    # real GDP 8th
    sns.lineplot(ax = ax,
                 data = GDP_8th,
                 x = 'year',
                 y = 'value',
                 hue = 'variable',
                 palette = custom_palette)
    
    ax.lines[1].set_linestyle('--')
    
    leg = ax.legend(title = '', 
                    fontsize = 8)
    
    leg_lines = leg.get_lines()

    leg_lines[1].set_linestyle('--')
    
    ax.set(title = economy + ' real GDP (2017 USD PPP)', 
           xlabel = 'Year', 
           ylabel = 'Real output (millions)',
           xlim = (1980, 2070))
    
    plt.tight_layout()
    fig.savefig(GDP_charts + economy + '_GDP_estimates.png')
    plt.show()
    plt.close()

    # Labour efficiency charts location
    lab_eff_charts = './results/labour_efficiency/To2100/'

    if not os.path.isdir(lab_eff_charts):
        os.makedirs(lab_eff_charts)

    # Labour efficiency charts
    labeff_df = GDP_estimates_long[(GDP_estimates_long['variable'].isin(['Labour efficiency']))]\
                                        .copy().reset_index(drop = True)
    
    if labeff_df['value'].isna().sum() == len(labeff_df['value']):
        pass

    else:

        fig, ax = plt.subplots()

        sns.set_theme(style = 'ticks')

        # Labour efficiency
        sns.lineplot(ax = ax,
                     data = labeff_df,
                     x = 'year',
                     y = 'value')
        
        ax.set(title = economy + ' labour efficiency estimate', 
               xlabel = 'Year', 
               ylabel = 'Labour efficiency')
        
        plt.tight_layout()
        fig.savefig(lab_eff_charts + economy + '_labour_efficiency_to2100.png')
        plt.show()
        plt.close()
#%%
