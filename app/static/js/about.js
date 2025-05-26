// About Page JavaScript
// 重構後的腳本，支援可訪問性和效能優化

class AboutPageController {
  constructor() {
    this.prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.isAnimating = false;
    this.observers = new Map();
    
    this.init();
  }

  init() {
    this.initTheme();
    this.initScrollAnimations();
    this.initStatCounters();
    this.initSmoothScroll();
    this.bindEvents();
  }

  // 主題切換功能
  initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const themeIcon = document.getElementById('theme-icon');
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
      document.documentElement.classList.add('dark');
      document.body.setAttribute('data-theme', 'dark');
      if (themeIcon) themeIcon.className = 'fas fa-sun';
    } else {
      if (themeIcon) themeIcon.className = 'fas fa-moon';
    }
  }

  toggleTheme() {
    const html = document.documentElement;
    const body = document.body;
    const themeIcon = document.getElementById('theme-icon');
    const isDark = html.classList.contains('dark');
    
    if (isDark) {
      html.classList.remove('dark');
      body.removeAttribute('data-theme');
      if (themeIcon) themeIcon.className = 'fas fa-moon';
      localStorage.setItem('theme', 'light');
    } else {
      html.classList.add('dark');
      body.setAttribute('data-theme', 'dark');
      if (themeIcon) themeIcon.className = 'fas fa-sun';
      localStorage.setItem('theme', 'dark');
    }
  }

  // 滾動動畫初始化
  initScrollAnimations() {
    if (this.prefersReducedMotion) return;

    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const scrollObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    }, observerOptions);

    // 為內容卡片添加進入動畫
    document.querySelectorAll('.content-card').forEach((card, index) => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(20px)';
      card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
      scrollObserver.observe(card);
    });

    this.observers.set('scroll', scrollObserver);
  }

  // 統計數字計數動畫
  initStatCounters() {
    if (this.prefersReducedMotion) return;

    const statObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const valueElement = entry.target.querySelector('[data-count]');
          if (valueElement && !valueElement.dataset.animated) {
            valueElement.dataset.animated = 'true';
            this.animateCounter(valueElement);
          }
        }
      });
    }, { threshold: 0.5 });

    document.querySelectorAll('.stat-card').forEach(card => {
      statObserver.observe(card);
    });

    this.observers.set('stats', statObserver);
  }

  // 數字計數動畫
  animateCounter(element) {
    const target = parseInt(element.dataset.count);
    const duration = 2000;
    const prefix = element.dataset.prefix || '';
    const suffix = element.dataset.suffix || '';
    
    if (isNaN(target)) return;

    let startTimestamp = null;
    
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      
      // 使用 easeOutCubic 緩動函數
      const easeOutCubic = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(easeOutCubic * target);
      
      element.textContent = prefix + current.toLocaleString() + suffix;
      
      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };
    
    requestAnimationFrame(step);
  }

  // 平滑滾動
  initSmoothScroll() {
    if (this.prefersReducedMotion) return;

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', (e) => {
        e.preventDefault();
        const target = document.querySelector(anchor.getAttribute('href'));
        if (target) {
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });
  }

  // 事件綁定
  bindEvents() {
    // 主題切換按鈕
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => this.toggleTheme());
    }

    // 系統主題變化監聽
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem('theme')) {
        const themeIcon = document.getElementById('theme-icon');
        if (e.matches) {
          document.documentElement.classList.add('dark');
          document.body.setAttribute('data-theme', 'dark');
          if (themeIcon) themeIcon.className = 'fas fa-sun';
        } else {
          document.documentElement.classList.remove('dark');
          document.body.removeAttribute('data-theme');
          if (themeIcon) themeIcon.className = 'fas fa-moon';
        }
      }
    });

    // 減少動畫偏好變化監聽
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
      this.prefersReducedMotion = e.matches;
      if (e.matches) {
        this.disableAnimations();
      }
    });
  }

  // 禁用動畫
  disableAnimations() {
    // 停止所有觀察者
    this.observers.forEach(observer => observer.disconnect());
    this.observers.clear();

    // 立即顯示所有元素
    document.querySelectorAll('.content-card').forEach(card => {
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    });

    // 立即設置統計數字
    document.querySelectorAll('[data-count]').forEach(element => {
      const target = parseInt(element.dataset.count);
      const prefix = element.dataset.prefix || '';
      const suffix = element.dataset.suffix || '';
      
      if (!isNaN(target)) {
        element.textContent = prefix + target.toLocaleString() + suffix;
      }
    });
  }

  // 清理資源
  destroy() {
    this.observers.forEach(observer => observer.disconnect());
    this.observers.clear();
  }
}

// 初始化頁面控制器
document.addEventListener('DOMContentLoaded', () => {
  window.aboutPageController = new AboutPageController();
});

// 頁面卸載時清理資源
window.addEventListener('beforeunload', () => {
  if (window.aboutPageController) {
    window.aboutPageController.destroy();
  }
}); 