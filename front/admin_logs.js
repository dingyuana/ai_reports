document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;

    // 检查登录状态和权限
    const token = localStorage.getItem('access_token');
    const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
    
    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    if (userInfo.role !== 'admin' && userInfo.role !== 'super_admin') {
        alert('您没有权限访问此页面');
        window.location.href = '/index.html';
        return;
    }

    // 获取DOM元素
    const logsTableBody = document.getElementById('logs-table-body');
    const loadingEl = document.getElementById('loading');
    const errorMessageEl = document.getElementById('error-message');
    const actionFilter = document.getElementById('action-filter');
    const userFilter = document.getElementById('user-filter');
    const dateFilter = document.getElementById('date-filter');
    const searchInput = document.getElementById('search-input');
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    const pageInfo = document.getElementById('page-info');
    const logoutBtn = document.getElementById('logout-btn');

    let logs = [];
    let users = [];
    let currentPage = 1;
    const pageSize = 20;

    // API请求辅助函数
    async function apiRequest(url, options = {}) {
        const headers = {
            'Authorization': `Bearer ${token}`,
            ...options.headers
        };
        
        const response = await fetch(url, { ...options, headers });
        
        if (response.status === 401) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_info');
            window.location.href = '/login.html';
            return null;
        }
        
        return response;
    }

    // 退出登录
    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        window.location.href = '/login.html';
    });

    // 加载用户列表（用于筛选）
    async function loadUsers() {
        try {
            const response = await apiRequest(`${API_BASE_URL}/api/admin/users`);
            
            if (!response) return;
            
            if (!response.ok) {
                console.error('加载用户列表失败');
                return;
            }

            users = await response.json();
            
            // 更新用户筛选下拉框
            userFilter.innerHTML = '<option value="">所有用户</option>';
            users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = user.username;
                userFilter.appendChild(option);
            });
        } catch (error) {
            console.error('加载用户列表失败:', error);
        }
    }

    // 加载日志列表
    async function loadLogs() {
        loadingEl.classList.remove('hidden');
        errorMessageEl.classList.add('hidden');
        logsTableBody.innerHTML = '';

        try {
            const params = new URLSearchParams();
            if (actionFilter.value) params.append('action', actionFilter.value);
            if (userFilter.value) params.append('user_id', userFilter.value);
            if (dateFilter.value) params.append('date', dateFilter.value);
            if (searchInput.value) params.append('search', searchInput.value);
            params.append('page', currentPage);
            params.append('page_size', pageSize);

            const response = await apiRequest(`${API_BASE_URL}/api/admin/logs?${params.toString()}`);
            
            if (!response) return;
            
            if (!response.ok) {
                throw new Error('加载日志列表失败');
            }

            const data = await response.json();
            logs = data.logs || [];
            const totalPages = Math.ceil(data.total / pageSize);

            renderLogs(logs);
            updatePagination(totalPages);
        } catch (error) {
            console.error('加载日志列表失败:', error);
            errorMessageEl.textContent = '加载日志列表失败: ' + error.message;
            errorMessageEl.classList.remove('hidden');
        } finally {
            loadingEl.classList.add('hidden');
        }
    }

    // 渲染日志列表
    function renderLogs(logList) {
        logsTableBody.innerHTML = '';
        
        if (logList.length === 0) {
            logsTableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem;">暂无日志记录</td></tr>';
            return;
        }

        const actionMap = {
            'login': '登录',
            'logout': '退出登录',
            'upload': '上传文件',
            'annotate': '批阅报告',
            'download': '下载文件',
            'delete': '删除文件',
            'create_user': '创建用户',
            'update_user': '更新用户',
            'delete_user': '删除用户'
        };

        logList.forEach(log => {
            const tr = document.createElement('tr');
            const actionName = actionMap[log.action] || log.action;
            
            tr.innerHTML = `
                <td>${log.id}</td>
                <td>${formatDateTime(log.created_at)}</td>
                <td>${log.username || '-'}</td>
                <td><span class="action-badge ${log.action}">${actionName}</span></td>
                <td>${log.ip_address || '-'}</td>
                <td class="log-details">${log.details || '-'}</td>
            `;
            logsTableBody.appendChild(tr);
        });
    }

    // 格式化日期时间
    function formatDateTime(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN');
    }

    // 更新分页信息
    function updatePagination(totalPages) {
        pageInfo.textContent = `第 ${currentPage} 页`;
        prevPageBtn.disabled = currentPage <= 1;
        nextPageBtn.disabled = currentPage >= totalPages;
    }

    // 筛选事件
    actionFilter.addEventListener('change', () => {
        currentPage = 1;
        loadLogs();
    });

    userFilter.addEventListener('change', () => {
        currentPage = 1;
        loadLogs();
    });

    dateFilter.addEventListener('change', () => {
        currentPage = 1;
        loadLogs();
    });

    // 搜索事件（防抖）
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentPage = 1;
            loadLogs();
        }, 500);
    });

    // 分页事件
    prevPageBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadLogs();
        }
    });

    nextPageBtn.addEventListener('click', () => {
        currentPage++;
        loadLogs();
    });

    // 初始加载
    loadUsers();
    loadLogs();
});
