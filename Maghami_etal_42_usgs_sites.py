# Imports usgs module from environment package
from context import usgs
import os

start_date = '2009-12-30'
end_date = '2015-01-01'

USGS_sites_file = os.path.join('./', 'data_files/USGS_Sites_Info_12_7_2019.txt')

parameter_id = []
site_number = []
Error_count = 0


with open(USGS_sites_file) as f:
    # reads all lines in the file
    reader = f.readlines()

    # Removes header (USGS std: lines 0 to 28)
    for line in reader[1:]:

        # split each line in rows
        rows = line.split()

        # constructs data vectors
        try:

            # Adds flow velocity value to flow vector
            site_number.append(str(rows[0]))
            parameter_id.append(int(rows[4]))


        except ValueError as e:
            Error_count = Error_count + 1  # counts missing or corrupted data


# Downloads streamflow velocity data for the 42 sites from 2009-12-30 to 2015-01-01 and saves output as the txt files
for i in range(0, len(site_number)):
    usgs.requestdata('data_files/hydro_data_files/' + str(site_number[i]) + "_" + str(parameter_id[i]) + ".txt",
                     str(site_number[i]), str(parameter_id[i]), start_date, end_date, verbose=True)

# Reads USGS text files ', converts them into a pandas dataframe with timezone aware timestamps and saves the data in
# '.pkl'-foramt files
for i in range(0, len(site_number)):
    usgs.txt2pkldataframe('data_files/hydro_data_files/'+ str(site_number[i]) + "_" + str(parameter_id[i]) + ".txt",
                          verbose=True)

