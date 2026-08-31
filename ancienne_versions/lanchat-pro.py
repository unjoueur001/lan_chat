#!/usr/bin/env python3
"""
LANchat Pro — Chat réseau complet entre utilisateurs du même Wi-Fi.
Un seul fichier, dépendances stdlib uniquement (PyAudio optionnel pour les appels
vocaux : s'il manque, les appels basculent en mode texte, tout le reste marche).

Fonctionnalités
  • Comptes locaux (pseudo + mot de passe) sauvegardés dans un petit fichier .txt
  • Système de cosmétiques : couleurs de pseudo, badges, titres, boutique aux coins
  • XP / niveaux gagnés en discutant
  • Découverte automatique des salons (UDP broadcast) + saisie IP manuelle en recours
  • Animation de chargement (spinner) pendant la recherche / connexion
  • Messages privés (MP) avec fenêtres dédiées + notifications (toast + son)
  • Appels (vocal si PyAudio, sinon texte) avec notification d'appel entrant
  • Carte de profil au clic sur un pseudo (cosmétiques, niveau, stats)
  • Architecture thread-safe (file -> thread principal pour Tkinter)

Lancement :  python3 lanchat_pro.py
"""

import os
import json
import socket
import threading
import queue
import random
import time
import hashlib
import struct
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# --- Audio (optionnel) ---
try:
    import pyaudio
    AUDIO_OK = True
except Exception:
    AUDIO_OK = False

# =====================================================================
#  Configuration
# =====================================================================
APP_NAME      = "LANchat Pro"
APP_MAGIC     = "LNCP"
TCP_PORT      = 5555
UDP_PORT      = 5556
SCAN_TIME     = 3.0
ANNOUNCE_EVERY = 2.0
MAX_PSEUDO    = 18
RECV_BUF      = 65536
COMPTE_FILE   = "comptes_lanchat.txt"   # petit fichier texte (JSON dedans)
SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# Audio
A_RATE, A_CHAN, A_FMT, A_CHUNK = 44100, 1, None, 4096   # A_FMT fixé si pyaudio

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("lanchat")

# =====================================================================
#  Cosmétiques
# =====================================================================
# (id) -> {nom, prix, ...}
COULEURS = {
    "bleu":   {"nom": "Bleu",   "hex": "#89b4fa", "prix": 0},
    "vert":   {"nom": "Vert",   "hex": "#a6e3a1", "prix": 0},
    "rouge":  {"nom": "Rouge",  "hex": "#f38ba8", "prix": 50},
    "violet": {"nom": "Violet", "hex": "#cba6f7", "prix": 80},
    "or":     {"nom": "Or",     "hex": "#f9e2af", "prix": 150},
    "cyan":   {"nom": "Cyan",   "hex": "#94e2d5", "prix": 100},
    "rose":   {"nom": "Rose",   "hex": "#f5c2e7", "prix": 120},
}
BADGES = {
    "aucun": {"nom": "Aucun",   "emoji": "",   "prix": 0},
    "etoile":{"nom": "Étoile", "emoji": "⭐", "prix": 0},
    "feu":   {"nom": "On Fire", "emoji": "🔥", "prix": 50},
    "rico":  {"nom": "Riche",  "emoji": "💎", "prix": 150},
    "vip":   {"nom": "VIP",    "emoji": "🚀", "prix": 120},
    "roi":   {"nom": "Légende","emoji": "👑", "prix": 200},
}
TITRES = {
    "membre":  {"nom": "Membre",        "prix": 0},
    "bavard":  {"nom": "Bavard",        "prix": 60},
    "veteran": {"nom": "Vétéran",       "prix": 120},
    "star":    {"nom": "Star du salon", "prix": 250},
    "pro":     {"nom": "Pro du réseau", "prix": 180},
}

COULEURS_DEFAUT = "bleu"
BADGE_DEFAUT = "etoile"
TITRE_DEFAUT = "membre"


def couleur_hex(cid):
    return COULEURS.get(cid, COULEURS[COULEURS_DEFAUT])["hex"]


def badge_emoji(bid):
    return BADGES.get(bid, BADGES[BADGE_DEFAUT])["emoji"]


def titre_nom(tid):
    return TITRES.get(tid, TITRES[TITRE_DEFAUT])["nom"]


# =====================================================================
#  Gestion des comptes (fichier .txt local)
# =====================================================================
class GestionnaireComptes:
    def __init__(self, chemin):
        self.chemin = chemin
        self.comptes = {}
        self._charger()

    def _charger(self):
        if not os.path.exists(self.chemin):
            return
        try:
            with open(self.chemin, "r", encoding="utf-8") as f:
                self.comptes = json.load(f)
        except (ValueError, OSError):
            self.comptes = {}

    def _sauver(self):
        try:
            with open(self.chemin, "w", encoding="utf-8") as f:
                json.dump(self.comptes, f, ensure_ascii=False, indent=2)
        except OSError as e:
            log.warning("Sauvegarde comptes impossible : %s", e)

    @staticmethod
    def _hash(mdp, salt):
        return hashlib.sha256((salt + mdp).encode("utf-8")).hexdigest()

    def existe(self, pseudo):
        return pseudo in self.comptes

    def creer(self, pseudo, mdp):
        if pseudo in self.comptes:
            return False, "Ce pseudo existe déjà."
        if not pseudo or len(pseudo) > MAX_PSEUDO:
            return False, f"Pseudo invalide (1 à {MAX_PSEUDO} caractères)."
        salt = os.urandom(16).hex()
        self.comptes[pseudo] = {
            "salt": salt,
            "hash": self._hash(mdp, salt),
            "coins": 100,            # bonus de bienvenue
            "xp": 0,
            "msgs": 0,
            "appels": 0,
            "possedes": {
                "couleurs": ["bleu", "vert"],
                "badges": ["aucun", "etoile"],
                "titres": ["membre"],
            },
            "equip": {
                "couleur": COULEURS_DEFAUT,
                "badge": BADGE_DEFAUT,
                "titre": TITRE_DEFAUT,
            },
        }
        self._sauver()
        return True, "Compte créé ! 100 coins de bienvenue 🎁"

    def verifier(self, pseudo, mdp):
        c = self.comptes.get(pseudo)
        if not c:
            return False, "Compte introuvable."
        if self._hash(mdp, c["salt"]) != c["hash"]:
            return False, "Mot de passe incorrect."
        return True, "ok"

    def get(self, pseudo):
        return self.comptes.get(pseudo)

    def sauver(self):
        self._sauver()


def _paliers():
    """Génère la liste cumulée des seuils de niveau : [0, 100, 215, ...]"""
    seuils = [0]
    step = 100
    total = 0
    for _ in range(200):
        total += step
        seuils.append(total)
        step = int(step * 1.15)
    return seuils

_SEUILS = _paliers()


def niveau_from_xp(xp):
    """Renvoie (niveau, xp restante avant le prochain niveau)."""
    niv = 0
    for i in range(1, len(_SEUILS)):
        if xp >= _SEUILS[i]:
            niv = i
        else:
            break
    restant = _SEUILS[niv + 1] - xp
    return niv, restant


def info_niveau(xp):
    """Renvoie (niveau, xp_dans_niveau, taille_niveau) pour afficher une barre."""
    niv = 0
    for i in range(1, len(_SEUILS)):
        if xp >= _SEUILS[i]:
            niv = i
        else:
            break
    bas = _SEUILS[niv]
    haut = _SEUILS[niv + 1]
    return niv, xp - bas, haut - bas


def profil_public(compte):
    """Renvoie le profil visible par les autres (sans le hash)."""
    niv, _ = niveau_from_xp(compte["xp"])
    return {
        "pseudo": None,           # rempli par l'appelant
        "niveau": niv,
        "xp": compte["xp"],
        "coins": compte["coins"],
        "msgs": compte["msgs"],
        "appels": compte["appels"],
        "couleur": compte["equip"]["couleur"],
        "badge": compte["equip"]["badge"],
        "titre": compte["equip"]["titre"],
    }


# =====================================================================
#  Utilitaires réseau
# =====================================================================
def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def recv_lines(sock, on_line):
    buf = b""
    try:
        while True:
            data = sock.recv(RECV_BUF)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line:
                    continue
                try:
                    on_line(json.loads(line.decode("utf-8")))
                except (ValueError, UnicodeDecodeError):
                    pass
    except OSError:
        pass


def make_msg(msg_type, **fields):
    fields["type"] = msg_type
    return (json.dumps(fields, ensure_ascii=False) + "\n").encode("utf-8")


def make_udp(msg_type, **fields):
    fields["magic"] = APP_MAGIC
    fields["type"] = msg_type
    return json.dumps(fields, ensure_ascii=False).encode("utf-8")


def parse_udp(data):
    try:
        m = json.loads(data.decode("utf-8"))
        if m.get("magic") == APP_MAGIC:
            return m
    except (ValueError, UnicodeDecodeError):
        pass
    return None


