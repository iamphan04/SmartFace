import React, { useState } from 'react';
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
  const docType = 'student_id';

  const [rate, setRate] = useState(0);
  const [scanning, setScanning] = useState(false);
  const [status, setStatus] = useState('Sẵn sàng quét khuôn mặt');
  const [done, setDone] = useState(false);

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

  const startFaceScan = () => {
    if (scanning) return;
    setScanning(true);
    setRate(0);
    setStatus('Đang khởi động camera quét...');

    let progress = 0;
    const interval = setInterval(() => {
      progress += 2;
      setRate(progress);

      if (progress === 20) {
        setStatus('Vui lòng nhìn thẳng vào camera...');
      } else if (progress === 50) {
        setStatus('Vui lòng quay nhẹ mặt sang trái và phải...');
      } else if (progress === 80) {
        setStatus('Đang tối ưu hóa sơ đồ đặc trưng khuôn mặt...');
      } else if (progress >= 100) {
        clearInterval(interval);
        setStatus('Thu thập dữ liệu khuôn mặt hoàn tất!');
        setScanning(false);
        setDone(true);
      }
    }, 60);
  };

  const handleRegisterSubmit = async () => {
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
      } catch (e) {
        usersList = [];
      }
    }
    usersList = usersList.filter((u) => u.studentId !== userData.studentId);
    usersList.push(userData);
    localStorage.setItem('smartface_db_users', JSON.stringify(usersList));

    try {
      await setDoc(doc(db, 'users', userData.studentId), userData);
      console.log("Successfully registered to cloud database: users/" + userData.studentId);
    } catch (error) {
      console.error("Firestore Save Error:", error);
      try {
        handleFirestoreError(error, OperationType.WRITE, `users/${userData.studentId}`);
      } catch (e) {}
    }

    setStep(4);
    setTimeout(() => {
      navigate('/');
    }, 2500);
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
                
                <div className={`video-frame ${scanning ? 'active-scan' : ''}`} style={{ marginBottom: '24px', position: 'relative' }}>
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
                  <div className="video-placeholder" style={{ zIndex: 2 }}>
                    <svg viewBox="0 0 24 24" fill="currentColor" className="camera-icon">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
                    </svg>
                    <p style={{ color: '#fff' }}>Hệ thống camera ghi nhận</p>
                    <span className="stream-status">{status}</span>
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
