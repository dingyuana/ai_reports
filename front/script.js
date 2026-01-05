document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;

    // 检查登录状态
    const token = localStorage.getItem('access_token');
    const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
    
    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    // 显示用户信息
    const userInfoEl = document.getElementById('user-info');
    const usernameEl = userInfoEl.querySelector('.username');
    const roleBadgeEl = userInfoEl.querySelector('.role-badge');
    const logoutBtn = document.getElementById('logout-btn');
    
    usernameEl.textContent = userInfo.username || '未知用户';
    
    // 设置角色标签
    const roleMap = {
        'user': '普通用户',
        'admin': '管理员',
        'super_admin': '超级管理员'
    };
    roleBadgeEl.textContent = roleMap[userInfo.role] || '用户';
    roleBadgeEl.className = `role-badge ${userInfo.role}`;
    
    // 根据角色控制界面显示
    if (userInfo.role === 'admin' || userInfo.role === 'super_admin') {
        // 管理员角色：隐藏系统功能，显示管理入口
        document.getElementById('student-reports-panel').style.display = 'none';
        document.getElementById('graded-reports-panel').style.display = 'none';
        document.getElementById('criteria-panel').style.display = 'none';
        document.querySelector('.bottom-control-panel').style.display = 'none';
        
        // 添加管理入口
        const mainGrid = document.querySelector('.main-grid');
        mainGrid.innerHTML = `
            <div class="panel admin-panel">
                <div class="panel-header">
                    <h2>管理功能</h2>
                </div>
                <div class="admin-menu">
                    <a href="/admin_users.html" class="admin-menu-item">
                        <span class="icon">👥</span>
                        <span>用户管理</span>
                    </a>
                    <a href="/admin_logs.html" class="admin-menu-item">
                        <span class="icon">📋</span>
                        <span>日志管理</span>
                    </a>
                </div>
            </div>
        `;
    }
    
    // 退出登录
    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        window.location.href = '/login.html';
    });

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

    let selectedDirectory = null;

    // 左侧面板元素
    const studentReportsPanel = document.getElementById('student-reports-panel');
    const dirLoadingEl = document.getElementById('dir-loading');
    const directoryListEl = document.getElementById('directory-list');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    
    // 中间面板元素
    const criteriaFormEl = document.getElementById('criteria-form');
    const criteriaInputEl = document.getElementById('criteria-input');
    const criteriaPreviewContentEl = document.getElementById('criteria-preview-content');
    const criteriaStatusEl = document.getElementById('criteria-status');
    const addMarkingsCheckbox = document.getElementById('option-add-markings');
    const aiReviewCheckbox = document.getElementById('option-ai-review');
    const autoGradingCheckbox = document.getElementById('option-auto-grading');

    // 右侧面板元素
    const gradedLoadingEl = document.getElementById('graded-loading');
    const gradedListEl = document.getElementById('graded-list');

    // 提交按钮
    const submitGradingBtn = document.getElementById('submit-grading-btn');

    // 结果面板元素
    const resultsContainerEl = document.getElementById('results-container');
    const resultsTitleEl = document.getElementById('results-title');
    const reportListEl = document.getElementById('report-list');
    const reportLoadingEl = document.getElementById('report-loading');
    const csvDownloadLinkEl = document.getElementById('csv-download-link');

    /**
     * 通用函数：创建文件/目录树
     */
    function createTreeView(items, container, isStudentReports) {
        container.innerHTML = '';
        if (items.length === 0) {
            container.innerHTML = '<p style="padding: 1rem; text-align: center; color: #888;">未找到任何项目。</p>';
            return;
        }

        const tree = document.createElement('ul');
        tree.className = 'tree';
        items.forEach(item => {
            const itemLi = document.createElement('li');
            itemLi.className = 'tree-item is-directory';
            itemLi.dataset.directoryName = item.name; // 将目录名存储在li元素上

            const itemRow = document.createElement('div');
            itemRow.className = 'tree-row';
            const fileCount = item.files ? item.files.length : 0;
            
            const downloadButtonHtml = !isStudentReports
                ? `<button class="button small-button download-btn" data-download-dir="${item.name}">下载</button>`
                : '';
            
            const deleteButtonHtml = `<button class="button small-button delete-btn" 
                data-delete-dir="${item.name}" 
                data-delete-type="${isStudentReports ? 'student' : 'graded'}">删除</button>`;

            itemRow.innerHTML = `
                <span class="caret"></span>
                <span class="icon folder-icon"></span>
                <span class="name" title="${item.name}">${item.name}</span>
                <span class="file-count">(${fileCount}个)</span>
                ${downloadButtonHtml}
                ${deleteButtonHtml}
            `;

            const fileUl = document.createElement('ul');
            fileUl.className = 'nested-list';

            if (item.files && item.files.length > 0) {
                item.files.forEach(file => {
                    const fileLi = document.createElement('li');
                    fileLi.className = 'tree-item is-file';
                    
                    const fileHtml = !isStudentReports 
                        ? `<a href="${API_BASE_URL}/graded_reports/${item.name}/${file}" target="_blank" class="name" title="${file}">${file}</a>`
                        : `<span class="name" title="${file}">${file}</span>`;

                    fileLi.innerHTML = `
                        <div class="tree-row">
                            <span class="icon file-icon"></span>
                            ${fileHtml}
                        </div>
                    `;
                    fileUl.appendChild(fileLi);
                });
            } else {
                const emptyLi = document.createElement('li');
                emptyLi.className = 'tree-item is-empty';
                emptyLi.innerHTML = `<div class="tree-row" style="cursor: default; color: #aaa;">此目录为空</div>`;
                fileUl.appendChild(emptyLi);
            }
            
            itemLi.appendChild(itemRow);
            itemLi.appendChild(fileUl);
            tree.appendChild(itemLi);
        });
        container.appendChild(tree);
    }

    /**
     * 获取并渲染待批阅报告目录
     */
    async function fetchAndRenderStudentReports() {
        dirLoadingEl.classList.remove('hidden');
        directoryListEl.innerHTML = '';
        try {
            const response = await apiRequest(`${API_BASE_URL}/api/reports/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const directories = await response.json();
            createTreeView(directories, directoryListEl, true);
        } catch (error) {
            console.error('获取待批阅报告失败:', error);
            directoryListEl.innerHTML = `<p class="error">无法加载目录列表。</p>`;
        } finally {
            dirLoadingEl.classList.add('hidden');
        }
    }

    /**
     * 获取并渲染已批阅报告目录
     */
    async function fetchAndRenderGradedReports() {
        gradedLoadingEl.classList.remove('hidden');
        gradedListEl.innerHTML = '';
        try {
            const response = await apiRequest(`${API_BASE_URL}/api/graded-reports/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const directories = await response.json();
            createTreeView(directories, gradedListEl, false);
        } catch (error) {
            console.error('获取已批阅报告失败:', error);
            gradedListEl.innerHTML = `<p class="error">无法加载目录列表。</p>`;
        } finally {
            gradedLoadingEl.classList.add('hidden');
        }
    }

    /**
     * 获取并设置当前的评分标准
     */
    async function fetchAndSetCriteria() {
        try {
            const response = await apiRequest(`${API_BASE_URL}/api/criteria`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            criteriaInputEl.value = data.criteria;
            criteriaPreviewContentEl.innerHTML = marked.parse(data.criteria);
            document.getElementById('min-score').value = data.min_score;
            document.getElementById('max-score').value = data.max_score;
        } catch (error) {
            console.error('获取评分标准失败:', error);
        }
    }

    /**
     * 提交评分标准
     */
    async function handleCriteriaSubmit(event) {
        event.preventDefault();
        const criteria = criteriaInputEl.value;
        criteriaStatusEl.textContent = '保存中...';
        criteriaStatusEl.className = 'status-message';

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/criteria`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ criteria }),
            });
            if (!response.ok) throw new Error('保存失败');
            const data = await response.json();
            criteriaStatusEl.textContent = data.message;
            criteriaStatusEl.classList.add('success');
        } catch (error) {
            criteriaStatusEl.textContent = error.message;
            criteriaStatusEl.classList.add('error');
        } finally {
            setTimeout(() => {
                criteriaStatusEl.textContent = '';
                criteriaStatusEl.className = 'status-message';
            }, 3000);
        }
    }

    /**
     * 恢复默认评分标准
     */
    async function handleCriteriaReset() {
        if (!confirm('确定要恢复默认评分标准吗？当前修改将丢失。')) {
            return;
        }

        criteriaStatusEl.textContent = '恢复中...';
        criteriaStatusEl.className = 'status-message';

        try {
            const response = await fetch(`${API_BASE_URL}/api/criteria/reset`, {
                method: 'POST',
            });
            if (!response.ok) throw new Error('恢复失败');
            const data = await response.json();
            criteriaStatusEl.textContent = data.message;
            criteriaStatusEl.classList.add('success');
            
            const getResponse = await apiRequest(`${API_BASE_URL}/api/criteria`);
            if (getResponse.ok) {
                const getData = await getResponse.json();
                criteriaInputEl.value = getData.criteria;
            }
        } catch (error) {
            criteriaStatusEl.textContent = error.message;
            criteriaStatusEl.classList.add('error');
        } finally {
            setTimeout(() => {
                criteriaStatusEl.textContent = '';
                criteriaStatusEl.className = 'status-message';
            }, 3000);
        }
    }

    /**
     * 保存用户配置（评分标准和分数范围）
     */
    async function handleSaveConfig() {
        const criteria = criteriaInputEl.value;
        const minScore = document.getElementById('min-score').value;
        const maxScore = document.getElementById('max-score').value;

        criteriaStatusEl.textContent = '保存配置中...';
        criteriaStatusEl.className = 'status-message';

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/criteria`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    criteria,
                    min_score: parseInt(minScore),
                    max_score: parseInt(maxScore)
                }),
            });
            if (!response.ok) throw new Error('保存配置失败');
            const data = await response.json();
            criteriaStatusEl.textContent = data.message;
            criteriaStatusEl.classList.add('success');
        } catch (error) {
            criteriaStatusEl.textContent = error.message;
            criteriaStatusEl.classList.add('error');
        } finally {
            setTimeout(() => {
                criteriaStatusEl.textContent = '';
                criteriaStatusEl.className = 'status-message';
            }, 3000);
        }
    }

    /**
     * 加载用户配置（评分标准和分数范围）
     */
    async function handleLoadConfig() {
        criteriaStatusEl.textContent = '加载配置中...';
        criteriaStatusEl.className = 'status-message';

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/criteria`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            
            criteriaInputEl.value = data.criteria;
            criteriaPreviewContentEl.innerHTML = marked.parse(data.criteria);
            document.getElementById('min-score').value = data.min_score;
            document.getElementById('max-score').value = data.max_score;
            
            criteriaStatusEl.textContent = '配置加载成功';
            criteriaStatusEl.classList.add('success');
        } catch (error) {
            console.error('加载配置失败:', error);
            criteriaStatusEl.textContent = error.message;
            criteriaStatusEl.classList.add('error');
        } finally {
            setTimeout(() => {
                criteriaStatusEl.textContent = '';
                criteriaStatusEl.className = 'status-message';
            }, 3000);
        }
    }

    /**
     * 处理文件上传
     */
    async function handleFileUpload() {
        const file = fileInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        const originalBtnText = uploadBtn.textContent;
        uploadBtn.textContent = '上传中...';
        uploadBtn.disabled = true;

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/upload`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '上传失败');
            }

            await fetchAndRenderStudentReports();
        } catch (error) {
            alert(`上传出错: ${error.message}`);
        } finally {
            uploadBtn.textContent = '上传文件';
            uploadBtn.disabled = false;
            fileInput.value = '';
        }
    }
    
    /**
     * 提交批阅任务
     */
    async function submitGrading() {
        if (!selectedDirectory) {
            alert("请先在左侧选择一个要批阅的目录。");
            return;
        }

        resultsContainerEl.classList.remove('hidden');
        resultsTitleEl.textContent = `批阅结果: ${selectedDirectory}`;
        reportListEl.innerHTML = '';
        reportLoadingEl.classList.remove('hidden');
        csvDownloadLinkEl.classList.add('hidden');
        
        submitGradingBtn.textContent = '正在批阅...';
        submitGradingBtn.disabled = true;

        // 获取选中的大模型
            const modelSelect = document.getElementById('model-select');
            const selectedModel = modelSelect.value;
            
            const payload = {
                directory: selectedDirectory,
                add_markings: addMarkingsCheckbox.checked,
                ai_review: aiReviewCheckbox.checked,
                auto_grading: autoGradingCheckbox.checked,
                selected_model: selectedModel
            };

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/annotate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                 const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            
            renderReportResults(result.documents);
            
            // 在所有文件批注完成后，刷新两个报告列表
            await fetchAndRenderGradedReports();
            await fetchAndRenderStudentReports();

            // 处理不合格报告CSV
            if (result.failed_count > 0 && result.csv_file) {
                csvDownloadLinkEl.href = `${API_BASE_URL}/api/download-csv?file_path=${encodeURIComponent(result.csv_file)}`;
                csvDownloadLinkEl.textContent = '下载不合格报告 (CSV)';
                csvDownloadLinkEl.classList.remove('hidden');
            }
            
            // 处理合格报告CSV
            if (result.qualified_csv_file) {
                const qualifiedCsvLink = document.createElement('a');
                qualifiedCsvLink.className = 'button';
                qualifiedCsvLink.href = `${API_BASE_URL}/api/download-csv?file_path=${encodeURIComponent(result.qualified_csv_file)}`;
                qualifiedCsvLink.textContent = '下载合格报告成绩 (CSV)';
                qualifiedCsvLink.download = '';
                qualifiedCsvLink.style.marginLeft = '10px';
                
                // 添加到结果容器
                const header = resultsContainerEl.querySelector('.results-header');
                if (header) {
                    header.appendChild(qualifiedCsvLink);
                }
            }

            // 所有文件批注完成后，自动关闭结果弹出窗口
            setTimeout(() => {
                resultsContainerEl.classList.add('hidden');
            }, 3000);

        } catch (error) {
            console.error('批阅时出错:', error);
            reportListEl.innerHTML = `<p class="error">批阅失败: ${error.message}</p>`;
        } finally {
            reportLoadingEl.classList.add('hidden');
            submitGradingBtn.textContent = '开始批阅选定目录';
            submitGradingBtn.disabled = false;
        }
    }


    /**
     * 渲染报告评估结果
     */
    function renderReportResults(reports) {
        reportListEl.innerHTML = '';
        if (!reports || reports.length === 0) {
            reportListEl.innerHTML = '<p>目录中没有找到可处理的报告。</p>';
            return;
        }

        reports.forEach(report => {
            const isQualified = report.status === '合格';
            const card = document.createElement('div');
            card.className = `report-card ${isQualified ? 'qualified' : 'unqualified'}`;
            
            // 确保正确显示中文字符，防止乱码
            const safeComments = report.comments ? report.comments.replace(/[<>&]/g, (match) => {
                const escapeMap = {'<': '&lt;', '>': '&gt;', '&': '&amp;'};
                return escapeMap[match];
            }) : '无';
            
            card.innerHTML = `
                <h3>
                    <span>${report.filename}</span>
                    <span class="score ${isQualified ? 'qualified' : 'unqualified'}">${report.score}分</span>
                </h3>
                <div class="details">
                    <p><strong>状态:</strong> ${report.status}</p>
                    <p><strong>文件类型:</strong> ${report.type}</p>
                    <p><strong>文件大小:</strong> ${(report.size / 1024).toFixed(2)} KB</p>
                </div>
                <div class="comments">
                    <strong>AI评语:</strong>
                    <p>${safeComments}</p>
                </div>
            `;
            reportListEl.appendChild(card);
        });
    }

    /**
     * 下载已批阅目录
     */
    async function downloadGradedDirectory(directoryName) {
        const button = document.querySelector(`.download-btn[data-download-dir="${directoryName}"]`);
        const originalText = button.innerHTML;
        button.innerHTML = '打包中...';
        button.disabled = true;

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/download-graded?directory=${encodeURIComponent(directoryName)}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '下载失败');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${directoryName}_graded.zip`; 
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (error) {
            alert(`下载失败: ${error.message}`);
        } finally {
            button.innerHTML = '下载';
            button.disabled = false;
        }
    }

    /**
     * 删除待批阅报告目录
     */
    async function deleteReportDirectory(directoryName) {
        if (!confirm(`确定要删除目录 "${directoryName}" 吗？此操作不可撤销。`)) {
            return;
        }

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/reports/${encodeURIComponent(directoryName)}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '删除失败');
            }

            // 重新加载待批阅报告列表
            await fetchAndRenderStudentReports();
            alert(`目录 "${directoryName}" 已成功删除`);
        } catch (error) {
            console.error('删除待批阅报告目录失败:', error);
            alert(`删除失败: ${error.message}`);
        }
    }

    /**
     * 删除已批阅报告目录
     */
    async function deleteGradedDirectory(directoryName) {
        if (!confirm(`确定要删除目录 "${directoryName}" 吗？此操作不可撤销。`)) {
            return;
        }

        try {
            const response = await apiRequest(`${API_BASE_URL}/api/graded-reports/${encodeURIComponent(directoryName)}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '删除失败');
            }

            // 重新加载已批阅报告列表
            await fetchAndRenderGradedReports();
            alert(`目录 "${directoryName}" 已成功删除`);
        } catch (error) {
            console.error('删除已批阅报告目录失败:', error);
            alert(`删除失败: ${error.message}`);
        }
    }

    // --- 全局事件委托 ---
    document.body.addEventListener('click', (event) => {
        const target = event.target;
        const row = target.closest('.tree-row');

        // 关闭结果弹窗
        if (target.classList.contains('close-results')) {
            resultsContainerEl.classList.add('hidden');
        }

        // 点击左侧面板中的目录行
        if (studentReportsPanel.contains(target) && row) {
            const li = row.parentElement;
            if (li.classList.contains('is-directory')) {
                // 切换展开/折叠
                li.classList.toggle('expanded');
                
                // 设置选中状态
                if (selectedDirectory !== li.dataset.directoryName) {
                     // 移除旧的选中
                    const currentSelected = studentReportsPanel.querySelector('.tree-item.selected');
                    if (currentSelected) {
                        currentSelected.classList.remove('selected');
                    }
                    // 添加新的选中
                    li.classList.add('selected');
                    selectedDirectory = li.dataset.directoryName;
                } else {
                    // 如果再次点击已选中的，则取消选中
                    li.classList.remove('selected');
                    selectedDirectory = null;
                }
            }
        }
        
        // 点击右侧面板中的目录行 (仅展开/折叠)
        if (gradedListEl.contains(target) && row) {
            const li = row.parentElement;
            if (li.classList.contains('is-directory')) {
                li.classList.toggle('expanded');
            }
        }

        // 点击下载按钮
        if (target.classList.contains('download-btn')) {
            const dirName = target.dataset.downloadDir;
            downloadGradedDirectory(dirName);
        }
        
        // 点击删除按钮（待批阅报告）
        if (target.classList.contains('delete-btn') && target.dataset.deleteType === 'student') {
            const dirName = target.dataset.deleteDir;
            deleteReportDirectory(dirName);
        }
        
        // 点击删除按钮（已批阅报告）
        if (target.classList.contains('delete-btn') && target.dataset.deleteType === 'graded') {
            const dirName = target.dataset.deleteDir;
            deleteGradedDirectory(dirName);
        }
    });

    // --- 独立事件监听 ---
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileUpload);
    criteriaFormEl.addEventListener('submit', handleCriteriaSubmit);
    document.getElementById('reset-criteria-btn').addEventListener('click', handleCriteriaReset);
    document.getElementById('save-config-btn').addEventListener('click', handleSaveConfig);
    document.getElementById('load-config-btn').addEventListener('click', handleLoadConfig);
    submitGradingBtn.addEventListener('click', submitGrading);

    // --- 批阅要求实时预览 ---
    criteriaInputEl.addEventListener('input', () => {
        const markdownText = criteriaInputEl.value;
        criteriaPreviewContentEl.innerHTML = marked.parse(markdownText);
    });

    // --- 标签切换功能 ---
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            button.classList.add('active');
            const targetPane = document.getElementById(`${tabId}-tab`);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        });
    });

    // --- 初始加载 ---
    fetchAndRenderStudentReports();
    fetchAndRenderGradedReports();
    fetchAndSetCriteria();
}); 