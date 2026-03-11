// 防止重复加载
if (window.__RECRUIT_AI_LOADED__) {
    console.log('[招聘AI助手] Content Script 已加载，跳过重复注入');
} else {
    window.__RECRUIT_AI_LOADED__ = true;

// 版本标识
var CONTENT_SCRIPT_VERSION = 'V4.2 - 2024-03-12';
console.log('[招聘AI助手] ========== Content Script 加载 ==========');
console.log('[招聘AI助手] 版本:', CONTENT_SCRIPT_VERSION);

// 招聘网站配置
var SITE_CONFIG = {
    'zhipin.com': {
        name: 'Boss直聘',
        selectors: {
            jobList: 'ul.job-list-box, .job-list-box, .search-job-result, ul.recommend-list',
            jobItem: 'li.company-job-item, li.job-card-wrapper, li[class*="job-card"], .job-card-wrapper, .job-card-left, .job-card-box, li[data-index]',
            title: 'p.name, .job-name a, .job-title a, .job-name span, .job-title span, .job-name, .job-title, span[class*="job-name"], span[class*="job-title"]',
            company: '.company-name a, .company-text a, .company-name span, .company-text span, .company-name, .company-text, span[class*="company"], a.company-info-top',
            salary: '.salary span, .job-salary span, .salary, .job-salary, span[class*="salary"], span[class*="money"], .red',
            location: '.job-area span, .job-location span, .area span, .job-area, .area, span[class*="area"]',
            experience: '.tag-list li, .job-info span, ul.tag-list li, span[class*="experience"], li[class*="experience"]',
            education: '.tag-list li, .job-info span, ul.tag-list li, span[class*="education"], li[class*="education"]',
            description: '.job-desc, .job-detail-text, .job-desc-wrapper, .job-detail-section, div[class*="desc"]'
        }
    },
    'lagou.com': {
        name: '拉勾网',
        selectors: {
            jobList: '.position-list, .list_item_box, .position-list-box',
            jobItem: '.position-list-item, .item__10RTO, .list_item_box, .position-list-item',
            title: '.position-name, .position__10RTO, .p_top a, .position-name a',
            company: '.company-name, .company__10RTO, .company_name, .company-name a',
            salary: '.salary, .money__10RTO, .p_bot .money, .salary span',
            location: '.position-address, .address__10RTO, .p_bot .city, .position-address span',
            experience: '.position-demand span, .p_bot__10RTO li, .p_bot span, .position-demand li',
            education: '.position-demand span, .p_bot__10RTO li, .p_bot span, .position-demand li',
            description: '.position-desc, .job_bt__10RTO, .job_detail, .position-desc'
        }
    },
    '51job.com': {
        name: '前程无忧',
        selectors: {
            jobList: '.joblist, .el-table__body, .joblist, .joblist-box',
            jobItem: '.job-item, .el-table__row, .j_joblist, .job-item',
            title: '.job-name, .job-title, .j_joblist .t, .job-name a',
            company: '.company-name, .company, .j_joblist .er, .company-name a',
            salary: '.job-salary, .salary, .j_joblist .sal, .salary span',
            location: '.job-location, .area, .j_joblist .d, .job-location span',
            experience: '.job-attr span, .attr, .j_joblist .d span, .job-attr',
            education: '.job-attr span, .attr, .j_joblist .d span, .job-attr',
            description: '.job-desc, .desc, .j_joblist .desc, .job-desc'
        }
    },
    'zhaopin.com': {
        name: '智联招聘',
        selectors: {
            jobList: '.positionlist, .joblist, .joblist-box, .joblist-box',
            jobItem: '.positionlist-item, .job-item, .joblist-box__item, .job-item',
            title: '.position-title, .job-title, .jobinfo__top, .job-title a',
            company: '.company-name, .company, .companyinfo__top, .company-name a',
            salary: '.position-salary, .salary, .jobinfo__salary, .salary span',
            location: '.position-location, .area, .jobinfo__other, .position-location span',
            experience: '.position-require span, .attr, .jobinfo__other span, .position-require',
            education: '.position-require span, .attr, .jobinfo__other span, .position-require',
            description: '.position-desc, .desc, .jobinfo__detail, .position-desc'
        }
    }
};

// 检测当前网站
function detectCurrentSite() {
    var hostname = window.location.hostname;
    console.log('[招聘AI助手] 当前网站域名:', hostname);
    for (var domain in SITE_CONFIG) {
        if (hostname.includes(domain)) {
            console.log('[招聘AI助手] 匹配到招聘网站:', SITE_CONFIG[domain].name);
            return { domain: domain, config: SITE_CONFIG[domain] };
        }
    }
    console.log('[招聘AI助手] 未匹配到已知招聘网站');
    return null;
}

// 滚动页面以加载更多内容
function scrollToLoadMore(callback) {
    console.log('[招聘AI助手] 开始滚动加载更多内容...');
    var scrollCount = 0;
    var maxScrolls = 5;
    var scrollInterval = 800;
    
    function doScroll() {
        if (scrollCount >= maxScrolls) {
            console.log('[招聘AI助手] 滚动完成，共滚动 ' + scrollCount + ' 次');
            if (callback) callback();
            return;
        }
        
        window.scrollBy(0, 500);
        scrollCount++;
        console.log('[招聘AI助手] 滚动第 ' + scrollCount + ' 次');
        
        setTimeout(doScroll, scrollInterval);
    }
    
    doScroll();
}

// 点击"查看更多"按钮加载更多岗位（安全版本）
function clickViewMoreButtons(callback) {
    console.log('[招聘AI助手] 开始查找查看更多按钮...');
    
    var clickedCount = 0;
    var maxClicks = 2;
    var clickedButtons = [];
    
    function findAndClick() {
        if (clickedCount >= maxClicks) {
            console.log('[招聘AI助手] 查看更多按钮点击完成，共点击 ' + clickedCount + ' 次');
            setTimeout(function() {
                if (callback) callback();
            }, 1000);
            return;
        }
        
        var allLinks = document.querySelectorAll('a, button, span[class*="more"], div[class*="more"]');
        var foundButton = null;
        
        for (var i = 0; i < allLinks.length; i++) {
            var el = allLinks[i];
            var text = el.textContent.trim();
            var href = el.href || '';
            
            // 只点击不会跳转的按钮（没有href或href是javascript:void）
            var isSafeButton = (
                (text.includes('查看更多') || text.includes('加载更多') || text.includes('展开')) &&
                (!href || href.includes('javascript') || href === '' || href === '#')
            );
            
            // 检查是否已经点击过
            var alreadyClicked = clickedButtons.some(function(b) { return b === el; });
            
            if (isSafeButton && !alreadyClicked) {
                foundButton = el;
                break;
            }
        }
        
        if (foundButton) {
            console.log('[招聘AI助手] 找到安全按钮: "' + foundButton.textContent.trim() + '"');
            clickedButtons.push(foundButton);
            
            try {
                foundButton.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                setTimeout(function() {
                    try {
                        foundButton.click();
                        clickedCount++;
                        console.log('[招聘AI助手] 已点击按钮，等待加载...');
                        
                        setTimeout(findAndClick, 2000);
                    } catch (e) {
                        console.log('[招聘AI助手] 点击按钮失败:', e.message);
                        if (callback) callback();
                    }
                }, 500);
            } catch (e) {
                console.log('[招聘AI助手] 操作按钮失败:', e.message);
                if (callback) callback();
            }
        } else {
            console.log('[招聘AI助手] 未找到更多安全按钮');
            if (callback) callback();
        }
    }
    
    // 设置超时保护
    var timeout = setTimeout(function() {
        console.log('[招聘AI助手] 深度爬取超时，直接爬取当前页面');
        if (callback) callback();
    }, 15000);
    
    findAndClick();
}

// 深度爬取：滚动 + 点击查看更多 + 爬取
function deepScrapeJobs(callback) {
    console.log('[招聘AI助手] 开始深度爬取...');
    
    // 先滚动加载更多
    scrollToLoadMore(function() {
        // 再尝试点击查看更多
        clickViewMoreButtons(function() {
            // 最后爬取所有岗位
            var jobs = scrapeJobs();
            if (callback) callback(jobs);
        });
    });
}

// 获取所有文档（包括 iframe）
function getAllDocuments() {
    var docs = [document];
    
    try {
        var iframes = document.querySelectorAll('iframe');
        console.log('[招聘AI助手] 找到 ' + iframes.length + ' 个 iframe');
        
        for (var i = 0; i < iframes.length; i++) {
            try {
                var iframe = iframes[i];
                var iframeSrc = iframe.src || '';
                console.log('[招聘AI助手] iframe ' + (i + 1) + ' src:', iframeSrc);
                
                var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                if (iframeDoc && iframeDoc.body) {
                    docs.push(iframeDoc);
                    console.log('[招聘AI助手] 成功访问 iframe ' + (i + 1) + ', body内容长度:', iframeDoc.body.innerHTML.length);
                }
            } catch (e) {
                console.log('[招聘AI助手] 无法访问 iframe ' + (i + 1) + ': ' + e.message);
                if (e.name === 'SecurityError') {
                    console.log('[招聘AI助手] iframe ' + (i + 1) + ' 是跨域iframe，无法直接访问');
                }
            }
        }
    } catch (e) {
        console.error('[招聘AI助手] 获取 iframe 失败:', e);
    }
    
    return docs;
}

// 调试：打印页面DOM结构
function debugPageStructure(doc, docName) {
    console.log('[招聘AI助手] ===== 调试 ' + docName + ' DOM结构 =====');
    
    var allClasses = {};
    var allElements = doc.querySelectorAll('*');
    for (var i = 0; i < allElements.length && i < 500; i++) {
        var el = allElements[i];
        if (el.className && typeof el.className === 'string') {
            var classes = el.className.split(' ');
            for (var j = 0; j < classes.length; j++) {
                if (classes[j] && classes[j].length > 2) {
                    allClasses[classes[j]] = (allClasses[classes[j]] || 0) + 1;
                }
            }
        }
    }
    
    var sortedClasses = Object.entries(allClasses).sort(function(a, b) { return b[1] - a[1]; });
    console.log('[招聘AI助手] 最常见的class名称（前20个）:');
    for (var i = 0; i < 20 && i < sortedClasses.length; i++) {
        console.log('  ' + sortedClasses[i][0] + ': ' + sortedClasses[i][1] + ' 次');
    }
    
    var jobRelated = sortedClasses.filter(function(c) { 
        return c[0].includes('job') || c[0].includes('company') || c[0].includes('card') || c[0].includes('recommend');
    });
    console.log('[招聘AI助手] 与岗位相关的class:');
    for (var i = 0; i < jobRelated.length; i++) {
        console.log('  ' + jobRelated[i][0] + ': ' + jobRelated[i][1] + ' 次');
    }
}

// 岗位爬取主函数
function scrapeJobs() {
    console.log('[招聘AI助手] ========== 开始爬取岗位信息 ==========');
    
    var allJobs = [];
    var docs = getAllDocuments();
    
    console.log('[招聘AI助手] 将搜索 ' + docs.length + ' 个文档（主页面 + iframe）');
    
    for (var d = 0; d < docs.length; d++) {
        var doc = docs[d];
        var docName = d === 0 ? '主页面' : 'iframe ' + d;
        console.log('[招聘AI助手] 搜索文档: ' + docName);
        
        // 调试：打印DOM结构
        debugPageStructure(doc, docName);
        
        var siteInfo = detectCurrentSite();
        if (siteInfo) {
            var jobs = scrapeDocument(doc, siteInfo.config);
            console.log('[招聘AI助手] 从 ' + docName + ' 提取到 ' + jobs.length + ' 个岗位');
            allJobs = allJobs.concat(jobs);
        }
    }
    
    // 去重
    var uniqueJobs = [];
    var seenIds = {};
    for (var i = 0; i < allJobs.length; i++) {
        var job = allJobs[i];
        var key = job.title + '_' + job.company + '_' + (job.salary || '');
        if (!seenIds[key]) {
            seenIds[key] = true;
            uniqueJobs.push(job);
        }
    }
    
    console.log('[招聘AI助手] ✅ 总共爬取到 ' + uniqueJobs.length + ' 个不重复岗位');
    return uniqueJobs;
}

// 带滚动的爬取（异步）
function scrapeJobsWithScroll(callback) {
    console.log('[招聘AI助手] 开始带滚动的爬取...');
    scrollToLoadMore(function() {
        var jobs = scrapeJobs();
        if (callback) callback(jobs);
    });
}

// 从单个文档爬取岗位
function scrapeDocument(doc, config) {
    var jobs = [];
    var selectors = config.selectors;
    
    // 方法1: 使用配置的选择器
    var jobItemSelectors = selectors.jobItem.split(',').map(function(s) { return s.trim(); });
    var jobElements = [];
    
    for (var i = 0; i < jobItemSelectors.length; i++) {
        var selector = jobItemSelectors[i];
        var elements = doc.querySelectorAll(selector);
        console.log('[招聘AI助手] 选择器 "' + selector + '" 找到 ' + elements.length + ' 个元素');
        if (elements.length > 0) {
            jobElements = elements;
            break;
        }
    }
    
    if (jobElements.length > 0) {
        console.log('[招聘AI助手] 共找到 ' + jobElements.length + ' 个岗位元素');
        
        for (var index = 0; index < jobElements.length; index++) {
            try {
                var job = extractJobInfo(jobElements[index], selectors);
                if (job && job.title && job.company) {
                    job.id = 'job_' + Date.now() + '_' + index;
                    job.source = config.name;
                    job.url = window.location.href;
                    job.scrapeTime = new Date().toISOString();
                    jobs.push(job);
                }
            } catch (error) {
                console.error('[招聘AI助手] 提取岗位信息失败:', error);
            }
        }
    }
    
    // 方法2: Boss直聘专用爬取
    if (jobs.length === 0 && window.location.hostname.includes('zhipin.com')) {
        jobs = scrapeBossZhipin(doc);
    }
    
    // 方法3: 通用爬取
    if (jobs.length === 0) {
        jobs = scrapeGeneric(doc);
    }
    
    return jobs;
}

// Boss直聘专用爬取 - 支持公司卡片多岗位 + 热招职位
function scrapeBossZhipin(doc) {
    console.log('[招聘AI助手] 使用Boss直聘专用爬取方法 V4');
    var jobs = [];
    
    // 方法1: 首页推荐 - li.company-job-item 模式
    var jobItems = doc.querySelectorAll('li.company-job-item');
    console.log('[招聘AI助手] 找到 ' + jobItems.length + ' 个 li.company-job-item 岗位');
    
    if (jobItems.length > 0) {
        for (var i = 0; i < jobItems.length; i++) {
            try {
                var jobItem = jobItems[i];
                var job = {};
                
                var nameEl = jobItem.querySelector('p.name');
                if (nameEl) {
                    job.title = nameEl.textContent.trim();
                }
                
                var linkEl = jobItem.querySelector('a.job-info, a[href*="job_detail"]');
                if (linkEl) {
                    job.jobUrl = linkEl.href;
                }
                
                var salaryEl = jobItem.querySelector('.salary, .red, span[class*="salary"]');
                if (salaryEl) {
                    job.salary = salaryEl.textContent.trim();
                }
                
                var companyName = '';
                var prevLi = jobItem.previousElementSibling;
                while (prevLi && !companyName) {
                    var companyLink = prevLi.querySelector('a.company-info-top, [class*="company-info"]');
                    if (companyLink) {
                        var imgEl = companyLink.querySelector('img');
                        if (imgEl && imgEl.alt) {
                            companyName = imgEl.alt;
                        } else {
                            companyName = companyLink.textContent.trim().substring(0, 50);
                        }
                        break;
                    }
                    prevLi = prevLi.previousElementSibling;
                }
                
                if (!companyName) {
                    var parent = jobItem.parentElement;
                    for (var p = 0; p < 5 && parent; p++) {
                        var companyEl = parent.querySelector('a.company-info-top, [class*="company-name"]');
                        if (companyEl) {
                            var imgEl = companyEl.querySelector('img');
                            if (imgEl && imgEl.alt) {
                                companyName = imgEl.alt;
                            } else {
                                companyName = companyEl.textContent.trim().substring(0, 50);
                            }
                            break;
                        }
                        parent = parent.parentElement;
                    }
                }
                
                job.company = companyName || '未知公司';
                
                if (job.title) {
                    job.id = 'job_' + Date.now() + '_' + jobs.length;
                    job.source = 'Boss直聘-推荐';
                    job.url = window.location.href;
                    job.scrapeTime = new Date().toISOString();
                    if (!job.salary) job.salary = '薪资面议';
                    jobs.push(job);
                }
            } catch (e) {
                console.error('[招聘AI助手] 提取岗位失败:', e);
            }
        }
    }
    
    // 方法2: 热招职位 - 搜索结果页模式
    console.log('[招聘AI助手] 开始爬取热招职位...');
    
    var hotJobSelectors = [
        // 搜索结果页
        '.job-card-wrapper',
        '.job-card-left', 
        '.job-card-box',
        'li.job-card-wrapper',
        '[class*="job-card-wrapper"]',
        // 热招职位区域
        '.hot-job-list li',
        '.hot-list li',
        '[class*="hot-job"] li',
        // 通用岗位列表
        '.search-job-result li',
        '.job-list-box li',
        '.job-list li',
        // 其他可能的容器
        'ul[class*="job"] li',
        'div[class*="job-list"] li'
    ];
    
    for (var s = 0; s < hotJobSelectors.length; s++) {
        var hotJobs = doc.querySelectorAll(hotJobSelectors[s]);
        if (hotJobs.length > 0) {
            console.log('[招聘AI助手] 热招职位选择器 "' + hotJobSelectors[s] + '" 找到 ' + hotJobs.length + ' 个岗位');
            
            for (var i = 0; i < hotJobs.length; i++) {
                try {
                    var job = extractBossJobFromElement(hotJobs[i], '');
                    if (job && job.title && job.company) {
                        job.id = 'job_' + Date.now() + '_' + jobs.length;
                        job.source = 'Boss直聘-热招';
                        job.url = window.location.href;
                        job.scrapeTime = new Date().toISOString();
                        if (!job.salary) job.salary = '薪资面议';
                        
                        var isDuplicate = jobs.some(function(j) {
                            return j.title === job.title && j.company === job.company;
                        });
                        if (!isDuplicate) {
                            jobs.push(job);
                        }
                    }
                } catch (e) {
                    console.error('[招聘AI助手] 提取热招岗位失败:', e);
                }
            }
        }
    }
    
    // 方法2.5: 查找所有包含岗位信息的链接
    console.log('[招聘AI助手] 查找岗位详情链接...');
    var jobLinks = doc.querySelectorAll('a[href*="job_detail"], a[href*="/job/"]');
    console.log('[招聘AI助手] 找到 ' + jobLinks.length + ' 个岗位链接');
    
    for (var i = 0; i < jobLinks.length; i++) {
        try {
            var link = jobLinks[i];
            var parent = link.closest('li, div[class*="job"], div[class*="card"]');
            if (parent) {
                var job = extractBossJobFromElement(parent, '');
                if (job && job.title) {
                    job.jobUrl = link.href;
                    job.id = 'job_' + Date.now() + '_' + jobs.length;
                    job.source = 'Boss直聘-链接';
                    job.url = window.location.href;
                    job.scrapeTime = new Date().toISOString();
                    if (!job.salary) job.salary = '薪资面议';
                    if (!job.company) job.company = '未知公司';
                    
                    var isDuplicate = jobs.some(function(j) {
                        return j.title === job.title && j.company === job.company;
                    });
                    if (!isDuplicate) {
                        jobs.push(job);
                    }
                }
            }
        } catch (e) {
            console.error('[招聘AI助手] 从链接提取岗位失败:', e);
        }
    }
    
    // 方法3: 通用 li 遍历（兜底）
    if (jobs.length === 0) {
        console.log('[招聘AI助手] 尝试通用 li 遍历模式');
        var allLi = doc.querySelectorAll('li');
        console.log('[招聘AI助手] 找到 ' + allLi.length + ' 个 li 元素');
        
        for (var i = 0; i < allLi.length; i++) {
            var li = allLi[i];
            var hasJobName = li.querySelector('p.name, [class*="job-name"], [class*="job-title"], .job-name, .job-title');
            var hasCompany = li.querySelector('[class*="company"], .company-name, .company-text');
            
            if (hasJobName && hasCompany) {
                try {
                    var job = extractBossJobFromElement(li, '');
                    if (job && job.title && job.company) {
                        job.id = 'job_' + Date.now() + '_' + jobs.length;
                        job.source = 'Boss直聘';
                        job.url = window.location.href;
                        job.scrapeTime = new Date().toISOString();
                        if (!job.salary) job.salary = '薪资面议';
                        jobs.push(job);
                    }
                } catch (e) {
                    console.error('[招聘AI助手] 提取岗位失败:', e);
                }
            }
        }
    }
    
    console.log('[招聘AI助手] Boss直聘总共爬取到 ' + jobs.length + ' 个岗位');
    return jobs;
}

// 从元素提取Boss直聘岗位信息
function extractBossJobFromElement(el, defaultCompany) {
    var job = {};
    
    // 提取标题
    var titleSelectors = [
        'p.name',
        '[class*="job-name"] a', '[class*="job-title"] a',
        '.job-name a', '.job-title a',
        '[class*="job-name"]', '[class*="job-title"]',
        '.job-name', '.job-title',
        'a[href*="/job_detail"]', 'a'
    ];
    for (var i = 0; i < titleSelectors.length; i++) {
        var titleEl = el.querySelector(titleSelectors[i]);
        if (titleEl && titleEl.textContent.trim()) {
            var text = titleEl.textContent.trim();
            if (text.length > 2 && text.length < 100) {
                job.title = text;
                break;
            }
        }
    }
    
    // 提取公司
    var companySelectors = [
        'a.company-info-top',
        '[class*="company-name"] a', '[class*="company-text"] a',
        '.company-name a', '.company-text a',
        '[class*="company-name"]', '[class*="company-text"]',
        '.company-name', '.company-text'
    ];
    for (var i = 0; i < companySelectors.length; i++) {
        var companyEl = el.querySelector(companySelectors[i]);
        if (companyEl) {
            // 尝试从img alt获取公司名
            var imgEl = companyEl.querySelector('img');
            if (imgEl && imgEl.alt) {
                job.company = imgEl.alt;
            } else {
                var text = companyEl.textContent.trim();
                if (text) {
                    job.company = text.substring(0, 50);
                }
            }
            if (job.company) break;
        }
    }
    if (!job.company && defaultCompany) {
        job.company = defaultCompany;
    }
    
    // 提取薪资
    var salarySelectors = [
        '[class*="salary"]', '[class*="money"]',
        '.salary', '.job-salary', '.red'
    ];
    for (var i = 0; i < salarySelectors.length; i++) {
        var salaryEl = el.querySelector(salarySelectors[i]);
        if (salaryEl) {
            var salaryText = salaryEl.textContent.trim();
            if (salaryText && (salaryText.includes('K') || salaryText.includes('k') || 
                salaryText.includes('万') || salaryText.includes('元') ||
                /\d+-\d+/.test(salaryText))) {
                job.salary = salaryText;
                break;
            }
        }
    }
    
    // 提取地点
    var areaSelectors = [
        '[class*="area"]', '[class*="location"]',
        '.job-area', '.area', '.city'
    ];
    for (var i = 0; i < areaSelectors.length; i++) {
        var areaEl = el.querySelector(areaSelectors[i]);
        if (areaEl) {
            var areaText = areaEl.textContent.trim();
            if (areaText && areaText.length < 20) {
                job.location = areaText;
                break;
            }
        }
    }
    
    // 提取标签（经验、学历）
    var tagEls = el.querySelectorAll('[class*="tag"] li, [class*="tag"] span, .tag-list li, .tag-list span, ul li');
    for (var t = 0; t < tagEls.length; t++) {
        var tagText = tagEls[t].textContent.trim();
        if (tagText.match(/\d+-\d+年|\d+年以上|应届|经验不限/)) {
            job.experience = tagText;
        }
        if (tagText.match(/本科|硕士|博士|大专|中专|高中|学历不限/)) {
            job.education = tagText;
        }
    }
    
    // 获取链接
    var linkEl = el.querySelector('a[href*="job"], a[href*="/job_detail"], a');
    if (linkEl) {
        job.jobUrl = linkEl.href;
    }
    
    return job;
}

// 通用爬取
function scrapeGeneric(doc) {
    console.log('[招聘AI助手] 使用通用爬取方法');
    var jobs = [];
    
    var selectors = [
        { container: 'li.company-job-item', title: 'p.name', company: 'a.company-info-top' },
        { container: 'li', title: 'p.name, [class*="job-name"], [class*="job-title"], [class*="name"]', company: '[class*="company"]' },
        { container: '[class*="job"]', title: '[class*="title"], [class*="name"], h3, h4', company: '[class*="company"]' },
        { container: '[class*="position"]', title: '[class*="title"], [class*="name"], h3, h4', company: '[class*="company"]' }
    ];
    
    for (var s = 0; s < selectors.length; s++) {
        var selector = selectors[s];
        var containers = doc.querySelectorAll(selector.container);
        
        if (containers.length > 0) {
            for (var index = 0; index < containers.length; index++) {
                try {
                    var container = containers[index];
                    var titleEl = container.querySelector(selector.title);
                    var companyEl = container.querySelector(selector.company);
                    
                    if (titleEl && companyEl) {
                        var title = titleEl.textContent.trim();
                        var company = companyEl.textContent.trim();
                        
                        if (title && company && title.length > 2 && company.length > 2) {
                            jobs.push({
                                id: 'job_' + Date.now() + '_' + index,
                                title: title,
                                company: company,
                                salary: '薪资面议',
                                location: '',
                                description: container.textContent.trim().substring(0, 500),
                                source: '通用爬取',
                                url: window.location.href,
                                jobUrl: container.querySelector('a') ? container.querySelector('a').href : '',
                                scrapeTime: new Date().toISOString()
                            });
                        }
                    }
                } catch (error) {
                    console.error('[招聘AI助手] 通用爬取错误:', error);
                }
            }
            
            if (jobs.length > 0) {
                return jobs;
            }
        }
    }
    
    return jobs;
}

// 提取岗位信息
function extractJobInfo(element, selectors) {
    var job = {};
    
    var titleSelectors = selectors.title.split(',').map(function(s) { return s.trim(); });
    for (var i = 0; i < titleSelectors.length; i++) {
        var titleEl = element.querySelector(titleSelectors[i]);
        if (titleEl && titleEl.textContent.trim()) {
            job.title = titleEl.textContent.trim();
            break;
        }
    }
    
    var companySelectors = selectors.company.split(',').map(function(s) { return s.trim(); });
    for (var i = 0; i < companySelectors.length; i++) {
        var companyEl = element.querySelector(companySelectors[i]);
        if (companyEl && companyEl.textContent.trim()) {
            job.company = companyEl.textContent.trim();
            break;
        }
    }
    
    var salarySelectors = selectors.salary.split(',').map(function(s) { return s.trim(); });
    for (var i = 0; i < salarySelectors.length; i++) {
        var salaryEl = element.querySelector(salarySelectors[i]);
        if (salaryEl && salaryEl.textContent.trim()) {
            var salaryText = salaryEl.textContent.trim();
            if (salaryText.includes('K') || salaryText.includes('k') || 
                salaryText.includes('万') || salaryText.includes('元') ||
                /\d+-\d+/.test(salaryText) || /\d+/.test(salaryText)) {
                job.salary = salaryText;
                break;
            }
        }
    }
    if (!job.salary) job.salary = '薪资面议';
    
    var locationSelectors = selectors.location.split(',').map(function(s) { return s.trim(); });
    for (var i = 0; i < locationSelectors.length; i++) {
        var locationEl = element.querySelector(locationSelectors[i]);
        if (locationEl && locationEl.textContent.trim()) {
            var locationText = locationEl.textContent.trim();
            if (locationText.length < 20) {
                job.location = locationText;
                break;
            }
        }
    }
    
    var linkEl = element.querySelector('a[href*="job"], a[href*="position"], a');
    job.jobUrl = linkEl ? linkEl.href : '';
    
    return job;
}

// 监听消息
chrome.runtime.onMessage.addListener(function(message, sender, sendResponse) {
    console.log('[招聘AI助手] Content script 收到消息:', message);
    
    if (message.action === 'scrapeJobs') {
        console.log('[招聘AI助手] 开始执行爬取任务');
        var jobs = scrapeJobs();
        console.log('[招聘AI助手] 爬取完成，返回结果:', jobs.length, '个岗位');
        sendResponse({ success: true, jobs: jobs, count: jobs.length });
    } else if (message.action === 'scrapeJobsWithScroll') {
        console.log('[招聘AI助手] 开始执行带滚动的爬取任务');
        scrapeJobsWithScroll(function(jobs) {
            console.log('[招聘AI助手] 带滚动爬取完成，返回结果:', jobs.length, '个岗位');
            sendResponse({ success: true, jobs: jobs, count: jobs.length });
        });
        return true;
    } else if (message.action === 'deepScrapeJobs') {
        console.log('[招聘AI助手] 开始执行深度爬取任务');
        deepScrapeJobs(function(jobs) {
            console.log('[招聘AI助手] 深度爬取完成，返回结果:', jobs.length, '个岗位');
            sendResponse({ success: true, jobs: jobs, count: jobs.length });
        });
        return true;
    } else if (message.action === 'getPageInfo') {
        var siteInfo = detectCurrentSite();
        sendResponse({
            success: true,
            site: siteInfo ? siteInfo.config.name : '未知网站',
            url: window.location.href,
            title: document.title
        });
    } else if (message.action === 'debugDOM') {
        console.log('[招聘AI助手] 执行DOM调试');
        var docs = getAllDocuments();
        for (var d = 0; d < docs.length; d++) {
            debugPageStructure(docs[d], d === 0 ? '主页面' : 'iframe ' + d);
        }
        sendResponse({ success: true, message: 'DOM结构已打印到控制台' });
    } else {
        sendResponse({ success: false, message: '未知操作' });
    }
    
    return true;
});

// 添加浮动按钮
function addFloatingButtons() {
    if (document.getElementById('recruit-ai-float-btn')) {
        return;
    }
    
    var siteInfo = detectCurrentSite();
    if (!siteInfo) {
        console.log('[招聘AI助手] 非招聘网站，不添加浮动按钮');
        return;
    }
    
    console.log('[招聘AI助手] 添加浮动按钮 V4.0');
    
    var container = document.createElement('div');
    container.id = 'recruit-ai-float-btn';
    container.style.cssText = 'position: fixed; right: 20px; bottom: 100px; z-index: 9999; display: flex; flex-direction: column; gap: 8px;';
    
    // 快速爬取按钮
    var scrapeBtn = document.createElement('button');
    scrapeBtn.textContent = '📋 快速爬取';
    scrapeBtn.style.cssText = 'padding: 10px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 25px; cursor: pointer; font-size: 14px; font-weight: bold; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);';
    
    scrapeBtn.addEventListener('click', function() {
        scrapeBtn.textContent = '⏳ 爬取中...';
        var jobs = scrapeJobs();
        
        chrome.runtime.sendMessage({
            action: 'saveJobs',
            jobs: jobs
        }, function(response) {
            if (response && response.success) {
                scrapeBtn.textContent = '✅ ' + jobs.length + ' 个岗位';
                setTimeout(function() {
                    scrapeBtn.textContent = '📋 快速爬取';
                }, 2000);
            }
        });
    });
    
    // 深度爬取按钮
    var deepScrapeBtn = document.createElement('button');
    deepScrapeBtn.textContent = '🚀 深度爬取';
    deepScrapeBtn.style.cssText = 'padding: 10px 20px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border: none; border-radius: 25px; cursor: pointer; font-size: 14px; font-weight: bold; box-shadow: 0 4px 15px rgba(240, 147, 251, 0.4);';
    
    deepScrapeBtn.addEventListener('click', function() {
        deepScrapeBtn.textContent = '⏳ 深度爬取中...';
        deepScrapeJobs(function(jobs) {
            chrome.runtime.sendMessage({
                action: 'saveJobs',
                jobs: jobs
            }, function(response) {
                if (response && response.success) {
                    deepScrapeBtn.textContent = '✅ ' + jobs.length + ' 个岗位';
                    setTimeout(function() {
                        deepScrapeBtn.textContent = '🚀 深度爬取';
                    }, 2000);
                }
            });
        });
    });
    
    // 调试按钮
    var debugBtn = document.createElement('button');
    debugBtn.textContent = '🔍 调试';
    debugBtn.style.cssText = 'padding: 8px 16px; background: #f0f0f0; color: #333; border: 1px solid #ccc; border-radius: 20px; cursor: pointer; font-size: 12px;';
    
    debugBtn.addEventListener('click', function() {
        debugBtn.textContent = '⏳ 调试中...';
        var docs = getAllDocuments();
        for (var d = 0; d < docs.length; d++) {
            debugPageStructure(docs[d], d === 0 ? '主页面' : 'iframe ' + d);
        }
        debugBtn.textContent = '✅ 已打印';
        setTimeout(function() {
            debugBtn.textContent = '🔍 调试';
        }, 2000);
    });
    
    container.appendChild(scrapeBtn);
    container.appendChild(deepScrapeBtn);
    container.appendChild(debugBtn);
    document.body.appendChild(container);
    console.log('[招聘AI助手] 浮动按钮添加完成');
}

// 监听 URL 变化（SPA 路由）
var lastUrl = location.href;
new MutationObserver(function() {
    if (location.href !== lastUrl) {
        lastUrl = location.href;
        console.log('[招聘AI助手] URL 变化:', lastUrl);
        setTimeout(function() {
            addFloatingButtons();
        }, 1000);
    }
}).observe(document, { subtree: true, childList: true });

// 初始化
function init() {
    console.log('[招聘AI助手] ========== Content Script 已加载 ==========');
    console.log('[招聘AI助手] 当前页面:', window.location.href);
    console.log('[招聘AI助手] 页面标题:', document.title);
    
    detectCurrentSite();
    
    setTimeout(function() {
        addFloatingButtons();
    }, 1000);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

} // 结束防止重复加载