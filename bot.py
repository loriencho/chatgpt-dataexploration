from dependencies import *

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN").strip()
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN").strip()

app = App(token=SLACK_BOT_TOKEN)

global dataframes, output
dataframes = {}

template = """Answer questions about Pandas dataframes (previously read from csv files) stored in a dictionary called dataframes. Sample data will be provided for each dataframe as well as information on its dictionary key. Generate Python code to be executed on the requested dataframe(s) to answer these questions in a print statement. Print in csv format for all tabular data, especially dataframes. Use markdown to notate all generated code blocks. Be as concise as possible in responses.
The user will sometimes provide sample data for a dataframe or code output to you. You do not need to generate code- just give a short acknowledgment.

Current conversation:
{history}

Human: {input}
AI:"""

memory = ConversationBufferMemory()
PROMPT = PromptTemplate(input_variables=["history", "input"], template=template)
model = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613")
chain = ConversationChain(
        prompt=PROMPT,
        llm=model, 
        verbose=True, 
        memory=memory)

####
# SLACKBOT APP
####

global output
output = ""
@app.command("/csv")
def upload_csv(ack: Ack, respond : Respond, command : dict, client: WebClient):
    global dataframes
    ack()
    channel_id = command["channel_id"]
    last_message = client.conversations_history(channel=command["channel_id"])["messages"][0]
    
    if ("files" not in last_message or len(last_message["files"])==0):
        respond("No file upload in last message")
        return

    try:
        
        # Find file(s) from last message sent
        names = command["text"].strip().split(",")
        files = last_message["files"]

        for name in names:
            name = name.strip()
            filename = name.split(".")[0]
    
            uploaded = None
            for i in range(len(files)):
                if (files[i]["title"] == name):
                    uploaded = files[i]
            if uploaded == None:
                respond(f"File {name} not found")
                continue
            if filename in dataframes:
                client.chat_postMessage(text=f"File {filename} already exists and will not be downloaded.", channel=channel_id)
                continue
            url = uploaded["url_private"]
        
            # Get csv files
            processing_res = client.chat_postMessage(text=f"Downloading csv file {name}...", channel=channel_id)
            res = requests.get(url, headers={'Authorization': 'Bearer %s' % SLACK_BOT_TOKEN})
            res.raise_for_status()
            csv = res.content     
        
            # Add to dataframes dictionary
            processing_res = client.chat_update(text=f"Reading csv file {name}...", channel=channel_id, ts=processing_res["ts"])
            df = pd.read_csv(BytesIO(csv)) 
            dataframes[filename] = df
        
            # Feed sample data
            client.chat_update(text=f"Processing sample data for {name}...", channel=channel_id, ts=processing_res["ts"])
            lines = res.text.split("\n")
            sample_lines = len(lines) if len(lines)<3 else 3
            sample_data = lines[:sample_lines]       

            try:
                with get_openai_callback() as cb:
                    chain.predict(input=f"Sample data for the \"{filename}\" dataframe stored in dataframes[\"{filename}\"]:\n {sample_data}")
                    client.chat_update(text=f"Successfully processed CSV file {name}. Current token usage: {cb.total_tokens}", channel=channel_id, ts=processing_res["ts"])

            except Exception as error:
                client.chat_update(text=f"An error occurred when giving {filename} sample data to ChatGPT: {type(error).__name__}- {error}", channel=channel_id, ts=processing_res["ts"])

    except Exception as error:
        respond(f"Error reading CSV file- {type(error).__name__} - {error}")

@app.command("/say")
def bot_input(ack: Ack, respond : Respond, command: dict, client: WebClient):
    global output
    ack()

    channel_id = command["channel_id"]

    if len(dataframes) == 0:
        respond("Please set a csv file.")

    # Send user input to ChatGPT
    res = client.chat_postMessage(text="Processing your input...", channel=channel_id)
    prompt = command["text"]

    try:
        with get_openai_callback() as cb:
            output = chain.predict(input=prompt)
            client.chat_update(text=f"Finished processing: \n{prompt}.", channel=channel_id, ts=res["ts"])
            client.chat_postMessage(text=f"{output}\nCurrent tokens: {cb.total_tokens}", channel=channel_id) 

    except Exception as error:
        client.chat_postMessage(text=f"An error occurred when sending your input to ChatGPT: {type(error).__name__}: {error}", channel=channel_id)
        

@app.command("/clear")
def clear(ack: Ack, respond: Respond, command:dict, client: WebClient):
    ack()

    # Clear memory and dataframes
    memory.clear()
    csv = None
    df = pd.DataFrame()
    client.chat_postMessage(text="Model memory and csv files cleared", channel=command["channel_id"])
 
@app.command("/system")
def get_system_info(ack: Ack, respond : Respond, command:dict, client: WebClient):
   ack()

   # Get system details (CPU, RAM)
   channel_id = command["channel_id"]
   processing_res = client.chat_postMessage(text="Getting system details...", channel=channel_id)

   message = f"""CPU Usage: {psutil.cpu_percent(4)}%
RAM Usage (percent): {psutil.virtual_memory()[2]}%
RAM Usage (GBs): {psutil.virtual_memory()[3]/1000000000}
   """
   client.chat_update(text=message, channel=channel_id, ts=processing_res["ts"])
    
@app.command("/run")
def run_code_output(ack: Ack, respond : Respond, command:dict, client : WebClient):
    global output
    ack()
    channel_id = command["channel_id"]

    # Check if files have been uploaded
    if len(dataframes) == 0:
        client.chat_postMessage(text="No files uploaded yet", channel=channel_id)
        return

    # Get code from the last message
    split = output.split('```python')
    if len(split) <= 1:
        respond("No python code generated.")
        return 
    output_aftercode = split[1]
    output_code = output_aftercode.split('```')[0]

    # Set output to be captured in string
    tmp = sys.stdout
    output = StringIO()
    sys.stdout = output

    # Try running code
    try:
        exec(output_code)
        sys.stdout = tmp
    except Exception as error:
        sys.stdout = tmp
        client.chat_postMessage(
                text=f"There was an error running the code: \n {type(error).__name__}: {error}", channel=channel_id)
        return
    
    # Feed output to ChatGPT
    output = output.getvalue()
    orig_output = output
    output_lines = output.split("\n")

    if len(output_lines) > 3:
        respond("Output was too long to send completely, and a sample was sent to ChatGPT.")
        tmp = "I ran the code, here's a sample of the code output: "
        for i in range(3):
            tmp += output_lines[i]
        output = tmp
    else:
        output = f"I ran the code, here's the output: {output}"
    try:
        with get_openai_callback() as cb:
            chain.predict(input=output)
            respond(f"Sent output, total tokens are {cb.total_tokens}")
    except Exception as error:
        client.chat_postMessage(text=f"There was an error sending the output to ChatGPT: {type(error).__name__} - {error}", channel=channel_id)
        
    # Send results file to user.
    filename = command["text"].strip() # check if user provided a filename
    if filename == "":
        filename = "results.txt"

    if len(orig_output)!=0:
        processing_res = client.chat_postMessage(text="Uploading output file...", channel=channel_id)
        res = client.files_upload(
            filename=filename,
            title=filename,
            content=orig_output,
            channels=channel_id)
        client.chat_update(text="Output file sent.", channel=channel_id, ts=processing_res["ts"])
    else:
        respond("No output from code.")
def main():
    handler = SocketModeHandler(app, SLACK_APP_TOKEN).start()



main()



