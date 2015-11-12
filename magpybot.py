#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Import some necessary libraries.
import json
import requests
import socket
from trans import trans

SERVER = "irc.cat.pdx.edu"  # Server
CHANNEL = "#mtgderp"  # Channel
BOTNICK = "magpybot"  # Your bots nick


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


def find_cards(cards, card_name):
    names = trans(card_name).split("//")
    return [cards[n.strip().lower()] for n in names if n.strip().lower() in cards]


def dictify(card):
    fields = ['type', 'name', 'names', 'cmc', 'manaCost', 'loyalty', 'text', 'power', 'toughness', 'hand', 'life']
    key = trans(card['name']).lower()
    value = dict([(k, v) for k, v in card.items() if k in fields])
    return key, value


def get_card_data():
    r = requests.get("http://mtgjson.com/json/AllCards.json")
    if r.status_code != 200:
        with open('cards.json') as reader:
            old = json.load(reader)
        return {'status': 'error', 'data': old}
    response = r.json()
    new = dict([dictify(v) for v in response.values()])
    with open('cards.json', 'w') as writer:
        json.dump(new, writer)
    return {'status': 'OK', 'data': new}


def line_break(text):
    line = []
    words = text.split()
    while words and len(" ".join(line)) <= 255:
        line.append(words.pop(0))

    # Move last word back over
    words.insert(0, line.pop(-1))
    return " ".join(line), " ".join(words)


def card_to_messages(card):
    name_line = "*** {}".format(card['name'])
    if 'names' in card:
        name_line = " ".join([name_line, "({})".format(" // ".join(card['names']))])

    info_line = card['type']

    if 'power' in card and 'toughness' in card:
        stats = "{}/{}".format(card['power'], card['toughness'])
        info_line = " ".join([info_line, stats])

    misc = []
    if 'loyalty' in card:
        misc.append("Loyalty: {}".format(card['loyalty']))
    if 'life' in card:
        misc.append("Life: {}".format(card['life']))
    if 'hand' in card:
        misc.append("Hand: {}".format(card['hand']))
    other = ", ".join(misc)
    if other:
        info_line = " ".join([info_line, "({})".format(other)])

    if 'cmc' in card and 'manaCost' in card:
        cost = card['manaCost'].replace("}", "").replace("{", "")
        info_line = ", ".join([info_line, "{} ({})".format(cost, card['cmc'])])

    lines = [name_line, info_line]

    if card.get('text'):
        for l in card['text'].splitlines():
            text_line = l
            while len(text_line) > 255:
                this_line, remainder = line_break(text_line)
                lines.append(this_line)
                text_line = remainder
            lines.append(text_line)

    return [l for l in lines if l]


def card_query(cards, msg, max_length):
    card_name = msg.split("!card ")[-1].strip()
    if not card_name:
        print("Card query: No name")
        return ["Yes...?"]
    else:
        results = find_cards(cards, card_name)
        if not results:
            print("Card query: No cards found: {}".format(card_name))
            return ["Oracle has no time for your games."]
        else:
            print("Cards Query: Found {}".format(card_name))
            messages = []
            for card in results:
                messages.extend(card_to_messages(card))
                if len(results) > 1:
                    messages.append("---")
            if len(results) > 1 and messages[-1] == "---":
                messages.pop(-1)
            return messages


def main():

    irc = BotSocket(SERVER, 6667, BOTNICK)
    print("Connected")
    card_data = get_card_data()
    cards = card_data['data']

    irc.join(CHANNEL)
    print("Joined")

    if card_data['status'] != 'OK':
        irc.send_msg(CHANNEL, "Error fetching data. Using last known good.")
    else:
        irc.send_msg(CHANNEL, "Ready.")
    while True:  # Be careful with these! it might send you to an infinite loop
        irc_msg = irc.get_msg()
        print()
        print(irc_msg)  # Here we print what's coming from the SERVER

        if "PING " in irc_msg:
            irc.ping()

        elif " PRIVMSG " in irc_msg:
            nick = irc_msg.split('!')[0][1:]
            channel = irc_msg.split(' PRIVMSG ')[-1].split(' :')[0]
            if nick == BOTNICK:  # My own messages -- ignore.
                continue
            if channel == BOTNICK:  # private message
                channel = nick
            # Calculate line length
            max_length = 447 - len("{0}!~{0}@ PRIVMSG {1} :".format(BOTNICK, channel))

            if "!card " in irc_msg:
                for line in card_query(cards, irc_msg, max_length):
                    irc.send_msg(channel, line)

            elif "!update" in irc_msg:
                print("Update")
                irc.send_msg(channel, "Updating card data...")
                card_data = get_card_data()
                cards = card_data['data']

                if card_data['status'] != 'OK':
                    irc.send_msg(channel, "Error fetching data. Using last known good.")
                else:
                    irc.send_msg(channel, "Card data updated.")


if __name__ == '__main__':
    main()
