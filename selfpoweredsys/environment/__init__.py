
#################################################################################
#
#  Environment package of the selfpoweredsys library contains the following modules
#
#			usgs: downloads USGS environmental data, formats it and saves it in pandas
#				  dataframe format with timezone-aware timestamps
#
#			timeseries: resamples dataframe time series, evaluates missing data,
#						creates ARMA models and synthetic traces 
#
#################################################################################


__all__ = ["usgs", "ehdc","timeseries"]
