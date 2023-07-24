from dependencies import *

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN").strip()
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN").strip()

app = AsyncApp(token=SLACK_BOT_TOKEN)

# format data into a table (string)
csv_file_path = "IRIS.csv"
df = pd.read_csv(csv_file_path)
csv = open(csv_file_path, "r").read()
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
    return chat

def query_chat_model(chat, query):
    messages = [
            SystemMessage(content=
                f"Answer questions about the following data: {csv}"),
            HumanMessage(content=query)]
    return chat(messages).content

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
model = create_chat_model()
chain = ConversationChain(
        prompt=PROMPT,
        llm=model, 
        verbose=True, 
        memory=ConversationBufferMemory())

user_input = input()
output = ""

while user_input != "exit":
    #messages.append(HumanMessage(content=user_input))
    #print(query_python_model(model, messages).content)
    
    if (user_input == "run"):
        output_aftercode = output.split('```python')[1]

        output_code = output_aftercode.split('```')[0]
            
        run = input(f"Run code: \n{output_code}\n? ")
        if (run=="y"):
            exec(output_code)

    else:
        output = chain.predict(input=user_input)

        print(output)
    print("Awaiting input: ")
    user_input = input()


####
# SLACKBOT APP
####

agent = create_pandas_agent() 
chat = create_chat_model()
qa = create_retrievalqa(csv_file_path)

@app.command("/chatprompt")
async def bot_prompt(ack: Ack, respond: Respond, command: dict, client: AsyncWebClient):
    await ack()
    prompt = command["text"]
    result = query_chat_model(chat, prompt)
    await respond(f"You asked: {prompt} \n\n You received: {result}")
    

@app.command("/agentprompt")
async def bot_prompt(ack: Ack, respond: Respond, command: dict, client: AsyncWebClient):
    await ack()
    prompt = command["text"]
    result = agent.run(prompt)

    await respond(f"You asked: {prompt} \n\n You received: {result}")
    

@app.command("/retrievalqaprompt")
async def bot_prompt(ack: Ack, respond: Respond, command: dict, client: AsyncWebClient):
    await ack()
    prompt = command["text"]
    result = qa.run(prompt)

    await respond(f"You asked: {prompt} \n\n You received: {result}")


async def main():
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN) 
    try:
        await handler.start_async()
    except:
        await handler.disconnect_async()
        await handler.close_async()

asyncio.run(main())