# =====================================================================
#  Audio (appel vocal, optionnel)
# =====================================================================
class AudioCall:
    """Gère un appel vocal P2P en UDP. Sans PyAudio, ne fait rien (mode texte)."""
    def __init__(self):
        self.pa = None
        self.in_stream = None
        self.out_stream = None
        self.sock = None
        self.peer = None          # (ip, port)
        self.actif = False
        self.mute = False
        self._threads = []

    def disponible(self):
        return AUDIO_OK

    def allouer(self):
        """Alloue un socket UDP (port libre) sans démarrer les flux.
        Retourne le port local ou None."""
        if not AUDIO_OK:
            return None
        if self.sock is None:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", 0))
                self.sock = s
            except OSError as e:
                log.warning("AudioCall allouer échoué : %s", e)
                return None
        return self.mon_port()

    def demarrer_streams(self, peer_ip, peer_port):
        """Ouvre les flux PyAudio et lance capture/lecture vers le pair.
        Réutilise le socket déjà alloué s'il existe."""
        if not AUDIO_OK or self.actif:
            return False
        if self.sock is None:
            self.allouer()
        try:
            global A_FMT
            if A_FMT is None:
                A_FMT = pyaudio.paInt16
            self.pa = pyaudio.PyAudio()
            self.in_stream = self.pa.open(format=A_FMT, channels=A_CHAN,
                                         rate=A_RATE, input=True,
                                         frames_per_buffer=A_CHUNK)
            self.out_stream = self.pa.open(format=A_FMT, channels=A_CHAN,
                                          rate=A_RATE, output=True,
                                          frames_per_buffer=A_CHUNK)
            self.peer = (peer_ip, peer_port)
            self.actif = True
            self.mute = False

            def capturer():
                while self.actif:
                    try:
                        data = self.in_stream.read(A_CHUNK, exception_on_overflow=False)
                        if not self.mute and self.peer:
                            self.sock.sendto(data, self.peer)
                    except OSError:
                        break

            def recevoir():
                self.sock.settimeout(1.0)
                while self.actif:
                    try:
                        data, _ = self.sock.recvfrom(A_CHUNK * 4)
                        self.out_stream.write(data)
                    except socket.timeout:
                        continue
                    except OSError:
                        break

            t1 = threading.Thread(target=capturer, daemon=True)
            t2 = threading.Thread(target=recevoir, daemon=True)
            t1.start(); t2.start()
            self._threads = [t1, t2]
            return True
        except Exception as e:
            log.warning("AudioCall streams échoué : %s", e)
            self.arreter()
            return False

    def demarrer(self, peer_ip, peer_port):
        """Alloue + démarre tout (raccourci)."""
        self.allouer()
        return self.demarrer_streams(peer_ip, peer_port)

    def mon_port(self):
        if self.sock:
            return self.sock.getsockname()[1]
        return None

    def basculer_mute(self):
        self.mute = not self.mute
        return self.mute

    def arreter(self):
        self.actif = False
        for s in (self.in_stream, self.out_stream):
            try:
                if s:
                    s.stop_stream(); s.close()
            except Exception:
                pass
        try:
            if self.pa:
                self.pa.terminate()
        except Exception:
            pass
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.in_stream = self.out_stream = self.sock = self.pa = None
        self.peer = None


# =====================================================================
#  Notifications sonores (cross-platform, best-effort)
# =====================================================================
def beep(freq=880, duree=120):
    try:
        import winsound
        winsound.Beep(freq, duree)
        return
    except Exception:
        pass
    try:
        # Linux/macOS : cloche du terminal via oss si dispo
        if os.name == "posix":
            with open("/dev/tty", "w") if os.path.exists("/dev/tty") else None as dev:
                pass
    except Exception:
        pass


def sonnerie():
    threading.Thread(target=_sonnerie_loop, daemon=True).start()

_SONNERIE_FLAG = {"stop": False}

def _sonnerie_loop():
    _SONNERIE_FLAG["stop"] = False
    for _ in range(12):
        if _SONNERIE_FLAG["stop"]:
            break
        beep(1000, 250)
        time.sleep(0.25)

def stop_sonnerie():
    _SONNERIE_FLAG["stop"] = True


