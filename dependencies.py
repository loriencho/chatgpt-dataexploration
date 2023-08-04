import os
import sys
from tabulate import tabulate
import asyncio
import datetime
import time 
from io import BytesIO, StringIO
import requests
from langchain.docstore.document import Document
####
# Slackbot Imports
####
import slack_sdk as slack
from slack_sdk import WebClient
from slack_sdk.web.async_client import AsyncWebClient

from slack_bolt import App, Ack, Respond
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

####
# LangChain Imports
####
from langchain import OpenAI

# Use PandasDataframeAgent
import pandas as pd
from pandas import DataFrame
from langchain.agents import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType

# Use ChatGPT conversationally with context (data)
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import(
        AIMessage,
        HumanMessage,
        SystemMessage)

# Use RetrievalQA Chain with chunking
from langchain.chains import RetrievalQA
from langchain.document_loaders import CSVLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma

