#################################################################################
#
# Function: requestdata
#
# Description: downloads data from usgs website and outputs or saves in a text file
#
# Inputs:   file_name,                                                           
#           site_number,                                                         
#           parameter_id,
#           start_date,                                                        
#           end_date
#
# Optional: save_file,                                                           
#           output_vec,
#           verbose
#
# Output: writes a text file (default) or outputs a string vector with the USGS site data requested
#
#################################################################################

def requestdata(file_name, site_number, parameter_id, start_date, end_date, 
                save_file=True, output_vec=False, verbose=False):

    # Imports the "requests" library dependency
    import requests

    ## EXAMPLE OF VALID INPUTS:
    # site_number = '03612600', file_name = 'ILState03612600.csv'
    # parameter_id = '72255' # (Mean water velocity for discharge computation, feet per second)
    # start_date = '2013-02-03', end_date = pd.datetime.today().strftime('%Y-%m-%d') # import pandas as pd  

    #Creating the url to receive the real time data (USGS format)
    url= 'https://nwis.waterdata.usgs.gov/usa/nwis/uv/?cb_{para_id}=on&format=rdb&site_no={site_id}&period=&' \
     'begin_date={beg_date}&end_date={end_date}'.format(
    para_id=parameter_id,
    site_id=site_number,
    end_date=end_date,
    beg_date=start_date
    )

    # Checks if verbose is enabled and prints inputs
    if (verbose==True):
        print(" ")
        print("Loaded http request input values:")
        print("  Site number: "+str(site_number)+"; Parameter ID: "+str(parameter_id)+";")
        print("  Start date: "+str(start_date)+"; End date: "+str(end_date)+";")
        print("Initiating HTTP request to USGS NWIS...")

    # Downloads url
    r = requests.get(url)

    # Checks if save_file option is enabled
    if save_file==True:

        try:
            # Saves data in text file
            with open(file_name, 'w') as f: 
                f.write(r.text)

            # Checks if verbose is enabled and prints success message
            if (verbose==True):
                print("File "+file_name+" was successfully saved!")

        except:

            # Checks if verbose is enabled and prints error message
            if (verbose==True):
                print("<<Error: File "+file_name+" was not saved>>")
            
    else:
        
        # Checks if verbose is enabled and prints warning message
        if (verbose==True):
            # Prints warning that file was not saved
            print("<<Warning: File "+file_name+" was not saved>>")

    # Checks if output_vec option is enabled
    if output_vec==True:
        
        # Checks if verbose is enabled and prints warning message
        if (verbose==True):
            print("<<Warning: output vector enabled>>")

        # Function returns data vector
        return r.text
    



#################################################################################
#
# Function: timezone_translator
#
# Description: Translates timezone string used in USGS files to tzinfo standard
#
# Inputs:   timezone_str                                                           
#
# Optional: verbose                                                           
#
# Output: Translated string in tzinfo format (GMT based)
#
#################################################################################

def timezone_translator(timezone_str, verbose=False):
    # Replaces string with one of the options listed or keeps the original if conversion is not possible 
    translated_tz_str = {
        'EST': 'Etc/GMT+5',
        'EDT': 'Etc/GMT+4',
        'PST': 'Etc/GMT+8',
        'PDT': 'Etc/GMT+7',
        'CST': 'Etc/GMT+6',
        'CDT': 'Etc/GMT+5',
        'MST': 'Etc/GMT+7',
        'MDT': 'Etc/GMT+6' 
    }.get(timezone_str, timezone_str)

    # If conversion could not be made and verbose option is enabled, prints warning
    if translated_tz_str==timezone_str and verbose==True:
        print("Warning, timezone could not be translated. Currently using timezone string as "+timezone_str+".")

    # Returns translated string
    return translated_tz_str



#################################################################################
#
# Function: txt2pkldataframe
#
# Description: Reads a USGS text file and converts
#
# Input:    file_name                                                           
#
# Optional: output_folder,
#           save_file,
#           output_df,
#           verbose
#
# Outputs: writes a pkl file with the pandas formated dataframe of timestamp and flow velocity data
#
#################################################################################



def txt2pkldataframe(file_name, output_folder=None, input_folder=None, save_file=True, output_df=False, verbose=False):
    
    # Imports the "pandas" library dependency
    import pandas as pd

    # define converter
    def convert_flow(raw_value):
        try:
            float_value = float(raw_value)
        except:
            float_value = float('nan')
        return float_value

    # Splits the file id from the extension
    [file_id, extension]=file_name.split('.',1)

    # Parameters used in USGS text files
    header_rows=1
    comment_symbol='#'
    delimiter_symbol='\t'

    # Checks if verbose is enabled and prints inputs
    if (verbose==True):
        print(" ")
        print("Reading file "+file_name+" with following input parameters:")
        print("  header rows:      "+str(header_rows)+";")
        print("  comment symbol:   "+comment_symbol+";")
        print("  delimiter symbol: "+delimiter_symbol+";")

    if (input_folder==None):
        file_loc = file_name
    else:
        file_loc = input_folder+'/'+file_name

    # Reads the text file and converts it to a dataframe
    df=pd.read_csv(file_loc, delimiter=delimiter_symbol,header=header_rows,comment=comment_symbol, names=['agency','station','str_timestamp', 'tz', 'flow', 'type'], converters={"flow":convert_flow}) 
    #df["flow"] = convert_flow(df["flow"])

    # Checks if verbose is enabled and prints read success message
    if (verbose==True):
        print(" ")
        print("File "+file_name+" was successfully read and information was converted to pandas dataframe!")

    # Converts the timestamp string information into pandas timezone aware timestamp 
    df['timestamp']=df.apply(lambda x: pd.Timestamp(x['str_timestamp'], tz= timezone_translator(x['tz'], verbose=verbose)) , axis=1)


    # Formats dataframe to contain only timestamp and flow
    formated_df = df[['timestamp','flow']]
    
    # Selects timestamp as the dataframe index
    formated_df.set_index('timestamp',inplace=True) 

    # Checks if verbose is enabled and prints timestamp conversion success message and dataframe head
    if (verbose==True):
        print(" ")
        print("File "+file_name+" timezone information was successfully converted to pandas timestamp!")
        print(file_id)
        print(" ")
        print("This is the head of converted dataframe")
        print(formated_df.head())

    # Checks if save file option is enabled
    if save_file==True:

        # Checks if output folder option is used
        if output_folder==None:
            # Saves pkl file in current directory 
            formated_df.to_pickle('./'+file_id+'.pkl')

        else:
            # Saves pkl file in given folder
            formated_df.to_pickle('./'+output_folder+'/'+file_id+'.pkl')

        # Checks if verbose is enabled and prints pkl write success message
        if (verbose==True):
            print(" ")
            print("File "+file_name+" was successfully saved in pkl format!")

    # Checks if output dataframe option is enabled
    if output_df==True:
        return formated_df
