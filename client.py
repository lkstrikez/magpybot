import socket


class BotSocket(object):
    def __init__(self, server, port, bot_nick):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((server, port))
        self.sock.send("USER {0} {0} {0} :This bot queries info for MTG cards.\n".format(bot_nick).encode('utf-8'))
        self.sock.send("NICK {}\n".format(bot_nick).encode('utf-8'))

    def join(self, chan):
        self.sock.send("JOIN {}\n".format(chan).encode('utf-8'))

    def ping(self):
        self.sock.send("PONG :pingis\n".encode('utf-8'))

    def send_msg(self, chan, msg):
        if chan and msg:
            self.sock.send("PRIVMSG {0} :{1}\n".format(chan, msg).encode('utf-8'))

    def get_msg(self):
        return self.sock.recv(2048).decode('utf-8').strip("\n\r ")

    def userhost(self, nick):
        if nick:
            self.sock.send("USERHOST {}".format(nick).encode('utf-8'))