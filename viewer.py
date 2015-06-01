__author__ = 'RAEON'

import pygame
from pygame.locals import *

class Viewer(object):

    def __init__(self):
        pygame.init()

        # screen
        self.resolution = self.width, self.height = 640, 480
        self.screen = pygame.display.set_mode(self.resolution)

        # background
        self.background = pygame.Surface(self.resolution)
        self.background.convert()
        self.background.fill((0, 0, 0))

        # text
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 12)

    def run(self):
        while self.render():
            pass

    def render(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

        # draw background to screen
        self.screen.blit(self.background, (0, 0))

        # draw string
        text = self.font.render("text", 0, (255, 0, 0))
        text_rect = text.get_rect()
        text_rect.centerx = self.screen.get_rect().centerx
        text_rect.centery = self.screen.get_rect().centery
        self.screen.blit(text, text_rect)

        # draw circle
        pygame.draw.circle(self.screen, (255, 255, 255), (320, 120), 50)

        # flip
        pygame.display.flip()
        return True


from time import time, sleep
class GameViewer(object):

    def __init__(self, game):
        self.game = game

        # initialize pygame
        pygame.init()

        # screen
        self.resolution = self.width, self.height = 800, 800
        self.screen = pygame.display.set_mode(self.resolution)

        # background (black)
        self.background = pygame.Surface(self.resolution)
        self.background.convert()
        self.background.fill((0, 0, 0))

        # font
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 12)

        # fps
        self.frames = 0
        self.last_frames = 0
        self.timer = 0

    def run(self):
        while self.render():
            pass

    def render(self):
        scale = self.game.view_w / 800
        if scale == 0:
            scale = 2

        # handle events (user input)
        for event in pygame.event.get():
            if event.type == QUIT:
                return False
            elif event.type == MOUSEMOTION:
                x, y = event.pos
                x *= scale
                y *= scale
                for bot in self.game.bots:
                    #bot.send_move_relative(5, 5)
                    bot.send_move(x, y)
            elif event.type == KEYDOWN:
                if event.key == K_w:
                    for bot in self.game.bots:
                        bot.send_throw(1)
                elif event.key == K_SPACE:
                    for bot in self.game.bots:
                        bot.send_split(1)
                elif event.key == K_r:
                    for bot in self.game.bots:
                        bot.send_spawn()

        # handle output (rendering)

        # clear screen
        self.screen.blit(self.background, (0, 0))

        # draw cells
        values = self.game.cells.copy().values()
        for cell in values:
            # print('rendering thing:', cell)
            # draw circle
            # print('[cell]', cell.x/scale, cell.y/scale, cell.color, cell.size/scale, scale)

            # get our own smallest cells size
            smallest_size = 0
            for i in self.game.ids:
                c = self.game.get_cell(i)
                if c is not None:
                    if c.size > smallest_size:
                        smallest_size = c.size

            color = (0, 255, 0)  # green
            if smallest_size == cell.size:
                color = (255, 255, 0)  # yellow
            elif smallest_size < cell.size:
                color = (255, 0, 0)  # red

            # draw cell
            pygame.draw.circle(self.screen, cell.color, (int(cell.x/scale), int(cell.y/scale)), int(cell.size/scale))

            # draw name
            if cell.name is not '':
                # render name above cell
                text = self.font.render(cell.name, 0, color)
                text_rect = text.get_rect()
                text_rect.centerx = int(cell.x/scale)
                text_rect.centery = int((cell.y - cell.size)/scale - 5)
                self.screen.blit(text, text_rect)

                # render mass in cell
                text = self.font.render(str(round(cell.size)), 0, color)
                text_rect = text.get_rect()
                text_rect.centerx = int(cell.x/scale)
                text_rect.centery = int((cell.y + cell.size)/scale + 5)
                self.screen.blit(text, text_rect)


        # update fps
        self.frames += 1
        if time() - self.timer > 1:
            self.timer = time()
            self.last_frames = self.frames
            self.frames = 0

        self.draw_debug()
        # self.draw_leaderboard()

        # flip buffers
        pygame.display.flip()

        return True

    def draw_debug(self):
        # update fps
        self.frames += 1
        if time() - self.timer > 1:
            self.timer = time()
            self.last_frames = self.frames
            self.frames = 0

        lines = []
        lines.append('FPS: ' + str(self.last_frames))
        lines.append('Bot/Cell_IDs: ' + str(self.game.bots[0].ids))
        lines.append('Game/Cell_IDs: ' + str(self.game.ids))
        lines.append('Server: ' + self.game.host + ':' + str(self.game.port))
        lines.append('Pos: ' + str(self.game.bots[0].get_center()))
        self.draw_lines(lines)

    def draw_lines(self, lines):
        x = 5
        y = 5
        for line in lines:
            text = self.font.render(line, 0, (255, 255, 255))
            text_rect = text.get_rect()
            text_rect.left = x
            text_rect.top = y
            y += 10
            self.screen.blit(text, text_rect)

    def draw_leaderboard(self):
        ladder = self.game.ladder
        x = 800 - 5
        y = 5
        i = 0
        for name in ladder.values():
            i += 1
            text = self.font.render(name + ' #' + str(i), 0, (255, 255, 255))
            text_rect = text.get_rect()
            text_rect.right = x
            text_rect.top = y
            self.screen.blit(text, text_rect)
            y += 10
