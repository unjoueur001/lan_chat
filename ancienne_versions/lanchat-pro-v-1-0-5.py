#!/usr/bin/env python3
import os, json, socket, threading, queue, time, hashlib, logging, re
import webbrowser, platform, subprocess, tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
try:
    import pyaudio
    AUDIO_OK = True
except Exception:
    AUDIO_OK = False

APP_NAME      = "LANchat Pro"
VERSION       = "V.1.0.5"
APP_MAGIC     = "LNCP"
TCP_PORT      = 5555
UDP_PORT     = 5556
SCAN_TIME     = 3.0
ANNOUNCE_EVERY = 2.0
MAX_PSEUDO    = 18
RECV_BUF      = 65536
COMPTE_FILE   = "comptes_lanchat.txt"
SPINNER = ["â ","â ","â ¹","â ¸","â ¼","â ´","â ¦","â §","â ","â "]
A_RATE, A_CHAN, A_CHUNK = 44100, 1, 4096
A_FMT = None

URL_RE = re.compile(r'(https?://[^\s<>"\']+|file://[^\s<>"\']+|www\.[^\s<>"\']+|[A-Za-z0-9._\\/-]+\.(?:mp4|webm|gif|mp3|wav|jpg|jpeg|png|mov|mkv))', re.I)
def _normalise_url(u):
    if u.lower().startswith(("http://","https://","file://")): return u
    if u.lower().startswith("www."): return "http://"+u
    return None

EMOJI_DIR = "emojis_lanchat"
EMOJIS = {
    "Smileys": ["😀","😂","🥰","😎","🤔","😴","😭","😡","🤯","🥳","😱","🤗","🤩","😇","🤓","🙃"],
    "Gestes": ["👍","👎","👏","🙏","💪","✌️","🤙","🤝","✋","👊","🫶","🙌","🤞","🤟","👌","👋"],
    "Coeur": ["❤️","🧡","💛","💚","💙","💜","🖤","🤍","💖","💝","💘","💔","❣️","💕","💞","💟"],
    "Objets": ["🔥","⭐","✨","💎","🎉","🎁","🏆","🚀","💰","🎯","💡","🎵","🎮","📱","💻","☕"],
    "Nature": ["🌈","☀️","🌙","⚡","❄️","🌊","🌸","🍀","🌟","🌻","🐶","🐱","🦄","🐉","🔥","🌌"],
    "Nourriture": ["🍕","🍔","🍟","🌮","🍩","🎂","🍓","🍉","🥑","🍿","🍫","🥤","🍣","🍜","🍪","🍇"],
    "Drapeaux": ["🇫🇷","🇬🇧","🇺🇸","🇪🇸","🇮🇹","🇩🇪","🇯🇵","🇨🇦","🇧🇪","🇨🇭","🇵🇹","🇲🇦","🇸🇳","🌍","🎯","⚡"],
    "Activités": ["⚽","🏀","🎮","🎧","🎨","📸","🎬","🎸","🎤","🎹","🥁","🎲","🎳","🎯","♟️","🏆"],
    "Symboles": ["💯","✅","❌","⭕","❓","❗","💢","💥","💫","💦","💨","🏁","🔔","🔕","📢","💬"],
    "Animaux": ["🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐨","🦁","🐯","🦄","🐉","🦖","🐙","🦋"],
}

def _lister_emojis_perso():
    if not os.path.isdir(EMOJI_DIR): return []
    out=[]
    for f in sorted(os.listdir(EMOJI_DIR)):
        if f.lower().endswith((".png",".gif",".jpg",".jpeg",".webp",".bmp")):
            out.append(f)
    return out


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
THEMES = {
    "sombre": {
        "bg":"#11111b","bg2":"#181825","surf":"#1e1e2e","surf2":"#313244",
        "inp":"#45475a","text":"#cdd6f4","sub":"#a6adc8","dim":"#6c7086",
        "blue":"#89b4fa","green":"#a6e3a1","red":"#f38ba8","yellow":"#f9e2af",
        "purple":"#cba6f7","pink":"#f5c2e7","teal":"#94e2d5",
    },
    "clair": {
        "bg":"#eff1f5","bg2":"#e6e9ef","surf":"#dce0e8","surf2":"#ccd0da",
        "inp":"#acb0be","text":"#4c4f69","sub":"#6c6f85","dim":"#9ca0b0",
        "blue":"#1e66f5","green":"#40a02b","red":"#d20f39","yellow":"#df8e1d",
        "purple":"#7287fd","pink":"#ea76cb","teal":"#179299",
    },
}
_theme_courant = "sombre"
def _appliquer_theme(nom):
    global C_BG,C_BG2,C_SURF,C_SURF2,C_INP,C_TEXT,C_SUB,C_DIM
    global C_BLUE,C_GREEN,C_RED,C_YELLOW,C_PURPLE,C_PINK,C_TEAL
    t=THEMES.get(nom,THEMES["sombre"])
    C_BG=t["bg"];C_BG2=t["bg2"];C_SURF=t["surf"];C_SURF2=t["surf2"]
    C_INP=t["inp"];C_TEXT=t["text"];C_SUB=t["sub"];C_DIM=t["dim"]
    C_BLUE=t["blue"];C_GREEN=t["green"];C_RED=t["red"];C_YELLOW=t["yellow"]
    C_PURPLE=t["purple"];C_PINK=t["pink"];C_TEAL=t["teal"]
_appliquer_theme("sombre")
FONT="Segoe UI"

SONS_PRESETS = {
    "notif_doux": "https://www.soundjay.com/buttons/sounds/beep-07a.mp3",
    "notif_classique": "https://www.soundjay.com/buttons/sounds/button-09.mp3",
    "sonnerie_retro": "https://www.soundjay.com/phone/sounds/telephone-ring-01.mp3",
    "sonnerie_modern": "https://www.soundjay.com/phone/sounds/ringtone-1.mp3",
    "notif_pop": "https://www.soundjay.com/misc/sounds/pop-2.mp3",
}
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
    "ninja":{"nom":"Ninja","emoji":"🥷","prix":280},
    "robot":{"nom":"Robot","emoji":"🤖","prix":320},
    "arc_en_ciel":{"nom":"Arc-en-ciel","emoji":"🌈","prix":550},
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
    "createur":{"nom":"Créateur","prix":350},
    "flamme":{"nom":"Flamme Éternelle","prix":700},
}

COULEURS_DEFAUT="bleu"; BADGE_DEFAUT="etoile"; TITRE_DEFAUT="membre"

def couleur_hex(cid): return COULEURS.get(cid,COULEURS[COULEURS_DEFAUT])["hex"]
def couleur_anime(cid): return COULEURS.get(cid,{}).get("anime",False)
def badge_emoji(bid): return BADGES.get(bid,BADGES[BADGE_DEFAUT])["emoji"]
def titre_nom(tid): return TITRES.get(tid,TITRES[TITRE_DEFAUT])["nom"]

def _paliers():
    seuils=[0]; step=100; total=0
    for _ in range(200):
        total+=step; seuils.append(total); step=int(step*1.15)
    return seuils
_SEUILS=_paliers()
def niveau_from_xp(xp):
    niv=0
    for i in range(1,len(_SEUILS)):
        if xp>=_SEUILS[i]: niv=i
        else: break
    return niv,_SEUILS[niv+1]-xp
def info_niveau(xp):
    niv=0
    for i in range(1,len(_SEUILS)):
        if xp>=_SEUILS[i]: niv=i
        else: break
    return niv,xp-_SEUILS[niv],_SEUILS[niv+1]-_SEUILS[niv]

class GestionnaireComptes:
    def __init__(self,chemin):
        self.chemin=chemin; self.comptes={}; self._charger()
    def _charger(self):
        if not os.path.exists(self.chemin): return
        try:
            with open(self.chemin,"r",encoding="utf-8") as f: self.comptes=json.load(f)
        except Exception: self.comptes={}
    def _sauver(self):
        try:
            with open(self.chemin,"w",encoding="utf-8") as f:
                json.dump(self.comptes,f,ensure_ascii=False,indent=2)
        except Exception as e: log.warning("Sauvegarde comptes: %s",e)
    @staticmethod
    def _hash(mdp,salt): return hashlib.sha256((salt+mdp).encode("utf-8")).hexdigest()
    def existe(self,p): return p in self.comptes
    def creer(self,pseudo,mdp):
        if pseudo in self.comptes: return False,"Ce pseudo existe dÃ©jÃ ."
        if not pseudo or len(pseudo)>MAX_PSEUDO: return False,f"Pseudo invalide (1 Ã  {MAX_PSEUDO} car)."
        salt=os.urandom(16).hex()
        self.comptes[pseudo]={"salt":salt,"hash":self._hash(mdp,salt),"coins":150,"xp":0,
            "msgs":0,"appels":0,"derniere_session":time.strftime("%Y-%m-%d %H:%M"),
            "possedes":{"couleurs":["bleu","vert"],"badges":["aucun","etoile"],"titres":["membre","newbie"]},
            "equip":{"couleur":"bleu","badge":"etoile","titre":"membre"},
            "sonnerie":"","notif":"","bio":"","liens":[],"theme":"sombre"}
        self._sauver(); return True,"Compte crÃ©Ã© ! 150 coins de bienvenue ð"
    def verifier(self,pseudo,mdp):
        c=self.comptes.get(pseudo)
        if not c: return False,"Compte introuvable."
        return (self._hash(mdp,c["salt"])==c["hash"]),"ok"
    def get(self,p): return self.comptes.get(p)
    def sauver(self): self._sauver()

def profil_public(c):
    niv,_=niveau_from_xp(c["xp"])
    return {"pseudo":None,"niveau":niv,"xp":c["xp"],"coins":c["coins"],"msgs":c["msgs"],
            "appels":c["appels"],"couleur":c["equip"]["couleur"],"badge":c["equip"]["badge"],
            "titre":c["equip"]["titre"],"bio":c.get("bio",""),"liens":c.get("liens",[])}

def local_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("8.8.8.8",80))
        ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return "127.0.0.1"

def recv_lines(sock,on_line):
    buf=b""
    try:
        while True:
            data=sock.recv(RECV_BUF)
            if not data: break
            buf+=data
            while b"\n" in buf:
                line,buf=buf.split(b"\n",1)
                if not line: continue
                try: on_line(json.loads(line.decode("utf-8")))
                except Exception: pass
    except OSError: pass

def make_msg(t,**f): f["type"]=t; return (json.dumps(f,ensure_ascii=False)+"\n").encode("utf-8")
def make_udp(t,**f): f["magic"]=APP_MAGIC; f["type"]=t; return json.dumps(f,ensure_ascii=False).encode("utf-8")
def parse_udp(data):
    try:
        m=json.loads(data.decode("utf-8"))
        return m if m.get("magic")==APP_MAGIC else None
    except Exception: return None

class AudioCall:
    def __init__(self):
        self.pa=None; self.in_stream=None; self.out_stream=None; self.sock=None
        self.peer=None; self.actif=False; self.mute=False; self._threads=[]
    def disponible(self): return AUDIO_OK
    def allouer(self):
        if not AUDIO_OK: return None
        if self.sock is None:
            try:
                s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(("0.0.0.0",0))
                self.sock=s
            except Exception: return None
        return self.mon_port()
    def demarrer_streams(self,ip,port):
        if not AUDIO_OK or self.actif: return False
        if self.sock is None: self.allouer()
        try:
            global A_FMT
            if A_FMT is None: A_FMT=pyaudio.paInt16
            self.pa=pyaudio.PyAudio()
            self.in_stream=self.pa.open(format=A_FMT,channels=A_CHAN,rate=A_RATE,input=True,frames_per_buffer=A_CHUNK)
            self.out_stream=self.pa.open(format=A_FMT,channels=A_CHAN,rate=A_RATE,output=True,frames_per_buffer=A_CHUNK)
            self.peer=(ip,port); self.actif=True; self.mute=False
            def capturer():
                while self.actif:
                    try:
                        data=self.in_stream.read(A_CHUNK,exception_on_overflow=False)
                        if not self.mute and self.peer: self.sock.sendto(data,self.peer)
                    except OSError: break
            def recevoir():
                self.sock.settimeout(1.0)
                while self.actif:
                    try:
                        data,_=self.sock.recvfrom(A_CHUNK*4); self.out_stream.write(data)
                    except socket.timeout: continue
                    except OSError: break
            t1=threading.Thread(target=capturer,daemon=True); t2=threading.Thread(target=recevoir,daemon=True)
            t1.start(); t2.start(); self._threads=[t1,t2]; return True
        except Exception as e: log.warning("Audio streams: %s",e); self.arreter(); return False
    def demarrer(self,ip,port): self.allouer(); return self.demarrer_streams(ip,port)
    def mon_port(self): return self.sock.getsockname()[1] if self.sock else None
    def basculer_mute(self): self.mute=not self.mute; return self.mute
    def arreter(self):
        self.actif=False
        for s in (self.in_stream,self.out_stream):
            try:
                if s: s.stop_stream(); s.close()
            except Exception: pass
        try:
            if self.pa: self.pa.terminate()
        except Exception: pass
        try:
            if self.sock: self.sock.close()
        except Exception: pass
        self.in_stream=self.out_stream=self.sock=self.pa=None; self.peer=None

