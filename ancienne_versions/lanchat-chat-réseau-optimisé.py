#!/usr/bin/env python3
"""
LANchat — Chat entre utilisateurs d'un même réseau (même Wi-Fi / même box).
Un seul fichier, 100% stdlib (aucune dépendance externe).

Fonctionnalités :
  • Héberger ou rejoindre une discussion depuis un menu simple.
  • Découverte automatique des serveurs sur le réseau via UDP broadcast
    (plus besoin de connaître l'IP / le port à la main).
  • Animation de chargement (spinner) pendant la recherche et la connexion.
  • Pseudos colorés, notifications de connexion/déconnexion, file thread-safe
    vers l'interface (Tkinter n'est manipulé que par le thread principal).
  • Protocole robuste : messages JSON délimités par '\n' (plus de découpage
    aléatoire comme avec un simple recv()).

Lance simplement :  python3 lanchat.py
"""

import socket
import threading
import queue
import json
import random
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox

# =====================================================================
#  Configuration
# =====================================================================
APP_NAME      = "LANchat"
APP_MAGIC     = "LNCH"          # signature pour ignorer le bruit réseau
TCP_PORT      = 5555           # port des messages (TCP)
UDP_PORT      = 5556           # port de découverte (UDP)
SCAN_TIME     = 3.0            # durée max de recherche des serveurs (s)
ANNOUNCE_EVERY = 2.0           # annonce serveur toutes les N secondes
MAX_PSEUDO    = 18
RECV_BUF      = 65536

# Palette de couleurs lisibles pour les pseudos (hex).
PALETTE = ["#e53935", "#8e24aa", "#3949ab", "#00897b", "#43a047", "#f4511e",
           "#6d4c41", "#2980b9", "#27ae60", "#d35400", "#16a085", "#9b59b6",
           "#f39c12", "#e74c3c", "#1abc9c", "#3498db", "#e91e63", "#009688"]

# Frames du spinner ( Unicode) pour l'animation de chargement.
SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler()])
log = logging.getLogger("lanchat")


