import os
import contextlib
import hashlib
import random
import socket
import logging
import sqlite3
import ssl
import traceback
import threading
import uuid

from utils import *

# setup simple logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class KokoRoutes:
  def ping_cmd(self, sock: socket.socket, msg: str = ''):
    """SOCKET COMMAND
    ping command"""
    return {"pong": msg}

  def register_client(self, sock: socket.socket, username: str, email: str, password: str):
    """SOCKET ROUTE -- RGST -- Register a user"""

    # todo: validate username, email, password (length, etc.) on server side too.

    # check if the user exists
    resp = self.execute("""SELECT id FROM users WHERE username=? OR email=?;""", args=(username, email),
                        fetchone=True)

    if resp is not None:
      return {"error": "User / Email already in use"}

    # hash the password (sha256)
    m = hashlib.sha256(password.encode() + b"kitkat" + username.encode())  # add a salt
    hashed_password = m.hexdigest()

    # insert the user
    self.execute("""INSERT INTO users (username, email, password) VALUES (?, ?, ?);""",
                 args=(username, email, hashed_password))

    # create an auth token (random uuid)
    auth = str(uuid.uuid4())

    self.auths[auth] = username

    return {"auth": auth}

  def logout_client(self, sock, auth):
    """SOCKET ROUTE -- LOUT -- Logout a user"""

    if auth in self.auths:
      del self.auths[auth]

    return {"status": "ok"}  # we return ok either way

  def login_client(self, sock, username: str, password: str):
    """SOCKET ROUTE -- LOGN -- Login a user"""

    # check if credentials are correct

    # hash the password (sha256)
    m = hashlib.sha256(password.encode() + b"kitkat" + username.encode())  # add a salt
    hashed_password = m.hexdigest()

    resp = self.execute("""SELECT email FROM users WHERE username=? AND password=?;""",
                        args=(username, hashed_password), fetchone=True)

    if resp is None:
      return {"error": "Invalid username or password"}

    # check if the user is already logged in
    if username in self.auths.values():
      return {"auth": next(k for k, v in self.auths.items() if v == username), "email": resp[0]}

    # create an auth token (random uuid)
    auth = str(uuid.uuid4())
    self.auths[auth] = username

    return {"auth": auth, "email": resp[0]}

  def send_mail_list(self, sock, auth):
    """SOCKET ROUTE -- MLIST -- Send the list of emails to the user"""

    if auth not in self.auths:
      return {"error": "Invalid auth token"}

    username = self.auths[auth]

    # get the user id
    user_id = self.execute("""SELECT id FROM users WHERE username=?;""", args=(username,), fetchone=True)[0]

    # get the list of emails
    emails = self.execute("""
    SELECT mails.id, mails.subject, mails.body, users.username AS sender, mails.recipient, mails.timestamp, mails.files, mails.read
    FROM mails
    JOIN users ON users.id = mails.sender
    WHERE mails.recipient = ?;
    """,
                          args=(user_id,), fetchall=True)

    retmails = {
      m[0]: dict(zip(('id', 'subject', 'body', 'sender', 'recipient', 'timestamp', 'attachments', 'read'), m))
      for m in emails
    }

    # get spam, star
    spam = self.execute("""SELECT mail_id FROM spam WHERE user_id=?;""", args=(user_id,), fetchall=True)
    star = self.execute("""SELECT mail_id FROM star WHERE user_id=?;""", args=(user_id,), fetchall=True)

    for s in spam: retmails[s[0]]['spam'] = True
    for s in star: retmails[s[0]]['star'] = True

    return {"mails": list(retmails.values())}

  def send_mail_sent_list(self, sock, auth):
    """SOCKET ROUTE -- MSNT -- Send the list of emails that the user **sent**"""

    if auth not in self.auths:
      return {"error": "Invalid auth token"}

    username = self.auths[auth]

    # get the user id
    user_id = self.execute("""SELECT id FROM users WHERE username=?;""", args=(username,), fetchone=True)[0]

    # get the list of emails
    emails = self.execute("""
    SELECT mails.id, mails.subject, mails.body, users.username AS sender, mails.recipient, mails.timestamp, mails.files
    FROM mails
    JOIN users ON users.id = mails.sender
    WHERE mails.sender = ?;
    """,
                          args=(user_id,), fetchall=True)

    retmails = {
      m[0]: dict(zip(('id', 'subject', 'body', 'sender', 'recipient', 'timestamp', 'attachments'), m))
      for m in emails
    }

    return {"mails": list(retmails.values())}

  def get_mail(self, sock, auth, id):
    """SOCKET ROUTE -- GETMAIL -- Get a specific email"""

    if auth not in self.auths:
      return {"error": "Invalid auth token"}

    username = self.auths[auth]

    # get the user id
    user_id = self.execute("""SELECT id FROM users WHERE username=?;""", args=(username,), fetchone=True)[0]

    mail = self.execute("""
        SELECT mails.id, mails.subject, mails.body, users.username AS sender, mails.recipient, mails.timestamp, mails.files
        FROM mails
        JOIN users ON users.id = mails.sender
        WHERE mails.id=? AND (mails.recipient = ? OR mails.sender = ?);
        """, args=(int(id), user_id, user_id), fetchone=True)


    self.execute("""UPDATE mails SET read=1 WHERE id=? AND recipient=?;""", args=(int(id), user_id))  # mark mail as read

    return dict(zip(('id', 'subject', 'body', 'sender', 'recipient', 'timestamp', 'attachments'), mail))

  def create_mail(self, sock, auth, to, subject, body):
    """SOCKET ROUTE -- SEND -- Create a email"""
    if auth not in self.auths:
      return {"error": "Invalid auth token"}

    username = self.auths[auth]

    # get the user id
    user_id = self.execute("""SELECT id FROM users WHERE username=?;""", args=(username,), fetchone=True)[0]

    # get the recipient id
    print(f'checking if {to} exists')
    recipient_id = self.execute("""SELECT id FROM users WHERE email=? OR username=?;""", args=(to, to),
                                fetchone=True)
    print(recipient_id)

    if recipient_id is None:
      return {"error": "Invalid recipient email"}

    recipient_id = recipient_id[0]

    # create the mail
    id = self.execute("""INSERT INTO mails (sender, recipient, subject, body) VALUES (?, ?, ?, ?);""",
                      args=(user_id, recipient_id, subject, body), getid=True)

    return {"id": id}

  def create_file(self, sock, data):
    """SOCKET ROUTE -- FILE -- Create a file"""

    # check if auth is valid
    auth = data[:36].decode()

    print('===================')
    print(auth)
    print(f'VS: {self.auths}')
    print('===================')

    if auth not in self.auths:
      return {"error": "Invalid auth token"}

    username = self.auths[auth]

    # get the user id
    user_id = self.execute("""SELECT id FROM users WHERE username=?;""", args=(username,), fetchone=True)[0]

    # get mail id
    id = self.execute("""SELECT id FROM mails WHERE sender=? ORDER BY id DESC LIMIT 1""", args=(user_id,),
                      fetchone=True)

    if id is None:
      return {"error": "No previous mail found"}

    id = id[0]

    fn = data[36:36 + 200].decode()

    print(fn)
    fn = os.path.basename(fn)
    filename = f'I{id}K{random.randint(100000, 999999)}' + fn.strip()

    # get the file data
    filedata = data[36 + 200:]

    if not os.path.exists('./files'):
      os.mkdir('./files')

    with open(os.path.join('./files', filename), 'wb') as f:
      f.write(filedata)

    # create the file
    self.execute("""UPDATE mails SET files = files || ? WHERE id=?""", args=(filename + ',', id))

    return {"status": "ok", "id": id}

  def get_file(self, sock, auth, id, filename):
    """SOCKET ROUTE -- GFLE -- Get a file (send the user for download)"""
    # check if auth is valid
    if auth not in self.auths:
      return {"error": "Invalid auth token"}

    username = self.auths[auth]

    # get the user id
    user_id = self.execute("""SELECT id FROM users WHERE username=?;""", args=(username,), fetchone=True)[0]

    # get mail id
    id = self.execute("""SELECT id FROM mails WHERE recipient=? AND id=?""", args=(user_id, id),
                      fetchone=True)

    if id is None:
      return {"error": "No mail found"}

    id = id[0]

    if not filename.startswith(f'I{id}K'):
      return {"error": "You don't have access to this file"}

    with open(os.path.join('files', filename), 'rb') as f:
      filedata = f.read()

    return filedata

  def mark_as_spam(self, sock, auth, id):
    """SOCKET ROUTE -- SPAM -- Mark a mail as spam"""
    # check if auth is valid
    if auth not in self.auths:
      return {"error": "Invalid auth token"}

    username = self.auths[auth]

    # get the user id
    user_id = self.execute("""SELECT id FROM users WHERE username=?;""", args=(username,), fetchone=True)[0]

    # check if already spam
    spam = self.execute("""SELECT mail_id FROM spam WHERE mail_id=? AND user_id=?""", args=(id, user_id), fetchone=True)

    # toggle the spam
    if spam is not None:
      # remove from spam
      self.execute("""DELETE FROM spam WHERE mail_id=? AND user_id=?""", args=(id, user_id))
    else:
      # mark as spam
      self.execute("""INSERT INTO spam (mail_id, user_id) VALUES (?, ?);""", args=(id, user_id))

    return {"status": "ok", "set": spam is None}

  def mark_as_important(self, sock, auth, id):
    """SOCKET ROUTE -- IMPT -- Mark a mail as important (star)"""
    # check if auth is valid
    if auth not in self.auths:
      return {"error": "Invalid auth token"}

    username = self.auths[auth]

    # get the user id
    user_id = self.execute("""SELECT id FROM users WHERE username=?;""", args=(username,), fetchone=True)[0]

    # check if already star
    star = self.execute("""SELECT mail_id FROM star WHERE mail_id=? AND user_id=?""", args=(id, user_id), fetchone=True)

    # toggle the star
    if star is not None:
      # remove from star
      self.execute("""DELETE FROM star WHERE mail_id=? AND user_id=?""", args=(id, user_id))
    else:
      # mark as star
      self.execute("""INSERT INTO star (mail_id, user_id) VALUES (?, ?);""", args=(id, user_id))

    return {"status": "ok", "set": star is None}


