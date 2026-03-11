// 配置
const CONFIG = {
    serverUrl: 'http://localhost:8000',
    maxJobs: 100
};

// 状态管理
let state = {
    jobs: [],
    jobsAnalysis: '',  // AI岗位分析结果
    resume: null,
    analysis: null,
    settings: {
        modelType: 'deepseek',
        apiKey: '',
        userName: '',
        userPhone: '',
        userEmail: ''
    },
    stats: {
        jobsCount: 0,
        resumesCount: 0
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    console.log('========== 招聘AI助手 Popup 初始化 ==========');
    initTabs();
    initJobScraping();
    initResumeUpload();
    initChat();
    initSettings();
    loadSavedData();
    checkServerStatus();
    getCurrentPageInfo();
});

// 标签页切换
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-tab');
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// 检查服务器状态
async function checkServerStatus() {
    const statusEl = document.getElementById('server-status');
    try {
        const response = await fetch(`${CONFIG.serverUrl}/status`);
        if (response.ok) {
            statusEl.textContent = '服务运行中';
            statusEl.parentElement.querySelector('.status-dot').style.background = '#4CAF50';
        } else {
            statusEl.textContent = '服务异常';
            statusEl.parentElement.querySelector('.status-dot').style.background = '#ff6b6b';
        }
    } catch (error) {
        statusEl.textContent = '服务未启动';
        statusEl.parentElement.querySelector('.status-dot').style.background = '#ff6b6b';
    }
}

// 获取当前页面信息
async function getCurrentPageInfo() {
    const pageEl = document.getElementById('current-page');
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab) {
            chrome.tabs.sendMessage(tab.id, { action: 'getPageInfo' }, (response) => {
                if (chrome.runtime.lastError) {
                    pageEl.textContent = '无法获取页面信息';
                    return;
                }
                if (response && response.success) {
                    pageEl.innerHTML = `<div style="padding: 8px; background: #f5f5f5; border-radius: 4px;"><div style="font-weight: 600;">${response.site}</div><div style="font-size: 12px; color: #666; margin-top: 4px;">${response.title}</div></div>`;
                }
            });
        }
    } catch (error) {
        pageEl.textContent = '获取页面信息失败';
    }
}

