import sys, os, json, threading, http.client
sys.path.insert(0, '/home/dongchan-lee/projects/nvidia-hackothon')
os.environ['SKILLFORGE_DB'] = ':memory:'
from backend.app import Database, Trace, Gateway, Outcome, run_refund, independent_oracle, split_manifest, validate_splits
from backend import server
def show(name, value): print(json.dumps({'check':name,'observed':value},ensure_ascii=False))

db=Database(); g=Gateway(db,Trace(db,'recheck-tx','mock','order-001')); errors=[]
def other_quote():
    try: g._quote_refund({'order_id':'order-001'})
    except Exception as e: errors.append(type(e).__name__)
try:
    with db.transaction():
        db.conn.execute("UPDATE orders SET status='SHOULD_ROLL_BACK' WHERE id='order-001'")
        th=threading.Thread(target=other_quote); th.start(); th.join(2)
        raise RuntimeError('force rollback')
except RuntimeError: pass
show('quote_commits_another_transaction',{'order_status':db.one("SELECT status FROM orders WHERE id='order-001'")[0],'thread_errors':errors})

db=Database(); original=Gateway._verify_refund
def broken_verify(self,args): raise TimeoutError('injected after commit')
Gateway._verify_refund=broken_verify
try:
    try: run_refund(db,'order-001')
    except Exception as e: show('post_commit_exception',{'exception':type(e).__name__,'run':dict(db.one('SELECT status,finished_at FROM runs')),'refunds':db.one('SELECT COUNT(*) FROM refunds')[0]})
finally: Gateway._verify_refund=original

db=Database(); db.conn.execute("UPDATE orders SET refunded_krw=100 WHERE id='order-001'"); db.conn.execute("INSERT INTO refunds VALUES ('bad','order-001','bad','bad',100,'COMMITTED')"); db.conn.commit()
show('oracle_accepts_mutation_on_denied',independent_oracle(db,'order-001',Outcome.DENIED))
show('oracle_accepts_normal_as_pending',independent_oracle(Database(),'order-001',Outcome.AWAITING_APPROVAL))
m=split_manifest(); db=Database()
show('fixture_coverage',{'defined':sum(len(m[k]) for k in ('discovery','validation','test')),'present_orders':sum(db.one('SELECT 1 FROM orders WHERE id=?',(c['order_id'],)) is not None for k in ('discovery','validation','test') for c in m[k])})
m['validation'][0]['order_id']=m['discovery'][0]['order_id']; m['validation'][0]['text']=m['discovery'][0]['text']; m['validation'][0]['seed']=m['discovery'][0]['seed']
show('order_text_seed_leak_accepted',validate_splits(m))
db=Database(); r=run_refund(db,'order-001'); ev=[e for e in db.events(r['run_id']) if e['kind']=='tool.requested' and json.loads(e['payload'])['tool']=='issue_refund'][0]
show('quote_provenance',json.loads(ev['provenance']))
db=Database(); db.conn.execute('UPDATE policies SET active=0'); db.conn.execute("INSERT INTO policies VALUES ('new-policy',500000,1)"); db.conn.commit()
show('fresh_quote_after_policy_change',run_refund(db,'order-001'))

server.DB=Database(); httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler); th=threading.Thread(target=httpd.serve_forever,daemon=True); th.start()
def req(method,path,body=None):
    c=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=3); c.request(method,path,json.dumps(body) if body else None,{'Content-Type':'application/json'}); r=c.getresponse(); data=r.read(); c.close(); return r.status,json.loads(data)
try:
    show('traversal_fixed',req('GET','/../README.md'))
    show('identity_fixed',req('POST','/api/runs',{'order_id':'order-003','customer_id':'cust-002'}))
    show('live_fixed',req('POST','/api/runs',{'order_id':'order-001','mode':'live'}))
finally: httpd.shutdown(); httpd.server_close(); th.join()
