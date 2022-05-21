from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, disconnect
import MySQLdb       
import time
import serial
import configparser as ConfigParser

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


def background_thread(args):
    count = 0  
    dataCounter = 0 
    dataList = []  
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)          
    while True:
        if args:
          dbV = dict(args).get('db_value')
        else:
          dbV = 'nieco'  
        print(dbV) 
        print(args)  
        socketio.sleep(2)
        count += 1
        dataCounter +=1
        prem = float(ser.readline().decode("utf-8").rstrip())
        if dbV == 'start':
          dataDict = {
            "t": time.time(),
            "y": prem,
            }
          dataList.append(dataDict)
        else:
          if len(dataList)>0:
            print(str(dataList))
            fuj = str(dataList).replace("'", "\"")
            print(fuj)
            cursor = db.cursor()
            cursor.execute("SELECT MAX(id) FROM graph")
            maxid = cursor.fetchone()
            cursor.execute("INSERT INTO graph (id, hodnoty) VALUES (%s, %s)", (maxid[0] + 1, fuj))
            db.commit()
          dataList = []
          dataCounter = 0
        socketio.emit('my_response',
                      {'data': prem, 'count': count},
                      namespace='/test')  
    db.close()

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode) 
    
@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    emit('my_response',
         {'data': message['value'], 'count': session['receive_count']})

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
