#%%

#%%
import pandas as pd
import numpy as np
import os
import re
import plotly.express as px

####
root_dir =re.split('macro_variables_9th', os.getcwd())[0]+'/macro_variables_9th'
#set the root directory for the project
os.chdir(root_dir)
####

#%%
#take in population from data\hkc_population_input.csv
pop = pd.read_csv('data/hkc_population_input.csv')#Year	Population (thousands) > this data is based on https://www.censtatd.gov.hk/en/web_table.html?id=150-11001#

#make a df with years from 2021 to 2100
years = pd.DataFrame({'Year':np.arange(2021,2101)})
#merge the two dfs on year
pop = years.merge(pop, how='left', on='Year')
#drop all spaces in the Population (thousands) column so we can convert to a float
pop['Population (thousands)'] = pop['Population (thousands)'].str.replace(' ','')
#make pop into a float
pop['Population (thousands)'] = pop['Population (thousands)'].astype(float)
#find the latest year with a population value
latest_year = pop.dropna().tail(1)['Year'].values[0]
#%%
#interploate the population for the years 2021 to 2100. where we are missing on the ends, leave as NaN.
pop['Population (interpolated)'] = pop['Population (thousands)'].interpolate()
#separate the population for years before the first year.
# pop.loc[pop['Year']>latest_year,'Population (interpolated)'] = np.nan
pop_original = pop.copy()
pop_original = pop_original[pop_original['Year']<=latest_year]

#%%
#calculate the growth rate for each year
pop_original['Growth Rate'] = pop_original['Population (interpolated)'].pct_change()
#%%
#we want to find a measure for the growth rate that is more stable than the raw growth rate. we will do it two ways, one using an exponential weighted moving average and one using the average of the last 5 years. then we'll grab the value for these from the last yea  with a population value and use that to project the population for the years after the last year with a population value.

#calcaulte the average growth rate, weighting the latest years by the most
pop_original['Growth Rate (projected - ewm)'] = pop_original['Growth Rate'].ewm(span=5).mean()
#calc the average growth rate from the last 5 years
pop_original['Growth Rate (projected)'] = pop_original['Growth Rate'].tail(5).mean()

#alsoi do it by first prjecting the growht rate and then the population based on that:
#calcautle the  % cahgne in growth rate in each eyar
pop_original['Growth Rate 2nd order'] = pop_original['Growth Rate'].pct_change()
#calculate the average growth rate change, weighting the latest years by the most
pop_original['Growth Rate 2nd order (projected - ewm)'] = pop_original['Growth Rate 2nd order'].ewm(span=5).mean()
#calc the average growth rate change from the last 5 years
pop_original['Growth Rate 2nd order (projected)'] = pop_original['Growth Rate 2nd order'].tail(5).mean()

#also do it using the ewma and 5 year mean of the absolute change in growth rate in the final years > use that to change the growth rate each year in the future (e.g. if it ddecrease by 0.1% in the final year, then decrease the growth rate by 0.1% each year in the future). this will allow us to captura a negative growth rate
pop_original['Growth Rate change'] = pop_original['Growth Rate'].diff()
pop_original['Growth Rate change (projected - ewm)'] = pop_original['Growth Rate change'].ewm(span=5).mean()
pop_original['Growth Rate change (projected)'] = pop_original['Growth Rate change'].tail(5).mean()

growth_ewm = pop_original['Growth Rate (projected - ewm)'].iloc[-1]
growth = pop_original['Growth Rate (projected)'].iloc[-1]
growth_2nd_deriv_ewm = pop_original['Growth Rate 2nd order (projected - ewm)'].iloc[-1]
growth_2nd_deriv = pop_original['Growth Rate 2nd order (projected)'].iloc[-1]
growth_change_ewm = pop_original['Growth Rate change (projected - ewm)'].iloc[-1]
growth_change = pop_original['Growth Rate change (projected)'].iloc[-1]

#%%
#now we can project the population for the years after the last year with a population value
pop_projection = pop_original.copy()
#initialize the projected population columns
pop_projection['Population (projected - ewm)'] = pop_projection['Population (interpolated)']
pop_projection['Population (projected)'] = pop_projection['Population (interpolated)']

