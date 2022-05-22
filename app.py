from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, disconnect
import MySQLdb       
import time
import serial
import configparser as ConfigParser
import json

async_mode = None

app = Flask(__name__)

ser = serial.Serial("/dev/ttyUSB0", 9600)

config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 
db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)          


def background_thread(args):
    count = 0  
    dataCounter = 0 
    dataList = []  
    while True:
        if args:
            record = dict(args).get('record')
        else:
          record = 'nieco'  
        print(args)  
        socketio.sleep(1.5)
        count += 1
        dataCounter +=1
        timestamp = time.time() * 1000
        prem = float(ser.readline().decode("utf-8").rstrip())
        if record == 'start':
          dataDict = {
            "t": timestamp,
            "y": prem,
            }
          dataList.append(dataDict)
        else:
          if len(dataList)>0:
            print(str(dataList))
            fuj = str(dataList).replace("'", "\"")
            print(fuj)
            if(record == 'stopDB'):
                cursor = db.cursor()
                cursor.execute("SELECT MAX(id) FROM graph")
                maxid = cursor.fetchone()
                cursor.execute("INSERT INTO graph (id, hodnoty) VALUES (%s, %s)", (maxid[0] + 1, fuj))
                db.commit()
            elif(record == 'stopFILE'):
                fo = open("static/files/test.txt", "a+");
                fo.write("%s\r\n" %fuj);
          dataList = []
          dataCounter = 0
        socketio.emit('my_response',
                      {'data': prem, 'count': count, 't': timestamp},
                      namespace='/test')  
    db.close()

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode) 
    
@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    cursor = db.cursor()
    cursor.execute("SELECT id FROM graph")
    idsDB = cursor.fetchall()
    fo = open("static/files/test.txt", "r");
    idsFILE = len(fo.readlines())
    emit('my_response',
         {'data': message['value'], 'count': session['receive_count'], 'idsDB': idsDB, 'idsFILE': idsFILE, 'initial': 1})

@socketio.on('db_event', namespace='/test')
def db_message(message):
    print(message['value'] == 'startDB')
    if(message['value'] == 'startDB'):
        session['record'] = 'start'   
    else:
        session['record'] = 'stopDB'

@socketio.on('get_db_event', namespace='/test')
def get_db_message(message):
    cursor = db.cursor()
    cursor.execute("SELECT hodnoty FROM graph where id = %s", message['db_id'])
    data = cursor.fetchone()
    emit('db_response', {'data': data})
    
@socketio.on('file_event', namespace='/test')
def file_message(message):   
    if(message['value'] == 'startFILE'):
        session['record'] = 'start'   
    else:
        session['record'] = 'stopFILE' 

@socketio.on('get_file_event', namespace='/test')
def get_file_message(message):
    fo = open("static/files/test.txt", "r");
    rows = fo.readlines()
    data = rows[int(message['file_id'])-1]
    emit('file_response', {'data': data})

@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
