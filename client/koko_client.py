import ssl
import re
import functools
import time

import easygui

from kivy_imports import *

import os
import random
import socket
import sys
import traceback

from urllib.parse import urlencode, parse_qs

from utils import *
import logging

# setup simple logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def logtcp(dir, byte_data):
  """
  log direction and all TCP byte array data
  return: void
  """
  if dir == 'sent':
    print(f'C LOG:Sent     >>>{byte_data[:300]}')
  else:
    print(f'C LOG:Recieved <<<{byte_data[:300]}')


class ExitResponded(Exception):
  """Raised when the server responds ok with the exit request (easy to stop the loop)"""
  pass


def exit_resp(sock: socket.socket):
  raise ExitResponded


def handle_server_response(sock: socket.socket, mdata: dict):
  """
   Handle messages that come from the server.
   Message is already parsed in the dict and ready to be handled.
  """

  route = mdata['route']
  mtype = mdata['type']

  # possible items in mdata:
  mtype = mdata['type']
  mdata = mdata['data']  # data (raw/json)

  if mtype == MessageType.ERROR:
    # This is where we can handle the specific error codes with specific messages
    # for now we just print the error code and message, but we can do more.
    print(f'Server responded with error: {mdata}')

    # check if the server is still connected
    # because some errors are critical (like the server shutting down) and we should exit
    # but some are fine like unknown command or bad arguments.
    if not is_alive(sock):  # We send an OK? message to the server to check if it's still alive
      raise ConnectionError
    return mdata

  elif mtype not in [MessageType.JSON, MessageType.RAW]:
    print(f'Server response (unstructured): {margs}')
    return

  # print the response
  # print(f'Server responded to {route}:\n\t{mdata=}')

  return mdata


def send_to_server(sock: socket.socket, msg_type: int, msg_route: str, msg_data):
  """
  Send a emssage to the server, following the protocol
  """

  if msg_type in [MessageType.JSON, MessageType.ERROR]:
    msg_data = jsoon.dumps(msg_data)
    msg = f"c{msg_type}{msg_route}{msg_data}".encode()
  else:
    msg = f"c{msg_type}{msg_route}".encode() + msg_data
  length_header = length_header_send(msg)

  try:
    sock.send(length_header + msg)

    logging.info(f'[@] Sent message \n\t{msg_type=}\n\t{msg_route=}\n\t{msg_data[:100]=}')

    # we expect a response from the server, so we wait for it
    resp = fetch_all(sock)
    mdata = parse_message_by_protocol(resp)

    return handle_server_response(sock, mdata)
  except ConnectionError:
    print('Connection to server was lost')
    exit()
  except ExitResponded:
    print("Server tells you ok, bye bye")
    exit()
  except DisconnectedError:
    logging.error(f'Server disconnected during recv()')
    exit()
  except BadMessageError as e:
    logging.error(f'Server sent bad message ({e})')
    exit()
  except socket.error as err:
    logging.error(f'Socket Error exit client loop: err:  {err}')
    exit()
  except Exception as err:
    logging.error(f'General Error %s exit client loop: {err}')
    logging.error(traceback.format_exc())
    exit()


