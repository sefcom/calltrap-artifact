
import json
import websockets
from aiohttp import web, WSMsgType
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

import random
import numpy as np
import asyncio
from tts_utils import *
from mimesis import Person, Address
from mimesis.locales import Locale
from mimesis.enums import Gender
import pgeocode
import pandas as pd
import datetime
from faker import Faker


TWILIO_ACCOUNT_SID="Insert value"
TWILIO_AUTH_TOKEN="Insert value"
TWILIO_API_ID ="Insert value"
OPENAI_API_KEY ="Insert value"
PORT = "Insert value"
PUBLIC_HOST = "Insert value"
SYSTEM_MESSAGE = "Insert value"
ROUTE = "insert value"
VOICE_PROFILE_TO_VOICE_IDS = "Insert value"
routes = web.RouteTableDef()


def generate_fake_persona_prompt(voice_profile: str, callee_number):
    # Setup
    person = Person(Locale.EN)
    address = Address(Locale.EN)
    geo = pgeocode.Nominatim('us')
    fake = Faker()

    # Parse voice_profile
    voice_gender, voice_age_group = voice_profile.split("_")
    gender = Gender.FEMALE if voice_gender == "female" else Gender.MALE

    # Age by category
    if voice_age_group == "young":
        age = random.randint(25, 40)
    elif voice_age_group == "middle":
        age = random.randint(41, 64)
    elif voice_age_group == "senior":
        age = random.randint(65, 75)
    

    # Real ZIP → city/state
    while True:
        zip_code = address.zip_code()
        location = geo.query_postal_code(zip_code)
        if pd.notna(location.place_name) and pd.notna(location.state_name):
            break

    # Name, age, dob
    name = fake.name_female() if gender == Gender.FEMALE else fake.name_male()
    
    year = datetime.datetime.now().year - age
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    dob = datetime.date(year, month, day).strftime("%B %d, %Y")

    # Fake address (real city/state, fake street)
    street = f"{random.randint(100, 9999)} {address.street_name()} {random.choice(['Street','Avenue','Road','Drive','Lane','Boulevard','Way','Place','Court','Terrace','Circle'])}"

    # Obfuscated email
    email_local = person.email().split("@")[0].replace(".", "").replace("_", "")

    # Generate realistic credit card number and ssn
    card_type = random.choice(["visa", "mastercard", "amex", "discover"])
    cc_num = fake.credit_card_number(card_type=card_type)
    cc_exp = fake.credit_card_expire(end="+3y", date_format="%m/%y")
    cc_cvv = fake.credit_card_security_code(card_type=card_type)
    ssn = fake.ssn()

    # Fake Medicare ID
    valid_letters = [ch for ch in "ABCDEFGHJKMNPQRTUVWXY"]
    mbi = (
        random.choice(valid_letters) + random.choice(valid_letters) + random.choice(valid_letters) + str(random.randint(0, 9))+ 
        str(random.randint(0, 9)) + random.choice(valid_letters) + str(random.randint(0, 9)) +
        random.choice(valid_letters) + str(random.randint(0, 9)) + str(random.randint(0, 9)) + str(random.randint(0, 9))
    )
    medicare_id = f"{mbi[:5]}--{mbi[5:9]}--{mbi[9:]}"

    identity_dict = {"name": name, "age": age, "dob": dob, "gender": voice_gender,
        "address": {"street": street, "city": location.place_name, "state": location.state_name,"zip": location.postal_code},
        "email": email_local, "ssn": ssn,
        "credit_card": {"type": card_type, "number": cc_num, "exp": cc_exp, "cvv": cc_cvv},
        "medicare_id": medicare_id, "medicare_reason": "disability"}

    new_personal_identity = f"""## Persona Details:
        - Name: {name}
        - Age: {age} (born {dob})
        - Gender: {voice_gender}
        - Born: {location.state_name}
        - Address: {street}, {location.place_name}, {location.state_name}, {location.postal_code}
        - Email: {email_local}
        - Phone Number: {callee_number[2:]}
        - Social Security Number: {ssn}
        - Credit Card: card type {card_type}, card number {cc_num}, exp {cc_exp}, CVV {cc_cvv}
        - Medicare ID: {medicare_id}
        """
    return SYSTEM_MESSAGE.replace("## Persona Details:", new_personal_identity), identity_dict


