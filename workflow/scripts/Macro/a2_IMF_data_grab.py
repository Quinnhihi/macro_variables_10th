#%%
# IMF data

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

# APEC in IMF data

APEC = ['Australia',
        'Brunei Darussalam',
        'Canada',
        'Chile',
        'China',
        'Hong Kong SAR',
        'Indonesia',
        'Japan',
        'Korea',
        'Malaysia',
        'Mexico',
        'New Zealand',
        'Papua New Guinea',
        'Peru',
        'Philippines',
        'Russia',
        'Singapore',
        'Taiwan Province of China',
        'Thailand',
        'United States',
        'Vietnam']

IMF_df = pd.read_excel('./data/IMF/WEOOct2022all.xlsx')
IMF_df = IMF_df[IMF_df['Country'].isin(APEC)].copy().reset_index(drop = True)

# Variables required are ('Subject Descriptor'):
# Constant real GDP per capita PPP 2017 USD: NGDPRPPPPC
# Population: LP
# Total investment: NID_NGDP
# Gross national savings: NGSD_NGDP

variables = ['NGDPRPPPPC', 'LP', 'NID_NGDP', 'NGSD_NGDP']

IMF_df = IMF_df[IMF_df['WEO Subject Code'].isin(variables)].copy().reset_index(drop = True)

# Now replace economy names
dict_to_replace = {'Hong Kong SAR': 'Hong Kong, China', 
                   'Taiwan Province of China': 'Chinese Taipei',
                   'United States': 'United States of America',
                   'Vietnam': 'Viet Nam'}

IMF_df.replace(dict_to_replace, inplace = True)
IMF_df

# Update APEC list
APEC = [dict_to_replace.get(e, e) for e in APEC]
APEC

# Now calculate PPP 2017 USD for all economies (multiply real PPP GDP per capita by population)

PPP_GDP = pd.DataFrame(columns = IMF_df.columns)

for economy in APEC:
    temp_df = IMF_df[(IMF_df['Country'] == economy) &
                     (IMF_df['WEO Subject Code'].isin(variables[:2]))]\
                        .copy().reset_index(drop = True)
    
    ppp_df = temp_df[range(1980, 2028, 1)].iloc[0] * temp_df[range(1980, 2028, 1)].iloc[1]
    ppp_df['Country'] = economy
    ppp_df['Subject Descriptor'] = 'Real GDP PPP 2017 USD'

    PPP_GDP = pd.concat([PPP_GDP, pd.DataFrame(ppp_df).transpose()], axis = 0).reset_index(drop = True)
    
PPP_GDP_long = PPP_GDP.melt(id_vars = ['Country', 'Subject Descriptor'], 
                            value_vars = list(range(1980, 2028, 1)), 
                            var_name = 'Year')

# Now reshape population, investment and gross national savings

IMF_data_long = IMF_df.melt(id_vars = ['Country', 'Subject Descriptor'],
                            value_vars = list(range(1980, 2028, 1)),
                            var_name = 'Year')

# Concat the real GDP with original IMF data to create new long data frame
IMF_data_long = pd.concat([IMF_data_long, PPP_GDP_long]).reset_index(drop = True)

# Now add percent change column
IMF_data_long['percent'] = IMF_data_long.groupby(['Country', 'Subject Descriptor'], 
                                                 group_keys = False)\
                                                    ['value'].apply(pd.Series.pct_change)

IMF_data_long = IMF_data_long.rename(columns = {'Country': 'economy',
                                                'Subject Descriptor': 'variable',
                                                'Year': 'year'})

# Add in economy code

