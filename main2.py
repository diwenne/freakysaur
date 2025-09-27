#!/usr/bin/env python3
import os, sys, math, random, pygame

# ---- Tongue switch (same module as your dino game) ----
try:
    from tongue_switch import TongueSwitch
    TONGUE_AVAILABLE = True
except Exception as e:
    print("[WARN] Tongue switch unavailable:", e)
    TONGUE_AVAILABLE = False

ROOT_DIR   = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(ROOT_DIR, "assets", "Flap")

# ---------------- helpers ----------------
def load_image(path: str) -> pygame.Surface:
    return pygame.image.load(path).convert_alpha()

def safe_load(path: str, fallback: str = None) -> pygame.Surface:
    p = os.path.join(ASSETS_DIR, path)
    if not os.path.exists(p) and fallback:
        pf = os.path.join(ASSETS_DIR, fallback)
        if os.path.exists(pf):
            p = pf
    return load_image(p)

def make_mask(surf: pygame.Surface) -> pygame.mask.Mask:
    return pygame.mask.from_surface(surf)

# ---------------- sprites ----------------
class PipePair:
    def __init__(self, x, gap_y, gap_size, speed, pipe_img):
        self.pipe_img = pipe_img
        self.flip_img = pygame.transform.flip(pipe_img, False, True)
        self.speed = float(speed)
        self.gap_size = gap_size

        # Track precise horizontal position as float; assign to rects after rounding
        self.x = float(x)

        self.top_rect = self.flip_img.get_rect()
        self.bot_rect = self.pipe_img.get_rect()

        ix = int(round(self.x))
        self.top_rect.x = self.bot_rect.x = ix
        self.top_rect.bottom = gap_y - gap_size // 2
        self.bot_rect.top = gap_y + gap_size // 2

        self.top_mask = make_mask(self.flip_img)
        self.bot_mask = make_mask(self.pipe_img)

        self.passed = False
        self.dead = False

    def update(self, dt):
        self.x -= self.speed * dt                  # precise movement
        ix = int(round(self.x))                    # round once
        self.top_rect.x = ix
        self.bot_rect.x = ix
        if self.top_rect.right < -50:
            self.dead = True

    def draw(self, surface, ox=0, oy=0):
        surface.blit(self.flip_img, (self.top_rect.x + ox, self.top_rect.y + oy))
        surface.blit(self.pipe_img, (self.bot_rect.x + ox, self.bot_rect.y + oy))

class BaseScroller:
    def __init__(self, img, y, speed):
        self.img = img
        self.y = y
        self.speed = float(speed)
        self.w = img.get_width()
        # Float positions for smooth scroll, with integer copies for drawing
        self.x1f = 0.0
        self.x2f = float(self.w)
        self.x1 = 0
        self.x2 = self.w

    def update(self, dt):
        self.x1f -= self.speed * dt
        self.x2f -= self.speed * dt
        # wrap using floats
        if self.x1f + self.w <= 0: self.x1f = self.x2f + self.w
        if self.x2f + self.w <= 0: self.x2f = self.x1f + self.w
        # assign integer positions once
        self.x1 = int(round(self.x1f))
        self.x2 = int(round(self.x2f))

    def draw(self, surface, ox=0, oy=0):
        surface.blit(self.img, (self.x1 + ox, self.y + oy))
        surface.blit(self.img, (self.x2 + ox, self.y + oy))

class Bird:
    def __init__(self, frames, x, y):
        self.frames = frames
        self.index = 0
        self.anim_t = 0.0
        self.anim_rate = 0.10

        self.image = self.frames[self.index]
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = 0.0
        self.gravity = 1000.0
        self.flap_speed = -400.0
        self.rot = 0.0

        # masks per frame for precise collision
        self.masks = [make_mask(f) for f in frames]

    def flap(self):
        self.vel = self.flap_speed
        self.rot = -25

    def update(self, dt):
        # physics
        self.vel += self.gravity * dt
        self.rect.y += int(self.vel * dt)

        # animation
        self.anim_t += dt
        if self.anim_t >= self.anim_rate:
            self.anim_t -= self.anim_rate
            self.index = (self.index + 1) % len(self.frames)
        self.image = self.frames[self.index]

        # rotation: tilt down when falling
        self.rot = max(-35, min(70, (self.vel / 400.0) * 90))
        self.rot = (self.rot * 0.9) + (15 if self.vel > 0 else -20) * 0.1
        self.rot_image = pygame.transform.rotate(self.image, -self.rot)  # negative to match visual
        self.rot_rect = self.rot_image.get_rect(center=self.rect.center)

    def draw(self, surface, ox=0, oy=0):
        surface.blit(self.rot_image, (self.rot_rect.x + ox, self.rot_rect.y + oy))

    def get_mask(self):
        return self.masks[self.index]

