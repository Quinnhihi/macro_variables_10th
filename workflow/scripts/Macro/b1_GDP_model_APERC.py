#%%
# Solow Swan Growth estimates for APEC economies - 10th Outlook Update

import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re
import openpyxl

# Change the working drive
wanted_wd = 'macro_variables_10th'
try:
    os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)
except Exception:
    pass 

# Load Economy Codes from static input folder
APEC_econcode = pd.read_csv('./data_source/APEC_economy_code.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

# 1. Import Generated Dataframes (from results/data) ---
# Note: Variable names in these files are 'pop_jan', 'Labour efficiency', and 'Capital stock'
UN_df = pd.read_csv('./results/data/undesa_pop_to2100.csv')
IMF_df = pd.read_csv('./results/data/IMF_to2030.csv')
lab_eff = pd.read_csv('./results/data/labour_efficiency_estimate_to2030.csv')
cap_df = pd.read_csv('./results/data/capital_stock.csv')

input_df = pd.concat([UN_df, IMF_df, lab_eff, cap_df]).reset_index(drop = True)

# Standardize years and filter variables

input_df['year'] = pd.to_numeric(input_df['year'], errors='coerce')
input_df = input_df[(input_df['variable']\
                          .isin(['population_1jan', 'Real GDP PPP 2021 USD',
                                 'Labour efficiency', 'Capital stock'])) &
                     (input_df['year'] >= 1980)].copy()\
                                 .reset_index(drop = True)

# 2. Import 9th Outlook Data (Raw input from data_source) ---
GDP_9th = pd.read_csv('./data_source/00_APEC_GDP_data_2024_02_01.csv')
GDP_9th['year'] = pd.to_numeric(GDP_9th['year'], errors='coerce')
# --- ADDED: Rename specific economy codes ---
GDP_9th['economy_code'] = GDP_9th['economy_code'].replace({
    '17_SIN': '17_SGP', 
    '15_RP': '15_PHL'
})


GDP_9th['source'] = '9th Outlook'

# Save the long-format 9th outlook to the results data folder
os.makedirs('./results/data', exist_ok=True)
GDP_9th.to_csv('./results/data/GDP_9th.csv', index = False)

# 3. Build Baseline GDP Dataframe ---
GDP_df1 = pd.DataFrame()

for economy in APEC_econcode.values():
    # Filter using 'population_1jan'
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
GDP_df1.to_csv('./results/data/gdp_df1.csv', index = False)

# Capital growth grab
cap_growth_df = cap_df[['economy_code', 'variable', 'year', 'percent']].copy().reset_index(drop = True)
cap_growth_df.to_csv('./results/data/cap_growth_df.csv', index = False)

# --- 4. Load Technical Inputs (from results/data) ---
delta_df = pd.read_csv('./results/data/PWT_delta_2023.csv')
savings_df = pd.read_csv('./results/data/IMF_savings_2030.csv')
save_invest_hist = pd.read_csv('./results/data/IMF_to2030.csv')
delta_hist = pd.read_csv('./results/data/PWT_cap_labour_to2023.csv')

def aperc_gdp_model(economy = '01_AUS',
                    input_data = GDP_df1,
                    labour_data = lab_eff,
                    delta_data = delta_df,
                    sav_data = savings_df,
                    GDP_9th = GDP_9th,
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
 
    # Labour efficiency calculation
    eff_df = labour_data[labour_data['economy_code'] == economy][['year', 'percent']]\
        .set_index('year', drop = True).iloc[-lab_eff_periods:]
   
    lab_eff_improvement = eff_df['percent'].sum() / lab_eff_periods

    # Update labour efficiency to 2101
    for year in range(2031, 2102, 1):
        # Calculate the rolling average of the 'percent' column safely
        rolling_avg = eff_df['percent'].iloc[-lab_eff_periods:].sum() / lab_eff_periods
        
        if rolling_avg > high_eff:
            eff_df.loc[year, 'percent'] = rolling_avg - change_eff
        elif rolling_avg < low_eff:
            eff_df.loc[year, 'percent'] = rolling_avg + change_eff
        else:
            eff_df.loc[year, 'percent'] = eff_df.loc[year - 1, 'percent']


    # Labour efficiency application
    GDP_df2 = input_data[input_data['economy_code'] == economy].copy()
    GDP_df2 = GDP_df2.set_index('year')
   
    for year in range (2031, 2102, 1):
        GDP_df2.at[year, 'efficiency'] = GDP_df2.loc[year - 1, 'efficiency'] * \
            (1 + (eff_df.loc[year, 'percent']))

    # Save labour efficiency dataframe
    lab_eff_loc = './results/labour_efficiency/data/'
    os.makedirs(lab_eff_loc, exist_ok=True)
    GDP_df2[['economy_code', 'economy', 'labour', 'efficiency']].to_csv(lab_eff_loc + '{}_labour_efficiency_estimate.csv'.format(economy))

    # Force year to integer to ensure the merge works
    #GDP_9th['year'] = pd.to_numeric(GDP_9th['year'], errors='coerce')
    #GDP_df2 = GDP_df2.reset_index()
    #GDP_df2['year'] = pd.to_numeric(GDP_df2['year'], errors='coerce')

    # Solow Swan projection loop preparation
    savings = sav_data[sav_data['economy_code'] == economy]['value'].values[0] / 100
    delta = delta_data[delta_data['economy_code'] == economy]['value'].values[0]

    dyn_savings = pd.DataFrame(index = range(1980, 2102, 1), columns = ['savings'])
    dyn_savings.index.name = 'year'
    dyn_savings.loc[2031, 'savings'] = savings

    dyn_delta = pd.DataFrame(index = range(1980, 2102, 1), columns = ['delta'])
    dyn_delta.index.name = 'year'
    dyn_delta.loc[2031, 'delta'] = delta

    cap_growth = cap_growth_df[cap_growth_df['economy_code'] == economy][['year', 'percent']].set_index('year')

    # Solow-Swan Loop
    #GDP_df2 = GDP_df2.set_index('year')
    for year in range(2031, 2102, 1):
        # Savings dynamics
        if dyn_savings.loc[year, 'savings'] > high_sav:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings'] - change_sav
        elif dyn_savings.loc[year, 'savings'] < low_sav:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings'] + change_sav
        else:
            dyn_savings.loc[year + 1, 'savings'] = dyn_savings.loc[year, 'savings']

        # Depreciation dynamics
        if dyn_delta.loc[year, 'delta'] > high_delta:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta'] - change_del
        elif dyn_delta.loc[year, 'delta'] < low_delta:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta'] + change_del
        else:
            dyn_delta.loc[year + 1, 'delta'] = dyn_delta.loc[year, 'delta']
       
        # Capital Accumulation
        new_cap_calc = GDP_df2.loc[year - 1, 'capital']\
            - (GDP_df2.loc[year - 1, 'capital'] * dyn_delta.loc[year, 'delta'])\
                + (GDP_df2.loc[year - 1, 'real_output'] * dyn_savings.loc[year, 'savings'])
       
        cap_prev = GDP_df2.loc[year - 1, 'capital']
        cap_diff = (new_cap_calc / cap_prev) - 1

        if ((cap_diff / cap_growth.loc[year - 1, 'percent']) < (1 - cap_compare)) | ((cap_diff / cap_growth.loc[year - 1, 'percent']) > (1 + cap_compare)):
            GDP_df2.at[year, 'capital'] = GDP_df2.loc[year - 1, 'capital'] * (1 + (cap_growth.loc[year - 1, 'percent'] * (1 - cap_compare)))
            cap_growth.loc[year, 'percent'] = cap_growth.loc[year - 1, 'percent'] * (1 - cap_compare)
        else:
             GDP_df2.at[year, 'capital'] = new_cap_calc
             cap_growth.loc[year, 'percent'] = cap_diff

        # Cobb-Douglas Output
        GDP_df2.at[year, 'real_output'] = (GDP_df2.loc[year, 'capital']) ** alpha\
            * ((GDP_df2.loc[year, 'labour'] * GDP_df2.loc[year, 'efficiency']) ** (1 - alpha))

    # Grab historical savings
    for year in range(1980, 2031, 1):
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

    for year in range(1980, 2024, 1):
        dyn_delta.loc[year, 'delta'] = delta_hist[(delta_hist['variable'] == 'delta') &
                                                  (delta_hist['economy_code'] == economy)]\
                                                    .set_index('year')\
                                                    .loc[year, 'value']
        
    for year in range(2024, 2031, 1):
        dyn_delta.loc[year, 'delta'] = delta
    
    GDP_df2 = pd.concat([GDP_df2, dyn_savings, dyn_delta], axis = 1)

    
    # Finalize Data and Labels
    GDP_estimates = GDP_df2.reset_index()

    GDP_estimates['real_output_IMF'] = np.where(GDP_estimates['year'] <= 2030, GDP_estimates['real_output'], np.nan)
    
    GDP_estimates['real_output_projection'] = np.where(GDP_estimates['year'] > 2030, GDP_estimates['real_output'], np.nan)

    GDP_estimates['economy_code'] = GDP_estimates['economy_code'].astype(str)
    
    GDP_9th['economy_code'] = GDP_9th['economy_code'].astype(str)

   # Filter 9th Outlook to only look at real GDP rows before merging
    gdp_9th_filtered = GDP_9th[GDP_9th['variable'] == 'real_GDP'][['economy_code', 'year', 'value']]

    # Merge with the filtered 9th Outlook data
    GDP_estimates = GDP_estimates.merge(gdp_9th_filtered, on = ['economy_code', 'year'], how = 'left')\
        .rename(columns = {'value': 'real_output_9th'})


    # Melt for plotting
    GDP_estimates_long = GDP_estimates.melt(id_vars = ['economy_code', 'economy', 'year'])
    GDP_estimates_long['variable'] = GDP_estimates_long['variable'].map({
        'real_output_IMF': 'IMF GDP projections to 2030',
        'real_output_projection': 'APERC real GDP projections from 2030',
        'real_output_9th': '9th Outlook projections',
        'labour': 'Population', 
        'capital': 'Capital stock', 
        'efficiency':'Labour efficiency',
        'savings': 'Savings',
        'delta': 'Depreciation'
    })

# Save CSV Results
    GDP_result_path = './results/GDP_estimates/data/'
    os.makedirs(GDP_result_path, exist_ok=True)
    GDP_estimates_long.to_csv(GDP_result_path + '{}_GDP_estimate.csv'.format(economy), index = False)

# Plotting
    GDP_charts = './results/GDP_estimates/'
    os.makedirs(GDP_charts, exist_ok=True)
   
   # Chart the results
    GDP_df = GDP_estimates_long[GDP_estimates_long['year'] <= 2070].copy().reset_index(drop = True)
    GDP_df = GDP_df[(GDP_df['variable']\
                     .isin(['IMF GDP projections to 2030',
                            'APERC real GDP projections from 2030']))]\
                                .copy().reset_index(drop = True)
    
    GDP_9th = GDP_estimates_long[(GDP_estimates_long['variable'].isin(['9th Outlook projections']))]\
                                        .copy().reset_index(drop = True)
    fig, ax = plt.subplots()

    sns.set_theme(style = 'ticks')
    custom_palette = {'IMF GDP projections to 2030': sns.color_palette('Paired', 6).as_hex()[0],
                      'APERC real GDP projections from 2030' : sns.color_palette('Paired', 6).as_hex()[1],
                      '9th Outlook projections': sns.color_palette('Dark2', 6).as_hex()[1]}

    # real GDP IMF 
    sns.lineplot(ax = ax,
                 data = GDP_df,
                 x = 'year',
                 y = 'value',
                 hue = 'variable',
                 palette = custom_palette)
    
    # real GDP 9th
    sns.lineplot(ax = ax,
                 data = GDP_9th,
                 x = 'year',
                 y = 'value',
                 hue = 'variable',
                 palette = custom_palette)
    
    ax.lines[1].set_linestyle('--')
    
    leg = ax.legend(title = '', 
                    fontsize = 8)
    
    leg_lines = leg.get_lines()

    leg_lines[1].set_linestyle('--')
    
    ax.set(title = economy + ' Real GDP (2021 USD PPP)', 
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

# --- 5. Run the Model for All Economies ---
if __name__ == "__main__":
    # Loop through each economy code in your dictionary and run the model
    for econ_code in APEC_econcode.values():
        print(f"Processing model and generating charts for: {econ_code}")
        try:
            aperc_gdp_model(economy=econ_code)
        except Exception as e:
            print(f"Error processing {econ_code}: {e}")

print("\nBatch processing complete. Check results folder.")
# %%
