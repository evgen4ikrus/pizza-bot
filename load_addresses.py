import os

from environs import Env

from file_helpers import get_json
from moltin_helpers import (create_entry, create_flow, create_flow_field,
                            get_moltin_access_token)


def main():
    env = Env()
    env.read_env()
    addresses_path = env('ADDRESSES_FILE', 'addresses.json')
    flow_name = env('FLOW_NAME', 'Pizzeria')
    flow_slug = env('FLOW_SLUG', 'pizzeria')
    flow_description = env('DESCRIPTION', 'Наши пиццерии')
    moltin_client_id = env('MOLTIN_CLIENT_ID')
    moltin_client_secret = env('MOLTIN_CLIENT_SECRET')
    moltin_access_token = get_moltin_access_token(moltin_client_id, moltin_client_secret)

    flow = create_flow(moltin_access_token, flow_name, flow_slug, flow_description)
    create_flow_field(moltin_access_token, flow['id'], 'Address', 'address', 'string', 'Адреса')
    create_flow_field(moltin_access_token, flow['id'], 'Alias', 'alias', 'string', 'Псевдоним')
    create_flow_field(moltin_access_token, flow['id'], 'Longitude', 'longitude', 'float', 'Долгота')
    create_flow_field(moltin_access_token, flow['id'], 'Latitude', 'latitude', 'float', 'Широта')

    raw_addresses = get_json(os.path.join(addresses_path))
    for raw_address in raw_addresses:
        create_entry(moltin_access_token, 'pizzeria',
                     'alias', raw_address['alias'],
                     'address', raw_address['address']['full'],
                     'longitude', float(raw_address['coordinates']['lon']),
                     'latitude', float(raw_address['coordinates']['lat']),)


if __name__ == '__main__':
    main()
