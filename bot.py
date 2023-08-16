from dependencies import *

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN").strip()
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN").strip()

app = App(token=SLACK_BOT_TOKEN)

global dataframes, csv
csv = None
dataframes = {}

template = """You will be given questions about tabular data in Pandas dataframes, stored in a dictionary called 'dataframes' with each key corresponding to the name of a dataframe and the value being the dataframe itself. Generate Python code to be executed on the requested dataframe to answer these questions in a print statement. If printing a dataframe, first put it in csv format. If you need more information, ask questions about the dataframes to gain more context before generating code. Use markdown to notate all generated code blocks.

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
def bot_prompt(ack: Ack, respond : Respond, command : dict, client: WebClient):
    global csv, dataframes
    ack()
    channel_id = command["channel_id"]
    last_message = client.conversations_history(channel=command["channel_id"])["messages"][0]
    if ("files" not in last_message or len(last_message["files"])==0):
        client.chat_postMessage(text="No file upload in last message", channel=channel_id)
        return

    try:
        import pdb
        pdb.set_trace()
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
        
        res = requests.get(url, headers={'Authorization': 'Bearer %s' % SLACK_BOT_TOKEN})
        
        res.raise_for_status()
        csv = res.content

        lines = res.text.split("\n")
        
        sample_lines = len(lines) if len(lines)<4 else 4
        
        sample_data = lines[:sample_lines]        
        filename = name.split(".")[0]

        processing_res = client.chat_postMessage(text="Reading csv file...", channel=channel_id)
        df = pd.read_csv(BytesIO(csv)) 

        dataframes[filename] = df

        client.chat_update(text="Processing sample data...", channel=channel_id, ts=processing_res["ts"])
        chain.predict(input=f"Here is the sample data for the dataframe called {filename}:\n {sample_data}")

        client.chat_update(text=f"Successfully processed CSV file {name}", channel=channel_id, ts=processing_res["ts"])

    except:
        respond("Error reading CSV file")

@app.command("/say")
def bot_prompt(ack: Ack, respond : Respond, command: dict, client: WebClient):
    global output
    ack()

    if csv == None:
        client.chat_postMessage(text="Please set a csv file.", channel=command["channel_id"])

    res = client.chat_postMessage(text="Processing your input...", channel=command["channel_id"])

    prompt = command["text"]
    output = chain.predict(input=prompt)
    

    
    client.chat_update(text=f"Finished processing: \n{prompt}", channel=command["channel_id"], ts=res["ts"])

    client.chat_postMessage(text=f"{output}", channel=command["channel_id"]) 

@app.command("/clear")
def bot_prompt(ack: Ack, respond: Respond, command:dict, client: WebClient):
    ack()
    memory.clear()
    csv = None
    df = pd.DataFrame()
    client.chat_postMessage(text="Memory and csv cleared", channel=command["channel_id"])

@app.command("/run")
def bot_prompt(ack: Ack, respond : Respond, command:dict, client : WebClient):

    global output
    ack()

    channel_id = command["channel_id"]
    if len(dataframes) == 0:
        client.chat_postMessage(text="No files uploaded yet", channel=channel_id)
        return

    split = output.split('```python')
    if len(split) <= 1:
        client.chat_postMessage(text=f"No python code generated", channel=channel_id)
        return 
    output_aftercode = split[1]
    output_code = output_aftercode.split('```')[0]

    tmp = sys.stdout
    output = StringIO()
    sys.stdout = output

    try:
        exec(output_code)
    except Exception as error:
        client.chat_postMessage(
                text=f"There was an error running the code: \n {type(error).__name__}", channel=channel_id)
        return
    sys.stdout = tmp
    


    filename = command["text"].strip()
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



