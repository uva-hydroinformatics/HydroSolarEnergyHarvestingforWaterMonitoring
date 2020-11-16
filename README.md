# Paper_sims_Maghami_etal

This folder contains the developed codes to perform simulations for the study "Exploring the Complementary Relationship between Solar and Hydro Energy Harvesting for Self-Powered Water Monitoring in Low-Light Conditions".

The developed codes for this study:

- Simulate the energy generation from a minituarized hydro turbine model and streamflow data using the model.
- Simulate the energy generation from solar source using the PVLib library developed by Sandia National Laboratory (https://pvlib-python.readthedocs.io/en/stable).
- Simulate energy storage and consumption by a sensor station using energy store and consumption model introdued by Buchli et al. (2014).
- Evaluate the operation of the self-powered monitoring station given energy consumption, storage and generation.

The data availability:

- While the “Stream velocity time series” for the 42 USGS sites to simulate the energy generation from a minituarized hydro turbine model can be automatically downloaded using the scripts provided, a zipped folder containing this dataset is made available in the Github repository for convenience. Please follow the instructions in the "paper_sims_Maghami_etal/data_files/hydro_data_files/" folder for further information.
- The “Historical satellite-derived estimated weather data” from Clean Power Research’s SolarAnywhere (https://data.solaranywhere.com) is used to simulate the energy generation from solar source. There is a free educational license available that was used in this study, but this license does not allow for public sharing of the data. "paper_sims_Maghami_etal/data_files/solar_data_files/" is the folder where these data need to be placed.