APEC_econcode = pd.read_csv('./data/APEC_economy_code.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

IMF_data_long['economy_code'] = IMF_data_long['economy'].map(APEC_econcode)

IMF_data_long = IMF_data_long[['economy_code', 'economy', 'variable', 'year', 'value', 'percent']]

IMF_data_long = IMF_data_long.sort_values(['economy_code', 'variable', 'year']).copy().reset_index(drop = True)

IMF_data_long['source'] = 'IMF'

IMF_data_long['variable'].unique()

# Create some IMF charts
# Save location for charts
IMF_charts = './results/IMF_data/'

if not os.path.isdir(IMF_charts):
    os.makedirs(IMF_charts)

for economy in APEC_econcode.values():
    chart_df = IMF_data_long[IMF_data_long['economy_code'] == economy].copy().reset_index(drop = True)

    fig, axs = plt.subplots(2, 2)

    sns.set_theme(style = 'ticks')

    # Output
    if chart_df[chart_df['variable'] == 'Real GDP PPP 2017 USD']['value'].isna().sum()\
        == len(chart_df[chart_df['variable'] == 'Real GDP PPP 2017 USD']['value']):
        pass

    else:
        sns.lineplot(ax = axs[0, 0],
                    data = chart_df[chart_df['variable'] == 'Real GDP PPP 2017 USD'],
                    x = 'year',
                    y = 'value')
        
        axs[0, 0].set(title = economy + ' real GDP ', 
                    xlabel = 'Year', 
                    ylabel = 'Real GDP PPP 2017 USD')
    
    # GDP per capita
    if chart_df[chart_df['variable'] == 'Gross domestic product per capita, constant prices']['value'].isna().sum()\
        == len(chart_df[chart_df['variable'] == 'Gross domestic product per capita, constant prices']['value']):
        pass
    
    else:
        sns.lineplot(ax = axs[0, 1],
                    data = chart_df[chart_df['variable'] == 'Gross domestic product per capita, constant prices'],
                    x = 'year',
                    y = 'value')
        
        axs[0, 1].set(title = economy + ' real GDP per capita', 
                    xlabel = 'Year', 
                    ylabel = 'Real GDP per capita')
    
    # Savings
    if chart_df[chart_df['variable'] == 'Gross national savings']['value'].isna().sum()\
        == len(chart_df[chart_df['variable'] == 'Gross national savings']['value']):
        pass

    else:
        sns.lineplot(ax = axs[1, 0],
                    data = chart_df[chart_df['variable'] == 'Gross national savings'],
                    x = 'year',
                    y = 'value')
        
        axs[1, 0].set(title = economy + ' gross national savings', 
                    xlabel = 'Year', 
                    ylabel = 'Gross national savings')
    
    # Total investment
    if chart_df[chart_df['variable'] == 'Total investment']['value'].isna().sum()\
        == len(chart_df[chart_df['variable'] == 'Total investment']['value']):
        pass
    
    else:
        sns.lineplot(ax = axs[1, 1],
                    data = chart_df[chart_df['variable'] == 'Total investment'],
                    x = 'year',
                    y = 'value')
        
        axs[1, 1].set(title = economy + ' total investment', 
                    xlabel = 'Year', 
                    ylabel = 'total investment')


    plt.tight_layout()
    fig.savefig(IMF_charts + economy + '_IMF_data.png')
    plt.close()

# Save csv
IMF_data_long.to_csv('./data/IMF/IMF_to2027.csv', index = False)

IMF_savings = IMF_data_long[(IMF_data_long['variable'] == 'Gross national savings') &
                            (IMF_data_long['year'] == 2027)].copy()\
                            [['economy_code', 'variable', 'year', 'value', 'source']]\
                                .reset_index(drop = True)

brunei_inv = IMF_data_long[(IMF_data_long['variable'] == 'Total investment') &
                            (IMF_data_long['year'] == 2027) &
                            (IMF_data_long['economy_code'] == '02_BD')].copy()\
                            [['economy_code', 'variable', 'year', 'value', 'source']]\
                                .reset_index(drop = True)

IMF_savings = pd.concat([IMF_savings[IMF_savings['economy_code'] != '02_BD'], 
                         brunei_inv]).sort_values(['economy_code']).reset_index(drop = True)

# PNG guess for savings
IMF_savings.loc[IMF_savings['economy_code'] == '13_PNG', 'value'] = 25
IMF_savings.loc[IMF_savings['economy_code'] == '13_PNG', 'source'] = 'Guess'

IMF_savings.to_csv('./data/IMF_savings_2027.csv', index = False)


#%%
