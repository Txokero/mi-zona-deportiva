"""Actualiza retratos desde las páginas oficiales, sin inventar asociaciones."""
import json, pathlib, re, unicodedata, urllib.request
from bs4 import BeautifulSoup
ROOT=pathlib.Path(__file__).parent
path=ROOT/'club-data.json'
data=json.loads(path.read_text(encoding='utf-8'))
def norm(s):
 s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]+',' ',s).strip()
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; SportsRosterUpdater/1.0)'})
 with urllib.request.urlopen(req,timeout=30) as r:return BeautifulSoup(r.read(3_000_000),'html.parser')
def src(img):
 for attr in ('data-src','data-lazy-src','src'):
  value=img.get(attr,'')
  if value.startswith('https://'):return value
  if value.startswith('//'):return 'https:'+value
 return ''
def athletic():
 soup=get('https://www.athletic-club.eus/equipos/athletic-club/2026-27/plantilla/')
 matches={}
 for img in soup.find_all('img'):
  url=src(img)
  if 'cdn.athletic-club.eus/imagenes/player_images/' not in url:continue
  alt=norm(img.get('alt',''))
  if not alt:continue
  matches[alt]=url
 # La web publica nombre completo en el alt y nombre deportivo en el título.
 names={
 'Unai Simón':'simón mendibil unai','Padilla':'padilla pérez alex','Vivian':'vivian moreno daniel',
 'Paredes':'paredes casamichana aitor','Yeray':'álvarez lópez yeray','Areso':'areso blanco jesús',
 'Laporte':'laporte aymeric','H. Rincón':'rincón lumbreras hugo','Yuri':'berchiche izeta yuri',
 'Johaneko':'louis-jean johaneko','Egiluz':'eguíluz arroyo unai',
 'Prados':'prados díaz beñat','O. Sancet':'sancet tirapu oihan',
 'R. de Galarreta':'ruiz de galarreta etxeberria iñigo','Jauregizar':'jauregizar alboniga mikel',
 'Rego':'rego mora alejandro','Gerenabarrena':'gerenabarrena zendoia beñat',
 'Canales':'canales urtasun peio','Selton':'sánchez camilo selton sued',
 'Berenguer':'berenguer remiro alejandro','Williams':'williams arthuer iñaki',
 'Nico Williams':'williams arthuer nicholas','Guruzeta':'guruzeta rodríguez gorka',
 'Maroan':'sannadi harrouch maroan','Nico Serrano':'serrano galdeano nicolás',
 'Navarro':'navarro muñoz robert','Djaló':'djaló dias fernandes álvaro',
 'Imga':'imga mitogo christian','Vizcay':'vizcay hurtado jesús','Conde':'conde albiol aritz'
 }
 changed=0
 for p in data['clubs']['Athletic Club']['squad']:
  key=norm(names.get(p['name'],''))
  if key in matches:
   if p.get('photo')!=matches[key]:p['photo']=matches[key];changed+=1
 return changed
def recre():
 soup=get('https://www.recreativohuelva.com/la-plantilla/')
 # Asociar exclusivamente si la foto tiene un texto alternativo con el nombre
 # deportivo o completo; no utilizar fotografías genéricas ni de otros jugadores.
 changed=0
 for p in data['clubs']['Recreativo de Huelva']['squad']:
  name=norm(p['name'])
  candidates=[]
  for img in soup.find_all('img'):
   alt=norm(img.get('alt',''))
   url=src(img)
   if alt and (alt==name or (len(name)>5 and name in alt)) and url and not any(x in url.lower() for x in ('logo','escudo')):
    candidates.append(url)
  if len(set(candidates))==1:
   url=candidates[0]
   if p.get('photo')!=url:p['photo']=url;changed+=1
 return changed
for label,fn in [('Athletic',athletic),('Recreativo',recre)]:
 try:print(label,'fotografías actualizadas:',fn())
 except Exception as exc:print(label,'sin cambios por error de fuente:',str(exc)[:160])
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
