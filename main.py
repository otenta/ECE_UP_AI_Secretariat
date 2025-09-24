import os
import json
import traceback

from twilio.twiml.voice_response import VoiceResponse, Gather
from name_hints import NAME_HINTS

from flask import Flask, request
from flask_sock import Sock
import ngrok
from twilio.rest import Client
from dotenv import load_dotenv
from handlers_base import Sector, SECTOR_PROMPTS, HANDLERS

load_dotenv()

PORT = 8080
DEBUG = False
INCOMING_CALL_ROUTE = '/select_sector'

# Twilio authentication
account_sid = os.environ['TWILIO_ACCOUNT_SID']
api_key = os.environ['TWILIO_API_KEY_SID']
api_secret = os.environ['TWILIO_API_SECRET']
client = Client(api_key, api_secret, account_sid)

# Twilio phone number to call
TWILIO_NUMBER = os.environ['TWILIO_NUMBER']

# ngrok authentication
ngrok.set_auth_token(os.getenv("NGROK_AUTHTOKEN"))
app = Flask(__name__)
sock = Sock(app)

SESSION = {}  # key: CallSid -> {"sector": Sector, "last_result": str}

def _safe_redirect_call(call_sid: str, url: str):
    try:
        client.calls(call_sid).update(url=url, method="POST")
    except Exception as e:
        print("Redirect error:", repr(e))

@app.route("/welcome", methods=["GET", "POST"])
def welcome_base():
    response = VoiceResponse()
    gather = Gather(method='POST', action=f"{NGROK_URL}{INCOMING_CALL_ROUTE}", numDigits="1", timeout=5)
    gather.say("Press 1 for Exams Schedule. \n"
               "2 for Office Hours. \n"
               "3 for Daily Schedule. \n"
               "4 for Academic Schedule. \n"
               "5 for Study Guide. \n"
               "6 to end the call.\n"
               "Or press 7 to hear the options again", language='en-GB')
    response.append(gather)

    response.redirect("/welcome") #if no input re-prompt
    return str(response)

@app.route("/select_sector", methods=["POST"])
def select_sector():
    digit_pressed = request.values.get('Digits', None)
    call_sid = request.values.get('CallSid')
    response = VoiceResponse()
    if digit_pressed == "6":
        response.say("Goodbye", language='en-GB')
        response.hangup()
        return str(response)

    if digit_pressed == "7":
        response.redirect("/welcome")
        return str(response)

    sector = next((s for s in Sector if s.value == digit_pressed), None)
    if not sector:
        response.say(f"You selected {digit_pressed}. Not configured. Returning to menu.")
        response.redirect("/welcome")
        return str(response)

    SESSION.setdefault(call_sid, {})["sector"] = sector
    prompt = SECTOR_PROMPTS[sector]

    response.say(prompt, language='en-GB')
    response.redirect("/voice")
    return str(response)

@app.route("/voice", methods=["GET", "POST"])
def voice():
    response = VoiceResponse()
    call_sid = request.values.get("CallSid")
    sess = SESSION.setdefault(call_sid, {})
    sess["transcription_active"] = True
    sess["handled_turn"] = False
    start = response.start()
    start.transcription(statusCallbackUrl=f"{listener.url()}/transcribe", transcription_engine='google', speech_model='telephony', hints=NAME_HINTS)
    response.pause(length=120)
    return str(response)


@app.route("/transcribe", methods=['POST'])
def transcribe_callback():
    # Use .form because Twilio sends data as form-encoded, not JSON
    event = request.form.get('TranscriptionEvent')
    call_sid = request.form.get("CallSid")  # used for session + redirect

    if event != "transcription-content":
        return "", 204

    payload = request.form.get("TranscriptionData") or request.form.get("TranscriptionText")
    text = None
    if payload:
        try:
            trans_json = json.loads(payload)
            text = trans_json.get("transcript") or trans_json.get("Transcript") or payload
            print(text)
        except json.JSONDecodeError:
            text = payload

    # Session + duplicate-chunk guard
    sess = SESSION.setdefault(call_sid, {})
    if not sess.get("transcription_active", False):
        print("[transcribe] Ignored: transcription no longer active.")
        return "", 204
    if sess.get("handled_turn", False):
        print("[transcribe] Ignored: turn already handled.")
        return "", 204

    sector = sess.get("sector")
    print(f"[transcribe] Sector: {sector} | Text: {text!r}")

    # If we got no usable text, respond kindly and go to menu
    if not text or not text.strip():
        sess["last_result"] = "Returning back to menu."
        sess["handled_turn"] = True
        _safe_redirect_call(call_sid, f"{NGROK_URL}/speak_result")
        return "", 204

    # Dispatch
    handler = HANDLERS.get(sector)
    if not handler:
        result_text = "Not a valid selection."
    else:
        try:
            result_text = handler(text.strip())
        except Exception as e:
            print("Handler error:", repr(e))
            traceback.print_exc()
            result_text = "An error occurred during the processing of the request."

    # Always set result + redirect (success OR failure)
    sess["last_result"] = result_text
    sess["handled_turn"] = True
    sess["transcription_active"] = False
    _safe_redirect_call(call_sid, f"{NGROK_URL}/speak_result")

    print("[transcribe] Processed transcript, redirecting to speak_result.")
    return "", 204


@app.route("/speak_result", methods=["POST"])
def speak_result():
    call_sid = request.values.get("CallSid")
    response = VoiceResponse()
    stop = response.stop()
    stop.transcription()
    text = SESSION.get(call_sid, {}).get("last_result") or "No results for announcement."
    response.say(text, language='en-GB')
    response.pause(length=1)
    SESSION.setdefault(call_sid, {}).pop("handled_turn", None)
    response.redirect("/welcome")
    return str(response)


if __name__ == "__main__":
    try:
        # Open Ngrok tunnel
        listener = ngrok.forward(f"http://localhost:{PORT}")
        print(f"Ngrok tunnel opened at {listener.url()} for port {PORT}")
        NGROK_URL = listener.url()

        # Set ngrok URL to ne the webhook for the appropriate Twilio number
        twilio_numbers = client.incoming_phone_numbers.list()
        twilio_number_sid = [num.sid for num in twilio_numbers if num.phone_number == TWILIO_NUMBER][0]
        client.incoming_phone_numbers(twilio_number_sid).update(account_sid, voice_url=f"{NGROK_URL}{INCOMING_CALL_ROUTE}")

        # run the app
        app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
    finally:
        # Always disconnect the ngrok tunnel
        ngrok.disconnect()