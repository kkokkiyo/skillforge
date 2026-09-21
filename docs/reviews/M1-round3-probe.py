import os,sys,json,threading,http.client
sys.path.insert(0,'/home/dongchan-lee/projects/nvidia-hackothon')
os.environ['SKILLFORGE_DB']=':memory:'
from backend.app import Database,Gateway,Trace,Outcome,independent_oracle,load_case,run_refund,split_manifest
from backend import server
def show(k,v):print(json.dumps({'check':k,'observed':v},ensure_ascii=False))
mismatches=[]; oracle_false_pass=[]; counts={}
for split in ('discovery','validation','test'):
    for case in split_manifest()[split]:
        db=Database(); load_case(db,case); r=run_refund(db,case['order_id']); verdict=independent_oracle(db,case['order_id'],case['expected']); counts[r['status']]=counts.get(r['status'],0)+1
        if r['status']!=case['expected']:
            mismatches.append({'case':case['id'],'expected':case['expected'],'actual':r['status'],'reason':r.get('reason_code')})
            if verdict['passed']:oracle_false_pass.append(case['id'])
show('all_100_cases',{'counts':counts,'mismatches':mismatches,'oracle_false_pass':oracle_false_pass})
db=Database(); db.conn.execute("UPDATE orders SET refunded_krw=600000 WHERE id='order-002'"); db.conn.execute("INSERT INTO refunds VALUES ('unauthorized','order-002','fake','fake',1,'COMMITTED')"); db.conn.commit()
show('oracle_unauthorized_wrong_amount',independent_oracle(db,'order-002',Outcome.SUCCEEDED))
db=Database(); g=Gateway(db,Trace(db,'missing','mock','order-001'))
try:g.call('get_order',{})
except Exception as e:show('missing_required_arg',{'exception':type(e).__name__,'reason':getattr(e,'code',None)})

server.DB=Database(); h=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler); th=threading.Thread(target=h.serve_forever,daemon=True); th.start()
def post(path,body,headers=None):
    c=http.client.HTTPConnection('127.0.0.1',h.server_port,timeout=4); c.request('POST',path,json.dumps(body),{'Content-Type':'application/json',**(headers or {})}); r=c.getresponse(); data=json.loads(r.read()); c.close(); return r.status,data
try:
    status,a=post('/api/approvals',{'order_id':'order-002','amount_krw':600000},{'X-Operator-Id':'arbitrary-unregistered-review-user'})
    out={'approval_http':status}
    if 'approval_id' in a:
        status,r=post('/api/runs',{'order_id':'order-002','approval_id':a['approval_id']},{'X-Operator-Id':'arbitrary-unregistered-review-user'})
        out.update({'run_http':status,'run_status':r['status'],'refunds':server.DB.one('SELECT COUNT(*) FROM refunds')[0]})
    show('unregistered_header_self_approval',out)
finally:h.shutdown();h.server_close();th.join()
