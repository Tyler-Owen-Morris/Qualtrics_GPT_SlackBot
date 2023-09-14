home_view = {
    # Home tabs must be enabled in your app configuration page under "App Home"
    # and your app must be subscribed to the app_home_opened event
    "type": "home",
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "I am a Qualtrics assistant that uses Chat GPT to answer Qualtrics related questions.\n\nI am still in beta, so don't trust everything I say. Look up my responses to verify!"
            },
            "accessory": {
                "type": "image",
                "image_url": "https://imgur.com/IUdjC13.jpg",
                "alt_text": "cute cat"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Behavior:",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "*Direct Message* me your qualtrics related questions and I will respond directly.\n*@ me in Channel* and I will reply in a thread. If I do not reply in thread- that channel is not in my go-list.\n\n"
                }
            ]
        },
        {
            "type": "image",
            "title": {
                "type": "plain_text",
                "text": "Replies are formatted with the text of what I said first, followed by the subject's I referenced to arrive an an answer:",
                "emoji": True
            },
            "image_url": "https://imgur.com/QMHuG24.jpg",
            "alt_text": "Sample Response"
        },
        {
            "type": "divider"
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Commands:",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "*--reset*  Dumps chat history and resets the conversation with the bot.\n"
                },
                {
                    "type": "mrkdwn",
                    "text": "\n*--subject*  Prompts the bot to report the subjects that it has available."
                }
            ]
        }
    ]
}
