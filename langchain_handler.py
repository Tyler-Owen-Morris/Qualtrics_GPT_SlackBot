import os
import sys

from pathlib import Path
from dotenv import load_dotenv
from langchain.document_loaders import TextLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI

envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)

os.environ['OPENAI_API_KEY'] = os.environ['OPENAI_KEY']


def query_langchain(query):
    loader = TextLoader(file_path='output.txt', encoding='utf8')
    index = VectorstoreIndexCreator().from_loaders([loader])
    return index.query(query)
