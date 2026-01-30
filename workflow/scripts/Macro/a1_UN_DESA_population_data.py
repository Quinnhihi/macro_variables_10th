#%%
# UN DESA

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

# Change the working drive
wanted_wd = 'macro_variables_9th'
os.chdir(re.split(wanted_wd, os.getcwd())[0] + wanted_wd)

# Define categories for data grab

APEC = ['Australia',
        'Brunei Darussalam',
        'Canada',
        'Chile',
        'China',
        'China, Hong Kong SAR',
        'Indonesia',
        'Japan',
        'Republic of Korea',
        'Malaysia',
        'Mexico',
        'New Zealand',
        'Papua New Guinea',
        'Peru',
        'Philippines',
        'Russian Federation',
        'Singapore',
        'China, Taiwan Province of China',
        'Thailand',
        'United States of America',
        'Viet Nam']

# All variants except 'Medium'
variant = ['High',
           'Medium',
           'Low',
           'Constant fertility',
           'Instant replacement',
           'Zero migration',
           'Constant mortality',
           'No change',
           'Momentum',
           'Instant replacement zero migration',
           'Median PI',
           'Upper 80 PI'
           'Lower 80 PI',
           'Upper 95 PI',
           'Lower 95 PI']

# Grab histroical data and medium scenario
undesa_hist = pd.read_csv("./data/UN_DESA/WPP2022_Demographic_Indicators_Medium.csv")
undesa_hist = undesa_hist[undesa_hist['Location'].isin(APEC)].copy().reset_index(drop = True)

# Only keep variables of interest
undesa_hist = undesa_hist[['Location', 'Variant', 'Time', 'TPopulation1Jan', 'TPopulation1July', 'NetMigrations']].copy()

# Projections to 2100 from UN DESA csv
undesa_proj = pd.read_csv("./data/UN_DESA/WPP2022_Demographic_Indicators_OtherVariants.csv")

# Subset so only APEC economies
undesa_proj = undesa_proj[undesa_proj['Location'].isin(APEC)].copy().reset_index(drop = True)
undesa_proj['Location'].unique()

# Only keep variables of interest
undesa_proj = undesa_proj[['Location', 'Variant', 'Time', 'TPopulation1Jan', 'TPopulation1July', 'NetMigrations']].copy()

# Concatenate medium scenario (including historical) with all other scenarios
undesa_apec = pd.concat([undesa_hist, undesa_proj]).copy().reset_index(drop = True)

dict_to_replace = {'China, Hong Kong SAR': 'Hong Kong, China', 
                   'Republic of Korea': 'Korea',
                   'Russian Federation': 'Russia',
                   'China, Taiwan Province of China': 'Chinese Taipei'}

undesa_apec.replace(dict_to_replace, inplace = True)

# Update APEC list
APEC = [dict_to_replace.get(e, e) for e in APEC]
APEC

# Colour palette for charts (15 categories) 
palette = sns.color_palette('rocket', 15)

# Save location for charts
population_charts = './results/population/'

if not os.path.isdir(population_charts):
    os.makedirs(population_charts)

for economy in APEC:
    chart_df = undesa_apec[undesa_apec['Location'] == economy].copy().reset_index(drop = True)
    chart_df['TPopulation1Jan'] = chart_df['TPopulation1Jan'] / 1000

    sizes = {a: 1 for a in chart_df['Variant'].unique()}
    med = {'Medium': 4}
    sizes.update(med)

    fig, ax = plt.subplots()

    sns.set_theme(style = 'ticks')
    sns.lineplot(ax = ax,
                 data = chart_df,
                 x = 'Time',
                      y = 'TPopulation1Jan',
                      hue = 'Variant',
                      palette = palette,
                      size = 'Variant',
                      sizes = sizes)
      
    ax.set(title = economy + ' population projections to 2100 (UN DESA)', 
           xlabel = 'Year', 
           ylabel = 'Population (millions)', 
           ylim = (0, max(chart_df['TPopulation1Jan']) * 1.1),
           xlim = (min(chart_df['Time']), 2100))

    plt.legend(title = '', fontsize = 7)

    plt.tight_layout()
    fig.savefig(population_charts + economy + '_population.png')
    plt.close()

# Save required dataframe

