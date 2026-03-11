// 后台服务
console.log('招聘AI助手后台服务已启动');

// 本地服务配置
const SERVER_CONFIG = {
    url: 'http://localhost:8000',
    timeout: 30000
};

// 监听来自 popup 和 content script 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('收到消息:', message);
    
    switch (message.action) {
        case 'saveJobs':
            saveJobs(message.jobs).then(sendResponse);
            return true;
        case 'getJobs':
            getJobs().then(sendResponse);
            return true;
        case 'analyzeResume':
            analyzeResume(message.data).then(sendResponse);
            return true;
        case 'optimizeResume':
            optimizeResume(message.data).then(sendResponse);
            return true;
        case 'chat':
            chat(message.data).then(sendResponse);
            return true;
        case 'testConnection':
            testConnection(message.data).then(sendResponse);
            return true;
        default:
            sendResponse({ success: false, message: '未知操作' });
    }
});

// 保存岗位
async function saveJobs(jobs) {
    try {
        const result = await chrome.storage.local.get('jobs');
        const existingJobs = result.jobs || [];
        const updatedJobs = [...existingJobs, ...jobs];
        
        // 去重
        const uniqueJobs = updatedJobs.filter((job, index, self) =>
            index === self.findIndex(j => j.title === job.title && j.company === job.company)
        );
        
        await chrome.storage.local.set({ jobs: uniqueJobs });
        
        return { success: true, count: uniqueJobs.length };
    } catch (error) {
        console.error('保存岗位失败:', error);
        return { success: false, message: error.message };
    }
}

// 获取岗位
async function getJobs() {
    try {
        const result = await chrome.storage.local.get('jobs');
        return { success: true, jobs: result.jobs || [] };
    } catch (error) {
        console.error('获取岗位失败:', error);
        return { success: false, message: error.message };
    }
}

// 分析简历
async function analyzeResume(data) {
    try {
        const response = await fetch(`${SERVER_CONFIG.url}/analyze-resume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('分析简历失败:', error);
        return { success: false, message: error.message };
    }
}

// 优化简历
async function optimizeResume(data) {
    try {
        const response = await fetch(`${SERVER_CONFIG.url}/optimize-resume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('优化简历失败:', error);
        return { success: false, message: error.message };
    }
}

// 聊天
async function chat(data) {
    try {
        const response = await fetch(`${SERVER_CONFIG.url}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('聊天失败:', error);
        return { success: false, message: error.message };
    }
}

// 测试连接
async function testConnection(data) {
    try {
        const response = await fetch(`${SERVER_CONFIG.url}/test-connection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('测试连接失败:', error);
        return { success: false, message: error.message };
    }
}

// 监听标签页更新
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        // 检查是否是招聘网站
        const recruitSites = ['zhipin.com', 'lagou.com', '51job.com', 'zhaopin.com', 'liepin.com'];
        const isRecruitSite = recruitSites.some(site => tab.url.includes(site));
        
        if (isRecruitSite) {
            // 注入 content script
            chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ['content-script/content.js']
            }).catch(error => {
                console.error('注入 content script 失败:', error);
            });
        }
    }
});

// 监听插件安装
chrome.runtime.onInstalled.addListener((details) => {
    console.log('插件安装或更新:', details);
    
    if (details.reason === 'install') {
        // 初始化默认设置
        chrome.storage.local.set({
            settings: {
                modelType: 'deepseek',
                apiKey: '',
                userName: '',
                userPhone: '',
                userEmail: ''
            },
            jobs: [],
            stats: {
                jobsCount: 0,
                resumesCount: 0
            }
        });
    }
});

// 监听浏览器启动
chrome.runtime.onStartup.addListener(() => {
    console.log('浏览器启动，初始化招聘AI助手');
});

// 定期清理过期数据
chrome.alarms.create('cleanup', { periodInMinutes: 60 });

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'cleanup') {
        cleanupOldData();
    }
});

// 清理过期数据
async function cleanupOldData() {
    try {
        const result = await chrome.storage.local.get('jobs');
        const jobs = result.jobs || [];
        
        // 只保留最近 7 天的数据
        const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
        const filteredJobs = jobs.filter(job => {
            const scrapeTime = new Date(job.scrapeTime).getTime();
            return scrapeTime > sevenDaysAgo;
        });
        
        if (filteredJobs.length !== jobs.length) {
            await chrome.storage.local.set({ jobs: filteredJobs });
            console.log(`清理了 ${jobs.length - filteredJobs.length} 个过期岗位`);
        }
    } catch (error) {
        console.error('清理数据失败:', error);
    }
}