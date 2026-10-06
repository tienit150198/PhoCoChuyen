// Prints, for every leg and lit junction, whether the client would ask for a light (onLeg). Input: {nodes,lit} on stdin.
import {onLeg} from '../public/js/careers/delivery_navigation.js';
let raw='';for await(const chunk of process.stdin)raw+=chunk;
const {nodes,lit}=JSON.parse(raw),out={};
for(const at of Object.keys(nodes))for(const target of Object.keys(nodes))if(at!==target)
 for(const [i,j] of lit)out[`${at}>${target}:${i},${j}`]=onLeg(nodes,at,target,i,j);
if(onLeg(nodes,'hub','hub',1,1)!==false||onLeg(nodes,'hub','nowhere',1,1)!==false)throw new Error('unknown leg must not ask');
console.log(JSON.stringify(out));