pop_projection['Growth Rate (projected - 2nd order)'] = pop_projection['Growth Rate']
pop_projection['Growth Rate (projected - 2nd order ewm)'] = pop_projection['Growth Rate (projected - ewm)']
pop_projection['Population (projected - 2nd order)'] = pop_projection['Population (interpolated)']
pop_projection['Population (projected - 2nd order ewm)'] = pop_projection['Population (interpolated)']

pop_projection['Growth Rate (projected 2)'] = pop_projection['Growth Rate']
pop_projection['Growth Rate (projected 2 - ewm)'] = pop_projection['Growth Rate']
pop_projection['Population (projected 2)'] = pop_projection['Population (interpolated)']
pop_projection['Population (projected 2 - ewm)'] = pop_projection['Population (interpolated)']

for year in range(latest_year+1,2101):
    new_row = pd.DataFrame({'Year':year, 
                            'Population (projected)':pop_projection['Population (projected - ewm)'].iloc[-1]*(1+growth), 'Population (projected - ewm)':pop_projection['Population (projected)'].iloc[-1]*(1+growth_ewm), 
                            'Growth Rate (projected)':growth, 'Growth Rate (projected - ewm)':growth_ewm, 
                            'Growth Rate (projected - 2nd order)':pop_projection['Growth Rate (projected - 2nd order)'].iloc[-1]*(1+growth_2nd_deriv), 
                            'Growth Rate (projected - 2nd order ewm)':pop_projection['Growth Rate (projected - 2nd order ewm)'].iloc[-1]*(1+growth_2nd_deriv_ewm),  
                            'Growth Rate (projected 2)':pop_projection['Growth Rate (projected 2)'].iloc[-1]+growth_change, 
                            'Growth Rate (projected 2 - ewm)':pop_projection['Growth Rate (projected 2 - ewm)'].iloc[-1]+growth_change_ewm}, index=[0])

    pop_projection = pd.concat([pop_projection, new_row], axis=0)
    #calcaulte the population using the 2nd order growth rate
    pop_projection['Population (projected - 2nd order)'].iloc[-1] = pop_projection['Population (projected - 2nd order)'].iloc[-2]*(1+pop_projection['Growth Rate (projected - 2nd order)'].iloc[-1])
    pop_projection['Population (projected - 2nd order ewm)'].iloc[-1] = pop_projection['Population (projected - 2nd order ewm)'].iloc[-2]*(1+pop_projection['Growth Rate (projected - 2nd order ewm)'].iloc[-1])
    
    pop_projection['Population (projected 2)'].iloc[-1] = pop_projection['Population (projected 2)'].iloc[-2]*(1+pop_projection['Growth Rate (projected 2)'].iloc[-1])
    pop_projection['Population (projected 2 - ewm)'].iloc[-1] = pop_projection['Population (projected 2 - ewm)'].iloc[-2]*(1+pop_projection['Growth Rate (projected 2 - ewm)'].iloc[-1])
        
    
#%%
#seaprate the population and growth rate dataframes
growth = pop_projection[['Year', 'Growth Rate (projected)', 'Growth Rate (projected - ewm)', 'Growth Rate (projected - 2nd order)', 'Growth Rate (projected - 2nd order ewm)',  'Growth Rate (projected 2)', 'Growth Rate (projected 2 - ewm)']]
pop = pop_projection[['Year', 'Population (projected)', 'Population (projected - ewm)', 'Population (projected - 2nd order)', 'Population (projected - 2nd order ewm)', 'Population (projected 2)', 'Population (projected 2 - ewm)']]
#reanem the columns after theirmeans of projection
growth.columns = ['Year', 'Final 5 years avg growth', 'EWMA average growth', 'Final 5 years avg growth (2nd order)', 'EWMA average growth (2nd order)', 'Final 5 years avg diff', 'EWMA average diff']
pop.columns = ['Year', 'Final 5 years avg growth', 'EWMA average growth', 'Final 5 years avg growth (2nd order)', 'EWMA average growth (2nd order)', 'Final 5 years avg diff', 'EWMA average diff']
#melt
pop_melt = pd.melt(pop, id_vars='Year', var_name='Method', value_name='Population')
growth_melt = pd.melt(growth, id_vars='Year', var_name='Method', value_name='Growth Rate')
#concatenate
pop_growth = pd.concat([pop_melt, growth_melt], axis=0)

