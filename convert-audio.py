import csv
from pydub import AudioSegment
import pyttsx3
import random
import json

# offset for initial voice, useful when default first voice is bad
SILENT = True

def categorize_voices(voices):
	male_voices = []
	female_voices = []
	other_voices = []

	for voice in voices:
		for lang in voice.languages:
			if 'en' in lang.lower():
				if 'Male' in voice.gender:
					male_voices.append(voice)
				elif 'Female' in voice.gender:
					female_voices.append(voice)
				else:
					other_voices.append(voice)

	if (len(male_voices) == 0):
		male_voices = voices
	if (len(female_voices) == 0):
		female_voices = voices
	if (len(other_voices) == 0):
		other_voices = voices
	return male_voices, female_voices, other_voices

def select_voice(voices, variant, randomOffset):
	num_voices = len(voices)
	variant += randomOffset
	selected_index = variant % num_voices  # Ensure variant is within the range of supported voices
	return voices[selected_index] if voices else None

def generate_audio_pieces(text_list, randomOffset):
	engine = pyttsx3.init()
	voices = engine.getProperty('voices')
	male_voices, female_voices, other_voices = categorize_voices(voices)

	audio_pieces = []
	for obj in text_list:
		#print(obj)
		gender = obj['gender']
		variant = int(obj['participant_id'])
		if gender == 'MALE':
			selected_voice = select_voice(male_voices, variant, randomOffset)
		elif gender == 'FEMALE':
			selected_voice = select_voice(female_voices, variant, randomOffset)
		else:
			selected_voice = select_voice(other_voices, variant, randomOffset)
		
		if selected_voice:
			print(f"Playing: {selected_voice.id}, text: {obj['text']}")
			engine.setProperty('voice', selected_voice.id)
			if not SILENT:
				engine.say(obj['text'])
			engine.save_to_file(obj['text'], 'temp.wav')
			engine.runAndWait()

			audio = AudioSegment.from_file('temp.wav')
			duration = len(audio)  # Duration in seconds
			audio_pieces.append((audio, duration))

	return audio_pieces

def merge_audio_with_delays(audio_pieces, delays):
	result_audio = AudioSegment.silent(duration=0)
	start_end_times = []
	current_time = 0

	for i, (audio, duration) in enumerate(audio_pieces):
		delayMillis = 300 + delays[i] * 1000 if delays[i] is not None else None
		if delayMillis is None:
			# If delay is None, concatenate with 300ms silence
			silence = AudioSegment.silent(duration=300)
			result_audio += silence + audio
			start_end_times.append({'start': current_time, 'end': current_time + duration})
			current_time += duration + 300  # Adding 1s silence duration
		elif delayMillis >= 0:
			# If delay is positive, add the specified delay before concatenating
			silence = AudioSegment.silent(duration=delayMillis)
			result_audio += silence + audio
			start_end_times.append({'start': current_time + delayMillis, 'end': current_time + delayMillis + duration})
			current_time += duration + delayMillis
		else:
			# If delay is negative, overlay the current audio piece over the previous one
			overlap_start = max(current_time + delayMillis, start_end_times[-1]['start'])
			overlap_end = overlap_start + duration
			
			result_audio = result_audio[:overlap_start] \
				+ audio.overlay(result_audio[overlap_start:min(overlap_end, current_time)]) \
				+ result_audio[overlap_end:]
			
			start_end_times.append({'start': overlap_start, 'end': overlap_end})
			current_time = max(overlap_end, current_time)

		print(f"Time: {start_end_times[-1]} (delay: {delayMillis})")

	return result_audio, start_end_times

def read_csv(file_path):
	data = []
	with open(file_path, 'r', newline='', encoding='utf-8') as file:
		reader = csv.DictReader(file)
		for row in reader:
			data.append(row)
	return data

# def write_csv(file_path, data, fieldnames):
# 	with open(file_path, 'w', newline='', encoding='utf-8') as file:
# 		writer = csv.DictWriter(file, fieldnames=fieldnames)
# 		writer.writeheader()
# 		writer.writerows(data)

def merge_data(conversation_data, participants_data):

	gender_dict = {row['name']: row['gender'] for row in participants_data}
	type_dict = {row['name']: row['gender'] for row in participants_data}
	participant_id_mapping = {row['name']: str(i) for i, row in enumerate(participants_data)}  # Mapping name to index
		
	merged_data = []
	for text_row in conversation_data:
		name = text_row['name']
		participant_id = participant_id_mapping.get(name, '')
		text_row['participant_id'] = participant_id
		text_row['type'] = type_dict.get(text_row['name'], '')
		text_row['gender'] = gender_dict.get(text_row['name'], '')
		merged_data.append(text_row)
	
	return merged_data

