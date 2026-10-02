(function (root) {
    if (!root.JobAISites && typeof require === 'function') {
        require('./common.js');
    }
    var sites = root.JobAISites;
    sites.register(sites.createSiteAdapter({
        id: '51job',
        domain: '51job.com',
        displayName: '前程无忧',
        listSelectors: {
            jobList: '.joblist, .el-table__body, .joblist, .joblist-box',
            jobItem: '.job-item, .el-table__row, .j_joblist, .job-item',
            title: '.job-name, .job-title, .j_joblist .t, .job-name a',
            company: '.company-name, .company, .j_joblist .er, .company-name a',
            salary: '.job-salary, .salary, .j_joblist .sal, .salary span',
            location: '.job-location, .area, .j_joblist .d, .job-location span',
            experience: '.job-attr span, .attr, .j_joblist .d span, .job-attr',
            education: '.job-attr span, .attr, .j_joblist .d span, .job-attr',
            description: '.job-desc, .desc, .j_joblist .desc, .job-desc'
        },
        detail: {
            title: ['.cn h1', '.job-name', 'h1'],
            company: ['.cname', '.company-name'],
            salary: ['.cn strong', '.job-salary'],
            location: ['.msg', '.job-location'],
            body: ['.job-detail-content', '.bmsg', '.job-desc']
        },
        isDetailUrl: function (host, path) {
            if (host.indexOf('51job.com') === -1) {
                return false;
            }
            if (path.indexOf('search') !== -1 || path.indexOf('joblist') !== -1 || path.indexOf('job-list') !== -1) {
                return false;
            }
            return /\d{3,}/.test(path);
        }
    }));
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = sites.all().filter(function (item) { return item.id === '51job'; })[0];
    }
})(typeof globalThis !== 'undefined' ? globalThis : this);
