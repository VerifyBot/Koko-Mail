import sqlite3

conn = sqlite3.connect('koko.db', isolation_level=None)

cur =  conn.cursor()



SETUP = dict(
  users = False,
  mails = True,
  spam = True,
  star = True
)
if SETUP["users"]:
  cur.execute("""DROP TABLE IF EXISTS users;""")
  cur.execute("""
  CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    password TEXT NOT NULL
  );
  """)

if SETUP["mails"]:
  # comma separated list of file ids

  cur.execute("""DROP TABLE IF EXISTS mails;""")
  cur.execute("""
  CREATE TABLE mails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender INTEGER NOT NULL,
    recipient INTEGER NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    files TEXT DEFAULT ',',
    read INTEGER DEFAULT 0
  );
  """)

if SETUP['spam']:
  cur.execute("""DROP TABLE IF EXISTS spam;""")
  # mail_id --> the mail that was marked as spam
  # user_id --> the user that marked the mail as spam
  cur.execute("""
  CREATE TABLE spam (
    mail_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL
  );
  """)

if SETUP['star']:
  cur.execute("""DROP TABLE IF EXISTS star;""")
  cur.execute("""
    CREATE TABLE star (
      mail_id INTEGER NOT NULL, 
      user_id INTEGER NOT NULL
    );
    """)

cur.close()
conn.close()
