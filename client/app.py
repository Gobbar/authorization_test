import socket
import json

def client_program(): 
    host = socket.gethostname() # as both code is running on same pc 
    port = 5001 # socket server port number 

    client_socket = socket.socket() # instantiate 
    client_socket.connect((host, port)) # connect to the server 
    is_auth = False
    
    send_data = json.dumps({"command": "AuthenticationReq", "data": {}}).encode()
    print("Authentication request send")
    client_socket.send(send_data)
    data = client_socket.recv(1024).decode()

    while not(is_auth):

        login = input("Connected. Enter the login: ")
        password = input("Enter the password: ")
        data = {"command": "Authentication", "data": {"login": login, "password": password} }
        client_socket.send(json.dumps(data).encode())
        data = json.loads(client_socket.recv(1024).decode())
        print_answer(data)
        
        is_auth = data["success"]

    
    while True: 
        data = {"login": login}
        message = input(" -> ") # take input 
        if "read" in message:
            message = message.split(' ')
            data.update({"object": message[1], "right": "CanRead"})
            message = message[0]
        if "write" in message:
            message = message.split(' ')
            data.update({"object": message[1], "right": "CanWrite"})
            message = message[0]
        if "grant" in message:
            message = message.split(' ')
            data.update({"object": message[2], "right": message[3], "user": message[1], "right_level": message[4]})
            message = message[0]
        send_data = {
            "data": data,
            "command": message
        }
        #print(send_data)
        client_socket.send(json.dumps(send_data).encode()) # send message 
        answer = json.loads(client_socket.recv(1024).decode()) # receive response  

        print_answer(answer)

        if message == "exit":
            break
        #if "close_connection" in answer["data"]:
        #    if bool(answer["data"]["close_connection"]):
        #        break
        #print('Received from server: ' + data) # show in terminal 
        
        #message = input(" -> ") # again take input 

    client_socket.close() # close the connection 

def print_answer(answer: str):
    message = answer["message"].split("\n")
    for line in message:
        print(line)

if __name__ == '__main__':
    client_program()
