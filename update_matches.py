"""Actualización conservadora de partidos de LaLiga desde ESPN (sin API key).
No reemplaza datos históricos, no inventa encuentros y no modifica Segunda RFEF.
"""
import datetime as dt
import json
import pathlib
import urllib.request
from zoneinfo import ZoneInfo

PATH=pathlib.Path(__file__).with_name("club-data.json")
BASE="https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard"
TARGET="Athletic Club"
ALIASES=("athletic club","athletic bilbao")
def fetch(date):
    url=f"{BASE}?dates={date}"
    req=urllib.request.Request(url,headers={"User-Agent":"MiZonaDeportiva/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.load(r)
def normalized(s):
    import unicodedata
    return " ".join(unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower().split())
def update():
    data=json.loads(PATH.read_text(encoding="utf-8"))
    club=data["clubs"][TARGET]
    today=dt.datetime.now(dt.timezone.utc).date()
    # Se consulta el pasado reciente y las próximas cuatro semanas.
    dates=[today+dt.timedelta(days=i) for i in range(-8,29)]
    seen=set()
    past=[]
    future=[]
    successes=0
    for day in dates:
        try:
            payload=fetch(day.strftime("%Y%m%d"))
            successes+=1
        except Exception as exc:
            print("ESPN: consulta fallida",day,str(exc)[:100])
            continue
        for event in payload.get("events",[]):
            eid=event.get("id")
            if not eid or eid in seen:continue
            comps=event.get("competitions",[])
            if not comps:continue
            c=comps[0]
            sides=c.get("competitors",[])
            if len(sides)!=2:continue
            names=[x.get("team",{}).get("displayName","") for x in sides]
            if not any(normalized(n) in ALIASES for n in names):continue
            seen.add(eid)
            home=next((x for x in sides if x.get("homeAway")=="home"),None)
            away=next((x for x in sides if x.get("homeAway")=="away"),None)
            if not home or not away:continue
            date_text=event.get("date","")
            try:
                timestamp=dt.datetime.fromisoformat(date_text.replace("Z","+00:00")).astimezone(ZoneInfo('Europe/Madrid'))
            except ValueError:continue
            item={"date":timestamp.date().isoformat(),"home":TARGET if normalized(home["team"].get("displayName","")) in ALIASES else home["team"].get("displayName",""),"away":TARGET if normalized(away["team"].get("displayName","")) in ALIASES else away["team"].get("displayName",""),"competition":"LaLiga","source":"ESPN","eventId":str(eid)}
            status=event.get("status",{}).get("type",{})
            if status.get("completed") is True and home.get("score") is not None and away.get("score") is not None:
                item["score"]=str(home["score"])+"-"+str(away["score"])
                past.append(item)
            elif status.get("state")=="pre":
                item["time"]=timestamp.strftime("%H:%M")
                future.append(item)
    if successes<5:
        print("No hay suficientes respuestas válidas: se conserva el calendario existente")
        return
    def match(x,y):
        return x.get("date")==y.get("date") and normalized(x.get("home"))==normalized(y.get("home")) and normalized(x.get("away"))==normalized(y.get("away"))
    added=0
    revised=0
    for match_new in past:
        existing=next((x for x in club.get("results",[]) if match(x,match_new)),None)
        if existing:
            # No alterar resultados manuales discrepantes: requieren comprobación.
            if existing.get("score")!=match_new["score"]:
                print("REVISAR MARCADOR",existing,match_new)
            continue
        club.setdefault("results",[]).append(match_new)
        added+=1
    # Los encuentros de LaLiga en la ventana se actualizan si coinciden por equipos y fecha.
    for match_new in future:
        existing=next((x for x in club.get("upcoming",[]) if match(x,match_new)),None)
        if existing:
            if existing.get("time")!=match_new["time"]:
                existing["time"]=match_new["time"]
                revised+=1
        elif not any(match(x,match_new) for x in club.get("results",[])):
            club.setdefault("upcoming",[]).append(match_new)
            added+=1
    club["results"].sort(key=lambda x:x.get("date",""),reverse=True)
    club["upcoming"].sort(key=lambda x:x.get("date",""))
    # No borrar encuentros futuros automáticamente: la fuente puede estar incompleta.
    if added or revised:
        data["automaticUpdate"]={"source":"ESPN LaLiga","checkedAt":dt.datetime.now(dt.timezone.utc).isoformat(),"scope":"Athletic Club: LaLiga","added":added,"revised":revised}
        PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Consultas:",successes,"nuevos:",added,"horarios corregidos:",revised)
if __name__=="__main__":
    update()
