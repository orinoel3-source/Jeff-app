# -*- coding: utf-8 -*-
"""
Jeff — application de rencontre (version Android / Kivy)
Stockage 100% local via SQLite (pas de backend en ligne).
"""

import os
import random
import sqlite3
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

# ---------------------------------------------------------------- couleurs
INK = (0.141, 0.106, 0.227, 1)      # #241B3A
ACCENT = (1, 0.267, 0.439, 1)       # #FF4470
GOLD = (1, 0.706, 0.263, 1)         # #FFB443
MUTED = (0.722, 0.698, 0.780, 1)    # #B8B2C7
BG = (0.980, 0.965, 0.984, 1)       # #FAF6FB

BOTS = [
    ("bot_aicha", "Aïcha", 26, "Cocody",
     "Danse l'afrobeat le vendredi, dort le samedi. Cherche partenaire de crime pour les deux.",
     "Café ou rien"),
    ("bot_kouassi", "Kouassi", 29, "Marcory",
     "Développeur le jour, DJ amateur la nuit. Je fais un attiéké-poisson légendaire.",
     "Amateur de bon son"),
    ("bot_mariam", "Mariam", 24, "Yopougon",
     "Je collectionne les couchers de soleil et les excuses pour manger du garba.",
     "Foodie assumée"),
    ("bot_yao", "Yao", 31, "Plateau",
     "Entrepreneur, deux cafés par jour minimum. Sérieux dans le travail, pas dans la vie.",
     "Toujours en réunion"),
    ("bot_fatou", "Fatou", 27, "Angré",
     "Prof de yoga qui n'a jamais réussi à méditer plus de 5 minutes. On rigole beaucoup.",
     "Zen (en théorie)"),
    ("bot_franck", "Franck", 28, "Riviera",
     "Je répare les motos et les cœurs brisés, dans cet ordre selon les jours.",
     "Mains dans le cambouis"),
]

OPENERS = [
    "Haha t'es drôle toi tu fais quoi ce soir ?",
    "Enfin quelqu'un avec un peu de goût sur cette appli !",
    "Ton profil m'a fait sourire direct, raconte un peu.",
    "On se lance un défi : le premier vrai date cette semaine ?",
    "T'as l'air sympa. C'est où le meilleur maquis du coin selon toi ?",
]
REPLIES = [
    "Haha bien vu",
    "On se capte quand alors ?",
    "T'es sérieux là ou tu me chauffes ?",
    "Ça marche, dis-moi le jour qui t'arrange.",
    "J'aime bien ta manière de voir les choses.",
]

ME = "me"


