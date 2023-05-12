import requests
from bs4 import BeautifulSoup
import openai
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from time import sleep

envpath = Path('.') / '.env'
load_dotenv(dotenv_path=envpath)
openai.api_key = os.environ['OPENAI_KEY']

inpts = [('info for survey takers', 'https://www.qualtrics.com/support/survey-platform/information-survey-takers/'),
         ('projects overview',
          'https://www.qualtrics.com/support/survey-platform/my-projects/my-projects-overview/'),
         ('survey basics', 'https://www.qualtrics.com/support/survey-platform/survey-module/survey-module-overview/'),
         ('workflow setup', 'https://www.qualtrics.com/support/survey-platform/actions-module/setting-up-actions/'),
         ('survey response workflow event',
          'https://www.qualtrics.com/support/survey-platform/actions-module/survey-response-events/'),
         ('global workflows', 'https://www.qualtrics.com/support/survey-platform/actions-page/actions-in-global-navigation/'),
         ('ticket event', 'https://www.qualtrics.com/support/survey-platform/actions-module/ticket-events/'),
         ('survey definition event',
          'https://www.qualtrics.com/support/survey-platform/actions-page/survey-definition-events/'),
         ('servicenow event', 'https://www.qualtrics.com/support/survey-platform/actions-page/servicenow-events/'),
         ('json event', 'https://www.qualtrics.com/support/survey-platform/actions-module/json-events/'),
         ('salesforce workflow rule event',
          'https://www.qualtrics.com/support/survey-platform/actions-module/salesforce-workflow-rule-event/'),
         ('XM directory funnel event',
          'https://www.qualtrics.com/support/survey-platform/actions-page/xm-directory-funnel-event/'),
         ('experience ID segments event',
          'https://www.qualtrics.com/support/survey-platform/actions-page/events/experience-id-segments-events/'),
         ('data set record event',
          'https://www.qualtrics.com/support/survey-platform/actions-page/events/dataset-record-events/'),
         ('experience id change event',
          'https://www.qualtrics.com/support/survey-platform/actions-page/events/experience-id-change-event/'),
         ('ticket task', 'https://www.qualtrics.com/support/survey-platform/actions-module/ticketing/tickets-task/'),
         ('update ticket task', 'https://www.qualtrics.com/support/survey-platform/actions-module/ticketing/update-ticket-task/'),
         ('email task', 'https://www.qualtrics.com/support/survey-platform/actions-module/email-task/'),
         ('xm directory task',
          'https://www.qualtrics.com/support/survey-platform/actions-module/xm-directory-task/'),
         ('notifications feed task',
          'https://www.qualtrics.com/support/survey-platform/actions-module/notifications-feed-task/'),
         ('single instance incentives',
          'https://www.qualtrics.com/support/survey-platform/actions-module/single-instance-incentives/'),
         ('code task', 'https://www.qualtrics.com/support/survey-platform/actions-module/code-task/'),
         ('extract data from qualtrics file service',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-extractor-tasks/extract-data-from-qualtrics-file-service-task/'),
         ('extract data from sftp files task',
          'https://www.qualtrics.com/support/survey-platform/actions-page/extract-data-from-sftp-files-task/'),
         ('extract data from salesforce task',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-extractor-tasks/extract-data-from-salesforce-task/'),
         ('extract data from google drive task',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-extractor-tasks/extract-data-from-google-drive-task/'),
         ('import salesforce report data task',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-extractor-tasks/import-salesforce-report-data-task/'),
         ('extract response from a survey task',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-extractor-tasks/extract-responses-from-a-survey-task/'),
         ('load b2b account data into xm directory',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-loader-tasks/load-data-into-xm-directory-task/'),
         ('add contacts and transactions to xmd task',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-loader-tasks/add-contacts-and-transactions-to-xmd-task/'),
         ('load users into ex directory',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-loader-tasks/load-users-into-ex-directory-task/'),
         ('load users into cx directory',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-loader-tasks/load-users-into-cx-directory-task/'),
         ('load into a data project', 'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-loader-tasks/load-into-a-data-project-task/'),
         ('load into a data set task',
          'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-loader-tasks/load-into-a-data-set-task/'),
         ('load data into sftp task', 'https://www.qualtrics.com/support/survey-platform/actions-page/etl-workflows/data-loader-tasks/load-data-into-sftp-task/'),
         ('text iq', 'https://www.qualtrics.com/support/survey-platform/data-and-analysis-module/text-iq/text-iq-functionality/'),
         ('text iq topics', 'https://www.qualtrics.com/support/survey-platform/data-and-analysis-module/text-iq/topics-in-text-iq/'),
         ('sentiment analysis', 'https://www.qualtrics.com/support/survey-platform/data-and-analysis-module/text-iq/sentiment-analysis/'),
         ('text iq widgets', 'https://www.qualtrics.com/support/survey-platform/data-and-analysis-module/text-iq/widgets-in-text-iq/'),
         ('text iq in cx dashboards',
          'https://www.qualtrics.com/support/vocalize/dashboard-settings-cx/text-analysis-cx/'),
         ('creating a website & app feedback project',
          'https://www.qualtrics.com/support/website-app-feedback/creating-website-app-feedback-project/'),
         ('building a creative', 'https://www.qualtrics.com/support/website-app-feedback/getting-started-with-website-app-feedback/step-3-building-your-creative/'),
         ('intercept setup', 'https://www.qualtrics.com/support/website-app-feedback/getting-started-with-website-app-feedback/step-4-setting-up-your-intercept/'),
         ('website app feedback technical documentation',
          'https://www.qualtrics.com/support/website-app-feedback/getting-started-with-website-app-feedback/website-app-feedback-technical-documentation/'),
         ('xm directory', 'https://www.qualtrics.com/support/iq-directory/getting-started-iq-directory/getting-started-with-iq-directory/'),
         ('distributing to contacts in xm directory',
          'https://www.qualtrics.com/support/iq-directory/getting-started-iq-directory/first-distribution-xm-directory/step-2-distributing-to-contacts-in-xm-directory/'),
         ('directory maintenance and organization tips',
          'https://www.qualtrics.com/support/iq-directory/getting-started-iq-directory/xm-directory-maintenance-organization-tips/'),
         ('finding qualtrics ids',
          'https://www.qualtrics.com/support/integrations/api-integration/finding-qualtrics-ids/'),
         ('api documentation', 'https://www.qualtrics.com/support/integrations/api-integration/using-qualtrics-api-documentation/')]


def run():
    for tpl in inpts:
        # get the HTML
        subject = tpl[0]
        url = tpl[1]
        text = get_text_from_url(url)
        # make the summary
        summary = get_summary_from_text(text)
        # Write the summary to the json file
        write_summary(subject, url+" "+summary)
        sleep(3)


def write_summary(subject, summary):
    file_name = "data/primed_created.json"
    data = load_or_create_json_file()
    data[subject] = summary
    with open(file_name, "w") as json_file:
        json.dump(data, json_file)


def get_summary_from_text(text):
    try:
        full_msg = [{'role': 'system', 'content': 'you are a summary assistant. You will take in a large block of text from Qualtrics documentation and compress it into the fewest tokens possible while allowing a large language model to understand the content. say OK if you understand.'}, {
            'role': 'assistant', 'content': 'OK'}, {'role': 'user', 'content': text}]
        completion = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=full_msg
        )
        resp = completion.choices[0].message.content
        print("summary:", resp)
        return resp
    except:
        sleep(30)
        return get_summary_from_text(text)


def get_text_from_url(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    accum = ''
    start = False
    for p_tag in soup.find_all('p'):
        if start:
            if "creating & managing con..." in p_tag.get_text().lower():
                break
            # file.write(p_tag.get_text())
            # file.write("\n")
            accum += p_tag.get_text()
        else:
            if "thank you for your feedback!" in p_tag.get_text().lower():
                start = True
                continue
    accum += "\n\ncompress the above as much as you can with symbols, emojis and other short hand, so that it takes as absolutely few tokens as possible, do not use line breaks, but be certain that you retain whatever is necessary for another chatbot like yourself to be able to decompress it and understand it."
    return accum


def load_or_create_json_file():
    file_name = "data/primed_created.json"
    # Write the empty file if it doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, "w") as json_file:
            json.dump({}, json_file)
    # Read the file data
    with open(file_name, "r") as json_file:
        data = json.load(json_file)

    return data


if __name__ == "__main__":
    run()
