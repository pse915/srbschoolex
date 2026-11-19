"""Original world/content authoring. Run to rebuild deterministic map data and 32px tiles."""
from pathlib import Path
import json, random
import numpy as np
from PIL import Image, ImageDraw,ImageColor
ROOT=Path(__file__).parent/'components/rpg_game'
DATA=ROOT/'data'; ASSETS=ROOT/'assets'
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
random.seed(915)
tile=Image.new('RGBA',(32*12,32)); d=ImageDraw.Draw(tile)
colors=['#8dab78','#dbcdb0','#b6b8b0','#9cc9c7','#cabb9e','#e7ddc8','#997b71','#647d68','#e0c996','#b59da8','#768d77','#ddaa97']
for i,c in enumerate(colors):
 x=i*32;d.rectangle((x,0,x+31,31),fill=c)
 rgb=ImageColor.getrgb(c)
 def shade(v):return tuple(max(0,min(255,k+v)) for k in rgb)+(255,)
 for k in range(12):
  a=x+random.randrange(32);b=random.randrange(32)
  d.line((a,b,min(x+31,a+random.randrange(1,3)),b),fill=shade(5 if k%2 else -4))
 if i in [1,2,4,5,8,9]:
  d.line((x,31,x+31,31),fill=shade(-9));d.line((x+31,0,x+31,31),fill=shade(-7))
 if i in [4,8]:
  for y in (7,15,23):d.line((x,y,x+31,y),fill=shade(-6))
 if i==6:
  for y in (0,8,16,24):
   d.line((x,y,x+31,y),fill='#d2b4a1');s=0 if y%16 else 8
   for a in range(s,32,16):d.line((x+a,y,x+a,y+8),fill='#d2b4a1')
 if i==3:
  for y in (6,19,26):d.line((x+4,y,x+16,y),fill='#c1e0cf')
tile.save(ASSETS/'terrain.png')
teachers=[('1-1','기술썜','일본어/진로활동'),('1-2','기술썜','기술가정'),('1-3','기술썜','음악'),('1-4','기술썜','수학'),('1-5','기술썜','과학'),('2-1','기술썜','한문'),('2-2','기술썜','수학'),('2-3','기술썜','과학'),('2-4','기술썜','역사'),('2-5','기술썜','국어'),('2-6','기술썜','음악/스포츠'),('3-1','기술썜','국어'),('3-2','기술썜','영어'),('3-3','기술썜','사회/역사'),('3-4','기술썜','수학'),('3-5','기술썜','사회'),('3-6','기술썜','도덕')]
# 층별 실 이름·순서는 data/school_layout.json 에서 읽는다 (v6, 교실배치도 기준).
catalog=[]
def new(id,name,w,h,kind='room',floor=None):
 return dict(id=id,name=name,width=w,height=h,kind=kind,floor=floor,spawn=[16,25],tiles=[0]*(w*h),solid=[0]*(w*h),objects=[],portals=[],npcs=[],interactions=[])
def rect(m,x,y,w,h,t,s=0):
 for yy in range(max(0,y),min(m['height'],y+h)):
  for xx in range(max(0,x),min(m['width'],x+w)):
   j=yy*m['width']+xx;m['tiles'][j]=t;m['solid'][j]=s
def obj(m,asset,x,y,w,h,solid=True):
 m['objects'].append(dict(asset=asset,x=x,y=y,w=w,h=h))
 if solid:rect(m,int(x),int(y+h/32-.6),max(1,int(w/32)),1,m['tiles'][min(m['height']-1,int(y+h/32-.6))*m['width']+int(x)],1)
def portal(m,x,y,target,label,arrival):m['portals'].append(dict(x=x,y=y,target=target,label=label,arrival=arrival))
def interaction(m,x,y,label,text,quest=None,clue=None):m['interactions'].append(dict(x=x,y=y,label=label,text=text,quest=quest,clue=clue))
def save(m):
 write(DATA/'maps'/f"{m['id']}.json",m);catalog.append({k:m[k] for k in ('id','name','kind','width','height','spawn')})
