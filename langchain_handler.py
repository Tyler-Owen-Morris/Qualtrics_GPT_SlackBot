import os
import sys

from pathlib import Path
from dotenv import load_dotenv
from langchain.document_loaders import TextLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.agents import initialize_agent, AgentType
from langchain.tools import FileSearchTool

from langchain.utilities import SerpAPIWrapper


envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
os.environ['OPENAI_API_KEY'] = os.environ['OPENAI_KEY']

# Load and setup the document data provider
# text_file_path = "output.txt" # initial load of data - somewhat functional.
# full corpus of website text by URL
text_file_path = "data/large-text-loader2.txt"
loader = TextLoader(file_path='output.txt', encoding='utf8')
index = VectorstoreIndexCreator().from_loaders([loader])

# Load Conversational model
# search = SerpAPIWrapper()
# tools = [Tool(
#     name="CurrentSearch",
#     func=search.run,
#     description="this is the talking tool object"
# )]
tools = [FileSearchTool(name="CurrentSearch", description="my description")]
memory = ConversationBufferMemory(
    memory_key="chat_history", return_messages=True)
llm = ChatOpenAI(openai_api_key=os.environ['OPENAI_KEY'], temperature=0)
agent_chain = initialize_agent(
    tools=tools, llm=llm, agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION, verbose=True, memory=memory)


def query_langchain(query):
    return agent_chain.run(input=query)

# def query_langchain(query):
#     return index.query(query)
