
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from email.parser import BytesParser
from email.policy import default
from urllib.parse import urlparse
from pypdf import PdfReader
from io import BytesIO
from datetime import datetime, date
from difflib import SequenceMatcher
import json, re, os, html

HOST = os.environ.get("ONEVISIT_HOST", "127.0.0.1")
PORT = int(os.environ.get("ONEVISIT_PORT", "5055"))
MAX_UPLOAD_BYTES = int(os.environ.get("ONEVISIT_MAX_UPLOAD_MB", "15")) * 1024 * 1024
LAST_REPORT = {}
SERVICES = {
 "Scholarship":["identity","income","bank","student"],
 "Pension":["identity","age","bank","income"],
 "Ration card":["identity","address","income"],
 "College admission":["identity","marksheet","transfer"]
}
LABELS={"identity":"Identity proof","income":"Income certificate","bank":"Bank passbook",
 "student":"Student / bonafide certificate","age":"Age proof","address":"Address proof",
 "marksheet":"Marksheets","transfer":"Transfer certificate"}
DEMO_DOCS=[
 ("01_identity_proof.txt","DOCUMENT TYPE: IDENTITY PROOF\nName: Aarav Demo\nDate of Birth: 14/03/2005\nAddress: Ward 4, Sample Nagar, Demo District\nDocument Number: DEMO-ID-001\n"),
 ("02_income_certificate.txt","DOCUMENT TYPE: INCOME CERTIFICATE\nName: Aarav D.\nAnnual Income: 180000\nIssue Date: 10/01/2024\nValid Until: 09/01/2025\nCertificate Number: DEMO-INC-002\n"),
 ("03_bank_passbook.txt","DOCUMENT TYPE: BANK PASSBOOK\nAccount Holder Name: Aarav Demo\nAccount Number: XXXX-XXXX-1234\nIFSC: DEMO0001234\n"),
 ("04_student_certificate.txt","DOCUMENT TYPE: STUDENT / BONAFIDE CERTIFICATE\nName: Aarav Demo\nInstitution: Demo College\nCourse: B.Tech\nAcademic Year: 2026-27\n")]

def find_value(text, patterns):
 for p in patterns:
  m=re.search(p,text,re.I|re.M)
  if m:return m.group(1).strip().strip(" ,;")
 return None

def parse_date(v):
 if not v:return None
 for fmt in ("%d/%m/%Y","%d-%m-%Y","%Y-%m-%d","%d %b %Y","%d %B %Y"):
  try:return datetime.strptime(v.strip(),fmt).date()
  except:pass
 return None

def classify(name,text):
 s=(name+" "+text[:500]).lower()
 for kind,words in [
  ("identity",["aadhaar","aadhar","identity","voter","passport","id proof"]),
  ("income",["income certificate","income_cert","income"]),
  ("bank",["bank","passbook","account holder","ifsc"]),
  ("student",["bonafide","student certificate","college id","student"]),
  ("age",["age proof","birth certificate"]),("address",["address proof","residence proof"]),
  ("marksheet",["marksheet","mark sheet","transcript"]),("transfer",["transfer certificate"])]:
  if any(w in s for w in words):return kind
 return "unknown"

def inspect(name,text):
 kind=classify(name,text)
 person=find_value(text,[r"^(?:account holder name|name of applicant|applicant name|name)\s*:\s*(.+)$"])
 expiry=find_value(text,[r"^(?:valid until|valid till|expiry date|expires on)\s*:\s*(.+)$"])
 flags=[]
 if len(text.strip())<15:flags.append("Text could not be extracted. Upload a clearer text-based PDF or TXT file.")
 d=parse_date(expiry)
 if d and d<date.today():flags.append("Document appears expired based on the extracted validity date.")
 return {"filename":name,"type":kind,"type_label":LABELS.get(kind,"Unclassified document"),
         "name":person,"expiry_date":expiry,"flags":flags,"status":"Readable" if len(text.strip())>15 else "Needs manual review"}

