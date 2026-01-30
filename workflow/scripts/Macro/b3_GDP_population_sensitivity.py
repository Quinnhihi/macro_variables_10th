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

# FOR NOW: Run 2a GDP_model_APERC prior to executing this script
# Import function from prior script
# from GDP_model_APERC import aperc_gdp_model

# Change the working drive
wanted_wd = 'macro_variables_9th'
os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)

# APEC economy codes
APEC_econcode = pd.read_csv('./data/APEC_economy_code.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

# Import required dataframes for sensitivity

UN_low = pd.read_csv('./data/UN_DESA/undesa_pop_to2100_Low.csv')
UN_med = pd.read_csv('./data/UN_DESA/undesa_pop_to2100_Medium.csv')
UN_high = pd.read_csv('./data/UN_DESA/undesa_pop_to2100_High.csv')

pop_dict = {'low': UN_low,
            'med': UN_med,
            'high': UN_high}

input_GDP = {}

for key, val in pop_dict.items():
    input_df = pd.concat([val, IMF_df, lab_eff, cap_df]).reset_index(drop = True)

    input_df = input_df[(input_df['variable']\
                            .isin(['population_1jan', 'Real GDP PPP 2017 USD', 
                                    'Labour efficiency', 'Capital stock'])) &
                        (input_df['year'] >= 1980)].copy()\
                                    .reset_index(drop = True)
    
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
    input_GDP['GDP_{0}'.format(key)] = GDP_df1

# Change directory to save these sensitivty results into
# Change the working drive
wanted_wd = '\\results\sensitivity'

if not os.path.isdir(os.getcwd() + wanted_wd):
    os.makedirs(os.getcwd() + wanted_wd)

os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)

# Now run the function with new input data
# input_data = input_GDP[input]
up_one_level = 'sensitivity'

for input in ['GDP_low', 'GDP_med', 'GDP_high']:
    wanted_wd = re.split(up_one_level, os.getcwd())[0] + up_one_level + '\\' + input

    if not os.path.isdir(wanted_wd):
        os.makedirs(wanted_wd)

    os.chdir(re.split(up_one_level, os.getcwd())[0] + up_one_level + '\\' + input)
    # 01_AUS
    aperc_gdp_model(economy = '01_AUS', input_data = input_GDP[input])

    # 02_BD
    aperc_gdp_model(economy = '02_BD', cap_compare = 0.2, input_data = input_GDP[input])

    # 03_CDA
    aperc_gdp_model(economy = '03_CDA', input_data = input_GDP[input])

    # 04_CHL
    aperc_gdp_model(economy = '04_CHL', input_data = input_GDP[input])

    # 05_PRC
    aperc_gdp_model(economy = '05_PRC', change_sav = 0.02, change_eff = 0.004, cap_compare = 0.1, input_data = input_GDP[input])

    # 06_HKC
    aperc_gdp_model(economy = '06_HKC', low_sav = 0.24, change_sav = 0.01, input_data = input_GDP[input])

    # 07_INA
    aperc_gdp_model(economy = '07_INA', lab_eff_periods = 5, high_eff = 0.03, low_delta = 0.04, cap_compare = 0.04, input_data = input_GDP[input])

    # 08_JPN
    aperc_gdp_model(economy = '08_JPN', cap_compare = 0.0001, input_data = input_GDP[input])

    # 09_ROK
    aperc_gdp_model(economy = '09_ROK', low_eff = 0.010, high_eff = 0.0125, input_data = input_GDP[input])

    # 10_MAS
    aperc_gdp_model(economy = '10_MAS', high_eff = 0.025, cap_compare = 0.1, input_data = input_GDP[input])

    # 11_MEX
    aperc_gdp_model(economy = '11_MEX', low_sav = 0.24, cap_compare = 0.01, input_data = input_GDP[input])

    # 12_NZ
    aperc_gdp_model(economy = '12_NZ', input_data = input_GDP[input])

    # 13_PNG
    aperc_gdp_model(economy = '13_PNG', lab_eff_periods = 1, low_eff = 0.06, high_eff = 0.08, change_eff = 0.013, input_data = input_GDP[input])

    # 14_PE
    aperc_gdp_model(economy = '14_PE', input_data = input_GDP[input])

    # 15_RP
    aperc_gdp_model(economy = '15_RP', input_data = input_GDP[input])

    # 16_RUS
    aperc_gdp_model(economy = '16_RUS', cap_compare = 0.0, input_data = input_GDP[input])

    # 17_SIN
    aperc_gdp_model(economy = '17_SIN', input_data = input_GDP[input])

    # 18_CT
    aperc_gdp_model(economy = '18_CT', input_data = input_GDP[input])

    # 19_THA
    aperc_gdp_model(economy = '19_THA', low_eff = 0.016, high_eff = 0.02, high_sav = 0.34, cap_compare = 0.001, input_data = input_GDP[input])

    # 20_USA
    aperc_gdp_model(economy = '20_USA', input_data = input_GDP[input])

    # 21_VN
    aperc_gdp_model(economy = '21_VN', change_sav = 0.01, low_eff = 0.01, change_eff = 0.005, input_data = input_GDP[input])

# Build some charts based on the above output

wanted_wd = 'macro_variables_9th'
os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)

for economy in APEC_econcode.values():
    new_df = pd.DataFrame()
    for location in ['GDP_low', 'GDP_med', 'GDP_high']:    
        temp_df = pd.read_csv('./results/sensitivity/' + location + '/results/GDP_estimates/data/' + economy + '_GDP_estimate.csv')
        temp_df = temp_df[temp_df['variable'].isin(['IMF GDP projections to 2027', 'APERC real GDP projections from 2027'])].reset_index(drop = True)
        temp_df['population'] = location

        new_df = pd.concat([new_df, temp_df]).reset_index(drop = True)

    split_1 = new_df[new_df['population'].isin(['GDP_low', 'GDP_high'])].copy().reset_index(drop = True)
    split_2 = new_df[~new_df['population'].isin(['GDP_low', 'GDP_high'])].copy().reset_index(drop = True)

    split_1 = split_1[split_1['variable'] != 'IMF GDP projections to 2027'].copy()

    new_df = pd.concat([split_1, split_2]).copy().reset_index(drop = True)

    new_df.to_csv('./results/sensitivity/' + economy + '.csv', index = False)

    # GDP sensitivity chart location
    GDP_charts = './results/sensitivity/charts/'

    if not os.path.isdir(GDP_charts):
        os.makedirs(GDP_charts)

    # Chart the results
    fig, ax = plt.subplots()

    sns.set_theme(style = 'ticks')

    # real GDP IMF 
    sns.lineplot(ax = ax,
                 data = new_df,
                 x = 'year',
                 y = 'value',
                 hue = 'population',
                 palette = sns.color_palette('magma', 3))
    
    plt.legend(title = '', 
               fontsize = 8)
    
    ax.set(title = economy + ' GDP population sensitivity', 
           xlabel = 'Year', 
           ylabel = 'Real output (millions)',
           xlim = (1980, 2070))
    
    plt.tight_layout()
    fig.savefig(GDP_charts + economy + '_GDP_sensitivity.png')
    plt.show()
    plt.close()
#%%
