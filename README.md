# Chat GPT Data Exploration Slackbot
Upload and set csv files, say things to ChatGPT, and run code. Clear memory and/or uploaded csvs  and check system info if neccessary

## Uploading CSV Files
Upload files to the desired Slack
Use the /csv (file_title), (file_title2).... command to download files to the bot
The /csv command only searches the previous message for files.
All file titles should be comma separated.
Use file titles, not file names. This appears next to the arrow and is often the entire filename, but not always.
Example: /csv netflix_titles (1).csv, results

## Talking with ChatGPT
Sends all following text after /say to ChatGPT for a messaged response.
Tip: Specify which csv file(s) you want to use in each question.
Each csv file is stored as a Pandas dataframe in a dictionary by their title. i.e., art.csv in dataframes[“art”] . Sometimes ChatGPT does not generate code to match this and needs to be reminded of the dictionary.

## Running Generated Code
The /run command will parse the most recent output for Python code and attempt a run.
The output is parsed to find Python in the markdown format. The model has been instructed to write it this way, 
but may need correction.

/run (filename) will write out the output to the file (filename), but otherwise to results.txt
Outputs can be further analyzed through /csv (file_title). If a file with the same title has already been used, then this will not work. 
Outputs are sent to ChatGPT with a max of 2 lines as a snippet.

## Clearing Memory and Downloaded Files
/clear causes all model memory to be cleared along with all downloaded files. 
Important for token limit!

## System Info
/system will send the CPU usage (%), RAM usage (%, GBs) after 4 seconds.

## Setup:
Requires environment variables:
OPENAI_API_KEY, 
SLACK_APP_TOKEN, 
SLACK_BOT_TOKEN

dependencies.py, requirements.txt in github repository

—----
How I run it from the dataexploration directory:
source .venv/bin/activate 
python bot.py

