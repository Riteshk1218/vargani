# Creates a demo organization through the real API (dev server with OTP_DEBUG_ECHO=true).
# Usage: python tool/seed_demo.py   (API at http://localhost:8000, empty database)
import json, sys, urllib.request
B="http://localhost:8000/api/v1"
def call(m,p,body=None,tok=None,org=None,ok=True):
    h={"Content-Type":"application/json","X-Client-Type":"app"}
    if tok:h["Authorization"]="Bearer "+tok
    if org:h["X-Organization-ID"]=org
    r=urllib.request.Request(B+p,data=json.dumps(body).encode() if body is not None else None,method=m,headers=h)
    try:
        with urllib.request.urlopen(r) as x: t=x.read(); return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        t=e.read().decode(); print("ERR",m,p,e.code,t[:600]); 
        if ok: sys.exit(1)
        return None
r=call("POST","/auth/register/",{"full_name":"Asha Admin","email":"admin@demo.test","mobile":"9800000001","password":"DemoPass#2026"})
print("register",json.dumps(r)[:400])
v=call("POST","/auth/verify/",{"destination":"admin@demo.test","code":r["debug_code"]})
print("verify keys",list(v.keys()))
L=call("POST","/auth/login/",{"identifier":"admin@demo.test","password":"DemoPass#2026"})
tok=L["access"]; print("login keys",list(L.keys()))
o=call("POST","/organizations/",{"name":"Demo Mitra Mandal","city":"Pune","state":"Maharashtra","financial_year":{"label":"2026-27","start_date":"2026-04-01","end_date":"2027-03-31"}},tok)
print("org",json.dumps(o)[:500])
O=o["id"]
md=call("GET",f"/me/organizations/{O}/",None,tok,O); print("me/org",json.dumps(md)[:700])
fy=md["current_financial_year"]["id"]
ev=call("POST","/events/",{"name":"Ganesh Chaturthi 2026","template":"festival","code":"GC","financial_year":fy,"start_date":"2026-08-01","end_date":"2026-12-31"},tok,O)
print("event",json.dumps(ev)[:400])
E=ev["id"]
roles=call("GET","/roles/",None,tok,O); rl=roles if isinstance(roles,list) else roles["results"]; print("roles",[(x["code"],x["id"]) for x in rl])
fund=call("POST","/funds/",{"event":E,"name":"Utsav Fund"},tok,O)
ct1=call("POST","/contribution-types/",{"event":E,"fund":fund["id"],"name":"Ganesh Vargani","kind":"one_time","suggested_min":"500.00","suggested_max":"700.00","is_mandatory":True,"target_amount":"600.00"},tok,O)
print("ct",json.dumps(ct1)[:300])
ct2=call("POST","/contribution-types/",{"event":E,"fund":fund["id"],"name":"Donation","kind":"one_time"},tok,O)
call("PATCH",f"/organizations/{O}/settings/",{"member_portal_enabled":True},tok,O)
ppl=[]
for i,(n,mob) in enumerate([("Ritesh Patil","9822001122"),("Sunita More","9822001133"),("Vikas Jadhav","9822001144")]):
    ppl.append(call("POST","/people/",{"full_name":n,"mobile":mob,"area":"Shivaji Nagar","person_types":["member"]},tok,O))
for p in ppl: call("POST","/event-participants/",{"event":E,"person":p["id"]},tok,O)
rid={x["code"]:x["id"] for x in rl}
inv=call("POST","/invitations/",{"full_name":"Kiran Collector","email":"collector@demo.test","role_id":rid["collector"]},tok,O)
print("inv",json.dumps(inv)[:500])
token=inv["invite_url"].rsplit("/",1)[1]
r2=call("POST","/auth/register/",{"full_name":"Kiran Collector","email":"collector@demo.test","password":"DemoPass#2026"})
call("POST","/auth/verify/",{"destination":"collector@demo.test","code":r2["debug_code"]})
ctok=call("POST","/auth/login/",{"identifier":"collector@demo.test","password":"DemoPass#2026"})["access"]
call("POST","/invitations/accept/",{"token":token},ctok)
mem=call("GET",f"/collectors/?event={E}",None,tok,O); ml=mem if isinstance(mem,list) else mem["results"]
print("collectors",json.dumps(ml)[:600])
mem=call("GET","/members/",None,tok,O); ml=mem if isinstance(mem,list) else mem["results"]
print("member0",json.dumps(ml[0])[:300])
cm=[m for m in ml if m["role"]["code"]=="collector"][0]
call("POST","/collector-assignments/bulk/",{"event":E,"collector":cm["id"],"people":[p["id"] for p in ppl[:2]]},tok,O)
# a couple of real collections by admin so member has history
import uuid
def collect(t,payer,amt,mode="cash",ref=""):
    req=urllib.request.Request(B+"/collections/",data=json.dumps({"event":E,"payer":payer,"mode":mode,"reference_number":ref,"lines":[{"contribution_type":ct1["id"],"amount":amt}]}).encode(),method="POST",headers={"Content-Type":"application/json","Authorization":"Bearer "+t,"X-Organization-ID":O,"Idempotency-Key":str(uuid.uuid4())})
    return json.loads(urllib.request.urlopen(req).read())
p1=collect(tok,ppl[0]["id"],"300.00"); print("collect",json.dumps(p1)[:600])
json.dump({"org":O,"event":E,"ct1":ct1["id"],"ct2":ct2["id"],"people":[p["id"] for p in ppl]},open("seed_ids.json","w"))
print("SEED OK")