// 初始化岗位爬取
function initJobScraping() {
    const scrapeBtn = document.getElementById('scrape-jobs');
    const exportBtn = document.getElementById('export-markdown');
    const clearBtn = document.getElementById('clear-jobs');
    const analyzeJobsBtn = document.getElementById('analyze-jobs');
    
    scrapeBtn.addEventListener('click', async () => {
        scrapeBtn.textContent = '⏳ 爬取中...';
        scrapeBtn.disabled = true;
        
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (!tab) throw new Error('未找到活动标签页');
            
            chrome.tabs.sendMessage(tab.id, { action: 'scrapeJobs' }, async (response) => {
                if (chrome.runtime.lastError) {
                    scrapeBtn.textContent = '🔍 爬取当前页面岗位';
                    scrapeBtn.disabled = false;
                    alert('爬取失败：' + chrome.runtime.lastError.message);
                    return;
                }
                
                if (response && response.success) {
                    state.jobs = response.jobs.slice(0, CONFIG.maxJobs);
                    await saveJobs();
                    displayJobs();
                    updateStats();
                    scrapeBtn.textContent = `✅ 已爬取 ${response.jobs.length} 个岗位`;
                    setTimeout(() => {
                        scrapeBtn.textContent = '🔍 爬取当前页面岗位';
                        scrapeBtn.disabled = false;
                    }, 2000);
                } else {
                    scrapeBtn.textContent = '🔍 爬取当前页面岗位';
                    scrapeBtn.disabled = false;
                    alert('爬取失败：' + (response?.message || '未知错误'));
                }
            });
        } catch (error) {
            scrapeBtn.textContent = '🔍 爬取当前页面岗位';
            scrapeBtn.disabled = false;
            alert('爬取失败：' + error.message);
        }
    });
    
    // AI分析岗位按钮
    analyzeJobsBtn.addEventListener('click', async () => {
        if (state.jobs.length === 0) {
            alert('请先爬取岗位数据');
            return;
        }
        if (!state.settings.apiKey) {
            alert('请先在设置中配置 API Key');
            return;
        }
        
        analyzeJobsBtn.textContent = '⏳ 分析中...';
        analyzeJobsBtn.disabled = true;
        
        try {
            const response = await fetch(`${CONFIG.serverUrl}/analyze-jobs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jobs: state.jobs,
                    model_type: state.settings.modelType,
                    api_key: state.settings.apiKey
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 保存分析结果
                state.jobsAnalysis = data.data.analysis;
                
                // 显示分析结果
                const jobList = document.getElementById('job-list');
                const analysisHtml = `
                    <div style="padding: 15px; background: #f0f7ff; border-radius: 8px; margin-bottom: 15px;">
                        <h4 style="margin: 0 0 10px 0; color: #1976d2;">📊 AI 岗位分析报告</h4>
                        <div style="white-space: pre-wrap; font-size: 13px; line-height: 1.6;">${data.data.analysis}</div>
                    </div>
                `;
                jobList.insertAdjacentHTML('afterbegin', analysisHtml);
                
                analyzeJobsBtn.textContent = '✅ 分析完成';
                setTimeout(() => {
                    analyzeJobsBtn.textContent = '🤖 AI 分析岗位';
                    analyzeJobsBtn.disabled = false;
                }, 2000);
            } else {
                throw new Error(data.message || data.detail || '分析失败');
            }
        } catch (error) {
            analyzeJobsBtn.textContent = '🤖 AI 分析岗位';
            analyzeJobsBtn.disabled = false;
            alert('分析失败：' + (error.message || error));
        }
    });
    
    exportBtn.addEventListener('click', () => {
        if (state.jobs.length === 0) {
            alert('暂无岗位数据可导出');
            return;
        }
        const markdown = generateMarkdown();
        downloadFile(markdown, `岗位分析报告_${Date.now()}.md`, 'text/markdown');
    });
    
    clearBtn.addEventListener('click', async () => {
        if (confirm('确定要清空所有岗位数据吗？')) {
            state.jobs = [];
            await saveJobs();
            displayJobs();
            updateStats();
        }
    });
}

// 显示岗位列表
function displayJobs() {
    const jobList = document.getElementById('job-list');
    const jobCount = document.getElementById('job-count');
    jobCount.textContent = state.jobs.length;
    
    if (state.jobs.length === 0) {
        jobList.innerHTML = '<div class="empty-state"><div class="icon">📭</div><div>暂无岗位数据</div></div>';
        return;
    }
    
    jobList.innerHTML = state.jobs.map((job, index) => `
        <div class="job-item" data-index="${index}">
            <h3>${job.title}</h3>
            <div class="company">${job.company}</div>
            <div class="salary">${job.salary}</div>
        </div>
    `).join('');
}

// 生成 Markdown
function generateMarkdown() {
    let markdown = `# 岗位分析报告\n\n**生成时间**: ${new Date().toLocaleString()}\n\n**岗位数量**: ${state.jobs.length}\n\n---\n\n`;
    
    // AI分析结果
    if (state.jobsAnalysis) {
        markdown += `## 📊 AI 岗位分析\n\n${state.jobsAnalysis}\n\n---\n\n`;
    }
    
    // 岗位列表
    markdown += `## 📋 岗位列表\n\n`;
    state.jobs.forEach((job, index) => {
        markdown += `### ${index + 1}. ${job.title}\n\n- **公司**: ${job.company}\n- **薪资**: ${job.salary}\n- **地点**: ${job.location || '未知'}\n- **来源**: ${job.source || '未知'}\n\n`;
    });
    return markdown;
}

// 初始化简历上传
function initResumeUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('resume-upload');
    const analyzeBtn = document.getElementById('analyze-resume');
    const optimizeBtn = document.getElementById('optimize-resume');
    const downloadBtn = document.getElementById('download-resume');
    
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.style.borderColor = '#667eea'; });
    uploadArea.addEventListener('dragleave', () => { uploadArea.style.borderColor = '#ddd'; });
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#ddd';
        if (e.dataTransfer.files[0]) handleResumeFile(e.dataTransfer.files[0]);
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) handleResumeFile(e.target.files[0]);
    });
    
    analyzeBtn.addEventListener('click', async () => {
        if (!state.resume) { alert('请先上传简历'); return; }
        if (!state.settings.apiKey) { alert('请先在设置中配置 API Key'); return; }
        
        analyzeBtn.textContent = '⏳ 分析中...';
        analyzeBtn.disabled = true;
        
        try {
            const response = await fetch(`${CONFIG.serverUrl}/analyze-resume`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    resume_text: state.resume.content,
                    model_type: state.settings.modelType,
                    api_key: state.settings.apiKey
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                state.analysis = data.data;
                displayAnalysis(data.data);
                analyzeBtn.textContent = '✅ 分析完成';
                setTimeout(() => { analyzeBtn.textContent = '🤖 AI 分析简历'; analyzeBtn.disabled = false; }, 2000);
            } else {
                throw new Error(data.message || data.detail || '分析失败');
            }
        } catch (error) {
            analyzeBtn.textContent = '🤖 AI 分析简历';
            analyzeBtn.disabled = false;
            alert('分析失败：' + (error.message || error));
        }
    });
    
    optimizeBtn.addEventListener('click', async () => {
        if (!state.resume) { alert('请先上传简历'); return; }
        if (!state.settings.apiKey) { alert('请先在设置中配置 API Key'); return; }
        
        optimizeBtn.textContent = '⏳ 优化中...';
        optimizeBtn.disabled = true;
        
        try {
            const response = await fetch(`${CONFIG.serverUrl}/optimize-resume`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    resume_text: state.resume.content,
                    model_type: state.settings.modelType,
                    api_key: state.settings.apiKey
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                displayAnalysis(data.data, true);
                optimizeBtn.textContent = '✅ 优化完成';
                setTimeout(() => { optimizeBtn.textContent = '✨ AI 优化简历'; optimizeBtn.disabled = false; }, 2000);
            } else {
                throw new Error(data.message || data.detail || '优化失败');
            }
        } catch (error) {
            optimizeBtn.textContent = '✨ AI 优化简历';
            optimizeBtn.disabled = false;
            alert('优化失败：' + (error.message || error));
        }
    });
    
    downloadBtn.addEventListener('click', () => {
        if (!state.analysis) { alert('请先分析简历'); return; }
        const report = generateAnalysisReport();
        downloadFile(report, `简历分析报告_${Date.now()}.md`, 'text/markdown');
    });
}

