# Data engineering practice

Scripts I wrote while practicing and testing data engineering ideas. This is a scratchpad, not a polished project — I keep it public because some of the snippets are useful to look back at.

## What's here

- `python/etl-project.py` — small ETL that reads raw JSON files (customers, products, orders) from S3, cleans and joins them with pandas, and writes the processed output back to S3
- `python/Sales-DW.py` — downloads sales CSVs from S3, cleans and reshapes them to a warehouse schema, loads them into a SQL Server FactSales table, and posts progress notifications to Slack
- `python/DataBase.py` and `python/MongoClient.py` — database connection experiments (SQL Server, MongoDB)
- `python/Project_Training.py` — misc training exercises
- `flattened_users.json` — sample output from a JSON flattening exercise

## Notes

Credentials are read from environment variables (`.env` via python-dotenv) — nothing sensitive is committed.