def room(id,name,kind,back,arrival,teacher=None,quest=None,seed=0):
 r=random.Random(seed);m=new(id,name,32,32);m['style']=kind;m['spawn']=[16,27]
 rect(m,0,0,32,32,7,1);rect(m,3,4,26,25,4 if kind in ['cafe','home','library'] else 5)
 rect(m,3,3,26,3,6 if kind=='cafe' else 9,1)
 portal(m,16,28,back,'나가기',arrival)
 if kind in ['classroom','science','technology']:obj(m,10,11,4,224,64)
 for x in [5,23]:obj(m,40,x,3,96,96,False)
 obj(m,45,4,9,64,64,False);obj(m,3,25,8,64,96)
 for x in [4,26]:obj(m,11,x,6,48,64)
 if kind=='classroom':
  for y in [11,14,17,20,23]:
   for x in [7,10,13,18,21,24]:obj(m,2,x,y,48,48)
  obj(m,3,4,5,80,96);obj(m,14,23,6,64,64)
 elif kind=='cafe':
  obj(m,12,9,6,224,160)
  for x,y in [(7,14),(12,14),(19,14),(24,14),(7,20),(12,20),(19,20),(24,20)]:obj(m,33,x,y,64,64)
  obj(m,34,10,24,96,64);obj(m,46,20,24,96,64)
 elif kind in ['science','technology']:
  for x,y in [(6,12),(20,12),(6,20),(20,20)]:obj(m,13 if kind=='science' else 14,x,y,96,96)
 elif kind=='library':
  for x in (4,11,21):
   for y in (7,16):obj(m,3,x,y,96,96)
  obj(m,43,13,21,96,96)
 elif kind=='home':
  obj(m,35,5,15,96,160);obj(m,36,19,6,192,96);obj(m,34,18,20,128,96);obj(m,33,11,19,64,64)
 elif kind=='nursery':
  for x,y in [(7,14),(20,14),(10,21)]:obj(m,42,x,y,128,96)
 elif kind=='hospital':
  for x,y in [(6,14),(21,14),(6,21),(21,21)]:obj(m,41,x,y,96,128)
 elif kind=='music':
  obj(m,37,10,8,160,128)
  for x,y in [(7,18),(14,18),(21,18)]:obj(m,43,x,y,96,96)
 elif kind=='art':
  for x,y in [(7,12),(21,12),(7,21),(21,21)]:obj(m,38,x,y,96,128)
 else:
  for x,y in [(6,15),(21,15),(6,22)]:obj(m,14,x,y,96,96)
  obj(m,34,20,22,128,96)
 labels=[('게시판','주민의 시간표에는 일과 휴식, 돌봄이 함께 놓여 있다.'),('자료 책장','주거와 고용의 불안정, 돌봄 부담은 개인의 노력만으로 해결하기 어렵다.'),('생활 기록','서로 다른 가족과 삶의 방식은 존중받아야 한다.'),('창가의 메모','재무·건강·여가·대인 관계는 노후 준비의 네 영역이다.')]
 for j,(label,text) in enumerate(labels):interaction(m,[5,25,5,25][j],[11,11,24,24][j],label,text,clue=quest if j<2 else None)
 if teacher:
  cls,n,subject=teacher;m['npcs'].append(dict(x=16,y=9,name=n,subject=subject,variant=4+teachers.index(teacher),text=f'{subject} 수업의 가상 대화예요. 나에게 소중한 시간을 떠올려 볼까요? 어떤 삶이 우수한지 순위를 매기지는 않아요.'))
  if cls=='1-2':interaction(m,16,11,'미래 다이어리','너의 미래는 정해져 있지 않아. 다이어리를 펼쳐 미래마을로 걸어가 보자.',quest='intro');obj(m,15,15,11,48,48,False)
 elif quest:m['npcs'].append(dict(x=16,y=11,name={'job':'진로 안내자 윤슬','housing':'주민 다온','care':'돌봄 활동가 보람','elder':'주민 은빛','generation':'문화 기획자 하람','policy':'마을 안내자 누리','retire':'미래의 나','budget':'카페지기 소담'}.get(quest,'주민'),variant={'job':32,'housing':34,'care':27,'elder':35,'generation':30,'policy':33,'retire':36,'budget':25}[quest],quest=quest,text='함께 이 동네의 이야기를 바꿔 볼래요?'))
 else:m['npcs'].append(dict(x=16,y=11,name='공간 안내자',variant=21+seed%12,text=f'{name}에서 잠깐 쉬어 가요. 다이어리에 오늘의 생각을 기록할 수 있어요.'))
 save(m)
# ---------------------------------------------------------------------------------------------
# v6: the school grounds and floors come from tools/school_art.py outputs and data/school_layout.json
#     (교실배치도 기준 ┌자 건물). Run `python tools/school_art.py --only all` first.
# ---------------------------------------------------------------------------------------------
import sys,math
sys.path.insert(0,str(Path(__file__).parent/'tools'))
import school_art as SA
FP_PATH=ASSETS/'school-footprint.json'
if not FP_PATH.exists():raise SystemExit('school-footprint.json 이 없습니다. 먼저 python tools/school_art.py --only all 을 실행하세요.')
FP=json.loads(FP_PATH.read_text(encoding='utf-8'))
LAYOUT=SA.load_layout()
SC=FP['displayScale'];PS=FP['projection'];S_,KX_,KY_=PS['s'],PS['kx'],PS['ky']
SO=FP['images']['school']['origin']
ENTRANCE_TILE=(64,50)   # 중앙현관 portal; kept from v5 so spawn [64,52], teacher [62,51], diary [64,51] stay valid
_ex,_ey=SO[0]+S_*(SA.XE-KX_*SA.D),SO[1]+S_*(KY_*SA.D)
OX=round((ENTRANCE_TILE[0]+.5-_ex*SC/32)*32)/32;OY=round((ENTRANCE_TILE[1]-.05-_ey*SC/32)*32)/32
def w2t(x,y,z=0):
 """world meters -> school-map tile coordinates (float)"""
 return OX+(SO[0]+S_*(x-KX_*y))*SC/32,OY+(SO[1]+S_*(KY_*y-z))*SC/32
