import requests, json

#Hotels
hotel_db = requests.get(
    "https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/hotel_db.json"
).json()

#Restaurants
restaurant_db = requests.get(
    "https://raw.githubusercontent.com/budzianowski/multiwoz/master/db/restaurant_db.json"
).json()

print(hotel_db[0])
print(restaurant_db[0])

print(len(hotel_db), "hoteles")
print(len(restaurant_db), "restaurantes")
