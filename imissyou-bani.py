import pygame, sys, os, math, random, textwrap, threading
try:
    import pyperclip
    HAS_CLIP = True
except ImportError:
    HAS_CLIP = False
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

os.environ['SDL_VIDEO_CENTERED'] = '1'
pygame.init()
info = pygame.display.Info()
FULL_W, FULL_H = info.current_w, info.current_h
WIN_W, WIN_H = int(FULL_W * 0.82), int(FULL_H * 0.82)
WIDTH, HEIGHT = FULL_W, FULL_H
is_fullscreen = True
screen = pygame.display.set_mode(
    (WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE)
pygame.display.set_caption("Clarx")
clock = pygame.time.Clock()

C_BG      = (10, 10, 13)
C_WHITE   = (245, 245, 248)
C_DIM     = (95, 95, 105)
C_PANEL   = (18, 18, 24)
C_PANEL2  = (26, 26, 34)
C_ACC     = (85, 155, 255)
C_RED     = (235, 65, 65)
C_GROUP   = (50, 230, 180)
C_NOTE    = (255, 200, 60)
C_GLOW    = (180, 120, 255)

COLORS_LIST = [
    (245,245,248),(255,85,85),(85,235,85),(75,165,255),
    (255,255,110),(255,135,235),(165,95,255),(255,155,75),
    (0,255,210),(255,75,175),(155,255,65),(210,210,225),
]

MARGIN_W, MARGIN_H = 120, 95
NEN_NGANG  = 0.89
LERP_SPEED = 10.5
FLASH_SPEED = 19.0

FONT_PRIORITY = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/seguiemj.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]
MAIN_FONT_PATH = next((p for p in FONT_PRIORITY if os.path.exists(p)), None)
font_cache = {}

def get_font(size, bold=True):
    size = max(2, int(size))
    key = (size, bold)
    if key not in font_cache:
        f = None
        if MAIN_FONT_PATH:
            try:
                f = pygame.font.Font(MAIN_FONT_PATH, size)
                if bold:
                    f.set_bold(True)
            except:
                f = None
        if f is None:
            f = pygame.font.SysFont("arial,notosanscjk,dejavusans,seguiemj", size, bold=bold)
        font_cache[key] = f
    return font_cache[key]


class VideoPlayer:
    def __init__(self):
        self.cap = None
        self.path = ""
        self.frame_surf = None
        self.fps = 30.0
        self.frame_timer = 0.0
        self._thread = None
        self._next_frame = None
        self._lock = threading.Lock()
        self._running = False
        self._scaled_cache = {}

    def load(self, path):
        if not HAS_CV2:
            return False, "cv2 (opencv-python) not installed"
        try:
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                return False, "Cannot open video"
            self.unload()
            self.cap = cap
            self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.path = path
            self.frame_timer = 0.0
            self.frame_surf = None
            self._scaled_cache = {}
            self._running = True
            self._read_frame_sync()
            self._thread = threading.Thread(target=self._decode_loop, daemon=True)
            self._thread.start()
            return True, ""
        except Exception as e:
            return False, str(e)

    def _read_frame_sync(self):
        if not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            surf = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
            with self._lock:
                self.frame_surf = surf
                self._scaled_cache = {}

    def _decode_loop(self):
        interval = 1.0 / self.fps
        while self._running:
            if not self.cap:
                break
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                surf = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
                with self._lock:
                    self._next_frame = surf
            pygame.time.wait(int(interval * 1000))

    def update(self, dt):
        if not self.cap:
            return
        self.frame_timer += dt
        if self.frame_timer >= 1.0 / self.fps:
            self.frame_timer -= 1.0 / self.fps
            with self._lock:
                if self._next_frame is not None:
                    self.frame_surf = self._next_frame
                    self._next_frame = None
                    self._scaled_cache = {}

    def draw(self, surf, w, h, dim=0.42):
        with self._lock:
            frame = self.frame_surf
        if not frame:
            return
        key = (id(frame), w, h)
        if key not in self._scaled_cache:
            fw, fh = frame.get_size()
            scale = max(w / fw, h / fh)
            nw, nh = int(fw * scale), int(fh * scale)
            scaled = pygame.transform.smoothscale(frame, (nw, nh))
            ox = (nw - w) // 2
            oy = (nh - h) // 2
            cropped = scaled.subsurface(pygame.Rect(ox, oy, w, h)).copy()
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(255 * dim)))
            cropped.blit(overlay, (0, 0))
            self._scaled_cache[key] = cropped
        surf.blit(self._scaled_cache[key], (0, 0))

    def is_loaded(self):
        return self.cap is not None

    def unload(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        if self.cap:
            self.cap.release()
        self.cap = None
        self.path = ""
        self.frame_surf = None
        self._next_frame = None
        self._thread = None


class BgManager:
    def __init__(self):
        self.menu_img    = None
        self.display_img = None
        self.menu_path   = ""
        self.display_path = ""
        self.menu_video   = VideoPlayer()
        self.display_video = VideoPlayer()
        self._scaled_cache = {}

    def _is_video(self, path):
        return path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))

    def load(self, path, target):
        if self._is_video(path):
            if not HAS_CV2:
                return False, "opencv-python not installed"
            ok_m = ok_d = True
            err = ""
            if target in ('menu', 'both'):
                ok_m, err = self.menu_video.load(path)
                if ok_m:
                    self.menu_path = path
                    self.menu_img = None
            if target in ('display', 'both'):
                ok_d, err = self.display_video.load(path)
                if ok_d:
                    self.display_path = path
                    self.display_img = None
            return (ok_m and ok_d), err
        else:
            try:
                img = pygame.image.load(path).convert()
            except Exception as e:
                return False, str(e)
            if target in ('menu', 'both'):
                self.menu_img = img
                self.menu_path = path
                self.menu_video.unload()
            if target in ('display', 'both'):
                self.display_img = img
                self.display_path = path
                self.display_video.unload()
            self._scaled_cache.clear()
            return True, ""

    def clear(self, target):
        if target in ('menu', 'both'):
            self.menu_img = None
            self.menu_path = ""
            self.menu_video.unload()
        if target in ('display', 'both'):
            self.display_img = None
            self.display_path = ""
            self.display_video.unload()
        self._scaled_cache.clear()

    def update(self, dt):
        self.menu_video.update(dt)
        self.display_video.update(dt)

    def draw(self, surf, which, w, h, dim=0.42):
        video = self.menu_video if which == 'menu' else self.display_video
        img   = self.menu_img   if which == 'menu' else self.display_img
        if video.is_loaded():
            video.draw(surf, w, h, dim)
            return
        if img is None:
            return
        key = (id(img), w, h)
        if key not in self._scaled_cache:
            iw, ih = img.get_size()
            scale = max(w / iw, h / ih)
            nw, nh = int(iw * scale), int(ih * scale)
            scaled = pygame.transform.smoothscale(img, (nw, nh))
            ox = (nw - w) // 2
            oy = (nh - h) // 2
            cropped = scaled.subsurface(pygame.Rect(ox, oy, w, h)).copy()
            overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(255 * dim)))
            cropped.blit(overlay, (0, 0))
            self._scaled_cache[key] = cropped
        surf.blit(self._scaled_cache[key], (0, 0))

bg = BgManager()