def t2w(tx,ty):
 """school-map tile coordinates -> world ground point (z=0)"""
 y=((ty-OY)*32/SC-SO[1])/(S_*KY_);return ((tx-OX)*32/SC-SO[0])/S_+KX_*y,y
def wtile(x,y,z=0):
 a,b=w2t(x,y,z);return int(math.floor(a)),int(math.floor(b))
def image_obj(m,name,sort=None,ground=False):
 """place a school_art image so its world origin lands on w2t(0,0,0); integer 2x scale"""
 meta=FP['images'][name];o=meta['origin'];ox,oy=w2t(0,0,0)
 d=dict(asset=-1,image=name,x=round((ox-o[0]*SC/32)*32)/32,y=round((oy-o[1]*SC/32)*32)/32,w=meta['size'][0]*SC,h=meta['size'][1]*SC,role='landmark')
 if sort is not None:d['sortY']=sort
 if ground:d['ground']=True
 m['objects'].append(d);return d
def in_box(x,y,b,pad=0):return b[0][0]-pad<=x<=b[1][0]+pad and b[0][1]-pad<=y<=b[1][1]+pad
SITE=FP['site'];BLD=FP['building']
def in_building(x,y):return in_box(x,y,[BLD['main'][0],BLD['main'][2]]) or in_box(x,y,[BLD['west'][0],BLD['west'][2]])
school=new('school','서라벌여중 · 교정',128,128,'outside');school['spawn']=[64,52]
W_,H_=school['width'],school['height']
# ground: grass(0) everywhere, sand(SA.TILE['sand']) where a tile lies fully inside the field
for ty in range(H_):
 for tx in range(W_):
  cs=[t2w(tx+a,ty+b) for a in (0,1) for b in (0,1)];x,y=t2w(tx+.5,ty+.5)
  if all(in_box(px,py,SITE['field']) for px,py in cs):school['tiles'][ty*W_+tx]=SA.TILE['sand']
  if in_building(x,y):j=ty*W_+tx;school['tiles'][j]=SA.TILE['paving'];school['solid'][j]=1
reserved=set()
def reserve(tx,ty,r=0):
 for yy in range(ty-r,ty+r+1):
  for xx in range(tx-r,tx+r+1):reserved.add((xx,yy))
def paint(tx,ty,t=None,s=None):
 if 0<=tx<W_ and 0<=ty<H_:
  j=ty*W_+tx
  if t is not None:school['tiles'][j]=t
  if s is not None:school['solid'][j]=s
# building sprite: one object; sorted at the main south face so the playground side draws in front of it
image_obj(school,'school-ground',ground=True)
face_row=w2t(SA.XE,SA.D)[1]
image_obj(school,'school',sort=face_row)
for tx in range(W_):
 for ty in range(H_):
  x,y=t2w(tx+.5,ty+.5)
  if in_building(x,y):reserve(tx,ty,1)
# sprite bounding box is reserved for trees (roof and walls are drawn there)
_sx,_sy=w2t(0,0,0);_m=FP['images']['school']
for ty in range(int(OY),int(OY+_m['size'][1]*SC/32)+1):
 for tx in range(int(OX),int(OX+_m['size'][0]*SC/32)+1):reserved.add((tx,ty))
# hedges and pines drawn in the sprite are solid at their base
for p in FP['planting']:
 tx,ty=wtile(p['x'],p['y'])
 for dx in ((-1,0,1) if p['kind']=='hedge' else (0,)):paint(tx+dx,ty,s=1)
# entrance: two white columns are solid, the steps between them are open
for c in FP['entrance']['columns']:
 tx,ty=wtile((c[0]+c[2])/2,(c[1]+c[3])/2);paint(tx,ty,s=1)
ex_,ey_=ENTRANCE_TILE
for xx in range(ex_-1,ex_+2):paint(xx,ey_,s=0)
portal(school,ex_,ey_,'floor1','중앙현관',None)
# 조회대: granite platform you can walk onto (steps on its south side)
pf=SITE['platform'];pcx,pcy=wtile((pf[0][0]+pf[1][0])/2,(pf[0][1]+pf[1][1])/2)
for ty in range(H_):
 for tx in range(W_):
  x,y=t2w(tx+.5,ty+.5)
  if in_box(x,y,pf):paint(tx,ty,t=SA.TILE['paving'],s=0);reserved.add((tx,ty))
