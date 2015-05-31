__author__ = 'RAEON'

from game import Game
import threading
import requests

class Server(object):

    def __init__(self):
        self.running = False
        self.thread = None

        self.host = ''
        self.port = ''

        self.games = []
        self.bots = []

        self.tmp_game = None
        self.tmp_bots = 0

    def start(self, host=None, port=None):
        if not self.is_running():

            if host == None or port == None:
                try:
                    req = requests.post('http://m.agar.io', data='EU-London')
                    a, b = req.text.split(':')
                    host = a
                    port = b
                except:
                    return False

            self.running = True

            self.host = host
            self.port = port

            for game in self.games:
                game.start(host, port)

            self.tmp_game = Game(self)
            self.tmp_game.start(host, port)

            self.thread = threading.Thread(name='ServerThread', target=self.update)
            self.thread.start()
            return True
        return False

    def stop(self):
        if self.is_running():
            self.running = False

            for game in self.games:
                game.stop()

            self.tmp_game.stop()
            return True
        return False

    def update(self):
        while self.is_running() and self.thread == threading.current_thread():
            if self.tmp_game.get_bot_count() == 0 and self.tmp_bots > 0:
                self.tmp_bots -= 1
                self.tmp_game.add_bot()
                continue

            if len(self.tmp_game.ladder) > 0:
                # ladder has been established
                # compare ladder to active game
                game = self.get_game(self.tmp_game.ladder)
                if game:
                    self.tmp_game.transfer(game)
                    print('[server] transferred temporary bot to existing Game')
                    continue

                # no game found
                game = Game(self)
                game.start(self.host, self.port)
                self.games.append(game)
                self.tmp_game.transfer(game)
                print('[server] transferred temporary bot to new Game')
                # done!

    def create_game(self, bot):
        if not self.has_game(bot.ladder):
            game = Game(self)
            game.ladder = bot.ladder
            bot.game.transfer(game)
            self.games.append(game)
            return game
        return None

    def get_game(self, ladder):
        for game in self.games:
            if game.compare_ladders(ladder) >= 70:
                return game
        return None

    def has_game(self, ladder):
        return not (self.get_game(ladder) == None)

    def is_running(self):
        return self.running

    def add_bot(self):
        if self.tmp_game.get_bot_count() == 0:
            self.tmp_game.add_bot()
        else:
            self.tmp_bots += 1
