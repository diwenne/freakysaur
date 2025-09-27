#!/usr/bin/env python3
import os, sys, random, pygame, numpy as np

try:
    from tongue_switch import TongueSwitch
    TONGUE_AVAILABLE = True
except Exception as e:
    print("[WARN] Tongue switch unavailable:", e)
    TONGUE_AVAILABLE = False

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# ---------------- helpers ----------------
def load_image(path: str) -> pygame.Surface:
    return pygame.image.load(path).convert_alpha()

def load_images(paths): return [load_image(p) for p in paths]

# ------------- sprites (game-panel coords) -------------
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
    def __init__(self, ground_y_panel: int):
        super().__init__()
        self.run_imgs = load_images(self.RUN)
        self.duck_imgs = load_images(self.DUCK)
        self.jump_img = load_image(os.path.join(ASSETS_DIR,"Dino","DinoJump.png"))
        self.dead_img = load_image(os.path.join(ASSETS_DIR,"Dino","DinoDead.png"))
        self.index=0
        self.image=self.run_imgs[0]
        self.rect=self.image.get_rect()
        self.rect.x=40
        self.ground_y=ground_y_panel
        self.rect.bottom=self.ground_y

        self.vel_y=0.0; self.gravity=2500.0; self.jump_speed=-900.0
        self.ducking=False; self.alive=True
        self.anim_timer=0.0; self.anim_rate=0.09
        self.mask = pygame.mask.from_surface(self.image)

    def start_jump(self):
        if self.alive and abs(self.rect.bottom - self.ground_y) < 2:
            self.vel_y = self.jump_speed

    def set_duck(self, on: bool):
        if self.alive: self.ducking = on and abs(self.rect.bottom - self.ground_y) < 2

    def update(self, dt):
        if not self.alive: return
        self.vel_y += self.gravity * dt
        self.rect.y += int(self.vel_y * dt)
        if self.rect.bottom >= self.ground_y:
            self.rect.bottom = self.ground_y; self.vel_y = 0.0

        self.anim_timer += dt
        if self.anim_timer >= self.anim_rate:
            self.anim_timer -= self.anim_rate
            self.index = (self.index + 1) % 2

        bottom = self.rect.bottom
        if self.rect.bottom < self.ground_y - 1:
            self.image = self.jump_img
        elif self.ducking:
            self.image = self.duck_imgs[self.index]
        else:
            self.image = self.run_imgs[self.index]
        self.rect = self.image.get_rect(midbottom=(self.rect.centerx, bottom))

        if self.ducking:
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

