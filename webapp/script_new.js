const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();

console.log("WebApp инициализирован");

document.getElementById('buy-btn').addEventListener('click', () => {
    alert("Кнопка нажата!"); // Если это не всплывает — проблема в HTML/JS
    
    const orderData = {
        items: [{title: "Пицца", count: 1}],
        total: 500
    };

    try {
        tg.sendData(JSON.stringify(orderData));
        alert("Данные отправлены в бота!"); // Если это всплывает, а в боте пусто — проблема в боте
    } catch (e) {
        alert("Ошибка: " + e.message);
    }
});