#%%
# =====================================================
# A1: UN DESA POPULATION DATA PIPELINE
# =====================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

# =====================================================
# WORKING DIRECTORY
# =====================================================
wanted_wd = 'macro_variables_10th'
try:
    os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)
except:
    pass

sns.set_theme(style='ticks')

# =====================================================
# PATHS
# =====================================================
base_path = './data_source/'
results_path = './results/'
population_full = results_path + 'population/'
population_hml = results_path + 'population_hml/'
population_medium = results_path + 'population_medium/'
data_output_loc = results_path + 'data/'

for f in [population_full, population_hml, population_medium, data_output_loc]:
    os.makedirs(f, exist_ok=True)

# =====================================================
# APEC LIST & NAME CLEANING
# =====================================================
APEC = [
    'Australia', 'Brunei Darussalam', 'Canada', 'Chile', 'China',
    'China, Hong Kong SAR', 'Indonesia', 'Japan', 'Republic of Korea',
    'Malaysia', 'Mexico', 'New Zealand', 'Papua New Guinea', 'Peru',
    'Philippines', 'Russian Federation', 'Singapore',
    'China, Taiwan Province of China', 'Thailand',
    'United States of America', 'Viet Nam'
]

dict_to_replace = {
    'China, Hong Kong SAR': 'Hong Kong, China',
    'Republic of Korea': 'Korea',
    'Russian Federation': 'Russia',
    'China, Taiwan Province of China': 'Chinese Taipei'
}

APEC_clean = [dict_to_replace.get(e, e) for e in APEC]

# =====================================================
# LOAD REFERENCE MAPPINGS
# =====================================================
APEC_econcode = pd.read_csv(
    base_path + 'APEC_economy_code.csv',
    header=None,
    index_col=0
).squeeze().to_dict()

pop_choice = pd.read_csv(
    base_path + 'APEC_population.csv',
    header=None,
    index_col=0
).squeeze().to_dict()

APEC_econcode = {dict_to_replace.get(k, k): v for k, v in APEC_econcode.items()}
pop_choice = {dict_to_replace.get(k, k): v for k, v in pop_choice.items()}

# =====================================================
# LOAD UN DESA DATA
# =====================================================
undesa_hist = pd.read_csv(base_path + 'WPP2024_Demographic_Indicators_Medium.csv')
undesa_proj = pd.read_csv(base_path + 'WPP2024_Demographic_Indicators_OtherVariants.csv')

cols = ['Location', 'Variant', 'Time', 'TPopulation1Jan', 'TPopulation1July', 'NetMigrations']

undesa_hist = undesa_hist[undesa_hist['Location'].isin(APEC)].copy()
undesa_proj = undesa_proj[undesa_proj['Location'].isin(APEC)].copy()

undesa_hist = undesa_hist[cols].copy()
undesa_proj = undesa_proj[cols].copy()

undesa_hist.replace(dict_to_replace, inplace=True)
undesa_proj.replace(dict_to_replace, inplace=True)

undesa_apec = pd.concat([undesa_hist, undesa_proj], ignore_index=True)

# =====================================================
# FORMATTER TO MATCH ORIGINAL OUTPUT STRUCTURE
# =====================================================
def format_to_original(df):
    df = df.rename(columns={
        'Economy': 'economy_code',
        'Location': 'economy',
        'Variant': 'variant',
        'Time': 'year',
        'TPopulation1Jan': 'population_1jan',
        'TPopulation1July': 'population_1jul',
        'NetMigrations': 'net_migration'
    }).copy()

    # IMPORTANT FIX:
    # original pipeline scale used population in thousands
    df['population_1jan'] = df['population_1jan'] 
    df['population_1jul'] = df['population_1jul']

    df = df.melt(
        id_vars=['economy', 'economy_code', 'year', 'variant'],
        value_vars=['population_1jan', 'population_1jul', 'net_migration']
    ).reset_index(drop=True)

    df = df[['economy_code', 'economy', 'year', 'variant', 'variable', 'value']]
    df['percent'] = df.groupby(['economy', 'variable'], group_keys=False)['value'].apply(pd.Series.pct_change)
    df['source'] = 'UN DESA'
    return df

# =====================================================
# 1. FULL VARIANT CHARTS
# =====================================================
palette = sns.color_palette('rocket', 15)

for economy in APEC_clean:
    chart_df = undesa_apec[undesa_apec['Location'] == economy].copy()
    if chart_df.empty:
        continue

    chart_df['TPopulation1Jan'] = chart_df['TPopulation1Jan']

    sizes = {a: 1 for a in chart_df['Variant'].unique()}
    sizes.update({'Medium': 4})

    fig, ax = plt.subplots()
    sns.lineplot(
        ax=ax,
        data=chart_df,
        x='Time',
        y='TPopulation1Jan',
        hue='Variant',
        palette=palette,
        size='Variant',
        sizes=sizes
    )

    ax.set(
        title=f'{economy} population projections to 2100 (UN DESA)',
        xlabel='Year',
        ylabel='Population (thousands)',
        ylim=(0, max(chart_df['TPopulation1Jan']) * 1.1),
        xlim=(min(chart_df['Time']), 2100)
    )
    ax.grid(True)
    plt.legend(title='', fontsize=7)
    plt.tight_layout()
    fig.savefig(population_full + economy.replace(' ', '_') + '_population.png')
    plt.close()

