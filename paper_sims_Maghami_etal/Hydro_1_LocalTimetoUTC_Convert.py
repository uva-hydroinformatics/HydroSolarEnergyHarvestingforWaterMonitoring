# This code converts the local time zone to UTC for the USGS Sites
import os
import datetime
import numpy as np
import pandas as pd
import datetime


now = datetime.datetime.now()

# # # --------------------------------------------------------------------------------------------------
# # ------------------------------- Hydro data Pre-processing ----------------------------------------
# # --------------------------------------------------------------------------------------------------
def timezone_translator(tz):
    return {
        'EST': 'Etc/GMT+5',
        'EDT': 'Etc/GMT+4',
        'PST': 'Etc/GMT+8',
        'PDT': 'Etc/GMT+7',
        'CST': 'Etc/GMT+6',
        'CDT': 'Etc/GMT+5',
        'MST': 'Etc/GMT+7',
        'MDT': 'Etc/GMT+6'
    }.get(tz, None)


# Search for all flow data files in the folder (txt files)
Data_files = [f for f in os.listdir('./data_files/Hydro_data_files/Raw_data') if
              os.path.isfile(os.path.join('./data_files/Hydro_data_files/Raw_data', f)) and 'txt' in f]

Data_files = os.path

# Print information on data found
print("Files found(" + str(len(Data_files)) + "):")
print(Data_files)

for File_name in Data_files:
        print("Reading file: " + File_name)

        [File_id, extension] = File_name.split('.', 1)

        df = pd.read_csv(os.path.join('./data_files/Hydro_data_files/Raw_data', File_name),
                         delimiter='\t', skiprows=30,
                         names=['agency', 'station', 'str_timestamp', 'tz', 'flow', 'type'], converters={"flow": float})

        df['timestamp'] = df.apply(lambda x: pd.Timestamp(x['str_timestamp'], tz=timezone_translator(x['tz'])), axis=1)
        df = df.sort_values(by='timestamp', ascending=True)
        df.set_index('timestamp', inplace=True)
        df[['flow']].to_csv('./data_files/Hydro_data_files/Processed_data/time_zone_converted_' + File_id + '.txt')

        print('File ' + File_name + ' converted and saved!')