_SONS_PERSO = {"sonnerie":"", "notif":""}

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
                except OSError:
                    continue
    except Exception:
        pass
    return False

def beep(freq=880, duree=120):
    try:
        import winsound; winsound.Beep(freq, duree); return
    except Exception: pass

_SONNERIE_FLAG = {"stop": False}
def sonnerie():
    _SONNERIE_FLAG["stop"] = False
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

def son_notif():
    path = _SONS_PERSO.get("notif", "")
    if path and os.path.isfile(path):
        _jouer_fichier(path); return
    beep(900, 100)

def hex_to_rgb(h):
    h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def rgb_to_hex(r,g,b): return f"#{r:02x}{g:02x}{b:02x}"
RAINBOW=["#f38ba8","#fab387","#f9e2af","#a6e3a1","#94e2d5","#89b4fa","#cba6f7"]

class LANchat:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title(f"{APP_NAME} {VERSION}")
        self.root.geometry("640x720")
        self.root.minsize(480,560)
        self.root.configure(bg=C_BG)
        self.root.protocol("WM_DELETE_WINDOW",self.quitter)
        self.gc=GestionnaireComptes(COMPTE_FILE)
        self.compte=None; self.pseudo=""
        self.mode=None; self.running=True; self.ui_queue=queue.Queue()
        self.profils={}; self.couleurs_tags=set()
        self.sock=None; self.host_ip=None; self.cible=None
        self.clients=[]; self.clients_lock=threading.Lock()
        self.pseudo_to_sock={}; self.client_ips={}
        self.udp_sock=None; self.tcp_server=None; self.nb_connectes=0
        self.fenetres_mp={}; self.mp_non_lus={}; self.mp_historique={}
        self.appels={}; self.fenetres_appel={}
        self.audio=AudioCall()
        self._anim_pseudos={}
        self._poll(); self._ecran_auth()

    def _poll(self):
        try:
            while True:
                kind,*args=self.ui_queue.get_nowait()
                self._handle(kind,args)
        except queue.Empty: pass
        self.root.after(80,self._poll)

    def _handle(self,kind,args):
        h={
            "msg":lambda:self.afficher_message(args[0],args[1]),
            "sys":lambda:self.afficher_systeme(args[0]),
            "err":lambda:self.afficher_erreur(args[0]),
            "scan_progress":lambda:self._maj_chargement(args[0]),
            "discovered":lambda:self._fin_scan(args[0]),
            "connected":self._on_connecte,
            "connect_fail":lambda:self._echec_connexion(args[0]),
            "mp":lambda:self._on_mp_recu(args[0],args[1]),
            "profil":lambda:self._maj_profil(args[0]),
            "profils_init":lambda:self._init_profils(args[0]),
            "call_incoming":lambda:self._on_appel_entrant(args[0]),
            "call_accepted":lambda:self._on_appel_accepte(args[0],args[1],args[2],args[3]),
            "call_ready":lambda:self._on_appel_ready(args[0],args[1],args[2]),
            "call_reject":lambda:self._on_appel_refuse(args[0]),
            "call_end":lambda:self._on_appel_fin(args[0]),
            "toast":lambda:self._toast(args[0],args[1] if len(args)>1 else None),
            "compte_maj":self._rafraichir_compte_ui,
        }
        f=h.get(kind)
        if f: f()

    def _reset_frame(self):
        if hasattr(self,"frame"): self.frame.destroy()
        self.frame=tk.Frame(self.root,bg=C_BG); self.frame.pack(fill="both",expand=True)

    def _entree_styler(self,e):
        e.config(font=(FONT,13),bg=C_INP,fg=C_TEXT,insertbackground=C_TEXT,relief="flat",bd=0)

    def _btn_styler(self,b,bg=C_BLUE,fg=C_BG):
        b.config(font=(FONT,11,"bold"),bg=bg,fg=fg,relief="flat",cursor="hand2",activebackground=bg,activeforeground=fg,bd=0)
        b.bind("<Enter>",lambda e:b.config(bg=self._lighten(bg)))
        b.bind("<Leave>",lambda e:b.config(bg=bg))

    def _lighten(self,hexcol,t=0.15):
        r,g,b=hex_to_rgb(hexcol)
        return rgb_to_hex(min(255,int(r+(255-r)*t)),min(255,int(g+(255-g)*t)),min(255,int(b+(255-b)*t)))

    def _titre_anime(self,parent,texte,couleur=C_BLUE,font_size=24):
        lbl=tk.Label(parent,text=texte,font=(FONT,font_size,"bold"),fg=couleur,bg=parent["bg"])
        lbl.pack()
        etapes=[couleur,self._lighten(couleur,0.2),self._lighten(couleur,0.35),self._lighten(couleur,0.2)]
        idx=[0]
        def anim():
            lbl.config(fg=etapes[idx[0]%len(etapes)])
            idx[0]+=1
            if lbl.winfo_exists(): self.root.after(600,anim)
        anim(); return lbl

    def _fond_anime(self,parent,height=80):
        canvas=tk.Canvas(parent,height=height,highlightthickness=0,bd=0)
        canvas.pack(fill="x")
        idx=[0]
        def anim():
            canvas.delete("fond")
            for i in range(len(RAINBOW)):
                c=RAINBOW[(idx[0]+i)%len(RAINBOW)]
                x0=i*60; canvas.create_rectangle(x0,0,x0+61,height,fill=c,outline="",tags="fond")
            idx[0]+=1
            if canvas.winfo_exists(): self.root.after(80,anim)
        anim(); return canvas

    def _ecran_auth(self):
        self._reset_frame()
        f=self.frame; f.configure(bg=C_BG)
        self._fond_anime(f,height=70)
        self._titre_anime(f,f"ð¬ {APP_NAME}",C_BLUE,22)
        tk.Label(f,text=VERSION,font=(FONT,10,"bold"),fg=C_YELLOW,bg=C_BG).pack(pady=(0,2))
        tk.Label(f,text="Compte local sÃ©curisÃ©",font=(FONT,11),fg=C_SUB,bg=C_BG).pack(pady=(0,16))
        cadre=tk.Frame(f,bg=C_SURF2,highlightbackground=C_INP,highlightthickness=1)
        cadre.pack(padx=40,pady=8,fill="x")
        self._auth_var=tk.StringVar(value="login")
        def toggle():
            if self._auth_var.get()=="login":
                self.btn_valider.config(text="Se connecter",bg=C_BLUE)
                self.lbl_mdp2.pack_forget(); self.ent_mdp2.pack_forget()
            else:
                self.btn_valider.config(text="CrÃ©er le compte",bg=C_GREEN)
                self.lbl_mdp2.pack(anchor="w",padx=16,pady=(8,0)); self.ent_mdp2.pack(padx=16,pady=4,fill="x")
        top=tk.Frame(cadre,bg=C_SURF2); top.pack(fill="x",padx=16,pady=(14,4))
        tk.Radiobutton(top,text="Connexion",variable=self._auth_var,value="login",command=toggle,
            bg=C_SURF2,fg=C_TEXT,selectcolor=C_SURF2,activebackground=C_SURF2,activeforeground=C_TEXT,
            font=(FONT,10)).pack(side="left")
        tk.Radiobutton(top,text="CrÃ©er un compte",variable=self._auth_var,value="creer",command=toggle,
            bg=C_SURF2,fg=C_TEXT,selectcolor=C_SURF2,activebackground=C_SURF2,activeforeground=C_TEXT,
            font=(FONT,10)).pack(side="left",padx=12)
        tk.Label(cadre,text="Pseudo",font=(FONT,10),fg=C_SUB,bg=C_SURF2).pack(anchor="w",padx=16,pady=(8,0))
        self.ent_pseudo_auth=tk.Entry(cadre); self._entree_styler(self.ent_pseudo_auth)
        self.ent_pseudo_auth.pack(padx=16,pady=4,fill="x")
        tk.Label(cadre,text="Mot de passe",font=(FONT,10),fg=C_SUB,bg=C_SURF2).pack(anchor="w",padx=16,pady=(8,0))
        self.ent_mdp=tk.Entry(cadre,show="â¢"); self._entree_styler(self.ent_mdp)
        self.ent_mdp.pack(padx=16,pady=4,fill="x")
        self.lbl_mdp2=tk.Label(cadre,text="Confirmer le mot de passe",font=(FONT,10),fg=C_SUB,bg=C_SURF2)
        self.ent_mdp2=tk.Entry(cadre,show="â¢"); self._entree_styler(self.ent_mdp2)
        self.btn_valider=tk.Button(cadre,text="Se connecter",command=self._valider_auth)
        self._btn_styler(self.btn_valider,C_BLUE); self.btn_valider.pack(padx=16,pady=14,fill="x")
        self.ent_mdp.bind("<Return>",lambda e:self._valider_auth()); self.ent_pseudo_auth.focus()
        tk.Label(f,text=f"ð Identifiants stockÃ©s localement dans {COMPTE_FILE} (jamais sur le rÃ©seau)",
            font=(FONT,9),fg=C_DIM,bg=C_BG,wraplength=420,justify="center").pack(pady=(14,0))

    def _valider_auth(self):
        pseudo=self.ent_pseudo_auth.get().strip(); mdp=self.ent_mdp.get(); mode=self._auth_var.get()
        if not pseudo or not mdp: messagebox.showwarning(APP_NAME,"Remplis le pseudo et le mot de passe."); return
        if mode=="creer":
            mdp2=self.ent_mdp2.get()
            if mdp!=mdp2: messagebox.showwarning(APP_NAME,"Les mots de passe ne correspondent pas."); return
            ok,msg=self.gc.creer(pseudo,mdp)
            if not ok: messagebox.showerror(APP_NAME,msg); return
            messagebox.showinfo(APP_NAME,msg)
        ok,msg=self.gc.verifier(pseudo,mdp)
        if not ok: messagebox.showerror(APP_NAME,msg); return
        self.compte=self.gc.get(pseudo); self.pseudo=pseudo
        for cle in ("sonnerie","notif"):
            if cle not in self.compte: self.compte[cle]=""
        if "bio" not in self.compte: self.compte["bio"]=""
        if "liens" not in self.compte: self.compte["liens"]=[]
        if "theme" not in self.compte: self.compte["theme"]="sombre"
        _appliquer_theme(self.compte.get("theme","sombre"))
        self.root.configure(bg=C_BG)
        _SONS_PERSO["sonnerie"]=self.compte.get("sonnerie","")
        _SONS_PERSO["notif"]=self.compte.get("notif","")
        self.profils[pseudo]=profil_public(self.compte); self.profils[pseudo]["pseudo"]=pseudo
        self.profils[pseudo]["en_ligne"]=True
        self._ecran_demarrage()

    def _ecran_demarrage(self):
        self._reset_frame()
        f=self.frame; f.configure(bg=C_BG)
        self._fond_anime(f,height=60)
        self._titre_anime(f,f"ð¬ {APP_NAME}",C_BLUE,20)
        tk.Label(f,text=VERSION,font=(FONT,9,"bold"),fg=C_YELLOW,bg=C_BG).pack(pady=(0,8))
        barre=tk.Frame(f,bg=C_SURF2); barre.pack(fill="x",padx=20,pady=(0,8))
        badge=self.compte["equip"]["badge"]; niv,_=niveau_from_xp(self.compte["xp"])
        tk.Label(barre,text=f"ð¤ {self.pseudo}  {badge_emoji(badge)}",font=(FONT,11,"bold"),
            fg=couleur_hex(self.compte["equip"]["couleur"]),bg=C_SURF2).pack(side="left",padx=14,pady=8)
        self.lbl_compte=tk.Label(barre,text="",font=(FONT,9),fg=C_SUB,bg=C_SURF2)
        self.lbl_compte.pack(side="right",padx=14,pady=8); self._rafraichir_compte_ui()
        cadre=tk.Frame(f,bg=C_SURF2,highlightbackground=C_INP,highlightthickness=1)
        cadre.pack(padx=40,pady=8,fill="x")
        b1=tk.Button(cadre,text="ð¥ï¸  HÃ©berger une discussion",command=self.demarrer_hote,height=2)
        self._btn_styler(b1,C_BLUE); b1.pack(padx=16,pady=(16,6),fill="x")
        b2=tk.Button(cadre,text="ð  Rejoindre (auto)",command=self.demarrer_rejoindre,height=2)
        self._btn_styler(b2,C_GREEN); b2.pack(padx=16,pady=6,fill="x")
        b3=tk.Button(cadre,text="âï¸  Rejoindre par IP (dernier recours)",command=self.rejoindre_ip_manuel,height=2)
        self._btn_styler(b3,C_INP,C_TEXT); b3.pack(padx=16,pady=6,fill="x")
        b4=tk.Button(cadre,text="ðï¸  Boutique & cosmÃ©tiques",command=self.ouvrir_boutique,height=2)
        self._btn_styler(b4,C_YELLOW,C_BG); b4.pack(padx=16,pady=(6,6),fill="x")
        ligne_bas=tk.Frame(f,bg=C_BG); ligne_bas.pack(fill="x",padx=40,pady=(0,4))
        b5=tk.Button(ligne_bas,text="⚙️  Paramètres",command=self.ouvrir_parametres)
        self._btn_styler(b5,C_PURPLE); b5.pack(fill="x",ipady=4)
        tk.Label(f,text="Astuce : l'hÃ©bergeur lance le salon, les autres le rejoignent automatiquement.",
            font=(FONT,9),fg=C_DIM,bg=C_BG,wraplength=440,justify="center").pack(pady=(10,0))

    def _rafraichir_compte_ui(self):
        if not self.compte: return
        niv,restant=niveau_from_xp(self.compte["xp"])
        txt=f"Lvl {niv}  â¢  {self.compte['coins']} ðª  â¢  {badge_emoji(self.compte['equip']['badge'])}  â¢  XP {self.compte['xp']} (+{restant} â niv.{niv+1})"
        if hasattr(self,"lbl_compte") and self.lbl_compte.winfo_exists(): self.lbl_compte.config(text=txt)

    def ouvrir_boutique(self):
        win=tk.Toplevel(self.root); win.title("ðï¸ Boutique"); win.geometry("540x640")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_anime(win,height=50)
        self.lbl_compte_bout=tk.Label(win,text="",font=(FONT,11,"bold"),fg=C_YELLOW,bg=C_BG)
        self.lbl_compte_bout.pack(pady=8); self._rafraichir_boutique(win)
        nbook=ttk.Notebook(win); nbook.pack(fill="both",expand=True,padx=14,pady=6)
        style=ttk.Style(); style.configure("TNotebook",background=C_BG,borderwidth=0)
        style.configure("TNotebook.Tab",background=C_SURF2,foreground=C_TEXT,padding=12)
        style.map("TNotebook.Tab",background=[("selected",C_BLUE)],foreground=[("selected",C_BG)])
        for cat,catalogue,equip_key in [("ð¨ Couleurs",COULEURS,"couleur"),("ð Badges",BADGES,"badge"),("ð·ï¸ Titres",TITRES,"titre")]:
            page=tk.Frame(nbook,bg=C_BG); nbook.add(page,text=cat)
            self._remplir_boutique_page(page,catalogue,equip_key,win)

    def _rafraichir_boutique(self,win):
        niv,_=niveau_from_xp(self.compte["xp"])
        self.lbl_compte_bout.config(text=f"{self.pseudo}  â¢  Niveau {niv}  â¢  {self.compte['coins']} ðª")

    def _remplir_boutique_page(self,page,catalogue,equip_key,win):
        canvas=tk.Canvas(page,bg=C_BG,highlightthickness=0)
        scroll=tk.Scrollbar(page,command=canvas.yview); inner=tk.Frame(canvas,bg=C_BG)
        inner.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window(0,0,window=inner,anchor="nw"); canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left",fill="both",expand=True); scroll.pack(side="right",fill="y")
        poss_key=equip_key+"s"; possedes=self.compte["possedes"][poss_key]; equipe=self.compte["equip"][equip_key]
        for cid,info in catalogue.items():
            row=tk.Frame(inner,bg=C_SURF2,highlightbackground=C_INP,highlightthickness=1)
            row.pack(fill="x",padx=6,pady=5)
            apercu=self._apercu_cosmetique(equip_key,cid)
            tk.Label(row,text=apercu,font=(FONT,16),bg=C_SURF2,fg=couleur_hex(cid) if equip_key=="couleur" else C_TEXT,width=6).pack(side="left",padx=10,pady=8)
            extra=""
            if info.get("anime"): extra=" â¨"
            tk.Label(row,text=info["nom"]+extra,font=(FONT,11,"bold"),fg=C_TEXT,bg=C_SURF2).pack(side="left",pady=8)
            tk.Label(row,text=f"{info['prix']} ðª",font=(FONT,10),fg=C_GREEN,bg=C_SURF2).pack(side="left",padx=10)
            if cid==equipe: etat,bg="â ÃquipÃ©",C_GREEN
            elif cid in possedes: etat,bg="PossÃ©dÃ© â Ãquiper",C_BLUE
            else: etat,bg=f"Acheter {info['prix']}ðª",C_YELLOW
            b=tk.Button(row,text=etat,command=lambda c=cid,k=equip_key,w=win:self._action_cosmetique(c,k,w))
            self._btn_styler(b,bg if bg!=C_YELLOW else C_YELLOW, C_BG if bg==C_YELLOW else C_BG)
            b.pack(side="right",padx=12,pady=8)

    def _apercu_cosmetique(self,key,cid):
        if key=="couleur": return "â"
        if key=="badge": return badge_emoji(cid) or "â"
        if key=="titre": return "ð·ï¸"
        return ""

    def _action_cosmetique(self,cid,key,win):
        poss_key=key+"s"; possedes=self.compte["possedes"][poss_key]
        if cid==self.compte["equip"][key]: return
        if cid in possedes:
            self.compte["equip"][key]=cid; self.gc.sauver()
            self._rafraichir_boutique(win); self._rafraichir_compte_ui(); self._propager_profil()
            win.destroy(); self.ouvrir_boutique(); return
        prix=COULEURS.get(cid,{}).get("prix") or BADGES.get(cid,{}).get("prix") or TITRES.get(cid,{}).get("prix",0)
        if self.compte["coins"]<prix:
            messagebox.showwarning(APP_NAME,f"Pas assez de coins ({prix} ðª). Discute pour en gagner !"); return
        if not messagebox.askyesno(APP_NAME,f"Acheter pour {prix} ðª ?"): return
        self.compte["coins"]-=prix; self.compte["possedes"][poss_key].append(cid)
        self.compte["equip"][key]=cid; self.gc.sauver()
        self._rafraichir_boutique(win); self._rafraichir_compte_ui(); self._propager_profil()
        win.destroy(); self.ouvrir_boutique()

    def demarrer_hote(self):
        self.mode="host"; self._propager_profil_local()
        threading.Thread(target=self._servir_tcp,daemon=True).start()
        threading.Thread(target=self._servir_udp,daemon=True).start()
        self._construire_interface_chat()

    def _propager_profil_local(self):
        self.profils[self.pseudo]=profil_public(self.compte); self.profils[self.pseudo]["pseudo"]=self.pseudo
        self.profils[self.pseudo]["en_ligne"]=True

    def _servir_tcp(self):
        try:
            srv=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            srv.bind(("0.0.0.0",TCP_PORT)); srv.listen(); self.tcp_server=srv
        except OSError as e:
            self.ui_queue.put(("err",f"Impossible d'hÃ©berger (port {TCP_PORT}) : {e}")); return
        while self.running:
            try: conn,addr=srv.accept()
            except OSError: break
            with self.clients_lock: self.clients.append(conn)
            threading.Thread(target=self._gerer_client,args=(conn,addr),daemon=True).start()

    def _gerer_client(self,conn,addr):
        pseudo_client=None
        def on_line(m):
            nonlocal pseudo_client
            t=m.get("type")
            if t=="hello":
                pseudo_client=(m.get("pseudo") or "?")[:MAX_PSEUDO]
                prof=m.get("profil",{}); prof["pseudo"]=pseudo_client; self.profils[pseudo_client]=prof
                with self.clients_lock:
                    self.pseudo_to_sock[pseudo_client]=conn; self.client_ips[pseudo_client]=addr[0]
                self.ui_queue.put(("sys",f"ð¢ {pseudo_client} a rejoint le salon"))
                self.ui_queue.put(("profil",prof)); self._maj_compteur(1)
                try: conn.sendall(make_msg("profils_init",profils=list(self.profils.values())))
                except OSError: pass
                self._diffuser(make_msg("profil",profil=prof),except_=conn)
                self._diffuser(make_msg("sys",text=f"ð¢ {pseudo_client} a rejoint"),except_=conn)
            elif t=="msg":
                p=m.get("pseudo","?"); txt=m.get("text","")
                self.ui_queue.put(("msg",p,txt)); self._diffuser(make_msg("msg",pseudo=p,text=txt),except_=conn)
            elif t=="mp": self._router_mp(m,conn)
            elif t=="profil_update":
                prof=m.get("profil",{}); prof["pseudo"]=pseudo_client; self.profils[pseudo_client]=prof
                self.ui_queue.put(("profil",prof)); self._diffuser(make_msg("profil",profil=prof),except_=conn)
            elif t=="call_request": self._router_appel(m,conn,addr[0])
            elif t=="call_accept": self._router_call_accept(m,conn)
            elif t=="call_ready": self._router_call_ready(m,conn)
            elif t=="call_reject": self._router_call_reject(m)
            elif t=="call_end": self._router_call_end(m,conn)
        recv_lines(conn,on_line)
        with self.clients_lock:
            if conn in self.clients: self.clients.remove(conn)
            if pseudo_client and self.pseudo_to_sock.get(pseudo_client) is conn:
                del self.pseudo_to_sock[pseudo_client]
            self.client_ips.pop(pseudo_client,None)
        try: conn.close()
        except OSError: pass
        if pseudo_client:
            self._maj_compteur(-1)
            self.ui_queue.put(("sys",f"ð´ {pseudo_client} a quittÃ© le salon"))
            self._diffuser(make_msg("sys",text=f"ð´ {pseudo_client} a quittÃ©"),except_=conn)
            self.profils.pop(pseudo_client,None)

    def _diffuser(self,data,except_=None):
        with self.clients_lock: cibles=[c for c in self.clients if c is not except_]
        for c in cibles:
            try: c.sendall(data)
            except OSError:
                with self.clients_lock:
                    if c in self.clients: self.clients.remove(c)

    def _maj_compteur(self,delta):
        self.nb_connectes+=delta; self.root.after(0,self._rafraichir_statut)

    def _router_mp(self,m,conn):
        src=m.get("from","?"); dest=m.get("to",""); txt=m.get("text","")
        if dest==self.pseudo: self.ui_queue.put(("mp",src,txt)); return
        sd=self.pseudo_to_sock.get(dest)
        if sd:
            try: sd.sendall(make_msg("mp",from_=src,text=txt))
            except OSError: pass
        else:
            try: conn.sendall(make_msg("sys",text=f"â  {dest} est introuvable."))
            except OSError: pass

    def _router_appel(self,m,conn,src_ip):
        src=m.get("from","?"); dest=m.get("to","")
        if dest==self.pseudo: self.ui_queue.put(("call_incoming",src)); return
        sd=self.pseudo_to_sock.get(dest)
        if sd:
            try: sd.sendall(make_msg("call_incoming",from_=src))
            except OSError: conn.sendall(make_msg("call_reject",from_=dest))
        else: conn.sendall(make_msg("call_reject",from_=dest))

    def _router_call_accept(self,m,conn):
        src=m.get("from","?"); dest=m.get("to","")
        audio_ip=m.get("audio_ip"); audio_port=m.get("audio_port")
        if dest==self.pseudo: self.ui_queue.put(("call_accepted",src,audio_ip,audio_port)); return
        sd=self.pseudo_to_sock.get(dest)
        if sd: sd.sendall(make_msg("call_accepted",from_=src,audio_ip=audio_ip,audio_port=audio_port))

    def _router_call_ready(self,m,conn):
        src=m.get("from","?"); dest=m.get("to","")
        audio_ip=m.get("audio_ip"); audio_port=m.get("audio_port")
        if dest==self.pseudo: self.ui_queue.put(("call_ready",src,audio_ip,audio_port)); return
        sd=self.pseudo_to_sock.get(dest)
        if sd: sd.sendall(make_msg("call_ready",from_=src,audio_ip=audio_ip,audio_port=audio_port))

    def _router_call_reject(self,m):
        dest=m.get("to",m.get("from",""))
        if dest==self.pseudo: self.ui_queue.put(("call_reject",m.get("from","?")))
        else:
            sd=self.pseudo_to_sock.get(dest)
            if sd: sd.sendall(make_msg("call_reject",from_=m.get("from","?")))

    def _router_call_end(self,m,conn):
        dest=m.get("to",""); src=m.get("from","?")
        if dest==self.pseudo: self.ui_queue.put(("call_end",src))
        else:
            sd=self.pseudo_to_sock.get(dest)
            if sd: sd.sendall(make_msg("call_end",from_=src))

    def _servir_udp(self):
        try:
            s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
            s.bind(("0.0.0.0",UDP_PORT)); self.udp_sock=s
        except OSError as e: log.warning("UDP: %s",e); return
        annonce=make_udp("announce",port=TCP_PORT,name=APP_NAME,host_pseudo=self.pseudo,version=VERSION)
        prochaine=time.time()
        while self.running:
            try:
                s.settimeout(0.5); data,addr=s.recvfrom(4096)
            except socket.timeout:
                if time.time()>=prochaine:
                    try: s.sendto(annonce,("255.255.255.255",UDP_PORT))
                    except OSError: pass
                    prochaine=time.time()+ANNOUNCE_EVERY
                continue
            except OSError: break
            msg=parse_udp(data)
            if msg and msg.get("type")=="discover":
                try: s.sendto(annonce,addr)
                except OSError: pass

    def demarrer_rejoindre(self):
        self.mode="client"; self._ecran_chargement("Recherche des discussions sur le rÃ©seauâ¦")
        threading.Thread(target=self._scan_reseau,daemon=True).start()

    def rejoindre_ip_manuel(self):
        ip=simpledialog.askstring("Connexion manuelle","Adresse IP de l'hÃ©bergeur :",parent=self.root)
        if not ip: return
        ip=ip.strip(); self.mode="client"; self.cible=(ip,TCP_PORT,f"{ip}:{TCP_PORT}")
        self._ecran_chargement(f"Connexion Ã  {ip}:{TCP_PORT}â¦")
        threading.Thread(target=self._connecter_a,args=(ip,TCP_PORT),daemon=True).start()

    def _scan_reseau(self):
        trouve={}
        try:
            s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
            s.bind(("0.0.0.0",UDP_PORT))
        except OSError as e:
            self.ui_queue.put(("connect_fail",f"Scan impossible : {e}")); return
        try: s.sendto(make_udp("discover"),("255.255.255.255",UDP_PORT))
        except OSError: pass
        echeance=time.time()+SCAN_TIME
        while time.time()<echeance and self.running:
            try: s.settimeout(0.4); data,addr=s.recvfrom(4096)
            except socket.timeout: continue
            except OSError: break
            msg=parse_udp(data)
            if not msg or msg.get("type")!="announce": continue
            ip=addr[0]; port=int(msg.get("port",TCP_PORT)); nom=msg.get("name",f"{ip}:{port}")
            hp=msg.get("host_pseudo",""); v=msg.get("version","")
            cle=(ip,port)
            if cle not in trouve:
                trouve[cle]=(nom,hp,v); self.ui_queue.put(("scan_progress",len(trouve)))
        try: s.close()
        except OSError: pass
        serveurs=[(ip,port,nom,hp,v) for (ip,port),(nom,hp,v) in trouve.items()]
        self.ui_queue.put(("discovered",serveurs))

    def _ecran_chargement(self,texte):
        self._reset_frame()
        f=self.frame; f.configure(bg=C_BG)
        self._fond_anime(f,height=50)
        self.lbl_spinner=tk.Label(f,text="â ",font=(FONT,42),fg=C_BLUE,bg=C_BG)
        self.lbl_spinner.pack(pady=(80,8))
        self.lbl_chargement=tk.Label(f,text=texte,font=(FONT,12),fg=C_TEXT,bg=C_BG)
        self.lbl_chargement.pack(pady=4)
        self.lbl_compteur=tk.Label(f,text="0 salon trouvÃ©",font=(FONT,10),fg=C_GREEN,bg=C_BG)
        self.lbl_compteur.pack(pady=2)
        self._spin_idx=0; self._animer_spinner()
        b=tk.Button(f,text="Annuler",command=self._ecran_demarrage)
        self._btn_styler(b,C_INP,C_TEXT); b.pack(pady=30)

    def _animer_spinner(self):
        if hasattr(self,"lbl_spinner") and self.lbl_spinner.winfo_exists():
            self.lbl_spinner.config(text=SPINNER[self._spin_idx%len(SPINNER)])
            self._spin_idx+=1; self.root.after(90,self._animer_spinner)

    def _maj_chargement(self,n):
        if hasattr(self,"lbl_compteur") and self.lbl_compteur.winfo_exists():
            p="s" if n!=1 else ""; self.lbl_compteur.config(text=f"{n} salon{p} trouvÃ©{p}")

    def _fin_scan(self,serveurs):
        if not serveurs:
            self._reset_frame(); f=self.frame; f.configure(bg=C_BG)
            tk.Label(f,text="ð",font=(FONT,40),bg=C_BG).pack(pady=(80,4))
            tk.Label(f,text="Aucune discussion trouvÃ©e",font=(FONT,13,"bold"),fg=C_TEXT,bg=C_BG).pack(pady=4)
            tk.Label(f,text="Demande Ã  un ami de lancer un salon, ou hÃ©berge le tien !",
                font=(FONT,10),fg=C_SUB,bg=C_BG,wraplength=380).pack(pady=6)
            b1=tk.Button(f,text="ð¥ï¸  HÃ©berger Ã  la place",command=self.demarrer_hote)
            self._btn_styler(b1,C_BLUE); b1.pack(pady=18)
            b2=tk.Button(f,text="âï¸  Saisir l'IP manuellement",command=self.rejoindre_ip_manuel)
            self._btn_styler(b2,C_INP,C_TEXT); b2.pack(pady=4)
            b3=tk.Button(f,text="â© Recommencer",command=self.demarrer_rejoindre)
            self._btn_styler(b3,C_INP,C_TEXT); b3.pack()
            return
        self._ecran_choix_serveur(serveurs)

    def _ecran_choix_serveur(self,serveurs):
        self._reset_frame(); f=self.frame; f.configure(bg=C_BG)
        self._titre_anime(f,"Salons disponibles",C_GREEN,16)
        liste=tk.Listbox(f,font=(FONT,12),bg=C_SURF2,fg=C_TEXT,selectbackground=C_BLUE,
            selectforeground=C_BG,relief="flat",bd=0,highlightbackground=C_INP,
            height=min(len(serveurs),10),activestyle="none")
        for ip,port,nom,hp,v in serveurs:
            lib=f"  {nom}"
            if hp: lib+=f"  (chez {hp})"
            lib+=f"  â  {ip}:{port}"
            if v: lib+=f"  [{v}]"
            liste.insert(tk.END,lib)
        liste.pack(padx=40,pady=6,fill="x"); liste.selection_set(0)
        def connecter():
            sel=liste.curselection()
            if not sel: messagebox.showinfo(APP_NAME,"Choisis un salon."); return
            ip,port,nom,hp,v=serveurs[sel[0]]; self.cible=(ip,port,nom)
            self._ecran_chargement(f"Connexion Ã  {nom} ({ip})â¦")
            threading.Thread(target=self._connecter_a,args=(ip,port),daemon=True).start()
        b1=tk.Button(f,text="Se connecter",command=connecter)
        self._btn_styler(b1,C_GREEN); b1.pack(pady=16)
        b2=tk.Button(f,text="âï¸  IP manuelle",command=self.rejoindre_ip_manuel)
        self._btn_styler(b2,C_INP,C_TEXT); b2.pack()

    def _connecter_a(self,ip,port):
        try:
            s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            s.settimeout(5.0); s.connect((ip,port)); s.settimeout(None)
            self.host_ip=ip; self._propager_profil_local()
            s.sendall(make_msg("hello",pseudo=self.pseudo,profil=profil_public(self.compte)))
            self.sock=s
            threading.Thread(target=self._boucle_reception,daemon=True).start()
            self.ui_queue.put(("connected",))
        except OSError as e: self.ui_queue.put(("connect_fail",f"Connexion Ã©chouÃ©e : {e}"))

    def _on_connecte(self): self._construire_interface_chat()

    def _echec_connexion(self,msg):
        messagebox.showerror(APP_NAME,msg); self._ecran_demarrage()

    def _boucle_reception(self):
        def on_line(m):
            t=m.get("type")
            if t=="msg": self.ui_queue.put(("msg",m.get("pseudo","?"),m.get("text","")))
            elif t=="sys": self.ui_queue.put(("sys",m.get("text","")))
            elif t=="mp": self.ui_queue.put(("mp",m.get("from_","?"),m.get("text","")))
            elif t=="profil": self.ui_queue.put(("profil",m.get("profil",{})))
            elif t=="profils_init": self.ui_queue.put(("profils_init",m.get("profils",[])))
            elif t=="call_incoming": self.ui_queue.put(("call_incoming",m.get("from_","?")))
            elif t=="call_accepted": self.ui_queue.put(("call_accepted",m.get("from_","?"),m.get("audio_ip"),m.get("audio_port")))
            elif t=="call_ready": self.ui_queue.put(("call_ready",m.get("from_","?"),m.get("audio_ip"),m.get("audio_port")))
            elif t=="call_reject": self.ui_queue.put(("call_reject",m.get("from_","?")))
            elif t=="call_end": self.ui_queue.put(("call_end",m.get("from_","?")))
        recv_lines(self.sock,on_line)
        self.ui_queue.put(("err","Connexion perdue avec le serveur."))

    def _construire_interface_chat(self):
        self._reset_frame(); f=self.frame; f.configure(bg=C_BG)
        barre=tk.Frame(f,bg=C_SURF2); barre.pack(fill="x")
        self._titre_anime_barre=tk.Label(barre,text=f"ð¬ {APP_NAME}",font=(FONT,12,"bold"),fg=C_TEXT,bg=C_SURF2)
        self._titre_anime_barre.pack(side="left",padx=14,pady=8)
        self._anim_titre_barre()
        self.lbl_statut=tk.Label(barre,text="",font=(FONT,9),fg=C_SUB,bg=C_SURF2)
        self.lbl_statut.pack(side="right",padx=14,pady=8); self._rafraichir_statut()
        corps=tk.Frame(f,bg=C_BG); corps.pack(fill="both",expand=True,padx=8,pady=8)
        cadre_msg=tk.Frame(corps,bg=C_BG); cadre_msg.pack(side="left",fill="both",expand=True)
        scroll=tk.Scrollbar(cadre_msg); scroll.pack(side="right",fill="y")
        self.zone=tk.Text(cadre_msg,font=(FONT,11),bg=C_BG2,fg=C_TEXT,insertbackground=C_TEXT,
            yscrollcommand=scroll.set,relief="flat",bd=0,padx=12,pady=10,wrap="word",state="disabled")
        self.zone.pack(side="left",fill="both",expand=True); scroll.config(command=self.zone.yview)
        self.zone.tag_config("sys",foreground=C_DIM,font=(FONT,9,"italic"))
        self.zone.tag_config("erreur",foreground=C_RED,font=(FONT,10,"bold"))
        self.zone.tag_config("moi",foreground=C_BLUE,font=(FONT,11,"bold"))
        self.zone.tag_config("moi_texte",foreground=C_TEXT,font=(FONT,11))
        self.zone.tag_config("autre_texte",foreground="#bac2de",font=(FONT,11))
        self.zone.tag_bind("pseudo","<Button-1>",self._clic_pseudo_event)
        panneau_d=tk.Frame(corps,bg=C_BG2,width=160)
        panneau_d.pack(side="right",fill="y",padx=(8,0)); panneau_d.pack_propagate(False)
        tk.Label(panneau_d,text="Participants",font=(FONT,9,"bold"),fg=C_SUB,bg=C_BG2).pack(pady=(8,4))
        self.liste_part=tk.Text(panneau_d,bg=C_BG2,fg=C_TEXT,relief="flat",bd=0,font=(FONT,10),
            wrap="none",cursor="hand2",height=20)
        self.liste_part.pack(fill="both",expand=True,padx=6)
        self.liste_part.tag_bind("p","<Button-1>",self._clic_pseudo_liste)
        self._rafraichir_liste_participants()
        barre_saisie=tk.Frame(f,bg=C_BG); barre_saisie.pack(fill="x",padx=8,pady=(0,8))
        self.entree=tk.Entry(barre_saisie); self._entree_styler(self.entree)
        self.entree.pack(side="left",fill="x",expand=True,ipady=8,padx=(0,8))
        self.entree.bind("<Return>",lambda e:self.envoyer()); self.entree.focus()
        b0=tk.Button(barre_saisie,text="😀",command=self.ouvrir_selecteur_emoji,padx=10)
        self._btn_styler(b0,C_YELLOW,C_BG); b0.pack(side="left",ipady=4,padx=(0,4))
        b1=tk.Button(barre_saisie,text="Envoyer â¤",command=self.envoyer,padx=14)
        self._btn_styler(b1,C_BLUE); b1.pack(side="left",ipady=4)
        b2=tk.Button(barre_saisie,text="ðï¸",command=self.ouvrir_boutique,padx=10)
        self._btn_styler(b2,C_INP,C_YELLOW); b2.pack(side="left",padx=(8,0),ipady=4)
        b3=tk.Button(barre_saisie,text="📎",command=self._attacher_media,padx=10)
        self._btn_styler(b3,C_TEAL,C_BG); b3.pack(side="left",padx=(8,0),ipady=4)
        self.afficher_systeme(f"ð¢ Bienvenue {self.pseudo} !")
        if self.mode=="host":
            self.afficher_systeme(f"Tu hÃ©berges sur {local_ip()}:{TCP_PORT}. Partage cette IP si l'auto-dÃ©couverte Ã©choue.")
        if not AUDIO_OK:
            self.afficher_systeme("â¹ Appels vocaux indisponibles (installe PyAudio). Les appels fonctionnent en mode texte.")

    def _anim_titre_barre(self):
        couleurs=[C_BLUE,C_PURPLE,C_TEAL,C_GREEN]
        idx=[0]
        def anim():
            if hasattr(self,"_titre_anime_barre") and self._titre_anime_barre.winfo_exists():
                self._titre_anime_barre.config(fg=couleurs[idx[0]%len(couleurs)])
                idx[0]+=1; self.root.after(800,anim)
        anim()

    def _rafraichir_statut(self):
        if not hasattr(self,"lbl_statut") or not self.lbl_statut.winfo_exists(): return
        if self.mode=="host":
            self.lbl_statut.config(text=f"ð¢ {local_ip()}:{TCP_PORT}  â¢  {self.nb_connectes} connectÃ©(s) en plus de toi")
        elif self.cible:
            ip,port,nom=self.cible; self.lbl_statut.config(text=f"ðµ {nom} ({ip}:{port})")

    def _rafraichir_liste_participants(self):
        if not hasattr(self,"liste_part"): return
        self.liste_part.config(state="normal"); self.liste_part.delete("1.0",tk.END)
        for p in self.profils:
            prof=self.profils[p]; badge=badge_emoji(prof.get("badge","etoile"))
            en_ligne=prof.get("en_ligne",True)
            point="🟢" if en_ligne else "⚫"
            self.liste_part.insert(tk.END,f" {point} {badge} {p}\n","p")
        self.liste_part.config(state="disabled")

    def _clic_pseudo_liste(self,event=None):
        idx=self.liste_part.index("@%d,%d"%(event.x,event.y)); ligne=int(idx.split(".")[0])
        pseudos=list(self.profils.keys())
        if 1<=ligne<=len(pseudos): self._ouvrir_carte_profil(pseudos[ligne-1])

    def _clic_pseudo_event(self,event):
        idx=self.zone.index("@%d,%d"%(event.x,event.y))
        for t in self.zone.tag_names(idx):
            if t.startswith("usr_"): self._ouvrir_carte_profil(t[4:]); return

    def _maj_profil(self,prof):
        p=prof.get("pseudo")
        if p: self.profils[p]=prof; self._rafraichir_liste_participants()

    def _init_profils(self,liste):
        for prof in liste:
            p=prof.get("pseudo")
            if p: self.profils[p]=prof
        self._rafraichir_liste_participants()

    def _propager_profil(self):
        self._propager_profil_local(); prof=self.profils[self.pseudo]
        data=make_msg("profil_update",profil=prof)
        if self.mode=="host": self._diffuser(data)
        elif self.sock:
            try: self.sock.sendall(data)
            except OSError: pass

    def _couleur_tag(self,pseudo):
        prof=self.profils.get(pseudo,{}); cid=prof.get("couleur",COULEURS_DEFAUT)
        couleur=couleur_hex(cid); tag="usr_"+pseudo
        if tag not in self.couleurs_tags and hasattr(self,"zone"):
            self.zone.tag_config(tag,foreground=couleur,font=(FONT,11,"bold"))
            self.couleurs_tags.add(tag)
            if couleur_anime(cid): self._animer_pseudo_tag(pseudo,tag,cid)
        return tag

    def _animer_pseudo_tag(self,pseudo,tag,cid):
        if pseudo in self._anim_pseudos: return
        self._anim_pseudos[pseudo]=True
        if cid=="arc":
            palette=RAINBOW
        elif cid=="galaxy":
            palette=["#cba6f7","#89b4fa","#f5c2e7","#b4befe","#cba6f7"]
        elif cid=="feu":
            palette=["#f38ba8","#fab387","#f9e2af","#f38ba8","#eba0ac"]
        else:
            palette=[couleur_hex(cid)]
        idx=[0]
        def anim():
            if not hasattr(self,"zone") or not self.zone.winfo_exists(): return
            self.zone.tag_config(tag,foreground=palette[idx[0]%len(palette)])
            idx[0]+=1; self.root.after(400,anim)
        anim()

    def _ouvrir_carte_profil(self,pseudo):
        prof=self.profils.get(pseudo,{"pseudo":pseudo,"niveau":0,"titre":TITRE_DEFAUT,
            "badge":"etoile","couleur":COULEURS_DEFAUT,"msgs":0,"coins":0,"appels":0,"xp":0,
            "bio":"","liens":[],"en_ligne":True})
        win=tk.Toplevel(self.root); win.title("Profil"); win.geometry("400x580")
        win.configure(bg=C_BG); win.transient(self.root)
        self._fond_anime(win,height=50)
        badge=badge_emoji(prof.get("badge","etoile"))
        couleur=couleur_hex(prof.get("couleur",COULEURS_DEFAUT))
        entete=tk.Frame(win,bg=C_BG); entete.pack(fill="x",padx=16,pady=(10,0))
        lbl_pseudo=tk.Label(entete,text=f"{badge} {pseudo}",font=(FONT,20,"bold"),fg=couleur,bg=C_BG)
        lbl_pseudo.pack(side="left")
        if couleur_anime(prof.get("couleur",COULEURS_DEFAUT)):
            self._animer_lbl_pseudo(lbl_pseudo,prof.get("couleur"))
        en_ligne=prof.get("en_ligne",True)
        statut_txt="🟢 En ligne" if en_ligne else "⚫ Hors ligne"
        statut_col=C_GREEN if en_ligne else C_DIM
        tk.Label(entete,text=statut_txt,font=(FONT,9,"bold"),fg=statut_col,bg=C_BG).pack(side="right",pady=(6,0))
        tk.Label(win,text="« "+titre_nom(prof.get("titre","membre"))+" »",
            font=(FONT,11,"italic"),fg=C_SUB,bg=C_BG).pack()
        niv,xp_dans,taille=info_niveau(prof.get("xp",0))
        tk.Label(win,text=f"Niveau {niv}",font=(FONT,13,"bold"),fg=C_YELLOW,bg=C_BG).pack(pady=(8,2))
        barre_xp=tk.Frame(win,bg=C_INP,height=10); barre_xp.pack(fill="x",padx=40,pady=(0,4))
        progress=(xp_dans/taille) if taille else 0
        self._anim_barre_xp(barre_xp,progress)
        tk.Label(win,text=f"{xp_dans}/{taille} XP",font=(FONT,8),fg=C_DIM,bg=C_BG).pack(pady=(0,8))
        corps=tk.Frame(win,bg=C_BG); corps.pack(fill="both",expand=True,padx=12,pady=4)
        bio=prof.get("bio","")
        if bio:
            tk.Label(corps,text="📝 À propos",font=(FONT,10,"bold"),fg=C_SUB,bg=C_BG).pack(anchor="w",pady=(4,2))
            tk.Label(corps,text=bio,font=(FONT,10),fg=C_TEXT,bg=C_BG,wraplength=350,justify="left").pack(anchor="w",pady=(0,8))
        liens=prof.get("liens",[])
        if liens:
            tk.Label(corps,text="🔗 Liens",font=(FONT,10,"bold"),fg=C_SUB,bg=C_BG).pack(anchor="w",pady=(4,2))
            zone_liens=tk.Text(corps,font=(FONT,10),bg=C_BG2,fg=C_TEXT,relief="flat",bd=0,
                wrap="word",height=min(4,len(liens)),width=40,padx=8,pady=6)
            zone_liens.pack(anchor="w",fill="x",pady=(0,8))
            for lien in liens:
                if not lien: continue
                ltag="lk_"+str(id(lien))
                zone_liens.tag_config(ltag,foreground=C_BLUE,underline=True)
                zone_liens.tag_bind(ltag,"<Button-1>",lambda e,c=lien:webbrowser.open(c))
                zone_liens.tag_bind(ltag,"<Enter>",lambda e,w=zone_liens:w.config(cursor="hand2"))
                zone_liens.tag_bind(ltag,"<Leave>",lambda e,w=zone_liens:w.config(cursor=""))
                zone_liens.insert(tk.END,lien+"\n",ltag)
            zone_liens.config(state="disabled")
        for lib,val in [("💬 Messages",prof.get("msgs",0)),("🪙 Coins",prof.get("coins",0)),
            ("📞 Appels",prof.get("appels",0)),("✨ XP",prof.get("xp",0))]:
            row=tk.Frame(corps,bg=C_BG); row.pack(fill="x",pady=3)
            tk.Label(row,text=lib,font=(FONT,11),fg=C_TEXT,bg=C_BG).pack(side="left")
            tk.Label(row,text=str(val),font=(FONT,11,"bold"),fg=C_GREEN,bg=C_BG).pack(side="right")
        tk.Label(corps,text="Cosmétiques équipés",font=(FONT,10,"bold"),fg=C_SUB,bg=C_BG).pack(anchor="w",pady=(12,4))
        tk.Label(corps,text=f"🎨 Couleur : {COULEURS.get(prof.get('couleur'),{}).get('nom','?')}\n"
            f"🏅 Badge : {BADGES.get(prof.get('badge'),{}).get('nom','?')}\n"
            f"🏷 Titre : {titre_nom(prof.get('titre','membre'))}",
            font=(FONT,10),fg=C_TEXT,bg=C_BG,justify="left").pack(anchor="w")
        if pseudo==self.pseudo:
            b_mod=tk.Button(corps,text="\u270f\ufe0f Modifier mon profil",command=lambda:self._modifier_profil(win))
            self._btn_styler(b_mod,C_PURPLE); b_mod.pack(pady=12)
        else:
            btns=tk.Frame(corps,bg=C_BG); btns.pack(pady=12)
            b1=tk.Button(btns,text="\u2709 MP",command=lambda:self._ouvrir_fenetre_mp(pseudo))
            self._btn_styler(b1,C_BLUE); b1.pack(side="left",padx=6)
            b2=tk.Button(btns,text="📞 Appeler",command=lambda:self._demarrer_appel(pseudo))
            self._btn_styler(b2,C_GREEN); b2.pack(side="left",padx=6)

    def _modifier_profil(self,parent_win):
        win=tk.Toplevel(self.root); win.title("Modifier mon profil"); win.geometry("460x420")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_anime(win,height=40)
        tk.Label(win,text="\u270f\ufe0f Modifier mon profil",font=(FONT,15,"bold"),fg=C_PURPLE,bg=C_BG).pack(pady=(8,8))
        tk.Label(win,text="📝 Bio",font=(FONT,10,"bold"),fg=C_SUB,bg=C_BG).pack(anchor="w",padx=24)
        txt_bio=tk.Text(win,font=(FONT,11),bg=C_INP,fg=C_TEXT,insertbackground=C_TEXT,
            relief="flat",bd=0,wrap="word",height=4,padx=10,pady=8)
        txt_bio.pack(fill="x",padx=24,pady=(2,8))
        txt_bio.insert("1.0",self.compte.get("bio",""))
        tk.Label(win,text="🔗 Liens (un par ligne)",font=(FONT,10,"bold"),fg=C_SUB,bg=C_BG).pack(anchor="w",padx=24)
        txt_liens=tk.Text(win,font=(FONT,11),bg=C_INP,fg=C_TEXT,insertbackground=C_TEXT,
            relief="flat",bd=0,wrap="word",height=5,padx=10,pady=8)
        txt_liens.pack(fill="x",padx=24,pady=(2,8))
        txt_liens.insert("1.0","\n".join(self.compte.get("liens",[])))
        def sauver():
            bio=txt_bio.get("1.0",tk.END).strip()[:300]
            liens_raw=txt_liens.get("1.0",tk.END).strip().split("\n")
            liens=[l.strip() for l in liens_raw if l.strip()][:10]
            self.compte["bio"]=bio; self.compte["liens"]=liens
            self.gc.sauver(); self._propager_profil()
            win.destroy(); parent_win.destroy(); self._ouvrir_carte_profil(self.pseudo)
            messagebox.showinfo(APP_NAME,"Profil mis à jour !")
        b=tk.Button(win,text="\u2714 Enregistrer",command=sauver)
        self._btn_styler(b,C_GREEN); b.pack(pady=10)

    def _animer_lbl_pseudo(self,lbl,cid):
        if cid=="arc": palette=RAINBOW
        elif cid=="galaxy": palette=["#cba6f7","#89b4fa","#f5c2e7","#b4befe"]
        elif cid=="feu": palette=["#f38ba8","#fab387","#f9e2af","#eba0ac"]
        else: palette=[couleur_hex(cid)]
        idx=[0]
        def anim():
            if lbl.winfo_exists():
                lbl.config(fg=palette[idx[0]%len(palette)]); idx[0]+=1; self.root.after(400,anim)
        anim()

    def _anim_barre_xp(self,barre,target):
        cur=[0.0]
        def anim():
            if not barre.winfo_exists(): return
            cur[0]+=0.05
            if cur[0]>target: cur[0]=target
            for w in barre.winfo_children(): w.destroy()
            tk.Frame(barre,bg=C_GREEN).place(x=0,y=0,relwidth=cur[0],relheight=1)
            if cur[0]<target: self.root.after(20,anim)
        anim()

    def envoyer(self):
        texte=self.entree.get().strip()
        if not texte: return
        self.entree.delete(0,tk.END)
        data=make_msg("msg",pseudo=self.pseudo,text=texte)
        if self.mode=="host": self._diffuser(data)
        else:
            try: self.sock.sendall(data)
            except OSError: self.afficher_erreur("Connexion perdue : message non envoyÃ©."); return
        self._gagner_xp(1,coins=1,msgs=1)
        self.afficher_message(self.pseudo,texte,moi=True)
        for mot in texte.split():
            if mot.startswith("@") and mot[1:] in self.profils and mot[1:]!=self.pseudo:
                self._toast(f"ð·ï¸ Tu as mentionnÃ© {mot[1:]}",None)

    def _gagner_xp(self,xp,coins=0,msgs=0,appels=0):
        ancien_niv,_=niveau_from_xp(self.compte["xp"])
        self.compte["xp"]+=xp; self.compte["coins"]+=coins
        self.compte["msgs"]+=msgs; self.compte["appels"]+=appels
        nouveau_niv,_=niveau_from_xp(self.compte["xp"])
        self.gc.sauver(); self._rafraichir_compte_ui(); self._propager_profil_local()
        if nouveau_niv>ancien_niv:
            self.compte["coins"]+=50; self.gc.sauver(); self._rafraichir_compte_ui()
            self._toast(f"ð Niveau {nouveau_niv} ! +50 ðª",None); beep(1200,200)

    def afficher_message(self,pseudo,texte,moi=False):
        if not hasattr(self,"zone"): return
        prof=self.profils.get(pseudo,{}); badge=badge_emoji(prof.get("badge","etoile"))
        self.zone.config(state="normal")
        prefixe=f"{badge} [{pseudo}]"
        if moi:
            self.zone.insert(tk.END,prefixe,"moi")
        else:
            debut=self.zone.index("end"); self.zone.insert(tk.END,prefixe)
            self.zone.tag_add(self._couleur_tag(pseudo),debut,"end")
            self.zone.tag_add("pseudo",debut,"end")
        self.zone.insert(tk.END,"  ")
        self._rendre_liens(self.zone,texte,"moi_texte" if moi else "autre_texte")
        self.zone.insert(tk.END,"\n")
        self.zone.config(state="disabled"); self.zone.see(tk.END)

    def afficher_systeme(self,texte):
        if not hasattr(self,"zone"): return
        self.zone.config(state="normal"); self.zone.insert(tk.END,texte+"\n","sys")
        self.zone.config(state="disabled"); self.zone.see(tk.END)

    def afficher_erreur(self,texte):
        if not hasattr(self,"zone"): return
        self.zone.config(state="normal"); self.zone.insert(tk.END,"â  "+texte+"\n","erreur")
        self.zone.config(state="disabled"); self.zone.see(tk.END)

    def _ouvrir_fenetre_mp(self,dest):
        if dest in self.fenetres_mp and self.fenetres_mp[dest].winfo_exists():
            self.fenetres_mp[dest].lift(); self.fenetres_mp[dest].focus_set(); return
        win=tk.Toplevel(self.root); win.title(f"MP avec {dest}"); win.geometry("420x440")
        win.configure(bg=C_BG); win.transient(self.root)
        self._fond_anime(win,height=35)
        tk.Label(win,text=f"ð Conversation privÃ©e avec {dest}",font=(FONT,11,"bold"),fg=C_TEXT,bg=C_BG).pack(pady=6)
        scroll=tk.Scrollbar(win); scroll.pack(side="right",fill="y")
        txt=tk.Text(win,font=(FONT,11),bg=C_BG2,fg=C_TEXT,yscrollcommand=scroll.set,
            relief="flat",bd=0,padx=10,pady=10,wrap="word",state="disabled")
        txt.pack(fill="both",expand=True,padx=8,pady=4); scroll.config(command=txt.yview)
        win.txt=txt
        entree_mp=tk.Entry(win); self._entree_styler(entree_mp)
        entree_mp.pack(side="left",fill="x",expand=True,padx=(8,4),pady=8,ipady=6)
        def envoyer_mp(e=None):
            texte=entree_mp.get().strip()
            if not texte: return
            entree_mp.delete(0,tk.END); self._envoyer_mp(dest,texte)
            self._afficher_mp(dest,self.pseudo,texte,win,win.txt,moi=True)
        entree_mp.bind("<Return>",envoyer_mp)
        b=tk.Button(win,text="â¤",command=envoyer_mp,padx=14)
        self._btn_styler(b,C_BLUE); b.pack(side="left",padx=(0,8),pady=8,ipady=6)
        for src,msg in self.mp_historique.get(dest,[]):
            self._afficher_mp(dest,src,msg,win,win.txt,moi=(src==self.pseudo))
        win.protocol("WM_DELETE_WINDOW",lambda:self._fermer_fenetre_mp(dest,win))
        self.fenetres_mp[dest]=win; self.mp_non_lus[dest]=0

    def _fermer_fenetre_mp(self,dest,win):
        win.destroy(); self.fenetres_mp.pop(dest,None)

    def _envoyer_mp(self,dest,texte):
        if self.mode=="host":
            if dest==self.pseudo: return
            sd=self.pseudo_to_sock.get(dest)
            if sd:
                try: sd.sendall(make_msg("mp",from_=self.pseudo,text=texte))
                except OSError: self.afficher_erreur(f"MP vers {dest} Ã©chouÃ©.")
            else: self.afficher_erreur(f"{dest} est introuvable.")
        else:
            try: self.sock.sendall(make_msg("mp",from_=self.pseudo,to=dest,text=texte))
            except OSError: self.afficher_erreur("MP non envoyÃ© (connexion perdue).")
        self._gagner_xp(2,coins=1)

    def _afficher_mp(self,dest,src,texte,win,txt,moi=False):
        txt.config(state="normal")
        couleur=C_BLUE if moi else couleur_hex(self.profils.get(src,{}).get("couleur",COULEURS_DEFAUT))
        tag=f"mp_{src}_{id(win)}"; txt.tag_config(tag,foreground=couleur,font=(FONT,11,"bold"))
        txt.insert(tk.END,f"[{src}] ",tag)
        self._rendre_liens(txt,texte,"moi_texte" if moi else "autre_texte")
        txt.insert(tk.END,"\n")
        txt.config(state="disabled"); txt.see(tk.END)

    def _on_mp_recu(self,src,texte):
        self.mp_historique.setdefault(src,[]).append((src,texte))
        if src in self.fenetres_mp and self.fenetres_mp[src].winfo_exists():
            win=self.fenetres_mp[src]; self._afficher_mp(src,src,texte,win,win.txt); win.lift()
        else: self.mp_non_lus[src]=self.mp_non_lus.get(src,0)+1
        son_notif(); self._toast(f"â MP de {src} : {texte[:30]}",lambda:self._ouvrir_fenetre_mp(src))

    def _demarrer_appel(self,dest):
        if dest==self.pseudo: return
        if dest in self.appels: messagebox.showinfo(APP_NAME,"Un appel est dÃ©jÃ  en cours."); return
        if dest in self.fenetres_appel and self.fenetres_appel[dest].winfo_exists(): return
        if self.mode=="host":
            sd=self.pseudo_to_sock.get(dest)
            if not sd: self.afficher_erreur(f"{dest} est introuvable."); return
            try: sd.sendall(make_msg("call_incoming",from_=self.pseudo))
            except OSError: self.afficher_erreur("Demande d'appel Ã©chouÃ©e.")
        else:
            try: self.sock.sendall(make_msg("call_request",from_=self.pseudo,to=dest))
            except OSError: self.afficher_erreur("Demande d'appel Ã©chouÃ©e."); return
        self._ouvrir_fenetre_appel(dest,appelant=True)

    def _ouvrir_fenetre_appel(self,peer,appelant=False):
        win=tk.Toplevel(self.root); win.title(f"Appel avec {peer}"); win.geometry("340x380")
        win.configure(bg=C_BG); win.transient(self.root)
        tk.Label(win,text="ð",font=(FONT,40),bg=C_BG,fg=C_GREEN).pack(pady=(16,4))
        self.lbl_appel_peer=tk.Label(win,text=peer,font=(FONT,16,"bold"),fg=C_TEXT,bg=C_BG)
        self.lbl_appel_peer.pack()
        self.lbl_appel_statut=tk.Label(win,text="En attenteâ¦",font=(FONT,11),fg=C_SUB,bg=C_BG)
        self.lbl_appel_statut.pack(pady=4)
        self.lbl_duree=tk.Label(win,text="00:00",font=(FONT,12,"bold"),fg=C_GREEN,bg=C_BG)
        self.lbl_duree.pack(pady=4)
        btns=tk.Frame(win,bg=C_BG); btns.pack(pady=18)
        self.btn_mute=tk.Button(btns,text="ð Muet",command=self._toggle_mute)
        self._btn_styler(self.btn_mute,C_INP,C_TEXT); self.btn_mute.pack(side="left",padx=6)
        b=tk.Button(btns,text="ðµ Raccrocher",command=lambda:self._raccrocher(peer))
        self._btn_styler(b,C_RED); b.pack(side="left",padx=6)
        if not AUDIO_OK:
            tk.Label(win,text="Mode texte (PyAudio absent)\nâ parle via le mini-chat â",
                font=(FONT,9),fg=C_DIM,bg=C_BG,justify="center").pack(pady=(0,4))
            ent=tk.Entry(win); self._entree_styler(ent)
            ent.pack(fill="x",padx=16,pady=4,ipady=5)
            ent.bind("<Return>",lambda e:self._appel_mini_msg(peer,ent))
        self._appel_start=None
        win.protocol("WM_DELETE_WINDOW",lambda:self._raccrocher(peer))
        self.fenetres_appel[peer]=win

    def _toggle_mute(self):
        if self.audio.actif:
            muet=self.audio.basculer_mute()
            self.btn_mute.config(text="ð Muet (ON)" if muet else "ð Muet")

    def _appel_mini_msg(self,peer,ent):
        texte=ent.get().strip()
        if not texte: return
        ent.delete(0,tk.END); self._envoyer_mp(peer,f"[appel] {texte}")

    def _on_appel_entrant(self,src):
        sonnerie()
        win=tk.Toplevel(self.root); win.title("Appel entrant"); win.geometry("320x240")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        tk.Label(win,text="ð",font=(FONT,36),bg=C_BG,fg=C_YELLOW).pack(pady=(16,2))
        tk.Label(win,text=f"{src} t'appelle !",font=(FONT,14,"bold"),fg=C_TEXT,bg=C_BG).pack()
        btns=tk.Frame(win,bg=C_BG); btns.pack(pady=18)
        def accepter(): stop_sonnerie(); win.destroy(); self._accepter_appel(src)
        def refuser(): stop_sonnerie(); win.destroy(); self._refuser_appel(src)
        b1=tk.Button(btns,text="â Accepter",command=accepter)
        self._btn_styler(b1,C_GREEN); b1.pack(side="left",padx=8)
        b2=tk.Button(btns,text="â Refuser",command=refuser)
        self._btn_styler(b2,C_RED); b2.pack(side="left",padx=8)

    def _accepter_appel(self,src):
        self._ouvrir_fenetre_appel(src,appelant=False)
        if AUDIO_OK:
            audio_port=self.audio.allouer() or 0; audio_ip=local_ip()
        else: audio_port=0; audio_ip=local_ip()
        self._envoyer_controle_appel(make_msg("call_accept",from_=self.pseudo,to=src,
            audio_ip=audio_ip,audio_port=audio_port),src)
        self._demarrer_timer_appel(src)

    def _refuser_appel(self,src):
        self._envoyer_controle_appel(make_msg("call_reject",from_=self.pseudo,to=src),src)

    def _on_appel_accepte(self,peer,audio_ip,audio_port):
        if peer not in self.fenetres_appel or not self.fenetres_appel[peer].winfo_exists():
            self._ouvrir_fenetre_appel(peer,appelant=True)
        win=self.fenetres_appel[peer]
        if AUDIO_OK and audio_port:
            mon_port=self.audio.allouer() or 0
            self.audio.demarrer_streams(audio_ip,audio_port)
            win.lbl_appel_statut.config(text="ConnectÃ© !")
            self._envoyer_controle_appel(make_msg("call_ready",from_=self.pseudo,to=peer,
                audio_ip=local_ip(),audio_port=mon_port),peer)
        else: win.lbl_appel_statut.config(text="Mode texte")
        self._demarrer_timer_appel(peer)

    def _on_appel_ready(self,peer,audio_ip,audio_port):
        if AUDIO_OK and audio_port: self.audio.demarrer_streams(audio_ip,audio_port)
        win=self.fenetres_appel.get(peer)
        if win and win.winfo_exists(): win.lbl_appel_statut.config(text="ConnectÃ© !")

    def _demarrer_timer_appel(self,peer):
        self._appel_start=time.time()
        def tick():
            win=self.fenetres_appel.get(peer)
            if not win or not win.winfo_exists(): return
            if self._appel_start:
                d=int(time.time()-self._appel_start); m,s=divmod(d,60)
                win.lbl_duree.config(text=f"{m:02d}:{s:02d}")
            self.root.after(1000,tick)
        tick()

    def _raccrocher(self,peer):
        self.audio.arreter()
        self._envoyer_controle_appel(make_msg("call_end",from_=self.pseudo,to=peer),peer)
        win=self.fenetres_appel.pop(peer,None)
        if win and win.winfo_exists(): win.destroy()
        self.appels.pop(peer,None); self._gagner_xp(0,appels=1)

    def _on_appel_refuse(self,peer):
        win=self.fenetres_appel.pop(peer,None)
        if win and win.winfo_exists():
            win.lbl_appel_statut.config(text="Appel refusÃ© ð"); self.root.after(2500,win.destroy)
        self.afficher_systeme(f"ð {peer} a refusÃ© l'appel.")

    def _on_appel_fin(self,peer):
        self.audio.arreter()
        win=self.fenetres_appel.pop(peer,None)
        if win and win.winfo_exists():
            win.lbl_appel_statut.config(text="Appel terminÃ©"); self.root.after(2000,win.destroy)
        self.afficher_systeme(f"ð Appel avec {peer} terminÃ©.")

    def _envoyer_controle_appel(self,data,dest):
        if self.mode=="host":
            if dest==self.pseudo: return
            sd=self.pseudo_to_sock.get(dest)
            if sd:
                try: sd.sendall(data)
                except OSError: pass
        else:
            try: self.sock.sendall(data)
            except OSError: pass

    def _toast(self,texte,callback=None):
        popup=tk.Toplevel(self.root); popup.overrideredirect(True); popup.configure(bg=C_SURF2)
        popup.attributes("-topmost",True)
        x=self.root.winfo_x()+self.root.winfo_width()-280
        y=self.root.winfo_y()+self.root.winfo_height()-90
        popup.geometry(f"+{x}+{y}")
        lbl=tk.Label(popup,text=" "+texte+" ",font=(FONT,10),fg=C_TEXT,bg=C_SURF2,
            padx=14,pady=10,wraplength=250,justify="left")
        lbl.pack()
        def cliquer(e=None):
            if callback: callback()
            popup.destroy()
        lbl.bind("<Button-1>",cliquer); popup.after(4500,popup.destroy)
    def ouvrir_parametres(self):
        win=tk.Toplevel(self.root); win.title("Paramètres"); win.geometry("520x560")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_anime(win,height=46)
        tk.Label(win,text="⚙️  Paramètres",font=(FONT,16,"bold"),fg=C_PURPLE,bg=C_BG).pack(pady=(8,4))
        nbook=ttk.Notebook(win); nbook.pack(fill="both",expand=True,padx=14,pady=6)
        style=ttk.Style()
        style.configure("TNotebook",background=C_BG,borderwidth=0)
        style.configure("TNotebook.Tab",background=C_SURF2,foreground=C_TEXT,padding=14)
        style.map("TNotebook.Tab",background=[("selected",C_PURPLE)],foreground=[("selected",C_BG)])
        self._param_page_apparence(nbook)
        self._param_page_sons(nbook)
        self._param_page_profil(nbook,win)

    def _param_page_apparence(self,nbook):
        page=tk.Frame(nbook,bg=C_BG); nbook.add(page,text="🎨 Apparence")
        tk.Label(page,text="Thème de l'application",font=(FONT,12,"bold"),fg=C_TEXT,bg=C_BG).pack(pady=(16,8))
        courant=self.compte.get("theme","sombre")
        for nom,label,couleur_apercu in [("sombre","🌙 Mode sombre",C_BG),("clair","☀️ Mode clair","#eff1f5")]:
            cadre=tk.Frame(page,bg=C_SURF2,highlightbackground=C_INP,highlightthickness=2 if nom==courant else 1)
            cadre.pack(fill="x",padx=24,pady=6)
            apercu=tk.Frame(cadre,bg=couleur_apercu,width=50,height=50)
            apercu.pack(side="left",padx=14,pady=10); apercu.pack_propagate(False)
            txt=tk.Label(cadre,text=label,font=(FONT,12,"bold"),fg=C_TEXT if nom!="clair" else "#4c4f69",bg=C_SURF2)
            txt.pack(side="left",padx=10)
            if nom==courant:
                tk.Label(cadre,text="  ✓ Actif",font=(FONT,10,"bold"),fg=C_GREEN,bg=C_SURF2).pack(side="right",padx=14)
            else:
                b=tk.Button(cadre,text="Activer",command=lambda n=nom:self._changer_theme(n))
                self._btn_styler(b,C_BLUE); b.pack(side="right",padx=14,pady=10)

    def _changer_theme(self,nom):
        self.compte["theme"]=nom; self.gc.sauver()
        _appliquer_theme(nom); self.root.configure(bg=C_BG)
        self._ecran_demarrage()
        messagebox.showinfo(APP_NAME,f"Thème {nom} appliqué !")

    def _param_page_sons(self,nbook):
        page=tk.Frame(nbook,bg=C_BG); nbook.add(page,text="🔊 Sons")
        tk.Label(page,text="Personnalisation sonore",font=(FONT,12,"bold"),fg=C_TEXT,bg=C_BG).pack(pady=(12,4))
        for cle,lib in [("sonnerie","Sonnerie d'appel"),("notif","Notification MP")]:
            cadre=tk.Frame(page,bg=C_SURF2,highlightbackground=C_INP,highlightthickness=1)
            cadre.pack(fill="x",padx=20,pady=6)
            tk.Label(cadre,text=lib,font=(FONT,11,"bold"),fg=C_TEXT,bg=C_SURF2).pack(anchor="w",padx=12,pady=(8,2))
            chemin=self.compte.get(cle,"")
            lbl_chemin=tk.Label(cadre,text=(chemin if chemin else "⚛ Par défaut (bip)"),
                font=(FONT,9),fg=C_SUB,bg=C_SURF2,wraplength=380,justify="left")
            lbl_chemin.pack(anchor="w",padx=12,pady=(0,4))
            boutons=tk.Frame(cadre,bg=C_SURF2); boutons.pack(anchor="w",padx=12,pady=(0,8))
            def choisir_fichier(c=cle,lb=lbl_chemin):
                f=filedialog.askopenfilename(title="Choisir un fichier son",
                    filetypes=[("Audio","*.mp3 *.wav *.ogg *.m4a"),("Tous","*.*")])
                if not f: return
                self.compte[c]=f; _SONS_PERSO[c]=f; self.gc.sauver(); lb.config(text=f)
            def tester(c=cle):
                _SONS_PERSO[c]=self.compte.get(c,"")
                if c=="sonnerie": sonnerie()
                else: son_notif()
            def reset(c=cle,lb=lbl_chemin):
                self.compte[c]=""; _SONS_PERSO[c]=""; self.gc.sauver(); lb.config(text="⚛ Par défaut (bip)")
            b1=tk.Button(boutons,text="📁 Fichier",command=choisir_fichier)
            self._btn_styler(b1,C_BLUE); b1.pack(side="left",padx=3)
            b2=tk.Button(boutons,text="▶ Tester",command=lambda c=cle:tester(c))
            self._btn_styler(b2,C_GREEN); b2.pack(side="left",padx=3)
            b3=tk.Button(boutons,text="Réinit.",command=lambda c=cle,lb=lbl_chemin:reset(c,lb))
            self._btn_styler(b3,C_INP,C_TEXT); b3.pack(side="left",padx=3)
        tk.Label(page,text="🎵 Sons téléchargeables (internet)",font=(FONT,11,"bold"),fg=C_TEAL,bg=C_BG).pack(pady=(10,4))
        zone_dl=tk.Frame(page,bg=C_BG); zone_dl.pack(fill="x",padx=20,pady=4)
        for nom_son,url in SONS_PRESETS.items():
            row=tk.Frame(zone_dl,bg=C_SURF2,highlightbackground=C_INP,highlightthickness=1)
            row.pack(fill="x",pady=3)
            tk.Label(row,text=nom_son.replace("_"," ").title(),font=(FONT,10),fg=C_TEXT,bg=C_SURF2).pack(side="left",padx=10,pady=6)
            def telecharger(u=url,n=nom_son):
                try:
                    dest=os.path.join(EMOJI_DIR,n+".mp3")
                    if not os.path.isdir(EMOJI_DIR): os.makedirs(EMOJI_DIR)
                    req=urllib.request.Request(u,headers={"User-Agent":f"LANchat/{VERSION}"})
                    with urllib.request.urlopen(req,timeout=8) as r:
                        data=r.read()
                    with open(dest,"wb") as f: f.write(data)
                    messagebox.showinfo(APP_NAME,f"Téléchargé : {n}\nApplique-le dans 'Fichier' ci-dessus.")
                except Exception as e:
                    messagebox.showerror(APP_NAME,f"Échec du téléchargement : {e}")
            b=tk.Button(row,text="⬇ Télécharger",command=telecharger)
            self._btn_styler(b,C_TEAL,C_BG); b.pack(side="right",padx=8,pady=4)

    def _param_page_profil(self,nbook,parent_win):
        page=tk.Frame(nbook,bg=C_BG); nbook.add(page,text="👤 Profil")
        tk.Label(page,text="Mon profil public",font=(FONT,12,"bold"),fg=C_TEXT,bg=C_BG).pack(pady=(12,4))
        tk.Label(page,text="Bio",font=(FONT,10,"bold"),fg=C_SUB,bg=C_BG).pack(anchor="w",padx=20,pady=(8,2))
        txt_bio=tk.Text(page,font=(FONT,11),bg=C_INP,fg=C_TEXT,insertbackground=C_TEXT,
            relief="flat",bd=0,wrap="word",height=3,padx=10,pady=8)
        txt_bio.pack(fill="x",padx=20,pady=(0,8))
        txt_bio.insert("1.0",self.compte.get("bio",""))
        tk.Label(page,text="Liens (un par ligne)",font=(FONT,10,"bold"),fg=C_SUB,bg=C_BG).pack(anchor="w",padx=20)
        txt_liens=tk.Text(page,font=(FONT,11),bg=C_INP,fg=C_TEXT,insertbackground=C_TEXT,
            relief="flat",bd=0,wrap="word",height=4,padx=10,pady=8)
        txt_liens.pack(fill="x",padx=20,pady=(0,8))
        txt_liens.insert("1.0","\n".join(self.compte.get("liens",[])))
        def sauver():
            bio=txt_bio.get("1.0",tk.END).strip()[:300]
            liens_raw=txt_liens.get("1.0",tk.END).strip().split("\n")
            liens=[l.strip() for l in liens_raw if l.strip()][:10]
            self.compte["bio"]=bio; self.compte["liens"]=liens
            self.gc.sauver(); self._propager_profil()
            messagebox.showinfo(APP_NAME,"Profil mis à jour !")
        b=tk.Button(page,text="✔ Enregistrer le profil",command=sauver)
        self._btn_styler(b,C_GREEN); b.pack(pady=10)


    def ouvrir_selecteur_emoji(self):
        win=tk.Toplevel(self.root); win.title("Sélecteur d'emojis"); win.geometry("460x460")
        win.configure(bg=C_BG); win.transient(self.root); win.grab_set()
        self._fond_anime(win,height=40)
        tk.Label(win,text="😀 Choisis un emoji",font=(FONT,14,"bold"),fg=C_YELLOW,bg=C_BG).pack(pady=(8,4))
        conteneur=tk.Frame(win,bg=C_BG); conteneur.pack(fill="both",expand=True,padx=8,pady=4)
        canvas=tk.Canvas(conteneur,bg=C_BG,highlightthickness=0)
        scroll=tk.Scrollbar(conteneur,command=canvas.yview)
        inner=tk.Frame(canvas,bg=C_BG)
        inner.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window(0,0,window=inner,anchor="nw"); canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left",fill="both",expand=True); scroll.pack(side="right",fill="y")
        try:
            from PIL import Image, ImageTk
            PIL_OK=True
        except Exception:
            PIL_OK=False
        def inserer_texte(e):
            self.entree.insert(tk.INSERT,e); win.lift(); self.entree.focus()
        def inserer_image(nom_fichier):
            chemin=os.path.join(EMOJI_DIR,nom_fichier)
            marque=f"[img:{nom_fichier}]"
            self.entree.insert(tk.INSERT,marque); win.lift(); self.entree.focus()
        persos=_lister_emojis_perso()
        if persos:
            tk.Label(inner,text="Mes emojis importés",font=(FONT,10,"bold"),fg=C_TEAL,bg=C_BG).pack(anchor="w",pady=(8,4))
            grille=tk.Frame(inner,bg=C_BG); grille.pack(anchor="w")
            col=0
            for nom in persos:
                chemin=os.path.join(EMOJI_DIR,nom)
                case=tk.Frame(grille,bg=C_SURF2,highlightbackground=C_INP,highlightthickness=1)
                case.grid(row=0,column=col,padx=3,pady=3)
                if PIL_OK:
                    try:
                        from PIL import Image, ImageTk
                        img=Image.open(chemin); img.thumbnail((36,36))
                        photo=ImageTk.PhotoImage(img)
                        lbl=tk.Label(case,image=photo,bg=C_SURF2)
                        lbl.image=photo; lbl.pack(padx=4,pady=4)
                        lbl.bind("<Button-1>",lambda e,n=nom:inserer_image(n))
                        lbl.bind("<Enter>",lambda e,w=lbl:w.config(bg=C_INP))
                        lbl.bind("<Leave>",lambda e,w=lbl:w.config(bg=C_SURF2))
                    except Exception:
                        tk.Label(case,text="\u2753",font=(FONT,18),bg=C_SURF2).pack(padx=8,pady=8)
                else:
                    b=tk.Button(case,text=nom[:8],font=(FONT,8),bg=C_SURF2,fg=C_TEXT,
                        relief="flat",command=lambda n=nom:inserer_image(n))
                    b.pack(padx=4,pady=4)
                col+=1
                if col>=8: col=0; grille=tk.Frame(inner,bg=C_BG); grille.pack(anchor="w")
            tk.Label(inner,text="",bg=C_BG).pack(pady=2)
        for cat,liste in EMOJIS.items():
            tk.Label(inner,text=cat,font=(FONT,10,"bold"),fg=C_BLUE,bg=C_BG).pack(anchor="w",pady=(8,2))
            grille=tk.Frame(inner,bg=C_BG); grille.pack(anchor="w")
            col=0
            for emo in liste:
                b=tk.Button(grille,text=emo,font=(FONT,18),bg=C_SURF2,fg=C_TEXT,relief="flat",
                    cursor="hand2",bd=0,activebackground=C_INP,padx=6,pady=4,
                    command=lambda e=emo:inserer_texte(e))
                b.grid(row=0,column=col,padx=2,pady=2)
                b.bind("<Enter>",lambda e,w=b:w.config(bg=C_INP))
                b.bind("<Leave>",lambda e,w=b:w.config(bg=C_SURF2))
                col+=1
                if col>=8: col=0; grille=tk.Frame(inner,bg=C_BG); grille.pack(anchor="w")
        barre_bas=tk.Frame(win,bg=C_BG); barre_bas.pack(fill="x",pady=6,padx=8)
        b_imp=tk.Button(barre_bas,text="📥 Importer un emoji / GIF",command=lambda:self._importer_emoji(win))
        self._btn_styler(b_imp,C_GREEN); b_imp.pack(side="left",ipady=3)
        b_fermer=tk.Button(barre_bas,text="Fermer",command=win.destroy)
        self._btn_styler(b_fermer,C_INP,C_TEXT); b_fermer.pack(side="right",ipady=3)
        if not PIL_OK:
            tk.Label(win,text="Installe Pillow (pip install Pillow) pour afficher les emojis/GIFs importés en images.",
                font=(FONT,8),fg=C_DIM,bg=C_BG,wraplength=420,justify="center").pack(pady=(0,4))

    def _importer_emoji(self,parent_win):
        f=filedialog.askopenfilename(title="Importer un emoji / GIF",
            filetypes=[("Image","*.png *.gif *.jpg *.jpeg *.webp *.bmp"),("Tous","*.*")])
        if not f: return
        if not os.path.isdir(EMOJI_DIR):
            try: os.makedirs(EMOJI_DIR)
            except Exception as e: messagebox.showerror(APP_NAME,f"Impossible de créer le dossier : {e}"); return
        nom=os.path.basename(f)
        dest=os.path.join(EMOJI_DIR,nom)
        try:
            import shutil; shutil.copy(f,dest)
        except Exception as e:
            messagebox.showerror(APP_NAME,f"Import échoué : {e}"); return
        messagebox.showinfo(APP_NAME,f"Emoji importé : {nom}")
        parent_win.destroy(); self.ouvrir_selecteur_emoji()

    def _attacher_media(self):
        choix=messagebox.askyesnocancel(APP_NAME,"Joindre un fichier local (Oui) ou coller un lien/URL (Non) ?",
            detail="Oui = fichier vidéo/GIF/image, Non = lien web")
        if choix is None: return
        if choix:
            f=filedialog.askopenfilename(title="Choisir un média à partager",
                filetypes=[("Média","*.mp4 *.webm *.mov *.mkv *.gif *.jpg *.jpeg *.png *.mp3 *.wav"),
                           ("Tous","*.*")])
            if not f: return
            texte=f"📎 {os.path.basename(f)}  [file://{f}]"
        else:
            lien=simpledialog.askstring("Partager un lien","Colle ton lien (vidéo, GIF, page web) :")
            if not lien: return
            texte=f"🔗 {lien}"
        self.entree.delete(0,tk.END); self.entree.insert(0,texte); self.envoyer()

    def _rendre_liens(self,txt_widget,texte,tag_base):
        try:
            from PIL import Image, ImageTk
            PIL_OK=True
        except Exception:
            PIL_OK=False
        img_re=re.compile(r'\[img:([^\]]+)\]')
        idx=0
        for m in img_re.finditer(texte):
            deb,fin=m.span(); nom=m.group(1)
            if deb>idx:
                self._rendre_urls(txt_widget,texte[idx:deb],tag_base)
            chemin=os.path.join(EMOJI_DIR,nom)
            if PIL_OK and os.path.isfile(chemin):
                try:
                    img=Image.open(chemin); img.thumbnail((28,28))
                    photo=ImageTk.PhotoImage(img)
                    if not hasattr(self,"_img_cache"): self._img_cache=[]
                    self._img_cache.append(photo)
                    txt_widget.image_create(tk.END,image=photo)
                except Exception:
                    txt_widget.insert(tk.END,f"[img:{nom}]",tag_base)
            else:
                txt_widget.insert(tk.END,f"[img:{nom}]",tag_base)
            idx=fin
        if idx<len(texte):
            self._rendre_urls(txt_widget,texte[idx:],tag_base)

    def _rendre_urls(self,txt_widget,texte,tag_base):
        i=0
        for m in URL_RE.finditer(texte):
            deb,fin=m.span(); morceau=m.group(0)
            if deb>i: txt_widget.insert(tk.END,texte[i:deb],tag_base)
            url=_normalise_url(morceau)
            cible=url or morceau
            ltag="link_"+str(id(morceau))+"_"+str(deb)
            txt_widget.tag_config(ltag,foreground=C_BLUE,underline=True,font=(FONT,11,"underline"))
            txt_widget.tag_bind(ltag,"<Button-1>",lambda e,c=cible:webbrowser.open(c))
            txt_widget.tag_bind(ltag,"<Enter>",lambda e,w=txt_widget,t=ltag:w.config(cursor="hand2"))
            txt_widget.tag_bind(ltag,"<Leave>",lambda e,w=txt_widget,t=ltag:w.config(cursor=""))
            txt_widget.insert(tk.END,morceau,ltag)
            i=fin
        if i<len(texte): txt_widget.insert(tk.END,texte[i:],tag_base)

    def quitter(self):
        self.running=False; self.audio.arreter()
        try:
            if self.sock: self.sock.close()
        except OSError: pass
        with self.clients_lock:
            for c in self.clients:
                try: c.close()
                except OSError: pass
        for s in (self.tcp_server,self.udp_sock):
            try:
                if s: s.close()
            except OSError: pass
        self.gc.sauver(); self.root.destroy()

if __name__=="__main__":
    try: LANchat().root.mainloop()
    except KeyboardInterrupt: pass