interaction(school,pcx,pcy,'조회대','화강석 조회대에 올라섰다. 아침 조회 때 선생님이 서는 자리에서 운동장이 한눈에 보인다.');school['interactions'][-1]['keep']=True
# 급수대 (north-west corner of the field)
fo=SITE['fountain']
image_obj(school,'school-fountain')
for ty in range(H_):
 for tx in range(W_):
  x,y=t2w(tx+.5,ty+.5)
  if in_box(x,y,fo,0.3):paint(tx,ty,s=1);reserve(tx,ty,1)
ftx,fty=wtile((fo[0][0]+fo[1][0])/2,fo[1][1]+2.5)
interaction(school,ftx,fty,'급수대','운동장 북서쪽 급수대. 체육 시간이 끝나면 줄이 길어진다.');school['interactions'][-1]['keep']=True
# 목련관 (south-east detached hall: 1층 식생활관·조리실, 2층 강당)
an=SITE['annex']
image_obj(school,'school-annex',sort=w2t(an[1][0],an[1][1])[1])
for ty in range(H_):
 for tx in range(W_):
  x,y=t2w(tx+.5,ty+.5)
  if in_box(x,y,an):paint(tx,ty,t=SA.TILE['paving'],s=1)
  if in_box(x,y,an,3):reserved.add((tx,ty))
_ax,_ay=w2t(an[0][0],an[0][1],SA.ANNEX_H+2);_bx,_by=w2t(an[1][0],an[1][1])
for ty in range(int(_ay),int(_by)+2):
 for tx in range(int(_ax)-8,int(_bx)+2):reserved.add((tx,ty))
adx,ady=wtile(SITE['annexDoor'][0],SITE['annexDoor'][1]+2.0)
interaction(school,adx,ady,'목련관','목련관 입구. 1층은 식생활관·조리실, 2층은 강당(목련관)이다.');school['interactions'][-1]['keep']=True
# 정문 (east) with the portal to the future village, 후문 (north)
ge=SITE['gateEast'];gcx,gcy=wtile(ge[0][0]+1.5,(ge[0][1]+ge[1][1])/2)
image_obj(school,'school-gate-east',sort=w2t(ge[1][0],ge[1][1]+1.2)[1])
gn=SITE['gateNorth'];ncx,ncy=wtile((gn[0][0]+gn[1][0])/2,gn[0][1]+1.5)
image_obj(school,'school-gate-north',sort=w2t(gn[0][0],gn[0][1]+0.6)[1])
for (gx0,gy0),(gx1,gy1),along in ((ge[0],ge[1],'y'),(gn[0],gn[1],'x')):
 pts=[]
 if along=='y':pts=[(gx0,gy0-v) for v in np.arange(0,10.5,0.5)]+[(gx0,gy1+v) for v in np.arange(0,10.5,0.5)]
 else:pts=[(gx0-v,gy0) for v in np.arange(0,10.5,0.5)]+[(gx1+v,gy0) for v in np.arange(0,10.5,0.5)]
 for x,y in pts:
  tx,ty=wtile(x,y);paint(tx,ty,s=1);reserve(tx,ty,2)
reserve(gcx,gcy,3);reserve(ncx,ncy,3)
# paths (보도블럭): entrance -> 정문, and 후문 -> around the east end -> 정문 path
def path_line(a,b,w=2):
 (x0,y0),(x1,y1)=a,b
 for tx in range(min(x0,x1),max(x0,x1)+1):
  for ty in range(min(y0,y1),max(y0,y1)+1):
   for k in range(w):
    xx,yy=(tx,ty+k) if y0==y1 else (tx+k,ty)
    j=yy*W_+xx
    if not school['solid'][j] or (xx,yy) in ((gcx,gcy),(ncx,ncy)):paint(xx,yy,t=SA.TILE['paving'],s=0)
    reserve(xx,yy,1)
east_end_x=wtile(SA.L1+3,SA.D)[0]
path_line((ex_,ey_+1),(ex_,gcy));path_line((ex_,gcy),(gcx,gcy))
north_row=wtile(SA.L1,-3)[1]
path_line((ncx,ncy),(ncx,north_row));path_line((min(ncx,east_end_x),north_row),(max(ncx,east_end_x),north_row))
path_line((east_end_x,north_row),(east_end_x,gcy))
portal(school,gcx,gcy,'town','미래마을로',[128,116])
interaction(school,ncx,ncy+1,'후문','학교 북쪽 후문. 등굣길에 이 문으로 들어오는 학생도 많다.');school['interactions'][-1]['keep']=True
_tcx,_tcy=wtile(*SITE['track']['center'])
interaction(school,_tcx,_tcy,'운동장','두 동이 감싸 안은 모래 운동장. 트랙 한 바퀴를 돌며 숨을 고른다.');school['interactions'][-1]['keep']=True
obj(school,15,64,50,64,64,False)   # 빛나는 다이어리 (interaction is added in world_v2)
# trees around the grounds, never on the building, field, paths, gates or the hall
for j in range(260):
 x=random.randrange(3,123);y=random.randrange(3,122)
 cx,cy=x+1,y+3
 if any((xx,yy) in reserved for xx in range(x,x+3) for yy in range(y+1,y+4)):continue
 fx,fy=t2w(cx+.5,cy+.5)
 if in_box(fx,fy,SITE['field'],4):continue
 obj(school,j%2,x,y,96,128)
