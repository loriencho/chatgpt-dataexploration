from dependencies import *

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN").strip()
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN").strip()

app = App(token=SLACK_BOT_TOKEN)

global dataframes, output
dataframes = {}

template = """Answer questions about data in Pandas dataframes stored in a dictionary called 'dataframes' with each key corresponding to the name of a dataframe and the value being the dataframe itself. Generate Python code to be executed on the requested dataframe(s) to answer these questions in a print statement. If printing a dataframe, first put it in csv format. Use markdown to notate all generated code blocks.

Current conversation:
{history}

Human: {input}
AI:"""

memory = ConversationBufferWindowMemory(k=4)
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
        client.chat_postMessage(text="No file upload in last message", channel=channel_id)
        return

    try:
        
        # Find file(s) from last message sent
        name = command["text"].strip()
        files = last_message["files"]
        uploaded = None
        for i in range(len(files)):
            if (files[i]["title"] == name):
                uploaded = files[i]
        if uploaded == None:
            respond("File {name} not found")
            return
        url = uploaded["url_private"]
        
        # Get csv files
        processing_res = client.chat_postMessage(text="Downloading csv files...", channel=channel_id)
        res = requests.get(url, headers={'Authorization': 'Bearer %s' % SLACK_BOT_TOKEN})
        res.raise_for_status()
        csv = res.content     
        
        # Add to dataframes dictionary
        filename = name.split(".")[0]
        processing_res = client.chat_postMessage(text="Reading csv file...", channel=channel_id)
        df = pd.read_csv(BytesIO(csv)) 
        dataframes[filename] = df
        
        # Feed sample data
        client.chat_update(text="Processing sample data...", channel=channel_id, ts=processing_res["ts"])
        lines = res.text.split("\n")
        sample_lines = len(lines) if len(lines)<4 else 4
        sample_data = lines[:sample_lines]       
        chain.predict(input=f"Sample data for the {filename} dataframe:\n {sample_data}")
        client.chat_update(text=f"Successfully processed CSV file {name}", channel=channel_id, ts=processing_res["ts"])

    except:
        respond("Error reading CSV file")

@app.command("/say")
def bot_input(ack: Ack, respond : Respond, command: dict, client: WebClient):
    global output
    ack()

    if csv == None:
        client.chat_postMessage(text="Please set a csv file.", channel=command["channel_id"])

    # Send user input to ChatGPT
    res = client.chat_postMessage(text="Processing your input...", channel=command["channel_id"])
    prompt = command["text"]
    output = chain.predict(input=prompt)
    client.chat_update(text=f"Finished processing: \n{prompt}", channel=command["channel_id"], ts=res["ts"])
    client.chat_postMessage(text=f"{output}", channel=command["channel_id"]) 

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
        client.chat_postMessage(text=f"No python code generated", channel=channel_id)
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
                text=f"There was an error running the code: \n {type(error).__name__}", channel=channel_id)
        return

    # Feed output to ChatGPT
    chain.save_context({"input":f"I ran the code. Output: \"{output.getvalue()}\"", "output":"Got it."})
    
    # Send results file to user.
    filename = command["text"].strip() # check if user provided a filename
    if filename == "":
        filename = "results.txt"
    processing_res = client.chat_postMessage(text="Uploading output file...", channel=channel_id)
    res = client.files_upload(
        filename=filename,
        content=output.getvalue(),
        channels=channel_id)
    client.chat_update(text="Output file sent.", channel=channel_id, ts=processing_res["ts"])
    
def main():
    handler = SocketModeHandler(app, SLACK_APP_TOKEN).start()



main()



