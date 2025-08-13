from lunarcalendar import Converter, Solar, Lunar

# 2025年1月1日（新暦）を旧暦に変換して表示するテスト
solar_date = Solar(2025, 1, 1)
lunar_date = Converter.Solar2Lunar(solar_date)

print("新暦:", solar_date)
print("旧暦:", lunar_date)
