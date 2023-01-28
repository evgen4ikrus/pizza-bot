import json


def get_json(path):
    with open(path, 'r', encoding='UTF-8') as file:
        file_contents = file.read()
    contents = json.loads(file_contents)
    return contents
