from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from datetime import datetime
import pytz

app = Flask(__name__)

mongo_uri = ""
mongo_dbname = 'your_database'  # MongoDB 数据库名称
mongo_collection_name = 'messages'  # MongoDB 集合名称


def connect_mongodb(uri):
    client = MongoClient(uri)
    try:
        # Send a ping to confirm a successful connection
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)
    return client

mongodb_client = connect_mongodb(mongo_uri)

def get_status():
    # 获取北京时间
    beijing_tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(beijing_tz).timestamp()
    last_update_time = get_last_update_time(mongodb_client)
    time_diff = current_time - last_update_time
    status = False if time_diff > 60 else True
    return status
@app.route('/')
def index():
    page = int(request.args.get('page', 1))

    messages = get_messages_from_mongodb(mongodb_client, mongo_collection_name, page) 
    
    # 根据时间差确定状态
    status = get_status()
    # print(status,last_update_time)
    return render_template('index.html', messages=messages, page=page, status=status)

@app.route('/jump_to_page')
def jump_to_page():
    page = int(request.args.get('page', 1))

    if page < 1:
        return redirect(url_for('jump_to_page', page=1))

    messages = get_messages_from_mongodb(mongodb_client, mongo_collection_name, page)
    # 根据时间差确定状态
    status = get_status()
    return render_template('index.html', messages=messages, page=page, status=status)

def get_last_update_time(client):
    db = client[mongo_dbname]
    collection = db[mongo_collection_name]
    # 获取 last_update 文档的时间戳
    last_update_doc = collection.find_one({"_id": "last_update"})
    return last_update_doc.get("timestamp") if last_update_doc else None

def get_messages_from_mongodb(client, collection_name, page=1, qtimestamp=None, limit=20):
    # qtimestamp 用于根据时间查询，当前还不需要这个功能
    db = client[mongo_dbname]
    collection = db[collection_name]

    # 确定查询条件
    query_condition = {}
    if qtimestamp is not None:
        query_condition = {'timestamp': {'$lt': int(qtimestamp)}}

    # 查询并排序数据
    query = collection.find(query_condition).sort('timestamp', -1).skip((page - 1) * limit).limit(limit)
    
    # 返回查询结果
    messages = []
    for record in query:
        name = record.get('name', '')
        message = record.get('message', '')
        
        timestamp_utc = datetime.utcfromtimestamp(record.get('timestamp', 0) // 10)
        beijing_tz = pytz.timezone('Asia/Shanghai')
        timestamp_beijing = timestamp_utc.replace(tzinfo=pytz.utc).astimezone(beijing_tz)
        
        formatted_time = timestamp_beijing.strftime('%Y-%m-%d %H:%M')
        date, time = formatted_time.split(' ')
        messages.append({
            'name': name,
            'message': message,
            'date': date,
            'time': time
        })
    
    return messages

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