# landmarks used by the game/ending code (instead of hard-coded coordinates)
def rt(v):return [round(v[0],2),round(v[1],2)]
school['landmarks']=dict(
 entrance=list(ENTRANCE_TILE),
 shutters=[rt(w2t(SA.XE-16,SA.D,3.0)),rt(w2t(SA.XE+30,SA.D,3.0))],
 roof=rt(w2t(SA.D+14,SA.D*0.35,SA.H4))+[round((SA.L1-SA.D-24)*S_*SC/32,2)],
 plaza=[ex_-7,ey_+2,15],
 learning=rt(w2t(SA.L1-14,SA.D,0.0)),
 care=[ex_-10,ey_+1],
 repair=[ex_-4,ey_+3],
 students=[ex_-3,ey_+3],
 benches=[[ex_-14,ey_+3],[ex_-10,ey_+3],[ex_+9,ey_+4],[ex_+13,ey_+4]],
 planters=[[ex_-5,ey_+1],[ex_+3,ey_+1]],
 access=[ex_+1,ey_],garden=[ex_-8,ey_+5],schoolLearning=[ex_-6,ey_+3],schoolBooks=[ex_+4,ey_+4])
# facade points (windows on the south face / west wing east face, roof spots) for crisis.js damage overlays
_fac=[]
for _z in (2.6,6.2,9.8,13.4):
 for _x in np.arange(SA.D+5,SA.L1-3,9.0):
  if not (abs(_x-SA.XE)<9 and _z<7):_fac.append(rt(w2t(_x,SA.D,_z))+['window'])   # not behind the entrance canopy
 for _y in np.arange(SA.D+6,SA.ARCH_Y0-2,8.0):_fac.append(rt(w2t(SA.D,_y,_z))+['window'])
for _x in np.arange(SA.D+8,SA.L1-6,14.0):_fac.append(rt(w2t(_x,SA.D*0.5,SA.H4))+['roof'])
random.Random(6).shuffle(_fac)
school['landmarks']['facade']=_fac
_vx,_vy=w2t(0,0,0)
school['endingView']=dict(x=int(OX)-2,y=int(OY)-3,w=80,h=45)
# minimap: building footprint in brick colour so the ┌ reads at a glance (keys: s=solid / w=walkable + tile index)
school['minimapColors']={f"s{SA.TILE['paving']}":'#a2584a',f"w{SA.TILE['paving']}":'#c9c2b2',f"w{SA.TILE['sand']}":'#e2d6b8','w0':'#7f9f73','s0':'#4d6650'}
school['floorplanSource']='data/school_layout.json'
save(school)
# ---------------- floors 1~4 (┌자 복도, 1 tile = 1 m) ----------------
FMG=4;FW=FMG+int(SA.L1)+FMG;FH_=FMG+int(SA.D+SA.L2)+6
CAT_TILE={'classroom':SA.TILE['room_classroom'],'office':SA.TILE['room_office'],'special':SA.TILE['room_special'],'care':SA.TILE['room_care'],'service':SA.TILE['room_service'],'restroom':SA.TILE['restroom']}
def mrect(m,r,t,s):
 x0,y0,x1,y1=[FMG+int(round(v)) for v in r];rect(m,x0,y0,x1-x0,y1-y0,t,s);return x0,y0,x1,y1
def room_type(name,t):
 return 'classroom' if t else 'science' if '과학' in name else 'technology' if any(s in name for s in ['기술','컴퓨터','정보']) else 'library' if any(s in name for s in ['도서','자료','글빛']) else 'music' if '음악' in name else 'art' if '미술' in name else 'hospital' if '보건' in name else 'home' if '가정' in name else 'office'
CORR_ROW=FMG+int(SA.OUTER_W+SA.CORR_W/2)        # main corridor middle row (12)
CORR_COL=CORR_ROW                               # west corridor middle column (12)
def corridor_tile(e,offset=0):
 """tile on the corridor in front of item e (door side), and the middle-of-corridor arrival tile"""
 if e['wing'] in ('main','corner'):
  cx=FMG+int(math.floor(e['door'][0]))+offset;row=FMG+int(SA.OUTER_W) if e['side']=='outer' else FMG+int(SA.OUTER_W+SA.CORR_W)-1
  return (cx,row),(cx,CORR_ROW)
 cy=FMG+int(math.floor(e['door'][1]))+offset;col=FMG+int(SA.OUTER_W) if e['side']=='outer' else FMG+int(SA.OUTER_W+SA.CORR_W)-1
 return (col,cy),(CORR_COL,cy)
