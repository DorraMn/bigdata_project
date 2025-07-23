# get_hbase_config_dynamic.py
import json
import xml.etree.ElementTree as ET

HBASE_SITE_PATH = "/hbase-2.1.3/conf/hbase-site.xml"

def parse_hbase_site():
    config = {}
    try:
        tree = ET.parse(HBASE_SITE_PATH)
        root = tree.getroot()

        for prop in root.findall('property'):
            name = prop.find('name').text
            value = prop.find('value').text
            config[name] = value
    except Exception as e:
        config["error"] = str(e)

    print(json.dumps(config))

if __name__ == "__main__":
    parse_hbase_site()
        