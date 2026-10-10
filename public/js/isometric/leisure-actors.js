/** Smooth public poses. They cannot complete a round or change the local player's state. */
import {publicActivity} from './leisure-presence.js';
const DURATIONS={cast:700,reel:400,caught:1900,board:700,exit:700};
export function createLeisureActors(kind,now=()=>Date.now()){
  const actors=new Map();
  return {
    receive(peers){
      const seen=new Set();let changed=false;
      for(const peer of (Array.isArray(peers)?peers:[]).slice(0,30)){
        const activity=publicActivity(peer.activity);if(!activity||activity.kind!==kind||typeof peer.pid!=='string'||seen.has(peer.pid))continue;
        seen.add(peer.pid);let actor=actors.get(peer.pid);
        const signature=JSON.stringify([peer.name,peer.gender,peer.look||{},activity]);
        if(actor?.signature===signature)continue;changed=true;
        if(!actor){actor={pid:peer.pid,x:activity.x,y:activity.y,reportedAction:null,action:null,heading:undefined};actors.set(peer.pid,actor);}
        if(activity.action!==actor.reportedAction){actor.reportedAction=activity.action;actor.action=activity.action?{kind:activity.action,at:now(),duration:DURATIONS[activity.action],from:[actor.x,actor.y],to:[activity.x,activity.y]}:null;}
        // Network travel, not unfinished interpolation, determines the body heading.
        const previous=actor.activity,dx=activity.x-(previous?.x??actor.x),dy=activity.y-(previous?.y??actor.y);
        if(Math.hypot(dx,dy)>.1)actor.heading=Math.atan2(dy,dx);
        else if(previous&&activity.direction!==previous.direction)actor.heading=undefined;
        Object.assign(actor,{name:typeof peer.name==='string'?peer.name.slice(0,24):'Người chơi',look:peer.look||{},gender:peer.gender,activity,signature});
      }
      for(const pid of actors.keys())if(!seen.has(pid)){actors.delete(pid);changed=true;}return changed;
    },
    needsFrame(){return [...actors.values()].some(actor=>actor.action||actor.activity.moving||['waiting','bite'].includes(actor.activity.phase)||Math.hypot(actor.activity.x-actor.x,actor.activity.y-actor.y)>.025);},
    sample(dt){
      const blend=1-Math.exp(-14*Math.max(0,Math.min(.1,dt)));
      return [...actors.values()].map(actor=>{
        actor.x+=(actor.activity.x-actor.x)*blend;actor.y+=(actor.activity.y-actor.y)*blend;
        if(Math.hypot(actor.activity.x-actor.x,actor.activity.y-actor.y)<=.025){actor.x=actor.activity.x;actor.y=actor.activity.y;}
        if(actor.action&&now()-actor.action.at>=actor.action.duration)actor.action=null;
        return {pid:actor.pid,name:actor.name,look:actor.look,gender:actor.gender,state:{...actor.activity,x:actor.x,y:actor.y,heading:actor.heading,action:actor.action}};
      });
    }
  };
}
