from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import requests

envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
q_api_token = os.environ['QUALTRICS_API_TOKEN']
survey_id = os.environ['QUALTRICS_LOG_SURVEY_ID']


def write_response_to_survey(bot_id, user_question, bot_response):
    try:

        headers = {
            'X-API-TOKEN': q_api_token,
            'Content-Type': 'application/json',
        }
        payload = {
            "values": {
                "distributionChannel": "api",
                "duration": 99,
                "endDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "finished": 1,
                "locationLatitude": "37.5558935160669",
                "locationLongitude": "-122.26054014925835",
                "progress": 100,
                "startDate": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "userLanguage": "EN"
            }}
        data = {bot_id: bot_id, user_question: user_question,
                bot_response: bot_response}
        response = requests.post(
            f'https://yul1.qualtrics.com/API/v3/surveys/{survey_id}/responses',
            json=payload,
            headers=headers
        )
        print("response from qapi", response.json())
        print(response.json()['meta']['httpStatus'])
        if (response.json()['result']['responseId'] != None):
            rid = response.json()['result']['responseId']
            print(rid)
            update_payload = {
                "surveyId": survey_id,
                "resetRecordedDate": False,
                "embeddedData": {
                    "bot_id": bot_id,
                    "user_question": user_question,
                    "bot_response": bot_response
                }
            }
            update_response = requests.put(
                f'https://yul1.qualtrics.com/API/v3/responses/{rid}', json=update_payload, headers=headers)
            print("update response:", update_response.json())
            return update_response.json()
        return response.json()
    except:
        print("record did not write: botid-", bot_id, " | user_question-",
              user_question, " | bot_response-", bot_response)
