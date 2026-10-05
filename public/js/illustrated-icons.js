/** Original small-town illustrations. Shared by the map HUD, sheets and careers.
 * Material colors stay legible on light paper and dark surfaces; --town-icon-*
 * properties can tune them without replacing the artwork. No bitmap/font assets.
 */
const color=(name,value)=>`var(--town-icon-${name}, ${value})`;
const ink=color('outline','#68574d'),paper=color('paper','#fff3d8'),cream=color('cream','#ecd7ad');
const clay=color('clay','#d98d72'),clayShade=color('clay-shade','#b86b59'),rose=color('rose','#e3a0a1');
const leaf=color('leaf','#91b28a'),leafShade=color('leaf-shade','#668d74'),mint=color('mint','#c1d9b3');
const blue=color('blue','#8dbcc9'),blueShade=color('blue-shade','#5f8eac'),water=color('water','#c4e0df');
const gold=color('gold','#edbf6a'),goldShade=color('gold-shade','#cf994f'),wood=color('wood','#b98e69');
const lilac=color('lilac','#b7a8cf'),skin=color('skin','#efc6a3'),hair=color('hair','#735b50');
const p=(d,fill='none',extra='')=>`<path d="${d}" fill="${fill}" ${extra}/>`;
const r=(x,y,w,h,fill,rx=1.5,extra='')=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" ${extra}/>`;
const c=(x,y,rad,fill,extra='')=>`<circle cx="${x}" cy="${y}" r="${rad}" fill="${fill}" ${extra}/>`;
const e=(x,y,rx,ry,fill,extra='')=>`<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${fill}" ${extra}/>`;
const wash=(d,fill)=>p(d,fill,'stroke="none"');
const line=(d,stroke=ink,width=1.1)=>p(d,'none',`stroke="${stroke}" stroke-width="${width}"`);
const dot=(x,y,rad,fill=ink)=>c(x,y,rad,fill,'stroke="none"');
const wheel=(x,y,rad=2.7)=>c(x,y,rad,ink)+c(x,y,rad*.47,cream,'stroke="none"');
const shine=d=>line(d,paper,1.15);
const face=(x,y)=>dot(x-1.7,y,.55)+dot(x+1.7,y,.55)+line(`M${x-1} ${y+2}q1 1 2 0`,ink,.8);

