import socket, time
s = socket.socket()
s.connect(('127.0.0.1', 8888))
for i in range(20):
    s.send(b'ping')
    print(f'{i}: {s.recv(1024)}')
    time.sleep(0.5)