import pandas as pd
import random
from datetime import datetime, timedelta

# Function to generate a random date within a specified range
def random_date(start_date, end_date):
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date

# Define the date range
start_date = datetime(2023, 6, 1)
end_date = datetime(2023, 9, 25)

# Read the CSV file
input_file = 'C:/Projects/datasets/recent/redmi6.csv'
df = pd.read_csv(input_file, encoding='utf-8')

# Add a new column with random dates
df['Date'] = [random_date(start_date, end_date) for _ in range(len(df))]

# Specify the output file
output_file = 'C:/Projects/datasets/recent/redmi6_1.csv'

# Write the modified DataFrame to a different CSV file
df.to_csv(output_file, index=False, encoding='utf-8')

print(f"Random dates added and saved to '{output_file}'.")