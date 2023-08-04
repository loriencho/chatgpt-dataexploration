from dependencies import *

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN").strip()
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN").strip()

app = App(token=SLACK_BOT_TOKEN)

global df, csv
csv = None
df = pd.DataFrame()

template = """You will be given questions about tabular data in a Pandas dataframe. Generate Python code to be executed on the dataframe, called 'df', to eventually answer these questions in a print statement. If you do not know how or need more information, ask questions about the dataframe to gain more context before generating code in order to increase accuracy. Use markdown to notate all generated code blocks.

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
    global csv, df
    ack()
    
    last_message = client.conversations_history(channel=command["channel_id"])["messages"][0]
    if ("files" not in last_message or len(last_message["files"])==0):
        respond("No file upload in last message")
        return

    try:
        name = command["text"]
        files = last_message["files"]
        uploaded = None
        for i in range(len(files)):
            if (files[i]["name"] == name):
                uploaded = files[i]
        
        if uploaded == None:
            respond(f"File {name} not found")
            return
                
        url = uploaded["url_private"]
        res = requests.get(url, headers={'Authorization': 'Bearer %s' % SLACK_BOT_TOKEN})
        
        res.raise_for_status()
        csv = res.content

        df = pd.read_csv(BytesIO(csv))  
        respond(f"Successfully read CSV file {name}")

        memory.clear()
    except:
        respond(f"Error reading CSV file")

@app.command("/say")
def bot_prompt(ack: Ack, respond : Respond, command: dict, client: WebClient):
    global output
    ack()

    if csv == None:
        respond("Please set a csv file.")

    prompt = command["text"]
    output = chain.predict(input=prompt)

    respond(f"You said: {prompt}\n Response: {output}") 

@app.command("/clear")
def bot_prompt(ack: Ack, respond: Respond, command:dict, client: WebClient):
    ack()
    memory.clear()
    csv = None
    df = pd.DataFrame()
    respond("Memory and csv cleared")

@app.command("/run")
def bot_prompt(ack: Ack, respond : Respond, command:dict, client : WebClient):
    global output, df
    ack()
    
    if df.empty:
        respond("No file uploaded yet")
        return

    split = output.split('```python')
    if len(split) <= 1:
        respond(f"No python code generated")
        return 
    output_aftercode = split[1]
    output_code = output_aftercode.split('```')[0]

    tmp = sys.stdout
    output = StringIO()
    sys.stdout = output

    try:
        exec(output_code)
    except Exception as error:
        respond(f"There was an error running the code: \n {type(error).__name__}")
        return
    sys.stdout = tmp
    
    respond(f"Output: \n{output.getvalue()}")


def main():
    handler = SocketModeHandler(app, SLACK_APP_TOKEN).start()



main()
