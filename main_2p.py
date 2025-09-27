#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Steve the Freakysaur — 2 Players (stacked lanes) with Winner Overlay
# + duo tongue restart: if BOTH players hold tongue out for 5s on game over, round resets.
#
# Layout matches main1: webcam (900x260) on top, game (900x560) below.
# P1 plays in the TOP lane, P2 in the BOTTOM lane. Round ends if EITHER dies.
#
# Controls:
#   P1 (top):   Space/Up = jump, Down = duck, Tongue index 0
#   P2 (bottom): W = jump,   S = duck,      Tongue index 1
#
# Requires: tongue_switch_2p.py (MultiTongueSwitch)

import os, sys, math, random, pygame
from tongue_switch_2p import MultiTongueSwitch, TONGUE_DEPS_OK

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# ---------------- helpers ----------------
def load_image(path: str) -> pygame.Surface:
    return pygame.image.load(path).convert_alpha()

def load_images(paths): return [load_image(p) for p in paths]

# ------------- sprites (lane-local coords) -------------
class Ground(pygame.sprite.Sprite):
    def __init__(self, ground_y_panel: int, speed: int):
        super().__init__()
        self.image = load_image(os.path.join(ASSETS_DIR, "Other", "Track.png"))
        self.h = self.image.get_height()
        self.y = ground_y_panel - self.h
        self.x1 = 0
        self.x2 = self.image.get_width()
        self.speed = speed

    def update(self, dt):
        move = int(self.speed * dt)
        self.x1 -= move; self.x2 -= move
        w = self.image.get_width()
        if self.x1 + w <= 0: self.x1 = self.x2 + w
        if self.x2 + w <= 0: self.x2 = self.x1 + w

    def draw(self, screen: pygame.Surface, offset):
        ox, oy = offset
        screen.blit(self.image, (self.x1 + ox, self.y + oy))
        screen.blit(self.image, (self.x2 + ox, self.y + oy))

class Cloud(pygame.sprite.Sprite):
    def __init__(self, panel_w, panel_h, speed, ground_y):
        super().__init__()
        self.image = load_image(os.path.join(ASSETS_DIR, "Other", "Cloud.png"))
        self.rect = self.image.get_rect()
        self.rect.x = panel_w + random.randint(0, 250)
        self.rect.y = random.randint(20, max(20, ground_y - 160))
        self.speed = speed * 0.4

    def update(self, dt):
        self.rect.x -= int(self.speed * dt)
        if self.rect.right < 0: self.kill()

