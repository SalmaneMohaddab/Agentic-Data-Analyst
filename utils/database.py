import psycopg2
from dotenv import load_dotenv 
load_dotenv()
import os 

class DatabaseUtil:
    def __init__(self,db_config):
        try:
            self.db_config = db_config
            self.connection = psycopg2.connect(**db_config)
        except Exception as e:
            self.connection = None
    

    def schema_details(self, schema_name : str):
        schema_details = ""

        try: 
            connection= self.connection
            cursor= connection.cursor()

            schema_details = f"Database Schema : {schema_name}\n"
            cursor.execute(f"SELECT * FROM information_schema.tables WHERE table_schema = %s", (schema_name, ))
            tables_list = cursor.fetchall()

            for table in tables_list: 
                table_name = table[2]
                schema_details = f" {schema_details} \n Table Name : {table_name} \n "

                cursor.execute("Select column_name,data_type  from information_schema.columns where table_name = %s and table_schema = %s", (table_name, schema_name))
                column_name_data_type = cursor.fetchall()

                for column in column_name_data_type:  
                    column_name = column[0]
                    column_data_type = column[1]
                    schema_details = f" {schema_details} \n column_name : {column_name} \n column_data_type : {column_data_type} "
                
                # dummy data for each table
                cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5")
                dummy_data = cursor.fetchall()
                schema_details= f" {schema_details}\nSample Data : \n" 
                for dd in dummy_data:
                    schema_details = f"{schema_details} {dd}\n"
            cursor.close()
            return schema_details
        except Exception as e:
            self.connection = None
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return schema_details
    def execute_sql(self,sql_query : str):
        try:
            connection = self.connection
            cursor = connection.cursor()
            cursor.execute(sql_query)
            result = cursor.fetchall()
            return str(result)
        except Exception as e:
            return f"Error executing SQL query: {e}"
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

