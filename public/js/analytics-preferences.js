/** Privacy-page controls. No third-party scripts run on this page. */
for(const button of document.querySelectorAll('[data-analytics-choice]'))button.addEventListener('click',()=>{
  const status=document.getElementById('analytics-status');
  try{
    const value=button.dataset.analyticsChoice;
    localStorage.setItem('mnl.analytics',value);
    status.textContent=value==='yes'?'Đã cho phép thống kê / Statistics allowed.':'Đã tắt thống kê / Statistics disabled.';
  }catch{status.textContent='Trình duyệt không cho lưu lựa chọn / Browser storage is unavailable.';}
});
