from dependencies import *

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN").strip()
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN").strip()

app = App(token=SLACK_BOT_TOKEN)

# format data into a table (string)

global df, csv
csv = None
df = pd.DataFrame()

def create_pandas_agent(df):

    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613")
    return create_pandas_dataframe_agent(llm, df, verbose=True)

def query_chat_model(chat, query):
    messages = [
            SystemMessage(content=
                f"Answer questions about the following data: {csv}"),
            HumanMessage(content=query)]
    return chat(messages).content

"""
def create_retrievalqa(csv):
    
    #    Uses the RetrievalQA chain for a chunking based approach
    

    text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=0)
    texts = text_splitter.split_text(csv)
    documents = text_splitter.create_documents(texts)
    docsearch = Chroma.from_documents(documents, OpenAIEmbeddings())

    llm = ChatOpenAI(temperature = 0, model="gpt-3.5-turbo-0613")

    qa = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff",
            reduce_k_below_max_tokens=True,
            retriever=docsearch.as_retriever())


    return qa
"""

def query_python_model(model, messages):
    if (len(messages) == 0):
        return
    else:
        response = model(messages)
        messages.append(response)
        return response

template = """You will be given questions about tabular data in a Pandas dataframe. Generate Python code to be executed on the dataframe, called 'df', to eventually answer these questions in a print statement. If you do not know how or need more information, ask questions about the dataframe to gain more context before generating code in order to increase accuracy. Use markdown to notate all generated code blocks.

Current conversation:
{history}

Human: {input}
AI:"""

PROMPT = PromptTemplate(input_variables=["history", "input"], template=template)
model = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613")
chain = ConversationChain(
        prompt=PROMPT,
        llm=model, 
        verbose=True, 
        memory=ConversationBufferMemory())

####
# SLACKBOT APP
####

global agent, chat, qa
agent = None 
chat = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613")
qa = None

global output
output = ""


@app.command("/csv")
def bot_prompt(ack: Ack, respond : Respond, command : dict, client: WebClient):
    global csv, df, agent, qa
    ack()
    
    last_message = client.conversations_history(channel=command["channel_id"])["messages"][0]

    if ("files" not in last_message or len(last_message["files"])==0):
        respond("No file upload in last message")
        return
    

    try:
        uploaded =  last_message["files"][0]
        url = uploaded["url_private"]
        name = uploaded["name"]
        res = requests.get(url, headers={'Authorization': 'Bearer %s' % SLACK_BOT_TOKEN})
        
        
        res.raise_for_status()
        csv = res.content

        df = pd.read_csv(BytesIO(csv))
        agent = create_pandas_agent(df)
       #  qa = create_retrievalqa(res.text)
    
        respond(f"Successfully read CSV file {name}")
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

    respond(output) 

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
            
    from io import StringIO
    import sys

    tmp = sys.stdout
    output = StringIO()
    sys.stdout = output
    try:
        exec(output_code)
    except:
        respond("There was an error running the code.")
    sys.stdout = tmp
    
    respond(f"Output: \n{output.getvalue()}")

@app.command("/chatprompt")
def bot_prompt(ack: Ack, respond: Respond, command: dict, client: WebClient):
    ack()

    if csv != None:
        prompt = command["text"]
        result = query_chat_model(chat, prompt)
        respond(f"You asked: {prompt} \n\n You received: {result}")
    else:
        respond("Please set a csv file.")

@app.command("/agentprompt")
def bot_prompt(ack: Ack, respond: Respond, command: dict, client: WebClient):
    ack()

    
    if agent:
        prompt = command["text"]
        result = agent.run(prompt)


        respond(f"You asked: {prompt} \n\n You received: {result}")
    else:
        respond("Please set a csv file.")
"""
@app.command("/retrievalqaprompt")
def bot_prompt(ack: Ack, respond: Respond, command: dict, client: WebClient):
    ack()

    if qa:
        prompt = command["text"]
        result = qa.run(prompt)

        respond(f"You asked: {prompt} \n\n You received: {result}")
    else:
        respond("Please set a csv file.")
"""

def main():
    handler = SocketModeHandler(app, SLACK_APP_TOKEN).start()



main()
