#!/usr/bin/env python3
import os, json, socket, threading, queue, time, hashlib, logging, re
import urllib.request, webbrowser, platform, subprocess, tkinter as tk
import base64
from tkinter import ttk, messagebox, simpledialog, filedialog
try:
    import pyaudio
    AUDIO_OK = True
except Exception:
    AUDIO_OK = False

APP_NAME = "LANchat Pro"
VERSION = "V.1.0.7"
APP_MAGIC = "LNCP"
TCP_PORT = 5555
UDP_PORT = 5556
SCAN_TIME = 3.0
ANNOUNCE_EVERY = 2.0
MAX_PSEUDO = 18
RECV_BUF = 65536
COMPTE_FILE = "comptes_lanchat.txt"
SLOTS_FILE = "slots_lanchat.json"
APP_SECRET = b"LANchatPro_2024_SecretKey!"
SPINNER = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
A_RATE, A_CHAN, A_CHUNK = 44100, 1, 4096
A_FMT = None

THEMES = {
    "sombre": {
        "bg":"#11111b","bg2":"#181825","surf":"#1e1e2e","surf2":"#313244",
        "inp":"#45475a","text":"#cdd6f4","sub":"#a6adc8","dim":"#6c7086",
        "blue":"#89b4fa","green":"#a6e3a1","red":"#f38ba8","yellow":"#f9e2af",
        "purple":"#cba6f7","pink":"#f5c2e7","teal":"#94e2d5","accent":"#f5c2e7",
        "grad1":"#1e1e2e","grad2":"#181825",
    },
    "clair": {
        "bg":"#eff1f5","bg2":"#e6e9ef","surf":"#dce0e8","surf2":"#ccd0da",
        "inp":"#acb0be","text":"#4c4f69","sub":"#6c6f85","dim":"#9ca0b0",
        "blue":"#1e66f5","green":"#40a02b","red":"#d20f39","yellow":"#df8e1d",
        "purple":"#7287fd","pink":"#ea76cb","teal":"#179299","accent":"#ea76cb",
        "grad1":"#dce0e8","grad2":"#ccd0da",
    },
}

def _appliquer_theme(nom):
    global C_BG, C_BG2, C_SURF, C_SURF2, C_INP, C_TEXT, C_SUB, C_DIM
    global C_BLUE, C_GREEN, C_RED, C_YELLOW, C_PURPLE, C_PINK, C_TEAL, C_ACCENT
    global C_GRAD1, C_GRAD2
    t = THEMES.get(nom, THEMES["sombre"])
    C_BG=t["bg"]; C_BG2=t["bg2"]; C_SURF=t["surf"]; C_SURF2=t["surf2"]
    C_INP=t["inp"]; C_TEXT=t["text"]; C_SUB=t["sub"]; C_DIM=t["dim"]
    C_BLUE=t["blue"]; C_GREEN=t["green"]; C_RED=t["red"]; C_YELLOW=t["yellow"]
    C_PURPLE=t["purple"]; C_PINK=t["pink"]; C_TEAL=t["teal"]
    C_ACCENT=t.get("accent",C_PINK)
    C_GRAD1=t.get("grad1",C_SURF); C_GRAD2=t.get("grad2",C_BG2)

_appliquer_theme("sombre")
FONT = "Segoe UI"

EMOJI_DIR = "emojis_lanchat"
EMOJIS = {
    "Smileys": ["😀","😂","🥰","😎","🤔","😴","😭","😡","🤯","🥳","😱","🤗","🤩","😇","🤓","🙃","😜","😝","🤪","🥺","😤","🥶","🤒","🤧"],
    "Gestes": ["👍","👎","👏","🙏","💪","✌️","🤙","🤝","✋","👊","🫶","🙌","🤞","🤟","👌","👋","🫰","🤜","🫲","🫱","👋","🤚","🖐️","✍️"],
    "Cœur": ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","💖","💝","💘","💔","❣️","💕","💞","💟","♥️","🫶","💟","💌"],
    "Objets": ["🔥","⭐","✨","💎","🎉","🎁","🏆","🚀","💰","🎯","💡","🎵","🎮","📱","💻","☕","🖥️","⌨️","🖱️","🔋","📌","📎","🔔","🔑"],
    "Nature": ["🌈","☀️","🌙","⚡","❄️","🌊","🌸","🍀","🌟","🌻","🐶","🐱","🦄","🐉","🔥","🌌","🏔️","🌋","🌅","🌠","🌳","🌺","🍄","☀️"],
    "Nourriture": ["🍕","🍔","🍟","🌮","🍩","🎂","🍓","🍉","🥑","🍿","🍫","🥤","🍣","🍜","🍪","🍇","🧁","🍰","🥗","🧋","🍬","🥨","🧀","🍗"],
    "Drapeaux": ["🇫🇷","🇬🇧","🇺🇸","🇪🇸","🇮🇹","🇩🇪","🇯🇵","🇨🇦","🇧🇪","🇨🇭","🇵🇹","🇲🇦","🇸🇳","🇧🇷","🇲🇽","🇮🇳","🇨🇳","🇰🇷","🇦🇺","🇷🇺","🌍","🏴","🏳️","🏁"],
    "Activités": ["⚽","🏀","🎮","🎧","🎨","📸","🎬","🎸","🎤","🎹","🥁","🎲","🎳","🎯","♟️","🏆","🥊","🏸","🏓","🏊","🚴","⛷️","🏂","🤸"],
    "Symboles": ["💯","✅","❌","⭕","❓","❗","💢","💥","💫","💦","💨","🏁","🔔","🔕","📢","💬","💤","♻️","✴️","🆗","🆒","🆕","🆓","🔞"],
    "Animaux": ["🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐨","🦁","🐯","🦄","🐉","🦖","🐙","🦋","🐢","🐬","🦉","🦅","🐝","🐞","🦜","🐠"],
    "Tech": ["💻","⌨️","🖥️","🖨️","🖱️","💿","💾","📱","📞","📡","🔌","🔋","💡","🔧","⚙️","🧰","🛠️","📡","📷","🎥","🕹️","🗜️","🧮","📊"],
    "Divers": ["🎪","🎭","🎨","🎬","🎤","🎧","🎼","🎹","🥁","🎷","🎺","🎸","🪕","🎻","🎲","🎯","🎳","🎰","🃏","🀄","♟️","🎭","🎟️","🎫"],
    "Fêtes": ["🎉","🎊","🎈","🎂","🎁","🎀","🛍️","🍾","🥂","🎆","🎇","✨","🎄","🎃","🏮","🎋","🎍","🎌","🎎","🎏","🎐","🎑","🎀","🎁"],
    "Météo": ["☀️","🌤️","⛅","🌥️","☁️","🌦️","🌧️","⛈️","🌩️","🌨️","❄️","🌬️","💨","🌪️","🌫️","🌈","☔","💧","🌊","🔥","🌡️","🌙","⚡","⛄"],
    "Transports": ["🚗","🚕","🚙","🚌","🚎","🏎️","🚓","🚑","🚒","🚐","🚚","🚛","🚜","🏍️","🛵","✈️","🚀","🛸","🚁","⛵","🚤","🚂","🚆","🚇"],
    "Voyages": ["🏔️","🌋","🏝️","🏖️","🏜️","🌳","🏕️","⛺","🏰","🏯","🗼","🗽","🗿","⛩️","🕌","🕍","⛪","🗺️","🧭","🚂","🌉","🌃","🌅","🌄"],
    "Sport": ["⚽","🏀","🏈","⚾","🥎","🎾","🏐","🏉","🥏","🎱","🏓","🏸","🥊","🥋","⛳","🏌️","🏇","🚴","🚵","🏅","🥇","🥈","🥉","🏆"],
    "Zodiaque": ["♈","♉","♊","♋","♌","♍","♎","♏","♐","♑","♒","♓","⛎","🔮","🌟","⭐","✨","💫","🌙","☀️","⚡","❄️","🔥","💧"],
    "Nourriture+": ["🍝","🥘","🍲","🍛","🍤","🥟","🍱","🍘","🍙","🍚","🍢","🍡","🍧","🍨","🥧","🧇","🥞","🧈","🧂","🥫","🧊","🍖","🍗","🥩"],
    "Boissons": ["☕","🍵","🥤","🧋","🧃","🧉","🍷","🍺","🍻","🥃","🍸","🍹","🍾","🥛","🧊","🍶","🚰","🧉","🥤","🍵","🍷","🍺","🧃","🍹"],
    "Jeux": ["🎮","🕹️","👾","🎲","🃏","🀄","♟️","🎯","🎳","🎰","🧩","🪀","🪁","🪅","🎰","🃏","♟️","🎯","🎮","🕹️","👾","🎲","🧩","🪁"],
}

SONS_PRESETS = {
    "notif_doux": "https://www.soundjay.com/buttons/sounds/beep-07a.mp3",
    "notif_classique": "https://www.soundjay.com/buttons/sounds/button-09.mp3",
    "notif_pop": "https://www.soundjay.com/misc/sounds/pop-2.mp3",
    "notif_alerte": "https://www.soundjay.com/buttons/sounds/button-10.mp3",
    "sonnerie_retro": "https://www.soundjay.com/phone/sounds/telephone-ring-01.mp3",
    "sonnerie_modern": "https://www.soundjay.com/phone/sounds/ringtone-1.mp3",
    "sonnerie_digitale": "https://www.soundjay.com/phone/sounds/digital-phone-1.mp3",
    "message_envoye": "https://www.soundjay.com/buttons/sounds/button-09.mp3",
    "connexion": "https://www.soundjay.com/misc/sounds/dial-up-modem-1.mp3",
    "erreur": "https://www.soundjay.com/buttons/sounds/button-2.mp3",
}

URL_RE = re.compile(r'(https?://[^\s<>"\']+|file://[^\s<>"\']+|www\.[^\s<>"\']+|[A-Za-z0-9._\\/-]+\.(?:mp4|webm|gif|mp3|wav|jpg|jpeg|png|mov|mkv))', re.I)

def _normalise_url(u):
    if u.lower().startswith(("http://","https://","file://")): return u
    if u.lower().startswith("www."): return "http://"+u
    return None

def _lister_emojis_perso():
    if not os.path.isdir(EMOJI_DIR): return []
    out = []
    for f in sorted(os.listdir(EMOJI_DIR)):
        if f.lower().endswith((".png",".gif",".jpg",".jpeg",".webp",".bmp")):
            out.append(f)
    return out

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("lanchat")

COULEURS = {
    "bleu":{"nom":"Bleu Glacier","hex":"#89b4fa","prix":0},
    "vert":{"nom":"Vert Émeraude","hex":"#a6e3a1","prix":0},
    "rouge":{"nom":"Rouge Lave","hex":"#f38ba8","prix":50},
    "violet":{"nom":"Violet Néon","hex":"#cba6f7","prix":80},
    "or":{"nom":"Or Royal","hex":"#f9e2af","prix":150},
    "cyan":{"nom":"Cyan Océan","hex":"#94e2d5","prix":100},
    "rose":{"nom":"Rose Bonbon","hex":"#f5c2e7","prix":120},
    "lavande":{"nom":"Lavande","hex":"#b4befe","prix":90},
    "corail":{"nom":"Corail Sunset","hex":"#eba0ac","prix":110},
    "menthol":{"nom":"Menthol","hex":"#a6d189","prix":110},
    "galaxy":{"nom":"Galaxy (animé)","hex":"#cba6f7","prix":250,"anime":True},
    "feu":{"nom":"Feu (animé)","hex":"#f38ba8","prix":250,"anime":True},
    "arc":{"nom":"Arc-en-ciel (animé)","hex":"#89b4fa","prix":400,"anime":True},
}

BADGES = {
    "aucun":{"nom":"Aucun","emoji":"","prix":0},
    "etoile":{"nom":"Étoile","emoji":"⭐","prix":0},
    "feu":{"nom":"On Fire","emoji":"🔥","prix":50},
    "rico":{"nom":"Riche","emoji":"💎","prix":150},
    "vip":{"nom":"VIP","emoji":"🚀","prix":120},
    "roi":{"nom":"Légende","emoji":"👑","prix":200},
    "coeur":{"nom":"Cœur d'or","emoji":"💛","prix":180},
    "foudre":{"nom":"Foudre","emoji":"⚡","prix":160},
    "trophy":{"nom":"Champion","emoji":"🏆","prix":300},
    "dragon":{"nom":"Dragon","emoji":"🐉","prix":500},
    "galaxie":{"nom":"Galaxie","emoji":"🌌","prix":450},
    "crystal":{"nom":"Crystal","emoji":"🔮","prix":350},
    "ninja":{"nom":"Ninja","emoji":"🥷","prix":280},
    "robot":{"nom":"Robot","emoji":"🤖","prix":320},
    "arc_en_ciel":{"nom":"Arc-en-ciel","emoji":"🌈","prix":550},
}

TITRES = {
    "membre":{"nom":"Membre","prix":0},
    "newbie":{"nom":"Petit Nouveau","prix":0},
    "bavard":{"nom":"Bavard","prix":60},
    "sociable":{"nom":"Sociable","prix":90},
    "veteran":{"nom":"Vétéran","prix":120},
    "pro":{"nom":"Pro du réseau","prix":180},
    "star":{"nom":"Star du salon","prix":250},
    "influent":{"nom":"Influent","prix":300},
    "mythe":{"nom":"Mythe vivant","prix":500},
    "boss":{"nom":"Boss du LAN","prix":600},
    "legende":{"nom":"Légende Éternelle","prix":800},
    "gamer":{"nom":"Gamer Pro","prix":220},
    "createur":{"nom":"Créateur","prix":350},
    "flamme":{"nom":"Flamme Éternelle","prix":700},
}

COULEURS_DEFAUT = "bleu"; BADGE_DEFAUT = "etoile"; TITRE_DEFAUT = "membre"

def couleur_hex(cid): return COULEURS.get(cid, COULEURS[COULEURS_DEFAUT])["hex"]
def couleur_anime(cid): return COULEURS.get(cid, {}).get("anime", False)
def badge_emoji(bid): return BADGES.get(bid, BADGES[BADGE_DEFAUT])["emoji"]
def titre_nom(tid): return TITRES.get(tid, TITRES[TITRE_DEFAUT])["nom"]

def _paliers():
    seuils = [0]; step = 100; total = 0
    for _ in range(200):
        total += step; seuils.append(total); step = int(step * 1.15)
    return seuils
_SEUILS = _paliers()

def niveau_from_xp(xp):
    niv = 0
    for i in range(1, len(_SEUILS)):
        if xp >= _SEUILS[i]: niv = i
        else: break
    return niv, _SEUILS[niv+1] - xp

def info_niveau(xp):
    niv = 0
    for i in range(1, len(_SEUILS)):
        if xp >= _SEUILS[i]: niv = i
        else: break
    return niv, xp - _SEUILS[niv], _SEUILS[niv+1] - _SEUILS[niv]

SALONS_DEFAUT = [
    {"nom":"général","type":"texte","desc":"Discussion générale"},
    {"nom":"annonces","type":"texte","desc":"Annonces importantes"},
    {"nom":"blabla","type":"texte","desc":"Pour parler de tout et de rien"},
    {"nom":"vocal","type":"vocal","desc":"Salon vocal principal"},
]