class Particle:
    SHAPES  = ['star4', 'star6', 'diamond', 'dot', 'line']
    PALETTE = [
        (255,225,70),(255,195,35),(195,165,25),
        (230,230,230),(170,215,255),(195,195,195),
        (255,155,195),(155,255,195),(195,155,255),
        (255,255,115),(115,255,255),
    ]

    def __init__(self, cx, cy, sw, sh):
        angle = random.uniform(0, math.pi * 2)
        spd   = random.uniform(55, 245)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd - random.uniform(35, 110)
        self.x  = cx + random.uniform(-sw * .5, sw * .5)
        self.y  = cy + random.uniform(-sh * .3, sh * .3)
        self.life  = 1.0
        self.decay = random.uniform(0.52, 1.25)
        self.size  = random.uniform(3.5, 11)
        self.rot   = random.uniform(0, math.pi * 2)
        self.rotspd = random.uniform(-7, 7)
        self.grav  = random.uniform(50, 135)
        self.shape = random.choice(self.SHAPES)
        self.color = random.choice(self.PALETTE)

    def update(self, dt):
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        self.vy += self.grav * dt
        self.rot += self.rotspd * dt
        self.life -= self.decay * dt
        return self.life > 0

    def _spts(self, cx, cy, r, n, rot):
        return [(cx + math.cos(rot + i * math.pi / n) * (r if i % 2 == 0 else r * .42),
                 cy + math.sin(rot + i * math.pi / n) * (r if i % 2 == 0 else r * .42))
                for i in range(n * 2)]

    def draw(self, surf):
        a   = max(0, min(255, int(self.life * 255)))
        r   = max(1, int(self.size * self.life))
        cx, cy = int(self.x), int(self.y)
        col = (*self.color, a)
        tmp = pygame.Surface((r * 4 + 4, r * 4 + 4), pygame.SRCALPHA)
        tc  = (r * 2 + 2, r * 2 + 2)
        if self.shape in ('star4', 'star6'):
            n = 4 if self.shape == 'star4' else 6
            pts = self._spts(tc[0], tc[1], r, n, self.rot)
            if len(pts) >= 3:
                pygame.draw.polygon(tmp, col, pts)
        elif self.shape == 'diamond':
            pts = self._spts(tc[0], tc[1], r, 2, self.rot)
            if len(pts) >= 3:
                pygame.draw.polygon(tmp, col, pts)
        elif self.shape == 'dot':
            pygame.draw.circle(tmp, col, tc, max(1, r))
        elif self.shape == 'line':
            ex = int(tc[0] + math.cos(self.rot) * r)
            ey = int(tc[1] + math.sin(self.rot) * r)
            pygame.draw.line(tmp, col, tc, (ex, ey), max(1, r // 3))
        surf.blit(tmp, (cx - tc[0], cy - tc[1]), special_flags=pygame.BLEND_PREMULTIPLIED)


class GlowStar:
    def __init__(self, screen_w, screen_h):
        side = random.choice(['left', 'right', 'top', 'bottom'])
        if side == 'left':
            self.x, self.y = -20.0, random.uniform(0, screen_h)
            self.vx, self.vy = random.uniform(40, 110), random.uniform(-25, 25)
        elif side == 'right':
            self.x, self.y = screen_w + 20.0, random.uniform(0, screen_h)
            self.vx, self.vy = random.uniform(-110, -40), random.uniform(-25, 25)
        elif side == 'top':
            self.x, self.y = random.uniform(0, screen_w), -20.0
            self.vx, self.vy = random.uniform(-25, 25), random.uniform(40, 110)
        else:
            self.x, self.y = random.uniform(0, screen_w), screen_h + 20.0
            self.vx, self.vy = random.uniform(-25, 25), random.uniform(-110, -40)
        self.life   = 1.0
        self.decay  = random.uniform(0.06, 0.18)
        self.size   = random.uniform(4, 14)
        self.rot    = random.uniform(0, math.pi * 2)
        self.rotspd = random.uniform(-2.5, 2.5)
        self.pulse  = random.uniform(0, math.pi * 2)
        colors = [
            (200, 160, 255), (255, 200, 80), (100, 220, 255),
            (255, 140, 200), (160, 255, 180), (255, 255, 180),
        ]
        self.color = random.choice(colors)
        self.sw = screen_w
        self.sh = screen_h

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.rot  += self.rotspd * dt
        self.pulse += 4.0 * dt
        self.life -= self.decay * dt
        if self.x < -60 or self.x > self.sw + 60:
            return False
        if self.y < -60 or self.y > self.sh + 60:
            return False
        return self.life > 0

    def _star_pts(self, cx, cy, r, n, rot):
        pts = []
        for i in range(n * 2):
            angle = rot + i * math.pi / n
            rad   = r if i % 2 == 0 else r * 0.38
            pts.append((cx + math.cos(angle) * rad, cy + math.sin(angle) * rad))
        return pts

    def draw(self, surf):
        pulse_val = 0.72 + 0.28 * math.sin(self.pulse)
        a   = max(0, min(255, int(self.life * 220 * pulse_val)))
        r   = max(2, int(self.size * pulse_val))
        cx, cy = int(self.x), int(self.y)
        tmp = pygame.Surface((r * 6 + 6, r * 6 + 6), pygame.SRCALPHA)
        tc  = (r * 3 + 3, r * 3 + 3)

        glow_r = r * 3
        for gr in range(glow_r, 0, -2):
            ga = int(a * 0.12 * (gr / glow_r))
            pygame.draw.circle(tmp, (*self.color, ga), tc, gr)

        pts = self._star_pts(tc[0], tc[1], r, 4, self.rot)
        if len(pts) >= 3:
            pygame.draw.polygon(tmp, (*self.color, a), pts)

        inner_pts = self._star_pts(tc[0], tc[1], r * 0.5, 4, self.rot + math.pi / 4)
        if len(inner_pts) >= 3:
            pygame.draw.polygon(tmp, (255, 255, 255, int(a * 0.6)), inner_pts)

        surf.blit(tmp, (cx - tc[0], cy - tc[1]), special_flags=pygame.BLEND_PREMULTIPLIED)


class GlowRing:
    def __init__(self, cx, cy, color):
        self.x      = float(cx)
        self.y      = float(cy)
        self.r      = 0.0
        self.max_r  = random.uniform(60, 160)
        self.life   = 1.0
        self.decay  = random.uniform(0.4, 0.9)
        self.color  = color
        self.speed  = random.uniform(80, 180)

    def update(self, dt):
        self.r    += self.speed * dt
        self.life -= self.decay * dt
        return self.life > 0 and self.r < self.max_r * 1.2

    def draw(self, surf):
        a = max(0, min(255, int(self.life * 160)))
        r = int(self.r)
        if r < 2:
            return
        tmp = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        tc  = (r + 4, r + 4)
        w   = max(1, int(3 * self.life))
        pygame.draw.circle(tmp, (*self.color, a), tc, r, w)
        surf.blit(tmp, (int(self.x) - tc[0], int(self.y) - tc[1]),
                  special_flags=pygame.BLEND_PREMULTIPLIED)


particles   = []
glow_stars  = []
glow_rings  = []


def spawn_particles(cx, cy, sw, sh, n=68):
    for _ in range(n):
        particles.append(Particle(cx, cy, sw, sh))


def spawn_glow_effect(cx, cy, color, screen_w, screen_h, n_stars=18, n_rings=4):
    for _ in range(n_stars):
        glow_stars.append(GlowStar(screen_w, screen_h))
    for _ in range(n_rings):
        glow_rings.append(GlowRing(cx, cy, color))


class BurstChar:
    def __init__(self, ch, cx, cy, color, size, idx, total):
        self.ch    = ch
        self.color = color
        self.size  = size
        self.x, self.y = cx, cy
        angle = random.uniform(0, math.pi * 2)
        spd   = random.uniform(310, 680)
        self.vx     = math.cos(angle) * spd
        self.vy     = math.sin(angle) * spd
        self.rot    = random.uniform(0, math.pi * 2)
        self.rotspd = random.uniform(-28, 28)
        self.life   = 1.0
        self.decay  = random.uniform(0.48, 0.92)
        self.surf   = None

    def update(self, dt):
        self.x  += self.vx * dt
        self.y  += self.vy * dt
        damp     = 6.8 if self.life > 0.65 else 2.4
        self.vx *= (1 - damp * dt)
        self.vy *= (1 - damp * dt)
        self.vy += 48 * dt
        self.rot += self.rotspd * dt
        self.rotspd *= 0.91
        self.life -= self.decay * dt
        return self.life > 0

    def get_surf(self):
        if self.surf is None:
            f   = get_font(self.size, bold=True)
            raw = f.render(self.ch, True, self.color).convert_alpha()
            tw  = max(1, int(raw.get_width() * NEN_NGANG))
            self.surf = pygame.transform.smoothscale(raw, (tw, raw.get_height()))
        return self.surf

    def draw(self, surface, master_alpha):
        s = self.get_surf()
        s.set_alpha(max(0, int(master_alpha * self.life)))
        rect = s.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(s, rect)


class BottomNote:
    def __init__(self, text):
        self.text   = text
        self.alpha  = 0.0
        self.cur_y  = HEIGHT
        self.timer  = 0.0
        self.active = True
        target_h    = HEIGHT - 72
        self.target_y = target_h

    def update(self, dt):
        if not self.active:
            return
        self.timer  += dt
        self.alpha   = min(255.0, self.alpha + 380 * dt)
        self.cur_y  += (self.target_y - self.cur_y) * 11 * dt

    def dismiss(self):
        self.active = False

    def draw(self, surf):
        if self.alpha < 2:
            return
        font_sz = 22
        f       = get_font(font_sz, bold=False)
        max_w   = min(720, WIDTH - 120)
        words   = self.text.split()
        lines   = []
        cur     = ""
        for w in words:
            test = (cur + " " + w).strip()
            if f.size(test)[0] > max_w:
                if cur:
                    lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)

        lh  = f.get_linesize()
        pad = 18
        tw  = max(f.size(l)[0] for l in lines) if lines else 10
        bw  = tw + pad * 2
        bh  = lh * len(lines) + pad * 2
        bx  = WIDTH // 2 - bw // 2
        by  = int(self.cur_y) - bh // 2

        pulse     = math.sin(self.timer * 2.8) * 0.5 + 0.5
        border_a  = int((160 + 60 * pulse) * (self.alpha / 255))

        shadow = pygame.Surface((bw + 16, bh + 16), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, int(self.alpha * 0.5)),
                         (0, 0, bw + 16, bh + 16), border_radius=14)
        surf.blit(shadow, (bx - 8, by - 8))

        panel = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 14, 24, int(self.alpha * 0.88)),
                         (0, 0, bw, bh), border_radius=12)
        surf.blit(panel, (bx, by))

        pygame.draw.rect(surf, (*C_NOTE, border_a),
                         pygame.Rect(bx, by, bw, bh), 2, border_radius=12)

        for li, line in enumerate(lines):
            ts = f.render(line, True, C_NOTE)
            ts.set_alpha(int(self.alpha))
            tx = bx + pad + (tw - f.size(line)[0]) // 2
            surf.blit(ts, (tx, by + pad + li * lh))


