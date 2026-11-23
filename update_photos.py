"""Actualiza retratos desde las páginas oficiales, sin inventar asociaciones."""
import json, pathlib, re, unicodedata, urllib.request
from bs4 import BeautifulSoup
from urllib.parse import urljoin
ROOT=pathlib.Path(__file__).parent
path=ROOT/'club-data.json'
data=json.loads(path.read_text(encoding='utf-8'))
def norm(s):
 s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
 return re.sub(r'[^a-z0-9]+',' ',s).strip()
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; SportsRosterUpdater/1.0)'})
 with urllib.request.urlopen(req,timeout=30) as r:return BeautifulSoup(r.read(3_000_000),'html.parser')
def src(img,base):
 for attr in ('data-src','data-lazy-src','data-original','src','srcset','data-srcset'):
  value=(img.get(attr,'') or '').strip()
  if not value:continue
  if attr.endswith('srcset'):value=value.split(',')[0].strip().split(' ')[0]
  if value.startswith('data:') or value.endswith('.svg'):continue
  url=urljoin(base,value)
  if url.startswith('https://'):return url
 return ''
def find_nearby_image(heading,base):
 # La fotografía puede estar en la misma tarjeta, en un hermano o en un ancestro.
 for ancestor in [heading,*list(heading.parents)[:7]]:
  images=ancestor.find_all('img') if hasattr(ancestor,'find_all') else []
  usable=[src(img,base) for img in images]
  usable=[url for url in usable if url and not any(x in url.lower() for x in ('logo','escudo','badge','flag','sponsor'))]
  if len(set(usable))==1:return usable[0]
 return ''
def update_club(club,url):
 soup=get(url)
 players=data['clubs'][club]['squad']
 updated=0
 for p in players:
  name=norm(p['name'])
  candidates=[]
  for heading in soup.find_all(['h2','h3','h4','h5','strong']):
   title=norm(heading.get_text(' ',strip=True))
   # Coincidencia exacta del nombre deportivo, con dorsal opcional.
   title=re.sub(r'^\\d+\\s+','',title)
   if title!=name:continue
   photo=find_nearby_image(heading,url)
   if photo:candidates.append(photo)
  # Alternativa: alt de fotografía que coincide exactamente con nombre deportivo.
  for img in soup.find_all('img'):
   if norm(img.get('alt',''))==name:
    photo=src(img,url)
    if photo:candidates.append(photo)
  if len(set(candidates))==1:
   photo=candidates[0]
   if not p.get('photo'):p['photo']=photo;updated+=1
 return updated
ATHLETIC_FULL_NAMES={
'Unai Simón':'Simón Mendibil Unai','Padilla':'Padilla Pérez Alex','Vivian':'Vivian Moreno Daniel','Paredes':'Paredes Casamichana Aitor','Yeray':'Álvarez López Yeray','Areso':'Areso Blanco Jesús','Laporte':'Laporte Aymeric','H. Rincón':'Rincón Lumbreras Hugo','Yuri':'Berchiche Izeta Yuri','Johaneko':'Louis-Jean Johaneko','Egiluz':'Eguíluz Arroyo Unai','Prados':'Prados Díaz Beñat','O. Sancet':'Sancet Tirapu Oihan','R. de Galarreta':'Ruiz de Galarreta Etxeberria Iñigo','Jauregizar':'Jauregizar Alboniga Mikel','Rego':'Rego Mora Alejandro','Gerenabarrena':'Gerenabarrena Zendoia Beñat','Canales':'Canales Urtasun Peio','Selton':'Sánchez Camilo Selton Sued','Berenguer':'Berenguer Remiro Alejandro','Williams':'Williams Arthuer Iñaki','Nico Williams':'Williams Arthuer Nicholas','Guruzeta':'Guruzeta Rodríguez Gorka','Maroan':'Sannadi Harrouch Maroan','Nico Serrano':'Serrano Galdeano Nicolás','Navarro':'Navarro Muñoz Robert','Djaló':'Djaló Dias Fernandes Álvaro','Imga':'Imga Mitogo Christian','Vizcay':'Vizcay Hurtado Jesús','Conde':'Conde Albiol Aritz'}
def athletic():
 url='https://www.athletic-club.eus/equipos/athletic-club/2026-27/plantilla/'
 soup=get(url)
 found={}
 for img in soup.find_all('img'):
  alt=norm(img.get('alt',''))
  photo=src(img,url)
  if alt and photo and not any(x in photo.lower() for x in ('logo','escudo','badge','flag','sponsor')):
   found.setdefault(alt,set()).add(photo)
 updated=0
 for p in data['clubs']['Athletic Club']['squad']:
  key=norm(ATHLETIC_FULL_NAMES.get(p['name'],''))
  candidates=found.get(key,set())
  if len(candidates)==1:
   photo=next(iter(candidates))
   if not p.get('photo'):p['photo']=photo;updated+=1
 print('Athletic: imágenes con alt:',len(found),'coincidencias:',sum(len(found.get(norm(x),set()))==1 for x in ATHLETIC_FULL_NAMES.values()))
 return updated
RECRE_FULL_NAMES={
'Jero Lario':'Jerónimo Manuel Lario Martínez','F. Padilla':'Fernando Padilla Pasión','Roan':'Roan Riera Bañuls','Nacho Ruiz':'Ignacio Ruiz Lluch','Bonaque':'Manuel Bonaque Acevedo','José Carlos':'José Carlos Ramírez Suárez','Iván Benito':'Iván Benito Mancera','A. Carrasco':'Alejandro Jesús Carrasco Navarro','Montero':'Mikel Montero Antúnez','Charbel':'Charbel Anthuan Wehbe González','Néstor Senra':'Néstor Senra Pérez','A. Vela':'Alberto Vela Serrano','Segura':'Juan Antonio Segura García','Ale Marín':'Alejandro Marín Díaz','Izaguirre':'Mateo Izaguirre','Álex Bernal':'Alejandro Bernal Carreras','L. Dasilva':'Luis Dasilva Rodríguez','Aitor G.':'Aitor García Flores','Leandro':'Leandro Martínez Ortiz','Agus Alonso':'Agustín Rafael Alonso Cavallero','Paolo':'Paolo Romero Monge','Pol Prats':'Pol Prats Moragrega','Hugo L.':'Hugo López Vargas','Chavarría':'Matías Nicolás Chavarría','Cortés':'Samuel Cruz Cortés Cortés'}
def recre():
 url='https://www.recreativohuelva.com/la-plantilla/'
 soup=get(url)
 updated=0
 for p in data['clubs']['Recreativo de Huelva']['squad']:
  if p.get('photo'):continue
  targets={norm(p['name']),norm(RECRE_FULL_NAMES.get(p['name'],''))}
  candidates=[]
  for h in soup.find_all(['h2','h3','h4','h5','strong','p']):
   title=re.sub(r'^\\d+\\s*\\.?\\s*','',norm(h.get_text(' ',strip=True)))
   if title not in targets:continue
   photo=find_nearby_image(h,url)
   if photo:candidates.append(photo)
  for img in soup.find_all('img'):
   alt=norm(img.get('alt',''))
   if alt in targets:
    photo=src(img,url)
    if photo:candidates.append(photo)
  if len(set(candidates))==1:
   p['photo']=candidates[0];updated+=1
 print('Recreativo: identificadas',updated,'fotografías nuevas con nombre coincidente')
 return updated
for label,fn in [('Athletic',athletic),('Recreativo',recre)]:
 try:print(label,'fotografías actualizadas:',fn())
 except Exception as exc:print(label,'sin cambios por error de fuente:',str(exc)[:160])
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