const marks={
  home:r(4.5,10,15,11,cream,1)+wash('M15 10h4.5v11H15Z',gold)+p('M2.5 10 11 3.5q1-1 2 0l8.5 6.5-2 1L12 5.5 4.5 11Z',clay)+line('m7 8 2 1m1-3 2 1m1-3 2 1m0 3 2 1',clayShade,.9)+r(9.5,13.5,5,7.5,wood,.9)+r(5.8,12.5,2.6,3.5,blue,.6)+line('M7.1 13v2.5',paper,.8)+dot(13.2,17.5,.45,paper)+p('M17 18v-4m0 2q-3 0-2-2 2 0 2 2m0-1q0-3 2-3 1 2-2 3',leaf)+p('M15.5 18h3l-.5 3H16Z',clay),
  store:r(4,10,16,11,cream,1)+wash('M16 10h4v11h-4Z',gold)+r(6,13,6,4.5,water,.7)+line('M9 13v4.5',wood,.8)+r(14,13,4,8,wood,.7)+p('M3 8.5 5 4h14l2 4.5Z',clay)+wash('M7 4h3L9 8.5H5.5Zm7 0h3l1.5 4.5H15Z',paper)+p('M3 8.5h18v1q-1.5 3-3 0-1.5 3-3 0-1.5 3-3 0-1.5 3-3 0-1.5 3-3 0-1.5 3-3 0Z',clay)+dot(16.8,17.5,.45,paper)+line('M3 21h18',wood),
  building:p('M4 20V4l11-2v18Z',cream)+p('m15 2 5 3v15h-5Z',gold)+p('m4 4 11-2 5 3-11 2Z',paper)+r(8,15,4,5,wood,.5)+r(6.5,8,2,2.4,blue,.3)+r(11,7.3,2,2.4,blue,.3)+r(6.5,11.5,2,2.2,blue,.3)+r(11,11,2,2.2,blue,.3)+line('M17 8h1m-1 4h1M3 21h18'),
  briefcase:p('M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2',wood)+r(2.5,7,19,14,wood,2.5)+wash('M17 8h3.5v11q0 1-1 1H17Z',goldShade)+p('M2.5 8q0-1 2-1h15q2 0 2 1v5q-9.5 4-19 0Z',gold)+line('M6.5 7v13M17.5 7v13',goldShade,.8)+r(10,12,4,4,paper,.8)+shine('M5 9h7'),
  map:p('m2.5 5 6-2 7 2 6-2v16l-6 2-7-2-6 2Z',cream)+wash('m8.5 3 7 2v16l-7-2Z',mint)+wash('m3 14 5.5-3 7 4 5.5-5v4l-5.5 4-7-4L3 17Z',water)+line('M8.5 3v16M15.5 5v16',wood,.8)+p('M16 9a3 3 0 0 1 6 0c0 2-3 5-3 5s-3-3-3-5Z',clay)+dot(19,9,1,paper)+line('m5 8 1 1 1-1m4 7 1 1 1-1',leafShade,.8),
  compass:c(12,12.5,9.3,gold)+c(12,12.5,7.3,paper)+p('m16 8-2.5 6.5L8 17l2.5-6.5Z',blue)+p('m16 8-2.5 6.5-3-4Z',clay)+dot(12,12.5,.9,paper)+line('M12 5.7v1.1m0 11.4v1.1M5.5 12.5h1m11 0h1',wood,.8)+line('M10 3V1.8h4V3',goldShade),
  truck:r(2,6,12,12,leaf,1.6)+wash('M2.5 14H14v3.5H2.5Z',leafShade)+p('M14 9h4q1 0 1.5 1l2 3v5H14Z',gold)+p('M16 10.5h2l2 3H16Z',water)+line('M3.5 9h7m-7 2.5H9',mint,.9)+wheel(6.5,18)+wheel(18,18)+r(20.5,15,1.5,1.5,paper,.3)+line('M16 15.5h1',wood),
  bike:wheel(5.5,17,3.5)+wheel(18.5,17,3.5)+line('m5.5 17 4-8 5 8h-9l7-5.5H16l2.5 5.5',clay,1.7)+r(4,5,6,4,gold,.8)+line('M8 9h3m4 2.5-1-5h3m-3 0h3',ink,1.3)+dot(14.5,17,1,clay)+shine('M5.5 6.5h2'),
  tractor:p('M4 15V8h7l3 6h7v5H4Z',leaf)+r(5,6,7,8,leaf,.6)+r(6.5,7.5,4,4.5,water,.4)+line('M4 5.5h9M17 14V8h2',leafShade,1.5)+p('M14 14h6.5l1 2H14Z',gold)+wheel(7,17,4.5)+wheel(19,18.5,2.5)+line('M16 16h2',leafShade,.8),
  bowl:p('M3 11c0 6 4 9 9 9s9-3 9-9Z',blue)+wash('M12 19c4-1 6-3 7-7h2c-.5 5-4 8-9 8Z',blueShade)+e(12,11,9,3.1,paper)+e(12,11,7,1.8,gold,'stroke="none"')+line('M7 11q2-2 4 0t4 0',paper,1.2)+line('m14 9 3 2m-2 .5 2-.5',leafShade,1.3)+line('m15 6 6-3m-6 5 7-3',wood,1.2)+line('M8 7q-2-2 0-4M11 6q-2-2 0-4',clay,.9)+p('M8 20h8v1H8Z',blueShade),
  coffee:p('M17 9h2a3.5 3.5 0 0 1 0 7h-2',gold)+e(11,20.5,9,1.5,cream)+p('M4 8h13v8a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4Z',clay)+wash('M13 9h4v7q0 4-4 4h-2q3-2 2-11Z',clayShade)+e(10.5,8,6.5,2,paper)+e(10.5,8,4.8,1.15,wood,'stroke="none"')+shine('M6.5 11v4')+line('M8 5q-1-1 0-3m4 3q-1-1 0-3',wood,.9),
  cake:r(4,11,16,9,rose,1.5)+wash('M16 12h3.5v7H16Z',clay)+p('M4 11q1-3 8-3t8 3v3q-2 2-4-1-2 3-4 0-2 3-4 0-2 3-4 0Z',paper)+line('M4 17h16',paper,1.3)+r(11,5,2,4,blue,.4)+p('M12 4q-2-1 0-3 2 2 0 3Z',gold)+e(12,21,10,1,cream)+c(7,10.8,.9,clay)+c(17,10.8,.9,clay),
  basket:line('M6 11V8a6 6 0 0 1 12 0v3',wood,2)+c(8,11,3,clay)+c(13,10,3.2,gold)+c(17,12,2.8,leaf)+p('M3 12h18l-2 8q-7 3-14 0Z',gold)+wash('m17 13 3-.5-2 7-3 .5Z',goldShade)+line('M5 15h14M5.5 18h13M8 13l.5 7M12 13v8M16 13l-.5 7',wood,.75)+p('M11 7q-3-3-4-1 1 3 4 1Z',leaf),
  flower:line('M12 21V9m0 8-5-4m5 3 5-4',leafShade,1.4)+p('M11 17q-6 1-7-4 5-1 7 4M13 16q5 1 7-4-5-1-7 4',leaf)+c(12,4.5,2.7,rose)+c(8.5,7,2.7,rose)+c(10,10.5,2.7,clay)+c(15,10.5,2.7,clay)+c(16,6.8,2.7,rose)+c(12.2,7.5,2.7,gold)+dot(11.5,6.8,.65,paper),
  plant:p('M5.5 14h13l-2 7h-9Z',clay)+wash('M14.5 14h4l-2 7h-3Z',clayShade)+r(5,13,14,3,gold,1)+line('M12 13V6',leafShade,1.5)+p('M12 10Q3 11 3 4q8-1 9 6Z',leaf)+p('M12 8q0-7 9-6 0 7-9 6Z',mint)+line('m6 6 6 5m0-3 5-3',leafShade,.8)+shine('m8 17 .5 2'),
  leaf:p('M20.5 3C8 1.5 3 7 5.2 14.5c1.5 5.5 8 6 11.5 1.8C19.5 13 20 8 20.5 3Z',leaf)+wash('M20.5 3Q19 15 9 17l3-6Z',leafShade)+line('M3.5 21 16 8',wood,1.2)+line('m9 15-1-5m1 5 5 .4m-1-4 .2-4',mint,.9),
  paw:p('M8 13q4-4 8 0l3 4q2 5-4 4l-3-1-3 1q-6 1-4-4Z',clay)+wash('M16 14q6 6-1 7l-3-1q6 0 4-6Z',clayShade)+e(4.5,10,2,2.8,gold)+e(8.6,5.8,2,3,gold)+e(15.2,5.8,2,3,gold)+e(19.5,10,2,2.8,gold)+shine('M8 16q1-2 2-2'),
  fish:p('M16 12q2-4 5-4l-1 4 1 4q-3 0-5-4Z',clay)+p('M3 12q6-9 14 0-8 9-14 0Z',blue)+wash('M4 13q6 5 12-1l1 0q-7 8-13 1Z',blueShade)+p('m10 7 3-2 1 3m-4 9 3 2 1-3',gold)+line('M8 8q3 4 0 8',blueShade,.9)+dot(6,11,.8)+dot(5.8,10.7,.2,paper)+line('m12 11 2 1-2 1',paper,.9)+c(3,5.5,1,water)+c(5,2.5,.7,water),
  bear:c(6.5,5.5,3.3,wood)+c(17.5,5.5,3.3,wood)+c(6.5,5.5,1.5,rose,'stroke="none"')+c(17.5,5.5,1.5,rose,'stroke="none"')+e(12,17,6,5,wood)+e(12,10.5,8,7,gold)+e(12,13,3.6,2.4,paper)+dot(9,10,.7)+dot(15,10,.7)+e(12,12,1.1,.8,ink,'stroke="none"')+line('M12 12v2m-1 0q1 1 2 0',ink,.8)+p('m12 18-3-2v4l3-1 3 1v-4Z',leaf)+e(6.5,20,2.5,2,gold)+e(17.5,20,2.5,2,gold),
  bed:r(3,9,18,10,wood,1.2)+r(4,10,16,7,cream,1)+r(5,10,6,4,paper,1.5)+p('M12 10h7q2 0 2 2v5H11V11Z',blue)+wash('M17 10h2q2 0 2 2v5h-4Z',blueShade)+line('M3 6v15m18-8v8',wood,2)+line('M3 18h18',gold,1.5),
  cart:line('M2 3h3l3 14h12',wood,1.5)+p('m6 7 15-1-2.5 8.5H8Z',mint)+wash('m16 6.5 5-.5-2.5 8.5h-4Z',leaf)+line('m10 7 1 6m4-6-.5 6M8 10h12',leafShade,.8)+c(10,20,1.7,wood)+c(18,20,1.7,wood)+p('M10 7V4h4v3',paper)+p('m15 6 1-4 3 .5-.5 4',clay),
  calculator:r(4.5,2.5,15,19,blue,2)+wash('M16 3h2q1 0 1 2v15q0 1-1 1h-2Z',blueShade)+r(7,5,10,4,paper,.7)+r(7,12,2.2,2.2,cream,.4)+r(11,12,2.2,2.2,cream,.4)+r(15,12,2.2,5.8,gold,.5)+r(7,16,2.2,2.2,cream,.4)+r(11,16,2.2,2.2,cream,.4)+line('M12 7h3',leafShade,.9),
  book:p('M3 4q5-2 9 1 4-3 9-1v16q-5-2-9 1-4-3-9-1Z',wood)+p('M4 3q5-1 8 2 3-3 8-2v15q-5-1-8 2-3-3-8-2Z',paper)+wash('M12 5q4-3 8-2v15q-5-1-8 2Z',cream)+line('M12 5v15M6 7h3m-3 3h3m-3 3h3m6-6h3m-3 3h3',wood,.8)+p('M16 3h2v7l-1-1-1 1Z',clay),
  user:p('M4 22v-2a8 8 0 0 1 16 0v2Z',leaf)+wash('M14 14q6 1 6 8h-5Z',leafShade)+p('M9 14v2q3 3 6 0v-2',skin)+e(12,8,5,6,hair)+e(12,9,4.5,5,skin)+p('M7.5 8q0-6 5-6 5 0 4 6-3-1-4-3-2 3-5 3Z',hair)+face(12,9)+line('m7 18 2 4m8-4-2 4',mint,.8),
  people:p('M13 20v-2q0-7 8-3l1 5Z',clay)+e(17,7.5,3.7,4.6,hair)+e(17,8.3,3.2,3.7,skin)+p('M2 21v-3q0-7 13-4l2 7Z',leaf)+wash('M12 14q4 1 5 7h-5Z',leafShade)+e(8.5,7.5,4.5,5.2,hair)+e(8.5,8.5,4,4.2,skin)+p('M4.5 7q1-6 5-4 3 0 3 4l-3-2q-2 3-5 2Z',hair)+face(8.5,8.5)+dot(17,8,.6)+dot(19,8,.5)+line('m5 17 2 4',mint,.8),
  bag:line('M8 8V6a4 4 0 0 1 8 0v2',wood,1.7)+p('M5 7h14l2 14H3Z',gold)+wash('M16 7h3l2 14h-5Z',goldShade)+p('M9 12q3-2 6 0v4q-3 2-6 0Z',paper)+p('M11 14q1-3 3-2 0 2-3 2Z',leaf)+line('M11 14v2',leafShade,.8)+dot(8,9,.6,wood)+dot(16,9,.6,wood),
  gift:r(4,9,16,12,leaf,1)+wash('M16 9h4v12h-4Z',leafShade)+r(3,7,18,5,mint,1)+r(10.5,7,3,14,clay,.2)+p('M12 7C3 8 5 0 9 3q3 2 3 4Zm0 0c9 1 7-7 3-4q-3 2-3 4Z',rose)+shine('M6 9h3'),
  cross:p('M8 2.5h8v5.5h5.5v8H16v5.5H8V16H2.5V8H8Z',clay)+wash('M13 3h3v5h5v8h-5v5h-3V13h6v-2h-6Z',clayShade)+shine('M5 10h5V5'),
  headphones:line('M4 13V10a8 8 0 0 1 16 0v3',blueShade,3)+line('M5 9q1-7 7-7',water,1)+r(2.5,11,5,8,blue,2)+r(16.5,11,5,8,blue,2)+r(5.5,12,2.5,6,cream,1)+r(16,12,2.5,6,cream,1)+line('M19 19q0 3-6 2',wood,1.3)+r(10,20,4,2,gold,1),
  wrench:p('M14 8q-1-5 5-6l-2 4 2 2 3-3q1 6-5 7L8 21q-3 2-5-1-1-2 1-3Z',blue)+wash('m17 11-9 10q-2 1-3-1l11-11Z',blueShade)+c(6,18.5,1.1,paper)+shine('m8 15 6-6'),
  scissors:c(6,7,3.5,rose)+c(6,18,3.5,rose)+c(6,7,1.8,paper)+c(6,18,1.8,paper)+p('m8 10 12 11q2-1 0-3L10 8Zm0 4L20 2q2 1 0 4L10 16Z',blue)+dot(12,12,.9,gold),
  chat:p('M3 11a8.5 8 0 1 1 8.5 8q-2 0-4-.7L3 21l1-5q-1-2-1-5Z',mint)+wash('M18 5q5 6-1 11-3 3-9 1l-5 4 4.5-2.7Q18 22 21 13q1-5-3-8Z',leaf)+line('M7 9h9M7 12.5h6',leafShade,1.3)+dot(16.5,13,.7,leafShade),
  chats:p('M11 8q11-3 11 5 0 2-1.5 4L22 21l-5-2q-7 1-8-5Z',gold)+p('M2 9q0-7 8-7t8 7q0 7-10 6l-5 3 1-5q-2-2-2-4Z',mint)+wash('M15 4q4 7-3 9l-5 1-4 4 5-3q12 1 10-8Z',leaf)+line('M6 7h8M6 10.5h5',leafShade,1.2),
  boat:p('M2 16h20l-4 5H6Z',wood)+wash('m4 18 16-.5-2 3H6Z',clayShade)+line('M11 16V2',wood,1.4)+p('M12 3v11h9Z',paper)+p('M9 6v8H3Z',leaf)+line('M2 22q3-2 5 0 3-2 5 0 3-2 5 0 3-2 5 0',blueShade,.9),
  pool:e(12,17,10,4.5,water)+wash('M3 18q8 4 18 0l-2 3H5Z',blue)+line('M7 17V6a2.5 2.5 0 0 1 5 0m2 10V5a2.5 2.5 0 0 1 5 0M7 9h7M7 13h7',wood,1.5)+line('M3 18q2-2 4 0t4 0m3 1q2-2 4 0',paper,1.1),
  overview:p('M6 13 11 6l7 3 1 7-9 2Z',mint)+p('m10 12 3-3 4 3v4h-7Z',cream)+p('m9 12 4-4 5 4',clay)+line('M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m13-5v3a2 2 0 0 1-2 2h-3','currentColor',1.5),
};