def analyze(service,docs):
 required=SERVICES.get(service,SERVICES["Scholarship"])
 items=[inspect(n,t) for n,t in docs]
 found={d["type"] for d in items}
 missing=[LABELS[k] for k in required if k not in found]
 issues=[]
 for d in items:
  for f in d["flags"]:
   issues.append({"severity":"high" if "expired" in f.lower() else "medium","document":d["filename"],"message":f})
 names=[(d["filename"],d["name"]) for d in items if d["name"]]
 if len(names)>1:
  base=names[0][1].lower()
  for fn,n in names[1:]:
   ratio=SequenceMatcher(None,re.sub("[^a-z]","",base),re.sub("[^a-z]","",n.lower())).ratio()
   if ratio<.90:issues.append({"severity":"medium","document":fn,"message":f"Name differs from another uploaded document: '{n}'. Verify against original records."})
 for m in missing:issues.append({"severity":"high","document":m,"message":"Required document not found for the selected service."})
 high=sum(x["severity"]=="high" for x in issues); med=sum(x["severity"]=="medium" for x in issues)
 score=max(0,100-high*25-med*10)
 readiness="Not ready — resolve critical items" if high else ("Review needed — check flagged items" if med else "Looks ready for final human review")
 actions=[]
 if missing:actions.append("Obtain: "+", ".join(missing)+".")
 if any("expired" in x["message"].lower() for x in issues):actions.append("Request a currently valid certificate and re-run the check.")
 if any("name differs" in x["message"].lower() for x in issues):actions.append("Check spelling/initials with the issuing authority; do not alter official documents yourself.")
 if not actions:actions.append("Cross-check this result with the latest official checklist before submission.")
 return {"service":service,"documents":items,"missing":missing,"issues":issues,"score":score,"readiness":readiness,
  "actions":actions,"generated_at":datetime.now().strftime("%d %b %Y, %I:%M %p"),
  "disclaimer":"Prototype assistance only. Not an official eligibility decision or legal validation. Requirements vary by scheme, state and authority. Confirm with the official portal/office."}

PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ONEVISIT</title>
<style>
:root{--navy:#142c4d;--blue:#2563eb;--teal:#0f9f91;--ink:#172033;--muted:#65748b;--bg:#f3f6fb;--line:#e3e9f2;--red:#c43d4d;--amber:#a76b08}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:var(--ink)}
header{background:linear-gradient(115deg,#102744,#1b4c79);color:#fff;padding:24px max(22px,calc((100% - 1180px)/2));display:flex;justify-content:space-between;align-items:center}
.brand{font-size:24px;font-weight:850;letter-spacing:.7px}.brand span{color:#65d7c7}.tag{font-size:12px;color:#d4e4f4;margin-top:3px}.pill{border:1px solid #ffffff55;border-radius:30px;padding:8px 13px;font-size:12px;color:#e8f5ff}
main{max-width:1180px;margin:28px auto;padding:0 20px}.hero{margin-bottom:22px}.hero h1{font-size:30px;margin:0 0 8px;color:var(--navy)}.hero p{margin:0;color:var(--muted);max-width:760px;line-height:1.5}
.grid{display:grid;grid-template-columns:1.05fr .95fr;gap:18px}.card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:22px;box-shadow:0 8px 26px #17345b0a}.card h2{font-size:17px;margin:0 0 6px;color:var(--navy)}.sub{font-size:13px;color:var(--muted);margin:0 0 17px;line-height:1.5}
label{display:block;font-weight:700;font-size:13px;margin:15px 0 7px}select,input[type=file]{width:100%;border:1px solid #d6dfeb;border-radius:10px;padding:12px;background:#fff;color:var(--ink)}
.drop{border:1.5px dashed #9db2ce;border-radius:14px;padding:20px;background:#f8fbff;text-align:center}.drop strong{display:block;color:var(--navy);margin-bottom:4px}.drop small{color:var(--muted)}
.btn{border:0;border-radius:10px;padding:12px 17px;font-weight:750;cursor:pointer;font-size:14px}.primary{background:var(--blue);color:#fff}.secondary{background:#eaf2ff;color:#1d4c8c}.demo{background:#e4f7f3;color:#08796e}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
.feature{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid var(--line)}.feature:last-child{border:0}.ico{width:34px;height:34px;border-radius:10px;background:#eaf2ff;color:#2455a0;display:grid;place-items:center;font-weight:800}.feature b{font-size:13px}.feature small{display:block;color:var(--muted);font-size:12px;margin-top:3px}
.result{margin-top:20px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.stat{background:#f7f9fc;border:1px solid var(--line);padding:15px;border-radius:13px}.stat strong{font-size:26px;color:var(--navy);display:block}.stat span{font-size:11px;color:var(--muted)}
.status{padding:12px 14px;border-radius:12px;background:#fff4e6;color:#885400;font-weight:750;margin:15px 0}.issue{padding:12px 14px;border:1px solid var(--line);border-radius:11px;margin:8px 0;display:flex;gap:10px}.dot{width:9px;height:9px;border-radius:50%;background:var(--amber);margin-top:5px;flex:none}.dot.high{background:var(--red)}.issue b{font-size:13px}.issue p{font-size:12px;color:var(--muted);margin:4px 0 0;line-height:1.4}
.docrow{display:grid;grid-template-columns:1fr auto;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:13px}.ok{color:#078269}.warn{color:#a76b08}footer{max-width:1180px;margin:24px auto 45px;padding:0 20px;color:#748197;font-size:11px;line-height:1.5}
@media(max-width:800px){.grid{grid-template-columns:1fr}.pill{display:none}.stats{grid-template-columns:1fr 1fr}}
</style></head><body><header><div><div class="brand">ONE<span>VISIT</span></div><div class="tag">Application readiness • Document consistency • Citizen-first services</div></div><div class="pill">LOCAL PROTOTYPE · SYNTHETIC DEMO</div></header>
<main><section class="hero"><h1>Make the first visit count.</h1><p>Check a document set before visiting an office or submitting an application. ONEVISIT flags missing documents, visible expiry dates and cross-document inconsistencies.</p></section>
<div class="grid"><section class="card"><h2>1. Choose your service</h2><p class="sub">Checklists are illustrative demo rules. A real deployment must use current, official requirements.</p>
<label for="service">Application type</label><select id="service"><option>Scholarship</option><option>Pension</option><option>Ration card</option><option>College admission</option></select>
<label>2. Upload supporting documents</label><div class="drop"><strong>Choose files from your device</strong><small>PDF (text-based), TXT, CSV or MD · 15 MB total</small><input id="files" type="file" multiple accept=".pdf,.txt,.csv,.md"></div>
<div class="actions"><button class="btn primary" id="analyze">Analyze application →</button><button class="btn demo" id="demo">▶ Run sample demo</button></div><p id="msg" class="sub" style="margin-top:12px"></p>
</section><section class="card"><h2>What ONEVISIT checks</h2><p class="sub">A practical pre-submission assistant, not an official approval engine.</p>
<div class="feature"><div class="ico">✓</div><div><b>Missing-document detection</b><small>Compares uploads with a service-specific checklist.</small></div></div>
<div class="feature"><div class="ico">↔</div><div><b>Cross-document consistency</b><small>Checks names and selected fields across documents.</small></div></div>
<div class="feature"><div class="ico">◷</div><div><b>Expiry &amp; validity alerts</b><small>Flags explicit validity dates that appear expired.</small></div></div>
<div class="feature"><div class="ico">✦</div><div><b>Actionable correction plan</b><small>Explains what to verify before a visit.</small></div></div>
<div class="feature"><div class="ico">↓</div><div><b>Portable audit report</b><small>Download a JSON report for the applicant or help desk.</small></div></div>
</section></div><div id="results"></div></main>
<footer>Privacy-first prototype: uploaded files are processed in memory and are not intentionally saved. Do not upload real identity documents to an untrusted deployment. This tool does not determine legal eligibility or guarantee acceptance.</footer>
<script>
const $=id=>document.getElementById(id);
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function render(r){let issues=r.issues.map(x=>`<div class="issue"><span class="dot ${x.severity==="high"?"high":""}"></span><div><b>${esc(x.document)} · ${esc(x.severity.toUpperCase())}</b><p>${esc(x.message)}</p></div></div>`).join("")||'<p class="sub">No issues detected by prototype rules. Verify the official checklist anyway.</p>';
let docs=r.documents.map(d=>`<div class="docrow"><span><b>${esc(d.type_label)}</b><br><span style="color:#718096;font-size:11px">${esc(d.filename)}</span></span><span class="${d.flags.length?"warn":"ok"}">${d.flags.length?"Review":esc(d.status)}</span></div>`).join("");
let actions=r.actions.map(a=>`<li style="font-size:13px;margin:7px 0">${esc(a)}</li>`).join("");
$("results").innerHTML=`<section class="card result"><h2>3. Readiness report</h2><p class="sub">${esc(r.service)} · ${esc(r.generated_at)}</p><div class="stats"><div class="stat"><strong>${r.score}/100</strong><span>Prototype readiness score</span></div><div class="stat"><strong>${r.documents.length}</strong><span>Documents analyzed</span></div><div class="stat"><strong>${r.issues.length}</strong><span>Items to review</span></div></div><div class="status">${esc(r.readiness)}</div><h2>Document inventory</h2>${docs}<h2 style="margin-top:18px">Issues detected</h2>${issues}<h2 style="margin-top:18px">Recommended next steps</h2><ol>${actions}</ol><div class="actions"><a class="btn secondary" href="/download-report">Download audit report (JSON)</a><button class="btn secondary" onclick="window.scrollTo({top:0,behavior:'smooth'})">Start new check</button></div><p class="sub" style="margin-top:16px">${esc(r.disclaimer)}</p></section>`;}
$("demo").onclick=async()=>{ $("msg").textContent="Running synthetic sample…";let r=await fetch("/demo",{method:"POST"});let j=await r.json();render(j);$("msg").textContent="Sample analysis complete. The demo intentionally includes an expired certificate and a name variation.";};
$("analyze").onclick=async()=>{let fs=$("files").files;if(!fs.length){$("msg").textContent="Please choose at least one PDF/TXT file, or run the sample demo.";return;}let fd=new FormData();fd.append("service",$("service").value);for(let f of fs)fd.append("documents",f);$("msg").textContent="Analyzing uploaded documents…";let r=await fetch("/analyze",{method:"POST",body:fd});let j=await r.json();render(j);$("msg").textContent="Analysis complete. Review every flag manually.";};
</script></body></html>'''

def extract_upload(filename,payload):
 text=""
 ext=os.path.splitext(filename)[1].lower()
 try:
  if ext==".pdf":
   reader=PdfReader(BytesIO(payload)); text="\n".join((p.extract_text() or "") for p in reader.pages)
  elif ext in (".txt",".csv",".md"): text=payload.decode("utf-8",errors="ignore")
 except Exception: text=""
 return filename,text

class Handler(BaseHTTPRequestHandler):
 def send(self,code,body,ctype="text/html; charset=utf-8"):
  b=body if isinstance(body,bytes) else body.encode("utf-8")
  self.send_response(code);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):
  global LAST_REPORT
  path=urlparse(self.path).path
  if path=="/":return self.send(200,PAGE)
  if path=="/health":return self.send(200,json.dumps({"status":"ok","app":"ONEVISIT","version":"0.1.0"}),"application/json")
  if path=="/download-report":
   if not LAST_REPORT:return self.send(404,'{"error":"Run analysis first"}',"application/json")
   b=json.dumps(LAST_REPORT,indent=2).encode()
   self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Disposition",'attachment; filename="onevisit_audit_report.json"');self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b);return
  return self.send(404,"Not found")
 def do_POST(self):
  global LAST_REPORT
  path=urlparse(self.path).path
  if path=="/demo":
   LAST_REPORT=analyze("Scholarship",DEMO_DOCS)
   return self.send(200,json.dumps(LAST_REPORT),"application/json")
  if path=="/analyze":
   length=int(self.headers.get("Content-Length","0"))
   if length > MAX_UPLOAD_BYTES:
    return self.send(413, json.dumps({"error":f"Upload exceeds {MAX_UPLOAD_BYTES//(1024*1024)} MB limit."}), "application/json")
   body=self.rfile.read(length)
   ct=self.headers.get("Content-Type","")
   msg=BytesParser(policy=default).parsebytes(("Content-Type: "+ct+"\r\nMIME-Version: 1.0\r\n\r\n").encode()+body)
   service="Scholarship";docs=[]
   if msg.is_multipart():
    for part in msg.iter_parts():
     field=part.get_param("name",header="content-disposition")
     filename=part.get_filename()
     data=part.get_payload(decode=True) or b""
     if field=="service":service=data.decode(errors="ignore")
     elif field=="documents" and filename:
      if os.path.splitext(filename)[1].lower() not in (".pdf",".txt",".csv",".md"):
       continue
      docs.append(extract_upload(os.path.basename(filename),data))
   LAST_REPORT=analyze(service,docs)
   return self.send(200,json.dumps(LAST_REPORT),"application/json")
  return self.send(404,"Not found")
 def log_message(self,*args): pass

if __name__=="__main__":
 print(f"ONEVISIT running at http://{HOST}:{PORT}")
 ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
