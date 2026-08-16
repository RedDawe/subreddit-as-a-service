import json,time,sys,urllib.request,datetime as dt
BASE="https://arctic-shift.photon-reddit.com/api"
def get(path,params,tries=6):
    q="&".join(f"{k}={v}" for k,v in params.items())
    url=f"{BASE}/{path}?{q}"
    for i in range(tries):
        try:
            r=urllib.request.urlopen(url,timeout=90)
            d=json.loads(r.read())
            if d.get("data") is not None: return d["data"]
            time.sleep(4*(i+1))
        except Exception as e:
            time.sleep(4*(i+1))
    return []
def walk(kind,sub,start,end,fields):
    out=[];cur=start
    while cur<end:
        b=cur+dt.timedelta(days=7)
        rows=get(f"{kind}/search",{"subreddit":sub,"after":cur.strftime("%Y-%m-%dT%H:%M:%S"),
            "before":min(b,end).strftime("%Y-%m-%dT%H:%M:%S"),"limit":100,"sort":"asc","fields":fields})
        out+=rows; cur=b
        print(f"  {cur.date()} +{len(rows)} total={len(out)}",file=sys.stderr)
        time.sleep(1.5)
    return out
if __name__=="__main__":
    kind,s,e,out=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
    f="id,created_utc,title,selftext,score,num_comments,author,retrieved_on" if kind=="posts" else "id,created_utc,body,score,author,retrieved_on"
    rows=walk(kind,"ValueInvesting",dt.datetime.fromisoformat(s),dt.datetime.fromisoformat(e),f)
    json.dump(rows,open(out,"w"))
    print(f"WROTE {len(rows)} -> {out}")
