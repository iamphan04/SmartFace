import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Landing from './Landing'; 
import Register from './Register';
import Dashboard from './Dashboard'; 



function App() {
    return (
    <Router>  
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/register" element={<Register />} />
        <Route path="/Dashboard" element={<Dashboard />} />
      </Routes>
    </Router>
  );
  return (
    <div className="relative min-h-screen w-full overflow-hidden flex flex-col items-center justify-between text-white font-sans">
      
     {/* Khung chứa các nút */}
<div className="w-full max-w-3xl bg-slate-950/40 backdrop-blur-md border border-slate-800 rounded-2xl p-8">
  <p className="text-gray-300 text-sm mb-6 text-center">
    Bạn chưa có tài khoản trong hệ thống? Vui lòng đăng nhập trước<br />
    hoặc sử dụng mẫu tài khoản để đăng nhập.
  </p>

  {/* Grid chia 3 cột bằng nhau */}
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
    
    {/* Nút 1 */}
    <button className="w-full h-24 flex items-center justify-center text-center border border-sky-500/50 rounded-xl hover:bg-sky-500/20 active:scale-95 transition-all duration-300 text-sm font-semibold px-4">
      Đăng ký tài khoản mới
    </button>

    {/* Nút 2 */}
    <button className="w-full h-24 flex items-center justify-center text-center border border-sky-500/50 rounded-xl hover:bg-sky-500/20 active:scale-95 transition-all duration-300 text-sm font-semibold px-4">
      Đăng nhập tài khoản đã đăng ký
    </button>

    {/* Nút 3 */}
    <button className="w-full h-24 flex items-center justify-center text-center border border-purple-500/50 rounded-xl hover:bg-purple-500/20 active:scale-95 transition-all duration-300 text-sm font-semibold px-4">
      Thử nghiệm Đăng nhập<br />(Khách hàng)
    </button>

  </div>
</div>
    </div>
  );
}

export default App;
