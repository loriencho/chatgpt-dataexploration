from dependencies import *

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN").strip()
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN").strip()
    
app = App(token=SLACK_BOT_TOKEN)

# format data into a table (string)
csv_file_path = "IRIS.csv"
df = pd.read_csv(csv_file_path)
table = tabulate(df, headers='keys', tablefmt='psql')


def create_pandas_agent():
    llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613")
    return create_pandas_dataframe_agent(llm, df, verbose=False, 
            agent_type=AgentType.OPENAI_FUNCTIONS)

def create_chat_model():
    """
        Sends context (the data) to ChatGPT
        Currently does not work because of token limit
    """

    chat = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613")
    memory = ConversationBufferMemory()
    
    memory.save_context(
            {"input":table}, {"output":chat.predict(table)})
    
    conversation = ConversationChain(
            llm=chat, verbose=False, memory=memory) 
    return conversation

def create_retrievalqa(csv_file_path):
    """
        Uses the RetrievalQA chain for a chunking based approach
    """
    documents = CSVLoader(csv_file_path).load()
    text_splitter = CharacterTextSplitter(
           chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)
    docsearch = Chroma.from_documents(texts, OpenAIEmbeddings())

    llm = ChatOpenAI(temperature = 0, model="gpt-3.5-turbo-0613")

    qa = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff", 
            retriever=docsearch.as_retriever())
    return qa

####
# SLACKBOT APP
####

agent = create_pandas_agent() 
# conversation = create_chat_model() hits token limit
qa = create_retrievalqa(csv_file_path)

@app.command("/chatprompt")
def bot_prompt(ack: Ack, respond: Respond, command: dict, client: WebClient):
    ack()
    prompt = command["text"]
    respond(f"You asked: {prompt} \n\n You received: not working yet")

@app.command("/agentprompt")
def bot_prompt(ack: Ack, respond: Respond, command: dict, client: WebClient):
    ack()
    prompt = command["text"]
    result = agent.run(prompt)

    respond(f"You asked: {prompt} \n\n You received: {result}")

@app.command("/retrievalqaprompt")
def bot_prompt(ack: Ack, respond: Respond, command: dict, client: WebClient):
    ack()
    prompt = command["text"]
    result = qa.run(prompt)

    respond(f"You asked: {prompt} \n\n You received: {result}")

if __name__ == "__main__":
    
    SocketModeHandler(app, SLACK_APP_TOKEN).start()