Object.assign(marks,{
  music:p('M9 5 20 2v14h-3V7l-5 1.5V18H9Z',clay)+wash('M9 5 20 2v3L9 8Z',gold)+e(8,18,4,3,blue)+e(16,16,4,3,blue)+shine('m11 5 6-1.5'),
  globe:c(12,10.5,8.5,blue)+p('m6 4 3 1 1 3-3 2-3-1m13-5-3 3 2 3-1 4 3 2 2-5',mint)+line('M19 3q9 12-5 18M12 20v2M7 22h11',wood,1.5)+shine('M7 5q-3 2-3 5'),
  palette:p('M12 2C5 1 1 8 3 14s8 9 11 6c2-2-2-4 1-5 3-1 5 2 7-2 2-5-4-11-10-11Z',cream)+wash('M20 6q5 8-4 9-4-1-3 4l1 1q-2 3-6 1 5 1 3-3-1-5 5-5 6 0 4-7Z',gold)+c(7,8,1.8,clay)+c(12,5.8,1.8,blue)+c(17,8,1.8,leaf)+c(6.5,13.5,1.8,lilac)+c(9.5,17.5,1.5,paper),
  layout:r(3,3,18,18,paper,2)+p('M3 6q0-3 3-3h12q3 0 3 3v3H3Z',clay)+p('M3 9h6v12H6q-3 0-3-3Z',mint)+line('M9 9v12M12 12h6m-6 3h4',wood,.9),
  inbox:p('m3 12 3-8h12l3 8v8H3Z',blue)+p('M6 4h12l2 8h-5l-1.5 3h-3L9 12H4Z',water)+p('M3 12h6l1.5 3h3l1.5-3h6v8H3Z',blue)+wash('M17 13h4v7h-4Z',blueShade)+line('M9 7h6m-6 2h4',wood,.9),
  settings:p('m9 3 1-1h4l1 3 3 1 3 3-1 3 1 3-3 3-3 1-1 3h-4l-1-3-3-1-3-3 1-3-1-3 3-3 3-1Z',blue)+c(12,12,5,water)+c(12,12,3,paper)+line('M9 5q3-1 5 0',paper,.9),
  coin:e(12,13,9,9,goldShade)+c(11,11,8.5,gold)+c(11,11,6.4,cream)+p('M9 7h4v8H9Z',gold)+line('M11 5v2m0 8v2',goldShade,.8)+shine('M5 8q1-3 4-3'),
  star:p('m12 2 3 6 6.5 1-4.7 4.7 1 6.8-5.8-3-5.8 3 1-6.8L2.5 9 9 8Z',gold)+wash('m12 2 3 6 6.5 1-9.5 4Z',cream)+wash('m12 13 5.8 7.5-1-6.8 4.7-4.7Z',goldShade)+shine('m6 10 3.5-.5L11 6'),
  sun:line('M12 2V4m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M19 5l-1.5 1.5m-11 11L5 19',goldShade,1.5)+c(12,12,6,gold)+wash('M14 6.5a6 6 0 0 1-5 11q7 0 5-11Z',clay)+shine('M8 10q.5-2 2-2'),
  cloud:p('M5 19a4.5 4.5 0 0 1-1-9q1-6 7-6 6 0 7 6a4.5 4.5 0 0 1 1 9Z',water)+wash('M19 10q5 1 3 6-1 3-5 3H5q-3 0-3-3 6 4 15 0 4-1 2-6Z',blue)+shine('M6 10q1-4 5-4'),
  clock:c(12,12,9.5,blue)+c(12,12,7.5,paper)+line('M12 7v5l4 2',wood,1.6)+dot(12,12,1,clay)+line('M12 5v1m0 12v1M5 12h1m12 0h1',goldShade,.8),
  sparkle:p('M12 2q2 7 10 10-8 2-10 10-2-8-10-10 8-3 10-10Z',gold)+wash('M12 2v10l10 0q-8 2-10 10Z',goldShade)+shine('m7 11 3-2 1-3'),
  sparkles:p('M9 6q1.5 6 7 8-6 2-7 8-2-6-7-8 6-2 7-8Z',gold)+p('M18 2q.7 3.3 4 4-3.3 1-4 4-1-3-4-4 3-1 4-4Z',rose)+p('m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8Z',blue)+shine('M6 14l2-1'),
  eye:p('M2 12q10-14 20 0-10 14-20 0Z',paper)+c(12,12,4.5,leaf)+c(12,12,2.2,ink)+dot(10.7,10.7,.9,paper),
  lock:line('M7 10V7a5 5 0 0 1 10 0v3',wood,2)+r(4,9,16,13,gold,2)+wash('M16 9h2q2 0 2 2v9q0 2-2 2h-2Z',goldShade)+c(12,14.5,1.5,wood)+line('M12 16v2',wood,1.8)+shine('M7 12v5'),
  box:p('m3 7 9-4 9 4v12l-9 3-9-3Z',gold)+p('m3 7 9 4 9-4-9-4Z',cream)+p('M12 11v11l9-3V7Z',wood)+p('m7 5 9 4v5l-3 1v-5L4 6Z',paper)+r(6,13,3,3,clay,.5)+line('m15 18 3-1',paper,.9),
  clipboard:r(4,4,16,18,wood,2)+r(6,6,12,14,paper,.8)+r(8,2,8,5,gold,1.5)+line('m8 11 1.2 1.2L12 9.5m1.5 1.5h2M8 16h8',leafShade,1.1)+dot(12,3.8,.5,wood),
  folder:p('M3 5h6l2 2h10v14H3Z',goldShade)+p('M3 8h18l-2 13H2Z',gold)+wash('m17 8 4 0-2 13h-3Z',clay)+r(5,11,7,3,paper,.6)+line('M6.5 12.5H10',wood,.6),
  trash:line('M9 5V2h6v3',wood,1.4)+p('M5 6h14l-1 15H6Z',blue)+wash('M15 6h4l-1 15h-3Z',blueShade)+r(3.5,4.5,17,3,water,1.2)+line('M9 10v7m6-7v7',paper,1.2),
  camera:p('M3 7h4l2-3h6l2 3h4v13H3Z',blue)+wash('M17 7h4v13h-4Z',blueShade)+r(3,7,18,4,cream,.6)+c(12,13,5,wood)+c(12,13,3.5,water)+c(12,13,2,blueShade)+dot(11,12,1,paper)+dot(18.5,9,.6,clay),
  grid:r(3,3,7.5,7.5,leaf,1.5)+r(13.5,3,7.5,7.5,gold,1.5)+r(3,13.5,7.5,7.5,clay,1.5)+r(13.5,13.5,7.5,7.5,blue,1.5)+shine('M5 5h3m7 0h3M5 15.5h3m7 0h3'),
  flag:line('M4 22V3',wood,1.7)+p('M4 3q5-3 10 0l6-1v11l-6 1q-5-3-10 0Z',clay)+wash('M14 3 20 2v11l-6 1Z',gold)+line('M7 5q3-1 5 0',paper,.9),
  award:p('m7 14-1 8 6-3 6 3-1-8Z',clay)+wash('m12 16 0 3 6 3-1-8Z',clayShade)+c(12,9,7.5,gold)+c(12,9,5.5,cream)+p('m12 5 1.2 2.6L16 8l-2 2 .5 2.7-2.5-1.3-2.5 1.3L10 10 8 8l2.8-.4Z',gold),
  calendar:r(3,4,18,18,paper,2)+p('M3 7V6q0-2 2-2h14q2 0 2 2v3H3Z',clay)+line('M7 2v4m10-4v4',wood,1.5)+r(6,12,3,3,mint,.4)+r(11,12,3,3,gold,.4)+r(16,12,2,3,cream,.4)+r(6,17,3,2,cream,.4)+r(11,17,3,2,cream,.4)+line('m16 18 1 1 2-2',leafShade,1),
  mail:r(2.5,5,19,15,cream,1.7)+p('m3 6 9 7 9-7',paper)+p('m3 19 6-6m12 6-6-6',gold)+p('M13 10q2-3 4-1 2 2-4 6-6-4-4-6 2-2 4 1Z',clay),
  send:p('m2 10 20-8-7 20-4-8Z',blue)+p('m2 10 20-8-11 12Z',water)+line('m11 14 11-12',blueShade,1)+wash('m11 14 4 8-1-10Z',blueShade),
  shield:p('M12 2 21 6v6c0 5-9 10-9 10S3 17 3 12V6Z',leaf)+p('M12 4 19 7v5q0 4-7 8Z',mint)+line('m7.5 12 3 3 6-7',paper,1.8),
  rug:p('m3 5 17-2 1 16-17 2Z',rose)+p('m6 7 11-1 1 10-11 2Z',cream)+p('m12 8 4 4-3 4-4-3Z',clay)+line('M3 2v2m4-2v2m6-3v2m6-3v2M4 22v1m5-2v2m6-3v2m5-3v2',wood,.8),
  lamp:p('M8 3h8l4 11H4Z',gold)+wash('m14 3 2 0 4 11h-5Z',goldShade)+p('M12 14v7m-5 1h10',wood)+e(12,14,8,1.5,cream)+line('M12 16v5',wood,1.8)+shine('m9 5-2 6'),
  chair:r(5,3,14,11,leaf,2.5)+wash('M15 3h2q2 0 2 2v9h-4Z',leafShade)+r(3.5,13,17,5,mint,1.5)+line('M5 18v4m14-4v4',wood,1.8)+line('M8 6v4m4-4v4',mint,.9),
  shelf:r(3,2,18,20,wood,.7)+r(5,4,14,6,paper,.1)+r(5,12,14,7,paper,.1)+r(6,5,2,5,clay,.2)+r(8.5,4.5,2,5.5,blue,.2)+p('m12 5 2-.5 1 5-2 .5Z',leaf)+r(6,14,5,4,gold,.5)+p('M14 18v-3q-4-3-1-4 3 1 2 4 1-5 4-3 0 3-4 3v3Z',leaf)+line('M3 20h18',goldShade,1.1),
  board:r(3,3,18,14,wood,1)+r(5,5,14,10,leafShade,.4)+line('M12 17v5m-5 0 5-5 5 5',wood,1.6)+line('M7 8h6m-6 3h10',paper,1.1)+r(15,14,3,1.5,paper,.3),
  image:r(3,3,18,18,wood,1.4)+r(5,5,14,14,water,.4)+c(15.5,8.5,2,gold)+p('m5 16 5-6 4 4 2-2 3 5v2H5Z',leaf)+p('m5 19 5-5 5 5Z',leafShade),
  heart:p('M12 21C4 16 0 10 3 5q4-5 9 1 5-6 9-1c3 5-1 11-9 16Z',rose)+wash('M18 3q6 4-1 12l-5 6q7-3 10-10 2-6-4-8Z',clayShade)+shine('M5 8q0-3 3-3'),
  cat:p('M5 10 4 3l6 3h4l6-3-1 7q6 11-7 11T5 10Z',gold)+p('m5.5 5 3 2-3 1Zm13 0-3 2 3 1Z',rose)+wash('M18 10q5 9-6 11 12 1 9-8Z',goldShade)+dot(8.5,12,.85)+dot(15.5,12,.85)+p('m10.5 15 1.5 1.5 1.5-1.5Z',clay)+line('M12 16.5q-2 2-3 0m3 0q2 2 3 0M3 14h3m12 0h3M3 17l3-1m12 0 3 1',wood,.8),
  note:p('M5 2.5h14V22l-4-2-3 2-3-2-4 2Z',paper)+wash('M16 3h3v19l-3-1.5Z',cream)+line('M8 7h8M8 11h8M8 15h5',wood,1)+r(8,2,8,2,clay,.5),
  bell:p('M5 17V10q0-7 7-7t7 7v7l2 3H3Z',gold)+wash('M14 3q5 1 5 7v7l2 3h-7q3-4 2-10Z',goldShade)+c(12,21,1.5,wood)+r(3,18,18,2.5,cream,1)+line('M12 1v2',wood,1.4)+shine('M8 8q.5-2 2-2'),
  phone:r(6,2,12,20,wood,2)+r(7.5,4.5,9,13,water,.8)+wash('m8 15 8-9v4l-8 7Z',blue)+line('M10 3h4',cream,.8)+c(12,19.5,.9,cream),
  server:r(4,3,16,6,blue,1.4)+r(4,10,16,6,blue,1.4)+r(4,17,16,5,blue,1.4)+line('M7 6h6m-6 7h6m-6 6.5h6',paper,.9)+dot(17,6,.8,gold)+dot(17,13,.8,mint)+dot(17,19.5,.8,mint),
  print:r(3,8,18,10,blue,2)+r(6,2,12,7,paper,.5)+r(6,14,12,8,paper,.5)+line('M9 17h6m-6 2h5',wood,.8)+dot(18,11,.7,gold),
  pulse:line('M2 13h4l3-8 5 15 3-9 2 2h3',clay,2),
});