#nelt the data
pop_growth = pd.melt(pop_growth, id_vars=['Year', 'Method'], var_name='Measure', value_name='Value')
#label all values after 2021 as projected
pop_growth['line_dash'] = 'historical'
pop_growth.loc[pop_growth['Year']>latest_year,'line_dash'] = 'projected'
#and eyars after 2060 will be 'not_in_outlook'
pop_growth.loc[pop_growth['Year']>2060,'line_dash'] = 'not_in_outlook'
#%%
#plot pop_melt with facet as measure
fig = px.line(pop_growth, x='Year', y='Value', color='Method', facet_col_wrap=2, facet_col='Measure', line_dash='line_dash', title='Hong Kong Population Growth Projection')
#make the axes independent
fig.update_yaxes(matches=None)
#make lines thicker
fig.update_traces(line=dict(width=4))
fig.write_html('plotting_output/hkc_population_growth_projection.html')
#%%
#calcualte the average growht rate and project missing years
#drop nas
pop_growth = pop_growth.dropna()
#save the output to data\hkc_population_output.xlsx
pop_growth.to_csv('results/population/09022024_HKC_pop_projection.csv')
#%%


#################################################################

CHOSEN_METHOD = 'Final 5 years avg growth (2nd order)'
#and also inset it into our macro variables excel file.
#load it in here: C:\Users\finbar.maunsell\github\macro_variables_9th\results\GDP_estimates\data\00_APEC_GDP_data_2024_07_26.csv
macro = pd.read_csv('results/GDP_estimates/data/00_APEC_GDP_data_2024_07_26.csv')
#cols: economy_code	economy	year	variable	value	units
#filter for:
# economy_code	economy		variable
# 06_HKC	Hong Kong, China		GDP_per_capita
# 06_HKC	Hong Kong, China		population

macro_hkc = macro[macro['economy_code']=='06_HKC']
macro_hkc_pop = macro_hkc[macro_hkc['variable']=='population'].copy()

#merge in the new data.note that we chose to use: 
# Method	Measure
# Final 5 years avg growth (2nd order)	Population
pop_new = pop_growth[(pop_growth['Method']==CHOSEN_METHOD) & (pop_growth['Measure']=='Population')][['Year', 'Value']]
pop_new.columns = ['year', 'value']

#%%
DO_THIS = True
if DO_THIS:
    #since population is kept at the same rate from 2047 onwards (its reasonable BUT we want to have a little bit of movement) we will add a little bit of movement to the population from 2046 onwards. we will do this by adding a random number between -0.1% and 0.1% to the population each year from 2046 onwards.
    pop_new['value'] = pop_new['value'].astype(float)
    pop_new.loc[pop_new['year']>2046, 'value'] = pop_new.loc[pop_new['year']>2046, 'value']*(1+np.random.uniform(-0.001, 0.001, pop_new.loc[pop_new['year']>2046].shape[0]))

macro_hkc_pop = macro_hkc_pop.merge(pop_new, how='left', left_on='year', right_on='year', suffixes=('', '_new'))
#quickly plotto check the vlaus are simialr
macro_hkc_pop_melt = pd.melt(macro_hkc_pop, id_vars='year', value_vars=['value', 'value_new'], var_name='Method', value_name='Population')
#%%
fig = px.line(macro_hkc_pop_melt, x='year', y='Population', color='Method', title='Hong Kong Population Growth Projection')
fig.write_html('plotting_output/hkc_population_growth_projection_vs_macro.html')