IDX_WORD  = 0
IDX_COLOR = 1
IDX_LISS  = 2
IDX_FLASH = 3
IDX_STAR  = 4
IDX_BURST = 5
IDX_GID   = 6
IDX_NOTE  = 7
IDX_GLOW  = 8


class WordAnim:
    def __init__(self, text, sx, sy, color,
                 liss=False, flash=False, star=False, burst=False,
                 glow=False, group_id=-1, note="", word_idx=0,
                 group_delay=0.0):
        self.text     = text
        self.color    = color
        self.liss     = liss
        self.flash    = flash
        self.star     = star
        self.burst    = burst
        self.glow     = glow
        self.group_id = group_id
        self.note     = note
        self.word_idx = word_idx
        self.group_delay = group_delay

        self.cur_x, self.cur_y = sx, sy + 80
        self.cur_size = 5.0
        self.alpha    = 0.0
        self.surface  = None
        self.timer    = random.uniform(0, 5)
        self.last_size  = -1
        self.last_color = color
        self.flash_active = flash

        self.burst_chars  = []
        self.burst_built  = False
        self.burst_timer  = 0.0

        self.group_revealed = (group_id < 0)
        self.group_timer    = 0.0

    def _build_burst_chars(self, target_size):
        self.burst_chars.clear()
        f        = get_font(target_size, bold=True)
        tw_total = f.size(self.text)[0] * NEN_NGANG
        x_start  = self.cur_x - tw_total / 2
        for i, ch in enumerate(self.text):
            if not ch.strip():
                continue
            cw = f.size(ch)[0] * NEN_NGANG
            cx = x_start + cw / 2
            self.burst_chars.append(
                BurstChar(ch, cx, self.cur_y, self.color, target_size, i, len(self.text)))
            x_start += cw

    def update(self, dt, tx, ty, target_size, flash_on):
        self.timer += dt
        ftx, fty      = tx, ty
        display_color = self.color

        if self.group_id >= 0 and not self.group_revealed:
            self.group_timer += dt
            if self.group_timer >= self.group_delay:
                self.group_revealed = True
            else:
                self.cur_x = tx
                self.cur_y = ty
                return

        if self.liss:
            ftx += math.cos(self.timer * 1.5) * 12
            fty += math.sin(self.timer * 3.0) * 8
            cycle = (math.sin(self.timer * 0.8) + 1) / 2
            display_color = (int(100 + 100 * cycle), int(150 + 105 * (1 - cycle)), 255)

        if self.flash and self.flash_active and flash_on:
            display_color = (10, 10, 10)

        self.cur_x    += (ftx - self.cur_x) * LERP_SPEED * dt
        self.cur_y    += (fty - self.cur_y) * LERP_SPEED * dt
        self.cur_size += (target_size - self.cur_size) * LERP_SPEED * dt
        self.alpha    += (255.0 - self.alpha) * LERP_SPEED * dt

        if self.burst:
            self.burst_timer += dt
            if not self.burst_built and self.burst_timer >= 1.35:
                self.burst_built = True
                self._build_burst_chars(int(self.cur_size))
            if self.burst_built:
                self.burst_chars[:] = [c for c in self.burst_chars if c.update(dt)]
                self.alpha = max(30, self.alpha - 420 * dt)

        s = int(self.cur_size)
        if s > 0 and not (self.burst and self.burst_built):
            cdiff = sum(abs(a - b) for a, b in zip(display_color, self.last_color))
            if (not self.surface or abs(s - self.last_size) > 1 or cdiff > 3 or
                    (self.flash and self.flash_active)):
                f   = get_font(s)
                raw = f.render(self.text, True, display_color).convert_alpha()
                tw  = max(1, int(raw.get_width() * NEN_NGANG))
                self.surface = pygame.transform.smoothscale(raw, (tw, raw.get_height()))
                self.last_size  = s
                self.last_color = display_color

    def draw(self, surface, local_flash_on=False):
        if not self.group_revealed or self.alpha < 2:
            return

        if self.burst and self.burst_built:
            for c in self.burst_chars:
                c.draw(surface, self.alpha)
            return

        if not self.surface:
            return

        self.surface.set_alpha(int(min(255, self.alpha)))
        rect = self.surface.get_rect(center=(int(self.cur_x), int(self.cur_y)))

        if self.glow:
            glow_s = max(1, int(self.cur_size * 0.12))
            glow_surf = pygame.Surface(
                (rect.w + glow_s * 6, rect.h + glow_s * 4), pygame.SRCALPHA)
            pulse_a = int(40 + 30 * math.sin(self.timer * 3.2))
            gc = C_GLOW
            pygame.draw.rect(glow_surf, (*gc, pulse_a),
                             (0, 0, rect.w + glow_s * 6, rect.h + glow_s * 4),
                             border_radius=glow_s * 2)
            surface.blit(glow_surf, (rect.x - glow_s * 3, rect.y - glow_s * 2),
                         special_flags=pygame.BLEND_PREMULTIPLIED)

        if self.flash and not self.liss and self.flash_active and local_flash_on:
            pad = int(self.cur_size * 0.18)
            pygame.draw.rect(surface, (245, 245, 245),
                             rect.inflate(pad * 2, pad), border_radius=8)

        if self.liss:
            sh2 = self.surface.copy()
            sh2.set_alpha(40)
            surface.blit(sh2, (rect.x + 4, rect.y + 4))
            au = self.surface.copy()
            au.set_alpha(int(30 + 20 * math.sin(self.timer * 2)))
            for off in (-2, 2):
                surface.blit(au, (rect.x + off, rect.y))

        surface.blit(self.surface, rect)

        if self.note:
            dot_surf = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(dot_surf, (*C_NOTE, int(self.alpha)), (7, 7), 7)
            surface.blit(dot_surf, (rect.right - 4, rect.top - 4))