class Dino(pygame.sprite.Sprite):
    RUN = [os.path.join(ASSETS_DIR,"Dino","DinoRun1.png"),
           os.path.join(ASSETS_DIR,"Dino","DinoRun2.png")]
    DUCK = [os.path.join(ASSETS_DIR,"Dino","DinoDuck1.png"),
            os.path.join(ASSETS_DIR,"Dino","DinoDuck2.png")]
    JUMP = [os.path.join(ASSETS_DIR,"Dino","DinoJump1.png"),
            os.path.join(ASSETS_DIR,"Dino","DinoJump2.png"),
            os.path.join(ASSETS_DIR,"Dino","DinoJump3.png"),
            os.path.join(ASSETS_DIR,"Dino","DinoJump4.png")]

    def __init__(self, ground_y_panel: int, x: int = 40, label: str = "P1", label_color=(30,110,255)):
        super().__init__()
        self.run_imgs  = load_images(self.RUN)
        self.duck_imgs = load_images(self.DUCK)
        self.jump_imgs = load_images(self.JUMP)
        self.dead_img  = load_image(os.path.join(ASSETS_DIR,"Dino","DinoDead.png"))

        self.index=0
        self.image=self.run_imgs[0]
        self.rect=self.image.get_rect()
        self.rect.x=x
        self.ground_y=ground_y_panel
        self.rect.bottom=self.ground_y

        # physics
        self.vel_y=0.0; self.gravity=2500.0; self.jump_speed=-900.0
        self.ducking=False; self.alive=True

        # animation
        self.anim_timer=0.0
        self.run_duck_rate=0.09
        self.jump_rate=0.07
        self.jump_index=0

        self.mask = pygame.mask.from_surface(self.image)

        # presentation
        self.label = label
        self.label_color = label_color

    def start_jump(self):
        if self.alive and abs(self.rect.bottom - self.ground_y) < 2:
            self.vel_y = self.jump_speed
            self.jump_index = 0
            self.anim_timer = 0.0

    def set_duck(self, on: bool):
        if self.alive:
            self.ducking = on and abs(self.rect.bottom - self.ground_y) < 2

    def _airborne(self) -> bool:
        return self.rect.bottom < self.ground_y - 1 or abs(self.vel_y) > 0.1

    def update(self, dt):
        if not self.alive: return

        self.vel_y += self.gravity * dt
        self.rect.y += int(self.vel_y * dt)

        if self.rect.bottom >= self.ground_y:
            self.rect.bottom = self.ground_y
            self.vel_y = 0.0

        self.anim_timer += dt
        bottom = self.rect.bottom

        if self._airborne():
            if self.anim_timer >= self.jump_rate:
                self.anim_timer -= self.jump_rate
                self.jump_index = (self.jump_index + 1) % len(self.jump_imgs)
            self.image = self.jump_imgs[self.jump_index]
        elif self.ducking:
            if self.anim_timer >= self.run_duck_rate:
                self.anim_timer -= self.run_duck_rate
                self.index = (self.index + 1) % 2
            self.image = self.duck_imgs[self.index]
        else:
            if self.anim_timer >= self.run_duck_rate:
                self.anim_timer -= self.run_duck_rate
                self.index = (self.index + 1) % 2
            self.image = self.run_imgs[self.index]

        self.rect = self.image.get_rect(midbottom=(self.rect.centerx, bottom))

        if self.ducking and not self._airborne():
            duck_surf = pygame.transform.smoothscale(
                self.image,
                (int(self.image.get_width()*0.9), int(self.image.get_height()*0.85))
            )
            pad = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            pad.blit(duck_surf, duck_surf.get_rect(center=pad.get_rect().center))
            self.mask = pygame.mask.from_surface(pad)
        else:
            self.mask = pygame.mask.from_surface(self.image)

    def die(self):
        if not self.alive: return
        self.alive=False
        bottom=self.rect.bottom
        self.image=self.dead_img
        self.rect=self.image.get_rect(midbottom=(self.rect.centerx,bottom))
        self.mask = pygame.mask.from_surface(self.image)

class Cactus(pygame.sprite.Sprite):
    SMALLS=[f"SmallCactus{i}.png" for i in (1,2,3)]
    LARGES=[f"LargeCactus{i}.png" for i in (1,2,3)]
    def __init__(self, ground_y_panel: int, speed: int, align_adjust: int=0):
        super().__init__()
        folder=os.path.join(ASSETS_DIR,"Cactus")
        name=random.choice(random.choice([self.SMALLS,self.LARGES]))
        self.image=load_image(os.path.join(folder,name))
        self.rect=self.image.get_rect()
        self.rect.bottom=ground_y_panel + align_adjust
        self.rect.x=900
        self.speed=speed
        self.mask = pygame.mask.from_surface(self.image)
    def update(self, dt):
        self.rect.x -= int(self.speed*dt)
        if self.rect.right < -50: self.kill()

class Bird(pygame.sprite.Sprite):
    FRAMES=[os.path.join(ASSETS_DIR,"Bird","Bird1.png"),
            os.path.join(ASSETS_DIR,"Bird","Bird2.png")]
    def __init__(self, speed:int, ground_y_panel:int):
        super().__init__()
        self.images=load_images(self.FRAMES)
        self.index=0; self.image=self.images[self.index]
        self.rect=self.image.get_rect()
        self.rect.x=900
        self.rect.y=random.choice([ground_y_panel-95, ground_y_panel-70, ground_y_panel-50])
        self.speed=speed+30
        self.anim_timer=0.0; self.anim_rate=0.09
        self.mask = pygame.mask.from_surface(self.image)
    def update(self, dt):
        self.anim_timer += dt
        if self.anim_timer >= self.anim_rate:
            self.anim_timer = 0.0
            self.index = 1 - self.index
            self.image = self.images[self.index]
            self.mask = pygame.mask.from_surface(self.image)
        self.rect.x -= int(self.speed*dt)
        if self.rect.right < -50: self.kill()

