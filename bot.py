#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Import some necessary libraries.
from textwrap import wrap
import argparse

from client import BotSocket
from finder import CardFinder

SERVER = "irc.cat.pdx.edu"  # Server
CHANNEL = "#mtg"  # Channel
BOTNICK = "magpybot"  # Your bots nick


def main():

    parser = argparse.ArgumentParser(description="Connect IRC bot for querying Magic: the Gathering card data")
    parser.add_argument("-s", "--server", type=str, default=SERVER)
    parser.add_argument("-c", "--channel", type=str, default=CHANNEL)
    parser.add_argument("-n", "--nick", type=str, default=BOTNICK)
    args = parser.parse_args()

    irc = BotSocket(args.server, 6667, args.nick)
    print("Connected")

    finder = CardFinder("http://mtgjson.com/json/AllCards.json", 'cards.json')

    irc.join(args.channel)
    print("Joined")

    if finder.fresh:
        irc.send_msg(args.channel, "Ready.")
    else:
        irc.send_msg(args.channel, "Error fetching data. Using last known good.")

    while True:  # Be careful with these! it might send you to an infinite loop
        irc_msg = irc.get_msg()
        print()
        print(irc_msg)  # Here we print what's coming from the SERVER

        if "PING " in irc_msg:
            irc.ping()

        elif " PRIVMSG " in irc_msg:
            nick = irc_msg.split('!')[0][1:]
            channel = irc_msg.split(' PRIVMSG ')[-1].split(' :')[0]
            if nick == args.nick:  # My own messages -- ignore.
                continue
            if channel == args.nick:  # private message
                channel = nick
            # Calculate line length. 447 = 510 - 63, presumed max host length.
            # TODO: Get actual "<nick>!<user>@<host>" length with USERHOST command
            max_length = 447 - len("{0}!~{0}@ PRIVMSG {1} :".format(args.nick, channel))

            if "!update" in irc_msg:
                print("Update")
                irc.send_msg(channel, "Updating card data...")
                finder.update()

                if finder.fresh:
                    irc.send_msg(channel, "Card data updated.")
                else:
                    irc.send_msg(channel, "Error fetching data. Using last known good.")

            elif "!source" in irc_msg:
                irc.send_msg(channel, "My source code is at https://github.com/midnightlynx/magpybot")

            elif "!card " in irc_msg:
                # TODO: Implement "!card(<name>) inline syntax, or "!card <name> endcard!"
                name = irc_msg.split("!card ")[1].strip()
                cards = finder.query(name)
                for card in cards:
                    print(card)
                    for line in [l for chunk in card.splitlines() for l in wrap(chunk, max_length)]:
                        irc.send_msg(channel, line)


if __name__ == '__main__':
    main()