def calc_layout(words_data, area_w, area_h, start_size=320):
    if not words_data:
        return 20, []
    size = start_size
    while size > 10:
        f    = get_font(size)
        sw   = f.size(" ")[0] * NEN_NGANG
        lines, cur_line, cur_w, fits = [], [], 0, True
        for wd in words_data:
            w  = wd[IDX_WORD]
            ww = f.size(w)[0] * NEN_NGANG
            if ww > area_w:
                fits = False
                break
            gid = wd[IDX_GID]
            gap = 0 if (cur_line and cur_line[-1][IDX_GID] >= 0
                        and cur_line[-1][IDX_GID] == gid) else sw
            if cur_w + gap + ww <= area_w:
                cur_line.append((*wd, ww))
                cur_w += gap + ww
            else:
                lines.append(cur_line)
                cur_line = [(*wd, ww)]
                cur_w = ww
        if not fits:
            size -= 4
            continue
        if cur_line:
            lines.append(cur_line)
        lh = f.get_linesize()
        th = len(lines) * lh
        if th <= area_h:
            pos = []
            sy  = (HEIGHT - th) / 2
            for ri, row in enumerate(lines):
                rw = 0
                for j, it in enumerate(row):
                    if j > 0 and it[IDX_GID] >= 0 and row[j - 1][IDX_GID] == it[IDX_GID]:
                        rw += it[-1]
                    else:
                        rw += it[-1] + (sw if j > 0 else 0)
                xo = (WIDTH - rw) / 2
                for j, it in enumerate(row):
                    ww    = it[-1]
                    word  = it[IDX_WORD]
                    color = it[IDX_COLOR]
                    liss  = it[IDX_LISS]
                    flash = it[IDX_FLASH]
                    star  = it[IDX_STAR]
                    burst = it[IDX_BURST]
                    gid   = it[IDX_GID]
                    note  = it[IDX_NOTE]
                    glow  = it[IDX_GLOW]
                    pos.append((word, xo + ww / 2, sy + ri * lh + lh / 2,
                                color, liss, flash, star, burst, gid, note, glow))
                    if j + 1 < len(row):
                        nxt = row[j + 1]
                        gap = 0 if (nxt[IDX_GID] >= 0 and nxt[IDX_GID] == gid) else sw
                        xo += ww + gap
            return size, pos
        size -= 4
    return 10, []


def draw_btn(surf, rect, label, active, active_color, hover, font_size=19):
    col = active_color if active else (C_DIM if not hover else (115, 115, 130))
    pygame.draw.rect(surf, col, rect, border_radius=12)
    txt = get_font(font_size, bold=True).render(
        label, True, (12, 12, 14) if active else C_WHITE)
    surf.blit(txt, txt.get_rect(center=rect.center))


def draw_panel(surf, rect, radius=16, alpha=205):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (20, 20, 27, alpha), (0, 0, rect.w, rect.h), border_radius=radius)
    surf.blit(s, rect.topleft)


state = "MENU"
text_data         = []
current_color     = C_WHITE
word_index        = 0
start_display_index = 0
active_anims      = []
last_hash         = None
input_buffer      = ""
is_cleared        = True
editing_index     = -1
word_rects        = []
flash_timer       = 0.0
global_timer      = 0.0
star_spawned      = set()
glow_spawned      = set()
c_size = 20
c_data = []
group_counters    = {}

bg_panel_open  = False
bg_pick_target = 'both'
bg_path_input  = ""
bg_path_active = False
bg_error_msg   = ""
bg_error_timer = 0.0

note_edit_open   = False
note_edit_index  = -1
note_edit_buffer = ""

group_selection    = []
ctrl_select_mode   = False
next_group_id      = 0
bottom_note_widget = None

pygame.key.start_text_input()


