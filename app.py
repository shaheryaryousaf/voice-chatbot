# Import Libraries
from itertools import zip_longest
import streamlit as st
from streamlit_chat import message
from langchain.chat_models import ChatOpenAI
from langchain.tools import YouTubeSearchTool
import ast
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from gtts import gTTS
import pyaudio
import wave
import speech_recognition as sr

openai_key = st.secrets["OPENAI_API_KEY"]

# Page Config
st.set_page_config(
    page_title="HealthMate Bot | Your Digital Partner in Nutrition")
st.title("HealthMate Bot")
st.write("Your Digital Partner in Nutrition")


# Create States
initialStates = {
    'entered': '',
    'generated': [],
    'past': [],
    'api_key': '',
    'key_validation': False
}
for key, value in initialStates.items():
    if key not in st.session_state:
        st.session_state[key] = value


with st.sidebar:
    st.title("API Key")
    api = st.text_input("Please add yout API key.", type="password")
    validate = st.button("Validate API")

    if validate:
        if api.startswith("sk-"):
            st.session_state['api_key'] = api
            st.session_state['key_validation'] = True
        elif not api.startswith('sk-'):
            st.write("Please add a valid API Key")
        else:
            st.write("Please an API Key")


with st.container():
    if st.session_state['key_validation']:
        # LLM
        chat = ChatOpenAI(
            temperature=0.9, openai_api_key=st.session_state['api_key'], model="gpt-3.5-turbo", max_tokens=300
        )

        # Constants for Audio File
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        CHUNK = 1024
        RECORD_SECONDS = 5
        TEMP_AUDIO_FILENAME = "temp_audio.wav"
        audio = pyaudio.PyAudio()

        # Create Message list

        def messages_list():
            system_instructions = """
                        your name is Nutrition Guide. You are an Health Expert for Nutrition and Dietetics, here to guide and assist individuals with their nutrition and diet-related questions and concerns. Please provide accurate and helpful advice, and always maintain a polite and professional demeanor.

                                        1. Greet the user politely, ask their name, and inquire how you can assist them with their nutrition and diet-related queries.
                                        2. Provide informative and relevant responses to questions about nutrition, dietary needs, weight management, vitamins and minerals, allergies and intolerances, and related topics.
                                        3. you must Avoid discussing sensitive, offensive, or harmful content. Refrain from engaging in any form of discrimination, harassment, or inappropriate behavior.
                                        4. If the user asks about a topic unrelated to nutrition or diet, politely steer the conversation back to those subjects or inform them that the topic is outside the scope of this conversation.
                                        5. Be patient and considerate when responding to user queries, and offer clear explanations.
                                        6. If the user expresses gratitude or indicates the end of the conversation, respond with a polite farewell.
                                        7. Do Not generate long paragraphs in response. Maximum Words should be 100.

                        Remember, your primary goal is to assist and educate individuals in the field of Nutrition and Dietetics. Always prioritize their health and well-being. Make sure to give answer under 100 words.
                            """
            messages = [SystemMessage(content=system_instructions)]

            for human_msg, ai_msg in zip_longest(st.session_state['generated'], st.session_state['past']):
                if human_msg is not None:
                    messages.append(HumanMessage(content=human_msg))
                if ai_msg is not None:
                    messages.append(AIMessage(content=ai_msg))
            return messages


        # Submit function
        def submit():
            st.session_state.entered, st.session_state.input = st.session_state.input, ""

        # Create Text Field
        st.text_input("Ask Question", on_change=submit, key="input")


        # Record Audio
        def record_audio_to_file():
            stream = audio.open(format=FORMAT, channels=CHANNELS,
                                rate=RATE, input=True, frames_per_buffer=CHUNK)
            frames = []

            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                data = stream.read(CHUNK)
                frames.append(data)

            stream.stop_stream()
            stream.close()

            with wave.open(TEMP_AUDIO_FILENAME, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))

        # Convert Audio to Text

        def audio_to_text(audio_filename):
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_filename) as source:
                recorded_audio = recognizer.listen(source)
                try:
                    return recognizer.recognize_google(recorded_audio)
                except sr.UnknownValueError:
                    return "Sorry, I could not understand the audio."
                except sr.RequestError as e:
                    return f"API unavailable or unresponsive. {str(e)}"

        record_btn = st.button("Record")

        if record_btn:
            record_audio_to_file()
            transcription = audio_to_text(TEMP_AUDIO_FILENAME)
            # st.write(transcription)
            st.session_state.entered = transcription

        # Generate Response

        def generate_response():
            return chat(messages_list()).content

        # Check if entered prompt is not empty
        if st.session_state.entered != "":
            st.session_state['past'].append(st.session_state.entered)
            st.session_state['generated'].append(generate_response())

        # Display Messages
        if st.session_state['generated']:
            for m in range(len(st.session_state['generated'])-1, -1, -1):
                message(st.session_state['generated'][m], key=str(m))
                tts = gTTS(st.session_state['generated'][m], lang='en')
                tts.save("custom_audio.mp3")
                st.audio("custom_audio.mp3")
                tool = YouTubeSearchTool()
                response = tool.run(st.session_state['past'][m] + ", 2")
                if response:
                    st.subheader("Related Youtube Videos:")
                    urlsList = ast.literal_eval(response)
                    columns = st.columns(len(urlsList))
                    for col, url in zip(columns, urlsList):
                        cleanUrl = url.split("&pp")[0]
                        finalUrl = cleanUrl.replace("watch?v=", "embed/")
                        col.markdown(f'<iframe width="100%" height="250px" src="{finalUrl}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
                message(st.session_state['past'][m],
                        is_user=True, key=str(m)+"_user")
