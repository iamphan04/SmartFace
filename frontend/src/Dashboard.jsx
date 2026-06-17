import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

const CARD_STEP_MIN_MS = 2500;
const SCAN_POLL_MS = 250;
const CARD_SCAN_TIMEOUT_MS = 28000;
const FACE_SCAN_TIMEOUT_MS = 22000;
const CARD_PROGRESS_SPEED = 280;
const FACE_PROGRESS_SPEED = 240;
const CARD_DONE_STEPS = new Set(['cardDone', 'face', 'done']);
const FACE_ACTIVE_STEPS = new Set(['cardDone', 'face']);

const stopCamera = () => {
  fetch('/api/camera/stop', { method: 'POST' }).catch(() => {});
};

const formatDob = dob => {
  if (!dob) return 'Chưa cập nhật';
  return dob.split('-').reverse().join('/');
};

const clampProgress = value => Math.min(98, value);

const Dashboard = () => {
  const navigate = useNavigate();
  const [active, setActive] = useState(false);
  const [pct, setPct] = useState(0);
  const [msg, setMsg] = useState('Sẵn sàng quét thẻ sinh viên');
  const [user, setUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [ok, setOk] = useState(false);
  const [errorMatch, setErrorMatch] = useState(false);
  const [confidence, setConfidence] = useState(0);
  const [cardConfidence, setCardConfidence] = useState(0);
  const [cardVerified, setCardVerified] = useState(false);
  const [mode, setMode] = useState('qr');
  const [flowStep, setFlowStep] = useState('card');
  const [streamSession, setStreamSession] = useState(null);

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
    } catch (error) {
      console.warn('Không thể phát âm báo', error);
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
        console.error('Không thể tải danh sách sinh viên', error);
        const cachedUsers = localStorage.getItem('smartface_db_users');
        if (cachedUsers) {
          try {
            usersList = JSON.parse(cachedUsers);
          } catch {
            usersList = [];
          }
        }
      }

      setUsers(usersList);
      setUser(usersList[0] || null);
    };

    fetchUsers();
  }, []);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  const resetVerification = () => {
    setActive(false);
    setPct(0);
    setOk(false);
    setErrorMatch(false);
    setConfidence(0);
    setCardConfidence(0);
    setCardVerified(false);
    setMode('qr');
    setFlowStep('card');
    setStreamSession(null);
    setMsg('Sẵn sàng quét thẻ sinh viên');
  };

  const waitForScan = async ({ statusUrl, sessionId, expectedMode, timeoutMs, progressOf }) => {
    const startedAt = Date.now();

    while (Date.now() - startedAt < timeoutMs) {
      await new Promise(resolve => setTimeout(resolve, SCAN_POLL_MS));
      const response = await fetch(statusUrl);
      const status = await response.json();

      if (!response.ok) {
        throw new Error(status.detail || 'Không đọc được trạng thái camera.');
      }
      if (status.sessionId !== sessionId || status.mode !== expectedMode) {
        throw new Error('Phiên camera đã thay đổi. Vui lòng thử lại.');
      }

      setPct(progressOf(status, Date.now() - startedAt));
      if (status.message) setMsg(status.message);
      if (status.completed) return status;
    }

    throw new Error('Hết thời gian chờ camera. Vui lòng thử lại.');
  };

  const runScanStep = async ({ step, studentId = '' }) => {
    const isFace = step === 'face';
    const startedAt = Date.now();
    const startUrl = isFace
      ? `/api/face/start/${encodeURIComponent(studentId)}?purpose=verify`
      : '/api/qr/start';
    const statusUrl = isFace ? '/api/face/status' : '/api/qr/status';
    const verifyUrl = isFace
      ? `/api/face/verify/${encodeURIComponent(studentId)}`
      : '/api/qr/verify-scan';

    setMode(isFace ? 'face' : 'qr');
    setFlowStep(isFace ? 'face' : 'card');
    setPct(0);
    setMsg(isFace ? 'Nhìn thẳng vào camera và giữ yên khuôn mặt.' : 'Đưa thẻ sinh viên vào khung.');

    const startResponse = await fetch(startUrl, { method: 'POST' });
    const started = await startResponse.json();
    if (!startResponse.ok) {
      throw new Error(started.detail || 'Không thể mở camera.');
    }

    setStreamSession(started.sessionId);

    await waitForScan({
      statusUrl,
      sessionId: started.sessionId,
      expectedMode: isFace ? 'face_verify' : 'qr',
      timeoutMs: isFace ? FACE_SCAN_TIMEOUT_MS : CARD_SCAN_TIMEOUT_MS,
      progressOf: (status, elapsed) => (
        isFace
          ? clampProgress(status.progress || Math.round(elapsed / FACE_PROGRESS_SPEED))
          : clampProgress(status.progress || Math.round(elapsed / CARD_PROGRESS_SPEED))
      ),
    });

    if (!isFace) {
      const remaining = CARD_STEP_MIN_MS - (Date.now() - startedAt);
      setPct(100);
      setMsg('Thẻ sinh viên hợp lệ.');
      if (remaining > 0) {
        await new Promise(resolve => setTimeout(resolve, remaining));
      }
    }

    const verifyResponse = await fetch(verifyUrl, { method: 'POST' });
    const result = await verifyResponse.json();
    if (!verifyResponse.ok || !result.success) {
      throw new Error(
        result.message ||
        result.detail ||
        (isFace ? 'Khuôn mặt chưa khớp. Vui lòng thử lại.' : 'Thẻ sinh viên chưa hợp lệ.')
      );
    }

    return result;
  };

  const rememberMatchedUser = matchedUser => {
    setUser(matchedUser);
    setUsers(prev => {
      const rest = prev.filter(item => item.studentId !== matchedUser.studentId);
      return [matchedUser, ...rest];
    });
  };

  const startCardScan = async () => {
    if (active) return;

    setActive(true);
    setPct(0);
    setOk(false);
    setErrorMatch(false);
    setConfidence(0);
    setCardConfidence(0);
    setCardVerified(false);
    setMode('qr');
    setFlowStep('card');
    setStreamSession(null);
    setMsg('Đưa thẻ sinh viên vào khung.');
    playBeep(440, 'sine', 0.1);

    try {
      const cardResult = await runScanStep({ step: 'qr' });
      const matchedUser = cardResult.user || user || users[0];
      if (!matchedUser?.studentId) {
        throw new Error('Không tìm thấy hồ sơ sinh viên.');
      }

      const score = Number(cardResult.cardConfidence || cardResult.cardScore || 0);
      rememberMatchedUser(matchedUser);
      setCardConfidence(score);
      setCardVerified(true);
      setPct(100);
      setErrorMatch(false);
      setFlowStep('cardDone');
      setMsg(`Thẻ sinh viên hợp lệ. Độ tin cậy ${score.toFixed(1)}%.`);
      playBeep(987.77, 'sine', 0.1);
    } catch (error) {
      console.error(error);
      setOk(false);
      setCardVerified(false);
      setErrorMatch(true);
      setMsg(error.message || 'Quét thẻ thất bại. Vui lòng thử lại.');
      playBeep(220, 'sawtooth', 0.4);
    } finally {
      setActive(false);
      setStreamSession(null);
      stopCamera();
    }
  };

  const startFaceScan = async () => {
    if (active) return;
    if (!cardVerified || !user?.studentId) {
      setErrorMatch(true);
      setMsg('Vui lòng quét thẻ sinh viên hợp lệ trước khi quét khuôn mặt.');
      return;
    }

    setActive(true);
    setPct(0);
    setOk(false);
    setErrorMatch(false);
    setMode('face');
    setFlowStep('face');
    setStreamSession(null);
    setMsg('Nhìn thẳng vào camera và giữ yên khuôn mặt.');
    playBeep(440, 'sine', 0.1);

    try {
      const faceResult = await runScanStep({
        step: 'face',
        studentId: user.studentId,
      });

      setConfidence(Number(faceResult.confidence || 0));
      setPct(100);
      setOk(true);
      setErrorMatch(false);
      setFlowStep('done');
      setMsg(`Xác thực thành công. Xin chào ${user.fullName}.`);
      playBeep(987.77, 'sine', 0.1);
      setTimeout(() => playBeep(1318.51, 'sine', 0.25), 110);
    } catch (error) {
      console.error(error);
      setOk(false);
      setErrorMatch(true);
      setMsg(error.message || 'Xác thực thất bại. Vui lòng thử lại.');
      playBeep(220, 'sawtooth', 0.4);
    } finally {
      setActive(false);
      setStreamSession(null);
      stopCamera();
    }
  };

  const cardStepDone = CARD_DONE_STEPS.has(flowStep);
  const faceStepActive = FACE_ACTIVE_STEPS.has(flowStep);
  const title = mode === 'face' ? 'Quét khuôn mặt' : 'Quét thẻ sinh viên';
  const description = mode === 'face'
    ? 'Nhìn thẳng vào camera, giữ khuôn mặt rõ và không di chuyển cho đến khi hoàn tất.'
    : 'Đưa thẻ sinh viên vào đúng khung. Sau khi thẻ hợp lệ, hệ thống sẽ hiện độ tin cậy của thẻ.';

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
            <div className={`video-frame ${active ? 'active-scan' : ''}`}>
              {active && streamSession !== null && (
                <img
                  id="backend-video"
                  src={`/api/camera/stream?session=${streamSession}`}
                  alt="Camera xác thực SmartFace"
                />
              )}

              {active && mode === 'face' && (
                <>
                  <div className="biometric-scanner-grid"></div>
                  <div className="biometric-box-overlay"></div>
                  <div className="biometric-hud">
                    <div className="biometric-hud-box">KHUÔN MẶT</div>
                    <div className="biometric-hud-box">TIẾN ĐỘ: {pct}%</div>
                  </div>
                  <div className="scan-line"></div>
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
                  <div className="biometric-hud">
                    <div className="biometric-hud-box">THẺ SINH VIÊN</div>
                    <div className="biometric-hud-box">TIẾN ĐỘ: {pct}%</div>
                  </div>
                </>
              )}

              <div className="video-placeholder">
                <svg viewBox="0 0 24 24" fill="currentColor" className="camera-icon">
                  <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z" />
                </svg>
                <p>{mode === 'face' ? 'Nhìn thẳng vào camera' : 'Đưa thẻ sinh viên vào khung'}</p>
                <span className="stream-status">
                  {active
                    ? (mode === 'face' ? 'Giữ yên khuôn mặt' : 'Giữ thẻ rõ nét')
                    : 'Sẵn sàng xác thực'}
                </span>
              </div>
            </div>
          </div>

          <div className="control-column">
            <div className="control-card">
              {!ok && !errorMatch && (
                <>
                  <div className="step-indicator">
                    <div className={`step-node ${flowStep === 'card' ? 'active' : ''} ${cardStepDone ? 'done' : ''}`}>
                      1. Thẻ sinh viên
                    </div>
                    <div className="step-line"></div>
                    <div className={`step-node ${faceStepActive ? 'active' : ''} ${flowStep === 'done' ? 'done' : ''}`}>
                      2. Khuôn mặt
                    </div>
                  </div>

                  {!cardVerified && (
                    <>
                      <h2 className="control-title">{title}</h2>
                      <div className="control-desc">{description}</div>

                      <button
                        id="btn-trigger-verify"
                        className={`btn-action-verify ${active ? 'disabled' : ''}`}
                        onClick={startCardScan}
                        disabled={active}
                      >
                        <span className="primary-action-label">
                          {active ? 'Đang quét thẻ...' : 'Bắt đầu quét thẻ'}
                        </span>
                      </button>
                    </>
                  )}

                  {cardVerified && !active && (
                    <div className="db-match-card card-result-card">
                      <h4>Thẻ sinh viên hợp lệ</h4>
                      <div>
                        <p>
                          <strong>Độ tin cậy thẻ:</strong>{' '}
                          <span className="confidence-highlight">{cardConfidence.toFixed(1)}%</span>
                        </p>
                        <p><strong>Họ và tên:</strong> {user?.fullName || 'Sinh viên'}</p>
                        <p><strong>MSSV:</strong> {user?.studentId || ''}</p>
                        <p><strong>Khoa:</strong> {user?.faculty || 'Chưa cập nhật'}</p>
                      </div>

                      <button className="btn-action-verify" onClick={startFaceScan}>
                        Tiếp tục quét khuôn mặt
                      </button>
                    </div>
                  )}

                  {cardVerified && active && (
                    <>
                      <h2 className="control-title">Quét khuôn mặt</h2>
                      <div className="control-desc">
                        Nhìn thẳng vào camera, giữ khuôn mặt rõ và không di chuyển cho đến khi hoàn tất.
                      </div>
                    </>
                  )}
                </>
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

              {!active && ok && (
                <div id="match-card" className="db-match-card">
                  <h4>Xác thực thành công</h4>
                  <div>
                    <p><strong>Họ và tên:</strong> {user?.fullName || 'Sinh viên'}</p>
                    <p><strong>MSSV:</strong> {user?.studentId || ''}</p>
                    <p><strong>Khoa:</strong> {user?.faculty || 'Chưa cập nhật'}</p>
                    <p><strong>Ngày sinh:</strong> {formatDob(user?.dob)}</p>
                    <p>
                      <strong>Chỉ số tin cậy:</strong>{' '}
                      <span style={{ color: '#00ff7f', fontWeight: 'bold' }}>
                        {confidence.toFixed(1)}%
                      </span>
                    </p>
                  </div>

                  <button className="btn-action-verify" onClick={resetVerification}>
                    Thực hiện lại
                  </button>
                </div>
              )}

              {!active && errorMatch && (
                <div id="match-card-fail" className="db-match-card fail-card">
                  <h4>Xác thực thất bại</h4>
                  <p>{msg}</p>
                  <button className="btn-action-verify" onClick={resetVerification}>
                    Thử lại
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="dashboard-footer">
            © {new Date().getFullYear()} SmartFace ID. Thông tin sinh viên được bảo mật trong hệ thống xác thực.
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