pop_choice = pd.read_csv('./data/APEC_population.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

APEC_econcode = pd.read_csv('./data/APEC_economy_code.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

historical_df = undesa_apec[undesa_apec['Time'] < 2022]
historical_df

projected_df = pd.DataFrame(columns = ['Economy', 'Location', 'Variant', 'Time', 'TPopulation1Jan', 'TPopulation1July', 'NetMigrations'])
projected_df

for economy in APEC:
    temp_df = undesa_apec[(undesa_apec['Location'] == economy) & 
                          (undesa_apec['Time'] > 2021) & 
                          (undesa_apec['Variant'] == pop_choice[economy])]\
                            .copy().reset_index(drop = True)
    
    temp_df['Economy'] = APEC_econcode[economy]
    
    projected_df = pd.concat([projected_df, temp_df]).reset_index(drop = True)

APEC_population = pd.concat([projected_df, historical_df]).copy().reset_index(drop = True)

APEC_population['Economy'] = APEC_population['Location'].map(APEC_econcode)

#################################################################################################
# Australia edit: load intergenerational report
aus_igr_df = pd.read_excel('./data/AUS_IGR/IGR_02_Population.xlsx', sheet_name = '2.2')
aus_igr_df['year'] = aus_igr_df['Year'].str[:4]

aus_igr_df['IGR2023'] = np.nan

for i in aus_igr_df.index[1:]:
    aus_igr_df.loc[i, 'IGR2023'] = (aus_igr_df.loc[i, 'IGR 2023'] + aus_igr_df.loc[i - 1, 'IGR 2023']) / 2 * 1000

# Australia subset
AUS_pop_df = APEC_population[APEC_population['Location'] == 'Australia'].copy()
everything_else_df = APEC_population[~(APEC_population['Location'] == 'Australia')].copy()

AUS_pop_df['TPopulation1Jan_adjust'] = AUS_pop_df['TPopulation1Jan']

additional_growth = 0.0015

for year in range(2023, 2102, 1):
    AUS_pop_df.loc[AUS_pop_df['Time'] == year, 'TPopulation1Jan_adjust'] = \
        AUS_pop_df.loc[AUS_pop_df['Time'] == year, 'TPopulation1Jan'] * (1 + additional_growth) ** (year - 2023)

AUS_pop_df['TPopulation1Jan'] = AUS_pop_df['TPopulation1Jan_adjust'] 
AUS_pop_df = AUS_pop_df.drop(columns = ['TPopulation1Jan_adjust']).copy()

AUS_pop_df['Variant'] = 'IGR_2023'

APEC_population = pd.concat([AUS_pop_df, everything_else_df]).copy().reset_index(drop = True)
###################################################################################################

APEC_population = APEC_population.sort_values(['Economy', 'Time']).copy().reset_index(drop = True)
APEC_population.to_csv(population_charts + 'APEC_population_to_2100.csv', index = False)

# Save population data

APEC_population = APEC_population.rename(columns = {'Economy': 'economy_code',
                                                    'Location': 'economy',
                                                    'Variant': 'variant',
                                                    'Time': 'year',
                                                    'TPopulation1Jan': 'population_1jan',
                                                    'TPopulation1July': 'population_1jul',
                                                    'NetMigrations': 'net_migration'})

APEC_population = APEC_population.melt(id_vars = ['economy', 'economy_code', 'year', 'variant'],
                                       value_vars = ['population_1jan', 'population_1jul', 'net_migration'])\
                                        .reset_index(drop = True)

APEC_population = APEC_population[['economy_code', 'economy', 'year', 'variant', 'variable', 'value']]

# Now add percent change column
APEC_population['percent'] = APEC_population.groupby(['economy', 'variable'], 
                                                 group_keys = False)\
                                                    ['value'].apply(pd.Series.pct_change)

APEC_population['source'] = 'UN DESA'

APEC_population.to_csv('./data/UN_DESA/undesa_pop_to2100.csv', index = False)

# Save location for charts
sensitivity_loc = './results/population/sensitivity/'

if not os.path.isdir(sensitivity_loc):
    os.makedirs(sensitivity_loc)

# Sensitivity
pop_low = pd.read_csv(population_charts + 'sensitivity/APEC_pop_low.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

pop_med = pd.read_csv(population_charts + 'sensitivity/APEC_pop_med.csv', header = None, index_col = 0)\
    .squeeze().to_dict()

pop_high = pd.read_csv(population_charts + 'sensitivity/APEC_pop_high.csv', header = None, index_col = 0)\
    .squeeze().to_dict()


for sens in [pop_low, pop_med, pop_high]:
    projected_df = pd.DataFrame(columns = ['Economy', 'Location', 'Variant', 'Time', 'TPopulation1Jan', 'TPopulation1July', 'NetMigrations'])
    
    for economy in APEC:
        temp_df = undesa_apec[(undesa_apec['Location'] == economy) & 
                            (undesa_apec['Time'] > 2021) & 
                            (undesa_apec['Variant'] == sens[economy])]\
                                .copy().reset_index(drop = True)
        
        temp_df['Economy'] = APEC_econcode[economy]
        
        projected_df = pd.concat([projected_df, temp_df]).reset_index(drop = True)

    APEC_population = pd.concat([projected_df, historical_df]).copy().reset_index(drop = True)

    APEC_population['Economy'] = APEC_population['Location'].map(APEC_econcode)

    APEC_population = APEC_population.sort_values(['Economy', 'Time']).copy().reset_index(drop = True)
    APEC_population.to_csv(population_charts + 'sensitivity/APEC_population_to_2100_' + list(sens.values())[0] + '.csv', index = False)

    # Save population data

    APEC_population = APEC_population.rename(columns = {'Economy': 'economy_code',
                                                        'Location': 'economy',
                                                        'Variant': 'variant',
                                                        'Time': 'year',
                                                        'TPopulation1Jan': 'population_1jan',
                                                        'TPopulation1July': 'population_1jul',
                                                        'NetMigrations': 'net_migration'})

    APEC_population = APEC_population.melt(id_vars = ['economy', 'economy_code', 'year', 'variant'],
                                        value_vars = ['population_1jan', 'population_1jul', 'net_migration'])\
                                            .reset_index(drop = True)

    APEC_population = APEC_population[['economy_code', 'economy', 'year', 'variant', 'variable', 'value']]

    # Now add percent change column
    APEC_population['percent'] = APEC_population.groupby(['economy', 'variable'], 
                                                    group_keys = False)\
                                                        ['value'].apply(pd.Series.pct_change)

    APEC_population['source'] = 'UN DESA'

    APEC_population.to_csv('./data/UN_DESA/undesa_pop_to2100_' + list(sens.values())[0] + '.csv', index = False)
#%%