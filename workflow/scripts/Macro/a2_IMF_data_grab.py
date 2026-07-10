# =====================================================
# IMF DATA PIPELINE (FINAL CLEAN VERSION ✅)
# =====================================================

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

sns.set_theme(style='ticks')

# =====================================================
# APEC LIST
# =====================================================

APEC = ['Australia','Brunei Darussalam','Canada','Chile','China',
        'Hong Kong, China','Indonesia','Japan','Korea','Malaysia',
        'Mexico','New Zealand','Papua New Guinea','Peru',
        'Philippines','Russia','Singapore',
        'Chinese Taipei','Thailand',
        'United States','Vietnam']

# =====================================================
# LOAD IMF DATA 
# =====================================================
base_path = "./data_source/"
data_output_loc = "./results/data/"

IMF_df = pd.read_excel(
    base_path + 'WEOOct2025all.xlsx',
    sheet_name="Countries",
    dtype=object,
    engine='openpyxl'
)

# =====================================================
# 🛡️ BULLETPROOF COLUMN DISCOVERY 
# =====================================================
# Clean headers to remove hidden spaces/newlines
IMF_df.columns = [' '.join(str(c).upper().replace('\n', ' ').replace('_', ' ').split()) for c in IMF_df.columns]

rename_map = {
    'COUNTRY': 'Country',
    'COUNTRY NAME': 'Country',
    'ECONOMY': 'Country',
    'INDICATOR ID': 'WEO Subject Code',
    'WEO SUBJECT CODE': 'WEO Subject Code',
    'SUBJECT CODE': 'WEO Subject Code'
}
IMF_df.rename(columns=rename_map, inplace=True)

# Safety Net if column headers are still weird
if 'WEO Subject Code' not in IMF_df.columns:
    for col in IMF_df.columns:
        if IMF_df[col].astype(str).isin(['NGDPRPPPPC', 'LP', 'NID_NGDP', 'NGSD_NGDP']).any():
            IMF_df.rename(columns={col: 'WEO Subject Code'}, inplace=True)
            break

if 'Country' not in IMF_df.columns:
    for col in IMF_df.columns:
        if IMF_df[col].astype(str).isin(['Australia', 'Japan', 'Canada']).any():
            IMF_df.rename(columns={col: 'Country'}, inplace=True)
            break

# =====================================================
# FIX COUNTRY NAMES 
# =====================================================

replace = {
    'Hong Kong SAR': 'Hong Kong, China',
    'Taiwan Province of China': 'Chinese Taipei',
    'United States of America': 'United States',
    'Viet Nam': 'Vietnam',
    'China, P.R.: Mainland': 'China'
}

IMF_df.replace(replace, inplace=True)
IMF_df = IMF_df[IMF_df['Country'].isin(APEC)].copy()

# =====================================================
# ISOLATE TARGET VARIABLES & FORCE HISTORICAL NAMES
# =====================================================
# Filter for the exact codes
variables = ['NGDPRPPPPC','LP','NID_NGDP','NGSD_NGDP']
IMF_df = IMF_df[IMF_df['WEO Subject Code'].isin(variables)].copy()

weo_mapping = {
    'NGDPRPPPPC': 'Gross domestic product per capita, constant prices',
    'LP': 'Population',
    'NID_NGDP': 'Total investment',
    'NGSD_NGDP': 'Gross national savings'
}
IMF_df['Subject Descriptor'] = IMF_df['WEO Subject Code'].map(weo_mapping)

# =====================================================
# DETECT YEAR COLUMNS & CONVERT TO NUMERIC
# =====================================================

years = [col for col in IMF_df.columns if str(col).isdigit()]
years = sorted([str(y) for y in years])

IMF_df[years] = IMF_df[years].apply(pd.to_numeric, errors='coerce')

# =====================================================
# BUILD PPP GDP 
# =====================================================

PPP_list = []

for economy in APEC:
    temp_df = IMF_df[
        (IMF_df['Country'] == economy) &
        (IMF_df['WEO Subject Code'].isin(['NGDPRPPPPC','LP']))
    ]

    gdp_pc = temp_df[temp_df['WEO Subject Code'] == 'NGDPRPPPPC']
    pop    = temp_df[temp_df['WEO Subject Code'] == 'LP']

    if len(gdp_pc) == 0 or len(pop) == 0:
        continue

    ppp_df = gdp_pc[years].iloc[0] * pop[years].iloc[0]
    ppp_df['Country'] = economy
    ppp_df['Subject Descriptor'] = 'Real GDP PPP 2021 USD'

    PPP_list.append(pd.DataFrame([ppp_df]))

PPP_GDP = pd.concat(PPP_list, ignore_index=True)

# =====================================================
# MELT DATA 
# =====================================================

