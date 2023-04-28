import openai
import os
from pathlib import Path
from dotenv import load_dotenv

envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)

# setup the openapi auth
openai.api_key = os.environ['OPENAI_KEY']
abpath = Path('training_data.jsonl').absolute()

resp = openai.FineTune.create(
    n_epochs=20,
    batch_size=100,
    training_file=os.path.abspath(abpath)
)

job_id = resp['id']
print(f"fine tuning job created with ID: {job_id}")