# =====================================================================
#  Application principale
# =====================================================================
class LANchat:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("600x660")
        self.root.minsize(460, 520)
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.quitter)

        self.gc = GestionnaireComptes(COMPTE_FILE)
        self.compte = None            # compte connecté
        self.pseudo = ""

        self.mode = None              # "host" / "client"
        self.running = True
        self.ui_queue = queue.Queue()
        self.profils = {}             # {pseudo: profil}
        self.couleurs_tags = set()    # tags couleur déjà créés

        self.sock = None              # socket client (mode client)
        self.host_ip = None
        self.host_pseudo = None
        self.clients = []
        self.clients_lock = threading.Lock()
        self.pseudo_to_sock = {}      # mode host
        self.client_ips = {}          # {pseudo: ip}
        self.udp_sock = None
        self.tcp_server = None
        self.nb_connectes = 0

        # MP
        self.fenetres_mp = {}         # {pseudo: Toplevel}
        self.mp_non_lus = {}          # {pseudo: nb}

        # Appels
        self.appels = {}              # {peer_pseudo: AudioCall}
        self.fenetres_appel = {}      # {peer_pseudo: Toplevel}
        self.audio = AudioCall()

        # Historique MP (pour ré-afficher à l'ouverture)
        self.mp_historique = {}

        self._poll()
        self._ecran_auth()

    # -----------------------------------------------------------------
    #  Boucle UI
    # -----------------------------------------------------------------
    def _poll(self):
        try:
            while True:
                kind, *args = self.ui_queue.get_nowait()
                self._handle(kind, args)
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    def _handle(self, kind, args):
        h = {
            "msg":          lambda: self.afficher_message(args[0], args[1]),
            "sys":          lambda: self.afficher_systeme(args[0]),
            "err":          lambda: self.afficher_erreur(args[0]),
            "scan_progress":lambda: self._maj_chargement(args[0]),
            "discovered":   lambda: self._fin_scan(args[0]),
            "connected":    self._on_connecte,
            "connect_fail": lambda: self._echec_connexion(args[0]),
            "mp":           lambda: self._on_mp_recu(args[0], args[1]),
            "mp_sent_ok":    lambda: None,
            "profil":       lambda: self._maj_profil(args[0]),
            "profils_init": lambda: self._init_profils(args[0]),
            "call_incoming":lambda: self._on_appel_entrant(args[0]),
            "call_accepted":lambda: self._on_appel_accepte(args[0], args[1], args[2], args[3]),
            "call_ready":    lambda: self._on_appel_ready(args[0], args[1], args[2]),
            "call_reject":   lambda: self._on_appel_refuse(args[0]),
            "call_end":      lambda: self._on_appel_fin(args[0]),
            "appel_audio_off": lambda: self._info_appel_texte(),
            "toast":        lambda: self._toast(args[0], args[1] if len(args) > 1 else None),
            "compte_maj":    self._rafraichir_compte_ui,
        }
        f = h.get(kind)
        if f:
            f()

    # -----------------------------------------------------------------
    #  Écran d'authentification (connexion / création de compte)
    # -----------------------------------------------------------------
    def _ecran_auth(self):
        self._reset_frame()
        f = self.frame
        f.configure(bg="#1e1e2e")
        tk.Label(f, text="💬 " + APP_NAME, font=("Segoe UI", 26, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(pady=(36, 2))
        tk.Label(f, text="Compte local sécurisé", font=("Segoe UI", 11),
                 fg="#a6adc8", bg="#1e1e2e").pack(pady=(0, 24))

        cadre = tk.Frame(f, bg="#313244", highlightbackground="#45475a",
                        highlightthickness=1)
        cadre.pack(padx=40, pady=8, fill="x")

        self._auth_var = tk.StringVar(value="login")

        def toggle():
            if self._auth_var.get() == "login":
                self.btn_valider.config(text="Se connecter", bg="#89b4fa")
                self.lbl_mdp2.pack_forget(); self.ent_mdp2.pack_forget()
            else:
                self.btn_valider.config(text="Créer le compte", bg="#a6e3a1")
                self.lbl_mdp2.pack(anchor="w", padx=16, pady=(8, 0))
                self.ent_mdp2.pack(padx=16, pady=4, fill="x")

        top = tk.Frame(cadre, bg="#313244")
        top.pack(fill="x", padx=16, pady=(14, 4))
        tk.Radiobutton(top, text="Connexion", variable=self._auth_var,
                       value="login", command=toggle, bg="#313244", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#313244",
                       activeforeground="#cdd6f4", font=("Segoe UI", 10)).pack(side="left")
        tk.Radiobutton(top, text="Créer un compte", variable=self._auth_var,
                       value="creer", command=toggle, bg="#313244", fg="#cdd6f4",
                       selectcolor="#313244", activebackground="#313244",
                       activeforeground="#cdd6f4", font=("Segoe UI", 10)).pack(side="left", padx=12)

        tk.Label(cadre, text="Pseudo", font=("Segoe UI", 10), fg="#a6adc8",
                 bg="#313244").pack(anchor="w", padx=16, pady=(8, 0))
        self.ent_pseudo_auth = tk.Entry(cadre, font=("Segoe UI", 13), bg="#45475a",
                                        fg="#cdd6f4", insertbackground="#cdd6f4",
                                        relief="flat", width=24)
        self.ent_pseudo_auth.pack(padx=16, pady=4, fill="x")

        tk.Label(cadre, text="Mot de passe", font=("Segoe UI", 10), fg="#a6adc8",
                 bg="#313244").pack(anchor="w", padx=16, pady=(8, 0))
        self.ent_mdp = tk.Entry(cadre, font=("Segoe UI", 13), bg="#45475a",
                                fg="#cdd6f4", insertbackground="#cdd6f4",
                                relief="flat", width=24, show="•")
        self.ent_mdp.pack(padx=16, pady=4, fill="x")

        self.lbl_mdp2 = tk.Label(cadre, text="Confirmer le mot de passe",
                                 font=("Segoe UI", 10), fg="#a6adc8", bg="#313244")
        self.ent_mdp2 = tk.Entry(cadre, font=("Segoe UI", 13), bg="#45475a",
                                 fg="#cdd6f4", insertbackground="#cdd6f4",
                                 relief="flat", width=24, show="•")

        self.btn_valider = tk.Button(cadre, text="Se connecter",
                                     font=("Segoe UI", 12, "bold"), bg="#89b4fa",
                                     fg="#1e1e2e", relief="flat", cursor="hand2",
                                     height=2, command=self._valider_auth)
        self.btn_valider.pack(padx=16, pady=14, fill="x")

        self.ent_mdp.bind("<Return>", lambda e: self._valider_auth())
        self.ent_pseudo_auth.focus()

        info = ("🔒 Tes identifiants sont stockés localement dans "
                f"{COMPTE_FILE} (jamais envoyés sur le réseau).")
        tk.Label(f, text=info, font=("Segoe UI", 9), fg="#6c7086", bg="#1e1e2e",
                 wraplength=420, justify="center").pack(pady=(18, 0))

    def _valider_auth(self):
        pseudo = self.ent_pseudo_auth.get().strip()
        mdp = self.ent_mdp.get()
        mode = self._auth_var.get()
        if not pseudo or not mdp:
            messagebox.showwarning(APP_NAME, "Remplis le pseudo et le mot de passe.")
            return
        if mode == "creer":
            mdp2 = self.ent_mdp2.get()
            if mdp != mdp2:
                messagebox.showwarning(APP_NAME, "Les mots de passe ne correspondent pas.")
                return
            ok, msg = self.gc.creer(pseudo, mdp)
            if not ok:
                messagebox.showerror(APP_NAME, msg)
                return
            messagebox.showinfo(APP_NAME, msg)
        ok, msg = self.gc.verifier(pseudo, mdp)
        if not ok:
            messagebox.showerror(APP_NAME, msg)
            return
        self.compte = self.gc.get(pseudo)
        self.pseudo = pseudo
        self.profils[pseudo] = profil_public(self.compte)
        self.profils[pseudo]["pseudo"] = pseudo
        self._ecran_demarrage()

    # -----------------------------------------------------------------
    #  Écran de démarrage (héberger / rejoindre / boutique)
    # -----------------------------------------------------------------
    def _ecran_demarrage(self):
        self._reset_frame()
        f = self.frame
        f.configure(bg="#1e1e2e")

        barre = tk.Frame(f, bg="#313244")
        barre.pack(fill="x")
        tk.Label(barre, text=f"👤 {self.pseudo}", font=("Segoe UI", 11, "bold"),
                 fg="#cdd6f4", bg="#313244").pack(side="left", padx=14, pady=8)
        niv, _ = niveau_from_xp(self.compte["xp"])
        self.lbl_compte = tk.Label(barre, text="", font=("Segoe UI", 9),
                                   fg="#a6adc8", bg="#313244")
        self.lbl_compte.pack(side="right", padx=14, pady=8)
        self._rafraichir_compte_ui()

        tk.Label(f, text="💬 " + APP_NAME, font=("Segoe UI", 24, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(pady=(20, 2))
        tk.Label(f, text="Chat sur le même réseau Wi-Fi", font=("Segoe UI", 11),
                 fg="#a6adc8", bg="#1e1e2e").pack(pady=(0, 22))

        cadre = tk.Frame(f, bg="#313244", highlightbackground="#45475a",
                        highlightthickness=1)
        cadre.pack(padx=40, pady=8, fill="x")
        tk.Button(cadre, text="🖥️  Héberger une discussion",
                  font=("Segoe UI", 12, "bold"), bg="#89b4fa", fg="#1e1e2e",
                  relief="flat", cursor="hand2", height=2,
                  command=self.demarrer_hote).pack(padx=16, pady=(16, 6), fill="x")
        tk.Button(cadre, text="🔍  Rejoindre (auto)", font=("Segoe UI", 12, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2", height=2,
                  command=self.demarrer_rejoindre).pack(padx=16, pady=6, fill="x")
        tk.Button(cadre, text="✍️  Rejoindre par IP (dernier recours)",
                  font=("Segoe UI", 11), bg="#45475a", fg="#cdd6f4", relief="flat",
                  cursor="hand2", height=2,
                  command=self.rejoindre_ip_manuel).pack(padx=16, pady=6, fill="x")
        tk.Button(cadre, text="🛍️  Boutique & cosmétiques",
                  font=("Segoe UI", 12, "bold"), bg="#f9e2af", fg="#1e1e2e",
                  relief="flat", cursor="hand2", height=2,
                  command=self.ouvrir_boutique).pack(padx=16, pady=(6, 16), fill="x")

        tk.Label(f, text="Astuce : l'hébergeur lance le salon, les autres le "
                         "rejoignent automatiquement.",
                 font=("Segoe UI", 9), fg="#6c7086", bg="#1e1e2e",
                 wraplength=440, justify="center").pack(pady=(14, 0))

    def _rafraichir_compte_ui(self):
        if not self.compte:
            return
        niv, restant = niveau_from_xp(self.compte["xp"])
        txt = (f"Lvl {niv}  •  {self.compte['coins']} 🪙  •  {badge_emoji(self.compte['equip']['badge'])} "
               f"•  XP {self.compte['xp']} (encore {restant} au niv. suivant)")
        if hasattr(self, "lbl_compte") and self.lbl_compte.winfo_exists():
            self.lbl_compte.config(text=txt)

    # -----------------------------------------------------------------
    #  Boutique de cosmétiques
    # -----------------------------------------------------------------
    def ouvrir_boutique(self):
        win = tk.Toplevel(self.root)
        win.title("🛍️ Boutique")
        win.geometry("520x620")
        win.configure(bg="#1e1e2e")
        win.transient(self.root)
        win.grab_set()

        self.lbl_compte_bout = tk.Label(win, text="", font=("Segoe UI", 11, "bold"),
                                        fg="#f9e2af", bg="#1e1e2e")
        self.lbl_compte_bout.pack(pady=10)
        self._rafraichir_boutique(win)

        nbook = ttk.Notebook(win)
        nbook.pack(fill="both", expand=True, padx=14, pady=6)
        for cat, catalogue, equip_key in [
            ("🎨 Couleurs", COULEURS, "couleur"),
            ("🏅 Badges", BADGES, "badge"),
            ("🏷️ Titres", TITRES, "titre"),
        ]:
            page = tk.Frame(nbook, bg="#1e1e2e")
            nbook.add(page, text=cat)
            self._remplir_boutique_page(page, catalogue, equip_key, win)

    def _rafraichir_boutique(self, win):
        niv, _ = niveau_from_xp(self.compte["xp"])
        self.lbl_compte_bout.config(
            text=f"{self.pseudo}  •  Niveau {niv}  •  {self.compte['coins']} 🪙")

    def _remplir_boutique_page(self, page, catalogue, equip_key, win):
        canvas = tk.Canvas(page, bg="#1e1e2e", highlightthickness=0)
        scroll = tk.Scrollbar(page, command=canvas.yview)
        inner = tk.Frame(canvas, bg="#1e1e2e")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window(0, 0, window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        possedes = self.compte["possedes"][equip_key + "s"]
        equipe = self.compte["equip"][equip_key]
        for cid, info in catalogue.items():
            row = tk.Frame(inner, bg="#313244", highlightbackground="#45475a",
                           highlightthickness=1)
            row.pack(fill="x", padx=6, pady=5)
            # aperçu
            apercu = self._apercu_cosmetique(equip_key, cid)
            tk.Label(row, text=apercu, font=("Segoe UI", 14), bg="#313244",
                     fg="#cdd6f4", width=6).pack(side="left", padx=10, pady=8)
            tk.Label(row, text=info["nom"], font=("Segoe UI", 11, "bold"),
                     fg="#cdd6f4", bg="#313244").pack(side="left", pady=8)
            tk.Label(row, text=f"{info['prix']} 🪙", font=("Segoe UI", 10),
                     fg="#a6e3a1", bg="#313244").pack(side="left", padx=10)

            etat = ""
            if cid == equipe:
                etat = "✅ Équipé"
            elif cid in possedes:
                etat = "Possédé"
            else:
                etat = "Acheter"
            b = tk.Button(row, text=etat, font=("Segoe UI", 10, "bold"),
                          bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                          command=lambda c=cid, k=equip_key, w=win:
                          self._action_cosmetique(c, k, w))
            b.pack(side="right", padx=12, pady=8)

    def _apercu_cosmetique(self, key, cid):
        if key == "couleur":
            return "●"
        if key == "badge":
            return badge_emoji(cid) or "—"
        if key == "titre":
            return "🏷️"
        return ""

    def _action_cosmetique(self, cid, key, win):
        poss_key = key + "s"
        possedes = self.compte["possedes"][poss_key]
        if cid == self.compte["equip"][key]:
            return
        if cid in possedes:
            self.compte["equip"][key] = cid
            self.gc.sauver()
            self._rafraichir_boutique(win)
            self._rafraichir_compte_ui()
            self._propager_profil()
            messagebox.showinfo(APP_NAME, "Cosmétique équipé !")
            win.destroy()
            self.ouvrir_boutique()
            return
        prix = (COULEURS.get(cid, {}).get("prix")
                or BADGES.get(cid, {}).get("prix")
                or TITRES.get(cid, {}).get("prix", 0))
        if self.compte["coins"] < prix:
            messagebox.showwarning(APP_NAME, f"Pas assez de coins ({prix} 🪙). "
                                             "Discute pour en gagner !")
            return
        if not messagebox.askyesno(APP_NAME, f"Acheter pour {prix} 🪙 ?"):
            return
        self.compte["coins"] -= prix
        self.compte["possedes"][poss_key].append(cid)
        self.compte["equip"][key] = cid
        self.gc.sauver()
        self._rafraichir_boutique(win)
        self._rafraichir_compte_ui()
        self._propager_profil()
        messagebox.showinfo(APP_NAME, "Acheté et équipé ! 🎉")
        win.destroy()
        self.ouvrir_boutique()

    # -----------------------------------------------------------------
    #  Mode HÔTE
    # -----------------------------------------------------------------
    def demarrer_hote(self):
        self.mode = "host"
        self.host_pseudo = self.pseudo
        self._propager_profil_local()
        threading.Thread(target=self._servir_tcp, daemon=True).start()
        threading.Thread(target=self._servir_udp, daemon=True).start()
        self._construire_interface_chat()

    def _propager_profil_local(self):
        self.profils[self.pseudo] = profil_public(self.compte)
        self.profils[self.pseudo]["pseudo"] = self.pseudo

    def _servir_tcp(self):
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", TCP_PORT))
            srv.listen()
            self.tcp_server = srv
        except OSError as e:
            self.ui_queue.put(("err", f"Impossible d'héberger (port {TCP_PORT}) : {e}"))
            return
        while self.running:
            try:
                conn, addr = srv.accept()
            except OSError:
                break
            with self.clients_lock:
                self.clients.append(conn)
            threading.Thread(target=self._gerer_client,
                             args=(conn, addr), daemon=True).start()

    def _gerer_client(self, conn, addr):
        pseudo_client = None

        def on_line(m):
            nonlocal pseudo_client
            t = m.get("type")
            if t == "hello":
                pseudo_client = (m.get("pseudo") or "?")[:MAX_PSEUDO]
                prof = m.get("profil", {})
                prof["pseudo"] = pseudo_client
                self.profils[pseudo_client] = prof
                with self.clients_lock:
                    self.pseudo_to_sock[pseudo_client] = conn
                    self.client_ips[pseudo_client] = addr[0]
                self.ui_queue.put(("sys", f"🟢 {pseudo_client} a rejoint le salon"))
                self.ui_queue.put(("profil", prof))
                self._maj_compteur(1)
                # envoyer la liste des profils existants au nouveau
                liste = [p for p in self.profils.values()]
                try:
                    conn.sendall(make_msg("profils_init", profils=liste))
                except OSError:
                    pass
                # diffuser le profil du nouveau aux autres
                self._diffuser(make_msg("profil", profil=prof), except_=conn)
                self._diffuser(make_msg("sys", text=f"🟢 {pseudo_client} a rejoint"),
                               except_=conn)
            elif t == "msg":
                p = m.get("pseudo", "?")
                txt = m.get("text", "")
                self.ui_queue.put(("msg", p, txt))
                self._diffuser(make_msg("msg", pseudo=p, text=txt), except_=conn)
            elif t == "mp":
                self._router_mp(m, conn)
            elif t == "profil_update":
                prof = m.get("profil", {})
                prof["pseudo"] = pseudo_client
                self.profils[pseudo_client] = prof
                self.ui_queue.put(("profil", prof))
                self._diffuser(make_msg("profil", profil=prof), except_=conn)
            elif t == "call_request":
                self._router_appel(m, conn, addr[0])
            elif t == "call_accept":
                self._router_call_accept(m, conn)
            elif t == "call_ready":
                self._router_call_ready(m, conn)
            elif t == "call_reject":
                self._router_call_reject(m)
            elif t == "call_end":
                self._router_call_end(m, conn)
        recv_lines(conn, on_line)
        with self.clients_lock:
            if conn in self.clients:
                self.clients.remove(conn)
            if pseudo_client and self.pseudo_to_sock.get(pseudo_client) is conn:
                del self.pseudo_to_sock[pseudo_client]
            self.client_ips.pop(pseudo_client, None)
        try:
            conn.close()
        except OSError:
            pass
        if pseudo_client:
            self._maj_compteur(-1)
            self.ui_queue.put(("sys", f"🔴 {pseudo_client} a quitté le salon"))
            self._diffuser(make_msg("sys", text=f"🔴 {pseudo_client} a quitté"),
                           except_=conn)
            self.profils.pop(pseudo_client, None)

    def _diffuser(self, data, except_=None):
        with self.clients_lock:
            cibles = [c for c in self.clients if c is not except_]
        for c in cibles:
            try:
                c.sendall(data)
            except OSError:
                with self.clients_lock:
                    if c in self.clients:
                        self.clients.remove(c)

    def _maj_compteur(self, delta):
        self.nb_connectes += delta
        self.root.after(0, self._rafraichir_statut)

    # --- routage MP par le host ---
    def _router_mp(self, m, conn):
        src = m.get("from", "?")
        dest = m.get("to", "")
        txt = m.get("text", "")
        if dest == self.pseudo:
            # le host est le destinataire
            self.ui_queue.put(("mp", src, txt))
            return
        sock_dest = self.pseudo_to_sock.get(dest)
        if sock_dest:
            try:
                sock_dest.sendall(make_msg("mp", from_=src, text=txt))
            except OSError:
                pass
        else:
            try:
                conn.sendall(make_msg("sys", text=f"⚠ {dest} est introuvable."))
            except OSError:
                pass

    # --- routage des appels par le host ---
    def _router_appel(self, m, conn, src_ip):
        src = m.get("from", "?")
        dest = m.get("to", "")
        if dest == self.pseudo:
            self.ui_queue.put(("call_incoming", src))
            return
        sock_dest = self.pseudo_to_sock.get(dest)
        if sock_dest:
            try:
                sock_dest.sendall(make_msg("call_incoming", from_=src))
            except OSError:
                conn.sendall(make_msg("call_reject", from_=dest))
        else:
            conn.sendall(make_msg("call_reject", from_=dest))

    def _router_call_accept(self, m, conn):
        src = m.get("from", "?")
        dest = m.get("to", "")
        audio_ip = m.get("audio_ip")
        audio_port = m.get("audio_port")
        if dest == self.pseudo:
            self.ui_queue.put(("call_accepted", src, audio_ip, audio_port))
            return
        # ajouter l'IP du dest (connue du host) au message relayé
        dest_ip = self.client_ips.get(dest)
        sock_dest = self.pseudo_to_sock.get(dest)
        if sock_dest:
            sock_dest.sendall(make_msg("call_accepted", from_=src,
                                       audio_ip=audio_ip, audio_port=audio_port))

    def _router_call_ready(self, m, conn):
        src = m.get("from", "?")
        dest = m.get("to", "")
        audio_ip = m.get("audio_ip")
        audio_port = m.get("audio_port")
        if dest == self.pseudo:
            self.ui_queue.put(("call_ready", src, audio_ip, audio_port))
            return
        sock_dest = self.pseudo_to_sock.get(dest)
        if sock_dest:
            sock_dest.sendall(make_msg("call_ready", from_=src,
                                       audio_ip=audio_ip, audio_port=audio_port))

    def _router_call_reject(self, m):
        dest = m.get("to", m.get("from", ""))
        if dest == self.pseudo:
            self.ui_queue.put(("call_reject", m.get("from", "?")))
        else:
            sock_dest = self.pseudo_to_sock.get(dest)
            if sock_dest:
                sock_dest.sendall(make_msg("call_reject", from_=m.get("from", "?")))

    def _router_call_end(self, m, conn):
        dest = m.get("to", "")
        src = m.get("from", "?")
        if dest == self.pseudo:
            self.ui_queue.put(("call_end", src))
        else:
            sock_dest = self.pseudo_to_sock.get(dest)
            if sock_dest:
                sock_dest.sendall(make_msg("call_end", from_=src))

    def _servir_udp(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("0.0.0.0", UDP_PORT))
            self.udp_sock = s
        except OSError as e:
            log.warning("UDP indisponible : %s", e)
            return
        annonce = make_udp("announce", port=TCP_PORT, name=APP_NAME,
                           host_pseudo=self.pseudo)
        prochaine = time.time()
        while self.running:
            try:
                s.settimeout(0.5)
                data, addr = s.recvfrom(4096)
            except socket.timeout:
                if time.time() >= prochaine:
                    try:
                        s.sendto(annonce, ("255.255.255.255", UDP_PORT))
                    except OSError:
                        pass
                    prochaine = time.time() + ANNOUNCE_EVERY
                continue
            except OSError:
                break
            msg = parse_udp(data)
            if msg and msg.get("type") == "discover":
                try:
                    s.sendto(annonce, addr)
                except OSError:
                    pass

    # -----------------------------------------------------------------
    #  Mode REJOINDRE (découverte + IP manuelle)
    # -----------------------------------------------------------------
    def demarrer_rejoindre(self):
        self.mode = "client"
        self._ecran_chargement("Recherche des discussions sur le réseau…")
        threading.Thread(target=self._scan_reseau, daemon=True).start()

    def rejoindre_ip_manuel(self):
        ip = simpledialog.askstring("Connexion manuelle",
                                    "Adresse IP de l'hébergeur :", parent=self.root)
        if not ip:
            return
        ip = ip.strip()
        self.mode = "client"
        self.cible = (ip, TCP_PORT, f"{ip}:{TCP_PORT}")
        self._ecran_chargement(f"Connexion à {ip}:{TCP_PORT}…")
        threading.Thread(target=self._connecter_a, args=(ip, TCP_PORT),
                         daemon=True).start()

    def _scan_reseau(self):
        trouve = {}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("0.0.0.0", UDP_PORT))
        except OSError as e:
            self.ui_queue.put(("connect_fail", f"Scan impossible : {e}"))
            return
        try:
            s.sendto(make_udp("discover"), ("255.255.255.255", UDP_PORT))
        except OSError:
            pass
        echeance = time.time() + SCAN_TIME
        while time.time() < echeance and self.running:
            try:
                s.settimeout(0.4)
                data, addr = s.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            msg = parse_udp(data)
            if not msg or msg.get("type") != "announce":
                continue
            ip = addr[0]
            port = int(msg.get("port", TCP_PORT))
            nom = msg.get("name", f"{ip}:{port}")
            hp = msg.get("host_pseudo", "")
            cle = (ip, port)
            if cle not in trouve:
                trouve[cle] = (nom, hp)
                self.ui_queue.put(("scan_progress", len(trouve)))
        try:
            s.close()
        except OSError:
            pass
        serveurs = [(ip, port, nom, hp) for (ip, port), (nom, hp) in trouve.items()]
        self.ui_queue.put(("discovered", serveurs))

    def _ecran_chargement(self, texte):
        self._reset_frame()
        f = self.frame
        f.configure(bg="#1e1e2e")
        self.lbl_spinner = tk.Label(f, text="⠋", font=("Segoe UI", 42),
                                    fg="#89b4fa", bg="#1e1e2e")
        self.lbl_spinner.pack(pady=(120, 8))
        self.lbl_chargement = tk.Label(f, text=texte, font=("Segoe UI", 12),
                                       fg="#cdd6f4", bg="#1e1e2e")
        self.lbl_chargement.pack(pady=4)
        self.lbl_compteur = tk.Label(f, text="0 salon trouvé", font=("Segoe UI", 10),
                                     fg="#a6e3a1", bg="#1e1e2e")
        self.lbl_compteur.pack(pady=2)
        self._spin_idx = 0
        self._animer_spinner()
        tk.Button(f, text="Annuler", font=("Segoe UI", 10), bg="#45475a",
                  fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self._ecran_demarrage).pack(pady=30)

    def _animer_spinner(self):
        if hasattr(self, "lbl_spinner") and self.lbl_spinner.winfo_exists():
            self.lbl_spinner.config(text=SPINNER[self._spin_idx % len(SPINNER)])
            self._spin_idx += 1
            self.root.after(90, self._animer_spinner)

    def _maj_chargement(self, n):
        if hasattr(self, "lbl_compteur") and self.lbl_compteur.winfo_exists():
            pluriel = "s" if n != 1 else ""
            self.lbl_compteur.config(text=f"{n} salon{pluriel} trouvé{pluriel}")

    def _fin_scan(self, serveurs):
        if not serveurs:
            self._reset_frame()
            f = self.frame
            f.configure(bg="#1e1e2e")
            tk.Label(f, text="😕", font=("Segoe UI", 40), bg="#1e1e2e").pack(pady=(110, 4))
            tk.Label(f, text="Aucune discussion trouvée", font=("Segoe UI", 13, "bold"),
                     fg="#cdd6f4", bg="#1e1e2e").pack(pady=4)
            tk.Label(f, text="Demande à un ami de lancer un salon, ou héberge le tien !",
                     font=("Segoe UI", 10), fg="#a6adc8", bg="#1e1e2e",
                     wraplength=380).pack(pady=6)
            tk.Button(f, text="🖥️  Héberger à la place", font=("Segoe UI", 11, "bold"),
                      bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                      command=self.demarrer_hote).pack(pady=18)
            tk.Button(f, text="✍️  Saisir l'IP manuellement", font=("Segoe UI", 10),
                      bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                      command=self.rejoindre_ip_manuel).pack(pady=4)
            tk.Button(f, text="↩ Recommencer", font=("Segoe UI", 10), bg="#45475a",
                      fg="#cdd6f4", relief="flat", cursor="hand2",
                      command=self.demarrer_rejoindre).pack()
            return
        self._ecran_choix_serveur(serveurs)

    def _ecran_choix_serveur(self, serveurs):
        self._reset_frame()
        f = self.frame
        f.configure(bg="#1e1e2e")
        tk.Label(f, text="Salons disponibles", font=("Segoe UI", 16, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(pady=(30, 14))
        liste = tk.Listbox(f, font=("Segoe UI", 12), bg="#313244", fg="#cdd6f4",
                          selectbackground="#89b4fa", selectforeground="#1e1e2e",
                          relief="flat", bd=0, highlightbackground="#45475a",
                          height=min(len(serveurs), 10), activestyle="none")
        for ip, port, nom, hp in serveurs:
            lib = f"  {nom}"
            if hp:
                lib += f"   (chez {hp})"
            lib += f"   —   {ip}:{port}"
            liste.insert(tk.END, lib)
        liste.pack(padx=40, pady=6, fill="x")
        liste.selection_set(0)

        def connecter():
            sel = liste.curselection()
            if not sel:
                messagebox.showinfo(APP_NAME, "Choisis un salon.")
                return
            ip, port, nom, hp = serveurs[sel[0]]
            self.cible = (ip, port, nom)
            self._ecran_chargement(f"Connexion à {nom} ({ip})…")
            threading.Thread(target=self._connecter_a, args=(ip, port),
                             daemon=True).start()
        tk.Button(f, text="Se connecter", font=("Segoe UI", 12, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=connecter).pack(pady=16)
        tk.Button(f, text="✍️  IP manuelle", font=("Segoe UI", 10), bg="#45475a",
                  fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self.rejoindre_ip_manuel).pack()

    def _connecter_a(self, ip, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((ip, port))
            s.settimeout(None)
            self.host_ip = ip
            self._propager_profil_local()
            s.sendall(make_msg("hello", pseudo=self.pseudo,
                               profil=profil_public(self.compte)))
            self.sock = s
            threading.Thread(target=self._boucle_reception, daemon=True).start()
            self.ui_queue.put(("connected",))
        except OSError as e:
            self.ui_queue.put(("connect_fail", f"Connexion échouée : {e}"))

    def _on_connecte(self):
        self._construire_interface_chat()

    def _echec_connexion(self, msg):
        messagebox.showerror(APP_NAME, msg)
        self._ecran_demarrage()

    def _boucle_reception(self):
        def on_line(m):
            t = m.get("type")
            if t == "msg":
                self.ui_queue.put(("msg", m.get("pseudo", "?"), m.get("text", "")))
            elif t == "sys":
                self.ui_queue.put(("sys", m.get("text", "")))
            elif t == "mp":
                self.ui_queue.put(("mp", m.get("from_", "?"), m.get("text", "")))
            elif t == "profil":
                self.ui_queue.put(("profil", m.get("profil", {})))
            elif t == "profils_init":
                self.ui_queue.put(("profils_init", m.get("profils", [])))
            elif t == "call_incoming":
                self.ui_queue.put(("call_incoming", m.get("from_", "?")))
            elif t == "call_accepted":
                self.ui_queue.put(("call_accepted", m.get("from_", "?"),
                                  m.get("audio_ip"), m.get("audio_port")))
            elif t == "call_ready":
                self.ui_queue.put(("call_ready", m.get("from_", "?"),
                                  m.get("audio_ip"), m.get("audio_port")))
            elif t == "call_reject":
                self.ui_queue.put(("call_reject", m.get("from_", "?")))
            elif t == "call_end":
                self.ui_queue.put(("call_end", m.get("from_", "?")))
        recv_lines(self.sock, on_line)
        self.ui_queue.put(("err", "Connexion perdue avec le serveur."))

    # -----------------------------------------------------------------
    #  Interface de chat
    # -----------------------------------------------------------------
    def _construire_interface_chat(self):
        self._reset_frame()
        f = self.frame
        f.configure(bg="#1e1e2e")

        barre = tk.Frame(f, bg="#313244")
        barre.pack(fill="x")
        tk.Label(barre, text="💬 " + APP_NAME, font=("Segoe UI", 12, "bold"),
                 fg="#cdd6f4", bg="#313244").pack(side="left", padx=14, pady=8)
        self.lbl_statut = tk.Label(barre, text="", font=("Segoe UI", 9),
                                   fg="#a6adc8", bg="#313244")
        self.lbl_statut.pack(side="right", padx=14, pady=8)
        self._rafraichir_statut()

        # Panneau de droite : liste des pseudos connectés
        corps = tk.Frame(f, bg="#1e1e2e")
        corps.pack(fill="both", expand=True, padx=8, pady=8)

        cadre_msg = tk.Frame(corps, bg="#1e1e2e")
        cadre_msg.pack(side="left", fill="both", expand=True)
        scroll = tk.Scrollbar(cadre_msg)
        scroll.pack(side="right", fill="y")
        self.zone = tk.Text(cadre_msg, font=("Segoe UI", 11), bg="#181825",
                           fg="#cdd6f4", insertbackground="#cdd6f4",
                           yscrollcommand=scroll.set, relief="flat", bd=0,
                           padx=12, pady=10, wrap="word", state="disabled")
        self.zone.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.zone.yview)
        self.zone.tag_config("sys", foreground="#6c7086",
                             font=("Segoe UI", 9, "italic"))
        self.zone.tag_config("erreur", foreground="#f38ba8",
                             font=("Segoe UI", 10, "bold"))
        self.zone.tag_config("moi", foreground="#89b4fa",
                             font=("Segoe UI", 11, "bold"))
        self.zone.tag_config("moi_texte", foreground="#cdd6f4",
                             font=("Segoe UI", 11))
        self.zone.tag_config("autre_texte", foreground="#bac2de",
                             font=("Segoe UI", 11))
        # cliquable
        self.zone.tag_bind("pseudo", "<Button-1>", self._clic_pseudo_event)

        # Liste participants
        panneau_d = tk.Frame(corps, bg="#181825", width=150)
        panneau_d.pack(side="right", fill="y", padx=(8, 0))
        panneau_d.pack_propagate(False)
        tk.Label(panneau_d, text="Participants", font=("Segoe UI", 9, "bold"),
                 fg="#a6adc8", bg="#181825").pack(pady=(8, 4))
        self.liste_part = tk.Text(panneau_d, bg="#181825", fg="#cdd6f4",
                                  relief="flat", bd=0, font=("Segoe UI", 10),
                                  wrap="none", cursor="hand2", height=20)
        self.liste_part.pack(fill="both", expand=True, padx=6)
        self.liste_part.tag_bind("p", "<Button-1>", self._clic_pseudo_liste)
        self._rafraichir_liste_participants()

        # Saisie
        barre_saisie = tk.Frame(f, bg="#1e1e2e")
        barre_saisie.pack(fill="x", padx=8, pady=(0, 8))
        self.entree = tk.Entry(barre_saisie, font=("Segoe UI", 12), bg="#313244",
                               fg="#cdd6f4", insertbackground="#cdd6f4",
                               relief="flat", bd=0)
        self.entree.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entree.bind("<Return>", lambda e: self.envoyer())
        self.entree.focus()
        tk.Button(barre_saisie, text="Envoyer ➤", font=("Segoe UI", 11, "bold"),
                  bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2", padx=14,
                  command=self.envoyer).pack(side="left", ipady=4)
        tk.Button(barre_saisie, text="🛍️", font=("Segoe UI", 12), bg="#45475a",
                  fg="#f9e2af", relief="flat", cursor="hand2", padx=10,
                  command=self.ouvrir_boutique).pack(side="left", padx=(8, 0), ipady=4)

        self.afficher_systeme(f"🟢 Bienvenue {self.pseudo} !")
        if self.mode == "host":
            self.afficher_systeme(f"Tu héberges sur {local_ip()}:{TCP_PORT}. "
                                  f"Partage cette IP si l'auto-découverte échoue.")
        if not AUDIO_OK:
            self.afficher_systeme("ℹ Appels vocaux indisponibles (installe PyAudio pour "
                                   "les activer). Les appels fonctionnent en mode texte.")

    def _rafraichir_statut(self):
        if not hasattr(self, "lbl_statut") or not self.lbl_statut.winfo_exists():
            return
        if self.mode == "host":
            self.lbl_statut.config(
                text=f"🟢 Hébergé sur {local_ip()}:{TCP_PORT}  •  "
                     f"{self.nb_connectes} connecté(s) en plus de toi")
        elif self.cible:
            ip, port, nom = self.cible
            self.lbl_statut.config(text=f"🔵 Connecté à {nom} ({ip}:{port})")

    def _rafraichir_liste_participants(self):
        if not hasattr(self, "liste_part"):
            return
        self.liste_part.config(state="normal")
        self.liste_part.delete("1.0", tk.END)
        for p in self.profils:
            prof = self.profils[p]
            badge = badge_emoji(prof.get("badge", "etoile"))
            ligne = f" {badge} {p}\n"
            self.liste_part.insert(tk.END, ligne, "p")
            debut = self.liste_part.index("end-1c linestart")
            # tag sur le pseudo seulement : on retag toute la ligne pour simplicité
        self.liste_part.config(state="disabled")

    def _clic_pseudo_liste(self, event=None):
        idx = self.liste_part.index("@%d,%d" % (event.x, event.y))
        ligne = int(idx.split(".")[0])
        pseudos = list(self.profils.keys())
        if 1 <= ligne <= len(pseudos):
            self._ouvrir_carte_profil(pseudos[ligne - 1])

    def _clic_pseudo_event(self, event):
        # cherche un tag "usr_<pseudo>" sous le curseur
        idx = self.zone.index("@%d,%d" % (event.x, event.y))
        for t in self.zone.tag_names(idx):
            if t.startswith("usr_"):
                self._ouvrir_carte_profil(t[4:])
                return

    # -----------------------------------------------------------------
    #  Profils
    # -----------------------------------------------------------------
    def _maj_profil(self, prof):
        p = prof.get("pseudo")
        if not p:
            return
        self.profils[p] = prof
        self._rafraichir_liste_participants()

    def _init_profils(self, liste):
        for prof in liste:
            p = prof.get("pseudo")
            if p:
                self.profils[p] = prof
        self._rafraichir_liste_participants()

    def _propager_profil(self):
        """Met à jour son propre profil et le diffuse aux autres."""
        self._propager_profil_local()
        prof = self.profils[self.pseudo]
        data = make_msg("profil_update", profil=prof)
        if self.mode == "host":
            self._diffuser(data)
        elif self.sock:
            try:
                self.sock.sendall(data)
            except OSError:
                pass

    def _couleur_tag(self, pseudo):
        prof = self.profils.get(pseudo, {})
        cid = prof.get("couleur", COULEURS_DEFAUT)
        couleur = couleur_hex(cid)
        tag = "usr_" + pseudo
        if tag not in self.couleurs_tags and hasattr(self, "zone"):
            self.zone.tag_config(tag, foreground=couleur,
                                 font=("Segoe UI", 11, "bold"))
            self.couleurs_tags.add(tag)
        return tag

    # -----------------------------------------------------------------
    #  Carte de profil (au clic sur un pseudo)
    # -----------------------------------------------------------------
    def _ouvrir_carte_profil(self, pseudo):
        prof = self.profils.get(pseudo, {"pseudo": pseudo, "niveau": 0,
                                         "titre": TITRE_DEFAUT, "badge": "etoile",
                                         "couleur": COULEURS_DEFAUT, "msgs": 0,
                                         "coins": 0, "appels": 0, "xp": 0})
        win = tk.Toplevel(self.root)
        win.title("Profil")
        win.geometry("340x420")
        win.configure(bg="#1e1e2e")
        win.transient(self.root)

        en_tete = tk.Frame(win, bg="#313244")
        en_tete.pack(fill="x")
        badge = badge_emoji(prof.get("badge", "etoile"))
        couleur = couleur_hex(prof.get("couleur", COULEURS_DEFAUT))
        tk.Label(en_tete, text=f"{badge} {pseudo}", font=("Segoe UI", 20, "bold"),
                 fg=couleur, bg="#313244").pack(pady=(18, 0))
        tk.Label(en_tete, text="« " + titre_nom(prof.get("titre", "membre")) + " »",
                 font=("Segoe UI", 11, "italic"), fg="#a6adc8", bg="#313244").pack()
        niv, xp_dans, taille = info_niveau(prof.get("xp", 0))
        tk.Label(en_tete, text=f"Niveau {niv}", font=("Segoe UI", 13, "bold"),
                 fg="#f9e2af", bg="#313244").pack(pady=(8, 2))
        # barre XP
        barre_xp = tk.Frame(en_tete, bg="#45475a", height=10)
        barre_xp.pack(fill="x", padx=40, pady=(0, 12))
        progress = (xp_dans / taille) if taille else 0
        tk.Frame(barre_xp, bg="#a6e3a1").place(x=0, y=0, relwidth=progress, relheight=1)
        tk.Label(en_tete, text=f"{xp_dans}/{taille} XP", font=("Segoe UI", 8),
                 fg="#6c7086", bg="#313244").pack(pady=(0, 12))

        corps = tk.Frame(win, bg="#1e1e2e")
        corps.pack(fill="both", expand=True, padx=16, pady=12)
        stats = [
            ("💬 Messages", prof.get("msgs", 0)),
            ("🪙 Coins", prof.get("coins", 0)),
            ("📞 Appels", prof.get("appels", 0)),
            ("✨ XP", prof.get("xp", 0)),
        ]
        for lib, val in stats:
            row = tk.Frame(corps, bg="#1e1e2e")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=lib, font=("Segoe UI", 11), fg="#cdd6f4",
                     bg="#1e1e2e").pack(side="left")
            tk.Label(row, text=str(val), font=("Segoe UI", 11, "bold"),
                     fg="#a6e3a1", bg="#1e1e2e").pack(side="right")

        tk.Label(corps, text="Cosmétiques équipés", font=("Segoe UI", 10, "bold"),
                 fg="#a6adc8", bg="#1e1e2e").pack(anchor="w", pady=(12, 4))
        tk.Label(corps, text=f"🎨 Couleur : {COULEURS.get(prof.get('couleur'),{}).get('nom','?')}\n"
                             f"🏅 Badge : {BADGES.get(prof.get('badge'),{}).get('nom','?')}\n"
                             f"🏷️ Titre : {titre_nom(prof.get('titre','membre'))}",
                 font=("Segoe UI", 10), fg="#cdd6f4", bg="#1e1e2e",
                 justify="left").pack(anchor="w")

        if pseudo != self.pseudo:
            btns = tk.Frame(win, bg="#1e1e2e")
            btns.pack(pady=12)
            tk.Button(btns, text="✉ MP", font=("Segoe UI", 11, "bold"),
                      bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                      command=lambda: self._ouvrir_fenetre_mp(pseudo)).pack(side="left", padx=6)
            tk.Button(btns, text="📞 Appeler", font=("Segoe UI", 11, "bold"),
                      bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                      command=lambda: self._demarrer_appel(pseudo)).pack(side="left", padx=6)

    # -----------------------------------------------------------------
    #  Envoi de messages publics
    # -----------------------------------------------------------------
    def envoyer(self):
        texte = self.entree.get().strip()
        if not texte:
            return
        self.entree.delete(0, tk.END)
        data = make_msg("msg", pseudo=self.pseudo, text=texte)
        if self.mode == "host":
            self._diffuser(data)
        else:
            try:
                self.sock.sendall(data)
            except OSError:
                self.afficher_erreur("Connexion perdue : message non envoyé.")
                return
        # XP + coins locaux
        self._gagner_xp(1, coins=1, msgs=1)
        self.afficher_message(self.pseudo, texte, moi=True)
        # mention ?
        for mot in texte.split():
            if mot.startswith("@") and mot[1:] in self.profils and mot[1:] != self.pseudo:
                self._toast(f"🏷️ Tu as mentionné {mot[1:]}", None)

    def _gagner_xp(self, xp, coins=0, msgs=0, appels=0):
        ancien_niv, _ = niveau_from_xp(self.compte["xp"])
        self.compte["xp"] += xp
        self.compte["coins"] += coins
        self.compte["msgs"] += msgs
        self.compte["appels"] += appels
        nouveau_niv, _ = niveau_from_xp(self.compte["xp"])
        self.gc.sauver()
        self._rafraichir_compte_ui()
        self._propager_profil_local()
        if nouveau_niv > ancien_niv:
            self._toast(f"🎉 Niveau {nouveau_niv} atteint ! +50 🪙", None)
            self.compte["coins"] += 50
            self.gc.sauver()
            self._rafraichir_compte_ui()
            beep(1200, 200)

    # -----------------------------------------------------------------
    #  Affichage
    # -----------------------------------------------------------------
    def afficher_message(self, pseudo, texte, moi=False):
        if not hasattr(self, "zone"):
            return
        prof = self.profils.get(pseudo, {})
        badge = badge_emoji(prof.get("badge", "etoile"))
        self.zone.config(state="normal")
        prefixe = f"{badge} [{pseudo}]"
        if moi:
            self.zone.insert(tk.END, prefixe, "moi")
        else:
            debut = self.zone.index("end")
            self.zone.insert(tk.END, prefixe)
            self.zone.tag_add(self._couleur_tag(pseudo), debut, "end")
            self.zone.tag_add("pseudo", debut, "end")
        self.zone.insert(tk.END, f"  {texte}\n", "moi_texte" if moi else "autre_texte")
        self.zone.config(state="disabled")
        self.zone.see(tk.END)

    def afficher_systeme(self, texte):
        if not hasattr(self, "zone"):
            return
        self.zone.config(state="normal")
        self.zone.insert(tk.END, texte + "\n", "sys")
        self.zone.config(state="disabled")
        self.zone.see(tk.END)

    def afficher_erreur(self, texte):
        if not hasattr(self, "zone"):
            return
        self.zone.config(state="normal")
        self.zone.insert(tk.END, "⚠ " + texte + "\n", "erreur")
        self.zone.config(state="disabled")
        self.zone.see(tk.END)

    # -----------------------------------------------------------------
    #  Messages privés (MP)
    # -----------------------------------------------------------------
    def _ouvrir_fenetre_mp(self, dest):
        if dest in self.fenetres_mp and self.fenetres_mp[dest].winfo_exists():
            self.fenetres_mp[dest].lift()
            self.fenetres_mp[dest].focus_set()
            return
        win = tk.Toplevel(self.root)
        win.title(f"MP avec {dest}")
        win.geometry("400x420")
        win.configure(bg="#1e1e2e")
        win.transient(self.root)

        tk.Label(win, text=f"🔒 Conversation privée avec {dest}",
                 font=("Segoe UI", 11, "bold"), fg="#cdd6f4", bg="#1e1e2e").pack(pady=8)

        scroll = tk.Scrollbar(win)
        scroll.pack(side="right", fill="y")
        txt = tk.Text(win, font=("Segoe UI", 11), bg="#181825", fg="#cdd6f4",
                     yscrollcommand=scroll.set, relief="flat", bd=0,
                     padx=10, pady=10, wrap="word", state="disabled")
        txt.pack(fill="both", expand=True, padx=8, pady=4)
        scroll.config(command=txt.yview)
        win.txt = txt   # référence robuste pour les réceptions
        win.entree = entree_mp

        entree_mp = tk.Entry(win, font=("Segoe UI", 12), bg="#313244", fg="#cdd6f4",
                             insertbackground="#cdd6f4", relief="flat", bd=0)
        entree_mp.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8, ipady=6)

        def envoyer_mp(e=None):
            texte = entree_mp.get().strip()
            if not texte:
                return
            entree_mp.delete(0, tk.END)
            self._envoyer_mp(dest, texte)
            self._afficher_mp_local(dest, texte, win, txt)

        entree_mp.bind("<Return>", envoyer_mp)
        tk.Button(win, text="➤", font=("Segoe UI", 12, "bold"), bg="#89b4fa",
                  fg="#1e1e2e", relief="flat", cursor="hand2", padx=14,
                  command=envoyer_mp).pack(side="left", padx=(0, 8), pady=8, ipady=6)

        # réafficher l'historique
        for src, msg in self.mp_historique.get(dest, []):
            self._afficher_mp(dest, src, msg, win, txt, animate=False)

        win.protocol("WM_DELETE_WINDOW", lambda: self._fermer_fenetre_mp(dest, win))
        self.fenetres_mp[dest] = win
        self.mp_non_lus[dest] = 0

    def _fermer_fenetre_mp(self, dest, win):
        win.destroy()
        self.fenetres_mp.pop(dest, None)

    def _envoyer_mp(self, dest, texte):
        if self.mode == "host":
            # le host envoie directement si dest est un client, sinon local
            data = make_msg("mp", from_=self.pseudo, to=dest, text=texte)
            if dest == self.pseudo:
                return
            sock_dest = self.pseudo_to_sock.get(dest)
            if sock_dest:
                try:
                    sock_dest.sendall(make_msg("mp", from_=self.pseudo, text=texte))
                except OSError:
                    self.afficher_erreur(f"MP vers {dest} échoué.")
            else:
                self.afficher_erreur(f"{dest} est introuvable.")
        else:
            try:
                self.sock.sendall(make_msg("mp", from_=self.pseudo, to=dest, text=texte))
            except OSError:
                self.afficher_erreur("MP non envoyé (connexion perdue).")
        self._gagner_xp(2, coins=1)

    def _afficher_mp_local(self, dest, texte, win, txt):
        self._afficher_mp(dest, self.pseudo, texte, win, txt, moi=True)

    def _afficher_mp(self, dest, src, texte, win, txt, moi=False, animate=True):
        txt.config(state="normal")
        couleur = "#89b4fa" if moi else couleur_hex(
            self.profils.get(src, {}).get("couleur", COULEURS_DEFAUT))
        tag = f"mp_{src}_{id(win)}"
        txt.tag_config(tag, foreground=couleur, font=("Segoe UI", 11, "bold"))
        txt.insert(tk.END, f"[{src}] ", tag)
        txt.insert(tk.END, f"{texte}\n", "moi_texte" if moi else "autre_texte")
        txt.config(state="disabled")
        txt.see(tk.END)

    def _on_mp_recu(self, src, texte):
        # historique
        self.mp_historique.setdefault(src, []).append((src, texte))
        if src in self.fenetres_mp and self.fenetres_mp[src].winfo_exists():
            win = self.fenetres_mp[src]
            self._afficher_mp(src, src, texte, win, win.txt)
            win.lift()
        else:
            self.mp_non_lus[src] = self.mp_non_lus.get(src, 0) + 1
        beep(1000, 100)
        self._toast(f"✉ MP de {src} : {texte[:30]}",
                    lambda: self._ouvrir_fenetre_mp(src))

    # -----------------------------------------------------------------
    #  Appels (vocal si PyAudio, sinon texte)
    # -----------------------------------------------------------------
    def _demarrer_appel(self, dest):
        if dest == self.pseudo:
            return
        if dest in self.appels:
            messagebox.showinfo(APP_NAME, "Un appel est déjà en cours avec cette personne.")
            return
        if dest in self.fenetres_appel and self.fenetres_appel[dest].winfo_exists():
            return
        # envoyer la demande
        if self.mode == "host":
            if dest == self.pseudo:
                return
            sock_dest = self.pseudo_to_sock.get(dest)
            if not sock_dest:
                self.afficher_erreur(f"{dest} est introuvable.")
                return
            try:
                sock_dest.sendall(make_msg("call_incoming", from_=self.pseudo))
            except OSError:
                self.afficher_erreur("Demande d'appel échouée.")
        else:
            try:
                self.sock.sendall(make_msg("call_request", from_=self.pseudo, to=dest))
            except OSError:
                self.afficher_erreur("Demande d'appel échouée.")
                return
        self._ouvrir_fenetre_appel(dest, appelant=True)

    def _ouvrir_fenetre_appel(self, peer, appelant=False):
        win = tk.Toplevel(self.root)
        win.title(f"Appel avec {peer}")
        win.geometry("340x380")
        win.configure(bg="#1e1e2e")
        win.transient(self.root)

        tk.Label(win, text="📞", font=("Segoe UI", 40), bg="#1e1e2e",
                 fg="#a6e3a1").pack(pady=(20, 4))
        self.lbl_appel_peer = tk.Label(win, text=peer, font=("Segoe UI", 16, "bold"),
                                       fg="#cdd6f4", bg="#1e1e2e")
        self.lbl_appel_peer.pack()
        self.lbl_appel_statut = tk.Label(win, text="En attente…",
                                        font=("Segoe UI", 11), fg="#a6adc8",
                                        bg="#1e1e2e")
        self.lbl_appel_statut.pack(pady=4)
        self.lbl_duree = tk.Label(win, text="00:00", font=("Segoe UI", 12, "bold"),
                                  fg="#a6e3a1", bg="#1e1e2e")
        self.lbl_duree.pack(pady=4)

        btns = tk.Frame(win, bg="#1e1e2e")
        btns.pack(pady=18)
        self.btn_mute = tk.Button(btns, text="🔇 Muet", font=("Segoe UI", 10, "bold"),
                                  bg="#45475a", fg="#cdd6f4", relief="flat",
                                  cursor="hand2", command=self._toggle_mute)
        self.btn_mute.pack(side="left", padx=6)
        tk.Button(btns, text="📵 Raccrocher", font=("Segoe UI", 10, "bold"),
                  bg="#f38ba8", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=lambda: self._raccrocher(peer)).pack(side="left", padx=6)

        if not AUDIO_OK:
            tk.Label(win, text="Mode texte (PyAudio absent)\n— parle via le mini-chat ci-dessous —",
                     font=("Segoe UI", 9), fg="#6c7086", bg="#1e1e2e",
                     justify="center").pack(pady=(0, 4))
            ent = tk.Entry(win, font=("Segoe UI", 11), bg="#313244", fg="#cdd6f4",
                           insertbackground="#cdd6f4", relief="flat", bd=0)
            ent.pack(fill="x", padx=16, pady=4, ipady=5)
            ent.bind("<Return>", lambda e: self._appel_mini_msg(peer, ent))

        self._appel_start = None
        win.protocol("WM_DELETE_WINDOW", lambda: self._raccrocher(peer))
        self.fenetres_appel[peer] = win

    def _toggle_mute(self):
        if self.audio.actif:
            muet = self.audio.basculer_mute()
            self.btn_mute.config(text="🔇 Muet (ON)" if muet else "🔇 Muet")

    def _appel_mini_msg(self, peer, ent):
        texte = ent.get().strip()
        if not texte:
            return
        ent.delete(0, tk.END)
        self._envoyer_mp(peer, f"[appel] {texte}")

    def _on_appel_entrant(self, src):
        sonnerie()
        win = tk.Toplevel(self.root)
        win.title("Appel entrant")
        win.geometry("320x220")
        win.configure(bg="#1e1e2e")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="📞", font=("Segoe UI", 36), bg="#1e1e2e",
                 fg="#f9e2af").pack(pady=(16, 2))
        tk.Label(win, text=f"{src} t'appelle !", font=("Segoe UI", 14, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack()
        btns = tk.Frame(win, bg="#1e1e2e")
        btns.pack(pady=18)

        def accepter():
            stop_sonnerie()
            win.destroy()
            self._accepter_appel(src)

        def refuser():
            stop_sonnerie()
            win.destroy()
            self._refuser_appel(src)

        tk.Button(btns, text="✓ Accepter", font=("Segoe UI", 11, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=accepter).pack(side="left", padx=8)
        tk.Button(btns, text="✗ Refuser", font=("Segoe UI", 11, "bold"),
                  bg="#f38ba8", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=refuser).pack(side="left", padx=8)

    def _accepter_appel(self, src):
        self._ouvrir_fenetre_appel(src, appelant=False)
        # allouer le socket audio (sans démarrer les flux) et répondre
        if AUDIO_OK:
            audio_port = self.audio.allouer() or 0
            audio_ip = local_ip()
        else:
            audio_port = 0
            audio_ip = local_ip()
        msg = make_msg("call_accept", from_=self.pseudo, to=src,
                       audio_ip=audio_ip, audio_port=audio_port)
        self._envoyer_controle_appel(msg, src)
        self._demarrer_timer_appel(src)

    def _refuser_appel(self, src):
        self._envoyer_controle_appel(make_msg("call_reject", from_=self.pseudo, to=src), src)

    def _on_appel_accepte(self, peer, audio_ip, audio_port):
        # l'initiateur reçoit l'acceptation : alloue, démarre les flux, envoie call_ready
        if peer not in self.fenetres_appel or not self.fenetres_appel[peer].winfo_exists():
            self._ouvrir_fenetre_appel(peer, appelant=True)
        win = self.fenetres_appel[peer]
        if AUDIO_OK and audio_port:
            mon_port = self.audio.allouer() or 0
            self.audio.demarrer_streams(audio_ip, audio_port)
            win.lbl_appel_statut.config(text="Connecté !")
            self._envoyer_controle_appel(
                make_msg("call_ready", from_=self.pseudo, to=peer,
                          audio_ip=local_ip(), audio_port=mon_port), peer)
        else:
            win.lbl_appel_statut.config(text="Mode texte")
        self._demarrer_timer_appel(peer)

    def _on_appel_ready(self, peer, audio_ip, audio_port):
        # le récepteur reçoit l'info de l'initiateur : démarre les flux (même socket)
        if AUDIO_OK and audio_port:
            self.audio.demarrer_streams(audio_ip, audio_port)
        win = self.fenetres_appel.get(peer)
        if win and win.winfo_exists():
            win.lbl_appel_statut.config(text="Connecté !")

    def _demarrer_timer_appel(self, peer):
        self._appel_start = time.time()
        def tick():
            win = self.fenetres_appel.get(peer)
            if not win or not win.winfo_exists():
                return
            if self._appel_start:
                d = int(time.time() - self._appel_start)
                m, s = divmod(d, 60)
                win.lbl_duree.config(text=f"{m:02d}:{s:02d}")
            self.root.after(1000, tick)
        tick()

    def _raccrocher(self, peer):
        self.audio.arreter()
        self._envoyer_controle_appel(make_msg("call_end", from_=self.pseudo, to=peer), peer)
        win = self.fenetres_appel.pop(peer, None)
        if win and win.winfo_exists():
            win.destroy()
        self.appels.pop(peer, None)
        self._gagner_xp(0, appels=1)

    def _on_appel_refuse(self, peer):
        win = self.fenetres_appel.pop(peer, None)
        if win and win.winfo_exists():
            win.lbl_appel_statut.config(text="Appel refusé 😕")
            self.root.after(2500, win.destroy)
        self.afficher_systeme(f"📞 {peer} a refusé l'appel.")

    def _on_appel_fin(self, peer):
        self.audio.arreter()
        win = self.fenetres_appel.pop(peer, None)
        if win and win.winfo_exists():
            win.lbl_appel_statut.config(text="Appel terminé")
            self.root.after(2000, win.destroy)
        self.afficher_systeme(f"📞 Appel avec {peer} terminé.")

    def _envoyer_controle_appel(self, data, dest):
        if self.mode == "host":
            if dest == self.pseudo:
                return
            sock_dest = self.pseudo_to_sock.get(dest)
            if sock_dest:
                try:
                    sock_dest.sendall(data)
                except OSError:
                    pass
        else:
            try:
                self.sock.sendall(data)
            except OSError:
                pass

    def _peer_ip(self, peer):
        if self.mode == "host":
            return self.client_ips.get(peer)
        else:
            return self.host_ip

    def _info_appel_texte(self):
        self.afficher_systeme("ℹ Appel en mode texte (audio indisponible).")

    # -----------------------------------------------------------------
    #  Toasts de notification
    # -----------------------------------------------------------------
    def _toast(self, texte, callback=None):
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg="#313244")
        popup.attributes("-topmost", True)
        x = self.root.winfo_x() + self.root.winfo_width() - 270
        y = self.root.winfo_y() + self.root.winfo_height() - 80
        popup.geometry(f"+{x}+{y}")
        lbl = tk.Label(popup, text=" " + texte + " ", font=("Segoe UI", 10),
                       fg="#cdd6f4", bg="#313244", padx=14, pady=10, wraplength=240,
                       justify="left")
        lbl.pack()
        def cliquer(e=None):
            if callback:
                callback()
            popup.destroy()
        lbl.bind("<Button-1>", cliquer)
        popup.after(4500, popup.destroy)

    # -----------------------------------------------------------------
    #  Divers
    # -----------------------------------------------------------------
    def _reset_frame(self):
        if hasattr(self, "frame"):
            self.frame.destroy()
        self.frame = tk.Frame(self.root, bg="#1e1e2e")
        self.frame.pack(fill="both", expand=True)

    def quitter(self):
        self.running = False
        self.audio.arreter()
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass
        with self.clients_lock:
            for c in self.clients:
                try:
                    c.close()
                except OSError:
                    pass
        for s in (self.tcp_server, self.udp_sock):
            try:
                if s:
                    s.close()
            except OSError:
                pass
        self.gc.sauver()
        self.root.destroy()


# =====================================================================
if __name__ == "__main__":
    try:
        LANchat().root.mainloop()
    except KeyboardInterrupt:
        pass