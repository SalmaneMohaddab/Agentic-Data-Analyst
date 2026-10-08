import os
import requests 
import pandas as pd

class ETLTools:
    def __init__(self):
        pass

    def extract_load(self, url:str, dest_folder:str, format:str):
        """
        Extracts data from an api (url) source and loads it into the desired Location (destination) .
        Args:
            url(str): The url of the api
            dest_folder(str): The path to the destination folder 
            format(str): The format of the data to be loaded (json, csv, or parquet)
        Return:
            message(str): A message indicating the status of the extraction and loading process.
        """
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(project_dir,dest_folder)
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            filename= os.path.join(output_path,f"data.{format}")
            os.makedirs(output_path,exist_ok=True)
            df= pd.json_normalize(data)
            if format == "csv":
                df.to_csv(filename,index=False)
            elif format == "parquet":
                df.to_parquet(filename,index=False)
            elif format == "json":
                df.to_json(filename,index=False)
            else:
                raise ValueError("Invalid format. Please provide one of the following: csv, parquet, or json")
            return f"Data extracted from {url} and loaded to {filename}"
        except Exception as e:
            return f"Error: {e}"

    def transforme_load_context(self, file_path:str, dest_folder:str, format:str):
        """
        Transformes data from a file and loads it into the desired format.
        Args:
            file_path(str): The path to the file to be transformed
            dest_folder(str): The path to the destination folder 
            format(str): The format of the data to be loaded (json, csv, or parquet)
        Return:
            message(str): A message indicating the status of the transformation and loading process.
        """
        try:
            filename_extension = os.path.splitext(file_path)[1].lower()
            if filename_extension == ".csv":
                df = pd.read_csv(file_path)
            elif filename_extension == ".parquet":
                df = pd.read_parquet(file_path)
            elif filename_extension == ".json":
                df = pd.read_json(file_path)
            else:
                raise ValueError("Invalid format. Please provide one of the following: csv, parquet, or json")
            top_5_rows = str(df.head(5))
            return f"The first 5 rows of the data are:\n{top_5_rows}"
        except Exception as e:
            return f"Error: {e}"

    def execute_code(self, code:str):
        """
        Executes the given code and returns the result.
        Args:
            code(str): The code to be executed
        Return:
            message(str): A message indicating the status of the execution.
        """
        try:
            exec(code)
            return "Code executed successfully"
        except Exception as e:
            return f"Error: {e}"
            



if __name__ == "__main__":
    etl_tools = ETLTools()
    print