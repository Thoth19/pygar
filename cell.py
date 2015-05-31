__author__ = 'RAEON'

class Cell(object):

    def __init__(self, id, x, y, size, color, virus, agitated, name):
        self.id = id
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.virus = virus
        self.agitated = agitated
        self.name = name
        self.watchers = []
        self.owner = None
        self.timestamp = None

    def update_timestamp(self, timestamp):
        if self.timestamp < timestamp:
            self.timestamp = timestamp
            return True
        return False

    def add_watcher(self, watcher):
        if not watcher in self.watchers:
            self.watchers.append(watcher)
            return True
        return False

    def remove_watcher(self, watcher):
        if watcher in self.watchers:
            self.watchers.remove(watcher)
            return True
        return False

    def has_watcher(self, watcher):
        return watcher in self.watchers

    def has_watchers(self):
        return len(self.watchers) > 0