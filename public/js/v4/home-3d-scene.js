var __defProp=Object.defineProperty;var __export=(target,all)=>{for(var name in all)__defProp(target,name,{get:all[name],enumerable:!0})};var MOUSE={LEFT:0,MIDDLE:1,RIGHT:2,ROTATE:0,DOLLY:1,PAN:2},TOUCH={ROTATE:0,PAN:1,DOLLY_PAN:2,DOLLY_ROTATE:3},CullFaceNone=0,CullFaceBack=1,CullFaceFront=2;var PCFShadowMap=1,PCFSoftShadowMap=2,VSMShadowMap=3,FrontSide=0,BackSide=1,DoubleSide=2,NoBlending=0,NormalBlending=1,AdditiveBlending=2,SubtractiveBlending=3,MultiplyBlending=4,CustomBlending=5;var AddEquation=100,SubtractEquation=101,ReverseSubtractEquation=102,MinEquation=103,MaxEquation=104,ZeroFactor=200,OneFactor=201,SrcColorFactor=202,OneMinusSrcColorFactor=203,SrcAlphaFactor=204,OneMinusSrcAlphaFactor=205,DstAlphaFactor=206,OneMinusDstAlphaFactor=207,DstColorFactor=208,OneMinusDstColorFactor=209,SrcAlphaSaturateFactor=210,ConstantColorFactor=211,OneMinusConstantColorFactor=212,ConstantAlphaFactor=213,OneMinusConstantAlphaFactor=214,NeverDepth=0,AlwaysDepth=1,LessDepth=2,LessEqualDepth=3,EqualDepth=4,GreaterEqualDepth=5,GreaterDepth=6,NotEqualDepth=7,MultiplyOperation=0,MixOperation=1,AddOperation=2,NoToneMapping=0,LinearToneMapping=1,ReinhardToneMapping=2,CineonToneMapping=3,ACESFilmicToneMapping=4,CustomToneMapping=5,AgXToneMapping=6,NeutralToneMapping=7;var UVMapping=300,CubeReflectionMapping=301,CubeRefractionMapping=302,EquirectangularReflectionMapping=303,EquirectangularRefractionMapping=304,CubeUVReflectionMapping=306,RepeatWrapping=1e3,ClampToEdgeWrapping=1001,MirroredRepeatWrapping=1002,NearestFilter=1003,NearestMipmapNearestFilter=1004;var NearestMipmapLinearFilter=1005;var LinearFilter=1006,LinearMipmapNearestFilter=1007;var LinearMipmapLinearFilter=1008;var UnsignedByteType=1009,ByteType=1010,ShortType=1011,UnsignedShortType=1012,IntType=1013,UnsignedIntType=1014,FloatType=1015,HalfFloatType=1016,UnsignedShort4444Type=1017,UnsignedShort5551Type=1018,UnsignedInt248Type=1020,UnsignedInt5999Type=35902,UnsignedInt101111Type=35899,AlphaFormat=1021,RGBFormat=1022,RGBAFormat=1023,DepthFormat=1026,DepthStencilFormat=1027,RedFormat=1028,RedIntegerFormat=1029,RGFormat=1030,RGIntegerFormat=1031;var RGBAIntegerFormat=1033,RGB_S3TC_DXT1_Format=33776,RGBA_S3TC_DXT1_Format=33777,RGBA_S3TC_DXT3_Format=33778,RGBA_S3TC_DXT5_Format=33779,RGB_PVRTC_4BPPV1_Format=35840,RGB_PVRTC_2BPPV1_Format=35841,RGBA_PVRTC_4BPPV1_Format=35842,RGBA_PVRTC_2BPPV1_Format=35843,RGB_ETC1_Format=36196,RGB_ETC2_Format=37492,RGBA_ETC2_EAC_Format=37496,R11_EAC_Format=37488,SIGNED_R11_EAC_Format=37489,RG11_EAC_Format=37490,SIGNED_RG11_EAC_Format=37491,RGBA_ASTC_4x4_Format=37808,RGBA_ASTC_5x4_Format=37809,RGBA_ASTC_5x5_Format=37810,RGBA_ASTC_6x5_Format=37811,RGBA_ASTC_6x6_Format=37812,RGBA_ASTC_8x5_Format=37813,RGBA_ASTC_8x6_Format=37814,RGBA_ASTC_8x8_Format=37815,RGBA_ASTC_10x5_Format=37816,RGBA_ASTC_10x6_Format=37817,RGBA_ASTC_10x8_Format=37818,RGBA_ASTC_10x10_Format=37819,RGBA_ASTC_12x10_Format=37820,RGBA_ASTC_12x12_Format=37821,RGBA_BPTC_Format=36492,RGB_BPTC_SIGNED_Format=36494,RGB_BPTC_UNSIGNED_Format=36495,RED_RGTC1_Format=36283,SIGNED_RED_RGTC1_Format=36284,RED_GREEN_RGTC2_Format=36285,SIGNED_RED_GREEN_RGTC2_Format=36286;var BasicDepthPacking=3200;var TangentSpaceNormalMap=0,ObjectSpaceNormalMap=1,NoColorSpace="",SRGBColorSpace="srgb",LinearSRGBColorSpace="srgb-linear",LinearTransfer="linear",SRGBTransfer="srgb";var KeepStencilOp=7680;var AlwaysStencilFunc=519,NeverCompare=512,LessCompare=513,EqualCompare=514,LessEqualCompare=515,GreaterCompare=516,NotEqualCompare=517,GreaterEqualCompare=518,AlwaysCompare=519,StaticDrawUsage=35044;var GLSL3="300 es",WebGLCoordinateSystem=2e3,WebGPUCoordinateSystem=2001;function arrayNeedsUint32(array){for(let i=array.length-1;i>=0;--i)if(array[i]>=65535)return!0;return!1}function createElementNS(name){return document.createElementNS("http://www.w3.org/1999/xhtml",name)}function createCanvasElement(){let canvas=createElementNS("canvas");return canvas.style.display="block",canvas}var _cache={},_setConsoleFunction=null;function log(...params){let message="THREE."+params.shift();_setConsoleFunction?_setConsoleFunction("log",message,...params):console.log(message,...params)}function enhanceLogMessage(params){let message=params[0];if(typeof message=="string"&&message.startsWith("TSL:")){let stackTrace=params[1];stackTrace&&stackTrace.isStackTrace?params[0]+=" "+stackTrace.getLocation():params[1]='Stack trace not available. Enable "THREE.Node.captureStackTrace" to capture stack traces.'}return params}function warn(...params){params=enhanceLogMessage(params);let message="THREE."+params.shift();if(_setConsoleFunction)_setConsoleFunction("warn",message,...params);else{let stackTrace=params[0];stackTrace&&stackTrace.isStackTrace?console.warn(stackTrace.getError(message)):console.warn(message,...params)}}function error(...params){params=enhanceLogMessage(params);let message="THREE."+params.shift();if(_setConsoleFunction)_setConsoleFunction("error",message,...params);else{let stackTrace=params[0];stackTrace&&stackTrace.isStackTrace?console.error(stackTrace.getError(message)):console.error(message,...params)}}function warnOnce(...params){let message=params.join(" ");message in _cache||(_cache[message]=!0,warn(...params))}function probeAsync(gl,sync,interval){return new Promise(function(resolve,reject){function probe(){switch(gl.clientWaitSync(sync,gl.SYNC_FLUSH_COMMANDS_BIT,0)){case gl.WAIT_FAILED:reject();break;case gl.TIMEOUT_EXPIRED:setTimeout(probe,interval);break;default:resolve()}}setTimeout(probe,interval)})}var ReversedDepthFuncs={[NeverDepth]:AlwaysDepth,[LessDepth]:GreaterDepth,[EqualDepth]:NotEqualDepth,[LessEqualDepth]:GreaterEqualDepth,[AlwaysDepth]:NeverDepth,[GreaterDepth]:LessDepth,[NotEqualDepth]:EqualDepth,[GreaterEqualDepth]:LessEqualDepth};var EventDispatcher=class{addEventListener(type,listener){this._listeners===void 0&&(this._listeners={});let listeners=this._listeners;listeners[type]===void 0&&(listeners[type]=[]),listeners[type].indexOf(listener)===-1&&listeners[type].push(listener)}hasEventListener(type,listener){let listeners=this._listeners;return listeners===void 0?!1:listeners[type]!==void 0&&listeners[type].indexOf(listener)!==-1}removeEventListener(type,listener){let listeners=this._listeners;if(listeners===void 0)return;let listenerArray=listeners[type];if(listenerArray!==void 0){let index=listenerArray.indexOf(listener);index!==-1&&listenerArray.splice(index,1)}}dispatchEvent(event){let listeners=this._listeners;if(listeners===void 0)return;let listenerArray=listeners[event.type];if(listenerArray!==void 0){event.target=this;let array=listenerArray.slice(0);for(let i=0,l=array.length;i<l;i++)array[i].call(this,event);event.target=null}}};var _lut=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"],_seed=1234567,DEG2RAD=Math.PI/180,RAD2DEG=180/Math.PI;function generateUUID(){let d0=Math.random()*4294967295|0,d1=Math.random()*4294967295|0,d2=Math.random()*4294967295|0,d3=Math.random()*4294967295|0;return(_lut[d0&255]+_lut[d0>>8&255]+_lut[d0>>16&255]+_lut[d0>>24&255]+"-"+_lut[d1&255]+_lut[d1>>8&255]+"-"+_lut[d1>>16&15|64]+_lut[d1>>24&255]+"-"+_lut[d2&63|128]+_lut[d2>>8&255]+"-"+_lut[d2>>16&255]+_lut[d2>>24&255]+_lut[d3&255]+_lut[d3>>8&255]+_lut[d3>>16&255]+_lut[d3>>24&255]).toLowerCase()}function clamp(value,min,max){return Math.max(min,Math.min(max,value))}function euclideanModulo(n,m){return(n%m+m)%m}function mapLinear(x,a1,a2,b1,b2){return b1+(x-a1)*(b2-b1)/(a2-a1)}function inverseLerp(x,y,value){return x!==y?(value-x)/(y-x):0}function lerp(x,y,t){return(1-t)*x+t*y}function damp(x,y,lambda,dt){return lerp(x,y,1-Math.exp(-lambda*dt))}function pingpong(x,length=1){return length-Math.abs(euclideanModulo(x,length*2)-length)}function smoothstep(x,min,max){return x<=min?0:x>=max?1:(x=(x-min)/(max-min),x*x*(3-2*x))}function smootherstep(x,min,max){return x<=min?0:x>=max?1:(x=(x-min)/(max-min),x*x*x*(x*(x*6-15)+10))}function randInt(low,high){return low+Math.floor(Math.random()*(high-low+1))}function randFloat(low,high){return low+Math.random()*(high-low)}function randFloatSpread(range){return range*(.5-Math.random())}function seededRandom(s){s!==void 0&&(_seed=s);let t=_seed+=1831565813;return t=Math.imul(t^t>>>15,t|1),t^=t+Math.imul(t^t>>>7,t|61),((t^t>>>14)>>>0)/4294967296}function degToRad(degrees){return degrees*DEG2RAD}function radToDeg(radians){return radians*RAD2DEG}function isPowerOfTwo(value){return value>0&&Number.isInteger(value)&&2**Math.round(Math.log2(value))===value}function ceilPowerOfTwo(value){return Math.pow(2,Math.ceil(Math.log(value)/Math.LN2))}function floorPowerOfTwo(value){return Math.pow(2,Math.floor(Math.log(value)/Math.LN2))}function setQuaternionFromProperEuler(q,a,b,c,order){let cos=Math.cos,sin=Math.sin,c2=cos(b/2),s2=sin(b/2),c13=cos((a+c)/2),s13=sin((a+c)/2),c1_3=cos((a-c)/2),s1_3=sin((a-c)/2),c3_1=cos((c-a)/2),s3_1=sin((c-a)/2);switch(order){case"XYX":q.set(c2*s13,s2*c1_3,s2*s1_3,c2*c13);break;case"YZY":q.set(s2*s1_3,c2*s13,s2*c1_3,c2*c13);break;case"ZXZ":q.set(s2*c1_3,s2*s1_3,c2*s13,c2*c13);break;case"XZX":q.set(c2*s13,s2*s3_1,s2*c3_1,c2*c13);break;case"YXY":q.set(s2*c3_1,c2*s13,s2*s3_1,c2*c13);break;case"ZYZ":q.set(s2*s3_1,s2*c3_1,c2*s13,c2*c13);break;default:warn("MathUtils: .setQuaternionFromProperEuler() encountered an unknown order: "+order)}}function denormalize(value,array){switch(array.constructor){case Float32Array:return value;case Uint32Array:return value/4294967295;case Uint16Array:return value/65535;case Uint8Array:case Uint8ClampedArray:return value/255;case Int32Array:return Math.max(value/2147483647,-1);case Int16Array:return Math.max(value/32767,-1);case Int8Array:return Math.max(value/127,-1);default:throw new Error("THREE.MathUtils: Invalid component type.")}}function normalize(value,array){switch(array.constructor){case Float32Array:return value;case Uint32Array:return Math.round(value*4294967295);case Uint16Array:return Math.round(value*65535);case Uint8Array:case Uint8ClampedArray:return Math.round(value*255);case Int32Array:return Math.round(value*2147483647);case Int16Array:return Math.round(value*32767);case Int8Array:return Math.round(value*127);default:throw new Error("THREE.MathUtils: Invalid component type.")}}var MathUtils={DEG2RAD,RAD2DEG,generateUUID,clamp,euclideanModulo,mapLinear,inverseLerp,lerp,damp,pingpong,smoothstep,smootherstep,randInt,randFloat,randFloatSpread,seededRandom,degToRad,radToDeg,isPowerOfTwo,ceilPowerOfTwo,floorPowerOfTwo,setQuaternionFromProperEuler,normalize,denormalize};var _Vector2=class _Vector2{constructor(x=0,y=0){this.x=x,this.y=y}get width(){return this.x}set width(value){this.x=value}get height(){return this.y}set height(value){this.y=value}set(x,y){return this.x=x,this.y=y,this}setScalar(scalar){return this.x=scalar,this.y=scalar,this}setX(x){return this.x=x,this}setY(y){return this.y=y,this}setComponent(index,value){switch(index){case 0:this.x=value;break;case 1:this.y=value;break;default:throw new Error("THREE.Vector2: index is out of range: "+index)}return this}getComponent(index){switch(index){case 0:return this.x;case 1:return this.y;default:throw new Error("THREE.Vector2: index is out of range: "+index)}}clone(){return new this.constructor(this.x,this.y)}copy(v){return this.x=v.x,this.y=v.y,this}add(v){return this.x+=v.x,this.y+=v.y,this}addScalar(s){return this.x+=s,this.y+=s,this}addVectors(a,b){return this.x=a.x+b.x,this.y=a.y+b.y,this}addScaledVector(v,s){return this.x+=v.x*s,this.y+=v.y*s,this}sub(v){return this.x-=v.x,this.y-=v.y,this}subScalar(s){return this.x-=s,this.y-=s,this}subVectors(a,b){return this.x=a.x-b.x,this.y=a.y-b.y,this}multiply(v){return this.x*=v.x,this.y*=v.y,this}multiplyScalar(scalar){return this.x*=scalar,this.y*=scalar,this}divide(v){return this.x/=v.x,this.y/=v.y,this}divideScalar(scalar){return this.multiplyScalar(1/scalar)}applyMatrix3(m){let x=this.x,y=this.y,e=m.elements;return this.x=e[0]*x+e[3]*y+e[6],this.y=e[1]*x+e[4]*y+e[7],this}min(v){return this.x=Math.min(this.x,v.x),this.y=Math.min(this.y,v.y),this}max(v){return this.x=Math.max(this.x,v.x),this.y=Math.max(this.y,v.y),this}clamp(min,max){return this.x=clamp(this.x,min.x,max.x),this.y=clamp(this.y,min.y,max.y),this}clampScalar(minVal,maxVal){return this.x=clamp(this.x,minVal,maxVal),this.y=clamp(this.y,minVal,maxVal),this}clampLength(min,max){let length=this.length();return this.divideScalar(length||1).multiplyScalar(clamp(length,min,max))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(v){return this.x*v.x+this.y*v.y}cross(v){return this.x*v.y-this.y*v.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(v){let denominator=Math.sqrt(this.lengthSq()*v.lengthSq());if(denominator===0)return Math.PI/2;let theta=this.dot(v)/denominator;return Math.acos(clamp(theta,-1,1))}distanceTo(v){return Math.sqrt(this.distanceToSquared(v))}distanceToSquared(v){let dx=this.x-v.x,dy=this.y-v.y;return dx*dx+dy*dy}manhattanDistanceTo(v){return Math.abs(this.x-v.x)+Math.abs(this.y-v.y)}setLength(length){return this.normalize().multiplyScalar(length)}lerp(v,alpha){return this.x+=(v.x-this.x)*alpha,this.y+=(v.y-this.y)*alpha,this}lerpVectors(v1,v2,alpha){return this.x=v1.x+(v2.x-v1.x)*alpha,this.y=v1.y+(v2.y-v1.y)*alpha,this}equals(v){return v.x===this.x&&v.y===this.y}fromArray(array,offset=0){return this.x=array[offset],this.y=array[offset+1],this}toArray(array=[],offset=0){return array[offset]=this.x,array[offset+1]=this.y,array}fromBufferAttribute(attribute,index){return this.x=attribute.getX(index),this.y=attribute.getY(index),this}rotateAround(center,angle){let c=Math.cos(angle),s=Math.sin(angle),x=this.x-center.x,y=this.y-center.y;return this.x=x*c-y*s+center.x,this.y=x*s+y*c+center.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}};_Vector2.prototype.isVector2=!0;var Vector2=_Vector2;var Quaternion=class{constructor(x=0,y=0,z=0,w=1){this.isQuaternion=!0,this._x=x,this._y=y,this._z=z,this._w=w}static slerpFlat(dst,dstOffset,src0,srcOffset0,src1,srcOffset1,t){let x0=src0[srcOffset0+0],y0=src0[srcOffset0+1],z0=src0[srcOffset0+2],w0=src0[srcOffset0+3],x1=src1[srcOffset1+0],y1=src1[srcOffset1+1],z1=src1[srcOffset1+2],w1=src1[srcOffset1+3];if(w0!==w1||x0!==x1||y0!==y1||z0!==z1){let dot=x0*x1+y0*y1+z0*z1+w0*w1;dot<0&&(x1=-x1,y1=-y1,z1=-z1,w1=-w1,dot=-dot);let s=1-t;if(dot<.9995){let theta=Math.acos(dot),sin=Math.sin(theta);s=Math.sin(s*theta)/sin,t=Math.sin(t*theta)/sin,x0=x0*s+x1*t,y0=y0*s+y1*t,z0=z0*s+z1*t,w0=w0*s+w1*t}else{x0=x0*s+x1*t,y0=y0*s+y1*t,z0=z0*s+z1*t,w0=w0*s+w1*t;let f=1/Math.sqrt(x0*x0+y0*y0+z0*z0+w0*w0);x0*=f,y0*=f,z0*=f,w0*=f}}dst[dstOffset]=x0,dst[dstOffset+1]=y0,dst[dstOffset+2]=z0,dst[dstOffset+3]=w0}static multiplyQuaternionsFlat(dst,dstOffset,src0,srcOffset0,src1,srcOffset1){let x0=src0[srcOffset0],y0=src0[srcOffset0+1],z0=src0[srcOffset0+2],w0=src0[srcOffset0+3],x1=src1[srcOffset1],y1=src1[srcOffset1+1],z1=src1[srcOffset1+2],w1=src1[srcOffset1+3];return dst[dstOffset]=x0*w1+w0*x1+y0*z1-z0*y1,dst[dstOffset+1]=y0*w1+w0*y1+z0*x1-x0*z1,dst[dstOffset+2]=z0*w1+w0*z1+x0*y1-y0*x1,dst[dstOffset+3]=w0*w1-x0*x1-y0*y1-z0*z1,dst}get x(){return this._x}set x(value){this._x=value,this._onChangeCallback()}get y(){return this._y}set y(value){this._y=value,this._onChangeCallback()}get z(){return this._z}set z(value){this._z=value,this._onChangeCallback()}get w(){return this._w}set w(value){this._w=value,this._onChangeCallback()}set(x,y,z,w){return this._x=x,this._y=y,this._z=z,this._w=w,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(quaternion){return this._x=quaternion.x,this._y=quaternion.y,this._z=quaternion.z,this._w=quaternion.w,this._onChangeCallback(),this}setFromEuler(euler,update=!0){let x=euler._x,y=euler._y,z=euler._z,order=euler._order,cos=Math.cos,sin=Math.sin,c1=cos(x/2),c2=cos(y/2),c3=cos(z/2),s1=sin(x/2),s2=sin(y/2),s3=sin(z/2);switch(order){case"XYZ":this._x=s1*c2*c3+c1*s2*s3,this._y=c1*s2*c3-s1*c2*s3,this._z=c1*c2*s3+s1*s2*c3,this._w=c1*c2*c3-s1*s2*s3;break;case"YXZ":this._x=s1*c2*c3+c1*s2*s3,this._y=c1*s2*c3-s1*c2*s3,this._z=c1*c2*s3-s1*s2*c3,this._w=c1*c2*c3+s1*s2*s3;break;case"ZXY":this._x=s1*c2*c3-c1*s2*s3,this._y=c1*s2*c3+s1*c2*s3,this._z=c1*c2*s3+s1*s2*c3,this._w=c1*c2*c3-s1*s2*s3;break;case"ZYX":this._x=s1*c2*c3-c1*s2*s3,this._y=c1*s2*c3+s1*c2*s3,this._z=c1*c2*s3-s1*s2*c3,this._w=c1*c2*c3+s1*s2*s3;break;case"YZX":this._x=s1*c2*c3+c1*s2*s3,this._y=c1*s2*c3+s1*c2*s3,this._z=c1*c2*s3-s1*s2*c3,this._w=c1*c2*c3-s1*s2*s3;break;case"XZY":this._x=s1*c2*c3-c1*s2*s3,this._y=c1*s2*c3-s1*c2*s3,this._z=c1*c2*s3+s1*s2*c3,this._w=c1*c2*c3+s1*s2*s3;break;default:warn("Quaternion: .setFromEuler() encountered an unknown order: "+order)}return update===!0&&this._onChangeCallback(),this}setFromAxisAngle(axis,angle){let halfAngle=angle/2,s=Math.sin(halfAngle);return this._x=axis.x*s,this._y=axis.y*s,this._z=axis.z*s,this._w=Math.cos(halfAngle),this._onChangeCallback(),this}setFromRotationMatrix(m){let te=m.elements,m11=te[0],m12=te[4],m13=te[8],m21=te[1],m22=te[5],m23=te[9],m31=te[2],m32=te[6],m33=te[10],trace=m11+m22+m33;if(trace>0){let s=.5/Math.sqrt(trace+1);this._w=.25/s,this._x=(m32-m23)*s,this._y=(m13-m31)*s,this._z=(m21-m12)*s}else if(m11>m22&&m11>m33){let s=2*Math.sqrt(1+m11-m22-m33);this._w=(m32-m23)/s,this._x=.25*s,this._y=(m12+m21)/s,this._z=(m13+m31)/s}else if(m22>m33){let s=2*Math.sqrt(1+m22-m11-m33);this._w=(m13-m31)/s,this._x=(m12+m21)/s,this._y=.25*s,this._z=(m23+m32)/s}else{let s=2*Math.sqrt(1+m33-m11-m22);this._w=(m21-m12)/s,this._x=(m13+m31)/s,this._y=(m23+m32)/s,this._z=.25*s}return this._onChangeCallback(),this}setFromUnitVectors(vFrom,vTo){let r=vFrom.dot(vTo)+1;return r<1e-8?(r=0,Math.abs(vFrom.x)>Math.abs(vFrom.z)?(this._x=-vFrom.y,this._y=vFrom.x,this._z=0,this._w=r):(this._x=0,this._y=-vFrom.z,this._z=vFrom.y,this._w=r)):(this._x=vFrom.y*vTo.z-vFrom.z*vTo.y,this._y=vFrom.z*vTo.x-vFrom.x*vTo.z,this._z=vFrom.x*vTo.y-vFrom.y*vTo.x,this._w=r),this.normalize()}angleTo(q){return 2*Math.acos(Math.abs(clamp(this.dot(q),-1,1)))}rotateTowards(q,step){let angle=this.angleTo(q);if(angle===0)return this;let t=Math.min(1,step/angle);return this.slerp(q,t),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(v){return this._x*v._x+this._y*v._y+this._z*v._z+this._w*v._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let l=this.length();return l===0?(this._x=0,this._y=0,this._z=0,this._w=1):(l=1/l,this._x=this._x*l,this._y=this._y*l,this._z=this._z*l,this._w=this._w*l),this._onChangeCallback(),this}multiply(q){return this.multiplyQuaternions(this,q)}premultiply(q){return this.multiplyQuaternions(q,this)}multiplyQuaternions(a,b){let qax=a._x,qay=a._y,qaz=a._z,qaw=a._w,qbx=b._x,qby=b._y,qbz=b._z,qbw=b._w;return this._x=qax*qbw+qaw*qbx+qay*qbz-qaz*qby,this._y=qay*qbw+qaw*qby+qaz*qbx-qax*qbz,this._z=qaz*qbw+qaw*qbz+qax*qby-qay*qbx,this._w=qaw*qbw-qax*qbx-qay*qby-qaz*qbz,this._onChangeCallback(),this}slerp(qb,t){let x=qb._x,y=qb._y,z=qb._z,w=qb._w,dot=this.dot(qb);dot<0&&(x=-x,y=-y,z=-z,w=-w,dot=-dot);let s=1-t;if(dot<.9995){let theta=Math.acos(dot),sin=Math.sin(theta);s=Math.sin(s*theta)/sin,t=Math.sin(t*theta)/sin,this._x=this._x*s+x*t,this._y=this._y*s+y*t,this._z=this._z*s+z*t,this._w=this._w*s+w*t,this._onChangeCallback()}else this._x=this._x*s+x*t,this._y=this._y*s+y*t,this._z=this._z*s+z*t,this._w=this._w*s+w*t,this.normalize();return this}slerpQuaternions(qa,qb,t){return this.copy(qa).slerp(qb,t)}random(){let theta1=2*Math.PI*Math.random(),theta2=2*Math.PI*Math.random(),x0=Math.random(),r1=Math.sqrt(1-x0),r2=Math.sqrt(x0);return this.set(r1*Math.sin(theta1),r1*Math.cos(theta1),r2*Math.sin(theta2),r2*Math.cos(theta2))}equals(quaternion){return quaternion._x===this._x&&quaternion._y===this._y&&quaternion._z===this._z&&quaternion._w===this._w}fromArray(array,offset=0){return this._x=array[offset],this._y=array[offset+1],this._z=array[offset+2],this._w=array[offset+3],this._onChangeCallback(),this}toArray(array=[],offset=0){return array[offset]=this._x,array[offset+1]=this._y,array[offset+2]=this._z,array[offset+3]=this._w,array}fromBufferAttribute(attribute,index){return this._x=attribute.getX(index),this._y=attribute.getY(index),this._z=attribute.getZ(index),this._w=attribute.getW(index),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(callback){return this._onChangeCallback=callback,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}};var _Vector3=class _Vector3{constructor(x=0,y=0,z=0){this.x=x,this.y=y,this.z=z}set(x,y,z){return z===void 0&&(z=this.z),this.x=x,this.y=y,this.z=z,this}setScalar(scalar){return this.x=scalar,this.y=scalar,this.z=scalar,this}setX(x){return this.x=x,this}setY(y){return this.y=y,this}setZ(z){return this.z=z,this}setComponent(index,value){switch(index){case 0:this.x=value;break;case 1:this.y=value;break;case 2:this.z=value;break;default:throw new Error("THREE.Vector3: index is out of range: "+index)}return this}getComponent(index){switch(index){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("THREE.Vector3: index is out of range: "+index)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(v){return this.x=v.x,this.y=v.y,this.z=v.z,this}add(v){return this.x+=v.x,this.y+=v.y,this.z+=v.z,this}addScalar(s){return this.x+=s,this.y+=s,this.z+=s,this}addVectors(a,b){return this.x=a.x+b.x,this.y=a.y+b.y,this.z=a.z+b.z,this}addScaledVector(v,s){return this.x+=v.x*s,this.y+=v.y*s,this.z+=v.z*s,this}sub(v){return this.x-=v.x,this.y-=v.y,this.z-=v.z,this}subScalar(s){return this.x-=s,this.y-=s,this.z-=s,this}subVectors(a,b){return this.x=a.x-b.x,this.y=a.y-b.y,this.z=a.z-b.z,this}multiply(v){return this.x*=v.x,this.y*=v.y,this.z*=v.z,this}multiplyScalar(scalar){return this.x*=scalar,this.y*=scalar,this.z*=scalar,this}multiplyVectors(a,b){return this.x=a.x*b.x,this.y=a.y*b.y,this.z=a.z*b.z,this}applyEuler(euler){return this.applyQuaternion(_quaternion.setFromEuler(euler))}applyAxisAngle(axis,angle){return this.applyQuaternion(_quaternion.setFromAxisAngle(axis,angle))}applyMatrix3(m){let x=this.x,y=this.y,z=this.z,e=m.elements;return this.x=e[0]*x+e[3]*y+e[6]*z,this.y=e[1]*x+e[4]*y+e[7]*z,this.z=e[2]*x+e[5]*y+e[8]*z,this}applyNormalMatrix(m){return this.applyMatrix3(m).normalize()}applyMatrix4(m){let x=this.x,y=this.y,z=this.z,e=m.elements,w=1/(e[3]*x+e[7]*y+e[11]*z+e[15]);return this.x=(e[0]*x+e[4]*y+e[8]*z+e[12])*w,this.y=(e[1]*x+e[5]*y+e[9]*z+e[13])*w,this.z=(e[2]*x+e[6]*y+e[10]*z+e[14])*w,this}applyQuaternion(q){let vx=this.x,vy=this.y,vz=this.z,qx=q.x,qy=q.y,qz=q.z,qw=q.w,tx=2*(qy*vz-qz*vy),ty=2*(qz*vx-qx*vz),tz=2*(qx*vy-qy*vx);return this.x=vx+qw*tx+qy*tz-qz*ty,this.y=vy+qw*ty+qz*tx-qx*tz,this.z=vz+qw*tz+qx*ty-qy*tx,this}project(camera){return this.applyMatrix4(camera.matrixWorldInverse).applyMatrix4(camera.projectionMatrix)}unproject(camera){return this.applyMatrix4(camera.projectionMatrixInverse).applyMatrix4(camera.matrixWorld)}transformDirection(m){let x=this.x,y=this.y,z=this.z,e=m.elements;return this.x=e[0]*x+e[4]*y+e[8]*z,this.y=e[1]*x+e[5]*y+e[9]*z,this.z=e[2]*x+e[6]*y+e[10]*z,this.normalize()}divide(v){return this.x/=v.x,this.y/=v.y,this.z/=v.z,this}divideScalar(scalar){return this.multiplyScalar(1/scalar)}min(v){return this.x=Math.min(this.x,v.x),this.y=Math.min(this.y,v.y),this.z=Math.min(this.z,v.z),this}max(v){return this.x=Math.max(this.x,v.x),this.y=Math.max(this.y,v.y),this.z=Math.max(this.z,v.z),this}clamp(min,max){return this.x=clamp(this.x,min.x,max.x),this.y=clamp(this.y,min.y,max.y),this.z=clamp(this.z,min.z,max.z),this}clampScalar(minVal,maxVal){return this.x=clamp(this.x,minVal,maxVal),this.y=clamp(this.y,minVal,maxVal),this.z=clamp(this.z,minVal,maxVal),this}clampLength(min,max){let length=this.length();return this.divideScalar(length||1).multiplyScalar(clamp(length,min,max))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(v){return this.x*v.x+this.y*v.y+this.z*v.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(length){return this.normalize().multiplyScalar(length)}lerp(v,alpha){return this.x+=(v.x-this.x)*alpha,this.y+=(v.y-this.y)*alpha,this.z+=(v.z-this.z)*alpha,this}lerpVectors(v1,v2,alpha){return this.x=v1.x+(v2.x-v1.x)*alpha,this.y=v1.y+(v2.y-v1.y)*alpha,this.z=v1.z+(v2.z-v1.z)*alpha,this}cross(v){return this.crossVectors(this,v)}crossVectors(a,b){let ax=a.x,ay=a.y,az=a.z,bx=b.x,by=b.y,bz=b.z;return this.x=ay*bz-az*by,this.y=az*bx-ax*bz,this.z=ax*by-ay*bx,this}projectOnVector(v){let denominator=v.lengthSq();if(denominator===0)return this.set(0,0,0);let scalar=v.dot(this)/denominator;return this.copy(v).multiplyScalar(scalar)}projectOnPlane(planeNormal){return _vector.copy(this).projectOnVector(planeNormal),this.sub(_vector)}reflect(normal){return this.sub(_vector.copy(normal).multiplyScalar(2*this.dot(normal)))}angleTo(v){let denominator=Math.sqrt(this.lengthSq()*v.lengthSq());if(denominator===0)return Math.PI/2;let theta=this.dot(v)/denominator;return Math.acos(clamp(theta,-1,1))}distanceTo(v){return Math.sqrt(this.distanceToSquared(v))}distanceToSquared(v){let dx=this.x-v.x,dy=this.y-v.y,dz=this.z-v.z;return dx*dx+dy*dy+dz*dz}manhattanDistanceTo(v){return Math.abs(this.x-v.x)+Math.abs(this.y-v.y)+Math.abs(this.z-v.z)}setFromSpherical(s){return this.setFromSphericalCoords(s.radius,s.phi,s.theta)}setFromSphericalCoords(radius,phi,theta){let sinPhiRadius=Math.sin(phi)*radius;return this.x=sinPhiRadius*Math.sin(theta),this.y=Math.cos(phi)*radius,this.z=sinPhiRadius*Math.cos(theta),this}setFromCylindrical(c){return this.setFromCylindricalCoords(c.radius,c.theta,c.y)}setFromCylindricalCoords(radius,theta,y){return this.x=radius*Math.sin(theta),this.y=y,this.z=radius*Math.cos(theta),this}setFromMatrixPosition(m){let e=m.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this}setFromMatrixScale(m){let sx=this.setFromMatrixColumn(m,0).length(),sy=this.setFromMatrixColumn(m,1).length(),sz=this.setFromMatrixColumn(m,2).length();return this.x=sx,this.y=sy,this.z=sz,this}setFromMatrixColumn(m,index){return this.fromArray(m.elements,index*4)}setFromMatrix3Column(m,index){return this.fromArray(m.elements,index*3)}setFromEuler(e){return this.x=e._x,this.y=e._y,this.z=e._z,this}setFromColor(c){return this.x=c.r,this.y=c.g,this.z=c.b,this}equals(v){return v.x===this.x&&v.y===this.y&&v.z===this.z}fromArray(array,offset=0){return this.x=array[offset],this.y=array[offset+1],this.z=array[offset+2],this}toArray(array=[],offset=0){return array[offset]=this.x,array[offset+1]=this.y,array[offset+2]=this.z,array}fromBufferAttribute(attribute,index){return this.x=attribute.getX(index),this.y=attribute.getY(index),this.z=attribute.getZ(index),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){let theta=Math.random()*Math.PI*2,u=Math.random()*2-1,c=Math.sqrt(1-u*u);return this.x=c*Math.cos(theta),this.y=u,this.z=c*Math.sin(theta),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}};_Vector3.prototype.isVector3=!0;var Vector3=_Vector3,_vector=new Vector3,_quaternion=new Quaternion;var _Matrix3=class _Matrix3{constructor(n11,n12,n13,n21,n22,n23,n31,n32,n33){this.elements=[1,0,0,0,1,0,0,0,1],n11!==void 0&&this.set(n11,n12,n13,n21,n22,n23,n31,n32,n33)}set(n11,n12,n13,n21,n22,n23,n31,n32,n33){let te=this.elements;return te[0]=n11,te[1]=n21,te[2]=n31,te[3]=n12,te[4]=n22,te[5]=n32,te[6]=n13,te[7]=n23,te[8]=n33,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(m){let te=this.elements,me=m.elements;return te[0]=me[0],te[1]=me[1],te[2]=me[2],te[3]=me[3],te[4]=me[4],te[5]=me[5],te[6]=me[6],te[7]=me[7],te[8]=me[8],this}extractBasis(xAxis,yAxis,zAxis){return xAxis.setFromMatrix3Column(this,0),yAxis.setFromMatrix3Column(this,1),zAxis.setFromMatrix3Column(this,2),this}setFromMatrix4(m){let me=m.elements;return this.set(me[0],me[4],me[8],me[1],me[5],me[9],me[2],me[6],me[10]),this}multiply(m){return this.multiplyMatrices(this,m)}premultiply(m){return this.multiplyMatrices(m,this)}multiplyMatrices(a,b){let ae=a.elements,be=b.elements,te=this.elements,a11=ae[0],a12=ae[3],a13=ae[6],a21=ae[1],a22=ae[4],a23=ae[7],a31=ae[2],a32=ae[5],a33=ae[8],b11=be[0],b12=be[3],b13=be[6],b21=be[1],b22=be[4],b23=be[7],b31=be[2],b32=be[5],b33=be[8];return te[0]=a11*b11+a12*b21+a13*b31,te[3]=a11*b12+a12*b22+a13*b32,te[6]=a11*b13+a12*b23+a13*b33,te[1]=a21*b11+a22*b21+a23*b31,te[4]=a21*b12+a22*b22+a23*b32,te[7]=a21*b13+a22*b23+a23*b33,te[2]=a31*b11+a32*b21+a33*b31,te[5]=a31*b12+a32*b22+a33*b32,te[8]=a31*b13+a32*b23+a33*b33,this}multiplyScalar(s){let te=this.elements;return te[0]*=s,te[3]*=s,te[6]*=s,te[1]*=s,te[4]*=s,te[7]*=s,te[2]*=s,te[5]*=s,te[8]*=s,this}determinant(){let te=this.elements,a=te[0],b=te[1],c=te[2],d=te[3],e=te[4],f=te[5],g=te[6],h=te[7],i=te[8];return a*e*i-a*f*h-b*d*i+b*f*g+c*d*h-c*e*g}invert(){let te=this.elements,n11=te[0],n21=te[1],n31=te[2],n12=te[3],n22=te[4],n32=te[5],n13=te[6],n23=te[7],n33=te[8],t11=n33*n22-n32*n23,t12=n32*n13-n33*n12,t13=n23*n12-n22*n13,det=n11*t11+n21*t12+n31*t13;if(det===0)return this.set(0,0,0,0,0,0,0,0,0);let detInv=1/det;return te[0]=t11*detInv,te[1]=(n31*n23-n33*n21)*detInv,te[2]=(n32*n21-n31*n22)*detInv,te[3]=t12*detInv,te[4]=(n33*n11-n31*n13)*detInv,te[5]=(n31*n12-n32*n11)*detInv,te[6]=t13*detInv,te[7]=(n21*n13-n23*n11)*detInv,te[8]=(n22*n11-n21*n12)*detInv,this}transpose(){let tmp3,m=this.elements;return tmp3=m[1],m[1]=m[3],m[3]=tmp3,tmp3=m[2],m[2]=m[6],m[6]=tmp3,tmp3=m[5],m[5]=m[7],m[7]=tmp3,this}getNormalMatrix(matrix4){return this.setFromMatrix4(matrix4).invert().transpose()}transposeIntoArray(r){let m=this.elements;return r[0]=m[0],r[1]=m[3],r[2]=m[6],r[3]=m[1],r[4]=m[4],r[5]=m[7],r[6]=m[2],r[7]=m[5],r[8]=m[8],this}setUvTransform(tx,ty,sx,sy,rotation,cx,cy){let c=Math.cos(rotation),s=Math.sin(rotation);return this.set(sx*c,sx*s,-sx*(c*cx+s*cy)+cx+tx,-sy*s,sy*c,-sy*(-s*cx+c*cy)+cy+ty,0,0,1),this}scale(sx,sy){return warnOnce("Matrix3: .scale() is deprecated. Use .makeScale() instead."),this.premultiply(_m3.makeScale(sx,sy)),this}rotate(theta){return warnOnce("Matrix3: .rotate() is deprecated. Use .makeRotation() instead."),this.premultiply(_m3.makeRotation(-theta)),this}translate(tx,ty){return warnOnce("Matrix3: .translate() is deprecated. Use .makeTranslation() instead."),this.premultiply(_m3.makeTranslation(tx,ty)),this}makeTranslation(x,y){return x.isVector2?this.set(1,0,x.x,0,1,x.y,0,0,1):this.set(1,0,x,0,1,y,0,0,1),this}makeRotation(theta){let c=Math.cos(theta),s=Math.sin(theta);return this.set(c,-s,0,s,c,0,0,0,1),this}makeScale(x,y){return this.set(x,0,0,0,y,0,0,0,1),this}equals(matrix){let te=this.elements,me=matrix.elements;for(let i=0;i<9;i++)if(te[i]!==me[i])return!1;return!0}fromArray(array,offset=0){for(let i=0;i<9;i++)this.elements[i]=array[i+offset];return this}toArray(array=[],offset=0){let te=this.elements;return array[offset]=te[0],array[offset+1]=te[1],array[offset+2]=te[2],array[offset+3]=te[3],array[offset+4]=te[4],array[offset+5]=te[5],array[offset+6]=te[6],array[offset+7]=te[7],array[offset+8]=te[8],array}clone(){return new this.constructor().fromArray(this.elements)}};_Matrix3.prototype.isMatrix3=!0;var Matrix3=_Matrix3,_m3=new Matrix3;var LINEAR_REC709_TO_XYZ=new Matrix3().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),XYZ_TO_LINEAR_REC709=new Matrix3().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);function createColorManagement(){let ColorManagement2={enabled:!0,workingColorSpace:LinearSRGBColorSpace,spaces:{},convert:function(color,sourceColorSpace,targetColorSpace){return this.enabled===!1||sourceColorSpace===targetColorSpace||!sourceColorSpace||!targetColorSpace||(this.spaces[sourceColorSpace].transfer===SRGBTransfer&&(color.r=SRGBToLinear(color.r),color.g=SRGBToLinear(color.g),color.b=SRGBToLinear(color.b)),this.spaces[sourceColorSpace].primaries!==this.spaces[targetColorSpace].primaries&&(color.applyMatrix3(this.spaces[sourceColorSpace].toXYZ),color.applyMatrix3(this.spaces[targetColorSpace].fromXYZ)),this.spaces[targetColorSpace].transfer===SRGBTransfer&&(color.r=LinearToSRGB(color.r),color.g=LinearToSRGB(color.g),color.b=LinearToSRGB(color.b))),color},workingToColorSpace:function(color,targetColorSpace){return this.convert(color,this.workingColorSpace,targetColorSpace)},colorSpaceToWorking:function(color,sourceColorSpace){return this.convert(color,sourceColorSpace,this.workingColorSpace)},getPrimaries:function(colorSpace){return this.spaces[colorSpace].primaries},getTransfer:function(colorSpace){return colorSpace===NoColorSpace?LinearTransfer:this.spaces[colorSpace].transfer},getToneMappingMode:function(colorSpace){return this.spaces[colorSpace].outputColorSpaceConfig.toneMappingMode||"standard"},getLuminanceCoefficients:function(target,colorSpace=this.workingColorSpace){return target.fromArray(this.spaces[colorSpace].luminanceCoefficients)},define:function(colorSpaces){Object.assign(this.spaces,colorSpaces)},_getMatrix:function(targetMatrix,sourceColorSpace,targetColorSpace){return targetMatrix.copy(this.spaces[sourceColorSpace].toXYZ).multiply(this.spaces[targetColorSpace].fromXYZ)},_getDrawingBufferColorSpace:function(colorSpace){return this.spaces[colorSpace].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(colorSpace=this.workingColorSpace){return this.spaces[colorSpace].workingColorSpaceConfig.unpackColorSpace},fromWorkingColorSpace:function(color,targetColorSpace){return warnOnce("ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."),ColorManagement2.workingToColorSpace(color,targetColorSpace)},toWorkingColorSpace:function(color,sourceColorSpace){return warnOnce("ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."),ColorManagement2.colorSpaceToWorking(color,sourceColorSpace)}},REC709_PRIMARIES=[.64,.33,.3,.6,.15,.06],REC709_LUMINANCE_COEFFICIENTS=[.2126,.7152,.0722],D65=[.3127,.329];return ColorManagement2.define({[LinearSRGBColorSpace]:{primaries:REC709_PRIMARIES,whitePoint:D65,transfer:LinearTransfer,toXYZ:LINEAR_REC709_TO_XYZ,fromXYZ:XYZ_TO_LINEAR_REC709,luminanceCoefficients:REC709_LUMINANCE_COEFFICIENTS,workingColorSpaceConfig:{unpackColorSpace:SRGBColorSpace},outputColorSpaceConfig:{drawingBufferColorSpace:SRGBColorSpace}},[SRGBColorSpace]:{primaries:REC709_PRIMARIES,whitePoint:D65,transfer:SRGBTransfer,toXYZ:LINEAR_REC709_TO_XYZ,fromXYZ:XYZ_TO_LINEAR_REC709,luminanceCoefficients:REC709_LUMINANCE_COEFFICIENTS,outputColorSpaceConfig:{drawingBufferColorSpace:SRGBColorSpace}}}),ColorManagement2}var ColorManagement=createColorManagement();function SRGBToLinear(c){return c<.04045?c*.0773993808:Math.pow(c*.9478672986+.0521327014,2.4)}function LinearToSRGB(c){return c<.0031308?c*12.92:1.055*Math.pow(c,.41666)-.055}var _canvas,ImageUtils=class{static getDataURL(image,type="image/png"){if(/^data:/i.test(image.src)||typeof HTMLCanvasElement>"u")return image.src;let canvas;if(image instanceof HTMLCanvasElement)canvas=image;else{_canvas===void 0&&(_canvas=createElementNS("canvas")),_canvas.width=image.width,_canvas.height=image.height;let context=_canvas.getContext("2d");image instanceof ImageData?context.putImageData(image,0,0):context.drawImage(image,0,0,image.width,image.height),canvas=_canvas}return canvas.toDataURL(type)}static sRGBToLinear(image){if(typeof HTMLImageElement<"u"&&image instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&image instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&image instanceof ImageBitmap){let canvas=createElementNS("canvas");canvas.width=image.width,canvas.height=image.height;let context=canvas.getContext("2d");context.drawImage(image,0,0,image.width,image.height);let imageData=context.getImageData(0,0,image.width,image.height),data=imageData.data;for(let i=0;i<data.length;i++)data[i]=SRGBToLinear(data[i]/255)*255;return context.putImageData(imageData,0,0),canvas}else if(image.data){let data=image.data.slice(0);for(let i=0;i<data.length;i++)data instanceof Uint8Array||data instanceof Uint8ClampedArray?data[i]=Math.floor(SRGBToLinear(data[i]/255)*255):data[i]=SRGBToLinear(data[i]);return{data,width:image.width,height:image.height}}else return warn("ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),image}};var _sourceId=0,TextureSource=class{constructor(data=null){this.isTextureSource=!0,Object.defineProperty(this,"id",{value:_sourceId++}),this.uuid=generateUUID(),this.data=data,this.dataReady=!0,this.version=0}getSize(target){let data=this.data;return typeof HTMLVideoElement<"u"&&data instanceof HTMLVideoElement?target.set(data.videoWidth,data.videoHeight,0):typeof VideoFrame<"u"&&data instanceof VideoFrame?target.set(data.displayWidth,data.displayHeight,0):data!==null?target.set(data.width,data.height,data.depth||0):target.set(0,0,0),target}set needsUpdate(value){value===!0&&this.version++}toJSON(meta){let isRootObject=meta===void 0||typeof meta=="string";if(!isRootObject&&meta.images[this.uuid]!==void 0)return meta.images[this.uuid];let output={uuid:this.uuid,url:""},data=this.data;if(data!==null){let url;if(Array.isArray(data)){url=[];for(let i=0,l=data.length;i<l;i++)data[i].isDataTexture?url.push(serializeImage(data[i].image)):url.push(serializeImage(data[i]))}else url=serializeImage(data);output.url=url}return isRootObject||(meta.images[this.uuid]=output),output}};function serializeImage(image){return typeof HTMLImageElement<"u"&&image instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&image instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&image instanceof ImageBitmap?ImageUtils.getDataURL(image):image.data?{data:Array.from(image.data),width:image.width,height:image.height,type:image.data.constructor.name}:(warn("Texture: Unable to serialize Texture."),{})}var _textureId=0,_tempVec3=new Vector3,Texture=class _Texture extends EventDispatcher{constructor(image=_Texture.DEFAULT_IMAGE,mapping=_Texture.DEFAULT_MAPPING,wrapS=ClampToEdgeWrapping,wrapT=ClampToEdgeWrapping,magFilter=LinearFilter,minFilter=LinearMipmapLinearFilter,format=RGBAFormat,type=UnsignedByteType,anisotropy=_Texture.DEFAULT_ANISOTROPY,colorSpace=NoColorSpace){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:_textureId++}),this.uuid=generateUUID(),this.name="",this.source=new TextureSource(image),this.mipmaps=[],this.mapping=mapping,this.channel=0,this.wrapS=wrapS,this.wrapT=wrapT,this.magFilter=magFilter,this.minFilter=minFilter,this.anisotropy=anisotropy,this.format=format,this.internalFormat=null,this.type=type,this.offset=new Vector2(0,0),this.repeat=new Vector2(1,1),this.center=new Vector2(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new Matrix3,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=colorSpace,this.userData={},this.updateRanges=[],this.version=0,this.onUpdate=null,this.renderTarget=null,this.isRenderTargetTexture=!1,this.isArrayTexture=!!(image&&image.depth&&image.depth>1),this.pmremVersion=0,this.normalized=!1}get width(){return this.source.getSize(_tempVec3).x}get height(){return this.source.getSize(_tempVec3).y}get depth(){return this.source.getSize(_tempVec3).z}get image(){return this.source.data}set image(value){this.source.data=value}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}addUpdateRange(start,count){this.updateRanges.push({start,count})}clearUpdateRanges(){this.updateRanges.length=0}clone(){return new this.constructor().copy(this)}copy(source){return this.name=source.name,this.source=source.source,this.mipmaps=source.mipmaps.slice(0),this.mapping=source.mapping,this.channel=source.channel,this.wrapS=source.wrapS,this.wrapT=source.wrapT,this.magFilter=source.magFilter,this.minFilter=source.minFilter,this.anisotropy=source.anisotropy,this.format=source.format,this.internalFormat=source.internalFormat,this.type=source.type,this.normalized=source.normalized,this.offset.copy(source.offset),this.repeat.copy(source.repeat),this.center.copy(source.center),this.rotation=source.rotation,this.matrixAutoUpdate=source.matrixAutoUpdate,this.matrix.copy(source.matrix),this.generateMipmaps=source.generateMipmaps,this.premultiplyAlpha=source.premultiplyAlpha,this.flipY=source.flipY,this.unpackAlignment=source.unpackAlignment,this.colorSpace=source.colorSpace,this.renderTarget=source.renderTarget,this.isRenderTargetTexture=source.isRenderTargetTexture,this.isArrayTexture=source.isArrayTexture,this.userData=JSON.parse(JSON.stringify(source.userData)),this.needsUpdate=!0,this}setValues(values){for(let key in values){let newValue=values[key];if(newValue===void 0){warn(`Texture.setValues(): parameter '${key}' has value of undefined.`);continue}let currentValue=this[key];if(currentValue===void 0){warn(`Texture.setValues(): property '${key}' does not exist.`);continue}currentValue&&newValue&&currentValue.isVector2&&newValue.isVector2||currentValue&&newValue&&currentValue.isVector3&&newValue.isVector3||currentValue&&newValue&&currentValue.isMatrix3&&newValue.isMatrix3?currentValue.copy(newValue):this[key]=newValue}}toJSON(meta){let isRootObject=meta===void 0||typeof meta=="string";if(!isRootObject&&meta.textures[this.uuid]!==void 0)return meta.textures[this.uuid];let output={metadata:{version:4.7,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(meta).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,normalized:this.normalized,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(output.userData=this.userData),isRootObject||(meta.textures[this.uuid]=output),output}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(uv){if(this.mapping!==UVMapping)return uv;if(uv.applyMatrix3(this.matrix),uv.x<0||uv.x>1)switch(this.wrapS){case RepeatWrapping:uv.x=uv.x-Math.floor(uv.x);break;case ClampToEdgeWrapping:uv.x=uv.x<0?0:1;break;case MirroredRepeatWrapping:Math.abs(Math.floor(uv.x)%2)===1?uv.x=Math.ceil(uv.x)-uv.x:uv.x=uv.x-Math.floor(uv.x);break}if(uv.y<0||uv.y>1)switch(this.wrapT){case RepeatWrapping:uv.y=uv.y-Math.floor(uv.y);break;case ClampToEdgeWrapping:uv.y=uv.y<0?0:1;break;case MirroredRepeatWrapping:Math.abs(Math.floor(uv.y)%2)===1?uv.y=Math.ceil(uv.y)-uv.y:uv.y=uv.y-Math.floor(uv.y);break}return this.flipY&&(uv.y=1-uv.y),uv}set needsUpdate(value){value===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(value){value===!0&&this.pmremVersion++}};Texture.DEFAULT_IMAGE=null;Texture.DEFAULT_MAPPING=UVMapping;Texture.DEFAULT_ANISOTROPY=1;var _Vector4=class _Vector4{constructor(x=0,y=0,z=0,w=1){this.x=x,this.y=y,this.z=z,this.w=w}get width(){return this.z}set width(value){this.z=value}get height(){return this.w}set height(value){this.w=value}set(x,y,z,w){return this.x=x,this.y=y,this.z=z,this.w=w,this}setScalar(scalar){return this.x=scalar,this.y=scalar,this.z=scalar,this.w=scalar,this}setX(x){return this.x=x,this}setY(y){return this.y=y,this}setZ(z){return this.z=z,this}setW(w){return this.w=w,this}setComponent(index,value){switch(index){case 0:this.x=value;break;case 1:this.y=value;break;case 2:this.z=value;break;case 3:this.w=value;break;default:throw new Error("THREE.Vector4: index is out of range: "+index)}return this}getComponent(index){switch(index){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("THREE.Vector4: index is out of range: "+index)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(v){return this.x=v.x,this.y=v.y,this.z=v.z,this.w=v.w!==void 0?v.w:1,this}add(v){return this.x+=v.x,this.y+=v.y,this.z+=v.z,this.w+=v.w,this}addScalar(s){return this.x+=s,this.y+=s,this.z+=s,this.w+=s,this}addVectors(a,b){return this.x=a.x+b.x,this.y=a.y+b.y,this.z=a.z+b.z,this.w=a.w+b.w,this}addScaledVector(v,s){return this.x+=v.x*s,this.y+=v.y*s,this.z+=v.z*s,this.w+=v.w*s,this}sub(v){return this.x-=v.x,this.y-=v.y,this.z-=v.z,this.w-=v.w,this}subScalar(s){return this.x-=s,this.y-=s,this.z-=s,this.w-=s,this}subVectors(a,b){return this.x=a.x-b.x,this.y=a.y-b.y,this.z=a.z-b.z,this.w=a.w-b.w,this}multiply(v){return this.x*=v.x,this.y*=v.y,this.z*=v.z,this.w*=v.w,this}multiplyScalar(scalar){return this.x*=scalar,this.y*=scalar,this.z*=scalar,this.w*=scalar,this}applyMatrix4(m){let x=this.x,y=this.y,z=this.z,w=this.w,e=m.elements;return this.x=e[0]*x+e[4]*y+e[8]*z+e[12]*w,this.y=e[1]*x+e[5]*y+e[9]*z+e[13]*w,this.z=e[2]*x+e[6]*y+e[10]*z+e[14]*w,this.w=e[3]*x+e[7]*y+e[11]*z+e[15]*w,this}divide(v){return this.x/=v.x,this.y/=v.y,this.z/=v.z,this.w/=v.w,this}divideScalar(scalar){return this.multiplyScalar(1/scalar)}setAxisAngleFromQuaternion(q){this.w=2*Math.acos(q.w);let s=Math.sqrt(1-q.w*q.w);return s<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=q.x/s,this.y=q.y/s,this.z=q.z/s),this}setAxisAngleFromRotationMatrix(m){let angle,x,y,z,te=m.elements,m11=te[0],m12=te[4],m13=te[8],m21=te[1],m22=te[5],m23=te[9],m31=te[2],m32=te[6],m33=te[10];if(Math.abs(m12-m21)<.01&&Math.abs(m13-m31)<.01&&Math.abs(m23-m32)<.01){if(Math.abs(m12+m21)<.1&&Math.abs(m13+m31)<.1&&Math.abs(m23+m32)<.1&&Math.abs(m11+m22+m33-3)<.1)return this.set(1,0,0,0),this;angle=Math.PI;let xx=(m11+1)/2,yy=(m22+1)/2,zz=(m33+1)/2,xy=(m12+m21)/4,xz=(m13+m31)/4,yz=(m23+m32)/4;return xx>yy&&xx>zz?xx<.01?(x=0,y=.707106781,z=.707106781):(x=Math.sqrt(xx),y=xy/x,z=xz/x):yy>zz?yy<.01?(x=.707106781,y=0,z=.707106781):(y=Math.sqrt(yy),x=xy/y,z=yz/y):zz<.01?(x=.707106781,y=.707106781,z=0):(z=Math.sqrt(zz),x=xz/z,y=yz/z),this.set(x,y,z,angle),this}let s=Math.sqrt((m32-m23)*(m32-m23)+(m13-m31)*(m13-m31)+(m21-m12)*(m21-m12));return Math.abs(s)<.001&&(s=1),this.x=(m32-m23)/s,this.y=(m13-m31)/s,this.z=(m21-m12)/s,this.w=Math.acos((m11+m22+m33-1)/2),this}setFromMatrixPosition(m){let e=m.elements;return this.x=e[12],this.y=e[13],this.z=e[14],this.w=e[15],this}min(v){return this.x=Math.min(this.x,v.x),this.y=Math.min(this.y,v.y),this.z=Math.min(this.z,v.z),this.w=Math.min(this.w,v.w),this}max(v){return this.x=Math.max(this.x,v.x),this.y=Math.max(this.y,v.y),this.z=Math.max(this.z,v.z),this.w=Math.max(this.w,v.w),this}clamp(min,max){return this.x=clamp(this.x,min.x,max.x),this.y=clamp(this.y,min.y,max.y),this.z=clamp(this.z,min.z,max.z),this.w=clamp(this.w,min.w,max.w),this}clampScalar(minVal,maxVal){return this.x=clamp(this.x,minVal,maxVal),this.y=clamp(this.y,minVal,maxVal),this.z=clamp(this.z,minVal,maxVal),this.w=clamp(this.w,minVal,maxVal),this}clampLength(min,max){let length=this.length();return this.divideScalar(length||1).multiplyScalar(clamp(length,min,max))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(v){return this.x*v.x+this.y*v.y+this.z*v.z+this.w*v.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(length){return this.normalize().multiplyScalar(length)}lerp(v,alpha){return this.x+=(v.x-this.x)*alpha,this.y+=(v.y-this.y)*alpha,this.z+=(v.z-this.z)*alpha,this.w+=(v.w-this.w)*alpha,this}lerpVectors(v1,v2,alpha){return this.x=v1.x+(v2.x-v1.x)*alpha,this.y=v1.y+(v2.y-v1.y)*alpha,this.z=v1.z+(v2.z-v1.z)*alpha,this.w=v1.w+(v2.w-v1.w)*alpha,this}equals(v){return v.x===this.x&&v.y===this.y&&v.z===this.z&&v.w===this.w}fromArray(array,offset=0){return this.x=array[offset],this.y=array[offset+1],this.z=array[offset+2],this.w=array[offset+3],this}toArray(array=[],offset=0){return array[offset]=this.x,array[offset+1]=this.y,array[offset+2]=this.z,array[offset+3]=this.w,array}fromBufferAttribute(attribute,index){return this.x=attribute.getX(index),this.y=attribute.getY(index),this.z=attribute.getZ(index),this.w=attribute.getW(index),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}};_Vector4.prototype.isVector4=!0;var Vector4=_Vector4;var RenderTarget=class extends EventDispatcher{constructor(width=1,height=1,options={}){super(),options=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:LinearFilter,depthBuffer:!0,stencilBuffer:!1,resolveColorBuffer:!0,resolveDepthBuffer:!0,resolveStencilBuffer:!0,storeMultisampledColorBuffer:!0,storeMultisampledDepthBuffer:!0,storeMultisampledStencilBuffer:!0,depthTexture:null,samples:0,count:1,depth:1,multiview:!1,useArrayDepthTexture:!1},options),this.isRenderTarget=!0,this.width=width,this.height=height,this.depth=options.depth,this.scissor=new Vector4(0,0,width,height),this.scissorTest=!1,this.viewport=new Vector4(0,0,width,height),this.textures=[];let image={width,height,depth:options.depth},texture=new Texture(image),count=options.count;for(let i=0;i<count;i++)this.textures[i]=texture.clone(),this.textures[i].isRenderTargetTexture=!0,this.textures[i].renderTarget=this;this._setTextureOptions(options),this.depthBuffer=options.depthBuffer,this.stencilBuffer=options.stencilBuffer,this.resolveColorBuffer=options.resolveColorBuffer,this.resolveDepthBuffer=options.resolveDepthBuffer,this.resolveStencilBuffer=options.resolveStencilBuffer,this.storeMultisampledColorBuffer=options.storeMultisampledColorBuffer,this.storeMultisampledDepthBuffer=options.storeMultisampledDepthBuffer,this.storeMultisampledStencilBuffer=options.storeMultisampledStencilBuffer,this._depthTexture=null,this.depthTexture=options.depthTexture,this.samples=options.samples,this.multiview=options.multiview,this.useArrayDepthTexture=options.useArrayDepthTexture}_setTextureOptions(options={}){let values={minFilter:LinearFilter,generateMipmaps:!1,flipY:!1,internalFormat:null};options.mapping!==void 0&&(values.mapping=options.mapping),options.wrapS!==void 0&&(values.wrapS=options.wrapS),options.wrapT!==void 0&&(values.wrapT=options.wrapT),options.wrapR!==void 0&&(values.wrapR=options.wrapR),options.magFilter!==void 0&&(values.magFilter=options.magFilter),options.minFilter!==void 0&&(values.minFilter=options.minFilter),options.format!==void 0&&(values.format=options.format),options.type!==void 0&&(values.type=options.type),options.anisotropy!==void 0&&(values.anisotropy=options.anisotropy),options.colorSpace!==void 0&&(values.colorSpace=options.colorSpace),options.flipY!==void 0&&(values.flipY=options.flipY),options.generateMipmaps!==void 0&&(values.generateMipmaps=options.generateMipmaps),options.internalFormat!==void 0&&(values.internalFormat=options.internalFormat);for(let i=0;i<this.textures.length;i++)this.textures[i].setValues(values)}get texture(){return this.textures[0]}set texture(value){this.textures[0]=value}set depthTexture(current){this._depthTexture!==null&&this._depthTexture.renderTarget===this&&(this._depthTexture.renderTarget=null),current!==null&&current.renderTarget===null&&(current.renderTarget=this),this._depthTexture=current}get depthTexture(){return this._depthTexture}setSize(width,height,depth=1){if(this.width!==width||this.height!==height||this.depth!==depth){this.width=width,this.height=height,this.depth=depth;for(let i=0,il=this.textures.length;i<il;i++)this.textures[i].image.width=width,this.textures[i].image.height=height,this.textures[i].image.depth=depth,this.textures[i].isData3DTexture!==!0&&(this.textures[i].isArrayTexture=this.textures[i].image.depth>1);this.dispose()}this.viewport.set(0,0,width,height),this.scissor.set(0,0,width,height)}clone(){return new this.constructor().copy(this)}copy(source){this.width=source.width,this.height=source.height,this.depth=source.depth,this.scissor.copy(source.scissor),this.scissorTest=source.scissorTest,this.viewport.copy(source.viewport),this.textures.length=0;for(let i=0,il=source.textures.length;i<il;i++){this.textures[i]=source.textures[i].clone(),this.textures[i].isRenderTargetTexture=!0,this.textures[i].renderTarget=this;let image=Object.assign({},source.textures[i].image);this.textures[i].source=new TextureSource(image)}if(this.depthBuffer=source.depthBuffer,this.stencilBuffer=source.stencilBuffer,this.resolveColorBuffer=source.resolveColorBuffer,this.resolveDepthBuffer=source.resolveDepthBuffer,this.resolveStencilBuffer=source.resolveStencilBuffer,this.storeMultisampledColorBuffer=source.storeMultisampledColorBuffer,this.storeMultisampledDepthBuffer=source.storeMultisampledDepthBuffer,this.storeMultisampledStencilBuffer=source.storeMultisampledStencilBuffer,source.depthTexture!==null)if(source.depthTexture.renderTarget===source){let depthTexture=source.depthTexture.clone();depthTexture.renderTarget=null,this.depthTexture=depthTexture}else this.depthTexture=source.depthTexture;return this.samples=source.samples,this.multiview=source.multiview,this.useArrayDepthTexture=source.useArrayDepthTexture,this}dispose(){this.dispatchEvent({type:"dispose"})}};var WebGLRenderTarget=class extends RenderTarget{constructor(width=1,height=1,options={}){super(width,height,options),this.isWebGLRenderTarget=!0}};var DataArrayTexture=class extends Texture{constructor(data=null,width=1,height=1,depth=1){super(null),this.isDataArrayTexture=!0,this.image={data,width,height,depth},this.magFilter=NearestFilter,this.minFilter=NearestFilter,this.wrapR=ClampToEdgeWrapping,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}copy(source){return super.copy(source),this.wrapR=source.wrapR,this}addLayerUpdate(layerIndex){this.layerUpdates.add(layerIndex)}clearLayerUpdates(){this.layerUpdates.clear()}};var Data3DTexture=class extends Texture{constructor(data=null,width=1,height=1,depth=1){super(null),this.isData3DTexture=!0,this.image={data,width,height,depth},this.magFilter=NearestFilter,this.minFilter=NearestFilter,this.wrapR=ClampToEdgeWrapping,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}copy(source){return super.copy(source),this.wrapR=source.wrapR,this}};var _Matrix4=class _Matrix4{constructor(n11,n12,n13,n14,n21,n22,n23,n24,n31,n32,n33,n34,n41,n42,n43,n44){this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],n11!==void 0&&this.set(n11,n12,n13,n14,n21,n22,n23,n24,n31,n32,n33,n34,n41,n42,n43,n44)}set(n11,n12,n13,n14,n21,n22,n23,n24,n31,n32,n33,n34,n41,n42,n43,n44){let te=this.elements;return te[0]=n11,te[4]=n12,te[8]=n13,te[12]=n14,te[1]=n21,te[5]=n22,te[9]=n23,te[13]=n24,te[2]=n31,te[6]=n32,te[10]=n33,te[14]=n34,te[3]=n41,te[7]=n42,te[11]=n43,te[15]=n44,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new _Matrix4().fromArray(this.elements)}copy(m){let te=this.elements,me=m.elements;return te[0]=me[0],te[1]=me[1],te[2]=me[2],te[3]=me[3],te[4]=me[4],te[5]=me[5],te[6]=me[6],te[7]=me[7],te[8]=me[8],te[9]=me[9],te[10]=me[10],te[11]=me[11],te[12]=me[12],te[13]=me[13],te[14]=me[14],te[15]=me[15],this}copyPosition(m){let te=this.elements,me=m.elements;return te[12]=me[12],te[13]=me[13],te[14]=me[14],this}setFromMatrix3(m){let me=m.elements;return this.set(me[0],me[3],me[6],0,me[1],me[4],me[7],0,me[2],me[5],me[8],0,0,0,0,1),this}extractBasis(xAxis,yAxis,zAxis){return this.determinantAffine()===0?(xAxis.set(1,0,0),yAxis.set(0,1,0),zAxis.set(0,0,1),this):(xAxis.setFromMatrixColumn(this,0),yAxis.setFromMatrixColumn(this,1),zAxis.setFromMatrixColumn(this,2),this)}makeBasis(xAxis,yAxis,zAxis){return this.set(xAxis.x,yAxis.x,zAxis.x,0,xAxis.y,yAxis.y,zAxis.y,0,xAxis.z,yAxis.z,zAxis.z,0,0,0,0,1),this}extractRotation(m){if(m.determinantAffine()===0)return this.identity();let te=this.elements,me=m.elements,scaleX=1/_v1.setFromMatrixColumn(m,0).length(),scaleY=1/_v1.setFromMatrixColumn(m,1).length(),scaleZ=1/_v1.setFromMatrixColumn(m,2).length();return te[0]=me[0]*scaleX,te[1]=me[1]*scaleX,te[2]=me[2]*scaleX,te[3]=0,te[4]=me[4]*scaleY,te[5]=me[5]*scaleY,te[6]=me[6]*scaleY,te[7]=0,te[8]=me[8]*scaleZ,te[9]=me[9]*scaleZ,te[10]=me[10]*scaleZ,te[11]=0,te[12]=0,te[13]=0,te[14]=0,te[15]=1,this}makeRotationFromEuler(euler){let te=this.elements,x=euler.x,y=euler.y,z=euler.z,a=Math.cos(x),b=Math.sin(x),c=Math.cos(y),d=Math.sin(y),e=Math.cos(z),f=Math.sin(z);if(euler.order==="XYZ"){let ae=a*e,af=a*f,be=b*e,bf=b*f;te[0]=c*e,te[4]=-c*f,te[8]=d,te[1]=af+be*d,te[5]=ae-bf*d,te[9]=-b*c,te[2]=bf-ae*d,te[6]=be+af*d,te[10]=a*c}else if(euler.order==="YXZ"){let ce=c*e,cf=c*f,de=d*e,df=d*f;te[0]=ce+df*b,te[4]=de*b-cf,te[8]=a*d,te[1]=a*f,te[5]=a*e,te[9]=-b,te[2]=cf*b-de,te[6]=df+ce*b,te[10]=a*c}else if(euler.order==="ZXY"){let ce=c*e,cf=c*f,de=d*e,df=d*f;te[0]=ce-df*b,te[4]=-a*f,te[8]=de+cf*b,te[1]=cf+de*b,te[5]=a*e,te[9]=df-ce*b,te[2]=-a*d,te[6]=b,te[10]=a*c}else if(euler.order==="ZYX"){let ae=a*e,af=a*f,be=b*e,bf=b*f;te[0]=c*e,te[4]=be*d-af,te[8]=ae*d+bf,te[1]=c*f,te[5]=bf*d+ae,te[9]=af*d-be,te[2]=-d,te[6]=b*c,te[10]=a*c}else if(euler.order==="YZX"){let ac=a*c,ad=a*d,bc=b*c,bd=b*d;te[0]=c*e,te[4]=bd-ac*f,te[8]=bc*f+ad,te[1]=f,te[5]=a*e,te[9]=-b*e,te[2]=-d*e,te[6]=ad*f+bc,te[10]=ac-bd*f}else if(euler.order==="XZY"){let ac=a*c,ad=a*d,bc=b*c,bd=b*d;te[0]=c*e,te[4]=-f,te[8]=d*e,te[1]=ac*f+bd,te[5]=a*e,te[9]=ad*f-bc,te[2]=bc*f-ad,te[6]=b*e,te[10]=bd*f+ac}return te[3]=0,te[7]=0,te[11]=0,te[12]=0,te[13]=0,te[14]=0,te[15]=1,this}makeRotationFromQuaternion(q){return this.compose(_zero,q,_one)}lookAt(eye,target,up){let te=this.elements;return _z.subVectors(eye,target),_z.lengthSq()===0&&(_z.z=1),_z.normalize(),_x.crossVectors(up,_z),_x.lengthSq()===0&&(Math.abs(up.z)===1?_z.x+=1e-4:_z.z+=1e-4,_z.normalize(),_x.crossVectors(up,_z)),_x.normalize(),_y.crossVectors(_z,_x),te[0]=_x.x,te[4]=_y.x,te[8]=_z.x,te[1]=_x.y,te[5]=_y.y,te[9]=_z.y,te[2]=_x.z,te[6]=_y.z,te[10]=_z.z,this}multiply(m){return this.multiplyMatrices(this,m)}premultiply(m){return this.multiplyMatrices(m,this)}multiplyMatrices(a,b){let ae=a.elements,be=b.elements,te=this.elements,a11=ae[0],a12=ae[4],a13=ae[8],a14=ae[12],a21=ae[1],a22=ae[5],a23=ae[9],a24=ae[13],a31=ae[2],a32=ae[6],a33=ae[10],a34=ae[14],a41=ae[3],a42=ae[7],a43=ae[11],a44=ae[15],b11=be[0],b12=be[4],b13=be[8],b14=be[12],b21=be[1],b22=be[5],b23=be[9],b24=be[13],b31=be[2],b32=be[6],b33=be[10],b34=be[14],b41=be[3],b42=be[7],b43=be[11],b44=be[15];return te[0]=a11*b11+a12*b21+a13*b31+a14*b41,te[4]=a11*b12+a12*b22+a13*b32+a14*b42,te[8]=a11*b13+a12*b23+a13*b33+a14*b43,te[12]=a11*b14+a12*b24+a13*b34+a14*b44,te[1]=a21*b11+a22*b21+a23*b31+a24*b41,te[5]=a21*b12+a22*b22+a23*b32+a24*b42,te[9]=a21*b13+a22*b23+a23*b33+a24*b43,te[13]=a21*b14+a22*b24+a23*b34+a24*b44,te[2]=a31*b11+a32*b21+a33*b31+a34*b41,te[6]=a31*b12+a32*b22+a33*b32+a34*b42,te[10]=a31*b13+a32*b23+a33*b33+a34*b43,te[14]=a31*b14+a32*b24+a33*b34+a34*b44,te[3]=a41*b11+a42*b21+a43*b31+a44*b41,te[7]=a41*b12+a42*b22+a43*b32+a44*b42,te[11]=a41*b13+a42*b23+a43*b33+a44*b43,te[15]=a41*b14+a42*b24+a43*b34+a44*b44,this}multiplyScalar(s){let te=this.elements;return te[0]*=s,te[4]*=s,te[8]*=s,te[12]*=s,te[1]*=s,te[5]*=s,te[9]*=s,te[13]*=s,te[2]*=s,te[6]*=s,te[10]*=s,te[14]*=s,te[3]*=s,te[7]*=s,te[11]*=s,te[15]*=s,this}determinant(){let te=this.elements,n11=te[0],n12=te[4],n13=te[8],n14=te[12],n21=te[1],n22=te[5],n23=te[9],n24=te[13],n31=te[2],n32=te[6],n33=te[10],n34=te[14],n41=te[3],n42=te[7],n43=te[11],n44=te[15],t11=n23*n34-n24*n33,t12=n22*n34-n24*n32,t13=n22*n33-n23*n32,t21=n21*n34-n24*n31,t22=n21*n33-n23*n31,t23=n21*n32-n22*n31;return n11*(n42*t11-n43*t12+n44*t13)-n12*(n41*t11-n43*t21+n44*t22)+n13*(n41*t12-n42*t21+n44*t23)-n14*(n41*t13-n42*t22+n43*t23)}determinantAffine(){let te=this.elements,n11=te[0],n12=te[4],n13=te[8],n21=te[1],n22=te[5],n23=te[9],n31=te[2],n32=te[6],n33=te[10];return n11*(n22*n33-n23*n32)-n12*(n21*n33-n23*n31)+n13*(n21*n32-n22*n31)}transpose(){let te=this.elements,tmp3;return tmp3=te[1],te[1]=te[4],te[4]=tmp3,tmp3=te[2],te[2]=te[8],te[8]=tmp3,tmp3=te[6],te[6]=te[9],te[9]=tmp3,tmp3=te[3],te[3]=te[12],te[12]=tmp3,tmp3=te[7],te[7]=te[13],te[13]=tmp3,tmp3=te[11],te[11]=te[14],te[14]=tmp3,this}setPosition(x,y,z){let te=this.elements;return x.isVector3?(te[12]=x.x,te[13]=x.y,te[14]=x.z):(te[12]=x,te[13]=y,te[14]=z),this}invert(){let te=this.elements,n11=te[0],n21=te[1],n31=te[2],n41=te[3],n12=te[4],n22=te[5],n32=te[6],n42=te[7],n13=te[8],n23=te[9],n33=te[10],n43=te[11],n14=te[12],n24=te[13],n34=te[14],n44=te[15],t1=n11*n22-n21*n12,t2=n11*n32-n31*n12,t3=n11*n42-n41*n12,t4=n21*n32-n31*n22,t5=n21*n42-n41*n22,t6=n31*n42-n41*n32,t7=n13*n24-n23*n14,t8=n13*n34-n33*n14,t9=n13*n44-n43*n14,t10=n23*n34-n33*n24,t11=n23*n44-n43*n24,t12=n33*n44-n43*n34,det=t1*t12-t2*t11+t3*t10+t4*t9-t5*t8+t6*t7;if(det===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);let detInv=1/det;return te[0]=(n22*t12-n32*t11+n42*t10)*detInv,te[1]=(n31*t11-n21*t12-n41*t10)*detInv,te[2]=(n24*t6-n34*t5+n44*t4)*detInv,te[3]=(n33*t5-n23*t6-n43*t4)*detInv,te[4]=(n32*t9-n12*t12-n42*t8)*detInv,te[5]=(n11*t12-n31*t9+n41*t8)*detInv,te[6]=(n34*t3-n14*t6-n44*t2)*detInv,te[7]=(n13*t6-n33*t3+n43*t2)*detInv,te[8]=(n12*t11-n22*t9+n42*t7)*detInv,te[9]=(n21*t9-n11*t11-n41*t7)*detInv,te[10]=(n14*t5-n24*t3+n44*t1)*detInv,te[11]=(n23*t3-n13*t5-n43*t1)*detInv,te[12]=(n22*t8-n12*t10-n32*t7)*detInv,te[13]=(n11*t10-n21*t8+n31*t7)*detInv,te[14]=(n24*t2-n14*t4-n34*t1)*detInv,te[15]=(n13*t4-n23*t2+n33*t1)*detInv,this}scale(v){let te=this.elements,x=v.x,y=v.y,z=v.z;return te[0]*=x,te[4]*=y,te[8]*=z,te[1]*=x,te[5]*=y,te[9]*=z,te[2]*=x,te[6]*=y,te[10]*=z,te[3]*=x,te[7]*=y,te[11]*=z,this}getMaxScaleOnAxis(){let te=this.elements,scaleXSq=te[0]*te[0]+te[1]*te[1]+te[2]*te[2],scaleYSq=te[4]*te[4]+te[5]*te[5]+te[6]*te[6],scaleZSq=te[8]*te[8]+te[9]*te[9]+te[10]*te[10];return Math.sqrt(Math.max(scaleXSq,scaleYSq,scaleZSq))}makeTranslation(x,y,z){return x.isVector3?this.set(1,0,0,x.x,0,1,0,x.y,0,0,1,x.z,0,0,0,1):this.set(1,0,0,x,0,1,0,y,0,0,1,z,0,0,0,1),this}makeRotationX(theta){let c=Math.cos(theta),s=Math.sin(theta);return this.set(1,0,0,0,0,c,-s,0,0,s,c,0,0,0,0,1),this}makeRotationY(theta){let c=Math.cos(theta),s=Math.sin(theta);return this.set(c,0,s,0,0,1,0,0,-s,0,c,0,0,0,0,1),this}makeRotationZ(theta){let c=Math.cos(theta),s=Math.sin(theta);return this.set(c,-s,0,0,s,c,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(axis,angle){let c=Math.cos(angle),s=Math.sin(angle),t=1-c,x=axis.x,y=axis.y,z=axis.z,tx=t*x,ty=t*y;return this.set(tx*x+c,tx*y-s*z,tx*z+s*y,0,tx*y+s*z,ty*y+c,ty*z-s*x,0,tx*z-s*y,ty*z+s*x,t*z*z+c,0,0,0,0,1),this}makeScale(x,y,z){return this.set(x,0,0,0,0,y,0,0,0,0,z,0,0,0,0,1),this}makeShear(xy,xz,yx,yz,zx,zy){return this.set(1,yx,zx,0,xy,1,zy,0,xz,yz,1,0,0,0,0,1),this}compose(position,quaternion,scale){let te=this.elements,x=quaternion._x,y=quaternion._y,z=quaternion._z,w=quaternion._w,x2=x+x,y2=y+y,z2=z+z,xx=x*x2,xy=x*y2,xz=x*z2,yy=y*y2,yz=y*z2,zz=z*z2,wx=w*x2,wy=w*y2,wz=w*z2,sx=scale.x,sy=scale.y,sz=scale.z;return te[0]=(1-(yy+zz))*sx,te[1]=(xy+wz)*sx,te[2]=(xz-wy)*sx,te[3]=0,te[4]=(xy-wz)*sy,te[5]=(1-(xx+zz))*sy,te[6]=(yz+wx)*sy,te[7]=0,te[8]=(xz+wy)*sz,te[9]=(yz-wx)*sz,te[10]=(1-(xx+yy))*sz,te[11]=0,te[12]=position.x,te[13]=position.y,te[14]=position.z,te[15]=1,this}decompose(position,quaternion,scale){let te=this.elements;position.x=te[12],position.y=te[13],position.z=te[14];let det=this.determinantAffine();if(det===0)return scale.set(1,1,1),quaternion.identity(),this;let sx=_v1.set(te[0],te[1],te[2]).length(),sy=_v1.set(te[4],te[5],te[6]).length(),sz=_v1.set(te[8],te[9],te[10]).length();det<0&&(sx=-sx),_m1.copy(this);let invSX=1/sx,invSY=1/sy,invSZ=1/sz;return _m1.elements[0]*=invSX,_m1.elements[1]*=invSX,_m1.elements[2]*=invSX,_m1.elements[4]*=invSY,_m1.elements[5]*=invSY,_m1.elements[6]*=invSY,_m1.elements[8]*=invSZ,_m1.elements[9]*=invSZ,_m1.elements[10]*=invSZ,quaternion.setFromRotationMatrix(_m1),scale.x=sx,scale.y=sy,scale.z=sz,this}makePerspective(left,right,top,bottom,near,far,coordinateSystem=WebGLCoordinateSystem,reversedDepth=!1){let te=this.elements,x=2*near/(right-left),y=2*near/(top-bottom),a=(right+left)/(right-left),b=(top+bottom)/(top-bottom),c,d;if(reversedDepth)c=near/(far-near),d=far*near/(far-near);else if(coordinateSystem===WebGLCoordinateSystem)c=-(far+near)/(far-near),d=-2*far*near/(far-near);else if(coordinateSystem===WebGPUCoordinateSystem)c=-far/(far-near),d=-far*near/(far-near);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+coordinateSystem);return te[0]=x,te[4]=0,te[8]=a,te[12]=0,te[1]=0,te[5]=y,te[9]=b,te[13]=0,te[2]=0,te[6]=0,te[10]=c,te[14]=d,te[3]=0,te[7]=0,te[11]=-1,te[15]=0,this}makeOrthographic(left,right,top,bottom,near,far,coordinateSystem=WebGLCoordinateSystem,reversedDepth=!1){let te=this.elements,x=2/(right-left),y=2/(top-bottom),a=-(right+left)/(right-left),b=-(top+bottom)/(top-bottom),c,d;if(reversedDepth)c=1/(far-near),d=far/(far-near);else if(coordinateSystem===WebGLCoordinateSystem)c=-2/(far-near),d=-(far+near)/(far-near);else if(coordinateSystem===WebGPUCoordinateSystem)c=-1/(far-near),d=-near/(far-near);else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+coordinateSystem);return te[0]=x,te[4]=0,te[8]=0,te[12]=a,te[1]=0,te[5]=y,te[9]=0,te[13]=b,te[2]=0,te[6]=0,te[10]=c,te[14]=d,te[3]=0,te[7]=0,te[11]=0,te[15]=1,this}equals(matrix){let te=this.elements,me=matrix.elements;for(let i=0;i<16;i++)if(te[i]!==me[i])return!1;return!0}fromArray(array,offset=0){for(let i=0;i<16;i++)this.elements[i]=array[i+offset];return this}toArray(array=[],offset=0){let te=this.elements;return array[offset]=te[0],array[offset+1]=te[1],array[offset+2]=te[2],array[offset+3]=te[3],array[offset+4]=te[4],array[offset+5]=te[5],array[offset+6]=te[6],array[offset+7]=te[7],array[offset+8]=te[8],array[offset+9]=te[9],array[offset+10]=te[10],array[offset+11]=te[11],array[offset+12]=te[12],array[offset+13]=te[13],array[offset+14]=te[14],array[offset+15]=te[15],array}};_Matrix4.prototype.isMatrix4=!0;var Matrix4=_Matrix4,_v1=new Vector3,_m1=new Matrix4,_zero=new Vector3(0,0,0),_one=new Vector3(1,1,1),_x=new Vector3,_y=new Vector3,_z=new Vector3;var _matrix=new Matrix4,_quaternion2=new Quaternion,Euler=class _Euler{constructor(x=0,y=0,z=0,order=_Euler.DEFAULT_ORDER){this.isEuler=!0,this._x=x,this._y=y,this._z=z,this._order=order}get x(){return this._x}set x(value){this._x=value,this._onChangeCallback()}get y(){return this._y}set y(value){this._y=value,this._onChangeCallback()}get z(){return this._z}set z(value){this._z=value,this._onChangeCallback()}get order(){return this._order}set order(value){this._order=value,this._onChangeCallback()}set(x,y,z,order=this._order){return this._x=x,this._y=y,this._z=z,this._order=order,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(euler){return this._x=euler._x,this._y=euler._y,this._z=euler._z,this._order=euler._order,this._onChangeCallback(),this}setFromRotationMatrix(m,order=this._order,update=!0){let te=m.elements,m11=te[0],m12=te[4],m13=te[8],m21=te[1],m22=te[5],m23=te[9],m31=te[2],m32=te[6],m33=te[10];switch(order){case"XYZ":this._y=Math.asin(clamp(m13,-1,1)),Math.abs(m13)<.9999999?(this._x=Math.atan2(-m23,m33),this._z=Math.atan2(-m12,m11)):(this._x=Math.atan2(m32,m22),this._z=0);break;case"YXZ":this._x=Math.asin(-clamp(m23,-1,1)),Math.abs(m23)<.9999999?(this._y=Math.atan2(m13,m33),this._z=Math.atan2(m21,m22)):(this._y=Math.atan2(-m31,m11),this._z=0);break;case"ZXY":this._x=Math.asin(clamp(m32,-1,1)),Math.abs(m32)<.9999999?(this._y=Math.atan2(-m31,m33),this._z=Math.atan2(-m12,m22)):(this._y=0,this._z=Math.atan2(m21,m11));break;case"ZYX":this._y=Math.asin(-clamp(m31,-1,1)),Math.abs(m31)<.9999999?(this._x=Math.atan2(m32,m33),this._z=Math.atan2(m21,m11)):(this._x=0,this._z=Math.atan2(-m12,m22));break;case"YZX":this._z=Math.asin(clamp(m21,-1,1)),Math.abs(m21)<.9999999?(this._x=Math.atan2(-m23,m22),this._y=Math.atan2(-m31,m11)):(this._x=0,this._y=Math.atan2(m13,m33));break;case"XZY":this._z=Math.asin(-clamp(m12,-1,1)),Math.abs(m12)<.9999999?(this._x=Math.atan2(m32,m22),this._y=Math.atan2(m13,m11)):(this._x=Math.atan2(-m23,m33),this._y=0);break;default:warn("Euler: .setFromRotationMatrix() encountered an unknown order: "+order)}return this._order=order,update===!0&&this._onChangeCallback(),this}setFromQuaternion(q,order,update){return _matrix.makeRotationFromQuaternion(q),this.setFromRotationMatrix(_matrix,order,update)}setFromVector3(v,order=this._order){return this.set(v.x,v.y,v.z,order)}reorder(newOrder){return _quaternion2.setFromEuler(this),this.setFromQuaternion(_quaternion2,newOrder)}equals(euler){return euler._x===this._x&&euler._y===this._y&&euler._z===this._z&&euler._order===this._order}fromArray(array){return this._x=array[0],this._y=array[1],this._z=array[2],array[3]!==void 0&&(this._order=array[3]),this._onChangeCallback(),this}toArray(array=[],offset=0){return array[offset]=this._x,array[offset+1]=this._y,array[offset+2]=this._z,array[offset+3]=this._order,array}_onChange(callback){return this._onChangeCallback=callback,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}};Euler.DEFAULT_ORDER="XYZ";var Layers=class{constructor(){this.mask=1}set(layer){this.mask=(1<<layer|0)>>>0}enable(layer){this.mask|=1<<layer|0}enableAll(){this.mask=-1}toggle(layer){this.mask^=1<<layer|0}disable(layer){this.mask&=~(1<<layer|0)}disableAll(){this.mask=0}test(layers){return(this.mask&layers.mask)!==0}isEnabled(layer){return(this.mask&(1<<layer|0))!==0}};var _object3DId=0,_v12=new Vector3,_q1=new Quaternion,_m12=new Matrix4,_target=new Vector3,_position=new Vector3,_scale=new Vector3,_quaternion3=new Quaternion,_xAxis=new Vector3(1,0,0),_yAxis=new Vector3(0,1,0),_zAxis=new Vector3(0,0,1),_addedEvent={type:"added"},_removedEvent={type:"removed"},_childaddedEvent={type:"childadded",child:null},_childremovedEvent={type:"childremoved",child:null},Object3D=class _Object3D extends EventDispatcher{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:_object3DId++}),this.uuid=generateUUID(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=_Object3D.DEFAULT_UP.clone();let position=new Vector3,rotation=new Euler,quaternion=new Quaternion,scale=new Vector3(1,1,1);function onRotationChange(){quaternion.setFromEuler(rotation,!1)}function onQuaternionChange(){rotation.setFromQuaternion(quaternion,void 0,!1)}rotation._onChange(onRotationChange),quaternion._onChange(onQuaternionChange),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:position},rotation:{configurable:!0,enumerable:!0,value:rotation},quaternion:{configurable:!0,enumerable:!0,value:quaternion},scale:{configurable:!0,enumerable:!0,value:scale},modelViewMatrix:{value:new Matrix4},normalMatrix:{value:new Matrix3}}),this.matrix=new Matrix4,this.matrixWorld=new Matrix4,this.matrixAutoUpdate=_Object3D.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=_Object3D.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new Layers,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.customDepthMaterial=void 0,this.customDistanceMaterial=void 0,this.static=!1,this.userData={},this.pivot=null}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(matrix){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(matrix),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(q){return this.quaternion.premultiply(q),this}setRotationFromAxisAngle(axis,angle){this.quaternion.setFromAxisAngle(axis,angle)}setRotationFromEuler(euler){this.quaternion.setFromEuler(euler,!0)}setRotationFromMatrix(m){this.quaternion.setFromRotationMatrix(m)}setRotationFromQuaternion(q){this.quaternion.copy(q)}rotateOnAxis(axis,angle){return _q1.setFromAxisAngle(axis,angle),this.quaternion.multiply(_q1),this}rotateOnWorldAxis(axis,angle){return _q1.setFromAxisAngle(axis,angle),this.quaternion.premultiply(_q1),this}rotateX(angle){return this.rotateOnAxis(_xAxis,angle)}rotateY(angle){return this.rotateOnAxis(_yAxis,angle)}rotateZ(angle){return this.rotateOnAxis(_zAxis,angle)}translateOnAxis(axis,distance){return _v12.copy(axis).applyQuaternion(this.quaternion),this.position.add(_v12.multiplyScalar(distance)),this}translateX(distance){return this.translateOnAxis(_xAxis,distance)}translateY(distance){return this.translateOnAxis(_yAxis,distance)}translateZ(distance){return this.translateOnAxis(_zAxis,distance)}localToWorld(vector){return this.updateWorldMatrix(!0,!1),vector.applyMatrix4(this.matrixWorld)}worldToLocal(vector){return this.updateWorldMatrix(!0,!1),vector.applyMatrix4(_m12.copy(this.matrixWorld).invert())}lookAt(x,y,z){x.isVector3?_target.copy(x):_target.set(x,y,z);let parent=this.parent;this.updateWorldMatrix(!0,!1),_position.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?_m12.lookAt(_position,_target,this.up):_m12.lookAt(_target,_position,this.up),this.quaternion.setFromRotationMatrix(_m12),parent&&(_m12.extractRotation(parent.matrixWorld),_q1.setFromRotationMatrix(_m12),this.quaternion.premultiply(_q1.invert()))}add(object){if(arguments.length>1){for(let i=0;i<arguments.length;i++)this.add(arguments[i]);return this}return object===this?(error("Object3D.add: object can't be added as a child of itself.",object),this):(object&&object.isObject3D?(object.removeFromParent(),object.parent=this,this.children.push(object),object.dispatchEvent(_addedEvent),_childaddedEvent.child=object,this.dispatchEvent(_childaddedEvent),_childaddedEvent.child=null):error("Object3D.add: object not an instance of THREE.Object3D.",object),this)}remove(object){if(arguments.length>1){for(let i=0;i<arguments.length;i++)this.remove(arguments[i]);return this}let index=this.children.indexOf(object);return index!==-1&&(object.parent=null,this.children.splice(index,1),object.dispatchEvent(_removedEvent),_childremovedEvent.child=object,this.dispatchEvent(_childremovedEvent),_childremovedEvent.child=null),this}removeFromParent(){let parent=this.parent;return parent!==null&&parent.remove(this),this}clear(){return this.remove(...this.children)}attach(object){return this.updateWorldMatrix(!0,!1),_m12.copy(this.matrixWorld).invert(),object.parent!==null&&(object.parent.updateWorldMatrix(!0,!1),_m12.multiply(object.parent.matrixWorld)),object.applyMatrix4(_m12),object.removeFromParent(),object.parent=this,this.children.push(object),object.updateWorldMatrix(!1,!0),object.dispatchEvent(_addedEvent),_childaddedEvent.child=object,this.dispatchEvent(_childaddedEvent),_childaddedEvent.child=null,this}getObjectById(id){return this.getObjectByProperty("id",id)}getObjectByName(name){return this.getObjectByProperty("name",name)}getObjectByProperty(name,value){if(this[name]===value)return this;for(let i=0,l=this.children.length;i<l;i++){let object=this.children[i].getObjectByProperty(name,value);if(object!==void 0)return object}}getObjectsByProperty(name,value,result=[]){this[name]===value&&result.push(this);let children=this.children;for(let i=0,l=children.length;i<l;i++)children[i].getObjectsByProperty(name,value,result);return result}getWorldPosition(target){return this.updateWorldMatrix(!0,!1),target.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(target){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(_position,target,_scale),target}getWorldScale(target){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(_position,_quaternion3,target),target}getWorldDirection(target){this.updateWorldMatrix(!0,!1);let e=this.matrixWorld.elements;return target.set(e[8],e[9],e[10]).normalize()}raycast(){}intersectsFrustum(){}traverse(callback){callback(this);let children=this.children;for(let i=0,l=children.length;i<l;i++)children[i].traverse(callback)}traverseVisible(callback){if(this.visible===!1)return;callback(this);let children=this.children;for(let i=0,l=children.length;i<l;i++)children[i].traverseVisible(callback)}traverseAncestors(callback){let parent=this.parent;parent!==null&&(callback(parent),parent.traverseAncestors(callback))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale);let pivot=this.pivot;if(pivot!==null){let px2=pivot.x,py2=pivot.y,pz2=pivot.z,te=this.matrix.elements;te[12]+=px2-te[0]*px2-te[4]*py2-te[8]*pz2,te[13]+=py2-te[1]*px2-te[5]*py2-te[9]*pz2,te[14]+=pz2-te[2]*px2-te[6]*py2-te[10]*pz2}this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(force){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||force)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,force=!0);let children=this.children;for(let i=0,l=children.length;i<l;i++)children[i].updateMatrixWorld(force)}updateWorldMatrix(updateParents,updateChildren,force=!1){let parent=this.parent;if(updateParents===!0&&parent!==null&&parent.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||force)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,force=!0),updateChildren===!0){let children=this.children;for(let i=0,l=children.length;i<l;i++)children[i].updateWorldMatrix(!1,!0,force)}}toJSON(meta){let isRootObject=meta===void 0||typeof meta=="string",output={};isRootObject&&(meta={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},output.metadata={version:4.7,type:"Object",generator:"Object3D.toJSON"});let object={};object.uuid=this.uuid,object.type=this.type,object.name=this.name,object.castShadow=this.castShadow,object.receiveShadow=this.receiveShadow,object.visible=this.visible,object.frustumCulled=this.frustumCulled,object.renderOrder=this.renderOrder,object.static=this.static,object.matrixAutoUpdate=this.matrixAutoUpdate,Object.keys(this.userData).length>0&&(object.userData=this.userData),object.layers=this.layers.mask,object.matrix=this.matrix.toArray(),object.up=this.up.toArray(),this.pivot!==null&&(object.pivot=this.pivot.toArray()),this.morphTargetDictionary!==void 0&&(object.morphTargetDictionary=Object.assign({},this.morphTargetDictionary)),this.morphTargetInfluences!==void 0&&(object.morphTargetInfluences=this.morphTargetInfluences.slice()),this.isInstancedMesh&&(object.type="InstancedMesh",object.count=this.count,object.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(object.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(object.type="BatchedMesh",object.perObjectFrustumCulled=this.perObjectFrustumCulled,object.sortObjects=this.sortObjects,object.drawRanges=this._drawRanges,object.reservedRanges=this._reservedRanges,object.geometryInfo=this._geometryInfo.map(info=>({...info,boundingBox:info.boundingBox?info.boundingBox.toJSON():void 0,boundingSphere:info.boundingSphere?info.boundingSphere.toJSON():void 0})),object.instanceInfo=this._instanceInfo.map(info=>({...info})),object.availableInstanceIds=this._availableInstanceIds.slice(),object.availableGeometryIds=this._availableGeometryIds.slice(),object.nextIndexStart=this._nextIndexStart,object.nextVertexStart=this._nextVertexStart,object.geometryCount=this._geometryCount,object.maxInstanceCount=this._maxInstanceCount,object.maxVertexCount=this._maxVertexCount,object.maxIndexCount=this._maxIndexCount,object.geometryInitialized=this._geometryInitialized,object.matricesTexture=this._matricesTexture.toJSON(meta),object.indirectTexture=this._indirectTexture.toJSON(meta),this._colorsTexture!==null&&(object.colorsTexture=this._colorsTexture.toJSON(meta)),this.boundingSphere!==null&&(object.boundingSphere=this.boundingSphere.toJSON()),this.boundingBox!==null&&(object.boundingBox=this.boundingBox.toJSON()));function serialize(library,element){return library[element.uuid]===void 0&&(library[element.uuid]=element.toJSON(meta)),element.uuid}if(this.isScene)this.background&&(this.background.isColor?object.background=this.background.toJSON():this.background.isTexture&&(object.background=this.background.toJSON(meta).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(object.environment=this.environment.toJSON(meta).uuid);else if(this.isMesh||this.isLine||this.isPoints){object.geometry=serialize(meta.geometries,this.geometry);let parameters=this.geometry.parameters;if(parameters!==void 0&&parameters.shapes!==void 0){let shapes=parameters.shapes;if(Array.isArray(shapes))for(let i=0,l=shapes.length;i<l;i++){let shape=shapes[i];serialize(meta.shapes,shape)}else serialize(meta.shapes,shapes)}}if(this.isSkinnedMesh&&(object.bindMode=this.bindMode,object.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(serialize(meta.skeletons,this.skeleton),object.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){let uuids=[];for(let i=0,l=this.material.length;i<l;i++)uuids.push(serialize(meta.materials,this.material[i]));object.material=uuids}else object.material=serialize(meta.materials,this.material);if(this.children.length>0){object.children=[];for(let i=0;i<this.children.length;i++)object.children.push(this.children[i].toJSON(meta).object)}if(this.animations.length>0){object.animations=[];for(let i=0;i<this.animations.length;i++){let animation=this.animations[i];object.animations.push(serialize(meta.animations,animation))}}if(isRootObject){let geometries=extractFromCache(meta.geometries),materials=extractFromCache(meta.materials),textures=extractFromCache(meta.textures),images=extractFromCache(meta.images),shapes=extractFromCache(meta.shapes),skeletons=extractFromCache(meta.skeletons),animations=extractFromCache(meta.animations),nodes=extractFromCache(meta.nodes);geometries.length>0&&(output.geometries=geometries),materials.length>0&&(output.materials=materials),textures.length>0&&(output.textures=textures),images.length>0&&(output.images=images),shapes.length>0&&(output.shapes=shapes),skeletons.length>0&&(output.skeletons=skeletons),animations.length>0&&(output.animations=animations),nodes.length>0&&(output.nodes=nodes)}return output.object=object,output;function extractFromCache(cache){let values=[];for(let key in cache){let data=cache[key];delete data.metadata,values.push(data)}return values}}clone(recursive){return new this.constructor().copy(this,recursive)}copy(source,recursive=!0){if(this.name=source.name,this.up.copy(source.up),this.position.copy(source.position),this.rotation.order=source.rotation.order,this.quaternion.copy(source.quaternion),this.scale.copy(source.scale),this.pivot=source.pivot!==null?source.pivot.clone():null,this.matrix.copy(source.matrix),this.matrixWorld.copy(source.matrixWorld),this.matrixAutoUpdate=source.matrixAutoUpdate,this.matrixWorldAutoUpdate=source.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=source.matrixWorldNeedsUpdate,this.layers.mask=source.layers.mask,this.visible=source.visible,this.castShadow=source.castShadow,this.receiveShadow=source.receiveShadow,this.frustumCulled=source.frustumCulled,this.renderOrder=source.renderOrder,this.static=source.static,this.animations=source.animations.slice(),this.userData=JSON.parse(JSON.stringify(source.userData)),recursive===!0)for(let i=0;i<source.children.length;i++){let child=source.children[i];this.add(child.clone())}return this}dispose(){this.dispatchEvent({type:"dispose"})}};Object3D.DEFAULT_UP=new Vector3(0,1,0);Object3D.DEFAULT_MATRIX_AUTO_UPDATE=!0;Object3D.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;var Group=class extends Object3D{constructor(){super(),this.isGroup=!0,this.type="Group"}};var _moveEvent={type:"move"},WebXRController=class{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new Group,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new Group,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new Vector3,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new Vector3),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new Group,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new Vector3,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new Vector3,this._grip.eventsEnabled=!1),this._grip}dispatchEvent(event){return this._targetRay!==null&&this._targetRay.dispatchEvent(event),this._grip!==null&&this._grip.dispatchEvent(event),this._hand!==null&&this._hand.dispatchEvent(event),this}connect(inputSource){if(inputSource&&inputSource.hand){let hand=this._hand;if(hand)for(let inputjoint of inputSource.hand.values())this._getHandJoint(hand,inputjoint)}return this.dispatchEvent({type:"connected",data:inputSource}),this}disconnect(inputSource){return this.dispatchEvent({type:"disconnected",data:inputSource}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(inputSource,frame,referenceSpace){let inputPose=null,gripPose=null,handPose=null,targetRay=this._targetRay,grip=this._grip,hand=this._hand;if(inputSource&&frame.session.visibilityState!=="visible-blurred"){if(hand&&inputSource.hand){handPose=!0;for(let inputjoint of inputSource.hand.values()){let jointPose=frame.getJointPose(inputjoint,referenceSpace),joint=this._getHandJoint(hand,inputjoint);jointPose!==null&&(joint.matrix.fromArray(jointPose.transform.matrix),joint.matrix.decompose(joint.position,joint.rotation,joint.scale),joint.matrixWorldNeedsUpdate=!0,joint.jointRadius=jointPose.radius),joint.visible=jointPose!==null}let indexTip=hand.joints["index-finger-tip"],thumbTip=hand.joints["thumb-tip"],distance=indexTip.position.distanceTo(thumbTip.position),distanceToPinch=.02,threshold=.005;hand.inputState.pinching&&distance>distanceToPinch+threshold?(hand.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:inputSource.handedness,target:this})):!hand.inputState.pinching&&distance<=distanceToPinch-threshold&&(hand.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:inputSource.handedness,target:this}))}else grip!==null&&inputSource.gripSpace&&(gripPose=frame.getPose(inputSource.gripSpace,referenceSpace),gripPose!==null&&(grip.matrix.fromArray(gripPose.transform.matrix),grip.matrix.decompose(grip.position,grip.rotation,grip.scale),grip.matrixWorldNeedsUpdate=!0,gripPose.linearVelocity?(grip.hasLinearVelocity=!0,grip.linearVelocity.copy(gripPose.linearVelocity)):grip.hasLinearVelocity=!1,gripPose.angularVelocity?(grip.hasAngularVelocity=!0,grip.angularVelocity.copy(gripPose.angularVelocity)):grip.hasAngularVelocity=!1,grip.eventsEnabled&&grip.dispatchEvent({type:"gripUpdated",data:inputSource,target:this})));targetRay!==null&&(inputPose=frame.getPose(inputSource.targetRaySpace,referenceSpace),inputPose===null&&gripPose!==null&&(inputPose=gripPose),inputPose!==null&&(targetRay.matrix.fromArray(inputPose.transform.matrix),targetRay.matrix.decompose(targetRay.position,targetRay.rotation,targetRay.scale),targetRay.matrixWorldNeedsUpdate=!0,inputPose.linearVelocity?(targetRay.hasLinearVelocity=!0,targetRay.linearVelocity.copy(inputPose.linearVelocity)):targetRay.hasLinearVelocity=!1,inputPose.angularVelocity?(targetRay.hasAngularVelocity=!0,targetRay.angularVelocity.copy(inputPose.angularVelocity)):targetRay.hasAngularVelocity=!1,this.dispatchEvent(_moveEvent)))}return targetRay!==null&&(targetRay.visible=inputPose!==null),grip!==null&&(grip.visible=gripPose!==null),hand!==null&&(hand.visible=handPose!==null),this}_getHandJoint(hand,inputjoint){if(hand.joints[inputjoint.jointName]===void 0){let joint=new Group;joint.matrixAutoUpdate=!1,joint.visible=!1,hand.joints[inputjoint.jointName]=joint,hand.add(joint)}return hand.joints[inputjoint.jointName]}};var _colorKeywords={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},_hslA={h:0,s:0,l:0},_hslB={h:0,s:0,l:0};function hue2rgb(p,q,t){return t<0&&(t+=1),t>1&&(t-=1),t<1/6?p+(q-p)*6*t:t<1/2?q:t<2/3?p+(q-p)*6*(2/3-t):p}var Color=class{constructor(r,g,b){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(r,g,b)}set(r,g,b){if(g===void 0&&b===void 0){let value=r;value&&value.isColor?this.copy(value):typeof value=="number"?this.setHex(value):typeof value=="string"&&this.setStyle(value)}else this.setRGB(r,g,b);return this}setScalar(scalar){return this.r=scalar,this.g=scalar,this.b=scalar,this}setHex(hex,colorSpace=SRGBColorSpace){return hex=Math.floor(hex),this.r=(hex>>16&255)/255,this.g=(hex>>8&255)/255,this.b=(hex&255)/255,ColorManagement.colorSpaceToWorking(this,colorSpace),this}setRGB(r,g,b,colorSpace=ColorManagement.workingColorSpace){return this.r=r,this.g=g,this.b=b,ColorManagement.colorSpaceToWorking(this,colorSpace),this}setHSL(h,s,l,colorSpace=ColorManagement.workingColorSpace){if(h=euclideanModulo(h,1),s=clamp(s,0,1),l=clamp(l,0,1),s===0)this.r=this.g=this.b=l;else{let p=l<=.5?l*(1+s):l+s-l*s,q=2*l-p;this.r=hue2rgb(q,p,h+1/3),this.g=hue2rgb(q,p,h),this.b=hue2rgb(q,p,h-1/3)}return ColorManagement.colorSpaceToWorking(this,colorSpace),this}setStyle(style,colorSpace=SRGBColorSpace){function handleAlpha(string){string!==void 0&&parseFloat(string)<1&&warn("Color: Alpha component of "+style+" will be ignored.")}let m;if(m=/^(\w+)\(([^\)]*)\)/.exec(style)){let color,name=m[1],components=m[2];switch(name){case"rgb":case"rgba":if(color=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(components))return handleAlpha(color[4]),this.setRGB(Math.min(255,parseInt(color[1],10))/255,Math.min(255,parseInt(color[2],10))/255,Math.min(255,parseInt(color[3],10))/255,colorSpace);if(color=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(components))return handleAlpha(color[4]),this.setRGB(Math.min(100,parseInt(color[1],10))/100,Math.min(100,parseInt(color[2],10))/100,Math.min(100,parseInt(color[3],10))/100,colorSpace);break;case"hsl":case"hsla":if(color=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(components))return handleAlpha(color[4]),this.setHSL(parseFloat(color[1])/360,parseFloat(color[2])/100,parseFloat(color[3])/100,colorSpace);break;default:warn("Color: Unknown color model "+style)}}else if(m=/^\#([A-Fa-f\d]+)$/.exec(style)){let hex=m[1],size=hex.length;if(size===3)return this.setRGB(parseInt(hex.charAt(0),16)/15,parseInt(hex.charAt(1),16)/15,parseInt(hex.charAt(2),16)/15,colorSpace);if(size===6)return this.setHex(parseInt(hex,16),colorSpace);warn("Color: Invalid hex color "+style)}else if(style&&style.length>0)return this.setColorName(style,colorSpace);return this}setColorName(style,colorSpace=SRGBColorSpace){let hex=_colorKeywords[style.toLowerCase()];return hex!==void 0?this.setHex(hex,colorSpace):warn("Color: Unknown color "+style),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(color){return this.r=color.r,this.g=color.g,this.b=color.b,this}copySRGBToLinear(color){return this.r=SRGBToLinear(color.r),this.g=SRGBToLinear(color.g),this.b=SRGBToLinear(color.b),this}copyLinearToSRGB(color){return this.r=LinearToSRGB(color.r),this.g=LinearToSRGB(color.g),this.b=LinearToSRGB(color.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(colorSpace=SRGBColorSpace){return ColorManagement.workingToColorSpace(_color.copy(this),colorSpace),Math.round(clamp(_color.r*255,0,255))*65536+Math.round(clamp(_color.g*255,0,255))*256+Math.round(clamp(_color.b*255,0,255))}getHexString(colorSpace=SRGBColorSpace){return("000000"+this.getHex(colorSpace).toString(16)).slice(-6)}getHSL(target,colorSpace=ColorManagement.workingColorSpace){ColorManagement.workingToColorSpace(_color.copy(this),colorSpace);let r=_color.r,g=_color.g,b=_color.b,max=Math.max(r,g,b),min=Math.min(r,g,b),hue,saturation,lightness=(min+max)/2;if(min===max)hue=0,saturation=0;else{let delta=max-min;switch(saturation=lightness<=.5?delta/(max+min):delta/(2-max-min),max){case r:hue=(g-b)/delta+(g<b?6:0);break;case g:hue=(b-r)/delta+2;break;case b:hue=(r-g)/delta+4;break}hue/=6}return target.h=hue,target.s=saturation,target.l=lightness,target}getRGB(target,colorSpace=ColorManagement.workingColorSpace){return ColorManagement.workingToColorSpace(_color.copy(this),colorSpace),target.r=_color.r,target.g=_color.g,target.b=_color.b,target}getStyle(colorSpace=SRGBColorSpace){ColorManagement.workingToColorSpace(_color.copy(this),colorSpace);let r=_color.r,g=_color.g,b=_color.b;return colorSpace!==SRGBColorSpace?`color(${colorSpace} ${r.toFixed(3)} ${g.toFixed(3)} ${b.toFixed(3)})`:`rgb(${Math.round(r*255)},${Math.round(g*255)},${Math.round(b*255)})`}offsetHSL(h,s,l){return this.getHSL(_hslA),this.setHSL(_hslA.h+h,_hslA.s+s,_hslA.l+l)}add(color){return this.r+=color.r,this.g+=color.g,this.b+=color.b,this}addColors(color1,color2){return this.r=color1.r+color2.r,this.g=color1.g+color2.g,this.b=color1.b+color2.b,this}addScalar(s){return this.r+=s,this.g+=s,this.b+=s,this}sub(color){return this.r=Math.max(0,this.r-color.r),this.g=Math.max(0,this.g-color.g),this.b=Math.max(0,this.b-color.b),this}multiply(color){return this.r*=color.r,this.g*=color.g,this.b*=color.b,this}multiplyScalar(s){return this.r*=s,this.g*=s,this.b*=s,this}lerp(color,alpha){return this.r+=(color.r-this.r)*alpha,this.g+=(color.g-this.g)*alpha,this.b+=(color.b-this.b)*alpha,this}lerpColors(color1,color2,alpha){return this.r=color1.r+(color2.r-color1.r)*alpha,this.g=color1.g+(color2.g-color1.g)*alpha,this.b=color1.b+(color2.b-color1.b)*alpha,this}lerpHSL(color,alpha){this.getHSL(_hslA),color.getHSL(_hslB);let h=lerp(_hslA.h,_hslB.h,alpha),s=lerp(_hslA.s,_hslB.s,alpha),l=lerp(_hslA.l,_hslB.l,alpha);return this.setHSL(h,s,l),this}setFromVector3(v){return this.r=v.x,this.g=v.y,this.b=v.z,this}applyMatrix3(m){let r=this.r,g=this.g,b=this.b,e=m.elements;return this.r=e[0]*r+e[3]*g+e[6]*b,this.g=e[1]*r+e[4]*g+e[7]*b,this.b=e[2]*r+e[5]*g+e[8]*b,this}equals(c){return c.r===this.r&&c.g===this.g&&c.b===this.b}fromArray(array,offset=0){return this.r=array[offset],this.g=array[offset+1],this.b=array[offset+2],this}toArray(array=[],offset=0){return array[offset]=this.r,array[offset+1]=this.g,array[offset+2]=this.b,array}fromBufferAttribute(attribute,index){return this.r=attribute.getX(index),this.g=attribute.getY(index),this.b=attribute.getZ(index),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}},_color=new Color;Color.NAMES=_colorKeywords;var Scene=class extends Object3D{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new Euler,this.environmentIntensity=1,this.environmentRotation=new Euler,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(source,recursive){return super.copy(source,recursive),source.background!==null&&(this.background=source.background.clone()),source.environment!==null&&(this.environment=source.environment.clone()),source.fog!==null&&(this.fog=source.fog.clone()),this.backgroundBlurriness=source.backgroundBlurriness,this.backgroundIntensity=source.backgroundIntensity,this.backgroundRotation.copy(source.backgroundRotation),this.environmentIntensity=source.environmentIntensity,this.environmentRotation.copy(source.environmentRotation),source.overrideMaterial!==null&&(this.overrideMaterial=source.overrideMaterial.clone()),this.matrixAutoUpdate=source.matrixAutoUpdate,this}toJSON(meta){let data=super.toJSON(meta);return this.fog!==null&&(data.object.fog=this.fog.toJSON()),data.object.backgroundBlurriness=this.backgroundBlurriness,data.object.backgroundIntensity=this.backgroundIntensity,data.object.backgroundRotation=this.backgroundRotation.toArray(),data.object.environmentIntensity=this.environmentIntensity,data.object.environmentRotation=this.environmentRotation.toArray(),data}};var _v0=new Vector3,_v13=new Vector3,_v2=new Vector3,_v3=new Vector3,_vab=new Vector3,_vac=new Vector3,_vbc=new Vector3,_vap=new Vector3,_vbp=new Vector3,_vcp=new Vector3,_v40=new Vector4,_v41=new Vector4,_v42=new Vector4,Triangle=class _Triangle{constructor(a=new Vector3,b=new Vector3,c=new Vector3){this.a=a,this.b=b,this.c=c}static getNormal(a,b,c,target){target.subVectors(c,b),_v0.subVectors(a,b),target.cross(_v0);let targetLengthSq=target.lengthSq();return targetLengthSq>0?target.multiplyScalar(1/Math.sqrt(targetLengthSq)):target.set(0,0,0)}static getBarycoord(point,a,b,c,target){_v0.subVectors(c,a),_v13.subVectors(b,a),_v2.subVectors(point,a);let dot00=_v0.dot(_v0),dot01=_v0.dot(_v13),dot02=_v0.dot(_v2),dot11=_v13.dot(_v13),dot12=_v13.dot(_v2),denom=dot00*dot11-dot01*dot01;if(denom===0)return target.set(0,0,0),null;let invDenom=1/denom,u=(dot11*dot02-dot01*dot12)*invDenom,v=(dot00*dot12-dot01*dot02)*invDenom;return target.set(1-u-v,v,u)}static containsPoint(point,a,b,c){return this.getBarycoord(point,a,b,c,_v3)===null?!1:_v3.x>=0&&_v3.y>=0&&_v3.x+_v3.y<=1}static getInterpolation(point,p1,p2,p3,v1,v2,v3,target){return this.getBarycoord(point,p1,p2,p3,_v3)===null?(target.x=0,target.y=0,"z"in target&&(target.z=0),"w"in target&&(target.w=0),null):(target.setScalar(0),target.addScaledVector(v1,_v3.x),target.addScaledVector(v2,_v3.y),target.addScaledVector(v3,_v3.z),target)}static getInterpolatedAttribute(attr,i1,i2,i3,barycoord,target){return _v40.setScalar(0),_v41.setScalar(0),_v42.setScalar(0),_v40.fromBufferAttribute(attr,i1),_v41.fromBufferAttribute(attr,i2),_v42.fromBufferAttribute(attr,i3),target.setScalar(0),target.addScaledVector(_v40,barycoord.x),target.addScaledVector(_v41,barycoord.y),target.addScaledVector(_v42,barycoord.z),target}static isFrontFacing(a,b,c,direction){return _v0.subVectors(c,b),_v13.subVectors(a,b),_v0.cross(_v13).dot(direction)<0}set(a,b,c){return this.a.copy(a),this.b.copy(b),this.c.copy(c),this}setFromPointsAndIndices(points,i0,i1,i2){return this.a.copy(points[i0]),this.b.copy(points[i1]),this.c.copy(points[i2]),this}setFromAttributeAndIndices(attribute,i0,i1,i2){return this.a.fromBufferAttribute(attribute,i0),this.b.fromBufferAttribute(attribute,i1),this.c.fromBufferAttribute(attribute,i2),this}clone(){return new this.constructor().copy(this)}copy(triangle){return this.a.copy(triangle.a),this.b.copy(triangle.b),this.c.copy(triangle.c),this}getArea(){return _v0.subVectors(this.c,this.b),_v13.subVectors(this.a,this.b),_v0.cross(_v13).length()*.5}getMidpoint(target){return target.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(target){return _Triangle.getNormal(this.a,this.b,this.c,target)}getPlane(target){return target.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(point,target){return _Triangle.getBarycoord(point,this.a,this.b,this.c,target)}getInterpolation(point,v1,v2,v3,target){return _Triangle.getInterpolation(point,this.a,this.b,this.c,v1,v2,v3,target)}containsPoint(point){return _Triangle.containsPoint(point,this.a,this.b,this.c)}isFrontFacing(direction){return _Triangle.isFrontFacing(this.a,this.b,this.c,direction)}intersectsBox(box){return box.intersectsTriangle(this)}closestPointToPoint(p,target){let a=this.a,b=this.b,c=this.c,v,w;_vab.subVectors(b,a),_vac.subVectors(c,a),_vap.subVectors(p,a);let d1=_vab.dot(_vap),d2=_vac.dot(_vap);if(d1<=0&&d2<=0)return target.copy(a);_vbp.subVectors(p,b);let d3=_vab.dot(_vbp),d4=_vac.dot(_vbp);if(d3>=0&&d4<=d3)return target.copy(b);let vc=d1*d4-d3*d2;if(vc<=0&&d1>=0&&d3<=0)return v=d1/(d1-d3),target.copy(a).addScaledVector(_vab,v);_vcp.subVectors(p,c);let d5=_vab.dot(_vcp),d6=_vac.dot(_vcp);if(d6>=0&&d5<=d6)return target.copy(c);let vb=d5*d2-d1*d6;if(vb<=0&&d2>=0&&d6<=0)return w=d2/(d2-d6),target.copy(a).addScaledVector(_vac,w);let va=d3*d6-d5*d4;if(va<=0&&d4-d3>=0&&d5-d6>=0)return _vbc.subVectors(c,b),w=(d4-d3)/(d4-d3+(d5-d6)),target.copy(b).addScaledVector(_vbc,w);let denom=1/(va+vb+vc);return v=vb*denom,w=vc*denom,target.copy(a).addScaledVector(_vab,v).addScaledVector(_vac,w)}equals(triangle){return triangle.a.equals(this.a)&&triangle.b.equals(this.b)&&triangle.c.equals(this.c)}};var Box3=class{constructor(min=new Vector3(1/0,1/0,1/0),max=new Vector3(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=min,this.max=max}set(min,max){return this.min.copy(min),this.max.copy(max),this}setFromArray(array){this.makeEmpty();for(let i=0,il=array.length;i<il;i+=3)this.expandByPoint(_vector2.fromArray(array,i));return this}setFromBufferAttribute(attribute){this.makeEmpty();for(let i=0,il=attribute.count;i<il;i++)this.expandByPoint(_vector2.fromBufferAttribute(attribute,i));return this}setFromPoints(points){this.makeEmpty();for(let i=0,il=points.length;i<il;i++)this.expandByPoint(points[i]);return this}setFromCenterAndSize(center,size){let halfSize=_vector2.copy(size).multiplyScalar(.5);return this.min.copy(center).sub(halfSize),this.max.copy(center).add(halfSize),this}setFromObject(object,precise=!1){return this.makeEmpty(),this.expandByObject(object,precise)}clone(){return new this.constructor().copy(this)}copy(box){return this.min.copy(box.min),this.max.copy(box.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(target){return this.isEmpty()?target.set(0,0,0):target.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(target){return this.isEmpty()?target.set(0,0,0):target.subVectors(this.max,this.min)}expandByPoint(point){return this.min.min(point),this.max.max(point),this}expandByVector(vector){return this.min.sub(vector),this.max.add(vector),this}expandByScalar(scalar){return this.min.addScalar(-scalar),this.max.addScalar(scalar),this}expandByObject(object,precise=!1){object.updateWorldMatrix(!1,!1);let geometry=object.geometry;if(geometry!==void 0){let positionAttribute=geometry.getAttribute("position");if(precise===!0&&positionAttribute!==void 0&&object.isInstancedMesh!==!0)for(let i=0,l=positionAttribute.count;i<l;i++)object.isMesh===!0?object.getVertexPosition(i,_vector2):_vector2.fromBufferAttribute(positionAttribute,i),_vector2.applyMatrix4(object.matrixWorld),this.expandByPoint(_vector2);else object.boundingBox!==void 0?(object.boundingBox===null&&object.computeBoundingBox(),_box.copy(object.boundingBox)):(geometry.boundingBox===null&&geometry.computeBoundingBox(),_box.copy(geometry.boundingBox)),_box.applyMatrix4(object.matrixWorld),this.min.min(_box.min),this.max.max(_box.max)}let children=object.children;for(let i=0,l=children.length;i<l;i++)this.expandByObject(children[i],precise);return this}containsPoint(point){return point.x>=this.min.x&&point.x<=this.max.x&&point.y>=this.min.y&&point.y<=this.max.y&&point.z>=this.min.z&&point.z<=this.max.z}containsBox(box){return this.min.x<=box.min.x&&box.max.x<=this.max.x&&this.min.y<=box.min.y&&box.max.y<=this.max.y&&this.min.z<=box.min.z&&box.max.z<=this.max.z}getParameter(point,target){return target.set((point.x-this.min.x)/(this.max.x-this.min.x),(point.y-this.min.y)/(this.max.y-this.min.y),(point.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(box){return box.max.x>=this.min.x&&box.min.x<=this.max.x&&box.max.y>=this.min.y&&box.min.y<=this.max.y&&box.max.z>=this.min.z&&box.min.z<=this.max.z}intersectsSphere(sphere){return this.clampPoint(sphere.center,_vector2),_vector2.distanceToSquared(sphere.center)<=sphere.radius*sphere.radius}intersectsPlane(plane){let min,max;return plane.normal.x>0?(min=plane.normal.x*this.min.x,max=plane.normal.x*this.max.x):(min=plane.normal.x*this.max.x,max=plane.normal.x*this.min.x),plane.normal.y>0?(min+=plane.normal.y*this.min.y,max+=plane.normal.y*this.max.y):(min+=plane.normal.y*this.max.y,max+=plane.normal.y*this.min.y),plane.normal.z>0?(min+=plane.normal.z*this.min.z,max+=plane.normal.z*this.max.z):(min+=plane.normal.z*this.max.z,max+=plane.normal.z*this.min.z),min<=-plane.constant&&max>=-plane.constant}intersectsTriangle(triangle){if(this.isEmpty())return!1;this.getCenter(_center),_extents.subVectors(this.max,_center),_v02.subVectors(triangle.a,_center),_v14.subVectors(triangle.b,_center),_v22.subVectors(triangle.c,_center),_f0.subVectors(_v14,_v02),_f1.subVectors(_v22,_v14),_f2.subVectors(_v02,_v22);let axes=[0,-_f0.z,_f0.y,0,-_f1.z,_f1.y,0,-_f2.z,_f2.y,_f0.z,0,-_f0.x,_f1.z,0,-_f1.x,_f2.z,0,-_f2.x,-_f0.y,_f0.x,0,-_f1.y,_f1.x,0,-_f2.y,_f2.x,0];return!satForAxes(axes,_v02,_v14,_v22,_extents)||(axes=[1,0,0,0,1,0,0,0,1],!satForAxes(axes,_v02,_v14,_v22,_extents))?!1:(_triangleNormal.crossVectors(_f0,_f1),axes=[_triangleNormal.x,_triangleNormal.y,_triangleNormal.z],satForAxes(axes,_v02,_v14,_v22,_extents))}clampPoint(point,target){return target.copy(point).clamp(this.min,this.max)}distanceToPoint(point){return this.clampPoint(point,_vector2).distanceTo(point)}getBoundingSphere(target){return this.isEmpty()?target.makeEmpty():(this.getCenter(target.center),target.radius=this.getSize(_vector2).length()*.5),target}intersect(box){return this.min.max(box.min),this.max.min(box.max),this.isEmpty()&&this.makeEmpty(),this}union(box){return this.min.min(box.min),this.max.max(box.max),this}applyMatrix4(matrix){return this.isEmpty()?this:(_points[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(matrix),_points[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(matrix),_points[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(matrix),_points[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(matrix),_points[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(matrix),_points[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(matrix),_points[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(matrix),_points[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(matrix),this.setFromPoints(_points),this)}translate(offset){return this.min.add(offset),this.max.add(offset),this}equals(box){return box.min.equals(this.min)&&box.max.equals(this.max)}toJSON(){return{min:this.min.toArray(),max:this.max.toArray()}}fromJSON(json){return this.min.fromArray(json.min),this.max.fromArray(json.max),this}},_points=[new Vector3,new Vector3,new Vector3,new Vector3,new Vector3,new Vector3,new Vector3,new Vector3],_vector2=new Vector3,_box=new Box3,_v02=new Vector3,_v14=new Vector3,_v22=new Vector3,_f0=new Vector3,_f1=new Vector3,_f2=new Vector3,_center=new Vector3,_extents=new Vector3,_triangleNormal=new Vector3,_testAxis=new Vector3;function satForAxes(axes,v0,v1,v2,extents){for(let i=0,j=axes.length-3;i<=j;i+=3){_testAxis.fromArray(axes,i);let r=extents.x*Math.abs(_testAxis.x)+extents.y*Math.abs(_testAxis.y)+extents.z*Math.abs(_testAxis.z),p0=v0.dot(_testAxis),p1=v1.dot(_testAxis),p2=v2.dot(_testAxis);if(Math.max(-Math.max(p0,p1,p2),Math.min(p0,p1,p2))>r)return!1}return!0}var _vector3=new Vector3,_vector22=new Vector2,_id=0,BufferAttribute=class extends EventDispatcher{constructor(array,itemSize,normalized=!1){if(super(),Array.isArray(array))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,Object.defineProperty(this,"id",{value:_id++}),this.name="",this.array=array,this.itemSize=itemSize,this.count=array!==void 0?array.length/itemSize:0,this.normalized=normalized,this.usage=StaticDrawUsage,this.updateRanges=[],this.gpuType=FloatType,this.version=0}onUploadCallback(){}set needsUpdate(value){value===!0&&this.version++}setUsage(value){return this.usage=value,this}addUpdateRange(start,count){this.updateRanges.push({start,count})}clearUpdateRanges(){this.updateRanges.length=0}copy(source){return this.name=source.name,this.array=new source.array.constructor(source.array),this.itemSize=source.itemSize,this.count=source.count,this.normalized=source.normalized,this.usage=source.usage,this.gpuType=source.gpuType,this}copyAt(index1,attribute,index2){index1*=this.itemSize,index2*=attribute.itemSize;for(let i=0,l=this.itemSize;i<l;i++)this.array[index1+i]=attribute.array[index2+i];return this}copyArray(array){return this.array.set(array),this}applyMatrix3(m){if(this.itemSize===2)for(let i=0,l=this.count;i<l;i++)_vector22.fromBufferAttribute(this,i),_vector22.applyMatrix3(m),this.setXY(i,_vector22.x,_vector22.y);else if(this.itemSize===3)for(let i=0,l=this.count;i<l;i++)_vector3.fromBufferAttribute(this,i),_vector3.applyMatrix3(m),this.setXYZ(i,_vector3.x,_vector3.y,_vector3.z);return this}applyMatrix4(m){for(let i=0,l=this.count;i<l;i++)_vector3.fromBufferAttribute(this,i),_vector3.applyMatrix4(m),this.setXYZ(i,_vector3.x,_vector3.y,_vector3.z);return this}applyNormalMatrix(m){for(let i=0,l=this.count;i<l;i++)_vector3.fromBufferAttribute(this,i),_vector3.applyNormalMatrix(m),this.setXYZ(i,_vector3.x,_vector3.y,_vector3.z);return this}transformDirection(m){for(let i=0,l=this.count;i<l;i++)_vector3.fromBufferAttribute(this,i),_vector3.transformDirection(m),this.setXYZ(i,_vector3.x,_vector3.y,_vector3.z);return this}set(value,offset=0){return this.array.set(value,offset),this}getComponent(index,component){let value=this.array[index*this.itemSize+component];return this.normalized&&(value=denormalize(value,this.array)),value}setComponent(index,component,value){return this.normalized&&(value=normalize(value,this.array)),this.array[index*this.itemSize+component]=value,this}getX(index){let x=this.array[index*this.itemSize];return this.normalized&&(x=denormalize(x,this.array)),x}setX(index,x){return this.normalized&&(x=normalize(x,this.array)),this.array[index*this.itemSize]=x,this}getY(index){let y=this.array[index*this.itemSize+1];return this.normalized&&(y=denormalize(y,this.array)),y}setY(index,y){return this.normalized&&(y=normalize(y,this.array)),this.array[index*this.itemSize+1]=y,this}getZ(index){let z=this.array[index*this.itemSize+2];return this.normalized&&(z=denormalize(z,this.array)),z}setZ(index,z){return this.normalized&&(z=normalize(z,this.array)),this.array[index*this.itemSize+2]=z,this}getW(index){let w=this.array[index*this.itemSize+3];return this.normalized&&(w=denormalize(w,this.array)),w}setW(index,w){return this.normalized&&(w=normalize(w,this.array)),this.array[index*this.itemSize+3]=w,this}setXY(index,x,y){return index*=this.itemSize,this.normalized&&(x=normalize(x,this.array),y=normalize(y,this.array)),this.array[index+0]=x,this.array[index+1]=y,this}setXYZ(index,x,y,z){return index*=this.itemSize,this.normalized&&(x=normalize(x,this.array),y=normalize(y,this.array),z=normalize(z,this.array)),this.array[index+0]=x,this.array[index+1]=y,this.array[index+2]=z,this}setXYZW(index,x,y,z,w){return index*=this.itemSize,this.normalized&&(x=normalize(x,this.array),y=normalize(y,this.array),z=normalize(z,this.array),w=normalize(w,this.array)),this.array[index+0]=x,this.array[index+1]=y,this.array[index+2]=z,this.array[index+3]=w,this}onUpload(callback){return this.onUploadCallback=callback,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){let data={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return data.name=this.name,data.usage=this.usage,data.gpuType=this.gpuType,data}dispose(){this.dispatchEvent({type:"dispose"})}};var Uint16BufferAttribute=class extends BufferAttribute{constructor(array,itemSize,normalized){super(new Uint16Array(array),itemSize,normalized)}};var Uint32BufferAttribute=class extends BufferAttribute{constructor(array,itemSize,normalized){super(new Uint32Array(array),itemSize,normalized)}};var Float32BufferAttribute=class extends BufferAttribute{constructor(array,itemSize,normalized){super(new Float32Array(array),itemSize,normalized)}};var _box2=new Box3,_v15=new Vector3,_v23=new Vector3,Sphere=class{constructor(center=new Vector3,radius=-1){this.isSphere=!0,this.center=center,this.radius=radius}set(center,radius){return this.center.copy(center),this.radius=radius,this}setFromPoints(points,optionalCenter){let center=this.center;optionalCenter!==void 0?center.copy(optionalCenter):_box2.setFromPoints(points).getCenter(center);let maxRadiusSq=0;for(let i=0,il=points.length;i<il;i++)maxRadiusSq=Math.max(maxRadiusSq,center.distanceToSquared(points[i]));return this.radius=Math.sqrt(maxRadiusSq),this}copy(sphere){return this.center.copy(sphere.center),this.radius=sphere.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(point){return point.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(point){return point.distanceTo(this.center)-this.radius}intersectsSphere(sphere){let radiusSum=this.radius+sphere.radius;return sphere.center.distanceToSquared(this.center)<=radiusSum*radiusSum}intersectsBox(box){return box.intersectsSphere(this)}intersectsPlane(plane){return Math.abs(plane.distanceToPoint(this.center))<=this.radius}clampPoint(point,target){let deltaLengthSq=this.center.distanceToSquared(point);return target.copy(point),deltaLengthSq>this.radius*this.radius&&(target.sub(this.center).normalize(),target.multiplyScalar(this.radius).add(this.center)),target}getBoundingBox(target){return this.isEmpty()?(target.makeEmpty(),target):(target.set(this.center,this.center),target.expandByScalar(this.radius),target)}applyMatrix4(matrix){return this.center.applyMatrix4(matrix),this.radius=this.radius*matrix.getMaxScaleOnAxis(),this}translate(offset){return this.center.add(offset),this}expandByPoint(point){if(this.isEmpty())return this.center.copy(point),this.radius=0,this;_v15.subVectors(point,this.center);let lengthSq=_v15.lengthSq();if(lengthSq>this.radius*this.radius){let length=Math.sqrt(lengthSq),delta=(length-this.radius)*.5;this.center.addScaledVector(_v15,delta/length),this.radius+=delta}return this}union(sphere){return sphere.isEmpty()?this:this.isEmpty()?(this.copy(sphere),this):(this.center.equals(sphere.center)===!0?this.radius=Math.max(this.radius,sphere.radius):(_v23.subVectors(sphere.center,this.center).setLength(sphere.radius),this.expandByPoint(_v15.copy(sphere.center).add(_v23)),this.expandByPoint(_v15.copy(sphere.center).sub(_v23))),this)}equals(sphere){return sphere.center.equals(this.center)&&sphere.radius===this.radius}clone(){return new this.constructor().copy(this)}toJSON(){return{radius:this.radius,center:this.center.toArray()}}fromJSON(json){return this.radius=json.radius,this.center.fromArray(json.center),this}};var _id2=0,_m13=new Matrix4,_obj=new Object3D,_offset=new Vector3,_box3=new Box3,_boxMorphTargets=new Box3,_vector4=new Vector3,BufferGeometry=class _BufferGeometry extends EventDispatcher{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:_id2++}),this.uuid=generateUUID(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.indirectOffset=0,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={},this._transformed=!1}getIndex(){return this.index}setIndex(index){return Array.isArray(index)?this.index=new(arrayNeedsUint32(index)?Uint32BufferAttribute:Uint16BufferAttribute)(index,1):this.index=index,this}setIndirect(indirect,indirectOffset=0){return this.indirect=indirect,this.indirectOffset=indirectOffset,this}getIndirect(){return this.indirect}getAttribute(name){return this.attributes[name]}setAttribute(name,attribute){return this.attributes[name]=attribute,this}deleteAttribute(name){return delete this.attributes[name],this}hasAttribute(name){return this.attributes[name]!==void 0}addGroup(start,count,materialIndex=0){this.groups.push({start,count,materialIndex})}clearGroups(){this.groups=[]}setDrawRange(start,count){this.drawRange.start=start,this.drawRange.count=count}applyMatrix4(matrix){let position=this.attributes.position;position!==void 0&&(position.applyMatrix4(matrix),position.needsUpdate=!0);let normal=this.attributes.normal;if(normal!==void 0){let normalMatrix=new Matrix3().getNormalMatrix(matrix);normal.applyNormalMatrix(normalMatrix),normal.needsUpdate=!0}let tangent=this.attributes.tangent;return tangent!==void 0&&(tangent.transformDirection(matrix),tangent.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this._transformed=!0,this}applyQuaternion(q){return _m13.makeRotationFromQuaternion(q),this.applyMatrix4(_m13),this}rotateX(angle){return _m13.makeRotationX(angle),this.applyMatrix4(_m13),this}rotateY(angle){return _m13.makeRotationY(angle),this.applyMatrix4(_m13),this}rotateZ(angle){return _m13.makeRotationZ(angle),this.applyMatrix4(_m13),this}translate(x,y,z){return _m13.makeTranslation(x,y,z),this.applyMatrix4(_m13),this}scale(x,y,z){return _m13.makeScale(x,y,z),this.applyMatrix4(_m13),this}lookAt(vector){return _obj.lookAt(vector),_obj.updateMatrix(),this.applyMatrix4(_obj.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(_offset).negate(),this.translate(_offset.x,_offset.y,_offset.z),this}setFromPoints(points){let positionAttribute=this.getAttribute("position");if(positionAttribute===void 0){let position=[];for(let i=0,l=points.length;i<l;i++){let point=points[i];position.push(point.x,point.y,point.z||0)}this.setAttribute("position",new Float32BufferAttribute(position,3))}else{let l=Math.min(points.length,positionAttribute.count);for(let i=0;i<l;i++){let point=points[i];positionAttribute.setXYZ(i,point.x,point.y,point.z||0)}points.length>positionAttribute.count&&warn("BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),positionAttribute.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new Box3);let position=this.attributes.position,morphAttributesPosition=this.morphAttributes.position;if(position&&position.isGLBufferAttribute){error("BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new Vector3(-1/0,-1/0,-1/0),new Vector3(1/0,1/0,1/0));return}if(position!==void 0){if(this.boundingBox.setFromBufferAttribute(position),morphAttributesPosition)for(let i=0,il=morphAttributesPosition.length;i<il;i++){let morphAttribute=morphAttributesPosition[i];_box3.setFromBufferAttribute(morphAttribute),this.morphTargetsRelative?(_vector4.addVectors(this.boundingBox.min,_box3.min),this.boundingBox.expandByPoint(_vector4),_vector4.addVectors(this.boundingBox.max,_box3.max),this.boundingBox.expandByPoint(_vector4)):(this.boundingBox.expandByPoint(_box3.min),this.boundingBox.expandByPoint(_box3.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&error('BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new Sphere);let position=this.attributes.position,morphAttributesPosition=this.morphAttributes.position;if(position&&position.isGLBufferAttribute){error("BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new Vector3,1/0);return}if(position){let center=this.boundingSphere.center;if(_box3.setFromBufferAttribute(position),morphAttributesPosition)for(let i=0,il=morphAttributesPosition.length;i<il;i++){let morphAttribute=morphAttributesPosition[i];_boxMorphTargets.setFromBufferAttribute(morphAttribute),this.morphTargetsRelative?(_vector4.addVectors(_box3.min,_boxMorphTargets.min),_box3.expandByPoint(_vector4),_vector4.addVectors(_box3.max,_boxMorphTargets.max),_box3.expandByPoint(_vector4)):(_box3.expandByPoint(_boxMorphTargets.min),_box3.expandByPoint(_boxMorphTargets.max))}_box3.getCenter(center);let maxRadiusSq=0;for(let i=0,il=position.count;i<il;i++)_vector4.fromBufferAttribute(position,i),maxRadiusSq=Math.max(maxRadiusSq,center.distanceToSquared(_vector4));if(morphAttributesPosition)for(let i=0,il=morphAttributesPosition.length;i<il;i++){let morphAttribute=morphAttributesPosition[i],morphTargetsRelative=this.morphTargetsRelative;for(let j=0,jl=morphAttribute.count;j<jl;j++)_vector4.fromBufferAttribute(morphAttribute,j),morphTargetsRelative&&(_offset.fromBufferAttribute(position,j),_vector4.add(_offset)),maxRadiusSq=Math.max(maxRadiusSq,center.distanceToSquared(_vector4))}this.boundingSphere.radius=Math.sqrt(maxRadiusSq),isNaN(this.boundingSphere.radius)&&error('BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){let index=this.index,attributes=this.attributes;if(index===null||attributes.position===void 0||attributes.normal===void 0||attributes.uv===void 0){error("BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}let positionAttribute=attributes.position,normalAttribute=attributes.normal,uvAttribute=attributes.uv,tangentAttribute=this.getAttribute("tangent");(tangentAttribute===void 0||tangentAttribute.count!==positionAttribute.count)&&(tangentAttribute=new BufferAttribute(new Float32Array(4*positionAttribute.count),4),this.setAttribute("tangent",tangentAttribute));let tan1=[],tan2=[];for(let i=0;i<positionAttribute.count;i++)tan1[i]=new Vector3,tan2[i]=new Vector3;let vA=new Vector3,vB=new Vector3,vC=new Vector3,uvA=new Vector2,uvB=new Vector2,uvC=new Vector2,sdir=new Vector3,tdir=new Vector3;function handleTriangle(a,b,c){vA.fromBufferAttribute(positionAttribute,a),vB.fromBufferAttribute(positionAttribute,b),vC.fromBufferAttribute(positionAttribute,c),uvA.fromBufferAttribute(uvAttribute,a),uvB.fromBufferAttribute(uvAttribute,b),uvC.fromBufferAttribute(uvAttribute,c),vB.sub(vA),vC.sub(vA),uvB.sub(uvA),uvC.sub(uvA);let r=1/(uvB.x*uvC.y-uvC.x*uvB.y);isFinite(r)&&(sdir.copy(vB).multiplyScalar(uvC.y).addScaledVector(vC,-uvB.y).multiplyScalar(r),tdir.copy(vC).multiplyScalar(uvB.x).addScaledVector(vB,-uvC.x).multiplyScalar(r),tan1[a].add(sdir),tan1[b].add(sdir),tan1[c].add(sdir),tan2[a].add(tdir),tan2[b].add(tdir),tan2[c].add(tdir))}let groups=this.groups;groups.length===0&&(groups=[{start:0,count:index.count}]);for(let i=0,il=groups.length;i<il;++i){let group=groups[i],start=group.start,count=group.count;for(let j=start,jl=start+count;j<jl;j+=3)handleTriangle(index.getX(j+0),index.getX(j+1),index.getX(j+2))}let tmp3=new Vector3,tmp22=new Vector3,n=new Vector3,n2=new Vector3;function handleVertex(v){n.fromBufferAttribute(normalAttribute,v),n2.copy(n);let t=tan1[v];tmp3.copy(t),tmp3.sub(n.multiplyScalar(n.dot(t))).normalize(),tmp22.crossVectors(n2,t);let w=tmp22.dot(tan2[v])<0?-1:1;tangentAttribute.setXYZW(v,tmp3.x,tmp3.y,tmp3.z,w)}for(let i=0,il=groups.length;i<il;++i){let group=groups[i],start=group.start,count=group.count;for(let j=start,jl=start+count;j<jl;j+=3)handleVertex(index.getX(j+0)),handleVertex(index.getX(j+1)),handleVertex(index.getX(j+2))}this._transformed=!0}computeVertexNormals(){let index=this.index,positionAttribute=this.getAttribute("position");if(positionAttribute!==void 0){let normalAttribute=this.getAttribute("normal");if(normalAttribute===void 0||normalAttribute.count!==positionAttribute.count)normalAttribute=new BufferAttribute(new Float32Array(positionAttribute.count*3),3),this.setAttribute("normal",normalAttribute);else for(let i=0,il=normalAttribute.count;i<il;i++)normalAttribute.setXYZ(i,0,0,0);let pA=new Vector3,pB=new Vector3,pC=new Vector3,nA=new Vector3,nB=new Vector3,nC=new Vector3,cb=new Vector3,ab=new Vector3;if(index)for(let i=0,il=index.count;i<il;i+=3){let vA=index.getX(i+0),vB=index.getX(i+1),vC=index.getX(i+2);pA.fromBufferAttribute(positionAttribute,vA),pB.fromBufferAttribute(positionAttribute,vB),pC.fromBufferAttribute(positionAttribute,vC),cb.subVectors(pC,pB),ab.subVectors(pA,pB),cb.cross(ab),nA.fromBufferAttribute(normalAttribute,vA),nB.fromBufferAttribute(normalAttribute,vB),nC.fromBufferAttribute(normalAttribute,vC),nA.add(cb),nB.add(cb),nC.add(cb),normalAttribute.setXYZ(vA,nA.x,nA.y,nA.z),normalAttribute.setXYZ(vB,nB.x,nB.y,nB.z),normalAttribute.setXYZ(vC,nC.x,nC.y,nC.z)}else for(let i=0,il=positionAttribute.count;i<il;i+=3)pA.fromBufferAttribute(positionAttribute,i+0),pB.fromBufferAttribute(positionAttribute,i+1),pC.fromBufferAttribute(positionAttribute,i+2),cb.subVectors(pC,pB),ab.subVectors(pA,pB),cb.cross(ab),normalAttribute.setXYZ(i+0,cb.x,cb.y,cb.z),normalAttribute.setXYZ(i+1,cb.x,cb.y,cb.z),normalAttribute.setXYZ(i+2,cb.x,cb.y,cb.z);this.normalizeNormals(),normalAttribute.needsUpdate=!0}}normalizeNormals(){let normals=this.attributes.normal;for(let i=0,il=normals.count;i<il;i++)_vector4.fromBufferAttribute(normals,i),_vector4.normalize(),normals.setXYZ(i,_vector4.x,_vector4.y,_vector4.z)}toNonIndexed(){function convertBufferAttribute(attribute,indices2){let array=attribute.array,itemSize=attribute.itemSize,normalized=attribute.normalized,array2=new array.constructor(indices2.length*itemSize),index=0,index2=0;for(let i=0,l=indices2.length;i<l;i++){attribute.isInterleavedBufferAttribute?index=indices2[i]*attribute.data.stride+attribute.offset:index=indices2[i]*itemSize;for(let j=0;j<itemSize;j++)array2[index2++]=array[index++]}return new BufferAttribute(array2,itemSize,normalized)}if(this.index===null)return warn("BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;let geometry2=new _BufferGeometry,indices=this.index.array,attributes=this.attributes;for(let name in attributes){let attribute=attributes[name],newAttribute=convertBufferAttribute(attribute,indices);geometry2.setAttribute(name,newAttribute)}let morphAttributes=this.morphAttributes;for(let name in morphAttributes){let morphArray=[],morphAttribute=morphAttributes[name];for(let i=0,il=morphAttribute.length;i<il;i++){let attribute=morphAttribute[i],newAttribute=convertBufferAttribute(attribute,indices);morphArray.push(newAttribute)}geometry2.morphAttributes[name]=morphArray}geometry2.morphTargetsRelative=this.morphTargetsRelative;let groups=this.groups;for(let i=0,l=groups.length;i<l;i++){let group=groups[i];geometry2.addGroup(group.start,group.count,group.materialIndex)}return geometry2}toJSON(){let data={metadata:{version:4.7,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(data.uuid=this.uuid,data.type=this.parameters!==void 0&&this._transformed===!0?"BufferGeometry":this.type,data.name=this.name,Object.keys(this.userData).length>0&&(data.userData=this.userData),this.parameters!==void 0&&this._transformed!==!0){let parameters=this.parameters;for(let key in parameters)parameters[key]!==void 0&&(data[key]=parameters[key]);return data}data.data={attributes:{}};let index=this.index;index!==null&&(data.data.index={type:index.array.constructor.name,array:Array.prototype.slice.call(index.array)});let attributes=this.attributes;for(let key in attributes){let attribute=attributes[key];data.data.attributes[key]=attribute.toJSON(data.data)}let morphAttributes={},hasMorphAttributes=!1;for(let key in this.morphAttributes){let attributeArray=this.morphAttributes[key],array=[];for(let i=0,il=attributeArray.length;i<il;i++){let attribute=attributeArray[i];array.push(attribute.toJSON(data.data))}array.length>0&&(morphAttributes[key]=array,hasMorphAttributes=!0)}hasMorphAttributes&&(data.data.morphAttributes=morphAttributes,data.data.morphTargetsRelative=this.morphTargetsRelative);let groups=this.groups;groups.length>0&&(data.data.groups=JSON.parse(JSON.stringify(groups)));let boundingSphere=this.boundingSphere;return boundingSphere!==null&&(data.data.boundingSphere=boundingSphere.toJSON()),data}clone(){return new this.constructor().copy(this)}copy(source){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;let data={};this.name=source.name;let index=source.index;index!==null&&this.setIndex(index.clone());let attributes=source.attributes;for(let name in attributes){let attribute=attributes[name];this.setAttribute(name,attribute.clone(data))}let morphAttributes=source.morphAttributes;for(let name in morphAttributes){let array=[],morphAttribute=morphAttributes[name];for(let i=0,l=morphAttribute.length;i<l;i++)array.push(morphAttribute[i].clone(data));this.morphAttributes[name]=array}this.morphTargetsRelative=source.morphTargetsRelative;let groups=source.groups;for(let i=0,l=groups.length;i<l;i++){let group=groups[i];this.addGroup(group.start,group.count,group.materialIndex)}let boundingBox=source.boundingBox;boundingBox!==null&&(this.boundingBox=boundingBox.clone());let boundingSphere=source.boundingSphere;return boundingSphere!==null&&(this.boundingSphere=boundingSphere.clone()),this.drawRange.start=source.drawRange.start,this.drawRange.count=source.drawRange.count,this.userData=source.userData,this._transformed=source._transformed,this}dispose(){this.dispatchEvent({type:"dispose"})}};var InterleavedBuffer=class{constructor(array,stride){this.isInterleavedBuffer=!0,this.array=array,this.stride=stride,this.count=array!==void 0?array.length/stride:0,this.usage=StaticDrawUsage,this.updateRanges=[],this.version=0,this.uuid=generateUUID()}onUploadCallback(){}set needsUpdate(value){value===!0&&this.version++}setUsage(value){return this.usage=value,this}addUpdateRange(start,count){this.updateRanges.push({start,count})}clearUpdateRanges(){this.updateRanges.length=0}copy(source){return this.array=new source.array.constructor(source.array),this.count=source.count,this.stride=source.stride,this.usage=source.usage,this}copyAt(index1,interleavedBuffer,index2){index1*=this.stride,index2*=interleavedBuffer.stride;for(let i=0,l=this.stride;i<l;i++)this.array[index1+i]=interleavedBuffer.array[index2+i];return this}set(value,offset=0){return this.array.set(value,offset),this}clone(data){data.arrayBuffers===void 0&&(data.arrayBuffers={}),this.array.buffer._uuid===void 0&&(this.array.buffer._uuid=generateUUID()),data.arrayBuffers[this.array.buffer._uuid]===void 0&&(data.arrayBuffers[this.array.buffer._uuid]=this.array.slice(0).buffer);let array=new this.array.constructor(data.arrayBuffers[this.array.buffer._uuid]),ib=new this.constructor(array,this.stride);return ib.setUsage(this.usage),ib}onUpload(callback){return this.onUploadCallback=callback,this}toJSON(data){data.arrayBuffers===void 0&&(data.arrayBuffers={}),this.array.buffer._uuid===void 0&&(this.array.buffer._uuid=generateUUID()),data.arrayBuffers[this.array.buffer._uuid]===void 0&&(data.arrayBuffers[this.array.buffer._uuid]=Array.from(new Uint32Array(this.array.buffer)));let json={uuid:this.uuid,buffer:this.array.buffer._uuid,type:this.array.constructor.name,stride:this.stride};return json.usage=this.usage,json}};var _vector5=new Vector3,InterleavedBufferAttribute=class _InterleavedBufferAttribute{constructor(interleavedBuffer,itemSize,offset,normalized=!1){this.isInterleavedBufferAttribute=!0,this.name="",this.data=interleavedBuffer,this.itemSize=itemSize,this.offset=offset,this.normalized=normalized}get count(){return this.data.count}get array(){return this.data.array}set needsUpdate(value){this.data.needsUpdate=value}applyMatrix4(m){for(let i=0,l=this.data.count;i<l;i++)_vector5.fromBufferAttribute(this,i),_vector5.applyMatrix4(m),this.setXYZ(i,_vector5.x,_vector5.y,_vector5.z);return this}applyNormalMatrix(m){for(let i=0,l=this.count;i<l;i++)_vector5.fromBufferAttribute(this,i),_vector5.applyNormalMatrix(m),this.setXYZ(i,_vector5.x,_vector5.y,_vector5.z);return this}transformDirection(m){for(let i=0,l=this.count;i<l;i++)_vector5.fromBufferAttribute(this,i),_vector5.transformDirection(m),this.setXYZ(i,_vector5.x,_vector5.y,_vector5.z);return this}getComponent(index,component){let value=this.array[index*this.data.stride+this.offset+component];return this.normalized&&(value=denormalize(value,this.array)),value}setComponent(index,component,value){return this.normalized&&(value=normalize(value,this.array)),this.data.array[index*this.data.stride+this.offset+component]=value,this}setX(index,x){return this.normalized&&(x=normalize(x,this.array)),this.data.array[index*this.data.stride+this.offset]=x,this}setY(index,y){return this.normalized&&(y=normalize(y,this.array)),this.data.array[index*this.data.stride+this.offset+1]=y,this}setZ(index,z){return this.normalized&&(z=normalize(z,this.array)),this.data.array[index*this.data.stride+this.offset+2]=z,this}setW(index,w){return this.normalized&&(w=normalize(w,this.array)),this.data.array[index*this.data.stride+this.offset+3]=w,this}getX(index){let x=this.data.array[index*this.data.stride+this.offset];return this.normalized&&(x=denormalize(x,this.array)),x}getY(index){let y=this.data.array[index*this.data.stride+this.offset+1];return this.normalized&&(y=denormalize(y,this.array)),y}getZ(index){let z=this.data.array[index*this.data.stride+this.offset+2];return this.normalized&&(z=denormalize(z,this.array)),z}getW(index){let w=this.data.array[index*this.data.stride+this.offset+3];return this.normalized&&(w=denormalize(w,this.array)),w}setXY(index,x,y){return index=index*this.data.stride+this.offset,this.normalized&&(x=normalize(x,this.array),y=normalize(y,this.array)),this.data.array[index+0]=x,this.data.array[index+1]=y,this}setXYZ(index,x,y,z){return index=index*this.data.stride+this.offset,this.normalized&&(x=normalize(x,this.array),y=normalize(y,this.array),z=normalize(z,this.array)),this.data.array[index+0]=x,this.data.array[index+1]=y,this.data.array[index+2]=z,this}setXYZW(index,x,y,z,w){return index=index*this.data.stride+this.offset,this.normalized&&(x=normalize(x,this.array),y=normalize(y,this.array),z=normalize(z,this.array),w=normalize(w,this.array)),this.data.array[index+0]=x,this.data.array[index+1]=y,this.data.array[index+2]=z,this.data.array[index+3]=w,this}clone(data){if(data===void 0){log("InterleavedBufferAttribute.clone(): Cloning an interleaved buffer attribute will de-interleave buffer data.");let array=[];for(let i=0;i<this.count;i++){let index=i*this.data.stride+this.offset;for(let j=0;j<this.itemSize;j++)array.push(this.data.array[index+j])}return new BufferAttribute(new this.array.constructor(array),this.itemSize,this.normalized)}else return data.interleavedBuffers===void 0&&(data.interleavedBuffers={}),data.interleavedBuffers[this.data.uuid]===void 0&&(data.interleavedBuffers[this.data.uuid]=this.data.clone(data)),new _InterleavedBufferAttribute(data.interleavedBuffers[this.data.uuid],this.itemSize,this.offset,this.normalized)}toJSON(data){if(data===void 0){log("InterleavedBufferAttribute.toJSON(): Serializing an interleaved buffer attribute will de-interleave buffer data.");let array=[];for(let i=0;i<this.count;i++){let index=i*this.data.stride+this.offset;for(let j=0;j<this.itemSize;j++)array.push(this.data.array[index+j])}return{itemSize:this.itemSize,type:this.array.constructor.name,array,normalized:this.normalized}}else return data.interleavedBuffers===void 0&&(data.interleavedBuffers={}),data.interleavedBuffers[this.data.uuid]===void 0&&(data.interleavedBuffers[this.data.uuid]=this.data.toJSON(data)),{isInterleavedBufferAttribute:!0,itemSize:this.itemSize,data:this.data.uuid,offset:this.offset,normalized:this.normalized}}};var _vector1=new Vector3,_vector23=new Vector3,_normalMatrix=new Matrix3,Plane=class{constructor(normal=new Vector3(1,0,0),constant=0){this.isPlane=!0,this.normal=normal,this.constant=constant}set(normal,constant){return this.normal.copy(normal),this.constant=constant,this}setComponents(x,y,z,w){return this.normal.set(x,y,z),this.constant=w,this}setFromNormalAndCoplanarPoint(normal,point){return this.normal.copy(normal),this.constant=-point.dot(this.normal),this}setFromCoplanarPoints(a,b,c){let normal=_vector1.subVectors(c,b).cross(_vector23.subVectors(a,b)).normalize();return this.setFromNormalAndCoplanarPoint(normal,a),this}copy(plane){return this.normal.copy(plane.normal),this.constant=plane.constant,this}normalize(){let inverseNormalLength=1/this.normal.length();return this.normal.multiplyScalar(inverseNormalLength),this.constant*=inverseNormalLength,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(point){return this.normal.dot(point)+this.constant}distanceToSphere(sphere){return this.distanceToPoint(sphere.center)-sphere.radius}projectPoint(point,target){return target.copy(point).addScaledVector(this.normal,-this.distanceToPoint(point))}intersectLine(line,target,clampToLine=!0){let direction=line.delta(_vector1),denominator=this.normal.dot(direction);if(denominator===0)return this.distanceToPoint(line.start)===0?target.copy(line.start):null;let t=-(line.start.dot(this.normal)+this.constant)/denominator;return clampToLine===!0&&(t<0||t>1)?null:target.copy(line.start).addScaledVector(direction,t)}intersectsLine(line){let startSign=this.distanceToPoint(line.start),endSign=this.distanceToPoint(line.end);return startSign<0&&endSign>0||endSign<0&&startSign>0}intersectsBox(box){return box.intersectsPlane(this)}intersectsSphere(sphere){return sphere.intersectsPlane(this)}coplanarPoint(target){return target.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(matrix,optionalNormalMatrix){let normalMatrix=optionalNormalMatrix||_normalMatrix.getNormalMatrix(matrix),referencePoint=this.coplanarPoint(_vector1).applyMatrix4(matrix),normal=this.normal.applyMatrix3(normalMatrix).normalize();return this.constant=-referencePoint.dot(normal),this}translate(offset){return this.constant-=offset.dot(this.normal),this}equals(plane){return plane.normal.equals(this.normal)&&plane.constant===this.constant}clone(){return new this.constructor().copy(this)}toJSON(){return{normal:this.normal.toArray(),constant:this.constant}}fromJSON(json){return this.normal.fromArray(json.normal),this.constant=json.constant,this}};var _materialId=0,Material=class extends EventDispatcher{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:_materialId++}),this.uuid=generateUUID(),this.name="",this.type="Material",this.blending=NormalBlending,this.side=FrontSide,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=SrcAlphaFactor,this.blendDst=OneMinusSrcAlphaFactor,this.blendEquation=AddEquation,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new Color(0,0,0),this.blendAlpha=0,this.depthFunc=LessEqualDepth,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=AlwaysStencilFunc,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=KeepStencilOp,this.stencilZFail=KeepStencilOp,this.stencilZPass=KeepStencilOp,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.allowOverride=!0,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(value){this._alphaTest>0!=value>0&&this.version++,this._alphaTest=value}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(values){if(values!==void 0)for(let key in values){let newValue=values[key];if(newValue===void 0){warn(`Material: parameter '${key}' has value of undefined.`);continue}let currentValue=this[key];if(currentValue===void 0){warn(`Material: '${key}' is not a property of THREE.${this.type}.`);continue}currentValue&&currentValue.isColor?currentValue.set(newValue):currentValue&&currentValue.isVector2&&newValue&&newValue.isVector2||currentValue&&currentValue.isEuler&&newValue&&newValue.isEuler||currentValue&&currentValue.isVector3&&newValue&&newValue.isVector3?currentValue.copy(newValue):this[key]=newValue}}toJSON(meta){let isRootObject=meta===void 0||typeof meta=="string";isRootObject&&(meta={textures:{},images:{}});let data={metadata:{version:4.7,type:"Material",generator:"Material.toJSON"}};data.uuid=this.uuid,data.type=this.type,data.blending=this.blending,data.side=this.side,data.shadowSide=this.shadowSide,data.vertexColors=this.vertexColors,data.opacity=this.opacity,data.transparent=this.transparent,data.blendSrc=this.blendSrc,data.blendDst=this.blendDst,data.blendEquation=this.blendEquation,data.blendSrcAlpha=this.blendSrcAlpha,data.blendDstAlpha=this.blendDstAlpha,data.blendEquationAlpha=this.blendEquationAlpha,data.blendColor=this.blendColor.getHex(),data.blendAlpha=this.blendAlpha,data.depthFunc=this.depthFunc,data.depthTest=this.depthTest,data.depthWrite=this.depthWrite,data.colorWrite=this.colorWrite,data.clipIntersection=this.clipIntersection,data.clipShadows=this.clipShadows,data.stencilWriteMask=this.stencilWriteMask,data.stencilFunc=this.stencilFunc,data.stencilRef=this.stencilRef,data.stencilFuncMask=this.stencilFuncMask,data.stencilFail=this.stencilFail,data.stencilZFail=this.stencilZFail,data.stencilZPass=this.stencilZPass,data.stencilWrite=this.stencilWrite,data.polygonOffset=this.polygonOffset,data.polygonOffsetFactor=this.polygonOffsetFactor,data.polygonOffsetUnits=this.polygonOffsetUnits,data.dithering=this.dithering,data.alphaTest=this.alphaTest,data.alphaHash=this.alphaHash,data.alphaToCoverage=this.alphaToCoverage,data.premultipliedAlpha=this.premultipliedAlpha,data.forceSinglePass=this.forceSinglePass,data.allowOverride=this.allowOverride,data.visible=this.visible,data.toneMapped=this.toneMapped,data.name=this.name,this.color&&this.color.isColor&&(data.color=this.color.getHex()),this.roughness!==void 0&&(data.roughness=this.roughness),this.metalness!==void 0&&(data.metalness=this.metalness),this.sheen!==void 0&&(data.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(data.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(data.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(data.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&(data.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(data.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(data.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(data.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(data.shininess=this.shininess),this.clearcoat!==void 0&&(data.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(data.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(data.clearcoatMap=this.clearcoatMap.toJSON(meta).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(data.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(meta).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(data.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(meta).uuid,data.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.sheenColorMap&&this.sheenColorMap.isTexture&&(data.sheenColorMap=this.sheenColorMap.toJSON(meta).uuid),this.sheenRoughnessMap&&this.sheenRoughnessMap.isTexture&&(data.sheenRoughnessMap=this.sheenRoughnessMap.toJSON(meta).uuid),this.dispersion!==void 0&&(data.dispersion=this.dispersion),this.retroreflectivity!==void 0&&(data.retroreflectivity=this.retroreflectivity),this.iridescence!==void 0&&(data.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(data.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(data.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(data.iridescenceMap=this.iridescenceMap.toJSON(meta).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(data.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(meta).uuid),this.anisotropy!==void 0&&(data.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(data.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(data.anisotropyMap=this.anisotropyMap.toJSON(meta).uuid),this.map&&this.map.isTexture&&(data.map=this.map.toJSON(meta).uuid),this.matcap&&this.matcap.isTexture&&(data.matcap=this.matcap.toJSON(meta).uuid),this.alphaMap&&this.alphaMap.isTexture&&(data.alphaMap=this.alphaMap.toJSON(meta).uuid),this.lightMap&&this.lightMap.isTexture&&(data.lightMap=this.lightMap.toJSON(meta).uuid,data.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(data.aoMap=this.aoMap.toJSON(meta).uuid,data.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(data.bumpMap=this.bumpMap.toJSON(meta).uuid,data.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(data.normalMap=this.normalMap.toJSON(meta).uuid,data.normalMapType=this.normalMapType,data.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(data.displacementMap=this.displacementMap.toJSON(meta).uuid,data.displacementScale=this.displacementScale,data.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(data.roughnessMap=this.roughnessMap.toJSON(meta).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(data.metalnessMap=this.metalnessMap.toJSON(meta).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(data.emissiveMap=this.emissiveMap.toJSON(meta).uuid),this.specularMap&&this.specularMap.isTexture&&(data.specularMap=this.specularMap.toJSON(meta).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(data.specularIntensityMap=this.specularIntensityMap.toJSON(meta).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(data.specularColorMap=this.specularColorMap.toJSON(meta).uuid),this.envMap&&this.envMap.isTexture&&(data.envMap=this.envMap.toJSON(meta).uuid,this.combine!==void 0&&(data.combine=this.combine)),this.envMapRotation!==void 0&&(data.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(data.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(data.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(data.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(data.gradientMap=this.gradientMap.toJSON(meta).uuid),this.transmission!==void 0&&(data.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(data.transmissionMap=this.transmissionMap.toJSON(meta).uuid),this.thickness!==void 0&&(data.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(data.thicknessMap=this.thicknessMap.toJSON(meta).uuid),this.attenuationDistance!==void 0&&(data.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(data.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(data.size=this.size),this.sizeAttenuation!==void 0&&(data.sizeAttenuation=this.sizeAttenuation),Array.isArray(this.clippingPlanes)&&this.clippingPlanes.length>0&&(data.clippingPlanes=this.clippingPlanes.map(plane=>plane.toJSON())),this.rotation!==void 0&&(data.rotation=this.rotation),this.depthPacking!==void 0&&(data.depthPacking=this.depthPacking),this.linewidth!==void 0&&(data.linewidth=this.linewidth),this.linecap!==void 0&&(data.linecap=this.linecap),this.linejoin!==void 0&&(data.linejoin=this.linejoin),this.dashSize!==void 0&&(data.dashSize=this.dashSize),this.gapSize!==void 0&&(data.gapSize=this.gapSize),this.scale!==void 0&&(data.scale=this.scale),this.wireframe!==void 0&&(data.wireframe=this.wireframe),this.wireframeLinewidth!==void 0&&(data.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!==void 0&&(data.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!==void 0&&(data.wireframeLinejoin=this.wireframeLinejoin),this.flatShading!==void 0&&(data.flatShading=this.flatShading),this.fog!==void 0&&(data.fog=this.fog),Object.keys(this.userData).length>0&&(data.userData=this.userData);function extractFromCache(cache){let values=[];for(let key in cache){let data2=cache[key];delete data2.metadata,values.push(data2)}return values}if(isRootObject){let textures=extractFromCache(meta.textures),images=extractFromCache(meta.images);textures.length>0&&(data.textures=textures),images.length>0&&(data.images=images)}return data}fromJSON(json,textures){if(json.uuid!==void 0&&(this.uuid=json.uuid),json.name!==void 0&&(this.name=json.name),json.color!==void 0&&this.color!==void 0&&this.color.setHex(json.color),json.roughness!==void 0&&(this.roughness=json.roughness),json.metalness!==void 0&&(this.metalness=json.metalness),json.sheen!==void 0&&(this.sheen=json.sheen),json.sheenColor!==void 0&&(this.sheenColor=new Color().setHex(json.sheenColor)),json.sheenRoughness!==void 0&&(this.sheenRoughness=json.sheenRoughness),json.emissive!==void 0&&this.emissive!==void 0&&this.emissive.setHex(json.emissive),json.specular!==void 0&&this.specular!==void 0&&this.specular.setHex(json.specular),json.specularIntensity!==void 0&&(this.specularIntensity=json.specularIntensity),json.specularColor!==void 0&&this.specularColor!==void 0&&this.specularColor.setHex(json.specularColor),json.shininess!==void 0&&(this.shininess=json.shininess),json.clearcoat!==void 0&&(this.clearcoat=json.clearcoat),json.clearcoatRoughness!==void 0&&(this.clearcoatRoughness=json.clearcoatRoughness),json.dispersion!==void 0&&(this.dispersion=json.dispersion),json.retroreflectivity!==void 0&&(this.retroreflectivity=json.retroreflectivity),json.iridescence!==void 0&&(this.iridescence=json.iridescence),json.iridescenceIOR!==void 0&&(this.iridescenceIOR=json.iridescenceIOR),json.iridescenceThicknessRange!==void 0&&(this.iridescenceThicknessRange=json.iridescenceThicknessRange),json.transmission!==void 0&&(this.transmission=json.transmission),json.thickness!==void 0&&(this.thickness=json.thickness),json.attenuationDistance!==void 0&&(this.attenuationDistance=json.attenuationDistance),json.attenuationColor!==void 0&&this.attenuationColor!==void 0&&this.attenuationColor.setHex(json.attenuationColor),json.anisotropy!==void 0&&(this.anisotropy=json.anisotropy),json.anisotropyRotation!==void 0&&(this.anisotropyRotation=json.anisotropyRotation),json.fog!==void 0&&(this.fog=json.fog),json.flatShading!==void 0&&(this.flatShading=json.flatShading),json.blending!==void 0&&(this.blending=json.blending),json.combine!==void 0&&(this.combine=json.combine),json.side!==void 0&&(this.side=json.side),json.shadowSide!==void 0&&(this.shadowSide=json.shadowSide),json.opacity!==void 0&&(this.opacity=json.opacity),json.transparent!==void 0&&(this.transparent=json.transparent),json.alphaTest!==void 0&&(this.alphaTest=json.alphaTest),json.alphaHash!==void 0&&(this.alphaHash=json.alphaHash),json.depthFunc!==void 0&&(this.depthFunc=json.depthFunc),json.depthTest!==void 0&&(this.depthTest=json.depthTest),json.depthWrite!==void 0&&(this.depthWrite=json.depthWrite),json.colorWrite!==void 0&&(this.colorWrite=json.colorWrite),json.clippingPlanes!==void 0&&(this.clippingPlanes=json.clippingPlanes.map(plane=>new Plane().fromJSON(plane))),json.clipIntersection!==void 0&&(this.clipIntersection=json.clipIntersection),json.clipShadows!==void 0&&(this.clipShadows=json.clipShadows),json.depthPacking!==void 0&&(this.depthPacking=json.depthPacking),json.blendSrc!==void 0&&(this.blendSrc=json.blendSrc),json.blendDst!==void 0&&(this.blendDst=json.blendDst),json.blendEquation!==void 0&&(this.blendEquation=json.blendEquation),json.blendSrcAlpha!==void 0&&(this.blendSrcAlpha=json.blendSrcAlpha),json.blendDstAlpha!==void 0&&(this.blendDstAlpha=json.blendDstAlpha),json.blendEquationAlpha!==void 0&&(this.blendEquationAlpha=json.blendEquationAlpha),json.blendColor!==void 0&&this.blendColor!==void 0&&this.blendColor.setHex(json.blendColor),json.blendAlpha!==void 0&&(this.blendAlpha=json.blendAlpha),json.stencilWriteMask!==void 0&&(this.stencilWriteMask=json.stencilWriteMask),json.stencilFunc!==void 0&&(this.stencilFunc=json.stencilFunc),json.stencilRef!==void 0&&(this.stencilRef=json.stencilRef),json.stencilFuncMask!==void 0&&(this.stencilFuncMask=json.stencilFuncMask),json.stencilFail!==void 0&&(this.stencilFail=json.stencilFail),json.stencilZFail!==void 0&&(this.stencilZFail=json.stencilZFail),json.stencilZPass!==void 0&&(this.stencilZPass=json.stencilZPass),json.stencilWrite!==void 0&&(this.stencilWrite=json.stencilWrite),json.wireframe!==void 0&&(this.wireframe=json.wireframe),json.wireframeLinewidth!==void 0&&(this.wireframeLinewidth=json.wireframeLinewidth),json.wireframeLinecap!==void 0&&(this.wireframeLinecap=json.wireframeLinecap),json.wireframeLinejoin!==void 0&&(this.wireframeLinejoin=json.wireframeLinejoin),json.rotation!==void 0&&(this.rotation=json.rotation),json.linewidth!==void 0&&(this.linewidth=json.linewidth),json.linecap!==void 0&&(this.linecap=json.linecap),json.linejoin!==void 0&&(this.linejoin=json.linejoin),json.dashSize!==void 0&&(this.dashSize=json.dashSize),json.gapSize!==void 0&&(this.gapSize=json.gapSize),json.scale!==void 0&&(this.scale=json.scale),json.polygonOffset!==void 0&&(this.polygonOffset=json.polygonOffset),json.polygonOffsetFactor!==void 0&&(this.polygonOffsetFactor=json.polygonOffsetFactor),json.polygonOffsetUnits!==void 0&&(this.polygonOffsetUnits=json.polygonOffsetUnits),json.dithering!==void 0&&(this.dithering=json.dithering),json.alphaToCoverage!==void 0&&(this.alphaToCoverage=json.alphaToCoverage),json.premultipliedAlpha!==void 0&&(this.premultipliedAlpha=json.premultipliedAlpha),json.forceSinglePass!==void 0&&(this.forceSinglePass=json.forceSinglePass),json.allowOverride!==void 0&&(this.allowOverride=json.allowOverride),json.visible!==void 0&&(this.visible=json.visible),json.toneMapped!==void 0&&(this.toneMapped=json.toneMapped),json.userData!==void 0&&(this.userData=json.userData),json.vertexColors!==void 0&&(typeof json.vertexColors=="number"?this.vertexColors=json.vertexColors>0:this.vertexColors=json.vertexColors),json.size!==void 0&&(this.size=json.size),json.sizeAttenuation!==void 0&&(this.sizeAttenuation=json.sizeAttenuation),json.map!==void 0&&(this.map=textures[json.map]||null),json.matcap!==void 0&&(this.matcap=textures[json.matcap]||null),json.alphaMap!==void 0&&(this.alphaMap=textures[json.alphaMap]||null),json.bumpMap!==void 0&&(this.bumpMap=textures[json.bumpMap]||null),json.bumpScale!==void 0&&(this.bumpScale=json.bumpScale),json.normalMap!==void 0&&(this.normalMap=textures[json.normalMap]||null),json.normalMapType!==void 0&&(this.normalMapType=json.normalMapType),json.normalScale!==void 0){let normalScale=json.normalScale;Array.isArray(normalScale)===!1&&(normalScale=[normalScale,normalScale]),this.normalScale=new Vector2().fromArray(normalScale)}return json.displacementMap!==void 0&&(this.displacementMap=textures[json.displacementMap]||null),json.displacementScale!==void 0&&(this.displacementScale=json.displacementScale),json.displacementBias!==void 0&&(this.displacementBias=json.displacementBias),json.roughnessMap!==void 0&&(this.roughnessMap=textures[json.roughnessMap]||null),json.metalnessMap!==void 0&&(this.metalnessMap=textures[json.metalnessMap]||null),json.emissiveMap!==void 0&&(this.emissiveMap=textures[json.emissiveMap]||null),json.emissiveIntensity!==void 0&&(this.emissiveIntensity=json.emissiveIntensity),json.specularMap!==void 0&&(this.specularMap=textures[json.specularMap]||null),json.specularIntensityMap!==void 0&&(this.specularIntensityMap=textures[json.specularIntensityMap]||null),json.specularColorMap!==void 0&&(this.specularColorMap=textures[json.specularColorMap]||null),json.envMap!==void 0&&(this.envMap=textures[json.envMap]||null),json.envMapRotation!==void 0&&this.envMapRotation.fromArray(json.envMapRotation),json.envMapIntensity!==void 0&&(this.envMapIntensity=json.envMapIntensity),json.reflectivity!==void 0&&(this.reflectivity=json.reflectivity),json.refractionRatio!==void 0&&(this.refractionRatio=json.refractionRatio),json.lightMap!==void 0&&(this.lightMap=textures[json.lightMap]||null),json.lightMapIntensity!==void 0&&(this.lightMapIntensity=json.lightMapIntensity),json.aoMap!==void 0&&(this.aoMap=textures[json.aoMap]||null),json.aoMapIntensity!==void 0&&(this.aoMapIntensity=json.aoMapIntensity),json.gradientMap!==void 0&&(this.gradientMap=textures[json.gradientMap]||null),json.clearcoatMap!==void 0&&(this.clearcoatMap=textures[json.clearcoatMap]||null),json.clearcoatRoughnessMap!==void 0&&(this.clearcoatRoughnessMap=textures[json.clearcoatRoughnessMap]||null),json.clearcoatNormalMap!==void 0&&(this.clearcoatNormalMap=textures[json.clearcoatNormalMap]||null),json.clearcoatNormalScale!==void 0&&(this.clearcoatNormalScale=new Vector2().fromArray(json.clearcoatNormalScale)),json.iridescenceMap!==void 0&&(this.iridescenceMap=textures[json.iridescenceMap]||null),json.iridescenceThicknessMap!==void 0&&(this.iridescenceThicknessMap=textures[json.iridescenceThicknessMap]||null),json.transmissionMap!==void 0&&(this.transmissionMap=textures[json.transmissionMap]||null),json.thicknessMap!==void 0&&(this.thicknessMap=textures[json.thicknessMap]||null),json.anisotropyMap!==void 0&&(this.anisotropyMap=textures[json.anisotropyMap]||null),json.sheenColorMap!==void 0&&(this.sheenColorMap=textures[json.sheenColorMap]||null),json.sheenRoughnessMap!==void 0&&(this.sheenRoughnessMap=textures[json.sheenRoughnessMap]||null),this}clone(){return new this.constructor().copy(this)}copy(source){this.name=source.name,this.blending=source.blending,this.side=source.side,this.vertexColors=source.vertexColors,this.opacity=source.opacity,this.transparent=source.transparent,this.blendSrc=source.blendSrc,this.blendDst=source.blendDst,this.blendEquation=source.blendEquation,this.blendSrcAlpha=source.blendSrcAlpha,this.blendDstAlpha=source.blendDstAlpha,this.blendEquationAlpha=source.blendEquationAlpha,this.blendColor.copy(source.blendColor),this.blendAlpha=source.blendAlpha,this.depthFunc=source.depthFunc,this.depthTest=source.depthTest,this.depthWrite=source.depthWrite,this.stencilWriteMask=source.stencilWriteMask,this.stencilFunc=source.stencilFunc,this.stencilRef=source.stencilRef,this.stencilFuncMask=source.stencilFuncMask,this.stencilFail=source.stencilFail,this.stencilZFail=source.stencilZFail,this.stencilZPass=source.stencilZPass,this.stencilWrite=source.stencilWrite;let srcPlanes=source.clippingPlanes,dstPlanes=null;if(srcPlanes!==null){let n=srcPlanes.length;dstPlanes=new Array(n);for(let i=0;i!==n;++i)dstPlanes[i]=srcPlanes[i].clone()}return this.clippingPlanes=dstPlanes,this.clipIntersection=source.clipIntersection,this.clipShadows=source.clipShadows,this.shadowSide=source.shadowSide,this.colorWrite=source.colorWrite,this.precision=source.precision,this.polygonOffset=source.polygonOffset,this.polygonOffsetFactor=source.polygonOffsetFactor,this.polygonOffsetUnits=source.polygonOffsetUnits,this.dithering=source.dithering,this.alphaTest=source.alphaTest,this.alphaHash=source.alphaHash,this.alphaToCoverage=source.alphaToCoverage,this.premultipliedAlpha=source.premultipliedAlpha,this.forceSinglePass=source.forceSinglePass,this.allowOverride=source.allowOverride,this.visible=source.visible,this.toneMapped=source.toneMapped,this.userData=JSON.parse(JSON.stringify(source.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(value){value===!0&&this.version++}};var SpriteMaterial=class extends Material{constructor(parameters){super(),this.isSpriteMaterial=!0,this.type="SpriteMaterial",this.color=new Color(16777215),this.map=null,this.alphaMap=null,this.rotation=0,this.sizeAttenuation=!0,this.transparent=!0,this.fog=!0,this.setValues(parameters)}copy(source){return super.copy(source),this.color.copy(source.color),this.map=source.map,this.alphaMap=source.alphaMap,this.rotation=source.rotation,this.sizeAttenuation=source.sizeAttenuation,this.fog=source.fog,this}};var _geometry,_intersectPoint=new Vector3,_worldScale=new Vector3,_mvPosition=new Vector3,_alignedPosition=new Vector2,_rotatedPosition=new Vector2,_viewWorldMatrix=new Matrix4,_vA=new Vector3,_vB=new Vector3,_vC=new Vector3,_uvA=new Vector2,_uvB=new Vector2,_uvC=new Vector2,Sprite=class extends Object3D{constructor(material=new SpriteMaterial){if(super(),this.isSprite=!0,this.type="Sprite",_geometry===void 0){_geometry=new BufferGeometry;let float32Array=new Float32Array([-.5,-.5,0,0,0,.5,-.5,0,1,0,.5,.5,0,1,1,-.5,.5,0,0,1]),interleavedBuffer=new InterleavedBuffer(float32Array,5);_geometry.setIndex([0,1,2,0,2,3]),_geometry.setAttribute("position",new InterleavedBufferAttribute(interleavedBuffer,3,0,!1)),_geometry.setAttribute("uv",new InterleavedBufferAttribute(interleavedBuffer,2,3,!1))}this.geometry=_geometry,this.material=material,this.center=new Vector2(.5,.5),this.count=1}intersectsFrustum(frustum){return frustum.intersectsSprite(this)}raycast(raycaster,intersects2){raycaster.camera===null&&error('Sprite: "Raycaster.camera" needs to be set in order to raycast against sprites.'),_worldScale.setFromMatrixScale(this.matrixWorld),_viewWorldMatrix.copy(raycaster.camera.matrixWorld),this.modelViewMatrix.multiplyMatrices(raycaster.camera.matrixWorldInverse,this.matrixWorld),_mvPosition.setFromMatrixPosition(this.modelViewMatrix),raycaster.camera.isPerspectiveCamera&&this.material.sizeAttenuation===!1&&_worldScale.multiplyScalar(-_mvPosition.z);let rotation=this.material.rotation,sin,cos;rotation!==0&&(cos=Math.cos(rotation),sin=Math.sin(rotation));let center=this.center;transformVertex(_vA.set(-.5,-.5,0),_mvPosition,center,_worldScale,sin,cos),transformVertex(_vB.set(.5,-.5,0),_mvPosition,center,_worldScale,sin,cos),transformVertex(_vC.set(.5,.5,0),_mvPosition,center,_worldScale,sin,cos),_uvA.set(0,0),_uvB.set(1,0),_uvC.set(1,1);let intersect2=raycaster.ray.intersectTriangle(_vA,_vB,_vC,!1,_intersectPoint);if(intersect2===null&&(transformVertex(_vB.set(-.5,.5,0),_mvPosition,center,_worldScale,sin,cos),_uvB.set(0,1),intersect2=raycaster.ray.intersectTriangle(_vA,_vC,_vB,!1,_intersectPoint),intersect2===null))return;let distance=raycaster.ray.origin.distanceTo(_intersectPoint);distance<raycaster.near||distance>raycaster.far||intersects2.push({distance,point:_intersectPoint.clone(),uv:Triangle.getInterpolation(_intersectPoint,_vA,_vB,_vC,_uvA,_uvB,_uvC,new Vector2),face:null,object:this})}copy(source,recursive){return super.copy(source,recursive),source.center!==void 0&&this.center.copy(source.center),this.material=source.material,this}};function transformVertex(vertexPosition,mvPosition,center,scale,sin,cos){_alignedPosition.subVectors(vertexPosition,center).addScalar(.5).multiply(scale),sin!==void 0?(_rotatedPosition.x=cos*_alignedPosition.x-sin*_alignedPosition.y,_rotatedPosition.y=sin*_alignedPosition.x+cos*_alignedPosition.y):_rotatedPosition.copy(_alignedPosition),vertexPosition.copy(mvPosition),vertexPosition.x+=_rotatedPosition.x,vertexPosition.y+=_rotatedPosition.y,vertexPosition.applyMatrix4(_viewWorldMatrix)}var _vector6=new Vector3,_segCenter=new Vector3,_segDir=new Vector3,_diff=new Vector3,Ray=class{constructor(origin=new Vector3,direction=new Vector3(0,0,-1)){this.origin=origin,this.direction=direction}set(origin,direction){return this.origin.copy(origin),this.direction.copy(direction),this}copy(ray){return this.origin.copy(ray.origin),this.direction.copy(ray.direction),this}at(t,target){return target.copy(this.origin).addScaledVector(this.direction,t)}lookAt(v){return this.direction.copy(v).sub(this.origin).normalize(),this}recast(t){return this.origin.copy(this.at(t,_vector6)),this}closestPointToPoint(point,target){target.subVectors(point,this.origin);let directionDistance=target.dot(this.direction);return directionDistance<0?target.copy(this.origin):target.copy(this.origin).addScaledVector(this.direction,directionDistance)}distanceToPoint(point){return Math.sqrt(this.distanceSqToPoint(point))}distanceSqToPoint(point){let directionDistance=_vector6.subVectors(point,this.origin).dot(this.direction);return directionDistance<0?this.origin.distanceToSquared(point):(_vector6.copy(this.origin).addScaledVector(this.direction,directionDistance),_vector6.distanceToSquared(point))}distanceSqToSegment(v0,v1,optionalPointOnRay,optionalPointOnSegment){_segCenter.copy(v0).add(v1).multiplyScalar(.5),_segDir.copy(v1).sub(v0).normalize(),_diff.copy(this.origin).sub(_segCenter);let segExtent=v0.distanceTo(v1)*.5,a01=-this.direction.dot(_segDir),b0=_diff.dot(this.direction),b1=-_diff.dot(_segDir),c=_diff.lengthSq(),det=Math.abs(1-a01*a01),s0,s1,sqrDist,extDet;if(det>0)if(s0=a01*b1-b0,s1=a01*b0-b1,extDet=segExtent*det,s0>=0)if(s1>=-extDet)if(s1<=extDet){let invDet=1/det;s0*=invDet,s1*=invDet,sqrDist=s0*(s0+a01*s1+2*b0)+s1*(a01*s0+s1+2*b1)+c}else s1=segExtent,s0=Math.max(0,-(a01*s1+b0)),sqrDist=-s0*s0+s1*(s1+2*b1)+c;else s1=-segExtent,s0=Math.max(0,-(a01*s1+b0)),sqrDist=-s0*s0+s1*(s1+2*b1)+c;else s1<=-extDet?(s0=Math.max(0,-(-a01*segExtent+b0)),s1=s0>0?-segExtent:Math.min(Math.max(-segExtent,-b1),segExtent),sqrDist=-s0*s0+s1*(s1+2*b1)+c):s1<=extDet?(s0=0,s1=Math.min(Math.max(-segExtent,-b1),segExtent),sqrDist=s1*(s1+2*b1)+c):(s0=Math.max(0,-(a01*segExtent+b0)),s1=s0>0?segExtent:Math.min(Math.max(-segExtent,-b1),segExtent),sqrDist=-s0*s0+s1*(s1+2*b1)+c);else s1=a01>0?-segExtent:segExtent,s0=Math.max(0,-(a01*s1+b0)),sqrDist=-s0*s0+s1*(s1+2*b1)+c;return optionalPointOnRay&&optionalPointOnRay.copy(this.origin).addScaledVector(this.direction,s0),optionalPointOnSegment&&optionalPointOnSegment.copy(_segCenter).addScaledVector(_segDir,s1),sqrDist}intersectSphere(sphere,target){if(sphere.radius<0)return null;_vector6.subVectors(sphere.center,this.origin);let tca=_vector6.dot(this.direction),d2=_vector6.dot(_vector6)-tca*tca,radius2=sphere.radius*sphere.radius;if(d2>radius2)return null;let thc=Math.sqrt(radius2-d2),t0=tca-thc,t1=tca+thc;return t1<0?null:t0<0?this.at(t1,target):this.at(t0,target)}intersectsSphere(sphere){return sphere.radius<0?!1:this.distanceSqToPoint(sphere.center)<=sphere.radius*sphere.radius}distanceToPlane(plane){let denominator=plane.normal.dot(this.direction);if(denominator===0)return plane.distanceToPoint(this.origin)===0?0:null;let t=-(this.origin.dot(plane.normal)+plane.constant)/denominator;return t>=0?t:null}intersectPlane(plane,target){let t=this.distanceToPlane(plane);return t===null?null:this.at(t,target)}intersectsPlane(plane){let distToPoint=plane.distanceToPoint(this.origin);return distToPoint===0||plane.normal.dot(this.direction)*distToPoint<0}intersectBox(box,target){let tmin,tmax,tymin,tymax,tzmin,tzmax,invdirx=1/this.direction.x,invdiry=1/this.direction.y,invdirz=1/this.direction.z,origin=this.origin;return invdirx>=0?(tmin=(box.min.x-origin.x)*invdirx,tmax=(box.max.x-origin.x)*invdirx):(tmin=(box.max.x-origin.x)*invdirx,tmax=(box.min.x-origin.x)*invdirx),invdiry>=0?(tymin=(box.min.y-origin.y)*invdiry,tymax=(box.max.y-origin.y)*invdiry):(tymin=(box.max.y-origin.y)*invdiry,tymax=(box.min.y-origin.y)*invdiry),tmin>tymax||tymin>tmax||((tymin>tmin||isNaN(tmin))&&(tmin=tymin),(tymax<tmax||isNaN(tmax))&&(tmax=tymax),invdirz>=0?(tzmin=(box.min.z-origin.z)*invdirz,tzmax=(box.max.z-origin.z)*invdirz):(tzmin=(box.max.z-origin.z)*invdirz,tzmax=(box.min.z-origin.z)*invdirz),tmin>tzmax||tzmin>tmax)||((tzmin>tmin||tmin!==tmin)&&(tmin=tzmin),(tzmax<tmax||tmax!==tmax)&&(tmax=tzmax),tmax<0)?null:this.at(tmin>=0?tmin:tmax,target)}intersectsBox(box){return this.intersectBox(box,_vector6)!==null}intersectTriangle(a,b,c,backfaceCulling,target){let origin=this.origin,direction=this.direction,dx=direction.x,dy=direction.y,dz=direction.z,aox=a.x-origin.x,aoy=a.y-origin.y,aoz=a.z-origin.z,box=b.x-origin.x,boy=b.y-origin.y,boz=b.z-origin.z,cox=c.x-origin.x,coy=c.y-origin.y,coz=c.z-origin.z,adx=Math.abs(dx),ady=Math.abs(dy),adz=Math.abs(dz),dkx,dky,dkz,akx,aky,akz,bkx,bky,bkz,ckx,cky,ckz;if(adx>=ady&&adx>=adz?(dkz=dx,akz=aox,bkz=box,ckz=cox,dx>=0?(dkx=dy,dky=dz,akx=aoy,aky=aoz,bkx=boy,bky=boz,ckx=coy,cky=coz):(dkx=dz,dky=dy,akx=aoz,aky=aoy,bkx=boz,bky=boy,ckx=coz,cky=coy)):ady>=adz?(dkz=dy,akz=aoy,bkz=boy,ckz=coy,dy>=0?(dkx=dz,dky=dx,akx=aoz,aky=aox,bkx=boz,bky=box,ckx=coz,cky=cox):(dkx=dx,dky=dz,akx=aox,aky=aoz,bkx=box,bky=boz,ckx=cox,cky=coz)):(dkz=dz,akz=aoz,bkz=boz,ckz=coz,dz>=0?(dkx=dx,dky=dy,akx=aox,aky=aoy,bkx=box,bky=boy,ckx=cox,cky=coy):(dkx=dy,dky=dx,akx=aoy,aky=aox,bkx=boy,bky=box,ckx=coy,cky=cox)),dkz===0)return null;let sx=dkx/dkz,sy=dky/dkz,sz=1/dkz,ax=akx-sx*akz,ay=aky-sy*akz,bx=bkx-sx*bkz,by=bky-sy*bkz,cx=ckx-sx*ckz,cy=cky-sy*ckz,u=cx*by-cy*bx,v=ax*cy-ay*cx,w=bx*ay-by*ax;if(backfaceCulling){if(u<0||v<0||w<0)return null}else if((u<0||v<0||w<0)&&(u>0||v>0||w>0))return null;let det=u+v+w;if(det===0)return null;let tScaled=sz*(u*akz+v*bkz+w*ckz);return(det>0?tScaled<0:tScaled>0)?null:this.at(tScaled/det,target)}applyMatrix4(matrix4){return this.origin.applyMatrix4(matrix4),this.direction.transformDirection(matrix4),this}equals(ray){return ray.origin.equals(this.origin)&&ray.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}};var MeshBasicMaterial=class extends Material{constructor(parameters){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new Color(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Euler,this.combine=MultiplyOperation,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(parameters)}copy(source){return super.copy(source),this.color.copy(source.color),this.map=source.map,this.lightMap=source.lightMap,this.lightMapIntensity=source.lightMapIntensity,this.aoMap=source.aoMap,this.aoMapIntensity=source.aoMapIntensity,this.specularMap=source.specularMap,this.alphaMap=source.alphaMap,this.envMap=source.envMap,this.envMapRotation.copy(source.envMapRotation),this.combine=source.combine,this.reflectivity=source.reflectivity,this.refractionRatio=source.refractionRatio,this.wireframe=source.wireframe,this.wireframeLinewidth=source.wireframeLinewidth,this.wireframeLinecap=source.wireframeLinecap,this.wireframeLinejoin=source.wireframeLinejoin,this.fog=source.fog,this}};var _inverseMatrix=new Matrix4,_ray=new Ray,_sphere=new Sphere,_sphereHitAt=new Vector3,_vA2=new Vector3,_vB2=new Vector3,_vC2=new Vector3,_tempA=new Vector3,_morphA=new Vector3,_intersectionPoint=new Vector3,_intersectionPointWorld=new Vector3,Mesh=class extends Object3D{constructor(geometry=new BufferGeometry,material=new MeshBasicMaterial){super(),this.isMesh=!0,this.type="Mesh",this.geometry=geometry,this.material=material,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.count=1,this.updateMorphTargets()}copy(source,recursive){return super.copy(source,recursive),source.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=source.morphTargetInfluences.slice()),source.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},source.morphTargetDictionary)),this.material=Array.isArray(source.material)?source.material.slice():source.material,this.geometry=source.geometry,this}updateMorphTargets(){let morphAttributes=this.geometry.morphAttributes,keys=Object.keys(morphAttributes);if(keys.length>0){let morphAttribute=morphAttributes[keys[0]];if(morphAttribute!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let m=0,ml=morphAttribute.length;m<ml;m++){let name=morphAttribute[m].name||String(m);this.morphTargetInfluences.push(0),this.morphTargetDictionary[name]=m}}}}getVertexPosition(index,target){let geometry=this.geometry,position=geometry.attributes.position,morphPosition=geometry.morphAttributes.position,morphTargetsRelative=geometry.morphTargetsRelative;target.fromBufferAttribute(position,index);let morphInfluences=this.morphTargetInfluences;if(morphPosition&&morphInfluences){_morphA.set(0,0,0);for(let i=0,il=morphPosition.length;i<il;i++){let influence=morphInfluences[i],morphAttribute=morphPosition[i];influence!==0&&(_tempA.fromBufferAttribute(morphAttribute,index),morphTargetsRelative?_morphA.addScaledVector(_tempA,influence):_morphA.addScaledVector(_tempA.sub(target),influence))}target.add(_morphA)}return target}intersectsFrustum(frustum){return frustum.intersectsObject(this)}raycast(raycaster,intersects2){let geometry=this.geometry,material=this.material,matrixWorld=this.matrixWorld;material!==void 0&&(geometry.boundingSphere===null&&geometry.computeBoundingSphere(),_sphere.copy(geometry.boundingSphere),_sphere.applyMatrix4(matrixWorld),_ray.copy(raycaster.ray).recast(raycaster.near),!(_sphere.containsPoint(_ray.origin)===!1&&(_ray.intersectSphere(_sphere,_sphereHitAt)===null||_ray.origin.distanceToSquared(_sphereHitAt)>(raycaster.far-raycaster.near)**2))&&(_inverseMatrix.copy(matrixWorld).invert(),_ray.copy(raycaster.ray).applyMatrix4(_inverseMatrix),!(geometry.boundingBox!==null&&_ray.intersectsBox(geometry.boundingBox)===!1)&&this._computeIntersections(raycaster,intersects2,_ray)))}_computeIntersections(raycaster,intersects2,rayLocalSpace){let intersection,geometry=this.geometry,material=this.material,index=geometry.index,position=geometry.attributes.position,uv=geometry.attributes.uv,uv1=geometry.attributes.uv1,normal=geometry.attributes.normal,groups=geometry.groups,drawRange=geometry.drawRange;if(index!==null)if(Array.isArray(material))for(let i=0,il=groups.length;i<il;i++){let group=groups[i],groupMaterial=material[group.materialIndex],start=Math.max(group.start,drawRange.start),end=Math.min(index.count,Math.min(group.start+group.count,drawRange.start+drawRange.count));for(let j=start,jl=end;j<jl;j+=3){let a=index.getX(j),b=index.getX(j+1),c=index.getX(j+2);intersection=checkGeometryIntersection(this,groupMaterial,raycaster,rayLocalSpace,uv,uv1,normal,a,b,c),intersection&&(intersection.faceIndex=Math.floor(j/3),intersection.face.materialIndex=group.materialIndex,intersects2.push(intersection))}}else{let start=Math.max(0,drawRange.start),end=Math.min(index.count,drawRange.start+drawRange.count);for(let i=start,il=end;i<il;i+=3){let a=index.getX(i),b=index.getX(i+1),c=index.getX(i+2);intersection=checkGeometryIntersection(this,material,raycaster,rayLocalSpace,uv,uv1,normal,a,b,c),intersection&&(intersection.faceIndex=Math.floor(i/3),intersects2.push(intersection))}}else if(position!==void 0)if(Array.isArray(material))for(let i=0,il=groups.length;i<il;i++){let group=groups[i],groupMaterial=material[group.materialIndex],start=Math.max(group.start,drawRange.start),end=Math.min(position.count,Math.min(group.start+group.count,drawRange.start+drawRange.count));for(let j=start,jl=end;j<jl;j+=3){let a=j,b=j+1,c=j+2;intersection=checkGeometryIntersection(this,groupMaterial,raycaster,rayLocalSpace,uv,uv1,normal,a,b,c),intersection&&(intersection.faceIndex=Math.floor(j/3),intersection.face.materialIndex=group.materialIndex,intersects2.push(intersection))}}else{let start=Math.max(0,drawRange.start),end=Math.min(position.count,drawRange.start+drawRange.count);for(let i=start,il=end;i<il;i+=3){let a=i,b=i+1,c=i+2;intersection=checkGeometryIntersection(this,material,raycaster,rayLocalSpace,uv,uv1,normal,a,b,c),intersection&&(intersection.faceIndex=Math.floor(i/3),intersects2.push(intersection))}}}};function checkIntersection(object,material,raycaster,ray,pA,pB,pC,point){let intersect2;if(material.side===BackSide?intersect2=ray.intersectTriangle(pC,pB,pA,!0,point):intersect2=ray.intersectTriangle(pA,pB,pC,material.side===FrontSide,point),intersect2===null)return null;_intersectionPointWorld.copy(point),_intersectionPointWorld.applyMatrix4(object.matrixWorld);let distance=raycaster.ray.origin.distanceTo(_intersectionPointWorld);return distance<raycaster.near||distance>raycaster.far?null:{distance,point:_intersectionPointWorld.clone(),object}}function checkGeometryIntersection(object,material,raycaster,ray,uv,uv1,normal,a,b,c){object.getVertexPosition(a,_vA2),object.getVertexPosition(b,_vB2),object.getVertexPosition(c,_vC2);let intersection=checkIntersection(object,material,raycaster,ray,_vA2,_vB2,_vC2,_intersectionPoint);if(intersection){let barycoord=new Vector3;Triangle.getBarycoord(_intersectionPoint,_vA2,_vB2,_vC2,barycoord),uv&&(intersection.uv=Triangle.getInterpolatedAttribute(uv,a,b,c,barycoord,new Vector2)),uv1&&(intersection.uv1=Triangle.getInterpolatedAttribute(uv1,a,b,c,barycoord,new Vector2)),normal&&(intersection.normal=Triangle.getInterpolatedAttribute(normal,a,b,c,barycoord,new Vector3),intersection.normal.dot(ray.direction)>0&&intersection.normal.multiplyScalar(-1));let face={a,b,c,normal:new Vector3,materialIndex:0};Triangle.getNormal(_vA2,_vB2,_vC2,face.normal),intersection.face=face,intersection.barycoord=barycoord}return intersection}var DataTexture=class extends Texture{constructor(data=null,width=1,height=1,format,type,mapping,wrapS,wrapT,magFilter=NearestFilter,minFilter=NearestFilter,anisotropy,colorSpace){super(null,mapping,wrapS,wrapT,magFilter,minFilter,format,type,anisotropy,colorSpace),this.isDataTexture=!0,this.image={data,width,height},this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}};var _sphere2=new Sphere,_defaultSpriteCenter=new Vector2(.5,.5),_vector7=new Vector3,Frustum=class{constructor(p0=new Plane,p1=new Plane,p2=new Plane,p3=new Plane,p4=new Plane,p5=new Plane){this.planes=[p0,p1,p2,p3,p4,p5]}set(p0,p1,p2,p3,p4,p5){let planes=this.planes;return planes[0].copy(p0),planes[1].copy(p1),planes[2].copy(p2),planes[3].copy(p3),planes[4].copy(p4),planes[5].copy(p5),this}copy(frustum){let planes=this.planes;for(let i=0;i<6;i++)planes[i].copy(frustum.planes[i]);return this}setFromProjectionMatrix(m,coordinateSystem=WebGLCoordinateSystem,reversedDepth=!1){let planes=this.planes,me=m.elements,me0=me[0],me1=me[1],me2=me[2],me3=me[3],me4=me[4],me5=me[5],me6=me[6],me7=me[7],me8=me[8],me9=me[9],me10=me[10],me11=me[11],me12=me[12],me13=me[13],me14=me[14],me15=me[15];if(planes[0].setComponents(me3-me0,me7-me4,me11-me8,me15-me12).normalize(),planes[1].setComponents(me3+me0,me7+me4,me11+me8,me15+me12).normalize(),planes[2].setComponents(me3+me1,me7+me5,me11+me9,me15+me13).normalize(),planes[3].setComponents(me3-me1,me7-me5,me11-me9,me15-me13).normalize(),reversedDepth)planes[4].setComponents(me2,me6,me10,me14).normalize(),planes[5].setComponents(me3-me2,me7-me6,me11-me10,me15-me14).normalize();else if(planes[4].setComponents(me3-me2,me7-me6,me11-me10,me15-me14).normalize(),coordinateSystem===WebGLCoordinateSystem)planes[5].setComponents(me3+me2,me7+me6,me11+me10,me15+me14).normalize();else if(coordinateSystem===WebGPUCoordinateSystem)planes[5].setComponents(me2,me6,me10,me14).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+coordinateSystem);return this}intersectsObject(object){if(object.boundingSphere!==void 0)object.boundingSphere===null&&object.computeBoundingSphere(),_sphere2.copy(object.boundingSphere).applyMatrix4(object.matrixWorld);else{let geometry=object.geometry;geometry.boundingSphere===null&&geometry.computeBoundingSphere(),_sphere2.copy(geometry.boundingSphere).applyMatrix4(object.matrixWorld)}return this.intersectsSphere(_sphere2)}intersectsSprite(sprite){_sphere2.center.set(0,0,0);let offset=_defaultSpriteCenter.distanceTo(sprite.center);return _sphere2.radius=.7071067811865476+offset,_sphere2.applyMatrix4(sprite.matrixWorld),this.intersectsSphere(_sphere2)}intersectsSphere(sphere){let planes=this.planes,center=sphere.center,negRadius=-sphere.radius;for(let i=0;i<6;i++)if(planes[i].distanceToPoint(center)<negRadius)return!1;return!0}intersectsBox(box){let planes=this.planes;for(let i=0;i<6;i++){let plane=planes[i];if(_vector7.x=plane.normal.x>0?box.max.x:box.min.x,_vector7.y=plane.normal.y>0?box.max.y:box.min.y,_vector7.z=plane.normal.z>0?box.max.z:box.min.z,plane.distanceToPoint(_vector7)<0)return!1}return!0}containsPoint(point){let planes=this.planes;for(let i=0;i<6;i++)if(planes[i].distanceToPoint(point)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}};var LineBasicMaterial=class extends Material{constructor(parameters){super(),this.isLineBasicMaterial=!0,this.type="LineBasicMaterial",this.color=new Color(16777215),this.map=null,this.linewidth=1,this.linecap="round",this.linejoin="round",this.fog=!0,this.setValues(parameters)}copy(source){return super.copy(source),this.color.copy(source.color),this.map=source.map,this.linewidth=source.linewidth,this.linecap=source.linecap,this.linejoin=source.linejoin,this.fog=source.fog,this}};var _vStart=new Vector3,_vEnd=new Vector3,_inverseMatrix2=new Matrix4,_ray2=new Ray,_sphere3=new Sphere,_intersectPointOnRay=new Vector3,_intersectPointOnSegment=new Vector3,Line=class extends Object3D{constructor(geometry=new BufferGeometry,material=new LineBasicMaterial){super(),this.isLine=!0,this.type="Line",this.geometry=geometry,this.material=material,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.updateMorphTargets()}copy(source,recursive){return super.copy(source,recursive),this.material=Array.isArray(source.material)?source.material.slice():source.material,this.geometry=source.geometry,this}computeLineDistances(){let geometry=this.geometry;if(geometry.index===null){let positionAttribute=geometry.attributes.position,lineDistances=[0];for(let i=1,l=positionAttribute.count;i<l;i++)_vStart.fromBufferAttribute(positionAttribute,i-1),_vEnd.fromBufferAttribute(positionAttribute,i),lineDistances[i]=lineDistances[i-1],lineDistances[i]+=_vStart.distanceTo(_vEnd);geometry.setAttribute("lineDistance",new Float32BufferAttribute(lineDistances,1))}else warn("Line.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}intersectsFrustum(frustum){return frustum.intersectsObject(this)}raycast(raycaster,intersects2){let geometry=this.geometry,matrixWorld=this.matrixWorld,threshold=raycaster.params.Line.threshold,drawRange=geometry.drawRange;if(geometry.boundingSphere===null&&geometry.computeBoundingSphere(),_sphere3.copy(geometry.boundingSphere),_sphere3.applyMatrix4(matrixWorld),_sphere3.radius+=threshold,raycaster.ray.intersectsSphere(_sphere3)===!1)return;_inverseMatrix2.copy(matrixWorld).invert(),_ray2.copy(raycaster.ray).applyMatrix4(_inverseMatrix2);let localThreshold=threshold/((this.scale.x+this.scale.y+this.scale.z)/3),localThresholdSq=localThreshold*localThreshold,step=this.isLineSegments?2:1,index=geometry.index,positionAttribute=geometry.attributes.position;if(index!==null){let start=Math.max(0,drawRange.start),end=Math.min(index.count,drawRange.start+drawRange.count);for(let i=start,l=end-1;i<l;i+=step){let a=index.getX(i),b=index.getX(i+1),intersect2=checkIntersection2(this,raycaster,_ray2,localThresholdSq,a,b,i);intersect2&&intersects2.push(intersect2)}if(this.isLineLoop){let a=index.getX(end-1),b=index.getX(start),intersect2=checkIntersection2(this,raycaster,_ray2,localThresholdSq,a,b,end-1);intersect2&&intersects2.push(intersect2)}}else{let start=Math.max(0,drawRange.start),end=Math.min(positionAttribute.count,drawRange.start+drawRange.count);for(let i=start,l=end-1;i<l;i+=step){let intersect2=checkIntersection2(this,raycaster,_ray2,localThresholdSq,i,i+1,i);intersect2&&intersects2.push(intersect2)}if(this.isLineLoop){let intersect2=checkIntersection2(this,raycaster,_ray2,localThresholdSq,end-1,start,end-1);intersect2&&intersects2.push(intersect2)}}}updateMorphTargets(){let morphAttributes=this.geometry.morphAttributes,keys=Object.keys(morphAttributes);if(keys.length>0){let morphAttribute=morphAttributes[keys[0]];if(morphAttribute!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let m=0,ml=morphAttribute.length;m<ml;m++){let name=morphAttribute[m].name||String(m);this.morphTargetInfluences.push(0),this.morphTargetDictionary[name]=m}}}}};function checkIntersection2(object,raycaster,ray,thresholdSq,a,b,i){let positionAttribute=object.geometry.attributes.position;if(_vStart.fromBufferAttribute(positionAttribute,a),_vEnd.fromBufferAttribute(positionAttribute,b),ray.distanceSqToSegment(_vStart,_vEnd,_intersectPointOnRay,_intersectPointOnSegment)>thresholdSq)return;_intersectPointOnRay.applyMatrix4(object.matrixWorld);let distance=raycaster.ray.origin.distanceTo(_intersectPointOnRay);if(!(distance<raycaster.near||distance>raycaster.far))return{distance,point:_intersectPointOnSegment.clone().applyMatrix4(object.matrixWorld),index:i,face:null,faceIndex:null,barycoord:null,object}}var _start=new Vector3,_end=new Vector3,LineSegments=class extends Line{constructor(geometry,material){super(geometry,material),this.isLineSegments=!0,this.type="LineSegments"}computeLineDistances(){let geometry=this.geometry;if(geometry.index===null){let positionAttribute=geometry.attributes.position,lineDistances=[];for(let i=0,l=positionAttribute.count;i<l;i+=2)_start.fromBufferAttribute(positionAttribute,i),_end.fromBufferAttribute(positionAttribute,i+1),lineDistances[i]=i===0?0:lineDistances[i-1],lineDistances[i+1]=lineDistances[i]+_start.distanceTo(_end);geometry.setAttribute("lineDistance",new Float32BufferAttribute(lineDistances,1))}else warn("LineSegments.computeLineDistances(): Computation only possible with non-indexed BufferGeometry.");return this}};var CubeTexture=class extends Texture{constructor(images=[],mapping=CubeReflectionMapping,wrapS,wrapT,magFilter,minFilter,format,type,anisotropy,colorSpace){super(images,mapping,wrapS,wrapT,magFilter,minFilter,format,type,anisotropy,colorSpace),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(value){this.image=value}};var CanvasTexture=class extends Texture{constructor(canvas,mapping,wrapS,wrapT,magFilter,minFilter,format,type,anisotropy){super(canvas,mapping,wrapS,wrapT,magFilter,minFilter,format,type,anisotropy),this.isCanvasTexture=!0,this.needsUpdate=!0}};var DepthTexture=class extends Texture{constructor(width,height,type=UnsignedIntType,mapping,wrapS,wrapT,magFilter=NearestFilter,minFilter=NearestFilter,anisotropy,format=DepthFormat,depth=1){if(format!==DepthFormat&&format!==DepthStencilFormat)throw new Error("THREE.DepthTexture: format must be either THREE.DepthFormat or THREE.DepthStencilFormat");let image={width,height,depth};super(image,mapping,wrapS,wrapT,magFilter,minFilter,format,type,anisotropy),this.isDepthTexture=!0,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(source){return super.copy(source),this.source=new TextureSource(Object.assign({},source.image)),this.compareFunction=source.compareFunction,this}toJSON(meta){let data=super.toJSON(meta);return data.compareFunction=this.compareFunction,data}};var CubeDepthTexture=class extends DepthTexture{constructor(size,type=UnsignedIntType,mapping=CubeReflectionMapping,wrapS,wrapT,magFilter=NearestFilter,minFilter=NearestFilter,anisotropy,format=DepthFormat){let image={width:size,height:size,depth:1},images=[image,image,image,image,image,image];super(size,size,type,mapping,wrapS,wrapT,magFilter,minFilter,anisotropy,format),this.image=images,this.isCubeDepthTexture=!0,this.isCubeTexture=!0}get images(){return this.image}set images(value){this.image=value}};var ExternalTexture=class extends Texture{constructor(sourceTexture=null){super(),this.sourceTexture=sourceTexture,this.isExternalTexture=!0}copy(source){return super.copy(source),this.sourceTexture=source.sourceTexture,this}};var BoxGeometry=class _BoxGeometry extends BufferGeometry{constructor(width=1,height=1,depth=1,widthSegments=1,heightSegments=1,depthSegments=1){super(),this.type="BoxGeometry",this.parameters={width,height,depth,widthSegments,heightSegments,depthSegments};let scope=this;widthSegments=Math.floor(widthSegments),heightSegments=Math.floor(heightSegments),depthSegments=Math.floor(depthSegments);let indices=[],vertices=[],normals=[],uvs=[],numberOfVertices=0,groupStart=0;buildPlane("z","y","x",-1,-1,depth,height,width,depthSegments,heightSegments,0),buildPlane("z","y","x",1,-1,depth,height,-width,depthSegments,heightSegments,1),buildPlane("x","z","y",1,1,width,depth,height,widthSegments,depthSegments,2),buildPlane("x","z","y",1,-1,width,depth,-height,widthSegments,depthSegments,3),buildPlane("x","y","z",1,-1,width,height,depth,widthSegments,heightSegments,4),buildPlane("x","y","z",-1,-1,width,height,-depth,widthSegments,heightSegments,5),this.setIndex(indices),this.setAttribute("position",new Float32BufferAttribute(vertices,3)),this.setAttribute("normal",new Float32BufferAttribute(normals,3)),this.setAttribute("uv",new Float32BufferAttribute(uvs,2));function buildPlane(u,v,w,udir,vdir,width2,height2,depth2,gridX,gridY,materialIndex){let segmentWidth=width2/gridX,segmentHeight=height2/gridY,widthHalf=width2/2,heightHalf=height2/2,depthHalf=depth2/2,gridX1=gridX+1,gridY1=gridY+1,vertexCounter=0,groupCount=0,vector=new Vector3;for(let iy=0;iy<gridY1;iy++){let y=iy*segmentHeight-heightHalf;for(let ix=0;ix<gridX1;ix++){let x=ix*segmentWidth-widthHalf;vector[u]=x*udir,vector[v]=y*vdir,vector[w]=depthHalf,vertices.push(vector.x,vector.y,vector.z),vector[u]=0,vector[v]=0,vector[w]=depth2>0?1:-1,normals.push(vector.x,vector.y,vector.z),uvs.push(ix/gridX),uvs.push(1-iy/gridY),vertexCounter+=1}}for(let iy=0;iy<gridY;iy++)for(let ix=0;ix<gridX;ix++){let a=numberOfVertices+ix+gridX1*iy,b=numberOfVertices+ix+gridX1*(iy+1),c=numberOfVertices+(ix+1)+gridX1*(iy+1),d=numberOfVertices+(ix+1)+gridX1*iy;indices.push(a,b,d),indices.push(b,c,d),groupCount+=6}scope.addGroup(groupStart,groupCount,materialIndex),groupStart+=groupCount,numberOfVertices+=vertexCounter}}copy(source){return super.copy(source),this.parameters=Object.assign({},source.parameters),this}static fromJSON(data){return new _BoxGeometry(data.width,data.height,data.depth,data.widthSegments,data.heightSegments,data.depthSegments)}};var CircleGeometry=class _CircleGeometry extends BufferGeometry{constructor(radius=1,segments=32,thetaStart=0,thetaLength=Math.PI*2){super(),this.type="CircleGeometry",this.parameters={radius,segments,thetaStart,thetaLength},segments=Math.max(3,segments);let indices=[],vertices=[],normals=[],uvs=[],vertex19=new Vector3,uv=new Vector2;vertices.push(0,0,0),normals.push(0,0,1),uvs.push(.5,.5);for(let s=0,i=3;s<=segments;s++,i+=3){let segment=thetaStart+s/segments*thetaLength;vertex19.x=radius*Math.cos(segment),vertex19.y=radius*Math.sin(segment),vertices.push(vertex19.x,vertex19.y,vertex19.z),normals.push(0,0,1),uv.x=(vertices[i]/radius+1)/2,uv.y=(vertices[i+1]/radius+1)/2,uvs.push(uv.x,uv.y)}for(let i=1;i<=segments;i++)indices.push(i,i+1,0);this.setIndex(indices),this.setAttribute("position",new Float32BufferAttribute(vertices,3)),this.setAttribute("normal",new Float32BufferAttribute(normals,3)),this.setAttribute("uv",new Float32BufferAttribute(uvs,2))}copy(source){return super.copy(source),this.parameters=Object.assign({},source.parameters),this}static fromJSON(data){return new _CircleGeometry(data.radius,data.segments,data.thetaStart,data.thetaLength)}};var CylinderGeometry=class _CylinderGeometry extends BufferGeometry{constructor(radiusTop=1,radiusBottom=1,height=1,radialSegments=32,heightSegments=1,openEnded=!1,thetaStart=0,thetaLength=Math.PI*2){super(),this.type="CylinderGeometry",this.parameters={radiusTop,radiusBottom,height,radialSegments,heightSegments,openEnded,thetaStart,thetaLength};let scope=this;radialSegments=Math.floor(radialSegments),heightSegments=Math.floor(heightSegments);let indices=[],vertices=[],normals=[],uvs=[],index=0,indexArray=[],halfHeight=height/2,groupStart=0;generateTorso(),openEnded===!1&&(radiusTop>0&&generateCap(!0),radiusBottom>0&&generateCap(!1)),this.setIndex(indices),this.setAttribute("position",new Float32BufferAttribute(vertices,3)),this.setAttribute("normal",new Float32BufferAttribute(normals,3)),this.setAttribute("uv",new Float32BufferAttribute(uvs,2));function generateTorso(){let normal=new Vector3,vertex19=new Vector3,groupCount=0,slope=(radiusBottom-radiusTop)/height;for(let y=0;y<=heightSegments;y++){let indexRow=[],v=y/heightSegments,radius=v*(radiusBottom-radiusTop)+radiusTop;for(let x=0;x<=radialSegments;x++){let u=x/radialSegments,theta=u*thetaLength+thetaStart,sinTheta=Math.sin(theta),cosTheta=Math.cos(theta);vertex19.x=radius*sinTheta,vertex19.y=-v*height+halfHeight,vertex19.z=radius*cosTheta,vertices.push(vertex19.x,vertex19.y,vertex19.z),normal.set(sinTheta,slope,cosTheta).normalize(),normals.push(normal.x,normal.y,normal.z),uvs.push(u,1-v),indexRow.push(index++)}indexArray.push(indexRow)}for(let x=0;x<radialSegments;x++)for(let y=0;y<heightSegments;y++){let a=indexArray[y][x],b=indexArray[y+1][x],c=indexArray[y+1][x+1],d=indexArray[y][x+1];(radiusTop>0||y!==0)&&(indices.push(a,b,d),groupCount+=3),(radiusBottom>0||y!==heightSegments-1)&&(indices.push(b,c,d),groupCount+=3)}scope.addGroup(groupStart,groupCount,0),groupStart+=groupCount}function generateCap(top){let centerIndexStart=index,uv=new Vector2,vertex19=new Vector3,groupCount=0,radius=top===!0?radiusTop:radiusBottom,sign2=top===!0?1:-1;for(let x=1;x<=radialSegments;x++)vertices.push(0,halfHeight*sign2,0),normals.push(0,sign2,0),uvs.push(.5,.5),index++;let centerIndexEnd=index;for(let x=0;x<=radialSegments;x++){let theta=x/radialSegments*thetaLength+thetaStart,cosTheta=Math.cos(theta),sinTheta=Math.sin(theta);vertex19.x=radius*sinTheta,vertex19.y=halfHeight*sign2,vertex19.z=radius*cosTheta,vertices.push(vertex19.x,vertex19.y,vertex19.z),normals.push(0,sign2,0),uv.x=cosTheta*.5+.5,uv.y=sinTheta*.5*sign2+.5,uvs.push(uv.x,uv.y),index++}for(let x=0;x<radialSegments;x++){let c=centerIndexStart+x,i=centerIndexEnd+x;top===!0?indices.push(i,i+1,c):indices.push(i+1,i,c),groupCount+=3}scope.addGroup(groupStart,groupCount,top===!0?1:2),groupStart+=groupCount}}copy(source){return super.copy(source),this.parameters=Object.assign({},source.parameters),this}static fromJSON(data){return new _CylinderGeometry(data.radiusTop,data.radiusBottom,data.height,data.radialSegments,data.heightSegments,data.openEnded,data.thetaStart,data.thetaLength)}};var ConeGeometry=class _ConeGeometry extends CylinderGeometry{constructor(radius=1,height=1,radialSegments=32,heightSegments=1,openEnded=!1,thetaStart=0,thetaLength=Math.PI*2){super(0,radius,height,radialSegments,heightSegments,openEnded,thetaStart,thetaLength),this.type="ConeGeometry",this.parameters={radius,height,radialSegments,heightSegments,openEnded,thetaStart,thetaLength}}static fromJSON(data){return new _ConeGeometry(data.radius,data.height,data.radialSegments,data.heightSegments,data.openEnded,data.thetaStart,data.thetaLength)}};var PolyhedronGeometry=class _PolyhedronGeometry extends BufferGeometry{constructor(vertices=[],indices=[],radius=1,detail=0){super(),this.type="PolyhedronGeometry",this.parameters={vertices,indices,radius,detail};let vertexBuffer=[],uvBuffer=[];subdivide(detail),applyRadius(radius),generateUVs(),this.setAttribute("position",new Float32BufferAttribute(vertexBuffer,3)),this.setAttribute("normal",new Float32BufferAttribute(vertexBuffer.slice(),3)),this.setAttribute("uv",new Float32BufferAttribute(uvBuffer,2)),detail===0?this.computeVertexNormals():this.normalizeNormals();function subdivide(detail2){let a=new Vector3,b=new Vector3,c=new Vector3;for(let i=0;i<indices.length;i+=3)getVertexByIndex(indices[i+0],a),getVertexByIndex(indices[i+1],b),getVertexByIndex(indices[i+2],c),subdivideFace(a,b,c,detail2)}function subdivideFace(a,b,c,detail2){let cols=detail2+1,v=[];for(let i=0;i<=cols;i++){v[i]=[];let aj=a.clone().lerp(c,i/cols),bj=b.clone().lerp(c,i/cols),rows=cols-i;for(let j=0;j<=rows;j++)j===0&&i===cols?v[i][j]=aj:v[i][j]=aj.clone().lerp(bj,j/rows)}for(let i=0;i<cols;i++)for(let j=0;j<2*(cols-i)-1;j++){let k=Math.floor(j/2);j%2===0?(pushVertex(v[i][k+1]),pushVertex(v[i+1][k]),pushVertex(v[i][k])):(pushVertex(v[i][k+1]),pushVertex(v[i+1][k+1]),pushVertex(v[i+1][k]))}}function applyRadius(radius2){let vertex19=new Vector3;for(let i=0;i<vertexBuffer.length;i+=3)vertex19.x=vertexBuffer[i+0],vertex19.y=vertexBuffer[i+1],vertex19.z=vertexBuffer[i+2],vertex19.normalize().multiplyScalar(radius2),vertexBuffer[i+0]=vertex19.x,vertexBuffer[i+1]=vertex19.y,vertexBuffer[i+2]=vertex19.z}function generateUVs(){let vertex19=new Vector3;for(let i=0;i<vertexBuffer.length;i+=3){vertex19.x=vertexBuffer[i+0],vertex19.y=vertexBuffer[i+1],vertex19.z=vertexBuffer[i+2];let u=azimuth(vertex19)/2/Math.PI+.5,v=inclination(vertex19)/Math.PI+.5;uvBuffer.push(u,1-v)}correctUVs(),correctSeam()}function correctSeam(){for(let i=0;i<uvBuffer.length;i+=6){let x0=uvBuffer[i+0],x1=uvBuffer[i+2],x2=uvBuffer[i+4],max=Math.max(x0,x1,x2),min=Math.min(x0,x1,x2);max>.9&&min<.1&&(x0<.2&&(uvBuffer[i+0]+=1),x1<.2&&(uvBuffer[i+2]+=1),x2<.2&&(uvBuffer[i+4]+=1))}}function pushVertex(vertex19){vertexBuffer.push(vertex19.x,vertex19.y,vertex19.z)}function getVertexByIndex(index,vertex19){let stride=index*3;vertex19.x=vertices[stride+0],vertex19.y=vertices[stride+1],vertex19.z=vertices[stride+2]}function correctUVs(){let a=new Vector3,b=new Vector3,c=new Vector3,centroid=new Vector3,uvA=new Vector2,uvB=new Vector2,uvC=new Vector2;for(let i=0,j=0;i<vertexBuffer.length;i+=9,j+=6){a.set(vertexBuffer[i+0],vertexBuffer[i+1],vertexBuffer[i+2]),b.set(vertexBuffer[i+3],vertexBuffer[i+4],vertexBuffer[i+5]),c.set(vertexBuffer[i+6],vertexBuffer[i+7],vertexBuffer[i+8]),uvA.set(uvBuffer[j+0],uvBuffer[j+1]),uvB.set(uvBuffer[j+2],uvBuffer[j+3]),uvC.set(uvBuffer[j+4],uvBuffer[j+5]),centroid.copy(a).add(b).add(c).divideScalar(3);let azi=azimuth(centroid);correctUV(uvA,j+0,a,azi),correctUV(uvB,j+2,b,azi),correctUV(uvC,j+4,c,azi)}}function correctUV(uv,stride,vector,azimuth2){azimuth2<0&&uv.x===1&&(uvBuffer[stride]=uv.x-1),vector.x===0&&vector.z===0&&(uvBuffer[stride]=azimuth2/2/Math.PI+.5)}function azimuth(vector){return Math.atan2(vector.z,-vector.x)}function inclination(vector){return Math.atan2(-vector.y,Math.sqrt(vector.x*vector.x+vector.z*vector.z))}}copy(source){return super.copy(source),this.parameters=Object.assign({},source.parameters),this}static fromJSON(data){return new _PolyhedronGeometry(data.vertices,data.indices,data.radius,data.detail)}};var Curves_exports={};__export(Curves_exports,{ArcCurve:()=>ArcCurve,CatmullRomCurve3:()=>CatmullRomCurve3,CubicBezierCurve:()=>CubicBezierCurve,CubicBezierCurve3:()=>CubicBezierCurve3,EllipseCurve:()=>EllipseCurve,LineCurve:()=>LineCurve,LineCurve3:()=>LineCurve3,QuadraticBezierCurve:()=>QuadraticBezierCurve,QuadraticBezierCurve3:()=>QuadraticBezierCurve3,SplineCurve:()=>SplineCurve});var Curve=class{constructor(){this.type="Curve",this.arcLengthDivisions=200,this.needsUpdate=!1,this.cacheArcLengths=null}getPoint(){warn("Curve: .getPoint() not implemented.")}getPointAt(u,optionalTarget){let t=this.getUtoTmapping(u);return this.getPoint(t,optionalTarget)}getPoints(divisions=5){let points=[];for(let d=0;d<=divisions;d++)points.push(this.getPoint(d/divisions));return points}getSpacedPoints(divisions=5){let points=[];for(let d=0;d<=divisions;d++)points.push(this.getPointAt(d/divisions));return points}getLength(){let lengths=this.getLengths();return lengths[lengths.length-1]}getLengths(divisions=this.arcLengthDivisions){if(this.cacheArcLengths&&this.cacheArcLengths.length===divisions+1&&!this.needsUpdate)return this.cacheArcLengths;this.needsUpdate=!1;let cache=[],current,last=this.getPoint(0),sum=0;cache.push(0);for(let p=1;p<=divisions;p++)current=this.getPoint(p/divisions),sum+=current.distanceTo(last),cache.push(sum),last=current;return this.cacheArcLengths=cache,cache}updateArcLengths(){this.needsUpdate=!0,this.getLengths()}getUtoTmapping(u,distance=null){let arcLengths=this.getLengths(),i=0,il=arcLengths.length,targetArcLength;distance?targetArcLength=distance:targetArcLength=u*arcLengths[il-1];let low=0,high=il-1,comparison;for(;low<=high;)if(i=Math.floor(low+(high-low)/2),comparison=arcLengths[i]-targetArcLength,comparison<0)low=i+1;else if(comparison>0)high=i-1;else{high=i;break}if(i=high,arcLengths[i]===targetArcLength)return i/(il-1);let lengthBefore=arcLengths[i],segmentLength=arcLengths[i+1]-lengthBefore,segmentFraction=(targetArcLength-lengthBefore)/segmentLength;return(i+segmentFraction)/(il-1)}getTangent(t,optionalTarget){let t1=t-1e-4,t2=t+1e-4;t1<0&&(t1=0),t2>1&&(t2=1);let pt1=this.getPoint(t1),pt2=this.getPoint(t2),tangent=optionalTarget||(pt1.isVector2?new Vector2:new Vector3);return tangent.copy(pt2).sub(pt1).normalize(),tangent}getTangentAt(u,optionalTarget){let t=this.getUtoTmapping(u);return this.getTangent(t,optionalTarget)}computeFrenetFrames(segments,closed=!1){let normal=new Vector3,tangents=[],normals=[],binormals=[],vec=new Vector3,mat=new Matrix4;for(let i=0;i<=segments;i++){let u=i/segments;tangents[i]=this.getTangentAt(u,new Vector3)}normals[0]=new Vector3,binormals[0]=new Vector3;let min=Number.MAX_VALUE,tx=Math.abs(tangents[0].x),ty=Math.abs(tangents[0].y),tz=Math.abs(tangents[0].z);tx<=min&&(min=tx,normal.set(1,0,0)),ty<=min&&(min=ty,normal.set(0,1,0)),tz<=min&&normal.set(0,0,1),vec.crossVectors(tangents[0],normal).normalize(),normals[0].crossVectors(tangents[0],vec),binormals[0].crossVectors(tangents[0],normals[0]);for(let i=1;i<=segments;i++){if(normals[i]=normals[i-1].clone(),binormals[i]=binormals[i-1].clone(),vec.crossVectors(tangents[i-1],tangents[i]),vec.length()>Number.EPSILON){vec.normalize();let theta=Math.acos(clamp(tangents[i-1].dot(tangents[i]),-1,1));normals[i].applyMatrix4(mat.makeRotationAxis(vec,theta))}binormals[i].crossVectors(tangents[i],normals[i])}if(closed===!0){let theta=Math.acos(clamp(normals[0].dot(normals[segments]),-1,1));theta/=segments,tangents[0].dot(vec.crossVectors(normals[0],normals[segments]))>0&&(theta=-theta);for(let i=1;i<=segments;i++)normals[i].applyMatrix4(mat.makeRotationAxis(tangents[i],theta*i)),binormals[i].crossVectors(tangents[i],normals[i])}return{tangents,normals,binormals}}clone(){return new this.constructor().copy(this)}copy(source){return this.arcLengthDivisions=source.arcLengthDivisions,this}toJSON(){let data={metadata:{version:4.7,type:"Curve",generator:"Curve.toJSON"}};return data.arcLengthDivisions=this.arcLengthDivisions,data.type=this.type,data}fromJSON(json){return this.arcLengthDivisions=json.arcLengthDivisions,this}};var EllipseCurve=class extends Curve{constructor(aX=0,aY=0,xRadius=1,yRadius=1,aStartAngle=0,aEndAngle=Math.PI*2,aClockwise=!1,aRotation=0){super(),this.isEllipseCurve=!0,this.type="EllipseCurve",this.aX=aX,this.aY=aY,this.xRadius=xRadius,this.yRadius=yRadius,this.aStartAngle=aStartAngle,this.aEndAngle=aEndAngle,this.aClockwise=aClockwise,this.aRotation=aRotation}getPoint(t,optionalTarget=new Vector2){let point=optionalTarget,twoPi=Math.PI*2,deltaAngle=this.aEndAngle-this.aStartAngle,samePoints=Math.abs(deltaAngle)<Number.EPSILON;for(;deltaAngle<0;)deltaAngle+=twoPi;for(;deltaAngle>twoPi;)deltaAngle-=twoPi;deltaAngle<Number.EPSILON&&(samePoints?deltaAngle=0:deltaAngle=twoPi),this.aClockwise===!0&&!samePoints&&(deltaAngle===twoPi?deltaAngle=-twoPi:deltaAngle=deltaAngle-twoPi);let angle=this.aStartAngle+t*deltaAngle,x=this.aX+this.xRadius*Math.cos(angle),y=this.aY+this.yRadius*Math.sin(angle);if(this.aRotation!==0){let cos=Math.cos(this.aRotation),sin=Math.sin(this.aRotation),tx=x-this.aX,ty=y-this.aY;x=tx*cos-ty*sin+this.aX,y=tx*sin+ty*cos+this.aY}return point.set(x,y)}copy(source){return super.copy(source),this.aX=source.aX,this.aY=source.aY,this.xRadius=source.xRadius,this.yRadius=source.yRadius,this.aStartAngle=source.aStartAngle,this.aEndAngle=source.aEndAngle,this.aClockwise=source.aClockwise,this.aRotation=source.aRotation,this}toJSON(){let data=super.toJSON();return data.aX=this.aX,data.aY=this.aY,data.xRadius=this.xRadius,data.yRadius=this.yRadius,data.aStartAngle=this.aStartAngle,data.aEndAngle=this.aEndAngle,data.aClockwise=this.aClockwise,data.aRotation=this.aRotation,data}fromJSON(json){return super.fromJSON(json),this.aX=json.aX,this.aY=json.aY,this.xRadius=json.xRadius,this.yRadius=json.yRadius,this.aStartAngle=json.aStartAngle,this.aEndAngle=json.aEndAngle,this.aClockwise=json.aClockwise,this.aRotation=json.aRotation,this}};var ArcCurve=class extends EllipseCurve{constructor(aX,aY,aRadius,aStartAngle,aEndAngle,aClockwise){super(aX,aY,aRadius,aRadius,aStartAngle,aEndAngle,aClockwise),this.isArcCurve=!0,this.type="ArcCurve"}};function CubicPoly(){let c0=0,c1=0,c2=0,c3=0;function init(x0,x1,t0,t1){c0=x0,c1=t0,c2=-3*x0+3*x1-2*t0-t1,c3=2*x0-2*x1+t0+t1}return{initCatmullRom:function(x0,x1,x2,x3,tension){init(x1,x2,tension*(x2-x0),tension*(x3-x1))},initNonuniformCatmullRom:function(x0,x1,x2,x3,dt0,dt1,dt2){let t1=(x1-x0)/dt0-(x2-x0)/(dt0+dt1)+(x2-x1)/dt1,t2=(x2-x1)/dt1-(x3-x1)/(dt1+dt2)+(x3-x2)/dt2;t1*=dt1,t2*=dt1,init(x1,x2,t1,t2)},calc:function(t){let t2=t*t,t3=t2*t;return c0+c1*t+c2*t2+c3*t3}}}var tmp=new Vector3,tmp2=new Vector3,px=new CubicPoly,py=new CubicPoly,pz=new CubicPoly,CatmullRomCurve3=class extends Curve{constructor(points=[],closed=!1,curveType="centripetal",tension=.5){super(),this.isCatmullRomCurve3=!0,this.type="CatmullRomCurve3",this.points=points,this.closed=closed,this.curveType=curveType,this.tension=tension}getPoint(t,optionalTarget=new Vector3){let point=optionalTarget,points=this.points,l=points.length,p=(l-(this.closed?0:1))*t,intPoint=Math.floor(p),weight=p-intPoint;this.closed?intPoint+=intPoint>0?0:(Math.floor(Math.abs(intPoint)/l)+1)*l:weight===0&&intPoint===l-1&&(intPoint=l-2,weight=1);let p0,p3;this.closed||intPoint>0?p0=points[(intPoint-1)%l]:(tmp2.subVectors(points[0],points[1]).add(points[0]),p0=tmp2);let p1=points[intPoint%l],p2=points[(intPoint+1)%l];if(this.closed||intPoint+2<l?p3=points[(intPoint+2)%l]:(tmp.subVectors(points[l-1],points[l-2]).add(points[l-1]),p3=tmp),this.curveType==="centripetal"||this.curveType==="chordal"){let pow=this.curveType==="chordal"?.5:.25,dt0=Math.pow(p0.distanceToSquared(p1),pow),dt1=Math.pow(p1.distanceToSquared(p2),pow),dt2=Math.pow(p2.distanceToSquared(p3),pow);dt1<1e-4&&(dt1=1),dt0<1e-4&&(dt0=dt1),dt2<1e-4&&(dt2=dt1),px.initNonuniformCatmullRom(p0.x,p1.x,p2.x,p3.x,dt0,dt1,dt2),py.initNonuniformCatmullRom(p0.y,p1.y,p2.y,p3.y,dt0,dt1,dt2),pz.initNonuniformCatmullRom(p0.z,p1.z,p2.z,p3.z,dt0,dt1,dt2)}else this.curveType==="catmullrom"&&(px.initCatmullRom(p0.x,p1.x,p2.x,p3.x,this.tension),py.initCatmullRom(p0.y,p1.y,p2.y,p3.y,this.tension),pz.initCatmullRom(p0.z,p1.z,p2.z,p3.z,this.tension));return point.set(px.calc(weight),py.calc(weight),pz.calc(weight)),point}copy(source){super.copy(source),this.points=[];for(let i=0,l=source.points.length;i<l;i++){let point=source.points[i];this.points.push(point.clone())}return this.closed=source.closed,this.curveType=source.curveType,this.tension=source.tension,this}toJSON(){let data=super.toJSON();data.points=[];for(let i=0,l=this.points.length;i<l;i++){let point=this.points[i];data.points.push(point.toArray())}return data.closed=this.closed,data.curveType=this.curveType,data.tension=this.tension,data}fromJSON(json){super.fromJSON(json),this.points=[];for(let i=0,l=json.points.length;i<l;i++){let point=json.points[i];this.points.push(new Vector3().fromArray(point))}return this.closed=json.closed,this.curveType=json.curveType,this.tension=json.tension,this}};function CatmullRom(t,p0,p1,p2,p3){let v0=(p2-p0)*.5,v1=(p3-p1)*.5,t2=t*t,t3=t*t2;return(2*p1-2*p2+v0+v1)*t3+(-3*p1+3*p2-2*v0-v1)*t2+v0*t+p1}function QuadraticBezierP0(t,p){let k=1-t;return k*k*p}function QuadraticBezierP1(t,p){return 2*(1-t)*t*p}function QuadraticBezierP2(t,p){return t*t*p}function QuadraticBezier(t,p0,p1,p2){return QuadraticBezierP0(t,p0)+QuadraticBezierP1(t,p1)+QuadraticBezierP2(t,p2)}function CubicBezierP0(t,p){let k=1-t;return k*k*k*p}function CubicBezierP1(t,p){let k=1-t;return 3*k*k*t*p}function CubicBezierP2(t,p){return 3*(1-t)*t*t*p}function CubicBezierP3(t,p){return t*t*t*p}function CubicBezier(t,p0,p1,p2,p3){return CubicBezierP0(t,p0)+CubicBezierP1(t,p1)+CubicBezierP2(t,p2)+CubicBezierP3(t,p3)}var CubicBezierCurve=class extends Curve{constructor(v0=new Vector2,v1=new Vector2,v2=new Vector2,v3=new Vector2){super(),this.isCubicBezierCurve=!0,this.type="CubicBezierCurve",this.v0=v0,this.v1=v1,this.v2=v2,this.v3=v3}getPoint(t,optionalTarget=new Vector2){let point=optionalTarget,v0=this.v0,v1=this.v1,v2=this.v2,v3=this.v3;return point.set(CubicBezier(t,v0.x,v1.x,v2.x,v3.x),CubicBezier(t,v0.y,v1.y,v2.y,v3.y)),point}copy(source){return super.copy(source),this.v0.copy(source.v0),this.v1.copy(source.v1),this.v2.copy(source.v2),this.v3.copy(source.v3),this}toJSON(){let data=super.toJSON();return data.v0=this.v0.toArray(),data.v1=this.v1.toArray(),data.v2=this.v2.toArray(),data.v3=this.v3.toArray(),data}fromJSON(json){return super.fromJSON(json),this.v0.fromArray(json.v0),this.v1.fromArray(json.v1),this.v2.fromArray(json.v2),this.v3.fromArray(json.v3),this}};var CubicBezierCurve3=class extends Curve{constructor(v0=new Vector3,v1=new Vector3,v2=new Vector3,v3=new Vector3){super(),this.isCubicBezierCurve3=!0,this.type="CubicBezierCurve3",this.v0=v0,this.v1=v1,this.v2=v2,this.v3=v3}getPoint(t,optionalTarget=new Vector3){let point=optionalTarget,v0=this.v0,v1=this.v1,v2=this.v2,v3=this.v3;return point.set(CubicBezier(t,v0.x,v1.x,v2.x,v3.x),CubicBezier(t,v0.y,v1.y,v2.y,v3.y),CubicBezier(t,v0.z,v1.z,v2.z,v3.z)),point}copy(source){return super.copy(source),this.v0.copy(source.v0),this.v1.copy(source.v1),this.v2.copy(source.v2),this.v3.copy(source.v3),this}toJSON(){let data=super.toJSON();return data.v0=this.v0.toArray(),data.v1=this.v1.toArray(),data.v2=this.v2.toArray(),data.v3=this.v3.toArray(),data}fromJSON(json){return super.fromJSON(json),this.v0.fromArray(json.v0),this.v1.fromArray(json.v1),this.v2.fromArray(json.v2),this.v3.fromArray(json.v3),this}};var LineCurve=class extends Curve{constructor(v1=new Vector2,v2=new Vector2){super(),this.isLineCurve=!0,this.type="LineCurve",this.v1=v1,this.v2=v2}getPoint(t,optionalTarget=new Vector2){let point=optionalTarget;return t===1?point.copy(this.v2):(point.copy(this.v2).sub(this.v1),point.multiplyScalar(t).add(this.v1)),point}getPointAt(u,optionalTarget){return this.getPoint(u,optionalTarget)}getTangent(t,optionalTarget=new Vector2){return optionalTarget.subVectors(this.v2,this.v1).normalize()}getTangentAt(u,optionalTarget){return this.getTangent(u,optionalTarget)}copy(source){return super.copy(source),this.v1.copy(source.v1),this.v2.copy(source.v2),this}toJSON(){let data=super.toJSON();return data.v1=this.v1.toArray(),data.v2=this.v2.toArray(),data}fromJSON(json){return super.fromJSON(json),this.v1.fromArray(json.v1),this.v2.fromArray(json.v2),this}};var LineCurve3=class extends Curve{constructor(v1=new Vector3,v2=new Vector3){super(),this.isLineCurve3=!0,this.type="LineCurve3",this.v1=v1,this.v2=v2}getPoint(t,optionalTarget=new Vector3){let point=optionalTarget;return t===1?point.copy(this.v2):(point.copy(this.v2).sub(this.v1),point.multiplyScalar(t).add(this.v1)),point}getPointAt(u,optionalTarget){return this.getPoint(u,optionalTarget)}getTangent(t,optionalTarget=new Vector3){return optionalTarget.subVectors(this.v2,this.v1).normalize()}getTangentAt(u,optionalTarget){return this.getTangent(u,optionalTarget)}copy(source){return super.copy(source),this.v1.copy(source.v1),this.v2.copy(source.v2),this}toJSON(){let data=super.toJSON();return data.v1=this.v1.toArray(),data.v2=this.v2.toArray(),data}fromJSON(json){return super.fromJSON(json),this.v1.fromArray(json.v1),this.v2.fromArray(json.v2),this}};var QuadraticBezierCurve=class extends Curve{constructor(v0=new Vector2,v1=new Vector2,v2=new Vector2){super(),this.isQuadraticBezierCurve=!0,this.type="QuadraticBezierCurve",this.v0=v0,this.v1=v1,this.v2=v2}getPoint(t,optionalTarget=new Vector2){let point=optionalTarget,v0=this.v0,v1=this.v1,v2=this.v2;return point.set(QuadraticBezier(t,v0.x,v1.x,v2.x),QuadraticBezier(t,v0.y,v1.y,v2.y)),point}copy(source){return super.copy(source),this.v0.copy(source.v0),this.v1.copy(source.v1),this.v2.copy(source.v2),this}toJSON(){let data=super.toJSON();return data.v0=this.v0.toArray(),data.v1=this.v1.toArray(),data.v2=this.v2.toArray(),data}fromJSON(json){return super.fromJSON(json),this.v0.fromArray(json.v0),this.v1.fromArray(json.v1),this.v2.fromArray(json.v2),this}};var QuadraticBezierCurve3=class extends Curve{constructor(v0=new Vector3,v1=new Vector3,v2=new Vector3){super(),this.isQuadraticBezierCurve3=!0,this.type="QuadraticBezierCurve3",this.v0=v0,this.v1=v1,this.v2=v2}getPoint(t,optionalTarget=new Vector3){let point=optionalTarget,v0=this.v0,v1=this.v1,v2=this.v2;return point.set(QuadraticBezier(t,v0.x,v1.x,v2.x),QuadraticBezier(t,v0.y,v1.y,v2.y),QuadraticBezier(t,v0.z,v1.z,v2.z)),point}copy(source){return super.copy(source),this.v0.copy(source.v0),this.v1.copy(source.v1),this.v2.copy(source.v2),this}toJSON(){let data=super.toJSON();return data.v0=this.v0.toArray(),data.v1=this.v1.toArray(),data.v2=this.v2.toArray(),data}fromJSON(json){return super.fromJSON(json),this.v0.fromArray(json.v0),this.v1.fromArray(json.v1),this.v2.fromArray(json.v2),this}};var SplineCurve=class extends Curve{constructor(points=[]){super(),this.isSplineCurve=!0,this.type="SplineCurve",this.points=points}getPoint(t,optionalTarget=new Vector2){let point=optionalTarget,points=this.points,p=(points.length-1)*t,intPoint=Math.floor(p),weight=p-intPoint,p0=points[intPoint===0?intPoint:intPoint-1],p1=points[intPoint],p2=points[intPoint>points.length-2?points.length-1:intPoint+1],p3=points[intPoint>points.length-3?points.length-1:intPoint+2];return point.set(CatmullRom(weight,p0.x,p1.x,p2.x,p3.x),CatmullRom(weight,p0.y,p1.y,p2.y,p3.y)),point}copy(source){super.copy(source),this.points=[];for(let i=0,l=source.points.length;i<l;i++){let point=source.points[i];this.points.push(point.clone())}return this}toJSON(){let data=super.toJSON();data.points=[];for(let i=0,l=this.points.length;i<l;i++){let point=this.points[i];data.points.push(point.toArray())}return data}fromJSON(json){super.fromJSON(json),this.points=[];for(let i=0,l=json.points.length;i<l;i++){let point=json.points[i];this.points.push(new Vector2().fromArray(point))}return this}};var CurvePath=class extends Curve{constructor(){super(),this.type="CurvePath",this.curves=[],this.autoClose=!1}add(curve){this.curves.push(curve)}closePath(){let startPoint=this.curves[0].getPoint(0),endPoint=this.curves[this.curves.length-1].getPoint(1);if(!startPoint.equals(endPoint)){let lineType=startPoint.isVector2===!0?"LineCurve":"LineCurve3";this.curves.push(new Curves_exports[lineType](endPoint,startPoint))}return this}getPoint(t,optionalTarget){let d=t*this.getLength(),curveLengths=this.getCurveLengths(),i=0;for(;i<curveLengths.length;){if(curveLengths[i]>=d){let diff=curveLengths[i]-d,curve=this.curves[i],segmentLength=curve.getLength(),u=segmentLength===0?0:1-diff/segmentLength;return curve.getPointAt(u,optionalTarget)}i++}return null}getLength(){let lens=this.getCurveLengths();return lens[lens.length-1]}updateArcLengths(){this.needsUpdate=!0,this.cacheLengths=null,this.getCurveLengths()}getCurveLengths(){if(this.cacheLengths&&this.cacheLengths.length===this.curves.length)return this.cacheLengths;let lengths=[],sums=0;for(let i=0,l=this.curves.length;i<l;i++)sums+=this.curves[i].getLength(),lengths.push(sums);return this.cacheLengths=lengths,lengths}getSpacedPoints(divisions=40){let points=[];for(let i=0;i<=divisions;i++)points.push(this.getPoint(i/divisions));return this.autoClose&&points.push(points[0]),points}getPoints(divisions=12){let points=[],last;for(let i=0,curves=this.curves;i<curves.length;i++){let curve=curves[i],resolution=curve.isEllipseCurve?divisions*2:curve.isLineCurve||curve.isLineCurve3?1:curve.isSplineCurve?divisions*curve.points.length:divisions,pts=curve.getPoints(resolution);for(let j=0;j<pts.length;j++){let point=pts[j];last&&last.equals(point)||(points.push(point),last=point)}}return this.autoClose&&points.length>1&&!points[points.length-1].equals(points[0])&&points.push(points[0]),points}copy(source){super.copy(source),this.curves=[];for(let i=0,l=source.curves.length;i<l;i++){let curve=source.curves[i];this.curves.push(curve.clone())}return this.autoClose=source.autoClose,this}toJSON(){let data=super.toJSON();data.autoClose=this.autoClose,data.curves=[];for(let i=0,l=this.curves.length;i<l;i++){let curve=this.curves[i];data.curves.push(curve.toJSON())}return data}fromJSON(json){super.fromJSON(json),this.autoClose=json.autoClose,this.curves=[];for(let i=0,l=json.curves.length;i<l;i++){let curve=json.curves[i];this.curves.push(new Curves_exports[curve.type]().fromJSON(curve))}return this}};var Path=class extends CurvePath{constructor(points){super(),this.type="Path",this.currentPoint=new Vector2,points&&this.setFromPoints(points)}setFromPoints(points){this.moveTo(points[0].x,points[0].y);for(let i=1,l=points.length;i<l;i++)this.lineTo(points[i].x,points[i].y);return this}moveTo(x,y){return this.currentPoint.set(x,y),this}lineTo(x,y){let curve=new LineCurve(this.currentPoint.clone(),new Vector2(x,y));return this.curves.push(curve),this.currentPoint.set(x,y),this}quadraticCurveTo(aCPx,aCPy,aX,aY){let curve=new QuadraticBezierCurve(this.currentPoint.clone(),new Vector2(aCPx,aCPy),new Vector2(aX,aY));return this.curves.push(curve),this.currentPoint.set(aX,aY),this}bezierCurveTo(aCP1x,aCP1y,aCP2x,aCP2y,aX,aY){let curve=new CubicBezierCurve(this.currentPoint.clone(),new Vector2(aCP1x,aCP1y),new Vector2(aCP2x,aCP2y),new Vector2(aX,aY));return this.curves.push(curve),this.currentPoint.set(aX,aY),this}splineThru(pts){let npts=[this.currentPoint.clone()].concat(pts),curve=new SplineCurve(npts);return this.curves.push(curve),this.currentPoint.copy(pts[pts.length-1]),this}arc(aX,aY,aRadius,aStartAngle,aEndAngle,aClockwise){let x0=this.currentPoint.x,y0=this.currentPoint.y;return this.absarc(aX+x0,aY+y0,aRadius,aStartAngle,aEndAngle,aClockwise),this}absarc(aX,aY,aRadius,aStartAngle,aEndAngle,aClockwise){return this.absellipse(aX,aY,aRadius,aRadius,aStartAngle,aEndAngle,aClockwise),this}ellipse(aX,aY,xRadius,yRadius,aStartAngle,aEndAngle,aClockwise,aRotation){let x0=this.currentPoint.x,y0=this.currentPoint.y;return this.absellipse(aX+x0,aY+y0,xRadius,yRadius,aStartAngle,aEndAngle,aClockwise,aRotation),this}absellipse(aX,aY,xRadius,yRadius,aStartAngle,aEndAngle,aClockwise,aRotation){let curve=new EllipseCurve(aX,aY,xRadius,yRadius,aStartAngle,aEndAngle,aClockwise,aRotation);if(this.curves.length>0){let firstPoint=curve.getPoint(0);firstPoint.equals(this.currentPoint)||this.lineTo(firstPoint.x,firstPoint.y)}this.curves.push(curve);let lastPoint=curve.getPoint(1);return this.currentPoint.copy(lastPoint),this}copy(source){return super.copy(source),this.currentPoint.copy(source.currentPoint),this}toJSON(){let data=super.toJSON();return data.currentPoint=this.currentPoint.toArray(),data}fromJSON(json){return super.fromJSON(json),this.currentPoint.fromArray(json.currentPoint),this}};var Shape=class extends Path{constructor(points){super(points),this.uuid=generateUUID(),this.type="Shape",this.holes=[]}getPointsHoles(divisions){let holesPts=[];for(let i=0,l=this.holes.length;i<l;i++)holesPts[i]=this.holes[i].getPoints(divisions);return holesPts}extractPoints(divisions){return{shape:this.getPoints(divisions),holes:this.getPointsHoles(divisions)}}copy(source){super.copy(source),this.holes=[];for(let i=0,l=source.holes.length;i<l;i++){let hole=source.holes[i];this.holes.push(hole.clone())}return this}toJSON(){let data=super.toJSON();data.uuid=this.uuid,data.holes=[];for(let i=0,l=this.holes.length;i<l;i++){let hole=this.holes[i];data.holes.push(hole.toJSON())}return data}fromJSON(json){super.fromJSON(json),this.uuid=json.uuid,this.holes=[];for(let i=0,l=json.holes.length;i<l;i++){let hole=json.holes[i];this.holes.push(new Path().fromJSON(hole))}return this}};function earcut(data,holeIndices,dim=2){let hasHoles=holeIndices&&holeIndices.length,outerLen=hasHoles?holeIndices[0]*dim:data.length,outerNode=linkedList(data,0,outerLen,dim,!0),triangles=[];if(!outerNode||outerNode.next===outerNode.prev)return triangles;let minX,minY,invSize;if(hasHoles&&(outerNode=eliminateHoles(data,holeIndices,outerNode,dim)),data.length>80*dim){minX=data[0],minY=data[1];let maxX=minX,maxY=minY;for(let i=dim;i<outerLen;i+=dim){let x=data[i],y=data[i+1];x<minX&&(minX=x),y<minY&&(minY=y),x>maxX&&(maxX=x),y>maxY&&(maxY=y)}invSize=Math.max(maxX-minX,maxY-minY),invSize=invSize!==0?32767/invSize:0}return earcutLinked(outerNode,triangles,dim,minX,minY,invSize,0),triangles}function linkedList(data,start,end,dim,clockwise){let last;if(clockwise===signedArea(data,start,end,dim)>0)for(let i=start;i<end;i+=dim)last=insertNode(i/dim|0,data[i],data[i+1],last);else for(let i=end-dim;i>=start;i-=dim)last=insertNode(i/dim|0,data[i],data[i+1],last);return last&&equals(last,last.next)&&(removeNode(last),last=last.next),last}function filterPoints(start,end){if(!start)return start;end||(end=start);let p=start,again;do if(again=!1,!p.steiner&&(equals(p,p.next)||area(p.prev,p,p.next)===0)){if(removeNode(p),p=end=p.prev,p===p.next)break;again=!0}else p=p.next;while(again||p!==end);return end}function earcutLinked(ear,triangles,dim,minX,minY,invSize,pass){if(!ear)return;!pass&&invSize&&indexCurve(ear,minX,minY,invSize);let stop=ear;for(;ear.prev!==ear.next;){let prev=ear.prev,next=ear.next;if(invSize?isEarHashed(ear,minX,minY,invSize):isEar(ear)){triangles.push(prev.i,ear.i,next.i),removeNode(ear),ear=next.next,stop=next.next;continue}if(ear=next,ear===stop){pass?pass===1?(ear=cureLocalIntersections(filterPoints(ear),triangles),earcutLinked(ear,triangles,dim,minX,minY,invSize,2)):pass===2&&splitEarcut(ear,triangles,dim,minX,minY,invSize):earcutLinked(filterPoints(ear),triangles,dim,minX,minY,invSize,1);break}}}function isEar(ear){let a=ear.prev,b=ear,c=ear.next;if(area(a,b,c)>=0)return!1;let ax=a.x,bx=b.x,cx=c.x,ay=a.y,by=b.y,cy=c.y,x0=Math.min(ax,bx,cx),y0=Math.min(ay,by,cy),x1=Math.max(ax,bx,cx),y1=Math.max(ay,by,cy),p=c.next;for(;p!==a;){if(p.x>=x0&&p.x<=x1&&p.y>=y0&&p.y<=y1&&pointInTriangleExceptFirst(ax,ay,bx,by,cx,cy,p.x,p.y)&&area(p.prev,p,p.next)>=0)return!1;p=p.next}return!0}function isEarHashed(ear,minX,minY,invSize){let a=ear.prev,b=ear,c=ear.next;if(area(a,b,c)>=0)return!1;let ax=a.x,bx=b.x,cx=c.x,ay=a.y,by=b.y,cy=c.y,x0=Math.min(ax,bx,cx),y0=Math.min(ay,by,cy),x1=Math.max(ax,bx,cx),y1=Math.max(ay,by,cy),minZ=zOrder(x0,y0,minX,minY,invSize),maxZ=zOrder(x1,y1,minX,minY,invSize),p=ear.prevZ,n=ear.nextZ;for(;p&&p.z>=minZ&&n&&n.z<=maxZ;){if(p.x>=x0&&p.x<=x1&&p.y>=y0&&p.y<=y1&&p!==a&&p!==c&&pointInTriangleExceptFirst(ax,ay,bx,by,cx,cy,p.x,p.y)&&area(p.prev,p,p.next)>=0||(p=p.prevZ,n.x>=x0&&n.x<=x1&&n.y>=y0&&n.y<=y1&&n!==a&&n!==c&&pointInTriangleExceptFirst(ax,ay,bx,by,cx,cy,n.x,n.y)&&area(n.prev,n,n.next)>=0))return!1;n=n.nextZ}for(;p&&p.z>=minZ;){if(p.x>=x0&&p.x<=x1&&p.y>=y0&&p.y<=y1&&p!==a&&p!==c&&pointInTriangleExceptFirst(ax,ay,bx,by,cx,cy,p.x,p.y)&&area(p.prev,p,p.next)>=0)return!1;p=p.prevZ}for(;n&&n.z<=maxZ;){if(n.x>=x0&&n.x<=x1&&n.y>=y0&&n.y<=y1&&n!==a&&n!==c&&pointInTriangleExceptFirst(ax,ay,bx,by,cx,cy,n.x,n.y)&&area(n.prev,n,n.next)>=0)return!1;n=n.nextZ}return!0}function cureLocalIntersections(start,triangles){let p=start;do{let a=p.prev,b=p.next.next;!equals(a,b)&&intersects(a,p,p.next,b)&&locallyInside(a,b)&&locallyInside(b,a)&&(triangles.push(a.i,p.i,b.i),removeNode(p),removeNode(p.next),p=start=b),p=p.next}while(p!==start);return filterPoints(p)}function splitEarcut(start,triangles,dim,minX,minY,invSize){let a=start;do{let b=a.next.next;for(;b!==a.prev;){if(a.i!==b.i&&isValidDiagonal(a,b)){let c=splitPolygon(a,b);a=filterPoints(a,a.next),c=filterPoints(c,c.next),earcutLinked(a,triangles,dim,minX,minY,invSize,0),earcutLinked(c,triangles,dim,minX,minY,invSize,0);return}b=b.next}a=a.next}while(a!==start)}function eliminateHoles(data,holeIndices,outerNode,dim){let queue=[];for(let i=0,len=holeIndices.length;i<len;i++){let start=holeIndices[i]*dim,end=i<len-1?holeIndices[i+1]*dim:data.length,list=linkedList(data,start,end,dim,!1);list===list.next&&(list.steiner=!0),queue.push(getLeftmost(list))}queue.sort(compareXYSlope);for(let i=0;i<queue.length;i++)outerNode=eliminateHole(queue[i],outerNode);return outerNode}function compareXYSlope(a,b){let result=a.x-b.x;if(result===0&&(result=a.y-b.y,result===0)){let aSlope=(a.next.y-a.y)/(a.next.x-a.x),bSlope=(b.next.y-b.y)/(b.next.x-b.x);result=aSlope-bSlope}return result}function eliminateHole(hole,outerNode){let bridge=findHoleBridge(hole,outerNode);if(!bridge)return outerNode;let bridgeReverse=splitPolygon(bridge,hole);return filterPoints(bridgeReverse,bridgeReverse.next),filterPoints(bridge,bridge.next)}function findHoleBridge(hole,outerNode){let p=outerNode,hx=hole.x,hy=hole.y,qx=-1/0,m;if(equals(hole,p))return p;do{if(equals(hole,p.next))return p.next;if(hy<=p.y&&hy>=p.next.y&&p.next.y!==p.y){let x=p.x+(hy-p.y)*(p.next.x-p.x)/(p.next.y-p.y);if(x<=hx&&x>qx&&(qx=x,m=p.x<p.next.x?p:p.next,x===hx))return m}p=p.next}while(p!==outerNode);if(!m)return null;let stop=m,mx=m.x,my=m.y,tanMin=1/0;p=m;do{if(hx>=p.x&&p.x>=mx&&hx!==p.x&&pointInTriangle(hy<my?hx:qx,hy,mx,my,hy<my?qx:hx,hy,p.x,p.y)){let tan=Math.abs(hy-p.y)/(hx-p.x);locallyInside(p,hole)&&(tan<tanMin||tan===tanMin&&(p.x>m.x||p.x===m.x&&sectorContainsSector(m,p)))&&(m=p,tanMin=tan)}p=p.next}while(p!==stop);return m}function sectorContainsSector(m,p){return area(m.prev,m,p.prev)<0&&area(p.next,m,m.next)<0}function indexCurve(start,minX,minY,invSize){let p=start;do p.z===0&&(p.z=zOrder(p.x,p.y,minX,minY,invSize)),p.prevZ=p.prev,p.nextZ=p.next,p=p.next;while(p!==start);p.prevZ.nextZ=null,p.prevZ=null,sortLinked(p)}function sortLinked(list){let numMerges,inSize=1;do{let p=list,e;list=null;let tail=null;for(numMerges=0;p;){numMerges++;let q=p,pSize=0;for(let i=0;i<inSize&&(pSize++,q=q.nextZ,!!q);i++);let qSize=inSize;for(;pSize>0||qSize>0&&q;)pSize!==0&&(qSize===0||!q||p.z<=q.z)?(e=p,p=p.nextZ,pSize--):(e=q,q=q.nextZ,qSize--),tail?tail.nextZ=e:list=e,e.prevZ=tail,tail=e;p=q}tail.nextZ=null,inSize*=2}while(numMerges>1);return list}function zOrder(x,y,minX,minY,invSize){return x=(x-minX)*invSize|0,y=(y-minY)*invSize|0,x=(x|x<<8)&16711935,x=(x|x<<4)&252645135,x=(x|x<<2)&858993459,x=(x|x<<1)&1431655765,y=(y|y<<8)&16711935,y=(y|y<<4)&252645135,y=(y|y<<2)&858993459,y=(y|y<<1)&1431655765,x|y<<1}function getLeftmost(start){let p=start,leftmost=start;do(p.x<leftmost.x||p.x===leftmost.x&&p.y<leftmost.y)&&(leftmost=p),p=p.next;while(p!==start);return leftmost}function pointInTriangle(ax,ay,bx,by,cx,cy,px2,py2){return(cx-px2)*(ay-py2)>=(ax-px2)*(cy-py2)&&(ax-px2)*(by-py2)>=(bx-px2)*(ay-py2)&&(bx-px2)*(cy-py2)>=(cx-px2)*(by-py2)}function pointInTriangleExceptFirst(ax,ay,bx,by,cx,cy,px2,py2){return!(ax===px2&&ay===py2)&&pointInTriangle(ax,ay,bx,by,cx,cy,px2,py2)}function isValidDiagonal(a,b){return a.next.i!==b.i&&a.prev.i!==b.i&&!intersectsPolygon(a,b)&&(locallyInside(a,b)&&locallyInside(b,a)&&middleInside(a,b)&&(area(a.prev,a,b.prev)||area(a,b.prev,b))||equals(a,b)&&area(a.prev,a,a.next)>0&&area(b.prev,b,b.next)>0)}function area(p,q,r){return(q.y-p.y)*(r.x-q.x)-(q.x-p.x)*(r.y-q.y)}function equals(p1,p2){return p1.x===p2.x&&p1.y===p2.y}function intersects(p1,q1,p2,q2){let o1=sign(area(p1,q1,p2)),o2=sign(area(p1,q1,q2)),o3=sign(area(p2,q2,p1)),o4=sign(area(p2,q2,q1));return!!(o1!==o2&&o3!==o4||o1===0&&onSegment(p1,p2,q1)||o2===0&&onSegment(p1,q2,q1)||o3===0&&onSegment(p2,p1,q2)||o4===0&&onSegment(p2,q1,q2))}function onSegment(p,q,r){return q.x<=Math.max(p.x,r.x)&&q.x>=Math.min(p.x,r.x)&&q.y<=Math.max(p.y,r.y)&&q.y>=Math.min(p.y,r.y)}function sign(num){return num>0?1:num<0?-1:0}function intersectsPolygon(a,b){let p=a;do{if(p.i!==a.i&&p.next.i!==a.i&&p.i!==b.i&&p.next.i!==b.i&&intersects(p,p.next,a,b))return!0;p=p.next}while(p!==a);return!1}function locallyInside(a,b){return area(a.prev,a,a.next)<0?area(a,b,a.next)>=0&&area(a,a.prev,b)>=0:area(a,b,a.prev)<0||area(a,a.next,b)<0}function middleInside(a,b){let p=a,inside=!1,px2=(a.x+b.x)/2,py2=(a.y+b.y)/2;do p.y>py2!=p.next.y>py2&&p.next.y!==p.y&&px2<(p.next.x-p.x)*(py2-p.y)/(p.next.y-p.y)+p.x&&(inside=!inside),p=p.next;while(p!==a);return inside}function splitPolygon(a,b){let a2=createNode(a.i,a.x,a.y),b2=createNode(b.i,b.x,b.y),an=a.next,bp=b.prev;return a.next=b,b.prev=a,a2.next=an,an.prev=a2,b2.next=a2,a2.prev=b2,bp.next=b2,b2.prev=bp,b2}function insertNode(i,x,y,last){let p=createNode(i,x,y);return last?(p.next=last.next,p.prev=last,last.next.prev=p,last.next=p):(p.prev=p,p.next=p),p}function removeNode(p){p.next.prev=p.prev,p.prev.next=p.next,p.prevZ&&(p.prevZ.nextZ=p.nextZ),p.nextZ&&(p.nextZ.prevZ=p.prevZ)}function createNode(i,x,y){return{i,x,y,prev:null,next:null,z:0,prevZ:null,nextZ:null,steiner:!1}}function signedArea(data,start,end,dim){let sum=0;for(let i=start,j=end-dim;i<end;i+=dim)sum+=(data[j]-data[i])*(data[i+1]+data[j+1]),j=i;return sum}var Earcut=class{static triangulate(data,holeIndices,dim=2){return earcut(data,holeIndices,dim)}};var ShapeUtils=class _ShapeUtils{static area(contour){let n=contour.length,a=0;for(let p=n-1,q=0;q<n;p=q++)a+=contour[p].x*contour[q].y-contour[q].x*contour[p].y;return a*.5}static isClockWise(pts){return _ShapeUtils.area(pts)<0}static triangulateShape(contour,holes){let vertices=[],holeIndices=[],faces=[];removeDupEndPts(contour),addContour(vertices,contour);let holeIndex=contour.length;holes.forEach(removeDupEndPts);for(let i=0;i<holes.length;i++)holeIndices.push(holeIndex),holeIndex+=holes[i].length,addContour(vertices,holes[i]);let triangles=Earcut.triangulate(vertices,holeIndices);for(let i=0;i<triangles.length;i+=3)faces.push(triangles.slice(i,i+3));return faces}};function removeDupEndPts(points){let l=points.length;l>2&&points[l-1].equals(points[0])&&points.pop()}function addContour(vertices,contour){for(let i=0;i<contour.length;i++)vertices.push(contour[i].x),vertices.push(contour[i].y)}var ExtrudeGeometry=class _ExtrudeGeometry extends BufferGeometry{constructor(shapes=new Shape([new Vector2(.5,.5),new Vector2(-.5,.5),new Vector2(-.5,-.5),new Vector2(.5,-.5)]),options={}){super(),this.type="ExtrudeGeometry",this.parameters={shapes,options},shapes=Array.isArray(shapes)?shapes:[shapes];let scope=this,verticesArray=[],uvArray=[];for(let i=0,l=shapes.length;i<l;i++){let shape=shapes[i];addShape(shape)}this.setAttribute("position",new Float32BufferAttribute(verticesArray,3)),this.setAttribute("uv",new Float32BufferAttribute(uvArray,2)),this.computeVertexNormals();function addShape(shape){let placeholder=[],curveSegments=options.curveSegments!==void 0?options.curveSegments:12,steps=options.steps!==void 0?options.steps:1,depth=options.depth!==void 0?options.depth:1,bevelEnabled=options.bevelEnabled!==void 0?options.bevelEnabled:!0,bevelThickness=options.bevelThickness!==void 0?options.bevelThickness:.2,bevelSize=options.bevelSize!==void 0?options.bevelSize:bevelThickness-.1,bevelOffset=options.bevelOffset!==void 0?options.bevelOffset:0,bevelSegments=options.bevelSegments!==void 0?options.bevelSegments:3,extrudePath=options.extrudePath,uvgen=options.UVGenerator!==void 0?options.UVGenerator:WorldUVGenerator,extrudePts,extrudeByPath=!1,splineTube,binormal,normal,position2;if(extrudePath){extrudePts=extrudePath.getSpacedPoints(steps),extrudeByPath=!0,bevelEnabled=!1;let isClosed=extrudePath.isCatmullRomCurve3?extrudePath.closed:!1;splineTube=extrudePath.computeFrenetFrames(steps,isClosed),binormal=new Vector3,normal=new Vector3,position2=new Vector3}bevelEnabled||(bevelSegments=0,bevelThickness=0,bevelSize=0,bevelOffset=0);let shapePoints=shape.extractPoints(curveSegments),vertices=shapePoints.shape,holes=shapePoints.holes;if(!ShapeUtils.isClockWise(vertices)){vertices=vertices.reverse();for(let h=0,hl=holes.length;h<hl;h++){let ahole=holes[h];ShapeUtils.isClockWise(ahole)&&(holes[h]=ahole.reverse())}}function mergeOverlappingPoints(points){let THRESHOLD_SQ=10000000000000001e-36,prevPos=points[0];for(let i=1;i<=points.length;i++){let currentIndex=i%points.length,currentPos=points[currentIndex],dx=currentPos.x-prevPos.x,dy=currentPos.y-prevPos.y,distSq=dx*dx+dy*dy,scalingFactorSqrt=Math.max(Math.abs(currentPos.x),Math.abs(currentPos.y),Math.abs(prevPos.x),Math.abs(prevPos.y)),thresholdSqScaled=THRESHOLD_SQ*scalingFactorSqrt*scalingFactorSqrt;if(distSq<=thresholdSqScaled){points.splice(currentIndex,1),i--;continue}prevPos=currentPos}}mergeOverlappingPoints(vertices),holes.forEach(mergeOverlappingPoints);let numHoles=holes.length,contour=vertices;for(let h=0;h<numHoles;h++){let ahole=holes[h];vertices=vertices.concat(ahole)}function scalePt2(pt,vec,size){return vec||error("ExtrudeGeometry: vec does not exist"),pt.clone().addScaledVector(vec,size)}let vlen=vertices.length;function getBevelVec(inPt,inPrev,inNext){let v_trans_x,v_trans_y,shrink_by,v_prev_x=inPt.x-inPrev.x,v_prev_y=inPt.y-inPrev.y,v_next_x=inNext.x-inPt.x,v_next_y=inNext.y-inPt.y,v_prev_lensq=v_prev_x*v_prev_x+v_prev_y*v_prev_y,collinear0=v_prev_x*v_next_y-v_prev_y*v_next_x;if(Math.abs(collinear0)>Number.EPSILON){let v_prev_len=Math.sqrt(v_prev_lensq),v_next_len=Math.sqrt(v_next_x*v_next_x+v_next_y*v_next_y),ptPrevShift_x=inPrev.x-v_prev_y/v_prev_len,ptPrevShift_y=inPrev.y+v_prev_x/v_prev_len,ptNextShift_x=inNext.x-v_next_y/v_next_len,ptNextShift_y=inNext.y+v_next_x/v_next_len,sf=((ptNextShift_x-ptPrevShift_x)*v_next_y-(ptNextShift_y-ptPrevShift_y)*v_next_x)/(v_prev_x*v_next_y-v_prev_y*v_next_x);v_trans_x=ptPrevShift_x+v_prev_x*sf-inPt.x,v_trans_y=ptPrevShift_y+v_prev_y*sf-inPt.y;let v_trans_lensq=v_trans_x*v_trans_x+v_trans_y*v_trans_y;if(v_trans_lensq<=2)return new Vector2(v_trans_x,v_trans_y);shrink_by=Math.sqrt(v_trans_lensq/2)}else{let direction_eq=!1;v_prev_x>Number.EPSILON?v_next_x>Number.EPSILON&&(direction_eq=!0):v_prev_x<-Number.EPSILON?v_next_x<-Number.EPSILON&&(direction_eq=!0):Math.sign(v_prev_y)===Math.sign(v_next_y)&&(direction_eq=!0),direction_eq?(v_trans_x=-v_prev_y,v_trans_y=v_prev_x,shrink_by=Math.sqrt(v_prev_lensq)):(v_trans_x=v_prev_x,v_trans_y=v_prev_y,shrink_by=Math.sqrt(v_prev_lensq/2))}return new Vector2(v_trans_x/shrink_by,v_trans_y/shrink_by)}let contourMovements=[];for(let i=0,il=contour.length,j=il-1,k=i+1;i<il;i++,j++,k++)j===il&&(j=0),k===il&&(k=0),contourMovements[i]=getBevelVec(contour[i],contour[j],contour[k]);let holesMovements=[],oneHoleMovements,verticesMovements=contourMovements.concat();for(let h=0,hl=numHoles;h<hl;h++){let ahole=holes[h];oneHoleMovements=[];for(let i=0,il=ahole.length,j=il-1,k=i+1;i<il;i++,j++,k++)j===il&&(j=0),k===il&&(k=0),oneHoleMovements[i]=getBevelVec(ahole[i],ahole[j],ahole[k]);holesMovements.push(oneHoleMovements),verticesMovements=verticesMovements.concat(oneHoleMovements)}let faces;if(bevelSegments===0)faces=ShapeUtils.triangulateShape(contour,holes);else{let contractedContourVertices=[],expandedHoleVertices=[];for(let b=0;b<bevelSegments;b++){let t=b/bevelSegments,z=bevelThickness*Math.cos(t*Math.PI/2),bs2=bevelSize*Math.sin(t*Math.PI/2)+bevelOffset;for(let i=0,il=contour.length;i<il;i++){let vert=scalePt2(contour[i],contourMovements[i],bs2);v(vert.x,vert.y,-z),t===0&&contractedContourVertices.push(vert)}for(let h=0,hl=numHoles;h<hl;h++){let ahole=holes[h];oneHoleMovements=holesMovements[h];let oneHoleVertices=[];for(let i=0,il=ahole.length;i<il;i++){let vert=scalePt2(ahole[i],oneHoleMovements[i],bs2);v(vert.x,vert.y,-z),t===0&&oneHoleVertices.push(vert)}t===0&&expandedHoleVertices.push(oneHoleVertices)}}faces=ShapeUtils.triangulateShape(contractedContourVertices,expandedHoleVertices)}let flen=faces.length,bs=bevelSize+bevelOffset;for(let i=0;i<vlen;i++){let vert=bevelEnabled?scalePt2(vertices[i],verticesMovements[i],bs):vertices[i];extrudeByPath?(normal.copy(splineTube.normals[0]).multiplyScalar(vert.x),binormal.copy(splineTube.binormals[0]).multiplyScalar(vert.y),position2.copy(extrudePts[0]).add(normal).add(binormal),v(position2.x,position2.y,position2.z)):v(vert.x,vert.y,0)}for(let s=1;s<=steps;s++)for(let i=0;i<vlen;i++){let vert=bevelEnabled?scalePt2(vertices[i],verticesMovements[i],bs):vertices[i];extrudeByPath?(normal.copy(splineTube.normals[s]).multiplyScalar(vert.x),binormal.copy(splineTube.binormals[s]).multiplyScalar(vert.y),position2.copy(extrudePts[s]).add(normal).add(binormal),v(position2.x,position2.y,position2.z)):v(vert.x,vert.y,depth/steps*s)}for(let b=bevelSegments-1;b>=0;b--){let t=b/bevelSegments,z=bevelThickness*Math.cos(t*Math.PI/2),bs2=bevelSize*Math.sin(t*Math.PI/2)+bevelOffset;for(let i=0,il=contour.length;i<il;i++){let vert=scalePt2(contour[i],contourMovements[i],bs2);v(vert.x,vert.y,depth+z)}for(let h=0,hl=holes.length;h<hl;h++){let ahole=holes[h];oneHoleMovements=holesMovements[h];for(let i=0,il=ahole.length;i<il;i++){let vert=scalePt2(ahole[i],oneHoleMovements[i],bs2);extrudeByPath?v(vert.x,vert.y+extrudePts[steps-1].y,extrudePts[steps-1].x+z):v(vert.x,vert.y,depth+z)}}}buildLidFaces(),buildSideFaces();function buildLidFaces(){let start=verticesArray.length/3;if(bevelEnabled){let layer=0,offset=vlen*layer;for(let i=0;i<flen;i++){let face=faces[i];f3(face[2]+offset,face[1]+offset,face[0]+offset)}layer=steps+bevelSegments*2,offset=vlen*layer;for(let i=0;i<flen;i++){let face=faces[i];f3(face[0]+offset,face[1]+offset,face[2]+offset)}}else{for(let i=0;i<flen;i++){let face=faces[i];f3(face[2],face[1],face[0])}for(let i=0;i<flen;i++){let face=faces[i];f3(face[0]+vlen*steps,face[1]+vlen*steps,face[2]+vlen*steps)}}scope.addGroup(start,verticesArray.length/3-start,0)}function buildSideFaces(){let start=verticesArray.length/3,layeroffset=0;sidewalls(contour,layeroffset),layeroffset+=contour.length;for(let h=0,hl=holes.length;h<hl;h++){let ahole=holes[h];sidewalls(ahole,layeroffset),layeroffset+=ahole.length}scope.addGroup(start,verticesArray.length/3-start,1)}function sidewalls(contour2,layeroffset){let i=contour2.length;for(;--i>=0;){let j=i,k=i-1;k<0&&(k=contour2.length-1);for(let s=0,sl=steps+bevelSegments*2;s<sl;s++){let slen1=vlen*s,slen2=vlen*(s+1),a=layeroffset+j+slen1,b=layeroffset+k+slen1,c=layeroffset+k+slen2,d=layeroffset+j+slen2;f4(a,b,c,d)}}}function v(x,y,z){placeholder.push(x),placeholder.push(y),placeholder.push(z)}function f3(a,b,c){addVertex(a),addVertex(b),addVertex(c);let nextIndex=verticesArray.length/3,uvs=uvgen.generateTopUV(scope,verticesArray,nextIndex-3,nextIndex-2,nextIndex-1);addUV(uvs[0]),addUV(uvs[1]),addUV(uvs[2])}function f4(a,b,c,d){addVertex(a),addVertex(b),addVertex(d),addVertex(b),addVertex(c),addVertex(d);let nextIndex=verticesArray.length/3,uvs=uvgen.generateSideWallUV(scope,verticesArray,nextIndex-6,nextIndex-3,nextIndex-2,nextIndex-1);addUV(uvs[0]),addUV(uvs[1]),addUV(uvs[3]),addUV(uvs[1]),addUV(uvs[2]),addUV(uvs[3])}function addVertex(index){verticesArray.push(placeholder[index*3+0]),verticesArray.push(placeholder[index*3+1]),verticesArray.push(placeholder[index*3+2])}function addUV(vector2){uvArray.push(vector2.x),uvArray.push(vector2.y)}}}copy(source){return super.copy(source),this.parameters=Object.assign({},source.parameters),this}toJSON(){let data=super.toJSON(),shapes=this.parameters.shapes,options=this.parameters.options;return toJSON(shapes,options,data)}static fromJSON(data,shapes){let geometryShapes=[];for(let j=0,jl=data.shapes.length;j<jl;j++){let shape=shapes[data.shapes[j]];geometryShapes.push(shape)}let extrudePath=data.options.extrudePath;return extrudePath!==void 0&&(data.options.extrudePath=new Curves_exports[extrudePath.type]().fromJSON(extrudePath)),new _ExtrudeGeometry(geometryShapes,data.options)}},WorldUVGenerator={generateTopUV:function(geometry,vertices,indexA,indexB,indexC){let a_x=vertices[indexA*3],a_y=vertices[indexA*3+1],b_x=vertices[indexB*3],b_y=vertices[indexB*3+1],c_x=vertices[indexC*3],c_y=vertices[indexC*3+1];return[new Vector2(a_x,a_y),new Vector2(b_x,b_y),new Vector2(c_x,c_y)]},generateSideWallUV:function(geometry,vertices,indexA,indexB,indexC,indexD){let a_x=vertices[indexA*3],a_y=vertices[indexA*3+1],a_z=vertices[indexA*3+2],b_x=vertices[indexB*3],b_y=vertices[indexB*3+1],b_z=vertices[indexB*3+2],c_x=vertices[indexC*3],c_y=vertices[indexC*3+1],c_z=vertices[indexC*3+2],d_x=vertices[indexD*3],d_y=vertices[indexD*3+1],d_z=vertices[indexD*3+2];return Math.abs(a_y-b_y)<Math.abs(a_x-b_x)?[new Vector2(a_x,1-a_z),new Vector2(b_x,1-b_z),new Vector2(c_x,1-c_z),new Vector2(d_x,1-d_z)]:[new Vector2(a_y,1-a_z),new Vector2(b_y,1-b_z),new Vector2(c_y,1-c_z),new Vector2(d_y,1-d_z)]}};function toJSON(shapes,options,data){if(data.shapes=[],Array.isArray(shapes))for(let i=0,l=shapes.length;i<l;i++){let shape=shapes[i];data.shapes.push(shape.uuid)}else data.shapes.push(shapes.uuid);return data.options=Object.assign({},options),options.extrudePath!==void 0&&(data.options.extrudePath=options.extrudePath.toJSON()),data}var IcosahedronGeometry=class _IcosahedronGeometry extends PolyhedronGeometry{constructor(radius=1,detail=0){let t=(1+Math.sqrt(5))/2,vertices=[-1,t,0,1,t,0,-1,-t,0,1,-t,0,0,-1,t,0,1,t,0,-1,-t,0,1,-t,t,0,-1,t,0,1,-t,0,-1,-t,0,1],indices=[0,11,5,0,5,1,0,1,7,0,7,10,0,10,11,1,5,9,5,11,4,11,10,2,10,7,6,7,1,8,3,9,4,3,4,2,3,2,6,3,6,8,3,8,9,4,9,5,2,4,11,6,2,10,8,6,7,9,8,1];super(vertices,indices,radius,detail),this.type="IcosahedronGeometry",this.parameters={radius,detail}}static fromJSON(data){return new _IcosahedronGeometry(data.radius,data.detail)}};var PlaneGeometry=class _PlaneGeometry extends BufferGeometry{constructor(width=1,height=1,widthSegments=1,heightSegments=1){super(),this.type="PlaneGeometry",this.parameters={width,height,widthSegments,heightSegments};let width_half=width/2,height_half=height/2,gridX=Math.floor(widthSegments),gridY=Math.floor(heightSegments),gridX1=gridX+1,gridY1=gridY+1,segment_width=width/gridX,segment_height=height/gridY,indices=[],vertices=[],normals=[],uvs=[];for(let iy=0;iy<gridY1;iy++){let y=iy*segment_height-height_half;for(let ix=0;ix<gridX1;ix++){let x=ix*segment_width-width_half;vertices.push(x,-y,0),normals.push(0,0,1),uvs.push(ix/gridX),uvs.push(1-iy/gridY)}}for(let iy=0;iy<gridY;iy++)for(let ix=0;ix<gridX;ix++){let a=ix+gridX1*iy,b=ix+gridX1*(iy+1),c=ix+1+gridX1*(iy+1),d=ix+1+gridX1*iy;indices.push(a,b,d),indices.push(b,c,d)}this.setIndex(indices),this.setAttribute("position",new Float32BufferAttribute(vertices,3)),this.setAttribute("normal",new Float32BufferAttribute(normals,3)),this.setAttribute("uv",new Float32BufferAttribute(uvs,2))}copy(source){return super.copy(source),this.parameters=Object.assign({},source.parameters),this}static fromJSON(data){return new _PlaneGeometry(data.width,data.height,data.widthSegments,data.heightSegments)}};var SphereGeometry=class _SphereGeometry extends BufferGeometry{constructor(radius=1,widthSegments=32,heightSegments=16,phiStart=0,phiLength=Math.PI*2,thetaStart=0,thetaLength=Math.PI){super(),this.type="SphereGeometry",this.parameters={radius,widthSegments,heightSegments,phiStart,phiLength,thetaStart,thetaLength},widthSegments=Math.max(3,Math.floor(widthSegments)),heightSegments=Math.max(2,Math.floor(heightSegments));let thetaEnd=Math.min(thetaStart+thetaLength,Math.PI),index=0,grid=[],vertex19=new Vector3,normal=new Vector3,indices=[],vertices=[],normals=[],uvs=[];for(let iy=0;iy<=heightSegments;iy++){let verticesRow=[],v=iy/heightSegments,theta=thetaStart+v*thetaLength,y=radius*Math.cos(theta),ringRadius=Math.sqrt(radius*radius-y*y),uOffset=0;iy===0&&thetaStart===0?uOffset=.5/widthSegments:iy===heightSegments&&thetaEnd===Math.PI&&(uOffset=-.5/widthSegments);for(let ix=0;ix<=widthSegments;ix++){let u=ix/widthSegments,phi=phiStart+u*phiLength;vertex19.x=-ringRadius*Math.cos(phi),vertex19.y=y,vertex19.z=ringRadius*Math.sin(phi),vertices.push(vertex19.x,vertex19.y,vertex19.z),normal.copy(vertex19).normalize(),normals.push(normal.x,normal.y,normal.z),uvs.push(u+uOffset,1-v),verticesRow.push(index++)}grid.push(verticesRow)}for(let iy=0;iy<heightSegments;iy++)for(let ix=0;ix<widthSegments;ix++){let a=grid[iy][ix+1],b=grid[iy][ix],c=grid[iy+1][ix],d=grid[iy+1][ix+1];(iy!==0||thetaStart>0)&&indices.push(a,b,d),(iy!==heightSegments-1||thetaEnd<Math.PI)&&indices.push(b,c,d)}this.setIndex(indices),this.setAttribute("position",new Float32BufferAttribute(vertices,3)),this.setAttribute("normal",new Float32BufferAttribute(normals,3)),this.setAttribute("uv",new Float32BufferAttribute(uvs,2))}copy(source){return super.copy(source),this.parameters=Object.assign({},source.parameters),this}static fromJSON(data){return new _SphereGeometry(data.radius,data.widthSegments,data.heightSegments,data.phiStart,data.phiLength,data.thetaStart,data.thetaLength)}};var TorusGeometry=class _TorusGeometry extends BufferGeometry{constructor(radius=1,tube=.4,radialSegments=12,tubularSegments=48,arc=Math.PI*2,thetaStart=0,thetaLength=Math.PI*2){super(),this.type="TorusGeometry",this.parameters={radius,tube,radialSegments,tubularSegments,arc,thetaStart,thetaLength},radialSegments=Math.floor(radialSegments),tubularSegments=Math.floor(tubularSegments);let indices=[],vertices=[],normals=[],uvs=[],center=new Vector3,vertex19=new Vector3,normal=new Vector3;for(let j=0;j<=radialSegments;j++){let v=thetaStart+j/radialSegments*thetaLength;for(let i=0;i<=tubularSegments;i++){let u=i/tubularSegments*arc;vertex19.x=(radius+tube*Math.cos(v))*Math.cos(u),vertex19.y=(radius+tube*Math.cos(v))*Math.sin(u),vertex19.z=tube*Math.sin(v),vertices.push(vertex19.x,vertex19.y,vertex19.z),center.x=radius*Math.cos(u),center.y=radius*Math.sin(u),normal.subVectors(vertex19,center).normalize(),normals.push(normal.x,normal.y,normal.z),uvs.push(i/tubularSegments),uvs.push(j/radialSegments)}}for(let j=1;j<=radialSegments;j++)for(let i=1;i<=tubularSegments;i++){let a=(tubularSegments+1)*j+i-1,b=(tubularSegments+1)*(j-1)+i-1,c=(tubularSegments+1)*(j-1)+i,d=(tubularSegments+1)*j+i;indices.push(a,b,d),indices.push(b,c,d)}this.setIndex(indices),this.setAttribute("position",new Float32BufferAttribute(vertices,3)),this.setAttribute("normal",new Float32BufferAttribute(normals,3)),this.setAttribute("uv",new Float32BufferAttribute(uvs,2))}copy(source){return super.copy(source),this.parameters=Object.assign({},source.parameters),this}static fromJSON(data){return new _TorusGeometry(data.radius,data.tube,data.radialSegments,data.tubularSegments,data.arc,data.thetaStart,data.thetaLength)}};function cloneUniforms(src){let dst={};for(let u in src){dst[u]={};for(let p in src[u]){let property=src[u][p];if(isThreeObject(property))property.isRenderTargetTexture?(warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),dst[u][p]=null):dst[u][p]=property.clone();else if(Array.isArray(property))if(isThreeObject(property[0])){let clonedProperty=[];for(let i=0,l=property.length;i<l;i++)clonedProperty[i]=property[i].clone();dst[u][p]=clonedProperty}else dst[u][p]=property.slice();else dst[u][p]=property}}return dst}function mergeUniforms(uniforms){let merged={};for(let u=0;u<uniforms.length;u++){let tmp3=cloneUniforms(uniforms[u]);for(let p in tmp3)merged[p]=tmp3[p]}return merged}function isThreeObject(property){return property&&(property.isColor||property.isMatrix3||property.isMatrix4||property.isVector2||property.isVector3||property.isVector4||property.isTexture||property.isQuaternion)}function cloneUniformsGroups(src){let dst=[];for(let u=0;u<src.length;u++)dst.push(src[u].clone());return dst}function getUnlitUniformColorSpace(renderer){let currentRenderTarget=renderer.getRenderTarget();return currentRenderTarget===null?renderer.outputColorSpace:currentRenderTarget.isXRRenderTarget===!0?currentRenderTarget.texture.colorSpace:ColorManagement.workingColorSpace}var UniformsUtils={clone:cloneUniforms,merge:mergeUniforms};var default_vertex_glsl_default=`
void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}
`;var default_fragment_glsl_default=`
void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}
`;var ShaderMaterial=class extends Material{constructor(parameters){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=default_vertex_glsl_default,this.fragmentShader=default_fragment_glsl_default,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,parameters!==void 0&&this.setValues(parameters)}copy(source){return super.copy(source),this.fragmentShader=source.fragmentShader,this.vertexShader=source.vertexShader,this.uniforms=cloneUniforms(source.uniforms),this.uniformsGroups=cloneUniformsGroups(source.uniformsGroups),this.defines=Object.assign({},source.defines),this.wireframe=source.wireframe,this.wireframeLinewidth=source.wireframeLinewidth,this.fog=source.fog,this.lights=source.lights,this.clipping=source.clipping,this.extensions=Object.assign({},source.extensions),this.glslVersion=source.glslVersion,this.defaultAttributeValues=Object.assign({},source.defaultAttributeValues),this.index0AttributeName=source.index0AttributeName,this.uniformsNeedUpdate=source.uniformsNeedUpdate,this}toJSON(meta){let data=super.toJSON(meta);data.glslVersion=this.glslVersion,data.uniforms={};for(let name in this.uniforms){let value=this.uniforms[name].value;value&&value.isTexture?data.uniforms[name]={type:"t",value:value.toJSON(meta).uuid}:value&&value.isColor?data.uniforms[name]={type:"c",value:value.getHex()}:value&&value.isVector2?data.uniforms[name]={type:"v2",value:value.toArray()}:value&&value.isVector3?data.uniforms[name]={type:"v3",value:value.toArray()}:value&&value.isVector4?data.uniforms[name]={type:"v4",value:value.toArray()}:value&&value.isMatrix3?data.uniforms[name]={type:"m3",value:value.toArray()}:value&&value.isMatrix4?data.uniforms[name]={type:"m4",value:value.toArray()}:data.uniforms[name]={value}}Object.keys(this.defines).length>0&&(data.defines=this.defines),data.vertexShader=this.vertexShader,data.fragmentShader=this.fragmentShader,data.lights=this.lights,data.clipping=this.clipping;let extensions={};for(let key in this.extensions)this.extensions[key]===!0&&(extensions[key]=!0);return Object.keys(extensions).length>0&&(data.extensions=extensions),data}fromJSON(json,textures){if(super.fromJSON(json,textures),json.uniforms!==void 0)for(let name in json.uniforms){let uniform=json.uniforms[name];switch(this.uniforms[name]={},uniform.type){case"t":this.uniforms[name].value=textures[uniform.value]||null;break;case"c":this.uniforms[name].value=new Color().setHex(uniform.value);break;case"v2":this.uniforms[name].value=new Vector2().fromArray(uniform.value);break;case"v3":this.uniforms[name].value=new Vector3().fromArray(uniform.value);break;case"v4":this.uniforms[name].value=new Vector4().fromArray(uniform.value);break;case"m3":this.uniforms[name].value=new Matrix3().fromArray(uniform.value);break;case"m4":this.uniforms[name].value=new Matrix4().fromArray(uniform.value);break;default:this.uniforms[name].value=uniform.value}}if(json.defines!==void 0&&(this.defines=json.defines),json.vertexShader!==void 0&&(this.vertexShader=json.vertexShader),json.fragmentShader!==void 0&&(this.fragmentShader=json.fragmentShader),json.glslVersion!==void 0&&(this.glslVersion=json.glslVersion),json.extensions!==void 0)for(let key in json.extensions)this.extensions[key]=json.extensions[key];return json.lights!==void 0&&(this.lights=json.lights),json.clipping!==void 0&&(this.clipping=json.clipping),this}};var RawShaderMaterial=class extends ShaderMaterial{constructor(parameters){super(parameters),this.isRawShaderMaterial=!0,this.type="RawShaderMaterial"}};var MeshStandardMaterial=class extends Material{constructor(parameters){super(),this.isMeshStandardMaterial=!0,this.type="MeshStandardMaterial",this.defines={STANDARD:""},this.color=new Color(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new Color(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=TangentSpaceNormalMap,this.normalScale=new Vector2(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new Euler,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(parameters)}copy(source){return super.copy(source),this.defines={STANDARD:""},this.color.copy(source.color),this.roughness=source.roughness,this.metalness=source.metalness,this.map=source.map,this.lightMap=source.lightMap,this.lightMapIntensity=source.lightMapIntensity,this.aoMap=source.aoMap,this.aoMapIntensity=source.aoMapIntensity,this.emissive.copy(source.emissive),this.emissiveMap=source.emissiveMap,this.emissiveIntensity=source.emissiveIntensity,this.bumpMap=source.bumpMap,this.bumpScale=source.bumpScale,this.normalMap=source.normalMap,this.normalMapType=source.normalMapType,this.normalScale.copy(source.normalScale),this.displacementMap=source.displacementMap,this.displacementScale=source.displacementScale,this.displacementBias=source.displacementBias,this.roughnessMap=source.roughnessMap,this.metalnessMap=source.metalnessMap,this.alphaMap=source.alphaMap,this.envMap=source.envMap,this.envMapRotation.copy(source.envMapRotation),this.envMapIntensity=source.envMapIntensity,this.wireframe=source.wireframe,this.wireframeLinewidth=source.wireframeLinewidth,this.wireframeLinecap=source.wireframeLinecap,this.wireframeLinejoin=source.wireframeLinejoin,this.flatShading=source.flatShading,this.fog=source.fog,this}};var MeshDepthMaterial=class extends Material{constructor(parameters){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=BasicDepthPacking,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(parameters)}copy(source){return super.copy(source),this.depthPacking=source.depthPacking,this.map=source.map,this.alphaMap=source.alphaMap,this.displacementMap=source.displacementMap,this.displacementScale=source.displacementScale,this.displacementBias=source.displacementBias,this.wireframe=source.wireframe,this.wireframeLinewidth=source.wireframeLinewidth,this}};var MeshDistanceMaterial=class extends Material{constructor(parameters){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(parameters)}copy(source){return super.copy(source),this.map=source.map,this.alphaMap=source.alphaMap,this.displacementMap=source.displacementMap,this.displacementScale=source.displacementScale,this.displacementBias=source.displacementBias,this}};var Light=class extends Object3D{constructor(color,intensity=1){super(),this.isLight=!0,this.type="Light",this.color=new Color(color),this.intensity=intensity}copy(source,recursive){return super.copy(source,recursive),this.color.copy(source.color),this.intensity=source.intensity,this}toJSON(meta){let data=super.toJSON(meta);return data.object.color=this.color.getHex(),data.object.intensity=this.intensity,data}};var HemisphereLight=class extends Light{constructor(skyColor,groundColor,intensity){super(skyColor,intensity),this.isHemisphereLight=!0,this.type="HemisphereLight",this.position.copy(Object3D.DEFAULT_UP),this.updateMatrix(),this.groundColor=new Color(groundColor)}copy(source,recursive){return super.copy(source,recursive),this.groundColor.copy(source.groundColor),this}toJSON(meta){let data=super.toJSON(meta);return data.object.groundColor=this.groundColor.getHex(),data}};var _projScreenMatrix=new Matrix4,_lightPositionWorld=new Vector3,_lookTarget=new Vector3,LightShadow=class{constructor(camera){this.camera=camera,this.intensity=1,this.bias=0,this.biasNode=null,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new Vector2(512,512),this.mapType=UnsignedByteType,this.map=null,this.mapPass=null,this.matrix=new Matrix4,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new Frustum,this._frameExtents=new Vector2(1,1),this._viewportCount=1,this._viewports=[new Vector4(0,0,1,1)]}getViewportCount(){return this._viewportCount}getCamera(){return this.camera}getFrustum(){return this._frustum}updateMatrices(light){let shadowCamera=this.camera;_lightPositionWorld.setFromMatrixPosition(light.matrixWorld),shadowCamera.position.copy(_lightPositionWorld),_lookTarget.setFromMatrixPosition(light.target.matrixWorld),shadowCamera.lookAt(_lookTarget),shadowCamera.updateMatrixWorld(),this._updateMatrix(shadowCamera,this.matrix,this._frustum)}_updateMatrix(shadowCamera,shadowMatrix,frustum,viewport){_projScreenMatrix.multiplyMatrices(shadowCamera.projectionMatrix,shadowCamera.matrixWorldInverse),frustum.setFromProjectionMatrix(_projScreenMatrix,shadowCamera.coordinateSystem,shadowCamera.reversedDepth);let frameExtents=this._frameExtents,scaleX=viewport?viewport.z/frameExtents.x:1,scaleY=viewport?viewport.w/frameExtents.y:1,offsetX=viewport?viewport.x/frameExtents.x:0,offsetY=viewport?viewport.y/frameExtents.y:0;shadowCamera.coordinateSystem===WebGPUCoordinateSystem||shadowCamera.reversedDepth?shadowMatrix.set(.5*scaleX,0,0,.5*scaleX+offsetX,0,.5*scaleY,0,.5*scaleY+offsetY,0,0,1,0,0,0,0,1):shadowMatrix.set(.5*scaleX,0,0,.5*scaleX+offsetX,0,.5*scaleY,0,.5*scaleY+offsetY,0,0,.5,.5,0,0,0,1),shadowMatrix.multiply(_projScreenMatrix)}getViewport(viewportIndex){return this._viewports[viewportIndex]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(source){return this.camera=source.camera.clone(),this.intensity=source.intensity,this.bias=source.bias,this.radius=source.radius,this.autoUpdate=source.autoUpdate,this.needsUpdate=source.needsUpdate,this.normalBias=source.normalBias,this.blurSamples=source.blurSamples,this.mapSize.copy(source.mapSize),this.biasNode=source.biasNode,this}clone(){return new this.constructor().copy(this)}toJSON(){let object={};return object.intensity=this.intensity,object.bias=this.bias,object.normalBias=this.normalBias,object.radius=this.radius,object.blurSamples=this.blurSamples,object.mapSize=this.mapSize.toArray(),object.camera=this.camera.toJSON(!1).object,delete object.camera.matrix,object}};var _position2=new Vector3,_quaternion4=new Quaternion,_scale2=new Vector3,Camera=class extends Object3D{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new Matrix4,this.projectionMatrix=new Matrix4,this.projectionMatrixInverse=new Matrix4,this.coordinateSystem=WebGLCoordinateSystem,this._reversedDepth=!1}get reversedDepth(){return this._reversedDepth}copy(source,recursive){return super.copy(source,recursive),this.matrixWorldInverse.copy(source.matrixWorldInverse),this.projectionMatrix.copy(source.projectionMatrix),this.projectionMatrixInverse.copy(source.projectionMatrixInverse),this.coordinateSystem=source.coordinateSystem,this}getWorldDirection(target){return super.getWorldDirection(target).negate()}updateMatrixWorld(force){super.updateMatrixWorld(force),this.matrixWorld.decompose(_position2,_quaternion4,_scale2),_scale2.x===1&&_scale2.y===1&&_scale2.z===1?this.matrixWorldInverse.copy(this.matrixWorld).invert():this.matrixWorldInverse.compose(_position2,_quaternion4,_scale2.set(1,1,1)).invert()}updateWorldMatrix(updateParents,updateChildren,force=!1){super.updateWorldMatrix(updateParents,updateChildren,force),this.matrixWorld.decompose(_position2,_quaternion4,_scale2),_scale2.x===1&&_scale2.y===1&&_scale2.z===1?this.matrixWorldInverse.copy(this.matrixWorld).invert():this.matrixWorldInverse.compose(_position2,_quaternion4,_scale2.set(1,1,1)).invert()}clone(){return new this.constructor().copy(this)}};var _v32=new Vector3,_minTarget=new Vector2,_maxTarget=new Vector2,PerspectiveCamera=class extends Camera{constructor(fov2=50,aspect2=1,near=.1,far=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=fov2,this.zoom=1,this.near=near,this.far=far,this.focus=10,this.aspect=aspect2,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(source,recursive){return super.copy(source,recursive),this.fov=source.fov,this.zoom=source.zoom,this.near=source.near,this.far=source.far,this.focus=source.focus,this.aspect=source.aspect,this.view=source.view===null?null:Object.assign({},source.view),this.filmGauge=source.filmGauge,this.filmOffset=source.filmOffset,this}setFocalLength(focalLength){let vExtentSlope=.5*this.getFilmHeight()/focalLength;this.fov=RAD2DEG*2*Math.atan(vExtentSlope),this.updateProjectionMatrix()}getFocalLength(){let vExtentSlope=Math.tan(DEG2RAD*.5*this.fov);return .5*this.getFilmHeight()/vExtentSlope}getEffectiveFOV(){return RAD2DEG*2*Math.atan(Math.tan(DEG2RAD*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(distance,minTarget,maxTarget){_v32.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),minTarget.set(_v32.x,_v32.y).multiplyScalar(-distance/_v32.z),_v32.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),maxTarget.set(_v32.x,_v32.y).multiplyScalar(-distance/_v32.z)}getViewSize(distance,target){return this.getViewBounds(distance,_minTarget,_maxTarget),target.subVectors(_maxTarget,_minTarget)}setViewOffset(fullWidth,fullHeight,x,y,width,height){this.aspect=fullWidth/fullHeight,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=fullWidth,this.view.fullHeight=fullHeight,this.view.offsetX=x,this.view.offsetY=y,this.view.width=width,this.view.height=height,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let near=this.near,top=near*Math.tan(DEG2RAD*.5*this.fov)/this.zoom,height=2*top,width=this.aspect*height,left=-.5*width,view=this.view;if(this.view!==null&&this.view.enabled){let fullWidth=view.fullWidth,fullHeight=view.fullHeight;left+=view.offsetX*width/fullWidth,top-=view.offsetY*height/fullHeight,width*=view.width/fullWidth,height*=view.height/fullHeight}let skew=this.filmOffset;skew!==0&&(left+=near*skew/this.getFilmWidth()),this.projectionMatrix.makePerspective(left,left+width,top,top-height,near,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(meta){let data=super.toJSON(meta);return data.object.fov=this.fov,data.object.zoom=this.zoom,data.object.near=this.near,data.object.far=this.far,data.object.focus=this.focus,data.object.aspect=this.aspect,this.view!==null&&(data.object.view=Object.assign({},this.view)),data.object.filmGauge=this.filmGauge,data.object.filmOffset=this.filmOffset,data}};var OrthographicCamera=class extends Camera{constructor(left=-1,right=1,top=1,bottom=-1,near=.1,far=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=left,this.right=right,this.top=top,this.bottom=bottom,this.near=near,this.far=far,this.updateProjectionMatrix()}copy(source,recursive){return super.copy(source,recursive),this.left=source.left,this.right=source.right,this.top=source.top,this.bottom=source.bottom,this.near=source.near,this.far=source.far,this.zoom=source.zoom,this.view=source.view===null?null:Object.assign({},source.view),this}setViewOffset(fullWidth,fullHeight,x,y,width,height){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=fullWidth,this.view.fullHeight=fullHeight,this.view.offsetX=x,this.view.offsetY=y,this.view.width=width,this.view.height=height,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let dx=(this.right-this.left)/(2*this.zoom),dy=(this.top-this.bottom)/(2*this.zoom),cx=(this.right+this.left)/2,cy=(this.top+this.bottom)/2,left=cx-dx,right=cx+dx,top=cy+dy,bottom=cy-dy;if(this.view!==null&&this.view.enabled){let scaleW=(this.right-this.left)/this.view.fullWidth/this.zoom,scaleH=(this.top-this.bottom)/this.view.fullHeight/this.zoom;left+=scaleW*this.view.offsetX,right=left+scaleW*this.view.width,top-=scaleH*this.view.offsetY,bottom=top-scaleH*this.view.height}this.projectionMatrix.makeOrthographic(left,right,top,bottom,this.near,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(meta){let data=super.toJSON(meta);return data.object.zoom=this.zoom,data.object.left=this.left,data.object.right=this.right,data.object.top=this.top,data.object.bottom=this.bottom,data.object.near=this.near,data.object.far=this.far,this.view!==null&&(data.object.view=Object.assign({},this.view)),data}};var DirectionalLightShadow=class extends LightShadow{constructor(){super(new OrthographicCamera(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}};var DirectionalLight=class extends Light{constructor(color,intensity){super(color,intensity),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(Object3D.DEFAULT_UP),this.updateMatrix(),this.target=new Object3D,this.shadow=new DirectionalLightShadow}dispose(){super.dispose(),this.shadow.dispose()}copy(source){return super.copy(source),this.target=source.target.clone(),this.shadow=source.shadow.clone(),this}toJSON(meta){let data=super.toJSON(meta);return data.object.shadow=this.shadow.toJSON(),data.object.target=this.target.uuid,data}};var fov=-90,aspect=1,CubeCamera=class extends Object3D{constructor(near,far,renderTarget){super(),this.type="CubeCamera",this.renderTarget=renderTarget,this.coordinateSystem=null,this.activeMipmapLevel=0;let cameraPX=new PerspectiveCamera(fov,aspect,near,far);cameraPX.layers=this.layers,this.add(cameraPX);let cameraNX=new PerspectiveCamera(fov,aspect,near,far);cameraNX.layers=this.layers,this.add(cameraNX);let cameraPY=new PerspectiveCamera(fov,aspect,near,far);cameraPY.layers=this.layers,this.add(cameraPY);let cameraNY=new PerspectiveCamera(fov,aspect,near,far);cameraNY.layers=this.layers,this.add(cameraNY);let cameraPZ=new PerspectiveCamera(fov,aspect,near,far);cameraPZ.layers=this.layers,this.add(cameraPZ);let cameraNZ=new PerspectiveCamera(fov,aspect,near,far);cameraNZ.layers=this.layers,this.add(cameraNZ)}updateCoordinateSystem(){let coordinateSystem=this.coordinateSystem,cameras=this.children.concat(),[cameraPX,cameraNX,cameraPY,cameraNY,cameraPZ,cameraNZ]=cameras;for(let camera of cameras)this.remove(camera);if(coordinateSystem===WebGLCoordinateSystem)cameraPX.up.set(0,1,0),cameraPX.lookAt(1,0,0),cameraNX.up.set(0,1,0),cameraNX.lookAt(-1,0,0),cameraPY.up.set(0,0,-1),cameraPY.lookAt(0,1,0),cameraNY.up.set(0,0,1),cameraNY.lookAt(0,-1,0),cameraPZ.up.set(0,1,0),cameraPZ.lookAt(0,0,1),cameraNZ.up.set(0,1,0),cameraNZ.lookAt(0,0,-1);else if(coordinateSystem===WebGPUCoordinateSystem)cameraPX.up.set(0,-1,0),cameraPX.lookAt(-1,0,0),cameraNX.up.set(0,-1,0),cameraNX.lookAt(1,0,0),cameraPY.up.set(0,0,1),cameraPY.lookAt(0,1,0),cameraNY.up.set(0,0,-1),cameraNY.lookAt(0,-1,0),cameraPZ.up.set(0,-1,0),cameraPZ.lookAt(0,0,1),cameraNZ.up.set(0,-1,0),cameraNZ.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+coordinateSystem);for(let camera of cameras)this.add(camera),camera.updateMatrixWorld()}update(renderer,scene){this.parent===null&&this.updateMatrixWorld();let{renderTarget,activeMipmapLevel}=this;this.coordinateSystem!==renderer.coordinateSystem&&(this.coordinateSystem=renderer.coordinateSystem,this.updateCoordinateSystem());let[cameraPX,cameraNX,cameraPY,cameraNY,cameraPZ,cameraNZ]=this.children,currentRenderTarget=renderer.getRenderTarget(),currentActiveCubeFace=renderer.getActiveCubeFace(),currentActiveMipmapLevel=renderer.getActiveMipmapLevel(),currentXrEnabled=renderer.xr.enabled;renderer.xr.enabled=!1;let generateMipmaps=renderTarget.texture.generateMipmaps;renderTarget.texture.generateMipmaps=!1;let reversedDepthBuffer=!1;renderer.isWebGLRenderer===!0?reversedDepthBuffer=renderer.state.buffers.depth.getReversed():reversedDepthBuffer=renderer.reversedDepthBuffer,renderer.setRenderTarget(renderTarget,0,activeMipmapLevel),reversedDepthBuffer&&renderer.autoClear===!1&&renderer.clearDepth(),renderer.render(scene,cameraPX),renderer.setRenderTarget(renderTarget,1,activeMipmapLevel),reversedDepthBuffer&&renderer.autoClear===!1&&renderer.clearDepth(),renderer.render(scene,cameraNX),renderer.setRenderTarget(renderTarget,2,activeMipmapLevel),reversedDepthBuffer&&renderer.autoClear===!1&&renderer.clearDepth(),renderer.render(scene,cameraPY),renderer.setRenderTarget(renderTarget,3,activeMipmapLevel),reversedDepthBuffer&&renderer.autoClear===!1&&renderer.clearDepth(),renderer.render(scene,cameraNY),renderer.setRenderTarget(renderTarget,4,activeMipmapLevel),reversedDepthBuffer&&renderer.autoClear===!1&&renderer.clearDepth(),renderer.render(scene,cameraPZ),renderTarget.texture.generateMipmaps=generateMipmaps,renderer.setRenderTarget(renderTarget,5,activeMipmapLevel),reversedDepthBuffer&&renderer.autoClear===!1&&renderer.clearDepth(),renderer.render(scene,cameraNZ),renderer.setRenderTarget(currentRenderTarget,currentActiveCubeFace,currentActiveMipmapLevel),renderer.xr.enabled=currentXrEnabled,renderTarget.texture.needsPMREMUpdate=!0}};var ArrayCamera=class extends PerspectiveCamera{constructor(array=[]){super(),this.isArrayCamera=!0,this.isMultiViewCamera=!1,this.cameras=array}};var _matrix2=new Matrix4,Raycaster=class{constructor(origin,direction,near=0,far=1/0){this.ray=new Ray(origin,direction),this.near=near,this.far=far,this.camera=null,this.layers=new Layers,this.params={Mesh:{},Line:{threshold:1},LOD:{},Points:{threshold:1},Sprite:{}}}set(origin,direction){this.ray.set(origin,direction)}setFromCamera(coords,camera){camera.isPerspectiveCamera?(this.ray.origin.setFromMatrixPosition(camera.matrixWorld),this.ray.direction.set(coords.x,coords.y,.5).unproject(camera).sub(this.ray.origin).normalize(),this.camera=camera):camera.isOrthographicCamera?(this.ray.origin.set(coords.x,coords.y,camera.projectionMatrix.elements[14]).unproject(camera),this.ray.direction.set(0,0,-1).transformDirection(camera.matrixWorld),this.camera=camera):error("Raycaster: Unsupported camera type: "+camera.type)}setFromXRController(controller){return _matrix2.identity().extractRotation(controller.matrixWorld),this.ray.origin.setFromMatrixPosition(controller.matrixWorld),this.ray.direction.set(0,0,-1).applyMatrix4(_matrix2),this}intersectObject(object,recursive=!0,intersects2=[]){return intersect(object,this,intersects2,recursive),intersects2.sort(ascSort),intersects2}intersectObjects(objects,recursive=!0,intersects2=[]){for(let i=0,l=objects.length;i<l;i++)intersect(objects[i],this,intersects2,recursive);return intersects2.sort(ascSort),intersects2}};function ascSort(a,b){return a.distance-b.distance}function intersect(object,raycaster,intersects2,recursive){let propagate=!0;if(object.layers.test(raycaster.layers)&&object.raycast(raycaster,intersects2)===!1&&(propagate=!1),propagate===!0&&recursive===!0){let children=object.children;for(let i=0,l=children.length;i<l;i++)intersect(children[i],raycaster,intersects2,!0)}}var Spherical=class{constructor(radius=1,phi=0,theta=0){this.radius=radius,this.phi=phi,this.theta=theta}set(radius,phi,theta){return this.radius=radius,this.phi=phi,this.theta=theta,this}copy(other){return this.radius=other.radius,this.phi=other.phi,this.theta=other.theta,this}makeSafe(){return this.phi=clamp(this.phi,1e-6,Math.PI-1e-6),this}setFromVector3(v){return this.setFromCartesianCoords(v.x,v.y,v.z)}setFromCartesianCoords(x,y,z){return this.radius=Math.sqrt(x*x+y*y+z*z),this.radius===0?(this.theta=0,this.phi=0):(this.theta=Math.atan2(x,z),this.phi=Math.acos(clamp(y/this.radius,-1,1))),this}clone(){return new this.constructor().copy(this)}};var _box4=new Box3,BoxHelper=class extends LineSegments{constructor(object,color=16776960){let indices=new Uint16Array([0,1,1,2,2,3,3,0,4,5,5,6,6,7,7,4,0,4,1,5,2,6,3,7]),positions=new Float32Array(24),geometry=new BufferGeometry;geometry.setIndex(new BufferAttribute(indices,1)),geometry.setAttribute("position",new BufferAttribute(positions,3)),super(geometry,new LineBasicMaterial({color,toneMapped:!1})),this.object=object,this.type="BoxHelper",this.matrixAutoUpdate=!1,this.update()}update(){if(this.object!==void 0&&_box4.setFromObject(this.object),_box4.isEmpty())return;let min=_box4.min,max=_box4.max,position=this.geometry.attributes.position,array=position.array;array[0]=max.x,array[1]=max.y,array[2]=max.z,array[3]=min.x,array[4]=max.y,array[5]=max.z,array[6]=min.x,array[7]=min.y,array[8]=max.z,array[9]=max.x,array[10]=min.y,array[11]=max.z,array[12]=max.x,array[13]=max.y,array[14]=min.z,array[15]=min.x,array[16]=max.y,array[17]=min.z,array[18]=min.x,array[19]=min.y,array[20]=min.z,array[21]=max.x,array[22]=min.y,array[23]=min.z,position.needsUpdate=!0,this.geometry.computeBoundingSphere()}setFromObject(object){return this.object=object,this.update(),this}copy(source,recursive){return super.copy(source,recursive),this.object=source.object,this}dispose(){super.dispose(),this.geometry.dispose(),this.material.dispose()}};var Controls=class extends EventDispatcher{constructor(object,domElement=null){super(),this.object=object,this.domElement=domElement,this.enabled=!0,this.state=-1,this.keys={},this.mouseButtons={LEFT:null,MIDDLE:null,RIGHT:null},this.touches={ONE:null,TWO:null}}connect(element){this.domElement!==null&&this.disconnect(),this.domElement=element}disconnect(){}dispose(){}update(){}};function getByteLength(width,height,format,type){let typeByteLength=getTextureTypeByteLength(type);switch(format){case AlphaFormat:return width*height;case RedFormat:return width*height/typeByteLength.components*typeByteLength.byteLength;case RedIntegerFormat:return width*height/typeByteLength.components*typeByteLength.byteLength;case RGFormat:return width*height*2/typeByteLength.components*typeByteLength.byteLength;case RGIntegerFormat:return width*height*2/typeByteLength.components*typeByteLength.byteLength;case RGBFormat:return width*height*3/typeByteLength.components*typeByteLength.byteLength;case RGBAFormat:return width*height*4/typeByteLength.components*typeByteLength.byteLength;case RGBAIntegerFormat:return width*height*4/typeByteLength.components*typeByteLength.byteLength;case RGB_S3TC_DXT1_Format:case RGBA_S3TC_DXT1_Format:return Math.floor((width+3)/4)*Math.floor((height+3)/4)*8;case RGBA_S3TC_DXT3_Format:case RGBA_S3TC_DXT5_Format:return Math.floor((width+3)/4)*Math.floor((height+3)/4)*16;case RGB_PVRTC_2BPPV1_Format:case RGBA_PVRTC_2BPPV1_Format:return Math.max(width,16)*Math.max(height,8)/4;case RGB_PVRTC_4BPPV1_Format:case RGBA_PVRTC_4BPPV1_Format:return Math.max(width,8)*Math.max(height,8)/2;case RGB_ETC1_Format:case RGB_ETC2_Format:case R11_EAC_Format:case SIGNED_R11_EAC_Format:return Math.floor((width+3)/4)*Math.floor((height+3)/4)*8;case RGBA_ETC2_EAC_Format:case RG11_EAC_Format:case SIGNED_RG11_EAC_Format:return Math.floor((width+3)/4)*Math.floor((height+3)/4)*16;case RGBA_ASTC_4x4_Format:return Math.floor((width+3)/4)*Math.floor((height+3)/4)*16;case RGBA_ASTC_5x4_Format:return Math.floor((width+4)/5)*Math.floor((height+3)/4)*16;case RGBA_ASTC_5x5_Format:return Math.floor((width+4)/5)*Math.floor((height+4)/5)*16;case RGBA_ASTC_6x5_Format:return Math.floor((width+5)/6)*Math.floor((height+4)/5)*16;case RGBA_ASTC_6x6_Format:return Math.floor((width+5)/6)*Math.floor((height+5)/6)*16;case RGBA_ASTC_8x5_Format:return Math.floor((width+7)/8)*Math.floor((height+4)/5)*16;case RGBA_ASTC_8x6_Format:return Math.floor((width+7)/8)*Math.floor((height+5)/6)*16;case RGBA_ASTC_8x8_Format:return Math.floor((width+7)/8)*Math.floor((height+7)/8)*16;case RGBA_ASTC_10x5_Format:return Math.floor((width+9)/10)*Math.floor((height+4)/5)*16;case RGBA_ASTC_10x6_Format:return Math.floor((width+9)/10)*Math.floor((height+5)/6)*16;case RGBA_ASTC_10x8_Format:return Math.floor((width+9)/10)*Math.floor((height+7)/8)*16;case RGBA_ASTC_10x10_Format:return Math.floor((width+9)/10)*Math.floor((height+9)/10)*16;case RGBA_ASTC_12x10_Format:return Math.floor((width+11)/12)*Math.floor((height+9)/10)*16;case RGBA_ASTC_12x12_Format:return Math.floor((width+11)/12)*Math.floor((height+11)/12)*16;case RGBA_BPTC_Format:case RGB_BPTC_SIGNED_Format:case RGB_BPTC_UNSIGNED_Format:return Math.ceil(width/4)*Math.ceil(height/4)*16;case RED_RGTC1_Format:case SIGNED_RED_RGTC1_Format:return Math.ceil(width/4)*Math.ceil(height/4)*8;case RED_GREEN_RGTC2_Format:case SIGNED_RED_GREEN_RGTC2_Format:return Math.ceil(width/4)*Math.ceil(height/4)*16}throw new Error(`Unable to determine texture byte length for ${format} format.`)}function getTextureTypeByteLength(type){switch(type){case UnsignedByteType:case ByteType:return{byteLength:1,components:1};case UnsignedShortType:case ShortType:case HalfFloatType:return{byteLength:2,components:1};case UnsignedShort4444Type:case UnsignedShort5551Type:return{byteLength:2,components:4};case UnsignedIntType:case IntType:case FloatType:return{byteLength:4,components:1};case UnsignedInt5999Type:case UnsignedInt101111Type:return{byteLength:4,components:3}}throw new Error(`THREE.TextureUtils: Unknown texture type ${type}.`)}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:"186"}}));typeof window<"u"&&(window.__THREE__?warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__="186");function WebGLAnimation(){let context=null,isAnimating=!1,animationLoop=null,requestId=null;function onAnimationFrame(time,frame){requestId=context.requestAnimationFrame(onAnimationFrame),animationLoop(time,frame)}return{start:function(){isAnimating!==!0&&animationLoop!==null&&context!==null&&(requestId=context.requestAnimationFrame(onAnimationFrame),isAnimating=!0)},stop:function(){context!==null&&context.cancelAnimationFrame(requestId),isAnimating=!1},setAnimationLoop:function(callback){animationLoop=callback},setContext:function(value){context=value}}}function WebGLAttributes(gl){let buffers=new WeakMap;function createBuffer(attribute,bufferType){let array=attribute.array,usage=attribute.usage,size=array.byteLength,buffer=gl.createBuffer();gl.bindBuffer(bufferType,buffer),gl.bufferData(bufferType,array,usage),attribute.onUploadCallback();let type;if(array instanceof Float32Array)type=gl.FLOAT;else if(typeof Float16Array<"u"&&array instanceof Float16Array)type=gl.HALF_FLOAT;else if(array instanceof Uint16Array)attribute.isFloat16BufferAttribute?type=gl.HALF_FLOAT:type=gl.UNSIGNED_SHORT;else if(array instanceof Int16Array)type=gl.SHORT;else if(array instanceof Uint32Array)type=gl.UNSIGNED_INT;else if(array instanceof Int32Array)type=gl.INT;else if(array instanceof Int8Array)type=gl.BYTE;else if(array instanceof Uint8Array)type=gl.UNSIGNED_BYTE;else if(array instanceof Uint8ClampedArray)type=gl.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+array);return{buffer,type,bytesPerElement:array.BYTES_PER_ELEMENT,version:attribute.version,size}}function updateBuffer(buffer,attribute,bufferType){let array=attribute.array,updateRanges=attribute.updateRanges;if(gl.bindBuffer(bufferType,buffer),updateRanges.length===0)gl.bufferSubData(bufferType,0,array);else{updateRanges.sort((a,b)=>a.start-b.start);let mergeIndex=0;for(let i=1;i<updateRanges.length;i++){let previousRange=updateRanges[mergeIndex],range=updateRanges[i];range.start<=previousRange.start+previousRange.count+1?previousRange.count=Math.max(previousRange.count,range.start+range.count-previousRange.start):(++mergeIndex,updateRanges[mergeIndex]=range)}updateRanges.length=mergeIndex+1;for(let i=0,l=updateRanges.length;i<l;i++){let range=updateRanges[i];gl.bufferSubData(bufferType,range.start*array.BYTES_PER_ELEMENT,array,range.start,range.count)}attribute.clearUpdateRanges()}attribute.onUploadCallback()}function get(attribute){return attribute.isInterleavedBufferAttribute&&(attribute=attribute.data),buffers.get(attribute)}function remove(attribute){attribute.isInterleavedBufferAttribute&&(attribute=attribute.data);let data=buffers.get(attribute);data&&(gl.deleteBuffer(data.buffer),buffers.delete(attribute))}function update(attribute,bufferType){if(attribute.isInterleavedBufferAttribute&&(attribute=attribute.data),attribute.isGLBufferAttribute){let cached=buffers.get(attribute);(!cached||cached.version<attribute.version)&&buffers.set(attribute,{buffer:attribute.buffer,type:attribute.type,bytesPerElement:attribute.elementSize,version:attribute.version});return}let data=buffers.get(attribute);if(data===void 0)buffers.set(attribute,createBuffer(attribute,bufferType));else if(data.version<attribute.version){if(data.size!==attribute.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");updateBuffer(data.buffer,attribute,bufferType),data.version=attribute.version}}return{get,remove,update}}var alphahash_fragment_glsl_default=`
#ifdef USE_ALPHAHASH

	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;

#endif
`;var alphahash_pars_fragment_glsl_default=`
#ifdef USE_ALPHAHASH

	/**
	 * See: https://casual-effects.com/research/Wyman2017Hashed/index.html
	 */

	const float ALPHA_HASH_SCALE = 0.05; // Derived from trials only, and may be changed.

	float hash2D( vec2 value ) {

		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );

	}

	float hash3D( vec3 value ) {

		return hash2D( vec2( hash2D( value.xy ), value.z ) );

	}

	float getAlphaHashThreshold( vec3 position ) {

		// Find the discretized derivatives of our coordinates
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );

		// Find two nearest log-discretized noise scales
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);

		// Compute alpha thresholds at our two noise scales
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);

		// Factor to interpolate lerp with
		float lerpFactor = fract( log2( pixScale ) );

		// Interpolate alpha threshold from noise at two scales
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;

		// Pass into CDF to compute uniformly distrib threshold
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);

		// Find our final, uniformly distributed alpha threshold (\u03B1\u03C4)
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;

		// Avoids \u03B1\u03C4 == 0. Could also do \u03B1\u03C4 =1-\u03B1\u03C4
		return clamp( threshold , 1.0e-6, 1.0 );

	}

#endif
`;var alphamap_fragment_glsl_default=`
#ifdef USE_ALPHAMAP

	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;

#endif
`;var alphamap_pars_fragment_glsl_default=`
#ifdef USE_ALPHAMAP

	uniform sampler2D alphaMap;

#endif
`;var alphatest_fragment_glsl_default=`
#ifdef USE_ALPHATEST

	#ifdef ALPHA_TO_COVERAGE

	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;

	#else

	if ( diffuseColor.a < alphaTest ) discard;

	#endif

#endif
`;var alphatest_pars_fragment_glsl_default=`
#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif
`;var aomap_fragment_glsl_default=`
#ifdef USE_AOMAP

	// reads channel R, compatible with a combined OcclusionRoughnessMetallic (RGB) texture
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;

	reflectedLight.indirectDiffuse *= ambientOcclusion;

	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif

	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif

	#if defined( USE_ENVMAP ) && defined( STANDARD )

		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );

		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );

	#endif

#endif
`;var aomap_pars_fragment_glsl_default=`
#ifdef USE_AOMAP

	uniform sampler2D aoMap;
	uniform float aoMapIntensity;

#endif
`;var batching_pars_vertex_glsl_default=`
#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif

	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {

		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );

	}

	float getIndirectIndex( const in int i ) {

		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );

	}

#endif

#ifdef USE_BATCHING_COLOR

	uniform sampler2D batchingColorTexture;
	vec4 getBatchingColor( const in float i ) {

		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 );

	}

#endif
`;var batching_vertex_glsl_default=`
#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif
`;var begin_vertex_glsl_default=`
vec3 transformed = vec3( position );

#ifdef USE_ALPHAHASH

	vPosition = vec3( position );

#endif
`;var beginnormal_vertex_glsl_default=`
vec3 objectNormal = vec3( normal );

#ifdef USE_TANGENT

	vec3 objectTangent = vec3( tangent.xyz );

#endif
`;var bsdfs_glsl_default=`

float G_BlinnPhong_Implicit( /* const in float dotNL, const in float dotNV */ ) {

	// geometry term is (n dot l)(n dot v) / 4(n dot l)(n dot v)
	return 0.25;

}

float D_BlinnPhong( const in float shininess, const in float dotNH ) {

	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );

}

vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {

	vec3 halfDir = normalize( lightDir + viewDir );

	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );

	vec3 F = F_Schlick( specularColor, 1.0, dotVH );

	float G = G_BlinnPhong_Implicit( /* dotNL, dotNV */ );

	float D = D_BlinnPhong( shininess, dotNH );

	return F * ( G * D );

} // validated

`;var iridescence_fragment_glsl_default=`

#ifdef USE_IRIDESCENCE

	// XYZ to linear-sRGB color space
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);

	// Assume air interface for top
	// Note: We don't handle the case fresnel0 == 1
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {

		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );

	}

	// Conversion FO/IOR
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {

		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );

	}

	// ior is a value between 1.0 and 3.0. 1.0 is air interface
	float IorToFresnel0( float transmittedIor, float incidentIor ) {

		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));

	}

	// Fresnel equations for dielectric/dielectric interfaces.
	// Ref: https://belcour.github.io/blog/research/2017/05/01/brdf-thin-film.html
	// Evaluation XYZ sensitivity curves in Fourier space
	vec3 evalSensitivity( float OPD, vec3 shift ) {

		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );

		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;

		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;

	}

	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {

		vec3 I;

		// Force iridescenceIOR -> outsideIOR when thinFilmThickness -> 0.0
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		// Evaluate the cosTheta on the base layer (Snell law)
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );

		// Handle TIR:
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {

			return vec3( 1.0 );

		}

		float cosTheta2 = sqrt( cosTheta2Sq );

		// First interface
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;

		// Second interface
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) ); // guard against 1.0
		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;

		// Phase shift
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;

		// Compound terms
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );

		// Reflectance term for m = 0 (DC term amplitude)
		vec3 C0 = R12 + Rs;
		I = C0;

		// Reflectance term for m > 0 (pairs of diracs)
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {

			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;

		}

		// Since out of gamut colors might be produced, negative color values are clamped to 0.
		return max( I, vec3( 0.0 ) );

	}

#endif

`;var bumpmap_pars_fragment_glsl_default=`
#ifdef USE_BUMPMAP

	uniform sampler2D bumpMap;
	uniform float bumpScale;

	// Bump Mapping Unparametrized Surfaces on the GPU by Morten S. Mikkelsen
	// https://mmikk.github.io/papers3d/mm_sfgrad_bump.pdf

	// Evaluate the derivative of the height w.r.t. screen-space using forward differencing (listing 2)

	vec2 dHdxy_fwd() {

		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );

		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;

		return vec2( dBx, dBy );

	}

	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {

		// normalize is done to ensure that the bump map looks the same regardless of the texture's scale
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm; // normalized

		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );

		float fDet = dot( vSigmaX, R1 ) * faceDirection;

		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );

	}

#endif
`;var clipping_planes_fragment_glsl_default=`
#if NUM_CLIPPING_PLANES > 0

	vec4 plane;

	#ifdef ALPHA_TO_COVERAGE

		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;

		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {

			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );

			if ( clipOpacity == 0.0 ) discard;

		}
		#pragma unroll_loop_end

		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES

			float unionClipOpacity = 1.0;

			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {

				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );

			}
			#pragma unroll_loop_end

			clipOpacity *= 1.0 - unionClipOpacity;

		#endif

		diffuseColor.a *= clipOpacity;

		if ( diffuseColor.a == 0.0 ) discard;

	#else

		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {

			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;

		}
		#pragma unroll_loop_end

		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES

			bool clipped = true;

			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {

				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;

			}
			#pragma unroll_loop_end

			if ( clipped ) discard;

		#endif

	#endif

#endif
`;var clipping_planes_pars_fragment_glsl_default=`
#if NUM_CLIPPING_PLANES > 0

	varying vec3 vClipPosition;

	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];

#endif
`;var clipping_planes_pars_vertex_glsl_default=`
#if NUM_CLIPPING_PLANES > 0

	varying vec3 vClipPosition;

#endif
`;var clipping_planes_vertex_glsl_default=`
#if NUM_CLIPPING_PLANES > 0

	vClipPosition = - mvPosition.xyz;

#endif
`;var color_fragment_glsl_default=`
#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )

	diffuseColor *= vColor;

#endif
`;var color_pars_fragment_glsl_default=`
#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA )

	varying vec4 vColor;

#endif
`;var color_pars_vertex_glsl_default=`
#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )

	varying vec4 vColor;

#endif
`;var color_vertex_glsl_default=`
#if defined( USE_COLOR ) || defined( USE_COLOR_ALPHA ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )

	vColor = vec4( 1.0 );

#endif

#ifdef USE_COLOR_ALPHA

	vColor *= color;

#elif defined( USE_COLOR )

	vColor.rgb *= color;

#endif

#ifdef USE_INSTANCING_COLOR

	vColor.rgb *= instanceColor.rgb;

#endif

#ifdef USE_BATCHING_COLOR

	vColor *= getBatchingColor( getIndirectIndex( gl_DrawID ) );

#endif
`;var common_glsl_default=`
#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6

#ifndef saturate
// <tonemapping_pars_fragment> may have defined saturate() already
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )

float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }

// expects values in the range of [0,1]x[0,1], returns values in the [0,1] range.
// do not collapse into a single function per: http://byteblacksmith.com/improvements-to-the-canonical-one-liner-glsl-rand-for-opengl-es-2-0/
highp float rand( const in vec2 uv ) {

	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );

	return fract( sin( sn ) * c );

}

#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif

struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};

struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};

#ifdef USE_ALPHAHASH

	varying vec3 vPosition;

#endif

vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

}

#define inverseTransformDirection transformDirectionByInverseViewMatrix // @deprecated r185

vec3 transformNormalByInverseViewMatrix( in vec3 normal, in mat4 viewMatrix ) {

	// upper-left 3x3 of view matrix is assumed to be orthogonal

	return normalize( ( vec4( normal, 0.0 ) * viewMatrix ).xyz );

}

vec3 transformDirectionByInverseViewMatrix( in vec3 dir, in mat4 viewMatrix ) {

	// upper-left 3x3 of view matrix is assumed to be orthogonal

	return normalize( ( vec4( dir, 0.0 ) * viewMatrix ).xyz );

}

bool isPerspectiveMatrix( mat4 m ) {

	return m[ 2 ][ 3 ] == - 1.0;

}

vec2 equirectUv( in vec3 dir ) {

	// dir is assumed to be unit length

	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;

	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;

	return vec2( u, v );

}

vec3 BRDF_Lambert( const in vec3 diffuseColor ) {

	return RECIPROCAL_PI * diffuseColor;

} // validated

vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {

	// Original approximation by Christophe Schlick '94
	// float fresnel = pow( 1.0 - dotVH, 5.0 );

	// Optimized variant (presented by Epic at SIGGRAPH '13)
	// https://cdn2.unrealengine.com/Resources/files/2013SiggraphPresentationsNotes-26915738.pdf
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );

	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );

} // validated

float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {

	// Original approximation by Christophe Schlick '94
	// float fresnel = pow( 1.0 - dotVH, 5.0 );

	// Optimized variant (presented by Epic at SIGGRAPH '13)
	// https://cdn2.unrealengine.com/Resources/files/2013SiggraphPresentationsNotes-26915738.pdf
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );

	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );

} // validated
`;var cube_uv_reflection_fragment_glsl_default=`
#ifdef ENVMAP_TYPE_CUBE_UV

	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0

	// These shader functions convert between the UV coordinates of a single face of
	// a cubemap, the 0-5 integer index of a cube face, and the direction vector for
	// sampling a textureCube (not generally normalized ).

	float getFace( vec3 direction ) {

		vec3 absDirection = abs( direction );

		float face = - 1.0;

		if ( absDirection.x > absDirection.z ) {

			if ( absDirection.x > absDirection.y )

				face = direction.x > 0.0 ? 0.0 : 3.0;

			else

				face = direction.y > 0.0 ? 1.0 : 4.0;

		} else {

			if ( absDirection.z > absDirection.y )

				face = direction.z > 0.0 ? 2.0 : 5.0;

			else

				face = direction.y > 0.0 ? 1.0 : 4.0;

		}

		return face;

	}

	// RH coordinate system; PMREM face-indexing convention
	vec2 getUV( vec3 direction, float face ) {

		vec2 uv;

		if ( face == 0.0 ) {

			uv = vec2( direction.z, direction.y ) / abs( direction.x ); // pos x

		} else if ( face == 1.0 ) {

			uv = vec2( - direction.x, - direction.z ) / abs( direction.y ); // pos y

		} else if ( face == 2.0 ) {

			uv = vec2( - direction.x, direction.y ) / abs( direction.z ); // pos z

		} else if ( face == 3.0 ) {

			uv = vec2( - direction.z, direction.y ) / abs( direction.x ); // neg x

		} else if ( face == 4.0 ) {

			uv = vec2( - direction.x, direction.z ) / abs( direction.y ); // neg y

		} else {

			uv = vec2( direction.x, direction.y ) / abs( direction.z ); // neg z

		}

		return 0.5 * ( uv + 1.0 );

	}

	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {

		float face = getFace( direction );

		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );

		mipInt = max( mipInt, cubeUV_minMipLevel );

		float faceSize = exp2( mipInt );

		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0; // #25071

		if ( face > 2.0 ) {

			uv.y += faceSize;

			face -= 3.0;

		}

		uv.x += face * faceSize;

		uv.x += filterInt * 3.0 * cubeUV_minTileSize;

		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );

		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;

		#ifdef texture2DGradEXT

			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb; // disable anisotropic filtering

		#else

			return texture2D( envMap, uv ).rgb;

		#endif

	}

	// These defines must match with PMREMGenerator

	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0

	float roughnessToMip( float roughness ) {

		float mip = 0.0;

		if ( roughness >= cubeUV_r1 ) {

			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;

		} else if ( roughness >= cubeUV_r4 ) {

			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;

		} else if ( roughness >= cubeUV_r5 ) {

			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;

		} else if ( roughness >= cubeUV_r6 ) {

			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;

		} else {

			mip = - 2.0 * log2( 1.16 * roughness ); // 1.16 = 1.79^0.25
		}

		return mip;

	}

	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {

		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );

		float mipF = fract( mip );

		float mipInt = floor( mip );

		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );

		if ( mipF == 0.0 ) {

			return vec4( color0, 1.0 );

		} else {

			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );

			return vec4( mix( color0, color1, mipF ), 1.0 );

		}

	}

#endif
`;var defaultnormal_vertex_glsl_default=`

vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT

	vec3 transformedTangent = objectTangent;

#endif

#ifdef USE_BATCHING

	// this is in lieu of a per-instance normal-matrix
	// non-uniform scaling in the instance matrix is supported
	// shear transforms are not supported

	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;

	#ifdef USE_TANGENT

		transformedTangent = bm * transformedTangent;

	#endif

#endif

#ifdef USE_INSTANCING

	// this is in lieu of a per-instance normal-matrix
	// non-uniform scaling in the instance matrix is supported
	// shear transforms are not supported

	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;

	#ifdef USE_TANGENT

		transformedTangent = im * transformedTangent;

	#endif

#endif

transformedNormal = normalMatrix * transformedNormal;

#ifdef FLIP_SIDED

	transformedNormal = - transformedNormal;

#endif

#ifdef USE_TANGENT

	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;

#endif
`;var displacementmap_pars_vertex_glsl_default=`
#ifdef USE_DISPLACEMENTMAP

	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;

#endif
`;var displacementmap_vertex_glsl_default=`
#ifdef USE_DISPLACEMENTMAP

	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );

#endif
`;var emissivemap_fragment_glsl_default=`
#ifdef USE_EMISSIVEMAP

	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );

	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE

		// use inline sRGB decode until browsers properly support SRGB8_ALPHA8 with video textures (#26516)

		emissiveColor = sRGBTransferEOTF( emissiveColor );

	#endif

	totalEmissiveRadiance *= emissiveColor.rgb;

#endif
`;var emissivemap_pars_fragment_glsl_default=`
#ifdef USE_EMISSIVEMAP

	uniform sampler2D emissiveMap;

#endif
`;var colorspace_fragment_glsl_default=`
gl_FragColor = linearToOutputTexel( gl_FragColor );
`;var colorspace_pars_fragment_glsl_default=`

vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}

vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}

vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}

`;var envmap_fragment_glsl_default=`
#ifdef USE_ENVMAP

	#ifdef ENV_WORLDPOS

		vec3 cameraToFrag;

		if ( isOrthographic ) {

			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );

		} else {

			cameraToFrag = normalize( vWorldPosition - cameraPosition );

		}

		// Transforming Normal Vectors with the Inverse Transformation
		vec3 worldNormal = transformNormalByInverseViewMatrix( normal, viewMatrix );

		#ifdef ENVMAP_MODE_REFLECTION

			vec3 reflectVec = reflect( cameraToFrag, worldNormal );

		#else

			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );

		#endif

	#else

		vec3 reflectVec = vReflect;

	#endif

	#ifdef ENVMAP_TYPE_CUBE

		vec4 envColor = textureCube( envMap, envMapRotation * reflectVec );

		#ifdef ENVMAP_BLENDING_MULTIPLY

			outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );

		#elif defined( ENVMAP_BLENDING_MIX )

			outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );

		#elif defined( ENVMAP_BLENDING_ADD )

			outgoingLight += envColor.xyz * specularStrength * reflectivity;

		#endif

	#endif

#endif
`;var envmap_common_pars_fragment_glsl_default=`
#ifdef USE_ENVMAP

	uniform float envMapIntensity;
	uniform mat3 envMapRotation;

	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif

#endif
`;var envmap_pars_fragment_glsl_default=`
#ifdef USE_ENVMAP

	uniform float reflectivity;

	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )

		#define ENV_WORLDPOS

	#endif

	#ifdef ENV_WORLDPOS

		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif

#endif
`;var envmap_pars_vertex_glsl_default=`
#ifdef USE_ENVMAP

	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )

		#define ENV_WORLDPOS

	#endif

	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;

	#else

		varying vec3 vReflect;
		uniform float refractionRatio;

	#endif

#endif
`;var envmap_vertex_glsl_default=`
#ifdef USE_ENVMAP

	#ifdef ENV_WORLDPOS

		vWorldPosition = worldPosition.xyz;

	#else

		vec3 cameraToVertex;

		if ( isOrthographic ) {

			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );

		} else {

			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );

		}

		vec3 worldNormal = transformNormalByInverseViewMatrix( transformedNormal, viewMatrix );

		#ifdef ENVMAP_MODE_REFLECTION

			vReflect = reflect( cameraToVertex, worldNormal );

		#else

			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );

		#endif

	#endif

#endif
`;var fog_vertex_glsl_default=`
#ifdef USE_FOG

	vFogDepth = - mvPosition.z;

#endif
`;var fog_pars_vertex_glsl_default=`
#ifdef USE_FOG

	varying float vFogDepth;

#endif
`;var fog_fragment_glsl_default=`
#ifdef USE_FOG

	#ifdef FOG_EXP2

		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );

	#else

		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );

	#endif

	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );

#endif
`;var fog_pars_fragment_glsl_default=`
#ifdef USE_FOG

	uniform vec3 fogColor;
	varying float vFogDepth;

	#ifdef FOG_EXP2

		uniform float fogDensity;

	#else

		uniform float fogNear;
		uniform float fogFar;

	#endif

#endif
`;var gradientmap_pars_fragment_glsl_default=`

#ifdef USE_GRADIENTMAP

	uniform sampler2D gradientMap;

#endif

vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {

	// dotNL will be from -1.0 to 1.0
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );

	#ifdef USE_GRADIENTMAP

		return vec3( texture2D( gradientMap, coord ).r );

	#else

		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );

	#endif

}
`;var lightmap_pars_fragment_glsl_default=`
#ifdef USE_LIGHTMAP

	uniform sampler2D lightMap;
	uniform float lightMapIntensity;

#endif
`;var lights_lambert_fragment_glsl_default=`
LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;
`;var lights_lambert_pars_fragment_glsl_default=`
varying vec3 vViewPosition;

struct LambertMaterial {

	vec3 diffuseColor;
	float specularStrength;

};

void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {

	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;

	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );

}

void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {

	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );

}

#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert
`;var lights_pars_begin_glsl_default=`
uniform bool receiveShadow;
uniform vec3 ambientLightColor;

#if defined( USE_LIGHT_PROBES )

	uniform vec3 lightProbe[ 9 ];

#endif

// get the irradiance (radiance convolved with cosine lobe) at the point 'normal' on the unit sphere
// source: https://graphics.stanford.edu/papers/envmap/envmap.pdf
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {

	// normal is assumed to have unit length

	float x = normal.x, y = normal.y, z = normal.z;

	// band 0
	vec3 result = shCoefficients[ 0 ] * 0.886227;

	// band 1
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;

	// band 2
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );

	return result;

}

vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {

	vec3 worldNormal = transformNormalByInverseViewMatrix( normal, viewMatrix );

	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );

	return irradiance;

}

vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {

	vec3 irradiance = ambientLightColor;

	return irradiance;

}

float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {

	// based upon Frostbite 3 Moving to Physically-based Rendering
	// page 32, equation 26: E[window1]
	// https://seblagarde.files.wordpress.com/2015/07/course_notes_moving_frostbite_to_pbr_v32.pdf
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );

	if ( cutoffDistance > 0.0 ) {

		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );

	}

	return distanceFalloff;

}

float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {

	return smoothstep( coneCosine, penumbraCosine, angleCosine );

}

#if NUM_SUN_LIGHTS > 0

	struct SunLight {
		vec3 direction;
		vec3 color;
	};

	uniform SunLight sunLights[ NUM_SUN_LIGHTS ];

	void getSunLightInfo( const in SunLight sunLight, out IncidentLight light ) {

		light.color = sunLight.color;
		light.direction = sunLight.direction;
		light.visible = true;

	}

#endif


#if NUM_DIR_LIGHTS > 0

	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};

	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];

	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {

		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;

	}

#endif


#if NUM_POINT_LIGHTS > 0

	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};

	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];

	// light is an out parameter as having it as a return value caused compiler errors on some devices
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {

		vec3 lVector = pointLight.position - geometryPosition;

		light.direction = normalize( lVector );

		float lightDistance = length( lVector );

		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );

	}

#endif


#if NUM_SPOT_LIGHTS > 0

	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};

	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];

	// light is an out parameter as having it as a return value caused compiler errors on some devices
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {

		vec3 lVector = spotLight.position - geometryPosition;

		light.direction = normalize( lVector );

		float angleCos = dot( light.direction, spotLight.direction );

		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );

		if ( spotAttenuation > 0.0 ) {

			float lightDistance = length( lVector );

			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );

		} else {

			light.color = vec3( 0.0 );
			light.visible = false;

		}

	}

#endif


#if NUM_RECT_AREA_LIGHTS > 0

	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};

	// Pre-computed values of LinearTransformedCosine approximation of BRDF
	// BRDF approximation Texture is 64x64
	uniform sampler2D ltc_1; // RGBA Float
	uniform sampler2D ltc_2; // RGBA Float

	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];

#endif


#if NUM_HEMI_LIGHTS > 0

	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};

	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];

	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {

		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;

		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );

		return irradiance;

	}

#endif

#include <lightprobes_pars_fragment>
`;var envmap_physical_pars_fragment_glsl_default=`
#ifdef USE_ENVMAP

	vec3 getIBLIrradiance( const in vec3 normal ) {

		#ifdef ENVMAP_TYPE_CUBE_UV

			vec3 worldNormal = transformNormalByInverseViewMatrix( normal, viewMatrix );

			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );

			return PI * envMapColor.rgb * envMapIntensity;

		#else

			return vec3( 0.0 );

		#endif

	}

	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {

		#ifdef ENVMAP_TYPE_CUBE_UV

			vec3 reflectVec = reflect( - viewDir, normal );

			// Mixing the reflection with the normal is more accurate and keeps rough objects from gathering light from behind their tangent plane.
			reflectVec = normalize( mix( reflectVec, normal, pow4( roughness ) ) );

			reflectVec = transformDirectionByInverseViewMatrix( reflectVec, viewMatrix );

			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );

			return envMapColor.rgb * envMapIntensity;

		#else

			return vec3( 0.0 );

		#endif

	}

	#ifdef USE_RETROREFLECTION

		vec3 getIBLRetroRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {

			#ifdef ENVMAP_TYPE_CUBE_UV

				// The retroreflective lobe returns light toward its source, so the environment is sampled along the view direction
				vec3 retroVec = normalize( mix( viewDir, normal, pow4( roughness ) ) );

				retroVec = transformDirectionByInverseViewMatrix( retroVec, viewMatrix );

				vec4 envMapColor = textureCubeUV( envMap, envMapRotation * retroVec, roughness );

				return envMapColor.rgb * envMapIntensity;

			#else

				return vec3( 0.0 );

			#endif

		}

	#endif

	#ifdef USE_ANISOTROPY

		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {

			#ifdef ENVMAP_TYPE_CUBE_UV

			  // https://google.github.io/filament/Filament.md.html#lighting/imagebasedlights/anisotropy
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );

				return getIBLRadiance( viewDir, bentNormal, roughness );

			#else

				return vec3( 0.0 );

			#endif

		}

		#ifdef USE_RETROREFLECTION

			vec3 getIBLAnisotropyRetroRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {

				#ifdef ENVMAP_TYPE_CUBE_UV

				  // https://google.github.io/filament/Filament.md.html#lighting/imagebasedlights/anisotropy
					vec3 bentNormal = cross( bitangent, viewDir );
					bentNormal = normalize( cross( bentNormal, bitangent ) );
					bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );

					return getIBLRetroRadiance( viewDir, bentNormal, roughness );

				#else

					return vec3( 0.0 );

				#endif

			}

		#endif

	#endif

#endif
`;var lights_toon_fragment_glsl_default=`
ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;
`;var lights_toon_pars_fragment_glsl_default=`
varying vec3 vViewPosition;

struct ToonMaterial {

	vec3 diffuseColor;

};

void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {

	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;

	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );

}

void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {

	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );

}

#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon
`;var lights_phong_fragment_glsl_default=`
BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;
`;var lights_phong_pars_fragment_glsl_default=`
varying vec3 vViewPosition;

struct BlinnPhongMaterial {

	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;

};

void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {

	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;

	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );

	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;

}

void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {

	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );

}

#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong
`;var lights_physical_fragment_glsl_default=`
PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.diffuseContribution = diffuseColor.rgb * ( 1.0 - metalnessFactor );
material.metalness = metalnessFactor;

vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );

material.roughness = max( roughnessFactor, 0.0525 );// 0.0525 corresponds to the base mip of a 256 cubemap.
material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );

#ifdef IOR

	material.ior = ior;

	#ifdef USE_SPECULAR

		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;

		#ifdef USE_SPECULAR_COLORMAP

			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;

		#endif

		#ifdef USE_SPECULAR_INTENSITYMAP

			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;

		#endif

		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );

	#else

		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;

	#endif

	material.specularColor = min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor;
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );

#else

	material.specularColor = vec3( 0.04 );
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;

#endif

#ifdef USE_CLEARCOAT

	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;

	#ifdef USE_CLEARCOATMAP

		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;

	#endif

	#ifdef USE_CLEARCOAT_ROUGHNESSMAP

		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;

	#endif

	material.clearcoat = saturate( material.clearcoat ); // Burley clearcoat model
	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );

#endif

#ifdef USE_DISPERSION

	material.dispersion = dispersion;

#endif

#ifdef USE_RETROREFLECTION

	material.retroreflectivity = retroreflectivity;

#endif

#ifdef USE_IRIDESCENCE

	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;

	#ifdef USE_IRIDESCENCEMAP

		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;

	#endif

	#ifdef USE_IRIDESCENCE_THICKNESSMAP

		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;

	#else

		material.iridescenceThickness = iridescenceThicknessMaximum;

	#endif

#endif

#ifdef USE_SHEEN

	material.sheenColor = sheenColor;

	#ifdef USE_SHEEN_COLORMAP

		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;

	#endif

	material.sheenRoughness = clamp( sheenRoughness, 0.0001, 1.0 );

	#ifdef USE_SHEEN_ROUGHNESSMAP

		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;

	#endif

#endif

#ifdef USE_ANISOTROPY

	#ifdef USE_ANISOTROPYMAP

		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;

	#else

		vec2 anisotropyV = anisotropyVector;

	#endif

	material.anisotropy = length( anisotropyV );

	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}

	// Roughness along the anisotropy bitangent is the material roughness, while the tangent roughness increases with anisotropy.
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );

	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;

#endif
`;var lights_physical_pars_fragment_glsl_default=`

uniform sampler2D dfgLUT;

struct PhysicalMaterial {

	vec3 diffuseColor;
	vec3 diffuseContribution;
	vec3 specularColor;
	vec3 specularColorBlended;

	float roughness;
	float metalness;
	float specularF90;
	float dispersion;
	vec2 dfg;
	vec3 multiScatteringCompensation;

	#ifdef USE_RETROREFLECTION
		float retroreflectivity;
	#endif

	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif

	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0Dielectric;
		vec3 iridescenceF0Metallic;
	#endif

	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif

	#ifdef IOR
		float ior;
	#endif

	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif

	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif

};

// temporary
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );

vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );

    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}

// Moving Frostbite to Physically Based Rendering 3.0 - page 12, listing 2
// https://seblagarde.files.wordpress.com/2015/07/course_notes_moving_frostbite_to_pbr_v32.pdf
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {

	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );

	return 0.5 / max( gv + gl, EPSILON );

}

// Microfacet Models for Refraction through Rough Surfaces - equation (33)
// http://graphicrants.blogspot.com/2013/08/specular-brdf-reference.html
// alpha is "roughness squared" in Disney\u2019s reparameterization
float D_GGX( const in float alpha, const in float dotNH ) {

	float a2 = pow2( alpha );

	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0; // avoid alpha = 0 with dotNH = 1

	return RECIPROCAL_PI * a2 / pow2( denom );

}

// https://google.github.io/filament/Filament.md.html#materialsystem/anisotropicmodel/anisotropicspecularbrdf
#ifdef USE_ANISOTROPY

	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {

		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		return 0.5 / max( gv + gl, EPSILON );

	}

	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {

		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;

		return RECIPROCAL_PI * a2 * pow2 ( w2 );

	}

#endif

#ifdef USE_CLEARCOAT

	// GGX Distribution, Schlick Fresnel, GGX_SmithCorrelated Visibility
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {

		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;

		float alpha = pow2( roughness ); // UE4's roughness

		vec3 halfDir = normalize( lightDir + viewDir );

		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );

		vec3 F = F_Schlick( f0, f90, dotVH );

		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );

		float D = D_GGX( alpha, dotNH );

		return F * ( V * D );

	}

#endif

vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {

	vec3 f0 = material.specularColorBlended;
	float f90 = material.specularF90;
	float roughness = material.roughness;

	float alpha = pow2( roughness ); // UE4's roughness

	vec3 halfDir = normalize( lightDir + viewDir );

	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );

	vec3 F = F_Schlick( f0, f90, dotVH );

	#ifdef USE_IRIDESCENCE

		F = mix( F, material.iridescenceFresnel, material.iridescence );

	#endif

	#ifdef USE_ANISOTROPY

		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );

		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );

		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );

	#else

		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );

		float D = D_GGX( alpha, dotNH );

	#endif

	return F * ( V * D );

}

// Rect Area Light

// Real-Time Polygonal-Light Shading with Linearly Transformed Cosines
// by Eric Heitz, Jonathan Dupuy, Stephen Hill and David Neubelt
// code: https://github.com/selfshadow/ltc_code/

vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {

	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;

	float dotNV = saturate( dot( N, V ) );

	// texture parameterized by sqrt( GGX alpha ) and sqrt( 1 - cos( theta ) )
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );

	uv = uv * LUT_SCALE + LUT_BIAS;

	return uv;

}

float LTC_ClippedSphereFormFactor( const in vec3 f ) {

	// Real-Time Area Lighting: a Journey from Research to Production (p.102)
	// An approximation of the form factor of a horizon-clipped rectangle.

	float l = length( f );

	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );

}

vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {

	float x = dot( v1, v2 );

	float y = abs( x );

	// rational polynomial approximation to theta / sin( theta ) / 2PI
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;

	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;

	return cross( v1, v2 ) * theta_sintheta;

}

vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {

	// bail if point is on back side of plane of light
	// assumes ccw winding order of light vertices
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );

	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );

	// construct orthonormal basis around N
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 ); // negated from paper; possibly due to a different handedness of world coordinate system

	// compute transform
	mat3 mat = mInv * transpose( mat3( T1, T2, N ) );

	// transform rect
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );

	// project rect onto sphere
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );

	// calculate vector form factor
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );

	// adjust for horizon clipping
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );

/*
	// alternate method of adjusting for horizon clipping (see reference)
	// refactoring required
	float len = length( vectorFormFactor );
	float z = vectorFormFactor.z / len;

	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;

	// tabulated horizon-clipped sphere, apparently...
	vec2 uv = vec2( z * 0.5 + 0.5, len );
	uv = uv * LUT_SCALE + LUT_BIAS;

	float scale = texture2D( ltc_2, uv ).w;

	float result = len * scale;
*/

	return vec3( result );

}

// End Rect Area Light

#if defined( USE_SHEEN )

// https://github.com/google/filament/blob/master/shaders/src/brdf.fs
float D_Charlie( float roughness, float dotNH ) {

	float alpha = pow2( roughness );

	// Estevez and Kulla 2017, "Production Friendly Microfacet Sheen BRDF"
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 ); // 2^(-14/2), so sin2h^2 > 0 in fp16

	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );

}

// https://github.com/google/filament/blob/master/shaders/src/brdf.fs
float V_Neubelt( float dotNV, float dotNL ) {

	// Neubelt and Pettineo 2013, "Crafting a Next-gen Material Pipeline for The Order: 1886"
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );

}

vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {

	vec3 halfDir = normalize( lightDir + viewDir );

	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );

	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );

	return sheenColor * ( D * V );

}

#endif

// This is a curve-fit approximation to the "Charlie sheen" BRDF integrated over the hemisphere from
// Estevez and Kulla 2017, "Production Friendly Microfacet Sheen BRDF".
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {

	float dotNV = saturate( dot( normal, viewDir ) );

	float r2 = roughness * roughness;
	float rInv = 1.0 / ( roughness + 0.1 );

	float a = -1.9362 + 1.0678 * roughness + 0.4573 * r2 - 0.8469 * rInv;
	float b = -0.6014 + 0.5538 * roughness - 0.4670 * r2 - 0.1255 * rInv;

	float DG = exp( a * dotNV + b );

	return saturate( DG );

}

vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {

	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 fab = texture2D( dfgLUT, vec2( roughness, dotNV ) ).rg;

	return specularColor * fab.x + specularF90 * fab.y;

}

// Fdez-Ag\xFCera's "Multiple-Scattering Microfacet Model for Real-Time Image Based Lighting"
// Approximates multiscattering in order to preserve energy.
// http://www.jcgt.org/published/0008/01/03/
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec2 fab, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec2 fab, const in vec3 specularColor, const in float specularF90, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif

	#ifdef USE_IRIDESCENCE

		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );

	#else

		vec3 Fr = specularColor;

	#endif

	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;

	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;

	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619; // 1/21
	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );

	singleScatter += FssEss;
	multiScatter += Fms * Ems;

}

#if NUM_RECT_AREA_LIGHTS > 0

	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {

		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;

		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight; // counterclockwise; light shines in local neg z direction
		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;

		vec2 uv = LTC_Uv( normal, viewDir, roughness );

		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );

		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);

		// LTC Fresnel Approximation by Stephen Hill
		// http://blog.selfshadow.com/publications/s2016-advances/s2016_ltc_fresnel.pdf
		vec3 fresnel = ( material.specularColorBlended * t2.x + ( material.specularF90 - material.specularColorBlended ) * t2.y );

		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );

		reflectedLight.directDiffuse += lightColor * material.diffuseContribution * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );

		#ifdef USE_CLEARCOAT

			vec3 Ncc = geometryClearcoatNormal;

			vec2 uvClearcoat = LTC_Uv( Ncc, viewDir, material.clearcoatRoughness );

			vec4 t1Clearcoat = texture2D( ltc_1, uvClearcoat );
			vec4 t2Clearcoat = texture2D( ltc_2, uvClearcoat );

			mat3 mInvClearcoat = mat3(
				vec3( t1Clearcoat.x, 0, t1Clearcoat.y ),
				vec3(             0, 1,             0 ),
				vec3( t1Clearcoat.z, 0, t1Clearcoat.w )
			);

			// LTC Fresnel Approximation for clearcoat
			vec3 fresnelClearcoat = material.clearcoatF0 * t2Clearcoat.x + ( material.clearcoatF90 - material.clearcoatF0 ) * t2Clearcoat.y;

			clearcoatSpecularDirect += lightColor * fresnelClearcoat * LTC_Evaluate( Ncc, viewDir, position, mInvClearcoat, rectCoords );

		#endif

	}

#endif

void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {

	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );

	vec3 irradiance = dotNL * directLight.color;

	#ifdef USE_CLEARCOAT

		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );

		vec3 ccIrradiance = dotNLcc * directLight.color;

		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );

	#endif

	#ifdef USE_SHEEN
 
 		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
 
 		float sheenAlbedoV = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
 		float sheenAlbedoL = IBLSheenBRDF( geometryNormal, directLight.direction, material.sheenRoughness );
 
 		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * max( sheenAlbedoV, sheenAlbedoL );
 
 		irradiance *= sheenEnergyComp;
 
 	#endif

	vec3 specularBRDF = BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );

	#ifdef USE_RETROREFLECTION

		// Minimal Retroreflective Microfacet Model:
		// https://jcgt.org/published/0015/01/04/
		vec3 retroViewDir = reflect( - geometryViewDir, geometryNormal );
		vec3 retroSpecularBRDF = BRDF_GGX( directLight.direction, retroViewDir, geometryNormal, material );

		specularBRDF = mix( specularBRDF, retroSpecularBRDF, saturate( material.retroreflectivity ) );

	#endif

	reflectedLight.directSpecular += irradiance * specularBRDF * material.multiScatteringCompensation;

	// Light reflected by the specular interface is not available to the diffuse layer ( glTF fresnel_mix )
	vec3 halfDir = normalize( directLight.direction + geometryViewDir );
	float dotVH = saturate( dot( geometryViewDir, halfDir ) );
	vec3 F = F_Schlick( material.specularColor, material.specularF90, dotVH );

	#ifdef USE_RETROREFLECTION

		vec3 retroHalfDir = normalize( directLight.direction + retroViewDir );
		float dotRetroVH = saturate( dot( retroViewDir, retroHalfDir ) );
		vec3 retroF = F_Schlick( material.specularColor, material.specularF90, dotRetroVH );

		F = mix( F, retroF, saturate( material.retroreflectivity ) );

	#endif

	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseContribution ) * ( 1.0 - F );
}

void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {

	// Energy reflected by the specular lobe is not available to the diffuse layer
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );

	#ifdef USE_IRIDESCENCE

		computeMultiscatteringIridescence( material.dfg, material.specularColor, material.specularF90, material.iridescence, material.iridescenceF0Dielectric, singleScattering, multiScattering );

	#else

		computeMultiscattering( material.dfg, material.specularColor, material.specularF90, singleScattering, multiScattering );

	#endif

	vec3 diffuse = irradiance * BRDF_Lambert( material.diffuseContribution ) * ( 1.0 - singleScattering - multiScattering );

	#ifdef USE_SHEEN

		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );

		sheenSpecularIndirect += irradiance * material.sheenColor * sheenAlbedo * RECIPROCAL_PI;

		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;

		diffuse *= sheenEnergyComp;

	#endif

	reflectedLight.indirectDiffuse += diffuse;

}

void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {

	#ifdef USE_CLEARCOAT

		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );

	#endif

	#ifdef USE_SHEEN

		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness ) * RECIPROCAL_PI;

 	#endif

	// Both indirect specular and indirect diffuse light accumulate here
	// Compute multiscattering separately for dielectric and metallic, then mix

	vec3 singleScatteringDielectric = vec3( 0.0 );
	vec3 multiScatteringDielectric = vec3( 0.0 );

	vec3 singleScatteringMetallic = vec3( 0.0 );
	vec3 multiScatteringMetallic = vec3( 0.0 );

	#ifdef USE_IRIDESCENCE

		computeMultiscatteringIridescence( material.dfg, material.specularColor, material.specularF90, material.iridescence, material.iridescenceF0Dielectric, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscatteringIridescence( material.dfg, material.diffuseColor, material.specularF90, material.iridescence, material.iridescenceF0Metallic, singleScatteringMetallic, multiScatteringMetallic );

	#else

		computeMultiscattering( material.dfg, material.specularColor, material.specularF90, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscattering( material.dfg, material.diffuseColor, material.specularF90, singleScatteringMetallic, multiScatteringMetallic );

	#endif

	// Mix based on metalness
	vec3 singleScattering = mix( singleScatteringDielectric, singleScatteringMetallic, material.metalness );
	vec3 multiScattering = mix( multiScatteringDielectric, multiScatteringMetallic, material.metalness );

	// Diffuse energy conservation uses dielectric path
	vec3 totalScatteringDielectric = singleScatteringDielectric + multiScatteringDielectric;
	vec3 diffuse = material.diffuseContribution * ( 1.0 - totalScatteringDielectric );

	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;

	vec3 indirectSpecular = radiance * singleScattering;
	indirectSpecular += multiScattering * cosineWeightedIrradiance;

	vec3 indirectDiffuse = diffuse * cosineWeightedIrradiance;

	#ifdef USE_SHEEN

		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );

		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;

		indirectSpecular *= sheenEnergyComp;
		indirectDiffuse *= sheenEnergyComp;

	#endif

	reflectedLight.indirectSpecular += indirectSpecular;
	reflectedLight.indirectDiffuse += indirectDiffuse;

}

#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical

// ref: https://seblagarde.files.wordpress.com/2015/07/course_notes_moving_frostbite_to_pbr_v32.pdf
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {

	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );

}
`;var lights_fragment_begin_glsl_default=`
/**
 * This is a template that can be used to light a material, it uses pluggable
 * RenderEquations (RE)for specific lighting scenarios.
 *
 * Instructions for use:
 * - Ensure that both RE_Direct, RE_IndirectDiffuse and RE_IndirectSpecular are defined
 * - Create a material parameter that is to be passed as the third parameter to your lighting functions.
 *
 * TODO:
 * - Add area light support.
 * - Add sphere light support.
 * - Add diffuse light probe (irradiance cubemap) support.
 */

vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );

vec3 geometryClearcoatNormal = vec3( 0.0 );

#ifdef USE_CLEARCOAT

	geometryClearcoatNormal = clearcoatNormal;

#endif

#ifdef USE_IRIDESCENCE

	float dotNVi = saturate( dot( normal, geometryViewDir ) );

	if ( material.iridescenceThickness == 0.0 ) {

		material.iridescence = 0.0;

	} else {

		material.iridescence = saturate( material.iridescence );

	}

	if ( material.iridescence > 0.0 ) {

		vec3 iridescenceFresnelDielectric = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		vec3 iridescenceFresnelMetallic = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.diffuseColor );

		material.iridescenceFresnel = mix( iridescenceFresnelDielectric, iridescenceFresnelMetallic, material.metalness );

		// Iridescence F0 approximation
		material.iridescenceF0Dielectric = Schlick_to_F0( iridescenceFresnelDielectric, 1.0, dotNVi );
		material.iridescenceF0Metallic = Schlick_to_F0( iridescenceFresnelMetallic, 1.0, dotNVi );

	}

#endif

#ifdef STANDARD

	float dotNVms = saturate( dot( geometryNormal, geometryViewDir ) );

	material.dfg = texture2D( dfgLUT, vec2( material.roughness, dotNVms ) ).rg;

	#if ( NUM_SUN_LIGHTS > 0 || NUM_DIR_LIGHTS > 0 || NUM_POINT_LIGHTS > 0 || NUM_SPOT_LIGHTS > 0 )

		// Multi-scattering energy compensation for direct lighting
		// Based on "Practical Multiple Scattering Compensation for Microfacet Models"
		// https://blog.selfshadow.com/publications/turquin/ms_comp_final.pdf

		// Energy of the single-scattering lobe in a white furnace ( F0 = F90 = 1 )
		float EssMs = material.dfg.x + material.dfg.y;

		// Compensate for the energy lost to multiple scattering, tinting the added term by F0 ( equation 16 )
		material.multiScatteringCompensation = 1.0 + material.specularColorBlended * ( 1.0 / EssMs - 1.0 );

	#endif

#endif

IncidentLight directLight;

#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )

	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {

		pointLight = pointLights[ i ];

		getPointLightInfo( pointLight, geometryPosition, directLight );

		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS ) && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif

		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );

	}
	#pragma unroll_loop_end

#endif

#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )

	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;

	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {

		spotLight = spotLights[ i ];

		getSpotLightInfo( spotLight, geometryPosition, directLight );

		// spot lights are ordered [shadows with maps, shadows without maps, maps without shadows, none]
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif

		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif

		#undef SPOT_LIGHT_MAP_INDEX

		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif

		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );

	}
	#pragma unroll_loop_end

#endif

#if ( NUM_SUN_LIGHTS > 0 ) && defined( RE_Direct )

	SunLight sunLight;
	#if defined( USE_SHADOWMAP ) && NUM_SUN_LIGHT_SHADOWS > 0
	SunLightShadow sunLightShadow;
	#endif

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SUN_LIGHTS; i ++ ) {

		sunLight = sunLights[ i ];

		getSunLightInfo( sunLight, directLight );

		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SUN_LIGHT_SHADOWS )
		sunLightShadow = sunLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getSunShadow( sunShadowMap[ i ], sunLightShadow, UNROLLED_LOOP_INDEX ) : 1.0;
		#endif

		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );

	}
	#pragma unroll_loop_end

#endif

#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )

	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {

		directionalLight = directionalLights[ i ];

		getDirectionalLightInfo( directionalLight, directLight );

		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif

		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );

	}
	#pragma unroll_loop_end

#endif

#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )

	RectAreaLight rectAreaLight;

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {

		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );

	}
	#pragma unroll_loop_end

#endif

#if defined( RE_IndirectDiffuse )

	vec3 iblIrradiance = vec3( 0.0 );

	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );

	#if defined( USE_LIGHT_PROBES )

		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );

	#endif

	#if ( NUM_HEMI_LIGHTS > 0 )

		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {

			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );

		}
		#pragma unroll_loop_end

	#endif

	#ifdef USE_LIGHT_PROBES_GRID

		vec3 probeWorldPos = ( ( vec4( geometryPosition, 1.0 ) - viewMatrix[ 3 ] ) * viewMatrix ).xyz;
		vec3 probeWorldNormal = transformNormalByInverseViewMatrix( geometryNormal, viewMatrix );
		irradiance += getLightProbeGridIrradiance( probeWorldPos, probeWorldNormal );

	#endif

#endif

#if defined( RE_IndirectSpecular )

	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );

#endif
`;var lights_fragment_maps_glsl_default=`
#if defined( RE_IndirectDiffuse )

	#ifdef USE_LIGHTMAP

		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;

		irradiance += lightMapIrradiance;

	#endif

	#if defined( USE_ENVMAP ) && defined( ENVMAP_TYPE_CUBE_UV )

		#if defined( STANDARD ) || defined( LAMBERT ) || defined( PHONG )

			iblIrradiance += getIBLIrradiance( geometryNormal );

		#endif

	#endif

#endif

#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )

	#ifdef USE_ANISOTROPY

		vec3 iblRadiance = getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );

	#else

		vec3 iblRadiance = getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );

	#endif

	#ifdef USE_RETROREFLECTION

		#ifdef USE_ANISOTROPY

			vec3 retroIBLRadiance = getIBLAnisotropyRetroRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );

		#else

			vec3 retroIBLRadiance = getIBLRetroRadiance( geometryViewDir, geometryNormal, material.roughness );

		#endif

		iblRadiance = mix( iblRadiance, retroIBLRadiance, saturate( material.retroreflectivity ) );

	#endif

	radiance += iblRadiance;

	#ifdef USE_CLEARCOAT

		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );

	#endif

#endif
`;var lights_fragment_end_glsl_default=`
#if defined( RE_IndirectDiffuse )

	#if defined( LAMBERT ) || defined( PHONG )

		irradiance += iblIrradiance;

	#endif

	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );

#endif

#if defined( RE_IndirectSpecular )

	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );

#endif
`;var lightprobes_pars_fragment_glsl_default=`
#ifdef USE_LIGHT_PROBES_GRID

// Single atlas 3D texture that stores all 7 SH sub-volumes stacked along Z.
// Atlas depth = 7 * ( nz + 2 ) where nz = probesResolution.z.
// Each sub-volume occupies ( nz + 2 ) slices: 1 padding + nz data + 1 padding.
// Padding is a copy of the first / last data slice and prevents color bleeding
// when the hardware linear filter reads across a sub-volume boundary.
uniform highp sampler3D probesSH;

uniform vec3 probesMin;
uniform vec3 probesMax;
uniform vec3 probesResolution;

vec3 getLightProbeGridIrradiance( vec3 worldPos, vec3 worldNormal ) {

	vec3 res = probesResolution;
	vec3 gridRange = probesMax - probesMin;
	vec3 resMinusOne = res - 1.0;
	vec3 probeSpacing = gridRange / resMinusOne;

	// Offset sample position along normal by half a probe spacing
	vec3 samplePos = worldPos + worldNormal * probeSpacing * 0.5;
	vec3 uvw = clamp( ( samplePos - probesMin ) / gridRange, 0.0, 1.0 );

	// Remap to texel centers of the probe grid (XY and Z)
	uvw = uvw * resMinusOne / res + 0.5 / res;

	// Atlas UV mapping along Z:
	//   paddedSlices = nz + 2  (1 padding texel at each end of every sub-volume)
	//   atlasDepth   = 7 * paddedSlices
	//   For sub-volume t the first DATA texel sits at atlas slice t*paddedSlices + 1.
	//   Given probe-grid texel-centre UVZ = ( iz + 0.5 ) / nz the atlas UV is:
	//     atlasUvZ = ( uvw.z * nz + t * paddedSlices + 1 ) / atlasDepth
	//
	// uvZBase encodes the nz-scaled Z plus the intra-volume offset (+ 1 for padding),
	// so adding t*paddedSlices steps to each successive sub-volume.
	float nz          = res.z;
	float paddedSlices = nz + 2.0;
	float atlasDepth  = 7.0 * paddedSlices;
	float uvZBase     = uvw.z * nz + 1.0;

	vec4 s0 = texture( probesSH, vec3( uvw.xy, ( uvZBase                       ) / atlasDepth ) );
	vec4 s1 = texture( probesSH, vec3( uvw.xy, ( uvZBase +       paddedSlices   ) / atlasDepth ) );
	vec4 s2 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 2.0 * paddedSlices   ) / atlasDepth ) );
	vec4 s3 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 3.0 * paddedSlices   ) / atlasDepth ) );
	vec4 s4 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 4.0 * paddedSlices   ) / atlasDepth ) );
	vec4 s5 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 5.0 * paddedSlices   ) / atlasDepth ) );
	vec4 s6 = texture( probesSH, vec3( uvw.xy, ( uvZBase + 6.0 * paddedSlices   ) / atlasDepth ) );

	// Unpack 9 vec3 SH L2 coefficients
	vec3 c0 = s0.xyz;
	vec3 c1 = vec3( s0.w, s1.xy );
	vec3 c2 = vec3( s1.zw, s2.x );
	vec3 c3 = s2.yzw;
	vec3 c4 = s3.xyz;
	vec3 c5 = vec3( s3.w, s4.xy );
	vec3 c6 = vec3( s4.zw, s5.x );
	vec3 c7 = s5.yzw;
	vec3 c8 = s6.xyz;

	// Evaluate L2 irradiance
	float x = worldNormal.x, y = worldNormal.y, z = worldNormal.z;

	vec3 result = c0 * 0.886227;
	result += c1 * 2.0 * 0.511664 * y;
	result += c2 * 2.0 * 0.511664 * z;
	result += c3 * 2.0 * 0.511664 * x;
	result += c4 * 2.0 * 0.429043 * x * y;
	result += c5 * 2.0 * 0.429043 * y * z;
	result += c6 * ( 0.743125 * z * z - 0.247708 );
	result += c7 * 2.0 * 0.429043 * x * z;
	result += c8 * 0.429043 * ( x * x - y * y );

	return max( result, vec3( 0.0 ) );

}

#endif
`;var logdepthbuf_fragment_glsl_default=`
#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )

	// Doing a strict comparison with == 1.0 can cause noise artifacts
	// on some platforms. See issue #17623.
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;

#endif
`;var logdepthbuf_pars_fragment_glsl_default=`
#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )

	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;

#endif
`;var logdepthbuf_pars_vertex_glsl_default=`
#ifdef USE_LOGARITHMIC_DEPTH_BUFFER

	varying float vFragDepth;
	varying float vIsPerspective;

#endif
`;var logdepthbuf_vertex_glsl_default=`
#ifdef USE_LOGARITHMIC_DEPTH_BUFFER

	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );

#endif
`;var map_fragment_glsl_default=`
#ifdef USE_MAP

	vec4 sampledDiffuseColor = texture2D( map, vMapUv );

	#ifdef DECODE_VIDEO_TEXTURE

		// use inline sRGB decode until browsers properly support SRGB8_ALPHA8 with video textures (#26516)

		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );

	#endif

	diffuseColor *= sampledDiffuseColor;

#endif
`;var map_pars_fragment_glsl_default=`
#ifdef USE_MAP

	uniform sampler2D map;

#endif
`;var map_particle_fragment_glsl_default=`
#if defined( USE_MAP ) || defined( USE_ALPHAMAP )

	#if defined( USE_POINTS_UV )

		vec2 uv = vUv;

	#else

		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;

	#endif

#endif

#ifdef USE_MAP

	diffuseColor *= texture2D( map, uv );

#endif

#ifdef USE_ALPHAMAP

	diffuseColor.a *= texture2D( alphaMap, uv ).g;

#endif
`;var map_particle_pars_fragment_glsl_default=`
#if defined( USE_POINTS_UV )

	varying vec2 vUv;

#else

	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )

		uniform mat3 uvTransform;

	#endif

#endif

#ifdef USE_MAP

	uniform sampler2D map;

#endif

#ifdef USE_ALPHAMAP

	uniform sampler2D alphaMap;

#endif
`;var metalnessmap_fragment_glsl_default=`
float metalnessFactor = metalness;

#ifdef USE_METALNESSMAP

	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );

	// reads channel B, compatible with a combined OcclusionRoughnessMetallic (RGB) texture
	metalnessFactor *= texelMetalness.b;

#endif
`;var metalnessmap_pars_fragment_glsl_default=`
#ifdef USE_METALNESSMAP

	uniform sampler2D metalnessMap;

#endif
`;var morphinstance_vertex_glsl_default=`
#ifdef USE_INSTANCING_MORPH

	float morphTargetInfluences[ MORPHTARGETS_COUNT ];

	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;

	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {

		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;

	}
#endif
`;var morphcolor_vertex_glsl_default=`
#if defined( USE_MORPHCOLORS )

	// morphTargetBaseInfluence is set based on BufferGeometry.morphTargetsRelative value:
	// When morphTargetsRelative is false, this is set to 1 - sum(influences); this results in normal = sum((target - base) * influence)
	// When morphTargetsRelative is true, this is set to 1; as a result, all morph targets are simply added to the base after weighting
	vColor *= morphTargetBaseInfluence;

	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {

		#if defined( USE_COLOR_ALPHA )

			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];

		#elif defined( USE_COLOR )

			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];

		#endif

	}

#endif
`;var morphnormal_vertex_glsl_default=`
#ifdef USE_MORPHNORMALS

	// morphTargetBaseInfluence is set based on BufferGeometry.morphTargetsRelative value:
	// When morphTargetsRelative is false, this is set to 1 - sum(influences); this results in normal = sum((target - base) * influence)
	// When morphTargetsRelative is true, this is set to 1; as a result, all morph targets are simply added to the base after weighting
	objectNormal *= morphTargetBaseInfluence;

	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {

		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];

	}

#endif
`;var morphtarget_pars_vertex_glsl_default=`
#ifdef USE_MORPHTARGETS

	#ifndef USE_INSTANCING_MORPH

		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];

	#endif

	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;

	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {

		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;

		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );

	}

#endif
`;var morphtarget_vertex_glsl_default=`
#ifdef USE_MORPHTARGETS

	// morphTargetBaseInfluence is set based on BufferGeometry.morphTargetsRelative value:
	// When morphTargetsRelative is false, this is set to 1 - sum(influences); this results in position = sum((target - base) * influence)
	// When morphTargetsRelative is true, this is set to 1; as a result, all morph targets are simply added to the base after weighting
	transformed *= morphTargetBaseInfluence;

	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {

		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];

	}

#endif
`;var normal_fragment_begin_glsl_default=`
float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;

#ifdef FLAT_SHADED

	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );

#else

	vec3 normal = normalize( vNormal );

	#ifdef DOUBLE_SIDED

		normal *= faceDirection;

	#endif

#endif

#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )

	#ifdef USE_TANGENT

		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );

	#else

		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);

	#endif

	#ifdef DOUBLE_SIDED

		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;

	#endif

#endif

#ifdef USE_CLEARCOAT_NORMALMAP

	#ifdef USE_TANGENT

		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );

	#else

		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );

	#endif

	#ifdef DOUBLE_SIDED

		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;

	#endif

#endif

// non perturbed normal for clearcoat among others

vec3 nonPerturbedNormal = normal;

`;var normal_fragment_maps_glsl_default=`

#ifdef USE_NORMALMAP_OBJECTSPACE

	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0; // overrides both flatShading and attribute normals

	#ifdef FLIP_SIDED

		normal = - normal;

	#endif

	#ifdef DOUBLE_SIDED

		normal = normal * faceDirection;

	#endif

	normal = normalize( normalMatrix * normal );

#elif defined( USE_NORMALMAP_TANGENTSPACE )

	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;

	#if defined( USE_PACKED_NORMALMAP )

		mapN = vec3( mapN.xy, sqrt( saturate( 1.0 - dot( mapN.xy, mapN.xy ) ) ) );

	#endif

	mapN.xy *= normalScale;

	normal = normalize( tbn * mapN );

#elif defined( USE_BUMPMAP )

	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );

#endif
`;var normal_pars_fragment_glsl_default=`
#ifndef FLAT_SHADED

	varying vec3 vNormal;

	#ifdef USE_TANGENT

		varying vec3 vTangent;
		varying vec3 vBitangent;

	#endif

#endif
`;var normal_pars_vertex_glsl_default=`
#ifndef FLAT_SHADED

	varying vec3 vNormal;

	#ifdef USE_TANGENT

		varying vec3 vTangent;
		varying vec3 vBitangent;

	#endif

#endif
`;var normal_vertex_glsl_default=`
#ifndef FLAT_SHADED // normal is computed with derivatives when FLAT_SHADED

	vNormal = normalize( transformedNormal );

	#ifdef USE_TANGENT

		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );

		#ifdef FLIP_SIDED

			vBitangent = - vBitangent;

		#endif

	#endif

#endif
`;var normalmap_pars_fragment_glsl_default=`
#ifdef USE_NORMALMAP

	uniform sampler2D normalMap;
	uniform vec2 normalScale;

#endif

#ifdef USE_NORMALMAP_OBJECTSPACE

	uniform mat3 normalMatrix;

#endif

#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )

	// Normal Mapping Without Precomputed Tangents
	// http://www.thetenthplanet.de/archives/1180

	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {

		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );

		vec3 N = surf_norm; // normalized

		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );

		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;

		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );

		return mat3( T * scale, B * scale, N );

	}

#endif
`;var clearcoat_normal_fragment_begin_glsl_default=`
#ifdef USE_CLEARCOAT

	vec3 clearcoatNormal = nonPerturbedNormal;

#endif
`;var clearcoat_normal_fragment_maps_glsl_default=`
#ifdef USE_CLEARCOAT_NORMALMAP

	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;

	clearcoatNormal = normalize( tbn2 * clearcoatMapN );

#endif
`;var clearcoat_pars_fragment_glsl_default=`

#ifdef USE_CLEARCOATMAP

	uniform sampler2D clearcoatMap;

#endif

#ifdef USE_CLEARCOAT_NORMALMAP

	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;

#endif

#ifdef USE_CLEARCOAT_ROUGHNESSMAP

	uniform sampler2D clearcoatRoughnessMap;

#endif
`;var iridescence_pars_fragment_glsl_default=`

#ifdef USE_IRIDESCENCEMAP

	uniform sampler2D iridescenceMap;

#endif

#ifdef USE_IRIDESCENCE_THICKNESSMAP

	uniform sampler2D iridescenceThicknessMap;

#endif
`;var opaque_fragment_glsl_default=`
#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif

#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif

gl_FragColor = vec4( outgoingLight, diffuseColor.a );
`;var packing_glsl_default=`
vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}

vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}

const float PackUpscale = 256. / 255.; // fraction -> 0..1 (including 1)
const float UnpackDownscale = 255. / 256.; // 0..1 -> fraction (excluding 1)
const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;

const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );

const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );

vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}

vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	// the 0.9999 tweak is unimportant, very tiny empirical improvement
	// return vec3( vuf * Inv255, gf * PackUpscale, bf * 0.9999 );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}

vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}

float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}

float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}

float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}

vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}

vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}

// NOTE: viewZ, the z-coordinate in camera space, is negative for points in front of the camera

float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	// -near maps to 0; -far maps to 1
	return ( viewZ + near ) / ( near - far );
}

float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {

	#ifdef USE_REVERSED_DEPTH_BUFFER
	
		return depth * ( far - near ) - far;

	#else

		return depth * ( near - far ) - near;

	#endif
}

// NOTE: https://twitter.com/gonnavis/status/1377183786949959682

float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	// -near maps to 0; -far maps to 1
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}

float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	
	#ifdef USE_REVERSED_DEPTH_BUFFER

		return ( near * far ) / ( ( near - far ) * depth - near );

	#else

		return ( near * far ) / ( ( far - near ) * depth - far );

	#endif
}
`;var premultiplied_alpha_fragment_glsl_default=`
#ifdef PREMULTIPLIED_ALPHA

	gl_FragColor.rgb *= gl_FragColor.a;

#endif
`;var project_vertex_glsl_default=`
vec4 mvPosition = vec4( transformed, 1.0 );

#ifdef USE_BATCHING

	mvPosition = batchingMatrix * mvPosition;

#endif

#ifdef USE_INSTANCING

	mvPosition = instanceMatrix * mvPosition;

#endif

mvPosition = modelViewMatrix * mvPosition;

gl_Position = projectionMatrix * mvPosition;
`;var dithering_fragment_glsl_default=`
#ifdef DITHERING

	gl_FragColor.rgb = dithering( gl_FragColor.rgb );

#endif
`;var dithering_pars_fragment_glsl_default=`
#ifdef DITHERING

	// based on https://www.shadertoy.com/view/MslGR8
	vec3 dithering( vec3 color ) {
		//Calculate grid position
		float grid_position = rand( gl_FragCoord.xy );

		//Shift the individual colors differently, thus making it even harder to see the dithering pattern
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );

		//modify shift according to grid position.
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );

		//shift the color by dither_shift
		return color + dither_shift_RGB;
	}

#endif
`;var roughnessmap_fragment_glsl_default=`
float roughnessFactor = roughness;

#ifdef USE_ROUGHNESSMAP

	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );

	// reads channel G, compatible with a combined OcclusionRoughnessMetallic (RGB) texture
	roughnessFactor *= texelRoughness.g;

#endif
`;var roughnessmap_pars_fragment_glsl_default=`
#ifdef USE_ROUGHNESSMAP

	uniform sampler2D roughnessMap;

#endif
`;var shadowmap_pars_fragment_glsl_default=`
#if NUM_SPOT_LIGHT_COORDS > 0

	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];

#endif

#if NUM_SPOT_LIGHT_MAPS > 0

	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];

#endif

#ifdef USE_SHADOWMAP

	#if NUM_SUN_LIGHT_SHADOWS > 0

		// must match the cascade count in SunLightShadow

		#define SUN_LIGHT_CASCADES 2

		#if defined( SHADOWMAP_TYPE_PCF )

			uniform sampler2DShadow sunShadowMap[ NUM_SUN_LIGHT_SHADOWS ];

		#else

			uniform sampler2D sunShadowMap[ NUM_SUN_LIGHT_SHADOWS ];

		#endif

		uniform mat4 sunShadowMatrix[ NUM_SUN_LIGHT_SHADOWS * SUN_LIGHT_CASCADES ];
		uniform vec4 sunShadowCascade[ NUM_SUN_LIGHT_SHADOWS * SUN_LIGHT_CASCADES ];
		varying vec4 vSunShadowWorldPosition;
		varying vec3 vSunShadowWorldNormal;

		struct SunLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};

		uniform SunLightShadow sunLightShadows[ NUM_SUN_LIGHT_SHADOWS ];

	#endif

	#if NUM_DIR_LIGHT_SHADOWS > 0

		#if defined( SHADOWMAP_TYPE_PCF )

			uniform sampler2DShadow directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];

		#else

			uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];

		#endif

		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];

		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};

		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];

	#endif

	#if NUM_SPOT_LIGHT_SHADOWS > 0

		#if defined( SHADOWMAP_TYPE_PCF )

			uniform sampler2DShadow spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];

		#else

			uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];

		#endif

		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};

		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];

	#endif

	#if NUM_POINT_LIGHT_SHADOWS > 0

		#if defined( SHADOWMAP_TYPE_PCF )

			uniform samplerCubeShadow pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];

		#elif defined( SHADOWMAP_TYPE_BASIC )

			uniform samplerCube pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];

		#endif

		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];

		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};

		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];

	#endif

	#if defined( SHADOWMAP_TYPE_PCF )

		// Interleaved Gradient Noise for randomizing sampling patterns
		float interleavedGradientNoise( vec2 position ) {

			return fract( 52.9829189 * fract( dot( position, vec2( 0.06711056, 0.00583715 ) ) ) );

		}

		// Vogel disk sampling for uniform circular distribution
		vec2 vogelDiskSample( int sampleIndex, int samplesCount, float phi ) {

			const float goldenAngle = 2.399963229728653;
			float r = sqrt( ( float( sampleIndex ) + 0.5 ) / float( samplesCount ) );
			float theta = float( sampleIndex ) * goldenAngle + phi;
			return vec2( cos( theta ), sin( theta ) ) * r;

		}

	#endif

	#if defined( SHADOWMAP_TYPE_PCF )

		float getShadow( sampler2DShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {

			float shadow = 1.0;

			shadowCoord.xyz /= shadowCoord.w;
			shadowCoord.z += shadowBias;

			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;

			if ( frustumTest ) {

				// Hardware PCF with LinearFilter gives us 4-tap filtering per sample
				// 5 samples using Vogel disk + IGN = effectively 20 filtered taps with better distribution
				vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
				float radius = shadowRadius * texelSize.x;

				// Use IGN to rotate sampling pattern per pixel
				float phi = interleavedGradientNoise( gl_FragCoord.xy ) * PI2;

				shadow = (
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 0, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 1, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 2, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 3, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 4, 5, phi ) * radius, shadowCoord.z ) )
				) * 0.2;

			}

			return mix( 1.0, shadow, shadowIntensity );

		}

	#elif defined( SHADOWMAP_TYPE_VSM )

		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {

			float shadow = 1.0;

			shadowCoord.xyz /= shadowCoord.w;

			#ifdef USE_REVERSED_DEPTH_BUFFER

				shadowCoord.z -= shadowBias;

			#else

				shadowCoord.z += shadowBias;

			#endif

			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;

			if ( frustumTest ) {

				vec2 distribution = texture2D( shadowMap, shadowCoord.xy ).rg;

				float mean = distribution.x;
				float variance = distribution.y * distribution.y;

				#ifdef USE_REVERSED_DEPTH_BUFFER

					float hard_shadow = step( mean, shadowCoord.z );

				#else

					float hard_shadow = step( shadowCoord.z, mean );

				#endif
				
				// Early return if fully lit
				if ( hard_shadow == 1.0 ) {

					shadow = 1.0;

				} else {

					// Variance must be non-zero to avoid division by zero
					variance = max( variance, 0.0000001 );

					// Distance from mean
					float d = shadowCoord.z - mean;

					// Chebyshev's inequality for upper bound on probability
					float p_max = variance / ( variance + d * d );

					// Reduce light bleeding by remapping [amount, 1] to [0, 1]
					p_max = clamp( ( p_max - 0.3 ) / 0.65, 0.0, 1.0 );

					shadow = max( hard_shadow, p_max );

				}

			}

			return mix( 1.0, shadow, shadowIntensity );

		}

	#else // SHADOWMAP_TYPE_BASIC

		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {

			float shadow = 1.0;

			shadowCoord.xyz /= shadowCoord.w;

			#ifdef USE_REVERSED_DEPTH_BUFFER

				shadowCoord.z -= shadowBias;

			#else

				shadowCoord.z += shadowBias;

			#endif

			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;

			if ( frustumTest ) {

				float depth = texture2D( shadowMap, shadowCoord.xy ).r;

				#ifdef USE_REVERSED_DEPTH_BUFFER

					shadow = step( depth, shadowCoord.z );

				#else

					shadow = step( shadowCoord.z, depth );

				#endif

			}

			return mix( 1.0, shadow, shadowIntensity );

		}

	#endif

	#if NUM_SUN_LIGHT_SHADOWS > 0

		float getSunShadow(
			#if defined( SHADOWMAP_TYPE_PCF )
				sampler2DShadow shadowMap,
			#else
				sampler2D shadowMap,
			#endif
			SunLightShadow sunLightShadow,
			int shadowIndex
		) {

			vec4 shadowWorldPosition = vec4( vSunShadowWorldPosition.xyz + vSunShadowWorldNormal * sunLightShadow.shadowNormalBias, 1.0 );
			float viewDepth = vSunShadowWorldPosition.w;
			int cascadeOffset = shadowIndex * SUN_LIGHT_CASCADES;

			float shadow = 1.0;

			// walk the cascades back to front so each fade band can blend with the shadow behind it

			for ( int i = SUN_LIGHT_CASCADES - 1; i >= 0; i -- ) {

				// ( begin, end, fade start ) view depths of the cascade

				vec4 cascade = sunShadowCascade[ cascadeOffset + i ];

				if ( viewDepth >= cascade.x && viewDepth < cascade.y ) {

					float cascadeShadow = getShadow(
						shadowMap,
						sunLightShadow.shadowMapSize,
						sunLightShadow.shadowIntensity,
						sunLightShadow.shadowBias,
						sunLightShadow.shadowRadius,
						sunShadowMatrix[ cascadeOffset + i ] * shadowWorldPosition
					);

					shadow = mix( cascadeShadow, shadow, smoothstep( cascade.z, cascade.y, viewDepth ) );

				}

			}

			return shadow;

		}

	#endif

	#if NUM_POINT_LIGHT_SHADOWS > 0

	#if defined( SHADOWMAP_TYPE_PCF )

	float getPointShadow( samplerCubeShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {

		float shadow = 1.0;

		// for point lights, the uniform @vShadowCoord is re-purposed to hold
		// the vector from the light to the world-space position of the fragment.
		vec3 lightToPosition = shadowCoord.xyz;

		// Direction from light to fragment
		vec3 bd3D = normalize( lightToPosition );

		// For cube shadow maps, depth is stored as distance along each face's view axis, not radial distance
		// The view-space depth is the maximum component of the direction vector (which face is sampled)
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );

		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {

			// viewZ to perspective depth

			#ifdef USE_REVERSED_DEPTH_BUFFER

				float dp = ( shadowCameraNear * ( shadowCameraFar - viewSpaceZ ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
				dp -= shadowBias;

			#else

				float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
				dp += shadowBias;

			#endif

			// Hardware PCF with LinearFilter gives us 4-tap filtering per sample
			// Use Vogel disk + IGN sampling for better quality
			float texelSize = shadowRadius / shadowMapSize.x;

			// Build a tangent-space coordinate system for applying offsets
			vec3 absDir = abs( bd3D );
			vec3 tangent = absDir.x > absDir.z ? vec3( 0.0, 1.0, 0.0 ) : vec3( 1.0, 0.0, 0.0 );
			tangent = normalize( cross( bd3D, tangent ) );
			vec3 bitangent = cross( bd3D, tangent );

			// Use IGN to rotate sampling pattern per pixel
			float phi = interleavedGradientNoise( gl_FragCoord.xy ) * PI2;

			vec2 sample0 = vogelDiskSample( 0, 5, phi );
			vec2 sample1 = vogelDiskSample( 1, 5, phi );
			vec2 sample2 = vogelDiskSample( 2, 5, phi );
			vec2 sample3 = vogelDiskSample( 3, 5, phi );
			vec2 sample4 = vogelDiskSample( 4, 5, phi );

			shadow = (
				texture( shadowMap, vec4( bd3D + ( tangent * sample0.x + bitangent * sample0.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample1.x + bitangent * sample1.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample2.x + bitangent * sample2.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample3.x + bitangent * sample3.y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * sample4.x + bitangent * sample4.y ) * texelSize, dp ) )
			) * 0.2;

		}

		return mix( 1.0, shadow, shadowIntensity );

	}

	#elif defined( SHADOWMAP_TYPE_BASIC )

	float getPointShadow( samplerCube shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {

		float shadow = 1.0;

		// for point lights, the uniform @vShadowCoord is re-purposed to hold
		// the vector from the light to the world-space position of the fragment.
		vec3 lightToPosition = shadowCoord.xyz;

		// For cube shadow maps, depth is stored as distance along each face's view axis, not radial distance
		// The view-space depth is the maximum component of the direction vector (which face is sampled)
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );

		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {

			// viewZ to perspective depth

			float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
			dp += shadowBias;

			// Direction from light to fragment
			vec3 bd3D = normalize( lightToPosition );

			float depth = textureCube( shadowMap, bd3D ).r;

			#ifdef USE_REVERSED_DEPTH_BUFFER

				depth = 1.0 - depth;

			#endif

			shadow = step( dp, depth );

		}

		return mix( 1.0, shadow, shadowIntensity );

	}

	#endif

	#endif

#endif
`;var shadowmap_pars_vertex_glsl_default=`

#if NUM_SPOT_LIGHT_COORDS > 0

	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];

#endif

#ifdef USE_SHADOWMAP

	#if NUM_SUN_LIGHT_SHADOWS > 0

		// cascade selection and shadow coordinates are computed per fragment

		varying vec4 vSunShadowWorldPosition;
		varying vec3 vSunShadowWorldNormal;

	#endif

	#if NUM_DIR_LIGHT_SHADOWS > 0

		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];

		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};

		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];

	#endif

	#if NUM_SPOT_LIGHT_SHADOWS > 0

		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};

		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];

	#endif

	#if NUM_POINT_LIGHT_SHADOWS > 0

		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];

		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};

		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];

	#endif

	/*
	#if NUM_RECT_AREA_LIGHTS > 0

		// TODO (abelnation): uniforms for area light shadows

	#endif
	*/

#endif
`;var shadowmap_vertex_glsl_default=`

#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_SUN_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )

	#ifdef HAS_NORMAL

		// Offsetting the position used for querying occlusion along the world normal can be used to reduce shadow acne.

		vec3 shadowWorldNormal = transformNormalByInverseViewMatrix( transformedNormal, viewMatrix );

	#else

		vec3 shadowWorldNormal = vec3( 0.0 ); // fallback, see #21483

	#endif

	vec4 shadowWorldPosition;

#endif

#if defined( USE_SHADOWMAP )

	#if NUM_SUN_LIGHT_SHADOWS > 0

		vSunShadowWorldPosition = vec4( worldPosition.xyz, - mvPosition.z );
		vSunShadowWorldNormal = shadowWorldNormal;

	#endif

	#if NUM_DIR_LIGHT_SHADOWS > 0

		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {

			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;

		}
		#pragma unroll_loop_end

	#endif

	#if NUM_POINT_LIGHT_SHADOWS > 0

		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {

			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;

		}
		#pragma unroll_loop_end

	#endif

	/*
	#if NUM_RECT_AREA_LIGHTS > 0

		// TODO (abelnation): update vAreaShadowCoord with area light info

	#endif
	*/

#endif

// spot lights can be evaluated without active shadow mapping (when SpotLight.map is used)

#if NUM_SPOT_LIGHT_COORDS > 0

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {

		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;

	}
	#pragma unroll_loop_end

#endif


`;var shadowmask_pars_fragment_glsl_default=`
float getShadowMask() {

	float shadow = 1.0;

	#ifdef USE_SHADOWMAP

	#if NUM_SUN_LIGHT_SHADOWS > 0

	SunLightShadow sunLight;

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SUN_LIGHT_SHADOWS; i ++ ) {

		sunLight = sunLightShadows[ i ];
		shadow *= receiveShadow ? getSunShadow( sunShadowMap[ i ], sunLight, UNROLLED_LOOP_INDEX ) : 1.0;

	}
	#pragma unroll_loop_end

	#endif

	#if NUM_DIR_LIGHT_SHADOWS > 0

	DirectionalLightShadow directionalLight;

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {

		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;

	}
	#pragma unroll_loop_end

	#endif

	#if NUM_SPOT_LIGHT_SHADOWS > 0

	SpotLightShadow spotLight;

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {

		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;

	}
	#pragma unroll_loop_end

	#endif

	#if NUM_POINT_LIGHT_SHADOWS > 0 && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )

	PointLightShadow pointLight;

	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {

		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;

	}
	#pragma unroll_loop_end

	#endif

	/*
	#if NUM_RECT_AREA_LIGHTS > 0

		// TODO (abelnation): update shadow for Area light

	#endif
	*/

	#endif

	return shadow;

}
`;var skinbase_vertex_glsl_default=`
#ifdef USE_SKINNING

	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );

#endif
`;var skinning_pars_vertex_glsl_default=`
#ifdef USE_SKINNING

	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;

	uniform highp sampler2D boneTexture;

	mat4 getBoneMatrix( const in float i ) {

		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );

		return mat4( v1, v2, v3, v4 );

	}

#endif
`;var skinning_vertex_glsl_default=`
#ifdef USE_SKINNING

	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );

	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;

	transformed = ( bindMatrixInverse * skinned ).xyz;

#endif
`;var skinnormal_vertex_glsl_default=`
#ifdef USE_SKINNING

	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;

	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;

	#ifdef USE_TANGENT

		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;

	#endif

#endif
`;var specularmap_fragment_glsl_default=`
float specularStrength;

#ifdef USE_SPECULARMAP

	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;

#else

	specularStrength = 1.0;

#endif
`;var specularmap_pars_fragment_glsl_default=`
#ifdef USE_SPECULARMAP

	uniform sampler2D specularMap;

#endif
`;var tonemapping_fragment_glsl_default=`
#if defined( TONE_MAPPING )

	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );

#endif
`;var tonemapping_pars_fragment_glsl_default=`
#ifndef saturate
// <common> may have defined saturate() already
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif

uniform float toneMappingExposure;

// exposure only
vec3 LinearToneMapping( vec3 color ) {

	return saturate( toneMappingExposure * color );

}

// source: https://www.cs.utah.edu/docs/techreports/2002/pdf/UUCS-02-001.pdf
vec3 ReinhardToneMapping( vec3 color ) {

	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );

}

// source: http://filmicworlds.com/blog/filmic-tonemapping-operators/
vec3 CineonToneMapping( vec3 color ) {

	// filmic operator by Jim Hejl and Richard Burgess-Dawson
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );

}

// source: https://github.com/selfshadow/ltc_code/blob/master/webgl/shaders/ltc/ltc_blit.fs
vec3 RRTAndODTFit( vec3 v ) {

	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;

}

// this implementation of ACES is modified to accommodate a brighter viewing environment.
// the scale factor of 1/0.6 is subjective. see discussion in #19621.

vec3 ACESFilmicToneMapping( vec3 color ) {

	// sRGB => XYZ => D65_2_D60 => AP1 => RRT_SAT
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ), // transposed from source
		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);

	// ODT_SAT => XYZ => D60_2_D65 => sRGB
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ), // transposed from source
		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);

	color *= toneMappingExposure / 0.6;

	color = ACESInputMat * color;

	// Apply RRT and ODT
	color = RRTAndODTFit( color );

	color = ACESOutputMat * color;

	// Clamp to [0, 1]
	return saturate( color );

}

// Matrices for rec 2020 <> rec 709 color space conversion
// matrix provided in row-major order so it has been transposed
// https://www.itu.int/pub/R-REP-BT.2407-2017
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);

const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);

// https://iolite-engine.com/blog_posts/minimal_agx_implementation
// Mean error^2: 3.6705141e-06
vec3 agxDefaultContrastApprox( vec3 x ) {

	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;

	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;

}

// AgX Tone Mapping implementation based on Filament, which in turn is based
// on Blender's implementation using rec 2020 primaries
// https://github.com/google/filament/pull/7236
// Inputs and outputs are encoded as Linear-sRGB.

vec3 AgXToneMapping( vec3 color ) {

	// AgX constants
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);

	// explicit AgXOutsetMatrix generated from Filaments AgXOutsetMatrixInv
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);

	// LOG2_MIN      = -10.0
	// LOG2_MAX      =  +6.5
	// MIDDLE_GRAY   =  0.18
	const float AgxMinEv = - 12.47393;  // log2( pow( 2, LOG2_MIN ) * MIDDLE_GRAY )
	const float AgxMaxEv = 4.026069;    // log2( pow( 2, LOG2_MAX ) * MIDDLE_GRAY )

	color *= toneMappingExposure;

	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;

	color = AgXInsetMatrix * color;

	// Log2 encoding
	color = max( color, 1e-10 ); // avoid 0 or negative numbers for log2
	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );

	color = clamp( color, 0.0, 1.0 );

	// Apply sigmoid
	color = agxDefaultContrastApprox( color );

	// Apply AgX look
	// v = agxLook(v, look);

	color = AgXOutsetMatrix * color;

	// Linearize
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );

	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;

	// Gamut mapping. Simple clamp for now.
	color = clamp( color, 0.0, 1.0 );

	return color;

}

// https://modelviewer.dev/examples/tone-mapping

vec3 NeutralToneMapping( vec3 color ) {

	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;

	color *= toneMappingExposure;

	float x = min( color.r, min( color.g, color.b ) );

	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;

	color -= offset;

	float peak = max( color.r, max( color.g, color.b ) );

	if ( peak < StartCompression ) return color;

	float d = 1. - StartCompression;

	float newPeak = 1. - d * d / ( peak + d - StartCompression );

	color *= newPeak / peak;

	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );

	return mix( color, vec3( newPeak ), g );

}

vec3 CustomToneMapping( vec3 color ) { return color; }
`;var transmission_fragment_glsl_default=`
#ifdef USE_TRANSMISSION

	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;

	#ifdef USE_TRANSMISSIONMAP

		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;

	#endif

	#ifdef USE_THICKNESSMAP

		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;

	#endif

	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = transformNormalByInverseViewMatrix( normal, viewMatrix );

	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseContribution, material.specularColorBlended, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );

	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );

	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );

#endif
`;var transmission_pars_fragment_glsl_default=`
#ifdef USE_TRANSMISSION

	// Transmission code is based on glTF-Sampler-Viewer
	// https://github.com/KhronosGroup/glTF-Sample-Viewer

	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;

	#ifdef USE_TRANSMISSIONMAP

		uniform sampler2D transmissionMap;

	#endif

	#ifdef USE_THICKNESSMAP

		uniform sampler2D thicknessMap;

	#endif

	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;

	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;

	varying vec3 vWorldPosition;

	// Mipped Bicubic Texture Filtering by N8
	// https://www.shadertoy.com/view/Dl2SDW

	float w0( float a ) {

		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );

	}

	float w1( float a ) {

		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );

	}

	float w2( float a ){

		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );

	}

	float w3( float a ) {

		return ( 1.0 / 6.0 ) * ( a * a * a );

	}

	// g0 and g1 are the two amplitude functions
	float g0( float a ) {

		return w0( a ) + w1( a );

	}

	float g1( float a ) {

		return w2( a ) + w3( a );

	}

	// h0 and h1 are the two offset functions
	float h0( float a ) {

		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );

	}

	float h1( float a ) {

		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );

	}

	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {

		uv = uv * texelSize.zw + 0.5;

		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );

		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );

		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;

		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );

	}

	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {

		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );

	}

	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {

		// Direction of refracted light.
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );

		// Compute rotation-independent scaling of the model matrix.
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );

		// The thickness is specified in local space.
		return normalize( refractionVector ) * thickness * modelScale;

	}

	float applyIorToRoughness( const in float roughness, const in float ior ) {

		// Scale roughness with IOR so that an IOR of 1.0 results in no microfacet refraction and
		// an IOR of 1.5 results in the default amount of microfacet refraction.
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );

	}

	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {

		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );

	}

	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {

		if ( isinf( attenuationDistance ) ) {

			// Attenuation distance is +\u221E, i.e. the transmitted color is not attenuated at all.
			return vec3( 1.0 );

		} else {

			// Compute light attenuation using Beer's law.
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance ); // Beer's law
			return transmittance;

		}

	}

	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {

		vec4 transmittedLight;
		vec3 transmittance;

		#ifdef USE_DISPERSION

			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );

			for ( int i = 0; i < 3; i ++ ) {

				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;

				// Project refracted vector on the framebuffer, while mapping to normalized device coordinates.
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;

				// Sample framebuffer to get pixel the refracted ray hits.
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;

				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];

			}

			transmittedLight.a /= 3.0;

		#else

			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;

			// Project refracted vector on the framebuffer, while mapping to normalized device coordinates.
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;

			// Sample framebuffer to get pixel the refracted ray hits.
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );

		#endif

		vec3 attenuatedColor = transmittance * transmittedLight.rgb;

		// Get the specular component.
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );

		// As less light is transmitted, the opacity should be increased. This simple approximation does a decent job
		// of modulating a CSS background, and has no effect when the buffer is opaque, due to a solid object or clear color.
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;

		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );

	}
#endif
`;var uv_pars_fragment_glsl_default=`
#if defined( USE_UV ) || defined( USE_ANISOTROPY )

	varying vec2 vUv;

#endif
#ifdef USE_MAP

	varying vec2 vMapUv;

#endif
#ifdef USE_ALPHAMAP

	varying vec2 vAlphaMapUv;

#endif
#ifdef USE_LIGHTMAP

	varying vec2 vLightMapUv;

#endif
#ifdef USE_AOMAP

	varying vec2 vAoMapUv;

#endif
#ifdef USE_BUMPMAP

	varying vec2 vBumpMapUv;

#endif
#ifdef USE_NORMALMAP

	varying vec2 vNormalMapUv;

#endif
#ifdef USE_EMISSIVEMAP

	varying vec2 vEmissiveMapUv;

#endif
#ifdef USE_METALNESSMAP

	varying vec2 vMetalnessMapUv;

#endif
#ifdef USE_ROUGHNESSMAP

	varying vec2 vRoughnessMapUv;

#endif
#ifdef USE_ANISOTROPYMAP

	varying vec2 vAnisotropyMapUv;

#endif
#ifdef USE_CLEARCOATMAP

	varying vec2 vClearcoatMapUv;

#endif
#ifdef USE_CLEARCOAT_NORMALMAP

	varying vec2 vClearcoatNormalMapUv;

#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP

	varying vec2 vClearcoatRoughnessMapUv;

#endif
#ifdef USE_IRIDESCENCEMAP

	varying vec2 vIridescenceMapUv;

#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP

	varying vec2 vIridescenceThicknessMapUv;

#endif
#ifdef USE_SHEEN_COLORMAP

	varying vec2 vSheenColorMapUv;

#endif
#ifdef USE_SHEEN_ROUGHNESSMAP

	varying vec2 vSheenRoughnessMapUv;

#endif
#ifdef USE_SPECULARMAP

	varying vec2 vSpecularMapUv;

#endif
#ifdef USE_SPECULAR_COLORMAP

	varying vec2 vSpecularColorMapUv;

#endif
#ifdef USE_SPECULAR_INTENSITYMAP

	varying vec2 vSpecularIntensityMapUv;

#endif
#ifdef USE_TRANSMISSIONMAP

	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;

#endif
#ifdef USE_THICKNESSMAP

	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;

#endif
`;var uv_pars_vertex_glsl_default=`
#if defined( USE_UV ) || defined( USE_ANISOTROPY )

	varying vec2 vUv;

#endif
#ifdef USE_MAP

	uniform mat3 mapTransform;
	varying vec2 vMapUv;

#endif
#ifdef USE_ALPHAMAP

	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;

#endif
#ifdef USE_LIGHTMAP

	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;

#endif
#ifdef USE_AOMAP

	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;

#endif
#ifdef USE_BUMPMAP

	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;

#endif
#ifdef USE_NORMALMAP

	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;

#endif
#ifdef USE_DISPLACEMENTMAP

	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;

#endif
#ifdef USE_EMISSIVEMAP

	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;

#endif
#ifdef USE_METALNESSMAP

	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;

#endif
#ifdef USE_ROUGHNESSMAP

	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;

#endif
#ifdef USE_ANISOTROPYMAP

	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;

#endif
#ifdef USE_CLEARCOATMAP

	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;

#endif
#ifdef USE_CLEARCOAT_NORMALMAP

	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;

#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP

	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;

#endif
#ifdef USE_SHEEN_COLORMAP

	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;

#endif
#ifdef USE_SHEEN_ROUGHNESSMAP

	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;

#endif
#ifdef USE_IRIDESCENCEMAP

	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;

#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP

	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;

#endif
#ifdef USE_SPECULARMAP

	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;

#endif
#ifdef USE_SPECULAR_COLORMAP

	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;

#endif
#ifdef USE_SPECULAR_INTENSITYMAP

	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;

#endif
#ifdef USE_TRANSMISSIONMAP

	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;

#endif
#ifdef USE_THICKNESSMAP

	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;

#endif
`;var uv_vertex_glsl_default=`
#if defined( USE_UV ) || defined( USE_ANISOTROPY )

	vUv = vec3( uv, 1 ).xy;

#endif
#ifdef USE_MAP

	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;

#endif
#ifdef USE_ALPHAMAP

	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_LIGHTMAP

	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_AOMAP

	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_BUMPMAP

	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_NORMALMAP

	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_DISPLACEMENTMAP

	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_EMISSIVEMAP

	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_METALNESSMAP

	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_ROUGHNESSMAP

	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_ANISOTROPYMAP

	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_CLEARCOATMAP

	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_CLEARCOAT_NORMALMAP

	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP

	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_IRIDESCENCEMAP

	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP

	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_SHEEN_COLORMAP

	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_SHEEN_ROUGHNESSMAP

	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_SPECULARMAP

	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_SPECULAR_COLORMAP

	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_SPECULAR_INTENSITYMAP

	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_TRANSMISSIONMAP

	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;

#endif
#ifdef USE_THICKNESSMAP

	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;

#endif
`;var worldpos_vertex_glsl_default=`
#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0

	vec4 worldPosition = vec4( transformed, 1.0 );

	#ifdef USE_BATCHING

		worldPosition = batchingMatrix * worldPosition;

	#endif

	#ifdef USE_INSTANCING

		worldPosition = instanceMatrix * worldPosition;

	#endif

	worldPosition = modelMatrix * worldPosition;

#endif
`;var vertex=`
varying vec2 vUv;
uniform mat3 uvTransform;

void main() {

	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;

	gl_Position = vec4( position.xy, 1.0, 1.0 );

}
`,fragment=`
uniform sampler2D t2D;
uniform float backgroundIntensity;

varying vec2 vUv;

void main() {

	vec4 texColor = texture2D( t2D, vUv );

	#ifdef DECODE_VIDEO_TEXTURE

		// use inline sRGB decode until browsers properly support SRGB8_ALPHA8 with video textures

		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );

	#endif

	texColor.rgb *= backgroundIntensity;

	gl_FragColor = texColor;

	#include <tonemapping_fragment>
	#include <colorspace_fragment>

}
`;var vertex2=`
varying vec3 vWorldDirection;

#include <common>

void main() {

	vWorldDirection = transformDirection( position, modelMatrix );

	#include <begin_vertex>
	#include <project_vertex>

	gl_Position.z = gl_Position.w; // set z to camera.far

}
`,fragment2=`

#ifdef ENVMAP_TYPE_CUBE

	uniform samplerCube envMap;

#elif defined( ENVMAP_TYPE_CUBE_UV )

	uniform sampler2D envMap;

#endif

uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;

varying vec3 vWorldDirection;

#include <cube_uv_reflection_fragment>

void main() {

	#ifdef ENVMAP_TYPE_CUBE

		vec4 texColor = textureCube( envMap, backgroundRotation * vWorldDirection );

	#elif defined( ENVMAP_TYPE_CUBE_UV )

		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );

	#else

		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );

	#endif

	texColor.rgb *= backgroundIntensity;

	gl_FragColor = texColor;

	#include <tonemapping_fragment>
	#include <colorspace_fragment>

}
`;var vertex3=`
varying vec3 vWorldDirection;

#include <common>

void main() {

	vWorldDirection = transformDirection( position, modelMatrix );

	#include <begin_vertex>
	#include <project_vertex>

	gl_Position.z = gl_Position.w; // set z to camera.far

}
`,fragment3=`
uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;

varying vec3 vWorldDirection;

void main() {

	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );

	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;

	#include <tonemapping_fragment>
	#include <colorspace_fragment>

}
`;var vertex4=`
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

// This is used for computing an equivalent of gl_FragCoord.z that is as high precision as possible.
// Some platforms compute gl_FragCoord at a lower precision which makes the manually computed value better for
// depth-based postprocessing effects. Reproduced on iPad with A10 processor / iPadOS 13.3.1.
varying vec2 vHighPrecisionZW;

void main() {

	#include <uv_vertex>

	#include <batching_vertex>
	#include <skinbase_vertex>

	#include <morphinstance_vertex>

	#ifdef USE_DISPLACEMENTMAP

		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>

	#endif

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>

	vHighPrecisionZW = gl_Position.zw;

}
`,fragment4=`
#if DEPTH_PACKING == 3200

	uniform float opacity;

#endif

#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

varying vec2 vHighPrecisionZW;

void main() {

	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>

	#if DEPTH_PACKING == 3200

		diffuseColor.a = opacity;

	#endif

	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>

	#include <logdepthbuf_fragment>

	// Higher precision equivalent of gl_FragCoord.z

	#ifdef USE_REVERSED_DEPTH_BUFFER

		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];

	#else

		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;

	#endif

	#if DEPTH_PACKING == 3200

		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );

	#elif DEPTH_PACKING == 3201

		// TODO Deprecate
		gl_FragColor = packDepthToRGBA( fragCoordZ );

	#elif DEPTH_PACKING == 3202

		// TODO Deprecate
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );

	#elif DEPTH_PACKING == 3203

		// TODO Deprecate
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );

	#endif

}
`;var vertex5=`
#define DISTANCE

varying vec3 vWorldPosition;

#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>

	#include <batching_vertex>
	#include <skinbase_vertex>

	#include <morphinstance_vertex>

	#ifdef USE_DISPLACEMENTMAP

		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>

	#endif

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>

	vWorldPosition = worldPosition.xyz;

}
`,fragment5=`
#define DISTANCE

uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;

#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>

	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>

	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist ); // clamp to [ 0, 1 ]

	gl_FragColor = vec4( dist, 0.0, 0.0, 1.0 );

}
`;var vertex6=`
varying vec3 vWorldDirection;

#include <common>

void main() {

	vWorldDirection = transformDirection( position, modelMatrix );

	#include <begin_vertex>
	#include <project_vertex>

}
`,fragment6=`
uniform sampler2D tEquirect;

varying vec3 vWorldDirection;

#include <common>

void main() {

	vec3 direction = normalize( vWorldDirection );

	vec2 sampleUV = equirectUv( direction );

	gl_FragColor = texture2D( tEquirect, sampleUV );

	#include <tonemapping_fragment>
	#include <colorspace_fragment>

}
`;var vertex7=`
uniform float scale;
attribute float lineDistance;

varying float vLineDistance;

#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	vLineDistance = scale * lineDistance;

	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>

}
`,fragment7=`
uniform vec3 diffuse;
uniform float opacity;

uniform float dashSize;
uniform float totalSize;

varying float vLineDistance;

#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	if ( mod( vLineDistance, totalSize ) > dashSize ) {

		discard;

	}

	vec3 outgoingLight = vec3( 0.0 );

	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>

	outgoingLight = diffuseColor.rgb; // simple shader

	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>

}
`;var vertex8=`
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>

	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )

		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>

	#endif

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>

	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>

}
`,fragment8=`
uniform vec3 diffuse;
uniform float opacity;

#ifndef FLAT_SHADED

	varying vec3 vNormal;

#endif

#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>

	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );

	// accumulation (baked indirect lighting only)
	#ifdef USE_LIGHTMAP

		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;

	#else

		reflectedLight.indirectDiffuse += vec3( 1.0 );

	#endif

	// modulation
	#include <aomap_fragment>

	reflectedLight.indirectDiffuse *= diffuseColor.rgb;

	vec3 outgoingLight = reflectedLight.indirectDiffuse;

	#include <envmap_fragment>

	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>

}
`;var vertex9=`
#define LAMBERT

varying vec3 vViewPosition;

#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>

	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>

	vViewPosition = - mvPosition.xyz;

	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>

}
`,fragment9=`
#define LAMBERT

uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;

#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;

	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>

	// accumulation
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>

	// modulation
	#include <aomap_fragment>

	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;

	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>

}
`;var vertex10=`
#define MATCAP

varying vec3 vViewPosition;

#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>

#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>

	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>

	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>

	vViewPosition = - mvPosition.xyz;

}
`,fragment10=`
#define MATCAP

uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;

varying vec3 vViewPosition;

#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>

	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5; // 0.495 to remove artifacts caused by undersized matcap disks

	#ifdef USE_MATCAP

		vec4 matcapColor = texture2D( matcap, uv );

	#else

		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 ); // default if matcap is missing

	#endif

	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;

	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>

}
`;var vertex11=`
#define NORMAL

#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )

	varying vec3 vViewPosition;

#endif

#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>
	#include <batching_vertex>

	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>

#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )

	vViewPosition = - mvPosition.xyz;

#endif

}
`,fragment11=`
#define NORMAL

uniform float opacity;

#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )

	varying vec3 vViewPosition;

#endif

#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );

	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>

	gl_FragColor = vec4( normalize( normal ) * 0.5 + 0.5, diffuseColor.a );

	#ifdef OPAQUE

		gl_FragColor.a = 1.0;

	#endif

}
`;var vertex12=`
#define PHONG

varying vec3 vViewPosition;

#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>

	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>

	vViewPosition = - mvPosition.xyz;

	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>

}
`,fragment12=`
#define PHONG

uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;

#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;

	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>

	// accumulation
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>

	// modulation
	#include <aomap_fragment>

	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;

	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>

}
`;var vertex13=`
#define STANDARD

varying vec3 vViewPosition;

#ifdef USE_TRANSMISSION

	varying vec3 vWorldPosition;

#endif

#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>

	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>

	vViewPosition = - mvPosition.xyz;

	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>

#ifdef USE_TRANSMISSION

	vWorldPosition = worldPosition.xyz;

#endif
}
`,fragment13=`
#define STANDARD

#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif

uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;

#ifdef IOR
	uniform float ior;
#endif

#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;

	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif

	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif

#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif

#ifdef USE_DISPERSION
	uniform float dispersion;
#endif

#ifdef USE_RETROREFLECTION
	uniform float retroreflectivity;
#endif

#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif

#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;

	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif

	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif

#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;

	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif

varying vec3 vViewPosition;

#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;

	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>

	// accumulation
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>

	// modulation
	#include <aomap_fragment>

	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;

	#include <transmission_fragment>

	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;

	#ifdef USE_SHEEN
 
		outgoingLight = outgoingLight + sheenSpecularDirect + sheenSpecularIndirect;
 
 	#endif

	#ifdef USE_CLEARCOAT

		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );

		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );

		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;

	#endif

	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>

}
`;var vertex14=`
#define TOON

varying vec3 vViewPosition;

#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>

	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>

	vViewPosition = - mvPosition.xyz;

	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>

}
`,fragment14=`
#define TOON

uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;

#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;

	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>

	// accumulation
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>

	// modulation
	#include <aomap_fragment>

	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;

	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>

}
`;var vertex15=`
uniform float size;
uniform float scale;

#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

#ifdef USE_POINTS_UV

	varying vec2 vUv;
	uniform mat3 uvTransform;

#endif

void main() {

	#ifdef USE_POINTS_UV

		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;

	#endif

	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>

	gl_PointSize = size;

	#ifdef USE_SIZEATTENUATION

		bool isPerspective = isPerspectiveMatrix( projectionMatrix );

		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );

	#endif

	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>

}
`,fragment15=`
uniform vec3 diffuse;
uniform float opacity;

#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	vec3 outgoingLight = vec3( 0.0 );

	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>

	outgoingLight = diffuseColor.rgb;

	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>

}
`;var vertex16=`
#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>

void main() {

	#include <batching_vertex>

	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>

	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>

	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>

}
`,fragment16=`
uniform vec3 color;
uniform float opacity;

#include <common>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>

void main() {

	#include <logdepthbuf_fragment>

	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );

	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>

}
`;var vertex17=`
uniform float rotation;
uniform vec2 center;

#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>

void main() {

	#include <uv_vertex>

	vec4 mvPosition = modelViewMatrix[ 3 ];

	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );

	#ifndef USE_SIZEATTENUATION

		bool isPerspective = isPerspectiveMatrix( projectionMatrix );

		if ( isPerspective ) scale *= - mvPosition.z;

	#endif

	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;

	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;

	mvPosition.xy += rotatedPosition;

	gl_Position = projectionMatrix * mvPosition;

	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>

}
`,fragment17=`
uniform vec3 diffuse;
uniform float opacity;

#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>

void main() {

	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>

	vec3 outgoingLight = vec3( 0.0 );

	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>

	outgoingLight = diffuseColor.rgb;

	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>

}
`;var ShaderChunk={alphahash_fragment:alphahash_fragment_glsl_default,alphahash_pars_fragment:alphahash_pars_fragment_glsl_default,alphamap_fragment:alphamap_fragment_glsl_default,alphamap_pars_fragment:alphamap_pars_fragment_glsl_default,alphatest_fragment:alphatest_fragment_glsl_default,alphatest_pars_fragment:alphatest_pars_fragment_glsl_default,aomap_fragment:aomap_fragment_glsl_default,aomap_pars_fragment:aomap_pars_fragment_glsl_default,batching_pars_vertex:batching_pars_vertex_glsl_default,batching_vertex:batching_vertex_glsl_default,begin_vertex:begin_vertex_glsl_default,beginnormal_vertex:beginnormal_vertex_glsl_default,bsdfs:bsdfs_glsl_default,iridescence_fragment:iridescence_fragment_glsl_default,bumpmap_pars_fragment:bumpmap_pars_fragment_glsl_default,clipping_planes_fragment:clipping_planes_fragment_glsl_default,clipping_planes_pars_fragment:clipping_planes_pars_fragment_glsl_default,clipping_planes_pars_vertex:clipping_planes_pars_vertex_glsl_default,clipping_planes_vertex:clipping_planes_vertex_glsl_default,color_fragment:color_fragment_glsl_default,color_pars_fragment:color_pars_fragment_glsl_default,color_pars_vertex:color_pars_vertex_glsl_default,color_vertex:color_vertex_glsl_default,common:common_glsl_default,cube_uv_reflection_fragment:cube_uv_reflection_fragment_glsl_default,defaultnormal_vertex:defaultnormal_vertex_glsl_default,displacementmap_pars_vertex:displacementmap_pars_vertex_glsl_default,displacementmap_vertex:displacementmap_vertex_glsl_default,emissivemap_fragment:emissivemap_fragment_glsl_default,emissivemap_pars_fragment:emissivemap_pars_fragment_glsl_default,colorspace_fragment:colorspace_fragment_glsl_default,colorspace_pars_fragment:colorspace_pars_fragment_glsl_default,envmap_fragment:envmap_fragment_glsl_default,envmap_common_pars_fragment:envmap_common_pars_fragment_glsl_default,envmap_pars_fragment:envmap_pars_fragment_glsl_default,envmap_pars_vertex:envmap_pars_vertex_glsl_default,envmap_physical_pars_fragment:envmap_physical_pars_fragment_glsl_default,envmap_vertex:envmap_vertex_glsl_default,fog_vertex:fog_vertex_glsl_default,fog_pars_vertex:fog_pars_vertex_glsl_default,fog_fragment:fog_fragment_glsl_default,fog_pars_fragment:fog_pars_fragment_glsl_default,gradientmap_pars_fragment:gradientmap_pars_fragment_glsl_default,lightmap_pars_fragment:lightmap_pars_fragment_glsl_default,lights_lambert_fragment:lights_lambert_fragment_glsl_default,lights_lambert_pars_fragment:lights_lambert_pars_fragment_glsl_default,lights_pars_begin:lights_pars_begin_glsl_default,lights_toon_fragment:lights_toon_fragment_glsl_default,lights_toon_pars_fragment:lights_toon_pars_fragment_glsl_default,lights_phong_fragment:lights_phong_fragment_glsl_default,lights_phong_pars_fragment:lights_phong_pars_fragment_glsl_default,lights_physical_fragment:lights_physical_fragment_glsl_default,lights_physical_pars_fragment:lights_physical_pars_fragment_glsl_default,lights_fragment_begin:lights_fragment_begin_glsl_default,lights_fragment_maps:lights_fragment_maps_glsl_default,lights_fragment_end:lights_fragment_end_glsl_default,lightprobes_pars_fragment:lightprobes_pars_fragment_glsl_default,logdepthbuf_fragment:logdepthbuf_fragment_glsl_default,logdepthbuf_pars_fragment:logdepthbuf_pars_fragment_glsl_default,logdepthbuf_pars_vertex:logdepthbuf_pars_vertex_glsl_default,logdepthbuf_vertex:logdepthbuf_vertex_glsl_default,map_fragment:map_fragment_glsl_default,map_pars_fragment:map_pars_fragment_glsl_default,map_particle_fragment:map_particle_fragment_glsl_default,map_particle_pars_fragment:map_particle_pars_fragment_glsl_default,metalnessmap_fragment:metalnessmap_fragment_glsl_default,metalnessmap_pars_fragment:metalnessmap_pars_fragment_glsl_default,morphinstance_vertex:morphinstance_vertex_glsl_default,morphcolor_vertex:morphcolor_vertex_glsl_default,morphnormal_vertex:morphnormal_vertex_glsl_default,morphtarget_pars_vertex:morphtarget_pars_vertex_glsl_default,morphtarget_vertex:morphtarget_vertex_glsl_default,normal_fragment_begin:normal_fragment_begin_glsl_default,normal_fragment_maps:normal_fragment_maps_glsl_default,normal_pars_fragment:normal_pars_fragment_glsl_default,normal_pars_vertex:normal_pars_vertex_glsl_default,normal_vertex:normal_vertex_glsl_default,normalmap_pars_fragment:normalmap_pars_fragment_glsl_default,clearcoat_normal_fragment_begin:clearcoat_normal_fragment_begin_glsl_default,clearcoat_normal_fragment_maps:clearcoat_normal_fragment_maps_glsl_default,clearcoat_pars_fragment:clearcoat_pars_fragment_glsl_default,iridescence_pars_fragment:iridescence_pars_fragment_glsl_default,opaque_fragment:opaque_fragment_glsl_default,packing:packing_glsl_default,premultiplied_alpha_fragment:premultiplied_alpha_fragment_glsl_default,project_vertex:project_vertex_glsl_default,dithering_fragment:dithering_fragment_glsl_default,dithering_pars_fragment:dithering_pars_fragment_glsl_default,roughnessmap_fragment:roughnessmap_fragment_glsl_default,roughnessmap_pars_fragment:roughnessmap_pars_fragment_glsl_default,shadowmap_pars_fragment:shadowmap_pars_fragment_glsl_default,shadowmap_pars_vertex:shadowmap_pars_vertex_glsl_default,shadowmap_vertex:shadowmap_vertex_glsl_default,shadowmask_pars_fragment:shadowmask_pars_fragment_glsl_default,skinbase_vertex:skinbase_vertex_glsl_default,skinning_pars_vertex:skinning_pars_vertex_glsl_default,skinning_vertex:skinning_vertex_glsl_default,skinnormal_vertex:skinnormal_vertex_glsl_default,specularmap_fragment:specularmap_fragment_glsl_default,specularmap_pars_fragment:specularmap_pars_fragment_glsl_default,tonemapping_fragment:tonemapping_fragment_glsl_default,tonemapping_pars_fragment:tonemapping_pars_fragment_glsl_default,transmission_fragment:transmission_fragment_glsl_default,transmission_pars_fragment:transmission_pars_fragment_glsl_default,uv_pars_fragment:uv_pars_fragment_glsl_default,uv_pars_vertex:uv_pars_vertex_glsl_default,uv_vertex:uv_vertex_glsl_default,worldpos_vertex:worldpos_vertex_glsl_default,background_vert:vertex,background_frag:fragment,backgroundCube_vert:vertex2,backgroundCube_frag:fragment2,cube_vert:vertex3,cube_frag:fragment3,depth_vert:vertex4,depth_frag:fragment4,distance_vert:vertex5,distance_frag:fragment5,equirect_vert:vertex6,equirect_frag:fragment6,linedashed_vert:vertex7,linedashed_frag:fragment7,meshbasic_vert:vertex8,meshbasic_frag:fragment8,meshlambert_vert:vertex9,meshlambert_frag:fragment9,meshmatcap_vert:vertex10,meshmatcap_frag:fragment10,meshnormal_vert:vertex11,meshnormal_frag:fragment11,meshphong_vert:vertex12,meshphong_frag:fragment12,meshphysical_vert:vertex13,meshphysical_frag:fragment13,meshtoon_vert:vertex14,meshtoon_frag:fragment14,points_vert:vertex15,points_frag:fragment15,shadow_vert:vertex16,shadow_frag:fragment16,sprite_vert:vertex17,sprite_frag:fragment17};var UniformsLib={common:{diffuse:{value:new Color(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new Matrix3},alphaMap:{value:null},alphaMapTransform:{value:new Matrix3},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new Matrix3}},envmap:{envMap:{value:null},envMapRotation:{value:new Matrix3},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98},dfgLUT:{value:null}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new Matrix3}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new Matrix3}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new Matrix3},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new Matrix3},normalScale:{value:new Vector2(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new Matrix3},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new Matrix3}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new Matrix3}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new Matrix3}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new Color(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},sunLights:{value:[],properties:{direction:{},color:{}}},sunLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},sunShadowMatrix:{value:[]},sunShadowCascade:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null},probesSH:{value:null},probesMin:{value:new Vector3},probesMax:{value:new Vector3},probesResolution:{value:new Vector3}},points:{diffuse:{value:new Color(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new Matrix3},alphaTest:{value:0},uvTransform:{value:new Matrix3}},sprite:{diffuse:{value:new Color(16777215)},opacity:{value:1},center:{value:new Vector2(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new Matrix3},alphaMap:{value:null},alphaMapTransform:{value:new Matrix3},alphaTest:{value:0}}};var ShaderLib={basic:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.specularmap,UniformsLib.envmap,UniformsLib.aomap,UniformsLib.lightmap,UniformsLib.fog]),vertexShader:ShaderChunk.meshbasic_vert,fragmentShader:ShaderChunk.meshbasic_frag},lambert:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.specularmap,UniformsLib.envmap,UniformsLib.aomap,UniformsLib.lightmap,UniformsLib.emissivemap,UniformsLib.bumpmap,UniformsLib.normalmap,UniformsLib.displacementmap,UniformsLib.fog,UniformsLib.lights,{emissive:{value:new Color(0)},envMapIntensity:{value:1}}]),vertexShader:ShaderChunk.meshlambert_vert,fragmentShader:ShaderChunk.meshlambert_frag},phong:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.specularmap,UniformsLib.envmap,UniformsLib.aomap,UniformsLib.lightmap,UniformsLib.emissivemap,UniformsLib.bumpmap,UniformsLib.normalmap,UniformsLib.displacementmap,UniformsLib.fog,UniformsLib.lights,{emissive:{value:new Color(0)},specular:{value:new Color(1118481)},shininess:{value:30},envMapIntensity:{value:1}}]),vertexShader:ShaderChunk.meshphong_vert,fragmentShader:ShaderChunk.meshphong_frag},standard:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.envmap,UniformsLib.aomap,UniformsLib.lightmap,UniformsLib.emissivemap,UniformsLib.bumpmap,UniformsLib.normalmap,UniformsLib.displacementmap,UniformsLib.roughnessmap,UniformsLib.metalnessmap,UniformsLib.fog,UniformsLib.lights,{emissive:{value:new Color(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:ShaderChunk.meshphysical_vert,fragmentShader:ShaderChunk.meshphysical_frag},toon:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.aomap,UniformsLib.lightmap,UniformsLib.emissivemap,UniformsLib.bumpmap,UniformsLib.normalmap,UniformsLib.displacementmap,UniformsLib.gradientmap,UniformsLib.fog,UniformsLib.lights,{emissive:{value:new Color(0)}}]),vertexShader:ShaderChunk.meshtoon_vert,fragmentShader:ShaderChunk.meshtoon_frag},matcap:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.bumpmap,UniformsLib.normalmap,UniformsLib.displacementmap,UniformsLib.fog,{matcap:{value:null}}]),vertexShader:ShaderChunk.meshmatcap_vert,fragmentShader:ShaderChunk.meshmatcap_frag},points:{uniforms:mergeUniforms([UniformsLib.points,UniformsLib.fog]),vertexShader:ShaderChunk.points_vert,fragmentShader:ShaderChunk.points_frag},dashed:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:ShaderChunk.linedashed_vert,fragmentShader:ShaderChunk.linedashed_frag},depth:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.displacementmap]),vertexShader:ShaderChunk.depth_vert,fragmentShader:ShaderChunk.depth_frag},normal:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.bumpmap,UniformsLib.normalmap,UniformsLib.displacementmap,{opacity:{value:1}}]),vertexShader:ShaderChunk.meshnormal_vert,fragmentShader:ShaderChunk.meshnormal_frag},sprite:{uniforms:mergeUniforms([UniformsLib.sprite,UniformsLib.fog]),vertexShader:ShaderChunk.sprite_vert,fragmentShader:ShaderChunk.sprite_frag},background:{uniforms:{uvTransform:{value:new Matrix3},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:ShaderChunk.background_vert,fragmentShader:ShaderChunk.background_frag},backgroundCube:{uniforms:{envMap:{value:null},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new Matrix3}},vertexShader:ShaderChunk.backgroundCube_vert,fragmentShader:ShaderChunk.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:ShaderChunk.cube_vert,fragmentShader:ShaderChunk.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:ShaderChunk.equirect_vert,fragmentShader:ShaderChunk.equirect_frag},distance:{uniforms:mergeUniforms([UniformsLib.common,UniformsLib.displacementmap,{referencePosition:{value:new Vector3},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:ShaderChunk.distance_vert,fragmentShader:ShaderChunk.distance_frag},shadow:{uniforms:mergeUniforms([UniformsLib.lights,UniformsLib.fog,{color:{value:new Color(0)},opacity:{value:1}}]),vertexShader:ShaderChunk.shadow_vert,fragmentShader:ShaderChunk.shadow_frag}};ShaderLib.physical={uniforms:mergeUniforms([ShaderLib.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new Matrix3},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new Matrix3},clearcoatNormalScale:{value:new Vector2(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new Matrix3},dispersion:{value:0},retroreflectivity:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new Matrix3},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new Matrix3},sheen:{value:0},sheenColor:{value:new Color(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new Matrix3},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new Matrix3},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new Matrix3},transmissionSamplerSize:{value:new Vector2},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new Matrix3},attenuationDistance:{value:0},attenuationColor:{value:new Color(0)},specularColor:{value:new Color(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new Matrix3},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new Matrix3},anisotropyVector:{value:new Vector2},anisotropyMap:{value:null},anisotropyMapTransform:{value:new Matrix3}}]),vertexShader:ShaderChunk.meshphysical_vert,fragmentShader:ShaderChunk.meshphysical_frag};var _rgb={r:0,b:0,g:0},_m14=new Matrix4,_m=new Matrix3;_m.set(-1,0,0,0,1,0,0,0,1);function WebGLBackground(renderer,environments,state,objects,alpha,premultipliedAlpha){let clearColor=new Color(0),clearAlpha=alpha===!0?0:1,planeMesh,boxMesh,currentBackground=null,currentBackgroundVersion=0,currentTonemapping=null;function getBackground(scene){let background=scene.isScene===!0?scene.background:null;if(background&&background.isTexture){let usePMREM=scene.backgroundBlurriness>0;background=environments.get(background,usePMREM)}return background}function render(scene){let forceClear=!1,background=getBackground(scene);background===null?setClear(clearColor,clearAlpha):background&&background.isColor&&(setClear(background,1),forceClear=!0);let environmentBlendMode=renderer.xr.getEnvironmentBlendMode();environmentBlendMode==="additive"?state.buffers.color.setClear(0,0,0,1,premultipliedAlpha):environmentBlendMode==="alpha-blend"&&state.buffers.color.setClear(0,0,0,0,premultipliedAlpha),(renderer.autoClear||forceClear)&&(state.buffers.depth.setTest(!0),state.buffers.depth.setMask(!0),state.buffers.color.setMask(!0),renderer.clear(renderer.autoClearColor,renderer.autoClearDepth,renderer.autoClearStencil))}function addToRenderList(renderList,scene){let background=getBackground(scene);background&&(background.isCubeTexture||background.mapping===CubeUVReflectionMapping)?(boxMesh===void 0&&(boxMesh=new Mesh(new BoxGeometry(1,1,1),new ShaderMaterial({name:"BackgroundCubeMaterial",uniforms:cloneUniforms(ShaderLib.backgroundCube.uniforms),vertexShader:ShaderLib.backgroundCube.vertexShader,fragmentShader:ShaderLib.backgroundCube.fragmentShader,side:BackSide,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),boxMesh.geometry.deleteAttribute("normal"),boxMesh.geometry.deleteAttribute("uv"),boxMesh.onBeforeRender=function(renderer2,scene2,camera){this.matrixWorld.copyPosition(camera.matrixWorld)},Object.defineProperty(boxMesh.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),objects.update(boxMesh)),boxMesh.material.uniforms.envMap.value=background,boxMesh.material.uniforms.backgroundBlurriness.value=scene.backgroundBlurriness,boxMesh.material.uniforms.backgroundIntensity.value=scene.backgroundIntensity,boxMesh.material.uniforms.backgroundRotation.value.setFromMatrix4(_m14.makeRotationFromEuler(scene.backgroundRotation)).transpose(),background.isCubeTexture&&background.isRenderTargetTexture===!1&&boxMesh.material.uniforms.backgroundRotation.value.premultiply(_m),boxMesh.material.toneMapped=ColorManagement.getTransfer(background.colorSpace)!==SRGBTransfer,(currentBackground!==background||currentBackgroundVersion!==background.version||currentTonemapping!==renderer.toneMapping)&&(boxMesh.material.needsUpdate=!0,currentBackground=background,currentBackgroundVersion=background.version,currentTonemapping=renderer.toneMapping),boxMesh.layers.enableAll(),renderList.unshift(boxMesh,boxMesh.geometry,boxMesh.material,0,0,null)):background&&background.isTexture&&(planeMesh===void 0&&(planeMesh=new Mesh(new PlaneGeometry(2,2),new ShaderMaterial({name:"BackgroundMaterial",uniforms:cloneUniforms(ShaderLib.background.uniforms),vertexShader:ShaderLib.background.vertexShader,fragmentShader:ShaderLib.background.fragmentShader,side:FrontSide,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),planeMesh.geometry.deleteAttribute("normal"),Object.defineProperty(planeMesh.material,"map",{get:function(){return this.uniforms.t2D.value}}),objects.update(planeMesh)),planeMesh.material.uniforms.t2D.value=background,planeMesh.material.uniforms.backgroundIntensity.value=scene.backgroundIntensity,planeMesh.material.toneMapped=ColorManagement.getTransfer(background.colorSpace)!==SRGBTransfer,background.matrixAutoUpdate===!0&&background.updateMatrix(),planeMesh.material.uniforms.uvTransform.value.copy(background.matrix),(currentBackground!==background||currentBackgroundVersion!==background.version||currentTonemapping!==renderer.toneMapping)&&(planeMesh.material.needsUpdate=!0,currentBackground=background,currentBackgroundVersion=background.version,currentTonemapping=renderer.toneMapping),planeMesh.layers.enableAll(),renderList.unshift(planeMesh,planeMesh.geometry,planeMesh.material,0,0,null))}function setClear(color,alpha2){color.getRGB(_rgb,getUnlitUniformColorSpace(renderer)),state.buffers.color.setClear(_rgb.r,_rgb.g,_rgb.b,alpha2,premultipliedAlpha)}function dispose(){boxMesh!==void 0&&(boxMesh.geometry.dispose(),boxMesh.material.dispose(),boxMesh=void 0),planeMesh!==void 0&&(planeMesh.geometry.dispose(),planeMesh.material.dispose(),planeMesh=void 0)}return{getClearColor:function(){return clearColor},setClearColor:function(color,alpha2=1){clearColor.set(color),clearAlpha=alpha2,setClear(clearColor,clearAlpha)},getClearAlpha:function(){return clearAlpha},setClearAlpha:function(alpha2){clearAlpha=alpha2,setClear(clearColor,clearAlpha)},render,addToRenderList,dispose}}function WebGLBindingStates(gl,attributes){let maxVertexAttributes=gl.getParameter(gl.MAX_VERTEX_ATTRIBS),bindingStates={},defaultState=createBindingState(null),currentState=defaultState,forceUpdate=!1;function setup(object,material,program,geometry,index){let updateBuffers=!1,state=getBindingState(object,geometry,program,material);currentState!==state&&(currentState=state,bindVertexArrayObject(currentState.object)),updateBuffers=needsUpdate(object,geometry,program,index),updateBuffers&&saveCache(object,geometry,program,index),index!==null&&attributes.update(index,gl.ELEMENT_ARRAY_BUFFER),(updateBuffers||forceUpdate)&&(forceUpdate=!1,setupVertexAttributes(object,material,program,geometry),index!==null&&gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,attributes.get(index).buffer))}function createVertexArrayObject(){return gl.createVertexArray()}function bindVertexArrayObject(vao){return gl.bindVertexArray(vao)}function deleteVertexArrayObject(vao){return gl.deleteVertexArray(vao)}function getBindingState(object,geometry,program,material){let wireframe=material.wireframe===!0,objectMap=bindingStates[geometry.id];objectMap===void 0&&(objectMap={},bindingStates[geometry.id]=objectMap);let objectId=object.isInstancedMesh===!0?object.id:0,programMap=objectMap[objectId];programMap===void 0&&(programMap={},objectMap[objectId]=programMap);let stateMap=programMap[program.id];stateMap===void 0&&(stateMap={},programMap[program.id]=stateMap);let state=stateMap[wireframe];return state===void 0&&(state=createBindingState(createVertexArrayObject()),stateMap[wireframe]=state),state}function createBindingState(vao){let newAttributes=[],enabledAttributes=[],attributeDivisors=[];for(let i=0;i<maxVertexAttributes;i++)newAttributes[i]=0,enabledAttributes[i]=0,attributeDivisors[i]=0;return{geometry:null,program:null,wireframe:!1,newAttributes,enabledAttributes,attributeDivisors,object:vao,attributes:{},index:null}}function needsUpdate(object,geometry,program,index){let cachedAttributes=currentState.attributes,geometryAttributes=geometry.attributes,attributesNum=0,programAttributes=program.getAttributes();for(let name in programAttributes)if(programAttributes[name].location>=0){let cachedAttribute=cachedAttributes[name],geometryAttribute=geometryAttributes[name];if(geometryAttribute===void 0&&(name==="instanceMatrix"&&object.instanceMatrix&&(geometryAttribute=object.instanceMatrix),name==="instanceColor"&&object.instanceColor&&(geometryAttribute=object.instanceColor)),cachedAttribute===void 0||cachedAttribute.attribute!==geometryAttribute||geometryAttribute&&cachedAttribute.data!==geometryAttribute.data)return!0;attributesNum++}return currentState.attributesNum!==attributesNum||currentState.index!==index}function saveCache(object,geometry,program,index){let cache={},attributes2=geometry.attributes,attributesNum=0,programAttributes=program.getAttributes();for(let name in programAttributes)if(programAttributes[name].location>=0){let attribute=attributes2[name];attribute===void 0&&(name==="instanceMatrix"&&object.instanceMatrix&&(attribute=object.instanceMatrix),name==="instanceColor"&&object.instanceColor&&(attribute=object.instanceColor));let data={};data.attribute=attribute,attribute&&attribute.data&&(data.data=attribute.data),cache[name]=data,attributesNum++}currentState.attributes=cache,currentState.attributesNum=attributesNum,currentState.index=index}function initAttributes(){let newAttributes=currentState.newAttributes;for(let i=0,il=newAttributes.length;i<il;i++)newAttributes[i]=0}function enableAttribute(attribute){enableAttributeAndDivisor(attribute,0)}function enableAttributeAndDivisor(attribute,meshPerAttribute){let newAttributes=currentState.newAttributes,enabledAttributes=currentState.enabledAttributes,attributeDivisors=currentState.attributeDivisors;newAttributes[attribute]=1,enabledAttributes[attribute]===0&&(gl.enableVertexAttribArray(attribute),enabledAttributes[attribute]=1),attributeDivisors[attribute]!==meshPerAttribute&&(gl.vertexAttribDivisor(attribute,meshPerAttribute),attributeDivisors[attribute]=meshPerAttribute)}function disableUnusedAttributes(){let newAttributes=currentState.newAttributes,enabledAttributes=currentState.enabledAttributes;for(let i=0,il=enabledAttributes.length;i<il;i++)enabledAttributes[i]!==newAttributes[i]&&(gl.disableVertexAttribArray(i),enabledAttributes[i]=0)}function vertexAttribPointer(index,size,type,normalized,stride,offset,integer){integer===!0?gl.vertexAttribIPointer(index,size,type,stride,offset):gl.vertexAttribPointer(index,size,type,normalized,stride,offset)}function setupVertexAttributes(object,material,program,geometry){initAttributes();let geometryAttributes=geometry.attributes,programAttributes=program.getAttributes(),materialDefaultAttributeValues=material.defaultAttributeValues;for(let name in programAttributes){let programAttribute=programAttributes[name];if(programAttribute.location>=0){let geometryAttribute=geometryAttributes[name];if(geometryAttribute===void 0&&(name==="instanceMatrix"&&object.instanceMatrix&&(geometryAttribute=object.instanceMatrix),name==="instanceColor"&&object.instanceColor&&(geometryAttribute=object.instanceColor)),geometryAttribute!==void 0){let normalized=geometryAttribute.normalized,size=geometryAttribute.itemSize,attribute=attributes.get(geometryAttribute);if(attribute===void 0)continue;let buffer=attribute.buffer,type=attribute.type,bytesPerElement=attribute.bytesPerElement,integer=type===gl.INT||type===gl.UNSIGNED_INT||geometryAttribute.gpuType===IntType;if(geometryAttribute.isInterleavedBufferAttribute){let data=geometryAttribute.data,stride=data.stride,offset=geometryAttribute.offset;if(data.isInstancedInterleavedBuffer){for(let i=0;i<programAttribute.locationSize;i++)enableAttributeAndDivisor(programAttribute.location+i,data.meshPerAttribute);object.isInstancedMesh!==!0&&geometry._maxInstanceCount===void 0&&(geometry._maxInstanceCount=data.meshPerAttribute*data.count)}else for(let i=0;i<programAttribute.locationSize;i++)enableAttribute(programAttribute.location+i);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);for(let i=0;i<programAttribute.locationSize;i++)vertexAttribPointer(programAttribute.location+i,size/programAttribute.locationSize,type,normalized,stride*bytesPerElement,(offset+size/programAttribute.locationSize*i)*bytesPerElement,integer)}else{if(geometryAttribute.isInstancedBufferAttribute){for(let i=0;i<programAttribute.locationSize;i++)enableAttributeAndDivisor(programAttribute.location+i,geometryAttribute.meshPerAttribute);object.isInstancedMesh!==!0&&geometry._maxInstanceCount===void 0&&(geometry._maxInstanceCount=geometryAttribute.meshPerAttribute*geometryAttribute.count)}else for(let i=0;i<programAttribute.locationSize;i++)enableAttribute(programAttribute.location+i);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);for(let i=0;i<programAttribute.locationSize;i++)vertexAttribPointer(programAttribute.location+i,size/programAttribute.locationSize,type,normalized,size*bytesPerElement,size/programAttribute.locationSize*i*bytesPerElement,integer)}}else if(materialDefaultAttributeValues!==void 0){let value=materialDefaultAttributeValues[name];if(value!==void 0)switch(value.length){case 2:gl.vertexAttrib2fv(programAttribute.location,value);break;case 3:gl.vertexAttrib3fv(programAttribute.location,value);break;case 4:gl.vertexAttrib4fv(programAttribute.location,value);break;default:gl.vertexAttrib1fv(programAttribute.location,value)}}}}disableUnusedAttributes()}function dispose(){reset();for(let geometryId in bindingStates){let objectMap=bindingStates[geometryId];for(let objectId in objectMap){let programMap=objectMap[objectId];for(let programId in programMap){let stateMap=programMap[programId];for(let wireframe in stateMap)deleteVertexArrayObject(stateMap[wireframe].object),delete stateMap[wireframe];delete programMap[programId]}}delete bindingStates[geometryId]}}function releaseStatesOfGeometry(geometry){if(bindingStates[geometry.id]===void 0)return;let objectMap=bindingStates[geometry.id];for(let objectId in objectMap){let programMap=objectMap[objectId];for(let programId in programMap){let stateMap=programMap[programId];for(let wireframe in stateMap)deleteVertexArrayObject(stateMap[wireframe].object),delete stateMap[wireframe];delete programMap[programId]}}delete bindingStates[geometry.id]}function releaseStatesOfProgram(program){for(let geometryId in bindingStates){let objectMap=bindingStates[geometryId];for(let objectId in objectMap){let programMap=objectMap[objectId];if(programMap[program.id]===void 0)continue;let stateMap=programMap[program.id];for(let wireframe in stateMap)deleteVertexArrayObject(stateMap[wireframe].object),delete stateMap[wireframe];delete programMap[program.id]}}}function releaseStatesOfObject(object){for(let geometryId in bindingStates){let objectMap=bindingStates[geometryId],objectId=object.isInstancedMesh===!0?object.id:0,programMap=objectMap[objectId];if(programMap!==void 0){for(let programId in programMap){let stateMap=programMap[programId];for(let wireframe in stateMap)deleteVertexArrayObject(stateMap[wireframe].object),delete stateMap[wireframe];delete programMap[programId]}delete objectMap[objectId],Object.keys(objectMap).length===0&&delete bindingStates[geometryId]}}}function reset(){resetDefaultState(),forceUpdate=!0,currentState!==defaultState&&(currentState=defaultState,bindVertexArrayObject(currentState.object))}function resetDefaultState(){defaultState.geometry=null,defaultState.program=null,defaultState.wireframe=!1}return{setup,reset,resetDefaultState,dispose,releaseStatesOfGeometry,releaseStatesOfObject,releaseStatesOfProgram,initAttributes,enableAttribute,disableUnusedAttributes}}function WebGLBufferRenderer(gl,extensions,info){let mode;function setMode(value){mode=value}function render(start,count){gl.drawArrays(mode,start,count),info.update(count,mode,1)}function renderInstances(start,count,primcount){primcount!==0&&(gl.drawArraysInstanced(mode,start,count,primcount),info.update(count,mode,primcount))}function renderMultiDraw(starts,counts,drawCount){if(drawCount===0)return;extensions.get("WEBGL_multi_draw").multiDrawArraysWEBGL(mode,starts,0,counts,0,drawCount);let elementCount=0;for(let i=0;i<drawCount;i++)elementCount+=counts[i];info.update(elementCount,mode,1)}this.setMode=setMode,this.render=render,this.renderInstances=renderInstances,this.renderMultiDraw=renderMultiDraw}function WebGLCapabilities(gl,extensions,parameters,utils){let maxAnisotropy;function getMaxAnisotropy(){if(maxAnisotropy!==void 0)return maxAnisotropy;if(extensions.has("EXT_texture_filter_anisotropic")===!0){let extension=extensions.get("EXT_texture_filter_anisotropic");maxAnisotropy=gl.getParameter(extension.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else maxAnisotropy=0;return maxAnisotropy}function textureFormatReadable(textureFormat){return!(textureFormat!==RGBAFormat&&utils.convert(textureFormat)!==gl.getParameter(gl.IMPLEMENTATION_COLOR_READ_FORMAT))}function textureTypeReadable(textureType){let halfFloatSupportedByExt=textureType===HalfFloatType&&(extensions.has("EXT_color_buffer_half_float")||extensions.has("EXT_color_buffer_float"));return!(textureType!==UnsignedByteType&&textureType!==FloatType&&!halfFloatSupportedByExt&&utils.convert(textureType)!==gl.getParameter(gl.IMPLEMENTATION_COLOR_READ_TYPE))}function getMaxPrecision(precision2){if(precision2==="highp"){if(gl.getShaderPrecisionFormat(gl.VERTEX_SHADER,gl.HIGH_FLOAT).precision>0&&gl.getShaderPrecisionFormat(gl.FRAGMENT_SHADER,gl.HIGH_FLOAT).precision>0)return"highp";precision2="mediump"}return precision2==="mediump"&&gl.getShaderPrecisionFormat(gl.VERTEX_SHADER,gl.MEDIUM_FLOAT).precision>0&&gl.getShaderPrecisionFormat(gl.FRAGMENT_SHADER,gl.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let precision=parameters.precision!==void 0?parameters.precision:"highp",maxPrecision=getMaxPrecision(precision);maxPrecision!==precision&&(warn("WebGLRenderer:",precision,"not supported, using",maxPrecision,"instead."),precision=maxPrecision);let logarithmicDepthBuffer=parameters.logarithmicDepthBuffer===!0,reversedDepthBuffer=parameters.reversedDepthBuffer===!0&&extensions.has("EXT_clip_control");parameters.reversedDepthBuffer===!0&&reversedDepthBuffer===!1&&warn("WebGLRenderer: Unable to use reversed depth buffer due to missing EXT_clip_control extension. Fallback to default depth buffer.");let maxTextures=gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS),maxVertexTextures=gl.getParameter(gl.MAX_VERTEX_TEXTURE_IMAGE_UNITS),maxTextureSize=gl.getParameter(gl.MAX_TEXTURE_SIZE),maxCubemapSize=gl.getParameter(gl.MAX_CUBE_MAP_TEXTURE_SIZE),maxAttributes=gl.getParameter(gl.MAX_VERTEX_ATTRIBS),maxVertexUniforms=gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS),maxVaryings=gl.getParameter(gl.MAX_VARYING_VECTORS),maxFragmentUniforms=gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS),maxSamples=gl.getParameter(gl.MAX_SAMPLES),samples=gl.getParameter(gl.SAMPLES);return{isWebGL2:!0,getMaxAnisotropy,getMaxPrecision,textureFormatReadable,textureTypeReadable,precision,logarithmicDepthBuffer,reversedDepthBuffer,maxTextures,maxVertexTextures,maxTextureSize,maxCubemapSize,maxAttributes,maxVertexUniforms,maxVaryings,maxFragmentUniforms,maxSamples,samples}}function WebGLClipping(properties){let scope=this,globalState=null,numGlobalPlanes=0,localClippingEnabled=!1,renderingShadows=!1,plane=new Plane,viewNormalMatrix=new Matrix3,uniform={value:null,needsUpdate:!1};this.uniform=uniform,this.numPlanes=0,this.numIntersection=0,this.init=function(planes,enableLocalClipping){let enabled=planes.length!==0||enableLocalClipping||numGlobalPlanes!==0||localClippingEnabled;return localClippingEnabled=enableLocalClipping,numGlobalPlanes=planes.length,enabled},this.beginShadows=function(){renderingShadows=!0,projectPlanes(null)},this.endShadows=function(){renderingShadows=!1},this.setGlobalState=function(planes,camera){globalState=projectPlanes(planes,camera,0)},this.setState=function(material,camera,useCache){let planes=material.clippingPlanes,clipIntersection=material.clipIntersection,clipShadows=material.clipShadows,materialProperties=properties.get(material);if(!localClippingEnabled||planes===null||planes.length===0||renderingShadows&&!clipShadows)renderingShadows?projectPlanes(null):resetGlobalState();else{let nGlobal=renderingShadows?0:numGlobalPlanes,lGlobal=nGlobal*4,dstArray=materialProperties.clippingState||null;uniform.value=dstArray,dstArray=projectPlanes(planes,camera,lGlobal,useCache);for(let i=0;i!==lGlobal;++i)dstArray[i]=globalState[i];materialProperties.clippingState=dstArray,this.numIntersection=clipIntersection?this.numPlanes:0,this.numPlanes+=nGlobal}};function resetGlobalState(){uniform.value!==globalState&&(uniform.value=globalState,uniform.needsUpdate=numGlobalPlanes>0),scope.numPlanes=numGlobalPlanes,scope.numIntersection=0}function projectPlanes(planes,camera,dstOffset,skipTransform){let nPlanes=planes!==null?planes.length:0,dstArray=null;if(nPlanes!==0){if(dstArray=uniform.value,skipTransform!==!0||dstArray===null){let flatSize=dstOffset+nPlanes*4,viewMatrix=camera.matrixWorldInverse;viewNormalMatrix.getNormalMatrix(viewMatrix),(dstArray===null||dstArray.length<flatSize)&&(dstArray=new Float32Array(flatSize));for(let i=0,i4=dstOffset;i!==nPlanes;++i,i4+=4)plane.copy(planes[i]).applyMatrix4(viewMatrix,viewNormalMatrix),plane.normal.toArray(dstArray,i4),dstArray[i4+3]=plane.constant}uniform.value=dstArray,uniform.needsUpdate=!0}return scope.numPlanes=nPlanes,scope.numIntersection=0,dstArray}}var LOD_MIN=4,EXTRA_LODS=6,BLUR_SAMPLES=20,GGX_SAMPLES=256,_flatCamera=new OrthographicCamera,_clearColor=new Color,_oldTarget=null,_oldActiveCubeFace=0,_oldActiveMipmapLevel=0,_oldXrEnabled=!1,_origin=new Vector3,_direction=new Vector3,PMREMGenerator=class{constructor(renderer){this._renderer=renderer,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._sizeLods=[],this._lodMeshes=[],this._backgroundBox=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._blurMaterial=null,this._ggxMaterial=null}fromScene(scene,sigma=0,near=.1,far=100,options={}){let{size=256,position=_origin}=options;_oldTarget=this._renderer.getRenderTarget(),_oldActiveCubeFace=this._renderer.getActiveCubeFace(),_oldActiveMipmapLevel=this._renderer.getActiveMipmapLevel(),_oldXrEnabled=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(size);let cubeUVRenderTarget=this._allocateTargets();return cubeUVRenderTarget.depthBuffer=!0,this._sceneToCubeUV(scene,near,far,cubeUVRenderTarget,position),sigma>0&&this._blur(cubeUVRenderTarget,0,0,sigma),this._applyPMREM(cubeUVRenderTarget),this._cleanup(cubeUVRenderTarget),cubeUVRenderTarget}fromEquirectangular(equirectangular,renderTarget=null){return this._fromTexture(equirectangular,renderTarget)}fromCubemap(cubemap,renderTarget=null){return this._fromTexture(cubemap,renderTarget)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=_getCubemapMaterial(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=_getEquirectMaterial(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose(),this._backgroundBox!==null&&(this._backgroundBox.geometry.dispose(),this._backgroundBox.material.dispose())}_setSize(cubeSize){this._lodMax=Math.floor(Math.log2(cubeSize)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._ggxMaterial!==null&&this._ggxMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let i=0;i<this._lodMeshes.length;i++)this._lodMeshes[i].geometry.dispose()}_cleanup(outputTarget){this._renderer.setRenderTarget(_oldTarget,_oldActiveCubeFace,_oldActiveMipmapLevel),this._renderer.xr.enabled=_oldXrEnabled,outputTarget.scissorTest=!1,_setViewport(outputTarget,0,0,outputTarget.width,outputTarget.height)}_fromTexture(texture,renderTarget){texture.mapping===CubeReflectionMapping||texture.mapping===CubeRefractionMapping?this._setSize(texture.image.length===0?16:texture.image[0].width||texture.image[0].image.width):this._setSize(texture.image.width/4),_oldTarget=this._renderer.getRenderTarget(),_oldActiveCubeFace=this._renderer.getActiveCubeFace(),_oldActiveMipmapLevel=this._renderer.getActiveMipmapLevel(),_oldXrEnabled=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;let cubeUVRenderTarget=renderTarget||this._allocateTargets();return this._textureToCubeUV(texture,cubeUVRenderTarget),this._applyPMREM(cubeUVRenderTarget),this._cleanup(cubeUVRenderTarget),cubeUVRenderTarget}_allocateTargets(){let width=3*Math.max(this._cubeSize,112),height=4*this._cubeSize,params={magFilter:LinearFilter,minFilter:LinearFilter,generateMipmaps:!1,type:HalfFloatType,format:RGBAFormat,colorSpace:LinearSRGBColorSpace,depthBuffer:!1},cubeUVRenderTarget=_createRenderTarget(width,height,params);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==width||this._pingPongRenderTarget.height!==height){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=_createRenderTarget(width,height,params);let{_lodMax}=this;({lodMeshes:this._lodMeshes,sizeLods:this._sizeLods}=_createPlanes(_lodMax)),this._blurMaterial=_getBlurShader(_lodMax,width,height),this._ggxMaterial=_getGGXShader(_lodMax,width,height)}return cubeUVRenderTarget}_compileMaterial(material){let mesh=new Mesh(new BufferGeometry,material);this._renderer.compile(mesh,_flatCamera)}_sceneToCubeUV(scene,near,far,cubeUVRenderTarget,position){let cubeCamera=new PerspectiveCamera(90,1,near,far),upSign=[1,-1,1,1,1,1],forwardSign=[1,1,1,-1,-1,-1],renderer=this._renderer,originalAutoClear=renderer.autoClear,toneMapping=renderer.toneMapping;renderer.getClearColor(_clearColor),renderer.toneMapping=NoToneMapping,renderer.autoClear=!1,renderer.state.buffers.depth.getReversed()&&(renderer.setRenderTarget(cubeUVRenderTarget),renderer.clearDepth(),renderer.setRenderTarget(null)),this._backgroundBox===null&&(this._backgroundBox=new Mesh(new BoxGeometry,new MeshBasicMaterial({name:"PMREM.Background",side:BackSide,depthWrite:!1,depthTest:!1})));let backgroundBox=this._backgroundBox,backgroundMaterial=backgroundBox.material,useSolidColor=!1,background=scene.background;background?background.isColor&&(backgroundMaterial.color.copy(background),scene.background=null,useSolidColor=!0):(backgroundMaterial.color.copy(_clearColor),useSolidColor=!0);for(let i=0;i<6;i++){let col=i%3;col===0?(cubeCamera.up.set(0,upSign[i],0),cubeCamera.position.set(position.x,position.y,position.z),cubeCamera.lookAt(position.x+forwardSign[i],position.y,position.z)):col===1?(cubeCamera.up.set(0,0,upSign[i]),cubeCamera.position.set(position.x,position.y,position.z),cubeCamera.lookAt(position.x,position.y+forwardSign[i],position.z)):(cubeCamera.up.set(0,upSign[i],0),cubeCamera.position.set(position.x,position.y,position.z),cubeCamera.lookAt(position.x,position.y,position.z+forwardSign[i]));let size=this._cubeSize;_setViewport(cubeUVRenderTarget,col*size,i>2?size:0,size,size),renderer.setRenderTarget(cubeUVRenderTarget),useSolidColor&&renderer.render(backgroundBox,cubeCamera),renderer.render(scene,cubeCamera)}renderer.toneMapping=toneMapping,renderer.autoClear=originalAutoClear,scene.background=background}_textureToCubeUV(texture,cubeUVRenderTarget){let renderer=this._renderer,isCubeTexture=texture.mapping===CubeReflectionMapping||texture.mapping===CubeRefractionMapping;isCubeTexture?(this._cubemapMaterial===null&&(this._cubemapMaterial=_getCubemapMaterial()),this._cubemapMaterial.uniforms.flipEnvMap.value=texture.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=_getEquirectMaterial());let material=isCubeTexture?this._cubemapMaterial:this._equirectMaterial,mesh=this._lodMeshes[0];mesh.material=material;let uniforms=material.uniforms;uniforms.envMap.value=texture;let size=this._cubeSize;_setViewport(cubeUVRenderTarget,0,0,3*size,2*size),renderer.setRenderTarget(cubeUVRenderTarget),renderer.render(mesh,_flatCamera)}_applyPMREM(cubeUVRenderTarget){let renderer=this._renderer,autoClear=renderer.autoClear;renderer.autoClear=!1;let n=this._lodMeshes.length;for(let i=1;i<n;i++)this._applyGGXFilter(cubeUVRenderTarget,i-1,i);renderer.autoClear=autoClear}_applyGGXFilter(cubeUVRenderTarget,lodIn,lodOut){let renderer=this._renderer,pingPongRenderTarget=this._pingPongRenderTarget,ggxMaterial=this._ggxMaterial,ggxMesh=this._lodMeshes[lodOut];ggxMesh.material=ggxMaterial;let ggxUniforms=ggxMaterial.uniforms,targetRoughness=lodOut/(this._lodMeshes.length-1),sourceRoughness=lodIn/(this._lodMeshes.length-1),incrementalRoughness=Math.sqrt(targetRoughness*targetRoughness-sourceRoughness*sourceRoughness),blurStrength=targetRoughness*1.25,adjustedRoughness=incrementalRoughness*blurStrength,{_lodMax}=this,outputSize=this._sizeLods[lodOut],x=3*outputSize*(lodOut>_lodMax-LOD_MIN?lodOut-_lodMax+LOD_MIN:0),y=4*(this._cubeSize-outputSize);ggxUniforms.envMap.value=cubeUVRenderTarget.texture,ggxUniforms.roughness.value=adjustedRoughness,ggxUniforms.mipInt.value=_lodMax-lodIn,_setViewport(pingPongRenderTarget,x,y,3*outputSize,2*outputSize),renderer.setRenderTarget(pingPongRenderTarget),renderer.render(ggxMesh,_flatCamera),ggxUniforms.envMap.value=pingPongRenderTarget.texture,ggxUniforms.roughness.value=0,ggxUniforms.mipInt.value=_lodMax-lodOut,_setViewport(cubeUVRenderTarget,x,y,3*outputSize,2*outputSize),renderer.setRenderTarget(cubeUVRenderTarget),renderer.render(ggxMesh,_flatCamera)}_blur(cubeUVRenderTarget,lodIn,lodOut,sigma){let pingPongRenderTarget=this._pingPongRenderTarget,blurSigma=Math.min(sigma,Math.PI)/Math.SQRT2;this._blurPass(cubeUVRenderTarget,pingPongRenderTarget,lodIn,lodOut,blurSigma),this._blurPass(pingPongRenderTarget,cubeUVRenderTarget,lodOut,lodOut,blurSigma)}_blurPass(targetIn,targetOut,lodIn,lodOut,sigmaRadians){let renderer=this._renderer,blurMaterial=this._blurMaterial,blurMesh=this._lodMeshes[lodOut];blurMesh.material=blurMaterial;let blurUniforms=blurMaterial.uniforms;blurUniforms.envMap.value=targetIn.texture,blurUniforms.sigma.value=sigmaRadians,blurUniforms.mipInt.value=this._lodMax-lodIn;let outputSize=this._sizeLods[lodOut],x=3*outputSize*(lodOut>this._lodMax-LOD_MIN?lodOut-this._lodMax+LOD_MIN:0),y=4*(this._cubeSize-outputSize);_setViewport(targetOut,x,y,3*outputSize,2*outputSize),renderer.setRenderTarget(targetOut),renderer.render(blurMesh,_flatCamera)}};function _createPlanes(lodMax){let sizeLods=[],lodMeshes=[],lod=lodMax,totalLods=lodMax-LOD_MIN+1+EXTRA_LODS;for(let i=0;i<totalLods;i++){let sizeLod=Math.pow(2,lod);sizeLods.push(sizeLod);let texelSize=1/(sizeLod-2),min=-texelSize,max=1+texelSize,uv1=[min,min,max,min,max,max,min,min,max,max,min,max],cubeFaces=6,vertices=6,positionSize=3,position=new Float32Array(positionSize*vertices*cubeFaces),outputDirection=new Float32Array(positionSize*vertices*cubeFaces);for(let face=0;face<cubeFaces;face++){let x=face%3*2/3-1,y=face>2?0:-1,coordinates=[x,y,0,x+2/3,y,0,x+2/3,y+1,0,x,y,0,x+2/3,y+1,0,x,y+1,0];position.set(coordinates,positionSize*vertices*face);for(let vertex19=0;vertex19<vertices;vertex19++){let u=uv1[vertex19*2]*2-1,v=uv1[vertex19*2+1]*2-1;face===0?_direction.set(1,v,u):face===1?_direction.set(-u,1,-v):face===2?_direction.set(-u,v,1):face===3?_direction.set(-1,v,-u):face===4?_direction.set(-u,-1,v):_direction.set(u,v,-1),_direction.toArray(outputDirection,(face*vertices+vertex19)*positionSize)}}let planes=new BufferGeometry;planes.setAttribute("position",new BufferAttribute(position,positionSize)),planes.setAttribute("outputDirection",new BufferAttribute(outputDirection,positionSize)),lodMeshes.push(new Mesh(planes,null)),lod>LOD_MIN&&lod--}return{lodMeshes,sizeLods}}function _createRenderTarget(width,height,params){let cubeUVRenderTarget=new WebGLRenderTarget(width,height,params);return cubeUVRenderTarget.texture.mapping=CubeUVReflectionMapping,cubeUVRenderTarget.texture.name="PMREM.cubeUv",cubeUVRenderTarget.scissorTest=!0,cubeUVRenderTarget}function _setViewport(target,x,y,width,height){target.viewport.set(x,y,width,height),target.scissor.set(x,y,width,height)}function _getGGXShader(lodMax,width,height){return new ShaderMaterial({name:"PMREMGGXConvolution",defines:{GGX_SAMPLES,CUBEUV_TEXEL_WIDTH:1/width,CUBEUV_TEXEL_HEIGHT:1/height,CUBEUV_MAX_MIP:`${lodMax}.0`},uniforms:{envMap:{value:null},roughness:{value:0},mipInt:{value:0}},vertexShader:_getCommonVertexShader(),fragmentShader:`

			precision highp float;
			precision highp int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform float roughness;
			uniform float mipInt;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			#define PI 3.14159265359

			// Van der Corput radical inverse
			float radicalInverse_VdC(uint bits) {
				bits = (bits << 16u) | (bits >> 16u);
				bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
				bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
				bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
				bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
				return float(bits) * 2.3283064365386963e-10; // / 0x100000000
			}

			// Hammersley sequence
			vec2 hammersley(uint i, uint N) {
				return vec2(float(i) / float(N), radicalInverse_VdC(i));
			}

			// GGX VNDF importance sampling (Eric Heitz 2018)
			// "Sampling the GGX Distribution of Visible Normals"
			// https://jcgt.org/published/0007/04/01/
			vec3 importanceSampleGGX_VNDF(vec2 Xi, vec3 V, float roughness) {
				float alpha = roughness * roughness;

				// Section 4.1: Orthonormal basis
				vec3 T1 = vec3(1.0, 0.0, 0.0);
				vec3 T2 = cross(V, T1);

				// Section 4.2: Parameterization of projected area
				float r = sqrt(Xi.x);
				float phi = 2.0 * PI * Xi.y;
				float t1 = r * cos(phi);
				float t2 = r * sin(phi);
				float s = 0.5 * (1.0 + V.z);
				t2 = (1.0 - s) * sqrt(1.0 - t1 * t1) + s * t2;

				// Section 4.3: Reprojection onto hemisphere
				vec3 Nh = t1 * T1 + t2 * T2 + sqrt(max(0.0, 1.0 - t1 * t1 - t2 * t2)) * V;

				// Section 3.4: Transform back to ellipsoid configuration
				return normalize(vec3(alpha * Nh.x, alpha * Nh.y, max(0.0, Nh.z)));
			}

			void main() {
				vec3 N = normalize(vOutputDirection);
				vec3 V = N; // Assume view direction equals normal for pre-filtering

				vec3 prefilteredColor = vec3(0.0);
				float totalWeight = 0.0;

				// For very low roughness, just sample the environment directly
				if (roughness < 0.001) {
					gl_FragColor = vec4(bilinearCubeUV(envMap, N, mipInt), 1.0);
					return;
				}

				// Tangent space basis for VNDF sampling
				vec3 up = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
				vec3 tangent = normalize(cross(up, N));
				vec3 bitangent = cross(N, tangent);

				for(uint i = 0u; i < uint(GGX_SAMPLES); i++) {
					vec2 Xi = hammersley(i, uint(GGX_SAMPLES));

					// For PMREM, V = N, so in tangent space V is always (0, 0, 1)
					vec3 H_tangent = importanceSampleGGX_VNDF(Xi, vec3(0.0, 0.0, 1.0), roughness);

					// Transform H back to world space
					vec3 H = normalize(tangent * H_tangent.x + bitangent * H_tangent.y + N * H_tangent.z);
					vec3 L = normalize(2.0 * dot(V, H) * H - V);

					float NdotL = max(dot(N, L), 0.0);

					if(NdotL > 0.0) {
						// Sample environment at fixed mip level
						// VNDF importance sampling handles the distribution filtering
						vec3 sampleColor = bilinearCubeUV(envMap, L, mipInt);

						// Weight by NdotL for the split-sum approximation
						// VNDF PDF naturally accounts for the visible microfacet distribution
						prefilteredColor += sampleColor * NdotL;
						totalWeight += NdotL;
					}
				}

				if (totalWeight > 0.0) {
					prefilteredColor = prefilteredColor / totalWeight;
				}

				gl_FragColor = vec4(prefilteredColor, 1.0);
			}
		`,blending:NoBlending,depthTest:!1,depthWrite:!1})}function _getBlurShader(lodMax,width,height){return new ShaderMaterial({name:"SphericalGaussianBlur",defines:{SAMPLES:BLUR_SAMPLES,CUBEUV_TEXEL_WIDTH:1/width,CUBEUV_TEXEL_HEIGHT:1/height,CUBEUV_MAX_MIP:`${lodMax}.0`},uniforms:{envMap:{value:null},sigma:{value:0},mipInt:{value:0}},vertexShader:_getCommonVertexShader(),fragmentShader:`

			precision highp float;
			precision highp int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform float sigma;
			uniform float mipInt;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			#define PI 3.14159265359
			#define GOLDEN_ANGLE 2.39996322973

			void main() {

				if ( sigma == 0.0 ) {

					gl_FragColor = vec4( bilinearCubeUV( envMap, vOutputDirection, mipInt ), 1.0 );
					return;

				}

				vec3 outputDirection = normalize( vOutputDirection );

				vec3 up = abs( outputDirection.z ) < 0.999 ? vec3( 0.0, 0.0, 1.0 ) : vec3( 1.0, 0.0, 0.0 );
				vec3 tangent = normalize( cross( up, outputDirection ) );
				vec3 bitangent = cross( outputDirection, tangent );

				// Truncate the kernel at three standard deviations or at the antipode.
				float thetaMax = min( 3.0 * sigma, PI );
				float truncation = 1.0 - exp( - 0.5 * thetaMax * thetaMax / ( sigma * sigma ) );

				vec3 accumColor = vec3( 0.0 );
				float accumWeight = 0.0;

				for ( int i = 0; i < SAMPLES; i ++ ) {

					// Stratified inverse-CDF sampling of the Gaussian, placed on a golden-angle spiral.
					float stratum = ( float( i ) + 0.5 ) / float( SAMPLES );
					float theta = sigma * sqrt( - 2.0 * log( 1.0 - stratum * truncation ) );
					float phi = float( i ) * GOLDEN_ANGLE;

					vec3 offset = cos( phi ) * tangent + sin( phi ) * bitangent;
					vec3 sampleDirection = cos( theta ) * outputDirection + sin( theta ) * offset;

					// Correct the planar sample density to solid angle.
					float weight = sin( theta ) / theta;

					accumColor += weight * bilinearCubeUV( envMap, sampleDirection, mipInt );
					accumWeight += weight;

				}

				gl_FragColor = vec4( accumColor / accumWeight, 1.0 );

			}
		`,blending:NoBlending,depthTest:!1,depthWrite:!1})}function _getEquirectMaterial(){return new ShaderMaterial({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:_getCommonVertexShader(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:NoBlending,depthTest:!1,depthWrite:!1})}function _getCubemapMaterial(){return new ShaderMaterial({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:_getCommonVertexShader(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:NoBlending,depthTest:!1,depthWrite:!1})}function _getCommonVertexShader(){return`

		precision mediump float;
		precision mediump int;

		attribute vec3 outputDirection;

		varying vec3 vOutputDirection;

		void main() {

			vOutputDirection = outputDirection;
			gl_Position = vec4( position, 1.0 );

		}
	`}var WebGLCubeRenderTarget=class extends WebGLRenderTarget{constructor(size=1,options={}){super(size,size,options),this.isWebGLCubeRenderTarget=!0;let image={width:size,height:size,depth:1},images=[image,image,image,image,image,image];this.texture=new CubeTexture(images),this._setTextureOptions(options),this.texture.isRenderTargetTexture=!0}fromEquirectangularTexture(renderer,texture){this.texture.type=texture.type,this.texture.colorSpace=texture.colorSpace,this.texture.generateMipmaps=texture.generateMipmaps,this.texture.minFilter=texture.minFilter,this.texture.magFilter=texture.magFilter;let shader={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},geometry=new BoxGeometry(5,5,5),material=new ShaderMaterial({name:"CubemapFromEquirect",uniforms:cloneUniforms(shader.uniforms),vertexShader:shader.vertexShader,fragmentShader:shader.fragmentShader,side:BackSide,blending:NoBlending});material.uniforms.tEquirect.value=texture;let mesh=new Mesh(geometry,material),currentMinFilter=texture.minFilter;return texture.minFilter===LinearMipmapLinearFilter&&(texture.minFilter=LinearFilter),new CubeCamera(1,10,this).update(renderer,mesh),texture.minFilter=currentMinFilter,mesh.geometry.dispose(),mesh.material.dispose(),this}clear(renderer,color=!0,depth=!0,stencil=!0){let currentRenderTarget=renderer.getRenderTarget();for(let i=0;i<6;i++)renderer.setRenderTarget(this,i),renderer.clear(color,depth,stencil);renderer.setRenderTarget(currentRenderTarget)}};function WebGLEnvironments(renderer){let cubeMaps=new WeakMap,pmremMaps=new WeakMap,pmremGenerator=null;function get(texture,usePMREM=!1){return texture==null?null:usePMREM?getPMREM(texture):getCube(texture)}function getCube(texture){if(texture&&texture.isTexture){let mapping=texture.mapping;if(mapping===EquirectangularReflectionMapping||mapping===EquirectangularRefractionMapping)if(cubeMaps.has(texture)){let cubemap=cubeMaps.get(texture).texture;return mapTextureMapping(cubemap,texture.mapping)}else{let image=texture.image;if(image&&image.height>0){let renderTarget=new WebGLCubeRenderTarget(image.height);return renderTarget.fromEquirectangularTexture(renderer,texture),cubeMaps.set(texture,renderTarget),texture.addEventListener("dispose",onCubemapDispose),mapTextureMapping(renderTarget.texture,texture.mapping)}else return null}}return texture}function getPMREM(texture){if(texture&&texture.isTexture){let mapping=texture.mapping,isEquirectMap=mapping===EquirectangularReflectionMapping||mapping===EquirectangularRefractionMapping,isCubeMap=mapping===CubeReflectionMapping||mapping===CubeRefractionMapping;if(isEquirectMap||isCubeMap){let renderTarget=pmremMaps.get(texture),currentPMREMVersion=renderTarget!==void 0?renderTarget.texture.pmremVersion:0;if(texture.isRenderTargetTexture&&texture.pmremVersion!==currentPMREMVersion)return pmremGenerator===null&&(pmremGenerator=new PMREMGenerator(renderer)),renderTarget=isEquirectMap?pmremGenerator.fromEquirectangular(texture,renderTarget):pmremGenerator.fromCubemap(texture,renderTarget),renderTarget.texture.pmremVersion=texture.pmremVersion,pmremMaps.set(texture,renderTarget),renderTarget.texture;if(renderTarget!==void 0)return renderTarget.texture;{let image=texture.image;return isEquirectMap&&image&&image.height>0||isCubeMap&&image&&isCubeTextureComplete(image)?(pmremGenerator===null&&(pmremGenerator=new PMREMGenerator(renderer)),renderTarget=isEquirectMap?pmremGenerator.fromEquirectangular(texture):pmremGenerator.fromCubemap(texture),renderTarget.texture.pmremVersion=texture.pmremVersion,pmremMaps.set(texture,renderTarget),texture.addEventListener("dispose",onPMREMDispose),renderTarget.texture):null}}}return texture}function mapTextureMapping(texture,mapping){return mapping===EquirectangularReflectionMapping?texture.mapping=CubeReflectionMapping:mapping===EquirectangularRefractionMapping&&(texture.mapping=CubeRefractionMapping),texture}function isCubeTextureComplete(image){let count=0,length=6;for(let i=0;i<length;i++)image[i]!==void 0&&count++;return count===length}function onCubemapDispose(event){let texture=event.target;texture.removeEventListener("dispose",onCubemapDispose);let cubemap=cubeMaps.get(texture);cubemap!==void 0&&(cubeMaps.delete(texture),cubemap.dispose())}function onPMREMDispose(event){let texture=event.target;texture.removeEventListener("dispose",onPMREMDispose);let pmrem=pmremMaps.get(texture);pmrem!==void 0&&(pmremMaps.delete(texture),pmrem.dispose())}function dispose(){cubeMaps=new WeakMap,pmremMaps=new WeakMap,pmremGenerator!==null&&(pmremGenerator.dispose(),pmremGenerator=null)}return{get,dispose}}function WebGLExtensions(gl){let extensions={};function getExtension(name){if(extensions[name]!==void 0)return extensions[name];let extension=gl.getExtension(name);return extensions[name]=extension,extension}return{has:function(name){return getExtension(name)!==null},init:function(){getExtension("EXT_color_buffer_float"),getExtension("WEBGL_clip_cull_distance"),getExtension("OES_texture_float_linear"),getExtension("EXT_color_buffer_half_float"),getExtension("WEBGL_multisampled_render_to_texture"),getExtension("WEBGL_render_shared_exponent")},get:function(name){let extension=getExtension(name);return extension===null&&warnOnce("WebGLRenderer: "+name+" extension not supported."),extension}}}function WebGLGeometries(gl,attributes,info,bindingStates){let geometries={},wireframeAttributes=new WeakMap;function onGeometryDispose(event){let geometry=event.target;geometry.index!==null&&attributes.remove(geometry.index);for(let name in geometry.attributes)attributes.remove(geometry.attributes[name]);geometry.removeEventListener("dispose",onGeometryDispose),delete geometries[geometry.id];let attribute=wireframeAttributes.get(geometry);attribute&&(attributes.remove(attribute),wireframeAttributes.delete(geometry)),bindingStates.releaseStatesOfGeometry(geometry),geometry.isInstancedBufferGeometry===!0&&delete geometry._maxInstanceCount,info.memory.geometries--}function get(object,geometry){return geometries[geometry.id]===!0||(geometry.addEventListener("dispose",onGeometryDispose),geometries[geometry.id]=!0,info.memory.geometries++),geometry}function update(geometry){let geometryAttributes=geometry.attributes;for(let name in geometryAttributes)attributes.update(geometryAttributes[name],gl.ARRAY_BUFFER)}function updateWireframeAttribute(geometry){let indices=[],geometryIndex=geometry.index,geometryPosition=geometry.attributes.position,version=0;if(geometryPosition===void 0)return;if(geometryIndex!==null){let array=geometryIndex.array;version=geometryIndex.version;for(let i=0,l=array.length;i<l;i+=3){let a=array[i+0],b=array[i+1],c=array[i+2];indices.push(a,b,b,c,c,a)}}else{let array=geometryPosition.array;version=geometryPosition.version;for(let i=0,l=array.length/3-1;i<l;i+=3){let a=i+0,b=i+1,c=i+2;indices.push(a,b,b,c,c,a)}}let attribute=new(geometryPosition.count>=65535?Uint32BufferAttribute:Uint16BufferAttribute)(indices,1);attribute.version=version;let previousAttribute=wireframeAttributes.get(geometry);previousAttribute&&attributes.remove(previousAttribute),wireframeAttributes.set(geometry,attribute)}function getWireframeAttribute(geometry){let currentAttribute=wireframeAttributes.get(geometry);if(currentAttribute){let geometryIndex=geometry.index;geometryIndex!==null&&currentAttribute.version<geometryIndex.version&&updateWireframeAttribute(geometry)}else updateWireframeAttribute(geometry);return wireframeAttributes.get(geometry)}return{get,update,getWireframeAttribute}}function WebGLIndexedBufferRenderer(gl,extensions,info){let mode;function setMode(value){mode=value}let type,bytesPerElement;function setIndex(value){type=value.type,bytesPerElement=value.bytesPerElement}function render(start,count){gl.drawElements(mode,count,type,start*bytesPerElement),info.update(count,mode,1)}function renderInstances(start,count,primcount){primcount!==0&&(gl.drawElementsInstanced(mode,count,type,start*bytesPerElement,primcount),info.update(count,mode,primcount))}function renderMultiDraw(starts,counts,drawCount){if(drawCount===0)return;extensions.get("WEBGL_multi_draw").multiDrawElementsWEBGL(mode,counts,0,type,starts,0,drawCount);let elementCount=0;for(let i=0;i<drawCount;i++)elementCount+=counts[i];info.update(elementCount,mode,1)}this.setMode=setMode,this.setIndex=setIndex,this.render=render,this.renderInstances=renderInstances,this.renderMultiDraw=renderMultiDraw}function WebGLInfo(gl){let memory={geometries:0,textures:0},render={frame:0,calls:0,triangles:0,points:0,lines:0};function update(count,mode,instanceCount){switch(render.calls++,mode){case gl.TRIANGLES:render.triangles+=instanceCount*(count/3);break;case gl.LINES:render.lines+=instanceCount*(count/2);break;case gl.LINE_STRIP:render.lines+=instanceCount*(count-1);break;case gl.LINE_LOOP:render.lines+=instanceCount*count;break;case gl.POINTS:render.points+=instanceCount*count;break;default:error("WebGLInfo: Unknown draw mode:",mode);break}}function reset(){render.calls=0,render.triangles=0,render.points=0,render.lines=0}return{memory,render,programs:null,autoReset:!0,reset,update}}function WebGLMorphtargets(gl,capabilities,textures){let morphTextures=new WeakMap,morph=new Vector4;function update(object,geometry,program){let objectInfluences=object.morphTargetInfluences,morphAttribute=geometry.morphAttributes.position||geometry.morphAttributes.normal||geometry.morphAttributes.color,morphTargetsCount=morphAttribute!==void 0?morphAttribute.length:0,entry=morphTextures.get(geometry);if(entry===void 0||entry.count!==morphTargetsCount){let disposeTexture=function(){texture.dispose(),morphTextures.delete(geometry),geometry.removeEventListener("dispose",disposeTexture)};entry!==void 0&&entry.texture.dispose();let hasMorphPosition=geometry.morphAttributes.position!==void 0,hasMorphNormals=geometry.morphAttributes.normal!==void 0,hasMorphColors=geometry.morphAttributes.color!==void 0,morphTargets=geometry.morphAttributes.position||[],morphNormals=geometry.morphAttributes.normal||[],morphColors=geometry.morphAttributes.color||[],vertexDataCount=0;hasMorphPosition===!0&&(vertexDataCount=1),hasMorphNormals===!0&&(vertexDataCount=2),hasMorphColors===!0&&(vertexDataCount=3);let width=geometry.attributes.position.count*vertexDataCount,height=1;width>capabilities.maxTextureSize&&(height=Math.ceil(width/capabilities.maxTextureSize),width=capabilities.maxTextureSize);let buffer=new Float32Array(width*height*4*morphTargetsCount),texture=new DataArrayTexture(buffer,width,height,morphTargetsCount);texture.type=FloatType,texture.needsUpdate=!0;let vertexDataStride=vertexDataCount*4;for(let i=0;i<morphTargetsCount;i++){let morphTarget=morphTargets[i],morphNormal=morphNormals[i],morphColor=morphColors[i],offset=width*height*4*i;for(let j=0;j<morphTarget.count;j++){let stride=j*vertexDataStride;hasMorphPosition===!0&&(morph.fromBufferAttribute(morphTarget,j),buffer[offset+stride+0]=morph.x,buffer[offset+stride+1]=morph.y,buffer[offset+stride+2]=morph.z,buffer[offset+stride+3]=0),hasMorphNormals===!0&&(morph.fromBufferAttribute(morphNormal,j),buffer[offset+stride+4]=morph.x,buffer[offset+stride+5]=morph.y,buffer[offset+stride+6]=morph.z,buffer[offset+stride+7]=0),hasMorphColors===!0&&(morph.fromBufferAttribute(morphColor,j),buffer[offset+stride+8]=morph.x,buffer[offset+stride+9]=morph.y,buffer[offset+stride+10]=morph.z,buffer[offset+stride+11]=morphColor.itemSize===4?morph.w:1)}}entry={count:morphTargetsCount,texture,size:new Vector2(width,height)},morphTextures.set(geometry,entry),geometry.addEventListener("dispose",disposeTexture)}if(object.isInstancedMesh===!0&&object.morphTexture!==null)program.getUniforms().setValue(gl,"morphTexture",object.morphTexture,textures);else{let morphInfluencesSum=0;for(let i=0;i<objectInfluences.length;i++)morphInfluencesSum+=objectInfluences[i];let morphBaseInfluence=geometry.morphTargetsRelative?1:1-morphInfluencesSum;program.getUniforms().setValue(gl,"morphTargetBaseInfluence",morphBaseInfluence),program.getUniforms().setValue(gl,"morphTargetInfluences",objectInfluences)}program.getUniforms().setValue(gl,"morphTargetsTexture",entry.texture,textures),program.getUniforms().setValue(gl,"morphTargetsTextureSize",entry.size)}return{update}}function WebGLObjects(gl,geometries,attributes,bindingStates,info){let updateMap=new WeakMap;function update(object){let frame=info.render.frame,geometry=object.geometry,buffergeometry=geometries.get(object,geometry);if(updateMap.get(buffergeometry)!==frame&&(geometries.update(buffergeometry),updateMap.set(buffergeometry,frame)),object.isInstancedMesh&&(object.hasEventListener("dispose",onInstancedMeshDispose)===!1&&object.addEventListener("dispose",onInstancedMeshDispose),updateMap.get(object)!==frame&&(attributes.update(object.instanceMatrix,gl.ARRAY_BUFFER),object.instanceColor!==null&&attributes.update(object.instanceColor,gl.ARRAY_BUFFER),updateMap.set(object,frame))),object.isSkinnedMesh){let skeleton=object.skeleton;updateMap.get(skeleton)!==frame&&(skeleton.update(),updateMap.set(skeleton,frame))}return buffergeometry}function dispose(){updateMap=new WeakMap}function onInstancedMeshDispose(event){let instancedMesh=event.target;instancedMesh.removeEventListener("dispose",onInstancedMeshDispose),bindingStates.releaseStatesOfObject(instancedMesh),attributes.remove(instancedMesh.instanceMatrix),instancedMesh.instanceColor!==null&&attributes.remove(instancedMesh.instanceColor)}return{update,dispose}}var toneMappingMap={[LinearToneMapping]:"LINEAR_TONE_MAPPING",[ReinhardToneMapping]:"REINHARD_TONE_MAPPING",[CineonToneMapping]:"CINEON_TONE_MAPPING",[ACESFilmicToneMapping]:"ACES_FILMIC_TONE_MAPPING",[AgXToneMapping]:"AGX_TONE_MAPPING",[NeutralToneMapping]:"NEUTRAL_TONE_MAPPING",[CustomToneMapping]:"CUSTOM_TONE_MAPPING"};function WebGLOutput(type,width,height,antialias,depth,stencil){let targetScene=new WebGLRenderTarget(width,height,{type,depthBuffer:depth,stencilBuffer:stencil,samples:antialias?4:0,storeMultisampledDepthBuffer:!1,storeMultisampledStencilBuffer:!1,resolveDepthBuffer:!1,resolveStencilBuffer:!1}),targetA=null,targetB=null,geometry=new BufferGeometry;geometry.setAttribute("position",new Float32BufferAttribute([-1,3,0,-1,-1,0,3,-1,0],3)),geometry.setAttribute("uv",new Float32BufferAttribute([0,2,0,0,2,0],2));let material=new RawShaderMaterial({uniforms:{tDiffuse:{value:null}},vertexShader:`
			precision highp float;

			uniform mat4 modelViewMatrix;
			uniform mat4 projectionMatrix;

			attribute vec3 position;
			attribute vec2 uv;

			varying vec2 vUv;

			void main() {
				vUv = uv;
				gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
			}`,fragmentShader:`
			precision highp float;

			uniform sampler2D tDiffuse;

			varying vec2 vUv;

			#include <tonemapping_pars_fragment>
			#include <colorspace_pars_fragment>

			void main() {
				gl_FragColor = texture2D( tDiffuse, vUv );

				#ifdef LINEAR_TONE_MAPPING
					gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );
				#elif defined( REINHARD_TONE_MAPPING )
					gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );
				#elif defined( CINEON_TONE_MAPPING )
					gl_FragColor.rgb = CineonToneMapping( gl_FragColor.rgb );
				#elif defined( ACES_FILMIC_TONE_MAPPING )
					gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );
				#elif defined( AGX_TONE_MAPPING )
					gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );
				#elif defined( NEUTRAL_TONE_MAPPING )
					gl_FragColor.rgb = NeutralToneMapping( gl_FragColor.rgb );
				#elif defined( CUSTOM_TONE_MAPPING )
					gl_FragColor.rgb = CustomToneMapping( gl_FragColor.rgb );
				#endif

				#ifdef SRGB_TRANSFER
					gl_FragColor = sRGBTransferOETF( gl_FragColor );
				#endif
			}`,depthTest:!1,depthWrite:!1}),mesh=new Mesh(geometry,material),camera=new OrthographicCamera(-1,1,1,-1,0,1),_outputColorSpace=null,_outputToneMapping=null,_isCompositing=!1,_savedToneMapping,_savedRenderTarget=null,_effects=[],_hasRenderPass=!1;this.setSize=function(width2,height2){targetScene.setSize(width2,height2),targetA!==null&&targetA.setSize(width2,height2),targetB!==null&&targetB.setSize(width2,height2);for(let i=0;i<_effects.length;i++){let effect=_effects[i];effect.setSize&&effect.setSize(width2,height2)}},this.setEffects=function(effects){_effects=effects,_hasRenderPass=_effects.length>0&&_effects[0].isRenderPass===!0;let width2=targetScene.width,height2=targetScene.height;_effects.length>0&&targetA===null&&(targetA=new WebGLRenderTarget(width2,height2,{type:HalfFloatType,depthBuffer:!1,stencilBuffer:!1}),targetB=new WebGLRenderTarget(width2,height2,{type:HalfFloatType,depthBuffer:!1,stencilBuffer:!1}));for(let i=0;i<_effects.length;i++){let effect=_effects[i];effect.setSize&&effect.setSize(width2,height2)}},this.begin=function(renderer,renderTarget){if(_isCompositing||renderer.toneMapping===NoToneMapping&&_effects.length===0)return!1;if(_savedRenderTarget=renderTarget,renderTarget!==null){let width2=renderTarget.width,height2=renderTarget.height;(targetScene.width!==width2||targetScene.height!==height2)&&this.setSize(width2,height2)}return _hasRenderPass===!1&&renderer.setRenderTarget(targetScene),_savedToneMapping=renderer.toneMapping,renderer.toneMapping=NoToneMapping,!0},this.hasRenderPass=function(){return _hasRenderPass},this.end=function(renderer,deltaTime){renderer.toneMapping=_savedToneMapping,_isCompositing=!0;let readBuffer=targetScene,writeBuffer=targetA;for(let i=0;i<_effects.length;i++){let effect=_effects[i];effect.enabled!==!1&&(effect.render(renderer,writeBuffer,readBuffer,deltaTime),effect.needsSwap!==!1&&(readBuffer=writeBuffer,writeBuffer=writeBuffer===targetA?targetB:targetA))}if(_outputColorSpace!==renderer.outputColorSpace||_outputToneMapping!==renderer.toneMapping){_outputColorSpace=renderer.outputColorSpace,_outputToneMapping=renderer.toneMapping,material.defines={},ColorManagement.getTransfer(_outputColorSpace)===SRGBTransfer&&(material.defines.SRGB_TRANSFER="");let toneMapping=toneMappingMap[_outputToneMapping];toneMapping&&(material.defines[toneMapping]=""),material.needsUpdate=!0}material.uniforms.tDiffuse.value=readBuffer.texture,renderer.setRenderTarget(_savedRenderTarget),renderer.render(mesh,camera),_savedRenderTarget=null,_isCompositing=!1},this.isCompositing=function(){return _isCompositing},this.dispose=function(){targetScene.dispose(),targetA!==null&&targetA.dispose(),targetB!==null&&targetB.dispose(),geometry.dispose(),material.dispose()}}var emptyTexture=new Texture,emptyShadowTexture=new DepthTexture(1,1),emptyArrayTexture=new DataArrayTexture,empty3dTexture=new Data3DTexture,emptyCubeTexture=new CubeTexture,arrayCacheF32=[],arrayCacheI32=[],mat4array=new Float32Array(16),mat3array=new Float32Array(9),mat2array=new Float32Array(4);function flatten(array,nBlocks,blockSize){let firstElem=array[0];if(firstElem<=0||firstElem>0)return array;let n=nBlocks*blockSize,r=arrayCacheF32[n];if(r===void 0&&(r=new Float32Array(n),arrayCacheF32[n]=r),nBlocks!==0){firstElem.toArray(r,0);for(let i=1,offset=0;i!==nBlocks;++i)offset+=blockSize,array[i].toArray(r,offset)}return r}function arraysEqual(a,b){if(a.length!==b.length)return!1;for(let i=0,l=a.length;i<l;i++)if(a[i]!==b[i])return!1;return!0}function copyArray(a,b){for(let i=0,l=b.length;i<l;i++)a[i]=b[i]}function allocTexUnits(textures,n){let r=arrayCacheI32[n];r===void 0&&(r=new Int32Array(n),arrayCacheI32[n]=r);for(let i=0;i!==n;++i)r[i]=textures.allocateTextureUnit();return r}function setValueV1f(gl,v){let cache=this.cache;cache[0]!==v&&(gl.uniform1f(this.addr,v),cache[0]=v)}function setValueV2f(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y)&&(gl.uniform2f(this.addr,v.x,v.y),cache[0]=v.x,cache[1]=v.y);else{if(arraysEqual(cache,v))return;gl.uniform2fv(this.addr,v),copyArray(cache,v)}}function setValueV3f(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y||cache[2]!==v.z)&&(gl.uniform3f(this.addr,v.x,v.y,v.z),cache[0]=v.x,cache[1]=v.y,cache[2]=v.z);else if(v.r!==void 0)(cache[0]!==v.r||cache[1]!==v.g||cache[2]!==v.b)&&(gl.uniform3f(this.addr,v.r,v.g,v.b),cache[0]=v.r,cache[1]=v.g,cache[2]=v.b);else{if(arraysEqual(cache,v))return;gl.uniform3fv(this.addr,v),copyArray(cache,v)}}function setValueV4f(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y||cache[2]!==v.z||cache[3]!==v.w)&&(gl.uniform4f(this.addr,v.x,v.y,v.z,v.w),cache[0]=v.x,cache[1]=v.y,cache[2]=v.z,cache[3]=v.w);else{if(arraysEqual(cache,v))return;gl.uniform4fv(this.addr,v),copyArray(cache,v)}}function setValueM2(gl,v){let cache=this.cache,elements=v.elements;if(elements===void 0){if(arraysEqual(cache,v))return;gl.uniformMatrix2fv(this.addr,!1,v),copyArray(cache,v)}else{if(arraysEqual(cache,elements))return;mat2array.set(elements),gl.uniformMatrix2fv(this.addr,!1,mat2array),copyArray(cache,elements)}}function setValueM3(gl,v){let cache=this.cache,elements=v.elements;if(elements===void 0){if(arraysEqual(cache,v))return;gl.uniformMatrix3fv(this.addr,!1,v),copyArray(cache,v)}else{if(arraysEqual(cache,elements))return;mat3array.set(elements),gl.uniformMatrix3fv(this.addr,!1,mat3array),copyArray(cache,elements)}}function setValueM4(gl,v){let cache=this.cache,elements=v.elements;if(elements===void 0){if(arraysEqual(cache,v))return;gl.uniformMatrix4fv(this.addr,!1,v),copyArray(cache,v)}else{if(arraysEqual(cache,elements))return;mat4array.set(elements),gl.uniformMatrix4fv(this.addr,!1,mat4array),copyArray(cache,elements)}}function setValueV1i(gl,v){let cache=this.cache;cache[0]!==v&&(gl.uniform1i(this.addr,v),cache[0]=v)}function setValueV2i(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y)&&(gl.uniform2i(this.addr,v.x,v.y),cache[0]=v.x,cache[1]=v.y);else{if(arraysEqual(cache,v))return;gl.uniform2iv(this.addr,v),copyArray(cache,v)}}function setValueV3i(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y||cache[2]!==v.z)&&(gl.uniform3i(this.addr,v.x,v.y,v.z),cache[0]=v.x,cache[1]=v.y,cache[2]=v.z);else{if(arraysEqual(cache,v))return;gl.uniform3iv(this.addr,v),copyArray(cache,v)}}function setValueV4i(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y||cache[2]!==v.z||cache[3]!==v.w)&&(gl.uniform4i(this.addr,v.x,v.y,v.z,v.w),cache[0]=v.x,cache[1]=v.y,cache[2]=v.z,cache[3]=v.w);else{if(arraysEqual(cache,v))return;gl.uniform4iv(this.addr,v),copyArray(cache,v)}}function setValueV1ui(gl,v){let cache=this.cache;cache[0]!==v&&(gl.uniform1ui(this.addr,v),cache[0]=v)}function setValueV2ui(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y)&&(gl.uniform2ui(this.addr,v.x,v.y),cache[0]=v.x,cache[1]=v.y);else{if(arraysEqual(cache,v))return;gl.uniform2uiv(this.addr,v),copyArray(cache,v)}}function setValueV3ui(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y||cache[2]!==v.z)&&(gl.uniform3ui(this.addr,v.x,v.y,v.z),cache[0]=v.x,cache[1]=v.y,cache[2]=v.z);else{if(arraysEqual(cache,v))return;gl.uniform3uiv(this.addr,v),copyArray(cache,v)}}function setValueV4ui(gl,v){let cache=this.cache;if(v.x!==void 0)(cache[0]!==v.x||cache[1]!==v.y||cache[2]!==v.z||cache[3]!==v.w)&&(gl.uniform4ui(this.addr,v.x,v.y,v.z,v.w),cache[0]=v.x,cache[1]=v.y,cache[2]=v.z,cache[3]=v.w);else{if(arraysEqual(cache,v))return;gl.uniform4uiv(this.addr,v),copyArray(cache,v)}}function setValueT1(gl,v,textures){let cache=this.cache,unit=textures.allocateTextureUnit();cache[0]!==unit&&(gl.uniform1i(this.addr,unit),cache[0]=unit);let emptyTexture2D;this.type===gl.SAMPLER_2D_SHADOW?(emptyShadowTexture.compareFunction=textures.isReversedDepthBuffer()?GreaterEqualCompare:LessEqualCompare,emptyTexture2D=emptyShadowTexture):emptyTexture2D=emptyTexture,textures.setTexture2D(v||emptyTexture2D,unit)}function setValueT3D1(gl,v,textures){let cache=this.cache,unit=textures.allocateTextureUnit();cache[0]!==unit&&(gl.uniform1i(this.addr,unit),cache[0]=unit),textures.setTexture3D(v||empty3dTexture,unit)}function setValueT6(gl,v,textures){let cache=this.cache,unit=textures.allocateTextureUnit();cache[0]!==unit&&(gl.uniform1i(this.addr,unit),cache[0]=unit),textures.setTextureCube(v||emptyCubeTexture,unit)}function setValueT2DArray1(gl,v,textures){let cache=this.cache,unit=textures.allocateTextureUnit();cache[0]!==unit&&(gl.uniform1i(this.addr,unit),cache[0]=unit),textures.setTexture2DArray(v||emptyArrayTexture,unit)}function getSingularSetter(type){switch(type){case 5126:return setValueV1f;case 35664:return setValueV2f;case 35665:return setValueV3f;case 35666:return setValueV4f;case 35674:return setValueM2;case 35675:return setValueM3;case 35676:return setValueM4;case 5124:case 35670:return setValueV1i;case 35667:case 35671:return setValueV2i;case 35668:case 35672:return setValueV3i;case 35669:case 35673:return setValueV4i;case 5125:return setValueV1ui;case 36294:return setValueV2ui;case 36295:return setValueV3ui;case 36296:return setValueV4ui;case 35678:case 36198:case 36298:case 36306:case 35682:return setValueT1;case 35679:case 36299:case 36307:return setValueT3D1;case 35680:case 36300:case 36308:case 36293:return setValueT6;case 36289:case 36303:case 36311:case 36292:return setValueT2DArray1}}function setValueV1fArray(gl,v){gl.uniform1fv(this.addr,v)}function setValueV2fArray(gl,v){let data=flatten(v,this.size,2);gl.uniform2fv(this.addr,data)}function setValueV3fArray(gl,v){let data=flatten(v,this.size,3);gl.uniform3fv(this.addr,data)}function setValueV4fArray(gl,v){let data=flatten(v,this.size,4);gl.uniform4fv(this.addr,data)}function setValueM2Array(gl,v){let data=flatten(v,this.size,4);gl.uniformMatrix2fv(this.addr,!1,data)}function setValueM3Array(gl,v){let data=flatten(v,this.size,9);gl.uniformMatrix3fv(this.addr,!1,data)}function setValueM4Array(gl,v){let data=flatten(v,this.size,16);gl.uniformMatrix4fv(this.addr,!1,data)}function setValueV1iArray(gl,v){gl.uniform1iv(this.addr,v)}function setValueV2iArray(gl,v){gl.uniform2iv(this.addr,v)}function setValueV3iArray(gl,v){gl.uniform3iv(this.addr,v)}function setValueV4iArray(gl,v){gl.uniform4iv(this.addr,v)}function setValueV1uiArray(gl,v){gl.uniform1uiv(this.addr,v)}function setValueV2uiArray(gl,v){gl.uniform2uiv(this.addr,v)}function setValueV3uiArray(gl,v){gl.uniform3uiv(this.addr,v)}function setValueV4uiArray(gl,v){gl.uniform4uiv(this.addr,v)}function setValueT1Array(gl,v,textures){let cache=this.cache,n=v.length,units=allocTexUnits(textures,n);arraysEqual(cache,units)||(gl.uniform1iv(this.addr,units),copyArray(cache,units));let emptyTexture2D;this.type===gl.SAMPLER_2D_SHADOW?emptyTexture2D=emptyShadowTexture:emptyTexture2D=emptyTexture;for(let i=0;i!==n;++i)textures.setTexture2D(v[i]||emptyTexture2D,units[i])}function setValueT3DArray(gl,v,textures){let cache=this.cache,n=v.length,units=allocTexUnits(textures,n);arraysEqual(cache,units)||(gl.uniform1iv(this.addr,units),copyArray(cache,units));for(let i=0;i!==n;++i)textures.setTexture3D(v[i]||empty3dTexture,units[i])}function setValueT6Array(gl,v,textures){let cache=this.cache,n=v.length,units=allocTexUnits(textures,n);arraysEqual(cache,units)||(gl.uniform1iv(this.addr,units),copyArray(cache,units));for(let i=0;i!==n;++i)textures.setTextureCube(v[i]||emptyCubeTexture,units[i])}function setValueT2DArrayArray(gl,v,textures){let cache=this.cache,n=v.length,units=allocTexUnits(textures,n);arraysEqual(cache,units)||(gl.uniform1iv(this.addr,units),copyArray(cache,units));for(let i=0;i!==n;++i)textures.setTexture2DArray(v[i]||emptyArrayTexture,units[i])}function getPureArraySetter(type){switch(type){case 5126:return setValueV1fArray;case 35664:return setValueV2fArray;case 35665:return setValueV3fArray;case 35666:return setValueV4fArray;case 35674:return setValueM2Array;case 35675:return setValueM3Array;case 35676:return setValueM4Array;case 5124:case 35670:return setValueV1iArray;case 35667:case 35671:return setValueV2iArray;case 35668:case 35672:return setValueV3iArray;case 35669:case 35673:return setValueV4iArray;case 5125:return setValueV1uiArray;case 36294:return setValueV2uiArray;case 36295:return setValueV3uiArray;case 36296:return setValueV4uiArray;case 35678:case 36198:case 36298:case 36306:case 35682:return setValueT1Array;case 35679:case 36299:case 36307:return setValueT3DArray;case 35680:case 36300:case 36308:case 36293:return setValueT6Array;case 36289:case 36303:case 36311:case 36292:return setValueT2DArrayArray}}var SingleUniform=class{constructor(id,activeInfo,addr){this.id=id,this.addr=addr,this.cache=[],this.type=activeInfo.type,this.setValue=getSingularSetter(activeInfo.type)}},PureArrayUniform=class{constructor(id,activeInfo,addr){this.id=id,this.addr=addr,this.cache=[],this.type=activeInfo.type,this.size=activeInfo.size,this.setValue=getPureArraySetter(activeInfo.type)}},StructuredUniform=class{constructor(id){this.id=id,this.seq=[],this.map={}}setValue(gl,value,textures){let seq=this.seq;for(let i=0,n=seq.length;i!==n;++i){let u=seq[i];u.setValue(gl,value[u.id],textures)}}},RePathPart=/(\w+)(\])?(\[|\.)?/g;function addUniform(container,uniformObject){container.seq.push(uniformObject),container.map[uniformObject.id]=uniformObject}function parseUniform(activeInfo,addr,container){let path=activeInfo.name,pathLength=path.length;for(RePathPart.lastIndex=0;;){let match=RePathPart.exec(path),matchEnd=RePathPart.lastIndex,id=match[1],idIsIndex=match[2]==="]",subscript=match[3];if(idIsIndex&&(id=id|0),subscript===void 0||subscript==="["&&matchEnd+2===pathLength){addUniform(container,subscript===void 0?new SingleUniform(id,activeInfo,addr):new PureArrayUniform(id,activeInfo,addr));break}else{let next=container.map[id];next===void 0&&(next=new StructuredUniform(id),addUniform(container,next)),container=next}}}var WebGLUniforms=class{constructor(gl,program){this.seq=[],this.map={};let n=gl.getProgramParameter(program,gl.ACTIVE_UNIFORMS);for(let i=0;i<n;++i){let info=gl.getActiveUniform(program,i),addr=gl.getUniformLocation(program,info.name);parseUniform(info,addr,this)}let shadowSamplers=[],otherUniforms=[];for(let u of this.seq)u.type===gl.SAMPLER_2D_SHADOW||u.type===gl.SAMPLER_CUBE_SHADOW||u.type===gl.SAMPLER_2D_ARRAY_SHADOW?shadowSamplers.push(u):otherUniforms.push(u);shadowSamplers.length>0&&(this.seq=shadowSamplers.concat(otherUniforms))}setValue(gl,name,value,textures){let u=this.map[name];u!==void 0&&u.setValue(gl,value,textures)}setOptional(gl,object,name){let v=object[name];v!==void 0&&this.setValue(gl,name,v)}static upload(gl,seq,values,textures){for(let i=0,n=seq.length;i!==n;++i){let u=seq[i],v=values[u.id];v.needsUpdate!==!1&&u.setValue(gl,v.value,textures)}}static seqWithValue(seq,values){let r=[];for(let i=0,n=seq.length;i!==n;++i){let u=seq[i];u.id in values&&r.push(u)}return r}};function WebGLShader(gl,type,string){let shader=gl.createShader(type);return gl.shaderSource(shader,string),gl.compileShader(shader),shader}var COMPLETION_STATUS_KHR=37297,programIdCount=0;function handleSource(string,errorLine){let lines=string.split(`
`),lines2=[],from=Math.max(errorLine-6,0),to=Math.min(errorLine+6,lines.length);for(let i=from;i<to;i++){let line=i+1;lines2.push(`${line===errorLine?">":" "} ${line}: ${lines[i]}`)}return lines2.join(`
`)}var _m0=new Matrix3;function getEncodingComponents(colorSpace){ColorManagement._getMatrix(_m0,ColorManagement.workingColorSpace,colorSpace);let encodingMatrix=`mat3( ${_m0.elements.map(v=>v.toFixed(4))} )`;switch(ColorManagement.getTransfer(colorSpace)){case LinearTransfer:return[encodingMatrix,"LinearTransferOETF"];case SRGBTransfer:return[encodingMatrix,"sRGBTransferOETF"];default:return warn("WebGLProgram: Unsupported color space: ",colorSpace),[encodingMatrix,"LinearTransferOETF"]}}function getShaderErrors(gl,shader,type){let status=gl.getShaderParameter(shader,gl.COMPILE_STATUS),errors=(gl.getShaderInfoLog(shader)||"").trim();if(status&&errors==="")return"";let errorMatches=/ERROR: 0:(\d+)/.exec(errors);if(errorMatches){let errorLine=parseInt(errorMatches[1]);return type.toUpperCase()+`

`+errors+`

`+handleSource(gl.getShaderSource(shader),errorLine)}else return errors}function getTexelEncodingFunction(functionName,colorSpace){let components=getEncodingComponents(colorSpace);return[`vec4 ${functionName}( vec4 value ) {`,`	return ${components[1]}( vec4( value.rgb * ${components[0]}, value.a ) );`,"}"].join(`
`)}var toneMappingFunctions={[LinearToneMapping]:"Linear",[ReinhardToneMapping]:"Reinhard",[CineonToneMapping]:"Cineon",[ACESFilmicToneMapping]:"ACESFilmic",[AgXToneMapping]:"AgX",[NeutralToneMapping]:"Neutral",[CustomToneMapping]:"Custom"};function getToneMappingFunction(functionName,toneMapping){let toneMappingName=toneMappingFunctions[toneMapping];return toneMappingName===void 0?(warn("WebGLProgram: Unsupported toneMapping:",toneMapping),"vec3 "+functionName+"( vec3 color ) { return LinearToneMapping( color ); }"):"vec3 "+functionName+"( vec3 color ) { return "+toneMappingName+"ToneMapping( color ); }"}var _v03=new Vector3;function getLuminanceFunction(){ColorManagement.getLuminanceCoefficients(_v03);let r=_v03.x.toFixed(4),g=_v03.y.toFixed(4),b=_v03.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${r}, ${g}, ${b} );`,"	return dot( weights, rgb );","}"].join(`
`)}function generateVertexExtensions(parameters){return[parameters.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",parameters.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(filterEmptyLine).join(`
`)}function generateDefines(defines){let chunks=[];for(let name in defines){let value=defines[name];value!==!1&&chunks.push("#define "+name+" "+value)}return chunks.join(`
`)}function fetchAttributeLocations(gl,program){let attributes={},n=gl.getProgramParameter(program,gl.ACTIVE_ATTRIBUTES);for(let i=0;i<n;i++){let info=gl.getActiveAttrib(program,i),name=info.name,locationSize=1;info.type===gl.FLOAT_MAT2&&(locationSize=2),info.type===gl.FLOAT_MAT3&&(locationSize=3),info.type===gl.FLOAT_MAT4&&(locationSize=4),attributes[name]={type:info.type,location:gl.getAttribLocation(program,name),locationSize}}return attributes}function filterEmptyLine(string){return string!==""}function replaceLightNums(string,parameters){let numSpotLightCoords=parameters.numSpotLightShadows+parameters.numSpotLightMaps-parameters.numSpotLightShadowsWithMaps;return string.replace(/NUM_SUN_LIGHTS/g,parameters.numSunLights).replace(/NUM_DIR_LIGHTS/g,parameters.numDirLights).replace(/NUM_SPOT_LIGHTS/g,parameters.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,parameters.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,numSpotLightCoords).replace(/NUM_RECT_AREA_LIGHTS/g,parameters.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,parameters.numPointLights).replace(/NUM_HEMI_LIGHTS/g,parameters.numHemiLights).replace(/NUM_SUN_LIGHT_SHADOWS/g,parameters.numSunLightShadows).replace(/NUM_DIR_LIGHT_SHADOWS/g,parameters.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,parameters.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,parameters.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,parameters.numPointLightShadows)}function replaceClippingPlaneNums(string,parameters){return string.replace(/NUM_CLIPPING_PLANES/g,parameters.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,parameters.numClippingPlanes-parameters.numClipIntersection)}var includePattern=/^[ \t]*#include +<([\w\d./]+)>/gm;function resolveIncludes(string){return string.replace(includePattern,includeReplacer)}var shaderChunkMap=new Map;function includeReplacer(match,include){let string=ShaderChunk[include];if(string===void 0){let newInclude=shaderChunkMap.get(include);if(newInclude!==void 0)string=ShaderChunk[newInclude],warn('WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',include,newInclude);else throw new Error("THREE.WebGLProgram: Can not resolve #include <"+include+">")}return resolveIncludes(string)}var unrollLoopPattern=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function unrollLoops(string){return string.replace(unrollLoopPattern,loopReplacer)}function loopReplacer(match,start,end,snippet){let string="";for(let i=parseInt(start);i<parseInt(end);i++)string+=snippet.replace(/\[\s*i\s*\]/g,"[ "+i+" ]").replace(/UNROLLED_LOOP_INDEX/g,i);return string}function generatePrecision(parameters){let precisionstring=`precision ${parameters.precision} float;
	precision ${parameters.precision} int;
	precision ${parameters.precision} sampler2D;
	precision ${parameters.precision} samplerCube;
	precision ${parameters.precision} sampler3D;
	precision ${parameters.precision} sampler2DArray;
	precision ${parameters.precision} sampler2DShadow;
	precision ${parameters.precision} samplerCubeShadow;
	precision ${parameters.precision} sampler2DArrayShadow;
	precision ${parameters.precision} isampler2D;
	precision ${parameters.precision} isampler3D;
	precision ${parameters.precision} isamplerCube;
	precision ${parameters.precision} isampler2DArray;
	precision ${parameters.precision} usampler2D;
	precision ${parameters.precision} usampler3D;
	precision ${parameters.precision} usamplerCube;
	precision ${parameters.precision} usampler2DArray;
	`;return parameters.precision==="highp"?precisionstring+=`
#define HIGH_PRECISION`:parameters.precision==="mediump"?precisionstring+=`
#define MEDIUM_PRECISION`:parameters.precision==="lowp"&&(precisionstring+=`
#define LOW_PRECISION`),precisionstring}var shadowMapTypeDefines={[PCFShadowMap]:"SHADOWMAP_TYPE_PCF",[VSMShadowMap]:"SHADOWMAP_TYPE_VSM"};function generateShadowMapTypeDefine(parameters){return shadowMapTypeDefines[parameters.shadowMapType]||"SHADOWMAP_TYPE_BASIC"}var envMapTypeDefines={[CubeReflectionMapping]:"ENVMAP_TYPE_CUBE",[CubeRefractionMapping]:"ENVMAP_TYPE_CUBE",[CubeUVReflectionMapping]:"ENVMAP_TYPE_CUBE_UV"};function generateEnvMapTypeDefine(parameters){return parameters.envMap===!1?"ENVMAP_TYPE_CUBE":envMapTypeDefines[parameters.envMapMode]||"ENVMAP_TYPE_CUBE"}var envMapModeDefines={[CubeRefractionMapping]:"ENVMAP_MODE_REFRACTION"};function generateEnvMapModeDefine(parameters){return parameters.envMap===!1?"ENVMAP_MODE_REFLECTION":envMapModeDefines[parameters.envMapMode]||"ENVMAP_MODE_REFLECTION"}var envMapBlendingDefines={[MultiplyOperation]:"ENVMAP_BLENDING_MULTIPLY",[MixOperation]:"ENVMAP_BLENDING_MIX",[AddOperation]:"ENVMAP_BLENDING_ADD"};function generateEnvMapBlendingDefine(parameters){return parameters.envMap===!1?"ENVMAP_BLENDING_NONE":envMapBlendingDefines[parameters.combine]||"ENVMAP_BLENDING_NONE"}function generateCubeUVSize(parameters){let imageHeight=parameters.envMapCubeUVHeight;if(imageHeight===null)return null;let maxMip=Math.log2(imageHeight)-2,texelHeight=1/imageHeight;return{texelWidth:1/(3*Math.max(Math.pow(2,maxMip),112)),texelHeight,maxMip}}function WebGLProgram(renderer,cacheKey,parameters,bindingStates){let gl=renderer.getContext(),defines=parameters.defines,vertexShader=parameters.vertexShader,fragmentShader=parameters.fragmentShader,shadowMapTypeDefine=generateShadowMapTypeDefine(parameters),envMapTypeDefine=generateEnvMapTypeDefine(parameters),envMapModeDefine=generateEnvMapModeDefine(parameters),envMapBlendingDefine=generateEnvMapBlendingDefine(parameters),envMapCubeUVSize=generateCubeUVSize(parameters),customVertexExtensions=generateVertexExtensions(parameters),customDefines=generateDefines(defines),program=gl.createProgram(),prefixVertex,prefixFragment,versionString=parameters.glslVersion?"#version "+parameters.glslVersion+`
`:"";parameters.isRawShaderMaterial?(prefixVertex=["#define SHADER_TYPE "+parameters.shaderType,"#define SHADER_NAME "+parameters.shaderName,customDefines].filter(filterEmptyLine).join(`
`),prefixVertex.length>0&&(prefixVertex+=`
`),prefixFragment=["#define SHADER_TYPE "+parameters.shaderType,"#define SHADER_NAME "+parameters.shaderName,customDefines].filter(filterEmptyLine).join(`
`),prefixFragment.length>0&&(prefixFragment+=`
`)):(prefixVertex=[generatePrecision(parameters),"#define SHADER_TYPE "+parameters.shaderType,"#define SHADER_NAME "+parameters.shaderName,customDefines,parameters.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",parameters.batching?"#define USE_BATCHING":"",parameters.batchingColor?"#define USE_BATCHING_COLOR":"",parameters.instancing?"#define USE_INSTANCING":"",parameters.instancingColor?"#define USE_INSTANCING_COLOR":"",parameters.instancingMorph?"#define USE_INSTANCING_MORPH":"",parameters.useFog&&parameters.fog?"#define USE_FOG":"",parameters.useFog&&parameters.fogExp2?"#define FOG_EXP2":"",parameters.map?"#define USE_MAP":"",parameters.envMap?"#define USE_ENVMAP":"",parameters.envMap?"#define "+envMapModeDefine:"",parameters.lightMap?"#define USE_LIGHTMAP":"",parameters.aoMap?"#define USE_AOMAP":"",parameters.bumpMap?"#define USE_BUMPMAP":"",parameters.normalMap?"#define USE_NORMALMAP":"",parameters.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",parameters.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",parameters.displacementMap?"#define USE_DISPLACEMENTMAP":"",parameters.emissiveMap?"#define USE_EMISSIVEMAP":"",parameters.anisotropy?"#define USE_ANISOTROPY":"",parameters.anisotropyMap?"#define USE_ANISOTROPYMAP":"",parameters.clearcoatMap?"#define USE_CLEARCOATMAP":"",parameters.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",parameters.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",parameters.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",parameters.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",parameters.specularMap?"#define USE_SPECULARMAP":"",parameters.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",parameters.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",parameters.roughnessMap?"#define USE_ROUGHNESSMAP":"",parameters.metalnessMap?"#define USE_METALNESSMAP":"",parameters.alphaMap?"#define USE_ALPHAMAP":"",parameters.alphaHash?"#define USE_ALPHAHASH":"",parameters.transmission?"#define USE_TRANSMISSION":"",parameters.transmissionMap?"#define USE_TRANSMISSIONMAP":"",parameters.thicknessMap?"#define USE_THICKNESSMAP":"",parameters.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",parameters.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",parameters.mapUv?"#define MAP_UV "+parameters.mapUv:"",parameters.alphaMapUv?"#define ALPHAMAP_UV "+parameters.alphaMapUv:"",parameters.lightMapUv?"#define LIGHTMAP_UV "+parameters.lightMapUv:"",parameters.aoMapUv?"#define AOMAP_UV "+parameters.aoMapUv:"",parameters.emissiveMapUv?"#define EMISSIVEMAP_UV "+parameters.emissiveMapUv:"",parameters.bumpMapUv?"#define BUMPMAP_UV "+parameters.bumpMapUv:"",parameters.normalMapUv?"#define NORMALMAP_UV "+parameters.normalMapUv:"",parameters.displacementMapUv?"#define DISPLACEMENTMAP_UV "+parameters.displacementMapUv:"",parameters.metalnessMapUv?"#define METALNESSMAP_UV "+parameters.metalnessMapUv:"",parameters.roughnessMapUv?"#define ROUGHNESSMAP_UV "+parameters.roughnessMapUv:"",parameters.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+parameters.anisotropyMapUv:"",parameters.clearcoatMapUv?"#define CLEARCOATMAP_UV "+parameters.clearcoatMapUv:"",parameters.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+parameters.clearcoatNormalMapUv:"",parameters.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+parameters.clearcoatRoughnessMapUv:"",parameters.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+parameters.iridescenceMapUv:"",parameters.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+parameters.iridescenceThicknessMapUv:"",parameters.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+parameters.sheenColorMapUv:"",parameters.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+parameters.sheenRoughnessMapUv:"",parameters.specularMapUv?"#define SPECULARMAP_UV "+parameters.specularMapUv:"",parameters.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+parameters.specularColorMapUv:"",parameters.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+parameters.specularIntensityMapUv:"",parameters.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+parameters.transmissionMapUv:"",parameters.thicknessMapUv?"#define THICKNESSMAP_UV "+parameters.thicknessMapUv:"",parameters.vertexTangents&&parameters.flatShading===!1?"#define USE_TANGENT":"",parameters.vertexNormals?"#define HAS_NORMAL":"",parameters.vertexColors?"#define USE_COLOR":"",parameters.vertexAlphas?"#define USE_COLOR_ALPHA":"",parameters.vertexUv1s?"#define USE_UV1":"",parameters.vertexUv2s?"#define USE_UV2":"",parameters.vertexUv3s?"#define USE_UV3":"",parameters.pointsUvs?"#define USE_POINTS_UV":"",parameters.flatShading?"#define FLAT_SHADED":"",parameters.skinning?"#define USE_SKINNING":"",parameters.morphTargets?"#define USE_MORPHTARGETS":"",parameters.morphNormals&&parameters.flatShading===!1?"#define USE_MORPHNORMALS":"",parameters.morphColors?"#define USE_MORPHCOLORS":"",parameters.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+parameters.morphTextureStride:"",parameters.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+parameters.morphTargetsCount:"",parameters.doubleSided?"#define DOUBLE_SIDED":"",parameters.flipSided?"#define FLIP_SIDED":"",parameters.shadowMapEnabled?"#define USE_SHADOWMAP":"",parameters.shadowMapEnabled?"#define "+shadowMapTypeDefine:"",parameters.sizeAttenuation?"#define USE_SIZEATTENUATION":"",parameters.numLightProbes>0?"#define USE_LIGHT_PROBES":"",parameters.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",parameters.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(filterEmptyLine).join(`
`),prefixFragment=[generatePrecision(parameters),"#define SHADER_TYPE "+parameters.shaderType,"#define SHADER_NAME "+parameters.shaderName,customDefines,parameters.useFog&&parameters.fog?"#define USE_FOG":"",parameters.useFog&&parameters.fogExp2?"#define FOG_EXP2":"",parameters.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",parameters.map?"#define USE_MAP":"",parameters.matcap?"#define USE_MATCAP":"",parameters.envMap?"#define USE_ENVMAP":"",parameters.envMap?"#define "+envMapTypeDefine:"",parameters.envMap?"#define "+envMapModeDefine:"",parameters.envMap?"#define "+envMapBlendingDefine:"",envMapCubeUVSize?"#define CUBEUV_TEXEL_WIDTH "+envMapCubeUVSize.texelWidth:"",envMapCubeUVSize?"#define CUBEUV_TEXEL_HEIGHT "+envMapCubeUVSize.texelHeight:"",envMapCubeUVSize?"#define CUBEUV_MAX_MIP "+envMapCubeUVSize.maxMip+".0":"",parameters.lightMap?"#define USE_LIGHTMAP":"",parameters.aoMap?"#define USE_AOMAP":"",parameters.bumpMap?"#define USE_BUMPMAP":"",parameters.normalMap?"#define USE_NORMALMAP":"",parameters.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",parameters.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",parameters.packedNormalMap?"#define USE_PACKED_NORMALMAP":"",parameters.emissiveMap?"#define USE_EMISSIVEMAP":"",parameters.anisotropy?"#define USE_ANISOTROPY":"",parameters.anisotropyMap?"#define USE_ANISOTROPYMAP":"",parameters.clearcoat?"#define USE_CLEARCOAT":"",parameters.clearcoatMap?"#define USE_CLEARCOATMAP":"",parameters.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",parameters.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",parameters.dispersion?"#define USE_DISPERSION":"",parameters.retroreflection?"#define USE_RETROREFLECTION":"",parameters.iridescence?"#define USE_IRIDESCENCE":"",parameters.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",parameters.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",parameters.specularMap?"#define USE_SPECULARMAP":"",parameters.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",parameters.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",parameters.roughnessMap?"#define USE_ROUGHNESSMAP":"",parameters.metalnessMap?"#define USE_METALNESSMAP":"",parameters.alphaMap?"#define USE_ALPHAMAP":"",parameters.alphaTest?"#define USE_ALPHATEST":"",parameters.alphaHash?"#define USE_ALPHAHASH":"",parameters.sheen?"#define USE_SHEEN":"",parameters.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",parameters.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",parameters.transmission?"#define USE_TRANSMISSION":"",parameters.transmissionMap?"#define USE_TRANSMISSIONMAP":"",parameters.thicknessMap?"#define USE_THICKNESSMAP":"",parameters.vertexTangents&&parameters.flatShading===!1?"#define USE_TANGENT":"",parameters.vertexColors||parameters.instancingColor?"#define USE_COLOR":"",parameters.vertexAlphas||parameters.batchingColor?"#define USE_COLOR_ALPHA":"",parameters.vertexUv1s?"#define USE_UV1":"",parameters.vertexUv2s?"#define USE_UV2":"",parameters.vertexUv3s?"#define USE_UV3":"",parameters.pointsUvs?"#define USE_POINTS_UV":"",parameters.gradientMap?"#define USE_GRADIENTMAP":"",parameters.flatShading?"#define FLAT_SHADED":"",parameters.doubleSided?"#define DOUBLE_SIDED":"",parameters.flipSided?"#define FLIP_SIDED":"",parameters.shadowMapEnabled?"#define USE_SHADOWMAP":"",parameters.shadowMapEnabled?"#define "+shadowMapTypeDefine:"",parameters.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",parameters.numLightProbes>0?"#define USE_LIGHT_PROBES":"",parameters.numLightProbeGrids>0?"#define USE_LIGHT_PROBES_GRID":"",parameters.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",parameters.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",parameters.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",parameters.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",parameters.toneMapping!==NoToneMapping?"#define TONE_MAPPING":"",parameters.toneMapping!==NoToneMapping?ShaderChunk.tonemapping_pars_fragment:"",parameters.toneMapping!==NoToneMapping?getToneMappingFunction("toneMapping",parameters.toneMapping):"",parameters.dithering?"#define DITHERING":"",parameters.opaque?"#define OPAQUE":"",ShaderChunk.colorspace_pars_fragment,getTexelEncodingFunction("linearToOutputTexel",parameters.outputColorSpace),getLuminanceFunction(),parameters.useDepthPacking?"#define DEPTH_PACKING "+parameters.depthPacking:"",`
`].filter(filterEmptyLine).join(`
`)),vertexShader=resolveIncludes(vertexShader),vertexShader=replaceLightNums(vertexShader,parameters),vertexShader=replaceClippingPlaneNums(vertexShader,parameters),fragmentShader=resolveIncludes(fragmentShader),fragmentShader=replaceLightNums(fragmentShader,parameters),fragmentShader=replaceClippingPlaneNums(fragmentShader,parameters),vertexShader=unrollLoops(vertexShader),fragmentShader=unrollLoops(fragmentShader),parameters.isRawShaderMaterial!==!0&&(versionString=`#version 300 es
`,prefixVertex=[customVertexExtensions,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+prefixVertex,prefixFragment=["#define varying in",parameters.glslVersion===GLSL3?"":"layout(location = 0) out highp vec4 pc_fragColor;",parameters.glslVersion===GLSL3?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+prefixFragment);let vertexGlsl=versionString+prefixVertex+vertexShader,fragmentGlsl=versionString+prefixFragment+fragmentShader,glVertexShader=WebGLShader(gl,gl.VERTEX_SHADER,vertexGlsl),glFragmentShader=WebGLShader(gl,gl.FRAGMENT_SHADER,fragmentGlsl);gl.attachShader(program,glVertexShader),gl.attachShader(program,glFragmentShader),parameters.index0AttributeName!==void 0?gl.bindAttribLocation(program,0,parameters.index0AttributeName):parameters.hasPositionAttribute===!0&&gl.bindAttribLocation(program,0,"position"),gl.linkProgram(program);function onFirstUse(self2){if(renderer.debug.checkShaderErrors){let programInfoLog=gl.getProgramInfoLog(program)||"",vertexShaderInfoLog=gl.getShaderInfoLog(glVertexShader)||"",fragmentShaderInfoLog=gl.getShaderInfoLog(glFragmentShader)||"",programLog=programInfoLog.trim(),vertexLog=vertexShaderInfoLog.trim(),fragmentLog=fragmentShaderInfoLog.trim(),runnable=!0,haveDiagnostics=!0;if(gl.getProgramParameter(program,gl.LINK_STATUS)===!1)if(runnable=!1,typeof renderer.debug.onShaderError=="function")renderer.debug.onShaderError(gl,program,glVertexShader,glFragmentShader);else{let vertexErrors=getShaderErrors(gl,glVertexShader,"vertex"),fragmentErrors=getShaderErrors(gl,glFragmentShader,"fragment");error("WebGLProgram: Shader Error "+gl.getError()+" - VALIDATE_STATUS "+gl.getProgramParameter(program,gl.VALIDATE_STATUS)+`

Material Name: `+self2.name+`
Material Type: `+self2.type+`

Program Info Log: `+programLog+`
`+vertexErrors+`
`+fragmentErrors)}else programLog!==""?warn("WebGLProgram: Program Info Log:",programLog):(vertexLog===""||fragmentLog==="")&&(haveDiagnostics=!1);haveDiagnostics&&(self2.diagnostics={runnable,programLog,vertexShader:{log:vertexLog,prefix:prefixVertex},fragmentShader:{log:fragmentLog,prefix:prefixFragment}})}gl.deleteShader(glVertexShader),gl.deleteShader(glFragmentShader),cachedUniforms=new WebGLUniforms(gl,program),cachedAttributes=fetchAttributeLocations(gl,program)}let cachedUniforms;this.getUniforms=function(){return cachedUniforms===void 0&&onFirstUse(this),cachedUniforms};let cachedAttributes;this.getAttributes=function(){return cachedAttributes===void 0&&onFirstUse(this),cachedAttributes};let programReady=parameters.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return programReady===!1&&(programReady=gl.getProgramParameter(program,COMPLETION_STATUS_KHR)),programReady},this.destroy=function(){bindingStates.releaseStatesOfProgram(this),gl.deleteProgram(program),this.program=void 0},this.type=parameters.shaderType,this.name=parameters.shaderName,this.id=programIdCount++,this.cacheKey=cacheKey,this.usedTimes=1,this.program=program,this.vertexShader=glVertexShader,this.fragmentShader=glFragmentShader,this}var _id3=0,WebGLShaderCache=class{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(material,vertexShaderStage,fragmentShaderStage){let materialShaders=this._getShaderCacheForMaterial(material);return materialShaders.has(vertexShaderStage)===!1&&(materialShaders.add(vertexShaderStage),vertexShaderStage.usedTimes++),materialShaders.has(fragmentShaderStage)===!1&&(materialShaders.add(fragmentShaderStage),fragmentShaderStage.usedTimes++),this}remove(material){let materialShaders=this.materialCache.get(material);for(let shaderStage of materialShaders)shaderStage.usedTimes--,shaderStage.usedTimes===0&&this.shaderCache.delete(shaderStage.code);return this.materialCache.delete(material),this}getVertexShaderStage(material){return this._getShaderStage(material.vertexShader)}getFragmentShaderStage(material){return this._getShaderStage(material.fragmentShader)}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(material){let cache=this.materialCache,set=cache.get(material);return set===void 0&&(set=new Set,cache.set(material,set)),set}_getShaderStage(code){let cache=this.shaderCache,stage=cache.get(code);return stage===void 0&&(stage=new WebGLShaderStage(code),cache.set(code,stage)),stage}},WebGLShaderStage=class{constructor(code){this.id=_id3++,this.code=code,this.usedTimes=0}};function isPackedRGFormat(format){return format===RGFormat||format===RG11_EAC_Format||format===RED_GREEN_RGTC2_Format}function WebGLPrograms(renderer,environments,extensions,capabilities,bindingStates,clipping){let _programLayers=new Layers,_customShaders=new WebGLShaderCache,_activeChannels=new Set,programs=[],programsMap=new Map,logarithmicDepthBuffer=capabilities.logarithmicDepthBuffer,precision=capabilities.precision,shaderIDs={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distance",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function getChannel(value){return _activeChannels.add(value),value===0?"uv":`uv${value}`}function getParameters(material,lights,shadows,scene,object,lightProbeGrids){let fog=scene.fog,geometry=object.geometry,environment=material.isMeshStandardMaterial||material.isMeshLambertMaterial||material.isMeshPhongMaterial?scene.environment:null,usePMREM=material.isMeshStandardMaterial||material.isMeshLambertMaterial&&!material.envMap||material.isMeshPhongMaterial&&!material.envMap,envMap=environments.get(material.envMap||environment,usePMREM),envMapCubeUVHeight=envMap&&envMap.mapping===CubeUVReflectionMapping?envMap.image.height:null,shaderID=shaderIDs[material.type];material.precision!==null&&(precision=capabilities.getMaxPrecision(material.precision),precision!==material.precision&&warn("WebGLProgram.getParameters:",material.precision,"not supported, using",precision,"instead."));let morphAttribute=geometry.morphAttributes.position||geometry.morphAttributes.normal||geometry.morphAttributes.color,morphTargetsCount=morphAttribute!==void 0?morphAttribute.length:0,morphTextureStride=0;geometry.morphAttributes.position!==void 0&&(morphTextureStride=1),geometry.morphAttributes.normal!==void 0&&(morphTextureStride=2),geometry.morphAttributes.color!==void 0&&(morphTextureStride=3);let vertexShader,fragmentShader,customVertexShaderID,customFragmentShaderID;if(shaderID){let shader=ShaderLib[shaderID];vertexShader=shader.vertexShader,fragmentShader=shader.fragmentShader}else{vertexShader=material.vertexShader,fragmentShader=material.fragmentShader;let vertexShaderStage=_customShaders.getVertexShaderStage(material),fragmentShaderStage=_customShaders.getFragmentShaderStage(material);_customShaders.update(material,vertexShaderStage,fragmentShaderStage),customVertexShaderID=vertexShaderStage.id,customFragmentShaderID=fragmentShaderStage.id}let currentRenderTarget=renderer.getRenderTarget(),reversedDepthBuffer=renderer.state.buffers.depth.getReversed(),IS_INSTANCEDMESH=object.isInstancedMesh===!0,IS_BATCHEDMESH=object.isBatchedMesh===!0,HAS_MAP=!!material.map,HAS_MATCAP=!!material.matcap,HAS_ENVMAP=!!envMap,HAS_AOMAP=!!material.aoMap,HAS_LIGHTMAP=!!material.lightMap,HAS_BUMPMAP=!!material.bumpMap&&material.wireframe===!1,HAS_NORMALMAP=!!material.normalMap,HAS_DISPLACEMENTMAP=!!material.displacementMap,HAS_EMISSIVEMAP=!!material.emissiveMap,HAS_METALNESSMAP=!!material.metalnessMap,HAS_ROUGHNESSMAP=!!material.roughnessMap,HAS_ANISOTROPY=material.anisotropy>0,HAS_CLEARCOAT=material.clearcoat>0,HAS_DISPERSION=material.dispersion>0,HAS_RETROREFLECTION=material.retroreflectivity>0,HAS_IRIDESCENCE=material.iridescence>0,HAS_SHEEN=material.sheen>0,HAS_TRANSMISSION=material.transmission>0,HAS_ANISOTROPYMAP=HAS_ANISOTROPY&&!!material.anisotropyMap,HAS_CLEARCOATMAP=HAS_CLEARCOAT&&!!material.clearcoatMap,HAS_CLEARCOAT_NORMALMAP=HAS_CLEARCOAT&&!!material.clearcoatNormalMap,HAS_CLEARCOAT_ROUGHNESSMAP=HAS_CLEARCOAT&&!!material.clearcoatRoughnessMap,HAS_IRIDESCENCEMAP=HAS_IRIDESCENCE&&!!material.iridescenceMap,HAS_IRIDESCENCE_THICKNESSMAP=HAS_IRIDESCENCE&&!!material.iridescenceThicknessMap,HAS_SHEEN_COLORMAP=HAS_SHEEN&&!!material.sheenColorMap,HAS_SHEEN_ROUGHNESSMAP=HAS_SHEEN&&!!material.sheenRoughnessMap,HAS_SPECULARMAP=!!material.specularMap,HAS_SPECULAR_COLORMAP=!!material.specularColorMap,HAS_SPECULAR_INTENSITYMAP=!!material.specularIntensityMap,HAS_TRANSMISSIONMAP=HAS_TRANSMISSION&&!!material.transmissionMap,HAS_THICKNESSMAP=HAS_TRANSMISSION&&!!material.thicknessMap,HAS_GRADIENTMAP=!!material.gradientMap,HAS_ALPHAMAP=!!material.alphaMap,HAS_ALPHATEST=material.alphaTest>0,HAS_ALPHAHASH=!!material.alphaHash,HAS_EXTENSIONS=!!material.extensions,toneMapping=NoToneMapping;material.toneMapped&&(currentRenderTarget===null||currentRenderTarget.isXRRenderTarget===!0)&&(toneMapping=renderer.toneMapping);let parameters={shaderID,shaderType:material.type,shaderName:material.name,vertexShader,fragmentShader,defines:material.defines,customVertexShaderID,customFragmentShaderID,isRawShaderMaterial:material.isRawShaderMaterial===!0,glslVersion:material.glslVersion,precision,batching:IS_BATCHEDMESH,batchingColor:IS_BATCHEDMESH&&object._colorsTexture!==null,instancing:IS_INSTANCEDMESH,instancingColor:IS_INSTANCEDMESH&&object.instanceColor!==null,instancingMorph:IS_INSTANCEDMESH&&object.morphTexture!==null,outputColorSpace:currentRenderTarget===null?renderer.outputColorSpace:currentRenderTarget.isXRRenderTarget===!0?currentRenderTarget.texture.colorSpace:ColorManagement.workingColorSpace,alphaToCoverage:!!material.alphaToCoverage,map:HAS_MAP,matcap:HAS_MATCAP,envMap:HAS_ENVMAP,envMapMode:HAS_ENVMAP&&envMap.mapping,envMapCubeUVHeight,aoMap:HAS_AOMAP,lightMap:HAS_LIGHTMAP,bumpMap:HAS_BUMPMAP,normalMap:HAS_NORMALMAP,displacementMap:HAS_DISPLACEMENTMAP,emissiveMap:HAS_EMISSIVEMAP,normalMapObjectSpace:HAS_NORMALMAP&&material.normalMapType===ObjectSpaceNormalMap,normalMapTangentSpace:HAS_NORMALMAP&&material.normalMapType===TangentSpaceNormalMap,packedNormalMap:HAS_NORMALMAP&&material.normalMapType===TangentSpaceNormalMap&&isPackedRGFormat(material.normalMap.format),metalnessMap:HAS_METALNESSMAP,roughnessMap:HAS_ROUGHNESSMAP,anisotropy:HAS_ANISOTROPY,anisotropyMap:HAS_ANISOTROPYMAP,clearcoat:HAS_CLEARCOAT,clearcoatMap:HAS_CLEARCOATMAP,clearcoatNormalMap:HAS_CLEARCOAT_NORMALMAP,clearcoatRoughnessMap:HAS_CLEARCOAT_ROUGHNESSMAP,dispersion:HAS_DISPERSION,retroreflection:HAS_RETROREFLECTION,iridescence:HAS_IRIDESCENCE,iridescenceMap:HAS_IRIDESCENCEMAP,iridescenceThicknessMap:HAS_IRIDESCENCE_THICKNESSMAP,sheen:HAS_SHEEN,sheenColorMap:HAS_SHEEN_COLORMAP,sheenRoughnessMap:HAS_SHEEN_ROUGHNESSMAP,specularMap:HAS_SPECULARMAP,specularColorMap:HAS_SPECULAR_COLORMAP,specularIntensityMap:HAS_SPECULAR_INTENSITYMAP,transmission:HAS_TRANSMISSION,transmissionMap:HAS_TRANSMISSIONMAP,thicknessMap:HAS_THICKNESSMAP,gradientMap:HAS_GRADIENTMAP,opaque:material.transparent===!1&&material.blending===NormalBlending&&material.alphaToCoverage===!1,alphaMap:HAS_ALPHAMAP,alphaTest:HAS_ALPHATEST,alphaHash:HAS_ALPHAHASH,combine:material.combine,mapUv:HAS_MAP&&getChannel(material.map.channel),aoMapUv:HAS_AOMAP&&getChannel(material.aoMap.channel),lightMapUv:HAS_LIGHTMAP&&getChannel(material.lightMap.channel),bumpMapUv:HAS_BUMPMAP&&getChannel(material.bumpMap.channel),normalMapUv:HAS_NORMALMAP&&getChannel(material.normalMap.channel),displacementMapUv:HAS_DISPLACEMENTMAP&&getChannel(material.displacementMap.channel),emissiveMapUv:HAS_EMISSIVEMAP&&getChannel(material.emissiveMap.channel),metalnessMapUv:HAS_METALNESSMAP&&getChannel(material.metalnessMap.channel),roughnessMapUv:HAS_ROUGHNESSMAP&&getChannel(material.roughnessMap.channel),anisotropyMapUv:HAS_ANISOTROPYMAP&&getChannel(material.anisotropyMap.channel),clearcoatMapUv:HAS_CLEARCOATMAP&&getChannel(material.clearcoatMap.channel),clearcoatNormalMapUv:HAS_CLEARCOAT_NORMALMAP&&getChannel(material.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:HAS_CLEARCOAT_ROUGHNESSMAP&&getChannel(material.clearcoatRoughnessMap.channel),iridescenceMapUv:HAS_IRIDESCENCEMAP&&getChannel(material.iridescenceMap.channel),iridescenceThicknessMapUv:HAS_IRIDESCENCE_THICKNESSMAP&&getChannel(material.iridescenceThicknessMap.channel),sheenColorMapUv:HAS_SHEEN_COLORMAP&&getChannel(material.sheenColorMap.channel),sheenRoughnessMapUv:HAS_SHEEN_ROUGHNESSMAP&&getChannel(material.sheenRoughnessMap.channel),specularMapUv:HAS_SPECULARMAP&&getChannel(material.specularMap.channel),specularColorMapUv:HAS_SPECULAR_COLORMAP&&getChannel(material.specularColorMap.channel),specularIntensityMapUv:HAS_SPECULAR_INTENSITYMAP&&getChannel(material.specularIntensityMap.channel),transmissionMapUv:HAS_TRANSMISSIONMAP&&getChannel(material.transmissionMap.channel),thicknessMapUv:HAS_THICKNESSMAP&&getChannel(material.thicknessMap.channel),alphaMapUv:HAS_ALPHAMAP&&getChannel(material.alphaMap.channel),vertexTangents:!!geometry.attributes.tangent&&(HAS_NORMALMAP||HAS_ANISOTROPY),vertexNormals:!!geometry.attributes.normal,vertexColors:material.vertexColors,vertexAlphas:material.vertexColors===!0&&!!geometry.attributes.color&&geometry.attributes.color.itemSize===4,pointsUvs:object.isPoints===!0&&!!geometry.attributes.uv&&(HAS_MAP||HAS_ALPHAMAP),fog:!!fog,useFog:material.fog===!0,fogExp2:!!fog&&fog.isFogExp2,flatShading:material.wireframe===!1&&(material.flatShading===!0||geometry.attributes.normal===void 0&&HAS_NORMALMAP===!1&&(material.isMeshLambertMaterial||material.isMeshPhongMaterial||material.isMeshStandardMaterial||material.isMeshPhysicalMaterial)),sizeAttenuation:material.sizeAttenuation===!0,logarithmicDepthBuffer,reversedDepthBuffer,skinning:object.isSkinnedMesh===!0,hasPositionAttribute:geometry.attributes.position!==void 0,morphTargets:geometry.morphAttributes.position!==void 0,morphNormals:geometry.morphAttributes.normal!==void 0,morphColors:geometry.morphAttributes.color!==void 0,morphTargetsCount,morphTextureStride,numSunLights:lights.sun.length,numDirLights:lights.directional.length,numPointLights:lights.point.length,numSpotLights:lights.spot.length,numSpotLightMaps:lights.spotLightMap.length,numRectAreaLights:lights.rectArea.length,numHemiLights:lights.hemi.length,numSunLightShadows:lights.sunShadowMap.length,numDirLightShadows:lights.directionalShadowMap.length,numPointLightShadows:lights.pointShadowMap.length,numSpotLightShadows:lights.spotShadowMap.length,numSpotLightShadowsWithMaps:lights.numSpotLightShadowsWithMaps,numLightProbes:lights.numLightProbes,numLightProbeGrids:lightProbeGrids.length,numClippingPlanes:clipping.numPlanes,numClipIntersection:clipping.numIntersection,dithering:material.dithering,shadowMapEnabled:renderer.shadowMap.enabled&&shadows.length>0,shadowMapType:renderer.shadowMap.type,toneMapping,decodeVideoTexture:HAS_MAP&&material.map.isVideoTexture===!0&&ColorManagement.getTransfer(material.map.colorSpace)===SRGBTransfer,decodeVideoTextureEmissive:HAS_EMISSIVEMAP&&material.emissiveMap.isVideoTexture===!0&&ColorManagement.getTransfer(material.emissiveMap.colorSpace)===SRGBTransfer,premultipliedAlpha:material.premultipliedAlpha,doubleSided:material.side===DoubleSide,flipSided:material.side===BackSide,useDepthPacking:material.depthPacking>=0,depthPacking:material.depthPacking||0,index0AttributeName:material.index0AttributeName,extensionClipCullDistance:HAS_EXTENSIONS&&material.extensions.clipCullDistance===!0&&extensions.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(HAS_EXTENSIONS&&material.extensions.multiDraw===!0||IS_BATCHEDMESH)&&extensions.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:extensions.has("KHR_parallel_shader_compile"),customProgramCacheKey:material.customProgramCacheKey()};return parameters.vertexUv1s=_activeChannels.has(1),parameters.vertexUv2s=_activeChannels.has(2),parameters.vertexUv3s=_activeChannels.has(3),_activeChannels.clear(),parameters}function getProgramCacheKey(parameters){let array=[];if(parameters.shaderID?array.push(parameters.shaderID):(array.push(parameters.customVertexShaderID),array.push(parameters.customFragmentShaderID)),parameters.defines!==void 0)for(let name in parameters.defines)array.push(name),array.push(parameters.defines[name]);return parameters.isRawShaderMaterial===!1&&(getProgramCacheKeyParameters(array,parameters),getProgramCacheKeyBooleans(array,parameters),array.push(renderer.outputColorSpace)),array.push(parameters.customProgramCacheKey),array.join()}function getProgramCacheKeyParameters(array,parameters){array.push(parameters.precision),array.push(parameters.outputColorSpace),array.push(parameters.envMapMode),array.push(parameters.envMapCubeUVHeight),array.push(parameters.mapUv),array.push(parameters.alphaMapUv),array.push(parameters.lightMapUv),array.push(parameters.aoMapUv),array.push(parameters.bumpMapUv),array.push(parameters.normalMapUv),array.push(parameters.displacementMapUv),array.push(parameters.emissiveMapUv),array.push(parameters.metalnessMapUv),array.push(parameters.roughnessMapUv),array.push(parameters.anisotropyMapUv),array.push(parameters.clearcoatMapUv),array.push(parameters.clearcoatNormalMapUv),array.push(parameters.clearcoatRoughnessMapUv),array.push(parameters.iridescenceMapUv),array.push(parameters.iridescenceThicknessMapUv),array.push(parameters.sheenColorMapUv),array.push(parameters.sheenRoughnessMapUv),array.push(parameters.specularMapUv),array.push(parameters.specularColorMapUv),array.push(parameters.specularIntensityMapUv),array.push(parameters.transmissionMapUv),array.push(parameters.thicknessMapUv),array.push(parameters.combine),array.push(parameters.fogExp2),array.push(parameters.sizeAttenuation),array.push(parameters.morphTargetsCount),array.push(parameters.morphAttributeCount),array.push(parameters.numSunLights),array.push(parameters.numDirLights),array.push(parameters.numPointLights),array.push(parameters.numSpotLights),array.push(parameters.numSpotLightMaps),array.push(parameters.numHemiLights),array.push(parameters.numRectAreaLights),array.push(parameters.numSunLightShadows),array.push(parameters.numDirLightShadows),array.push(parameters.numPointLightShadows),array.push(parameters.numSpotLightShadows),array.push(parameters.numSpotLightShadowsWithMaps),array.push(parameters.numLightProbes),array.push(parameters.shadowMapType),array.push(parameters.toneMapping),array.push(parameters.numClippingPlanes),array.push(parameters.numClipIntersection),array.push(parameters.depthPacking)}function getProgramCacheKeyBooleans(array,parameters){_programLayers.disableAll(),parameters.instancing&&_programLayers.enable(0),parameters.instancingColor&&_programLayers.enable(1),parameters.instancingMorph&&_programLayers.enable(2),parameters.matcap&&_programLayers.enable(3),parameters.envMap&&_programLayers.enable(4),parameters.normalMapObjectSpace&&_programLayers.enable(5),parameters.normalMapTangentSpace&&_programLayers.enable(6),parameters.clearcoat&&_programLayers.enable(7),parameters.iridescence&&_programLayers.enable(8),parameters.alphaTest&&_programLayers.enable(9),parameters.vertexColors&&_programLayers.enable(10),parameters.vertexAlphas&&_programLayers.enable(11),parameters.vertexUv1s&&_programLayers.enable(12),parameters.vertexUv2s&&_programLayers.enable(13),parameters.vertexUv3s&&_programLayers.enable(14),parameters.vertexTangents&&_programLayers.enable(15),parameters.anisotropy&&_programLayers.enable(16),parameters.alphaHash&&_programLayers.enable(17),parameters.batching&&_programLayers.enable(18),parameters.dispersion&&_programLayers.enable(19),parameters.retroreflection&&_programLayers.enable(24),parameters.batchingColor&&_programLayers.enable(20),parameters.gradientMap&&_programLayers.enable(21),parameters.packedNormalMap&&_programLayers.enable(22),parameters.vertexNormals&&_programLayers.enable(23),array.push(_programLayers.mask),_programLayers.disableAll(),parameters.fog&&_programLayers.enable(0),parameters.useFog&&_programLayers.enable(1),parameters.flatShading&&_programLayers.enable(2),parameters.logarithmicDepthBuffer&&_programLayers.enable(3),parameters.reversedDepthBuffer&&_programLayers.enable(4),parameters.skinning&&_programLayers.enable(5),parameters.morphTargets&&_programLayers.enable(6),parameters.morphNormals&&_programLayers.enable(7),parameters.morphColors&&_programLayers.enable(8),parameters.premultipliedAlpha&&_programLayers.enable(9),parameters.shadowMapEnabled&&_programLayers.enable(10),parameters.doubleSided&&_programLayers.enable(11),parameters.flipSided&&_programLayers.enable(12),parameters.useDepthPacking&&_programLayers.enable(13),parameters.dithering&&_programLayers.enable(14),parameters.transmission&&_programLayers.enable(15),parameters.sheen&&_programLayers.enable(16),parameters.opaque&&_programLayers.enable(17),parameters.pointsUvs&&_programLayers.enable(18),parameters.decodeVideoTexture&&_programLayers.enable(19),parameters.decodeVideoTextureEmissive&&_programLayers.enable(20),parameters.alphaToCoverage&&_programLayers.enable(21),parameters.numLightProbeGrids>0&&_programLayers.enable(22),parameters.hasPositionAttribute&&_programLayers.enable(23),array.push(_programLayers.mask)}function getUniforms(material){let shaderID=shaderIDs[material.type],uniforms;if(shaderID){let shader=ShaderLib[shaderID];uniforms=UniformsUtils.clone(shader.uniforms)}else uniforms=material.uniforms;return uniforms}function acquireProgram(parameters,cacheKey){let program=programsMap.get(cacheKey);return program!==void 0?++program.usedTimes:(program=new WebGLProgram(renderer,cacheKey,parameters,bindingStates),programs.push(program),programsMap.set(cacheKey,program)),program}function releaseProgram(program){if(--program.usedTimes===0){let i=programs.indexOf(program);programs[i]=programs[programs.length-1],programs.pop(),programsMap.delete(program.cacheKey),program.destroy()}}function releaseShaderCache(material){_customShaders.remove(material)}function dispose(){_customShaders.dispose()}return{getParameters,getProgramCacheKey,getUniforms,acquireProgram,releaseProgram,releaseShaderCache,programs,dispose}}function WebGLProperties(){let properties=new WeakMap;function has(object){return properties.has(object)}function get(object){let map=properties.get(object);return map===void 0&&(map={},properties.set(object,map)),map}function remove(object){properties.delete(object)}function update(object,key,value){properties.get(object)[key]=value}function dispose(){properties=new WeakMap}return{has,get,remove,update,dispose}}function painterSortStable(a,b){return a.groupOrder!==b.groupOrder?a.groupOrder-b.groupOrder:a.renderOrder!==b.renderOrder?a.renderOrder-b.renderOrder:a.material.id!==b.material.id?a.material.id-b.material.id:a.materialVariant!==b.materialVariant?a.materialVariant-b.materialVariant:a.z!==b.z?a.z-b.z:a.id-b.id}function reversePainterSortStable(a,b){return a.groupOrder!==b.groupOrder?a.groupOrder-b.groupOrder:a.renderOrder!==b.renderOrder?a.renderOrder-b.renderOrder:a.z!==b.z?b.z-a.z:a.id-b.id}function WebGLRenderList(){let renderItems=[],renderItemsIndex=0,opaque=[],transmissive=[],transparent=[];function init(){renderItemsIndex=0,opaque.length=0,transmissive.length=0,transparent.length=0}function materialVariant(object){let variant=0;return object.isInstancedMesh&&(variant+=2),object.isSkinnedMesh&&(variant+=1),variant}function getNextRenderItem(object,geometry,material,groupOrder,z,group){let renderItem=renderItems[renderItemsIndex];return renderItem===void 0?(renderItem={id:object.id,object,geometry,material,materialVariant:materialVariant(object),groupOrder,renderOrder:object.renderOrder,z,group},renderItems[renderItemsIndex]=renderItem):(renderItem.id=object.id,renderItem.object=object,renderItem.geometry=geometry,renderItem.material=material,renderItem.materialVariant=materialVariant(object),renderItem.groupOrder=groupOrder,renderItem.renderOrder=object.renderOrder,renderItem.z=z,renderItem.group=group),renderItemsIndex++,renderItem}function push(object,geometry,material,groupOrder,z,group,camera){camera.reversedDepth===!0&&(z=-z);let renderItem=getNextRenderItem(object,geometry,material,groupOrder,z,group);material.transmission>0?transmissive.push(renderItem):material.transparent===!0?transparent.push(renderItem):opaque.push(renderItem)}function unshift(object,geometry,material,groupOrder,z,group){let renderItem=getNextRenderItem(object,geometry,material,groupOrder,z,group);material.transmission>0?transmissive.unshift(renderItem):material.transparent===!0?transparent.unshift(renderItem):opaque.unshift(renderItem)}function sort(customOpaqueSort,customTransparentSort){opaque.length>1&&opaque.sort(customOpaqueSort||painterSortStable),transmissive.length>1&&transmissive.sort(customTransparentSort||reversePainterSortStable),transparent.length>1&&transparent.sort(customTransparentSort||reversePainterSortStable)}function finish(){for(let i=renderItemsIndex,il=renderItems.length;i<il;i++){let renderItem=renderItems[i];if(renderItem.id===null)break;renderItem.id=null,renderItem.object=null,renderItem.geometry=null,renderItem.material=null,renderItem.group=null}}return{opaque,transmissive,transparent,init,push,unshift,finish,sort}}function WebGLRenderLists(){let lists=new WeakMap;function get(scene,renderCallDepth){let listArray=lists.get(scene),list;return listArray===void 0?(list=new WebGLRenderList,lists.set(scene,[list])):renderCallDepth>=listArray.length?(list=new WebGLRenderList,listArray.push(list)):list=listArray[renderCallDepth],list}function dispose(){lists=new WeakMap}return{get,dispose}}function UniformsCache(){let lights={};return{get:function(light){if(lights[light.id]!==void 0)return lights[light.id];let uniforms;switch(light.type){case"SunLight":case"DirectionalLight":uniforms={direction:new Vector3,color:new Color};break;case"SpotLight":uniforms={position:new Vector3,direction:new Vector3,color:new Color,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":uniforms={position:new Vector3,color:new Color,distance:0,decay:0};break;case"HemisphereLight":uniforms={direction:new Vector3,skyColor:new Color,groundColor:new Color};break;case"RectAreaLight":uniforms={color:new Color,position:new Vector3,halfWidth:new Vector3,halfHeight:new Vector3};break}return lights[light.id]=uniforms,uniforms}}}function ShadowUniformsCache(){let lights={};return{get:function(light){if(lights[light.id]!==void 0)return lights[light.id];let uniforms;switch(light.type){case"SunLight":case"DirectionalLight":uniforms={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Vector2};break;case"SpotLight":uniforms={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Vector2};break;case"PointLight":uniforms={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new Vector2,shadowCameraNear:1,shadowCameraFar:1e3};break}return lights[light.id]=uniforms,uniforms}}}var nextVersion=0;function shadowCastingAndTexturingLightsFirst(lightA,lightB){return(lightB.castShadow?2:0)-(lightA.castShadow?2:0)+(lightB.map?1:0)-(lightA.map?1:0)}function WebGLLights(extensions){let cache=new UniformsCache,shadowCache=ShadowUniformsCache(),state={version:0,hash:{sunLength:-1,directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numSunShadows:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],sun:[],sunShadow:[],sunShadowMap:[],sunShadowMatrix:[],sunShadowCascade:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let i=0;i<9;i++)state.probe.push(new Vector3);let vector3=new Vector3,matrix4=new Matrix4,matrix42=new Matrix4;function setup(lights){let r=0,g=0,b=0;for(let i=0;i<9;i++)state.probe[i].set(0,0,0);let sunLength=0,numSunShadows=0,numSunShadowCascades=0,directionalLength=0,pointLength=0,spotLength=0,rectAreaLength=0,hemiLength=0,numDirectionalShadows=0,numPointShadows=0,numSpotShadows=0,numSpotMaps=0,numSpotShadowsWithMaps=0,numLightProbes=0;lights.sort(shadowCastingAndTexturingLightsFirst);for(let i=0,l=lights.length;i<l;i++){let light=lights[i],color=light.color,intensity=light.intensity,distance=light.distance,shadowMap=null;if(light.shadow&&light.shadow.map&&(light.shadow.map.texture.format===RGFormat?shadowMap=light.shadow.map.texture:shadowMap=light.shadow.map.depthTexture||light.shadow.map.texture),light.isAmbientLight)r+=color.r*intensity,g+=color.g*intensity,b+=color.b*intensity;else if(light.isLightProbe){for(let j=0;j<9;j++)state.probe[j].addScaledVector(light.sh.coefficients[j],intensity);numLightProbes++}else if(light.isSunLight){let uniforms=cache.get(light);if(uniforms.color.copy(light.color).multiplyScalar(light.intensity),light.castShadow){let shadow=light.shadow,shadowUniforms=shadowCache.get(light);shadowUniforms.shadowIntensity=shadow.intensity,shadowUniforms.shadowBias=shadow.bias,shadowUniforms.shadowNormalBias=shadow.normalBias,shadowUniforms.shadowRadius=shadow.radius,shadowUniforms.shadowMapSize.copy(shadow.mapSize).multiply(shadow.getFrameExtents()),state.sunShadow[numSunShadows]=shadowUniforms,state.sunShadowMap[numSunShadows]=shadowMap;let cascadeCount=shadow.getViewportCount();for(let j=0;j<cascadeCount;j++)state.sunShadowMatrix[numSunShadowCascades+j]=shadow.getMatrix(j),state.sunShadowCascade[numSunShadowCascades+j]=shadow._cascadeData[j];numSunShadowCascades+=cascadeCount,numSunShadows++}state.sun[sunLength]=uniforms,sunLength++}else if(light.isDirectionalLight){let uniforms=cache.get(light);if(uniforms.color.copy(light.color).multiplyScalar(light.intensity),light.castShadow){let shadow=light.shadow,shadowUniforms=shadowCache.get(light);shadowUniforms.shadowIntensity=shadow.intensity,shadowUniforms.shadowBias=shadow.bias,shadowUniforms.shadowNormalBias=shadow.normalBias,shadowUniforms.shadowRadius=shadow.radius,shadowUniforms.shadowMapSize=shadow.mapSize,state.directionalShadow[directionalLength]=shadowUniforms,state.directionalShadowMap[directionalLength]=shadowMap,state.directionalShadowMatrix[directionalLength]=light.shadow.matrix,numDirectionalShadows++}state.directional[directionalLength]=uniforms,directionalLength++}else if(light.isSpotLight){let uniforms=cache.get(light);uniforms.position.setFromMatrixPosition(light.matrixWorld),uniforms.color.copy(color).multiplyScalar(intensity),uniforms.distance=distance,uniforms.coneCos=Math.cos(light.angle),uniforms.penumbraCos=Math.cos(light.angle*(1-light.penumbra)),uniforms.decay=light.decay,state.spot[spotLength]=uniforms;let shadow=light.shadow;if(light.map&&(state.spotLightMap[numSpotMaps]=light.map,numSpotMaps++,shadow.updateMatrices(light),light.castShadow&&numSpotShadowsWithMaps++),state.spotLightMatrix[spotLength]=shadow.matrix,light.castShadow){let shadowUniforms=shadowCache.get(light);shadowUniforms.shadowIntensity=shadow.intensity,shadowUniforms.shadowBias=shadow.bias,shadowUniforms.shadowNormalBias=shadow.normalBias,shadowUniforms.shadowRadius=shadow.radius,shadowUniforms.shadowMapSize=shadow.mapSize,state.spotShadow[spotLength]=shadowUniforms,state.spotShadowMap[spotLength]=shadowMap,numSpotShadows++}spotLength++}else if(light.isRectAreaLight){let uniforms=cache.get(light);uniforms.color.copy(color).multiplyScalar(intensity),uniforms.halfWidth.set(light.width*.5,0,0),uniforms.halfHeight.set(0,light.height*.5,0),state.rectArea[rectAreaLength]=uniforms,rectAreaLength++}else if(light.isPointLight){let uniforms=cache.get(light);if(uniforms.color.copy(light.color).multiplyScalar(light.intensity),uniforms.distance=light.distance,uniforms.decay=light.decay,light.castShadow){let shadow=light.shadow,shadowUniforms=shadowCache.get(light);shadowUniforms.shadowIntensity=shadow.intensity,shadowUniforms.shadowBias=shadow.bias,shadowUniforms.shadowNormalBias=shadow.normalBias,shadowUniforms.shadowRadius=shadow.radius,shadowUniforms.shadowMapSize=shadow.mapSize,shadowUniforms.shadowCameraNear=shadow.camera.near,shadowUniforms.shadowCameraFar=shadow.camera.far,state.pointShadow[pointLength]=shadowUniforms,state.pointShadowMap[pointLength]=shadowMap,state.pointShadowMatrix[pointLength]=light.shadow.matrix,numPointShadows++}state.point[pointLength]=uniforms,pointLength++}else if(light.isHemisphereLight){let uniforms=cache.get(light);uniforms.skyColor.copy(light.color).multiplyScalar(intensity),uniforms.groundColor.copy(light.groundColor).multiplyScalar(intensity),state.hemi[hemiLength]=uniforms,hemiLength++}}rectAreaLength>0&&(extensions.has("OES_texture_float_linear")===!0?(state.rectAreaLTC1=UniformsLib.LTC_FLOAT_1,state.rectAreaLTC2=UniformsLib.LTC_FLOAT_2):(state.rectAreaLTC1=UniformsLib.LTC_HALF_1,state.rectAreaLTC2=UniformsLib.LTC_HALF_2)),state.ambient[0]=r,state.ambient[1]=g,state.ambient[2]=b;let hash2=state.hash;(hash2.sunLength!==sunLength||hash2.directionalLength!==directionalLength||hash2.pointLength!==pointLength||hash2.spotLength!==spotLength||hash2.rectAreaLength!==rectAreaLength||hash2.hemiLength!==hemiLength||hash2.numSunShadows!==numSunShadows||hash2.numDirectionalShadows!==numDirectionalShadows||hash2.numPointShadows!==numPointShadows||hash2.numSpotShadows!==numSpotShadows||hash2.numSpotMaps!==numSpotMaps||hash2.numLightProbes!==numLightProbes)&&(state.sun.length=sunLength,state.directional.length=directionalLength,state.spot.length=spotLength,state.rectArea.length=rectAreaLength,state.point.length=pointLength,state.hemi.length=hemiLength,state.sunShadow.length=numSunShadows,state.sunShadowMap.length=numSunShadows,state.sunShadowMatrix.length=numSunShadowCascades,state.sunShadowCascade.length=numSunShadowCascades,state.directionalShadow.length=numDirectionalShadows,state.directionalShadowMap.length=numDirectionalShadows,state.directionalShadowMatrix.length=numDirectionalShadows,state.pointShadow.length=numPointShadows,state.pointShadowMap.length=numPointShadows,state.pointShadowMatrix.length=numPointShadows,state.spotShadow.length=numSpotShadows,state.spotShadowMap.length=numSpotShadows,state.spotLightMatrix.length=numSpotShadows+numSpotMaps-numSpotShadowsWithMaps,state.spotLightMap.length=numSpotMaps,state.numSpotLightShadowsWithMaps=numSpotShadowsWithMaps,state.numLightProbes=numLightProbes,hash2.sunLength=sunLength,hash2.directionalLength=directionalLength,hash2.pointLength=pointLength,hash2.spotLength=spotLength,hash2.rectAreaLength=rectAreaLength,hash2.hemiLength=hemiLength,hash2.numSunShadows=numSunShadows,hash2.numDirectionalShadows=numDirectionalShadows,hash2.numPointShadows=numPointShadows,hash2.numSpotShadows=numSpotShadows,hash2.numSpotMaps=numSpotMaps,hash2.numLightProbes=numLightProbes,state.version=nextVersion++)}function setupView(lights,camera){let sunLength=0,directionalLength=0,pointLength=0,spotLength=0,rectAreaLength=0,hemiLength=0,viewMatrix=camera.matrixWorldInverse;for(let i=0,l=lights.length;i<l;i++){let light=lights[i];if(light.isSunLight){let uniforms=state.sun[sunLength];uniforms.direction.setFromMatrixPosition(light.matrixWorld),uniforms.direction.transformDirection(viewMatrix),sunLength++}else if(light.isDirectionalLight){let uniforms=state.directional[directionalLength];uniforms.direction.setFromMatrixPosition(light.matrixWorld),vector3.setFromMatrixPosition(light.target.matrixWorld),uniforms.direction.sub(vector3),uniforms.direction.transformDirection(viewMatrix),directionalLength++}else if(light.isSpotLight){let uniforms=state.spot[spotLength];uniforms.position.setFromMatrixPosition(light.matrixWorld),uniforms.position.applyMatrix4(viewMatrix),uniforms.direction.setFromMatrixPosition(light.matrixWorld),vector3.setFromMatrixPosition(light.target.matrixWorld),uniforms.direction.sub(vector3),uniforms.direction.transformDirection(viewMatrix),spotLength++}else if(light.isRectAreaLight){let uniforms=state.rectArea[rectAreaLength];uniforms.position.setFromMatrixPosition(light.matrixWorld),uniforms.position.applyMatrix4(viewMatrix),matrix42.identity(),matrix4.copy(light.matrixWorld),matrix4.premultiply(viewMatrix),matrix42.extractRotation(matrix4),uniforms.halfWidth.set(light.width*.5,0,0),uniforms.halfHeight.set(0,light.height*.5,0),uniforms.halfWidth.applyMatrix4(matrix42),uniforms.halfHeight.applyMatrix4(matrix42),rectAreaLength++}else if(light.isPointLight){let uniforms=state.point[pointLength];uniforms.position.setFromMatrixPosition(light.matrixWorld),uniforms.position.applyMatrix4(viewMatrix),pointLength++}else if(light.isHemisphereLight){let uniforms=state.hemi[hemiLength];uniforms.direction.setFromMatrixPosition(light.matrixWorld),uniforms.direction.transformDirection(viewMatrix),hemiLength++}}}return{setup,setupView,state}}function WebGLRenderState(extensions){let lights=new WebGLLights(extensions),lightsArray=[],shadowsArray=[],lightProbeGridArray=[];function init(camera){state.camera=camera,lightsArray.length=0,shadowsArray.length=0,lightProbeGridArray.length=0}function pushLight(light){lightsArray.push(light)}function pushShadow(shadowLight){shadowsArray.push(shadowLight)}function pushLightProbeGrid(volume){lightProbeGridArray.push(volume)}function setupLights(){lights.setup(lightsArray)}function setupLightsView(camera){lights.setupView(lightsArray,camera)}let state={lightsArray,shadowsArray,lightProbeGridArray,camera:null,lights,transmissionRenderTarget:{},textureUnits:0};return{init,state,setupLights,setupLightsView,pushLight,pushShadow,pushLightProbeGrid}}function WebGLRenderStates(extensions){let renderStates=new WeakMap;function get(scene,renderCallDepth=0){let renderStateArray=renderStates.get(scene),renderState;return renderStateArray===void 0?(renderState=new WebGLRenderState(extensions),renderStates.set(scene,[renderState])):renderCallDepth>=renderStateArray.length?(renderState=new WebGLRenderState(extensions),renderStateArray.push(renderState)):renderState=renderStateArray[renderCallDepth],renderState}function dispose(){renderStates=new WeakMap}return{get,dispose}}var vertex18=`
void main() {

	gl_Position = vec4( position, 1.0 );

}
`,fragment18=`
uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;

void main() {

	const float samples = float( VSM_SAMPLES );

	float mean = 0.0;
	float squared_mean = 0.0;

	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {

		float uvOffset = uvStart + i * uvStride;

		#ifdef HORIZONTAL_PASS

			vec2 distribution = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ).rg;
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;

		#else

			float depth = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ).r;
			mean += depth;
			squared_mean += depth * depth;

		#endif

	}

	mean = mean / samples;
	squared_mean = squared_mean / samples;

	float std_dev = sqrt( max( 0.0, squared_mean - mean * mean ) );

	gl_FragColor = vec4( mean, std_dev, 0.0, 1.0 );

}
`;var _cubeDirections=[new Vector3(1,0,0),new Vector3(-1,0,0),new Vector3(0,1,0),new Vector3(0,-1,0),new Vector3(0,0,1),new Vector3(0,0,-1)],_cubeUps=[new Vector3(0,-1,0),new Vector3(0,-1,0),new Vector3(0,0,1),new Vector3(0,0,-1),new Vector3(0,-1,0),new Vector3(0,-1,0)],_projScreenMatrix2=new Matrix4,_lightPositionWorld2=new Vector3,_lookTarget2=new Vector3;function WebGLShadowMap(renderer,objects,capabilities){let _frustum=new Frustum,_shadowMapSize=new Vector2,_viewportSize=new Vector2,_viewport=new Vector4,_depthMaterial=new MeshDepthMaterial,_distanceMaterial=new MeshDistanceMaterial,_materialCache={},_maxTextureSize=capabilities.maxTextureSize,shadowSide={[FrontSide]:BackSide,[BackSide]:FrontSide,[DoubleSide]:DoubleSide},shadowMaterialVertical=new ShaderMaterial({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new Vector2},radius:{value:4}},vertexShader:vertex18,fragmentShader:fragment18}),shadowMaterialHorizontal=shadowMaterialVertical.clone();shadowMaterialHorizontal.defines.HORIZONTAL_PASS=1;let fullScreenTri=new BufferGeometry;fullScreenTri.setAttribute("position",new BufferAttribute(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));let fullScreenMesh=new Mesh(fullScreenTri,shadowMaterialVertical),scope=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=PCFShadowMap;let _previousType=this.type;this.render=function(lights,scene,camera){if(scope.enabled===!1||scope.autoUpdate===!1&&scope.needsUpdate===!1||lights.length===0)return;this.type===PCFSoftShadowMap&&(warn("WebGLShadowMap: PCFSoftShadowMap has been removed. Using PCFShadowMap instead."),this.type=PCFShadowMap);let currentRenderTarget=renderer.getRenderTarget(),activeCubeFace=renderer.getActiveCubeFace(),activeMipmapLevel=renderer.getActiveMipmapLevel(),_state=renderer.state;_state.setBlending(NoBlending),_state.buffers.depth.getReversed()===!0?_state.buffers.color.setClear(0,0,0,0):_state.buffers.color.setClear(1,1,1,1),_state.buffers.depth.setTest(!0),_state.setScissorTest(!1);let typeChanged=_previousType!==this.type;typeChanged&&scene.traverse(function(object){object.material&&(Array.isArray(object.material)?object.material.forEach(mat=>mat.needsUpdate=!0):object.material.needsUpdate=!0)});for(let i=0,il=lights.length;i<il;i++){let light=lights[i],shadow=light.shadow;if(shadow===void 0){warn("WebGLShadowMap:",light,"has no shadow.");continue}if(shadow.autoUpdate===!1&&shadow.needsUpdate===!1)continue;_shadowMapSize.copy(shadow.mapSize);let shadowFrameExtents=shadow.getFrameExtents();_shadowMapSize.multiply(shadowFrameExtents),_viewportSize.copy(shadow.mapSize),(_shadowMapSize.x>_maxTextureSize||_shadowMapSize.y>_maxTextureSize)&&(_shadowMapSize.x>_maxTextureSize&&(_viewportSize.x=Math.floor(_maxTextureSize/shadowFrameExtents.x),_shadowMapSize.x=_viewportSize.x*shadowFrameExtents.x,shadow.mapSize.x=_viewportSize.x),_shadowMapSize.y>_maxTextureSize&&(_viewportSize.y=Math.floor(_maxTextureSize/shadowFrameExtents.y),_shadowMapSize.y=_viewportSize.y*shadowFrameExtents.y,shadow.mapSize.y=_viewportSize.y));let reversedDepthBuffer=renderer.state.buffers.depth.getReversed();if(shadow.camera._reversedDepth=reversedDepthBuffer,shadow.map===null||typeChanged===!0){if(shadow.map!==null&&(shadow.map.depthTexture!==null&&(shadow.map.depthTexture.dispose(),shadow.map.depthTexture=null),shadow.map.dispose()),this.type===VSMShadowMap){if(light.isPointLight){warn("WebGLShadowMap: VSM shadow maps are not supported for PointLights. Use PCF or BasicShadowMap instead.");continue}shadow.map=new WebGLRenderTarget(_shadowMapSize.x,_shadowMapSize.y,{format:RGFormat,type:HalfFloatType,minFilter:LinearFilter,magFilter:LinearFilter,generateMipmaps:!1}),shadow.map.texture.name=light.name+".shadowMap",shadow.map.depthTexture=new DepthTexture(_shadowMapSize.x,_shadowMapSize.y,FloatType),shadow.map.depthTexture.name=light.name+".shadowMapDepth",shadow.map.depthTexture.format=DepthFormat,shadow.map.depthTexture.compareFunction=null,shadow.map.depthTexture.minFilter=NearestFilter,shadow.map.depthTexture.magFilter=NearestFilter}else light.isPointLight?(shadow.map=new WebGLCubeRenderTarget(_shadowMapSize.x),shadow.map.depthTexture=new CubeDepthTexture(_shadowMapSize.x,UnsignedIntType)):(shadow.map=new WebGLRenderTarget(_shadowMapSize.x,_shadowMapSize.y),shadow.map.depthTexture=new DepthTexture(_shadowMapSize.x,_shadowMapSize.y,UnsignedIntType)),shadow.map.depthTexture.name=light.name+".shadowMap",shadow.map.depthTexture.format=DepthFormat,this.type===PCFShadowMap?(shadow.map.depthTexture.compareFunction=reversedDepthBuffer?GreaterEqualCompare:LessEqualCompare,shadow.map.depthTexture.minFilter=LinearFilter,shadow.map.depthTexture.magFilter=LinearFilter):(shadow.map.depthTexture.compareFunction=null,shadow.map.depthTexture.minFilter=NearestFilter,shadow.map.depthTexture.magFilter=NearestFilter);shadow.camera.updateProjectionMatrix()}shadow.map.isWebGLCubeRenderTarget!==!0&&(shadow.map.width!==_shadowMapSize.x||shadow.map.height!==_shadowMapSize.y)&&shadow.map.setSize(_shadowMapSize.x,_shadowMapSize.y);let faceCount=shadow.map.isWebGLCubeRenderTarget?6:shadow.getViewportCount();light.isPointLight!==!0&&shadow.updateMatrices(light,camera);for(let face=0;face<faceCount;face++){let shadowCamera=shadow.getCamera(face);if(light.isPointLight){let camera2=shadow.camera,shadowMatrix=shadow.matrix,far=light.distance||camera2.far;far!==camera2.far&&(camera2.far=far,camera2.updateProjectionMatrix()),_lightPositionWorld2.setFromMatrixPosition(light.matrixWorld),camera2.position.copy(_lightPositionWorld2),_lookTarget2.copy(camera2.position),_lookTarget2.add(_cubeDirections[face]),camera2.up.copy(_cubeUps[face]),camera2.lookAt(_lookTarget2),camera2.updateMatrixWorld(),shadowMatrix.makeTranslation(-_lightPositionWorld2.x,-_lightPositionWorld2.y,-_lightPositionWorld2.z),_projScreenMatrix2.multiplyMatrices(camera2.projectionMatrix,camera2.matrixWorldInverse),shadow._frustum.setFromProjectionMatrix(_projScreenMatrix2,camera2.coordinateSystem,camera2.reversedDepth)}if(shadow.map.isWebGLCubeRenderTarget)renderer.setRenderTarget(shadow.map,face),renderer.clear();else{face===0&&(renderer.setRenderTarget(shadow.map),renderer.clear());let viewport=shadow.getViewport(face);_viewport.set(_viewportSize.x*viewport.x,_viewportSize.y*viewport.y,_viewportSize.x*viewport.z,_viewportSize.y*viewport.w),_state.viewport(_viewport)}_frustum=shadow.getFrustum(face),renderObject(scene,camera,shadowCamera,light,this.type)}shadow.isPointLightShadow!==!0&&this.type===VSMShadowMap&&VSMPass(shadow,camera),shadow.needsUpdate=!1}_previousType=this.type,scope.needsUpdate=!1,renderer.setRenderTarget(currentRenderTarget,activeCubeFace,activeMipmapLevel)};function VSMPass(shadow,camera){let geometry=objects.update(fullScreenMesh);shadowMaterialVertical.defines.VSM_SAMPLES!==shadow.blurSamples&&(shadowMaterialVertical.defines.VSM_SAMPLES=shadow.blurSamples,shadowMaterialHorizontal.defines.VSM_SAMPLES=shadow.blurSamples,shadowMaterialVertical.needsUpdate=!0,shadowMaterialHorizontal.needsUpdate=!0),shadow.mapPass===null?shadow.mapPass=new WebGLRenderTarget(_shadowMapSize.x,_shadowMapSize.y,{format:RGFormat,type:HalfFloatType}):(shadow.mapPass.width!==shadow.map.width||shadow.mapPass.height!==shadow.map.height)&&shadow.mapPass.setSize(shadow.map.width,shadow.map.height),shadowMaterialVertical.uniforms.shadow_pass.value=shadow.map.depthTexture,shadowMaterialVertical.uniforms.resolution.value.set(shadow.map.width,shadow.map.height),shadowMaterialVertical.uniforms.radius.value=shadow.radius,renderer.setRenderTarget(shadow.mapPass),renderer.clear(),renderer.renderBufferDirect(camera,null,geometry,shadowMaterialVertical,fullScreenMesh,null),shadowMaterialHorizontal.uniforms.shadow_pass.value=shadow.mapPass.texture,shadowMaterialHorizontal.uniforms.resolution.value.set(shadow.map.width,shadow.map.height),shadowMaterialHorizontal.uniforms.radius.value=shadow.radius,renderer.setRenderTarget(shadow.map),renderer.clear(),renderer.renderBufferDirect(camera,null,geometry,shadowMaterialHorizontal,fullScreenMesh,null)}function getDepthMaterial(object,material,light,type){let result=null,customMaterial=light.isPointLight===!0?object.customDistanceMaterial:object.customDepthMaterial;if(customMaterial!==void 0)result=customMaterial;else if(result=light.isPointLight===!0?_distanceMaterial:_depthMaterial,renderer.localClippingEnabled&&material.clipShadows===!0&&Array.isArray(material.clippingPlanes)&&material.clippingPlanes.length!==0||material.displacementMap&&material.displacementScale!==0||material.alphaMap&&material.alphaTest>0||material.map&&material.alphaTest>0||material.alphaToCoverage===!0){let keyA=result.uuid,keyB=material.uuid,materialsForVariant=_materialCache[keyA];materialsForVariant===void 0&&(materialsForVariant={},_materialCache[keyA]=materialsForVariant);let cachedMaterial=materialsForVariant[keyB];cachedMaterial===void 0&&(cachedMaterial=result.clone(),materialsForVariant[keyB]=cachedMaterial,material.addEventListener("dispose",onMaterialDispose)),result=cachedMaterial}if(result.visible=material.visible,result.wireframe=material.wireframe,type===VSMShadowMap?result.side=material.shadowSide!==null?material.shadowSide:material.side:result.side=material.shadowSide!==null?material.shadowSide:shadowSide[material.side],result.alphaMap=material.alphaMap,result.alphaTest=material.alphaToCoverage===!0?.5:material.alphaTest,result.map=material.map,result.clipShadows=material.clipShadows,result.clippingPlanes=material.clippingPlanes,result.clipIntersection=material.clipIntersection,result.displacementMap=material.displacementMap,result.displacementScale=material.displacementScale,result.displacementBias=material.displacementBias,result.wireframeLinewidth=material.wireframeLinewidth,result.linewidth=material.linewidth,light.isPointLight===!0&&result.isMeshDistanceMaterial===!0){let materialProperties=renderer.properties.get(result);materialProperties.light=light}return result}function renderObject(object,camera,shadowCamera,light,type){if(object.visible===!1)return;if(object.layers.test(camera.layers)&&(object.isMesh||object.isLine||object.isPoints)&&(object.castShadow||object.receiveShadow&&type===VSMShadowMap)&&(!object.frustumCulled||object.intersectsFrustum(_frustum))){object.modelViewMatrix.multiplyMatrices(shadowCamera.matrixWorldInverse,object.matrixWorld);let geometry=objects.update(object),material=object.material;if(Array.isArray(material)){let groups=geometry.groups;for(let k=0,kl=groups.length;k<kl;k++){let group=groups[k],groupMaterial=material[group.materialIndex];if(groupMaterial&&groupMaterial.visible){let depthMaterial=getDepthMaterial(object,groupMaterial,light,type);object.onBeforeShadow(renderer,object,camera,shadowCamera,geometry,depthMaterial,group),renderer.renderBufferDirect(shadowCamera,null,geometry,depthMaterial,object,group),object.onAfterShadow(renderer,object,camera,shadowCamera,geometry,depthMaterial,group)}}}else if(material.visible){let depthMaterial=getDepthMaterial(object,material,light,type);object.onBeforeShadow(renderer,object,camera,shadowCamera,geometry,depthMaterial,null),renderer.renderBufferDirect(shadowCamera,null,geometry,depthMaterial,object,null),object.onAfterShadow(renderer,object,camera,shadowCamera,geometry,depthMaterial,null)}}let children=object.children;for(let i=0,l=children.length;i<l;i++)renderObject(children[i],camera,shadowCamera,light,type)}function onMaterialDispose(event){event.target.removeEventListener("dispose",onMaterialDispose);for(let id in _materialCache){let cache=_materialCache[id],uuid=event.target.uuid;uuid in cache&&(cache[uuid].dispose(),delete cache[uuid])}}}function WebGLState(gl,extensions){function ColorBuffer(){let locked=!1,color=new Vector4,currentColorMask=null,currentColorClear=new Vector4(0,0,0,0);return{setMask:function(colorMask){currentColorMask!==colorMask&&!locked&&(gl.colorMask(colorMask,colorMask,colorMask,colorMask),currentColorMask=colorMask)},setLocked:function(lock){locked=lock},setClear:function(r,g,b,a,premultipliedAlpha){premultipliedAlpha===!0&&(r*=a,g*=a,b*=a),color.set(r,g,b,a),currentColorClear.equals(color)===!1&&(gl.clearColor(r,g,b,a),currentColorClear.copy(color))},reset:function(){locked=!1,currentColorMask=null,currentColorClear.set(-1,0,0,0)}}}function DepthBuffer(){let locked=!1,currentReversed=!1,currentDepthMask=null,currentDepthFunc=null,currentDepthClear=null;return{setReversed:function(reversed){if(currentReversed!==reversed){let ext=extensions.get("EXT_clip_control");reversed?ext.clipControlEXT(ext.LOWER_LEFT_EXT,ext.ZERO_TO_ONE_EXT):ext.clipControlEXT(ext.LOWER_LEFT_EXT,ext.NEGATIVE_ONE_TO_ONE_EXT),currentReversed=reversed;let oldDepth=currentDepthClear;currentDepthClear=null,this.setClear(oldDepth)}},getReversed:function(){return currentReversed},setTest:function(depthTest){depthTest?enable(gl.DEPTH_TEST):disable(gl.DEPTH_TEST)},setMask:function(depthMask){currentDepthMask!==depthMask&&!locked&&(gl.depthMask(depthMask),currentDepthMask=depthMask)},setFunc:function(depthFunc){if(currentReversed&&(depthFunc=ReversedDepthFuncs[depthFunc]),currentDepthFunc!==depthFunc){switch(depthFunc){case NeverDepth:gl.depthFunc(gl.NEVER);break;case AlwaysDepth:gl.depthFunc(gl.ALWAYS);break;case LessDepth:gl.depthFunc(gl.LESS);break;case LessEqualDepth:gl.depthFunc(gl.LEQUAL);break;case EqualDepth:gl.depthFunc(gl.EQUAL);break;case GreaterEqualDepth:gl.depthFunc(gl.GEQUAL);break;case GreaterDepth:gl.depthFunc(gl.GREATER);break;case NotEqualDepth:gl.depthFunc(gl.NOTEQUAL);break;default:gl.depthFunc(gl.LEQUAL)}currentDepthFunc=depthFunc}},setLocked:function(lock){locked=lock},setClear:function(depth){currentDepthClear!==depth&&(currentDepthClear=depth,currentReversed&&(depth=1-depth),gl.clearDepth(depth))},reset:function(){locked=!1,currentDepthMask=null,currentDepthFunc=null,currentDepthClear=null,currentReversed=!1}}}function StencilBuffer(){let locked=!1,currentStencilMask=null,currentStencilFunc=null,currentStencilRef=null,currentStencilFuncMask=null,currentStencilFail=null,currentStencilZFail=null,currentStencilZPass=null,currentStencilClear=null;return{setTest:function(stencilTest){locked||(stencilTest?enable(gl.STENCIL_TEST):disable(gl.STENCIL_TEST))},setMask:function(stencilMask){currentStencilMask!==stencilMask&&!locked&&(gl.stencilMask(stencilMask),currentStencilMask=stencilMask)},setFunc:function(stencilFunc,stencilRef,stencilMask){(currentStencilFunc!==stencilFunc||currentStencilRef!==stencilRef||currentStencilFuncMask!==stencilMask)&&(gl.stencilFunc(stencilFunc,stencilRef,stencilMask),currentStencilFunc=stencilFunc,currentStencilRef=stencilRef,currentStencilFuncMask=stencilMask)},setOp:function(stencilFail,stencilZFail,stencilZPass){(currentStencilFail!==stencilFail||currentStencilZFail!==stencilZFail||currentStencilZPass!==stencilZPass)&&(gl.stencilOp(stencilFail,stencilZFail,stencilZPass),currentStencilFail=stencilFail,currentStencilZFail=stencilZFail,currentStencilZPass=stencilZPass)},setLocked:function(lock){locked=lock},setClear:function(stencil){currentStencilClear!==stencil&&(gl.clearStencil(stencil),currentStencilClear=stencil)},reset:function(){locked=!1,currentStencilMask=null,currentStencilFunc=null,currentStencilRef=null,currentStencilFuncMask=null,currentStencilFail=null,currentStencilZFail=null,currentStencilZPass=null,currentStencilClear=null}}}let colorBuffer=new ColorBuffer,depthBuffer=new DepthBuffer,stencilBuffer=new StencilBuffer,uboBindings=new WeakMap,uboProgramMap=new WeakMap,enabledCapabilities={},parameters={},currentBoundFramebuffers={},currentDrawbuffers=new WeakMap,defaultDrawbuffers=[],currentProgram=null,currentBlendingEnabled=!1,currentBlending=null,currentBlendEquation=null,currentBlendSrc=null,currentBlendDst=null,currentBlendEquationAlpha=null,currentBlendSrcAlpha=null,currentBlendDstAlpha=null,currentBlendColor=new Color(0,0,0),currentBlendAlpha=0,currentPremultipledAlpha=!1,currentFlipSided=null,currentCullFace=null,currentLineWidth=null,currentPolygonOffsetFactor=null,currentPolygonOffsetUnits=null,maxTextures=gl.getParameter(gl.MAX_COMBINED_TEXTURE_IMAGE_UNITS),lineWidthAvailable=!1,version=0,glVersion=gl.getParameter(gl.VERSION);glVersion.indexOf("WebGL")!==-1?(version=parseFloat(/^WebGL (\d)/.exec(glVersion)[1]),lineWidthAvailable=version>=1):glVersion.indexOf("OpenGL ES")!==-1&&(version=parseFloat(/^OpenGL ES (\d)/.exec(glVersion)[1]),lineWidthAvailable=version>=2);let currentTextureSlot=null,currentBoundTextures={},scissorParam=gl.getParameter(gl.SCISSOR_BOX),viewportParam=gl.getParameter(gl.VIEWPORT),currentScissor=new Vector4().fromArray(scissorParam),currentViewport=new Vector4().fromArray(viewportParam);function createTexture(type,target,count,dimensions2){let data=new Uint8Array(4),texture=gl.createTexture();gl.bindTexture(type,texture),gl.texParameteri(type,gl.TEXTURE_MIN_FILTER,gl.NEAREST),gl.texParameteri(type,gl.TEXTURE_MAG_FILTER,gl.NEAREST);for(let i=0;i<count;i++)type===gl.TEXTURE_3D||type===gl.TEXTURE_2D_ARRAY?gl.texImage3D(target,0,gl.RGBA,1,1,dimensions2,0,gl.RGBA,gl.UNSIGNED_BYTE,data):gl.texImage2D(target+i,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,data);return texture}let emptyTextures={};emptyTextures[gl.TEXTURE_2D]=createTexture(gl.TEXTURE_2D,gl.TEXTURE_2D,1),emptyTextures[gl.TEXTURE_CUBE_MAP]=createTexture(gl.TEXTURE_CUBE_MAP,gl.TEXTURE_CUBE_MAP_POSITIVE_X,6),emptyTextures[gl.TEXTURE_2D_ARRAY]=createTexture(gl.TEXTURE_2D_ARRAY,gl.TEXTURE_2D_ARRAY,1,1),emptyTextures[gl.TEXTURE_3D]=createTexture(gl.TEXTURE_3D,gl.TEXTURE_3D,1,1),colorBuffer.setClear(0,0,0,1),depthBuffer.setClear(1),stencilBuffer.setClear(0),enable(gl.DEPTH_TEST),depthBuffer.setFunc(LessEqualDepth),setFlipSided(!1),setCullFace(CullFaceBack),enable(gl.CULL_FACE),setBlending(NoBlending);function enable(id){enabledCapabilities[id]!==!0&&(gl.enable(id),enabledCapabilities[id]=!0)}function disable(id){enabledCapabilities[id]!==!1&&(gl.disable(id),enabledCapabilities[id]=!1)}function bindFramebuffer(target,framebuffer){return currentBoundFramebuffers[target]!==framebuffer?(gl.bindFramebuffer(target,framebuffer),currentBoundFramebuffers[target]=framebuffer,target===gl.DRAW_FRAMEBUFFER&&(currentBoundFramebuffers[gl.FRAMEBUFFER]=framebuffer),target===gl.FRAMEBUFFER&&(currentBoundFramebuffers[gl.DRAW_FRAMEBUFFER]=framebuffer),!0):!1}function drawBuffers(renderTarget,framebuffer){let drawBuffers2=defaultDrawbuffers,needsUpdate=!1;if(renderTarget){drawBuffers2=currentDrawbuffers.get(framebuffer),drawBuffers2===void 0&&(drawBuffers2=[],currentDrawbuffers.set(framebuffer,drawBuffers2));let textures=renderTarget.textures;if(drawBuffers2.length!==textures.length||drawBuffers2[0]!==gl.COLOR_ATTACHMENT0){for(let i=0,il=textures.length;i<il;i++)drawBuffers2[i]=gl.COLOR_ATTACHMENT0+i;drawBuffers2.length=textures.length,needsUpdate=!0}}else drawBuffers2[0]!==gl.BACK&&(drawBuffers2[0]=gl.BACK,needsUpdate=!0);needsUpdate&&gl.drawBuffers(drawBuffers2)}function useProgram(program){return currentProgram!==program?(gl.useProgram(program),currentProgram=program,!0):!1}let equationToGL={[AddEquation]:gl.FUNC_ADD,[SubtractEquation]:gl.FUNC_SUBTRACT,[ReverseSubtractEquation]:gl.FUNC_REVERSE_SUBTRACT};equationToGL[MinEquation]=gl.MIN,equationToGL[MaxEquation]=gl.MAX;let factorToGL={[ZeroFactor]:gl.ZERO,[OneFactor]:gl.ONE,[SrcColorFactor]:gl.SRC_COLOR,[SrcAlphaFactor]:gl.SRC_ALPHA,[SrcAlphaSaturateFactor]:gl.SRC_ALPHA_SATURATE,[DstColorFactor]:gl.DST_COLOR,[DstAlphaFactor]:gl.DST_ALPHA,[OneMinusSrcColorFactor]:gl.ONE_MINUS_SRC_COLOR,[OneMinusSrcAlphaFactor]:gl.ONE_MINUS_SRC_ALPHA,[OneMinusDstColorFactor]:gl.ONE_MINUS_DST_COLOR,[OneMinusDstAlphaFactor]:gl.ONE_MINUS_DST_ALPHA,[ConstantColorFactor]:gl.CONSTANT_COLOR,[OneMinusConstantColorFactor]:gl.ONE_MINUS_CONSTANT_COLOR,[ConstantAlphaFactor]:gl.CONSTANT_ALPHA,[OneMinusConstantAlphaFactor]:gl.ONE_MINUS_CONSTANT_ALPHA};function setBlending(blending,blendEquation,blendSrc,blendDst,blendEquationAlpha,blendSrcAlpha,blendDstAlpha,blendColor,blendAlpha,premultipliedAlpha){if(blending===NoBlending){currentBlendingEnabled===!0&&(disable(gl.BLEND),currentBlendingEnabled=!1);return}if(currentBlendingEnabled===!1&&(enable(gl.BLEND),currentBlendingEnabled=!0),blending!==CustomBlending){if(blending!==currentBlending||premultipliedAlpha!==currentPremultipledAlpha){if((currentBlendEquation!==AddEquation||currentBlendEquationAlpha!==AddEquation)&&(gl.blendEquation(gl.FUNC_ADD),currentBlendEquation=AddEquation,currentBlendEquationAlpha=AddEquation),premultipliedAlpha)switch(blending){case NormalBlending:gl.blendFuncSeparate(gl.ONE,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);break;case AdditiveBlending:gl.blendFunc(gl.ONE,gl.ONE);break;case SubtractiveBlending:gl.blendFuncSeparate(gl.ZERO,gl.ONE_MINUS_SRC_COLOR,gl.ZERO,gl.ONE);break;case MultiplyBlending:gl.blendFuncSeparate(gl.DST_COLOR,gl.ONE_MINUS_SRC_ALPHA,gl.ZERO,gl.ONE);break;default:error("WebGLState: Invalid blending: ",blending);break}else switch(blending){case NormalBlending:gl.blendFuncSeparate(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);break;case AdditiveBlending:gl.blendFuncSeparate(gl.SRC_ALPHA,gl.ONE,gl.ONE,gl.ONE);break;case SubtractiveBlending:error("WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");break;case MultiplyBlending:error("WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");break;default:error("WebGLState: Invalid blending: ",blending);break}currentBlendSrc=null,currentBlendDst=null,currentBlendSrcAlpha=null,currentBlendDstAlpha=null,currentBlendColor.set(0,0,0),currentBlendAlpha=0,currentBlending=blending,currentPremultipledAlpha=premultipliedAlpha}return}blendEquationAlpha=blendEquationAlpha||blendEquation,blendSrcAlpha=blendSrcAlpha||blendSrc,blendDstAlpha=blendDstAlpha||blendDst,(blendEquation!==currentBlendEquation||blendEquationAlpha!==currentBlendEquationAlpha)&&(gl.blendEquationSeparate(equationToGL[blendEquation],equationToGL[blendEquationAlpha]),currentBlendEquation=blendEquation,currentBlendEquationAlpha=blendEquationAlpha),(blendSrc!==currentBlendSrc||blendDst!==currentBlendDst||blendSrcAlpha!==currentBlendSrcAlpha||blendDstAlpha!==currentBlendDstAlpha)&&(gl.blendFuncSeparate(factorToGL[blendSrc],factorToGL[blendDst],factorToGL[blendSrcAlpha],factorToGL[blendDstAlpha]),currentBlendSrc=blendSrc,currentBlendDst=blendDst,currentBlendSrcAlpha=blendSrcAlpha,currentBlendDstAlpha=blendDstAlpha),(blendColor.equals(currentBlendColor)===!1||blendAlpha!==currentBlendAlpha)&&(gl.blendColor(blendColor.r,blendColor.g,blendColor.b,blendAlpha),currentBlendColor.copy(blendColor),currentBlendAlpha=blendAlpha),currentBlending=blending,currentPremultipledAlpha=!1}function setMaterial(material,frontFaceCW){material.side===DoubleSide?disable(gl.CULL_FACE):enable(gl.CULL_FACE);let flipSided=material.side===BackSide;frontFaceCW&&(flipSided=!flipSided),setFlipSided(flipSided),material.blending===NormalBlending&&material.transparent===!1?setBlending(NoBlending):setBlending(material.blending,material.blendEquation,material.blendSrc,material.blendDst,material.blendEquationAlpha,material.blendSrcAlpha,material.blendDstAlpha,material.blendColor,material.blendAlpha,material.premultipliedAlpha),depthBuffer.setFunc(material.depthFunc),depthBuffer.setTest(material.depthTest),depthBuffer.setMask(material.depthWrite),colorBuffer.setMask(material.colorWrite);let stencilWrite=material.stencilWrite;stencilBuffer.setTest(stencilWrite),stencilWrite&&(stencilBuffer.setMask(material.stencilWriteMask),stencilBuffer.setFunc(material.stencilFunc,material.stencilRef,material.stencilFuncMask),stencilBuffer.setOp(material.stencilFail,material.stencilZFail,material.stencilZPass)),setPolygonOffset(material.polygonOffset,material.polygonOffsetFactor,material.polygonOffsetUnits),material.alphaToCoverage===!0?enable(gl.SAMPLE_ALPHA_TO_COVERAGE):disable(gl.SAMPLE_ALPHA_TO_COVERAGE)}function setFlipSided(flipSided){currentFlipSided!==flipSided&&(flipSided?gl.frontFace(gl.CW):gl.frontFace(gl.CCW),currentFlipSided=flipSided)}function setCullFace(cullFace){cullFace!==CullFaceNone?(enable(gl.CULL_FACE),cullFace!==currentCullFace&&(cullFace===CullFaceBack?gl.cullFace(gl.BACK):cullFace===CullFaceFront?gl.cullFace(gl.FRONT):gl.cullFace(gl.FRONT_AND_BACK))):disable(gl.CULL_FACE),currentCullFace=cullFace}function setLineWidth(width){width!==currentLineWidth&&(lineWidthAvailable&&gl.lineWidth(width),currentLineWidth=width)}function setPolygonOffset(polygonOffset,factor,units){polygonOffset?(enable(gl.POLYGON_OFFSET_FILL),(currentPolygonOffsetFactor!==factor||currentPolygonOffsetUnits!==units)&&(currentPolygonOffsetFactor=factor,currentPolygonOffsetUnits=units,depthBuffer.getReversed()&&(factor=-factor),gl.polygonOffset(factor,units))):disable(gl.POLYGON_OFFSET_FILL)}function setScissorTest(scissorTest){scissorTest?enable(gl.SCISSOR_TEST):disable(gl.SCISSOR_TEST)}function activeTexture(webglSlot){webglSlot===void 0&&(webglSlot=gl.TEXTURE0+maxTextures-1),currentTextureSlot!==webglSlot&&(gl.activeTexture(webglSlot),currentTextureSlot=webglSlot)}function bindTexture(webglType,webglTexture,webglSlot){webglSlot===void 0&&(currentTextureSlot===null?webglSlot=gl.TEXTURE0+maxTextures-1:webglSlot=currentTextureSlot);let boundTexture=currentBoundTextures[webglSlot];boundTexture===void 0&&(boundTexture={type:void 0,texture:void 0},currentBoundTextures[webglSlot]=boundTexture),(boundTexture.type!==webglType||boundTexture.texture!==webglTexture)&&(currentTextureSlot!==webglSlot&&(gl.activeTexture(webglSlot),currentTextureSlot=webglSlot),gl.bindTexture(webglType,webglTexture||emptyTextures[webglType]),boundTexture.type=webglType,boundTexture.texture=webglTexture)}function unbindTexture(){let boundTexture=currentBoundTextures[currentTextureSlot];boundTexture!==void 0&&boundTexture.type!==void 0&&(gl.bindTexture(boundTexture.type,null),boundTexture.type=void 0,boundTexture.texture=void 0)}function compressedTexImage2D(){try{gl.compressedTexImage2D(...arguments)}catch(e){error("WebGLState:",e)}}function compressedTexImage3D(){try{gl.compressedTexImage3D(...arguments)}catch(e){error("WebGLState:",e)}}function texSubImage2D(){try{gl.texSubImage2D(...arguments)}catch(e){error("WebGLState:",e)}}function texSubImage3D(){try{gl.texSubImage3D(...arguments)}catch(e){error("WebGLState:",e)}}function compressedTexSubImage2D(){try{gl.compressedTexSubImage2D(...arguments)}catch(e){error("WebGLState:",e)}}function compressedTexSubImage3D(){try{gl.compressedTexSubImage3D(...arguments)}catch(e){error("WebGLState:",e)}}function texStorage2D(){try{gl.texStorage2D(...arguments)}catch(e){error("WebGLState:",e)}}function texStorage3D(){try{gl.texStorage3D(...arguments)}catch(e){error("WebGLState:",e)}}function texImage2D(){try{gl.texImage2D(...arguments)}catch(e){error("WebGLState:",e)}}function texImage3D(){try{gl.texImage3D(...arguments)}catch(e){error("WebGLState:",e)}}function getParameter(name){return parameters[name]!==void 0?parameters[name]:gl.getParameter(name)}function pixelStorei(name,value){parameters[name]!==value&&(gl.pixelStorei(name,value),parameters[name]=value)}function scissor(scissor2){currentScissor.equals(scissor2)===!1&&(gl.scissor(scissor2.x,scissor2.y,scissor2.z,scissor2.w),currentScissor.copy(scissor2))}function viewport(viewport2){currentViewport.equals(viewport2)===!1&&(gl.viewport(viewport2.x,viewport2.y,viewport2.z,viewport2.w),currentViewport.copy(viewport2))}function updateUBOMapping(uniformsGroup,program){let mapping=uboProgramMap.get(program);mapping===void 0&&(mapping=new WeakMap,uboProgramMap.set(program,mapping));let blockIndex=mapping.get(uniformsGroup);blockIndex===void 0&&(blockIndex=gl.getUniformBlockIndex(program,uniformsGroup.name),mapping.set(uniformsGroup,blockIndex))}function uniformBlockBinding(uniformsGroup,program){let blockIndex=uboProgramMap.get(program).get(uniformsGroup);uboBindings.get(program)!==blockIndex&&(gl.uniformBlockBinding(program,blockIndex,uniformsGroup.__bindingPointIndex),uboBindings.set(program,blockIndex))}function reset(){gl.disable(gl.BLEND),gl.disable(gl.CULL_FACE),gl.disable(gl.DEPTH_TEST),gl.disable(gl.POLYGON_OFFSET_FILL),gl.disable(gl.SCISSOR_TEST),gl.disable(gl.STENCIL_TEST),gl.disable(gl.SAMPLE_ALPHA_TO_COVERAGE),gl.blendEquation(gl.FUNC_ADD),gl.blendFunc(gl.ONE,gl.ZERO),gl.blendFuncSeparate(gl.ONE,gl.ZERO,gl.ONE,gl.ZERO),gl.blendColor(0,0,0,0),gl.colorMask(!0,!0,!0,!0),gl.clearColor(0,0,0,0),gl.depthMask(!0),gl.depthFunc(gl.LESS),depthBuffer.setReversed(!1),gl.clearDepth(1),gl.stencilMask(4294967295),gl.stencilFunc(gl.ALWAYS,0,4294967295),gl.stencilOp(gl.KEEP,gl.KEEP,gl.KEEP),gl.clearStencil(0),gl.cullFace(gl.BACK),gl.frontFace(gl.CCW),gl.polygonOffset(0,0),gl.activeTexture(gl.TEXTURE0),gl.bindFramebuffer(gl.FRAMEBUFFER,null),gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER,null),gl.bindFramebuffer(gl.READ_FRAMEBUFFER,null),gl.useProgram(null),gl.lineWidth(1),gl.scissor(0,0,gl.canvas.width,gl.canvas.height),gl.viewport(0,0,gl.canvas.width,gl.canvas.height),gl.pixelStorei(gl.PACK_ALIGNMENT,4),gl.pixelStorei(gl.UNPACK_ALIGNMENT,4),gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,!1),gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,!1),gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.BROWSER_DEFAULT_WEBGL),gl.pixelStorei(gl.PACK_ROW_LENGTH,0),gl.pixelStorei(gl.PACK_SKIP_PIXELS,0),gl.pixelStorei(gl.PACK_SKIP_ROWS,0),gl.pixelStorei(gl.UNPACK_ROW_LENGTH,0),gl.pixelStorei(gl.UNPACK_IMAGE_HEIGHT,0),gl.pixelStorei(gl.UNPACK_SKIP_PIXELS,0),gl.pixelStorei(gl.UNPACK_SKIP_ROWS,0),gl.pixelStorei(gl.UNPACK_SKIP_IMAGES,0),enabledCapabilities={},parameters={},currentTextureSlot=null,currentBoundTextures={},currentBoundFramebuffers={},currentDrawbuffers=new WeakMap,defaultDrawbuffers=[],currentProgram=null,currentBlendingEnabled=!1,currentBlending=null,currentBlendEquation=null,currentBlendSrc=null,currentBlendDst=null,currentBlendEquationAlpha=null,currentBlendSrcAlpha=null,currentBlendDstAlpha=null,currentBlendColor=new Color(0,0,0),currentBlendAlpha=0,currentPremultipledAlpha=!1,currentFlipSided=null,currentCullFace=null,currentLineWidth=null,currentPolygonOffsetFactor=null,currentPolygonOffsetUnits=null,currentScissor.set(0,0,gl.canvas.width,gl.canvas.height),currentViewport.set(0,0,gl.canvas.width,gl.canvas.height),colorBuffer.reset(),depthBuffer.reset(),stencilBuffer.reset()}return{buffers:{color:colorBuffer,depth:depthBuffer,stencil:stencilBuffer},enable,disable,bindFramebuffer,drawBuffers,useProgram,setBlending,setMaterial,setFlipSided,setCullFace,setLineWidth,setPolygonOffset,setScissorTest,activeTexture,bindTexture,unbindTexture,compressedTexImage2D,compressedTexImage3D,texImage2D,texImage3D,pixelStorei,getParameter,updateUBOMapping,uniformBlockBinding,texStorage2D,texStorage3D,texSubImage2D,texSubImage3D,compressedTexSubImage2D,compressedTexSubImage3D,scissor,viewport,reset}}function WebGLTextures(_gl,extensions,state,properties,capabilities,utils,info){let multisampledRTTExt=extensions.has("WEBGL_multisampled_render_to_texture")?extensions.get("WEBGL_multisampled_render_to_texture"):null,supportsInvalidateFramebuffer=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),_imageDimensions=new Vector2,_videoTextures=new WeakMap,_htmlTextures=new Set,_canvas2,_sources=new WeakMap,useOffscreenCanvas=!1;try{useOffscreenCanvas=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function createCanvas(width,height){return useOffscreenCanvas&&typeof OffscreenCanvas<"u"?new OffscreenCanvas(width,height):createElementNS("canvas")}function resizeImage(image,needsNewCanvas,maxSize){let scale=1,dimensions2=getDimensions(image);if((dimensions2.width>maxSize||dimensions2.height>maxSize)&&(scale=maxSize/Math.max(dimensions2.width,dimensions2.height)),scale<1)if(typeof HTMLImageElement<"u"&&image instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&image instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&image instanceof ImageBitmap||typeof VideoFrame<"u"&&image instanceof VideoFrame){let width=Math.floor(scale*dimensions2.width),height=Math.floor(scale*dimensions2.height);_canvas2===void 0&&(_canvas2=createCanvas(width,height));let canvas=needsNewCanvas?createCanvas(width,height):_canvas2;return canvas.width=width,canvas.height=height,canvas.getContext("2d").drawImage(image,0,0,width,height),warn("WebGLRenderer: Texture has been resized from ("+dimensions2.width+"x"+dimensions2.height+") to ("+width+"x"+height+")."),canvas}else return"data"in image&&warn("WebGLRenderer: Image in DataTexture is too big ("+dimensions2.width+"x"+dimensions2.height+")."),image;return image}function textureNeedsGenerateMipmaps(texture){return texture.generateMipmaps}function generateMipmap(target){_gl.generateMipmap(target)}function getTargetType(texture){return texture.isWebGLCubeRenderTarget?_gl.TEXTURE_CUBE_MAP:texture.isWebGL3DRenderTarget?_gl.TEXTURE_3D:texture.isWebGLArrayRenderTarget||texture.isCompressedArrayTexture?_gl.TEXTURE_2D_ARRAY:_gl.TEXTURE_2D}function getInternalFormat(internalFormatName,glFormat,glType,normalized,colorSpace,forceLinearTransfer=!1){if(internalFormatName!==null){if(_gl[internalFormatName]!==void 0)return _gl[internalFormatName];warn("WebGLRenderer: Attempt to use non-existing WebGL internal format '"+internalFormatName+"'")}let ext_texture_norm16;normalized&&(ext_texture_norm16=extensions.get("EXT_texture_norm16"),ext_texture_norm16||warn("WebGLRenderer: Unable to use normalized textures without EXT_texture_norm16 extension"));let internalFormat=glFormat;if(glFormat===_gl.RED&&(glType===_gl.FLOAT&&(internalFormat=_gl.R32F),glType===_gl.HALF_FLOAT&&(internalFormat=_gl.R16F),glType===_gl.UNSIGNED_BYTE&&(internalFormat=_gl.R8),glType===_gl.UNSIGNED_SHORT&&ext_texture_norm16&&(internalFormat=ext_texture_norm16.R16_EXT),glType===_gl.SHORT&&ext_texture_norm16&&(internalFormat=ext_texture_norm16.R16_SNORM_EXT)),glFormat===_gl.RED_INTEGER&&(glType===_gl.UNSIGNED_BYTE&&(internalFormat=_gl.R8UI),glType===_gl.UNSIGNED_SHORT&&(internalFormat=_gl.R16UI),glType===_gl.UNSIGNED_INT&&(internalFormat=_gl.R32UI),glType===_gl.BYTE&&(internalFormat=_gl.R8I),glType===_gl.SHORT&&(internalFormat=_gl.R16I),glType===_gl.INT&&(internalFormat=_gl.R32I)),glFormat===_gl.RG&&(glType===_gl.FLOAT&&(internalFormat=_gl.RG32F),glType===_gl.HALF_FLOAT&&(internalFormat=_gl.RG16F),glType===_gl.UNSIGNED_BYTE&&(internalFormat=_gl.RG8),glType===_gl.UNSIGNED_SHORT&&ext_texture_norm16&&(internalFormat=ext_texture_norm16.RG16_EXT),glType===_gl.SHORT&&ext_texture_norm16&&(internalFormat=ext_texture_norm16.RG16_SNORM_EXT)),glFormat===_gl.RG_INTEGER&&(glType===_gl.UNSIGNED_BYTE&&(internalFormat=_gl.RG8UI),glType===_gl.UNSIGNED_SHORT&&(internalFormat=_gl.RG16UI),glType===_gl.UNSIGNED_INT&&(internalFormat=_gl.RG32UI),glType===_gl.BYTE&&(internalFormat=_gl.RG8I),glType===_gl.SHORT&&(internalFormat=_gl.RG16I),glType===_gl.INT&&(internalFormat=_gl.RG32I)),glFormat===_gl.RGB_INTEGER&&(glType===_gl.UNSIGNED_BYTE&&(internalFormat=_gl.RGB8UI),glType===_gl.UNSIGNED_SHORT&&(internalFormat=_gl.RGB16UI),glType===_gl.UNSIGNED_INT&&(internalFormat=_gl.RGB32UI),glType===_gl.BYTE&&(internalFormat=_gl.RGB8I),glType===_gl.SHORT&&(internalFormat=_gl.RGB16I),glType===_gl.INT&&(internalFormat=_gl.RGB32I)),glFormat===_gl.RGBA_INTEGER&&(glType===_gl.UNSIGNED_BYTE&&(internalFormat=_gl.RGBA8UI),glType===_gl.UNSIGNED_SHORT&&(internalFormat=_gl.RGBA16UI),glType===_gl.UNSIGNED_INT&&(internalFormat=_gl.RGBA32UI),glType===_gl.BYTE&&(internalFormat=_gl.RGBA8I),glType===_gl.SHORT&&(internalFormat=_gl.RGBA16I),glType===_gl.INT&&(internalFormat=_gl.RGBA32I)),glFormat===_gl.RGB&&(glType===_gl.UNSIGNED_SHORT&&ext_texture_norm16&&(internalFormat=ext_texture_norm16.RGB16_EXT),glType===_gl.SHORT&&ext_texture_norm16&&(internalFormat=ext_texture_norm16.RGB16_SNORM_EXT),glType===_gl.UNSIGNED_INT_5_9_9_9_REV&&(internalFormat=_gl.RGB9_E5),glType===_gl.UNSIGNED_INT_10F_11F_11F_REV&&(internalFormat=_gl.R11F_G11F_B10F)),glFormat===_gl.RGBA){let transfer=forceLinearTransfer?LinearTransfer:ColorManagement.getTransfer(colorSpace);glType===_gl.FLOAT&&(internalFormat=_gl.RGBA32F),glType===_gl.HALF_FLOAT&&(internalFormat=_gl.RGBA16F),glType===_gl.UNSIGNED_BYTE&&(internalFormat=transfer===SRGBTransfer?_gl.SRGB8_ALPHA8:_gl.RGBA8),glType===_gl.UNSIGNED_SHORT&&ext_texture_norm16&&(internalFormat=ext_texture_norm16.RGBA16_EXT),glType===_gl.SHORT&&ext_texture_norm16&&(internalFormat=ext_texture_norm16.RGBA16_SNORM_EXT),glType===_gl.UNSIGNED_SHORT_4_4_4_4&&(internalFormat=_gl.RGBA4),glType===_gl.UNSIGNED_SHORT_5_5_5_1&&(internalFormat=_gl.RGB5_A1)}return(internalFormat===_gl.R16F||internalFormat===_gl.R32F||internalFormat===_gl.RG16F||internalFormat===_gl.RG32F||internalFormat===_gl.RGBA16F||internalFormat===_gl.RGBA32F)&&extensions.get("EXT_color_buffer_float"),internalFormat}function getInternalDepthFormat(useStencil,depthType){let glInternalFormat;return useStencil?depthType===null||depthType===UnsignedIntType||depthType===UnsignedInt248Type?glInternalFormat=_gl.DEPTH24_STENCIL8:depthType===FloatType?glInternalFormat=_gl.DEPTH32F_STENCIL8:depthType===UnsignedShortType&&(glInternalFormat=_gl.DEPTH24_STENCIL8,warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):depthType===null||depthType===UnsignedIntType||depthType===UnsignedInt248Type?glInternalFormat=_gl.DEPTH_COMPONENT24:depthType===FloatType?glInternalFormat=_gl.DEPTH_COMPONENT32F:depthType===UnsignedShortType&&(glInternalFormat=_gl.DEPTH_COMPONENT16),glInternalFormat}function getMipLevels(texture,image){return textureNeedsGenerateMipmaps(texture)===!0||texture.isFramebufferTexture&&texture.minFilter!==NearestFilter&&texture.minFilter!==LinearFilter?Math.log2(Math.max(image.width,image.height))+1:texture.mipmaps!==void 0&&texture.mipmaps.length>0?texture.mipmaps.length:texture.isCompressedTexture&&Array.isArray(texture.image)?image.mipmaps.length:1}function onTextureDispose(event){let texture=event.target;texture.removeEventListener("dispose",onTextureDispose),deallocateTexture(texture),texture.isVideoTexture&&_videoTextures.delete(texture),texture.isHTMLTexture&&_htmlTextures.delete(texture)}function onRenderTargetDispose(event){let renderTarget=event.target;renderTarget.removeEventListener("dispose",onRenderTargetDispose),deallocateRenderTarget(renderTarget)}function deallocateTexture(texture){let textureProperties=properties.get(texture);if(textureProperties.__webglInit===void 0)return;let source=texture.source,webglTextures=_sources.get(source);if(webglTextures){let webglTexture=webglTextures[textureProperties.__cacheKey];webglTexture.usedTimes--,webglTexture.usedTimes===0&&deleteTexture(texture),Object.keys(webglTextures).length===0&&_sources.delete(source)}properties.remove(texture)}function deleteTexture(texture){let textureProperties=properties.get(texture);_gl.deleteTexture(textureProperties.__webglTexture);let source=texture.source,webglTextures=_sources.get(source);delete webglTextures[textureProperties.__cacheKey],info.memory.textures--}function deallocateRenderTarget(renderTarget){let renderTargetProperties=properties.get(renderTarget);if(renderTarget.depthTexture&&(renderTarget.depthTexture.dispose(),properties.remove(renderTarget.depthTexture)),renderTarget.isWebGLCubeRenderTarget)for(let i=0;i<6;i++){if(Array.isArray(renderTargetProperties.__webglFramebuffer[i]))for(let level=0;level<renderTargetProperties.__webglFramebuffer[i].length;level++)_gl.deleteFramebuffer(renderTargetProperties.__webglFramebuffer[i][level]);else _gl.deleteFramebuffer(renderTargetProperties.__webglFramebuffer[i]);renderTargetProperties.__webglDepthbuffer&&_gl.deleteRenderbuffer(renderTargetProperties.__webglDepthbuffer[i])}else{if(Array.isArray(renderTargetProperties.__webglFramebuffer))for(let level=0;level<renderTargetProperties.__webglFramebuffer.length;level++)_gl.deleteFramebuffer(renderTargetProperties.__webglFramebuffer[level]);else _gl.deleteFramebuffer(renderTargetProperties.__webglFramebuffer);if(renderTargetProperties.__webglDepthbuffer&&_gl.deleteRenderbuffer(renderTargetProperties.__webglDepthbuffer),renderTargetProperties.__webglMultisampledFramebuffer&&_gl.deleteFramebuffer(renderTargetProperties.__webglMultisampledFramebuffer),renderTargetProperties.__webglColorRenderbuffer)for(let i=0;i<renderTargetProperties.__webglColorRenderbuffer.length;i++)renderTargetProperties.__webglColorRenderbuffer[i]&&_gl.deleteRenderbuffer(renderTargetProperties.__webglColorRenderbuffer[i]);renderTargetProperties.__webglDepthRenderbuffer&&_gl.deleteRenderbuffer(renderTargetProperties.__webglDepthRenderbuffer)}let textures=renderTarget.textures;for(let i=0,il=textures.length;i<il;i++){let attachmentProperties=properties.get(textures[i]);attachmentProperties.__webglTexture&&(_gl.deleteTexture(attachmentProperties.__webglTexture),info.memory.textures--),properties.remove(textures[i])}properties.remove(renderTarget)}let textureUnits=0;function resetTextureUnits(){textureUnits=0}function getTextureUnits(){return textureUnits}function setTextureUnits(value){textureUnits=value}function allocateTextureUnit(){let textureUnit=textureUnits;return textureUnit>=capabilities.maxTextures&&warn("WebGLTextures: Trying to use "+(textureUnit+1)+" texture units while this GPU supports only "+capabilities.maxTextures),textureUnits+=1,textureUnit}function getTextureCacheKey(texture){let array=[];return array.push(texture.wrapS),array.push(texture.wrapT),array.push(texture.wrapR||0),array.push(texture.magFilter),array.push(texture.minFilter),array.push(texture.anisotropy),array.push(texture.internalFormat),array.push(texture.format),array.push(texture.type),array.push(texture.generateMipmaps),array.push(texture.premultiplyAlpha),array.push(texture.flipY),array.push(texture.unpackAlignment),array.push(texture.colorSpace),array.join()}function setTexture2D(texture,slot){let textureProperties=properties.get(texture);if(texture.isVideoTexture&&updateVideoTexture(texture),texture.isRenderTargetTexture===!1&&texture.isExternalTexture!==!0&&texture.version>0&&textureProperties.__version!==texture.version){let image=texture.image;if(image===null)warn("WebGLRenderer: Texture marked for update but no image data found.");else if(image.complete===!1)warn("WebGLRenderer: Texture marked for update but image is incomplete");else{uploadTexture(textureProperties,texture,slot);return}}else texture.isExternalTexture&&(textureProperties.__webglTexture=texture.sourceTexture?texture.sourceTexture:null);state.bindTexture(_gl.TEXTURE_2D,textureProperties.__webglTexture,_gl.TEXTURE0+slot)}function setTexture2DArray(texture,slot){let textureProperties=properties.get(texture);if(texture.isRenderTargetTexture===!1&&texture.version>0&&textureProperties.__version!==texture.version){uploadTexture(textureProperties,texture,slot);return}else texture.isExternalTexture&&(textureProperties.__webglTexture=texture.sourceTexture?texture.sourceTexture:null);state.bindTexture(_gl.TEXTURE_2D_ARRAY,textureProperties.__webglTexture,_gl.TEXTURE0+slot)}function setTexture3D(texture,slot){let textureProperties=properties.get(texture);if(texture.isRenderTargetTexture===!1&&texture.version>0&&textureProperties.__version!==texture.version){uploadTexture(textureProperties,texture,slot);return}state.bindTexture(_gl.TEXTURE_3D,textureProperties.__webglTexture,_gl.TEXTURE0+slot)}function setTextureCube(texture,slot){let textureProperties=properties.get(texture);if(texture.isCubeDepthTexture!==!0&&texture.version>0&&textureProperties.__version!==texture.version){uploadCubeTexture(textureProperties,texture,slot);return}state.bindTexture(_gl.TEXTURE_CUBE_MAP,textureProperties.__webglTexture,_gl.TEXTURE0+slot)}let wrappingToGL={[RepeatWrapping]:_gl.REPEAT,[ClampToEdgeWrapping]:_gl.CLAMP_TO_EDGE,[MirroredRepeatWrapping]:_gl.MIRRORED_REPEAT},filterToGL={[NearestFilter]:_gl.NEAREST,[NearestMipmapNearestFilter]:_gl.NEAREST_MIPMAP_NEAREST,[NearestMipmapLinearFilter]:_gl.NEAREST_MIPMAP_LINEAR,[LinearFilter]:_gl.LINEAR,[LinearMipmapNearestFilter]:_gl.LINEAR_MIPMAP_NEAREST,[LinearMipmapLinearFilter]:_gl.LINEAR_MIPMAP_LINEAR},compareToGL={[NeverCompare]:_gl.NEVER,[AlwaysCompare]:_gl.ALWAYS,[LessCompare]:_gl.LESS,[LessEqualCompare]:_gl.LEQUAL,[EqualCompare]:_gl.EQUAL,[GreaterEqualCompare]:_gl.GEQUAL,[GreaterCompare]:_gl.GREATER,[NotEqualCompare]:_gl.NOTEQUAL};function setTextureParameters(textureType,texture){if(texture.type===FloatType&&extensions.has("OES_texture_float_linear")===!1&&(texture.magFilter===LinearFilter||texture.magFilter===LinearMipmapNearestFilter||texture.magFilter===NearestMipmapLinearFilter||texture.magFilter===LinearMipmapLinearFilter||texture.minFilter===LinearFilter||texture.minFilter===LinearMipmapNearestFilter||texture.minFilter===NearestMipmapLinearFilter||texture.minFilter===LinearMipmapLinearFilter)&&warn("WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),_gl.texParameteri(textureType,_gl.TEXTURE_WRAP_S,wrappingToGL[texture.wrapS]),_gl.texParameteri(textureType,_gl.TEXTURE_WRAP_T,wrappingToGL[texture.wrapT]),(textureType===_gl.TEXTURE_3D||textureType===_gl.TEXTURE_2D_ARRAY)&&_gl.texParameteri(textureType,_gl.TEXTURE_WRAP_R,wrappingToGL[texture.wrapR]),_gl.texParameteri(textureType,_gl.TEXTURE_MAG_FILTER,filterToGL[texture.magFilter]),_gl.texParameteri(textureType,_gl.TEXTURE_MIN_FILTER,filterToGL[texture.minFilter]),texture.compareFunction&&(_gl.texParameteri(textureType,_gl.TEXTURE_COMPARE_MODE,_gl.COMPARE_REF_TO_TEXTURE),_gl.texParameteri(textureType,_gl.TEXTURE_COMPARE_FUNC,compareToGL[texture.compareFunction])),extensions.has("EXT_texture_filter_anisotropic")===!0){if(texture.magFilter===NearestFilter||texture.minFilter!==NearestMipmapLinearFilter&&texture.minFilter!==LinearMipmapLinearFilter||texture.type===FloatType&&extensions.has("OES_texture_float_linear")===!1)return;if(texture.anisotropy>1||properties.get(texture).__currentAnisotropy){let extension=extensions.get("EXT_texture_filter_anisotropic");_gl.texParameterf(textureType,extension.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(texture.anisotropy,capabilities.getMaxAnisotropy())),properties.get(texture).__currentAnisotropy=texture.anisotropy}}}function initTexture(textureProperties,texture){let forceUpload=!1;textureProperties.__webglInit===void 0&&(textureProperties.__webglInit=!0,texture.addEventListener("dispose",onTextureDispose));let source=texture.source,webglTextures=_sources.get(source);webglTextures===void 0&&(webglTextures={},_sources.set(source,webglTextures));let textureCacheKey=getTextureCacheKey(texture);if(textureCacheKey!==textureProperties.__cacheKey){webglTextures[textureCacheKey]===void 0&&(webglTextures[textureCacheKey]={texture:_gl.createTexture(),usedTimes:0},info.memory.textures++,forceUpload=!0),webglTextures[textureCacheKey].usedTimes++;let webglTexture=webglTextures[textureProperties.__cacheKey];webglTexture!==void 0&&(webglTextures[textureProperties.__cacheKey].usedTimes--,webglTexture.usedTimes===0&&deleteTexture(texture)),textureProperties.__cacheKey=textureCacheKey,textureProperties.__webglTexture=webglTextures[textureCacheKey].texture}return forceUpload}function getRow(index,rowLength,componentStride){return Math.floor(Math.floor(index/componentStride)/rowLength)}function updateTexture(texture,image,glFormat,glType){let updateRanges=texture.updateRanges;if(updateRanges.length===0)state.texSubImage2D(_gl.TEXTURE_2D,0,0,0,image.width,image.height,glFormat,glType,image.data);else{updateRanges.sort((a,b)=>a.start-b.start);let mergeIndex=0;for(let i=1;i<updateRanges.length;i++){let previousRange=updateRanges[mergeIndex],range=updateRanges[i],previousEnd=previousRange.start+previousRange.count,currentRow=getRow(range.start,image.width,4),previousRow=getRow(previousRange.start,image.width,4);range.start<=previousEnd+1&&currentRow===previousRow&&getRow(range.start+range.count-1,image.width,4)===currentRow?previousRange.count=Math.max(previousRange.count,range.start+range.count-previousRange.start):(++mergeIndex,updateRanges[mergeIndex]=range)}updateRanges.length=mergeIndex+1;let currentUnpackRowLen=state.getParameter(_gl.UNPACK_ROW_LENGTH),currentUnpackSkipPixels=state.getParameter(_gl.UNPACK_SKIP_PIXELS),currentUnpackSkipRows=state.getParameter(_gl.UNPACK_SKIP_ROWS);state.pixelStorei(_gl.UNPACK_ROW_LENGTH,image.width);for(let i=0,l=updateRanges.length;i<l;i++){let range=updateRanges[i],pixelStart=Math.floor(range.start/4),pixelCount=Math.ceil(range.count/4),x=pixelStart%image.width,y=Math.floor(pixelStart/image.width),width=pixelCount,height=1;state.pixelStorei(_gl.UNPACK_SKIP_PIXELS,x),state.pixelStorei(_gl.UNPACK_SKIP_ROWS,y),state.texSubImage2D(_gl.TEXTURE_2D,0,x,y,width,height,glFormat,glType,image.data)}texture.clearUpdateRanges(),state.pixelStorei(_gl.UNPACK_ROW_LENGTH,currentUnpackRowLen),state.pixelStorei(_gl.UNPACK_SKIP_PIXELS,currentUnpackSkipPixels),state.pixelStorei(_gl.UNPACK_SKIP_ROWS,currentUnpackSkipRows)}}function uploadTexture(textureProperties,texture,slot){let textureType=_gl.TEXTURE_2D;(texture.isDataArrayTexture||texture.isCompressedArrayTexture)&&(textureType=_gl.TEXTURE_2D_ARRAY),texture.isData3DTexture&&(textureType=_gl.TEXTURE_3D);let forceUpload=initTexture(textureProperties,texture),source=texture.source;state.bindTexture(textureType,textureProperties.__webglTexture,_gl.TEXTURE0+slot);let sourceProperties=properties.get(source);if(source.version!==sourceProperties.__version||forceUpload===!0){if(state.activeTexture(_gl.TEXTURE0+slot),(typeof ImageBitmap<"u"&&texture.image instanceof ImageBitmap)===!1){let workingPrimaries=ColorManagement.getPrimaries(ColorManagement.workingColorSpace),texturePrimaries=texture.colorSpace===NoColorSpace?null:ColorManagement.getPrimaries(texture.colorSpace),unpackConversion=texture.colorSpace===NoColorSpace||workingPrimaries===texturePrimaries?_gl.NONE:_gl.BROWSER_DEFAULT_WEBGL;state.pixelStorei(_gl.UNPACK_FLIP_Y_WEBGL,texture.flipY),state.pixelStorei(_gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,texture.premultiplyAlpha),state.pixelStorei(_gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,unpackConversion)}state.pixelStorei(_gl.UNPACK_ALIGNMENT,texture.unpackAlignment);let image=resizeImage(texture.image,!1,capabilities.maxTextureSize);image=verifyColorSpace(texture,image);let glFormat=utils.convert(texture.format,texture.colorSpace),glType=utils.convert(texture.type),glInternalFormat=getInternalFormat(texture.internalFormat,glFormat,glType,texture.normalized,texture.colorSpace,texture.isVideoTexture);setTextureParameters(textureType,texture);let mipmap,mipmaps=texture.mipmaps,useTexStorage=texture.isVideoTexture!==!0,allocateMemory=sourceProperties.__version===void 0||forceUpload===!0,dataReady=source.dataReady,levels=getMipLevels(texture,image);if(texture.isDepthTexture)glInternalFormat=getInternalDepthFormat(texture.format===DepthStencilFormat,texture.type),allocateMemory&&(useTexStorage?state.texStorage2D(_gl.TEXTURE_2D,1,glInternalFormat,image.width,image.height):state.texImage2D(_gl.TEXTURE_2D,0,glInternalFormat,image.width,image.height,0,glFormat,glType,null));else if(texture.isDataTexture)if(mipmaps.length>0){useTexStorage&&allocateMemory&&state.texStorage2D(_gl.TEXTURE_2D,levels,glInternalFormat,mipmaps[0].width,mipmaps[0].height);for(let i=0,il=mipmaps.length;i<il;i++)mipmap=mipmaps[i],useTexStorage?dataReady&&state.texSubImage2D(_gl.TEXTURE_2D,i,0,0,mipmap.width,mipmap.height,glFormat,glType,mipmap.data):state.texImage2D(_gl.TEXTURE_2D,i,glInternalFormat,mipmap.width,mipmap.height,0,glFormat,glType,mipmap.data);texture.generateMipmaps=!1}else useTexStorage?(allocateMemory&&state.texStorage2D(_gl.TEXTURE_2D,levels,glInternalFormat,image.width,image.height),dataReady&&updateTexture(texture,image,glFormat,glType)):state.texImage2D(_gl.TEXTURE_2D,0,glInternalFormat,image.width,image.height,0,glFormat,glType,image.data);else if(texture.isCompressedTexture)if(texture.isCompressedArrayTexture){useTexStorage&&allocateMemory&&state.texStorage3D(_gl.TEXTURE_2D_ARRAY,levels,glInternalFormat,mipmaps[0].width,mipmaps[0].height,image.depth);for(let i=0,il=mipmaps.length;i<il;i++)if(mipmap=mipmaps[i],texture.format!==RGBAFormat)if(glFormat!==null)if(useTexStorage){if(dataReady)if(texture.layerUpdates.size>0){let layerByteLength=getByteLength(mipmap.width,mipmap.height,texture.format,texture.type);for(let layerIndex of texture.layerUpdates){let layerData=mipmap.data.subarray(layerIndex*layerByteLength/mipmap.data.BYTES_PER_ELEMENT,(layerIndex+1)*layerByteLength/mipmap.data.BYTES_PER_ELEMENT);state.compressedTexSubImage3D(_gl.TEXTURE_2D_ARRAY,i,0,0,layerIndex,mipmap.width,mipmap.height,1,glFormat,layerData)}}else state.compressedTexSubImage3D(_gl.TEXTURE_2D_ARRAY,i,0,0,0,mipmap.width,mipmap.height,image.depth,glFormat,mipmap.data)}else state.compressedTexImage3D(_gl.TEXTURE_2D_ARRAY,i,glInternalFormat,mipmap.width,mipmap.height,image.depth,0,mipmap.data,0,0);else warn("WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else useTexStorage?dataReady&&state.texSubImage3D(_gl.TEXTURE_2D_ARRAY,i,0,0,0,mipmap.width,mipmap.height,image.depth,glFormat,glType,mipmap.data):state.texImage3D(_gl.TEXTURE_2D_ARRAY,i,glInternalFormat,mipmap.width,mipmap.height,image.depth,0,glFormat,glType,mipmap.data);texture.layerUpdates.size>0&&texture.clearLayerUpdates()}else{useTexStorage&&allocateMemory&&state.texStorage2D(_gl.TEXTURE_2D,levels,glInternalFormat,mipmaps[0].width,mipmaps[0].height);for(let i=0,il=mipmaps.length;i<il;i++)mipmap=mipmaps[i],texture.format!==RGBAFormat?glFormat!==null?useTexStorage?dataReady&&state.compressedTexSubImage2D(_gl.TEXTURE_2D,i,0,0,mipmap.width,mipmap.height,glFormat,mipmap.data):state.compressedTexImage2D(_gl.TEXTURE_2D,i,glInternalFormat,mipmap.width,mipmap.height,0,mipmap.data):warn("WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):useTexStorage?dataReady&&state.texSubImage2D(_gl.TEXTURE_2D,i,0,0,mipmap.width,mipmap.height,glFormat,glType,mipmap.data):state.texImage2D(_gl.TEXTURE_2D,i,glInternalFormat,mipmap.width,mipmap.height,0,glFormat,glType,mipmap.data)}else if(texture.isDataArrayTexture)if(useTexStorage){if(allocateMemory&&state.texStorage3D(_gl.TEXTURE_2D_ARRAY,levels,glInternalFormat,image.width,image.height,image.depth),dataReady)if(texture.layerUpdates.size>0){let layerByteLength=getByteLength(image.width,image.height,texture.format,texture.type);for(let layerIndex of texture.layerUpdates){let layerData=image.data.subarray(layerIndex*layerByteLength/image.data.BYTES_PER_ELEMENT,(layerIndex+1)*layerByteLength/image.data.BYTES_PER_ELEMENT);state.texSubImage3D(_gl.TEXTURE_2D_ARRAY,0,0,0,layerIndex,image.width,image.height,1,glFormat,glType,layerData)}texture.clearLayerUpdates()}else state.texSubImage3D(_gl.TEXTURE_2D_ARRAY,0,0,0,0,image.width,image.height,image.depth,glFormat,glType,image.data)}else state.texImage3D(_gl.TEXTURE_2D_ARRAY,0,glInternalFormat,image.width,image.height,image.depth,0,glFormat,glType,image.data);else if(texture.isData3DTexture)useTexStorage?(allocateMemory&&state.texStorage3D(_gl.TEXTURE_3D,levels,glInternalFormat,image.width,image.height,image.depth),dataReady&&state.texSubImage3D(_gl.TEXTURE_3D,0,0,0,0,image.width,image.height,image.depth,glFormat,glType,image.data)):state.texImage3D(_gl.TEXTURE_3D,0,glInternalFormat,image.width,image.height,image.depth,0,glFormat,glType,image.data);else if(texture.isFramebufferTexture){if(allocateMemory)if(useTexStorage)state.texStorage2D(_gl.TEXTURE_2D,levels,glInternalFormat,image.width,image.height);else{let width=image.width,height=image.height;for(let i=0;i<levels;i++)state.texImage2D(_gl.TEXTURE_2D,i,glInternalFormat,width,height,0,glFormat,glType,null),width>>=1,height>>=1}}else if(texture.isHTMLTexture){if("texElementImage2D"in _gl){let canvas=_gl.canvas;if(canvas.hasAttribute("layoutsubtree")||canvas.setAttribute("layoutsubtree","true"),image.parentNode!==canvas){canvas.appendChild(image),_htmlTextures.add(texture),canvas.onpaint=event=>{let changed=event.changedElements;for(let t of _htmlTextures)changed.includes(t.image)&&(t.needsUpdate=!0)},canvas.requestPaint();return}if(_gl.texElementImage2D.length===3)_gl.texElementImage2D(_gl.TEXTURE_2D,_gl.RGBA8,image);else{let internalFormat=_gl.RGBA,srcFormat=_gl.RGBA,srcType=_gl.UNSIGNED_BYTE;_gl.texElementImage2D(_gl.TEXTURE_2D,0,internalFormat,srcFormat,srcType,image)}_gl.texParameteri(_gl.TEXTURE_2D,_gl.TEXTURE_MIN_FILTER,_gl.LINEAR),_gl.texParameteri(_gl.TEXTURE_2D,_gl.TEXTURE_WRAP_S,_gl.CLAMP_TO_EDGE),_gl.texParameteri(_gl.TEXTURE_2D,_gl.TEXTURE_WRAP_T,_gl.CLAMP_TO_EDGE)}}else if(mipmaps.length>0){if(useTexStorage&&allocateMemory){let dimensions2=getDimensions(mipmaps[0]);state.texStorage2D(_gl.TEXTURE_2D,levels,glInternalFormat,dimensions2.width,dimensions2.height)}for(let i=0,il=mipmaps.length;i<il;i++)mipmap=mipmaps[i],useTexStorage?dataReady&&state.texSubImage2D(_gl.TEXTURE_2D,i,0,0,glFormat,glType,mipmap):state.texImage2D(_gl.TEXTURE_2D,i,glInternalFormat,glFormat,glType,mipmap);texture.generateMipmaps=!1}else if(useTexStorage){if(allocateMemory){let dimensions2=getDimensions(image);state.texStorage2D(_gl.TEXTURE_2D,levels,glInternalFormat,dimensions2.width,dimensions2.height)}dataReady&&state.texSubImage2D(_gl.TEXTURE_2D,0,0,0,glFormat,glType,image)}else state.texImage2D(_gl.TEXTURE_2D,0,glInternalFormat,glFormat,glType,image);textureNeedsGenerateMipmaps(texture)&&generateMipmap(textureType),sourceProperties.__version=source.version,texture.onUpdate&&texture.onUpdate(texture)}textureProperties.__version=texture.version}function uploadCubeTexture(textureProperties,texture,slot){if(texture.image.length!==6)return;let forceUpload=initTexture(textureProperties,texture),source=texture.source;state.bindTexture(_gl.TEXTURE_CUBE_MAP,textureProperties.__webglTexture,_gl.TEXTURE0+slot);let sourceProperties=properties.get(source);if(source.version!==sourceProperties.__version||forceUpload===!0){state.activeTexture(_gl.TEXTURE0+slot);let workingPrimaries=ColorManagement.getPrimaries(ColorManagement.workingColorSpace),texturePrimaries=texture.colorSpace===NoColorSpace?null:ColorManagement.getPrimaries(texture.colorSpace),unpackConversion=texture.colorSpace===NoColorSpace||workingPrimaries===texturePrimaries?_gl.NONE:_gl.BROWSER_DEFAULT_WEBGL;state.pixelStorei(_gl.UNPACK_FLIP_Y_WEBGL,texture.flipY),state.pixelStorei(_gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,texture.premultiplyAlpha),state.pixelStorei(_gl.UNPACK_ALIGNMENT,texture.unpackAlignment),state.pixelStorei(_gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,unpackConversion);let isCompressed=texture.isCompressedTexture||texture.image[0].isCompressedTexture,isDataTexture=texture.image[0]&&texture.image[0].isDataTexture,cubeImage=[];for(let i=0;i<6;i++)!isCompressed&&!isDataTexture?cubeImage[i]=resizeImage(texture.image[i],!0,capabilities.maxCubemapSize):cubeImage[i]=isDataTexture?texture.image[i].image:texture.image[i],cubeImage[i]=verifyColorSpace(texture,cubeImage[i]);let image=cubeImage[0],glFormat=utils.convert(texture.format,texture.colorSpace),glType=utils.convert(texture.type),glInternalFormat=getInternalFormat(texture.internalFormat,glFormat,glType,texture.normalized,texture.colorSpace),useTexStorage=texture.isVideoTexture!==!0,allocateMemory=sourceProperties.__version===void 0||forceUpload===!0,dataReady=source.dataReady,levels=getMipLevels(texture,image);setTextureParameters(_gl.TEXTURE_CUBE_MAP,texture);let mipmaps;if(isCompressed){useTexStorage&&allocateMemory&&state.texStorage2D(_gl.TEXTURE_CUBE_MAP,levels,glInternalFormat,image.width,image.height);for(let i=0;i<6;i++){mipmaps=cubeImage[i].mipmaps;for(let j=0;j<mipmaps.length;j++){let mipmap=mipmaps[j];texture.format!==RGBAFormat?glFormat!==null?useTexStorage?dataReady&&state.compressedTexSubImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,j,0,0,mipmap.width,mipmap.height,glFormat,mipmap.data):state.compressedTexImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,j,glInternalFormat,mipmap.width,mipmap.height,0,mipmap.data):warn("WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):useTexStorage?dataReady&&state.texSubImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,j,0,0,mipmap.width,mipmap.height,glFormat,glType,mipmap.data):state.texImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,j,glInternalFormat,mipmap.width,mipmap.height,0,glFormat,glType,mipmap.data)}}}else{if(mipmaps=texture.mipmaps,useTexStorage&&allocateMemory){mipmaps.length>0&&levels++;let dimensions2=getDimensions(cubeImage[0]);state.texStorage2D(_gl.TEXTURE_CUBE_MAP,levels,glInternalFormat,dimensions2.width,dimensions2.height)}for(let i=0;i<6;i++)if(isDataTexture){useTexStorage?dataReady&&state.texSubImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,0,0,0,cubeImage[i].width,cubeImage[i].height,glFormat,glType,cubeImage[i].data):state.texImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,0,glInternalFormat,cubeImage[i].width,cubeImage[i].height,0,glFormat,glType,cubeImage[i].data);for(let j=0;j<mipmaps.length;j++){let mipmapImage=mipmaps[j].image[i].image;useTexStorage?dataReady&&state.texSubImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,j+1,0,0,mipmapImage.width,mipmapImage.height,glFormat,glType,mipmapImage.data):state.texImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,j+1,glInternalFormat,mipmapImage.width,mipmapImage.height,0,glFormat,glType,mipmapImage.data)}}else{useTexStorage?dataReady&&state.texSubImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,0,0,0,glFormat,glType,cubeImage[i]):state.texImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,0,glInternalFormat,glFormat,glType,cubeImage[i]);for(let j=0;j<mipmaps.length;j++){let mipmap=mipmaps[j];useTexStorage?dataReady&&state.texSubImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,j+1,0,0,glFormat,glType,mipmap.image[i]):state.texImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,j+1,glInternalFormat,glFormat,glType,mipmap.image[i])}}}textureNeedsGenerateMipmaps(texture)&&generateMipmap(_gl.TEXTURE_CUBE_MAP),sourceProperties.__version=source.version,texture.onUpdate&&texture.onUpdate(texture)}textureProperties.__version=texture.version}function setupFrameBufferTexture(framebuffer,renderTarget,texture,attachment,textureTarget,level){let glFormat=utils.convert(texture.format,texture.colorSpace),glType=utils.convert(texture.type),glInternalFormat=getInternalFormat(texture.internalFormat,glFormat,glType,texture.normalized,texture.colorSpace),renderTargetProperties=properties.get(renderTarget),textureProperties=properties.get(texture);if(textureProperties.__renderTarget=renderTarget,!renderTargetProperties.__hasExternalTextures){let width=Math.max(1,renderTarget.width>>level),height=Math.max(1,renderTarget.height>>level);textureTarget===_gl.TEXTURE_3D||textureTarget===_gl.TEXTURE_2D_ARRAY?state.texImage3D(textureTarget,level,glInternalFormat,width,height,renderTarget.depth,0,glFormat,glType,null):state.texImage2D(textureTarget,level,glInternalFormat,width,height,0,glFormat,glType,null)}state.bindFramebuffer(_gl.FRAMEBUFFER,framebuffer),useMultisampledRTT(renderTarget)?multisampledRTTExt.framebufferTexture2DMultisampleEXT(_gl.FRAMEBUFFER,attachment,textureTarget,textureProperties.__webglTexture,0,getRenderTargetSamples(renderTarget)):(textureTarget===_gl.TEXTURE_2D||textureTarget>=_gl.TEXTURE_CUBE_MAP_POSITIVE_X&&textureTarget<=_gl.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&_gl.framebufferTexture2D(_gl.FRAMEBUFFER,attachment,textureTarget,textureProperties.__webglTexture,level),state.bindFramebuffer(_gl.FRAMEBUFFER,null)}function setupRenderBufferStorage(renderbuffer,renderTarget,useMultisample){if(_gl.bindRenderbuffer(_gl.RENDERBUFFER,renderbuffer),renderTarget.depthBuffer){let depthTexture=renderTarget.depthTexture,depthType=depthTexture&&depthTexture.isDepthTexture?depthTexture.type:null,glInternalFormat=getInternalDepthFormat(renderTarget.stencilBuffer,depthType),glAttachmentType=renderTarget.stencilBuffer?_gl.DEPTH_STENCIL_ATTACHMENT:_gl.DEPTH_ATTACHMENT;useMultisampledRTT(renderTarget)?multisampledRTTExt.renderbufferStorageMultisampleEXT(_gl.RENDERBUFFER,getRenderTargetSamples(renderTarget),glInternalFormat,renderTarget.width,renderTarget.height):useMultisample?_gl.renderbufferStorageMultisample(_gl.RENDERBUFFER,getRenderTargetSamples(renderTarget),glInternalFormat,renderTarget.width,renderTarget.height):_gl.renderbufferStorage(_gl.RENDERBUFFER,glInternalFormat,renderTarget.width,renderTarget.height),_gl.framebufferRenderbuffer(_gl.FRAMEBUFFER,glAttachmentType,_gl.RENDERBUFFER,renderbuffer)}else{let textures=renderTarget.textures;for(let i=0;i<textures.length;i++){let texture=textures[i],glFormat=utils.convert(texture.format,texture.colorSpace),glType=utils.convert(texture.type),glInternalFormat=getInternalFormat(texture.internalFormat,glFormat,glType,texture.normalized,texture.colorSpace);useMultisampledRTT(renderTarget)?multisampledRTTExt.renderbufferStorageMultisampleEXT(_gl.RENDERBUFFER,getRenderTargetSamples(renderTarget),glInternalFormat,renderTarget.width,renderTarget.height):useMultisample?_gl.renderbufferStorageMultisample(_gl.RENDERBUFFER,getRenderTargetSamples(renderTarget),glInternalFormat,renderTarget.width,renderTarget.height):_gl.renderbufferStorage(_gl.RENDERBUFFER,glInternalFormat,renderTarget.width,renderTarget.height)}}_gl.bindRenderbuffer(_gl.RENDERBUFFER,null)}function setupDepthTexture(framebuffer,renderTarget,cubeFace){let isCube=renderTarget.isWebGLCubeRenderTarget===!0;if(state.bindFramebuffer(_gl.FRAMEBUFFER,framebuffer),!(renderTarget.depthTexture&&renderTarget.depthTexture.isDepthTexture))throw new Error("THREE.WebGLTextures: renderTarget.depthTexture must be an instance of THREE.DepthTexture.");let textureProperties=properties.get(renderTarget.depthTexture);if(textureProperties.__renderTarget=renderTarget,(!textureProperties.__webglTexture||renderTarget.depthTexture.image.width!==renderTarget.width||renderTarget.depthTexture.image.height!==renderTarget.height)&&(renderTarget.depthTexture.image.width=renderTarget.width,renderTarget.depthTexture.image.height=renderTarget.height,renderTarget.depthTexture.needsUpdate=!0),isCube){if(textureProperties.__webglInit===void 0&&(textureProperties.__webglInit=!0,renderTarget.depthTexture.addEventListener("dispose",onTextureDispose)),textureProperties.__webglTexture===void 0){textureProperties.__webglTexture=_gl.createTexture(),state.bindTexture(_gl.TEXTURE_CUBE_MAP,textureProperties.__webglTexture),setTextureParameters(_gl.TEXTURE_CUBE_MAP,renderTarget.depthTexture);let glFormat=utils.convert(renderTarget.depthTexture.format),glType=utils.convert(renderTarget.depthTexture.type),glInternalFormat;renderTarget.depthTexture.format===DepthFormat?glInternalFormat=_gl.DEPTH_COMPONENT24:renderTarget.depthTexture.format===DepthStencilFormat&&(glInternalFormat=_gl.DEPTH24_STENCIL8);for(let i=0;i<6;i++)_gl.texImage2D(_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,0,glInternalFormat,renderTarget.width,renderTarget.height,0,glFormat,glType,null)}}else setTexture2D(renderTarget.depthTexture,0);let webglDepthTexture=textureProperties.__webglTexture,samples=getRenderTargetSamples(renderTarget),glTextureType=isCube?_gl.TEXTURE_CUBE_MAP_POSITIVE_X+cubeFace:_gl.TEXTURE_2D,glAttachmentType=renderTarget.depthTexture.format===DepthStencilFormat?_gl.DEPTH_STENCIL_ATTACHMENT:_gl.DEPTH_ATTACHMENT;if(renderTarget.depthTexture.format===DepthFormat)useMultisampledRTT(renderTarget)?multisampledRTTExt.framebufferTexture2DMultisampleEXT(_gl.FRAMEBUFFER,glAttachmentType,glTextureType,webglDepthTexture,0,samples):_gl.framebufferTexture2D(_gl.FRAMEBUFFER,glAttachmentType,glTextureType,webglDepthTexture,0);else if(renderTarget.depthTexture.format===DepthStencilFormat)useMultisampledRTT(renderTarget)?multisampledRTTExt.framebufferTexture2DMultisampleEXT(_gl.FRAMEBUFFER,glAttachmentType,glTextureType,webglDepthTexture,0,samples):_gl.framebufferTexture2D(_gl.FRAMEBUFFER,glAttachmentType,glTextureType,webglDepthTexture,0);else throw new Error("THREE.WebGLTextures: Unknown depthTexture format.")}function setupDepthRenderbuffer(renderTarget){let renderTargetProperties=properties.get(renderTarget),isCube=renderTarget.isWebGLCubeRenderTarget===!0;if(renderTargetProperties.__boundDepthTexture!==renderTarget.depthTexture){let depthTexture=renderTarget.depthTexture;if(renderTargetProperties.__depthDisposeCallback&&renderTargetProperties.__depthDisposeCallback(),depthTexture){let disposeEvent=()=>{delete renderTargetProperties.__boundDepthTexture,delete renderTargetProperties.__depthDisposeCallback,depthTexture.removeEventListener("dispose",disposeEvent)};depthTexture.addEventListener("dispose",disposeEvent),renderTargetProperties.__depthDisposeCallback=disposeEvent}renderTargetProperties.__boundDepthTexture=depthTexture}if(renderTarget.depthTexture&&!renderTargetProperties.__autoAllocateDepthBuffer)if(isCube)for(let i=0;i<6;i++)setupDepthTexture(renderTargetProperties.__webglFramebuffer[i],renderTarget,i);else{let mipmaps=renderTarget.texture.mipmaps;mipmaps&&mipmaps.length>0?setupDepthTexture(renderTargetProperties.__webglFramebuffer[0],renderTarget,0):setupDepthTexture(renderTargetProperties.__webglFramebuffer,renderTarget,0)}else if(isCube){renderTargetProperties.__webglDepthbuffer=[];for(let i=0;i<6;i++)if(state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglFramebuffer[i]),renderTargetProperties.__webglDepthbuffer[i]===void 0)renderTargetProperties.__webglDepthbuffer[i]=_gl.createRenderbuffer(),setupRenderBufferStorage(renderTargetProperties.__webglDepthbuffer[i],renderTarget,!1);else{let glAttachmentType=renderTarget.stencilBuffer?_gl.DEPTH_STENCIL_ATTACHMENT:_gl.DEPTH_ATTACHMENT,renderbuffer=renderTargetProperties.__webglDepthbuffer[i];_gl.bindRenderbuffer(_gl.RENDERBUFFER,renderbuffer),_gl.framebufferRenderbuffer(_gl.FRAMEBUFFER,glAttachmentType,_gl.RENDERBUFFER,renderbuffer)}}else{let mipmaps=renderTarget.texture.mipmaps;if(mipmaps&&mipmaps.length>0?state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglFramebuffer[0]):state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglFramebuffer),renderTargetProperties.__webglDepthbuffer===void 0)renderTargetProperties.__webglDepthbuffer=_gl.createRenderbuffer(),setupRenderBufferStorage(renderTargetProperties.__webglDepthbuffer,renderTarget,!1);else{let glAttachmentType=renderTarget.stencilBuffer?_gl.DEPTH_STENCIL_ATTACHMENT:_gl.DEPTH_ATTACHMENT,renderbuffer=renderTargetProperties.__webglDepthbuffer;_gl.bindRenderbuffer(_gl.RENDERBUFFER,renderbuffer),_gl.framebufferRenderbuffer(_gl.FRAMEBUFFER,glAttachmentType,_gl.RENDERBUFFER,renderbuffer)}}state.bindFramebuffer(_gl.FRAMEBUFFER,null)}function rebindTextures(renderTarget,colorTexture,depthTexture){let renderTargetProperties=properties.get(renderTarget);colorTexture!==void 0&&setupFrameBufferTexture(renderTargetProperties.__webglFramebuffer,renderTarget,renderTarget.texture,_gl.COLOR_ATTACHMENT0,_gl.TEXTURE_2D,0),depthTexture!==void 0&&setupDepthRenderbuffer(renderTarget)}function setupRenderTarget(renderTarget){let texture=renderTarget.texture,renderTargetProperties=properties.get(renderTarget),textureProperties=properties.get(texture);renderTarget.addEventListener("dispose",onRenderTargetDispose);let textures=renderTarget.textures,isCube=renderTarget.isWebGLCubeRenderTarget===!0,isMultipleRenderTargets=textures.length>1;if(isMultipleRenderTargets||(textureProperties.__webglTexture===void 0&&(textureProperties.__webglTexture=_gl.createTexture()),textureProperties.__version=texture.version,info.memory.textures++),isCube){renderTargetProperties.__webglFramebuffer=[];for(let i=0;i<6;i++)if(texture.mipmaps&&texture.mipmaps.length>0){renderTargetProperties.__webglFramebuffer[i]=[];for(let level=0;level<texture.mipmaps.length;level++)renderTargetProperties.__webglFramebuffer[i][level]=_gl.createFramebuffer()}else renderTargetProperties.__webglFramebuffer[i]=_gl.createFramebuffer()}else{if(texture.mipmaps&&texture.mipmaps.length>0){renderTargetProperties.__webglFramebuffer=[];for(let level=0;level<texture.mipmaps.length;level++)renderTargetProperties.__webglFramebuffer[level]=_gl.createFramebuffer()}else renderTargetProperties.__webglFramebuffer=_gl.createFramebuffer();if(isMultipleRenderTargets)for(let i=0,il=textures.length;i<il;i++){let attachmentProperties=properties.get(textures[i]);attachmentProperties.__webglTexture===void 0&&(attachmentProperties.__webglTexture=_gl.createTexture(),info.memory.textures++)}if(renderTarget.samples>0&&useMultisampledRTT(renderTarget)===!1){renderTargetProperties.__webglMultisampledFramebuffer=_gl.createFramebuffer(),renderTargetProperties.__webglColorRenderbuffer=[],state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglMultisampledFramebuffer);for(let i=0;i<textures.length;i++){let texture2=textures[i];renderTargetProperties.__webglColorRenderbuffer[i]=_gl.createRenderbuffer(),_gl.bindRenderbuffer(_gl.RENDERBUFFER,renderTargetProperties.__webglColorRenderbuffer[i]);let glFormat=utils.convert(texture2.format,texture2.colorSpace),glType=utils.convert(texture2.type),glInternalFormat=getInternalFormat(texture2.internalFormat,glFormat,glType,texture2.normalized,texture2.colorSpace,renderTarget.isXRRenderTarget===!0),samples=getRenderTargetSamples(renderTarget);_gl.renderbufferStorageMultisample(_gl.RENDERBUFFER,samples,glInternalFormat,renderTarget.width,renderTarget.height),_gl.framebufferRenderbuffer(_gl.FRAMEBUFFER,_gl.COLOR_ATTACHMENT0+i,_gl.RENDERBUFFER,renderTargetProperties.__webglColorRenderbuffer[i])}_gl.bindRenderbuffer(_gl.RENDERBUFFER,null),renderTarget.depthBuffer&&(renderTargetProperties.__webglDepthRenderbuffer=_gl.createRenderbuffer(),setupRenderBufferStorage(renderTargetProperties.__webglDepthRenderbuffer,renderTarget,!0)),state.bindFramebuffer(_gl.FRAMEBUFFER,null)}}if(isCube){state.bindTexture(_gl.TEXTURE_CUBE_MAP,textureProperties.__webglTexture),setTextureParameters(_gl.TEXTURE_CUBE_MAP,texture);for(let i=0;i<6;i++)if(texture.mipmaps&&texture.mipmaps.length>0)for(let level=0;level<texture.mipmaps.length;level++)setupFrameBufferTexture(renderTargetProperties.__webglFramebuffer[i][level],renderTarget,texture,_gl.COLOR_ATTACHMENT0,_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,level);else setupFrameBufferTexture(renderTargetProperties.__webglFramebuffer[i],renderTarget,texture,_gl.COLOR_ATTACHMENT0,_gl.TEXTURE_CUBE_MAP_POSITIVE_X+i,0);textureNeedsGenerateMipmaps(texture)&&generateMipmap(_gl.TEXTURE_CUBE_MAP),state.unbindTexture()}else if(isMultipleRenderTargets){for(let i=0,il=textures.length;i<il;i++){let attachment=textures[i],attachmentProperties=properties.get(attachment),glTextureType=_gl.TEXTURE_2D;(renderTarget.isWebGL3DRenderTarget||renderTarget.isWebGLArrayRenderTarget)&&(glTextureType=renderTarget.isWebGL3DRenderTarget?_gl.TEXTURE_3D:_gl.TEXTURE_2D_ARRAY),state.bindTexture(glTextureType,attachmentProperties.__webglTexture),setTextureParameters(glTextureType,attachment),setupFrameBufferTexture(renderTargetProperties.__webglFramebuffer,renderTarget,attachment,_gl.COLOR_ATTACHMENT0+i,glTextureType,0),textureNeedsGenerateMipmaps(attachment)&&generateMipmap(glTextureType)}state.unbindTexture()}else{let glTextureType=_gl.TEXTURE_2D;if((renderTarget.isWebGL3DRenderTarget||renderTarget.isWebGLArrayRenderTarget)&&(glTextureType=renderTarget.isWebGL3DRenderTarget?_gl.TEXTURE_3D:_gl.TEXTURE_2D_ARRAY),state.bindTexture(glTextureType,textureProperties.__webglTexture),setTextureParameters(glTextureType,texture),texture.mipmaps&&texture.mipmaps.length>0)for(let level=0;level<texture.mipmaps.length;level++)setupFrameBufferTexture(renderTargetProperties.__webglFramebuffer[level],renderTarget,texture,_gl.COLOR_ATTACHMENT0,glTextureType,level);else setupFrameBufferTexture(renderTargetProperties.__webglFramebuffer,renderTarget,texture,_gl.COLOR_ATTACHMENT0,glTextureType,0);textureNeedsGenerateMipmaps(texture)&&generateMipmap(glTextureType),state.unbindTexture()}renderTarget.depthBuffer&&setupDepthRenderbuffer(renderTarget)}function updateRenderTargetMipmap(renderTarget){let textures=renderTarget.textures;for(let i=0,il=textures.length;i<il;i++){let texture=textures[i];if(textureNeedsGenerateMipmaps(texture)){let targetType=getTargetType(renderTarget),webglTexture=properties.get(texture).__webglTexture;state.bindTexture(targetType,webglTexture),generateMipmap(targetType),state.unbindTexture()}}}let invalidationArrayRead=[],invalidationArrayDraw=[];function updateMultisampleRenderTarget(renderTarget){if(renderTarget.samples>0){if(useMultisampledRTT(renderTarget)===!1){let textures=renderTarget.textures,width=renderTarget.width,height=renderTarget.height,mask=_gl.COLOR_BUFFER_BIT,depthStyle=renderTarget.stencilBuffer?_gl.DEPTH_STENCIL_ATTACHMENT:_gl.DEPTH_ATTACHMENT,renderTargetProperties=properties.get(renderTarget),isMultipleRenderTargets=textures.length>1;if(isMultipleRenderTargets)for(let i=0;i<textures.length;i++)state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglMultisampledFramebuffer),_gl.framebufferRenderbuffer(_gl.FRAMEBUFFER,_gl.COLOR_ATTACHMENT0+i,_gl.RENDERBUFFER,null),state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglFramebuffer),_gl.framebufferTexture2D(_gl.DRAW_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0+i,_gl.TEXTURE_2D,null,0);state.bindFramebuffer(_gl.READ_FRAMEBUFFER,renderTargetProperties.__webglMultisampledFramebuffer);let mipmaps=renderTarget.texture.mipmaps;mipmaps&&mipmaps.length>0?state.bindFramebuffer(_gl.DRAW_FRAMEBUFFER,renderTargetProperties.__webglFramebuffer[0]):state.bindFramebuffer(_gl.DRAW_FRAMEBUFFER,renderTargetProperties.__webglFramebuffer);for(let i=0;i<textures.length;i++){if(renderTarget.resolveDepthBuffer&&(renderTarget.depthBuffer&&(mask|=_gl.DEPTH_BUFFER_BIT),renderTarget.stencilBuffer&&renderTarget.resolveStencilBuffer&&(mask|=_gl.STENCIL_BUFFER_BIT)),isMultipleRenderTargets){_gl.framebufferRenderbuffer(_gl.READ_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,_gl.RENDERBUFFER,renderTargetProperties.__webglColorRenderbuffer[i]);let webglTexture=properties.get(textures[i]).__webglTexture;_gl.framebufferTexture2D(_gl.DRAW_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,_gl.TEXTURE_2D,webglTexture,0)}_gl.blitFramebuffer(0,0,width,height,0,0,width,height,mask,_gl.NEAREST),supportsInvalidateFramebuffer===!0&&(invalidationArrayRead.length=0,invalidationArrayDraw.length=0,invalidationArrayRead.push(_gl.COLOR_ATTACHMENT0+i),renderTarget.depthBuffer&&renderTarget.storeMultisampledDepthBuffer===!1&&(invalidationArrayRead.push(depthStyle),invalidationArrayDraw.push(depthStyle),_gl.invalidateFramebuffer(_gl.DRAW_FRAMEBUFFER,invalidationArrayDraw)),_gl.invalidateFramebuffer(_gl.READ_FRAMEBUFFER,invalidationArrayRead))}if(state.bindFramebuffer(_gl.READ_FRAMEBUFFER,null),state.bindFramebuffer(_gl.DRAW_FRAMEBUFFER,null),isMultipleRenderTargets)for(let i=0;i<textures.length;i++){state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglMultisampledFramebuffer),_gl.framebufferRenderbuffer(_gl.FRAMEBUFFER,_gl.COLOR_ATTACHMENT0+i,_gl.RENDERBUFFER,renderTargetProperties.__webglColorRenderbuffer[i]);let webglTexture=properties.get(textures[i]).__webglTexture;state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglFramebuffer),_gl.framebufferTexture2D(_gl.DRAW_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0+i,_gl.TEXTURE_2D,webglTexture,0)}state.bindFramebuffer(_gl.DRAW_FRAMEBUFFER,renderTargetProperties.__webglMultisampledFramebuffer)}else if(renderTarget.depthBuffer&&renderTarget.storeMultisampledDepthBuffer===!1&&supportsInvalidateFramebuffer){let depthStyle=renderTarget.stencilBuffer?_gl.DEPTH_STENCIL_ATTACHMENT:_gl.DEPTH_ATTACHMENT;_gl.invalidateFramebuffer(_gl.DRAW_FRAMEBUFFER,[depthStyle])}}}function getRenderTargetSamples(renderTarget){return Math.min(capabilities.maxSamples,renderTarget.samples)}function useMultisampledRTT(renderTarget){let renderTargetProperties=properties.get(renderTarget);return renderTarget.samples>0&&extensions.has("WEBGL_multisampled_render_to_texture")===!0&&renderTargetProperties.__useRenderToTexture!==!1}function updateVideoTexture(texture){let frame=info.render.frame;_videoTextures.get(texture)!==frame&&(_videoTextures.set(texture,frame),texture.update())}function verifyColorSpace(texture,image){let colorSpace=texture.colorSpace,format=texture.format,type=texture.type;return texture.isCompressedTexture===!0||texture.isVideoTexture===!0||colorSpace!==LinearSRGBColorSpace&&colorSpace!==NoColorSpace&&(ColorManagement.getTransfer(colorSpace)===SRGBTransfer?(format!==RGBAFormat||type!==UnsignedByteType)&&warn("WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):error("WebGLTextures: Unsupported texture color space:",colorSpace)),image}function getDimensions(image){return typeof HTMLImageElement<"u"&&image instanceof HTMLImageElement?(_imageDimensions.width=image.naturalWidth||image.width,_imageDimensions.height=image.naturalHeight||image.height):typeof VideoFrame<"u"&&image instanceof VideoFrame?(_imageDimensions.width=image.displayWidth,_imageDimensions.height=image.displayHeight):(_imageDimensions.width=image.width,_imageDimensions.height=image.height),_imageDimensions}this.allocateTextureUnit=allocateTextureUnit,this.resetTextureUnits=resetTextureUnits,this.getTextureUnits=getTextureUnits,this.setTextureUnits=setTextureUnits,this.setTexture2D=setTexture2D,this.setTexture2DArray=setTexture2DArray,this.setTexture3D=setTexture3D,this.setTextureCube=setTextureCube,this.rebindTextures=rebindTextures,this.setupRenderTarget=setupRenderTarget,this.updateRenderTargetMipmap=updateRenderTargetMipmap,this.updateMultisampleRenderTarget=updateMultisampleRenderTarget,this.setupDepthRenderbuffer=setupDepthRenderbuffer,this.setupFrameBufferTexture=setupFrameBufferTexture,this.useMultisampledRTT=useMultisampledRTT,this.isReversedDepthBuffer=function(){return state.buffers.depth.getReversed()}}function WebGLUtils(gl,extensions){function convert(p,colorSpace=NoColorSpace){let extension,transfer=ColorManagement.getTransfer(colorSpace);if(p===UnsignedByteType)return gl.UNSIGNED_BYTE;if(p===UnsignedShort4444Type)return gl.UNSIGNED_SHORT_4_4_4_4;if(p===UnsignedShort5551Type)return gl.UNSIGNED_SHORT_5_5_5_1;if(p===UnsignedInt5999Type)return gl.UNSIGNED_INT_5_9_9_9_REV;if(p===UnsignedInt101111Type)return gl.UNSIGNED_INT_10F_11F_11F_REV;if(p===ByteType)return gl.BYTE;if(p===ShortType)return gl.SHORT;if(p===UnsignedShortType)return gl.UNSIGNED_SHORT;if(p===IntType)return gl.INT;if(p===UnsignedIntType)return gl.UNSIGNED_INT;if(p===FloatType)return gl.FLOAT;if(p===HalfFloatType)return gl.HALF_FLOAT;if(p===AlphaFormat)return gl.ALPHA;if(p===RGBFormat)return gl.RGB;if(p===RGBAFormat)return gl.RGBA;if(p===DepthFormat)return gl.DEPTH_COMPONENT;if(p===DepthStencilFormat)return gl.DEPTH_STENCIL;if(p===RedFormat)return gl.RED;if(p===RedIntegerFormat)return gl.RED_INTEGER;if(p===RGFormat)return gl.RG;if(p===RGIntegerFormat)return gl.RG_INTEGER;if(p===RGBAIntegerFormat)return gl.RGBA_INTEGER;if(p===RGB_S3TC_DXT1_Format||p===RGBA_S3TC_DXT1_Format||p===RGBA_S3TC_DXT3_Format||p===RGBA_S3TC_DXT5_Format)if(transfer===SRGBTransfer)if(extension=extensions.get("WEBGL_compressed_texture_s3tc_srgb"),extension!==null){if(p===RGB_S3TC_DXT1_Format)return extension.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(p===RGBA_S3TC_DXT1_Format)return extension.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(p===RGBA_S3TC_DXT3_Format)return extension.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(p===RGBA_S3TC_DXT5_Format)return extension.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(extension=extensions.get("WEBGL_compressed_texture_s3tc"),extension!==null){if(p===RGB_S3TC_DXT1_Format)return extension.COMPRESSED_RGB_S3TC_DXT1_EXT;if(p===RGBA_S3TC_DXT1_Format)return extension.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(p===RGBA_S3TC_DXT3_Format)return extension.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(p===RGBA_S3TC_DXT5_Format)return extension.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(p===RGB_PVRTC_4BPPV1_Format||p===RGB_PVRTC_2BPPV1_Format||p===RGBA_PVRTC_4BPPV1_Format||p===RGBA_PVRTC_2BPPV1_Format)if(extension=extensions.get("WEBGL_compressed_texture_pvrtc"),extension!==null){if(p===RGB_PVRTC_4BPPV1_Format)return extension.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(p===RGB_PVRTC_2BPPV1_Format)return extension.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(p===RGBA_PVRTC_4BPPV1_Format)return extension.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(p===RGBA_PVRTC_2BPPV1_Format)return extension.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(p===RGB_ETC1_Format||p===RGB_ETC2_Format||p===RGBA_ETC2_EAC_Format||p===R11_EAC_Format||p===SIGNED_R11_EAC_Format||p===RG11_EAC_Format||p===SIGNED_RG11_EAC_Format)if(extension=extensions.get("WEBGL_compressed_texture_etc"),extension!==null){if(p===RGB_ETC1_Format||p===RGB_ETC2_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ETC2:extension.COMPRESSED_RGB8_ETC2;if(p===RGBA_ETC2_EAC_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:extension.COMPRESSED_RGBA8_ETC2_EAC;if(p===R11_EAC_Format)return extension.COMPRESSED_R11_EAC;if(p===SIGNED_R11_EAC_Format)return extension.COMPRESSED_SIGNED_R11_EAC;if(p===RG11_EAC_Format)return extension.COMPRESSED_RG11_EAC;if(p===SIGNED_RG11_EAC_Format)return extension.COMPRESSED_SIGNED_RG11_EAC}else return null;if(p===RGBA_ASTC_4x4_Format||p===RGBA_ASTC_5x4_Format||p===RGBA_ASTC_5x5_Format||p===RGBA_ASTC_6x5_Format||p===RGBA_ASTC_6x6_Format||p===RGBA_ASTC_8x5_Format||p===RGBA_ASTC_8x6_Format||p===RGBA_ASTC_8x8_Format||p===RGBA_ASTC_10x5_Format||p===RGBA_ASTC_10x6_Format||p===RGBA_ASTC_10x8_Format||p===RGBA_ASTC_10x10_Format||p===RGBA_ASTC_12x10_Format||p===RGBA_ASTC_12x12_Format)if(extension=extensions.get("WEBGL_compressed_texture_astc"),extension!==null){if(p===RGBA_ASTC_4x4_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:extension.COMPRESSED_RGBA_ASTC_4x4_KHR;if(p===RGBA_ASTC_5x4_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:extension.COMPRESSED_RGBA_ASTC_5x4_KHR;if(p===RGBA_ASTC_5x5_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:extension.COMPRESSED_RGBA_ASTC_5x5_KHR;if(p===RGBA_ASTC_6x5_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:extension.COMPRESSED_RGBA_ASTC_6x5_KHR;if(p===RGBA_ASTC_6x6_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:extension.COMPRESSED_RGBA_ASTC_6x6_KHR;if(p===RGBA_ASTC_8x5_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:extension.COMPRESSED_RGBA_ASTC_8x5_KHR;if(p===RGBA_ASTC_8x6_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:extension.COMPRESSED_RGBA_ASTC_8x6_KHR;if(p===RGBA_ASTC_8x8_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:extension.COMPRESSED_RGBA_ASTC_8x8_KHR;if(p===RGBA_ASTC_10x5_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:extension.COMPRESSED_RGBA_ASTC_10x5_KHR;if(p===RGBA_ASTC_10x6_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:extension.COMPRESSED_RGBA_ASTC_10x6_KHR;if(p===RGBA_ASTC_10x8_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:extension.COMPRESSED_RGBA_ASTC_10x8_KHR;if(p===RGBA_ASTC_10x10_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:extension.COMPRESSED_RGBA_ASTC_10x10_KHR;if(p===RGBA_ASTC_12x10_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:extension.COMPRESSED_RGBA_ASTC_12x10_KHR;if(p===RGBA_ASTC_12x12_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:extension.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(p===RGBA_BPTC_Format||p===RGB_BPTC_SIGNED_Format||p===RGB_BPTC_UNSIGNED_Format)if(extension=extensions.get("EXT_texture_compression_bptc"),extension!==null){if(p===RGBA_BPTC_Format)return transfer===SRGBTransfer?extension.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:extension.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(p===RGB_BPTC_SIGNED_Format)return extension.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(p===RGB_BPTC_UNSIGNED_Format)return extension.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(p===RED_RGTC1_Format||p===SIGNED_RED_RGTC1_Format||p===RED_GREEN_RGTC2_Format||p===SIGNED_RED_GREEN_RGTC2_Format)if(extension=extensions.get("EXT_texture_compression_rgtc"),extension!==null){if(p===RED_RGTC1_Format)return extension.COMPRESSED_RED_RGTC1_EXT;if(p===SIGNED_RED_RGTC1_Format)return extension.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(p===RED_GREEN_RGTC2_Format)return extension.COMPRESSED_RED_GREEN_RGTC2_EXT;if(p===SIGNED_RED_GREEN_RGTC2_Format)return extension.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return p===UnsignedInt248Type?gl.UNSIGNED_INT_24_8:gl[p]!==void 0?gl[p]:null}return{convert}}var _occlusion_vertex=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,_occlusion_fragment=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`,WebXRDepthSensing=class{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(depthData,renderState){if(this.texture===null){let texture=new ExternalTexture(depthData.texture);(depthData.depthNear!==renderState.depthNear||depthData.depthFar!==renderState.depthFar)&&(this.depthNear=depthData.depthNear,this.depthFar=depthData.depthFar),this.texture=texture}}getMesh(cameraXR){if(this.texture!==null&&this.mesh===null){let viewport=cameraXR.cameras[0].viewport,material=new ShaderMaterial({vertexShader:_occlusion_vertex,fragmentShader:_occlusion_fragment,uniforms:{depthColor:{value:this.texture},depthWidth:{value:viewport.z},depthHeight:{value:viewport.w}}});this.mesh=new Mesh(new PlaneGeometry(20,20),material)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}};var WebXRManager=class extends EventDispatcher{constructor(renderer,gl){super();let scope=this,session=null,framebufferScaleFactor=1,referenceSpace=null,referenceSpaceType="local-floor",foveation=1,customReferenceSpace=null,pose=null,glBinding=null,glProjLayer=null,glBaseLayer=null,xrFrame=null,supportsGlBinding=typeof XRWebGLBinding<"u",depthSensing=new WebXRDepthSensing,cameraAccessTextures={},attributes=gl.getContextAttributes(),initialRenderTarget=null,newRenderTarget=null,controllers=[],controllerInputSources=[],currentSize=new Vector2,currentPixelRatio=null,currentCameraSettings=null,cameraL=new PerspectiveCamera;cameraL.viewport=new Vector4;let cameraR=new PerspectiveCamera;cameraR.viewport=new Vector4;let cameras=[cameraL,cameraR],cameraXR=new ArrayCamera,_currentDepthNear=null,_currentDepthFar=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(index){let controller=controllers[index];return controller===void 0&&(controller=new WebXRController,controllers[index]=controller),controller.getTargetRaySpace()},this.getControllerGrip=function(index){let controller=controllers[index];return controller===void 0&&(controller=new WebXRController,controllers[index]=controller),controller.getGripSpace()},this.getHand=function(index){let controller=controllers[index];return controller===void 0&&(controller=new WebXRController,controllers[index]=controller),controller.getHandSpace()};function onSessionEvent(event){let controllerIndex=controllerInputSources.indexOf(event.inputSource);if(controllerIndex===-1)return;let controller=controllers[controllerIndex];controller!==void 0&&(controller.update(event.inputSource,event.frame,customReferenceSpace||referenceSpace),controller.dispatchEvent({type:event.type,data:event.inputSource}))}function onSessionEnd(){session.removeEventListener("select",onSessionEvent),session.removeEventListener("selectstart",onSessionEvent),session.removeEventListener("selectend",onSessionEvent),session.removeEventListener("squeeze",onSessionEvent),session.removeEventListener("squeezestart",onSessionEvent),session.removeEventListener("squeezeend",onSessionEvent),session.removeEventListener("end",onSessionEnd),session.removeEventListener("inputsourceschange",onInputSourcesChange);for(let i=0;i<controllers.length;i++){let inputSource=controllerInputSources[i];inputSource!==null&&(controllerInputSources[i]=null,controllers[i].disconnect(inputSource))}_currentDepthNear=null,_currentDepthFar=null,depthSensing.reset();for(let key in cameraAccessTextures)delete cameraAccessTextures[key];if(renderer.setRenderTarget(initialRenderTarget),glBaseLayer=null,glProjLayer=null,glBinding=null,session=null,newRenderTarget=null,animation.stop(),scope.isPresenting=!1,renderer.setPixelRatio(currentPixelRatio),renderer.setSize(currentSize.width,currentSize.height,!1),currentCameraSettings!==null){let camera=currentCameraSettings.camera;camera.fov=currentCameraSettings.fov,camera.zoom=currentCameraSettings.zoom,camera.updateProjectionMatrix(),currentCameraSettings=null}scope.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(value){framebufferScaleFactor=value,scope.isPresenting===!0&&warn("WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(value){referenceSpaceType=value,scope.isPresenting===!0&&warn("WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return customReferenceSpace||referenceSpace},this.setReferenceSpace=function(space){customReferenceSpace=space},this.getBaseLayer=function(){return glProjLayer!==null?glProjLayer:glBaseLayer},this.getBinding=function(){return glBinding===null&&supportsGlBinding&&(glBinding=new XRWebGLBinding(session,gl)),glBinding},this.getFrame=function(){return xrFrame},this.getSession=function(){return session},this.setSession=async function(value){if(session=value,session!==null){if(initialRenderTarget=renderer.getRenderTarget(),session.addEventListener("select",onSessionEvent),session.addEventListener("selectstart",onSessionEvent),session.addEventListener("selectend",onSessionEvent),session.addEventListener("squeeze",onSessionEvent),session.addEventListener("squeezestart",onSessionEvent),session.addEventListener("squeezeend",onSessionEvent),session.addEventListener("end",onSessionEnd),session.addEventListener("inputsourceschange",onInputSourcesChange),attributes.xrCompatible!==!0&&await gl.makeXRCompatible(),currentPixelRatio=renderer.getPixelRatio(),renderer.getSize(currentSize),supportsGlBinding&&"createProjectionLayer"in XRWebGLBinding.prototype){let depthFormat=null,depthType=null,glDepthFormat=null;attributes.depth&&(glDepthFormat=attributes.stencil?gl.DEPTH24_STENCIL8:gl.DEPTH_COMPONENT24,depthFormat=attributes.stencil?DepthStencilFormat:DepthFormat,depthType=attributes.stencil?UnsignedInt248Type:UnsignedIntType);let projectionlayerInit={colorFormat:gl.RGBA8,depthFormat:glDepthFormat,scaleFactor:framebufferScaleFactor};glBinding=this.getBinding(),glProjLayer=glBinding.createProjectionLayer(projectionlayerInit),session.updateRenderState({layers:[glProjLayer]}),renderer.setPixelRatio(1),renderer.setSize(glProjLayer.textureWidth,glProjLayer.textureHeight,!1),newRenderTarget=new WebGLRenderTarget(glProjLayer.textureWidth,glProjLayer.textureHeight,{format:RGBAFormat,type:UnsignedByteType,depthTexture:new DepthTexture(glProjLayer.textureWidth,glProjLayer.textureHeight,depthType,void 0,void 0,void 0,void 0,void 0,void 0,depthFormat),stencilBuffer:attributes.stencil,colorSpace:renderer.outputColorSpace,samples:attributes.antialias?4:0,resolveDepthBuffer:glProjLayer.ignoreDepthValues===!1,resolveStencilBuffer:glProjLayer.ignoreDepthValues===!1,storeMultisampledDepthBuffer:glProjLayer.ignoreDepthValues===!1,storeMultisampledStencilBuffer:glProjLayer.ignoreDepthValues===!1})}else{let layerInit={antialias:attributes.antialias,alpha:!0,depth:attributes.depth,stencil:attributes.stencil,framebufferScaleFactor};glBaseLayer=new XRWebGLLayer(session,gl,layerInit),session.updateRenderState({baseLayer:glBaseLayer}),renderer.setPixelRatio(1),renderer.setSize(glBaseLayer.framebufferWidth,glBaseLayer.framebufferHeight,!1),newRenderTarget=new WebGLRenderTarget(glBaseLayer.framebufferWidth,glBaseLayer.framebufferHeight,{format:RGBAFormat,type:UnsignedByteType,colorSpace:renderer.outputColorSpace,stencilBuffer:attributes.stencil,resolveDepthBuffer:glBaseLayer.ignoreDepthValues===!1,resolveStencilBuffer:glBaseLayer.ignoreDepthValues===!1,storeMultisampledDepthBuffer:glBaseLayer.ignoreDepthValues===!1,storeMultisampledStencilBuffer:glBaseLayer.ignoreDepthValues===!1})}newRenderTarget.isXRRenderTarget=!0,this.setFoveation(foveation),customReferenceSpace=null,referenceSpace=await session.requestReferenceSpace(referenceSpaceType),animation.setContext(session),animation.start(),scope.isPresenting=!0,scope.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(session!==null)return session.environmentBlendMode},this.getDepthTexture=function(){return depthSensing.getDepthTexture()};function onInputSourcesChange(event){for(let i=0;i<event.removed.length;i++){let inputSource=event.removed[i],index=controllerInputSources.indexOf(inputSource);index>=0&&(controllerInputSources[index]=null,controllers[index].disconnect(inputSource))}for(let i=0;i<event.added.length;i++){let inputSource=event.added[i],controllerIndex=controllerInputSources.indexOf(inputSource);if(controllerIndex===-1){for(let i2=0;i2<controllers.length;i2++)if(i2>=controllerInputSources.length){controllerInputSources.push(inputSource),controllerIndex=i2;break}else if(controllerInputSources[i2]===null){controllerInputSources[i2]=inputSource,controllerIndex=i2;break}if(controllerIndex===-1)break}let controller=controllers[controllerIndex];controller&&controller.connect(inputSource)}}let cameraLPos=new Vector3,cameraRPos=new Vector3;function setProjectionFromUnion(camera,cameraL2,cameraR2){cameraLPos.setFromMatrixPosition(cameraL2.matrixWorld),cameraRPos.setFromMatrixPosition(cameraR2.matrixWorld);let ipd=cameraLPos.distanceTo(cameraRPos),projL=cameraL2.projectionMatrix.elements,projR=cameraR2.projectionMatrix.elements,near=projL[14]/(projL[10]-1),far=projL[14]/(projL[10]+1),topFov=(projL[9]+1)/projL[5],bottomFov=(projL[9]-1)/projL[5],leftFov=(projL[8]-1)/projL[0],rightFov=(projR[8]+1)/projR[0],left=near*leftFov,right=near*rightFov,zOffset=ipd/(-leftFov+rightFov),xOffset=zOffset*-leftFov;if(cameraL2.matrixWorld.decompose(camera.position,camera.quaternion,camera.scale),camera.translateX(xOffset),camera.translateZ(zOffset),camera.matrixWorld.compose(camera.position,camera.quaternion,camera.scale),camera.matrixWorldInverse.copy(camera.matrixWorld).invert(),projL[10]===-1)camera.projectionMatrix.copy(cameraL2.projectionMatrix),camera.projectionMatrixInverse.copy(cameraL2.projectionMatrixInverse);else{let near2=near+zOffset,far2=far+zOffset,left2=left-xOffset,right2=right+(ipd-xOffset),top2=topFov*far/far2*near2,bottom2=bottomFov*far/far2*near2;camera.projectionMatrix.makePerspective(left2,right2,top2,bottom2,near2,far2),camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert()}}function updateCamera(camera,parent){parent===null?camera.matrixWorld.copy(camera.matrix):camera.matrixWorld.multiplyMatrices(parent.matrixWorld,camera.matrix),camera.matrixWorldInverse.copy(camera.matrixWorld).invert()}this.updateCamera=function(camera){if(session===null)return;let depthNear=camera.near,depthFar=camera.far;depthSensing.texture!==null&&(depthSensing.depthNear>0&&(depthNear=depthSensing.depthNear),depthSensing.depthFar>0&&(depthFar=depthSensing.depthFar)),cameraXR.near=cameraR.near=cameraL.near=depthNear,cameraXR.far=cameraR.far=cameraL.far=depthFar,(_currentDepthNear!==cameraXR.near||_currentDepthFar!==cameraXR.far)&&(session.updateRenderState({depthNear:cameraXR.near,depthFar:cameraXR.far}),_currentDepthNear=cameraXR.near,_currentDepthFar=cameraXR.far),cameraXR.layers.mask=camera.layers.mask|6,cameraL.layers.mask=cameraXR.layers.mask&-5,cameraR.layers.mask=cameraXR.layers.mask&-3;let parent=camera.parent,cameras2=cameraXR.cameras;updateCamera(cameraXR,parent);for(let i=0;i<cameras2.length;i++)updateCamera(cameras2[i],parent);cameras2.length===2?setProjectionFromUnion(cameraXR,cameraL,cameraR):cameraXR.projectionMatrix.copy(cameraL.projectionMatrix),currentCameraSettings===null&&camera.isPerspectiveCamera&&(currentCameraSettings={camera,fov:camera.fov,zoom:camera.zoom}),updateUserCamera(camera,cameraXR,parent)};function updateUserCamera(camera,cameraXR2,parent){parent===null?camera.matrix.copy(cameraXR2.matrixWorld):(camera.matrix.copy(parent.matrixWorld),camera.matrix.invert(),camera.matrix.multiply(cameraXR2.matrixWorld)),camera.matrix.decompose(camera.position,camera.quaternion,camera.scale),camera.updateMatrixWorld(!0),camera.projectionMatrix.copy(cameraXR2.projectionMatrix),camera.projectionMatrixInverse.copy(cameraXR2.projectionMatrixInverse),camera.isPerspectiveCamera&&(camera.fov=RAD2DEG*2*Math.atan(1/camera.projectionMatrix.elements[5]),camera.zoom=1)}this.getCamera=function(){return cameraXR},this.getFoveation=function(){if(!(glProjLayer===null&&glBaseLayer===null))return foveation},this.setFoveation=function(value){foveation=value,glProjLayer!==null&&(glProjLayer.fixedFoveation=value),glBaseLayer!==null&&glBaseLayer.fixedFoveation!==void 0&&(glBaseLayer.fixedFoveation=value)},this.hasDepthSensing=function(){return depthSensing.texture!==null},this.getDepthSensingMesh=function(){return depthSensing.getMesh(cameraXR)},this.getCameraTexture=function(xrCamera){return cameraAccessTextures[xrCamera]};let onAnimationFrameCallback=null;function onAnimationFrame(time,frame){if(pose=frame.getViewerPose(customReferenceSpace||referenceSpace),xrFrame=frame,pose!==null){let views=pose.views;glBaseLayer!==null&&(renderer.setRenderTargetFramebuffer(newRenderTarget,glBaseLayer.framebuffer),renderer.setRenderTarget(newRenderTarget));let cameraXRNeedsUpdate=!1;views.length!==cameraXR.cameras.length&&(cameraXR.cameras.length=0,cameraXRNeedsUpdate=!0);for(let i=0;i<views.length;i++){let view=views[i],viewport=null;if(glBaseLayer!==null)viewport=glBaseLayer.getViewport(view);else{let glSubImage=glBinding.getViewSubImage(glProjLayer,view);viewport=glSubImage.viewport,i===0&&(renderer.setRenderTargetTextures(newRenderTarget,glSubImage.colorTexture,glSubImage.depthStencilTexture),renderer.setRenderTarget(newRenderTarget))}let camera=cameras[i];camera===void 0&&(camera=new PerspectiveCamera,camera.layers.enable(i),camera.viewport=new Vector4,cameras[i]=camera),camera.matrix.fromArray(view.transform.matrix),camera.matrix.decompose(camera.position,camera.quaternion,camera.scale),camera.projectionMatrix.fromArray(view.projectionMatrix),camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert(),camera.viewport.set(viewport.x,viewport.y,viewport.width,viewport.height),i===0&&(cameraXR.matrix.copy(camera.matrix),cameraXR.matrix.decompose(cameraXR.position,cameraXR.quaternion,cameraXR.scale)),cameraXRNeedsUpdate===!0&&cameraXR.cameras.push(camera)}let enabledFeatures=session.enabledFeatures;if(enabledFeatures&&enabledFeatures.includes("depth-sensing")&&session.depthUsage=="gpu-optimized"&&supportsGlBinding){glBinding=scope.getBinding();let depthData=glBinding.getDepthInformation(views[0]);depthData&&depthData.isValid&&depthData.texture&&depthSensing.init(depthData,session.renderState)}if(enabledFeatures&&enabledFeatures.includes("camera-access")&&supportsGlBinding){renderer.state.unbindTexture(),glBinding=scope.getBinding();for(let i=0;i<views.length;i++){let camera=views[i].camera;if(camera){let cameraTex=cameraAccessTextures[camera];cameraTex||(cameraTex=new ExternalTexture,cameraAccessTextures[camera]=cameraTex);let glTexture=glBinding.getCameraImage(camera);cameraTex.sourceTexture=glTexture}}}}for(let i=0;i<controllers.length;i++){let inputSource=controllerInputSources[i],controller=controllers[i];inputSource!==null&&controller!==void 0&&controller.update(inputSource,frame,customReferenceSpace||referenceSpace)}onAnimationFrameCallback&&onAnimationFrameCallback(time,frame),frame.detectedPlanes&&scope.dispatchEvent({type:"planesdetected",data:frame}),xrFrame=null}let animation=new WebGLAnimation;animation.setAnimationLoop(onAnimationFrame),this.setAnimationLoop=function(callback){onAnimationFrameCallback=callback},this.dispose=function(){}}};var _m15=new Matrix4,_m2=new Matrix3;_m2.set(-1,0,0,0,1,0,0,0,1);function WebGLMaterials(renderer,properties){function refreshTransformUniform(map,uniform){map.matrixAutoUpdate===!0&&map.updateMatrix(),uniform.value.copy(map.matrix)}function refreshFogUniforms(uniforms,fog){fog.color.getRGB(uniforms.fogColor.value,getUnlitUniformColorSpace(renderer)),fog.isFog?(uniforms.fogNear.value=fog.near,uniforms.fogFar.value=fog.far):fog.isFogExp2&&(uniforms.fogDensity.value=fog.density)}function refreshMaterialUniforms(uniforms,material,pixelRatio,height,transmissionRenderTarget){material.isNodeMaterial?material.uniformsNeedUpdate=!1:material.isMeshBasicMaterial?refreshUniformsCommon(uniforms,material):material.isMeshLambertMaterial?(refreshUniformsCommon(uniforms,material),material.envMap&&(uniforms.envMapIntensity.value=material.envMapIntensity)):material.isMeshToonMaterial?(refreshUniformsCommon(uniforms,material),refreshUniformsToon(uniforms,material)):material.isMeshPhongMaterial?(refreshUniformsCommon(uniforms,material),refreshUniformsPhong(uniforms,material),material.envMap&&(uniforms.envMapIntensity.value=material.envMapIntensity)):material.isMeshStandardMaterial?(refreshUniformsCommon(uniforms,material),refreshUniformsStandard(uniforms,material),material.isMeshPhysicalMaterial&&refreshUniformsPhysical(uniforms,material,transmissionRenderTarget)):material.isMeshMatcapMaterial?(refreshUniformsCommon(uniforms,material),refreshUniformsMatcap(uniforms,material)):material.isMeshDepthMaterial?refreshUniformsCommon(uniforms,material):material.isMeshDistanceMaterial?(refreshUniformsCommon(uniforms,material),refreshUniformsDistance(uniforms,material)):material.isMeshNormalMaterial?refreshUniformsCommon(uniforms,material):material.isLineBasicMaterial?(refreshUniformsLine(uniforms,material),material.isLineDashedMaterial&&refreshUniformsDash(uniforms,material)):material.isPointsMaterial?refreshUniformsPoints(uniforms,material,pixelRatio,height):material.isSpriteMaterial?refreshUniformsSprites(uniforms,material):material.isShadowMaterial?(uniforms.color.value.copy(material.color),uniforms.opacity.value=material.opacity):material.isShaderMaterial&&(material.uniformsNeedUpdate=!1)}function refreshUniformsCommon(uniforms,material){uniforms.opacity.value=material.opacity,material.color&&uniforms.diffuse.value.copy(material.color),material.emissive&&uniforms.emissive.value.copy(material.emissive).multiplyScalar(material.emissiveIntensity),material.map&&(uniforms.map.value=material.map,refreshTransformUniform(material.map,uniforms.mapTransform)),material.alphaMap&&(uniforms.alphaMap.value=material.alphaMap,refreshTransformUniform(material.alphaMap,uniforms.alphaMapTransform)),material.bumpMap&&(uniforms.bumpMap.value=material.bumpMap,refreshTransformUniform(material.bumpMap,uniforms.bumpMapTransform),uniforms.bumpScale.value=material.bumpScale,material.side===BackSide&&(uniforms.bumpScale.value*=-1)),material.normalMap&&(uniforms.normalMap.value=material.normalMap,refreshTransformUniform(material.normalMap,uniforms.normalMapTransform),uniforms.normalScale.value.copy(material.normalScale),material.side===BackSide&&uniforms.normalScale.value.negate()),material.displacementMap&&(uniforms.displacementMap.value=material.displacementMap,refreshTransformUniform(material.displacementMap,uniforms.displacementMapTransform),uniforms.displacementScale.value=material.displacementScale,uniforms.displacementBias.value=material.displacementBias),material.emissiveMap&&(uniforms.emissiveMap.value=material.emissiveMap,refreshTransformUniform(material.emissiveMap,uniforms.emissiveMapTransform)),material.specularMap&&(uniforms.specularMap.value=material.specularMap,refreshTransformUniform(material.specularMap,uniforms.specularMapTransform)),material.alphaTest>0&&(uniforms.alphaTest.value=material.alphaTest);let materialProperties=properties.get(material),envMap=materialProperties.envMap,envMapRotation=materialProperties.envMapRotation;envMap&&(uniforms.envMap.value=envMap,uniforms.envMapRotation.value.setFromMatrix4(_m15.makeRotationFromEuler(envMapRotation)).transpose(),envMap.isCubeTexture&&envMap.isRenderTargetTexture===!1&&uniforms.envMapRotation.value.premultiply(_m2),uniforms.reflectivity.value=material.reflectivity,uniforms.ior.value=material.ior,uniforms.refractionRatio.value=material.refractionRatio),material.lightMap&&(uniforms.lightMap.value=material.lightMap,uniforms.lightMapIntensity.value=material.lightMapIntensity,refreshTransformUniform(material.lightMap,uniforms.lightMapTransform)),material.aoMap&&(uniforms.aoMap.value=material.aoMap,uniforms.aoMapIntensity.value=material.aoMapIntensity,refreshTransformUniform(material.aoMap,uniforms.aoMapTransform))}function refreshUniformsLine(uniforms,material){uniforms.diffuse.value.copy(material.color),uniforms.opacity.value=material.opacity,material.map&&(uniforms.map.value=material.map,refreshTransformUniform(material.map,uniforms.mapTransform))}function refreshUniformsDash(uniforms,material){uniforms.dashSize.value=material.dashSize,uniforms.totalSize.value=material.dashSize+material.gapSize,uniforms.scale.value=material.scale}function refreshUniformsPoints(uniforms,material,pixelRatio,height){uniforms.diffuse.value.copy(material.color),uniforms.opacity.value=material.opacity,uniforms.size.value=material.size*pixelRatio,uniforms.scale.value=height*.5,material.map&&(uniforms.map.value=material.map,refreshTransformUniform(material.map,uniforms.uvTransform)),material.alphaMap&&(uniforms.alphaMap.value=material.alphaMap,refreshTransformUniform(material.alphaMap,uniforms.alphaMapTransform)),material.alphaTest>0&&(uniforms.alphaTest.value=material.alphaTest)}function refreshUniformsSprites(uniforms,material){uniforms.diffuse.value.copy(material.color),uniforms.opacity.value=material.opacity,uniforms.rotation.value=material.rotation,material.map&&(uniforms.map.value=material.map,refreshTransformUniform(material.map,uniforms.mapTransform)),material.alphaMap&&(uniforms.alphaMap.value=material.alphaMap,refreshTransformUniform(material.alphaMap,uniforms.alphaMapTransform)),material.alphaTest>0&&(uniforms.alphaTest.value=material.alphaTest)}function refreshUniformsPhong(uniforms,material){uniforms.specular.value.copy(material.specular),uniforms.shininess.value=Math.max(material.shininess,1e-4)}function refreshUniformsToon(uniforms,material){material.gradientMap&&(uniforms.gradientMap.value=material.gradientMap)}function refreshUniformsStandard(uniforms,material){uniforms.metalness.value=material.metalness,material.metalnessMap&&(uniforms.metalnessMap.value=material.metalnessMap,refreshTransformUniform(material.metalnessMap,uniforms.metalnessMapTransform)),uniforms.roughness.value=material.roughness,material.roughnessMap&&(uniforms.roughnessMap.value=material.roughnessMap,refreshTransformUniform(material.roughnessMap,uniforms.roughnessMapTransform)),material.envMap&&(uniforms.envMapIntensity.value=material.envMapIntensity)}function refreshUniformsPhysical(uniforms,material,transmissionRenderTarget){uniforms.ior.value=material.ior,material.sheen>0&&(uniforms.sheenColor.value.copy(material.sheenColor).multiplyScalar(material.sheen),uniforms.sheenRoughness.value=material.sheenRoughness,material.sheenColorMap&&(uniforms.sheenColorMap.value=material.sheenColorMap,refreshTransformUniform(material.sheenColorMap,uniforms.sheenColorMapTransform)),material.sheenRoughnessMap&&(uniforms.sheenRoughnessMap.value=material.sheenRoughnessMap,refreshTransformUniform(material.sheenRoughnessMap,uniforms.sheenRoughnessMapTransform))),material.clearcoat>0&&(uniforms.clearcoat.value=material.clearcoat,uniforms.clearcoatRoughness.value=material.clearcoatRoughness,material.clearcoatMap&&(uniforms.clearcoatMap.value=material.clearcoatMap,refreshTransformUniform(material.clearcoatMap,uniforms.clearcoatMapTransform)),material.clearcoatRoughnessMap&&(uniforms.clearcoatRoughnessMap.value=material.clearcoatRoughnessMap,refreshTransformUniform(material.clearcoatRoughnessMap,uniforms.clearcoatRoughnessMapTransform)),material.clearcoatNormalMap&&(uniforms.clearcoatNormalMap.value=material.clearcoatNormalMap,refreshTransformUniform(material.clearcoatNormalMap,uniforms.clearcoatNormalMapTransform),uniforms.clearcoatNormalScale.value.copy(material.clearcoatNormalScale),material.side===BackSide&&uniforms.clearcoatNormalScale.value.negate())),material.dispersion>0&&(uniforms.dispersion.value=material.dispersion),material.retroreflectivity>0&&(uniforms.retroreflectivity.value=material.retroreflectivity),material.iridescence>0&&(uniforms.iridescence.value=material.iridescence,uniforms.iridescenceIOR.value=material.iridescenceIOR,uniforms.iridescenceThicknessMinimum.value=material.iridescenceThicknessRange[0],uniforms.iridescenceThicknessMaximum.value=material.iridescenceThicknessRange[1],material.iridescenceMap&&(uniforms.iridescenceMap.value=material.iridescenceMap,refreshTransformUniform(material.iridescenceMap,uniforms.iridescenceMapTransform)),material.iridescenceThicknessMap&&(uniforms.iridescenceThicknessMap.value=material.iridescenceThicknessMap,refreshTransformUniform(material.iridescenceThicknessMap,uniforms.iridescenceThicknessMapTransform))),material.transmission>0&&(uniforms.transmission.value=material.transmission,uniforms.transmissionSamplerMap.value=transmissionRenderTarget.texture,uniforms.transmissionSamplerSize.value.set(transmissionRenderTarget.width,transmissionRenderTarget.height),material.transmissionMap&&(uniforms.transmissionMap.value=material.transmissionMap,refreshTransformUniform(material.transmissionMap,uniforms.transmissionMapTransform)),uniforms.thickness.value=material.thickness,material.thicknessMap&&(uniforms.thicknessMap.value=material.thicknessMap,refreshTransformUniform(material.thicknessMap,uniforms.thicknessMapTransform)),uniforms.attenuationDistance.value=material.attenuationDistance,uniforms.attenuationColor.value.copy(material.attenuationColor)),material.anisotropy>0&&(uniforms.anisotropyVector.value.set(material.anisotropy*Math.cos(material.anisotropyRotation),material.anisotropy*Math.sin(material.anisotropyRotation)),material.anisotropyMap&&(uniforms.anisotropyMap.value=material.anisotropyMap,refreshTransformUniform(material.anisotropyMap,uniforms.anisotropyMapTransform))),uniforms.specularIntensity.value=material.specularIntensity,uniforms.specularColor.value.copy(material.specularColor),material.specularColorMap&&(uniforms.specularColorMap.value=material.specularColorMap,refreshTransformUniform(material.specularColorMap,uniforms.specularColorMapTransform)),material.specularIntensityMap&&(uniforms.specularIntensityMap.value=material.specularIntensityMap,refreshTransformUniform(material.specularIntensityMap,uniforms.specularIntensityMapTransform))}function refreshUniformsMatcap(uniforms,material){material.matcap&&(uniforms.matcap.value=material.matcap)}function refreshUniformsDistance(uniforms,material){let light=properties.get(material).light;uniforms.referencePosition.value.setFromMatrixPosition(light.matrixWorld),uniforms.nearDistance.value=light.shadow.camera.near,uniforms.farDistance.value=light.shadow.camera.far}return{refreshFogUniforms,refreshMaterialUniforms}}function WebGLUniformsGroups(gl,info,capabilities,state){let buffers={},updateList={},allocatedBindingPoints=[],maxBindingPoints=gl.getParameter(gl.MAX_UNIFORM_BUFFER_BINDINGS);function bind(uniformsGroup,program){let webglProgram=program.program;state.uniformBlockBinding(uniformsGroup,webglProgram)}function update(uniformsGroup,program){let buffer=buffers[uniformsGroup.id];buffer===void 0&&(prepareUniformsGroup(uniformsGroup),buffer=createBuffer(uniformsGroup),buffers[uniformsGroup.id]=buffer,uniformsGroup.addEventListener("dispose",onUniformsGroupsDispose));let webglProgram=program.program;state.updateUBOMapping(uniformsGroup,webglProgram);let frame=info.render.frame;updateList[uniformsGroup.id]!==frame&&(updateBufferData(uniformsGroup),updateList[uniformsGroup.id]=frame)}function createBuffer(uniformsGroup){let bindingPointIndex=allocateBindingPointIndex();uniformsGroup.__bindingPointIndex=bindingPointIndex;let buffer=gl.createBuffer(),size=uniformsGroup.__size,usage=uniformsGroup.usage;return gl.bindBuffer(gl.UNIFORM_BUFFER,buffer),gl.bufferData(gl.UNIFORM_BUFFER,size,usage),gl.bindBuffer(gl.UNIFORM_BUFFER,null),gl.bindBufferBase(gl.UNIFORM_BUFFER,bindingPointIndex,buffer),buffer}function allocateBindingPointIndex(){for(let i=0;i<maxBindingPoints;i++)if(allocatedBindingPoints.indexOf(i)===-1)return allocatedBindingPoints.push(i),i;return error("WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function updateBufferData(uniformsGroup){let buffer=buffers[uniformsGroup.id],uniforms=uniformsGroup.uniforms,cache=uniformsGroup.__cache;gl.bindBuffer(gl.UNIFORM_BUFFER,buffer);for(let i=0,il=uniforms.length;i<il;i++){let uniformItem=uniforms[i];if(Array.isArray(uniformItem))for(let j=0,jl=uniformItem.length;j<jl;j++)updateUniform(uniformItem[j],i,j,cache);else updateUniform(uniformItem,i,0,cache)}gl.bindBuffer(gl.UNIFORM_BUFFER,null)}function updateUniform(uniform,index,indexArray,cache){if(hasUniformChanged(uniform,index,indexArray,cache)===!0){let offset=uniform.__offset,value=uniform.value;if(Array.isArray(value)){let arrayOffset=0;for(let k=0;k<value.length;k++){let val=value[k],info2=getUniformSize(val);writeUniformValue(val,uniform.__data,arrayOffset),typeof val!="number"&&typeof val!="boolean"&&!val.isMatrix3&&!ArrayBuffer.isView(val)&&(arrayOffset+=info2.storage/Float32Array.BYTES_PER_ELEMENT)}}else writeUniformValue(value,uniform.__data,0);gl.bufferSubData(gl.UNIFORM_BUFFER,offset,uniform.__data)}}function writeUniformValue(value,data,offset){typeof value=="number"||typeof value=="boolean"?data[0]=value:value.isMatrix3?(data[0]=value.elements[0],data[1]=value.elements[1],data[2]=value.elements[2],data[3]=0,data[4]=value.elements[3],data[5]=value.elements[4],data[6]=value.elements[5],data[7]=0,data[8]=value.elements[6],data[9]=value.elements[7],data[10]=value.elements[8],data[11]=0):ArrayBuffer.isView(value)?data.set(new value.constructor(value.buffer,value.byteOffset,data.length)):value.toArray(data,offset)}function hasUniformChanged(uniform,index,indexArray,cache){let value=uniform.value,indexString=index+"_"+indexArray;if(cache[indexString]===void 0)return typeof value=="number"||typeof value=="boolean"?cache[indexString]=value:ArrayBuffer.isView(value)?cache[indexString]=value.slice():cache[indexString]=value.clone(),!0;{let cachedObject=cache[indexString];if(typeof value=="number"||typeof value=="boolean"){if(cachedObject!==value)return cache[indexString]=value,!0}else{if(ArrayBuffer.isView(value))return!0;if(cachedObject.equals(value)===!1)return cachedObject.copy(value),!0}}return!1}function prepareUniformsGroup(uniformsGroup){let uniforms=uniformsGroup.uniforms,offset=0,chunkSize=16;for(let i=0,l=uniforms.length;i<l;i++){let uniformArray=Array.isArray(uniforms[i])?uniforms[i]:[uniforms[i]];for(let j=0,jl=uniformArray.length;j<jl;j++){let uniform=uniformArray[j],values=Array.isArray(uniform.value)?uniform.value:[uniform.value];for(let k=0,kl=values.length;k<kl;k++){let value=values[k],info2=getUniformSize(value),chunkOffset2=offset%chunkSize,chunkPadding=chunkOffset2%info2.boundary,chunkStart=chunkOffset2+chunkPadding;offset+=chunkPadding,chunkStart!==0&&chunkSize-chunkStart<info2.storage&&(offset+=chunkSize-chunkStart),uniform.__data=new Float32Array(info2.storage/Float32Array.BYTES_PER_ELEMENT),uniform.__offset=offset,offset+=info2.storage}}}let chunkOffset=offset%chunkSize;return chunkOffset>0&&(offset+=chunkSize-chunkOffset),uniformsGroup.__size=offset,uniformsGroup.__cache={},this}function getUniformSize(value){let info2={boundary:0,storage:0};return typeof value=="number"||typeof value=="boolean"?(info2.boundary=4,info2.storage=4):value.isVector2?(info2.boundary=8,info2.storage=8):value.isVector3||value.isColor?(info2.boundary=16,info2.storage=12):value.isVector4?(info2.boundary=16,info2.storage=16):value.isMatrix3?(info2.boundary=48,info2.storage=48):value.isMatrix4?(info2.boundary=64,info2.storage=64):value.isTexture?warn("WebGLRenderer: Texture samplers can not be part of an uniforms group."):ArrayBuffer.isView(value)?(info2.boundary=16,info2.storage=value.byteLength):warn("WebGLRenderer: Unsupported uniform value type.",value),info2}function onUniformsGroupsDispose(event){let uniformsGroup=event.target;uniformsGroup.removeEventListener("dispose",onUniformsGroupsDispose);let index=allocatedBindingPoints.indexOf(uniformsGroup.__bindingPointIndex);allocatedBindingPoints.splice(index,1),gl.deleteBuffer(buffers[uniformsGroup.id]),delete buffers[uniformsGroup.id],delete updateList[uniformsGroup.id]}function dispose(){for(let id in buffers)gl.deleteBuffer(buffers[id]);allocatedBindingPoints=[],buffers={},updateList={}}return{bind,update,dispose}}var DATA=new Uint16Array([12469,15057,12620,14925,13266,14620,13807,14376,14323,13990,14545,13625,14713,13328,14840,12882,14931,12528,14996,12233,15039,11829,15066,11525,15080,11295,15085,10976,15082,10705,15073,10495,13880,14564,13898,14542,13977,14430,14158,14124,14393,13732,14556,13410,14702,12996,14814,12596,14891,12291,14937,11834,14957,11489,14958,11194,14943,10803,14921,10506,14893,10278,14858,9960,14484,14039,14487,14025,14499,13941,14524,13740,14574,13468,14654,13106,14743,12678,14818,12344,14867,11893,14889,11509,14893,11180,14881,10751,14852,10428,14812,10128,14765,9754,14712,9466,14764,13480,14764,13475,14766,13440,14766,13347,14769,13070,14786,12713,14816,12387,14844,11957,14860,11549,14868,11215,14855,10751,14825,10403,14782,10044,14729,9651,14666,9352,14599,9029,14967,12835,14966,12831,14963,12804,14954,12723,14936,12564,14917,12347,14900,11958,14886,11569,14878,11247,14859,10765,14828,10401,14784,10011,14727,9600,14660,9289,14586,8893,14508,8533,15111,12234,15110,12234,15104,12216,15092,12156,15067,12010,15028,11776,14981,11500,14942,11205,14902,10752,14861,10393,14812,9991,14752,9570,14682,9252,14603,8808,14519,8445,14431,8145,15209,11449,15208,11451,15202,11451,15190,11438,15163,11384,15117,11274,15055,10979,14994,10648,14932,10343,14871,9936,14803,9532,14729,9218,14645,8742,14556,8381,14461,8020,14365,7603,15273,10603,15272,10607,15267,10619,15256,10631,15231,10614,15182,10535,15118,10389,15042,10167,14963,9787,14883,9447,14800,9115,14710,8665,14615,8318,14514,7911,14411,7507,14279,7198,15314,9675,15313,9683,15309,9712,15298,9759,15277,9797,15229,9773,15166,9668,15084,9487,14995,9274,14898,8910,14800,8539,14697,8234,14590,7790,14479,7409,14367,7067,14178,6621,15337,8619,15337,8631,15333,8677,15325,8769,15305,8871,15264,8940,15202,8909,15119,8775,15022,8565,14916,8328,14804,8009,14688,7614,14569,7287,14448,6888,14321,6483,14088,6171,15350,7402,15350,7419,15347,7480,15340,7613,15322,7804,15287,7973,15229,8057,15148,8012,15046,7846,14933,7611,14810,7357,14682,7069,14552,6656,14421,6316,14251,5948,14007,5528,15356,5942,15356,5977,15353,6119,15348,6294,15332,6551,15302,6824,15249,7044,15171,7122,15070,7050,14949,6861,14818,6611,14679,6349,14538,6067,14398,5651,14189,5311,13935,4958,15359,4123,15359,4153,15356,4296,15353,4646,15338,5160,15311,5508,15263,5829,15188,6042,15088,6094,14966,6001,14826,5796,14678,5543,14527,5287,14377,4985,14133,4586,13869,4257,15360,1563,15360,1642,15358,2076,15354,2636,15341,3350,15317,4019,15273,4429,15203,4732,15105,4911,14981,4932,14836,4818,14679,4621,14517,4386,14359,4156,14083,3795,13808,3437,15360,122,15360,137,15358,285,15355,636,15344,1274,15322,2177,15281,2765,15215,3223,15120,3451,14995,3569,14846,3567,14681,3466,14511,3305,14344,3121,14037,2800,13753,2467,15360,0,15360,1,15359,21,15355,89,15346,253,15325,479,15287,796,15225,1148,15133,1492,15008,1749,14856,1882,14685,1886,14506,1783,14324,1608,13996,1398,13702,1183]),lut=null;function getDFGLUT(){return lut===null&&(lut=new DataTexture(DATA,16,16,RGFormat,HalfFloatType),lut.name="DFG_LUT",lut.minFilter=LinearFilter,lut.magFilter=LinearFilter,lut.wrapS=ClampToEdgeWrapping,lut.wrapT=ClampToEdgeWrapping,lut.generateMipmaps=!1,lut.needsUpdate=!0),lut}var WebGLRenderer=class{constructor(parameters={}){let{canvas=createCanvasElement(),context=null,depth=!0,stencil=!1,alpha=!1,antialias=!1,premultipliedAlpha=!0,preserveDrawingBuffer=!1,powerPreference="default",failIfMajorPerformanceCaveat=!1,reversedDepthBuffer=!1,outputBufferType=UnsignedByteType}=parameters;this.isWebGLRenderer=!0;let _alpha;if(context!==null){if(typeof WebGLRenderingContext<"u"&&context instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");_alpha=context.getContextAttributes().alpha}else _alpha=alpha;let _outputBufferType=outputBufferType,INTEGER_FORMATS=new Set([RGBAIntegerFormat,RGIntegerFormat,RedIntegerFormat]),UNSIGNED_TYPES=new Set([UnsignedByteType,UnsignedIntType,UnsignedShortType,UnsignedInt248Type,UnsignedShort4444Type,UnsignedShort5551Type]),uintClearColor=new Uint32Array(4),intClearColor=new Int32Array(4),objectPosition=new Vector3,currentRenderList=null,currentRenderState=null,renderListStack=[],renderStateStack=[],output=null;this.domElement=canvas,this.debug={checkShaderErrors:!0,diagnostics:{keywords:!1},onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this.toneMapping=NoToneMapping,this.toneMappingExposure=1,this.transmissionResolutionScale=1;let _this=this,_isContextLost=!1,_nodesHandler=null,_scratchFramebuffer=null,_srcFramebuffer=null,_dstFramebuffer=null;this._outputColorSpace=SRGBColorSpace;let _currentActiveCubeFace=0,_currentActiveMipmapLevel=0,_currentRenderTarget=null,_currentMaterialId=-1,_currentCamera=null,_currentViewport=new Vector4,_currentScissor=new Vector4,_currentScissorTest=null,_currentClearColor=new Color(0),_currentClearAlpha=0,_width=canvas.width,_height=canvas.height,_pixelRatio=1,_opaqueSort=null,_transparentSort=null,_viewport=new Vector4(0,0,_width,_height),_scissor=new Vector4(0,0,_width,_height),_scissorTest=!1,_frustum=new Frustum,_clippingEnabled=!1,_localClippingEnabled=!1,_projScreenMatrix3=new Matrix4,_vector32=new Vector3,_vector42=new Vector4,_emptyScene={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0},_renderBackground=!1;function getTargetPixelRatio(){return _currentRenderTarget===null?_pixelRatio:1}let _gl=context;function getContext(contextName,contextAttributes){return canvas.getContext(contextName,contextAttributes)}let extensions,capabilities,state,info,properties,textures,environments,attributes,geometries,objects,programCache,materials,renderLists,renderStates,clipping,shadowMap,background,morphtargets,bufferRenderer,indexedBufferRenderer,utils,bindingStates,uniformsGroups;try{let contextAttributes={alpha:!0,depth,stencil,antialias,premultipliedAlpha,preserveDrawingBuffer,powerPreference,failIfMajorPerformanceCaveat};if("setAttribute"in canvas&&canvas.setAttribute("data-engine",`three.js r${"186"}`),canvas.addEventListener("webglcontextlost",onContextLost,!1),canvas.addEventListener("webglcontextrestored",onContextRestore,!1),canvas.addEventListener("webglcontextcreationerror",onContextCreationError,!1),_gl===null){let contextName="webgl2";if(_gl=getContext(contextName,contextAttributes),_gl===null)throw getContext(contextName)?new Error("THREE.WebGLRenderer: Error creating WebGL context with your selected attributes."):new Error("THREE.WebGLRenderer: Error creating WebGL context.")}initGLContext()}catch(e){throw canvas.removeEventListener("webglcontextlost",onContextLost,!1),canvas.removeEventListener("webglcontextrestored",onContextRestore,!1),canvas.removeEventListener("webglcontextcreationerror",onContextCreationError,!1),error("WebGLRenderer: "+e.message),e}function initGLContext(){extensions=new WebGLExtensions(_gl),extensions.init(),utils=new WebGLUtils(_gl,extensions),capabilities=new WebGLCapabilities(_gl,extensions,parameters,utils),state=new WebGLState(_gl,extensions),capabilities.reversedDepthBuffer&&reversedDepthBuffer&&state.buffers.depth.setReversed(!0),_scratchFramebuffer=_gl.createFramebuffer(),_srcFramebuffer=_gl.createFramebuffer(),_dstFramebuffer=_gl.createFramebuffer(),info=new WebGLInfo(_gl),properties=new WebGLProperties,textures=new WebGLTextures(_gl,extensions,state,properties,capabilities,utils,info),environments=new WebGLEnvironments(_this),attributes=new WebGLAttributes(_gl),bindingStates=new WebGLBindingStates(_gl,attributes),geometries=new WebGLGeometries(_gl,attributes,info,bindingStates),objects=new WebGLObjects(_gl,geometries,attributes,bindingStates,info),morphtargets=new WebGLMorphtargets(_gl,capabilities,textures),clipping=new WebGLClipping(properties),programCache=new WebGLPrograms(_this,environments,extensions,capabilities,bindingStates,clipping),materials=new WebGLMaterials(_this,properties),renderLists=new WebGLRenderLists,renderStates=new WebGLRenderStates(extensions),background=new WebGLBackground(_this,environments,state,objects,_alpha,premultipliedAlpha),shadowMap=new WebGLShadowMap(_this,objects,capabilities),uniformsGroups=new WebGLUniformsGroups(_gl,info,capabilities,state),bufferRenderer=new WebGLBufferRenderer(_gl,extensions,info),indexedBufferRenderer=new WebGLIndexedBufferRenderer(_gl,extensions,info),info.programs=programCache.programs,_this.capabilities=capabilities,_this.extensions=extensions,_this.properties=properties,_this.renderLists=renderLists,_this.shadowMap=shadowMap,_this.state=state,_this.info=info}_outputBufferType!==UnsignedByteType&&(output=new WebGLOutput(_outputBufferType,canvas.width,canvas.height,antialias,depth,stencil));let xr=new WebXRManager(_this,_gl);this.xr=xr,this.getContext=function(){return _gl},this.getContextAttributes=function(){return _gl.getContextAttributes()},this.forceContextLoss=function(){let extension=extensions.get("WEBGL_lose_context");extension&&extension.loseContext()},this.forceContextRestore=function(){let extension=extensions.get("WEBGL_lose_context");extension&&extension.restoreContext()},this.getPixelRatio=function(){return _pixelRatio},this.setPixelRatio=function(value){value!==void 0&&(_pixelRatio=value,this.setSize(_width,_height,!1))},this.getSize=function(target){return target.set(_width,_height)},this.setSize=function(width,height,updateStyle=!0){if(xr.isPresenting){warn("WebGLRenderer: Can't change size while VR device is presenting.");return}_width=width,_height=height,canvas.width=Math.floor(width*_pixelRatio),canvas.height=Math.floor(height*_pixelRatio),updateStyle===!0&&(canvas.style.width=width+"px",canvas.style.height=height+"px"),output!==null&&output.setSize(canvas.width,canvas.height),this.setViewport(0,0,width,height)},this.getDrawingBufferSize=function(target){return target.set(_width*_pixelRatio,_height*_pixelRatio).floor()},this.setDrawingBufferSize=function(width,height,pixelRatio){_width=width,_height=height,_pixelRatio=pixelRatio,canvas.width=Math.floor(width*pixelRatio),canvas.height=Math.floor(height*pixelRatio),this.setViewport(0,0,width,height)},this.setEffects=function(effects){if(_outputBufferType===UnsignedByteType){error("WebGLRenderer: setEffects() requires outputBufferType set to HalfFloatType or FloatType.");return}if(effects){for(let i=0;i<effects.length;i++)if(effects[i].isOutputPass===!0){warn("WebGLRenderer: OutputPass is not needed in setEffects(). Tone mapping and color space conversion are applied automatically.");break}}output.setEffects(effects||[])},this.getCurrentViewport=function(target){return target.copy(_currentViewport)},this.getViewport=function(target){return target.copy(_viewport)},this.setViewport=function(x,y,width,height){x.isVector4?_viewport.set(x.x,x.y,x.z,x.w):_viewport.set(x,y,width,height),state.viewport(_currentViewport.copy(_viewport).multiplyScalar(_pixelRatio).round())},this.getScissor=function(target){return target.copy(_scissor)},this.setScissor=function(x,y,width,height){x.isVector4?_scissor.set(x.x,x.y,x.z,x.w):_scissor.set(x,y,width,height),state.scissor(_currentScissor.copy(_scissor).multiplyScalar(_pixelRatio).round())},this.getScissorTest=function(){return _scissorTest},this.setScissorTest=function(boolean){state.setScissorTest(_scissorTest=boolean)},this.setOpaqueSort=function(method){_opaqueSort=method},this.setTransparentSort=function(method){_transparentSort=method},this.getClearColor=function(target){return target.copy(background.getClearColor())},this.setClearColor=function(){background.setClearColor(...arguments)},this.getClearAlpha=function(){return background.getClearAlpha()},this.setClearAlpha=function(){background.setClearAlpha(...arguments)},this.clear=function(color=!0,depth2=!0,stencil2=!0){let bits=0;if(color){let isIntegerFormat=!1;if(_currentRenderTarget!==null){let targetFormat=_currentRenderTarget.texture.format;isIntegerFormat=INTEGER_FORMATS.has(targetFormat)}if(isIntegerFormat){let targetType=_currentRenderTarget.texture.type,isUnsignedType=UNSIGNED_TYPES.has(targetType),clearColor=background.getClearColor(),a=background.getClearAlpha(),r=clearColor.r,g=clearColor.g,b=clearColor.b;isUnsignedType?(uintClearColor[0]=r,uintClearColor[1]=g,uintClearColor[2]=b,uintClearColor[3]=a,_gl.clearBufferuiv(_gl.COLOR,0,uintClearColor)):(intClearColor[0]=r,intClearColor[1]=g,intClearColor[2]=b,intClearColor[3]=a,_gl.clearBufferiv(_gl.COLOR,0,intClearColor))}else bits|=_gl.COLOR_BUFFER_BIT}depth2&&(bits|=_gl.DEPTH_BUFFER_BIT,this.state.buffers.depth.setMask(!0)),stencil2&&(bits|=_gl.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),bits!==0&&_gl.clear(bits)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.setNodesHandler=function(nodesHandler){nodesHandler.setRenderer(this),_nodesHandler=nodesHandler},this.dispose=function(){canvas.removeEventListener("webglcontextlost",onContextLost,!1),canvas.removeEventListener("webglcontextrestored",onContextRestore,!1),canvas.removeEventListener("webglcontextcreationerror",onContextCreationError,!1),background.dispose(),renderLists.dispose(),renderStates.dispose(),properties.dispose(),environments.dispose(),objects.dispose(),bindingStates.dispose(),uniformsGroups.dispose(),programCache.dispose(),xr.dispose(),xr.removeEventListener("sessionstart",onXRSessionStart),xr.removeEventListener("sessionend",onXRSessionEnd),animation.stop()};function onContextLost(event){event.preventDefault(),log("WebGLRenderer: Context Lost."),_isContextLost=!0}function onContextRestore(){log("WebGLRenderer: Context Restored."),_isContextLost=!1;let infoAutoReset=info.autoReset,shadowMapEnabled=shadowMap.enabled,shadowMapAutoUpdate=shadowMap.autoUpdate,shadowMapNeedsUpdate=shadowMap.needsUpdate,shadowMapType=shadowMap.type;initGLContext(),info.autoReset=infoAutoReset,shadowMap.enabled=shadowMapEnabled,shadowMap.autoUpdate=shadowMapAutoUpdate,shadowMap.needsUpdate=shadowMapNeedsUpdate,shadowMap.type=shadowMapType}function onContextCreationError(event){error("WebGLRenderer: A WebGL context could not be created. Reason: ",event.statusMessage)}function onMaterialDispose(event){let material=event.target;material.removeEventListener("dispose",onMaterialDispose),deallocateMaterial(material)}function deallocateMaterial(material){releaseMaterialProgramReferences(material),properties.remove(material)}function releaseMaterialProgramReferences(material){let programs=properties.get(material).programs;programs!==void 0&&(programs.forEach(function(program){programCache.releaseProgram(program)}),material.isShaderMaterial&&programCache.releaseShaderCache(material))}this.renderBufferDirect=function(camera,scene,geometry,material,object,group){scene===null&&(scene=_emptyScene);let frontFaceCW=object.isMesh&&object.matrixWorld.determinantAffine()<0,program=setProgram(camera,scene,geometry,material,object);state.setMaterial(material,frontFaceCW);let index=geometry.index,rangeFactor=1;if(material.wireframe===!0){if(index=geometries.getWireframeAttribute(geometry),index===void 0)return;rangeFactor=2}let drawRange=geometry.drawRange,position=geometry.attributes.position,drawStart=drawRange.start*rangeFactor,drawEnd=(drawRange.start+drawRange.count)*rangeFactor;group!==null&&(drawStart=Math.max(drawStart,group.start*rangeFactor),drawEnd=Math.min(drawEnd,(group.start+group.count)*rangeFactor)),index!==null?(drawStart=Math.max(drawStart,0),drawEnd=Math.min(drawEnd,index.count)):position!=null&&(drawStart=Math.max(drawStart,0),drawEnd=Math.min(drawEnd,position.count));let drawCount=drawEnd-drawStart;if(drawCount<0||drawCount===1/0)return;bindingStates.setup(object,material,program,geometry,index);let attribute,renderer=bufferRenderer;if(index!==null&&(attribute=attributes.get(index),renderer=indexedBufferRenderer,renderer.setIndex(attribute)),object.isMesh)material.wireframe===!0?(state.setLineWidth(material.wireframeLinewidth*getTargetPixelRatio()),renderer.setMode(_gl.LINES)):renderer.setMode(_gl.TRIANGLES);else if(object.isLine){let lineWidth=material.linewidth;lineWidth===void 0&&(lineWidth=1),state.setLineWidth(lineWidth*getTargetPixelRatio()),object.isLineSegments?renderer.setMode(_gl.LINES):object.isLineLoop?renderer.setMode(_gl.LINE_LOOP):renderer.setMode(_gl.LINE_STRIP)}else object.isPoints?renderer.setMode(_gl.POINTS):object.isSprite&&renderer.setMode(_gl.TRIANGLES);if(object.isBatchedMesh)if(extensions.get("WEBGL_multi_draw"))renderer.renderMultiDraw(object._multiDrawStarts,object._multiDrawCounts,object._multiDrawCount);else{let starts=object._multiDrawStarts,counts=object._multiDrawCounts,drawCount2=object._multiDrawCount,bytesPerElement=index?attributes.get(index).bytesPerElement:1,uniforms=properties.get(material).currentProgram.getUniforms();for(let i=0;i<drawCount2;i++)uniforms.setValue(_gl,"_gl_DrawID",i),renderer.render(starts[i]/bytesPerElement,counts[i])}else if(object.isInstancedMesh)renderer.renderInstances(drawStart,drawCount,object.count);else if(geometry.isInstancedBufferGeometry){let maxInstanceCount=geometry._maxInstanceCount!==void 0?geometry._maxInstanceCount:1/0,instanceCount=Math.min(geometry.instanceCount,maxInstanceCount);renderer.renderInstances(drawStart,drawCount,instanceCount)}else renderer.render(drawStart,drawCount)};function prepareMaterial(material,scene,camera,object){_nodesHandler!==null&&material.isNodeMaterial&&_nodesHandler.setObject(object,material),_clippingEnabled===!0&&clipping.setState(material,camera,!1),material.transparent===!0&&material.side===DoubleSide&&material.forceSinglePass===!1?(material.side=BackSide,material.needsUpdate=!0,getProgram(material,scene,object),material.side=FrontSide,material.needsUpdate=!0,getProgram(material,scene,object),material.side=DoubleSide):getProgram(material,scene,object)}this.compile=function(scene,camera,targetScene=null){targetScene===null&&(targetScene=scene),_nodesHandler!==null&&_nodesHandler.renderStart(scene,camera,targetScene),currentRenderState=renderStates.get(targetScene),currentRenderState.init(camera),renderStateStack.push(currentRenderState),targetScene.traverseVisible(function(object){object.isLight&&object.layers.test(camera.layers)&&(currentRenderState.pushLight(object),object.castShadow&&currentRenderState.pushShadow(object))}),scene!==targetScene&&scene.traverseVisible(function(object){object.isLight&&object.layers.test(camera.layers)&&(currentRenderState.pushLight(object),object.castShadow&&currentRenderState.pushShadow(object))}),currentRenderState.setupLights(),_nodesHandler!==null&&_nodesHandler.updateLights(currentRenderState.state.lightsArray),_localClippingEnabled=this.localClippingEnabled,_clippingEnabled=clipping.init(this.clippingPlanes,_localClippingEnabled),_clippingEnabled===!0&&clipping.setGlobalState(this.clippingPlanes,camera),_nodesHandler!==null&&shadowMap.render(currentRenderState.state.shadowsArray,targetScene,camera);let materials2=new Set;return scene.traverse(function(object){if(!(object.isMesh||object.isPoints||object.isLine||object.isSprite))return;let material=object.material;if(material)if(Array.isArray(material))for(let i=0;i<material.length;i++){let material2=material[i];prepareMaterial(material2,targetScene,camera,object),materials2.add(material2)}else prepareMaterial(material,targetScene,camera,object),materials2.add(material)}),currentRenderState=renderStateStack.pop(),_nodesHandler!==null&&_nodesHandler.renderEnd(),materials2},this.compileAsync=function(scene,camera,targetScene=null){let materials2=this.compile(scene,camera,targetScene);return new Promise(resolve=>{function checkMaterialsReady(){if(materials2.forEach(function(material){let program=properties.get(material).currentProgram;(program===void 0||program.isReady())&&materials2.delete(material)}),materials2.size===0){resolve(scene);return}setTimeout(checkMaterialsReady,10)}extensions.get("KHR_parallel_shader_compile")!==null?checkMaterialsReady():setTimeout(checkMaterialsReady,10)})};let onAnimationFrameCallback=null;function onAnimationFrame(time){onAnimationFrameCallback&&onAnimationFrameCallback(time)}function onXRSessionStart(){animation.stop()}function onXRSessionEnd(){animation.start()}let animation=new WebGLAnimation;animation.setAnimationLoop(onAnimationFrame),typeof self<"u"&&animation.setContext(self),this.setAnimationLoop=function(callback){onAnimationFrameCallback=callback,xr.setAnimationLoop(callback),callback===null?animation.stop():animation.start()},xr.addEventListener("sessionstart",onXRSessionStart),xr.addEventListener("sessionend",onXRSessionEnd),this.render=function(scene,camera){if(camera!==void 0&&camera.isCamera!==!0){error("WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(_isContextLost===!0)return;_nodesHandler!==null&&_nodesHandler.renderStart(scene,camera);let isXRPresenting=xr.enabled===!0&&xr.isPresenting===!0,useOutput=output!==null&&(_currentRenderTarget===null||isXRPresenting)&&output.begin(_this,_currentRenderTarget);if(scene.matrixWorldAutoUpdate===!0&&scene.updateMatrixWorld(),camera.parent===null&&camera.matrixWorldAutoUpdate===!0&&camera.updateMatrixWorld(),xr.enabled===!0&&xr.isPresenting===!0&&(output===null||output.isCompositing()===!1)&&(xr.cameraAutoUpdate===!0&&xr.updateCamera(camera),camera=xr.getCamera()),scene.isScene===!0&&scene.onBeforeRender(_this,scene,camera,_currentRenderTarget),currentRenderState=renderStates.get(scene,renderStateStack.length),currentRenderState.init(camera),currentRenderState.state.textureUnits=textures.getTextureUnits(),renderStateStack.push(currentRenderState),_projScreenMatrix3.multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse),_frustum.setFromProjectionMatrix(_projScreenMatrix3,WebGLCoordinateSystem,camera.reversedDepth),_localClippingEnabled=this.localClippingEnabled,_clippingEnabled=clipping.init(this.clippingPlanes,_localClippingEnabled),currentRenderList=renderLists.get(scene,renderListStack.length),currentRenderList.init(),renderListStack.push(currentRenderList),xr.enabled===!0&&xr.isPresenting===!0){let depthSensingMesh=_this.xr.getDepthSensingMesh();depthSensingMesh!==null&&projectObject(depthSensingMesh,camera,-1/0,_this.sortObjects)}projectObject(scene,camera,0,_this.sortObjects),currentRenderList.finish(),_nodesHandler!==null&&_nodesHandler.updateLights(currentRenderState.state.lightsArray),_this.sortObjects===!0&&currentRenderList.sort(_opaqueSort,_transparentSort),_renderBackground=xr.enabled===!1||xr.isPresenting===!1||xr.hasDepthSensing()===!1,_renderBackground&&background.addToRenderList(currentRenderList,scene),this.info.render.frame++,this.info.autoReset===!0&&this.info.reset(),_clippingEnabled===!0&&clipping.beginShadows();let shadowsArray=currentRenderState.state.shadowsArray;if(shadowMap.render(shadowsArray,scene,camera),_clippingEnabled===!0&&clipping.endShadows(),(useOutput&&output.hasRenderPass())===!1){let opaqueObjects=currentRenderList.opaque,transmissiveObjects=currentRenderList.transmissive;if(currentRenderState.setupLights(),camera.isArrayCamera){let cameras=camera.cameras;if(transmissiveObjects.length>0)for(let i=0,l=cameras.length;i<l;i++){let camera2=cameras[i];renderTransmissionPass(opaqueObjects,transmissiveObjects,scene,camera2)}_renderBackground&&background.render(scene);for(let i=0,l=cameras.length;i<l;i++){let camera2=cameras[i];renderScene(currentRenderList,scene,camera2,camera2.viewport)}}else transmissiveObjects.length>0&&renderTransmissionPass(opaqueObjects,transmissiveObjects,scene,camera),_renderBackground&&background.render(scene),renderScene(currentRenderList,scene,camera)}_currentRenderTarget!==null&&_currentActiveMipmapLevel===0&&(textures.updateMultisampleRenderTarget(_currentRenderTarget),textures.updateRenderTargetMipmap(_currentRenderTarget)),useOutput&&output.end(_this),scene.isScene===!0&&scene.onAfterRender(_this,scene,camera),bindingStates.resetDefaultState(),_currentMaterialId=-1,_currentCamera=null,renderStateStack.pop(),renderStateStack.length>0?(currentRenderState=renderStateStack[renderStateStack.length-1],textures.setTextureUnits(currentRenderState.state.textureUnits),_clippingEnabled===!0&&clipping.setGlobalState(_this.clippingPlanes,currentRenderState.state.camera)):currentRenderState=null,renderListStack.pop(),renderListStack.length>0?currentRenderList=renderListStack[renderListStack.length-1]:currentRenderList=null,_nodesHandler!==null&&_nodesHandler.renderEnd()};function projectObject(object,camera,groupOrder,sortObjects){if(object.visible===!1)return;if(object.layers.test(camera.layers)){if(object.isGroup)groupOrder=object.renderOrder;else if(object.isLOD)object.autoUpdate===!0&&object.update(camera);else if(object.isLightProbeGrid)currentRenderState.pushLightProbeGrid(object);else if(object.isLight)currentRenderState.pushLight(object),object.castShadow&&currentRenderState.pushShadow(object);else if(object.isSprite){if(!object.frustumCulled||object.intersectsFrustum(_frustum)){sortObjects&&_vector42.setFromMatrixPosition(object.matrixWorld).applyMatrix4(_projScreenMatrix3);let geometry=objects.update(object),material=object.material;material.visible&&currentRenderList.push(object,geometry,material,groupOrder,_vector42.z,null,camera)}}else if((object.isMesh||object.isLine||object.isPoints)&&(!object.frustumCulled||object.intersectsFrustum(_frustum))){let geometry=objects.update(object),material=object.material;if(sortObjects&&(object.boundingSphere!==void 0?(object.boundingSphere===null&&object.computeBoundingSphere(),_vector42.copy(object.boundingSphere.center)):(geometry.boundingSphere===null&&geometry.computeBoundingSphere(),_vector42.copy(geometry.boundingSphere.center)),_vector42.applyMatrix4(object.matrixWorld).applyMatrix4(_projScreenMatrix3)),Array.isArray(material)){let groups=geometry.groups;for(let i=0,l=groups.length;i<l;i++){let group=groups[i],groupMaterial=material[group.materialIndex];groupMaterial&&groupMaterial.visible&&currentRenderList.push(object,geometry,groupMaterial,groupOrder,_vector42.z,group,camera)}}else material.visible&&currentRenderList.push(object,geometry,material,groupOrder,_vector42.z,null,camera)}}let children=object.children;for(let i=0,l=children.length;i<l;i++)projectObject(children[i],camera,groupOrder,sortObjects)}function renderScene(currentRenderList2,scene,camera,viewport){let{opaque:opaqueObjects,transmissive:transmissiveObjects,transparent:transparentObjects}=currentRenderList2;currentRenderState.setupLightsView(camera),_clippingEnabled===!0&&clipping.setGlobalState(_this.clippingPlanes,camera),viewport&&state.viewport(_currentViewport.copy(viewport)),opaqueObjects.length>0&&renderObjects(opaqueObjects,scene,camera),transmissiveObjects.length>0&&renderObjects(transmissiveObjects,scene,camera),transparentObjects.length>0&&renderObjects(transparentObjects,scene,camera),state.buffers.depth.setTest(!0),state.buffers.depth.setMask(!0),state.buffers.color.setMask(!0),state.setPolygonOffset(!1)}function renderTransmissionPass(opaqueObjects,transmissiveObjects,scene,camera){if((scene.isScene===!0?scene.overrideMaterial:null)!==null)return;if(currentRenderState.state.transmissionRenderTarget[camera.id]===void 0){let hasHalfFloatSupport=extensions.has("EXT_color_buffer_half_float")||extensions.has("EXT_color_buffer_float");currentRenderState.state.transmissionRenderTarget[camera.id]=new WebGLRenderTarget(1,1,{generateMipmaps:!0,type:hasHalfFloatSupport?HalfFloatType:UnsignedByteType,minFilter:LinearMipmapLinearFilter,samples:Math.max(4,capabilities.samples),stencilBuffer:stencil,resolveDepthBuffer:!1,resolveStencilBuffer:!1,storeMultisampledDepthBuffer:!1,storeMultisampledStencilBuffer:!1,colorSpace:ColorManagement.workingColorSpace})}let transmissionRenderTarget=currentRenderState.state.transmissionRenderTarget[camera.id],activeViewport=camera.viewport||_currentViewport;transmissionRenderTarget.setSize(activeViewport.z*_this.transmissionResolutionScale,activeViewport.w*_this.transmissionResolutionScale);let currentRenderTarget=_this.getRenderTarget(),currentActiveCubeFace=_this.getActiveCubeFace(),currentActiveMipmapLevel=_this.getActiveMipmapLevel();_this.setRenderTarget(transmissionRenderTarget),_this.getClearColor(_currentClearColor),_currentClearAlpha=_this.getClearAlpha(),_currentClearAlpha<1&&_this.setClearColor(16777215,.5),_this.clear(),_renderBackground&&background.render(scene);let currentToneMapping=_this.toneMapping;_this.toneMapping=NoToneMapping;let currentCameraViewport=camera.viewport;if(camera.viewport!==void 0&&(camera.viewport=void 0),currentRenderState.setupLightsView(camera),_clippingEnabled===!0&&clipping.setGlobalState(_this.clippingPlanes,camera),renderObjects(opaqueObjects,scene,camera),textures.updateMultisampleRenderTarget(transmissionRenderTarget),textures.updateRenderTargetMipmap(transmissionRenderTarget),extensions.has("WEBGL_multisampled_render_to_texture")===!1){let renderTargetNeedsUpdate=!1;for(let i=0,l=transmissiveObjects.length;i<l;i++){let renderItem=transmissiveObjects[i],{object,geometry,material,group}=renderItem;if(material.side===DoubleSide&&object.layers.test(camera.layers)){let currentSide=material.side;material.side=BackSide,material.needsUpdate=!0,renderObject(object,scene,camera,geometry,material,group),material.side=currentSide,material.needsUpdate=!0,renderTargetNeedsUpdate=!0}}renderTargetNeedsUpdate===!0&&(textures.updateMultisampleRenderTarget(transmissionRenderTarget),textures.updateRenderTargetMipmap(transmissionRenderTarget))}_this.setRenderTarget(currentRenderTarget,currentActiveCubeFace,currentActiveMipmapLevel),_this.setClearColor(_currentClearColor,_currentClearAlpha),currentCameraViewport!==void 0&&(camera.viewport=currentCameraViewport),_this.toneMapping=currentToneMapping}function renderObjects(renderList,scene,camera){let overrideMaterial=scene.isScene===!0?scene.overrideMaterial:null;for(let i=0,l=renderList.length;i<l;i++){let renderItem=renderList[i],{object,geometry,group}=renderItem,material=renderItem.material;material.allowOverride===!0&&overrideMaterial!==null&&(material=overrideMaterial),object.layers.test(camera.layers)&&renderObject(object,scene,camera,geometry,material,group)}}function renderObject(object,scene,camera,geometry,material,group){_nodesHandler!==null&&material.isNodeMaterial&&_nodesHandler.setObject(object,material),object.onBeforeRender(_this,scene,camera,geometry,material,group),object.modelViewMatrix.multiplyMatrices(camera.matrixWorldInverse,object.matrixWorld),object.normalMatrix.getNormalMatrix(object.modelViewMatrix),material.onBeforeRender(_this,scene,camera,geometry,object,group),material.transparent===!0&&material.side===DoubleSide&&material.forceSinglePass===!1?(material.side=BackSide,material.needsUpdate=!0,_this.renderBufferDirect(camera,scene,geometry,material,object,group),material.side=FrontSide,material.needsUpdate=!0,_this.renderBufferDirect(camera,scene,geometry,material,object,group),material.side=DoubleSide):_this.renderBufferDirect(camera,scene,geometry,material,object,group),object.onAfterRender(_this,scene,camera,geometry,material,group)}function getProgram(material,scene,object){scene.isScene!==!0&&(scene=_emptyScene);let materialProperties=properties.get(material),lights=currentRenderState.state.lights,shadowsArray=currentRenderState.state.shadowsArray,lightsStateVersion=lights.state.version,parameters2=programCache.getParameters(material,lights.state,shadowsArray,scene,object,currentRenderState.state.lightProbeGridArray),programCacheKey=programCache.getProgramCacheKey(parameters2),programs=materialProperties.programs;materialProperties.environment=material.isMeshStandardMaterial||material.isMeshLambertMaterial||material.isMeshPhongMaterial?scene.environment:null,materialProperties.fog=scene.fog;let usePMREM=material.isMeshStandardMaterial||material.isMeshLambertMaterial&&!material.envMap||material.isMeshPhongMaterial&&!material.envMap;materialProperties.envMap=environments.get(material.envMap||materialProperties.environment,usePMREM),materialProperties.envMapRotation=materialProperties.environment!==null&&material.envMap===null?scene.environmentRotation:material.envMapRotation,programs===void 0&&(material.addEventListener("dispose",onMaterialDispose),programs=new Map,materialProperties.programs=programs);let program=programs.get(programCacheKey);if(program!==void 0){if(materialProperties.currentProgram===program&&materialProperties.lightsStateVersion===lightsStateVersion)return updateCommonMaterialProperties(material,parameters2),program}else parameters2.uniforms=programCache.getUniforms(material),_nodesHandler!==null&&material.isNodeMaterial&&_nodesHandler.build(material,object,parameters2),material.onBeforeCompile(parameters2,_this),program=programCache.acquireProgram(parameters2,programCacheKey),programs.set(programCacheKey,program),materialProperties.uniforms=parameters2.uniforms;let uniforms=materialProperties.uniforms;return(!material.isShaderMaterial&&!material.isRawShaderMaterial||material.clipping===!0)&&(uniforms.clippingPlanes=clipping.uniform),updateCommonMaterialProperties(material,parameters2),materialProperties.needsLights=materialNeedsLights(material),materialProperties.lightsStateVersion=lightsStateVersion,materialProperties.needsLights&&(uniforms.ambientLightColor.value=lights.state.ambient,uniforms.lightProbe.value=lights.state.probe,uniforms.sunLights.value=lights.state.sun,uniforms.sunLightShadows.value=lights.state.sunShadow,uniforms.directionalLights.value=lights.state.directional,uniforms.directionalLightShadows.value=lights.state.directionalShadow,uniforms.spotLights.value=lights.state.spot,uniforms.spotLightShadows.value=lights.state.spotShadow,uniforms.rectAreaLights.value=lights.state.rectArea,uniforms.ltc_1.value=lights.state.rectAreaLTC1,uniforms.ltc_2.value=lights.state.rectAreaLTC2,uniforms.pointLights.value=lights.state.point,uniforms.pointLightShadows.value=lights.state.pointShadow,uniforms.hemisphereLights.value=lights.state.hemi,uniforms.sunShadowMatrix.value=lights.state.sunShadowMatrix,uniforms.sunShadowCascade.value=lights.state.sunShadowCascade,uniforms.directionalShadowMatrix.value=lights.state.directionalShadowMatrix,uniforms.spotLightMatrix.value=lights.state.spotLightMatrix,uniforms.spotLightMap.value=lights.state.spotLightMap,uniforms.pointShadowMatrix.value=lights.state.pointShadowMatrix),materialProperties.lightProbeGrid=currentRenderState.state.lightProbeGridArray.length>0,materialProperties.currentProgram=program,materialProperties.uniformsList=null,program}function getUniformList(materialProperties){if(materialProperties.uniformsList===null){let progUniforms=materialProperties.currentProgram.getUniforms();materialProperties.uniformsList=WebGLUniforms.seqWithValue(progUniforms.seq,materialProperties.uniforms)}return materialProperties.uniformsList}function updateCommonMaterialProperties(material,parameters2){let materialProperties=properties.get(material);materialProperties.outputColorSpace=parameters2.outputColorSpace,materialProperties.batching=parameters2.batching,materialProperties.batchingColor=parameters2.batchingColor,materialProperties.instancing=parameters2.instancing,materialProperties.instancingColor=parameters2.instancingColor,materialProperties.instancingMorph=parameters2.instancingMorph,materialProperties.skinning=parameters2.skinning,materialProperties.morphTargets=parameters2.morphTargets,materialProperties.morphNormals=parameters2.morphNormals,materialProperties.morphColors=parameters2.morphColors,materialProperties.morphTargetsCount=parameters2.morphTargetsCount,materialProperties.numClippingPlanes=parameters2.numClippingPlanes,materialProperties.numIntersection=parameters2.numClipIntersection,materialProperties.vertexAlphas=parameters2.vertexAlphas,materialProperties.vertexTangents=parameters2.vertexTangents,materialProperties.toneMapping=parameters2.toneMapping}function findLightProbeGrid(volumes,object){if(volumes.length===0)return null;if(volumes.length===1)return volumes[0].texture!==null?volumes[0]:null;objectPosition.setFromMatrixPosition(object.matrixWorld);for(let i=0,l=volumes.length;i<l;i++){let v=volumes[i];if(v.texture!==null&&v.boundingBox.containsPoint(objectPosition))return v}return null}function setProgram(camera,scene,geometry,material,object){scene.isScene!==!0&&(scene=_emptyScene),textures.resetTextureUnits();let fog=scene.fog,environment=material.isMeshStandardMaterial||material.isMeshLambertMaterial||material.isMeshPhongMaterial?scene.environment:null,colorSpace=_currentRenderTarget===null?_this.outputColorSpace:_currentRenderTarget.isXRRenderTarget===!0?_currentRenderTarget.texture.colorSpace:ColorManagement.workingColorSpace,usePMREM=material.isMeshStandardMaterial||material.isMeshLambertMaterial&&!material.envMap||material.isMeshPhongMaterial&&!material.envMap,envMap=environments.get(material.envMap||environment,usePMREM),vertexAlphas=material.vertexColors===!0&&!!geometry.attributes.color&&geometry.attributes.color.itemSize===4,vertexTangents=!!geometry.attributes.tangent&&(!!material.normalMap||material.anisotropy>0),morphTargets=!!geometry.morphAttributes.position,morphNormals=!!geometry.morphAttributes.normal,morphColors=!!geometry.morphAttributes.color,toneMapping=NoToneMapping;material.toneMapped&&(_currentRenderTarget===null||_currentRenderTarget.isXRRenderTarget===!0)&&(toneMapping=_this.toneMapping);let morphAttribute=geometry.morphAttributes.position||geometry.morphAttributes.normal||geometry.morphAttributes.color,morphTargetsCount=morphAttribute!==void 0?morphAttribute.length:0,materialProperties=properties.get(material),lights=currentRenderState.state.lights;if(_clippingEnabled===!0&&(_localClippingEnabled===!0||camera!==_currentCamera)){let useCache=camera===_currentCamera&&material.id===_currentMaterialId;clipping.setState(material,camera,useCache)}let needsProgramChange=!1;material.version===materialProperties.__version?(materialProperties.needsLights&&materialProperties.lightsStateVersion!==lights.state.version||materialProperties.outputColorSpace!==colorSpace||object.isBatchedMesh&&materialProperties.batching===!1||!object.isBatchedMesh&&materialProperties.batching===!0||object.isBatchedMesh&&materialProperties.batchingColor===!0&&object._colorsTexture===null||object.isBatchedMesh&&materialProperties.batchingColor===!1&&object._colorsTexture!==null||object.isInstancedMesh&&materialProperties.instancing===!1||!object.isInstancedMesh&&materialProperties.instancing===!0||object.isSkinnedMesh&&materialProperties.skinning===!1||!object.isSkinnedMesh&&materialProperties.skinning===!0||object.isInstancedMesh&&materialProperties.instancingColor===!0&&object.instanceColor===null||object.isInstancedMesh&&materialProperties.instancingColor===!1&&object.instanceColor!==null||object.isInstancedMesh&&materialProperties.instancingMorph===!0&&object.morphTexture===null||object.isInstancedMesh&&materialProperties.instancingMorph===!1&&object.morphTexture!==null||materialProperties.envMap!==envMap||material.fog===!0&&materialProperties.fog!==fog||materialProperties.numClippingPlanes!==void 0&&(materialProperties.numClippingPlanes!==clipping.numPlanes||materialProperties.numIntersection!==clipping.numIntersection)||materialProperties.vertexAlphas!==vertexAlphas||materialProperties.vertexTangents!==vertexTangents||materialProperties.morphTargets!==morphTargets||materialProperties.morphNormals!==morphNormals||materialProperties.morphColors!==morphColors||materialProperties.toneMapping!==toneMapping||materialProperties.morphTargetsCount!==morphTargetsCount||!!materialProperties.lightProbeGrid!=currentRenderState.state.lightProbeGridArray.length>0)&&(needsProgramChange=!0):(needsProgramChange=!0,materialProperties.__version=material.version);let program=materialProperties.currentProgram;needsProgramChange===!0&&(program=getProgram(material,scene,object),_nodesHandler&&material.isNodeMaterial&&_nodesHandler.onUpdateProgram(material,program,materialProperties));let refreshProgram=!1,refreshMaterial=!1,refreshLights=!1,p_uniforms=program.getUniforms(),m_uniforms=materialProperties.uniforms;if(state.useProgram(program.program)&&(refreshProgram=!0,refreshMaterial=!0,refreshLights=!0),material.id!==_currentMaterialId&&(_currentMaterialId=material.id,refreshMaterial=!0),materialProperties.needsLights){let objectVolume=findLightProbeGrid(currentRenderState.state.lightProbeGridArray,object);materialProperties.lightProbeGrid!==objectVolume&&(materialProperties.lightProbeGrid=objectVolume,refreshMaterial=!0)}if(refreshProgram||_currentCamera!==camera){state.buffers.depth.getReversed()&&camera.reversedDepth!==!0&&(camera._reversedDepth=!0,camera.updateProjectionMatrix()),p_uniforms.setValue(_gl,"projectionMatrix",camera.projectionMatrix),p_uniforms.setValue(_gl,"viewMatrix",camera.matrixWorldInverse);let uCamPos=p_uniforms.map.cameraPosition;uCamPos!==void 0&&uCamPos.setValue(_gl,_vector32.setFromMatrixPosition(camera.matrixWorld)),capabilities.logarithmicDepthBuffer&&p_uniforms.setValue(_gl,"logDepthBufFC",2/(Math.log(camera.far+1)/Math.LN2)),(material.isMeshPhongMaterial||material.isMeshToonMaterial||material.isMeshLambertMaterial||material.isMeshBasicMaterial||material.isMeshStandardMaterial||material.isShaderMaterial)&&p_uniforms.setValue(_gl,"isOrthographic",camera.isOrthographicCamera===!0),_currentCamera!==camera&&(_currentCamera=camera,refreshMaterial=!0,refreshLights=!0)}if(materialProperties.needsLights&&(lights.state.sunShadowMap.length>0&&p_uniforms.setValue(_gl,"sunShadowMap",lights.state.sunShadowMap,textures),lights.state.directionalShadowMap.length>0&&p_uniforms.setValue(_gl,"directionalShadowMap",lights.state.directionalShadowMap,textures),lights.state.spotShadowMap.length>0&&p_uniforms.setValue(_gl,"spotShadowMap",lights.state.spotShadowMap,textures),lights.state.pointShadowMap.length>0&&p_uniforms.setValue(_gl,"pointShadowMap",lights.state.pointShadowMap,textures)),object.isSkinnedMesh){p_uniforms.setOptional(_gl,object,"bindMatrix"),p_uniforms.setOptional(_gl,object,"bindMatrixInverse");let skeleton=object.skeleton;skeleton&&(skeleton.boneTexture===null&&skeleton.computeBoneTexture(),p_uniforms.setValue(_gl,"boneTexture",skeleton.boneTexture,textures))}object.isBatchedMesh&&(p_uniforms.setOptional(_gl,object,"batchingTexture"),p_uniforms.setValue(_gl,"batchingTexture",object._matricesTexture,textures),p_uniforms.setOptional(_gl,object,"batchingIdTexture"),p_uniforms.setValue(_gl,"batchingIdTexture",object._indirectTexture,textures),p_uniforms.setOptional(_gl,object,"batchingColorTexture"),object._colorsTexture!==null&&p_uniforms.setValue(_gl,"batchingColorTexture",object._colorsTexture,textures));let morphAttributes=geometry.morphAttributes;if((morphAttributes.position!==void 0||morphAttributes.normal!==void 0||morphAttributes.color!==void 0)&&morphtargets.update(object,geometry,program),(refreshMaterial||materialProperties.receiveShadow!==object.receiveShadow)&&(materialProperties.receiveShadow=object.receiveShadow,p_uniforms.setValue(_gl,"receiveShadow",object.receiveShadow)),(material.isMeshStandardMaterial||material.isMeshLambertMaterial||material.isMeshPhongMaterial)&&material.envMap===null&&scene.environment!==null&&(m_uniforms.envMapIntensity.value=scene.environmentIntensity),m_uniforms.dfgLUT!==void 0&&(m_uniforms.dfgLUT.value=getDFGLUT()),refreshMaterial){if(p_uniforms.setValue(_gl,"toneMappingExposure",_this.toneMappingExposure),materialProperties.needsLights&&markUniformsLightsNeedsUpdate(m_uniforms,refreshLights),fog&&material.fog===!0&&materials.refreshFogUniforms(m_uniforms,fog),materials.refreshMaterialUniforms(m_uniforms,material,_pixelRatio,_height,currentRenderState.state.transmissionRenderTarget[camera.id]),materialProperties.needsLights&&materialProperties.lightProbeGrid){let volume=materialProperties.lightProbeGrid;m_uniforms.probesSH.value=volume.texture,m_uniforms.probesMin.value.copy(volume.boundingBox.min),m_uniforms.probesMax.value.copy(volume.boundingBox.max),m_uniforms.probesResolution.value.copy(volume.resolution)}WebGLUniforms.upload(_gl,getUniformList(materialProperties),m_uniforms,textures)}if(material.isShaderMaterial&&material.uniformsNeedUpdate===!0&&(WebGLUniforms.upload(_gl,getUniformList(materialProperties),m_uniforms,textures),material.uniformsNeedUpdate=!1),material.isSpriteMaterial&&p_uniforms.setValue(_gl,"center",object.center),p_uniforms.setValue(_gl,"modelViewMatrix",object.modelViewMatrix),p_uniforms.setValue(_gl,"normalMatrix",object.normalMatrix),p_uniforms.setValue(_gl,"modelMatrix",object.matrixWorld),material.uniformsGroups!==void 0){let groups=material.uniformsGroups;for(let i=0,l=groups.length;i<l;i++){let group=groups[i];uniformsGroups.update(group,program),uniformsGroups.bind(group,program)}}return program}function markUniformsLightsNeedsUpdate(uniforms,value){uniforms.ambientLightColor.needsUpdate=value,uniforms.lightProbe.needsUpdate=value,uniforms.sunLights.needsUpdate=value,uniforms.sunLightShadows.needsUpdate=value,uniforms.directionalLights.needsUpdate=value,uniforms.directionalLightShadows.needsUpdate=value,uniforms.pointLights.needsUpdate=value,uniforms.pointLightShadows.needsUpdate=value,uniforms.spotLights.needsUpdate=value,uniforms.spotLightShadows.needsUpdate=value,uniforms.rectAreaLights.needsUpdate=value,uniforms.hemisphereLights.needsUpdate=value}function materialNeedsLights(material){return material.isMeshLambertMaterial||material.isMeshToonMaterial||material.isMeshPhongMaterial||material.isMeshStandardMaterial||material.isShadowMaterial||material.isShaderMaterial&&material.lights===!0}this.getActiveCubeFace=function(){return _currentActiveCubeFace},this.getActiveMipmapLevel=function(){return _currentActiveMipmapLevel},this.getRenderTarget=function(){return _currentRenderTarget},this.setRenderTargetTextures=function(renderTarget,colorTexture,depthTexture){let renderTargetProperties=properties.get(renderTarget);renderTargetProperties.__autoAllocateDepthBuffer=renderTarget.resolveDepthBuffer===!1,renderTargetProperties.__autoAllocateDepthBuffer===!1&&(renderTargetProperties.__useRenderToTexture=!1),properties.get(renderTarget.texture).__webglTexture=colorTexture,properties.get(renderTarget.depthTexture).__webglTexture=renderTargetProperties.__autoAllocateDepthBuffer?void 0:depthTexture,renderTargetProperties.__hasExternalTextures=!0},this.setRenderTargetFramebuffer=function(renderTarget,defaultFramebuffer){let renderTargetProperties=properties.get(renderTarget);renderTargetProperties.__webglFramebuffer=defaultFramebuffer,renderTargetProperties.__useDefaultFramebuffer=defaultFramebuffer===void 0},this.setRenderTarget=function(renderTarget,activeCubeFace=0,activeMipmapLevel=0){_currentRenderTarget=renderTarget,_currentActiveCubeFace=activeCubeFace,_currentActiveMipmapLevel=activeMipmapLevel;let framebuffer=null,isCube=!1,isRenderTarget3D=!1;if(renderTarget){let renderTargetProperties=properties.get(renderTarget);if(renderTargetProperties.__useDefaultFramebuffer!==void 0){state.bindFramebuffer(_gl.FRAMEBUFFER,renderTargetProperties.__webglFramebuffer),_currentViewport.copy(renderTarget.viewport),_currentScissor.copy(renderTarget.scissor),_currentScissorTest=renderTarget.scissorTest,state.viewport(_currentViewport),state.scissor(_currentScissor),state.setScissorTest(_currentScissorTest),_currentMaterialId=-1;return}else if(renderTargetProperties.__webglFramebuffer===void 0)textures.setupRenderTarget(renderTarget);else if(renderTargetProperties.__hasExternalTextures)textures.rebindTextures(renderTarget,properties.get(renderTarget.texture).__webglTexture,properties.get(renderTarget.depthTexture).__webglTexture);else if(renderTarget.depthBuffer){let depthTexture=renderTarget.depthTexture;if(renderTargetProperties.__boundDepthTexture!==depthTexture){if(depthTexture!==null&&properties.has(depthTexture)&&(renderTarget.width!==depthTexture.image.width||renderTarget.height!==depthTexture.image.height))throw new Error("THREE.WebGLRenderer: Attached DepthTexture is initialized to the incorrect size.");textures.setupDepthRenderbuffer(renderTarget)}}let texture=renderTarget.texture;(texture.isData3DTexture||texture.isDataArrayTexture||texture.isCompressedArrayTexture)&&(isRenderTarget3D=!0);let __webglFramebuffer=properties.get(renderTarget).__webglFramebuffer;renderTarget.isWebGLCubeRenderTarget?(Array.isArray(__webglFramebuffer[activeCubeFace])?framebuffer=__webglFramebuffer[activeCubeFace][activeMipmapLevel]:framebuffer=__webglFramebuffer[activeCubeFace],isCube=!0):renderTarget.samples>0&&textures.useMultisampledRTT(renderTarget)===!1?framebuffer=properties.get(renderTarget).__webglMultisampledFramebuffer:Array.isArray(__webglFramebuffer)?framebuffer=__webglFramebuffer[activeMipmapLevel]:framebuffer=__webglFramebuffer,_currentViewport.copy(renderTarget.viewport),_currentScissor.copy(renderTarget.scissor),_currentScissorTest=renderTarget.scissorTest}else _currentViewport.copy(_viewport).multiplyScalar(_pixelRatio).floor(),_currentScissor.copy(_scissor).multiplyScalar(_pixelRatio).floor(),_currentScissorTest=_scissorTest;if(activeMipmapLevel!==0&&(framebuffer=_scratchFramebuffer),state.bindFramebuffer(_gl.FRAMEBUFFER,framebuffer)&&state.drawBuffers(renderTarget,framebuffer),state.viewport(_currentViewport),state.scissor(_currentScissor),state.setScissorTest(_currentScissorTest),isCube){let textureProperties=properties.get(renderTarget.texture);_gl.framebufferTexture2D(_gl.FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,_gl.TEXTURE_CUBE_MAP_POSITIVE_X+activeCubeFace,textureProperties.__webglTexture,activeMipmapLevel)}else if(isRenderTarget3D){let layer=activeCubeFace;for(let i=0;i<renderTarget.textures.length;i++){let textureProperties=properties.get(renderTarget.textures[i]);_gl.framebufferTextureLayer(_gl.FRAMEBUFFER,_gl.COLOR_ATTACHMENT0+i,textureProperties.__webglTexture,activeMipmapLevel,layer)}}else if(renderTarget!==null&&activeMipmapLevel!==0){let textureProperties=properties.get(renderTarget.texture);_gl.framebufferTexture2D(_gl.FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,_gl.TEXTURE_2D,textureProperties.__webglTexture,activeMipmapLevel)}_currentMaterialId=-1};function getReadableState(texture){let textureProperties=properties.get(texture);return(textureProperties.__readFormat!==texture.format||textureProperties.__readType!==texture.type)&&(textureProperties.__readFormat=texture.format,textureProperties.__readType=texture.type,textureProperties.__formatReadable=capabilities.textureFormatReadable(texture.format),textureProperties.__typeReadable=capabilities.textureTypeReadable(texture.type)),textureProperties}this.readRenderTargetPixels=function(renderTarget,x,y,width,height,buffer,activeCubeFaceIndex,textureIndex=0){if(!(renderTarget&&renderTarget.isWebGLRenderTarget)){error("WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let framebuffer=properties.get(renderTarget).__webglFramebuffer;if(renderTarget.isWebGLCubeRenderTarget&&activeCubeFaceIndex!==void 0&&(framebuffer=framebuffer[activeCubeFaceIndex]),framebuffer){state.bindFramebuffer(_gl.FRAMEBUFFER,framebuffer);try{let texture=renderTarget.textures[textureIndex],textureFormat=texture.format,textureType=texture.type;renderTarget.textures.length>1&&_gl.readBuffer(_gl.COLOR_ATTACHMENT0+textureIndex);let readableState=getReadableState(texture);if(readableState.__formatReadable===!1){error("WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(readableState.__typeReadable===!1){error("WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}x>=0&&x<=renderTarget.width-width&&y>=0&&y<=renderTarget.height-height&&_gl.readPixels(x,y,width,height,utils.convert(textureFormat),utils.convert(textureType),buffer)}finally{let framebuffer2=_currentRenderTarget!==null?properties.get(_currentRenderTarget).__webglFramebuffer:null;state.bindFramebuffer(_gl.FRAMEBUFFER,framebuffer2)}}},this.readRenderTargetPixelsAsync=async function(renderTarget,x,y,width,height,buffer,activeCubeFaceIndex,textureIndex=0){if(!(renderTarget&&renderTarget.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let framebuffer=properties.get(renderTarget).__webglFramebuffer;if(renderTarget.isWebGLCubeRenderTarget&&activeCubeFaceIndex!==void 0&&(framebuffer=framebuffer[activeCubeFaceIndex]),framebuffer)if(x>=0&&x<=renderTarget.width-width&&y>=0&&y<=renderTarget.height-height){state.bindFramebuffer(_gl.FRAMEBUFFER,framebuffer);let texture=renderTarget.textures[textureIndex],textureFormat=texture.format,textureType=texture.type;renderTarget.textures.length>1&&_gl.readBuffer(_gl.COLOR_ATTACHMENT0+textureIndex);let readableState=getReadableState(texture);if(readableState.__formatReadable===!1)throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(readableState.__typeReadable===!1)throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");let glBuffer=_gl.createBuffer();_gl.bindBuffer(_gl.PIXEL_PACK_BUFFER,glBuffer),_gl.bufferData(_gl.PIXEL_PACK_BUFFER,buffer.byteLength,_gl.STREAM_READ),_gl.readPixels(x,y,width,height,utils.convert(textureFormat),utils.convert(textureType),0),_gl.bindBuffer(_gl.PIXEL_PACK_BUFFER,null);let currFramebuffer=_currentRenderTarget!==null?properties.get(_currentRenderTarget).__webglFramebuffer:null;state.bindFramebuffer(_gl.FRAMEBUFFER,currFramebuffer);let sync=_gl.fenceSync(_gl.SYNC_GPU_COMMANDS_COMPLETE,0);return _gl.flush(),await probeAsync(_gl,sync,4),_gl.bindBuffer(_gl.PIXEL_PACK_BUFFER,glBuffer),_gl.getBufferSubData(_gl.PIXEL_PACK_BUFFER,0,buffer),_gl.bindBuffer(_gl.PIXEL_PACK_BUFFER,null),_gl.deleteBuffer(glBuffer),_gl.deleteSync(sync),buffer}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")},this.copyFramebufferToTexture=function(texture,position=null,level=0){let levelScale=Math.pow(2,-level),width=Math.floor(texture.image.width*levelScale),height=Math.floor(texture.image.height*levelScale),x=position!==null?position.x:0,y=position!==null?position.y:0;textures.setTexture2D(texture,0),_gl.copyTexSubImage2D(_gl.TEXTURE_2D,level,0,0,x,y,width,height),state.unbindTexture()},this.copyTextureToTexture=function(srcTexture,dstTexture,srcRegion=null,dstPosition=null,srcLevel=0,dstLevel=0){let width,height,depth2,minX,minY,minZ,dstX,dstY,dstZ,image=srcTexture.isCompressedTexture?srcTexture.mipmaps[dstLevel]:srcTexture.image;if(srcRegion!==null)width=srcRegion.max.x-srcRegion.min.x,height=srcRegion.max.y-srcRegion.min.y,depth2=srcRegion.isBox3?srcRegion.max.z-srcRegion.min.z:1,minX=srcRegion.min.x,minY=srcRegion.min.y,minZ=srcRegion.isBox3?srcRegion.min.z:0;else{let levelScale=Math.pow(2,-srcLevel);width=Math.floor(image.width*levelScale),height=Math.floor(image.height*levelScale),srcTexture.isDataArrayTexture?depth2=image.depth:srcTexture.isData3DTexture?depth2=Math.floor(image.depth*levelScale):depth2=1,minX=0,minY=0,minZ=0}dstPosition!==null?(dstX=dstPosition.x,dstY=dstPosition.y,dstZ=dstPosition.z):(dstX=0,dstY=0,dstZ=0);let glFormat=utils.convert(dstTexture.format),glType=utils.convert(dstTexture.type),glTarget;dstTexture.isData3DTexture?(textures.setTexture3D(dstTexture,0),glTarget=_gl.TEXTURE_3D):dstTexture.isDataArrayTexture||dstTexture.isCompressedArrayTexture?(textures.setTexture2DArray(dstTexture,0),glTarget=_gl.TEXTURE_2D_ARRAY):(textures.setTexture2D(dstTexture,0),glTarget=_gl.TEXTURE_2D),state.activeTexture(_gl.TEXTURE0),state.pixelStorei(_gl.UNPACK_FLIP_Y_WEBGL,dstTexture.flipY),state.pixelStorei(_gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,dstTexture.premultiplyAlpha),state.pixelStorei(_gl.UNPACK_ALIGNMENT,dstTexture.unpackAlignment);let currentUnpackRowLen=state.getParameter(_gl.UNPACK_ROW_LENGTH),currentUnpackImageHeight=state.getParameter(_gl.UNPACK_IMAGE_HEIGHT),currentUnpackSkipPixels=state.getParameter(_gl.UNPACK_SKIP_PIXELS),currentUnpackSkipRows=state.getParameter(_gl.UNPACK_SKIP_ROWS),currentUnpackSkipImages=state.getParameter(_gl.UNPACK_SKIP_IMAGES);state.pixelStorei(_gl.UNPACK_ROW_LENGTH,image.width),state.pixelStorei(_gl.UNPACK_IMAGE_HEIGHT,image.height),state.pixelStorei(_gl.UNPACK_SKIP_PIXELS,minX),state.pixelStorei(_gl.UNPACK_SKIP_ROWS,minY),state.pixelStorei(_gl.UNPACK_SKIP_IMAGES,minZ);let isSrc3D=srcTexture.isDataArrayTexture||srcTexture.isData3DTexture,isDst3D=dstTexture.isDataArrayTexture||dstTexture.isData3DTexture;if(srcTexture.isDepthTexture){let srcTextureProperties=properties.get(srcTexture),dstTextureProperties=properties.get(dstTexture),srcRenderTargetProperties=properties.get(srcTextureProperties.__renderTarget),dstRenderTargetProperties=properties.get(dstTextureProperties.__renderTarget);state.bindFramebuffer(_gl.READ_FRAMEBUFFER,srcRenderTargetProperties.__webglFramebuffer),state.bindFramebuffer(_gl.DRAW_FRAMEBUFFER,dstRenderTargetProperties.__webglFramebuffer);for(let i=0;i<depth2;i++)isSrc3D&&(_gl.framebufferTextureLayer(_gl.READ_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,properties.get(srcTexture).__webglTexture,srcLevel,minZ+i),_gl.framebufferTextureLayer(_gl.DRAW_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,properties.get(dstTexture).__webglTexture,dstLevel,dstZ+i)),_gl.blitFramebuffer(minX,minY,width,height,dstX,dstY,width,height,_gl.DEPTH_BUFFER_BIT,_gl.NEAREST);state.bindFramebuffer(_gl.READ_FRAMEBUFFER,null),state.bindFramebuffer(_gl.DRAW_FRAMEBUFFER,null)}else if(srcLevel!==0||srcTexture.isRenderTargetTexture||properties.has(srcTexture)){let srcTextureProperties=properties.get(srcTexture),dstTextureProperties=properties.get(dstTexture);state.bindFramebuffer(_gl.READ_FRAMEBUFFER,_srcFramebuffer),state.bindFramebuffer(_gl.DRAW_FRAMEBUFFER,_dstFramebuffer);for(let i=0;i<depth2;i++)isSrc3D?_gl.framebufferTextureLayer(_gl.READ_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,srcTextureProperties.__webglTexture,srcLevel,minZ+i):_gl.framebufferTexture2D(_gl.READ_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,_gl.TEXTURE_2D,srcTextureProperties.__webglTexture,srcLevel),isDst3D?_gl.framebufferTextureLayer(_gl.DRAW_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,dstTextureProperties.__webglTexture,dstLevel,dstZ+i):_gl.framebufferTexture2D(_gl.DRAW_FRAMEBUFFER,_gl.COLOR_ATTACHMENT0,_gl.TEXTURE_2D,dstTextureProperties.__webglTexture,dstLevel),srcLevel!==0?_gl.blitFramebuffer(minX,minY,width,height,dstX,dstY,width,height,_gl.COLOR_BUFFER_BIT,_gl.NEAREST):isDst3D?_gl.copyTexSubImage3D(glTarget,dstLevel,dstX,dstY,dstZ+i,minX,minY,width,height):_gl.copyTexSubImage2D(glTarget,dstLevel,dstX,dstY,minX,minY,width,height);state.bindFramebuffer(_gl.READ_FRAMEBUFFER,null),state.bindFramebuffer(_gl.DRAW_FRAMEBUFFER,null)}else isDst3D?srcTexture.isDataTexture||srcTexture.isData3DTexture?_gl.texSubImage3D(glTarget,dstLevel,dstX,dstY,dstZ,width,height,depth2,glFormat,glType,image.data):dstTexture.isCompressedArrayTexture?_gl.compressedTexSubImage3D(glTarget,dstLevel,dstX,dstY,dstZ,width,height,depth2,glFormat,image.data):_gl.texSubImage3D(glTarget,dstLevel,dstX,dstY,dstZ,width,height,depth2,glFormat,glType,image):srcTexture.isDataTexture?_gl.texSubImage2D(_gl.TEXTURE_2D,dstLevel,dstX,dstY,width,height,glFormat,glType,image.data):srcTexture.isCompressedTexture?_gl.compressedTexSubImage2D(_gl.TEXTURE_2D,dstLevel,dstX,dstY,image.width,image.height,glFormat,image.data):_gl.texSubImage2D(_gl.TEXTURE_2D,dstLevel,dstX,dstY,width,height,glFormat,glType,image);state.pixelStorei(_gl.UNPACK_ROW_LENGTH,currentUnpackRowLen),state.pixelStorei(_gl.UNPACK_IMAGE_HEIGHT,currentUnpackImageHeight),state.pixelStorei(_gl.UNPACK_SKIP_PIXELS,currentUnpackSkipPixels),state.pixelStorei(_gl.UNPACK_SKIP_ROWS,currentUnpackSkipRows),state.pixelStorei(_gl.UNPACK_SKIP_IMAGES,currentUnpackSkipImages),dstLevel===0&&dstTexture.generateMipmaps&&_gl.generateMipmap(glTarget),state.unbindTexture()},this.initRenderTarget=function(target){properties.get(target).__webglFramebuffer===void 0&&textures.setupRenderTarget(target)},this.initTexture=function(texture){texture.isCubeTexture?textures.setTextureCube(texture,0):texture.isData3DTexture?textures.setTexture3D(texture,0):texture.isDataArrayTexture||texture.isCompressedArrayTexture?textures.setTexture2DArray(texture,0):textures.setTexture2D(texture,0),state.unbindTexture()},this.resetState=function(){_currentActiveCubeFace=0,_currentActiveMipmapLevel=0,_currentRenderTarget=null,state.reset(),bindingStates.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return WebGLCoordinateSystem}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(colorSpace){this._outputColorSpace=colorSpace;let gl=this.getContext();gl.drawingBufferColorSpace=ColorManagement._getDrawingBufferColorSpace(colorSpace),gl.unpackColorSpace=ColorManagement._getUnpackColorSpace()}};var _changeEvent={type:"change"},_startEvent={type:"start"},_endEvent={type:"end"},_ray3=new Ray,_plane=new Plane,_TILT_LIMIT=Math.cos(70*MathUtils.DEG2RAD),_v=new Vector3,_twoPI=2*Math.PI,_STATE={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6},_EPS=1e-6,OrbitControls=class extends Controls{constructor(object,domElement=null){super(object,domElement),this.state=_STATE.NONE,this.target=new Vector3,this.cursor=new Vector3,this.minDistance=0,this.maxDistance=1/0,this.minZoom=0,this.maxZoom=1/0,this.minTargetRadius=0,this.maxTargetRadius=1/0,this.minPolarAngle=0,this.maxPolarAngle=Math.PI,this.minAzimuthAngle=-1/0,this.maxAzimuthAngle=1/0,this.enableDamping=!1,this.dampingFactor=.05,this.enableZoom=!0,this.zoomSpeed=1,this.enableRotate=!0,this.rotateSpeed=1,this.keyRotateSpeed=1,this.enablePan=!0,this.panSpeed=1,this.screenSpacePanning=!0,this.keyPanSpeed=7,this.zoomToCursor=!1,this.autoRotate=!1,this.autoRotateSpeed=2,this.keys={LEFT:"ArrowLeft",UP:"ArrowUp",RIGHT:"ArrowRight",BOTTOM:"ArrowDown"},this.mouseButtons={LEFT:MOUSE.ROTATE,MIDDLE:MOUSE.DOLLY,RIGHT:MOUSE.PAN},this.touches={ONE:TOUCH.ROTATE,TWO:TOUCH.DOLLY_PAN},this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this._cursorStyle="auto",this._domElementKeyEvents=null,this._lastPosition=new Vector3,this._lastQuaternion=new Quaternion,this._lastTargetPosition=new Vector3,this._quat=new Quaternion().setFromUnitVectors(object.up,new Vector3(0,1,0)),this._quatInverse=this._quat.clone().invert(),this._spherical=new Spherical,this._sphericalDelta=new Spherical,this._scale=1,this._panOffset=new Vector3,this._rotateStart=new Vector2,this._rotateEnd=new Vector2,this._rotateDelta=new Vector2,this._panStart=new Vector2,this._panEnd=new Vector2,this._panDelta=new Vector2,this._dollyStart=new Vector2,this._dollyEnd=new Vector2,this._dollyDelta=new Vector2,this._dollyDirection=new Vector3,this._mouse=new Vector2,this._performCursorZoom=!1,this._pointers=[],this._pointerPositions={},this._controlActive=!1,this._onPointerMove=onPointerMove.bind(this),this._onPointerDown=onPointerDown.bind(this),this._onPointerUp=onPointerUp.bind(this),this._onContextMenu=onContextMenu.bind(this),this._onMouseWheel=onMouseWheel.bind(this),this._onKeyDown=onKeyDown.bind(this),this._onTouchStart=onTouchStart.bind(this),this._onTouchMove=onTouchMove.bind(this),this._onMouseDown=onMouseDown.bind(this),this._onMouseMove=onMouseMove.bind(this),this._interceptControlDown=interceptControlDown.bind(this),this._interceptControlUp=interceptControlUp.bind(this),this.domElement!==null&&this.connect(this.domElement),this.update()}set cursorStyle(type){this._cursorStyle=type,type==="grab"?this.domElement.style.cursor="grab":this.domElement.style.cursor="auto"}get cursorStyle(){return this._cursorStyle}connect(element){super.connect(element),this.domElement.addEventListener("pointerdown",this._onPointerDown),this.domElement.addEventListener("pointercancel",this._onPointerUp),this.domElement.addEventListener("contextmenu",this._onContextMenu),this.domElement.addEventListener("wheel",this._onMouseWheel,{passive:!1}),this.domElement.getRootNode().addEventListener("keydown",this._interceptControlDown,{passive:!0,capture:!0}),this.domElement.style.touchAction="none"}disconnect(){this.state=_STATE.NONE,this.domElement.removeEventListener("pointerdown",this._onPointerDown),this.domElement.ownerDocument.removeEventListener("pointermove",this._onPointerMove),this.domElement.ownerDocument.removeEventListener("pointerup",this._onPointerUp),this.domElement.removeEventListener("pointercancel",this._onPointerUp),this.domElement.removeEventListener("wheel",this._onMouseWheel),this.domElement.removeEventListener("contextmenu",this._onContextMenu),this.stopListenToKeyEvents();let document2=this.domElement.getRootNode();document2.removeEventListener("keydown",this._interceptControlDown,{capture:!0}),document2.removeEventListener("keyup",this._interceptControlUp,{capture:!0}),this._controlActive=!1,this._pointers.length=0,this._pointerPositions={},this.domElement.style.touchAction="",this.domElement.style.cursor="auto"}dispose(){this.disconnect()}getPolarAngle(){return this._spherical.phi}getAzimuthalAngle(){return this._spherical.theta}getDistance(){return this.object.position.distanceTo(this.target)}listenToKeyEvents(domElement){domElement.addEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=domElement}stopListenToKeyEvents(){this._domElementKeyEvents!==null&&(this._domElementKeyEvents.removeEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=null)}saveState(){this.target0.copy(this.target),this.position0.copy(this.object.position),this.zoom0=this.object.zoom}reset(){this.target.copy(this.target0),this.object.position.copy(this.position0),this.object.zoom=this.zoom0,this.object.updateProjectionMatrix(),this.dispatchEvent(_changeEvent),this.update(),this.state=_STATE.NONE}pan(deltaX,deltaY){this._pan(deltaX,deltaY),this.update()}dollyIn(dollyScale){this._dollyIn(dollyScale),this.update()}dollyOut(dollyScale){this._dollyOut(dollyScale),this.update()}rotateLeft(angle){this._rotateLeft(angle),this.update()}rotateUp(angle){this._rotateUp(angle),this.update()}update(deltaTime=null){let position=this.object.position;_v.copy(position).sub(this.target),_v.applyQuaternion(this._quat),this._spherical.setFromVector3(_v),this.autoRotate&&this.state===_STATE.NONE&&this._rotateLeft(this._getAutoRotationAngle(deltaTime)),this.enableDamping?(this._spherical.theta+=this._sphericalDelta.theta*this.dampingFactor,this._spherical.phi+=this._sphericalDelta.phi*this.dampingFactor):(this._spherical.theta+=this._sphericalDelta.theta,this._spherical.phi+=this._sphericalDelta.phi);let min=this.minAzimuthAngle,max=this.maxAzimuthAngle;isFinite(min)&&isFinite(max)&&(min<-Math.PI?min+=_twoPI:min>Math.PI&&(min-=_twoPI),max<-Math.PI?max+=_twoPI:max>Math.PI&&(max-=_twoPI),min<=max?this._spherical.theta=Math.max(min,Math.min(max,this._spherical.theta)):this._spherical.theta=this._spherical.theta>(min+max)/2?Math.max(min,this._spherical.theta):Math.min(max,this._spherical.theta)),this._spherical.phi=Math.max(this.minPolarAngle,Math.min(this.maxPolarAngle,this._spherical.phi)),this._spherical.makeSafe(),this.enableDamping===!0?this.target.addScaledVector(this._panOffset,this.dampingFactor):this.target.add(this._panOffset),this.target.sub(this.cursor),this.target.clampLength(this.minTargetRadius,this.maxTargetRadius),this.target.add(this.cursor);let zoomChanged=!1;if(this.zoomToCursor&&this._performCursorZoom||this.object.isOrthographicCamera)this._spherical.radius=this._clampDistance(this._spherical.radius);else{let prevRadius=this._spherical.radius;this._spherical.radius=this._clampDistance(this._spherical.radius*this._scale),zoomChanged=prevRadius!=this._spherical.radius}if(_v.setFromSpherical(this._spherical),_v.applyQuaternion(this._quatInverse),position.copy(this.target).add(_v),this.object.lookAt(this.target),this.enableDamping===!0?(this._sphericalDelta.theta*=1-this.dampingFactor,this._sphericalDelta.phi*=1-this.dampingFactor,this._panOffset.multiplyScalar(1-this.dampingFactor)):(this._sphericalDelta.set(0,0,0),this._panOffset.set(0,0,0)),this.zoomToCursor&&this._performCursorZoom){let newRadius=null;if(this.object.isPerspectiveCamera){let prevRadius=_v.length();newRadius=this._clampDistance(prevRadius*this._scale);let radiusDelta=prevRadius-newRadius;this.object.position.addScaledVector(this._dollyDirection,radiusDelta),this.object.updateMatrixWorld(),zoomChanged=!!radiusDelta}else if(this.object.isOrthographicCamera){let mouseBefore=new Vector3(this._mouse.x,this._mouse.y,0);mouseBefore.unproject(this.object);let prevZoom=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),this.object.updateProjectionMatrix(),zoomChanged=prevZoom!==this.object.zoom;let mouseAfter=new Vector3(this._mouse.x,this._mouse.y,0);mouseAfter.unproject(this.object),this.object.position.sub(mouseAfter).add(mouseBefore),this.object.updateMatrixWorld(),newRadius=_v.length()}else console.warn("WARNING: OrbitControls.js encountered an unknown camera type - zoom to cursor disabled."),this.zoomToCursor=!1;newRadius!==null&&(this.screenSpacePanning?this.target.set(0,0,-1).transformDirection(this.object.matrix).multiplyScalar(newRadius).add(this.object.position):(_ray3.origin.copy(this.object.position),_ray3.direction.set(0,0,-1).transformDirection(this.object.matrix),Math.abs(this.object.up.dot(_ray3.direction))<_TILT_LIMIT?this.object.lookAt(this.target):(_plane.setFromNormalAndCoplanarPoint(this.object.up,this.target),_ray3.intersectPlane(_plane,this.target))))}else if(this.object.isOrthographicCamera){let prevZoom=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),prevZoom!==this.object.zoom&&(this.object.updateProjectionMatrix(),zoomChanged=!0)}return this._scale=1,this._performCursorZoom=!1,zoomChanged||this._lastPosition.distanceToSquared(this.object.position)>_EPS||8*(1-this._lastQuaternion.dot(this.object.quaternion))>_EPS||this._lastTargetPosition.distanceToSquared(this.target)>_EPS?(this.dispatchEvent(_changeEvent),this._lastPosition.copy(this.object.position),this._lastQuaternion.copy(this.object.quaternion),this._lastTargetPosition.copy(this.target),!0):!1}_getAutoRotationAngle(deltaTime){return deltaTime!==null?_twoPI/60*this.autoRotateSpeed*deltaTime:_twoPI/60/60*this.autoRotateSpeed}_getZoomScale(delta){let normalizedDelta=Math.abs(delta*.01);return Math.pow(.95,this.zoomSpeed*normalizedDelta)}_rotateLeft(angle){this._sphericalDelta.theta-=angle}_rotateUp(angle){this._sphericalDelta.phi-=angle}_panLeft(distance,objectMatrix){_v.setFromMatrixColumn(objectMatrix,0),_v.multiplyScalar(-distance),this._panOffset.add(_v)}_panUp(distance,objectMatrix){this.screenSpacePanning===!0?_v.setFromMatrixColumn(objectMatrix,1):(_v.setFromMatrixColumn(objectMatrix,0),_v.crossVectors(this.object.up,_v)),_v.multiplyScalar(distance),this._panOffset.add(_v)}_pan(deltaX,deltaY){let element=this.domElement;if(this.object.isPerspectiveCamera){let position=this.object.position;_v.copy(position).sub(this.target);let targetDistance=_v.length();targetDistance*=Math.tan(this.object.fov/2*Math.PI/180),this._panLeft(2*deltaX*targetDistance/element.clientHeight,this.object.matrix),this._panUp(2*deltaY*targetDistance/element.clientHeight,this.object.matrix)}else this.object.isOrthographicCamera?(this._panLeft(deltaX*(this.object.right-this.object.left)/this.object.zoom/element.clientWidth,this.object.matrix),this._panUp(deltaY*(this.object.top-this.object.bottom)/this.object.zoom/element.clientHeight,this.object.matrix)):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),this.enablePan=!1)}_dollyOut(dollyScale){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale/=dollyScale:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_dollyIn(dollyScale){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale*=dollyScale:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_updateZoomParameters(x,y){if(!this.zoomToCursor)return;this._performCursorZoom=!0;let rect=this.domElement.getBoundingClientRect(),dx=x-rect.left,dy=y-rect.top,w=rect.width,h=rect.height;this._mouse.x=dx/w*2-1,this._mouse.y=-(dy/h)*2+1,this._dollyDirection.set(this._mouse.x,this._mouse.y,1).unproject(this.object).sub(this.object.position).normalize()}_clampDistance(dist){return Math.max(this.minDistance,Math.min(this.maxDistance,dist))}_handleMouseDownRotate(event){this._rotateStart.set(event.clientX,event.clientY)}_handleMouseDownDolly(event){this._updateZoomParameters(event.clientX,event.clientX),this._dollyStart.set(event.clientX,event.clientY)}_handleMouseDownPan(event){this._panStart.set(event.clientX,event.clientY)}_handleMouseMoveRotate(event){this._rotateEnd.set(event.clientX,event.clientY),this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);let element=this.domElement;this._rotateLeft(_twoPI*this._rotateDelta.x/element.clientHeight),this._rotateUp(_twoPI*this._rotateDelta.y/element.clientHeight),this._rotateStart.copy(this._rotateEnd),this.update()}_handleMouseMoveDolly(event){this._dollyEnd.set(event.clientX,event.clientY),this._dollyDelta.subVectors(this._dollyEnd,this._dollyStart),this._dollyDelta.y>0?this._dollyOut(this._getZoomScale(this._dollyDelta.y)):this._dollyDelta.y<0&&this._dollyIn(this._getZoomScale(this._dollyDelta.y)),this._dollyStart.copy(this._dollyEnd),this.update()}_handleMouseMovePan(event){this._panEnd.set(event.clientX,event.clientY),this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd),this.update()}_handleMouseWheel(event){this._updateZoomParameters(event.clientX,event.clientY),event.deltaY<0?this._dollyIn(this._getZoomScale(event.deltaY)):event.deltaY>0&&this._dollyOut(this._getZoomScale(event.deltaY)),this.update()}_handleKeyDown(event){let needsUpdate=!1;switch(event.code){case this.keys.UP:event.ctrlKey||event.metaKey||event.shiftKey?this.enableRotate&&this._rotateUp(_twoPI*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(0,this.keyPanSpeed),needsUpdate=!0;break;case this.keys.BOTTOM:event.ctrlKey||event.metaKey||event.shiftKey?this.enableRotate&&this._rotateUp(-_twoPI*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(0,-this.keyPanSpeed),needsUpdate=!0;break;case this.keys.LEFT:event.ctrlKey||event.metaKey||event.shiftKey?this.enableRotate&&this._rotateLeft(_twoPI*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(this.keyPanSpeed,0),needsUpdate=!0;break;case this.keys.RIGHT:event.ctrlKey||event.metaKey||event.shiftKey?this.enableRotate&&this._rotateLeft(-_twoPI*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(-this.keyPanSpeed,0),needsUpdate=!0;break}needsUpdate&&(event.preventDefault(),this.update())}_handleTouchStartRotate(event){if(this._pointers.length===1)this._rotateStart.set(event.pageX,event.pageY);else{let position=this._getSecondPointerPosition(event),x=.5*(event.pageX+position.x),y=.5*(event.pageY+position.y);this._rotateStart.set(x,y)}}_handleTouchStartPan(event){if(this._pointers.length===1)this._panStart.set(event.pageX,event.pageY);else{let position=this._getSecondPointerPosition(event),x=.5*(event.pageX+position.x),y=.5*(event.pageY+position.y);this._panStart.set(x,y)}}_handleTouchStartDolly(event){let position=this._getSecondPointerPosition(event),dx=event.pageX-position.x,dy=event.pageY-position.y,distance=Math.sqrt(dx*dx+dy*dy);this._dollyStart.set(0,distance)}_handleTouchStartDollyPan(event){this.enableZoom&&this._handleTouchStartDolly(event),this.enablePan&&this._handleTouchStartPan(event)}_handleTouchStartDollyRotate(event){this.enableZoom&&this._handleTouchStartDolly(event),this.enableRotate&&this._handleTouchStartRotate(event)}_handleTouchMoveRotate(event){if(this._pointers.length==1)this._rotateEnd.set(event.pageX,event.pageY);else{let position=this._getSecondPointerPosition(event),x=.5*(event.pageX+position.x),y=.5*(event.pageY+position.y);this._rotateEnd.set(x,y)}this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);let element=this.domElement;this._rotateLeft(_twoPI*this._rotateDelta.x/element.clientHeight),this._rotateUp(_twoPI*this._rotateDelta.y/element.clientHeight),this._rotateStart.copy(this._rotateEnd)}_handleTouchMovePan(event){if(this._pointers.length===1)this._panEnd.set(event.pageX,event.pageY);else{let position=this._getSecondPointerPosition(event),x=.5*(event.pageX+position.x),y=.5*(event.pageY+position.y);this._panEnd.set(x,y)}this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd)}_handleTouchMoveDolly(event){let position=this._getSecondPointerPosition(event),dx=event.pageX-position.x,dy=event.pageY-position.y,distance=Math.sqrt(dx*dx+dy*dy);this._dollyEnd.set(0,distance),this._dollyDelta.set(0,Math.pow(this._dollyEnd.y/this._dollyStart.y,this.zoomSpeed)),this._dollyOut(this._dollyDelta.y),this._dollyStart.copy(this._dollyEnd);let centerX=(event.pageX+position.x)*.5,centerY=(event.pageY+position.y)*.5;this._updateZoomParameters(centerX,centerY)}_handleTouchMoveDollyPan(event){this.enableZoom&&this._handleTouchMoveDolly(event),this.enablePan&&this._handleTouchMovePan(event)}_handleTouchMoveDollyRotate(event){this.enableZoom&&this._handleTouchMoveDolly(event),this.enableRotate&&this._handleTouchMoveRotate(event)}_addPointer(event){this._pointers.push(event.pointerId)}_removePointer(event){delete this._pointerPositions[event.pointerId];for(let i=0;i<this._pointers.length;i++)if(this._pointers[i]==event.pointerId){this._pointers.splice(i,1);return}}_isTrackingPointer(event){for(let i=0;i<this._pointers.length;i++)if(this._pointers[i]==event.pointerId)return!0;return!1}_trackPointer(event){let position=this._pointerPositions[event.pointerId];position===void 0&&(position=new Vector2,this._pointerPositions[event.pointerId]=position),position.set(event.pageX,event.pageY)}_getSecondPointerPosition(event){let pointerId=event.pointerId===this._pointers[0]?this._pointers[1]:this._pointers[0];return this._pointerPositions[pointerId]}_customWheelEvent(event){let mode=event.deltaMode,newEvent={clientX:event.clientX,clientY:event.clientY,deltaY:event.deltaY};switch(mode){case 1:newEvent.deltaY*=16;break;case 2:newEvent.deltaY*=100;break}return event.ctrlKey&&!this._controlActive&&(newEvent.deltaY*=10),newEvent}};function onPointerDown(event){this.enabled!==!1&&(this._pointers.length===0&&(this.domElement.setPointerCapture(event.pointerId),this.domElement.ownerDocument.addEventListener("pointermove",this._onPointerMove),this.domElement.ownerDocument.addEventListener("pointerup",this._onPointerUp)),!this._isTrackingPointer(event)&&(this._addPointer(event),event.pointerType==="touch"?this._onTouchStart(event):this._onMouseDown(event),this._cursorStyle==="grab"&&(this.domElement.style.cursor="grabbing")))}function onPointerMove(event){this.enabled!==!1&&(event.pointerType==="touch"?this._onTouchMove(event):this._onMouseMove(event))}function onPointerUp(event){switch(this._removePointer(event),this._pointers.length){case 0:this.domElement.releasePointerCapture(event.pointerId),this.domElement.ownerDocument.removeEventListener("pointermove",this._onPointerMove),this.domElement.ownerDocument.removeEventListener("pointerup",this._onPointerUp),this.dispatchEvent(_endEvent),this.state=_STATE.NONE,this._cursorStyle==="grab"&&(this.domElement.style.cursor="grab");break;case 1:let pointerId=this._pointers[0],position=this._pointerPositions[pointerId];this._onTouchStart({pointerId,pageX:position.x,pageY:position.y});break}}function onMouseDown(event){let mouseAction;switch(event.button){case 0:mouseAction=this.mouseButtons.LEFT;break;case 1:mouseAction=this.mouseButtons.MIDDLE;break;case 2:mouseAction=this.mouseButtons.RIGHT;break;default:mouseAction=-1}switch(mouseAction){case MOUSE.DOLLY:if(this.enableZoom===!1)return;this._handleMouseDownDolly(event),this.state=_STATE.DOLLY;break;case MOUSE.ROTATE:if(event.ctrlKey||event.metaKey||event.shiftKey){if(this.enablePan===!1)return;this._handleMouseDownPan(event),this.state=_STATE.PAN}else{if(this.enableRotate===!1)return;this._handleMouseDownRotate(event),this.state=_STATE.ROTATE}break;case MOUSE.PAN:if(event.ctrlKey||event.metaKey||event.shiftKey){if(this.enableRotate===!1)return;this._handleMouseDownRotate(event),this.state=_STATE.ROTATE}else{if(this.enablePan===!1)return;this._handleMouseDownPan(event),this.state=_STATE.PAN}break;default:this.state=_STATE.NONE}this.state!==_STATE.NONE&&this.dispatchEvent(_startEvent)}function onMouseMove(event){switch(this.state){case _STATE.ROTATE:if(this.enableRotate===!1)return;this._handleMouseMoveRotate(event);break;case _STATE.DOLLY:if(this.enableZoom===!1)return;this._handleMouseMoveDolly(event);break;case _STATE.PAN:if(this.enablePan===!1)return;this._handleMouseMovePan(event);break}}function onMouseWheel(event){this.enabled===!1||this.enableZoom===!1||this.state!==_STATE.NONE||(event.preventDefault(),this.dispatchEvent(_startEvent),this._handleMouseWheel(this._customWheelEvent(event)),this.dispatchEvent(_endEvent))}function onKeyDown(event){this.enabled!==!1&&this._handleKeyDown(event)}function onTouchStart(event){switch(this._trackPointer(event),this._pointers.length){case 1:switch(this.touches.ONE){case TOUCH.ROTATE:if(this.enableRotate===!1)return;this._handleTouchStartRotate(event),this.state=_STATE.TOUCH_ROTATE;break;case TOUCH.PAN:if(this.enablePan===!1)return;this._handleTouchStartPan(event),this.state=_STATE.TOUCH_PAN;break;default:this.state=_STATE.NONE}break;case 2:switch(this.touches.TWO){case TOUCH.DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchStartDollyPan(event),this.state=_STATE.TOUCH_DOLLY_PAN;break;case TOUCH.DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchStartDollyRotate(event),this.state=_STATE.TOUCH_DOLLY_ROTATE;break;default:this.state=_STATE.NONE}break;default:this.state=_STATE.NONE}this.state!==_STATE.NONE&&this.dispatchEvent(_startEvent)}function onTouchMove(event){switch(this._trackPointer(event),this.state){case _STATE.TOUCH_ROTATE:if(this.enableRotate===!1)return;this._handleTouchMoveRotate(event),this.update();break;case _STATE.TOUCH_PAN:if(this.enablePan===!1)return;this._handleTouchMovePan(event),this.update();break;case _STATE.TOUCH_DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchMoveDollyPan(event),this.update();break;case _STATE.TOUCH_DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchMoveDollyRotate(event),this.update();break;default:this.state=_STATE.NONE}}function onContextMenu(event){this.enabled!==!1&&event.preventDefault()}function interceptControlDown(event){event.key==="Control"&&(this._controlActive=!0,this.domElement.getRootNode().addEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}function interceptControlUp(event){event.key==="Control"&&(this._controlActive=!1,this.domElement.getRootNode().removeEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}var _tempNormal=new Vector3;function getUv(faceDirVector,normal,uvAxis,projectionAxis,radius,sideLength){let totArcLength=2*Math.PI*radius/4,centerLength=Math.max(sideLength-2*radius,0),halfArc=Math.PI/4;_tempNormal.copy(normal),_tempNormal[projectionAxis]=0,_tempNormal.normalize();let arcUvRatio=.5*totArcLength/(totArcLength+centerLength),arcAngleRatio=1-_tempNormal.angleTo(faceDirVector)/halfArc;return Math.sign(_tempNormal[uvAxis])===1?arcAngleRatio*arcUvRatio:centerLength/(totArcLength+centerLength)+arcUvRatio+arcUvRatio*(1-arcAngleRatio)}var RoundedBoxGeometry=class _RoundedBoxGeometry extends BoxGeometry{constructor(width=1,height=1,depth=1,segments=2,radius=.1){let totalSegments=segments*2+1;if(radius=Math.min(width/2,height/2,depth/2,radius),super(1,1,1,totalSegments,totalSegments,totalSegments),this.type="RoundedBoxGeometry",this.parameters={width,height,depth,segments,radius},totalSegments===1)return;let geometry2=this.toNonIndexed();this.index=null,this.attributes.position=geometry2.attributes.position,this.attributes.normal=geometry2.attributes.normal,this.attributes.uv=geometry2.attributes.uv;let position=new Vector3,normal=new Vector3,box=new Vector3(width,height,depth).divideScalar(2).subScalar(radius),positions=this.attributes.position.array,normals=this.attributes.normal.array,uvs=this.attributes.uv.array,faceTris=positions.length/6,faceDirVector=new Vector3,halfSegmentSize=.5/totalSegments;for(let i=0,j=0;i<positions.length;i+=3,j+=2)switch(position.fromArray(positions,i),normal.copy(position),normal.x-=Math.sign(normal.x)*halfSegmentSize,normal.y-=Math.sign(normal.y)*halfSegmentSize,normal.z-=Math.sign(normal.z)*halfSegmentSize,normal.normalize(),positions[i+0]=box.x*Math.sign(position.x)+normal.x*radius,positions[i+1]=box.y*Math.sign(position.y)+normal.y*radius,positions[i+2]=box.z*Math.sign(position.z)+normal.z*radius,normals[i+0]=normal.x,normals[i+1]=normal.y,normals[i+2]=normal.z,Math.floor(i/faceTris)){case 0:faceDirVector.set(1,0,0),uvs[j+0]=getUv(faceDirVector,normal,"z","y",radius,depth),uvs[j+1]=1-getUv(faceDirVector,normal,"y","z",radius,height);break;case 1:faceDirVector.set(-1,0,0),uvs[j+0]=1-getUv(faceDirVector,normal,"z","y",radius,depth),uvs[j+1]=1-getUv(faceDirVector,normal,"y","z",radius,height);break;case 2:faceDirVector.set(0,1,0),uvs[j+0]=1-getUv(faceDirVector,normal,"x","z",radius,width),uvs[j+1]=getUv(faceDirVector,normal,"z","x",radius,depth);break;case 3:faceDirVector.set(0,-1,0),uvs[j+0]=1-getUv(faceDirVector,normal,"x","z",radius,width),uvs[j+1]=1-getUv(faceDirVector,normal,"z","x",radius,depth);break;case 4:faceDirVector.set(0,0,1),uvs[j+0]=1-getUv(faceDirVector,normal,"x","y",radius,width),uvs[j+1]=1-getUv(faceDirVector,normal,"y","x",radius,height);break;case 5:faceDirVector.set(0,0,-1),uvs[j+0]=getUv(faceDirVector,normal,"x","y",radius,width),uvs[j+1]=1-getUv(faceDirVector,normal,"y","x",radius,height);break}}static fromJSON(data){return new _RoundedBoxGeometry(data.width,data.height,data.depth,data.segments,data.radius)}};var clamp2=(n,a,b)=>Math.max(a,Math.min(b,Number(n)||0)),dimensions=room=>({width:room.cols,depth:room.frows,height:Math.max(1.6,room.wrows*1.1+.35)}),surfaceHeight=it=>it.ledge?.1:Math.max(.12,(it.surface||22)/32);function hostOf(room,id,all){if(!id)return null;if(id[0]==="#"){let f=(room.fix||[]).find(x=>x.t===id.slice(1)&&x.surface);return f?{id,it:{...f,spot:f.layer,surface:f.surface,ledge:f.layer==="wall"},q:{r:room.id,x:f.x*20,y:f.y*20,f:0}}:null}return all.find(o=>o.id===id)||null}function placement(room,o,all=[],depth=0){let{width,depth:d,height}=dimensions(room),{it,q}=o,w=it.w||1,h=it.h||1,host=depth<3?hostOf(room,q.on,all):null;if(host){let p=placement(room,host,all,depth+1),hw=host.it.w,offset=q.x/20+w/2-hw/2;return{x:p.x+(host.q.f?-offset:offset),y:p.y+surfaceHeight(host.it),z:host.it.spot==="wall"?p.z+.28:p.z-host.it.h/2+q.y/20+h/2}}return{x:q.x/20+w/2-width/2,y:it.spot==="wall"?height-(q.y/20+h/2)*1.1:it.spot==="rug"?.018:0,z:it.spot==="wall"?-d/2+.1:q.y/20+h/2-d/2}}function hitPlacement(room,it,hit,{host=null,all=[],f=0}={}){let{width,depth,height}=dimensions(room),w=it.w||1,h=it.h||1,x,y,on;if(host&&it.spot==="top"&&(host.it.surface||host.it.ledge)){let p=placement(room,host,all),off=(hit.x-p.x)*(host.q.f?-1:1);x=clamp2(Math.round((off+host.it.w/2-w/2)*20),0,Math.max(0,(host.it.w-w)*20)),y=host.it.spot==="wall"?0:clamp2(Math.round((hit.z-p.z+host.it.h/2-h/2)*20),0,Math.max(0,(host.it.h-h)*20)),on=host.id}else x=clamp2(Math.round((hit.x+width/2-w/2)*20),0,Math.max(0,(width-w)*20)),y=it.spot==="wall"?(height-hit.y)/1.1-h/2:hit.z+depth/2-h/2,y=clamp2(Math.round(y*20),0,Math.max(0,((it.spot==="wall"?room.wrows:room.frows)-h)*20));return{r:room.id,x,y,f,...on?{on}:{}}}function editIntent(state,item,hit){return state.busy?null:state.edit?state.remote&&!state.coop?null:state.held?{type:"place",point:hit}:item&&!item.mate?{type:"select",uid:item.id}:null:{type:"walk",uid:item?.id||"",point:hit}}var boundedActors=(people=[],children=[],pets=[])=>[...people.slice(0,12),...children.slice(0,8),...pets.slice(0,8)];var KINDS=["ky_tuc_xa","tro_moi","tap_the","can_ho_studio","can_ho_mini","can_ho_1pn","can_ho_2pn","penthouse","nha_pho","nha_san","biet_thu_vuon","biet_thu_song"];function interiorProfile(room,scope=""){let bits=String(scope).split(":"),kind=KINDS.find(k=>bits.includes(k))||(bits[0]==="estate"?"estate":bits[0]==="attic"?"attic":"home"),type=room.type||room.id,privateRoom=["bath","bathc","bed","bed2","suite","cinema","cellar","closet"].includes(type);return{kind,id:kind+":"+type,room:type,windowDepth:{can_ho_studio:.6,can_ho_1pn:.85,penthouse:.72,biet_thu_song:.9}[kind]||0,sideHeight:privateRoom?null:{can_ho_mini:.75,nha_pho:.36,nha_san:.5,biet_thu_vuon:.42,biet_thu_song:.58}[kind]??null}}function addInteriorArchitecture(room,scope,painters,size){let profile=interiorProfile(room,scope),{width:w,depth:d,height:h}=size,{solid,back,side}=painters,wrap=p=>Object.fromEntries(Object.entries(p).map(([name,fn])=>[name,(...args)=>{let m=fn(...args);return m.userData.architectureOnly=!0,m}])),A=wrap(solid),W=wrap(back),L=wrap(side),B=A.box,z=-d/2-.05,wood="#956d4a",cream="#fff0d5",mint="#85ac9b",dark="#5f7772",glass="#a8cbd0",pillar=(x,zz,top=h)=>A.box(x,top/2,zz,.15,top,.15,cream);function cornice(level=h){W.box(0,level,z,w+.35,.18,.34,cream),L.box(-w/2-.07,level,0,.32,.18,d+.2,cream)}function arch(x,zz,span,rise,base=h-.55,p=W){for(let i=0;i<12;i++){let a=i*Math.PI/12,b=(i+1)*Math.PI/12,x1=Math.cos(a)*span/2,y1=Math.sin(a)*rise,x2=Math.cos(b)*span/2,y2=Math.sin(b)*rise,m=p.box(x+(x1+x2)/2,base+(y1+y2)/2,zz,Math.hypot(x2-x1,y2-y1)+.035,.13,.17,cream);m.rotation.z=Math.atan2(y2-y1,x2-x1)}}function rafters(pitch=.27,woodColor=wood){for(let zz=-d/2;zz<d/2;zz+=Math.max(.65,d/4))for(let s of[-1,1]){let m=B(s*w*.25,h+.25,zz,w*.51,.12,.12,woodColor);m.rotation.z=-s*pitch}B(0,h+.25+w*.25*Math.sin(pitch),0,.14,.14,d+.2,woodColor);let eave=h+.25-w*.255*Math.sin(pitch);for(let x of[-w/2-.05,w/2+.05])B(x,eave,0,.13,.15,d+.2,woodColor),pillar(x,d/2+.04,eave)}function bay(span=w*.55,depth=.55){W.box(0,h+.18,z-depth*.45,span,.36,.07,glass);for(let x of[-span/2,0,span/2])W.box(x,h+.18,z-depth*.45+.05,.065,.42,.1,cream);W.box(0,h+.4,z-depth*.3,span+.3,.1,depth*.6+.25,cream)}function veranda(){L.box(-w/2-.53,-.02,0,.95,.12,d+.15,wood);for(let zz of[-d*.42,0,d*.42]){let m=L.cyl(-w/2-.9,h/2,zz,.12,h,.12,cream);m.userData.architectureOnly=!0}L.box(-w/2-.55,h,0,1.1,.14,d+.2,wood);for(let zz=-d/2;zz<=d/2;zz+=.36)L.box(-w/2-.55,h+.12,zz,1.2,.08,.065,cream)}if(room.out){if(["pool","infinity"].includes(profile.room)){for(let x of[-w/2-.13,w/2+.13])for(let zz of[-d/2,d/2])pillar(x,zz,1.65);B(0,.09,-d/2-.25,w+.4,.14,.38,cream),B(0,.2,-d/2-.27,w+.35,.035,.16,glass)}else if(["yard","pavilion"].includes(profile.room)){veranda();for(let zz=-d/2;zz<=d/2;zz+=.5)L.box(-w/2-.14,.7,zz,.1,1.4,.07,wood);L.box(-w/2-.14,1.35,0,.14,.12,d+.2,wood)}else{W.box(0,.58,z,w+.3,1.1,.055,glass);for(let x=-w/2;x<=w/2;x+=.6)W.box(x,.58,z+.06,.04,1.2,.05,dark);W.box(0,1.2,z+.07,w+.35,.07,.09,wood),(profile.kind==="penthouse"||profile.room==="terrace")&&(veranda(),B(0,2.35,z,w+.4,.12,.8,cream))}return profile}switch(profile.kind){case"attic":rafters(.36);for(let x=-w/2;x<w/2;x+=.55)W.box(x,h*.72,z+.13,.04,.9,.05,wood);break;case"ky_tuc_xa":for(let x of[-w/2-.07,w/2+.07])for(let zz of[-d/2,d/2])pillar(x,zz,h+.5);B(0,h+.27,-d*.25,w+.22,.18,d*.55,wood);for(let x=-w/2;x<=w/2;x+=.45)W.box(x,h+.56,-d*.49,.055,.65,.055,mint);W.box(0,h+.85,-d*.49,w,.07,.07,mint),L.box(-w/2-.1,h*.6,0,.09,.85,d*.75,mint);break;case"tro_moi":B(0,h+.15,-d*.28,w+.15,.18,d*.46,wood);for(let x=-w/2;x<=w/2;x+=.52)W.box(x,h+.48,-d*.05,.055,.62,.055,dark);W.box(0,h+.8,-d*.05,w,.07,.07,wood);for(let zz=-d/2;zz<d/2;zz+=.65)L.box(-w/2-.12,h-.3,zz,.25,.12,.14,wood);break;case"tap_the":W.box(0,h-.17,z+.12,w,.25,.26,"#b4afa0");for(let x of[-w*.45,w*.4])W.box(x,h/2,z+.09,.19,h,.23,"#b4afa0");L.cyl(-w/2-.07,h/2,d*.2,.07,h,.07,"#929f98");for(let zz=-d*.4;zz<d*.5;zz+=.32)L.box(-w/2-.15,.67,zz,.12,.9,.07,mint);break;case"can_ho_studio":bay(w*.72,.6),W.box(0,h+.2,z,w+.4,.35,.18,cream),L.box(-w/2-.1,h*.5,0,.08,h,d*.82,glass);break;case"can_ho_mini":cornice(),arch(0,z+.14,w*.65,.38,h-.4),veranda();break;case"can_ho_1pn":bay(w*.43,.85),cornice();for(let x=-w/2;x<w/2;x+=.7)W.box(x,h-.08,z+.16,.11,.3,.4,wood);break;case"can_ho_2pn":cornice();for(let x of[-w*.25,w*.25])arch(x,z+.16,w*.45,.52,h-.55);arch(0,0,w+.1,.5,h-.55,A);for(let x of[-w/2-.06,w/2+.06])pillar(x,0,h-.55);break;case"penthouse":rafters(.16,dark),bay(w*.82,.72);for(let x=-w/2;x<=w/2;x+=w/3)W.box(x,h+.2,z,.1,.55,.1,dark);W.box(0,h+.45,z,w,.055,.6,glass),veranda();break;case"nha_pho":cornice(h+.17);for(let i=0;i<8;i++)L.box(-w/2-.58,.13+i*.19,-d*.36+i*d*.09,.9,.14+i*.38,d*.085,wood);L.box(-w/2-.65,h+.1,-d*.1,1.05,.16,d*.85,cream),W.box(w*.35,h+.38,z,w*.3,.65,.14,glass);break;case"nha_san":veranda(),rafters(.23),arch(0,z+.13,w*.8,.5,h-.4);break;case"biet_thu_vuon":veranda(),cornice();for(let x of[-w*.33,0,w*.33])arch(x,z+.17,w*.3,.58,h-.5),W.box(x-w*.15,h/2,z+.15,.16,h,.23,cream);rafters(.22);break;case"biet_thu_song":bay(w*.86,.9),cornice(h+.35),W.box(0,h+.1,z,w,.28,.13,glass);for(let zz=-d/2;zz<d/2;zz+=d/3)B(0,h+.28,zz,w+.4,.16,.16,cream);veranda();break;case"estate":if(cornice(h+.2),["living","suite","bed","hall"].includes(profile.room)){veranda();for(let x of[-w*.26,w*.26])arch(x,z+.18,w*.48,.6,h-.4);rafters(.12)}break;default:cornice()}if(["bath","bathc"].includes(profile.room)){for(let x=-w/2;x<w/2;x+=.45)W.box(x,.7,z+.12,.42,1.36,.05,"#b6d0c5"),W.box(x,1.41,z+.15,.42,.04,.07,cream);for(let y=.2;y<h;y+=.42)L.box(-w/2+.035,y,0,.035,.025,d,"#f5eade")}else if(profile.room==="kitchen"){W.box(-w*.12,h-.24,z+.18,w*.55,.36,.34,wood);for(let x=-w*.38;x<w*.18;x+=.42)W.box(x,h-.25,z+.37,.035,.28,.025,cream)}else if(["bed","bed2","suite"].includes(profile.room)){W.box(0,h-.05,z+.17,w*.72,.16,.38,wood);for(let x of[-w*.34,w*.34])W.box(x,h*.57,z+.19,.13,h*.82,.23,cream)}else if(profile.room==="cinema"){for(let x=-w/2;x<w/2;x+=.36)W.box(x,h/2,z+.15,.16,h,.12,"#8e5154");L.box(-w/2+.03,h/2,0,.08,h,d,"#65575c")}else if(profile.room==="cellar")for(let zz of[-d*.44,0,d*.44]){arch(0,zz,w+.15,.6,h-.3,A);for(let x of[-w/2-.075,w/2+.075])pillar(x,zz,h-.3)}else if(profile.room==="gym")L.box(-w/2+.035,h*.55,0,.045,h*.73,d*.85,glass),B(0,h-.12,z,w*.85,.04,.045,cream);else if(profile.room==="study"){for(let x of[-w*.42,w*.42])W.box(x,h/2,z+.18,.13,h,.25,wood);W.box(0,h-.12,z+.16,w,.16,.35,wood)}else if(profile.room==="closet")cornice(h-.08),W.box(0,h*.4,z+.1,w,.035,.16,"#d5a193");else if(profile.room==="showroom"){for(let x=-w/2;x<=w/2;x+=w/3)B(x,h+.07,0,.1,.16,d+.2,dark);L.box(-w/2+.02,.17,0,.08,.09,d,"#d5b673")}return profile}var P={wood:"#c99260",dark:"#79563f",cream:"#fff3df",pink:"#efa8ba",mint:"#9acbb3",blue:"#9bc7df",leaf:"#6da775",gold:"#edc773",ink:"#51494b"};function resources(){let geometries={box:new RoundedBoxGeometry(1,1,1,2,.07),ball:new SphereGeometry(.5,12,8),cylinder:new CylinderGeometry(.5,.5,1,12),cone:new ConeGeometry(.5,1,12),ring:new TorusGeometry(.36,.1,8,20)},materials=new Map;return{geometries,material(color,glow=!1,wall=""){let key=color+glow+wall;return materials.has(key)||materials.set(key,new MeshStandardMaterial({color,roughness:.87,metalness:0,...glow?{emissive:color,emissiveIntensity:.35}:{}})),materials.get(key)},prune(root){let used=new Set;root.traverse(o=>{o.material&&used.add(o.material)});for(let[key,m]of materials)used.has(m)||(m.dispose(),materials.delete(key))},dispose(){for(let g of Object.values(geometries))g.dispose();for(let m of materials.values())m.dispose();materials.clear()}}}function sculpt(group,R,wall=""){function shape(kind,x,y,z,w,h,d,c,glow=!1){let m=new Mesh(R.geometries[kind],R.material(c,glow,wall));return m.position.set(x,y,z),m.scale.set(w,h,d),m.castShadow=!0,m.receiveShadow=!0,wall&&(m.userData.wall=wall),group.add(m),m}return{box:(...a)=>shape("box",...a),ball:(...a)=>shape("ball",...a),cyl:(...a)=>shape("cylinder",...a),cone:(...a)=>shape("cone",...a),ring:(...a)=>shape("ring",...a)}}var sets={sofa:"sofa sofa_don ghe_da_bo ghe_rap_doi",bed:"giuong giuong_don giuong_king nem sap_go",shelf:"ke_sach ke_go ke_tivi ke_giay ke_bep ke_treo ke_go_treo ke_tron ke_khan ke_tam ke_my_pham ke_chen tu_giay",wardrobe:"tu_quan_ao tu_ngan_keo tu_dau_giuong tu_thuoc chan_bat",fridge:"tu_lanh tu_lanh_magnet",washer:"may_giat",screen:"tv may_choi_game ban_gaming",fan:"quat quat_mini quat_tran",guitar:"dan dan_bau",piano:"piano",speaker:"loa loa_cot radio hop_nhac",plush:"gau_bong gau_bong_lon tho_bong goi_om goi_tua",rug:"tham tham_hoa tham_tam tham_tron tham_dai",curtain:"rem rem_voan rem_giuong man_tuyn ao_choang",mirror:"guong guong_tam guong_dung ban_trang_diem",clock:"dong_ho dong_ho_qua_lac dong_ho_cuc_cu dong_ho_bao_thuc",tub:"bon_tam bon_rua",shower:"buong_tam",basket:"gio_do_tam gio_giat gio_trai_cay mam_ngu_qua ro_rau",vessel:"am_chen noi_com am_sieu_toc may_ca_phe may_xay hu_dua binh_gom chum_nuoc binh_tuoi coc_ban_chai thung_ruou",oven:"lo_nuong lo_vi_song lo_nuong_banh bep_ga lo_suoi_ngoai",umbrella:"du_che ban_ngoai",swing:"xich_du ghe_trung",hammock:"vong",float:"phao phao_hong_hac",water:"be_ca ho_ca_koi",birdcage:"long_chim",bike:"xe_dap xe_may_co xe_do_choi",tent:"leu_choi nha_cho",globe:"qua_dia_cau cau_tuyet",gym:"may_chay_bo gia_ta",telescope:"kinh_thien_van",rack:"moc_ao treo_noi"},byId=new Map(Object.entries(sets).flatMap(([family,ids])=>ids.split(" ").map(id=>[id,family])));function familyOf(it){return byId.has(it.id)?byId.get(it.id):it.id==="cay_dua"||it.id==="cay_mai"||it.id==="canh_dao"||it.cat==="plant"?"plant":it.cat==="light"||it.id==="den_vuon"||it.id==="long_den_sao"||it.id==="den_keo_quan"?"lamp":it.spot==="rug"?"rug":it.tags?.includes("seat")?"chair":it.tags?.includes("table")||it.tags?.includes("desk")||it.cat==="table"?"table":it.spot==="wall"?"art":{bath:"bathkit",bep:"kitchenkit",le:"festival",bed:"cushion",pool:"garden",fun:"toy"}[it.cat]||"art"}function furniture(it,tint,R){let g=new Group,s=sculpt(g,R),B=s.box,C=s.cyl,S=s.ball,K=s.cone,Q=s.ring,w=(it.w||1)*.9,d=(it.h||1)*.87,family=familyOf(it),color=tint||{table:P.pink,bed:P.wood,plant:"#df9a72",light:P.gold,bath:P.blue,pool:P.mint,bep:P.cream,wall:P.wood,fun:P.mint,le:"#da7377"}[it.cat]||P.wood;g.userData.family=family,g.name=it.name||it.id;let legs=(h=.6)=>{for(let x of[-w*.38,w*.38])for(let z of[-d*.35,d*.35])B(x,h/2,z,.09,h,.09,P.dark)},tabletop=(h=surfaceHeight(it))=>(legs(h),B(0,h,0,w,.12,d,color),h),plant=(x=0,z=0,scale=1)=>{C(x,.2*scale,z,.48*scale,.4*scale,.48*scale,color),C(x,.41*scale,z,.45*scale,.06*scale,.45*scale,P.dark),C(x,.65*scale,z,.04,.56*scale,.04,P.dark);for(let i=0;i<5;i++){let a=i*2.4,leaf=S(x+Math.cos(a)*.17*scale,(.66+i*.08)*scale,z+Math.sin(a)*.13*scale,.3*scale,.12*scale,.48*scale,i%2?P.leaf:P.mint);leaf.rotation.z=Math.cos(a)*.6}if(/hoa|mai|dao|sen|cuc/.test(it.id))for(let i=0;i<4;i++)S(x+Math.cos(i*2)*.22*scale,1.05*scale,z+Math.sin(i*2)*.17*scale,.18,.18,.18,P.pink)};switch(family){case"sofa":legs(.19),B(0,.4,0,w,.4,d,color),B(0,.88,-d*.4,w,.65,.2,color);for(let x of[-w*.43,w*.43])B(x,.65,0,.2,.55,d,color);for(let i=0;i<Math.ceil(w);i++)B(-w*.32+i*w/Math.ceil(w),.66,.04,w/Math.ceil(w)*.72,.15,d*.7,P.cream);S(w*.28,.83,-.12,.32,.32,.15,P.gold);break;case"bed":{let h=surfaceHeight(it);legs(h*.55),B(0,h*.7,0,w,.2,d,P.dark),B(0,h,0,w,.23,d,P.cream),B(0,h+.14,d*.22,w*.98,.1,d*.54,color),B(0,h+.32,-d*.47,w,.8,.13,P.wood);for(let x of[-w*.24,w*.24])B(x,h+.19,-d*.28,w*.37,.16,d*.23,P.cream);break}case"table":{let h=tabletop();if(it.id==="ban_co_tuong"){B(0,h+.08,0,w*.65,.03,d*.7,P.cream);for(let i=0;i<5;i++)C(-w*.25+i*.2,h+.12,-d*.15,.08,.05,.08,P.ink)}it.id==="may_may"&&(B(0,h+.25,0,.5,.4,.3,P.ink),B(.2,h+.15,.1,.1,.2,.1,P.gold));break}case"chair":{let stool=it.id==="ghe_dau",lounge=/tam_nang|bap_benh|luoi/.test(it.id);if(legs(.42),B(0,.48,0,w,.17,d,color),stool||B(0,lounge?.66:.9,-d*.38,w*.95,lounge?.45:.9,.16,color),!stool)for(let x of[-w*.43,w*.43])B(x,.68,0,.1,.1,d*.9,P.wood);break}case"shelf":{let h=it.spot==="wall"?.75:1.5;B(-w*.46,h/2,0,.09,h,d,P.dark),B(w*.46,h/2,0,.09,h,d,P.dark),B(0,h/2,-d*.43,w,h,.07,P.wood);for(let j=0;j<3;j++){B(0,j*h/2+.04,0,w,.08,d,color);for(let i=0;i<3;i++)B(-w*.28+i*w*.27,j*h/2+.19,0,w*.17,.28,d*.6,[P.mint,P.pink,P.gold][i])}break}case"wardrobe":{let h=it.id==="tu_dau_giuong"?surfaceHeight(it):1.75;B(0,h/2,0,w,h,d,color);for(let x of[-w*.24,w*.24])B(x,h/2,d*.5,w*.45,h*.9,.06,P.cream),C(x*.45,h*.55,d*.56,.06,.13,.06,P.gold);break}case"fridge":B(0,.93,0,w,1.86,d,color);for(let[h,y]of[[.56,1.55],[1.13,.68]])B(0,y,d*.5,w*.92,h,.05,P.cream),B(w*.3,y,d*.56,.07,.3,.07,P.dark);if(it.id.endsWith("magnet"))for(let i=0;i<3;i++)B(-.18+i*.16,1.4,d*.55,.1,.1,.03,[P.pink,P.gold,P.blue][i]);break;case"washer":B(0,.57,0,w,1.12,d,color),B(0,1.02,d*.5,w*.9,.12,.04,P.cream),Q(0,.51,d*.51,.9,.9,.8,P.cream),C(0,.51,d*.5,.52,.06,.52,P.blue).rotation.x=Math.PI/2;break;case"screen":{let h=it.id==="ban_gaming"?tabletop():.18;B(0,h,0,w*.65,.12,d*.55,P.dark),B(0,h+.2,-.12,.15,.4,.12,P.dark),B(0,h+.7,-.12,w,1,.14,P.ink),B(0,h+.7,-.035,w*.9,.85,.035,P.blue,!0),B(-w*.18,h+.5,-.01,w*.4,.22,.025,P.mint);break}case"fan":C(0,.06,0,w*.6,.1,d*.6,color),C(0,.47,0,.08,.9,.08,P.cream),Q(0,.95,0,.9,.9,.75,color);for(let i=0;i<3;i++){let blade=S(Math.sin(i*2.1)*.18,.95+Math.cos(i*2.1)*.18,0,.16,.4,.06,P.blue);blade.rotation.z=-i*2.1}break;case"guitar":S(0,.42,0,w*.7,.8,d*.4,color),S(0,.67,0,w*.5,.5,d*.35,P.wood),B(0,1.15,0,.13,.9,.1,P.dark),C(0,.6,d*.21,.19,.025,.19,P.dark).rotation.x=Math.PI/2;break;case"piano":legs(.6),B(0,1,0,w,1.2,d*.8,color),B(0,.68,d*.45,w,.15,d*.5,P.cream);for(let i=0;i<12;i++)B(-w*.46+i*w/12,.78,d*.4,.065,.07,.2,P.ink);break;case"speaker":B(0,.62,0,w*.8,1.24,d*.8,color);for(let y of[.35,.87])C(0,y,d*.42,.35,.07,.35,P.ink).rotation.x=Math.PI/2,C(0,y,d*.46,.12,.03,.12,P.gold).rotation.x=Math.PI/2;break;case"plush":S(0,.32,0,w*.74,.65,d*.72,color),S(0,.7,0,w*.58,.5,d*.57,color);for(let x of[-w*.23,w*.23])S(x,.95,0,.22,it.id==="tho_bong"?.6:.23,.19,color);for(let x of[-.12,.12])S(x,.76,d*.28,.055,.055,.04,P.ink);S(0,.64,d*.29,.09,.06,.05,P.pink);break;case"rug":B(0,.023,0,w,.035,d,color),B(0,.048,0,w*.84,.016,d*.76,P.cream);for(let i=0;i<5;i++)B(-w*.33+i*w*.16,.061,0,.025,.012,d*.72,color);break;case"curtain":B(0,0,0,w,.08,.09,P.dark);for(let i=0;i<7;i++)B(-w*.43+i*w*.143,-it.h*.38,Math.sin(i)*.04,w*.15,it.h*.76,.1,i%2?color:P.cream);break;case"mirror":B(0,.5,0,w*.82,1.15,.12,P.gold),B(0,.5,.07,w*.7,1.02,.025,P.blue),B(-w*.12,.64,.09,w*.04,.65,.02,P.cream).rotation.z=-.25,it.spot==="floor"&&legs(.2);break;case"clock":C(0,.2,0,w*.8,.13,w*.8,color).rotation.x=Math.PI/2,C(0,.2,.08,w*.66,.035,w*.66,P.cream).rotation.x=Math.PI/2,B(0,.3,.12,.04,.25,.03,P.ink),B(.09,.2,.12,.2,.04,.03,P.ink);break;case"plant":w>1.3?(B(0,.2,0,w,.38,d,color),plant(-w*.27,0,.7),plant(w*.27,0,.8)):plant(0,0,it.spot==="top"?.55:1);break;case"lamp":{let wall=it.spot==="wall",h=it.id==="den_cay"?1.4:.65;C(0,.04,0,.38,.08,.38,P.dark),C(0,h/2,0,.065,h,.065,P.wood),K(0,h,0,.72,.45,.72,color,!0),S(0,h-.14,0,.24,.2,.24,P.cream,!0),wall&&B(0,h/2,-.18,.08,.07,.4,P.dark);break}case"tub":B(0,.33,0,w,.62,d,color),B(0,.66,0,w*.92,.08,d*.92,P.cream),B(0,.7,0,w*.72,.035,d*.7,P.blue),C(-w*.33,.86,-d*.3,.05,.42,.05,P.gold),B(-w*.27,1.04,-d*.3,.17,.05,.06,P.gold);break;case"shower":B(0,.06,0,w,.1,d,P.cream);for(let x of[-w*.46,w*.46])B(x,1.1,0,.06,2.2,d,P.blue);B(0,2.17,0,w,.06,d,P.gold),C(0,1.1,-d*.43,.05,2.2,.05,P.dark),S(0,2.05,-d*.2,.35,.08,.32,P.gold);break;case"basket":C(0,.27,0,w*.7,.5,d*.8,color),Q(0,.63,0,w*.78,.75,.6,P.dark);for(let i=0;i<3;i++)S(-w*.2+i*w*.2,.5,0,.22,.22,.3,[P.gold,P.mint,P.pink][i]);break;case"vessel":C(0,.25,0,w*.6,.48,d*.6,color),C(0,.5,0,w*.68,.07,d*.68,P.cream),S(0,.56,0,.13,.11,.13,P.dark),Q(w*.3,.27,0,.5,.5,.4,P.dark);break;case"oven":legs(.23),B(0,.58,0,w,.7,d,color),B(0,.53,d*.52,w*.77,.44,.04,P.ink),B(0,.76,d*.55,w*.65,.04,.03,P.gold);for(let x of[-w*.25,w*.25])C(x,.96,0,.3,.03,.3,P.dark);break;case"umbrella":it.id==="ban_ngoai"&&tabletop(),C(0,1.2,0,.055,2.4,.055,P.wood),K(0,2.33,0,w*1.3,.5,w*1.3,color),K(0,2.36,0,w*.9,.48,w*.9,P.cream);break;case"swing":for(let x of[-w*.44,w*.44])B(x,1,0,.1,2,.1,P.dark);B(0,2,0,w,.1,.1,P.wood);for(let x of[-w*.25,w*.25])C(x,1.23,0,.03,1.4,.03,P.dark);B(0,.6,0,w*.7,.2,d*.8,color),B(0,.9,-d*.3,w*.7,.65,.1,color);break;case"hammock":for(let x of[-w*.45,w*.45])B(x,.7,0,.1,1.4,.12,P.wood);S(0,.5,0,w,.15,d*.8,color),B(0,.1,0,w,.1,.15,P.dark);break;case"float":Q(0,.23,0,w,w,d,color).rotation.x=Math.PI/2,it.id==="phao_hong_hac"?(C(w*.32,.55,0,.12,.75,.12,P.pink),S(w*.32,.94,0,.3,.3,.3,P.pink)):S(w*.3,.22,0,.12,.08,.12,P.cream);break;case"water":B(0,.25,0,w,.45,d,P.dark),B(0,.51,0,w*.9,.07,d*.9,P.blue);for(let i=0;i<3;i++)S(-w*.25+i*w*.25,.56,Math.sin(i)*d*.2,.21,.07,.11,P.gold);if(it.id==="be_ca"){for(let x of[-w*.45,w*.45])B(x,.88,0,.05,.7,d,P.blue);B(0,1.24,0,w,.06,d,P.dark)}break;case"birdcage":C(0,.08,0,w*.7,.12,d*.7,P.gold);for(let i=0;i<8;i++){let a=i*Math.PI/4;C(Math.cos(a)*w*.3,.5,Math.sin(a)*d*.3,.025,.85,.025,P.gold)}K(0,1,0,w*.8,.35,d*.8,P.gold),S(0,.45,0,.3,.26,.2,P.mint);break;case"bike":for(let x of[-w*.34,w*.34])Q(x,.35,0,.8,.8,.7,P.ink),C(x,.35,0,.08,.08,.08,P.gold);B(0,.6,0,w*.65,.09,.09,color).rotation.z=.2,B(.1,.9,0,.5,.12,.2,P.dark),B(w*.33,.8,0,.05,.6,.05,P.dark);break;case"tent":B(0,.25,0,w,.5,d,color);let roof=K(0,.85,0,w*1.3,.95,d*1.3,P.wood);roof.rotation.y=Math.PI/4,B(0,.3,d*.51,w*.37,.58,.02,P.dark);break;case"globe":C(0,.07,0,.45,.1,.45,P.wood),C(0,.32,0,.06,.5,.06,P.gold),S(0,.68,0,.65,.65,.65,P.blue),S(.12,.71,.25,.3,.25,.06,P.leaf);break;case"gym":B(0,.15,0,w,.22,d,P.ink),B(0,.28,0,w*.8,.05,d*.72,P.dark);for(let x of[-w*.4,w*.4])B(x,.7,-d*.35,.08,1.4,.08,color);B(0,1.4,-d*.35,w,.09,.1,color);break;case"telescope":for(let i=0;i<3;i++){let a=i*2.1;B(Math.cos(a)*.2,.45,Math.sin(a)*.2,.06,.9,.06,P.dark).rotation.z=Math.cos(a)*.4}C(0,1,0,.25,.9,.25,color).rotation.z=1,C(.35,1.23,0,.3,.08,.3,P.ink).rotation.z=1;break;case"rack":C(0,.9,0,.06,1.8,.06,P.wood),B(0,1.6,0,w,.08,.08,P.dark);for(let i=0;i<3;i++)B(-w*.3+i*w*.3,1.2,0,w*.2,.6,.12,[P.pink,P.mint,P.blue][i]);C(0,.05,0,.6,.1,.6,P.dark);break;case"art":B(0,0,0,w,it.h*.83,.12,color),B(0,0,.07,w*.87,it.h*.7,.02,P.cream),S(-w*.22,it.h*.16,.1,.22,.22,.04,P.gold),K(w*.12,-it.h*.12,.1,w*.62,it.h*.43,.03,P.mint);break;case"bathkit":C(0,.18,0,.38,.36,.38,color),B(.12,.46,0,.09,.35,.09,P.cream),S(-.15,.28,.12,.22,.16,.2,P.gold);break;case"kitchenkit":B(0,.05,0,w*.8,.1,d*.75,P.wood),B(-.12,.14,0,w*.38,.09,.18,P.cream),C(.2,.23,0,.22,.38,.22,color);break;case"festival":C(0,.07,0,w,.1,d,P.gold);for(let i=0;i<5;i++)S(Math.cos(i*1.4)*w*.25,.2,Math.sin(i*1.4)*d*.22,.25,.25,.25,[P.gold,P.pink,P.leaf][i%3]);break;case"cushion":S(0,.15,0,w,.3,d,color),B(0,.25,0,w*.7,.08,d*.7,P.cream);break;case"garden":C(0,.25,0,w*.7,.5,d*.7,color),B(.25,.35,0,.5,.1,.1,P.dark);break;case"toy":B(0,.18,0,w*.55,.36,d*.55,color),B(-.15,.43,0,w*.3,.18,d*.3,P.gold),S(.16,.29,d*.3,.12,.12,.1,P.cream);break}return g}var walls={kem:"#f8edd9",bac_ha:"#c6e2d1",hong_dao:"#f1c8bb",soc:"#e2d6d8",cham_bi:"#e6dbe8",hoa_nhi:"#e6dfcc",may_sao:"#ccdce8",gach_the:"#eee8dc",op_go:"#d9ba95"},floors={go_sang:"#d4ae83",gach_trang:"#eee9de",chieu:"#c7b580",caro:"#d5d1c4",tham_len:"#d89baf",gach_bong:"#b7cbbb",xuong_ca:"#bd9670",ga_ke:"#e2b9c2",ga_may:"#bdd7e3",ga_dau:"#e9b9b8",ga_meo:"#e7d2b6"};function roomStructure(room,parts={},R,scope=""){let g=new Group,solid=sculpt(g,R),{box:B,cyl:C,ball:S}=solid,{width:w,depth:d,height:h}=dimensions(room),skin={...room.skin0,...room.skin},profile=interiorProfile(room,scope),bayWindow=profile.windowDepth&&(room.fix||[]).find(f=>f.t==="window"&&f.layer==="wall"),backGroup=new Group,sideGroup=new Group;g.add(backGroup,sideGroup);let backArt=sculpt(backGroup,R,"back"),sideArt=sculpt(sideGroup,R,"side"),W=backArt.box,L=sideArt.box,outside=room.out,wall=walls[skin.w]||(/bath/.test(room.type)?"#d8e7df":parts?.wall?.lv?"#faefdb":P.cream),floor=floors[skin.f]||(room.type==="yard"?"#9cbd89":outside?"#d3c5ad":parts?.floor?.lv===1?"#e0ddd1":parts?.floor?.lv===2?"#b68b60":"#d1ac87");B(0,-.16,0,w+.3,.3,d+.3,P.dark);let ground=B(0,-.01,0,w,.05,d,floor);ground.name="floor",ground.userData.zone="floor";for(let z=0;z<d*2;z++)B(0,.019,-d/2+z*.5,w,.012,.012,"#b7a18a");for(let x=0;x<w;x++)B(-w/2+x,.019,0,.014,.012,d,"#b7a18a");if(outside){let fence=new Group;fence.name="garden-fence",g.add(fence);let F=sculpt(fence,R).box;for(let x=0;x<=w;x+=.5)F(-w/2+x,.38,-d/2,.09,.78,.09,P.cream);for(let y of[.24,.59])F(0,y,-d/2,w,.07,.08,P.wood);for(let z=0;z<=d;z+=.5)F(-w/2,.38,-d/2+z,.09,.78,.09,P.cream);F(-w/2,.56,0,.09,.08,d,P.wood)}else{let wallPart=(x,y,width,height)=>{if(width<=0||height<=0)return;let m=W(x,y,-d/2-.075,width,height,.16,wall);m.userData.zone="wall",g.getObjectByName("back-wall")||(m.name="back-wall")};if(bayWindow){let f=bayWindow,cx=-w/2+f.x+f.w/2,cy=h-(f.y+f.h/2)*1.1,ow=f.w*.87,oh=f.h*.85,l=cx-ow/2,r=cx+ow/2,b=cy-oh/2,t=cy+oh/2;wallPart((-w/2-.125+l)/2,h/2,l+w/2+.125,h),wallPart((r+w/2+.125)/2,h/2,w/2+.125-r,h),wallPart(cx,b/2,ow,b),wallPart(cx,(t+h)/2,ow,h-t)}else wallPart(0,h/2,w+.25,h);let sideHeight=profile.sideHeight??h,side=L(-w/2-.075,sideHeight/2,0,.16,sideHeight,d,wall);if(side.name="side-wall",sideHeight<h){for(let zz of[-d/2,d/2])L(-w/2-.075,h/2,zz,.16,h,.14,P.cream);L(-w/2-.075,sideHeight,0,.24,.09,d,P.wood)}if(W(0,.13,-d/2+.035,w,.24,.08,P.wood),L(-w/2+.035,.13,0,.08,.24,d,P.wood),W(0,h,-d/2,w+.3,.13,.24,P.dark),L(-w/2,h,0,.23,.13,d,P.dark),room.type==="bunk"){B(0,.13,0,w,.2,d,P.cream);for(let x of[-w/2,w/2])for(let z of[-d/2,d/2])B(x,h/2,z,.12,h,.12,P.wood)}if((room.fix||[]).some(f=>f.t==="slope")&&(B(-w*.29,h-.22,-d*.22,w*.5,.15,d*.65,P.wood).rotation.z=-.24),parts?.wall?.c<65)for(let i=0;i<3;i++)W(-w*.22+i*.16,.8+i*.13,-d/2+.018,.025,.3,.025,"#ab9079").rotation.z=i%2?.5:-.5;if(parts?.wall?.lv===2||skin.w==="op_go"){let trim=W(0,.53,-d/2+.03,w,1,.065,"#cfab83");trim.name="wall-upgrade";for(let x=0;x<w;x+=.45)W(-w/2+x,.53,-d/2+.075,.028,1,.03,"#b58d66")}if(parts?.floor?.c<60){let crack=B(w*.21,.038,d*.15,.026,.012,.9,"#8f775f");crack.rotation.y=.6,crack.name="floor-damage",B(w*.21-.16,.038,d*.15+.25,.45,.012,.026,"#8f775f")}if(parts?.roof?.c<60){let damp2=backArt.ball(w*.25,h-.16,-d/2+.026,1,.25,.025,"#cabda4");damp2.name="roof-damage"}if(parts?.power?.lv===2&&W(0,h-.12,-d/2+.11,w*.9,.06,.08,P.gold,!0),["soc","cham_bi","hoa_nhi","may_sao","gach_the"].includes(skin.w))for(let x=0;x<w;x+=.65)if(skin.w==="soc")W(-w/2+x,h/2,-d/2+.015,.12,h,.012,"#fff3e6");else for(let y=.55;y<h;y+=.6)backArt.ball(-w/2+x,y,-d/2+.022,skin.w==="gach_the"?.55:.07,skin.w==="gach_the"?.015:.07,.012,skin.w==="may_sao"?P.gold:P.cream)}for(let f of room.fix||[]){let painter=f.layer==="wall"?backArt:solid,marked=Object.fromEntries(Object.entries(painter).map(([key,fn])=>[key,(...args)=>{let m=fn(...args);return m.userData.fixture=f.t,m}])),{box:B2,cyl:C2,ball:S2,cone:K,ring:Q}=marked,x=-w/2+f.x+f.w/2,z=-d/2+f.y+f.h/2,fy=h-(f.y+f.h/2)*1.1;if(f===bayWindow){let width=f.w*.87,height=f.h*.85,deep=profile.windowDepth,outer=-d/2-deep;B2(x,fy,outer,width,height,.07,P.blue);for(let xx of[x-width/2,x+width/2])B2(xx,fy,-d/2-deep/2,.085,height+.15,deep+.18,P.cream),B2(xx,fy,outer+.06,.09,height+.15,.12,P.wood);for(let yy of[fy-height/2,fy+height/2])B2(x,yy,-d/2-deep/2,width+.2,.08,deep+.3,P.wood);B2(x,fy,outer+.09,.045,height,.055,P.cream),B2(x,fy,outer+.09,width,.045,.055,P.cream)}else if(f.t==="window"&&f.layer==="wall")B2(x,fy,-d/2+.03,f.w*.87,f.h*.85,.1,P.wood),B2(x,fy,-d/2+.1,f.w*.73,f.h*.7,.06,P.blue),B2(x,fy,-d/2+.16,.05,f.h*.73,.05,P.cream),B2(x,fy,-d/2+.16,f.w*.76,.05,.05,P.cream),B2(x,fy-f.h*.4,-d/2+.23,f.w,.09,.35,P.wood);else if(f.t==="door"&&f.layer==="wall")B2(x,1.05,-d/2+.025,f.w*.83,2.1,.12,P.wood),B2(x,.96,-d/2+.1,f.w*.65,1.6,.04,"#b88256"),S2(x+.25,.95,-d/2+.15,.07,.07,.07,P.gold);else if(f.t==="pool"){B2(x,.025,z,f.w,.07,f.h,P.cream),B2(x,.07,z,f.w-.2,.045,f.h-.2,P.blue);for(let i=0;i<4;i++)B2(x-f.w*.3+i*f.w*.2,.1,z,.4,.012,.045,"#cee9e7")}else if(f.t==="toilet")C2(x,.26,z,.5,.5,.65,P.cream),S2(x,.56,z+.06,.6,.15,.7,P.cream),B2(x,.65,z-.25,.5,.65,.19,P.cream);else if(f.t==="shower")C2(x,1.1,-d/2+.12,.04,1.9,.04,P.gold),S2(x,2,-d/2+.28,.35,.08,.3,P.gold),B2(x,.025,-d/2+.5,.9,.04,.9,P.cream);else if(f.t==="ladder"){for(let xx of[-.27,.27])B2(x+xx,.8,z,.08,1.6,.08,P.wood);for(let i=0;i<5;i++)B2(x,.15+i*.29,z,.62,.08,.08,P.dark)}else if(f.t==="pillow")B2(x,.23,z,f.w*.9,.26,f.h*.75,P.cream);else if(f.t==="bookwall"){B2(x,fy,-d/2+.15,f.w*.93,f.h*1.02,.22,P.dark);for(let row=0;row<4;row++){let yy=fy-f.h*.43+row*f.h*.27;B2(x,yy,-d/2+.32,f.w,.065,.32,P.wood);for(let col=0;col<Math.floor(f.w*5);col++){let xx=x-f.w*.43+col*.2;B2(xx,yy+.17,-d/2+.34,.13,.25+col%3*.04,.19,[P.mint,P.pink,P.gold,P.blue][(col+row)%4])}}for(let xx of[x-f.w*.48,x+f.w*.48])B2(xx,fy,-d/2+.3,.09,f.h*1.12,.37,P.wood)}else if(f.t==="screen"){B2(x,fy,-d/2+.12,f.w,f.h,.2,P.ink),B2(x,fy,-d/2+.24,f.w*.91,f.h*.85,.025,"#b6cacc"),B2(x,fy+f.h*.43,-d/2+.28,f.w*.8,.035,.025,P.cream);for(let side of[-1,1]){B2(x+side*f.w*.48,fy,-d/2+.28,.12,f.h,.14,"#9a5c60");for(let i=0;i<2;i++)C2(x+side*f.w*.56,fy-.23+i*.47,-d/2+.24,.19,.08,.19,P.ink).rotation.x=Math.PI/2}}else if(f.t==="racks"){B2(x,fy,-d/2+.16,f.w,f.h,.27,P.dark);for(let row=0;row<4;row++)for(let col=0;col<Math.floor(f.w*2);col++){let xx=x-f.w*.42+col*.48,yy=fy-f.h*.36+row*f.h*.24;for(let direction of[-1,1])B2(xx,yy,-d/2+.34,.045,.48,.25,P.wood).rotation.z=direction*Math.PI/4;C2(xx,yy,-d/2+.36,.15,.3,.15,col%2?"#61877a":"#895a57").rotation.x=Math.PI/2,C2(xx,yy,-d/2+.54,.055,.1,.055,P.gold).rotation.x=Math.PI/2}}else if(f.t==="mirror"){B2(x,fy,-d/2+.15,f.w,f.h,.14,P.gold),B2(x,fy,-d/2+.24,f.w*.95,f.h*.93,.035,"#c3d5d4");for(let i=0;i<3;i++)B2(x-f.w*.35+i*f.w*.32,fy,-d/2+.27,.025,f.h*.9,.025,P.cream)}else if(f.t==="rails"){for(let xx of[x-f.w*.46,x+f.w*.46])B2(xx,fy,-d/2+.3,.09,f.h,.4,P.wood);B2(x,fy+f.h*.46,-d/2+.3,f.w,.1,.48,P.wood),B2(x,fy+f.h*.2,-d/2+.32,f.w,.055,.055,P.gold);for(let i=0;i<5;i++){let xx=x-f.w*.35+i*f.w*.17;Q(xx,fy+f.h*.14,-d/2+.34,.13,.17,.09,P.gold);for(let s of[-1,1])B2(xx+s*.1,fy-.03,-d/2+.34,.24,.035,.04,P.wood).rotation.z=s*.45}}else if(f.t==="gate"){for(let xx of[x-f.w/2,x+f.w/2])B2(xx,1.07,-d/2+.15,.16,2.15,.18,P.dark);for(let i=0;i<12;i++)B2(x,.12+i*.165,-d/2+.19,f.w,.14,.07,i%2?"#a6b4af":"#bac4b7");B2(x,2.16,-d/2+.23,f.w+.24,.25,.4,P.dark)}else if(f.t==="car"){let fw=f.w*.86,fd=f.h*.72;B2(x,.48,z,fw,.47,fd,"#c88470"),S2(x,.76,z,fw*.57,.66,fd*.84,P.cream),B2(x,.82,z+fd*.43,fw*.46,.32,.035,P.blue),B2(x,.32,z+fd*.5,fw*.93,.09,.08,P.gold);for(let xx of[x-fw*.35,x+fw*.35])for(let zz of[z-fd*.47,z+fd*.47])C2(xx,.25,zz,.36,.16,.36,P.ink).rotation.x=Math.PI/2,C2(xx,.25,zz+(zz>z?.09:-.09),.18,.025,.18,P.gold).rotation.x=Math.PI/2;for(let xx of[x-fw*.36,x+fw*.36])S2(xx,.5,z+fd*.51,.18,.11,.035,P.cream)}else if(f.t==="gazebo"){for(let xx of[x-f.w*.44,x+f.w*.44])for(let zz of[z-f.h*.43,z+f.h*.43])C2(xx,1.03,zz,.12,2.06,.12,P.wood);B2(x,2.06,z,f.w,.15,f.h,P.dark),K(x,2.56,z,f.w*1.25,1,f.h*1.25,P.wood).rotation.y=Math.PI/4,B2(x,.07,z,f.w,.14,f.h,P.cream)}else if(f.surface){let y=f.layer==="wall"?fy:f.surface/32,top=B2(x,y,f.layer==="wall"?-d/2+.3:z,f.w,.14,f.layer==="wall"?.5:f.h,parts?.kitchen?.lv===2?"#dadbd3":P.wood);top.userData.host="#"+f.t,f.layer!=="wall"&&B2(x,y/2,z,f.w*.92,y,f.h*.9,parts?.kitchen?.lv===2?P.mint:P.cream)}}return addInteriorArchitecture(room,scope,{solid,back:backArt,side:sideArt},dimensions(room)),g.userData.architecture=profile.id,g}function mergeGeometries(geometries,useGroups=!1){let isIndexed=geometries[0].index!==null,attributesUsed=new Set(Object.keys(geometries[0].attributes)),morphAttributesUsed=new Set(Object.keys(geometries[0].morphAttributes)),attributes={},morphAttributes={},morphTargetsRelative=geometries[0].morphTargetsRelative,mergedGeometry=new BufferGeometry,offset=0;for(let i=0;i<geometries.length;++i){let geometry=geometries[i],attributesCount=0;if(isIndexed!==(geometry.index!==null))return console.error("THREE.BufferGeometryUtils: .mergeGeometries() failed with geometry at index "+i+". All geometries must have compatible attributes; make sure index attribute exists among all geometries, or in none of them."),null;for(let name in geometry.attributes){if(!attributesUsed.has(name))return console.error("THREE.BufferGeometryUtils: .mergeGeometries() failed with geometry at index "+i+'. All geometries must have compatible attributes; make sure "'+name+'" attribute exists among all geometries, or in none of them.'),null;attributes[name]===void 0&&(attributes[name]=[]),attributes[name].push(geometry.attributes[name]),attributesCount++}if(attributesCount!==attributesUsed.size)return console.error("THREE.BufferGeometryUtils: .mergeGeometries() failed with geometry at index "+i+". Make sure all geometries have the same number of attributes."),null;if(morphTargetsRelative!==geometry.morphTargetsRelative)return console.error("THREE.BufferGeometryUtils: .mergeGeometries() failed with geometry at index "+i+". .morphTargetsRelative must be consistent throughout all geometries."),null;for(let name in geometry.morphAttributes){if(!morphAttributesUsed.has(name))return console.error("THREE.BufferGeometryUtils: .mergeGeometries() failed with geometry at index "+i+".  .morphAttributes must be consistent throughout all geometries."),null;morphAttributes[name]===void 0&&(morphAttributes[name]=[]),morphAttributes[name].push(geometry.morphAttributes[name])}if(useGroups){let count;if(isIndexed)count=geometry.index.count;else if(geometry.attributes.position!==void 0)count=geometry.attributes.position.count;else return console.error("THREE.BufferGeometryUtils: .mergeGeometries() failed with geometry at index "+i+". The geometry must have either an index or a position attribute"),null;mergedGeometry.addGroup(offset,count,i),offset+=count}}if(isIndexed){let indexOffset=0,mergedIndex=[];for(let i=0;i<geometries.length;++i){let index=geometries[i].index;for(let j=0;j<index.count;++j)mergedIndex.push(index.getX(j)+indexOffset);indexOffset+=geometries[i].attributes.position.count}mergedGeometry.setIndex(mergedIndex)}for(let name in attributes){let mergedAttribute=mergeAttributes(attributes[name]);if(!mergedAttribute)return console.error("THREE.BufferGeometryUtils: .mergeGeometries() failed while trying to merge the "+name+" attribute."),null;mergedGeometry.setAttribute(name,mergedAttribute)}for(let name in morphAttributes){let numMorphTargets=morphAttributes[name][0].length;if(numMorphTargets!==0){mergedGeometry.morphAttributes=mergedGeometry.morphAttributes||{},mergedGeometry.morphAttributes[name]=[];for(let i=0;i<numMorphTargets;++i){let morphAttributesToMerge=[];for(let j=0;j<morphAttributes[name].length;++j)morphAttributesToMerge.push(morphAttributes[name][j][i]);let mergedMorphAttribute=mergeAttributes(morphAttributesToMerge);if(!mergedMorphAttribute)return console.error("THREE.BufferGeometryUtils: .mergeGeometries() failed while trying to merge the "+name+" morphAttribute."),null;mergedGeometry.morphAttributes[name].push(mergedMorphAttribute)}}}return mergedGeometry}function mergeAttributes(attributes){let TypedArray,itemSize,normalized,gpuType=-1,arrayLength=0;for(let i=0;i<attributes.length;++i){let attribute=attributes[i];if(TypedArray===void 0&&(TypedArray=attribute.array.constructor),TypedArray!==attribute.array.constructor)return console.error("THREE.BufferGeometryUtils: .mergeAttributes() failed. BufferAttribute.array must be of consistent array types across matching attributes."),null;if(itemSize===void 0&&(itemSize=attribute.itemSize),itemSize!==attribute.itemSize)return console.error("THREE.BufferGeometryUtils: .mergeAttributes() failed. BufferAttribute.itemSize must be consistent across matching attributes."),null;if(normalized===void 0&&(normalized=attribute.normalized),normalized!==attribute.normalized)return console.error("THREE.BufferGeometryUtils: .mergeAttributes() failed. BufferAttribute.normalized must be consistent across matching attributes."),null;if(gpuType===-1&&(gpuType=attribute.gpuType),gpuType!==attribute.gpuType)return console.error("THREE.BufferGeometryUtils: .mergeAttributes() failed. BufferAttribute.gpuType must be consistent across matching attributes."),null;arrayLength+=attribute.count*itemSize}let array=new TypedArray(arrayLength),result=new BufferAttribute(array,itemSize,normalized),offset=0;for(let i=0;i<attributes.length;++i){let attribute=attributes[i];if(attribute.isInterleavedBufferAttribute){let tupleOffset=offset/itemSize;for(let j=0,l=attribute.count;j<l;j++)for(let c=0;c<itemSize;c++){let value=attribute.getComponent(j,c);result.setComponent(j+tupleOffset,c,value)}}else array.set(attribute.array,offset);offset+=attribute.count*itemSize}return gpuType!==void 0&&(result.gpuType=gpuType),result}var DISTRICTS={rent:{name:"X\xF3m tr\u1ECD",wall:"#efd4a1",roof:"#aa644c",floors:1},apartment:{name:"Khu c\u0103n h\u1ED9",wall:"#e1e7d7",roof:"#5c8792",floors:3},townhouse:{name:"Ph\u1ED1 nh\xE0 li\u1EC1n k\u1EC1",wall:"#eeddb8",roof:"#bf7255",floors:2},villa:{name:"V\u01B0\u1EDDn bi\u1EC7t th\u1EF1",wall:"#fff0d5",roof:"#b45f46",floors:2}};function districtStep(at,input,dt){let n=Math.hypot(input.x,input.y),s=Math.max(0,Math.min(.05,Number(dt)||0))*3.2/Math.max(1,n);return{x:Math.max(-2.8,Math.min(2.8,at.x+input.x*s)),y:Math.max(-14,Math.min(14,at.y+input.y*s))}}function districtHomes(group,content,state,rentals){let cat=(content?.journey?.homes?.homes||[]).filter(h=>h.group===group),home=state?.journey?.home||{},own=home.own,rent=home.rent,shared=home.shared,props=[...own?[own]:[],...home.props||[]],lease=home.tenancy||rentals?.tenancy,fallback=lease?["lease",lease]:own?["own",own]:shared?["shared",shared]:rent?["rent",rent]:["attic",null],place=home.place?.where_id?home.place:{where_id:fallback[0],kind:fallback[1]?.kind},current=(where,kind)=>place.where_id===where&&place.kind===kind,homes=[],byKind=new Map(cat.map(h=>[h.id,{...h,kindId:h.id}]));if(rent){let h=byKind.get(rent.kind);h&&homes.push({...h,id:"rent:"+h.id,status:current("rent",h.id)?"current":"rented",label:current("rent",h.id)?"Ph\xF2ng b\u1EA1n \u0111ang \u1EDF":"Ph\xF2ng b\u1EA1n thu\xEA"})}for(let p of props){let h=byKind.get(p.kind);if(!h)continue;let live=p===own&&current("own",p.kind),ad=(rentals?.mine||[]).find(r=>r.property===p.id&&["listing","leased"].includes(r.status)),label=live?"Nh\xE0 b\u1EA1n \u0111ang \u1EDF":p.let||ad?.status==="leased"?"Nh\xE0 c\u1EE7a b\u1EA1n \xB7 \u0111ang cho thu\xEA":ad?.status==="listing"||p.rental_ad?.active?"Nh\xE0 c\u1EE7a b\u1EA1n \xB7 \u0111ang \u0111\u0103ng cho thu\xEA":"Nh\xE0 c\u1EE7a b\u1EA1n";homes.push({...h,id:"own:"+p.id,property:p.id,status:live?"current":"owned",label})}if(shared){let h=byKind.get(shared.kind);h&&homes.push({...h,id:"shared:"+(shared.id||h.id),status:current("shared",h.id)?"current":"shared",label:"Nh\xE0 \u1EDF c\xF9ng"+(shared.name?" \xB7 "+shared.name:"")})}if(lease){let h=byKind.get(lease.kind);h&&homes.push({...h,id:"lease:"+lease.id,status:current("lease",h.id)?"current":"leased",label:current("lease",h.id)?"Nh\xE0 thu\xEA b\u1EA1n \u0111ang \u1EDF":"Nh\xE0 b\u1EA1n thu\xEA"})}place.where_id==="estate"&&place.group===group&&place.kind&&place.name&&homes.push({...place,id:"estate:"+place.kind,status:"current",label:"Dinh th\u1EF1 b\u1EA1n \u0111ang \u1EDF"});for(let p of(rentals?.market||[]).slice(0,100)){let h=byKind.get(p.kind);h&&p.status==="listing"&&homes.push({...h,id:"listing:"+p.id,status:"listing",label:`${p.owner_name} \xB7 cho thu\xEA`,rent:p.rent})}for(let h of cat)homes.push({...h,kindId:h.id,id:"model:"+h.id,status:"model",label:"Nh\xE0 m\u1EABu \xB7 xem th\xF4ng tin"});return homes.sort((a,b)=>+(b.status==="current")-+(a.status==="current"))}function customerPoint(slot,t){let phase=(t*.065+slot/6)%1,y=-13+phase*26;return{x:(slot%2?1:-1)*(1.5+Math.sin(phase*Math.PI*2)*.35),y}}var FORMS={rent:[["corridor",[[0,-1,5.4,2.1,1.75,"gable"],[-2.1,1,1.15,1.35,1.15,"shed"]],["gallery","laundry"]],["l-court",[[0,-1.6,5.2,1.5,1.7,"shed"],[-1.8,.5,1.6,2.7,1.7,"gable"]],["court","laundry"]],["paired",[[-1.8,-.2,1.8,4,1.65,"shed"],[1.8,-.8,1.8,2.8,1.95,"gable"],[.1,-1.8,1.5,1,1.2,"flat"]],["lane","laundry"]],["pavilion",[[.7,-.6,3.4,3.1,1.9,"hip"],[-2,0,1.4,2,1.35,"shed"]],["veranda","laundry"]],["u-court",[[0,-1.7,5.3,1.2,1.6,"gable"],[-2,.1,1.3,2.3,1.75,"shed"],[2,.4,1.3,2.9,1.5,"shed"]],["court","laundry"]],["staggered",[[-1.9,-1.1,1.5,2.4,1.45,"gable"],[0,-.45,1.8,3.4,1.8,"gable"],[1.9,-.95,1.5,2.5,1.65,"gable"]],["veranda","laundry"]],["garden-rooms",[[-1.65,-1.1,2.1,2.1,1.85,"hip"],[1.55,.15,2.2,2.6,1.65,"hip"],[.2,-1.55,1.8,.9,1.25,"flat"]],["pergola","laundry"]],["sawtooth",[[-1.7,-.7,1.65,3.1,1.7,"shed"],[0,-1.25,1.5,2.1,2.05,"shed"],[1.65,-.35,1.65,3.5,1.45,"shed"]],["court","laundry"]]],apartment:[["walkup",[[-.8,-.55,3.3,3.1,5.3,"flat"],[1.75,-1.2,1.7,2.1,3.4,"flat"]],["stairs","gallery"]],["sun-steps",[[-1.7,-.5,1.9,3.3,6.1,"flat"],[.35,-.5,2,3.3,4.65,"flat"],[2,-.15,1.25,2.6,3.1,"flat"]],["terraces"]],["lift-tower",[[-.7,-.9,3.5,2.7,5.8,"flat"],[1.65,-.3,1.6,3.7,6.7,"flat"],[-.6,1.45,3.5,1.25,1.5,"flat"]],["lobby","balconies"]],["skybridge",[[-1.65,-.8,2.2,3.2,5.9,"flat"],[1.65,-.5,2.1,2.8,4.4,"flat"]],["bridge","balconies"]],["family-court",[[0,-1.5,5.4,1.5,3.25,"flat"],[-1.95,.2,1.55,2.5,5.9,"flat"],[1.95,.7,1.55,1.7,4.8,"flat"]],["court","balconies"]],["penthouse",[[0,-.4,5,3.8,4.5,"flat"],[-1.2,-.9,2.5,2.3,2,"butterfly",4.5]],["roofgarden","balconies"]],["corner-ribbon",[[-1.5,-.4,2.3,3.5,6.2,"flat"],[1,-1.3,2.8,1.7,4.6,"flat"],[1.4,1,1.9,1.8,2.2,"round"]],["lobby","terraces"]],["courtyard-tiers",[[0,-1.55,5.2,1.2,6.3,"flat"],[-1.8,.05,1.6,2.2,4.5,"flat"],[1.7,.8,1.8,2.1,2.9,"flat"]],["pergola","terraces"]]],townhouse:[["shop-house",[[-.85,-.35,2.65,3.8,4.8,"gable"],[1.5,-1.35,1.9,1.8,2.8,"flat"]],["shopfront","balconies"]],["garden-l",[[0,-1.5,5.1,1.65,2.75,"hip"],[-1.8,.45,1.65,2.4,3.35,"gable"]],["pergola","court"]],["twin-gables",[[-1.35,-.5,2.25,3.4,3.8,"gable"],[1.2,-.8,2.25,2.7,2.4,"gable"]],["veranda","bay"]],["stepped-courtyard",[[-1.8,-.5,1.8,3.7,4.5,"flat"],[.15,-1.35,2.1,1.9,3,"flat"],[1.9,-1,1.5,2.5,1.65,"flat"]],["terraces","court"]],["patio-house",[[0,-1.7,5.2,1.25,2.6,"gable"],[-1.95,.05,1.3,2.5,2.6,"gable"],[1.9,.45,1.4,1.7,3.9,"flat"]],["court","veranda"]],["round-corner",[[-.85,-.9,3.6,2.6,3.1,"hip"],[1.55,.3,1.85,2.15,4.2,"round"]],["bay","balconies"]],["butterfly",[[.4,-.65,4.5,3.3,3.15,"butterfly"],[-2.25,.55,1,2.15,1.9,"flat"]],["portal","terraces"]],["split-pavilions",[[-1.65,-1,2.1,2.5,3.75,"hip"],[1.35,.05,2.5,3.3,2.75,"gable"]],["bridge","pergola"]]],villa:[["garden-l",[[0,-1.5,5.4,1.7,2.5,"hip"],[-1.85,.35,1.7,2.7,3.7,"hip"]],["pool","pergola"]],["river-terraces",[[-1.55,-.5,2.5,3.4,4.9,"flat"],[1.2,-1.2,2.6,2.1,3.1,"flat"],[1.2,1.1,2.5,1.8,1.55,"flat"]],["pool","terraces"]],["u-colonnade",[[0,-1.65,5.5,1.3,2.6,"hip"],[-2,.15,1.4,2.3,2.6,"hip"],[2,.15,1.4,2.3,2.6,"hip"]],["court","pool"]],["glass-pavilion",[[-.8,-.25,3.55,3.55,2.3,"butterfly"],[1.85,-1.1,1.6,2.1,1.5,"flat"]],["pergola","bay"]],["orangery",[[-1.25,-.65,2.8,3.2,3.55,"gable"],[1.65,.15,1.7,2.4,1.9,"gable"],[.65,-1.75,1.25,.7,1.8,"flat"]],["veranda","court"]],["rotunda",[[-.95,-1.05,3.5,2.15,2.5,"hip"],[1.55,.4,2.1,2.1,3.85,"round"],[-1.85,1.2,1.7,1.4,1.5,"flat"]],["pool","bay"]],["twin-roofs",[[-1.65,-.75,2.1,3,3.2,"hip"],[1.2,-.3,2.8,3.7,2.1,"hip"]],["bridge","pergola"]],["courtyard-manor",[[0,-1.65,5.45,1.2,3.15,"gable"],[-2.05,0,1.35,2.25,2.2,"hip"],[2.05,.3,1.35,2.7,4,"hip"]],["portal","court"]]]},PREFERRED={ky_tuc_xa:0,tro_moi:1,tap_the:0,can_ho_studio:1,can_ho_mini:2,can_ho_1pn:3,can_ho_2pn:4,penthouse:5,nha_pho:0,nha_san:1,biet_thu_vuon:0,biet_thu_song:1},PALETTE={rent:["#efd4a1","#b3664b"],apartment:["#e8dfc8","#638787"],townhouse:["#e9d2ae","#ae624b"],villa:["#f3e7cc","#9e6750"]};function hash(s){let n=0;for(let c of String(s))n=n*31+c.charCodeAt(0)>>>0;return n}function districtArchitecture(group,homes=[]){group=FORMS[group]?group:"rent";let used=new Set;return Array.from({length:8},(_,lot)=>{let home=homes[lot],kind=home?.kindId||home?.kind||"",preferred=PREFERRED[kind],index=Number.isInteger(preferred)?preferred:hash(home?.id||lot)%8;for(;used.has(index);)index=(index+1)%8;used.add(index);let[name,masses,features]=FORMS[group][index];return{id:group+"-"+name,group,index,kind,lot,masses,features,wall:PALETTE[group][0],roof:PALETTE[group][1]}})}function createResidenceKit(material,geometries){let triangle=new Shape;triangle.moveTo(-.5,0),triangle.lineTo(0,1),triangle.lineTo(.5,0),triangle.closePath();let shapes={box:new BoxGeometry(1,1,1),cylinder:new CylinderGeometry(.5,.5,1,16),hip:new ConeGeometry(Math.SQRT1_2,1,4).rotateY(Math.PI/4).translate(0,.5,0),round:new ConeGeometry(.5,1,16).translate(0,.5,0),gable:new ExtrudeGeometry(triangle,{depth:1,bevelEnabled:!1}).translate(0,0,-.5),arch:new TorusGeometry(.5,.07,6,14,Math.PI),leaf:new IcosahedronGeometry(.5,1)};for(let key of Object.keys(shapes)){if(shapes[key].index){let old=shapes[key];shapes[key]=old.toNonIndexed(),old.dispose()}geometries.add(shapes[key])}let C={trim:"#fff0d2",wood:"#846044",dark:"#536a60",glass:"#719da2",brick:"#b28362",leaf:"#7ea36a",water:"#8cc3c6"};function build(plan){let root=new Group;root.name=plan.id,root.userData.architecture=plan;let part=(kind,color,x,y,z,w,h,d,label="detail")=>{let m=new Mesh(shapes[kind],material(color));return m.position.set(x,y,z),m.scale.set(w,h,d),m.userData.structure=label,root.add(m),m},B=(x,y,z,w,h,d,c=C.trim,label)=>part("box",c,x,y,z,w,h,d,label),cyl=(x,y,z,w,h,d,c)=>part("cylinder",c,x,y,z,w,h,d),roof=(x,y,z,w,d,style)=>{if(style==="flat"){B(x,y+.09,z,w+.15,.18,d+.15,C.trim,"roof");for(let s of[-1,1])B(x+s*w/2,y+.27,z,.1,.36,d+.12,C.trim),B(x,y+.27,z+s*d/2,w,.36,.1,C.trim);return}if(style==="shed"){let m=B(x,y+.22,z,w+.25,.13,d+.28,plan.roof,"roof");m.rotation.x=-.14;for(let i=-w/2;i<w/2;i+=.28)B(x+i,y+.3,z,.025,.03,d+.25,C.trim).rotation.x=-.14;return}if(style==="butterfly"){for(let side of[-1,1]){let m=B(x+side*w*.25,y+.25,z,w*.56,.16,d+.25,plan.roof,"roof");m.rotation.z=side*.22}B(x,y+.16,z,.12,.1,d+.28,C.dark);return}let h=style==="gable"?Math.min(.95,w*.28):Math.min(1.2,w*.33);if(part(style==="round"?"round":style==="hip"?"hip":"gable",plan.roof,x,y,z,w+.26,h,d+.24,"roof"),style==="gable"&&B(x,y+h+.025,z,.12,.08,d+.2,C.trim),style!=="round")for(let s of[-1,1])B(x+s*w*.5,y+.02,z,.1,.09,d+.24,C.trim)};function window2(x,y,z,w=.65,h=.85){B(x,y,z,w+.12,h+.12,.12,C.trim),B(x,y,z+.075,w,h,.035,C.glass),B(x,y,z+.1,.045,h,.025,C.trim),B(x,y-h*.5-.06,z+.12,w+.24,.09,.3,C.trim)}function rail(x,y,z,w,d=.65){B(x,y,z,w,.12,d,C.trim);for(let p=-w*.45;p<=w*.46;p+=.32)B(x+p,y+.36,z+d*.46,.045,.65,.045,C.dark);B(x,y+.69,z+d*.46,w,.06,.06,C.dark)}function porch(x,z,w,d,h=1.65,pergola=!1,base=0){B(x,base+.13,z,w,.16,d,C.brick);for(let a of[-1,1])for(let b of[-1,1])cyl(x+a*w*.44,base+h/2,z+b*d*.4,.1,h,.1,C.wood);if(B(x,base+h,z,w+.12,.12,d+.12,C.wood),pergola)for(let q=-w/2;q<=w/2;q+=.28)B(x+q,base+h+.12,z,.07,.1,d+.35,C.trim);else{B(x,base+h+.09,z,w+.22,.13,d+.16,plan.roof);for(let q=-w*.34;q<w*.4;q+=w/3)part("arch",C.trim,x+q,base+h-.25,z+d*.41,w*.27,.65,.55)}}let flower=(x,z)=>{cyl(x,.18,z,.34,.36,.34,C.brick),part("leaf",C.leaf,x,.48,z,.53,.48,.5)};B(0,.02,0,5.9,.1,5.7,plan.group==="villa"?"#a8bd90":"#c5b38e");for(let[index,mass]of plan.masses.entries()){let[x,z,w,d,h,style,base=0]=mass,y=base+.18;part(style==="round"?"cylinder":"box",plan.wall,x,y+h/2,z,w,h,d,"mass"),B(x,y-.04,z,w+.12,.16,d+.12,C.brick);for(let side of[-1,1])B(x+side*(w/2-.055),y+h/2,z+d/2+.03,.11,h,.13,C.trim),B(x,y+.15,z+side*d/2,w,.18,.08,C.brick);let floors2=Math.max(1,Math.floor(h/1.45));for(let f=0;f<floors2;f++){let wy=y+.84+f*(h/floors2);if(!(wy+.52>y+h)){for(let wx=x-w*.3;wx<=x+w*.31;wx+=Math.max(.75,w*.58))window2(wx,wy,z+d/2+.075,Math.min(.68,w*.35),.77);for(let side of[-1,1])B(x+side*(w/2+.025),wy,z,.08,.82,d*.38,C.trim),B(x+side*(w/2+.07),wy,z,.03,.68,d*.29,C.glass);f>0&&(plan.features.includes("balconies")||plan.features.includes("terraces"))&&rail(x,y+f*h/floors2-.08,z+d/2+.32,w*.86,.58)}}if(roof(x,y+h,z,w,d,style),index===0||plan.group==="rent"){let dx=x+(plan.group==="rent"?-.15:0),dz=z+d/2+.12;B(dx,y+.58,dz,.58,1.16,.12,C.wood);for(let j=0;j<4;j++)B(dx,y+.2+j*.22,dz+.075,.43,.035,.025,C.trim);B(dx+.18,y+.64,dz+.09,.06,.07,.04,"#dfbb6a"),B(dx,y+.02,dz+.19,.95,.13,.52,C.trim)}}let has=f=>plan.features.includes(f);if(has("gallery")){porch(0,1.15,5.45,.82,1.65);for(let i=-2.2;i<=2.2;i+=1.1)flower(i,1.75)}if(has("veranda")&&porch(.2,1.65,3.8,.75,1.8),has("pergola")&&porch(.45,1.6,2.25,1.3,1.85,!0),has("court")){for(let i=0;i<5;i++)B(.25,.095,1.2+i*.25,.65,.03,.13,C.trim);flower(-.7,1.7),flower(1.2,1.9)}if(has("lane"))for(let i=0;i<7;i++)B(0,.085,-1.3+i*.52,.7,.04,.3,C.trim);if(has("laundry")){for(let x of[-1,1])cyl(x*.8,1.15,2.38,.045,2.3,.045,C.dark);B(0,2.18,2.38,1.7,.025,.025,C.wood);for(let i=0;i<4;i++)B(-.6+i*.4,1.96,2.38,.28,.42,.035,["#e4ae8c","#e9e4cd","#aac7b9","#ddb7c0"][i]),B(-.6+i*.4,2.15,2.38,.38,.1,.04,C.trim)}if(has("stairs")){for(let i=0;i<10;i++)B(2.14,.15+i*.19,.9-i*.3,.78,.3+i*.38,.28,C.brick);for(let x of[1.72,2.56]){let m=B(x,1.95,-.45,.045,.065,3.1,C.dark);m.rotation.x=.56}}if(has("bridge")){B(0,2.15,-.2,1.5,.18,.95,C.trim);for(let z of[-.62,.22])B(0,2.58,z,1.5,.66,.06,C.glass),B(0,2.94,z,1.56,.06,.08,C.dark)}if(has("roofgarden")){porch(1.35,.45,1.85,1.8,1.5,!0,4.68);for(let i=0;i<3;i++)B(1+i*.5,4.93,.95,.4,.35,.45,C.brick),part("leaf",C.leaf,1+i*.5,5.18,.95,.5,.45,.5)}if(has("lobby")){B(-.7,.8,1.8,1.8,1.4,.05,C.glass),B(-.7,1.7,2.05,2.4,.13,.9,C.trim);for(let x of[-1.75,.4])cyl(x,.85,2.26,.11,1.7,.11,C.dark)}if(has("shopfront")){B(-.85,.86,1.6,2.15,1.35,.05,C.glass),B(-.85,1.75,1.87,2.7,.13,.65,C.wood);for(let i=0;i<6;i++)B(-1.96+i*.43,1.82,1.87,.24,.055,.68,i%2?C.trim:"#b77864")}if(has("portal")){for(let x of[-.9,.9])B(x,1.1,2.25,.24,2.2,.28,C.trim);part("arch",C.trim,0,2.1,2.25,1.8,1.25,1.7)}if(has("pool")){B(.55,.12,1.45,2,.2,1.15,C.trim),B(.55,.23,1.45,1.78,.025,.92,C.water);for(let i=0;i<3;i++)B(-.04+i*.43,.25,1.5,.25,.015,.035,C.trim)}if(has("bay")){B(-1.5,.95,1.65,1.6,1.6,.06,C.glass);for(let x of[-2.31,-.69])B(x,.94,1.78,.09,1.88,.5,C.trim);B(-1.5,1.91,1.78,1.7,.12,.55,C.trim)}return flower(-2.62,2.12),flower(2.6,2.15),root}return{build}}function createDistrictScene(host,options={}){let theme=DISTRICTS[options.group]||DISTRICTS.rent,renderer=new WebGLRenderer({antialias:!0,powerPreference:"low-power"});renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5)),renderer.outputColorSpace=SRGBColorSpace,renderer.setClearColor("#cfdfd4");let canvas=renderer.domElement;canvas.tabIndex=0,canvas.setAttribute("aria-label",theme.name+" 3D. WASD ho\u1EB7c c\u1EA7n tr\xF2n \u0111\u1EC3 \u0111i, k\xE9o \u0111\u1EC3 xoay, ch\u1EA1m nh\xE0 \u0111\u1EC3 xem."),host.append(canvas);let scene=new Scene,camera=new PerspectiveCamera(42,1,.1,120),controls=new OrbitControls(camera,canvas);camera.position.set(19,22,25),controls.target.set(0,0,0),controls.minDistance=9,controls.maxDistance=52,controls.minPolarAngle=.28,controls.maxPolarAngle=1.25,controls.enablePan=!1,controls.enableDamping=!1,controls.update(),scene.add(new HemisphereLight("#fff5de","#799a86",2.6));let sun=new DirectionalLight("#ffe1ab",3);sun.position.set(-12,25,9),scene.add(sun);let geometries=new Set,materials=new Map,textures=new Map,disposers=[],doors=[],houses=[],keys=new Set,disposed=!1,raf=0,last=0,peerMotionUntil=0,suspended=!1,input={x:0,y:0},position={x:0,y:10},direction="se",people=[],goal=null,down=null,material=color=>(materials.has(color)||materials.set(color,new MeshStandardMaterial({color,roughness:1})),materials.get(color));function mesh(geo,color,x,y,z,parent=scene){geometries.add(geo);let m=new Mesh(geo,material(color));return m.position.set(x,y,z),parent.add(m),m}let box=(w,h,d,c,x,y,z,p)=>mesh(new BoxGeometry(w,h,d),c,x,y,z,p);box(21,.2,34,"#97b991",0,-.2,0),box(6.2,.08,32,"#c6b38e",0,-.05,0);for(let side of[-1,1])box(.17,.12,32,"#e9dcc1",side*3.25,0,0),box(1,.04,32,"#e5d7b7",side*3.85,-.01,0);function tree(x,z,i){mesh(new CylinderGeometry(.14,.24,1.55,6),"#8d6845",x,.77,z),mesh(new IcosahedronGeometry(1.08,1),["#77a75b","#55935b","#8eb45c"][i%3],x,1.98,z),mesh(new IcosahedronGeometry(.75,1),"#9bbf6f",x+.4,2.4,z+.1),mesh(new CylinderGeometry(.7,.8,.15,12),"#d3c3a0",x,.03,z)}let homes=(options.homes||[]).slice(0,8),plans=districtArchitecture(options.group,homes),residences=createResidenceKit(material,geometries);for(let i=0;i<8;i++){let side=i%2?1:-1,z=Math.floor(i/2)*8-12,x=side*6.6,home=homes[i],g=residences.build(plans[i]);g.position.set(x,0,z),scene.add(g),side<0?g.rotation.y=Math.PI/2:g.rotation.y=-Math.PI/2,houses.push(g),home&&(g.traverse(o=>{o.isMesh&&(o.userData.home=home)}),doors.push(g)),tree(side*4.35,z+3.5,i)}for(let side of[-1,1])for(let z of[-8,8])box(.75,.12,2,"#9b7651",side*4.05,.55,z),box(.1,.6,2,"#9b7651",side*4.4,.85,z),mesh(new CylinderGeometry(.055,.08,2.8,6),"#4f6860",side*3.5,1.4,z+1.7),mesh(new SphereGeometry(.22,8,6),"#fff0b2",side*3.5,2.87,z+1.7);function batch(parent,cloneMaterials=!1){let buckets=new Map;for(let m of[...parent.children])if(m.isMesh){m.updateMatrix();let geo=m.geometry.clone().applyMatrix4(m.matrix),b=buckets.get(m.material);b||buckets.set(m.material,b={parts:[],home:m.userData.home}),b.parts.push(geo),parent.remove(m)}for(let[mat,b]of buckets){let geometry=mergeGeometries(b.parts,!1);for(let p of b.parts)p.dispose();if(!geometry)continue;geometries.add(geometry);let paint=cloneMaterials?mat.clone():mat;cloneMaterials&&materials.set("house-"+materials.size,paint);let m=new Mesh(geometry,paint);m.userData.home=b.home,parent.add(m)}}for(let house of houses)batch(house,!0);batch(scene);let actors=[];for(let i=0;i<25;i++){let m=new SpriteMaterial({transparent:!0,alphaTest:.07,depthWrite:!1}),s=new Sprite(m);s.center.set(.5,0),s.scale.set(1.6,2.05,1),s.visible=!1,scene.add(s),actors.push(s);let shadow=mesh(new CircleGeometry(.43,12),"#91a18b",0,.025,0);shadow.rotation.x=-Math.PI/2,shadow.visible=!1,s.userData.shadow=shadow}function actor(slot,person,point,moving,t){let sprite=actors[slot];if(!sprite)return;let frame=moving?1+Math.floor(t*7)%2:0,dir=person.direction||"se",id=person.pid||"npc"+slot,key=id+":"+dir+":"+frame+":"+(person.fc||""),tex=textures.get(key);if(!tex){let art=options.avatar?.(person,dir,frame);art&&(tex=new CanvasTexture(art),tex.colorSpace=SRGBColorSpace,textures.set(key,tex))}tex&&(sprite.material.map=tex,sprite.material.needsUpdate=sprite.userData.key!==key,sprite.userData.key=key,sprite.visible=!0),sprite.position.set(point.x,moving?Math.sin(t*12)*.035:0,point.y),sprite.userData.shadow.visible=sprite.visible,sprite.userData.shadow.position.set(point.x,.025,point.y)}let visible=()=>{if(disposed||document.hidden||!host.isConnected)return!1;let dialog=host.closest("dialog"),dialogs=document.querySelectorAll("dialog[open]");return!!dialog?.open&&dialogs[dialogs.length-1]===dialog};function wake(){!raf&&visible()&&(raf=requestAnimationFrame(draw))}function draw(ms){if(raf=0,!visible())return;let t=ms/1e3;if(last&&t-last<1/30){wake();return}let dt=last?Math.min(.05,t-last):0;last=t;let v={x:input.x+(keys.has("d")||keys.has("arrowright")?1:0)-(keys.has("a")||keys.has("arrowleft")?1:0),y:input.y+(keys.has("s")||keys.has("arrowdown")?1:0)-(keys.has("w")||keys.has("arrowup")?1:0)};if(goal&&!v.x&&!v.y){let dx=goal.x-position.x,dy=goal.y-position.y,n=Math.hypot(dx,dy);n<.12?goal=null:v={x:dx/n,y:dy/n}}else(v.x||v.y)&&(goal=null);let next=districtStep(position,v,dt),moving=Math.hypot(next.x-position.x,next.y-position.y)>.001;moving&&(direction=v.y<0?v.x<0?"nw":"ne":v.x<0?"sw":"se"),position=next,options.onMove?.({...position,direction,moving,phase:moving?"walk":"idle"}),actor(0,{...options.player||{pid:"self"},direction},position,moving,t);for(let i=0;i<6;i++){let p=customerPoint(i,options.reduced?0:t);actor(i+1,{pid:"customer"+i,npc:i,direction:i%2?"sw":"ne"},p,!options.reduced,t)}for(let i=7;i<actors.length;i++){let p=people[i-7];if(p){let target=p.activity||{},old=actors[i].position,k=1-Math.exp(-12*dt);actor(i,{...p,direction:target.direction},{x:old.x+(target.x-old.x)*k,y:old.z+(target.y-old.z)*k},target.moving,t)}else actors[i].visible=!1,actors[i].userData.shadow.visible=!1}let eye=new Vector3(position.x,1.1,position.y),delta=eye.clone().sub(camera.position),distance=delta.length();ray.set(camera.position,delta.normalize()),ray.far=distance-.1;let cover=new Set(ray.intersectObjects(houses,!0).map(h=>h.object.parent));ray.far=1/0;for(let house of houses)for(let object of house.children){let target=cover.has(house)?.35:1;object.material.opacity!==target&&(object.material.opacity=target,object.material.transparent=target<1,object.material.depthWrite=target===1,object.material.needsUpdate=!0)}if(renderer.render(scene,camera),(moving||goal||ms<peerMotionUntil||!options.reduced)&&wake(),textures.size>180){let used=new Set(actors.filter(s=>s.visible).map(s=>s.material.map));for(let[key,tex]of textures){if(textures.size<=120)break;used.has(tex)||(tex.dispose(),textures.delete(key))}}}function listen(node,type,fn,opts){node.addEventListener(type,fn,opts),disposers.push(()=>node.removeEventListener(type,fn,opts))}let ray=new Raycaster,plane=new Plane(new Vector3(0,1,0),0),hit=new Vector3;listen(canvas,"pointerdown",e=>{down={x:e.clientX,y:e.clientY},canvas.focus({preventScroll:!0})}),listen(canvas,"pointerup",e=>{if(!down||Math.hypot(e.clientX-down.x,e.clientY-down.y)>6)return;down=null;let r=canvas.getBoundingClientRect();ray.setFromCamera(new Vector2((e.clientX-r.left)/r.width*2-1,1-(e.clientY-r.top)/r.height*2),camera);let house=ray.intersectObjects(doors,!0)[0]?.object.userData.home;if(house){options.onHome?.(house);return}ray.ray.intersectPlane(plane,hit)&&(goal={x:Math.max(-2.8,Math.min(2.8,hit.x)),y:Math.max(-14,Math.min(14,hit.z))},wake())}),listen(canvas,"keydown",e=>{let k=e.key.toLowerCase();["w","a","s","d","arrowup","arrowdown","arrowleft","arrowright"].includes(k)&&(e.preventDefault(),keys.add(k),wake())}),listen(canvas,"keyup",e=>keys.delete(e.key.toLowerCase()));let stop=()=>{keys.clear(),input={x:0,y:0},goal=null,last=0,options.onMove?.({...position,direction,moving:!1,phase:"idle"})},syncVisibility=()=>{visible()?suspended&&(suspended=!1,last=0,wake()):(suspended||stop(),suspended=!0,cancelAnimationFrame(raf),raf=0)};listen(canvas,"blur",stop),listen(window,"blur",stop),listen(document,"visibilitychange",syncVisibility),controls.addEventListener("change",wake);let modalObserver=new MutationObserver(syncVisibility);modalObserver.observe(document.body,{subtree:!0,childList:!0,attributes:!0,attributeFilter:["open"]});let resize=()=>{let w=host.clientWidth||600,h=host.clientHeight||440;renderer.setSize(w,h,!1),camera.aspect=w/h,camera.updateProjectionMatrix(),wake()},observer=new ResizeObserver(resize);return observer.observe(host),resize(),{setPeople(rows){people=(rows||[]).slice(0,18),peerMotionUntil=performance.now()+500,wake()},setInput(x,y){visible()&&(input={x,y},wake())},getPosition:()=>({...position}),dispose(){if(!disposed){disposed=!0,cancelAnimationFrame(raf),observer.disconnect(),modalObserver.disconnect(),controls.dispose();for(let off of disposers)off();for(let a of actors)a.material.dispose();for(let t of textures.values())t.dispose();for(let g of geometries)g.dispose();for(let m of materials.values())m.dispose();renderer.dispose(),renderer.forceContextLoss(),canvas.remove()}}}}function createHomeScene(element,actions={}){let renderer=new WebGLRenderer({antialias:!0,alpha:!1,powerPreference:"low-power"});renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,1.6)),renderer.setClearColor("#eee2cd"),renderer.outputColorSpace=SRGBColorSpace,renderer.shadowMap.enabled=!0,renderer.shadowMap.type=PCFShadowMap,renderer.shadowMap.autoUpdate=!1;let canvas=renderer.domElement;canvas.className="home3d-canvas",canvas.tabIndex=0,canvas.setAttribute("aria-label","Nh\xE0 3D. K\xE9o \u0111\u1EC3 xoay, cu\u1ED9n ho\u1EB7c ch\u1EE5m \u0111\u1EC3 thu ph\xF3ng. Ch\u1EA1m s\xE0n \u0111\u1EC3 \u0111i.");let scene=new Scene,camera=new PerspectiveCamera(38,1,.1,100),R=resources(),world=new Group,actors=new Group;scene.add(world,actors,new HemisphereLight("#fff6e0","#a7ad9b",2.4));let sun=new DirectionalLight("#ffe1ac",3.2);sun.position.set(4,10,7),sun.castShadow=!0,sun.shadow.mapSize.set(1024,1024),sun.shadow.camera.left=-12,sun.shadow.camera.right=12,sun.shadow.camera.top=12,sun.shadow.camera.bottom=-12,sun.shadow.normalBias=.05,scene.add(sun);let fill=new DirectionalLight("#cadfeb",.6);fill.position.set(-5,5,-3),scene.add(fill);let controls=new OrbitControls(camera,canvas);controls.enableDamping=!1,controls.enablePan=!1,controls.minPolarAngle=.3,controls.maxPolarAngle=Math.PI*.47,controls.minDistance=3,controls.maxDistance=30;let ray=new Raycaster,pointer=new Vector2,plane=new Plane,hitPoint=new Vector3,normal=new Vector3,objects=new Map,actorSlots=[],wallMaterials={back:new Set,side:new Set},selection=new BoxHelper(new Object3D,"#e7ae4c");selection.visible=!1,scene.add(selection);let container=element,data=null,key="",roomKey="",closed=!1,raf=0,press=null,drag=null,visible=!0;for(let i=0;i<28;i++){let material=new SpriteMaterial({transparent:!0,alphaTest:.06,depthWrite:!1}),sprite=new Sprite(material);sprite.center.set(.5,0),sprite.visible=!1,actors.add(sprite);let nameMaterial=new SpriteMaterial({transparent:!0,depthWrite:!1}),label=new Sprite(nameMaterial);label.visible=!1,actors.add(label),actorSlots.push({sprite,label,id:"",art:"",name:"",version:0,x:0,z:0,toX:0,toZ:0,fromX:0,fromZ:0,start:0,height:1.7})}let usable=()=>!closed&&visible&&container?.isConnected&&document.visibilityState!=="hidden"&&(()=>{let dialogs=document.querySelectorAll("dialog[open]");return!dialogs.length||dialogs[dialogs.length-1]===container.closest("dialog")})();function invalidate(){!raf&&usable()&&(raf=requestAnimationFrame(draw))}function draw(now){if(raf=0,!usable())return;let moving=!1;if(data){let{width:w,depth:d}=dimensions(data.room);fadeWall("back",camera.position.z<-d/2),fadeWall("side",camera.position.x<-w/2)}for(let a of actorSlots){if(!a.sprite.visible)continue;let t=Math.min(1,(now-a.start)/155);a.x=a.fromX+(a.toX-a.fromX)*t,a.z=a.fromZ+(a.toZ-a.fromZ)*t,a.sprite.position.set(a.x,.025,a.z),a.label.position.set(a.x,a.height+.14,a.z),t<1&&Math.abs(a.toX-a.fromX)+Math.abs(a.toZ-a.fromZ)>.003&&(moving=!0)}renderer.render(scene,camera),moving&&invalidate()}function fadeWall(side,covered){for(let material of wallMaterials[side]){let opacity=covered?.35:1;material.opacity!==opacity&&(material.opacity=opacity,material.transparent=covered,material.depthWrite=!covered,material.needsUpdate=!0)}}function resize(){if(closed||!container)return;let w=container.clientWidth||500,h=container.clientHeight||380;renderer.setSize(w,h,!1),camera.aspect=w/h,camera.updateProjectionMatrix(),invalidate()}function resetCamera(){if(!data)return;let{width:w,depth:d}=dimensions(data.room),dist=Math.max(w,d)*1.7;camera.position.set(dist*.55,dist*.72,dist*.88),controls.target.set(0,.35,0),controls.maxDistance=Math.max(15,dist*2),controls.update(),invalidate()}function attach(el){container=el,canvas.parentNode!==el&&el.append(canvas),observer.disconnect(),observer.observe(el),resize()}function findItem(object){for(let o=object;o;o=o.parent)if(o.userData.uid)return objects.get(o.userData.uid);return null}function cast(event,withActors=!1){let r=canvas.getBoundingClientRect();return pointer.set((event.clientX-r.left)/r.width*2-1,1-(event.clientY-r.top)/r.height*2),ray.setFromCamera(pointer,camera),ray.intersectObjects(withActors?[world,actors]:world.children,!0).filter(h=>!h.object.userData.architectureOnly&&(!h.object.userData.wall||h.object.material.opacity===1))}function pointFor(event,it,allowHost=!0){let hits=cast(event),host=null;if(it?.spot==="top"&&allowHost)for(let hit of hits){let o=findItem(hit.object);if(o&&!o.mate&&o.id!==data.held?.uid&&(o.it.surface||o.it.ledge)){host=o,hitPoint.copy(hit.point);break}if(hit.object.userData.host&&(host=hostOf(data.room,hit.object.userData.host,data.items),host)){hitPoint.copy(hit.point);break}}if(!host){let{depth:d}=dimensions(data.room);if(normal.set(0,it?.spot==="wall"?0:1,it?.spot==="wall"?1:0),plane.set(normal,it?.spot==="wall"?d/2-.1:0),!ray.ray.intersectPlane(plane,hitPoint))return null}return{point:{x:hitPoint.x,y:hitPoint.y,z:hitPoint.z},q:it?hitPlacement(data.room,it,hitPoint,{host,all:data.items,f:data.held?.f||0}):null}}function down(e){if(e.isPrimary===!1){cancel();return}if(!(e.button!==0||!data||data.busy)&&(canvas.focus({preventScroll:!0}),press={x:e.clientX,y:e.clientY,id:e.pointerId},actions.interacting?.(!0),data.edit&&!data.held&&(!data.remote||data.coop))){let hits=cast(e),o=hits.length?findItem(hits[0].object):null;o&&!o.mate&&!o.pinned&&(drag={item:o,moved:!1},e.pointerType!=="touch"&&(controls.enabled=!1),canvas.setPointerCapture?.(e.pointerId))}}function move(e){if(!drag||!press||press.id!==e.pointerId||Math.hypot(e.clientX-press.x,e.clientY-press.y)<9&&!drag.moved)return;let p=pointFor(e,drag.item.it);if(!p)return;drag.moved=!0,controls.enabled=!1,drag.q={...p.q,f:drag.item.q.f||0,...drag.item.q.face?{face:drag.item.q.face}:{}};let mesh=objects.get(drag.item.id)?.mesh;if(mesh){let at=placement(data.room,{...drag.item,q:drag.q},data.items);mesh.position.set(at.x,at.y,at.z),selection.setFromObject(mesh),selection.visible=!0,invalidate()}}function up(e){if(!press||press.id!==e.pointerId)return;let was=drag,tap=Math.hypot(e.clientX-press.x,e.clientY-press.y)<9;if(press=null,drag=null,controls.enabled=!0,actions.interacting?.(!1),was?.moved){actions.move?.(was.item.id,was.q);return}if(!tap||data.busy)return;if(data.edit&&data.held){let it=data.held.it,p2=pointFor(e,it);p2&&editIntent(data,null,p2.point)?.type==="place"&&actions.place?.(p2.q);return}let hits=cast(e,!data.edit).filter(h=>h.object.visible),o=hits.length?findItem(hits[0].object):null,actorUid=hits[0]?.object.userData.actorUid||"";if(data.edit){let intent=editIntent(data,o,null);intent?.type==="select"&&actions.select?.(intent.uid);return}let p=pointFor(e,null);if(p){let{width:w,depth:d}=dimensions(data.room);actions.walk?.([clamp2((p.point.x+w/2)/w,0,1),clamp2((p.point.z+d/2)/d,0,1)],o?.id||actorUid)}}function cancel(){drag&&(key="",update(data)),press=null,drag=null,controls.enabled=!0,actions.interacting?.(!1)}function keydown(e){["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","Delete","Backspace","f","F","r","R","PageUp","PageDown"].includes(e.key)&&actions.key?.(e)}function onVisibility(){!usable()&&raf?(cancelAnimationFrame(raf),raf=0):(syncActors(),invalidate())}function contextLost(e){e.preventDefault(),actions.fallback?.("Thi\u1EBFt b\u1ECB v\u1EEBa m\u1EA5t k\u1EBFt n\u1ED1i \u0111\u1ED3 h\u1ECDa. \u0110\xE3 m\u1EDF l\u1EA1i ph\xF2ng minh h\u1ECDa.")}function svgTexture(a,actor){let version=++a.version,img=new Image,svg=`<svg xmlns="http://www.w3.org/2000/svg" width="192" height="256" viewBox="${actor.viewBox||"-55 -165 110 170"}">${actor.art}</svg>`;img.onload=()=>{if(closed||a.version!==version)return;let texture=new Texture(img);texture.colorSpace=SRGBColorSpace,texture.needsUpdate=!0,a.sprite.material.map?.dispose(),a.sprite.material.map=texture,a.sprite.material.needsUpdate=!0,invalidate()},img.src="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg)}function nameTexture(a,name){if(a.label.material.map?.dispose(),a.label.material.map=null,a.label.visible=!!name,!name)return;let c=document.createElement("canvas");c.width=256,c.height=48;let ctx=c.getContext("2d");ctx.fillStyle="rgba(255,248,230,.92)",ctx.beginPath(),ctx.roundRect(0,3,256,42,18),ctx.fill(),ctx.fillStyle="#604c40",ctx.textAlign="center",ctx.font="600 22px sans-serif",ctx.fillText(name.slice(0,22),128,31,236);let texture=new CanvasTexture(c);texture.colorSpace=SRGBColorSpace,a.label.material.map=texture,a.label.material.needsUpdate=!0,a.label.scale.set(1.5,.28,1)}function syncActors(){if(!data||!usable())return;let source=actions.actors?.()||{},list=boundedActors(source.people,source.children,source.pets),{width:w,depth:d}=dimensions(data.room),now=performance.now(),changed=!1;for(let a of actorSlots)a.id&&!list.some(x=>x.id===a.id)&&(a.id="",a.sprite.visible=!1,a.label.visible=!1,a.version++,a.art="",a.name="",a.sprite.material.map?.dispose(),a.sprite.material.map=null,a.label.material.map?.dispose(),a.label.material.map=null,changed=!0);for(let actor of list){let a=actorSlots.find(s=>s.id===actor.id),fresh=!a;if(a||(a=actorSlots.find(s=>!s.id)),!a)break;a.id=actor.id,a.sprite.visible=!0,a.sprite.userData.actorUid=actor.id.startsWith("baby:")?actor.id:"",a.height=actor.height||1.7;let x=(actor.at?.[0]??.5)*w-w/2,z=(actor.at?.[1]??.8)*d-d/2;fresh&&(a.x=x,a.z=z),(fresh||Math.abs(a.toX-x)+Math.abs(a.toZ-z)>.003)&&(a.fromX=a.x,a.fromZ=a.z,a.toX=x,a.toZ=z,a.start=actions.calm?.()?now-200:now,changed=!0),a.art!==actor.art&&(a.art=actor.art,svgTexture(a,actor),changed=!0);let name=actor.name||"";a.name!==name&&(a.name=name,nameTexture(a,name),changed=!0),a.label.visible=!!name,a.sprite.scale.set(actor.width||a.height*.7,a.height,1),a.sprite.position.set(a.x,.025,a.z),a.label.position.set(a.x,a.height+.14,a.z)}changed&&invalidate()}function update(next){if(closed||!next)return;data=next;let signature=JSON.stringify([data.scope,data.room,data.parts,data.items.map(o=>[o.id,o.k,o.it,o.q,o.color,o.mate])]);if(signature!==key){key=signature,world.clear(),objects.clear(),world.add(roomStructure(data.room,data.parts,R,data.scope));for(let o of data.items){let mesh=furniture(o.it,o.color,R),at=placement(data.room,o,data.items);mesh.position.set(at.x,at.y,at.z),mesh.scale.x=o.q.f?-1:1,mesh.rotation.y=o.q.face==="back"?Math.PI:0,mesh.userData.uid=o.id,objects.set(o.id,{...o,mesh}),world.add(mesh)}wallMaterials.back.clear(),wallMaterials.side.clear(),world.traverse(o=>{o.userData.wall&&wallMaterials[o.userData.wall].add(o.material)}),R.prune(world),renderer.shadowMap.needsUpdate=!0}else for(let o of data.items){let old=objects.get(o.id);if(old){old.pinned=o.pinned;let at=placement(data.room,o,data.items);old.mesh.position.set(at.x,at.y,at.z)}}let identity=data.scope+":"+data.room.id;if(identity!==roomKey){roomKey=identity,resetCamera();for(let a of actorSlots)a.id="",a.sprite.visible=!1,a.label.visible=!1}let selected=objects.get(data.selected);selection.visible=!!selected,selected&&selection.setFromObject(selected.mesh),canvas.setAttribute("aria-label",`${data.room.name||"Ph\xF2ng"} 3D. ${data.edit?"Ch\u1EA1m \u0111\u1ED3 \u0111\u1EC3 ch\u1ECDn, k\xE9o \u0111\u1ED3 \u0111\u1EC3 d\u1EDDi.":"Ch\u1EA1m s\xE0n \u0111\u1EC3 \u0111i, ch\u1EA1m \u0111\u1ED3 \u0111\u1EC3 d\xF9ng."} K\xE9o ch\u1ED7 tr\u1ED1ng \u0111\u1EC3 xoay; cu\u1ED9n ho\u1EB7c ch\u1EE5m \u0111\u1EC3 thu ph\xF3ng.`),syncActors(),invalidate()}function cameraAction(action){action==="reset"?resetCamera():(action==="in"||action==="out")&&(camera.position.sub(controls.target).multiplyScalar(action==="in"?.85:1.18).add(controls.target),controls.update(),invalidate())}let observer=new ResizeObserver(resize),intersection=globalThis.IntersectionObserver?new IntersectionObserver(entries=>{visible=entries[0]?.isIntersecting!==!1,onVisibility()}):null;controls.addEventListener("change",invalidate),canvas.addEventListener("pointerdown",down),canvas.addEventListener("pointermove",move),canvas.addEventListener("pointerup",up),canvas.addEventListener("pointercancel",cancel),canvas.addEventListener("keydown",keydown),canvas.addEventListener("webglcontextlost",contextLost),document.addEventListener("visibilitychange",onVisibility),attach(element),intersection?.observe(element);let timer=setInterval(syncActors,155),wasUsable=usable(),modalObserver=new MutationObserver(()=>{let next=usable();next!==wasUsable&&(wasUsable=next,onVisibility())});modalObserver.observe(document.body,{subtree:!0,childList:!0,attributes:!0,attributeFilter:["open"]});function dispose(){if(!closed){closed=!0,clearInterval(timer),raf&&cancelAnimationFrame(raf),observer.disconnect(),intersection?.disconnect(),modalObserver.disconnect(),document.removeEventListener("visibilitychange",onVisibility);for(let[type,fn]of[["pointerdown",down],["pointermove",move],["pointerup",up],["pointercancel",cancel],["keydown",keydown],["webglcontextlost",contextLost]])canvas.removeEventListener(type,fn);controls.dispose();for(let a of actorSlots){a.version++;for(let sprite of[a.sprite,a.label])sprite.material.map?.dispose(),sprite.material.dispose()}selection.geometry.dispose(),selection.material.dispose(),R.dispose(),world.clear(),actors.clear(),scene.clear(),sun.shadow.map?.dispose(),renderer.renderLists.dispose(),renderer.dispose(),renderer.forceContextLoss(),canvas.remove(),objects.clear()}}return{attach,detach:()=>canvas.remove(),update,cameraAction,dispose,stats:()=>({objects:objects.size,actors:actorSlots.filter(a=>a.sprite.visible).length,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,closed})}}export{createDistrictScene,createHomeScene,districtHomes};
