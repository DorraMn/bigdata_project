#!/usr/bin/env python3
import sys
import json
import xml.etree.ElementTree as ET
import os

HBASE_SITE_PATH = "/opt/hbase-2.1.3/conf/hbase-site.xml"

def load_config(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} introuvable")
    config = {}
    tree = ET.parse(path)
    root = tree.getroot()
    for prop in root.findall("property"):
        name = prop.find("name").text
        value = prop.find("value").text
        config[name] = value
    return config

def save_config(path, config):
    root = ET.Element("configuration")
    for k, v in config.items():
        prop = ET.SubElement(root, "property")
        name_elem = ET.SubElement(prop, "name")
        name_elem.text = k
        value_elem = ET.SubElement(prop, "value")
        value_elem.text = str(v)
    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(json.dumps(load_config(HBASE_SITE_PATH), indent=2))
    else:
        config = load_config(HBASE_SITE_PATH)
        for arg in sys.argv[1:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                config[k] = v
        save_config(HBASE_SITE_PATH, config)
        print(json.dumps({"status": "updated", "config": config}, indent=2))
