import {CIVIC_ASSETS} from './amenity-art';
import {NEW_BUILDING_ART} from './building-art';
import {CAREER_ASSETS} from './career-art';

/** Shared URL lookup for on-demand loading. Registering a URL does not preload
 * all 50 paintings at boot; the world requests building kinds as it creates them. */
export const ISOMETRIC_ASSETS:Record<string,string>={
  ...Object.fromEntries(['grocery','home','cafe','tree','bench','counter','shelf','desk','crates','interior-shop','interior-office','interior-cafe','interior-home'].map(kind=>[kind,'/icons/isometric/'+kind+'.webp'])),
  ...CIVIC_ASSETS,
  gazebo:'/icons/cozy-v3/park-gazebo.webp',
  'pool-map':'/icons/cozy-v3/town-pool.webp',
  pharmacy:'/icons/cozy-v2/pharmacy.webp',
  'mother-baby':'/icons/cozy-v2/mother-baby.webp',
  garage:'/icons/cozy-v2/garage.webp',
  pho:'/icons/cozy-v2/pho.webp',
  pond:'/icons/cozy-v2/leisure-lake.webp',
  pool:'/icons/cozy-v2/leisure-pool.webp',
  boat:'/icons/cozy-v2/boat.webp',
  vegetation:'/icons/cozy-v2/vegetation.webp',
  ...Object.fromEntries(NEW_BUILDING_ART.map(kind=>[kind,`/icons/cozy-v3/${kind}.webp`])),
  ...CAREER_ASSETS,
};
