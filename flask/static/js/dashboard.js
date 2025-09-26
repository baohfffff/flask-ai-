// 仪表盘功能
class Dashboard {
    constructor() {
        this.charts = {};
    }

    // 初始化
    init() {
        this.loadStatistics();
        this.loadRecentAttendance();
        this.setupEventListeners();
    }

    // 加载统计数据
    async loadStatistics() {
        try {
            // 这里可以添加API调用获取实时数据
            // 目前使用页面加载时传递的数据
            console.log('统计数据加载完成');
        } catch (error) {
            console.error('加载统计数据错误:', error);
        }
    }

    // 加载最近考勤记录
    async loadRecentAttendance() {
        try {
            const response = await Api.get('/api/attendance_records');
            if (response.success) {
                this.renderRecentAttendance(response.records.slice(0, 5));
            }
        } catch (error) {
            console.error('加载考勤记录错误:', error);
        }
    }

    // 渲染最近考勤记录
    renderRecentAttendance(records) {
        const container = document.getElementById('recent-attendance');
        if (!container) return;

        if (records.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">暂无考勤记录</p>';
            return;
        }

        let html = '<div class="list-group">';
        records.forEach(record => {
            const time = new Date(record.timestamp).toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit'
            });

            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${record.student_name}</h6>
                        <small class="text-muted">${record.student_id}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-success rounded-pill">${record.status}</span>
                        <br>
                        <small>${time}</small>
                    </div>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;
    }

    // 设置事件监听器
    setupEventListeners() {
        // 刷新按钮
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadStatistics();
            this.loadRecentAttendance();
            Utils.showMessage('数据已刷新', 'success');
        });

        // 快速操作按钮
        document.querySelectorAll('.quick-action').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.handleQuickAction(action);
            });
        });
    }

    // 处理快速操作
    handleQuickAction(action) {
        switch (action) {
            case 'attendance':
                window.location.href = '/attendance';
                break;
            case 'add-student':
                window.location.href = '/students';
                break;
            case 'records':
                // 打开考勤记录页面或模态框
                Utils.showMessage('正在开发中...', 'info');
                break;
            case 'stats':
                // 打开统计页面
                Utils.showMessage('正在开发中...', 'info');
                break;
        }
    }
}

// 初始化仪表盘
document.addEventListener('DOMContentLoaded', function() {
    const dashboard = new Dashboard();
    dashboard.init();
});