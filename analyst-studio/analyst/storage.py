import json
import sqlite3
import time
import uuid
from pathlib import Path


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'history.sqlite3'
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, title TEXT, updated REAL, messages TEXT);
            CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, value TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS events(session TEXT, at REAL, kind TEXT, payload TEXT);
            ''')

    def connect(self):
        return sqlite3.connect(self.db, timeout=10)

    def new(self):
        sid = uuid.uuid4().hex
        self.save(sid, 'New analysis', [])
        return sid

    def workspace(self, sid):
        if len(sid) != 32 or any(c not in '0123456789abcdef' for c in sid):
            raise ValueError('Invalid session ID')
        path = self.root / 'sessions' / sid
        for name in ('data', 'outputs'):
            (path / name).mkdir(parents=True, exist_ok=True)
        return path

    def save(self, sid, title, messages):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?,?)',
                      (sid, title[:100], time.time(), json.dumps(messages)))

    def load(self, sid):
        with self.connect() as c:
            row = c.execute('SELECT messages FROM sessions WHERE id=?', (sid,)).fetchone()
        return json.loads(row[0]) if row else []

    def sessions(self):
        with self.connect() as c:
            return c.execute('SELECT id,title FROM sessions ORDER BY updated DESC').fetchall()

    def event(self, sid, kind, payload):
        with self.connect() as c:
            c.execute('INSERT INTO events VALUES(?,?,?,?)',
                      (sid, time.time(), kind, json.dumps(payload, default=str)))

    def events(self, sid):
        with self.connect() as c:
            return [dict(at=t, kind=k, payload=json.loads(p)) for t,k,p in c.execute(
                'SELECT at,kind,payload FROM events WHERE session=? ORDER BY at', (sid,))]

    def cached(self, key):
        with self.connect() as c:
            row = c.execute('SELECT value FROM cache WHERE key=? AND expires>?', (key,time.time())).fetchone()
        return json.loads(row[0]) if row else None

    def cache(self, key, value, ttl=3600):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)', (key,json.dumps(value),time.time()+ttl))
