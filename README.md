# 🦖👅 Steve the Freakysaur

> control a dinosaur with your tongue. no really. stick your tongue out and watch the magic happen ✨

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/pygame-2.5.2-green.svg)
![OpenCV](https://img.shields.io/badge/opencv-4.9.0-red.svg)
![MediaPipe](https://img.shields.io/badge/mediapipe-0.10.14-orange.svg)

## 🎮 what is this?

imagine flappy bird met chrome's dinosaur game and they had a baby that's controlled by your tongue. that's steve the freakysaur. using computer vision and AI-powered face detection, this game lets you jump and duck by sticking your tongue out (or just use your keyboard if you're boring 😛).

it's a mashup of three games in one:
- 🦕 classic dino endless runner (dodge cacti and birds)
- 🐦 flappy bird clone (navigate through pipes)
- 👯 two-player competitive mode (battle your friends with your tongues out)

the webcam watches your face in real-time, detects when you stick your tongue out, and makes your dino jump. it's ridiculous. it's amazing. it's exactly what the internet needed.

**🌐 try it online:** [freakysaur.vercel.app](https://freakysaur.vercel.app)

## ✨ features

- 👅 **tongue-controlled gameplay** - opencv + mediapipe detect your tongue in real-time
- 🎥 **live webcam preview** - see yourself looking absolutely ridiculous while playing
- 🎯 **direction detection** - tongue pointing up/down/left/right for advanced controls
- ⌨️ **keyboard fallback** - for the tongue-shy among us
- 🎨 **pixel-perfect collision** - mask-based detection just like the classics
- 🏃 **progressive difficulty** - gets faster as your score increases
- 🎭 **smooth animations** - running, jumping, ducking, and dying in style
- 👫 **multiplayer mode** - compete head-to-head (tongue-to-tongue?)
- 🔄 **duo tongue restart** - both players hold tongue out for 3 seconds to quick-restart
- 📊 **score tracking** - beat your personal best

## 🚀 quick start

### prerequisites

you'll need python 3.8 or higher. that's pretty much it!

### installation

1. **clone this bad boy**
   ```bash
   git clone https://github.com/diwenne/freakysaur.git
   cd freakysaur
   ```

2. **set up virtual environment** (recommended)
   ```bash
   python -m venv .venv

   # on macOS/Linux:
   source .venv/bin/activate

   # on Windows:
   .venv\Scripts\activate
   ```

3. **install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **grant camera permissions**
   - on macOS: System Preferences → Security & Privacy → Camera → allow Terminal/your IDE
   - on Windows: Settings → Privacy → Camera → allow apps to access camera
   - on Linux: usually just works™

### running the games

**single-player dino runner:**
```bash
python game_dino.py
```

**flappy bird mode:**
```bash
python game_flappy.py
```

**two-player battle:**
```bash
python game_dino_2p.py
```

**disable tongue control** (keyboard only):
```bash
python game_dino.py --no-tongue
```

## 🎯 how to play

### controls

**single-player dino:**
- 👅 stick out tongue = jump
- ⬆️ space/up arrow = jump
- ⬇️ down arrow = duck
- ESC = quit

**flappy bird:**
- 👅 stick out tongue = flap
- ⬆️ space/up arrow/mouse click = flap
- ESC = quit

**two-player mode:**
- **player 1 (top lane):**
  - 👅 tongue = jump
  - ⬆️ space/up arrow = jump
  - ⬇️ down arrow = duck

- **player 2 (bottom lane):**
  - 👅 tongue = jump
  - W = jump
  - S = duck

- **special:** both players hold tongue out for 3 seconds = quick restart 🔄

### gameplay tips

- make sure your face is well-lit and visible to the webcam
- the game needs to see your full mouth to detect tongue
- open your mouth wide when sticking tongue out for best detection
- the game has a 120ms debounce, so rapid tongue flicks won't work
- duck under flying birds in dino mode!
- in multiplayer, round ends when either player dies
- higher scorer gets to control the world speed in multiplayer

## 🏗️ project structure

```
tongue_jump/
├── game_dino.py            # single-player dino runner
├── game_flappy.py          # flappy bird variant
├── game_dino_2p.py         # two-player competitive mode
├── tongue_switch.py        # single-player tongue detection engine
├── tongue_switch_2p.py     # multi-player tongue detection engine
├── requirements.txt        # python dependencies
├── assets/                 # game sprites and images
│   ├── Dino/              # dinosaur animations
│   ├── Bird/              # flying enemy sprites
│   ├── Cactus/            # obstacle sprites
│   ├── Flap/              # flappy bird assets
│   └── Other/             # UI elements (track, clouds, game over)
└── .venv/                 # virtual environment (create this)
```

## 🧠 how it works

the tongue detection uses a multi-stage computer vision pipeline:

1. **face detection** - mediapipe finds your face and 468 facial landmarks
2. **mouth isolation** - extracts just the inner lip area (20 landmarks)
3. **color detection** - hsv color space filtering for red tones (tongue)
4. **noise reduction** - median blur + morphological operations
5. **threshold calculation** - if red pixels > 6% of mouth area = tongue detected! 👅
6. **direction classification** - compares tongue centroid to mouth center
7. **debouncing** - 120ms cooldown prevents false triggers
8. **state management** - threaded capture for smooth 60fps gameplay

all running in real-time at 60fps while the game runs in the main thread. pretty neat!

## 🏆 stats & achievements

- 🎯 **won daydream** at [Hack Club Daydream](https://daydream.hackclub.com)
- 👀 **200k+ LinkedIn impressions** - people love watching others play with their tongues out
- 🦖 built with mediapipe's 468-point face mesh detection
- ⚡ runs at smooth 60fps with threaded camera processing
- 🎨 pixel-perfect collision detection
- 🌈 supports macOS, Windows, and Linux

## 🔧 technical details

**dependencies:**
- `pygame 2.5.2` - game engine and rendering
- `opencv-python 4.9.0.80` - computer vision and image processing
- `mediapipe 0.10.14` - face mesh and landmark detection

**performance:**
- 60 fps game loop
- threaded camera capture (30 fps)
- 900×820 window (260px webcam preview + 560px game panel)
- progressive difficulty scaling
- graceful camera fallback if detection unavailable

**physics:**
- dino gravity: 2500 px/s²
- dino jump velocity: -900 px/s
- flappy bird gravity: 1000 px/s²
- flappy bird flap velocity: -400 px/s

## 🐛 troubleshooting

**camera won't open:**
- check camera permissions for terminal/IDE
- close other apps using camera (zoom, teams, etc.)
- try `--no-tongue` flag to play with keyboard only

**tongue detection not working:**
- ensure good lighting on your face
- face the camera straight-on
- open mouth wide when sticking tongue out
- adjust `frac_threshold` in tongue_switch.py if too sensitive/insensitive

**game running slow:**
- close other applications
- update graphics drivers
- reduce window size (edit source if needed)

**import errors:**
- make sure virtual environment is activated
- reinstall requirements: `pip install -r requirements.txt`

## 🤝 contributing

this is a weird art project / game hybrid. if you want to make it weirder, feel free to fork it and go wild! some ideas:

- add sound effects (especially tongue sounds)
- more tongue gestures (roll tongue = power-up?)
- online multiplayer (tongue battles across the internet)
- mobile version (front-facing camera gameplay)
- different dinosaur skins
- power-ups and collectibles
- leaderboards
- tongue speed detection for variable jump height

## 📝 license

do whatever you want with this. make cool stuff. make weird stuff. just credit me if you show it off!

## 🙏 credits

built by a crazy person who thought "what if i controlled games with my tongue?" and then actually did it.

powered by:
- mediapipe (google's amazing face detection)
- opencv (computer vision workhorse)
- pygame (game dev made easy)
- chrome's dino runner (inspiration)
- flappy bird (inspiration)
- way too much caffeine ☕

---

made with 💚 and 👅 | if you play this in public, don't blame me for the weird looks you get
