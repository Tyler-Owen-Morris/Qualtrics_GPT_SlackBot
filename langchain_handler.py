import os
import sys

from pathlib import Path
from dotenv import load_dotenv
from langchain.document_loaders import TextLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.llms import OpenAI
# from langchain.memory import ConversationBufferMemory
# from langchain.chat_models import ChatOpenAI


envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
os.environ['OPENAI_API_KEY'] = os.environ['OPENAI_KEY']

# memory = ConversationBufferMemory(
#     memory_key="chat_history", return_messages=True)
# llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, temperature=0)
# agent_chain = initialize_agent(
#     tools, llm, agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION, verbose=True, memory=memory)
# Load and setup the langchain data provider
# text_file_path = "output.txt" # initial load of data - somewhat functional.
text_file_path = "data/large-text-loader2.txt"
loader = TextLoader(file_path='output.txt', encoding='utf8')
index = VectorstoreIndexCreator().from_loaders([loader])


def query_langchain(query):
    return index.query(query)
