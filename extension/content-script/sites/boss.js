(function (root) {
    if (!root.JobAISites && typeof require === 'function') {
        require('./common.js');
    }
    var sites = root.JobAISites;
    sites.register(sites.createSiteAdapter({
        id: 'boss',
        domain: 'zhipin.com',
        displayName: 'Boss直聘',
        listSelectors: {
            jobList: 'ul.job-list-box, .job-list-box, .search-job-result, ul.recommend-list',
            jobItem: 'li.company-job-item, li.job-card-wrapper, li[class*="job-card"], .job-card-wrapper, .job-card-left, .job-card-box, li[data-index]',
            title: 'p.name, .job-name a, .job-title a, .job-name span, .job-title span, .job-name, .job-title, span[class*="job-name"], span[class*="job-title"]',
            company: '.company-name a, .company-text a, .company-name span, .company-text span, .company-name, .company-text, span[class*="company"], a.company-info-top',
            salary: '.salary span, .job-salary span, .salary, .job-salary, span[class*="salary"], span[class*="money"], .red',
            location: '.job-area span, .job-location span, .area span, .job-area, .area, span[class*="area"]',
            experience: '.tag-list li, .job-info span, ul.tag-list li, span[class*="experience"], li[class*="experience"]',
            education: '.tag-list li, .job-info span, ul.tag-list li, span[class*="education"], li[class*="education"]',
            description: '.job-desc, .job-detail-text, .job-desc-wrapper, .job-detail-section, div[class*="desc"]'
        },
        detail: {
            title: ['.job-banner .name', 'h1.job-title', '.job-name'],
            company: ['.company-info .name', '.sider-company .company-name', 'a.company-info-top'],
            salary: ['.job-banner .salary', '.salary'],
            location: ['.job-banner .location-address', '.job-area'],
            body: ['.job-sec-text', '.job-detail-section', '.job-detail']
        },
        isDetailUrl: function (host, path) {
            if (host.indexOf('zhipin.com') === -1 || path.indexOf('job_detail') === -1) {
                return false;
            }
            var last = path.replace(/\/+$/, '').split('/').pop();
            return last !== '' && last !== 'job_detail';
        }
    }));
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = sites.all().filter(function (item) { return item.id === 'boss'; })[0];
    }
})(typeof globalThis !== 'undefined' ? globalThis : this);
