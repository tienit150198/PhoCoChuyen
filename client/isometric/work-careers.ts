import type {Rect} from './model';
import type {WorkFloor,WorkFurniture,WorkLayout} from './work-layout';

export interface CareerRoomIdentity {focus:string;workbench:string;zones:[string,string]}
const identity=(focus:string,workbench:string,a:string,b:string):CareerRoomIdentity=>({focus,workbench,zones:[a,b]});

/** Names describe the existing tasks in game/content.py, extra_content.py and
 * game/careers/<career>.py; these are signs, never new actions or game rules. */
const IDENTITIES:Record<string,CareerRoomIdentity>={
  milk_tea:identity('Đọc món · chỉnh đường và đá','Quầy pha chế','Ủ trà & topping','Nhận ly'),
  cafe_bakery:identity('Nướng bánh · pha cà phê','Lò bánh & bàn pha','Bánh mới ra lò','Góc cà phê'),
  restaurant:identity('Chuẩn bị nguyên liệu · ra món','Bếp chế biến','Bếp nóng','Soạn món'),
  grocery:identity('Chọn hàng · cân và tính tiền','Bàn soạn hàng','Hàng thiết yếu','Cân hàng'),
  florist:identity('Chọn hoa · bó theo lời nhắn','Bàn bó hoa','Dưỡng hoa','Gói hoa'),
  mother_baby:identity('Chọn đúng cỡ · gói quà cho bé','Quầy soạn đồ cho bé','Đồ cho bé','Gói quà'),
  pharmacy:identity('Đọc phiếu · kiểm đúng mã hộp','Khay kiểm tra','Mã hộp & vật tư','Kiểm phiếu'),
  salon:identity('Tư vấn kiểu · chăm sóc tóc','Ghế gương làm tóc','Gội & dưỡng','Tạo kiểu'),
  pet_care:identity('Nhận bé · tắm và chăm sóc','Bồn tắm thú cưng','Tắm & vệ sinh','Chờ đón bé'),
  repair:identity('Nhận máy · tìm lỗi và kiểm lại','Bàn kiểm tra máy','Dụng cụ & linh kiện','Kiểm máy'),
  nail:identity('Đọc lịch hẹn · làm móng','Bàn làm móng','Chọn màu','Làm móng'),
  teacher:identity('Soạn tiết học · giúp từng bạn','Bảng và góc học tập','Lớp học','Góc học liệu'),
  accounting:identity('Mở bản gốc · đối chiếu hồ sơ','Bàn đối chiếu','Bản gốc','Đối chiếu'),
  corp_accounting:identity('Hạch toán · đối soát và khóa sổ','Bàn hạch toán','Chứng từ mua bán','Đối soát sổ'),
  tax_payroll:identity('Chấm công · tính lương và kê khai','Bàn tính lương & thuế','Hợp đồng & chấm công','Kê khai & phiếu lương'),
  group_accounting:identity('Đối chiếu nội bộ · hợp nhất báo cáo','Bàn hợp nhất','Báo cáo công ty con','Đối chiếu nội bộ'),
  customer_care:identity('Lắng nghe · phối hợp xử lý yêu cầu','Bàn hỗ trợ','Tiếp nhận cuộc gọi','Phối hợp xử lý'),
  hr_admin:identity('Xét hồ sơ · xếp lịch phỏng vấn','Bàn hồ sơ nhân sự','Hồ sơ & chấm công','Phỏng vấn'),
  secretary:identity('Phân thư · thu xếp lịch giám đốc','Bàn thư ký','Thư đến & lịch hẹn','Tiếp khách'),
  it_helpdesk:identity('Phân loại phiếu · kiểm tra thiết bị','Bàn hỗ trợ IT','Thiết bị & mạng','Kiểm tra sự cố'),
  farm:identity('Chăm luống rau · đóng hàng','Luống rau','Luống canh tác','Đường thu hoạch'),
  delivery:identity('Xếp bưu kiện · theo tuyến giao','Bàn chia tuyến','Chia bưu kiện','Hàng chờ giao'),
  tour_guide:identity('Chọn lộ trình · kiểm đủ người','Bản đồ hành trình','Hành trình','Tập trung đoàn'),
  homestay:identity('Xem lịch phòng · đón khách','Bàn nhận phòng','Buồng khách','Lễ tân'),
  homemaker:identity('Sắp việc nhà · chăm bữa cơm','Bàn việc nhà','Bếp gia đình','Sinh hoạt chung'),
  naucom:identity('Nghe chủ nhà dặn · nấu bữa cơm','Bếp nấu cơm thuê','Sơ chế','Bữa cơm gia đình'),
  tra_da:identity('Dọn hàng ra · đón khách bên gốc bàng','Bàn pha trà','Góc pha trà','Ghế chuyện phố'),
  clothing:identity('Chọn áo · so cỡ và gói hàng','Bàn so cỡ','Giá áo','Thử & gấp đồ'),
  pet_shop:identity('Chọn hạt và pate · chăm thú nhỏ','Bàn soạn đồ thú cưng','Hạt & pate','Góc thú nhỏ'),
  fruit:identity('Lựa trái · cân và tách trái dập','Sạp lựa trái cây','Trái mới về','Lựa & cân'),
  garbage:identity('Phân loại túi · thu gom theo tuyến','Xe gom ba ngăn','Phân loại rác','Điểm tập kết'),
  drain:identity('Hỏi triệu chứng · kiểm tra đường thoát','Bàn kiểm dụng cụ','Ống & dụng cụ','Kiểm tra nước'),
  ice_cream:identity('Chọn vị · múc kem và thêm topping','Tủ múc kem','Kem & ốc quế','Nhận kem'),
  com:identity('Nấu cơm · nướng sườn và soạn đĩa','Bếp cơm tấm','Bếp than','Soạn đĩa cơm'),
  pagoda:identity('Công phu · chăm sân chùa','Bàn chuẩn bị việc chùa','Gian thờ','Chiếu công phu'),
  pho:identity('Nếm nước dùng · chần và soạn bát','Bếp phở','Nồi nước dùng','Soạn bát'),
  photobooth:identity('Chụp thử · chọn khung và in ảnh','Buồng chụp ảnh','Buồng chụp','Chọn & in ảnh'),
  giupviec:identity('Chuẩn bị khăn chai · dọn theo lịch','Xe đồ nghề dọn nhà','Giặt & chuẩn bị','Lịch dọn nhà'),
  babysitter:identity('Đọc giấy dặn · chăm giấc ngủ của bé','Bàn chơi cùng bé','Giấc ngủ của bé','Chơi & học'),
  library:identity('Xếp theo ký hiệu · mượn trả sách','Bàn xử lý sách','Kho sách','Phòng đọc'),
  pilot:identity('Xem thời tiết · kiểm chuyến và ghi sổ','Bảng kiểm buồng lái','Buồng lái','Điều phái'),
  flight_attendant:identity('Đón hành khách · phục vụ khoang','Bàn chuẩn bị khoang','Khoang hành khách','Khoang bếp'),
  oil:identity('Nhận giấy phép · kiểm tra thiết bị','Bàn kiểm ca vận hành','Cụm ống & đồng hồ','Giấy phép làm việc'),
  railway:identity('Thử thiết bị · canh đường ngang','Bàn trực gác chắn','Thiết bị tín hiệu','Chòi gác'),
  nurse:identity('Đọc sổ giao ca · theo dõi người bệnh','Bàn điều dưỡng','Buồng bệnh','Điều dưỡng'),
  lighthouse:identity('Thử máy · lau kính và trực đèn','Bàn trực hải đăng','Tháp đèn & bàn trực','Vườn rau trên đá'),
  rescue:identity('Nhận cuộc gọi · liên lạc từng đội','Bàn trực tổng đài','Tổng đài','Bản đồ & bộ đàm'),
  lifeguard:identity('Thử nước · kiểm phao và quan sát hồ','Bàn trực cứu hộ','Mặt hồ','Trực cứu hộ'),
  police:identity('Đọc sổ trực · tiếp nhận việc dân','Bàn tiếp dân','Tiếp dân','Ghế chờ'),
  zpop:identity('Kiểm bản giới hạn · quét album','Bàn kiểm album','Album & đặt trước','Quét Zchart'),
};

