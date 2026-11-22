import json, urllib.request, urllib.parse, xml.etree.ElementTree as ET, datetime, pathlib, re, html
ROOT=pathlib.Path(__file__).parent
TOPICS={'Athletic Club':'"Athletic Club" when:7d','Recreativo de Huelva':'"Recreativo de Huelva" OR "Recreativo Huelva" when:7d','Fútbol':'fútbol España when:2d','Baloncesto':'baloncesto ACB NBA when:2d','Voleibol':'voleibol España when:7d','Tenis':'tenis ATP WTA when:2d'}
output={'updated':datetime.datetime.now(datetime.timezone.utc).isoformat(),'topics':{},'errors':{}}
old={}
try: old=json.loads((ROOT/'news.json').read_text(encoding='utf-8')).get('topics',{})
except (OSError,ValueError): pass
for name,q in TOPICS.items():
 url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':'es','gl':'ES','ceid':'ES:es'})
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; PersonalSportsReader/1.0)'})
  with urllib.request.urlopen(req,timeout=25) as response: data=response.read(2_000_000)
  tree=ET.fromstring(data)
  articles=[]
  for item in tree.findall('./channel/item')[:45]:
   title=html.unescape(item.findtext('title','')).strip(); link=item.findtext('link','').strip(); date=item.findtext('pubDate',''); source=item.findtext('source','Google News')
   if not link.startswith('https://'): continue
   articles.append({'id':link,'title':title,'link':link,'date':date,'source':source,'topic':name})
  if not articles: raise ValueError('La fuente no devolvió noticias')
  output['topics'][name]=articles
 except Exception as e:
  output['errors'][name]=str(e)[:160]
  output['topics'][name]=old.get(name,[])
(ROOT/'news.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Actualizadas:', ', '.join(k for k,v in output['topics'].items() if v))
print('Errores:', output['errors'])
