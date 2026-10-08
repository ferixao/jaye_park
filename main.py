# -*- coding: utf-8 -*-
"""
Jaye Park - اپ مدیریت پارکینگ
ساخته شده با Python + Kivy + KivyMD
"""

import os
import sqlite3
import shutil
from datetime import datetime, timedelta
from calendar import monthrange

# --- Kivy ---
os.environ['KIVY_NO_ARGS'] = '1'
from kivy.config import Config
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty

# --- ثبت فونت فارسی ---
LabelBase.register(
    name='Vazir',
    fn_regular='Vazirmatn-Regular.ttf',
    fn_bold='Vazirmatn-Bold.ttf'
)

# --- KivyMD ---
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.list import MDList, TwoLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.toast import toast
from kivymd.uix.menu import MDDropdownMenu

# --- برای نمایش فارسی ---
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    def fa(text):
        """تبدیل متن فارسی برای نمایش درست در Kivy"""
        if not text:
            return ''
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
except ImportError:
    def fa(text):
        return str(text)


# ================== دیتابیس ==================
DB = "parking.db"

def init_db():
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate TEXT NOT NULL,
        phone TEXT,
        vtype TEXT,
        spot TEXT,
        start TEXT,
        expire TEXT,
        amount INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sub_id INTEGER,
        date TEXT,
        months INTEGER,
        amount INTEGER,
        note TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    # قیمت‌های پیش‌فرض
    defaults = {
        'price_car': '1500000',
        'price_motor': '1000000',
        'price_heavy': '1700000',
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    con.commit()
    con.close()


def get_setting(key):
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    con.close()
    return int(row[0]) if row else 0


def set_setting(key, value):
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    con.commit()
    con.close()


def fa_num(n):
    """تبدیل عدد به فرمت فارسی با کاما"""
    try:
        return f"{int(n):,}"
    except:
        return str(n)


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def add_months(d, months):
    """اضافه کردن ماه به تاریخ با در نظر گرفتن ۳۰ یا ۳۱ روز"""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return datetime(year, month, day)


def vtype_fa(v):
    return {
        'car': 'خودرو سواری',
        'motor': 'موتورسیکلت',
        'heavy': 'وانت / شاسی‌بلند'
    }.get(v, v)


# ================== کیوی لِنگ ==================
KV = '''
<CardItem>:
    orientation: "vertical"
    padding: dp(10)
    spacing: dp(5)
    size_hint_y: None
    height: dp(120)
    radius: [dp(12)]
    md_bg_color: 1, 1, 1, 1
    elevation: 3
'''

Builder.load_string(KV)


# ================== کارت مشتری ==================
class SubCard(MDCard):
    def __init__(self, sub_data, app, **kw):
        super().__init__(**kw)
        self.sub_data = sub_data
        self.app = app
        self.orientation = 'vertical'
        self.padding = dp(10)
        self.spacing = dp(5)
        self.size_hint_y = None
        self.height = dp(135)
        self.radius = [dp(12)]
        self.md_bg_color = (1, 1, 1, 1)
        self.elevation = 3

        sid, plate, phone, vtype, spot, start, expire, amount = sub_data

        # محاسبه روزهای مانده
        try:
            exp_date = datetime.strptime(expire, "%Y-%m-%d")
            days_left = (exp_date - datetime.now()).days
        except:
            days_left = 0

        if days_left < 0:
            status_color = (0.8, 0.2, 0.2, 1)
            status_text = f"منقضی شده ({abs(days_left)} روز پیش)"
        elif days_left <= 5:
            status_color = (1, 0.5, 0, 1)
            status_text = f"⚠️ {days_left} روز مانده"
        else:
            status_color = (0.2, 0.6, 0.2, 1)
            status_text = f"✅ {days_left} روز مانده"

        # خط اول: پلاک + نوع
        line1 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(30))
        lbl_plate = MDLabel(
            text=fa(f"🚗 {plate}"),
            font_name='Vazir',
            halign='right',
            theme_text_color='Custom',
            text_color=(0.1, 0.1, 0.1, 1),
            bold=True,
        )
        line1.add_widget(lbl_plate)
        self.add_widget(line1)

        # خط دوم: نوع + محل
        line2 = MDLabel(
            text=fa(f"{vtype_fa(vtype)} | محل: {spot}"),
            font_name='Vazir',
            halign='right',
            theme_text_color='Custom',
            text_color=(0.3, 0.3, 0.3, 1),
            size_hint_y=None,
            height=dp(25),
        )
        self.add_widget(line2)

        # خط سوم: تاریخ
        line3 = MDLabel(
            text=fa(f"شروع: {start}  |  انقضا: {expire}"),
            font_name='Vazir',
            halign='right',
            theme_text_color='Custom',
            text_color=(0.4, 0.4, 0.4, 1),
            size_hint_y=None,
            height=dp(25),
        )
        self.add_widget(line3)

        # خط چهارم: وضعیت + دکمه‌ها
        line4 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        status_lbl = MDLabel(
            text=fa(status_text),
            font_name='Vazir',
            halign='left',
            theme_text_color='Custom',
            text_color=status_color,
            bold=True,
        )
        line4.add_widget(status_lbl)

        btn_layout = MDBoxLayout(orientation='horizontal', size_hint_x=None, width=dp(120))
        btn_edit = MDIconButton(
            icon='pencil',
            theme_icon_color='Custom',
            icon_color=(0.1, 0.5, 0.9, 1),
            on_release=lambda x: app.open_edit_dialog(self.sub_data),
        )
        btn_renew = MDIconButton(
            icon='refresh',
            theme_icon_color='Custom',
            icon_color=(0.9, 0.5, 0, 1),
            on_release=lambda x: app.open_renew_dialog(self.sub_data),
        )
        btn_del = MDIconButton(
            icon='delete',
            theme_icon_color='Custom',
            icon_color=(0.8, 0.2, 0.2, 1),
            on_release=lambda x: app.confirm_delete(self.sub_data),
        )
        btn_layout.add_widget(btn_del)
        btn_layout.add_widget(btn_renew)
        btn_layout.add_widget(btn_edit)
        line4.add_widget(btn_layout)
        self.add_widget(line4)


