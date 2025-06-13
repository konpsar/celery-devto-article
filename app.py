from flask import Flask, jsonify
from celery import Celery
import time

app = Flask(__name__)

# Configure Celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
xxx = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
# celery.conf.update(app.config)

# Define a Celery task
@xxx.task
def say_hello():
    time.sleep(10)
    return "Hello, World!"

# API route to trigger the task
@app.route('/hello', methods=['GET'])
def trigger_task():
    task = say_hello.delay()
    return jsonify({"task_id": task.id, "status": "Task has been submitted"}), 202

if __name__ == '__main__':
    app.run(debug=True)