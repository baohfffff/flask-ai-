// 摄像头管理类
class CameraManager {
    constructor(videoElement, canvasElement) {
        this.video = videoElement;
        this.canvas = canvasElement;
        this.stream = null;
        this.isCameraOn = false;
    }

    // 开启摄像头
    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            this.video.srcObject = this.stream;
            this.isCameraOn = true;
            return true;
        } catch (err) {
            console.error('摄像头访问错误:', err);
            Utils.showMessage(`无法访问摄像头: ${err.message}`, 'error');
            return false;
        }
    }

    // 关闭摄像头
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.video.srcObject = null;
            this.isCameraOn = false;
        }
    }

    // 拍照
    capturePhoto() {
        if (!this.isCameraOn) {
            Utils.showMessage('请先开启摄像头', 'warning');
            return null;
        }

        const context = this.canvas.getContext('2d');
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

        return this.canvas.toDataURL('image/jpeg', 0.8);
    }

    // 检测人脸（简化版，实际应该调用后端API）
    detectFace(imageData) {
        return new Promise((resolve) => {
            // 这里应该调用后端的人脸检测API
            // 暂时模拟检测过程
            setTimeout(() => {
                resolve({ success: true, faces: 1 });
            }, 1000);
        });
    }
}

// 考勤功能类
class AttendanceManager {
    constructor() {
        this.cameraManager = null;
        this.isProcessing = false;
    }

    // 初始化
    init(videoElement, canvasElement) {
        this.cameraManager = new CameraManager(videoElement, canvasElement);
        this.bindEvents();
    }

    // 绑定事件
    bindEvents() {
        document.getElementById('start-camera')?.addEventListener('click', () => this.startCamera());
        document.getElementById('stop-camera')?.addEventListener('click', () => this.stopCamera());
        document.getElementById('capture-btn')?.addEventListener('click', () => this.takeAttendance());
        document.getElementById('retry-btn')?.addEventListener('click', () => this.retry());
    }

    // 开启摄像头
    async startCamera() {
        const success = await this.cameraManager.startCamera();
        if (success) {
            document.getElementById('start-camera').style.display = 'none';
            document.getElementById('stop-camera').style.display = 'inline-block';
            document.getElementById('capture-btn').disabled = false;
            Utils.showMessage('摄像头已开启', 'success');
        }
    }

    // 关闭摄像头
    stopCamera() {
        this.cameraManager.stopCamera();
        document.getElementById('start-camera').style.display = 'inline-block';
        document.getElementById('stop-camera').style.display = 'none';
        document.getElementById('capture-btn').disabled = true;
        Utils.showMessage('摄像头已关闭', 'info');
    }

    // 进行考勤
    async takeAttendance() {
        if (this.isProcessing) return;

        this.isProcessing = true;
        const captureBtn = document.getElementById('capture-btn');
        const retryBtn = document.getElementById('retry-btn');
        const resultDiv = document.getElementById('result');

        // 更新UI状态
        captureBtn.disabled = true;
        captureBtn.innerHTML = '<span class="loading"></span> 识别中...';
        resultDiv.innerHTML = '<div class="alert alert-info">人脸识别中，请保持面向摄像头...</div>';

        try {
            // 拍照
            const imageData = this.cameraManager.capturePhoto();
            if (!imageData) {
                throw new Error('拍照失败');
            }

            // 发送到后端进行识别
            const response = await Api.post('/api/face_recognition', { image: imageData });

            if (response.success) {
                resultDiv.innerHTML = `
                    <div class="alert alert-success">
                        <h5><i class="bi bi-check-circle"></i> 打卡成功!</h5>
                        <p>学生: ${response.student_name}</p>
                        <p>置信度: ${response.confidence}%</p>
                        <p>时间: ${new Date().toLocaleString()}</p>
                    </div>
                `;
                Utils.showMessage(`打卡成功: ${response.student_name}`, 'success');

                // 更新考勤记录
                this.loadAttendanceRecords();
            } else {
                throw new Error(response.message);
            }
        } catch (error) {
            console.error('考勤错误:', error);
            resultDiv.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
            Utils.showMessage(`打卡失败: ${error.message}`, 'error');
        } finally {
            // 恢复UI状态
            captureBtn.disabled = false;
            captureBtn.innerHTML = '<i class="bi bi-camera"></i> 拍照打卡';
            retryBtn.style.display = 'inline-block';
            this.isProcessing = false;
        }
    }

    // 重试
    retry() {
        document.getElementById('result').innerHTML = '';
        document.getElementById('retry-btn').style.display = 'none';
        document.getElementById('capture-btn').style.display = 'inline-block';
    }

    // 加载考勤记录
    async loadAttendanceRecords() {
        try {
            const response = await Api.get('/api/attendance_records');
            if (response.success) {
                this.renderAttendanceRecords(response.records);
            }
        } catch (error) {
            console.error('加载考勤记录错误:', error);
        }
    }

    // 渲染考勤记录
    renderAttendanceRecords(records) {
        const container = document.getElementById('attendance-records');
        if (!container) return;

        if (records.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">暂无打卡记录</p>';
            return;
        }

        let html = '<div class="list-group">';
        records.slice(0, 10).forEach(record => {
            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${record.student_name}</h6>
                        <small class="text-muted">学号: ${record.student_id}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-success rounded-pill">${record.status}</span>
                        <br>
                        <small>${record.timestamp}</small>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;
    }
}

// 初始化考勤系统
document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');

    if (video && canvas) {
        const attendanceManager = new AttendanceManager();
        attendanceManager.init(video, canvas);

        // 自动开启摄像头（可选）
        // attendanceManager.startCamera();
    }
});