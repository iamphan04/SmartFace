import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { db, handleFirestoreError, OperationType } from './database';
import { collection, getDocs } from 'firebase/firestore';
import './App.css';

const Landing = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [profile, setProfile] = useState(false);
  
  const [modal, setModal] = useState(false); 
  
  const [loginModal, setLoginModal] = useState(false); 
  const [mssvInput, setMssvInput] = useState('');
  const [loginError, setLoginError] = useState('');

  const loadUsersFromStorage = async () => {
    const listStr = localStorage.getItem('smartface_db_users');
    let usersList = [];
    if (listStr) {
      try {
        const parsed = JSON.parse(listStr);
        if (Array.isArray(parsed)) {
          usersList = parsed;
        }
      } catch (e) {}
    }

    const savedUser = localStorage.getItem('smartface_db_user');
    let activeUser = null;
    if (savedUser) {
      try {
        activeUser = JSON.parse(savedUser);
      } catch (e) {}
    }

    if (activeUser && usersList.length === 0) {
      usersList = [activeUser];
      localStorage.setItem('smartface_db_users', JSON.stringify(usersList));
    }

    try {
      const snap = await getDocs(collection(db, 'users'));
      const fbUsers = [];
      snap.forEach((docSnap) => {
        fbUsers.push(docSnap.data());
      });
      
      if (fbUsers.length > 0) {
        const merged = [...fbUsers];
        usersList.forEach((localU) => {
          if (!merged.some(u => u.studentId === localU.studentId)) {
            merged.push(localU);
          }
        });
        usersList = merged;
        localStorage.setItem('smartface_db_users', JSON.stringify(usersList));
        
        if (!activeUser && fbUsers.length > 0) {
          activeUser = fbUsers[0];
          localStorage.setItem('smartface_db_user', JSON.stringify(activeUser));
        }
      }
    } catch (error) {
      console.error("Firestore Load Error:", error);
      try {
        handleFirestoreError(error, OperationType.LIST, 'users');
      } catch (e) {}
    }

    setUsers(usersList);
    setUser(activeUser);
  };

  useEffect(() => {
    loadUsersFromStorage();
  }, [profile]);

  useEffect(() => {
    const canvas = document.getElementById('cyber-grid-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const pCount = 65;
    const pts = [];

    for (let i = 0; i < pCount; i++) {
      pts.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 2 + 1,
        alpha: Math.random() * 0.5 + 0.15,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      ctx.strokeStyle = 'rgba(6, 182, 212, 0.04)';
      ctx.lineWidth = 1;
      const step = 60;
      for (let x = 0; x < width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      for (let i = 0; i < pCount; i++) {
        const p = pts[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        ctx.fillStyle = `rgba(34, 211, 238, ${p.alpha})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fill();

        if (i % 6 === 0) {
          ctx.strokeStyle = `rgba(34, 211, 238, ${p.alpha * 0.35})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(p.x - 4, p.y);
          ctx.lineTo(p.x + 4, p.y);
          ctx.moveTo(p.x, p.y - 4);
          ctx.lineTo(p.x, p.y + 4);
          ctx.stroke();
        }

        for (let j = i + 1; j < pCount; j++) {
          const p2 = pts[j];
          const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
          if (dist < 130) {
            const opacity = (1 - dist / 130) * 0.14;
            ctx.strokeStyle = `rgba(6, 182, 212, ${opacity})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animId);
    };
  }, []);

  const handleRegisteredLoginClick = () => {
    setLoginError('');
    setMssvInput('');
    setLoginModal(true); 
  }
  const handleLoginSubmit = async (e) => {
    if (e) e.preventDefault();
    const inputClean = mssvInput.trim().toUpperCase();

    if (!inputClean) {
      setLoginError('Vui lòng nhập MSSV!');
      return;
    }

    setLoginError('');

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/users/${inputClean}`);      
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error('Mã số sinh viên (MSSV) này chưa được đăng ký trong hệ thống SQLite.');
        } else {
          throw new Error('Không thể kết nối hoặc truy xuất dữ liệu từ Python Server.');
        }
      }

      const dbUser = await res.json();

      const finalUser = {
        ...dbUser,
        frontCard: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="180" viewBox="0 0 300 180" style="background:%231e293b;border-radius:8px;font-family:sans-serif;"><rect width="298" height="178" x="1" y="1" rx="8" fill="%230f172a" stroke="%2338bdf8" stroke-width="2"/><circle cx="50" cy="90" r="24" fill="%2338bdf8" opacity="0.2"/><circle cx="50" cy="90" r="16" fill="%233a82f6"/><text x="110" y="55" fill="%2338bdf8" font-size="14" font-weight="bold">THẺ SINH VIÊN</text><text x="110" y="80" fill="%23ffffff" font-size="12">Họ tên:</text><text x="110" y="100" fill="%23ffffff" font-size="12">MSSV: </text><text x="110" y="120" fill="%23cbd5e1" font-size="10">Khoa: </text><text x="110" y="140" fill="%2322c55e" font-size="9" font-weight="bold">● SMARTFACE VERIFIED</text></svg>',
        backCard: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="180" viewBox="0 0 300 180" style="background:%231e293b;border-radius:8px;font-family:sans-serif;"><rect width="298" height="178" x="1" y="1" rx="8" fill="%230f172a" stroke="%2338bdf8" stroke-width="2"/><text x="30" y="40" fill="%2394a3b8" font-size="9">CHỮ KÝ SINH VIÊN / STUDENT SIGNATURE</text><line x1="30" y1="70" x2="160" y2="70" stroke="%23ff3366" stroke-width="1.5" stroke-dasharray="2 2"/><text x="30" y="110" fill="%2394a3b8" font-size="9">ĐIỀU KIỆN SỬ DỤNG</text><text x="30" y="130" fill="%23cbd5e1" font-size="8">Thẻ này chỉ dùng trong khuôn viên nhà trường.</text><text x="30" y="145" fill="%23cbd5e1" font-size="8">Mất thẻ vui lòng báo cho phòng công tác SV.</text></svg>'
      };

      localStorage.setItem('smartface_db_user', JSON.stringify(finalUser));
      setUser(finalUser);

      const listStr = localStorage.getItem('smartface_db_users');
      let usersList = [];
      if (listStr) {
        try { usersList = JSON.parse(listStr); } catch (e) {}
      }
      usersList = usersList.filter(u => u.studentId !== finalUser.studentId);
      usersList.push(finalUser);
      localStorage.setItem('smartface_db_users', JSON.stringify(usersList));

      setLoginModal(false);
      setMssvInput('');

      navigate('/Dashboard');

    } catch (err) {
      setLoginError(err.message);
    }
  };

  const features = [
    {
      id: 1,
      text: "Đơn giản hóa quy trình xác thực",
      icon: (
        <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25M19.5 5.25a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25m15 0V13.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 13.5V5.25" />
        </svg>
      )
    },
    {
      id: 2,
      text: "Bảo mật & Độ chính xác cao",
      icon: (
        <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0110 21a3.745 3.745 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.746 3.746 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0114 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
        </svg>
      )
    },
    {
      id: 3,
      text: "Xử lý tức thì bằng AI",
      icon: (
        <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
      )
    },
    {
      id: 4,
      text: "Mang lại tính công bằng cao",
      icon: (
        <svg fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v17.25m0-17.25a9 9 0 019 9M12 3a9 9 0 00-9 9m9 5.25a9 9 0 01-9-9m9 9a9 9 0 009-9M5.625 7.5h12.75M5.625 12h12.75m-12.75 4.5h12.75" />
        </svg>
      )
    }
  ];

  return (
    <div id="landing-id-container" className="landing-wrapper">
      <video autoPlay loop muted playsInline className="background-video">
        <source src="/intro.mp4" type="video/mp4" />
        <source src="https://assets.mixkit.co/videos/preview/mixkit-blue-and-purple-cosmic-particles-background-31362-large.mp4" type="video/mp4" />
      </video>
      <canvas 
        id="cyber-grid-canvas" 
        style={{ 
          position: 'fixed', 
          top: 0, 
          left: 0, 
          width: '100vw', 
          height: '100vh', 
          zIndex: -1, 
          pointerEvents: 'none', 
          opacity: 0.8 
        }} 
      />

      <header id="landing-header" className="header">
        <div className="container header-container">
          <div className="header-left">
            <a href="/" className="logo">SmartFace</a>
          </div>
          <div className="header-right" style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          </div>
        </div>
      </header>

      <main id="landing-main-section" className="hero-section">
        <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: '30px', width: '100%', zIndex: 10 }}>
          
          <div className="hero-left" style={{ textAlign: 'center' }}>
            <h1 id="landing-title">
              XÁC THỰC THÔNG MINH <br/> <span className="gradient-title-accent">SMARTFACE</span>
            </h1>
            <p id="landing-subtitle" style={{ color: '#cbd5e1', fontSize: '18px', maxWidth: '700px', margin: '0 auto 30px auto', textShadow: '0 1px 3px rgba(0,0,0,0.8)' }}>
              Công nghệ nhận diện khuôn mặt kết hợp đối sánh dữ liệu thẻ sinh viên trực quan.
            </p>

            <div id="auth-choice-box" className="auth-choice-box" style={{ maxWidth: '480px', margin: '0 auto', background: 'rgba(15, 23, 42, 0.75)', border: '1px solid rgba(6, 182, 212, 0.25)', padding: '20px', borderRadius: '16px' }}>
              {user ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div style={{ fontSize: '13px', lineHeight: '1.6', background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.04)', textAlign: 'left' }}>
                    <p style={{ margin: '4px 0' }}><strong>Họ và tên:</strong> {user.fullName}</p>
                    <p style={{ margin: '4px 0' }}><strong>MSSV:</strong> {user.studentId}</p>
                    <p style={{ margin: '4px 0' }}><strong>Ngày sinh:</strong> {user.dob ? user.dob.split('-').reverse().join('/') : "N/A"}</p>
                    <p style={{ margin: '4px 0' }}><strong>Khoa:</strong> {user.faculty || "Công nghệ thông tin"}</p>
                    <p style={{ margin: '4px 0' }}><strong>Email:</strong> {user.email || "N/A"}</p>
                    <p style={{ margin: '4px 0' }}><strong>Ngày đăng ký:</strong> {user.registeredAt}</p>
                  </div>
                  
                  <div className="profile-images" style={{ display: 'flex', gap: '10px' }}>
                    <div className="img-thumbnail-wrap" style={{ flex: 1, textAlign: 'center' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Mặt trước thẻ</span>
                      {user.frontCard ? (
                        <img src={user.frontCard} alt="Mặt trước" style={{ width: '100%', height: '80px', objectFit: 'cover', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.1)' }} />
                      ) : (
                        <div className="no-img" style={{ fontSize: '11px', padding: '10px', background: '#000', borderRadius: '4px' }}>Không có</div>
                      )}
                    </div>
                    <div className="img-thumbnail-wrap" style={{ flex: 1, textAlign: 'center' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Mặt sau thẻ</span>
                      {user.backCard ? (
                        <img src={user.backCard} alt="Mặt sau" style={{ width: '100%', height: '80px', objectFit: 'cover', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.1)' }} />
                      ) : (
                        <div className="no-img" style={{ fontSize: '11px', padding: '10px', background: '#000', borderRadius: '4px' }}>Không có</div>
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '10px' }}>
                    <button 
                      id="btn-active-scan"
                      className="btn-dangnhap" 
                      onClick={() => navigate('/Dashboard')}
                      style={{ width: '100%', margin: 0 }}
                    >
                      Bắt đầu quét khuôn mặt để đăng nhập
                    </button>
                    <button 
                      id="btn-change-account"
                      className="btn-dangnhap" 
                      onClick={() => {
                        localStorage.removeItem('smartface_db_user');
                        setUser(null);
                      }}
                      style={{ 
                        width: '100%', 
                        margin: 0,
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#94a3b8'
                      }}
                    >
                      Đăng ký tài khoản khác / Quay lại
                    </button>
                  </div>
                </div>
              ) : (
                <div id="unregistered-box" className="unregistered-box" style={{ width: '100%', textAlign: 'center' }}>
                  <p style={{ fontSize: '15px', color: '#cbd5e1', marginBottom: '20px' }}>
                    Bạn chưa có tài khoản trong hệ thống? Vui lòng tiến hành đăng ký!
                  </p>
                  <div className="btn-actions-row">
                    <button 
                      id="btn-navigate-register"
                      className="btn-dangnhap" 
                      onClick={() => navigate('/register')}
                    >
                      Đăng ký 
                    </button>
                    
                    <button 
                      id="btn-navigate-login-registered"
                      className="btn-dangnhap" 
                      onClick={handleRegisteredLoginClick}
                    >
                      Đăng nhập tài khoản đã đăng ký
                    </button>
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      </main>

      {/* MODAL 1: CẢNH BÁO CHƯA ĐĂNG KÝ (GIỮ NGUYÊN) */}
      {modal && (
        <div 
          id="no-account-modal" 
          className="modal-overlay" 
          onClick={() => setModal(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(5, 8, 16, 0.85)',
            backdropFilter: 'blur(12px)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px'
          }}
        >
          <div 
            className="modal-content" 
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              boxShadow: '0 0 30px rgba(239, 68, 68, 0.15)',
              borderRadius: '24px',
              padding: '32px',
              maxWidth: '500px',
              width: '100%',
              textAlign: 'center'
            }}
          >
            <div style={{
              width: '64px',
              height: '64px',
              background: 'rgba(239, 68, 68, 0.1)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ef4444',
              margin: '0 auto 20px auto',
              border: '1px solid rgba(239, 68, 68, 0.2)'
            }}>
              <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>

            <h3 style={{ fontSize: '20px', fontWeight: '800', color: '#ffffff', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Yêu cầu đăng ký tài khoản
            </h3>
            
            <p style={{ color: '#cbd5e1', fontSize: '14px', lineHeight: '1.6', marginBottom: '24px' }}>
              Hệ thống chưa ghi nhận bất kỳ dữ liệu định danh sinh viên nào từ phía bạn. Vui lòng tiến hành đăng ký tài khoản!
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                id="btn-modal-install"
                onClick={() => {
                  setModal(false);
                  navigate('/register');
                }}
                style={{
                  background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
                  color: '#ffffff',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  boxShadow: '0 4px 15px rgba(6, 182, 212, 0.25)',
                  transition: 'all 0.2s ease',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}
              >
                Đăng ký tài khoản mới
              </button>
              <button
                id="btn-modal-cancel"
                onClick={() => setModal(false)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: '#e2e8f0',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  padding: '12px 24px',
                  borderRadius: '12px',
                  fontSize: '13px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                Hủy bỏ
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: ĐĂNG NHẬP BẰNG MSSV (MỚI THÊM) */}
      {loginModal && (
        <div 
          id="login-account-modal" 
          className="modal-overlay" 
          onClick={() => setLoginModal(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(5, 8, 16, 0.85)',
            backdropFilter: 'blur(12px)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px'
          }}
        >
          <div 
            className="modal-content" 
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              boxShadow: '0 0 30px rgba(6, 182, 212, 0.15)',
              borderRadius: '24px',
              padding: '32px',
              maxWidth: '450px',
              width: '100%',
              textAlign: 'center'
            }}
          >
            <div style={{
              width: '64px',
              height: '64px',
              background: 'rgba(6, 182, 212, 0.1)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#06b6d4',
              margin: '0 auto 20px auto',
              border: '1px solid rgba(6, 182, 212, 0.2)'
            }}>
              <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
              </svg>
            </div>

            <h3 style={{ fontSize: '18px', fontWeight: '800', color: '#ffffff', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Xác thực mã sinh viên
            </h3>
            
            <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: '1.5', marginBottom: '20px' }}>
              Vui lòng nhập Mã số sinh viên (MSSV) của bạn để kiểm tra tính hợp lệ trên hệ thống.
            </p>

            <form onSubmit={handleLoginSubmit} style={{ marginBottom: '20px' }}>
              <input
                type="text"
                value={mssvInput}
                onChange={(e) => setMssvInput(e.target.value)}
                placeholder="Ví dụ: B22DCCN068"
                style={{
                  width: '100%',
                  padding: '14px 16px',
                  background: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid rgba(6, 182, 212, 0.3)',
                  borderRadius: '12px',
                  color: '#ffffff',
                  fontSize: '14px',
                  fontWeight: '600',
                  outline: 'none',
                  textAlign: 'center',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  boxSizing: 'border-box',
                  marginBottom: '10px'
                }}
              />
              {loginError && (
                <div style={{ color: '#ef4444', fontSize: '12px', fontWeight: '600', textAlign: 'center', marginTop: '6px' }}>
                  ❌ {loginError}
                </div>
              )}
            </form>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                type="button"
                onClick={handleLoginSubmit}
                style={{
                  background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
                  color: '#ffffff',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  boxShadow: '0 4px 15px rgba(6, 182, 212, 0.25)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}
              >
                Xác thực & Đi tới quét
              </button>
              
              <button
                type="button"
                onClick={() => setLoginModal(false)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: '#e2e8f0',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  padding: '12px 24px',
                  borderRadius: '12px',
                  fontSize: '13px',
                  fontWeight: '700',
                  cursor: 'pointer'
                }}
              >
                Hủy bỏ
              </button>
            </div>
          </div>
        </div>
      )}

      <section id="features-section" className="features-section" style={{ zIndex: 10 }}>
        <div className="container features-grid">
          {features.map((item) => (
            <div key={item.id} className="feature-item">
              <div className="icon-box">
                {item.icon}
              </div>
              <div className="feature-text">
                {item.text}
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer id="landing-footer" style={{ borderTop: '1px solid rgba(255,255,255,0.05)', padding: '30px 20px', textAlign: 'center', zIndex: 10, background: 'rgba(5, 5, 10, 0.4)', marginTop: '40px' }}>
        <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0, fontWeight: 500 }}>
            © {new Date().getFullYear()} SmartFace ID. Toàn bộ thông tin sinh học và đăng ký được bảo mật theo tiêu chuẩn sở hữu trí tuệ của nhà phát triển.
        </p>
      </footer>
    </div>
  );
};

export default Landing; 