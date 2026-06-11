import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { db, handleFirestoreError, OperationType } from './database';
import { doc, setDoc } from 'firebase/firestore';
import './Dashboard.css';

const Register = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  
  const [form, setForm] = useState({
    fullName: '',
    studentId: '',
    dob: '',
    faculty: '',
    email: ''
  });

  const [front, setFront] = useState(null);
  const [back, setBack] = useState(null);

  const [rate, setRate] = useState(0);
  const [scanning, setScanning] = useState(false);
  const [status, setStatus] = useState('Sẵn sàng quét khuôn mặt');
  const [done, setDone] = useState(false);

  const [capturedFaces, setCapturedFaces] = useState({
    front: null,
    left: null,
    right: null
  });

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e, side) => {
    const files = e.target.files;
    if (files && files[0]) {
      const file = files[0];
      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === 'string') {
          if (side === 'front') setFront(reader.result);
          if (side === 'back') setBack(reader.result);
        }
      };
      reader.readAsDataURL(file);
    }
  };

  useEffect(() => {
    if (step === 3) {
      navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
        .then(stream => {
          streamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
          }
        })
        .catch(err => {
          console.error("Lỗi truy cập camera: ", err);
          setStatus("Không thể truy cập camera. Vui lòng cấp quyền.");
        });
    }

    return () => {
      stopCamera();
    };
  }, [step]);

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
  };

  const captureFrame = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      if (context) {
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        return canvas.toDataURL('image/jpeg', 0.95);
      }
    }
    return null;
  };

  const startFaceScan = () => {
    if (scanning) return;
    setScanning(true);
    setRate(0);
    setStatus('Đang khởi động camera quét...');

    const tempFaces = { front: null, left: null, right: null };
    let progress = 0;

    const interval = setInterval(() => {
      progress += 2;
      setRate(progress);

      if (progress === 20) {
        setStatus('Vui lòng nhìn thẳng vào camera...');
        const img = captureFrame();
        if (img) tempFaces.front = img;
      } else if (progress === 50) {
        setStatus('Vui lòng quay nhẹ mặt sang trái...');
        const img = captureFrame();
        if (img) tempFaces.left = img;
      } else if (progress === 80) {
        setStatus('Vui lòng quay nhẹ mặt sang phải...');
        const img = captureFrame();
        if (img) tempFaces.right = img;
      } else if (progress === 90) {
        setStatus('Đang tối ưu hóa sơ đồ đặc trưng khuôn mặt...');
      } else if (progress >= 100) {
        clearInterval(interval);
        setStatus('Thu thập dữ liệu khuôn mặt hoàn tất!');
        setScanning(false);
        setDone(true);
        setCapturedFaces(tempFaces);
        stopCamera();
      }
    }, 80); 
  };

  const handleRegisterSubmit = async () => {
    const finalFront = capturedFaces.front || front; 
    const finalLeft = capturedFaces.left || finalFront;
    const finalRight = capturedFaces.right || finalFront;

    const userData = {
      ...form,
      frontCard: front,
      backCard: back,
      faceModel: "face_signature_vector_simulated",
      registeredAt: new Date().toLocaleDateString('vi-VN')
    };
    
    localStorage.setItem('smartface_db_user', JSON.stringify(userData));
    const existingUsersStr = localStorage.getItem('smartface_db_users');
    let usersList = [];
    if (existingUsersStr) {
      try {
        usersList = JSON.parse(existingUsersStr);
        if (!Array.isArray(usersList)) usersList = [];
      } catch (e) { usersList = []; }
    }
    usersList = usersList.filter((u) => u.studentId !== userData.studentId);
    usersList.push(userData);
    localStorage.setItem('smartface_db_users', JSON.stringify(usersList));

    try {
      await setDoc(doc(db, 'users', userData.studentId), userData);
    } catch (error) {
      try { handleFirestoreError(error, OperationType.WRITE, `users/${userData.studentId}`); } catch (e) {}
    }

    try {
        const res = await fetch("http://127.0.0.1:8000/api/register", 
        {        
          
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fullName:       userData.fullName,
          studentId:      userData.studentId,
          dob:            userData.dob,
          faculty:        userData.faculty,
          email:          userData.email,
          registeredAt:   userData.registeredAt,
          face_front_b64: finalFront,
          face_left_b64:  finalLeft,
          face_right_b64: finalRight
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      console.log("✅ Đã lưu thành công vào SQLite qua Python backend");
    } catch (err) {
      console.error("❌ Lỗi gửi dữ liệu về Python backend:", err.message);
      alert("Đăng ký hoàn tất trên Cloud nhưng lỗi lưu trữ SQLite nội bộ: " + err.message);
    }

    setStep(4);
    setTimeout(() => navigate('/'), 2500);
  };

  return (
    <div id="register-root-container" className="dashboard-wrapper">
      <header id="register-header" className="dashboard-header">
        <div className="db-container header-inner">
          <div className="logo" onClick={() => navigate('/')}>SmartFace</div>
          <button id="btn-cancel-register" className="btn-back" onClick={() => navigate('/')}>Hủy đăng ký</button>
        </div>
      </header>

      <main id="register-main-section" className="dashboard-main">
        <div className="db-container" style={{ maxWidth: '800px' }}>
          
          <div className="step-indicator">
            <div className={`step-node ${step >= 1 ? 'active' : ''}`}>1. Thông tin</div>
            <div className="step-line"></div>
            <div className={`step-node ${step >= 2 ? 'active' : ''}`}>2. Thẻ sinh viên</div>
            <div className="step-line"></div>
            <div className={`step-node ${step >= 3 ? 'active' : ''}`}>3. Quét khuôn mặt</div>
            <div className="step-line"></div>
            <div className={`step-node ${step === 4 ? 'active' : ''}`}>4. Hoàn tất</div>
          </div>

          <div className="control-card">
            
            {step === 1 && (
              <div id="register-step-1">
                <h2 className="control-title">Nhập thông tin cá nhân</h2>
                <p className="control-desc">Vui lòng nhập đầy đủ các trường thông tin cần thiết.</p>
                
                <div className="form-group">
                  <label>Họ và tên</label>
                  <input 
                    type="text" 
                    name="fullName" 
                    value={form.fullName} 
                    onChange={handleInputChange} 
                    placeholder="Nguyễn Văn A"
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Mã số sinh viên (MSSV)</label>
                    <input 
                      type="text" 
                      name="studentId" 
                      value={form.studentId} 
                      onChange={handleInputChange} 
                      placeholder="e.g. B20DCCN001"
                    />
                  </div>
                  <div className="form-group">
                    <label>Ngày sinh</label>
                    <input 
                      type="date" 
                      name="dob" 
                      value={form.dob} 
                      onChange={handleInputChange}
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Khoa / Ngành</label>
                    <input 
                      type="text" 
                      name="faculty" 
                      value={form.faculty} 
                      onChange={handleInputChange} 
                      placeholder="Công nghệ thông tin"
                    />
                  </div>
                  <div className="form-group">
                    <label>Email liên hệ</label>
                    <input 
                      type="email" 
                      name="email" 
                      value={form.email} 
                      onChange={handleInputChange} 
                      placeholder="sv@university.edu.vn"
                    />
                  </div>
                </div>

                <button 
                  id="btn-step1-next"
                  className="btn-action-verify" 
                  style={{ marginTop: '20px' }}
                  disabled={!form.fullName || !form.studentId || !form.dob}
                  onClick={() => setStep(2)}
                >
                  Tiếp theo: Xác thực thẻ sinh viên
                </button>
              </div>
            )}

            {step === 2 && (
              <div id="register-step-2">
                <h2 className="control-title">Xác thực thẻ sinh viên</h2>
                <p className="control-desc">Tải ảnh hai mặt rõ nét của Thẻ sinh viên cá nhân để tiến hành đăng ký.</p>
                
                <div className="card-upload-grid">
                  <div className="upload-box">
                    <p className="upload-label">Mặt trước thẻ sinh viên</p>
                    <div className="image-preview-container">
                      {front ? (
                        <img src={front} alt="Mặt trước" className="card-preview" />
                      ) : (
                        <div className="preview-placeholder">Chưa tải ảnh lên</div>
                      )}
                    </div>
                    <input 
                      type="file" 
                      accept="image/*" 
                      id="front-upload" 
                      style={{ display: 'none' }} 
                      onChange={(e) => handleFileChange(e, 'front')} 
                    />
                    <label htmlFor="front-upload" className="btn-upload">Tải ảnh mặt trước</label>
                  </div>

                  <div className="upload-box">
                    <p className="upload-label">Mặt sau thẻ sinh viên</p>
                    <div className="image-preview-container">
                      {back ? (
                        <img src={back} alt="Mặt sau" className="card-preview" />
                      ) : (
                        <div className="preview-placeholder">Chưa tải ảnh lên</div>
                      )}
                    </div>
                    <input 
                      type="file" 
                      accept="image/*" 
                      id="back-upload" 
                      style={{ display: 'none' }} 
                      onChange={(e) => handleFileChange(e, 'back')} 
                    />
                    <label htmlFor="back-upload" className="btn-upload">Tải ảnh mặt sau</label>
                  </div>
                </div>

                <div className="btn-group" style={{ display: 'flex', gap: '15px', marginTop: '30px' }}>
                  <button id="btn-step2-back" className="btn-back" style={{ flex: 1 }} onClick={() => setStep(1)}>Quay lại</button>
                  <button 
                    id="btn-step2-next"
                    className="btn-action-verify" 
                    style={{ flex: 2 }} 
                    disabled={!front || !back}
                    onClick={() => setStep(3)}
                  >
                    Tiếp theo: Quét khuôn mặt
                  </button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div id="register-step-3">
                <h2 className="control-title">Ghi nhận khuôn mặt sinh trắc học</h2>
                <p className="control-desc">Vui lòng giữ vị trí thẳng trước camera khi quét.</p>
                
                <div className={`video-frame ${scanning ? 'active-scan' : ''}`} style={{ marginBottom: '24px', position: 'relative', overflow: 'hidden', height: '360px', background: '#000' }}>
                  
                  <canvas ref={canvasRef} style={{ display: 'none' }} />

                  <video 
                    ref={videoRef} 
                    autoPlay 
                    playsInline 
                    muted
                    style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }} 
                  />

                  {scanning && (
                    <>
                      <div className="biometric-scanner-grid"></div>
                      <div className="biometric-box-overlay"></div>
                      <div className="biometric-points-container">
                        <div className="biometric-point" style={{ top: '40%', left: '42%' }}></div>
                        <div className="biometric-point" style={{ top: '40%', left: '58%' }}></div>
                        <div className="biometric-point" style={{ top: '53%', left: '50%' }}></div>
                        <div className="biometric-point" style={{ top: '65%', left: '44%' }}></div>
                        <div className="biometric-point" style={{ top: '65%', left: '56%' }}></div>
                        <div className="biometric-point" style={{ top: '75%', left: '50%' }}></div>
                      </div>
                      <div className="biometric-hud">
                        <div className="biometric-hud-box">PXL_SIZE: 640x480</div>
                        <div className="biometric-hud-box">SAFE_VEC: ON | SYN: {rate}%</div>
                      </div>
                      <div className="scan-line" style={{ zIndex: 10 }}></div>
                    </>
                  )}

                  <div className="stream-overlay-text" style={{ position: 'absolute', bottom: '10px', left: '10px', color: '#fff', background: 'rgba(0,0,0,0.6)', padding: '4px 10px', borderRadius: '4px', fontSize: '12px', zIndex: 3 }}>
                    Trạng thái: <span style={{ color: '#00ff7f' }}>{status}</span>
                  </div>
                </div>

                {scanning && (
                  <div className="progress-section" style={{ marginBottom: '20px' }}>
                    <div className="progress-header">
                      <span className="status-label">{status}</span>
                      <span className="percent-label">{rate}%</span>
                    </div>
                    <div className="progress-bar-track">
                      <div className="progress-bar-fill" style={{ width: `${rate}%` }}></div>
                    </div>
                  </div>
                )}

                <div className="btn-group" style={{ display: 'flex', gap: '15px' }}>
                  <button id="btn-step3-back" className="btn-back" style={{ flex: 1 }} disabled={scanning} onClick={() => setStep(2)}>Quay lại</button>
                  {!done ? (
                    <button 
                      id="btn-step3-scan"
                      className={`btn-action-verify ${scanning ? 'disabled' : ''}`} 
                      style={{ flex: 2 }}
                      onClick={startFaceScan}
                      disabled={scanning}
                    >
                      {scanning ? 'Đang thực hiện quét...' : 'Bắt đầu quét khuôn mặt'}
                    </button>
                  ) : (
                    <button 
                      id="btn-step3-submit"
                      className="btn-action-glow" 
                      style={{ flex: 2 }} 
                      onClick={handleRegisterSubmit}
                    >
                      Hoàn thành & Lưu dữ liệu
                    </button>
                  )}
                </div>
              </div>
            )}

            {step === 4 && (
              <div id="register-step-4" style={{ textAlign: 'center', padding: '30px 10px' }}>
                <div className="success-checkmark"></div>
                <h2 className="control-title" style={{ color: '#00ff7f', marginTop: '24px', textAlign: 'center' }}>Đăng ký hoàn tất!</h2>
                <p className="control-desc" style={{ textAlign: 'center' }}>
                  Hồ sơ sinh học đã được đồng bộ hóa thành công vào cơ sở dữ liệu SmartFace.
                </p>
                <div className="loader-db">Hệ thống đang điều hướng về trang chủ...</div>
              </div>
            )}

          </div>

          <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '12px', color: '#64748b' }}>
            © {new Date().getFullYear()} SmartFace ID. Toàn bộ thông tin sinh học và đăng ký được bảo mật theo tiêu chuẩn sở hữu trí tuệ của nhà phát triển.
          </div>
        </div>
      </main>
    </div>
  );
};

export default Register;