# ------------- lane (self-contained world) -------------
class Lane:
    def __init__(self, panel_w, panel_h, ground_y, speed, label, label_color):
        self.panel_w = panel_w
        self.panel_h = panel_h
        self.ground_y = ground_y
        self.speed = speed
        self.label = label
        self.label_color = label_color

        self.ground = Ground(self.ground_y, speed=self.speed)
        self.clouds = pygame.sprite.Group()
        self.obstacles = pygame.sprite.Group()
        self.dino = Dino(self.ground_y, x=40, label=label, label_color=label_color)

        # flow
        self.score = 0
        self.best  = 0
        self.spawn_timer = 0.0
        self.spawn_interval = 1.1
        self.cloud_timer = 0.0

    def reset(self):
        self.clouds.empty(); self.obstacles.empty()
        self.dino = Dino(self.ground_y, x=40, label=self.label, label_color=self.label_color)
        self.speed = 420
        self.score = 0
        self.spawn_timer = 0.0
        self.cloud_timer = 0.0
        self.ground = Ground(self.ground_y, speed=self.speed)

    def set_speed(self, spd):
        self.speed = spd
        self.ground.speed = spd
        for o in self.obstacles:
            if isinstance(o, Cactus): o.speed = spd
            else: o.speed = spd + 30

    def maybe_spawn_cloud(self, dt):
        self.cloud_timer += dt
        if self.cloud_timer > 1.5:
            self.cloud_timer = 0.0
            self.clouds.add(Cloud(self.panel_w, self.panel_h, self.speed, self.ground_y))

    def spawn_obstacle(self):
        if random.random() < 0.7:
            self.obstacles.add(Cactus(self.ground_y, self.speed, 0))
        else:
            self.obstacles.add(Bird(self.speed, self.ground_y))

    def update(self, dt):
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_obstacle()

        self.maybe_spawn_cloud(dt)
        self.dino.update(dt)
        self.obstacles.update(dt)
        self.clouds.update(dt)
        self.ground.update(dt)

        if self.dino.alive:
            self.score += dt * 120

    def collide_and_handle(self):
        if self.dino.alive and pygame.sprite.spritecollide(self.dino, self.obstacles, False, pygame.sprite.collide_mask):
            self.dino.die()
            self.best = max(self.best, int(self.score))
            return True
        return False

    def draw(self, screen, offset, font, font_small):
        ox, oy = offset
        for c in self.clouds: screen.blit(c.image, (c.rect.x + ox, c.rect.y + oy))
        self.ground.draw(screen, (ox, oy))
        for o in self.obstacles: screen.blit(o.image, (o.rect.x + ox, o.rect.y + oy))
        screen.blit(self.dino.image, (self.dino.rect.x + ox, self.dino.rect.y + oy))
        tag = font_small.render(self.label, True, self.label_color)
        screen.blit(tag, (self.dino.rect.centerx - tag.get_width()//2 + ox, self.dino.rect.top - 18 + oy))
        s = font.render(f"{self.label}: {int(self.score):05d}   Best: {self.best:05d}", True, (60,60,60))
        screen.blit(s, (ox + 10, oy + 10))

# ---------------- game ----------------
class Game:
    def __init__(self, use_tongue=True):
        pygame.init()
        pygame.display.set_caption("steve the freakysaur — 2P (stacked)")

        # Layout (match main1)
        self.cam_w, self.cam_h = 900, 260
        self.game_w, self.game_h = 900, 560
        self.win_w = self.cam_w
        self.win_h = self.cam_h + self.game_h

        self.cam_offset  = (0, 0)
        self.game_offset = (0, self.cam_h)

        self.screen = pygame.display.set_mode((self.win_w, self.win_h))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.font_small = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_big = pygame.font.SysFont("Arial", 40, bold=True)   # winner banner

        self.bg_cam  = pygame.Surface((self.cam_w,  self.cam_h ), pygame.SRCALPHA); self.bg_cam.fill((16,16,16))
        self.bg_game = pygame.Surface((self.game_w, self.game_h), pygame.SRCALPHA); self.bg_game.fill((247,247,247))

        # Split the game panel into two stacked lanes
        self.lane_h = self.game_h // 2  # 280
        lane_ground_y = 258             # fits in 280px lane (same as your main1)

        # Two independent lanes
        self.lane_top    = Lane(self.game_w, self.lane_h, lane_ground_y, speed=420, label="P1 (TOP)",    label_color=(30,110,255))
        self.lane_bottom = Lane(self.game_w, self.lane_h, lane_ground_y, speed=420, label="P2 (BOTTOM)", label_color=(230,100,30))

        # UI assets
        self.img_gameover = load_image(os.path.join(ASSETS_DIR,"Other","GameOver.png"))
        self.img_reset    = load_image(os.path.join(ASSETS_DIR,"Other","Reset.png"))

        # tongue
        self.use_tongue = use_tongue and TONGUE_DEPS_OK
        self.tongue=None
        if self.use_tongue:
            try:
                self.tongue = MultiTongueSwitch(show_window=False, preview_size=(self.cam_w, self.cam_h), mirror=True, max_players=2)
                self.tongue.start()
                print("[INFO] Tongue control ON (P1 left/top lane, P2 right/bottom lane). Keys also work.")
            except Exception as e:
                print("[WARN] Failed to start MultiTongueSwitch:", e)
                self.use_tongue=False

        self.game_over=False
        self.winner_text=""

        # --- NEW: duo tongue restart timer ---
        self.duo_hold = 0.0       # seconds both tongues have been held
        self.duo_target = 5.0     # need 5 seconds to restart

    # ----- helpers -----
    def reset(self):
        self.lane_top.reset()
        self.lane_bottom.reset()
        self.game_over=False
        self.winner_text=""
        self.duo_hold = 0.0

    def update_world_speed(self):
        # Use the higher score to ramp both lanes equally
        world_score = max(self.lane_top.score, self.lane_bottom.score)
        spd = 420 + int(world_score/80)
        self.lane_top.set_speed(spd)
        self.lane_bottom.set_speed(spd)

    # ----- drawing -----
    def draw_cam_panel(self):
        ox, oy = self.cam_offset
        self.screen.blit(self.bg_cam, (ox, oy))
        frame = self.tongue.get_preview_rgb() if self.tongue else None
        if frame is not None:
            fh, fw, _ = frame.shape
            scale = min(self.cam_w / fw, self.cam_h / fh)
            dw, dh = int(fw*scale), int(fh*scale)
            surf = pygame.image.frombuffer(frame.tobytes(), (fw, fh), "RGB")
            if (dw, dh) != (fw, fh):
                surf = pygame.transform.smoothscale(surf, (dw, dh))
            dx = ox + (self.cam_w - dw)//2
            dy = oy + (self.cam_h - dh)//2
            self.screen.blit(surf, (dx, dy))
        # HUD (right)
        if self.tongue:
            s1 = self.tongue.get_state(0)
            s2 = self.tongue.get_state(1)
            lbl = self.font_small.render(f"P1 Tongue: {'True' if s1 else 'False'}   P2 Tongue: {'True' if s2 else 'False'}", True, (230,230,230))
            self.screen.blit(lbl, (ox + self.cam_w - lbl.get_width() - 10, oy + 8))

    def draw_game_panel(self):
        ox, oy = self.game_offset
        self.screen.blit(self.bg_game, (ox, oy))
        pygame.draw.line(self.screen, (210,210,210), (ox, oy + self.lane_h), (ox + self.game_w, oy + self.lane_h), 2)

        self.lane_top.draw(self.screen,   (ox, oy + 0),           self.font, self.font_small)
        self.lane_bottom.draw(self.screen,(ox, oy + self.lane_h), self.font, self.font_small)

        if self.game_over:
            go_rect = self.img_gameover.get_rect(center=(ox + self.game_w//2, oy + self.game_h//2 - 40))
            rs_rect = self.img_reset.get_rect(center=(ox + self.game_w//2, oy + self.game_h//2 + 40))
            self.screen.blit(self.img_gameover, go_rect.topleft)
            self.screen.blit(self.img_reset, rs_rect.topleft)

            # Winner banner
            win = self.font_big.render(self.winner_text, True, (40,40,40))
            self.screen.blit(win, (ox + self.game_w//2 - win.get_width()//2, go_rect.top - 50))

            # Final scores line
            final = self.font.render(
                f"P1: {int(self.lane_top.score)}   |   P2: {int(self.lane_bottom.score)}",
                True, (60,60,60)
            )
            self.screen.blit(final, (ox + self.game_w//2 - final.get_width()//2, go_rect.bottom + 8))

            tip = self.font_small.render("Press Space / Up / W to play again", True, (80,80,80))
            self.screen.blit(tip, (ox + self.game_w//2 - tip.get_width()//2, rs_rect.bottom + 8))

            # --- NEW: duo tongue restart UI (progress bar + countdown) ---
            if self.tongue:
                both_on = self.tongue.get_state(0) and self.tongue.get_state(1)
                bar_w, bar_h = 300, 12
                bx = ox + self.game_w//2 - bar_w//2
                by = rs_rect.bottom + 36
                # outline
                pygame.draw.rect(self.screen, (120,120,120), (bx-1,by-1,bar_w+2,bar_h+2), 1)
                # fill
                pct = max(0.0, min(1.0, self.duo_hold / self.duo_target))
                pygame.draw.rect(self.screen, (60,180,90), (bx,by,int(bar_w*pct),bar_h))
                # label
                if both_on:
                    remain = max(0.0, self.duo_target - self.duo_hold)
                    lbl = self.font_small.render(f"Both tongues: hold {remain:.1f}s to restart", True, (60,60,60))
                else:
                    lbl = self.font_small.render("Both tongues: hold to restart", True, (60,60,60))
                self.screen.blit(lbl, (ox + self.game_w//2 - lbl.get_width()//2, by + bar_h + 6))

    # ----- loop -----
    def run(self):
        running=True
        while running:
            dt = self.clock.tick(60)/1000.0
            for e in pygame.event.get():
                if e.type==pygame.QUIT: running=False
                elif e.type==pygame.KEYDOWN:
                    if e.key==pygame.K_ESCAPE: running=False
                    if not self.game_over:
                        # P1 (TOP)
                        if e.key in (pygame.K_SPACE, pygame.K_UP): self.lane_top.dino.start_jump()
                        if e.key==pygame.K_DOWN: self.lane_top.dino.set_duck(True)
                        # P2 (BOTTOM)
                        if e.key==pygame.K_w: self.lane_bottom.dino.start_jump()
                        if e.key==pygame.K_s: self.lane_bottom.dino.set_duck(True)
                    else:
                        if e.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                            self.reset()
                elif e.type==pygame.KEYUP:
                    if e.key==pygame.K_DOWN: self.lane_top.dino.set_duck(False)
                    if e.key==pygame.K_s: self.lane_bottom.dino.set_duck(False)

            # tongue jumps (rising edge)
            if not self.game_over and self.tongue:
                if self.tongue.consume_rising_edge(0): self.lane_top.dino.start_jump()
                if self.tongue.consume_rising_edge(1): self.lane_bottom.dino.start_jump()

            # --- NEW: duo tongue restart timer (only on game-over screen) ---
            if self.tongue:
                both_on = self.tongue.get_state(0) and self.tongue.get_state(1)
                if self.game_over and both_on:
                    self.duo_hold = min(self.duo_target, self.duo_hold + dt)
                    if self.duo_hold >= self.duo_target:
                        self.reset()
                        # skip rest of loop this frame so UI updates cleanly after reset
                        self.screen.fill((22,22,22))
                        self.draw_cam_panel()
                        self.draw_game_panel()
                        pygame.display.flip()
                        continue
                else:
                    # reset timer if not both or not on game over screen
                    self.duo_hold = 0.0

            if not self.game_over:
                # update both lanes
                self.lane_top.update(dt)
                self.lane_bottom.update(dt)
                self.update_world_speed()

                # collide — end round immediately if EITHER dies
                dead_top = self.lane_top.collide_and_handle()
                dead_bot = self.lane_bottom.collide_and_handle()
                if dead_top or dead_bot:
                    self.game_over = True
                    # Decide winner right now using alive states after collision handling
                    top_alive = self.lane_top.dino.alive
                    bot_alive = self.lane_bottom.dino.alive
                    if top_alive and not bot_alive:
                        self.winner_text = "P1 WINS!"
                    elif bot_alive and not top_alive:
                        self.winner_text = "P2 WINS!"
                    else:
                        self.winner_text = "TIE!"

            # draw
            self.screen.fill((22,22,22))
            self.draw_cam_panel()
            self.draw_game_panel()
            pygame.display.flip()

        if self.tongue: self.tongue.stop()
        pygame.quit()

# ---------- entry ----------
def main():
    use_tongue = True
    if "--no-tongue" in sys.argv:
        use_tongue=False
    Game(use_tongue=use_tongue).run()

if __name__=="__main__":
    main()