def door_tile(e):
 (px,py),_=corridor_tile(e)
 if e['wing'] in ('main','corner'):return px,py+(1 if e['side']=='inner' else -1)
 return px+(1 if e['side']=='inner' else -1),py
PLANS=SA.all_plans(LAYOUT)
NFLOORS=len(PLANS)
floor_rooms={}
for f,plan in PLANS.items():
 m=new(f'floor{f}',f'서라벌여중 · {f}층',FW,FH_,'floor',f)
 rect(m,0,0,FW,FH_,7,1)
 m['layout']='data/school_layout.json'
 for r in plan['corridors']:mrect(m,r,SA.TILE['corridor'],0)
 stairs={}
 for e in plan['items']:
  k=e['kind'];r=e['rect']
  if k=='gap':mrect(m,r,SA.TILE['wall'],1);continue
  if k=='void':mrect(m,r,SA.TILE['void'],1);continue
  if k=='lobby':
   x0,y0,x1,y1=mrect(m,r,SA.TILE['lobby'],0);cx=FMG+int(math.floor(e['door'][0]))
   m['spawn']=[cx,y0+3];portal(m,cx,y1-1,'school','교정으로',[ENTRANCE_TILE[0],ENTRANCE_TILE[1]+2])
   continue
  if k in ('stair','ev'):
   mrect(m,r,SA.TILE['stair' if k=='stair' else 'ev'],1);stairs[e['id']]=e;continue
  # rooms
  x0,y0,x1,y1=mrect(m,r,CAT_TILE.get(e.get('category'),SA.TILE['room_service']),1)
  if e['wing']=='main' and x1-x0>=3:rect(m,x0,y0,1,y1-y0,SA.TILE['wall'],1)
  if e['wing']=='west' and y1-y0>=3:rect(m,x0,y0,x1-x0,1,SA.TILE['wall'],1)
  dx,dy=door_tile(e);rect(m,dx,dy,1,1,SA.TILE['door'],1)
  (px,py),arr=corridor_tile(e)
  rid=e['id'];t=next((t for t in teachers if t[0]==e['name']),None) if e.get('category')=='classroom' else None
  label=SA.room_label(e);portal(m,px,py,rid,label,[16,26])
  if e['wing']=='main' and e['side']=='outer':obj(m,5,px-1,py-2,64,64,False)
  room(rid,label,room_type(e['name'],t),m['id'],list(arr),t,seed=f*100+int(rid.split('-')[-1]))
  floor_rooms.setdefault(f,[]).append(rid)
 for sid,e in stairs.items():
  dests=[d for d in range(1,NFLOORS+1) if d!=f and sid in {i['id'] for i in PLANS[d]['items']} and (e['kind']=='ev' or abs(d-f)==1)]
  offs={1:[0],2:[-1,1],3:[-1,0,1]}[len(dests)]
  for d,o in zip(dests,offs):
   (px,py),_=corridor_tile(e,o);de=next(i for i in PLANS[d]['items'] if i['id']==sid);_,arr=corridor_tile(de,o)
   portal(m,px,py,f'floor{d}',f"{e['name']} · {d}층"+('으로' if e['kind']=='stair' else ''),list(arr))
 if f!=1:m['spawn']=list(corridor_tile(stairs['stair-centralStair'])[1])
 save(m)
# arrival for the school's 중앙현관 portal = just inside the floor-1 lobby
_lobby=next(e for e in PLANS[1]['items'] if e['kind']=='lobby')
school['portals'][0]['arrival']=[FMG+int(math.floor(_lobby['door'][0])),FMG+int(SA.D)-2]
write(DATA/'maps'/'school.json',school)
town=new('town','미래마을 · 느린 내일의 거리',256,256,'town');town['spawn']=[128,122]
rect(town,0,0,256,256,0)
for y in (48,92,132,180,222):rect(town,12,y,232,7,1);rect(town,12,y+3,232,1,2)
for x in (40,84,124,170,216):rect(town,x,10,7,236,1)
rect(town,108,110,42,36,2);rect(town,188,0,9,256,3,1)
for y in (48,92,132,180,222):rect(town,187,y,11,7,4)
obj(town,8,125,124,128,128);interaction(town,128,130,'광장의 오래된 편지','세대가 함께 쓰는 공간에는 여러 목소리가 필요하다.',clue='generation')
buildings=[('cafe','내일의 카페',6,115,109,'cafe','budget'),('career','직업상담센터',7,134,108,'technology','job'),('rental','청년 임대주택',7,67,78,'home','housing'),('care','돌봄센터',7,151,120,'home','care'),('welfare','노인복지관',7,102,149,'library','elder'),('culture','문화공방',6,151,151,'library','generation'),('hall','마을회관',7,113,165,'technology','policy'),('home','미래의 집',6,68,161,'home','retire'),('hospital','병원',7,202,118,'science',None),('library','마을도서관',7,204,164,'library',None),('bakery','햇살 빵집',6,56,117,'cafe',None),('shop','골목 소품점',6,23,75,'cafe',None),('office','함께 일하는 사무실',7,99,76,'technology',None),('nursery','어린이집',6,152,76,'home',None),('shared','이웃 공동주거',7,61,206,'home',None),('mart','동네 편의점',6,204,77,'cafe',None)]
for j,(id,name,asset,x,y,kind,q) in enumerate(buildings):
 if id in ['care','nursery']:kind='nursery'
 if id=='hospital':kind='hospital'
 rect(town,x-1,y+5,9,5,1);obj(town,16+j,x,y,224,224);portal(town,x+3,y+7,id,name,[16,26]);room(id,name,kind,'town',[x+3,y+9],quest=q,seed=j)
 rect(town,x+1,y+1,5,5,0,1)
