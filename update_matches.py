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
SUMMARY="https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/summary?event={}"
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
def fetch_summary(event_id):
    """Solo se incorporan incidencias presentes en el acta ESPN del evento."""
    req=urllib.request.Request(SUMMARY.format(event_id),headers={"User-Agent":"MiZonaDeportiva/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=15) as response:
        return json.load(response)

def detail_from_summary(payload, event_id):
    details={"sourceUrl":f"https://www.espn.com/soccer/match/_/gameId/{event_id}"}
    header=payload.get("header") or {}
    comps=header.get("competitions") or []
    competition=comps[0] if comps else {}
    venue=(competition.get("venue") or {}).get("fullName") or (payload.get("gameInfo") or {}).get("venue",{}).get("fullName")
    if venue:details["venue"]=venue
    events=[]
    for play in payload.get("keyEvents") or payload.get("plays") or []:
        if not isinstance(play,dict):continue
        clock=play.get("clock") or {}
        minute=clock.get("displayValue") or play.get("minute")
        if minute is None:continue
        raw_type=play.get("type")
        kind=(raw_type.get("text") or raw_type.get("displayName") or "") if isinstance(raw_type,dict) else str(raw_type or "")
        text=play.get("text") or play.get("description") or play.get("shortText") or ""
        if not kind and not text:continue
        # Los campos del proveedor se conservan sin deducir nombres o minutos.
        if text:
            events.append({"minute":str(minute).replace("'",""),"type":str(kind or "Incidencia")[:70],"description":str(text)[:300]})
    if events:details["events"]=events
    return details

def enrich_match_details(club):
    """Enriquece solo encuentros LaLiga con identificador ESPN y no altera el marcador."""
    updated=0
    for match in club.get("results",[]):
        eid=str(match.get("eventId") or "")
        if not eid.isdigit() or (match.get("source")!="ESPN" and "LaLiga" not in match.get("competition","")):continue
        if match.get("detailEventId")==eid and match.get("detailsChecked"):continue
        try:
            payload=fetch_summary(eid)
            if not payload.get("header"):continue
            detail=detail_from_summary(payload,eid)
            for key,value in detail.items():
                if key=="events" and not value:continue
                match[key]=value
            match["detailEventId"]=eid
            match["detailsChecked"]=dt.datetime.now(dt.timezone.utc).isoformat()
            updated+=1
        except Exception as exc:
            print("ESPN acta no disponible",eid,str(exc)[:100])
    return updated

def update():
    data=json.loads(PATH.read_text(encoding="utf-8"))
    club=data["clubs"][TARGET]
    today=dt.datetime.now(ZoneInfo("Europe/Madrid")).date()
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
            home=next((x for x in sides if x.get("homeAway")=="home"),None)
            away=next((x for x in sides if x.get("homeAway")=="away"),None)
            if not home or not away:continue
            date_text=event.get("date","")
            try:
                timestamp=dt.datetime.fromisoformat(date_text.replace("Z","+00:00")).astimezone(ZoneInfo('Europe/Madrid'))
            except ValueError:continue
            seen.add(eid)
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
    def same_event(x,y):
        return bool(x.get("eventId") and y.get("eventId") and x["eventId"]==y["eventId"]) or match(x,y)
    for match_new in past:
        existing=next((x for x in club.get("results",[]) if same_event(x,match_new)),None)
        if existing:
            # No alterar resultados manuales discrepantes: requieren comprobación.
            if existing.get("score")!=match_new["score"]:
                print("REVISAR MARCADOR",existing,match_new)
            continue
        club.setdefault("results",[]).append(match_new)
        added+=1
    # Retirar de próximos partidos los encuentros que ESPN confirma como finalizados.
    # No se borran partidos por una simple ausencia en el proveedor.
    completed_ids={x["eventId"] for x in past}
    before=len(club.get("upcoming",[]))
    club["upcoming"]=[x for x in club.get("upcoming",[]) if not (x.get("eventId") in completed_ids or (any(same_event(x,p) for p in past) and ("LaLiga" in x.get("competition","") or x.get("source")=="ESPN"))]
    removed=before-len(club["upcoming"])
    # Los encuentros de LaLiga en la ventana se actualizan si coinciden por equipos y fecha.
    for match_new in future:
        existing=next((x for x in club.get("upcoming",[]) if same_event(x,match_new)),None)
        if existing:
            if existing.get("date")!=match_new["date"]:
                existing["date"]=match_new["date"]
                revised+=1
            if existing.get("time")!=match_new["time"]:
                existing["time"]=match_new["time"]
                revised+=1
            if not existing.get("eventId"):
                existing["eventId"]=match_new["eventId"]
                revised+=1
        elif not any(same_event(x,match_new) for x in club.get("results",[])):
            club.setdefault("upcoming",[]).append(match_new)
            added+=1
    club["results"].sort(key=lambda x:x.get("date",""),reverse=True)
    club["upcoming"].sort(key=lambda x:x.get("date",""))
    # No borrar encuentros futuros automáticamente: la fuente puede estar incompleta.
    # Excluir del calendario partidos pasados de LaLiga ya incluidos en resultados.
    known_results=club.get("results",[])
    old_count=len(club["upcoming"])
    club["upcoming"]=[m for m in club["upcoming"] if not (("LaLiga" in m.get("competition","") or m.get("source")=="ESPN") and any(same_event(m,r) for r in known_results))]
    removed+=old_count-len(club["upcoming"])
    enriched=enrich_match_details(club)
    if added or revised or removed or enriched:
        data["automaticUpdate"]={"source":"ESPN LaLiga","checkedAt":dt.datetime.now(dt.timezone.utc).isoformat(),"scope":"Athletic Club: LaLiga","added":added,"revised":revised,"removedCompleted":removed,"detailsEnriched":enriched}
        PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Consultas:",successes,"nuevos:",added,"horarios corregidos:",revised,"partidos finalizados retirados:",removed,"actas enriquecidas:",enriched)
if __name__=="__main__":
    update()
