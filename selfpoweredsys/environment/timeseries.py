#################################################################################
#
# Function: missingsamples
#
# Description: Counts the number of missing samples of a time series dataframe
#
# Input:   df                                                           
#
# Optional: max_period,                                                           
#           verbose
#
# Output: returns missing samples 
#
#################################################################################

def missingsamples(df, step_unit='T', max_period=15, verbose=False):

    # Imports the library dependencies
    import numpy as np
    import pandas as pd

    # Checks if verbose is enabled and prints input parameters
    if (verbose==True):
        print(" ")
        print("Evaluating missing samples...")
        print(" chosen step units:         "+step_unit)
        print(" max period in step units:  "+str(max_period))

  
    # Converts timestamp to datetime UTC time and round it to given step unit
    df.index = pd.to_datetime(df.index, utc='true').round(step_unit)

    # Resamples the input dataframe to given step unit
    reference_df = df.resample(step_unit).asfreq()

    # Counts and groups missing values in the reference dataframe
    time_without_sample = reference_df[reference_df.columns[0]].isnull().astype(int).groupby(reference_df[reference_df.columns[0]].notnull().astype(int).cumsum()).sum()

    # Selects periods without sample longer than max_period
    sample_gap = time_without_sample.loc[time_without_sample >= max_period]

    # Calculates how many missing samples per sampling gap
    missing_count = sample_gap.apply(lambda x: np.floor(x/max_period))

    # Checks if verbose is enabled and prints reference dataframe and grouped missing samples dataframe and missing sample gaps
    if (verbose==True):
        print(" ")
        print("Reference resampled dataframe:")
        print(reference_df.head())
        print(" ")
        print("Grouped steps without sample dataframe:")
        print(time_without_sample.head())
        print(" ")
        print("Missing sample gaps dataframe:")
        print(sample_gap.head())
        print(" ")
        print("Missing sample count dataframe:")
        print(missing_count.head())

    # Calculates total number of missing samples
    total_missing_samples = missing_count.sum()

    # Calculates expected total number of samples
    total_samples = np.floor(len(reference_df.index)/max_period)

    # Calculates the percentage of missing samples
    percentage_missing_samples = 100*(total_missing_samples/total_samples)

    # Max sampling gap in number of samples
    max_sample_gap_count = missing_count.max()

    # Max sampling gap in steps
    max_sample_gap = time_without_sample.max()

    # Min sampling gap in steps
    min_sample_gap = time_without_sample.min()

    # Median sampling gap in steps
    median_sample_gap = time_without_sample.median()

    # Calculates max sampling interval
    max_sampling_interval = max_sample_gap + 1

    # Calculates min sampling interval
    min_sampling_interval = min_sample_gap + 1

    # Calculates median sampling interval
    median_sampling_interval = median_sample_gap + 1

    # Calculates average sampling interval
    average_sampling_interval = (time_without_sample.sum()/len(time_without_sample)) + 1

    # Creates the output vector with missing samples information
    missing_sample_report = [max_sampling_interval,
                             min_sampling_interval,
                             median_sampling_interval,
                             average_sampling_interval,
                             total_missing_samples,
                             max_sample_gap,
                             max_sample_gap_count,
                             percentage_missing_samples]

    # Checks if verbose is enabled and prints missing samples information
    if (verbose==True):
        # prints report on missing samples
        print(" ")
        print("Total missing samples:     "+str(int(total_missing_samples))+" out of "+str(int(total_samples))+" (or "+"{0:.4f}".format(percentage_missing_samples)+"%)")
       # print("Longest sample gap:        "+str(int(max_sample_gap_count))+" (or "+str(int(max_sample_gap))+" minutes)")
        print("Average sampling interval: "+"{0:.4f}".format(average_sampling_interval))
        print("Max sampling interval:     "+str(int(max_sampling_interval)))
        print("Min sampling interval:     "+str(int(min_sampling_interval)))
        print("Median sampling interval:  "+str(int(median_sampling_interval)))

    return missing_sample_report



#################################################################################
#
# Function: resampledf
#
# Description: Resamples and interpolates a time series dataframe
#
# Input:    df                                                         
#
# Optional: step,
#           interp_method,                                                           
#           verbose
#
# Output: Resampled dataframe
#
#################################################################################

def resampledf(df, step='T', interp_method='linear', verbose=False):

    # Imports the library dependency
    import pandas as pd

    # Checks if verbose is enabled and prints input parameters
    if (verbose==True):
        print(" ")
        print("Resampling dataframe with parameters:")
        print("  Step:   "+step)
        print("  Method: "+interp_method)

    # Converts timestamp to datetime UTC time 
    df.index = pd.to_datetime(df.index, utc='true').round(step)

    # Resamples the input dataframe using input parameters
    resampled_df = df.resample(step).asfreq().interpolate(method=interp_method)

    # Checks if verbose is enabled and prints output parameters
    if (verbose==True):
        print(" ")
        print("Resampled dataframe:")
        print(resampled_df.head())

    return resampled_df
