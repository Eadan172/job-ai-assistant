importScripts('outbox.js');

// 后台服务
console.log('招聘AI助手后台服务已启动');

const CONTENT_FILES = [
    'content-script/sites/common.js',
    'content-script/sites/boss.js',
    'content-script/sites/lagou.js',
    'content-script/sites/51job.js',
    'content-script/sites/zhaopin.js',
    'content-script/page-detector.js',
    'content-script/auto-capture.js',
    'content-script/content.js'
];

// 本地服务配置
const SERVER_CONFIG = {
    url: 'http://localhost:8000',
    timeout: 30000
};

// 监听来自 popup 和 content script 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('收到消息:', message && message.action);
    
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
        case 'enqueueJobEvent':
            enqueueJobEvent(message.event).then(sendResponse);
            return true;
        case 'requeueFailedEvents':
            outbox.requeueFailed().then(function () {
                return flushOutbox();
            }).then(sendResponse);
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
                files: CONTENT_FILES
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
    flushOutbox();
});

// 岗位历史默认长期保留。以前这里每小时删除 7 天前的记录。
// 重新加载扩展时清掉已经排上的闹钟，避免旧闹钟继续删数据。
chrome.alarms.clear('cleanup');

const outbox = self.JobAIOutbox.createOutbox({
    storage: self.JobAIOutbox.openIndexedDbStorage(),
    send: sendJobEvent,
    now: function () { return Date.now(); }
});

function sendJobEvent(record) {
    const controller = new AbortController();
    const timer = setTimeout(function () { controller.abort(); }, 15000);
    return fetch(SERVER_CONFIG.url + '/api/jobs/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(record.payload),
        signal: controller.signal
    }).then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (body) {
            if (!response.ok) {
                const error = new Error('HTTP_' + response.status);
                error.status = response.status;
                throw error;
            }
            const sessionId = body.data && body.data.session_id;
            if (sessionId) {
                chrome.storage.local.set({ activeBrowseSessionId: sessionId });
            }
            return body;
        });
    }).catch(function (error) {
        if (error && error.name === 'AbortError') {
            const timeout = new Error('TIMEOUT');
            timeout.name = 'AbortError';
            throw timeout;
        }
        throw error;
    }).finally(function () {
        clearTimeout(timer);
    });
}

function flushOutbox() {
    return outbox.flush().then(function (results) {
        (results || []).forEach(function (result) {
            if (result.status === 'SENT' && result.fingerprint) {
                console.log('[JobAI] JOB_FINGERPRINT_GENERATED', String(result.fingerprint).slice(0, 12));
                console.log('[JobAI] EVENT_SENT', result.id);
            }
        });
        armRetry(results);
        return { success: true, results: results };
    }).catch(function (error) {
        console.error('[JobAI] outbox flush failed', error && error.name);
        return { success: false, message: error && error.message };
    });
}

function armRetry(results) {
    const times = (results || []).map(function (result) {
        return result.nextRetryAt;
    }).filter(Boolean);
    if (!times.length) {
        return;
    }
    const delay = Math.max(0, Math.min.apply(null, times) - Date.now());
    setTimeout(flushOutbox, delay);
}

function enqueueJobEvent(event) {
    return outbox.enqueue(event).then(function () {
        console.log('[JobAI] EVENT_QUEUED', event.event_type);
        return flushOutbox();
    });
}

chrome.alarms.create('outbox-flush', { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener(function (alarm) {
    if (alarm.name === 'outbox-flush') {
        flushOutbox();
    }
});
flushOutbox();