// Item symbols also appear in reward and inventory interfaces. Their 24px
// silhouettes share material colors with the larger itemArt illustrations.
Object.assign(marks,{
  bunny:e(8,6,2.7,5,paper)+e(16,6,2.7,5,paper)+line('M8 3v4m8-4v4',rose,1.5)+e(12,18,6,4.5,cream)+e(12,13,8,6,paper)+dot(9,12,.75)+dot(15,12,.75)+p('m11 14 1 1 1-1Z',rose)+line('m10 16 2-1 2 1',wood,.7)+p('m12 20-3-2v4l3-1 3 1v-4Z',leaf),
  shirt:p('m8 3-6 4 3 5 3-1v11h8V11l3 1 3-5-6-4q-4 5-8 0Z',blue)+wash('M14 4h2v18h-3Z',blueShade)+line('M8 3q4 7 8 0',paper,1.2)+p('M9.5 11h5v5h-5Z',cream)+p('M11 12q1-2 2 0l-1 2Z',clay),
  cloth:r(3,6,18,15,rose,2)+wash('M16 6h5v15h-5Z',clay)+r(10.5,6,3,15,paper,.1)+p('M12 7C3 6 7 0 10 3Zm0 0c9-1 5-7 2-4Z',cream)+line('M5 9v9',paper,.8),
  blocks:p('m3 9 7-7 7 7Z',clay)+r(3,12,8,9,gold,.8)+p('m14 11 7 1v9h-7Z',blue)+p('m14 11 3-2 6 1-2 2Z',water)+c(7,16.5,2,paper)+p('m16 18 2-4 2 4Z',cream),
  card:r(3,4,18,16,paper,1)+p('M3 5 12 12 21 5',cream)+p('M12 9q3-4 5-1 2 3-5 8-7-5-5-8 2-3 5 1Z',rose)+line('M6 18h5',wood,.8),
  rattle:line('m12 13 3 7',wood,4)+c(10,8,7,gold)+wash('M4 9q7 3 12-3 2 7-4 9-6 1-8-6Z',clay)+dot(7,6,1,paper)+dot(11,5,1,paper)+dot(13.5,8,.8,paper)+e(15.2,20,3,2,leaf),
  teether:p('M6 7q-3-4 1-5 4-1 5 3 1-4 5-3 4 1 1 5 6 0 4 5-1 3-5 1 3 5-2 7-3 1-3-3-1 4-4 3-5-2-2-7-4 2-5-1-2-5 5-5Z',mint)+c(12,10.5,4.1,paper)+c(12,10.5,2.7,blue),
  bottle:p('M8 7V5q1-1 2-1V2h4v2q1 0 2 1v2',cream)+r(6,9,12,13,water,3)+p('M6 14h12v5q0 3-3 3H9q-3 0-3-3Z',paper)+r(5.5,7,13,4,rose,1.5)+line('M8.5 15h2m-2 3h2',blueShade,.8),
  bib:p('M7 3q-4 2-4 8v3q0 8 9 8t9-8v-3q0-6-4-8-1 6-5 6T7 3Z',blue)+p('M9 14q3-4 6 0 2 3-3 5-5-2-3-5Z',gold)+dot(7,4,.65,paper)+dot(17,4,.65,paper),
  socks:p('M4 3h6v12q0 5-5 5-4 0-3-3l2-3Z',rose)+p('M14 5h6v11l2 2q1 4-3 4-5 0-5-5Z',blue)+line('M4 6h6m4 2h6',paper,2)+wash('m3 15 2 2-1 3q-4 0-2-3Zm16 2 3 1q1 4-3 4Z',cream),
  blanket:p('M4 3h14q3 0 3 3v15H6q-3 0-3-3V6q0-3 3-3Z',lilac)+p('M7 3v14q-4-2-4 1V6q0-3 4-3Z',cream)+p('M10 7h7v8h-7Z',paper)+p('m13.5 8 1 2 2 .5-1.5 1.5.2 2-1.7-1-1.7 1 .2-2-1.5-1.5 2-.5Z',gold)+line('M8 19h10',paper,.9),
});

