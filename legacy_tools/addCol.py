import pandas as pd
import csv

def addCol(FPfileslist, filemissingcolumns):

    all_columns = set()

    for file in FPfileslist:
        # Read each file, specifying the delimiter
        df = pd.read_csv(file, delimiter=';')
        # Update the set of all columns
        all_columns.update(df.columns)
    
    # Convert the set of all columns to a sorted list
    all_columns = sorted(all_columns)

    # Initialize a new DataFrame with all unique columns and default NaN values
    new_all_col=['time']+all_columns[:-4] 

    data=pd.read_csv(filemissingcolumns, delimiter =';')
    combined_df = pd.DataFrame(columns=new_all_col)

    for column in new_all_col:
        if column not in data.columns:
            data[column] = None

    data = data[new_all_col]
    
    data.fillna(-100.0, inplace=True)

    combined_df = pd.concat([combined_df, data], ignore_index=True)

    arr=combined_df.values


    with open(filemissingcolumns, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(new_all_col)
            for row in arr:
                writer.writerow(row)