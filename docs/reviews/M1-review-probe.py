import sys, json, threading, http.client, os
from pathlib import Path
sys.path.insert(0, '/home/dongchan-lee/projects/nvidia-hackothon')
from backend.app import Database, Trace, Gateway, run_refund, split_manifest
from backend import server

def show(name, value):
    print(json.dumps({'check': name, 'observed': value}, ensure_ascii=False))

db = Database()
gateway = Gateway(db, Trace(db, 'review-stale', 'mock', 'order-001'))
quote = gateway.call('quote_refund', {'order_id': 'order-001'})
db.conn.execute("UPDATE returns SET received=0 WHERE order_id='order-001'")
db.conn.execute("UPDATE orders SET paid_krw=100, version=2 WHERE id='order-001'")
db.conn.execute("UPDATE quotes SET policy_hash='stale-policy' WHERE id=?", (quote['quote_id'],))
db.conn.commit()
result = gateway.call('issue_refund', {'order_id': 'order-001', 'quote_id': quote['quote_id'], 'idempotency_key': 'review-stale-key'})
show('stale_quote_write', {'result': result, 'order': dict(db.one("SELECT paid_krw,refunded_krw,version FROM orders WHERE id='order-001'"))})

db2 = Database()
t = Trace(db2, 'review-transaction', 'mock', 'order-001')
db2.conn.execute('BEGIN IMMEDIATE')
db2.conn.execute("UPDATE orders SET status='REVIEW_UNCOMMITTED' WHERE id='order-001'")
thread = threading.Thread(target=lambda: t.add('review.other_request', {}))
thread.start(); thread.join()
db2.conn.rollback()
show('cross_thread_trace_commit', dict(db2.one("SELECT status FROM orders WHERE id='order-001'")))

db3 = Database()
original = Gateway._verify_refund
Gateway._verify_refund = lambda self, args: {'committed': False, 'amount_krw': 0}
try:
    r = run_refund(db3, 'order-001')
    show('failed_verification_oracle', {'response': r, 'run': dict(db3.one('SELECT status,oracle_result FROM runs WHERE id=?', (r['run_id'],)))})
finally:
    Gateway._verify_refund = original

server.DB = Database()
server.DB.conn.execute("UPDATE returns SET received=1 WHERE order_id='order-003'")
server.DB.conn.commit()
httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
worker = threading.Thread(target=httpd.serve_forever, daemon=True)
worker.start()
def request(method, path, body=None):
    conn = http.client.HTTPConnection('127.0.0.1', httpd.server_port, timeout=5)
    conn.request(method, path, body=json.dumps(body) if body is not None else None,
                 headers={'Content-Type': 'application/json'})
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response.status, data
try:
    status, data = request('POST', '/api/runs', {'order_id':'order-003','customer_id':'cust-002','mode':'live'})
    result = json.loads(data)
    show('client_identity_and_live_label', {'http':status,'response':result,'stored_mode':server.DB.one('SELECT mode FROM runs WHERE id=?',(result['run_id'],))['mode']})
    status, data = request('GET', '/../README.md')
    show('static_path_escape', {'http':status,'matches_repository_readme':data == Path('/home/dongchan-lee/projects/nvidia-hackothon/README.md').read_bytes()})
    os.environ['NVIDIA_API_KEY'] = 'review-dummy-not-a-real-key'
    status, data = request('GET', '/health')
    show('health_dummy_key', json.loads(data))
finally:
    httpd.shutdown(); httpd.server_close(); worker.join()

manifest = split_manifest()
show('split_sizes', {k:len(manifest[k]) for k in ('discovery','validation','test')})
