#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, socket, threading, queue, time, hashlib, logging, re

def _crash_log(msg):
    try:
        _d = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else os.getcwd()
        with open(os.path.join(_d, "lanchat_erreur.log"), "w", encoding="utf-8") as _f:
            _f.write(msg + "\n")
    except Exception:
        pass

def _alerter_demarrage(titre, msg):
    import platform as _pf, subprocess as _sp
    s = _pf.system()
    try:
        if s == "Windows":
            _sp.Popen(["msg", "*", titre + "\n\n" + msg])
        elif s == "Darwin":
            _sp.Popen(["osascript", "-e", 'display dialog "' + msg.replace('"', "'") + '" buttons {"OK"}'])
        elif _sp.run(["which", "zenity"], capture_output=True).returncode == 0:
            _sp.Popen(["zenity", "--error", "--title=" + titre, "--text=" + msg])
        elif _sp.run(["which", "xmessage"], capture_output=True).returncode == 0:
            _sp.Popen(["xmessage", titre + "\n\n" + msg])
    except Exception:
        pass

try:
    import urllib.request, webbrowser, platform, subprocess, tkinter as tk
    import base64
    from tkinter import ttk, messagebox, simpledialog, filedialog
except Exception as _e:
    import traceback
    _tb = traceback.format_exc()
    _crash_log(_tb)
    sys.stderr.write(_tb)
    _msg = ("Une bibliotheque requise est introuvable (probablement tkinter).\n\n"
            "Sur Linux Mint, installe-la avec :\n    sudo apt install python3-tk\n\n"
            "Sur Windows, reinstalle Python depuis python.org en cochant 'tcl/tk'.\n\n")
    _msg += ("Detail : " + str(_e)) if "tkinter" in str(_e).lower() else _tb
    _alerter_demarrage("LANchat Pro - Erreur de demarrage", _msg)
    sys.exit(1)

try:
    import pyaudio
    AUDIO_OK = True
except Exception:
    AUDIO_OK = False

APP_NAME = "LANchat Pro"
VERSION = "V.1.0.9.0"
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
SPINNER = ["â ","â ","â ¹","â ¸","â ¼","â ´","â ¦","â §","â ","â "]
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
    "Smileys": ["ð","ð","ð¥°","ð","ð¤","ð´","ð­","ð¡","ð¤¯","ð¥³","ð±","ð¤","ð¤©","ð","ð¤","ð","ð","ð","ð¤ª","ð¥º","ð¤","ð¥¶","ð¤","ð¤§"],
    "Gestes": ["ð","ð","ð","ð","ðª","âï¸","ð¤","ð¤","â","ð","ð«¶","ð","ð¤","ð¤","ð","ð","ð«°","ð¤","ð«²","ð«±","ð","ð¤","ðï¸","âï¸"],
    "CÅur": ["â¤ï¸","ð§¡","ð","ð","ð","ð","ð¤","ð¤","ð","ð","ð","ð","â£ï¸","ð","ð","ð","â¥ï¸","ð«¶","ð","ð"],
    "Objets": ["ð¥","â­","â¨","ð","ð","ð","ð","ð","ð°","ð¯","ð¡","ðµ","ð®","ð±","ð»","â","ð¥ï¸","â¨ï¸","ð±ï¸","ð","ð","ð","ð","ð"],
    "Nature": ["ð","âï¸","ð","â¡","âï¸","ð","ð¸","ð","ð","ð»","ð¶","ð±","ð¦","ð","ð¥","ð","ðï¸","ð","ð","ð ","ð³","ðº","ð","âï¸"],
    "Nourriture": ["ð","ð","ð","ð®","ð©","ð","ð","ð","ð¥","ð¿","ð«","ð¥¤","ð£","ð","ðª","ð","ð§","ð°","ð¥","ð§","ð¬","ð¥¨","ð§","ð"],
    "Drapeaux": ["ð«ð·","ð¬ð§","ðºð¸","ðªð¸","ð®ð¹","ð©ðª","ð¯ðµ","ð¨ð¦","ð§ðª","ð¨ð­","ðµð¹","ð²ð¦","ð¸ð³","ð§ð·","ð²ð½","ð®ð³","ð¨ð³","ð°ð·","ð¦ðº","ð·ðº","ð","ð´","ð³ï¸","ð"],
    "ActivitÃ©s": ["â½","ð","ð®","ð§","ð¨","ð¸","ð¬","ð¸","ð¤","ð¹","ð¥","ð²","ð³","ð¯","âï¸","ð","ð¥","ð¸","ð","ð","ð´","â·ï¸","ð","ð¤¸"],
    "Symboles": ["ð¯","â","â","â­","â","â","ð¢","ð¥","ð«","ð¦","ð¨","ð","ð","ð","ð¢","ð¬","ð¤","â»ï¸","â´ï¸","ð","ð","ð","ð","ð"],
    "Animaux": ["ð¶","ð±","ð­","ð¹","ð°","ð¦","ð»","ð¼","ð¨","ð¦","ð¯","ð¦","ð","ð¦","ð","ð¦","ð¢","ð¬","ð¦","ð¦","ð","ð","ð¦","ð "],
    "Tech": ["ð»","â¨ï¸","ð¥ï¸","ð¨ï¸","ð±ï¸","ð¿","ð¾","ð±","ð","ð¡","ð","ð","ð¡","ð§","âï¸","ð§°","ð ï¸","ð¡","ð·","ð¥","ð¹ï¸","ðï¸","ð§®","ð"],
    "Divers": ["ðª","ð­","ð¨","ð¬","ð¤","ð§","ð¼","ð¹","ð¥","ð·","ðº","ð¸","ðª","ð»","ð²","ð¯","ð³","ð°","ð","ð","âï¸","ð­","ðï¸","ð«"],
    "FÃªtes": ["ð","ð","ð","ð","ð","ð","ðï¸","ð¾","ð¥","ð","ð","â¨","ð","ð","ð®","ð","ð","ð","ð","ð","ð","ð","ð","ð"],
    "MÃ©tÃ©o": ["âï¸","ð¤ï¸","â","ð¥ï¸","âï¸","ð¦ï¸","ð§ï¸","âï¸","ð©ï¸","ð¨ï¸","âï¸","ð¬ï¸","ð¨","ðªï¸","ð«ï¸","ð","â","ð§","ð","ð¥","ð¡ï¸","ð","â¡","â"],
    "Transports": ["ð","ð","ð","ð","ð","ðï¸","ð","ð","ð","ð","ð","ð","ð","ðï¸","ðµ","âï¸","ð","ð¸","ð","âµ","ð¤","ð","ð","ð"],
    "Voyages": ["ðï¸","ð","ðï¸","ðï¸","ðï¸","ð³","ðï¸","âº","ð°","ð¯","ð¼","ð½","ð¿","â©ï¸","ð","ð","âª","ðºï¸","ð§­","ð","ð","ð","ð","ð"],
    "Sport": ["â½","ð","ð","â¾","ð¥","ð¾","ð","ð","ð¥","ð±","ð","ð¸","ð¥","ð¥","â³","ðï¸","ð","ð´","ðµ","ð","ð¥","ð¥","ð¥","ð"],
    "Zodiaque": ["â","â","â","â","â","â","â","â","â","â","â","â","â","ð®","ð","â­","â¨","ð«","ð","âï¸","â¡","âï¸","ð¥","ð§"],
    "Nourriture+": ["ð","ð¥","ð²","ð","ð¤","ð¥","ð±","ð","ð","ð","ð¢","ð¡","ð§","ð¨","ð¥§","ð§","ð¥","ð§","ð§","ð¥«","ð§","ð","ð","ð¥©"],
    "Boissons": ["â","ðµ","ð¥¤","ð§","ð§","ð§","ð·","ðº","ð»","ð¥","ð¸","ð¹","ð¾","ð¥","ð§","ð¶","ð°","ð§","ð¥¤","ðµ","ð·","ðº","ð§","ð¹"],
    "Jeux": ["ð®","ð¹ï¸","ð¾","ð²","ð","ð","âï¸","ð¯","ð³","ð°","ð§©","ðª","ðª","ðª","ð°","ð","âï¸","ð¯","ð®","ð¹ï¸","ð¾","ð²","ð§©","ðª"],
    "Maison": ["ð ","ð¡","ð ","ðï¸","ðï¸","ðï¸","ð­","ð¢","ð¬","ð£","ð¤","ð¥","ð¦","ð¨","ðª","ð«","ð©","ð","ðï¸","âª","ð","ð","â©ï¸","ð"],
    "SantÃ©": ["ð¥","ð","ð","ð©¹","ð©º","ð§¬","ð¦ ","ð§ª","ð¬","ð©»","ð","ð","ð¥","ð§","ð","ðª","ð§´","ð§¼","ð¦·","ð©¸","ð¡ï¸","ð§","ð¤","ð¤"],
    "VÃªtements": ["ð","ð","ð","ð","ð","ð©±","ð§¥","ð¥¼","ð¦º","ð§¦","ð§¤","ð§£","ð©","ð§¢","ð","ð","âï¸","ðª","ð","ð","ð","ð","ð","ð"],
    "Personnages": ["ð§","ð©","ð¨","ð§","ð§","ð¦","ð¶","ðµ","ð´","ð§","ð§","ð±","ð®","ðµï¸","ð","ð¥·","ð§âð","ð¤´","ð¸","ð¦¸","ð¦¹","ð§","ð§","ð§"],
    "Drapeaux+": ["ð³ï¸","ð´","ð´ââ ï¸","ð","ð©","ð³ï¸âð","ð³ï¸ââ§ï¸","ðªðº","ðºð³","ð«ð·","ð§ðª","ð¨ð­","ð¨ð¦","ð²ð¦","ð©ð¿","ð¹ð³","ð¸ð³","ð¨ð®","ð²ð±","ð³ðª","ð¹ð¬","ð§ð¯","ð¬ð¦","ð¿ð¦"],
    "Temps": ["ð","ð","ð","ð","ð","ð","ð","ð","ð","ð","ð","ð","â°","â±ï¸","â²ï¸","ð°ï¸","â³","â","ð","ð","ðï¸","ð","âï¸","ð"],
    "Argent": ["ð°","ð´","ðµ","ð¶","ð·","ðª","ð¸","ð³","ð§¾","ð¹","ð¦","ð","ð","ð","ð±","ð²","ðª","ð°","ð","ð·ï¸","ð","ð¦","ð","ð"],
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
    "vert":{"nom":"Vert Ãmeraude","hex":"#a6e3a1","prix":0},
    "rouge":{"nom":"Rouge Lave","hex":"#f38ba8","prix":50},
    "violet":{"nom":"Violet NÃ©on","hex":"#cba6f7","prix":80},
    "or":{"nom":"Or Royal","hex":"#f9e2af","prix":150},
    "cyan":{"nom":"Cyan OcÃ©an","hex":"#94e2d5","prix":100},
    "rose":{"nom":"Rose Bonbon","hex":"#f5c2e7","prix":120},
    "lavande":{"nom":"Lavande","hex":"#b4befe","prix":90},
    "corail":{"nom":"Corail Sunset","hex":"#eba0ac","prix":110},
    "menthol":{"nom":"Menthol","hex":"#a6d189","prix":110},
    "galaxy":{"nom":"Galaxy (animÃ©)","hex":"#cba6f7","prix":250,"anime":True},
    "feu":{"nom":"Feu (animÃ©)","hex":"#f38ba8","prix":250,"anime":True},
    "arc":{"nom":"Arc-en-ciel (animÃ©)","hex":"#89b4fa","prix":400,"anime":True},
}

BADGES = {
    "aucun":{"nom":"Aucun","emoji":"","prix":0},
    "etoile":{"nom":"Ãtoile","emoji":"â­","prix":0},
    "feu":{"nom":"On Fire","emoji":"ð¥","prix":50},
    "rico":{"nom":"Riche","emoji":"ð","prix":150},
    "vip":{"nom":"VIP","emoji":"ð","prix":120},
    "roi":{"nom":"LÃ©gende","emoji":"ð","prix":200},
    "coeur":{"nom":"CÅur d'or","emoji":"ð","prix":180},
    "foudre":{"nom":"Foudre","emoji":"â¡","prix":160},
    "trophy":{"nom":"Champion","emoji":"ð","prix":300},
    "dragon":{"nom":"Dragon","emoji":"ð","prix":500},
    "galaxie":{"nom":"Galaxie","emoji":"ð","prix":450},
    "crystal":{"nom":"Crystal","emoji":"ð®","prix":350},
    "ninja":{"nom":"Ninja","emoji":"ð¥·","prix":280},
    "robot":{"nom":"Robot","emoji":"ð¤","prix":320},
    "arc_en_ciel":{"nom":"Arc-en-ciel","emoji":"ð","prix":550},
}

TITRES = {
    "membre":{"nom":"Membre","prix":0},
    "newbie":{"nom":"Petit Nouveau","prix":0},
    "bavard":{"nom":"Bavard","prix":60},
    "sociable":{"nom":"Sociable","prix":90},
    "veteran":{"nom":"VÃ©tÃ©ran","prix":120},
    "pro":{"nom":"Pro du rÃ©seau","prix":180},
    "star":{"nom":"Star du salon","prix":250},
    "influent":{"nom":"Influent","prix":300},
    "mythe":{"nom":"Mythe vivant","prix":500},
    "boss":{"nom":"Boss du LAN","prix":600},
    "legende":{"nom":"LÃ©gende Ãternelle","prix":800},
    "gamer":{"nom":"Gamer Pro","prix":220},
    "createur":{"nom":"CrÃ©ateur","prix":350},
    "flamme":{"nom":"Flamme Ãternelle","prix":700},
}

COULEURS_DEFAUT = "bleu"; BADGE_DEFAUT = "etoile"; TITRE_DEFAUT = "membre"

AVATARS_PREF = {
    "defaut": {"emoji":"\U0001F9D1", "nom":"D\u00e9faut", "prix":0},
    "ninja": {"emoji":"\U0001F977", "nom":"Ninja", "prix":80},
    "robot": {"emoji":"\U0001F916", "nom":"Robot", "prix":80},
    "alien": {"emoji":"\U0001F47D", "nom":"Alien", "prix":120},
    "fantome": {"emoji":"\U0001F47B", "nom":"Fant\u00f4me", "prix":100},
    "diable": {"emoji":"\U0001F608", "nom":"Diable", "prix":150},
    "ange": {"emoji":"\U0001F607", "nom":"Ange", "prix":150},
    "roi": {"emoji":"\U0001F934", "nom":"Roi", "prix":200},
    "magicien": {"emoji":"\U0001F9D9", "nom":"Magicien", "prix":180},
    "fee": {"emoji":"\U0001F9DA", "nom":"F\u00e9e", "prix":180},
    "vampire": {"emoji":"\U0001F9DB", "nom":"Vampire", "prix":200},
    "zombie": {"emoji":"\U0001F9DF", "nom":"Zombie", "prix":160},
    "dragon": {"emoji":"\U0001F409", "nom":"Dragon", "prix":350},
    "licorne": {"emoji":"\U0001F984", "nom":"Licorne", "prix":300},
    "chat": {"emoji":"\U0001F431", "nom":"Chat", "prix":60},
    "chien": {"emoji":"\U0001F436", "nom":"Chien", "prix":60},
    "renard": {"emoji":"\U0001F98A", "nom":"Renard", "prix":100},
    "panda": {"emoji":"\U0001F43C", "nom":"Panda", "prix":120},
    "frog": {"emoji":"\U0001F438", "nom":"Frog", "prix":90},
    "singe": {"emoji":"\U0001F435", "nom":"Singe", "prix":90},
}
AVATAR_DEFAUT = "defaut"

