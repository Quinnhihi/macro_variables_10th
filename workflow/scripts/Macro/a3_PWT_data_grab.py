#%%
# =====================================================
# A3: PWT 11.0 PIPELINE (UPDATED TO 2023)
# =====================================================

import pandas as pd
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
# APEC LIST
# =====================================================
APEC = [
    'Australia', 'Brunei Darussalam', 'Canada', 'Chile', 'China',
    'China, Hong Kong SAR', 'Indonesia', 'Japan', 'Republic of Korea',
    'Malaysia', 'Mexico', 'New Zealand', 'Papua New Guinea', 'Peru',
    'Philippines', 'Russian Federation', 'Singapore', 'Taiwan',
    'Thailand', 'United States', 'Viet Nam'
]

# =====================================================
# PATHS
# =====================================================
base_path = "./data_source/"
data_output_loc = "./results/data/"
PWT_chart_folder = './results/PWT/'

os.makedirs(PWT_chart_folder, exist_ok=True)
os.makedirs(data_output_loc, exist_ok=True)

# =====================================================
# LOAD DATA
# =====================================================
PWT_df = pd.read_excel(base_path + 'pwt110.xlsx', sheet_name='Data', engine='openpyxl')

# =====================================================
# CLEAN COUNTRY NAMES
# =====================================================
replace = {
    'China, Hong Kong SAR': 'Hong Kong, China',
    'Republic of Korea': 'Korea',
    'Russian Federation': 'Russia',
    'Taiwan': 'Chinese Taipei',
    'United States': 'United States of America'
}

PWT_df.replace(replace, inplace=True)
APEC = [replace.get(e, e) for e in APEC]

# =====================================================
# FILTER APEC
# =====================================================
PWT_df = PWT_df[PWT_df['country'].isin(APEC)].copy().reset_index(drop=True)

# =====================================================
# SELECT VARIABLES
# =====================================================
PWT_df = PWT_df[['country', 'year', 'pop', 'emp', 'avh', 'rgdpna', 'rnna', 'rtfpna', 'delta']].copy()

PWT_df = PWT_df.rename(columns={
    'country': 'economy',
    'pop': 'population',
    'emp': 'employed',
    'avh': 'avg_hours'
})

# =====================================================
# CREATE OUTPUT/CAPITAL RATIO
# =====================================================
PWT_df['output_to_kstock'] = PWT_df['rgdpna'] / PWT_df['rnna']

# =====================================================
# ADD PNG DATA (RESTORED OVERRIDES)
# =====================================================
PNG_data = PWT_df[PWT_df['economy'] == 'Australia'][
    ['economy', 'year', 'delta', 'output_to_kstock']
].copy()

PNG_data['economy'] = 'Papua New Guinea'
PNG_data['delta'] = 0.06
PNG_data['output_to_kstock'] = 0.5

PWT_df = pd.concat([PWT_df, PNG_data], ignore_index=True)

# =====================================================
# CHARTS
# =====================================================
for economy in APEC:
    chart_df = PWT_df[PWT_df['economy'] == economy]
    if chart_df.empty:
        continue

    fig, axs = plt.subplots(2, 2, figsize=(10, 7))

    sns.lineplot(ax=axs[0, 0], data=chart_df, x='year', y='population')
    axs[0, 0].set(title=f"{economy} PWT Population", xlabel="Year", ylabel="Population (Millions)")
    axs[0, 0].grid(True)

    sns.lineplot(ax=axs[0, 1], data=chart_df, x='year', y='rnna')
    axs[0, 1].set(title=f"{economy} PWT Capital Stock", xlabel="Year", ylabel="Real Capital Stock")
    axs[0, 1].grid(True)

    sns.lineplot(ax=axs[1, 0], data=chart_df, x='year', y='rgdpna')
    axs[1, 0].set(title=f"{economy} PWT Real GDP", xlabel="Year", ylabel="Real GDP (Millions)")
    axs[1, 0].grid(True)

    sns.lineplot(ax=axs[1, 1], data=chart_df, x='year', y='delta')
    axs[1, 1].set(title=f"{economy} PWT Depreciation", xlabel="Year", ylabel="Depreciation")
    axs[1, 1].grid(True)

    plt.tight_layout()
    fig.savefig(PWT_chart_folder + f"{economy.replace(' ', '_')}_PWT_data.png")
    plt.close()

# =====================================================
# OUTPUT TO CAPITAL CHART
# =====================================================
for economy in APEC:
    chart_df = PWT_df[PWT_df['economy'] == economy]
    if chart_df.empty:
        continue

    fig, ax = plt.subplots()
    sns.lineplot(ax=ax, data=chart_df, x='year', y='output_to_kstock')
    ax.set(title=f"{economy} PWT Output to Capital Stock", xlabel="Year", ylabel="Output to Capital Ratio")
    ax.grid(True)
    plt.tight_layout()
    fig.savefig(PWT_chart_folder + f"{economy.replace(' ', '_')}_output_cap.png")
    plt.close()

# =====================================================
# LONG FORMAT
# =====================================================
APEC_econcode = pd.read_csv(
    base_path + 'APEC_economy_code.csv',
    header=None,
    index_col=0
).squeeze().to_dict()

PWT_df['economy_code'] = PWT_df['economy'].map(APEC_econcode)

PWT_df_long = PWT_df.melt(
    id_vars=['economy_code', 'economy', 'year'],
    value_vars=['employed', 'avg_hours', 'rgdpna', 'rnna', 'rtfpna', 'delta', 'output_to_kstock'],
    var_name='variable',
    value_name='value'
)

# =====================================================
# MAP VARIABLE NAMES TO MATCH B1 SCHEMA
# =====================================================
# b1 expects 'Capital stock' not 'rnna', so we map it here
variable_rename = {
    'rnna': 'Capital stock',
    'rgdpna': 'Real GDP (PWT)',
    'rtfpna': 'TFP',
    'employed': 'Employment',
    'avg_hours': 'Average hours',
    'delta': 'delta',
    'output_to_kstock': 'output_to_kstock'
}

PWT_df_long['variable'] = PWT_df_long['variable'].replace(variable_rename)

# =====================================================
# GROWTH RATE
# =====================================================
PWT_df_long['percent'] = PWT_df_long.groupby(
    ['economy', 'variable'],
    group_keys=False
)['value'].pct_change()

PWT_df_long['source'] = 'PWT'
PWT_df_long = PWT_df_long.sort_values(['economy_code', 'variable', 'year']).reset_index(drop=True)

# =====================================================
# SAVE TO RESULTS/DATA
# =====================================================
PWT_df_long.to_csv(data_output_loc + 'PWT_cap_labour_to2023.csv', index=False)
print(f"✅ PWT_cap_labour_to2023.csv saved with {len(PWT_df_long)} rows")

# =====================================================
# DELTA SNAPSHOT FOR 2023
# =====================================================
PWT_delta = PWT_df_long[
    (PWT_df_long['variable'] == 'delta') &
    (PWT_df_long['year'] == 2023)
][['economy_code', 'year', 'variable', 'value', 'source']].reset_index(drop=True)

PWT_delta.to_csv(data_output_loc + 'PWT_delta_2023.csv', index=False)
print(f"✅ PWT_delta_2023.csv saved with {len(PWT_delta)} economies")

print("✅ A3 PWT Pipeline Completed")
#%%