# =====================================================================
#  Utilitaires réseau
# =====================================================================
def local_ip():
    """Renvoie l'IP LAN approximative de cette machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))      # n'envoie rien, fixe juste le routage
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def recv_lines(sock, on_line):
    """
    Lit un socket TCP, découpe le flux en lignes JSON terminées par '\n'
    et appelle on_line(dict) pour chaque message complet.
    Gère correctement la fragmentation TCP (contrairement à recv() brut).
    """
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
                    pass        # message mal formé : on ignore
    except OSError:
        pass


def make_msg(msg_type, **fields):
    """Construit un message JSON + '\n' prêt à envoyer."""
    fields["type"] = msg_type
    return (json.dumps(fields, ensure_ascii=False) + "\n").encode("utf-8")


# =====================================================================
#  Application
# =====================================================================
class LANchat:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("560x620")
        self.root.minsize(420, 480)
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", self.quitter)

        # État partagé
        self.pseudo = ""
        self.mode = None                 # "host" ou "client"
        self.running = True
        self.ui_queue = queue.Queue()    # file thread-safe -> thread principal
        self.couleurs = {}               # {"pseudo": "#couleur"}
        self.sock = None                 # socket client (mode client)
        self.clients = []                # liste de sockets (mode host)
        self.clients_lock = threading.Lock()
        self.pseudos = {}                # {socket: pseudo} (mode host)
        self.udp_sock = None             # socket découverte (host)
        self.tcp_server = None          # socket serveur (host)
        self.nb_connectes = 0
        self.cible = None                # (ip, port, nom) du serveur rejoint

        # Lancer la boucle de polling UI + écran de démarrage
        self._poll()
        self._ecran_demarrage()

    # -----------------------------------------------------------------
    #  Boucle UI : vide la file en toute sécurité (thread principal)
    # -----------------------------------------------------------------
    def _poll(self):
        try:
            while True:
                kind, *args = self.ui_queue.get_nowait()
                self._handle_event(kind, args)
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    def _handle_event(self, kind, args):
        if kind == "msg":
            pseudo, texte = args
            self.afficher_message(pseudo, texte)
        elif kind == "sys":
            (texte,) = args
            self.afficher_systeme(texte)
        elif kind == "err":
            (texte,) = args
            self.afficher_erreur(texte)
        elif kind == "scan_progress":
            (n,) = args
            self._maj_chargement(n)
        elif kind == "discovered":
            (serveurs,) = args
            self._fin_scan(serveurs)
        elif kind == "connected":
            self._on_connecte()
        elif kind == "connect_fail":
            (msg,) = args
            self._echec_connexion(msg)

    # -----------------------------------------------------------------
    #  Écran de démarrage : pseudo + Héberger / Rejoindre
    # -----------------------------------------------------------------
    def _ecran_demarrage(self):
        self._reset_frame()
        f = self.frame
        f.configure(bg="#1e1e2e")

        tk.Label(f, text="💬  " + APP_NAME, font=("Segoe UI", 26, "bold"),
                 fg="#cdd6f4", bg="#1e1e2e").pack(pady=(40, 4))
        tk.Label(f, text="Chat sur le même réseau Wi-Fi", font=("Segoe UI", 11),
                 fg="#a6adc8", bg="#1e1e2e").pack(pady=(0, 30))

        cadre = tk.Frame(f, bg="#313244", bd=0, highlightbackground="#45475a",
                        highlightthickness=1)
        cadre.pack(padx=40, pady=10, fill="x")

        tk.Label(cadre, text="Ton pseudo", font=("Segoe UI", 10),
                 fg="#a6adc8", bg="#313244").pack(anchor="w", padx=16, pady=(14, 0))
        self.entree_pseudo = tk.Entry(cadre, font=("Segoe UI", 13),
                                      bg="#45475a", fg="#cdd6f4",
                                      insertbackground="#cdd6f4",
                                      relief="flat", width=24)
        self.entree_pseudo.pack(padx=16, pady=6, fill="x")
        self.entree_pseudo.focus()

        tk.Button(cadre, text="🖥️  Héberger une discussion", font=("Segoe UI", 11, "bold"),
                  bg="#89b4fa", fg="#1e1e2e", activebackground="#b4befe",
                  relief="flat", cursor="hand2", height=2,
                  command=self.demarrer_hote).pack(padx=16, pady=(10, 6), fill="x")
        tk.Button(cadre, text="🔍  Rejoindre une discussion", font=("Segoe UI", 11, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", activebackground="#b4e6a8",
                  relief="flat", cursor="hand2", height=2,
                  command=self.demarrer_rejoindre).pack(padx=16, pady=(0, 16), fill="x")

        tk.Label(f, text="Astuce : sur le même Wi-Fi, l'hébergeur lance le salon "
                         "et les autres le rejoignent automatiquement.",
                 font=("Segoe UI", 9), fg="#6c7086", bg="#1e1e2e",
                 wraplength=420, justify="center").pack(pady=(20, 0))

    def _reset_frame(self):
        if hasattr(self, "frame"):
            self.frame.destroy()
        self.frame = tk.Frame(self.root, bg="#1e1e2e")
        self.frame.pack(fill="both", expand=True)

    def _valider_pseudo(self):
        p = self.entree_pseudo.get().strip()
        if not p:
            messagebox.showwarning(APP_NAME, "Choisis un pseudo s'il te plaît 🙂")
            return None
        if len(p) > MAX_PSEUDO:
            messagebox.showwarning(APP_NAME,
                                   f"Pseudo trop long (max {MAX_PSEUDO} caractères).")
            return None
        self.pseudo = p
        return p

    # -----------------------------------------------------------------
    #  Mode HÔTE
    # -----------------------------------------------------------------
    def demarrer_hote(self):
        if not self._valider_pseudo():
            return
        self.mode = "host"
        self._couleur_pseudo(self.pseudo)
        threading.Thread(target=self._servir_tcp, daemon=True).start()
        threading.Thread(target=self._servir_udp, daemon=True).start()
        self._construire_interface_chat()

    def _servir_tcp(self):
        """Serveur TCP : accepte les clients et gère leurs messages."""
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("0.0.0.0", TCP_PORT))
            srv.listen()
            self.tcp_server = srv
            log.info("Serveur TCP en écoute sur le port %d", TCP_PORT)
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
            threading.Thread(target=self._gerer_client, args=(conn, addr),
                             daemon=True).start()

    def _gerer_client(self, conn, addr):
        pseudo_client = None
        def on_line(m):
            nonlocal pseudo_client
            t = m.get("type")
            if t == "hello":
                pseudo_client = (m.get("pseudo") or "?")[:MAX_PSEUDO]
                self.pseudos[conn] = pseudo_client
                self.ui_queue.put(("sys", f"🟢 {pseudo_client} a rejoint le salon"))
                self._couleur_pseudo(pseudo_client)
                self._maj_compteur(1)
                self._diffuser(make_msg("sys", text=f"🟢 {pseudo_client} a rejoint le salon"), except_=conn)
            elif t == "msg":
                p = m.get("pseudo", "?")
                txt = m.get("text", "")
                self.ui_queue.put(("msg", p, txt))          # l'hôte voit le message
                self._diffuser(make_msg("msg", pseudo=p, text=txt), except_=conn)
        recv_lines(conn, on_line)
        # Déconnexion
        with self.clients_lock:
            if conn in self.clients:
                self.clients.remove(conn)
        try:
            conn.close()
        except OSError:
            pass
        if pseudo_client:
            self._maj_compteur(-1)
            self.ui_queue.put(("sys", f"🔴 {pseudo_client} a quitté le salon"))
            self._diffuser(make_msg("sys", text=f"🔴 {pseudo_client} a quitté le salon"), except_=conn)

    def _diffuser(self, data, except_=None):
        """Envoie un message à tous les clients connectés (sauf l'émetteur)."""
        with self.clients_lock:
            cibles = [c for c in self.clients if c is not except_]
        for c in cibles:
            try:
                c.sendall(data)
            except OSError:
                with self.clients_lock:
                    if c in self.clients:
                        self.clients.remove(c)

    def _servir_udp(self):
        """Découverte réseau : répond aux broadcasts des rejoignants + s'annonce."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("0.0.0.0", UDP_PORT))
            self.udp_sock = s
        except OSError as e:
            log.warning("UDP découverte indisponible : %s", e)
            return
        annonce = make_udp_msg("announce", port=TCP_PORT, name=APP_NAME)
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
            if not msg:
                continue
            if msg.get("type") == "discover":      # un rejoignant nous cherche
                try:
                    s.sendto(annonce, addr)         # on lui répond en unicast
                except OSError:
                    pass

    def _maj_compteur(self, delta):
        self.nb_connectes += delta
        if hasattr(self, "lbl_statut"):
            self.root.after(0, self._rafraichir_statut)

    def _rafraichir_statut(self):
        if hasattr(self, "lbl_statut"):
            if self.mode == "host":
                self.lbl_statut.config(
                    text=f"🟢 Hébergé sur {local_ip()}:{TCP_PORT}  •  "
                         f"{self.nb_connectes} connecté(s) en plus de toi")
            else:
                ip, port, nom = self.cible
                self.lbl_statut.config(text=f"🔵 Connecté à {nom} ({ip}:{port})")

    # -----------------------------------------------------------------
    #  Mode REJOINDRE  (découverte + animation de chargement)
    # -----------------------------------------------------------------
    def demarrer_rejoindre(self):
        if not self._valider_pseudo():
            return
        self._couleur_pseudo(self.pseudo)
        self.mode = "client"
        self._ecran_chargement("Recherche des discussions sur le réseau…")
        threading.Thread(target=self._scan_reseau, daemon=True).start()

    def _scan_reseau(self):
        """Envoie un broadcast de découverte et collecte les réponses."""
        trouve = {}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("0.0.0.0", UDP_PORT))
        except OSError as e:
            self.ui_queue.put(("connect_fail", f"Scan réseau impossible : {e}"))
            return
        # On lance le broadcast de découverte
        try:
            s.sendto(make_udp_msg("discover"), ("255.255.255.255", UDP_PORT))
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
            if not msg or msg.get("type") not in ("announce",):
                continue           # on ignore nos propres "discover"
            ip = addr[0]
            port = int(msg.get("port", TCP_PORT))
            nom = msg.get("name", f"{ip}:{port}")
            trouve[(ip, port)] = nom
            self.ui_queue.put(("scan_progress", len(trouve)))
        try:
            s.close()
        except OSError:
            pass
        serveurs = [(ip, port, nom) for (ip, port), nom in trouve.items()]
        self.ui_queue.put(("discovered", serveurs))

    def _ecran_chargement(self, texte):
        self._reset_frame()
        f = self.frame
        f.configure(bg="#1e1e2e")
        self.lbl_spinner = tk.Label(f, text="⠋", font=("Segoe UI", 40),
                                    fg="#89b4fa", bg="#1e1e2e")
        self.lbl_spinner.pack(pady=(120, 10))
        self.lbl_chargement = tk.Label(f, text=texte, font=("Segoe UI", 12),
                                       fg="#cdd6f4", bg="#1e1e2e")
        self.lbl_chargement.pack(pady=4)
        self.lbl_compteur = tk.Label(f, text="0 salon trouvé", font=("Segoe UI", 10),
                                     fg="#a6e3a1", bg="#1e1e2e")
        self.lbl_compteur.pack(pady=2)
        self._spin_idx = 0
        self._animer_spinner()
        # Bouton annuler
        tk.Button(f, text="Annuler", font=("Segoe UI", 10), bg="#45475a", fg="#cdd6f4",
                  relief="flat", cursor="hand2", command=self._ecran_demarrage
                  ).pack(pady=30)

    def _animer_spinner(self):
        if hasattr(self, "lbl_spinner") and self.lbl_spinner.winfo_exists():
            self.lbl_spinner.config(text=SPINNER[self._spin_idx % len(SPINNER)])
            self._spin_idx += 1
            self.root.after(90, self._animer_spinner)

    def _maj_chargement(self, n):
        if hasattr(self, "lbl_compteur") and self.lbl_compteur.winfo_exists():
            self.lbl_compteur.config(text=f"{n} salon{'s' if n != 1 else ''} trouvé{'s' if n != 1 else ''}")

    def _fin_scan(self, serveurs):
        if not serveurs:
            self._reset_frame()
            f = self.frame
            f.configure(bg="#1e1e2e")
            tk.Label(f, text="😕", font=("Segoe UI", 40), bg="#1e1e2e"
                     ).pack(pady=(110, 6))
            tk.Label(f, text="Aucune discussion trouvée", font=("Segoe UI", 13, "bold"),
                     fg="#cdd6f4", bg="#1e1e2e").pack(pady=4)
            tk.Label(f, text="Demande à un ami de lancer un salon, "
                             "ou héberge le tien !", font=("Segoe UI", 10),
                     fg="#a6adc8", bg="#1e1e2e", wraplength=380).pack(pady=6)
            tk.Button(f, text="🖥️  Héberger à la place", font=("Segoe UI", 11, "bold"),
                      bg="#89b4fa", fg="#1e1e2e", relief="flat", cursor="hand2",
                      command=self.demarrer_hote).pack(pady=20)
            tk.Button(f, text="↩ Recommencer la recherche", font=("Segoe UI", 10),
                      bg="#45475a", fg="#cdd6f4", relief="flat", cursor="hand2",
                      command=self.demarrer_rejoindre).pack(pady=4)
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
        for ip, port, nom in serveurs:
            liste.insert(tk.END, f"  {nom}   —   {ip}:{port}")
        liste.pack(padx=40, pady=6, fill="x")
        liste.selection_set(0)

        def connecter():
            sel = liste.curselection()
            if not sel:
                messagebox.showinfo(APP_NAME, "Choisis un salon s'il te plaît.")
                return
            ip, port, nom = serveurs[sel[0]]
            self.cible = (ip, port, nom)
            self._ecran_chargement(f"Connexion à {nom} ({ip})…")
            threading.Thread(target=self._connecter_a, args=(ip, port),
                             daemon=True).start()

        tk.Button(f, text="Se connecter", font=("Segoe UI", 12, "bold"),
                  bg="#a6e3a1", fg="#1e1e2e", relief="flat", cursor="hand2",
                  command=connecter).pack(pady=18)
        tk.Button(f, text="↩ Actualiser", font=("Segoe UI", 10), bg="#45475a",
                  fg="#cdd6f4", relief="flat", cursor="hand2",
                  command=self.demarrer_rejoindre).pack()

    def _connecter_a(self, ip, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((ip, port))
            s.settimeout(None)
            s.sendall(make_msg("hello", pseudo=self.pseudo))
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
        """Thread client : lit les messages du serveur et les met dans la file."""
        def on_line(m):
            t = m.get("type")
            if t == "msg":
                self.ui_queue.put(("msg", m.get("pseudo", "?"), m.get("text", "")))
            elif t == "sys":
                self.ui_queue.put(("sys", m.get("text", "")))
        recv_lines(self.sock, on_line)
        self.ui_queue.put(("err", "Connexion perdue avec le serveur."))

    # -----------------------------------------------------------------
    #  Interface de chat (commune aux deux modes)
    # -----------------------------------------------------------------
    def _construire_interface_chat(self):
        self._reset_frame()
        f = self.frame
        f.configure(bg="#1e1e2e")

        # Barre de titre / statut
        barre = tk.Frame(f, bg="#313244", height=44)
        barre.pack(fill="x")
        tk.Label(barre, text=f"💬  {APP_NAME}", font=("Segoe UI", 12, "bold"),
                 fg="#cdd6f4", bg="#313244").pack(side="left", padx=14, pady=8)
        self.lbl_statut = tk.Label(barre, text="", font=("Segoe UI", 9),
                                   fg="#a6adc8", bg="#313244")
        self.lbl_statut.pack(side="right", padx=14, pady=8)
        self._rafraichir_statut()

        # Zone de messages
        cadre_msg = tk.Frame(f, bg="#1e1e2e")
        cadre_msg.pack(fill="both", expand=True, padx=10, pady=10)
        scroll = tk.Scrollbar(cadre_msg)
        scroll.pack(side="right", fill="y")
        self.zone = tk.Text(cadre_msg, font=("Segoe UI", 11), bg="#181825",
                           fg="#cdd6f4", insertbackground="#cdd6f4",
                           yscrollcommand=scroll.set, relief="flat", bd=0,
                           padx=12, pady=10, wrap="word", state="disabled")
        self.zone.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.zone.yview)

        # Tags de style
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

        # Zone de saisie
        barre_saisie = tk.Frame(f, bg="#1e1e2e")
        barre_saisie.pack(fill="x", padx=10, pady=(0, 10))
        self.entree = tk.Entry(barre_saisie, font=("Segoe UI", 12),
                               bg="#313244", fg="#cdd6f4",
                               insertbackground="#cdd6f4", relief="flat", bd=0)
        self.entree.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entree.bind("<Return>", lambda e: self.envoyer())
        self.entree.focus()
        tk.Button(barre_saisie, text="Envoyer ➤", font=("Segoe UI", 11, "bold"),
                  bg="#89b4fa", fg="#1e1e2e", activebackground="#b4befe",
                  relief="flat", cursor="hand2", padx=14,
                  command=self.envoyer).pack(side="right", ipady=4)

        self.afficher_systeme(f"🟢 Bienvenue {self.pseudo} !")
        if self.mode == "host":
            self.afficher_systeme(f"Tu héberges le salon sur {local_ip()}:{TCP_PORT}. "
                                  f"Partage cette IP si la découverte ne marche pas.")

    def _couleur_pseudo(self, pseudo):
        if pseudo not in self.couleurs:
            self.couleurs[pseudo] = random.choice(PALETTE)
        # Crée le tag Tkinter (depuis le thread principal uniquement)
        if hasattr(self, "zone"):
            self.zone.tag_config(pseudo, foreground=self.couleurs[pseudo],
                                 font=("Segoe UI", 11, "bold"))
        return self.couleurs[pseudo]

    def envoyer(self):
        texte = self.entree.get().strip()
        if not texte:
            return
        self.entree.delete(0, tk.END)
        data = make_msg("msg", pseudo=self.pseudo, text=texte)
        if self.mode == "host":
            self._diffuser(data)                  # envoie aux autres clients
        else:
            try:
                self.sock.sendall(data)
            except OSError:
                self.afficher_erreur("Connexion perdue : message non envoyé.")
                return
        # Affiche son propre message localement
        self.afficher_message(self.pseudo, texte, moi=True)

    # -----------------------------------------------------------------
    #  Affichage des messages (thread principal)
    # -----------------------------------------------------------------
    def afficher_message(self, pseudo, texte, moi=False):
        self.zone.config(state="normal")
        self.zone.insert(tk.END, f"[{pseudo}]", "moi" if moi else self._couleur_tag(pseudo))
        self.zone.insert(tk.END, f"  {texte}\n", "moi_texte" if moi else "autre_texte")
        self.zone.config(state="disabled")
        self.zone.see(tk.END)

    def _couleur_tag(self, pseudo):
        self._couleur_pseudo(pseudo)
        return pseudo if pseudo != self.pseudo else "moi"

    def afficher_systeme(self, texte):
        self.zone.config(state="normal")
        self.zone.insert(tk.END, texte + "\n", "sys")
        self.zone.config(state="disabled")
        self.zone.see(tk.END)

    def afficher_erreur(self, texte):
        self.zone.config(state="normal")
        self.zone.insert(tk.END, "⚠ " + texte + "\n", "erreur")
        self.zone.config(state="disabled")
        self.zone.see(tk.END)

    # -----------------------------------------------------------------
    #  Fermeture propre
    # -----------------------------------------------------------------
    def quitter(self):
        self.running = False
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
        try:
            if self.tcp_server:
                self.tcp_server.close()
        except OSError:
            pass
        try:
            if self.udp_sock:
                self.udp_sock.close()
        except OSError:
            pass
        self.root.destroy()


# =====================================================================
#  Encodage / décodage UDP pour la découverte
# =====================================================================
def make_udp_msg(msg_type, **fields):
    fields["magic"] = APP_MAGIC
    fields["type"] = msg_type
    return (json.dumps(fields, ensure_ascii=False)).encode("utf-8")


def parse_udp(data):
    try:
        m = json.loads(data.decode("utf-8"))
        if m.get("magic") == APP_MAGIC:
            return m
    except (ValueError, UnicodeDecodeError):
        pass
    return None


# =====================================================================
#  Lancement
# =====================================================================
if __name__ == "__main__":
    try:
        LANchat().root.mainloop()
    except KeyboardInterrupt:
        pass