#%%
#replace the value with the new value
macro_hkc_pop['value'] = macro_hkc_pop['value_new'].fillna(macro_hkc_pop['value'])
#%%
# Cool now lets recalculate the gdp per capita:
# GDP per capita = GDP / population
macro_hkc_gdp_per_cap = macro_hkc[macro_hkc['variable'].isin(['real_GDP', 'population', 'GDP_per_capita'])][['year', 'economy', 'variable', 'value']].copy()
macro_hkc_gdp_per_cap = macro_hkc_gdp_per_cap.pivot(index=['year', 'economy'], columns='variable', values='value').reset_index()
#test calcualting it
macro_hkc_gdp_per_cap['GDP_per_capita_new'] = (macro_hkc_gdp_per_cap['real_GDP']*1000) / macro_hkc_gdp_per_cap['population']
#calc diff
macro_hkc_gdp_per_cap['diff'] = macro_hkc_gdp_per_cap['GDP_per_capita_new'] - macro_hkc_gdp_per_cap['GDP_per_capita']
#ok so its got to have gdp times 1000.
#%%
macro_hkc_gdp = macro_hkc[macro_hkc['variable'].isin(['real_GDP'])][['year', 'value']].copy()
#rename the value column
macro_hkc_gdp.columns = ['year', 'real_GDP']
#join in the new population
macro_hkc_gdp = macro_hkc_gdp.merge(macro_hkc_pop[['year', 'value']], how='left', left_on='year', right_on='year')
#rename value to population
macro_hkc_gdp.columns = ['year', 'real_GDP', 'population']

#%%
#calc the new gdp per capita
macro_hkc_gdp['GDP_per_capita'] = (macro_hkc_gdp['real_GDP']*1000) / macro_hkc_gdp['population']
#%%
#plot against the old value
macro_hkc_gdp_per_cap_new = macro_hkc_gdp_per_cap[['year', 'economy', 'GDP_per_capita']].copy()
macro_hkc_gdp_per_cap_new = macro_hkc_gdp_per_cap_new.merge(macro_hkc_gdp[['year', 'GDP_per_capita']], how='left', left_on='year', right_on='year', suffixes=('', '_new'))
macro_hkc_gdp_per_cap_new = macro_hkc_gdp_per_cap_new[['year', 'economy', 'GDP_per_capita', 'GDP_per_capita_new']]#, 'real_GDP', 'population'
#plot 
macro_hkc_gdp_per_cap_melt = pd.melt(macro_hkc_gdp_per_cap_new, id_vars=['year', 'economy'], var_name='Method', value_name='value')

#%%
fig = px.line(macro_hkc_gdp_per_cap_melt, x='year', y='value', color='Method', title='Hong Kong GDP per Capita Projection')
fig.write_html('plotting_output/hkc_gdp_per_capita_projection_vs_macro.html')

#%%
#ok now we can replace the old values with the new values
macro_hkc_gdp_per_cap['GDP_per_capita'] = macro_hkc_gdp_per_cap['GDP_per_capita_new'].fillna(macro_hkc_gdp_per_cap['GDP_per_capita'])
#%%
#now join otgether our new popualtion and gdp per capita
macro_hkc_pop = macro_hkc_pop[['year', 'value']].copy()
macro_hkc_pop.columns = ['year', 'value']
macro_hkc_pop['variable'] = 'population'
macro_hkc_pop['units'] = 'thousands'
macro_hkc_pop['economy'] = 'Hong Kong, China'
macro_hkc_pop['economy_code'] = '06_HKC'

macro_hkc_gdp_per_cap = macro_hkc_gdp_per_cap[['year', 'GDP_per_capita']].copy()
macro_hkc_gdp_per_cap.columns = ['year', 'value']
macro_hkc_gdp_per_cap['variable'] = 'GDP_per_capita'
macro_hkc_gdp_per_cap['units'] = 'USD PPP 2017'
macro_hkc_gdp_per_cap['economy'] = 'Hong Kong, China'
macro_hkc_gdp_per_cap['economy_code'] = '06_HKC'

#concatenate
macro_hkc_new = pd.concat([macro_hkc[~macro_hkc['variable'].isin(['population', 'GDP_per_capita'])], macro_hkc_pop, macro_hkc_gdp_per_cap], axis=0)

#drop hkc from original
macro = macro[macro['economy_code']!='06_HKC']
#concatenate
macro = pd.concat([macro, macro_hkc_new], axis=0)
#save with new date
import datetime as dt
new_date = dt.datetime.now().strftime('%Y_%m_%d')
macro.to_csv(f'results/GDP_estimates/data/00_APEC_GDP_data_{new_date}.csv', index=False)



#


# %%
#%%
