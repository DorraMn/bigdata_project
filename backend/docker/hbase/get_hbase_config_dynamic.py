# get_hbase_config_dynamic.py

import sys
import json
import xml.etree.ElementTree as ET

HBASE_SITE_PATH = "/hbase-2.1.3/conf/hbase-site.xml"

def parse_hbase_site(path):
    config = {}
    try:
        tree = ET.parse(path)
        root = tree.getroot()

        for prop in root.findall('property'):
            name = prop.find('name')
            value = prop.find('value')
            if name is not None and value is not None:
                config[name.text] = value.text
    except Exception as e:
        config["error"] = str(e)

    return config

if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        # Utiliser le chemin passé en argument si fourni
        config_path = args[0]
    else:
        config_path = HBASE_SITE_PATH

    config = parse_hbase_site(config_path)
    print(json.dumps(config))
