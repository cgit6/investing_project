from flask import Flask, request, jsonify
from flask import render_template, redirect
from flask import g
import sqlite3
import requests 
import math
import os
import matplotlib.pyplot as plt
import matplotlib
# 這什麼?
matplotlib.use("agg") 

# 創建 flask
app = Flask(__name__) 
# db 位置
database = "datafile.db"

# 連結數據庫
def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect(database)
    return g.sqlite_db

# 會自動執行
@app.teardown_appcontext
def close_connection(exception):
    # 每完成一次發送 request 就會關閉一次 sql db
    print("我們正在關閉 sql connection....") 
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

# home page
@app.route("/")
def home():
    # 更新首頁的狀態
    conn = get_db()
    cursor = conn.cursor()
    result = cursor.execute("select * from cash")
    cash_result = result.fetchall() # 獲取所有資料[(1,15000,500.0,'十月份薪水','2023-10-03'),(2,10000,1500.0,'津貼'，'2023-10-03')]
    # 計算總額(台幣, 美金) 
    taiwanese_dollars = 0
    us_dollars = 0 

    for data in cash_result:
        taiwanese_dollars += data[1]
        us_dollars += data[2]

    # 獲取匯率資訊
    r=requests.get('https://tw.rter.info/capi.php')
    currency=r.json() # 解析 json 獲取匯率資訊

    total = math.floor(taiwanese_dollars + us_dollars * currency["USDTWD"]["Exrate"])

    # 獲取當前持股數據
    result2 = cursor.execute("select * from stock")
    stock_result = result2.fetchall()
    unique_stock_list = [] # 紀錄當前買了那些股票

    # 處理當重複買相同股票的紀錄
    for data in stock_result:
        if data[1] not in unique_stock_list:
            unique_stock_list.append(data[1])

    # 計算股票總市值
    total_stock_value = 0
    # 計算單一股票數據
    stock_info = []

    # 對每個股票類別做數據的計算
    for stock in unique_stock_list:
        result = cursor.execute(
            "select * from stock where stock_id =?", (stock, ))
        result = result.fetchall()
        stock_cost = 0 # 計算單一股票的總成本
        shares = 0  # 單一股票股數
        for d in result:
            print("d[2]",d[2])
            shares += d[2]
            stock_cost += d[2] * d[3] + d[4] + d[5] # 市價*數量 + 手續費 + 稅金
        
        # 取得目前股價
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo=" + stock
        response = requests.get(url)
        data = response.json()
        
        # 處理的方式跟數據格式有關(如果股票不存在呢?)
        price_array = data['data']
        current_price = float(price_array[len(price_array) - 1][6])
        # 接下來計算單一股票的總市值
        print("shares:",shares)
        total_value = round(current_price * shares)
        # 更新總持倉的金額
        total_stock_value += total_value
        # 單一股票的平均成本
        avg_coat = round(stock_cost/shares, 2)
        # 單一股票的報酬率
        rate_of_return = round((total_value - stock_cost) * 100/stock_cost,2)

        # 處理完的數值存在 stock_info
        stock_info.append({'stock_id': stock, 'stock_cost': stock_cost,
                           'total_value': total_value, 'avg_coat': avg_coat,
                           'shares': shares, 'current_price': current_price, 'rate_of_return': rate_of_return})

    # 計算每支股票的百分比
    for stock in stock_info:
        stock["value_percentage"] = round(stock["total_value"]* 100 / total_stock_value, 2)
    
    # 如果當前stock存在數據，才繪製圖表
    # 繪製股票圓餅圖
    if len(unique_stock_list) != 0:
        labels = tuple(unique_stock_list)
        sizes = [d['total_value'] for d in stock_info]
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, labels=labels, autopct=None, shadow=None)
        fig.subplots_adjust(top=1, bottom=0, right=1,
                            left=0, hspace=0, wspace=0)
        # 儲存圖片，一定要存在static 資料夾
        plt.savefig("static/piechart.jpg", dpi=200)
    else:
        # 如果狀態更新後資產為0 時則刪掉圖片
        try:
            # 移除圖片
            os.remove('static/piechart.jpg')
        except:
            pass

    # 繪製股票現金圓餅圖
    if us_dollars != 0 or taiwanese_dollars != 0 or total_stock_value != 0:
        labels = ('USD', 'TWD', 'Stock')
        sizes = (us_dollars * currency['USDTWD']['Exrate'],
                 taiwanese_dollars, total_stock_value)
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, labels=labels, autopct=None, shadow=None)
        fig.subplots_adjust(top=1, bottom=0, right=1,
                            left=0, hspace=0, wspace=0)
        plt.savefig("static/piechart2.jpg", dpi=200)
    else:
        # 如果狀態更新後資產為0 時則刪掉圖片
        try:
            os.remove('static/piechart2.jpg')
        except:
            pass

    
    # 選染當前頁面所需要的數據
    # show_pic_1 的 value 是 boolean
    data = {"show_pic_1": os.path.exists("static/piechart.jpg"), "show_pic_2": os.path.exists("static/piechart2.jpg"), "total": total, "currency": currency["USDTWD"]["Exrate"], "ud":us_dollars, "td": taiwanese_dollars, "cash_result": cash_result, "stock_info":stock_info}


    return render_template('index.html', data = data)

# cash page
@app.route("/cash")
def cash_form():
    return render_template('cash.html')

@app.post('/cash') 
def submit_cash():
    # print(request.values["taiwanese-dollar"])# 想要獲取特定屬性就是抓 input tag 的 name
    # 使用者提交的資料，存進 sqllite 中
    taiwanese_dollars = 0
    us_dollars = 0
    if request.values['taiwanese-dollars'] != '':
        taiwanese_dollars = request.values['taiwanese-dollars']
    if request.values['us-dollars'] != '':
        us_dollars = request.values['us-dollars']
    note = request.values['note']
    date = request.values['date']

    # 更新數據庫資料
    conn = get_db()
    cursor = conn.cursor() # 建立一個操作的物件
    # 執行
    cursor.execute("""
        insert into cash(taiwanese_dollars, us_dollars, note, date_info) values (?, ?, ?, ?)
    """, (taiwanese_dollars, us_dollars, note, date))

    conn.commit()
    # 返回 hame page
    return redirect("/")

# 刪除渲染頁面的數據
@app.route('/cash-delete', methods=['POST'])
def cash_delete():
    #  request.values 索引的 key 一定要是 input 的 name
    transaction_id = request.values['id']
    # 操作 db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""delete from cash where transaction_id=?""",(transaction_id, ))
    conn.commit()
    return redirect("/") # 有重新更新(渲染)的感覺


# stock page
@app.route("/stock")
def stock():
    return render_template('stock.html')

@app.post("/stock")
def submit_stock():
    # 取得股票資訊、日期資料
    stock_id = request.values['stock_id']
    stock_num = request.values['stock_num']
    stock_price = request.values['stock_price']

    processing_fee = 0
    tax = 0

    # 確認數據狀態
    # if 
    if request.values['processing_fee'] != '':
        processing_fee = request.values['processing_fee']
    if request.values['tax'] != '':
        tax = request.values['tax']
    date = request.values['date']

    # 更新數據庫資料
    conn = get_db()
    cursor = conn.cursor() # 建立一個操作的物件
    # 執行
    cursor.execute("""insert into stock (stock_id, stock_num, stock_price, processing_fee, tax, date_info) values (?, ?, ?, ?, ?, ?)""",
                   (stock_id, stock_num, stock_price, processing_fee, tax, date))

    conn.commit()

    # 返回 hame page
    return redirect("/")



if __name__ == "__main__":
    app.run(debug=True)
