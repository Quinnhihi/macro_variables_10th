#%%
# Solow Swan Growth estimates for APEC economies - Sensitivity Analysis

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

# IMPORT YOUR MODEL FUNCTION HERE
# Change the working drive
wanted_wd = 'macro_variables_10th'
try:
    os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)
except Exception:
    pass

from workflow.scripts.Macro.b1_GDP_model_APERC import aperc_gdp_model
# APEC economy codes
APEC_econcode = pd.read_csv('./data_source/APEC_economy_code.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

# --- 1. Import Required Dataframes ---
UN_low = pd.read_csv('./results/data/undesa_pop_to2100_low.csv')
UN_med = pd.read_csv('./results/data/undesa_pop_to2100_med.csv')
UN_high = pd.read_csv('./results/data/undesa_pop_to2100_high.csv')

# Load missing components required for the concat step
IMF_df = pd.read_csv('./results/data/IMF_to2030.csv')
lab_eff = pd.read_csv('./results/data/labour_efficiency_estimate_to2030.csv')
cap_df = pd.read_csv('./results/data/capital_stock.csv')

pop_dict = {'low': UN_low,
            'med': UN_med,
            'high': UN_high}

input_GDP = {}

# --- 2. Build Input Dictionaries ---
for key, val in pop_dict.items():
    input_df = pd.concat([val, IMF_df, lab_eff, cap_df]).reset_index(drop = True)

    input_df['year'] = pd.to_numeric(input_df['year'], errors='coerce')
    input_df = input_df[(input_df['variable']\
                            .isin(['population_1jan', 'Real GDP PPP 2021 USD', 
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
        
        interim_df1 = pop_df1.merge(eff_df1, how = 'left', on = 'year').copy()
        
        cap_df1 = input_df[(input_df['economy_code'] == economy) &
                        (input_df['variable'] == 'Capital stock')].copy()\
                            [['year', 'value']]\
                                .rename(columns = {'value': 'capital'}).reset_index(drop = True)
        
        interim_df2 = interim_df1.merge(cap_df1, how = 'left', on = 'year').copy()
        
        y_df1 = input_df[(input_df['economy_code'] == economy) &
                        (input_df['variable'] == 'Real GDP PPP 2021 USD')].copy()\
                            [['year', 'value']]\
                                .rename(columns = {'value': 'real_output'}).reset_index(drop = True)
        
        interim_df3 = interim_df2.merge(y_df1, how = 'left', on = 'year').copy()

        GDP_df1 = pd.concat([GDP_df1, interim_df3]).reset_index(drop = True)

    GDP_df1['year'] = GDP_df1['year'].astype(int)
    input_GDP['GDP_{0}'.format(key)] = GDP_df1

# 3. Execute Model for Sensitivities
base_sens_dir = './results/sensitivity/'
os.makedirs(base_sens_dir, exist_ok=True)

for input_key in ['GDP_low', 'GDP_med', 'GDP_high']:
    
    # Change working directory specifically for the function's internal saves
    scenario_dir = os.path.join(base_sens_dir, input_key)
    os.makedirs(scenario_dir, exist_ok=True)
    os.chdir(scenario_dir) 

    print(f"Running scenario: {input_key}")

    aperc_gdp_model(economy = '01_AUS', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '02_BD', cap_compare = 0.2, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '03_CDA', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '04_CHL', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '05_PRC', change_sav = 0.02, change_eff = 0.004, cap_compare = 0.1, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '06_HKC', low_sav = 0.24, change_sav = 0.01, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '07_INA', lab_eff_periods = 5, high_eff = 0.03, low_delta = 0.04, cap_compare = 0.04, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '08_JPN', cap_compare = 0.0001, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '09_ROK', low_eff = 0.010, high_eff = 0.0125, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '10_MAS', high_eff = 0.025, cap_compare = 0.1, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '11_MEX', low_sav = 0.24, cap_compare = 0.01, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '12_NZ', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '13_PNG', lab_eff_periods = 1, low_eff = 0.06, high_eff = 0.08, change_eff = 0.013, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '14_PE', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '15_PHL', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '16_RUS', cap_compare = 0.0, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '17_SGP', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '18_CT', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '19_THA', low_eff = 0.016, high_eff = 0.02, high_sav = 0.34, cap_compare = 0.001, input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '20_USA', input_data = input_GDP[input_key])
    aperc_gdp_model(economy = '21_VN', change_sav = 0.01, low_eff = 0.01, change_eff = 0.005, input_data = input_GDP[input_key])

    # Reset working directory to base before next loop
    os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)

# --- 4. Chart Generation ---
print("Generating Sensitivity Charts...")

GDP_charts = './results/sensitivity/charts/'
os.makedirs(GDP_charts, exist_ok=True)

for economy in APEC_econcode.values():
    new_df = pd.DataFrame()
    for location in ['GDP_low', 'GDP_med', 'GDP_high']:    
        # Ensure path matches the internal output structure of aperc_gdp_model
        file_path = f'./results/sensitivity/{location}/results/GDP_estimates/data/{economy}_GDP_estimate.csv'
        
        if os.path.exists(file_path):
            temp_df = pd.read_csv(file_path)
            temp_df = temp_df[temp_df['variable'].isin(['IMF GDP projections to 2030', 'APERC real GDP projections from 2030'])].reset_index(drop = True)
            temp_df['population'] = location
            new_df = pd.concat([new_df, temp_df]).reset_index(drop = True)

    if new_df.empty:
        continue

    split_1 = new_df[new_df['population'].isin(['GDP_low', 'GDP_high'])].copy().reset_index(drop = True)
    split_2 = new_df[~new_df['population'].isin(['GDP_low', 'GDP_high'])].copy().reset_index(drop = True)

    split_1 = split_1[split_1['variable'] != 'IMF GDP projections to 2030'].copy()

    new_df = pd.concat([split_1, split_2]).copy().reset_index(drop = True)
    new_df.to_csv(f'./results/sensitivity/{economy}.csv', index = False)

    # Chart the results
    fig, ax = plt.subplots()
    sns.set_theme(style = 'ticks')

    sns.lineplot(ax = ax,
                 data = new_df,
                 x = 'year',
                 y = 'value',
                 hue = 'population',
                 palette = sns.color_palette('magma', 3))
    
    plt.legend(title = '', fontsize = 8)
    
    ax.set(title = economy + ' GDP population sensitivity', 
           xlabel = 'Year', 
           ylabel = 'Real output (millions)',
           xlim = (1980, 2070))
    
    plt.tight_layout()
    fig.savefig(GDP_charts + economy + '_GDP_sensitivity.png')
    plt.close()

print("Sensitivity analysis complete.")
#%%


