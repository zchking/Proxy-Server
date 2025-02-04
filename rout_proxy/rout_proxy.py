import socket
from _thread import *
import ssl
import json


class ProxyServer:
    
    def __init__(self) -> None:
        self.PORT = 5000
        self.NETWORK = "0.0.0.0"
        self.BUFFERSIZE = 8124

    def start(self): # --> Used to start the proxy server
        
        suscket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        suscket.bind((self.NETWORK, self.PORT))
        suscket.listen(5) # --> Proxy is listening for max 5 clients
        
        print("[*] Proxy is running on {} and Port: {}".format(self.NETWORK, self.PORT))
        
        while True:
            client, address = suscket.accept()
            data = client.recv(self.BUFFERSIZE)
            print(data)
            print("[*] New connection from {}".format(address[0]))

            start_new_thread(self.get_request_data, (client, data)) # --> Starting new thread to get the request data
    
    def get_request_data(self, client:socket.socket, data:bytes):
        data_dec = data.decode().split("\r") # --> Seperating the request headers
        temp = data_dec[1].split(" ")[1].split(":") # --> Taking the second header (Where the host's address is loacated),
                                                          #splitting the "Host: " String from it and seperating the Hostaddr from the port

        port = 80
        if len(temp) > 1:
            server, port = temp
            port = int(port)
        else:
            server = temp[0]
            

        method, path, http_ver = data_dec[0].split(" ")

        if port != 443:
            path = path.replace("http://", "")
        elif method != "CONNECT":
            path = path.replace("https://", "")
        else:
            data = self.handle_connect(server, data_dec)


        if self.is_allowed(server, path):
            print("[*] Allowing request to {} on port: {}".format(server, port))
            start_new_thread(self.send_request_server, (server, port, data, client))
        else:
            print("[*] Blocked request to {} on port: {}".format(server, port))
            start_new_thread(self.load_block_info, (server, client))
        
    def send_request_server(self, server, port, data, client:socket.socket):

        with socket.create_connection((server, port)) as sock:
            if port == 443:
                ctxt = ssl.create_default_context()
                server_sock = ctxt.wrap_socket(sock, server_hostname=server)
                client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            else:
                server_sock = sock
            server_sock.sendall(data)

            response = b''
            while True:
                reply = server_sock.recv(self.BUFFERSIZE)
                if len(reply) == 0: # --> When the server stops sending data
                    break
                print(str("-" * 50))
                print(reply)
                print(str("-" * 50))
                response += reply
                
                if client.fileno() != -1:
                    try:
                        client.send(reply)
                    except (BrokenPipeError, ConnectionResetError):
                        break
                else:
                    break
        
        print("[*] Succesfully transmitted data")
        client.close()

    def is_allowed(self, server, path):
        with open("black_list.json") as json_data:
            data = json.load(json_data)
            return not server in data["hosts"]["address"] and path not in data["hosts"]["paths"]
        
    def load_block_info(self, server, client:socket.socket):
        with open("unnallowed_page/unnallowed.html") as html_data:
            html_text = html_data.read()
            text = "HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\nContent-Length: " + str(len(html_text)) + '\r\n\r\n' + html_text
            response = str(text).encode("utf-8")
        client.sendall(response)
        client.close()
        
    def handle_connect(self, server, data):
        user_agent = ''
        for line in data:
            if str(line).startswith('User-Agent:'):
                user_agent = line
        return f"GET / HTTP/1.1\r\nHost: {server}\r\n{user_agent}\r\nProxy-Connection: Keep-Alive\r\n\r\n".encode()

     
if __name__ == "__main__":
    ProxyServer().start()