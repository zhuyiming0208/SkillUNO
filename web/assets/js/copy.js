/**
 * SkillUNO 网页商店 · 复制工具
 */

/**
 * 复制安装命令，成功/失败均显示 toast
 */
function copyInstallCommand(modId) {
    const cmd = `skilluno mod install ${modId}`;
    copyToClipboard(cmd).then(
        () => showCopyToast('已复制到剪贴板'),
        () => showCopyToast('复制失败，请手动复制')
    );
}

/**
 * 通用复制：优先 navigator.clipboard，失败回退 execCommand
 */
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    }
    // fallback
    return new Promise((resolve, reject) => {
        try {
            const el = document.createElement('textarea');
            el.value = text;
            el.style.position = 'fixed';
            el.style.opacity = '0';
            document.body.appendChild(el);
            el.select();
            const ok = document.execCommand('copy');
            document.body.removeChild(el);
            ok ? resolve() : reject(new Error('execCommand failed'));
        } catch (e) {
            reject(e);
        }
    });
}

/**
 * 底部 toast，2 秒后消失
 */
function showCopyToast(message) {
    let toast = document.getElementById('copy-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'copy-toast';
        toast.className = 'copy-toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
        toast.classList.remove('show');
    }, 2000);
}
