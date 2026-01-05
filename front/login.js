document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    
    // 获取DOM元素
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const messageEl = document.getElementById('message');

    // 切换标签页
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            
            // 更新按钮状态
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // 更新标签页内容
            tabPanes.forEach(pane => {
                pane.classList.remove('active');
                if (pane.id === `${targetTab}-tab`) {
                    pane.classList.add('active');
                }
            });
            
            // 清除消息
            hideMessage();
        });
    });

    // 显示消息
    function showMessage(text, type = 'info') {
        messageEl.textContent = text;
        messageEl.className = `message ${type}`;
    }

    // 隐藏消息
    function hideMessage() {
        messageEl.className = 'message';
        messageEl.textContent = '';
    }

    // 处理登录
    async function handleLogin(event) {
        event.preventDefault();
        
        const formData = new FormData(loginForm);
        const formDataObj = {
            username: formData.get('username'),
            password: formData.get('password')
        };

        const submitBtn = loginForm.querySelector('.submit-btn');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = '登录中...';
        submitBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formDataObj)
            });

            const data = await response.json();

            if (response.ok) {
                // 保存token和用户信息
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('user_info', JSON.stringify(data.user));
                
                showMessage('登录成功，正在跳转...', 'success');
                
                // 延迟跳转到主页面
                setTimeout(() => {
                    window.location.href = '/index.html';
                }, 1000);
            } else {
                showMessage(data.detail || '登录失败，请检查用户名和密码', 'error');
            }
        } catch (error) {
            console.error('登录错误:', error);
            showMessage('网络错误，请稍后重试', 'error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    // 处理注册
    async function handleRegister(event) {
        event.preventDefault();
        
        const formData = new FormData(registerForm);
        const password = formData.get('password');
        const confirmPassword = formData.get('confirm_password');

        // 验证密码
        if (password !== confirmPassword) {
            showMessage('两次输入的密码不一致', 'error');
            return;
        }

        if (password.length < 6) {
            showMessage('密码长度至少为6位', 'error');
            return;
        }

        const formDataObj = {
            username: formData.get('username'),
            password: password,
            email: formData.get('email') || null
        };

        const submitBtn = registerForm.querySelector('.submit-btn');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = '注册中...';
        submitBtn.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formDataObj)
            });

            const data = await response.json();

            if (response.ok) {
                showMessage('注册成功，请登录', 'success');
                
                // 清空注册表单
                registerForm.reset();
                
                // 切换到登录标签
                setTimeout(() => {
                    tabButtons[0].click();
                }, 1500);
            } else {
                showMessage(data.detail || '注册失败', 'error');
            }
        } catch (error) {
            console.error('注册错误:', error);
            showMessage('网络错误，请稍后重试', 'error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    // 绑定表单提交事件
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);

    // 检查是否已登录
    const token = localStorage.getItem('access_token');
    if (token) {
        // 验证token是否有效
        fetch(`${API_BASE_URL}/api/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            if (response.ok) {
                // token有效，跳转到主页面
                window.location.href = '/index.html';
            } else {
                // token无效，清除
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_info');
            }
        })
        .catch(error => {
            console.error('验证token失败:', error);
        });
    }
});
