#%%
# =====================================================
# A4: COMBINED MINI PROJECTION PIPELINE (2026 UPDATE)
# Generates: Capital Stock, Labour Efficiency
# Inputs : a1 → undesa_pop_to2100.csv
#          a2 → IMF_to2030.csv
#          a3 → PWT_cap_labour_to2023.csv
# Outputs live in results
# =====================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

sns.set_theme(style='ticks')

# =====================================================
# WORKING DIRECTORY
# =====================================================
wanted_wd = 'macro_variables_10th'
try:
    os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)
except:
    pass

# =====================================================
# PATHS
# =====================================================
base_path       = './data_source/'
data_output_loc = './results/data/'
os.makedirs(data_output_loc, exist_ok=True)

# =====================================================
# LOAD INPUTS
# =====================================================
APEC_econcode = pd.read_csv(
    base_path + 'APEC_economy_code.csv',
    header=None, index_col=0
).squeeze().to_dict()

UN_df_long  = pd.read_csv(data_output_loc + 'undesa_pop_to2100.csv').copy()
IMF_df_long = pd.read_csv(data_output_loc + 'IMF_to2030.csv').copy()
PWT_df_long = pd.read_csv(data_output_loc + 'PWT_cap_labour_to2023.csv').copy()

# =====================================================
# NORMALISE ECONOMY NAMES
# =====================================================
name_fix = {
    'United States': 'United States of America',
    'Vietnam': 'Viet Nam',
}

UN_df_long['economy']  = UN_df_long['economy'].replace(name_fix)
IMF_df_long['economy'] = IMF_df_long['economy'].replace(name_fix)
PWT_df_long['economy'] = PWT_df_long['economy'].replace(name_fix)

UN_df_long['economy_code']  = UN_df_long['economy'].map(APEC_econcode)
IMF_df_long['economy_code'] = IMF_df_long['economy'].map(APEC_econcode)
PWT_df_long['economy_code'] = PWT_df_long['economy'].map(APEC_econcode)

all_codes = sorted(IMF_df_long['economy_code'].dropna().unique().tolist())

# =====================================================
# YEAR CONSTANTS
# =====================================================
YEAR_START   = 1980
YEAR_END_PWT = 2023
YEAR_END_IMF = 2030

# =====================================================
# GDP VARIABLE FALLBACK
# =====================================================
GDP_VAR_CANDIDATES = ['Real GDP PPP 2017 USD', 'Real GDP PPP 2021 USD']

# =====================================================
# SECTION 1: CAPITAL STOCK
# Old logic preserved as much as possible:
# capital = GDP / output_to_kstock
# output_to_kstock comes from PWT and is forward-filled after last PWT year
# =====================================================
capital_df = pd.DataFrame()

for economy in all_codes:

    IMF_temp = IMF_df_long[
        (IMF_df_long['economy_code'] == economy) &
        (IMF_df_long['variable'].isin(GDP_VAR_CANDIDATES))
    ].copy()

    # If both 2017 and 2021 versions exist, prefer 2017 to mimic old pipeline
    IMF_temp['gdp_priority'] = IMF_temp['variable'].map({
        'Real GDP PPP 2017 USD': 0,
        'Real GDP PPP 2021 USD': 1
    })
    IMF_temp = IMF_temp.sort_values(['year', 'gdp_priority']).drop_duplicates(
        subset=['year'], keep='first'
    ).drop(columns='gdp_priority')

    IMF_temp = IMF_temp.set_index('year')

    PWT_temp = PWT_df_long[
        (PWT_df_long['economy_code'] == economy) &
        (PWT_df_long['variable'] == 'output_to_kstock')
    ].copy()[['year', 'value']].rename(columns={'value': 'ratio'}).set_index('year')

    if IMF_temp.empty or PWT_temp.empty:
        continue

    capital_stock = pd.concat([IMF_temp, PWT_temp], axis=1).sort_index()
    capital_stock = capital_stock.loc[YEAR_START:YEAR_END_IMF, :].copy()

    # Forward-fill ratio exactly like the old logic
    capital_stock['ratio'] = capital_stock['ratio'].ffill()

    # For years after PWT ends, explicitly continue last known ratio
    for i in range(YEAR_END_PWT + 1, YEAR_END_IMF + 1):
        if i in capital_stock.index and pd.isna(capital_stock.loc[i, 'ratio']) and (i - 1) in capital_stock.index:
            capital_stock.loc[i, 'ratio'] = capital_stock.loc[i - 1, 'ratio']

    capital_stock['capital'] = capital_stock['value'] / capital_stock['ratio']
    capital_stock['variable'] = 'Capital stock'
    capital_stock['source'] = 'IMF and PWT calculation'

    capital_stock = capital_stock.reset_index(drop=False)
    capital_stock = capital_stock[['economy_code', 'economy', 'year', 'variable', 'capital', 'source']]
    capital_stock = capital_stock.rename(columns={'capital': 'value'})

    capital_stock['percent'] = capital_stock.groupby(
        ['economy', 'variable'], group_keys=False
    )['value'].apply(pd.Series.pct_change)

    capital_df = pd.concat([capital_df, capital_stock], axis=0).reset_index(drop=True)

# -------------------------------------------------------
# CAPITAL CHARTS
# -------------------------------------------------------
capital_chart_folder = './results/capital/'
os.makedirs(capital_chart_folder, exist_ok=True)