CADRES = {
    "aucun": {"nom":"Aucun", "symbole":"", "prix":0},
    "simple": {"nom":"Simple", "symbole":"\u25AC", "prix":0},
    "etoile": {"nom":"\u00c9toil\u00e9", "symbole":"\u272A", "prix":50},
    "couronne": {"nom":"Couronne", "symbole":"\u265B", "prix":120},
    "fleur": {"nom":"Fleur", "symbole":"\u2740", "prix":80},
    "foudre": {"nom":"Foudre", "symbole":"\u26A1", "prix":100},
    "coeur": {"nom":"C\u0153ur", "symbole":"\u2665", "prix":80},
    "diamant": {"nom":"Diamant", "symbole":"\u25C6", "prix":150},
    "flamme": {"nom":"Flamme", "symbole":"\U0001F525", "prix":130},
    "galaxie": {"nom":"Galaxie", "symbole":"\u2726", "prix":250},
}
CADRE_DEFAUT = "simple"

FONDS_PROFIL = {
    "defaut": {"nom":"D\u00e9faut", "couleur":None, "prix":0},
    "bleu": {"nom":"Bleu Glacier", "couleur":"#1e1e2e", "prix":0},
    "violet": {"nom":"Violet Nuit", "couleur":"#2a1e3e", "prix":60},
    "vert": {"nom":"Vert For\u00eat", "couleur":"#1e2e1e", "prix":60},
    "rouge": {"nom":"Rouge Lave", "couleur":"#2e1e1e", "prix":80},
    "or": {"nom":"Or Royal", "couleur":"#2e2a1e", "prix":120},
    "arc": {"nom":"Arc-en-ciel", "couleur":"rainbow", "prix":250},
    "galaxy": {"nom":"Galaxy", "couleur":"galaxy", "prix":300},
}
FOND_DEFAUT = "defaut"

def couleur_hex(cid): return COULEURS.get(cid, COULEURS[COULEURS_DEFAUT])["hex"]
def couleur_anime(cid): return COULEURS.get(cid, {}).get("anime", False)
def badge_emoji(bid): return BADGES.get(bid, BADGES[BADGE_DEFAUT])["emoji"]
def titre_nom(tid): return TITRES.get(tid, TITRES[TITRE_DEFAUT])["nom"]
def avatar_emoji(aid): return AVATARS_PREF.get(aid, AVATARS_PREF[AVATAR_DEFAUT])["emoji"]
def cadre_symbole(cid): return CADRES.get(cid, CADRES[CADRE_DEFAUT])["symbole"]

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
    {"nom":"gÃ©nÃ©ral","type":"texte","desc":"Discussion gÃ©nÃ©rale"},
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
        if pseudo in self.comptes: return False, "Ce pseudo existe dÃ©jÃ ."
        if not pseudo or len(pseudo) > MAX_PSEUDO: return False, f"Pseudo invalide (1 Ã  {MAX_PSEUDO} car.)."
        if not mdp or len(mdp) < 3: return False, "Mot de passe trop court (3 car. min)."
        salt = os.urandom(16).hex()
        self.comptes[pseudo] = {"salt":salt, "hash":self._hash(mdp, salt), "coins":150, "xp":0,
            "msgs":0, "appels":0, "derniere_session":time.strftime("%Y-%m-%d %H:%M"),
            "possedes":{"couleurs":["bleu","vert"], "badges":["aucun","etoile"], "titres":["membre","newbie"]},
            "equip":{"couleur":"bleu", "badge":"etoile", "titre":"membre"},
            "sonnerie":"", "notif":"", "bio":"", "liens":[], "theme":"sombre",
            "avatar_emoji":"ð§", "couleur_pseudo":"bleu", "amis":[], "avatar_pref":AVATAR_DEFAUT, "cadre":CADRE_DEFAUT, "fond":"defaut", "possedes_avatars":[AVATAR_DEFAUT], "possedes_cadres":[CADRE_DEFAUT], "possedes_fonds":["defaut"]}
        self._sauver(); return True, "Compte crÃ©Ã© ! 150 coins de bienvenue ð"
    def verifier(self, pseudo, mdp):
        c = self.comptes.get(pseudo)
        if not c: return False, "Compte introuvable."
        return (self._hash(mdp, c["salt"]) == c["hash"]), "ok"
    def supprimer(self, pseudo, mdp):
        c = self.comptes.get(pseudo)
        if not c: return False, "Compte introuvable."
        if self._hash(mdp, c["salt"]) != c["hash"]: return False, "Mot de passe incorrect."
        del self.comptes[pseudo]; self._sauver(); return True, "Compte supprimÃ©."
    def get(self, p): return self.comptes.get(p)
    def sauver(self): self._sauver()

def profil_public(c):
    niv, _ = niveau_from_xp(c["xp"])
    return {"pseudo":None, "niveau":niv, "xp":c["xp"], "coins":c["coins"], "msgs":c["msgs"],
            "appels":c["appels"], "couleur":c["equip"]["couleur"], "badge":c["equip"]["badge"],
            "titre":c["equip"]["titre"], "bio":c.get("bio",""), "liens":c.get("liens",[]),
            "avatar":c.get("avatar_emoji","ð§"),
            "avatar_pref":c.get("avatar_pref",AVATAR_DEFAUT),
            "cadre":c.get("cadre",CADRE_DEFAUT), "fond":c.get("fond","defaut")}

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

RAINBOW = ["#f38ba8","#fab387","#f9e2af","#a6e3a1","#94e2d5","#89b4fa","#cba6f7"]
GRADIENT_OCEAN = ["#0f0f23","#1a1a3e","#11111b","#181825","#1e1e2e"]
GRADIENT_SUNSET = ["#f38ba8","#fab387","#f9e2af","#cba6f7","#89b4fa"]
GRADIENT_NEON = ["#89b4fa","#b4befe","#cba6f7","#f5c2e7","#f38ba8","#fab387","#f9e2af","#a6e3a1","#94e2d5","#89b4fa"]
GRADIENT_AURORA = ["#94e2d5","#89b4fa","#cba6f7","#f5c2e7","#fab387","#94e2d5"]
GRADIENT_COSMOS = ["#1e1e2e","#313244","#45475a","#1e1e2e","#181825","#1e1e2e"]
SPARKLES = ["\u2726","\u2727","\u2736","\u2740","\u272A",""]

def hex_to_rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def rgb_to_hex(r, g, b): return f"#{r:02x}{g:02x}{b:02x}"

def _gradient_hex(c1, c2, steps=20):
    r1,g1,b1 = hex_to_rgb(c1); r2,g2,b2 = hex_to_rgb(c2)
    out = []
    for i in range(steps):
        t = i / max(1, steps-1)
        te = 0.5 - 0.5 * (1 - t) ** 2
        out.append(rgb_to_hex(int(r1+(r2-r1)*te), int(g1+(g2-g1)*te), int(b1+(b2-b1)*te)))
    return out

