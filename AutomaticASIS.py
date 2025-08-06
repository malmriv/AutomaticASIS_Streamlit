import os
import shutil
import zipfile
import xml.etree.ElementTree as ET
import csv
import re
import secrets
import string
import sys

ADDRESS_KEYS_BY_TYPE = {
    'HTTPS': ['urlPath'],
    'HTTP': ['httpAddressWithoutQuery'],
    'SFTP': ['host'],
    'JMS': {
        'Sender': ['QueueName_inbound'],
        'Receiver': ['QueueName_outbound']
    },
    'ProcessDirect': ['address'],
    'HCIOData': ['address'],
    'SOAP': ['address'],
    'PollingSFTP': ['host'],
    'JDBC': ['alias'] 
}

TEMP_DIR = './temp'


def unzip_file(zip_path, extract_to):
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"Zip file not found: {zip_path}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)


def find_iflw_file(root_dir):
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.iflw'):
                return os.path.join(root, file)
    raise FileNotFoundError("No .iflw file found in extracted content.")


def strip_namespace(tag):
    return tag.split('}', 1)[-1] if '}' in tag else tag


def load_parameters(root_dir):
    params = {}
    for root, _, files in os.walk(root_dir):
        if 'parameters.prop' in files:
            with open(os.path.join(root, 'parameters.prop'), encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.replace('\\ ', ' ').strip()
                        params[key] = value.strip()
            break
    return params


def parse_manifest(manifest_path):
    bundle_name = version = bundle_id = None
    if not os.path.isfile(manifest_path):
        return bundle_name, version, bundle_id

    with open(manifest_path, encoding='utf-8') as f:
        content = f.read()

    lines = []
    for line in content.splitlines():
        if line.startswith(' '):
            lines[-1] += line[1:]
        else:
            lines.append(line)

    for line in lines:
        if line.startswith('Bundle-Name:'):
            bundle_name = line.split(':', 1)[1].strip()
        elif line.startswith('Bundle-Version:'):
            version = line.split(':', 1)[1].strip()
        elif line.startswith('Origin-Bundle-SymbolicName:'):
            bundle_id = line.split(':', 1)[1].strip()

    return bundle_name, version, bundle_id


def parse_package_name(export_info_path):
    if not os.path.exists(export_info_path):
        return 'Unknown'
    with open(export_info_path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('Name='):
                return line.split('=', 1)[1].strip()
    return 'Unknown'


def generate_prefix_from_package(package_name):
    words = re.findall(r'[A-Z]{2,}|[A-Z][a-z]+', package_name)
    prefix = ''.join(word[0] for word in words if word).upper()
    return prefix[:5] if prefix else 'PKG'


def extract_message_flows(iflw_path, iflow_name, iflow_id, version, parameters, package_name, uid):
    tree = ET.parse(iflw_path)
    root = tree.getroot()
    results = []

    for elem in root.iter():
        if strip_namespace(elem.tag) == "messageFlow":
            message_data = {
                'UID': uid,
                'Package': package_name,
                'Iflow': iflow_name,
                'IflowID': iflow_id,
                'IflowVersion': version,
                'AdapterType': None,
                'TransportProtocol': None,
                'AdapterDirection': None,
                'AdapterName': None,
                'AdapterVersion': None,
                'AdapterAddress': None,
                'IsParametrized': False
            }

            for child in elem:
                if strip_namespace(child.tag) == "extensionElements":
                    properties = {}
                    for prop in child.iter():
                        if strip_namespace(prop.tag) == "property":
                            key = value = None
                            for kv in prop:
                                tag = strip_namespace(kv.tag)
                                if tag == "key":
                                    key = kv.text
                                elif tag == "value":
                                    value = kv.text
                            if key:
                                properties[key] = value

                    message_data['AdapterType'] = properties.get('ComponentType')
                    message_data['AdapterDirection'] = properties.get('direction')
                    message_data['AdapterName'] = properties.get('Name')
                    message_data['TransportProtocol'] = properties.get('TransportProtocol')
                    message_data['AdapterVersion'] = properties.get('componentVersion')

                    ctype = message_data['AdapterType']
                    direction = message_data['AdapterDirection']
                    possible_keys = ADDRESS_KEYS_BY_TYPE.get(ctype, {})
                    if isinstance(possible_keys, dict):
                        possible_keys = possible_keys.get(direction, [])

                    address = None
                    for k in possible_keys:
                        if k in properties:
                            address = properties[k]
                            break
                    if not address:
                        for key, val in properties.items():
                            if val and 'url' in key.lower():
                                address = val
                                break

                    def substitute_param(match):
                        param_key = match.group(1).strip()
                        message_data['IsParametrized'] = True
                        return parameters.get(param_key, match.group(0))

                    if address:
                        address = re.sub(r'{{(.*?)}}', substitute_param, address)

                    message_data['AdapterAddress'] = address

            if message_data['AdapterType']:
                results.append(message_data)

    return results


def save_to_csv(data, output_path):
    with open(output_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(
            file,
            fieldnames=['UID', 'Package', 'Iflow', 'IflowID', 'IflowVersion', 'AdapterType', 'TransportProtocol',
                        'AdapterDirection', 'AdapterName', 'AdapterVersion', 'AdapterAddress', 'IsParametrized'],
            quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        writer.writerows(data)


def prepare_inner_zips(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if '_' in file and '.' not in file:
                new_file_path = file_path + '.zip'
                os.rename(file_path, new_file_path)


def process_inner_zip(zip_path, package_name, iflow_index, uid_prefix):
    extract_path = os.path.splitext(zip_path)[0]
    unzip_file(zip_path, extract_path)

    iflw_file = find_iflw_file(extract_path)
    parameters = load_parameters(extract_path)
    manifest_path = os.path.join(extract_path, 'META-INF', 'MANIFEST.MF')
    iflow_name, version, iflow_id = parse_manifest(manifest_path)

    uid = f"{uid_prefix}-{iflow_index}"
    return extract_message_flows(iflw_file, iflow_name, iflow_id, version, parameters, package_name, uid)


def generate_short_id(length=7):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def main():
    if len(sys.argv) < 2:
        print("❌ No input directory provided.")
        return
    input_dir = sys.argv[1]
    output_uid = generate_short_id()
    output_csv = os.path.join(input_dir, f'automatic_asis_{output_uid}.csv')
    all_flows = []
    package_iflow_counter = {}

    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    zip_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.zip')]
    if not zip_files:
        print("❌ No zip files found.")
        return

    try:
        for zip_file in zip_files:
            zip_path = os.path.join(input_dir, zip_file)
            short_id = generate_short_id()
            extract_dir = os.path.join(TEMP_DIR, short_id)
            try:
                unzip_file(zip_path, extract_dir)

                export_info_path = os.path.join(extract_dir, 'ExportInformation.info')
                package_name = parse_package_name(export_info_path)
                uid_prefix = generate_prefix_from_package(package_name)

                package_iflow_counter.setdefault(uid_prefix, 0)

                prepare_inner_zips(extract_dir)
                inner_zips = [
                    os.path.join(root, f)
                    for root, _, files in os.walk(extract_dir)
                    for f in files if f.endswith('.zip')
                ]
                if not inner_zips:
                    print(f"⚠️  No inner zip files found in '{zip_file}'.")

                for inner_zip in inner_zips:
                    try:
                        package_iflow_counter[uid_prefix] += 1
                        index = package_iflow_counter[uid_prefix]
                        flows = process_inner_zip(inner_zip, package_name, index, uid_prefix)
                        all_flows.extend(flows)
                        print(f"✅ Processed inner zip '{os.path.basename(inner_zip)}' with {len(flows)} adapters.")
                    except Exception as e:
                        print(f"❌ Error processing inner zip '{inner_zip}': {e}")
            except Exception as e:
                print(f"❌ Error unzipping '{zip_file}': {e}")

        if all_flows:
            save_to_csv(all_flows, output_csv)
            print(f"✅ Saved {len(all_flows)} adapters into '{output_csv}'.")
        else:
            print("❌ No adapters found to save.")
    finally:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)


if __name__ == '__main__':
    main()