# ================== صفحات ==================
class MainScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = MDBoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))

        title = MDLabel(
            text=fa("🅿️ جای پارک"),
            font_name='Vazir',
            halign='center',
            font_style='H4',
            size_hint_y=None,
            height=dp(60),
            theme_text_color='Custom',
            text_color=(1, 0.5, 0, 1),
            bold=True,
        )
        box.add_widget(title)

        box.add_widget(MDRaisedButton(
            text=fa("➕ ثبت مشتری جدید"),
            font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.5, 0, 1),
            on_release=lambda x: self.goto("add"),
        ))
        box.add_widget(MDRaisedButton(
            text=fa("📋 لیست مشتریان"),
            font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.6, 0.1, 1),
            on_release=lambda x: self.goto("list"),
        ))
        box.add_widget(MDRaisedButton(
            text=fa("⚠️ هشدار انقضا"),
            font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.7, 0.2, 1),
            on_release=lambda x: self.goto("warn"),
        ))
        box.add_widget(MDRaisedButton(
            text=fa("🔍 جستجو"),
            font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.6, 0.1, 1),
            on_release=lambda x: self.goto("search"),
        ))
        box.add_widget(MDRaisedButton(
            text=fa("📊 گزارش‌ها"),
            font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.5, 0, 1),
            on_release=lambda x: self.goto("report"),
        ))
        box.add_widget(MDRaisedButton(
            text=fa("⚙️ تنظیمات قیمت‌ها"),
            font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.6, 0.1, 1),
            on_release=lambda x: self.goto("settings"),
        ))
        box.add_widget(MDRaisedButton(
            text=fa("💾 پشتیبان‌گیری"),
            font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.7, 0.2, 1),
            on_release=lambda x: MDApp.get_running_app().backup_db(),
        ))

        self.add_widget(box)

    def goto(self, name):
        self.manager.current = name


class AddScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.scroll = MDScrollView()
        self.box = MDBoxLayout(orientation='vertical', padding=dp(15), spacing=dp(8),
                                size_hint_y=None)
        self.box.bind(minimum_height=self.box.setter('height'))

        self.box.add_widget(MDLabel(
            text=fa("ثبت مشتری جدید"), font_name='Vazir', halign='center',
            font_style='H5', size_hint_y=None, height=dp(50),
            theme_text_color='Custom', text_color=(1, 0.5, 0, 1), bold=True,
        ))

        self.plate = MDTextField(hint_text=fa("شماره پلاک"), font_name='Vazir',
                                  size_hint_y=None, height=dp(60))
        self.phone = MDTextField(hint_text=fa("شماره تماس"), font_name='Vazir',
                                  size_hint_y=None, height=dp(60), input_filter='int')
        self.vtype = MDTextField(hint_text=fa("نوع وسیله"), font_name='Vazir',
                                  size_hint_y=None, height=dp(60))
        self.vtype.bind(focus=self.on_vtype_focus)
        self.spot = MDTextField(hint_text=fa("شماره محل پارک"), font_name='Vazir',
                                 size_hint_y=None, height=dp(60))

        self.type_hint = MDLabel(
            text=fa("کاراکترهای مجاز: car / motor / heavy"),
            font_name='Vazir', halign='center', size_hint_y=None, height=dp(20),
            theme_text_color='Custom', text_color=(0.5, 0.5, 0.5, 1), font_style='Caption',
        )

        self.box.add_widget(self.plate)
        self.box.add_widget(self.phone)
        self.box.add_widget(self.vtype)
        self.box.add_widget(self.type_hint)
        self.box.add_widget(self.spot)

        self.box.add_widget(MDRaisedButton(
            text=fa("ثبت + پرداخت"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.5, 0, 1), on_release=self.save,
        ))
        self.box.add_widget(MDFlatButton(
            text=fa("بازگشت"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(45),
            on_release=lambda x: self.back(),
        ))

        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

    def on_vtype_focus(self, instance, value):
        if value:
            app = MDApp.get_running_app()
            items = [
                {"viewclass": "OneLineListItem", "text": fa("خودرو سواری (car)"),
                 "on_release": lambda x="car": self.set_type("car")},
                {"viewclass": "OneLineListItem", "text": fa("موتورسیکلت (motor)"),
                 "on_release": lambda x="motor": self.set_type("motor")},
                {"viewclass": "OneLineListItem", "text": fa("وانت / شاسی‌بلند (heavy)"),
                 "on_release": lambda x="heavy": self.set_type("heavy")},
            ]
            self.menu = MDDropdownMenu(caller=self.vtype, items=items, width_mult=4)
            self.menu.open()

    def set_type(self, val):
        self.vtype.text = val
        self.menu.dismiss()

    def save(self, *a):
        plate = self.plate.text.strip()
        phone = self.phone.text.strip()
        vtype = self.vtype.text.strip().lower()
        spot = self.spot.text.strip()

        if not all([plate, vtype, spot]):
            toast(fa("همه فیلدهای ضروری را پر کن"))
            return
        if vtype not in ('car', 'motor', 'heavy'):
            toast(fa("نوع وسیله نامعتبر است"))
            return

        price_key = {'car': 'price_car', 'motor': 'price_motor', 'heavy': 'price_heavy'}[vtype]
        amount = get_setting(price_key)

        start = datetime.now()
        expire = add_months(start, 1)

        con = sqlite3.connect(DB)
        c = con.cursor()
        c.execute("""INSERT INTO subscribers (plate, phone, vtype, spot, start, expire, amount)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (plate, phone, vtype, spot,
                   start.strftime("%Y-%m-%d"), expire.strftime("%Y-%m-%d"), amount))
        sub_id = c.lastrowid
        c.execute("""INSERT INTO payments (sub_id, date, months, amount, note)
                     VALUES (?, ?, ?, ?, ?)""",
                  (sub_id, today_str(), 1, amount, fa("ثبت اولیه")))
        con.commit()
        con.close()

        toast(fa(f"✅ ثبت شد | انقضا: {expire.strftime('%Y-%m-%d')}"))
        self.plate.text = ""
        self.phone.text = ""
        self.vtype.text = ""
        self.spot.text = ""
        self.manager.current = "list"

    def back(self):
        self.manager.current = "main"


class ListScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        title = MDLabel(
            text=fa("📋 لیست مشتریان"), font_name='Vazir', halign='center',
            font_style='H5', size_hint_y=None, height=dp(50),
            theme_text_color='Custom', text_color=(1, 0.5, 0, 1), bold=True,
        )
        box.add_widget(title)

        self.scroll = MDScrollView()
        self.list = MDList()
        self.scroll.add_widget(self.list)
        box.add_widget(self.scroll)

        box.add_widget(MDFlatButton(
            text=fa("بازگشت"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(45),
            on_release=lambda x: self.back(),
        ))
        self.add_widget(box)

    def on_enter(self):
        self.load()

    def load(self):
        self.list.clear_widgets()
        con = sqlite3.connect(DB)
        c = con.cursor()
        c.execute("SELECT id, plate, phone, vtype, spot, start, expire, amount FROM subscribers ORDER BY id DESC")
        rows = c.fetchall()
        con.close()
        for row in rows:
            self.list.add_widget(SubCard(row, MDApp.get_running_app()))

        if not rows:
            self.list.add_widget(MDLabel(
                text=fa("هنوز مشتری‌ای ثبت نشده"), font_name='Vazir',
                halign='center', size_hint_y=None, height=dp(50),
            ))

    def back(self):
        self.manager.current = "main"


class WarnScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        box.add_widget(MDLabel(
            text=fa("⚠️ هشدار انقضا (۵ روز)"), font_name='Vazir', halign='center',
            font_style='H5', size_hint_y=None, height=dp(50),
            theme_text_color='Custom', text_color=(1, 0.5, 0, 1), bold=True,
        ))
        self.scroll = MDScrollView()
        self.list = MDList()
        self.scroll.add_widget(self.list)
        box.add_widget(self.scroll)
        box.add_widget(MDFlatButton(
            text=fa("بازگشت"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(45),
            on_release=lambda x: self.back(),
        ))
        self.add_widget(box)

    def on_enter(self):
        self.list.clear_widgets()
        con = sqlite3.connect(DB)
        c = con.cursor()
        c.execute("SELECT id, plate, phone, vtype, spot, start, expire, amount FROM subscribers")
        rows = c.fetchall()
        con.close()

        found = False
        for row in rows:
            try:
                exp = datetime.strptime(row[6], "%Y-%m-%d")
                days = (exp - datetime.now()).days
                if 0 <= days <= 5:
                    found = True
                    self.list.add_widget(SubCard(row, MDApp.get_running_app()))
            except:
                pass

        if not found:
            self.list.add_widget(MDLabel(
                text=fa("هیچ اشتراکی در ۵ روز آینده منقضی نمی‌شود ✅"),
                font_name='Vazir', halign='center',
                size_hint_y=None, height=dp(60),
            ))

    def back(self):
        self.manager.current = "main"


class SearchScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = MDBoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        box.add_widget(MDLabel(
            text=fa("🔍 جستجو"), font_name='Vazir', halign='center',
            font_style='H5', size_hint_y=None, height=dp(50),
            theme_text_color='Custom', text_color=(1, 0.5, 0, 1), bold=True,
        ))
        self.query = MDTextField(hint_text=fa("پلاک یا محل پارک"), font_name='Vazir',
                                  size_hint_y=None, height=dp(60))
        box.add_widget(self.query)
        box.add_widget(MDRaisedButton(
            text=fa("جستجو"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(45),
            md_bg_color=(1, 0.5, 0, 1), on_release=self.do_search,
        ))
        self.scroll = MDScrollView()
        self.list = MDList()
        self.scroll.add_widget(self.list)
        box.add_widget(self.scroll)
        box.add_widget(MDFlatButton(
            text=fa("بازگشت"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(45),
            on_release=lambda x: self.back(),
        ))
        self.add_widget(box)

    def do_search(self, *a):
        self.list.clear_widgets()
        q = self.query.text.strip()
        if not q:
            return
        con = sqlite3.connect(DB)
        c = con.cursor()
        c.execute("""SELECT id, plate, phone, vtype, spot, start, expire, amount
                     FROM subscribers WHERE plate LIKE ? OR spot LIKE ?""",
                  (f"%{q}%", f"%{q}%"))
        rows = c.fetchall()
        con.close()
        if not rows:
            self.list.add_widget(MDLabel(
                text=fa("چیزی پیدا نشد"), font_name='Vazir',
                halign='center', size_hint_y=None, height=dp(50),
            ))
        for row in rows:
            self.list.add_widget(SubCard(row, MDApp.get_running_app()))

    def back(self):
        self.manager.current = "main"


class ReportScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = MDBoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        box.add_widget(MDLabel(
            text=fa("📊 گزارش‌ها"), font_name='Vazir', halign='center',
            font_style='H5', size_hint_y=None, height=dp(50),
            theme_text_color='Custom', text_color=(1, 0.5, 0, 1), bold=True,
        ))
        self.scroll = MDScrollView()
        self.list = MDList()
        self.scroll.add_widget(self.list)
        box.add_widget(self.scroll)
        box.add_widget(MDRaisedButton(
            text=fa("بروزرسانی"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(45),
            md_bg_color=(1, 0.5, 0, 1), on_release=lambda x: self.load(),
        ))
        box.add_widget(MDFlatButton(
            text=fa("بازگشت"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(45),
            on_release=lambda x: self.back(),
        ))
        self.add_widget(box)

    def on_enter(self):
        self.load()

    def load(self):
        self.list.clear_widgets()
        con = sqlite3.connect(DB)
        c = con.cursor()

        c.execute("SELECT COUNT(*) FROM subscribers")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM subscribers WHERE vtype='car'")
        cars = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM subscribers WHERE vtype='motor'")
        motors = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM subscribers WHERE vtype='heavy'")
        heavies = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments")
        total_income = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE date LIKE ?",
                  (f"{datetime.now().strftime('%Y-%m')}%",))
        month_income = c.fetchone()[0]

        # فعال و منقضی
        c.execute("SELECT expire FROM subscribers")
        active = 0
        expired = 0
        for (exp,) in c.fetchall():
            try:
                d = datetime.strptime(exp, "%Y-%m-%d")
                if d >= datetime.now():
                    active += 1
                else:
                    expired += 1
            except:
                pass
        con.close()

        items = [
            ("👥", f"کل مشتریان: {fa_num(total)}"),
            ("🚗", f"خودرو سواری: {fa_num(cars)}"),
            ("🏍️", f"موتورسیکلت: {fa_num(motors)}"),
            ("🚐", f"وانت / شاسی‌بلند: {fa_num(heavies)}"),
            ("✅", f"فعال: {fa_num(active)}"),
            ("❌", f"منقضی: {fa_num(expired)}"),
            ("💰", f"درآمد کل: {fa_num(total_income)} تومان"),
            ("📅", f"درآمد این ماه: {fa_num(month_income)} تومان"),
        ]
        for icon, text in items:
            item = TwoLineAvatarIconListItem(text=fa(text))
            item.font_name = 'Vazir'
            item.add_widget(IconLeftWidget(icon=icon.replace("👥", "account-group")
                                                 .replace("🚗", "car")
                                                 .replace("🏍️", "motorbike")
                                                 .replace("🚐", "van-utility")
                                                 .replace("✅", "check-circle")
                                                 .replace("❌", "close-circle")
                                                 .replace("💰", "cash")
                                                 .replace("📅", "calendar")))
            self.list.add_widget(item)

    def back(self):
        self.manager.current = "main"


class SettingsScreen(MDScreen):
    def __init__(self, **kw):
        super().__init__(**kw)
        box = MDBoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        box.add_widget(MDLabel(
            text=fa("⚙️ تنظیمات قیمت‌ها"), font_name='Vazir', halign='center',
            font_style='H5', size_hint_y=None, height=dp(50),
            theme_text_color='Custom', text_color=(1, 0.5, 0, 1), bold=True,
        ))
        self.p_car = MDTextField(hint_text=fa("قیمت خودرو سواری (تومان)"),
                                  font_name='Vazir', input_filter='int',
                                  size_hint_y=None, height=dp(60))
        self.p_motor = MDTextField(hint_text=fa("قیمت موتورسیکلت (تومان)"),
                                    font_name='Vazir', input_filter='int',
                                    size_hint_y=None, height=dp(60))
        self.p_heavy = MDTextField(hint_text=fa("قیمت وانت / شاسی‌بلند (تومان)"),
                                    font_name='Vazir', input_filter='int',
                                    size_hint_y=None, height=dp(60))
        box.add_widget(self.p_car)
        box.add_widget(self.p_motor)
        box.add_widget(self.p_heavy)
        box.add_widget(MDRaisedButton(
            text=fa("ذخیره"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(50),
            md_bg_color=(1, 0.5, 0, 1), on_release=self.save,
        ))
        box.add_widget(MDFlatButton(
            text=fa("بازگشت"), font_name='Vazir',
            size_hint_x=1, size_hint_y=None, height=dp(45),
            on_release=lambda x: self.back(),
        ))
        self.add_widget(box)

    def on_enter(self):
        self.p_car.text = str(get_setting('price_car'))
        self.p_motor.text = str(get_setting('price_motor'))
        self.p_heavy.text = str(get_setting('price_heavy'))

    def save(self, *a):
        try:
            set_setting('price_car', int(self.p_car.text or 0))
            set_setting('price_motor', int(self.p_motor.text or 0))
            set_setting('price_heavy', int(self.p_heavy.text or 0))
            toast(fa("✅ ذخیره شد"))
        except:
            toast(fa("عدد نامعتبر"))

    def back(self):
        self.manager.current = "main"


# ================== اپ اصلی ==================
class JayeParkApp(MDApp):
    def build(self):
        self.title = "Jaye Park"
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.primary_hue = "500"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.font_styles['H4'] = ['Vazir', 28, False, 0.15]
        self.theme_cls.font_styles['H5'] = ['Vazir', 22, False, 0.15]
        self.theme_cls.font_styles['H6'] = ['Vazir', 18, False, 0.15]
        self.theme_cls.font_styles['Subtitle1'] = ['Vazir', 15, False, 0.15]
        self.theme_cls.font_styles['Subtitle2'] = ['Vazir', 13, False, 0.15]
        self.theme_cls.font_styles['Body1'] = ['Vazir', 14, False, 0.15]
        self.theme_cls.font_styles['Body2'] = ['Vazir', 12, False, 0.15]
        self.theme_cls.font_styles['Button'] = ['Vazir', 14, True, 0.15]
        self.theme_cls.font_styles['Caption'] = ['Vazir', 11, False, 0.15]

        init_db()

        sm = MDScreenManager()
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(AddScreen(name="add"))
        sm.add_widget(ListScreen(name="list"))
        sm.add_widget(WarnScreen(name="warn"))
        sm.add_widget(SearchScreen(name="search"))
        sm.add_widget(ReportScreen(name="report"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

    def open_edit_dialog(self, sub_data):
        sid, plate, phone, vtype, spot, start, expire, amount = sub_data
        self._edit_sid = sid

        content = MDBoxLayout(orientation='vertical', spacing=dp(10),
                               size_hint_y=None, height=dp(340))
        self.e_plate = MDTextField(text=plate, hint_text=fa("پلاک"), font_name='Vazir')
        self.e_phone = MDTextField(text=phone or "", hint_text=fa("تماس"),
                                    font_name='Vazir', input_filter='int')
        self.e_vtype = MDTextField(text=vtype, hint_text=fa("نوع"),
                                    font_name='Vazir')
        self.e_spot = MDTextField(text=spot, hint_text=fa("محل"), font_name='Vazir')
        self.e_expire = MDTextField(text=expire, hint_text=fa("تاریخ انقضا (YYYY-MM-DD)"),
                                     font_name='Vazir')
        for w in [self.e_plate, self.e_phone, self.e_vtype, self.e_spot, self.e_expire]:
            w.size_hint_y = None
            w.height = dp(60)
            content.add_widget(w)

        self.edit_dialog = MDDialog(
            title=fa("ویرایش مشتری"),
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text=fa("لغو"), font_name='Vazir',
                              on_release=lambda x: self.edit_dialog.dismiss()),
                MDRaisedButton(text=fa("ذخیره"), font_name='Vazir',
                                md_bg_color=(1, 0.5, 0, 1),
                                on_release=lambda x: self.save_edit()),
            ],
        )
        self.edit_dialog.open()

    def save_edit(self):
        try:
            con = sqlite3.connect(DB)
            c = con.cursor()
            c.execute("""UPDATE subscribers SET plate=?, phone=?, vtype=?, spot=?, expire=?
                         WHERE id=?""",
                      (self.e_plate.text, self.e_phone.text, self.e_vtype.text,
                       self.e_spot.text, self.e_expire.text, self._edit_sid))
            con.commit()
            con.close()
            self.edit_dialog.dismiss()
            toast(fa("✅ ذخیره شد"))
            self.screen_manager_refresh()
        except Exception as e:
            toast(fa(f"خطا: {e}"))

    def screen_manager_refresh(self):
        sm = self.root
        if sm and sm.current == "list":
            sm.get_screen("list").load()
        elif sm and sm.current == "warn":
            sm.get_screen("warn").on_enter()

    def open_renew_dialog(self, sub_data):
        sid, plate, phone, vtype, spot, start, expire, amount = sub_data
        self._renew_sid = sid
        self._renew_vtype = vtype

        price_key = {'car': 'price_car', 'motor': 'price_motor', 'heavy': 'price_heavy'}.get(vtype, 'price_car')
        default_price = get_setting(price_key)

        content = MDBoxLayout(orientation='vertical', spacing=dp(10),
                               size_hint_y=None, height=dp(260))
        self.r_months = MDTextField(text="1", hint_text=fa("تعداد ماه"),
                                     font_name='Vazir', input_filter='int',
                                     size_hint_y=None, height=dp(60))
        self.r_amount = MDTextField(text=str(default_price),
                                     hint_text=fa("مبلغ پرداختی"),
                                     font_name='Vazir', input_filter='int',
                                     size_hint_y=None, height=dp(60))
        self.r_note = MDTextField(hint_text=fa("توضیح (اختیاری)"),
                                   font_name='Vazir',
                                   size_hint_y=None, height=dp(60))
        content.add_widget(self.r_months)
        content.add_widget(self.r_amount)
        content.add_widget(self.r_note)

        self.renew_dialog = MDDialog(
            title=fa(f"تمدید {plate}"),
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text=fa("لغو"), font_name='Vazir',
                              on_release=lambda x: self.renew_dialog.dismiss()),
                MDRaisedButton(text=fa("تمدید"), font_name='Vazir',
                                md_bg_color=(1, 0.5, 0, 1),
                                on_release=lambda x: self.do_renew()),
            ],
        )
        self.renew_dialog.open()

    def do_renew(self):
        try:
            months = int(self.r_months.text or 1)
            amount = int(self.r_amount.text or 0)
            note = self.r_note.text or fa("تمدید")

            con = sqlite3.connect(DB)
            c = con.cursor()
            c.execute("SELECT expire FROM subscribers WHERE id=?", (self._renew_sid,))
            row = c.fetchone()
            old_exp = datetime.strptime(row[0], "%Y-%m-%d") if row else datetime.now()
            # اگر منقضی شده، از امروز حساب کن؛ وگرنه از تاریخ انقضای قبلی
            base = max(old_exp, datetime.now())
            new_exp = add_months(base, months)

            c.execute("UPDATE subscribers SET expire=? WHERE id=?",
                      (new_exp.strftime("%Y-%m-%d"), self._renew_sid))
            c.execute("""INSERT INTO payments (sub_id, date, months, amount, note)
                         VALUES (?, ?, ?, ?, ?)""",
                      (self._renew_sid, today_str(), months, amount, note))
            con.commit()
            con.close()

            self.renew_dialog.dismiss()
            toast(fa(f"✅ تمدید شد | انقضای جدید: {new_exp.strftime('%Y-%m-%d')}"))
            self.screen_manager_refresh()
        except Exception as e:
            toast(fa(f"خطا: {e}"))

    def confirm_delete(self, sub_data):
        sid = sub_data[0]
        plate = sub_data[1]
        self._del_sid = sid

        self.del_dialog = MDDialog(
            title=fa("حذف مشتری"),
            text=fa(f"آیا از حذف {plate} مطمئنی؟"),
            buttons=[
                MDFlatButton(text=fa("لغو"), font_name='Vazir',
                              on_release=lambda x: self.del_dialog.dismiss()),
                MDRaisedButton(text=fa("حذف"), font_name='Vazir',
                                md_bg_color=(0.8, 0.2, 0.2, 1),
                                on_release=lambda x: self.do_delete()),
            ],
        )
        self.del_dialog.open()

    def do_delete(self):
        con = sqlite3.connect(DB)
        c = con.cursor()
        c.execute("DELETE FROM subscribers WHERE id=?", (self._del_sid,))
        c.execute("DELETE FROM payments WHERE sub_id=?", (self._del_sid,))
        con.commit()
        con.close()
        self.del_dialog.dismiss()
        toast(fa("🗑 حذف شد"))
        self.screen_manager_refresh()

    def backup_db(self):
        try:
            downloads = "/storage/emulated/0/Download"
            if not os.path.isdir(downloads):
                downloads = os.path.expanduser("~")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(downloads, f"parking_backup_{timestamp}.db")
            shutil.copy(DB, dest)
            toast(fa(f"✅ پشتیبان در: {dest}"))
        except Exception as e:
            toast(fa(f"خطا: {e}"))


if __name__ == "__main__":
    JayeParkApp().run()