Object.assign(marks,{
  milk_tea:p('M6 7h12l-1 15H7Z',cream)+wash('M14 7h4l-1 15h-4Z',gold)+p('m12 8 3-7h2l-3 7',leaf)+r(5,5,14,3,paper,1)+dot(9,18,1.1,wood)+dot(13,19,1.1,wood)+dot(15,16,1,wood)+dot(10.5,15.5,1,wood)+shine('M8 10v3'),
  ice_cream:p('m6 11 6 11 6-11Z',gold)+line('m8 12 6 6m-3-6 4 4m0-4-6 4',wood,.7)+p('M4 10q-1-4 3-5 0-5 5-3 5-2 5 3 4 1 3 5Z',rose)+p('M4 10h16v2q-2 2-4 0-2 3-4 0-2 3-4 0-2 2-4 0Z',paper)+dot(10,4,.6,clay),
  com:e(12,13,10,7,blue)+e(12,12,8,5,paper)+p('M6 13q0-8 6-8 5 0 5 8Z',cream)+line('m8 10 .8-1m2-1 1 1m1-3 1 1m0 3 1 1',paper,.9)+e(16,13,3,1.8,clay)+p('M5 14q2-3 4 0-2 3-4 0Z',leaf),
  nail:r(4,6,10,16,rose,2)+r(5.5,2,7,6,wood,1)+r(6,12,6,6,paper,1)+p('M9 13q2 0 2 3v1H7v-1q0-3 2-3Z',clay)+p('M19 3v6m-3-3h6m-4 7 1.2 2.8L22 17l-2.8 1.2L18 21l-1.2-2.8L14 17l2.8-1.2Z',gold),
  cleaning:line('M15 2 8 15',wood,2)+p('m7 13 6 3-3 6-8-4Z',gold)+line('m6 16-2 3m4-2-2 3m4-2-2 3',wood,.8)+p('M18 8V3h2v5l2 3v10h-8V11Z',blue)+r(15,12,6,5,paper,.5)+line('M17 2h4',clay,2),
  pilot:p('m2 12 8-3V4q2-4 4 0v5l8 3v3l-8-2v5l3 2v2l-5-1-5 1v-2l3-2v-5l-8 2Z',paper)+wash('M12 2q2 0 2 2v5l8 3v3l-8-2v5l3 2v2l-5-1Z',blue)+p('M10.5 6h3v3h-3Z',blueShade)+line('M4 13h2m12 0h2',clay,1),
  pagoda:p('M5 12h14v9H5Z',cream)+r(10,15,4,6,wood,.7)+p('M3 12q6-3 9-7 3 4 9 7-6 1-9-1-3 2-9 1Z',clay)+p('M5 6q5-1 7-4 2 3 7 4-4 2-7 0-3 2-7 0Z',gold)+line('M12 1v1m-5 13v4m10-4v4',wood,.9),
});

