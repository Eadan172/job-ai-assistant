(function (root) {
    if (!root.JobAISites && typeof require === 'function') {
        require('./common.js');
    }
    var sites = root.JobAISites;
    sites.register(sites.createSiteAdapter({
        id: 'zhaopin',
        domain: 'zhaopin.com',
        displayName: '智联招聘',
        listSelectors: {
            jobList: '.positionlist, .joblist, .joblist-box, .joblist-box',
            jobItem: '.positionlist-item, .job-item, .joblist-box__item, .job-item',
            title: '.position-title, .job-title, .jobinfo__top, .job-title a',
            company: '.company-name, .company, .companyinfo__top, .company-name a',
            salary: '.position-salary, .salary, .jobinfo__salary, .salary span',
            location: '.position-location, .area, .jobinfo__other, .position-location span',
            experience: '.position-require span, .attr, .jobinfo__other span, .position-require',
            education: '.position-require span, .attr, .jobinfo__other span, .position-require',
            description: '.position-desc, .desc, .jobinfo__detail, .position-desc'
        },
        detail: {
            title: ['.summary-plane__title', '.job-title', 'h1'],
            company: ['.company__title', '.company-name'],
            salary: ['.summary-plane__salary', '.jobinfo__salary'],
            location: ['.summary-plane__info li', '.job-address'],
            body: ['.describt', '.job-detail', '.position-desc']
        },
        isDetailUrl: function (host, path) {
            if (host.indexOf('zhaopin.com') === -1) {
                return false;
            }
            if (path.indexOf('search') !== -1 || path.indexOf('joblist') !== -1) {
                return false;
            }
            var detailed = path.indexOf('jobdetail') !== -1 || path.indexOf('/job/') !== -1;
            return detailed && /\d{3,}/.test(path);
        }
    }));
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = sites.all().filter(function (item) { return item.id === 'zhaopin'; })[0];
    }
})(typeof globalThis !== 'undefined' ? globalThis : this);
