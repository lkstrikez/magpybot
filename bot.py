#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Import some necessary libraries.
from textwrap import wrap
import argparse
import logging.config

from client import BotSocket
from finder import CardFinder

SERVER = "irc.cat.pdx.edu"  # Server
CHANNEL = "#mtg"  # Channel
BOTNICK = "magpybot"  # Your bots nick


log_cfg = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'datefmt': '%Y.%m.%dT%H:%M:%S',
            'format': '%(asctime)s %(levelname)s l=%(name)s f=%(funcName)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'formatter': 'default',
            'class': 'logging.StreamHandler',
            'level': 'DEBUG'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'bot.log',
            'formatter': 'default',
            'delay': True,
            'level': 'DEBUG',
            'maxBytes': 10485760,
            'backupCount': 10
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG'
    }
}

logging.config.dictConfig(log_cfg)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Connect IRC bot for querying Magic: the Gathering card data")
    parser.add_argument("-s", "--server", type=str, default=SERVER)
    parser.add_argument("-c", "--channel", type=str, default=CHANNEL)
    parser.add_argument("-n", "--nick", type=str, default=BOTNICK)
    args = parser.parse_args()

    irc = BotSocket(args.server, 6667, args.nick)
    logger.info("Connected")

    finder = CardFinder("http://mtgjson.com/json/AllCards.json", 'cards.json')

    irc.join(args.channel)
    logger.info("Joined")

    if finder.fresh:
        irc.send_msg(args.channel, "Ready.")
    else:
        irc.send_msg(args.channel, "Error fetching data. Using last known good.")

    while True:  # Be careful with these! it might send you to an infinite loop
        irc_msg = irc.get_msg()
        logger.debug('Message received:\n%s', irc_msg)  # Here we print what's coming from the SERVER

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
                logger.info("Update")
                irc.send_msg(channel, "Updating card data...")
                finder.update()

                if finder.fresh:
                    logger.debug('Udate successful')
                    irc.send_msg(channel, "Card data updated.")
                else:
                    logger.warn('Error fetching updated data!')
                    irc.send_msg(channel, "Error fetching data. Using last known good.")

            elif "!source" in irc_msg:
                logger.info('Source request')
                irc.send_msg(channel, "My source code is at https://github.com/midnightlynx/magpybot")

            elif "!card " in irc_msg:
                # TODO: Implement "!card(<name>) inline syntax, or "!card <name> endcard!"
                name = irc_msg.split("!card ")[1].strip()
                logger.debug('Card query: "%s"', name)
                cards = finder.query(name)
                for card in cards:
                    for line in [l for chunk in card.splitlines() for l in wrap(chunk, max_length)]:
                        irc.send_msg(channel, line)

            elif "!momir " in irc_msg:
                cost = irc_msg.split("!momir ")[1].strip()
                logger.debug('Momir request, cost=%s', cost)
                try:
                    cost = int(cost)
                    if cost < 0:
                        raise ValueError
                    card = finder.momir(cost)
                    for line in [l for chunk in card.splitlines() for l in wrap(chunk, max_length)]:
                        irc.send_msg(channel, line)
                    logger.info('Momir cost %s found card:%s\n', cost, card)
                except ValueError:
                    logger.warn('Invalid Momir cost: "%s"', cost)
                    irc.send_msg(channel, "Momir has no time for your foolishness.")

if __name__ == '__main__':
    main()