@routes.get("insert value")
async def index(request):
    return web.json_response({"message": "Try again"})

@routes.post("insert value")
async def handle_incoming_call(request):

    # Randomize id
    wait_time = random.randrange(3, 6)
    body = await request.post()
    body_dict = dict(body)
    call_sid = body.get("CallSid")
    print(call_sid)

    # Check if callee number is in progress
    if body.get("CalledVia"):
        callee_number = body.get("CalledVia")
    else:
        callee_number = body.get("Called")
    # inprogress_call = request.app['twilio_client'].calls.list(to=callee_number, status="in-progress")

    # Check if caller number is blocked
    from_number = body_dict["From"]

    response = VoiceResponse()

    response.pause(length=wait_time)
    host = PUBLIC_HOST or request.url.host
    print(host)
    connect = Connect()
    stream = Stream("Insert value")
    stream.parameter(name="call_sid", value=call_sid)
    connect.append(stream)
    response.append(connect)

    # Store call related information
    voice_profiles = ["female_senior", "male_senior", "female_middle", "male_middle", "female_young", "male_young"]
    voice_profile = random.choice(voice_profiles)
    voice_id = random.choice(VOICE_PROFILE_TO_VOICE_IDS[voice_profile])

    system_message, identity_dict = generate_fake_persona_prompt(voice_profile, callee_number)
    identity_dict["voice_profile"] = voice_profile
    identity_dict["voice_id"] = voice_id


    request.app[call_sid] = {}
    request.app[call_sid]["identity"] = identity_dict
    request.app[call_sid]["conversation"] = [{"role": "system", "content": system_message}]
    request.app[call_sid]["metadata"] = body_dict
    request.app[call_sid]["latest_media_timestamp"] = 0
    request.app[call_sid]["last_assistant_item"] = None
    request.app[call_sid]["response_start_timestamp_twilio"] = None
    request.app[call_sid]["mark_queue"] = []
    request.app[call_sid]["interim_queue"] = asyncio.Queue()
    request.app[call_sid]["synth_started"] = False


    return web.Response(text=str(response), content_type='application/xml')

