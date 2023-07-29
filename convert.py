import argparse
import csv
import json
import re

def csv_to_json(input_csv_file, output_json_file):
	
	api_payload = {
		"responseLevel": "FULL",
		"save": "true",
		"process": "true",
		"projectName": "<YOUR PROJECT NAME>",
	}
	api_payload["attributes"] = get_attributes(input_csv_file)
	api_payload["records"] = read_data(input_csv_file)

	with open(output_json_file, 'w') as jsonfile:
		json.dump(api_payload, jsonfile, indent=4)

def read_data(input_file):
	json_array = []

	with open(input_file, newline='') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			json_array.append(row)

	return json_array

def get_data_type(column_values, header_name):
	# Helper function to check if all values are numbers
	def are_all_numbers(values):
		return all(value.replace('.', '', 1).isdigit() for value in values)

	# Helper function to check if all values are dates in ISO format or header contains "DATE"
	def are_all_dates(values):
		date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
		return all(date_pattern.match(value) or "DATE" in header_name.upper() for value in values)

	# Helper function to calculate average word count in values
	def average_word_count(values):
		word_counts = [len(value.split()) for value in values]
		return sum(word_counts) / len(word_counts)
	
	if ("NATURAL_ID" in header_name.upper()):
		return "ID"
	if are_all_numbers(column_values):
		return "NUMBER"
	elif are_all_dates(column_values):
		return "DATE"
	elif average_word_count(column_values) > 2:
		return "VERBATIM"
	else:
		return "TEXT"

def extract_headers(input_file):
	with open(input_file, newline='') as csvfile:
		reader = csv.reader(csvfile)
		headers = next(reader)  # Extract headers from the first row
		column_values = {header: [] for header in headers}

		for row in reader:
			for header, value in zip(headers, row):
				column_values[header].append(value)
	data_types = {header: get_data_type(values, header) for header, values in column_values.items()}

	headers_info = []
	for header in headers:
		headers_info.append({"name": header, "type": data_types[header]})

	return headers_info

def get_attributes(input_file):
	headers = extract_headers(input_file)
	def get_type(type):
		return {
			'ID': 'TEXT',
			'TEXT': 'TEXT',
			'NUMBER': 'NUMBER',
			'DATE': 'DATE',
			'VERBATIM': 'TEXT',
			# Add more cases as needed
		}.get(type, 'TEXT')
	def get_map(type):
		return {
			'ID': 'ID1',
			'TEXT': 'STRUCT',
			'NUMBER': 'STRUCT',
			'DATE': 'DOC_DATE',
			'VERBATIM': 'VERBATIM',
			# Add more cases as needed
		}.get(type, 'STRUCT')

	def transform_header(header):
		return {
			"name": header["name"],
			"type": get_type(header["type"]),
			"map": get_map(header["type"]),
			"display": header["name"],
			"defaultValue": None,
			"isReportable": True
		}
	return list(map(transform_header, headers))
	
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Convert CSV to JSON.')
	parser.add_argument('input', type=str, help='Path to the input CSV file')
	parser.add_argument('output', type=str, help='Path to the output JSON file')

	args = parser.parse_args()

	input_csv_file = args.input
	output_json_file = args.output

	csv_to_json(input_csv_file, output_json_file)

	print(f"Conversion successful. JSON data saved to {output_json_file}.")
