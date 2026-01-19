import os, json
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import user, system, assistant

# Load environment variables from .env file
load_dotenv()

# This class is a wrapper around the xai_sdk.Client to interact with the Grok API
class GrokChat:
    # Get the API key from the environment variables
    api_key = os.environ.get('API_KEY')
    if api_key == None:
        raise KeyError("API_KEY environment variable not set")

    # The model to use for the chat
    model = "grok-4"

    # The xai_sdk.Client instance
    client = Client(
        api_key=api_key,
        api_host="us-east-1.api.x.ai",
        timeout=3600
    )

    def __init__(self):
        # Create a new chat when the class is instantiated
        self.chat = self.create_new_chat()
    
    # Add a system message to the chat
    def system_teach(self, story):
        self.chat.append(system(story))
    
    # Add a user message to the chat and get a response
    def user_talk(self, input_text):
        self.chat.append(user(input_text))
        response = self.ask_grok_chat()
        return {"input": input_text, "response": response}

    # Get a response from the Grok API
    def ask_grok_chat(self):
        print("Asking Grok...")
        response = self.chat.sample()
        return response.content
    
    # Load the chat history from a list of dictionaries
    def load_history(self, history):
        for hist_dict in history:
            self.chat.append(user(hist_dict["input"]))
            self.chat.append(assistant(hist_dict["response"]))

    # Create a new chat
    def create_new_chat(self):
        return self.client.chat.create(model=self.model)

# The personality prompts
PERSONALITIES = {
    "daniel": "You are Daniel, a 40 year old man who is knowledgeable, smart, and has a fun personality. Your revenge stories are focused more on real life or in person revenge.",
    "harry": "You are Harry, a 25 year old man who is a streamer who is knowledgeable, smart, enthusiastic, and curious. Your revenge stories are focused more on online internet revenge.",
    "jessica": "You are Jessica, a 30 year old female who is caring, empathetic, a good listener and provide thoughtful responses. Your revenge stories are focused more on real life or in person revenge."
}

# The source to guide each personalities information and how it will give responses.
personality_source = os.environ.get('PERSONALITY_SOURCE')
if personality_source == None:
    raise KeyError("PERSONALITY_SOURCE environment variable not set")


# This function gets a response from the Grok API for a given chat and user input
def get_grok_response(chat_name, user_input):
    chat_name = chat_name.lower()
    if chat_name not in PERSONALITIES:
        raise ValueError(f"Unknown personality: {chat_name}")
    
    # Load the chat history from the corresponding json file
    file_path = f"{chat_name}_chat.json"
    history = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            history = json.load(f)

    # Create a new GrokChat instance, load the history, and get a response
    grok_chat = GrokChat()
    grok_chat.system_teach(PERSONALITIES[chat_name] + personality_source)
    grok_chat.load_history(history)
    
    return grok_chat.user_talk(user_input)

# This function saves a message to the corresponding chat file
def save_message(chat_name, message):
    file_path = f"{chat_name}_chat.json"
    history = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            history = json.load(f)
    
    history.append({"input": message["input"], "response": message["response"]})
    with open(file_path, 'w') as f:
        json.dump(history, f, indent=2)