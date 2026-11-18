"""CS2 Game State Integration: локальный приём игровых событий."""
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT=38477
PHRASE='Bingo, Bango, Bongo, Bish, Bash, Bosh'
TOKEN_PATH=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'JARVISASSISTENT'/'cs2-token.txt'

def token():
    TOKEN_PATH.parent.mkdir(parents=True,exist_ok=True)
    if not TOKEN_PATH.exists():TOKEN_PATH.write_text(secrets.token_hex(24),encoding='ascii')
    return TOKEN_PATH.read_text(encoding='ascii').strip()

def config(secret):
    return '''"JARVIS ace reaction"
{
 "uri" "http://127.0.0.1:%s/"
 "timeout" "3.0"
 "buffer" "0.1"
 "throttle" "0.1"
 "heartbeat" "10.0"
 "auth" { "token" "%s" }
 "data"
 {
  "provider" "1"
  "map" "1"
  "round" "1"
  "player_id" "1"
  "player_state" "1"
  "player_match_stats" "1"
  "bomb" "1"
 }
}
''' % (PORT,secret)

class Detector:
    def __init__(self):self.fired=set();self.lock=threading.Lock()
    def update(self,data):
        player=data.get('player',{});provider=data.get('provider',{});game=data.get('map',{})
        if game.get('phase')!='live':
            if game.get('phase')=='warmup':
                with self.lock:self.fired.clear()
            return False
        if game.get('mode') not in ('competitive','scrimcomp2v2'):return False
        if provider.get('appid')!=730 or not player.get('steamid') or player.get('steamid')!=provider.get('steamid'):return False
        if player.get('activity')!='playing' or data.get('round',{}).get('phase') not in ('live','over'):return False
        kills=player.get('state',{}).get('round_kills',0)
        if not isinstance(kills,int) or kills<5:return False
        number=game.get('round')
        if not isinstance(number,int):return False
        key=(game.get('name'),number,player['steamid'])
        with self.lock:
            if key in self.fired:return False
            if len(self.fired)>128:self.fired.clear()
            self.fired.add(key)
        return True

class AceServer:
    def __init__(self,callback,port=PORT,secret=None,comment_callback=None,state_callback=None,win_callback=None,match_callback=None,kill_callback=None):
        self.last_received=0;self.last_summary={}
        self.state_lock=threading.Lock()
        self.round_wins=0;self.match_wins=0;self.diagnostic_key=None
        owner=self
        self.detector=Detector();secret=secret or token();detector=self.detector
        from game_commentator import Commentator
        commentator=Commentator()
        from round_drops import RoundWins,MatchWins
        wins=RoundWins();matches=MatchWins()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<length<=1048576:self.send_error(413);return
                    data=json.loads(self.rfile.read(length))
                    if not isinstance(data,dict):self.send_error(400);return
                    auth=data.get('auth',{})
                    supplied=auth.get('token','') if isinstance(auth,dict) else ''
                    if not isinstance(supplied,str) or not hmac.compare_digest(supplied,secret):self.send_error(403);return
                    owner.last_received=time.monotonic()
                    owner.last_summary={'phase':data.get('round',{}).get('phase'),'mode':data.get('map',{}).get('mode'),'local_player':data.get('player',{}).get('steamid')==data.get('provider',{}).get('steamid')}
                    with owner.state_lock:
                        if state_callback:state_callback(data)
                        match=matches.update(data)
                        won_round=wins.update(data)
                        if match and match_callback:match_callback()
                        elif won_round and win_callback:win_callback()
                        owner.round_wins += int(won_round)
                        owner.match_wins += int(match)
                        owner.last_summary.update(map_phase=data.get('map',{}).get('phase'),
                            round_number=data.get('map',{}).get('round'),
                            local_team=wins.team, round_wins=owner.round_wins, match_wins=owner.match_wins,
                            win_team=data.get('round',{}).get('win_team'))
                        diagnostic_key=tuple(str(owner.last_summary.get(key)) for key in
                            ('phase','mode','map_phase','round_number','local_player','local_team','round_wins','match_wins'))
                        if diagnostic_key!=owner.diagnostic_key:
                            owner.diagnostic_key=diagnostic_key
                            try:
                                target=TOKEN_PATH.with_name('cs2-status.json')
                                temporary=target.with_suffix('.tmp')
                                temporary.write_text(json.dumps(owner.last_summary,ensure_ascii=False),encoding='utf-8')
                                temporary.replace(target)
                            except OSError:pass
                        ace=detector.update(data)
                        comment=commentator.update(data,quiet=False)
                        if kill_callback and isinstance(comment,list):
                            for event in comment:
                                if event.get('type')=='kill':kill_callback()
                        if ace:callback(PHRASE)
                        if comment and comment_callback:
                            for event in (comment if isinstance(comment,list) else [comment]):
                                if not ace or (isinstance(event,dict) and event.get('type') in ('planted','defused')):
                                    comment_callback(event)
                    self.send_response(200);self.end_headers();self.wfile.write(b'OK')
                except (ValueError,TypeError,AttributeError):self.send_error(400)
            def log_message(self,*args):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def close(self):self.server.shutdown();self.server.server_close()