// Compact controls deliberately stay open and use the surrounding text color.
const controls={
  menu:'M4 6h16M4 12h16M4 18h16',chevron:'m9 5 7 7-7 7',arrow:'M4 12h16m-7-7 7 7-7 7',back:'M20 12H4m7-7-7 7 7 7',
  plus:'M12 5v14M5 12h14',minus:'M5 12h14',check:'m4 12 5 5L20 6',x:'m6 6 12 12M18 6 6 18',
  search:'M10.5 3a7.5 7.5 0 1 0 0 15 7.5 7.5 0 0 0 0-15Zm5.5 13 5 5',
  link:'m10 14 4-4m-6 1L5 14a3.5 3.5 0 0 0 5 5l3-3m-2-8 3-3a3.5 3.5 0 0 1 5 5l-3 3',
  play:'m8 4 12 8-12 8Z',pause:'M8 4v16m8-16v16',
  volume:'M3 9h4l5-5v16l-5-5H3Zm13-1a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14',
  mute:'M3 9h4l5-5v16l-5-5H3Zm14 0 5 6m0-6-5 6',
  expand:'M3 9V3h6m6 0h6v6m0 6v6h-6m-6 0H3v-6',
  download:'M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4',upload:'M12 16V4m-5 5 5-5 5 5M4 17v4h16v-4',
  refresh:'M20 7a9 9 0 1 0-1 12m1-17v6h-6',exit:'M9 3H3v18h6m0-9h12m-5-5 5 5-5 5',
  move:'M12 2v20M2 12h20M8 6l4-4 4 4M8 18l4 4 4-4M6 8l-4 4 4 4M18 8l4 4-4 4',
  external:'M13 3h8v8m0-8L10 14M9 5H3v16h16v-6',
};
for(const [name,path] of Object.entries(controls))marks[name]=p(path,'none','stroke="currentColor" stroke-width="1.7"');
marks.question=c(12,12,9.5,water)+line('M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5',blueShade,1.5)+dot(12,17,1,blueShade);
marks.info=c(12,12,9.5,water)+dot(12,7,1,blueShade)+line('M12 11v6',blueShade,1.8);
marks.alert=p('M10.5 3.5q1.5-2 3 0l9 16q1 2-1 2h-19q-2 0-1-2Z',gold)+line('M12 8v6',wood,1.8)+dot(12,17.5,1,wood);
marks.tool=marks.wrench;
marks.envelope=marks.mail;
marks.pho=marks.bowl;

