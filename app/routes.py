import openai
from flask import (
    Flask,
    render_template,
    request,
    Response,
    stream_with_context,
    jsonify,
    current_app,
    session
)
import json
from prometheus_client import Summary, Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
from openai import OpenAI
import uuid
import redis

# Configure OpenAI client
client = OpenAI(api_key=current_app.config['OPENAI_API_KEY'], timeout=20.0, max_retries=2)

CHAT_HISTORY_TTL = 3600

def get_redis_client():
    return current_app.config['REDIS_CLIENT']

def get_or_create_conversation_id():
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
    return session['conversation_id']

def get_chat_history(conversation_id):
    redis_client = get_redis_client()
    cache_version = current_app.config['CACHE_VERSION']
    try:
        chat_history = redis_client.get(f"chat:{cache_version}:{conversation_id}")
        if chat_history:
            return json.loads(chat_history)
    except redis.RedisError as e:
        current_app.logger.error(f"Redis error when getting chat history: {str(e)}")
    return [{"role": "system", "content": "Hello. What would you like to talk about?"}]

def save_chat_history(conversation_id, chat_history):
    redis_client = get_redis_client()
    cache_version = current_app.config['CACHE_VERSION']
    try:
        redis_client.setex(f"chat:{cache_version}:{conversation_id}", CHAT_HISTORY_TTL, json.dumps(chat_history))
    except redis.RedisError as e:
        current_app.logger.error(f"Redis error when saving chat history: {str(e)}")

call_metric = Counter('flaskai_monitor_home_count', 'Number of visits to FlaskAI', ["service", "endpoint"])
time_metric = Summary('flaskai_monitor_request_processing_seconds', 'Time spent processing request', ["method"])

@current_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@current_app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

index_timer = time_metric.labels(method="index")
index_visitor_count = call_metric.labels(service="devopseraidemo", endpoint="index")

# Chat quickstart
@current_app.route("/", methods=["GET"])
def index():
    start_time = time.time()  # Start timing

    # Increment the counter
    index_visitor_count.inc()

    # Observe the time taken to process the request
    index_timer.observe(time.time() - start_time)

    # Render the template with result and error_message
    conversation_id = get_or_create_conversation_id()
    chat_history = get_chat_history(conversation_id)
    return render_template("index.html", chat_history=chat_history)

@current_app.route("/chat", methods=["POST"])
def chat():
    conversation_id = get_or_create_conversation_id()
    chat_history = get_chat_history(conversation_id)
    content = request.json["message"]
    chat_history.append({"role": "user", "content": content})
    save_chat_history(conversation_id, chat_history)
    return jsonify(success=True)

@current_app.route("/stream", methods=["GET"])
def stream():
    conversation_id = get_or_create_conversation_id()
    chat_history = get_chat_history(conversation_id)

    def generate():
        assistant_response_content = ""
        try:
            with client.chat.completions.create(
                model="gpt-4",
                messages=chat_history,
                stream=True,
            ) as stream:
                for chunk in stream:
                    if chunk.choices[0].delta and chunk.choices[0].delta.content:
                        assistant_response_content += chunk.choices[0].delta.content
                        yield f"data: {chunk.choices[0].delta.content}\n\n"
                    if chunk.choices[0].finish_reason == "stop":
                        break

            chat_history.append(
                {"role": "assistant", "content": assistant_response_content}
            )
            save_chat_history(conversation_id, chat_history)
        except openai.APIConnectionError as e:
            yield f"data: Error - The server could not be reached: {str(e)}\n\n"
        except openai.RateLimitError as e:
            yield f"data: Error - A 429 status code was received; we should back off a bit: {str(e)}\n\n"
        except openai.APIStatusError as e:
            yield f"data: Error - Another non-200-range status code was received: {str(e)} (Status Code: {e.status_code}, Response: {e.response})\n\n"
        except openai.APIError as e:
            yield f"data: Error - An unknown API error occurred: {str(e)}\n\n"
        except Exception as e:
            yield f"data: Error - {str(e)}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@current_app.route("/reset", methods=["POST"])
def reset_chat():
    conversation_id = get_or_create_conversation_id()
    initial_message = [{"role": "system", "content": "Hello. What would you like to talk about?"}]
    save_chat_history(conversation_id, initial_message)
    return jsonify(success=True)


# Example route to check session handling
@current_app.route('/set_session', methods=['POST'])
def set_session():
    session['user_input'] = request.json['message']
    return jsonify(success=True)

@current_app.route('/get_session', methods=['GET'])
def get_session():
    user_input = session.get('user_input', 'No input set')
    return jsonify(user_input=user_input)