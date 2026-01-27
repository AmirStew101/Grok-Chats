import os, json, sqlite3, glob
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import user, system, assistant

# Load environment variables from .env file
load_dotenv()

# This class handles all database operations using SQLite
class Database:
    DB_NAME = 'chat_history.db'

    # This function establishes a connection to the SQLite database
    def get_db_connection(self):
        conn = sqlite3.connect(self.DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    
    # This function initializes the database and creates necessary tables
    def init_db(self):
        conn = self.get_db_connection()
        c = conn.cursor()
        # Create personalities table
        # We are ignoring the 'liked' column in personalities if it exists, as it's no longer used.
        c.execute('''
            CREATE TABLE IF NOT EXISTS personalities (
                name TEXT PRIMARY KEY,
                liked INTEGER DEFAULT 0
            )
        ''')
        # Create messages table
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personality_name TEXT,
                input TEXT,
                response TEXT,
                liked INTEGER DEFAULT 0,
                FOREIGN KEY(personality_name) REFERENCES personalities(name)
            )
        ''')
        
        # Attempt to add 'liked' column to messages if it doesn't exist (migration)
        try:
            c.execute('ALTER TABLE messages ADD COLUMN liked INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()
    
    # This function migrates existing JSON chat history files to the SQLite database
    def migrate_from_json(self):
        # Ensure all defined personalities exist in DB
        conn = self.get_db_connection()
        c = conn.cursor()
        for name in PERSONALITIES:
            c.execute('INSERT OR IGNORE INTO personalities (name) VALUES (?)', (name,))
        conn.commit()
        
        # Migrate JSON files
        json_files = glob.glob('*_chat.json')
        for file_path in json_files:
            chat_name = os.path.splitext(os.path.basename(file_path))[0].replace('_chat', '')
            
            # Ensure personality exists
            c.execute('INSERT OR IGNORE INTO personalities (name) VALUES (?)', (chat_name,))
            
            with open(file_path, 'r') as f:
                try:
                    history = json.load(f)
                    for item in history:
                        c.execute('INSERT INTO messages (personality_name, input, response) VALUES (?, ?, ?)',
                                (chat_name, item['input'], item['response']))
                except json.JSONDecodeError:
                    print(f"Error reading {file_path}")
            
            conn.commit()
            # Rename processed file
            os.rename(file_path, file_path + '.bak')
        
        conn.close()

    # This function returns the chat history for a given chat name
    def get_chat_history(self, chat_name):
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, input, response, liked FROM messages WHERE personality_name = ?', (chat_name,))
        rows = c.fetchall()
        conn.close()
        return [{'id': row['id'], 'input': row['input'], 'response': row['response'], 'liked': bool(row['liked'])} for row in rows]
    
    # This function returns a list of all chat names
    def get_all_chats(self):
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute('SELECT name FROM personalities')
        rows = c.fetchall()
        conn.close()
        return [{'name': row['name']} for row in rows]
    
    # This function toggles the liked status of a message
    def toggle_message_like(self, message_id):
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute('SELECT liked FROM messages WHERE id = ?', (message_id,))
        row = c.fetchone()
        if row:
            new_liked = 0 if row['liked'] else 1
            c.execute('UPDATE messages SET liked = ? WHERE id = ?', (new_liked, message_id))
            conn.commit()
            conn.close()
            return bool(new_liked)
        conn.close()
        return False
    
    # This function updates the content of a message
    def update_message_content(self, message_id, new_content):
        conn = self.get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE messages SET response = ? WHERE id = ?', (new_content, message_id))
        conn.commit()
        updated = c.rowcount > 0
        conn.close()
        return updated

    # This function saves a message to the corresponding chat file
    def save_message(self, chat_name, message):
        conn = self.get_db_connection()
        c = conn.cursor()
        # Ensure personality exists
        c.execute('INSERT OR IGNORE INTO personalities (name) VALUES (?)', (chat_name,))
        c.execute('INSERT INTO messages (personality_name, input, response) VALUES (?, ?, ?)',
                (chat_name, message["input"], message["response"]))
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        return new_id

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

db = Database()

# The personality prompts
PERSONALITIES = {
    "daniel": os.environ.get('PERSONALITY_DANIEL', "You are Daniel, a middle aged man who is knowledgeable, smart, and has a fun personality."), 
    "harry": os.environ.get('PERSONALITY_HARRY', "You are Harry, a young adult man who is a streamer who is knowledgeable, smart, enthusiastic, and curious."),
    "jessica": os.environ.get('PERSONALITY_JESSICA', "You are Jessica, a middle aged female who is caring, empathetic, a good listener and provide thoughtful responses."),
    "zeke": os.environ.get('PERSONALITY_ZEKE', "You are Zeke, a middle aged male who is damn near crazy, eccentric, and have an explosive personality.")
}

# The source to guide each personalities information and how it will give responses.
def get_personality_source(personality_name):
    if not personality_name.lower() in PERSONALITIES:
        raise ValueError(f"Unknown personality: {personality_name}")
    
    if personality_name == "zeke":
        return os.environ.get('GENERAL_SOURCE', "")
    else:
        return os.environ.get('PERSONALITY_SOURCE', "You tell entertaining and captivating stories. Don't mention your age, AI nature, or say these are real stories. Always use engaging and descriptive language to captivate the audience that matches your personality.")

# This function gets a response from the Grok API for a given chat and user input
def get_grok_response(chat_name, user_input):
    chat_name = chat_name.lower()
    if chat_name not in PERSONALITIES:
        # It might be a custom chat not in the hardcoded list, check DB or raise
        # For now, sticking to logic that requires it to be in PERSONALITIES or we rely on DB existence?
        # The original code checked PERSONALITIES. Let's keep that check but also support if it's in DB?
        # Actually, original code raised ValueError.
        if chat_name not in PERSONALITIES:
             raise ValueError(f"Unknown personality: {chat_name}")
    
    # Load the chat history from DB
    history = db.get_chat_history(chat_name)

    # Create a new GrokChat instance, load the history, and get a response
    grok_chat = GrokChat()
    grok_chat.system_teach(PERSONALITIES[chat_name] + get_personality_source(chat_name))
    grok_chat.load_history(history)
    
    return grok_chat.user_talk(user_input)


# Initialize DB and migrate on module load (or call explicitly from app.py)
# Better to call explicitly to avoid side effects on import, but for simplicity/script nature:
if __name__ == "__main__":
    db.init_db()
    db.migrate_from_json()