import argparse
import csv
import json
import re
import os
from datetime import datetime, timedelta
import random

def csv_to_json(input_csv_file, output_json_file, date_range):
	
	api_payload = {
		"responseLevel": "FULL",
		"save": "true",
		"process": "true",
		"projectName": "{{PROJECT_NAME}}",
	}
	api_payload["attributes"] = get_attributes(input_csv_file, date_range != None)
	api_payload["records"] = read_data(input_csv_file)
	if date_range != None:
		start_date, end_date = validate_and_parse_date_range(date_range)
		api_payload["attributes"].append({
			"name": "Date",
			"type": "DATE",
			"map": "DOC_DATE",
			"display": "Date",
			"defaultValue": None,
			"isReportable": True,
			"isMultiValue": False,
			"isCaseSensitive": False
		})
		for record in api_payload["records"]:
			record["Date"] = generate_random_date(start_date, end_date)

	with open(output_json_file, 'w', encoding='utf-8') as jsonfile:
		json.dump(api_payload, jsonfile, indent=4)

def convert_multivalue(text):
	if text == '':
		return ''
	substrings = text.split(',')
	quoted_substrings = [f'"{substring.strip()}"' for substring in substrings]
	result = ','.join(quoted_substrings)
	return result

def read_data(input_file):
	json_array = []

	with open(input_file, newline='', encoding='utf-8') as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			json_array.append(row)

	headers = extract_headers(input_file)
	for h in headers:
		if h["type"] == 'MULTIVALUE':
			for row in json_array:
				row[h["name"]] = convert_multivalue(row[h["name"]])
	return json_array

def get_data_type(column_values, header_name):
	# Helper function to check if all values are numbers
	def are_all_numbers(values):
		if average_word_count(values) == 0:
			return False
		return all(value.replace('.', '', 1).isdigit() or value.strip() == '' or value == None for value in values)

	# Helper function to check if all values are dates in ISO format or header contains "DATE"
	def are_all_dates(values):
		date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
		return all(date_pattern.match(value) or "DATE" in header_name.upper() for value in values)

	# Helper function to calculate average word count in values
	def average_word_count(values):
		non_empty_values = [value for value in values if value.strip()]
		
		if not non_empty_values:
			return 0
		
		word_counts = [len(value.split()) for value in non_empty_values]
		return sum(word_counts) / len(word_counts)
	
	def distinct_word_count(values):
		if not values:
			return False
		
		word_count_set = set(word_count(value) for value in values)
		return len(word_count_set)
	
	def distinct_count(values):
		if not values:
			return 0
		
		word_set = set(values)
		return len(word_set)
	
	def word_count(value):
		if not value:
			return 0
		return len(value.split())
	
	def distinct_char_count(values):
		if not values:
			return False
		
		char_count_set = set(len(value) for value in values)
		return len(char_count_set)
	
	
	def are_multi_value(values):
		multi_value_pattern = re.compile(r'^[^,.!?]+(,[^,.!?]+)*$')
		multi_value_mandatory = re.compile(r'^[^,.!?]+(,[^,.!?]+)+$')
		return all(multi_value_pattern.match(value) or value == '' for value in values) and any(multi_value_mandatory.match(value) for value in values)
	
	#distinct_count_threshold = max(len(column_values) / 50, 10) if len(column_values) > 10 else 4

	if "NATURAL_ID" in header_name.upper() or "ID" == header_name.upper() \
		or distinct_count(column_values) == len(column_values) and average_word_count(column_values) < 2:
		return "ID"
	if are_all_numbers(column_values):
		return "NUMBER"
	elif are_all_dates(column_values):
		return "DATE"
	elif are_multi_value(column_values):
		return "MULTIVALUE"
	elif average_word_count(column_values) > 3 \
		and distinct_count(column_values) > len(column_values) * 0.5:
		#and (distinct_word_count(column_values) > distinct_count_threshold \
		#	or distinct_char_count(column_values) > distinct_count_threshold):

		return "VERBATIM"
	elif "SOURCE" in header_name.upper():
		return "SOURCE"
	else:
		return "TEXT"

def extract_headers(input_file):
	with open(input_file, newline='', encoding='utf-8') as csvfile:
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

def get_attributes(input_file, random_date):
	headers = extract_headers(input_file)
	def get_type(type):
		return {
			'ID': 'TEXT',
			'TEXT': 'TEXT',
			'NUMBER': 'NUMBER',
			'DATE': 'DATE',
			'VERBATIM': 'TEXT',
			'MULTIVALUE': 'TEXT',
			'SOURCE': 'TEXT'
			# Add more cases as needed
		}.get(type, 'TEXT')
	def get_map(type):
		return {
			'ID': 'ID1',
			'TEXT': 'STRUCT',
			'NUMBER': 'STRUCT',
			'DATE': 'DOC_DATE' if not random_date else 'STRUCT',
			'VERBATIM': 'VERBATIM',
			'MULTIVALUE': 'STRUCT',
			'SOURCE': 'SOURCE'
			# Add more cases as needed
		}.get(type, 'STRUCT')

	def transform_header(header):
		return {
			"name": header["name"],
			"type": get_type(header["type"]),
			"map": get_map(header["type"]),
			"display": header["name"],
			"defaultValue": None,
			"isReportable": True,
			"isMultiValue": header["type"] == 'MULTIVALUE',
			"isCaseSensitive": False
		}
	return list(map(transform_header, headers))

def validate_and_parse_date_range(date_range):
	try:
		start_date_str, end_date_str = date_range.split(' to ')
		start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
		end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
		return start_date, end_date
	except ValueError:
		raise argparse.ArgumentTypeError("Invalid date range format. Use 'YYYY-MM-DD to YYYY-MM-DD'.")

def generate_random_date(start_date, end_date):
	delta = end_date - start_date
	random_days = random.randint(0, delta.days)
	random_date = start_date + timedelta(days=random_days)
	return random_date.strftime('%Y-%m-%d')
	
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Convert CSV to JSON.')
	parser.add_argument('input', type=str, help='Path to the input CSV file')
	parser.add_argument('output', type=str, help='Path to the output JSON file', nargs='?')
	parser.add_argument('--date-range', type=str, help='Date range for random date population, format: "2023-01-01 to 2023-12-31"')

	args = parser.parse_args()

	input_csv_file = args.input
	output_json_file = args.output
	date_range = args.date_range

	if input_csv_file[-3:] != 'csv':
		print("Error. Can only convert csv files")
		exit(1)
	if output_json_file == None:
		output_json_file = os.path.splitext(input_csv_file)[0] + '.json'

	csv_to_json(input_csv_file, output_json_file, date_range)

	print(f"Conversion successful. JSON data saved to {output_json_file}.")
