import json

import requests
from trans import trans


class CardFinder(object):
    def __init__(self, source_url, filename):
        self.source = source_url
        self.file = filename
        self.data, self.fresh = self._update_data()

    def _update_data(self):
        r = requests.get(self.source)
        if r.status_code != 200:
            with open(self.file) as reader:
                return json.load(reader), False

        response = r.json()
        new = dict([self._dictify(v) for v in response.values()])
        with open(self.file, 'w') as writer:
            json.dump(new, writer)
        return new, True

    def update(self):
        self.data, self.fresh = self._update_data()
        return self.fresh

    def query(self, card_name):
        if not card_name:
            print("Card query: No name")
            return ["Yes...?"]
        else:
            results = self._find_cards(card_name)
            if not results:
                print("Card query: No cards found: {}".format(card_name))
                return ["Oracle has no time for your games."]
            else:
                print("Cards Query: Found {}".format(card_name))
                return [self._card_to_messages(card) for card in results]

    def _find_cards(self, card_name):
        names = trans(card_name).split("//")
        return [self.data[n.strip().lower()] for n in names if n.strip().lower() in self.data]

    @staticmethod
    def _dictify(card):
        fields = ['type', 'name', 'names', 'cmc', 'manaCost', 'loyalty', 'text', 'power', 'toughness', 'hand', 'life']
        key = trans(card['name']).lower()
        value = dict([(k, v) for k, v in card.items() if k in fields])
        return key, value

    @staticmethod
    def _card_to_messages(card):
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
        header = " *** ".join([l for l in [name_line, info_line] if l])
        return "\n".join([l for l in [header, card.get('text')] if l])
