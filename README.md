# chatgpt-dataexploration

This Slack bot allows a user to communicate with ChatGPT to gather information and make conclusions on given data. 
CSVs are uploaded into a workspace channel, and then by using the /csv command, the bot converts them into pandas DataFrames. 
Using /say, the user inquires ChatGPT for data conclusions that it has been primed to find by generating Python code. 
When a user triggers the /run command, the ChatGPT generated code is run on the relevant DataFrames. 
Output is sent to the user in Slack, thus answering their query.
