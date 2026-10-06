"""Play-test bot for Alien in the Backyard.
1) BFS: every find, George and the ship-side are reachable from the start on foot.
2) Full scripted playthrough walking real paths (step by step): intro, school, find 6 pieces,
   back to George, finale, ending.  3) Save/continue.  4) Real-time keyboard walk."""
import sys, json
from playwright.sync_api import sync_playwright
CH='/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
URL='file://'+__file__.rsplit('/tests/',1)[0]+'/index.html'
JS="""
window.mgr=function(){
  const A=__AE, S=4, W=Math.ceil(A.WW/S), H=Math.ceil(A.WH/S);
  window.pathTo=function(tx,ty){
    const sx=Math.round(A.P.x/S), sy=Math.round(A.P.y/S), prev=new Int32Array(W*H).fill(-2);
    const q=[sy*W+sx]; prev[q[0]]=-1; let best=-1;
    const gx=Math.round(tx/S), gy=Math.round(ty/S);
    for(let h=0;h<q.length;h++){ const c=q[h], x=c%W, y=(c-x)/W;
      if(Math.abs(x-gx)<=2&&Math.abs(y-gy)<=2){ best=c; break; }
      for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){ const nx=x+dx,ny=y+dy; if(nx<0||ny<0||nx>=W||ny>=H) continue; const n=ny*W+nx; if(prev[n]!==-2) continue;
        const X=nx*S,Y=ny*S; if(!(A.canStand(X,Y)&&A.canStand(X+2,Y)&&A.canStand(X-2,Y)&&A.canStand(X,Y+2)&&A.canStand(X,Y-2))) continue; prev[n]=c; q.push(n); } }
    if(best<0) return null; const out=[]; for(let c=best;c>=0;c=prev[c]) out.push([(c%W)*S,Math.floor(c/W)*S]); return out.reverse();
  };
  return true;
};
window.walk=function(tx,ty,max){
  const A=__AE; let p=pathTo(tx,ty), f=0, i=0; if(!p) return {fail:'no path'};
  while(f<max){ f++;
    if(f%240===0){ p=pathTo(tx,ty); i=0; if(!p) return {fail:'lost path'}; }
    if(i>=p.length-1) break;
    const [px,py]=p[Math.min(i+1,p.length-1)]; const dx=px-A.P.x, dy=py-A.P.y;
    A.down.left=dx<-1; A.down.right=dx>1; A.down.up=dy<-1; A.down.down=dy>1;
    if(Math.hypot(dx,dy)<=2.5) i++;
    A.step();
    if(A.state!=='play') break;
  }
  A.down.left=A.down.right=A.down.up=A.down.down=false;
  return {ok:i>=p.length-1,frames:f};
};
window.skip=function(max){ const A=__AE; let n=0; while(['intro','talk','found','finale','title'].includes(A.state)&&n<max){ n++; A.hit.add('act'); A.hit.add('start'); A.step(); } return {n,state:A.state}; };
;0
"""
fails=[]
def chk(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CH,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
    pg=b.new_page(viewport={'width':900,'height':600}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None)
    pg.add_init_script('window.__AEmanual=true;')
    pg.goto(URL); pg.wait_for_timeout(500); pg.evaluate(JS); pg.evaluate('mgr();0')
    pg.evaluate('__AE.startIntro();0'); r=pg.evaluate('skip(5000)'); chk(r['state']=='play','intro->play '+json.dumps(r))
    # 1 reachability
    info=pg.evaluate("({finds:__AE.finds.map(f=>[f.id,f.type,f.x,f.y,f.piece,f.zone]),g:[__AE.GEORGE.x,__AE.GEORGE.y]})")
    bad=pg.evaluate("""(()=>{const A=__AE,S=4,W=Math.ceil(A.WW/S),H=Math.ceil(A.WH/S),seen=new Uint8Array(W*H),q=[Math.round(A.P.y/S)*W+Math.round(A.P.x/S)];seen[q[0]]=1;
      for(let h=0;h<q.length;h++){const c=q[h],x=c%W,y=(c-x)/W;for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const nx=x+dx,ny=y+dy;if(nx<0||ny<0||nx>=W||ny>=H)continue;const n=ny*W+nx;if(seen[n])continue;const X=nx*S,Y=ny*S;if(!(A.canStand(X,Y)&&A.canStand(X+2,Y)&&A.canStand(X-2,Y)&&A.canStand(X,Y+2)&&A.canStand(X,Y-2)))continue;seen[n]=1;q.push(n);}}
      const bad=[];for(const f of A.finds){let ok=false;for(let dy=-14;dy<=20&&!ok;dy+=4)for(let dx=-14;dx<=14&&!ok;dx+=4){const x=Math.round((f.x+dx)/S),y=Math.round((f.y+dy)/S);if(x>=0&&y>=0&&x<W&&y<H&&seen[y*W+x])ok=true;}if(!ok)bad.push([f.id,f.type,f.x,f.y]);}
      const g=A.GEORGE;let gok=false;for(let dy=-30;dy<=40;dy+=4)for(let dx=-30;dx<=30;dx+=4){const x=Math.round((g.x+dx)/S),y=Math.round((g.y+dy)/S);if(seen[y*W+x])gok=true;} if(!gok)bad.push('george');
      return bad;})()""")
    chk(not bad,f"all {len(info['finds'])} finds reachable {bad[:5]}")
    # 2 playthrough: walk to school first (checks the route), then each piece
    pieces=[f for f in info['finds'] if f[4]>=0]; chk(len(pieces)==6,'6 pieces placed')
    pieces.sort(key=lambda f:(f[5],f[2]))
    for fid,ty,x,y,pc,z in pieces:
        r=pg.evaluate(f'walk({x},{y+8},6000)'); 
        near=pg.evaluate('!!__AE.nearestFind()')
        pg.evaluate('__AE.hit.add("act");__AE.step();0')
        st=pg.evaluate('__AE.state'); chk(st=='found',f'piece {pc} in {ty}@{z} found ({json.dumps(r)}, near={near}, state={st})')
        pg.evaluate('skip(600)')
    chk(pg.evaluate('__AE.allFound()'),'all found')
    r=pg.evaluate('skip(3000)'); 
    # back to George
    r=pg.evaluate(f"walk({info['g'][0]},{info['g'][1]+30},9000)"); print('walk home',r)
    pg.evaluate('skip(5)')
    st=pg.evaluate('__AE.state'); print('state near George',st)
    if st=='play': pg.evaluate('__AE.hit.add("act");__AE.step();0'); st=pg.evaluate('__AE.state')
    chk(st in('talk','finale'),'George finale dialog '+st)
    r=pg.evaluate('skip(4000)'); print(r)
    seen=set(); 
    for i in range(3000):
        s=pg.evaluate('__AE.step();__AE.state'); seen.add(s)
        if s=='ending': break
        pg.evaluate('__AE.hit.add("act");0')
    chk('ending' in seen,'reached ending '+str(seen))
    # 3 save/continue
    pg.reload(); pg.wait_for_timeout(400); pg.evaluate(JS); pg.evaluate('mgr();0')
    saved=pg.evaluate('JSON.stringify(__AE.saved)'); print('saved',saved[:120]); chk(saved!='null','save exists')
    # 4 real time keyboard
    pg.add_init_script('0'); pg.evaluate('window.__AEmanual=false;0')
    pg.evaluate('__AE.startIntro();0'); pg.evaluate('window.__AEmanual=true;0'); pg.evaluate('skip(5000)'); pg.evaluate('window.__AEmanual=false;0')
    x0=pg.evaluate('__AE.P.x'); pg.keyboard.down('ArrowRight'); pg.wait_for_timeout(800); pg.keyboard.up('ArrowRight'); x1=pg.evaluate('__AE.P.x')
    chk(x1>x0+20,f'keyboard walk {x0}->{x1}')
    errs=[e for e in errs if 'Failed to load resource' not in e]; chk(not errs,'no console errors '+str(errs[:3]))
    b.close()
print('FAILS',fails); sys.exit(1 if fails else 0)
