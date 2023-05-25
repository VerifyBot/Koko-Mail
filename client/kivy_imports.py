from kivy.properties import ObjectProperty
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, ScreenManager, SwapTransition, NoTransition
from kivymd.uix.button import MDFillRoundFlatIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.tab import MDTabsBase, MDTabs
from kivymd.icon_definitions import md_icons
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivy.properties import VariableListProperty
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import TwoLineIconListItem, TwoLineAvatarIconListItem, TwoLineRightIconListItem, TwoLineListItem, \
  TwoLineAvatarListItem, IconLeftWidget, MDList, OneLineIconListItem, IRightBodyTouch
from kivy.properties import StringProperty
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.chip import MDChip
from kivy.uix.gridlayout import GridLayout
from kivymd.uix.snackbar import Snackbar
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.chip import MDChip
from kivymd.uix.scrollview import MDScrollView
from kivy.uix.boxlayout import BoxLayout


class Tab(MDFloatLayout, MDTabsBase):
  icon = ObjectProperty()


themes_combinations = [
  {
    "name": "Default Theme",
    "primary_color": "Amber",
    "accent_color": "Red",
    "theme_style": "Dark"
  },
  {
    "name": "Bubblegum",
    "primary_color": "Teal",
    "accent_color": "DeepOrange",
    "theme_style": "Dark"
  },
  {
    "name": "Sunshine",
    "primary_color": "Indigo",
    "accent_color": "Yellow",
    "theme_style": "Dark"
  },
  {
    "name": "Electric",
    "primary_color": "Red",
    "accent_color": "LightGreen",
    "theme_style": "Dark"
  },
  {
    "name": "Cosmic",
    "primary_color": "Pink",
    "accent_color": "Cyan",
    "theme_style": "Dark"
  }
]


class ThemedButton(MDRaisedButton):
  pass
