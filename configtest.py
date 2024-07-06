import json
from typing import Any, Dict

import jsonschema
import yaml


def load_yaml(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def load_json_schema(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        raise Exception(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON format in {file_path}: {e}")


def validate_config(config: Dict[str, Any], schema: Dict[str, Any]):
    jsonschema.validate(instance=config, schema=schema)


def merge_configs(configs: list[Dict[str, Any]]) -> Dict[str, Any]:
    merged_config = {}
    for config in configs:
        for key, value in config.items():
            if isinstance(value, list):
                if key not in merged_config:
                    merged_config[key] = []
                merged_config[key].extend(value)
            elif isinstance(value, dict):
                if key not in merged_config:
                    merged_config[key] = {}
                merged_config[key].update(value)
            else:
                merged_config[key] = value
    return merged_config


def config_to_json(config: Dict[str, Any]) -> str:
    return json.dumps(config)

def write_json_to_file(json_str: str, file_path: str):
    with open(file_path, "w") as file:
        file.write(json_str)

# Usage
try:
    schema = load_json_schema("schema.json")
    config1 = load_yaml("config1.yaml")
    #config2 = load_yaml("config2.yaml")

    merged_config = merge_configs([config1])
    validate_config(merged_config, schema)

    config_json = config_to_json(merged_config)
    print(config_json)
    write_json_to_file(config_json, "config.json")

except Exception as e:
    print(f"Error: {e}")
