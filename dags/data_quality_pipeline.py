import pendulum
from airflow import DAG
from datetime import datetime
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
import pandas as pd

# Set the timezone using pendulum
TIMEZONE = pendulum.timezone("UTC")

# Define default_args
default_args = {
    'owner': 'airflow',
    'retries': 1,
}

dag = DAG('data_quality_check_pipeline', default_args=default_args, start_date=datetime(2025, 3, 10), schedule_interval='@daily')

# Python functions for each task
def check_missing_values(df, **kwargs):
    missing_values = df.isnull().sum()
    print(f"Missing values:\n{missing_values}")
    return missing_values.to_dict()  # Return as dict to pass via XCom

def check_data_types(df, **kwargs):
    data_types = df.dtypes
    print(f"Data types:\n{data_types}")
    return data_types.to_dict()  # Return as dict to pass via XCom

def check_duplicates(df, **kwargs):
    duplicates = df[df.duplicated()]
    print(f"Duplicates:\n{duplicates}")
    return duplicates.to_dict()  # Return as dict to pass via XCom

# Define expected data types
expected_data_types = {
    'PassengerId': 'int64',
    'Survived': 'int64',
    'Pclass': 'int64',
    'Name': 'object',
    'Sex': 'object',
    'Age': 'float64',
    'SibSp': 'int64',
    'Parch': 'int64',
    'Ticket': 'object',
    'Fare': 'float64',
    'Cabin': 'object',
    'Embarked': 'object'
}

def report_quality_issues(**kwargs):
    # Retrieve XCom values from previous tasks
    missing = kwargs['ti'].xcom_pull(task_ids='check_missing_value')
    data_types = kwargs['ti'].xcom_pull(task_ids='check_data_types')
    duplicates = kwargs['ti'].xcom_pull(task_ids='check_duplicates')

    # Convert results back to Series
    missing = pd.Series(missing)
    data_types = pd.Series(data_types)
    duplicates = pd.DataFrame(duplicates)

    if missing.any() or not data_types.equals(expected_data_types) or not duplicates.empty:
        print("Data Quality Issues Found!")
        print(f"Missing Values: \n{missing}")
        print(f"Data Types: \n{data_types}")
        print(f"Duplicate Rows: \n{duplicates}")
    else:
        print("Data Quality is Good.")

def load_data(**kwargs):
    # Load the data from CSV
    df = pd.read_csv('data/titanic-dataset.csv')
    kwargs['ti'].xcom_push(key='data', value=df)
    return df

# Define tasks
start_task = EmptyOperator(
    task_id='start',
    dag=dag
)

load_task = PythonOperator(
    task_id='load_data',
    python_callable=load_data,
    provide_context=True,
    dag=dag
)

check_missing_task = PythonOperator(
    task_id='check_missing_value',
    python_callable=check_missing_values,
    op_args=["{{ task_instance.xcom_pull(task_ids='load_data', key='data') }}"],  # Pull the data from XCom
    provide_context=True,
    dag=dag
)

check_data_types_task = PythonOperator(
    task_id='check_data_types',
    python_callable=check_data_types,
    op_args=["{{ task_instance.xcom_pull(task_ids='load_data', key='data') }}"],
    provide_context=True,
    dag=dag
)

check_duplicates_task = PythonOperator(
    task_id='check_duplicates',
    python_callable=check_duplicates,
    op_args=["{{ task_instance.xcom_pull(task_ids='load_data', key='data') }}"],
    provide_context=True,
    dag=dag
)

report_quality_task = PythonOperator(
    task_id='report_quality_issues',
    python_callable=report_quality_issues,
    provide_context=True,
    dag=dag
)

end_task = EmptyOperator(
    task_id='end',
    dag=dag
)

# Set task dependencies
start_task >> load_task >> [check_missing_task, check_data_types_task, check_duplicates_task] >> report_quality_task >> end_task