# ---------------- game ----------------
class Game:
    def __init__(self, use_tongue=True):
        pygame.init()
        pygame.display.set_caption("steve the freakysaur")

        # Layout: TOP = webcam panel, BOTTOM = game panel
        self.cam_w, self.cam_h = 900, 260
        self.game_w, self.game_h = 900, 300
        self.win_w = self.cam_w
        self.win_h = self.cam_h + self.game_h

        self.cam_offset  = (0, 0)
        self.game_offset = (0, self.cam_h)

        self.screen = pygame.display.set_mode((self.win_w, self.win_h))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 20)
        self.font_small = pygame.font.SysFont("Arial", 16, bold=True)

        self.bg_cam  = pygame.Surface((self.cam_w,  self.cam_h ), pygame.SRCALPHA); self.bg_cam.fill((16,16,16))
        self.bg_game = pygame.Surface((self.game_w, self.game_h), pygame.SRCALPHA); self.bg_game.fill((247,247,247))

        self.ground_y = 258
        self.GROUND_ALIGN_ADJUST = 0

        self.ground = Ground(self.ground_y, speed=420)
        self.obstacles = pygame.sprite.Group()
        self.clouds = pygame.sprite.Group()
        self.dino = Dino(self.ground_y)

        self.speed=420; self.score=0; self.best=0
        self.game_over=False; self.spawn_timer=0.0; self.spawn_interval=1.1
        self.cloud_timer=0.0

        self.img_gameover = load_image(os.path.join(ASSETS_DIR,"Other","GameOver.png"))
        self.img_reset    = load_image(os.path.join(ASSETS_DIR,"Other","Reset.png"))

        self.use_tongue = use_tongue and TONGUE_AVAILABLE
        self.tongue=None
        if self.use_tongue:
            try:
                # IMPORTANT: mirror happens INSIDE TongueSwitch; do not flip here
                self.tongue = TongueSwitch(show_window=False, preview_size=(self.cam_w, self.cam_h), mirror=True)
                self.tongue.start()
                print("[INFO] Tongue control ON (Space also works).")
            except Exception as e:
                print("[WARN] Failed to start TongueSwitch:", e)
                self.use_tongue=False

    # ----- helpers -----
    def reset(self):
        self.obstacles.empty(); self.clouds.empty()
        self.dino = Dino(self.ground_y)
        self.speed=420; self.score=0; self.game_over=False; self.spawn_timer=0.0

    def spawn_obstacle(self):
        if random.random() < 0.7:
            self.obstacles.add(Cactus(self.ground_y, self.speed, self.GROUND_ALIGN_ADJUST))
        else:
            self.obstacles.add(Bird(self.speed, self.ground_y))

    def maybe_spawn_cloud(self, dt):
        self.cloud_timer += dt
        if self.cloud_timer > 1.5:
            self.cloud_timer = 0.0
            self.clouds.add(Cloud(self.game_w, self.game_h, self.speed, self.ground_y))

    def update_speed(self):
        self.speed = 420 + int(self.score/80)
        self.ground.speed = self.speed
        for o in self.obstacles:
            if isinstance(o, Cactus): o.speed = self.speed
            else: o.speed = self.speed + 30

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
            # DO NOT flip here — text is already correct
            if (dw, dh) != (fw, fh):
                surf = pygame.transform.smoothscale(surf, (dw, dh))
            dx = ox + (self.cam_w - dw)//2
            dy = oy + (self.cam_h - dh)//2
            self.screen.blit(surf, (dx, dy))

        # camera panel HUD (right aligned)
        status = self.tongue.get_state() if self.tongue else False

    def draw_game_panel(self):
        ox, oy = self.game_offset
        self.screen.blit(self.bg_game, (ox, oy))
        for c in self.clouds: self.screen.blit(c.image, (c.rect.x + ox, c.rect.y + oy))
        self.ground.draw(self.screen, (ox, oy))
        for o in self.obstacles: self.screen.blit(o.image, (o.rect.x + ox, o.rect.y + oy))
        self.screen.blit(self.dino.image, (self.dino.rect.x + ox, self.dino.rect.y + oy))
        txt=self.font.render(f"Score: {int(self.score):05d}   Best: {self.best:05d}", True, (60,60,60))
        self.screen.blit(txt, (ox + self.game_w - txt.get_width() - 10, oy + 10))
        if self.game_over:
            go_rect = self.img_gameover.get_rect(center=(ox + self.game_w//2, oy + self.game_h//2 - 20))
            rs_rect = self.img_reset.get_rect(center=(ox + self.game_w//2, oy + self.game_h//2 + 20))
            self.screen.blit(self.img_gameover, go_rect.topleft)
            self.screen.blit(self.img_reset, rs_rect.topleft)

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
                        if e.key in (pygame.K_SPACE, pygame.K_UP): self.dino.start_jump()
                        if e.key==pygame.K_DOWN: self.dino.set_duck(True)
                    else:
                        if e.key in (pygame.K_SPACE, pygame.K_UP): self.reset()
                elif e.type==pygame.KEYUP:
                    if e.key==pygame.K_DOWN: self.dino.set_duck(False)

            if not self.game_over and self.tongue and self.tongue.consume_rising_edge():
                self.dino.start_jump()

            if not self.game_over:
                self.spawn_timer += dt
                if self.spawn_timer >= self.spawn_interval:
                    self.spawn_timer = 0.0; self.spawn_obstacle()

                self.maybe_spawn_cloud(dt); self.update_speed()
                self.dino.update(dt); self.obstacles.update(dt); self.clouds.update(dt); self.ground.update(dt)

                if pygame.sprite.spritecollide(self.dino, self.obstacles, False, pygame.sprite.collide_mask):
                    self.dino.die(); self.game_over=True; self.best=max(self.best, int(self.score))
                self.score += dt*120

            self.screen.fill((22,22,22))
            self.draw_cam_panel()
            self.draw_game_panel()
            pygame.display.flip()

        if self.tongue: self.tongue.stop()
        pygame.quit()

def main():
    use_tongue = True
    if "--no-tongue" in sys.argv: use_tongue=False
    Game(use_tongue=use_tongue).run()

if __name__=="__main__":
    main()