const r=(x0:number,y0:number,x1:number,y1:number):Rect=>({x0,y0,x1,y1});
const wood=0xbc9972,mint=0xabc6b6,blue=0x93aeb9,cream=0xe3d3b0;

/** Authored occupation plans use the same protected perimeter as the original
 * room: x 2.7–8.4 / y .5–4.45 is the work area, y 5–7 is circulation. Nothing
 * depends on random seeds, save contents, or character count. */
export function applyCareerPlan(layout:WorkLayout,career:string):void{
  layout.identity=IDENTITIES[career]||layout.identity;
  const s=(id:string,kind:WorkFurniture,box:Rect,x:number,y:number,height=62,color=wood)=>{
    const item=layout.stations.find(st=>st.id===id)!;
    Object.assign(item,{kind,footprint:box,at:{x:(box.x0+box.x1)/2,y:box.y1},approach:{x,y},height,color});
  };
  const f=(kind:WorkFurniture,footprint:Rect,height=58,color=wood)=>layout.fixtures.push({kind,footprint,height,color});
  const refurnish=(id:string,kind:WorkFurniture,height:number,color=wood)=>Object.assign(layout.stations.find(st=>st.id===id)!,{kind,height,color});
  const z=(footprint:Rect,pattern:WorkFloor['pattern']='carpet',color=0xc5c6b4,accent=0xe2d9bd)=>layout.floors.push({footprint,pattern,color,accent});
  const clear=(outdoor=false,pattern:WorkFloor['pattern']='plank')=>{
    layout.fixtures=[];layout.floors=[{footprint:r(0,0,10,9),pattern,color:outdoor?0xd0ccb5:0xe5cba4,accent:0xc2b99b}];layout.outdoor=outdoor;
  };

  if(career==='accounting'){
    clear();s('workbench','desk',r(3,2.9,5.5,3.9),4.2,4.5);
    f('bookcase',r(2.9,.55,4.25,1.25),116);f('desk',r(5,.55,6.3,1.3),55,mint);f('sofa',r(.55,7.7,1.5,8.3),40,blue);
    z(r(2.65,.3,6.55,1.55),'plank');z(r(2.75,2.6,5.8,4.25));
  }else if(career==='corp_accounting'){
    clear();s('workbench','desk',r(3,.65,6.1,1.65),4.5,2.25,63,mint);
    f('desk',r(3.05,3.6,4.35,4.3),60,blue);f('desk',r(5.15,3.6,6.15,4.3),60,blue);
    z(r(2.75,.35,6.4,1.95),'tile');z(r(2.8,3.3,6.4,4.6));
  }else if(career==='tax_payroll'){
    clear();s('workbench','desk',r(3.1,2.65,5.65,3.6),4.2,4.2,62,mint);
    f('bookcase',r(3,.55,4.55,1.3),112);f('board',r(5.4,.55,6.4,1.3),102,blue);f('bench',r(.55,7.7,1.5,8.3),34);
    z(r(2.75,.3,6.65,1.6),'tile');z(r(2.8,2.35,5.95,3.95));
  }else if(career==='group_accounting'){
    clear();s('workbench','desk',r(3.15,2.9,6.1,4.15),4.6,4.75,62,mint);
    // Four reporting packages are physically separated on the back wall.
    for(const x of [2.8,3.75,4.7,5.65])f('bookcase',r(x,.55,x+.65,1.3),104,blue);
    z(r(2.55,.3,6.55,1.6),'plank');z(r(2.85,2.6,6.4,4.5));
  }else if(career==='customer_care'){
    clear();s('workbench','console',r(3.1,1.25,4.5,2.4),3.8,3,74,blue);
    f('console',r(5.35,.6,6.45,1.8),74,blue);f('sofa',r(3.4,3.7,5.5,4.4),45,mint);
    z(r(2.8,.35,6.7,2.7));z(r(3.15,3.4,5.8,4.65),'mat');
  }else if(career==='hr_admin'){
    clear();s('workbench','desk',r(3.05,.7,5.2,1.65),4.15,2.25,60,mint);
    f('desk',r(3.65,3.35,4.95,4.05),48,cream);f('bench',r(2.8,3.25,3.15,4.25),35,blue);f('bench',r(5.55,3.25,5.9,4.25),35,blue);f('bookcase',r(5.7,.55,6.4,1.5),110);
    z(r(2.75,.4,6.65,1.9),'plank');z(r(2.55,3,6.15,4.6));
  }else if(career==='secretary'){
    clear();s('workbench','desk',r(3.15,1.25,5.65,2.1),4.4,2.7);
    f('board',r(3,.5,4.9,.85),92,mint);f('sofa',r(3.5,3.65,5.5,4.4),43,blue);f('desk',r(5.9,.65,6.5,1.6),50);
    z(r(2.85,1,5.95,2.4),'plank');z(r(3.2,3.3,5.8,4.7));
  }else if(career==='it_helpdesk'){
    clear();s('shelf','rack',r(.55,1.8,1.5,3.8),2,2.8,122,blue);
    s('workbench','tools',r(3.05,3.25,5.65,4.25),4.4,4.85,77,mint);
    f('rack',r(2.85,.55,4.05,1.45),115,blue);f('console',r(5.1,.55,6.35,1.65),78,cream);
    z(r(2.55,.3,6.65,1.9),'tile');z(r(2.8,2.95,5.95,4.55),'mat');
  }else if(career==='salon'){
    clear();s('workbench','mirror',r(3.05,1.8,4.3,2.85),3.7,3.45,118,0xd5b3a1);
    f('mirror',r(5.35,1.8,6.5,2.85),118,0xd5b3a1);f('sink',r(3,.55,4.4,1.1),60,blue);
    z(r(2.75,.3,4.65,1.4),'tile');z(r(2.8,1.55,6.75,3.15),'stone');
  }else if(career==='pet_care'){
    clear();s('workbench','sink',r(3.05,.7,5.3,1.95),4.2,2.55,60,mint);
    f('desk',r(3.4,3.5,5.3,4.35),38,cream);f('bench',r(5.9,.65,6.45,1.9),38);f('display',r(5.95,3.6,6.4,4.3),56,blue);
    z(r(2.75,.4,5.6,2.25),'tile');z(r(3.15,3.2,6.65,4.6),'mat');
  }else if(career==='repair'){
    clear();s('workbench','tools',r(3.2,3.2,5.95,4.25),4.6,4.85,82);
    refurnish('shelf','tools',125);
    f('tools',r(3,.55,5.3,1.25),125);f('rack',r(5.9,.65,6.5,1.65),87,blue);
    z(r(2.7,.3,6.75,1.9),'plank');z(r(2.95,2.95,6.2,4.55),'stone');
  }else if(career==='nail'){
    clear();s('workbench','desk',r(3.05,2.65,4.6,3.45),3.85,4.05,52,0xd5b3a1);
    f('display',r(2.85,.55,5.2,1.15),100,0xd5b3a1);f('desk',r(5.65,2.65,6.3,3.65),52,cream);f('sink',r(5.9,.55,6.45,1.3),59,blue);
    z(r(2.6,.3,6.7,1.45),'tile');z(r(2.8,2.35,6.55,3.95));
  }else if(career==='homemaker'){
    clear();f('sofa',r(3.15,3.5,5.3,4.35),43,mint);f('washer',r(5.95,.65,6.6,1.75),62,cream);f('desk',r(5.85,3.55,6.35,4.2),34);
    refurnish('shelf','coldcabinet',122,0xe3e3d0);
    z(r(2.75,.3,6.85,2),'tile');z(r(2.9,3.2,6.6,4.65));
  }else if(career==='naucom'){
    clear();s('workbench','stove',r(3.2,.65,5,1.75),4.1,2.35,66,mint);
    refurnish('shelf','coldcabinet',122,0xe3e3d0);
    f('sink',r(5.75,.65,6.5,1.75),62,blue);f('desk',r(3.25,3.4,5.75,4.35),46,cream);f('bench',r(3.2,2.75,5.8,3.05),25);
    z(r(2.9,.35,6.8,2.05),'tile');z(r(2.95,2.5,6.05,4.65),'checker');
  }else if(career==='giupviec'){
    clear();s('shelf','sink',r(.55,2.05,1.5,3.95),1.95,3,63,blue);
    s('workbench','counter',r(3.5,3.45,5.4,4.3),4.4,4.9,60,mint);
    f('washer',r(2.95,.55,4.3,1.75),76,cream);f('shelf',r(5.2,.55,6.4,1.45),93);f('sofa',r(2.85,3.5,3.2,4.3),42,blue);
    z(r(2.65,.3,6.65,2),'tile');z(r(3.25,3.15,5.7,4.6),'plank');
  }else if(career==='homestay'){
    clear();s('workbench','desk',r(3.1,3.4,5.4,4.3),4.25,4.9,61);
    f('bed',r(3,.55,4.9,1.95),43,mint);f('sofa',r(5.85,.65,6.45,1.85),43,0xd1b6a6);
    z(r(2.7,.3,6.7,2.2));z(r(2.8,3.1,5.7,4.6),'plank');
  }else if(career==='grocery'){
    // Two merchandising aisles and a packing surface.
    clear();f('shelf',r(2.9,.55,4.2,1.4),115);f('shelf',r(5.3,.55,6.55,2.15),99);f('crate',r(3.05,2.3,4.15,2.8),42);
    z(r(2.65,.3,6.8,3),'plank');z(r(2.8,3.2,5.75,4.55),'checker');
  }else if(career==='florist'){
    clear();s('workbench','counter',r(3.4,2.75,5.3,3.8),4.4,4.4,58,mint);
    f('planter',r(2.85,.55,4,1.6),35);f('planter',r(4.8,.55,6.4,1.6),35);f('sink',r(5.95,3.4,6.5,4.25),60,blue);
    z(r(2.6,.3,6.65,1.85),'stone');z(r(3.1,2.45,5.6,4.1),'plank');
  }else if(career==='clothing'){
    clear();s('workbench','desk',r(3,3.45,5.2,4.3),4.1,4.9,52,mint);
    f('display',r(3,.55,4.65,1.3),120);f('mirror',r(5.7,.55,6.5,1.8),125,0xc8b1b9);f('bench',r(5.95,3.5,6.4,4.2),32);
    z(r(2.7,.3,4.95,1.6),'plank');z(r(2.7,3.15,6.65,4.6));
  }else if(career==='photobooth'){
    clear();s('workbench','photobooth',r(3.2,.8,5.65,2.2),4.4,2.8,126,0xbab6ce);
    refurnish('shelf','crate',72,0xc5adba);
    f('console',r(5.9,3.4,6.45,4.3),77,blue);f('sofa',r(3.2,3.8,5.25,4.4),40,0xd6b5c2);
    z(r(2.9,.5,5.95,2.5),'checker');z(r(2.9,3.5,6.7,4.65));
  }else if(career==='zpop'){
    clear();s('workbench','desk',r(3.05,3.45,5.5,4.3),4.3,4.9,60,0xc0b4ca);
    s('shelf','bookcase',r(.55,1.8,1.5,4.05),1.95,3,114,0xbea5b4);
    f('display',r(3,.55,6.35,1.45),112,0xb7b6cc);f('display',r(3.35,2.3,4.7,2.75),57,0xd5bcc8);
    z(r(2.75,.3,6.6,3),'plank');z(r(2.8,3.15,5.75,4.6),'checker');
  }else if(career==='pilot'){
    clear();s('workbench','console',r(3,.65,6.25,1.9),4.6,2.5,91,blue);
    f('seatrow',r(3.1,3.5,4.3,4.25),52,blue);f('seatrow',r(5.2,3.5,6.4,4.25),52,blue);
    z(r(2.7,.35,6.55,4.55),'mat',0xb9c9c7);z(r(6.7,3.3,8.55,4.6),'tile');
  }else if(career==='flight_attendant'){
    clear();s('shelf','counter',r(.55,2,1.5,3.8),2,2.9,68,cream);
    s('workbench','counter',r(3,.65,5.8,1.5),4.4,2.1,64,mint);
    for(const y of [2.7,3.8]){f('seatrow',r(3,y,4,y+.65),65,blue);f('seatrow',r(5.4,y,6.4,y+.65),65,blue);}
    z(r(2.75,2.45,6.65,4.7),'carpet',0xbdc9c3);z(r(2.7,.35,6.1,1.8),'tile');
  }else if(career==='oil'){
    clear(true,'stone');s('shelf','routeboard',r(.55,2,1.5,3.9),2,3,115,blue);
    s('workbench','console',r(3.25,3.5,5.5,4.3),4.4,4.9,75,blue);
    s('evidence','console',r(6.9,.55,8.3,1.25),7.6,1.85,89,blue);
    f('pipework',r(2.8,.55,6.25,1.8),136,cream);f('tools',r(5.95,3.6,6.4,4.3),86);
    z(r(2.55,.3,6.55,2.1),'stone');z(r(3,3.2,8.55,4.6),'mat',0xd7c6a0);
  }else if(career==='lighthouse'){
    clear(true,'stone');s('shelf','planter',r(.55,2,1.5,3.9),2,3,32,mint);
    s('workbench','desk',r(3.25,3.4,5.45,4.25),4.4,4.85,62,mint);
    f('beacon',r(3.6,.55,5.4,1.95),190,cream);f('rack',r(5.95,.65,6.5,1.6),69,blue);
    z(r(2.95,.3,5.75,4.55),'stone');z(r(.3,1.75,1.75,4.15),'earth',0xb6ba89);
  }else if(career==='rescue'){
    clear();s('workbench','console',r(3.1,2.4,5.4,3.4),4.25,4,78,blue);
    s('shelf','board',r(.55,2.1,1.4,4.1),1.95,3,111,mint);
    f('routeboard',r(2.9,.55,5.15,1.2),125,mint);f('rack',r(5.9,.55,6.45,1.55),101,blue);f('console',r(5.8,3.65,6.4,4.3),72,blue);
    z(r(2.8,2.1,6.65,4.6),'mat');z(r(2.65,.3,6.7,1.8),'tile');
  }else if(career==='lifeguard'){
    clear(true,'tile');s('workbench','desk',r(5.75,3.5,6.5,4.3),6.1,4.9,63,mint);
    s('shelf','board',r(.55,2,1.5,3.9),2,3,110,blue);
    f('pool',r(2.85,.55,6.35,2.65),12,0x94cbc7);f('seatrow',r(3.2,3.7,4.3,4.35),100,cream);
    z(r(2.6,.3,6.6,2.9),'tile',0xc8e0d3);z(r(2.9,3.4,8.55,4.65),'stone');
  }else if(career==='police'){
    clear();s('shelf','bookcase',r(.55,2.1,1.4,4.1),1.95,3,114);
    s('workbench','desk',r(3,.65,6,1.7),4.5,2.3,61,mint);
    s('evidence','board',r(6.9,.55,8.3,1.25),7.6,1.85,108,blue);
    f('seatrow',r(3.1,3.55,4.35,4.35),51,blue);f('seatrow',r(5.05,3.55,6.3,4.35),51,blue);f('board',r(2.8,.45,3.2,.85),87);
    z(r(2.7,.35,6.3,2),'plank');z(r(2.85,3.3,6.55,4.6),'tile');
  }else if(career==='railway'){
    clear(true,'stone');s('workbench','console',r(3.15,3.4,5.35,4.3),4.25,4.9,75,mint);
    f('signal',r(3,.55,6.3,1.65),132,cream);f('bench',r(5.95,3.55,6.5,4.3),37);
    z(r(2.7,.3,6.6,1.95),'stone');z(r(2.85,3.1,6.75,4.6),'plank');
  }else if(career==='delivery'){
    clear();s('shelf','shelf',r(.55,2.1,1.4,4.1),1.95,3,110);
    s('workbench','counter',r(3.1,3.4,5.5,4.3),4.3,4.9,60,mint);
    for(const x of [2.8,4,5.2])f('crate',r(x,.55,x+.85,1.65),65+(x===4?20:0));
    z(r(2.55,.3,6.3,1.95),'stone');z(r(2.85,3.1,5.8,4.6),'plank');
  }else if(career==='tour_guide'){
    clear(true,'stone');s('workbench','routeboard',r(3,.55,5.65,1.45),4.3,2.05,110,mint);
    s('shelf','display',r(.55,2.1,1.4,4.1),1.95,3,93);
    f('bench',r(3.1,3.75,5.65,4.3),32);f('planter',r(5.95,.65,6.5,1.7),34,mint);
    z(r(2.7,.3,5.95,1.75),'stone');z(r(2.8,3.4,5.95,4.6),'earth');
  }else if(career==='fruit'){
    clear(true,'stone');s('shelf','crate',r(.55,2.1,1.4,4.1),1.95,3,61);
    s('workbench','display',r(3,3.2,5.65,4.25),4.3,4.85,57,mint);
    f('display',r(2.85,.55,4.2,1.4),52,cream);f('display',r(5,.55,6.35,1.4),52,mint);f('crate',r(5.95,3.5,6.45,4.2),37);
    z(r(2.6,.3,6.6,1.7),'plank');z(r(2.7,2.9,5.95,4.55),'mat');
  }else if(career==='garbage'){
    clear(true,'stone');s('shelf','bin',r(.55,2.1,1.4,4.1),1.95,3,62,mint);
    s('workbench','bin',r(3.1,3.1,5.7,4.25),4.4,4.85,68,mint);
    for(const [x,color] of [[2.9,0xa9b692],[4.15,0xd8bc7f],[5.4,0x939891]])f('bin',r(x,.55,x+.9,1.65),84,color);
    z(r(2.65,.3,6.55,1.95),'tile');z(r(2.8,2.8,6,4.55),'stone');
  }else if(career==='drain'){
    clear(true,'stone');s('shelf','tools',r(.55,2.1,1.4,4.1),1.95,3,115);
    s('workbench','tools',r(3.05,.65,5.5,1.65),4.25,2.25,93);
    f('pipework',r(3.2,3.35,5.5,4.25),57,blue);f('sink',r(5.95,.65,6.5,1.75),63,blue);
    z(r(2.75,.35,6.75,1.95),'plank');z(r(2.9,3.05,5.8,4.55),'tile');
  }else if(career==='ice_cream'){
    clear(true,'stone');s('shelf','display',r(.55,2.1,1.4,4.1),1.95,3,91,cream);
    s('workbench','freezer',r(3.15,2.6,5.75,3.85),4.45,4.45,68,mint);
    f('counter',r(3,.55,5.2,1.2),60,cream);f('bench',r(5.95,.6,6.5,1.75),34);
    z(r(2.75,.3,6.75,1.5),'checker');z(r(2.85,2.3,6.05,4.15),'stone');
  }else if(career==='nurse'){
    // Beds share a defined ward behind the desk. The roster stays on the left;
    // the nursing desk and hand-washing sink occupy the separate front area.
    clear(false,'tile');
    s('shelf','board',r(.55,1.8,1.5,4.1),1.95,2.95,110,mint);
    s('workbench','desk',r(3.5,3.4,5.45,4.3),4.4,4.85,57,0xc3dfd7);
    f('bed',r(2.85,.55,4.1,2.3),43,0xeceded);f('bed',r(5,.55,6.25,2.3),43,0xc3dfd7);
    f('sink',r(5.95,3.3,6.45,4.1),62,0xd5e8e1);
    z(r(2.6,.3,6.5,2.55),'tile',0xe1e8d6);z(r(3.2,3.1,6.65,4.55),'tile',0xcce1d7);
  }else if(career==='pharmacy'){
    // Dispensing and stock checks are not bedside care. Keep every legacy
    // approach while replacing the ward's examination bed and washing fixture.
    clear(false,'tile');
    refurnish('shelf','medicine',128,0xbcdad0);
    refurnish('workbench','counter',60,cream);
    refurnish('counter','counter',61,mint);
    f('coldcabinet',r(.55,2.1,1.5,3.9),126,0xe3e8d7);
    f('medicine',r(5.75,.55,6.25,1.35),105,0xbcdad0);
    z(r(2.5,.3,6.5,1.65),'tile',0xe1e8d6,0xc6d6cc);
    z(r(3.2,3.1,5.75,4.6),'tile',0xcce1d7,0xf4eee1);
    z(r(.3,1.85,1.75,4.15),'tile',0xd8e5d5,0xc6d6cc);
  }else if(career==='pagoda'){
    refurnish('shelf','planter',35,mint);
    refurnish('counter','altar',66,0xbd835b);
  }else if(career==='pho'){
    refurnish('counter','stove',69,0xa5bbb4);
  }else if(career==='babysitter'){
    layout.floors[1].footprint=r(2.7,.35,5.4,2.2);
    layout.floors[2].footprint=r(2.8,2.75,5.65,4.6);
  }else if(career==='library'){
    layout.floors[1].footprint=r(2.7,.3,6.85,1.55);
    layout.floors[2].footprint=r(2.8,3.2,8.55,4.65);
  }else if(career==='mother_baby'||career==='pet_shop'||career==='farm'){
    [layout.floors[1],layout.floors[2]]=[layout.floors[2],layout.floors[1]];
  }

  // Name two actual floor zones; no separate decorative hotspot is introduced.
  for(const [index,label] of layout.identity.zones.entries()){
    const zone=layout.floors[index+1];if(zone)zone.label=label;
  }
}
