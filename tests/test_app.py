"""Offline tests for storage and authentication primitives (no network socket required)."""
import os, sys, tempfile, unittest
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEMP=tempfile.TemporaryDirectory(dir=ROOT.parents[1]/'work')
os.environ['LIVING_LENS_SECRET']='test-secret-'+'x'*40
os.environ['LIVING_LENS_DB']=str(Path(TEMP.name)/'test.sqlite3')
sys.path.insert(0,str(ROOT))
import server

class BackendCoreTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        TEMP.cleanup()

    def setUp(self):
        server.initialize()

    def test_password_hashing_and_wrong_password(self):
        hashed=server.pw_hash('correct horse battery staple')
        self.assertNotEqual(hashed,'correct horse battery staple')
        self.assertTrue(server.pw_check('correct horse battery staple',hashed))
        self.assertFalse(server.pw_check('wrong password',hashed))

    def test_observation_and_prediction_persist_separately(self):
        with server.db() as c:
            c.execute("INSERT INTO users(name,email,password_hash,role,zoo) VALUES('Keeper','k@example.test','x','zookeeper','Zoo A')")
            uid=c.execute('SELECT id FROM users WHERE email=?',('k@example.test',)).fetchone()['id']
            cur=c.execute("INSERT INTO observations(user_id,zoo,enclosure,animal,behaviour,total_animals,affected_animals,abnormality,intensity,duration,description) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(uid,'Zoo A','Habitat 1','Elephant','pacing',4,2,50,5,10,'Observed pacing'))
            oid=cur.lastrowid
            c.execute("INSERT INTO predictions(observation_id,estimate,model_version) VALUES(?,?,?)",(oid,37.5,'fixture-test'))
        with server.db() as c:
            row=c.execute('SELECT o.abnormality,p.estimate,p.model_version FROM observations o JOIN predictions p ON p.observation_id=o.id WHERE o.id=?',(oid,)).fetchone()
            self.assertEqual((row['abnormality'],row['estimate'],row['model_version']),(50,37.5,'fixture-test'))

    def test_zoo_filter_and_count_constraints(self):
        with server.db() as c:
            for zoo,email in [('Zoo A','a@example.test'),('Zoo B','b@example.test')]:
                c.execute('INSERT INTO users(name,email,password_hash,role,zoo) VALUES(?,?,?,?,?)',(email,email,'x','zookeeper',zoo))
            rows=c.execute("SELECT zoo FROM users WHERE email IN ('a@example.test','b@example.test') AND role=? AND zoo=?",('zookeeper','Zoo A')).fetchall()
            self.assertEqual([r['zoo'] for r in rows],['Zoo A'])
            uid=c.execute('SELECT id FROM users WHERE email=?',('a@example.test',)).fetchone()['id']
            with self.assertRaises(Exception):
                c.execute("INSERT INTO observations(user_id,zoo,enclosure,animal,behaviour,total_animals,affected_animals,abnormality,intensity,duration,description) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(uid,'Zoo A','Habitat','Elephant','pacing',2,3,150,5,10,'Invalid affected count'))

    def test_observation_history_is_private_to_submitting_zookeeper(self):
        with server.db() as c:
            keeper_ids=[]
            for name,email in [('Keeper One','keeper-one@example.test'),('Keeper Two','keeper-two@example.test')]:
                c.execute('INSERT INTO users(name,email,password_hash,role,zoo) VALUES(?,?,?,\'zookeeper\',?)',(name,email,'x','Shared Zoo'))
                keeper_ids.append(c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()['id'])
            c.execute("INSERT INTO users(name,email,password_hash,role,zoo) VALUES('Admin','admin-observations@example.test','x','admin','Shared Zoo')")
            admin_id=c.execute('SELECT id FROM users WHERE email=?',('admin-observations@example.test',)).fetchone()['id']
            for keeper_id,animal in zip(keeper_ids,['Elephant','Giraffe']):
                c.execute('INSERT INTO observations(user_id,zoo,enclosure,animal,behaviour,total_animals,affected_animals,abnormality,intensity,duration,description) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(keeper_id,'Shared Zoo','Habitat',animal,'pacing',2,1,50,5,10,'Test observation'))

        def get_observations(user):
            handler=object.__new__(server.Handler)
            handler.path='/api/observations'
            handler.user=lambda:user
            response={}
            handler.send_json=lambda status,payload,cookie=None:response.update(status=status,payload=payload)
            handler.do_GET()
            return response

        keeper_response=get_observations({'id':keeper_ids[0],'role':'zookeeper','zoo':'Shared Zoo'})
        self.assertEqual(keeper_response['status'],200)
        self.assertEqual([item['animal'] for item in keeper_response['payload']['items']],['Elephant'])
        admin_response=get_observations({'id':admin_id,'role':'admin','zoo':'Shared Zoo'})
        self.assertEqual(admin_response['status'],403)
        self.assertEqual(admin_response['payload']['error'],'Zookeeper access required')

    def test_uploaded_dataset_model_is_ready_and_predicts(self):
        state=server.inference.status()
        self.assertTrue(state['ready'],state['reason'])
        self.assertEqual(state['target'],'Hazard_Probability')
        self.assertTrue(state['animal_names'])
        self.assertTrue(state['behaviours'])
        estimate,version=server.inference.predict(state['animal_names'][0],state['behaviours'][0],5,50,10)
        self.assertTrue(math.isfinite(estimate))
        self.assertEqual(version,'notebook-random-forest-200')

    def test_zookeeper_observation_api_saves_real_model_prediction(self):
        state=server.inference.status()
        with server.db() as c:
            c.execute("INSERT INTO users(name,email,password_hash,role,zoo) VALUES('Model Keeper','model-keeper@example.test','x','zookeeper','Model Zoo')")
            uid=c.execute('SELECT id FROM users WHERE email=?',('model-keeper@example.test',)).fetchone()['id']
        payload={
            'animal':state['animal_names'][0],
            'behaviour':state['behaviours'][0],
            'total_animals':10,
            'affected_animals':5,
            'intensity':5,
            'duration':10,
            'enclosure':'Habitat 1',
            'description':'Observed test behaviour',
        }
        handler=object.__new__(server.Handler)
        handler.path='/api/observations'
        handler.user=lambda:{'id':uid,'role':'zookeeper','zoo':'Model Zoo'}
        handler.body=lambda:payload
        response={}
        handler.send_json=lambda status,data,cookie=None:response.update(status=status,payload=data)
        handler.do_POST()
        self.assertEqual(response['status'],201,response)
        self.assertTrue(math.isfinite(response['payload']['estimate']))
        with server.db() as c:
            row=c.execute('SELECT o.user_id,o.abnormality,p.estimate,p.model_version FROM observations o JOIN predictions p ON p.observation_id=o.id WHERE o.id=?',(response['payload']['id'],)).fetchone()
            self.assertEqual((row['user_id'],row['abnormality'],row['model_version']),(uid,50.0,'notebook-random-forest-200'))
            self.assertAlmostEqual(row['estimate'],response['payload']['estimate'])

if __name__=='__main__': unittest.main(verbosity=2)
