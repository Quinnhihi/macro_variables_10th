#%%
# Building combined data frame to generate capital, labour, depreciation, savings, etc to 2027

import pandas as pd
import numpy as np
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

UN_df_long = pd.read_csv('./data/UN_DESA/undesa_pop_to2100.csv')
IMF_df_long = pd.read_csv('./data/IMF/IMF_to2027.csv')
PWT_df_long = pd.read_csv('./data/PWT/PWT_cap_labour_to2019.csv') 

# Use output to capital stock from PWT_df to generate capital variable in IMF data 

capital_df = pd.DataFrame(columns = IMF_df_long.columns)

for economy in APEC_econcode.values():
    IMF_temp = IMF_df_long[(IMF_df_long['economy_code'] == economy) & 
                           (IMF_df_long['variable'] == 'Real GDP PPP 2017 USD')]\
                            .copy().set_index('year')
    
    PWT_temp = PWT_df_long[(PWT_df_long['economy_code'] == economy) & 
                           (PWT_df_long['variable'] == 'output_to_kstock')]\
                            .copy().set_index('year')[['value']].rename(columns = {'value': 'ratio'})
    
    capital_stock = pd.concat([IMF_temp, PWT_temp], axis = 1).loc[1980: 2027, :]

    for i in range(2020, 2028, 1):
        capital_stock.loc[i, 'ratio'] = capital_stock.loc[i - 1, 'ratio']

    capital_stock['capital'] = capital_stock['value'] / capital_stock['ratio']
    capital_stock['variable'] = 'Capital stock'
    capital_stock['source'] = 'IMF and PWT calculation'

    capital_stock = capital_stock.reset_index(drop = False)\
        [['economy_code', 'economy', 'year', 'variable', 'capital', 'source']]\
            .rename(columns = {'capital': 'value'})
    
    capital_stock['percent'] = capital_stock.groupby(['economy', 'variable'],
                                                     group_keys = False)\
                                                        ['value'].apply(pd.Series.pct_change)
    
    capital_df = pd.concat([capital_df, capital_stock], axis = 0).reset_index(drop = True)

# Chart capital

# Save location for charts
capital = './results/capital/'

if not os.path.isdir(capital):
    os.makedirs(capital)

for economy in APEC_econcode.values():
    chart_df = capital_df[capital_df['economy_code'] == economy].copy().reset_index(drop = True)
    
    if chart_df['value'].isna().sum() == len(chart_df['value']):
        pass

    else:

        fig, axs = plt.subplots(2, 1)

        sns.set_theme(style = 'ticks')

        # Capital stock
        sns.lineplot(ax = axs[0],
                    data = chart_df,
                    x = 'year',
                    y = 'value')
        
        axs[0].set(title = economy + ' capital stock', 
                    xlabel = 'Year', 
                    ylabel = 'Capital stock')
        
        # Capital stock growth
        sns.lineplot(ax = axs[1],
                    data = chart_df,
                    x = 'year',
                    y = 'percent')
        
        axs[1].set(title = economy + ' capital stock growth', 
                    xlabel = 'Year', 
                    ylabel = 'Capital stock growth')
        
        plt.tight_layout()
        fig.savefig(capital + economy + '_capital.png')
        plt.close()


# Save capital df
capital_df.to_csv('./data/capital_stock.csv', index = False)

#############################################################################################

# Estimating efficiency of Labour, E

ALPHA = 0.4

# Create Dataframe that has labour (UN population), capital and GDP (real GDP PPP 2017 USD)

IMF_subset = IMF_df_long[IMF_df_long['variable'] == 'Real GDP PPP 2017 USD'].copy().reset_index(drop = True)
UN_subset = UN_df_long[(UN_df_long['variable'] == 'population_1jan') &
                       (UN_df_long['year'].isin(range(1980, 2028, 1)))].copy().reset_index(drop = True)

E_calc_df = pd.concat([IMF_subset.copy(), 
                       UN_subset.copy(), 
                       capital_df.copy()]).reset_index(drop = True)

# Combined dataframe for Labour efficiency calculation

E_estimate = pd.DataFrame()

for economy in APEC_econcode.values():
    labour_df = E_calc_df[(E_calc_df['economy_code'] == economy) &
                          (E_calc_df['variable'] == 'population_1jan')]\
                            .copy().set_index('year')

    labour_df['L^1-alpha'] = labour_df['value'] ** (1 - ALPHA)
    labour_df = labour_df[['economy_code', 'economy', 'L^1-alpha']]

    k_df = E_calc_df[(E_calc_df['economy_code'] == economy) &
                     (E_calc_df['variable'] == 'Capital stock')]\
                        .copy().set_index('year') 
    
    k_df['K^alpha'] = k_df['value'] ** ALPHA
    k_df = k_df[['K^alpha']]

    y_df = E_calc_df[(E_calc_df['economy_code'] == economy) &
                     (E_calc_df['variable'] == 'Real GDP PPP 2017 USD')]\
                        .copy().set_index('year')[['value']].rename(columns = {'value': 'Output_y'})

    eqn_df = pd.concat([y_df, labour_df, k_df], axis = 1)

    eqn_df['E'] = (eqn_df['Output_y'] / (eqn_df['L^1-alpha'] * eqn_df['K^alpha'])) ** (1/ (1 - ALPHA))
    eqn_df = eqn_df.reset_index(drop = False)\
        [['year', 'economy_code', 'economy', 'Output_y', 'L^1-alpha', 'K^alpha', 'E']]

    E_estimate = pd.concat([E_estimate, eqn_df]).reset_index(drop = True)

# E_estimate charts

# Save E estimate data frame

E_df = E_estimate.copy()

E_df['variable'] = 'Labour efficiency'

E_df = E_df[['economy_code', 'economy', 'year', 'variable', 'E']]\
    .rename(columns = {'E': 'value'}).reset_index(drop = True)

E_df['percent'] = E_df.groupby(['economy', 'variable'], 
                               group_keys = False)\
                                ['value'].apply(pd.Series.pct_change)

E_df['source'] = 'Derived'

E_df.to_csv('./data/labour_efficiency_estimate_to2027.csv', index = False)

# Save location for charts
lab_eff = './results/labour_efficiency/'

if not os.path.isdir(lab_eff):
    os.makedirs(lab_eff)

for economy in APEC_econcode.values():
    chart_df = E_df[E_df['economy_code'] == economy].copy().reset_index(drop = True)
    
    if chart_df['value'].isna().sum() == len(chart_df['value']):
        pass

    else:

        fig, axs = plt.subplots(2, 1)

        sns.set_theme(style = 'ticks')

        # Labour efficiency
        sns.lineplot(ax = axs[0],
                    data = chart_df,
                    x = 'year',
                    y = 'value')
        
        axs[0].set(title = economy + ' labour efficiency estimate', 
                    xlabel = 'Year', 
                    ylabel = 'Labour efficiency')
        
        # Labour efficiency growth
        sns.lineplot(ax = axs[1],
                    data = chart_df,
                    x = 'year',
                    y = 'percent')
        
        axs[1].set(title = economy + ' labour efficiency growth', 
                    xlabel = 'Year', 
                    ylabel = 'Labour efficiency growth')
        
        plt.tight_layout()
        fig.savefig(lab_eff + economy + '_labour_efficiency.png')
        plt.close()
#%%
