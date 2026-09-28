/** Storefront scene (shop kind): awning, sign, back shelves, counter, store
 * cabinet, ledger desk and door sign. The drawing lives on the world
 * (shopRoom / portraitRoom / shopProps) because shop careers dress it in many
 * small ways; this module is the plan plus the hooks.
 *
 * PLAN schema, used by every scene kind (scene pixels; landscape 1200×790,
 * portrait 700×890):
 *   floor [x0,y0,x1,y1]    where feet may stand
 *   blocks [[x0,y0,x1,y1]]  furniture footprints (feet area), never walkable
 *   home [x,y]             where the player starts; lane y = the working line
 *   kx, ky                 scene pixels per nav unit (keep 82/45 land, 51/57 port)
 *   customers [[x,y]]×4    where guests stand; event, officer [x,y]
 *   staff {x,step,y}       hired staff line; sway = how far they pace
 *   cat [x,y]; counterSpan [x0,x1] (talk across it)
 *   decor {corner,front,center} floor spots; sill {plant,lamp,seat,rug}
 *   bench, garden          extra footprints for the property tiers
 *   spots: id -> [[hit x,y], hit range, [[approach x,y],…]] for shelf,
 *     evidence, workbench, counter, warehouse, board, finance, property,
 *     security, door, pet
 *   badge {id:[dx,dy]}     optional nudge of a hotspot's "+" badge
 */
// Rect footprints are [x0,y0,x1,y1] of the feet area a prop stands on.
// spots: id → [hit anchor, hit range, approach points (feet)].
export const PLAN={
 land:{floor:[130,452,1070,682],lane:505,line:563,home:[600,505],kx:82,ky:45,sway:38,
   blocks:[[220,540,872,586],[140,445,209,536],[979,544,1085,566],[100,570,136,582],[970,652,1082,668]],
   bench:[148,652,273,676],garden:[[780,684],[835,684]],
   customers:[[540,616],[665,621],[790,614],[605,668]],event:[440,662],officer:[330,662],
   staff:{x:300,step:125,y:460},cat:[660,410],counterSpan:[245,850],
   decor:{corner:[138,640],front:[905,672],center:[712,672]},sill:{plant:[452,410],lamp:[505,410],seat:[565,410],rug:[575,648]},
   spots:{shelf:[[264,330],100,[[264,505]]],evidence:[[876,330],100,[[876,505]]],workbench:[[480,436],62,[[480,505]]],counter:[[740,436],60,[[740,505]]],
     warehouse:[[175,488],48,[[175,562],[246,505]]],board:[[1054,365],48,[[1040,505]]],finance:[[1032,515],42,[[946,556],[1032,600]]],
     property:[[999,288],35,[[990,505]]],security:[[190,228],30,[[250,505]]],door:[[1026,640],45,[[930,640],[1026,602]]],pet:[[660,392],38,[[660,505]]]}},
 port:{badge:{board:[36,-44]},floor:[62,512,638,822],lane:572,line:626,home:[330,572],kx:51,ky:57,sway:24,
   blocks:[[95,604,555,650],[57,506,113,612],[556,738,654,752],[46,783,78,795],[629,812,655,824],[470,806,584,820]],
   bench:[80,810,201,826],garden:[[279,826],[330,826],[381,826]],
   customers:[[215,698],[335,694],[455,700],[250,768]],event:[160,738],officer:[455,772],
   staff:{x:175,step:95,y:524},cat:[395,467],counterSpan:[120,540],
   decor:{corner:[520,690],front:[410,812],center:[335,760]},sill:{plant:[262,467],lamp:[300,467],seat:[340,467],rug:[330,735]},
   spots:{shelf:[[145,340],100,[[175,572]]],evidence:[[545,340],100,[[545,572]]],workbench:[[268,512],58,[[268,572]]],counter:[[458,505],56,[[458,572]]],
     warehouse:[[85,570],45,[[90,672],[140,572]]],board:[[603,463],45,[[605,572]]],finance:[[605,712],42,[[605,690],[520,745]]],
     property:[[600,255],35,[[600,572]]],security:[[90,242],30,[[175,572]]],door:[[527,802],45,[[440,790],[527,772]]],pet:[[395,450],38,[[395,572]]]}},
};

export default {
  id:'shop',
  plan:PLAN,
  room(w){w.shopRoom();},
  props(w){return w.shopProps();},
};
