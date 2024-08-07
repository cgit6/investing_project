import sqlite3
# 連結到資料庫
conn = sqlite3.connect("./investing_project/datafile4.db")
cursor = conn.cursor()

# 創建 table1 => cash
cursor.execute(
    """create table cash (transaction_id integer primary key, taiwanese_dollars integer, us_dollars real, note varchar(30), date_info date)""")

# 創建 table2 => stock
cursor.execute(
    """create table stock (transaction_id integer primary key, stock_id varchar(10), stock_num integer, stock_price real, processing_fee integer, tax integer, date_info date)""")

conn.commit()
conn.close()
