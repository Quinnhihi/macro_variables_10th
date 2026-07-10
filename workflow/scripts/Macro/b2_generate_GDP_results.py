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
import datetime

# Change the working drive
wanted_wd = 'macro_variables_10th'
try:
    os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)
except Exception:
    pass

# Load Economy Codes from static input folder
APEC_econcode = pd.read_csv('./data_source/APEC_economy_code.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

# Date
timestamp = datetime.datetime.now().strftime('%Y_%m_%d')

# 1. Import Generated Dataframes (from results/data)
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

# --- 2. Import 9th Outlook Data (Raw input from data_source) ---
GDP_9th = pd.read_csv('./data_source/00_APEC_GDP_data_2024_02_01.csv')
GDP_9th['year'] = pd.to_numeric(GDP_9th['year'], errors='coerce')

# Rename specific economy codes
GDP_9th['economy_code'] = GDP_9th['economy_code'].replace({
    '17_SIN': '17_SGP',
    '15_RP': '15_PHL'
})

GDP_9th['value'] = GDP_9th['value'] / (1000)
GDP_9th['source'] = '9th Outlook'

# Save the long-format 9th outlook to the results data folder
os.makedirs('./results/data', exist_ok=True)
GDP_9th.to_csv('./results/data/GDP_9th.csv', index = False)

# --- 3. Build Baseline GDP Dataframe ---
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
GDP_df1.to_csv('./results/data/gdp_df1.csv', index = False)

# Capital growth grab
cap_growth_df = cap_df[['economy_code', 'variable', 'year', 'percent']].copy().reset_index(drop = True)
cap_growth_df.to_csv('./results/data/cap_growth_df.csv', index = False)

# --- 4. Load Technical Inputs (from results/data) ---
delta_df = pd.read_csv('./results/data/PWT_delta_2023.csv')
savings_df = pd.read_csv('./results/data/IMF_savings_2030.csv')
save_invest_hist = pd.read_csv('./results/data/IMF_to2030.csv')
delta_hist = pd.read_csv('./results/data/PWT_cap_labour_to2023.csv')

# --- DEFINING THE MODEL ---
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
   
    GDP_9th_plot = GDP_estimates_long[(GDP_estimates_long['variable'].isin(['9th Outlook projections']))]\
                                        .copy().reset_index(drop = True)
    fig, ax = plt.subplots()

    sns.set_theme(style = 'ticks')
    custom_palette = {'IMF GDP projections to 2030': sns.color_palette('Paired', 6).as_hex()[0],
                      'APERC real GDP projections from 2030' : sns.color_palette('Paired', 6).as_hex()[1],
                      '9th Outlook projections': sns.color_palette('Dark2', 6).as_hex()[1]}

    # real GDP IMF and Projection
    sns.lineplot(ax = ax,
                 data = GDP_df,
                 x = 'year',
                 y = 'value',
                 hue = 'variable',
                 palette = custom_palette)
   
    # real GDP 9th
    sns.lineplot(ax = ax,
                 data = GDP_9th_plot,
                 x = 'year',
                 y = 'value',
                 hue = 'variable',
                 palette = custom_palette)
   
    if len(ax.lines) > 1:
        ax.lines[1].set_linestyle('--')
   
    leg = ax.legend(title = '', fontsize = 8)
    leg_lines = leg.get_lines()

    if len(leg_lines) > 1:
        leg_lines[1].set_linestyle('--')
   
    ax.set(title = economy + ' Real GDP (2021 USD PPP)',
           xlabel = 'Year',
           ylabel = 'Real output (millions)',
           xlim = (1980, 2070))
   
    plt.tight_layout()
    fig.savefig(GDP_charts + economy + '_GDP_estimates.png')
    plt.close()

    # Labour efficiency charts location
    lab_eff_charts = './results/labour_efficiency/To2100/'
    os.makedirs(lab_eff_charts, exist_ok=True)

    # Labour efficiency charts
    labeff_df = GDP_estimates_long[(GDP_estimates_long['variable'].isin(['Labour efficiency']))]\
                                        .copy().reset_index(drop = True)
   
    if not labeff_df['value'].isna().all():
        fig, ax = plt.subplots()
        sns.set_theme(style = 'ticks')

        sns.lineplot(ax = ax,
                     data = labeff_df,
                     x = 'year',
                     y = 'value')
       
        ax.set(title = economy + ' labour efficiency estimate',
               xlabel = 'Year',
               ylabel = 'Labour efficiency')
       
        plt.tight_layout()
        fig.savefig(lab_eff_charts + economy + '_labour_efficiency_to2100.png')
        plt.close()


# --- 5. Run the Model for Specific Economies ---
print("Starting economy-specific batch processing...")

aperc_gdp_model(economy = '01_AUS', change_del = 0.0002)
aperc_gdp_model(economy = '02_BD', cap_compare = 0.2)
aperc_gdp_model(economy = '03_CDA', change_del = 0.0002)
aperc_gdp_model(economy = '04_CHL', change_del = 0.0002, low_eff = 0.016, high_eff = 0.02)
aperc_gdp_model(economy = '05_PRC', high_sav = 0.2, low_sav = 0.18, change_sav = 0.006, lab_eff_periods = 10,
                change_eff = 0.003, low_eff = 0.01, high_eff = 0.013, high_delta = 0.054, low_delta = 0.052, cap_compare = 0.1)
aperc_gdp_model(economy = '06_HKC', low_sav = 0.24, change_sav = 0.01, change_del = 0.0002)
aperc_gdp_model(economy = '07_INA', lab_eff_periods = 5, high_eff = 0.03, change_eff = 0.001,
                low_delta = 0.04, change_sav = 0.0015, cap_compare = 0.04)
aperc_gdp_model(economy = '08_JPN', cap_compare = 0.0001)
aperc_gdp_model(economy = '09_ROK', low_eff = 0.012, high_eff = 0.015)
aperc_gdp_model(economy = '10_MAS', high_eff = 0.025, cap_compare = 0.1)
aperc_gdp_model(economy = '11_MEX', change_sav = 0.001, low_sav = 0.24, change_del = 0.0002, cap_compare = 0.01)
aperc_gdp_model(economy = '12_NZ', change_del = 0.0001, change_sav = 0.0005)
aperc_gdp_model(economy = '13_PNG', lab_eff_periods = 1, low_eff = 0.06, high_eff = 0.08, change_eff = 0.0075, change_del = 0.0002)
aperc_gdp_model(economy = '14_PE', lab_eff_periods = 7, change_eff = 0.0003)
aperc_gdp_model(economy = '15_PHL', change_del = 0.0001, lab_eff_periods = 5) # Note: changed from 15_RP to match dict
aperc_gdp_model(economy = '16_RUS', change_del = 0.0002, change_sav = 0.001, cap_compare = 0.0)
aperc_gdp_model(economy = '17_SGP', lab_eff_periods = 7, high_delta = 0.05, change_eff = 0.0001, change_sav = 0.001, change_del = 0.0003) # Note: changed from 17_SIN
aperc_gdp_model(economy = '18_CT', change_del = 0.0002, change_eff = 0.001, change_sav = 0.003)
aperc_gdp_model(economy = '19_THA', low_eff = 0.016, high_eff = 0.02, change_eff = 0.001, high_sav = 0.34, cap_compare = 0.001)
aperc_gdp_model(economy = '20_USA')
aperc_gdp_model(economy = '21_VN', change_sav = 0.003, lab_eff_periods = 5, change_eff = 0.00175, change_del = 0.0003)

# --- 6. Post Processing & Chart Generation ---
print("Combining data and generating final charts...")

# Data location mapped to where the function outputs the estimates
GDP_data = './results/GDP_estimates/data/'

# Save a combined dataframe from the results generated above
combined_df = pd.DataFrame()

for economy in APEC_econcode.values():
    if os.path.exists(GDP_data + '{}_GDP_estimate.csv'.format(economy)):
        individual_df = pd.read_csv(GDP_data + '{}_GDP_estimate.csv'.format(economy))
        combined_df = pd.concat([combined_df, individual_df]).reset_index(drop = True)

# Write combined data frame
combined_df.to_csv(GDP_data + 'combined_GDP_estimate_' + timestamp + '.csv', index = False)

# --- ADDED: Drop duplicates to ensure unique index before pivoting ---
combined_df = combined_df.drop_duplicates(subset=['economy_code', 'economy', 'year', 'variable'], keep='last')

# Generate some quick GDP per capita charts
APEC_gdp_pop = combined_df.pivot(columns = 'variable',
                                 values = 'value',
                                 index = ['economy_code', 'economy', 'year']).copy()\
                                    .reset_index(drop = False)


# Shifted splitting year to 2030 to match 10th Outlook models
APEC_gdp_pop['real_GDP'] = np.where(APEC_gdp_pop['year'] <= 2030,
                                    APEC_gdp_pop['IMF GDP projections to 2030'],
                                    APEC_gdp_pop['APERC real GDP projections from 2030'])

APEC_gdp_pop = APEC_gdp_pop[['economy_code', 'economy', 'year', 'real_GDP',
                             'Population', 'Labour efficiency', 'Depreciation', # Ensure 'Depreciation' is actually generated in the final loop if you need this
                             'Savings', 'Capital stock']].copy()\
                                .rename(columns = {'Population': 'population',
                                                   'Labour efficiency': 'lab_efficiency',
                                                   'Depreciation': 'depreciation',
                                                   'Savings': 'savings',
                                                   'Capital stock': 'k_stock'})

APEC_gdp_pop['GDP_per_capita'] = APEC_gdp_pop['real_GDP'] / APEC_gdp_pop['population'] * 1000

APEC_gdp_pop = APEC_gdp_pop.melt(id_vars = ['economy_code', 'economy', 'year']).copy()

# Define units
real_GDP = APEC_gdp_pop[APEC_gdp_pop['variable'] == 'real_GDP'].copy().reset_index(drop = True)
real_GDP['units'] = 'Millions (2021 USD PPP)'

population = APEC_gdp_pop[APEC_gdp_pop['variable'] == 'population'].copy().reset_index(drop = True)
population['units'] = 'Thousands'

lab_eff = APEC_gdp_pop[APEC_gdp_pop['variable'] == 'lab_efficiency'].copy().reset_index(drop = True)
lab_eff['units'] = 'Derived value (residual to model)'

depreciation = APEC_gdp_pop[APEC_gdp_pop['variable'] == 'depreciation'].copy().reset_index(drop = True)
depreciation['units'] = 'Proportion'

savings = APEC_gdp_pop[APEC_gdp_pop['variable'] == 'savings'].copy().reset_index(drop = True)
savings['units'] = 'Proportion'

k_stock = APEC_gdp_pop[APEC_gdp_pop['variable'] == 'k_stock'].copy().reset_index(drop = True)
k_stock['units'] = 'Millions (2021 USD)'

GDP_pc = APEC_gdp_pop[APEC_gdp_pop['variable'] == 'GDP_per_capita'].copy().reset_index(drop = True)
GDP_pc['units'] = 'USD PPP 2021'

APEC_gdp_data = pd.concat([real_GDP, population, lab_eff, depreciation, savings, k_stock, GDP_pc]).copy()
APEC_gdp_data = APEC_gdp_data.sort_values(['economy_code', 'variable', 'year']).copy().reset_index(drop = True)

APEC_gdp_data.to_csv(GDP_data + '00_APEC_GDP_data_' + timestamp + '.csv', index = False)

# Save space for GDP per capita charts
GDP_pc_dir = './results/GDP_estimates/per_capita/'
os.makedirs(GDP_pc_dir, exist_ok=True)

# Generate a dataframe that is only gdp and population
for economy in APEC_econcode.values():
    chart_df = APEC_gdp_pop[(APEC_gdp_pop['economy_code'] == economy) &
                            (APEC_gdp_pop['variable'] == 'GDP_per_capita')]\
        .copy().reset_index(drop = True)
   
    fig, ax = plt.subplots()
    sns.set_theme(style = 'ticks')

    # Per Capita Plot
    sns.lineplot(ax = ax,
                 data = chart_df,
                 x = 'year',
                 y = 'value')
   
    ax.set(title = economy + ' real GDP per capita',
                xlabel = 'Year',
                ylabel = 'GDP per capita (USD 2021 PPP)',
                xlim = (1980, 2070),
                ylim = (0))
   
    plt.tight_layout()
    fig.savefig(GDP_pc_dir + economy + '_gdp_pc.png')
    plt.close()

# APEC GDP per capita overall chart
palette = sns.color_palette('rocket', 21)
fig, ax = plt.subplots()

sns.set_theme(style = 'ticks')

sns.lineplot(ax = ax,
             data = APEC_gdp_pop[APEC_gdp_pop['variable'] == 'GDP_per_capita'],
             x = 'year',
             y = 'value',
             hue = 'economy',
             palette = palette)

ax.set(title = 'GDP per capita (USD 2021 PPP)',
       xlabel = 'Year',
       ylabel = 'GDP per capita',
       xlim = (1980, 2070),
       ylim = (0))

plt.legend(title = '', fontsize = 7)
plt.tight_layout()
fig.savefig(GDP_pc_dir + 'APEC_gdp_pc.png')
plt.close()

# GDP bar chart growth
GDP_growth_charts = './results/GDP_estimates/growth/'
os.makedirs(GDP_growth_charts, exist_ok=True)

for economy in APEC_econcode.values():
    rGDP_growth = APEC_gdp_pop[(APEC_gdp_pop['economy_code'] == economy) &
                            (APEC_gdp_pop['variable'] == 'real_GDP') &
                            (APEC_gdp_pop['year'] <= 2070)]\
                                .copy().reset_index(drop = True)
   
    rGDP_growth['percent'] = rGDP_growth.groupby(['economy', 'variable'],
                                                 group_keys = False)\
                                                    ['value'].apply(pd.Series.pct_change)
   
    fig, ax = plt.subplots()
    sns.set_theme(style = 'ticks')

    # Growth Bar Plot
    sns.barplot(ax = ax,
                data = rGDP_growth,
                x = 'year',
                y = 'percent',
                color = 'blue')
   
    ax.set(title = economy + ' real GDP growth',
           xlabel = 'Year: 1980 to 2070',
           ylabel = 'Percent',
           xticklabels = [])
   
    ax.tick_params(bottom = False)
    plt.tight_layout()
    fig.savefig(GDP_growth_charts + economy + '_gdp_growth.png')
    plt.close()

# Create charts for all relevant results people want to see
GDP_results = './results/GDP_estimates/input_data/'
os.makedirs(GDP_results, exist_ok=True)

for economy in APEC_econcode.values():
    rGDP_df = APEC_gdp_pop[(APEC_gdp_pop['economy_code'] == economy) &
                            (APEC_gdp_pop['variable'] == 'real_GDP') &
                            (APEC_gdp_pop['year'] <= 2070)]\
                                .copy().reset_index(drop = True)
   
    rGDP_growth = rGDP_df.copy()
    rGDP_growth['percent'] = rGDP_growth.groupby(['economy', 'variable'],
                                                 group_keys = False)\
                                                    ['value'].apply(pd.Series.pct_change)
   
    leff_df = APEC_gdp_pop[(APEC_gdp_pop['economy_code'] == economy) &
                            (APEC_gdp_pop['variable'] == 'lab_efficiency') &
                            (APEC_gdp_pop['year'] <= 2070)]\
                                .copy().reset_index(drop = True)
   
    leff_growth = leff_df.copy()
    leff_growth['percent'] = leff_growth.groupby(['economy', 'variable'],
                                                 group_keys = False)\
                                                    ['value'].apply(pd.Series.pct_change)
   
    dep_df = APEC_gdp_pop[(APEC_gdp_pop['economy_code'] == economy) &
                            (APEC_gdp_pop['variable'] == 'depreciation') &
                            (APEC_gdp_pop['year'] <= 2070)]\
                                .copy().reset_index(drop = True)
   
    sav_df = APEC_gdp_pop[(APEC_gdp_pop['economy_code'] == economy) &
                            (APEC_gdp_pop['variable'] == 'savings') &
                            (APEC_gdp_pop['year'] <= 2070)]\
                                .copy().reset_index(drop = True)
   
    k_df = APEC_gdp_pop[(APEC_gdp_pop['economy_code'] == economy) &
                            (APEC_gdp_pop['variable'] == 'k_stock') &
                            (APEC_gdp_pop['year'] <= 2070)]\
                                .copy().reset_index(drop = True)
   
    pop_df = APEC_gdp_pop[(APEC_gdp_pop['economy_code'] == economy) &
                            (APEC_gdp_pop['variable'] == 'population') &
                            (APEC_gdp_pop['year'] <= 2070)]\
                                .copy().reset_index(drop = True)
   
    fig, ax = plt.subplots(2, 3)
    sns.set_theme(style = 'ticks')

    # GDP
    sns.lineplot(ax = ax[0, 0], data = rGDP_df, x = 'year', y = 'value')
    ax[0, 0].set(title = economy + ' real GDP', xlabel = 'Year', ylabel = 'GDP (USD 2021 PPP)', xlim = (1980, 2070), ylim = (0))
   
    # leff
    sns.lineplot(ax = ax[0, 1], data = leff_growth, x = 'year', y = 'percent')
    ax[0, 1].set(title = economy + ' labour efficiency', xlabel = 'Year', ylabel = 'Labour efficiency', xlim = (1980, 2070))
   
    # depreciation
    sns.lineplot(ax = ax[0, 2], data = dep_df, x = 'year', y = 'value')
    ax[0, 2].set(title = economy + ' depreciation', xlabel = 'Year', ylabel = 'Depreciation', xlim = (1980, 2070))
   
    # savings
    sns.lineplot(ax = ax[1, 0], data = sav_df, x = 'year', y = 'value')
    ax[1, 0].set(title = economy + ' savings (% GDP)', xlabel = 'Year', ylabel = 'Savings', xlim = (1980, 2070))
   
    # K stock
    sns.lineplot(ax = ax[1, 1], data = k_df, x = 'year', y = 'value')
    ax[1, 1].set(title = economy + ' capital stock', xlabel = 'Year', ylabel = 'Capital stock', xlim = (1980, 2070))
   
    # Population
    sns.lineplot(ax = ax[1, 2], data = pop_df, x = 'year', y = 'value')
    ax[1, 2].set(title = economy + ' population', xlabel = 'Year', ylabel = 'Population', xlim = (1980, 2070))
   
    plt.tight_layout()
    fig.savefig(GDP_results + economy + '_gdp_results.png')
    plt.close()

print("\nProcess fully complete. All charts and data saved to GDP_estimates.")
#%%