for economy in all_codes:
    chart_df = capital_df[capital_df['economy_code'] == economy].copy().reset_index(drop=True)

    if chart_df.empty or chart_df['value'].isna().all():
        continue

    fig, axs = plt.subplots(2, 1, figsize=(9, 6))

    sns.lineplot(ax=axs[0], data=chart_df, x='year', y='value')
    axs[0].set(title=economy + ' capital stock',
               xlabel='Year', ylabel='Capital stock')
    axs[0].grid(True)

    sns.lineplot(ax=axs[1], data=chart_df, x='year', y='percent')
    axs[1].set(title=economy + ' capital stock growth',
               xlabel='Year', ylabel='Capital stock growth')
    axs[1].grid(True)

    plt.tight_layout()
    fig.savefig(capital_chart_folder + economy + '_capital.png')
    plt.close()

capital_df.to_csv(data_output_loc + 'capital_stock.csv', index=False)
print("✅ Section 1 complete — capital_stock.csv saved.")

# =====================================================
# SECTION 2: LABOUR EFFICIENCY
# Cobb-Douglas:
# Y = K^α · (E·L)^(1-α)
# E = [Y / (K^α · L^(1-α))]^(1/(1-α))
# =====================================================
ALPHA = 0.4

IMF_subset = IMF_df_long[
    IMF_df_long['variable'].isin(GDP_VAR_CANDIDATES)
].copy()

IMF_subset['gdp_priority'] = IMF_subset['variable'].map({
    'Real GDP PPP 2017 USD': 0,
    'Real GDP PPP 2021 USD': 1
})
IMF_subset = IMF_subset.sort_values(['economy_code', 'year', 'gdp_priority']).drop_duplicates(
    subset=['economy_code', 'year'], keep='first'
).drop(columns='gdp_priority').reset_index(drop=True)

UN_subset = UN_df_long[
    (UN_df_long['variable'] == 'population_1jan') &
    (UN_df_long['year'].isin(range(YEAR_START, YEAR_END_IMF + 1)))
].copy().reset_index(drop=True)

E_calc_df = pd.concat([IMF_subset, UN_subset, capital_df], ignore_index=True)

E_estimate = pd.DataFrame()

for economy in all_codes:

    labour_df = E_calc_df[
        (E_calc_df['economy_code'] == economy) &
        (E_calc_df['variable'] == 'population_1jan')
    ].copy().set_index('year')

    labour_df['L^1-alpha'] = labour_df['value'] ** (1 - ALPHA)
    labour_df = labour_df[['economy_code', 'economy', 'L^1-alpha']]

    k_df = E_calc_df[
        (E_calc_df['economy_code'] == economy) &
        (E_calc_df['variable'] == 'Capital stock')
    ].copy().set_index('year')

    k_df['K^alpha'] = k_df['value'] ** ALPHA
    k_df = k_df[['K^alpha']]

    y_df = E_calc_df[
        (E_calc_df['economy_code'] == economy) &
        (E_calc_df['variable'].isin(GDP_VAR_CANDIDATES))
    ].copy()

    y_df['gdp_priority'] = y_df['variable'].map({
        'Real GDP PPP 2017 USD': 0,
        'Real GDP PPP 2021 USD': 1
    })
    y_df = y_df.sort_values(['year', 'gdp_priority']).drop_duplicates(
        subset=['year'], keep='first'
    ).drop(columns='gdp_priority')

    y_df = y_df.set_index('year')[['value']].rename(columns={'value': 'Output_y'})

    eqn_df = pd.concat([y_df, labour_df, k_df], axis=1)

    eqn_df['E'] = (
        eqn_df['Output_y'] / (eqn_df['L^1-alpha'] * eqn_df['K^alpha'])
    ) ** (1 / (1 - ALPHA))

    eqn_df = eqn_df.reset_index(drop=False)[
        ['year', 'economy_code', 'economy', 'Output_y', 'L^1-alpha', 'K^alpha', 'E']
    ]

    E_estimate = pd.concat([E_estimate, eqn_df]).reset_index(drop=True)

E_df = (
    E_estimate[['economy_code', 'economy', 'year', 'E']]
    .copy()
    .rename(columns={'E': 'value'})
)
E_df['variable'] = 'Labour efficiency'
E_df = E_df[['economy_code', 'economy', 'year', 'variable', 'value']].reset_index(drop=True)

E_df['percent'] = E_df.groupby(
    ['economy', 'variable'], group_keys=False
)['value'].apply(pd.Series.pct_change)

E_df['source'] = 'Derived'

E_df.to_csv(data_output_loc + 'labour_efficiency_estimate_to2030.csv', index=False)
print("✅ Section 2 complete — labour_efficiency_estimate_to2030.csv saved.")

# -------------------------------------------------------
# LABOUR EFFICIENCY CHARTS
# -------------------------------------------------------
lab_eff_folder = './results/labour_efficiency/'
os.makedirs(lab_eff_folder, exist_ok=True)

for economy in all_codes:
    chart_df = E_df[E_df['economy_code'] == economy].copy().reset_index(drop=True)

    if chart_df.empty or chart_df['value'].isna().all():
        continue

    fig, axs = plt.subplots(2, 1, figsize=(9, 6))

    sns.lineplot(ax=axs[0], data=chart_df, x='year', y='value')
    axs[0].set(title=economy + ' labour efficiency estimate',
               xlabel='Year', ylabel='Labour efficiency')
    axs[0].grid(True)

    sns.lineplot(ax=axs[1], data=chart_df, x='year', y='percent')
    axs[1].set(title=economy + ' labour efficiency growth',
               xlabel='Year', ylabel='Labour efficiency growth')
    axs[1].grid(True)

    plt.tight_layout()
    fig.savefig(lab_eff_folder + economy + '_labour_efficiency.png')
    plt.close()

print("✅ A4 Pipeline Complete.")
#%%


