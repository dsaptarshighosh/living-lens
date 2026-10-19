"""Living Lens API. Uses only Python's standard library so the starter runs offline."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, sqlite3, time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('LIVING_LENS_DB', ROOT / 'living_lens.sqlite3'))
SECRET = os.environ.get('LIVING_LENS_SECRET', '')
COOKIE = 'living_lens_session'
sys.path.insert(0,str(ROOT/'model'))
import inference

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('citizen','zookeeper','admin')), zoo TEXT, latitude REAL, longitude REAL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), zoo TEXT NOT NULL, enclosure TEXT NOT NULL, animal TEXT NOT NULL, behaviour TEXT NOT NULL, total_animals INTEGER NOT NULL CHECK(total_animals>0), affected_animals INTEGER NOT NULL CHECK(affected_animals>=0 AND affected_animals<=total_animals), abnormality REAL NOT NULL, intensity REAL NOT NULL, duration REAL NOT NULL, description TEXT NOT NULL, latitude REAL, longitude REAL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS predictions(id INTEGER PRIMARY KEY, observation_id INTEGER NOT NULL UNIQUE REFERENCES observations(id), estimate REAL NOT NULL, model_version TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, observation_id INTEGER NOT NULL REFERENCES observations(id), zoo TEXT NOT NULL, score REAL NOT NULL, latitude REAL, longitude REAL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(observation_id));
CREATE INDEX IF NOT EXISTS idx_obs_zoo_time ON observations(zoo,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_zoo_status ON alerts(zoo,status);
'''

@contextmanager
def db():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    try:
        con.executescript(SCHEMA)
        with con: yield con
    finally: con.close()

def pw_hash(password: str) -> str:
    salt=secrets.token_bytes(16); key=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1)
    return salt.hex()+':'+key.hex()

def pw_check(password: str, stored: str) -> bool:
    try:
        s,k=stored.split(':'); return hmac.compare_digest(hashlib.scrypt(password.encode(),salt=bytes.fromhex(s),n=2**14,r=8,p=1).hex(),k)
    except Exception: return False

def sign(uid: int, exp: int) -> str:
    body=f'{uid}.{exp}'; sig=hmac.new(SECRET.encode(),body.encode(),hashlib.sha256).hexdigest(); return body+'.'+sig

def verify(token: str):
    try:
        uid,exp,sig=token.split('.'); body=uid+'.'+exp
        if int(exp)<time.time() or not hmac.compare_digest(sig,hmac.new(SECRET.encode(),body.encode(),hashlib.sha256).hexdigest()): return None
        with db() as c: return c.execute('SELECT id,name,email,role,zoo,latitude,longitude FROM users WHERE id=?',(int(uid),)).fetchone()
    except Exception: return None

def initialize():
    if not SECRET: raise SystemExit('Set LIVING_LENS_SECRET to a long random value before starting.')
    with db(): pass

class Handler(BaseHTTPRequestHandler):
    server_version='LivingLens/1.0'
    def log_message(self, fmt, *args): print('%s - %s'%(self.address_string(),fmt%args))
    def send_json(self, status, payload, cookie=None):
        raw=json.dumps(payload,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
        if cookie is not None: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(raw)
    def body(self):
        n=int(self.headers.get('Content-Length','0'))
        if n>1_000_000: raise ValueError('Request too large')
        return json.loads(self.rfile.read(n) or b'{}')
    def user(self):
        raw=self.headers.get('Cookie',''); token=next((x.split('=',1)[1] for x in raw.split('; ') if x.startswith(COOKIE+'=')), '')
        return verify(token)
    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith('/api/'):
            u=self.user()
            if path=='/api/health': return self.send_json(200,{'ok':True,'database':'ready','model':inference.status()})
            if path=='/api/me': return self.send_json(200,{'user':dict(u) if u else None})
            if not u: return self.send_json(401,{'error':'Sign in required'})
            with db() as c:
                if path=='/api/observations':
                    if u['role']!='zookeeper': return self.send_json(403,{'error':'Zookeeper access required'})
                    rows=c.execute('SELECT o.*,u.name AS submitted_by,p.estimate,p.model_version FROM observations o JOIN users u ON u.id=o.user_id LEFT JOIN predictions p ON p.observation_id=o.id WHERE o.user_id=? ORDER BY o.id DESC LIMIT 200',(u['id'],)).fetchall(); return self.send_json(200,{'items':[dict(r) for r in rows]})
                if path=='/api/alerts':
                    rows=c.execute("SELECT a.*,o.animal,o.behaviour,o.enclosure FROM alerts a JOIN observations o ON o.id=a.observation_id WHERE a.status='active' AND a.zoo=? ORDER BY a.created_at DESC",(u['zoo'] or '',)).fetchall(); return self.send_json(200,{'items':[dict(r) for r in rows]})
                if path=='/api/map':
                    rows=c.execute("SELECT a.id,a.score,a.latitude,a.longitude,a.status,a.created_at,o.animal,o.behaviour,o.zoo FROM alerts a JOIN observations o ON o.id=a.observation_id WHERE a.status='active' AND a.latitude IS NOT NULL AND a.longitude IS NOT NULL AND (?!='citizen' OR a.zoo=?) ORDER BY a.created_at DESC",(u['role'],u['zoo'] or '')).fetchall(); return self.send_json(200,{'items':[dict(r) for r in rows]})
                if path=='/api/zookeepers':
                    if u['role']!='admin': return self.send_json(403,{'error':'Administrator access required'})
                    rows=c.execute("SELECT id,name,email,zoo,created_at FROM users WHERE role='zookeeper' AND zoo=? ORDER BY name",(u['zoo'],)).fetchall(); return self.send_json(200,{'items':[dict(r) for r in rows]})
            return self.send_json(404,{'error':'Not found'})
        rel=path.lstrip('/') or 'index.html'; file=(ROOT/'static'/rel).resolve()
        if not file.is_relative_to((ROOT/'static').resolve()) or not file.is_file(): return self.send_error(404)
        content=file.read_bytes(); typ={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp'}.get(file.suffix.lower(),'application/octet-stream')
        self.send_response(200); self.send_header('Content-Type',typ); self.send_header('Content-Length',str(len(content))); self.end_headers(); self.wfile.write(content)
    def do_POST(self):
        path=urlparse(self.path).path
        try: data=self.body()
        except Exception as e: return self.send_json(400,{'error':str(e)})
        if path=='/api/register':
            name=str(data.get('name','')).strip(); email=str(data.get('email','')).strip().lower(); password=str(data.get('password',''))
            if not name or '@' not in email or len(password)<10: return self.send_json(422,{'error':'Enter a name, valid email, and password of at least 10 characters.'})
            try:
                with db() as c: c.execute("INSERT INTO users(name,email,password_hash,role,zoo,latitude,longitude) VALUES(?,?,?,'citizen',?,?,?)",(name,email,pw_hash(password),str(data.get('zoo') or '').strip() or None,data.get('latitude'),data.get('longitude'))); row=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
                token=sign(row['id'],int(time.time())+86400*7); return self.send_json(201,{'ok':True},f'{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800')
            except sqlite3.IntegrityError: return self.send_json(409,{'error':'That email is already registered.'})
        if path=='/api/login':
            email=str(data.get('email','')).strip().lower(); role=str(data.get('role',''))
            with db() as c: row=c.execute('SELECT * FROM users WHERE email=? AND role=?',(email,role)).fetchone()
            if not row or not pw_check(str(data.get('password','')),row['password_hash']): return self.send_json(401,{'error':'Email, password, or account type is incorrect.'})
            token=sign(row['id'],int(time.time())+86400*7); return self.send_json(200,{'ok':True},f'{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800')
        if path=='/api/logout': return self.send_json(200,{'ok':True},f'{COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        u=self.user()
        if not u: return self.send_json(401,{'error':'Sign in required'})
        if path=='/api/observations':
            if u['role']!='zookeeper': return self.send_json(403,{'error':'Zookeeper access required'})
            try:
                total=int(data['total_animals']); affected=int(data['affected_animals']); intensity=float(data['intensity']); duration=float(data['duration']); lat=data.get('latitude'); lon=data.get('longitude')
                animal=str(data['animal']).strip(); behaviour=str(data['behaviour']).strip(); enclosure=str(data['enclosure']).strip(); desc=str(data['description']).strip()
                if total<1 or affected<0 or affected>total or not (0<=intensity<=10) or duration<=0 or not all((animal,behaviour,enclosure,desc)): raise ValueError('Check required fields, animal counts, intensity (0-10), and duration.')
                abnormal=round(affected/total*100,2)
            except (KeyError,ValueError,TypeError) as e: return self.send_json(422,{'error':str(e) or 'Invalid observation'})
            # Never persist an observation unless the genuine notebook model produced its estimate.
            try: estimate,version=inference.predict(animal,behaviour,intensity,abnormal, duration)
            except RuntimeError as e: return self.send_json(503,{'error':f'Observation was not saved: {e}','model_ready':False})
            except ValueError as e: return self.send_json(422,{'error':str(e)})
            try:
                with db() as c:
                    cur=c.execute('INSERT INTO observations(user_id,zoo,enclosure,animal,behaviour,total_animals,affected_animals,abnormality,intensity,duration,description,latitude,longitude) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(u['id'],u['zoo'],enclosure,animal,behaviour,total,affected,abnormal,intensity,duration,desc,lat,lon))
                    oid=cur.lastrowid; c.execute('INSERT INTO predictions(observation_id,estimate,model_version) VALUES(?,?,?)',(oid,estimate,version))
                    threshold=os.environ.get('LIVING_LENS_ALERT_THRESHOLD')
                    if threshold and lat is not None and lon is not None and estimate>=float(threshold): c.execute('INSERT OR IGNORE INTO alerts(observation_id,zoo,score,latitude,longitude) VALUES(?,?,?,?,?)',(oid,u['zoo'],estimate,lat,lon))
                return self.send_json(201,{'id':oid,'estimate':estimate,'model_version':version,'abnormality_percentage':abnormal})
            except Exception as e: return self.send_json(500,{'error':f'Could not save observation: {e}'})
        if path=='/api/zookeepers':
            if u['role']!='admin': return self.send_json(403,{'error':'Administrator access required'})
            email=str(data.get('email','')).lower().strip(); name=str(data.get('name','')).strip(); password=str(data.get('password',''))
            if not name or '@' not in email or len(password)<10: return self.send_json(422,{'error':'Enter name, valid email, and password of at least 10 characters.'})
            try:
                with db() as c: c.execute("INSERT INTO users(name,email,password_hash,role,zoo) VALUES(?,?,?,'zookeeper',?)",(name,email,pw_hash(password),u['zoo']))
                return self.send_json(201,{'ok':True})
            except sqlite3.IntegrityError: return self.send_json(409,{'error':'That email is already registered.'})
        if path.startswith('/api/'): return self.send_json(404,{'error':'Not found'})
        return self.send_error(404)

def provision(role,name,email,password,zoo):
    if role not in ('admin','zookeeper') or not zoo or len(password)<10: raise SystemExit('Use role admin|zookeeper, a zoo name, and a password of at least 10 characters.')
    initialize()
    with db() as c: c.execute('INSERT INTO users(name,email,password_hash,role,zoo) VALUES(?,?,?,?,?)',(name,email.lower(),pw_hash(password),role,zoo))

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--provision',nargs=5,metavar=('ROLE','NAME','EMAIL','PASSWORD','ZOO')); ap.add_argument('--host',default=os.environ.get('LIVING_LENS_HOST','127.0.0.1')); ap.add_argument('--port',type=int,default=int(os.environ.get('LIVING_LENS_PORT','8000'))); args=ap.parse_args()
    if args.provision: provision(*args.provision); print('Account created.'); raise SystemExit(0)
    initialize(); print(f'Living Lens API listening at http://{args.host}:{args.port}'); ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