class KokoServer(KokoRoutes):
  """
  The server class handles and all the clients connected to it.
  """

  def __init__(self):
    self.server_sock = None
    self.client_socks = []

    self.kill_threads = False

    self.SERVER_ROUTES = {
      "PING": self.ping_cmd,
      "RGST": self.register_client,
      "LOGN": self.login_client,
      "LOUT": self.logout_client,
      "MLST": self.send_mail_list,
      "SEND": self.create_mail,
      "FILE": self.create_file,
      "MAIL": self.get_mail,
      "GFLE": self.get_file,
      "SPAM": self.mark_as_spam,
      "IMPT": self.mark_as_important,
      "MSNT": self.send_mail_sent_list,
    }

    self.conn = sqlite3.connect('koko.db', isolation_level=None, check_same_thread=False)
    self.auths = {}

  def execute(self, command, args=None, fetchall=False, fetchone=False, getid=False):
    """Executes a command."""
    cur = self.conn.cursor()

    cur.execute(command, args)

    resp = cur.fetchall() if fetchall else cur.fetchone() if fetchone else None

    if getid:
      resp = cur.lastrowid

    cur.close()

    return resp

  def run(self):
    """
    The main function of the server.
    It handles new clients and creates a thread for each one.
    """

    # create socket and bind to port
    self.server_sock = socket.socket()
    self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allow reuse of address:
    # If killing the server then starting it again works without
    # waiting for the port to be released

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain('new.pem', 'private.key')

    self.server_sock = ctx.wrap_socket(self.server_sock, server_side=True)

    try:
      self.server_sock.bind((SERVER_IP, SERVER_PORT))  # bind to port and ip from config file
    except OSError:
      print('Port is perhaps unavailable')
      # print traceback
      logging.error(traceback.format_exc())
      return

    self.server_sock.listen(20)  # it basically means that at the same bit of a second we can read 20 clients.
    # it's not really a big deal for a small application like this.
    # NOTE: this is not the maximum number of clients that can connect to the server.

    threads = []
    client_id = 1

    while True:
      logging.info('[Main] Waiting for clients...')

      cli_sock, addr = self.server_sock.accept()  # ready accept a new client (BLOCKING)

      # create a thread for the new client
      t = threading.Thread(target=self.handle_client, args=(cli_sock, str(client_id), addr))
      t.start()
      threads.append(t)
      self.client_socks.append(cli_sock)

      client_id += 1

      # We can decide to kill the server by a certain condition.
      # This does not wait for the clients to disconnect (normally),
      # it just forces them to after they are done with the current job.
      if client_id > 100000000:  # for tests change it to 4
        logging.warning('[Main] Going down for maintenance')
        break

    socket.shutdown(socket.SHUT_WR)  # shutdown the socket (no reads or writes)
    self.kill_threads = True  # tell the threads to break their loops to close the socket

    logging.info('[Main] waiting to all clients to die')

    for t in threads:
      t.join()

    self.server_sock.close()  # close the server socket
    print('Bye ..')

  def logtcp(self, dir, tid, byte_data):
    """log direction, tid and all TCP byte array data"""
    if dir == 'sent':
      logging.info(f'{tid} S LOG:Sent\t>>>\t{byte_data}')
    else:
      logging.info(f'{tid} S LOG:Recieved\t<<<\t{byte_data}')

  def send_error(self, sock, tid, err, errmsg=None):
    """
    Send error message to client
    """
    msg = f's{MessageType.ERROR}EROR' + jsoon.dumps({
      "error_code": err.eid if hasattr(err, "eid") else GeneralError.eid,
      "error": errmsg or str(err)
    })

    length_header = length_header_send(msg)

    with contextlib.suppress(ConnectionError):
      sock.sendall(length_header + msg.encode())
      self.logtcp('sent', tid, msg)

  def handle_client_message(self, sock, mdata, tid):
    """
    Do something with the client message. The message is already parsed.
    This function understands the message, does something with it and sends a response.
    """

    route = mdata['route']

    # unknown command
    if route not in self.SERVER_ROUTES: raise BadMessageError(f'Unknown route {route}')

    # possible items in mdata:
    mtype = mdata['type']
    mdata = mdata['data']  # data (raw/json)

    def try_func(**kw):
      # call function with arguments
      try:
        fun = self.SERVER_ROUTES[route]
        return fun(sock=sock, **kw)
      except ResponseGenerateError as e:
        return send_error(sock, tid, e.eid)

    if mtype == MessageType.ERROR:
      # client sent an error
      logging.info(f'Client sent error: {mdata=}')
      return route

    elif mtype == MessageType.RAW:
      resp = try_func(data=mdata)

    elif mtype == MessageType.JSON:
      if isinstance(mdata, list):
        resp = try_func(data=mdata)
      else:  # dict
        resp = try_func(**mdata)

    else:  # unstructured data, not supported.
      raise BadMessageError(f'Invalid message type')

    print('#' * 20)
    print(f'server is sending the client a message back:')
    print(resp)
    print('#' * 20)

    # get type
    if isinstance(resp, (dict, list)):
      otype = MessageType.JSON
      resp = jsoon.dumps(resp).encode()
    else:
      otype = MessageType.RAW

    resp = f's{otype}{route}'.encode() + resp

    # get data length header
    length_header = length_header_send(resp)

    # send
    sock.sendall(length_header + resp)
    self.logtcp('sent', tid, f'{route} {len(resp)} bytes')

    return route

  def handle_client(self, sock: socket.socket, tid, addr):
    """
    A thread dedicated for a single client.
    It is responsible for handling the client's requests.

    :param sock: The client's socket
    :param tid: The thread/client id
    :param addr: The client's address
    """
    logging.info(f'[+] Client {tid} connected from {addr}')

    while True:  # loop until client disconnects or sends EXIT command, or when a critical error occurs

      if self.kill_threads:  # if the server is shutting down, kill this thread
        logging.warning(f'Killing {tid}')
        break

      try:
        # wait for the client to send a message (BLOCKING)
        # this function follows the protocol rules and does not
        # give up until all the message is received.
        msg = fetch_all(sock)

        self.logtcp('recieved', tid, msg)

        mdata = parse_message_by_protocol(msg)  # parse the message by the protocol rules into a dict
        print('PARSED:', mdata)

        # handle the message, meaning that depending on the route, the server will do something
        # and send a response to the client. An error might occur, and it will be handled here (catch).
        cmd = self.handle_client_message(sock, mdata, tid)

        # client wants to go, bye bye
        if cmd == 'EXIT': break

      except OkCheck:  # client sent OK to validate the connection, send OK back.
        sock.send('OK'.encode())
        continue
      except DisconnectedError as e:
        logging.error(f'Client {tid} disconnected during recv()')
        self.send_error(sock, tid, e, 'Disconnected')
        break
      except BadMessageError as e:
        logging.error(f'Client {tid} sent bad message ({e})')
        self.send_error(sock, tid, e)
      except socket.error as err:
        logging.error(f'Socket Error exit client loop: err:  {err}')
        self.send_error(sock, tid, err, 'Socket Error')
        break
      except Exception as err:
        logging.error(f'General Error %s exit client loop: {err}')
        logging.error(traceback.format_exc())
        self.send_error(sock, tid, err, 'General Error')
        break

    logging.info(f'Client {tid} Exit')
    sock.close()


if __name__ == '__main__':
  KokoServer().run()
