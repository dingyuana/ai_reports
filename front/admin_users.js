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
    const usersTableBody = document.getElementById('users-table-body');
    const loadingEl = document.getElementById('loading');
    const errorMessageEl = document.getElementById('error-message');
    const searchInput = document.getElementById('search-input');
    const addUserBtn = document.getElementById('add-user-btn');
    const userModal = document.getElementById('user-modal');
    const userForm = document.getElementById('user-form');
    const modalTitle = document.getElementById('modal-title');
    const deleteModal = document.getElementById('delete-modal');
    const logoutBtn = document.getElementById('logout-btn');

    let users = [];
    let userToDelete = null;

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

    // 加载用户列表
    async function loadUsers() {
        loadingEl.classList.remove('hidden');
        errorMessageEl.classList.add('hidden');
        usersTableBody.innerHTML = '';

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/admin/users`);
            
            if (!response) return;
            
            if (!response.ok) {
                throw new Error('加载用户列表失败');
            }

            users = await response.json();
            renderUsers(users);
        } catch (error) {
            console.error('加载用户列表失败:', error);
            errorMessageEl.textContent = '加载用户列表失败: ' + error.message;
            errorMessageEl.classList.remove('hidden');
        } finally {
            loadingEl.classList.add('hidden');
        }
    }

    // 渲染用户列表
    function renderUsers(userList) {
        usersTableBody.innerHTML = '';
        
        if (userList.length === 0) {
            usersTableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem;">暂无用户</td></tr>';
            return;
        }

        const roleMap = {
            'user': '普通用户',
            'admin': '管理员',
            'super_admin': '超级管理员'
        };

        userList.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email || '-'}</td>
                <td><span class="role-badge ${user.role}">${roleMap[user.role] || user.role}</span></td>
                <td>${formatDate(user.created_at)}</td>
                <td>${user.last_login ? formatDate(user.last_login) : '从未登录'}</td>
                <td class="actions">
                    <button class="button small-button edit-btn" data-id="${user.id}">编辑</button>
                    <button class="button small-button danger delete-btn" data-id="${user.id}" data-username="${user.username}">删除</button>
                </td>
            `;
            usersTableBody.appendChild(tr);
        });

        // 绑定编辑和删除按钮事件
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const userId = parseInt(e.target.dataset.id);
                openEditModal(userId);
            });
        });

        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const userId = parseInt(e.target.dataset.id);
                const username = e.target.dataset.username;
                openDeleteModal(userId, username);
            });
        });
    }

    // 格式化日期
    function formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN');
    }

    // 搜索用户
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredUsers = users.filter(user => 
            user.username.toLowerCase().includes(searchTerm) ||
            (user.email && user.email.toLowerCase().includes(searchTerm))
        );
        renderUsers(filteredUsers);
    });

    // 打开添加用户模态框
    addUserBtn.addEventListener('click', () => {
        modalTitle.textContent = '添加用户';
        userForm.reset();
        document.getElementById('user-id').value = '';
        document.getElementById('password').required = true;
        document.getElementById('password-hint').textContent = '(必填)';
        userModal.classList.add('active');
    });

    // 打开编辑用户模态框
    async function openEditModal(userId) {
        const user = users.find(u => u.id === userId);
        if (!user) return;

        modalTitle.textContent = '编辑用户';
        document.getElementById('user-id').value = user.id;
        document.getElementById('username').value = user.username;
        document.getElementById('email').value = user.email || '';
        document.getElementById('password').value = '';
        document.getElementById('password').required = false;
        document.getElementById('password-hint').textContent = '(留空则不修改)';
        document.getElementById('role').value = user.role;
        userModal.classList.add('active');
    }

    // 打开删除确认模态框
    function openDeleteModal(userId, username) {
        userToDelete = userId;
        document.getElementById('delete-username').textContent = username;
        deleteModal.classList.add('active');
    }

    // 关闭模态框
    function closeModal(modal) {
        modal.classList.remove('active');
    }

    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            closeModal(userModal);
            closeModal(deleteModal);
        });
    });

    document.querySelectorAll('.cancel-btn').forEach(cancelBtn => {
        cancelBtn.addEventListener('click', () => {
            closeModal(userModal);
            closeModal(deleteModal);
        });
    });

    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal(e.target);
        }
    });

    // 提交用户表单
    userForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(userForm);
        const userId = document.getElementById('user-id').value;
        const userData = {
            username: formData.get('username'),
            email: formData.get('email') || null,
            role: formData.get('role')
        };

        const password = formData.get('password');
        if (password) {
            userData.password = password;
        }

        const submitBtn = userForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = '保存中...';
        submitBtn.disabled = true;

        try {
            let response;
            if (userId) {
                response = await apiRequest(`${API_BASE_URL}/api/admin/users/${userId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData)
                });
            } else {
                response = await apiRequest(`${API_BASE_URL}/api/admin/users`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(userData)
                });
            }

            if (!response) return;

            if (response.ok) {
                alert('保存成功');
                closeModal(userModal);
                await loadUsers();
            } else {
                const error = await response.json();
                alert('保存失败: ' + (error.detail || '未知错误'));
            }
        } catch (error) {
            console.error('保存用户失败:', error);
            alert('保存失败: ' + error.message);
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    });

    // 确认删除用户
    document.getElementById('confirm-delete-btn').addEventListener('click', async () => {
        if (!userToDelete) return;

        const deleteBtn = document.getElementById('confirm-delete-btn');
        const originalText = deleteBtn.textContent;
        deleteBtn.textContent = '删除中...';
        deleteBtn.disabled = true;

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/admin/users/${userToDelete}`, {
                method: 'DELETE'
            });

            if (!response) return;

            if (response.ok) {
                alert('删除成功');
                closeModal(deleteModal);
                await loadUsers();
            } else {
                const error = await response.json();
                alert('删除失败: ' + (error.detail || '未知错误'));
            }
        } catch (error) {
            console.error('删除用户失败:', error);
            alert('删除失败: ' + error.message);
        } finally {
            deleteBtn.textContent = originalText;
            deleteBtn.disabled = false;
            userToDelete = null;
        }
    });

    // 初始加载
    loadUsers();
});