@routes.get("insert value")
async def handle_media_stream(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    #gpt-realtime-2025-08-28
    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03',
        additional_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:


        stop_event = asyncio.Event()
        async def wait_for_start_event():

            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("event") == "start":
                        call_sid = data["start"]["callSid"]
                        print("Got call_sid from Twilio start event:", call_sid)
                        request.app[call_sid]["stream_sid"] = data["start"]["streamSid"]

                        # Retrieve the system message
                        system_message = request.app[call_sid]["conversation"][0]["content"]
                        await initialize_session(openai_ws, system_message)
                        await send_initial_conversation_item(openai_ws)
                        # Initilize elevenlabs websockets connection
                        ws_eleven = await initialize_eleven_connection(ws, request.app[call_sid]["stream_sid"], request.app[call_sid]["identity"]["voice_id"], request.app[call_sid])
                        request.app[call_sid]["tts_ws"] = ws_eleven

                        # First synthesize_with_eleven
                        await request.app[call_sid]["interim_queue"]
                        await synthesize_with_eleven(call_sid, request)
                        
                        # request.app[call_sid]["eleven_finished"] = eleven_finished``

                        
                        return call_sid
            return False

        async def receive_from_twilio(call_sid):
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    event = data.get("event")
                    if event == "start":
                        call_sid = data["start"]['callSid']

                    elif event == "media" and openai_ws.state == websockets.protocol.State.OPEN:
                        request.app[call_sid]["latest_media_timestamp"] = int(data['media']['timestamp'])
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }))

                    # elif event == "mark" and request.app[call_sid]["mark_queue"]:
                    elif event == "mark":
                        print(data["name"])
                        request.app[call_sid]["mark_queue"].pop(0)
                    
                    elif event == "stop":
                        stop_event.set()
                        break
                elif msg.type == WSMsgType.ERROR:
                    pass
                
                elif msg.type == WSMsgType.CLOSE:
                    pass

        async def send_to_twilio(call_sid):
            # call_sid = request.
            request.app[call_sid].setdefault("assistant_partial_buffer", "")
            request.app[call_sid].setdefault("synth_started", False)
            async for raw in openai_ws:
                if stop_event.is_set():
                    break
                response = json.loads(raw)

                # Get caller transcript
                if response.get("type") == "conversation.item.input_audio_transcription.completed":
                    transcript = response["transcript"]
                    request.app[call_sid]["conversation"].append({"role": "user", "content": transcript})
                    # print(f"caller: {transcript}" )
                
                # This is used to print out chatgpt's response  when it is audio_input-2-audio_output
                # Get assistant transcript
                if response.get("type") == "response.text.done":
                    transcript = response["text"]
                    request.app[call_sid]["conversation"].append({"role": "assistant", "content": transcript})
                    # print(f"assistant: {transcript}")
                    if request.app[call_sid]["response_start_timestamp_twilio"] is None:
                        request.app[call_sid]["response_start_timestamp_twilio"] = request.app[call_sid]["latest_media_timestamp"]
                        print("LLM response started at Twilio timestamp:", request.app[call_sid]["response_start_timestamp_twilio"])

                    await synthesize_with_eleven(call_sid, request)
                    # await send_mark(ws, request.app[call_sid])
                if response.get("type") == "response.text.delta":
                    if request.app[call_sid]["response_start_timestamp_twilio"] is None:
                        request.app[call_sid]["response_start_timestamp_twilio"] = request.app[call_sid]["latest_media_timestamp"]
                        # print("LLM response started at Twilio timestamp:", request.app[call_sid]["response_start_timestamp_twilio"])
                    # Update last_assistant_item safely
                    if response.get('item_id'):
                        request.app[call_sid]["last_assistant_item"] = response['item_id']
                    # await send_mark(ws, request.app[call_sid])
                    delta = response["delta"]
                    # print(f"[interim] assistant: {delta}")
                    if "oh" not in delta.lower():
                        await request.app[call_sid]["interim_queue"].put(delta)
                    
                    if delta.strip() and delta.strip()[-1] in ",.!?" and len(delta.split(" ")) >= 3:
                        await synthesize_with_eleven(call_sid, request)
                        # await send_mark(ws, request.app[call_sid])
                
                # Handling interruption
                if response.get("type") == "input_audio_buffer.speech_started":
                    # print("speech started detected")
                    await handle_speech_interruption_event(call_sid)
        
        async def handle_speech_interruption_event(call_sid):
            """Truncate assistant response if caller interrupts."""
            if request.app[call_sid]["mark_queue"] and request.app[call_sid]["response_start_timestamp_twilio"] is not None:
                elapsed_time = request.app[call_sid]["latest_media_timestamp"] - request.app[call_sid]["response_start_timestamp_twilio"]

                await ws.send_json({
                    "event": "clear",
                    "streamSid": request.app[call_sid]["stream_sid"]
                })
                request.app[call_sid]["mark_queue"].clear()
                request.app[call_sid]["last_assistant_item"] = None
                request.app[call_sid]["response_start_timestamp_twilio"] = None

        try:
            call_sid = await wait_for_start_event()
            task_send = asyncio.create_task(send_to_twilio(call_sid))
            await receive_from_twilio(call_sid)  # returns when "stop" is seen
            task_send.cancel()
            try:
                await task_send
            except asyncio.CancelledError:
                pass

        finally:
            if call_sid and call_sid in request.app:

                # Remove unnecessary items
                del request.app[call_sid]["tts_ws"]
                del request.app[call_sid]["interim_queue"]
                del request.app[call_sid]
            
    return ws


async def initialize_session(openai_ws, system_message):
    await openai_ws.send(json.dumps({
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad", "threshold": 0.8, "silence_duration_ms": 350,"create_response": True},
            "input_audio_format": "g711_ulaw",
            "instructions": system_message,
            "input_audio_transcription": {"model": "gpt-4o-mini-transcribe", "language": "en"},
            "modalities": ["text"],
            "temperature": 0.8
        }
    }))

    # Let the model talks first
    await send_initial_conversation_item(openai_ws)


async def send_initial_conversation_item(openai_ws):

    await openai_ws.send(json.dumps({
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [{
                "type": "input_text",
                "text": "Hello"
            }]
        }
    }))

    await openai_ws.send(json.dumps({
        "type": "response.create",
        "response": {
            "type": "text"
        }
    }))


def create_app():
    app = web.Application()
    app.add_routes(routes)
    return app


def main():
    web.run_app(create_app(), port=PORT)


if __name__ == "__main__":
    main()