class IndexCls:
  def check_creds(self, username, password, email=None):
    if not re.match(r'^[a-zA-Z0-9]{3,20}$', username):
      self.alert('[b]Username Invalid![/b] 3-20 English letters/numbers', color='#e74c3c')
      return False

    # password must be at least 4 characters and max 20, only [a-zA-z0-9$@#]
    if not re.match(r'^[a-zA-Z0-9$@#]{4,20}$', password):
      self.alert('[b]Password Invalid![/b] 4-20 English letters/numbers/$@#', color='#e74c3c')
      return False

    # email must be valid
    if email and not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
      self.alert('[b]Email Invalid![/b] You know how it should look like...', color='#e74c3c')
      return False

    return True

  def on_login(self, o):

    username = self.login_comp['username'].text.strip('@')
    password = self.login_comp['password'].text

    print(f'{username=}, {password=}')

    if not self.check_creds(username, password):
      return

    # send the request to the server
    resp = send_to_server(self.sock, MessageType.JSON, 'LOGN', {
      'username': username,
      'password': password
    })

    if err := resp.get('error'):
      return self.alert(f'[b]Error:[/b] {err}', color='#e74c3c')

    # if we got here, the registration was successful
    self.auth = resp['auth']
    self.username = username
    self.email = resp['email']

    self.root.current = 'maillist'
    self.alert(f'[b]Welcome back {username}![/b] You are now logged in', color='#2ecc71')

    for aw in self.account_widgets:
      aw.text = f"Signed in as @{username} ({self.email})"

    self.update_mail_list()

  def on_register(self, o):
    """
    Called when the user clicks the register button
    and aims to create a new account.
    """

    username = self.register_comp['username'].text
    email = self.register_comp['email'].text
    password = self.register_comp['password'].text

    print(f"{username=}, {email=}, {password=}")

    # username must be at least 3 characters and max 20, only [a-zA-z0-9]
    if not self.check_creds(username, password, email):
      return

    # send the request to the server
    resp = send_to_server(self.sock, MessageType.JSON, 'RGST', {
      'username': username,
      'email': email,
      'password': password
    })

    # print(f'Register response: {resp}')

    if err := resp.get('error'):
      return self.alert(f'[b]Error:[/b] {err}', color='#e74c3c')

    # if we got here, the registration was successful
    self.auth = resp['auth']
    self.username = username
    self.email = email

    self.root.current = 'maillist'
    self.alert(f'[b]Welcome {username}![/b] You are now logged in', color='#2ecc71')

    for aw in self.account_widgets:
      aw.text = f"Signed in as @{username} ({email})"

    self.update_mail_list()


class MailListCls:
  def click_mailrow(self, id):
    self.load_mail(id=id)
    self.root.current = 'mail'


class ViewMailScreen(MDScreen):
  def __init__(self, appbar, app, **kwargs):
    self.app = app
    super().__init__(**kwargs)

    # Create the email sender label and text input
    self.sender_input = MDTextField(hint_text='From:', readonly=True)

    # Create the email subject label and text input
    self.subject_label = MDLabel(text='Subject', halign='center', font_style='H4')

    # Create the email body label and text input
    self.body_label = MDTextField(text='Body', halign='center', multiline=True, readonly=True, mode='fill')

    # Create the files label and file chips
    self.files_list = BoxLayout(orientation='vertical', spacing='5dp')
    self.scroll_view = MDScrollView()
    self.scroll_view.add_widget(self.files_list)

    body_layout = BoxLayout(orientation='vertical')
    body_scroll_view = MDScrollView()
    body_scroll_view.add_widget(self.body_label)
    body_layout.add_widget(body_scroll_view)

    # Wrap the widgets in a vertical box layout
    box_layout = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
    box_layout.add_widget(self.sender_input)
    box_layout.add_widget(self.subject_label)
    box_layout.add_widget(body_layout)
    box_layout.add_widget(self.scroll_view)

    # Add the box layout to the screen layout
    bb = BoxLayout(orientation='vertical')
    bb.add_widget(appbar)
    bb.add_widget(box_layout)
    self.add_widget(bb)

  def set_mail_info(self, id, auth, sock):
    mail = send_to_server(sock, MessageType.JSON, 'MAIL', {'auth': auth, 'id': id})

    # print(f'🪁 Fetched {mail=}')
    self.subject_label.text = mail['subject']
    self.body_label.text = mail['body']
    self.sender_input.text = mail['sender']

    def download_attachment(card):
      # print(card.text)
      resp = send_to_server(sock, MessageType.JSON, 'GFLE', {'auth': auth, 'id': id, 'filename': card.text})
      # print(resp)

      save_path = os.path.join(os.path.expanduser('~'), 'Downloads', card.text)

      with open(save_path, 'wb') as f:
        f.write(resp)

      self.app.alert(f'[b]Downloaded {card.text}[/b] to {save_path}', color='#1abc9c')

    # Add the files as MDChip widgets to the files list
    self.files_list.clear_widgets()
    for file in mail['attachments'].strip(',').split(','):
      if not file: continue

      chip = MDChip(text=file, icon_right='download', on_release=download_attachment)
      self.files_list.add_widget(chip)

  def open_file(self, chip):
    # Replace this method with your own implementation to open the file
    print(f"Opening file {chip.text}")