# ---------------- game ----------------
class FlapGame:
    def __init__(self, use_tongue=True):
        pygame.init()
        pygame.display.set_caption("Steve the Freaksaur - Flappy Tongue")

        # ---- MATCH main1 WINDOW LAYOUT ----
        # TOP webcam panel, BOTTOM game panel (no overlap)
        self.cam_w, self.cam_h = 900, 260
        self.game_w, self.game_h = 900, 560
        self.win_w = self.cam_w
        self.win_h = self.cam_h + self.game_h

        self.cam_offset  = (0, 0)
        self.game_offset = (0, self.cam_h)

        self.screen = pygame.display.set_mode((self.win_w, self.win_h))
        self.clock  = pygame.time.Clock()
        self.font   = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_s = pygame.font.SysFont("Arial", 16)

        # Background panels (same colors as main1)
        self.bg_cam  = pygame.Surface((self.cam_w,  self.cam_h ), pygame.SRCALPHA); self.bg_cam.fill((16,16,16))
        self.bg_game = pygame.Surface((self.game_w, self.game_h), pygame.SRCALPHA); self.bg_game.fill((247,247,247))

        # ---- Internal render at native Flappy size; scale into 900x560 panel ----
        self.game_w_native, self.game_h_native = 288, 512
        self.game_surface = pygame.Surface((self.game_w_native, self.game_h_native), pygame.SRCALPHA)

        # assets
        self.bg      = safe_load("background-day.png")
        self.baseimg = safe_load("base.png")
        self.pipeimg = safe_load("pipe-green.png")
        self.msg     = safe_load("message.png")
        self.gameover_img = safe_load("gameover.png")

        # bird frames (with typo fallback for midflap)
        bird_frames = [
            safe_load("yellowbird-downflap.png"),
            safe_load("yellowbird-midflap.png", fallback="yellobird-midflap.png"),
            safe_load("yellowbird-upflap.png"),
        ]
        self.bird = Bird(bird_frames, x=60, y=self.game_h_native//2)

        # world
        base_y = self.game_h_native - self.baseimg.get_height()
        self.base = BaseScroller(self.baseimg, base_y, speed=120.0)
        self.pipes = []

        # flow
        self.state = "ready"  # ready -> playing -> dead
        self.spawn_t = 0.0
        self.spawn_interval = 1.25
        self.pipe_gap = 150
        self.speed = 120.0
        self.score = 0
        self.best  = 0

        # tongue
        self.use_tongue = use_tongue and TONGUE_AVAILABLE
        self.tongue = None
        if self.use_tongue:
            try:
                # Mirror is handled inside TongueSwitch; do not flip preview here
                self.tongue = TongueSwitch(show_window=False, preview_size=(self.cam_w, self.cam_h), mirror=True)
                self.tongue.start()
                print("[INFO] Tongue control ON (Space/Click also flaps).")
            except Exception as e:
                print("[WARN] Failed to start TongueSwitch:", e)
                self.use_tongue = False

    # ---------- helpers ----------
    def reset_round(self):
        self.pipes.clear()
        self.bird = Bird(self.bird.frames, x=60, y=self.game_h_native//2)
        self.base = BaseScroller(self.baseimg, self.game_h_native - self.baseimg.get_height(), speed=120.0)
        self.spawn_t = 0.0
        self.speed = 120.0
        self.score = 0
        self.state = "ready"
        # NOTE: don't reset self.pipe_gap here; keep whatever player picked

    def spawn_pipepair(self):
        margin_top = 40
        margin_bot = 90
        gap_center = random.randint(
            margin_top + self.pipe_gap//2,
            self.game_h_native - margin_bot - self.pipe_gap//2
        )
        self.pipes.append(
            PipePair(
                x=self.game_w_native + 30,
                gap_y=gap_center,
                gap_size=self.pipe_gap,
                speed=self.speed,
                pipe_img=self.pipeimg
            )
        )

    def bird_collides(self) -> bool:
        # ground / ceiling
        if self.bird.rect.top <= -5: return True
        if self.bird.rect.bottom >= self.base.y + 2: return True

        bmask = self.bird.get_mask()
        boff = (self.bird.rot_rect.x, self.bird.rot_rect.y)  # using rotated rect for position

        for p in self.pipes:
            # Top pipe overlap check
            off_t = (p.top_rect.x - boff[0], p.top_rect.y - boff[1])
            off_b = (p.bot_rect.x - boff[0], p.bot_rect.y - boff[1])
            if bmask.overlap(p.top_mask, off_t) or bmask.overlap(p.bot_mask, off_b):
                return True
        return False

    def update_score_and_speed(self):
        # Score when bird passes pipe center
        for p in self.pipes:
            if not p.passed and p.top_rect.centerx < self.bird.rect.centerx:
                p.passed = True
                self.score += 1
                # slight difficulty ramp
                self.speed = min(210.0, 120.0 + self.score * 2.0)
                self.base.speed = self.speed
        # remove offscreen
        self.pipes = [p for p in self.pipes if not p.dead]

    def maybe_flap_from_tongue(self):
        if self.tongue and self.tongue.consume_rising_edge():
            self.bird.flap()
            if self.state == "ready":
                self.state = "playing"

    # ---------- drawing ----------
    def draw_cam_panel(self):
        ox, oy = self.cam_offset
        self.screen.blit(self.bg_cam, (ox, oy))
        frame = self.tongue.get_preview_rgb() if self.tongue else None
        if frame is not None:
            fh, fw, _ = frame.shape
            scale = min(self.cam_w / fw, self.cam_h / fh)
            dw, dh = int(fw * scale), int(fh * scale)
            surf = pygame.image.frombuffer(frame.tobytes(), (fw, fh), "RGB")
            if (dw, dh) != (fw, fh): surf = pygame.transform.smoothscale(surf, (dw, dh))
            dx = ox + (self.cam_w - dw)//2
            dy = oy + (self.cam_h - dh)//2
            self.screen.blit(surf, (dx, dy))

        # HUD (right aligned, same vibe as main1)
        lbl = self.font_s.render(
            f"Tongue: {'ON' if (self.tongue and self.tongue.get_state()) else 'OFF'}",
            True, (230,230,230)
        )
        self.screen.blit(lbl, (ox + self.cam_w - lbl.get_width() - 10, oy + 8))

    def draw_game_panel(self):
        ox, oy = self.game_offset

        # draw the light-grey game background panel (like main1)
        self.screen.blit(self.bg_game, (ox, oy))

        # render native flappy scene
        gs = self.game_surface
        gs.blit(self.bg, (0,0))                  # background
        for p in self.pipes: p.draw(gs)          # pipes
        self.base.draw(gs)                       # ground
        self.bird.draw(gs)                       # bird

        # score (simple centered)
        score_txt = self.font.render(f"{self.score}", True, (255,255,255))
        gs.blit(score_txt, (self.game_w_native//2 - score_txt.get_width()//2, 20))

        if self.state == "ready":
            msg_rect = self.msg.get_rect(center=(self.game_w_native//2, self.game_h_native//2 - 30))
            gs.blit(self.msg, msg_rect)
        elif self.state == "dead":
            go_rect = self.gameover_img.get_rect(center=(self.game_w_native//2, self.game_h_native//2 - 10))
            gs.blit(self.gameover_img, go_rect)
            sub = self.font_s.render(f"Score {self.score}   Best {self.best}", True, (255,255,255))
            gs.blit(sub, (self.game_w_native//2 - sub.get_width()//2, go_rect.bottom + 8))
            tip = self.font_s.render("Press Space / Click / Tongue to retry", True, (240,240,240))
            gs.blit(tip, (self.game_w_native//2 - tip.get_width()//2, go_rect.bottom + 28))

        # scale native scene to exactly fill the 900x560 game panel
        disp = pygame.transform.smoothscale(gs, (self.game_w, self.game_h))
        self.screen.blit(disp, (ox, oy))

    # ---------- loop ----------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60)/1000.0

            for e in pygame.event.get():
                if e.type == pygame.QUIT: running = False
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE: running = False
                    elif e.key in (pygame.K_SPACE, pygame.K_UP):
                        if self.state == "dead":
                            self.reset_round()
                        else:
                            self.bird.flap()
                            self.state = "playing"
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if e.button == 1:
                        if self.state == "dead":
                            self.reset_round()
                        else:
                            self.bird.flap(); self.state = "playing"

            # tongue input
            self.maybe_flap_from_tongue()

            # update world based on state
            if self.state == "playing":
                self.spawn_t += dt
                if self.spawn_t >= self.spawn_interval:
                    self.spawn_t = 0.0
                    self.spawn_pipepair()

                self.bird.update(dt)
                for p in self.pipes: p.update(dt)
                self.base.update(dt)
                self.update_score_and_speed()

                if self.bird_collides():
                    self.state = "dead"
                    self.best = max(self.best, self.score)

            elif self.state == "ready":
                # idle bobbing
                self.base.update(dt)
                self.bird.update(dt * 0.7)
                self.bird.rect.y += int(math.sin(pygame.time.get_ticks()/300.0) * 0.4)

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
        use_tongue = False
    FlapGame(use_tongue=use_tongue).run()

if __name__ == "__main__":
    main()
