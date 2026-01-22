from aiohttp import web
import json, glob, os
from grok_chat import get_grok_response, db

# API endpoint to get a list of all available chats.
# It returns a list of chat objects with name.
async def get_chats(request):
    chats = db.get_all_chats()
    return web.json_response(chats)

# API endpoint to get the chat history for a specific chat.
# It reads the history from the database and returns the content.
# The data is transformed to the format expected by the frontend.
async def get_chat_history(request):
    chat_name = request.match_info['chat_name']
    history = db.get_chat_history(chat_name)

    # Transform the data to the format expected by the frontend
    transformed_history = []
    for item in history:
        transformed_history.append({'role': 'user', 'content': item['input']})
        # Include id and liked status for assistant messages
        transformed_history.append({
            'role': 'assistant', 
            'content': item['response'],
            'id': item['id'],
            'liked': item['liked']
        })

    return web.json_response(transformed_history)

# API endpoint to toggle the like status of a message.
async def like_message(request):
    try:
        message_id = int(request.match_info['message_id'])
        new_status = db.toggle_message_like(message_id)
        return web.json_response({'liked': new_status})
    except ValueError:
        return web.Response(status=400, text="Invalid message ID")

# API endpoint to add a new message to a chat.
# It gets the new message from the request, calls the grok API to get a response,
# saves the new message and response to the chat file, and returns the response to the frontend.
async def add_message(request):
    chat_name = request.match_info['chat_name']
    
    try:
        data = await request.json()
        user_input = data['content']
    except (json.JSONDecodeError, KeyError):
        return web.Response(status=400, text="Invalid JSON")

    new_message = get_grok_response(chat_name, user_input)
    # save_message now returns the new message ID
    msg_id = db.save_message(chat_name, new_message)

    return web.json_response({
        'role': 'assistant', 
        'content': new_message['response'],
        'id': msg_id,
        'liked': False
    })

# Serves the main html file
async def index(request):
    return web.FileResponse('./index.html')

# Serves the javascript file
async def script(request):
    return web.FileResponse('./script.js')


app = web.Application()
# Add the routes for the static files and the API endpoints
app.add_routes([
    web.get('/', index),
    web.get('/script.js', script),
    web.get('/api/chats', get_chats),
    web.get('/api/chats/{chat_name}', get_chat_history),
    web.post('/api/chats/{chat_name}', add_message),
    web.post('/api/messages/{message_id}/like', like_message),
])

if __name__ == '__main__':
    # Initialize the database and migrate any existing JSON files
    db.init_db()
    db.migrate_from_json()
    # Runs the web application
    web.run_app(app)