def _xor_cipher(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def _chiffrer_json(obj, key: bytes = None) -> bytes:
    if key is None: key = APP_SECRET
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    salt = os.urandom(8)
    k = hashlib.sha256(key + salt).digest()
    enc = _xor_cipher(raw, k)
    blob = salt + enc
    return base64.b85encode(blob)

def _dechiffrer_json(blob: bytes, key: bytes = None):
    if key is None: key = APP_SECRET
    try:
        raw = base64.b85decode(blob)
        salt = raw[:8]; enc = raw[8:]
        k = hashlib.sha256(key + salt).digest()
        data = _xor_cipher(enc, k)
        return json.loads(data.decode("utf-8"))
    except Exception: return None

class GestionnaireComptes:
    def __init__(self, chemin):
        self.chemin = chemin; self.comptes = {}; self._charger()
    def _charger(self):
        if not os.path.exists(self.chemin): return
        try:
            with open(self.chemin, "rb") as f: blob = f.read().strip()
            if not blob: self.comptes = {}; return
            if blob.startswith(b"{"):
                with open(self.chemin, "r", encoding="utf-8") as f: self.comptes = json.load(f)
                self._sauver()
            else:
                dec = _dechiffrer_json(blob)
                self.comptes = dec if dec is not None else {}
        except Exception: self.comptes = {}
    def _sauver(self):
        try:
            blob = _chiffrer_json(self.comptes)
            with open(self.chemin, "wb") as f: f.write(blob)
        except Exception as e: log.warning("Sauvegarde comptes: %s", e)
    @staticmethod
    def _hash(mdp, salt): return hashlib.sha256((salt + mdp).encode("utf-8")).hexdigest()
    def liste_pseudos(self): return sorted(self.comptes.keys())
    def existe(self, p): return p in self.comptes
    def creer(self, pseudo, mdp):
        if pseudo in self.comptes: return False, "Ce pseudo existe déjà."
        if not pseudo or len(pseudo) > MAX_PSEUDO: return False, f"Pseudo invalide (1 à {MAX_PSEUDO} car.)."
        if not mdp or len(mdp) < 3: return False, "Mot de passe trop court (3 car. min)."
        salt = os.urandom(16).hex()
        self.comptes[pseudo] = {"salt":salt, "hash":self._hash(mdp, salt), "coins":150, "xp":0,
            "msgs":0, "appels":0, "derniere_session":time.strftime("%Y-%m-%d %H:%M"),
            "possedes":{"couleurs":["bleu","vert"], "badges":["aucun","etoile"], "titres":["membre","newbie"]},
            "equip":{"couleur":"bleu", "badge":"etoile", "titre":"membre"},
            "sonnerie":"", "notif":"", "bio":"", "liens":[], "theme":"sombre",
            "avatar_emoji":"🧑", "couleur_pseudo":"bleu"}
        self._sauver(); return True, "Compte créé ! 150 coins de bienvenue 🎁"
    def verifier(self, pseudo, mdp):
        c = self.comptes.get(pseudo)
        if not c: return False, "Compte introuvable."
        return (self._hash(mdp, c["salt"]) == c["hash"]), "ok"
    def supprimer(self, pseudo, mdp):
        c = self.comptes.get(pseudo)
        if not c: return False, "Compte introuvable."
        if self._hash(mdp, c["salt"]) != c["hash"]: return False, "Mot de passe incorrect."
        del self.comptes[pseudo]; self._sauver(); return True, "Compte supprimé."
    def get(self, p): return self.comptes.get(p)
    def sauver(self): self._sauver()

def profil_public(c):
    niv, _ = niveau_from_xp(c["xp"])
    return {"pseudo":None, "niveau":niv, "xp":c["xp"], "coins":c["coins"], "msgs":c["msgs"],
            "appels":c["appels"], "couleur":c["equip"]["couleur"], "badge":c["equip"]["badge"],
            "titre":c["equip"]["titre"], "bio":c.get("bio",""), "liens":c.get("liens",[]),
            "avatar":c.get("avatar_emoji","🧑")}

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception: return "127.0.0.1"

def recv_lines(sock, on_line):
    buf = b""
    try:
        while True:
            data = sock.recv(RECV_BUF)
            if not data: break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line: continue
                try: on_line(json.loads(line.decode("utf-8")))
                except Exception: pass
    except OSError: pass

def make_msg(t, **f): f["type"] = t; return (json.dumps(f, ensure_ascii=False) + "\n").encode("utf-8")
def make_udp(t, **f): f["magic"] = APP_MAGIC; f["type"] = t; return json.dumps(f, ensure_ascii=False).encode("utf-8")
def parse_udp(data):
    try:
        m = json.loads(data.decode("utf-8"))
        return m if m.get("magic") == APP_MAGIC else None
    except Exception: return None

class AudioCall:
    def __init__(self):
        self.pa = None; self.in_stream = None; self.out_stream = None; self.sock = None
        self.peer = None; self.actif = False; self.mute = False; self._threads = []
    def disponible(self): return AUDIO_OK
    def allouer(self):
        if not AUDIO_OK: return None
        if self.sock is None:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("0.0.0.0", 0))
                self.sock = s
            except Exception: return None
        return self.mon_port()
    def demarrer_streams(self, ip, port):
        if not AUDIO_OK or self.actif: return False
        if self.sock is None: self.allouer()
        try:
            global A_FMT
            if A_FMT is None: A_FMT = pyaudio.paInt16
            self.pa = pyaudio.PyAudio()
            self.in_stream = self.pa.open(format=A_FMT, channels=A_CHAN, rate=A_RATE, input=True, frames_per_buffer=A_CHUNK)
            self.out_stream = self.pa.open(format=A_FMT, channels=A_CHAN, rate=A_RATE, output=True, frames_per_buffer=A_CHUNK)
            self.peer = (ip, port); self.actif = True; self.mute = False
            def capturer():
                while self.actif:
                    try:
                        data = self.in_stream.read(A_CHUNK, exception_on_overflow=False)
                        if not self.mute and self.peer: self.sock.sendto(data, self.peer)
                    except OSError: break
            def recevoir():
                self.sock.settimeout(1.0)
                while self.actif:
                    try:
                        data, _ = self.sock.recvfrom(A_CHUNK * 4); self.out_stream.write(data)
                    except socket.timeout: continue
                    except OSError: break
            t1 = threading.Thread(target=capturer, daemon=True)
            t2 = threading.Thread(target=recevoir, daemon=True)
            t1.start(); t2.start(); self._threads = [t1, t2]; return True
        except Exception as e: log.warning("Audio streams: %s", e); self.arreter(); return False
    def demarrer(self, ip, port): self.allouer(); return self.demarrer_streams(ip, port)
    def mon_port(self): return self.sock.getsockname()[1] if self.sock else None
    def basculer_mute(self): self.mute = not self.mute; return self.mute
    def arreter(self):
        self.actif = False
        for s in (self.in_stream, self.out_stream):
            try:
                if s: s.stop_stream(); s.close()
            except Exception: pass
        try:
            if self.pa: self.pa.terminate()
        except Exception: pass
        try:
            if self.sock: self.sock.close()
        except Exception: pass
        self.in_stream = self.out_stream = self.sock = self.pa = None; self.peer = None

_SONS_PERSO = {"sonnerie":"", "notif":"", "envoi":"", "connexion":"", "erreur":""}

