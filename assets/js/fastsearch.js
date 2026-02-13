// 検索実行のラグ（ミリ秒）
const searchDelay = 300; 
let timeout = null;

// PaperModの標準入力IDを取得
const searchInput = document.getElementById('searchInput');

if (searchInput) {
    // 標準のinputイベントをデバウンス（防振）処理で包む
    searchInput.addEventListener('input', function(e) {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            // ここで検索処理が実行される
            console.log("Searching for:", this.value);
        }, searchDelay);
    });
}