def _multi_gradient_hex(colors, steps=60):
    if len(colors) < 2: return colors * steps
    out = []
    seg = max(2, steps // max(1, len(colors)-1))
    for i in range(len(colors)-1):
        out.extend(_gradient_hex(colors[i], colors[i+1], seg if i < len(colors)-2 else seg + steps - seg*(len(colors)-1)))
    return out[:steps]

def _ease(t):
    return 0.5 - 0.5 * (1 - t) ** 2

def _shift_gradient(colors, offset):
    n = len(colors)
    return [colors[(i + offset) % n] for i in range(n)]

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
        self.salon_courant = "gÃ©nÃ©ral"
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
        e.config(font=(FONT, 13), bg=C_INP, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", bd=0,
                 highlightbackground=C_DIM, highlightthickness=1, highlightcolor=C_BLUE)
        def on_focus_in(ev):
            e.config(highlightbackground=C_BLUE, highlightthickness=2)
        def on_focus_out(ev):
            e.config(highlightbackground=C_DIM, highlightthickness=1)
        e.bind("<FocusIn>", on_focus_in)
        e.bind("<FocusOut>", on_focus_out)

    def _btn_styler(self, b, bg=C_BLUE, fg=C_BG):
        b.config(font=(FONT, 11, "bold"), bg=bg, fg=fg, relief="flat", cursor="hand2",
                 activebackground=self._lighten(bg, 0.25), activeforeground=fg, bd=0,
                 padx=14, pady=7)
        orig_bg = bg
        def on_enter(e):
            b.config(bg=self._lighten(bg, 0.28), relief="flat")
        def on_leave(e):
            b.config(bg=orig_bg)
        def on_press(e):
            b.config(bg=self._darken(bg, 0.15), relief="sunken")
        def on_release(e):
            b.config(bg=self._lighten(bg, 0.28), relief="flat")
        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)
        b.bind("<ButtonPress-1>", on_press)
        b.bind("<ButtonRelease-1>", on_release)

    def _lighten(self, hexcol, t=0.15):
        r, g, b = hex_to_rgb(hexcol)
        return rgb_to_hex(min(255, int(r+(255-r)*t)), min(255, int(g+(255-g)*t)), min(255, int(b+(255-b)*t)))

    def _darken(self, hexcol, t=0.15):
        r, g, b = hex_to_rgb(hexcol)
        return rgb_to_hex(max(0, int(r*(1-t))), max(0, int(g*(1-t))), max(0, int(b*(1-t))))

    def _cadre_arrondi(self, parent, bg=None, radius=12, padx=1, pady=1, **kw):
        bg = bg or C_SURF2
        canvas = tk.Canvas(parent, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=bg)
        def _place():
            if not canvas.winfo_exists(): return
            w = canvas.winfo_width(); h = canvas.winfo_height()
            if w < 2 or h < 2: canvas.after(50, _place); return
            canvas.delete("rr")
            canvas.create_polygon(
                radius, 0, w - radius, 0, w, radius, w, h - radius,
                w - radius, h, radius, h, 0, h - radius, 0, radius,
                smooth=True, fill=bg, outline=self._lighten(bg, 0.15), width=1, tags="rr")
            canvas.create_window(w // 2, h // 2, window=inner, anchor="center",
                                 width=w - padx * 2, height=h - pady * 2)
        canvas.after(50, _place)
        canvas._inner = inner
        canvas._redraw = _place
        return inner

    def _titre_anime(self, parent, texte, couleur=C_BLUE, font_size=24):
        lbl = tk.Label(parent, text=texte, font=(FONT, font_size, "bold"), fg=couleur, bg=C_BG)
        lbl.pack()
        try:
            palette = _multi_gradient_hex([couleur, self._lighten(couleur, 0.5), self._lighten(couleur, 0.2), couleur], 60)
            idx = [0]
            def anim():
                if lbl.winfo_exists():
                    lbl.config(fg=palette[idx[0] % len(palette)])
                    idx[0] = (idx[0] + 1) % len(palette)
                    self.root.after(90, anim)
            anim()
        except Exception:
            log.warning("titre anime indisponible")
        return lbl

    def _fond_anime(self, parent, height=80):
        canvas = tk.Canvas(parent, height=height, highlightthickness=0, bd=0)
        canvas.pack(fill="x")
        try:
            base = _multi_gradient_hex(GRADIENT_NEON, 180)
            strips = []; n_strips = 180; offset = [0]; initialized = [False]
            def init_strips():
                w = canvas.winfo_width() or 600
                sw = max(1, w / n_strips)
                canvas.delete("fond")
                strips.clear()
                for i in range(n_strips + 2):
                    x = i * sw
                    c = base[(offset[0] + i) % len(base)]
                    rid = canvas.create_rectangle(x, 0, x + sw + 1, height, fill=c, outline="", tags="fond")
                    strips.append(rid)
                initialized[0] = True
            def anim():
                if not canvas.winfo_exists(): return
                if not initialized[0]: init_strips()
                for i, rid in enumerate(strips):
                    c = base[(offset[0] + i) % len(base)]
                    canvas.itemconfig(rid, fill=c)
                offset[0] = (offset[0] + 1) % len(base)
                self.root.after(80, anim)
            canvas.after(100, anim)
        except Exception:
            log.warning("fond anime indisponible")
            canvas.config(bg=C_BG2)
        return canvas

    def _fond_gradient(self, parent, height=60):
        canvas = tk.Canvas(parent, height=height, highlightthickness=0, bd=0)
        canvas.pack(fill="x")
        try:
            strips = []; n_strips = 120; offset = [0]; initialized = [False]
            def init_strips():
                w = canvas.winfo_width() or 400
                sw = max(1, w / n_strips)
                canvas.delete("grad")
                strips.clear()
                base = _multi_gradient_hex([C_GRAD1, self._lighten(C_GRAD1, 0.25), C_GRAD2, C_GRAD1], 120)
                for i in range(n_strips + 2):
                    x = i * sw
                    c = base[(offset[0] + i) % len(base)]
                    rid = canvas.create_rectangle(x, 0, x + sw + 1, height, fill=c, outline="", tags="grad")
                    strips.append(rid)
                initialized[0] = True
            def dessiner():
                if not canvas.winfo_exists(): return
                if not initialized[0]: init_strips()
                base = _multi_gradient_hex([C_GRAD1, self._lighten(C_GRAD1, 0.25), C_GRAD2, C_GRAD1], 120)
                for i, rid in enumerate(strips):
                    c = base[(offset[0] + i) % len(base)]
                    canvas.itemconfig(rid, fill=c)
                offset[0] = (offset[0] + 1) % len(base)
                self.root.after(90, dessiner)
            canvas.after(100, dessiner)
        except Exception:
            log.warning("fond gradient indisponible")
            canvas.config(bg=C_GRAD1)
        return canvas

    def _particules(self, parent, count=12, height=200):
        canvas = tk.Canvas(parent, height=height, highlightthickness=0, bd=0)
        canvas.pack(fill="x")
        try:
            import random as _r
            cols = [C_BLUE, C_PURPLE, C_PINK, C_TEAL, C_YELLOW, C_GREEN]
            particules = []
            for _ in range(count):
                x = _r.randint(0, 400); y = _r.randint(0, height)
                vy = -_r.uniform(0.2, 0.8); vx = _r.uniform(-0.2, 0.2)
                col = _r.choice(cols)
                r = _r.choice([3, 4, 5, 6, 7])
                phase = _r.uniform(0, 6.28)
                is_circle = _r.random() < 0.6
                sym = "" if is_circle else _r.choice(SPARKLES)
                particules.append({"x":x, "y":y, "vy":vy, "vx":vx, "col":col, "r":r, "phase":phase, "sym":sym})
            def anim():
                if not canvas.winfo_exists(): return
                canvas.delete("p")
                t = time.time()
                for p in particules:
                    p["y"] += p["vy"]; p["x"] += p["vx"]
                    if p["y"] < -20:
                        p["y"] = height + 10; p["x"] = _r.randint(0, canvas.winfo_width() or 400)
                    phase_t = (t * 2 + p["phase"]) % 6.28
                    pulse = 0.75 + 0.25 * (phase_t / 3.14)
                    rr = p["r"] * pulse
                    glow_c = self._lighten(p["col"], 0.6)
                    if p["sym"]:
                        canvas.create_text(p["x"], p["y"], text=p["sym"], fill=p["col"],
                            font=(FONT, int(rr * 2)), tags="p")
                    else:
                        canvas.create_oval(p["x"]-rr*2.5, p["y"]-rr*2.5, p["x"]+rr*2.5, p["y"]+rr*2.5,
                            fill=glow_c, outline="", tags="p")
                        canvas.create_oval(p["x"]-rr, p["y"]-rr, p["x"]+rr, p["y"]+rr,
                            fill=p["col"], outline="", tags="p")
                self.root.after(50, anim)
            anim()
        except Exception:
            log.warning("particules indisponibles")
        return canvas

    def _ecran_auth(self):
        self._reset_frame()
        f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=70)
        self._titre_anime(f, f"\U0001f4ac {APP_NAME}", C_BLUE, 22)
        tk.Label(f, text=VERSION, font=(FONT, 10, "bold"), fg=C_YELLOW, bg=C_BG).pack(pady=(0, 2))
        tk.Label(f, text="Compte local s\u00e9curis\u00e9", font=(FONT, 11), fg=C_SUB, bg=C_BG).pack(pady=(0, 16))
        cadre = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
        cadre.pack(padx=40, pady=8, fill="x")
        self._auth_var = tk.StringVar(value="login")
        def toggle():
            if self._auth_var.get() == "login":
                self.btn_valider.config(text="Se connecter", bg=C_BLUE)
                self.lbl_mdp2.pack_forget(); self.ent_mdp2.pack_forget()
            else:
                self.btn_valider.config(text="CrÃ©er le compte", bg=C_GREEN)
                self.lbl_mdp2.pack(anchor="w", padx=16, pady=(8, 0)); self.ent_mdp2.pack(padx=16, pady=4, fill="x")
        top = tk.Frame(cadre, bg=C_SURF2); top.pack(fill="x", padx=16, pady=(14, 4))
        tk.Radiobutton(top, text="Connexion", variable=self._auth_var, value="login", command=toggle,
            bg=C_SURF2, fg=C_TEXT, selectcolor=C_SURF2, activebackground=C_SURF2, activeforeground=C_TEXT,
            font=(FONT, 10)).pack(side="left")
        tk.Radiobutton(top, text="CrÃ©er un compte", variable=self._auth_var, value="creer", command=toggle,
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
        self.ent_mdp = tk.Entry(cadre, show="â¢"); self._entree_styler(self.ent_mdp)
        self.ent_mdp.pack(padx=16, pady=4, fill="x")
        self.lbl_mdp2 = tk.Label(cadre, text="Confirmer le mot de passe", font=(FONT, 10), fg=C_SUB, bg=C_SURF2)
        self.ent_mdp2 = tk.Entry(cadre, show="â¢"); self._entree_styler(self.ent_mdp2)
        self.btn_valider = tk.Button(cadre, text="Se connecter", command=self._valider_auth)
        self._btn_styler(self.btn_valider, C_BLUE); self.btn_valider.pack(padx=16, pady=14, fill="x")
        self.ent_mdp.bind("<Return>", lambda e: self._valider_auth()); self.ent_pseudo_auth.focus()
        ligne_bas_auth = tk.Frame(cadre, bg=C_SURF2); ligne_bas_auth.pack(fill="x", padx=16, pady=(0, 12))
        btn_suppr = tk.Button(ligne_bas_auth, text="ðï¸ Supprimer un compte", command=self._supprimer_compte)
        self._btn_styler(btn_suppr, C_RED, C_BG); btn_suppr.pack(fill="x", ipady=3)
        tk.Label(f, text=f"ð Identifiants stockÃ©s localement dans {COMPTE_FILE} (jamais sur le rÃ©seau)",
            font=(FONT, 9), fg=C_DIM, bg=C_BG, wraplength=420, justify="center").pack(pady=(14, 0))

    def _supprimer_compte(self):
        pseudo = simpledialog.askstring("Supprimer un compte", "Pseudo Ã  supprimer :", parent=self.root)
        if not pseudo: return
        mdp = simpledialog.askstring("Supprimer un compte", f"Mot de passe de {pseudo} :", parent=self.root, show="â¢")
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
        if "avatar_emoji" not in self.compte: self.compte["avatar_emoji"] = "ð§"
        if "amis" not in self.compte: self.compte["amis"] = []
        if "avatar_pref" not in self.compte: self.compte["avatar_pref"] = AVATAR_DEFAUT
        if "cadre" not in self.compte: self.compte["cadre"] = CADRE_DEFAUT
        if "fond" not in self.compte: self.compte["fond"] = "defaut"
        if "possedes_avatars" not in self.compte: self.compte["possedes_avatars"] = [AVATAR_DEFAUT]
        if "possedes_cadres" not in self.compte: self.compte["possedes_cadres"] = [CADRE_DEFAUT]
        if "possedes_fonds" not in self.compte: self.compte["possedes_fonds"] = ["defaut"]
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
        self._particules(f, count=8, height=120)
        self._titre_anime(f, f"\U0001f4ac {APP_NAME}", C_BLUE, 20)
        tk.Label(f, text=VERSION, font=(FONT, 9, "bold"), fg=C_YELLOW, bg=C_BG).pack(pady=(0, 8))
        barre = tk.Frame(f, bg=C_SURF2); barre.pack(fill="x", padx=20, pady=(0, 8))
        badge = self.compte["equip"]["badge"]; niv, _ = niveau_from_xp(self.compte["xp"])
        avatar = self.compte.get("avatar_emoji", "ð§")
        tk.Label(barre, text=f"{avatar} {self.pseudo}  {badge_emoji(badge)}", font=(FONT, 11, "bold"),
            fg=couleur_hex(self.compte["equip"]["couleur"]), bg=C_SURF2).pack(side="left", padx=14, pady=8)
        self.lbl_compte = tk.Label(barre, text="", font=(FONT, 9), fg=C_SUB, bg=C_SURF2)
        self.lbl_compte.pack(side="right", padx=14, pady=8); self._rafraichir_compte_ui()
        cadre = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
        cadre.pack(padx=40, pady=8, fill="x")
        b1 = tk.Button(cadre, text="ð¥ï¸  HÃ©berger une discussion", command=self.demarrer_hote, height=2)
        self._btn_styler(b1, C_BLUE); b1.pack(padx=16, pady=(16, 6), fill="x")
        b2 = tk.Button(cadre, text="ð  Rejoindre (auto)", command=self.demarrer_rejoindre, height=2)
        self._btn_styler(b2, C_GREEN); b2.pack(padx=16, pady=6, fill="x")
        b3 = tk.Button(cadre, text="âï¸  Rejoindre par IP (dernier recours)", command=self.rejoindre_ip_manuel, height=2)
        self._btn_styler(b3, C_INP, C_TEXT); b3.pack(padx=16, pady=6, fill="x")
        b4 = tk.Button(cadre, text="ðï¸  Boutique & cosmÃ©tiques", command=self.ouvrir_boutique, height=2)
        self._btn_styler(b4, C_YELLOW, C_BG); b4.pack(padx=16, pady=(6, 6), fill="x")
        b_ami = tk.Button(cadre, text="ð¥  Mes amis", command=self.ouvrir_amis, height=2)
        self._btn_styler(b_ami, C_PINK); b_ami.pack(padx=16, pady=6, fill="x")
        ligne_bas = tk.Frame(f, bg=C_BG); ligne_bas.pack(fill="x", padx=40, pady=(0, 4))
        b5 = tk.Button(ligne_bas, text="âï¸  ParamÃ¨tres", command=self.ouvrir_parametres)
        self._btn_styler(b5, C_PURPLE); b5.pack(fill="x", ipady=4)
        b6 = tk.Button(ligne_bas, text="ð  Journal des nouveautÃ©s", command=self.ouvrir_journal)
        self._btn_styler(b6, C_INP, C_YELLOW); b6.pack(fill="x", ipady=4)
        b7 = tk.Button(ligne_bas, text="ðª  Changer de compte", command=self._deconnexion)
        self._btn_styler(b7, C_RED, C_BG); b7.pack(fill="x", ipady=4)
        tk.Label(f, text="Astuce : l'hÃ©bergeur lance le salon, les autres le rejoignent automatiquement.",
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
        txt = f"Lvl {niv}  â¢  {self.compte['coins']} ðª  â¢  {badge_emoji(self.compte['equip']['badge'])}  â¢  XP {self.compte['xp']} (+{restant} â niv.{niv+1})"
        if hasattr(self, "lbl_compte") and self.lbl_compte.winfo_exists(): self.lbl_compte.config(text=txt)

    def ouvrir_boutique(self):
        win = tk.Toplevel(self.root); win.title("ðï¸ Boutique"); win.geometry("540x640")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_anime(win, height=50)
        self.lbl_compte_bout = tk.Label(win, text="", font=(FONT, 11, "bold"), fg=C_YELLOW, bg=C_BG)
        self.lbl_compte_bout.pack(pady=8); self._rafraichir_boutique(win)
        nbook = ttk.Notebook(win); nbook.pack(fill="both", expand=True, padx=14, pady=6)
        style = ttk.Style(); style.configure("TNotebook", background=C_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=C_SURF2, foreground=C_TEXT, padding=12)
        style.map("TNotebook.Tab", background=[("selected", C_BLUE)], foreground=[("selected", C_BG)])
        for cat, catalogue, equip_key in [("ð¨ Couleurs", COULEURS, "couleur"), ("ð Badges", BADGES, "badge"), ("ð·ï¸ Titres", TITRES, "titre")]:
            page = tk.Frame(nbook, bg=C_BG); nbook.add(page, text=cat)
            self._remplir_boutique_page(page, catalogue, equip_key, win)
        for cat, catalogue, st in [("Avatars", AVATARS_PREF, "avatar"), ("Cadres", CADRES, "cadre"), ("Fonds", FONDS_PROFIL, "fond")]:
            page = tk.Frame(nbook, bg=C_BG); nbook.add(page, text=cat)
            self._remplir_boutique_skins(page, catalogue, st, win)

    def _rafraichir_boutique(self, win):
        niv, _ = niveau_from_xp(self.compte["xp"])
        self.lbl_compte_bout.config(text=f"{self.pseudo}  â¢  Niveau {niv}  â¢  {self.compte['coins']} ðª")

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
            if info.get("anime"): extra = " â¨"
            tk.Label(row, text=info["nom"] + extra, font=(FONT, 11, "bold"), fg=C_TEXT, bg=C_SURF2).pack(side="left", pady=8)
            tk.Label(row, text=f"{info['prix']} ðª", font=(FONT, 10), fg=C_GREEN, bg=C_SURF2).pack(side="left", padx=10)
            if cid == equipe: etat, bg = "â ÃquipÃ©", C_GREEN
            elif cid in possedes: etat, bg = "PossÃ©dÃ© â Ãquiper", C_BLUE
            else: etat, bg = f"Acheter {info['prix']}ðª", C_YELLOW
            b = tk.Button(row, text=etat, command=lambda c=cid, k=equip_key, w=win: self._action_cosmetique(c, k, w))
            self._btn_styler(b, bg if bg != C_YELLOW else C_YELLOW, C_BG if bg == C_YELLOW else C_BG)
            b.pack(side="right", padx=12, pady=8)

    def _apercu_cosmetique(self, key, cid):
        if key == "couleur": return "â"
        if key == "badge": return badge_emoji(cid) or "â"
        if key == "titre": return "ð·ï¸"
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
            messagebox.showwarning(APP_NAME, f"Pas assez de coins ({prix} ðª). Discute pour en gagner !"); return
        if not messagebox.askyesno(APP_NAME, f"Acheter pour {prix} ðª ?"): return
        self.compte["coins"] -= prix; self.compte["possedes"][poss_key].append(cid)
        self.compte["equip"][key] = cid; self.gc.sauver()
        self._rafraichir_boutique(win); self._rafraichir_compte_ui(); self._propager_profil()
        win.destroy(); self.ouvrir_boutique()

    def _remplir_boutique_skins(self, page, catalogue, skin_type, win):
        canvas = tk.Canvas(page, bg=C_BG, highlightthickness=0)
        scroll = tk.Scrollbar(page, command=canvas.yview); inner = tk.Frame(canvas, bg=C_BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window(0, 0, window=inner, anchor="nw"); canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        if skin_type == "avatar":
            possedes = self.compte.get("possedes_avatars", [AVATAR_DEFAUT])
            equipe = self.compte.get("avatar_pref", AVATAR_DEFAUT)
        elif skin_type == "cadre":
            possedes = self.compte.get("possedes_cadres", [CADRE_DEFAUT])
            equipe = self.compte.get("cadre", CADRE_DEFAUT)
        else:
            possedes = self.compte.get("possedes_fonds", ["defaut"])
            equipe = self.compte.get("fond", "defaut")
        for cid, info in catalogue.items():
            row = tk.Frame(inner, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
            row.pack(fill="x", padx=6, pady=5)
            if skin_type == "avatar": apercu = info.get("emoji", "")
            elif skin_type == "cadre": apercu = info.get("symbole", "") or "\u2014"
            else: apercu = "\U0001f3a8"
            tk.Label(row, text=apercu, font=(FONT, 18), bg=C_SURF2, fg=C_TEXT, width=6).pack(side="left", padx=10, pady=8)
            tk.Label(row, text=info["nom"], font=(FONT, 11, "bold"), fg=C_TEXT, bg=C_SURF2).pack(side="left", pady=8)
            tk.Label(row, text=f"{info.get('prix', 0)} \U0001fa99", font=(FONT, 10), fg=C_GREEN, bg=C_SURF2).pack(side="left", padx=10)
            if cid == equipe: etat, bg = "\u2705 \u00c9quip\u00e9", C_GREEN
            elif cid in possedes: etat, bg = "Poss\u00e9d\u00e9 \u2014 \u00c9quiper", C_BLUE
            else: etat, bg = f"Acheter {info.get('prix', 0)}\U0001fa99", C_YELLOW
            b = tk.Button(row, text=etat, command=lambda c=cid, st=skin_type, w=win: self._action_skin(c, st, w))
            self._btn_styler(b, bg, C_BG)
            b.pack(side="right", padx=12, pady=8)

    def _action_skin(self, cid, skin_type, win):
        if skin_type == "avatar":
            possedes = self.compte.get("possedes_avatars", [AVATAR_DEFAUT])
            field, poss_field = "avatar_pref", "possedes_avatars"
            cat = AVATARS_PREF
        elif skin_type == "cadre":
            possedes = self.compte.get("possedes_cadres", [CADRE_DEFAUT])
            field, poss_field = "cadre", "possedes_cadres"
            cat = CADRES
        else:
            possedes = self.compte.get("possedes_fonds", ["defaut"])
            field, poss_field = "fond", "possedes_fonds"
            cat = FONDS_PROFIL
        if cid == self.compte.get(field): return
        if cid in possedes:
            self.compte[field] = cid
            if skin_type == "avatar": self.compte["avatar_emoji"] = avatar_emoji(cid)
            self.gc.sauver(); self._propager_profil()
            win.destroy(); self.ouvrir_boutique(); return
        prix = cat.get(cid, {}).get("prix", 0)
        if self.compte["coins"] < prix:
            messagebox.showwarning(APP_NAME, f"Pas assez de coins ({prix} \U0001fa99)."); return
        if not messagebox.askyesno(APP_NAME, f"Acheter pour {prix} \U0001fa99 ?"): return
        self.compte["coins"] -= prix
        self.compte.setdefault(poss_field, []).append(cid)
        self.compte[field] = cid
        if skin_type == "avatar": self.compte["avatar_emoji"] = avatar_emoji(cid)
        self.gc.sauver(); self._propager_profil()
        win.destroy(); self.ouvrir_boutique()

    def ouvrir_journal(self):
        win = tk.Toplevel(self.root); win.title("Journal des nouveautÃ©s"); win.geometry("560x640")
        win.configure(bg=C_BG); win.transient(self.root)
        cadre_h = tk.Frame(win, bg=C_BG2); cadre_h.pack(fill="x")
        tk.Label(cadre_h, text="ð Journal des nouveautÃ©s", font=(FONT, 16, "bold"), fg=C_YELLOW, bg=C_BG2).pack(pady=(14, 2))
        tk.Label(cadre_h, text=f"{APP_NAME} â historique des versions", font=(FONT, 10), fg=C_DIM, bg=C_BG2).pack(pady=(0, 12))
        zone = tk.Text(win, font=(FONT, 11), bg=C_BG2, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", wrap="word", padx=16, pady=12)
        scroll = tk.Scrollbar(win, command=zone.yview); zone.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y"); zone.pack(fill="both", expand=True)
        versions = [
            ("V.1.0.9.0", "Correctif d\u00e9finitif du crash au d\u00e9marrage", [
                "CORRECTION CRITIQUE : accolade '}' superflue dans la cr\u00e9ation de compte (SyntaxError fatale)",
                "Cette erreur de syntaxe emp\u00eachait le module de compiler - crash silencieux \u00e0 chaque lancement",
                "V\u00e9rification de compilation compl\u00e8te du fichier r\u00e9ussie",
                "D\u00e9gradation gracieuse des animations (titre, fond, particules)",
                "Journal d'erreurs \u00e9crit dans lanchat_erreur.log \u00e0 chaque crash",
                "Dialogue d'erreur de d\u00e9marrage (zenity/msg) si tkinter est absent",
                "Compatibilit\u00e9 Linux Mint et Windows renforc\u00e9e",
            ]),
            ("V.1.0.8.1", "Correctifs de stabilitÃ©", [
                "Correction des f-strings imbriquÃ©s causant un crash au dÃ©marrage",
                "DÃ©claration d'encodage UTF-8 explicite ajoutÃ©e",
                "Gestion d'erreurs au dÃ©marrage avec affichage du traceback",
                "Retrait du paramÃ¨tre bg=parent[\"bg\"] sur les Canvas (compatibilitÃ©)",
                "D\u00e9gradation gracieuse des animations (titre, fond, particules) en cas d'erreur",
                "Journal d'erreurs : trace compl\u00e8te \u00e9crite dans lanchat_erreur.log \u00e0 chaque crash",
                "Dialogue d'erreur de d\u00e9marrage (zenity/msg) si tkinter est absent",
                "Compatibilit\u00e9 Linux Mint et Windows renforc\u00e9e au d\u00e9marrage",
                "Bip syst\u00e8me de secours multi-plateforme (aplay/paplay/winsound)",
            ]),
            ("V.1.0.8", "Skins, refonte visuelle & particules", [
                "20 avatars pr\u00e9fabriqu\u00e9s (ninja, robot, dragon, licorne, ange, vampire...)",
                "10 cadres d\u00e9coratifs (\u00e9toile, couronne, flamme, diamant, galaxie...)",
                "8 fonds de profil (bleu glacier, violet nuit, arc-en-ciel, galaxy...)",
                "Boutique \u00e9tendue : onglets Avatars, Cadres et Fonds achetables aux coins",
                "Refonte graphique : d\u00e9grad\u00e9s multi-couleurs fluides et anim\u00e9s",
                "D\u00e9grad\u00e9s lisses sans scintillement (bandes 1px pr\u00e9-cr\u00e9\u00e9es, itemconfig)",
                "Effet de particules lumineuses : cercles pulsants avec halo et \u00e9toiles",
                "Coins arrondis sur les bandeaux de d\u00e9grad\u00e9 (effet carte moderne)",
                "Palettes de d\u00e9grad\u00e9 enrichies : Neon, Aurora, Cosmos plus vibrantes",
                "Animations fluides : titre, barre de chat et pseudos en d\u00e9grad\u00e9 coul\u00e9",
                "Interpolation douce (easing) pour transitions de couleur naturelles",
                "Boutons am\u00e9lior\u00e9s : survol lumineux, effet de pression tactile",
                "Champs de saisie avec contour lumineux bleu au focus",
                "Horodatage des messages (HH:MM) pour un rendu plus moderne",
                "Espacement a\u00e9r\u00e9 des messages dans le salon",
                "Spinner de chargement avec d\u00e9grad\u00e9 continu multicolore",
                "Barre de XP avec effet de brillance anim\u00e9e",
                "Carte de profil : cadre et avatar affich\u00e9s en en-t\u00eate",
                "Profil public enrichi : avatar pr\u00e9fabriqu\u00e9, cadre et fond visibles",
            ]),
            ("V.1.0.7", "SÃ©curitÃ©, slots, amis & Ã©mojis", [
                "Quitter un salon textuel (bouton dÃ©diÃ© dans la liste des salons)",
                "9 slots de configuration serveur : sauvegarde et import de configs",
                "Ãcran de configuration serveur au lancement (rapide, personnalisÃ©e, import)",
                "CrÃ©ation de serveur personnalisÃ©e : nom, salons texte/vocal, descriptions",
                "Chiffrement des donnÃ©es de comptes (XOR + base85 + sel alÃ©atoire)",
                "Chiffrement des slots de configuration serveur",
                "Migration automatique des anciens comptes non chiffrÃ©s",
                "SystÃ¨me d'amis : ajouter/supprimer depuis le profil ou le menu",
                "Liste d'amis avec statut en ligne/hors ligne et accÃ¨s MP",
                "Bouton Amis dans le menu principal et la barre de chat",
                "SÃ©lecteur d'Ã©mojis refait : barre de dÃ©filement, molette, recherche globale",
                "CatÃ©gories d'Ã©mojis scrollables horizontalement (28 catÃ©gories)",
                "Plus d'Ã©mojis : 8 nouvelles catÃ©gories (Maison, SantÃ©, VÃªtements, Personnages, Drapeaux+, Temps, Argent)",
                "Total : 28 catÃ©gories d'Ã©mojis avec 24 Ã©mojis chacune (672 Ã©mojis !)",
                "Recherche d'Ã©mojis par mot-clÃ© dans toutes les catÃ©gories",
                "Notification rÃ©seau quand un membre quitte un salon",
                "Menu principal enrichi : bouton Amis ajoutÃ©",
            ]),
            ("V.1.0.6", "Salons, style & sons", [
                "Salons textuels multiples (gÃ©nÃ©ral, annonces, blabla) avec commutation",
                "Salon vocal dÃ©diÃ© avec connexion/dÃ©connexion audio",
                "CrÃ©ation de nouveaux salons personnalisÃ©s par l'hÃ´te",
                "SystÃ¨me de comptes amÃ©liorÃ© : boutons de sÃ©lection rapide, suppression de compte",
                "Validation des mots de passe (3 caractÃ¨res minimum)",
                "Avatar Ã©moji personnalisable par compte",
                "Bouton 'Changer de compte' sur l'Ã©cran d'accueil",
                "Plus d'Ã©mojis : 12 catÃ©gories avec 24 Ã©mojis chacune (+ catÃ©gories Tech et Divers)",
                "10 sons prÃ©chargÃ©s au lieu de 5 (ajout de sons pour envoi, connexion, erreur)",
                "Sons d'envoi et de connexion personnalisables",
                "AmÃ©lioration du style : dÃ©gradÃ©s, textures, animations fluides",
                "RÃ©paration dÃ©finitive du bug de corruption UTF-8 (accents)",
            ]),
            ("V.1.0.5", "Correction critique & nouvelles fonctionnalitÃ©s", [
                "Correction du bug de corruption UTF-8 (les accents s'affichaient mal)",
                "Sons personnalisÃ©s pour la sonnerie et les notifications",
                "Panneau ParamÃ¨tres avec 3 onglets : Apparence, Sons, Profil",
                "ThÃ¨me sombre / clair changeable en direct",
                "Profil enrichi : bio, liens cliquables, statut en ligne",
                "SÃ©lecteur d'Ã©mojis avec import d'Ã©mojis/GIFs personnalisÃ©s",
                "Envoi d'images inline dans le chat",
                "DÃ©tection automatique des liens cliquables",
            ]),
            ("V.1.0.4", "Multi-comptes & cosmÃ©tiques", [
                "SystÃ¨me de comptes locaux sÃ©curisÃ©s (hash SHA-256 + salt)",
                "Boutique de cosmÃ©tiques : couleurs, badges, titres",
                "SystÃ¨me de niveaux et XP",
            ]),
            ("V.1.0.3", "Appels vocaux & messages privÃ©s", [
                "Appels vocaux en peer-to-peer via UDP",
                "Messages privÃ©s entre membres",
                "FenÃªtres d'appel avec minuteur et mute",
            ]),
            ("V.1.0.1", "Fondations", [
                "Architecture client/serveur TCP",
                "Profils publics propagÃ©s sur le rÃ©seau",
            ]),
            ("V.1.0.0", "Version initiale", [
                "Chat LAN basique en Python/Tkinter",
            ]),
        ]
        for ver, titre, items in versions:
            zone.insert(tk.END, f"  {ver} â {titre}\n", ("ver",))
            for item in items:
                zone.insert(tk.END, f"    â¢ {item}\n", ("item",))
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
        self._titre_anime(f, "ð¥ï¸ Configurer le serveur", C_BLUE, 18)
        tk.Label(f, text="Choisis comment lancer ton salon", font=(FONT, 11), fg=C_SUB, bg=C_BG).pack(pady=(0, 12))
        cadre = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
        cadre.pack(padx=40, pady=4, fill="x")
        b_quick = tk.Button(cadre, text="â¡  DÃ©marrage rapide (salons par dÃ©faut)", height=2,
            command=self._config_rapide)
        self._btn_styler(b_quick, C_GREEN); b_quick.pack(padx=16, pady=(16, 6), fill="x")
        b_custom = tk.Button(cadre, text="ð  CrÃ©er une config personnalisÃ©e", height=2,
            command=self._config_personnalisee)
        self._btn_styler(b_custom, C_BLUE); b_custom.pack(padx=16, pady=6, fill="x")
        b_import = tk.Button(cadre, text="ð  Importer une config sauvegardÃ©e", height=2,
            command=self._config_importer)
        self._btn_styler(b_import, C_PURPLE); b_import.pack(padx=16, pady=6, fill="x")
        b_annul = tk.Button(f, text="â© Annuler", command=self._ecran_demarrage)
        self._btn_styler(b_annul, C_INP, C_TEXT); b_annul.pack(pady=12)

    def _config_rapide(self):
        self.salons = list(SALONS_DEFAUT); self.salon_courant = "gÃ©nÃ©ral"
        self._lancer_hote()

    def _config_personnalisee(self):
        self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=40)
        self._titre_anime(f, "ð CrÃ©ation de serveur", C_BLUE, 16)
        tk.Label(f, text="Nom du serveur", font=(FONT, 10), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=40, pady=(8, 0))
        self._ent_nom_srv = tk.Entry(f); self._entree_styler(self._ent_nom_srv)
        self._ent_nom_srv.pack(padx=40, pady=4, fill="x")
        self._ent_nom_srv.insert(0, "Mon serveur")
        self._salons_custom = list(SALONS_DEFAUT)
        tk.Label(f, text="Salons (clique pour supprimer)", font=(FONT, 10), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=40, pady=(12, 4))
        self._cadre_salons_custom = tk.Frame(f, bg=C_BG2, highlightbackground=C_INP, highlightthickness=1)
        self._cadre_salons_custom.pack(padx=40, pady=4, fill="x")
        self._rafraichir_salons_custom()
        b_ajout_txt = tk.Button(f, text="â Salon textuel", command=lambda: self._ajout_salon_custom("texte"))
        self._btn_styler(b_ajout_txt, C_GREEN); b_ajout_txt.pack(side="left", padx=40, pady=8)
        b_ajout_voc = tk.Button(f, text="ð¤ Salon vocal", command=lambda: self._ajout_salon_custom("vocal"))
        self._btn_styler(b_ajout_voc, C_TEAL); b_ajout_voc.pack(side="left", padx=4, pady=8)
        cadre_slot = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
        cadre_slot.pack(padx=40, pady=(12, 4), fill="x")
        tk.Label(cadre_slot, text="ð¾ Sauvegarder dans un slot (1-9)", font=(FONT, 10, "bold"), fg=C_YELLOW, bg=C_SURF2).pack(pady=(8, 4))
        grille = tk.Frame(cadre_slot, bg=C_SURF2); grille.pack(pady=(0, 8))
        for i in range(9):
            b = tk.Button(grille, text=str(i+1), font=(FONT, 12, "bold"), width=4,
                command=lambda n=i: self._sauver_config_slot(n))
            self._btn_styler(b, C_INP, C_TEXT); b.grid(row=i//3, column=i%3, padx=4, pady=4)
        b_lancer = tk.Button(f, text="ð Lancer le serveur", height=2, command=self._lancer_config_custom)
        self._btn_styler(b_lancer, C_BLUE); b_lancer.pack(padx=40, pady=(8, 4), fill="x")
        b_retour = tk.Button(f, text="â© Retour", command=self._ecran_config_serveur)
        self._btn_styler(b_retour, C_INP, C_TEXT); b_retour.pack(pady=4)

    def _rafraichir_salons_custom(self):
        for w in self._cadre_salons_custom.winfo_children(): w.destroy()
        if not self._salons_custom:
            tk.Label(self._cadre_salons_custom, text="Aucun salon", font=(FONT, 9), fg=C_DIM, bg=C_BG2).pack(padx=8, pady=8)
            return
        for s in self._salons_custom:
            icone = "ð" if s["type"] == "texte" else "ð¤"
            row = tk.Frame(self._cadre_salons_custom, bg=C_BG2); row.pack(fill="x", padx=4, pady=2)
            tk.Label(row, text=f" {icone} #{s['nom']}", font=(FONT, 10), fg=C_TEXT, bg=C_BG2).pack(side="left", padx=8, pady=4)
            b_suppr = tk.Button(row, text="ðï¸", font=(FONT, 8), bg=C_RED, fg=C_BG, relief="flat", bd=0, cursor="hand2",
                command=lambda n=s["nom"]: self._suppr_salon_custom(n))
            b_suppr.pack(side="right", padx=4, pady=4)

    def _ajout_salon_custom(self, type_s):
        nom = simpledialog.askstring("Nouveau salon", f"Nom du salon {'textuel' if type_s=='texte' else 'vocal'} :", parent=self.root)
        if not nom: return
        nom = nom.strip().lower()[:20]
        if any(s["nom"] == nom for s in self._salons_custom):
            messagebox.showwarning(APP_NAME, "Ce salon existe dÃ©jÃ ."); return
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
        if ok: self._toast("Slot sauvegardÃ©", f"Config sauvegardÃ©e dans le slot {num+1}.")
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
            messagebox.showinfo(APP_NAME, "Aucune config sauvegardÃ©e. CrÃ©e-en une d'abord !"); return
        self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
        self._fond_anime(f, height=40)
        self._titre_anime(f, "ð Importer une config", C_PURPLE, 16)
        for num, config in dispo:
            row = tk.Frame(f, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
            row.pack(padx=40, pady=4, fill="x")
            txt = f"Slot {num+1} : {config.get('nom','?')} ({len(config.get('salons',[]))} salons)"
            tk.Label(row, text=txt, font=(FONT, 11), fg=C_TEXT, bg=C_SURF2).pack(side="left", padx=12, pady=8)
            b = tk.Button(row, text="Importer", command=lambda n=num, c=config: self._importer_slot(n, c))
            self._btn_styler(b, C_GREEN); b.pack(side="right", padx=12, pady=8)
        b_retour = tk.Button(f, text="â© Retour", command=self._ecran_config_serveur)
        self._btn_styler(b_retour, C_INP, C_TEXT); b_retour.pack(pady=12)

    def _importer_slot(self, num, config):
        self.salons = list(config.get("salons", SALONS_DEFAUT))
        self.salon_courant = self.salons[0]["nom"] if self.salons else "gÃ©nÃ©ral"
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
            self.ui_queue.put(("err", f"Impossible d'hÃ©berger (port {TCP_PORT}) : {e}")); return
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
                self.ui_queue.put(("sys", f"ð¢ {pseudo_client} a rejoint le salon"))
                self.ui_queue.put(("profil", prof)); self._maj_compteur(1)
                try:
                    conn.sendall(make_msg("profils_init", profils=list(self.profils.values())))
                    conn.sendall(make_msg("salons_init", salons=self.salons))
                except OSError: pass
                self._diffuser(make_msg("profil", profil=prof), except_=conn)
                self._diffuser(make_msg("sys", text=f"ð¢ {pseudo_client} a rejoint"), except_=conn)
            elif t == "msg":
                p = m.get("pseudo", "?"); txt = m.get("text", ""); salon = m.get("salon", "gÃ©nÃ©ral")
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
                self.ui_queue.put(("sys", f"ðª {pseudo_l} a quittÃ© #{salon_l}"))
                self._diffuser(make_msg("sys", text=f"ðª {pseudo_l} a quittÃ© #{salon_l}"), except_=conn)
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
            self.ui_queue.put(("sys", f"ð´ {pseudo_client} a quittÃ© le salon"))
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
            try: conn.sendall(make_msg("sys", text=f"â  {dest} est introuvable."))
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
        self.mode = "client"; self._ecran_chargement("Recherche des discussions sur le rÃ©seauâ¦")
        threading.Thread(target=self._scan_reseau, daemon=True).start()

    def rejoindre_ip_manuel(self):
        ip = simpledialog.askstring("Connexion manuelle", "Adresse IP de l'hÃ©bergeur :", parent=self.root)
        if not ip: return
        ip = ip.strip(); self.mode = "client"; self.cible = (ip, TCP_PORT, f"{ip}:{TCP_PORT}")
        self._ecran_chargement(f"Connexion Ã  {ip}:{TCP_PORT}â¦")
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
        self.lbl_spinner = tk.Label(f, text="â ", font=(FONT, 42), fg=C_BLUE, bg=C_BG)
        self.lbl_spinner.pack(pady=(80, 8))
        self.lbl_chargement = tk.Label(f, text=texte, font=(FONT, 12), fg=C_TEXT, bg=C_BG)
        self.lbl_chargement.pack(pady=4)
        self.lbl_compteur = tk.Label(f, text="0 salon trouvÃ©", font=(FONT, 10), fg=C_GREEN, bg=C_BG)
        self.lbl_compteur.pack(pady=2)
        self._spin_idx = 0; self._animer_spinner()
        b = tk.Button(f, text="Annuler", command=self._ecran_demarrage)
        self._btn_styler(b, C_INP, C_TEXT); b.pack(pady=30)

    def _animer_spinner(self):
        if hasattr(self, "lbl_spinner") and self.lbl_spinner.winfo_exists():
            palette = _multi_gradient_hex([C_BLUE, C_PURPLE, C_PINK, C_TEAL, C_GREEN, C_YELLOW, C_BLUE], 60)
            self.lbl_spinner.config(text=SPINNER[self._spin_idx % len(SPINNER)],
                                    fg=palette[self._spin_idx % len(palette)])
            self._spin_idx += 1; self.root.after(80, self._animer_spinner)

    def _maj_chargement(self, n):
        if hasattr(self, "lbl_compteur") and self.lbl_compteur.winfo_exists():
            p = "s" if n != 1 else ""; self.lbl_compteur.config(text=f"{n} salon{p} trouvÃ©{p}")

    def _fin_scan(self, serveurs):
        if not serveurs:
            self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
            self._particules(f, count=6, height=100)
            tk.Label(f, text="\U0001f615", font=(FONT, 40), bg=C_BG).pack(pady=(60, 4))
            tk.Label(f, text="Aucune discussion trouvÃ©e", font=(FONT, 13, "bold"), fg=C_TEXT, bg=C_BG).pack(pady=4)
            tk.Label(f, text="Demande Ã  un ami de lancer un salon, ou hÃ©berge le tien !",
                font=(FONT, 10), fg=C_SUB, bg=C_BG, wraplength=380).pack(pady=6)
            b1 = tk.Button(f, text="ð¥ï¸  HÃ©berger Ã  la place", command=self.demarrer_hote)
            self._btn_styler(b1, C_BLUE); b1.pack(pady=18)
            b2 = tk.Button(f, text="âï¸  Saisir l'IP manuellement", command=self.rejoindre_ip_manuel)
            self._btn_styler(b2, C_INP, C_TEXT); b2.pack(pady=4)
            b3 = tk.Button(f, text="â© Recommencer", command=self.demarrer_rejoindre)
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
            lib += f"  â  {ip}:{port}"
            if v: lib += f"  [{v}]"
            liste.insert(tk.END, lib)
        liste.pack(padx=40, pady=6, fill="x"); liste.selection_set(0)
        def connecter():
            sel = liste.curselection()
            if not sel: messagebox.showinfo(APP_NAME, "Choisis un salon."); return
            ip, port, nom, hp, v = serveurs[sel[0]]; self.cible = (ip, port, nom)
            self._ecran_chargement(f"Connexion Ã  {nom} ({ip})â¦")
            threading.Thread(target=self._connecter_a, args=(ip, port), daemon=True).start()
        b1 = tk.Button(f, text="Se connecter", command=connecter)
        self._btn_styler(b1, C_GREEN); b1.pack(pady=16)
        b2 = tk.Button(f, text="âï¸  IP manuelle", command=self.rejoindre_ip_manuel)
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
        except OSError as e: self.ui_queue.put(("connect_fail", f"Connexion Ã©chouÃ©e : {e}"))

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
            elif t == "salon_leave": self.ui_queue.put(("sys", f"ðª {m.get('pseudo','?')} a quittÃ© #{m.get('salon','')}"))
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
            self.afficher_systeme(f"ð Nouveau salon crÃ©Ã© : #{nom}")

    def _on_vocal_join(self, pseudo, salon=None):
        self.afficher_systeme(f"ð¤ {pseudo} a rejoint le vocal")
        if hasattr(self, "liste_vocal"): self._rafraichir_liste_vocal()

    def _on_vocal_leave(self, pseudo):
        self.afficher_systeme(f"ð {pseudo} a quittÃ© le vocal")
        if hasattr(self, "liste_vocal"): self._rafraichir_liste_vocal()

    def _construire_interface_chat(self):
        self._reset_frame(); f = self.frame; f.configure(bg=C_BG)
        self._fond_gradient(f, height=44)
        barre = tk.Frame(f, bg=C_SURF2, height=40); barre.pack(fill="x")
        barre.pack_propagate(False)
        self._titre_anime_barre = tk.Label(barre, text=f"\U0001f4ac {APP_NAME}", font=(FONT, 13, "bold"), fg=C_TEXT, bg=C_SURF2)
        self._titre_anime_barre.pack(side="left", padx=14, pady=8)
        self._anim_titre_barre()
        self.lbl_statut = tk.Label(barre, text="", font=(FONT, 9), fg=C_SUB, bg=C_SURF2)
        self.lbl_statut.pack(side="right", padx=14, pady=8); self._rafraichir_statut()
        corps = tk.Frame(f, bg=C_BG); corps.pack(fill="both", expand=True, padx=4, pady=4)
        panneau_g = tk.Frame(corps, bg=C_BG2, width=170); panneau_g.pack(side="left", fill="y", padx=(0, 4))
        panneau_g.pack_propagate(False)
        tk.Label(panneau_g, text="ð SALONS", font=(FONT, 9, "bold"), fg=C_SUB, bg=C_BG2).pack(pady=(8, 4), padx=10, anchor="w")
        cadre_salons = tk.Frame(panneau_g, bg=C_BG2); cadre_salons.pack(fill="x", padx=4)
        self.liste_salons = cadre_salons
        self._rafraichir_liste_salons()
        tk.Label(panneau_g, text="ð¤ VOCAL", font=(FONT, 9, "bold"), fg=C_SUB, bg=C_BG2).pack(pady=(8, 4), padx=10, anchor="w")
        cadre_vocal = tk.Frame(panneau_g, bg=C_BG2); cadre_vocal.pack(fill="x", padx=4)
        self.liste_vocal = cadre_vocal
        self._rafraichir_liste_vocal()
        if self.mode == "host":
            btn_new = tk.Button(panneau_g, text="â Nouveau salon", font=(FONT, 9), command=self._creer_salon)
            self._btn_styler(btn_new, C_GREEN, C_BG); btn_new.pack(fill="x", padx=4, pady=4)
        cadre_msg = tk.Frame(corps, bg=C_BG); cadre_msg.pack(side="left", fill="both", expand=True)
        self.lbl_salon_courant = tk.Label(cadre_msg, text="#gÃ©nÃ©ral", font=(FONT, 11, "bold"), fg=C_BLUE, bg=C_BG)
        self.lbl_salon_courant.pack(anchor="w", padx=4, pady=(4, 2))
        scroll = tk.Scrollbar(cadre_msg); scroll.pack(side="right", fill="y")
        self.zone = tk.Text(cadre_msg, font=(FONT, 11), bg=C_BG2, fg=C_TEXT, insertbackground=C_TEXT,
            yscrollcommand=scroll.set, relief="flat", bd=0, padx=14, pady=12, wrap="word", state="disabled",
            spacing1=2, spacing3=2, highlightbackground=C_SURF2, highlightthickness=1)
        self.zone.pack(side="left", fill="both", expand=True); scroll.config(command=self.zone.yview)
        self.zone.tag_config("sys", foreground=C_DIM, font=(FONT, 9, "italic"), spacing1=6, spacing3=4)
        self.zone.tag_config("timestamp", foreground=C_DIM, font=(FONT, 8), spacing1=6)
        self.zone.tag_config("erreur", foreground=C_RED, font=(FONT, 10, "bold"), spacing1=6)
        self.zone.tag_config("moi", foreground=C_BLUE, font=(FONT, 11, "bold"), spacing1=6)
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
        b0 = tk.Button(barre_saisie, text="ð", command=self.ouvrir_selecteur_emoji, padx=10)
        self._btn_styler(b0, C_YELLOW, C_BG); b0.pack(side="left", ipady=4, padx=(0, 4))
        b1 = tk.Button(barre_saisie, text="Envoyer â¤", command=self.envoyer, padx=14)
        self._btn_styler(b1, C_BLUE); b1.pack(side="left", ipady=4)
        b2 = tk.Button(barre_saisie, text="ðï¸", command=self.ouvrir_boutique, padx=10)
        self._btn_styler(b2, C_INP, C_YELLOW); b2.pack(side="left", padx=(8, 0), ipady=4)
        b3 = tk.Button(barre_saisie, text="ð", command=self._attacher_media, padx=10)
        self._btn_styler(b3, C_TEAL, C_BG); b3.pack(side="left", padx=(8, 0), ipady=4)
        b4_chat = tk.Button(barre_saisie, text="ð¥", command=self.ouvrir_amis, padx=10)
        self._btn_styler(b4_chat, C_PINK); b4_chat.pack(side="left", padx=(8, 0), ipady=4)
        self.afficher_systeme(f"ð¢ Bienvenue {self.pseudo} !")
        if self.mode == "host":
            self.afficher_systeme(f"Tu hÃ©berges sur {local_ip()}:{TCP_PORT}. Partage cette IP si l'auto-dÃ©couverte Ã©choue.")
        if not AUDIO_OK:
            self.afficher_systeme("â¹ Appels vocaux indisponibles (installe PyAudio). Les appels fonctionnent en mode texte.")

    def _rafraichir_liste_salons(self):
        if not hasattr(self, "liste_salons"): return
        for w in self.liste_salons.winfo_children(): w.destroy()
        for s in self.salons:
            icone = "ð" if s.get("type", "texte") == "texte" else "ð¤"
            nom = s["nom"]; actif = (nom == self.salon_courant)
            bg = C_BLUE if actif else C_SURF
            fg = C_BG if actif else C_TEXT
            btn = tk.Button(self.liste_salons, text=f" {icone} #{nom}", font=(FONT, 10, "bold" if actif else "normal"),
                bg=bg, fg=fg, relief="flat", bd=0, cursor="hand2", anchor="w",
                command=lambda n=nom: self._changer_salon(n))
            btn.pack(fill="x", pady=1, padx=2)
        salon_courant_type = next((s.get("type","texte") for s in self.salons if s["nom"] == self.salon_courant), "texte")
        if salon_courant_type == "texte":
            b_quitter = tk.Button(self.liste_salons, text="ðª Quitter le salon", font=(FONT, 8),
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
        self.afficher_systeme(f"ð Tu es maintenant dans #{nom}")

    def _quitter_salon_texte(self):
        salons_texte = [s for s in self.salons if s.get("type", "texte") == "texte"]
        if len(salons_texte) <= 1:
            messagebox.showwarning(APP_NAME, "Impossible de quitter : c'est le seul salon textuel."); return
        ancien = self.salon_courant
        self.salons = [s for s in self.salons if s["nom"] != ancien]
        salons_texte = [s for s in self.salons if s.get("type", "texte") == "texte"]
        self.salon_courant = salons_texte[0]["nom"] if salons_texte else "gÃ©nÃ©ral"
        self.lbl_salon_courant.config(text=f"#{self.salon_courant}")
        self._rafraichir_liste_salons()
        self.afficher_systeme(f"ðª Tu as quittÃ© #{ancien} â #{self.salon_courant}")
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
            messagebox.showwarning(APP_NAME, "Ce salon existe dÃ©jÃ ."); return
        type_s = messagebox.askyesno("Type de salon", "Salon vocal ? (Non = salon textuel)")
        type_salon = "vocal" if type_s else "texte"
        desc = simpledialog.askstring("Description", "Description (optionnel) :", parent=self.root) or ""
        data = make_msg("salon_cree", nom=nom, type_salon=type_salon, desc=desc[:50])
        if self.mode == "host":
            self.salons.append({"nom":nom, "type":type_salon, "desc":desc[:50]})
            self._rafraichir_liste_salons()
            self._diffuser(data)
            self.afficher_systeme(f"ð Salon #{nom} crÃ©Ã© !")
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: self.afficher_erreur("Impossible de crÃ©er le salon.")

    def _rejoindre_vocal(self, salon_nom):
        self.salon_courant = salon_nom
        self.lbl_salon_courant.config(text=f"ð¤ #{salon_nom}")
        self._rafraichir_liste_salons()
        if not AUDIO_OK:
            self.afficher_systeme("ð¤ Mode vocal texte (PyAudio absent). Tu peux quand mÃªme discuter.")
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
        self.salon_courant = "gÃ©nÃ©ral"
        self.lbl_salon_courant.config(text="#gÃ©nÃ©ral")
        self._rafraichir_liste_salons()
        self._rafraichir_liste_vocal()
        self.afficher_systeme("ð Tu as quittÃ© le vocal.")

    def _rafraichir_liste_vocal(self):
        if not hasattr(self, "liste_vocal"): return
        for w in self.liste_vocal.winfo_children(): w.destroy()
        if self.vocal_actif:
            btn = tk.Button(self.liste_vocal, text=f"ð´ {self.pseudo} (toi)", font=(FONT, 9, "bold"),
                bg=C_RED, fg=C_BG, relief="flat", bd=0, cursor="hand2", command=self._quitter_vocal)
            btn.pack(fill="x", pady=1, padx=2)
            btn_q = tk.Button(self.liste_vocal, text="Quitter le vocal", font=(FONT, 8),
                bg=C_INP, fg=C_TEXT, relief="flat", bd=0, cursor="hand2", command=self._quitter_vocal)
            btn_q.pack(fill="x", pady=1, padx=2)
        else:
            tk.Label(self.liste_vocal, text="Personne en vocal", font=(FONT, 8), fg=C_DIM, bg=C_BG2).pack(padx=4)

    def _anim_titre_barre(self):
        palette = _multi_gradient_hex([C_BLUE, C_PURPLE, C_TEAL, C_BLUE], 60)
        idx = [0]
        def anim():
            if hasattr(self, "_titre_anime_barre") and self._titre_anime_barre.winfo_exists():
                self._titre_anime_barre.config(fg=palette[idx[0] % len(palette)])
                idx[0] = (idx[0] + 1) % len(palette)
                self.root.after(100, anim)
        anim()

    def _rafraichir_statut(self):
        if not hasattr(self, "lbl_statut") or not self.lbl_statut.winfo_exists(): return
        if self.mode == "host":
            self.lbl_statut.config(text=f"ð¢ {local_ip()}:{TCP_PORT}  â¢  {self.nb_connectes} connectÃ©(s) en plus de toi")
        elif self.cible:
            ip, port, nom = self.cible; self.lbl_statut.config(text=f"ðµ {nom} ({ip}:{port})")

    def _rafraichir_liste_participants(self):
        if not hasattr(self, "liste_part"): return
        self.liste_part.config(state="normal"); self.liste_part.delete("1.0", tk.END)
        for p in self.profils:
            prof = self.profils[p]; badge = badge_emoji(prof.get("badge", "etoile"))
            en_ligne = prof.get("en_ligne", True)
            point = "ð¢" if en_ligne else "â«"
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
            "bio":"", "liens":[], "en_ligne":True, "avatar":"ð§"})
        win = tk.Toplevel(self.root); win.title(f"Profil â {pseudo}"); win.geometry("420x600")
        win.configure(bg=C_BG); win.transient(self.root)
        self._fond_gradient(win, height=50)
        entete = tk.Frame(win, bg=C_BG); entete.pack(fill="x", padx=16, pady=(10, 0))
        avatar = prof.get("avatar", "\U0001f9d1")
        cadre_sym = CADRES.get(prof.get("cadre", CADRE_DEFAUT), {}).get("symbole", "")
        badge = badge_emoji(prof.get("badge", "etoile"))
        couleur = couleur_hex(prof.get("couleur", COULEURS_DEFAUT))
        if cadre_sym:
            tk.Label(entete, text=cadre_sym, font=(FONT, 36), fg=couleur, bg=C_BG).pack(side="left", padx=(0, 2))
        tk.Label(entete, text=avatar, font=(FONT, 36), bg=C_BG).pack(side="left", padx=(0, 8))
        col_pseudo = tk.Frame(entete, bg=C_BG); col_pseudo.pack(side="left")
        lbl_pseudo = tk.Label(col_pseudo, text=pseudo, font=(FONT, 18, "bold"), fg=couleur, bg=C_BG)
        lbl_pseudo.pack(anchor="w")
        if couleur_anime(prof.get("couleur", COULEURS_DEFAUT)):
            self._animer_lbl_pseudo(lbl_pseudo, prof.get("couleur"))
        en_ligne = prof.get("en_ligne", True)
        statut_txt = "ð¢ En ligne" if en_ligne else "â« Hors ligne"
        statut_col = C_GREEN if en_ligne else C_DIM
        tk.Label(col_pseudo, text=f"{badge} {statut_txt}", font=(FONT, 10), fg=statut_col, bg=C_BG).pack(anchor="w")
        tk.Label(win, text="Â« " + titre_nom(prof.get("titre", "membre")) + " Â»",
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
            tk.Label(corps, text="ð Ã propos", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", pady=(4, 2))
            tk.Label(corps, text=bio, font=(FONT, 10), fg=C_TEXT, bg=C_BG, wraplength=350, justify="left").pack(anchor="w", pady=(0, 8))
        liens = prof.get("liens", [])
        if liens:
            tk.Label(corps, text="ð Liens", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", pady=(4, 2))
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
        for lib, val in [("ð¬ Messages", prof.get("msgs", 0)), ("ðª Coins", prof.get("coins", 0)),
            ("ð Appels", prof.get("appels", 0)), ("â¨ XP", prof.get("xp", 0))]:
            row = tk.Frame(corps, bg=C_BG); row.pack(fill="x", pady=3)
            tk.Label(row, text=lib, font=(FONT, 11), fg=C_TEXT, bg=C_BG).pack(side="left")
            tk.Label(row, text=str(val), font=(FONT, 11, "bold"), fg=C_GREEN, bg=C_BG).pack(side="right")
        tk.Label(corps, text="CosmÃ©tiques Ã©quipÃ©s", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", pady=(12, 4))
        coul_nom = COULEURS.get(prof.get('couleur'), {}).get('nom', '?')
        badge_nom = BADGES.get(prof.get('badge'), {}).get('nom', '?')
        titre_nom_aff = titre_nom(prof.get('titre', 'membre'))
        tk.Label(corps, text=f"ð¨ Couleur : {coul_nom}\n"
            f"ð Badge : {badge_nom}\n"
            f"ð·ï¸ Titre : {titre_nom_aff}",
            font=(FONT, 10), fg=C_TEXT, bg=C_BG, justify="left").pack(anchor="w")
        av_nom = AVATARS_PREF.get(prof.get('avatar_pref', AVATAR_DEFAUT), {}).get('nom', '?')
        cad_nom = CADRES.get(prof.get('cadre', CADRE_DEFAUT), {}).get('nom', '?')
        fond_nom = FONDS_PROFIL.get(prof.get('fond', 'defaut'), {}).get('nom', '?')
        tk.Label(corps, text=f"Avatar: {av_nom}  |  Cadre: {cad_nom}  |  Fond: {fond_nom}", font=(FONT, 9), fg=C_SUB, bg=C_BG, justify="left").pack(anchor="w", pady=(4, 0))
        if pseudo == self.pseudo:
            b_mod = tk.Button(corps, text="âï¸ Modifier mon profil", command=lambda: self._modifier_profil(win))
            self._btn_styler(b_mod, C_PURPLE); b_mod.pack(pady=12)
        else:
            btns = tk.Frame(corps, bg=C_BG); btns.pack(pady=12)
            b1 = tk.Button(btns, text="ð¬ MP", command=lambda: self._ouvrir_fenetre_mp(pseudo))
            self._btn_styler(b1, C_BLUE); b1.pack(side="left", padx=6)
            b2 = tk.Button(btns, text="ð Appeler", command=lambda: self._demarrer_appel(pseudo))
            self._btn_styler(b2, C_GREEN); b2.pack(side="left", padx=6)
            if self._est_ami(pseudo):
                b3 = tk.Button(btns, text="â Ami", command=lambda: (self._supprimer_ami(pseudo), self._rafraichir_carte_ami(win, pseudo)))
                self._btn_styler(b3, C_PINK); b3.pack(side="left", padx=6)
            else:
                b3 = tk.Button(btns, text="â Ami", command=lambda: (self._ajouter_ami(pseudo), self._rafraichir_carte_ami(win, pseudo)))
                self._btn_styler(b3, C_TEAL); b3.pack(side="left", padx=6)

    def _rafraichir_carte_ami(self, win, pseudo):
        try: win.destroy()
        except: pass
        self._ouvrir_carte_profil(pseudo)

    def _modifier_profil(self, parent_win):
        win = tk.Toplevel(self.root); win.title("Modifier mon profil"); win.geometry("460x480")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_gradient(win, height=40)
        tk.Label(win, text="âï¸ Modifier mon profil", font=(FONT, 15, "bold"), fg=C_PURPLE, bg=C_BG).pack(pady=(8, 8))
        tk.Label(win, text="ð§ Avatar Ã©moji", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=24)
        ent_avatar = tk.Entry(win, font=(FONT, 16), width=4); self._entree_styler(ent_avatar)
        ent_avatar.insert(0, self.compte.get("avatar_emoji", "ð§"))
        ent_avatar.pack(anchor="w", padx=24, pady=(2, 8))
        tk.Label(win, text="ð Bio", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=24)
        txt_bio = tk.Text(win, font=(FONT, 11), bg=C_INP, fg=C_TEXT, insertbackground=C_TEXT,
            relief="flat", bd=0, wrap="word", height=4, padx=10, pady=8)
        txt_bio.pack(fill="x", padx=24, pady=(2, 8))
        txt_bio.insert("1.0", self.compte.get("bio", ""))
        tk.Label(win, text="ð Liens (un par ligne)", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=24)
        txt_liens = tk.Text(win, font=(FONT, 11), bg=C_INP, fg=C_TEXT, insertbackground=C_TEXT,
            relief="flat", bd=0, wrap="word", height=5, padx=10, pady=8)
        txt_liens.pack(fill="x", padx=24, pady=(2, 8))
        txt_liens.insert("1.0", "\n".join(self.compte.get("liens", [])))
        def sauver():
            bio = txt_bio.get("1.0", tk.END).strip()[:300]
            liens_raw = txt_liens.get("1.0", tk.END).strip().split("\n")
            liens = [l.strip() for l in liens_raw if l.strip()][:10]
            avatar = ent_avatar.get().strip()[:2] or "ð§"
            self.compte["bio"] = bio; self.compte["liens"] = liens; self.compte["avatar_emoji"] = avatar
            self.gc.sauver(); self._propager_profil()
            win.destroy(); parent_win.destroy(); self._ouvrir_carte_profil(self.pseudo)
            messagebox.showinfo(APP_NAME, "Profil mis Ã  jour !")
        b = tk.Button(win, text="âï¸ Enregistrer", command=sauver)
        self._btn_styler(b, C_GREEN); b.pack(pady=10)

    def _animer_lbl_pseudo(self, lbl, cid):
        if cid == "arc": palette = _multi_gradient_hex(RAINBOW + RAINBOW, 60)
        elif cid == "galaxy": palette = _multi_gradient_hex(["#cba6f7","#89b4fa","#f5c2e7","#b4befe","#cba6f7"], 60)
        elif cid == "feu": palette = _multi_gradient_hex(["#f38ba8","#fab387","#f9e2af","#eba0ac","#f38ba8"], 60)
        else: palette = [couleur_hex(cid)]
        idx = [0]
        def anim():
            if lbl.winfo_exists():
                lbl.config(fg=palette[idx[0] % len(palette)]); idx[0] += 1; self.root.after(100, anim)
        anim()

    def _anim_barre_xp(self, barre, target):
        cur = [0.0]
        def anim():
            if not barre.winfo_exists(): return
            cur[0] = min(cur[0] + 0.03, target)
            for w in barre.winfo_children(): w.destroy()
            fill = tk.Frame(barre, bg=C_GREEN)
            fill.place(x=0, y=0, relwidth=cur[0], relheight=1)
            if cur[0] > 0.02:
                glow_col = _multi_gradient_hex([C_GREEN, self._lighten(C_GREEN, 0.6), C_GREEN], 40)
                glow = tk.Frame(fill, bg=glow_col[int((time.time()*3) % len(glow_col))])
                glow.place(x=0, y=0, relwidth=1, relheight=1)
            if cur[0] < target: self.root.after(18, anim)
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
            except OSError: self.afficher_erreur("Connexion perdue : message non envoyÃ©."); return
        self._gagner_xp(1, coins=1, msgs=1)
        self.afficher_message(self.pseudo, texte, moi=True)
        son_envoi(self.compte)
        for mot in texte.split():
            if mot.startswith("@") and mot[1:] in self.profils and mot[1:] != self.pseudo:
                self._toast(f"ð·ï¸ Tu as mentionnÃ© {mot[1:]}", None)

    def _gagner_xp(self, xp, coins=0, msgs=0, appels=0):
        ancien_niv, _ = niveau_from_xp(self.compte["xp"])
        self.compte["xp"] += xp; self.compte["coins"] += coins
        self.compte["msgs"] += msgs; self.compte["appels"] += appels
        nouveau_niv, _ = niveau_from_xp(self.compte["xp"])
        self.gc.sauver(); self._rafraichir_compte_ui(); self._propager_profil_local()
        if nouveau_niv > ancien_niv:
            self.compte["coins"] += 50; self.gc.sauver(); self._rafraichir_compte_ui()
            self._toast(f"ð Niveau {nouveau_niv} ! +50 ðª", None); beep(1200, 200)

    def afficher_message(self, pseudo, texte, moi=False):
        if not hasattr(self, "zone"): return
        prof = self.profils.get(pseudo, {}); badge = badge_emoji(prof.get("badge", "etoile"))
        avatar = prof.get("avatar", "\U0001f9d1")
        self.zone.config(state="normal")
        ts = time.strftime("%H:%M")
        self.zone.insert(tk.END, f"{ts} ", "timestamp")
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
        self.zone.config(state="normal"); self.zone.insert(tk.END, "â  " + texte + "\n", "erreur")
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
                    widget.insert(tk.END, f"ð¬ {url_text}", tag_v)
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
        tk.Label(win, text=f"ð Conversation privÃ©e avec {dest}", font=(FONT, 11, "bold"), fg=C_TEXT, bg=C_BG).pack(pady=6)
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
        b = tk.Button(win, text="â¤", command=envoyer_mp, padx=14)
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
                except OSError: self.afficher_erreur(f"MP vers {dest} Ã©chouÃ©.")
            else: self.afficher_erreur(f"{dest} est introuvable.")
        else:
            try: self.sock.sendall(make_msg("mp", from_=self.pseudo, dest=dest, text=texte))
            except OSError: self.afficher_erreur("MP non envoyÃ© (connexion perdue).")
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
        self._toast(f"âï¸ MP de {src} : {texte[:30]}", lambda: self._ouvrir_fenetre_mp(src))
    def _demarrer_appel(self, dest):
        if dest == self.pseudo: return
        if dest in self.appels: messagebox.showinfo(APP_NAME, "Un appel est dÃ©jÃ  en cours."); return
        if dest in self.fenetres_appel and self.fenetres_appel[dest].winfo_exists(): return
        if self.mode == "host":
            sd = self.pseudo_to_sock.get(dest)
            if not sd: self.afficher_erreur(f"{dest} est introuvable."); return
            try: sd.sendall(make_msg("call_incoming", from_=self.pseudo))
            except OSError: self.afficher_erreur("Demande d'appel Ã©chouÃ©e.")
        else:
            try: self.sock.sendall(make_msg("call_request", from_=self.pseudo, dest=dest))
            except OSError: self.afficher_erreur("Demande d'appel Ã©chouÃ©e."); return
        self._ouvrir_fenetre_appel(dest, appelant=True)

    def _ouvrir_fenetre_appel(self, peer, appelant=False):
        win = tk.Toplevel(self.root); win.title(f"Appel avec {peer}"); win.geometry("340x380")
        win.configure(bg=C_BG); win.transient(self.root)
        tk.Label(win, text="ð", font=(FONT, 40), bg=C_BG, fg=C_GREEN).pack(pady=(16, 4))
        self.lbl_appel_peer = tk.Label(win, text=peer, font=(FONT, 16, "bold"), fg=C_TEXT, bg=C_BG)
        self.lbl_appel_peer.pack()
        self.lbl_appel_statut = tk.Label(win, text="En attenteâ¦" if appelant else "Appel entrantâ¦", font=(FONT, 11), fg=C_SUB, bg=C_BG)
        self.lbl_appel_statut.pack(pady=4)
        self.lbl_duree = tk.Label(win, text="00:00", font=(FONT, 12, "bold"), fg=C_GREEN, bg=C_BG)
        self.lbl_duree.pack(pady=4)
        btns = tk.Frame(win, bg=C_BG); btns.pack(pady=18)
        self.btn_mute = tk.Button(btns, text="ð Muet", command=self._toggle_mute)
        self._btn_styler(self.btn_mute, C_INP, C_TEXT); self.btn_mute.pack(side="left", padx=6)
        b = tk.Button(btns, text="ð Raccrocher", command=lambda: self._raccrocher(peer))
        self._btn_styler(b, C_RED); b.pack(side="left", padx=6)
        if not AUDIO_OK:
            tk.Label(win, text="Mode texte (PyAudio absent)\nâ parle via le mini-chat â",
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
            if muet: self.btn_mute.config(text="ðï¸ Activer", bg=C_GREEN, fg=C_BG)
            else: self.btn_mute.config(text="ð Muet", bg=C_INP, fg=C_TEXT)

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
        result = messagebox.askyesno(APP_NAME, f"ð {src} t'appelle ! Accepter ?")
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
        if hasattr(win, "lbl_appel_statut"): win.lbl_appel_statut.config(text="ConnectÃ© !")
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
        if hasattr(win, "lbl_appel_statut"): win.lbl_appel_statut.config(text="ConnectÃ© !")
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
            if hasattr(win, "lbl_appel_statut"): win.lbl_appel_statut.config(text=f"{src} a refusÃ© l'appel.")
            self.root.after(3000, lambda: win.destroy() if win.winfo_exists() else None)
            self.fenetres_appel.pop(src, None)

    def _on_appel_fin(self, src):
        self.audio.arreter()
        if src in self.fenetres_appel:
            win = self.fenetres_appel[src]
            if win.winfo_exists():
                if hasattr(win, "lbl_appel_statut"): win.lbl_appel_statut.config(text="Appel terminÃ©.")
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
    def _ajouter_ami(self, pseudo):
        if pseudo == self.pseudo:
            messagebox.showwarning(APP_NAME, "Tu ne peux pas t'ajouter toi-mÃªme comme ami !"); return
        if pseudo in self.compte.get("amis", []):
            messagebox.showinfo(APP_NAME, f"{pseudo} est dÃ©jÃ  ton ami."); return
        amis = self.compte.get("amis", [])
        amis.append(pseudo); self.compte["amis"] = amis; self.gc.sauver()
        self._toast("Ami ajoutÃ©", f"{pseudo} a Ã©tÃ© ajoutÃ© Ã  tes amis.")

    def _supprimer_ami(self, pseudo):
        amis = self.compte.get("amis", [])
        if pseudo in amis:
            amis.remove(pseudo); self.compte["amis"] = amis; self.gc.sauver()
            self._toast("Ami retirÃ©", f"{pseudo} a Ã©tÃ© retirÃ© de tes amis.")

    def _est_ami(self, pseudo):
        return pseudo in self.compte.get("amis", [])

    def ouvrir_amis(self):
        win = tk.Toplevel(self.root); win.title("ð¥ Mes amis"); win.geometry("480x560")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_gradient(win, height=40)
        tk.Label(win, text="ð¥ Mes amis", font=(FONT, 15, "bold"), fg=C_PINK, bg=C_BG).pack(pady=(8, 4))
        amis = self.compte.get("amis", [])
        tk.Label(win, text=f"{len(amis)} ami(s)", font=(FONT, 10), fg=C_DIM, bg=C_BG).pack(pady=(0, 8))

        # Liste scrollable
        zone = tk.Frame(win, bg=C_BG); zone.pack(fill="both", expand=True, padx=12, pady=4)
        canvas = tk.Canvas(zone, bg=C_BG, highlightthickness=0)
        scroll = tk.Scrollbar(zone, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y"); canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=C_BG)
        canvas.create_window(0, 0, window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        if not amis:
            tk.Label(inner, text="Tu n'as pas encore d'amis.", font=(FONT, 11), fg=C_DIM, bg=C_BG).pack(pady=(30, 8))
            tk.Label(inner, text="Clique sur un pseudo dans le chat ou la liste\npour ouvrir son profil et l'ajouter.",
                font=(FONT, 9), fg=C_SUB, bg=C_BG, justify="center").pack(pady=4)
        else:
            for ami in sorted(amis):
                prof = self.profils.get(ami, {})
                en_ligne = prof.get("en_ligne", False)
                avatar = prof.get("avatar", "ð§")
                badge = badge_emoji(prof.get("badge", "etoile"))
                point = "ð¢" if en_ligne else "â«"
                row = tk.Frame(inner, bg=C_SURF2, highlightbackground=C_INP, highlightthickness=1)
                row.pack(fill="x", padx=4, pady=3)
                tk.Label(row, text=f"{point} {avatar} {ami} {badge}", font=(FONT, 11, "bold"),
                    fg=couleur_hex(prof.get("couleur", COULEURS_DEFAUT)), bg=C_SURF2).pack(side="left", padx=10, pady=6)
                statut_txt = "En ligne" if en_ligne else "Hors ligne"
                tk.Label(row, text=statut_txt, font=(FONT, 8), fg=C_GREEN if en_ligne else C_DIM, bg=C_SURF2).pack(side="left", padx=8)
                b_mp = tk.Button(row, text="ð¬", font=(FONT, 10), bg=C_BLUE, fg=C_BG, relief="flat", bd=0, cursor="hand2",
                    command=lambda p=ami: (win.destroy(), self._ouvrir_fenetre_mp(p)))
                b_mp.pack(side="right", padx=4, pady=6)
                b_suppr = tk.Button(row, text="ðï¸", font=(FONT, 9), bg=C_RED, fg=C_BG, relief="flat", bd=0, cursor="hand2",
                    command=lambda p=ami, r=row: self._supprimer_ami_depuis_liste(p, r, win))
                b_suppr.pack(side="right", padx=4, pady=6)

        btn_f = tk.Button(win, text="Fermer", command=win.destroy)
        self._btn_styler(btn_f, C_INP, C_TEXT); btn_f.pack(pady=8)

    def _supprimer_ami_depuis_liste(self, pseudo, row, win):
        if messagebox.askyesno(APP_NAME, f"Retirer {pseudo} de tes amis ?"):
            self._supprimer_ami(pseudo)
            row.destroy()

    def ouvrir_parametres(self):
        win = tk.Toplevel(self.root); win.title("ParamÃ¨tres"); win.geometry("560x580")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_gradient(win, height=40)
        tk.Label(win, text="âï¸ ParamÃ¨tres", font=(FONT, 15, "bold"), fg=C_PURPLE, bg=C_BG).pack(pady=(8, 6))
        nb = ttk.Notebook(win); nb.pack(fill="both", expand=True, padx=12, pady=12)
        f_app = tk.Frame(nb, bg=C_BG); f_sons = tk.Frame(nb, bg=C_BG); f_profil = tk.Frame(nb, bg=C_BG)
        nb.add(f_app, text="ð¨ Apparence")
        nb.add(f_sons, text="ð Sons")
        nb.add(f_profil, text="ð¤ Profil")
        self._param_page_apparence(f_app)
        self._param_page_sons(f_sons)
        self._param_page_profil(f_profil)
        btn_f = tk.Button(win, text="Fermer", command=win.destroy)
        self._btn_styler(btn_f, C_INP, C_TEXT); btn_f.pack(pady=8)

    def _param_page_apparence(self, parent):
        tk.Label(parent, text="ThÃ¨me", font=(FONT, 14, "bold"), fg=C_BLUE, bg=C_BG).pack(anchor="w", padx=16, pady=(16, 6))
        cadre = tk.Frame(parent, bg=C_SURF); cadre.pack(fill="x", padx=16, pady=4)
        for nom_theme in THEMES:
            ligne = tk.Frame(cadre, bg=C_SURF); ligne.pack(fill="x", pady=3)
            icone = "ð" if nom_theme == "sombre" else "âï¸"
            tk.Label(ligne, text=f"{icone} {nom_theme.capitalize()}", font=(FONT, 12), fg=C_TEXT, bg=C_SURF).pack(side="left", padx=12, pady=8)
            actuel = self.compte.get("theme", "sombre")
            if nom_theme == actuel:
                tk.Label(ligne, text="â Actif", font=(FONT, 10, "bold"), fg=C_GREEN, bg=C_SURF).pack(side="right", padx=12)
            else:
                btn = tk.Button(ligne, text="Activer", command=lambda t=nom_theme: self._changer_theme(t, parent))
                self._btn_styler(btn, C_BLUE); btn.pack(side="right", padx=12, ipady=3)
        tk.Label(parent, text="Le thÃ¨me s'applique Ã  toute l'application immÃ©diatement.", font=(FONT, 9, "italic"), fg=C_DIM, bg=C_BG).pack(anchor="w", padx=16, pady=(8, 0))

    def _changer_theme(self, nom, parent=None):
        self.compte["theme"] = nom; self.gc.sauver()
        _appliquer_theme(nom)
        self.root.configure(bg=C_BG)
        if hasattr(self, "frame"): self.frame.configure(bg=C_BG)
        self._toast("ThÃ¨me", f"ThÃ¨me {nom} appliquÃ©.")
        if parent:
            for w in parent.winfo_children(): w.destroy()
            self._param_page_apparence(parent)

    def _param_page_sons(self, parent):
        tk.Label(parent, text="Sons personnalisÃ©s", font=(FONT, 14, "bold"), fg=C_BLUE, bg=C_BG).pack(anchor="w", padx=16, pady=(16, 4))
        for cle, label in [("sonnerie", "Sonnerie d'appel"), ("notif", "Notification MP"), ("son_envoi", "Son d'envoi"), ("son_connexion", "Son de connexion")]:
            cadre = tk.Frame(parent, bg=C_SURF); cadre.pack(fill="x", padx=16, pady=3)
            courant = self.compte.get(cle, "")
            tk.Label(cadre, text=label, font=(FONT, 10), fg=C_TEXT, bg=C_SURF).pack(side="left", padx=12, pady=6)
            tk.Label(cadre, text=(courant[:25] + "â¦") if len(courant) > 25 else (courant or "Par dÃ©faut"), font=(FONT, 8), fg=C_DIM, bg=C_SURF).pack(side="left", padx=8)
            btn = tk.Button(cadre, text="ð", command=lambda c=cle: self._choisir_son(c))
            self._btn_styler(btn, C_BLUE); btn.pack(side="right", padx=12, ipady=2)
        tk.Label(parent, text="Sons prÃ©chargÃ©s (tÃ©lÃ©chargement internet)", font=(FONT, 12, "bold"), fg=C_PURPLE, bg=C_BG).pack(anchor="w", padx=16, pady=(16, 4))
        cadre_p = tk.Frame(parent, bg=C_BG); cadre_p.pack(fill="x", padx=16, pady=4)
        for i, (nom, url) in enumerate(SONS_PRESETS.items()):
            ligne = tk.Frame(cadre_p, bg=C_SURF); ligne.pack(fill="x", pady=2)
            tk.Label(ligne, text=nom, font=(FONT, 9), fg=C_TEXT, bg=C_SURF).pack(side="left", padx=12, pady=6)
            btn_test = tk.Button(ligne, text="â¶", command=lambda u=url: self._tester_son_url(u))
            self._btn_styler(btn_test, C_INP, C_TEXT); btn_test.pack(side="right", padx=4, ipady=2)
            btn_dl = tk.Button(ligne, text="â¬ Sonnerie", command=lambda u=url: self._telecharger_son(u, "sonnerie"))
            self._btn_styler(btn_dl, C_GREEN); btn_dl.pack(side="right", padx=4, ipady=2)
            btn_dn = tk.Button(ligne, text="â¬ Notif", command=lambda u=url: self._telecharger_son(u, "notif"))
            self._btn_styler(btn_dn, C_TEAL, C_BG); btn_dn.pack(side="right", padx=4, ipady=2)
        tk.Label(parent, text="Les fichiers sont stockÃ©s localement et rÃ©utilisÃ©s.", font=(FONT, 9, "italic"), fg=C_DIM, bg=C_BG).pack(anchor="w", padx=16, pady=(8, 0))

    def _choisir_son(self, cle):
        chemin = filedialog.askopenfilename(title=f"Choisir son â {cle}", filetypes=[("Audio", "*.mp3 *.wav *.ogg *.m4a"), ("Tous", "*.*")])
        if not chemin: return
        self.compte[cle] = chemin; self.gc.sauver()
        _SONS_PERSO[cle.replace("son_", "").replace("sonnerie", "sonnerie")] = chemin
        if cle == "sonnerie": _SONS_PERSO["sonnerie"] = chemin
        elif cle == "notif": _SONS_PERSO["notif"] = chemin
        elif cle == "son_envoi": _SONS_PERSO["envoi"] = chemin
        elif cle == "son_connexion": _SONS_PERSO["connexion"] = chemin
        self._toast("Son configurÃ©", f"{cle} mis Ã  jour.")

    def _telecharger_son(self, url, cle):
        ext = url.rsplit(".", 1)[-1]
        dossier = "sons_lanchat"; os.makedirs(dossier, exist_ok=True)
        chemin = os.path.join(dossier, f"{cle}.{ext}")
        try:
            urllib.request.urlretrieve(url, chemin)
            self.compte[cle] = chemin; self.gc.sauver()
            if cle == "sonnerie": _SONS_PERSO["sonnerie"] = chemin
            elif cle == "notif": _SONS_PERSO["notif"] = chemin
            self._toast("TÃ©lÃ©chargÃ©", f"{cle} sauvegardÃ© localement.")
        except Exception as e:
            self._toast("Erreur", f"TÃ©lÃ©chargement impossible: {e}")

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
        tk.Label(parent, text="ð§ Avatar Ã©moji", font=(FONT, 10, "bold"), fg=C_SUB, bg=C_BG).pack(anchor="w", padx=16, pady=(4, 2))
        ent_avatar = tk.Entry(parent, font=(FONT, 14), width=4); self._entree_styler(ent_avatar)
        ent_avatar.insert(0, self.compte.get("avatar_emoji", "ð§"))
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
            avatar = ent_avatar.get().strip()[:2] or "ð§"
            self.compte["bio"] = bio; self.compte["liens"] = liens; self.compte["avatar_emoji"] = avatar
            self.gc.sauver(); self._propager_profil()
            self._toast("Profil", "Modifications enregistrÃ©es.")
        btn_s = tk.Button(parent, text="ð¾ Enregistrer", command=sauver)
        self._btn_styler(btn_s, C_GREEN); btn_s.pack(anchor="e", padx=16, pady=12)

    def ouvrir_selecteur_emoji(self):
        win = tk.Toplevel(self.root); win.title("ð SÃ©lecteur d'Ã©mojis"); win.geometry("560x620")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()

        # --- Barre de recherche ---
        barre_rech = tk.Frame(win, bg=C_BG2); barre_rech.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(barre_rech, text="ð", font=(FONT, 12), bg=C_BG2).pack(side="left", padx=4)
        ent_rech = tk.Entry(barre_rech); self._entree_styler(ent_rech)
        ent_rech.pack(side="left", fill="x", expand=True, padx=(4, 8), ipady=4)
        lbl_info = tk.Label(barre_rech, text="", font=(FONT, 8), fg=C_DIM, bg=C_BG2)
        lbl_info.pack(side="left", padx=4)

        # --- Barre des catÃ©gories (scrollable horizontalement) ---
        zone_cats = tk.Frame(win, bg=C_BG2, height=36); zone_cats.pack(fill="x", padx=4, pady=(0, 4))
        canvas_cats = tk.Canvas(zone_cats, bg=C_BG2, highlightthickness=0, height=34)
        scroll_cats = tk.Scrollbar(zone_cats, orient="horizontal", command=canvas_cats.xview)
        canvas_cats.configure(xscrollcommand=scroll_cats.set)
        scroll_cats.pack(side="bottom", fill="x")
        canvas_cats.pack(side="top", fill="both", expand=True)
        frame_cats = tk.Frame(canvas_cats, bg=C_BG2)
        canvas_cats.create_window(0, 0, window=frame_cats, anchor="nw")
        frame_cats.bind("<Configure>", lambda e: canvas_cats.configure(scrollregion=canvas_cats.bbox("all")))

        # --- Zone d'Ã©mojis scrollable (Canvas + Scrollbar vertical) ---
        zone_emojis = tk.Frame(win, bg=C_BG); zone_emojis.pack(fill="both", expand=True, padx=4, pady=4)
        canvas_e = tk.Canvas(zone_emojis, bg=C_BG, highlightthickness=0)
        scroll_e = tk.Scrollbar(zone_emojis, orient="vertical", command=canvas_e.yview)
        canvas_e.configure(yscrollcommand=scroll_e.set)
        scroll_e.pack(side="right", fill="y")
        canvas_e.pack(side="left", fill="both", expand=True)
        conteneur = tk.Frame(canvas_e, bg=C_BG)
        canvas_e.create_window(0, 0, window=conteneur, anchor="nw")
        conteneur.bind("<Configure>", lambda e: canvas_e.configure(scrollregion=canvas_e.bbox("all")))

        # Molette pour scroller
        def _molette(event):
            canvas_e.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_e.bind("<MouseWheel>", _molette)
        canvas_e.bind("<Enter>", lambda e: canvas_e.bind_all("<MouseWheel>", _molette))
        canvas_e.bind("<Leave>", lambda e: canvas_e.unbind_all("<MouseWheel>"))

        # --- Barre perso ---
        barre_perso = tk.Frame(win, bg=C_BG); barre_perso.pack(fill="x", padx=8, pady=6)
        btn_import = tk.Button(barre_perso, text="ð Importer Ã©moji / GIF", command=self._importer_emoji)
        self._btn_styler(btn_import, C_PURPLE); btn_import.pack(side="left", ipady=4, padx=8)
        persos = _lister_emojis_perso()
        if persos:
            tk.Label(barre_perso, text=f"{len(persos)} perso(s)", font=(FONT, 9), fg=C_DIM, bg=C_BG).pack(side="left", padx=8)

        PIL_OK = False
        try:
            from PIL import Image, ImageTk
            PIL_OK = True
        except Exception:
            PIL_OK = False

        def inserer(e):
            if hasattr(self, "entree"):
                self.entree.insert(tk.INSERT, e)
                win.destroy(); self.entree.focus()

        cat_active = [None]
        def afficher_categorie(cat):
            cat_active[0] = cat
            ent_rech.delete(0, tk.END)
            _afficher_emojis(cat, "")

        def _afficher_emojis(cat, filtre):
            for w in conteneur.winfo_children(): w.destroy()
            if cat == "Perso" and persos:
                if PIL_OK:
                    for f in persos:
                        try:
                            path = os.path.join(EMOJI_DIR, f)
                            img = Image.open(path); img.thumbnail((40, 40))
                            photo = ImageTk.PhotoImage(img)
                            btn = tk.Button(conteneur, image=photo, bg=C_SURF, relief="flat", bd=0, cursor="hand2",
                                command=lambda p=path: inserer(f"[img:{p}]"))
                            btn.image = photo; btn.grid(padx=2, pady=2)
                        except Exception:
                            btn = tk.Button(conteneur, text=f[:8], bg=C_SURF, relief="flat", bd=0,
                                command=lambda p=os.path.join(EMOJI_DIR, f): inserer(f"[img:{p}]"))
                            btn.grid(padx=2, pady=2)
                else:
                    tk.Label(conteneur, text="Installe Pillow pour les Ã©mojis persos", font=(FONT, 10), fg=C_DIM, bg=C_BG).pack(pady=20)
                lbl_info.config(text=f"{len(persos)} perso(s)")
                return
            liste = EMOJIS.get(cat, [])
            if filtre:
                liste = [e for e in liste if filtre.lower() in e.lower()]
            nb_col = 10
            for i, emoji in enumerate(liste):
                btn = tk.Button(conteneur, text=emoji, font=(FONT, 22), bg=C_SURF, fg=C_TEXT,
                    relief="flat", bd=0, cursor="hand2", command=lambda e=emoji: inserer(e))
                btn.grid(row=i // nb_col, column=i % nb_col, padx=3, pady=3)
            lbl_info.config(text=f"{len(liste)} Ã©moji(s)")

        def _on_recherche(event=None):
            filtre = ent_rech.get().strip()
            cat = cat_active[0]
            if not cat: return
            if filtre:
                # Recherche globale dans toutes les catÃ©gories
                for w in conteneur.winfo_children(): w.destroy()
                tous = []
                for c, ems in EMOJIS.items():
                    for e in ems:
                        if filtre.lower() in e.lower():
                            tous.append(e)
                nb_col = 10
                for i, emoji in enumerate(tous):
                    btn = tk.Button(conteneur, text=emoji, font=(FONT, 22), bg=C_SURF, fg=C_TEXT,
                        relief="flat", bd=0, cursor="hand2", command=lambda e=emoji: inserer(e))
                    btn.grid(row=i // nb_col, column=i % nb_col, padx=3, pady=3)
                lbl_info.config(text=f"{len(tous)} rÃ©sultat(s)")
            else:
                _afficher_emojis(cat, "")
        ent_rech.bind("<KeyRelease>", _on_recherche)

        # --- Boutons catÃ©gories ---
        cats = list(EMOJIS.keys())
        if persos: cats.append("Perso")
        for cat in cats:
            b = tk.Button(frame_cats, text=cat, font=(FONT, 9, "bold"), bg=C_SURF, fg=C_TEXT,
                relief="flat", bd=0, cursor="hand2", padx=6, pady=2,
                command=lambda c=cat: afficher_categorie(c))
            b.pack(side="left", padx=2, pady=2)

        # SÃ©lectionner la premiÃ¨re catÃ©gorie par dÃ©faut
        if cats:
            afficher_categorie(cats[0])

        btn_fermer = tk.Button(win, text="Fermer", command=win.destroy)
        self._btn_styler(btn_fermer, C_INP, C_TEXT); btn_fermer.pack(pady=4)

    def _importer_emoji(self):
        chemin = filedialog.askopenfilename(title="Importer un Ã©moji / GIF", filetypes=[("Images", "*.png *.gif *.jpg *.jpeg *.webp *.bmp"), ("Tous", "*.*")])
        if not chemin: return
        os.makedirs(EMOJI_DIR, exist_ok=True)
        nom = os.path.basename(chemin)
        import shutil
        shutil.copy2(chemin, os.path.join(EMOJI_DIR, nom))
        self._toast("ImportÃ©", f"{nom} ajoutÃ© Ã  tes Ã©mojis persos.")

    def _attacher_media(self):
        chemin = filedialog.askopenfilename(title="Attacher un mÃ©dia", filetypes=[("MÃ©dias", "*.png *.gif *.jpg *.jpeg *.mp4 *.webm *.mov *.mkv"), ("Tous", "*.*")])
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
                data = make_msg("sys", text=f"ð´ {self.pseudo} a quittÃ© le salon")
                self._diffuser(data)
        except Exception: pass
        if self.compte:
            self.compte["derniere_session"] = time.strftime("%Y-%m-%d %H:%M")
            self.gc.sauver()
        self.root.destroy()


def _fenetre_erreur_persistante(titre, tb_texte):
    """Affiche une fenetre d'erreur PERSISTANTE qui reste ouverte
    jusqu'a ce que l'utilisateur clique sur Fermer. Le traceback complet
    est visible dans une zone de texte scrollable. H24 : l'erreur ne
    disparait jamais toute seule."""
    try:
        _crash_log(tb_texte)
        sys.stderr.write(tb_texte)
    except Exception:
        pass
    try:
        root_err = tk.Tk()
        root_err.title(titre)
        root_err.geometry("680x560")
        root_err.minsize(480, 360)
        try:
            root_err.configure(bg="#1e1e2e")
        except Exception:
            pass
        try:
            root_err.iconbitmap(default="")
        except Exception:
            pass
        # Bandeau
        bandeau = tk.Frame(root_err, bg="#181825", height=64)
        bandeau.pack(fill="x", side="top")
        try:
            tk.Label(bandeau, text="⛔  " + titre, font=("Segoe UI", 15, "bold"),
                     fg="#f38ba8", bg="#181825").pack(side="left", padx=16, pady=12)
        except Exception:
            tk.Label(bandeau, text=titre, font=("Arial", 15, "bold"),
                     fg="#f38ba8", bg="#181825").pack(side="left", padx=16, pady=12)
        tk.Label(bandeau, text="Le programme a rencontre une erreur. Cette fenetre reste ouverte.\n"
                "Copie le contenu ci-dessous ou consulte lanchat_erreur.log.",
                font=("Segoe UI", 9), fg="#a6adc8", bg="#181825",
                justify="left").pack(side="left", padx=8, pady=8)
        # Zone de texte scrollable avec le traceback complet
        cadre_txt = tk.Frame(root_err, bg="#1e1e2e")
        cadre_txt.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        scrollbar = tk.Scrollbar(cadre_txt)
        scrollbar.pack(side="right", fill="y")
        txt = tk.Text(cadre_txt, wrap="word", font=("Consolas", 10),
                      bg="#11111b", fg="#f38ba8", insertbackground="#cdd6f4",
                      yscrollcommand=scrollbar.set, relief="flat", bd=0,
                      padx=12, pady=10)
        txt.pack(fill="both", expand=True)
        scrollbar.config(command=txt.yview)
        txt.insert("1.0", tb_texte)
        txt.config(state="disabled")
        # Barre de boutons
        barre_btn = tk.Frame(root_err, bg="#181825", height=52)
        barre_btn.pack(fill="x", side="bottom", padx=12, pady=(4, 12))
        def _copier():
            try:
                root_err.clipboard_clear()
                root_err.clipboard_append(tb_texte)
                btn_copier.config(text="✓ Copie !", bg="#a6e3a1")
                root_err.after(1500, lambda: btn_copier.config(text="📋 Copier", bg="#45475a"))
            except Exception:
                pass
        btn_copier = tk.Button(barre_btn, text="📋 Copier", font=("Segoe UI", 10, "bold"),
                               bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                               padx=14, pady=7, command=_copier)
        btn_copier.pack(side="left", padx=4)
        def _rouvrir():
            try:
                _crash_log(tb_texte)
                _alerter_demarrage(titre, "Erreur aussi ecrite dans lanchat_erreur.log")
            except Exception:
                pass
        btn_log = tk.Button(barre_btn, text="💾 Voir le log", font=("Segoe UI", 10, "bold"),
                            bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                            padx=14, pady=7, command=_rouvrir)
        btn_log.pack(side="left", padx=4)
        btn_fermer = tk.Button(barre_btn, text="Fermer le programme", font=("Segoe UI", 10, "bold"),
                              bg="#f38ba8", fg="#1e1e2e", relief="flat", cursor="hand2",
                              padx=14, pady=7, command=root_err.destroy)
        btn_fermer.pack(side="right", padx=4)
        # Bloque la fermeture par echap : la fenetre reste visible
        root_err.protocol("WM_DELETE_WINDOW", root_err.destroy)
        root_err.mainloop()
        return True
    except Exception:
        return False

def _install_excepthook(app_ref=None):
    """Installe un gestionnaire d'erreurs global (H24) qui intercepte
    TOUTE erreur non geree pendant l'execution et affiche la fenetre
    persistante au lieu de fermer l'application silencieusement."""
    def _hook(exc_type, exc_val, exc_tb):
        import traceback
        _tb = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        _crash_log(_tb)
        sys.stderr.write(_tb)
        # Tenter la fenetre persistante
        ok = False
        try:
            ok = _fenetre_erreur_persistante("LANchat Pro - Erreur runtime", _tb)
        except Exception:
            ok = False
        if not ok:
            _alerter_demarrage("LANchat Pro - Erreur", _tb[-1000:])
    sys.excepthook = _hook

if __name__ == "__main__":
    # Pre-installer le hook global AVANT le lancement : toute erreur
    # pendant la vie de l'app sera interceptee et affichee dans une
    # fenetre persistante (H24) au lieu de fermer silencieusement.
    _install_excepthook()
    try:
        app = LANchat()
        # Re-installer le hook avec la reference de l'app pour pouvoir
        # optionally rouvrir l'ecran si l'erreur est non fatale.
        _install_excepthook(app)
        app.root.mainloop()
    except Exception:
        import traceback
        _tb = traceback.format_exc()
        _crash_log(_tb)
        sys.stderr.write(_tb)
        # Fenetre persistante : reste ouverte jusqu'a clic sur Fermer
        ok = False
        try:
            ok = _fenetre_erreur_persistante("LANchat Pro - Erreur de demarrage", _tb)
        except Exception:
            ok = False
        if not ok:
            _alerter_demarrage("LANchat Pro - Erreur de demarrage", _tb[-1000:])