def _jouer_fichier(path):
    if not path or not os.path.isfile(path): return False
    sysname = platform.system()
    try:
        if sysname == "Windows":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        elif sysname == "Darwin":
            subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        else:
            for lecteur in ("aplay", "mpv", "ffplay", "paplay"):
                try:
                    subprocess.Popen([lecteur, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except OSError: continue
    except Exception: pass
    return False

def beep(freq=880, duree=120):
    try:
        import winsound; winsound.Beep(freq, duree); return
    except Exception: pass

_SONNERIE_FLAG = {"stop": False}
def sonnerie(compte=None):
    _SONNERIE_FLAG["stop"] = False
    if compte:
        _SONS_PERSO["sonnerie"] = compte.get("sonnerie", "")
    path = _SONS_PERSO.get("sonnerie", "")
    if path and os.path.isfile(path):
        def loop():
            for _ in range(4):
                if _SONNERIE_FLAG["stop"]: break
                _jouer_fichier(path); time.sleep(0.8)
        threading.Thread(target=loop, daemon=True).start(); return
    def loop_beep():
        for _ in range(12):
            if _SONNERIE_FLAG["stop"]: break
            beep(1000, 250); time.sleep(0.25)
    threading.Thread(target=loop_beep, daemon=True).start()

def stop_sonnerie(): _SONNERIE_FLAG["stop"] = True

def son_notif(compte=None):
    if compte:
        _SONS_PERSO["notif"] = compte.get("notif", "")
    path = _SONS_PERSO.get("notif", "")
    if path and os.path.isfile(path):
        _jouer_fichier(path); return
    beep(900, 100)

def son_envoi(compte=None):
    if compte:
        _SONS_PERSO["envoi"] = compte.get("son_envoi", "")
    path = _SONS_PERSO.get("envoi", "")
    if path and os.path.isfile(path):
        _jouer_fichier(path); return
    beep(600, 50)

def son_connexion(compte=None):
    if compte:
        _SONS_PERSO["connexion"] = compte.get("son_connexion", "")
    path = _SONS_PERSO.get("connexion", "")
    if path and os.path.isfile(path):
        _jouer_fichier(path); return
    beep(880, 80); time.sleep(0.05); beep(1100, 80)

RAINBOW = ["#f38ba8","#fab387","##f9e2af","#a6e3a1","#94e2d5","#89b4fa","#cba6f7"]
RAINBOW = ["#f38ba8","#fab387","#f9e2af","#a6e3a1","#94e2d5","#89b4fa","#cba6f7"]

def hex_to_rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def rgb_to_hex(r, g, b): return f"#{r:02x}{g:02x}{b:02x}"

def _gradient_hex(c1, c2, steps=20):
    r1,g1,b1 = hex_to_rgb(c1); r2,g2,b2 = hex_to_rgb(c2)
    out = []
    for i in range(steps):
        t = i / max(1, steps-1)
        out.append(rgb_to_hex(int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t)))
    return out

class LANchat:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.geometry("720x780")
        self.root.minsize(520, 600)
        self.root.configure(bg=C_BG)
        self.root.protocol("WM_DELETE_WINDOW", self.quitter)
        self.gc = GestionnaireComptes(COMPTE_FILE)
        self.compte = None; self.pseudo = ""
        self.mode = None; self.running = True; self.ui_queue = queue.Queue()
        self.profils = {}; self.couleurs_tags = set()
        self.sock = None; self.host_ip = None; self.cible = None
        self.clients = []; self.clients_lock = threading.Lock()
        self.pseudo_to_sock = {}; self.client_ips = {}
        self.udp_sock = None; self.tcp_server = None; self.nb_connectes = 0
        self.fenetres_mp = {}; self.mp_non_lus = {}; self.mp_historique = {}
        self.appels = {}; self.fenetres_appel = {}
        self.audio = AudioCall()
        self._anim_pseudos = {}
        self.salons = list(SALONS_DEFAUT)
        self.salon_courant = "général"
        self.messages_par_salon = {}
        self.vocal_actif = False
        self._poll(); self._ecran_auth()

    def _poll(self):
        try:
            while True:
                kind, *args = self.ui_queue.get_nowait()
                self._handle(kind, args)
        except queue.Empty: pass
        self.root.after(80, self._poll)

    def _handle(self, kind, args):
        h = {
            "msg": lambda: self.afficher_message(args[0], args[1]),
            "sys": lambda: self.afficher_systeme(args[0]),
            "err": lambda: self.afficher_erreur(args[0]),
            "scan_progress": lambda: self._maj_chargement(args[0]),
            "discovered": lambda: self._fin_scan(args[0]),
            "connected": self._on_connecte,
            "connect_fail": lambda: self._echec_connexion(args[0]),
            "mp": lambda: self._on_mp_recu(args[0], args[1]),
            "profil": lambda: self._maj_profil(args[0]),
            "profils_init": lambda: self._init_profils(args[0]),
            "salons_init": lambda: self._init_salons(args[0]),
            "salon_cree": lambda: self._on_salon_cree(args[0], args[1] if len(args)>1 else "texte", args[2] if len(args)>2 else ""),
            "vocal_join": lambda: self._on_vocal_join(args[0], args[1] if len(args)>1 else None),
            "vocal_leave": lambda: self._on_vocal_leave(args[0]),
            "call_incoming": lambda: self._on_appel_entrant(args[0]),
            "call_accepted": lambda: self._on_appel_accepte(args[0], args[1], args[2], args[3]),
            "call_ready": lambda: self._on_appel_ready(args[0], args[1], args[2]),
            "call_reject": lambda: self._on_appel_refuse(args[0]),
            "call_end": lambda: self._on_appel_fin(args[0]),
            "toast": lambda: self._toast(args[0], args[1] if len(args)>1 else None),
            "compte_maj": self._rafraichir_compte_ui,
        }
        f = h.get(kind)
        if f: f()

    def _reset_frame(self):
        if hasattr(self, "frame"): self.frame.destroy()
        self.frame = tk.Frame(self.root, bg=C_BG); self.frame.pack(fill="both", expand=True)

    def _entree_styler(self, e):
        e.config(font=(FONT, 13), bg=C_INP, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", bd=0)

    def _btn_styler(self, b, bg=C_BLUE, fg=C_BG):
        b.config(font=(FONT, 11, "bold"), bg=bg, fg=fg, relief="flat", cursor="hand2",
                 activebackground=bg, activeforeground=fg, bd=0)
        b.bind("<Enter>", lambda e: b.config(bg=self._lighten(bg)))
        b.bind("<Leave>", lambda e: b.config(bg=bg))

    def _lighten(self, hexcol, t=0.15):
        r, g, b = hex_to_rgb(hexcol)
        return rgb_to_hex(min(255, int(r+(255-r)*t)), min(255, int(g+(255-g)*t)), min(255, int(b+(255-b)*t)))

    def _titre_anime(self, parent, texte, couleur=C_BLUE, font_size=24):
        lbl = tk.Label(parent, text=texte, font=(FONT, font_size, "bold"), fg=couleur, bg=parent["bg"])
        lbl.pack()
        etapes = [couleur, self._lighten(couleur, 0.2), self._lighten(couleur, 0.35), self._lighten(couleur, 0.2)]
        idx = [0]
        def anim():
            lbl.config(fg=etapes[idx[0] % len(etapes)]); idx[0] += 1
            if lbl.winfo_exists(): self.root.after(600, anim)
        anim(); return lbl

    def _fond_anime(self, parent, height=80):
        canvas = tk.Canvas(parent, height=height, highlightthickness=0, bd=0)
        canvas.pack(fill="x")
        idx = [0]
        def anim():
            canvas.delete("fond")
            for i in range(len(RAINBOW)):
                c = RAINBOW[(idx[0]+i) % len(RAINBOW)]
                x0 = i * 60; canvas.create_rectangle(x0, 0, x0+61, height, fill=c, outline="", tags="fond")
            idx[0] += 1
            if canvas.winfo_exists(): self.root.after(80, anim)
        anim(); return canvas

    def _fond_gradient(self, parent, height=60):
        canvas = tk.Canvas(parent, height=height, highlightthickness=0, bd=0)
        canvas.pack(fill="x")
        def dessiner():
            canvas.delete("grad")
            w = canvas.winfo_width() or 400
            grad = _gradient_hex(C_GRAD1, C_GRAD2, max(10, w // 8))
            for i, c in enumerate(grad):
                x0 = i * 8; canvas.create_rectangle(x0, 0, x0+9, height, fill=c, outline="", tags="grad")
            if canvas.winfo_exists(): self.root.after(500, dessiner)
        canvas.after(100, dessiner)
        return canvas
    def _ecran_auth(self):
        self._reset_frame()
        f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=70)
        self._titre_anime(f, f"💬 {APP_NAME}", C_BLUE, 22)
        tk.Label(f, text=VERSION, font=(FONT, 10, "bold"), fg=C_YELLOW, bg=C_BG).pack(pady=(0, 2))
        tk.Label(f, text="Compte local sécurisé", font=(FONT, 11), fg=C_SUB, bg=C_BG).pack(pady=(0, 16))
        cadre = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
        cadre.pack(padx=40, pady=8, fill="x")
        self._auth_var = tk.StringVar(value="login")
        def toggle():
            if self._auth_var.get() == "login":
                self.btn_valider.config(text="Se connecter", bg=C_BLUE)
                self.lbl_mdp2.pack_forget(); self.ent_mdp2.pack_forget()
            else:
                self.btn_valider.config(text="Créer le compte", bg=C_GREEN)
                self.lbl_mdp2.pack(anchor="w", padx=16, pady=(8, 0)); self.ent_mdp2.pack(padx=16, pady=4, fill="x")
        top = tk.Frame(cadre, bg=C_SURF2); top.pack(fill="x", padx=16, pady=(14, 4))
        tk.Radiobutton(top, text="Connexion", variable=self._auth_var, value="login", command=toggle,
            bg=C_SURF2, fg=C_TEXT, selectcolor=C_SURF2, activebackground=C_SURF2, activeforeground=C_TEXT,
            font=(FONT, 10)).pack(side="left")
        tk.Radiobutton(top, text="Créer un compte", variable=self._auth_var, value="creer", command=toggle,
            bg=C_SURF2, fg=C_TEXT, selectcolor=C_SURF2, activebackground=C_SURF2, activeforeground=C_TEXT,
            font=(FONT, 10)).pack(side="left", padx=12)
        tk.Label(cadre, text="Pseudo", font=(FONT, 10), fg=C_SUB, bg=C_SURF2).pack(anchor="w", padx=16, pady=(8, 0))
        self.ent_pseudo_auth = tk.Entry(cadre); self._entree_styler(self.ent_pseudo_auth)
        self.ent_pseudo_auth.pack(padx=16, pady=4, fill="x")
        pseudos_existants = self.gc.liste_pseudos()
        if pseudos_existants:
            ligne_cpt = tk.Frame(cadre, bg=C_SURF2); ligne_cpt.pack(fill="x", padx=16, pady=(2, 0))
            tk.Label(ligne_cpt, text="Comptes existants :", font=(FONT, 8), fg=C_DIM, bg=C_SURF2).pack(side="left")
            for p in pseudos_existants[:6]:
                btn = tk.Button(ligne_cpt, text=p, font=(FONT, 8), bg=C_INP, fg=C_TEXT, relief="flat",
                    cursor="hand2", bd=0, command=lambda x=p: self.ent_pseudo_auth.insert(0, x))
                btn.pack(side="left", padx=2)
        tk.Label(cadre, text="Mot de passe", font=(FONT, 10), fg=C_SUB, bg=C_SURF2).pack(anchor="w", padx=16, pady=(8, 0))
        self.ent_mdp = tk.Entry(cadre, show="•"); self._entree_styler(self.ent_mdp)
        self.ent_mdp.pack(padx=16, pady=4, fill="x")
        self.lbl_mdp2 = tk.Label(cadre, text="Confirmer le mot de passe", font=(FONT, 10), fg=C_SUB, bg=C_SURF2)
        self.ent_mdp2 = tk.Entry(cadre, show="•"); self._entree_styler(self.ent_mdp2)
        self.btn_valider = tk.Button(cadre, text="Se connecter", command=self._valider_auth)
        self._btn_styler(self.btn_valider, C_BLUE); self.btn_valider.pack(padx=16, pady=14, fill="x")
        self.ent_mdp.bind("<Return>", lambda e: self._valider_auth()); self.ent_pseudo_auth.focus()
        ligne_bas_auth = tk.Frame(cadre, bg=C_SURF2); ligne_bas_auth.pack(fill="x", padx=16, pady=(0, 12))
        btn_suppr = tk.Button(ligne_bas_auth, text="🗑️ Supprimer un compte", command=self._supprimer_compte)
        self._btn_styler(btn_suppr, C_RED, C_BG); btn_suppr.pack(fill="x", ipady=3)
        tk.Label(f, text=f"🔒 Identifiants stockés localement dans {COMPTE_FILE} (jamais sur le réseau)",
            font=(FONT, 9), fg=C_DIM, bg=C_BG, wraplength=420, justify="center").pack(pady=(14, 0))

    def _supprimer_compte(self):
        pseudo = simpledialog.askstring("Supprimer un compte", "Pseudo à supprimer :", parent=self.root)
        if not pseudo: return
        mdp = simpledialog.askstring("Supprimer un compte", f"Mot de passe de {pseudo} :", parent=self.root, show="•")
        if not mdp: return
        ok, msg = self.gc.supprimer(pseudo, mdp)
        if ok:
            messagebox.showinfo(APP_NAME, msg)
            self._reset_frame(); self._ecran_auth()
        else:
            messagebox.showerror(APP_NAME, msg)

    def _valider_auth(self):
        pseudo = self.ent_pseudo_auth.get().strip(); mdp = self.ent_mdp.get(); mode = self._auth_var.get()
        if not pseudo or not mdp:
            messagebox.showwarning(APP_NAME, "Remplis le pseudo et le mot de passe."); return
        if mode == "creer":
            mdp2 = self.ent_mdp2.get()
            if mdp != mdp2:
                messagebox.showwarning(APP_NAME, "Les mots de passe ne correspondent pas."); return
            ok, msg = self.gc.creer(pseudo, mdp)
            if not ok: messagebox.showerror(APP_NAME, msg); return
            messagebox.showinfo(APP_NAME, msg)
        ok, msg = self.gc.verifier(pseudo, mdp)
        if not ok: messagebox.showerror(APP_NAME, msg); return
        self.compte = self.gc.get(pseudo); self.pseudo = pseudo
        for cle in ("sonnerie", "notif", "son_envoi", "son_connexion"):
            if cle not in self.compte: self.compte[cle] = ""
        if "bio" not in self.compte: self.compte["bio"] = ""
        if "liens" not in self.compte: self.compte["liens"] = []
        if "theme" not in self.compte: self.compte["theme"] = "sombre"
        if "avatar_emoji" not in self.compte: self.compte["avatar_emoji"] = "🧑"
        _appliquer_theme(self.compte.get("theme", "sombre"))
        self.root.configure(bg=C_BG)
        _SONS_PERSO["sonnerie"] = self.compte.get("sonnerie", "")
        _SONS_PERSO["notif"] = self.compte.get("notif", "")
        _SONS_PERSO["envoi"] = self.compte.get("son_envoi", "")
        _SONS_PERSO["connexion"] = self.compte.get("son_connexion", "")
        self.profils[pseudo] = profil_public(self.compte); self.profils[pseudo]["pseudo"] = pseudo
        self.profils[pseudo]["en_ligne"] = True
        son_connexion(self.compte)
        self._ecran_demarrage()

    def _ecran_demarrage(self):
        self._reset_frame()
        f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=60)
        self._titre_anime(f, f"💬 {APP_NAME}", C_BLUE, 20)
        tk.Label(f, text=VERSION, font=(FONT, 9, "bold"), fg=C_YELLOW, bg=C_BG).pack(pady=(0, 8))
        barre = tk.Frame(f, bg=C_SURF2); barre.pack(fill="x", padx=20, pady=(0, 8))
        badge = self.compte["equip"]["badge"]; niv, _ = niveau_from_xp(self.compte["xp"])
        avatar = self.compte.get("avatar_emoji", "🧑")
        tk.Label(barre, text=f"{avatar} {self.pseudo}  {badge_emoji(badge)}", font=(FONT, 11, "bold"),
            fg=couleur_hex(self.compte["equip"]["couleur"]), bg=C_SURF2).pack(side="left", padx=14, pady=8)
        self.lbl_compte = tk.Label(barre, text="", font=(FONT, 9), fg=C_SUB, bg=C_SURF2)
        self.lbl_compte.pack(side="right", padx=14, pady=8); self._rafraichir_compte_ui()
        cadre = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
        cadre.pack(padx=40, pady=8, fill="x")
        b1 = tk.Button(cadre, text="🖥️  Héberger une discussion", command=self.demarrer_hote, height=2)
        self._btn_styler(b1, C_BLUE); b1.pack(padx=16, pady=(16, 6), fill="x")
        b2 = tk.Button(cadre, text="🔍  Rejoindre (auto)", command=self.demarrer_rejoindre, height=2)
        self._btn_styler(b2, C_GREEN); b2.pack(padx=16, pady=6, fill="x")
        b3 = tk.Button(cadre, text="✍️  Rejoindre par IP (dernier recours)", command=self.rejoindre_ip_manuel, height=2)
        self._btn_styler(b3, C_INP, C_TEXT); b3.pack(padx=16, pady=6, fill="x")
        b4 = tk.Button(cadre, text="🛍️  Boutique & cosmétiques", command=self.ouvrir_boutique, height=2)
        self._btn_styler(b4, C_YELLOW, C_BG); b4.pack(padx=16, pady=(6, 6), fill="x")
        ligne_bas = tk.Frame(f, bg=C_BG); ligne_bas.pack(fill="x", padx=40, pady=(0, 4))
        b5 = tk.Button(ligne_bas, text="⚙️  Paramètres", command=self.ouvrir_parametres)
        self._btn_styler(b5, C_PURPLE); b5.pack(fill="x", ipady=4)
        b6 = tk.Button(ligne_bas, text="📋  Journal des nouveautés", command=self.ouvrir_journal)
        self._btn_styler(b6, C_INP, C_YELLOW); b6.pack(fill="x", ipady=4)
        b7 = tk.Button(ligne_bas, text="🚪  Changer de compte", command=self._deconnexion)
        self._btn_styler(b7, C_RED, C_BG); b7.pack(fill="x", ipady=4)
        tk.Label(f, text="Astuce : l'hébergeur lance le salon, les autres le rejoignent automatiquement.",
            font=(FONT, 9), fg=C_DIM, bg=C_BG, wraplength=440, justify="center").pack(pady=(10, 0))

    def _deconnexion(self):
        self.running = False
        try:
            if self.udp_sock: self.udp_sock.close()
            if self.tcp_server: self.tcp_server.close()
            if self.sock: self.sock.close()
            self.audio.arreter()
        except Exception: pass
        if self.compte:
            self.compte["derniere_session"] = time.strftime("%Y-%m-%d %H:%M")
            self.gc.sauver()
        self.running = True
        self.compte = None; self.pseudo = ""
        self.profils = {}; self.sock = None; self.mode = None
        self._ecran_auth()

    def _rafraichir_compte_ui(self):
        if not self.compte: return
        niv, restant = niveau_from_xp(self.compte["xp"])
        txt = f"Lvl {niv}  •  {self.compte['coins']} 🪙  •  {badge_emoji(self.compte['equip']['badge'])}  •  XP {self.compte['xp']} (+{restant} → niv.{niv+1})"
        if hasattr(self, "lbl_compte") and self.lbl_compte.winfo_exists(): self.lbl_compte.config(text=txt)

    def ouvrir_boutique(self):
        win = tk.Toplevel(self.root); win.title("🛍️ Boutique"); win.geometry("540x640")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_anime(win, height=50)
        self.lbl_compte_bout = tk.Label(win, text="", font=(FONT, 11, "bold"), fg=C_YELLOW, bg=C_BG)
        self.lbl_compte_bout.pack(pady=8); self._rafraichir_boutique(win)
        nbook = ttk.Notebook(win); nbook.pack(fill="both", expand=True, padx=14, pady=6)
        style = ttk.Style(); style.configure("TNotebook", background=C_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=C_SURF2, foreground=C_TEXT, padding=12)
        style.map("TNotebook.Tab", background=[("selected", C_BLUE)], foreground=[("selected", C_BG)])
        for cat, catalogue, equip_key in [("🎨 Couleurs", COULEURS, "couleur"), ("🏆 Badges", BADGES, "badge"), ("🏷️ Titres", TITRES, "titre")]:
            page = tk.Frame(nbook, bg=C_BG); nbook.add(page, text=cat)
            self._remplir_boutique_page(page, catalogue, equip_key, win)

    def _rafraichir_boutique(self, win):
        niv, _ = niveau_from_xp(self.compte["xp"])
        self.lbl_compte_bout.config(text=f"{self.pseudo}  •  Niveau {niv}  •  {self.compte['coins']} 🪙")

    def _remplir_boutique_page(self, page, catalogue, equip_key, win):
        canvas = tk.Canvas(page, bg=C_BG, highlightthickness=0)
        scroll = tk.Scrollbar(page, command=canvas.yview); inner = tk.Frame(canvas, bg=C_BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window(0, 0, window=inner, anchor="nw"); canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        poss_key = equip_key + "s"; possedes = self.compte["possedes"][poss_key]; equipe = self.compte["equip"][equip_key]
        for cid, info in catalogue.items():
            row = tk.Frame(inner, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
            row.pack(fill="x", padx=6, pady=5)
            apercu = self._apercu_cosmetique(equip_key, cid)
            tk.Label(row, text=apercu, font=(FONT, 16), bg=C_SURF2,
                fg=couleur_hex(cid) if equip_key == "couleur" else C_TEXT, width=6).pack(side="left", padx=10, pady=8)
            extra = ""
            if info.get("anime"): extra = " ✨"
            tk.Label(row, text=info["nom"] + extra, font=(FONT, 11, "bold"), fg=C_TEXT, bg=C_SURF2).pack(side="left", pady=8)
            tk.Label(row, text=f"{info['prix']} 🪙", font=(FONT, 10), fg=C_GREEN, bg=C_SURF2).pack(side="left", padx=10)
            if cid == equipe: etat, bg = "✅ Équipé", C_GREEN
            elif cid in possedes: etat, bg = "Possédé — Équiper", C_BLUE
            else: etat, bg = f"Acheter {info['prix']}🪙", C_YELLOW
            b = tk.Button(row, text=etat, command=lambda c=cid, k=equip_key, w=win: self._action_cosmetique(c, k, w))
            self._btn_styler(b, bg if bg != C_YELLOW else C_YELLOW, C_BG if bg == C_YELLOW else C_BG)
            b.pack(side="right", padx=12, pady=8)

    def _apercu_cosmetique(self, key, cid):
        if key == "couleur": return "●"
        if key == "badge": return badge_emoji(cid) or "—"
        if key == "titre": return "🏷️"
        return ""

    def _action_cosmetique(self, cid, key, win):
        poss_key = key + "s"; possedes = self.compte["possedes"][poss_key]
        if cid == self.compte["equip"][key]: return
        if cid in possedes:
            self.compte["equip"][key] = cid; self.gc.sauver()
            self._rafraichir_boutique(win); self._rafraichir_compte_ui(); self._propager_profil()
            win.destroy(); self.ouvrir_boutique(); return
        prix = COULEURS.get(cid, {}).get("prix") or BADGES.get(cid, {}).get("prix") or TITRES.get(cid, {}).get("prix", 0)
        if self.compte["coins"] < prix:
            messagebox.showwarning(APP_NAME, f"Pas assez de coins ({prix} 🪙). Discute pour en gagner !"); return
        if not messagebox.askyesno(APP_NAME, f"Acheter pour {prix} 🪙 ?"): return
        self.compte["coins"] -= prix; self.compte["possedes"][poss_key].append(cid)
        self.compte["equip"][key] = cid; self.gc.sauver()
        self._rafraichir_boutique(win); self._rafraichir_compte_ui(); self._propager_profil()
        win.destroy(); self.ouvrir_boutique()

    def ouvrir_journal(self):
        win = tk.Toplevel(self.root); win.title("Journal des nouveautés"); win.geometry("560x640")
        win.configure(bg=C_BG); win.transient(self.root)
        cadre_h = tk.Frame(win, bg=C_BG2); cadre_h.pack(fill="x")
        tk.Label(cadre_h, text="📋 Journal des nouveautés", font=(FONT, 16, "bold"), fg=C_YELLOW, bg=C_BG2).pack(pady=(14, 2))
        tk.Label(cadre_h, text=f"{APP_NAME} — historique des versions", font=(FONT, 10), fg=C_DIM, bg=C_BG2).pack(pady=(0, 12))
        zone = tk.Text(win, font=(FONT, 11), bg=C_BG2, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", wrap="word", padx=16, pady=12)
        scroll = tk.Scrollbar(win, command=zone.yview); zone.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y"); zone.pack(fill="both", expand=True)
        versions = [
            ("V.1.0.7", "Sécurité, slots & plus d'émojis", [
                "Quitter un salon textuel (bouton dédié dans la liste des salons)",
                "9 slots de configuration serveur : sauvegarde et import de configs",
                "Écran de configuration serveur au lancement (rapide, personnalisée, import)",
                "Création de serveur personnalisée : nom, salons texte/vocal, descriptions",
                "Chiffrement des données de comptes (XOR + base85 + sel aléatoire)",
                "Chiffrement des slots de configuration serveur",
                "Migration automatique des anciens comptes non chiffrés",
                "Plus d'émojis : 9 nouvelles catégories (Fêtes, Météo, Transports, Voyages, Sport, Zodiaque, Nourriture+, Boissons, Jeux)",
                "Total : 21 catégories d'émojis avec 24 émojis chacune",
                "Notification réseau quand un membre quitte un salon",
                "Amélioration du système de connexion et création de comptes",
            ]),
            ("V.1.0.6", "Salons, style & sons", [
                "Salons textuels multiples (général, annonces, blabla) avec commutation",
                "Salon vocal dédié avec connexion/déconnexion audio",
                "Création de nouveaux salons personnalisés par l'hôte",
                "Système de comptes amélioré : boutons de sélection rapide, suppression de compte",
                "Validation des mots de passe (3 caractères minimum)",
                "Avatar émoji personnalisable par compte",
                "Bouton 'Changer de compte' sur l'écran d'accueil",
                "Plus d'émojis : 12 catégories avec 24 émojis chacune (+ catégories Tech et Divers)",
                "10 sons préchargés au lieu de 5 (ajout de sons pour envoi, connexion, erreur)",
                "Sons d'envoi et de connexion personnalisables",
                "Amélioration du style : dégradés, textures, animations fluides",
                "Réparation définitive du bug de corruption UTF-8 (accents)",
            ]),
            ("V.1.0.5", "Correction critique & nouvelles fonctionnalités", [
                "Correction du bug de corruption UTF-8 (les accents s'affichaient mal)",
                "Sons personnalisés pour la sonnerie et les notifications",
                "Panneau Paramètres avec 3 onglets : Apparence, Sons, Profil",
                "Thème sombre / clair changeable en direct",
                "Profil enrichi : bio, liens cliquables, statut en ligne",
                "Sélecteur d'émojis avec import d'émojis/GIFs personnalisés",
                "Envoi d'images inline dans le chat",
                "Détection automatique des liens cliquables",
            ]),
            ("V.1.0.4", "Multi-comptes & cosmétiques", [
                "Système de comptes locaux sécurisés (hash SHA-256 + salt)",
                "Boutique de cosmétiques : couleurs, badges, titres",
                "Système de niveaux et XP",
            ]),
            ("V.1.0.3", "Appels vocaux & messages privés", [
                "Appels vocaux en peer-to-peer via UDP",
                "Messages privés entre membres",
                "Fenêtres d'appel avec minuteur et mute",
            ]),
            ("V.1.0.1", "Fondations", [
                "Architecture client/serveur TCP",
                "Profils publics propagés sur le réseau",
            ]),
            ("V.1.0.0", "Version initiale", [
                "Chat LAN basique en Python/Tkinter",
            ]),
        ]
        for ver, titre, items in versions:
            zone.insert(tk.END, f"  {ver} — {titre}\n", ("ver",))
            for item in items:
                zone.insert(tk.END, f"    • {item}\n", ("item",))
            zone.insert(tk.END, "\n")
        zone.tag_config("ver", foreground=C_YELLOW, font=(FONT, 13, "bold"))
        zone.tag_config("item", foreground=C_TEXT, font=(FONT, 10))
        zone.config(state="disabled")
        btn_f = tk.Button(win, text="Fermer", command=win.destroy)
        self._btn_styler(btn_f, C_INP, C_TEXT); btn_f.pack(pady=8)
    def _lister_slots(self):
        try:
            with open(SLOTS_FILE, "rb") as f: blob = f.read().strip()
            if not blob: return [None]*9
            dec = _dechiffrer_json(blob)
            if dec is None: return [None]*9
            slots = dec.get("slots", [])
            return (slots + [None]*9)[:9]
        except Exception: return [None]*9

    def _sauver_slot(self, num, config):
        try:
            slots = self._lister_slots()
            if num < 0 or num > 8: return False
            slots[num] = config
            with open(SLOTS_FILE, "wb") as f:
                f.write(_chiffrer_json({"slots": slots}))
            return True
        except Exception as e: log.warning("Sauvegarde slot: %s", e); return False

    def _charger_slot(self, num):
        slots = self._lister_slots()
        if 0 <= num <= 8: return slots[num]
        return None

    def _ecran_config_serveur(self):
        self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=50)
        self._titre_anime(f, "🖥️ Configurer le serveur", C_BLUE, 18)
        tk.Label(f, text="Choisis comment lancer ton salon", font=(FONT, 11), fg=C_SUB, bg=C_BG).pack(pady=(0, 12))
        cadre = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
        cadre.pack(padx=40, pady=4, fill="x")
        b_quick = tk.Button(cadre, text="⚡  Démarrage rapide (salons par défaut)", height=2,
            command=self._config_rapide)
        self._btn_styler(b_quick, C_GREEN); b_quick.pack(padx=16, pady=(16, 6), fill="x")
        b_custom = tk.Button(cadre, text="📝  Créer une config personnalisée", height=2,
            command=self._config_personnalisee)
        self._btn_styler(b_custom, C_BLUE); b_custom.pack(padx=16, pady=6, fill="x")
        b_import = tk.Button(cadre, text="📂  Importer une config sauvegardée", height=2,
            command=self._config_importer)
        self._btn_styler(b_import, C_PURPLE); b_import.pack(padx=16, pady=6, fill="x")
        b_annul = tk.Button(f, text="↩ Annuler", command=self._ecran_demarrage)
        self._btn_styler(b_annul, C_INP, C_TEXT); b_annul.pack(pady=12)

    def _config_rapide(self):
        self.salons = list(SALONS_DEFAUT); self.salon_courant = "général"
        self._lancer_hote()

    def _config_personnalisee(self):
        self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=40)
        self._titre_anime(f, "📝 Création de serveur", C_BLUE, 16)
        tk.Label(f, text="Nom du serveur", font=(FONT, 10), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=40, pady=(8, 0))
        self._ent_nom_srv = tk.Entry(f); self._entree_styler(self._ent_nom_srv)
        self._ent_nom_srv.pack(padx=40, pady=4, fill="x")
        self._ent_nom_srv.insert(0, "Mon serveur")
        self._salons_custom = list(SALONS_DEFAUT)
        tk.Label(f, text="Salons (clique pour supprimer)", font=(FONT, 10), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=40, pady=(12, 4))
        self._cadre_salons_custom = tk.Frame(f, bg=C_BG2, highlightbackground=C_INP, highlightthickness=1)
        self._cadre_salons_custom.pack(padx=40, pady=4, fill="x")
        self._rafraichir_salons_custom()
        b_ajout_txt = tk.Button(f, text="➕ Salon textuel", command=lambda: self._ajout_salon_custom("texte"))
        self._btn_styler(b_ajout_txt, C_GREEN); b_ajout_txt.pack(side="left", padx=40, pady=8)
        b_ajout_voc = tk.Button(f, text="🎤 Salon vocal", command=lambda: self._ajout_salon_custom("vocal"))
        self._btn_styler(b_ajout_voc, C_TEAL); b_ajout_voc.pack(side="left", padx=4, pady=8)
        cadre_slot = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
        cadre_slot.pack(padx=40, pady=(12, 4), fill="x")
        tk.Label(cadre_slot, text="💾 Sauvegarder dans un slot (1-9)", font=(FONT, 10, "bold"), fg=C_YELLOW, bg=C_SURF2).pack(pady=(8, 4))
        grille = tk.Frame(cadre_slot, bg=C_SURF2); grille.pack(pady=(0, 8))
        for i in range(9):
            b = tk.Button(grille, text=str(i+1), font=(FONT, 12, "bold"), width=4,
                command=lambda n=i: self._sauver_config_slot(n))
            self._btn_styler(b, C_INP, C_TEXT); b.grid(row=i//3, column=i%3, padx=4, pady=4)
        b_lancer = tk.Button(f, text="🚀 Lancer le serveur", height=2, command=self._lancer_config_custom)
        self._btn_styler(b_lancer, C_BLUE); b_lancer.pack(padx=40, pady=(8, 4), fill="x")
        b_retour = tk.Button(f, text="↩ Retour", command=self._ecran_config_serveur)
        self._btn_styler(b_retour, C_INP, C_TEXT); b_retour.pack(pady=4)

    def _rafraichir_salons_custom(self):
        for w in self._cadre_salons_custom.winfo_children(): w.destroy()
        if not self._salons_custom:
            tk.Label(self._cadre_salons_custom, text="Aucun salon", font=(FONT, 9), fg=C_DIM, bg=C_BG2).pack(padx=8, pady=8)
            return
        for s in self._salons_custom:
            icone = "📝" if s["type"] == "texte" else "🎤"
            row = tk.Frame(self._cadre_salons_custom, bg=C_BG2); row.pack(fill="x", padx=4, pady=2)
            tk.Label(row, text=f" {icone} #{s['nom']}", font=(FONT, 10), fg=C_TEXT, bg=C_BG2).pack(side="left", padx=8, pady=4)
            b_suppr = tk.Button(row, text="🗑️", font=(FONT, 8), bg=C_RED, fg=C_BG, relief="flat", bd=0, cursor="hand2",
                command=lambda n=s["nom"]: self._suppr_salon_custom(n))
            b_suppr.pack(side="right", padx=4, pady=4)

    def _ajout_salon_custom(self, type_s):
        nom = simpledialog.askstring("Nouveau salon", f"Nom du salon {'textuel' if type_s=='texte' else 'vocal'} :", parent=self.root)
        if not nom: return
        nom = nom.strip().lower()[:20]
        if any(s["nom"] == nom for s in self._salons_custom):
            messagebox.showwarning(APP_NAME, "Ce salon existe déjà."); return
        desc = simpledialog.askstring("Description", "Description (optionnel) :", parent=self.root) or ""
        self._salons_custom.append({"nom": nom, "type": type_s, "desc": desc[:50]})
        self._rafraichir_salons_custom()

    def _suppr_salon_custom(self, nom):
        if len(self._salons_custom) <= 1:
            messagebox.showwarning(APP_NAME, "Impossible : il faut au moins un salon."); return
        self._salons_custom = [s for s in self._salons_custom if s["nom"] != nom]
        self._rafraichir_salons_custom()

    def _sauver_config_slot(self, num):
        config = {"nom": self._ent_nom_srv.get().strip()[:30] or "Mon serveur",
                  "salons": list(self._salons_custom), "created": time.strftime("%Y-%m-%d %H:%M")}
        ok = self._sauver_slot(num, config)
        if ok: self._toast("Slot sauvegardé", f"Config sauvegardée dans le slot {num+1}.")
        else: self._toast("Erreur", "Sauvegarde impossible.")

    def _lancer_config_custom(self):
        if not self._salons_custom:
            messagebox.showwarning(APP_NAME, "Ajoute au moins un salon."); return
        self.salons = list(self._salons_custom); self.salon_courant = self.salons[0]["nom"]
        self._lancer_hote()

    def _config_importer(self):
        slots = self._lister_slots()
        dispo = [(i, s) for i, s in enumerate(slots) if s]
        if not dispo:
            messagebox.showinfo(APP_NAME, "Aucune config sauvegardée. Crée-en une d'abord !"); return
        self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=40)
        self._titre_anime(f, "📂 Importer une config", C_PURPLE, 16)
        for num, config in dispo:
            row = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
            row.pack(padx=40, pady=4, fill="x")
            txt = f"Slot {num+1} : {config.get('nom','?')} ({len(config.get('salons',[]))} salons)"
            tk.Label(row, text=txt, font=(FONT, 11), fg=C_TEXT, bg=C_SURF2).pack(side="left", padx=12, pady=8)
            b = tk.Button(row, text="Importer", command=lambda n=num, c=config: self._importer_slot(n, c))
            self._btn_styler(b, C_GREEN); b.pack(side="right", padx=12, pady=8)
        b_retour = tk.Button(f, text="↩ Retour", command=self._ecran_config_serveur)
        self._btn_styler(b_retour, C_INP, C_TEXT); b_retour.pack(pady=12)

    def _importer_slot(self, num, config):
        self.salons = list(config.get("salons", SALONS_DEFAUT))
        self.salon_courant = self.salons[0]["nom"] if self.salons else "général"
        self._lancer_hote()

    def _lancer_hote(self):
        self.mode = "host"; self._propager_profil_local()
        threading.Thread(target=self._servir_tcp, daemon=True).start()
        threading.Thread(target=self._servir_udp, daemon=True).start()
        self._construire_interface_chat()

    def demarrer_hote(self):
        self._ecran_config_serveur()

    def _propager_profil_local(self):
        self.profils[self.pseudo] = profil_public(self.compte); self.profils[self.pseudo]["pseudo"] = self.pseudo
        self.profils[self.pseudo]["en_ligne"] = True

    def _servir_tcp(self):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", TCP_PORT)); srv.listen(); self.tcp_server = srv
        except OSError as e:
            self.ui_queue.put(("err", f"Impossible d'héberger (port {TCP_PORT}) : {e}")); return
        while self.running:
            try: conn, addr = srv.accept()
            except OSError: break
            with self.clients_lock: self.clients.append(conn)
            threading.Thread(target=self._gerer_client, args=(conn, addr), daemon=True).start()

    def _gerer_client(self, conn, addr):
        pseudo_client = None
        def on_line(m):
            nonlocal pseudo_client
            t = m.get("type")
            if t == "hello":
                pseudo_client = (m.get("pseudo") or "?")[:MAX_PSEUDO]
                prof = m.get("profil", {}); prof["pseudo"] = pseudo_client; self.profils[pseudo_client] = prof
                with self.clients_lock:
                    self.pseudo_to_sock[pseudo_client] = conn; self.client_ips[pseudo_client] = addr[0]
                self.ui_queue.put(("sys", f"🟢 {pseudo_client} a rejoint le salon"))
                self.ui_queue.put(("profil", prof)); self._maj_compteur(1)
                try:
                    conn.sendall(make_msg("profils_init", profils=list(self.profils.values())))
                    conn.sendall(make_msg("salons_init", salons=self.salons))
                except OSError: pass
                self._diffuser(make_msg("profil", profil=prof), except_=conn)
                self._diffuser(make_msg("sys", text=f"🟢 {pseudo_client} a rejoint"), except_=conn)
            elif t == "msg":
                p = m.get("pseudo", "?"); txt = m.get("text", ""); salon = m.get("salon", "général")
                self.ui_queue.put(("msg", p, txt)); self._diffuser(make_msg("msg", pseudo=p, text=txt, salon=salon), except_=conn)
            elif t == "mp": self._router_mp(m, conn)
            elif t == "salon_cree":
                nom = (m.get("nom") or "")[:20]; typ = m.get("type_salon", "texte")
                desc = (m.get("desc") or "")[:50]
                if nom and not any(s["nom"] == nom for s in self.salons):
                    self.salons.append({"nom":nom, "type":typ, "desc":desc})
                    self.ui_queue.put(("salon_cree", nom, typ, desc))
                    self._diffuser(make_msg("salon_cree", nom=nom, type_salon=typ, desc=desc), except_=conn)
            elif t == "salon_leave":
                pseudo_l = m.get("pseudo", "?"); salon_l = m.get("salon", "")
                self.ui_queue.put(("sys", f"🚪 {pseudo_l} a quitté #{salon_l}"))
                self._diffuser(make_msg("sys", text=f"🚪 {pseudo_l} a quitté #{salon_l}"), except_=conn)
            elif t == "vocal_join":
                pseudo = m.get("pseudo", "?"); salon = m.get("salon", "vocal")
                self.ui_queue.put(("vocal_join", pseudo, salon))
                self._diffuser(make_msg("vocal_join", pseudo=pseudo, salon=salon), except_=conn)
            elif t == "vocal_leave":
                pseudo = m.get("pseudo", "?")
                self.ui_queue.put(("vocal_leave", pseudo))
                self._diffuser(make_msg("vocal_leave", pseudo=pseudo), except_=conn)
            elif t == "profil_update":
                prof = m.get("profil", {}); prof["pseudo"] = pseudo_client; self.profils[pseudo_client] = prof
                self.ui_queue.put(("profil", prof)); self._diffuser(make_msg("profil", profil=prof), except_=conn)
            elif t == "call_request": self._router_appel(m, conn, addr[0])
            elif t == "call_accept": self._router_call_accept(m, conn)
            elif t == "call_ready": self._router_call_ready(m, conn)
            elif t == "call_reject": self._router_call_reject(m)
            elif t == "call_end": self._router_call_end(m, conn)
        recv_lines(conn, on_line)
        with self.clients_lock:
            if conn in self.clients: self.clients.remove(conn)
            if pseudo_client and self.pseudo_to_sock.get(pseudo_client) is conn:
                del self.pseudo_to_sock[pseudo_client]
            self.client_ips.pop(pseudo_client, None)
        try: conn.close()
        except OSError: pass
        if pseudo_client:
            self._maj_compteur(-1)
            self.ui_queue.put(("sys", f"🔴 {pseudo_client} a quitté le salon"))
            if pseudo_client in self.profils:
                self.profils[pseudo_client]["en_ligne"] = False
            prof_off = self.profils.get(pseudo_client, {"pseudo": pseudo_client, "en_ligne": False})
            self._diffuser(make_msg("profil", profil=prof_off), except_=conn)

    def _diffuser(self, data, except_=None):
        with self.clients_lock: cibles = [c for c in self.clients if c is not except_]
        for c in cibles:
            try: c.sendall(data)
            except OSError:
                with self.clients_lock:
                    if c in self.clients: self.clients.remove(c)

    def _maj_compteur(self, delta):
        self.nb_connectes += delta; self.root.after(0, self._rafraichir_statut)

    def _router_mp(self, m, conn):
        src = m.get("from_", "?"); dest = m.get("dest", ""); txt = m.get("text", "")
        if dest == self.pseudo: self.ui_queue.put(("mp", src, txt)); return
        sd = self.pseudo_to_sock.get(dest)
        if sd:
            try: sd.sendall(make_msg("mp", from_=src, dest=dest, text=txt))
            except OSError: pass
        elif conn:
            try: conn.sendall(make_msg("sys", text=f"⚠ {dest} est introuvable."))
            except OSError: pass

    def _router_appel(self, m, conn, src_ip):
        src = m.get("from_", "?"); dest = m.get("dest", "")
        if dest == self.pseudo: self.ui_queue.put(("call_incoming", src)); return
        sd = self.pseudo_to_sock.get(dest)
        if sd:
            try: sd.sendall(make_msg("call_incoming", from_=src))
            except OSError: pass
        elif conn:
            try: conn.sendall(make_msg("call_reject", from_=dest))
            except OSError: pass

    def _router_call_accept(self, m, conn):
        src = m.get("from_", "?"); dest = m.get("dest", "")
        audio_ip = m.get("audio_ip"); audio_port = m.get("audio_port")
        if dest == self.pseudo: self.ui_queue.put(("call_accepted", src, audio_ip, audio_port)); return
        sd = self.pseudo_to_sock.get(dest)
        if sd: sd.sendall(make_msg("call_accepted", from_=src, audio_ip=audio_ip, audio_port=audio_port))

    def _router_call_ready(self, m, conn):
        src = m.get("from_", "?"); dest = m.get("dest", "")
        audio_ip = m.get("audio_ip"); audio_port = m.get("audio_port")
        if dest == self.pseudo: self.ui_queue.put(("call_ready", src, audio_ip, audio_port)); return
        sd = self.pseudo_to_sock.get(dest)
        if sd: sd.sendall(make_msg("call_ready", from_=src, audio_ip=audio_ip, audio_port=audio_port))

    def _router_call_reject(self, m):
        dest = m.get("dest", m.get("from_", ""))
        if dest == self.pseudo: self.ui_queue.put(("call_reject", m.get("from_", "?")))
        else:
            sd = self.pseudo_to_sock.get(dest)
            if sd: sd.sendall(make_msg("call_reject", from_=m.get("from_", "?")))

    def _router_call_end(self, m, conn):
        dest = m.get("dest", ""); src = m.get("from_", "?")
        if dest == self.pseudo: self.ui_queue.put(("call_end", src))
        else:
            sd = self.pseudo_to_sock.get(dest)
            if sd: sd.sendall(make_msg("call_end", from_=src))

    def _servir_udp(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("0.0.0.0", UDP_PORT)); self.udp_sock = s
        except OSError as e: log.warning("UDP: %s", e); return
        annonce = make_udp("announce", port=TCP_PORT, name=APP_NAME, host_pseudo=self.pseudo, version=VERSION)
        prochaine = time.time()
        while self.running:
            try:
                s.settimeout(0.5); data, addr = s.recvfrom(4096)
            except socket.timeout:
                if time.time() >= prochaine:
                    try: s.sendto(annonce, ("255.255.255.255", UDP_PORT))
                    except OSError: pass
                    prochaine = time.time() + ANNOUNCE_EVERY
                continue
            except OSError: break
            msg = parse_udp(data)
            if msg and msg.get("type") == "discover":
                try: s.sendto(annonce, addr)
                except OSError: pass

    def demarrer_rejoindre(self):
        self.mode = "client"; self._ecran_chargement("Recherche des discussions sur le réseau…")
        threading.Thread(target=self._scan_reseau, daemon=True).start()

    def rejoindre_ip_manuel(self):
        ip = simpledialog.askstring("Connexion manuelle", "Adresse IP de l'hébergeur :", parent=self.root)
        if not ip: return
        ip = ip.strip(); self.mode = "client"; self.cible = (ip, TCP_PORT, f"{ip}:{TCP_PORT}")
        self._ecran_chargement(f"Connexion à {ip}:{TCP_PORT}…")
        threading.Thread(target=self._connecter_a, args=(ip, TCP_PORT), daemon=True).start()

    def _scan_reseau(self):
        trouve = {}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("0.0.0.0", UDP_PORT))
        except OSError as e:
            self.ui_queue.put(("connect_fail", f"Scan impossible : {e}")); return
        try: s.sendto(make_udp("discover"), ("255.255.255.255", UDP_PORT))
        except OSError: pass
        echeance = time.time() + SCAN_TIME
        while time.time() < echeance and self.running:
            try: s.settimeout(0.4); data, addr = s.recvfrom(4096)
            except socket.timeout: continue
            except OSError: break
            msg = parse_udp(data)
            if not msg or msg.get("type") != "announce": continue
            ip = addr[0]; port = int(msg.get("port", TCP_PORT)); nom = msg.get("name", f"{ip}:{port}")
            hp = msg.get("host_pseudo", ""); v = msg.get("version", "")
            cle = (ip, port)
            if cle not in trouve:
                trouve[cle] = (nom, hp, v); self.ui_queue.put(("scan_progress", len(trouve)))
        try: s.close()
        except OSError: pass
        serveurs = [(ip, port, nom, hp, v) for (ip, port), (nom, hp, v) in trouve.items()]
        self.ui_queue.put(("discovered", serveurs))

    def _ecran_chargement(self, texte):
        self._reset_frame()
        f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=50)
        self.lbl_spinner = tk.Label(f, text="⠋", font=(FONT, 42), fg=C_BLUE, bg=C_BG)
        self.lbl_spinner.pack(pady=(80, 8))
        self.lbl_chargement = tk.Label(f, text=texte, font=(FONT, 12), fg=C_TEXT, bg=C_BG)
        self.lbl_chargement.pack(pady=4)
        self.lbl_compteur = tk.Label(f, text="0 salon trouvé", font=(FONT, 10), fg=C_GREEN, bg=C_BG)
        self.lbl_compteur.pack(pady=2)
        self._spin_idx = 0; self._animer_spinner()
        b = tk.Button(f, text="Annuler", command=self._ecran_demarrage)
        self._btn_styler(b, C_INP, C_TEXT); b.pack(pady=30)

    def _animer_spinner(self):
        if hasattr(self, "lbl_spinner") and self.lbl_spinner.winfo_exists():
            self.lbl_spinner.config(text=SPINNER[self._spin_idx % len(SPINNER)])
            self._spin_idx += 1; self.root.after(90, self._animer_spinner)

    def _maj_chargement(self, n):
        if hasattr(self, "lbl_compteur") and self.lbl_compteur.winfo_exists():
            p = "s" if n != 1 else ""; self.lbl_compteur.config(text=f"{n} salon{p} trouvé{p}")

    def _fin_scan(self, serveurs):
        if not serveurs:
            self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
            tk.Label(f, text="😕", font=(FONT, 40), bg=C_BG).pack(pady=(80, 4))
            tk.Label(f, text="Aucune discussion trouvée", font=(FONT, 13, "bold"), fg=C_TEXT, bg=C_BG).pack(pady=4)
            tk.Label(f, text="Demande à un ami de lancer un salon, ou héberge le tien !",
                font=(FONT, 10), fg=C_SUB, bg=C_BG, wraplength=380).pack(pady=6)
            b1 = tk.Button(f, text="🖥️  Héberger à la place", command=self.demarrer_hote)
            self._btn_styler(b1, C_BLUE); b1.pack(pady=18)
            b2 = tk.Button(f, text="✍️  Saisir l'IP manuellement", command=self.rejoindre_ip_manuel)
            self._btn_styler(b2, C_INP, C_TEXT); b2.pack(pady=4)
            b3 = tk.Button(f, text="↩ Recommencer", command=self.demarrer_rejoindre)
            self._btn_styler(b3, C_INP, C_TEXT); b3.pack()
            return
        self._ecran_choix_serveur(serveurs)

    def _ecran_choix_serveur(self, serveurs):
        self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
        self._titre_anime(f, "Salons disponibles", C_GREEN, 16)
        liste = tk.Listbox(f, font=(FONT, 12), bg=C_SURF2, fg=C_TEXT, selectbackground=C_BLUE,
            selectforeground=C_BG, relief="flat", bd=0, highlightbackground=C_INP,
            height=min(len(serveurs), 10), activestyle="none")
        for ip, port, nom, hp, v in serveurs:
            lib = f"  {nom}"
            if hp: lib += f"  (chez {hp})"
            lib += f"  —  {ip}:{port}"
            if v: lib += f"  [{v}]"
            liste.insert(tk.END, lib)
        liste.pack(padx=40, pady=6, fill="x"); liste.selection_set(0)
        def connecter():
            sel = liste.curselection()
            if not sel: messagebox.showinfo(APP_NAME, "Choisis un salon."); return
            ip, port, nom, hp, v = serveurs[sel[0]]; self.cible = (ip, port, nom)
            self._ecran_chargement(f"Connexion à {nom} ({ip})…")
            threading.Thread(target=self._connecter_a, args=(ip, port), daemon=True).start()
        b1 = tk.Button(f, text="Se connecter", command=connecter)
        self._btn_styler(b1, C_GREEN); b1.pack(pady=16)
        b2 = tk.Button(f, text="✍️  IP manuelle", command=self.rejoindre_ip_manuel)
        self._btn_styler(b2, C_INP, C_TEXT); b2.pack()

    def _connecter_a(self, ip, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0); s.connect((ip, port)); s.settimeout(None)
            self.host_ip = ip; self._propager_profil_local()
            s.sendall(make_msg("hello", pseudo=self.pseudo, profil=profil_public(self.compte)))
            self.sock = s
            threading.Thread(target=self._boucle_reception, daemon=True).start()
            self.ui_queue.put(("connected",))
        except OSError as e: self.ui_queue.put(("connect_fail", f"Connexion échouée : {e}"))

    def _on_connecte(self): self._construire_interface_chat()

    def _echec_connexion(self, msg):
        messagebox.showerror(APP_NAME, msg); self._ecran_demarrage()

    def _boucle_reception(self):
        def on_line(m):
            t = m.get("type")
            if t == "msg": self.ui_queue.put(("msg", m.get("pseudo", "?"), m.get("text", "")))
            elif t == "sys": self.ui_queue.put(("sys", m.get("text", "")))
            elif t == "mp": self.ui_queue.put(("mp", m.get("from_", "?"), m.get("text", "")))
            elif t == "profil": self.ui_queue.put(("profil", m.get("profil", {})))
            elif t == "profils_init": self.ui_queue.put(("profils_init", m.get("profils", [])))
            elif t == "salons_init": self.ui_queue.put(("salons_init", m.get("salons", [])))
            elif t == "salon_cree": self.ui_queue.put(("salon_cree", m.get("nom", ""), m.get("type_salon", "texte"), m.get("desc", "")))
            elif t == "salon_leave": self.ui_queue.put(("sys", f"🚪 {m.get('pseudo','?')} a quitté #{m.get('salon','')}"))
            elif t == "vocal_join": self.ui_queue.put(("vocal_join", m.get("pseudo", "?"), m.get("salon", "vocal")))
            elif t == "vocal_leave": self.ui_queue.put(("vocal_leave", m.get("pseudo", "?")))
            elif t == "call_incoming": self.ui_queue.put(("call_incoming", m.get("from_", "?")))
            elif t == "call_accepted": self.ui_queue.put(("call_accepted", m.get("from_", "?"), m.get("audio_ip"), m.get("audio_port")))
            elif t == "call_ready": self.ui_queue.put(("call_ready", m.get("from_", "?"), m.get("audio_ip"), m.get("audio_port")))
            elif t == "call_reject": self.ui_queue.put(("call_reject", m.get("from_", "?")))
            elif t == "call_end": self.ui_queue.put(("call_end", m.get("from_", "?")))
        recv_lines(self.sock, on_line)
        self.ui_queue.put(("err", "Connexion perdue avec le serveur."))

    def _init_salons(self, salons):
        self.salons = salons if salons else list(SALONS_DEFAUT)
        if hasattr(self, "liste_salons"): self._rafraichir_liste_salons()

    def _on_salon_cree(self, nom, type_s, desc):
        if nom and not any(s["nom"] == nom for s in self.salons):
            self.salons.append({"nom": nom, "type": type_s, "desc": desc})
            if hasattr(self, "liste_salons"): self._rafraichir_liste_salons()
            self.afficher_systeme(f"📁 Nouveau salon créé : #{nom}")

    def _on_vocal_join(self, pseudo, salon=None):
        self.afficher_systeme(f"🎤 {pseudo} a rejoint le vocal")
        if hasattr(self, "liste_vocal"): self._rafraichir_liste_vocal()

    def _on_vocal_leave(self, pseudo):
        self.afficher_systeme(f"🔇 {pseudo} a quitté le vocal")
        if hasattr(self, "liste_vocal"): self._rafraichir_liste_vocal()

    def _construire_interface_chat(self):
        self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
        barre = tk.Frame(f, bg=C_SURF2); barre.pack(fill="x")
        self._titre_anime_barre = tk.Label(barre, text=f"💬 {APP_NAME}", font=(FONT, 12, "bold"), fg=C_TEXT, bg=C_SURF2)
        self._titre_anime_barre.pack(side="left", padx=14, pady=8)
        self._anim_titre_barre()
        self.lbl_statut = tk.Label(barre, text="", font=(FONT, 9), fg=C_SUB, bg=C_SURF2)
        self.lbl_statut.pack(side="right", padx=14, pady=8); self._rafraichir_statut()
        corps = tk.Frame(f, bg=C_BG); corps.pack(fill="both", expand=True, padx=4, pady=4)
        panneau_g = tk.Frame(corps, bg=C_BG2, width=170); panneau_g.pack(side="left", fill="y", padx=(0, 4))
        panneau_g.pack_propagate(False)
        tk.Label(panneau_g, text="📁 SALONS", font=(FONT, 9, "bold"), fg=C_SUB, bg=C_BG2).pack(pady=(8, 4), padx=10, anchor="w")
        cadre_salons = tk.Frame(panneau_g, bg=C_BG2); cadre_salons.pack(fill="x", padx=4)
        self.liste_salons = cadre_salons
        self._rafraichir_liste_salons()
        tk.Label(panneau_g, text="🎤 VOCAL", font=(FONT, 9, "bold"), fg=C_SUB, bg=C_BG2).pack(pady=(8, 4), padx=10, anchor="w")
        cadre_vocal = tk.Frame(panneau_g, bg=C_BG2); cadre_vocal.pack(fill="x", padx=4)
        self.liste_vocal = cadre_vocal
        self._rafraichir_liste_vocal()
        if self.mode == "host":
            btn_new = tk.Button(panneau_g, text="➕ Nouveau salon", font=(FONT, 9), command=self._creer_salon)
            self._btn_styler(btn_new, C_GREEN, C_BG); btn_new.pack(fill="x", padx=4, pady=4)
        cadre_msg = tk.Frame(corps, bg=C_BG); cadre_msg.pack(side="left", fill="both", expand=True)
        self.lbl_salon_courant = tk.Label(cadre_msg, text="#général", font=(FONT, 11, "bold"), fg=C_BLUE, bg=C_BG)
        self.lbl_salon_courant.pack(anchor="w", padx=4, pady=(4, 2))
        scroll = tk.Scrollbar(cadre_msg); scroll.pack(side="right", fill="y")
        self.zone = tk.Text(cadre_msg, font=(FONT, 11), bg=C_BG2, fg=C_TEXT, insertbackground=C_TEXT,
            yscrollcommand=scroll.set, relief="flat", bd=0, padx=12, pady=10, wrap="word", state="disabled")
        self.zone.pack(side="left", fill="both", expand=True); scroll.config(command=self.zone.yview)
        self.zone.tag_config("sys", foreground=C_DIM, font=(FONT, 9, "italic"))
        self.zone.tag_config("erreur", foreground=C_RED, font=(FONT, 10, "bold"))
        self.zone.tag_config("moi", foreground=C_BLUE, font=(FONT, 11, "bold"))
        self.zone.tag_config("moi_texte", foreground=C_TEXT, font=(FONT, 11))
        self.zone.tag_config("autre_texte", foreground="#bac2de", font=(FONT, 11))
        self.zone.tag_bind("pseudo", "<Button-1>", self._clic_pseudo_event)
        panneau_d = tk.Frame(corps, bg=C_BG2, width=140)
        panneau_d.pack(side="right", fill="y", padx=(4, 0)); panneau_d.pack_propagate(False)
        tk.Label(panneau_d, text="Participants", font=(FONT, 9, "bold"), fg=C_SUB, bg=C_BG2).pack(pady=(8, 4))
        self.liste_part = tk.Text(panneau_d, bg=C_BG2, fg=C_TEXT, relief="flat", bd=0, font=(FONT, 10),
            wrap="none", cursor="hand2", height=20)
        self.liste_part.pack(fill="both", expand=True, padx=6)
        self.liste_part.tag_bind("p", "<Button-1>", self._clic_pseudo_liste)
        self._rafraichir_liste_participants()
        barre_saisie = tk.Frame(f, bg=C_BG); barre_saisie.pack(fill="x", padx=8, pady=(0, 8))
        self.entree = tk.Entry(barre_saisie); self._entree_styler(self.entree)
        self.entree.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entree.bind("<Return>", lambda e: self.envoyer()); self.entree.focus()
        b0 = tk.Button(barre_saisie, text="😀", command=self.ouvrir_selecteur_emoji, padx=10)
        self._btn_styler(b0, C_YELLOW, C_BG); b0.pack(side="left", ipady=4, padx=(0, 4))
        b1 = tk.Button(barre_saisie, text="Envoyer ➤", command=self.envoyer, padx=14)
        self._btn_styler(b1, C_BLUE); b1.pack(side="left", ipady=4)
        b2 = tk.Button(barre_saisie, text="🛍️", command=self.ouvrir_boutique, padx=10)
        self._btn_styler(b2, C_INP, C_YELLOW); b2.pack(side="left", padx=(8, 0), ipady=4)
        b3 = tk.Button(barre_saisie, text="📎", command=self._attacher_media, padx=10)
        self._btn_styler(b3, C_TEAL, C_BG); b3.pack(side="left", padx=(8, 0), ipady=4)
        self.afficher_systeme(f"🟢 Bienvenue {self.pseudo} !")
        if self.mode == "host":
            self.afficher_systeme(f"Tu héberges sur {local_ip()}:{TCP_PORT}. Partage cette IP si l'auto-découverte échoue.")
        if not AUDIO_OK:
            self.afficher_systeme("ℹ Appels vocaux indisponibles (installe PyAudio). Les appels fonctionnent en mode texte.")

    def _rafraichir_liste_salons(self):
        if not hasattr(self, "liste_salons"): return
        for w in self.liste_salons.winfo_children(): w.destroy()
        for s in self.salons:
            icone = "📝" if s.get("type", "texte") == "texte" else "🎤"
            nom = s["nom"]; actif = (nom == self.salon_courant)
            bg = C_BLUE if actif else C_SURF
            fg = C_BG if actif else C_TEXT
            btn = tk.Button(self.liste_salons, text=f" {icone} #{nom}", font=(FONT, 10, "bold" if actif else "normal"),
                bg=bg, fg=fg, relief="flat", bd=0, cursor="hand2", anchor="w",
                command=lambda n=nom: self._changer_salon(n))
            btn.pack(fill="x", pady=1, padx=2)
        salon_courant_type = next((s.get("type","texte") for s in self.salons if s["nom"] == self.salon_courant), "texte")
        if salon_courant_type == "texte":
            b_quitter = tk.Button(self.liste_salons, text="🚪 Quitter le salon", font=(FONT, 8),
                bg=C_INP, fg=C_RED, relief="flat", bd=0, cursor="hand2", command=self._quitter_salon_texte)
            b_quitter.pack(fill="x", pady=(4, 1), padx=2)

    def _changer_salon(self, nom):
        if nom == self.salon_courant: return
        salon = next((s for s in self.salons if s["nom"] == nom), None)
        if not salon: return
        if salon.get("type") == "vocal":
            self._rejoindre_vocal(nom)
            return
        self.salon_courant = nom
        self.lbl_salon_courant.config(text=f"#{nom}")
        self._rafraichir_liste_salons()
        self.afficher_systeme(f"📁 Tu es maintenant dans #{nom}")

    def _quitter_salon_texte(self):
        salons_texte = [s for s in self.salons if s.get("type", "texte") == "texte"]
        if len(salons_texte) <= 1:
            messagebox.showwarning(APP_NAME, "Impossible de quitter : c'est le seul salon textuel."); return
        ancien = self.salon_courant
        self.salons = [s for s in self.salons if s["nom"] != ancien]
        salons_texte = [s for s in self.salons if s.get("type", "texte") == "texte"]
        self.salon_courant = salons_texte[0]["nom"] if salons_texte else "général"
        self.lbl_salon_courant.config(text=f"#{self.salon_courant}")
        self._rafraichir_liste_salons()
        self.afficher_systeme(f"🚪 Tu as quitté #{ancien} → #{self.salon_courant}")
        data = make_msg("salon_leave", pseudo=self.pseudo, salon=ancien)
        if self.mode == "host": self._diffuser(data)
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass

    def _creer_salon(self):
        nom = simpledialog.askstring("Nouveau salon", "Nom du salon :", parent=self.root)
        if not nom: return
        nom = nom.strip().lower()[:20]
        if any(s["nom"] == nom for s in self.salons):
            messagebox.showwarning(APP_NAME, "Ce salon existe déjà."); return
        type_s = messagebox.askyesno("Type de salon", "Salon vocal ? (Non = salon textuel)")
        type_salon = "vocal" if type_s else "texte"
        desc = simpledialog.askstring("Description", "Description (optionnel) :", parent=self.root) or ""
        data = make_msg("salon_cree", nom=nom, type_salon=type_salon, desc=desc[:50])
        if self.mode == "host":
            self.salons.append({"nom":nom, "type":type_salon, "desc":desc[:50]})
            self._rafraichir_liste_salons()
            self._diffuser(data)
            self.afficher_systeme(f"📁 Salon #{nom} créé !")
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: self.afficher_erreur("Impossible de créer le salon.")

    def _rejoindre_vocal(self, salon_nom):
        self.salon_courant = salon_nom
        self.lbl_salon_courant.config(text=f"🎤 #{salon_nom}")
        self._rafraichir_liste_salons()
        if not AUDIO_OK:
            self.afficher_systeme("🎤 Mode vocal texte (PyAudio absent). Tu peux quand même discuter.")
        else:
            self.audio.allouer()
            port = self.audio.mon_port() or 0
            ip = local_ip()
        data = make_msg("vocal_join", pseudo=self.pseudo, salon=salon_nom)
        if self.mode == "host":
            self._diffuser(data)
            self.ui_queue.put(("vocal_join", self.pseudo, salon_nom))
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass
        self.vocal_actif = True
        self._rafraichir_liste_vocal()

    def _quitter_vocal(self):
        if not self.vocal_actif: return
        self.audio.arreter()
        data = make_msg("vocal_leave", pseudo=self.pseudo)
        if self.mode == "host":
            self._diffuser(data)
            self.ui_queue.put(("vocal_leave", self.pseudo))
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass
        self.vocal_actif = False
        self.salon_courant = "général"
        self.lbl_salon_courant.config(text="#général")
        self._rafraichir_liste_salons()
        self._rafraichir_liste_vocal()
        self.afficher_systeme("🔇 Tu as quitté le vocal.")

    def _rafraichir_liste_vocal(self):
        if not hasattr(self, "liste_vocal"): return
        for w in self.liste_vocal.winfo_children(): w.destroy()
        if self.vocal_actif:
            btn = tk.Button(self.liste_vocal, text=f"🔴 {self.pseudo} (toi)", font=(FONT, 9, "bold"),
                bg=C_RED, fg=C_BG, relief="flat", bd=0, cursor="hand2", command=self._quitter_vocal)
            btn.pack(fill="x", pady=1, padx=2)
            btn_q = tk.Button(self.liste_vocal, text="Quitter le vocal", font=(FONT, 8),
                bg=C_INP, fg=C_TEXT, relief="flat", bd=0, cursor="hand2", command=self._quitter_vocal)
            btn_q.pack(fill="x", pady=1, padx=2)
        else:
            tk.Label(self.liste_vocal, text="Personne en vocal", font=(FONT, 8), fg=C_DIM, bg=C_BG2).pack(padx=4)

    def _anim_titre_barre(self):
        couleurs = [C_BLUE, C_PURPLE, C_TEAL, C_GREEN]
        idx = [0]
        def anim():
            if hasattr(self, "_titre_anime_barre") and self._titre_anime_barre.winfo_exists():
                self._titre_anime_barre.config(fg=couleurs[idx[0] % len(couleurs)])
                idx[0] += 1; self.root.after(800, anim)
        anim()

    def _rafraichir_statut(self):
        if not hasattr(self, "lbl_statut") or not self.lbl_statut.winfo_exists(): return
        if self.mode == "host":
            self.lbl_statut.config(text=f"🟢 {local_ip()}:{TCP_PORT}  •  {self.nb_connectes} connecté(s) en plus de toi")
        elif self.cible:
            ip, port, nom = self.cible; self.lbl_statut.config(text=f"🔵 {nom} ({ip}:{port})")

    def _rafraichir_liste_participants(self):
        if not hasattr(self, "liste_part"): return
        self.liste_part.config(state="normal"); self.liste_part.delete("1.0", tk.END)
        for p in self.profils:
            prof = self.profils[p]; badge = badge_emoji(prof.get("badge", "etoile"))
            en_ligne = prof.get("en_ligne", True)
            point = "🟢" if en_ligne else "⚫"
            self.liste_part.insert(tk.END, f" {point} {badge} {p}\n", "p")
        self.liste_part.config(state="disabled")

    def _clic_pseudo_liste(self, event=None):
        idx = self.liste_part.index(f"@{event.x},{event.y}"); ligne = int(idx.split(".")[0])
        pseudos = list(self.profils.keys())
        if 1 <= ligne <= len(pseudos): self._ouvrir_carte_profil(pseudos[ligne-1])

    def _clic_pseudo_event(self, event):
        idx = self.zone.index(f"@{event.x},{event.y}")
        for t in self.zone.tag_names(idx):
            if t.startswith("usr_"): self._ouvrir_carte_profil(t[4:]); return

    def _maj_profil(self, prof):
        p = prof.get("pseudo")
        if p: self.profils[p] = prof; self._rafraichir_liste_participants()

    def _init_profils(self, liste):
        for prof in liste:
            p = prof.get("pseudo")
            if p: self.profils[p] = prof
        self._rafraichir_liste_participants()

    def _propager_profil(self):
        self._propager_profil_local(); prof = self.profils[self.pseudo]
        data = make_msg("profil_update", profil=prof)
        if self.mode == "host": self._diffuser(data)
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass

    def _couleur_tag(self, pseudo):
        prof = self.profils.get(pseudo, {}); cid = prof.get("couleur", COULEURS_DEFAUT)
        couleur = couleur_hex(cid); tag = "usr_" + pseudo
        if tag not in self.couleurs_tags and hasattr(self, "zone"):
            self.zone.tag_config(tag, foreground=couleur, font=(FONT, 11, "bold"))
            self.couleurs_tags.add(tag)
            if couleur_anime(cid): self._animer_pseudo_tag(pseudo, tag, cid)
        return tag

    def _animer_pseudo_tag(self, pseudo, tag, cid):
        if pseudo in self._anim_pseudos: return
        self._anim_pseudos[pseudo] = True
        if cid == "arc": palette = RAINBOW
        elif cid == "galaxy": palette = ["#cba6f7","#89b4fa","#f5c2e7","#b4befe","#cba6f7"]
        elif cid == "feu": palette = ["#f38ba8","#fab387","#f9e2af","#f38ba8","#eba0ac"]
        else: palette = [couleur_hex(cid)]
        idx = [0]
        def anim():
            if not hasattr(self, "zone") or not self.zone.winfo_exists(): return
            self.zone.tag_config(tag, foreground=palette[idx[0] % len(palette)])
            idx[0] += 1; self.root.after(400, anim)
        anim()
    def _ouvrir_carte_profil(self, pseudo):
        prof = self.profils.get(pseudo, {"pseudo":pseudo, "niveau":0, "titre":TITRE_DEFAUT,
            "badge":"etoile", "couleur":COULEURS_DEFAUT, "msgs":0, "coins":0, "appels":0, "xp":0,
            "bio":"", "liens":[], "en_ligne":True, "avatar":"🧑"})
        win = tk.Toplevel(self.root); win.title(f"Profil — {pseudo}"); win.geometry("420x600")
        win.configure(bg=C_BG); win.transient(self.root)
        self._fond_gradient(win, height=50)
        entete = tk.Frame(win, bg=C_BG); entete.pack(fill="x", padx=16, pady=(10, 0))
        avatar = prof.get("avatar", "🧑")
        badge = badge_emoji(prof.get("badge", "etoile"))
        couleur = couleur_hex(prof.get("couleur", COULEURS_DEFAUT))
        tk.Label(entete, text=avatar, font=(FONT, 36), bg=C_BG).pack(side="left", padx=(0, 8))
        col_pseudo = tk.Frame(entete, bg=C_BG); col_pseudo.pack(side="left")
        lbl_pseudo = tk.Label(col_pseudo, text=pseudo, font=(FONT, 18, "bold"), fg=couleur, bg=C_BG)
        lbl_pseudo.pack(anchor="w")
        if couleur_anime(prof.get("couleur", COULEURS_DEFAUT)):
            self._animer_lbl_pseudo(lbl_pseudo, prof.get("couleur"))
        en_ligne = prof.get("en_ligne", True)
        statut_txt = "🟢 En ligne" if en_ligne else "⚫ Hors ligne"
        statut_col = C_GREEN if en_ligne else C_DIM
        tk.Label(col_pseudo, text=f"{badge} {statut_txt}", font=(FONT, 10), fg=statut_col, bg=C_BG).pack(anchor="w")
        tk.Label(win, text="« " + titre_nom(prof.get("titre", "membre")) + " »",
            font=(FONT, 11, "italic"), fg=C_SUB, bg=C_BG).pack()
        niv, xp_dans, taille = info_niveau(prof.get("xp", 0))
        tk.Label(win, text=f"Niveau {niv}", font=(FONT, 13, "bold"), fg=C_YELLOW, bg=C_BG).pack(pady=(8, 2))
        barre_xp = tk.Frame(win, bg=C_INP, height=10); barre_xp.pack(fill="x", padx=40, pady=(0, 4))
        progress = (xp_dans / taille) if taille else 0
        self._anim_barre_xp(barre_xp, progress)
        tk.Label(win, text=f"{xp_dans}/{taille} XP", font=(FONT, 8), fg=C_DIM, bg=C_BG).pack(pady=(0, 8))
        corps = tk.Frame(win, bg=C_BG); corps.pack(fill="both", expand=True, padx=12, pady=4)
        bio = prof.get("bio", "")
        if bio:
            tk.Label(corps, text="📝 À propos", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", pady=(4, 2))
            tk.Label(corps, text=bio, font=(FONT, 10), fg=C_TEXT, bg=C_BG, wraplength=350, justify="left").pack(anchor="w", pady=(0, 8))
        liens = prof.get("liens", [])
        if liens:
            tk.Label(corps, text="🔗 Liens", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", pady=(4, 2))
            zone_liens = tk.Text(corps, font=(FONT, 10), bg=C_BG2, fg=C_TEXT, relief="flat", bd=0,
                wrap="word", height=min(4, len(liens)), width=40, padx=8, pady=6)
            zone_liens.pack(anchor="w", fill="x", pady=(0, 8))
            for lien in liens:
                if not lien: continue
                ltag = "lk_" + str(id(lien))
                zone_liens.tag_config(ltag, foreground=C_BLUE, underline=True)
                zone_liens.tag_bind(ltag, "<Button-1>", lambda e, c=lien: webbrowser.open(c))
                zone_liens.tag_bind(ltag, "<Enter>", lambda e, w=zone_liens: w.config(cursor="hand2"))
                zone_liens.tag_bind(ltag, "<Leave>", lambda e, w=zone_liens: w.config(cursor=""))
                zone_liens.insert(tk.END, lien + "\n", ltag)
            zone_liens.config(state="disabled")
        for lib, val in [("💬 Messages", prof.get("msgs", 0)), ("🪙 Coins", prof.get("coins", 0)),
            ("📞 Appels", prof.get("appels", 0)), ("✨ XP", prof.get("xp", 0))]:
            row = tk.Frame(corps, bg=C_BG); row.pack(fill="x", pady=3)
            tk.Label(row, text=lib, font=(FONT, 11), fg=C_TEXT, bg=C_BG).pack(side="left")
            tk.Label(row, text=str(val), font=(FONT, 11, "bold"), fg=C_GREEN, bg=C_BG).pack(side="right")
        tk.Label(corps, text="Cosmétiques équipés", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", pady=(12, 4))
        tk.Label(corps, text=f"🎨 Couleur : {COULEURS.get(prof.get('couleur'),{}).get('nom','?')}\n"
            f"🏅 Badge : {BADGES.get(prof.get('badge'),{}).get('nom','?')}\n"
            f"🏷️ Titre : {titre_nom(prof.get('titre','membre'))}",
            font=(FONT, 10), fg=C_TEXT, bg=C_BG, justify="left").pack(anchor="w")
        if pseudo == self.pseudo:
            b_mod = tk.Button(corps, text="✏️ Modifier mon profil", command=lambda: self._modifier_profil(win))
            self._btn_styler(b_mod, C_PURPLE); b_mod.pack(pady=12)
        else:
            btns = tk.Frame(corps, bg=C_BG); btns.pack(pady=12)
            b1 = tk.Button(btns, text="💬 MP", command=lambda: self._ouvrir_fenetre_mp(pseudo))
            self._btn_styler(b1, C_BLUE); b1.pack(side="left", padx=6)
            b2 = tk.Button(btns, text="📞 Appeler", command=lambda: self._demarrer_appel(pseudo))
            self._btn_styler(b2, C_GREEN); b2.pack(side="left", padx=6)

    def _modifier_profil(self, parent_win):
        win = tk.Toplevel(self.root); win.title("Modifier mon profil"); win.geometry("460x480")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_gradient(win, height=40)
        tk.Label(win, text="✏️ Modifier mon profil", font=(FONT, 15, "bold"), fg=C_PURPLE, bg=C_BG).pack(pady=(8, 8))
        tk.Label(win, text="🧑 Avatar émoji", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=24)
        ent_avatar = tk.Entry(win, font=(FONT, 16), width=4); self._entree_styler(ent_avatar)
        ent_avatar.insert(0, self.compte.get("avatar_emoji", "🧑"))
        ent_avatar.pack(anchor="w", padx=24, pady=(2, 8))
        tk.Label(win, text="📝 Bio", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=24)
        txt_bio = tk.Text(win, font=(FONT, 11), bg=C_INP, fg=C_TEXT, insertbackground=C_TEXT,
            relief="flat", bd=0, wrap="word", height=4, padx=10, pady=8)
        txt_bio.pack(fill="x", padx=24, pady=(2, 8))
        txt_bio.insert("1.0", self.compte.get("bio", ""))
        tk.Label(win, text="🔗 Liens (un par ligne)", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=24)
        txt_liens = tk.Text(win, font=(FONT, 11), bg=C_INP, fg=C_TEXT, insertbackground=C_TEXT,
            relief="flat", bd=0, wrap="word", height=5, padx=10, pady=8)
        txt_liens.pack(fill="x", padx=24, pady=(2, 8))
        txt_liens.insert("1.0", "\n".join(self.compte.get("liens", [])))
        def sauver():
            bio = txt_bio.get("1.0", tk.END).strip()[:300]
            liens_raw = txt_liens.get("1.0", tk.END).strip().split("\n")
            liens = [l.strip() for l in liens_raw if l.strip()][:10]
            avatar = ent_avatar.get().strip()[:2] or "🧑"
            self.compte["bio"] = bio; self.compte["liens"] = liens; self.compte["avatar_emoji"] = avatar
            self.gc.sauver(); self._propager_profil()
            win.destroy(); parent_win.destroy(); self._ouvrir_carte_profil(self.pseudo)
            messagebox.showinfo(APP_NAME, "Profil mis à jour !")
        b = tk.Button(win, text="✔️ Enregistrer", command=sauver)
        self._btn_styler(b, C_GREEN); b.pack(pady=10)

    def _animer_lbl_pseudo(self, lbl, cid):
        if cid == "arc": palette = RAINBOW
        elif cid == "galaxy": palette = ["#cba6f7","#89b4fa","#f5c2e7","#b4befe"]
        elif cid == "feu": palette = ["#f38ba8","#fab387","#f9e2af","#eba0ac"]
        else: palette = [couleur_hex(cid)]
        idx = [0]
        def anim():
            if lbl.winfo_exists():
                lbl.config(fg=palette[idx[0] % len(palette)]); idx[0] += 1; self.root.after(400, anim)
        anim()

    def _anim_barre_xp(self, barre, target):
        cur = [0.0]
        def anim():
            if not barre.winfo_exists(): return
            cur[0] += 0.05
            if cur[0] > target: cur[0] = target
            for w in barre.winfo_children(): w.destroy()
            tk.Frame(barre, bg=C_GREEN).place(x=0, y=0, relwidth=cur[0], relheight=1)
            if cur[0] < target: self.root.after(20, anim)
        anim()

    def envoyer(self):
        texte = self.entree.get().strip()
        if not texte: return
        self.entree.delete(0, tk.END)
        if len(texte) > 500: texte = texte[:500]
        data = make_msg("msg", pseudo=self.pseudo, text=texte, salon=self.salon_courant)
        if self.mode == "host": self._diffuser(data)
        else:
            try: self.sock.sendall(data)
            except OSError: self.afficher_erreur("Connexion perdue : message non envoyé."); return
        self._gagner_xp(1, coins=1, msgs=1)
        self.afficher_message(self.pseudo, texte, moi=True)
        son_envoi(self.compte)
        for mot in texte.split():
            if mot.startswith("@") and mot[1:] in self.profils and mot[1:] != self.pseudo:
                self._toast(f"🏷️ Tu as mentionné {mot[1:]}", None)

    def _gagner_xp(self, xp, coins=0, msgs=0, appels=0):
        ancien_niv, _ = niveau_from_xp(self.compte["xp"])
        self.compte["xp"] += xp; self.compte["coins"] += coins
        self.compte["msgs"] += msgs; self.compte["appels"] += appels
        nouveau_niv, _ = niveau_from_xp(self.compte["xp"])
        self.gc.sauver(); self._rafraichir_compte_ui(); self._propager_profil_local()
        if nouveau_niv > ancien_niv:
            self.compte["coins"] += 50; self.gc.sauver(); self._rafraichir_compte_ui()
            self._toast(f"🎉 Niveau {nouveau_niv} ! +50 🪙", None); beep(1200, 200)

    def afficher_message(self, pseudo, texte, moi=False):
        if not hasattr(self, "zone"): return
        prof = self.profils.get(pseudo, {}); badge = badge_emoji(prof.get("badge", "etoile"))
        avatar = prof.get("avatar", "🧑")
        self.zone.config(state="normal")
        prefixe = f"{avatar} {badge} [{pseudo}]"
        if moi:
            self.zone.insert(tk.END, prefixe, "moi")
        else:
            debut = self.zone.index("end"); self.zone.insert(tk.END, prefixe)
            self.zone.tag_add(self._couleur_tag(pseudo), debut, "end")
            self.zone.tag_add("pseudo", debut, "end")
        self.zone.insert(tk.END, "  ")
        self._rendre_liens(self.zone, texte, "moi_texte" if moi else "autre_texte")
        self.zone.insert(tk.END, "\n")
        self.zone.config(state="disabled"); self.zone.see(tk.END)
        if not moi: son_notif(self.compte)

    def afficher_systeme(self, texte):
        if not hasattr(self, "zone"): return
        self.zone.config(state="normal"); self.zone.insert(tk.END, texte + "\n", "sys")
        self.zone.config(state="disabled"); self.zone.see(tk.END)

    def afficher_erreur(self, texte):
        if not hasattr(self, "zone"): return
        self.zone.config(state="normal"); self.zone.insert(tk.END, "⚠ " + texte + "\n", "erreur")
        self.zone.config(state="disabled"); self.zone.see(tk.END)

    def _rendre_liens(self, widget, texte, tag_base):
        self._img_cache = getattr(self, "_img_cache", {})
        img_pat = re.compile(r'\[img:([^\]]+)\]')
        parts = []; pos = 0
        for m in img_pat.finditer(texte):
            if m.start() > pos: parts.append(("txt", texte[pos:m.start()]))
            parts.append(("img", m.group(1))); pos = m.end()
        if pos < len(texte): parts.append(("txt", texte[pos:]))
        if not parts: parts = [("txt", texte)]
        try:
            from PIL import Image, ImageTk
            PIL_OK = True
        except Exception:
            PIL_OK = False
        for kind, content in parts:
            if kind == "txt":
                self._rendre_urls(widget, content, tag_base)
            elif kind == "img":
                if not PIL_OK:
                    widget.insert(tk.END, f"[{content}]", tag_base); continue
                path = content.strip()
                if not os.path.isfile(path):
                    widget.insert(tk.END, f"[img:{content}]", tag_base); continue
                try:
                    img = Image.open(path); img.thumbnail((240, 240))
                    photo = ImageTk.PhotoImage(img)
                    key = f"{path}_{id(widget)}"; self._img_cache[key] = photo
                    widget.image_create(tk.END, image=photo)
                    widget.insert(tk.END, " ")
                except Exception:
                    widget.insert(tk.END, f"[img:{content}]", tag_base)

    def _rendre_urls(self, widget, texte, tag_base):
        pos = 0
        for m in URL_RE.finditer(texte):
            if m.start() > pos: widget.insert(tk.END, texte[pos:m.start()], tag_base)
            url_text = m.group(0); link = _normalise_url(url_text)
            tag = f"link_{id(widget)}_{m.start()}"
            if link:
                widget.tag_config(tag, foreground=C_BLUE, underline=True, font=(FONT, 11, "underline"))
                widget.tag_bind(tag, "<Button-1>", lambda e, u=link: webbrowser.open(u))
                widget.tag_bind(tag, "<Enter>", lambda e: widget.config(cursor="hand2"))
                widget.tag_bind(tag, "<Leave>", lambda e: widget.config(cursor=""))
                widget.insert(tk.END, url_text, tag)
            else:
                if url_text.lower().endswith((".mp4", ".webm", ".mov", ".mkv")):
                    tag_v = f"vid_{id(widget)}_{m.start()}"
                    widget.tag_config(tag_v, foreground=C_TEAL, underline=True, font=(FONT, 11, "underline"))
                    widget.tag_bind(tag_v, "<Button-1>", lambda e, u=url_text: self._ouvrir_media_ext(u))
                    widget.insert(tk.END, f"🎬 {url_text}", tag_v)
                else:
                    widget.insert(tk.END, url_text, tag_base)
            pos = m.end()
        if pos < len(texte): widget.insert(tk.END, texte[pos:], tag_base)

    def _ouvrir_media_ext(self, chemin):
        try:
            if platform.system() == "Windows": os.startfile(chemin)
            elif platform.system() == "Darwin": subprocess.Popen(["open", chemin])
            else: subprocess.Popen(["xdg-open", chemin])
        except Exception as e:
            self._toast("Ouverture impossible", str(e))

    def _ouvrir_fenetre_mp(self, dest):
        if dest in self.fenetres_mp and self.fenetres_mp[dest].winfo_exists():
            self.fenetres_mp[dest].lift(); self.fenetres_mp[dest].focus_set(); return
        win = tk.Toplevel(self.root); win.title(f"MP avec {dest}"); win.geometry("420x440")
        win.configure(bg=C_BG); win.transient(self.root)
        self._fond_gradient(win, height=35)
        tk.Label(win, text=f"🔒 Conversation privée avec {dest}", font=(FONT, 11, "bold"), fg=C_TEXT, bg=C_BG).pack(pady=6)
        scroll = tk.Scrollbar(win); scroll.pack(side="right", fill="y")
        txt = tk.Text(win, font=(FONT, 11), bg=C_BG2, fg=C_TEXT, yscrollcommand=scroll.set,
            relief="flat", bd=0, padx=10, pady=10, wrap="word", state="disabled")
        txt.pack(fill="both", expand=True, padx=8, pady=4); scroll.config(command=txt.yview)
        win.txt = txt
        entree_mp = tk.Entry(win); self._entree_styler(entree_mp)
        entree_mp.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8, ipady=6)
        def envoyer_mp(e=None):
            texte = entree_mp.get().strip()
            if not texte: return
            entree_mp.delete(0, tk.END); self._envoyer_mp(dest, texte)
            self._afficher_mp(dest, self.pseudo, texte, win, win.txt, moi=True)
        entree_mp.bind("<Return>", envoyer_mp)
        b = tk.Button(win, text="➤", command=envoyer_mp, padx=14)
        self._btn_styler(b, C_BLUE); b.pack(side="left", padx=(0, 8), pady=8, ipady=6)
        for src, msg in self.mp_historique.get(dest, []):
            self._afficher_mp(dest, src, msg, win, win.txt, moi=(src == self.pseudo))
        win.protocol("WM_DELETE_WINDOW", lambda: self._fermer_fenetre_mp(dest, win))
        self.fenetres_mp[dest] = win; self.mp_non_lus[dest] = 0

    def _fermer_fenetre_mp(self, dest, win):
        win.destroy(); self.fenetres_mp.pop(dest, None)

    def _envoyer_mp(self, dest, texte):
        if self.mode == "host":
            if dest == self.pseudo: return
            sd = self.pseudo_to_sock.get(dest)
            if sd:
                try: sd.sendall(make_msg("mp", from_=self.pseudo, dest=dest, text=texte))
                except OSError: self.afficher_erreur(f"MP vers {dest} échoué.")
            else: self.afficher_erreur(f"{dest} est introuvable.")
        else:
            try: self.sock.sendall(make_msg("mp", from_=self.pseudo, dest=dest, text=texte))
            except OSError: self.afficher_erreur("MP non envoyé (connexion perdue).")
        self._gagner_xp(2, coins=1)

    def _afficher_mp(self, dest, src, texte, win, txt, moi=False):
        txt.config(state="normal")
        couleur = C_BLUE if moi else couleur_hex(self.profils.get(src, {}).get("couleur", COULEURS_DEFAUT))
        tag = f"mp_{src}_{id(win)}"; txt.tag_config(tag, foreground=couleur, font=(FONT, 11, "bold"))
        txt.insert(tk.END, f"[{src}] ", tag)
        self._rendre_liens(txt, texte, "moi_texte" if moi else "autre_texte")
        txt.insert(tk.END, "\n")
        txt.config(state="disabled"); txt.see(tk.END)

    def _on_mp_recu(self, src, texte):
        self.mp_historique.setdefault(src, []).append((src, texte))
        if src in self.fenetres_mp and self.fenetres_mp[src].winfo_exists():
            win = self.fenetres_mp[src]; self._afficher_mp(src, src, texte, win, win.txt); win.lift()
        else: self.mp_non_lus[src] = self.mp_non_lus.get(src, 0) + 1
        son_notif(self.compte)
        self._toast(f"✉️ MP de {src} : {texte[:30]}", lambda: self._ouvrir_fenetre_mp(src))
    def _demarrer_appel(self, dest):
        if dest == self.pseudo: return
        if dest in self.appels: messagebox.showinfo(APP_NAME, "Un appel est déjà en cours."); return
        if dest in self.fenetres_appel and self.fenetres_appel[dest].winfo_exists(): return
        if self.mode == "host":
            sd = self.pseudo_to_sock.get(dest)
            if not sd: self.afficher_erreur(f"{dest} est introuvable."); return
            try: sd.sendall(make_msg("call_incoming", from_=self.pseudo))
            except OSError: self.afficher_erreur("Demande d'appel échouée.")
        else:
            try: self.sock.sendall(make_msg("call_request", from_=self.pseudo, dest=dest))
            except OSError: self.afficher_erreur("Demande d'appel échouée."); return
        self._ouvrir_fenetre_appel(dest, appelant=True)

    def _ouvrir_fenetre_appel(self, peer, appelant=False):
        win = tk.Toplevel(self.root); win.title(f"Appel avec {peer}"); win.geometry("340x380")
        win.configure(bg=C_BG); win.transient(self.root)
        tk.Label(win, text="📞", font=(FONT, 40), bg=C_BG, fg=C_GREEN).pack(pady=(16, 4))
        self.lbl_appel_peer = tk.Label(win, text=peer, font=(FONT, 16, "bold"), fg=C_TEXT, bg=C_BG)
        self.lbl_appel_peer.pack()
        self.lbl_appel_statut = tk.Label(win, text="En attente…" if appelant else "Appel entrant…", font=(FONT, 11), fg=C_SUB, bg=C_BG)
        self.lbl_appel_statut.pack(pady=4)
        self.lbl_duree = tk.Label(win, text="00:00", font=(FONT, 12, "bold"), fg=C_GREEN, bg=C_BG)
        self.lbl_duree.pack(pady=4)
        btns = tk.Frame(win, bg=C_BG); btns.pack(pady=18)
        self.btn_mute = tk.Button(btns, text="🔇 Muet", command=self._toggle_mute)
        self._btn_styler(self.btn_mute, C_INP, C_TEXT); self.btn_mute.pack(side="left", padx=6)
        b = tk.Button(btns, text="📞 Raccrocher", command=lambda: self._raccrocher(peer))
        self._btn_styler(b, C_RED); b.pack(side="left", padx=6)
        if not AUDIO_OK:
            tk.Label(win, text="Mode texte (PyAudio absent)\n— parle via le mini-chat —",
                font=(FONT, 9), fg=C_DIM, bg=C_BG, justify="center").pack(pady=(0, 4))
            ent = tk.Entry(win); self._entree_styler(ent)
            ent.pack(fill="x", padx=16, pady=4, ipady=5)
            ent.bind("<Return>", lambda e: self._appel_mini_msg(peer, ent))
        self._appel_start = None
        win.protocol("WM_DELETE_WINDOW", lambda: self._raccrocher(peer))
        self.fenetres_appel[peer] = win

    def _toggle_mute(self):
        if self.audio.actif:
            muet = self.audio.basculer_mute()
            if muet: self.btn_mute.config(text="🎙️ Activer", bg=C_GREEN, fg=C_BG)
            else: self.btn_mute.config(text="🔇 Muet", bg=C_INP, fg=C_TEXT)

    def _appel_mini_msg(self, peer, ent):
        txt = ent.get().strip()
        if not txt: return
        ent.delete(0, tk.END)
        data = make_msg("mp", from_=self.pseudo, dest=peer, text=f"[appel] {txt}")
        if self.mode == "host":
            sd = self.pseudo_to_sock.get(peer)
            if sd:
                try: sd.sendall(data)
                except OSError: pass
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass
        if peer in self.fenetres_mp and self.fenetres_mp[peer].winfo_exists():
            self._afficher_mp(peer, self.pseudo, txt, self.fenetres_mp[peer], self.fenetres_mp[peer].txt, moi=True)

    def _on_appel_entrant(self, src):
        sonnerie(self.compte)
        result = messagebox.askyesno(APP_NAME, f"📞 {src} t'appelle ! Accepter ?")
        stop_sonnerie()
        if result: self._accepter_appel(src)
        else: self._refuser_appel(src)

    def _accepter_appel(self, src):
        self._ouvrir_fenetre_appel(src, appelant=False)
        self.audio.allouer()
        port = self.audio.mon_port() or 0
        ip = local_ip()
        data = make_msg("call_accept", from_=self.pseudo, dest=src, audio_ip=ip, audio_port=port)
        if self.mode == "host":
            sd = self.pseudo_to_sock.get(src)
            if sd:
                try: sd.sendall(data)
                except OSError: pass
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass
        self._gagner_xp(5, coins=5, appels=1)

    def _refuser_appel(self, src):
        data = make_msg("call_reject", from_=self.pseudo, dest=src)
        if self.mode == "host":
            sd = self.pseudo_to_sock.get(src)
            if sd:
                try: sd.sendall(data)
                except OSError: pass
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass

    def _on_appel_accepte(self, src, audio_ip, audio_port):
        if src not in self.fenetres_appel: return
        win = self.fenetres_appel[src]
        win._lbl_statut = getattr(win, "_lbl_statut", None)
        if hasattr(win, "lbl_appel_statut"): win.lbl_appel_statut.config(text="Connecté !")
        self.audio.allouer()
        my_port = self.audio.mon_port() or 0
        my_ip = local_ip()
        data = make_msg("call_ready", from_=self.pseudo, dest=src, audio_ip=my_ip, audio_port=my_port)
        if self.mode == "host":
            sd = self.pseudo_to_sock.get(src)
            if sd:
                try: sd.sendall(data)
                except OSError: pass
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass
        if audio_ip and audio_port:
            self.audio.peer = (audio_ip, audio_port)
            threading.Thread(target=self.audio.demarrer_streams, args=(audio_ip, audio_port), daemon=True).start()
        self._demarrer_timer_appel(src)

    def _on_appel_ready(self, src, audio_ip, audio_port):
        if src not in self.fenetres_appel: return
        win = self.fenetres_appel[src]
        if hasattr(win, "lbl_appel_statut"): win.lbl_appel_statut.config(text="Connecté !")
        if audio_ip and audio_port:
            self.audio.peer = (audio_ip, audio_port)
            threading.Thread(target=self.audio.demarrer_streams, args=(audio_ip, audio_port), daemon=True).start()
        self._demarrer_timer_appel(src)

    def _demarrer_timer_appel(self, cible):
        win = self.fenetres_appel.get(cible)
        if not win: return
        win._timer_start = time.time()
        def tick():
            if not win.winfo_exists() or not hasattr(win, "_timer_start") or win._timer_start is None: return
            elap = int(time.time() - win._timer_start)
            mm, ss = divmod(elap, 60)
            if hasattr(win, "lbl_duree"): win.lbl_duree.config(text=f"{mm:02d}:{ss:02d}")
            self.root.after(1000, tick)
        tick()

    def _raccrocher(self, cible):
        self.audio.arreter()
        data = make_msg("call_end", from_=self.pseudo, dest=cible)
        if self.mode == "host":
            sd = self.pseudo_to_sock.get(cible)
            if sd:
                try: sd.sendall(data)
                except OSError: pass
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass
        if cible in self.fenetres_appel:
            self.fenetres_appel[cible].destroy()
            del self.fenetres_appel[cible]

    def _on_appel_refuse(self, src):
        if src in self.fenetres_appel:
            win = self.fenetres_appel[src]
            if hasattr(win, "lbl_appel_statut"): win.lbl_appel_statut.config(text=f"{src} a refusé l'appel.")
            self.root.after(3000, lambda: win.destroy() if win.winfo_exists() else None)
            self.fenetres_appel.pop(src, None)

    def _on_appel_fin(self, src):
        self.audio.arreter()
        if src in self.fenetres_appel:
            win = self.fenetres_appel[src]
            if win.winfo_exists():
                if hasattr(win, "lbl_appel_statut"): win.lbl_appel_statut.config(text="Appel terminé.")
                if hasattr(win, "lbl_duree"): win.lbl_duree.config(text="00:00")
                self.root.after(2000, lambda: win.destroy() if win.winfo_exists() else None)
            self.fenetres_appel.pop(src, None)

    def _toast(self, titre, callback=None):
        if not hasattr(self, "root") or not self.root.winfo_exists(): return
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg=C_SURF2)
        x = self.root.winfo_x() + self.root.winfo_width() - 280
        y = self.root.winfo_y() + 20
        popup.geometry(f"260x50+{x}+{y}")
        lbl = tk.Label(popup, text=titre, font=(FONT, 11, "bold"), fg=C_BLUE, bg=C_SURF2)
        lbl.pack(pady=8)
        popup.attributes("-alpha", 0.95)
        if callback:
            def cliquer(e): callback(); popup.destroy()
            lbl.bind("<Button-1>", cliquer); lbl.config(cursor="hand2")
        popup.after(4500, popup.destroy)
    def ouvrir_parametres(self):
        win = tk.Toplevel(self.root); win.title("Paramètres"); win.geometry("560x580")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_gradient(win, height=40)
        tk.Label(win, text="⚙️ Paramètres", font=(FONT, 15, "bold"), fg=C_PURPLE, bg=C_BG).pack(pady=(8, 6))
        nb = ttk.Notebook(win); nb.pack(fill="both", expand=True, padx=12, pady=12)
        f_app = tk.Frame(nb, bg=C_BG); f_sons = tk.Frame(nb, bg=C_BG); f_profil = tk.Frame(nb, bg=C_BG)
        nb.add(f_app, text="🎨 Apparence")
        nb.add(f_sons, text="🔊 Sons")
        nb.add(f_profil, text="👤 Profil")
        self._param_page_apparence(f_app)
        self._param_page_sons(f_sons)
        self._param_page_profil(f_profil)
        btn_f = tk.Button(win, text="Fermer", command=win.destroy)
        self._btn_styler(btn_f, C_INP, C_TEXT); btn_f.pack(pady=8)

    def _param_page_apparence(self, parent):
        tk.Label(parent, text="Thème", font=(FONT, 14, "bold"), fg=C_BLUE, bg=C_BG).pack(anchor="w", padx=16, pady=(16, 6))
        cadre = tk.Frame(parent, bg=C_SURF); cadre.pack(fill="x", padx=16, pady=4)
        for nom_theme in THEMES:
            ligne = tk.Frame(cadre, bg=C_SURF); ligne.pack(fill="x", pady=3)
            icone = "🌙" if nom_theme == "sombre" else "☀️"
            tk.Label(ligne, text=f"{icone} {nom_theme.capitalize()}", font=(FONT, 12), fg=C_TEXT, bg=C_SURF).pack(side="left", padx=12, pady=8)
            actuel = self.compte.get("theme", "sombre")
            if nom_theme == actuel:
                tk.Label(ligne, text="✓ Actif", font=(FONT, 10, "bold"), fg=C_GREEN, bg=C_SURF).pack(side="right", padx=12)
            else:
                btn = tk.Button(ligne, text="Activer", command=lambda t=nom_theme: self._changer_theme(t, parent))
                self._btn_styler(btn, C_BLUE); btn.pack(side="right", padx=12, ipady=3)
        tk.Label(parent, text="Le thème s'applique à toute l'application immédiatement.", font=(FONT, 9, "italic"), fg=C_DIM, bg=C_BG).pack(anchor="w", padx=16, pady=(8, 0))

    def _changer_theme(self, nom, parent=None):
        self.compte["theme"] = nom; self.gc.sauver()
        _appliquer_theme(nom)
        self.root.configure(bg=C_BG)
        if hasattr(self, "frame"): self.frame.configure(bg=C_BG)
        self._toast("Thème", f"Thème {nom} appliqué.")
        if parent:
            for w in parent.winfo_children(): w.destroy()
            self._param_page_apparence(parent)

    def _param_page_sons(self, parent):
        tk.Label(parent, text="Sons personnalisés", font=(FONT, 14, "bold"), fg=C_BLUE, bg=C_BG).pack(anchor="w", padx=16, pady=(16, 4))
        for cle, label in [("sonnerie", "Sonnerie d'appel"), ("notif", "Notification MP"), ("son_envoi", "Son d'envoi"), ("son_connexion", "Son de connexion")]:
            cadre = tk.Frame(parent, bg=C_SURF); cadre.pack(fill="x", padx=16, pady=3)
            courant = self.compte.get(cle, "")
            tk.Label(cadre, text=label, font=(FONT, 10), fg=C_TEXT, bg=C_SURF).pack(side="left", padx=12, pady=6)
            tk.Label(cadre, text=(courant[:25] + "…") if len(courant) > 25 else (courant or "Par défaut"), font=(FONT, 8), fg=C_DIM, bg=C_SURF).pack(side="left", padx=8)
            btn = tk.Button(cadre, text="📂", command=lambda c=cle: self._choisir_son(c))
            self._btn_styler(btn, C_BLUE); btn.pack(side="right", padx=12, ipady=2)
        tk.Label(parent, text="Sons préchargés (téléchargement internet)", font=(FONT, 12, "bold"), fg=C_PURPLE, bg=C_BG).pack(anchor="w", padx=16, pady=(16, 4))
        cadre_p = tk.Frame(parent, bg=C_BG); cadre_p.pack(fill="x", padx=16, pady=4)
        for i, (nom, url) in enumerate(SONS_PRESETS.items()):
            ligne = tk.Frame(cadre_p, bg=C_SURF); ligne.pack(fill="x", pady=2)
            tk.Label(ligne, text=nom, font=(FONT, 9), fg=C_TEXT, bg=C_SURF).pack(side="left", padx=12, pady=6)
            btn_test = tk.Button(ligne, text="▶", command=lambda u=url: self._tester_son_url(u))
            self._btn_styler(btn_test, C_INP, C_TEXT); btn_test.pack(side="right", padx=4, ipady=2)
            btn_dl = tk.Button(ligne, text="⬇ Sonnerie", command=lambda u=url: self._telecharger_son(u, "sonnerie"))
            self._btn_styler(btn_dl, C_GREEN); btn_dl.pack(side="right", padx=4, ipady=2)
            btn_dn = tk.Button(ligne, text="⬇ Notif", command=lambda u=url: self._telecharger_son(u, "notif"))
            self._btn_styler(btn_dn, C_TEAL, C_BG); btn_dn.pack(side="right", padx=4, ipady=2)
        tk.Label(parent, text="Les fichiers sont stockés localement et réutilisés.", font=(FONT, 9, "italic"), fg=C_DIM, bg=C_BG).pack(anchor="w", padx=16, pady=(8, 0))

    def _choisir_son(self, cle):
        chemin = filedialog.askopenfilename(title=f"Choisir son — {cle}", filetypes=[("Audio", "*.mp3 *.wav *.ogg *.m4a"), ("Tous", "*.*")])
        if not chemin: return
        self.compte[cle] = chemin; self.gc.sauver()
        _SONS_PERSO[cle.replace("son_", "").replace("sonnerie", "sonnerie")] = chemin
        if cle == "sonnerie": _SONS_PERSO["sonnerie"] = chemin
        elif cle == "notif": _SONS_PERSO["notif"] = chemin
        elif cle == "son_envoi": _SONS_PERSO["envoi"] = chemin
        elif cle == "son_connexion": _SONS_PERSO["connexion"] = chemin
        self._toast("Son configuré", f"{cle} mis à jour.")

    def _telecharger_son(self, url, cle):
        ext = url.rsplit(".", 1)[-1]
        dossier = "sons_lanchat"; os.makedirs(dossier, exist_ok=True)
        chemin = os.path.join(dossier, f"{cle}.{ext}")
        try:
            urllib.request.urlretrieve(url, chemin)
            self.compte[cle] = chemin; self.gc.sauver()
            if cle == "sonnerie": _SONS_PERSO["sonnerie"] = chemin
            elif cle == "notif": _SONS_PERSO["notif"] = chemin
            self._toast("Téléchargé", f"{cle} sauvegardé localement.")
        except Exception as e:
            self._toast("Erreur", f"Téléchargement impossible: {e}")

    def _tester_son_url(self, url):
        try:
            dossier = "sons_lanchat"; os.makedirs(dossier, exist_ok=True)
            chemin = os.path.join(dossier, "test.mp3")
            urllib.request.urlretrieve(url, chemin)
            _jouer_fichier(chemin)
        except Exception:
            beep()

    def _param_page_profil(self, parent):
        tk.Label(parent, text="Modifier mon profil public", font=(FONT, 14, "bold"), fg=C_BLUE, bg=C_BG).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(parent, text="🧑 Avatar émoji", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=16, pady=(4, 2))
        ent_avatar = tk.Entry(parent, font=(FONT, 14), width=4); self._entree_styler(ent_avatar)
        ent_avatar.insert(0, self.compte.get("avatar_emoji", "🧑"))
        ent_avatar.pack(anchor="w", padx=16, pady=(2, 8))
        tk.Label(parent, text="Bio (visible par tous)", font=(FONT, 10), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=16, pady=(4, 2))
        txt_bio = tk.Text(parent, font=(FONT, 11), bg=C_BG2, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", height=4, wrap="word")
        txt_bio.pack(fill="x", padx=16); txt_bio.insert("1.0", self.compte.get("bio", ""))
        tk.Label(parent, text="Liens (un par ligne)", font=(FONT, 10), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=16, pady=(8, 2))
        txt_liens = tk.Text(parent, font=(FONT, 11), bg=C_BG2, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", height=4, wrap="word")
        txt_liens.pack(fill="x", padx=16)
        for lien in self.compte.get("liens", []): txt_liens.insert(tk.END, lien + "\n")
        def sauver():
            bio = txt_bio.get("1.0", tk.END).strip()[:300]
            lignes = txt_liens.get("1.0", tk.END).strip().split("\n")
            liens = [l.strip() for l in lignes if l.strip()]
            avatar = ent_avatar.get().strip()[:2] or "🧑"
            self.compte["bio"] = bio; self.compte["liens"] = liens; self.compte["avatar_emoji"] = avatar
            self.gc.sauver(); self._propager_profil()
            self._toast("Profil", "Modifications enregistrées.")
        btn_s = tk.Button(parent, text="💾 Enregistrer", command=sauver)
        self._btn_styler(btn_s, C_GREEN); btn_s.pack(anchor="e", padx=16, pady=12)

    def ouvrir_selecteur_emoji(self):
        win = tk.Toplevel(self.root); win.title("😀 Sélecteur d'émojis"); win.geometry("540x580")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        zone_categories = tk.Frame(win, bg=C_BG2); zone_categories.pack(fill="x")
        zone_emojis = tk.Frame(win, bg=C_BG); zone_emojis.pack(fill="both", expand=True)
        conteneur = tk.Frame(zone_emojis, bg=C_BG); conteneur.pack(fill="both", expand=True, padx=8, pady=8)
        barre_perso = tk.Frame(win, bg=C_BG); barre_perso.pack(fill="x", padx=8, pady=6)
        btn_import = tk.Button(barre_perso, text="📁 Importer mon émoji / GIF", command=self._importer_emoji)
        self._btn_styler(btn_import, C_PURPLE); btn_import.pack(side="left", ipady=4, padx=8)
        persos = _lister_emojis_perso()
        if persos:
            tk.Label(barre_perso, text=f"{len(persos)} perso(s)", font=(FONT, 9), fg=C_DIM, bg=C_BG).pack(side="left", padx=8)
        def inserer(e):
            if hasattr(self, "entree"):
                self.entree.insert(tk.INSERT, e)
                win.destroy(); self.entree.focus()
        def afficher_categorie(cat):
            for w in conteneur.winfo_children(): w.destroy()
            liste = EMOJIS.get(cat, [])
            try:
                from PIL import Image, ImageTk
                PIL_OK = True
            except Exception:
                PIL_OK = False
            for emoji in liste:
                btn = tk.Button(conteneur, text=emoji, font=(FONT, 18), bg=C_SURF, fg=C_TEXT, relief="flat", bd=0, cursor="hand2", command=lambda e=emoji: inserer(e))
                btn.grid(padx=2, pady=2)
            if persos and cat == "Perso" and PIL_OK:
                for f in persos:
                    try:
                        path = os.path.join(EMOJI_DIR, f)
                        img = Image.open(path); img.thumbnail((40, 40))
                        photo = ImageTk.PhotoImage(img)
                        btn = tk.Button(conteneur, image=photo, bg=C_SURF, relief="flat", bd=0, cursor="hand2", command=lambda p=path: inserer(f"[img:{p}]"))
                        btn.image = photo; btn.grid(padx=2, pady=2)
                    except Exception:
                        btn = tk.Button(conteneur, text=f[:8], bg=C_SURF, relief="flat", bd=0, command=lambda p=os.path.join(EMOJI_DIR, f): inserer(f"[img:{p}]"))
                        btn.grid(padx=2, pady=2)
        cats = list(EMOJIS.keys())
        if persos: cats.append("Perso")
        for cat in cats:
            btn_c = tk.Button(zone_categories, text=cat, font=(FONT, 10, "bold"), bg=C_SURF, fg=C_TEXT, relief="flat", bd=0, cursor="hand2", command=lambda c=cat: afficher_categorie(c))
            btn_c.pack(side="left", padx=2, pady=4)
        afficher_categorie(cats[0])

    def _importer_emoji(self):
        chemin = filedialog.askopenfilename(title="Importer un émoji / GIF", filetypes=[("Images", "*.png *.gif *.jpg *.jpeg *.webp *.bmp"), ("Tous", "*.*")])
        if not chemin: return
        os.makedirs(EMOJI_DIR, exist_ok=True)
        nom = os.path.basename(chemin)
        import shutil
        shutil.copy2(chemin, os.path.join(EMOJI_DIR, nom))
        self._toast("Importé", f"{nom} ajouté à tes émojis persos.")

    def _attacher_media(self):
        chemin = filedialog.askopenfilename(title="Attacher un média", filetypes=[("Médias", "*.png *.gif *.jpg *.jpeg *.mp4 *.webm *.mov *.mkv"), ("Tous", "*.*")])
        if not chemin: return
        if chemin.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
            self.entree.insert(tk.INSERT, f"[img:{chemin}] ")
        else:
            self.entree.insert(tk.INSERT, f"{chemin} ")
        self.entree.focus()

    def quitter(self):
        self.running = False
        try:
            if self.udp_sock: self.udp_sock.close()
            if self.tcp_server: self.tcp_server.close()
            if self.sock: self.sock.close()
            self.audio.arreter()
            if self.mode == "host":
                data = make_msg("sys", text=f"🔴 {self.pseudo} a quitté le salon")
                self._diffuser(data)
        except Exception: pass
        if self.compte:
            self.compte["derniere_session"] = time.strftime("%Y-%m-%d %H:%M")
            self.gc.sauver()
        self.root.destroy()


if __name__ == "__main__":
    app = LANchat()
    app.root.mainloop()