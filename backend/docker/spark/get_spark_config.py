# get_spark_config.py
import sys
import json
from pyspark.sql import SparkSession

args = sys.argv[1:]
config_dict = {}

# Lire les arguments sous forme de clé=valeur
for arg in args:
    if '=' in arg:
        key, val = arg.split('=', 1)
        config_dict[key] = val

builder = SparkSession.builder

for key, val in config_dict.items():
    builder = builder.config(key, val)

spark = builder.getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
conf = spark.sparkContext.getConf().getAll()

print(json.dumps(dict(conf)))