def open_file_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title="Select image or video",
            filetypes=[
                ("Media files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.mp4 *.avi *.mov *.mkv *.webm"),
                ("Images",      "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
                ("Videos",      "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("All files",   "*.*"),
            ]
        )
        root.destroy()
        return path or ""
    except Exception:
        return ""


while True:
    dt = min(clock.tick(180) / 1000.0, 0.05)
    flash_timer  += dt
    global_timer += dt
    bg_error_timer = max(0.0, bg_error_timer - dt)
    bg.update(dt)

    screen.fill(C_BG)
    which_bg = 'menu' if state == 'MENU' else 'display'
    bg.draw(screen, which_bg, WIDTH, HEIGHT)

    m_pos = pygame.mouse.get_pos()
    mods  = pygame.key.get_mods()
    ctrl  = mods & pygame.KMOD_CTRL

    bw, bh = 268, 62
    bx     = WIDTH // 2 - bw // 2
    btn_start = pygame.Rect(bx, HEIGHT // 2 - 140, bw, bh)
    btn_edit  = pygame.Rect(bx, HEIGHT // 2 -  63, bw, bh)
    btn_bg    = pygame.Rect(bx, HEIGHT // 2 +  14, bw, bh)
    btn_quit  = pygame.Rect(bx, HEIGHT // 2 +  91, bw, bh)
    btn_fs    = pygame.Rect(WIDTH - 218, 26, 192, 46)

    EBW, EBH = 120, 44
    EBX = WIDTH - EBW - 28
    eff_btn_defs = [
        ("WAVE",    (0, 225, 165),    IDX_LISS),
        ("FLASH",   (255, 215, 30),   IDX_FLASH),
        ("STAR",    (255, 160, 40),   IDX_STAR),
        ("BURST",   (255, 85, 185),   IDX_BURST),
        ("GLOW",    C_GLOW,           IDX_GLOW),
    ]
    eff_btns = []
    for ei, (lbl, col, idx) in enumerate(eff_btn_defs):
        r = pygame.Rect(EBX, 28 + ei * (EBH + 8), EBW, EBH)
        eff_btns.append((r, lbl, col, idx))

    EBY_group = 28 + len(eff_btn_defs) * (EBH + 8)
    btn_group = pygame.Rect(EBX, EBY_group,         EBW, EBH)
    btn_note  = pygame.Rect(EBX, EBY_group + EBH + 8, EBW, EBH)

    swatch_x0   = 28
    swatch_y0   = 28
    SWATCH_W    = 46
    SWATCH_H    = 46
    SWATCH_COLS = 6
    color_rects = []
    for i, color in enumerate(COLORS_LIST):
        row_i = i // SWATCH_COLS
        col_i = i % SWATCH_COLS
        color_rects.append((
            pygame.Rect(swatch_x0 + col_i * (SWATCH_W + 6),
                        swatch_y0 + row_i * (SWATCH_H + 6),
                        SWATCH_W, SWATCH_H),
            color
        ))

    swatch_bottom = swatch_y0 + 2 * (SWATCH_H + 6) + 6
    hint_top      = HEIGHT - 58
    box = pygame.Rect(28, swatch_bottom + 12,
                      WIDTH - EBW - 72, hint_top - swatch_bottom - 24)

    bgp       = pygame.Rect(WIDTH // 2 - 325, HEIGHT // 2 - 195, 650, 390)
    inp_rect  = pygame.Rect(bgp.x + 25,  bgp.y + 100,  bgp.w - 50, 52)
    btn_bp_imp = pygame.Rect(bgp.x + 25,  bgp.y + 162, 175, 44)
    btn_bp_m   = pygame.Rect(bgp.x + 215, bgp.y + 162, 135, 44)
    btn_bp_d   = pygame.Rect(bgp.x + 363, bgp.y + 162, 135, 44)
    btn_bp_b   = pygame.Rect(bgp.x + 508, bgp.y + 162, 110, 44)
    btn_bp_ok  = pygame.Rect(bgp.x + 25,  bgp.y + 224, 185, 44)
    btn_bp_clr = pygame.Rect(bgp.x + 225, bgp.y + 224, 185, 44)
    btn_bp_cls = pygame.Rect(bgp.x + 425, bgp.y + 224, 175, 44)

    nep    = pygame.Rect(WIDTH // 2 - 300, HEIGHT // 2 - 130, 600, 260)
    ne_inp = pygame.Rect(nep.x + 24, nep.y + 80, nep.w - 48, 100)
    btn_ne_ok  = pygame.Rect(nep.x + 24,  nep.y + 200, 170, 44)
    btn_ne_clr = pygame.Rect(nep.x + 210, nep.y + 200, 170, 44)
    btn_ne_cls = pygame.Rect(nep.x + 400, nep.y + 200, 170, 44)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.DROPFILE:
            dropped = event.file
            ok, err = bg.load(dropped, bg_pick_target)
            bg_error_msg   = f"Loaded: {os.path.basename(dropped)}" if ok else "Error: " + err[:40]
            bg_error_timer = 2.6

        if event.type == pygame.TEXTINPUT and not ctrl:
            if note_edit_open:
                note_edit_buffer += event.text
            elif bg_panel_open and bg_path_active:
                bg_path_input += event.text
            elif state == "INPUT" and not note_edit_open:
                input_buffer += event.text

        if event.type == pygame.MOUSEBUTTONDOWN:
            if note_edit_open:
                if btn_ne_ok.collidepoint(m_pos):
                    if note_edit_index >= 0:
                        text_data[note_edit_index][IDX_NOTE] = note_edit_buffer.strip()
                    note_edit_open = False
                elif btn_ne_clr.collidepoint(m_pos):
                    note_edit_buffer = ""
                elif btn_ne_cls.collidepoint(m_pos) or not nep.collidepoint(m_pos):
                    note_edit_open = False
                continue

            if bg_panel_open:
                if inp_rect.collidepoint(m_pos):
                    bg_path_active = True
                elif btn_bp_imp.collidepoint(m_pos):
                    path = open_file_dialog()
                    if path:
                        bg_path_input = path
                        ok, err = bg.load(path, bg_pick_target)
                        bg_error_msg   = "Loaded!" if ok else "Error: " + err[:42]
                        bg_error_timer = 2.6
                elif btn_bp_m.collidepoint(m_pos):
                    bg_pick_target = 'menu'
                elif btn_bp_d.collidepoint(m_pos):
                    bg_pick_target = 'display'
                elif btn_bp_b.collidepoint(m_pos):
                    bg_pick_target = 'both'
                elif btn_bp_ok.collidepoint(m_pos):
                    ok, err = bg.load(bg_path_input.strip(), bg_pick_target)
                    bg_error_msg   = "Loaded!" if ok else "Error: " + err[:42]
                    bg_error_timer = 2.6
                elif btn_bp_clr.collidepoint(m_pos):
                    bg.clear(bg_pick_target)
                    bg_error_msg   = "Background cleared"
                    bg_error_timer = 1.6
                elif btn_bp_cls.collidepoint(m_pos) or not bgp.collidepoint(m_pos):
                    bg_panel_open  = False
                    bg_path_active = False
                continue

            if state == "MENU":
                if btn_start.collidepoint(m_pos):
                    state = "DISPLAY"
                    word_index = 0
                    start_display_index = 0
                    active_anims.clear()
                    last_hash = None
                    star_spawned.clear()
                    glow_spawned.clear()
                    is_cleared = True
                    bottom_note_widget = None
                elif btn_edit.collidepoint(m_pos):
                    state = "INPUT"
                    group_selection.clear()
                    ctrl_select_mode = False
                elif btn_bg.collidepoint(m_pos):
                    bg_panel_open  = True
                    bg_path_active = False
                elif btn_quit.collidepoint(m_pos):
                    pygame.quit()
                    sys.exit()
                elif btn_fs.collidepoint(m_pos):
                    is_fullscreen = not is_fullscreen
                    WIDTH, HEIGHT = (FULL_W, FULL_H) if is_fullscreen else (WIN_W, WIN_H)
                    mode = (pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
                            if is_fullscreen else pygame.DOUBLEBUF | pygame.HWSURFACE)
                    screen = pygame.display.set_mode((WIDTH, HEIGHT), mode)

            elif state == "INPUT":
                hit = False
                if editing_index != -1 and not ctrl:
                    for btn_r, lbl, col_a, eff_idx in eff_btns:
                        if btn_r.collidepoint(m_pos):
                            text_data[editing_index][eff_idx] = \
                                not text_data[editing_index][eff_idx]
                            if eff_idx == IDX_STAR and text_data[editing_index][eff_idx]:
                                for rr, idx2 in word_rects:
                                    if idx2 == editing_index:
                                        spawn_particles(rr.centerx, rr.centery, rr.w, rr.h, 58)
                                        break
                            hit = True
                            break

                if not hit and btn_group.collidepoint(m_pos):
                    if ctrl and len(group_selection) >= 2:
                        gs = sorted(group_selection)
                        contiguous = all(gs[i] + 1 == gs[i + 1] for i in range(len(gs) - 1))
                        if contiguous:
                            gid = next_group_id
                            next_group_id += 1
                            for idx2 in gs:
                                text_data[idx2][IDX_GID] = gid
                            bg_error_msg   = f"Group created ({len(gs)} word)"
                            bg_error_timer = 1.8
                        else:
                            bg_error_msg   = "Only adjacent words can be group"
                            bg_error_timer = 2.0
                        group_selection.clear()
                    elif editing_index != -1:
                        text_data[editing_index][IDX_GID] = -1
                        bg_error_msg   = "Ungrouped"
                        bg_error_timer = 1.2
                    hit = True

                if not hit and btn_note.collidepoint(m_pos):
                    if editing_index != -1:
                        note_edit_open   = True
                        note_edit_index  = editing_index
                        note_edit_buffer = text_data[editing_index][IDX_NOTE]
                    hit = True

                if not hit:
                    for r, c in color_rects:
                        if r.collidepoint(m_pos):
                            current_color = c
                            if editing_index != -1:
                                text_data[editing_index][IDX_COLOR] = c
                            hit = True
                            break

                if not hit:
                    for rr, idx2 in word_rects:
                        if rr.collidepoint(m_pos):
                            if ctrl:
                                if idx2 in group_selection:
                                    group_selection.remove(idx2)
                                else:
                                    group_selection.append(idx2)
                                ctrl_select_mode = True
                            else:
                                editing_index    = idx2
                                input_buffer     = text_data[idx2][IDX_WORD]
                                group_selection.clear()
                                ctrl_select_mode = False
                            hit = True
                            break

                if not hit:
                    editing_index = -1
                    input_buffer  = ""
                    if not ctrl:
                        group_selection.clear()
                        ctrl_select_mode = False

        if event.type == pygame.KEYDOWN:
            if note_edit_open:
                if event.key == pygame.K_BACKSPACE:
                    note_edit_buffer = note_edit_buffer[:-1]
                elif event.key == pygame.K_RETURN and ctrl:
                    if note_edit_index >= 0:
                        text_data[note_edit_index][IDX_NOTE] = note_edit_buffer.strip()
                    note_edit_open = False
                elif event.key == pygame.K_ESCAPE:
                    note_edit_open = False
                continue

            if bg_panel_open and bg_path_active:
                if event.key == pygame.K_BACKSPACE:
                    bg_path_input = bg_path_input[:-1]
                elif event.key == pygame.K_RETURN:
                    ok, err = bg.load(bg_path_input.strip(), bg_pick_target)
                    bg_error_msg   = "Loaded!" if ok else "Error: " + err[:42]
                    bg_error_timer = 2.6
                elif event.key == pygame.K_ESCAPE:
                    bg_panel_open  = False
                    bg_path_active = False
                continue

            if HAS_CLIP and state == "INPUT" and event.key == pygame.K_v and ctrl:
                pasted = pyperclip.paste()
                if editing_index != -1:
                    input_buffer += pasted
                else:
                    for w in pasted.strip().split():
                        text_data.append([w, current_color, False, False, False, False, -1, "", False])
                continue

            if event.key == pygame.K_ESCAPE:
                if state == "MENU":
                    pygame.quit()
                    sys.exit()
                else:
                    state         = "MENU"
                    editing_index = -1
                    input_buffer  = ""
                    bg_panel_open = False
                    group_selection.clear()

            if event.key == pygame.K_a and ctrl:
                if state == "INPUT":
                    text_data.clear()
                    input_buffer  = ""
                    editing_index = -1
                    group_selection.clear()
                elif state == "DISPLAY":
                    start_display_index = word_index
                    active_anims.clear()
                    is_cleared    = True
                    star_spawned.clear()
                    glow_spawned.clear()
                    glow_stars.clear()
                    glow_rings.clear()
                    bottom_note_widget = None
                continue

            if state == "INPUT":
                if event.key == pygame.K_BACKSPACE:
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                    elif text_data and editing_index == -1:
                        text_data.pop()
                elif event.key == pygame.K_SPACE:
                    if input_buffer.strip():
                        w = input_buffer.strip()
                        if editing_index != -1:
                            td = text_data[editing_index]
                            text_data[editing_index] = [w, td[IDX_COLOR], td[IDX_LISS],
                                td[IDX_FLASH], td[IDX_STAR], td[IDX_BURST],
                                td[IDX_GID], td[IDX_NOTE], td[IDX_GLOW]]
                            editing_index = -1
                        else:
                            text_data.append([w, current_color, False, False, False, False, -1, "", False])
                        input_buffer = ""
                elif event.key == pygame.K_RETURN:
                    if input_buffer.strip():
                        w = input_buffer.strip()
                        if editing_index != -1:
                            td = text_data[editing_index]
                            text_data[editing_index] = [w, td[IDX_COLOR], td[IDX_LISS],
                                td[IDX_FLASH], td[IDX_STAR], td[IDX_BURST],
                                td[IDX_GID], td[IDX_NOTE], td[IDX_GLOW]]
                        else:
                            text_data.append([w, current_color, False, False, False, False, -1, "", False])
                    input_buffer  = ""
                    editing_index = -1
                    state         = "MENU"

            elif state == "DISPLAY":
                if event.key == pygame.K_SPACE:
                    for a in active_anims:
                        a.flash_active = False
                    is_cleared         = False
                    bottom_note_widget = None
                    if word_index < len(text_data):
                        word_index += 1
                        if text_data[word_index - 1][IDX_LISS]:
                            start_display_index = word_index - 1
                            active_anims.clear()
                            star_spawned.clear()
                            glow_spawned.clear()
                    else:
                        word_index = 0
                        start_display_index = 0
                        active_anims.clear()
                        star_spawned.clear()
                        glow_spawned.clear()
                        is_cleared         = True
                        bottom_note_widget = None

                elif event.key == pygame.K_BACKSPACE:
                    word_index = 0
                    start_display_index = 0
                    active_anims.clear()
                    is_cleared  = True
                    star_spawned.clear()
                    glow_spawned.clear()
                    glow_stars.clear()
                    glow_rings.clear()
                    bottom_note_widget = None

                elif event.key == pygame.K_ESCAPE:
                    state         = "MENU"
                    editing_index = -1
                    input_buffer  = ""

    particles[:]  = [p for p in particles  if p.update(dt)]
    glow_stars[:] = [s for s in glow_stars if s.update(dt)]
    glow_rings[:] = [r for r in glow_rings if r.update(dt)]

    if state == "MENU" and not bg_panel_open:
        title_f = get_font(88, bold=True)
        ts = title_f.render("I miss you bani", True, C_WHITE)
        ts.set_alpha(235)
        screen.blit(ts, ts.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 210)))

        ver_s = get_font(21).render("", True, C_DIM)
        screen.blit(ver_s, ver_s.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 148)))

        for b, lbl, col, _ in [
            (btn_start, "START",      C_ACC,       False),
            (btn_edit,  "EDIT",       (75,75,90),  False),
            (btn_bg,    "BACKGROUND", (75,75,90),  False),
            (btn_quit,  "EXIT",       (115,45,45), False),
        ]:
            hov = b.collidepoint(m_pos)
            bc  = tuple(min(255, c + 28) for c in col) if hov else col
            pygame.draw.rect(screen, bc, b, border_radius=14)
            tsurf = get_font(27, bold=True).render(lbl, True, C_WHITE)
            screen.blit(tsurf, tsurf.get_rect(center=b.center))

        fslbl = "WINDOWED" if is_fullscreen else "FULLSCREEN"
        hov   = btn_fs.collidepoint(m_pos)
        pygame.draw.rect(screen, (60,60,73) if not hov else (82,82,98), btn_fs, border_radius=12)
        fs_s = get_font(17).render(fslbl, True, C_WHITE)
        screen.blit(fs_s, fs_s.get_rect(center=btn_fs.center))

        if bg.menu_path or bg.display_path:
            parts = []
            if bg.menu_path:    parts.append(f"Menu: …{bg.menu_path[-24:]}")
            if bg.display_path: parts.append(f"Display: …{bg.display_path[-24:]}")
            ss = get_font(15).render(" | ".join(parts), True, C_DIM)
            screen.blit(ss, ss.get_rect(center=(WIDTH // 2, HEIGHT - 48)))

        dh = get_font(14).render("", True, C_DIM)
        screen.blit(dh, dh.get_rect(center=(WIDTH // 2, HEIGHT - 28)))

        if bg_error_timer > 0:
            ec = (85, 215, 130) if "Loaded" in bg_error_msg else C_RED
            es = get_font(17).render(bg_error_msg, True, ec)
            screen.blit(es, es.get_rect(center=(WIDTH // 2, HEIGHT - 68)))

    if bg_panel_open:
        dim_s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim_s.fill((0, 0, 0, 165))
        screen.blit(dim_s, (0, 0))
        draw_panel(screen, bgp, radius=18, alpha=245)
        pygame.draw.rect(screen, (60, 60, 78), bgp, 2, border_radius=18)

        hdr = get_font(26, bold=True).render("Background Settings", True, C_WHITE)
        screen.blit(hdr, (bgp.x + 28, bgp.y + 22))

        sub = get_font(16).render("", True, C_DIM)
        screen.blit(sub, (bgp.x + 28, bgp.y + 62))

        ic = (55, 55, 78) if bg_path_active else (32, 32, 44)
        pygame.draw.rect(screen, ic, inp_rect, border_radius=10)
        pygame.draw.rect(screen, C_ACC if bg_path_active else C_DIM, inp_rect, 2, border_radius=10)
        dp = bg_path_input or "Paste or type image/video path here…"
        pc = C_WHITE if bg_path_input else C_DIM
        ps = get_font(17).render(dp[-58:], True, pc)
        screen.blit(ps, (inp_rect.x + 14, inp_rect.y + 16))
        if bg_path_active and int(global_timer * 2) % 2 == 0:
            cx2 = inp_rect.x + 16 + get_font(17).size(dp[-58:])[0]
            pygame.draw.line(screen, C_WHITE, (cx2, inp_rect.y + 12), (cx2, inp_rect.y + 38), 2)

        draw_btn(screen, btn_bp_imp, "Import", False, C_ACC, btn_bp_imp.collidepoint(m_pos), 18)
        for key, lbl, btn_r in [('menu','Menu',btn_bp_m), ('display','Display',btn_bp_d), ('both','Both',btn_bp_b)]:
            draw_btn(screen, btn_r, lbl, bg_pick_target == key, C_ACC, btn_r.collidepoint(m_pos))
        draw_btn(screen, btn_bp_ok,  "Load",  False, C_ACC,       btn_bp_ok.collidepoint(m_pos),  20)
        draw_btn(screen, btn_bp_clr, "Clear", False, (145,55,55), btn_bp_clr.collidepoint(m_pos), 20)
        draw_btn(screen, btn_bp_cls, "Close", False, (60,60,78),  btn_bp_cls.collidepoint(m_pos), 20)

        if bg_error_timer > 0:
            ec = (85, 215, 130) if ("Load" in bg_error_msg or "clear" in bg_error_msg.lower()) else C_RED
            es = get_font(17).render(bg_error_msg, True, ec)
            screen.blit(es, (bgp.x + 28, bgp.y + 284))

        py = bgp.y + 314
        for lbl, val in [("Menu:   ", bg.menu_path or "—"), ("Display:", bg.display_path or "—")]:
            t1 = get_font(15, bold=True).render(lbl, True, C_DIM)
            t2 = get_font(15).render(val[-44:] if val != "—" else val, True, C_WHITE)
            screen.blit(t1, (bgp.x + 28, py))
            screen.blit(t2, (bgp.x + 100, py))
            py += 22

    elif state == "INPUT" and not note_edit_open:
        for r, c in color_rects:
            pygame.draw.rect(screen, c, r, border_radius=8)
            if c == current_color:
                pygame.draw.rect(screen, C_WHITE, r.inflate(8, 8), 3, border_radius=8)

        sidebar_rect = pygame.Rect(EBX - 14, 14, EBW + 28,
                                   EBY_group + EBH * 2 + 8 * 3 + 14)
        draw_panel(screen, sidebar_rect, radius=14, alpha=160)

        for btn_r, lbl, col_a, eff_idx in eff_btns:
            active_e = editing_index != -1 and text_data[editing_index][eff_idx]
            hov      = btn_r.collidepoint(m_pos) and editing_index != -1
            draw_btn(screen, btn_r, lbl, active_e, col_a, hov, 17)
            if active_e:
                pygame.draw.circle(screen, col_a, (btn_r.right - 8, btn_r.top + 8), 5)

        group_active_display = (editing_index != -1 and
                                len(text_data) > editing_index and
                                text_data[editing_index][IDX_GID] >= 0)
        group_highlight = len(group_selection) >= 2 and ctrl
        g_hov = btn_group.collidepoint(m_pos)
        pygame.draw.rect(screen,
                         C_GROUP if (group_active_display or group_highlight)
                         else ((100, 100, 115) if g_hov else (60, 60, 75)),
                         btn_group, border_radius=12)
        glbl = get_font(16, bold=True).render("GROUP", True, C_WHITE)
        screen.blit(glbl, glbl.get_rect(center=btn_group.center))
        if group_highlight:
            pygame.draw.rect(screen, C_GROUP, btn_group, 2, border_radius=12)

        note_active = (editing_index != -1 and len(text_data) > editing_index
                       and text_data[editing_index][IDX_NOTE])
        n_col = C_NOTE if note_active else ((100, 100, 115) if btn_note.collidepoint(m_pos) else (60, 60, 75))
        pygame.draw.rect(screen, n_col, btn_note, border_radius=12)
        nlbl = get_font(16, bold=True).render("NOTE", True, C_BG if note_active else C_WHITE)
        screen.blit(nlbl, nlbl.get_rect(center=btn_note.center))

        if ctrl:
            gh = get_font(13).render(
                f"CTRL held — click word to multi-select ({len(group_selection)} selected)",
                True, C_GROUP)
            screen.blit(gh, (28, swatch_y0 + 2 * (SWATCH_H + 6) + 6))

        draw_panel(screen, box, radius=14, alpha=185)
        pygame.draw.rect(screen, (50, 50, 65), box, 1, border_radius=14)

        f_inp = get_font(max(30, box.height // 35), bold=True)
        lh    = f_inp.get_linesize()
        sp_w  = f_inp.size(" ")[0] * NEN_NGANG
        word_rects.clear()
        lines, cur_line, cur_x = [], [], 0
        max_bw = box.width - 48

        for i, (word, col, liss, fl, st, bu, gid, note, glow) in enumerate(text_data):
            disp_t = input_buffer if i == editing_index else word
            disp_c = current_color if i == editing_index else col
            ww     = f_inp.size(disp_t)[0] * NEN_NGANG
            gap    = 0 if (cur_line and cur_line[-1][6] >= 0 and cur_line[-1][6] == gid) else sp_w
            if cur_x + gap + ww > max_bw:
                lines.append(cur_line)
                cur_line = [(disp_t, disp_c, ww, i, liss, fl, st, bu, gid, note, glow)]
                cur_x    = ww
            else:
                cur_line.append((disp_t, disp_c, ww, i, liss, fl, st, bu, gid, note, glow))
                cur_x += gap + ww

        if cur_line:
            lines.append(cur_line)

        if input_buffer and editing_index == -1:
            ww    = f_inp.size(input_buffer)[0] * NEN_NGANG
            entry = (input_buffer, current_color, ww, -1, False, False, False, False, -1, "", False)
            if not lines or cur_x + ww > max_bw:
                lines.append([entry])
            else:
                lines[-1].append(entry)

        max_vis  = max(1, (box.height - 36) // lh)
        vis_lines = lines[-max_vis:]
        sy = box.top + 20

        for ri, row in enumerate(vis_lines):
            dx, dy = box.left + 24, sy + ri * lh
            for j, (disp_t, disp_c, ww, idx2, liss, fl, st, bu, gid, note, glow) in enumerate(row):
                r = pygame.Rect(dx, dy, ww, lh)
                if idx2 >= 0:
                    word_rects.append((r, idx2))

                if idx2 == editing_index:
                    hs = pygame.Surface((ww + 12, lh + 4), pygame.SRCALPHA)
                    pygame.draw.rect(hs, (85, 115, 195, 88), (0, 0, ww + 12, lh + 4), border_radius=8)
                    screen.blit(hs, (dx - 6, dy - 2))

                if idx2 in group_selection:
                    gs2 = pygame.Surface((ww + 12, lh + 4), pygame.SRCALPHA)
                    pygame.draw.rect(gs2, (*C_GROUP, 60),  (0, 0, ww + 12, lh + 4), border_radius=8)
                    pygame.draw.rect(gs2, (*C_GROUP, 180), (0, 0, ww + 12, lh + 4), 2, border_radius=8)
                    screen.blit(gs2, (dx - 6, dy - 2))

                if gid >= 0:
                    pygame.draw.rect(screen, (*C_GROUP, 100),
                                     pygame.Rect(dx - 2, dy + lh - 3, ww + 4, 3))

                dot_x = dx + ww + 5
                for eflag, ecol in [
                    (liss,   (0,225,165)),
                    (fl,     (255,215,30)),
                    (st,     (255,160,40)),
                    (bu,     (255,85,185)),
                    (glow,   C_GLOW),
                    (gid >= 0, C_GROUP),
                    (bool(note), C_NOTE),
                ]:
                    if eflag:
                        pygame.draw.circle(screen, ecol, (int(dot_x), int(dy + lh // 2)), 4)
                        dot_x += 10

                ws = pygame.transform.smoothscale(
                    f_inp.render(disp_t, True, disp_c), (int(ww), lh))
                screen.blit(ws, (dx, dy))

                if j + 1 < len(row):
                    nxt_gid = row[j + 1][8]
                    dx += ww + (0 if (gid >= 0 and nxt_gid == gid) else sp_w)
                else:
                    dx += ww + sp_w

        if int(global_timer * 2) % 2 == 0:
            if word_rects:
                lr, _ = word_rects[-1]
                cdx, cdy = lr.right + 6, lr.top
            else:
                cdx, cdy = box.left + 24, box.top + 20
            pygame.draw.line(screen, C_ACC, (cdx, cdy), (cdx, cdy + lh - 4), 3)

        hints = ["SPACE=confirm", "ENTER=finish", "BKSP=delete",
                 "CTRL+A=clear", "Click=edit", "CTRL+Click=group"]
        hx = 28
        for hi in hints:
            hs = get_font(13).render(hi, True, C_DIM)
            if hx + hs.get_width() < WIDTH - EBW - 40:
                screen.blit(hs, (hx, HEIGHT - 42))
                hx += hs.get_width() + 20

        for p in particles:
            p.draw(screen)

    if note_edit_open:
        dim_s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim_s.fill((0, 0, 0, 155))
        screen.blit(dim_s, (0, 0))
        draw_panel(screen, nep, radius=16, alpha=248)
        pygame.draw.rect(screen, (*C_NOTE, 180), nep, 2, border_radius=16)

        wn   = (text_data[note_edit_index][IDX_WORD] if 0 <= note_edit_index < len(text_data) else "")
        hdr2 = get_font(22, bold=True).render(f'Note for: "{wn}"', True, C_WHITE)
        screen.blit(hdr2, (nep.x + 24, nep.y + 20))
        sub2 = get_font(14).render("Note", True, C_DIM)
        screen.blit(sub2, (nep.x + 24, nep.y + 52))

        pygame.draw.rect(screen, (32, 32, 44), ne_inp, border_radius=10)
        pygame.draw.rect(screen, C_NOTE, ne_inp, 2, border_radius=10)

        f_ne    = get_font(18, bold=False)
        wrapped = textwrap.wrap(note_edit_buffer or " ",
                                width=max(1, ne_inp.width // (f_ne.size("a")[0] + 1)))
        for li, line in enumerate(wrapped[-4:]):
            ls = f_ne.render(line, True, C_WHITE if note_edit_buffer else C_DIM)
            screen.blit(ls, (ne_inp.x + 12, ne_inp.y + 10 + li * f_ne.get_linesize()))
        if not note_edit_buffer:
            ph = f_ne.render("Type note here…", True, C_DIM)
            screen.blit(ph, (ne_inp.x + 12, ne_inp.y + 10))
        if int(global_timer * 2) % 2 == 0:
            last_line = wrapped[-1] if wrapped else ""
            cx3 = ne_inp.x + 14 + f_ne.size(last_line)[0]
            cy3 = (ne_inp.y + 10 + (len(wrapped[-4:]) - 1) * f_ne.get_linesize()
                   if wrapped else ne_inp.y + 10)
            pygame.draw.line(screen, C_NOTE, (cx3, cy3), (cx3, cy3 + f_ne.get_linesize() - 4), 2)

        draw_btn(screen, btn_ne_ok,  "Save",   False, (60,180,100), btn_ne_ok.collidepoint(m_pos),  17)
        draw_btn(screen, btn_ne_clr, "Clear",  False, (145,55,55),  btn_ne_clr.collidepoint(m_pos), 17)
        draw_btn(screen, btn_ne_cls, "Cancel", False, (60,60,78),   btn_ne_cls.collidepoint(m_pos), 17)

    elif state == "DISPLAY":
        flash_on_now      = math.sin(flash_timer * FLASH_SPEED * math.pi * 2) > 0
        fullscreen_flash  = any(a.flash and a.liss and a.flash_active for a in active_anims)

        if fullscreen_flash and flash_on_now:
            screen.fill((248, 248, 248))
            bg.draw(screen, 'display', WIDTH, HEIGHT, dim=0.06)
        else:
            bg.draw(screen, 'display', WIDTH, HEIGHT, dim=0.38)

        if is_cleared:
            df  = get_font(108, bold=True)
            dsp = 92
            dbx = WIDTH // 2 - dsp
            dby = HEIGHT // 2
            for di in range(3):
                phase = global_timer * 2.2 + di * 0.65
                oy    = math.sin(phase) * 19
                sc2   = 0.72 + 0.28 * (math.sin(phase) * .5 + .5)
                av    = int(65 + 195 * (math.sin(phase) * .5 + .5))
                ds    = df.render("•", True, C_WHITE)
                nsw   = max(1, int(ds.get_width()  * sc2))
                nsh   = max(1, int(ds.get_height() * sc2))
                dsc   = pygame.transform.smoothscale(ds, (nsw, nsh))
                dsc.set_alpha(av)
                screen.blit(dsc, (dbx + di * dsp - nsw // 2, int(dby - nsh // 2 + oy)))

            ht = get_font(19).render("...", True, C_DIM)
            ht.set_alpha(int(120 + 135 * math.sin(global_timer * 1.6)))
            screen.blit(ht, ht.get_rect(center=(WIDTH // 2, HEIGHT - 64)))
        else:
            cur_list = text_data[start_display_index:word_index]
            cur_h    = hash(tuple(tuple(row) for row in cur_list))

            if cur_h != last_hash:
                group_counters = {}
                c_size, c_data = calc_layout(cur_list, WIDTH - MARGIN_W * 2, HEIGHT - MARGIN_H * 2)
                last_hash = cur_h

            while len(active_anims) > len(c_data):
                active_anims.pop()

            for i, (word, tx, ty, col, liss, flash, star, burst, gid, note, glow) in enumerate(c_data):
                if i < len(active_anims):
                    active_anims[i].update(dt, tx, ty, c_size, flash_on_now)
                else:
                    delay = 0.0
                    if gid >= 0:
                        if gid not in group_counters:
                            group_counters[gid] = 0
                        delay = group_counters[gid] * 0.10
                        group_counters[gid] += 1

                    n = WordAnim(word, tx, ty, col,
                                 liss=liss, flash=flash, star=star,
                                 burst=burst, glow=glow, group_id=gid,
                                 note=note, word_idx=i, group_delay=delay)
                    n.update(dt, tx, ty, c_size, flash_on_now)
                    active_anims.append(n)

                    if note and bottom_note_widget is None:
                        bottom_note_widget = BottomNote(note)
                    elif note and bottom_note_widget is not None and bottom_note_widget.text != note:
                        bottom_note_widget = BottomNote(note)

                if star and i not in star_spawned:
                    a = active_anims[i]
                    if a.alpha > 20:
                        est_w = int(c_size * len(word) * 0.56 * NEN_NGANG)
                        est_h = int(c_size * 1.12)
                        spawn_particles(int(a.cur_x), int(a.cur_y), est_w, est_h, 74)
                        star_spawned.add(i)

                if glow and i not in glow_spawned:
                    a = active_anims[i]
                    if a.alpha > 20:
                        spawn_glow_effect(int(a.cur_x), int(a.cur_y),
                                          col, WIDTH, HEIGHT, n_stars=24, n_rings=5)
                        glow_spawned.add(i)

            for p in particles:
                p.draw(screen)
            for gs in glow_stars:
                gs.draw(screen)
            for gr in glow_rings:
                gr.draw(screen)

            for anim in active_anims:
                local = flash_on_now and not fullscreen_flash
                anim.draw(screen, local_flash_on=local)

            if bottom_note_widget:
                bottom_note_widget.update(dt)
                bottom_note_widget.draw(screen)

    sig = get_font(13).render("Clarx - Tiktok | i miss you kowaies", True, (55, 55, 68))
    screen.blit(sig, (WIDTH - sig.get_width() - 16, HEIGHT - 24))

    pygame.display.flip()