"""Screenshots of the main scenes -> tests/shots/*.png"""
import os
from playwright.sync_api import sync_playwright
CH='/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
ROOT=__file__.rsplit('/tests/',1)[0]; URL='file://'+ROOT+'/index.html'; OUT=ROOT+'/tests/shots'; os.makedirs(OUT,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CH,args=['--no-sandbox']); pg=b.new_page(viewport={'width':900,'height':560})
    pg.add_init_script('window.__AEmanual=true;'); pg.goto(URL); pg.wait_for_timeout(500)
    def snap(n,frames=3):
        pg.evaluate(f'for(let i=0;i<{frames};i++){{__AE.step();}} __AE.draw();0'); pg.wait_for_timeout(120); pg.screenshot(path=f'{OUT}/{n}.png')
    snap('1_title')
    pg.evaluate('__AE.startIntro();0')
    for i,n in enumerate(['2_intro_a','3_intro_b']): snap(n,150)
    pg.evaluate('for(let i=0;i<3000&&__AE.state!=="talk";i++){__AE.step()};0'); snap('4_talk',90)
    pg.evaluate('for(let i=0;i<3000&&__AE.state!=="play";i++){__AE.hit.add("act");__AE.step()};0'); snap('5_backyard')
    for n,(x,y) in {'6_lane':(500,505),'7_main':(1000,825),'8_school':(1320,930),'9_front_playground':(1650,1000),'10_back_playground':(1300,1300),'11_court':(1000,1470)}.items():
        pg.evaluate(f'__AE.P.x={x};__AE.P.y={y};0'); snap(n,40)
    f=pg.evaluate('(()=>{const f=__AE.finds.find(f=>f.piece>=0);__AE.P.x=f.x;__AE.P.y=f.y+8;__AE.doSearch(f);return 1})()'); snap('12_found',60)
    b.close()
