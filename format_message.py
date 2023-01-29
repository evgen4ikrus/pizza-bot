def create_product_description(product):
    description = product.get('description')
    title = product.get('name')
    price = product.get('price')[0].get('amount')
    text = f'{title}\nСтоимость: {price} рублей\n\n{description}'
    return text


def create_cart_description(cart_items):
    cart_description = ''
    total_price = 0
    for item in cart_items:
        one_for_price = item.get('unit_price').get('amount')
        quantity = item.get('quantity')
        price = one_for_price * quantity
        total_price += price
        title = item.get('name')
        description = item.get('description')
        if quantity == 1:
            cart_description += f"{title}\n{description}\n{quantity} пицца в корзине на сумму {price} рублей\n\n"
        else:
            cart_description += f"{title}\n{description}\n{quantity} пицц(ы) в корзине на сумму {price} рублей\n\n"
    cart_description += f'К оплате: {total_price} рублей'
    return cart_description