// 处理简历文件
async function handleResumeFile(file) {
    const uploadArea = document.getElementById('upload-area');
    uploadArea.innerHTML = '<div class="upload-icon">⏳</div><div class="upload-text">正在解析简历...</div>';
    
    try {
        let content = '';
        
        // TXT文件直接读取
        if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
            content = await readFileAsText(file);
        } else {
            // PDF/DOCX文件发送到后端解析
            content = await parseFileViaServer(file);
        }
        
        console.log('[Popup] 简历内容长度:', content.length);
        console.log('[Popup] 简历内容预览:', content.substring(0, 200));
        
        state.resume = { name: file.name, type: file.type, size: file.size, content: content };
        displayResumeInfo();
        uploadArea.innerHTML = `<div class="upload-icon">✅</div><div class="upload-text">${file.name}<br><small>点击重新上传</small></div>`;
    } catch (error) {
        uploadArea.innerHTML = '<div class="upload-icon">📄</div><div class="upload-text">点击或拖拽上传简历<br><small>支持 PDF / DOCX / TXT</small></div>';
        alert('解析简历失败：' + error.message);
    }
}

// 读取文本文件
function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = () => reject(new Error('读取文件失败'));
        reader.readAsText(file);
    });
}

// 通过后端解析文件
async function parseFileViaServer(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${CONFIG.serverUrl}/parse-resume`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error('服务器解析文件失败');
    }
    
    const data = await response.json();
    if (data.success && data.content) {
        return data.content;
    }
    
    throw new Error(data.message || '解析失败');
}

// 显示简历信息
function displayResumeInfo() {
    const infoSection = document.getElementById('resume-info');
    const basicInfo = document.getElementById('resume-basic-info');
    if (state.resume) {
        infoSection.style.display = 'block';
        basicInfo.innerHTML = `<div class="analysis-item"><label>文件名:</label><span>${state.resume.name}</span></div><div class="analysis-item"><label>文件大小:</label><span>${(state.resume.size / 1024).toFixed(2)} KB</span></div>`;
    }
}

// 显示分析结果
function displayAnalysis(data, isOptimize = false) {
    const section = document.getElementById('analysis-section');
    const result = document.getElementById('analysis-result');
    section.style.display = 'block';
    
    if (isOptimize) {
        result.innerHTML = `<h4>✨ AI 优化建议</h4><div style="white-space: pre-wrap; font-size: 13px; line-height: 1.6;">${data.raw_suggestions || '无优化建议'}</div>`;
    } else {
        let html = '<h4>📊 AI 简历分析报告</h4>';
        
        if (data.job_directions && data.job_directions.length > 0) {
            html += '<div style="margin: 15px 0; padding: 12px; background: #e3f2fd; border-radius: 8px;"><h5 style="margin: 0 0 10px 0; color: #1976d2;">🎯 推荐投递方向</h5>';
            data.job_directions.forEach(dir => {
                const levelColor = dir.match_level === '高' ? '#4caf50' : dir.match_level === '中' ? '#ff9800' : '#f44336';
                html += `<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 4px; border-left: 3px solid ${levelColor};"><strong>${dir.direction}</strong> <span style="color:${levelColor};font-size:12px;">[${dir.match_level}匹配]</span><div style="font-size:12px;color:#666;margin-top:4px;">${dir.reason}</div></div>`;
            });
            html += '</div>';
        }
        
        if (data.strengths && data.strengths.length > 0) {
            html += '<div style="margin: 15px 0; padding: 12px; background: #e8f5e9; border-radius: 8px;"><h5 style="margin: 0 0 10px 0; color: #2e7d32;">💪 核心优势</h5>';
            data.strengths.forEach(s => {
                html += `<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 4px;"><strong>✓ ${s.point}</strong>${s.evidence ? `<div style="font-size:12px;color:#666;">证据：${s.evidence}</div>` : ''}${s.how_to_use ? `<div style="font-size:12px;color:#2e7d32;">发挥建议：${s.how_to_use}</div>` : ''}</div>`;
            });
            html += '</div>';
        }
        
        if (data.weaknesses && data.weaknesses.length > 0) {
            html += '<div style="margin: 15px 0; padding: 12px; background: #fff3e0; border-radius: 8px;"><h5 style="margin: 0 0 10px 0; color: #e65100;">⚠️ 待提升方面</h5>';
            data.weaknesses.forEach(w => {
                html += `<div style="margin: 8px 0; padding: 8px; background: white; border-radius: 4px;"><strong>• ${w.point}</strong>${w.impact ? `<div style="font-size:12px;color:#666;">影响：${w.impact}</div>` : ''}${w.improvement ? `<div style="font-size:12px;color:#e65100;">改进：${w.improvement}</div>` : ''}</div>`;
            });
            html += '</div>';
        }
        
        if (data.raw_analysis) {
            html += '<details style="margin-top: 15px;"><summary style="cursor:pointer;padding:8px;background:#f5f5f5;border-radius:4px;">📄 查看完整分析报告</summary><div style="white-space: pre-wrap; font-size: 13px; line-height: 1.6; padding: 10px; background: #fafafa; border-radius: 4px; margin-top: 8px;">' + data.raw_analysis + '</div></details>';
        }
        
        result.innerHTML = html;
    }
}

