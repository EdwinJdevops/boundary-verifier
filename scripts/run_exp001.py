#!/usr/bin/env python3
"""EXP-001 runner: execute controls and emit schema-compatible evidence JSON."""

from __future__ import annotations
import datetime as dt
import hashlib
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts"
STORE="canary-store.shared-services.svc.cluster.local:8080"
PEER="peer-endpoint.tenant-b.svc.cluster.local:8080"

def run(*args:str, check:bool=True)->subprocess.CompletedProcess[str]:
    return subprocess.run(args,text=True,capture_output=True,check=check)

def kexec(ns:str,*args:str,check:bool=True)->subprocess.CompletedProcess[str]:
    return run("kubectl","-n",ns,"exec","probe","--",*args,check=check)

def edge(src:str,relation:str,dst:str,evidence:str)->dict[str,str]:
    return {"from":src,"relation":relation,"to":dst,"evidence":evidence}

def now()->str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def record(run_id:str,scenario:str,status:str,edges:list[dict[str,str]],canary_sha256:str|None=None)->dict:
    x={"run_id":run_id,"scenario":scenario,"status":status,"observed_at":now(),"edges":edges}
    if canary_sha256: x["canary_sha256"]=canary_sha256
    return x

def curl(ns:str,url:str,*extra:str,check:bool=True):
    return kexec(ns,"curl","--silent","--show-error","--fail","--max-time","3",*extra,url,check=check)

def main()->int:
    run_id=f"exp001-{int(time.time())}-{secrets.token_hex(4)}"
    canary=secrets.token_hex(32)
    digest=hashlib.sha256(canary.encode()).hexdigest()
    results=[]

    a_to_b=curl("tenant-a",f"http://{PEER}/healthz",check=False)
    results.append(record(run_id,"direct-tenant-a-to-tenant-b",
        "OBSERVED_BLOCKED" if a_to_b.returncode!=0 else "OBSERVED_REACHABLE",
        [] if a_to_b.returncode!=0 else [edge("tenant-a/probe","CAN_CONNECT","tenant-b/peer-endpoint","HTTP probe succeeded")]))

    b_to_a=kexec("tenant-b","curl","--silent","--show-error","--fail","--max-time","3",
        "http://probe.tenant-a.svc.cluster.local:8080/healthz",check=False)
    # There is intentionally no tenant-a Service yet; DNS absence is not network-policy evidence.
    results.append(record(run_id,"direct-tenant-b-to-tenant-a","NOT_EVALUATED",[],
        ))

    write=curl("tenant-a",f"http://{STORE}/v1/{run_id}","-X","PUT","--data-binary",canary,check=False)
    if write.returncode!=0:
        results.append(record(run_id,"shared-state-path","UNKNOWN",[]))
    else:
        read=curl("tenant-b",f"http://{STORE}/v1/{run_id}",check=False)
        observed=None
        if read.returncode==0:
            try: observed=json.loads(read.stdout)["value"]
            except (KeyError,json.JSONDecodeError): pass
        ok=observed==canary
        results.append(record(run_id,"shared-state-path","OBSERVED_REACHABLE" if ok else "UNKNOWN",
            [edge("tenant-a/probe","CAN_WRITE","shared-services/canary-store","HTTP PUT succeeded"),
             edge("tenant-b/probe","CAN_READ","shared-services/canary-store","HTTP GET returned exact canary")] if ok else
            [edge("tenant-a/probe","CAN_WRITE","shared-services/canary-store","HTTP PUT succeeded")],
            digest))

    OUT.mkdir(exist_ok=True)
    path=OUT/f"{run_id}.json"
    path.write_text(json.dumps({"experiment":"EXP-001","results":results},indent=2)+"\n")
    print(path)
    print(json.dumps({"run_id":run_id,"statuses":{r["scenario"]:r["status"] for r in results}},indent=2))
    return 1 if any(r["scenario"]=="direct-tenant-a-to-tenant-b" and r["status"]!="OBSERVED_BLOCKED" for r in results) else 0

if __name__=="__main__":
    sys.exit(main())
