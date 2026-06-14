import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  const [errorMatch, setErrorMatch] = useState(false); 
  const [confidence, setConfidence] = useState(0); 
  const [mode, setMode] = useState('face');
  const [logs, setLogs] = useState([]);
  const [streamSession, setStreamSession] = useState(null);
  const [showAuthWarning, setShowAuthWarning] = useState(false);

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

  useEffect(() => {
    const fetchUsers = async () => {
      let usersList = [];

      try {
        const response = await fetch('/api/users');
        if (!response.ok) throw new Error(await response.text());
        usersList = await response.json();
        localStorage.setItem('smartface_db_users', JSON.stringify(usersList));
      } catch (error) {
        console.error("Dashboard API Load Error:", error);
        const listStr = localStorage.getItem('smartface_db_users');
        if (listStr) {
          try {
            usersList = JSON.parse(listStr);
          } catch (e) {}
        }
      }

      setUsers(usersList);
      
      if (usersList.length > 0) {
        setIndex(0);
        setUser(usersList[0]);
        setShowAuthWarning(false);
      } else {
        setUser(null);
      }
    };

    fetchUsers();
  }, []);

  useEffect(() => {
    return () => {
      fetch('/api/camera/stop', { method: 'POST' }).catch(() => {});
    };
  }, []);

  const startVerification = async () => {
    if (!user) {
      setShowAuthWarning(true);
      playBeep(330, 'sine', 0.25);
      return;
    }
    
    setShowAuthWarning(false);
    if (active) return;
    setActive(true);
    setPct(0);
    setOk(false);
    setErrorMatch(false);
    setStreamSession(null);
    const scanMode = mode;
    
    if (scanMode === 'qr') {
      setLogs(['[HỆ THỐNG QR] Đang khởi động pdt_QR.py trên FastAPI...']);
    }
    
    setMsg(scanMode === 'face' ? 'Đang khởi động pdt_face.py...' : 'Đang khởi động pdt_QR.py...');
    playBeep(440, 'sine', 0.1);

    try {
      const startUrl = scanMode === 'face'
        ? `/api/face/start/${encodeURIComponent(user.studentId)}?purpose=verify`
        : '/api/qr/start';
      const startResponse = await fetch(startUrl, { method: 'POST' });
      const started = await startResponse.json();
      if (!startResponse.ok) throw new Error(started.detail || 'Không thể mở camera');
      const sessionId = started.sessionId;
      const expectedMode = scanMode === 'face' ? 'face_verify' : 'qr';
      setStreamSession(sessionId);

      const statusUrl = scanMode === 'face' ? '/api/face/status' : '/api/qr/status';
      const startedAt = Date.now();
      let scannerStatus = null;

      while (Date.now() - startedAt < 45000) {
        await new Promise(resolve => setTimeout(resolve, 400));
        const statusResponse = await fetch(statusUrl);
        scannerStatus = await statusResponse.json();
        if (!statusResponse.ok) {
          throw new Error(scannerStatus.detail || 'Không đọc được trạng thái camera');
        }
        if (
          scannerStatus.sessionId !== sessionId ||
          scannerStatus.mode !== expectedMode
        ) {
          throw new Error('Phiên camera đã chuyển sang chế độ khác.');
        }

        const progress = scanMode === 'face'
          ? (scannerStatus.progress || 0)
          : Math.min(95, Math.round((Date.now() - startedAt) / 250));
        setPct(progress);
        setMsg(scannerStatus.message || 'Đang xử lý camera...');
        if (scannerStatus.completed) break;
      }

      if (!scannerStatus?.completed) {
        throw new Error('Hết thời gian chờ camera. Vui lòng thử lại.');
      }

      const verifyUrl = scanMode === 'face'
        ? `/api/face/verify/${encodeURIComponent(user.studentId)}`
        : `/api/qr/verify/${encodeURIComponent(user.studentId)}`;
      const verifyResponse = await fetch(verifyUrl, { method: 'POST' });
      const result = await verifyResponse.json();
      const success = verifyResponse.ok && result.success;

      setPct(100);
      setOk(success);
      setErrorMatch(!success);
      if (scanMode === 'face') {
        setConfidence(result.confidence || 0);
        setMsg(success
          ? `Xác thực thành công! Xin chào ${user.fullName}`
          : 'Xác thực thất bại! Khuôn mặt không khớp.');
      } else {
        setLogs(prev => [
          ...prev,
          success
            ? `[MATCH] QR ${result.qrValue} trùng MSSV ${user.studentId}`
            : `[ERROR] QR ${result.qrValue || '(trống)'} không trùng MSSV ${user.studentId}`
        ]);
        setMsg(success ? 'Mã QR trùng khớp hồ sơ!' : 'Mã QR không trùng hồ sơ.');
      }

      if (success) {
        playBeep(987.77, 'sine', 0.1);
        setTimeout(() => playBeep(1318.51, 'sine', 0.25), 110);
      } else {
        playBeep(220, 'sawtooth', 0.4);
      }
    } catch (error) {
      console.error(error);
      setOk(false);
      setErrorMatch(true);
      setMsg(`Lỗi FastAPI camera: ${error.message}`);
      playBeep(220, 'sawtooth', 0.4);
    } finally {
      setActive(false);
      setStreamSession(null);
      fetch('/api/camera/stop', { method: 'POST' }).catch(() => {});
    }
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
              {active && streamSession !== null && (
                <img
                  id="backend-video"
                  src={`/api/camera/stream?session=${streamSession}`}
                  alt="Camera SmartFace FastAPI"
                  style={{
                    position: 'absolute',
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    zIndex: 2
                  }}
                />
              )}
              
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

              {mode === 'qr' && (
                <>
                  <div className="id-card-guide-box">
                    <div className="id-card-corner corner-tl"></div>
                    <div className="id-card-corner corner-tr"></div>
                    <div className="id-card-corner corner-bl"></div>
                    <div className="id-card-corner corner-br"></div>
                  </div>
                  {active && <div className="id-laser-scanner"></div>}
                  <div className="biometric-hud" style={{ zIndex: 6 }}>
                    <div className="biometric-hud-box">QR DETECTOR: PDT_QR</div>
                    <div className="biometric-hud-box">SCAN: {pct}%</div>
                  </div>
                </>
              )}
              
              <div className="video-placeholder" style={{ zIndex: 1 }}>
                <svg viewBox="0 0 24 24" fill="currentColor" className="camera-icon">
                  <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
                </svg>
                <p>
                  {mode === 'face' ? 'Luồng xử lý Camera Sinh trắc' : 'Luồng quét Mã QR'}
                </p>
                <span className="stream-status">
                  {active 
                    ? (mode === 'face' ? 'Hệ thống đang quét diện mạo...' : 'Máy quét QR đang hoạt động...')
                    : 'Sẵn sàng ghi nhận'}
                </span>
              </div>
            </div>
          </div>
          
          <div className="control-column">
            <div className="control-card">
              {showAuthWarning && (
                <div style={{
                  padding: '12px 16px',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '8px',
                  color: '#ef4444',
                  fontSize: '13px',
                  marginBottom: '16px',
                  textAlign: 'left'
                }}>
                  ⚠️ <strong>Cảnh báo:</strong> Không tìm thấy hồ sơ sinh viên hợp lệ để tiến hành đối sánh. Vui lòng thêm dữ liệu trước khi quét.
                </div>
              )}

              {!ok && !errorMatch && (
                <div className="verify-mode-tabs">
                  <button 
                    type="button"
                    className={`verify-tab-btn ${mode === 'face' ? 'active' : ''}`}
                    disabled={active}
                    onClick={() => {
                      setMode('face');
                      setOk(false);
                      setErrorMatch(false);
                      setPct(0);
                      setLogs([]);
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
                    className={`verify-tab-btn ${mode === 'qr' ? 'active' : ''}`}
                    disabled={active}
                    onClick={() => {
                      setMode('qr');
                      setOk(false);
                      setErrorMatch(false);
                      setPct(0);
                      setLogs([]);
                      setMsg('Sẵn sàng quét QR');
                      playBeep(600, 'sine', 0.08);
                    }}
                  >
                    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5zm6-10.125a1.875 1.875 0 11-3.75 0 1.875 1.875 0 013.75 0zm1.294 6.336a6.721 6.721 0 01-3.17.789 6.721 6.721 0 01-3.168-.789 3.376 3.376 0 016.338 0z" />
                    </svg>
                    Mã QR sinh viên
                  </button>
                </div>
              )}

              {!ok && !errorMatch && (
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
                      Đưa mã QR sinh viên vào camera để pdt_QR.py đọc và đối chiếu với MSSV đã chọn.
                    </div>
                  </>
                )
              )}

              {!ok && !errorMatch && users.length > 0 && (
                <div className="form-group" style={{ marginBottom: '24px' }}>
                  <label htmlFor="select-match-student" style={{ color: '#22d3ee', fontSize: '11px', fontWeight: '800', letterSpacing: '0.1em' }}>
                    Hồ sơ Sinh viên Đối sánh
                  </label>
                  <select
                    id="select-match-student"
                    value={index}
                    disabled={active}
                    onChange={(e) => {
                      const idx = parseInt(e.target.value);
                      setIndex(idx);
                      setUser(users[idx]);
                      setOk(false);
                      setErrorMatch(false);
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
                    }}
                  >
                    {users.map((item, idx) => (
                      <option key={item.studentId || idx} value={idx} style={{ background: '#0f172a', color: '#fff' }}>
                        {item.fullName} ({item.studentId})
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              {!ok && !errorMatch && (
                <button 
                  id="btn-trigger-verify"
                  className={`btn-action-verify ${active ? 'disabled' : ''}`}
                  onClick={startVerification}
                  disabled={active}
                >
                  {active ? 'Đang phân tích...' : (mode === 'face' ? 'Bắt đầu quét khuôn mặt' : 'Bắt đầu quét QR')}
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

              {active && mode === 'qr' && (
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
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', textAlign: 'left' }}>
                    <p style={{ margin: '2px 0' }}><strong>Họ và Tên:</strong> {user?.fullName}</p>
                    <p style={{ margin: '2px 0' }}><strong>MSSV:</strong> {user?.studentId}</p>
                    <p style={{ margin: '2px 0' }}><strong>Khoa:</strong> {user?.faculty || "Công nghệ thông tin"}</p>
                    <p style={{ margin: '2px 0' }}><strong>Ngày sinh:</strong> {user?.dob ? user.dob.split('-').reverse().join('/') : ''}</p>
                    <p style={{ margin: '2px 0' }}><strong>Chỉ số tin cậy:</strong> <span style={{ color: '#00ff7f', fontWeight: 'bold' }}>{confidence.toFixed(1)}% (SIÊU KHỚP)</span></p>
                  </div>

                  <button
                    onClick={() => { setOk(false); setErrorMatch(false); setPct(0); }}
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
                    }}
                  >
                    Thực hiện lại
                  </button>
                </div>
              )}

              {!active && errorMatch && (
                <div id="match-card-fail" className="db-match-card" style={{ borderColor: 'rgba(239, 68, 68, 0.4)', background: 'rgba(15, 23, 42, 0.85)' }}>
                  <h4 style={{ textTransform: 'uppercase', color: '#ef4444', fontSize: '13px', fontWeight: 'bold', marginBottom: '14px', borderBottom: '1px solid rgba(239,68,68,0.2)', paddingBottom: '8px' }}>
                    XÁC THỰC THẤT BẠI ❌
                  </h4>
                  <p style={{ fontSize: '14px', color: '#cbd5e1', marginBottom: '16px' }}>
                    {mode === 'face'
                      ? <>Khuôn mặt hiện tại không khớp với hồ sơ sinh viên <strong>{user?.fullName}</strong> ({user?.studentId}).</>
                      : <>Mã QR vừa quét không trùng với MSSV <strong>{user?.studentId}</strong> của hồ sơ đã chọn.</>}
                  </p>
                  <button
                    onClick={() => { setOk(false); setErrorMatch(false); setPct(0); }}
                    style={{
                      width: '100%', padding: '10px',
                      background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: '8px', color: '#ef4444', fontWeight: 'bold', cursor: 'pointer'
                    }}
                  >
                    Thử lại
                  </button>
                </div>
              )}

              {!active && ok && mode === 'qr' && (
                <div className="document-matched-display">
                  <div className="ocr-details-grid">
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                      <div style={{
                        width: '50px',
                        height: '50px',
                        background: 'rgba(34, 211, 238, 0.1)',
                        border: '1px solid rgba(34, 211, 238, 0.2)',
                        borderRadius: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}>
                        <svg width="24" height="24" fill="currentColor" viewBox="0 0 24 24" style={{ color: '#22d3ee' }}>
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                      </div>
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '3px', textAlign: 'left' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>HỌ VÀ TÊN / FULL NAME</div>
                        <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#ffffff' }}>{user?.fullName}</div>
                      </div>
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '4px', textAlign: 'left' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>MSSV / STUDENT ID</div>
                        <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#e2e8f0', fontFamily: 'monospace' }}>
                          {user?.studentId}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>NGÀY SINH / DATE OF BIRTH</div>
                        <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#e2e8f0' }}>
                          {user?.dob ? user.dob.split('-').reverse().join('/') : ''}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '4px', textAlign: 'left' }}>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>KHOA PHÒNG / REGION</div>
                        <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#cbd5e1' }}>
                          {user?.faculty || 'Khoa Công nghệ thông tin'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>TRẠNG THÁI QR</div>
                        <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#4ade80' }}>
                          ĐÃ ĐỐI CHIẾU ĐÚNG MSSV
                        </div>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => { setOk(false); setErrorMatch(false); setPct(0); }}
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
                    }}
                  >
                    Thực hiện lại
                  </button>
                </div>
              )}
            </div>
          </div>

          <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '12px', color: '#64748b', zIndex: 10 }}>
              © {new Date().getFullYear()} SmartFace ID. Toàn bộ thông tin sinh học và đăng ký được bảo mật theo tiêu chuẩn sở hữu trí tuệ của nhà phát triển.
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