PPP_GDP_long = PPP_GDP.melt(
    id_vars=['Country','Subject Descriptor'],
    value_vars=years,
    var_name='year',
    value_name='value'
)

IMF_data_long = IMF_df.melt(
    id_vars=['Country','Subject Descriptor'],
    value_vars=years,
    var_name='year',
    value_name='value'
)

IMF_data_long = pd.concat([PPP_GDP_long, IMF_data_long], ignore_index=True)
IMF_data_long['year'] = IMF_data_long['year'].astype(int)

# =====================================================
# ADD GROWTH & RENAME COLUMNS
# =====================================================

IMF_data_long['percent'] = IMF_data_long.groupby(
    ['Country','Subject Descriptor']
)['value'].pct_change()

IMF_data_long = IMF_data_long.rename(columns={
    'Country': 'economy',
    'Subject Descriptor': 'variable'
})

# =====================================================
# ECONOMY CODE 
# =====================================================

APEC_econcode = pd.read_csv(
    base_path + 'APEC_economy_code.csv',
    header=None, index_col=0
).squeeze().to_dict()

# Force dictionary to recognize the renamed countries
APEC_econcode['United States'] = '20_USA'
APEC_econcode['Vietnam'] = '21_VN'
APEC_econcode['Chinese Taipei'] = '18_CT'
APEC_econcode['Hong Kong, China'] = '06_HKC'

IMF_data_long['economy_code'] = IMF_data_long['economy'].map(APEC_econcode)

IMF_data_long = IMF_data_long[
    ['economy_code','economy','variable','year','value','percent']
].sort_values(['economy_code','variable','year']).reset_index(drop=True)

IMF_data_long['source'] = 'IMF'

# =====================================================
# SAVE MAIN DATASET 
# =====================================================
os.makedirs(data_output_loc, exist_ok=True)
IMF_data_long.to_csv(data_output_loc + 'IMF_to2030.csv', index=False)

# =====================================================
# CREATE SAVINGS FILE (WITH BD & PNG OVERRIDES)
# =====================================================
target_year = 2030 

# 1. Grab base savings for jump-off year
IMF_savings = IMF_data_long[
    (IMF_data_long['variable'] == 'Gross national savings') &
    (IMF_data_long['year'] == target_year)
].copy()

# 2. Grab Brunei's 'Total investment' as proxy
brunei_inv = IMF_data_long[
    (IMF_data_long['variable'] == 'Total investment') &
    (IMF_data_long['year'] == target_year) &
    (IMF_data_long['economy_code'] == '02_BD')
].copy()

# 3. Swap in Brunei and sort
IMF_savings = IMF_savings[IMF_savings['economy_code'] != '02_BD']
IMF_savings = pd.concat([IMF_savings, brunei_inv]).sort_values('economy_code').reset_index(drop=True)

# 4. Hardcode PNG 
IMF_savings.loc[IMF_savings['economy_code'] == '13_PNG', 'value'] = 25
IMF_savings.loc[IMF_savings['economy_code'] == '13_PNG', 'source'] = 'Guess'

IMF_savings = IMF_savings[['economy_code', 'economy', 'year', 'value', 'source']].reset_index(drop=True)
IMF_savings.to_csv(data_output_loc + 'IMF_savings_2030.csv', index=False)
print("✅ IMF_savings_2030.csv CREATED WITH CUSTOM OVERRIDES")

# =====================================================
# CHARTS 
# =====================================================
IMF_chart_folder = './results/IMF/'
os.makedirs(IMF_chart_folder, exist_ok=True)

# Loop using both the name and the code for clean saving
for econ_name, econ_code in APEC_econcode.items():
    if econ_name not in APEC:
        continue

    chart_df = IMF_data_long[IMF_data_long['economy_code'] == econ_code]

    if chart_df.empty:
        continue

    fig, axs = plt.subplots(2, 2, figsize=(10,7))

    sns.lineplot(ax=axs[0,0], data=chart_df[chart_df['variable'] == 'Real GDP PPP 2021 USD'], x='year', y='value')
    axs[0,0].set_title(f"{econ_name} real GDP")

    sns.lineplot(ax=axs[0,1], data=chart_df[chart_df['variable'] == 'Gross domestic product per capita, constant prices'], x='year', y='value')
    axs[0,1].set_title(f"{econ_name} GDP per capita")

    sns.lineplot(ax=axs[1,0], data=chart_df[chart_df['variable'] == 'Gross national savings'], x='year', y='value')
    axs[1,0].set_title(f"{econ_name} savings")

    sns.lineplot(ax=axs[1,1], data=chart_df[chart_df['variable'] == 'Total investment'], x='year', y='value')
    axs[1,1].set_title(f"{econ_name} investment")

    plt.tight_layout()
    fig.savefig(IMF_chart_folder + f"{econ_code}_IMF_data.png")
    plt.close()

print("✅ A2 IMF Pipeline Completed")


