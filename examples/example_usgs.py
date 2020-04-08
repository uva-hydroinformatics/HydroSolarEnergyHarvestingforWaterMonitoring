# Imports usgs module from environment package
from context import usgs

# Downloads streamflow velocity data from site 03612600 from 2013-02-03 to 2013-04-03 and saves output as the file 'data_files/ILState03612600.csv'
usgs.requestdata('data_files/ILState03612600.csv', '03612600', '72255', '2018-01-10', '2018-02-20',verbose=True)

# Reads USGS text file 'data_files/ILState03612600.csv', converts it into a pandas dataframe with timezone aware timestamps and saves the data in 'data_files/ILState03612600.pkl' file
usgs.txt2pkldataframe('data_files/ILState03612600.csv',verbose=True)