/** Resolve careers without changing the server catalogue or old icon(name) API. */
export const careerIconNames=Object.freeze({
  mother_baby:'gift',pharmacy:'cross',accounting:'book',customer_care:'headphones',restaurant:'bowl',cafe_bakery:'cake',
  freelancer:'palette',farm:'tractor',sales:'store',grocery:'cart',fashion:'shirt',pet_care:'paw',florist:'flower',salon:'scissors',
  repair:'wrench',homestay:'bed',teacher:'book',tour_guide:'compass',milk_tea:'milk_tea',delivery:'bike',corp_accounting:'calculator',
  tax_payroll:'calculator',group_accounting:'building',clothing:'shirt',pet_shop:'fish',tra_da:'coffee',fruit:'basket',garbage:'truck',
  drain:'wrench',homemaker:'home',ice_cream:'ice_cream',nail:'nail',pagoda:'pagoda',pho:'pho',com:'com',photobooth:'camera',
  giupviec:'cleaning',naucom:'com',babysitter:'bear',pilot:'pilot',flight_attendant:'bell',hr_admin:'people',secretary:'calendar',it_helpdesk:'settings',
});
export const iconNames=Object.freeze(Object.keys(marks));
export const hasIcon=name=>Object.hasOwn(marks,name);
const safe=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
// A neutral unknown mark makes omissions distinguishable from intentional sparkles.
const unknown=p('m12 3 9 9-9 9-9-9Z',cream)+dot(12,12,1.5,wood);
export function illustratedIcon(name,size=20,cls=''){
  const value=Number(size),dimension=Number.isFinite(value)&&value>0?Math.min(256,value):20;
  const primitive=Object.hasOwn(controls,name);
  return `<svg class="icon illustrated-ui-icon${cls?' '+safe(cls):''}" width="${dimension}" height="${dimension}" viewBox="0 0 24 24" fill="none" stroke="${primitive?'currentColor':ink}" stroke-width="1.05" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${hasIcon(name)?marks[name]:unknown}</svg>`;
}