class KokoMail(MDApp, IndexCls, MailListCls):
  """
  The class that handles the UI *and* the Client Network
  """
  title = "Koko Mail"

  def __init__(self, sock: socket.socket, *args, **kw):
    """Initialize the app with the socket"""
    super().__init__(*args, **kw)

    self.snack = None  # for app alerts via self.alert(msg, color)

    self.sock = sock  # socket connection to the server

    self.auth = None  # the auth token
    self.username = None
    self.email = None

    self.mails = []

    self.mail_filter = None

  def load_mail(self, id):
    self.mailscreen.set_mail_info(id, self.auth, self.sock)

  def send_mail(self, to, subject, body, files):
    if not to:
      return self.alert('[b]To is empty![/b] Please enter a recipient', color='#e74c3c')
    if not subject:
      return self.alert('[b]Subject is empty![/b] Please enter a subject', color='#e74c3c')
    body = body or 'No body.'

    if to.startswith('@'):
      to = to[1:]

    resp = send_to_server(self.sock, MessageType.JSON, 'SEND', {
      'auth': self.auth,
      'to': to,
      'subject': subject,
      'body': body,
    })

    if err := resp.get('error'):
      return self.alert(f'[b]Error:[/b] {err}', color='#e74c3c')

    # send files
    for file in files:
      with open(file, 'rb') as f:
        data = f.read()

      filename = file[:200].ljust(200, ' ').encode()

      # print((self.auth.encode() + filename + data)[:500])

      r = send_to_server(self.sock, MessageType.RAW, 'FILE', self.auth.encode() + filename + data)

      if err := r.get('error'):
        return self.alert(f'[b]Error:[/b] {err}', color='#e74c3c')

    self.alert(f'[b]Mail sent![/b] Your mail was sent successfully', color='#2ecc71')

    self.update_mail_list()
    self.load_mail(id=resp['id'])
    self.root.current = 'mail'

  def on_trash_can_pressed(self, button):
    trash_can_buttons = [widget for widget in self.root.walk() if
                         isinstance(widget, MDIconButton) and widget.icon == "trash-can"]
    idx = trash_can_buttons.index(button)

    mail_id = int(self.maillist_obj.ids.rv.data[idx]['mailid'])

    # mark mail as spam
    resp = send_to_server(self.sock, MessageType.JSON, 'SPAM', {'auth': self.auth, 'id': mail_id})

    if resp['set']:
      self.alert(f'[b]Mail marked as spam![/b]', color='#9b59b6')
    else:
      self.alert(f'[b]Moved mail out of spam![/b]', color='#9b59b6')

    self.update_mail_list()

  def on_star_pressed(self, button):
    star_buttons = [widget for widget in self.root.walk() if
                    isinstance(widget, MDIconButton) and widget.icon == "star"]
    idx = star_buttons.index(button)

    mail_id = int(self.maillist_obj.ids.rv.data[idx]['mailid'])

    # mark mail as important
    resp = send_to_server(self.sock, MessageType.JSON, 'IMPT', {'auth': self.auth, 'id': mail_id})

    if resp['set']:
      self.alert(f'[b]Mail is starred![/b]', color='#d35400')
      # set star icon color to yellow (not the background)
    else:
      self.alert(f'[b]Mail is no longer starred![/b]', color='#d35400')

    # refresh rycleview
    self.update_mail_list()

  def logout(self, _):
    if self.auth:
      send_to_server(self.sock, MessageType.JSON, 'LOUT', {'auth': self.auth})
      self.auth = None
      self.username = None
      self.email = None
      self.root.current = 'index'
      self.alert("Logged out!", color='#9b59b6')

  def alert(self, msg, color='#ddbb34'):
    # kill all previous snacks
    if self.snack:
      self.snack.dismiss()

    # add a new snackbar to the current screen
    self.snack = Snackbar(
      text=f"[color={color}]{msg}[/color]",
      snackbar_y="10dp",
      pos_hint={"center_x": .5, "center_y": .1},
      size_hint_x=.5,
      duration=3)
    self.snack.open()

  def update_mail_list(self):
    if not self.auth:
      return

    if self.mail_filter != 'sent':
      resp = send_to_server(self.sock, MessageType.JSON, 'MLST', {'auth': self.auth})
    else:
      resp = send_to_server(self.sock, MessageType.JSON, 'MSNT', {'auth': self.auth})

    if err := resp.get('error'):
      return self.alert(f'[b]Error:[/b] {err}', color='#e74c3c')

    self.mails = resp['mails'][::-1]

    # print(self.mails)

    def check_mail_filter(m):
      if self.mail_filter == 'sent':
        return True

      is_spam = m.get('spam', False)
      is_star = m.get('star', False)

      if self.mail_filter is None:
        return not is_spam
      elif self.mail_filter == 'spam':
        return is_spam
      elif self.mail_filter == 'star':
        return is_star

      return True

    show_mails = []

    for i, m in enumerate(self.mails):
      if not check_mail_filter(m):
        continue

      mail_txt = f"[@{m['sender']}] {m['subject']}"

      if m.get('read') == 0:
        mail_txt = f"[b]{mail_txt}[/b]"

      show_mails.append(
        {
          "viewclass": "CustomOneLineIconListItem" if self.mail_filter != 'sent' else "CustomOneLineIconListItemSent",
          "text": mail_txt,
          "secondary_text": m['body'][:50] + ('...' if len(m['body']) > 50 else ''),
          "mailid": str(m['id']),
          "on_press": functools.partial(self.click_mailrow, m['id']),
          "theme_text_color": 'Custom' if m.get('star', False) else 'Primary',
          "text_color": (1, 0.8, 0, 1) if m.get('star', False) else (1, 1, 1, 1),
        }
      )

    self.maillist_obj.ids.rv.data = show_mails
    self.maillist_obj.ids.rv.refresh_from_data()

  def build(self):
    theme = {'primary_color': 'Amber', 'accent_color': 'Red', 'theme_style': 'Dark', }

    if os.path.exists('client_config.json'):
      with open('client_config.json', 'r') as f:
        theme = jsoon.load(f).get('theme', theme)

    self.theme_cls.primary_palette = theme['primary_color']
    self.theme_cls.accent_palette = theme['accent_color']
    self.theme_cls.theme_style = theme['theme_style']

    sm = ScreenManager(transition=SwapTransition())

    # Index Screen
    IndexScreen = Screen(name='index')

    self.IndexTabs = MDBoxLayout(
      MDTopAppBar(title="KokoMail"),
      MDTabs(id="tabs"),
      orientation="vertical",
    )
    IndexScreen.add_widget(self.IndexTabs)

    sm.add_widget(IndexScreen)

    # Mail List Screen
    MailListScreen = Screen(name='maillist')

    self.MailListLayout = MDBoxLayout()

    self.account_widgets = [
      MDLabel(text="Not signed in", theme_text_color="Error"),
      MDLabel(text="Not signed in", theme_text_color="Error"),
      MDLabel(text="Not signed in", theme_text_color="Error"),
    ]

    ap = MDTopAppBar(title="KokoMail", right_action_items=[['logout', self.logout, 'Log Out']])
    ap.add_widget(self.account_widgets[0])

    MailListScreen.add_widget(MDBoxLayout(
      ap,
      self.MailListLayout,
      orientation="vertical",
    ))
    sm.add_widget(MailListScreen)

    # Mail Screen

    ap2 = MDTopAppBar(title="KokoMail", right_action_items=[
      ['logout', self.logout, 'Log Out'],
      ['arrow-u-right-top', lambda _: (self.update_mail_list(), setattr(sm, 'current', 'maillist'))]
    ])
    ap2.add_widget(self.account_widgets[1])

    # sm.add_widget(MailScreen)
    self.mailscreen = ViewMailScreen(ap2, self, name='mail')
    sm.add_widget(self.mailscreen)

    # Mail Create Screen
    MailCreateScreen = Screen(name='mailcreate')
    self.MailCreateLayout = GridLayout(cols=1, spacing=10, padding=20, size_hint=(.6, None),
                                       pos_hint={'center_x': 0.5, 'center_y': 0.5})
    self.MailCreateLayout.bind(minimum_height=self.MailCreateLayout.setter('height'))

    MailCreateScreen.add_widget(self.MailCreateLayout)

    sm.add_widget(MailCreateScreen)

    # Settings Screen
    SettingsScreen = Screen(name='settings')
    self.SettingsScreenLayout = MDFloatLayout()

    ap3 = MDTopAppBar(title="KokoMail", right_action_items=[
      ['logout', self.logout, 'Log Out'],
      ['arrow-u-right-top', lambda _: (self.update_mail_list(), setattr(sm, 'current', 'maillist'))]
    ])
    ap3.add_widget(self.account_widgets[2])

    SettingsScreen.add_widget(MDBoxLayout(
      ap3,
      self.SettingsScreenLayout,
      orientation="vertical",
    ))

    sm.add_widget(SettingsScreen)

    self.maillist_obj = None

    sm.current = 'index'

    return sm

  def on_start(self):
    """
    Here we build all the screens
    """

    self.build_index_screen()
    self.build_maillist_screen()
    self.build_mailcreate_screen()
    self.build_settings_screen()

  def build_mailcreate_screen(self):
    self.MailCreateLayout.add_widget(MDLabel(text='Create Mail', halign='center', font_style='H4'))

    # Create 3 input fields and a button inside the box
    to = MDTextField(hint_text=f'To', size_hint=(1, None), write_tab=False)
    self.MailCreateLayout.add_widget(to)
    subject = MDTextField(hint_text=f'Subject', size_hint=(1, None), write_tab=False)
    self.MailCreateLayout.add_widget(subject)
    body = MDTextField(hint_text=f'Body', multiline=True, size_hint=(1, None), height=400, padding=10, write_tab=False)
    self.MailCreateLayout.add_widget(body)

    atchs_group = MDGridLayout(cols=4, spacing='10dp', padding=[0, '-140dp'], pos_hint={"center_x": .1, "center_y": .9},
                               adaptive_size=True, adaptive_height=True, width='60dp')

    raw_attachments = set()
    atchs_objs = {}

    def remove_attachment(card):
      atchs_group.remove_widget(card)
      raw_attachments.remove(atchs_objs[card])

    def choose_attachment(*args):
      names = set(easygui.fileopenbox(multiple=True) or []).difference(raw_attachments)

      for atc in names:
        if len(raw_attachments) > 8:
          self.alert('You can only attach up to 9 files!')
          break

        raw_attachments.add(atc)

        attachment_card = MDChip(
          text=atc.rsplit('\\', 1)[-1],
          icon_right="close-circle-outline",
          on_release=remove_attachment,
        )

        atchs_objs[attachment_card] = atc
        atchs_group.add_widget(attachment_card)
        # print(f"added {atc}")

    self.MailCreateLayout.add_widget(atchs_group)

    btns = [
      MDFillRoundFlatIconButton(text='Send', icon='send', text_color='darkgreen', icon_color='darkgreen',
                                font_style='Subtitle1',
                                on_release=lambda _: self.send_mail(to.text, subject.text, body.text, raw_attachments)),
      MDFillRoundFlatIconButton(text='Add Files', icon='attachment', text_color='darkblue', icon_color='darkblue',
                                font_style='Subtitle1', on_release=choose_attachment),
      MDFillRoundFlatIconButton(text='Cancel', icon='trash-can', text_color='darkred', icon_color='darkred',
                                on_release=lambda _: setattr(self.root, 'current', 'maillist'), font_style='Subtitle1')
    ]

    self.MailCreateLayout.add_widget(MDGridLayout(*btns, orientation='lr-bt', rows=1, spacing=10, padding=[0, -40]))

  def set_maillist(self, filter=None):
    keep_mails = []

    # todo: search is broken

    for i, m in enumerate(self.mails):
      if filter in str(m):
        keep_mails.append(self.maillist_obj.ids.rv.data[i])

    self.maillist_obj.ids.rv.data = keep_mails

  def apply_mail_filter(self, fl, btn):

    self.mail_filter = fl

    # reset other btns' background
    for w in self.root.walk():
      if hasattr(w, 'id') and w.id.startswith('ea_'):
        w.md_bg_color = [0.129, 0.129, 0.129, 1.0]

    btn.md_bg_color = (230 / 255, 126 / 255, 34 / 255, 1.0)

    self.update_mail_list()

  def build_maillist_screen(self):
    edge_apps = MDBoxLayout(orientation='vertical', spacing=10, pos_hint={'top': 1.15}, padding=20, size_hint=(.24, 1))
    for edge_app in [('Mailbox', 'notification-clear-all', functools.partial(self.apply_mail_filter, None)),
                     ('Important', 'star', functools.partial(self.apply_mail_filter, 'star')),
                     ('Spam', 'trash-can', functools.partial(self.apply_mail_filter, 'spam')),
                     ('Forwarded', 'chevron-double-right'),
                     ('Sent', 'chart-bubble', functools.partial(self.apply_mail_filter, 'sent')),
                     ('Settings', 'cog', lambda _: setattr(self.root, 'current', 'settings'))
                     ]:
      edge_apps.add_widget(
        MDChip(text=edge_app[0], icon_left=edge_app[1], on_release=edge_app[2] if len(edge_app) > 2 else lambda _: _,
               id='ea_' + edge_app[0]))

    edge_apps.add_widget(MDList())
    edge_apps.add_widget(MDList())
    edge_apps.add_widget(MDChip(text="Compose", icon_left="pencil", elevation=4, radius=10, text_color="lightblue",
                                icon_left_color="lightblue",
                                on_press=lambda x: setattr(self.root, 'current', 'mailcreate')
                                ))

    self.maillist_obj = Builder.load_file('mailrow.kv')

    class CustomOneLineIconListItem(TwoLineRightIconListItem):
      icon = StringProperty()

    class CustomOneLineIconListItemSent(TwoLineRightIconListItem):
      icon = StringProperty()

    class YourContainer(IRightBodyTouch, MDBoxLayout):
      padding = (-80, 0, 0, 0)
      pass

    self.maillist_obj.ids.rv.data = []

    self.MailListLayout.add_widget(edge_apps)
    self.MailListLayout.add_widget(MDScrollView(self.maillist_obj, size_hint=(.9, .9)))

    # print(YourContainer.ids)

  def set_theme(self, theme, btn):
    self.theme_cls.primary_palette = theme['primary_color']
    self.theme_cls.accent_palette = theme['accent_color']
    self.theme_cls.theme_style = theme['theme_style']

    with open('client_config.json') as f:
      dt = jsoon.load(f)

    dt['theme'] = theme

    with open('client_config.json', 'w') as f:
      jsoon.dump(dt, f, indent=2)

    self.alert('Restart the app to apply changes!')

    # # change every existing button to new theme
    # for w in self.root.walk():
    #   if isinstance(w, ThemedButton):
    #     w.md_bg_color = self.theme_cls.primary_color

  def build_settings_screen(self):

    # put on center of screen
    theme_choose_list = MDList(
      pos_hint={'center_x': .55, 'center_y': .5},
      size_hint=(.5, .5),
      spacing=10,
      padding=10,

    )

    # mdtextfield with no underline
    theme_choose_list.add_widget(MDTextField(
      hint_text='Choose Theme',
      readonly=True,
      mode='fill',

    ))

    for i, theme in enumerate(themes_combinations, start=1):
      theme_choose_list.add_widget(
        MDRaisedButton(
          text=theme['name'],
          md_bg_color=(random.randint(1, 100) / 255, random.randint(1, 100) / 255, random.randint(1, 100) / 255, 55),
          text_color=(1, 1, 1, 1),
          icon='star',
          on_release=functools.partial(self.set_theme, theme)
        )
      )

    self.SettingsScreenLayout.add_widget(theme_choose_list)

  def build_index_screen(self):
    """
       [[ LOGIN LAYOUT ]]

       MDBoxLayout (login_box):
         MDTextField (username_input)   self.login_comp["username"]
         MDTextField (password_input)   self.login_comp["password"]
         MDRaisedButton (login_button)  handler::self.on_login()

       [[ REGISTER LAYOUT ]]

       MDBoxLayout (login_box):
         MDTextField (username_input)   self.register_comp["username"]
         MDTextField (email_input)      self.register_comp["email"]
         MDTextField (password_input)   self.register_comp["password"]
         MDRaisedButton (login_button)  handler::self.on_login()
       """

    # <LOGIN LAYOUT>

    login_box = MDBoxLayout(orientation='vertical', size_hint_y=None, size_hint_x=None,
                            width="300dp", pos_hint={"center_x": .5, "center_y": .5}, )
    username_input = MDTextField(hint_text="@username", icon_left="horse-human",
                                 write_tab=False, multiline=False, text="niryo123")
    password_input = MDTextField(hint_text="password", password=True, write_tab=False,
                                 multiline=False, icon_left="key-variant", text="niryo123")
    login_button = ThemedButton(text="     LOGIN     ", on_press=self.on_login)
    login_box.add_widget(username_input)
    login_box.add_widget(password_input)
    login_box.add_widget(login_button)

    self.login_comp = dict(username=username_input, password=password_input)
    self.IndexTabs.ids.tabs.add_widget(Tab(login_box, title="Login", icon="login", ))
    # </LOGIN LAYOUT>

    # <REGISTER LAYOUT>
    register_box = MDBoxLayout(orientation='vertical', size_hint_y=None, size_hint_x=None,
                               width="300dp", pos_hint={"center_x": .5, "center_y": .4}, )
    username_input = MDTextField(hint_text="username", icon_left="human-greeting-proximity",
                                 write_tab=False, multiline=False, text="niryo123")
    email_input = MDTextField(hint_text="email address", icon_left="email",
                              write_tab=False, multiline=False, text="mymail123@gmail.com")
    password_input = MDTextField(hint_text="password", password=True, write_tab=False,
                                 multiline=False, icon_left="key-variant", text="niryo123")
    register_button = ThemedButton(text=" CREATE ACCOUNT ", on_press=self.on_register)
    register_box.add_widget(username_input)
    register_box.add_widget(email_input)
    register_box.add_widget(password_input)
    register_box.add_widget(register_button)

    self.register_comp = dict(username=username_input, email=email_input, password=password_input)
    self.IndexTabs.ids.tabs.add_widget(Tab(register_box, title="Register", icon="badge-account", ))

    # </REGISTER LAYOUT>


