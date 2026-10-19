"""Create local-only demo accounts for trying the Living Lens interface."""
import os
import server

DEMO_USERS = [
    ('admin', 'Demo Administrator', 'demo.admin@livinglens.local', 'LensAdmin-2026!', 'Demo Zoo'),
    ('zookeeper', 'Demo Zookeeper', 'demo.keeper@livinglens.local', 'LensKeeper-2026!', 'Demo Zoo'),
    ('citizen', 'Demo Citizen', 'demo.citizen@livinglens.local', 'LensCitizen-2026!', 'Demo Zoo'),
]

if not os.environ.get('LIVING_LENS_SECRET'):
    raise SystemExit('Set LIVING_LENS_SECRET before running the demo seeder.')
server.initialize()
with server.db() as con:
    for role, name, email, password, zoo in DEMO_USERS:
        exists = con.execute('SELECT 1 FROM users WHERE email=?', (email,)).fetchone()
        if not exists:
            con.execute('INSERT INTO users(name,email,password_hash,role,zoo) VALUES(?,?,?,?,?)',
                        (name, email, server.pw_hash(password), role, zoo))
            print(f'Created {role}: {email}')
        else:
            print(f'Already exists {role}: {email}')
