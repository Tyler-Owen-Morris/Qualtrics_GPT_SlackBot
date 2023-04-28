import openai
import os
from pathlib import Path
from dotenv import load_dotenv
from time import sleep

envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)

# setup the openapi auth
openai.api_key = os.environ['OPENAI_KEY']
abpath = Path('training_data.jsonl').absolute()

# upld = openai.File.create(
#     file=open("training_data.jsonl", 'rb'),
#     purpose="fine-tune"
# )

# print(upld)
# myid = upld['id']
# print("myid:", myid)

# resp = openai.FineTune.create(training_file=myid)

# print(resp)
# job_id = resp['id']
# print(f"fine tuning job created with ID: {job_id}")

job_id = "ft-vxLGQcDdSQBEAUC0kw0Gjhuf"
finished = False
while not finished:
    mdl = openai.FineTune.retrieve(id=job_id)

    print(mdl)
    print("model:", mdl['fine_tuned_model'])
    if not mdl['fine_tuned_model'] == None:
        finished = True
    sleep(5)