# ---------------------------------------------------------------- base de données
class DB:
    def __init__(self):
        folder = App.get_running_app().user_data_dir
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "jeff.db")
        self.conn = sqlite3.connect(path)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, name TEXT, age INTEGER, city TEXT,
            bio TEXT, tag TEXT, is_bot INTEGER)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS swipes (
            username TEXT, target TEXT, action TEXT,
            PRIMARY KEY (username, target))""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS matches (
            pair_key TEXT PRIMARY KEY, user_a TEXT, user_b TEXT, created_at REAL)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, pair_key TEXT,
            sender TEXT, text TEXT, ts REAL)""")
        self.conn.commit()
        self._seed_bots()

    def _seed_bots(self):
        for username, name, age, city, bio, tag in BOTS:
            self.conn.execute(
                "INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,1)",
                (username, name, age, city, bio, tag),
            )
        self.conn.commit()

    def get_profile(self, username):
        cur = self.conn.execute("SELECT * FROM users WHERE username=?", (username,))
        return cur.fetchone()

    def save_profile(self, username, name, age, city, bio, tag):
        self.conn.execute(
            "INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,0)",
            (username, name, age, city, bio, tag),
        )
        self.conn.commit()

    def deck(self, username):
        cur = self.conn.execute(
            """SELECT * FROM users WHERE username != ? AND username NOT IN
               (SELECT target FROM swipes WHERE username=?)""",
            (username, username),
        )
        return cur.fetchall()

    def swipe(self, username, target, liked):
        self.conn.execute(
            "INSERT OR REPLACE INTO swipes VALUES (?,?,?)",
            (username, target, "liked" if liked else "passed"),
        )
        self.conn.commit()

    def pair_key(self, a, b):
        return "__".join(sorted([a, b]))

    def create_match(self, a, b):
        pk = self.pair_key(a, b)
        cur = self.conn.execute("SELECT 1 FROM matches WHERE pair_key=?", (pk,))
        if cur.fetchone() is None:
            self.conn.execute(
                "INSERT INTO matches VALUES (?,?,?,?)", (pk, a, b, time.time())
            )
            self.conn.commit()
        return pk

    def matches_for(self, username):
        cur = self.conn.execute(
            "SELECT pair_key, user_a, user_b FROM matches WHERE user_a=? OR user_b=? ORDER BY created_at",
            (username, username),
        )
        rows = cur.fetchall()
        result = []
        for pk, a, b in rows:
            other_username = b if a == username else a
            profile = self.get_profile(other_username)
            if profile:
                result.append((pk, profile))
        return result

    def add_message(self, pair_key, sender, text):
        self.conn.execute(
            "INSERT INTO messages (pair_key, sender, text, ts) VALUES (?,?,?,?)",
            (pair_key, sender, text, time.time()),
        )
        self.conn.commit()

    def messages_for(self, pair_key):
        cur = self.conn.execute(
            "SELECT sender, text FROM messages WHERE pair_key=? ORDER BY id", (pair_key,)
        )
        return cur.fetchall()


# ---------------------------------------------------------------- widgets utilitaires
class Card(BoxLayout):
    """Rectangle arrondi coloré utilisé comme fond de carte / bulle."""

    def __init__(self, bg_color=(1, 1, 1, 1), radius=18, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*bg_color)
            self._rect = RoundedRectangle(radius=[radius])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


def styled_button(text, bg=ACCENT, fg=(1, 1, 1, 1), **kwargs):
    btn = Button(
        text=text,
        background_normal="",
        background_color=bg,
        color=fg,
        bold=True,
        size_hint_y=None,
        height=dp(48),
        **kwargs,
    )
    return btn


# ---------------------------------------------------------------- écran : profil
class OnboardingScreen(Screen):
    def __init__(self, db, on_done, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.on_done = on_done
        root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(10))
        root.add_widget(Label(text="Jeff", font_size=dp(30), color=INK, size_hint_y=None, height=dp(50)))
        root.add_widget(Label(text="Crée ton profil", color=MUTED, size_hint_y=None, height=dp(24)))

        self.name = TextInput(hint_text="Prénom", multiline=False, size_hint_y=None, height=dp(44))
        self.age = TextInput(hint_text="Âge", multiline=False, input_filter="int", size_hint_y=None, height=dp(44))
        self.city = TextInput(hint_text="Ville / quartier", multiline=False, size_hint_y=None, height=dp(44))
        self.bio = TextInput(hint_text="Petite bio", multiline=True, size_hint_y=None, height=dp(90))
        self.tag = TextInput(hint_text="Un tag qui te résume", multiline=False, size_hint_y=None, height=dp(44))

        for w in (self.name, self.age, self.city, self.bio, self.tag):
            root.add_widget(w)

        self.error = Label(text="", color=ACCENT, size_hint_y=None, height=dp(20))
        root.add_widget(self.error)

        submit = styled_button("Créer mon profil")
        submit.bind(on_release=self._submit)
        root.add_widget(submit)
        root.add_widget(Widget())
        self.add_widget(root)

    def _submit(self, *args):
        if not (self.name.text.strip() and self.age.text.strip() and self.city.text.strip()
                and self.bio.text.strip() and self.tag.text.strip()):
            self.error.text = "Remplis tous les champs."
            return
        self.db.save_profile(
            ME, self.name.text.strip(), int(self.age.text.strip()),
            self.city.text.strip(), self.bio.text.strip(), self.tag.text.strip(),
        )
        self.on_done()


# ---------------------------------------------------------------- écran : découvrir
class DiscoverScreen(Screen):
    def __init__(self, db, on_match, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.on_match = on_match
        self.root_box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
        self.add_widget(self.root_box)
        self.refresh()

    def refresh(self):
        self.root_box.clear_widgets()
        deck = self.db.deck(ME)
        if not deck:
            self.root_box.add_widget(Label(text="Plus de profils pour l'instant", color=MUTED))
            return
        profile = deck[0]
        _, name, age, city, bio, tag, _is_bot = profile

        card = Card(bg_color=(1, 1, 1, 1), orientation="vertical", padding=dp(18), spacing=dp(6))
        card.add_widget(Label(text=f"{name}, {age}", color=INK, bold=True, font_size=dp(22),
                               size_hint_y=None, height=dp(32)))
        card.add_widget(Label(text=city, color=MUTED, size_hint_y=None, height=dp(20)))
        card.add_widget(Label(text=bio, color=INK, size_hint_y=None, height=dp(80)))
        card.add_widget(Label(text=tag, color=ACCENT, bold=True, size_hint_y=None, height=dp(24)))
        self.root_box.add_widget(card)

        buttons = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(20))
        pass_btn = styled_button("Passer", bg=MUTED, fg=INK)
        like_btn = styled_button("J'aime", bg=ACCENT)
        pass_btn.bind(on_release=lambda *_: self._swipe(profile[0], False))
        like_btn.bind(on_release=lambda *_: self._swipe(profile[0], True))
        buttons.add_widget(pass_btn)
        buttons.add_widget(like_btn)
        self.root_box.add_widget(buttons)

    def _swipe(self, target_username, liked):
        self.db.swipe(ME, target_username, liked)
        if liked and random.random() < 0.55:
            pk = self.db.create_match(ME, target_username)
            profile = self.db.get_profile(target_username)
            self.db.add_message(pk, target_username, random.choice(OPENERS))
            self.on_match(profile)
        self.refresh()


# ---------------------------------------------------------------- écran : discussions
class MatchesScreen(Screen):
    def __init__(self, db, on_open_chat, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.on_open_chat = on_open_chat
        self.box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None)
        self.box.bind(minimum_height=self.box.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.box)
        self.add_widget(scroll)

    def refresh(self):
        self.box.clear_widgets()
        matches = self.db.matches_for(ME)
        if not matches:
            self.box.add_widget(Label(text="Pas encore de discussion", color=MUTED,
                                       size_hint_y=None, height=dp(40)))
            return
        for pk, profile in matches:
            _, name, age, city, bio, tag, _ = profile
            btn = styled_button(name, bg=(1, 1, 1, 1), fg=INK)
            btn.bind(on_release=lambda *_a, pk=pk, profile=profile: self.on_open_chat(pk, profile))
            self.box.add_widget(btn)


# ---------------------------------------------------------------- écran : tchat
class ChatScreen(Screen):
    def __init__(self, db, on_back, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.on_back = on_back
        self.pair_key = None
        self.other = None

        root = BoxLayout(orientation="vertical")
        header = BoxLayout(size_hint_y=None, height=dp(48), padding=dp(8))
        back_btn = Button(text="< Retour", size_hint_x=None, width=dp(100),
                           background_normal="", background_color=BG, color=INK)
        back_btn.bind(on_release=lambda *_: self.on_back())
        self.title_label = Label(text="", color=INK, bold=True)
        header.add_widget(back_btn)
        header.add_widget(self.title_label)
        root.add_widget(header)

        self.messages_box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6),
                                       size_hint_y=None)
        self.messages_box.bind(minimum_height=self.messages_box.setter("height"))
        self.scroll = ScrollView()
        self.scroll.add_widget(self.messages_box)
        root.add_widget(self.scroll)

        input_row = BoxLayout(size_hint_y=None, height=dp(52), padding=dp(6), spacing=dp(6))
        self.input = TextInput(hint_text="Écris un message...", multiline=False)
        send_btn = styled_button("Envoyer", size_hint_x=None, width=dp(90))
        send_btn.bind(on_release=lambda *_: self._send())
        input_row.add_widget(self.input)
        input_row.add_widget(send_btn)
        root.add_widget(input_row)

        self.add_widget(root)

    def open(self, pair_key, other):
        self.pair_key = pair_key
        self.other = other
        self.title_label.text = other[1]
        self.refresh()

    def refresh(self):
        self.messages_box.clear_widgets()
        for sender, text in self.db.messages_for(self.pair_key):
            mine = sender == ME
            bubble = Card(
                bg_color=ACCENT if mine else (1, 1, 1, 1),
                orientation="vertical", padding=dp(10), size_hint_y=None, height=dp(44),
            )
            bubble.add_widget(Label(text=text, color=(1, 1, 1, 1) if mine else INK))
            row = BoxLayout(size_hint_y=None, height=dp(44))
            if mine:
                row.add_widget(Widget(size_hint_x=0.2))
                row.add_widget(bubble)
            else:
                row.add_widget(bubble)
                row.add_widget(Widget(size_hint_x=0.2))
            self.messages_box.add_widget(row)

    def _send(self):
        text = self.input.text.strip()
        if not text:
            return
        self.input.text = ""
        self.db.add_message(self.pair_key, ME, text)
        self.refresh()
        if self.other[6]:  # is_bot
            Clock.schedule_once(self._bot_reply, 1.1)

    def _bot_reply(self, *args):
        self.db.add_message(self.pair_key, self.other[0], random.choice(REPLIES))
        self.refresh()


# ---------------------------------------------------------------- app racine
class JeffApp(App):
    def build(self):
        Window.clearcolor = BG
        self.db = DB()

        self.sm = ScreenManager(transition=NoTransition())
        self.discover_screen = DiscoverScreen(self.db, self._show_match_popup, name="discover")
        self.matches_screen = MatchesScreen(self.db, self._open_chat, name="matches")
        self.chat_screen = ChatScreen(self.db, self._back_to_matches, name="chat")

        root = BoxLayout(orientation="vertical")

        if self.db.get_profile(ME) is None:
            onboarding = OnboardingScreen(self.db, self._after_onboarding, name="onboarding")
            self.sm.add_widget(onboarding)
            self.sm.current = "onboarding"
        else:
            self.sm.add_widget(self.discover_screen)
            self.sm.add_widget(self.matches_screen)
            self.sm.add_widget(self.chat_screen)

        root.add_widget(self.sm)

        self.nav = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(6), spacing=dp(6))
        discover_btn = styled_button("Découvrir", bg=BG, fg=INK)
        chats_btn = styled_button("Discussions", bg=BG, fg=INK)
        discover_btn.bind(on_release=lambda *_: self._goto("discover"))
        chats_btn.bind(on_release=lambda *_: self._goto("matches"))
        self.nav.add_widget(discover_btn)
        self.nav.add_widget(chats_btn)
        if self.db.get_profile(ME) is not None:
            root.add_widget(self.nav)
        self.root_layout = root

        return root

    def _after_onboarding(self):
        self.sm.clear_widgets()
        self.sm.add_widget(self.discover_screen)
        self.sm.add_widget(self.matches_screen)
        self.sm.add_widget(self.chat_screen)
        self.sm.current = "discover"
        if self.nav not in self.root_layout.children:
            self.root_layout.add_widget(self.nav)
        self.discover_screen.refresh()

    def _goto(self, name):
        if name == "matches":
            self.matches_screen.refresh()
        self.sm.current = name

    def _show_match_popup(self, profile):
        # Popup simple de confirmation de match
        from kivy.uix.popup import Popup
        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        content.add_widget(Label(text="C'est un Jeff !", color=(1, 1, 1, 1), font_size=dp(26), bold=True))
        content.add_widget(Label(text=f"Toi et {profile[1]}, vous vous êtes likés.", color=(1, 1, 1, 1)))
        close_btn = styled_button("Continuer")
        popup = Popup(title="", content=content, size_hint=(0.85, 0.4),
                       separator_height=0, background_color=INK)
        close_btn.bind(on_release=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()

    def _open_chat(self, pair_key, profile):
        self.chat_screen.open(pair_key, profile)
        self.sm.current = "chat"

    def _back_to_matches(self):
        self.matches_screen.refresh()
        self.sm.current = "matches"


if __name__ == "__main__":
    JeffApp().run()
