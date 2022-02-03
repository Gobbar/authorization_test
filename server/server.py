import socket
import json
from sqlite3.dbapi2 import Connection, connect
from typing import ByteString
from dbwork import DataBase
import hashlib
import queue
import threading

def authentication_req(data: tuple, db: DataBase) -> dict:
    return {"success": True, "result": "",  "data": {}, "message": "Write your authentication data"}


def authentication(data: tuple, db: DataBase) -> dict:
    data = data[0]
    user_data = db.get_user_data(data["login"])
    send_data = {"success": None, "result": "", "data": None, "message": None}
    if user_data == {}:
        send_data["success"] = False
        send_data["message"] = "Authentication goes wrong"
        return send_data
    current_pass = data["password"] + user_data["salt"]
    current_pass = hashlib.sha256(current_pass.encode()).hexdigest()


    if current_pass == user_data["password"]:
        send_data["success"] = True
        send_data["message"] = ""
        res = db.get_access_rights(user_data["id"])
        message = "Authentication was successful\nYour access rights list:\n"
        for i in range(res["length"]):
            obj = res["array"][i]
            key_list = ["canRead", "canWrite", "canDelegate"]
            sum = 0
            for key in key_list:
                sum += obj[key]
            if sum == 3:
                access = "Full access"
            elif sum == 0:
                access = "No access"
            else:
                access = ", ".join([key[3:] for key in key_list if obj[key]])
            message_line = "{0}{1}{2}{3}".format(obj["objectName"], ":\t", access, "\n")
            message += message_line
        send_data["message"] = message
    else:
        send_data["success"] = False
        #send_data["data"] = {"close_connection": True}
        send_data["message"] = "Authentication goes wrong"
    return send_data

def start_server():

    host = socket.gethostname()
    port = 5001

    server_socket = socket.socket()
    server_socket.bind((host, port))
    server_socket.listen(2)

    tasks_queue = queue.Queue()
    db_thread = threading.Thread(target=db_work, args=(tasks_queue,))
    db_thread.start()

    threads_arr = []
    connect_list = []
    socket_connection_thread = threading.Thread(target=socket_connection, args=(server_socket, connect_list))
    socket_connection_thread.start()
    while True: 
        if not(socket_connection_thread.is_alive()):
            socket_connection_thread.join()
            thread = threading.Thread(target=client_connection, args=(connect_list[0], tasks_queue)) 
            thread.start()
            threads_arr.append(thread)
            connect_list = []
            
            socket_connection_thread = threading.Thread(target=socket_connection, args=(server_socket, connect_list))
            socket_connection_thread.start()
        for thread in threads_arr:
            if not(thread.is_alive()):
                threads_arr.remove(thread)
                thread.join()
    db_thread.join()
    socket_connection_thread.join()
        
def socket_connection(server_socket: socket, connect_list: list):
        connection, address = server_socket.accept()
        connect_list.append(connection)
        return connection

def db_work(tasks_queue: queue):
    db = DataBase()

    while True:
        task = tasks_queue.get()
        data = task["function"](task["function_args"], db)
        task["callback"](task["callback_args"], data)

    # connection, address = server_socket.accept()
    # connection.send(json.dumps("1").encode())


    # print("Connection form: " + str(address))



        # data = connection.recv(1024).decode()
        # if not(data):
        #     break
        # print("User command: " + str(data))
        # data = input(' -> ')
        # connection.send(data.encode())
def  close_connection(data: dict, db: DataBase) -> dict:
    return {"success": True, "data": { "close_connection": True }, "message": "Close connection"}

def check_right(data: dict, db: DataBase) -> dict:
    data = data[0]
    right = data["right"]
    #right_level = data["data"]["right_level"]
    obj = data["object"]
    user = data["login"]
    send_data = db.check_right(right, obj, user)
    success = send_data[right] == 1
    if success:
        message = "Operation goes successfuly"
    else:
        message = "You haven't rights for this operation"


    return {"success": success, "data": send_data, "message": message}

def grant_right(data: dict, db: DataBase) -> dict:
    data = data[0]
    right = data["right"]
    obj = data["object"]
    user = data["login"]
    right_reciver = data["user"]
    right_level = data["right_level"]
    return db.grant_right(right, obj, user, right_reciver, right_level)


def client_connection(connection: socket, db_requests: queue):
    #db = DataBase()
    auth = {
        "Authentication": authentication,
        "AuthenticationReq": authentication_req,
    }
    commands = {
        "exit": close_connection,
        "read": check_right,
        "write": check_right,
        "grant": grant_right,
        "rights": ""
    }
    answers_queue = queue.Queue()
    print("open")
    is_authenticaficated = False 
    while not(is_authenticaficated):
        # a = connection.recv(1024).decode()
        # print(a)
        # client_data = json.loads(a)
        client_data = json.loads(connection.recv(1024).decode())
        if client_data["command"] in auth:
            # tuple_t = None
            # if client_data["command"] == "Authentication":
            #     tuple_t = (client_data["data"], connection, answers_queue)
            # else:
            #     tuple_t = (connection, answers_queue)
            db_requests.put(
            {
                "function": auth[client_data["command"]],
                "function_args": (client_data["data"], ),
                "callback": command_callback,
                "callback_args": (connection, answers_queue)
            })
            answer = answers_queue.get()
            is_authenticaficated =  client_data["command"] == "Authentication" and answer["success"]

    answer = None

    while True:
        client_data = connection.recv(1024).decode()
        print(client_data)
        client_data = json.loads(client_data)
        print(client_data)
        if client_data["command"] in commands:
            #answer = commands[client_data["command"]](client_data["data"], db)
            db_requests.put(
            {
                "function": commands[client_data["command"]],
                "function_args": (client_data["data"], ),
                "callback": command_callback,
                "callback_args": (connection, answers_queue)
            })
            answer = answers_queue.get()
            print(answer)
            #connection.send(json.dumps(answer).encode())
        else:
            send_data(connection, {"success": False, "data": {}, "message": "Sorry, wrong command"})

        if "close_connection" in answer["data"]:
            if bool(answer["data"]["close_connection"]):
                break
    print("close")
    connection.close()

def command_callback(callback_args: tuple, data: dict):
    connection = callback_args[0]
    thread_queue = callback_args[1]
    thread_queue.put(data)
    connection.send(json.dumps(data).encode())

def back_data_to_thread(thread_queue: queue, data: dict):
    thread_queue.put(data)

def send_data(connection: socket, data: dict):
    connection.send(json.dumps(data).encode())

if __name__ == "__main__":
    start_server()