# =====================================================
# 2. HML CHARTS
# =====================================================
for economy in APEC_clean:
    temp = undesa_apec[undesa_apec['Location'] == economy].copy()
    if temp.empty:
        continue

    temp['pop_thousands'] = temp['TPopulation1Jan'] 
    historical = temp[temp['Time'] <= 2023].copy()
    projection = temp[temp['Time'] >= 2024].copy()

    fig, ax = plt.subplots()
    sns.lineplot(ax=ax, data=historical, x='Time', y='pop_thousands', color='black', marker='o', label='Historical')

    for v, c in zip(['High', 'Medium', 'Low'], ['red', 'green', 'blue']):
        subset = projection[projection['Variant'] == v]
        if not subset.empty:
            sns.lineplot(ax=ax, data=subset, x='Time', y='pop_thousands', color=c, marker='o', label=f'Projection ({v})')

    ax.axvline(x=2024, color='gray', linestyle='--')
    ax.set(
        title=f'{economy} Population: Historical + High/Medium/Low Projections',
        xlabel='Year',
        ylabel='Population (thousands)'
    )
    ax.grid(True)
    ax.legend()
    plt.tight_layout()
    fig.savefig(population_hml + economy.replace(' ', '_') + '_population.png')
    plt.close()

# =====================================================
# 3. MEDIUM CHARTS
# =====================================================
for economy in APEC_clean:
    temp = undesa_apec[undesa_apec['Location'] == economy].copy()
    if temp.empty:
        continue

    temp['pop_thousands'] = temp['TPopulation1Jan'] 
    historical = temp[temp['Time'] <= 2023].copy()
    projection = temp[temp['Time'] >= 2024].copy()

    fig, ax = plt.subplots()
    sns.lineplot(ax=ax, data=historical, x='Time', y='pop_thousands', marker='o', color='blue', label='Historical')

    medium_proj = projection[projection['Variant'] == 'Medium']
    if not medium_proj.empty:
        sns.lineplot(
            ax=ax,
            data=medium_proj,
            x='Time',
            y='pop_thousands',
            marker='o',
            color=sns.color_palette("Set2")[1],
            label='Projection (Medium)'
        )

    ax.axvline(x=2024, color='gray', linestyle='--', linewidth=1)
    ax.set(
        title=f"{economy} Population: Historical + Projections to 2100",
        xlabel="Year",
        ylabel="Population (thousands)"
    )
    ax.grid(True)
    ax.legend()
    plt.tight_layout()
    fig.savefig(population_medium + economy.replace(' ', '_') + '_population.png')
    plt.close()

# =====================================================
# MAIN DATASET
# KEEP ORIGINAL CUT: HISTORICAL <= 2023, PROJECTION > 2023
# =====================================================
historical_df = undesa_apec[undesa_apec['Time'] <= 2023].copy()

projected_df = pd.DataFrame()

for economy in APEC_clean:
    chosen_variant = pop_choice.get(economy, 'Medium')

    temp_df = undesa_apec[
        (undesa_apec['Location'] == economy) &
        (undesa_apec['Time'] > 2023) &
        (undesa_apec['Variant'] == chosen_variant)
    ].copy().reset_index(drop=True)

    temp_df['Economy'] = APEC_econcode.get(economy)
    projected_df = pd.concat([projected_df, temp_df], ignore_index=True)

APEC_population_main = pd.concat([projected_df, historical_df], ignore_index=True)
APEC_population_main['Economy'] = APEC_population_main['Location'].map(APEC_econcode)

# =====================================================
# AUSTRALIA ADJUSTMENT
# =====================================================
AUS_pop_df = APEC_population_main[APEC_population_main['Location'] == 'Australia'].copy()
everything_else_df = APEC_population_main[APEC_population_main['Location'] != 'Australia'].copy()

additional_growth = 0.0015
for year in range(2023, 2102):
    mask = AUS_pop_df['Time'] == year
    AUS_pop_df.loc[mask, 'TPopulation1Jan'] = (
        AUS_pop_df.loc[mask, 'TPopulation1Jan'] * (1 + additional_growth) ** (year - 2023)
    )

APEC_population_main = pd.concat([AUS_pop_df, everything_else_df], ignore_index=True)
APEC_population_main = APEC_population_main.sort_values(['Economy', 'Time']).reset_index(drop=True)

final_main_dataset = format_to_original(APEC_population_main)
final_main_dataset.to_csv(data_output_loc + 'undesa_pop_to2100.csv', index=False)

# =====================================================
# SENSITIVITY DATASETS
# =====================================================
sens_configs = [
    ('Low', 'low'),
    ('Medium', 'med'),
    ('High', 'high')
]

for variant_name, label in sens_configs:
    projected_sens_df = pd.DataFrame()

    for economy in APEC_clean:
        temp_df = undesa_apec[
            (undesa_apec['Location'] == economy) &
            (undesa_apec['Time'] > 2023) &
            (undesa_apec['Variant'] == variant_name)
        ].copy().reset_index(drop=True)

        temp_df['Economy'] = APEC_econcode.get(economy)
        projected_sens_df = pd.concat([projected_sens_df, temp_df], ignore_index=True)

    APEC_population_sens = pd.concat([projected_sens_df, historical_df], ignore_index=True)
    APEC_population_sens['Economy'] = APEC_population_sens['Location'].map(APEC_econcode)
    APEC_population_sens = APEC_population_sens.sort_values(['Economy', 'Time']).reset_index(drop=True)

    final_sens_dataset = format_to_original(APEC_population_sens)
    final_sens_dataset.to_csv(data_output_loc + f'undesa_pop_to2100_{label}.csv', index=False)

print("✅ A1 Pipeline Complete. Saved:")
print(" - undesa_pop_to2100.csv")
print(" - undesa_pop_to2100_low.csv")
print(" - undesa_pop_to2100_med.csv")
print(" - undesa_pop_to2100_high.csv")
#%%