def convert_to_json(participants_data, audio_segments, id):
	json_data = {}

	# Add additional fields
	json_data['ID'] = id
	json_data['duration'] = audio_segments[-1]['end'] if audio_segments else 0
	json_data['segment_type'] = 'SENTENCE'
	json_data['participants'] = []
	json_data['segments'] = []

	for (i, row) in enumerate(participants_data):
		participant = {
			'participant_id': str(i),
			'gender': 'MALE' if row['gender'] == 'ROBOT' else row['gender'],
			'type': row['type'],
			'is_bot': True if row['gender'] == 'ROBOT' else False
		}
		json_data['participants'].append(participant)

	# Populate the segments array
	for segment in audio_segments:
		segment_data = {
			'participant_id': segment['participant_id'],
			'start': segment['start'],
			'end': segment['end'],
			'text': segment['text']
		}
		json_data['segments'].append(segment_data)

	return json_data

def convert_to_payload(json_data, id):
	return {
		'responseLevel': 'FULL',
		'save': True,
		'process': True,
		'projectName': '<YOUR_PROJECT>',
		'attributes': [
			{
				'name': 'verbatim_type_for_agent',
				'type': 'TEXT',
				'map': 'VERBATIM',
				'verbatimMetadataTags': [
					'CHANNEL_AGENT',
					'TYPE_AUDIO'
				]
			},
			{
				'name': 'verbatim_type_for_bot',
				'type': 'TEXT',
				'map': 'VERBATIM',
				'verbatimMetadataTags': [
					'CHANNEL_UNKNOWN',
					'TYPE_AUDIO'
				]
			},
			{
				'name': 'verbatim_type_for_client',
				'type': 'TEXT',
				'map': 'VERBATIM',
				'verbatimMetadataTags': [
					'CHANNEL_CLIENT',
					'TYPE_AUDIO'
				]
			},
			{
				'name': 'cool_rich_verbatim',
				'type': 'TEXT',
				'map': 'RICH_VERBATIM',
				'parameters': {
					'type': 'CALL',
					'verbatimTypes': [
						'verbatim_type_for_agent',
						'verbatim_type_for_client',
						'verbatim_type_for_bot'
					],
					'language': 'en'
				}
			},
			{
				'name': 'NATURAL_ID',
				'type': 'TEXT',
				'map': 'ID1'
			}
		],
		'records': [{
			'NATURAL_ID': f"Audio;{id}",
			'cool_rich_verbatim': json.dumps(json_data)
		}]
	}

def main(text_csv, type_csv, output_file, seed = 42):

	random.seed(seed)
	randomOffset = random.randint(0, 100)

	conversation_data = read_csv(text_csv)
	participants_data = read_csv(type_csv)
	merged_data = merge_data(conversation_data, participants_data)
		
	audio_pieces = generate_audio_pieces(merged_data, randomOffset)
	delays = [float(row['delay']) if row.get('delay') is not None and row['delay'].strip() != '' else None for row in merged_data]
		
	result_audio, start_end_times = merge_audio_with_delays(audio_pieces, delays)
		
	result_audio.export(f"{output_file}.mp3", format="mp3")
		
	for i, row in enumerate(merged_data):
		row['start'] = int(start_end_times[i]['start'])
		row['end'] = int(start_end_times[i]['end'])
		row.pop('delay', None)
	json_data = convert_to_json(participants_data, merged_data, output_file)
	payload = convert_to_payload(json_data, output_file)
	with open(f"{output_file}.json", 'w') as json_file:
		json.dump(payload, json_file, indent=4)

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Generate audio and merge datasets.")
	parser.add_argument("base_name", help="Base name for all files: <base_name>.csv ('name', 'text', 'delay'), <base_name>_participants.csv ('name', 'type', 'gender'), output: <base_name>.json/mp3")
	parser.add_argument("seed", help="Random seed.")
	args = parser.parse_args()
		
	text_csv = f"{args.base_name}.csv"
	type_csv = f"{args.base_name}_participants.csv"
	output_file = args.base_name
	main(text_csv, type_csv, output_file, args.seed)
