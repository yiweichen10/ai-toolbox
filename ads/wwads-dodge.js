// wwads 悬浮广告避让脚本
// 问题：wwads 悬浮广告（宽屏 ≥1300px 浮右下角）与本站右下角的「暗黑模式 / 返回顶部」按钮重叠，
//       且按钮会压住广告（违反 wwads「不得遮挡广告」规则）。
// 解法：本脚本检测 wwads 悬浮广告渲染后，读取其高度，把两个按钮的 bottom 顶到广告正上方（紧贴、不重叠）。
//       - 仅当广告处于 fixed 悬浮态（宽屏）时才避让；窄屏广告回固定位，按钮恢复 CSS 默认右下角。
//       - 未引入 wwads 的页面（无 .wwads-cn.wwads-sticky）不做事。
//       - 不改变 wwads 自身任何代码，仅调整本站按钮位置，合规。
(function () {
  'use strict';

  function adjust() {
    var ad = document.querySelector('.wwads-cn.wwads-sticky');
    var fab = document.querySelector('.dark-toggle-fab');
    var topBtn = document.getElementById('backToTop');
    if (!ad || !fab || !topBtn) return;

    var cs = getComputedStyle(ad);
    if (cs.position === 'fixed') {
      // 广告悬浮在右下角 bottom:0，将按钮顶到广告上方
      var h = Math.ceil(ad.getBoundingClientRect().height);
      var gap = 16;
      topBtn.style.bottom = (h + gap) + 'px';
      // 暗黑按钮在返回顶部上方，约 44px 高 + 12px 间距
      fab.style.bottom = (h + gap + 56) + 'px';
    } else {
      // 非悬浮态（窄屏/固定位），恢复由 CSS 控制的默认位置
      topBtn.style.bottom = '';
      fab.style.bottom = '';
    }
  }

  function start() {
    adjust();
    // wwads 由 makemoney.js 异步渲染，轮询若干次确保抓到悬浮态
    var n = 0;
    var iv = setInterval(function () {
      adjust();
      if (++n > 20) clearInterval(iv);
    }, 400);
    // 窗口缩放可能触发 悬浮<->固定 切换，重算
    window.addEventListener('resize', function () {
      clearInterval(iv);
      adjust();
    });
  }

  if (document.readyState !== 'loading') {
    start();
  } else {
    document.addEventListener('DOMContentLoaded', start);
  }
})();