town['npcs']=[dict(x=122+j%4*5,y=118+j//4*9,name=['산책하는 이웃','청년 주민','공방 수강생','마을 정원사'][j%4],variant=25+j,text='이 마을의 제도와 환경도 우리의 선택에 영향을 줘요.') for j in range(12)]
for j in range(1300):
 x=random.randrange(4,250);y=random.randrange(4,250)
 if any(abs(x-bx)<10 and abs(y-by)<11 for _,_,_,bx,by,_,_ in buildings):continue
 if town['tiles'][y*256+x]!=0 or 104<x<153 and 104<y<149:continue
 obj(town,j%2,x,y,96,128)
for x,y in [(115,121),(140,121),(116,137),(142,137),(178,135),(178,177)]:obj(town,9,x,y,96,64)
for x,y in [(111,117),(142,114),(112,129),(140,130)]:obj(town,1,x,y,96,128)
for x,y in [(119,117),(135,117),(120,131),(136,131)]:obj(town,47,x,y,32,96);obj(town,46,x+1,y+2,64,48)
portal(town,128,111,'school','학교로 돌아가기',[gcx-2,gcy]);save(town)
write(DATA/'catalog.json',catalog);write(DATA/'teachers.json',[dict(classroom=a,name=b,subject=c,fictionalAppearance=True) for a,b,c in teachers])
quests=[
 dict(id='job',title='나에게 맞는 일',place='career',concept='고용 불안정 · 청년 일자리',story='채용 공고는 많지만 계약 기간과 근무 시간이 모두 다르다. 게시판과 책장을 살펴보고 나의 조건을 정해 보자.',choices=[['배우며 일하는 기술 직무','학습 기회가 늘고 당분간 여유 시간은 줄어든다.',{'money':8,'time':-7,'leisure':-3},'기술을 배우는 일'],['지역 협동조합의 일','소득의 상승 폭은 작지만 주민과 함께 결정할 수 있다.',{'money':3,'relations':8,'community':9},'협동조합의 일'],['유연근무가 가능한 일','일정 조정이 쉽다. 안정적인 계약인지 확인하는 과정도 필요하다.',{'time':8,'money':2,'care':5},'유연근무의 일']]),
 dict(id='housing',title='나의 첫 번째 집',place='rental',concept='주거 부담 · 사회적 지원',story='집을 구하는 다온은 보증금과 통근 시간을 함께 고민한다. 임대 안내와 생활 자료를 조사하자.',choices=[['지원 임대주택','주거비 부담이 줄지만 입주 조건과 위치를 확인해야 한다.',{'money':9,'time':-3,'support':8},'지원 임대주택'],['공동주거','공용 공간 규칙을 함께 정하고 생활비를 나눈다.',{'money':6,'relations':8,'time':-2},'공동주거'],['작은 독립주택','혼자 쉬는 공간을 확보하고 더 많은 주거비를 배정한다.',{'money':-8,'leisure':8,'time':3},'독립주거']]),
 dict(id='budget',title='카페의 바쁜 오후',place='cafe',concept='경제생활 · 시간과 소비',story='카페지기 소담이 갑자기 바쁜 시간을 맞았다. 근무표와 생활비 자료를 확인하고 오늘의 오후를 선택하자.',choices=[['짧은 교대 근무를 돕는다','보수를 얻고 쉬려던 시간 일부를 사용한다.',{'money':8,'time':-6,'relations':3},'수입과 휴식 나누기'],['교대 시간을 함께 재설계한다','협의 시간이 필요하지만 앞으로 쉴 시간이 생긴다.',{'time':6,'community':6,'money':-2},'지속 가능한 시간표'],['계획한 휴식을 지킨다','소비 한도를 정하고 친구와 여가를 보낸다.',{'money':-4,'health':5,'leisure':9},'계획된 소비와 휴식']]),
 dict(id='care',title='겹쳐 버린 두 시간표',place='care',concept='일·가정 양립 · 평등한 돌봄',story='주민의 근무와 가족 돌봄 시간이 겹쳤다. 돌봄을 한 사람에게만 맡기지 않는 방법을 찾아보자.',choices=[['공공 돌봄과 유연근무를 연결한다','서비스 운영 시간과 이용 조건을 먼저 확인한다.',{'care':14,'support':9,'time':4},'공공 돌봄 연결'],['가족·이웃과 공평한 역할표를 만든다','동의한 참여자들이 가능한 시간을 나눈다. 공적 지원도 계속 필요하다.',{'care':8,'relations':10,'time':-4},'평등한 역할 분담'],['마을의 저녁 돌봄 확대를 제안한다','당장의 공백은 별도 지원으로 메우고 제도 개선을 요청한다.',{'care':6,'community':12,'support':7},'돌봄 운영 시간 개선']]),
 dict(id='elder',title='집 밖으로 이어지는 길',place='welfare',concept='고령 친화 환경 · 의료와 돌봄',story='은빛 주민은 버스 정류장 계단 때문에 모임에 자주 오지 못한다. 생활 기록과 이용 안내를 확인하자.',choices=[['이동 지원과 안전한 길을 연결한다','외출 선택지가 늘어난다. 교통 운영비도 함께 필요하다.',{'health':7,'relations':6,'support':10},'이동 지원'],['방문 건강관리와 모임을 연결한다','의료 접근과 사회적 관계를 함께 고려한다.',{'health':12,'care':6,'relations':4},'건강·관계 연결'],['주민과 접근성 개선 지도를 만든다','당사자의 의견을 바탕으로 마을 개선에 참여한다.',{'community':12,'relations':8,'time':-4},'접근성 지도']]),
 dict(id='generation',title='모두의 오후 공원',place='culture',concept='세대 간 이해와 협력',story='조용히 쉬고 싶은 주민과 공연 연습을 하고 싶은 주민이 같은 공간을 원한다. 서로의 이용 기록을 살펴보자.',choices=[['시간을 나누어 사용한다','시간표를 정기적으로 다시 협의한다.',{'time':4,'relations':8,'leisure':6},'시간을 나누는 공원'],['조용한 쉼터와 활동 구역을 나눈다','공간 배치와 접근성에 예산을 배정한다.',{'money':-4,'leisure':10,'community':8},'함께 쓰는 공원'],['세대가 함께하는 작은 행사를 연다','참여는 자유롭게 두고 조용한 시간도 보장한다.',{'relations':12,'community':8,'time':-3},'세대 협력 행사']]),
 dict(id='policy',title='한정된 예산, 함께 정하는 우선순위',place='hall',concept='사회적 책임 · 가족 친화 문화',story='이번 마을 예산으로 모든 사업을 동시에 확대하기는 어렵다. 의견 자료를 조사하고 먼저 추진할 조합을 정하자.',choices=[['주거 지원 + 청년 일자리','경제적 독립을 돕는다. 돌봄과 의료는 다음 예산에서도 논의해야 한다.',{'money':10,'support':10,'community':4},'주거·일자리 우선'],['돌봄 + 이동·의료 접근','일과 생활의 조화, 고령 주민의 일상을 지원한다.',{'care':10,'health':8,'support':10},'돌봄·의료 우선'],['문화·여가 + 세대 협력','관계와 참여 기회를 넓힌다. 주거 부담 해결도 계속 필요하다.',{'leisure':12,'relations':10,'community':10},'문화·협력 우선']]),
 dict(id='retire',title='미래의 내가 보내온 편지',place='home',concept='노후 준비: 재무·건강·여가·대인 관계',story='시간이 흘러 미래의 집에 도착했다. 네 영역의 기록을 살펴보고 앞으로 이어 갈 계획을 정하자.',choices=[['네 영역을 고르게 돌보는 주간 계획','작은 저축, 산책, 취미, 만남을 일상에 배치한다.',{'money':4,'health':4,'leisure':4,'relations':4},'작게 꾸준히 준비하기'],['사회적 지원과 이웃 관계를 먼저 찾는다','혼자 감당하기 어려운 부분은 상담과 지역 자원을 연결한다.',{'support':10,'relations':8,'care':5},'연결하며 준비하기'],['새로운 활동을 배우며 계획을 조정한다','지금의 상황과 관심에 맞추어 미래 계획을 다시 쓴다.',{'leisure':10,'health':4,'time':-3,'community':5},'배우며 다시 설계하기']])]
write(DATA/'quests.json',quests)
_mp=ASSETS/'manifest.json';_man=json.loads(_mp.read_text(encoding='utf-8')) if _mp.exists() else dict(tileSize=32,characterFrame=[32,48],assets=[])
_man.update(mapCount=len(catalog),schoolPlan='data/school_layout.json (교실배치도 기준 ┌자; 4층 서쪽 끝 구역 confirmed:false)',schoolArt='tools/school_art.py (code pixel art; school.png, school-ruin.png, school-hero.png, floor-plan-1~4, props)')
_man.pop('referenceComparison',None);_mp.write_text(json.dumps(_man,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Built {len(catalog)} maps and {len(teachers)} teacher records')

from world_v2 import upgrade
upgrade(ROOT)
