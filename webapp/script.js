document.getElementById('checkout-btn').onclick = () => {
    const order = Object.keys(cart).map(id => ({ ...products.find(p=>p.id==id), count: cart[id] }));
    const total = order.reduce((s, i) => s + i.price * i.count, 0);
    
    // Подготавливаем данные
    const data = JSON.stringify({ items: order, total: total });
    
    // ОТПРАВЛЯЕМ ДАННЫЕ
    tg.sendData(data);
    
    // НЕ ЗАКРЫВАЕМ СРАЗУ! 
    // Дадим пользователю понять, что заказ ушел.
    const btn = document.getElementById('checkout-btn');
    btn.textContent = "✅ Заказ отправлен!";
    btn.style.backgroundColor = "#28a745"; // Зеленый цвет успеха
    btn.disabled = true;

    // Закрываем через 1.5 секунды, чтобы человек успел увидеть успех
    setTimeout(() => {
        tg.close();
    }, 1500);
};