def main():
  """
    main client - handle socket and main loop
    """

  sock = socket.socket()
  ip = SERVER_IP

  if ip == '0.0.0.0':
    ip = '127.0.0.1'

  port = SERVER_PORT

  ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
  ctx.load_verify_locations('new.pem')
  sock = ctx.wrap_socket(sock, server_hostname='merkaz')

  try:
    sock.connect((ip, port))
    print(f'Connect succeeded {ip}:{port}')
  except:
    print(f'Error while trying to connect.  Check ip or port -- {ip}:{port}')
    return

  KokoMail(sock).run()

  # while True:
  #   route = input('> ').strip().upper()
  #   data = jsoon.loads(input('Data: ').strip())
  #
  #   try:
  #     # send command
  #     send_to_server(sock, MessageType.JSON, route, data)
  #
  #     # receive reply from server
  #     resp = fetch_all(sock)
  #     mdata = parse_message_by_protocol(resp)
  #
  #     handle_server_response(sock, mdata)
  #   except ConnectionError:
  #     print('Connection to server was lost')
  #     break
  #   except ExitResponded:
  #     print("Server tells you ok, bye bye")
  #     break
  #   except DisconnectedError:
  #     logging.error(f'Server disconnected during recv()')
  #     break
  #   except BadMessageError as e:
  #     logging.error(f'Server sent bad message ({e})')
  #     break
  #   except socket.error as err:
  #     logging.error(f'Socket Error exit client loop: err:  {err}')
  #     break
  #   except Exception as err:
  #     logging.error(f'General Error %s exit client loop: {err}')
  #     logging.error(traceback.format_exc())
  #     break

  sock.close()


if __name__ == '__main__':
  main()
