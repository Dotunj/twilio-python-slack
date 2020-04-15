import os
import slack
import redis
from dotenv import load_dotenv
from flask import Flask, request, Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
load_dotenv()
app = Flask(__name__)


redisClient = redis.Redis(decode_responses=True)
slackClient = slack.WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilioClient = Client(account_sid, auth_token)


@app.route('/incoming/twilio', methods=['POST'])
def send_incoming_message():
    from_number = request.form['From']
    sms_message = request.form['Body']
    message = f"Text message from {from_number}: {sms_message}"
    slack_message = slackClient.chat_postMessage(
        channel='#general', text=message, icon_emoji=':robot_face:')
    message_id = slack_message['ts']
    attributes = {message_id: from_number}
    redis_message = redisClient.mset(attributes)
    response = MessagingResponse()
    return Response(response.to_xml(), mimetype="text/html"), 200

@app.route('/incoming/slack', methods=['POST'])
def send_incoming_slack():
    attributes = request.get_json()
    incoming_slack_message_id, slack_message = parse_message(attributes)
    if incoming_slack_message_id and slack_message:
        to_number = redisClient.get(incoming_slack_message_id)
        if to_number:
            messages = twilioClient.messages.create(
                to=to_number, from_=os.getenv("TWILIO_FROM"), body=slack_message)
        return Response(), 200
    return Response(), 200


def parse_message(attributes):
    if 'event' in attributes and 'thread_ts' in attributes['event']:
        return attributes['event']['thread_ts'], attributes['event']['text']
    return None, None


if __name__ == '__main__':
    app.run()
