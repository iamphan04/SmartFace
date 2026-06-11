import React, { useState } from 'react';
import { HelpCircle, X, UserPlus, Camera, CheckCircle2, FileText } from 'lucide-react';

const HelpButton = () => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const toggleModal = () => {
    setIsOpen(!isOpen);
    setShowTooltip(false);
  };

  return (
    <>

      <div 
        id="floating-help-container"
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}
      >
        {showTooltip && !isOpen && (
          <div 
            id="help-tooltip"
            style={{
              background: 'rgba(15, 23, 42, 0.9)',
              color: '#22d3ee',
              padding: '8px 14px',
              borderRadius: '8px',
              fontSize: '12px',
              fontWeight: '600',
              letterSpacing: '0.5px',
              border: '1px solid rgba(6, 182, 212, 0.4)',
              boxShadow: '0 0 15px rgba(6, 182, 212, 0.2)',
              backdropFilter: 'blur(8px)',
              animation: 'fadeIn 0.2s ease-out',
              whiteSpace: 'nowrap',
              fontFamily: 'system-ui, -apple-system, sans-serif'
            }}
          >
            HƯỚNG DẪN SỬ DỤNG
          </div>
        )}

        <button
          id="btn-floating-user-guide"
          onClick={toggleModal}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          style={{
            width: '52px',
            height: '52px',
            borderRadius: '50%',
            background: 'rgba(15, 23, 42, 0.75)',
            border: '2px solid #22d3ee',
            color: '#22d3ee',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: '0 0 12px rgba(6, 182, 212, 0.3), inset 0 0 8px rgba(6, 182, 212, 0.2)',
            transition: 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            backdropFilter: 'blur(10px)',
            outline: 'none',
            padding: 0
          }}
          className="floating-guide-button"
        >
          <HelpCircle size={26} style={{ filter: 'drop-shadow(0 0 4px rgba(6, 182, 212, 0.5))' }} />
        </button>
      </div>

      {isOpen && (
        <div 
          className="modal-overlay" 
          onClick={toggleModal}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(5, 8, 16, 0.82)',
            backdropFilter: 'blur(16px)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
            overflowY: 'auto'
          }}
        >
          <div 
            className="modal-content" 
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              borderRadius: '24px',
              width: '100%',
              maxWidth: '850px',
              padding: '36px',
              position: 'relative',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 40px rgba(6, 182, 212, 0.1)',
              animation: 'modalSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
          >
            <button
              onClick={toggleModal}
              style={{
                position: 'absolute',
                top: '20px',
                right: '25px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#94a3b8',
                borderRadius: '50%',
                width: '36px',
                height: '36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#ff4a4a';
                e.currentTarget.style.background = 'rgba(255, 74, 74, 0.15)';
                e.currentTarget.style.borderColor = 'rgba(255, 74, 74, 0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#94a3b8';
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
              }}
            >
              <X size={18} />
            </button>

            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <div 
                style={{
                  display: 'inline-block',
                  background: 'rgba(6, 182, 212, 0.1)',
                  color: '#22d3ee',
                  padding: '4px 12px',
                  borderRadius: '100px',
                  fontSize: '11px',
                  fontWeight: '700',
                  letterSpacing: '1.5px',
                  marginBottom: '12px',
                  border: '1px solid rgba(6, 182, 212, 0.2)'
                }}
              >
                CẨM NANG SỬ DỤNG
              </div>
              <h2 
                style={{ 
                  fontSize: '24px', 
                  fontWeight: '800', 
                  color: '#ffffff', 
                  letterSpacing: '-0.5px', 
                  textTransform: 'uppercase', 
                  margin: '0 0 10px 0',
                  lineHeight: '1.2'
                }}
              >
                HƯỚNG DẪN SỬ DỤNG HỆ THỐNG SMARTFACE
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '14px', maxWidth: '600px', margin: '0 auto' }}>
                Làm quen với quy trình đăng ký và xác thực thông minh chỉ với các bước thao tác đơn giản dưới đây.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginBottom: '28px' }}>
              <div style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid rgba(6, 182, 212, 0.12)',
                padding: '24px',
                borderRadius: '16px',
                display: 'flex',
                gap: '20px',
                alignItems: 'flex-start',
                textAlign: 'left'
              }}>
                <div style={{
                  width: '44px',
                  height: '44px',
                  background: 'rgba(6, 182, 212, 0.1)',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#22d3ee',
                  flexShrink: 0
                }}>
                  <UserPlus size={22} />
                </div>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#ffffff', margin: '0 0 6px 0' }}>
                    Bước 1: Đăng Ký Tài Khoản Sinh Viên
                  </h3>
                  <p style={{ color: '#94a3b8', fontSize: '13.5px', lineHeight: '1.5', margin: 0 }}>
                    Nhấn chọn <strong>"Đăng ký tài khoản mới"</strong>. Nhập đầy đủ thông tin định danh cần thiết như Họ tên, Mã số sinh viên (MSSV), Ngày sinh, Khoa, và tiến hành thực hiện quét chân dung Thẻ sinh viên với dạng mặt trước & mặt sau.
                  </p>
                </div>
              </div>

              <div style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid rgba(59, 130, 246, 0.12)',
                padding: '24px',
                borderRadius: '16px',
                display: 'flex',
                gap: '20px',
                alignItems: 'flex-start',
                textAlign: 'left'
              }}>
                <div style={{
                  width: '44px',
                  height: '44px',
                  background: 'rgba(59, 130, 246, 0.1)',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#3b82f6',
                  flexShrink: 0
                }}>
                  <Camera size={22} />
                </div>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#ffffff', margin: '0 0 6px 0' }}>
                    Bước 2: Cấp Quyền Truy Cập Camera
                  </h3>
                  <p style={{ color: '#94a3b8', fontSize: '13.5px', lineHeight: '1.5', margin: 0 }}>
                    Khi được hỏi, vui lòng đồng ý cấp quyền webcam. Camera quang học live-feed là thiết bị phân tích thời gian thực bắt buộc dùng xác thực tương quan gương mặt bạn với Thẻ sinh viên.
                  </p>
                </div>
              </div>

              <div style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid rgba(147, 51, 234, 0.12)',
                padding: '24px',
                borderRadius: '16px',
                display: 'flex',
                gap: '20px',
                alignItems: 'flex-start',
                textAlign: 'left'
              }}>
                <div style={{
                  width: '44px',
                  height: '44px',
                  background: 'rgba(147, 51, 234, 0.1)',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#a855f7',
                  flexShrink: 0
                }}>
                  <CheckCircle2 size={22} />
                </div>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#ffffff', margin: '0 0 6px 0' }}>
                    Bước 3: Thực Hiện Kiểm Thử Đối Chiếu
                  </h3>
                  <p style={{ color: '#94a3b8', fontSize: '13.5px', lineHeight: '1.5', margin: 0 }}>
                    Vào giao diện Máy quét (Dashboard), nhấp chọn tab <strong>"Xác thực Gương mặt"</strong> hoặc <strong>"Giấy tờ tùy thân (OCR)"</strong> và ấn nút Bắt đầu để bắt đầu xác thực.
                  </p>
                </div>
              </div>
            </div>

            <div style={{
              background: 'rgba(6, 182, 212, 0.05)',
              border: '1px solid rgba(6, 182, 212, 0.15)',
              borderLeft: '4px solid #22d3ee',
              padding: '16px 20px',
              borderRadius: '12px',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '30px'
            }}>
            </div>

            <div style={{ textAlign: 'center' }}>
              <button
                id="btn-close-guide"
                onClick={toggleModal}
                style={{
                  background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
                  color: '#ffffff',
                  border: 'none',
                  padding: '12px 36px',
                  borderRadius: '12px',
                  fontSize: '14px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  boxShadow: '0 4px 15px rgba(6, 182, 212, 0.3)',
                  transition: 'all 0.2s ease',
                  textTransform: 'uppercase',
                  letterSpacing: '1px'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(6, 182, 212, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 4px 15px rgba(6, 182, 212, 0.3)';
                }}
              >
                Tôi đã hiểu
              </button>
            </div>
          </div>
        </div>
      )}

 
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateX(10px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes modalSlideUp {
          from { opacity: 0; transform: scale(0.95) translateY(20px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
        .floating-guide-button:hover {
          transform: scale(1.1) rotate(10deg);
          border-color: #3b82f6 !important;
          color: #3b82f6 !important;
          box-shadow: 0 0 20px rgba(59, 130, 246, 0.6), inset 0 0 12px rgba(59, 130, 246, 0.3) !important;
        }
        .floating-guide-button:active {
          transform: scale(0.95);
        }
      `}</style>
    </>
  );
};

export default HelpButton;
