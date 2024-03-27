from flask import Flask, render_template, request, redirect, url_for, session
from kafka import KafkaConsumer
import threading
import openai
import os

#보고서 다운로드
from flask import send_from_directory

app = Flask(__name__)
app.secret_key = 'welcome1'

# GPT-3 설정
OPENAI_API_KEY = '${OPEN_API_KEY}'

# 파일이 저장될 경로 설정
UPLOAD_FOLDER = '/jhhan/hackerton/test_log'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Kafka 설정
KAFKA_TOPIC = 'default_topic'
KAFKA_SERVERS = ['211.110.82.175:9092']  # Kafka 서버 주소

# 메시지 버퍼
messages = []

# Kafka 메시지 수신 함수
def kafka_consumer(topic):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_SERVERS,
        auto_offset_reset='earliest',
        enable_auto_commit='False',
        group_id=None
    )
    for message in consumer:
        msg = message.value.decode('utf-8')
        print(f"Received message: {msg}")  # 로깅
        messages.append(msg)
        if len(messages) > 100:  # 버퍼 사이즈 조절
            messages.pop(0)

@app.route('/')
def index():
    return render_template('index.html')

#new file download
@app.route('/download_response')
def download_response():
    filename = 'gpt_response.txt'
    # GPT 응답을 텍스트 파일로 저장
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'w') as f:
        f.write(session.get('gpt_response', 'No response'))
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=filename, as_attachment=True)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    if file:
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        return redirect(url_for('index'))  # 파일 업로드 후, index 페이지로 리디렉션

@app.route('/select_topic', methods=['POST'])
def select_topic():
    selected_topic = request.form['topic']
    session['KAFKA_TOPIC'] = selected_topic
    # Kafka Consumer 스레드 시작
    threading.Thread(target=kafka_consumer, args=(selected_topic,), daemon=True).start()
    return redirect(url_for('run'))

@app.route('/run', methods=['GET', 'POST'])
def run():
    kafka_message = "<br>".join(messages) if messages else "No Kafka messages yet"
    gpt_response = ""
    if request.method == 'POST':
        user_input = request.form.get('user_input', '')
        prompt = f"{kafka_message}\n\n{user_input}"
        gpt_response = ask_gpt(prompt)
    return render_template('run.html', kafka_message=kafka_message, gpt_response=gpt_response)

def ask_gpt(prompt):
    openai.api_key = OPENAI_API_KEY
    response = openai.Completion.create(
        engine="gpt-3.5-turbo-instruct",
        prompt=prompt,
        temperature=0.5,
        max_tokens=2048
        #max_tokens=4097
    )
    return response.choices[0].text.strip()

if __name__ == '__main__':
    app.run(debug=True)
