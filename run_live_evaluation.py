import json
from backend.config import ROOT,load_env
from backend.app import Database
from backend.engine import WorkflowService
from backend.evaluation import benchmark
load_env()
report=benchmark(WorkflowService(Database(str(ROOT/'artifacts/skillforge.sqlite3'))),live=True)
print(json.dumps({'id':report['id'],'summary':report['summary']}),flush=True)