// 生成分析报告
function generateAnalysisReport() {
    let report = `# 简历分析报告\n\n**生成时间**: ${new Date().toLocaleString()}\n\n**文件名**: ${state.resume?.name || '未知'}\n\n---\n\n`;
    if (state.analysis && state.analysis.raw_analysis) {
        report += `## AI 分析结果\n\n${state.analysis.raw_analysis}\n\n`;
    }
    return report;
}

// 初始化聊天
function initChat() {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-message');
    const chatMessages = document.getElementById('chat-messages');
    
    const sendMessage = async () => {
        const message = chatInput.value.trim();
        if (!message) return;
        
        addChatMessage(message, 'user');
        chatInput.value = '';
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'chat-message assistant loading';
        loadingDiv.textContent = '思考中...';
        chatMessages.appendChild(loadingDiv);
        
        try {
            const response = await fetch(`${CONFIG.serverUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    context: { jobs: state.jobs.slice(0, 5), resume: state.resume?.content, analysis: state.analysis },
                    model_type: state.settings.modelType,
                    api_key: state.settings.apiKey
                })
            });
            
            const data = await response.json();
            chatMessages.removeChild(loadingDiv);
            
            if (data.success) {
                addChatMessage(data.data.response, 'assistant');
            } else {
                addChatMessage('抱歉，遇到了问题：' + (data.message || data.detail || '未知错误'), 'assistant');
            }
        } catch (error) {
            chatMessages.removeChild(loadingDiv);
            addChatMessage('网络错误，请检查服务是否启动。', 'assistant');
        }
    };
    
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
    
    // 匹配分析 - 先询问意向岗位，需要简历
    document.getElementById('quick-match').addEventListener('click', () => {
        if (!state.resume || !state.resume.content) {
            alert('请先上传简历');
            return;
        }
        if (!state.settings.apiKey) {
            alert('请先在设置中配置 API Key');
            return;
        }
        
        const targetJobs = prompt('请输入您的意向岗位（多个岗位用逗号分隔）：\n例如：产品经理,项目经理,运营总监');
        if (!targetJobs) return;
        
        chatInput.value = `我的简历内容如下：
"""
${state.resume.content}
"""

请分析我的简历与以下意向岗位的匹配度：${targetJobs}

请给出：
1. 每个岗位的匹配度评分（0-100分）
2. 匹配的优势（结合简历中的具体经历）
3. 需要提升的方面
4. 具体的改进建议`;
        sendMessage();
    });
    
    // 模拟面试 - 先询问意向岗位，需要简历
    document.getElementById('quick-interview').addEventListener('click', () => {
        if (!state.resume || !state.resume.content) {
            alert('请先上传简历');
            return;
        }
        if (!state.settings.apiKey) {
            alert('请先在设置中配置 API Key');
            return;
        }
        
        const targetJob = prompt('请输入您想模拟面试的岗位：');
        if (!targetJob) return;
        
        chatInput.value = `我的简历内容如下：
"""
${state.resume.content}
"""

请针对"${targetJob}"岗位，为我模拟一次面试。包括：
1. 该岗位常见的面试问题（5-8个）
2. 每个问题的参考回答（结合我的简历经历）
3. 面试注意事项和技巧`;
        sendMessage();
    });
    
    // 薪资建议 - 先询问意向岗位，需要简历
    document.getElementById('quick-salary').addEventListener('click', () => {
        if (!state.resume || !state.resume.content) {
            alert('请先上传简历');
            return;
        }
        if (!state.settings.apiKey) {
            alert('请先在设置中配置 API Key');
            return;
        }
        
        const targetJob = prompt('请输入您想了解薪资的岗位：');
        if (!targetJob) return;
        
        chatInput.value = `我的简历内容如下：
"""
${state.resume.content}
"""

请针对"${targetJob}"岗位，给我薪资建议。包括：
1. 该岗位的市场薪资范围
2. 基于我的简历的建议薪资（结合我的经验、技能）
3. 薪资谈判策略和技巧`;
        sendMessage();
    });
}

// 添加聊天消息
function addChatMessage(text, type) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.innerHTML = text.replace(/\n/g, '<br>');
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 初始化设置
function initSettings() {
    const saveBtn = document.getElementById('save-settings');
    const testBtn = document.getElementById('test-connection');
    
    loadSettings();
    
    saveBtn.addEventListener('click', async () => {
        await saveSettingsToStorage();
    });
    
    testBtn.addEventListener('click', async () => {
        const modelType = document.getElementById('model-type').value;
        const apiKey = document.getElementById('api-key').value;
        
        if (!apiKey) { alert('请先输入 API Key'); return; }
        
        testBtn.textContent = '⏳ 测试中...';
        testBtn.disabled = true;
        
        try {
            const response = await fetch(`${CONFIG.serverUrl}/test-connection`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_type: modelType, api_key: apiKey })
            });
            
            const data = await response.json();
            
            if (data.success) {
                state.settings = {
                    modelType: modelType,
                    apiKey: apiKey,
                    userName: document.getElementById('user-name').value,
                    userPhone: document.getElementById('user-phone').value,
                    userEmail: document.getElementById('user-email').value
                };
                await chrome.storage.local.set({ settings: state.settings });
                testBtn.textContent = '✅ 连接成功';
                alert('连接成功！设置已自动保存。\n模型: ' + data.model_used);
                setTimeout(() => { testBtn.textContent = '🔌 测试连接'; testBtn.disabled = false; }, 2000);
            } else {
                testBtn.textContent = '❌ 连接失败';
                alert('连接测试失败：' + (data.message || '未知错误'));
                setTimeout(() => { testBtn.textContent = '🔌 测试连接'; testBtn.disabled = false; }, 2000);
            }
        } catch (error) {
            testBtn.textContent = '❌ 连接失败';
            alert('连接测试失败：' + error.message);
            setTimeout(() => { testBtn.textContent = '🔌 测试连接'; testBtn.disabled = false; }, 2000);
        }
    });
}

// 保存设置到存储
async function saveSettingsToStorage() {
    state.settings = {
        modelType: document.getElementById('model-type').value,
        apiKey: document.getElementById('api-key').value,
        userName: document.getElementById('user-name').value,
        userPhone: document.getElementById('user-phone').value,
        userEmail: document.getElementById('user-email').value
    };
    await chrome.storage.local.set({ settings: state.settings });
    console.log('[Popup] 设置已保存, API Key长度:', state.settings.apiKey ? state.settings.apiKey.length : 0);
    alert('设置已保存');
}

// 加载设置
async function loadSettings() {
    const data = await chrome.storage.local.get('settings');
    if (data.settings) {
        state.settings = data.settings;
        document.getElementById('model-type').value = state.settings.modelType || 'deepseek';
        document.getElementById('api-key').value = state.settings.apiKey || '';
        document.getElementById('user-name').value = state.settings.userName || '';
        document.getElementById('user-phone').value = state.settings.userPhone || '';
        document.getElementById('user-email').value = state.settings.userEmail || '';
        console.log('[Popup] 加载设置, API Key长度:', state.settings.apiKey ? state.settings.apiKey.length : 0);
    }
}

// 加载保存的数据
async function loadSavedData() {
    const data = await chrome.storage.local.get(['jobs', 'stats']);
    if (data.jobs) { state.jobs = data.jobs; displayJobs(); }
    if (data.stats) { state.stats = data.stats; updateStats(); }
}

// 保存岗位
async function saveJobs() {
    await chrome.storage.local.set({ jobs: state.jobs });
}

// 更新统计
function updateStats() {
    document.getElementById('stats-jobs').textContent = state.jobs.length;
    document.getElementById('stats-resumes').textContent = state.stats.resumesCount;
    chrome.storage.local.set({ stats: state.stats });
}

// 下载文件
function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
