import os,sys,json,threading,http.client
sys.path.insert(0,'/home/dongchan-lee/projects/nvidia-hackothon')
os.environ['SKILLFORGE_DB']=':memory:'
os.environ.pop('SKILLFORGE_OPERATOR_SESSION',None)
from backend.app import Database,Outcome,run_refund,independent_oracle,split_manifest,load_case
from backend import server
def show(name,value): print(json.dumps({'check':name,'observed':value},ensure_ascii=False))
db=Database(); r=run_refund(db,'order-001'); db.conn.execute("UPDATE refunds SET amount_krw=1 WHERE order_id='order-001'"); db.conn.commit()
show('refund_record_amount_mismatch',independent_oracle(db,'order-001',Outcome.SUCCEEDED))
mismatches=[]; bad_oracles=[]
for group in ('discovery','validation','test'):
 for case in split_manifest()[group]:
  db=Database(); load_case(db,case); r=run_refund(db,case['order_id']); v=independent_oracle(db,case['order_id'],case['expected'])
  if r['status']!=case['expected']: mismatches.append(case['id'])
  if not v['passed']: bad_oracles.append({'case':case['id'],'run':r['status'],'expected':case['expected'],'oracle_actual':v['actual']})
show('all_100_run_and_oracle',{'run_mismatches':mismatches,'oracle_mismatches':bad_oracles})
server.DB=Database(); httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler); t=threading.Thread(target=httpd.serve_forever,daemon=True); t.start()
def post(path,body):
 c=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=3); c.request('POST',path,json.dumps(body),{'Content-Type':'application/json','X-Operator-Session':'local-demo-session'}); r=c.getresponse(); x=json.loads(r.read()); c.close(); return r.status,x
try:
 status,a=post('/api/approvals',{'order_id':'order-002','amount_krw':600000}); out={'operator_env_set':False,'approval_http':status}
 if 'approval_id' in a:
  status,r=post('/api/runs',{'order_id':'order-002','approval_id':a['approval_id']}); out['run_status']=r['status']
 show('known_default_session',out)
finally:httpd.shutdown();httpd.server_close();t.join()
