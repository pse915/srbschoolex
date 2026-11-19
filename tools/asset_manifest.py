"""Refresh assets/manifest.json: size, mode and SHA-256 of every PNG. Other manifest fields are kept."""
from pathlib import Path
from PIL import Image
import hashlib,json
r=Path(__file__).resolve().parents[1]/'components/rpg_game/assets';assets=[]
for p in sorted(r.glob('*.png')):
 im=Image.open(p);assets.append(dict(file=p.name,width=im.width,height=im.height,mode=im.mode,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source=p.stem.endswith('-source')))
mp=r/'manifest.json'
manifest=json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else dict(version=3,tileSize=32,characterFrame=[32,48])
manifest['assets']=assets
manifest['schoolFootprint']='school-footprint.json'
manifest['kioskPlan']='kiosk-plan.json'
mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'manifest: {len(assets)} png')
