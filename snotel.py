import numpy as np
import pandas as pd
import ulmo
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# CUAHSI API endpoint
url = 'https://hydroportal.cuahsi.org/Snotel/cuahsi_1_1.asmx?WSDL'

# Site ID, variable ID, start/end_date
#     example site ID 842 Vail Mountain, 10,300 ft
#     example site ID 590 Lone Mountain (Big Sky) 8,800 ft
sitecode = '590_MT_SNTL'
variablecode = 'SNOTEL:WTEQ_D'
start_date = '1949-10-01'
end_date = dt.date.today().strftime('%Y-%m-%d')

# Pull data and move values to dataframe
site_values = ulmo.cuahsi.wof.get_values(url, sitecode, variablecode, start=start_date, end=end_date)
site_values_df = pd.DataFrame(site_values['values'])

# Get datetime, value, quality_control_level_code
site_values_df = site_values_df[['datetime', 'value', 'quality_control_level_code']]

# Review datatypes
site_values_df['datetime'] = pd.to_datetime(site_values_df['datetime'], format='%Y-%m-%d')
site_values_df['value'] = site_values_df['value'].astype(float)
site_values_df['quality_control_level_code'] = site_values_df['quality_control_level_code'].astype(str)

# Add additional date information for statistics
site_values_df.insert(0, 'day', site_values_df['datetime'].dt.strftime('%d'))
site_values_df.insert(0, 'month', site_values_df['datetime'].dt.strftime('%m'))
site_values_df.insert(0, 'month-day', site_values_df['datetime'].dt.strftime('%m-%d'))
site_values_df.insert(0, 'year', site_values_df['datetime'].dt.strftime('%Y'))
site_values_df['year'] = site_values_df['year'].astype(int)
site_values_df.insert(0, 'wateryear', 0)
site_values_df.loc[site_values_df['month'] == '10', 'wateryear'] = 1
site_values_df.loc[site_values_df['month'] == '11', 'wateryear'] = 1
site_values_df.loc[site_values_df['month'] == '12', 'wateryear'] = 1
site_values_df['wateryear'] = site_values_df['wateryear'] + site_values_df['year']

# Add day of year for statistics
site_values_df.insert(4, 'dayofyear', '1970-' + site_values_df['month'] + '-' + site_values_df['day'])
# Drop leap years ... OK for this application
site_values_df = site_values_df[site_values_df['dayofyear'].str.contains("1970-02-29") == False]
site_values_df['dayofyear'] = pd.to_datetime(site_values_df['dayofyear'], format='%Y-%m-%d').dt.strftime('%j')

# Set poor quality data and missing values to missing
site_values_df.loc[site_values_df['quality_control_level_code'] != '1', 'value'] = np.NaN
site_values_df.loc[site_values_df['value'] == -9999, 'value'] = np.NaN
site_values_df.loc[site_values_df['value'] == '', 'value'] = np.NaN

# Pull out current year
today = dt.date.today()
this_year = today.strftime('%Y')
this_month = today.strftime('%m')

if this_month not in ("10", "11", "12"):
    this_year = int(this_year) - 1

current_year_index = site_values_df.index[site_values_df['datetime'] == dt.datetime(int(this_year), 10, 1)]
current_year_data = site_values_df.iloc[current_year_index[0]:, ]

# Get Statistics
stat_list = ['count', 'min', 'max', 'mean', 'std', 'median']
count_df = site_values_df.groupby('dayofyear').agg(stat_list)['value']
count_df.insert(3, 'percentile_75', site_values_df.groupby('dayofyear').quantile(0.75)['value'])
count_df.insert(3, 'percentile_25', site_values_df.groupby('dayofyear').quantile(0.25)['value'])

# Format for Plotting
count_df = count_df.iloc[273:, ].append(count_df.iloc[:273, ])
date_list = [(dt.datetime(1969, 10, 1) + dt.timedelta(days=x)) for x in range(365)]
count_df.insert(0, 'month-day', date_list)
count_df.insert(2, 'thisyear-data', current_year_data['value'].tolist() + ([np.NaN] * (365-len(current_year_data))))

# Plot
fig, ax = plt.subplots()
line1, = ax.plot(count_df['month-day'], count_df['thisyear-data'], color='black', label="current")
line2, = ax.plot(count_df['month-day'], count_df['median'], color='grey', linestyle='dashed', label="median")
line3, = ax.plot(count_df['month-day'], count_df['percentile_25'], color='grey', label="25/75th percentiles")
ax.plot(count_df['month-day'], count_df['percentile_75'], color='grey')
line5, = ax.plot(count_df['month-day'], count_df['max'], color='green', alpha=0.5, label="POR max")
line6, = ax.plot(count_df['month-day'], count_df['min'], color='red', alpha=0.5, label="POR min")
ax.fill_between(count_df['month-day'], count_df['percentile_25'], count_df['percentile_75'], color='grey', alpha=0.5)
ax.set(xlabel='Day of Year', ylabel='SWE (inches)', title=sitecode)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax.spines['bottom'].set_position('zero')
ax.grid()
ax.legend(handles=[line1, line2, line3, line5, line6])

# View and save
plt.show()
fig.savefig(sitecode + ".png")
