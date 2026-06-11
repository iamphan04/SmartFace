import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { db, handleFirestoreError, OperationType } from './database';
import { collection, getDocs } from 'firebase/firestore';
import './Dashboard.css';

const Dashboard = () => {
  const navigate = useNavigate();
  const [active, setActive] = useState(false);
  const [pct, setPct] = useState(0);
  const [msg, setMsg] = useState('Sẵn sàng xác thực');
  const [user, setUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [index, setIndex] = useState(0);
  const [ok, setOk] = useState(false);
  const [mode, setMode] = useState('face');
  const docType = 'student_id';
  const [logs, setLogs] = useState([]);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // Play audio synthesizer beeps
  const playBeep = (freq, type, duration) => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      
      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.06, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
      
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      console.warn("AudioContext block", e);
    }
  };

  // Load registered users from multi-user array, synchronized with Firestore
  useEffect(() => {
    const fetchUsers = async () => {
      const listStr = localStorage.getItem('smartface_db_users');
      let usersList = [];
      if (listStr) {
        try {
          const parsed = JSON.parse(listStr);
          if (Array.isArray(parsed) && parsed.length > 0) {
            usersList = parsed;
          }
        } catch (e) {
          console.warn("Could not parse smartface_db_users", e);
        }
      }

      // Fallback if smartface_db_users is empty but smartface_db_user has data
      if (usersList.length === 0) {
        const singleStr = localStorage.getItem('smartface_db_user');
        if (singleStr) {
          try {
            const parsed = JSON.parse(singleStr);
            usersList = [parsed];
            localStorage.setItem('smartface_db_users', JSON.stringify(usersList));
          } catch (e) {}
        }
      }

      // Ultimate fallback to simulated sample data so they always have at least 1-2 students to match
      if (usersList.length === 0) {
        const sample1 = {
          fullName: 'Nguyễn Đức Anh',
          studentId: 'B22DCCN068',
          dob: '2004-10-15',
          faculty: 'Khoa Công nghệ thông tin',
          email: 'ducanh.n@student.edu.vn',
          registeredAt: new Date().toLocaleDateString('vi-VN')
        };
        const sample2 = {
          fullName: 'Trần Thị Mai',
          studentId: 'B22DCCN102',
          dob: '2004-03-22',
          faculty: 'Khoa An toàn thông tin',
          email: 'maitt.b22@student.edu.vn',
          registeredAt: new Date().toLocaleDateString('vi-VN')
        };
        usersList = [sample1, sample2];
        localStorage.setItem('smartface_db_users', JSON.stringify(usersList));
        localStorage.setItem('smartface_db_user', JSON.stringify(sample1));
      }

      // Sync with cloud database
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
        }
      } catch (error) {
        console.error("Dashboard Firestore Load Error:", error);
        try {
          handleFirestoreError(error, OperationType.LIST, 'users');
        } catch (e) {}
      }

      setUsers(usersList);
      
      // Default selected user is either the one in smartface_db_user or first in array
      const activeSingleStr = localStorage.getItem('smartface_db_user');
      if (activeSingleStr) {
        try {
          const activeObj = JSON.parse(activeSingleStr);
          const foundIndex = usersList.findIndex(u => u.studentId === activeObj.studentId);
          if (foundIndex >= 0) {
            setIndex(foundIndex);
            setUser(usersList[foundIndex]);
          } else {
            setIndex(0);
            setUser(usersList[0]);
          }
        } catch (e) {
          setIndex(0);
          setUser(usersList[0]);
        }
      } else {
        setIndex(0);
        setUser(usersList[0]);
      }
    };

    fetchUsers();
  }, []);

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startVerification = async () => {
    if (active) return;
    setActive(true);
    setPct(0);
    setOk(false);
    
    if (mode === 'document') {
      setLogs(['[HỆ THỐNG OCR] Đang phân phối luồng xử lý quét tài liệu...']);
    }
    
    setMsg(mode === 'face' ? 'Đang khởi động kết nối camera...' : 'Đang căn chỉnh camera quét giấy tờ...');
    playBeep(440, 'sine', 0.1);

    // Attempt to access true user camera
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(e => console.log("Video play error:", e));
      }
    } catch (err) {
      console.warn("Could not access physical webcam, falling back to dynamic simulated stream.", err);
    }

    let currentProgress = 0;
    const interval = setInterval(() => {
      currentProgress += 2;
      setPct(currentProgress);

      // Procedural telemetry click beeps
      if (currentProgress % 10 === 0 && currentProgress < 100) {
        playBeep(700 + currentProgress, 'sine', 0.04);
      }

      if (mode === 'face') {
        if (currentProgress === 16) {
          setMsg('Đang tìm kiếm và căn chỉnh khuôn mặt...');
        } else if (currentProgress === 46) {
          setMsg('Đang trích xuất đặc trưng sinh trắc học...');
        } else if (currentProgress === 76) {
          setMsg(user ? `Đang đối chiếu với hồ sơ MSSV: ${user.studentId}...` : 'Đang tìm kiếm dữ liệu lưu trữ khách...');
        }
      } else {
        // Document OCR logs
        if (currentProgress === 10) {
          setLogs(prev => [...prev, `[INFO] Đang dò tìm vật thể và đóng khung biên cạnh Thẻ sinh viên...`]);
          setMsg('Đang tìm biên cạnh tài liệu...');
        } else if (currentProgress === 30) {
          setLogs(prev => [...prev, `[INFO] Đã căn lề tài liệu. Tiến hành phân đoạn ký tự vùng thông tin cá nhân...`]);
        } else if (currentProgress === 52) {
          setLogs(prev => [...prev, `[SUCCESS] Đã bóc tách trường văn bản bằng mạng thần kinh nhân tạo OCR...`]);
          setMsg('Đang giải mã thông tin văn bản...');
        } else if (currentProgress === 72) {
          setLogs(prev => [...prev, `[MATCH] Trùng khớp mã định danh sinh viên: ${user ? user.studentId : 'GUEST_ID'} trong Cơ sở dữ liệu`]);
        } else if (currentProgress === 88) {
          setLogs(prev => [...prev, `[FACE MATCH] Đối tương quan ảnh chân dung Thẻ sinh viên với Gương mặt Live: 98.7% TRÙNG KHỚP`]);
          setMsg('Đang kiểm tra sinh trắc chân dung...');
        }
      }

      if (currentProgress >= 100) {
        clearInterval(interval);
        setOk(true);
        
        if (mode === 'face') {
          setMsg(user ? `Xác thực thành công! Xin chào ${user.fullName}` : 'Xác thực thành công với tài khoản Khách!');
        } else {
          setLogs(prev => [...prev, `[XÁC MINH HOÀN TẤT] HỒ SƠ ĐÃ ĐƯỢC THÔNG QUA AN TOÀN TOÀN DIỆN ●`]);
          setMsg(`Đã đối soát giấy tờ hoàn tất!`);
        }
        
        setActive(false);
        
        // Match chime double beep
        setTimeout(() => playBeep(987.77, 'sine', 0.1), 0);
        setTimeout(() => playBeep(1318.51, 'sine', 0.25), 110);

        // Turn off camera upon completion
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
      }
    }, 50); 
  };

  return (
    <div id="dashboard-root-container" className="dashboard-wrapper">
      <header id="dashboard-header" className="dashboard-header">
        <div className="db-container header-inner">
          <div className="logo" onClick={() => navigate('/')}>
            SmartFace
          </div>
          <button id="btn-dashboard-back" className="btn-back" onClick={() => navigate('/')}>
            Quay lại trang chủ
          </button>
        </div>
      </header>
      
      <main id="dashboard-main-section" className="dashboard-main">
        <div className="db-container main-grid">
          <div className="video-column">
            <div className={`video-frame ${active ? 'active-scan' : ''}`} style={{ position: 'relative' }}>
              <video 
                id="backend-video" 
                ref={videoRef}
                autoPlay 
                playsInline 
                muted
                style={{ 
                  position: 'absolute', 
                  width: '100%', 
                  height: '100%', 
                  objectFit: 'cover', 
                  zIndex: 2, 
                  opacity: active ? 1 : 0,
                  transition: 'opacity 0.4s'
                }}
              />
              
              {active && mode === 'face' && (
                <>
                  <div className="biometric-scanner-grid" style={{ zIndex: 3 }}></div>
                  <div className="biometric-box-overlay" style={{ zIndex: 4 }}></div>
                  <div className="biometric-points-container" style={{ zIndex: 5 }}>
                    <div className="biometric-point" style={{ top: '38%', left: '42%' }} id="bp-le"></div>
                    <span className="biometric-point-label" style={{ top: '35%', left: '44%', zIndex: 5 }}>L_EYE</span>
                    
                    <div className="biometric-point" style={{ top: '38%', left: '58%' }} id="bp-re"></div>
                    <span className="biometric-point-label" style={{ top: '35%', left: '60%', zIndex: 5 }}>R_EYE</span>
                    
                    <div className="biometric-point" style={{ top: '51%', left: '50%' }} id="bp-nt"></div>
                    <span className="biometric-point-label" style={{ top: '51%', left: '52%', zIndex: 5 }}>NOSE_T</span>
                    
                    <div className="biometric-point" style={{ top: '64%', left: '44%' }} id="bp-ml"></div>
                    <div className="biometric-point" style={{ top: '64%', left: '56%' }} id="bp-mr"></div>
                    <span className="biometric-point-label" style={{ top: '66%', left: '47%', zIndex: 5 }}>ORAL_VEC</span>
                    
                    <div className="biometric-point" style={{ top: '75%', left: '50%' }} id="bp-ch"></div>
                    <span className="biometric-point-label" style={{ top: '77%', left: '48%', zIndex: 5 }}>MENTON</span>
                  </div>
                  <div className="biometric-hud" style={{ zIndex: 6 }}>
                    <div className="biometric-hud-box">CONFIDENCE: {(85 + (pct * 0.14)).toFixed(1)}%</div>
                    <div className="biometric-hud-box">SYNC: {pct}%</div>
                  </div>
                  <div className="scan-line" style={{ zIndex: 10 }}></div>
                </>
              )}

              {mode === 'document' && (
                <>
                  <div className="id-card-guide-box">
                    <div className="id-card-corner corner-tl"></div>
                    <div className="id-card-corner corner-tr"></div>
                    <div className="id-card-corner corner-bl"></div>
                    <div className="id-card-corner corner-br"></div>
                  </div>
                  {active && <div className="id-laser-scanner"></div>}
                  <div className="biometric-hud" style={{ zIndex: 6 }}>
                    <div className="biometric-hud-box">OCR REGION: AUTO_ALIGN</div>
                    <div className="biometric-hud-box">SCAN: {pct}%</div>
                  </div>
                </>
              )}
              
              <div className="video-placeholder" style={{ zIndex: 1 }}>
                <svg viewBox="0 0 24 24" fill="currentColor" className="camera-icon">
                  <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
                </svg>
                <p>
                  {mode === 'face' ? 'Luồng xử lý Camera Sinh trắc' : 'Luồng quét Thẻ Cận Cảnh'}
                </p>
                <span className="stream-status">
                  {active 
                    ? (mode === 'face' ? 'Hệ thống đang quét diện mạo...' : 'Máy quét OCR đang hoạt động...') 
                    : 'Sẵn sàng ghi nhận'}
                </span>
              </div>
            </div>
          </div>
          
          <div className="control-column">
            <div className="control-card">
              {!ok && (
                <div className="verify-mode-tabs">
                  <button 
                    type="button"
                    className={`verify-tab-btn ${mode === 'face' ? 'active' : ''}`}
                    onClick={() => {
                      setMode('face');
                      setOk(false);
                      setPct(0);
                      setMsg('Sẵn sàng xác thực');
                      playBeep(600, 'sine', 0.08);
                    }}
                  >
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M18 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM3 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 019.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
                    </svg>
                    Xác thực Gương mặt
                  </button>
                  <button 
                    type="button"
                    className={`verify-tab-btn ${mode === 'document' ? 'active' : ''}`}
                    onClick={() => {
                      setMode('document');
                      setOk(false);
                      setPct(0);
                      setMsg('Sẵn sàng quét giấy tờ');
                      playBeep(600, 'sine', 0.08);
                    }}
                  >
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5zm6-10.125a1.875 1.875 0 11-3.75 0 1.875 1.875 0 013.75 0zm1.294 6.336a6.721 6.721 0 01-3.17.789 6.721 6.721 0 01-3.168-.789 3.376 3.376 0 016.338 0z" />
                    </svg>
                    Giấy tờ tùy thân (OCR)
                  </button>
                </div>
              )}

              {!ok && (
                mode === 'face' ? (
                  <>
                    <h2 className="control-title">Xác thực Sinh trắc</h2>
                    <div className="control-desc">
                      Đối sánh trực tiếp sơ đồ đặc trưng hình thể gương mặt với Cơ sở dữ liệu Sinh viên lưu trữ.
                    </div>
                  </>
                ) : (
                  <>
                    <h2 className="control-title">Đối soát Thẻ sinh viên</h2>
                    <div className="control-desc" style={{ marginBottom: '18px' }}>
                      Đặt mặt trước Thẻ sinh viên hướng về camera để trích xuất ký tự chữ viết tự động bằng máy quét OCR.
                    </div>
                  </>
                )
              )}

              {!ok && users.length > 0 && (
                <div className="form-group" style={{ marginBottom: '24px' }}>
                  <label htmlFor="select-match-student" style={{ color: '#22d3ee', fontSize: '11px', fontWeight: '800', letterSpacing: '0.1em' }}>
                    Hồ sơ Sinh viên Đối sánh
                  </label>
                  <select
                    id="select-match-student"
                    value={index}
                    onChange={(e) => {
                      const idx = parseInt(e.target.value);
                      setIndex(idx);
                      setUser(users[idx]);
                      setOk(false);
                      playBeep(520, 'sine', 0.08);
                    }}
                    style={{
                      width: '100%',
                      background: 'rgba(15, 23, 42, 0.65)',
                      border: '1px solid rgba(6, 182, 212, 0.25)',
                      borderRadius: '12px',
                      padding: '12px 14px',
                      color: '#ffffff',
                      fontSize: '14px',
                      cursor: 'pointer',
                      outline: 'none',
                      transition: 'border-color 0.2s'
                    }}
                  >
                    {users.map((item, idx) => (
                      <option key={item.studentId} value={idx} style={{ background: '#0f172a', color: '#fff' }}>
                        {item.fullName} ({item.studentId}) - {item.faculty || 'Khoa CNTT'}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              {!ok && (
                <button 
                  id="btn-trigger-verify"
                  className={`btn-action-verify ${active ? 'disabled' : ''}`}
                  onClick={startVerification}
                  disabled={active}
                  style={ok ? { backgroundColor: '#00cc66', borderColor: '#00cc66' } : {}}
                >
                  {active ? 'Đang phân tích...' : (mode === 'face' ? 'Bắt đầu quét khuôn mặt' : 'Bắt đầu quét Giấy tờ')}
                </button>
              )}

              {active && (
                <div className="progress-section">
                  <div className="progress-header">
                    <span className="status-label">{msg}</span>
                    <span className="percent-label">{pct}%</span>
                  </div>
                  <div className="progress-bar-track">
                    <div className="progress-bar-fill" style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              )}

              {active && mode === 'document' && (
                <div className="ocr-terminal">
                  {logs.map((log, idx) => {
                    let logClass = 'info';
                    if (log.includes('[SUCCESS]') || log.includes('[MATCH]') || log.includes('[FACE MATCH]')) {
                      logClass = 'success';
                    } else if (log.includes('[WARNING]') || log.includes('[ERROR]')) {
                      logClass = 'warning';
                    }
                    return (
                      <div key={idx} className={`ocr-log-line ${logClass}`}>
                        <span>&gt;</span>
                        <span>{log}</span>
                      </div>
                    );
                  })}
                </div>
              )}

              {!active && ok && mode === 'face' && (
                <div id="match-card" className="db-match-card">
                  <h4 style={{ textTransform: 'uppercase', color: '#22d3ee', fontSize: '13px', fontWeight: 'bold', marginBottom: '14px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '8px' }}>
                    KẾT QUẢ ĐỐI CHIẾU THÀNH CÔNG
                  </h4>
                  {user ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', textAlign: 'left' }}>
                      <p style={{ margin: '2px 0' }}><strong>Họ và Tên:</strong> {user.fullName}</p>
                      <p style={{ margin: '2px 0' }}><strong>MSSV:</strong> {user.studentId}</p>
                      <p style={{ margin: '2px 0' }}><strong>Khoa:</strong> {user.faculty || "Công nghệ thông tin"}</p>
                      <p style={{ margin: '2px 0' }}><strong>Ngày sinh:</strong> {user.dob.split('-').reverse().join('/')}</p>
                      <p style={{ margin: '2px 0' }}><strong>Chỉ số tin cậy:</strong> <span style={{ color: '#00ff7f', fontWeight: 'bold' }}>98.4% (SIÊU KHỚP)</span></p>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', textAlign: 'left' }}>
                      <p style={{ margin: '2px 0' }}><strong>Họ và Tên:</strong> KHÁCH THỦ NGHIỆM</p>
                      <p style={{ margin: '2px 0' }}><strong>MSSV:</strong> GUEST_MODE_ACTIVE</p>
                      <p style={{ margin: '2px 0' }}><strong>Trạng thái:</strong> Thành công (Chế độ mô phỏng tự do)</p>
                      <p style={{ margin: '2px 0' }}><strong>Chỉ số tin cậy:</strong> <span style={{ color: '#00ff7f', fontWeight: 'bold' }}>95.0% (MÔ PHỎNG KHỚP)</span></p>
                    </div>
                  )}

                  <button
                    onClick={() => { setOk(false); setPct(0); }}
                    style={{
                      width: '100%',
                      marginTop: '18px',
                      padding: '10px',
                      background: 'rgba(6, 182, 212, 0.15)',
                      border: '1px solid rgba(6, 182, 212, 0.3)',
                      borderRadius: '8px',
                      color: '#22d3ee',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      fontSize: '12px',
                      transition: 'all 0.2s'
                    }}
                  >
                    Thực hiện lại
                  </button>
                </div>
              )}

              {!active && ok && mode === 'document' && (
                <div className="document-matched-display">
                  <div className="ocr-details-grid">
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                      <div style={{
                        width: '50px',
                        height: '60px',
                        background: 'rgba(34, 211, 238, 0.1)',
                        border: '1px solid rgba(34, 211, 238, 0.2)',
                        borderRadius: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        <svg width="24" height="24" fill="currentColor" viewBox="0 0 24 24" style={{ color: '#22d3ee' }}>
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                      </div>
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '3px', textAlign: 'left' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>HỌ VÀ TÊN / FULL NAME</div>
                        <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#ffffff' }}>{user ? user.fullName : 'KHÁCH THỦ NGHIỆM'}</div>
                      </div>
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '4px', textAlign: 'left' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>MSSV / STUDENT ID</div>
                        <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#e2e8f0', fontFamily: 'monospace' }}>
                          {user ? user.studentId : 'GUEST_9999'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>NGÀY SINH / DATE OF BIRTH</div>
                        <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#e2e8f0' }}>
                          {user ? user.dob.split('-').reverse().join('/') : '10/10/2004'}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '4px', textAlign: 'left' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>KHOA PHÒNG / REGION</div>
                        <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#cbd5e1' }}>
                          {user ? (user.faculty || 'Công nghệ thông tin') : 'Khoa CNTT'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>ĐỘ CHÍNH XÁC KHỚP</div>
                        <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#4ade80' }}>
                          98.7% (ĐỒNG NHẤT KHÍT)
                        </div>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => { setOk(false); setPct(0); }}
                    style={{
                      width: '100%',
                      marginTop: '18px',
                      padding: '10px',
                      background: 'rgba(6, 182, 212, 0.15)',
                      border: '1px solid rgba(6, 182, 212, 0.3)',
                      borderRadius: '8px',
                      color: '#22d3ee',
                      fontWeight: 'bold',
                      cursor: 'pointer',
                      fontSize: '12px',
                      transition: 'all 0.2s'
                    }}
                  >
                    Thực hiện lại
                  </button>
                </div>
              )}
            </div>
          </div>

          <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '12px', color: '#64748b', zIndex: 10 }}>
            © {new Date().getFullYear()} SmartFace ID. Toàn bộ tính năng nhận diện sinh học nâng cao và dữ liệu đối quang đều bảo lưu bản quyền tác giả.
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
