__author__ = 'RAEON'

from session import Session
from buffer import Buffer
from cell import Cell
import random
import time

class Bot(object):

    def __init__(self, game):
        self.game = game

        # core variables
        # self.running = False  # no point, is there? we have is_connected() and is_alive()
        # self.thread = None  # instances are updated by their Game or Server if no game has been found yet
        self.session = Session()
        self.buffer = Buffer()

        # game information
        self.name = 'Test'  #''.join([random.choice('0123456789abcdefghijlkmnopqrstuvwxyz') for i in range(8)])
        self.last_x = 0  # last sent mouse X coordinate
        self.last_y = 0  # last sent mouse Y coordinate
        self.view_x = 0  # viewport x
        self.view_y = 0  # viewport y
        self.view_w = 0  # viewport width
        self.view_h = 0  # viewport height

        # our state
        self.has_sent_init = False
        self.last_sent_spawn = 0
        self.last_update = 0

        # cell information
        self.ids = []  # list of ids (to get cell, query id in all_cells)
        self.stamps = {}  # maps cell id to cell
        self.ladder = []
        self.mode = 'ffa'

    def connect(self, host, port):
        if not self.is_connected() and (time.time() - self.game.last_connect > 15):
            if self.session.connect(host, port):
                print('[' + self.name + '] Connected')
                # reset game variables
                self.last_x = 0
                self.last_y = 0
                self.view_x = 0
                self.view_y = 0
                self.view_w = 0
                self.view_h = 0

                # reset some more variables
                self.game.last_connect = time.time()
                self.has_sent_init = False
                self.last_sent_spawn = 0

                # clear our lists
                self.ids = []
                self.stamps = {}
                self.ladder = {}

                # try and become ALIIIIVE!
                self.send_init()
                self.send_spawn()
                self.send_move_relative(0, 0)  # cuz fuck moving, thats why
                return True
            print('[' + self.name + '] Failed to connect')
        return False

    def disconnect(self):
        if self.is_connected():
            # disconnect
            self.session.disconnect()

            # remove all bot.ids from game.ids
            for id in self.ids:
                self.game.remove_id(id)

            # remove watcher from all seen cells
            for id, stamp in self.stamps.items():
                # get cell
                cell = self.game.get_cell(id)

                # remove watcher
                cell.remove_watcher(self)

                # if we were the owner, remove owner tag
                if self.has_id(id):
                    cell.owner = None

                # dont remove cell if unwatched: it would be redundant
                # game.update removes it for us
            return True
        return False

    def update(self):
        # connect if not connected
        if not self.is_connected():
            self.connect(self.game.host, self.game.port)
            return False

        # spawn if not alive
        if not self.is_alive():
            self.send_spawn()
            # dont return: if we do, we dont parse spawn packet

        # get all data
        all = []
        all.extend(self.session.inbound)
        self.session.inbound = self.session.inbound[len(all):]

        # parse all data
        for data in all:
            self.buffer.fill(data)
            packet = self.buffer.read_byte()
            self.parse_packet(packet)

        if not self.last_update == self.game.timestamp:
            # if we didn't receive an update this tick, we dont need to check for destroys.
            return

        # remove dead cells
        destroy = []
        for id, stamp in self.stamps.items():
            if stamp < self.game.timestamp:
                # print('[' + self.name + '] losing track of cell #' + str(id) + ': stamp=' + str(stamp) + ', gamestamp=' + str(self.game.timestamp))
                destroy.append(id)

        for id in destroy:
            # remove local timestamp
            self.remove_stamp(id)

            # tell game we arent watching the cell anymore
            cell = self.game.get_cell(id)
            cell.remove_watcher(self)

            # check if it was us who died
            if self.has_id(cell.id):
                self.remove_id(cell.id)
                self.game.remove_id(cell.id)
                print('[bot/update] lost cell', cell.id)
                if len(self.ids) == 0:
                    self.send_spawn()
                    print('[bot/update] respawning')


            # dont remove global_cell, game will do this on it's own
            # print('[' + self.name + '] lost track of cell #' + str(id))
        return True

    def act(self):
        # todo: write AI
        pass

    def parse_packet(self, id):
        b = self.buffer
        if id == 16:
            self.last_update = self.game.timestamp
            self.parse_mergers()
            self.parse_updates()
            self.parse_alives()
        elif id == 17:
            x = b.read_float()
            y = b.read_float()
            ratio = b.read_float()
            print('[17]', x, y, ratio)
        elif id == 20:
            for id in self.ids:
                self.game.remove_id(id)
            self.ids = []

            for id in self.stamps:
                cell = self.game.get_cell(id)
                cell.remove_watcher(self)
            self.stamps = []
            print('[20]')
        elif id == 32:
            id = b.read_int()
            self.add_id(id)
            self.game.add_id(id)
            print('[32]', id)
        elif id == 49:
            self.ladder = {}
            self.mode = 'ffa'
            amount = b.read_int()
            for i in range(0, amount):
                id = b.read_int()
                self.ladder[id] = b.read_string()

            self.game.ladder = self.ladder.copy()
            self.game.mode = 'ffa'
            #print('[49]')
        elif id == 50:
            # the 3rd ladder version, original was 48 (non-indexed ladder), 49 (indexed) and now 50
            self.ladder = []
            count = b.read_int()
            for i in range(0, count):
                self.ladder.append(b.read_float())

            if len(self.game.ladder) == 0:
                self.game.ladder = self.ladder.copy()
                self.game.mode = 'teams'
            #print('[50]')
        elif id == 64:
            print('[64] viewport')
            self.game.view_x = self.view_x = b.read_double()
            self.game.view_y = self.view_y = b.read_double()
            self.game.view_w = self.view_w = b.read_double()
            self.game.view_h = self.view_h = b.read_double()


    def parse_mergers(self):
        amount = self.buffer.read_short()
        for i in range(0, amount):
            hunter, prey = self.buffer.read_int(), self.buffer.read_int()
            if hunter in self.stamps and prey in self.stamps:  # if we both know these cells
                # no point in updating hunter's stamp, because it will be updated in parse_updates.

                # remove timestamp for eaten cell
                self.remove_stamp(prey)

                # remove eaten cell from global cells
                cell = self.game.get_cell(prey)  # prey = prey_id
                self.game.remove_cell(prey)

                # remove cell id if it is our own
                if self.has_id(cell.id):
                    self.remove_id(cell.id)

                # remove cell id if it is in game.ids
                if self.game.has_id(cell.id):
                    self.game.remove_id(cell.id)

                print('[game/parse_mergers] %d ate %d' % (hunter, prey))

    def parse_updates(self):
        b = self.buffer
        while True:
            id = b.read_int()

            if id == 0:
                break

            x = b.read_short()
            y = b.read_short()
            size = b.read_short()

            red = b.read_byte()
            green = b.read_byte()
            blue = b.read_byte()

            color = (red, green, blue)

            byte = b.read_byte()

            virus = (byte & 1)
            agitated = (byte & 16)  # what is this?

            # skipping bytes, no idea what the purpose is
            if (byte & 2):
                b.skip(4)
            elif (byte & 4):
                b.skip(8)
            elif (byte & 8):
                b.skip(16)

            # read name
            name = b.read_string()

            # check if this cell is known locally
            if self.has_stamp(id):
                # known locally
                # from that, we can conclude it is known globally

                # update local timestamp
                self.update_stamp(id, self.game.timestamp)

                # update global cell
                cell = self.game.get_cell(id)
                cell.x = x
                cell.y = y
                cell.size = size
                cell.color = color
                cell.virus = virus
                cell.agitated = agitated
                cell.timestamp = self.game.timestamp
            else:
                # not known locally

                # create local timestamp
                self.add_stamp(id, self.game.timestamp)

                if self.game.has_cell(id):
                    # not known locally (but already added)
                    # known globally

                    # update global cell
                    cell = self.game.get_cell(id)
                    cell.add_watcher(self)  # add ourselves as watcher (because it wasnt know locally)
                    cell.x = x
                    cell.y = y
                    cell.size = size
                    cell.color = color
                    cell.virus = virus
                    cell.agitated = agitated
                    cell.timestamp = self.game.timestamp

                    # check if cell is ours. this can happen when another bot sees this cell
                    # before we do, yet it is in our id list.
                    if self.has_id(id):
                        cell.owner = self
                        self.game.add_id(id)
                else:
                    # not known locally (but already added)
                    # not known globally

                    # create global cell instance
                    cell = Cell(id, x, y, size, color, virus, agitated, name)
                    cell.watchers.append(self)
                    cell.timestamp = self.game.timestamp

                    # add global cell to global cell list
                    self.game.add_cell(cell)

                    # check if cell is ours. if so, change owner and call game.on_bot_spawn
                    if self.has_id(id):
                        cell.owner = self
                        self.game.add_id(id)

    def parse_alives(self):
        if self.buffer.input_size() <= 0:
            return 
        print("parse_alives bytes: " + str(self.buffer.input_size())) 
        amount = self.buffer.read_int()
        print("parse_alives amount: " + str(amount))
        alives = []
        for i in range(0, amount):
            print("parse_alives current: " + str(i))
            id = self.buffer.read_int()
            if self.has_stamp(id):  # why are we checking if we know it?.. if we dont, we cant update timestamp
                # update timestamp
                self.update_stamp(id, self.game.timestamp)

                # update global cells timestamp
                cell = self.game.get_cell(id)
                cell.timestamp = self.game.timestamp

                # append etc
                alives.append(id)
        return alives

    def send_init(self):
        if self.is_connected() and not self.has_sent_init:
            self.has_sent_init = True

            self.buffer.write_byte(254)
            self.buffer.write_int(4)
            self.buffer.flush_session(self.session)

            self.buffer.write_byte(255)
            self.buffer.write_int(1)
            self.buffer.flush_session(self.session)
            return True
        return False

    def send_spawn(self):
        if self.is_connected() and (time.time() - self.last_sent_spawn > 4):
            #not self.is_alive() and \
            self.last_sent_spawn = time.time()
            self.buffer.write_string(self.name)
            self.buffer.flush_session(self.session)
            return True
        return False

    def send_move(self, x, y):
        if self.is_connected() and self.is_alive():
            if not (self.last_x == x and self.last_y == y):
                # update our last variables
                self.last_x = x
                self.last_y = y

                # send new coordinates
                self.buffer.write_byte(16)
                self.buffer.write_double(x)
                self.buffer.write_double(y)
                self.buffer.write_int(0)

                # flush
                self.buffer.flush_session(self.session)

                return True
        return False

    def send_move_relative(self, rel_x, rel_y):
        x, y = self.get_center()
        x += rel_x
        y += rel_y
        return self.send_move(x, y)

    def send_split(self, times=1):
        if self.is_connected() and self.is_alive():
            for i in range(0, times):
                self.buffer.write_byte(17)
                self.buffer.flush_session(self.session)
            return True
        return False

    def send_throw(self, times=1):
        if self.is_connected() and self.is_alive():
            for i in range(0, times):
                self.buffer.write_byte(21)
                self.buffer.flush_session(self.session)
            return True
        return False

    def send_spectate(self):
        if self.is_connected():
            self.buffer.write_byte(1)
            self.buffer.flush_session(self.session)
            return True
        return False

    def get_center(self):
        x = 0
        y = 0
        amount = max(1, len(self.ids))  # prevent div by zero
        for id in self.ids:
            cell = self.game.get_cell(id)
            if cell:
                x += cell.x
                y += cell.y
            else:
                amount -= 1
        return x/amount, y/amount

    def get_mass(self):
        mass = 0
        for id in self.ids:
            cell = self.game.get_cell(id)
            if cell:
                mass += cell.size
        return mass

    def is_alive(self):
        return len(self.ids) > 0

    def is_connected(self):
        return self.session.is_connected()

    def add_id(self, id):
        if not self.has_id(id):
            self.ids.append(id)
            return True
        return False

    def remove_id(self, id):
        if self.has_id(id):
            self.ids.remove(id)
            return True
        return False

    def has_id(self, id):
        return id in self.ids

    def add_stamp(self, id, stamp):
        if not self.has_stamp(id):
            self.stamps[id] = stamp
            return True
        return False

    def remove_stamp(self, id):
        if self.has_stamp(id):
            del self.stamps[id]
            return True
        return False

    def update_stamp(self, id, stamp):
        if self.has_stamp(id):
            self.stamps[id] = stamp
            return True
        return False

    def get_stamp(self, id):
        if self.has_stamp(id):
            return self.stamps[id]
        return None

    def has_stamp(self, id):
        return id in self.stamps

